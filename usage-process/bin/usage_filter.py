#!/soft/XCI-Usage-Tools/python/bin/python3
import argparse
import csv
from datetime import datetime
import fnmatch
import gzip
import json
import logging
import logging.handlers
import os
import pwd
import re
import signal
import sys
import pdb

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def ip_to_u32(ip):
  return int(''.join('%02x' % int(d) for d in ip.split('.')), 16)

class Filter():
    def __init__(self):
        # Variales that must be defined
        self.IN_FD = None
        self.OUT_FD = None
        self.IN_ROWS = 0
        self.OUT_ROWS = 0

        parser = argparse.ArgumentParser()
        parser.add_argument('file', nargs='?')
        parser.add_argument('-c', '--config', action='store', default='./repository_process.conf', \
                            help='Configuration file default=./repository_process.conf')
        parser.add_argument('-l', '--log', action='store',
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
            self.exit(1)

    def Setup(self):
        # Initialize logging from arguments or config file, with WARNING level as default
        loglevel_string = (self.args.log or self.config.get('LOG_LEVEL') or 'WARNING').upper()
        loglevel_number = getattr(logging, loglevel_string, None)
        if not isinstance(loglevel_number, int):
            raise ValueError('Invalid log level={}'.format(loglevel_number))
        self.logger = logging.getLogger('DaemonLog')
        self.logger.setLevel(loglevel_number)
        PROGRAM = os.path.basename(__file__)
        self.formatter = logging.Formatter(fmt='%(asctime)s.%(msecs)03d %(levelname)s {} %(message)s'.format(PROGRAM),
                                           datefmt='%Y/%m/%d %H:%M:%S')
        
        LOG_FILE = self.config.get('LOG_FILE', 'stdout')
        if LOG_FILE.lower() == 'stdout':
            self.handler = logging.StreamHandler(sys.stdout)
        else:
            self.handler = logging.FileHandler(LOG_FILE)
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)

        signal.signal(signal.SIGINT, self.exit_signal)
        signal.signal(signal.SIGTERM, self.exit_signal)

        self.logger.debug('Starting pid={}, uid={}({})'.format(os.getpid(), os.geteuid(), pwd.getpwuid(os.geteuid()).pw_name))

        COMPONENT_FILTER_FILE = self.config.get('component_filter_file')
        self.COMPONENT_FILTER = None
        if COMPONENT_FILTER_FILE:
            try:
                with open(COMPONENT_FILTER_FILE) as fh:
                   self.COMPONENT_FILTER = json.load(fh)
            except Exception as e:
                self.logger.error('{} loading file={}'.format(e, COMPONENT_FILTER_FILE))
                self.exit(1)

        USER_FILTER_FILE = self.config.get('user_filter_file')
        self.USER_FILTER = None
        if USER_FILTER_FILE:
            try:
                with open(USER_FILTER_FILE) as fh:
                   self.USER_FILTER = json.load(fh)
            except Exception as e:
                self.logger.error('{} loading user map={}'.format(e, USER_FILTER_FILE))
                self.exit(1)

        CLIENT_FILTER_FILE = self.config.get('client_filter_file')
        self.CLIENT_FILTER = None
        if CLIENT_FILTER_FILE:
            try:
                with open(CLIENT_FILTER_FILE) as fh:
                   self.CLIENT_FILTER = json.load(fh)
            except Exception as e:
                self.logger.error('{} loading client map={}'.format(e, CLIENT_FILTER_FILE))
                self.exit(1)

        # Convert client filters into networks
        self.CLIENT_NETS = {}
        if self.CLIENT_FILTER:
            for cidr in self.CLIENT_FILTER:
                if '/' in cidr:
                    netstr, bits = cidr.split('/')
                    mask = (0xffffffff << (32 - int(bits))) & 0xffffffff
                    net = ip_to_u32(netstr) & mask
                    self.CLIENT_NETS[cidr] = (mask, net)

        self.CILOGON_USE_CLIENT = self.config.get('cilogon_use_client')

        REGEX_FILTER_FILE = self.config.get('regex_filter_file')
        if REGEX_FILTER_FILE:
            try:
                with open(REGEX_FILTER_FILE) as fh:
                   REGEX_FILTER_CONF = json.load(fh)
            except Exception as e:
                self.logger.error('{} loading regex_filter_file={}'.format(e, REGEX_FILTER_FILE))
                self.exit(1)
        # Convert from {<fld1>: [<fld1reg1>, !<fld1reg2>], <fld2> ...]
        #           to {True: {<fld1>: [<fld1reg1>]},
        #              {False: {<fld1>: [<fld1reg2>]}
        # ALL regex must be true for a row to match
        self.REGEX_FILTERS = {}
        try:
            for FLD, REGEXS in REGEX_FILTER_CONF.items():
                for REGEX in REGEXS:
                    if REGEX[0:1] == '!':
                        REGEX = REGEX[1:]
                        MATCH = False 
                    else:
                        MATCH = True
                    if MATCH not in self.REGEX_FILTERS: self.REGEX_FILTERS[MATCH] = {}
                    if FLD not in self.REGEX_FILTERS[MATCH]: self.REGEX_FILTERS[MATCH][FLD] = list()
                    self.REGEX_FILTERS[MATCH][FLD].append(re.compile(REGEX))
        except:
            self.logger.error('Compiling regex_filter_file reg: {}'.format(REGEX))
            self.exit(1)

