#!/soft/XCI-Usage-Tools/python/bin/python3
import argparse
import csv
import fnmatch
import gzip
import json
import logging
import logging.handlers
import os
import re
#import socket, struct
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
        self.ROWS_BEFORE = 0
        self.ROWS_AFTER = 0

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
        numeric_log = None
        if self.args.log is not None:
            numeric_log = getattr(logging, self.args.log.upper(), None)
        if numeric_log is None and self.config.get('LOG_LEVEL'):
            numeric_log = getattr(logging, self.config['LOG_LEVEL'].upper(), None)
        if numeric_log is None:
            numeric_log = getattr(logging, 'WARNING', None)
        if not isinstance(numeric_log, int):
            raise ValueError('Invalid log level: {}'.format(numeric_log))
        self.logger = logging.getLogger('DaemonLog')
        self.logger.setLevel(numeric_log)
        program = os.path.basename(__file__)
        self.formatter = logging.Formatter(fmt='%(asctime)s.%(msecs)03d %(levelname)s {} %(message)s'.format(program),
                                           datefmt='%Y/%m/%d %H:%M:%S')
        
        LOGFILE = self.config.get('LOG_FILE', 'stdout')
        if LOGFILE.lower() == 'stdout':
            self.handler = logging.StreamHandler(sys.stdout)
        else:
            self.handler = logging.handlers.FileHandler(self.config['LOG_FILE'])
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)

        signal.signal(signal.SIGINT, self.exit_signal)
        signal.signal(signal.SIGTERM, self.exit_signal)

        self.logger.debug('Starting pid={}, uid={}({})'.format(os.getpid(), os.geteuid(), pwd.getpwuid(os.geteuid()).pw_name))

        USER_FILTER_FILE = self.config.get('user_filter_file')
        self.USER_FILTER = None
        if USER_FILTER_FILE:
            try:
                with open(USER_FILTER_FILE) as fh:
                   self.USER_FILTER = json.load(fh)
            except Exception as e:
                self.logger.error('Loading user map={}'.format(USER_FILTER_FILE))
                sys.exit(1)

        CLIENT_FILTER_FILE = self.config.get('client_filter_file')
        self.CLIENT_FILTER = None
        if CLIENT_FILTER_FILE:
            try:
                with open(CLIENT_FILTER_FILE) as fh:
                   self.CLIENT_FILTER = json.load(fh)
            except Exception as e:
                self.logger.error('Loading client map={}'.format(CLIENT_FILTER_FILE))
                sys.exit(1)

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
            self.logger.error('File is missing USED_COMPONENT field: {}'.format(self.args.file))
            self.exit(1)

        self.OUT_WRITER = csv.DictWriter(sys.stdout, fieldnames=self.IN_READER._fieldnames, delimiter=',', quotechar='|')
        self.OUT_WRITER.writeheader()

    def Process(self):
        self.start_ts = datetime.utcnow()
        INPUT = self.IN_READER
        OUTPUT = self.OUT_WRITER
        for row in INPUT:
            self.ROWS_BEFORE += 1
            if self.USER_FILTER:
                row = self.filter_action_simple(row, 'USE_USER', self.USER_FILTER)
                if not row: continue
            if self.CLIENT_FILTER:
                row = self.filter_action_subnet(row, 'USE_CLIENT', self.CLIENT_FILTER)
                if not row: continue
            if self.CILOGON_USE_CLIENT:
                row = self.filter_action_cilogon_use_client(row, 'USE_CLIENT')
                if not row: continue
            OUTPUT.writerow(row)
            self.ROWS_AFTER += 1

        self.end_ts = datetime.utcnow()
        seconds = (self.end_ts - self.start_ts).total_seconds()
        rate = self.ROWS_BEFORE / seconds
        self.logger.info('Read {}/rows wrote {}/rows in seconds={} rate={} rows/second'.format(
            self.ROWS_BEFORE, self.ROWS_AFTER, round(seconds, 2), round(rate, 0) ))

    ##########################################################################
    # Simple filter based on exact field match
    ##########################################################################
    def filter_action_simple(self, row, field, filter_rules):
        try:
            action = filter_rules[row[field]]
            action_fields = action.split(':', 1)        # Actions are "DELETE", "MAP:<replacement_value>"
            command = action_fields[0].lower()
            if command == 'delete':
                return(None)  
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
            if command == 'delete':
                return(None)  
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
               if command == 'delete':
                   return(None)  
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
    def exit_signal(self, signum, frame):
        self.logger.critical('Caught signal={}({}), exiting with rc={}'.format(signum, signal.Signals(signum).name, signum))
        self.exit(signum)

    def exit(self, rc = 0):
        if self.IN_FD:
            self.IN_FD.close()
        if self.OUT_WRITER:
            self.OUT_WRITER.close()
        sys.exit(rc)

if __name__ == '__main__':
    me = Filter()
    me.Setup()
    me.Process()
    me.exit(0)
