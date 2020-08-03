import sys
import datetime
import logging
import os
import shutil
libPathList = ['./lib/Python', './util']
for libPath in libPathList:
    sys.path.insert(0, libPath)
from SetMeUp import SetMeUp
from Calibration import Calibration
from Validation import Validation
from sanityPreCheck import RunPreCheck, RunCalibCheck, RunPreSubmitTest
import accessories as acc
import argparse


# ---- PARSE INPUT ARGS----


parser = argparse.ArgumentParser()
parser.add_argument("--overwrite", action="store_true", help="Overwrite exixting directory")   


# ----- log -----
suffix = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
logfile = 'testing.log'

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

if not RunPreCheck(setupfile).run_all(): sys.exit()
if not RunCalibCheck(setupfile).run_all(): sys.exit()

# create the setup instance
setup = SetMeUp(setupfile)

# remove dir if it exists...

if setup.parent_directory.exists():
    if args.overwrite == True:
        shutil.rmtree(setup.parent_directory, ignore_errors=True)
    else: 
        logger.error("directory already exists. exiting. use overwrite flag to delete")
        sys.exit()
    

# get the current directory 
cwd = os.getcwd()

# Calibrate
calib = Calibration(setupfile)
calib.PrepareCalibration()
calib.AdjustCalibTable()

#logger.info(calib.df)
calib()


logger.info(calib.failed_iterations)
# make sure we are in the parent directory...
os.chdir(cwd) 

# Validate
#---------
valid = Validation(setupfile)
valid.PrepareValidation()
valid.run_validation()
valid.aggregate_results()
