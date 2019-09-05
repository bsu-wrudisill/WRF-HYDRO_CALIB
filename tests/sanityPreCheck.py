import json
import sys 
import yaml
import pandas as pd 
import unittest 
import os
import xarray as xr
import glob
import numpy as np
from testSetup import testSetup

#libPath = '../lib/Python/'
#sys.path.insert(0,libPath)
#from adjustParameters import *
'''
Checks that the necessary files, folders, and environments are setup before starting the calibration procedure
The purpose is to be QUICK -- not completely thorough. The goal is to check for common or likely mistakes 
'''


class RunPreCheck(testSetup):
	'''
	Tests to perform right-off the bat-- ensure that there are no incorrect parameters 
	entered into the .yaml setup file 
	'''
	def test_existenz(self):
		self.assertFalse(os.path.exists(self.clbdirc), '{} already exists'.format(self.clbdirc))
	
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
	

if __name__ == '__main__':
	unittest.main(verbosity=2)

