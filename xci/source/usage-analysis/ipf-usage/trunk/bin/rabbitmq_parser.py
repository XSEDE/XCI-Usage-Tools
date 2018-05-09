#!/soft/ipf-usage/python/bin/python
###############################################################################
# Parse a RabbitMQ log and return standard usage in CSV
# Usage:  ./<script> [<input_file>]
# Input:  text <input_file> or stdin, accept gzip'ed (.gz) <input_file>
# Output: stdout in CSV
###############################################################################
from datetime import datetime
import csv
import gzip
import pytz
import re
import sys

# All possible output fields
#   Required:     'USED_COMPONENT', 'USE_TIMESTAMP', 'USE_CLIENT',
#   Recommended:  'USE_USER', 'USED_COMPONENT_VERSION', 'USED_RESOURCE'
#   Optional:     'USAGE_STATUS'

#==== CUSTOMIZATION VARIABLES ====================

INPUT_TZ = 'US/Central'                        # One of pytz.common_timezones
INPUT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S.%f'     # A datetime.strptime format
# The fields we are generating
OUTPUT_FIELDS = ['USED_COMPONENT', 'USE_TIMESTAMP', 'USE_CLIENT', 'USE_USER']

# Regex for lines of interest: $1=timestamp, $2=ip details, $3=everthing else
REGEX_LINE = re.compile(r"^([^\[]+)\[([^\]]+)\]\s+\<[0-9.]+\> connection \<[0-9.]+\> \(([^)]+)\):\s*(.*)$")
# Regex for client IP in $2=ip details
REGEX_IP   = re.compile(r"^([0-9.]+):[0-9]+ -\> [0-9.]+:[0-9]+$")
# Regex for user in $3=everthing else 
REGEX_USER = re.compile(r"\buser\s+\'([^\']+)\'.*$")

# Add filter code below if desired

#==== END OF CUSTOMIZATIONS ====================

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

    matches = 0
    for line in input:
        match_line = re.search(REGEX_LINE, line)
        if not match_line:
            continue

        o = {}
        o['USED_COMPONENT']         = 'rabbitmq.xsede.org'

        o['USED_COMPONENT_VERSION'] = None

        dtm = datetime.strptime(match_line.group(1).strip(), INPUT_DATE_FORMAT)
        o['USE_TIMESTAMP']          = pytz.timezone(INPUT_TZ).localize(dtm).astimezone(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        match_ip = re.search(REGEX_IP, match_line.group(3))
        if match_ip:
            o['USE_CLIENT']         = match_ip.group(1)
        else:
            o['UGE_CLIENT']         = ''

        match_user = re.search(REGEX_USER, match_line.group(4))
        if match_user:
            o['USE_USER']           = 'local:' + match_user.group(1)
        else:
            o['USE_USER']           = ''

        o['USED_RESOURCE']          = None

        o['USAGE_STATUS']           = None

        # PLACE FILTER CODE HERE 
        # if <filter_expression>:
        #   continue

        matches += 1
        if matches == 1:
            output.writerow(OUTPUT_FIELDS)
        output.writerow([o[f] for f in OUTPUT_FIELDS])
