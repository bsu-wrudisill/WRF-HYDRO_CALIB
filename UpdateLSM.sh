#!/bin/bash

# script to turn select HRLDAS LSM fields into WRF Restart (or wrfinput) file


VARLIST=SNOW,SNOWH,SNOWC,TSNO,TSLB,SH20,SMOIS,SNILIQ,SOIL_T,SNOW_T
ncks -A -v $VARLIST -d Time,1 $INIT_FILE $outfile
