import unittest

from pytorrent.bencode import Bencoder
from pytorrent.tracker import TrackerRequest, TrackerResponse
import os, logging

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class TestTracker(unittest.TestCase):

    def setUp(self):
        self.torrent_content = open(os.getcwd()+'/tests/an-introduction-to-neural-networks.torrent', 'rb').read()
        self.torrent_content = Bencoder.decode(self.torrent_content)
        self.sample_content = open(os.getcwd()+'/tests/sample.torrent').read()
        self.sample_content = Bencoder.decode(self.sample_content)
        log.info(self.sample_content)

    def test_tracker_decode(self):
        request = TrackerRequest(**self.torrent_content)
        self.assertEqual(request.url, 'http://tracker.openbittorrent.com:80/announce')

    def test_tracker_request(self):
        log.info(self.sample_content)
        request = TrackerRequest(**self.sample_content)
        # request.url = request.url.replace("udp://", "http://")
        log.info(request)
        request.hit()
        self.assertIsNotNone(request)
