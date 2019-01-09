#!/bin/bash
###############################################################################
# Upload GLUE2 Usage, steps:
# 1) Extract all available glue2.glue2_db_entityhistory for of desired type
# 2) Parse/convert to XSEDE standard usage format 
# 3) Split usage file into daily usage files
# 4) Selectively copy daily usage files to staging directory
###############################################################################

if [ -z ${1+x} ]; then
    echo "Missing GLUE2 type selecton parameter"
    exit 1
fi

TYPE=$1
echo "*** Processing GLUE2 type '${TYPE}' at `date` ***"

HOME=/soft/usage-upload
TMP=${HOME}/tmp
UPLOAD=${HOME}/upload
RAW_FILE=${TMP}/${TYPE}

cd ${TMP}
if [ $? -ne 0 ]; then
    echo "Failed: cd ${TMP}"
    exit 1
fi
if [ ! -w ${UPLOAD} ]; then
    echo "Upload directory not writeable: ${UPLOAD}"
    exit 1
fi
if [ -f ${RAW_FILE} ]; then
    rm ${RAW_FILE}
fi

#select pg_xlog_replay_pause();
#\o /dev/null
#select pg_xlog_replay_resume();
PGPASSWORD={{ GLUE2_PASS }}
psql -a -h <DB_HOSTNAME> -U glue2_owner warehouse <<EOF
\copy (select "ResourceID" as "USE_CLIENT", to_char("ReceivedTime",'YYYY-MM-DD"T"HH24:MI:SSZ') as "USE_TIMESTAMP" from glue2.glue2_db_entityhistory where "DocumentType"='${TYPE}' and age("ReceivedTime") between interval '1 day' and interval '15 days') to '${RAW_FILE}' with CSV header quote as '|';
EOF

for f in ${TMP}/${TYPE}-20*; do
    [ -e "$f" ] && rm $f
done
${HOME}/bin/usage_splitter.py ${RAW_FILE}

for f in ${TMP}/${TYPE}-20*; do
    [ -e "$f" ] && gzip $f
done
${HOME}/bin/usage_sync.py ${TMP} "${TYPE}-20[0-9][0-9][0-9][0-9][0-9][0-9]*" ${UPLOAD}
