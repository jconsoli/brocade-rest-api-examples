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
redistribution, or service delivery for commerce requires an additional license. Contact jack_consoli@yahoo.com for
details.

:mod:`maps_clear.py` - Clear the MAPS dashboard

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
| 4.0.3     | 19 Oct 2025   | Updated comments only.                                                                |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2024, 2025 Consoli Solutions, LLC'
__date__ = '19 Oct 2025'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.3'

import argparse
import brcdapi.util as brcdapi_util
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as brcdapi_auth
import brcdapi.log as brcdapi_log

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation
# When _DEBUG is True, use _DEBUG_xxx below instead of parameters passed from the command line. I did it this way,
# rather than rely on parameter passing with IDE tools because the API examples are typically used as programming
# examples, not stand-alone scripts. It's easier to modify the inputs this way.
_DEBUG = False
_DEBUG_ip = 'xx.xxx.x.69'
_DEBUG_id = 'admin'
_DEBUG_pw = 'password'
_DEBUG_s = None  # HTTPS is the default. Use 'none' for HTTP.
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
        args_ip, args_id, args_pw, args_s, args_fid, args_d, args_log, args_nl =\
            _DEBUG_IP, _DEBUG_ID, _DEBUG_PW, _DEBUG_SEC, _DEBUG_FID, _DEBUG_VERBOSE, _DEBUG_LOG, _DEBUG_NL
    else:
        buf = 'Clears the MAPS dashboard.'
        parser = argparse.ArgumentParser(description=buf)
        parser.add_argument('-ip', help='IP address', required=True)
        parser.add_argument('-id', help='User ID', required=True)
        parser.add_argument('-pw', help='Password', required=True)
        parser.add_argument('-s', help='Optional. "none" for HTTP. The default is "self" for HTTPS mode.',
                            required=False,)
        parser.add_argument('-fid', help='FID number', required=True,)
        buf = 'Enable debug logging. Prints the formatted data structures (pprint) to the log and console.'
        parser.add_argument('-d', help=buf, action='store_true', required=False)
        buf = '(Optional) Directory where log file is to be created. Default is to use the current directory. The ' \
              'log file name will always be "Log_xxxx" where xxxx is a time and date stamp.'
        parser.add_argument('-log', help=buf, required=False, )
        buf = '(Optional) No parameters. When set, a log file is not created. The default is to create a log file.'
        parser.add_argument('-nl', help=buf, action='store_true', required=False)
        args = parser.parse_args()
        args_ip, args_id, args_pw, args_s, args_fid, args_d, args_log, args_nl =\
            args.ip, args.id, args.pw, args.s, args.fid, args.d, args.log, args.nl

    # Default security
    if args_s is None:
        args_s = 'self'

    return args_ip, args_id, args_pw, args_s, args_fid, args_d, args_log, args_nl


def _clear_dashboard(session, fid):
    """Clears the MAPS dashboard

    :return fid: Fabric ID
    :rtype fid: int
    """
    content = {'clear-data': True}
    obj = brcdapi_rest.send_request(session, 'running/brocade-maps/dashboard-misc', 'PUT', content, fid)
    if brcdapi_auth.is_error(obj):
        brcdapi_log.log(brcdapi_auth.formatted_error_msg(obj), echo=True)
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
        brcdapi_rest.verbose_debug(True)
    brcdapi_log.open_log(folder=args_log, suppress=False, version_d=brcdapi_util.get_import_modules(), no_log=args_nl)
    fid = int(fids)

    ml.append('FID: ' + fids)
    if sec is None:
        sec = 'none'
    brcdapi_log.log(ml, echo=True)

    # Login
    brcdapi_log.log('Attempting login', True)
    session = brcdapi_rest.login(user_id, pw, ip, sec)
    if brcdapi_auth.is_error(session):
        brcdapi_log.log('Login failed', True)
        brcdapi_log.log(brcdapi_auth.formatted_error_msg(session), echo=True)
        return -1
    brcdapi_log.log('Login succeeded', True)

    try:
        ec = _clear_dashboard(session, fid)
    except brcdapi_util.VirtualFabricIdError:
        brcdapi_log.log('Software error. Search the log for "Invalid FID" for details.', echo=True)
        ec = -1
    except BaseException as e:
        brcdapi_log.exception(['Programming error encountered.', str(type(e)) + ': ' + str(e)], echo=True)
        ec = -1

    obj = brcdapi_rest.logout(session)
    if brcdapi_auth.is_error(obj):
        brcdapi_log.log(['Logout failed:', brcdapi_auth.formatted_error_msg(obj)], echo=True)
        ec = -1

    return ec


###################################################################
#
#                    Main Entry Point
#
###################################################################
if _DOC_STRING:
    print('_DOC_STRING is True. No processing')
    exit(0)

_ec = pseudo_main()
brcdapi_log.close_log(str(_ec))
exit(_ec)
