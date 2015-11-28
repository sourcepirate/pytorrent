
from random import choice


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