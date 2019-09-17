import sys 
import yaml
import pandas as pd 
import os
import xarray as xr
import glob
from adjustParameters import *
from accessories import passfail 

'''
Checks that the necessary files, folders, and environments are setup before starting the calibration procedure
The purpose is to be QUICK -- not completely thorough. The goal is to check for common or likely mistakes 
'''
import logging
logger = logging.getLogger(__name__)


# Checker Classes 
class RunPreCheck(SetMeUp):
	# checks that the config.yaml file is sensible (paths exist, etc)
	def __init__(self, setup):
		# This is an incredibly handy function all of the self.X attrs. from SetMeUP 
		# instance get put into the "self" of this object
		# same as super(RunPreCheck, self).__init__(setup)
		super(self.__class__, self).__init__(setup)  
	
	def __unittest(self):
		assert 1 == 2, "MESSAGE"
	
	@passfail
	def test_existenz(self):
		assert os.path.exists(self.clbdirc) == False, '{} already exists'.format(self.clbdirc)
	
	@passfail
	def test_dates(self):
		#Purpose: test that the date ranges passed into the model config (in the .yaml file) are reasonable
		assert (self.end_date > self.start_date), "Specified model start date is before the model end date. Fatal"
		assert (self.eval_end_date <= self.end_date) & (self.eval_start_date >= self.eval_start_date), "Specified evaluation date is not \
				within the range of the \calibration date period. Fatal."
	@passfail
	def test_filePaths(self):
		assert os.path.exists(self.hydrorestart) or self.hydrorestart == 'None', "hydro restart file {} not found (or it isn't set to None)".format(self.hydrorestart)
		assert os.path.exists(self.hrldasrestart) or self.hrldasrestart == 'None', "hrldas restart file {} not found (or it isn't set to None)".format(self.hydrorestart)
		assert os.path.exists(self.parmdirc), "parameter directory {} does not exists".format(self.parmdirc)
		assert os.path.exists(self.exedirc), "parameter directory {} does not exists".format(self.exedirc)
			
	@passfail
	def test_queue(self):
		queuelist = ['leaf','defq','shortq', 'gpuq']	
		assert self.queue in queuelist, '{} is not one of {}'.format(self.queue, " ".join(queuelist))
		if self.queue == 'leaf':
			assert self.nodes <= 2, 'More nodes ({}) requested than the available 2 on leaf'.format(self.nodes)
	def run_all(self):
		# emulate behavior of the unittesting module 
		testList = [method for method in dir(self.__class__) if method.startswith('test_')]	
		numTests = len(testList)
		numPassedTests = 0 
		logger.info("========================   {}     ===================".format(self.__class__.__name__))
		for test in testList:
			testFunction = getattr(self.__class__, test)
			success,status = testFunction(self)
			if success: logger.info(status) 
			if not success: logger.error(status)
			numPassedTests += success # zero or one 
		logger.info("{} out of {} tests passed".format(numPassedTests, numTests))
		# return status of test passing  
		if numPassedTests != numTests:
			return False 
		else:	
			return True


class RunCalibCheck(SetMeUp):
	# verify that the calib_params makes sense
	def __init__(self, setup):
		# same as above ... 
		super(self.__class__, self).__init__(setup)
		self.calib = CalibrationMaster(setup) # this is maybe a bad idea
		logger.info(self.calib.df)
	@passfail
	def test_filenames(self):
		#check that the requested filenames correspond with a wrf-hydro file name
		for fname in self.calib.df['file'].unique():
			assert fname in self.calib_files_to_copy, '{} is not a valid filename. check {}'.format(fname, 
								   self.parameter_table)
	
	@passfail
	def test_minmax_range(self):
		# check that the min is l.t max
		for param in self.calib.df.index:
			minValue = self.calib.df.loc[param]['minValue']
			maxValue = self.calib.df.loc[param]['maxValue']
			assert minValue <= maxValue, 'minValue ({}) is greater than maxValue ({}) for {}. \
			 			      Check {}'.format(minValue,maxValue,param, self.parameter_table)
	@passfail			
	def test_mult_initval(self):
		multlist = self.calib.df.groupby('factor').groups['mult']
		for param in multlist:
			initval = self.calib.df.loc[param]['ini']  # CHANGE ME (RENAME 'ini' IN THE FUTURE)
			assert initval ==  1.0, 'the ini value must be >0 for multiplicative updates. \
					       Check {} in {}'.format(param, self.parameter_table)
	@passfail			
	def test_calib_flag(self):
		# check that the min is l.t max
		for param in self.calib.df.index:
			calib_flag = self.calib.df.loc[param]['calib_flag']
			assert (calib_flag == 1 or calib_flag == 0), 'calib_flag must be 0 or 1. {} in {} has a value of  \
					                                    {}'.format(param , self.parameter_table, calib_flag)
	@passfail
	def test_calib_iters(self):
		assert self.calib.max_iters > 1, 'max iters is less than or == to one'
					
	def run_all(self):
		# emulate behavior of the unittesting module 
		testList = [method for method in dir(self.__class__) if method.startswith('test_')]	
		numTests = len(testList)
		numPassedTests = 0 
		logger.info("========================   {}     ===================".format(self.__class__.__name__))
		for test in testList:
			testFunction = getattr(self.__class__, test)
			success,status = testFunction(self)
			if success: logger.info(status)
			if not success: logger.error(status)
			numPassedTests += success # zero or one 
		logger.info("{} out of {} tests passed".format(numPassedTests, numTests))
		if numPassedTests != numTests:
			return False 
		else:	
			return True

