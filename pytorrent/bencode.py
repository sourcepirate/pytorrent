#author: plasmashadow

import six, json


class BenCoder(json.JSONEncoder):

    """
      The Bencoding is done like the one
      which is mentioned in bittorent rfc.

           dictionary = "d" 1*(string anytype) "e" ; non-empty dictionary
           list       = "l" 1*anytype "e"          ; non-empty list
           integer    = "i" signumber "e"
           string     = number ":" <number long sequence of any CHAR>
           anytype    = dictionary / list / integer / string
           signumber  = "-" number / number
           number     = 1*DIGIT
           CHAR       = %x00-FF                    ; any 8-bit character
           DIGIT      = "0" / "1" / "2" / "3" / "4" /
                        "5" / "6" / "7" / "8" / "9"
    """

    def encode(self, obj):
        print obj
        if isinstance(obj, int):
            return "%s%s%s"%("i", str(obj), "e")
        if isinstance(obj, str):
            length = len(obj)
            return "%s:%s"%(str(length), obj)
        if isinstance(obj, list):
            return "%s%s%s"%("l", self._parse_list(obj), "e")
        if isinstance(obj, dict):
            return "%s%s%s"%("d", self._parse_dict(obj), "e")


    def _parse_list(self, lst):
        """
         while parsing list we need to parse
         the contents of list in bencode as well
        :param lst:
        :return: string of parsed list
        """

        strs = ""
        for key in lst:
            strs += self.default(key)

        return strs

    def _parse_dict(self, dct):
        """
         Trying to parse the dictionary to bencoded
         elements.
        :param dct:
        :return:
        """

        strs = ""
        for key, value in six.iteritems(dct):
            strs += self.default(str(key))
            strs += self.default(value)
        return strs

    @classmethod
    def bencode(cls, value):
        return json.dumps(value, cls=cls)




