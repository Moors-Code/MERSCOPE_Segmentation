# Segmentation and image analysis of MERSCOPE data
This repository contains code to anlayse data produced by MERSCOPE. This involves the following steps:

- Segmentation using cellpose
- Counting transcripts per segments
- Deriving properties of segments

# The data
Currently the MERSCOPE output contains the following:
- stitched images of all FOVS (>1400) as large mosaic.tiff files (> 17GB) per z-stack (7 in total)
- table with called transcripts and their global (micron) coordinates

# Comments on the segmentation:

1. It takes roughly 1TB of RAM for a 16GB image
2. You have to change a protocol in the numpy pickle.dump to allow arrays larger than 4GB when writing the npy output. This is done by changing the hardcoded value of the pickle.dump protocol from 3 to 4 in
"/cluster/project/moor/kabach/miniconda3/envs/cellpose/lib/python3.8/site-packages/numpy/lib/format.py"
See https://github.com/MouseLand/cellpose/issues/178
3. Even then this takes about 53 hours per z-stack

# Distributed Segmentation

I here implemented an approach that utilizes [dask](https://www.dask.org/]) to parallelize the segmentation.
A lot of this based upon code in https://github.com/MouseLand/cellpose/blob/main/cellpose/contrib/distributed_segmentation.py

