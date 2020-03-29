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


logger = logging.getLogger(__name__)


class Validation(SetMeUp):

    """Summary
    """

    def __init__(self, setup):
        """Summary

        Args:
            setup (TYPE): Description
        """
        # get all of the methods from SetMeUp...
        super(self.__class__, self).__init__(setup)
        vd = self.val_end_date
        self.final_val_file = Path(self.chrtfmt.format(vd.strftime("%Y"),
                                                       vd.strftime("%m"),
                                                       vd.strftime("%d"),
                                                       vd.strftime("%H")))
        # link to the correct database name
        self.database_name = 'Validation.db'
        self.database = self.valdirc.joinpath(self.database_name)
    
    def PrepareValidation(self):
        """Summary
        Create run directory for the calibration run
        """
        logger.info('~~~~ Prepare Validation directory ~~~~')
        linkForcings = self.GatherForcings(self.val_start_date,
                                           self.val_end_date)

        # provide the directory path and the forcings to link
        self.CreateRunDir(self.valdirc, linkForcings)

        # create the ...
        self.CreateNamelist(self.valdirc,
                            self.val_start_date,
                            self.val_end_date)

        self.CreateSubmitScript(self.valdirc)
        self.GatherObs(self.valdirc,
                       self.val_start_date,
                       self.val_end_date)

        # self.CreateAnalScript(self.valdirc, 'Validation.db')

        # Log the USGS observations to the database...
        obsQ, lat, lon = dbl.readObsFiles(self.valdirc)
        table_name = 'qObserved'
        dbl.logDataframe(obsQ,
                         table_name,
                         self.database)

        # Database parsing functions
    def getParameters(self, dbcon):
        """Summary
        Returns a pandas da`taframe of parameters that have been actively
        calibrated.
        Args:
            dbcon (TYPE): path/name of the calibration directory

        Returns:
            param (pandas.dataFrame): dataframe of calibration parameter values
        """

        param_cmd = "SELECT * FROM PARAMETERS WHERE calib_flag = 1"
        param = pd.read_sql(sql=param_cmd, con="sqlite:///{}".format(dbcon))
        return param

    def getPerformance(self, dbcon):
        """Summary

        Args:
            dbcon (TYPE): Description

        Returns:
            perf (pandas.dataFrame): Description
        """
        perf_cmd = "SELECT * FROM Calibration"
        perf = pd.read_sql(sql=perf_cmd, con="sqlite:///{}".format(dbcon))
        return perf

    def returnQmodOnly(self, dbcon):
        """Summary
        only use this when there is just one iteration

        Args:
            dbcon (TYPE): Description

        Returns:
            mod (pandas.dataFrame): Description
        """
        mod_cmd = "SELECT * FROM Modout"
        mod = pd.read_sql(sql=mod_cmd, con="sqlite:///{}".format(dbcon))
        mod['time'] = pd.to_datetime(mod['time'])
        mod['type'] = 'WRF_Hydro V5'
        return mod

    def LogData(self):
        # dataframe --> sql database
        paramDic = {'Iteration': [str(self.iters)],
                    'Objective': [self.obj],
                    'Improvement': [self.improvement]}

        paramDic.update(self.performance)
        print(paramDic)
        pdf = pd.DataFrame(paramDic)
        pdf.set_index('Iteration', inplace=True)
        dbl.logDataframe(pdf, 'Validation', self.valdirc)

    # Read the parameter sets....
    def get_best_parameters(self):
        """Summary
        Read the calibration database and find the best parameter set
        create new netcdf files with those parameters
        """

        path_to_original_files = self.parmdirc
        path_to_output_files = self.valdirc.joinpath('DOMAIN')
        calib_params = self.clbdirc.joinpath(self.parameter_table)
        database = self.clbdirc.joinpath('Calibration.db')

        # Begin....
        param = self.getParameters(database)
        param.Iteration = list(map(int, param.Iteration))
        performance = self.getPerformance(database)
        best_row = performance.loc[(performance.Objective == performance['Objective'].min()) & (
            performance.Improvement == 1)]
        best_parameters = param.loc[param.Iteration == int(best_row.Iteration)]
        best_parameters.set_index('parameter', inplace=True)

        # Read the calibration table
        clb = pd.read_csv(calib_params, delimiter=' *, *', engine='python')
        clb.set_index('parameter', inplace=True)
        grouped = clb.groupby('file')
        ncList = grouped.groups.keys()

        # Open each file once and adjust the paremater values
        for ncSingle in ncList:
            UpdateMe = xr.open_dataset(
                path_to_original_files.joinpath(ncSingle))
            # This is kinda dumb.... we can't overwrite the file
            os.remove(path_to_output_files.joinpath(ncSingle))

            # But we only want to deletete the ones that get updated
            for param in grouped.groups[ncSingle]:
                if param in list(best_parameters.index):
                    updateFun = acc.AddOrMult(clb.loc[param].factor)
                    dims = clb.loc[param].dims
                    updateVal = best_parameters.loc[param].currentValue
                    # apply logic to update w/ the correct dims
                    if dims == 1:
                        UpdateMe[param][:] = updateFun(
                            UpdateMe[param][:], updateVal)
                    if dims == 2:
                        UpdateMe[param][:, :] = updateFun(
                            UpdateMe[param][:, :], updateVal)
                    if dims == 3:
                        UpdateMe[param][:, :, :] = updateFun(
                            UpdateMe[param][:, :, :], updateVal)
            UpdateMe.to_netcdf(path_to_output_files.joinpath(ncSingle))
            UpdateMe.close()

    def run_validation(self):
        """
        Perform the 'Validation' experiment
        """

        # Create the val directory if it doesn't exist...
        if not self.valdirc.exists():
            self.valdirc.mkdir()


        # Part 1: Run the std. parameters for the val period
        # --------------------------------------------------
        logger.info('Calling Model Validation Run-- Baseline')
        base = self.valdirc.joinpath('baseline')
        linkForcings = self.GatherForcings(self.val_start_date,
                                           self.val_end_date)

        self.CreateRunDir(base, linkForcings)
        self.CreateNamelist(base, self.val_start_date, self.val_end_date)
        self.CreateSubmitScript(base)
        self.GatherObs(base, self.val_start_date,
                       self.val_end_date)

        self.CreateAnalScript(base, 'Validation.db', 0)

        # Move to the directory and call the run
        success = acc.ForwardModel(base,
                                   self.userid,
                                   self.catchid,
                                   self.final_val_file)

        if not success:
            logger.error('Model run fail. check {}'.format(base))
            sys.exit()

        # Part 2: Run the calibrated parameters
        # for the val period
        # -------------------------------------
        logger.info('Calling Model Validation Run-- Calibrated')
        base = self.valdirc.joinpath('calibrated')
        linkForcings = self.GatherForcings(self.val_start_date,
                                           self.val_end_date)

        self.CreateRunDir(base, linkForcings)
        self.CreateNamelist(base)
        self.CreateSubmitScript(base)
        self.GatherObs(base, start_date=self.val_start_date,
                       end_date=self.val_end_date)

        self.CreateAnalScript(base, 'Validation.db', 0)

        # Move to the directory and call the run
        success = acc.ForwardModel(base,
                                   self.userid,
                                   self.catchid,
                                   self.final_val_file)
        
        if not success:
            sys.exit('Model run fail. check {}'.format(base))
