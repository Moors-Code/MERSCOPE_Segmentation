# This is the main script to exectue the segmentation
import numpy as np
import os
import argparse
import re
from scipy import sparse, io
from cellpose import models
from cellpose.io import imread
from skimage import segmentation
import cpdist
from datetime import datetime
import dask.array as da
import zarr

# Get input
filename = "../output/dask/mosaic_stacks.zarr"
#im = zarr.load(filename)
im = da.from_zarr(filename)
im = im.rechunk(chunks=(7,im.shape[1] // 19,im.shape[2] //18))

from dask_jobqueue import SLURMCluster
from dask.distributed import Client

# This step below is highly specific to a given HPC environment
cluster = SLURMCluster(cores=1,
        memory='48 GB',
        job_directives_skip=['--mem'],
        job_extra_directives=['--mem-per-cpu=48000'],
        walltime='24:00:00',
        log_directory="logs/")
cluster.adapt(minimum=1, maximum=72)
client = Client(cluster)

### Now start the segmentation and record the time
# Note the iou threshold is farily low because this is computed across all z-stacks at a time.
start_time = datetime.now()
labels_dist = cpdist.segment(image=im,model_type="nuclei",diameter=80,fast_mode=True,iou_depth=(0,2,2),iou_threshold=0.1,cellprob_threshold=-0.3,flow_threshold=0.6)
labels_dist = client.persist(labels_dist)


# Save as zarr
outputdir = "../output/dask/"
outname = "segmentation.zarr"
da.to_zarr(arr=labels_dist, url=os.path.join(outputdir,outname))
time_elapsed = datetime.now() - start_time
print('Time elapsed (hh:mm:ss.ms) {}'.format(time_elapsed))
