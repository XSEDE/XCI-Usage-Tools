#!/soft/XCI-Usage-Tools/python/bin/python3

import argparse
import csv
import fnmatch
import gzip
import json
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
        parser = argparse.ArgumentParser()
        parser.add_argument('file', nargs='?')
        parser.add_argument('-c', '--config', action='store', default='./repository_process.conf', \
                            help='Configuration file default=./repository_process.conf')
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

        for c in ['user_filter_file', 'client_filter_file']:
            if not self.config.get(c, None):
                eprint('Missing config "{}"'.format(c))
                sys.exit(1)

        self.USER_FILTER_FILE = self.config['user_filter_file']
        try:
            with open(self.USER_FILTER_FILE) as fh:
               self.USER_FILTER = json.load(fh)
        except Exception as e:
            eprint('ERROR loading map={}, initializing'.format(self.USER_FILTER_FILE))
            self.USER_FILTER = {}

        self.CLIENT_FILTER_FILE = self.config['client_filter_file']
        try:
            with open(self.CLIENT_FILTER_FILE) as fh:
               self.CLIENT_FILTER = json.load(fh)
        except Exception as e:
            eprint('ERROR loading map={}, initializing'.format(self.CLIENT_FILTER_FILE))
            self.CLIENT_FILTER = {}

        # Convert client filters into networks
        self.CLIENT_NETS = {}
        for cidr in self.CLIENT_FILTER:
            if '/' in cidr:
                netstr, bits = cidr.split('/')
                mask = (0xffffffff << (32 - int(bits))) & 0xffffffff
                net = ip_to_u32(netstr) & mask
                self.CLIENT_NETS[cidr] = (mask, net)
#           else:
#               mask = 0xffffffff
#               net = ip_to_u32(cidr)
#           self.CLIENT_NETS[cidr] = (mask, net)

#       eprint('Loaded {}/USER_FILTER {}/CLIENT_FILTER entries'.format(len(self.USER_FILTER), len(self.CLIENT_FILTER)))

    def filter_file(self, file_name):
        if file_name:
            if file_name[-3:] == '.gz':
                fd = gzip.open(file_name, mode='rt')
            else:
                fd = open(file_name, mode='r')
        else:
            fd = sys.stdin
        
        csv_reader = csv.DictReader(fd, delimiter=',', quotechar='|')
        if not csv_reader.fieldnames or 'USED_COMPONENT' not in csv_reader.fieldnames:
            eprint('ERROR file is missing CSV fields: {}'.format(file_name))
            fd.close()
            return
        csv_writer = csv.DictWriter(sys.stdout, fieldnames=csv_reader._fieldnames, delimiter=',', quotechar='|')
        csv_writer.writeheader()
        for row in csv_reader:
            row1 = self.filter_action_simple(row, 'USE_USER', self.USER_FILTER)
            if row1:
                row2 = self.filter_action_subnet(row1, 'USE_CLIENT', self.CLIENT_FILTER)
                if row2:
                    csv_writer.writerow(row2)

        fd.close()

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

    def finish(self):
        return(0)

if __name__ == '__main__':
    me = Filter()
    me.filter_file(me.args.file)
    exit(me.finish())
