# wrapper script for fastread.f90
# is this faster than xarray? lets see
import glob
from pathlib import Path
import sys 

libPath = '/home/wrudisill/scratch/WRF-HYDRO_CALIB/lib/fortran'
sys.path.insert(0,libPath)
from fastread import test

parser = argparse.ArgumentParser()
parser.add_argument("channel_point", type=str, help="directory containing model files") 
parser.add_argument("clbdirc", type=str, help="directory containing model files") 


args = parser.parse_args()

pathtofiles = Path(args.clbdirc)

filelist = pathtofiles.glob('*CHRTOUT*')
outputfile = 'modelstreamflow.txt'


for f in filelist:
	test.readnc(f, 22, 752, outputfile) 

