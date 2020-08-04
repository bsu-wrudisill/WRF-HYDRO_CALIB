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
from dblogger import readSqlDischarge
import accessories as acc
import matplotlib.pyplot as plt
import argparse

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


# create the setup instance
setup = SetMeUp(setupfile)

parser = argparse.ArgumentParser()
parser.add_argument("--overwrite", action="store_true", help="Overwrite exixting directory")   


args = parser.parse_args()

if setup.parent_directory.exists():
    if args.overwrite == True:
        shutil.rmtree(setup.parent_directory, ignore_errors=True)
    else: 
        logger.error("directory already exists. exiting. use overwrite flag to delete")
        sys.exit()

# do checks ...
if not RunPreCheck(setupfile).run_all(): sys.exit()
    
# get the current directory 
cwd = os.getcwd()

# Calibrate
calib = Calibration(setupfile)
calib.PrepareCalibration()
#calib.AdjustCalibTable()

#calib.CreateAnalScript(calib.clbdirc, 'Calibration.db', 0) 
final_file = calib.clbdirc.joinpath(calib.final_chrtfile)

# Run the model once
success, message = acc.ForwardModel(calib.clbdirc,
                           calib.userid,
                           calib.catchid,
                           final_file)

if not success:
    logger.error('model failure')
    logger.info(message)
    sys.exit()

# submit the analysis...
os.chdir(calib.clbdirc)
jobid, err = acc.Submit('submit_analysis.sh', calib.catchid)

# make some plots ...
df = readSqlDischarge(calib.clbdirc.joinpath('Calibration.db'), 0)
plt.plot(df.time, df.qMod, label=str(self.parent_directory.name))
plt.plot(df.time, df.qObs, label='qobs')
plt.legend()
plt.savefig(calib.clbdirc.joinpath('qplot'))
