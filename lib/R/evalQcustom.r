# Evaluate streamflow observations
library(dataRetrieval)
library(data.table)
library(ggplot2)
library(foreach)
library(rwrfhydro)
library(dplyr)
library(lubridate)

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!#
#~~~~~~~~~~~~~~~ Part 0 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# 
#  User Parameters 
#  Usage: Rscript evalQcustom.R <dataPath> <startDate (YYYY-MM-DD)> <endDate (YYYY-MM-DD)> <USGS GageID>
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!#

# arguments
args = commandArgs(trailingOnly=TRUE)
# test if there is at least one argument: if not, return an error
if (length(args) ==0) {
	print("usage: Rscript evalQcustom.R <dataPath> <startDate> <endDate> <USGS GageID>")
        print('No input arguments provided. using defaults')
	dataPath <- '/home/wrudisill/scratch/test/WRF-HYDRO_CALIB/13235000/'
	startDate <- "2010-01-01"
	endDate <- "2010-04-10"
	gageID        <- "13235000"
	modelOutputCSV <- "discharge.csv"        # this will either be read in (if it exists) or created. Perhaps create a better name for this file 
} else {
	dataPath <- args[1]
	startDate <- args[2]
	endDate <- args[3]
	gageID  <- args[4]
	modelOutputCSV <- "WRFHydroDischarge.csv"        # this will either be read in (if it exists) or created. Perhaps create a better name for this file 
	
}

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!#
#~~~~~~~~~~~~~~~ Part 1~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# 
# read the USGS data and station information 
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!#

obsDF <- readNWISuv(siteNumbers=gageID, parameterCd="00060", startDate=startDate, endDate=endDate)  #discharge
stationInfo <- readNWISsite(siteNumbers=gageID)
requestedLat <- stationInfo$dec_lat_va         #44.080834 latitude of gauge point
requestedLon <- stationInfo$dec_long_va         #-115.618558 longitude of gauge point 
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!#
#~~~~~~~~~~~~~~~ Part 2 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# 
# Create a CSV file of discharge for the grid cell that corresponds 
# w/ the guage we are interested in. 
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!#

# Check if a csv od model outputs exists 
if(file.exists(modelOutputCSV)){
	print("Model output CSV file exists")

} else{
	# if the csv does not exist, then read the files and write the csv
	print("Model output CSV does not exist. Reading files from...")
	print(dataPath)
       
       	# format the date ... this is just so we can pick out a (single) file to read 
	# gauge locations and lat/lon points 
	dateSplit = unlist(strsplit(endDate, "-"))
	yr=dateSplit[1]
	mo=dateSplit[2]
	day=dateSplit[3]
	print(yr)
	print(mo)
	print(day)
	print(paste0(dataPath,yr,mo,day,'0000.CHRTOUT_DOMAIN2'))
	# ~~ Find the correct index the corresponds w/ the gauge location lat/lon
	# using a simple minimum distance formula
	SampleFile <- GetNcdfFile(paste0(dataPath,yr,mo,day,'0000.CHRTOUT_DOMAIN2'), quiet=TRUE)  #
	distance <- sqrt((SampleFile$lat - requestedLat)^2 + (SampleFile$lon - requestedLon)^2)
	GaugeGridCell <- which(distance==min(distance))
	# create lists to pass into the multinc function
	chFiles <- list.files(path=dataPath, pattern='CHRTOUT_DOMAIN2', full.names=TRUE)
	hydroVars <- list(Q='streamflow') # lat='latitude',lon='longitude')
	hydroInds <- list(streamflow=GaugeGridCell)
	# construct lists
	fileList <- list(hydro=chFiles)
	varList  <- list(hydro=hydroVars)
	indList  <- list(hydro=hydroInds)
	fileData <- GetMultiNcdf(file=fileList,var=varList, ind=indList, parallel=FALSE)
	# write CSV file 
	write.csv(fileData, file=modelOutputCSV)
}

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!#
#~~~~~~~~~~~~~~~ Part 3 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# 
# Update the data frames that we have read/created above.
# Create plots comparing model and obs
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!#

colnames(obsDF) <- c("agency","site_no","dateTime","streamflow_cfs","quality_flag", "time_zone")
obsDF$q_cms <- obsDF$streamflow_cfs/35.31 

#Read the model output CSV
colNames <- c("","dateTime","inds","stat","statArg","variable","q_cms","variableGroup","fileGroup")
simQ <- read.csv(modelOutputCSV, col.names =colNames) 
simQ$site_no <- gageID


# Create a ggplot of the observations versus the model simulation ~~~~~~~# 
obsDF$run <- "Observation"
simQ$run <- "Gridded Baseline"
selected_cols<-c("dateTime", "site_no", "q_cms","run")

# merge data 
merged <- rbind(obsDF[,selected_cols], simQ[,selected_cols])
write.csv(merged, file='merged_discharge.csv')
# plot the data
ggplot(data = merged) + geom_line(aes(dateTime, q_cms, color=run)) + facet_wrap(~site_no, ncol = 1)
#ggplot(data = merged) + geom_line(aes(dateTime, q_cms, color=run)) + facet_wrap(~site_no, ncol = 1) + ylim(0,.0025)



#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!#
#~~~~~~~~~~~~~~~ Part 3 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# 
# Perform some statistics  
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!#

# Aggregate data to daily 
dailySimQ <- simQ %>%
  mutate(day = as.Date(dateTime, format="%Y-%m-%d")) %>%
  group_by(day) %>% # group by the day column
    summarise(Qm=sum(q_cms)) %>%  # calculate the SUM of all precipitation that occurred on each day
    na.omit()

dailyObsQ <- obsDF %>%
  mutate(day = as.Date(dateTime, format="%Y-%m-%d")) %>%
  group_by(day) %>% # group by the day column
    summarise(Qo=sum(q_cms)) %>%  # calculate the SUM of all precipitation that occurred on each day
    na.omit()

# merged daily --- there are some cases where the Obs are not reported for data quality issues
mergedDailyAgg <- left_join(dailySimQ, dailyObsQ, by=c("day"))
fit.lm = lm(Qm~Qo, data=mergedDailyAgg)
print('-------- statistics -------')
print('r^2 value is...')
summary(fit.lm)$r.squared 
