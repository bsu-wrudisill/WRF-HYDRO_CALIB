import json
import shutil
import os
import glob 
import lib 
import subprocess
#
#
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

#
#
#
# run if called 
if __name__ == '__main__':
	try:
		os.rmdir("13235000")
	except:
		pass
	setup = SetMeUp()
	setup.CreateRunDir()
	setup.GatherObs()
	setup.CreateNamelist()
	setup.CreateSubmitScript()

