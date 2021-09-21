#!/usr/bin/python

import sys
import os
import re
import time

ssh_config_file = "/etc/gsissh/ssh_config"
auditd_log_dir = "/var/log/audit/"

if len(sys.argv) < 3:
    print "ERROR: USAGE: ", sys.argv[0], " [-d <log-dir>] [-f <log-output-file>] from-mm-dd-yyyy to-mm-dd-yyyy"
    exit(1)

argcount = 1

if sys.argv[argcount] == "-d":
    auditd_log_dir = sys.argv[argcount+1]
    argcount = argcount + 2

if not os.access(auditd_log_dir, os.R_OK):
    print "ERROR: Unable to access the specified log directory: ", auditd_log_dir
    print "USAGE: ", sys.argv[0], " [-d <log-dir>] [-f <log-output-file>] from-mm-dd-yyyy to-mm-dd-yyyy"
    exit(2)

if sys.argv[argcount] == "-f":
    log_output_file = sys.argv[argcount+1]
    argcount = argcount + 2

    try:
        f = open(log_output_file, 'w')
        f.write("")
        log_output_fd = open(log_output_file, 'a')
    except IOError:
        print "ERROR: Could not open file for writing:", log_output_file
        print "USAGE: ", sys.argv[0], " [-d <log-dir>] [-f <log-output-file>] from-mm-dd-yyyy to-mm-dd-yyyy"
        exit(3)

#from_date = time.strptime(sys.argv[argcount], '%m-%d-%Y')
#to_date = time.strptime(sys.argv[argcount+1], '%m-%d-%Y')
from_date = time.strptime(sys.argv[argcount] + "-00:00:00", '%m-%d-%Y-%H:%M:%S')
to_date = time.strptime(sys.argv[argcount+1] + "-23:59:59", '%m-%d-%Y-%H:%M:%S')

hosts = {}
host_to_hostname = {}

#hosts['mason.iu.xsede.org'] = 0

# Get hosts from ssh_config
with open(ssh_config_file, "r") as in_file:
    host_regex = re.compile(r"^Host [^*]*$")
    hostname_regex = re.compile(r"^\s*Hostname\s.*$")
    # Loop over each log line

    host = ""
    for line in in_file:
        if (host_regex.search(line)):
            host_config = re.split(r'\s', line)
            hosts[host_config[1]] = 0
            host = host_config[1]
        if (hostname_regex.search(line)):
            host_config = re.split(r'\s*', line)
            host_to_hostname[host] = host_config[2]

print "HOSTS CONFIGURED IN", ssh_config_file, " ARE:"
print ""
for key, value in hosts.iteritems():
    print key, "(", host_to_hostname[key], ")"
print ""

# Regex used to match relevant audit log lines (in this case, EXECVE instances
# with one of the GSISSH service in the arguments)
#line_regex = re.compile(r"type=EXECVE msg=audit(.*).*a[\d+]=\"mason.iu.xsede.org\".*$")
line_regex = re.compile(r"type=EXECVE msg=audit(.*).*a0=\".*ssh\".*$")


print "PROCESSING AUDIT RECORDS IN ", auditd_log_dir

# These for Python 3.6
#directory = os.fsencode(auditd_log_dir)
#for file in os.listdir(directory):
#    logfile = os.fsdecode(file)

for filename in os.listdir(auditd_log_dir):
    # Open input file in 'read' mode
    with open(auditd_log_dir + "/" + filename, "r") as in_file:
        # Loop over each log line
        for line in in_file:
            # If log line matches our regex, print to console, and output file
            if (line_regex.search(line)):
                if 'log_output_fd' in locals():
                    log_output_fd.write(line)
                timestamp = re.split(r':', line)
                timestamp = re.split(r'\(', timestamp[0])
                # print "TIMESTAMP IS:", timestamp
                audit_time = time.localtime(float(timestamp[1]))
                if from_date <= audit_time and audit_time <= to_date:
                    args = re.split(r'"', line)
                    for arg in args:
                        # print "Looking for ", arg
                        if arg in hosts:
                            hosts[arg] = hosts[arg] + 1
                        if arg in host_to_hostname.values():
                            hosts[host_to_hostname.keys()[host_to_hostname.values().index(arg)]] = hosts[host_to_hostname.keys()[host_to_hostname.values().index(arg)]] + 1
                # print line

print "LOGINS TO HOSTS FROM", time.strftime('%m-%d-%Y', from_date), "TO", time.strftime('%m-%d-%Y', to_date), ":"
print ""
total_logins = 0
for key, value in hosts.iteritems():
    print key, "(", host_to_hostname[key], ")", value
    total_logins += value
print ""
print "TOTAL LOGINS: ", total_logins
