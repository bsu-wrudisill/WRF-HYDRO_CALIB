#!/bin/bash
# not actually a makefile... i don't know how to make these

module purge
module load slurm
module load gcc/6.4.0
module load openmpi/gcc-6/1.10.3
module load netcdf/gcc/openmpi/4.6.1 

rm fr.pyf
f2py fastread.f90 -m fastread -h fastread.pyf
f2py -c --fcompiler=gfortran -I$NETCDF/include -L$NETCDF/lib -lnetcdff fastread.pyf fastread.f90

# copy the so file if successful; python cant import weird characters
cp fastread.cpython-37m-x86_64-linux-gnu.so fastread.so
