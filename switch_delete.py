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

Scroll all the way to the bottom to find the entry point.

**WARNING**

    This module was written to provide programming examples. It does not have a full user interface or robust error
    checking. It has not undergone the type of rigorous testing that a supported product would undergo.

**Description**

    Example on how to delete logical switches. It also includes an example on how to read the logical switch information
    from a chassis and filter out the default switch.

    Although GE ports can be deleted, at this time there isn't an example of how to tear down the circuits and tunnels.
    Tearing down the circuits and tunnels is required before the ports can be moved to another logical switch.

    Switch delete notes: this is all checked and taken care of in brcdapi.switch.delete_switch():

    * You cannot delete the default logical switch.
    * All ports in the switch being deleted must be moved to another logical switch before deleting the switch
    * Ports must be at there factory default configuration before they can be moved.

**Example**

To delete the logical switch whose FID is 20:

py switch_delete.py -ip xx.x.xxx.10 -id admin -pw password -s self -fid 20

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Increased estimated port group time from 25 sec to 40 sec.                            |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 06 Dec 2024   | Fixed spelling mistake in message.                                                    |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.3     | 25 Aug 2025   | Use brcdapi_util.get_import_modules() when opening log.                               |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2023, 2024, 2025 Consoli Solutions, LLC'
__date__ = '25 Aug 2025'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.3'

import argparse
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as fos_auth
import brcdapi.log as brcdapi_log
import brcdapi.gen_util as gen_util
import brcdapi.util as brcdapi_util
import brcdapi.switch as brcdapi_switch

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation
# _STAND_ALONE: True: Executes as a standalone module taking input from the command line. False: Does not automatically
# execute. This is useful when importing this module into another module that calls psuedo_main().
_STAND_ALONE = True  # See note above

# Input parameter definitions
_input_d = gen_util.parseargs_login_d.copy()
_input_d.update(
    fid=dict(h='Required. Virtual Fabric ID to delete. May be a range, a CSV list, or "*" for all non-default '
               'switches.'),
)
_input_d.update(gen_util.parseargs_log_d.copy())
_input_d.update(gen_util.parseargs_debug_d.copy())


def _get_fid_list(session):
    """Returns a list of non-default switch fabric IDs

    :param session: Session object returned from brcdapi.fos_auth.login()
    :type session: dict
    :return: List of FIDs as integers
    :rtype: list
    """
    # Get the chassis information
    obj = brcdapi_rest.get_request(session,
                                   'running/brocade-fibrechannel-logical-switch/fibrechannel-logical-switch',
                                   None)
    if fos_auth.is_error(obj):
        brcdapi_log.log(fos_auth.formatted_error_msg(obj), echo=True)
    else:  # All FID numbers except the default switch.
        return [d['fabric-id'] for d in obj['fibrechannel-logical-switch'] if d['default-switch-status'] != 1]

    return list()


def pseudo_main(ip, user_id, pw, sec, fid_l):
    """Basically the main().

    :param ip: Switch IP address
    :type ip: str
    :param user_id: User ID
    :type user_id: str
    :param pw: User password
    :type ip: str
    :param sec: Secure method. None for HTTP, otherwise the certificate or 'self' if self-signed
    :type sec: str, None
    :param fid_l: FID(s) to delete
    :type fid_l: list
    :return: Exit code
    :rtype: int
    """
    ec = 0

    # Login
    brcdapi_log.log('Attempting login', echo=True)
    session = brcdapi_rest.login(user_id, pw, ip, sec)
    if fos_auth.is_error(session):
        brcdapi_log.log(['Login failed. API error message is:', fos_auth.formatted_error_msg(session)], echo=True)
        return -1
    brcdapi_log.log('Login succeeded.', echo=True)

    # Delete the logical switch(es)
    try:  # I always do a try in code development so that if there is a code bug, I still log out.
        if len(fid_l) == 0:
            fid_l = _get_fid_list(session)
        for fid in fid_l:
            buf = ('Deleting FID ' + str(fid) + '. This will take about 20 sec per switch + 40 sec per group of 32 '
                                                'ports.')
            brcdapi_log.log(buf, echo=True)
            obj = brcdapi_switch.delete_switch(session, fid, echo=True)
            if fos_auth.is_error(obj):
                brcdapi_log.log(['Error deleting FID ' + str(fid), fos_auth.formatted_error_msg(obj)], echo=True)
                ec = -1

    except brcdapi_util.VirtualFabricIdError:
        brcdapi_log.log('Software error. Search the log for "Invalid FID" for details.', echo=True)
        ec = -1
    except BaseException as e:
        brcdapi_log.exception(['Programming error encountered.', str(type(e)) + ': ' + str(e)], echo=True)
        ec = -1

    # Logout
    obj = brcdapi_rest.logout(session)
    if fos_auth.is_error(obj):
        brcdapi_log.log(['Logout failed. API error message is:',  fos_auth.formatted_error_msg(obj)], echo=True)

    return ec


def _get_input():
    """Parses the module load command line

    :return: Exit code
    :rtype: int
    """
    global __version__, _input_d

    ec = 0

    # Get command line input
    args_d = gen_util.get_input('Delete logical switches.', _input_d)

    # Set up logging
    if args_d['d']:
        brcdapi_rest.verbose_debug(True)
    brcdapi_log.open_log(
        folder=args_d['log'],
        suppress=args_d['sup'],
        version_d=brcdapi_util.get_import_modules(),
        no_log=args_d['nl']
    )

    # Convert the FID range to a list
    args_fid_l, args_fid_help = list(), ''
    if args_d['fid'] != '*':
        args_fid_l = gen_util.range_to_list(args_d['fid'])
        args_fid_help = brcdapi_util.validate_fid(args_fid_l)
        if len(args_fid_help) > 0:
            args_fid_help = ' *ERROR: ' + args_fid_help
            ec = -1

    # Command line feedback
    ml = ['switch_delete.py:    ' + __version__,
          'IP, -ip:             ' + brcdapi_util.mask_ip_addr(args_d['ip'], keep_last=True),
          'ID, -id:             ' + args_d['id'],
          'Security, -s:        ' + args_d['s'],
          'FID, -fid:           ' + args_d['fid'] + args_fid_help,
          'Log, -log:           ' + str(args_d['log']),
          'No log, -nl:         ' + str(args_d['nl']),
          'Debug, -d:           ' + str(args_d['d']),
          'Suppress, -sup:      ' + str(args_d['sup']),
          '',]
    brcdapi_log.log(ml, echo=True)

    return ec if ec != 0 else \
        pseudo_main(args_d['ip'], args_d['id'], args_d['pw'], args_d['s'], args_fid_l)


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
