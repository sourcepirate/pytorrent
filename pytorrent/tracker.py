# author: plasmashadow

import requests, six
from six.moves.urllib.parse import urlencode



class TrackerException(Exception):
    """base class for all tracker exception"""

    def __init__(self, message, data):
        self.message = message
        self.data = data

    def __repr__(self):
        return "<TrackerException mode = %s>[%s]=>[%s]" % (self.mode, self.message, self.data)


class TrackerRequestException(TrackerException):
    """exception on tracker request"""
    mode = "request"


class TrackerResponseException(TrackerException):
    """exception on tracker response"""
    mode = "response"


class TrackerRequest(dict):
    """request wrapper for tracker request"""

    __allowables = [
        ("info_hash", True),
        ("peer_id", True),
        ("port", True),
        ("uploaded", True),
        ("downloaded", True),
        ("left", True),
        ("ip", False),
        ("numwant", False),
        ("event", False)
    ]

    __events_allowed = [
        "started",
        "stopped",
        "completed"
    ]

    def __init__(self, *args, **kwargs):

        self.url = kwargs.pop('announce', None)
        if not self.url:
            raise TrackerRequestException("no url mentioned", kwargs)

        allowed_values = filter(lambda x: x[1] == True, self.__allowables)
        allowed_values = set(allowed_values)
        given_values = set(six.iterkeys(kwargs))

        if not allowed_values.issubset(given_values):
            remaining = given_values - allowed_values
            raise TrackerRequest("[illegal request] expected %s not in request", str(remaining))

        if 'event' in kwargs and kwargs.get('event') not in self.__events_allowed:
            raise TrackerRequest("Illegal event value", kwargs['event'])

        self.update(*args, **kwargs)

    def get(self):
        response = requests.get(self.url, params=self)
        return TrackerResponse(response)

# work in progress
class TrackerResponse(object):
    pass
