#!/bin/bash

# This is simply for convenience to run indidvidual scripts. Will be put into a proper workflow one day.
#sbatch -J 'dask' -n 4 --mem-per-cpu=32000 -o dask_test.out -e dask_test.err --wrap="python ./dask_cellpose_test.py"
#sbatch -J 'dask_slurm' -n 1 --mem-per-cpu=12000 -o dask_test_slurm.out -e dask_test_slurm.err --wrap="python ./dask_cellpose_test_slurm.py"
#sbatch -J 'dask_reference' -n 4 --mem-per-cpu=32000 -o dask_test_ref.out -e dask_test_ref.err --wrap="python ./dask_cellpose_test_reference.py"

sbatch -J 'make_single' -n 1 --time=12:00:00 --mem-per-cpu=412000 -o make_single.out -e make_single.err --wrap="python ./make_single_file.py"
sbatch -J 'dask_full_0' -n 1 --time=48:00:00 --mem-per-cpu=128000 -o dask_full_test_0.out -e dask_full_test_0.err --wrap="python ./dask_fulltest.py ../images/mosaic_DAPI_z0.tif"
sbatch -J 'dask_full_1' -n 1 --time=48:00:00 --mem-per-cpu=128000 -o dask_full_test_1.out -e dask_full_test_1.err --wrap="python ./dask_fulltest.py ../images/mosaic_DAPI_z1.tif"
sbatch -J 'dask_full_2' -n 1 --time=48:00:00 --mem-per-cpu=128000 -o dask_full_test_2.out -e dask_full_test_2.err --wrap="python ./dask_fulltest.py ../images/mosaic_DAPI_z2.tif"
sbatch -J 'dask_stitch' -n 2 --time=12:00:00 --mem-per-cpu=512000 -o dask_stitch.out -e dask_stitch.err --wrap="python ./stitch_output.py"
sbatch -J 'dask_full' -n 1 --time=48:00:00 --mem-per-cpu=32000 -o dask_all_stacks.out -e dask_all_stacks.err --wrap="python ./dask_fulltest_stacks.py"
sbatch -J 'count' -n 2 --time=48:00:00 --mem-per-cpu=128000 -o count.out -e count.err --wrap="python ./count_molecules.py"
