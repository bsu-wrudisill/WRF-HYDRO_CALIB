#!/bin/bash
#SBATCH -J analysis                 # Job name
#SBATCH -o analysis_wh.o%j         # Output and error file name (%j expands to jobID)
#SBATCH -n 1                   # Total number of mpi tasks requested
#SBATCH -N 1                   # Total number of nodes at 16 mpi tasks per-node requested
#SBATCH -p leaf                   # Queue (partition) -- normal, development, etc.
#SBATCH -t 00:20:00                # Run time (hh:mm:ss) - 2.0 hours


#~~~~~~~~ Source Module Files ~~~~~~~~~~~~~~~~~~~~~
. /cm/shared/apps/anaconda3/etc/profile.d/conda.sh


#~~~~~~~~~~~~ RUN EXECUTABLE ~~~~~~~~~~~~~~~~
conda activate WRFDev

echo 'ITERATION'
python modelEval.py CLBDIRC ITERATION

exit 
