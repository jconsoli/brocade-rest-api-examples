#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Copyright 2025 Consoli Solutions, LLC.  All rights reserved.

**License**

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
the License. You may also obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
language governing permissions and limitations under the License.

The license is free for single customer use (internal applications). Use of this module in the production,
redistribution, or service delivery for commerce requires an additional license. Contact jack_consoli@yahoo.com for
details.

**Description**

Search files using exact, wild card, or ReGex searching. Intended for Windows where searching tools are minimal. I'm
sure someone has a tool like this somewhere, but I couldn't find one.

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 1.0.0     | xx xxx 2025   | Initial Launch                                                                        |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2025 Consoli Solutions, LLC'
__date__ = 'xx xxx 2025'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Development'
__version__ = '1.0.0'

import os
import collections
import re

from pypdf import PdfReader
import brcdapi.log as brcdapi_log
import brcdapi.gen_util as gen_util
import brcdapi.util as brcdapi_util
import brcdapi.file as brcdapi_file
import brcddb.brcddb_common as brcddb_common

from pypdf.errors import PdfReadError

_DOC_STRING = False  # Should always be False. Prohibits any code execution. Only useful for building documentation

# _STAND_ALONE: True: Executes as a standalone module taking input from the command line. False: Does not automatically
# execute. This is useful when importing this module into another module that calls psuedo_main().
_STAND_ALONE = True  # See note above

_search_type_d = dict(wild='wild', regex_m='regex-m', regex_s='regex-s', exact='exact')
_search_type_l = [str(_b) for _b in _search_type_d.keys()]
_input_d = collections.OrderedDict()
_input_d.update(
    path=dict(r=False, d='.', h='Optional. Directory path to search in. If omitted, searches the current directory.'),
    t=dict(h='Required. Search term (pattern) to find in the files. Use of ReGex and wild cards is '
             'supported with -s. Enclose in quotes if the search string includes characters the command line '
             'interpreter interprets as a parameter seperator, such as a space.'),
    s=dict(r=False, d='regex_s', v=_search_type_l,
           h='Optional. Search type associated with -t. Options are: ' + ', '.join(_search_type_l) +
             ' The default is "regex_s". Keep in mind that the search is on the entire line, so exact means the entire '
             'line must match.'),
    c=dict(r=False, d=False, t='bool', h='Optional. If specified, ignore comments.'),
    ic=dict(r=False, d=False, t='bool', h='Optional. If specified, ignore case.'),
    fic=dict(r=False, d=False, t='bool', h='Optional. Ignore case in file search.'),
    ft=dict(r=False,
            h='Optional. Similar to -t but used on the names of files to search. If omitted, all files are read.'),
    fs=dict(r=False, d='wild', v=_search_type_l,
            h='Optional. Same as -s but used on the names of files to search. Ignored if -ft is not specified. The '
              'default is "wild".'),
    sub=dict(r=False, d=False, t='bool', h='Optional. If specified, include sub-directories in search.'),
    sum=dict(r=False, d=False, t='bool', h='Optional. If specified, display the file names only in the results.'),
)
_input_d.update(gen_util.parseargs_log_d.copy())

_MAX_FINDS = 500


def pseudo_main(file_l, search_term, search_type, ignore_comments, ignore_case, summary):
    """Basically the main(). Did it this way so that it can easily be used as a standalone module or called externally.

    :param file_l: List of files to search
    :type file_l: list
    :param search_term: What to search for
    :type search_term: str
    :param search_type: Search type. See _search_type_l for valid types.
    :type search_type: str
    :param ignore_comments: If True, ignore comments
    :type ignore_comments: bool
    :param ignore_case: If True, ignore case
    :type ignore_case: bool
    :param summary: If True, display the file names only in the output
    :type summary: bool
    :return: Exit code. See exist codes in brcddb.brcddb_common
    :rtype: int
    """
    global _MAX_FINDS

    ec, ml = brcddb_common.EXIT_STATUS_OK, list()

    for file in file_l:
        content_l = list()
        try:
            if file.split('.')[-1].lower() == 'pdf':
                for page in PdfReader(file).pages:
                    content_l.extend(page.extract_text().split('\n'))
            else:
                content_l = brcdapi_file.read_file(file, remove_blank=True, rc=ignore_comments)
        except (FileNotFoundError, FileExistsError, PermissionError):
            continue
        except PdfReadError:
            brcdapi_log.log('Error reading : ' + file + '. Skipped')
        except Exception as e:
            brcdapi_log.log(['Unknown error: ' + str(e), '  while processing ' + file])
        try:
            temp_l = gen_util.match_str(content_l, search_term, ignore_case=ignore_case, stype=search_type)
        except re.error:
            if 'regex' in search_type and '*' in search_term:
                buf_l = ['',
                         'ReGex library error.',
                         'Search term, -t: ' + search_term,
                         'Search type, -s: ' + search_type,
                         'An "*" was used in the search term, -t, but not followed with anything to repeat. This '
                         'typically happens when "wild" was the intended search type. Keep in mind that the default '
                         'serach type is "regex_s".']
            else:
                buf_l = ['Unknown ReGex library error.']
            brcdapi_log.log(buf_l, echo=True)
            return brcddb_common.EXIT_STATUS_INPUT_ERROR
        if len(temp_l) > 0:
            ml.append(file)
            if not summary:
                ml.extend(['  ' + b for b in temp_l[0:_MAX_FINDS]])
                x = len(temp_l) - _MAX_FINDS
                if x > 0:
                    ml.append('  + ' + str(x) + ' more.')

    # Display the result
    ml.extend(['', 'Total matches: ' + str(len(ml)), ''])
    brcdapi_log.log(ml, echo=True)

    return ec


