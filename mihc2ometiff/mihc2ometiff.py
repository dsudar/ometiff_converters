#!/usr/bin/python3

# mihc2ometiff.py: converts a directory of single channel TIFFs generated by the Coussens Lab workflow into a single tiled/pyramid OME-TIFF
# originally written as a bash script and modified to Python3 routine by Damir Sudar
# copyright OHSU

import argparse
import sys
import pandas as pd
import glob
import os
import tempfile
import subprocess
import re
from libtiff import TIFF
from shutil import copyfile

# natural_sort function properly sorts file names with number sequences such as f0, f1, ... ,f9, f10, f11 and ignores upper/lower case
def natural_sort(l): 
    convert = lambda text: int(text) if text.isdigit() else text.lower() 
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
    return sorted(l, key = alphanum_key)

# mIHC Image Tiler and converter to OME-TIFF
# 
# 

# The arguments:
# 1. Get the absolute location of the directory with individual registered channel tiff files
#     * This should be a directory!!
# 2. Get the file path of where you want to save the file.
#     * This should be a file name without an extensions; multiple intermediate files and directories will actually be saved with different
#       extensions, the ultimate one with the extension `ome.tif`
# 3. Options:
#       -v produces more verbose output
#       -p allows specification of the pixel size (default = 0.325)

# command line processing of arguments
parser = argparse.ArgumentParser(description='mihc2ometiff.py: convert a directory of channels generated by Coussens Lab workflow into a single pyramidal OME-TIFF file')
parser.add_argument("InPath", help="Provide path to the directory containing the individual registered channel TIFFs")
parser.add_argument("OutName", help="Provide a path/basename for the output OME-TIFF files (do not provide the extension .ome.tif)")
parser.add_argument("-p", "--pixsize", help="Pixel size (default is 0.5022 microns)", action="store", default="0.5022")
parser.add_argument("-v", "--verbose", help="Be more verbose", action="store_true", default=False)
parser.add_argument("-m", "--masks", help="Include any masks into output OME-TIFF", action="store_true", default=False)

args = parser.parse_args()

inpath = os.path.abspath(args.InPath)

outname = os.path.abspath(args.OutName)
outbasename = os.path.basename(outname)

# create a bunch of paths for the temporary directories and files incl. the final name of the output ome.tif
OUT_PATH_conv = '/tmp/{}.conv'.format(outbasename)
OUT_PATH_n5 = '/tmp/{}.n5'.format(outbasename)
OUT_PATH_xml = '/tmp/{}.xml'.format(outbasename)
OUT_PATH_log = '/tmp/{}.log'.format(outbasename)
OUT_PATH_csv = '/tmp/{}.csv'.format(outbasename)

# remove any leftover intermediate results
cmd = "rm -rf " + OUT_PATH_conv + " " + OUT_PATH_n5 + " " + OUT_PATH_xml + " " + OUT_PATH_log + " " + OUT_PATH_csv
msg = subprocess.call(cmd, shell=True)

# get a list of all files in the specified directory and sort them naturally
image_paths = list(glob.glob('{}/*'.format(inpath)))
sorted_image_paths = natural_sort(image_paths)

# the regex pattern of the single channel registered tif files
cycif_pattern=re.compile("^V_([a-zA-Z0-9-]+)_[a-zA-Z0-9-_]+_C([0-9]+)R([0-9]+)_([a-zA-Z0-9-]+)_([a-zA-Z0-9-_]+_)*ROI([0-9]+)\.tif")
mask_pattern=re.compile("^MASK_([a-zA-Z0-9-]+)_[a-zA-Z0-9-_]+_C([0-9]+)R([0-9]+)_([a-zA-Z0-9-]+)_([a-zA-Z0-9-_]+_)*ROI([0-9]+)\.tif")

# create temporary conversion directory
os.mkdir(OUT_PATH_conv)

# csv file collects metadata extracted from filenames
of = open(OUT_PATH_csv, "w")
of.write("Markers,Cycle,Round,ExpTime\n")

if args.verbose: print("Metadata extracted from files found:")
if args.verbose: print("Cycle\tRound\tBiomarker\tROI")

# channel counter increments while stepping through the individual tif files
chan_count = 0
exps_avail = 0

# read metadata file if provided
if False:
    meta = pd.read_csv(args.metadata, ",")
    meta_avail = True
