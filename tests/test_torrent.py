import unittest
from pytorrent.torrent import Torrent
import os

class TestTorrent(unittest.TestCase):

    def setUp(self):
        self.torrent = Torrent(os.getcwd()+"/tests/sample.torrent")

    def test_request(self):
        self.torrent.connect()
        self.torrent.announce()