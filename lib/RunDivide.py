import os,sys
import datetime 
from collections import OrderedDict

class wrfChunk():
    # more stuff
    restart = False 
    namelistPath="./namelist.input.template"
    submitPath="./submit_template.sh"
    
    # params
    namelist = {"RUN_DAYS":None,
                   "RUN_HOURS":None,
                   "START_YEAR":None,
                   "START_MONTH":None,
                   "START_DAY":None,
                   "START_HOUR":None,
                   "END_YEAR":None,
                   "END_MONTH":None,
                   "END_DAY":None,
                   "END_HOUR":None,
                   "FRAMES_PER_OUTFILE":None,
                   "RESTART_RUN":None,
                   "RESTART_INTERVAL_MINS":None,
                   "FRAMES_PER_AUXHIST":None,
                   "LAST_WRFOUT":None}
    
    slurmlist = {"RUNDIR": None,
                 "JOBNAME": None, 
                 "QUEUE"  : None,
                 ".ERR"   : None,
                 ".OUT"   : None,
                 "RUNTIME": None,
                 "EXECUTABLE":None,
                 "LOGFILE":None,
                 "CATCHID":None,
                 "NODES":None,
                 "TASKS":None}
    # 
    def __init__(self,restart):
       self.restart = restart
       pass  

    def padZero(self,string):
        if type(string) != str:
            string=str(string)
        if len(string)==1:
            return "0"+string
        else:
            return string

    def DateGenerator(self, d1, d2):
        #
        #
        #check that the command makes sense
        if d2<=d1:
            print("check the dates. exiting")
            return 
        # wrf run time  
        delta=datetime.timedelta(days=3)    # length of WRF runs  
        DateList = [d1]                    # list of dates 
        # round to nearest h=00":00 to make things nicer 
        if d1.hour!=0:
            round_up_hour = 24 - d1.hour
            whole=d1+datetime.timedelta(round_up_hour)
            DateList.append(d1+datetime.timedelta(hours=round_up_hour))
        
        # now create list of <start> <end> date pairs
        next_date = DateList[-1]                  
        while (next_date+delta) < d2:
            next_date = next_date + delta
            DateList.append(next_date)  
        # append final date 
        DateList.append(d2)
        
        #update parameters 
        zippedlist=zip(DateList[:-1],DateList[1:])
        self.zipped = zippedlist 
        # update self 
        self.DateList=DateList
        self.RunHours=[ (x[1] - x[0]).days*24 + (x[1] - x[0]).seconds/3600 for x in zippedlist]
        self.RunDays=[ (x[1] - x[0]).days for x in zippedlist]
        self.Counter=len(zippedlist)
        #
        #
    def UpdateNamelist(self, index):
        start=self.zipped[index][0]
        end=self.zipped[index][1]
        
        # calculate frames per outfile 
        #framesperout=min(self.RunHours[index], 24)
        #framesperaux=min(self.RunHours[index], 24)
        
        #!! LETS DO HOURLY OUTPUT INSTEAD!! 
        framesperout=24
        framesperaux=24
        restartinterval=max(self.RunHours[index]*60,self.RunDays[index]*24*60)
        
        # restart run?   CHANGE TO OPTIONAL KEYWORD ARGUMENT
        if index > 0:
            self.restart=True
        
        # get name of last wrfout
        last_wrfout = "wrfout_*_{}-{}-{}_"
        # update starting dates  
        namelistUpdate = {"RUN_DAYS":self.RunDays[index],
                          "RUN_HOURS":self.RunHours[index],
                          "START_YEAR":start.year,
                          "START_MONTH":self.padZero(start.month),
                          "START_DAY":self.padZero(start.day),
                          "START_HOUR":self.padZero(start.hour),
                          "END_YEAR":end.year,
                          "END_MONTH":self.padZero(end.month),
                          "END_DAY":self.padZero(end.day),
                          "END_HOUR":self.padZero(end.hour),
                          "FRAMES_PER_OUTFILE":framesperout,
                          "RESTART_RUN":self.restart,
                          "RESTART_INTERVAL_MINS":restartinterval,
                          "FRAMES_PER_AUXHIST":framesperaux} 
        
        self.namelist.update(namelistUpdate) # recall that this is a dictionary method
        # done
    
    def GenericWrite(self,readpath,replacedata,writepath):
        # path to file to read 
        # data dictionary to put into file
        # path to the write out file 

        with open(readpath, 'r') as file:
            filedata = file.read()
            #  
            # loop thru dictionary and replace items
        for item in replacedata:
            filedata = filedata.replace(item, str(replacedata[item])) # make sure it's a string 

        # Write the file out again
        with open(writepath, 'w') as file:
            file.write(filedata)
        # done 
        
    def WriteNamelist(self):
        try:
            os.remove('namelist.input')
        except:
            pass
        # namelist that will be used to submit the run
        self.GenericWrite(self.namelistPath, self.namelist,'./namelist.input')
        # copy of the namelist, so we can look at it later 
        
        datestr="{}_{}_{}".format(self.namelist["START_YEAR"], self.namelist["START_DAY"], self.namelist["START_HOUR"])
        self.GenericWrite(self.namelistPath, self.namelist,'./namelist.input_{}'.format(datestr))

    # update the slurm run script 
    def SlurmUpdate(self, flag):
        # create slurm scripts to submit  
        sdate = "{}_{}_{}".format(self.namelist["START_YEAR"], self.namelist["START_DAY"], self.namelist["START_HOUR"])
        # real run
        if flag == "r":
            runtime="02:00:00" # UPDATE ME 
            jobname="real_{}".format(sdate)
            exe = "real.exe"
            nodes = 1 
            tasks = 28 
            exclusive = ""
        # wrf run
        if flag == "w":
            runtime="12:00:00"   # UPDATE ME 
            jobname="wrf_{}".format(sdate)
            exe = "wrf.exe"
            nodes = 2 
            tasks = nodes*28
            exclusive = "SBATCH --exclusive" 

        # update the slurm submit parameters 
        self.slurmlist = {"EXCLUSIVE": exclusive,
                         "JOBNAME": jobname, 
                         "QUEUE"  : "leaf",
                         ".ERR"   : jobname+'.err',
                         ".OUT"   : jobname+'.out',
                         "RUNTIME": runtime,
                         "EXECUTABLE": exe,
                         "LOGFILE": "timing_{}.log".format(sdate),
                         "CATCHID":"catch_{}".format(jobname),
                         "NODES":nodes,
                         "TASKS":tasks}
    # 
    def WriteSlurm(self):
        self.GenericWrite(self.submitPath, self.slurmlist,'submit_{}.sh'.format(self.slurmlist['JOBNAME']))
        pass 
        
