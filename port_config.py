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
redistribution, or service delivery for commerce requires an additional license. Contact jack_consoli@yahoo.com for
details.

:mod:`port_config.py` - Examples on how to modify port configuration parameters.

**Description**

    Initially, this began as a module with programming examples only. If that is all you are looking for, search on the
    methods in the Examples section. As with many of these examples, I added a shell interface to use them for my own
    scripts to configure ports.

    To set break points for experimentation purposes, search for _DEBUG. This allows you to simulate command line input.

**Examples**

    In the table below, the "Action" column is used with the "-a" option when running this script from a shell. If
    interested in how that aspect of this script works, search for _action_tbl_d. If all you are looking for are code
    examples, just search for the methods.

    |-----------------------+-----------+-----------------------------------------------------------+
    | Method                | Action    | Description                                               |
    |=======================+===========+===========================================================+
    | _action_name          | name      | Assigns user-friendly name to a port or list of ports.    |
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
    | _action_cli           | cli       | Executes CLI commands for a port or list of ports.        |
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

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Set verbose debug via brcdapi.brcdapi_rest.verbose_debug()                            |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 25 Aug 2025   | Replaced obsolete "supress" in call to brcdapi_log.open_log with "suppress".          |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.3     | 19 Oct 2025   | Updated comments only.                                                                |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.4     | 04 Dec 2025   | Added CLI action and options.                                                         |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2024, 2025 Consoli Solutions, LLC'
__date__ = '04 Dec 2025'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.4'

import os
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as brcdapi_auth
import brcdapi.log as brcdapi_log
import brcdapi.util as brcdapi_util
import brcdapi.gen_util as gen_util
import brcdapi.port as brcdapi_port
import brcdapi.file as brcdapi_file
import brcdapi.fos_cli as fos_cli

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation


####################################################################
#
#       Action methods for _action_tbl_d
#
####################################################################
def _action_name(session, fid, in_port_l, cli):
    """Assigns user-friendly name to a port or list of ports.

    :param session: FOS session object
    :type session: dict
    :param fid: Fabric ID
    :type fid: int
    :param in_port_l: List of ports. Each list entry is the port number followed by a colon and the port name
    :type in_port_l: list
    :param cli: CLI command(s). Only used with _action_cli()
    :type cli: str
    :return: Request response from FOS
    :rtype: dict
    """
    # Build the content of the request to send to the switch
    pl = list()
    content = {'fibrechannel': pl}
    for port_l in [p.split(':') for p in in_port_l]:
        d = {
            'name': port_l[0] if '/' in port_l[0] else '0/' + port_l[0],
            'user-friendly-name': port_l[1]
        }
        pl.append(d)

    # PATCH only changes specified leaves in the content for this URI. It does not replace all resources
    return brcdapi_rest.send_request(session, 'running/brocade-interface/fibrechannel', 'PATCH', content, fid)


def _action_disable(session, fid, in_port_l, cli):
    """Disable a port or list of ports. See _action_name() for parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.disable_port(session,
                                     fid,
                                     [p.split(':')[0] for p in in_port_l],  # port list
                                     persistent=False,
                                     echo=False)


def _action_p_disable(session, fid, in_port_l, cli):
    """Persistently disable a port or list of ports. See _action_name() for parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.disable_port(session,
                                     fid,
                                     [p.split(':')[0] for p in in_port_l],  # port list
                                     persistent=True,
                                     echo=False)


def _action_enable(session, fid, in_port_l, cli):
    """Enable a port or list of ports. See _action_name() for parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.enable_port(session,
                                    fid,
                                    [p.split(':')[0] for p in in_port_l],  # port list
                                    persistent=False,
                                    echo=False)


def _action_p_enable(session, fid, in_port_l, cli):
    """Persistently enable a port or list of ports. See _action_name() for parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.enable_port(session,
                                    fid,
                                    [p.split(':')[0] for p in in_port_l],  # port list
                                    persistent=True,
                                    echo=False)


def _action_decom(session, fid, in_port_l, cli):
    """Decommission a port or list of ports. See _action_name() for parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.decommission_port(session, fid, [p.split(':')[0] for p in in_port_l], 'port')


def _action_clear(session, fid, in_port_l, cli):
    """Clears statistics for a port or list of ports. See _action_name() for parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.clear_stats(session, fid, [p.split(':')[0] for p in in_port_l])


