import json
import shutil
import os 
import glob 
import subprocess
import xarray as xr
import pandas as pd
import functools as ft
import netCDF4 as nc
import numpy as np
import sys 
from pathlib import Path
import logging 

libPath = '/scratch/wrudisill/WRF-HYDRO_CALIB/lib/Python'  #CHANGE ME TO SOMETHING BETTER !!!!! 
sys.path.insert(0,libPath)
import dbLogger as dbL
import ancil

def ReadQ(clbdirc, iteration):
	# read usgs obs 
	obsQ = pd.read_csv(clbdirc+'/obsStrData.csv')
	obsQ.drop(columns=['Unnamed: 0', 'POSIXct', "agency_cd"], inplace=True)
	obsQ.rename(index=str, columns={"Date":"time", "obs":"qObs"}, inplace=True)
	obsQ.set_index('time',inplace=True)
	obsQ.index = pd.to_datetime(obsQ.index)
	lat = obsQ['lat'].iloc[0]
	lon = obsQ['lon'].iloc[0]
	
	# get the gauge location grid cell 
	chrtFiles = glob.glob(clbdirc+'/*CHRTOUT_DOMAIN2*')
	gauge_loc = ancil.GaugeToGrid(chrtFiles[0], lat, lon) # pick the first chrt file 
	print(gauge_loc)	
	logging.info('gauge_loc is ... {}'.format(gauge_loc))

	# read model output variables 
	# and usgs observations
	# gauge_loc = 29
	modQfiles = xr.open_mfdataset(chrtFiles)
	# do some slicing and dicing... 	
	qDf = pd.DataFrame(
			{'qMod':modQfiles['streamflow'][:,gauge_loc].values,
			 'time':modQfiles['time'].values}
			)
	qDf.set_index('time', inplace=True)
	modQdly = pd.DataFrame(qDf.resample('D').mean())

	
	# log the output to a database for keeping 
	# add iteration count to the df.
	modQdly['Iterations'] = str(iteration)
	dbL.LogResultsToDB(modQdly, 'MODOUT')
	
	# log the observations only once 
	if iteration == str(0):
		dbL.LogResultsToDB(obsQ, 'Observations')
		print('logging the observations to db')	

	# close files ... (not that it does anything...)
	modQfiles.close()

if __name__ == "__main__":
	clbdirc = sys.argv[1]
	iteration = sys.argv[2]
	ReadQ(clbdirc, iteration) 
