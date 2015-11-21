# A test file for bencode.py in pytorrent package.

import unittest, json

#including the target source file.
from pytorrent.bencode import BenCoder

class BecodeTester(unittest.TestCase):

    def test_list_string_encoding(self):
        strs = json.dumps(["announce"], cls=BenCoder)
        self.assertEqual(strs, "8:announce")
