#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2023 Consoli Solutions, LLC.  All rights reserved.
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
:mod:`zone_config.py` - Simple zone configuration activation example.

**Description**

    Activates an existing zone configuration on a switch.

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 4.0.0     | 04 Aug 2023   | Re-Launch                                                                         |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""

__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2023 Consoli Solutions, LLC'
__date__ = '04 August 2023'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.0'

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
_DEBUG = False
_DEBUG_ip = 'xx.xxx.xx.xx'
_DEBUG_id = 'admin'
_DEBUG_pw = 'password!'  # 'password'
_DEBUG_s = 'self'
_DEBUG_z = 'good_zonecfg'
_DEBUG_fid = 1
_DEBUG_sup = False
_DEBUG_d = False
_DEBUG_log = '_logs'
_DEBUG_nl = False


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
    :param sec: Security. 'none' for HTTP, 'self' for self signed certificate, 'CA' for signed certificate
    :type sec: str
    :param fid: Fabric ID
    :type fid: int, str
    :param zone_cfg: Name of zone configuration to activate
    :type zone_cfg: str
    :return: Exit code
    :rtype: int
    """
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
        return -1

    # try/except was so that during development a bug would not cause an abort and skip the logout
    try:
        brcdapi_log.log('Enabling zone configuration ' + zone_cfg + ', fid: ' + str(fid), echo=True)
        obj = brcdapi_zone.enable_zonecfg(session, checksum, fid, zone_cfg, True)
        if brcdapi_auth.is_error(obj):
            # Commented out code below is redundant because brcdapi.zone methods print formatted error messages to
            # the log. Should you need to format error objects into human readable text:
            # brcdapi_log.log(brcdapi_auth.formatted_error_msg(obj), True)
            brcdapi_zone.abort(session, fid, True)
            _logout(session)
            return -1

    except BaseException as e:
        brcdapi_log.log(['', 'Software error.', 'Exception: ' + str(e)], echo=True)
        brcdapi_log.log('Logging out', True)
        _logout(session)
        brcdapi_log.exception('Exception', True)
        return -1

    _logout(session)
    return 0


def _get_input():
    """Retrieves the command line input, reads the input Workbook, and validates the input

    :return ec: Error code. 0 - OK. Anything else is an error
    :rtype ec: int
    """
    global __version__, _DEBUG, _DEBUG_ip, _DEBUG_id, _DEBUG_pw, _DEBUG_s, _DEBUG_z, _DEBUG_fid, _DEBUG_d, _DEBUG_sup
    global _DEBUG_log, _DEBUG_nl

    ec, args_s_append = 0, ''

    # Get shell input
    if _DEBUG:
        args_ip, args_id, args_pw, args_s, args_z, args_fid, args_d, args_sup, args_log, args_nl = \
            _DEBUG_ip, _DEBUG_id, _DEBUG_pw, _DEBUG_s, _DEBUG_z, _DEBUG_fid, _DEBUG_d, _DEBUG_sup, _DEBUG_log, _DEBUG_nl
    else:
        buf = 'Activates an existing zone configuration on a switch'
        parser = argparse.ArgumentParser(description=buf)
        parser.add_argument('-ip', help='IP address', required=True)
        parser.add_argument('-id', help='User ID', required=True)
        parser.add_argument('-pw', help='Password', required=True)
        parser.add_argument('-s', help='(Optional) "none" for HTTP, default, or "self" for HTTPS mode.',
                            required=False)
        parser.add_argument('-fid', help='Fabric ID of logical switch', required=True)
        parser.add_argument('-z', help='Zone configuration to activate.', required=True)
        buf = 'Optional. Suppress all output to STD_IO except the exit code and argument parsing errors. Useful with ' \
              'batch processing where only the exit status code is desired. Messages are still printed to the log ' \
              'file. No operands.'
        parser.add_argument('-sup', help=buf, action='store_true', required=False)
        buf = '(Optional) No parameters. When set, a pprint of all content sent and received to/from the API, except ' \
              'login information, is printed to the log.'
        parser.add_argument('-d', help=buf, action='store_true', required=False)
        buf = '(Optional) Directory where log file is to be created. Default is to use the current directory. The ' \
              'log file name will always be "Log_xxxx" where xxxx is a time and date stamp.'
        parser.add_argument('-log', help=buf, required=False, )
        buf = '(Optional) No parameters. When set, a log file is not created. The default is to create a log file.'
        parser.add_argument('-nl', help=buf, action='store_true', required=False)
        args = parser.parse_args()
        args_ip, args_id, args_pw, args_s, args_z, args_fid, args_d, args_sup, args_log, args_nl = \
            args.ip, args.id, args.pw, args.s, args.z, args.fid, args.d,  args.sup, args.log, args.nl

    # Set up logging
    if args_d:
        brcdapi_rest.verbose_debug = True
    if args_sup:
        brcdapi_log.set_suppress_all()
    if not args_nl:
        brcdapi_log.open_log(args_log)

    # Is the security method valid?
    if args_s is None:
        args_s = 'none'
    elif args_s != 'self' and args_s != 'none':
        ec, args_s_append = -1, ' *ERROR: Unsupported HTTP method'

    # User feedback
    ml = [
        'chassis_restore.py version: ' + __version__,
        'IP address, -ip:         ' + brcdapi_util.mask_ip_addr(args_ip),
        'ID, -id:                 ' + str(args_id),
        'HTTPS, -s:               ' + str(args_s) + args_s_append,
        'Zone configuration, -z:  ' + str(args_z),
        ]
    if _DEBUG:
        ml.insert(0, 'WARNING!!! Debug is enabled')
    brcdapi_log.log(ml, echo=True)

    return ec if ec != 0 else pseudo_main(args_id, args_pw, args_ip, args_s, args_fid, args_z)


###################################################################
#
#                    Main Entry Point
#
###################################################################
if not _DOC_STRING:
    _ec = _get_input()
    brcdapi_log.close_log(str(_ec), echo=True)
exit(0)
