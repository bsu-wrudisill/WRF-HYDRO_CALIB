import os,sys
import datetime 
from collections import OrderedDict
#
#
#   
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

