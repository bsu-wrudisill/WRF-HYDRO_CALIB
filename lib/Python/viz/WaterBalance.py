import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import xarray as xr
import sys 
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
from pathlib import Path

# ds 

#chrtFiles = xr.open_mfdataset(dsPath.glob(chrt))

class WaterBalance():
	
	def __init__(self):
		self.dsPath = Path('/scratch/wrudisill/WRF-HYDRO_CALIB/13185000_TESTING')
		self.chrt ='*CHRTOUT*'
		self.ldas = '*LDASOUT*'
		
		self.Qdic = {"qSfcLatRunoff":"Runoff From Terrain Routing (m3/s)",
			     "qBucket": "Flux from gw bucket",
			     "qBtmVertRunoff": "Runoff from bottom of soil to bucket",
			     "streamflow": "streamflow"		
			     }
		# GUESSTIMATE
		self.GaugeID = 126 

	def AccVars():
		# get acc variables 
		final_file = '201109031700.LDASOUT_DOMAIN1'
		lastFile = xr.open_dataset(dsPath.joinpath(final_file))


		# ET and P 
		ET = lastFile['ACCET'][0,:,:]
		P  = lastFile['ACCPRCP'][0,:,:]

		# get the grid shape 
		x,y = ET.shape
		gridRes = 1.0 #km 
		gridArea = x*y*gridRes # area in km^2
		return P
	
	def Routing(self):
		# open the chan routing files
		ds = xr.open_mfdataset(self.dsPath.glob(self.chrt))
			
		# read things 
		qsfc = ds['qSfcLatRunoff'][:,self.GaugeID].mean()*dts 
		qbk  = ds['qBucket'][:,self.GaugeID].mean()*dts  
		qbtm = ds['qBtmVertRunoff'][:,self.GaugeID].mean()*dts  
		Q    = ds['streamflow'][:,self.GaugeID].mean()*dts   
			
		return [qsfc, qbk, qbtm, Q]	 

						

if __name__=='__main__':
	foo=WaterBalance()
	foo.Routing()



# CHECK THe 

