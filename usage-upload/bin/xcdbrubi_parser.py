#!/soft/XCI-Usage-Tools/python/bin/python3
###############################################################################
# Parse xcdb Ruby on Rails log and return standard usage in CSV
# Usage:  ./<script> [<input_file>]
# Input:  text <input_file> or stdin, accept gzip'ed (.gz) <input_file>
# Output: stdout in CSV
###############################################################################
from datetime import datetime, timezone
import csv
import gzip
import pytz
import re
import shlex
import sys

# All possible output fields
#   Required:     'USED_COMPONENT', 'USE_TIMESTAMP', 'USE_CLIENT',
#   Recommended:  'USE_USER', 'USED_COMPONENT_VERSION', 'USED_RESOURCE'
#   Optional:     'USAGE_STATUS', 'USE_AMOUNT', 'USE_AMOUNT_UNITS'

#==== CUSTOMIZATION VARIABLES ====================

INPUT_TZ = 'US/Central'                        # One of pytz.common_timezones
INPUT_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'     # A datetime.strptime format
# The fields we are generating
OUTPUT_FIELDS = ['USED_COMPONENT', 'USE_TIMESTAMP', 'USE_CLIENT', 'USAGE_STATUS', 'USED_RESOURCE', 'USE_AMOUNT', 'USE_AMOUNT_UNITS']

# Regex for lines of interest: $1=timestamp, $2=ip details, $3=everthing else
REGEX_LINE = re.compile(r"^(\S), \[(\S+) (\S+)\]\s+(\S+)\s+\-\-\s+\:\s+(.*)$")
REGEX_STARTED = re.compile(r"^Started\s+(\S+)\s+(\"[^\"]*\")\s+for\s+(\S+)\s+at\s+(.*)$")
REGEX_COMPLETED = re.compile(r"^Completed\s+(\S+)\s+(\S+)\s+in\s+(\S+)\s+\([^\)]+\)(.*)$")
REGEX_AMOUNT = re.compile(r"^(\d+)(\S+)$")

# Add filter code below if desired

#==== END OF CUSTOMIZATIONS ====================
#import pdb
#pdb.set_trace()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        file = sys.argv[1]      # First arg after program name, 0 indexed
        if file[-3:] == '.gz':
            input = gzip.open(file, mode='r')
        else:
            input = open(file, 'r')
    else:
        input = sys.stdin

    output = csv.writer(sys.stdout, delimiter=',', quotechar='|')

    STATE = {}                          # Contains the state as we process lines from multiple threads
    THREAD = None                       # The current thread we are working on
    TEMPLATE = {'USED_COMPONENT': 'org.xsede.xdcdb.api'}

    matches = 0
    for line in input:
        match_line = re.search(REGEX_LINE, line.decode('utf-8'))
        if not match_line:
            continue

        NEW_THREAD = match_line.group(3)
        if THREAD and THREAD != NEW_THREAD:     # We were working on a thread and need to switch to another one
            STATE[THREAD] = o                   # Save the state of the thread we were working on
        if not THREAD or THREAD != NEW_THREAD:  # We weren't working on a thread or need to switch to another one
            o = STATE.get(NEW_THREAD, TEMPLATE.copy())  # Retrieve the thread we are working on, or initialize it
            THREAD = NEW_THREAD
            
#        o['USED_COMPONENT_VERSION'] = None

        if not o.get('USE_TIMESTAMP'):
            date_parse = datetime.strptime(match_line.group(2), INPUT_DATE_FORMAT).astimezone(tz=timezone.utc)
            o['USE_TIMESTAMP']          = date_parse.strftime("%Y-%m-%dT%H:%M:%SZ")

#            match_dtm = re.search(REGEX_TS, match_line.group(2))
#            if match_dtm:
#                o['USE_TIMESTAMP']      = datetime.fromtimestamp(float(match_dtm.group(1))).strftime("%Y-%m-%dT%H:%M:%S.%f")
#            else:
#                o['USE_TIMESTAMP']      = ''

        match_started = re.search(REGEX_STARTED, match_line.group(5))
        if match_started:
            o['USE_CLIENT'] = match_started.group(3)
            o['USED_RESOURCE'] = ' '.join([match_started.group(1), match_started.group(2)])
            continue

        match_completed = re.search(REGEX_COMPLETED, match_line.group(5))
        if not match_completed:
            continue

        # Process the completed usage
        o['USAGE_STATUS'] = ' '.join([match_completed.group(1), match_completed.group(2)])
        match_amount = re.search(REGEX_AMOUNT, match_completed.group(3))
        if match_amount:
            o['USE_AMOUNT'] = match_amount.group(1)
            o['USE_AMOUNT_UNITS'] = match_amount.group(2)
        matches += 1
        if matches == 1:
            output.writerow(OUTPUT_FIELDS)      # Write the CSV header row
        output.writerow([o.get(f,'') for f in OUTPUT_FIELDS])
        if THREAD in STATE:
            del STATE[THREAD]  # We're done with this thread so delete it
