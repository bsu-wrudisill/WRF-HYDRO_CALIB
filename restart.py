import shutil
import os 
import time 
import sys 
import datetime 
import logging
import yaml 
import pandas as pd 
from pathlib import Path
libPathList = ['./lib/Python', './util']
for libPath in libPathList:
	sys.path.insert(0,libPath)
from SetMeUp import SetMeUp
from Calibration import Calibration
from Validation import Validation
from sanityPreCheck import RunPreCheck, RunCalibCheck, RunPreSubmitTest
import accessories as acc


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

# this is pretty neat --- we can provide a relative path as argument adn get the full path
directory = Path(sys.argv[1]).resolve()
setupfile = directory.joinpath('setup.yaml')

# create the setup instance
setup = SetMeUp(setupfile)



# -----  main ------ 
calibrationfile = 'calib_params.tbl' 

# start the logging with some handy info
logger.info('starting {}. using {} setup parameters and {}' .format(__name__, setupfile, calibrationfile))
logger.info('Logging to file: {}/{}'.format(os.getcwd(), logfile))

# ---- run 'sanity checks' -----  
#if not RunPreCheck(setupfile).run_all(): sys.exit()
#if not RunCalibCheck(setupfile).run_all(): sys.exit()

# create the setup instance 
setup = SetMeUp(setupfile)

calib = Calibration(setupfile)
calib.AdjustCalibTable()                                                                                                                                            

param_cmd = "SELECT * FROM PARAMETERS"
param = pd.read_sql(sql = param_cmd, con="sqlite:///{}/Calibration.db".format(setup.clbdirc))
lastState = param.loc[param.iteration == param.iteration.iloc[-1]]
lastState.set_index('parameter', inplace=True)
calib.df.update(lastState)
calib.df.nextValue = calib.df.currentValue 
# update the iteration 
calib.iteration = int(lastState.iteration.iloc[0])+1

# now run the calibration 
calib()

## clean up 
logger.info('----- Calibration Complete -----')
logger.info('moving logfile {} to directory {}'.format(logfile, clbdirc))
shutil.move(logfile, setup.clbdirc+'/'+logfile)  # move the log file to the directory 
# make some plots or something ....
#
