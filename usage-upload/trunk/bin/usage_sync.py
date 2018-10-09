#!/soft/usage-upload/python/bin/python
###############################################################################
# Moves usage files in one directory to another
# Skipping files with the same content or with less in the source
# Usage:  <input_path> <input_glob> <output_path>
###############################################################################
from __future__ import print_function
from datetime import datetime
from stat import *
import fnmatch
import os
import sys
import pdb

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

if __name__ == '__main__':
#   pdb.set_trace()
    if len(sys.argv) != 4:
        eprint("Missing argument(s)")
        sys.exit(1)
    input_path = sys.argv[1]
    input_glob = sys.argv[2]
    output_path = sys.argv[3]
    if not os.path.isdir(input_path):
        eprint("Input path isn't a directory") 
        sys.exit(1)
    if not os.path.isdir(output_path):
        eprint("Output path isn't a directory") 
        sys.exit(1)
    if not os.access(output_path, os.W_OK):
        eprint("Output directory isn't writeable") 
        sys.exit(1)

    FILES = [f for f in fnmatch.filter(os.listdir(input_path), input_glob) if os.path.isfile(os.path.join(input_path, f))]
    if len(FILES) < 1:
        eprint("No files matching <input_glob> found at input_path") 
        sys.exit(1)

    stats = {'new': 0, 'same': 0, 'smaller': 0, 'replaced': 0}
    for file in FILES:
        input_fqn = os.path.join(input_path, file)
        output_fqn = os.path.join(output_path, file)
        if not os.path.isfile(output_fqn): 
            os.rename(input_fqn, output_fqn)
            stats['new'] += 1
            continue
        input_stat = os.stat(input_fqn)
        output_stat = os.stat(output_fqn)
        if input_stat.st_size == output_stat.st_size:
            stats['same'] += 1
            os.remove(input_fqn)
            continue
        if input_stat.st_size < output_stat.st_size:
            stats['smaller'] += 1
            continue
        os.rename(input_fqn, output_fqn)
        stats['replaced'] += 1

    print('Synchronized: new={}, same={}, smaller={}, replaced={}'.format(stats['new'], stats['same'], stats['smaller'], stats['replaced']))
    sys.exit(0)
