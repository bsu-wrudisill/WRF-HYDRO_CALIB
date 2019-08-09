import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import xarray as xr
import sys 

# read stuff from the database and create a plot 
gauge_loc = -1 

def plotQ(ax, dirc):
	modQfiles = xr.open_mfdataset(glob.glob(dirc+'/*CHRTOUT_DOMAIN2*'))
	
	# aggregate 
	qDf = pd.DataFrame(
	{'qMod':modQfiles['streamflow'][:,gauge_loc].values,
	'time':modQfiles['time'].values}
	)
	qDf.set_index('time', inplace=True)
	modQdly = pd.DataFrame(qDf.resample('D').sum())
	ax.plot(modQdly,label=dirc)



if __name__ == '__main__':
	dirc=sys.argv[1]
	fig,ax = plt.subplots(1)
	fig.set_size_inches(8,8)

	plotQ(ax,dirc) 

	obsQ = pd.read_csv('{}/obsStrData.csv'.format(dirc))
	obsQ.drop(columns=['Unnamed: 0', 'site_no', 'POSIXct', "agency_cd"], inplace=True)
	obsQ.rename(index=str, columns={"Date":"time", "obs":"qObs"}, inplace=True)
	obsQ.set_index('time',inplace=True)
	obsQ.index = pd.to_datetime(obsQ.index)

	ax.plot(obsQ, label='Observations')
	plt.legend()
	ax.set_ylabel('Q m3/s')
	ax.tick_params(axis='x', rotation=45)
	plt.savefig('QuickPlot.png')
