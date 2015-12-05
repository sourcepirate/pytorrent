# author: plasmashadow

from collections import deque
import socket
import struct
from bitstring import BitArray

# peers represent individual elements connected
# with the data

REQUEST_MAX = 2

# PEER WIRE MESSAGES
#
#  All integer members in PWP messages are encoded as a 4-byte big-endian number.
#  Furthermore, all index and offset members in PWP messages are zero-based.
#
# A PWP message has the following structure:
#
# -----------------------------------------
# | Message Length | Message ID | Payload |
# -----------------------------------------

# NOTE: Coded on handshake method on tracker

# Message Length:
# This is an integer which denotes the length of the message,
# excluding the length part itself.
# If a message has no payload, its size is 1.
# Messages of size 0 MAY be sent periodically as keep-alive messages.
# Apart from the limit that the four bytes impose on the message length,
# BTP does not specify a maximum limit on this value.
# Thus an implementation MAY choose to specify a different limit,
# and for instance disconnect a remote peer that wishes to communicate using a
# message length that would put too much strain on the local peer's resources.

# Message ID:
# This is a one byte value, indicating the type of the message.
# BTP/1.0 specifies 9 different messages, as can be seen further below.
# Payload:
# The payload is a variable length stream of bytes.


MSG_TYPES = ['choke',
             'unchoke',
             'interested',
             'not_interested',
             'have',
             'bitfield',
             'request',
             'piece',
             'cancel',
             'port']

#Message Types
#
# CHOKE:
# This message has ID 0 and no payload.
# A peer sends this message to a remote peer to
# inform the remote peer that it is being choked.
#
# UNCHOKE:
# This message has ID 1 and no payload.
# A peer sends this message to a remote peer to
# inform the remote peer that it is no longer being choked.
#
# INTERESTED:
# This message has ID 2 and no payload.
# A peer sends this message to a remote peer to inform
# the remote peer of its desire to request data.
#
# UNINTERSTED:
# This message has ID 3 and no payload.
# A peer sends this message to a remote peer to inform
# it that it is not interested in any pieces from the remote peer.
#
# HAVE:
# This message has ID 4 and a payload of length 4.
# The payload is a number denoting the index of a piece that
# the peer has successfully downloaded and validated.
# A peer receiving this message must validate the index and drop the connection
# if this index is not within the expected bounds.
# Also, a peer receiving this message MUST send an interested message
# to the sender if indeed it lacks the piece announced. Further,
# it MAY also send a request for that piece.
#
# BITFIELD
# This message has ID 5 and a variable payload length.
# The payload is a bitfield representing the pieces that the sender
# has successfully downloaded, with the high bit in the first byte
# corresponding to piece index 0.
# If a bit is cleared it is to be interpreted as a missing piece.
# A peer MUST send this message immediately after the handshake operation,
# and MAY choose not to send it if it has no pieces at all
# This message MUST not be sent at any other time during the communication.
#
# REQUEST:
# This message has ID 6 and a payload of length 12.
# The payload is 3 integer values indicating a block within a piece
# that the sender is interested in downloading from the recipient.
# The recipient MUST only send piece messages to a sender that has already requested it,
# and only in accordance to the rules given above about the choke and interested states.
# The payload has the following structure:
#
# ---------------------------------------------
# | Piece Index | Block Offset | Block Length |
# ---------------------------------------------
#
# PIECE:
# This message has ID 7 and a variable length payload.
# The payload holds 2 integers indicating from which piece and with what
#  offset the block data in the 3rd member is derived.
#  Note: the data length is implicit and can be calculated by subtracting 9 from the total message length.
#        The payload has the following structure:
#
# -------------------------------------------
# | Piece Index | Block Offset | Block Data |
# -------------------------------------------
#
#  CANCEL:
# This message has ID 8 and a payload of length 12.
# The payload is 3 integer values indicating a block within
# a piece that the sender has requested for, but is no longer interested in.
# The recipient MUST erase the request information upon receiving this messages.
# The payload has the following structure:
#
# ---------------------------------------------
# | Piece Index | Block Offset | Block Length |
# ---------------------------------------------


def payload_encode(msg_type, payload=b''):   # A byte string
    """encodes the payload corresponding to the specified message type"""
    if msg_type == 'keep-alive':
        msg = ''
    else:
        pack = struct.Struct('B')
        msg = pack.pack(MSG_TYPES.index(msg_type)) + payload

    # pack to little endian while traveling in network
    return struct.pack('>I', len(msg))+msg

