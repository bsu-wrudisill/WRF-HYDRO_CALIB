import pandas as pd 
import json
import os 
import time 
import sys 
import datetime 
import logging
import yaml 

libPathList = ['./lib/Python','tests']
for libPath in libPathList:
	sys.path.insert(0,libPath)

# import lib modules 
import yaml
import ancil
from adjustForcings import adjustForcings 
from CalibCreator import * 
# import testing modules 
import unittest
import testSetup
import sanityPreCheck
from mainSQL import *

# read the setup file --- why not do this? Can't think of a reason not to read it twice... 

## setup the run directory 
setup = SetMeUp('setup.yaml')
setup()
# 
logging.info('creating run directory')
# adjustForcings(setup)	 #OPTIONAL

calib = CalibrationMaster(setup)
for i in range(10):
	calib.OneLoop()
