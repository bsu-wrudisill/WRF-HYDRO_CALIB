import json
import shutil
import os 
import glob 
import lib
import subprocess
import xarray as xr
import pandas as pd
import functools as ft
import netCDF4 as nc
import numpy as np
# read in the parameter adjustment table
# read.json...


# Helper functions 
def returnItem(dic,x):
	try:
		return dic[x]
		#return 1
	except KeyError:
		return None


class CalibrationMaster:
	# class to start and do the entire
	# calibrarion update from start to finish
	# 
	def __init__(self):
		# --- keep track of the number of iterations ---# 
		self.niter = 0
		self.fileDir = '/scratch/wrudisill/WillCalibHydro/TestDOMAIN'    #TEMPORARY 
		# --- read in the parameter tables, and assign some extra stuff ---# 
		soilF   = 'soil_properties.nc'
		hydro2d = 'hydro2dtbl.nc'
		chanF   = 'MPTABLE.TBL'
		fileParamDic = {'dksat': soilF, 
				'bexp': soilF,
				'OV_ROUGH2D':hydro2d,
				'refkdt': soilF, 
				'HLINK': chanF}
		# create a dataframe w/ the parameter values and links to the right files
		df = pd.read_csv('calib_params.tbl')
		df.set_index('parameter', inplace=True)
		df['file'] = [ft.partial(returnItem, fileParamDic)(param) for param in df.index]
		df['type'] = [param.split('.')[1] if param is not None else None for param in df['file']] 
		
		# assign the df to itself, so we can hold onto it in later fx  
		self.df = df 
		df.to_csv('calibrationDataFrame')
	def UpdateParamFiles(self, adjustment):
		# update the NC files given the adjustment param
		# Group parameters by the file type   -- tbl or nc
		grouped = self.df.groupby('type')
		ncFiles = self.df.loc[grouped.groups['nc']]
		tblFiles = self.df.loc[grouped.groups['TBL']]
		# process the netcdf files first 
		
		ncUnique =  list(ncFiles.groupby('file').groups.keys())
		for ncSingle in ncUnique: 
			UpdateMe = xr.open_dataset(self.fileDir+'/'+ncSingle)
			print(UpdateMe)
			for param in list(ncFiles.groupby('file').groups[ncSingle]):
				# PERFORM THE DDS PARAMETER UPDATE FOR EACH PARAM
				UpdateMe[param][:,:,:] = UpdateMe[param][:,:,:] + self.DDS()
				UpdateMe.to_netcdf(self.fileDir+'/'+ncSingle+'updated')
				print('updated --- {}'.format(param))
			UpdateMe.close()
		# now process the .TBL files 
	
	def ObFun(self):
		return 
	
	def DDS(self):
		# i, j are the dimensions of the input parameter 
		return np.random.rand()	


if __name__ == '__main__':
	CalibrateMe = CalibrationMaster()
	CalibrateMe.UpdateParamFiles(1)
