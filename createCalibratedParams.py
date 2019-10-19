import numpy as np
import pandas as pd
from pathlib import Path
import xarray as xr
import shutil
import sys 
libPathList = ['./lib/Python', './util']
for libPath in libPathList:
	sys.path.insert(0,libPath)
import accessories as acc
import os 

path_to_original_files = Path("/scratch/leaf/share/WRF_hydro_subsets_201810/13185000")
path_to_output_files = Path("/scratch/wrudisill/IDWR_Calibration/seedingfiles/BoiseTwin_13185000/calibrated_domain")
calib_params = 'calib_params.tbl'
database = '/scratch/wrudisill/IDWR_Calibration/Calibration/Boise_twin/13185000_WY2014_CALIB/CALIBRATION.db'


# copy over all of the files from the original directory --- that way it is compelte 
for domainfile in list(path_to_original_files.glob('*')):
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


param = getParameters(database)
param.Iteration = list(map(int, param.Iteration))
performance = getPerformance(database) 
best_row = performance.loc[(performance.Objective == performance['Objective'].min()) & (performance.Improvement ==1)]

best_parameters = param.loc[param.Iteration == int(best_row.Iteration)]
best_parameters.set_index('parameter', inplace=True)


# read the calibration table 
clb = pd.read_csv(calib_params, delimiter=' *, *', engine='python')
clb.set_index('parameter', inplace=True)

grouped = clb.groupby('file')
ncList = grouped.groups.keys()
        
# open each file once and adjust the paremater values 
for ncSingle in ncList:
	UpdateMe = xr.open_dataset(path_to_original_files.joinpath(ncSingle))
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
