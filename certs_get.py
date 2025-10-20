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

:mod:`certs_get` - Read and generate a report of security certificates.

**Description**

    The intent of this module is to provide a programming example on how to GET and determine certificate begin and
    expiration dates.

**Version Control*

+-----------+---------------+-----------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                       |
+===========+===============+===================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                         |
+-----------+---------------+-----------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Set verbose debug via brcdapi.brcdapi_rest.verbose_debug()                        |
+-----------+---------------+-----------------------------------------------------------------------------------+
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
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import brcdapi.log as brcdapi_log
import brcdapi.util as brcdapi_util
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as fos_auth
import brcdapi.gen_util as gen_util

_DOC_STRING = False  # Should always be False. Prohibits any code execution. Only useful for building documentation
# When _DEBUG is True, use _DEBUG_xxx below instead of parameters passed from the command line. I did it this way,
# rather than rely on parameter passing with IDE tools because the API examples are typically used as programming
# examples, not stand-alone scripts. It's easier to modify the inputs this way.
_DEBUG = False
_DEBUG_ip = 'xx.xxx.x.69'
_DEBUG_id = 'admin'
_DEBUG_pw = 'password'
_DEBUG_s = None  # HTTPS is the default. Use 'none' for HTTP.
_DEBUG_d = True
_DEBUG_log = '_logs'
_DEBUG_nl = False


def _cert_detail_report(obj):
    """Generates a user-friendly cert report.

    :param obj: Object returned from the API.
    :type obj: dict
    :rtype: None
    """
    # For each certificate, display the full cert if present
    for cert_d in obj['security-certificate']:
        hexdump = cert_d.get('certificate-verbose')
        if isinstance(hexdump, str) and len(hexdump) > 0:
            buf = cert_d['certificate-entity'] + ', ' + cert_d['certificate-type'] + ' Detail:'
            brcdapi_log.log(['', buf, '', hexdump], echo=True)


def _cert_summary_report(obj):
    """Generates a user-friendly cert report.

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

    brcdapi_log.log(ml, echo=True)


def _get_input():
    """Parses the module load command line, performs basic parameter validation checks, and sets up the log file.

    :return ip_addr: IP address of switch
    :rtype ip_addr: str
    :return user_id: User login ID
    :rtype user_id: str
    :return pw: Login password
    :rtype pw: str
    :return sec: 'self' for self-signed certificate (HTTPS) or 'none' (HTTP)
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
        parser.add_argument('-s', help='Optional. "none" for HTTP. The default is "self" for HTTPS mode.',
                            required=False)
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
    brcdapi_log.open_log(folder=args_log, suppress=False, version_d=brcdapi_util.get_import_modules(), no_log=args_nl)
    if args_d:  # Verbose debug
        brcdapi_rest.verbose_debug(True)

    # Condition the input
    if args_s is None:
        args_s = 'self'

    # User feedback about input.
    ml = ['WARNING: Debug mode is enabled'] if _DEBUG else list()
    ml.extend(['IP, -ip:                   ' + brcdapi_util.mask_ip_addr(args_ip, True),
               'ID, -id:                   ' + args_id,
               'Security, -sec:            ' + args_s,
               ''])
    brcdapi_log.log(ml, echo=True)

    return args_ip, args_id, args_pw, args_s


def pseudo_main():
    """Basically the main(). Did it this way, so it can easily be modified to be called from another script.

    :return: Exit code. See exit codes in brcddb.brcddb_common
    :rtype: int
    """
    ec, cert_obj = 0, None

    # Get the command line input
    ip_addr, user_id, pw, sec = _get_input()

    # Login
    brcdapi_log.log('Attempting login', echo=True)
    session = brcdapi_rest.login(user_id, pw, ip_addr, sec)
    if fos_auth.is_error(session):
        brcdapi_log.log('Login failed. Error message is:', echo=True)
        brcdapi_log.log(fos_auth.formatted_error_msg(session), echo=True)
        return -1
    brcdapi_log.log(['Login succeeded', 'Getting certificates. This will take about 30 sec.'], echo=True)

    try:  # This try is to ensure the logout code gets executed regardless of what happened.
        # Get the certificates from the API
        cert_obj = brcdapi_rest.get_request(session, 'running/brocade-security/security-certificate')
    except brcdapi_util.VirtualFabricIdError:
        brcdapi_log.log('Software error. Search the log for "Invalid FID" for details.', echo=True)
        ec = -1
    except BaseException as e:
        brcdapi_log.exception(['Unexpected error encountered.', str(type(e)) + ': ' + str(e)], echo=True)
        ec = -1

    # Logout
    brcdapi_log.log('Attempting logout', echo=True)
    obj = brcdapi_rest.logout(session)
    if fos_auth.is_error(obj):
        brcdapi_log.log('Logout failed. Error message is:', echo=True)
        brcdapi_log.log(fos_auth.formatted_error_msg(obj), echo=True)
        ec = -1
    else:
        brcdapi_log.log('Logout succeeded.', echo=True)

    # Display the certificates
    if fos_auth.is_error(cert_obj):
        brcdapi_log.exception('Failed to capture certificates.' + fos_auth.formatted_error_msg(cert_obj), echo=True)
        ec = -1
    else:
        _cert_detail_report(cert_obj)
        _cert_summary_report(cert_obj)

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
brcdapi_log.close_log('All processing complete. Exit code: ' + str(_ec))
exit(_ec)
