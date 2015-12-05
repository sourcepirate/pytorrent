import select
import socket
from .tracker import HttpTracker as Torrent
from .tracker import MAX_CONNECTIONS

class PyTorrent(object):

    """
      Torrent Object acts as a torrent client.
    """

    def __init__(self, filename, host='localhost', port=6880):
        self.torrent = Torrent(filename)
        self.host = host
        self.port = port
        self.inputs = []
        self.outputs = []

    def create_listener(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self.host, self.port))
        listener.listen(5)
        return listener

    def add_peer(self):
        # TODO: accept connection
        # connect to a new peer
        peer = self.torrent.peers.pop()  # get a new peer
        peer.connect()
        self.inputs.append(peer)
        self.outputs.append(peer)

    def remove(self, peer):
        # remove peer from select's queue
        self.inputs.remove(peer)
        self.outputs.remove(peer)
        # put the peer in the back of the torrent's queue of peers
        self.torrent.peers.appendleft(peer)
        # reset peer's values and queues
        peer.teardown()

    def main_loop(self):
        while not self.torrent.is_complete():
            while len(self.inputs) < MAX_CONNECTIONS and self.torrent.peers:
                self.add_peer()

            # get what is ready
            to_read, to_write, errors = select.select(self.inputs, self.outputs, self.inputs)
            for peer in to_read:
                peer.read()
            for peer in to_write:
                peer.write()
            for peer in errors:
                self.remove(peer)