#!/bin/bash
#
# londonconvert.sh
#
# Copyright 2011 Joachim Pfeiffer
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#
#
#       This Unix script converts Transport for London TransXChange transit data to GTFS
#       Depends on: 
#               - TransXCHange2GTFS converter executable JAR file, version 1.7.0 or later. Download at: http://code.google.com/p/googletransitdatafeed
#               - Transport for London TransXChange export data feed. Request the current data feed (stream.zip) at: http://www.tfl.gov.uk/businessandpartners/syndication/default.aspx
#               - Version 1 CSV NaPTAN stop file. Available at: http://www.dft.gov.uk/public-transportdatamanagement/NaPTANDownload/
#                       NaPTAN stop file augmentation. Manually append to NaPTAN stop file. Create from reference stops below.
#               - Operator and mode specific configuration files (.cfg files). Create from reference code below. Place files in directory ./configs
#
#       Please visit the GTDF wiki at http://code.google.com/p/googletransitdatafeed/w/list for instructions
#
# Support functions: Silent creation and removal of directories and files

set -e

function tflrmdir() {
if [ -d $1 ]
then
        rm -r $1
fi
}
function tflmkdir() {
tflrmdir $1
mkdir $1
}
function tflrm() {
if [ -f $1 ]
then
        rm $1
fi
}
# Support function: move .xml files containing $1 (e.g. operator OId_59) to corresponding directory 
function tflprepare() {
if [ ! "$2" ]
then
        echo "-I- Preparing $1"
else
        echo "-I- Preparing $1 / $2"
fi
tflmkdir tfltmp
grep -c $1 london/*.xml | grep -v ".xml:0" | sed "s/:[^:]*$//;s/.*://" | sed "s/^/mv /" | sed "s/$/ tfltmp/" >_a.sh
chmod 777 _a.sh
./_a.sh
rm _a.sh
if [ "$2" ]
then
        mv tfltmp/*.xml $2
else
        zip -q tfltmp/data.zip tfltmp/*.xml
        rm tfltmp/*.xml
        tflrmdir $1
        mv tfltmp $1
        if [ -z "$(ls $1/)" ]
        then
                echo "-W- No TransXChange input files for operator ID $1. Operator has been removed from input file set by file set originator. It is recommended to modify this script to reflect operator change(s) in the input file set"
        else 
                tflrm $1/*.xml
        fi
fi
}
# Support function: convert intput files. Arguments: $1-Operator Name $2-Operator directory $3 configuration file
function tflconvert() {
echo
echo "-I- Converting $1"
if [ -f $2/data.zip ]
then
        java -Xmx1080M -jar $TXC2GTFS/transxchange2GoogleTransit.jar $2/data.zip $2/GTFS -c $3
        tflrm $2/data.zip
else
        echo "-E- Data for operator $1 not found"
fi
}
#
# START OF SCRIPT
#
echo
echo "londonconvert.sh - London TransXChange2GTFS conversion"
echo "Copyright 2011 Joachim Pfeiffer. Licensed under the Apache License, Version 2.0."
echo "You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0"
echo
#
# Test if zip is installed
if [ ! -f /usr/bin/zip ]
then
        echo "-E- zip not found. Please install zip"
        exit 1
fi
if [ ! -f /usr/bin/unzip ]
then
        echo "-E- unzip not found. Please install unzip"
        exit 1
fi
#
# Set directory that contains converter's executable JAR file transxchange2GoogleTransit.jar. CHANGE DIRECTORY REFERENCE AS NECESSARY
[ "$TXC2GTFS" ] || TXC2GTFS='/usr/lib/TransXChange2GTFS/dist'
if [ ! -f $TXC2GTFS"/transxchange2GoogleTransit.jar" ]
then
        echo "-E- "$TXC2GTFS"/transxchange2GoogleTransit.jar not found. Please correctly set TXC2GTFS"
        exit 1
fi
echo "-I- Using converter " $TXC2GTFS"/transxchange2GoogleTransit.jar"

#
DATASOURCE='http://www.tfl.gov.uk/tfl/businessandpartners/syndication/example-feeds/journeyplannertimetables/journey-planner-timetables.zip' # Note: This is a link to an example feed only. Request the current stream.zip as listed in dependency declaration above
#
# Download Demo TransXChange file from TfL and unzip
# echo "-I- Downloading Demo London data set from $DATASOURCE"
# curl $DATASOURCE >stream.zip # Example only.
if [ ! -f stream.zip ]
then
        echo "-E- stream.zip not found. Please put the data set in a zip called stream.zip in the CWD."
        exit 1
fi
echo "-I- Unzipping London data set: stream.zip"
tflrmdir london
unzip -q stream.zip -d london
#
# Sort files of different modes into respective directories
echo "-I- Preparing Underground"
tflmkdir LondonUnderground
zip -q LondonUnderground/data.zip london/output_txc_01*.xml
rm london/output_txc_01*.xml
#
tflmkdir LondonRiverServices
tflprepare OId_30 LondonRiverServices
tflprepare OId_31 LondonRiverServices
tflprepare OId_32 LondonRiverServices
tflprepare OId_33 LondonRiverServices
tflprepare OId_35 LondonRiverServices
tflprepare OId_36 LondonRiverServices
tflprepare OId_37 LondonRiverServices
zip -q LondonRiverServices/data.zip LondonRiverServices/*.xml
rm LondonRiverServices/*.xml
#
echo "-I- Preparing DLR"
tflmkdir DLR
zip -q DLR/data.zip london/output_txc_25*.xml
rm london/output_txc_25*.xml
#
echo "-I- Preparing Tramlink"
tflmkdir Tramlink
zip -q Tramlink/data.zip london/output_txc_63*.xml
rm london/output_txc_63*.xml
# London Service Permits (cross boundary)
tflprepare OId_OL
tflprepare OId_KE
tflprepare OId_LD
tflprepare OId_SL
tflprepare OId_MN
tflprepare OId_DC
tflprepare OId_BE
tflprepare OId_CX
tflprepare OId_TE
tflprepare OId_CW
tflprepare OId_CC
tflprepare OId_HY
tflprepare OId_LC
tflprepare OId_ET
tflprepare OId_LG
tflprepare OId_LU
tflprepare OId_SV
tflprepare OId_ME
tflprepare OId_ML
tflprepare OId_SK
tflprepare OId_IF
tflprepare OId_EB
# London Buses
tflmkdir LondonBuses
tflprepare OId_07 LondonBuses
tflprepare OId_08 LondonBuses
tflprepare OId_16 LondonBuses
tflprepare OId_21 LondonBuses
tflprepare OId_24 LondonBuses
tflprepare OId_41 LondonBuses
tflprepare OId_45 LondonBuses
tflprepare OId_48 LondonBuses
tflprepare OId_49 LondonBuses
tflprepare OId_55 LondonBuses
tflprepare OId_51 LondonBuses
tflprepare OId_54 LondonBuses
tflprepare OId_59 LondonBuses
tflprepare OId_60 LondonBuses
tflprepare OId_61 LondonBuses
tflprepare OId_74 LondonBuses
tflprepare OId_76 LondonBuses
tflprepare OId_06 LondonBuses # little problem: grep needs multiple .xml files left in order to evoke file names, so operator OId_06 with multiple TransXChange files is placed at the end
zip -q LondonBuses/data.zip LondonBuses/*.xml
rm LondonBuses/*.xml
#
# Any leftovers? Warning if that's the case
if [ ! -z "$(ls london/)" ]
then
        echo "-W- The following TransXChange input file(s) have not been accounted for. Cause: Unkown operator(s)"
        ls -l london
        echo "It is recommended to modify this script to reflect operator change(s)"
        read -p "Press return to continue, ^C to stop"
fi
#
# Convert, using mode specific configuration files
tflconvert "London Underground" LondonUnderground configs/Underground.cfg
tflconvert "London River Services" LondonRiverServices configs/RiverServices.cfg
tflconvert DLR DLR configs/DLR.cfg
tflconvert Tramlink Tramlink configs/Tramlink.cfg
tflconvert "London Buses" LondonBuses configs/Buses.cfg
tflconvert "The Original London Sightseeing Tour" OId_OL configs/Buses.cfg
tflconvert "Arriva Kent Thameside" OId_KE configs/Buses.cfg
tflconvert "Arriva The Shires" OId_LD configs/Buses.cfg
tflconvert "Arriva London South" OId_SL configs/Buses.cfg
tflconvert "Arriva London North" OId_MN configs/Buses.cfg
tflconvert "Docklands Buses" OId_DC configs/Buses.cfg
tflconvert "Blue Triangle Buses" OId_BE configs/Buses.cfg
tflconvert "Travel London" OId_CX configs/Buses.cfg
tflconvert "Travel London (West)" OId_TE configs/Buses.cfg
tflconvert Centrewest OId_CW configs/Buses.cfg
tflconvert First OId_CC configs/Buses.cfg
tflconvert "C T Plus" OId_HY configs/Buses.cfg
tflconvert "London Central" OId_LC configs/Buses.cfg
tflconvert "East Thames Buses" OId_ET configs/Buses.cfg
tflconvert "London General" OId_LG configs/Buses.cfg
tflconvert "London United" OId_LU configs/Buses.cfg
tflconvert Sovereign OId_SV configs/Buses.cfg
tflconvert Metrobus OId_ME configs/Buses.cfg
tflconvert Metroline OId_ML configs/Buses.cfg
tflconvert "Stagecoach in London" OId_SK configs/Buses.cfg
tflconvert "Stagecoach in London" OId_IF configs/Buses.cfg
tflconvert "H R Richmond" OId_EB configs/Buses.cfg
#
tflrmdir tfltmp
exit
#
# END OF SCRIPT
#
#
# START OF REFERENCE FILES
#
# Proposed for-reference content for the mode specific configuration files
# ./configs/Underground.cfg
url=http://tfl.gov.uk
timezone=Europe/London
default-route-type=1
skipemptyservice=true
skiporphanstops=true
stopfile=NaPTANcsv/Stops.csv
naptanstopcolumn="CommonName"
#
# ./configs/RiverServices.cfg
url=http://tfl.gov.uk
timezone=Europe/London
default-route-type=4
skipemptyservice=true
skiporphanstops=true
stopfile=NaPTANcsv/Stops.csv
naptanstopcolumn="CommonName"
agency:OId_30=London River Services, operated by Crown River Cruises
agency:OId_32=London River Services, operated by City Cruises
agency:OId_33=London River Services, operated by Thames Clippers
agency:OId_35=London River Services, operated by Woolwich Free Ferry
agency:OId_36=London River Services, operated by Westminster Passenger Services Association
agency:OId_37=London River Services, operated by Turk Launches
#
# ./configs/DLR.cfg
url=http://tfl.gov.uk
timezone=Europe/London
default-route-type=0
skipemptyservice=true
skiporphanstops=true
stopfile=NaPTANcsv/Stops.csv
naptanstopcolumn="CommonName"
#
# ./configs/Tramlink.cfg
url=http://tfl.gov.uk
timezone=Europe/London
default-route-type=0
skipemptyservice=true
skiporphanstops=true
stopfile=NaPTANcsv/Stops.csv
naptanstopcolumn="CommonName"
#
# ./configs/Buses.cfg
url=http://tfl.gov.uk
timezone=Europe/London
default-route-type=3
skipemptyservice=true
skiporphanstops=true
stopfile=NaPTANcsv/Stops.csv
geocodemissingstops=true
agency:OId_06=London Buses, operated by Arriva
agency:OId_08=London Buses, operated by Arriva London
agency:OId_16=London Buses, operated by Blue Triangle
agency:OId_21=London Buses, operated by Abellio London
agency:OId_24=London Buses, operated by First
agency:OId_41=London Buses, operated by C T Plus
agency:OId_45=London Buses, operated by London Central
agency:OId_48=London Buses, operated by London General
agency:OId_49=London Buses, operated by London United
agency:OId_51=London Buses, operated by Metrobus
agency:OId_54=London Buses, operated by Metroline
agency:OId_55=London Buses, operated by Red Rose Travel
agency:OId_59=London Buses, operated by Selkent
agency:OId_60=London Buses, operated by East London
agency:OId_61=London Buses, operated by Transdev
agency:OId_74=London Buses, operated by Quality Line
agency:OId_76=London Buses, operated by Docklands Buses
agency:OId_OL=London Buses, operated by The Original London Sightseeing Tour
agency:OId_KE=London Buses, operated by Arriva Kent Thameside
agency:OId_LD=London Buses, operated by Arriva The Shires
agency:OId_SL=London Buses, operated by Arriva London South
agency:OId_MN=London Buses, operated by Arriva London North
agency:OId_DC=London Buses, operated by Docklands Buses
agency:OId_BE=London Buses, operated by Blue Triangle Buses
agency:OId_CX=London Buses, operated by Travel London
agency:OId_TE=London Buses, operated by Travel London (West)
agency:OId_CW=London Buses, operated by Centrewest
agency:OId_CC=London Buses, operated by First
agency:OId_HY=London Buses, operated by C T Plus
agency:OId_LC=London Buses, operated by London Central
agency:OId_ET=London Buses, operated by East Thames Buses
agency:OId_LG=London Buses, operated by London General
agency:OId_LU=London Buses, operated by London United
agency:OId_SV=London Buses, operated by Sovereign
agency:OId_ME=London Buses, operated by Metrobus
agency:OId_ML=London Buses, operated by Metroline
agency:OId_SK=London Buses, operated by Stagecoach in London
agency:OId_IF=London Buses, operated by Stagecoach in London
agency:OId_EB=London Buses, operated by H R Richmond
agency:OId_NL=London Buses, operated by N S L
#
# Proposed manual augmentation for missing stops in NaPTANcsv/Stops.csv
"AtcoCode","GridType","Easting","Northing","Longitude","Latitude","CommonName","Indicator","Bearing","Street","Landmark","NptgLocalityCode","LocalityName","ParentLocalityName","GrandParentLocality","Town","Suburb","StopType","BusStopType","BusRegistrationStatus","RecordStatus","Notes","LocalityCentre","NaptanCode","LastChanged"
"9300RQP","","","",-0.305037,51.456417,"Richmond Pier","","NA","Richmond St.","","","Richmond St. Helena Pier","Richmond","","","","","","","","","","",
"9300WAP","","","",-0.199003,51.462742,"Wandsworth Pier","","NA","Point Pleasant","","","Wandsworth Riverside Quarter Pier","Wandsworth","","","","","","","","","","",
"9400ZZLUDGY1","","","",0.14754,51.54164,"Dagenham Heathway Underground Station","Entrance unknown","NA","-","TBA","E0033934","Dagenham","","","","","MET","","","ACT","","","",
"490000276005","","","",-0.18516,51.61796,"Woodside Park Underground Station","Entrance unknown","NA","---","---","N0060479","North Finchley","","","","","","","","","","","",
"490000238006","","","",-0.076352,51.510046,"Tower Hill Underground Station","Entrance unkown","NA","---","---","","Tower Hill","London","","","","","","","","","","",
"490000254009","",531046,180007,-0.11328,51.50382,"Waterloo Underground Station","Entrance unkown","NA","---","---","E0034649","Waterloo (London)","London","","","","TMU","","","DEL","","N","",
#
#
# COMMENTS
#
# 1. Overlapping DaysOfNonOperation in VehicleJourney definitions
# A common imperfection are overlapping DaysOfNonOperation in VehicleJourney definitions. Example: File output_txc_24165g.xml, VehicleJourney 24165gg2R1650176, ServiceRef SId_24165g2 defines NonOperatingDays as follows:
# <DaysOfNonOperation><DateRange><StartDate>2010-11-06</StartDate><EndDate>2010-11-06</EndDate></DateRange><DateRange><StartDate>2010-11-06</StartDate><EndDate>2011-12-03</EndDate></DateRange></DaysOfNonOperation>
# Day 2010-11-06 hits calendar_dates.txt twice, causing a warning when validated with the GTFS feedvalidator.
#
# 2. Incomplete London Underground Destinations
# The TransXChange exports include only a single Destination for a direction on a London Underground line. 
# This seems incorrect. More detailed destinations can be looked up on the journeyplanner web site. Although this passes GTFS validation, it introduces misleading trip Destinations. 
# As an example, LId_01DIS0 and the associated services only include the Destination "Upminster" although the Destinations vary by individual trip.
#
# 3. Multiple Line IDs for a single line
# Individual lines are represented by multiple line IDs. This is common throughout the entire TransXChange export files
#
# 4. Stops and stations without corresponding records in NaPTAN
# Manually backfill such stops in Stops.csv, or use geocoding. Caution: Geocoding of stops and stations is inaccurate relative to the required precision. This becomes evident in "Stops Too Close" and "Too Fast Travel" warnings when a resulting GTFS feed is validated with the feedvalidator
#
# 5. TransXChange <VehicleJourney> times after midnight. (This is a serious problem)
# VehicleJourney's with times after midnight cannot be resolved to the correct calendar day. (The "easiest" solution would be if the originator of the data use the 25 hour format.)
# Example of this problem:
# Line: Hammersmith
# Corresponding TransXChange file: output_txc_01HAM_.xml
# VehicleJourney: 01HAM0R457
# DepartureTime: 00:15:30
# ServiceRef: SId_01HAM0 / DaysOfWeek: MondayToFriday
# This VehicleJourney technically falls on a Monday calendar day at 00:15:30. This is a problem - the last VehicleJourney on a Sunday night ends before this time and there are no more trains in service at that time.
# When converted to GTFS, this problem propagates to the stop times in stop_times.txt. The stop times are rolled out accordingly.
#
# 6. Operator churn
# Operators enter or leave the TransXChange feed almost on a weekly basis. OId codes change on occasion. This drives the need for frequent adjustments to this script and possibly the configuration files.
#
# END OF FILE londonconvert.sh
#