def _action_cli(session, fid, in_port_l, cli):
    """Execute CLI commands for ports. See _action_name() for parameters and return value definitions"""
    brcdapi_log.log('Executing CLI commands. This will take about ' + str(20 + len(in_port_l)) + ' seconds', echo=True)
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    for port in [p.split(':')[0] for p in in_port_l]:
        cmd = cli.replace('$p', port)
        response = fos_cli.send_command(session, fid, cmd)
        # Not doing anything with the response. At least not yet anyway. Just put it in the log without echo.
        brcdapi_log.log(['Command:  ' + cmd, 'Response: ' + str(response)])
    fos_cli.cli_wait()  # Let the API and CLI sync up.
    return brcdapi_util.GOOD_STATUS_OBJ


def _action_default(session, fid, in_port_l, cli):
    """Set ports to the default configuration. See _action_name() for parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    brcdapi_log.log(
        'Setting ports to the default configuration. This will take about ' + str(20 + len(in_port_l)) + ' seconds.',
        echo=log
    )
    return brcdapi_port.default_port_config(session, fid, [p.split(':')[0] for p in in_port_l])


def _action_enable_eport(session, fid, in_port_l, cli):
    """Enables ports for use as an E-Port. See _action_name() for parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.e_port(session,
                               fid,
                               [p.split(':')[0] for p in in_port_l],  # port list
                               mode=True)


def _action_disable_eport(session, fid, in_port_l, cli):
    """Disables ports for use as an E-Port. See _action_name() for parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.e_port(session,
                               fid,
                               [p.split(':')[0] for p in in_port_l],  # port list
                               mode=False)


def _action_enable_nport(session, fid, in_port_l, cli):
    """Enables ports for use as an E-Port. See _action_name() for parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.n_port(session,
                               fid,
                               [p.split(':')[0] for p in in_port_l],  # port list
                               mode=True)


