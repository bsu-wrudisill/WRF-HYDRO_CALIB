#import json
#import shutil
#import os 
#import glob 
#import subprocess
#import xarray as xr
#import pandas as pd
#import functools as ft
#import netCDF4 as nc
#import numpy as np
#from pathlib import Path
#import logging 

import sys 

libPath = '/scratch/wrudisill/WRF-HYDRO_CALIB/lib/Python'  #CHANGE ME TO SOMETHING BETTER !!!!! 
sys.path.insert(0,libPath)
import dblogger as dbl
#import accessories as acc 


if __name__ == "__main__":
	clbdirc = sys.argv[1]
	iteration = sys.argv[2]
	dbl.logModelout(clbdirc, iteration) 

else:
	pass 
