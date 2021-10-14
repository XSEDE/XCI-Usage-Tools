#!/soft/XCI-Usage-Tools/python/bin/python3
import argparse
import csv
import gzip
import sys
import pdb

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class Filter():
    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('file', nargs='?')
        parser.add_argument('--pdb', action='store_true', \
                            help='Run with Python debugger')
        self.args = parser.parse_args()

        if self.args.pdb:
            pdb.set_trace()

    def Setup(self):
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
                eprint('INFO: Input file empty')
                sys.exit(0)
            else:
                eprint('Input file is missing CSV fields in first row')
                sys.exit(1)

        if 'USED_COMPONENT' not in self.IN_READER.fieldnames:
            eprint('ERROR: Input file is missing field=USED_COMPONENT')
            sys.exit(1)

        OUT_FIELDS = self.IN_READER._fieldnames + ['USED_RESOURCE']
        self.OUT_FD = sys.stdout
        self.OUT_WRITER = csv.DictWriter(self.OUT_FD, fieldnames=OUT_FIELDS, delimiter=',', quotechar='|')
        self.OUT_WRITER.writeheader()

    def Process(self):
        for row in self.IN_READER:
            RESOURCE, INFOROUTER = row.get('USED_COMPONENT', '').split('@')
            if INFOROUTER == 'inforouter':
                row['USED_RESOURCE'] = RESOURCE
                row['USED_COMPONENT'] = 'org.xsede.info.router'
            self.OUT_WRITER.writerow(row)

if __name__ == '__main__':
    me = Filter()
    me.Setup()
    me.Process()
    sys.exit(0)
