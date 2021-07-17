#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2021 Jack Consoli.  All rights reserved.
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
:mod:`lib_validate.py` - Recursively validates access to the Python libraries for import statements

**Background**

The most common problem I ran into helping customers getting their scripts running was finding the libraries. I wrote
this script to help aid in determining why import statements were failing. Common problems that this script tries to
help identify, are:

* Imported libraries are imported from a different path than the customer thought.
* Imported libraries cannot be found
* Imported libraries are not executable
* Imported libraries import additional libraries the customer did not install

I thought about using modulefinder but I wanted to know all the library paths an import is found in. I also wanted to
read the file attributes so I cn report if the library was executable. It was easier to read the file attributes than
figuring out all the exceptions and reading the file attributes gave me more information.

I ended up plowing my way through it by recursively reading each file and looking for the import statements. Although
unlikely, it's possible to have executable rights but not read access so I attempt to import each import module even if
I couldn't read it.

**Description**

Accepts a Python module, or list of Python modules. Each module is read to extract the import statements. Each module
associated with an import statement is read. If the module is a folder then each module in the folder is read. This is
done recursively so that all required import files are determined.

The file paths and attributes are read and an import of each module to import is attempted so as to generate a report
that contains:

* A list of library search paths
* The operating system, version, and release number
* File attributes associated with each module
* Articulated list of where each imported module was imported from
* List of individual success or failure for each import
* List of all paths where an imported module can be found

**Limitations**

* Conditional imports are ignored
* Imports using importlib are ignored
* Comments preceeded with '#' are ignored but a line beginning with "import" or "from" inside tripple quote comments are
  handled as though they were not in a comment.
* Only imports from the line the import statement is included in is included. If the import statement continues to the
  next line, the imported modules from the next line are ignored.
* Internal imports are ignored (ie: from .decoder ...)
* $ToDo - Add ability to determine which file a failed import belongs to.

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 1.0.0     | 14 May 2021   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 1.0.1     | 17 Jul 2021   | Added date and time stamp. Added Python version. Added -h help message.           |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2021 Jack Consoli'
__date__ = '17 Jul 2021'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '1.0.1'

import sys
import os
import importlib
try:
    import platform
except:
    print('Could not import platform')
try:
    import datetime
    print('\n' + datetime.datetime.now().strftime('%d %b %Y %H:%M:%S'))
except:
    print('Could not import datetime')

_DOC_STRING = False  # Should always be False. Prohibits any importing. Only useful for building documentation
_DEBUG_argv = None  # ['lib_check.py', 'test_2.py']

_help_msg = ('',
                'This utility reads a Python script, or list of Python',
                'scripts, and performs the following actions:',
                '',
                '* Determines the OS, release, and version',
                '* Determines the Python library paths',
                '* Finds all import statements in the script(s)',
                '* Checks the access rights for imported scripts',
                '* Attempts to import the packages',
                '* Recursively reads all imported modules and',
                '  validates those modules as well',
                '* When available, reports the version of each',
                '  module and the specific library path actually used',
                '',
                'Example:',
                '',
                'python lib_validate.py script1.py script1.py',
                '',
                'Note: Do not use a comma to seperate multiple',
                '  scripts on the CLI. If a script has spaces in the',
                ' name, encapsulate it with quotation marks,'
                '"my scipt.py"',
                '')


def _remove_duplicates(obj_list):
    """Copy and paste from brcddb.util.util.remove_duplicates()"""
    seen = set()
    seen_add = seen.add  # seen.add isn't changing so making it local makes the next line more efficient
    return [obj for obj in obj_list if not (obj in seen or seen_add(obj))]


