#!/soft/usage-upload/python/bin/python
###############################################################################
# Parse a usage file and split it into daily files
# Usage:  ./<script> [<input_file>]
# Input:  text <input_file> or stdin, accept gzip'ed (.gz) <input_file>
# Output: stdout in CSV
###############################################################################
from datetime import datetime
import csv
import gzip
import os
import sys

if __name__ == '__main__':
    if len(sys.argv) > 1:
        file = sys.argv[1]      # First arg after program name, 0 indexed
        if file[-3:] == '.gz':
            input_fd = gzip.open(file, mode='r')
        else:
            input_fd = open(file, 'r')
    else:
        input_fd = sys.stdin

    slash = file.rfind('/')			# File name follows last slash
    if slash == -1:
        path_prefix = ''
    else:
        path_prefix = file[:slash] + '/'
    filewords = file[slash+1:].split('.')	# Works even if slash returned -1
    if filewords[-1] == 'gz':
        filewords.pop()
    while filewords[-1] in ('csv', 'usage', 'log'):
        filewords.pop()
    file_prefix = '.'.join(filewords)
    
    input = csv.DictReader(input_fd, delimiter=',', quotechar='|')

    LAST_DATE = None
    OUTPUT_FIELDS = None
    for line in input:
        if OUTPUT_FIELDS == None:
            OUTPUT_FIELDS = line.keys()
        d = line['USE_TIMESTAMP']
        DATE = d[:4] + d[5:7] + d[8:10]	  # Leading YYYY-MM-DD
        if DATE != LAST_DATE:
            if LAST_DATE is not None:
                output_fd.close()
            out_filename = path_prefix + file_prefix + '-' + DATE
            try:
                size = os.stat(out_filename).st_size
            except:
                size = 0
            output_fd = open(out_filename, 'a')
            output = csv.writer(output_fd, delimiter=',', quotechar='|')
            if size == 0:
                output.writerow(OUTPUT_FIELDS)
            LAST_DATE = DATE 

        output.writerow([line[f] for f in OUTPUT_FIELDS])
