#!/usr/bin/env bash

# enc variabale to set here or in a .env file 
# IMPORTER=<location of the importer>
# BEAN_EXTRACT=<location of the bean-extract exec from beancount>
# DOWNLOADS=<where the csv files from your bankk are located>
# OUTPUT=<where to write the output>
# RULES=<location of csv rules file>

[ -f .env ] && source .env

echo "Running with following parameters:"
echo "IMPORTER:$IMPORTER"
echo "BEAN_EXTRACT:$BEAN_EXTRACT"
echo "DOWNLOADS:$DOWNLOADS"
echo "OUTPUT:$OUTPUT"
echo "RULES:$RULES"

pushd `dirname $0` > /dev/null

cd $IMPORTER
$BEAN_EXTRACT config.py $DOWNLOADS > $OUTPUT 

popd > /dev/null