def _lib_search(lib_d, folder, file, f_flag=False):
    """Search for modules in lib_d and returns the file attribute dictionary for the file

    :param lib_d: Dictionary of files and folders for all library paths
    :type lib_d: dict
    :param folder: Folder where to look for file
    :type folder: str
    :param file: Name of file or folder to look for
    :type file: str
    :param f_flag: If True and file is a folder, return the attributes for all files in that folder
    :type f_flag: bool
    :return: A list file attributes, one for each .py file, associated with file.
    :rtype: list
    """
    rl = list()

    temp_l = file.split('.')
    if len(temp_l) == 0 or temp_l[0] == 'os':
        return rl
    last_file = temp_l.pop()
    sub_folder = '\\'.join(temp_l)

    search_d = _get_d(lib_d, folder.split('\\') + temp_l)
    if search_d is None:
        return rl
    file_d = search_d['file'].get(last_file + '.py')
    if isinstance(file_d, dict):
        rl.append(file_d)
    elif f_flag:
        folder_d = search_d['folder'].get(last_file)
        if folder_d is not None:
            rl.extend(folder_d['file'].values())

    return rl


def _import_file_report(lib_d, lib_l, import_files):
    """
    :param lib_d: Dictionary of files and folders for all library paths
    :type lib_d: dict
    :param lib_l: Path list
    :type lib_l: list
    :param import_files: List of modules to import
    :type import_files: list
    :return: None
    :rtype: None
    """
    print('\nFile permissions (attr) follow standard Linux rwx format + f for')
    print('file access. Permissions are from the user perspective and often')
    print('wrong in Windows environments. As long as a module imported')
    print('successfully, there is no problem.')
    for lib in import_files:
        print('\n' + lib)

        # Try to import it
        ver = ''
        path = ''
        try:
            mod = importlib.import_module(lib)
            print('  Import:    Success')
            try:
                ver = mod.__version__
            except:
                pass
            try:
                path = os.path.abspath(mod.__file__)
            except:
                pass
        except:
            print('  Import:    Failed')

        # Write out the file attributes
        print('  Version:   ' + ver)
        print('  Path used: ' + path)
        for lib_folder in lib_l:
            file_d_l = _lib_search(lib_d, lib_folder, lib, True)
            if len(file_d_l) > 0:
                print('  Lib path:  ' + lib_folder)
                for d in file_d_l:
                    attr = 'r' if d['permission_r'] else '-'
                    attr += 'w' if d['permission_w'] else '-'
                    attr += 'x' if d['permission_x'] else '-'
                    attr += 'f' if d['permission_f'] else '-'
                    print('    ' + attr + ' ' + os.path.join(d['folder'], d['name']))


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


def _build_list(base_d, file_l):
    for file_d in file_l:
        current_d = base_d
        file_name = file_d['name']
        if len(file_name) > len('.py') and file_name.lower()[len(file_name)-len('.py'):] == '.py':
            d = None
            for folder in file_d['folder'].split('\\'):
                if folder == '__pycache__':
                    d = None
                    break
                d = current_d['folder'].get(folder)
                if d is None:
                    d = dict(folder=dict(), file=dict())
                    current_d['folder'].update({folder: d})
                current_d = d
            if isinstance(d, dict):
                d['file'].update({file_name: file_d})


def file_properties(folder, file):
    """This is  a copy and paste of brcddb.util.file.file_properties()"""
    stats = os.stat(os.path.join(folder, file))
    return dict(
        name=file,
        folder=folder,
        st_atime=stats.st_atime,
        st_ctime=stats.st_ctime,
        st_mtime=stats.st_mtime,
        st_size=stats.st_size,
        st_mode=stats.st_mode,
        st_ino=stats.st_ino,
        st_dev=stats.st_dev,
        st_nlink=stats.st_nlink,
        st_uid=stats.st_uid,
        st_gid=stats.st_gid,
        permission_r=os.access(file, os.R_OK),
        permission_w=os.access(file, os.W_OK),
        permission_x=os.access(file, os.X_OK),
        permission_f=os.access(file, os.F_OK)
    )


