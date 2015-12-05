
from random import choice
import threading


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


def _generate_pear_id(client_id, client_version):
    """generate a 20 char peer id"""
    random_string = ""
    while len(random_string) != 12:
        random_string = random_string + choice("1234567890")
    return '-'+client_id+client_version+'-'+random_string


def generation_randomid(size, integer=False):
    """generates random id for a given size"""
    digits = range(10)
    id = []
    for i in range(size):
        id.append(choice(digits))
    res = ''.join(map(str, id))
    if not integer:
        return res
    else:
        return int(res)


class Timeout(object):

    """
      A very small timer which triggers an event
      after particular time.
    """

    def __init__(self, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message
        self.timer = None

    def handle_timeout(self, *args, **kwargs):
        raise Exception("timeout beep beep")

    def __enter__(self):
        self.timer = threading.Timer(self.seconds, self.handle_timeout)

    def __exit__(self, type, value, traceback):

        if self.timer:
          self.timer.cancel()