#       USED_RESOURCE_REGEXS_CONFIG = self.config.get('used_resource_regexs')
#       self.USED_RESOURCE_REGEXS = list()
#       if USED_RESOURCE_REGEXS_CONFIG:
#           # Pre-compile all the regular expressions
#           for REGEX in USED_RESOURCE_REGEXS_CONFIG:
#               try:
#                   self.USED_RESOURCE_REGEXS.append(re.compile(REGEX))
#               except:
#                   self.logger.error('used_resource_regexs compile failed: {}'.format(REGEX))
#                   self.exit(1)

        if self.args.file:
            if self.args.file[-3:] == '.gz':
                self.IN_FD = gzip.open(self.args.file, mode='rt')
            else:
                self.IN_FD = open(self.args.file, mode='r')
        else:
            self.IN_FD = sys.stdin
        
        self.IN_READER = csv.DictReader(self.IN_FD, delimiter=',', quotechar='|')
        if not self.IN_READER.fieldnames:
            if self.IN_READER.line_num == 0:
                self.logger.info('Input file empty')
                self.exit(0)
            else:
                self.logger.error('Input file is missing CSV fields in first row')
                self.exit(1)

        if 'USED_COMPONENT' not in self.IN_READER.fieldnames:
            self.logger.error('Input file is missing field=USED_COMPONENT')
            self.exit(1)

        for M in (True, False):
            if M not in self.REGEX_FILTERS: continue
            for F in self.REGEX_FILTERS[M]:
                if F not in self.IN_READER.fieldnames:
                    self.logger.error('Input file is missing REGEX field={}'.format(F))
                    self.exit(1)
                
        self.OUT_FD = sys.stdout
        self.OUT_WRITER = csv.DictWriter(self.OUT_FD, fieldnames=self.IN_READER._fieldnames, delimiter=',', quotechar='|')
        self.OUT_WRITER.writeheader()

    def Process(self):
        self.start_ts = datetime.utcnow()
        for row in self.IN_READER:
            self.IN_ROWS += 1
            if self.COMPONENT_FILTER:
                row = self.filter_action_simple(row, 'USED_COMPONENT', self.COMPONENT_FILTER)
                if not row: continue
            if self.USER_FILTER:
                row = self.filter_action_simple(row, 'USE_USER', self.USER_FILTER)
                if not row: continue
            if self.CLIENT_FILTER:
                row = self.filter_action_subnet(row, 'USE_CLIENT', self.CLIENT_FILTER)
                if not row: continue
            if self.CILOGON_USE_CLIENT:
                row = self.filter_action_cilogon_use_client(row, 'USE_CLIENT')
                if not row: continue
