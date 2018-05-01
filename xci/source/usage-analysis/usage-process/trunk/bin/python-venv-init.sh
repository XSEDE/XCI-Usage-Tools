#!/bin/bash

#export LD_LIBRARY_PATH=/soft/python-current/lib

#CMD="/soft/python-current/bin/virtualenv /soft/xci-metrics/venv-1.0"
CMD="virtualenv /soft/usage-process/venv-1.0"
echo Executing: ${CMD}
${CMD}

CMD="source /soft/usage-process/venv-1.0/bin/activate"
echo Executing: ${CMD}
${CMD}

pip install pytz
#pip install dns
