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
:mod:`stats_clear.py` - Clears all port statistics for all ports in a FID on a chassis.

**Description**

    Example on how to:

    * Determine all FC ports in a logical switch
    * Determine all GE ports in a logical switch
    * Clear all port statistics for both FC and GE ports

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 1.0.0     | 13 Feb 2021   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2021 Jack Consoli'
__date__ = '13 Feb 2021'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '1.0.0'

import argparse
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.pyfos_auth as pyfos_auth
import brcdapi.log as brcdapi_log
import brcdapi.port as brcdapi_port

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation
_DEBUG = False   # When True, use _DEBUG_xxx below instead of parameters passed from the command line.
_DEBUG_IP = '10.8.105.10'
_DEBUG_ID = 'admin'
_DEBUG_PW = 'password'
_DEBUG_SEC = 'self'  # Use None or 'none' for HTTP. Use the certificate if HTTPS and not self signed
_DEBUG_FID = '128'
_DEBUG_VERBOSE = False  # When True, all content and responses are formatted and printed (pprint).
_DEBUG_LOG = '_logs'
_DEBUG_NL = False


def get_ge_port_list(session, fid):
    """Returns the list of GE ports in a logical switch

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical switch FID number
    :type fid: int
    :return: List of GE ports
    :rtype: list
    """
    obj = brcdapi_rest.get_request(
        session, 'brocade-fibrechannel-logical-switch/fibrechannel-logical-switch/fabric-id/' + str(fid))
    if pyfos_auth.is_error(obj):
        brcdapi_log.log(pyfos_auth.formatted_error_msg(obj), True)
        return list()
    if 'fibrechannel-logical-switch' in obj and 'ge-port-member-list' in obj['fibrechannel-logical-switch']:
        pl = obj['fibrechannel-logical-switch']['ge-port-member-list'].get('port-member')
        return list() if pl is None else pl
    return list()


def parse_args():
    """Parses the module load command line

    :return ip: Switch IP address
    :rtype ip: str
    :return id: User ID
    :rtype id: str
    :return pw: User password
    :rtype ip: str
    :return sec: Secure method. None for HTTP, otherwise the certificate or 'self' if self signed
    :rtype sec: str, None
    :return fids: FID whose ports are to be enabled.
    :rtype fids: str
    :return vd: Verbose debug flag.
    :rtype vd: bool
    :return log: Name of log file
    :rtype log: str, None
    :return nl: No log flag. When true, logging is disabled.
    :rtype nl: bool
    """
    global _DEBUG_IP, _DEBUG_ID, _DEBUG_PW, _DEBUG_SEC, _DEBUG_FID, _DEBUG_VERBOSE, _DEBUG_LOG, _DEBUG_NL

    if _DEBUG:
        return _DEBUG_IP, _DEBUG_ID, _DEBUG_PW, _DEBUG_SEC, _DEBUG_FID, _DEBUG_VERBOSE, _DEBUG_LOG, _DEBUG_NL
    else:
        parser = argparse.ArgumentParser(description='Clear statistics for all ports in a logical switch.')
        parser.add_argument('-ip', help='(Required) IP address', required=True)
        parser.add_argument('-id', help='(Required) User ID', required=True)
        parser.add_argument('-pw', help='(Required) Password', required=True)
        parser.add_argument('-s', help="(Optional) Default is HTTP. CA or self for HTTPS mode.", required=False)
        parser.add_argument('-fid', help='(Required) Virtual Fabric ID.', required=True)
        buf = '(Optional) Enable debug logging. Prints the formatted data structures (pprint) to the log and console.'
        parser.add_argument('-d', help=buf, action='store_true', required=False)
        buf = '(Optional) Directory where log file is to be created. Default is to use the current directory. The log ' \
              'file name will always be "Log_xxxx" where xxxx is a time and date stamp.'
        parser.add_argument('-log', help=buf, required=False, )
        buf = '(Optional) No parameters. When set, a log file is not created. The default is to create a log file.'
        parser.add_argument('-nl', help=buf, action='store_true', required=False)
        args = parser.parse_args()
        return args.ip, args.id, args.pw, args.s, args.fid, args.d, args.log, args.nl


def pseudo_main():
    """Basically the main().

    :return: Exit code
    :rtype: int
    """
    global _DEBUG

    # Get and validate command line input
    ml = ['WARNING!!! Debug is enabled'] if _DEBUG else list()
    ip, user_id, pw, sec, fid_str, vd, log, nl = parse_args()
    if not nl:
        brcdapi_log.open_log(log)
    if vd:
        brcdapi_rest.verbose_debug = True
    if fid_str.isdigit():
        fid = int(fid_str)
    else:
        brcdapi_log.log('Invalid FID: ' + fid_str, True)
        return -1
    brcdapi_log.log(ml, True)

    # Login
    brcdapi_log.log('Attempting login', True)
    session = brcdapi_rest.login(user_id, pw, ip, sec)
    if pyfos_auth.is_error(session):
        brcdapi_log.log('Login failed', True)
        brcdapi_log.log(pyfos_auth.formatted_error_msg(session), True)
        return -1
    brcdapi_log.log('Login succeeded', True)

    ec = 0
    try:  # I always do a try in code development so that if there is a code bug, I still log out.

        # Get FC port list for this FID by reading the configurations
        kpi = 'brocade-interface/fibrechannel'
        obj = brcdapi_rest.get_request(session, kpi, fid)
        if pyfos_auth.is_error(obj):
            brcdapi_log.log('Failed to read ' + kpi + ' for fid ' + str(fid), True)
            ec = -1

        else:
            # Get the port lists
            fc_plist = [port.get('name') for port in obj.get('fibrechannel')]
            ge_plist = get_ge_port_list(session, fid)

            # Clear stats for all FC and GE ports
            brcdapi_log.log('Clearing statistics for all ports of fid: ' + str(fid), True)
            obj = brcdapi_port.clear_stats(session, fid, fc_plist, ge_plist)
            if pyfos_auth.is_error(obj):
                brcdapi_log.log('Error clearing stats for ports for FID ' + str(fid), True)
                brcdapi_log.log(pyfos_auth.formatted_error_msg(obj), True)
                ec = -1
            else:
                brcdapi_log.log('Successfully cleared stats for all ports for FID ' + str(fid), True)

    except:
        brcdapi_log.log('Encountered a programming error', True)
        ec = -1

    # Logout
    obj = brcdapi_rest.logout(session)
    if pyfos_auth.is_error(obj):
        brcdapi_log.log('Logout failed:\n' + pyfos_auth.formatted_error_msg(obj), True)
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
    brcdapi_log.close_log('Processing complete. Exit status: ' + str(_ec), True)
exit(_ec)
