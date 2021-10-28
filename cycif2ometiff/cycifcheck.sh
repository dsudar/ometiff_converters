#!/bin/bash

while getopts "v" opt; do
    case $opt in
        v)
            echo "Verbose mode is enabled" >&2
            verbose=1
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

anyopts="-v "
# if [[ $verbose = 1 ]]; then anyopts="${anyopts} -v "; fi

for arg in "$@"
do
	echo "Processing directory: ${arg}"
	name=`basename ${arg}`

	# determine name and location of exposure times file
	realbase=`echo $name | sed 's/-Scene.*//g'`
	expfilebase="${realbase}_ExposureTimes.csv"
	expfile="${arg}/../../${expfilebase}"
        if [ -f ${expfile} ]; then
                echo "     Using exposure times file: ${expfile}"
		anyopts="${anyopts} -e ${expfile} "
	else
		echo "     No exposure times file found!!"
	fi
	python3 ~/src/cycifcheck.py ${anyopts} ${arg}
	echo "Done with: ${arg}"
done

echo "Done with all"

