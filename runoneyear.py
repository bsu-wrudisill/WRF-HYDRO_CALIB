#import pandas as pd 
#import json
import shutil
import os 
import time 
import sys 
import datetime 
import logging
libPathList = ['./lib/Python', './util']
for libPath in libPathList:
	sys.path.insert(0,libPath)
from adjustParameters import *
from adjustForcings import adjustForcings
from sanityPreCheck import RunPreCheck, RunCalibCheck, RunPreSubmitTest


# setup the log file --- this will get passed to all of the imported modules!!!

suffix = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
logfile= 'logfile_{}.log'.format(suffix)

file_handler = logging.FileHandler(filename=logfile)
stdout_handler = logging.StreamHandler(sys.stdout)
logging.basicConfig(level=logging.INFO, 
		    format='%(asctime)s %(name)15s %(levelname)-8s %(message)s',
		    datefmt='%a, %d %b %Y %H:%M:%S',
		    handlers=[file_handler, stdout_handler]
		    )
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# -----  main ------ 
setupfile = 'setup.yaml'
calibrationfile = 'calib_params.tbl' 

# start the logging with some handy info
logger.warning('RUN ONE YEAR ONLY')
logger.info('starting {}. using {} setup parameters' .format(__name__, setupfile))
logger.info('Logging to file: {}/{}'.format(os.getcwd(), logfile))

# ---- run 'sanity checks' -----  
if not RunPreCheck(setupfile).run_all(): sys.exit()
#if not RunCalibCheck(setupfile).run_all(): sys.exit()  -- dont check params, we are not calibrating

# create the setup instance 
setup = SetMeUp(setupfile)
setup()   # gather forcing files, create directories, etc.

# BE CAREFUL --- maybe change this later .... make it a namelist option 
if setup.adjust_forcings:
	logging.warning("manualy adjusting precipitation forcings")
	adjustForcings(setup)
#

# check that setup() was successful 
if not RunPreSubmitTest(setupfile).run_all(): sys.exit()
calib = CalibrationMaster(setupfile)
calib.ForwardModel()  # run just one timeperiod 
calib()


## clean up 
logger.info('----- Calibration Complete -----')
logger.info('moving logfile {} to directory {}'.format(logfile, setup.clbdirc))
logfile='logfile_2019-10-29_210310.log'
shutil.move(logfile, setup.clbdirc +'/'+ logfile)  # move the log file to the directory 
# make some plots or something ....

