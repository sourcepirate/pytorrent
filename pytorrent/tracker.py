# author: plasmashadow

import requests, six, json
from six.moves.urllib.parse import urlencode
from .bencode import Bencoder



class TrackerException(Exception):
    """base class for all tracker exception"""

    def __init__(self, message, data):
        self.message = message
        self.data = data

    def __repr__(self):
        return "<TrackerException mode = %s>[%s]=>[%s]" % (self.mode, self.message, self.data)


class TrackerRequestException(TrackerException):
    """exception on tracker request"""
    mode = "request"


class TrackerResponseException(TrackerException):
    """exception on tracker response"""
    mode = "response"


class TrackerRequest(dict):
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
        ("event", False)
    ]

    __events_allowed = [
        "started",
        "stopped",
        "completed"
    ]

    def __init__(self, *args, **kwargs):

        self.url = kwargs.pop('announce', None)
        if not self.url:
            raise TrackerRequestException("no url mentioned", kwargs)

        allowed_values = filter(lambda x: x[1] == True, self.__allowables)
        allowed_values = set(allowed_values)
        given_values = set(six.iterkeys(kwargs))

        if not allowed_values.issubset(given_values):
            remaining = given_values - allowed_values
            raise TrackerRequest("[illegal request] expected %s not in request", str(remaining))

        if 'event' in kwargs and kwargs.get('event') not in self.__events_allowed:
            raise TrackerRequest("Illegal event value", kwargs['event'])

        self.update(*args, **kwargs)

    def hit(self):
        """Hit the announce url and get the trackers response """
        response = requests.get(self.url, params=self)
        return TrackerResponse(response.content)

# work in progress
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