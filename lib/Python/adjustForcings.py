''''
Adjust the forcing parameters using a given function...
or something like that ugh...
'''
import numpy as np
import xarray as xr 
import glob 
from pathlib import Path
import os 
import logging 
logger = logging.getLogger(__name__)

def adjustForcings(setup):
	# requires an instance of 'setup' to gather the correct paths 
	# MAKE THIS OPTIONAL-- add ability to pass in the forcing directory
	clbdirc = setup.clbdirc

	logger.info('adjustForcings has been called')
	def ModifyVars(ds):
		# ds is an opened xarray dataset 
		# adjustmetn parameters --- make this more extensible later ---- 
		VAR='RAINNC'
		VALUE = .9
		# adjust 
		ds[VAR][0,:,:] = ds[VAR][0,:,:]*VALUE
		# log 
		logger.info('___________ {} by * {}'.format(VAR,VALUE))
		return ds
	#
	fdir =Path(clbdirc+"/FORCING")
	forcingList = [f for f in fdir.glob('*')]

	## create a directory for the modified forcings
	outdir=Path(clbdirc+"/FORCING_MOD")
	outdir.mkdir()

	## modify the variables of interest
	for f in forcingList:
		logging.info('adjusting forcing file {}'.format(f.name))
		ds = xr.open_dataset(f)
		modDs = ModifyVars(ds)
		modDs.to_netcdf(outdir.joinpath(f.name))


	# now rename the original FORCING directory, 
	# and create a symlik from the FORCING_MOD directory 
	# to FORCING; this is easier than telling the run 
	# scripts later where to look ( i think ...) 
	logger.info('creating symlinks for forcings')
	os.rename(fdir, fdir.parent.joinpath('FORCING_ORIG'))
	os.symlink(outdir, fdir)



