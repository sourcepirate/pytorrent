# author: plasmashadow

import hashlib
import json
import requests
import socket
import struct
import binascii
from six.moves.urllib.parse import urlparse

from utils import _generate_pear_id, generation_randomid
from .bencode import Bencoder


class TrackerException(Exception):
    """base class for all tracker exception"""

    def __init__(self, message, data):
        self.message = message
        self.data = data

    def __repr__(self):
        return "<TrackerException mode = %s>[%s]=>[%s]" % (self.mode, self.message, self.data)

    def __str__(self):
        return self.__repr__()


class TrackerRequestException(TrackerException):
    """exception on tracker request"""
    mode = "request"


class TrackerResponseException(TrackerException):
    """exception on tracker response"""
    mode = "response"


def _parse_udp_url(url):
    """parses the udp trackert url"""
    parsed = urlparse(url)
    return parsed.hostname, parsed.port


class TrackerRequest(dict, object):
    """request wrapper for tracker request

    'info_hash':
        In order to obtain this value the peer must calculate
        the SHA1 of the value of the "info" key in the metainfo file

    'peer_id':
        Must contain the 20-byte self-designated ID of the peer.

    'port':
        The port number that the peer is listening to
        for incoming connections from other peers.

    'uploaded':
        This is a base ten integer value.
        It denotes the total amount of bytes that the peer has
        uploaded in the swarm since it sent the "started" event to the tracker.

    'downloaded':
        This is a base ten integer value.
        It denotes the total amount of bytes that the peer has
        downloaded in the swarm since it sent the "started" event to the tracker.

    'left':
       This is a base ten integer value.
       It denotes the total amount of bytes that the
       peer needs in this torrent in order to complete its download.

    'ip':
       If present should indicate the true, Internet-wide address of the peer,
       either in dotted quad IPv4 format, hexadecimal IPv6 format, or a DNS name.

    'numwant':
       If present, it should indicate the number of peers
       that the local peer wants to receive from the tracker.
       If not present, the tracker uses an implementation defined value.

    'event':
       If not specified, the request is taken to be a regular periodic request.

    """

    __allowables = [

        ("info_hash", True),
        ("peer_id", True),
        ("port", True),
        ("uploaded", True),
        ("downloaded", True),
        ("left", True),
        ("ip", False),
        ("numwant", False),
        ("event", False),

    ]

    __events_allowed = [
        "started",
        "stopped",
        "completed"
    ]

    __connection_id = 0x41727101980
    __transaction_id = generation_randomid(5, integer=True)

    def __setattr__(self, key, value):
        """setting attribute to the dict instance"""
        self.__dict__.update([(key, value)])

    def __init__(self, **kwargs):

        data = self.__dict__
        event = (0, 'started')

        self.connected = False
        self.connection_id = self.__connection_id

        data["url"] = kwargs.pop('announce', None)

        if not data["url"]:
            raise TrackerRequestException("no url mentioned", kwargs)

        becoded_str = Bencoder.encode(kwargs.get("info"))

        self["length"] = self.length = kwargs.get("info")
        self["info_hash"] = self.info_hash = hashlib.sha1(becoded_str).digest()
        self["peer_id"] = self.peer_id = _generate_pear_id('KO', '0001')

        self["port"] = self.port = kwargs.get("port", int(6753))

        self["uploaded"] = self.uploaded = 0
        self["downloaded"] = self.downloaded = 0
        self["compact"] = 1

        if kwargs.get("info").get('files'):
            files = kwargs.get("info").get('files')
            self["length"] = self.length = sum([f["length"] for f in files])
        else:
            self["length"] = self.length = kwargs.get("info").get("length")

        self["left"] = self.left
        self["event"] = event[0]

        #optional values
        self["ip"] = 0
        self["key"] = 0
        self["numwant"] = -1
        self["action"] = 0

    def hit(self):
        """Hit the announce url and get the trackers response """
        if not "udp://" in self.url:
            response = requests.get(self.__dict__["url"], params=self)
            return TrackerResponse(response.content)
        else:
            self._handler_udp()




    @property
    def left(self):
        return self["length"] - self["downloaded"]


    def _announce(self, announce_state, event_state):
        announce_packet = struct.pack(">Qii20s20sQQQiiiii", self.connection_id,
                                long(announce_state),
                                self.__transaction_id, self.get("info_hash"),
                                self.get("peer_id"), long(self.get("downloaded")),
                                long(self.left), long(self.get("uploaded")),
                                event_state, self.get("ip"),
                                self.get('key'), self.get('numwant'),self.get("port"))
        return announce_packet

    def _handler_udp(self):
        self.socket = client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if not self.connected:
            announce_packet = self._announce(0, 0) # 0 for on connect NOTE: refere beps
            client_socket.sendto(announce_packet, _parse_udp_url(self.url))
            res = client_socket.recvfrom(1024)
            data, address = res
            unpack_struct = struct.Struct('>iiq')
            action, self.transaction_id, message = unpack_struct.unpack(data)
            if action == 3:
                raise TrackerRequestException(message, "")
            if message:
                self.connected = True
                self.connection_id = hex(message)
        else:
            announce_packet = self._announce(1, 1) # 0 for on connect NOTE: refere beps
            client_socket.sendto(announce_packet, _parse_udp_url(self.url))
            res = client_socket.recvfrom(1024)
            data, address = res
            unpack_struct = struct.Struct('>HLLLLQQQ20s20sLLQ')
            action, _, interval, leechers, seeders, ip_address, port = unpack_struct.unpack(data[:98])
#wip





class TrackerResponse(object):
    """

      Wrapper for Trackers response
      failure_reason: The peer should interpret this as if the attempt to join the torrent failed.
      interval      : The value of this key indicated the amount of time that a
                      peer should wait between to consecutive regular requests
      complete      : The Integer that indicates the number of seeders.
      incomplete    : The Integer that indicates the number of peers downloading
                      torrent.
      peers         : This is a bencoded list of dictionaries containing
                      a list of peers that must be contacted
                      in order to download a file

      Peers intern containse three assosiated properties.

      peer_id : self defined 20 bit id.

      ip      : string value indicating the ip
                address of the peer.

      port    : self designated port number of the peer.

    """

    def __init__(self, string_response):
        self._response = json.loads(string_response)

        if 'failure_reason' in self._response:
            raise TrackerResponseException('tracker request failed',
                                           self._response.get('failure_reason'))

        self.interval = self._response.get("interval", 10)
        self.seeds = self._response.get("complete")
        self.len_peers = self._response.get("incomplete")
        self.peers = Bencoder.decode(self._response.get("peers"))

    def to_dict(self):
        return self._response