def _get_input():
    """Parses the module load command line

    :return ec: Error code
    :rtype ec: int
    """
    global __version__, _input_d

    ec, path_help, file_l = brcddb_common.EXIT_STATUS_OK, '', list()

    # Get command line input
    try:
        args_d = gen_util.get_input('File search.', _input_d)
    except TypeError:
        return brcddb_common.EXIT_STATUS_INPUT_ERROR  # gen_util.get_input() already posted the error message.

    # Set up logging
    brcdapi_log.open_log(
        folder=args_d['log'],
        suppress=args_d['sup'],
        no_log=args_d['nl'],
        version_d=brcdapi_util.get_import_modules()
    )

    # Get a list of files that match the search criteria.
    full_l, file_l = list(), list()
    if args_d['sub']:
        try:
            full_l = brcdapi_file.read_full_directory(args_d['path'], skip_sys=True)
        except FileNotFoundError:
            if len(full_l) == 0:
                ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
                path_help = '**ERROR** Path does not exist.'
        except PermissionError:
            if len(full_l) == 0:
                ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
                path_help = '**ERROR** Permission error.'
        for d in full_l:
            try:
                name, folder = d['name'], d['folder']
            except KeyError:
                continue  # The file system is broke if we get here. We're not debugging the file system.
            temp_l = [name]
            if isinstance(args_d['ft'], str):
                temp_l = gen_util.match_str(temp_l, args_d['ft'], ignore_case=args_d['ic'], stype=args_d['fs'])
            for temp_name in temp_l:
                file_l.append(folder + '\\' + temp_name)
    else:
        try:
            if isinstance(args_d['ft'], str):
                temp_l = gen_util.match_str(brcdapi_file.read_directory(args_d['path']),
                                            args_d['ft'],
                                            ignore_case=args_d['ic'],
                                            stype=args_d['fs'])
                file_l = [args_d['path'] + '\\' + f for f in temp_l]
            else:
                file_l = [args_d['path'] + '\\' + f for f in brcdapi_file.read_directory(args_d['path'])]
        except (FileExistsError, FileNotFoundError):
            if len(file_l) == 0:
                ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
                path_help = ' **ERROR** Path does not exist.'
        except PermissionError:
            if len(file_l) == 0:
                ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
                path_help = ' **ERROR** Permission denied.'

    # Command line feedback
    ml = [
        os.path.basename(__file__) + ', ' + __version__,
        'Search path, -path:            ' + str(args_d['path']) + path_help,
        'Search term (pattern), -t:     ' + str(args_d['t']),
        'Search type, -s:               ' + args_d['s'],
        'Ignore comments, -c:           ' + str(args_d['c']),
        'Ignore case, -ic:              ' + str(args_d['ic']),
        'File ignore case, -fic:        ' + str(args_d['fic']),
        'File search term, -ft:         ' + str(args_d['ft']),
        'Include sub-directories, -sub: ' + str(args_d['sub']),
        'Log, -log:                     ' + str(args_d['log']),
        'No log, -nl:                   ' + str(args_d['nl']),
        'Suppress, -sup:                ' + str(args_d['sup']),
        'Summary, -sum:                 ' + str(args_d['sum']),
        'Matching files to search:      ' + str(len(file_l)),
        '',
        ]
    brcdapi_log.log(ml, echo=True)

    return ec if ec != brcddb_common.EXIT_STATUS_OK else \
        pseudo_main(file_l, args_d['t'], args_d['s'], args_d['c'], args_d['ic'], args_d['sum'])


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
