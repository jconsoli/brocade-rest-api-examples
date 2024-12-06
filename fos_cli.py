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

Methods to login via SSH, send  commands, and logout.

**WARNING**

This module was written as an expedient to handle a few commands for things not yet supported via the API. It doesn't
do anything with prompts and doesn't perform any error checking.
**Public Methods & Data**

+-----------------------+-------------------------------------------------------------------------------------------+
| Method                | Description                                                                               |
+=======================+===========================================================================================+
| login                 | Performs an SSH login                                                                     |
+-----------------------+-------------------------------------------------------------------------------------------+
| logout                | Logout of an SSH session                                                                  |
+-----------------------+-------------------------------------------------------------------------------------------+
| send_command          | Sends a FOS command via an SSH connection to a FOS switch                                 |
+-----------------------+-------------------------------------------------------------------------------------------+
| parse_cli             | If cmd begins with 'fos_cli/' the remaining portion of cmd is returned. Otherwise, None   |
|                       | is returned.                                                                              |
+-----------------------+-------------------------------------------------------------------------------------------+
| cli_port              | Strips out "0/" in "0/port_num" for fixed port switches                                   |
+-----------------------+-------------------------------------------------------------------------------------------+
| cli_wait              | Introduces a sleep. This is necessary to allow the API and CLI to sync up                 |
+-----------------------+-------------------------------------------------------------------------------------------+
| verbose_debug         | Sets or clears verbose debugging                                                          |
+-----------------------+-------------------------------------------------------------------------------------------+

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Added cli_port() and cli_wait()                                                       |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 06 Dec 2024   | Fixed SSH logout when no SSH login was performed. Limited to debug modes only.        |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2023, 2024 Consoli Solutions, LLC'
__date__ = '06 Dec 2024'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack@consoli-solutions.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.2'

import time
import paramiko
import brcdapi.log as brcdapi_log

_FOS_CLI = 'fos_cli/'
_FOS_CLI_LEN = len(_FOS_CLI)
_DEFAULT_TIMEOUT = 15  # Default timeout when setting up SSH session in login()
_DEFAULT_WAIT = 10  # Time to sleep waiting for the CLI and API to sync up

_verbose_debug = False  # When True, prints data structures. Only useful for debugging.


def login(session, timeout=_DEFAULT_TIMEOUT, force=False):
    """Performs an SSH login

    :param session: Dictionary of the session returned by fos_auth.login().
    :type session: dict
    :param timeout: SSH timeout value
    :type timeout: int
    :param force: If True, try logging in regardless of whether the login failed previously
    :type force: bool
    :return err_msgs: List of error messages
    :rtype err_msgs: list
    """
    if session.get('debug', False):
        session['ssh_fault'] = True
        return ['SSH login not supported while in debug mode']
    if force:
        session['ssh_fault'] = False
    if session.get('ssh_fault', False):
        return list()  # An error message was posted when ssh_fault was set so no need to repeat the message
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.client.WarningPolicy())
    try:
        ssh.connect(session['ip_addr'], username=session['user_id'], password=session['user_pw'], timeout=timeout)
    except BaseException as e:
        session['ssh_login'], session['ssh-fault'] = None, True
        return ['Access denied', 'Unexpected FOS error', 'Error is: ' + str(type(e)) + ': ' + str(e)]
    shell = ssh.invoke_shell()
    shell.settimeout(timeout)
    session['ssh_login'] = ssh

    return list()


def logout(session):
    """Logout of an SSH session

    :param session: Dictionary of the session returned by fos_auth.login().
    :type session: dict
    :rtype: None
    """
    if isinstance(session, dict):
        if session.get('ssh_login') is not None:
            session['ssh_login'].close()
        session['ssh_login'], session['ssh_fault'] = None, False


def send_command(session, fid, cmd):
    """Sends a FOS command via an SSH connection to a FOS switch

    :param session: Dictionary of the session returned by fos_auth.login().
    :type session: dict
    :param fid: Fabric ID
    :type fid: int
    :param cmd: Command to send to switch
    :type cmd: str
    :return: Responses
    :rtype: list
    """
    global _verbose_debug

    response_l = list()
    if session.get('ssh_fault', False):
        return response_l  # An error for the login fault has already been presented so no need to do anything else.
    if session.get('debug', False):
        session['ssh_fault'] = True
        brcdapi_log.log('Sending commands via SSH not supported while in debug mode', echo=True)
        return response_l

    # Make sure there is an SSH login
    if session.get('ssh_login') is None:
        el = login(session)
        if len(el) > 0:
            el.append('Could not login while attempting to process ' + cmd)
            brcdapi_log.exception(el, echo=True)
            return list()

    # Send the command
    full_cmd = 'fosexec --fid ' + str(fid) + ' -cmd "' + cmd + '"'
    if _verbose_debug:
        brcdapi_log.log(['FOS CLI send_command() - send:', full_cmd], echo=True)
    try:
        stdin, stdout, stderr = session['ssh_login'].exec_command(full_cmd)
    except BaseException as e:
        brcdapi_log.exception(str(type(e)) + ': ' + str(e), echo=True)
        return response_l
    try:
        response_l = stdout.readlines()
    except BaseException as e:
        brcdapi_log.exception(str(type(e)) + ': ' + str(e), echo=True)
        return response_l
    if _verbose_debug:
        brcdapi_log.log(['FOS CLI send_command() - response:'] + [str(b) for b in response_l], echo=True)

    return response_l


def parse_cli(cmd):
    """If cmd begins with 'fos_cli/' the remaining portion of cmd is returned. Otherwise, None is returned

    :param cmd: Command to check
    :type cmd: str
    :return: If cmd begins with 'fos_cli/' the remaining portion of cmd is returned. Otherwise, None is returned
    :rtype: str, None
    """
    global _FOS_CLI, _FOS_CLI_LEN

    if len(cmd) >= _FOS_CLI_LEN and cmd[0: _FOS_CLI_LEN] == _FOS_CLI:
        return cmd[_FOS_CLI_LEN:]
    return None


def cli_port(port):
    """Strips out "0/" in "0/port_num" for fixed port switches

    :param port: Port number
    :type port: str
    :return: Port
    :rtype: str
    """
    try:
        port_l = port.split('/')
        return port_l[1] if port_l[0] == '0' else port
    except (IndexError, TypeError):
        brcdapi_log.exception('Invalid port number: ' + str(type(port))) + ': ' + str(port)
    return port


def cli_wait(wait_time=_DEFAULT_WAIT):
    """Introduces a sleep. This is necessary to allow the API and CLI to sync up

    :param wait_time: Time in seconds to sleep
    :type wait_time: int
    :rtype: None
    """
    time.sleep(wait_time)


def verbose_debug(state):
    """Sets or clears verbose debugging

    :param state: True - Enable verbose debug, False - disable verbose debug
    :type state: bool
    """
    global _verbose_debug

    _verbose_debug = state
