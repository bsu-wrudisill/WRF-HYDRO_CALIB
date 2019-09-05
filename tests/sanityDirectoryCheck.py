from sanityCheck import  testSetup
import unittest
import xarray as xr
import os 

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

if __name__=='__main__':
	RunPreSubmit
