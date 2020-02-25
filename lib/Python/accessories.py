import os
import sys 
import datetime 
import subprocess
import time 
import glob 
import xarray as xr
import numpy as np
import time 
import traceback
import logging
logger = logging.getLogger(__name__)



def checkFile(pathtofile):
	# assert that a file exists. otherwise return false
	return pathtofile.is_file()



# function decorators 
def passfail(func):
	def wrapped_func(*args, **kwargs):
		try:
			func(*args)
			message = "{} Passed".format(str(func))
			return (True,message)
		except Exception as e:
			trace_string =  traceback.format_exc()	
			error_message = "{} Failed with the following Error: {}\n {}".format(str(func), e, trace_string)
			return (False, error_message)
	return wrapped_func


def timer(function):
	# simple decorator to time a function
	def wrapper(*args,**kwargs):
		t1 = datetime.datetime.now()
		wrapped_function = function(*args,**kwargs)
		t2 = datetime.datetime.now()
		dt = (t2 - t1).total_seconds()/60   # time in minutes
		logging.info('function {} took {} minutes complete'.format(function.__name__, dt))	
		return wrapped_function
	return wrapper

# functions 
def AddOrMult(factor):
	# create and addition or mult function 
	# based on a string input 
	if factor == 'mult':
		return lambda a,b: a*b
	if factor == 'add':
		return lambda a,b: a+b
	else:
		return None

def CleanUp(path):
	# remove files from the run directory 
	cwd = os.getcwd()
	os.chdir(path)
	removeList = ["*LDASOUT*"
		    ,"*CHRTOUT*"
		    ,"*RTOUT*"
		    ,"*LSMOUT*"
		    ,"*diag_hydro*"
		    ,"*HYDRO_RST*"
	            "log_wrf_hydro*"]
	
	logger.info('cleaning up model run directory ({})'.format(path)) 
	for removeMe in removeList:
		cmd = 'rm -rf ./{}'.format(removeMe)
		out,err = SystemCmd(cmd)
		
	# move back to o.g. dir
	os.chdir(cwd)

def GaugeToGrid(chrtout, lat, lon):
	# go from lat-lon pair to the gauge location on the 
	# routing grid   
	ds = xr.open_dataset(chrtout)
	latgrid = ds['latitude'].values
	longrid  = ds['longitude'].values
	
	# finds the lat/lon that corresponds 
	# to a given gauge point. 
	# returns an integer
	return np.sqrt((latgrid-lat)**2 + (longrid-lon)**2).argmin()	

def ConcatLDAS(path,ID):
	# path to output files
	# ID to assign to the output name 
	logger.info('reading LDAS files')	
	ldas = glob.glob(path+'/*LDASOUT_DOMAIN1')
	var_list = ['x', 'y', 'SNLIQ', 'SOIL_T', 'SNOWH', 'ISNOW']
	ds = xr.open_mfdataset(ldas, drop_variables=var_list)
	logger.info('concatenating LDAS files...')
	ds.to_netcdf("{}_LDASFILES.nc".format(ID))
	logger.info('wrote {}_LDASFILES.nc'.format(ID))
	del ds

def SystemCmd(cmd):
	# issue system commands 
	proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True)
	out,err = proc.communicate()
	return out.split(),err

def Submit(subname,catchid):
	cmd = 'sbatch --parsable {}'.format(subname)
	proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True)	
	jobid,err = proc.communicate()
	logger.info("issuing system command {}".format(cmd))
	return jobid.decode("utf-8").rstrip(),err


def WaitForJob(jobid,user):
	# ----NEW METHOD--- PASS IN JOBID 
	still_running = 1     # start with 1 for still running 
	while still_running == 1: # as long as theres a job running, keep looping and checking
		# command
		chid = "squeue -u {} | sed \"s/^ *//\" | cut -d' ' -f1".format(user)   
		# run command and parse output 
		chidout, chiderr = SystemCmd(chid)    
		chidout = [i.decode("utf-8") for i in chidout]
		# convert the id to an integer
		# the length of the list. should be zero or one. one means the job ID is found 
		still_running_list = list(filter(lambda x: x == jobid, chidout))
		
		still_running = len(still_running_list)
		logger.info('jobID {} is still running...'.format(still_running_list))
		logger.info('sleep for 10 seconds')
		time.sleep(10)

def formatDate(dstr):
	if type(dstr) == str:
		return datetime.datetime.strptime(dstr, '%Y-%m-%d')
	if type(dstr) == datetime.datetime:
		return dstr
	

def GenericWrite(readpath,replacedata,writepath):
	# path to file to read 
	# data dictionary to put into file
	# path to the write out file 
	with open(readpath, 'r') as file:
	    filedata = file.read()
	    #  
	    # loop thru dictionary and replace items
	for item in replacedata:
	    filedata = filedata.replace(item, str(replacedata[item])) # make sure it's a string 

	# Write the file out again
	with open(writepath, 'w') as file:
	    file.write(filedata)
	# done 


