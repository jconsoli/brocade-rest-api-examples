#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2023 Consoli Solutions, LLC.  All rights reserved.
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
:mod:`port_config.py` - Examples on how to modify port configuration parameters.

**Description**

    Initially, this began as a module with programming examples only. If that is all you are looking for, search on the
    methods in the Examples section. As with many of these examples, I added a shell interface to use them for my own
    scripts to configure ports.

    To set break points for experimentation purposes, search for _DEBUG. This allows you to simulate command line input.

**Examples**

    In the table below, the "Action" column is used with the -a option when running this script from a shell. If
    interested in how that aspect of this script works, search for _action_tbl_d. If all you are looking for are code
    examples, just search for the methods.

    |-----------------------+-----------+-----------------------------------------------------------+
    | Method                | Action    | Description                                               |
    |=======================+===========+===========================================================+
    | _action_name          | name      | Assigns user friendly name to a port or list of ports.    |
    |-----------------------+-----------+-----------------------------------------------------------+
    | _action_disable       | disable   | Disable a port or list of ports.                          |
    |-----------------------+-----------+-----------------------------------------------------------+
    | _action_p_disable     | p_disable | Persistently disable a port or list of ports.             |
    |-----------------------+-----------+-----------------------------------------------------------+
    | _action_enable        | enable    | Enable a port or list of ports.                           |
    |-----------------------+-----------+-----------------------------------------------------------+
    | _action_p_enable      | p_enable  | Persistently enable a port or list of ports.              |
    |-----------------------+-----------+-----------------------------------------------------------+
    | _action_decom         | decom     | Decommission a port or list of ports                      |
    |-----------------------+-----------+-----------------------------------------------------------+
    | _action_clear         | clear     | Clears statistics for a port or list of ports.            |
    |-----------------------+-----------+-----------------------------------------------------------+
    | _action_default       | default   | Set a port or list of ports to the default configuration. |
    |-----------------------+-----------+-----------------------------------------------------------+
    | _action_enable_eport  | enable_e  | Enables E-Port mode on a port or list of ports.           |
    |-----------------------+-----------+-----------------------------------------------------------+
    | _action_disable_eport | disable_e | Disables E-Port mode on a port or list of ports.          |
    |-----------------------+-----------+-----------------------------------------------------------+
    | _action_enable_nport  | enable_n  | Enables N-Port mode on a port or list of ports.           |
    |-----------------------+-----------+-----------------------------------------------------------+
    | _action_disable_nport | disable_n | Disables N-Port mode on a port or list of ports.          |
    |-----------------------+-----------+-----------------------------------------------------------+
    | _action_reserve       | reserve   | Reserves POD license for ports.                           |
    |-----------------------+-----------+-----------------------------------------------------------+
    | _action_release       | release   | Releases POD license for ports.                           |
    |-----------------------+-----------+-----------------------------------------------------------+

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 4.0.0     | 04 Aug 2023   | Re-Launch                                                                         |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""

__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2023 Consoli Solutions, LLC'
__date__ = '04 August 2023'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.0'

import argparse
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as brcdapi_auth
import brcdapi.log as brcdapi_log
import brcdapi.util as brcdapi_util
import brcdapi.gen_util as gen_util
import brcdapi.port as brcdapi_port
import brcdapi.file as brcdapi_file

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation
_DEBUG = False   # When True, use _DEBUG_xxx below instead of parameters passed from the command line.
_DEBUG_ip = 'xx.xxx.xx.xx'
_DEBUG_id = 'admin'
_DEBUG_pw = 'password'
_DEBUG_s = 'self'  # Use None or 'none' for HTTP. Use the certificate if HTTPS and not self signed
_DEBUG_fid = '128'
_DEBUG_p = '0/0-3'  # Use s/p notation for directors
_DEBUG_a = 'disable'
_DEBUG_d = True  # When True, all content and responses are formatted and printed (pprint).
_DEBUG_sup = False
_DEBUG_log = '_logs'
_DEBUG_nl = False


####################################################################
#
#       Action methods for _action_tbl_d
#
####################################################################
def _action_name(session, fid, in_port_l):
    """Assigns user friendly name to a port or list of ports.

    :param session: FOS session object
    :type session: dict
    :param fid: Fabric ID
    :type fid: int
    :param in_port_l: List of ports. Each list entry is the port number followed by a colon and the port name
    :type in_port_l: list
    :return: Request response from FOS
    :rtype: dict
    """
    # Build the content of the request to send to the switch
    pl = list()
    content = {'fibrechannel': pl}
    for port_l in [p.split(':') for p in in_port_l]:  # This is referred to as a list comprehension
        d = {
            'name': port_l[0] if '/' in port_l[0] else '0/' + port_l[0],
            'user-friendly-name': port_l[1]
        }
        pl.append(d)

    # PATCH only changes specified leaves in the content for this URI. It does not replace all resources
    return brcdapi_rest.send_request(session, 'running/brocade-interface/fibrechannel', 'PATCH', content, fid)


