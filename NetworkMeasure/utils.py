import scapy.all as scapy


def get_protocol_and_ports(transport):
    if transport.haslayer(scapy.TCP):
        return 'TCP', transport.sport, transport.dport
    if transport.haslayer(scapy.UDP):
        return 'UDP', transport.sport, transport.dport
    if transport.haslayer(scapy.ICMP):
        return 'ICMP', None, None
    return 'Other', None, None


def get_ip_layer(pkt):
    if pkt.haslayer(scapy.IP):
        return scapy.IP
    if pkt.haslayer(scapy.IPv6):
        return scapy.IPv6
    return None
