#!/soft/XCI-Usage-Tools/python/bin/python3

import argparse
import csv
import datetime
from datetime import datetime, tzinfo, timedelta, timezone
import fnmatch
import gzip
import json
import logging
import logging.handlers
import os
from pid import PidFile, PidFileError
import re
import subprocess
import sys
import pdb
from stat import *

#class UTC(tzinfo):
#    def utcoffset(self, dt):
#        return timedelta(0)
#    def tzname(self, dt):
#        return 'UTC'
#    def dst(self, dt):
#        return timedelta(0)
#utc = UTC()

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
        except ValueError as e:
            eprint('ERROR "{}" parsing config={}'.format(e, config_path))
            sys.exit(1)

        if self.config.get('PID_FILE'):
            self.pidfile_path = self.config['PID_FILE']
        else:   # Only one program may run per status file
            self.pidfile_path = self.config['file_status_file'] + '.pid'

    def Setup_Logging(self):
        # Initialize logging from arguments, or config file, or default to WARNING as last resort
        numeric_log = None
        if self.args.log is not None:
            numeric_log = getattr(logging, self.args.log.upper(), None)
        if numeric_log is None and 'LOG_LEVEL' in self.config:
            numeric_log = getattr(logging, self.config['LOG_LEVEL'].upper(), None)
        if numeric_log is None:
            numeric_log = getattr(logging, 'WARNING', None)
        if not isinstance(numeric_log, int):
            raise ValueError('Invalid log level: {}'.format(numeric_log))
        self.logger = logging.getLogger('DaemonLog')
        self.logger.setLevel(numeric_log)
        self.formatter = logging.Formatter(fmt='%(asctime)s.%(msecs)03d %(levelname)s %(message)s', \
                                           datefmt='%Y/%m/%d %H:%M:%S')
        self.handler = logging.handlers.TimedRotatingFileHandler(self.config['LOG_FILE'], when='W6', \
                                                                 backupCount=999, utc=True)
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)

    def Setup(self):
        for c in ['file_status_file', 'source_dir', 'target_dir']:
            if not self.config.get(c, None):
                self.logger.error('Missing config "{}"'.format(c))
                self.exit(1)

        try:
            with open(self.config['file_status_file']) as fh:
                self.FILE_STATUS = json.load(fh)
        except IOError as e:
            self.logger.error('IO Error loading status={}, initializing'.format(self.config['file_status_file']))
            self.FILE_STATUS = {}
        except json.JSONDecodeError as e:
            self.logger.error('Status file json error "{}", QUITTING'.format(e))
            self.exit(1)

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
        self.logger.info('Steps {}'.format(' | '.join(print_steps)))

        self.stats = {
            'skipped': 0,
            'errors': 0,
            'processed': 0,
            'entries': 0
        }

        SOURCE_DIRS = [d for d in self.config.get('source_dir', '').split(',') if d]
        SOURCE_GLOB = self.config.get('source_glob', '*')
        self.IN_FILES = {}          # key=filename, value=fully qualified file
        for DIR in SOURCE_DIRS:
            if not os.path.isdir(DIR):
                self.logger.error('Specified source_dir={} is not a directory'.format(DIR))
                self.exit(1)
            files = [file for file in fnmatch.filter(os.listdir(DIR), SOURCE_GLOB) if os.path.isfile(os.path.join(DIR, file))]
            if len(files) == 0:
                self.logger.warning('Specified source_dir={} has no files that match source_glob={}'.format(DIR, SOURCE_GLOB))
            for f in files:
                self.IN_FILES[f] = os.path.join(DIR, f)

        self.TARGET_DIR = self.config.get('target_dir', None)
        if not os.path.isdir(self.TARGET_DIR):
            self.logger.error('Specified target_dir={} is not a directory'.format(self.TARGET_DIR))
            self.exit(1)
        self.TARGET_EXTENSION = self.config.get('target_extension', None)

    def process_file(self, file_name, file_fqn):
        this_history = self.FILE_STATUS.get(file_fqn, {})
        input_stat = os.stat(file_fqn)
        input_mtime_str = str(datetime.fromtimestamp(input_stat.st_mtime, tz=timezone.utc))
        newext = getattr(self, 'TARGET_EXTENSION')
        if not newext:
            newext = ''
        out_file_fqn = os.path.join(self.TARGET_DIR, file_name[:-3] + newext + '.gz')
        if input_stat.st_size == this_history.get('in_size', None) and input_mtime_str == this_history.get('in_mtime', None) \
                and os.path.isfile(out_file_fqn):
            self.stats['skipped'] += 1
            return

        this_history['in_size'] = input_stat.st_size
        this_history['in_mtime'] = input_mtime_str
        self.logger.info("Processing {} mtime={} size={}".format(file_name, input_mtime_str, input_stat.st_size))
          
        sp = {}
        for stepidx in sorted(self.STEPS):
            cmdlist = self.STEPS[stepidx].split()
            if stepidx == 1:
                cmdlist.append(file_fqn)
                sp[stepidx] = subprocess.Popen(cmdlist, bufsize=1, stdout=subprocess.PIPE)
            else:
                sp[stepidx] = subprocess.Popen(cmdlist, bufsize=1, stdin=sp[stepidx-1].stdout, stdout=subprocess.PIPE)
            if self.args.verbose:
                self.logger.debug('Step.{}: {}'.format(stepidx, ' '.join(cmdlist)))
            last_stdout = sp[stepidx].stdout
                
        try:
            with gzip.open(out_file_fqn, 'w') as output_f:
                for line in iter(last_stdout):
                    output_f.write(line)
            self.stats['processed'] += 1
        except subprocess.CalledProcessError as e:
            self.logger.error('Raised "{}" in command pipe'.format(e))
            self.stats['errors'] += 1

        output_stat = os.stat(out_file_fqn)
        this_history['output'] = out_file_fqn
        this_history['out_size'] = output_stat.st_size
        this_history['out_mtime'] = str(datetime.fromtimestamp(output_stat.st_mtime, tz=timezone.utc))
        self.FILE_STATUS[file_fqn] = this_history
        self.save_status()

    def save_status(self):
        try:
            with open(self.config['file_status_file'], 'w+') as file:
                json.dump(self.FILE_STATUS, file, indent=4, sort_keys=True)
                file.close()
        except IOError:
            self.logger.error('Failed to write status=' + self.config['file_status_file'])
            self.exit(1)

    def exit(self, rc = 0):
        sys.exit(rc)

if __name__ == '__main__':
    start_utc = datetime.now(timezone.utc)
    process = RepositoryProcess()
    process.Setup_Logging()
    try:
        with PidFile(process.pidfile_path):
            process.Setup()
            for file in sorted(process.IN_FILES):
                rc = process.process_file(file, process.IN_FILES[file])
    except PidFileError:
        process.logger.critical('Pidfile lock error: {}'.format(process.pidfile_path))
        sys.exit(1)
    except Exception as e:
        process.logger.critical('Setup exception={}'.format(e))
        sys.exit(1)
    end_utc = datetime.now(timezone.utc)
    process.logger.info("Processed files={}, seconds={}, skipped={}, errors={}".format(
        process.stats['processed'], (end_utc - start_utc).total_seconds(), 
        process.stats['skipped'], process.stats['errors']))
    process.exit(0)
