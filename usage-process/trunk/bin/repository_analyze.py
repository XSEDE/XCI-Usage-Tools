#!/soft/usage-process-python/bin/python

from __future__ import print_function
import argparse
import csv
import fnmatch
import gzip
import json
import logging
import logging.handlers
import os
import re
import socket
import sys
import pdb

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class Analyze():
    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-c', '--config', action='store', default='./repository_process.conf', \
                            help='Configuration file default=./repository_process.conf')
        parser.add_argument('-p', '--path', action='store', \
                            help='Directory path where files are located')
        parser.add_argument('-g', '--glob', action='store', \
                            help='File selection glob in directory path')
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

        for c in ['user_filter_file', 'client_filter_file']:
            if not self.config.get(c, None):
                self.logger.error('Missing config "{}"'.format(c))
                sys.exit(1)

        self.USER_FILTER_FILE = self.config['user_filter_file']
        try:
            with open(self.USER_FILTER_FILE) as fh:
               self.USER_MAP = json.load(fh)
            self.logger.info('Loaded {}/USER_MAP entries'.format(len(self.USER_MAP)))
        except Exception as e:
            self.logger.error('ERROR loading map={}, initializing'.format(self.USER_FILTER_FILE))
            self.USER_MAP = {}

        self.CLIENT_FILTER_FILE = self.config['client_filter_file']
        try:
            with open(self.CLIENT_FILTER_FILE) as fh:
               self.CLIENT_MAP = json.load(fh)
            self.logger.info('Loaded {}/CLIENT_MAP entries'.format(len(self.CLIENT_MAP)))
        except Exception as e:
            self.logger.warning('ERROR loading map={}, initializing'.format(self.CLIENT_FILTER_FILE))
            self.CLIENT_MAP = {}

        self.IPRE = re.compile('^\d+.\d+.\d+.\d+$')
        self.PATH = self.args.path
        self.GLOB = self.args.glob
        self.logger.info('Starting {}: path={} glob={}'.format(sys.argv[0], self.PATH, self.GLOB))

        self.FILES = [f for f in fnmatch.filter(os.listdir(self.PATH), self.GLOB) if os.path.isfile(os.path.join(self.PATH, f))]

        self.USE_USER = {}
        self.USE_CLIENT = {}

    def load_files(self):
        for f in self.FILES:
            if f[-3:] == '.gz':
                fd = gzip.open(os.path.join(self.PATH, f), 'r')
            else:
                fd = open(os.path.join(self.PATH, f), 'r')

            csv_reader =  csv.DictReader(fd, delimiter=',', quotechar='|')
            for row in csv_reader:
                user = row.get('USE_USER', None)
                if user:
                    self.USE_USER[user] = self.USE_USER.get(user, 0) + 1
                client = row.get('USE_CLIENT', None)
                if client:
                    self.USE_CLIENT[client] = self.USE_CLIENT.get(client, 0) + 1
            fd.close()

    def ip_reverse(self, ip):
        if self.IPRE.match(ip):
            try:
                return(socket.gethostbyaddr(ip)[0])
            except:
                pass
        return('')

    def dump_summary(self):
        for i in sorted(self.USE_USER):
            print('USE_USER   {:7d} {}'.format(self.USE_USER[i], i))
        for i in sorted(self.USE_CLIENT):
            ip_revname = self.ip_reverse(i)
            print('USE_CLIENT {:7d} {} ({})'.format(self.USE_CLIENT[i], i, ip_revname))

    def prompt(self, prompt_text, response_chars):
        rc_list = list(response_chars)
        rc_list.append('')
        done = False
        sys.stdout.write(prompt_text)
        while not done:
            input = sys.stdin.readline().lstrip().rstrip()
            cmd = input[:1].lower()
            if cmd in rc_list:
                done = True
            else:
                sys.stdout.write(prompt_text)
            
        arg = input[2:].lstrip()
        return(cmd, arg)

    def interactive_review(self):
        for USER in sorted(self.USE_USER):
            MY_UM = self.USER_MAP.get(USER, None)
            if MY_UM:
                continue
            print('USE_USER   {:7d} {}'.format(self.USE_USER[USER], USER))
            (cmd, arg) =  self.prompt('Enter D[elete], M[ap] <new_value>, Q(uit), <return> (ignore): ', 'dmq')
            if cmd == 'q':
                return(False)
            if cmd == 'd':
                self.USER_MAP[USER] = 'DELETE'
            elif cmd == 'm':
                self.USER_MAP[USER] = 'MAP:' + arg

        for CLIENT in sorted(self.USE_CLIENT):
            MY_CM = self.CLIENT_MAP.get(CLIENT, None)
            if MY_CM:
                continue
            ip_revname = self.ip_reverse(CLIENT)
            print('USE_CLIENT {:7d} {} ({})'.format(self.USE_CLIENT[CLIENT], CLIENT, ip_revname))
            (cmd, arg) =  self.prompt('Enter D[elete], H[ost(map)], M[ap] <new_value>, Q(uit), <return> (ignore): ', 'dmqh')
            if cmd == 'q':
                return(False)
            if cmd == 'd':
                self.CLIENT_MAP[CLIENT] = 'DELETE'
            elif cmd == 'h':
                self.CLIENT_MAP[CLIENT] = 'MAP:' + ip_revname
            elif cmd == 'm':
                self.CLIENT_MAP[CLIENT] = 'MAP:' + arg

        return(True)

    def finish(self):
        rc = 0
        self.logger.info('Writing {}/USER_MAP {}/CLIENT_MAP entries'.format(len(self.USER_MAP), len(self.CLIENT_MAP)))
        try:
            with open(self.USER_FILTER_FILE, 'w+') as file:
                json.dump(self.USER_MAP, file, indent=4, sort_keys=True)
        except IOError:
            self.logger.error('Failed to write config=' + self.USER_FILTER_FILE)
            rc = 1

        try:
            with open(self.CLIENT_FILTER_FILE, 'w+') as file:
                json.dump(self.CLIENT_MAP, file, indent=4, sort_keys=True)
        except IOError:
            self.logger.error('Failed to write config=' + self.CLIENT_FILTER_FILE)
            rc = 1
        return(rc)

if __name__ == '__main__':
    me = Analyze()
    me.load_files()
    rc = me.interactive_review()
#   me.dump_summary()
    exit(me.finish())
