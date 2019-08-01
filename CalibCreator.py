import pandas as pd 
import json
import os 
import time 
import sys 

libPath = './lib/Python'
sys.path.insert(0,libPath)
from adjustParameters import *  
from dbLogger import LogParamsToDB 
import ancil

# lib.SystemCmd('source ./env_nwm_r2.sh') ## this doesn't work 
cwd = os.getcwd()

# Do some checks here that things are reasonable... (maybe?..)
setup = SetMeUp("setup.json")
setup.CreateRunDir()
setup.GatherObs()
setup.CreateNamelist()
setup.CreateSubmitScript()

# initiate the calibration object
calib = CalibrationMaster(setup)
calib() # do this... i think 


objlist = []

NITERS = 1000
for ITER in range(NITERS):
	print('on iteration...{}'.format(ITER))
	# execute the run 
	os.chdir(setup.clbdirc)
	#submitCmd = "sbatch submit.sh >> {}".format(setup.catchid)
	jobid, err = ancil.Submit('submit.sh', setup.catchid)
	time.sleep(1) # wait a second before checking for the job
	ancil.WaitForJob(jobid, 'wrudisill')
	
	# change directories	
	os.chdir(cwd)

	print('job finished-- perform analysis/update')	
	calib.ReadQ() # read model/usgs OBS

	print("evaluate... obj fun")
	obj,improvement = calib.EvaluateIteration()  # check if the model improved 
	
	# log things to the objective fx
	LogParamsToDB(str(ITER), './', obj, improvement)

	calib.DDS() # generate new parameters 
	calib.UpdateParamFiles()  # write the new parameters 
	calib.UpdateCalibDF()
	# concat files 
	#lib.ConcatLDAS(setup.clbdirc, ITER)
	# clean up the directory 
	
	ancil.CleanUp(setup.clbdirc)
	
	# move the iternal iteration state one forward 
	calib()
	
print(objlist)
