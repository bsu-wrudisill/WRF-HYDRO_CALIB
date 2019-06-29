import pandas as pd 
import json
# check that the files and directories exist are reasonable  
from setupRunDir import SetMeUp

setMeUp()   # create run directories, submit scripts, etc. 
            # it is up for the user to create the spinup files 
	    # and link to them appropriately 
            # download USGS data to evaluate against and place it in the correct place 

masterCalibrate()
	calibrate()  # read in the calibration parameters 
        	     # update namelist to reflect correct time period
	     	     # update submit script 
	     	     # submit the job
	             # wait for the job to complete -- check the job status 
	             # evaluate againt observations...

