#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2020, 2021, 2022 Jack Consoli.  All rights reserved.
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
:mod:`lib_check.py` - Validates the Python development environment by checking the Python version and import path.
Also Checks to ensure that all imported libraries required the modules in brcdapi and brcddb are in the Python path.

Intended as a tool to validate the supported version of Python and proper installation of libraries used for:

* brcdapi
* brcddb
* api_examples
* applications

For a generic but more detailed library validation report, use lib_validate.py from:

https://github.com/jconsoli/Tools

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 3.0.0     | 19 Jul 2020   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.2.4     | 19 Oct 2022   | Latest updates.                                                                   |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2020, 2021, 2022 Jack Consoli'
__date__ = '19 Oct 2022'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.2.4'

import sys
import os
import importlib
try:
    import platform
except ImportError(platform):
    print('Could not import platform')
try:
    import datetime
    print('\n' + datetime.datetime.now().strftime('%d %b %Y %H:%M:%S'))
except ImportError(datetime):
    print('Could not import datetime')

_DOC_STRING = False  # Should always be False. Prohibits any importing. Only useful for building documentation

_imports = (
    {'d': ''},
    {'d': 'Standard Python Libraries.'},
    {'d': ''},
    {'l': 'abc', 'd': 'Required for most applications'},
    {'l': 'base64', 'd': 'Required by brcdbapi.fos_auth'},
    {'l': 'contextlib', 'd': 'Required by any module using openpyxl (Excel Workbooks)'},
    {'l': 'copy', 'd': 'Required for most applications'},
    {'l': 'time', 'd': 'Required by brcdbapi.fos_auth and brcdbapi.brcdb_rest'},
    {'l': 'errno', 'd': 'Required by brcdbapi.fos_auth'},
    {'l': 'fnmatch', 'd': 'Required for most applications'},
    {'l': 'http.client', 'd': 'Required by brcdbapi.fos_auth and brcdbapi.brcdb_rest'},
    {'l': 'itertools', 'd': 'Required by brcdbapi.fos_auth and brcdbapi.brcdb_rest'},
    {'l': 'json', 'd': 'Required by brcdbapi.fos_auth and brcdbapi.brcdb_rest'},
    {'l': 'jdcal', 'd': 'Required by any module using openpyxl (Excel Workbooks)'},
    {'l': 'et_xmlfile', 'd': 'Required by any module using openpyxl (Excel Workbooks)'},
    {'l': 'os', 'd': 'Required for most applications'},
    {'l': 'pathlib', 'd': 'Required for most applications'},
    {'l': 'ssl', 'd': 'Required by brcdapi.brcdapi_rest'},
    {'l': 'argparse', 'd': 'Required for most applications'},
    {'l': 'datetime', 'd': 'Required for brcdapi.log'},
    {'l': 'pprint', 'd': 'Used for error reporting.'},
    {'l': 're', 'd': 'Used in brcddb.util.search for ReGex searching'},
    {'l': 'cryptography', 'd': 'Used in examples that update security certificates'},
    {'l': 'urllib3', 'd': 'Used in examples that update security certificates'},
    {'d': ''},
    {'d': 'Open source python libraries. Typically not included in standard Python installs.'},
    {'d': ''},
    {'l': 'collections', 'd': 'Required by brcdapi.switch and several brcddb.report modules.'},
    {'l': 'openpyxl', 'd': 'Required by report utilities for creating Excel Workbooks.'},
    # {'l': 'paramiko', 'd': 'Only required by applications/switch_config.py.'},
    {'l': 'warnings', 'd': 'Required for most applications'},
    {'d': ''},
    {'d': 'FOS API driver libraries from github/jconsoli - brcdapi.'},
    {'d': ''},
    {'l': 'brcdapi.fos_auth', 'd': 'Required by brcdapi.brcdapi_rest.', 'r': '1.0.5'},
    {'l': 'brcdapi.brcdapi_rest', 'd': 'FOS RESTConf API driver.', 'r': '3.0.8'},
    {'l': 'brcdapi.excel_util', 'd': 'Required by modules that read or write Excel workbooks', 'r': '1.0.1'},
    {'l': 'brcdapi.fos_cli', 'd': 'Required by switch_config.py applications.', 'r': '3.0.2'},
    {'l': 'brcdapi.file', 'd': 'Required by modules that perform file I/O.', 'r': '1.0.3'},
    {'l': 'brcdapi.gen_util', 'd': 'Required by most scripts.', 'r': '1.0.5'},
    {'l': 'brcdapi.log', 'd': 'Required by all scripts.', 'r': '3.0.7'},
    {'l': 'brcdapi.port', 'd': 'Required for reading and configuring ports.', 'r': '3.0.7'},
    {'l': 'brcdapi.switch', 'd': 'Required for reading and configuring switches.', 'r': '3.0.6'},
    {'l': 'brcdapi.util', 'd': 'Utilities supporting the FOS RESTConf API driver.', 'r': '3.0.8'},
    {'l': 'brcdapi.zone', 'd': 'Required by scripts performing zoning operations.', 'r': '3.0.5'},
    {'d': ''},
    {'d': 'FOS API database libraries from github/jconsoli - brcddb'},
    {'d': ''},
    {'l': 'brcddb.api.interface', 'd': 'Required for all access to the API', 'r': '3.0.8'},
    {'l': 'brcddb.api.zone', 'd': 'Required for zoning applications', 'r': '3.0.6'},
    {'l': 'brcddb.apps.report', 'd': 'Required for the report.py application', 'r': '3.1.4'},
    {'l': 'brcddb.apps.zone', 'd': 'Required for the cli_zone.py application', 'r': '3.0.4'},
    {'l': 'brcddb.brcddb_bp', 'd': 'Required for the report.py application', 'r': '3.0.8'},
    {'l': 'brcddb.brcddb_chassis', 'd': 'Required for most brcddb libraries', 'r': '3.0.7'},
    {'l': 'brcddb.brcddb_common', 'd': 'Required for most applications and brcddb libraries', 'r': '3.0.8'},
    {'l': 'brcddb.brcddb_fabric', 'd': 'Required for most brcddb libraries', 'r': '3.1.8'},
    {'l': 'brcddb.brcddb_login', 'd': 'Required for most applications', 'r': '3.0.5'},
    {'l': 'brcddb.brcddb_port', 'd': 'Required for most brcddb libraries', 'r': '3.0.8'},
    {'l': 'brcddb.brcddb_project', 'd': 'Required for most brcddb libraries', 'r': '3.1.1'},
    {'l': 'brcddb.brcddb_switch', 'd': 'Required for most brcddb libraries', 'r': '3.0.7'},
    {'l': 'brcddb.brcddb_zone', 'd': 'Required for most brcddb libraries', 'r': '3.0.5'},
    {'l': 'brcddb.classes.alert', 'd': 'Required for all brcddb libraries', 'r': '3.0.4'},
    {'l': 'brcddb.classes.chassis', 'd': 'Required for all brcddb libraries', 'r': '3.0.6'},
    {'l': 'brcddb.classes.fabric', 'd': 'Required for all brcddb libraries', 'r': '3.0.9'},
    {'l': 'brcddb.classes.iocp', 'd': 'Required for all brcddb libraries', 'r': '3.0.6'},
    {'l': 'brcddb.classes.login', 'd': 'Required for all brcddb libraries', 'r': '3.0.5'},
    {'l': 'brcddb.classes.port', 'd': 'Required for all brcddb libraries', 'r': '3.0.8'},
    {'l': 'brcddb.classes.project', 'd': 'Required for all brcddb libraries', 'r': '3.0.7'},
    {'l': 'brcddb.classes.switch', 'd': 'Required for all brcddb libraries', 'r': '3.0.8'},
    {'l': 'brcddb.classes.util', 'd': 'Required for all brcddb libraries', 'r': '3.0.8'},
    {'l': 'brcddb.classes.zone', 'd': 'Required for all brcddb libraries', 'r': '3.0.8'},
    {'l': 'brcddb.util.copy', 'd': 'Required for most brcddb libraries', 'r': '3.0.5'},
    {'l': 'brcddb.util.compare', 'd': 'Required for most brcddb libraries', 'r': '3.1.0'},
    {'l': 'brcddb.util.file', 'd': 'Required for most brcddb libraries', 'r': '3.0.9'},
    {'l': 'brcddb.util.iocp', 'd': 'Required for most brcddb libraries', 'r': '3.0.9'},
    {'l': 'brcddb.util.maps', 'd': 'Required for most brcddb libraries', 'r': '3.0.7'},
    {'l': 'brcddb.util.obj_convert', 'd': 'Required for search.py application', 'r': '3.0.5'},
    {'l': 'brcddb.util.parse_cli', 'd': 'Required for most brcddb libraries', 'r': '1.0.4'},
    {'l': 'brcddb.util.search', 'd': 'Required for most brcddb libraries', 'r': '3.1.0'},
    {'l': 'brcddb.util.util', 'd': 'Required for most brcddb libraries', 'r': '3.1.7'},
    {'l': 'brcddb.report.bp', 'd': 'Required for generating Excel reports', 'r': '3.0.6'},
    {'l': 'brcddb.report.chassis', 'd': 'Required for generating Excel reports', 'r': '3.0.7'},
    {'l': 'brcddb.report.fabric', 'd': 'Required for generating Excel reports', 'r': '3.0.8'},
    {'l': 'brcddb.report.graph', 'd': 'Required for generating Excel reports', 'r': '3.0.3'},
    {'l': 'brcddb.report.iocp', 'd': 'Required for generating Excel reports', 'r': '3.0.8'},
    {'l': 'brcddb.report.login', 'd': 'Required for generating Excel reports', 'r': '3.0.9'},
    {'l': 'brcddb.report.port', 'd': 'Required for generating Excel reports', 'r': '3.1.0'},
    {'l': 'brcddb.report.switch', 'd': 'Required for generating Excel reports', 'r': '3.0.8'},
    {'l': 'brcddb.report.utils', 'd': 'Required for generating Excel reports', 'r': '3.1.3'},
    {'l': 'brcddb.report.zone', 'd': 'Required for generating Excel reports', 'r': '3.1.3'},
    {'l': 'brcddb.app_data.alert_tables', 'd': 'Alert format tables. Required for zone and best practice analysis.',
     'r': '3.1.1'},
    {'l': 'brcddb.app_data.bp_tables', 'd': 'Needed for the report application to determine best practice violations',
     'r': '3.0.7'},
    {'l': 'brcddb.app_data.report_tables', 'd': 'Required for controlling the formats when generating Excel reports',
     'r': '3.1.3'},
    {'d': ''},
    {'d': 'FOS API driver libraries from github/jconsoli, brcdapi, required for SANnav scripts.'},
    {'d': ''},
    {'l': 'brcdapi.sannav_auth', 'd': 'Required by all SANnav scripts', 'r': '1.0.0'},
)


