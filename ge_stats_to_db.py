#!/usr/bin/python
# -*- coding: utf-8 -*-
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

**Description**

  Example on how to capture GE port statistics and add them to your own database. Similar to stats_to_db, this module
  contains sample code to illustrate:

  * How to capture basic port information
  * How to capture GE port statistics
  * Considerations for adding the statistics to a database
    * Databases require unique keys.
    * Many database applications have key naming convention rules.

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 06 Mar 2024   | Initial launch                                                                        |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Dec 2024   | Fixed spelling mistake in message.                                                    |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""

__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2024 Consoli Solutions, LLC'
__date__ = '06 Dec 2024'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack@consoli-solutions.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.1'

import argparse
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as brcdapi_auth
import brcdapi.util as brcdapi_util
import brcdapi.log as brcdapi_log

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation
# _STAND_ALONE: True: Executes as a standalone module taking input from the command line. False: Does not automatically
# execute. This is useful when importing this module into another module that calls psuedo_main().
_STAND_ALONE = True  # See note above

_input_d = gen_util.parseargs_login_d.copy()
_input_d.update(fid=dict(t='int', v=gen_util.range_to_list('1-128'), h='Required. Fabric ID of logical switch'))
_input_d.update(gen_util.parseargs_log_d.copy())
_input_d.update(gen_util.parseargs_debug_d.copy())


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


def pseudo_main(ip, user_id, pw, sec, fid):
    """Basically the main(). Did it this way to use with IDE

    :param ip: Switch IP address
    :type ip: str
    :param user_id: User ID
    :type user_id: str
    :param pw: User password
    :type ip: str
    :param sec: Secure method. None for HTTP, otherwise the certificate or 'self' if self-signed
    :type sec: str, None
    :param fid: Fabric ID of logical switch the statistics will be collected from.
    :type fid: int
    :return: Exit code
    :rtype: int
    """
    ec, switch_wwn = 0, None  # Error code. 0: No errors. -1: error encountered

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
        uri = 'brocade-fibrechannel-logical-switch/fibrechannel-logical-switch'
        obj = brcdapi_rest.get_request(session, uri)
        if brcdapi_auth.is_error(obj):
            brcdapi_log.log(brcdapi_auth.formatted_error_msg(obj), True)
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
        if ec == 0:  # Make sure we didn't encounter any errors above
            # It's common to keep track of other port information, such as the user-friendly name.
            # Capture some basic port information.
            brcdapi_log.log('Capturing basic port information.', True)
            uri = 'brocade-interface/fibrechannel'
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
            uri = 'brocade-interface/fibrechannel-statistics'
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
        brcdapi_log.exception(['Programming error encountered.', str(type(e)) + ': ' + str(e)], echo=True)
        ec = -1

    # Logout
    obj = brcdapi_rest.logout(session)
    if brcdapi_auth.is_error(obj):
        brcdapi_log.log('Logout failed:\n' + brcdapi_auth.formatted_error_msg(obj), True)
        ec = -1

    return ec


def _get_input():
    """Parses the module load command line

    :return: Exit code
    :rtype: int
    """
    global __version__, _input_d

    # Get command line input
    args_d = gen_util.get_input('Delete logical switches.', _input_d)

    # Set up logging
    if args_d['d']:
        brcdapi_rest.verbose_debug(True)
    brcdapi_log.open_log(folder=args_d['log'], suppress=args_d['sup'], no_log=args_d['nl'])

    # Command line feedback
    ml = ['ge_stats_to_db.py:   ' + __version__,
          'IP, -ip:             ' + brcdapi_util.mask_ip_addr(args_d['ip'], keep_last=True),
          'ID, -id:             ' + args_d['id'],
          'Security, -s:        ' + args_d['s'],
          'FID, -fid:           ' + args_d['fid'],
          'Log, -log:           ' + str(args_d['log']),
          'No log, -nl:         ' + str(args_d['nl']),
          'Debug, -d:           ' + str(args_d['d']),
          'Suppress, -sup:      ' + str(args_d['sup']),
          '', ]
    brcdapi_log.log(ml, echo=True)

    return pseudo_main(args_d['ip'], args_d['id'], args_d['pw'], args_d['s'], args_d['fid'])


###################################################################
#
#                    Main Entry Point
#
###################################################################
if _DOC_STRING:
    print('_DOC_STRING is True. No processing')
    exit(brcddb_common.EXIT_STATUS_OK)

if _STAND_ALONE:
    _ec = _get_input()
    brcdapi_log.close_log(['', 'Processing Complete. Exit code: ' + str(_ec)], echo=True)
    exit(_ec)
