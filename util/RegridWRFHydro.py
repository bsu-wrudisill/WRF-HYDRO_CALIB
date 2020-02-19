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
def regridFiles(setup):
        # find/regrid the appropriate files that are dictated in the setup file
        # gather things from the setup file 
        clbdirc = Path(setup.clbdirc)
        parmdirc = Path(setup.parmdirc)
        start_date = setup.start_date
        end_date = setup.end_date
        dRangeDfmt = pd.date_range(start_date, end_date, freq='h')
        dRange = dRangeDfmt.strftime("%Y-%m-%d_%H:%M:%S") 
        forcings_format ="wrfout_d02_{}"
        forcingList = [forcings_format.format(x) for x in dRange] 
        basin = setup.usgs_code
        print(basin)

        # input (forcing files) directory 
        domain = 'd02'
        wrfout_base_dir = Path("/home/wrudisill/leaf/WRF-Hydro_Forcing/WRFSUB/d02")
        filebasename = 'wrfout*'
        targetfilename = 'wrfinput_d01.nc'

        # target grid directory and 'output' directory 
        output_dir_base = clbdirc
        output_dir_base.mkdir()
        # create the sub directory for the output files if it does not exist yet


        # rename the dimensions to lon / lat; the regridding library reads these by default 
        target_file = xr.open_dataset(parmdirc.joinpath('wrfinput_d01.nc'))
        target_file.rename({'XLONG': 'lon', 'XLAT': 'lat'}, inplace=True)
        target_file['lat'] = target_file['lat'][0,:,:]
        target_file['lon'] = target_file['lon'][0,:,:]


	# ----- Start doing some regridding ---------------- # 
        for date,wrfout_file in zip(dRangeDfmt, forcingList):
                # establish with folder to look in 
                if date.month in [10,11,12]: 
                        wy = date.year + 1
                else:
                        wy = date.year  

                src_folder = wrfout_base_dir.joinpath('wy{}'.format(wy)).joinpath(domain)
                dst_folder = output_dir_base.joinpath("wy{}".format(wy)).joinpath(domain)

                # create the output directory --- no real need to do this every time...
                dst_folder.mkdir(parents=True, exist_ok=True) # permission denied... 
                src = src_folder.joinpath(wrfout_file) 
                print(src)
                if src.is_file():
                        ds = xr.open_dataset(src, engine='netcdf4')
                        ds.rename({'XLONG': 'lon', 'XLAT': 'lat'}, inplace=True)
                        ds['lat'] = ds['lat'][0,:,:]
                        ds['lon'] = ds['lon'][0,:,:]

                        # Create the regridding weight file 
                        regridder = xe.Regridder(ds, target_file, 'bilinear', reuse_weights=True)

                        # Get the list of variables in the list 
                        varlist = [varname for varname in ds.keys() if varname != 'Times']  # huh... this is acceptable syntax

                        # Create a new output file 
                        newds = xr.Dataset(data_vars=None, attrs=ds.attrs)

                        ## loop thru varlist and regrid variables; assign these to the newds
                        for var in varlist:
                                var_regrid = regridder(ds[var])
                                newds[var] = (['Time', 'south_north','west_east'], np.zeros_like(var_regrid))     
                                newds[var] = var_regrid 
                                print('done with...{}'.format(var))
                        outname = str(dst_folder.joinpath(src.name))
                        newds.to_netcdf(outname)         
                        print('wrote ', outname)
                else: 
                       print("error: missing forcing file")
