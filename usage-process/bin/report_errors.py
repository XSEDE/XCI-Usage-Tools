#!/soft/XCI-Usage-Tools/python/bin/python3
import argparse
from collections import Counter
import datetime
from datetime import datetime, timedelta
import fnmatch
import json
import logging
import logging.handlers
import os
import pytz
import re
import smtplib
#from smtplib import SMTP
import sys
import pdb

CENTRAL = pytz.timezone('US/Central')

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class ReportErrors():
    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-c', '--config', action='store', default='./report_errors.conf', \
                            help='Configuration file default=./report_errors.conf')
        parser.add_argument('-l', '--log', action='store', \
                            help='Logging level (default=warning)')
        parser.add_argument('--verbose', action='store_true', \
                            help='Verbose output')
        parser.add_argument('--pdb', action='store_true', \
                            help='Run with Python debugger')
        self.args = parser.parse_args()

        if self.args.pdb:
            pdb.set_trace()

        self.config = {'LOG_FILE': 'report_errors.log'}

        config_path = os.path.abspath(self.args.config)
        try:
            with open(config_path, 'r') as cf:
                self.config = json.load(cf)
        except ValueError as e:
            eprint('ERROR "{}" parsing config={}'.format(e, config_path))
            sys.exit(1)

        self.Setup_Logging()
        self.Setup_Config()
        self.Setup_FindFiles()

    def Setup_Logging(self):
        # Initialize logging from arguments, or config file, or default to WARNING as last resort
        loglevel_string = (self.args.log or self.config.get('LOG_LEVEL') or 'WARNING').upper()
        loglevel_number = getattr(logging, loglevel_string, None)
        if not isinstance(loglevel_number, int):
            raise ValueError('Invalid log level={}'.format(loglevel_number))
        self.logger = logging.getLogger('DaemonLog')
        self.logger.setLevel(loglevel_number)
        self.formatter = logging.Formatter(fmt='%(asctime)s.%(msecs)03d %(levelname)s %(message)s', \
                                           datefmt='%Y/%m/%d %H:%M:%S')
        self.handler = logging.handlers.TimedRotatingFileHandler(self.config['LOG_FILE'], when='W6', \
                                                                 backupCount=999, utc=True)
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)

    def Setup_Config(self):
        try:
            self.PAST_DAYS = int(self.config.get('PAST_DAYS', '1'))
        except:
            self.logger.error('Config PAST_DAYS is not numeric: "{}"'.format(self.PAST_DAYS))
            self.exit(1)
        # Earliest relevant date
        self.START_DATE = (datetime.now() + timedelta(days=-self.PAST_DAYS)).date()

        # Logging line parsing regular expression
        #LOG_REGEX = '(?P<datetime>\S+ \S+) (?P<level>\S+) (?P<REST>\S+)'
        LOG_REGEX = self.config.get('LOG_REGEX')
        if not LOG_REGEX:
            self.logger.error('Config LOG_REGEX is missing')
            self.exit(1)
        self.REGCOMP = re.compile(LOG_REGEX)

        # Logging date parsing format
        #self.INPUT_DATE_FORMAT = '%Y/%m/%d %H:%M:%S.%f'     # A datetime.strptime format
        self.INPUT_DATE_FORMAT = self.config.get('INPUT_DATE_FORMAT')
        if not self.INPUT_DATE_FORMAT:
            self.logger.error('Config INPUT_DATE_FORMAT is missing')
            self.exit(1)
 
        self.SOURCE_DIRS = self.config.get('SOURCE_DIRS')
        if not self.SOURCE_DIRS:
            self.logger.error('Config SOURCE_DIRS is missing')
            self.exit(1)
        if not isinstance(self.SOURCE_DIRS, list):
            self.SOURCE_DIRS = [self.SOURCE_DIRS]

        self.SOURCE_FILEGLOB = self.config.get('SOURCE_FILEGLOB')
        if not self.SOURCE_FILEGLOB:
            self.logger.error('Config SOURCE_FILEGLOB is missing')
            self.exit(1)

        self.ERROR_EMAILS = self.config.get('ERROR_EMAILS')
        if not self.ERROR_EMAILS:
            self.logger.error('Config ERROR_EMAILS is missing')
            self.exit(1)
        if not isinstance(self.ERROR_EMAILS, list):
            self.ERROR_EMAILS = [self.ERROR_EMAILS]

    def Setup_FindFiles(self):
        self.ERRORS = {}
        self.STATS = Counter()

        self.LOGFILES = []          # fully qualified filenames
        for DIR in self.SOURCE_DIRS:
            if not os.path.isdir(DIR):
                self.logger.error('Specified source_dir={} is not a directory'.format(DIR))
                self.exit(1)
            files = [file for file in fnmatch.filter(os.listdir(DIR), self.SOURCE_FILEGLOB) if os.path.isfile(os.path.join(DIR, file))]
            if len(files) == 0:
                self.logger.warning('Specified source_dir={} has no files that match source_glob={}'.format(DIR, self.SOURCE_FILEGLOB))
            for f in files:
                self.LOGFILES.append(os.path.join(DIR, f))

    def Process_Logfile(self, file_fqn):
        self.STATS.update('files')
        with open(file_fqn, 'r') as IN_FILE:
            for line in IN_FILE:
                match = self.REGCOMP.match(line)
                if not match: continue
                try:
                    log_datetime = datetime.strptime(match.group('datetime'), self.INPUT_DATE_FORMAT)
                except:
                    continue
                if log_datetime.date() < self.START_DATE:
                    continue
                if match.group('level') in ['INFO']:
                    continue
                self.STATS.update('errors')
                if file_fqn not in self.ERRORS:
                    self.ERRORS[file_fqn] = []
                self.ERRORS[file_fqn].append(line)
                
    def MailErrors(self):
        if not self.ERRORS: return
        MSG = "Subject: XCI recent metrics errors on {}\r\n".format(datetime.strftime(datetime.now(CENTRAL), "%Y-%m-%d"))
        FROM = "info-serv-admin@xsede.org"
        MSG += "From: {}\r\n".format(FROM)
        MSG += "To: {}\r\n".format(','.join(self.ERROR_EMAILS))
        MSG += "\r\n"
        for file, errors in self.ERRORS.items():
            MSG += "*** {}\r\n\r\n".format(file)
            for line in errors:
                MSG += line
            MSG += "\r\n"
        server = smtplib.SMTP('localhost')
#       server.set_debuglevel(1)
        server.sendmail(FROM, self.ERROR_EMAILS, MSG)
        server.quit()

    def exit(self, rc = 0):
        sys.exit(rc)

if __name__ == '__main__':
    start_utc = datetime.utcnow()
    process = ReportErrors()
    try:
        for file in sorted(process.LOGFILES):
            rc = process.Process_Logfile(file)
        process.MailErrors()
    except Exception as e:
        process.logger.critical('Processing exception={}'.format(e))
        process.exit(1)
    end_utc = datetime.utcnow()
    process.logger.info("Processed files={}, seconds={}, errors={}".format(
        process.STATS['files'], (end_utc - start_utc).total_seconds(), process.STATS['errors']))
    process.exit(0)
