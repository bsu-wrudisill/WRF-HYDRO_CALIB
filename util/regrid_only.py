import shutil
import os 
import time 
import sys 
import datetime 
import logging
import argparse 

libPathList = ['./lib/Python', './util']
for libPath in libPathList:
	sys.path.insert(0,libPath)
from adjustParameters import *
from adjustForcings import adjustForcings
from sanityPreCheck import RunPreCheck, RunCalibCheck, RunPreSubmitTest
from util import RegridWRFHydro as rwh


setupfile = 'setup.yaml'
setup = SetMeUp(setupfile)
rwh.regridFiles(setup)