def read_file(file, remove_blank=True, rc=True):
    """This is  a copy and paste of brcddb.util.file.read_file()"""
    f = open(file, 'rb')
    data = f.read().decode('utf-8', errors='ignore')
    f.close()
    content = data.replace('\r', '').split('\n')
    rl = [buf[:buf.find('#')].rstrip() if buf.find('#') >= 0 else buf.rstrip() for buf in content] if rc else content
    return [buf for buf in rl if len(buf) > 0] if remove_blank else [buf for buf in rl]


def read_directory(folder):
    """This is  a copy and paste of brcddb.util.file.read_directory()"""
    rl = list()
    try:
        for file in os.listdir(folder):
            full_path = os.path.join(folder, file)
            try:
                if os.path.isfile(full_path) and '~$' not in file:
                    rl.append(file)
            except:
                pass  # It's probably a system file
    except:
        pass  # It's a protected folder. Usually system folders

    return rl


def read_full_directory(folder, skip_sys=False):
    """This is  a copy and paste of brcddb.util.file.read_full_directory()"""
    rl = list()

    # All the files
    for file in read_directory(folder):
        rl.append(file_properties(folder, file))

    # Recursively look through all the folders
    temp_l = list()
    try:
        temp_l = [os.path.join(folder, f) for f in os.listdir(folder)]
    except:
        pass  # It's a protected folder. Usually system folders
    folder_l = list()
    for new_folder in [f for f in temp_l if not os.path.isfile(f)]:
        try:
            full_path = os.path.join(folder, new_folder)
            if os.listdir(full_path):
                if '~$' not in new_folder:  # '-$' is a temporary Windows file that sometimes shows up
                    if not skip_sys or (len(new_folder) > 0 and new_folder[0] != '$'):
                        folder_l.append(full_path)
        except:
            pass  # This happens when the user doesn't have access to a file system
    for new_folder in folder_l:
        rl.extend(read_full_directory(new_folder, skip_sys=True))

    return rl


def _python_ver():
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
        except:
            msg += '\nInvalid version returned from sys.version'
    except:
        msg += 'Unable to read sys.version'

    return msg


def _get_d(lib_d, dl):
    d = lib_d
    for key in dl:
        d = d['folder'].get(key)
        if d is None:
            break

    return d


def _clean_import_line(in_buf):
    rl = list()

    if in_buf[0: len('import ')] == 'import ' or in_buf[0: len('from ')] == 'from ':

        # Clean up the input line: remove parenthesis and duplicated spaces
        len_buf = len(in_buf)
        buf = in_buf.replace('(', ' ').replace('(', ' ').replace('  ', ' ')
        while len(buf) != len_buf:  # Remove duplicate spaces
            len_buf = len(buf)
            buf = buf.replace('  ', ' ')
        # remove anything in the line from 'as' and thereafter
        temp_l = buf.split(' ')
        for i in range(0, len(temp_l)):
            if temp_l[i] == 'as':
                buf = ' '.join(temp_l[0:i])
                break

        if buf[0: len('import ')] == 'import ':
            rl.extend([b for b in buf.split(' ')[1].split(',') if len(b) > 0])
        elif buf[0: len('from ')] == 'from ':
            temp_l = buf.split(' ')
            from_path = temp_l[1]
            if len(from_path) > 0 and from_path[0] != '.':
                rl.append(from_path)  # Just import the package

    return rl


