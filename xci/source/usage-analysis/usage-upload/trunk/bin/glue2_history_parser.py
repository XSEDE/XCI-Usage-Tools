#!/soft/usage-upload/python/bin/python
###############################################################################
# Parse a glue2 history usage file and return standard usage in CSV
# Usage:  ./<script> [<input_file>]
# Input:  text <input_file> or stdin, accept gzip'ed (.gz) <input_file>
# Output: stdout in CSV
###############################################################################
from datetime import datetime
import csv
import gzip
import sys

# All possible output fields
#   Required:     'USED_COMPONENT', 'USE_TIMESTAMP', 'USE_CLIENT',
#   Recommended:  'USE_USER', 'USED_COMPONENT_VERSION', 'USED_RESOURCE'
#   Optional:     'USAGE_STATUS'

#==== CUSTOMIZATION VARIABLES ====================

# The fields we are generating
OUTPUT_FIELDS = ['USED_COMPONENT', 'USE_TIMESTAMP', 'USE_CLIENT']

# Add filter code below if desired

#==== END OF CUSTOMIZATIONS ====================

if __name__ == '__main__':
    if len(sys.argv) > 1:
        file = sys.argv[1]      # First arg after program name, 0 indexed
        if file[-3:] == '.gz':
            input_fd = gzip.open(file, mode='r')
        else:
            input_fd = open(file, 'r')
    else:
        input_fd = sys.stdin

    file_nopath = file[file.rfind('/')+1:]       # Works even if slash returned -1
    hyphen = file_nopath.find('-')
    if hyphen == -1:
        file_nodate = file_nopath
    else:
        file_nodate = file_nopath[:hyphen]
    filewords = file_nodate.split('.')
    if filewords[-1] == 'gz':
        filewords.pop()
    if filewords[-1] in ('csv', 'usage', 'log'):
        filewords.pop()
    COMPONENT = '.'.join(filewords)
    
    input = csv.DictReader(input_fd, delimiter=',', quotechar='|')

    output = csv.writer(sys.stdout, delimiter=',', quotechar='|')

    matches = 0
    for line in input:
        o = {}
        o['USED_COMPONENT']         = COMPONENT

        o['USED_COMPONENT_VERSION'] = None

        o['USE_TIMESTAMP']          = line['USE_TIMESTAMP'] 

        o['USE_CLIENT']             = line['USE_CLIENT']

        o['USE_USER']               = None

        o['USED_RESOURCE']          = None

        o['USAGE_STATUS']           = None

        # PLACE FILTER CODE HERE 
        # if <filter_expression>:
        #   continue

        matches += 1
        if matches == 1:
            output.writerow(OUTPUT_FIELDS)
        output.writerow([o[f] for f in OUTPUT_FIELDS])
