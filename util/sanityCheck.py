import json
import sys 
libPath = '../lib/Python/'
sys.path.insert(0,libPath)
from adjustParameters import *
import pandas as pd 

'''
Checks that the necessary files, folders, and environments are setup before starting the calibration procedure
The purpose is to be QUICK -- not completely thorough
'''

# open file 
setup = sys.argv[1]
with open(setup) as j:
	jsonfile = json.load(j)[0]

# get usgs code 
usgs_code = jsonfile['usgs_code']
clbdirc = jsonfile['calib_location'] 

# 
hydrorestart = jsonfile['hydro_restart_file']  
hrldasrestart = jsonfile['hrldas_restart_file'] 

# --- directories and run parameters 
queue = jsonfile['QUEUE']
nodes = jsonfile['NODES']
parmdirc = jsonfile['parameter_location'].format(usgs_code)
exedirc = jsonfile['executable_location']
forcdirc = jsonfile['forcing_location']
cwd = os.getcwd()

# get dates for start, end of spinup,eval period
calib_date = jsonfile['calib_date']
start_date = pd.to_datetime(calib_date['start_date'])
end_date = pd.to_datetime(calib_date['end_date'])

eval_date = jsonfile['eval_date']
eval_start_date = pd.to_datetime(eval_date['start_date'])
eval_end_date = pd.to_datetime(eval_date['end_date'])

def check(condition, error):
	if not condition:
		raise error 

'''
Python philosophy --- assert statements are for things that should never happen!!! 
i.e. not to control program flow 
'''

# CHECK LIST

# Date stuff 
check(end_date > start_date, ValueError("end date is before the start date"))
check(eval_end_date > eval_start_date, ValueError("eval end date is before the eval start date"))
check(((eval_end_date <= end_date) & (eval_start_date >= eval_start_date)), ValueError("eval date range is not within the calib date range"))

# file path checks 
check(os.path.exists(hydrorestart) or hydrorestart == 'None', FileNotFoundError("hydro restart does not exist"))
check(os.path.exists(hrldasrestart) or hrldasrestart == 'None', FileNotFoundError("hrldas restart does not exist"))








