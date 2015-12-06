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
