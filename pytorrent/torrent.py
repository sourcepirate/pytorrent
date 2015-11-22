# author: plasmashadow

import six
from datetime import datetime
from .bencode import Bencoder
import time, hashlib
from random import choice


__client_name = 'bittorent'
__client_version = '0001'
__client_id = 'KO'

MAX_CONNECTIONS = 4 #maximum parllel connections
BLOCK_LEN = 2 ** 14 #maximum block size

class TorrentExcepiton(Exception):
    message = None
    data = None

    def __init__(self, message, data):
        self.message = message
        self.data = data

    def __repr__(self):
        return "%s:<%s>==>%s" % (self.__class__.__name__, self.message, self.data)


def _split_pieces(string, n):
    """
      Used to split pieces with n as interval

      NOTE: the first 20 bytes of the string represent
      the SHA1 value used to verify piece index 0.
    """

    temp = []
    i = n
    while i <= len(string):
        temp.append(string[(i - n):i])
        i += n
    try:
        if string[(i - n)] != "":
            temp.append(string[(i - n):])
    except IndexError:
        pass

    return temp


def _generate_pear_id():
    """generate a 20 char peer id"""
    random_string = ""
    while len(random_string) != 12:
        random_string = random_string + choice("1234567890")
    return '-'+__client_id+__client_version+'-'+random_string


# work in progress

class TorrentFile(object):
    """
       Represents a torrent file
      The torrent file contains.

      {announce: "",
       announce-list: "",
       comment: "",
       created_by: "",
       creation_date: "",
       info:  {
           length: "",
           md5sum: "",
           name: "",
           piece_length: "",
           pieces: []
          }
       }
    """


    __block_len = BLOCK_LEN
    __max_connection = MAX_CONNECTIONS

    def __raise(self, message):
        raise TorrentExcepiton(message, self.data)

    def __init__(self, name):
        self.name = name
        self.data = data = open(self.name, 'rb').read()
        decoded_data = Bencoder.decode(data)
        self.announce = decoded_data.get("announce", self.__raise("No Announce"))
        self.created_date = datetime.fromtimestamp(decoded_data.get("creation date", time.time()))
        info = decoded_data.get("info")
        self.info_hash = hashlib.sha1(Bencoder.encode(info)).digest()
        self.multi = 'files' in info  # check whether it is single torrent or multitorrent file
        self.files = []
        if self.multi:
            raise NotImplementedError

        self.length = info.get("length")
        self.piece_length = info.get("piece_length")
        self.torrent_name = info.get("name")

        self.md5 = info.get("md5sum")
        pieces = info.get("pieces")

        self.pieces = map(lambda x: hashlib.sha1(x).digest(), _split_pieces(pieces, self.piece_length))


class Torrent(object):
    def __init__(self, filename):
        pass
