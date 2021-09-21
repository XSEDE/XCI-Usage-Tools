#!/bin/bash

MY_BASE="/soft/ipf-usage"
PYTHON_BASE="/soft/python-current"

export LD_LIBRARY_PATH="${PYTHON_BASE}/lib"
${MY_BASE}/PROD/bin/upload_usage.py -l info -c ${MY_BASE}/conf/upload_rabbitmq.conf
