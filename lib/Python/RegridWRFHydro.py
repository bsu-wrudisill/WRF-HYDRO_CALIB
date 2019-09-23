import pandas as pd
import xarray as xr
import xesmf as xe
import argparse
import glob 
import datetime
import numpy as np
import sys 
import os 
from pathlib import Path
# funcs

def fileCheck(path):
	#if type(path) != pathlib.PosixPath:
	#	raise TypeError('path must be PosixPath type')
	if not path.exists(): 
		message = path.as_posix() + ' not_found. exiting'
		raise FileNotFoundError(message)
		sys.exit()	

# ----------- input arguments  ---------------------- # 
year = sys.argv[1]
domain = 'd02'

# input (forcing files) directory 
wrfout_base_dir = "/mnt/selway/data/data_03/IPC_HYDRO_FORCE/wrf_hydro_forcing/wy{}/{}"
wrfout_dir = Path(wrfout_base_dir.format(year, domain))
filebasename = 'wrfout*'

# target grid directory and 'output' directory 
target_file_path = Path("/home/wrudisill/leaf/WRF-Hydro/cutouts/13186000/wrfinput_d01.nc")
output_dir_base = Path("/mnt/selway/data/data_03/BOISE_FEATHER")

# check that they exist be fore continuing 
fileCheck(wrfout_dir)
fileCheck(target_file_path)
fileCheck(output_dir_base)

# create the sub directory for the output files if it does not exist yet
output_dir = output_dir_base.joinpath(domain).joinpath(year)
output_dir.mkdir(parents=True, exist_ok=True)

# rename the dimensions to lon / lat; the regridding library reads these by default 
target_file = xr.open_dataset(target_file_path)
target_file.rename({'XLONG': 'lon', 'XLAT': 'lat'}, inplace=True)
target_file['lat'] = target_file['lat'][0,:,:]
target_file['lon'] = target_file['lon'][0,:,:]


# ----- start doing some regridding ---------------- # 
for wrfout_file in wrfout_dir.glob('wrfout*'):
	ds = xr.open_dataset(wrfout_file)
	ds.rename({'XLONG': 'lon', 'XLAT': 'lat'}, inplace=True)
	ds['lat'] = ds['lat'][0,:,:]
	ds['lon'] = ds['lon'][0,:,:]

	# create the regridding weight file 
	regridder = xe.Regridder(ds, target_file, 'bilinear', reuse_weights=True)

	# get the list of variables in the list 
	varlist = [varname for varname in ds.keys() if varname != 'Times']  # huh... this is acceptable syntax

	# create a new output file 
	newds = xr.Dataset(data_vars=None, attrs=ds.attrs)

	# loop thru varlist and regrid variables; assign these to the newds
	for var in varlist:
		var_regrid = regridder(ds[var])
		newds[var] = (['Time', 'south_north','west_east'], np.zeros_like(var_regrid))     
		newds[var] = var_regrid 
		print('done with...{}'.format(var))
		# save the output file 
		newds.to_netcdf(output_dir.joinpath(wrfout_file.name)) 




