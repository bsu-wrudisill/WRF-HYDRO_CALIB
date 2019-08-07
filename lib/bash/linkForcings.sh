#!/bin/bash
dir=/mnt/selway/data/data_03/SFPAYETTE
for i in {1995..2010}
do 
	ln -s -v ${dir}/wy$i/wrfout* ./FORCING/.

done
