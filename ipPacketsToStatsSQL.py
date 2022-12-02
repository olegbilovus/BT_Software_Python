import argparse
import sqlite3
from datetime import datetime

import scapy.all as scapy
from tqdm import tqdm

import utils

# Parse command line arguments
parser = argparse.ArgumentParser(
    description='Convert pcap file to SQL stats, it considers only IP packets. ARP and some other packets are ignored.')
parser.add_argument('--pcap', help='pcap file')
parser.add_argument('--db', help='sqlite3 database to write to', required=True)
parser.add_argument('--db_reset', help='reset the database', action='store_true')
print_args = parser.add_mutually_exclusive_group()
print_args.add_argument('--n_packets', help='number of packets to process, used for the progress bar', type=int)
print_args.add_argument('-v', '--verbose', action='store_true', help='verbose output')
args = parser.parse_args()

# Connect to the database
conn = sqlite3.connect(args.db)
c = conn.cursor()

# Reset the database if requested
if args.db_reset:
    c.execute('DROP TABLE IF EXISTS pcap_stats')
    conn.commit()

# Create the table if it doesn't exist
try:
    c.execute(
        'CREATE TABLE pcap_stats (No INT PRIMARY KEY, timestamp TIMESTAMP, src TEXT, sport INT, dst TEXT, dport INT, transport TEXT, length INT)')
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
    if pkt.haslayer(scapy.IP):
        ip = pkt[scapy.IP]
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

# Print the skipped packets
print(f'Skipped {skipped} no IP packets')
