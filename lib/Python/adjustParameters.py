import json
import shutil
import os 
import glob 
import ancil 
import subprocess
import xarray as xr
import pandas as pd
import functools as ft
import netCDF4 as nc
import numpy as np
from dbLogger import LogResultsToDB
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
	def __init__(self,setup,**kwargs):
		# Read in all of the parameter files and hanf 
		# onto them.
		name_ext = kwargs.get('name_ext', '')
		# 
		#!!!! ----- THIS IS WAY TOO VERBOSE ---- DO SOMETHING TO CHANGE -----!!!!
		# 
		if type(setup) == str:
			with open(setup) as j:
				jsonfile = json.load(j)[0]
		if type(setup) == dict:
			jsonfile=setup

		self.usgs_code = jsonfile['usgs_code']
		self.clbdirc = jsonfile['calib_location'] + self.usgs_code + name_ext
		self.hydrorestart = jsonfile['hydro_restart_file']  # NOT CURRENTLY ACTIVE --- CHANGE ME
		self.hrldasrestart = jsonfile['hrldas_restart_file']  # NOT CURRENTLY ACTIVE --- CHANGE ME
		self.queue = jsonfile['QUEUE']
		self.nodes = jsonfile['NODES']
		self.start_date = jsonfile['START_DATE']
		self.end_date   = jsonfile['END_DATE']
		self.parmdirc = jsonfile['parameter_location'].format(self.usgs_code)
		self.exedirc = jsonfile['executable_location']
		self.forcdirc = jsonfile['forcing_location']
		# create catch id file name 	
		self.catchid = 'catch_{}'.format(self.usgs_code)
	
	def GatherObs(self, **kwargs):
		# run the rscripts to download the USGS observations for the correct 
		# time period and gauge 
		obsFileName='obsStrData.csv'
		cmdEmpty = 'Rscript ./lib/R/fetchUSGSobs.R {} {} {} {}/{}'
		os.system(cmdEmpty.format(self.usgs_code, self.start_date, self.end_date, self.clbdirc, obsFileName))	
			
	def CreateRunDir(self, **kwargs):
		"""
		Create run directory for WRF-hdyro calib.ation runs.
		Copies files from the "directory_location" to the 
		"calib.location" defined in the setup.json file
		"""
		
		# now, lets create the directory to perform the calib.ation in
		shutil.copytree(self.parmdirc, self.clbdirc+'/DOMAIN')  # this is an annoying command ....
		
		# create a directory to store the original domain files in. this is just a convenience
		startingParamDir = "{}/ORIG_PARM/".format(self.clbdirc)
		os.mkdir(startingParamDir)

		# make copies of the domain parameters that we will later calib.ate
		caliblist = ['hydro2dtbl.nc',
			     'Route_Link.nc',
			     'soil_properties.nc', 
			     'GWBUCKPARM.nc']			     

		# make copies of these 
		[shutil.copy("{}/{}".format(self.parmdirc,i), startingParamDir+i) for i in caliblist]
	
		# 
		# get these files. ..
		grabMe = ["wrf_hydro.exe",
			  "SOILPARM.TBL",
			  "CHANPARM.TBL",
			  "GENPARM.TBL",
			  "HYDRO.TBL",
			  "MPTABLE.TBL",
			  "SOILPARM.TBL"]

		# copy files in the 'grab me list' to the run directory 
		[shutil.copy(self.exedirc+'/'+item, self.clbdirc) for item in grabMe]

		# link forcings
		os.symlink(self.forcdirc, self.clbdirc+'/FORCING')

		# copy namelist (from THIS directory. we modify the namelists here, not in the far-away directory)
		shutil.copy('./namelists/hydro.namelist.TEMPLATE', self.clbdirc+'/hydro.namelist') 
		shutil.copy('./namelists/namelist.hrldas.TEMPLATE', self.clbdirc) 
		shutil.copy('./env_nwm_r2.sh', self.clbdirc) 

	def CreateNamelist(self, **kwargs):
		# modify the namelist templates that reside in the run dir
		startDate = ancil.formatDate(self.start_date)	
		endDate = ancil.formatDate(self.end_date)	
		dateRange = endDate - startDate		
		nlistDic = {"YYYY": startDate.year,
			    "MM": startDate.month,
			    "DD": startDate.day,
			    "HH": startDate.hour,
			    "NDAYS": dateRange.days,
			    "RESTARTFILENAME": self.hrldasrestart
			    }
		# create the submission script 	
		ancil.GenericWrite('./namelists/namelist.hrldas.TEMPLATE', nlistDic, self.clbdirc+'/namelist.hrldas')	
		# modify the hydro.namelist
		hydDic = {"HYDRO_RSTFILENAME":self.hydrorestart}
		ancil.GenericWrite('./namelists/hydro.namelist.TEMPLATE',hydDic,self.clbdirc+'/hydro.namelist')

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
		ancil.GenericWrite('./namelists/submit.TEMPLATE.sh', slurmDic, namelistHolder.format('submit.sh'))

