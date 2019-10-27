# WRF-HYDRO_CALIB
Author: Will Rudisill, Boise State University

Email: williamrudisill@u.boisestate.edu


# Decription
WRF-HYDRO_CALIB employs the 'Dynamic Dimensional Search' (DDS) automatic parameter optimization algorithm the WRF-Hydro hydrologic model. 
One of the goals was to keep the directory structure as simple and transparent as possible,
so that it's easier to debug should things go wrong. The user is responsible for editing only two additional config files 
(described below) beyond the normal *namelist* files. Currently the code tunes land surface and routing paramters to match observed
discharge using the kling-gupta-efficiencty objective function. It would be relatively easy to implement a different calibration for 
another state variable such as soil moisture or SWE. 


# Requirements 
1) WRF-Hydro V5 (MORE)
2) Python 3.+  (MORE)
3) R (MORE) 


WRF-Hydro must be compiled successfully before using. It is a good idea to double check the build with a test case before trying to calibrate.
The calibration scripts use Python for almost everything, including logging, file moving, opening/closing netcdf files, and plotting. 


# Setup
1. Edit the **setup.yml** in the parent directory. The variable names should be explanatory. They include pointers to where the wrf hdyro
executable lives, the parameter files, the name to append to the calibration directory, and the USGS gauge ID to calibrate to. The code
will automatically find the correct channel location point to use. 

2. Edit the namelist TEMPLATE files in the **namelists/**. Do not change the dates or the file paths -- these get edited by the run code. 

3. Edit the **calib_params.tbl** file. Set the 'calib_flag' to 1 in to calibrate the parameter. Parameters in the table with a 
zero value are not calibrated. Each parameter can be tuned by either an additive or a multiplicative factor. The ranges of which are 
set by the 'min' and 'max columns.

You are now ready to run. The code has some functions to check for obvious mistakes (such as incorrect filepaths), but not everything
will be caught at the beginning. 

# Setup
To run the calibration, do the following:
```bash
source env.sh
conda activate WRFDev
python calibrate.py 
```

# References
1. Tolson, Bryan A., and Christine A. Shoemaker. "Dynamically dimensioned search algorithm for computationally efficient 
watershed model calibration." Water Resources Research 43.1 (2007).


