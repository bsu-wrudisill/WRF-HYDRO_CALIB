import json
import sys 
import yaml
import pandas as pd 
import unittest 
import os
import xarray as xr
import glob
import numpy as np

#libPath = '../lib/Python/'
#sys.path.insert(0,libPath)
#from adjustParameters import *


'''
Checks that the necessary files, folders, and environments are setup before starting the calibration procedure
The purpose is to be QUICK -- not completely thorough. The goal is to check for common or likely mistakes 
'''

setup = 'spinup.yaml'
if type(setup) == str:
	with open(setup) as y:
		yamlfile = yaml.load(y, Loader=yaml.FullLoader)


class testSetup(unittest.TestCase):
	'''
	test setup class. the tester classes ingest this class 
	'''
	def setUp(self):  # open file 

		# ------ USER INPUT PARAMETERS --------# 
		self.usgs_code = yamlfile['usgs_code']
		self.name_ext = yamlfile['name_ext']
		self.clbdirc = yamlfile['calib_location'] + str(self.usgs_code) + self.name_ext
		
		# restart files 
		self.hydrorestart = yamlfile['hydro_restart_file']  
		self.hrldasrestart = yamlfile['hrldas_restart_file'] 

		# directories and run parameters 
		self.queue = yamlfile['QUEUE']
		self.nodes = yamlfile['NODES']
		self.parmdirc = yamlfile['parameter_location'].format(self.usgs_code)
		self.exedirc = yamlfile['executable_location']
		self.forcdirc = yamlfile['forcing_location']
		self.cwd = os.getcwd()

		# get dates for start, end of spinup,eval period
		self.calib_date = yamlfile['calib_date']
		self.start_date = pd.to_datetime(self.calib_date['start_date'])
		self.end_date = pd.to_datetime(self.calib_date['end_date'])
		# eval period...
		self.eval_date = yamlfile['eval_date']
		self.eval_start_date = pd.to_datetime(self.eval_date['start_date'])
		self.eval_end_date = pd.to_datetime(self.eval_date['end_date'])
		
		# ------- FILES NEEDED TO RUN WRF-HYDRO --------# 
		# depends on version / configuration  
		self.filelist_domain = ["soil_properties.nc", "wrfinput_d01.nc", "Route_Link.nc", "GWBUCKPARM.nc",
		         		"Fulldom_hires.nc", "spatialweights.nc", "geo_em.d01.nc", "hydro2dtbl.nc",
				        "GEOGRID_LDASOUT_Spatial_Metadata.nc"]

		self.filelist_clbdirc = ['wrf_hydro.exe', 'submit.sh', 'namelist.hrldas', 'hydro.namelist', 
					 'HYDRO.TBL', 'MPTABLE.TBL', 'GENPARM.TBL', 'CHANPARM.TBL',
					 'SOILPARM.TBL', 'DOMAIN', 'FORCING']

		# ---- CALIBRATION PARAMETERS ----# 
		self.parameter_table = 'calib_params.tbl'
		self.df = pd.read_csv(self.parameter_table, delimiter=' *, *', engine='python')  # this strips away the whitesapce
		self.df.set_index('parameter', inplace=True)

class RunPreCheck(testSetup):
	'''
	Tests to perform right-off the bat-- ensure that there are no incorrect parameters 
	entered into the .yaml setup file 
	'''
	def test_dates(self):
		#Purpose: test that the date ranges passed into the model config (in the .yaml file) are reasonable
		self.assertGreater(self.end_date, self.start_date, 
				"Specified model start date is before the model end date. Fatal")
		self.assertTrue((self.eval_end_date <= self.end_date) & (self.eval_start_date >= self.eval_start_date),
				"Specified evaluation date is not within the range of the \
						calibration date period. Fatal.")
	def test_filePaths(self):
		self.assertTrue(os.path.exists(self.hydrorestart) or self.hydrorestart == 'None', 
				"hydro restart file {} not found (or it isn't set to None)".format(self.hydrorestart))
	
		self.assertTrue(os.path.exists(self.hrldasrestart) or self.hrldasrestart == 'None', 
				"hrldas restart file {} not found (or it isn't set to None)".format(self.hydrorestart))
		
		self.assertTrue(os.path.exists(self.parmdirc), 
				"parameter directory {} does not exists".format(self.parmdirc))

		self.assertTrue(os.path.exists(self.parmdirc), 
				"parameter directory {} does not exists".format(self.parmdirc))
		
		self.assertTrue(os.path.exists(self.exedirc), 
				"parameter directory {} does not exists".format(self.exedirc))
	
	def test_queue(self):
		queuelist = ['leaf','defq','shortq']
		self.assertTrue(self.queue in queuelist, '{} is not one of {}'.format(self.queue, " ".join(queuelist)))
		if self.queue == 'leaf':
			self.assertLessEqual(self.nodes, 2, 
					'More nodes ({}) requested than the available 2 on leaf'.format(self.nodes))

