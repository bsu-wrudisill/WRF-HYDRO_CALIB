import numpy as np

"""
Objective functions. Calculates how well the model compares to observations
"""
def objchecker(func):
	large_number = 1e6
	def wrapped_function(obs,mod):
		if np.sum(mod) == 0:
			message='model values are zero'
			return np.nan, message 
		
		if np.sum(obs) == 0:
			message='obs values are zero'
			return np.nan, message 
		else:
			return func(obs,mod)
	return wrapped_function


# KGE
@objchecker
def KGE(mod,obs):
	# Kling-Gupta Efficiency (KGE)
	# KGE as it is reported is 1 - sqrt( (1-corrcoef_ratio)^2 + (1-std_ratio)^2 + (1-mean_ratio)^2 ) 
	# So a value of 1 is perfect( i,e the ratios a,b,and r 
	# are all unity).
	# let's not subtract the inside from 1. 
	# this way, a lower value is more optimal
	# same as RMSE or most other objective functions 
	b = np.mean(mod)/np.mean(obs)
	# std 
	a = np.std(mod)/np.std(obs) 
	# corr coeff
	r = np.corrcoef(mod,obs)[0,1]  # corrcoef returns the correlation matrix... 
	                               # the diagonals are 1, the off-diags are the 'r'
				       # value that we want
	kgeval = np.sqrt((r-1.)**2 + (a-1.)**2 + (b-1)**2)
	return kgeval, r, b, a 

@objchecker
def RMSE(mod,obs):
	rmse = np.sqrt(np.mean((mod - obs)**2))
	return rmse
