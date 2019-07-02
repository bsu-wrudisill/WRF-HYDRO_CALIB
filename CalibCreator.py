import pandas as pd 
import json
#from setupRunDir import SetMeUp
from adjustParameters import *  
import lib
import os 

lib.SystemCmd('source ./env_nwm_r2.sh')

# Do some checks here that things are reasonable... (maybe?..)
setup = SetMeUp()
setup.CreateRunDir()
setup.GatherObs()
setup.CreateNamelist()
setup.CreateSubmitScript()

# initiate the calibration object
calib = CalibrationMaster(setup)

#NITERS = 1 
#for ITER in NITERS:
#	# assign catchfile name 
#	setup.catch_id = "{}/catch_{}".format(setup.clbdirc, setup.usgs_code)
#
#	niters = 2 # read this from a json file or something ....
#	# execute the run 
#	#os.chdir("/scratch/wrudisill/WillCalibHydro/13235000/")
#	submitCmd = "sbatch {}/submit.sh >> {}".format(setup.clbdirc, setup.catch_id)
#	lib.SystemCmd(submitCmd)
#	lib.WaitForJob(setup.catch_id, 'wrudisill')
#	
#	# Now let's update the parameters...
		


# wait for the run to finish

#
