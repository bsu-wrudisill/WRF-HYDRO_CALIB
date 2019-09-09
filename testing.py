import pandas as pd 
import json
import os 
import time 
import sys 
import datetime 
import logging

libPathList = ['./lib/Python', './util']
for libPath in libPathList:
	sys.path.insert(0,libPath)
from adjustParameters import *
import ancil
from adjustForcings import adjustForcings
#from sanityCheck import *


setupfile = 'setup.yaml'
# setup the run directory 
setup = SetMeUp(setupfile)
setup.GatherForcings()

logging.info('creating run directory')
setup.CreateRunDir()
# adjustForcings(setup)	 #OPTIONAL
setup.CreateNamelist()
setup.CreateSubmitScript()
setup.GatherObs()
calib = CalibrationMaster(setup)
calib.OneLoop()
