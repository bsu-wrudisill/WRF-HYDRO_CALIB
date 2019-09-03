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

import ancil
from adjustForcings import adjustForcings
from sanityCheck import *


def main(setupfile):
	# start the timer 
	cts0 = datetime.datetime.now()
	
	# read the setup file --- why not do this? Can't think of a reason not to read it twice... 
	if type(setupfile) == str:
		with open(setupfile) as y:
			yamlfile = yaml.load(y, Loader=yaml.FullLoader)
	
	# will this run ??? 
	unittest.main(verbosity=2)
	## get parameters from the YAML file 
	#usgs_code = yamlfile['usgs_code']
	#name_ext  = yamlfile['name_ext'] 
	#start_date = yamlfile['calib_date']['start_date']	
	#end_date = yamlfile['calib_date']['end_date']	
	#dds_iter = yamlfile['dds_iter'] 

	## start logging 
	#logging.basicConfig(filename='{}{}.log'.format(usgs_code,name_ext), level=logging.INFO)
	#logging.info('starting WRF Hydro Calibration at {}'.format(cts0.strftime("%Y-%m-%d_%H:%M:%S")))

	## setup the run directory 
	#setup = SetMeUp(setupfile)
	#setup.GatherForcings()
	#
	#logging.info('creating run directory')
	#setup.CreateRunDir()
	## adjustForcings(setup)	 #OPTIONAL
	#setup.CreateNamelist()
	#setup.CreateSubmitScript()
	#setup.GatherObs()
	#calib = CalibrationMaster(setup)
	#
	## loop through the calibration step	
	#cwd = os.getcwd()
	#for i in range(1000):
	#	logging.info('======= ON ITERATION {}====='.format(i))
	#	loopstart=datetime.datetime.now()
	#	# initiate the calibration object
	#	# prepare a job submite script for the analysis step
	#	# we have to create a new one each time... the iteration 
	#	# count is hardcoded into the script (yuck...)
	#	calib.CreateAnalScript()

	#	##----- MODEL SETUP/SUBMIT ----# 
	#	## switch to the calibdirectory 
	#	os.chdir(setup.clbdirc)

	#	## submit the job 
	#	jobid, err = ancil.Submit('submit.sh', setup.catchid)

	#	## sleep 
	#	time.sleep(1) # wait a second before checking for the job

	#	## wait for the job to complete 
	#	ancil.WaitForJob(jobid, 'wrudisill')

	#	## --- MODEL EVALUATION ---- # 
	#	print('submitting analysis job')
	#	jobid, err = ancil.Submit('submit_analysis.sh', setup.catchid)   # THIS STEP LOGS THE MODEL FILES TO THE DB

	#	## wait for the job to complete 
	#	ancil.WaitForJob(jobid, 'wrudisill')

	#	#print("evaluate... obj fun")
	#	obj,improvement = calib.EvaluateIteration()  # check if the model improved 

	#	#os.chdir(cwd)
	#	## log the parameters and obfun to the database
	#	calib.LogParams()     
	#	calib.LogObj() 

	#	## generate new parameters 
	#	calib.DDS()          

	#	## update the parameters 
	#	calib.UpdateParamFiles()  # write the new parameters to files 

	#	## clean up the directory 
	#	ancil.CleanUp(setup.clbdirc)

	#	## move the iternal iteration state one forward 
	#	calib.MoveForward()
	#	
	#	# time at the end of the loop 
	#	loopend = datetime.datetime.now()
	#	dt = (loopstart - loopend).total_seconds()/60.
	#	logging.info('==== ITERATION {} TOOK {} MINUTES TO COMPLETE ======'.format(i, dt))
	#
	## end 		
	#cts1 = datetime.datetime.now()
	#logging.info('finished WRF Hydro Calibration at {}'.format(cts1.strftime("%Y-%m-%d_%H:%M:%S")))

if __name__ == '__main__':
	# pass in the json file that we want
	setupfile = sys.argv[1]
	suite = unittest.TestLoader().loadTestsFromTestCase(MyTests)
	main(setupfile)
