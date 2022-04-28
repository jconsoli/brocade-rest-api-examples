#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2022 Jack Consoli.  All rights reserved.
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
:mod:`certs_get` - Read and generate a report of security certificates.

**Description**

    The intent of this module is to provide a programming example on how to GET and determine certificate begin and
    expiration dates.

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 1.0.0     | 28 Apr 2022   | Initial launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""

__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2022 Jack Consoli'
__date__ = '28 Apr 2022'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '1.0.0'

import argparse
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import brcdapi.log as brcdapi_log
import brcdapi.util as brcdapi_util
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as fos_auth
import brcdapi.gen_util as gen_util

_DOC_STRING = False  # Should always be False. Prohibits any code execution. Only useful for building documentation
_DEBUG = False  # When True, use _DEBUG_xxx below instead of passed arguments
_DEBUG_ip = 'xx.xxx.x.69'
_DEBUG_id = 'admin'
_DEBUG_pw = 'password'
_DEBUG_s = 'self'
_DEBUG_d = True
_DEBUG_log = '_logs'
_DEBUG_nl = False


def _cert_detail_report(obj):
    """Generates a user friendly cert report.

    :param obj: Object returned from the API.
    :type obj: dict
    :rtype: None
    """
    # For each certificate, display the full cert if present
    for cert_d in obj['security-certificate']:
        hexdump = cert_d.get('certificate-verbose')
        if isinstance(hexdump, str) and len(hexdump) > 0:
            buf = cert_d['certificate-entity'] + ', ' + cert_d['certificate-type'] + ' Detail:'
            brcdapi_log.log(['', buf, '', hexdump], True)


def _cert_summary_report(obj):
    """Generates a user friendly cert report.

    :param obj: Object returned from the API.
    :type obj: dict
    :rtype: None
    """
    # Add the report header
    separator = '+----------------+----------------+----------------+----------------+----------------+'
    to_display = '|'
    for buf in ('Entity', 'Type', 'Present', 'Begins', 'Expires'):
        to_display += gen_util.pad_string(buf + ' ', 16, ' ') + '|'
    ml = ['', 'Summary:', '', separator, to_display, separator.replace('-', '=')]

    # Add each individual cert to the report
    for cert_d in obj['security-certificate']:
        to_display = '|'
        to_display += gen_util.pad_string(cert_d['certificate-entity'] + ' ', 16, ' ') + '|'
        to_display += gen_util.pad_string(cert_d['certificate-type'] + ' ', 16, ' ') + '|'
        hexdump = cert_d.get('certificate-hexdump')
        buf = 'X       ' if isinstance(hexdump, str) and len(hexdump) > 0 else ' '
        to_display += gen_util.pad_string(buf, 16, ' ') + '|'
        try:
            # With the cryptography library 3.1 and above, default_backend() is used if not specified. Earlier versions
            # require it explicitly so below is intended to work with both.
            cert = x509.load_pem_x509_certificate(hexdump.encode(), default_backend())
            for date in [cert.not_valid_before, cert.not_valid_after]:  # date is in datetime format
                to_display += gen_util.pad_string(date.strftime('%d %b %Y') + ' ', 16, ' ') + '|'
        except ValueError:
            # There is no certificate
            for buf in (' ', ' '):
                to_display += gen_util.pad_string(buf, 16, ' ') + '|'
        ml.append(to_display)
        ml.append(separator)

    brcdapi_log.log(ml, True)


