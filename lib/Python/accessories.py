import os
import datetime
import subprocess
import time
import glob
import xarray as xr
import numpy as np
import traceback
import logging

logger = logging.getLogger(__name__)


"""
Function decorators
"""


def passfail(func):
    """Summary

    Args:
        func (TYPE): Description

    Returns:
        TYPE: Description
    """
    def wrapped_func(*args, **kwargs):
        try:
            func(*args)
            message = "{} Passed".format(str(func))
            return (True, message)
        except Exception as e:
            trace_string = traceback.format_exc()
            error_message = "{} Failed with the following Error: {}\n {}".format(
                str(func), e, trace_string)
            return (False, error_message)
    return wrapped_func


def timer(function):
    """Summary
    Simple decorator to time a function

    Args:
        function (TYPE): Description

    Returns:
        TYPE: Description
    """
    def wrapper(*args, **kwargs):
        t1 = datetime.datetime.now()
        wrapped_function = function(*args, **kwargs)
        t2 = datetime.datetime.now()
        dt = (t2 - t1).total_seconds() / 60   # time in minutes
        logger.info('function {} took {} minutes complete'.format(function.__name__, dt))
        return wrapped_function
    return wrapper


"""
Regular functions
"""


def checkFile(pathtofile):
    """Summary
    assert that a file exists. otherwise return false

    Args:
        pathtofile (TYPE): Description

    Returns:
        TYPE: Description
    """
    return pathtofile.is_file()


def AddOrMult(factor):
    """Summary
    Remove files from the run directory

    Args:
        factor (TYPE): Description

    Returns:
        TYPE: Description
    """

    if factor == 'mult':
        return lambda a, b: a * b
    if factor == 'add':
        return lambda a, b: a + b
    else:
        return None


def CleanUp(path):
    """Summary
    Remove files from the run directory

    Args:
        path (TYPE): Description
    """
    cwd = os.getcwd()
    os.chdir(path)
    removeList = ["*LDASOUT*", "*CHRTOUT*", "*RTOUT*", "*LSMOUT*", "*diag_hydro*", "*HYDRO_RST*"
                  "log_wrf_hydro*"]

    logger.info('cleaning up model run directory ({})'.format(path))
    for removeMe in removeList:
        cmd = 'rm -rf ./{}'.format(removeMe)
        out, err = SystemCmd(cmd)

    # move back to o.g. dir
    os.chdir(cwd)


def GaugeToGrid(chrtout, lat, lon):
    """Summary
    Go from lat-lon pair to the gauge location on the
    Routing grid
    Args:
        chrtout (TYPE): Description
        lat (TYPE): Description
        lon (TYPE): Description

    Returns:
        TYPE: Description
    """

    ds = xr.open_dataset(chrtout)
    latgrid = ds['latitude'].values
    longrid = ds['longitude'].values

    # finds the lat/lon that corresponds
    # to a given gauge point.
    # returns an integer
    return np.sqrt((latgrid - lat)**2 + (longrid - lon)**2).argmin()


def ConcatLDAS(path, ID):
    """Summary
    Path to output files
    ID to assign to the output name
    Args:
        path (TYPE): Description
        ID (TYPE): Description
    """

    logger.info('reading LDAS files')
    ldas = glob.glob(path + '/*LDASOUT_DOMAIN1')
    var_list = ['x', 'y', 'SNLIQ', 'SOIL_T', 'SNOWH', 'ISNOW']
    ds = xr.open_mfdataset(ldas, drop_variables=var_list)
    logger.info('concatenating LDAS files...')
    ds.to_netcdf("{}_LDASFILES.nc".format(ID))
    logger.info('wrote {}_LDASFILES.nc'.format(ID))
    del ds


def SystemCmd(cmd):
    """Summary

    Args:
        cmd (TYPE): Description

    Returns:
        TYPE: Description
    """
    proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True)
    out, err = proc.communicate()
    return out.split(), err


def Submit(subname, catchid):
    """Summary

    Args:
        subname (TYPE): Description
        catchid (TYPE): Description

    Returns:
        TYPE: Description
    """
    cmd = 'sbatch --parsable {}'.format(subname)
    proc = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True)
    jobid, err = proc.communicate()
    logger.info("issuing system command {}".format(cmd))
    return jobid.decode("utf-8").rstrip(), err


