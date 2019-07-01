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

class SetMeUp:
	def __init__(self):
		# Read in all of the parameter files and hanf 
		# onto them.
		with open("setup.json") as j:
			jsonfile = json.load(j)
			self.indirc = jsonfile[0]['directory_location']
			self.usgs_code = jsonfile[0]['usgs_code']
			self.clbdirc = jsonfile[0]['calib_location'] + self.usgs_code
		with open("calib.json") as cbj:
			jsonfile = json.load(cbj)
			self.queue = jsonfile[0]['QUEUE']
			self.nodes = jsonfile[0]['NODES']
			self.start_date = jsonfile[0]['START_DATE']
			self.end_date   = jsonfile[0]['END_DATE']
		self.catchid = 'catch_{}'.format(self.usgs_code)
	# END INIT 
	def GatherObs(self, **kwargs):
		# run the rscripts to download the USGS observations for the correct 
		# time period and gauge 
		obsFileName='obsStrData.Rdata'
		cmdEmpty = 'Rscript ./lib/R/fetchUSGSobs.R {} {} {} {}/{}'
		os.system(cmdEmpty.format(self.usgs_code, self.start_date, self.end_date, self.clbdirc, obsFileName))	
			
	def CreateRunDir(self, **kwargs):
		"""
		Create run directory for WRF-hdyro calibration runs.
		Copies files from the "directory_location" to the 
		"calib_location" defined in the setup.json file
		"""
		# now, lets create the directory to perform the calibration in
		shutil.copytree(self.indirc+'/DOMAIN/', self.clbdirc+'/DOMAIN')  # this is an annoying command ....

		grabMe = ["wrf_hydro.exe",
			  "SOILPARM.TBL",
			  "CHANPARM.TBL",
			  "GENPARM.TBL",
			  "HYDRO.TBL",
			  "MPTABLE.TBL",
			  "SOILPARM.TBL"]

		# copy files in the 'grab me list' to the run directory 
		[shutil.copy(self.indirc+'/'+item, self.clbdirc) for item in grabMe]

		# link forcings
		os.symlink(self.indirc+'/FORCING', self.clbdirc+'/FORCING')

		# copy namelist (from THIS directory. we modify the namelists here, not in the far-away directory)
		shutil.copy('./namelists/hydro.namelist.TEMPLATE', self.clbdirc+'/hydro.namelist') 
		#shutil.copy('./namelists/namelist.hrldas.TEMPLATE', self.clbdirc) 
		shutil.copy('./env_nwm_r2.sh', self.clbdirc) 

	def CreateNamelist(self, **kwargs):
		# modify the namelist templates that reside in the run dir
		startDate = lib.formatDate(self.start_date)	
		endDate = lib.formatDate(self.end_date)	
		dateRange = startDate - endDate		
		nlistDic = {"YYYY": startDate.year,
			    "MM": startDate.month,
			    "DD": startDate.day,
			    "HH": startDate.hour,
			    "NDAYS": dateRange.days
			    }

		# create the submission script 	
		lib.GenericWrite('./namelists/namelist.hrldas.TEMPLATE', nlistDic, self.clbdirc+'/namelist.hrldas')	
		
	def CreateSubmitScript(self,**kwargs):
		"""
		Read the  the submit script template and modify the correct lines
		to run the desired job
		"""
		namelistHolder = self.clbdirc+'/{}'
		taskX = 16 
		runTime = "02:00:00"   # THIS IS A DEFAULT-- CHANGE ME LATER 
		slurmDic = {"QUEUE":self.queue, 
			    "NODES":self.nodes, 
			    "TASKS":int(self.nodes)*taskX,
			    "RUN_TIME":runTime,
			    "CATCHID":"catch_{}".format(self.usgs_code)
			    }
		# create the submission script 	
		lib.GenericWrite('./namelists/submit.TEMPLATE.sh', slurmDic, namelistHolder.format('submit.sh'))

class CalibrationMaster():
	# class to start and do the entire
	# calibrarion update from start to finish
	# 
	def __init__(self,setup):
		# --- keep track of the number of iterations ---# 
		self.iters = 0 # keep track of the iterations of calibration 
		self.setup = setup  # pass the setup class into here...  
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
		obfun=np.random.rand(1)
		print('OBFUN: {}'.format(obfun))
		return 

	def DDS(self):
		# i, j are the dimensions of the input parameter 
		return np.random.rand()	
	
	def __call__(self):
		# This creatres a "call" -- when we do calib(), we 
		# are applying this function that is inside of here
		# this way ... we can call the calibration routine N 
		# times and update the calib method w/ each step 
		self.iters = self.iters + 1 	
	


if __name__ == '__main__':
	setup = SetMeUp()
	CalibrateMe = CalibrationMaster(setup)
	#CalibrateMe.UpdateParamFiles(1
