import sys
libPathList = ['./lib/Python', './util']
for libPath in libPathList:
    sys.path.insert(0, libPath)
from SetMeUp import SetMeUp
from Calibration import Calibration


setupfile = 'setup.yaml'
calibrationfile = 'calib_params.tbl'

# create the setup instance
setup = SetMeUp(setupfile)
calib = Calibration(setupfile)

calib.AdjustCalibTable()
