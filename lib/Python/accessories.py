import os
import datetime
import subprocess
import time
import glob
import xarray as xr
import numpy as np
import traceback
import logging
import secrets
import string
import threading
import sys

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
                  "log_wrf_*", "analysis_*"]

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



def DateGenerator(start_date, end_date, chunk_size):
    """
    Creates a lsit of dates between start_date, end_date, by interval of
    length 'chunk_size'
    :param      start_date:  The start date
    :type       start_date:  pd.datetime object
    :param      end_date:    The end date
    :type       end_date:    pd.datetime.object
    :param      chunk_size:  The chunk size in units of days
    :type       chunk_size:  intger
    :returns:   { description_of_the_return_value }
    :rtype:     { return_type_description }
    """
    if end_date <= start_date:
        logger.error("{} LTE {}".format(end_date, start_date))
        sys.exit()

    # WRF run time
    delta = datetime.timedelta(days=chunk_size)     # length of WRF runs
    DateList = [start_date]                         # list of dates

    # Round to nearest h=00":00 to make things nicer
    if start_date.hour != 0:
        round_up_hour = 24 - start_date.hour
        DateList.append(start_date + datetime.timedelta(hours=round_up_hour))

    # Now create list of <start> <end> date pairs
    next_date = DateList[-1]
    while (next_date + delta) < end_date:
        next_date = next_date + delta
        DateList.append(next_date)

    # Append final date
    DateList.append(end_date)

    # Update list and return. Contains (date_i,date_i+1)
    zippedlist = zip(DateList[:-1], DateList[1:])
    return zippedlist


def DateParser(obj, **kwargs):
    """
    Parse a date string into a useable format, using a known list
    of date string types (which can also be passed in as kwarg)
    :param      obj:         The object
    :type       obj:         str
                             pandas._libs.tslibs.timestamps.Timestamp
                             datetime.datetime
    :param      kwargs:      "format=<parsable by strptime()>"
    :type       kwargs:      dictionary
    :returns:   Formatted date object
    :rtype:     pandas._libs.tslibs.timestamps.Timestamp OR
                datetime.datetime
    :raises     Exception:    String format not parsable using listed methods
    :raises     ValueError:   Input type is something other than <str>
    """
    import pandas as pd
    # interpred the date type of an object. return the appropriate format
    acceptable_string_formats = ["%Y-%m-%d",
                                 "%Y-%m-%d %H",
                                 "%Y %m %d %H",
                                 "%Y-%m-%d_%H",
                                 "%Y-%m-%d-%H",
                                 "%Y-%m-%d:%H",
                                 "%Y-%m-%d:%H:00",
                                 "%Y-%m-%d:%H:00:00"]

    last_chance = len(acceptable_string_formats) - 1

    if type(obj) == str:
        for chance, asf in enumerate(acceptable_string_formats):
            try:
                return datetime.datetime.strptime(obj, asf)
            except ValueError:
                if chance == last_chance:
                    raise Exception("Not acceptable string format")

    if type(obj) == pd._libs.tslibs.timestamps.Timestamp:  # ugh that's dumb
        return obj

    if type(obj) == datetime.datetime:
        return obj

    else:
        raise ValueError("type ({}) not accepted".format(type(obj)))



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
        if qerr:
            error = qerr.decode("utf-8")
            # Check QSTAT Error
            if error != '':  # the error string is non-empty
                qstat_error = True
                logger.error("Error encountered in qstat:\n    {}".format(error))
                # set the qstat error to true; we cant exit if it is
            else:
                qstat_error = False

        # no error thrown at all..
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


def string_gen(N):
    """Summary
    Create a random string sequence
    Args:
        N (TYPE): Description
    """
    letters = string.ascii_uppercase
    numbers = string.digits
    random = [secrets.choice(letters + numbers) for i in range(N)]
    res = ''.join(random)
    return res


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


def multi_thread(function, mappable, thread_chunk_size=5):
    """
    Use with caution-- not working. Generic function applies given function to
    a list, where a list item is the ONLY input arg to that function.
    :param      function:  The function
    :type       function:  { type_description }
    :param      mappable:  The mappable
    :type       mappable:  { type_description }
    :returns:   { description_of_the_return_value }
    :rtype:     { return_type_description }
    """

    def divide_chunks(l, n):
        # looping till length l
        for i in range(0, len(l), n):
            yield l[i:i + n]

    # Create a list of lists
    chunked_list = list(divide_chunks(mappable, thread_chunk_size))

    # loop thru the chunked list. max of <thread_chunk_size> threads get opened
    for chunk in chunked_list:
        threads = [threading.Thread(target=function, args=(item,))
                   for item in chunk]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()  #


def test():
    logger.info('log')
    print('here i am')


def AssembleSubmitString(nodes,
                         mpi_tasks,
                         queue,
                         run_time,
                         executable='./wrf_hydro.exe',
                         jobname='wrf_hydro',
                         logname='log_wrf_hydro.o%j'):
    """Summary

    Args:
        nodes (TYPE): Description
        mpi_tasks (TYPE): Description
        queue (TYPE): Description
        run_time (TYPE): Description
        jobname (str, optional): Description
        logname (str, optional): Description
    """
    shebang = "#!/bin/bash \n"
    template = "SBATCH -{} {} \n"

    # build the string ...
    string = shebang
    string += template.format("-J", jobname)
    string += template.format("-o", logname)
    string += template.format("-n", mpi_tasks)
    string += template.format("-N", nodes)
    string += template.format("-p", queue)
    string += template.format("-t", run_time)

    # body
    string += "module purge \n"
    string += "source ./env_nwm_r2.sh \n"
    string += "mpirun -np {} {} \n".format(mpi_tasks, executable)
    string += "exit"

    # Done
    return string


@passfail
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
    cwd = os.getcwd()
    logger.info('Calling Forward Model')

    # Move directories and submit the job...
    os.chdir(directory)
    jobid, err = Submit('submit.sh', catchid)
    time.sleep(1)

    # Wait for the job to complete
    WaitForJob(jobid, userid)

    # Verify that the model worked...
    logger.info('Done waiting...')
    success = checkFile(check_file)

    # Move back to the parent directory...
    os.chdir(cwd)

    # Check success message ...
    if success:
        logger.info(
            'Found last chrt file--assume the model finished successfully')
        return True
    else:
        logger.info('{} not found. assume model run \
                     failed. exiting'.format(check_file))
        return False
