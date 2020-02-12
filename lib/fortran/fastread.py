# wrapper script for fastread.f90
# is this faster than xarray? lets see
import glob
from pathlib import Path
import sys 

libPath = '/home/wrudisill/scratch/WRF-HYDRO_CALIB/lib/fortran'
sys.path.insert(0,libPath)
from fastread import test


clbdirc = sys.argv[1]
pathtofiles = Path(clbdirc)
filelist = pathtofiles.glob('*CHRTOUT*')
outputfile = 'modelstreamflow.txt'


for f in filelist:
	test.readnc(f, 22, 752, outputfile) 

