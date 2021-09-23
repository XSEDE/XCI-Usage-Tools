#!/soft/XCI-Usage-Tools/python/bin/python3

import argparse
import datetime
from datetime import datetime, tzinfo, timedelta
import fnmatch
import gzip
import json
import logging
import logging.handlers
import os
import paramiko
import socket
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

class HandleUpload():
    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-c', '--config', action='store', default='./upload_usage.conf', \
                            help='Configuration file default=./upload_usage.conf')
        parser.add_argument('-l', '--log', action='store', \
                            help='Logging level (default=warning)')
        parser.add_argument('--pdb', action='store_true', \
                            help='Run with Python debugger')
        self.args = parser.parse_args()

        if self.args.pdb:
            pdb.set_trace()

        # Load configuration
        config_path = os.path.abspath(self.args.config)
        try:
            with open(config_path, 'r') as cf:
                self.config = json.load(cf)
        except ValueError as e:
            eprint('Error "{}" parsing config={}'.format(e, config_path))
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

        for c in ['LOCAL_DIRECTORY', 'LOCAL_GLOB', 'UPLOAD_STATUS_FILE', 'RSA_KEY', 'REMOTE_HOSTNAME', 'REMOTE_USERNAME']:
            if not self.config.get(c, None):
                self.logger.error('Missing config "{}"'.format(c))
                sys.exit(1)

        # Upload history/state
        try:
            with open(self.config['UPLOAD_STATUS_FILE']) as hf:
                self.UPLOAD_STATUS = json.load(hf)
        except Exception as e:
            self.logger.warning('Upload status file not found or failed to parse, initializing "{}"'.format(self.config['UPLOAD_STATUS_FILE']))
            self.UPLOAD_STATUS = {}

        self.stats = {
            'skipped': 0,
            'errors': 0,
            'uploads': 0,
            'bytes': 0
        }

    def upload_directory(self, log_path, log_glob):
        start_utc = datetime.now(utc)
        self.logger.info('Processing {}/{}'.format(log_path, log_glob))

        matching_files = [f for f in fnmatch.filter(os.listdir(log_path), log_glob) if os.path.isfile(os.path.join(log_path, f))]
        if len(matching_files) == 0:
            return

        try:
            rsakey = paramiko.RSAKey.from_private_key_file(self.config.get('RSA_KEY'))
        except Exception as e:
            self.logger.error('Exception "{}" loading RSA private key {}'.format(e, self.config.get('RSA_KEY')))
            sys.exit(1)
        
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh_client.connect(hostname=self.config.get('REMOTE_HOSTNAME', 'xci-metrics.xsede.org'),
                port=self.config.get('REMOTE_PORT', '22'),
                username=self.config.get('REMOTE_USERNAME'),
                pkey=rsakey)
        except Exception as e:
            self.logger.error('ssh_client_connect error: {}'.format(e))
            sys.exit(1)

        try:
            self.scp_client = ssh_client.open_sftp()
        except Exception as e:
            self.logger.error('ssh_client.open_sftp() error: {}'.format(e))
            sys.exit(1)

        for f in matching_files:
            self.upload_file(f, os.path.join(log_path, f))

        try:
            self.scp_client.close()
        except Exception as e:
            self.logger.error('scp_client.close() error: {}'.format(e))
            sys.exit(1)

        end_utc = datetime.now(utc)
        self.logger.info('Uploaded files={}, bytes={}, seconds={}, skipped={}, errors={}'.format(
            self.stats['uploads'], self.stats['bytes'], (end_utc - start_utc).total_seconds(), 
            self.stats['skipped'], self.stats['errors']))

