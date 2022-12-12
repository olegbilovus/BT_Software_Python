import scapy.all as scapy


def get_protocol_and_ports(transport):
    name = transport.name
    sport = transport.sport if hasattr(transport, 'sport') else None
    dport = transport.dport if hasattr(transport, 'dport') else None

    return name, sport, dport


def get_ip_layer(pkt):
    if pkt.haslayer(scapy.IP):
        return scapy.IP
    if pkt.haslayer(scapy.IPv6):
        return scapy.IPv6
    return None
