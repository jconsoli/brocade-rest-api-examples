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

    Simple zone configuration activation example. Activates an existing zone configuration on a switch.

**Version Control*

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Set verbose debug via brcdapi.brcdapi_rest.verbose_debug()                            |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 06 Dec 2024   | Fixed spelling mistake in message.                                                    |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2023, 2024 Consoli Solutions, LLC'
__date__ = '06 Dec 2024'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack@consoli-solutions.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.2'

import argparse
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as brcdapi_auth
import brcdapi.log as brcdapi_log
import brcdapi.gen_util as gen_util
import brcdapi.zone as brcdapi_zone
import brcdapi.file as brcdapi_file
import brcdapi.util as brcdapi_util
import brcdapi.excel_util as excel_util

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation
# _STAND_ALONE: True: Executes as a standalone module taking input from the command line. False: Does not automatically
# execute. This is useful when importing this module into another module that calls psuedo_main().
_STAND_ALONE = True  # See note above

# debug input (for copy and paste into Run->Edit Configurations->script parameters):
# -ip 10.144.72.15 -id admin -pw AdminPassw0rd! -s self -fid 0 -z test_zonecfg -log _logs

_input_d = gen_util.parseargs_login_d.copy()
_input_d.update(
    fid=dict(t='int', v=gen_util.range_to_list('1-128'), h='Required. Fabric ID of logical switch'),
    z=dict(h='Zone configuration to activate.'),
)
_input_d.update(gen_util.parseargs_log_d.copy())
_input_d.update(gen_util.parseargs_debug_d.copy())


def _logout(session):
    """Logout and post message if the logout failed

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    """
    brcdapi_log.log('Logging out', echo=True)
    obj = brcdapi_rest.logout(session)
    if brcdapi_auth.is_error(obj):
        brcdapi_log.log('Logout failed:\n' + brcdapi_auth.formatted_error_msg(obj), echo=True)


def pseudo_main(user_id, pw, ip, sec, fid, zone_cfg):
    """Basically the main().

    :param user_id: User ID
    :type user_id: str
    :param pw: Password
    :type pw: str
    :param ip: IP address
    :type ip: str
    :param sec: Security. 'none' for HTTP, 'self' for self-signed certificate, 'CA' for signed certificate
    :type sec: str
    :param fid: Fabric ID
    :type fid: int, str
    :param zone_cfg: Name of zone configuration to activate
    :type zone_cfg: str
    :return: Exit code
    :rtype: int
    """
    ec = 0

    # Login
    brcdapi_log.log('Attempting login', echo=True)
    session = brcdapi_rest.login(user_id, pw, ip, sec)
    if brcdapi_auth.is_error(session):
        brcdapi_log.log(['Login failed', brcdapi_auth.formatted_error_msg(session)], echo=True)
        return -1
    brcdapi_log.log('Login succeeded', echo=True)

    # A check sum is needed to save any updates
    checksum, obj = brcdapi_zone.checksum(session, fid, echo=True)
    if checksum is None:
        brcdapi_log.log('Could not get a valid checksum', echo=True)
        _logout(session)
        ec = -1

    else:
        try:
            brcdapi_log.log('Enabling zone configuration ' + zone_cfg + ', fid: ' + str(fid), echo=True)
            obj = brcdapi_zone.enable_zonecfg(session, checksum, fid, zone_cfg, True)
            if brcdapi_auth.is_error(obj):
                # brcdapi_zone.enable_zonecfg() already printed the error messages so just abort the transaction
                brcdapi_zone.abort(session, fid, True)
                ec = -1

        except brcdapi_util.VirtualFabricIdError:
            brcdapi_log.log('Software error. Search the log for "Invalid FID" for details.', echo=True)
            ec = -1

        except BaseException as e:
            brcdapi_log.exception(['Programming error encountered.', 'Exception: (' + str(type(e)) + ') ' + str(e)],
                                  echo=True)
            ec = -1

    _logout(session)

    return ec


def _get_input():
    """Retrieves the command line input, reads the input Workbook, and validates the input

    :return ec: Error code. 0 - OK. Anything else is an error
    :rtype ec: int
    """
    global __version__, _input_d

    ec, args_s_append = 0, ''

    # Get command line input
    try:
        args_d = gen_util.get_input('Activates an existing zone configuration on a switch', _input_d)
    except TypeError:
        return -1  # gen_util.get_input() already posted the error message.

    # Set up logging
    if args_d['d']:
        brcdapi_rest.verbose_debug(True)
    brcdapi_log.open_log(folder=args_d['log'], suppress=args_d['sup'], no_log=args_d['nl'])

    # Command line feedback
    ml = [
        'zonecfg_enable.py version: ' + __version__,
        'IP, -ip:                   ' + brcdapi_util.mask_ip_addr(args_d['ip'], keep_last=True),
        'ID, -id:                   ' + args_d['id'],
        'Security, -s:              ' + args_d['s'],
        'Zone configuration, -z:    ' + str(args_d['z']),
        'Log, -log:                 ' + str(args_d['log']),
        'No log, -nl:               ' + str(args_d['nl']),
        'Debug, -d:                 ' + str(args_d['d']),
        'Suppress, -sup:            ' + str(args_d['sup']),
        '',
        ]
    brcdapi_log.log(ml, echo=True)

    return ec if ec != 0 else pseudo_main(args_id, args_pw, args_ip, args_s, args_fid, args_z)


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
