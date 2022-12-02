import argparse
import sqlite3
from datetime import datetime

import dpkt
from dpkt.utils import inet_to_str
from tqdm import tqdm

import utils

# Parse command line arguments
parser = argparse.ArgumentParser(
    description='Convert pcap file to SQL stats, it considers only IP packets. ARP and some other packets are ignored.')
pcap_grp = parser.add_mutually_exclusive_group(required=True)
pcap_grp.add_argument('--pcap', help='pcap file to convert')
pcap_grp.add_argument('--pcapng', help='pcapng file to convert')
parser.add_argument('--db', help='sqlite3 database to write to', required=True)
parser.add_argument('--db_reset', help='reset the database', action='store_true')
print_grp = parser.add_mutually_exclusive_group()
print_grp.add_argument('--n_packets', help='number of packets to process, this will show a progress bar', type=int,
                       default=None)
print_grp.add_argument('-v', '--verbose', action='store_true', help='verbose output')
args = parser.parse_args()

# Connect to the database
conn = sqlite3.connect(args.db)
c = conn.cursor()

# Create the table if it doesn't exist
try:
    c.execute(
        'CREATE TABLE pcap_stats (No INT PRIMARY KEY, timestamp TIMESTAMP, src TEXT, dst TEXT, transport TEXT, length INT, sport INT, dport INT)')
except sqlite3.OperationalError:
    pass

# Reset the database if requested
if args.db_reset:
    c.execute('DELETE FROM pcap_stats')
    conn.commit()

# Open the pcap file
if args.pcap:
    pcap = dpkt.pcap.Reader(open(args.pcap, 'rb'))
else:
    pcap = dpkt.pcapng.Reader(open(args.pcapng, 'rb'))

# Print the headers if verbose
VERBOSE_HEADERS = '[No] [Timestamp] Src[SrcPort] -> Dst[DstPort] [Protocol] [Length]'
if args.verbose:
    print(VERBOSE_HEADERS)

# Process the packets
skipped = 0
for i, (ts, buf) in tqdm(enumerate(pcap, 1), total=args.n_packets, unit='packets', desc='Processing packets'):
    eth = dpkt.ethernet.Ethernet(buf)
    if isinstance(eth.data, dpkt.ip.IP):
        ip = eth.data
        transport = ip.data
        protocol, sport, dport = utils.get_protocol_and_ports(transport)
        ts = datetime.utcfromtimestamp(ts).isoformat().replace('T', ' ')
        src = inet_to_str(ip.src)
        dst = inet_to_str(ip.dst)
        length = len(buf)

        c.execute('INSERT INTO pcap_stats VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                  (i, ts, src, dst, protocol, length, sport, dport))

        if args.verbose:
            print(f'[#{i}] [{ts}] {src}[{sport}] -> {dst}[{dport}] {protocol} {length}')
    else:
        skipped += 1

# Commit the changes and close the connection
conn.commit()
conn.close()

if args.verbose:
    print(VERBOSE_HEADERS)

# Print the skipped packets
print(f'Skipped {skipped} no IP packets')
