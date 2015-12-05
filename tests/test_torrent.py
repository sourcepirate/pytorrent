
# from pytorrent.torrent import PyTorrent
# t = PyTorrent('/home/plasmashadow/github/pytorrent/pytorrent/tests/an-introduction-to-neural-networks.torrent')


import unittest


class PyTorrentTest(unittest.TestCase):

    def setUp(self):
        from pytorrent.torrent import PyTorrent
        t = PyTorrent('/home/plasmashadow/github/pytorrent/pytorrent/tests/an-introduction-to-neural-networks.torrent')

    def test_me(self):
        pass