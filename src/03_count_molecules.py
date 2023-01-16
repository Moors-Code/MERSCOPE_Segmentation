# Here I count the molecule within each segment
import numpy as np
import os
import zarr
import pandas as pd
import dask.array as da
from scipy import sparse, io
from datetime import datetime

start = datetime.now()
# Read in masks as dask.array
masks_full = da.from_zarr('../output/dask/segmentation.zarr')
n = masks_full.max().compute() + 1
allspots = pd.read_csv("../detected_transcripts.csv")
# I have to load it in memory otherwise the transcript assigning will have to read from disk for each spot
# Alternatively I could read per block which seems more complicated
# It would probably be even more efficient to do this as sparse matrix. Need to look at 3D sparse arrays or doing this per z stack..
# Conversion to pixel (MERSCOPE specific)
mi_per_pixel = 0.108 # This is the conversion of micrometer to pixel, can be found in the analysis.json output file
# We can check that by looking at FOV 0 global_x (micrometer) to x (pixel) ratio. God knows why this is not 0.108
allspots['pixel_x'] = np.rint(allspots['global_x'] / mi_per_pixel).astype(int) #round to integer
allspots['pixel_y'] = np.rint(allspots['global_y'] / mi_per_pixel).astype(int)

# There are negative values for pixel_y, yai, will delete for now.
allspots = allspots[allspots.pixel_y > 0]


for z in range(0,7):
    # We gonan do this now per fucked up fucky de fuck z stack because this is thing is too fucking large.
    # Need to get the global max first
    masks = masks_full[z,:,:]
    masks = masks.map_blocks(sparse.csr_matrix)
    masks = masks.compute()
    elapse = datetime.now() - start
    print("Loaded data, elapsed time {}".format(elapse))

    # Loading the spot csv, could be done as dask.df
    spots = allspots[allspots.global_z == z]

    print('Assigning spots')
#    spots = spots.sample(frac=0.01)
    ## Assigning transcript position to cell identity
    coords = np.stack([spots['pixel_y'],spots['pixel_x']],axis=0)
    it = np.nditer(coords,flags=['external_loop'],order='F')
    cell_id = []
    for x in it:
        cell_id += [masks[x[0],x[1]]]


    cell_id = np.asarray(cell_id)
    elapse = datetime.now() - start
    print("Elapsed time {}".format(elapse))


    # Now we can create a count matrix
    # I extract them as array assuming that's faster
    # This feels very inefficient
    genes = spots['gene']
    genes_uq = genes.unique()
    gncounts = []
    print('Creating matrix ')
    for i in range(1,n):
        if np.any(cell_id==i):
            tmp = genes[cell_id==i].value_counts()
        else:
            tmp = [0 for _ in range(genes_uq.size)]
            tmp = pd.Series(tmp)
            tmp.index = genes_uq
        gncounts += [tmp.rename("Cell_" + str(i))]


    count_matrix = pd.concat(gncounts,axis=1).fillna(0)

    out = 'count_matrix_{}.csv'.format(z)
    count_matrix.to_csv(out)
    #mtx = sparse.csr_matrix(count_matrix.values)
    #io.mmwrite('test.mtx',mtx)
    elapse = datetime.now() - start
    print("Elapsed time {}".format(elapse))
