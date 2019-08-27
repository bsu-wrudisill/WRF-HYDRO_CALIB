import numpy as np

"""
Objective functions. Calculates how well the model compares to observations
"""


# KGE 
def KGE(mod,obs):
	# Kling-Gupta Efficiency 
	# mean 
	b = np.mean(mod)/np.mean(obs)
	# std 
	a = np.std(mod)/np.std(obs) 

	# corr coeff
	r = np.corrcoef(mod,obs)[0,1]  # corrcoef returns the correlation matrix... 
	                               # the diagonals are 1, the off-diags are the 'r'
				       # value that we want
	
	# KGE as it is reported is 1 - (stuff)...
	# So a value of 1 is perfect( i,e the ratios a,b,and r 
	# are all unity).
	# let's not subtract the inside from 1. 
	# this way, a lower value is more optimal
	# same as RMSE or most other objective functions 
	kgeval = np.sqrt((r-1.)**2 + (a-1.)**2 + (b-1)**2)
	if kgeval == None:
		kgeval = 1000.
	return kgeval

# RMSE 
def RMSE(mod,obs):
	rmse = np.sqrt(np.mean((mod - obs)**2))
	return rmse
