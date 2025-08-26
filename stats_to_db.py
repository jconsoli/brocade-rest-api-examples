#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Copyright 2023, 2024, 2025 Consoli Solutions, LLC.  All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
the License. You may also obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
language governing permissions and limitations under the License.

The license is free for single customer use (internal applications). Use of this module in the production,
redistribution, or service delivery for commerce requires an additional license. Contact jack@consoli-solutions.com for
details.

:mod:`stats_to_db` - Example on how to capture port statistics and add them to your own database

**Description**

  This module contains sample code to illustrate:

  * How to capture basic port information
  * How to capture GE port statistics
  * Considerations for adding the statistics to a database
    * Databases require unique keys.
    * Many database applications have key naming convention rules.

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Set verbose debug via brcdapi.brcdapi_rest.verbose_debug()                            |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 25 Aug 2025   | Replaced obsolete "supress" in call to brcdapi_log.open_log with "suppress".          |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2023, 2024, 2025 Consoli Solutions, LLC'
__date__ = '25 Aug 2025'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.2'

import argparse
import brcdapi.util as brcdapi_util
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as brcdapi_auth
import brcdapi.log as brcdapi_log

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation
_DEBUG = False   # When True, instead of getting input parameters from the command line (shell), use:
_DEBUG_ip = 'xxx.xxx.xxx.xxx'
_DEBUG_id = 'admin'
_DEBUG_pw = 'password'
_DEBUG_sec = 'self'  # Use None or 'none' for HTTP. Use the certificate if HTTPS and not self-signed
_DEBUG_fid = '128'
_DEBUG_verbose = False  # When True, all content and responses are formatted and printed (pprint).
_DEBUG_log = '_logs'
_DEBUG_nl = False


def _db_add(key_0, key_1, key_2, val):
    """Stubbed out method to add key value pairs to your database. Derives a unique key from a hash of the 3 input keys

    :param key_0: First key (switch WWN in xx:xx:xx:xx:xx:xx:xx:xx notation)
    :type key_0: str
    :param key_1: Second key (port number in s/p notation)
    :type key_1: str
    :param key_2: Third key (value type such as CRC)
    :type key_2: str
    :param val: Value associated with the keys
    :type val: str, int, float
    """
    # You might want to make sure you are adding a valid value to your database.
    if not isinstance(val, (str, int, float)):
        brcdapi_log.log('Invalid value type, ' + str(type(val)) + ', for database.', True)
        return

    # Verbose explanation of the next line of code:
    # key_list = list() - create a list to store the keys in
    # for key in (key_0, key_1, key_2):
    #     clean_key = key.replace(':', '_').replace('/', '_') - Replace ':' and '/' with '_'
    #     short_key = clean_key[11:] - removes the non-unique portion of WWN in the key
    #     key_list.append(short_key) - Add the key to key_list
    # For the Python savvy, a compiled regex would be better than .replace() above but this is good enough for a simple
    # example. Using a regex probably won't save enough time to make researching it worthwhile so if you don't
    # understand this comment, just stick with using .replace().
    key_list = [key.replace(':', '_').replace('/', '_')[11:] for key in (key_0, key_1, key_2)]

    unique_key = '_'.join(key_list)  # Concatenates all items in key_list seperated by a '_'
    brcdapi_log.log('Adding key: ' + unique_key + ', Value: ' + str(val), True)


def parse_args():
    """Parses the module load command line

    :return: ip, id, pw, sec, FID, verbose debug flag, log folder, log flag
    :rtype: (str, str, str, str, str, bool, str, bool)
    """
    global _DEBUG, _DEBUG_ip, _DEBUG_id, _DEBUG_pw, _DEBUG_sec, _DEBUG_fid, _DEBUG_verbose, _DEBUG_log, _DEBUG_nl

    if _DEBUG:
        args_ip, args_id, args_pw, args_s, args_fid, args_d, args_log, args_nl =\
            _DEBUG_ip, _DEBUG_id, _DEBUG_pw, _DEBUG_sec, _DEBUG_fid, _DEBUG_verbose, _DEBUG_log, _DEBUG_nl
    else:
        buf = 'This is a programming example only. It illustrates how to capture port statistics and additional ' \
              'information that is typical of a custom script to capture statistics and add them to a database.'
        parser = argparse.ArgumentParser(description=buf)
        parser.add_argument('-ip', help='(Required) IP address', required=True)
        parser.add_argument('-id', help='(Required) User ID', required=True)
        parser.add_argument('-pw', help='(Required) Password', required=True)
        parser.add_argument('-s', help='Optional. "none" for HTTP. The default is "self" for HTTPS mode.',
                            required=False,)
        parser.add_argument('-fid', help='(Required) Virtual Fabric ID.', required=True)
        buf = '(Optional) Enable debug logging. Prints the formatted data structures (pprint) to the log and console.'
        parser.add_argument('-d', help=buf, action='store_true', required=False)
        buf = '(Optional) Directory where log file is to be created. Default is to use the current directory. The ' \
              'log file name will always be "Log_xxxx" where xxxx is a time and date stamp.'
        parser.add_argument('-log', help=buf, required=False, )
        buf = '(Optional) No parameters. When set, a log file is not created. The default is to create a log file.'
        parser.add_argument('-nl', help=buf, action='store_true', required=False)
        args = parser.parse_args()
        args_ip, args_id, args_pw, args_s, args_fid, args_d, args_log, args_nl = \
            args.ip, args.id, args.pw, args.s, args.fid, args.d, args.log, args.nl

    # Default security
    if args_s is None:
        args_s = 'self'

    return args_ip, args_id, args_pw, args_s, args_fid, args_d, args_log, args_nl


