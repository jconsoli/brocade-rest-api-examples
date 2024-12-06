"""
Copyright 2023, 2024 Consoli Solutions, LLC.  All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
the License. You may also obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
language governing permissions and limitations under the License.

The license is free for single customer use (internal applications). Use of this module in the production,
redistribution, or service delivery for commerce requires an additional license. Contact jack@consoli-solutions.com for
details.

**Description**

General purpose file operations.

**Public Methods & Data**

+-----------------------+-------------------------------------------------------------------------------------------+
| Method                | Description                                                                               |
+=======================+===========================================================================================+
| file_properties       | Reads the file properties into a dictionary                                               |
+-----------------------+-------------------------------------------------------------------------------------------+
| full_file_name        | Checks to see if an extension is already in the file name and adds it if necessary        |
+-----------------------+-------------------------------------------------------------------------------------------+
| read_directory        | Reads in the contents of a folder (directory) and return the list of files only (no       |
|                       | directories) in that folder                                                               |
+-----------------------+-------------------------------------------------------------------------------------------+
| read_dump             | Reads in a file with JSON formatted data and loads into a Python object.                  |
+-----------------------+-------------------------------------------------------------------------------------------+
| read_file             | Reads a file, comments and blank lines optionally removed, and trailing white space       |
|                       | removed into a list                                                                       |
+-----------------------+-------------------------------------------------------------------------------------------+
| read_full_directory   | Beginning with folder, reads the full content of a folder and puts all file names and     |
|                       | stats in a list of dict                                                                   |
+-----------------------+-------------------------------------------------------------------------------------------+
| write_dump            | Converts a Python object to JSON and writes it to a file.                                 |
+-----------------------+-------------------------------------------------------------------------------------------+
| write_file            | Write a list of strings to a file                                                         |
+-----------------------+-------------------------------------------------------------------------------------------+

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Documentation updates only.                                                           |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 03 Apr 2024   | Added write_file(). Added dot parameter to full_file_name()                           |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.3     | 15 May 2024   | Fixed full_file_name() when dot is False and the file name has a '.' in it.           |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.4     | 20 Oct 2024   | Fixed typo in error message                                                           |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.5     | 06 Dec 2024   | Skip inaccessible files in read_full_directory().                                     |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2023, 2024 Consoli Solutions, LLC'
__date__ = '06 Dec 2024'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack@consoli-solutions.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.5'

import json
import os


def write_dump(obj, file):
    """Converts a Python object to JSON and writes it to a file.

    :param obj: Dictionary to write to file
    :type obj: dict, list
    :param file: Name of file to write to
    :type file: str
    :rtype: None
    """
    with open(file, 'w') as f:
        f.write(json.dumps(obj, sort_keys=True))
    f.close()


def read_dump(file):
    """Reads in a file with JSON formatted data and loads into a Python object.

    :param file: Name of JSON file to read
    :type file: str
    :return: The JSON file converted to standard Python data types. None if an error was encountered
    :rtype: dict, list, None
    """
    f = open(file, 'r')
    obj = json.load(f)
    f.close()

    return obj


def read_directory(folder):
    """Reads in the contents of a folder (directory) and returns the list of files only (no directories) in that folder

    :param folder: Name of the folder
    :type folder: str
    :return: List of file names in the folder. List is empty if the folder doesn't exist
    :rtype: str
    """
    rl = list()
    if folder is not None:
        try:
            for file in os.listdir(folder):
                full_path = os.path.join(folder, file)
                try:
                    if os.path.isfile(full_path) and len(file) > 2 and file[0:2] != '~$':
                        rl.append(file)
                except PermissionError:
                    pass  # It's probably a system file
        except PermissionError:
            pass  # It's a protected folder. Usually system folders
        except FileNotFoundError:
            pass

    return rl


def read_director(folder):
    """To support old misspelled method name."""
    return read_directory(folder)


def read_file(file, remove_blank=True, rc=True):
    """Reads a file, comments and blank lines optionally removed, and trailing white space removed into a list

    :param file: Full path with name of file to read
    :type file: str
    :param remove_blank: If True, blank lines are removed
    :type remove_blank: bool
    :param rc: If True, remove anything beginning with # to the end of line
    :type rc: bool
    :return: File contents.
    :rtype: list
    """
    # Apparently, Putty puts some weird characters in the file. Looks like there is a Python bug with the line below. I
    # get "NameError: name 'open' is not defined".
    # f = open(file, 'r', encoding='utf-8', errors='ignore')
    #  So I read as bytes, decoded using utf-8 and then had to ignore errors.
    f = open(file, 'rb')
    data = f.read().decode('utf-8', errors='ignore')
    f.close()

    # Every once in a while, a Windows file has just '\r' for the line end. I've never seen '\n\r' but just in case...
    content = data.replace('\r\n', '\n').replace('\n\r', '\n').replace('\r', '\n').split('\n')
    rl = [buf[:buf.find('#')].rstrip() if buf.find('#') >= 0 else buf.rstrip() for buf in content] if rc else content
    return [buf for buf in rl if len(buf) > 0] if remove_blank else rl


def write_file(file, content_l):
    """Write a list of strings to a file

    :param file: Full path with name of file to write
    :type file: str
    :param content_l: List of strings to write to file
    :type content_l: list
    :return: Error messages.
    :rtype: list
    """
    el = list()
    try:
        with open(file, 'w') as f:
            f.write('\n'.join(content_l))
        f.close()
    except FileExistsError:
        el.append('A folder in ' + file + ' does not exist.')
    except PermissionError:
        el.append('You do not have permission to write ' + file + '.')
    except BaseException as e:
        el.extend(['Unexpected error while writing ' + str(file), str(type(e)) + str(e)])
    return el


def file_properties(folder, file):
    """Reads the file properties and returns the following dictionary:

    +---------------+-------+---------------------------------------------------------------------------+
    | key           | type  | Description                                                               |
    +===============+=======+===========================================================================+
    | name          | str   | File name                                                                 |
    +---------------+-------+---------------------------------------------------------------------------+
    | folder        | str   | Folder name, relative to passed param folder.                             |
    +---------------+-------+---------------------------------------------------------------------------+
    | st_atime      | float | Last access time (epoch time).                                            |
    +---------------+-------+---------------------------------------------------------------------------+
    | st_ctime      | float | Creation time (epoch time)                                                |
    +---------------+-------+---------------------------------------------------------------------------+
    | st_mtime      | float | Last time modified (epoch time)                                           |
    +---------------+-------+---------------------------------------------------------------------------+
    | st_size       | int   | File size in bytes                                                        |
    +---------------+-------+---------------------------------------------------------------------------+
    | st_mode       | int   | File mode, see os.stat()                                                  |
    +---------------+-------+---------------------------------------------------------------------------+
    | st_ino        | int   | File mode, see os.stat()                                                  |
    +---------------+-------+---------------------------------------------------------------------------+
    | st_dev        | int   | File mode, see os.stat()                                                  |
    +---------------+-------+---------------------------------------------------------------------------+
    | st_nlink      | int   | File mode, see os.stat()                                                  |
    +---------------+-------+---------------------------------------------------------------------------+
    | st_uid        | int   | File mode, see os.stat()                                                  |
    +---------------+-------+---------------------------------------------------------------------------+
    | st_gid        | int   | See os.stat()                                                             |
    +---------------+-------+---------------------------------------------------------------------------+
    | permission_r  | bool  | True if file is readable. Same as os.R_OK. Not valid for Windows          |
    +---------------+-------+---------------------------------------------------------------------------+
    | permission_w  | bool  | True if file is writeable. Same as os.W_OK. Not valid for Windows         |
    +---------------+-------+---------------------------------------------------------------------------+
    | permission_x  | bool  | True if file is executable. Same as os.X_OK. Not valid for Windows        |
    +---------------+-------+---------------------------------------------------------------------------+
    | permission_f  | bool  | True if user has path access to file. Same as os.F_OK. Not valid for      |
    |               |       | Windows                                                                   |
    +---------------+-------+---------------------------------------------------------------------------+

    :param folder: Folder containing file
    :type folder: str
    :param file: Name of file to read
    :type file: str
    :return: See dictionary definition above in the function description.
    :rtype: dict
    """
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


def read_full_directory(folder, skip_sys=False):
    """Beginning with folder, reads the full content of a folder and puts all file names and stats in a list of dict

    :param folder: Name of the directory to read
    :type folder: str
    :param skip_sys: If True, skip any file or folder that begins with '$' or '~'
    :param skip_sys: bool
    :return rl: List of properties dictionaries (as returned from file_properties) for each file as described above.
    :rtype rl: list
    """
    rl = list()
    try:
        for file in os.listdir(folder):
            if skip_sys and len(file) > 1 and (file[0:1] == '$' or file[0:1] == '~'):
                continue
            full_path = os.path.join(folder, file)
            if os.path.isfile(full_path):
                rl.append(file_properties(folder, file))
            else:
                rl.extend(read_full_directory(full_path, skip_sys))
    except (FileExistsError, FileNotFoundError, PermissionError):
        pass

    return rl


def full_file_name(file, extension, prefix=None, dot=False):
    """Checks to see if an extension is already in the file name and adds it if necessary

    :param file: File name. If None, None is returned
    :type file: str, None
    :param extension: The file extension
    :type extension: str
    :param prefix: A prefix to add. Typically, a folder name. If a folder, don't forget the last character must be '/'
    :type prefix: None, str
    :param dot: If True, return file as is if there is a "." in it.
    :type dot: bool
    :return: File name with the extension and prefix added
    :rtype: str
    """
    if isinstance(file, str):
        if not dot or (dot and '.' not in file):
            x = len(extension)
            p = '' if prefix is None else prefix
            return p + file + extension if len(file) < x or file[len(file)-x:].lower() != extension.lower() \
                else p + file
    return file
