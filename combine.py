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
redistribution, or service delivery for commerce requires an additional license. Contact jack@consoli-solutions.com for
details.

**Description**

Combines the output of multiple capture or combine files into a single project object.

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Improved error messages.                                                              |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 03 Apr 2024   | Added version numbers of imported libraries.                                          |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.3     | 06 Dec 2024   | Updated comments only                                                                 |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.4     | 25 Aug 2025   | Improve error message when the files don't exist                                      |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2023, 2024, 2025 Consoli Solutions, LLC'
__date__ = '25 Aug 2025'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.4'

import sys
import os
import datetime
import brcdapi.log as brcdapi_log
import brcdapi.gen_util as gen_util
import brcdapi.file as brcdapi_file
import brcdapi.util as brcdapi_util
import brcddb.brcddb_project as brcddb_project
import brcddb.util.copy as brcddb_copy
import brcddb.brcddb_common as brcddb_common

_DOC_STRING = False  # Should always be False. Prohibits any code execution. Only useful for building documentation
# _STAND_ALONE: True: Executes as a standalone module taking input from the command line. False: Does not automatically
# execute. This is useful when importing this module into another module that calls psuedo_main().
_STAND_ALONE = True  # See note above


_input_d = dict(
    i=dict(h='Required. Directory of captured data files. Only files with a ".json" extension are read.'),
    o=dict(h='Required. Name of combined data capture file. Placed in the folder specified by -i. The extension '
             '".json"  is automatically appended.')
)
_input_d.update(gen_util.parseargs_log_d)


def pseudo_main(inf, outf):
    """Basically the main(). Did it this way so that it can easily be used as a standalone module or called externally.

    :param inf: Name of the input folder containing capture.py or combine.py output
    :type inf: str
    :param outf: Name of the output file
    :type outf: str
    :return: Exit code
    :rtype: int
    """
    ec, el, file_l = brcddb_common.EXIT_STATUS_OK, list(), list()

    # Create project
    proj_obj = brcddb_project.new(inf, datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S'))
    proj_obj.s_python_version(sys.version)
    proj_obj.s_description('Captured data from ' + inf)

    # Get a list of files - Filter out directories is just to protect the user. It shouldn't be necessary.
    try:
        file_l = brcdapi_file.read_directory(inf)
    except FileExistsError:
        el.append('Folder ' + inf + ', specified with -i, does not exist.')
    except PermissionError:
        el.append('You do not have access rights to read the folder ' + inf + ' specified with -i')
    if outf in file_l:
        el.extend('Combined output file, ' + outf + ', already exists in: ' + inf + '. Processing halted')
    else:
        x = len('.json')
        for file in [f for f in file_l if len(f) > x and f.lower()[len(f)-x:] == '.json']:
            brcdapi_log.log('Processing file: ' + file, echo=True)
            obj = brcdapi_file.read_dump(inf + '/' + file)
            brcddb_copy.plain_copy_to_brcddb(obj, proj_obj)

        # Now save the combined file
        plain_copy = dict()
        brcddb_copy.brcddb_to_plain_copy(proj_obj, plain_copy)
        try:
            brcdapi_file.write_dump(plain_copy, inf + '/' + outf)
        except FileNotFoundError:
            el.append('Input file, ' + inf + '/' + outf + ', not found')
        except FileExistsError:
            el.append('Folder in ' + inf + '/' + outf + ' does not exist')
        except PermissionError:
            el.append('Permission error writing ' + inf + '/' + outf)

    # Wrap up
    if len(el) > 0:
        brcdapi_log.log(el, echo=True)
        ec = brcddb_common.EXIT_STATUS_INPUT_ERROR

    return ec


def _get_input():
    """Parses the module load command line

    :return ec: Error code
    :rtype ec: int
    """
    global __version__, _input_d

    ec = brcddb_common.EXIT_STATUS_OK

    # Get command line input
    args_d = gen_util.get_input('Combine the output of multiple JSON files from capture.py or this utility.', _input_d)

    # Set up logging
    brcdapi_log.open_log(
        folder=args_d['log'],
        suppress=args_d['sup'],
        no_log=args_d['nl'],
        version_d=brcdapi_util.get_import_modules()
    )

    # User feedback
    ml = [
        os.path.basename(__file__) + ', ' + __version__,
        'Directory, -i:       ' + args_d['i'],
        'Output file, -o:     ' + args_d['o'],
        'Log, -log:           ' + str(args_d['log']),
        'No log, -nl:         ' + str(args_d['nl']),
        'Suppress, -sup:      ' + str(args_d['sup']),
        '',
    ]
    brcdapi_log.log(ml, echo=True)

    return ec if ec != brcddb_common.EXIT_STATUS_OK else \
        pseudo_main(args_d['i'], brcdapi_file.full_file_name(args_d['o'], '.json'))


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
