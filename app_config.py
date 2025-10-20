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

:mod:`app_config.py` - Examples on how to modify chassis configuration parameters.

**Description**

    Illustrates how to read and change parameters available in the
    "running/brocade-chassis/management-interface-configuration". Specifically:

    * Enable/disable the Rest interface
    * Enable/disable HTTPS
    * Enable/disable keep alive


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
import pprint
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as fos_auth
import brcdapi.log as brcdapi_log
import brcdapi.util as brcdapi_util

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation
# When _DEBUG is True, use _DEBUG_xxx below instead of parameters passed from the command line. I did it this way,
# rather than rely on parameter passing with IDE tools because the API examples are typically used as programming
# examples, not stand-alone scripts. It's easier to modify the inputs this way.
_DEBUG = False
_DEBUG_ip = 'xx.xxx.x.69'
_DEBUG_id = 'admin'
_DEBUG_pw = 'password'
_DEBUG_s = None  # HTTPS is the default. Use 'none' for HTTP.
_DEBUG_rest_en = False
_DEBUG_rest_dis = False
_DEBUG_https_en = False
_DEBUG_https_dis = False
_DEBUG_max_rest = None
_DEBUG_ka_en = True
_DEBUG_ka_dis = False
_DEBUG_d = False  # When True, all content and responses are formatted and printed (pprint).
_DEBUG_log = '_logs'
_DEBUG_nl = False


def _get_input():
    """Parses the module load command line

    :return ec: Error code. 0: OK, -1: Errors encountered
    :rtype ec: int
    :return ip: Switch IP address
    :rtype ip: str
    :return id: User ID
    :rtype id: str
    :return pw: User password
    :rtype ip: str
    :return sec: Secure method. None for HTTP, otherwise the certificate or 'self' if self-signed
    :rtype sec: str, None
    :return content: Content for "running/brocade-chassis/management-interface-configuration".
    :rtype content: dict
    """
    global _DEBUG_ip, _DEBUG_id, _DEBUG_pw, _DEBUG_s, _DEBUG_rest_en, _DEBUG_rest_dis
    global _DEBUG_https_en, _DEBUG_https_dis, _DEBUG_max_rest, _DEBUG_ka_en, _DEBUG_ka_en
    global _DEBUG_d, _DEBUG_log, _DEBUG_nl

    ec = 0

    if _DEBUG:
        args_ip, args_id, args_pw, args_s = _DEBUG_ip, _DEBUG_id, _DEBUG_pw, 'none' if _DEBUG_s is None else _DEBUG_s
        args_rest_en, args_rest_dis, args_https_en, args_https_dis = \
            _DEBUG_rest_en, _DEBUG_rest_dis, _DEBUG_https_en, _DEBUG_https_dis
        args_max_rest, args_ka_en, args_ka_dis = \
            _DEBUG_max_rest, _DEBUG_ka_en, _DEBUG_ka_dis
        args_d, args_log, args_nl = _DEBUG_d, _DEBUG_log, _DEBUG_nl
    else:
        buf = 'Useful as a programming example only on how to read and make chassis configuration changes via the '\
              '"running/brocade-chassis/management-interface-configuration" URI. If the only input is the login '\
              'credentials, the parameters are displayed and no other action taken.'
        parser = argparse.ArgumentParser(description=buf)
        parser.add_argument('-ip', help='(Required) IP address', required=True)
        parser.add_argument('-id', help='(Required) User ID', required=True)
        parser.add_argument('-pw', help='(Required) Password', required=True)
        parser.add_argument('-s', help='Optional. "none" for HTTP. The default is "self" for HTTPS mode.',
                            required=False)
        parser.add_argument('-rest_en', help='(Optional) No parameters. Enables the Rest interface',
                            action='store_true', required=False)
        parser.add_argument('-rest_dis', help='(Optional) No parameters. Disables the Rest interface',
                            action='store_true', required=False)
        parser.add_argument('-https_en', help='(Optional) No parameters. Enable HTTPS', action='store_true',
                            required=False)
        parser.add_argument('-https_dis', help='(Optional) No parameters. Disable HTTPS', action='store_true',
                            required=False)
        parser.add_argument('-max_rest',
                            help='(Optional) Set the maximum number of REST sessions. Valid options are 1-10',
                            required=False)
        parser.add_argument('-ka_en', help='(Optional) No parameters. Enable keep-alive', action='store_true',
                            required=False)
        parser.add_argument('-ka_dis', help='(Optional) No parameters. Disable keep-alive', action='store_true',
                            required=False)
        buf = '(Optional) Enable debug logging. Prints the formatted data structures (pprint) to the log and console.'
        parser.add_argument('-d', help=buf, action='store_true', required=False)
        buf = '(Optional) Directory where log file is to be created. Default is to use the current directory. The log' \
              ' file name will always be "Log_xxxx" where xxxx is a time and date stamp.'
        parser.add_argument('-log', help=buf, required=False, )
        buf = '(Optional) No parameters. When set, a log file is not created. The default is to create a log file.'
        parser.add_argument('-nl', help=buf, action='store_true', required=False)

        args = parser.parse_args()
        args_ip, args_id, args_pw, args_s = args.ip, args.id, args.pw, args.s
        args_rest_en, args_rest_dis, args_https_en, args_https_dis = \
            args.rest_en, args.rest_dis, args.https_en, args.https_dis
        args_max_rest, args_ka_en, args_ka_dis = args.max_rest, args.ka_en, args.ka_dis
        args_d, args_log, args_nl = args.d, args.log, args.nl

    # Set up the log file
    brcdapi_log.open_log(folder=args_log, suppress=False, no_log=args_nl, version_d=brcdapi_util.get_import_modules())
    if args_d:  # Verbose debug
        brcdapi_rest.verbose_debug(True)

    # Default security
    if args_s is None:
        args_s = 'self'

    rd = {
        'rest-enabled': True if args_rest_en else False if args_rest_dis else None,
        'https-protocol-enabled': True if args_https_en else False if args_https_dis else None,
        'max-rest-sessions': args_max_rest,
        'https-keep-alive-enabled': True if args_ka_en else False if args_ka_dis else None
    }

    # User feedback
    ml = ['WARNING!!! Debug is enabled'] if _DEBUG else list()
    ml.append('IP, -ip:                      ' + brcdapi_util.mask_ip_addr(args_ip, True))
    ml.append('ID, -id:                      ' + args_id)
    ml.append('Security, -s:                 ' + args_s)
    ml.append('Enable Rest, -rest_en:        ' + str(args_rest_en))
    ml.append('Disable Rest, -rest_dis:      ' + str(args_rest_dis))
    ml.append('Enable HTTPS, -https_en:      ' + str(args_https_en))
    ml.append('Disable HTTPS, -https_dis:    ' + str(args_https_dis))
    ml.append('Enable keep-alive, -ka_en:    ' + str(args_ka_en))
    ml.append('Disable keep-alive, -ka_dis:  ' + str(args_ka_dis))
    ml.append('Max Rest sessions, -max_rest: ' + str(args_max_rest))

    # Validate the input and set up the return dictionary
    if args_rest_en and args_rest_dis:
        ml.append('-rest_en and -rest_dis are mutually exclusive.')
        ec = -1
    if args_https_en and args_https_dis:
        ml.append('-https_en and -https_dis are mutually exclusive.')
        ec = -1
    if args_ka_en and args_ka_dis:
        ml.append('-ka_en and -ka_dis are mutually exclusive.')
        ec = -1
    if len(rd) == 0:
        ml.extend(['', 'No changes'])
    brcdapi_log.log(ml, echo=True)

    return ec, args_ip, args_id, args_pw, args_s, rd


