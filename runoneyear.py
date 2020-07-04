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

# ----- log -----
suffix = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
logfile = 'runoneyear_{}.log'.format(suffix)

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

#if not RunPreCheck(setupfile).run_all(): sys.exit()
#if not RunCalibCheck(setupfile).run_all(): sys.exit()

# create the setup instance
setup = SetMeUp(setupfile)

# remove dir if it exists...
if setup.parent_directory.exists():
    shutil.rmtree(setup.parent_directory, ignore_errors=True)

# get the current directory 
cwd = os.getcwd()

# Calibrate
calib = Calibration(setupfile)
calib.PrepareCalibration()


calib.CreateAnalScript(calib.clbdirc, 'Calibration.db', 0) 
final_file = calib.clbdirc.joinpath(calib.final_chrtfile)

# Run the model once
success, message = acc.ForwardModel(calib.clbdirc,
                           calib.userid,
                           calib.catchid,
                           final_file)

# submit the analysis...
os.chdir(calib.clbdirc)
jobid, err = acc.Submit('submit_analysis.sh', calib.catchid)


##logger.info(calib.df)
#calib()

#logger.info(calib.failed_iterations)
# make sure we are in the parent directory...
#os.chdir(cwd) 

# Validate
#---------
##valid = Validation(setupfile)
#valid.PrepareValidation()
#valid.run_validation()
#valid.aggregate_results()
