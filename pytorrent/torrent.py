# author: plasmashadow

import six, struct
import socket, random
from .bencode import Bencoder
from hashlib import sha1
from threading import Thread
from time import sleep
from .utils import _generate_pear_id, _split_pieces
from six.moves.urllib.parse import urlparse
from collections import defaultdict, deque
import requests

from .connections import *

CLIENTNAME = 'bittorent'
VERSION = '0001'
CID = 'DE'

MAX_CONNECTIONS = 4  # maximum parllel connections
BLOCK_LEN = 2 ** 14  # maximum block size


class TorrentExcepiton(Exception):
    message = None
    data = None

    def __init__(self, message, data):
        self.message = message
        self.data = data

    def __repr__(self):
        return "%s:<%s>==>%s" % (self.__class__.__name__, self.message, self.data)


def get_file_info(torrent_file):
    """
       Get the metainfo dict from file

       Args:
           torrent_file : Filename with .torrent extension

       Returns:
           dict: dictionary of bencode decoded metainfo
    """
    metainfo = None
    with open(torrent_file, 'rb') as tf:
        strs = tf.read()
        metainfo = Bencoder.decode(strs)

    return metainfo


def handshake(info_hash, peer_id):
    """Generates a 20 byte handshake with info_hash and peer_id"""

    protocol_id = "BitTorrent protocol"
    len_id = str(len(protocol_id))
    reserved = "00000000"
    return len_id + protocol_id + reserved + info_hash + peer_id


def _parse_udp_url(url):
    """parses the udp trackert url"""
    parsed = urlparse(url)
    return parsed.hostname, parsed.port


def peers(prs):
    """decodes the bencoded peer response to get peers"""

    if isinstance(prs, str):
        # single set of peers
        prs = _split_pieces(prs, 6)
        anon = lambda p: socket.inet_aton(p[:4]), struct.unpack(">H", prs[4:])
        return map(anon, prs)

    elif isinstance(prs, list):
        return map(lambda p: (p["ip"], p["port"]), prs)


class Torrent(object):
    """Torrent class used to download torrent data"""

    def __init__(self, torrent_file):

        self.running = False
        self._data = get_file_info(torrent_file)

        info = self._data.get('info')

        self.info_hash = sha1(Bencoder.encode(info)).digest()
        self.peer_id = _generate_pear_id(CID, VERSION)
        self.handshake = handshake(self.info_hash, self.peer_id)
        self.tracker_response = None
        self.peers = []
        self.tracker_loop = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.downloaded = self.uploaded = 0
        self.port = random.choice(range(20000,30000))

        files = self._data.get('info').get('files')

        if files:
            self.length = sum([f['length'] for f in files])
        else:
            self.length = self._data.get("info").get("length")

        self.left = lambda : self.length - self.downloaded


    def request(self, url, info_hash, peer_id):

        """
           Requests url for more peers
        """

        while self.running:
            self.tracker_response = request_tracker(info_hash, peer_id, url)
            if "failure reason" not in self.tracker_response:
                self.peers = peers(self.tracker_response['peers'])
            sleep(self.tracker_response["interval"])

    def connect(self):

        """sending connect signal to udp tracker"""

        connect_packet = udp_connect_packet()
        host_detail = _parse_udp_url(self._data.get('announce'))
        self.sock.sendto(connect_packet, host_detail)
        response = self.sock.recvfrom(1024)
        parsed_response = parse_udp_response(response)
        self.tid = parsed_response['transaction_id']
        self.cid = parsed_response['connection_id']
        return parsed_response

    def announce(self):

        """make an announce request to the trackers"""

        param_list = [
            self.cid,
            1,
            self.tid,
            self.info_hash,
            self.peer_id,
            self.downloaded,
            self.left(),
            self.uploaded,
            0,
            0,
            0,
            -1,
            self.port
        ]

        packet = udp_announce_packet(*param_list)
        host_detail = _parse_udp_url(self._data.get('announce'))
        self.sock.sendto(packet, host_detail)
        response = self.sock.recvfrom(1024)
        parsed_response = parse_udp_response(response)


    def run(self):
        """start running torrent"""

        if not self.running:
            self.running = True
            self.tracker_loop = Thread(target=self.request,
                                       args=(self._data["announce"], self.info_hash, self.peer_id))
            self.tracker_loop.start()

    def stop(self):
        """ Stop the torrent from running. """
        if self.running:
            self.running = False
            self.tracker_loop.join()


