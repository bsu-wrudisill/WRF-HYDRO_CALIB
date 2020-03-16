import sys
import datetime
import logging
libPathList = ['./lib/Python', './util']
for libPath in libPathList:
    sys.path.insert(0, libPath)
from SetMeUp import SetMeUp
from Calibration import Calibration
from Validation import Validation
from sanityPreCheck import RunPreCheck, RunCalibCheck, RunPreSubmitTest


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

# create the setup instance
setup = SetMeUp(setupfile)

# Calirate
calib = Calibration(setupfile)
calib.PrepareCalibration()

# Validate
valid = Validation(setupfile)
valid.PrepareValidation()
