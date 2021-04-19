#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2019, 2020, 2021 Jack Consoli.  All rights reserved.
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
:mod:`maps_clear.py` - Clear the MAPS dashboard

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 3.0.0     | 14 Nov 2020   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.1-3   | 17 Apr 2021   | Miscellaneous bug fixes                                                           |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2020, 2021 Jack Consoli'
__date__ = '17 Apr 2021'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.3'

import argparse
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.pyfos_auth as pyfos_auth
import brcdapi.log as brcdapi_log

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation
_DEBUG = False   # When True, use _DEBUG_IP, _DEBUG_ID, _DEBUG_PW, _DEBUG_OUTF, and _DEBUG_VERBOSE
_DEBUG_IP = 'xx.x.xxx.xx'
_DEBUG_ID = 'admin'
_DEBUG_PW = 'password'
_DEBUG_SEC = 'self'  # Use None or 'none' for HTTP. Use the certificate if HTTPS and not self signed
_DEBUG_FID = '128'
_DEBUG_VERBOSE = True  # When True, all content and responses are formatted and printed (pprint).
_DEBUG_LOG = '_logs'
_DEBUG_NL = False


def parse_args():
    """Parses the module load command line

    :return ip: IP address
    :rtype ip: str
    :return id: User ID
    :rtype id: str
    :return pw: Password
    :rtype pw: str
    :return s: Type of HTTP security. None if not specified
    :rtype s: str, None
    :return fid: Fabric ID
    :rtype fid: int
    :return d: True - enable log debug
    :rtype d: bool
    """
    global _DEBUG_IP, _DEBUG_ID, _DEBUG_PW, _DEBUG_SEC, _DEBUG_FID, _DEBUG_VERBOSE, _DEBUG_LOG, _DEBUG_NL

    if _DEBUG:
        return _DEBUG_IP, _DEBUG_ID, _DEBUG_PW, _DEBUG_SEC, _DEBUG_FID, _DEBUG_VERBOSE, _DEBUG_LOG, _DEBUG_NL
    else:
        buf = 'Clears the MAPS dashboard.'
        parser = argparse.ArgumentParser(description=buf)
        parser.add_argument('-ip', help='IP address', required=True)
        parser.add_argument('-id', help='User ID', required=True)
        parser.add_argument('-pw', help='Password', required=True)
        parser.add_argument('-s', help='\'CA\' or \'self\' for HTTPS mode.', required=False,)
        parser.add_argument('-fid', help='FID number', required=True,)
        buf = 'Enable debug logging. Prints the formatted data structures (pprint) to the log and console.'
        parser.add_argument('-d', help=buf, action='store_true', required=False)
        buf = '(Optional) Directory where log file is to be created. Default is to use the current directory. The log ' \
              'file name will always be "Log_xxxx" where xxxx is a time and date stamp.'
        parser.add_argument('-log', help=buf, required=False, )
        buf = '(Optional) No parameters. When set, a log file is not created. The default is to create a log file.'
        parser.add_argument('-nl', help=buf, action='store_true', required=False)
        args = parser.parse_args()
        return args.ip, args.id, args.pw, args.s, args.fid, args.d, args.log, args.nl


def _clear_dashboard(session, fid):
    """Clears the MAPS dashboard

    :return fid: Fabric ID
    :rtype fid: int
    """
    content = {'clear-data': True}
    obj = brcdapi_rest.send_request(session, 'brocade-maps/dashboard-misc', 'PUT', content, fid)
    if pyfos_auth.is_error(obj):
        brcdapi_log.log(pyfos_auth.formatted_error_msg(obj), True)
        return -1
    return 0


def pseudo_main():
    """Basically the main().

    :return: Exit code
    :rtype: int
    """
    ml = ['WARNING!!! Debug is enabled'] if _DEBUG else list()
    ip, user_id, pw, sec, fids, vd, log, nl = parse_args()
    if vd:
        brcdapi_rest.verbose_debug = True
    if not nl:
        brcdapi_log.open_log(log)
    fid = int(fids)
    ml.append('FID: ' + fids)
    if sec is None:
        sec = 'none'
    brcdapi_log.log(ml, True)

    # Login
    brcdapi_log.log('Attempting login', True)
    session = brcdapi_rest.login(user_id, pw, ip, sec)
    if pyfos_auth.is_error(session):
        brcdapi_log.log('Login failed', True)
        brcdapi_log.log(pyfos_auth.formatted_error_msg(session), True)
        return -1
    brcdapi_log.log('Login succeeded', True)

    # try/except used during development to ensure logout due to programming errors.
    try:
        ec = _clear_dashboard(session, fid)
    except:
        brcdapi_log.exception('Encountered a programming error', True)
        ec = -1

    obj = brcdapi_rest.logout(session)
    if pyfos_auth.is_error(obj):
        brcdapi_log.log('Logout failed:\n' + pyfos_auth.formatted_error_msg(obj), True)
    return ec

###################################################################
#
#                    Main Entry Point
#
###################################################################


if not _DOC_STRING:
    brcdapi_log.close_log('Processing Complete. Exit code: ' + str(pseudo_main()), True)
