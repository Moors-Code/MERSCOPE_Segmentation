#!/bin/bash

# This is simply for convenience to run indidvidual scripts. Will be put into a proper workflow one day.
#sbatch -J 'dask' -n 4 --mem-per-cpu=32000 -o dask_test.out -e dask_test.err --wrap="python ./dask_cellpose_test.py"
#sbatch -J 'dask_slurm' -n 1 --mem-per-cpu=12000 -o dask_test_slurm.out -e dask_test_slurm.err --wrap="python ./dask_cellpose_test_slurm.py"
#sbatch -J 'dask_reference' -n 4 --mem-per-cpu=32000 -o dask_test_ref.out -e dask_test_ref.err --wrap="python ./dask_cellpose_test_reference.py"

sbatch -J 'make_single' -n 1 --time=12:00:00 --mem-per-cpu=412000 -o make_single.out -e make_single.err --wrap="python ./01_make_zarr.py"
sbatch -J 'dask_full' -n 1 --time=48:00:00 --mem-per-cpu=32000 -o dask_all_stacks.out -e dask_all_stacks.err --wrap="python ./02_distributed_segmentation.py"
stdbuf -i0 -o0 -e0 sbatch -J 'count' -n 2 --time=48:00:00 --mem-per-cpu=64000 -o count.out -e count.err --wrap="python ./03_count_molecules.py"
sbatch -J 'prop2' -n 1 --time=120:00:00 --mem-per-cpu=512000 -o prop.out -e prop.err --wrap="python ./04_get_region_props.py"
