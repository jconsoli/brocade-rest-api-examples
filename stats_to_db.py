#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2021 Jack Consoli.  All rights reserved.
#
# NOT BROADCOM SUPPORTED
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may also obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
:mod:`stats_to_db` - Example on how to capture port statistics and add them to your own database

**Description**

  For any database to work, the keys must be unique. Since multiple switches can have the same port and in environments
  with multiple fabrics, it's possible to have the same fibre channel address. In this example, a unique key is a hash
  of the switch WWN and port number. Note that the switch WWN will always be unique.

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 1.0.0     | 25 Feb 2021   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2021 Jack Consoli'
__date__ = '25 Feb 2021'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '1.0.0'

from pprint import pformat
import argparse
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.pyfos_auth as pyfos_auth
import brcdapi.log as brcdapi_log

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation
_DEBUG = False   # When True, use _DEBUG_IP, _DEBUG_ID, _DEBUG_PW, _DEBUG_OUTF, and _DEBUG_VERBOSE
_DEBUG_IP = 'xxx.xxx.xxx.xxx'
_DEBUG_ID = 'admin'
_DEBUG_PW = 'password'
_DEBUG_SEC = 'self'  # Use None or 'none' for HTTP. Use the certificate if HTTPS and not self signed
_DEBUG_FID = '128'
_DEBUG_VERBOSE = False  # When True, all content and responses are formatted and printed (pprint).
_DEBUG_LOG = '_logs'
_DEBUG_NL = False


def _db_add(key_0, key_1, key_2, val):
    """Stubbed out method to add key value pairs to your database

    :param key_0: First key
    :type key_0: str
    :param key_1: Second key
    :type key_1: str
    :param key_2: Third key
    :type key_2: str
    :param val: Value associated with the keys
    :type val: str, int, float
    """
    # You might want to make sure you are adding a valid value to your database.
    if not isinstance(val, (str, int, float)):
        brcdapi_log.log('Invalid value type, ' + str(type(val)) + ', for database.', True)
        return
    # It's probably a good idea to make sure the keys are valid as well. In this example, we're only going to convert
    # ':' (used in the switch WWN) and '/' (used in the port number) to an underscore, '_'. There may be other
    # characters, such as '-', that are not valid database keys that you will need to modify.

    key_list = [key.replace(':', '_').replace('/', '_') for key in (key_0, key_1, key_2)]
    # If you are new to Python, above is equivalent to:
    # key_list = list()
    # for key in (key_0, key_1, key_2):
    #     key_list.append(key.replace(':', '_').replace('/', '_'))
    # It's probably better to do the equivalent of the key.replace above with a compiled regex but for the few usec it
    # may save, this is good enough for a simple example.

    brcdapi_log.log('Adding key: ' + '/'.join(key_list) + ', Value: ' + str(val), True)


def parse_args():
    """Parses the module load command line

    :return: ip, id, pw, file
    :rtype: (str, str, str, str)
    """
    global _DEBUG_IP, _DEBUG_ID, _DEBUG_PW, _DEBUG_SEC, _DEBUG_FID, _DEBUG_VERBOSE, _DEBUG_LOG, _DEBUG_NL

    if _DEBUG:
        return _DEBUG_IP, _DEBUG_ID, _DEBUG_PW, _DEBUG_SEC, _DEBUG_FID, _DEBUG_VERBOSE, _DEBUG_LOG, _DEBUG_NL
    else:
        buf = 'This is a programming example only. It illustrates how to capture port statistics and additional '\
              'information that is typical of a custom script to capture statistics and add them to a database.'
        parser = argparse.ArgumentParser(description=buf)
        parser.add_argument('-ip', help='(Required) IP address', required=True)
        parser.add_argument('-id', help='(Required) User ID', required=True)
        parser.add_argument('-pw', help='(Required) Password', required=True)
        buf = '(Optional) Default is HTTP. Certificate or "self" for HTTPS mode.'
        parser.add_argument('-s', help=buf, required=False,)
        parser.add_argument('-fid', help='(Required) Virtual Fabric ID.', required=True)
        buf = '(Optional) Enable debug logging. Prints the formatted data structures (pprint) to the log and console.'
        parser.add_argument('-d', help=buf, action='store_true', required=False)
        buf = '(Optional) Directory where log file is to be created. Default is to use the current directory. The ' \
              'log file name will always be "Log_xxxx" where xxxx is a time and date stamp.'
        parser.add_argument('-log', help=buf, required=False, )
        buf = '(Optional) No parameters. When set, a log file is not created. The default is to create a log file.'
        parser.add_argument('-nl', help=buf, action='store_true', required=False)
        args = parser.parse_args()
        return args.ip, args.id, args.pw, args.s, args.fid, args.d, args.log, args.nl


