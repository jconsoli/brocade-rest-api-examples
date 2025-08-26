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

Reads a list of CLI commands from a file and converts those commands to an equivalent brcddb object

Using the API as a replacement for an SSH CLI session isn't useful; however, since there are numerous CLI zoning
scripts, this was a useful tool to test brcddb.apps.zone.py. This module was posted for those familiar with the CLI to
use as an example with the following caveats and features:

    * d,i zones are not parsed properly
    * Includes common error checking
    * Takes advantage of all brcddb.apps.zone.py features (test mode, suppress output, zone from saved container)
    * Unsupported commands: zoneobjectexpunge, zoneobjectreplace, cfgdisable

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Improved error messaging.                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 03 Apr 2024   | Added version numbers of imported libraries.                                          |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.3     | 06 Dec 2024   | Improved help messages.                                                               |
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
import brcdapi.gen_util as gen_util
import brcdapi.util as brcdapi_util
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.file as brcdapi_file
import brcddb.brcddb_common as brcddb_common
import brcddb.apps.zone as action_c
import brcddb.util.util as brcddb_util

_DOC_STRING = False  # Should always be False. Prohibits any code execution. Only useful for building documentation

# _STAND_ALONE: True: Executes as a standalone module taking input from the command line. False: Does not automatically
# execute. This is useful when importing this module into another module that calls psuedo_main().
_STAND_ALONE = True  # See note above

_input_d = gen_util.parseargs_login_d.copy()
_input_d.update(
    cli=dict(h='Required. Name of plain text file with CLI commands. ".txt" is automatically appended. Comments and '
               'empty lines are removed.'),
    fid=dict(t='int', v=gen_util.range_to_list('1-128'), h='Required. Virtual Fabric ID (1 - 128)'),
    t=dict(r=False, d=False, t='bool',
           h='Optional. Test mode. No arguments. Validates the -cli file only. Zoning is not sent to the switch'),
    f=dict(r=False, d=False, t='bool',
           h='Optional. Force. No arguments. Ignore warnings and, when creating objects, overwrite the objects that '
             'already exist.'),
)
_input_d.update(gen_util.parseargs_log_d.copy())
_input_d.update(gen_util.parseargs_debug_d.copy())


def _format_fault(obj, line_num, file_content):
    """Formats a fault into printable text

    :param obj: Dictionary as defined in return from action_c.send_zoning()
    :type obj: dict
    :param line_num: Line number
    :type line_num: int
    :return: Formatted text
    :rtype: str
    """
    try:
        buf = str(file_content[line_num])
    except BaseException as e:
        buf = 'Unknown exception:' + str(type(e)) + ': ' + str(e)
    msg_l = [
        '',
        'Line:    ' + str(line_num + 1),
        'Input:   ' + buf,
        'changed: ' + str(obj.get('changed')),
        'fail:    ' + str(obj.get('fail')),
        'io:      ' + str(obj.get('io')),
        'Status:  ' + str(obj.get('status')),
        'Reason:  ' + str(obj.get('reason')),
        'err_msg:',
    ]
    msg_l.extend(['  ' + buf for buf in gen_util.convert_to_list(obj.get('err_msg'))])
    return '\n'.join(msg_l)


