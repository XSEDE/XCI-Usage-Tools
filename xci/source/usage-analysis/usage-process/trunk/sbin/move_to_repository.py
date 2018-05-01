#!/usr/bin/env python
###############################################################################
# :wq
###############################################################################

import argparse
import binascii
import datetime
from datetime import datetime, tzinfo, timedelta
import grp
import json
import os
import pwd
import shutil
import subprocess
import sys
import gzip
import pdb
from stat import *

class UTC(tzinfo):
    def utcoffset(self, dt):
        return timedelta(0)
    def tzname(self, dt):
        return 'UTC'
    def dst(self, dt):
        return timedelta(0)
utc = UTC()

def is_gz_file(filepath):
    with open(filepath, 'rb') as test_f:
        return binascii.hexlify(test_f.read(2)) == b'1f8b'

def file_compare(filename1, filename2):
    if filename1[-3:] == '.gz':
        fh1 = gzip.open(filename1, mode='rb')
    else:
        fh1 = open(filename1, 'rb')
    if filename2[-3:] == '.gz':
        fh2 = gzip.open(filename2, mode='rb')
    else:
        fh2 = open(filename2, 'rb')
    result = None
    while result is None:
        buff1 = fh1.read(1024*1024)
        buff2 = fh2.read(1024*1024)
        if not buff1 and not buff2:
            result = True
        if buff1 != buff2:
            result = False
    fh1.close()
    fh2.close()
    return(result)

class ProcessMoves():
    def __init__(self):
        argparser = argparse.ArgumentParser()
        argparser.add_argument('-c', '--config', action='store', default='./move_to_repository.conf', \
                            help='Configuration file default=./move_to_repository.conf')
        argparser.add_argument('-l', '--log', action='store', \
                            help='Logging level (default=warning)')
        argparser.add_argument('--verbose', action='store_true', \
                            help='Verbose output')
        argparser.add_argument('--pdb', action='store_true', \
                            help='Run with Python debugger')
        self.args = argparser.parse_args()

        if self.args.pdb:
            pdb.set_trace()

        config_path = os.path.abspath(self.args.config)
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except ValueError, e:
            print 'ERROR: "{}" parsing config={}'.format(e, config_path)
            sys.exit(1)

        self.owner = self.config.get('owner', None)
        if self.owner:
            (user, group) = self.owner.split('.')
            self.owner_uid = pwd.getpwnam(user).pw_uid
            self.group_uid = grp.getgrnam(group).gr_gid
        self.perms = self.config.get('perms', None)
        self.stats = {
            'skipped': 0,
            'errors': 0,
            'moves': 0,
            'bytes': 0
        }

    def run(self, moveitem):
        start_ts = datetime.now(utc)
        start_moves = self.stats['moves']
        source_path = moveitem.get('source', '')
        if not os.path.isdir(source_path):
            print('ERROR: move source is not a directory: ' + source_path)
            return
        dest_path = moveitem.get('destination', '')
        if not os.path.isdir(dest_path):
            print('ERROR: move destination is not a directory: ' + dest_path)
            return
        print('Start moving from={} to={}'.format(source_path, dest_path))

     	move_filenames = [f for f in os.listdir(source_path) if os.path.isfile(os.path.join(source_path, f))]
        for filename in move_filenames:
            rc = self.move_one_file(os.path.join(source_path, filename), os.path.join(dest_path, filename))
        end_ts = datetime.now(utc)
        end_moves = self.stats['moves']
        print('Done  moving from={} files={} elapsed={}/seconds'.format(source_path, end_moves - start_moves, round((end_ts - start_ts).total_seconds(), 3)))

    def move_one_file(self, input_fqn, output_fqn): # Different paths with the same file name
        input_gz = is_gz_file(input_fqn)
        if (input_gz and input_fqn[-3:] != '.gz') or ( not input_gz and input_fqn[-3:] == '.gz'):
            print('ERROR: move source file extension and gzip contents do not match: ' + input_fqn)
            self.stats['errors'] += 1
            return
        if not input_gz:
            output_fqn += '.gz'                     # Gzip output if input isn't gzip'ed
        input_bytes = os.stat(input_fqn).st_size
        if os.path.exists(output_fqn):
            if not file_compare(input_fqn, output_fqn):         # Fall thru to copy input to output
                print('ERROR: move target exists: ' + output_fqn)
                self.stats['errors'] += 1
            else:
                try:
                    os.remove(input_fqn)
                    print('Removed input that matches file in repository: ' + input_fqn)
                    self.stats['skipped'] += 1
                except Exception, e:
                    print('ERROR: removing input that matches file in repostisory: ' + input_fqn)
                    self.stats['errors'] += 1
            return
            
        if input_gz:
            try:
                rc = os.rename(input_fqn, output_fqn)
            except Exception, e:
                print 'ERROR: "{}" moving file={}'.format(e, input_fqn)
                self.stats['errors'] += 1
                return
        else:
            try:
                with open(input_fqn, 'rb') as fh_read:
                    with gzip.open(output_fqn, mode='wb', compresslevel=9) as fh_write:
                        shutil.copyfileobj(fh_read, fh_write)
                os.remove(input_fqn)
            except Exception, e:
                print 'ERROR: "{}" gzip copy and remove file={}'.format(e, input_fqn)
                self.stats['errors'] += 1
                return
    
        self.stats['moves'] += 1
        output_bytes = os.stat(output_fqn).st_size
        if self.owner:
            os.chown(output_fqn, self.owner_uid, self.group_uid)
        if self.perms:
            os.chmod(output_fqn, int(self.perms, 8))

        print("Moved file={}, in_bytes={}, out_bytes={}".format(input_fqn, input_bytes, output_bytes))

    def finish(self):
        pass

if __name__ == '__main__':
    process = ProcessMoves()
    moves = process.config.get('moves', [])
    for each_move in moves:
        rc = process.run(each_move)
    rc = process.finish()
    sys.exit(rc)
