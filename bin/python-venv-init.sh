#!/bin/bash

read -p "Python venv directory [/soft/XCI-Usage-Tools/python]: " VENV_BASE
VENV_BASE=${VENV_BASE:-/soft/XCI-Usage-Tools/python}
echo $VENV_BASE

#export LD_LIBRARY_PATH=/soft/python-current/lib
VENV_BASE="/soft/XCI-Usage-Tools/python"

#CMD="/soft/python-current/bin/virtualenv /soft/xci-metrics/venv-1.0"
CMD="virtualenv --python=python3 ${VENV_BASE}"
echo Executing: ${CMD}
${CMD}

CMD="source ${VENV_BASE}/bin/activate"
echo Executing: ${CMD}
${CMD}

CMD="pip3 install --upgrade pip"
echo Executing: ${CMD}
${CMD}

CMD="pip3 install pytz"
echo Executing: ${CMD}
${CMD}

CMD="pip3 install paramiko"
echo Executing: ${CMD}
${CMD}