else: meta_avail = False

posx = 0
posy = 0
# add grid_coordinate to output name for TMAs
grid_coor = ""

for fname in sorted_image_paths:
    inbasename = os.path.basename(fname)
    if cycif_pattern.match(inbasename):
        # if regex match found, extract all the embedded metadata from filename
        match = cycif_pattern.search(inbasename)
        nuclei = match.group(1)
        cycle = int(match.group(2))
        round = int(match.group(3))
        bm = match.group(4)
        tma_stuff = match.group(5)
        roi = int(match.group(6))

        tma_pattern=re.compile("^([A-Za-z])([0-9]+)_*")
        if (tma_stuff and tma_pattern.match(tma_stuff)):
            match2 = tma_pattern.search(tma_stuff)
            grid_coor = "_" + match2.group(1) + match2.group(2)
            posx = int(match2.group(2))
            posy = ord(match2.group(1).lower()) - 96

	# use the metadata file (if available) as a sanity check
        # if meta_avail:
            # exp_pat = "^R" + str(round) + "_.*"
            # thisR = exps.loc[exps.czi_name.str.contains(exp_pat), :]
            # exp_time = float(thisR[str(channel-1)])

        if args.verbose: print("%d\t%d\t%s\t%d" % (cycle, round, bm, roi), end = ' ')

        if args.verbose: print("    Accepting: ", inbasename)
        example_file = fname

        if nuclei == "NUCLEI":
            # add entry for a numbered DAPI channel
            chan_line = "NUCLEI,%d,%d\n" % (cycle, round)
            of.write(chan_line)
        else:
            # add entry for a biomarker channel
            chan_line = "%s,%d,%d\n" % (bm, cycle, round)
            of.write(chan_line)

        # create a symlink in conversion directory for bioformats pattern matching
        chan_count += 1
        slink = "%s/Reg_C%03d.tif" % (OUT_PATH_conv, chan_count)
        copyfile(fname, slink)
#        os.symlink(fname, slink)
    else:
        if args.verbose: print("File \"%s\" is not a regular channel file - skipped. " % inbasename)

if args.masks:
    if args.verbose: print("\nAvailable masks will be appended as extra channels.")
    # check whether this a MASK file and belongs to the NUCLEI channel
    for fname in sorted_image_paths:
        inbasename = os.path.basename(fname)
        if mask_pattern.match(inbasename):
            match = mask_pattern.search(inbasename)
            nuclei = match.group(1)
            cycle = int(match.group(2))
            round = int(match.group(3))
            bm = match.group(4)
            ignore = match.group(5)
            roi = int(match.group(6))
            if nuclei == "NUCLEI":
                 chan_line = "NUC_MASK,%d,%d\n" % (cycle, round)
                 of.write(chan_line)
                 if args.verbose: print("%d\t%d\t%s\t%d     Accepting Mask Image: %s" % (cycle, round, bm, roi, inbasename))
                 # create a symlink in conversion directory for bioformats pattern matching
                 chan_count += 1
                 slink = "%s/Reg_C%03d.tif" % (OUT_PATH_conv, chan_count)
                 copyfile(fname, slink)
#                 os.symlink(fname, slink)

of.close()

# create the pattern file needed for bioformats
pattern_file = "%s/%s.pattern" % (OUT_PATH_conv, outbasename)
of = open(pattern_file, "w")
of.write("Reg_C<001-%03d>.tif" % chan_count)
of.close()

# retrieve channel names from csv file
cf = pd.read_csv(OUT_PATH_csv, ",")
chans = cf["Markers"]
if exps_avail:
    exposures = cf["ExpTime"]

physsize = args.pixsize

tif = TIFF.open(example_file, mode = 'r')
xs = tif.GetField("ImageWidth")
ys = tif.GetField("ImageLength")
TIFF.close(tif)

OUT_PATH_ometiff = '{}.ome.tif'.format(outname + grid_coor)

if args.verbose: print("Creating a single OME.TIFF file of %d by %d pixels (pixel spacing: %s) with %d channels" % (xs, ys, physsize, chan_count))


