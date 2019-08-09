#!/bin/bash

# Executes the calibration routines 
# 1. sources the environment variables
# 2. activates the conda virtual environment needed for the 
#    calibration routine 

. /cm/shared/apps/anaconda3/etc/profile.d/conda.sh

# ---- USER PARAMS ----# 
logfile=CALIBRATE.log 
condaenv=WRFDev


source env_nwm_r2.sh >> $logfile

echo 'activate conda virtual env'
conda activate $condaenv

echo 'execute calib script'

python CalibCreator.py