def WaitForJob(jobid, user, scheduler='SLURM'):
    """
    Queries the queue and finds all of the job ids that match the username.
    Create a list of those job ids (different than job names( nd tries to
    match them with the 'jobid' argument. The code will wait until none of
    the jobs in the queue match the jobid that has been passed in
    :param      jobid:      Fullpath to the submission script
    :type       jobid:      string or pathlib.Path
    :param      user:       Username on system ('whoami')
    :type       user:       string
    :param      scheduler:  The scheduler ('PBS' OR 'SLURM')
    :type       scheduler:  string
    :raises     Exception:  ValueError if scheduler is not 'PBS' or 'SLURM'
    """
    start_time = datetime.datetime.now()

    if scheduler == 'PBS':
        qcmd = "qstat | grep {} | sed \"s/^ *//\" | cut -d' ' -f1".format(user)
        # the qstat -u option parses the jobname oddly

    if scheduler == 'SLURM':
        qcmd = "squeue -u {} | sed \"s/^ *//\" | cut -d' ' -f1".format(user)

    # !!!! THIS SHOULD BE CAUGHT WAY BEFORE THIS POINT!!!!
    if scheduler not in ['PBS', 'SLURM']:
        logger.error()
        raise Exception('unknown scheduler type {}'.format(scheduler))

    def _wait(qcmd, jobid):
        # run command and parse output
        qout_raw, qerr = SystemCmd(qcmd)

        qout = [i.decode("utf-8") for i in qout_raw]
        error = qerr.decode("utf-8")

        # Check QSTAT Error
        if error != '':  # the error string is non-empty
            qstat_error = True
            logger.error("Error encountered in qstat:\n    {}".format(error))
            # set the qstat error to true; we cant exit if it is
        else:
            qstat_error = False

        # Check if the job is still running
        if jobid in qout:
            still_running = True
        else:
            still_running = False

        # RETURN
        return still_running, qstat_error

    def _timelylog(message):
        # only log every ... 10 min since the start of the
        # main function
        current_time = datetime.datetime.now()
        dt = (current_time - start_time).total_seconds() / 60

        # listing of log frequencies.... this is unnecessary
        if (dt % 60. < .1) and (dt > 60.):
            logger.info(message)

    # Set to true initially.Gets updated based on _wait return
    keep_going = True

    # start of loop
    while keep_going:
        # do the search ...
        still_running, qstat_error = _wait(qcmd, jobid)
        ctime = datetime.datetime.now()
        dt = (ctime - start_time).total_seconds() / 60
        # A job is running and qstat didn't return an error
        if still_running and (not qstat_error):
            keep_going = True
            if dt < 1.0:  # more than 1 minutes of logging..
                logger.info('Found jobid {}. Continuing...'.format(jobid))
            else:
                _timelylog('Found jobid {}. Continuing...'.format(jobid))  # Only log every hour

        # !!!! KEEP GOING UNTIL QSTAT STARTS WORKING AGAIN !!!
        if qstat_error:
            keep_going = True
            logger.info('Qstat encountered error. Continuing...')

        # The only acceptable exit point. No jobs found, and qstat didn't return an error
        if (not still_running) and (not qstat_error):
            keep_going = False
            logger.info('jobid {} is no longer in the queue'.format(jobid))

        # sleep for thirty seconds
        time.sleep(30)

    # Get the time in minutes
    final_time = datetime.datetime.now()
    dt = (final_time - start_time).total_seconds() / 60

    # Now log the time
    logger.info('jobid {} completion time: {} min'.format(jobid, dt))


def formatDate(dstr):
    """Summary

    Args:
        dstr (TYPE): Description

    Returns:
        TYPE: Description
    """
    if type(dstr) == str:
        return datetime.datetime.strptime(dstr, '%Y-%m-%d')
    if type(dstr) == datetime.datetime:
        return dstr


def GenericWrite(readpath, replacedata, writepath):
    """Summary
    Path to file to read
    Data dictionary to put into file
    Path to the write out file
    Args:
        readpath (TYPE): Description
        replacedata (TYPE): Description
        writepath (TYPE): Description
    """

    with open(readpath, 'r') as file:
        filedata = file.read()
        #
        # loop thru dictionary and replace items
    for item in replacedata:
        filedata = filedata.replace(item, str(replacedata[item]))  # make sure it's a string

    # Write the file out again
    with open(writepath, 'w') as file:
        file.write(filedata)
    # done


def ForwardModel(directory,
                 userid,
                 catchid,
                 check_file,
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

    # Move directories and submit the job...
    os.chdir(directory)
    jobid, err = Submit('submit.sh', catchid)
    time.sleep(1)

    # Wait for the job to complete
    WaitForJob(jobid, userid)

    # Verify that the model worked...
    logger.info('done waiting...')
    success = checkFile(check_file)

    # Verify that the model worked...
    if success:
        logger.info(
            'Found last chrt file--assume the model finished successfully')
        return True
    else:
        logger.info('{} not found. assume model run \
                    failed. exiting'.format(check_file))
        return False
