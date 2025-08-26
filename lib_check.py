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

Validates the Python development environment by checking the Python version and import path. Also Checks to ensure that
all imported libraries required the modules in brcdapi and brcddb are in the Python path.

For a generic but more detailed library validation report, use lib_validate.py

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.1.4     | 25 Aug 2025   | Updated versions references.                                                          |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2023, 2024, 2025 Consoli Solutions, LLC'
__date__ = '25 Aug 2025'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.1.4'

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
    dict(d=''),
    dict(d='Standard Python Libraries.'),
    dict(d=''),
    dict(l='abc', d='Required for most applications'),
    dict(l='argparse', d='Required for most applications'),
    dict(l='base64', d='Required by brcdbapi.fos_auth'),
    dict(l='contextlib', d='Required by any module using openpyxl (Excel Workbooks)'),
    dict(l='copy', d='Required for most applications'),
    dict(l='cryptography', d='Used in API examples certs_eval.py and certs_get.py'),
    dict(l='datetime', d='Required for brcdapi.log'),
    dict(l='deepdiff', d='Required for most applications'),
    dict(l='errno', d='Required by brcdbapi.fos_auth'),
    dict(l='et_xmlfile', d='Required by any module using openpyxl (Excel Workbooks)'),
    dict(l='fnmatch', d='Required for most applications'),
    dict(l='http.client', d='Required by brcdbapi.fos_auth and brcdbapi.brcdb_rest'),
    dict(l='itertools', d='Required by brcdbapi.fos_auth and brcdbapi.brcdb_rest'),
    dict(l='jdcal', d='Required by any module using openpyxl (Excel Workbooks)'),
    dict(l='json', d='Required by brcdbapi.fos_auth and brcdbapi.brcdb_rest'),
    dict(l='os', d='Required for most applications'),
    dict(l='paramiko', d='Required for most applications'),
    dict(l='pathlib', d='Required for most applications'),
    dict(l='pprint', d='Used for error reporting.'),
    dict(l='re', d='Used in brcddb.util.search for ReGex searching'),
    dict(l='ssl', d='Required by brcdapi.brcdapi_rest'),
    dict(l='urllib3', d='Used in examples that update security certificates'),
    dict(d=''),
    dict(d='Open source python libraries. Typically not included in standard Python installs.'),
    dict(d=''),
    dict(l='collections', d='Required by brcdapi.switch and several brcddb.report modules.'),
    dict(l='openpyxl', d='Required by report utilities for creating Excel Workbooks.'),
    dict(l='time', d='Required by brcdbapi.fos_auth and brcdbapi.brcdb_rest'),
    dict(l='warnings', d='Required for most applications'),
    dict(d=''),
    dict(d='FOS API driver libraries from github/jconsoli - brcdapi.'),
    dict(d=''),
    dict(l='brcdapi.fos_auth', d='Required by brcdapi.brcdapi_rest.', r='4.0.2'),
    dict(l='brcdapi.brcdapi_rest', d='FOS RESTConf API driver.', r='4.0.4'),
    dict(l='brcdapi.excel_util', d='Required by modules that read or write Excel workbooks', r='4.0.5'),
    dict(l='brcdapi.excel_fonts', d='Required by modules that read or write Excel workbooks', r='4.0.3'),
    dict(l='brcdapi.file', d='Required by modules that perform file I/O.', r='4.0.7'),
    dict(l='brcdapi.fos_cli', d='Required by modules that need CLI access.', r='4.0.3'),
    dict(l='brcdapi.gen_util', d='Required by most scripts.', r='4.0.9'),
    dict(l='brcdapi.log', d='Required by all scripts.', r='4.0.4'),
    dict(l='brcdapi.port', d='Required for reading and configuring ports.', r='4.0.5'),
    dict(l='brcdapi.switch', d='Required for reading and configuring switches.', r='4.0.4'),
    dict(l='brcdapi.util', d='Utilities supporting the FOS RESTConf API driver.', r='4.0.7'),
    dict(l='brcdapi.zone', d='Required by scripts performing zoning operations.', r='4.0.2'),
    dict(d=''),
    dict(d='FOS API database libraries from github/jconsoli - brcddb'),
    dict(d=''),
    dict(l='brcddb.api.interface', d='Required for all access to the API', r='4.0.5'),
    dict(l='brcddb.api.zone', d='Required for zoning applications', r='4.0.5'),
    dict(l='brcddb.apps.report', d='Required for the report.py application', r='4.0.6'),
    dict(l='brcddb.apps.zone', d='Required for the cli_zone.py application', r='4.0.3'),
    dict(l='brcddb.brcddb_bp', d='Required for the report.py application', r='4.0.5'),
    dict(l='brcddb.brcddb_chassis', d='Required for most brcddb libraries', r='4.0.7'),
    dict(l='brcddb.brcddb_common', d='Required for most applications and brcddb libraries', r='4.0.3'),
    dict(l='brcddb.brcddb_fabric', d='Required for most brcddb libraries', r='4.0.7'),
    dict(l='brcddb.brcddb_login', d='Required for most applications', r='4.0.3'),
    dict(l='brcddb.brcddb_port', d='Required for most brcddb libraries', r='4.0.5'),
    dict(l='brcddb.brcddb_project', d='Required for most brcddb libraries', r='4.0.5'),
    dict(l='brcddb.brcddb_switch', d='Required for most brcddb libraries', r='4.0.2'),
    dict(l='brcddb.brcddb_zone', d='Required for most brcddb libraries', r='4.0.4'),
    dict(l='brcddb.classes.alert', d='Required for all brcddb libraries', r='4.0.3'),
    dict(l='brcddb.classes.chassis', d='Required for all brcddb libraries', r='4.0.4'),
    dict(l='brcddb.classes.fabric', d='Required for all brcddb libraries', r='4.0.3'),
    dict(l='brcddb.classes.iocp', d='Required for all brcddb libraries', r='4.0.4'),
    dict(l='brcddb.classes.login', d='Required for all brcddb libraries', r='4.0.3'),
    dict(l='brcddb.classes.port', d='Required for all brcddb libraries', r='4.0.6'),
    dict(l='brcddb.classes.project', d='Required for all brcddb libraries', r='4.0.3'),
    dict(l='brcddb.classes.switch', d='Required for all brcddb libraries', r='4.0.5'),
    dict(l='brcddb.classes.util', d='Required for all brcddb libraries', r='4.0.3'),
    dict(l='brcddb.classes.zone', d='Required for all brcddb libraries', r='4.0.5'),
    dict(l='brcddb.util.copy', d='Required for most brcddb libraries', r='4.0.2'),
    dict(l='brcddb.util.compare', d='Required for most brcddb libraries', r='4.0.3'),
    dict(l='brcddb.util.iocp', d='Required for most brcddb libraries', r='4.0.4'),
    dict(l='brcddb.util.maps', d='Required for most brcddb libraries', r='4.0.2'),
    dict(l='brcddb.util.obj_convert', d='Required for search.py application', r='4.0.3'),
    dict(l='brcddb.util.parse_cli', d='Required for most brcddb libraries', r='4.0.7'),
    dict(l='brcddb.util.search', d='Required for most brcddb libraries', r='4.0.6'),
    dict(l='brcddb.util.util', d='Required for most brcddb libraries', r='4.0.5'),
    dict(l='brcddb.report.bp', d='Required for generating Excel reports', r='4.0.4'),
    dict(l='brcddb.report.chassis', d='Required for generating Excel reports', r='4.0.7'),
    dict(l='brcddb.report.fabric', d='Required for generating Excel reports', r='4.0.3'),
    dict(l='brcddb.report.graph', d='Required for generating Excel reports', r='4.0.2'),
    dict(l='brcddb.report.iocp', d='Required for generating Excel reports', r='4.0.4'),
    dict(l='brcddb.report.login', d='Required for generating Excel reports', r='4.0.3'),
    dict(l='brcddb.report.port', d='Required for generating Excel reports', r='4.0.4'),
    dict(l='brcddb.report.switch', d='Required for generating Excel reports', r='4.0.4'),
    dict(l='brcddb.report.utils', d='Required for generating Excel reports', r='4.0.7'),
    dict(l='brcddb.report.zone', d='Required for generating Excel reports', r='4.0.7'),
    dict(l='brcddb.app_data.alert_tables', d='Alert format tables. Required for best practice analysis.',
     r='4.0.4'),
    dict(l='brcddb.app_data.report_tables', d='Required for controlling the formats when generating Excel reports',
     r='4.0.7'),
    dict(d=''),
    dict(d='FOS API driver libraries from github/jconsoli, brcdapi, required for SANnav scripts.'),
    dict(d=''),
    dict(l='brcdapi.sannav_auth', d='Required by all SANnav scripts', r='4.0.2'),
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
    print(msg)

    # Display the operating system, version, and release
    lib_paths, operating_system, rel, ver = _get_os_and_lib_paths()
    print('OS:      ' + operating_system)
    print('Release: ' + rel)
    print('Version: ' + ver)

    # Display the lib path
    print('\nPython library path(s):\n  * ' + '\n  * '.join(lib_paths))

    summary_updates, summary_missing, modules = list(), list(), dict()
    modules['Module'] = dict(v='Version', i='Status', r='Rec Ver')
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
                    buf = 'Success'
                modules[lib] = dict(v=ver, i=buf)
            except ModuleNotFoundError:
                modules[lib] = dict(v='', i='Failed')
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
    for i in range(0, total_len + 2):
        s = s + '-'
    print(s)
    ol = [dict(l='Module', d='Description', r='Rec Ver')]
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
        print('\n\nLibraries will appear as missing if a previous required library is missing or contains errors.')
    else:
        print('Found all modules')
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
