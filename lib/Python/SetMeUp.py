import yaml
import shutil
import os
import sys
import accessories as acc
import logging
import pandas as pd
import pathlib
from pathlib import Path

logger = logging.getLogger(__name__)


class SetMeUp:
    """
    Description:
    ------------
    SetMeUp instance--- the purpose is to read in general stuff from the
    'setup.yml' file. The __init__ methods parses this file and assigns
    names, filepaths, etc. Other functions (not in __init__) will perform
    other tasks related to model setup, such as creating directories, linking
    files, downloading things, etc.

    Attributes:
    -----------
        adjust_forcings (TYPE): Description
        benefit_file (TYPE): Description
        calib_date (TYPE): Description
        calib_files_to_copy (TYPE): Description
        catchid (TYPE): Description
        clbdirc (TYPE): Description
        cwd (TYPE): Description
        end_date (TYPE): Description
        eval_date (TYPE): Description
        eval_end_date (TYPE): Description
        eval_start_date (TYPE): Description
        exedirc (TYPE): Description
        files_to_copy (TYPE): Description
        final_chrtfile (TYPE): Description
        final_val_chrtfile (TYPE): Description
        forcdirc (TYPE): Description
        forcings_format (str): Description
        forcings_time_format (str): Description
        gauge_loc (TYPE): Description
        hrldasrestart (TYPE): Description
        hydrorestart (TYPE): Description
        linkForcingPath (TYPE): Description
        max_iters (TYPE): Description
        nodes (TYPE): Description
        obsFileName (str): Description
        parameter_table (str): Description
        parent_directory (TYPE): Description
        parmdirc (TYPE): Description
        queue (TYPE): Description
        setup (TYPE): Description
        start_date (TYPE): Description
        userid (TYPE): Description
        usgs_code (TYPE): Description
        val_date (TYPE): Description
        val_end_date (TYPE): Description
        val_eval_date (TYPE): Description
        val_start_date (TYPE): Description
        valdirc (TYPE): Description
    """

    def __init__(self, setup, **kwargs):
        """
        Parse the setup.yaml file. The init class gets called
        by other classes, so no actions should take place.

        Args:
            setup (str): path to .yaml file
            **kwargs:
                None
        """
        if type(setup) == str:
            with open(setup) as y:
                yamlfile = yaml.load(y, Loader=yaml.FullLoader)
        if type(setup) == dict:
            yamlfile = setup

        # General stuff
        # -------------
        self.userid = 'wrudisill'
        self.parameter_table = 'calib_params.tbl'
        self.setup = setup
        self.usgs_code = str(yamlfile['usgs_code'])
        self.max_iteration = yamlfile['dds_iter']
        self.obsFileName = 'obsStrData.csv'  # this gets created
        name_ext = yamlfile['name_ext']

        # Restart files
        # --------------------------------
        self.hydrorestart = yamlfile['hydro_restart_file']
        self.hrldasrestart = yamlfile['hrldas_restart_file']

        # Run parameters (more?)
        # ------------------------------
        self.queue = yamlfile['QUEUE']
        self.nodes = yamlfile['NODES']

        # File Paths and Directories
        # --------------------------
        self.cwd = Path(os.getcwd())
        self.libdirc = self.cwd.joinpath('lib', 'Python')
        self.parmdirc = Path(yamlfile['parameter_location'])
        self.exedirc = Path(yamlfile['executable_location'])
        self.forcdirc = Path(yamlfile['forcing_location'])
        self.parent_directory = Path(yamlfile['calib_location']).joinpath(name_ext)
        self.clbdirc = self.parent_directory.joinpath('Calibration')
        self.valdirc = self.parent_directory.joinpath('Validation')

        # Forcing files stuff goes here
        # -----------------------------
        # Assumes WRF Forcings .... change format if using different
        self.forcings_time_format = "%Y-%m-%d_%H:%M:%S"
        self.forcings_format = "wrfout_d02_{}"
        self.files_to_copy = ["wrf_hydro.exe",
                              "SOILPARM.TBL",
                              "CHANPARM.TBL",
                              "GENPARM.TBL",
                              "HYDRO.TBL",
                              "MPTABLE.TBL",
                              "SOILPARM.TBL"]

        self.calib_files_to_copy = ['hydro2dtbl.nc',
                                    'Route_Link.nc',
                                    'soil_properties.nc',
                                    'GWBUCKPARM.nc']
        # Create catch id file name
        self.catchid = 'catch_{}'.format(self.usgs_code)

        # Start/End Dates for the different time periods
        # ----------------------------------------------
        # Calibration date
        calib_date = yamlfile['calib_date']
        self.calib_start_date = pd.to_datetime(calib_date['start_date'])
        self.calib_end_date = pd.to_datetime(calib_date['end_date'])

        # Calibration Evaluation period
        eval_date = yamlfile['calib_eval_date']
        self.ceval_start_date = pd.to_datetime(eval_date['start_date'])
        self.ceval_end_date = pd.to_datetime(eval_date['end_date'])

        # Validataion period
        val_date = yamlfile['val_date']
        self.val_start_date = pd.to_datetime(val_date['start_date'])
        self.val_end_date = pd.to_datetime(val_date['end_date'])

        # Validataion Evaluation Period
        val_eval_date = yamlfile['val_eval_date']
        self.veval_start_date = pd.to_datetime(val_eval_date['start_date'])
        self.veval_end_date = pd.to_datetime(val_eval_date['end_date'])

        # Starting gauge location--- not known until we can read
        # a channel routing point...
        self.gauge_loc = None

        # Precipition adustment
        # ---------------------
        self.adjust_forcings = yamlfile['adjust_forcings']
        self.benefit_file = yamlfile['benefit_file']

        # Final Output File Name...
        self.chrtfmt = "{}{}{}{}00.CHRTOUT_DOMAIN2"

    def GatherForcingsFast(self, start_date, end_date, **kwargs):
        """
        Args:
            start_date :: str parsable by pandas daterange
            end_date :: "   "
            **kwargs
        Returns:
            None. Assings 'linkForcingPath' list to self
        """

        # Parse **kwargs
        # --------------

        # Begin
        # ------
        logger.info('Searching for forcing data...')
        # Get the correct dates for the forcing files
        dRange = pd.date_range(start_date,
                               end_date,
                               freq='H')
        dRange = dRange.strftime("%Y-%m-%d_%H:%M:%S")
        reqForcingList = [self.forcings_format.format(x) for x in dRange]

        # Create list of files for linking to the directory
        linkForcingPath = []
        missing_list = []
        failureFlag = 0  # Missing forcing file count

        for f in reqForcingList:
            src = Path(self.forcdirc).joinpath(f)
            if (not src.is_symlink() or not src.is_file()):
                failureFlag += 1
                missing_list.append(str(src))
            else:
                linkForcingPath.append(src)

        # Exit if forcings aren't found
        if failureFlag != 0:
            lreq = len(reqForcingList)
            lmis = len(missing_list)
            logger.error('Missing {}/{} forcing files'.format(lmis, lreq))
            sys.exit()
        else:
            logger.info('Found req forcing files')
            self.linkForcingPath = linkForcingPath

        # Return a full list of forcing files necessary for the start/date
        return linkForcingPath

    def GatherForcings(self, start_date, end_date, **kwargs):
        """
        Find all of the forcings for the specified time period
        this recursively searches all directories date range of
        calibration period.
        Assumes forcings are hourly.

        Args:
            start_date :: str parsable by pandas daterange
            end_date :: "   "
        Returns:
            None. Assings 'linkForcingPath' list to self
        """

        # Parse **kwargs
        # --------------

        # Begin
        # -----
        dRange = pd.date_range(start_date,
                               end_date,
                               freq='H')
        dRange = dRange.strftime("%Y-%m-%d_%H:%M:%S")

        # Create list of forcing names
        forcingList = [self.forcings_format.format(x) for x in dRange]
        forcingNumber = len(forcingList)

        # List of filepaths for linking ....
        linkForcingPath = []

        # Create a dictionary with name:filepath
        globDic = dict([(p.name, p)
                        for p in Path(self.forcdirc).glob("**/wrfout*")])

        # Loop through the forcing list, try to find all of the files
        failureFlag = 0
        for f in forcingList:
            if f in globDic:  # check if the key is in the dictionary
                linkForcingPath.append(globDic[f])
            else:
                failureFlag += 1
                logger.info('Cannot locate: \n {}'.format(f))

        # Check if things failed
        if failureFlag != 0:
            logger.error('Unable to locate {} of {} forcing files'.format(
                failureFlag, forcingNumber))
            sys.exit()
        else:
            message = 'Found {} required forcing files, \
                       continuing'.format(forcingNumber)
            logger.info(message)

        # Assign list of forcing paths to link--- but do not link yet
        self.linkForcingPath = linkForcingPath

        # Return a full list of forcing files necessary for the start/date
        return linkForcingPath

    def GatherObs(self, runpath, start_date, end_date, **kwargs):
        """Summary
        Run the rscripts to download the USGS observations
        for the correct time period and gauge.
        This is prone to error!! The download will work
        but the USGS data might not exists....

        Args:
            runpath (posix.Path): directory of download destination
            start_date (str) :: parsable by pandas daterange
            end_date (str) :: "   "
        """

        if type(runpath) != pathlib.PosixPath:
            runpath = pathlib.Path(runpath)

        datapath = runpath.joinpath(self.obsFileName)
        # TODO: figure out root path thing....
        cmdEmpty = 'Rscript ./lib/R/fetchUSGSobs.R {} {} {} {}'

        # Format the datetime in the format that R wants...
        startString = str(start_date.strftime("%Y-%m-%d"))
        endString = str(end_date.strftime("%Y-%m-%d"))
        cmd = cmdEmpty.format(self.usgs_code,
                                      startString,
                                      endString,
                                      datapath)
        logger.debug(cmd)
        try:
            os.system(cmd)

        except Error as e: # WHAT IS THE EXCEPTION!!!!
            logger.error(e)
            logger.error('Unable to execute command {}'.format(cmdEmpty))
            sys.exit()

        # now we check the observations to make sure there are none missing...

    def CreateRunDir(self, runpath, linkForcings, **kwargs):
        """
        Create run directory for WRF-hdyro calib.ation runs.
        Copies files from the "directory_location" to the
        "calib.location" defined in the setup.yaml file

        Args:
            runpath (posix.Path): Description
            linkForcings (TYPE): List of posix.Path to forcing files
            **kwargs: linkForcing ([pathlib.Path]): paths of the req. forcing
                                                  files
        """
        # Check if the runpath exists...
        if type(runpath) != pathlib.PosixPath:
            runpath = pathlib.Path(runpath)
        if runpath.exists():
            logger.error("{} exists...".format(runpath))
            sys.exit()

        # Now, lets create the directory to perform the calibration
        shutil.copytree(self.parmdirc, runpath.joinpath('DOMAIN'))

        # Create a directory to store the original domain files in.
        startingParamDir = runpath.joinpath('ORIG_PARM')
        startingParamDir.mkdir(exist_ok=True)

        # Make copies of the domain parameters that we will later calibrate
        for cf in self.calib_files_to_copy:
            src = self.parmdirc.joinpath(cf)
            dst = startingParamDir.joinpath(cf)
            shutil.copy(src, dst)

        # Copy files in the 'files_to_copy list' to the run directory
        for cf in self.files_to_copy:
            src = self.exedirc.joinpath(cf)
            dst = runpath.joinpath(cf)
            shutil.copy(src, dst)

        # Create the Forcing Directory and Link forcings
        forcing_directory = runpath.joinpath('FORCING')
        forcing_directory.mkdir(exist_ok=True)
        for src in linkForcings:
            dst = forcing_directory.joinpath(src.name)
            os.symlink(src, dst)

        # Copy namelists and other text files...
        #shutil.copy('./namelists/hydro.namelist.TEMPLATE',
        #            runpath.joinpath('hydro.namelist'))
        #shutil.copy('./namelists/namelist.hrldas.TEMPLATE', runpath)

        shutil.copy('./env_nwm_r2.sh', runpath)
        shutil.copy(self.parameter_table, runpath)
        shutil.copy('./{}'.format(self.setup), runpath)

        # Copy more scripts
        shutil.copy('./lib/Python/viz/PlotQ.py', runpath)
        shutil.copy('./lib/fortran/fastread.py', runpath)

        # log success
        logger.info('created run directory {}'.format(runpath))

    def CreateNamelist(self, runpath, start_date, end_date, **kwargs):
        """Summary
        Write in text into the namelist script templates

        Args:
            runpath (posix.Path): script destination
            start_date (datetime):
            end_date (datetime):
        **kwargs: Description

        """
        # Check if the runpath exists...
        if type(runpath) != pathlib.PosixPath:
            runpath = pathlib.Path(runpath)

        if self.hrldasrestart == "None":
            hrldasrestart = "!RESTART_FILENAME_REQUESTED"
        else:
            hrldasrestart = "RESTART_FILENAME_REQUESTED = \"{}\"".format(
                self.hrldasrestart)

        if self.hydrorestart == "None":
            hydrorestart = "!RESTART_FILE"
        else:
            hydrorestart = "RESTART_FILE = \"{}\"".format(self.hydrorestart)

        # modify the namelist templates that reside in the run dir
        date_range = end_date - start_date
        nlistDic = {"YYYY": start_date.year,
                    "MM": start_date.month,
                    "DD": start_date.day,
                    "HH": start_date.hour,
                    "NDAYS": date_range.days,
                    "RESTART_FILENAME_REQUESTED": hrldasrestart
                    }
        # Modify namelist.hrldas
        acc.GenericWrite('./namelists/namelist.hrldas.TEMPLATE',
                         nlistDic,
                         runpath.joinpath('namelist.hrldas'))

        # Modify the hydro.namelist
        hydDic = {"RESTART_FILE": hydrorestart}
        acc.GenericWrite('./namelists/hydro.namelist.TEMPLATE',
                         hydDic,
                         runpath.joinpath('hydro.namelist'))
        # Done
        logger.info('Created Namelist files')

    def CreateSubmitScript(self, runpath, **kwargs):
        """
        Read the  the submit script template and modify the correct lines
        to run the desired job
        """
        if type(runpath) != pathlib.PosixPath:
            runpath = pathlib.Path(runpath)

        taskX = 28
        runTime = "06:00:00"
        slurmDic = {"QUEUE": self.queue,
                    "NODES": self.nodes,
                    "TASKS": int(self.nodes) * taskX,
                    "RUN_TIME": runTime,
                    "CATCHID": "catch_{}".format(self.usgs_code)
                    }
        # Create the submission script
        acc.GenericWrite('{}/namelists/submit.TEMPLATE.sh'.format(self.cwd),
                         slurmDic,
                         runpath.joinpath('submit.sh'))
        # Done
        logger.info('created job submission script')

    def CreateAnalScript(self, runpath, database, iteration, **kwargs):
        """
        Create the job submit script for the analysis step.
        Previous code did the analysis on the head node and
        ran into memory issues. This way, each file read process
        (called later) gets started and closed with each iteration,
        so memory leaks in the python netcdf library don't accumulate

        Args:
            runpath (posix.Path): run path
            database (str): name of database to log information to
            **kwargs:
                None
        """
        if type(runpath) != pathlib.PosixPath:
            runpath = pathlib.Path(runpath)

        submit_analysis = runpath.joinpath('submit_analysis.sh')

        if os.path.isfile(submit_analysis):
            os.remove(submit_analysis)
            message = 'removed previous analysis job\
                       submit script {}'.format(submit_analysis)
            logger.info(message)

        namelist_template = self.cwd.joinpath('namelists',
                                              'submit_analysis.TEMPLATE.sh')

        namelist_replace = runpath.joinpath('submit_analysis.sh')
        # Determine submit parameters...
        taskX = 28
        runTime = "06:00:00"  # make this dynamic...
        aNodes = 2
        aTasks = aNodes * taskX

        # update dictionary...
        insert = {"DATABASE_NAME": database,
                  "ITERATION_COUNT": iteration,
                  "PATH_TO_PYTHON": self.libdirc,
                  "ANALYSIS_TASKS": aTasks,
                  "ANALYSIS_NODES": aNodes,
                  "ANALYSIS_QUEUE": self.queue,
                  "ANALYSIS_TIME": runTime
                  }

        # Create/Update the job submit template into the directory
        acc.GenericWrite(namelist_template,
                         insert,
                         namelist_replace)

