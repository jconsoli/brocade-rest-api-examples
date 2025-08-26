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

Captures all switch data from a list and generates a report.

This is effectively an intelligent batch file that does the following:

    * Create a folder for the collected data.
    * Start capture.py for each chassis specified in a passed chassis list
    * Start combine.py once the data capture completes
    * Start report.py once the combine completes

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Added port stats clear, -clr, maps_report, and comparison report                      |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 03 Apr 2024   | Added version numbers of imported libraries.                                          |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.3     | 16 Jun 2024   | Changed default HTTP to "self". Added -sheet input parameter.                         |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.4     | 29 Oct 2024   | Accidentally left _DEBUG enabled. Disabled it in this release. Other than printing    |
|           |               | additional debug information to the console, this parameter does nothing.             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.5     | 06 Dec 2024   | Fixed spelling mistake in message.                                                    |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.6     | 25 Aug 2025   | Fixed missing -d parameter passing to capture.py                                      |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2024, 2025 Consoli Solutions, LLC'
__date__ = '25 Aug 2025'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.6'

import signal
import datetime
import os
import subprocess
import brcdapi.log as brcdapi_log
import brcdapi.gen_util as gen_util
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.util as brcdapi_util
import brcdapi.excel_util as excel_util
import brcdapi.file as brcdapi_file
import brcddb.brcddb_common as brcddb_common

# debug input (for copy and paste into Run->Edit Configurations->script parameters):
# -i multi_capture_gsh -bp bp -sfp sfp_rules_r12 -r -c * -nm -log _logs

_DOC_STRING = False  # Should always be False. Prohibits any code execution. Only useful for building documentation
# _STAND_ALONE: True: Executes as a standalone module taking input from the command line. False: Does not automatically
# execute. This is useful when importing this module into another module that calls psuedo_main().
_STAND_ALONE = True  # See note above

_DEBUG = False   # When True, echos additional status and debug information to STD_IO

# Input parameter definitions
_input_d = dict(
    i=dict(h='Required. Excel file of switch login credentials. See multi_capture_example.xlsx. ".xlsx" is '
             'automatically appended. The cells in the "security" column default to "self" if empty. The "name" '
             'column is only used for error reporting if there is a problem logging in.'),
    f=dict(r=False,
           h='Optional. Folder name where captured data is to be placed. If not specified, a folder with the default '
             'name _capture_yyyy_mmm_dd_hh_mm_ss is created. The individual switch data is put in this folder with '
             'the switch name. A file named combined.json, output of combine.py, and reports are added to this '
             'folder. Typically not used.'),
    bp=dict(r=False,
            h='Optional. Name of the Excel Workbook with best practice checks. This parameter is passed to report.py '
              'if -r is specified. Otherwise it is not used. ".xlsx" is automatically appended. Typically used.'),
    sheet=dict(r=False, h='Optional. Specifies the sheet name in -bp to read. The default is "active".'),
    sfp=dict(r=False,
             h='Optional. Name of the Excel Workbook with SFP thresholds. This parameter is passed to report.py if -r '
               'is specified. Otherwise it is not used. ".xlsx" is automatically appended.'),
    group=dict(r=False,
               h='Optional. Name of Excel file containing group definitions. This parameter is passed to report.py if '
                 '-r is specified. Otherwise it is not used. ".xlsx" is automatically appended.'),
    iocp=dict(r=False,
              h='Optional. Name of folder with IOCP files. All files in this folder must be IOCP files (build I/O '
                'configuration statements from HCD) and must begin with the CEC serial number followed by \'_\'. '
                'Leading 0s are not required. Example, for a CPC with serial number 12345: 12345_M90_iocp.txt'),
    r=dict(r=False, t='bool', d=False,
           h='Optional. No parameters. When specified, generates a report (report.py), MAPS report (maps_report.py) '
             'and a comparison (compare_report.py). See -f option for location. The name of the reports are: '
             '"report_yyyy_mm_dd_hh_mm_ss.xlsx", "maps_report_yyyy_mm_dd_hh_mm_ss.xlsx" and '
             '"compare_to_yyyy_mm_dd_hh_mm_ss.xlsx"'),
    c=dict(r=False,
           h='Optional. Name of file with list of KPIs to capture. Use * to capture all data the chassis supports. The '
             'default is to capture all KPIs required for the report.'),
    clr=dict(r=False, t='bool', d=False, h='Optional. No parameters. Clear port statistics after successful capture'),
    nm=dict(r=False, t='bool', d=False,
            h='Optional. No parameters. By default, all but the last octet of IP addresses are masked before being '
              'stored in the output file. This option preserves the full IP address which is useful for having full '
              'IP addresses in reports and when using restore_all.py.'),
)
_input_d.update(gen_util.parseargs_log_d.copy())
_input_d.update(gen_util.parseargs_debug_d.copy())