def _action_disable(session, fid, in_port_l):
    """Disable a port or list of ports. See _action_name() parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.disable_port(session,
                                     fid,
                                     [p.split(':')[0] for p in in_port_l],  # port list
                                     persistent=False,
                                     echo=False)


def _action_p_disable(session, fid, in_port_l):
    """Persistently disable a port or list of ports. See _action_name() parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.disable_port(session,
                                     fid,
                                     [p.split(':')[0] for p in in_port_l],  # port list
                                     persistent=True,
                                     echo=False)


def _action_enable(session, fid, in_port_l):
    """Enable a port or list of ports. See _action_name() parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.enable_port(session,
                                    fid,
                                    [p.split(':')[0] for p in in_port_l],  # port list
                                    persistent=False,
                                    echo=False)


def _action_p_enable(session, fid, in_port_l):
    """Persistently enable a port or list of ports. See _action_name() parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.enable_port(session,
                                    fid,
                                    [p.split(':')[0] for p in in_port_l],  # port list
                                    persistent=True,
                                    echo=False)


def _action_decom(session, fid, in_port_l):
    """Decommission a port or list of ports. See _action_name() parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.decommission_port(session, fid, [p.split(':')[0] for p in in_port_l], 'port')


def _action_clear(session, fid, in_port_l):
    """Clears statistics for a port or list of ports. See _action_name() parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.clear_stats(session, fid, [p.split(':')[0] for p in in_port_l])


def _action_default(session, fid, in_port_l):
    """Set a port or list of ports to the default configuration. See _action_name() parameters and return value
    definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.default_port_config(session, fid, [p.split(':')[0] for p in in_port_l])


def _action_enable_eport(session, fid, in_port_l):
    """Enables ports for use as an E-Port. See _action_name() parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.e_port(session,
                                     fid,
                                     [p.split(':')[0] for p in in_port_l],  # port list
                                     mode=True)


def _action_disable_eport(session, fid, in_port_l):
    """Disables ports for use as an E-Port. See _action_name() parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.e_port(session,
                               fid,
                               [p.split(':')[0] for p in in_port_l],  # port list
                               mode=False)


def _action_enable_nport(session, fid, in_port_l):
    """Enables ports for use as an E-Port. See _action_name() parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.n_port(session,
                               fid,
                               [p.split(':')[0] for p in in_port_l],  # port list
                               mode=True)


def _action_disable_nport(session, fid, in_port_l):
    """Disables ports for use as an E-Port. See _action_name() parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.n_port(session,
                               fid,
                               [p.split(':')[0] for p in in_port_l],  # port list
                               mode=False)


def _action_reserve(session, fid, in_port_l):
    """Reserves POD license for ports. See _action_name() parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.reserve_pod(session,
                                    fid,
                                    [p.split(':')[0] for p in in_port_l])  # port list


