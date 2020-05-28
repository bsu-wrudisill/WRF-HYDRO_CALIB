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
        self.baseline = self.valdirc.joinpath('baseline')
        self.calibrated = self.valdirc.joinpath('calibrated')

    def PrepareValidation(self):
        """Summary
        Create run directory for the calibration run

        /Validation
            |__ baseline/
            |__ calibrated/

        """
        logger.info('~~~~ Prepare Validation/baseline directory ~~~~')
        self.valdirc.mkdir(exist_ok=True)

        # get the correct forcings...
        linkForcings = self.GatherForcings(self.val_start_date,
                                           self.val_end_date)

        # Create the 'Baseline' directory
        # -------------------------------
        self.CreateRunDir(self.baseline, linkForcings)
        self.CreateNamelist(self.baseline,
                            self.val_start_date,
                            self.val_end_date)

        self.CreateSubmitScript(self.baseline)
        self.GatherObs(self.baseline,
                       self.val_start_date,
                       self.val_end_date)

        self.CreateAnalScript(self.baseline, self.database, 0)
        obsQ, lat, lon = dbl.readObsFiles(self.baseline)
        table_name = 'qObserved'
        dbl.logDataframe(obsQ,
                         table_name,
                         self.database)

        # Create the 'Calibrated' directory
        # -------------------------------
        logger.info('~~~~ Prepare Validation/calibrated directory ~~~~')

        self.CreateRunDir(self.calibrated, linkForcings)
        self.CreateNamelist(self.calibrated,
                            self.val_start_date,
                            self.val_end_date)

        self.CreateSubmitScript(self.calibrated)
        self.GatherObs(self.calibrated,
                       self.val_start_date,
                       self.val_end_date)

        self.CreateAnalScript(self.calibrated, self.database, 1)
        # Done setting up.... no need to download obs twice

        # get the best parameter files... append them to the domain files in
        # the 'calibrated' directory
        logger.info('calling get_best_parameters')
        self.get_best_parameters()


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
        paramDic = {'Iteration': [str(self.iteration)],
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
        logger.info('find the optimal parameters from calibration run...')
        path_to_original_files = self.parmdirc
        path_to_output_files = self.calibrated.joinpath('DOMAIN')
        calib_params = self.clbdirc.joinpath(self.parameter_table)
        database = self.clbdirc.joinpath('Calibration.db')

        # Begin....
        param = self.getParameters(database)
        print(param)
        param.Iteration = list(map(int, param.iteration))
        performance = self.getPerformance(database)
        print(performance) 
        
        best_row = performance.loc[(performance['objective'] == performance['objective'].min()) & (
            performance['improvement']== 1)]
        best_parameters = param.loc[param['iteration'] == int(best_row['iteration'])]
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

        # Part 1: Run the std. parameters for the val period
        # --------------------------------------------------
        # Move to the directory and call the run
        success = acc.ForwardModel(self.baseline,
                                   self.userid,
                                   self.catchid,
                                   self.final_val_file)
        if not success:
            logger.error('Model run fail. check {}'.format(self.baseline))
            sys.exit()

        # Part 2: Run the calibrated parameters
        # -------------------------------------
        logger.info('Calling Model Validation Run-- Calibrated')

        # Move to the directory and call the run
        success = acc.ForwardModel(self.calibrated,
                                   self.userid,
                                   self.catchid,
                                   self.final_val_file)
        if not success:
            sys.exit('Model run fail. check {}'.format(self.calibrated))



    def aggregate_results(self):
        """
        """
        # Log the validation (baseline) run
        cwd = os.getcwd()
        self.CreateAnalScript(self.baseline,
                              self.database,
                              0,
                              'baseline') 
        os.chdir(self.baseline)
        jobid, err = acc.Submit('submit_analysis.sh', self.catchid)


        # Log the validation (calibrated) run
        self.CreateAnalScript(self.calibrated,
                              self.database,
                              0,
                              'calibrated') 
        
        os.chdir(self.calibrated)
        jobid, err = acc.Submit('submit_analysis.sh', self.catchid)

        #go back to orig directory
        os.chdir(cwd)


