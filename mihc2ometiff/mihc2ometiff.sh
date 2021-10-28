#!/bin/bash

# default pixel spacing if not found in .xml file
spacing=0.5022

while getopts "p:vmsh" opt; do
    case $opt in
        p)
            echo "pixel spacing will be: $OPTARG" >&2
            spacing=$OPTARG
            ;;
        v)
            echo "Verbose mode is enabled" >&2
            verbose=1
            ;;
        m)
            echo "Mask(s) will be included in output ome.tif" >&2
            masks=1
            ;;
        s)
            echo "Only the main image with be included in output ome.tif" >&2
            series=1
            ;;
        h)
            echo "Usage: $0 [-p pixelsize] [-v] [-m] [-h] path_to_mIHC_directory" >&2
            echo "-p pixelsize: Provide an override value for pixelsize" >&2
            echo "-v:  Verbose mode" >&2
            echo "-m:  Add the segmentation mask (if available) as a last channel" >&2
	    echo "-s:  Extract only the main image and discard the slide label and macro image" >&2
            echo "-h:  Print this help message" >&2
            exit 1
            ;;
        \?)
            echo "Invalid option -$OPTARG" >&2
            exit 1
            ;;
        :)
            echo "Option -$OPTARG requires an argument" >&2
            exit 1
            ;;
     esac
done
shift "$(($OPTIND -1))"

anyopts="-p ${spacing} "
if [[ $verbose = 1 ]]; then anyopts="${anyopts} -v "; fi
if [[ $masks = 1 ]]; then anyopts="${anyopts} -m "; fi

seriesopts=""
if [[ $series = 1 ]]; then seriesopts="--series 0 "; fi

for arg in "$@"
do
	dir=`readlink -f ${arg}`
	echo "Processing directory: ${dir}"
	name=`basename ${dir}`
	# create output directory
	[ ! -d "${dir}/${name}_OMETIFF" ] && mkdir ${dir}/${name}_OMETIFF

	# determine name and location of the XML file
	xmlfile=`ls ${dir}/*.xml`
	xmlbase=`basename ${xmlfile}`
	xmlfound=0
	[ -f "${xmlfile}" ] && xmlfound=1

	# depending on Aperio XML file found, use matching _HEM file or just the first _HEM file it finds
	if [ $xmlfound ]; then
		echo "Found Aperio/ScanScope XML file: ${xmlfile}"
		spacing=`mihcparse.py ${xmlfile} /tmp/${name}`
		hemfile=`echo ${xmlfile} | sed 's/.xml/.svs/g'`
	else
		echo "No Aperio/ScanScope XML file found - continuing with HEM and ROI files"
		hemfile=(ls *_HEM.svs)
	fi

	# convert the _HEM file to OME-TIFF and annotate with the ROIs from Aperio XML file
	if [ -f ${hemfile} ]; then
		echo "Using HEM file: ${hemfile}"
		bioformats2raw $seriesopts ${hemfile} /tmp/${name}.n5 > /tmp/${name}.log
		raw2ometiff /tmp/${name}.n5 ${dir}/${name}_OMETIFF/${name}.ome.tif >> /tmp/${name}.log
		rm -r /tmp/${name}.n5 /tmp/${name}.log
		if [ $xmlfound ]; then
			# extract the OME-XML header
			tiffcomment ${dir}/${name}_OMETIFF/${name}.ome.tif > /tmp/${name}_HEM.xml
			# add the ROI info at the correct locations
			insert=`cat /tmp/${name}_ROI1.xml`
			sed -i 's@</Image>@'"$insert"'@' /tmp/${name}_HEM.xml
			insert=`cat /tmp/${name}_ROI2.xml`
			sed -i 's@</OME>@'"$insert"'@' /tmp/${name}_HEM.xml
			# stick the modified header back into the ome.tif
			tiffcomment -set '-' ${dir}/${name}_OMETIFF/${name}.ome.tif < /tmp/${name}_HEM.xml
			rm /tmp/${name}_*.xml
		fi
	else
		echo "Cannot find an appropriate HEM file (either nothing matching .xml file or HEM file not available)"
	fi

	metadataf="Metadata_${name}.csv"
        if [ -f ${metadataf} ]; then
                echo "Using metadata file: ${metadataf}"
		anyopts="${anyopts} -e ${metadataf} "
	fi
	# Convert the individual ROI files to OME-TIFF
	for ff in `ls ${dir}/Processed`
	do
		echo "Working on: ${ff}"
		~/src/mihc2ometiff.py ${anyopts} ${dir}/Processed/${ff} ${dir}/${name}_OMETIFF/${name}_${ff}
	done
	echo "Done with: ${dir}"
done

echo "Done with all"