###############################################################################
# UPLOAD_STATUS fields and states
#   log_size     size of file to process and upload
#   log_mtime    modified time of file to process and upload
#   parser       parser used to process
#   upload_size  size of file uploaded
#   upload_rc    return code for upload
#   remote_size  size of remote uploaded file
#   remote_mtime modified time of remote uploaded file
#   
###############################################################################
    def upload_file(self, local_filename, local_fqn):
        my_status = self.UPLOAD_STATUS.get(local_fqn, {})
        local_filestat = os.stat(local_fqn)
        local_filemtime_str = str(datetime.fromtimestamp(local_filestat.st_mtime))
        # We don't need to process a file if:
        #   Previously uploaded without error
        #   local file size and mtime are the same as processed before
        #   NOTE: Log may be processed/parsed before upload
        if my_status.get('upload_rc', '') in ('0','') and \
                my_status.get('log_size', '') == local_filestat.st_size and \
                my_status.get('log_mtime', '') == local_filemtime_str:
            self.stats['skipped'] += 1
            return

        self.logger.info('Uploading file={}, size={}, mtime={}'.format(local_filename, local_filestat.st_size, local_filemtime_str))

        PARSER = self.config.get('LOG_PARSER', None)
        if PARSER:
            try:
                my_status['parser'] = PARSER
                parse_command = [PARSER, local_fqn] # Parser first argument is the input fully qualified filename
                subproc = subprocess.Popen(parse_command, bufsize=1, stdout=subprocess.PIPE)
                temp_fqn = '/tmp/usage_{}.usage.gz'.format(os.getpid())
                if os.path.isfile(temp_fqn):
                    os.remove(temp_fqn)
                with gzip.open(temp_fqn, 'w') as temp_f:
                    for line in iter(subproc.stdout):
                        temp_f.write(line)
                subproc.terminate()
                upload_fqn = temp_fqn
                upload_stat = os.stat(upload_fqn)
                my_status['upload_size'] = upload_stat.st_size
                if local_filename[-3:] == '.gz':
                    remote_filename = local_filename[:-3] + '.usage.csv.gz'
                else:
                    remote_filename = local_filename + '.usage.csv.gz'
#           except subprocess.CalledProcessError as e:
            except Exception as e:
                self.logger.error('Parsing step failed: {}'.format(e))
                self.stats['skipped'] += 1
                return
        else:
            upload_fqn = local_fqn
            my_status['upload_size'] = local_filestat.st_size
            remote_filename = local_filename

        my_status['log_size'] = local_filestat.st_size
        my_status['log_mtime'] = local_filemtime_str
        try:
            remote_fqn = os.path.join(self.config.get('REMOTE_PATH', ''), remote_filename)
            remote_stat = self.scp_client.put(upload_fqn, remote_fqn, confirm=True)
            if my_status['upload_size'] == remote_stat.st_size:
                my_status['upload_rc'] = ''
            else:
                my_status['upload_rc'] = 'local and remote byte counts do not match'
            my_status['remote_mtime'] = str(datetime.fromtimestamp(remote_stat.st_mtime))
            my_status['remote_size'] = remote_stat.st_size
            self.stats['bytes'] += remote_stat.st_size                  # Total bytes
            self.stats['uploads'] += 1
            self.logger.info('Uploaded  file={}, size={}'.format(remote_filename, remote_stat.st_size))
        except Exception as e:
            my_status['upload_rc'] = str(e)
            self.stats['errors'] += 1
            self.logger.error('scp_client.put "{}" failed: {}'.format(remote_filename, e))

        self.UPLOAD_STATUS[local_fqn] = my_status

    def finish(self):
        try:
            with open(self.config['UPLOAD_STATUS_FILE'], 'w+') as file:
                json.dump(self.UPLOAD_STATUS, file, indent=4, sort_keys=True)
                file.close()
        except IOError:
            self.logger.error('Failed to write config=' + self.config['UPLOAD_STATUS_FILE'])
            sys.exit(1)

if __name__ == '__main__':
    task = HandleUpload()
    rc = task.upload_directory(task.config.get('LOCAL_DIRECTORY'), task.config.get('LOCAL_GLOB'))
    rc = task.finish()
