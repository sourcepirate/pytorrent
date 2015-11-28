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

