#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2020, 2021, 2022, 2023 Jack Consoli.  All rights reserved.
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
:mod:`switch_delete.py` - Examples on how to delete a logical switch.

Scroll all the way to the bottom to find the entry point.

**WARNING**

    This module was written to provide programming examples. It does not have a full user interface or robust error
    checking. It has not undergone the type of rigorous testing that a supported product would undergo.

**Description**

    Example on how to delete logical switches. It also includes an example on how to read the logical switch information
    from a chassis and filter out the default switch.

    Although GE ports can be deleted, at this time there isn't an example of how to tear down the circuits and tunnels.
    Tearing down the circuits and tunnels is required before the ports can be moved to another logical switch.

    Switch delete notes (this is all checked and taken care of in brcdapi.switch.delete_switch():

    * You cannot delete the default logical switch.
    * All ports in the switch being deleted must be moved to another logical switch before deleting the swithc
    * Ports must be at there factory default configuration before they can be moved.

**Example**

To delete the logical switch whose FID is 20:

py switch_delete.py -ip xx.x.xxx.10 -id admin -pw password -s self -echo -fid 20

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 3.0.0     | 27 Nov 2020   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.1     | 09 Jan 2021   | Open log file.                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.2     | 13 Feb 2021   | Added # -*- coding: utf-8 -*-                                                     |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.3     | 14 Nov 2021   | Deprecated pyfos_auth                                                             |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.4     | 01 Jan 2023   | Added ability to delete all non-default or a range of FIDs.                       |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2020, 2021, 2022, 2023 Jack Consoli'
__date__ = '01 Jan 2023'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.4'

import argparse
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as fos_auth
import brcdapi.log as brcdapi_log
import brcdapi.gen_util as gen_util
import brcdapi.util as brcdapi_util
import brcdapi.switch as brcdapi_switch

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation
_DEBUG = False   # When True, use _DEBUG_ip, _DEBUG_id, _DEBUG_pw, _DEBUG_OUTF, and _DEBUG_d
_DEBUG_ip = 'xx.xxx.xx.xx'
_DEBUG_id = 'admin'
_DEBUG_pw = 'password'
_DEBUG_s = 'self'  # Use None or 'none' for HTTP. Use the certificate if HTTPS and not self signed
_DEBUG_fid = '*'
_DEBUG_echo = True  # When true, echoes details of ports being moved.
_DEBUG_d = False  # When True, all content and responses are formatted and printed (pprint).
_DEBUG_sup = False  # This is a global override to suppress all logging echo to STD_OUT
_DEBUG_log = '_logs'
_DEBUG_nl = False


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


def _get_input():
    """Parses the module load command line

    :return ip: Switch IP address
    :rtype ip: str
    :return id: User ID
    :rtype id: str
    :return pw: User password
    :rtype ip: str
    :return sec: Secure method. None for HTTP, otherwise the certificate or 'self' if self signed
    :rtype sec: str, None
    :return fids: FID(s) to delete
    :rtype fids: str
    :return vd: Verbose debug flag.
    :rtype vd: bool
    """
    global _DEBUG_ip, _DEBUG_id, _DEBUG_pw, _DEBUG_s, _DEBUG_fid, _DEBUG_echo, _DEBUG_d, _DEBUG_log, _DEBUG_nl
    global _DEBUG_sup

    if _DEBUG:
        args_ip, args_id, args_pw, args_s, args_fid, args_echo, args_d, args_sup, args_log, args_nl = \
            _DEBUG_ip, _DEBUG_id, _DEBUG_pw, _DEBUG_s, _DEBUG_fid, _DEBUG_echo, _DEBUG_d, _DEBUG_sup, _DEBUG_log, \
            _DEBUG_nl
    else:
        parser = argparse.ArgumentParser(description='Delete a logical switch.')
        parser.add_argument('-ip', help='(Required) IP address', required=True)
        parser.add_argument('-id', help='(Required) User ID', required=True)
        parser.add_argument('-pw', help='(Required) Password', required=True)
        buf = '(Required) Virtual Fabric ID to delete. May be a range, a CSV list, or "*" for all non-default switches.'
        parser.add_argument('-fid', help=buf, required=True)
        parser.add_argument('-s', help="(Optional) Default is HTTP. CA or self for HTTPS mode.", required=False)
        buf = '(Optional) Echoes activity detail to STD_OUT. Recommended because there are multiple operations that '\
              'can be very time consuming.'
        parser.add_argument('-echo', help=buf, action='store_true', required=False)
        buf = '(Optional) Enable debug logging. Prints the formatted data structures (pprint) to the log and console.'
        buf = '(Optional) Suppress all library generated output to STD_IO except the exit code. Useful with batch ' \
              'processing'
        parser.add_argument('-sup', help=buf, action='store_true', required=False)
        parser.add_argument('-d', help=buf, action='store_true', required=False)
        buf = '(Optional) Directory where log file is to be created. Default is to use the current directory. The log '\
              'file name will always be "Log_xxxx" where xxxx is a time and date stamp.'
        parser.add_argument('-log', help=buf, required=False, )
        buf = '(Optional) No parameters. When set, a log file is not created. The default is to create a log file.'
        parser.add_argument('-nl', help=buf, action='store_true', required=False)
        args = parser.parse_args()

        args_ip, args_id, args_pw, args_s, args_fid, args_echo, args_d, args_sup, args_log, args_nl = \
            args.ip, args.id, args.pw, args.s, args.fid, args.echo, args.d, args.sup, args.log, args.nl

    # Set up the logging options
    if args_sup:
        brcdapi_log.set_suppress_all()
    if not args_nl:
        brcdapi_log.open_log(args_log)
    if args_d:
        brcdapi_rest.verbose_debug = True

    # User feedback
    ml = ['switch_delete.py:    ' + __version__,
          'IP, -ip:             ' + brcdapi_util.mask_ip_addr(args_ip, keep_last=True),
          'FID, -fid:           ' + args_fid,
          'Echo, -echo:         ' + str(args_echo),
          'Debug, -d:           ' + str(args_d)]
    if _DEBUG:
        ml.insert(0, 'WARNING!!! Debug is enabled')
    brcdapi_log.log(ml, echo=True)

    return args_ip, args_id, args_pw, args_s, args_fid, args_echo


def pseudo_main():
    """Basically the main().

    :return: Exit code
    :rtype: int
    """
    ec = 0

    # Get and condition the command line input
    ip, user_id, pw, sec, fid, echo = _get_input()

    # Login
    brcdapi_log.log('Attempting login', echo=True)
    session = brcdapi_rest.login(user_id, pw, ip, sec)
    if fos_auth.is_error(session):
        brcdapi_log.log(['Login failed. API error message is:', fos_auth.formatted_error_msg(session)], echo=True)
        return -1
    brcdapi_log.log('Login succeeded.', echo=True)

    # Delete the logical switch(es)
    try:  # I always do a try in code development so that if there is a code bug, I still log out.
        for fid in _get_fid_list(session) if '*' in fid else gen_util.range_to_list(fid):
            buf = 'Deleting FID ' + str(fid) + '. This will take about 20 sec + 25 sec per group of 32 ports.'
            brcdapi_log.log(buf, echo=True)
            obj = brcdapi_switch.delete_switch(session, fid, echo)
            if fos_auth.is_error(obj):
                brcdapi_log.log(['Error deleting FID ' + str(fid), fos_auth.formatted_error_msg(obj)], echo=True)
                ec = -1

    except BaseException as e:  # To ensure the logout is executed no matter what went wrong
        brcdapi_log.log('Encountered a programming error', echo=True)
        ec = -1

    # Logout
    obj = brcdapi_rest.logout(session)
    if fos_auth.is_error(obj):
        brcdapi_log.log(['Logout failed. API error message is:',  fos_auth.formatted_error_msg(obj)], echo=True)

    return ec

###################################################################
#
#                    Main Entry Point
#
###################################################################


_ec = 0
if _DOC_STRING:
    print('_DOC_STRING is True. No processing')
else:
    _ec = pseudo_main()
    brcdapi_log.close_log('Processing complete. Exit status: ' + str(_ec), echo=True)
exit(_ec)
