#!/usr/bin/python3

# convert2ometiff.py: converts an OME-TIFF or other file into a single tiled/pyramid OME-TIFF (BF6 or legacy)
# originally written as a bash script and modified to Python3 routine by Damir Sudar
# copyright OHSU

import argparse
import sys
import glob
import os
import tempfile
import subprocess
import re

# convert2ometiff: Image Tiler, pyramid creator, and converter to OME-TIFF
# 
# 

# The arguments:
# 1. Get the absolute location of the input file
#     * This should be a file that bioformats can read!!
# 2. Get the file path of where you want to save the file.
#     * This should be a file name without an extensions; multiple intermediate files and directories will actually be saved with different
#       extensions, the ultimate one with the extension `ome.tif`
# 3. Options:
#       -l creates a legacy OME.TIFF file instead
#       -v produces more verbose output

# command line processing of arguments
parser = argparse.ArgumentParser(description='convert2ometiff.py: convert a OME-TIFF or other file into a single pyramidal OME-TIFF file')
parser.add_argument("InPath", help="Provide path to the input (OME-)TIFF or other file")
parser.add_argument("OutName", help="Provide a path/basename for the output OME-TIFF files (do not provide the extension .ome.tif)")
parser.add_argument("-v", "--verbose", help="Be more verbose", action="store_true", default=False)

args = parser.parse_args()

inpath = os.path.abspath(args.InPath)

outname = os.path.abspath(args.OutName)
outbasename = os.path.basename(outname)

# create a bunch of paths for the temporary directories and files incl. the final name of the output ome.tiff
OUT_PATH_n5 = '/tmp/{}.n5'.format(outbasename)
OUT_PATH_ometiff = '{}.ome.tif'.format(outname)
OUT_PATH_log = '/tmp/{}.log'.format(outbasename)
OUT_PATH_csv = '{}.csv'.format(outname)

# remove any leftover intermediate results
cmd = "rm -rf " + OUT_PATH_n5 + " " + OUT_PATH_log
msg = subprocess.call(cmd, shell=True)

# csv file collects metadata extracted from filenames
# of = open(OUT_PATH_csv, "w")
# of.write("Markers,Round,Channel,ExpTime\n")

# if args.verbose: print("Metadata extracted from files found:")
# if args.verbose: print("Round\tBM1\tBM2\tBM3\tBM4\tName\t\tScene\tChannel")

# retrieve channel names from csv file
# cf = pd.read_csv(OUT_PATH_csv, ",")
# chans = cf["Markers"]
# exposures = cf["ExpTime"]

# convert the input file to a pyramid n5 structure
if args.verbose: print("Converting input file into a n5 structure - this may take a while")
cmd = "bioformats2raw " + inpath + " " + OUT_PATH_n5 + " > " + OUT_PATH_log
msg = subprocess.call(cmd, shell=True)

# convert the n5 structure into a pyramid ome-tiff (either standard or legacy)
if args.verbose: print("Converting the n5 structure into a pyramid ome-tiff - this may take a while")
cmd = "raw2ometiff " + OUT_PATH_n5 + " " + OUT_PATH_ometiff + " >> " + OUT_PATH_log
msg = subprocess.call(cmd, shell=True)

# delete all intermediate results
cmd = "rm -rf " + OUT_PATH_n5 + " " + OUT_PATH_log
msg = subprocess.call(cmd, shell=True)

if args.verbose: print("Done")

