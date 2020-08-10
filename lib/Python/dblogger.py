import sys
from sqlalchemy import create_engine
import pandas as pd
import accessories as acc
import logging
#from fastread import test
import pathlib
from datetime import datetime
import xarray as xr
import os
logger = logging.getLogger(__name__)


"""
Read csv files and model outputs
"""


def readObsFiles(directory, filename='obsStrData.csv'):
        """Summary
        Args:
            directory (TYPE): Description
            filename (str, optional): Description
        """
        # Read USGS observations
        obsQ = pd.read_csv(directory.joinpath('obsStrData.csv'))
        obsQ.drop(columns=['Unnamed: 0', 'POSIXct', "agency_cd"], inplace=True)
        obsQ.rename(index=str, columns={
                    "Date": "time", "obs": "qObs"}, inplace=True)
        obsQ.set_index('time', inplace=True)
        obsQ.index = pd.to_datetime(obsQ.index)
        # find the length between the dates --- this could be different than
        # the time index if there are missing dates in the observations
        idx = pd.date_range(obsQ.index[0], obsQ.index[-1])

        # Check if there are missing times from the observations ...
        if len(idx) != len(obsQ.index):
            missing_list = [str(i) for i in idx if i not in obsQ.index]
            message = 'Missing the following dates: {}. Applying interpolation'.format(
                missing_list)
            logger.info(message)

        # Reindex and interpolate
        obs = obsQ.reindex(idx)
        obs_interpolate = obs.interpolate()
        obs_interpolate['time'] = idx
        lat = obsQ['lat'].iloc[0]
        lon = obsQ['lon'].iloc[0]

        # Return the observation dataframe and the lat/lon gaugel location
        return obs_interpolate, lat, lon


def readChRtFiles(directory='./', use_xarray=True):
    """Summary

    Logs obs/modelout to the calibration sql database
    Also finds the correct USGS gauge location
    Ideally this gets run on a compute node, not head

    Args:
        directory (str or pathlib.Path): Directory where model files live
        use_xarray (bool, optional): Determines which method to use  for t
                                     the read step. If false, uses a fortran
                                     script and writes a .txt output file...
                                     somewhat of a kluge. xarray takes a while.
    Returns:
        modQdly (pandas.DataFrame) : A dataframe containign the data variables,
                                     aggregated to a daily timestep.


    Other Requirements (located in directory path):
            *CHROUT* file(s)
            obsStrData.csv file
        Optional:
            gauge_loc.txt file
    """

    if type(directory) != pathlib.PosixPath:
        directory = pathlib.Path(directory)
    
    # Look for gauge location file
    chrtFiles = list(directory.glob('*CHRTOUT_DOMAIN*'))

    # Look for the gauge location file, if it exists
    glocfile = directory.joinpath('gauge_loc.txt')
    if glocfile.exists():
        logger.info('reading gauge loc from txt file...')
        with open('gauge_loc.txt', 'r') as f:
            gauge_loc = int(f.readline())
            print(gauge_loc)

    # Find the correct gauge ID and write one for later use...
    else:
        obs, lat, lon = readObsFiles(directory)
        gauge_loc = acc.GaugeToGrid(chrtFiles[0], lat, lon)
        logger.info('gauge_loc is ... {}'.format(gauge_loc))
        with open('gauge_loc.txt', 'w') as f:
            f.write(str(gauge_loc))
        f.close()

    # Two read options: use Xarray or use the Fortran read/write script
    # Fortran would seem to be faster but not as elegant...

    # Option 1: Use Xarray
    # ---------------------
    if use_xarray:
        modQfiles = xr.open_mfdataset(chrtFiles, concat_dim="time")
        # Parse the xrarray data
        data_dict = {'qMod': modQfiles['streamflow'][:, gauge_loc].values,
                     'time': modQfiles['time'].values}

        qDf = pd.DataFrame(data_dict)
        qDf.set_index('time', inplace=True)

        # Now resample the data to a daily timestep...
        modQdly = pd.DataFrame(qDf.resample('D').mean())
    
    # Option 2: Use fortran function to write discharge as a .txt file
    # ----------------------------------------------------------------
    else:
        # TODO !!! FIX THIS PATH!!!!!
        libPath = '/home/wrudisill/scratch/WRF-HYDRO_CALIB/lib/fortran'
        sys.path.insert(0, libPath)

        # Run the fortan script ....
        txtfile = 'modelstreamflow.txt'
        outputfile = directory.joinpath(txtfile)

        if outputfile.exists():
            message = 'removing previous file\n {}'.format(outputfile)
            logger.warning(message)
            os.remove(outputfile)

        # TODO !!! CHANGE ME !!!
        n = 752
        timelist = []
        logger.info('Read data from output files...')

        # Loop through the Q files and write the gauge loc point
        # to a .txt file
        for f in chrtFiles:
            test.readnc(f, gauge_loc, n, outputfile)
            time = f.name.split('.')[0]
            time_raw = datetime.strptime(time, "%Y%m%d%H%M")
            timelist.append(time_raw)

        # Read the written in the previous step
        qDf = pd.read_csv(outputfile, sep=',', names=['fname', 'qMod'])
        qDf['time'] = pd.to_datetime(timelist)
        qDf = qDf.set_index('time')
        del qDf['fname']

        # Now resample the data to a daily timestep...
        modQdly = pd.DataFrame(qDf.resample('D').mean())
    # Done reading model files
    # ------------------------
    return modQdly


"""
SQL methods
"""


def logDataframe(df, table_name, database):
    """Summary
    Args:
        df (pandas.DataFrame): data frame containing the data to log
        table_name (string): The tile of the SQL table name
        database (pathlib.Path or str): Full Path to the Calibration Database
    """

    # Path to database file; a little wonky...
    logger.info('database location: {}'.format(database))
    _dbengine = 'sqlite:///{}'.format(database._str)
    engine = create_engine(_dbengine, echo=False)

    # Log the dataframe
    df.to_sql(table_name,
              con=engine,
              if_exists='append')


def readSqlDischarge(database, iteration):
    '''
    Description: Creates a pandas dataframe of merged
                 model and observed states from the
                 SQL database.

    Args:
        iteration (integer): Current model iteration
        database (str): Name of the database file

    Returns:
        Pandas dataframe of model and observed data
        for the iteration input.

    '''
    # convert
    #if type(database) == pathlib.PosixPath:
    #    database = database._str

    _dbengine = "sqlite:///{}".format(database)

    # Read model states
    mod_cmd = "SELECT * FROM qModeled WHERE iteration = {}".format(iteration)
    mod = pd.read_sql(sql=mod_cmd, con=_dbengine)
    mod['time'] = pd.to_datetime(mod['time'])

    # Read observation stattes
    obs_cmd = "SELECT * FROM qObserved"
    obs = pd.read_sql(sql=obs_cmd, con=_dbengine)
    obs['time'] = pd.to_datetime(obs['time'])
    obs.drop(columns=['site_no'], inplace=True)

    # Merge the databases and assign index
    merged = obs.copy()
    merged['qMod'] = mod['qMod']
    merged.dropna(inplace=True)
    merged.set_index(merged.time, inplace=True)

    # Return
    return merged

