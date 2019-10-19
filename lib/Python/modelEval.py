import sys 
libPath = '/scratch/wrudisill/IDWR_Calibration/Boise_feather/WRF-HYDRO_CALIB/lib/Python'
sys.path.insert(0,libPath)
import dblogger as dbl
import WaterBalance as WB 
import logging 


logfile = 'model_evalualtion.log'
file_handler = logging.FileHandler(filename=logfile)
stdout_handler = logging.StreamHandler(sys.stdout)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)15s %(levelname)-8s %(message)s',datefmt='%a, %d %b %Y %H:%M:%S',handlers=[file_handler, stdout_handler])
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


if __name__ == "__main__":
	clbdirc = sys.argv[1]
	iteration = sys.argv[2]
	# log the performance 
	dbl.logModelout(clbdirc, iteration) 
	
	# log some water balance stuff 
	#WB.ChannelRouting('setup.yaml').logRouting(iteration)
	#WB.LandSurface('setup.yaml').logLSM(iteration)
	#WB.LandSurface('setup.yaml').logAquifer(iteration)
