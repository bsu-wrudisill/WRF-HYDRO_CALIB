import sys
import os
import sqlite3
from sqlalchemy import create_engine
import pandas as pd 
import glob
import accessories as acc 
import logging
import xarray as xr

# !!! THIS IS HERE FOR NOW..... MAKE ME A STATIC METHOD LATER !!!

def logDataframe(df,table_name,clbdirc):
	#db_connection = kwargs.get('dbcon', 'CALIBRATION.db')
	#
	engine = create_engine('sqlite:///{}/CALIBRATION.db'.format(clbdirc), echo=False)
	df.to_sql(table_name, con = engine, if_exists='append')

def getDischarge(iteration,clbdirc):
	'''
	Description: creates a pandas dataframe from observations in the SQL database
	
	<calibration_directory>/CALIBRATION.db ------> (model_output_i, observations)_dataframe                                         
	'''
	# select data from the table 
	mod_cmd = "SELECT * FROM MODOUT WHERE ITERATIONS = {}".format(iteration)
	mod = pd.read_sql(sql = mod_cmd, con="sqlite:///{}/CALIBRATION.db".format(clbdirc))
	mod['time'] = pd.to_datetime(mod['time']) 
	
	# read obs 	
	obs = pd.read_sql(sql="SELECT * FROM OBSERVATIONS", con="sqlite:///{}/CALIBRATION.db".format(clbdirc))
	obs['time'] = pd.to_datetime(obs['time'])
	obs.drop(columns=['site_no'], inplace=True)
	
	# merge things  
	merged = obs.copy()
	merged['qMod'] = mod['qMod']
	merged.dropna(inplace=True)
	
	# assign index
	merged.set_index(merged.time, inplace=True)
	return merged	

def logModelout(clbdirc, iteration):
	'''
	Description: -Logs obs/modelout to the calibration sql database 
	             -Also finds the correct USGS gauge location 
		     -Ideally this gets run on a compute node, not head  
	
	ModelOutput_i  ------> <calibration_directory>/CALIBRATION.db
	USGS Observations ------^
	'''
	
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
	gauge_loc = acc.GaugeToGrid(chrtFiles[0], lat, lon) # pick the first chrt file 
	logging.info('gauge_loc is ... {}'.format(gauge_loc))
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
	logDataframe(modQdly, 'MODOUT',clbdirc)
	# log the observations only once 
	if iteration == str(0):
		logDataframe(obsQ, 'Observations', clbdirc)
		print('logging the observations to db')	
	# close files ... (not that it does anything...)
	modQfiles.close()
