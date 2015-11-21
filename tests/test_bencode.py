# A test file for bencode.py in pytorrent package.

import unittest, json

#including the target source file.
from pytorrent.bencode import Bencoder

class BecodeTester(unittest.TestCase):

    def test_string_encoding(self):
        """tests string encoding"""
        strs = Bencoder.encode("announce")
        self.assertEqual(strs, "8:announce")

    def test_integer_encoding(self):
        """tests integer encoding"""
        strs = Bencoder.encode(1)
        self.assertEqual(strs, "i1e")

    def test_list_encoding(self):
        """tests list encoding"""
        strs = Bencoder.encode([1,2])
        self.assertEqual(strs, "li1ei2ee")

    def test_dict_encoding(self):
        """tests dictionary encoding"""
        strs = Bencoder.encode(dict(a="1"))
        self.assertEqual(strs, "d1:a1:1e")

