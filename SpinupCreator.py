import pandas as pd 
import json
#from setupRunDir import SetMeUp
from adjustParameters import *  
import lib
import os 
import time 
from dbLogger import LogParamsToDB 

# lib.SystemCmd('source ./env_nwm_r2.sh') ## this doesn't work 
cwd = os.getcwd()

# Do some checks here that things are reasonable... (maybe?..)
setup = SetMeUp("spinup.json")
setup.CreateRunDir()
setup.GatherObs()
setup.CreateNamelist()
setup.CreateSubmitScript()

# initiate the calibration object
calib = CalibrationMaster(setup)
calib() # do this... i think 

# submit it 
#os.chdir(setup.clbdirc)
#submitCmd = "sbatch submit.sh >> {}".format(setup.catchid)
#lib.SystemCmd(submitCmd)
