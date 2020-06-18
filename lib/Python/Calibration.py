import yaml
import os
import sys
import logging
import pandas as pd
import dblogger as dbl
import numpy as np
import xarray as xr
import datetime
from pathlib import Path
from SetMeUp import SetMeUp
import ObjectiveFunctions as OF
import accessories as acc

logger = logging.getLogger(__name__)

class Calibration(SetMeUp):
    """
    The "Calibration" class. This requires a "setup" object
    (created above) to be passed in. This object will 1) submit
    batch jobs to run WRF-Hydro, 2) submit (and create) the analysis
    job, 3) evaluate objective functions, 4) implement the DDS
    selection algorithm, and 5) update model parameter files according
    to the DDS rule, and 5) log items to a SQL database

    Attributes:
        ALG (str): Description
        bestObj (float): Description
        dbcon (TYPE): Description
        df (TYPE): Description
        improvement (TYPE): Description
        iteration (int): Description
        obj (TYPE): Description
        paramDir (TYPE): Description
        performance (TYPE): Description
    """

    def __init__(self, setup):
        """Summary

        Args:
            setup (TYPE): Description

        """

        # Get all of the methods from SetMeUp __init__ method
        # ----------------------------------------------------
        super(self.__class__, self).__init__(setup)

        # Parameters assosicated with the calibration
        self.iteration = 0  # keep track of the iterations of calib.ation
        self.bestObj = 1e16            # intialize the 'best ojective'
        self.objective = self.bestObj  # initialize the obective function state
        self.paramDir = self.clbdirc.joinpath('DOMAIN')
        self.database_name = 'Calibration.db'
        self.database = self.clbdirc.joinpath(self.database_name)

        # Database file
        # Temporary variable... makes following lines shorter...
        ed = self.calib_end_date
        self.final_chrtfile = Path(self.chrtfmt.format(ed.strftime("%Y"),
                                                       ed.strftime("%m"),
                                                       ed.strftime("%d"),
                                                       ed.strftime("%H")))
        # 'failed iteration counter'
        self.failed_iterations = 0

    def PrepareCalibration(self):
        """Summary
        Create run directory for the calibration run
        """
        logger.info('~~~~ Prepare Calibration directory ~~~~')
        linkForcings = self.GatherForcings(self.calib_start_date,
                                           self.calib_end_date)

        # Create the run directory...
        self.CreateRunDir(self.clbdirc,
                          linkForcings)

        self.CreateNamelist(self.clbdirc,
                            self.calib_start_date,
                            self.calib_end_date)

        # create submit script..
        self.CreateSubmitScript(self.clbdirc)

        # Get the USGS gauge observations...
        self.GatherObs(self.clbdirc,
                       self.calib_start_date,
                       self.calib_end_date)

        self.CreateAnalScript(self.clbdirc, 'Calibration.db', self.iteration)

        logger.info(self.clbdirc)
        # Log the USGS observations to the database...
        obsQ, lat, lon = dbl.readObsFiles(self.clbdirc)
        table_name = 'qObserved'
        dbl.logDataframe(obsQ,
                         table_name,
                         self.database)

    def AdjustCalibTable(self):
        """
        Change the limits of the 'cali_params.tbl' so that the values do not exceed
        predefined limits
        """
        grouped = self.df.groupby('file')
        ncList = grouped.groups.keys()
        logger.info('------------ Adjust Calibration Table based on min/max values of parameters ----------')
        # Loop through files
        logger.info(self.df)
        for ncSingle in ncList:
            ncfile = self.parmdirc.joinpath(ncSingle)
            readMe = xr.open_dataset(ncfile)

            # loop through individual parameters
            for param in grouped.groups[ncSingle]:
                
                logger.info("\n##################")
                logger.info(param)
                logger.info("##################")


                # determine the max value of the parameter file
                real_param_max = readMe[param].values.max()
                real_param_min = readMe[param].values.min()
                
                logger.info("Max value in orig param file: {}".format(real_param_max))
                logger.info("Min value in orig param file: {}".format(real_param_min))
                
                # get the min/max delta values from the table
                delta_max = self.df.at[param, 'maxDelta']
                delta_min = self.df.at[param, 'minDelta']

                # get the min/max ttoal values from df
                value_min = self.df.at[param, 'minValue']
                value_max = self.df.at[param, 'maxValue']
                
                logger.info("Max value allowed in calib_params.yaml: {}".format(value_max))
                logger.info("Min value allowed in calib_params.yaml: {}".format(value_min))
                
                # Adjust the 'delta factors'
                # for the multiplicative case 
                if self.df.at[param, 'factor'] == 'mult':
                    if value_max < real_param_max:
                        logger.error('the real max value is greater than the max allowed...')
                    
                    if value_min > real_param_min:
                        logger.error('the real min value is less than the min allowed...')
                    
                    # set the values
                    # max value 
                    if real_param_max == 0:
                         new_delta_max = value_max                       
                    else: 
                         new_delta_max = value_max/real_param_max

                    # min value
                    if real_param_min == 0:
                        new_delta_min = value_min 
                    else:
                        new_delta_min = value_min/real_param_min


                # for the addative case  
                if self.df.at[param, 'factor'] == 'add':
                    new_delta_max = value_max - real_param_max
                    new_delta_min = value_min - real_param_min
                
                
                logger.info("Adjusted 'delta' values...") 
                logger.info('{} --> {}'.format(delta_max, new_delta_max))
                logger.info('{} --> {}'.format(delta_min, new_delta_min))
                
                # now adjust the calib_params.tbl...
                self.df.at[param, 'maxDelta'] = float(new_delta_max)
                self.df.at[param, 'minDelta'] = float(new_delta_min)



    def EvaluateIteration(self):
        """Summary
        Apply objective function, evaluating perfomance
        of model relative to the observations. Determine
        if the model improved or not and assign improvement
        flag to 0 or 1. Then set the 'next value' to the
        initial value

        Returns:
            TYPE: Description
        """
        # Read the model and the observed discharge
        # from SQL db into a pandas dataframe
        merged = dbl.readSqlDischarge(self.database, self.iteration)

        # Only evaluate during the evaluation period
        eval_period = merged.loc[self.ceval_start_date: self.ceval_end_date]

        # Compute the objective function(s)
        objective, corrcoef, mn, std = OF.KGE(eval_period.qMod,
                                              eval_period.qObs)
        modmin = OF.minn(eval_period.qMod, eval_period.qObs)
        modmax = OF.maxx(eval_period.qMod, eval_period.qObs)
        modrmse = OF.RMSE(eval_period.qMod, eval_period.qObs)
        modtq = OF.tq(eval_period.qMod, eval_period.qObs)
        modnse = OF.NSE(eval_period.qMod, eval_period.qObs)
        kendal = OF.kendal(eval_period.qMod, eval_period.qObs)
        spearman = OF.spear(eval_period.qMod, eval_period.qObs)

        self.performance = {'kge': [str(objective)],
                            'rmse': [str(modrmse)],
                            'nse': [str(modnse)],
                            'spearman-rho': [str(spearman)],
                            'kendal-tau': [str(kendal)],
                            'corrcoef': [str(corrcoef)],
                            'min_difference': [str(modmin)],
                            'max_difference': [str(modmax)],
                            'total_q_difference': [str(modtq)]}

        # Log the performance
        logger.info(self.performance)

        # Determine if the Objective function has improved
        improvement = 0

        # Case 1: First Iteration
        # -----------------------
        if self.iteration == 0:
            logger.info('On the first iteration')
            # this is the first iteration; we have just tested
            # the 'stock' parameters
            self.bestObj = objective
            improvement = 0

            # update the active params
            for param in self.df.groupby('calib_flag').groups[1]:
                self.df.at[param, 'bestValue'] = self.df.loc[param, 'initialValue']

            # keep the inactive params at 0
            try:
                for param in self.df.groupby('calib_flag').groups[0]:
                    self.df.at[param, 'bestValue'] = self.df.loc[param, 'initialValue']
                logger.info('we are on the first iter')
            except KeyError:
                logger.info('all parameters are active')

        # Case 2: All further iterations
        # ------------------------------
        else:
            if objective < self.bestObj:
                # Parameter improvement.
                # The 'next value' is the parameter set that
                # we just tested, so thus we assign it to the
                # 'best value' column
                improvement = 1
                self.bestObj = objective
                self.df['bestValue'] = self.df['nextValue']

                message = 'the objective fx improved \
                           on iteration {}'.format(self.iteration)
                logger.info(message)

            else:
                # No parameter improvement.
                # log and move on to the next step.
                improvement = 0
                message = 'no obj. improvement on \
                           iteration {}'.format(self.iteration)
                logger.info(message)

        # Finish....
        # ----------
        # Clean the nextvalue and onOff switches.
        # These get updated by the DDS ( or whatever alg. we chose...)
        self.improvement = improvement
        self.objective = objective
        self.df['nextValue'] = self.df['initialValue']

        return objective, improvement

    def DDS(self, r=.2):
        """Summary
        The Dynamic Dimension Search (DDS) parameter selection algorithm,
        adapted from Tolson et al. "Greedy" algorithm -- holds onto best
        parameter estimate and updates from there by adding random gaussian
        noise with a specified standard deviation and mean of zero. This
        function established the correct parameter values and saves them
        to a pandas dataframe.

        Returns:
            TYPE: Description

        Args:
            r (float, optional): scaling parameter of gaussian noise.
        """

        # Read the parameter tables.
        activeParams = list(self.df.groupby('calib_flag').groups[1])

        # Randomly select parameters to update
        prob = 1 - np.log(self.iteration + 1) / np.log(self.max_iteration + 1)

        # Determine the 'active set'
        for param in activeParams:
            sel = np.random.choice(2, p=[1 - prob, prob])
            if sel == 1:
                self.df.at[param, 'onOff'] = 1
            else:
                self.df.at[param, 'onOff'] = 0

        # The 'onOff' flag is updated for each iteration... the
        # calib_flag is not (this flag decides if we want to consider
        # the parameter at all.
        try:
            selectedParams = list(self.df.groupby('onOff').groups[1])
            deselectedParams = list(self.df.groupby('onOff').groups[0])

        except KeyError:
            # CHANGE ME --- select 1 random parameter instead
            message = 'no parameters were selected\
                       during DDS search algorithm'
            logger.warning(message)
            return

        # Determine new values for the 'Active Parameters'
        # ------------------------------------------------
        for param in selectedParams:
            # get the parameter, and the static bounds (xmin-----xmax)
            J = self.df.loc[param]
            xj_min = J.minDelta  # Note --
            xj_max = J.maxDelta  # Note --
            xj_best = J.bestValue
            xj_init = J.initialValue
           
            logger.info('------------------')
            logger.info(param)
            logger.info('xj_min:'+str(xj_min))
            logger.info('xj_max:'+ str(xj_max))
            logger.info('xj_best'+ str(xj_best))
            logger.info('xj_init:' + str(xj_init))
            logger.info('------------------')
            
            # Is this a multiplicative parameter or an additive one?
            factor = J.factor

            # Multiplicative update factor
            # ----------------------------
            if factor == 'mult':
                
                # create the standard deviation 
                sigj = r * (np.log10(xj_max) - np.log10(xj_min))

                # Randomly chosen unit normal variable
                # Recall that we are just 'scaling' the random normal variable by the given standard 
                # deviation, "sigj" with a mean shift given by the log of xj_init...
                x_update = sigj * np.random.randn(1) + np.log10(xj_init)
                x_new = xj_best * 10**x_update
                if x_new < xj_min:  # if it is less than min, reflect to middle
                    x_new = 10**(np.log10(xj_min) +
                                 (np.log10(xj_min) - np.log10(x_new)))

                # If xnew is greater than the max, reflect to middle
                if x_new > xj_max:
                    x_new = 10**(np.log10(xj_max) -
                                 (np.log10(x_new) - np.log10(xj_max)))

            # Additive update factor
            # ----------------------
            if factor == 'add':
                sigj = r * (xj_max - xj_min)
                # Randomly chosen unit normal variable
                x_update = sigj * np.random.randn(1) + xj_init
                x_new = xj_best + x_update

                # If new factor is l.t min, reflect to middle
                if x_new < xj_min:
                    x_new = xj_min + (xj_min - x_new)

                # If new factor is g.t max, reflect to middle
                if x_new > xj_max:
                    x_new = xj_max - (x_new - xj_max)

            # Assign the parameter to the 'next value'
            self.df.at[param, 'nextValue'] = np.float(x_new)

        # Keep the innactive parameters the same
        # --------------------------------------
        for param in deselectedParams:
            J = self.df.loc[param]
            xj_best = J.bestValue
            self.df.at[param, 'nextValue'] = np.float(xj_best)  # no updating

        # DDS iteration complete
        # ----------------------
        logger.info('Performed DDS update for iteration {}'.format(self.iteration))



    def UpdateParamFiles(self):
        """Summary
        Update the NC files given the adjustment parameters
        determined by the DDS algorithm or similar...
        """
        # Get the list of individual netcdf files
        grouped = self.df.groupby('file')
        ncList = grouped.groups.keys()

        # Loop through files
        for ncSingle in ncList:
            ncfile = self.clbdirc.joinpath('ORIG_PARM', ncSingle)
            UpdateMe = xr.open_dataset(ncfile)

            # Remove the old file(s) in the main parameter file
            # Directory... we overwrite w/ the update
            remove_ncfile = self.paramDir.joinpath(ncSingle)
            os.remove(remove_ncfile)

            # Loop through the params and update. write files
            for param in grouped.groups[ncSingle]:
                # returns a function (addition or multiplication) to apply
                updateFun = acc.AddOrMult(self.df.loc[param].factor)
                # get the dims of the parameter
                dims = self.df.loc[param].dims

                # Create the value for updating
                # this will include the 'initialValue' value
                updateVal = self.df.nextValue.loc[param]

                # apply logic to update w/ the correct dims
                if dims == 1:
                    UpdateMe[param][:] = updateFun(UpdateMe[param][:],
                                                   updateVal)
                if dims == 2:
                    UpdateMe[param][:, :] = updateFun(UpdateMe[param][:, :],
                                                      updateVal)
                if dims == 3:
                    UpdateMe[param][:, :, :] = updateFun(UpdateMe[param][:, :, :],
                                                         updateVal)
                # log info
                message = 'updated--{} in file \
                          {}--with value {}'.format(param, ncSingle, updateVal)
                logger.info(message)

            # done looping thru params
            # save the file now and close
            UpdateMe.to_netcdf(self.paramDir.joinpath(ncSingle), mode='w')
            UpdateMe.close()

        # update the dataframe to reflect that the
        # 'next param' values have been inserted into the current params
        self.df['currentValue'] = self.df['nextValue']

    def LogParameters(self):
        """
        Summary:
        Log the parameter values to the dataframe... so we
        know which are being calibtrated, and their value,
        for each iteration
        """

        # Build the dataframe...
        table_name = 'parameters'
        params = self.df.copy()
        params['iteration'] = str(self.iteration)
        params.drop(columns=['file', 'dims', 'nextValue'], inplace=True)

        # Log the data frame to the Calib. sql database
        dbl.logDataframe(params,
                         table_name,
                         self.database)

    def LogPerformance(self):
        """Summary
        """

        # SQL table name
        table_name = 'Calibration'

        # Build the dataframe ...
        paramDic = {'iteration': [str(self.iteration)],
                    'objective': [self.objective],
                    'improvement': [self.improvement]}

        paramDic.update(self.performance)
        pdf = pd.DataFrame(paramDic)
        pdf.set_index('iteration', inplace=True)

        # Log the dataframe to the Calib.. sql database
        dbl.logDataframe(pdf,
                         table_name,
                         self.database)
    @acc.passfail
    def OneLoop(self):
        """Summary
        Run one forward model, evaluate, DDS loop.
        """
        logger.info('Calling one loop..')
        os.chdir(self.clbdirc)

        # the last file to look for..
        final_file = self.clbdirc.joinpath(self.final_chrtfile)
        
        # Run the model once
        success, message = acc.ForwardModel(self.clbdirc,
                                   self.userid,
                                   self.catchid,
                                   final_file)
        
        # Check if the model produced the correct output
        if not success:
            self.failed_iterations += 1 
            # Since hte model failed... and presumably because the parameter set
            # was bad... lets do the DDS iteration again and find better parameters
            # generate new parameters
            self.DDS()

            # update the parameters
            self.UpdateParamFiles()  # write the new parameters to files

            # clean up the directory
            acc.CleanUp(self.clbdirc)

            # raise an an error that the final file was not found ...
            raise FileNotFoundError(final_file)
        
        # Otherwise, assume that the model run was a succes. Compute the perfomance
        # and do the DDS algorithm. 
        else:
            logger.info('Sucess. Found: {}'.format(final_file))
        
        # Model Evaluation
        # -----------------
        # This step will log the model outputs to the database
        self.CreateAnalScript(self.clbdirc,
                              self.database,
                              self.iteration)

        jobid, err = acc.Submit('submit_analysis.sh', self.catchid)
        # wait for the job to complete
        acc.WaitForJob(jobid, self.userid)
        obj, improvement = self.EvaluateIteration()
        self.LogParameters()
        self.LogPerformance()

        # --- MODEL CALIBRATION STEP
        # generate new parameters
        self.DDS()

        # update the parameters
        self.UpdateParamFiles()  # write the new parameters to files

        # clean up the directory
        acc.CleanUp(self.clbdirc)

        # move the iternal iteration state one forward
        logger.info('Completed OneLoop for iteration {}/{}'.format(self.iteration, self.max_iteration))
        self.iteration += 1

    def __call__(self):
        # usage: calib = CalibrationMaster(); calib()
        # allow 3 failures in a row-- this probably means something is wrong
        threeFailureMax = 0
        while threeFailureMax <= 3:
            # break the loop if we are at the final iter
            if self.iteration == self.max_iteration:
                break

            # Run the model and time it...
            t1 = datetime.datetime.now()
            success, status = self.OneLoop()
            t2 = datetime.datetime.now()
            dt = (t2 - t1).total_seconds() / 60  # Time in mintes..
            logger.info("Iteration {} took {} minutes".format(self.iteration, dt))

            if success:
                logger.info(status)
                threeFailureMax = 0
            if not success:
                logger.error(status)
                threeFailureMax += 1

        else:
            message = "Three failures in a row. \n Check logs for more details. \n \
                                     Exiting"
            logger.error(message)
            sys.exit()

        # done with max_iters...
        logger.info('reached max iterations')
