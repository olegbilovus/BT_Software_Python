import os
import sys

_path_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(_path_parent)

import argparse
import sqlite3
from datetime import datetime

import scapy.all as scapy
from tqdm import tqdm

import utils
from Utility import sharedUtils

# Parse config file
file_end, _, table_name, _ = sharedUtils.get_config_from_file(os.path.join(_path_parent, 'config.ini'),
                                                              'NETWORK')

# Parse command line arguments
parser = argparse.ArgumentParser(
    description='Convert pcap file to SQL stats, it considers only IP packets. ARP and some other packets are ignored.')
sharedUtils.parser_add_db_args(parser)
parser.add_argument('--pcap', help='pcap file')
print_args = parser.add_mutually_exclusive_group()
print_args.add_argument('--n_packets', help='number of packets to process, used for the progress bar', type=int)
print_args.add_argument('-v', '--verbose', action='store_true', help='verbose output')
args = parser.parse_args()

# Connect to the database
db_name = args.db + file_end
conn = sqlite3.connect(db_name)
c = conn.cursor()

# Reset the database if requested
if args.db_reset:
    c.execute('DROP TABLE IF EXISTS ' + table_name)
    conn.commit()

# Create the table if it doesn't exist
try:
    c.execute(
        'CREATE TABLE ' + table_name + ' (No INT PRIMARY KEY, timestamp TIMESTAMP, src TEXT, sport INT, dst TEXT, dport INT, transport TEXT, length INT)')
except sqlite3.OperationalError:
    pass

# Open the pcap file
pcap = scapy.PcapReader(args.pcap)

# Print the headers if verbose
VERBOSE_HEADERS = '[No] [Timestamp] Src[SrcPort] -> Dst[DstPort] [Protocol] [Length]'
if args.verbose:
    print(VERBOSE_HEADERS)

# Choose the type of iterator
iterator = enumerate(pcap, 1)
if not args.verbose:
    iterator = tqdm(iterator, total=args.n_packets, unit='packets', desc='Processing packets')

# Process the packets
skipped = 0
for i, pkt in iterator:
    ip_type = utils.get_ip_layer(pkt)
    if ip_type:
        ip = pkt[ip_type]
        transport = ip.payload
        protocol, sport, dport = utils.get_protocol_and_ports(transport)
        ts = datetime.utcfromtimestamp(float(pkt.time)).isoformat().replace('T', ' ')
        src = ip.src
        dst = ip.dst
        length = len(pkt)

        c.execute('INSERT INTO pcap_stats VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                  (i, ts, src, sport, dst, dport, protocol, length))

        if args.verbose:
            print(f'[#{i}] [{ts}] {src}[{sport}] -> {dst}[{dport}] {protocol} {length}')
    else:
        skipped += 1

# Commit the changes and close the connection
conn.commit()
conn.close()

if args.verbose:
    print(VERBOSE_HEADERS)

print(f'Skipped {skipped} no IP packets')
print(f'Saved packets to {db_name}')
