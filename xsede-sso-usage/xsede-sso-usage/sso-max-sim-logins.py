#!/usr/bin/python

import sys
import os
import re
import time
import subprocess

from collections import defaultdict

input_file = ""

if len(sys.argv) < 3:
    print "ERROR: USAGE: ", sys.argv[0], " [-i <input_file>] [-f <log-output-file>] from-mm-dd-yyyy to-mm-dd-yyyy"
    exit(1)

argcount = 1

if sys.argv[argcount] == "-i":
    input_file = sys.argv[argcount+1]
    argcount = argcount + 2

    if not os.access(input_file, os.R_OK):
        print "ERROR: Unable to access the specified input file: ", input_file
        print "USAGE: ", sys.argv[0], " [-i <input_file>] [-f <log-output-file>] from-mm-dd-yyyy to-mm-dd-yyyy"
        exit(2)
    in_file = open(input_file, "r")
else:
    #in_file = sys.stdin
    p = subprocess.Popen(["/usr/bin/last", "-F"], stdout=subprocess.PIPE)
    in_file = p.stdout

if sys.argv[argcount] == "-f":
    log_output_file = sys.argv[argcount+1]
    argcount = argcount + 2

    try:
        log_output_fd = open(log_output_file, 'w')
        log_output_fd.write("")
    except IOError:
        print "ERROR: Could not open file for writing:", log_output_file
        print "USAGE: ", sys.argv[0], " [-i <input_file>] [-f <log-output-file>] from-mm-dd-yyyy to-mm-dd-yyyy"
        exit(3)

from_date = time.strptime(sys.argv[argcount] + "-00:00:00", '%m-%d-%Y-%H:%M:%S')
to_date = time.strptime(sys.argv[argcount+1] + "-23:59:59", '%m-%d-%Y-%H:%M:%S')

logins = defaultdict(list)

if input_file != "":
    print "PROCESSING \"last -F\" RECORDS IN ", input_file
else:
    print "PROCESSING \"last -F\" RECORDS", input_file
print ""

#with open(input_file, "r") as in_file:
#try:
#except IOError:
#    print "ERROR: Could not open file for reading:", input_file
#    print "USAGE: ", sys.argv[0], " [-i <input_file>] [-f <log-output-file>] from-mm-dd-yyyy to-mm-dd-yyyy"
#    exit(4)

reboot_regex = re.compile(r"^reboot.*$")
wtmp_regex = re.compile(r"^wtmp.*$")
# Loop over each log line

reboot_date = ""
for line in in_file:
    log = 1
    # record reboot date to assign it to logout date shown as "down" or "crash"
    if (reboot_regex.search(line)):
        fields = re.split(r'\s*', line)
        reboot_date = fields[5] + "-" + fields[6] + "-" + fields[8] + "-" + fields[7]
        #print reboot_date
    # ignore the wtmp line
    elif (wtmp_regex.search(line)):
        continue
    else:
        fields = re.split(r'\s*', line)
        # ignore empty lines
        if (len(fields) < 3):
            continue
        login_date_str = fields[4] + "-" + fields[5] + "-" + fields[7] + "-" + fields[6]
        if fields[9] == "down" or fields[9] == "crash":
            logout_date_str = reboot_date
        elif fields[8] == "still":
            logout_date_str = time.strftime('%b-%d-%Y-%H:%M:%S', time.localtime())
            log = 0
        else:
            logout_date_str = fields[10] + "-" + fields[11] + "-" + fields[13] + "-" + fields[12]
        # print login_date_str, logout_date_str
        login_date = time.strptime(login_date_str, '%b-%d-%Y-%H:%M:%S')
        logout_date = time.strptime(logout_date_str, '%b-%d-%Y-%H:%M:%S')
        if (from_date <= logout_date) and (to_date >= login_date):
            logins[login_date].append('0')
            logins[logout_date].append('1')
    # output all lines except the "still logged in" lines
    if log == 1 and 'log_output_fd' in vars():
        log_output_fd.write(line)

# print logins

current_logins = 0
max_simultaneous_logins = 0
for key in sorted(logins.iterkeys()):
    # print "PROCESSING ", logins[key], current_logins, max_simultaneous_logins
    for x in reversed(logins[key]):
        if x == '0':
            current_logins = current_logins + 1
            if current_logins > max_simultaneous_logins:
                max_simultaneous_logins = current_logins
        elif x == '1':
            current_logins = current_logins - 1

print "MAXIMUM NUMBER OF SIMULTANEOUS LOGINS: ", max_simultaneous_logins
