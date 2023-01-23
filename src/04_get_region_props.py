import numpy as np
import pandas as pd
import dask
import dask.array as da
import dask.dataframe as dd
from dask_regionprops import regionprops


# Set up the workers
#from dask_jobqueue import SLURMCluster
#from dask.distributed import Client

# This step below is highly specific to a given HPC environment
#cluster = SLURMCluster(cores=1,
#        memory='96 GB',
#        job_directives_skip=['--mem'],
##        job_extra_directives=['--mem-per-cpu=96000'],
#        walltime='24:00:00',
#        log_directory="logs/")
#cluster.adapt(minimum=1, maximum=7)
#client = Client(cluster)

# Load Data
masks = da.from_zarr('../output/dask/segmentation.zarr')

result = regionprops(masks)
res = result.compute() # works as expected
res.to_csv('dask_properties.csv')
