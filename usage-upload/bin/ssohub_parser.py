#!/soft/XCI-Usage-Tools/python/bin/python3
###############################################################################
# Parse Audit log and return standard usage (LOGIN) in CSV
# Usage:  ./<script> [<input_file>]
# Input:  text <input_file> or stdin, accept gzip'ed (.gz) <input_file>
# Output: stdout in CSV
###############################################################################
from datetime import datetime
import csv
import gzip
import pytz
import re
import shlex
import sys

# All possible output fields
#   Required:     'USED_COMPONENT', 'USE_TIMESTAMP', 'USE_CLIENT',
#   Recommended:  'USE_USER', 'USED_COMPONENT_VERSION', 'USED_RESOURCE'
#   Optional:     'USAGE_STATUS'

#==== CUSTOMIZATION VARIABLES ====================

INPUT_TZ = 'US/Central'                        # One of pytz.common_timezones
INPUT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S.%f'     # A datetime.strptime format
# The fields we are generating
OUTPUT_FIELDS = ['USED_COMPONENT', 'USE_TIMESTAMP', 'USE_CLIENT', 'USE_USER', 'USAGE_STATUS']

# Regex for lines of interest: $1=timestamp, $2=ip details, $3=everthing else
REGEX_LINE = re.compile(r"^type=USER_START msg=audit\(([^\)]+)\):\s*(.*)$")
# Regex for timestamp
REGEX_TS   = re.compile(r"^([0-9.]+)[^0-9.].*")
# Regex for keyword value pair
REGEX_KV   = re.compile(r"^([^=]+)=(.*)$")
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
        match_line = re.search(REGEX_LINE, line.decode('utf-8'))
        if not match_line:
            continue

        o = {}
        o['USED_COMPONENT']         = 'login.xsede.org'

        o['USED_COMPONENT_VERSION'] = None

        match_dtm = re.search(REGEX_TS, match_line.group(1))
        if match_dtm:
            o['USE_TIMESTAMP']      = datetime.fromtimestamp(float(match_dtm.group(1))).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            o['USE_TIMESTAMP']      = ''
       
        base_dict = {}          # Base keyword=value
        for i in shlex.split(match_line.group(2)):
            match_kv = re.search(REGEX_KV, i)
            if match_kv:
                k, v = match_kv.group(1), match_kv.group(2)
                base_dict[k] = v

        msg_dict = {}           # Additional keyword=value from base msg=<stuff>
        if base_dict.get('msg'):
            for i in shlex.split(base_dict.get('msg')):
                k, v = i.split('=')
                msg_dict[k] = v

        match_ip = msg_dict.get('hostname', msg_dict.get('addr'))
        if match_ip:
            o['USE_CLIENT']         = match_ip
        else:
            o['UGE_CLIENT']         = ''

        match_user = msg_dict.get('acct')
        if match_user:
            o['USE_USER']           = 'local:' + match_user
        else:
            o['USE_USER']           = ''

        o['USED_RESOURCE']          = None

        o['USAGE_STATUS']           = msg_dict.get('res')

        # PLACE FILTER CODE HERE 
        # if <filter_expression>:
        #   continue
        if not match_user or match_user in ('root', 'pcp'):
            continue

        matches += 1
        if matches == 1:
            output.writerow(OUTPUT_FIELDS)
        output.writerow([o[f] for f in OUTPUT_FIELDS])
