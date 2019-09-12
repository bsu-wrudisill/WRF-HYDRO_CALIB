import yaml
import shutil
import os
import sys
import glob 
import accessories as acc
import subprocess
import logging 
import xarray as xr
import pandas as pd
import functools as ft
import netCDF4 as nc
import numpy as np
import dblogger as dbl
from ObjectiveFunctions import KGE, RMSE 
from pathlib import Path
import time 

import logging
logger = logging.getLogger(__name__)


class SetMeUp:
	def __init__(self,setup,**kwargs):
		# Read in all of the parameter files and hanf 
		# onto them.
		#name_ext = kwargs.get('name_ext', '')
		# ------- THIS SYSTEM MIGHT CHANGE LATER ------------# 
		if type(setup) == str:
			with open(setup) as y:
				yamlfile = yaml.load(y, Loader=yaml.FullLoader)
		if type(setup) == dict:
			yamlfile=setup
		self.parameter_table = 'calib_params.tbl'	
		self.setup = setup # name of the setup file. THIS MIGHT CHANGE LATER !!!!	
		self.name_ext = yamlfile['name_ext']
		self.usgs_code = str(yamlfile['usgs_code'])
		self.max_iters = yamlfile['dds_iter']
		self.clbdirc = yamlfile['calib_location'] + self.usgs_code + self.name_ext
		# ---- restart file logic -- a bit ugly  ---- 
		self.hydrorestart = yamlfile['hydro_restart_file']
		self.hrldasrestart = yamlfile['hrldas_restart_file']
		# --- directories and run parameters 
		self.queue = yamlfile['QUEUE']
		self.nodes = yamlfile['NODES']
		self.parmdirc = yamlfile['parameter_location'].format(self.usgs_code)
		self.exedirc = yamlfile['executable_location']
		self.forcdirc = yamlfile['forcing_location']
		self.cwd = os.getcwd()
		# forcing files stuff goes here 
		self.forcings_time_format = "%Y-%m-%d_%H:%M:%S" #!!! FOR WRF -- CHANGE ME LATER !!! 
		self.forcings_format ="wrfout_d02_{}"  # !! FOR WRF -- CHANGE ME LATER !!! 
		self.files_to_copy = ["wrf_hydro.exe",
			      	      "SOILPARM.TBL",
				      "CHANPARM.TBL",
				      "GENPARM.TBL",
				      "HYDRO.TBL",
				      "MPTABLE.TBL",
				       "SOILPARM.TBL"]
		
		self.calib_files_to_copy = ['hydro2dtbl.nc',
			     		    'Route_Link.nc',
			     		    'soil_properties.nc', 
			     		    'GWBUCKPARM.nc']			     
		# create catch id file name 	
		self.catchid = 'catch_{}'.format(self.usgs_code)
		# get dates for start, end of spinup,eval period
		calib_date = yamlfile['calib_date']
		self.start_date = pd.to_datetime(calib_date['start_date'])
		self.end_date = pd.to_datetime(calib_date['end_date'])
		# evaluation period 
		eval_date = yamlfile['eval_date']
		self.eval_start_date = pd.to_datetime(eval_date['start_date'])
		self.eval_end_date = pd.to_datetime(eval_date['end_date'])
		# LOG all of the things 
		self.objfun = KGE
		self.gauge_loc = None


	def GatherForcings(self,**kwargs):
		# find all of the forcings for the specified time period 	
		# this recursively searches all directories 
		# date range of calibration period 
		# ASSUME HOURLY FORCINGS 
		dRange = pd.date_range(self.start_date, self.end_date, freq='H').strftime("%Y-%m-%d_%H:%M:%S") 
		# create list of forcing names 
		forcingList = [self.forcings_format.format(x) for x in dRange] 
		forcingNumber  = len(forcingList)
		# create the copy path 
		linkForcingPath = [] 
		# create a dictionary with name:filepath
		globDic = dict([(p.name, p) for p in Path(self.forcdirc).glob("**/wrfout*")])
		
		# loop through the forcing list, try to find all of the files  
		failureFlag = 0 
		for f in forcingList:
			if f in globDic:  # check if the key is in the dictionary
				linkForcingPath.append(globDic[f])
			else:
				failureFlag += 1  
				logging.info('cannot locate: \n {}'.format(f))
		# check if things failed 
		if failureFlag!=0:
			logger.error('Unable to locate {} of {} forcing files'.format(failureFlag, forcingNumber))
			# raise FileNotFoundError("cannot locate {}... files .... or something")
			sys.exit()
		else:
			logging.info('Found {} required forcing files, continuing'.format(forcingNumber))
			
		# assign the copy list to self
		self.linkForcingPath = linkForcingPath 


	def GatherObs(self, **kwargs):
		# run the rscripts to download the USGS observations for the correct 
		# time period and gauge 
		obsFileName='obsStrData.csv'
		cmdEmpty = 'Rscript ./lib/R/fetchUSGSobs.R {} {} {} {}/{}'
		#
		startString = str(self.start_date.strftime("%Y-%m-%d"))
		endString = str(self.end_date.strftime("%Y-%m-%d"))
		try:
			os.system(cmdEmpty.format(self.usgs_code, startString, endString, self.clbdirc, obsFileName))	
		except:
			logging.error('unable to execute command {}'.format(cmdEmpty))
			# if it is a calibrate command ... then maybe sys.exit. since we need this  


	def CreateRunDir(self, **kwargs):
		"""
		Create run directory for WRF-hdyro calib.ation runs.
		Copies files from the "directory_location" to the 
		"calib.location" defined in the setup.yaml file
		"""
		
		# now, lets create the directory to perform the calib.ation in
		shutil.copytree(self.parmdirc, self.clbdirc+'/DOMAIN')  # this is an annoying command ....
		
		# create a directory to store the original domain files in. this is just a convenience
		startingParamDir = "{}/ORIG_PARM/".format(self.clbdirc)
		os.mkdir(startingParamDir)

		# make copies of the domain parameters that we will later calib.ate
		[shutil.copy("{}/{}".format(self.parmdirc,i), startingParamDir+i) for i in self.calib_files_to_copy]
	
		# copy files in the 'files_to_copy list' to the run directory 
		[shutil.copy(self.exedirc+'/'+item, self.clbdirc) for item in self.files_to_copy]
		
		# link forcings
		os.mkdir(self.clbdirc+'/FORCING')
		for source in self.linkForcingPath:
			os.symlink(str(source), self.clbdirc+'/FORCING/{}'.format(source.name))

		# copy namelist (from THIS directory. we modify the namelists here, not in the far-away directory)
		shutil.copy('./namelists/hydro.namelist.TEMPLATE', self.clbdirc+'/hydro.namelist') 
		shutil.copy('./namelists/namelist.hrldas.TEMPLATE', self.clbdirc) 
		shutil.copy('./env_nwm_r2.sh', self.clbdirc) 
		shutil.copy('./{}'.format(self.setup), self.clbdirc) 
		
		# why am i copying model eval
		shutil.copy('./lib/Python/modelEval.py', self.clbdirc) 
		shutil.copy('./lib/Python/viz/PlotQ.py', self.clbdirc) 
		
		# log success
		logging.info('created run directory {}'.format(self.clbdirc))

	def CreateNamelist(self, **kwargs):
		if self.hrldasrestart == "None":
			hrldasrestart = "!RESTART_FILENAME_REQUESTED"
		else:
			hrldasrestart = "RESTART_FILENAME_REQUESTED = \"{}\"".format(self.hrldasrestart)

		if self.hydrorestart == "None":
			hydrorestart = "!RESTART_FILE"
		else:
			hydrorestart = "RESTART_FILE = \"{}\"".format(self.hydrorestart)
		
		# modify the namelist templates that reside in the run dir
		startDate = self.start_date
		endDate = self.end_date	
		dateRange = endDate - startDate		
		nlistDic = {"YYYY": startDate.year,
			    "MM": startDate.month,
			    "DD": startDate.day,
			    "HH": startDate.hour,
			    "NDAYS": dateRange.days,
			    "RESTART_FILENAME_REQUESTED": hrldasrestart
			    }
		#modify namelist.hrldas
		acc.GenericWrite('./namelists/namelist.hrldas.TEMPLATE', nlistDic, self.clbdirc+'/namelist.hrldas')	
		
		# modify the hydro.namelist
		hydDic = {"RESTART_FILE":hydrorestart}
		acc.GenericWrite('./namelists/hydro.namelist.TEMPLATE',hydDic,self.clbdirc+'/hydro.namelist')
		# log 
		logging.info('created namelist files')
	
	def CreateSubmitScript(self,**kwargs):
		"""
		Read the  the submit script template and modify the correct lines
		to run the desired job
		"""
		namelistHolder = self.clbdirc+'/{}'
		taskX = 16 
		runTime = "03:00:00"   # THIS IS A DEFAULT-- CHANGE ME LATER 
		slurmDic = {"QUEUE":self.queue, 
			    "NODES":self.nodes, 
			    "TASKS":int(self.nodes)*taskX,
			    "RUN_TIME":runTime,
			    "CATCHID":"catch_{}".format(self.usgs_code)
			    }
		# create the submission script 	
		acc.GenericWrite('{}/namelists/submit.TEMPLATE.sh'.format(self.cwd), slurmDic, namelistHolder.format('submit.sh'))
		logging.info('created job submission script')

	def __call__(self):
		loggin.info("Tests Successful...presumably")
		logging.info("Calibrating to USGS code {}".format(self.usgs_code))
		logging.info("ParentDirectory: {}".format(self.clbdirc))
		logging.info("StartDate: {}".format(self.start_date))
		logging.info("EndDate: {} ".format(self.end_date))
		
		# do the things in the right order -- 
		# find forcings, create directory, write namelist, write submit script, gather observations 
		self.GatherForcings()
		self.CreateRunDir()
		self.CreateNamelist()
		self.CreateSubmitScript()
		self.GatherObs()



