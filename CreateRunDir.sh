#!/bin/bash
# create a run directory

if [ "$#" -ne 1 ]; then
    echo 'Usage: ./CreateRunDir <name of directory>'
    echo 'exiting'
    exit 
fi

name=$1

# create 
echo 'Creating Directory' $name 
sleep 2 
mkdir $name

# copy 
echo 'Copying Files' 
cp Run/* $name/.

# link 
echo 'Linking Files....' 
sleep 2
ln -s -v $PWD/LBC/* $name/.
#echo 'Done'
