import json
import shutil
import os
import glob 

# read in the json data from the params file 
with open("setup.json") as j:
	jsonfile = json.load(j)
	indirc = jsonfile[0]['directory_location'] 
	clbdirc = jsonfile[0]['calib_location']+'/DOMAIN/'

# now, lets create the directory to perform the calibration in
shutil.copytree(indirc+'/DOMAIN/', clbdirc)  # this is an annoying command ....

grabMe = ["wrfhydro.exe",
	  "SOILPARM.TBL",
	  "