class Peer(object):

    """
      A peer represents the induvidual host connected with
      the data network on the torrent.

      The various types of peer states that are allowed with
      the torrent has been mentioned above.
    """

    def __init__(self, torrent, ip, port, peer_id=None):

        self.torrent = torrent
        self.ip = ip
        self.port = port
        self.peer_id = peer_id
        self.sock = None
        self.handshake = ''
        self.state = None
        self.is_choking = True
        self.am_interested = False
        self.am_choking = True
        self.is_interested = False
        self.msg_queue = deque()
        self.pieces = BitArray(bin='0' * self.torrent.num_pieces)
        self.reply = ''

        self.requests = []  # array of tuples: piece, offset
        self.MAX_REQUESTS = REQUEST_MAX
        self.MAX_MSG_LEN = 2 ** 15


    @property
    def fileno(self):
        """returns the unix socket filenumber"""
        return self.sock.fileno()

    def connect(self):
        """
          Since peer wire protocol is completly async we need
          to have an nonblocking message passing been
          torrent peers.
        """

        if not self.sock:
            self.sock = socket.socket()

        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setblocking(False) #changing to non blocking mode

        try:
            self.sock.connect((self.ip, self.port))
        except socket.error:
            pass
        finally:
            self.state = 'sending_to_wait'

    def read(self):
        """recive a incoming message from peer connected to the socket"""
        try:
            self.reply += self.sock.recv(self.MAX_MSG_LEN)
        except socket.error:
            pass
        finally:
            self.doreply()

    def write(self):
        """send a message to other peer"""
        self.enqueue_msg()
        self.send_msg()

    def doreply(self):
        """reply to the adjecent peer on getting a message"""

        while self.reply != '':

            if ord(self.reply[0]) == 19 and self.reply[1:20] == 'BitTorrent protocol':
                self.process_handshake(self.reply[:68])
                self.reply = self.reply[68:]

            else:
                msg_len = struct.unpack('>I', self.reply[:4])[0]
                if msg_len == 0:
                    # checking keep alive connection
                    self.reply = self.reply[:4]
                elif len(self.reply) >= (msg_len + 4):
                    self.process_msg(self.reply[4:4 + msg_len])
                    self.reply = self.reply[4 + msg_len:]
                else:
                    break

    def enqueue_msg(self):
        """enqueuing messageing tasks"""
        if self.state == 'sending_to_wait':
            self.msg_queue.append(self.torrent.handshake)
            self.state = 'waiting'
        elif self.state == 'connected':
            if not self.am_interested:
                if self.pieces & self.torrent.need_pieces:
                    self.am_interested = True
                    self.msg_queue.append(payload_encode('interested'))
            elif not self.is_choking and len(self.requests) < self.MAX_REQUESTS:
                new_request = self.torrent.get_next_request(self)
                if new_request:
                    index, begin, length = new_request
                    self.msg_queue.append(payload_encode('request',
                                                         struct.pack('>III', index, begin, length)))
                    self.requests.append((index, begin))

    def send_msg(self):
        """send message from queue"""
        while self.msg_queue:
            try:
                self.sock.sendall(self.msg_queue[0])
            except socket.error:
                break
            self.msg_queue.popleft()

    def process_handshake(self):
        """handling handshake signal from other peer"""
        if self.state == "waiting_to_send":
            self.msg_queue.append(self.torrent.handshake)
        self.msg_queue.append(payload_encode('bitfield', self.torrent.have_pieces.tobytes()))
        self.state = 'connected'

    def process_msg(self, msg_str):
        """processing message string"""
        msg = struct.unpack('B', msg_str[0])[0]

        if msg == 0:
            #choking
            self.is_choking = True

        elif msg == 1:
            #unchoking
            self.is_choking = False

        elif msg == 2:
            #unchoking peer
            self.sock.sendall(payload_encode('unchoke'))

        elif msg == 3:
            self.is_interested = False

        elif msg == 4:
            #update info about peer's need_pieces
            piece_idx = struct.unpack('>I', msg_str[1:])[0]
            self.pieces[piece_idx] = True

        #bitfield msg
        elif msg == 5:
            self.pieces = BitArray(bytes=msg_str[1:])
            del self.pieces[self.torrent.num_pieces:]  #cut out unnecessary bits

        #request for a piece
        elif msg == 6:
            #check that not choking
            if not self.am_choking:
                #locate requested piece, send it
                index, begin, length = struct.unpack('>I I I', msg_str[1:])
                #read the data
                data = self.torrent.read(index, begin, length)
                if data:  # if read is successful
                    self.msg_queue.append(payload_encode('piece', struct.pack('>I I', index, begin) + data))
                #update uploaded
                self.torrent.uploaded += length

        #piece
        elif msg == 7:
            index, begin = struct.unpack('>I I', msg_str[1:9])
            # store the file
            self.torrent.store(index, begin, msg_str[9:])
            #update the peer's queue
            self.requests.remove((index, begin))

        #cancel piece
        elif msg == 8:
            pass

        #port msg
        elif msg == 9:
            pass

        else:
            raise Exception("unknown message")

    def teardown(self):
        """reseting all values"""
        for index, offset in self.requests:
            if self.torrent.need_blocks[index].count(1) == 0:
                self.torrent.need_pieces[index] = True
            self.torrent.need_blocks[index][offset / self.torrent.block_len] = True
        # reset values
        self.state = None
        self.am_interested = False
        self.is_chocking = True
        self.is_interested = False
        self.am_choking = True










