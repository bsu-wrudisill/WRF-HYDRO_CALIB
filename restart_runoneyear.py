import re
import sys
from datetime import datetime 
import logging
import os
import shutil
from pathlib import Path
libPathList = ['./lib/Python', './util']
for libPath in libPathList:
    sys.path.insert(0, libPath)
from SetMeUp import SetMeUp
from Calibration import Calibration
from Validation import Validation
from sanityPreCheck import RunPreCheck, RunCalibCheck, RunPreSubmitTest
import accessories as acc

# ----- log -----
suffix = datetime.now().strftime("%Y-%m-%d_%H%M%S")
logfile = 'runoneyear_{}.log'.format(suffix)

file_handler = logging.FileHandler(filename=logfile)
stdout_handler = logging.StreamHandler(sys.stdout)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)15s %(levelname)-8s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    handlers=[file_handler, stdout_handler]
                    )

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# this is pretty neat --- we can provide a relative path as argument adn get the full path
directory = Path(sys.argv[1]).resolve()
setupfile = directory.joinpath('setup.yaml')

# create the setup instance
setup = SetMeUp(setupfile)

# log stuff
logger.info('Calling RESTART run...')
logger.info("We are restarting the following directory...")
logger.info(directory)


# unpack the generator, getting the last restart point ...
*_, last_hrldas_restart = directory.glob('*RESTART*')
*_, last_hydro_restart = directory.glob('HYDRO_RST*')

# log which ones we found  
logger.info("found the following restart files")
logger.info(last_hydro_restart)
logger.info(last_hrldas_restart)

# assign to the setup object 
setup.hydrorestart = last_hydro_restart
setup.hrldasrestart = last_hrldas_restart

# get the last date ...
start = 'HYDRO_RST.'
end = '_DOMAIN'
result = re.search('%s(.*)%s' % (start, end), setup.hydrorestart.name).group(1)
hydro_rst_time_fmt = "%Y-%m-%d_%H:%M"
restart_time = datetime.strptime(result, hydro_rst_time_fmt)


# rename the old namelists. maybe we want to keep these for some reason
logger.info('rename old namelists...')
old_namelist = directory.joinpath('namelist.hrldas')
if old_namelist.is_file():
        old_namelist.rename(directory.joinpath('namelist.hrldas.original'))
old_namelist = directory.joinpath('hydro.namelist')
if old_namelist.is_file():
        old_namelist.rename(directory.joinpath('hydro.namelist.original'))

# ready to restart .... log the times 
logger.info(directory)
logger.info("-----restart time-----")
logger.info("original: {} --> {}".format(setup.calib_start_date, setup.calib_end_date))
logger.info("new time: {} --> {}".format(restart_time, setup.calib_end_date))

# write the new namelist with the new restart date. 
setup.CreateNamelist(directory, restart_time, setup.calib_end_date)

# grab the final chrt file name so we can check when hte model finishes...
ed = setup.calib_end_date
final_chrtfile = Path(setup.chrtfmt.format(ed.strftime("%Y"),
                                               ed.strftime("%m"),
                                               ed.strftime("%d"),
                                               ed.strftime("%H")))
# run the restart  
final_file = directory.joinpath(final_chrtfile)
success, message = acc.ForwardModel(directory,
                          setup.userid,
                          setup.catchid,
                          final_file)

# check if it finished --- submit analysis if it did...
logger.info(success)
logger.info(message)
if success:
        # submit the analysis...
        os.chdir(directory)
        setup.CreateAnalScript(directory, 'Calibration.db', 1) 
        jobid, err = acc.Submit('submit_analysis.sh', setup.catchid)


