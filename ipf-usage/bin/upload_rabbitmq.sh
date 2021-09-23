#!/bin/bash

MY_BASE="/soft/XCI-Usage-Tools"
source ${MY_BASE}/python/bin/activate

${MY_BASE}/PROD/usage-upload/bin/upload_usage.py -l info -c ${MY_BASE}/conf/upload_rabbitmq.conf
