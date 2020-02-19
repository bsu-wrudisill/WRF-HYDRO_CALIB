# After the DDS calibration is complete, perform cross-validation statistics
# on the calibrated parameters. Reads in the same namelist as the normal 
# calibration script
#


import shutil
import os 
import time 
import sys 
import datetime 
import logging
import yaml 

libPathList = ['./lib/Python', './util']
for libPath in libPathList:
	sys.path.insert(0,libPath)
from adjustParameters import *
from adjustForcings import adjustForcings
from sanityPreCheck import RunPreCheck, RunCalibCheck, RunPreSubmitTest
from util import RegridWRFHydro as rwh

# setup the log file --- this will get passed to all of the imported modules!!!
suffix = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
logfile= 'POSTPROCESS_logfile_{}.log'.format(suffix)

file_handler = logging.FileHandler(filename=logfile)
stdout_handler = logging.StreamHandler(sys.stdout)
logging.basicConfig(level=logging.INFO, 
		    format='%(asctime)s %(name)14s %(levelname)-8s %(message)s',
		    datefmt='%a, %d %b %Y %H:%M:%S',
		    handlers=[file_handler, stdout_handler]
		    )
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# -----  main ------ 
setupfile = 'setup.yaml'
calibrationfile = 'calib_params.tbl' 

# start the logging with some handy info
logger.info('starting {}. using {} setup parameters and {}' .format(__name__, setupfile, calibrationfile))
logger.info('Logging to file: {}/{}'.format(os.getcwd(), logfile))


# check that the calibration database exists in the correct location; otherwise exit
setup = SetMeUp(setupfile)