def _get_input():
    """Parses the module load command line, performs basic parameter validation checks, and sets up the log file.

    :return ip_addr: IP address of switch
    :rtype ip_addr: str
    :return user_id: User login ID
    :rtype user_id: str
    :return pw: Login password
    :rtype pw: str
    :return sec: 'self' for self signed certificate (HTTPS) or 'none' (HTTP)
    :rtype sec: str
    """
    global _DEBUG_ip, _DEBUG_id, _DEBUG_pw, _DEBUG_s, _DEBUG_d, _DEBUG_log, _DEBUG_nl

    if _DEBUG:
        args_ip, args_id, args_pw, args_s, args_d, args_log, args_nl = \
            _DEBUG_ip, _DEBUG_id, _DEBUG_pw, _DEBUG_s, _DEBUG_d, _DEBUG_log, _DEBUG_nl
    else:
        buf = 'Displays the results from GET running/brocade-security/security-certificate. In addition to security '\
              'certificates, this URL also returns CSRs. Usually, this done to validate certificates so the CSRs '\
              'would be filtered out or ignored.'
        parser = argparse.ArgumentParser(description=buf)
        parser.add_argument('-ip', help='(Required) IP address', required=True)
        parser.add_argument('-id', help='(Required) User ID', required=True)
        parser.add_argument('-pw', help='(Required) Password', required=True)
        parser.add_argument('-s', help="(Optional) Default is HTTP. Use self for HTTPS mode.", required=False)
        buf = '(Optional) Enable debug logging. Prints the formatted data structures (pprint) to the log and console.'
        parser.add_argument('-d', help=buf, action='store_true', required=False)
        buf = '(Optional) Directory where log file is to be created. Default is to use the current directory. The log' \
              ' file name will always be "Log_xxxx" where xxxx is a time and date stamp.'
        parser.add_argument('-log', help=buf, required=False, )
        buf = '(Optional) No parameters. When set, a log file is not created. The default is to create a log file.'
        parser.add_argument('-nl', help=buf, action='store_true', required=False)

        args = parser.parse_args()
        args_ip, args_id, args_pw, args_s, args_d, args_log, args_nl = \
            args.ip, args.id, args.pw, args.s, args.d, args.log, args.nl

    # Set up the log file
    if not args_nl:
        brcdapi_log.open_log(args_log)
    if args_d:  # Verbose debug
        brcdapi_rest.verbose_debug = True

    # Condition the input
    if args_s is None:
        args_s = 'none'

    # User feedback about input.
    ml = ['WARNING: Debug mode is enabled'] if _DEBUG else list()
    ml.extend(['IP, -ip:                   ' + brcdapi_util.mask_ip_addr(args_ip, True),
               'ID, -id:                   ' + args_id,
               'Security, -sec:            ' + args_s,
               ''])
    brcdapi_log.log(ml, True)

    return args_ip, args_id, args_pw, args_s


def pseudo_main():
    """Basically the main(). Did it this way so it can easily be modified to be called from another script.

    :return: Exit code. See exit codes in brcddb.brcddb_common
    :rtype: int
    """
    # Get the command line input
    ip_addr, user_id, pw, sec = _get_input()

    # Login
    brcdapi_log.log('Attempting login', True)
    session = brcdapi_rest.login(user_id, pw, ip_addr, sec)
    if fos_auth.is_error(session):
        brcdapi_log.log('Login failed. Error message is:', True)
        brcdapi_log.log(fos_auth.formatted_error_msg(session), True)
        return -1
    brcdapi_log.log(['Login succeeded', 'Getting certificates. This will take about 30 sec.'], True)

    try:  # This try is to ensure the logout code gets executed regardless of what happened.
        # Get the certificates from the API
        cert_obj = brcdapi_rest.get_request(session, 'running/brocade-security/security-certificate')
    except BaseException as e:
        brcdapi_log.exception('Unexpected error encountered. Exception is: ' + str(e), True)

    # Logout
    brcdapi_log.log('Attempting logout', True)
    obj = brcdapi_rest.logout(session)
    if fos_auth.is_error(obj):
        brcdapi_log.log('Logout failed. Error message is:', True)
        brcdapi_log.log(fos_auth.formatted_error_msg(obj), True)
        return -1
    brcdapi_log.log('Logout succeeded.', True)

    # Display the certificates
    if fos_auth.is_error(cert_obj):
        brcdapi_log.exception('Failed to capture certificates.' + fos_auth.formatted_error_msg(cert_obj), True)
        return -1
    _cert_detail_report(cert_obj)
    _cert_summary_report(cert_obj)

    return 0


###################################################################
#
#                    Main Entry Point
#
###################################################################
if _DOC_STRING:
    print('_DOC_STRING is True. No processing')
    exit(0)

_ec = pseudo_main()
brcdapi_log.close_log('All processing complete. Exit code: ' + str(_ec))
exit(_ec)
