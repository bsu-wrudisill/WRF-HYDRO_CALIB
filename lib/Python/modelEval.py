import sys 
libPath = '/scratch/wrudisill/WRF-HYDRO_CALIB/lib/Python'  #CHANGE ME TO SOMETHING BETTER !!!!! 
sys.path.insert(0,libPath)
import dblogger as dbl

if __name__ == "__main__":
	clbdirc = sys.argv[1]
	iteration = sys.argv[2]
	dbl.logModelout(clbdirc, iteration) 

else:
	pass 
