import json
import shutil
import os 
import glob 
import subprocess
import xarray as xr
import pandas as pd
import functools as ft
import netCDF4 as nc
import numpy as np
import sys 
from pathlib import Path
import logging 
libPath = '/scratch/wrudisill/WRF-HYDRO_CALIB/lib/Python'  #CHANGE ME TO SOMETHING BETTER !!!!! 
sys.path.insert(0,libPath)
import dblogger as dbl
from adjustParameters import CalibrationMaster as cm
import ancil


if __name__ == "__main__":
	clbdirc = sys.argv[1]
	iteration = sys.argv[2]
	cm.ReadQ(clbdirc, iteration) 

else:
	pass 
