#!/bin/bash

# *****************************************************************************
# FILE:     env_nwm_r2.sh
# AUTHOR:   Matt Masarik      (MM) 
# VERSION:  0     2019-01-19   MM    Base version
#
# PURPOSE:  Provides evironment variables and modules required for the 
#           National Water Model (NWM) version of WRF-Hydro, on R2.
#
# USAGE:    source env_nwm_r2.sh
# *****************************************************************************

# unload any auto-loaded modules
module purge

# now load modules
module load shared
module load git/64/2.12.2
module load slurm/17.11.12
module load intel/compiler/64/2018/18.0.5
module load intel/mpi/64/2018/4.274
module load intel/mkl/64/2018/4.274
module load hdf5_18/intel/1.8.18-mpi
module load netcdf/intel/64/4.4.1
module load udunits/intel/64/2.2.24
module load R/3.6.2
module load gcc
# export netCDF env variable
export NETCDF=/cm/shared/apps/netcdf/intel/64/4.4.1

