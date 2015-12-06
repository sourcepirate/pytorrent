
#author: plasmashadow

from six.moves.urllib.parse import urlparse
from collections import defaultdict, deque
import six, struct
import socket, random

def udp_connect_packet():
    """
      connect with udp tracker
    """
    connection_id = 0x41727101980
    action = 0
    five_digit = random.sample(range(10), 5)
    transaction_id = int(''.join(map(str, five_digit)))
    packet = struct.pack(">qii", connection_id, action, transaction_id)
    return packet

def udp_announce_packet(connection_id, action, transaction_id, info_hash, peer_id, downloaded, left , uploaded,
                          event, ip, key, numwant, port):

    """announce the tracker about the protocol"""

    packet = struct.Struct(">qii20s20sqqqiiiih")
    print connection_id, action, transaction_id, info_hash,\
                              peer_id, downloaded, left, uploaded,\
                              event, ip, key, numwant, port
    packet_data = packet.pack(connection_id, action, transaction_id, info_hash,
                              peer_id, downloaded, left, uploaded,
                              event, ip, key, numwant, port)
    return packet_data


def _parse_udp_url(url):

    """parses the udp trackert url"""

    parsed = urlparse(url)
    return parsed.hostname, parsed.port

def parse_udp_response(response):

    """parse the udp response"""

    data, address = response
    response = defaultdict(lambda x: None)

    if len(data) == 16:
        #then it is a connect response
        action, transaction_id, connection_id = struct.unpack(">iiq", data)
        response['connection_id'] = connection_id
        response['transaction_id'] = transaction_id
        response['action'] = action
        return response

    elif len(data) == 26:
        action, transaction_id, interval, leechers, seeders, ip_address, tcp_port =\
            struct.unpack(">iiiiiih", data)

        response['action'] = action
        response['transaction_id'] = transaction_id
        response['interval'] = interval
        response['leechers'] = leechers
        response['seeders'] = seeders
        response['ip_address'] = ip_address
        response['port'] = tcp_port
        return response
    else:
        pass