def pseudo_main():
    """Basically the main(). Did it this way to use with IDE
    :return: Exit code
    :rtype: int
    """
    global _DEBUG

    ec, uri, fid, switch_wwn = 0, '', 0, None  # Error code. 0: No errors. -1: error encountered

    # Get the command line input
    ml = ['WARNING!!! Debug is enabled'] if _DEBUG else list()
    ip, user_id, pw, sec, fid_str, vd, log, nl = parse_args()
    if vd:
        brcdapi_rest.verbose_debug(True)
    if sec is None:
        sec = 'none'
    brcdapi_log.open_log(folder=args_log, suppress=False, version_d=brcdapi_util.get_import_modules(), no_log=args_nl)

    ml.append('FID: ' + fid_str)
    try:
        fid = int(fid_str)
    except ValueError:
        brcdapi_log.log('Invalid FID, -f. FID must be an integer between 1-128')
    brcdapi_log.log(ml, True)

    # Login
    session = brcdapi_rest.login(user_id, pw, ip, sec)
    if brcdapi_auth.is_error(session):
        brcdapi_log.log('Login failed:\n' + brcdapi_auth.formatted_error_msg(session), True)
        return -1

    port_info_d = dict()  # Will use this to store basic port information
    port_stats_d = dict()  # Will use this to store port statistics in

    # You may want to put better error checking in your code as well as use a more efficient code. A verbose coding
    # style was used here for readability.
    try:
        # Get the switch WWN
        brcdapi_log.log('Capturing chassis Data', True)
        uri = 'running/brocade-fibrechannel-logical-switch/fibrechannel-logical-switch'
        obj = brcdapi_rest.get_request(session, uri)
        if brcdapi_auth.is_error(obj):
            brcdapi_log.log(brcdapi_auth.formatted_error_msg(obj), True)
            ec = -1
        else:
            # Find the switch with the matching FID
            for switch_obj in obj['fibrechannel-logical-switch']:
                if switch_obj['fabric-id'] == fid:
                    switch_wwn = switch_obj['switch-wwn']
                    break
                if switch_wwn is None:
                    brcdapi_log.log('Logical switch for FID ' + str(fid) + 'not found', True)
                    ec = -1

        # Get some basic port information
        if ec == 0:  # Make sure we didn't encounter any errors above
            # It's common to keep track of other port information, such as the user-friendly name and FC address. Below
            # captures this basic port information.
            brcdapi_log.log('Capturing basic port information.', True)
            uri = 'running/brocade-interface/fibrechannel'
            port_info = brcdapi_rest.get_request(session, uri, fid)
            if brcdapi_auth.is_error(port_info):
                brcdapi_log.log(brcdapi_auth.formatted_error_msg(port_info), True)
                ec = -1
            else:
                # To make it easier to match the port information with the port statistics, we're going to create a
                # dictionary using the port name (port number) as the key
                for port_obj in port_info['fibrechannel']:
                    port_info_d.update({port_obj['name']: port_obj})

        # Capture the port statistics
        if ec == 0:  # Make sure we didn't encounter any errors above
            brcdapi_log.log('Capturing port statistics', True)
            uri = 'running/brocade-interface/fibrechannel-statistics'
            port_stats = brcdapi_rest.get_request(session, uri, fid)
            if brcdapi_auth.is_error(port_stats):
                brcdapi_log.log(brcdapi_auth.formatted_error_msg(port_stats), True)
                ec = -1
            else:
                # We could just add each port to the database here but since it's common to capture additional
                # information, such as determining the login alias(es), we'll add it to a dictionary as was done with
                # the basic port information
                for port_obj in port_stats['fibrechannel-statistics']:
                    port_stats_d.update({port_obj['name']: port_obj})

        # Add all the ports to the database
        if ec == 0:  # Make sure we didn't encounter any errors above
            brcdapi_log.log('Adding key value pairs to the database.', True)
            for port_num, port_obj in port_info_d.items():
                sub_key = 'fcid-hex'  # Just using the FC address for this example
                _db_add(switch_wwn, port_num, sub_key, port_obj[sub_key])
                for k, v in port_stats_d[port_num].items():
                    _db_add(switch_wwn, port_num, k, v)

    except brcdapi_util.VirtualFabricIdError:
        brcdapi_log.log('Software error. Search the log for "Invalid FID" for details.', echo=True)
        ec = -1
    except BaseException as e:
        brcdapi_log.exception(['Programming error encountered while processing: ' + uri,
                               str(type(e)) + ': ' + str(e)],
                              echo=True)
        ec = -1

    # Logout
    obj = brcdapi_rest.logout(session)
    if brcdapi_auth.is_error(obj):
        brcdapi_log.log('Logout failed:\n' + brcdapi_auth.formatted_error_msg(obj), True)
        ec = -1

    return ec


###################################################################
#
#                    Main Entry Point
#
###################################################################
if _DOC_STRING:
    print('_DOC_STRING set. No processing')
    exit(0)

_ec = pseudo_main()
brcdapi_log.close_log('Processing Complete. Exit code: ' + str(_ec))
exit(_ec)