def _action_release(session, fid, in_port_l):
    """Releases POD license for ports. See _action_name() parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.release_pod(session,
                                    fid,
                                    [p.split(':')[0] for p in in_port_l])  # port list


"""This table is only used when using this module as a stand alone utility. The key in _action_tbl_d is the action, -a
from the command line. The value is a dictionary as follows:
+-------+-----------------------------------------------------------------------------------------------------------+
| Key   | Value                                                                                                     |
+=======+===========================================================================================================+
| a     | Pointer to the action to take. See *Table Driven Software* in the module header if this is not familiar   |
|       | to your.                                                                                                  |
+-------+-----------------------------------------------------------------------------------------------------------+
| h     | Help text associated with the action                                                                      |
+-------+-----------------------------------------------------------------------------------------------------------+
"""
_action_tbl_d = dict(
    name=dict(a=_action_name, h='Set the port name. Port list, -p, must be s/p:port_name'),
    disable=dict(a=_action_disable, h='Disable ports'),
    p_disable=dict(a=_action_p_disable, h='Persistently disable ports'),
    enable=dict(a=_action_enable, h='Enable ports'),
    p_enable=dict(a=_action_p_enable, h='Persistently enable ports'),
    decom=dict(a=_action_decom, h='Decommission ports (E-Ports only)'),
    clear=dict(a=_action_clear, h='Clear port statistics'),
    default=dict(a=_action_default, h='Disable and set all ports to the default port configuration'),
    eport_enable=dict(a=_action_enable_eport, h='Enable ports for use as an E-Port'),
    eport_disable=dict(a=_action_disable_eport, h='Disable ports for use as an E-Port'),
    nport_enable=dict(a=_action_enable_nport, h='Enable ports for use as an N-Port'),
    nport_disable=dict(a=_action_disable_nport, h='Disable ports for use as an N-Port'),
    reserve=dict(a=_action_reserve, h='Reserves POD license for ports.'),
    release=dict(a=_action_release, h='Releases POD license for ports.'),
)
_help_pad_len = 0
for _key in _action_tbl_d.keys():
    _help_pad_len = max(_help_pad_len, len(_key)+2)


def _get_input():
    """Parses the module load command line

    :return ip: Switch IP address
    :rtype ip: str
    :return id: User ID
    :rtype id: str
    :return pw: User password
    :rtype ip: str
    :return sec: Secure method. None for HTTP, otherwise the certificate or 'self' if self signed
    :rtype sec: str, None
    :return fid: FID associated with the ports, port_l
    :rtype fid: str
    :return port_l: List of ports to operate on
    :rtype port_l: list
    :return action: List of actions to take
    :rtype action: list
    """
    global _DEBUG, _DEBUG_ip, _DEBUG_id, _DEBUG_pw, _DEBUG_s, _DEBUG_fid, _DEBUG_p, _DEBUG_a, _DEBUG_d, _DEBUG_sup
    global _DEBUG_log, _DEBUG_nl, _help_pad_len

    ec = 0  # Return error code

    if _DEBUG:
        args_ip, args_id, args_pw, args_s, args_fid, args_p, args_a, args_d, args_sup, args_log, args_nl = \
            _DEBUG_ip, _DEBUG_id, _DEBUG_pw, _DEBUG_s, _DEBUG_fid, _DEBUG_p, _DEBUG_a, _DEBUG_d, _DEBUG_sup, \
            _DEBUG_log, _DEBUG_nl
    else:
        buf = 'Initially developed as programming examples. A shell interface was added to be run as a stand-alone '\
              'utility to modify port configurations.'
        parser = argparse.ArgumentParser(description=buf)
        parser.add_argument('-ip', help='(Required) IP address', required=False)
        parser.add_argument('-id', help='(Required) User ID', required=False)
        parser.add_argument('-pw', help='(Required) Password', required=False)
        parser.add_argument('-s', help="(Optional) Default is HTTP. Use -s self for HTTPS mode.", required=False)
        parser.add_argument('-fid', help='(Required) Virtual Fabric ID.', required=False)
        buf = '(Required) CSV list of ports or range of ports in s/p notation. Use "*" for all ports in FID. Any '\
              'entry with "." in it is assumed to be a file to read the port list from. For action "name", use '\
              's/p:port_name. "*" or a range of ports is not supported if the action, -a, is "name".'
        parser.add_argument('-p', help=buf, required=False)
        buf = '(Required) CSV list of actions to take on the port list, -p. For a list of actions, enter "help".'
        parser.add_argument('-a', help=buf, required=True)
        buf = '(Optional) Enable debug logging. Prints the formatted data structures (pprint) to the log and console.'
        parser.add_argument('-d', help=buf, action='store_true', required=False)
        buf = '(Optional) No parameters. Suppress all output to STD_IO except the exit message. Useful with batch '\
              'processing'
        parser.add_argument('-sup', help=buf, action='store_true', required=False)
        buf = '(Optional) Directory where log file is to be created. Default is to use the current directory. The log' \
              ' file name will always be "Log_xxxx" where xxxx is a time and date stamp.'
        parser.add_argument('-log', help=buf, required=False, )
        buf = '(Optional) No parameters. When set, a log file is not created. The default is to create a log file.'
        parser.add_argument('-nl', help=buf, action='store_true', required=False)
        args = parser.parse_args()
        args_ip, args_id, args_pw, args_s, args_fid, args_p, args_a, args_d, args_sup, args_log, args_nl = \
            args.ip, args.id, args.pw, args.s, args.fid, args.p, args.a, args.d, args.sup, args.log, args.nl

    # Set up the log and debug parameters
    if args_d:
        brcdapi_rest.verbose_debug = True
    if args_sup:
        brcdapi_log.set_suppress_all()
    if not args_nl:
        brcdapi_log.open_log(args_log)

    # Validate the actions:
    action_buf = args_a
    action_l = args_a.split(',')
    for action in action_l:
        if action not in _action_tbl_d:
            if action == 'help':
                ml = ['']
                for buf, d in _action_tbl_d.items():
                    ml.append(gen_util.pad_string(str(buf), _help_pad_len, ' ', append=True) + d['h'])
                ml.append('')
                brcdapi_log.log(ml, echo=True)
                return -1, args_ip, args_id, args_pw, args_s, args_fid, args_p, action_l
            else:
                ec = -1
                action_buf += ' INVALID. Re-run with "-a help" for a list of valid actions.'

    # Validate the FID
    fid = int(args_fid) if isinstance(args_fid, str) and args_fid.isnumeric() and '.' not in args_fid else 0
    fid_buf = str(args_fid)
    if fid < 1 or fid > 128:
        fid_buf += ' INVALID: Fabric ID must be an integer in the range 1-128'
        ec = -1

    # Validate that the remaining options were defined
    if args_ip is None:
        args_ip = 'Missing. For additional help, re-run with -h.'
        ec = -1
    if args_id is None:
        args_id = 'Missing. For additional help, re-run with -h.'
        ec = -1
    if args_p is None:
        args_p = 'Missing. For additional help, re-run with -h.'
        ec = -1

    # User feedback
    ml = ['port_disable.py: ' + __version__,
          'IP address, -ip: ' + brcdapi_util.mask_ip_addr(args_ip),
          'ID, -id:         ' + args_id,
          'Secure, -s:      ' + str(args_s),
          'Fabric ID, -fid: ' + str(fid_buf),
          'Ports, -p:       ' + args_p,
          'Actions, -a:     ' + action_buf]
    if _DEBUG:
        ml.insert(0, 'WARNING!!! Debug is enabled')
    if args_pw is None:
        ml.append('Missing password, -pw. For additional help, re-run with -h.')
        ec = -1
    brcdapi_log.log(ml, echo=True)

    return ec, args_ip, args_id, args_pw, args_s, fid, args_p, action_l


def pseudo_main():
    """Basically the main().

    :return: Exit code
    :rtype: int
    """
    global _DEBUG

    # Get and validate command line input
    ec, ip, user_id, pw, sec, fid, args_p, action_l = _get_input()
    if ec != 0:
        return ec

    # Login
    brcdapi_log.log('Attempting login', echo=True)
    session = brcdapi_rest.login(user_id, pw, ip, sec)
    if brcdapi_auth.is_error(session):
        brcdapi_log.log(['Login failed:', brcdapi_auth.formatted_error_msg(session)], echo=True)
        return -1
    brcdapi_log.log('Login succeeded', echo=True)

    try:  # I always do a try in code development so that if there is a code bug, I still log out.

        # Get the port list
        port_l = list()  # So port_l is not unassigned in the event of an error

        if args_p == '*':
            # Get all ports in this FID
            kpi = 'running/brocade-interface/fibrechannel'
            obj = brcdapi_rest.get_request(session, kpi, fid)
            if brcdapi_auth.is_error(obj):
                brcdapi_log.log('Failed to read ' + kpi + ' for fid ' + str(fid), echo=True)
                ec = -1
            else:
                port_l = [port_d['name'] for port_d in obj['fibrechannel']]

        elif '.' in args_p:  # Get the port list from a file
            try:
                for buf in brcdapi_file.read_file(args_p, remove_blank=True, rc=True):
                    port_l.extend(buf.split(','))  # So the file contents can be seperate lines or CSV or both
            except FileNotFoundError:
                brcdapi_log.log(['', 'File not found: ' + args_p, ''], echo=True)
                ec = -1
            except FileExistsError:
                brcdapi_log.log(['', 'Folder in ' + args_p + ' does not exist.', ''], echo=True)
                ec = -1

        else:  # Just take the user input as a CSV list of ports or range of ports
            port_l = brcdapi_port.port_range_to_list(args_p)

        # Perform the actions
        for action in action_l:
            if ec != 0:
                break
            obj = _action_tbl_d[action]['a'](session, fid, port_l)
            if brcdapi_auth.is_error(obj):
                brcdapi_log.log(['Error executing action ' + action,
                                 brcdapi_auth.formatted_error_msg(obj),
                                 'All processing stopped'],
                                echo=True)
                ec = -1
            else:
                brcdapi_log.log('Successfully completed action: ' + action, echo=True)

    except BaseException as e:
        e_buf = str(e, errors='ignore') if isinstance(e, (bytes, str)) else str(type(e))
        brcdapi_log.exception('Programming error encountered. Exception is: ' + e_buf, echo=True)
        ec = -1

    # Logout
    obj = brcdapi_rest.logout(session)
    if brcdapi_auth.is_error(obj):
        brcdapi_log.log(['Logout failed:', brcdapi_auth.formatted_error_msg(obj)], echo=True)
    else:
        brcdapi_log.log('Logout succeeded', echo=True)

    return ec


###################################################################
#
#                    Main Entry Point
#
###################################################################
if _DOC_STRING:
    print('_DOC_STRING is True. No processing')
    exit(0)

_ec = pseudo_main()
brcdapi_log.close_log('Processing complete. Exit status: ' + str(_ec), echo=True)
exit(_ec)