def pseudo_main():
    """Basically the main().

    :return: Exit code
    :rtype: int
    """
    global _DEBUG

    # Get and validate command line input
    ec, ip, user_id, pw, sec, input_d = _get_input()
    if ec != 0:
        return ec

    # Login
    brcdapi_log.log('Attempting login', echo=True)
    session = brcdapi_rest.login(user_id, pw, ip, sec)
    if fos_auth.is_error(session):
        brcdapi_log.log(fos_auth.formatted_error_msg(session), echo=True)
        return -1
    brcdapi_log.log('Login succeeded', echo=True)

    ec = 0
    uri = 'running/brocade-chassis/management-interface-configuration'

    try:  # try/except so that no matter what happens, the logout code gets executed.

        # Display initial read (GET) of parameters
        brcdapi_log.log(['', 'Before Changes:'], echo=True)
        obj = brcdapi_rest.get_request(session, uri)
        if fos_auth.is_error(obj):
            brcdapi_log.log(fos_auth.formatted_error_msg(obj), echo=True)
            ec = -1
        else:
            brcdapi_log.log(pprint.pformat(obj), echo=True)

        if ec == 0:

            # Make the changes
            content_d = dict()
            for k, v in input_d.items():
                if v is not None:
                    content_d.update({k: v})
            if len(content_d) == 0:
                brcdapi_log.log('No changes to make.', echo=True)
            else:
                obj = brcdapi_rest.send_request(session,
                                                uri,
                                                'PATCH',
                                                {'management-interface-configuration': content_d})
                if fos_auth.is_error(obj):
                    brcdapi_log.log(fos_auth.formatted_error_msg(obj), echo=True)
                    ec = -1
                else:

                    # Display read (GET) after changing parameters
                    brcdapi_log.log(['', 'After Changes:'], echo=True)
                    obj = brcdapi_rest.get_request(session, uri)
                    if fos_auth.is_error(obj):
                        brcdapi_log.log(fos_auth.formatted_error_msg(obj), echo=True)
                        ec = -1
                    else:
                        brcdapi_log.log(pprint.pformat(obj), True)

    except brcdapi_util.VirtualFabricIdError:
        brcdapi_log.log('Software error. Search the log for "Invalid FID" for details.', echo=True)
        ec = -1
    except BaseException as e:
        brcdapi_log.exception(['Programming error encountered.', str(type(e)) + ': ' + str(e)], echo=True)
        ec = -1

    # Logout
    obj = brcdapi_rest.logout(session)
    if fos_auth.is_error(obj):
        brcdapi_log.log('Logout failed', True)
        ec = -1
    else:
        brcdapi_log.log('Logout succeeded', True)

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
brcdapi_log.close_log('Processing complete. Exit status: ' + str(_ec), echo=True)
exit(_ec)
