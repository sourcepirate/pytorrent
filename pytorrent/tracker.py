# author: plasmashadow

import hashlib
import json
import requests
import random
import socket
import struct
import binascii
from six.moves.urllib.parse import urlparse

from .utils import _generate_pear_id, generation_randomid
from .utils import Timeout
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

class Tracker(object):

    """
       Tracker is the announce server
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

    def __init__(self, torrent_file):

        torrent_data = open(torrent_file, 'rb').read()
        #gives in a torrent metainfo dict
        torrent_data = Bencoder.decode(torrent_data)
        self._data = torrent_data
        self._announce = self._data.get("url")
        info_hash_data = Bencoder.encode(self._data.get("info"))
        self._info_hash = hashlib.sha1(info_hash_data).digest()
        self._peer_id = _generate_pear_id('KO', '0001')
        self._port = random.choice(range(70000, 80000))
        self._uploaded = self._downloaded = 0
        self._compact = 1

        if self._data.get("info").get('files'):
            files = self._data.get('info').get('files')
            self._length = sum([f["length"] for f in files])
        else:
            self._length = self._data.get("info").get("length")

        self.event = 0
        self.ip = 0
        self.key = 0
        self.numwant = 0
        self.action = 0

    @property
    def left(self):
        return self["length"] - self["downloaded"]



class HttpTracker(Tracker):
    """
      Http Tracker has announce url under
      http.
    """
    def __init__(self, torrent_file):
        super(HttpTracker, self).__init__(torrent_file)
        self.connected = False

    def hit(self, event):
        """
          Hits the http tracker request
          and gets the response.
        """

        response = requests.get(self._announce, params={
            "info_hash": self._info_hash,
            "peer_id": self._peer_id,
            "port": self._port,
            "uploaded": self._uploaded,
            "downloaded": self._downloaded,
            "left": self.left,
            "ip": self.ip,
            "numwant": self.numwant,
            "event": event
        })
        return TrackerResponse(response)

    def start(self):
        response = self.hit('started')
        self.connected = True
        return response

    def stop(self):
        response = self.hit('stopped')
        return response

    def complete(self):
        response = self.hit('completed')
        return response


class UDPTracker(Tracker):
    """
      UDPTracker is one which has the udp
      protocol.
    """

    __events = {
        'none': 0
        'completed': 1,
        'started': 2,
        'stopped': 3
    }

    __actions = {
        'connect': 0,
        'announce': 1
    }

    _transaction_id = generation_randomid(5, integer=True)
    _connection_id = 0x41727101980

    def __init__(self, torrent_file):
        super(UDPTracker, self).__init__(torrent_file)
        self.connected = False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.transaction_id = self._transaction_id
        self.connection_id = self._connection_id

    def hit(self, event_state, action):

        event_state = self.__events[event_state]
        action = self.__actions[action]

        announce_packet = struct.pack(">Qii20s20sQQQiiiii",
                                      self.connection_id,
                                      long(action),
                                      self.transaction_id,
                                      self._info_hash,
                                      self._peer_id,
                                      long(self._downloaded),
                                      long(self.left),
                                      long(self._uploaded),
                                      event_state,
                                      self.ip,
                                      self.key,
                                      self.numwant,
                                      self._port)
        self.socket.sendto(announce_packet, _parse_udp_url(self._announce))
        response = self.socket.recv()
        return response

    def start(self):
        data, address = self.hit('none', 'connect')
        #unpacking transaction_ids
        unpack_struct = struct.Struct('>iiq')
        action, self.transaction_id, message = unpack_struct.unpack(data)
        if action == 3:
            raise TrackerRequestException(message, "")
        if message:
            self.connected = True
            self.connection_id = hex(message)

    def announce(self):
        """announces for trackers"""
        data, address = self.hit('started', 'announce')
        unpack_struct = struct.Struct('>HLLLLQQQ20s20sLLQ')
        action, transaction_id, \
              self.interval, self.leechers, self.seeders,\
                   self.ip_address, port = unpack_struct.unpack(data[:98])

        if transaction_id != self.transaction_id:
            raise TrackerRequestException("transaction id not matching", transaction_id)

        try:
            with Timeout(seconds=self.interval) as f:
                pass
        except Exception:
            self.announce()

























class TrackerRequest(dict, object):
    """
    request wrapper for tracker request

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