def _recursive_imports(lib_d, lib_l, cant_read_l, folder, file, in_file_d=None):
    """Finds all import statements in file, looks for those files in the lib_l paths, and recursively reads those files

    :param lib_d: Dictionary of files and folders for all library paths
    :type lib_d: dict
    :param lib_l: Path list
    :type lib_l: list
    :param cant_read_l: List of import files we attempted to read but couldn't
    :type cant_read_l: list
    :param folder: Starting folder where to look for file
    :type folder: str
    :param file: Name of file to read
    :type file: str
    :param in_file_d: File dict structure for file. None if not known.
    :type in_file_d: dict, None
    :return: List of modules to import
    :rtype: list
    """
    rl = list()

    if in_file_d is not None and in_file_d.get('_read') is not None and in_file_d.get('_read'):
        return rl  # We already read this file

    # Get a list of all the files from import statements in file
    try:
        content = read_file(os.path.join(folder, file), remove_blank=True, rc=True)
        if isinstance(in_file_d, dict):
            in_file_d.update(dict(_read=True))  # Different modules often import the same libraries. Only check once
        for buf in [b for b in content if 'import ' in b]:
            rl.extend(_clean_import_line(buf))
    except:
        if in_file_d is None:
            cant_read_l.append(file)
        else:
            in_file_d.update(dict(_cant_read=True))

    # Read all the imported files
    for lib_folder in lib_l:

        # Debug
        if 'JetBrains' in lib_folder:
            continue

        for import_file in rl:
            for file_d in _lib_search(lib_d, lib_folder, import_file, True):
                rl.extend(_recursive_imports(lib_d, lib_l, cant_read_l, file_d['folder'], file_d['name'], file_d))

    return rl


def pseudo_main():
    """Basically the main().
    :return: Exit code
    :rtype: int
    """
    global __version__

    # Get the command line input.
    if _DEBUG_argv is not None:
        print('WARNING: Debug mode.')
    try:
        temp_l = sys.argv if _DEBUG_argv is None else _DEBUG_argv
    except:
        print('Can\'t find sys library')
        return
    argv = list()
    print('\nTEST\n')
    for buf in temp_l:
        argv.extend([b.strip() for b in buf.split(',') if len(b.strip()) > 0])
        if buf == '-h':
            print('\n'.join(_help_msg))
            return
    print('Input arguments (scripts to validate):')
    if len(argv) > 1:
        for buf in argv:
            print(buf)
    else:
        print('No scripts specified. Only the operating')
        print('system and library paths will be determined')

    # Print a description of what this module does, version, and operating system information
    print(argv.pop(0) + ' version: ' + __version__ + '\n')
    lib_paths, operating_system, rel, ver = _get_os_and_lib_paths()
    print('OS:      ' + operating_system)
    print('Release: ' + rel)
    print('Version: ' + ver)

    # Python version
    print(_python_ver())

    # Find and validate all import statements
    lib_d = dict(folder=dict(), file=dict())  # Put all files and folders in a dictionary for easier lookup
    print('\nLibrary paths (These checks can take several minutes):')
    ml = list()
    for buf in lib_paths:
        temp_l = read_full_directory(buf)
        if len(temp_l) == 0:
            ml.append(buf)
        else:
            _build_list(lib_d, temp_l)
            print(buf)
    if len(ml) > 0:
        print('Included in the path but no user accessible files found in:\n  ' + '\n  '.join(ml))

    import_files = list()
    input_file_l = list()
    cant_read_list = list()
    for file in argv:
        input_file_l.append(file_properties('', file))
        import_files.extend(_recursive_imports(lib_d, lib_paths, cant_read_list, '', file, None))

    print('\nTest files:')
    for d in input_file_l:
        print('\n' + d['name'])
        print('  Executable:    ' + 'Yes' if d['permission_x'] else 'No. You cannot run this script.')
        print('  Readable:      ' + 'Yes' if d['permission_r'] else 'No. Cannot validate imports.')
        print('  Write Access:  ' + 'Yes' if d['permission_w'] else 'No. You cannot modify this script.')
        print('  Folder access: ' + 'Yes' if d['permission_f'] else
              'No. You do not have permission to access this folder.')

    if len(cant_read_list) > 0:
        print('\nCould not read the following imported modules:')
        for file in cant_read_list:
            print('  ' + file)

    _import_file_report(lib_d, lib_paths, _remove_duplicates(import_files))


###################################################################
#
#                    Main Entry Point
#
###################################################################
if not _DOC_STRING:
    pseudo_main()
