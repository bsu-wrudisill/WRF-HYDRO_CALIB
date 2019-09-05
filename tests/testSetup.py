import unittest
import yaml 
import os 
import pandas as pd 

class testSetup(unittest.TestCase):
	'''
	test setup class. the tester classes ingest this class 
	'''
	#def __init__(self, testname, setup):
	#	#setup = 'spinup.yaml'
	#	if type(setup) == str:
	#		with open(setup) as y:
	#			yamlfile = yaml.load(y, Loader=yaml.FullLoader)
	#	yamlfile = yamlfile
	#	super(testSetup, self).__init__(testname)
	def setUp(self):  # open file 
		setup = '/scratch/wrudisill/WRF-HYDRO_CALIB/setup.yaml' ## !!!!!THIS WILL NOT WORK!!!!!!!
		if type(setup) == str:
			with open(setup) as y:
				yamlfile = yaml.load(y, Loader=yaml.FullLoader)
		
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
	

if __name__ == '__main__':
	unittest.main()	
	
	# ---- this is kinda weird...
	#test_loader = unittest.TestLoader()
	#test_names = test_loader.getTestCaseNames(testSetup)
	#suite = unittest.TestSuite()
	#for i in test_names:
	#	suite.addTest(testSetup(i, 'setup.yaml'))
	#result = unittest.TextTestRunner().run(suite)



	
