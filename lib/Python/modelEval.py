import sys 
libPath = '/scratch/wrudisill/WRF-HYDRO_CALIB/lib/Python'  #CHANGE ME TO SOMETHING BETTER !!!!! 
sys.path.insert(0,libPath)
import dblogger as dbl
import WaterBalance as WB 

if __name__ == "__main__":
	clbdirc = sys.argv[1]
	iteration = sys.argv[2]
	# log the performance 
	dbl.logModelout(clbdirc, iteration) 
	
	# log some water balance stuff 
	WB.ChannelRouting('setup.yaml').logRouting(iteration)
	WB.LandSurface('setup.yaml').logLSM(iteration)
	WB.LandSurface('setup.yaml').logAquifer(iteration)
