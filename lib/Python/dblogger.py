import sys
import os
import sqlite3
from sqlalchemy import create_engine
import pandas as pd 


# !!! THIS IS HERE FOR NOW..... MAKE ME A STATIC METHOD LATER !!!
def getDischarge(iteration,**kwargs):
	'''
	This function reads both observations and model outputs from the 
	sql database
	'''
	#read 	
	dbdir = kwargs.get('dbdir','CALIBRATION.db')
	
	# select data from the table 
	mod_cmd = "SELECT * FROM MODOUT WHERE ITERATIONS = {}".format(iteration)
	mod = pd.read_sql(sql = mod_cmd, con="sqlite:///{}/CALIBRATION.db".format(dbdir))
	mod['time'] = pd.to_datetime(mod['time']) 
	
	# read obs 	
	obs = pd.read_sql(sql="SELECT * FROM OBSERVATIONS", con="sqlite:///{}/CALIBRATION.db".format(dbdir))
	obs['time'] = pd.to_datetime(obs['time'])
	obs.drop(columns=['site_no'], inplace=True)
	
	# merge things  
	merged = obs.copy()
	merged['qMod'] = mod['qMod']
	merged.dropna(inplace=True)
	
	# assign index
	merged.set_index(merged.time, inplace=True)
	return merged	

def logDataframe(df,table_name,**kwargs):
	db_connection = kwargs.get('dbcon', 'CALIBRATION.db')
	#
	engine = create_engine('sqlite:///{}'.format(db_connection), echo=False)
	df.to_sql(table_name, con = engine, if_exists='append')


