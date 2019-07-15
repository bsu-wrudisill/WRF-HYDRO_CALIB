import os,sys
import datetime 
from collections import OrderedDict
import subprocess
import time 
import glob 
import xarray as xr
#
#   
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
	            ,"log_wrf_hydro*"
		    , "catch_*"]

	print('cleaning up...')
	for removeMe in removeList:
		for singleFile in glob.glob(removeMe):
			try:
				os.remove(singleFile)
			except:
				pass
	# move back to o.g. dir
	os.chdir(cwd)

def ConcatLDAS(path,ID):
	# path to output files
	# ID to assign to the output name 
	print('reading LDAS files')	
	ldas = glob.glob(path+'/*LDASOUT_DOMAIN1')
	var_list = ['x', 'y', 'SNLIQ', 'SOIL_T', 'SNOWH', 'ISNOW']
	ds = xr.open_mfdataset(ldas, drop_variables=var_list)
	print('concatenating LDAS files...')
	ds.to_netcdf("{}_LDASFILES.nc".format(ID))
	print('wrote {}_LDASFILES.nc'.format(ID))
	del ds

def SystemCmd(cmd):
	# issue system commands 
	proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True)
	out,err = proc.communicate()
	return out.split(),err

def WaitForJob(catch,user):
	# Gather the Job id from the catch file
	# (the catchid gets updated with eath iteration of real/wrf)
	gid = "grep \"\" {} | cut -d' ' -f4".format(catch)    
	gidout,giderr = SystemCmd(gid)    
	print(gidout)

	# IF STDERROR NULL (NO ERRORS) THEN CONTINUE
	jobid = gidout[0]           # assign jobid
	print("jobid found {}".format(jobid))

	still_running = 1     # start with 1 for still running 
	while still_running == 1: # as long as theres a job running, keep looping and checking
		# command
		chid = "squeue -u {} | sed \"s/^ *//\" | cut -d' ' -f1".format(user)   
		# run command and parse output 
		chidout, chiderr = SystemCmd(chid)    
		# the length of the list. should be zero or one. one means the job ID is found 
		still_running_list = list(filter(lambda x: x == jobid, chidout))
		still_running = len(still_running_list)
		time.sleep(5)
		print('still running...')
	pass 

def formatDate(dstr):
	return datetime.datetime.strptime(dstr, '%Y-%m-%d')
	

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