def pseudo_main(ip, user_id, pw, sec, cli_file, fid, t_flag, f_flag):
    """Basically the main(). Did it this way so that it can easily be used as a standalone module or called externally.

    :param ip: IP address
    :type ip: str
    :param user_id: User ID
    :type user_id: str
    :param pw: Password
    :type pw: str
    :param sec: Type of HTTP security. Should be 'none' or 'self'
    :type sec: str
    :param cli_file: Name of file with zoning CLI commands
    :type cli_file: str
    :param fid: Fabric ID for zoning CLI commands
    :type fid: int
    :param t_flag: Test flag
    :type t_flag: bool
    :param f_flag: Force flag
    :type f_flag: bool
    :return: Exit code. See exist codes in brcddb.brcddb_common
    :rtype: int
    """
    content = {
        'fid': fid,
        'ip-addr': ip,
        'id': user_id,
        'pw': pw,
        'sec': sec,
        'force': f_flag,
        'test': t_flag,
    }

    # Read in the CLI file, condition the input strings and send it
    ml, file_contents = list(), list()
    try:
        file_contents = brcdapi_file.read_file(cli_file)
    except FileNotFoundError:
        ml.extend(['', 'File ' + cli_file + ' not found. Did you remember the file extension?'])
    except PermissionError:
        ml.extend(['', 'You do not have permission to read ' + cli_file])
    if len(ml) > 0:
        brcdapi_log.log(ml, echo=True)
        return brcddb_common.EXIT_STATUS_INPUT_ERROR

    content.update(changes=brcddb_util.parse_cli(file_contents))
    response = action_c.send_zoning(content)

    # General information
    ec = brcddb_common.EXIT_STATUS_OK
    total_changes = total_failures = total_io = i = 0
    for obj in response:
        if isinstance(obj, dict):  # obj is None for blank or commented our lines in the input
            if obj.get('changed'):
                total_changes += 1
            if obj.get('fail'):
                total_failures += 1
                brcdapi_log.log(_format_fault(obj, i, file_contents), echo=True)
                ec = brcddb_common.EXIT_STATUS_ERROR
            if obj.get('io'):
                total_io += 1
        i += 1

    summary = 'Summary (Test mode. No fabric changes made):' if t_flag else 'Summary:'
    ml = [
        '',
        summary,
        'Total Changes  : ' + str(total_changes),
        'Total Failures : ' + str(total_failures),
        'Total I/O      : ' + str(total_io)
    ]
    brcdapi_log.log(ml, echo=True)

    return ec


def _get_input():
    """Parses the module load command line

    :return ec: Error code
    :rtype ec: int
    """
    global __version__, _input_d

    ec = brcddb_common.EXIT_STATUS_OK

    # Get command line input
    buf = 'Parses a plain text file with FOS zoning CLI commands and sets the zoning on the switch.'
    try:
        args_d = gen_util.get_input(buf, _input_d)
    except TypeError:
        return brcddb_common.EXIT_STATUS_INPUT_ERROR  # gen_util.get_input() already posted the error message.

    # Set up logging
    brcdapi_rest.verbose_debug(args_d['d'])
    brcdapi_log.open_log(
        folder=args_d['log'],
        suppress=args_d['sup'],
        no_log=args_d['nl'],
        version_d=brcdapi_util.get_import_modules()
    )

    # If not in test mode, were the switch parameters entered?
    help_msg_d = dict(ip='', id='', pw='')
    if not args_d['t']:
        for k in help_msg_d.keys():
            if args_d[k] is None:
                help_msg_d[k] = ' Required parameters when -t is not specified.'
                ec = brcddb_common.EXIT_STATUS_INPUT_ERROR

    # Command line feedback
    ip_help_msg = 'None' if args_d['ip'] is None else brcdapi_util.mask_ip_addr(args_d['ip'], keep_last=True)
    ml = [
        os.path.basename(__file__) + ', ' + __version__,
        'IP, -ip:        ' + ip_help_msg + help_msg_d['ip'],
        'ID, -id:        ' + str(args_d['id']) + help_msg_d['id'],
        'PW, -pw:        xxxxx' + help_msg_d['pw'],
        'CLI file:       ' + args_d['cli'],
        'FID:            ' + str(args_d['fid']),
        'Test flag:      ' + str(args_d['t']),
        'Force flag:     ' + str(args_d['f']),
        'Log, -log:      ' + str(args_d['log']),
        'No log, -nl:    ' + str(args_d['nl']),
        'Debug, -d:      ' + str(args_d['d']),
        'Suppress, -sup: ' + str(args_d['sup']),
        '',
        ]
    brcdapi_log.log(ml, echo=True)

    if ec != brcddb_common.EXIT_STATUS_OK:
        return ec

    args_d['cli'] = brcdapi_file.full_file_name(args_d['cli'], '.txt')
    return pseudo_main(args_d['ip'], args_d['id'], args_d['pw'], args_d['s'], args_d['cli'], args_d['fid'], args_d['t'],
                       args_d['f'])


##################################################################
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