class CalibrationMaster(SetMeUp):
	"""
	The "Calibration" class. This requires a "setup" object (created above) to be passed in. 
	This object will 1) submit batch jobs to run WRF-Hydro, 2) submit (and create) the analysis
	job, 3) evaluate objective functions, 4) implement the DDS selection algorithm, and 5) update 
	model parameter files according to the DDS rule, and 5) log items to a SQL database 
	"""
	
	def __init__(self, setup):
		# get all of the methods from SetMeUp... 
		super(self.__class__, self).__init__(setup)
		self.iters = 0 # keep track of the iterations of calib.ation 
		self.bestObj = 1e16
		self.objFun = KGE   # !!!!!  make this dynamic later  !!!! 
		self.dbcon = self.clbdirc+'/CALIBRATION.db'
		self.paramDir = "{}/DOMAIN".format(self.clbdirc)

		# create a dataframe w/ the parameter values and links to the right files
		df = pd.read_csv(self.parameter_table, delimiter=' *, *', engine='python')  # this strips away the whitesapce
		df.set_index('parameter', inplace=True)
		
		# initialize the best value parameter  
		df["bestValue"] = df["ini"] 
		df["currentValue"] = df["ini"]
		df["nextValue"] = None 
		df["onOff"] = df["calib_flag"]  # used for the DDS alg... 
		# assign the df to itself, so we can hold onto it in later fx  
		self.df = df 
		
		# log lots of things 
		#logging.info('Initialized CalibrationMaster')
		#logging.info('Using calib_params.tbl')
		#logging.info('Objective function: {}'.format(str(self.objFun)))
		#logging.info('Maximum iters: {}'.format(self.max_iters))
		

	def CreateAnalScript(self, **kwargs):
		"""
		Create the job submit script for the analysis step.
		Previous code did the analysis on the head node and 
		ran into memory issues. This way, each file read process 
		(called later) gets started and closed with each iteration,
		so memory leaks in the python netcdf library don't accumulate
		"""
		# remove previous analysis submit script 
		submit_analysis = 'rm {}/submit_analysis.sh'.format(self.clbdirc)
		if os.path.isfile(submit_analysis):
			os.remove(submit_analysis)
			logging.info('removed previous analysis job submit script {}'.format(submit_analysis))
		
		namelistHolder = self.clbdirc+'/{}'	
		insert = {"CLBDIRC":self.clbdirc, 
		          "ITERATION":self.iters} 
		# 	
		# create the job submit template. 
		acc.GenericWrite('{}/namelists/submit_analysis.TEMPLATE.sh'.format(self.cwd), insert,  \
				    namelistHolder.format('submit_analysis.sh'))
	
	# this is nothing more than a bookkeeping step to make this a static method 
	# no different than letting it live outside of this class 
	def LogParameters(self):
		# Log Params  
		sql_params = self.df.copy()
		sql_params['Iteration'] = str(self.iters)
		sql_params.drop(columns=['file', 'dims','nextValue'], inplace=True)
		dbl.logDataframe(sql_params, 'PARAMETERS', self.clbdirc)
	
	
	def LogPerformance(self):
		paramDic = {'Iteration': [str(self.iters)], 
			    'Objective':  [self.obj], 
			    'Improvement': [self.improvement],
			    'Function': [str(self.objfun)]}   # CHANGE ME! make __repr__ instead. obfun needs to be class thoguh
		pdf = pd.DataFrame(paramDic)
		pdf.set_index('Iteration', inplace=True)
		dbl.logDataframe(pdf, 'CALIBRATION', self.clbdirc)
	'''
	Function: EvaluateIteration
		1.a. apply objective function, evaluating perfomance of model relative to the observations
		1.b  determine if the model improved or not, assignt improvement flag to 0 or 1 
		1.c  set the 'next value' to the initial value
	'''
	
	def EvaluateIteration(self):
		merged = dbl.getDischarge(self.iters, self.clbdirc)
		# only evaluate during the evaluation period
		eval_period = merged.loc[self.eval_start_date : self.eval_end_date]
		# compute the objective function
		obj = self.objFun(eval_period.qMod, eval_period.qObs)
		self.obj = obj

		# if the performance of the last parameter set us better, then update the 
		# calib.data frame 
		improvement = 0  
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
					self.df.at[param, 'bestValue'] = self.df.loc[param, 'ini'] 
				logger.info('we are on the first iter')
			except KeyError:
				logger.info('all parameters are active')
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
				logger.info('the objective fx improved on iteration {}'.format(self.iters))
					
			elif obj >= self.bestObj:
				# the self.bestObj remains the same
				improvement = 0
				logger.info('no obj. improvement on iteration {}'.format(self.iters))
		# lastly, let's clean the nextvalue and onOff switches 
		# these get updated by the DDS ( or whatever alg. we chose...)
		self.improvement = improvement
		self.df['nextValue'] = self.df['ini'] 
		return obj,improvement
	
	def DDS(self):
		"""
		The DDS parameter selection algorithm, adapted from Tolson et al.
		"Greedy" algorithm -- holds onto best parameter estimate and updates
		from there by adding random gaussian noise with a specified standard deviation
		and mean of zero. 
		
		This function established the correct parameter values
		and saves them to a pandas dataframe. 'self.UpdateParamFiles'
		then updates the parameter values in the correct files. 
		"""

		# Begin algorithm
		r= 0.2    # there is a justification for this value... can't recall. 
		self.ALG = 'DDS'
		# read the parameter tables 
	   	# this seems like a dumb algorithm.... 
		activeParams = list(self.df.groupby('calib_flag').groups[1])
		# Part 1: Randomly select parameters to update 
		
		
		#def LogLik(self,curiter, maxiter):
		# logliklihood function
		#return 1 - np.log(curiter)/np.log(maxiter)
		
		prob = 1 - np.log(self.iters+1) / np.log(self.max_iters)
		#print(prob)	
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
			logging.warning('no parameters were selected during DDS search algorithm')
			return

		# 'active params' just contains those to update now
		for param in selectedParams: 
			J = self.df.loc[param]
			xj_min = J.minValue
			xj_max = J.maxValue
			xj_best = J.bestValue
			sigj = r * (xj_max - xj_min)
			x_new = xj_best + sigj*np.random.randn(1)
			
			if x_new < xj_min: # if it is less than min, reflect to middle
				x_new = xj_min + (xj_min - x_new)
			
			if x_new > xj_max: # if xnew is greater than the max, reflect to middle
				x_new = xj_max - (x_new - xj_max)
			
			# assign the parameter to the 'next value' 
			self.df.at[param,'nextValue'] = np.float(x_new)
		
		for param in deselectedParams:
			J = self.df.loc[param]
			xj_best = J.bestValue
			self.df.at[param,'nextValue'] = np.float(xj_best) # no updating 
			#self.df.at[param,"CALIB_{}".format(self.iters)] = np.float(xj_best)
			
		logging.info('Performed DDS update for iteration {}'.format(self.iters))

	def UpdateParamFiles(self):
		# update the NC files given the adjustment param
		# Group parameters by the file type   -- tbl or nc
		grouped = self.df.groupby('file')
		# process the netcdf files first 
		ncList = grouped.groups.keys()
		for ncSingle in ncList:
			UpdateMe = xr.open_dataset(self.clbdirc+'/ORIG_PARM/'+ncSingle)
			# remove the file... we overwrite w/ the update 
			os.remove(self.paramDir+'/'+ncSingle)
			# loop through the params and update. write files 
			for param in grouped.groups[ncSingle]: 
				# returns a function (addition or multiplication) to apply 
				updateFun = acc.AddOrMult(self.df.loc[param].factor)
				# get the dims of the parameter
				dims = self.df.loc[param].dims 
				# create the value for updating --- this will include the 'ini' value 
				updateVal = self.df.nextValue.loc[param] + self.df.ini.loc[param]
				
				# apply logic to update w/ the correct dims 
				if dims == 1:
					UpdateMe[param][:] = updateFun(UpdateMe[param][:], updateVal) 
				if dims == 2:
					UpdateMe[param][:,:] = updateFun(UpdateMe[param][:,:], updateVal) 
				if dims == 3:
					UpdateMe[param][:,:,:] = updateFun(UpdateMe[param][:,:,:], updateVal) 
				# log info
				logging.info('updated--{} in file {}--with value {}'.format(param,ncSingle, updateVal))
			# done looping thru params 
			# save the file now and close  
			UpdateMe.to_netcdf(self.paramDir+'/'+ncSingle, mode='w')
			UpdateMe.close()
		
		# update the dataframe to reflect that the 'next param' values have been inserted into the current params 
		self.df['currentValue'] = self.df['nextValue']

	
	def MoveForward(self):
		# move the model forward one iteration
		self.iters = self.iters+1


	def OneLoop(self):
		logger.info('Calling OneLoop for iteration {}'.format(self.iters))
		# create analysis script 
		self.CreateAnalScript()
		
		# switch to the selfdirectory 
		os.chdir(self.clbdirc)

		# submit the job 
		jobid, err = acc.Submit('submit.sh', self.catchid)

		# sleep 
		time.sleep(1) # wait a second before checking for the job

		# wait for the job to complete 
		acc.WaitForJob(jobid, 'wrudisill')

		# --- MODEL EVALUATION ---- # 
		jobid, err = acc.Submit('submit_analysis.sh', self.catchid)   # THIS STEP LOGS THE MODEL FILES TO THE DB

		## wait for the job to complete 
		acc.WaitForJob(jobid, 'wrudisill')
			
		obj,improvement = self.EvaluateIteration()  # check if the model improved 

		#os.chdir(cwd)
		# log the parameters and obfun to the database
		self.LogParameters()     
		self.LogPerformance() 
		# generate new parameters 
		self.DDS()          

		# update the parameters 
		self.UpdateParamFiles()  # write the new parameters to files 

		# clean up the directory 
		acc.CleanUp(self.clbdirc)

		# move the iternal iteration state one forward 
		self.MoveForward()
	
	def __call__(self):
		# This creatres a "call" -- when we do calib.), we 
		# are applying this function that is inside of here
		# this way ... we can call the calib.ation routine N 
		# times and update the calib.method w/ each step 
		for i in range(self.max_iters):
			self.OneLoop()
		

if __name__ == '__main__':
	pass