def psuedo_main(addl_parms_all, addl_parms_capture, addl_parms_report, file, folder, r_flag, b_file, date_str):
    """Basically the main(). Did it this way so that it can easily be used as a standalone module or called externally.

    :param addl_parms_all: Additional parameters for invoked scripts.
    :type addl_parms_all: list
    :param addl_parms_capture: Additional parameters for capture.py
    :type addl_parms_capture: list
    :param addl_parms_report: Additional parameters for report.py
    :type addl_parms_report: list
    :param file: Login credentials file
    :type file: str
    :param folder: Output folder, -f, for capture.py
    :type folder: str
    :param r_flag: If True, execute report.py
    :type r_flag: bool
    :param b_file: Name of base file, -b, for compare_report.py
    :type b_file: str, None
    :param date_str: Date and time stamp used for naming report files.
    :type date_str: str, None
    :return: Exit code. See exist codes in brcddb.brcddb_common
    :rtype: int
    """
    global _DEBUG

    signal.signal(signal.SIGINT, brcdapi_rest.control_c)

    c_file = folder + '/combined.json'

    # Read the file with login credentials and perform some basic validation
    ml, switch_params = list(), list()
    row = 1
    try:
        for d in excel_util.parse_parameters(sheet_name='parameters', hdr_row=0, wb_name=file)['content']:
            row += 1
            buf = brcdapi_file.full_file_name(d['name'].split('/').pop().split('\\').pop(), '.json')  # Just file name
            switch_params.append(['-id', d['user_id'],
                                  '-pw', d['pw'],
                                  '-ip', d['ip_addr'],
                                  '-s', 'self' if d['security'] is None else d['security'],
                                  '-f', folder + '/' + buf])
    except FileNotFoundError:
        ml.extend(['', file + ' not found.'])
    except FileExistsError:
        ml.extend(['', 'Path in ' + file + ' does not exist.'])
    except AttributeError:
        ml.extend(['',
                   'Invalid login credentials in row ' + str(row) + ' in ' + file,
                   'This typically occurs when cells are formatted with no content. Try deleting any unused rows.'])
    except KeyboardInterrupt:
        ml.extend(['', 'Processing terminated with Control-C from keyboard'])

    # Create the folder
    if len(ml) == 0:
        try:
            os.mkdir(folder)
        except FileExistsError:
            ml.extend(['', 'Folder ' + folder + ' already exists.'])
        except FileNotFoundError:
            ml.extend(['', folder + ' contains a path that does not exist.'])
    if len(ml) > 0:
        brcdapi_log.log(ml, echo=True)
        return brcddb_common.EXIT_STATUS_INPUT_ERROR

    # Kick off all the data captures
    try:
        pid_l = list()
        for temp_l in switch_params:
            params = ['python.exe', 'capture.py'] + temp_l + addl_parms_capture + addl_parms_all
            debug_params, ip_flag = list(), False
            for buf in params:
                if ip_flag:
                    debug_params.append(brcdapi_util.mask_ip_addr(buf, keep_last=True))
                    ip_flag = False
                else:
                    debug_params.append(buf)
                    if buf == '-ip' and '-nm' not in params:
                        ip_flag = True
            brcdapi_log.log('DEBUG: ' + ' '.join(debug_params), echo=_DEBUG)
            pid_l.append(subprocess.Popen(params))

        # Below waits for all processes to complete before generating the report.
        pid_done = [p.wait() for p in pid_l]
        for i in range(0, len(pid_done)):
            brcdapi_log.log('Completed switch capture at index ' + str(i) + '. Ending status: ' + str(pid_done[i]),
                            echo=True)
    except KeyboardInterrupt:
        brcdapi_log.log(['Processing terminating with Control-C from keyboard.',
                         'WARNING: This module starts other capture sessions which must be terminated individually'],
                        echo=True)

    try:
        # Combine the captured data
        brcdapi_log.log('Combining captured data. This may take several seconds', echo=True)
        params = ['python.exe', 'combine.py', '-i', folder, '-o', 'combined'] + addl_parms_all
        brcdapi_log.log('DEBUG: ' + ' '.join(params), echo=_DEBUG)
        ec = subprocess.Popen(params).wait()
        brcdapi_log.log('Combine completed with status: ' + str(ec), echo=True)

        # Generate the report
        if r_flag and ec == brcddb_common.EXIT_STATUS_OK:
            brcdapi_log.log('Creating report.', echo=True)
            buf = folder + '/report' + date_str + '.xlsx'
            params = ['python.exe', 'report.py', '-i', c_file, '-o', buf]
            params.extend(addl_parms_report + addl_parms_all)
            brcdapi_log.log('DEBUG: ' + ' '.join(params), echo=_DEBUG)
            ec = subprocess.Popen(params).wait()

        # Generate the MAPS report
        if r_flag and ec == brcddb_common.EXIT_STATUS_OK:
            brcdapi_log.log('Creating MAPS report.', echo=True)
            buf = folder + '/maps_report' + date_str + '.xlsx'
            params = ['python.exe', 'maps_report.py', '-i', c_file, '-o', buf]
            params.extend(addl_parms_all)
            brcdapi_log.log('DEBUG: ' + ' '.join(params), echo=_DEBUG)
            ec = subprocess.Popen(params).wait()

        # Generate the comparison report
        if r_flag and isinstance(b_file, str) and ec == brcddb_common.EXIT_STATUS_OK:
            # Figure out what the base file should be
            buf = folder + '/compare' + date_str + '_to' + b_file.split('/')[0].replace('_capture', '')
            brcdapi_log.log('Creating comparison report.', echo=True)
            params = ['python.exe', 'compare_report.py', '-b', b_file, '-c', c_file, '-r', buf]
            params.extend(addl_parms_all)
            brcdapi_log.log('DEBUG: ' + ' '.join(params), echo=_DEBUG)
            ec = subprocess.Popen(params).wait()

    except KeyboardInterrupt:
        brcdapi_log.log('Processing terminating with Control-C from keyboard.', echo=True)
        ec = brcddb_common.EXIT_STATUS_INPUT_ERROR

    return ec


