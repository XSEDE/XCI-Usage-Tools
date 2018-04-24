#!/bin/bash

MY_BASE="/soft/ipf-usage"
VENV_BASE="${MY_BASE}/python-venv-1.0"
PYTHON_BASE="/soft/python-current"

export LD_LIBRARY_PATH=${PYTHON_BASE}/lib

CMD="${PYTHON_BASE}/bin/virtualenv ${VENV_BASE}"
echo Executing: ${CMD}
${CMD}

CMD="source ${VENV_BASE}/bin/activate"
echo Executing: ${CMD}
${CMD}

pip install paramiko
pip install pytz
