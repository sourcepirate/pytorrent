# author: plasmashadow

import hashlib
import json
import requests
import random
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

class Tracker(object):

    """
       Tracker is the announce server

       Base class for all Trackers.
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
        self.left = self.left
        self.ip = 0
        self.key = 0
        self.numwant = 0
        self.action = 0

    @property
    def left(self):
        return self["length"] - self["downloaded"]





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