class RunCalibCheck(testSetup):
	'''
	Check that the calibration parameters are sensible
	'''
	def test_filenames(self):
		#check that the requested filenames correspond with a wrf-hydro file name
		for fname in self.df['file'].unique():
			self.assertTrue(fname in self.filelist_domain, 
					'{} is not a valid filename. check {}'.format(fname, self.parameter_table)
					)
	def test_minmax_range(self):
		# check that the min is l.t max
		for param in self.df.index:
			minValue = self.df.loc[param]['minValue']
			maxValue = self.df.loc[param]['maxValue']
			self.assertLess(minValue, maxValue, 
					'minValue ({}) is greater than maxValue ({}) for {}. Check {}'.format(minValue,maxValue,param, self.parameter_table)
					)
	def test_mult_initval(self):
		multlist = self.df.groupby('factor').groups['mult']
		for param in multlist:
			initval = self.df.loc[param]['ini']  # CHANGE ME ---- I WILL LIKELY RENAME 'ini' IN THE FUTURE
			self.assertGreater(initval, 0,  
					'the ini value must be >0 for multiplicative updates. Check {} in {}'.format(param, self.parameter_table)
					)
	def test_calib_flag(self):
		# check that the min is l.t max
		for param in self.df.index:
			calib_flag = self.df.loc[param]['calib_flag']
			self.assertTrue((calib_flag == 1 or calib_flag == 0).all(),
					'calib_flag must be 0 or 1. {} in {} has a value of {}'.format(param , self.parameter_table, calib_flag)
					)
	

class RunPreSubmitTest(testSetup):
	'''
	Tests to perform prior to submitting the job, but after the run directory has been copied over. 
	Some of them may take a minute and require opening/reading .nc files. 
	'''
	def test_modeldirectory(self):
		#check that all of the correct files exist in the run directory
		self.assertTrue(os.path.exists(self.clbdirc), '{} does not exist'.format(self.clbdirc))
		
		# ensure that the correct files exist in the clbdirc directory 
		withext_filelist_clbdirc = ["{}/{}".format(self.clbdirc, x) for x in self.filelist_clbdirc]
		for fl in withext_filelist_clbdirc:
			self.assertTrue(os.path.exists(fl), "{} not found".format(fl))
		
		# check that the domain files live within clbdirc/DOMAIN
		withext_filelist_clbdirc = ["{}/DOMAIN/{}".format(self.clbdirc, x) for x in self.filelist_domain]
		for fl in withext_filelist_clbdirc:
			self.assertTrue(os.path.exists(fl), "{} not found".format(fl))
	
	'''
	Check that the forcing dimensions match the ldas grid. surprisingly the model WILL NOT crash if there 
	is a mis-match between the two
	'''
	def test_forcing_we_dim(self):
		
		# grab the wrfinput file 
		wrfinputFilename = '{}/DOMAIN/wrfinput_d01.nc'.format(self.clbdirc) 
		wrfinput = xr.open_dataset(wrfinputFilename)
		
		# forcigns
		forcingFilename =  glob.glob('{}/FORCING/*'.format(self.clbdirc))[0] # CHANGE ME -- THIS IS SLOW
		forcing = xr.open_mfdataset(forcingFilename)
		

		# unittests below here 
		self.assertEqual(forcing.dims['west_east'], wrfinput.dims['west_east'], 
					"Forcing/Grid Size Mis-Match.\n \
					{}: | west_east | {}\n\
					{}: | west_east | {}\n".format(forcingFilename, forcing.dims['west_east'], 
						                                        wrfinputFilename, wrfinput.dims['west_east']))
	def test_forcing_sn_dim(self):
		# grab the wrfinput file 
		wrfinputFilename = '{}/DOMAIN/wrfinput_d01.nc'.format(self.clbdirc) 
		wrfinput = xr.open_dataset(wrfinputFilename)
		
		# forcigns
		forcingFilename =  glob.glob('{}/FORCING/*'.format(self.clbdirc))[0] # CHANGE ME -- THIS IS SLOW
		forcing = xr.open_mfdataset(forcingFilename)
		

		# unittests below here 
		self.assertEqual(forcing.dims['south_north'], wrfinput.dims['south_north'], 
					"Forcing/Grid Size Mis-Match.\n \
					{}: | south_north | {}\n\
					{}: | south_north | {}\n".format(forcingFilename, forcing.dims['south_north'], 
						                                        wrfinputFilename, wrfinput.dims['south_north']))
if __name__ == '__main__':
	state=unittest.main(verbosity=2)
	loggiing.info(state)

