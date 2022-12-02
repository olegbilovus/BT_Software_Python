import dpkt


def get_protocol_and_ports(transport):
    if isinstance(transport, dpkt.tcp.TCP):
        protocol = 'TCP'
        sport = transport.sport
        dport = transport.dport
    elif isinstance(transport, dpkt.udp.UDP):
        protocol = 'UDP'
        sport = transport.sport
        dport = transport.dport
    elif isinstance(transport, dpkt.icmp.ICMP):
        protocol = 'ICMP'
        sport = None
        dport = None
    else:
        protocol = 'Unknown'
        sport = None
        dport = None

    return protocol, sport, dport