#           if self.USED_RESOURCE_REGEXS:
#               row = self.filter_action_regexs(row, 'USED_RESOURCE', self.USED_RESOURCE_REGEXS)
            if self.REGEX_FILTERS:
                row = self.filter_action_regexs(row, self.REGEX_FILTERS)
                if not row: continue
            self.OUT_WRITER.writerow(row)
            self.OUT_ROWS += 1

        self.end_ts = datetime.utcnow()
        seconds = (self.end_ts - self.start_ts).total_seconds()
        self.logger.info('in={}/rows out={}/rows seconds={} in_rows/second={} '.format(
            self.IN_ROWS, self.OUT_ROWS, round(seconds, 2), round(self.IN_ROWS / seconds, 0) ))

    ##########################################################################
    # Simple filter based on exact field match
    ##########################################################################
    def filter_action_simple(self, row, field, filter_rules):
        try:
            action = filter_rules[row[field]]
            action_fields = action.split(':', 1)        # Actions are "DELETE", "MAP:<replacement_value>"
            command = action_fields[0].lower()
            if command == 'delete': return(None)
            if command == 'map':
                row[field] = action_fields[1]
        except:
            pass
        return(row)

    ##########################################################################
    # Complex subnet <subnet>/<bits> field match
    ##########################################################################
    def filter_action_subnet(self, row, field, filter_rules):
        try:
            action = filter_rules[row[field]]
            action_fields = action.split(':', 1)        # Actions are "DELETE", "MAP:<replacement_value>"
            command = action_fields[0].lower()
            if command == 'delete': return(None)  
            if command == 'map':
                row[field] = action_fields[1]
            return(row)
        except:
            pass
        # In Python3
        #ip = ipaddress.IPv4Address(row[field])
        # In Python2
        ip = ip_to_u32(row[field])
        for rule, network in iter(self.CLIENT_NETS.items()):
            mask, net = network
            if ip & mask == net:
               action = self.CLIENT_FILTER[rule]
               action_fields = action.split(':', 1)        # Actions are "DELETE", "MAP:<replacement_value>"
               command = action_fields[0].lower()
               if command == 'delete': return(None)
               if command == 'map':
                   row[field] = action_fields[1]
               return(row)
        return(row)

    ##########################################################################
    # Custom filter for cilogon use_client
    ##########################################################################
    def filter_action_cilogon_use_client(self, row, field):
        client = row.get(field,'')
        if client.lower() not in ('ecp', 'pkcs12', ''):
            row[field] = 'OAUTH_client_name:{}'.format(client)
        return(row)

    ##########################################################################
    # Complex multiple regex matching filter
    ##########################################################################
#   def filter_action_regexs(self, row, field, filter_regexs):
#       val = row.get(field, '')
#       for regex in filter_regexs:
#           match = re.search(regex, val)
#           if not match: return(None)
    def filter_action_regexs(self, row, filter_regexs):
        for WANT_MATCH, NEGDICT in filter_regexs.items():
            for FLD, REGEXS in NEGDICT.items():
                VAL = row.get(FLD, '')
                for REGEX in REGEXS:
                    match = re.search(REGEX, VAL)
                    if bool(match) != WANT_MATCH: return(None)
        return(row)

    ##########################################################################
    def exit_signal(self, signum, frame):
        self.logger.critical('Caught signal={}({}), exiting with rc={}'.format(signum, signal.Signals(signum).name, signum))
        self.exit(signum)

    def exit(self, rc = 0):
        if self.IN_FD:
            self.IN_FD.close()
        if self.OUT_FD:
            self.OUT_FD.close()
        sys.exit(rc)

if __name__ == '__main__':
    me = Filter()
    me.Setup()
    me.Process()
    me.exit(0)
