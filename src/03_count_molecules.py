# Here I count the molecule within each segment
import numpy as np
import os
import zarr
import pandas as pd
import dask.array as da
from scipy import sparse, io
from datetime import datetime
from itertools import compress
from collections import Counter

start = datetime.now()
################# Read in Masks #########################
# Read in masks as dask.array
masks_full = da.from_zarr('../output/dask/segmentation.zarr')

################# Read in Spots #########################
# Read in transcripts
allspots = pd.read_csv("../detected_transcripts.csv")

# I have to load it in memory otherwise the transcript assigning will have to read from disk for each spot
# Alternatively I could read per block which seems more complicated
# It would probably be even more efficient to do this as sparse matrix. Need to look at 3D sparse arrays or doing this per z stack..
# Conversion to pixel (MERSCOPE specific)

# Conversion to pixel
arr = np.genfromtxt('../images/micron_to_mosaic_pixel_transform.csv')
# The micron to pixel is affine transformation involving a scaling and a translation. The below code is equivalent to the matrix multiplicaiton arr %*% [x,y,1]=[pixel_x,pixel_y,1]
allspots['pixel_x'] = np.rint(allspots['global_x'] * arr[0,0] + arr[0,2]).astype(int) #round to integer
allspots['pixel_y'] = np.rint(allspots['global_y'] * arr[1,1] + arr[1,2]).astype(int)

################# Setup count matrix #########################
# Define the rows of our matrix (might be different across z stacks)
# Rows
genes_uq = allspots['gene'].unique()
genes_uq = np.array([str(x) for x in genes_uq])
nrow = len(genes_uq)

#Cols
# Compute maximum cell number
n = masks_full.max().compute() + 1 # +1 here is for the range later
ncol = n - 1

#Matrix
counts = sparse.lil_matrix((nrow,ncol))

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

    # Genes identified in specifc z slice
    genes = list(spots['gene'])
    genes = np.array([str(x) for x in genes])

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
    print('Creating matrix ')
    for i in range(1,n):
        genes_xprsd = genes[cell_id==i]
        gene, nspots = np.unique(genes_xprsd,return_counts=True)
        for gn in gene:
            r = int(np.where(genes_uq==gn)[0])
            counts[r,i-1] += nspots[gene==gn]
    elapse = datetime.now() - start
    print("Elapsed time {}".format(elapse))


io.mmwrite('count_matrix.mtx',counts)
genes_uq.tofile('rownames.csv', sep = ',')
