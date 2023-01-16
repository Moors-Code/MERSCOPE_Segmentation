"""Segments detected regions in a chunked dask array.

This is based on https://raw.githubusercontent.com/MouseLand/cellpose/main/cellpose/contrib/distributed_segmentation.py
The original version was designed for 3D annotation, I adapted it here for 2D segmentation.
Heavily based on dask_image.ndmeasure.label, which uses non-overlapping blocks
with a structuring element that links segments at the chunk boundaries.
Difference to dask_image.ndmeasure.label is that overlapping chunks are used.
"""
import functools
import logging
import operator

import dask
import dask.array as da
import numpy as np

class DistSegError(Exception):
    """Error in image segmentation."""

try:
    from dask_image.ndmeasure._utils import _label
    from sklearn import metrics as sk_metrics
except ModuleNotFoundError as e:
    raise DistSegError("Install 'cellpose[distributed]' for distributed segmentation dependencies") from e


logger = logging.getLogger(__name__)

# Segmentation function
def segment(image,
                 diameter,
                 iou_depth=(0,2,2), # This should be a tuple for 3D
                 iou_threshold=0.7,
                 cellprob_threshold=-0.3,
                 flow_threshold=0.6,
                 fast_mode = True,
                 model_type = 'nuclei'):
    """Use cellpose to segment nuclei in fluorescence data.

    Parameters
    ----------
    image : array of shape (z, y, x, channel) # for now without channel
        Image used for detection of objects
    diameter : int
        Approximate diameter (in pixels) of a segmented region, i.e. cell width
    model_type : str
        "cyto" or "nuclei"
    fast_mode : bool
        In fast mode, network averaging, tiling, and augmentation are turned off.
    iou_depth: dask depth parameter
        Number of pixels of overlap to use in intersection-over-union calculation when
        linking segments across neighboring, overlapping dask chunk regions.
    iou_threshold: float
        Minimum intersection-over-union in neighboring, overlapping dask chunk regions
        to be considered the same segment.  The region for calculating IOU is given by the
        iou_depth parameter.

    Returns:
        segments : array of int32 with same shape as input
            Each segmented cell is assigned a number and all its pixels contain that value (0 is background)
    """

    assert image.ndim == 3, image.ndim
    #assert image.shape[-1] in {1, 2}, image.shape # This checks that the last one is the channel, unnecessary
    #assert diameter[1] == diameter[2], diameter # also unnecessary
    diameter_yx = diameter
    #anisotropy = diameter[0] / diameter[1] if use_anisotropy else None
    # Compute chunk size

#    image = da.asarray(image)
    print("We have {} chunks".format(np.prod(image.numblocks)))
    image.numblocks

    # Maybe rather ensure that Z is chunked together?
    #image = image.rechunk({0:-1})
    #image = image.rechunk({-1: -1},)  # color channel is chunked together # The -1:-1 means last dimension ([-1]) full size (encoded by -1)

    #depth = tuple(np.ceil(diameter).astype(np.int64)) #This is for 3D as the Z dimension can be different for diameter
    depth = (0,diameter,diameter)
    boundary = "reflect"

    # No chunking in channel direction
    image = da.overlap.overlap(image, depth, boundary) # If you have a channel you need to do + (,0) to depth here
    print("We have {} chunks after overlapping".format(np.prod(image.numblocks)))
    print(image.chunksize)

    # This creates an iterable object that contains the index (used for rnd seed) and the chunk itself
    block_iter = zip(
        np.ndindex(*image.numblocks),
        map(
            functools.partial(operator.getitem, image),
            da.core.slices_from_chunks(image.chunks),
        ),
    )

    labeled_blocks = np.empty(image.numblocks, dtype=object) # Also here there would be a [:-1] to remove the channel
    total = None

    for index, input_block in block_iter:
        labeled_block, n = dask.delayed(segment_chunk, nout=2)(
            input_block,
            model_type,
            diameter_yx,
            cellprob_threshold,
            flow_threshold,
            fast_mode,
            index,
        )

        shape = input_block.shape #[:-1] # Here used to be a [:-1] to take off the channel
        labeled_block = da.from_delayed(labeled_block, shape=shape, dtype=np.int32)

        n = dask.delayed(np.int32)(n)
        n = da.from_delayed(n, shape=(), dtype=np.int32)

        total = n if total is None else total + n

        block_label_offset = da.where(labeled_block > 0, total, np.int32(0)) #This is to increase the label numbers in the blocks
        labeled_block += block_label_offset

        labeled_blocks[index] = labeled_block # Again the index would be index[:-1]
        total += n
    # Put all the blocks together
    block_labeled = da.block(labeled_blocks.tolist())

    depth = da.overlap.coerce_depth(len(depth), depth)

    if np.prod(block_labeled.numblocks) > 1:
        iou_depth = da.overlap.coerce_depth(len(depth), iou_depth)

        if any(iou_depth[ax] > depth[ax] for ax in depth.keys()):
            raise DistSegError("iou_depth (%s) > depth (%s)" % (iou_depth, depth))

        trim_depth = {k: depth[k] - iou_depth[k] for k in depth.keys()}
        block_labeled = da.overlap.trim_internal(
            block_labeled, trim_depth, boundary=boundary
        )
        block_labeled = link_labels(
            block_labeled,
            total,
            iou_depth,
            iou_threshold=iou_threshold,
        )

        block_labeled = da.overlap.trim_internal(
            block_labeled, iou_depth, boundary=boundary
        )

    else:
        block_labeled = da.overlap.trim_internal(
            block_labeled, depth, boundary=boundary
        )

    return block_labeled
