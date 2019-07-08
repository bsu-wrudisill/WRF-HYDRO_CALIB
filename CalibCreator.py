import pandas as pd 
import json
#from setupRunDir import SetMeUp
from adjustParameters import *  
import lib
import os 
import time 

lib.SystemCmd('source ./env_nwm_r2.sh')
cwd = os.getcwd()

# Do some checks here that things are reasonable... (maybe?..)
setup = SetMeUp()
setup.CreateRunDir()
setup.GatherObs()
setup.CreateNamelist()
setup.CreateSubmitScript()

# initiate the calibration object
calib = CalibrationMaster(setup)
calib() # do this... i think 

NITERS = 20
for ITER in range(NITERS):
	print('on iteration...{}'.format(ITER))
	# execute the run 
	os.chdir(setup.clbdirc)
	submitCmd = "sbatch submit.sh >> {}".format(setup.catchid)
	lib.SystemCmd(submitCmd)
	
	time.sleep(.5) # wait a second before checking for the job
	lib.WaitForJob(setup.catchid, 'wrudisill')
	os.chdir(cwd)

	print('job finished-- perform analysis/update')	
	calib.ReadQ() # read model/usgs OBS

	print("evaluate... obj fun")
	calib.EvaluateIteration()  # check if the model improved 

	calib.DDS() # generate new parameters 
	calib.UpdateParamFiles()  # write the new parameters 
	lib.CleanUp(setup.clbdirc)
		
	# move the iternal iteration state one forward 
	calib()
	

