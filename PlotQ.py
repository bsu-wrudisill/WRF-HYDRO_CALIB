import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns 


# read stuff from the database and create a plot 
sql_cmds = {'objvals': "SELECT * FROM CALIBRATION WHERE IMPROVEMENT=1",
	    'tsplot': "SELECT * FROM CALIBRATION WHERE"}

# ------ Functions ------# 
#
#
#
def returnObs(**kwargs):
	obs = pd.read_sql(sql="SELECT * FROM OBSERVATIONS", con="sqlite:///CALIBRATION.db")
	obs['time'] = pd.to_datetime(obs['time'])
	obs.drop(columns=['site_no'], inplace=True)
	return obs['qObs']
#
#
#
def PlotObj(ax, **kwargs):
	# pass in a mean to normalize RMSE by (obs, for example). Otherwise 0
	mean = kwargs.get('mean', 1)
	
	sql_cmd = "SELECT * FROM CALIBRATION"
	df = pd.read_sql(sql = sql_cmd, con="sqlite:///CALIBRATION.db")
	ax.plot(df['Iteration'], df['ObjectiveFX']/mean)
	ax.set_xlabel('iteration')
	ax.set_ylabel('Objective fx: RMSE')
	ax.set_xticks(ax.get_xticks()[::10])
	plt.savefig('objplot', dpi=601)
#
#
#
def EnsemblePlot(ax):
	# read 	
	mod_cmd = "SELECT * FROM MODOUT"
	mod = pd.read_sql(sql = mod_cmd, con="sqlite:///CALIBRATION.db")
	# 
	calib_cmd = "SELECT * FROM CALIBRATION"
	calib = pd.read_sql(sql = calib_cmd, con="sqlite:///CALIBRATION.db")
	#
	obs = pd.read_sql(sql="SELECT * FROM OBSERVATIONS", con="sqlite:///CALIBRATION.db")
	obs['time'] = pd.to_datetime(obs['time'])
	obs.drop(columns=['site_no'], inplace=True)
	
	#df.drop(columns=["Directory", "Iterations"], inplace=True)
	mod['time'] = pd.to_datetime(mod['time'])
	df_cd = pd.merge(calib, mod, how='outer', left_on = 'Iteration', right_on = 'Iterations')
	df_cd['time'] = pd.to_datetime(df_cd['time'])
	
	# now plot ....
	for iteration in df_cd['Iteration'].unique():
		sub = df_cd.loc[df_cd['Iteration'] == iteration][['time', 'qMod']]
		ax.plot(sub['time'], sub['qMod'])
	ax.plot(obs['time'], obs['qObs'])
	plt.savefig('ensemble_plot', dpi=500)
#
#
#
def ParameterPlot():
	fig,ax =  plt.subplots(2,3)
	#def ParameterPlot(ax):
	param_cmd = "SELECT * FROM PARAMETERS WHERE calib_flag = 1"
	param = pd.read_sql(sql = param_cmd, con="sqlite:///CALIBRATION.db")
	calib_cmd = "SELECT * FROM CALIBRATION"
	calib = pd.read_sql(sql = calib_cmd, con="sqlite:///CALIBRATION.db")
	merge = pd.merge(param, calib, how='outer', left_on = 'Iteration', right_on = 'Iteration')

	for axx, p in zip(ax.flatten(), param['parameter'].unique()):
		sub=merge.loc[merge['parameter'] == p]
		cval = sub['currentValue']  # normalize the parameter range 
		obj = sub['ObjectiveFX']
		xmax = sub['maxValue'].iloc[0]
		xmin = sub['minValue'].iloc[0]
		axx.scatter(cval, obj, label = p)
		axx.set_xlim(xmin,xmax)
		axx.legend(loc=1)
		axx.set_xlabel('param value')
		axx.set_ylabel('RMSE')
	fig.tight_layout()
	plt.savefig('param_performance')


if __name__ == '__main__':
	fig,ax = plt.subplots()
	#mean = returnObs().mean()
	#PlotObj(ax, mean=mean)
	EnsemblePlot(ax)
	pass 

