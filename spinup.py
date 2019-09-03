import pandas as pd 
import json
import os 
import time 
import sys 
import datetime 
import logging

libPath = './lib/Python'
sys.path.insert(0,libPath)
from adjustParameters import *  
import ancil
from adjustForcings import adjustForcings


def main(setupfile):
	cts0 = datetime.datetime.now()
	# start logging 
	logging.basicConfig(filename='{}.log'.format(cts0.strftime("%s")), level=logging.INFO)
	logging.info('starting WRF Hydro Calibration at {}'.format(cts0.strftime("%Y-%m-%d_%H:%M:%S")))
	cwd = os.getcwd()

	# Do some checks here that things are reasonable... (maybe?..)
	setup = SetMeUp(setupfile)
	setup.GatherForcings()
	
	logging.info('creating run directory')
	setup.CreateRunDir()
	adjustForcings(setup)	 #OPTIONAL
	setup.CreateNamelist()
	setup.CreateSubmitScript()
	setup.GatherObs()
	calib = CalibrationMaster(setup)
	
	# end 		
	cts1 = datetime.datetime.now()
	logging.info('finished WRF Hydro Calibration at {}'.format(cts1.strftime("%Y-%m-%d_%H:%M:%S")))

if __name__ == '__main__':
	# pass in the json file that we want
	setupfile = sys.argv[1]
	main(setupfile)