def _get_os_and_lib_paths():
    try:
        operating_system = platform.system()
    except:
        operating_system = 'Unknown'
    try:
        rel = platform.release()
    except:
        rel = 'Unknown'
    try:
        ver = platform.version()
    except:
        ver = 'Unknown'
    try:
        pl = sys.path
    except:
        pl = ['Unknown']

    return pl, operating_system, rel, ver


def pseudo_main():
    """Basically the main().
    :return: Exit code
    :rtype: int
    """
    global _imports, __version__

    # Print a description of what this module does.
    print(os.path.basename(__file__) + ' version: ' + __version__)
    msg = '\n\nThis is a simple pass/fail test to validate that the necessary'
    msg += '\nlibraries to support the Brocade libraries to use with the FOS'
    msg += '\nAPI were installed properly.\n'
    msg += '\nFor a generic but more detailed library validation report, use'
    msg += '\nlib_validate.py from:\n\nhttps://github.com/jconsoli/Tools\n'
    print(msg)

    # Display the operating system, version, and release
    lib_paths, operating_system, rel, ver = _get_os_and_lib_paths()
    print('OS:      ' + operating_system)
    print('Release: ' + rel)
    print('Version: ' + ver)

    # Display the lib path
    print('\nPython library path(s):\n  * ' + '\n  * '.join(lib_paths))

    summary_updates = list()
    summary_missing = list()
    modules = dict()
    modules['Module'] = {'v': 'Version', 'i': 'Status', 'r': 'Rec Ver'}
    for d in _imports:
        lib = d.get('l')
        if lib is not None:
            try:
                mod = importlib.import_module(lib)
                try:
                    ver = mod.__version__
                except AttributeError:
                    ver = ''
                if d.get('r') is not None:
                    if ver == d['r']:
                        buf = 'Success'
                    else:
                        buf = 'Update'
                        summary_updates.append(lib)
                else:
                    buf = buf = 'Success'
                modules[lib] = {'v': ver, 'i': buf}
            except ModuleNotFoundError:
                modules[lib] = {'v': '', 'i': 'Failed'}
                summary_missing.append(lib)

    _LEN_VER = 9  # Width of Version column
    _REC_VER = 9  # Width of recommended version
    _LEN_STATUS = 10  # Width of Status column
    _LEN_MOD = 30  # Width of Module column
    _LEN_DESC = 50  # Width of description column
    total_len = _LEN_VER + _REC_VER + _LEN_STATUS + _LEN_MOD + _LEN_DESC
    e_buf = '|  '
    for x in (_LEN_MOD, _LEN_STATUS, _LEN_VER, _REC_VER):
        space = ''
        for i in range(0, x - 1):
            space = space + ' '
        e_buf = e_buf + space + '|'

    # Check the Python version
    msg = '\nPython Version: '
    try:
        ver = sys.version
        msg += ver
        try:
            ver = ver.split(' ')[0]
            ol = ver.split('.')
            if int(ol[0]) != 3 or int(ol[1]) < 3:
                msg += '\nWARNING: Unsupported version of Python. Python must be version  3.3 or higher.'
            else:
                msg += '\nPython version OK'
        except (ValueError, IndexError):
            msg += '\nInvalid version returned from sys.version'
    except AttributeError:
        msg += 'Unable to read sys.version'
    print(msg)

    # Now generate a simple report to STD_OUT
    s = '-'
    for i in range(0, total_len + 1):
        s = s + '-'
    print(s)
    ol = [{'l': 'Module', 'd': 'Description', 'r': 'Rec Ver'}]
    ol.extend(_imports)

    for mod in ol:
        extra_desc = ''
        print_buf = '| '
        if 'l' not in mod:
            if 'd' in mod:
                buf = mod.get('d')
            else:
                continue
            space = ''
            for i in range(0, total_len - len(buf) if total_len - len(buf) > 0 else 0):
                space = space + ' '
            print_buf = print_buf + buf + space
        else:
            obj = modules[mod.get('l')]

            # Module
            buf = mod.get('l')
            space = ''
            for i in range(0, _LEN_MOD - len(buf) if _LEN_MOD - len(buf) > 0 else 0):
                space = space + ' '
            print_buf = print_buf + buf + space

            # Status
            buf = obj.get('i') if 'i' in obj else 'Unknown'
            buf = '| ' + buf
            space = ''
            for i in range(0, _LEN_STATUS - len(buf) if _LEN_STATUS - len(buf) > 0 else 0):
                space = space + ' '
            print_buf = print_buf + buf + space

            # Version
            buf = obj.get('v') if 'v' in obj else ''
            buf = '| ' + buf
            space = ''
            for i in range(0, _LEN_VER - len(buf) if _LEN_VER - len(buf) > 0 else 0):
                space = space + ' '
            print_buf = print_buf + buf + space

            # Recommended Version
            buf = mod.get('r') if 'r' in mod else ''
            buf = '| ' + buf
            space = ''
            for i in range(0, _REC_VER - len(buf) if _REC_VER - len(buf) > 0 else 0):
                space = space + ' '
            print_buf = print_buf + buf + space

            # Description
            space = ''
            buf = mod.get('d') if 'd' in mod else ''
            buf = '| ' + buf
            if len(buf) > _LEN_DESC:
                extra_desc = buf[_LEN_DESC:]
                buf = buf[:_LEN_DESC]
            else:
                for i in range(0, _LEN_DESC - len(buf) if _LEN_DESC - len(buf) > 0 else 0):
                    space = space + ' '
            print_buf = print_buf + buf + space

        print(print_buf + '|')
        while len(extra_desc) > 0:
            space = ''
            buf = ' ' + extra_desc
            if len(buf) >= _LEN_DESC:
                buf = buf[:_LEN_DESC - 1]
                extra_desc = extra_desc[_LEN_DESC - 2:]
            else:
                for i in range(1, _LEN_DESC - len(buf) if _LEN_DESC - len(buf) > 0 else 0):
                    space = space + ' '
                extra_desc = ''
            print(e_buf + buf + space + '|')
        print(s)

    print('\nSummary of missing libraries:')
    if len(summary_missing) > 0:
        print('\n'.join(summary_missing))
    else:
        print('Found all moduless')
    print('\nSummary of recommended updates:')
    if len(summary_updates) > 0:
        print('\n'.join(summary_updates))
    else:
        print('All found modules are at recommended versions')


###################################################################
#
#                    Main Entry Point
#
###################################################################
if not _DOC_STRING:
    pseudo_main()
