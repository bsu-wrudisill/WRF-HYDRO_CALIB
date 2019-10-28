# WRF-HYDRO_CALIB (BETA)
Author: Will Rudisill, Boise State University

Email: williamrudisill@u.boisestate.edu


# Description
WRF-HYDRO_CALIB employs the **'Dynamic Dimensional Search' (DDS)** (1) automatic parameter optimization algorithm the WRF-Hydro hydrologic model. 
One of the goals was to keep the directory structure as simple and transparent as possible,
so that it's easier to debug should things go wrong. The user is responsible for editing only two additional config files 
(described below) beyond the normal *namelist* files. Currently the code tunes land surface and routing paramters to match observed
discharge using the kling-gupta-efficiencty objective function. It would be relatively easy to implement a different calibration for 
another state variable such as soil moisture or SWE. 

This code is designed to work on HPC systmes that use the SLURM job scheduling system (It would be relatively trivial to port
to another job scheduler system). The heavy compute tasks are submitted to the job scheduler. Here is a general overview of what the code does, in order:

1. Create a run directory (copy executables, forcing files, etc.) using paths supplied in the config file
2. Download USGS streamflow data for the correct gauge station and time period 
3. Perform basic checks of model run sanity
4. Submit the model job to the sheduler and wait for completion
5. Record the model performance compared to stream observations (apply the Kling-Gupta Efficiency objective function). This step also submitted as a queue job 
6. Update model parameters according to DDS methodology 
7. Log parameter updates, model output time series, and objective function value to a database file. 
8. Repeat steps 4-7 *n* times; the more the better
`

# Software Requirements 
1) WRF-Hydro V5
2) Python 3.7
3) R 3.5.2 


WRF-Hydro must be compiled successfully before using. It is a good idea to double check the build with a test case before trying to calibrate.
The calibration scripts use Python for almost everything, including logging, file moving, opening/closing netcdf files, and plotting. The only requirement for R is the USGS data retrieval package, which is unfortunately the easiest way do download 
USGS station data and metadata (http://usgs-r.github.io/dataRetrieval/). 


# Setup
1. Edit the **setup.yaml** in the parent directory. The variable names should be explanatory. They include pointers to where the wrf hdyro executable lives, the parameter files, the name to append to the calibration directory, and the USGS gauge ID to calibrate to. The code will automatically find the correct channel location point to use. For multiple basins, I would reccomend naming the setup.yaml something else (such as setup.yaml.basin_name, and then creating a symlink to that file. 

For example:
```bash
ln -s setup.yaml.basin_name setup.yaml
```

2. Edit the namelist TEMPLATE files in the **namelists/**. Do not change the dates or the file paths -- these get edited by the run code. 

3. Edit the **calib_params.tbl** file. Set the 'calib_flag' to 1 in to calibrate the parameter. Parameters in the table with a 
zero value are not calibrated. Each parameter can be tuned by either an additive or a multiplicative factor. The ranges of which are set by the 'min' and 'max columns.

You are now ready to run. The code has some functions to check for obvious mistakes (such as incorrect filepaths), but not everything will be caught at the beginning. 

# Run  
To run the calibration, do the following:
```bash
source env.sh
conda activate WRFDev
python calibrate.py 
```

### Post Processing
There are a number of visualization scripts found in the **/lib/python/viz directory**. All of the relevant information for plotting the model performance is contained in the database directory (the model outputs for each iteration, the objective function value for that iteration, and the model parameters). The python pandas library can easily read data from the CALIBRATION.db file. Additionally, there are a number of applications that can examine sql databases, such as https://sqlitebrowser.org/. Sqlite browser also offers basic plotting capablities whcih are handy for getting a quick view of the data. 

### Creating the calibrated parameter files 
Once the calibration is sufficiently 'finished', use the **createCalibratedParams.py** script, found in the **/util** directory. The parameter files are overwritten for each calibration iteration, so at the end of the calibration the optimal parameter set must be recreated by applying the optimal set of multipliers/addends. 



# Dealing with errors
First, check the logfile. On issuing the calibration run, a logfile gets created with the current timestamp. Any errors that 
have occurred will be in this file. If there is something wrong with the model configuration that causes results in model outputs not being generated, the python process will not necessarily catch this error (but it will stop after a maximum of three model failures). Navigate to the model run directory and read the slurm log files that. These will contain debug information from the **wrf_hydro.exe** execution. 

If model files are not being generated, then verify that the model run settings are working. The calibration run directory is self-contained with everything needed to run the model. This provides a nice way to debug -- simply navigate to this directory, modify namelist parameters as needed to fix whatever setting is 'off', and re-run the model by issuing 'sbatch submit.sh'. 

# Restarting Failed Runs 
By default, the calibration routing will quit after three errors are raised in a row. This could happen for a variety of reasons. If you are certain that the failures are caused by something on the HPC system, and not a bug in the calibration scripts or WRF-Hydro itself, then you can restart a failed run from where it left of.  Use the **restart.py** script:
```bash
conda activate WRFDev
python restart.py
```
The script will read the setup.yaml file to find the run directory and the calibration database file. Restarting the run requires that the databse file and run directories exists and have not been modified. 



# Bugs/Feature Requests
If there are problems, bugs, or things that are unclear, create an 'issue' on this github page. Please copy/paste the relevant lines of the log file or the error message in the standard out. 

# References
1. Tolson, Bryan A., and Christine A. Shoemaker. "Dynamically dimensioned search algorithm for computationally efficient 
watershed model calibration." Water Resources Research 43.1 (2007).


