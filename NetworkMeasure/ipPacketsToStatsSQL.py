import os
import re
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
config_path = os.path.join(_path_parent, 'config.ini')
file_end = sharedUtils.get_file_end_from_config(config_path)
_, table_name, _ = sharedUtils.get_chart_config_from_file(config_path, 'NETWORK')

# Parse command line arguments
parser = argparse.ArgumentParser(
    description='Convert pcap file to SQL stats, it considers only IP packets. ARP and some other packets are ignored.')
sharedUtils.parser_add_db_args(parser, table_name)
parser.add_argument('--pcap', help='pcap file', required=True)
print_args = parser.add_mutually_exclusive_group()
print_args.add_argument('--n_packets', help='number of packets to process, used for the progress bar', type=int)
print_args.add_argument('-v', '--verbose', action='store_true', help='verbose output')
args = parser.parse_args()

# Connect to the database
db_name = args.db if sharedUtils.check_file_end(args.db, file_end) else args.db + file_end
conn = sqlite3.connect(db_name)
c = conn.cursor()

# Reset the database if requested
if args.db_reset:
    c.execute('DROP TABLE IF EXISTS ' + table_name)
    conn.commit()

# Create the table if it doesn't exist
try:
    c.execute(
        'CREATE TABLE ' + table_name + ' (No INT PRIMARY KEY, timestamp TIMESTAMP, src TEXT, sport INT, dst TEXT, dport INT, transport TEXT, length INT, flags TEXT, hostname TEXT)')
except sqlite3.OperationalError:
    pass

# Open the pcap file
pcap = scapy.PcapReader(args.pcap)

# Print the headers if verbose
VERBOSE_HEADERS = '[No] [Timestamp] Src[SrcPort] -> Dst[DstPort] [Protocol] [Length] [Flags]'
if args.verbose:
    print(VERBOSE_HEADERS)

# Choose the type of iterator
iterator = enumerate(pcap, 1)
if not args.verbose:
    iterator = tqdm(iterator, total=args.n_packets, unit='packets', desc='Processing packets')

# Process the packets
skipped = 0
dns_hostnames = {}
for i, pkt in iterator:
    ip_type = utils.get_ip_layer(pkt)
    if ip_type:
        if pkt.haslayer(scapy.DNS):
            dns = pkt[scapy.DNS]
            hostnames = set()
            if dns.ancount > 0:
                for an in range(dns.ancount):
                    dns_an = dns[scapy.DNSRR][an]
                    dns_an_rdata = dns_an.rdata.decode("utf-8") if type(
                        dns_an.rdata) is bytes else dns_an.rdata
                    if re.match('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',
                                dns_an_rdata) is not None:
                        dns_hostnames[dns_an_rdata] = dns_an.rrname.decode(
                            "utf-8")[:-1]

        ip = pkt[ip_type]
        transport = ip.payload
        protocol, sport, dport = utils.get_protocol_and_ports(transport)
        ts = datetime.utcfromtimestamp(float(pkt.time)).isoformat()

        src = ip.src
        dst = ip.dst
        length = len(pkt)
        flags = str(transport.flags) if protocol == 'TCP' else None

        c.execute(
            'INSERT INTO pcap_stats VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (i, ts, src, sport, dst, dport, protocol, length, flags,
             dns_hostnames.get(dst)))

        if args.verbose:
            print(f'[#{i}] [{ts}] {src}[{sport}] -> {dst}[{dport}] {protocol} {length} {flags}')
    else:
        skipped += 1

# Commit the changes and close the connection
conn.commit()
conn.close()

if args.verbose:
    print(VERBOSE_HEADERS)

print(f'Skipped {skipped} no IP packets')
print(f'Saved packets to {db_name}')
