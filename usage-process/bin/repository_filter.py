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

        USER_FILTER_FILE = self.config.get('user_filter_file')
        self.USER_FILTER = None
        if USER_FILTER_FILE:
            try:
                with open(USER_FILTER_FILE) as fh:
                   self.USER_FILTER = json.load(fh)
            except Exception as e:
                eprint('ERROR loading user map={}'.format(USER_FILTER_FILE))
                sys.exit(1)

        CLIENT_FILTER_FILE = self.config.get('client_filter_file')
        self.CLIENT_FILTER = None
        if CLIENT_FILTER_FILE:
            try:
                with open(CLIENT_FILTER_FILE) as fh:
                   self.CLIENT_FILTER = json.load(fh)
            except Exception as e:
                eprint('ERROR loading client map={}'.format(CLIENT_FILTER_FILE))
                sys.exit(1)

        # Convert client filters into networks
        self.CLIENT_NETS = {}
        for cidr in self.CLIENT_FILTER:
            if '/' in cidr:
                netstr, bits = cidr.split('/')
                mask = (0xffffffff << (32 - int(bits))) & 0xffffffff
                net = ip_to_u32(netstr) & mask
                self.CLIENT_NETS[cidr] = (mask, net)

        self.CILOGON_USE_CLIENT = self.config.get('cilogon_use_client')
        
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
            if self.USER_FILTER:
                row = self.filter_action_simple(row, 'USE_USER', self.USER_FILTER)
                if not row: continue
            if self.CLIENT_FILTER:
                row = self.filter_action_subnet(row, 'USE_CLIENT', self.CLIENT_FILTER)
                if not row: continue
            if self.CILOGON_USE_CLIENT:
                row = self.filter_action_cilogon_use_client(row, 'USE_CLIENT')
                if not row: continue
            csv_writer.writerow(row)

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

    ##########################################################################
    # Custom filter for cilogon use_client
    ##########################################################################
    def filter_action_cilogon_use_client(self, row, field):
        client = row.get(field,'')
        if client.lower() not in ('ecp', 'pkcs12', ''):
            row[field] = 'OAUTH_client_name:{}'.format(client)
        return(row)

    def finish(self):
        return(0)

if __name__ == '__main__':
    me = Filter()
    me.filter_file(me.args.file)
    exit(me.finish())