# create the OME-XML header
part1 = """<?xml version="1.0" encoding="UTF-8"?>
<!-- Warning: this comment is an OME-XML metadata block, which contains crucial dimensional parameters and other important metadata. Please edit cautiously (if at all), and back up the original data before doing so. For more information, see the OME-TIFF web site: https://docs.openmicroscopy.org/latest/ome-model/ome-tiff/. -->
<OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" Creator="OME Bio-Formats 6.2.1" UUID="urn:uuid:f44e8e82-3f44-4733-b6a3-43ac52b810e3" xsi:schemaLocation="http://www.openmicroscopy.org/Schemas/OME/2016-06 http://www.openmicroscopy.org/Schemas/OME/2016-06/ome.xsd">
   <Instrument ID="Instrument:0">
      <Microscope Type="Upright" Model="Aperio AT2" Manufacturer="Leica Biosystems"/>
      <Detector ID="Detector:0" Type="CCD" Model="Unknown-22C" Manufacturer="Unknown"/>
      <Objective ID="Objective:1" Model="Plan-Apochromat 20x/0.75 NA" Immersion="Air" LensNA="0.75" NominalMagnification="20.0" WorkingDistance="620.0"/>
   </Instrument>\n"""

part1 += "   <Image ID=\"Image:0\" Name=\"" + outbasename + "\">\n"

part2 = """      <Description/>
      <InstrumentRef ID="Instrument:0"/>
      <ObjectiveSettings ID="Objective:1"/>\n"""

part2 += "      <Pixels BigEndian=\"true\" DimensionOrder=\"XYCZT\" ID=\"Pixels:0\" PhysicalSizeX=\"" + physsize + "\" PhysicalSizeXUnit=\"µm\" "
part2 +=  "PhysicalSizeY=\"" + physsize + "\" PhysicalSizeYUnit=\"µm\" Interleaved=\"false\" SignificantBits=\"8\" "
part2 += "SizeC=\"" + str(chan_count) + "\" SizeT=\"1\" SizeX=\"" + str(xs) + "\" SizeY=\"" + str(ys) + "\" SizeZ=\"1\" Type=\"uint8\">\n"

# add the channels info
part3 = ""
for i in range(0, int(chan_count)):
    part3 += "         <Channel ID=\"Channel:0:" + str(i) + "\" Name=\"" + chans[i] + "\" SamplesPerPixel=\"1\">\n"
    part3 += "            <LightPath/>\n"
    part3 += "         </Channel>\n"

if True:
    part4 = ""
    for i in range(0, int(chan_count)):
        part4 += "         <TiffData FirstC=\"" + str(i) + "\" FirstT=\"0\" FirstZ=\"0\" IFD=\"" + str(i) + "\" PlaneCount=\"1\"/>\n"
    for i in range(0, int(chan_count)):
        part4 += "         <Plane PositionX=\"" + str(posx) + "\" PositionY=\"" + str(posy) + "\" TheC=\"" + str(i) + "\" TheT=\"0\" TheZ=\"0\"/>\n"
else:
    part4 = "         <TiffData/>"

part4 += """      </Pixels>
   </Image>
</OME>\n"""

xmlstr = part1 + part2 + part3 + part4

of = open(OUT_PATH_xml, "w")
of.write(xmlstr)
of.close()

# convert the pile of tif symlinks in the conversion directory into a pyramid n5 structure
if args.verbose: print("Converting individual registered non-tiled tif files into a n5 structure - this may take a while")
cmd = "bioformats2raw " + pattern_file + " " + OUT_PATH_n5 + " > " + OUT_PATH_log
msg = subprocess.call(cmd, shell=True)

# convert the n5 structure into a pyramid ome-tiff
if args.verbose: print("Converting the n5 structure into a pyramid ome-tiff - this may take a while")
cmd = "raw2ometiff " + OUT_PATH_n5 + " " + OUT_PATH_ometiff + " >> " + OUT_PATH_log
msg = subprocess.call(cmd, shell=True)

# inject the OME-XML metadata string into the final OME-TIFF file
cmd = "tiffcomment -set '" + OUT_PATH_xml + "' " + OUT_PATH_ometiff
msg = subprocess.call(cmd, shell=True)

# delete all intermediate results
cmd = "rm -rf " + OUT_PATH_conv + " " + OUT_PATH_n5 + " " + OUT_PATH_xml + " " + OUT_PATH_log + " " + OUT_PATH_csv
msg = subprocess.call(cmd, shell=True)

if args.verbose: print("Done")
