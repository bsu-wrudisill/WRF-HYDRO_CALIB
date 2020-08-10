import numpy as np
import pandas as pd
from pathlib import Path
import xarray as xr
import shutil
import sys 
libPathList = ['./lib/Python', './util']
for libPath in libPathList:
	sys.path.insert(0,libPath)
from Calibration import Calibration
import accessories as acc
import os 
import yaml 

####################################################################################
"""
createCalibratedParams.py <path_to_calibration_directory>

Description: This script makes the calibred "domain" files based on the results from
a calibration run. To run it, you must provide the path to the .../Calibration directory,
or wherever contains the "Calibration.db" file. The script will create a directory 
called "calibrated_parameters" and place files there. 

"""
#####################################################################################


directory = Path(sys.argv[1]).resolve()
setupfile = directory.joinpath('setup.yaml')

# create the setup instance
calib = Calibration(setupfile)

#output location
path_to_output_files = Path("./calibrated_parameters")
path_to_output_files.mkdir(exist_ok=True)



# copy over all of the files from the original directory --- that way it is compelte 
for domainfile in list(calib.parmdirc.glob('*')):
	print(domainfile)
	shutil.copy(domainfile, path_to_output_files)


def getParameters(dbcon):
    param_cmd = "SELECT * FROM PARAMETERS WHERE calib_flag = 1"
    param = pd.read_sql(sql = param_cmd, con="sqlite:///{}".format(dbcon))
    return param


def getPerformance(dbcon, **kwargs):
    # only use this when there is just one iteration 
    perf_cmd = "SELECT * FROM CALIBRATION"
    perf = pd.read_sql(sql = perf_cmd, con="sqlite:///{}".format(dbcon))
    return perf 

def returnQmodOnly(dbcon, **kwargs):
    # only use this when there is just one iteration 
    mod_cmd = "SELECT * FROM MODOUT"
    mod = pd.read_sql(sql = mod_cmd, con="sqlite:///{}".format(dbcon))
    mod['time'] = pd.to_datetime(mod['time']) 
    mod['type'] = 'WRF_Hydro V5'
    return mod 


param = getParameters(calib.database)
param.iteration = list(map(int, param.iteration))
performance = getPerformance(calib.database) 
best_row = performance.loc[(performance.objective == performance['objective'].min()) & (performance.improvement ==1)]

best_parameters = param.loc[param.iteration == int(best_row.iteration)]
best_parameters.set_index('parameter', inplace=True)


# read the calibration table 
clb = pd.read_csv('calib_params.tbl', delimiter=' *, *', engine='python')
clb.set_index('parameter', inplace=True)

# I changed the stupid way that the parameters get read in... ugh.
# append the file name to the dataframe...
clb["file"] = None
clb["dims"] = None

with open('calib_params.yaml') as y:
    yamlfile = yaml.load(y, Loader=yaml.FullLoader)

keys = yamlfile['parameters'].keys()

# Group the files with the table ...
for param in clb.index:
    if param in keys:
        clb.at[param, 'file'] = yamlfile['parameters'][param]['file']
        clb.at[param, 'dims'] = yamlfile['parameters'][param]['dimensions']


print(clb)

grouped = clb.groupby('file')
ncList = grouped.groups.keys()
        
# open each file once and adjust the paremater values 
for ncSingle in ncList:
	UpdateMe = xr.open_dataset(calib.parmdirc.joinpath(ncSingle))
	os.remove(path_to_output_files.joinpath(ncSingle)) # this is kinda dumb.... we can't overwrite the file
	# but we only want to deletete the ones that get updated
	for param in grouped.groups[ncSingle]:
		if param in list(best_parameters.index):
			updateFun = acc.AddOrMult(clb.loc[param].factor)
			dims = clb.loc[param].dims
			updateVal = best_parameters.loc[param].currentValue 

			# apply logic to update w/ the correct dims
			if dims == 1:
				UpdateMe[param][:] = updateFun(UpdateMe[param][:], updateVal)
			if dims == 2:
				UpdateMe[param][:,:] = updateFun(UpdateMe[param][:,:], updateVal)
			if dims == 3:
				UpdateMe[param][:,:,:] = updateFun(UpdateMe[param][:,:,:], updateVal)
	UpdateMe.to_netcdf(path_to_output_files.joinpath(ncSingle))
	UpdateMe.close()
#
##output directory 
