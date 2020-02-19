import numpy as np
from scipy.stats import spearmanr
from scipy.stats import kendalltau


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

def corrcoef(mod,obs):
	return np.corrcoef(mod,obs)[0,1]

def NSE(mod,obs):
	# NSE is the same as the R^2 value... with is 
	# same as the squared correlation coefficient....
	# why is this a separate thing...

	return np.corrcoef(mod,obs)[0,1]**2


def minn(mod,obs):
	return np.min(mod) - np.min(obs)

def maxx(mod,obs):
	return np.max(mod) - np.max(obs)

def tq(mod, obs):
	return np.sum(mod) - np.sum(obs)

def RMSE(mod,obs):
	rmse = np.sqrt(np.mean((mod - obs)**2))
	return rmse

def spear(mod,obs):
	# from scipy
	# the spearman rank correlation method
	# a non parametric method for testing 
	# that two datasets are monotonically 
	# moving in the same directions 
	coef, p = spearmanr(mod,obs)

def kendal(mod,obs):
	# from scipy...
	# the kendal tau test, another 
	# nonparametric method for computing
	# correlation between 2 datasets 
	coef, p = kendalltau(mod,obs) 


