import os
import sys
import logging
import pandas as pd
import xarray as xr
import time
from pathlib import Path
import dblogger as dbl
from SetMeUp import SetMeUp
import accessories as acc
import yaml
import functools
from math import ceil


logger = logging.getLogger(__name__)

class Assimilate(SetMeUp):

    """Summary
    """

    def __init__(self, setup, dasetup):
        """Summary

        Args:
            setup (TYPE): Description
        """
        # get all of the methods from SetMeUp...
        super(self.__class__, self).__init__(setup)
        with open(dasetup) as y:
            yamlfile = yaml.load(y, Loader=yaml.FullLoader)

        self.dadirc = self.parent_directory.joinpath('Assimilation')
        self.da_params = yamlfile
        self.n_ens = yamlfile['n_ens']     # Read this from above later
        self.obs_interval = 1              # days

    def DaTimeStepping(self, **kwargs):
        '''
        Divide up the run into the correct size of 'chunks'. (We don't want to
        run WRF in one continuous run-- that is too much time on the scheduler
        most likely...). Use logic to figure out the amount of walltime to
        request.
        :type       kwargs: start_date (str)
                            end_date: (str)
                            chunk_size: (int)
        '''
        # Read in the kwargs and assign optional values
        start_date = acc.DateParser(kwargs.get('start_date', self.calib_start_date))
        end_date = acc.DateParser(kwargs.get('end_date', self.calib_end_date))
        restart = False
        chunk_size = self.obs_interval

        # Get the start/end dates
        zippedlist = list(acc.DateGenerator(start_date, end_date, chunk_size))
        chunk_tracker = []

        # Log things
        logger.info('WRF-Hydro start date: %s', start_date)
        logger.info('WRF-Hydro end date: %s', end_date)
        logger.info('WRF-Hydro Observation Interval: %s', self.obs_interval)

        # Loop through the list of dates and create chunking dictionary
        for i, dates in enumerate(zippedlist):
            # Calculate the lenght of the chunk
            chunk_start = dates[0]
            chunk_end = dates[1]

            # Get hrs/days from length, compute hours
            _cdays_to_hrs = (chunk_end - chunk_start).days*24
            _cdays_to_sec = (chunk_end - chunk_start).seconds/3600
            chunk_hours = _cdays_to_hrs + _cdays_to_sec

            # determine if the initial run is a restart:
            if i == 0:
                # check if the 'restart' flag exists in the setup, and
                # verify that the restart file lives in the correct spot
                restart = restart  # should be true or false

                #check that the restart files exist in the run directory...
                #TODO
            else:
                restart = True

            # write out some useful information
            log_message_template = 'Chunk {}:{}->{}({}hrs). Restart:{}'
            log_message = log_message_template.format(i,
                                          chunk_start,
                                          chunk_end,
                                          chunk_hours,
                                          restart)
            logger.info(log_message)

            # Create the wall time string -- no need to EVER ask for less than
            # an hour of wall time. Only whole hours allowed.
            # Get the rate value from the setup parameters
            time_rate = .1

            # rounds up -- minumum is 1 hour
            wall_hours = ceil(chunk_hours*time_rate)
            wall_hours_format = "{}:00:00"

            walltime_request = wall_hours_format.format(wall_hours)
            # assign things to the dictionary
            chunk = {'start_date': chunk_start,  # timestamp obj
                     'end_date': chunk_end,      # timestamp obj
                     'run_hours': int(chunk_hours),
                     'restart': restart,
                     'walltime_request': walltime_request}
            # assign to the list
            chunk_tracker.append(chunk)

        # assign chunk list to self
        return chunk_tracker


    @acc.timer
    def PrepareAssimilation(self):
        """Summary
        Create the requisite directories for running the ensembles. The submit scripts
        and the namelists get updated when we actually run each iteration
        """

        # Get the appropriate forcing files
        # TODO: do the timestepping

        linkForcings = self.GatherForcings(self.calib_start_date,
                                           self.calib_end_date)

        # Make the Parent Directory
        self.dadirc.mkdir(exist_ok = True, parents=True)

        # Make the Ensemble directory....
        # unique names for the ensemble directories
        uniqueNames = [acc.string_gen(3) + '_tmp' for i in range(self.n_ens)]
        self.ensDirectories = [self.dadirc.joinpath(i) for i in uniqueNames]

        # Build directories
        # -----------------
        #  Define a 'partial' function for mapping
        # reorder the arguments in the create run dir so we can use functools.partial ... ugh
        reorder = lambda linkForcings, runpath: self._CreateRunDir_(runpath, linkForcings)

        # 'fixed' link forcings parameter, now we can use multithread
        CreateRunDir_Partial = functools.partial(reorder, linkForcings)
        acc.multi_thread(CreateRunDir_Partial, self.ensDirectories)

        # Done

    @staticmethod
    def _ForwardModel_(userid,
                       catchid,
                       check_file,
                       directory,
                       submit_script='submit.sh'):
        """Summary
        Parameters:
            directory (TYPE): Description
            check_file (TYPE): Description
            userid (TYPE): Description
            jobid (TYPE): Description
            submit_script (str, optional): Description

        Returns:
            Bool : True if check_file is found, false otherwise

        """
        cwd = os.getcwd()
        logger.info('Calling Forward Model')

        # Move directories and submit the job...
        os.chdir(directory)
    #    jobid, err = Submit('submit.sh', catchid)
        time.sleep(1)

        # Wait for the job to complete
    #    WaitForJob(jobid, userid)
        acc.SystemCmd('touch foo.txt')

        # Verify that the model worked...
        logger.info('Done waiting...')
    #    success = acc.checkFile(check_file)

        # Move back to the parent directory...
        os.chdir(cwd)



    def EnsembleFowardStep(self):
        """Summary
        """

        #Write  all of the submit scripts

        foo = acc.AssembleSubmitString(1,16,'leaf',"01:00:00")

        ForwardModel_Partial = functools.partial(self._ForwardModel_, 'aaa','vvv','foo')

        # apply the forward model function to all of the ensemble directories
        acc.multi_thread(ForwardModel_Partial, self.ensDirectories, thread_chunk_size=self.n_ens)

    def perturb_forcings(self):
        """Summary
        Create the forcings ensemble if it does not already exist
        """
        pass
