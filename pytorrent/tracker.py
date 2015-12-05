# author: plasmashadow

import hashlib
import json
import requests
import random
import socket
import struct, os
import binascii
from six.moves.urllib.parse import urlparse
from collections import defaultdict, deque
from bitstring import BitArray
from .peer import Peer
from .utils import _generate_pear_id, generation_randomid
from .utils import Timeout
from .bencode import Bencoder

BLOCK_LEN = 2**14
MAX_CONNECTIONS = 4


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


def _get_hashes(hashes):
     """group into 20 block hashes"""
     return [hashes[i * 20:(i + 1) * 20] for i in range(len(hashes))]

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
        print self._data
        self.name = self._data.get('name')
        self._announce = self._data.get("announce")
        info_hash_data = Bencoder.encode(self._data.get("info"))
        self._info_hash = hashlib.sha1(info_hash_data).digest()
        self._peer_id = _generate_pear_id('KO', '0001')
        self._port = random.choice(range(10000,20000))
        self._uploaded = self._downloaded = 0
        self._compact = 1

        if self._data.get("info").get('files'):
            files = self._data.get('info').get('files')
            self._length = sum([f["length"] for f in files])
        else:
            self._length = self._data.get("info").get("length")

        self._piece_length = self._data.get("info").get("piece length")

        self.event = 0
        self.ip = 0
        self.key = 0
        self.numwant = -1
        self.action = 0

        #pieces
        self._last_piece_length = self._length % self._piece_length
        self.num_pieces = self._length / self._piece_length + 1 * (self._last_piece_length != 0)
        self._last_piece = self.num_pieces - 1
        self.last_block_length = self._piece_length % BLOCK_LEN
        self._blocks_per_piece = self._piece_length / BLOCK_LEN + 1* (self.last_block_length != 0)

        self.need_pieces = BitArray(bin='1' * self.num_pieces)
        self.need_blocks = [BitArray(bin='1' * self._blocks_per_piece) for i in range(self.num_pieces)]
        self.have_pieces = BitArray(bin='0' * self.num_pieces)
        self.have_blocks = [BitArray(bin='0' * self._blocks_per_piece) for i in range(self.num_pieces)]


        #info from tracker
        self.tracker_info = self.hit('started')

    @property
    def left(self):
        return self._length - self._downloaded

    @property
    def handshake(self):
        return ''.join([
            chr(19),
            'BitTorrent Protocol',
            chr(0)*8,
            self._info_hash,
            self._peer_id
        ])



class HttpTracker(Tracker):
    """
      Http Tracker has announce url under
      http.
    """
    def __init__(self, torrent_file):
        super(HttpTracker, self).__init__(torrent_file)
        self.connected = False
        self.pieces = defaultdict(lambda: [[] for i in range(self._blocks_per_piece)])
        self.piece_hashes = _get_hashes(self._data.get("info").get("pieces"))


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
            "event": event,
            "compact": 1
        })
        print dir(response)
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

    def initialize(self, filename):

        """creates a new file if already exists writes the
        data to that file"""

        if not os.path.exists(filename):
            with open(filename, 'wb') as f:
                pass
        else:
            with open(filename, 'rb') as f:
                # verifies there is no disuruption in chunck that
                # is been recived.
                content = f.read()
                for i in range(self.num_pieces):
                    block_hash = hashlib.sha1(content[i* self._piece_length: (i+1) * self._piece_length]).digest()
                    if block_hash == self.piece_hashes[i]:
                        self.need_pieces[i] = False
                        self.have_pieces[i] = True

    def is_complete(self):
        return not self.left > 0

    @property
    def peers(self):

        """Getting all peer list from the tracker info
           which we got from announce request.
        """

        peer_bytes = [ord(byte) for byte in self.tracker_info.peers]
        peers = deque()

        for i in range(len(peer_bytes)/6):
            ip = '.'.join([str(byte) for byte in peer_bytes[i * 6:i * 6 + 4]])
            port = peer_bytes[i * 6 + 4] * 256 + peer_bytes[i * 6 + 5]
            peers.append(Peer(self, ip, port))

        return peers

    def store(self, index, offset, data):
        """storing the downloaded data to the disk"""

        self.pieces[index][offset/BLOCK_LEN] = data
        self._downloaded += len(data)
        self.have_blocks[index][offset/BLOCK_LEN] = True

        if self.have_blocks[index].count(0) == 0:
            piece = ''.join(self.pieces[index])
            if self.piece_hashes[index] == hashlib.sha1(piece).digest():
                with open(self.name, 'r+b') as f:
                    f.seek(index * self._piece_length+offset)
                    f.write(data)
                self.have_pieces[index] = True
                del self.pieces[index]
        else:
            self.pieces[index] = self.blocklist()
            self.have_blocks[index] = BitArray(bin='0' * self._blocks_per_piece)
            self.need_pieces[index] = True
            self.need_blocks[index] = BitArray(bin='1' * self._blocks_per_piece)

    def read(self, index, begin, length):
        """reading a file on particular index"""
        # currently not handling length discrepancies
        with open(self.name, 'r+b') as f:
            f.seek(index * self._piece_length + begin)
            return f.read(length)

    def get_next_request(self, peer):
        """
        takes Torrent and Peer objects and finds the next block to download
        """

        def is_last_piece(index):
            return index == self.num_pieces - 1

        diff = peer.pieces & self.need_pieces
        # find next piece/block that the peer has and I don't have
        try:
            piece_idx = next(i for i in range(len(diff)) if diff[i] == True)
        except StopIteration:
            return None
        # find next block in that piece that I don't have
        block_idx = next(i for i in range(self._blocks_per_piece) if self.need_blocks[piece_idx][i] == True)
        offset = block_idx * BLOCK_LEN
        piece_len = self._last_piece_length if is_last_piece(piece_idx) else self.piece_len
        length = min(BLOCK_LEN, piece_len - offset)
        if length < 0:
            return None
        # update need_blocks and need_pieces
        self.need_blocks[piece_idx][block_idx] = False
        if self.need_blocks[piece_idx].count(1) == 0:
            self.need_pieces[piece_idx] = False
        return piece_idx, offset, length


class UDPTracker(Tracker):
    """
      UDPTracker is one which has the udp
      protocol.
    """

    __events = {
        'none': 0,
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
        print self.connection_id, action, self.transaction_id, len(self._info_hash), len(self._peer_id)
        announce_packet = struct.pack(">QLL20s20sQQQiiiiH",
                                      self.connection_id,
                                      action,
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
        data, address = self.socket.recvfrom(1024)
        return data, address

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

        pass


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
