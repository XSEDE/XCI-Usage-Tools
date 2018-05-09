#!/soft/usage-process-python/bin/python

# The initial basic usage reports that will be generated are:
# 1) How many times a component was used in a month, quarter, or year.
# 2) How many clients used a service component in a month, quarter, or year.
# 3) How many distinct users used a component in a month, quarter, or year.

from __future__ import print_function
import argparse
import csv
import datetime
import fnmatch
import gzip
import json
import os
import pytz
import re
import socket
import sys
import pdb

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class Analyze():
    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('files', nargs='*')
        parser.add_argument('--verbose', action='store_true', \
                            help='Verbose output')
        parser.add_argument('--pdb', action='store_true', \
                            help='Run with Python debugger')
        self.args = parser.parse_args()

        if self.args.pdb:
            pdb.set_trace()

        self.FILES = self.args.files
        self.COMPONENT = None
        self.USAGE = {}
        self.skip = 0

    def load_files(self):
        for f in self.FILES:
            if f[-3:] == '.gz':
                fd = gzip.open(f, 'r')
            else:
                fd = open(f, 'r')

            csv_reader =  csv.DictReader(fd, delimiter=',', quotechar='|')
            for row in csv_reader:
                self.record_usage(row)
            fd.close()

    def record_usage(self, row):
        UC = row.get('USED_COMPONENT', None)
        if not UC:
            self.skip += 1
            return
        if self.COMPONENT is None:
            self.COMPONENT = UC
        elif self.COMPONENT != UC:
            self.skip += 1
            eprint('Ignoring second component =' + UC)
            return
 
        TS_STR = row.get('USE_TIMESTAMP', None)
        if not TS_STR:
            self.skip += 1
            return
            
        TS = pytz.utc.localize(datetime.datetime.strptime(TS_STR, '%Y-%m-%dT%H:%M:%SZ'))
        MON_STR = TS.strftime("%Y-%m")
        if MON_STR not in self.USAGE:
            self.USAGE[MON_STR] = {
                'TIMESUSED': 0,
                'CLIENTS': {},
                'USERS': {}
            }

        client = row.get('USE_CLIENT', None)
        if not client:
            self.skip += 1
            return
 
        MON_USAGE = self.USAGE[MON_STR]
        MON_USAGE['TIMESUSED'] += 1
        MON_USAGE['CLIENTS'][client] = MON_USAGE['CLIENTS'].get(client, 0) + 1

        user = row.get('USE_USER', None)
        if user:
            MON_USAGE['USERS'][user] = MON_USAGE['USERS'].get(user, 0) + 1
    
    def dump_usage(self):
        for mon in sorted(self.USAGE):
            MON_USAGE = self.USAGE[mon]
            print('For month={}'.format(mon))
            print('   Times used={}'.format(MON_USAGE['TIMESUSED']))
            print('   Client cnt={}'.format(len(MON_USAGE['CLIENTS'])))
            print('   User   cnt={}'.format(len(MON_USAGE['USERS'])))
        
    def finish(self):
        rc = 0
        return(rc)

if __name__ == '__main__':
    me = Analyze()
    me.load_files()
    me.dump_usage()
    exit(me.finish())
