import shutil
import os 
import time 
import sys 
import datetime 
import logging
import argparse 

libPathList = ['./lib/Python', './util']
for libPath in libPathList:
	sys.path.insert(0,libPath)

from SetMeUp import SetMeUp
from Calibration import Calibration 
from Validation import Validation
from sanityPreCheck import RunPreCheck, RunCalibCheck, RunPreSubmitTest


# -----  main ------ 
setupfile = 'setup.yaml'
calibrationfile = 'calib_params.tbl' 

# create the setup instance 
setup = SetMeUp(setupfile)

# Calirate 
calib = Calibration(setupfile)
calib.PrepareCalibration()

# Validate 
valid  =  Validation(setupfile)
valid.PrepareValidation()



