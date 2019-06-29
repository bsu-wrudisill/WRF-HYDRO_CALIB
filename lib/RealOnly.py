import RunDivide as rd 
import RunWRF as rw
import datetime 
import sys

"""
Run WRF. Supply d1 and d2 with the start and end date, and edit the run dir
for the right directory. right now, the run directory must be populated 
with the correct met_em* files and restart files (if the run is a restart run). 
the RunDivide.py and RunWRF scripts must live within this same directory for 
the time being. 
"""
# run directory -- full path 
rundir=sys.argv[1]

# the time range 
d1 = datetime.datetime(2010, 10, 1, 0, 0)
d2 = datetime.datetime(2010, 10, 1, 21, 0)

# create the 'chunk' object 
timeperiod=rd.wrfChunk(False)            # restart == True 
timeperiod.DateGenerator(d1,d2)          

# initialize WRF object 
wrf= rw.WRF_Run(timeperiod, rundir)

# create a namelist 
timeperiod.UpdateNamelist(0)
timeperiod.WriteNamelist()

# run real 
wrf.Real()
#
#
#
#