def pseudo_main():
    """Basically the main(). Did it this way to use with IDE
    :return: Exit code
    :rtype: int
    """
    # Get the command line input
    ml = ['WARNING!!! Debug is enabled'] if _DEBUG else list()
    ip, user_id, pw, sec, fid_str, vd, log, nl = parse_args()
    if vd:
        brcdapi_rest.verbose_debug = True
    if sec is None:
        sec = 'none'
    if not nl:
        brcdapi_log.open_log(log)
    ml.append('FID: ' + fid_str)
    try:
        fid = int(fid_str)
    except:
        brcdapi_log.log('Invalid FID, -f. FID must be an integer between 1-128')
    brcdapi_log.log(ml, True)

    # Login
    session = brcdapi_rest.login(user_id, pw, ip, sec)
    if pyfos_auth.is_error(session):
        brcdapi_log.log('Login failed:\n' + pyfos_auth.formatted_error_msg(session), True)
        return -1

    ec = 0  # Error code. 0: No errors. -1: error encountered
    port_info_d = dict()  # Will use this to store basic port information
    port_stats_d = dict()  # Will use this to store port statistics in

    # You may want to put better error checking in your code as well as use a more efficient code. A verbose coding
    # style was used here for readability.
    try:
        # Get the switch WWN
        brcdapi_log.log('Capturing chassis Data', True)
        uri = 'brocade-fibrechannel-logical-switch/fibrechannel-logical-switch'
        obj = brcdapi_rest.get_request(session, uri)
        if pyfos_auth.is_error(obj):
            brcdapi_log.log(pyfos_auth.formatted_error_msg(obj), True)
            ec = -1
        else:
            # Find the switch with the matching FID
            switch_wwn = None
            for switch_obj in obj['fibrechannel-logical-switch']:
                if switch_obj['fabric-id'] == fid:
                    switch_wwn = switch_obj['switch-wwn']
                    break
            if switch_wwn is None:
                brcdapi_log.log('Logical switch for FID ' + str(fid) + 'not found', True)
                ec = -1

        # Get some basic port information
        if ec == 0:  # Make sure we didn't encountered any errors above
            # It's common to keep track of other port information besides just the statistics so here we are going to
            # capture some basic port information.
            brcdapi_log.log('Capturing basic port information.', True)
            uri = 'brocade-interface/fibrechannel'
            port_info = brcdapi_rest.get_request(session, uri, fid)
            if pyfos_auth.is_error(port_info):
                brcdapi_log.log(pyfos_auth.formatted_error_msg(port_info), True)
                ec = -1
            else:
                # To make it easier to match the port information with the port statistics, we're going to create a
                # a dictionary using the port name (port number) as the key
                for port_obj in port_info['fibrechannel']:
                    port_info_d.update({port_obj['name']: port_obj})

        # Capture the port statistics
        if ec == 0:  # Make sure we didn't encountered any errors above
            brcdapi_log.log('Capturing port statistics', True)
            uri = 'brocade-interface/fibrechannel-statistics'
            port_stats = brcdapi_rest.get_request(session, uri, fid)
            if pyfos_auth.is_error(port_stats):
                brcdapi_log.log(pyfos_auth.formatted_error_msg(port_stats), True)
                ec = -1
            else:
                # We could just add each port to the database here but since it's common to capture additional
                # information, such as determining the login alias(es), we'll add it to a dictionary as was done with
                # the basic port information
                for port_obj in port_stats['fibrechannel-statistics']:
                    port_stats_d.update({port_obj['name']: port_obj})

        # Add all the ports to the database
        if ec == 0:  # Make sure we didn't encountered any errors above
            brcdapi_log.log('Adding key value pairs to the database.', True)
            for port_num, port_obj in port_info_d.items():
                sub_key = 'fcid-hex'  # Just using the FC address for this example
                _db_add(switch_wwn, port_num, sub_key, port_obj[sub_key])
                for k, v in port_stats_d[port_num].items():
                    _db_add(switch_wwn, port_num, k, v)

    except:
        # The exception() method preceeds the passed message parameter with a stack trace
        brcdapi_log.exception('Unknown programming error occured whild processing: ' + uri, True)

    # Logout
    obj = brcdapi_rest.logout(session)
    if pyfos_auth.is_error(obj):
        brcdapi_log.log('Logout failed:\n' + pyfos_auth.formatted_error_msg(obj), True)
        return -1

    return 0


###################################################################
#
#                    Main Entry Point
#
###################################################################

_ec = 0
if _DOC_STRING:
    print('_DOC_STRING set. No processing')
else:
    _ec = pseudo_main()
    brcdapi_log.close_log('Processing Complete. Exit code: ' + str(_ec), True)
exit(_ec)