class CalibrationMaster():
	# class to start and do the entire
	# calib.arion update from start to finish
	# 
	def __init__(self,setup):
		# --- keep track of the number of iterations ---# 
		self.iters = 0 # keep track of the iterations of calib.ation 
		self.setup = setup  # pass the setup class into here...  
		self.paramDir = "{}/DOMAIN".format(self.setup.clbdirc)
		#self.paramDir = '/scratch/wrudisill/WillCaancil.ydro/TestDOMAIN'    #TEMPORARY 
		self.MaxIters = 1e5   # the maximum # of iterations allowed
		self.bestObj = 1e16
		self.objList = [] 

		# create a dataframe w/ the parameter values and links to the right files
		df = pd.read_csv('calib_params.tbl')
		df.set_index('parameter', inplace=True)
		
		# initialize the best value parameter  
		df["bestValue"] = df["ini"] 
		df["nextValue"] = None 
		df["onOff"] = df["calib_flag"]  # used for the DDS alg... 
		# assign the df to itself, so we can hold onto it in later fx  
		self.df = df 
		
		# maybe write to a csv... or not-- ADD ME TO A DATABASE INSTEAD!!! 
		#df.to_csv('calib.ationDataFrame.csv')
		
	
	def UpdateCalibDF(self):
		# update the calib.ation dataframe for each iteration 
		self.df["CALIB_{}".format(self.iters)] = None
		
		# ADD ME TO DATABASE INSTEAD
		#self.df.to_csv("calib.ationDataFrame.csv")
		# done.. 

	def UpdateParamFiles(self):
		# update the NC files given the adjustment param
		# Group parameters by the file type   -- tbl or nc
		if self.iters == 0:
			print("nothing to update-- 1st iteration")
			return
		grouped = self.df.groupby('file')
		# process the netcdf files first 
		ncList = grouped.groups.keys()
		for ncSingle in ncList:
			UpdateMe = xr.open_dataset(self.setup.clbdirc+'/ORIG_PARM/'+ncSingle)
			# remove the file... we overwrite w/ the update 
			os.remove(self.paramDir+'/'+ncSingle)
			
			# loop through the params and update. write files 
			for param in grouped.groups[ncSingle]: 
				# PERFORM THE DDS PARAMETER UPDATE FOR EACH PARAM
				# the different files have differend dimensions 
				dims = self.df.loc[param].dims 
				if dims == 1:
					UpdateMe[param][:] = UpdateMe[param][:]+self.df.nextValue.loc[param]
				if dims == 2:
					UpdateMe[param][:,:] = UpdateMe[param][:,:]+self.df.nextValue.loc[param]
				if dims == 3:
					UpdateMe[param][:,:,:] = UpdateMe[param][:,:,:]+self.df.nextValue.loc[param]
				print('updated--{} in file {}--with value {}'.format(param,ncSingle,self.df.nextValue.loc[param]))
			# done looping thru params 
			# save the file now and close  
			UpdateMe.to_netcdf(self.paramDir+'/'+ncSingle, mode='w')
			UpdateMe.close()

	def ObFun(self):
		# RMSE 
		# the 'merged' dataframe gets created in the ReadQ step
		rmse = np.sqrt(np.mean((self.merged.qMod - self.merged.qObs)**2))
		print(rmse)
		return rmse
	
	def CheckModelOutput(self):
		pass 
	
	def FilterNegative(self,array):
		array[np.where(array<0)] = 0
		return array 

	def ReadQ(self):
		# read model output variables 
		# and usgs observations
		# creates a df, and applies the ObFun
		gauge_loc = 230
		modQfiles = xr.open_mfdataset(glob.glob(self.setup.clbdirc+'/*CHRTOUT_DOMAIN2*'))
		# do some slicing and dicing... 	
		qDf = pd.DataFrame(
				{'qMod':modQfiles['streamflow'][:,gauge_loc].values,
				 'time':modQfiles['time'].values}
				)
		qDf.set_index('time', inplace=True)
		modQdly = pd.DataFrame(qDf.resample('D').sum())

		# read usgs obs 
		obsQ = pd.read_csv(self.setup.clbdirc+'/obsStrData.csv')
		obsQ.drop(columns=['Unnamed: 0', 'POSIXct', "agency_cd"], inplace=True)
		obsQ.rename(index=str, columns={"Date":"time", "obs":"qObs"}, inplace=True)
		obsQ.set_index('time',inplace=True)
		obsQ.index = pd.to_datetime(obsQ.index)
			
		# merge the dataframes...
		merged = obsQ.copy()
		merged['qMod'] = modQdly
		merged.dropna(inplace=True)
		
		# pass off merged to itself 
		self.merged = merged	
		
		# log the output to a database for keeping 
		LogResultsToDB(modQdly, 'Iteration_{}'.format(self.iters))
		if self.iters == 1:
			LogResultsToDB(obsQ, 'Observations')

	def LogLik(self,curiter, maxiter):
		# logliklihood function
		return 1 - np.log(curiter)/np.log(maxiter)

	def DDS(self):
		r= .2
		self.ALG = 'DDS'
		# read the parameter tables 
	   	# this seems like a dumb algorithm.... 
		activeParams = list(self.df.groupby('calib_flag').groups[1])

		# Part 1: Randomly select parameters to update 
		prob = self.LogLik(self.iters+1, self.MaxIters)
		
		for param in activeParams:
			sel = np.random.choice(2, p=[1-prob,prob])
			if sel == 1: 
				self.df.at[param, 'onOff'] = 1
			else:
				self.df.at[param, 'onOff'] = 0 
		# the 'onOff' flag is updated for each iteration... the 
		# calib_flag is not (this flag decides if we want to consider
		# the parameter at all 
		# loop thgouh 
		try:
			selectedParams = list(self.df.groupby('onOff').groups[1])
			deselectedParams = list(self.df.groupby('onOff').groups[0])

		except KeyError:
			print('no parameters were selected during DDS search algorithm')
			return

		# 'active params' just contains those to update now
		for param in selectedParams: 
			J = self.df.loc[param]
			xj_min = J.minValue
			xj_max = J.maxValue
			xj_best = J.bestValue
			print(xj_best)
			sigj = r * (xj_max - xj_min)
			x_new = xj_best + sigj*np.random.randn(1)
			if x_new < xj_min: # if it is less than min, reflect to middle
				x_new = xj_min + (xj_min - x_new)
			if x_new > xj_max:
				x_new = xj_max - (x_new - xj_max)
			self.df.at[param,'nextValue'] = np.float(x_new)
			#self.df.at[param,"CALIB_{}".format(self.iters)] = np.float(x_new)

		for param in deselectedParams:
			J = self.df.loc[param]
			xj_best = J.bestValue
			self.df.at[param,'nextValue'] = np.float(xj_best) # no updating 
			#self.df.at[param,"CALIB_{}".format(self.iters)] = np.float(xj_best)

	def EvaluateIteration(self):
		# check the obfun. 
		# if the performance of the last parameter set us better, then update the 
		# calib.data frame 
		obj = self.ObFun()
		improvement = 0  # were the parameters improved upon?

		# nothing special here -- we just have to pull out hte 
		# list, append to it, then reassign it to 'self' (we can't append to self)
		objList = self.objList
		objList.append(obj)
		self.objList = objList 
	
		
		# check if the new parameters improved the objective function 
		if self.iters == 0:
			print('ON ITER O')
			# this is the first iteration; we have just tested 
			# the 'stock' parameters 
			self.bestObj = obj 
			improvement = 0 	
			# update the active params 
			for param in self.df.groupby('calib_flag').groups[1]:
				self.df.at[param, 'bestValue'] = self.df.loc[param,'ini']
			
			# keep the inactive params at 0 
			try:
				for param in self.df.groupby('calib_flag').groups[0]:
					self.df.at[param, 'bestValue'] = 0.0 
				print('we are on the first iter')
			except KeyError:
				print('all parameters are active')
		else:
			# we ar beyond the first iteration
			# test of the onbjective fx hax improved 
			if obj < self.bestObj:
				# hold onto the best obj 
				self.bestObj = obj
				# the 'next value' is what we just tested; 
				# if it resulted in a better objfun, assign 
				# it to the 'best value' column
				self.df['bestValue'] = self.df['nextValue']
				improvement = 1
				print('obj. improvement')
					
			elif obj >= self.bestObj:
				# the self.bestObj remains the same
				improvement = 0
				print('no obj. improvement')

		# lastly, let's clean the nextvalue and onOff switches 
		# these get updated by the DDS ( or whatever alg. we chose...)
		self.df['nextValue'] = np.float(0)
		self.df['onOff'] = 0
		return obj,improvement

	def __call__(self):
		# This creatres a "call" -- when we do calib.), we 
		# are applying this function that is inside of here
		# this way ... we can call the calib.ation routine N 
		# times and update the calib.method w/ each step 
		self.iters = self.iters + 1 	
		niter = self.iters
#		self.UpdateCaancil.F(n)


if __name__ == '__main__':
	setup = SetMeUp()
	setup.CreateRunDir()
#	calib= calib.ationMaster(setup)
	#calib.ReadQ()
	#calib.EvaluateIteration()
	#calib.DDS()
	#calib.UpdateParamFiles()
