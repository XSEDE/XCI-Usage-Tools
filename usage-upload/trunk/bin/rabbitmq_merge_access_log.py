#!/usr/bin/env python
#
# Merges RabbitMQ access.log.2020_01_27_17 like hourly files into access.log-20200127.gz like daily files
#
# Developed on 2020-01-28 by JP Navarro
#

import argparse
from datetime import datetime, timedelta
import glob
import gzip
import logging
import logging.handlers
import os
from pathlib import Path
import pwd
import re
import shutil
import sys

class Process():
    def __init__(self):
        self.START_UTC = datetime.utcnow()
        parser = argparse.ArgumentParser()
#       parser.add_argument('-c', '--config', action='store', default='./merge_rabbitmq_access_log.conf', \
#                           help='Configuration file default=./merge_rabbitmq_access_log.conf')
        parser.add_argument('-l', '--log', action='store', \
                            help='Logging level (default=warning)')
        parser.add_argument('--verbose', action='store_true', \
                            help='Verbose output')
        parser.add_argument('--pdb', action='store_true', \
                            help='Run with Python debugger')
        self.args = parser.parse_args()

        if self.args.pdb:
            pdb.set_trace()

        # Hardcoded config because we don't want to have a config file
        self.config = {'LOG_FILE': '/soft/usage-upload/var/merge_rabbitmq_access_log.log'}

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

        self.logger.info('Starting program={} pid={}, uid={}({})'.format(os.path.basename(
            __file__), os.getpid(), os.geteuid(), pwd.getpwuid(os.geteuid()).pw_name))

        self.FILEDIR = '/var/log/rabbitmq/'
        self.FILEGLOB = 'access.log.*'
        self.logger.info('Merging files {}{}'.format(self.FILEDIR, self.FILEGLOB))
        os.chdir(self.FILEDIR)

        # Input file pattern
        self.INPATTERN = re.compile(r'^access.log.([0-9]{4})_([0-9]{2})_([0-9]{2})_([0-9]{2})$')
        # Hourly input files in dict keyed by date: {<date_string>: [<hourly_filename1>, <hourly_filename2>, ...], ...}
        self.INFILES = {}
        # Size of all the input files
        self.INSIZE = 0

        # Only process input files thru the day before yesterday
        self.INDATELIMIT = (datetime.today()-timedelta(days=2)).strftime('%Y%m%d')

        # Output file pattern
        self.OUTPATTERN = re.compile(r'^access.log.([0-9]{8}).gz$')
        # Daily output files dict keyed by date: {<date_string>: <daily_filename>, ...}
        self.OUTFILES = {}
        # Size _increase_ of output files (we may append to existing files)
        self.OUTSIZE = 0

    def run(self):
        #
        # Find all the relevant files and index them as INFILES or OUTFILES
        # There are multiple INFILES in a day since they are hourly
        #
        files = glob.glob(self.FILEGLOB)
        for f in files:
            inmatch = re.search(self.INPATTERN, f)
            if inmatch:
                indate = inmatch.group(1) + inmatch.group(2) + inmatch.group(3)
                if indate > self.INDATELIMIT:
                    continue
                if indate not in self.INFILES:
                    self.INFILES[indate] = [f]
                else:
                    self.INFILES[indate].append(f)
                continue

            outmatch = re.search(self.OUTPATTERN, f)
            if outmatch:
                outdate = outmatch.group(1)
                self.OUTFILES[outdate] = f

        #
        # Process the input files in date order and in filename/hourly order
        #
        tmpfile = '.access.log.tmp'
        tmpfilegz = '.access.log.tmp.gz'

        for adate in sorted(self.INFILES):
            if Path(tmpfile).exists():
                Path(tmpfile).unlink()

            # When the destination file exists, unzip it to a temp file to append to it
            if adate in self.OUTFILES:
                self.logger.debug('Unzipping existing file: '.format(self.OUTFILES[adate]))
                with gzip.open(self.OUTFILES[adate], 'rb') as f_in:
                    with open(tmpfile, 'wb') as f_out:
                       shutil.copyfileobj(f_in, f_out)

            # Append the current date files in hourly/filename order
            with open(tmpfile, 'a') as a_out:
                for afile in sorted(self.INFILES[adate]):
                    with open(afile, 'r') as a_in:
                        shutil.copyfileobj(a_in, a_out)
                    self.logger.debug('Appended {} <- {} (size={})'.format(tmpfile, afile, os.stat(tmpfile).st_size))

            if Path(tmpfilegz).exists():
                Path(tmpfilegz).unlink()

            with gzip.open(tmpfilegz, 'wb') as f_out:
                with open(tmpfile, 'rb') as f_in:
                    shutil.copyfileobj(f_in, f_out)

            # If the file we appended to isn't bigger than the original something is very wrong
            if adate in self.OUTFILES and os.stat(tmpfilegz).st_size < os.stat(self.OUTFILES[adate]).st_size:
                self.logger.critical('FATAL: new file is smaller than the one it replaces {}: {}/new, {}/existing'.format(
                    self.OUTFILES[adate], os.stat(tmpfilegz).st_size, os.stat(self.OUTFILES[adate]).st_size))
                sys.exit(1)

            if adate in self.OUTFILES:
                self.OUTSIZE += (os.stat(tmpfilegz).st_size - os.stat(self.OUTFILES[adate]).st_size)
            else:
                self.OUTSIZE += os.stat(tmpfilegz).st_size
                self.OUTFILES[adate] = 'access.log.{}.gz'.format(adate)

            Path(tmpfilegz).rename(self.OUTFILES[adate])   # Silently replaces on Unix
            Path(tmpfile).unlink()

            for afile in self.INFILES[adate]:
                self.INSIZE += os.stat(afile).st_size
                Path(afile).unlink()

    def summarize(self):
        self.END_UTC = datetime.utcnow()
        self.logger.info('Merged {}/files, in {}/seconds, saved {}/bytes'.format(
                len(self.INFILES), (self.END_UTC - self.START_UTC).total_seconds(), (self.INSIZE - self.OUTSIZE)
            ))

if __name__ == '__main__':
    process = Process()
    rc = process.run()
    process.summarize()
    sys.exit(rc)