# Define the segment_chunk function
def segment_chunk(
    chunk,
    model_type,
    diameter_yx,
    cellprob_threshold,
    flow_threshold,
    fast_mode,
    index
):
    """Use cellpose to segment a chunk.

    Parameters
    ----------
    chunk : dask chunk of shape (y, x)
        Chunk used for detection of objects
    diameter_yx : int
        Approximate diameter (in pixels) of a segmented region, i.e. cell width
    model_type : str
        "cyto" or "nuclei"
    fast_mode : bool
        In fast mode, network averaging, tiling, and augmentation are turned off.
    index : int
        This is the block index used for seeding the RNG

    Returns:
        segments : array of int32 with same shape as input
            Each segmented cell is assigned a number and all its pixels contain that value (0 is background)
    """
    # Cellpose seems to have some randomness, which is made deterministic by using the block
    # details as a random seed.
    np.random.seed(index)

    from cellpose import models

    model = models.Cellpose(gpu=False, model_type=model_type, net_avg=not fast_mode)

    logger.info("Evaluating model")
    segments, _, _, _ = model.eval(
        chunk,
   #     channels=channels,
        z_axis=0,
   #     channel_axis=3,
        cellprob_threshold=cellprob_threshold,
        flow_threshold=flow_threshold,
        diameter=diameter_yx,
        do_3D=False,
   #     anisotropy=anisotropy,
        net_avg=not fast_mode,
        augment=not fast_mode,
        tile=not fast_mode,
    )
    logger.info("Done segmenting chunk")

    return segments.astype(np.int32), segments.max()

# Other helper functions
def link_labels(block_labeled, total, depth, iou_threshold=1):
    """
    Build a label connectivity graph that groups labels across blocks,
    use this graph to find connected components, and then relabel each
    block according to those.
    """
    label_groups = label_adjacency_graph(block_labeled, total, depth, iou_threshold)
    new_labeling = _label.connected_components_delayed(label_groups)
    return _label.relabel_blocks(block_labeled, new_labeling)


def label_adjacency_graph(labels, nlabels, depth, iou_threshold):
    all_mappings = [da.empty((2, 0), dtype=np.int32, chunks=1)]

    slices_and_axes = get_slices_and_axes(labels.chunks, labels.shape, depth)
    for face_slice, axis in slices_and_axes:
        face = labels[face_slice]
        mapped = _across_block_iou_delayed(face, axis, iou_threshold)
        all_mappings.append(mapped)

    i, j = da.concatenate(all_mappings, axis=1)
    result = _label._to_csr_matrix(i, j, nlabels + 1)
    return result


def _across_block_iou_delayed(face, axis, iou_threshold):
    """Delayed version of :func:`_across_block_label_grouping`."""
    _across_block_label_grouping_ = dask.delayed(_across_block_label_iou)
    grouped = _across_block_label_grouping_(face, axis, iou_threshold)
    return da.from_delayed(grouped, shape=(2, np.nan), dtype=np.int32)


def _across_block_label_iou(face, axis, iou_threshold):
    unique = np.unique(face)
    face0, face1 = np.split(face, 2, axis)

    intersection = sk_metrics.confusion_matrix(face0.reshape(-1), face1.reshape(-1))
    sum0 = intersection.sum(axis=0, keepdims=True)
    sum1 = intersection.sum(axis=1, keepdims=True)

    # Note that sum0 and sum1 broadcast to square matrix size.
    union = sum0 + sum1 - intersection

    # Ignore errors with divide by zero, which the np.where sets to zero.
    with np.errstate(divide="ignore", invalid="ignore"):
        iou = np.where(intersection > 0, intersection / union, 0)

    labels0, labels1 = np.nonzero(iou >= iou_threshold)

    labels0_orig = unique[labels0]
    labels1_orig = unique[labels1]
    grouped = np.stack([labels0_orig, labels1_orig])

    valid = np.all(grouped != 0, axis=0)  # Discard any mappings with bg pixels
    return grouped[:, valid]


def get_slices_and_axes(chunks, shape, depth):
    ndim = len(shape)
    depth = da.overlap.coerce_depth(ndim, depth)
    slices = da.core.slices_from_chunks(chunks)
    slices_and_axes = []
    for ax in range(ndim):
        for sl in slices:
            if sl[ax].stop == shape[ax]:
                continue
            slice_to_append = list(sl)
            slice_to_append[ax] = slice(
                sl[ax].stop - 2 * depth[ax], sl[ax].stop + 2 * depth[ax]
            )
            slices_and_axes.append((tuple(slice_to_append), ax))
    return slices_and_axes
