import pandas as pd 
import json
#from setupRunDir import SetMeUp
import lib
import os 
import time 
import glob
import sys 
import time 

# insert the lib path into the python path
libPath = './lib/Python'
sys.path.insert(0,libPath)
from dbLogger import LogParamsToDB
from adjustParameters import * 


#done importing 
# lib.SystemCmd('source ./env_nwm_r1.sh') ## this doesn't work 
cwd = os.getcwd()
restart_list = zip(glob.glob('RESTARTS/HYDRO_RST.2010*'), glob.glob('RESTARTS/RESTART.2010*'))

with open("setup.json") as j:
	jsonfile = json.load(j)[0]

cwd = os.getcwd()
# Do some checks here that things are reasonable... (maybe?..)
for  ID,initial_condition in enumerate(restart_list):
	jsonfile["hydro_restart_file"] = cwd+'/'+initial_condition[0]
	jsonfile["hrldas_restart_file"] = cwd+'/'+initial_condition[1]
	# create the setup file
	setup = SetMeUp(jsonfile,name_ext='INIT_COND{}'.format(str(ID)))
	setup.CreateRunDir()
	setup.GatherObs()
	setup.CreateNamelist()
	setup.CreateSubmitScript()
	
	# switch to the calib directory 
	os.chdir(setup.clbdirc)
	submitCmd = "sbatch submit.sh >> {}".format(setup.catchid)
	ancil.SystemCmd(submitCmd)
	# switch back
	os.chdir(cwd)
	time.sleep(2)


# initiate the calibration object
# calib = CalibrationMaster(setup)
# calib() # do this... i think 

# submit it 

