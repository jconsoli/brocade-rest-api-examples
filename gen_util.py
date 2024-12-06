"""
Copyright 2023, 2024 Consoli Solutions, LLC.  All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
the License. You may also obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
language governing permissions and limitations under the License.

The license is free for single customer use (internal applications). Use of this module in the production,
redistribution, or service delivery for commerce requires an additional license. Contact jack@consoli-solutions.com for
details.

:mod:`brcdapi.gen_util` - General purpose utility functions

**Description**

  Contains miscellaneous utility methods not specific to FOS

**Public Methods & Data**

+---------------------------+---------------------------------------------------------------------------------------|
| Method or Data            | Description                                                                           |
+===========================+=======================================================================================+
| add_to_obj                | Adds a key value pair to obj using '/' notation in the key. If the key already        |
|                           | exists, it is overwritten.                                                            |
+---------------------------+---------------------------------------------------------------------------------------|
| compare_lists             | Compare two lists. Returns True if they are equal, False otherwise.                   |
+---------------------------+---------------------------------------------------------------------------------------|
| convert_to_list           | Converts an object to a list. Typically used to convert objects that may be None,     |
|                           | str, int, float, dict, or list.                                                       |
+---------------------------+---------------------------------------------------------------------------------------|
| date_to_epoch             | Converts a date and time string to epoch time.                                        |
+---------------------------+---------------------------------------------------------------------------------------|
| dBm_to_absolute           | Converts a number in dBm to its value                                                 |
+---------------------------+---------------------------------------------------------------------------------------|
| get_input                 | Performs standard command line input parsing using argparse.                          |
+---------------------------+---------------------------------------------------------------------------------------|
| get_key_val               | Spins through a list of keys separated by a '/' and returns the value associated      |
|                           | with the last key.                                                                    |
+---------------------------+---------------------------------------------------------------------------------------|
| get_struct_from_obj       | Returns a Python data structure for a key using / notation in obj with everything     |
|                           | not in the key, k, filtered out                                                       |
+---------------------------+---------------------------------------------------------------------------------------|
| is_di                     | Determines if a str is a d,i pair (used in zoning)                                    |
+---------------------------+---------------------------------------------------------------------------------------|
| int_list_to_range         | Converts a list of integers to ranges as text.                                        |
+---------------------------+---------------------------------------------------------------------------------------|
| is_valid_zone_name        | Checks to ensure that a zone object meets the FOS zone object naming convention       |
|                           | rules                                                                                 |
+---------------------------+---------------------------------------------------------------------------------------|
| is_wwn                    | Validates that the wwn is a properly formed WWN                                       |
+---------------------------+---------------------------------------------------------------------------------------|
| match_str                 | Returns a list of strings using exact, wild card, ReGex match, or ReGex search.       |
+---------------------------+---------------------------------------------------------------------------------------|
| month_to_num              | Using datetime is clumsy. These are easier. Speed is seldom the issue, but it is      |
|                           | faster.                                                                               |
+---------------------------+---------------------------------------------------------------------------------------|
| multiplier                | Converts K, M, G, & T to an integer multiplier.                                       |
+---------------------------+---------------------------------------------------------------------------------------|
| num_to_month              | Converts an integer representing a month to text.                                     |
+---------------------------+---------------------------------------------------------------------------------------|
| pad_string                | Pads characters to a string to a fixed length. This is a cheesy way to support        |
|                           | report formatting without textable                                                    |
+---------------------------+---------------------------------------------------------------------------------------|
| paren_content             | Returns the contents of a string within matching parenthesis. First character         |
|                           | must be '('                                                                           |
+---------------------------+---------------------------------------------------------------------------------------|
| range_to_list             | Converts a CSV list of integer or hex numbers as ranges to a list                     |
+---------------------------+---------------------------------------------------------------------------------------|
| ReGex & miscellaneous     | Compiled ReGex for filtered or converting common. Common multipliers and date         |
|                           | conversion tables. Search for "ReGex matching" for details.                           |
+---------------------------+---------------------------------------------------------------------------------------|
| remove_duplicate_char     | Removes duplicate characters                                                          |
+---------------------------+---------------------------------------------------------------------------------------|
| remove_duplicate_space    | Deprecated. Use remove_duplicate_char                                                 |
+---------------------------+---------------------------------------------------------------------------------------|
| remove_duplicates         | Removes duplicate entries in a list                                                   |
+---------------------------+---------------------------------------------------------------------------------------|
| remove_leading_char       | Removes leading characters. Typically used to remove "0" from numbers as str.         |
+---------------------------+---------------------------------------------------------------------------------------|
| remove_none               | Removes list entries whose value is None                                              |
+---------------------------+---------------------------------------------------------------------------------------|
| resolve_multiplier        | Converts str representation of a number with a multiplier. Supported conversions      |
|                           | are K, k, M, m, G, g, T, and t.                                                       |
+---------------------------+---------------------------------------------------------------------------------------|
| slot_port                 | Separate the slot and port number from s/p port reference. Can also be used to        |
|                           | validate s/p notation.                                                                |
+---------------------------+---------------------------------------------------------------------------------------|
| sort_obj_num              | Sorts a list of dictionaries based on the value for a key. Value must be a number.    |
|                           | Key may be in '/' format.                                                             |
+---------------------------+---------------------------------------------------------------------------------------|
| sort_obj_str              | Sorts a list of dictionaries based on the value for a key or list of keys. Value      |
|                           | must be a string.                                                                     |
+---------------------------+---------------------------------------------------------------------------------------|
| sp_range_to_list          | Returns a list of ports based on a range of ports using s/p notation.                 |
+---------------------------+---------------------------------------------------------------------------------------|
| str_to_num                | Converts str to an int if it can be represented as an int, otherwise float.           |
|                           | 12.0 is returned as a float.                                                          |
+---------------------------+---------------------------------------------------------------------------------------|
| uwatts_to_dbm             | Converts a number in uWatts to dBm                                                    |
+---------------------------+---------------------------------------------------------------------------------------|
| wrap_text                 | Formats text into paragraphs.                                                         |
+---------------------------+---------------------------------------------------------------------------------------|

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Added sort to int_list_to_range(). Added wrap_text() and sp_range_to_list()           |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 03 Apr 2024   | Set default to None in parseargs_login_false_d. Added compare_lists()                 |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.3     | 15 May 2024   | Made parseargs_* an ordered dictionary. Only validate parameters if required or the   |
|           |               | value is not None in get_input(). Added match_str().                                  |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.4     | 16 Jun 2024   | Added parseargs_scan_d and parseargs_eh_d.                                            |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.5     | 20 Oct 2024   | Added error checking to slot_port(), removed unused variables in range_to_list() and  |
|           |               | date_to_epoch(),                                                                      |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.6     | 06 Dec 2024   | Added remove_leading_char()                                                           |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2023, 2024 Consoli Solutions, LLC'
__date__ = '06 Dec 2024'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack@consoli-solutions.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.6'

import re
import fnmatch
import datetime
import math
import argparse
import collections
import brcdapi.log as brcdapi_log

_MAX_ZONE_NAME_LEN = 64

# Common input parameters - For use with get_input()
_login_false_help = 'Required unless using -i, -scan, -cli, -t, or -eh options. This is a generic message. Only a  '\
                    'subset of these options are available with each module.'
_http_help = 'Optional. "none" for HTTP. The default is "self" for HTTPS mode.'
parseargs_login_d = collections.OrderedDict()
parseargs_login_d['ip'] = dict(h='Required. IP address.')
parseargs_login_d['id'] = dict(h='Required. User ID.')
parseargs_login_d['pw'] = dict(h='Required. Password.')
parseargs_login_d['s'] = dict(r=False, d='self', v=('self', 'none'), h=_http_help)

parseargs_login_false_d = collections.OrderedDict()
parseargs_login_false_d['ip'] = dict(r=False, d=None, h=_login_false_help + 'IP address.')
parseargs_login_false_d['id'] = dict(r=False, d=None, h=_login_false_help + 'User ID.')
parseargs_login_false_d['pw'] = dict(r=False, d=None, h=_login_false_help + 'Password.')
parseargs_login_false_d['s'] = dict(r=False, d='self', h=_http_help)
parseargs_log_d = dict(
    sup=dict(
        r=False, d=False, t='bool',
        h='Optional. No parameters. Suppress all output to STD_IO except the exit code and argument parsing errors. '
          'Useful with batch processing where only the exit status code is desired. Messages are still printed to the '
          'log file.'),
    log=dict(
        r=False, d=None,
        h='Optional. Directory where log file is to be created. Default is to use the current directory. The log file '
          'name will always be "Log_xxxx" where xxxx is a time and date stamp.'),
    nl=dict(
        r=False, d=False, t='bool',
        h='Optional. No parameters. When set, a log file is not created. The default is to create a log file.'),
)
parseargs_debug_d = dict(d=dict(
    r=False, d=False, t='bool',
    h='Optional. No parameters. When set, a pprint of all content sent and received to/from the API, except login '
      'information, is printed to the log.'))
parseargs_scan_d = dict(scan=dict(
    r=False, d=False, t='bool',
    h='Optional. No parameters. Scans for chassis and logical fabric information including the active zone '
      'configuration. No other actions are taken.'))
parseargs_eh_d = dict(eh=dict(
    r=False, d=False, t='bool',
    h='Optional. No parameters. Displays extended help text. No other actions are taken.'))

# ReGex matching
non_decimal = re.compile(r'[^\d.]+')
decimal = re.compile(r'[\d.]+')  # Use: decimal.sub('', '1.4G') returns 'G'
zone_notes = re.compile(r'[~*#+^]')
ishex = re.compile(r'^[A-Fa-f0-9]*$')  # use: if ishex.match(hex_str) returns True if hex_str represents a hex number
valid_file_name = re.compile(r'\w[ -]')  # use: good_file_name = valid_file_name.sub('_', bad_file_name)
date_to_space = re.compile(r'[-/,+]')  # Used to convert special characters in data formats to a space
valid_banner = re.compile(r'[^A-Za-z0-9 .,*\-\"\']')  # Use: good_banner = gen_util.valid_banner.sub('-', buf)

# Left these public for legacy support. Use is_valid_zone_name().
valid_zone_first_char = re.compile(r'[A-Za-z0-9]')  # use: if valid_zone_first_char.match(zone_str[0])
valid_zone_char = re.compile(r'[\w\-_$^]*$')  # use: if valid_zone_char.match(zone_str)

multiplier = dict(k=1000, K=1000, m=1000000, M=1000000, g=1000000000, G=1000000000, t=1000000000000, T=1000000000000)
# Using datetime is clumsy. These are easier. Speed is seldom the issue but it is faster
month_to_num = dict(
    jan=1, january=1,
    feb=2, february=2,
    mar=3, march=3,
    apr=4, april=4,
    may=5,
    jun=6, june=6,
    jul=7, july=7,
    aug=8, august=8,
    sep=9, september=9,
    oct=10, october=10,
    nov=11, november=11,
    dec=12, december=12,
)
num_to_month = ('Inv', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
_tz_utc_offset = dict(est=-4, edt=-5, cst=-5, cdt=-6, pst=-6, pdt=-7)


def remove_duplicate_char(buf, char):
    """Removes duplicate characters

    :param buf: Text to remove duplicate spaces from
    :type buf: str
    :param char: Character to check for duplicates in buf
    :type char: str
    :return: Input text with duplicate characters removed
    :rtype: str
    """
    buf = 'x' + buf
    temp_l = [buf[i] for i in range(1, len(buf)) if buf[i] != char or (buf[i] == char and buf[i-1] != char)]
    return ''.join(temp_l)


def remove_duplicate_space(buf):
    """Removes duplicate spaces - Deprecated

    :param buf: Text to remove duplicate spaces from
    :type buf: str
    :return: Input text with duplicate spaces removed
    :rtype: str
    """
    return remove_duplicate_char(buf, ' ')


def get_key_val(obj, keys):
    """Spins through a list of dict keys separated by a '/' and returns the value associated with the last key.

    :param obj: Starting point in the object
    :type obj: dict, ProjectObj, FabricObj, SwitchObj, PortObj, ZoneCfgObj, ZoneObj, PortObj, LoginObj
    :param keys: Sting of keys to look through
    :type keys: str, int, key
    :return: Value associated with last key. None if not found
    :rtype: int, float, str, list, tuple, dict
    """
    if obj is None:
        return None  # Saves the calling method of having to determine they are working on a valid object
    if hasattr(obj, 'r_get') and callable(obj.r_get):
        return obj.r_get(keys)
    if not isinstance(obj, dict):
        brcdapi_log.exception('Object type, ' + str(type(obj)) + ', not a dict or brcddb object,', echo=True)
        return None

    key_l = keys.split('/')
    if len(key_l) == 0:
        return None
    last_key = key_l[len(key_l)-1]
    v = obj
    for k in key_l:
        if isinstance(v, dict):
            v = v.get(k, None)
        elif v is None:
            return None
        elif k != last_key:
            brcdapi_log.exception('Object type, ' + str(type(v)) + ', for ' + k + ', in ' + keys +
                                  ' not a dict or brcddb object ', echo=True)
            return None
    return v


def sort_obj_num(obj_list, key, r=False, h=False):
    """Sorts a list of dictionaries based on the value for a key. Value must be a number. Key may be in '/' format

    :param obj_list: List of dict or brcddb class objects
    :type obj_list: list, tuple
    :param key: Key for the value to be compared. '/' is supported.
    :type key: str
    :param r: Reverse flag. If True, sort in reverse order (largest in [0])
    :type r: bool
    :param h: True indicates that the value referenced by the key is a hex number
    :type h: bool
    :return: Sorted list of objects.
    :rtype: list
    """
    # count_dict: key is the count (value of dict item whose key is the input counter). Value is a list of port objects
    # whose counter matches this count
    count_dict = dict()

    for obj in obj_list:
        # Get the object to test against
        v = get_key_val(obj, key)
        if v is not None and h:
            v = int(v, 16)
        if isinstance(v, (int, float)):
            try:
                count_dict[v].append(obj)
            except KeyError:
                count_dict.update({v: [obj]})

    # Sort the keys, which are the actual counter values and return the sorted list of objects
    return [v for k in sorted(list(count_dict.keys()), reverse=r) for v in count_dict[k]]


def sort_obj_str(obj_list, key_list, r=False):
    """Sorts a list of dictionaries based on the value for a key or list of keys. Value must be a string

    :param obj_list: List of dict or brcddb class objects
    :type obj_list: list, tuple
    :param key_list: Key or list of keys. Sort order is based key_list[0], then [1] ... Keys may be in '/' format
    :type key_list: str, list, tuple, None
    :param r: Reverse flag. If True, sort in reverse order ('z' first, 'a' last)
    :type r: bool
    :return: Sorted list of objects.
    :rtype: list
    """
    # count_dict: key is the count (value of dict item whose key is the input counter). Value is a list of port objects
    # whose counter matches this count
    key_l = convert_to_list(key_list)
    while len(key_l) > 0:
        key, sort_d = key_l.pop(), dict()
        for obj in obj_list:
            # Get the object to test against
            v = get_key_val(obj, key)
            if isinstance(v, str):
                try:
                    sort_d[v].append(obj)
                except KeyError:
                    sort_d.update({v: [obj]})
        obj_list = [v for k in sorted(list(sort_d.keys()), reverse=r) for v in sort_d[k]]

    return obj_list


def compare_lists(l1, l2):
    """Compare two lists. Returns True if they are equal, False otherwise

    :param l1: One of the lists to compare. The contents may be mixed types; however, embedded lists and dictionaries
        are pointers in Python. It's the pointer that is being compared, not the contents of the list or dictionary.
    :type l1: list,tuple
    :param l2: The other lists to compare. See description with l1.
    :type l2: list,tuple
    :return: True if they are equal, False otherwise. Returns False if either l1 or l2 are not a list or tuple
    :rtype: bool
    """
    if not isinstance(l1, (list, tuple)) or not isinstance(l2, (list, tuple)):
        brcdapi_log.exception(
            'l1 and l2 must be a list or tuple. l1: ' + str(type(l1)) + '. l2: ' + str(type(l2)),
            echo=True
        )
        return False
    s1, s2 = set(l1), set(l2)
    if len([x for x in s1 if x not in s2]):
        return False
    if len([x for x in s2 if x not in s1]):
        return False
    return True


def convert_to_list(obj):
    """Converts an object to a list. Typically used to convert objects that may be None or list.

    +-----------+-------------------------------------------------------+
    | obj       | Return                                                |
    +===========+=======================================================+
    | None      | Empty list                                            |
    +-----------+-------------------------------------------------------+
    | list      | The same passed object, obj, is returned - NOT A COPY |
    +-----------+-------------------------------------------------------+
    | tuple     | Converted, copied, to a list                          |
    +-----------+-------------------------------------------------------+
    | All else  | List with the passed obj as the only member           |
    +-----------+-------------------------------------------------------+

    :param obj: Object to be converted to a list
    :type obj: dict, str, float, int, list, tuple
    :return: Converted obj
    :rtype: list
    """
    if obj is None:
        return list()
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        return list() if len(obj.keys()) == 0 else [obj]
    if isinstance(obj, tuple):
        return [b for b in obj]
    else:
        return [obj]


def remove_duplicates(obj_list):
    """Removes duplicate entries in a list

    :param obj_list: List of class objects.
    :type obj_list: list, tuple
    :return return_list: Input list less duplicates
    :rtype: list
    """
    seen = set()
    seen_add = seen.add  # seen.add isn't changing so making it local makes the next line more efficient
    try:
        return [obj for obj in obj_list if not (obj in seen or seen_add(obj))]
    except TypeError:
        return obj_list


def remove_leading_char(obj, char):
    """Removes leading characters in a list or string

    :param obj: String or list of strings.
    :type obj: str, list, tuple, None
    :param char:
    :return: Same type as the input except for tuple which is returned as list
    :rtype: str, list, None
    """
    rl, ri = list(), 0
    for buf in convert_to_list(obj):
        if not isinstance(buf, str):
            e_buf = 'Object in obj was ' + str(type(buf)) + ' at index ' + str(ri) + '. Objects must be type str.'
            brcdapi_log.exception(e_buf, echo=True)
            raise TypeError
        i = 0  # If len(buf) == 0, i never gets initialized in the loop below
        for i in range(0, len(buf)):
            if buf[i] != char:
                break
        rl.append(buf[i:] if i < len(buf)-1 else '')
        ri += 1

    return None if obj is None else rl[0] if isinstance(obj, str) else rl


def remove_none(obj_list):
    """Removes list entries whose value is None

    :param obj_list: List of items.
    :type obj_list: list, tuple
    :return return_list: Input list less items that were None
    :rtype: list
    """
    return [obj for obj in obj_list if obj is not None]


def is_wwn(wwn, full_check=True):
    """Validates that the wwn is a properly formed WWN

    :param wwn: WWN
    :type wwn: str
    :param full_check: When True, the first byte cannot be 0
    :return: True - wwn is a valid WWN, False - wwn is not a valid WWN
    :rtype: bool
    """
    if not isinstance(wwn, str) or len(wwn) != 23 or (wwn[0] == '0' and full_check):
        return False
    clean_wwn = list()
    for i in range(0, len(wwn)):
        if i in (2, 5, 8, 11, 14, 17, 20):
            if wwn[i] != ':':
                return False
        else:
            clean_wwn.append(wwn[i])

    return True if ishex.match(''.join(clean_wwn)) else False


def is_valid_zone_name(zone_name):
    """Checks to ensure that a zone object meets the FOS zone object naming convention rules

    :param zone_name: Zone, zone configuration, or alias name
    :type zone_name: str
    :return: True if zone object name is a valid format, otherwise False
    :rtype: bool
    """
    global _MAX_ZONE_NAME_LEN, valid_zone_first_char, valid_zone_char

    if zone_name is None:
        return False
    if len(zone_name) < 2 or len(zone_name) > _MAX_ZONE_NAME_LEN:  # At least 2 characters and less than or = 64
        return False
    if not valid_zone_first_char.match(zone_name[0:1]):
        return False
    return valid_zone_char.match(zone_name[1:])


def slot_port(port):
    """Separate the slot and port number from s/p port reference. Can also be used to validate s/p notation.

    :param port: Port number in s/p notation
    :type port: str
    :return slot: Slot number. None if not in standard s/p notation
    :rtype slot: int, None
    :return port: Port number as an int if an integer. None if GigE port
    :rtype port: int, None
    :return ge_port: GigE port, including leading "ge" or "xge"
    :rtype ge_port: str, None
    """
    if isinstance(port, str):
        temp_l = port.split('/')
        if len(temp_l) == 1:
            temp_l.insert(0, '0')
        if len(temp_l) == 2:
            try:
                if temp_l[1].isnumeric():
                    return int(temp_l[0]), int(temp_l[1]), None
                else:
                    return int(temp_l[0]), None, temp_l[1]
            except (ValueError, IndexError):
                pass
    brcdapi_log.exception(
        'ERROR: Invalid port number. Type: ' + str(type(port)) + ', Value: ' + str(port),
        echo=True
    )
    return None, None, None


def is_di(di):
    """Determines if di is a d,i pair (used in zoning)

    :param di: Domain index pair as a "d,i"
    :type di: str
    :return: True - di looks like a d,i pair. Otherwise, False.
    :rtype: bool
    """
    try:
        temp = [int(x) for x in di.replace(' ', '').split(',')]
        return True if len(temp) == 2 else False
    except ValueError:
        return False


def str_to_num(buf):
    """Converts str to an int if it can be represented as an int, otherwise float. 12.0 is returned as a float.

    :param buf: Text to convert to float or int
    :type buf: str
    :return: buf converted to number. If the input cannot be converted to a number, it is returned as passed in.
    :rtype: str, float, int
    """
    if isinstance(buf, str):
        if '.' in buf:
            try:
                num = float(buf)
            except ValueError:
                return buf
            else:
                return num
        else:
            try:
                num = int(buf)
            except ValueError:
                return buf
            else:
                return num
    return buf


def paren_content(buf, p_remove=False):
    """Returns the contents of a string within matching parenthesis. First character must be '('

    :param buf: String to find text within matching parenthesis
    :type buf: str
    :param p_remove: If True, remove the leading and trailing parenthesis
    :return p_text: Text within matching parenthesis
    :rtype p_text: str
    :return x_buf: Remainder of buf after matching parenthesis have been found
    :rtype x_buf: str
    """
    p_count, r_buf = 0, list()
    if len(buf) > 1 and buf[0] == '(':
        p_count += 1  # The first character must be (
        r_buf.append('(')
        for c in buf[1:]:
            r_buf.append(c)
            if c == '(':
                p_count += 1
            elif c == ')':
                p_count -= 1
                if p_count == 0:
                    break

    if p_count != 0:
        brcdapi_log.exception('Input string does not have matching parenthesis:\n' + buf, echo=True)
        r_buf = list()
    remainder = '' if len(buf) - len(r_buf) < 1 else buf[len(r_buf):]
    if len(r_buf) > 2 and p_remove:
        r_buf.pop()
        r_buf.pop(0)

    return ''.join(r_buf), remainder


def add_to_obj(obj, k, v):
    """Adds a key value pair to obj using '/' notation in the key. If the key already exists, it is overwritten.

    :param obj: Dictionary the key value pair is to be added to
    :type obj: dict
    :param k: The key
    :type k: str
    :param v: Value associated with the key.
    :type v: int, str, list, dict
    """
    if not isinstance(k, str):
        brcdapi_log.exception('Invalid key. Expected type str, received type ' + str(type(k)), echo=True)
        return
    key_list = k.split('/')
    if isinstance(obj, dict):
        if len(key_list) == 1:
            obj.update({k: v})
            return
        key = key_list.pop(0)
        d = obj.get(key, None)
        if d is None:
            d = dict()
            obj.update({key: d})
        add_to_obj(d, '/'.join(key_list), v)
    else:
        brcdapi_log.exception('Invalid object type. Expected dict, received ' + str(type(obj)), echo=True)


def get_struct_from_obj(obj, k):
    """Returns a Python data structure for a key using / notation in obj with everything not in the key, k, filtered out

    :param obj: Dictionary the key is for
    :type obj: dict
    :param k: The key
    :type k: str
    :return: Filtered data structure. None is returned if the key was not found
    :rtype: int, str, list, dict, None
    """
    if not isinstance(k, str) or len(k) == 0:
        return None
    w_obj, kl = obj, k.split('/')
    while len(kl) > 0 and isinstance(w_obj, dict):
        w_obj = w_obj.get(kl.pop(0), None)

    return w_obj if len(kl) == 0 else None


def resolve_multiplier(val):
    """Converts str representation of a number with a multiplier. Supported conversions are K, k, M, m, G, g, T, and t.

    :param val: Dictionary the key is for
    :type val: str
    :return: val as a number. Returns None if val is not a number
    :rtype: float, None
    """
    if isinstance(val, str):
        try:
            mod_val = float(non_decimal.sub('', val))
            mult = decimal.sub('', val)
            if len(mult) > 0:
                return mod_val * multiplier[mult]
            return mod_val
        except ValueError:
            return None
    return val


def dBm_to_absolute(val, r=1):
    """Converts a number in dBm to it's value

    :param val: dBm value
    :type val: str, float, int
    :param r: Number of digits to the right of the decimal point to round off to
    :type r: int
    :return: val converted to its absolute value. None if val cannot be converted to a float.
    :rtype: float, None
    """
    try:
        return round((10 ** (float(val)/10)) * 1000, r)
    except ValueError:
        pass
    return None


def uwatts_to_dbm(val, r=1):
    """Converts a number in uWatts to dBm

    :param val: uWatt value
    :type val: str, float, int
    :param r: Number of digits to the right of the decimal point to round off to
    :type r: int
    :return: val converted to its absolute value. None if val cannot be converted to a float.
    :rtype: float, None
    """
    try:
        return round(10*math.log10(float(val)/1000), r)
    except ValueError:
        pass
    return None


def int_list_to_range(num_list, sort=False):
    """Converts a list of integers to ranges as text. For example, if sort == False: 0, 1, 5, 6, 2, 9 is returned as:

    0:  '0-1'
    1:  '5-6'
    2:  '2'
    3:  '9'

    Using the same example when sort==True:

    0:  '0-2'
    1:  '5-6'
    2:  '9'

    :param num_list: List of numeric values, int or float
    :type num_list: list
    :param sort: If True, num_list is sorted first. This makes for more efficient ranges.
    :type sort: bool
    :return: List of str as described above
    :rtype: list
    """
    rl, range_l, num_l = list(), list(), num_list.copy()
    if sort:
        num_l.sort()
    for i in num_l:
        ri = len(range_l)
        if ri > 0 and i != range_l[ri-1] + 1:
            rl.append(str(range_l[0]) if ri == 1 else str(range_l[0]) + '-' + str(range_l[ri-1]))
            range_l = list()
        range_l.append(i)
    ri = len(range_l)
    if ri > 0:
        rl.append(str(range_l[0]) if ri == 1 else str(range_l[0]) + '-' + str(range_l[ri-1]))

    return rl


def range_to_list(num_range, hex_num=False, upper=False, rsort=False, strip=False):
    """Converts a CSV list of integer or hex numbers as ranges to a list.

    For example: "0-2, 9, 6-5" is returned as [0, 1, 2, 9, 6, 5]. If hex is True, all values are assumed to be hex and
    the returned list is a list of str. For example: "0-2, 9-0xb" is returned as ["0x0", "0x1", "0x2", "0x9", "0xa",
    "0xb"]. Note that a reverse range is permitted.

    :param num_range: CSV of numeric values as described in the example above.
    :type num_range: str
    :param hex_num: If True, treat the input str num_range as hex
    :type hex_num: bool
    :param upper: Ony significant when hex_num==True. If True, output is upper case. Otherwise, lower case.
    :type upper: bool
    :param rsort: When True, the output is sorted from highest to lowest. Otherwise, output is sorted lowest to highest
    :type rsort: bool
    :param strip: Only significant when hex_num==True. If true, leading '0x' is removed
    :return: List of int or hex str as described above
    :rtype: list
    """
    rl = list()

    # Get all the values as integers
    for buf in num_range.replace(' ', '').split(','):
        temp_l = [int(v, 16) for v in buf.split('-')] if hex_num else [int(v) for v in buf.split('-')]
        if len(temp_l) > 0:
            max_i, min_i = max(temp_l), min(temp_l)
            if min_i == temp_l[0]:
                rl.extend([v for v in range(min_i, max_i+1)])
            else:
                rl.extend([v for v in reversed(range(min_i, max_i+1))])

    # Prepare the return data
    rl.sort(reverse=rsort)

    # Return
    if hex_num:
        if strip:
            return [hex(v).upper().replace('0X', '') for v in rl] if upper else [hex(v).replace('0x', '') for v in rl]
        else:
            return [hex(v).upper().replace('X', 'x') for v in rl] if upper else [hex(v) for v in rl]
    return rl


_fmt_map = {  # Used in date_to_epoch() to determine the indices for each date/time item. cm=True means month is text
    0: dict(y=2, m=0, d=1, t=3, z=4, cm=True),
    1: dict(y=2, m=1, d=0, t=3, z=4, cm=True),
    2: dict(y=2, m=0, d=1, t=3, z=4, cm=False),
    3: dict(y=2, m=1, d=0, t=3, z=4, cm=False),
    4: dict(y=5, m=1, d=2, t=3, z=4, cm=True),
    5: dict(y=4, m=1, d=2, t=3, cm=True),
    6: dict(y=0, m=1, d=2, t=3, cm=False),
    7: dict(y=3, m=0, d=1, t=2, cm=True),
    8: dict(y=0, m=1, d=2, t=3, cm=False),
}
for _v in _fmt_map.values():  # Add the minimum size the date/time array needs to be for each format
    _v.update(max=max([_i for _i in _v.values() if not isinstance(_i, bool)]))


def date_to_epoch(date_time, fmt=0):
    """Converts a date and time string to epoch time. Originally intended for various date formats in FOS.

    WARNING: Time zone to UTC conversion not yet implemented.

    If .msec is not present in any of the below output it is treated as 0.
    +-------+-------------------------------------------+-----------------------------------------------------------+
    | fmt   | Sample                                    | Where Used                                                |
    +=======+===========================================+===========================================================+
    |  0    | Dec 31, 2021 hh:mm:ss.msec EDT (May or    |                                                           |
    |       | may not have the comma)                   |                                                           |
    +-------+-------------------------------------------+-----------------------------------------------------------+
    |  1    | 31 Dec 2021 hh:mm:ss.msec EDT             |                                                           |
    +-------+-------------------------------------------+-----------------------------------------------------------+
    |  2    | 12/31/2021 hh:mm:ss.msec EDT (or          |                                                           |
    |       | 12-31-2021 or 12 31 2021)                 |                                                           |
    +-------+-------------------------------------------+-----------------------------------------------------------+
    |  3    | 31/12/2021 hh:mm:ss.msec EDT (or          |                                                           |
    |       | 31-12-2021 or 31 12 2021)                 |                                                           |
    +-------+-------------------------------------------+-----------------------------------------------------------+
    |  4    | Tue Dec 31 hh:mm:ss.msec EDT 2021         | (CLI) date                                                |
    +-------+-------------------------------------------+-----------------------------------------------------------+
    |  5    | Tue Dec  3 hh:mm:ss 2020                  | (CLI) clihistory                                          |
    +-------+-------------------------------------------+-----------------------------------------------------------+
    |  6    | 2021/12/31-hh:mm:ss                       | (CLI) errdump                                             |
    +-------+-------------------------------------------+-----------------------------------------------------------+
    |  7    | Dec 31 hh:mm:ss.msec 2021 EDT             | (OpenSSL) certs                                           |
    +-------+-------------------------------------------+-----------------------------------------------------------+
    |  8    | 2021-12-31Thh:mm:ss+00:00                 | brocade-logging/error-log                                 |
    |       |                                           | brocade-logging/audit-log                                 |
    +-------+-------------------------------------------+-----------------------------------------------------------+

    :param date_time: Date and time
    :type date_time: str
    :param fmt: Format. See table above
    :type fmt: int
    :return: Epoch time. 0 If an error was encountered.
    :rtype: float
    """
    global month_to_num, _fmt_map

    year, month, day, time_l = 0, 0, 0, list()  # Just to keep the IDE analyzer from whining

    # Get and validate the input string.
    ml = list()
    buf = date_time.replace('T', ' ') if fmt == 8 else date_time
    ts_l = remove_duplicate_space(date_to_space.sub(' ', buf)).split(' ')
    if fmt in _fmt_map:
        if len(ts_l) >= _fmt_map[fmt]['max']:
            d = _fmt_map[fmt]

            # Get the year
            buf = ts_l[d['y']]
            year = int(buf) if buf.isnumeric() else None
            if year is None or year < 1970:
                ml.append('Invalid year: ' + str(year))

            # Get the month
            buf = ts_l[d['m']]
            month = month_to_num.get(buf.lower()) if d['cm'] else int(buf) if buf.isnumeric() else None
            if month is None or month < 1 or month > 12:
                ml.append('Invalid month: ' + str(month))

            # Get the day
            buf = ts_l[d['d']]
            day = int(buf) if buf.isnumeric() else None
            if day is None or day < 1 or day > 31:
                ml.append('Invalid day: ' + str(day))

            # Get the time
            time_l = [int(buf) if buf.isnumeric() else None for buf in ts_l[d['t']].replace('.', ':').split(':')]
            if len(time_l) == 3:
                time_l.append(0)  # Fractional seconds are not always included with the time stamp
            if len(time_l) != 4 or None in time_l:
                ml.append('Invalid time: ' + ts_l[d['t']])
        else:
            ml.append('Invalid date/time stamp')
    else:
        ml.append('Invalid format (fmt): ' + str(fmt))

    if len(ml) > 0:
        ml.append('Unsupported format for: ' + date_time + ' Format, fmt, is: ' + str(fmt))
        brcdapi_log.exception(ml, echo=True)
        return 0.0

    return datetime.datetime(year, month, day, time_l[0], time_l[1], time_l[2], time_l[3]).timestamp()


def pad_string(in_buf, pad_len, pad_char, append=False):
    """Pads characters to a string to a fixed length. This is a cheesy way to support report formatting without textable

    :param in_buf: The text string to pad
    :type in_buf: str
    :param pad_len: Total number of characters
    :type pad_len: int
    :param pad_char: Pad character. Must be a single character string.
    :type pad_char: str
    :param append: True: Append pad character to the end of the string. False: Prepend pad characters to the beginning
    :type append: bool
    :return: Padded text
    :rtype: str
    """
    buf = '' if in_buf is None else in_buf
    x, pad_buf = pad_len-len(buf), ''
    for i in range(0, x):
        pad_buf += pad_char
    return buf + pad_buf if append else pad_buf + buf


def wrap_text(buf, max_len, prepend_buf=None):
    """Formats text into paragraphs.

    :param buf: The text string(s) to format
    :type buf: str, list, tuple, None
    :param max_len: Maximum line length
    :type max_len: int
    :param prepend_buf: Prefix text inserted at the beginning of each string in in_buf. If additional lines are
        required, subsequent lines are padded with all spaces. Typically used for bullets. prepend_buf is not prepended
        for blank lines.
    :type prepend_buf: str, None
    :return: Formatted text
    :rtype: list
    """
    rl = list()
    if buf is None:
        return rl
    w_prepend_buf = '' if prepend_buf is None else prepend_buf

    # Validate the input
    if not isinstance(buf, (list, tuple, str)):
        rl.append('buf type, ' + str(type(buf)) + ', is not valid. Type must be str, list, tuple, or None.')
    if not isinstance(max_len, int):
        rl.append('max_len type, ' + str(type(max_len)) + ', is not valid. Type must be int.')
    if not isinstance(w_prepend_buf, str):
        rl.append('prepend_buf type, ' + str(type(max_len)) + ', is not valid. Type must be None or str.')
    if len(rl) > 0:
        brcdapi_log.exception(rl, echo=True)
        return list()

    # Format the text
    next_pad = pad_string('', len(w_prepend_buf), ' ', append=True)
    for t_buf in convert_to_list(buf):
        print_buf = w_prepend_buf
        i = 0
        for w_buf in t_buf.split(' '):
            if i == 0:
                print_buf += w_buf
                i += 1
            elif len(print_buf) + len(w_buf) >= max_len:
                rl.append(print_buf)
                print_buf, i = next_pad + w_buf, i + 1
            else:
                print_buf += ' ' + w_buf
                i += 1
        rl.append(print_buf)

    return rl


# Case statements fir get_input()
def _get_input_bool(parser, k, d):
    parser.add_argument('-' + str(k), help=d['h'], action='store_true', required=d.get('r', True))


def _get_input_int(parser, k, d):
    parser.add_argument('-'+str(k), help=d['h'], type=int, required=d.get('r', True))


def _get_input_float(parser, k, d):
    parser.add_argument('-'+str(k), help=d['h'], type=float, required=d.get('r', True))


def _get_input_str(parser, k, d):
    parser.add_argument('-' + str(k), help=d['h'], type=str, required=d.get('r', True))


def _get_input_list(parser, k, d):
    parser.add_argument('-' + str(k), help=d['h'], type=list, required=d.get('r', True))


def _get_input_none(parser, k, d):
    parser.add_argument('-' + str(k), help=d['h'], required=d.get('r', True))


_get_input_d = dict(
    bool=_get_input_bool,
    int=_get_input_int,
    float=_get_input_float,
    str=_get_input_str,
    list=_get_input_list,
    none=_get_input_none,
)


def get_input(desc, param_d):
    """Performs standard command line input parsing using argparse

    Returns a dictionary of arguments. The key is the option, without the leading -. Value is the entered value.

    Dictionaries of param_d detail:

    +-------+---------------+---------------------------------------------------------------------------------------+
    | Key   | Type          | Description                                                                           |
    +=======+===============+=======================================================================================+
    | d     | any           | The return value for any optional parameter when not specified. Default is None.      |
    |       |               | WARNING: This can be anything you want. Dictionaries, pointers, etc. Keep in mind     |
    |       |               | that the power to do whatever you want also gives you the power to do some pretty     |
    |       |               | stupid stuff.                                                                         |
    +-------+---------------+---------------------------------------------------------------------------------------+
    | h     | str           | Help text                                                                             |
    +-------+---------------+---------------------------------------------------------------------------------------+
    | r     | None, bool    | Required parameter. The default is False                                              |
    +-------+---------------+---------------------------------------------------------------------------------------+
    | t     | str           | If bool, sets action='store_true', not the "type=bool" parameter. All else sets       |
    |       |               | "type=t". Supported types are: bool, int, float, str, list. If ommitted, "type=" is   |
    |       |               | not specified. argparse treats the argument as a str by default.                      |
    +-------+---------------+---------------------------------------------------------------------------------------+
    | v     | list, tuple   | Valid parameter options                                                               |
    +-------+---------------+---------------------------------------------------------------------------------------+

    :param desc: General module description displayed with -h
    :type desc: str
    :param param_d: As described above
    :type param_d: dict
    """
    global _get_input_d

    return_d, el = dict(), list()

    # Set up parameter parsing for argparse
    parser = argparse.ArgumentParser(description=desc)
    for k, d in param_d.items():
        t = d.get('t', 'none')
        try:
            _get_input_d[t](parser, k, d)
        except KeyError as e:
            el.append('Missing or invalid key: ' + str(e))

    for k, v in vars(parser.parse_args()).items():
        val = param_d[k].get('d', None) if v is None else v
        if param_d[k].get('r', True) or val is not None:
            valid_val_l = param_d[k].get('v', None)
            if valid_val_l is not None:
                try:
                    if val not in valid_val_l:
                        el.append('Invalid value, ' + str(val) + ', for -' + str(k))
                except TypeError:
                    el.append('Invalid value, ' + str(val) + ' type: ' + str(type(val)) + ', for -' + str(k))
        return_d.update({k: val})

    # If there are errors, report them and exit. Note that the log isn't set up yet, so use print()
    if len(el) > 0:
        for buf in el:
            print(buf)
        print('Re-run with the -h option for additional help')
        exit(0)

    return return_d


def sp_range_to_list(port_range):
    """Returns a list of ports based on a range of ports using s/p notation

    :param port_range: CSV list of port ranges in s/p notation
    :type port_range: str, None
    :return: Ports
    :rtype: list
    """
    rl = list()
    if port_range is None:
        return rl
    for sp_range in port_range.split(','):
        temp_l = sp_range.split('/')
        if len(temp_l) == 1:
            temp_l.insert(0, '0')
        if len(temp_l) != 2:
            brcdapi_log.exception('Invalid port range.', echo=True)
            return rl
        for slot in range_to_list(temp_l[0]):
            rl.extend([str(slot) + '/' + str(p) for p in range_to_list(temp_l[1])])

    return rl


def _match_str_exact(test_l, search_term, ignore_case=False):
    """Finds items in test_list that match test_str exactly.

    :param test_list: Input list of strings to test against
    :type test_list: tuple, list
    :param search_term: Match test
    :param ignore_case: Default is False. If True, ignores case in search_term. Not that keys are always case-sensitive
    :type ignore_case: bool
    :type search_term: str
    :return: List of matches
    :rtype: list
    """
    s = search_term.lower() if ignore_case else search_term
    return [c for c in test_l if c.lower() == s] if ignore_case else [c for c in test_l if c == s]


def _match_str_wild(test_l, search_term, ignore_case):
    """Finds items in test_list using wild card matching in test_str. See _match_str_exact() for parameters"""
    s = search_term.lower() if ignore_case else search_term
    return [c for c in test_l if fnmatch.fnmatch(c, s)] if ignore_case \
        else [c for c in test_l if fnmatch.fnmatchcase(c, s)]


def _match_str_regexm(test_l, search_term, ignore_case):
    """Finds items in test_list using ReGex Matching in test_str. See _match_str_exact() for parameters"""
    regex_obj = re.compile(search_term, re.IGNORECASE) if ignore_case else re.compile(search_term)
    return [c for c in test_l if regex_obj.match(c)]


def _match_str_regexs(test_l, search_term, ignore_case):
    """Finds items in test_list using ReGex Searching in test_str. See _match_str_exact() for parameters"""
    regex_obj = re.compile(search_term, re.IGNORECASE) if ignore_case else re.compile(search_term)
    return [c for c in test_l if regex_obj.search(c)]


_match_str_d = {
    'exact': _match_str_exact,
    'wild': _match_str_wild,
    'regexm': _match_str_regexm,
    'regex_m': _match_str_regexm,
    'regex-m': _match_str_regexm,
    'regexs': _match_str_regexs,
    'regex_s': _match_str_regexs,
    'regex-s': _match_str_regexs,
}


def match_str(test_l, search_term, ignore_case=False, stype='exact'):
    """Returns a list of strings using exact, wild card, ReGex match, or ReGex search.

    **Summary of wild card strings**

    Search the web for 'python fnmatch.fnmatch' for additional information

    *         matches everything
    ?         matches any single character
    [seq]     matches any character in seq
    [!seq]    matches any character not in seq

    **Summary of ReGex strings**

    Search the web for 'regex' for additional information. A regex match must match the beginning of the string. A regex
    search must match any instance of the regex in the string.

    abc…          Letters
    123…          Digits
    \d            Any Digit
    \D            Any Non - digit character
    .             Any Character
    \.            Period
    [abc]         Only a, b, or c
    [ ^ abc]      Not a, b, nor c
    [a - z]       Characters a to z
    [0 - 9]       Numbers 0 to 9
    \w            Any Alphanumeric character
    \W            Any Non - alphanumeric character
    {m}           m Repetitions
    {m, n}        m to n Repetitions
    *             Zero or more repetitions
    +             One or more repetitions
    ?             Optional character
    \s            Any Whitespace
    \S            Any Non - whitespace character
    ^ …$          Starts and ends
    (…)           Capture Group
    (a(bc))       Capture Sub - group
    (.*)          Capture all
    (abc | def )  Matches abc or def

    :param test_l: Strings to test against
    :type test_l: list, tuple
    :param search_term: text to test against. Maybe a regex, wildcard, or exact match
    :type search_term: str
    :param ignore_case: Default is False. If True, ignores case in search_term. Note that keys are always case-sensitive
    :type ignore_case: bool
    :param stype: Valid options are keys in _match_str_d
    :param stype: str
    :return return_list: List of items matching the search criteria.
    :rtype: list
    """
    global _match_str_d

    # Validate the input
    el = list()
    if not isinstance(test_l, (tuple, list)):
        el.append('Invalid test list, test_list, type: ' + str(type(test_l)))
    if not isinstance(search_term, str):
        el.append('Invalid test string, search_term, type: ' + str(type(search_term)))
    if not isinstance(ignore_case, bool):
        el.append('Ignore case must be a boolean. Type: ' + str(type(ignore_case)))
    if not isinstance(stype, str):
        el.append('Invalid type for search term, stype: ' + str(type(stype)))
    elif not _match_str_d.get(stype, False):
        el.append('Invalid test type, stype: ' + stype)
    if len(el) > 0:
        brcdapi_log.exception(el, echo=True)
        return list()

    return _match_str_d[stype](test_l, search_term, ignore_case)
