# This is at Logan s request
# This script is pulling the streamflow observations from NWIS
# and put in a format that is expected by Calibration format...
args = commandArgs(trailingOnly=TRUE)

siteNumber <- args[1] 
startDate <- args[2] 
endDate <- args[3] 
filePath <- args[4]

library(data.table)
library(dataRetrieval)

# The discharge code is "00060" and when you pull the data is in cfs, so you need to change it to cms
parameterCd <- "00060"  # Discharge
obsDischarge <- dataRetrieval::readNWISuv(siteNumber, parameterCd, startDate, endDate)
obsDischarge <- as.data.table(obsDischarge)
cfsToCms <- 1/35.31466621266132
obsDischarge[, `:=`(discharge.cms=X_00060_00000*cfsToCms)]

# add the day information to it 
obsDischarge[, Date := format(dateTime, "%Y-%m-%d")]

# average over each day, each USGS gages to get the daily flow 
obsDT <- obsDischarge[, .(obs = mean(discharge.cms, na.rm = TRUE)), by = c("Date", "agency_cd", "site_no")]

# convert the date information from character to date format
obsDT[, Date := as.Date(Date, tz = "UTC")]

# Convert to the expected name for the calibration workflow
obsStrData <- obsDT

# Add in a POSIXct column, which is also expected by the workflow. 
obsStrData$POSIXct <- as.POSIXct(obsStrData$Date,tz='UTC')

# save it to a file
save(obsStrData, file = filePath)
