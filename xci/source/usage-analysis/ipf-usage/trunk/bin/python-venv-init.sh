#!/bin/bash

VENV_BASE="/soft/ipf-usage/python"
PYTHON_BASE="/soft/python-current"

export LD_LIBRARY_PATH=${PYTHON_BASE}/lib

CMD="${PYTHON_BASE}/bin/virtualenv ${VENV_BASE}"
echo Executing: ${CMD}
${CMD}

CMD="source ${VENV_BASE}/bin/activate"
echo Executing: ${CMD}
${CMD}

pip --no-cache-dir install paramiko
pip --no-cache-dir install pytz
