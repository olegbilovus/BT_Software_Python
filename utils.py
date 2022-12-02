import ntpath

import scapy.all as scapy


def get_protocol_and_ports(transport):
    if transport.haslayer(scapy.TCP):
        return 'TCP', transport.sport, transport.dport
    elif transport.haslayer(scapy.UDP):
        return 'UDP', transport.sport, transport.dport
    elif transport.haslayer(scapy.ICMP):
        return 'ICMP', None, None
    else:
        return 'Other', None, None


def get_ip_layer(pkt):
    if pkt.haslayer(scapy.IP):
        return scapy.IP
    elif pkt.haslayer(scapy.IPv6):
        return scapy.IPv6
    else:
        return None


def file_name(file_path):
    head, tail = ntpath.split(file_path)
    return tail or ntpath.basename(head)
