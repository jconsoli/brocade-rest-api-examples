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

Methods to create and manage logging content.

Automatically creates a log as soon as it is imported with a time stamp in the log file name if not already open.
Although the Python libraries automatically close all open file handles upon exit, there is a close_log() method to
flush and close the file. This is not only useful for traditional programmers who want a greater degree of program
control, but useful in conjunction with control programs such as Ansible whereby printing to STD_OUT needs to be
suppressed for all log messages except the final completion message.

**Public Methods**

+-----------------------+-------------------------------------------------------------------------------------------+
| Method                | Description                                                                               |
+=======================+===========================================================================================+
| open_log              | Creates a log file. If the log file is already open, it is closed and a new one created.  |
+-----------------------+-------------------------------------------------------------------------------------------+
| close_log             | Closes the log file                                                                       |
+-----------------------+-------------------------------------------------------------------------------------------+
| log                   | Writes a message to the log file and optionally echos the message to STD_OUT              |
+-----------------------+-------------------------------------------------------------------------------------------+
| exception             | Prints the traceback followed by the message. Optionally echoed to STD_OUT                |
+-----------------------+-------------------------------------------------------------------------------------------+
| flush                 | Flushes (writes) the contents of the log file cache to storage                            |
+-----------------------+-------------------------------------------------------------------------------------------+
| set_suppress_all      | Suppress all output except forced output. Useful with a playbook when only exit statis is |
|                       | desired                                                                                   |
+-----------------------+-------------------------------------------------------------------------------------------+
| clear_suppress_all    | Clears suppress all flag. See set_suppress_all()                                          |
+-----------------------+-------------------------------------------------------------------------------------------+
| is_prog_suppress_all  | Returns the status of the "suppress all" flag                                             |
+-----------------------+-------------------------------------------------------------------------------------------+

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Documentation updates only.                                                           |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 03 Apr 2024   | Added version_d to open_log()                                                         |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.3     | 06 Dec 2024   | Try/Except in log() to get around PyCharm issue with special characters.              |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2023, 2024 Consoli Solutions, LLC'
__date__ = '06 Dec 2024'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack@consoli-solutions.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.3'

import traceback
import datetime

_local_suppress_all = False
_log_obj = None  # Log file handle


def set_suppress_all():
    """Suppress all output except forced output. Useful with a playbook when only exit status is desired
    """
    global _local_suppress_all
    _local_suppress_all = True


def clear_suppress_all():
    """Clears suppress all flag. See set_suppress_all()
    """
    global _local_suppress_all
    _local_suppress_all = False


def is_prog_suppress_all():
    """Returns the status of the "suppress all" flag

    :return: Flag state for _local_suppress_all
    :rtype: bool
    """
    global _local_suppress_all
    return _local_suppress_all


def log(msg, echo=False, force=False):
    """Writes a message to the log file and optionally echos the message to STD_OUT

    :param msg: Message to be printed to the log file
    :type msg: str, list
    :param echo: If True, also echoes message to STDOUT. Default is False
    :type echo: bool
    :param force: If True, ignores is_prog_suppress_all(). Useful for only echoing exit codes.
    :type force: bool
    :return: None
    """
    global _log_obj

    ml = msg if isinstance(msg, list) else [msg]
    buf = '\n'.join([str(b) for b in ml])
    if _log_obj is not None:
        try:
            _log_obj.write('\n# Log date: ' + datetime.datetime.now().strftime('%Y-%m-%d time: %H:%M:%S') + '\n' + buf)
        except UnicodeEncodeError:
            log_buf = '\n# Log date: ' + datetime.datetime.now().strftime('%Y-%m-%d time: %H:%M:%S') + '\nEncode Error'
            _log_obj.write(log_buf)
    if echo and (not is_prog_suppress_all() or force):
        print(buf)


def flush():
    """Flushes (writes) the contents of the log file cache to storage
    """
    global _log_obj

    if _log_obj is not None:
        _log_obj.flush()


def exception(msg, echo=False):
    """Prints the traceback followed by the message. Optionally echoed to STD_OUT

    :param msg: Message to be printed to the log file
    :type msg: str, list
    :param echo: If True, also echoes message to STDOUT
    :type echo: bool
    :return: None
    """
    msg_list = ['brcdapi library exception call. Traceback:']
    msg_list.extend([buf.rstrip() for buf in traceback.format_stack()])  # rstrip() because log() adds a line feed
    msg_list.extend(msg if isinstance(msg, list) else [msg])
    log(msg_list, echo)
    flush()


def close_log(msg=None, echo=False, force=False):
    """Closes the log file

    :param msg: Final message to be printed to the log file
    :type msg: str, None
    :param echo: If True, also echoes msg to STDOUT
    :type echo: bool
    :param force: If True, ignores is_prog_suppress_all(). Useful for only echoing exit codes.
    :type force: bool
    :return: None
    """
    global _log_obj

    if msg is not None:
        log(msg, echo, force)
    if _log_obj is not None:
        _log_obj.close()
        _log_obj = None


def open_log(folder=None, suppress=False, no_log=False, version_d=None, supress=None):
    """Creates a log file. If the log file is already open, it is closed and a new one created.

    :param folder: Directory for the log file.
    :type folder: str, None
    :param suppress: If True, suppresses all output to STD_IO
    :type suppress: None, bool
    :param no_log: If True, do not open the log file
    :type no_log: None, bool
    :param version_d: Dictionary of imported modules and version numbers
    :type version_d: None,dict
    :param supress: Depracated due to misspelling
    :type supress: None, bool
    :rtype: None
    """
    global _log_obj

    in_version_d = dict() if version_d is None else version_d
    if supress is not None:
        suppress = supress

    # Figure out what the log file name is
    log_file = 'Log_' + datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f') + '.txt'
    folder_name = '' if folder is None else folder + '/'
    file_name = folder_name + log_file

    if suppress:
        set_suppress_all()
    if no_log:
        return

    # Get a handle for the log file. If the log file is already open, close it and open a new one
    if _log_obj is not None:
        close_log('Closing this file and opening a new log file: ' + file_name, False, False)

    el = list()  # Error messages
    try:
        _log_obj = open(file_name, 'w')
        el.append('Successfully opened log file: ' + file_name)
        el.extend([str(k) + ': ' + str(v) for k,v in in_version_d.items()])
        log(el)
        return
    except FileNotFoundError:
        el.append(folder + ' Does not exist.')
    except PermissionError:
        el.append('You do not have access to the log folder, ' + folder + '.')

    # Opening the log file failed if the script ran this far. Try opening the log file in the current directory.
    if len(folder_name) > 0:
        el.append('Attempting to open log file in local directory.')
        try:
            _log_obj = open(log_file, 'w')
            el.append('Successfully opened log file in local directory')
            log(el, echo=True)
            log([str(k) + ': ' + str(v) for k, v in in_version_d.items()])
            return
        except PermissionError:
            el.append('Write access permission was not granted. All processing terminated.')

    # The log file couldn't be opened if the script ran this far.
    for buf in el:
        print(buf)
    exit(0)
