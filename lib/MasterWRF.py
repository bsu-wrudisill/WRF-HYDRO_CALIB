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
rundir=sys.argv[1]
#
#
d1 = datetime.datetime(1998, 3, 19, 0, 0)
d2 = datetime.datetime(1998, 3, 27, 0, 0)
#
timeperiod=rd.wrfChunk(False)            # restart == True 
timeperiod.DateGenerator(d1,d2)          
#
#rundir = "/scratch/wrudisill/WRFTestDir/Run_MScase"
wrf= rw.WRF_Run(timeperiod, rundir)

#timeperiod.UpdateNamelist(0)
#timeperiod.WriteNamelist()

#wrf.Real()
#wrf.WRF()
wrf.Run()
#
#
#
#
