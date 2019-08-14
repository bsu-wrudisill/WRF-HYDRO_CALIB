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
import dbLogger as dbL
from ObjectiveFunctions import KGE, RMSE 

# User options 
#xr.set_options(file_cache_maxsize=1)


# Helper functions   !!! MOVE ME TO THE ANCIL SCRIPT !!! 
def returnItem(dic,x):
	# not sure what i'm supposed to do!
	try:
		return dic[x]
		#return 1
	except KeyError:
		return None

def minDistance(latgrid, longrid, lat,lon):
	# finds the lat/lon that corresponds 
	# to a given gauge point. 
	# returns an integer
	return np.sqrt((latgrid-lat)**2 + (longrid-lon)**2).argmin()

def AddOrMult(factor):
	# create and addition or mult function 
	# based on a string input 
	if factor == 'mult':
		return lambda a,b: a*b
	if factor == 'add':
		return lambda a,b: a+b
	else:
		return None

# !!! THIS IS HERE FOR NOW..... MAKE ME A STATIC METHOD LATER !!!
def GrepSQLstate(iteration,**kwargs):
	# read 	
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
	return merged	

#!!!!!!!!!!!!!!! Classes Below !!!!!!!!!!!!!# 

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
		self.parmdirc = jsonfile['parameter_location'].format(self.usgs_code)
		self.exedirc = jsonfile['executable_location']
		self.forcdirc = jsonfile['forcing_location']
		self.cwd = os.getcwd()
		# create catch id file name 	
		self.catchid = 'catch_{}'.format(self.usgs_code)
	        	
		# get dates for start, end of spinup,eval period
		self.calib_date = jsonfile['calib_date']
		self.start_date = self.calib_date['start_date']
		self.end_date = self.calib_date['end_date']
		self.eval_date = jsonfile['eval_date']	

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
		shutil.copy('./lib/Python/modelEval.py', self.clbdirc) 
		shutil.copy('./lib/Python/viz/PlotQ.py', self.clbdirc) 

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
		ancil.GenericWrite('{}/namelists/submit.TEMPLATE.sh'.format(self.cwd), slurmDic, namelistHolder.format('submit.sh'))



class CalibrationMaster():
	"""
	The "Calibration" class. This requires a "setup" object (created above) to be passed in. 
	This object will 1) submit batch jobs to run WRF-Hydro, 2) submit (and create) the analysis
	job, 3) evaluate objective functions, 4) implement the DDS selection algorithm, and 5) update 
	model parameter files according to the DDS rule, and 5) log items to a SQL database 
	"""
	
	def __init__(self,setup):
		# --- keep track of the number of iterations ---# 
		self.iters = 0 # keep track of the iterations of calib.ation 
		self.setup = setup  # pass the setup class into here...  
		self.paramDir = "{}/DOMAIN".format(self.setup.clbdirc)
		#self.paramDir = '/scratch/wrudisill/WillCaancil.ydro/TestDOMAIN'    #TEMPORARY 
		self.MaxIters = 1e5   # the maximum # of iterations allowed
		self.bestObj = 1e16
		self.objFun = KGE   # !!!!!  make this dynamic later  !!!! 
		self.dbcon = self.setup.clbdirc+'/CALIBRATION.db'
		# create a dataframe w/ the parameter values and links to the right files
		df = pd.read_csv('calib_params.tbl', delimiter=' *, *', engine='python')  # this strips away the whitesapce
		df.set_index('parameter', inplace=True)
		
		# initialize the best value parameter  
		df["bestValue"] = df["ini"] 
		df["currentValue"] = df["ini"]
		df["nextValue"] = None 
		df["onOff"] = df["calib_flag"]  # used for the DDS alg... 
		# assign the df to itself, so we can hold onto it in later fx  
		self.df = df 
	

	def CreateAnalScript(self, **kwargs):
		"""
		Create the job submit script for the analysis step.
		Previous code did the analysis on the head node and 
		ran into memory issues. This way, each file read process 
		(called later) gets started and closed with each iteration,
		so memory leaks in the python netcdf library don't accumulate
		"""
		# remove previous analysis submit script 
		try:
			os.system('rm {}/submit_analysis.sh'.format(self.setup.clbdirc))
		except:
			pass
		namelistHolder = self.setup.clbdirc+'/{}'	
		insert = {"CLBDIRC":self.setup.clbdirc, 
		          "ITERATION":self.iters}
		
		# create the job submit template. 
		ancil.GenericWrite('{}/namelists/submit_analysis.TEMPLATE.sh'.format(self.setup.cwd), insert,  \
				    namelistHolder.format('submit_analysis.sh'))
        

	def UpdateParamFiles(self):
		# update the NC files given the adjustment param
		# Group parameters by the file type   -- tbl or nc
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
				print(self.df.loc[param].factor)
				print(param)
				# returns a function (addition or multiplication) to apply 
				updateFun = AddOrMult(self.df.loc[param].factor)
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
				print('updated--{} in file {}--with value {}'.format(param,ncSingle, updateVal))
			# done looping thru params 
			# save the file now and close  
			UpdateMe.to_netcdf(self.paramDir+'/'+ncSingle, mode='w')
			UpdateMe.close()
		# update the dataframe to reflect that the 'next param' values have been inserted into the current params 
		self.df['currentValue'] = self.df['nextValue']

	def ApplyObjFun(self):
		dbdir = self.setup.clbdirc+'/'
		merged = GrepSQLstate(self.iters, dbdir=dbdir)
		# RMSE 
		# the 'merged' dataframe gets created in the ReadQ step
		#rmse = np.sqrt(np.mean((merged.qMod - merged.qObs)**2))
		#print(rmse)
		obj = self.objFun(merged.qMod, merged.qObs)
		self.obj = obj
		return obj

	def LogLik(self,curiter, maxiter):
		# logliklihood function
		return 1 - np.log(curiter)/np.log(maxiter)

	def LogParams(self):
		# Log Params  
		sql_params = self.df.copy()
		sql_params['Iteration'] = str(self.iters)
		sql_params.drop(columns=['file', 'dims','nextValue'], inplace=True)
		dbL.LogResultsToDB(sql_params, 'PARAMETERS', dbcon=self.dbcon)
	
	def LogObj(self):
		dbL.LogObjToDB(str(self.iters), self.obj, self.improvement, dbcon=self.dbcon)

	def DDS(self):
		# Begin algorithm
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
		obj = self.ApplyObjFun()
		# check the obfun. 
		# if the performance of the last parameter set us better, then update the 
		# calib.data frame 
		improvement = 0  # were the parameters improved upon?
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
		self.improvement = improvement
		self.df['nextValue'] = np.float(0)
		self.df['onOff'] = 0
		return obj,improvement
	
	def MoveForward(self):
		# move the model forward one iteration
		self.iters = self.iters+1

	def __call__(self):
		# This creatres a "call" -- when we do calib.), we 
		# are applying this function that is inside of here
		# this way ... we can call the calib.ation routine N 
		# times and update the calib.method w/ each step 
		pass 	
	

if __name__ == '__main__':
	pass
