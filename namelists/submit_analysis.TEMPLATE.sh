#!/bin/bash
#SBATCH -J analysis                 # Job name
#SBATCH -o analysis_wh.o%j          # Output and error file name (%j expands to jobID)
#SBATCH -n ANALYSIS_TASKS           # Total number of mpi tasks requested
#SBATCH -N ANALYSIS_NODES           # Total number of nodes at 16 mpi tasks per-node requested
#SBATCH -p ANALYSIS_QUEUE           # Queue (partition) -- normal, development, etc.
#SBATCH -t ANALYSIS_TIME                 # Run time (hh:mm:ss) - 2.0 hours


#~~~~~~~~ Source Module Files ~~~~~~~~~~~~~~~~~~~~~
. /cm/shared/apps/anaconda3/etc/profile.d/conda.sh


#~~~~~~~~~~~~ RUN EXECUTABLE ~~~~~~~~~~~~~~~~
conda activate WRFDev

# the names with the "%" get substituted in by the parent python process.. lol.
iteration=ITERATION_COUNT
directory=DIRECTORY_PATH
database=DATABASE_NAME
libPath=PATH_TO_PYTHON

sys.path.insert(0, libPath)
python -c "

import sys
from pathlib import Path

# Append the path so that the 'dblogger' functions are available
sys.path.insert(0, '$libPath')
import dblogger as dbl

# read and aggregate model output
modQ = dbl.getModelOut()

# append the iteration count to the column
modQ['iteration'] = str($iteration)

# log the data to the sql database
database = Path('$directory').joinpath('Calibration.db')
table_name = 'Calibration'

dbl.logDataframe(modQ, table_name, database)
"

exit
