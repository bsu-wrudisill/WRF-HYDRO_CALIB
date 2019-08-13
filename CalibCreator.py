import pandas as pd 
import json
import os 
import time 
import sys 

libPath = './lib/Python'
sys.path.insert(0,libPath)
from adjustParameters import *  
import ancil


# ---- TEMP ---- 
try:
	os.system('rm -rf 13235000/')
	os.system('rm CALIBRATION.db')
except:
	pass

# ------ # ----- # --- 


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

# prepare a job submite script for the analysis step
# we have to create a new one each time... the iteration 
# count is hardcoded into the script (yuck...)
calib.CreateAnalScript()

#----- MODEL SETUP/SUBMIT ----# 
# switch to the calibdirectory 
os.chdir(setup.clbdirc)

# submit the job 
jobid, err = ancil.Submit('submit.sh', setup.catchid)

# sleep 
time.sleep(1) # wait a second before checking for the job

# wait for the job to complete 
ancil.WaitForJob(jobid, 'wrudisill')

# --- MODEL EVALUATION ---- # 
print('submitting analysis job')
jobid, err = ancil.Submit('submit_analysis.sh', setup.catchid)   # THIS STEP LOGS THE MODEL FILES TO THE DB

# wait for the job to complete 
ancil.WaitForJob(jobid, 'wrudisill')

print("evaluate... obj fun")
obj,improvement = calib.EvaluateIteration()  # check if the model improved 

os.chdir(cwd)
# log the parameters and obfun to the database
calib.LogParams()     
calib.LogObj() 

# generate new parameters 
calib.DDS()          

# update the parameters 
calib.UpdateParamFiles()  # write the new parameters to files 

# clean up the directory 
ancil.CleanUp(setup.clbdirc)

# move the iternal iteration state one forward 
calib.MoveForward()
		

#niters= 1000
#failures = 0  

#for iters in range(niters):
#	# allow the model to break no more than three times in a row 
#	while failures < 3:
#		try:
#			SingleIteration(setup,calib)
#			failures = 0 
#		except:
#			# Clean up and try again
#			ancil.CleanUp(setup.clbdirc)
#			failures += 1 
#			time.sleep(5)
## done 
#print(failures)