def _action_disable_nport(session, fid, in_port_l, cli):
    """Disables ports for use as an E-Port. See _action_name() for parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.n_port(session,
                               fid,
                               [p.split(':')[0] for p in in_port_l],  # port list
                               mode=False)


def _action_reserve(session, fid, in_port_l, cli):
    """Reserves POD license for ports. See _action_name() for parameters and return value definitions"""
    # Since users may be using the port list for names, 's/p:name', below strips out the name
    return brcdapi_port.reserve_pod(session,
                                    fid,
                                    [p.split(':')[0] for p in in_port_l])  # port list


def _action_release(session, fid, in_port_l, cli):
    """Releases POD license for ports. See _action_name() for parameters and return value definitions"""
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
    clear=dict(a=_action_clear, h='Clear port statistics'),
    cli=dict(a=_action_cli, h='Execute CLI commands specified with -cli.'),
    default=dict(a=_action_default, h='Disable and set all ports to the default port configuration'),
    disable=dict(a=_action_disable, h='Disable ports'),
    enable=dict(a=_action_enable, h='Enable ports'),
    eport_disable=dict(a=_action_disable_eport, h='Disable ports for use as an E-Port'),
    eport_enable=dict(a=_action_enable_eport, h='Enable ports for use as an E-Port'),
    name=dict(a=_action_name, h='Set the port name. Port list, -p, must be s/p:port_name'),
    p_disable=dict(a=_action_p_disable, h='Persistently disable ports'),
    p_enable=dict(a=_action_p_enable, h='Persistently enable ports'),
    decom=dict(a=_action_decom, h='Decommission ports (E-Ports only)'),
    nport_enable=dict(a=_action_enable_nport, h='Enable ports for use as an N-Port'),
    nport_disable=dict(a=_action_disable_nport, h='Disable ports for use as an N-Port'),
    reserve=dict(a=_action_reserve, h='Reserves POD license for ports.'),
    release=dict(a=_action_release, h='Releases POD license for ports.'),
    help=dict(a=None, h='Display this help message and exit.'),
)
_help_pad_len = 0
for _key in _action_tbl_d.keys():
    _help_pad_len = max(_help_pad_len, len(_key)+2)

# debug input (for copy and paste into Run->Edit Configurations->script parameters):
# -ip 10.144.72.15 -id admin -pw AdminPassw0rd! -fid 1 -p 0/* -a clear -log _logs

_input_d = gen_util.parseargs_login_d.copy()
_input_d.update(
    fid=dict(t='int', v=gen_util.range_to_list('1-128'), h='Required. Fabric ID of logical switch'),
    p=dict(h='Required. Port or range of ports. Use "*" for all ports. Use "3/0-47" to specify ports 0-47 on slot 3. '
             'Separate multiple ports or port ranges with a comma. Range example: to specify ports 3/0, 3/1, 4/0, 4/1, '
             'and 5/3 enter "3-4/0-1,5/3" for the -p parameter. If the entry contains a ".", it is assumed to be a '
             'file containing a list of ports and port ranges. Ports in ranges that do not belong to the switch are '
             'ignored. Port ranges ARE NOT SUPPORTED when naming ports (using "name" as an action, -a, parameter)'),
    a=dict(h='(Required) CSV list of actions to take on the port list, -p. For a list of actions, enter "help".'),
    ge_ports=dict(r=False, h='Optional. Same as -ports but for GE ports.'),
    cli=dict(
        r=False,
        h='Optional. Required if "cli" is one of the actions, -a. Use $p in the command string where a port number is '
          'required.'
    ),
)
_input_d.update(gen_util.parseargs_log_d.copy())
_input_d.update(gen_util.parseargs_debug_d.copy())


def _get_input():
    """Parses the module load command line

    :return ip: Switch IP address
    :rtype ip: str
    :return id: User ID
    :rtype id: str
    :return pw: User password
    :rtype ip: str
    :return sec: Secure method. None for HTTP, otherwise the certificate or 'self' if self-signed
    :rtype sec: str, None
    :return fid: FID associated with the ports, port_l
    :rtype fid: str
    :return port_l: Ports to operate on
    :rtype port_l: list
    :return action: Actions to take
    :rtype action: list
    """
    global __version__, _input_d, _help_pad_len

    ec = 0  # Return error code

    # Get command line input
    args_d = gen_util.get_input('Create a logical switch.', _input_d)

    # Set up logging
    if args_d['d']:
        brcdapi_rest.verbose_debug(True)
    brcdapi_log.open_log(
        folder=args_d['log'],
        suppress=args_d['sup'],
        version_d=brcdapi_util.get_import_modules(),
        no_log=args_d['nl']
    )

    ml = [
        os.path.basename(__file__) + ', ' + __version__,
        'IP, -ip:         ' + brcdapi_util.mask_ip_addr(args_d['ip'], keep_last=True),
        'ID, -id:         ' + args_d['id'],
        'Security, -s:    ' + args_d['s'],
        'FID List, -fid:  ' + str(args_d['fid']),
        'Ports, -p:       ' + args_d['p'],
        'Actions, -a:     ' + args_d['a'],
        'CLI, -cli:       ' + str(args_d['cli']),
        'Log, -log:       ' + str(args_d['log']),
        'No log, -nl:     ' + str(args_d['nl']),
        'Debug, -d:       ' + str(args_d['d']),
        'Suppress, -sup:  ' + str(args_d['sup']),
        '',
    ]

    # Action help
    action_l = args_d['a'].split(',')
    for action in action_l:
        if action == 'help':
            ml.append(gen_util.pad_string('Action', _help_pad_len, ' ', append=True) + 'Description')
            ml.append(gen_util.pad_string('------', _help_pad_len, ' ', append=True) + '-----------')
            for buf, d in _action_tbl_d.items():
                ml.append(gen_util.pad_string(str(buf), _help_pad_len, ' ', append=True) + d['h'])
            ml.append('')
            ec = -1
        if action == 'cli':
            if args_d['cli'] is None:
                ml.extend(['cli specified with -a, but -cli was not specified.', ''])
                ec = -1
        if action not in _action_tbl_d:
            ml.append('Invalid action: ' + action)

    brcdapi_log.log(ml, echo=True)

    return ec, args_d['ip'], args_d['id'], args_d['pw'], args_d['s'], args_d['fid'], args_d['p'], action_l, \
        args_d['cli']


def pseudo_main():
    """Basically the main().

    :return: Exit code
    :rtype: int
    """
    # Get and validate command line input
    ec, ip, user_id, pw, sec, fid, args_p, action_l, cli = _get_input()
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

        # Get the port list from the switch
        all_port_l = list()
        kpi = 'running/brocade-interface/fibrechannel'
        obj = brcdapi_rest.get_request(session, kpi, fid)
        if brcdapi_auth.is_error(obj):
            brcdapi_log.log('Failed to read ' + kpi + ' for fid ' + str(fid), echo=True)
            ec = -1
        else:
            all_port_l = [port_d['name'] for port_d in obj['fibrechannel']]
        port_l = list()  # So port_l is not unassigned in the event of an error

        if args_p == '*':
            port_l = all_port_l
        else:

            if '.' in args_p:  # Get the port list from a file
                try:
                    for buf in brcdapi_file.read_file(args_p, remove_blank=True, rc=True):
                        port_l.extend(buf.split(','))  # So the file contents can be separate lines or CSV or both
                except FileNotFoundError:
                    brcdapi_log.log(['', 'File not found: ' + args_p, ''], echo=True)
                    ec = -1
                except FileExistsError:
                    brcdapi_log.log(['', 'Folder in ' + args_p + ' does not exist.', ''], echo=True)
                    ec = -1

            else:  # Take the user input and filter out any ports not the logical switch.
                # All ports specified by the range
                port_range_l = args_p.split(',') if 'name' in action_l else brcdapi_port.port_range_to_list(args_p)

                # Create a dictionary of ports in the switch to be used to determine which ports in port_range_l exist.
                all_port_d = dict()
                for port in all_port_l:
                    # name_l = port.split(':')
                    temp_port_l = port.split(':')[0].split('/')
                    slot_d = all_port_d.get(temp_port_l[0])
                    if slot_d is None:
                        slot_d = dict()
                        all_port_d[temp_port_l[0]] = slot_d
                    slot_d[temp_port_l[1]] = True

                # Get a list of ports in the range that match ports that exist in the logical switch
                for port in port_range_l:
                    name_l = port.split(':')
                    temp_port_l = name_l[0].split('/')
                    if len(temp_port_l) == 1:
                        slot_num, port_num = '0', temp_port_l[0]
                    else:
                        slot_num, port_num = temp_port_l[0], temp_port_l[1]
                    try:
                        if all_port_d[slot_num][port_num]:
                            if len(name_l) == 1:
                                port_l.append(slot_num + '/' + port_num)
                            else:
                                port_l.append(slot_num + '/' + port_num + ':' + name_l[1])
                    except KeyError:
                        pass

        # Do we have any ports to act on?
        if len(port_l) == 0:
            brcdapi_log.log('No matching ports found in the logical switch with FID ' + str(fid), echo=True)
            ec = -1
        else:
            brcdapi_log.log('Total matching ports to act on: ' + str(len(port_l)), echo=True)

        # Perform the actions
        if ec == 0:
            for action in action_l:
                obj = _action_tbl_d[action]['a'](session, fid, port_l, cli)
                if brcdapi_auth.is_error(obj):
                    brcdapi_log.log(['Error executing action ' + action,
                                     brcdapi_auth.formatted_error_msg(obj),
                                     'All processing stopped'],
                                    echo=True)
                    ec = -1
                    break
                else:
                    brcdapi_log.log('Successfully completed action: ' + action, echo=True)

    except brcdapi_util.VirtualFabricIdError:
        brcdapi_log.log('Software error. Search the log for "Invalid FID" for details.', echo=True)
        ec = -1
    except ValueError:
        buf = 'Invalid port or port range used with -p.'
        if 'name' in action_l:
            buf += ' This typically happens when a port range is used with names. Naming ports is not supported with '
            buf += 'port ranges.'
        brcdapi_log.log(buf, echo=True)
        ec = -1
    except BaseException as e:
        brcdapi_log.exception(['Programming error encountered.', str(type(e)) + ': ' + str(e)], echo=True)
        ec = -1

    # Logout
    obj = brcdapi_rest.logout(session)
    if brcdapi_auth.is_error(obj):
        brcdapi_log.log(['Logout failed:', brcdapi_auth.formatted_error_msg(obj)], echo=True)
        ec = -1
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
