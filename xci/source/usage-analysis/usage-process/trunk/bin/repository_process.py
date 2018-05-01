#!/soft/metrics-tools/venv-1.0/bin/python

from __future__ import print_function
import argparse
import csv
import datetime
from datetime import datetime, tzinfo, timedelta
import fnmatch
import gzip
import json
import os
import re
import subprocess
import sys
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

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class RepositoryProcess():
    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-c', '--config', action='store', default='./repository_process.conf', \
                            help='Configuration file default=./repository_process.conf')
        parser.add_argument('-l', '--log', action='store', \
                            help='Logging level (default=warning)')
        parser.add_argument('--verbose', action='store_true', \
                            help='Verbose output')
        parser.add_argument('--pdb', action='store_true', \
                            help='Run with Python debugger')
        self.args = parser.parse_args()

        if self.args.pdb:
            pdb.set_trace()

        config_path = os.path.abspath(self.args.config)
        try:
            with open(config_path, 'r') as cf:
                self.config = json.load(cf)
        except ValueError, e:
            eprint('ERROR "{}" parsing config={}'.format(e, config_path))
            sys.exit(1)

        for c in ['file_status_file', 'source_dir', 'target_dir']:
            if not self.config.get(c, None):
                eprint('Missing config "{}"'.format(c))
                sys.exit(1)

        try:
            with open(self.config['file_status_file']) as fh:
                self.file_status = json.load(fh)
        except Exception as e:
            eprint('ERROR loading config={}, initializing'.format(self.config['file_status_file']))
            self.file_status = {}

        self.STEPS = {}
        step_re = re.compile('^step.(\d+)$', re.IGNORECASE)
        for c in self.config:
            c_match = step_re.match(c)
            if not c_match:
                continue
            self.STEPS[int(c_match.group(1))] = self.config[c]
            
        print_steps = []
        for s in sorted(self.STEPS):
            print_steps.append(self.STEPS[s].split()[0])
        eprint('Steps {}'.format(' | '.join(print_steps)))

        self.stats = {
            'skipped': 0,
            'errors': 0,
            'processed': 0,
            'entries': 0
        }

        SOURCE_DIR = self.config.get('source_dir', None)
        if not os.path.isdir(SOURCE_DIR):
            eprint('ERROR config source_dir={} is not a directory'.format(SOURCE_DIR))
            sys.exit(1)
        SOURCE_GLOB = self.config.get('source_glob', '*')
        files = [f for f in fnmatch.filter(os.listdir(SOURCE_DIR), SOURCE_GLOB) if os.path.isfile(os.path.join(SOURCE_DIR, f))]
        if len(files) == 0:
            eprint('WARNING no files in source_dir={} match source_glob={}'.format(SOURCE_DIR, SOURCE_GLOB))
            sys.exit(1)

        self.FILES = {}
        for f in files:
            self.FILES[f] = os.path.join(SOURCE_DIR, f)

        self.TARGET_DIR = self.config.get('target_dir', None)
        if not os.path.isdir(self.TARGET_DIR):
            eprint('ERROR config target_dir={} is not a directory'.format(self.TARGET_DIR))
            sys.exit(1)
        self.TARGET_EXTENSION = self.config.get('target_extension', None)

    def process_file(self, file_name, file_fqn):
    	this_history = self.file_status.get(file_fqn, {})
        input_stat = os.stat(file_fqn)
        input_mtime_str = str(datetime.fromtimestamp(input_stat.st_mtime))
        out_file_fqn = os.path.join(self.TARGET_DIR, file_name[:-3] + self.TARGET_EXTENSION + '.gz')
        if input_stat.st_size == this_history.get('in_size', None) and input_mtime_str == this_history.get('in_mtime', None) \
                and os.path.isfile(out_file_fqn):
            self.stats['skipped'] += 1
            return

        this_history['in_size'] = input_stat.st_size
        this_history['in_mtime'] = input_mtime_str
        eprint("Processing {} mtime={} size={}".format(file_name, input_mtime_str, input_stat.st_size))
          
        sp = {}
        for step in sorted(self.STEPS):
            commands = self.STEPS[step].split()
            if step == 1:
                commands.append(file_fqn)
                sp[step] = subprocess.Popen(commands, bufsize=1, stdout=subprocess.PIPE)
            else:
                sp[step] = subprocess.Popen(commands, bufsize=1, stdin=sp[step-1].stdout, stdout=subprocess.PIPE)
            last_stdout = sp[step].stdout
                
        try:
            with gzip.open(out_file_fqn, 'w') as output_f:
                for line in iter(last_stdout):
                    output_f.write(line)
            self.stats['processed'] += 1
        except subprocess.CalledProcessError, e:
            eprint('ERROR: "{}" in command pipe'.format(e))
            self.stats['errors'] += 1
 
        output_stat = os.stat(out_file_fqn)
        this_history['output'] = out_file_fqn
        this_history['out_size'] = output_stat.st_size
        this_history['out_mtime'] = str(datetime.fromtimestamp(output_stat.st_mtime))
    	self.file_status[file_fqn] = this_history

    def finish(self):
        try:
            with open(self.config['file_status_file'], 'w+') as file:
                json.dump(self.file_status, file, indent=4, sort_keys=True)
                file.close()
        except IOError:
            eprint('Failed to write config=' + self.config['file_status_file'])
            sys.exit(1)

if __name__ == '__main__':
    start_utc = datetime.now(utc)
    process = RepositoryProcess()
    for file in sorted(process.FILES):
        rc = process.process_file(file, process.FILES[file])
    end_utc = datetime.now(utc)
    eprint("Processed files={}, seconds={}, skipped={}, errors={}".format(
        process.stats['processed'], (end_utc - start_utc).total_seconds(), 
        process.stats['skipped'], process.stats['errors']))
    rc = process.finish()
