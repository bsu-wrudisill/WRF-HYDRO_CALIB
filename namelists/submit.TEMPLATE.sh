#!/bin/bash
#SBATCH -J wrf_hydro                 # Job name
#SBATCH -o log_wrf_hydro.o%j         # Output and error file name (%j expands to jobID)
#SBATCH -n TASKS                   # Total number of mpi tasks requested
#SBATCH -N NODES                   # Total number of nodes at 16 mpi tasks per-node requested
#SBATCH -p QUEUE                   # Queue (partition) -- normal, development, etc.
#SBATCH -t RUN_TIME                # Run time (hh:mm:ss) - 2.0 hours


#~~~~~~~~ Source Module Files ~~~~~~~~~~~~~~~~~~~~~
module purge 
source ./env_nwm_r2.sh

#~~~~~~~~~~~~ RUN EXECUTABLE ~~~~~~~~~~~~~~~~
mpirun -np TASKS ./wrf_hydro.exe &> CATCHID # !!!!!!  CHANGE ME !!!!!!! 

exit 