def _get_input():
    """Parses the module load command line when launching from stand-alone desk top application

    :return: Exit code. See exist codes in brcddb.brcddb_common
    :rtype: int
    """
    global __version__, _input_d

    addl_parms_capture, addl_parms_report, addl_parms_all = list(), list(), list()

    # Get command line input
    args_d = gen_util.get_input('Capture (GET) requests from a chassis', _input_d)

    # Set up logging
    brcdapi_log.open_log(
        folder=args_d['log'],
        suppress=args_d['sup'],
        no_log=args_d['nl'],
        version_d=brcdapi_util.get_import_modules()
    )
    if args_d['log'] is not None:
        addl_parms_all.extend(['-log', args_d['log']])
    for k in ('sup', 'nl'):
        if args_d[k]:
            addl_parms_all.append('-' + k)

    # Additional input for capture.py
    if isinstance(args_d['c'], str):
        addl_parms_capture.extend(['-c', args_d['c']])
    for k, v in {'-clr': args_d['clr'], '-nm': args_d['nm'], '-d': args_d['d']}.items():
        if v:
            addl_parms_capture.append(k)

    # Additional input report.py
    r_d = {'-iocp': args_d['iocp'],
           '-sfp': args_d['sfp'],
           '-group': args_d['group'],
           '-bp': args_d['bp'],
           '-sheet': args_d['sheet']}
    for k, v in r_d.items():
        if v is not None:
            addl_parms_report.extend([k, v])

    # Figure out the file name for the most recent report for compare_report.py
    b_file = None
    in_file = brcdapi_file.full_file_name(args_d['i'], '.xlsx')
    if args_d['r']:
        c_time = 0.0
        for d in brcdapi_file.read_full_directory('.'):
            if d['name'] == 'combined.json':
                b_folder_l = d['folder'].split('_')
                if len(b_folder_l) == 8 and b_folder_l[1] == 'capture':  # A leap of faith the rest is right
                    if d['st_ctime'] > c_time:
                        c_time = d['st_ctime']
                        b_file = '_' + '_'.join(b_folder_l[1:]) + '/' + 'combined.json'

    # Get file names for the reports and data capture
    date_str = '_' + datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
    folder = '_capture' + date_str if args_d['f'] is None else args_d['f']

    # User feedback
    buf = '(Default) ' if args_d['f'] is None else ''
    ml = [
        os.path.basename(__file__) + ', ' + __version__,
        'Input file, -i:           ' + args_d['i'],
        'Output folder, -f:        ' + buf + folder,
        'SFP, -sfp:                ' + str(args_d['sfp']),
        'Group, -group:            ' + str(args_d['group']),
        'Best Practices, -bp:      ' + str(args_d['bp']),
        'IOCP, -iocp:              ' + str(args_d['iocp']),
        'Report, -r:               ' + str(args_d['r']),
        'Zone groups, -group:      ' + str(args_d['group']),
        'KPI File, -c:             ' + str(args_d['c']),
        'Clear stats, -clr:        ' + str(args_d['clr']),
        'Log, -log:                ' + str(args_d['log']),
        'No log, -nl:              ' + str(args_d['nl']),
        'Debug, -d:                ' + str(args_d['d']),
        'Suppress, -sup:           ' + str(args_d['sup']),
        '',
    ]
    brcdapi_log.log(ml, echo=True)

    return psuedo_main(addl_parms_all, addl_parms_capture, addl_parms_report, in_file, folder, args_d['r'], b_file,
                       date_str)


###################################################################
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
