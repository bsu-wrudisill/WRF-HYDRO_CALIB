import unittest
import sys
libPathList = ['../lib/Python', '../util', '../']
for libPath in libPathList:
    sys.path.insert(0, libPath)
from SetMeUp import SetMeUp
from Calibration import Calibration
from Validation import Validation
from sanityPreCheck import RunPreCheck, RunCalibCheck, RunPreSubmitTest
import accessories as acc

setupfile = '../setup.yaml'
calibrationfile = '../calib_params.tbl'




class TestSetup(unittest.TestCase):
    def setUp(self):
        self.setmeup_instance = SetMeUp(setupfile)

    def test_basic(self):
        assert self.setmeup_instance != None


class TestCalibration(unittest.TestCase):

    def setUp(self):
        self.calibration_instance = Calibration(setupfile)

    def test_basic(self):
        assert self.calibration_instance != None


class TestValidation(unittest.TestCase):
    def setUp(self):
        self.validation_instance = Validation(setupfile)

    def test_basic(self):
        self.validation_instance != None



if __name__ == '__main__':
    unittest.main()
