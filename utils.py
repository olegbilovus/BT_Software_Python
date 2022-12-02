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
