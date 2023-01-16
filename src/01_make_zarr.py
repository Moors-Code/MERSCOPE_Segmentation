# This script reads in all the individual z stacks and outputs a single zarr document
import numpy as np
import os
from cellpose.io import imread
import zarr

im0 = imread('../images/mosaic_DAPI_z0.tif')
im1 = imread('../images/mosaic_DAPI_z1.tif')
im2 = imread('../images/mosaic_DAPI_z2.tif')
im3 = imread('../images/mosaic_DAPI_z3.tif')
im4 = imread('../images/mosaic_DAPI_z4.tif')
im5 = imread('../images/mosaic_DAPI_z5.tif')
im6 = imread('../images/mosaic_DAPI_z6.tif')

out = np.stack((im0,im1,im2,im3,im4,im5,im6),axis=0)
zarr.save('../output/dask/mosaic_stacks.zarr',out)
