#author: plasmashadow

import six, json
import re

# http://www.bittorrent.org/beps/bep_0003.html
# given specification

if six.PY3:
    basestring = str

class BencodeException(Exception):
    """Base class for all bencode Exceptions"""

    def __init__(self, message, data):
        self.message = message
        self.data = data

    def __repr__(self):
        return "<BencodeException mode = %s>[%s]=>[%s]"%(self.mode, self.message, self.data)

class BencodeEncodeError(BencodeException):
    """
    Bencode Encoding Error while converting
    standard objects to bencoded Strings

    """
    mode = "Encode"

class BencodeDecodeError(BencodeException):
    """
    Bencode Decoding Error while converting
    Bencoded Strings to python Objects.
    """

    mode = "Decode"

def _encode_int(data):
    """
       Encodes the int, long in to bencoded strs
    :param data:
    :return String: becoded string
    """
    if isinstance(data, (int, long)):
        return "%s%s%s"%("i", str(data), "e")
    else:
        raise BencodeEncodeError("Invalid Integer", data)

def _encode_string(data):
    """
      Encodes the str, basestring into becoded strs
    :param data:
    :return: String: bencoded Strings
    """
    if isinstance(data, (str, basestring, unicode, )):
        return "%s:%s"%(str(len(data)), data)
    else:
        raise BencodeEncodeError("Invalid String", data)

def _recursive_baselist_encode(data):
    """
      Encodes the sequence of str, int bencoded strs
    :param data:
    :return:
    """
    strs = ""
    for element in data:
        if isinstance(element, (str, basestring, unicode)):
            strs += _encode_string(element)
        elif isinstance(element, (int, long, )):
            strs += _encode_int(element)
    return strs


def _encode_list(lst):
    """
     Encodes the list, set, tuple into bencoded strs
    :param list:
    :return: String: bencoded Strings
    """
    if isinstance(lst, (list, set, tuple,)):
        lst = list(lst)
        return "%s%s%s"%("l", _recursive_baselist_encode(lst), "e")
    else:
        raise BencodeEncodeError("Invalid Collection ", lst)

def _encode_dict(dct):

    """
     Encodes the key, value pair to becoded strs
    :param dct:
    :return: String: bencoded strings
    """
    strs = ""
    if isinstance(dct, (dict,)):
        for key, value in six.iteritems(dct):
            if isinstance(value, (list, set, tuple)):
                value = _encode_list(value)
            elif isinstance(value, (str, )):
                value = _encode_string(value)
            elif isinstance(value, (int, )):
                value = _encode_int(value)
            key = _encode_string(key)
            strs += "%s%s%s%s"%("d", key, value, "e")
    else:
        raise BencodeEncodeError("Invalid Dictionary", dct)
    return strs

#decoding part



class Bencoder(object):

    """
      A class wrapper around bencode encoding.
    """

    @classmethod
    def encode(cls, obj):
        """encodes each python std object to bencoded strs"""

        if isinstance(obj, (str, basestring, unicode)):
            return _encode_string(obj)
        elif isinstance(obj, (int, long, )):
            return _encode_int(obj)
        elif isinstance(obj, (list, tuple, set)):
            return _encode_list(obj)
        elif isinstance(obj, (dict,)):
            return _encode_dict(obj)

        else:
            raise BencodeEncodeError("Object Doesn't match any base types", obj)

    @classmethod
    def decode(cls, becode_string):
        pass
