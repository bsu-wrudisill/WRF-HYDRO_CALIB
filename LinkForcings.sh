#!/bin/bash
# links met files from the first path ($1) to the run directory ($2). No ending /

ln -s ${1}/met_em* $2/. 
