import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import xarray as xr
import sys 
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
from pathlib import Path
libPath = '../'  #CHANGE ME TO SOMETHING BETTER !!!!! 
sys.path.insert(0,libPath)
import dblogger as dbl
from adjustParameters import SetMeUp

# Units and conversions 
km3_to_acrefeet = 810714
m3_to_acrefeet = 0.000810714 # one cubic meter is this many acre feet
			     # according to wikipwdia, lucky peak is 307,000 acre_ft
m3_to_km3 = 1E-6             # cubic meter to cubic kilometer
mm_to_km = 1E-6              # mm to km 

def dfCreator(dataList):
	print(len(dataList))
	#if len(dataList) != 7:
	#	print('inptut list len not correct')
#		return 
	fulldf = {'Iteration': dataList[0],
		   'Quantity':dataList[1],
		   'Value':dataList[2],
		   'Description':dataList[3],
		   'Unit':dataList[4],
		   'Aggregation':dataList[5],
		   'EvalPeriod':dataList[6]}
	return fulldf  


# classes below here 
class ChannelRouting(SetMeUp):
	def __init__(self,setup):
		super(self.__class__, self).__init__(setup) # this will get all of the attrs. from the SetMeUp instance 
		self.dsPath= Path(self.clbdirc)
		print(self.dsPath)
		self.chrt ='*CHRTOUT*'
		self.GaugeID = 126
		self.Qdic = {"qSfcLatRunoff":"Runoff From Terrain Routing (m3/s)",
			     "qBucket": "Flux from gw bucket",
			     "qBtmVertRunoff": "Runoff from bottom of soil to bucket",
			     "streamflow": "Total streamflow"		
			     }
		
		self.dtSeconds = 3600 #model output time step in seconds
		
		# open up the model files 	
		self.ds = xr.open_mfdataset(self.dsPath.glob(self.chrt))
		self.dateRange = self.eval_start_date - self.eval_end_date 
	
		self.df = pd.DataFrame(columns=['Iteration', 'Quantity','Value',
			                        'Description','Unit','Aggregation',
						'EvalPeriod'])
	def integrateRate(self,var):
		#___________________________________________________________
		# cm/s convert to km3
		#           _               _______
		#     _    | |             |       | 
		#  _ | | _ | | (cf/s)  ==> | acre_feet  |
		# | || || || |             |_______| 
		#    ( time ) 
		#___________________________________________________________
		output = self.ds[var][:,self.GaugeID].sum()*self.dtSeconds*m3_to_acrefeet
		return np.float(output.values)

	
	def logRouting(self, iters):
		drange = '{} : {}'.format(str(self.eval_start_date), str(self.eval_end_date))
		df = self.df.copy()
		# open the chan routing files
		for key in self.Qdic.keys():
			output = self.integrateRate(key)
			row = [iters, key, output, self.Qdic[key], 'acre_feet', 'point', drange]
			dic = dfCreator(row)
			df = df.append(dic, ignore_index=True)
		df.set_index('Iteration', inplace=True)
		dbl.logDataframe(df, 'WATER_BALANCE', str(self.dsPath))

class LandSurface(SetMeUp):
	def __init__(self,setup):
		super(self.__class__, self).__init__(setup)
		self.dsPath = Path(self.clbdirc)
		
		# get acc variables 
		firstFile = "{}.LDASOUT_DOMAIN1".format(self.eval_start_date.strftime("%Y%m%d%M%S"))
		lastFile = "{}.LDASOUT_DOMAIN1".format(self.eval_end_date.strftime("%Y%m%d%M%S"))
		self.first = xr.open_dataset(self.dsPath.joinpath(firstFile))
		self.last = xr.open_dataset(self.dsPath.joinpath(lastFile))
		self.df = pd.DataFrame(columns=['Iteration', 'Quantity','Value',
			                        'Description','Unit','Aggregation','EvalPeriod'])
		self.landDic = {'ACCET': 'Acc. Evapotranspiration',
				'ACCPRCP': 'Acc. Precipitation',
				'SFCRNOFF': 'Acc. Surface Runoff',
				'UGDRNOFF': 'Acc. Underground Runoff'}
	
		self.drange = '{} : {}'.format(str(self.eval_start_date), str(self.eval_end_date)) 
	def accVar(self,var): 
		# get change in acc. vars between start and end periods 
		varDepth = (self.last[var][0,:,:] - self.first[var][0,:,:])*mm_to_km
		
		# get the grid shape 
		x,y = varDepth.shape
		gridRes = 1.0 #km^2
		#gridArea = x*y*gridRes # the TOTAL grid sqkm 
	
		# now mult to get volume in km3 
		varVol = (varDepth*gridRes).sum()*km3_to_acrefeet
		return np.float(varVol.values)
		

	def logAquifer(self, niter):
		# kgm-2 * 1E6m2km-2 / density (1000kgm-3) ==> m3 
		df = self.df.copy()
		
		gridRes_m = 1E6 #m2
		h20_density = 1E3 # kg/m3 
		WT = (self.last['WT'][0,:,:] - self.first['WT'][0,:,:])*gridRes_m  # now units of kg 
		WA = (self.last['WA'][0,:,:] - self.first['WA'][0,:,:])*gridRes_m  #
		# 
		WT_vol = WT.sum()/h20_density*m3_to_acrefeet  # kg --> m3 --> acrefeet 
		WA_vol = WA.sum()/h20_density*m3_to_acrefeet
		WT_row = [niter, 'WT', np.float(WT_vol.values),'Water in aquifer', 'acre_feet', 'area_total', self.drange]
		WA_row = [niter, 'WA', np.float(WA_vol.values),'Water in aquifer and sat soil', 'acre_feet', 'area_total', self.drange]
		df = df.append(dfCreator(WT_row), ignore_index=True)
		df = df.append(dfCreator(WA_row), ignore_index=True)
		df.set_index('Iteration', inplace=True)
		dbl.logDataframe(df, 'WATER_BALANCE', str(self.dsPath))

	def logLSM(self, niter): 
		df = self.df.copy()
		# creat list 		
		for key in self.landDic.keys():
			output = self.accVar(key)
			row = [niter, key, output, self.landDic[key], 'acre_feet', 'area_total', self.drange]
			dic = dfCreator(row)
			df = df.append(dic, ignore_index=True)
			# assign to df ... this is dumb 
		df.set_index('Iteration', inplace=True)
		dbl.logDataframe(df, 'WATER_BALANCE', str(self.dsPath))


	def RP_ratio(self):
		P,ET = self.AccVars()
		RP = Q/P 
		

if __name__=='__main__':
	foo = LandSurface('../../setup.yaml')
	foo.logLSM(1)
	foo.logAquifer(1)	
	# do something 
	pass
