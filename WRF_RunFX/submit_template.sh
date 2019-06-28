#!/bin/bash
#SBATCH -J JOBNAME         # Job name
#SBATCH -o log.o%j         # Output and error file name (%j expands to jobID)
#SBATCH -n TASKS                  # Total number of mpi tasks requested
#SBATCH -N NODES                   # Total number of nodes at 16 mpi tasks per-node requested
#SBATCH -p QUEUE                # Queue (partition) -- normal, development, etc.
#SBATCH -t RUNTIME            # Run time (hh:mm:ss) - 2.0 hours
#SBATCH -o .OUT 
#SBATCH -e .ERR
#EXCLUSIVE

#~~~~~~~~ Source Module Files ~~~~~~~~~~~~~~~~~~~~~
echo -e "***** Sourcing (loading) default modules \n"
module purge 
source /home/wrudisill/LEAF/WRF-R2/build/envWRF_3.8.1_R2.sh


#~~~~~~ Create a Log file to store timing info and model params ~~~~~~~~~# 
LogFile=LOGFILE
SECONDS=0
echo "WRF Model starting at time: `date`" >> $LogFile 2>&1

#~~~~~~~~~~~~ RUN EXECUTABLE ~~~~~~~~~~~~~~~~
mpirun ./EXECUTABLE &> CATCHID # !!!!!!  CHANGE ME !!!!!!! 

#~~~~~~~~~~~  Finish  ~~~~~~~~~~~~~~~~~~~~~~~~~~~
DURATION=$SECONDS
echo $DURATION >> $Log_File

#~~~~~~~~~~ Move Output Files ~~~~~~~~~~~~~~~
exit