class RunPreSubmitTest(SetMeUp):
	'''
	Tests to perform prior to submitting the job, but after the run directory has been copied over. 
	Some of them may take a minute and require opening/reading .nc files. 
	'''
	def __init__(self, setup):
		# same as above ... 
		super(self.__class__, self).__init__(setup)
		# I SHOULD PROBABLY REWRITE THE SETUP STEP TO INCLUDE THIS LIST 		
		self.filelist_domain = ["soil_properties.nc", "wrfinput_d01.nc", "Route_Link.nc", "GWBUCKPARM.nc",
		         		"Fulldom_hires.nc", "spatialweights.nc", "geo_em.d01.nc", "hydro2dtbl.nc",
				        "GEOGRID_LDASOUT_Spatial_Metadata.nc"]
		
		self.filelist_clbdirc = ['wrf_hydro.exe', 'submit.sh', 'namelist.hrldas', 'hydro.namelist', 
					 'HYDRO.TBL', 'MPTABLE.TBL', 'GENPARM.TBL', 'CHANPARM.TBL',
					 'SOILPARM.TBL', 'DOMAIN', 'FORCING']
	
	@passfail
	def test_modeldirectory(self):
		#check that all of the correct files exist in the run directory
		assert os.path.exists(self.clbdirc), '{} does not exist'.format(self.clbdirc)
		
		# ensure that the correct files exist in the clbdirc directory 
		withext_filelist_clbdirc = ["{}/{}".format(self.clbdirc, x) for x in self.filelist_clbdirc]
		for fl in withext_filelist_clbdirc:
			assert os.path.exists(fl), "{} not found".format(fl)
		
		# check that the domain files live within clbdirc/DOMAIN
		withext_filelist_clbdirc = ["{}/DOMAIN/{}".format(self.clbdirc, x) for x in self.filelist_domain]
		for fl in withext_filelist_clbdirc:
			assert os.path.exists(fl), "{} not found".format(fl)
	
	@passfail	
	def test_forcing_we_dim(self):
		'''
		Check that the forcing dimensions match the ldas grid. surprisingly the model WILL NOT crash if there 
		is a mis-match between the two
		'''
		# grab the wrfinput file 
		wrfinputFilename = '{}/DOMAIN/wrfinput_d01.nc'.format(self.clbdirc) 
		wrfinput = xr.open_dataset(wrfinputFilename)
		
		# forcigns
		forcingFilename =  glob.glob('{}/FORCING/*'.format(self.clbdirc))[0] # CHANGE ME -- THIS IS SLOW
		forcing = xr.open_mfdataset(forcingFilename)
		assert forcing.dims['west_east'] == wrfinput.dims['west_east'], "Forcing/Grid Size Mis-Match.\n \
										 {}: | west_east | {}\n\
										 {}: | west_east | {}\n".format(
									       forcingFilename, forcing.dims['west_east'], 
									       wrfinputFilename, wrfinput.dims['west_east'])
	
	@passfail
	def test_forcing_sn_dim(self):
		# same as above 
		# grab the wrfinput file 
		wrfinputFilename = '{}/DOMAIN/wrfinput_d01.nc'.format(self.clbdirc) 
		wrfinput = xr.open_dataset(wrfinputFilename)
		
		# forcigns
		forcingFilename =  glob.glob('{}/FORCING/*'.format(self.clbdirc))[0] # CHANGE ME -- THIS IS SLOW
		forcing = xr.open_mfdataset(forcingFilename)
		assert forcing.dims['south_north'] == wrfinput.dims['south_north'], "Forcing/Grid Size Mis-Match.\n \
										     {}: | south_north | {}\n\
										     {}: | south_north | {}\n".format(
										forcingFilename, forcing.dims['south_north'],  
										wrfinputFilename, wrfinput.dims['south_north'])
	@passfail
	def test_observations(self):
		observation_file = self.clbdirc+'/'+self.obsFileName
		assert os.path.isfile(observation_file), "{} not found".format(observation_file)

	def run_all(self):
		# emulate behavior of the unittesting module 
		testList = [method for method in dir(self.__class__) if method.startswith('test_')]	
		numTests = len(testList)
		numPassedTests = 0 
		logger.info("========================   {}     ===================".format(self.__class__.__name__))
		for test in testList:
			testFunction = getattr(self.__class__, test)
			success,status = testFunction(self)
			if success: logger.info(status) 
			if not success: logger.error(status)
			numPassedTests += success # zero or one 
		logger.info("{} out of {} tests passed".format(numPassedTests, numTests))
		if numPassedTests != numTests:
			return False 
		else:	
			return True


if __name__ == '__main__':
	pass


