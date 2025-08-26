#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Copyright 2023, 2024, 2025 Consoli Solutions, LLC.  All rights reserved.

**License**

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
the License. You may also obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
language governing permissions and limitations under the License.

The license is free for single customer use (internal applications). Use of this module in the production,
redistribution, or service delivery for commerce requires an additional license. Contact jack@consoli-solutions.com for
details.

**Description**

Login and logout. Used to validate the HTTP(S) connections

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Improved error messaging                                                              |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 03 Apr 2024   | Added version numbers of imported libraries.                                          |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.3     | 06 Dec 2024   | Updated comments only.                                                                |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.4     | 25 Aug 2025   | Use brcddb.util.util.get_import_modules to dynamically determined imported libraries. |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2024, 2025 Consoli Solutions, LLC'
__date__ = '25 Aug 2025'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.4'

import os
import brcdapi.log as brcdapi_log
import brcdapi.util as brcdapi_util
import brcdapi.gen_util as gen_util
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as brcdapi_auth

_DOC_STRING = False  # Should always be False. Prohibits any code execution. Only useful for building documentation

_input_d = gen_util.parseargs_login_d.copy()
_input_d.update(gen_util.parseargs_log_d.copy())
_input_d.update(gen_util.parseargs_debug_d.copy())


def pseudo_main(ip, user_id, pw, sec):
    """For consistency with all other modules.

    :param ip: IP address
    :type ip: str
    :param user_id: User ID
    :type user_id: str
    :param pw: Password
    :type pw: str
    :param sec: Type of HTTP security. Should be 'none' or 'self'
    :type sec: str
    :return: Exit code. See exist codes in brcddb.brcddb_common
    :rtype: int
    """
    global __version__

    session = None

    # Login
    brcdapi_log.log('Attempting login', True)
    try:
        session = brcdapi_rest.login(user_id, pw, ip, sec)
        if brcdapi_auth.is_error(session):
            brcdapi_log.log('Login failed. Error message is:', echo=True)
            brcdapi_log.log(brcdapi_auth.formatted_error_msg(session), echo=True)
            return -1
    except BaseException as e:
        brcdapi_log.log(['Unexpected FOS error.', 'Exception: ' + str(type(e)) + ': ' + str(e)], echo=True)

    # Logout
    try:
        brcdapi_log.log('Login succeeded. Attempting logout', echo=True)
        obj = brcdapi_rest.logout(session)
        if brcdapi_auth.is_error(obj):
            brcdapi_log.log('Logout failed. Error message is:', echo=True)
            brcdapi_log.log(brcdapi_auth.formatted_error_msg(obj), echo=True)
            return -1
        brcdapi_log.log('Logout succeeded.', True)
    except BaseException as e:
        brcdapi_log.log(['Unexpected FOS error.', 'Exception: ' + str(type(e)) + ': ' + str(e)], echo=True)

    return 0


def _get_input():
    """Parses the module load command line

    :return: Exit code. See exist codes in brcddb.brcddb_common
    :rtype: int
    """
    global __version__, _input_d

    # Get command line input
    args_d = gen_util.get_input('Capture (GET) requests from a chassis', _input_d)

    # Set up logging
    brcdapi_rest.verbose_debug(args_d['d'])
    brcdapi_log.open_log(
        folder=args_d['log'],
        suppress=args_d['sup'],
        no_log=args_d['nl'],
        version_d=brcdapi_util.get_import_modules()
    )

    # Command line feedback
    ml = [
        os.path.basename(__file__) + ', ' + __version__,
        'IP, -ip:               ' + brcdapi_util.mask_ip_addr(args_d['ip'], keep_last=True),
        'ID, -id:               ' + args_d['id'],
        'Security, -s:          ' + args_d['s'],
        'Log, -log:             ' + str(args_d['log']),
        'No log, -nl:           ' + str(args_d['nl']),
        'Debug, -d:             ' + str(args_d['d']),
        'Suppress, -sup:        ' + str(args_d['sup']),
        '',
    ]
    brcdapi_log.log(ml, echo=True)

    return pseudo_main(args_d['ip'], args_d['id'], args_d['pw'], args_d['s'])


###################################################################
#
#                    Main Entry Point
#
###################################################################
if _DOC_STRING:
    print('_DOC_STRING is True. No processing')
    exit(0)

_ec = _get_input()
brcdapi_log.close_log(['', 'Processing Complete. Exit code: ' + str(_ec)], echo=True)
exit(_ec)
