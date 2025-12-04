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

:mod:`switch_create.py` - Examples on how to create a logical switch with some basic configuration

Scroll all the way to the bottom to find the entry point.

**Description**

    Examples on how to create a logical switch, add ports, and make some basic configuration changes. Your code should
    do more error checking and likely will want to set additional switch parameters. This example illustrates how to
    create a logical switch, add ports, and set common switch configuration parameters.

**Example**

    To create a standard switch, FID 21, with an insistent DID of 11 on an 8 slot chassis switch with all ports on all
    blades except the core blades (ICL ports) and enable all the ports, it has to be done in 2 steps because the user
    interface in this module only allows a range of slot and port numbers.

    py switch_create.py -ip 10.1.1.10 -id admin -pw password -fid 21 -name Test_switch_21 -did 11 -ports 3-6/0-47 -idid

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 25 Aug 2025   | Replaced obsolete "supress" in call to brcdapi_log.open_log with "suppress".          |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 19 Oct 2025   | Updated comments only.                                                                |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.3     | 04 Dec 2025   | Dynamically obtain file name instead of hard coding it for help message.              |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2024, 2025 Consoli Solutions, LLC'
__date__ = '04 Dec 2025'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.3'

import os
import brcdapi.gen_util as gen_util
import brcdapi.util as brcdapi_util
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as fos_auth
import brcdapi.log as brcdapi_log
import brcdapi.switch as brcdapi_switch
import brcdapi.port as brcdapi_port

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation
# _STAND_ALONE: True: Executes as a standalone module taking input from the command line. False: Does not automatically
# execute. This is useful when importing this module into another module that calls psuedo_main().
_STAND_ALONE = True  # See note above

# debug input (for copy and paste into Run->Edit Configurations->script parameters):
# -ip 10.144.72.15 -id admin -pw AdminPassw0rd! -fid 1 -name test_switch -did 20 -idid -xisl -ports 0-7 -log _logs

_input_d = gen_util.parseargs_login_d.copy()
_input_d.update(
    fid=dict(t='int', v=gen_util.range_to_list('1-128'), h='Required. Fabric ID of logical switch'),
    name=dict(r=False,
              h='Optional. Switch user-friendly name. Default is "switchxx" where "xx" is the domain ID.'),
    did=dict(t='int', v=gen_util.range_to_list('1-239'),
             h='Required. Sets the switch domain ID. Default is 1'),
    idid=dict(r=False, t='bool', d=False, h='Optional. No parameters. When set, makes the domain ID insistent.'),
    xisl=dict(r=False, t='bool', d=False, h='Optional. No parameters. When set, permits use of ISL in base switch.'),
    type=dict(r=False, d='open', v=('base', 'ficon', 'open'),
              h='Optional. choices are "base", "ficon", and "open". The default is "open"'),
    ports=dict(r=False,
               h='Optional. Ports to add. Default is none. Accepts a range. For example, for all ports of slots 3 & 4 '
                 'you can enter "-ports 3-4/0-47".'),
    ge_ports=dict(r=False, h='Optional. Same as -ports but for GE ports.'),
)
_input_d.update(gen_util.parseargs_log_d.copy())
_input_d.update(gen_util.parseargs_debug_d.copy())


class FOSError(Exception):
    pass


def pseudo_main(ip, user_id, pw, sec, fid, name, did, idid, xisl, switch_type, port_l, ge_port_l):
    """Basically the main().

    :param ip: Switch IP address
    :type ip: str
    :param id: User ID
    :type id: str
    :param pw: User password
    :type ip: str
    :param sec: Secure method. None for HTTP, otherwise the certificate or 'self' if self-signed
    :type sec: str, None
    :param fid: Fabric ID (FID)
    :type fid: int
    :param name: Switch name.
    :type name: str
    :param did: Domain ID
    :type did: int
    :param idid: If True, set insistent domain ID
    :type idid: bool
    :param xisl: If True, set "allow XISL"
    :type xisl: bool
    :switch_type: Type of switch (open, base, or ficon)
    :type switch_type: str
    :param port_l: Ports
    :type port_l: list
    :param ge_port_l: GE ports
    :type ge_port_l: list
    :param es: Enable switch
    :type es: bool
    :param ep: Enable ports
    :type ep: bool
    :return: Exit code
    :rtype: int
    """
    ec = 0  # Return code

    # Login
    brcdapi_log.log('Attempting login', True)
    session = brcdapi_rest.login(user_id, pw, ip, sec)
    if fos_auth.is_error(session):
        brcdapi_log.log(['Login failed. API error message is:', fos_auth.formatted_error_msg(session)], True)
        return -1
    brcdapi_log.log('Login succeeded.', True)

    try:  # I always do a try in code development so that if there is a code bug, I still log out.

        # Create the logical switch. This will take about 20 sec.
        obj = brcdapi_switch.create_switch(session,
                                           fid,
                                           True if switch_type == 'base' else False,
                                           True if switch_type == 'ficon' else False,
                                           echo=True)  # Prints additional progress status to the log and console
        if fos_auth.is_error(obj):
            brcdapi_log.log(['Failed to created logical switch FID ' + str(fid), fos_auth.formatted_error_msg(obj)],
                            echo=True)
            raise FOSError

        # Some switch parameters require the switch to be offline, so disable the switch
        obj = brcdapi_switch.disable_switch(session, fid, echo=True)
        if fos_auth.is_error(obj):
            brcdapi_log.log(['Failed to disable logical switch FID ' + str(fid), fos_auth.formatted_error_msg(obj)],
                            echo=True)
            raise FOSError

        # Configure the user-friendly fabric name banner, domain ID, switch user-friendly name. Just making up a fabric
        # name and banner for illustration purposes. Updates using brocade-fibrechannel-switch/fibrechannel-switch
        # have a unique handling, so it is done in a library.
        sub_content_d = {
            'domain-id': did,
            'user-friendly-name': name,
            'fabric-user-friendly-name': name + '_fab',
            'banner': 'Welcome to the test switch',
        }
        obj = brcdapi_switch.fibrechannel_switch(session, fid, sub_content_d, echo=True)
        if fos_auth.is_error(obj):
            brcdapi_log.exception(['Failed to configure name and banner for FID ' + str(fid),
                                   fos_auth.formatted_error_msg(obj)],
                                  echo=True)
            raise FOSError

        # Set XISL. Setting the XISL is in the brocade-fibrechannel-configuration branch which does not require special
        # handling. This example illustrates how changes are typically sent to the switch
        content_d = {
            'switch-configuration': {
                'xisl-enabled': xisl
            }
        }
        obj = brcdapi_rest.send_request(session,
                                        'running/' + brcdapi_util.bfc_sw_uri,
                                        'PATCH',
                                        content_d,
                                        fid)
        if fos_auth.is_error(obj):
            brcdapi_log.exception(['Failed to configure "Allow XISL" ' + str(fid),
                                   fos_auth.formatted_error_msg(obj)],
                                  echo=True)
            raise FOSError

        # Add the ports. Since this is just an example, I'm going to assume the ports are in FID 128
        # This will take about 40 sec per group of 32 ports
        success_l, fault_l = brcdapi_switch.add_ports(session, fid, 128, ports=port_l, ge_ports=ge_port_l, echo=True)
        if len(success_l) > 0:
            brcdapi_log.log(['Succesfully added ports:'] + success_l, echo=True)
        if len(fault_l) > 0:
            brcdapi_log.log(['Failed to added ports:'] + fault_l, echo=True)

        # Enable the switch
        obj = brcdapi_switch.enable_switch(session, fid, echo=True)
        if fos_auth.is_error(obj):
            brcdapi_log.log(['Failed to enable switch, FID ' + str(fid), fos_auth.formatted_error_msg(obj)],
                            echo=True)
            raise FOSError

        # Enable the ports
        # For a fixed port switch the POD license was removed when the ports were moved. To add the POD license, see
        # brcdapi.port.reserve_pod()
        obj = brcdapi_port.enable_port(session, fid, port_l + ge_port_l, persistent=False, echo=False)
        if fos_auth.is_error(obj):
            brcdapi_log.log(['Failed to enable ports, FID ' + str(fid), fos_auth.formatted_error_msg(obj)],
                            echo=True)
            raise FOSError

    except brcdapi_util.VirtualFabricIdError:
        brcdapi_log.log('Software error. Search the log for "Invalid FID" for details.', echo=True)
        ec = -1
    except FOSError:
        pass  # The specific error messages have already been sent to the log
        ec = -1
    except BaseException as e:
        brcdapi_log.exception(['Programming error encountered.', str(type(e)) + ': ' + str(e)], echo=True)
        ec = -1

    # Logout
    obj = brcdapi_rest.logout(session)
    if fos_auth.is_error(obj):
        brcdapi_log.log(['Logout failed. API error message is:',  fos_auth.formatted_error_msg(obj)], echo=True)
        ec = -1

    return ec


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
    :return fids: FID(s) to delete
    :rtype fids: str
    :return vd: Verbose debug flag.
    :rtype vd: bool
    """
    global __version__, _input_d

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
        'IP, -ip:                  ' + brcdapi_util.mask_ip_addr(args_d['ip'], keep_last=True),
        'ID, -id:                  ' + args_d['id'],
        'Security, -s:             ' + args_d['s'],
        'FID, -fid:                ' + str(args_d['fid']),
        'Name, -name:              ' + str(args_d['name']),
        'DID, -did:                ' + str(args_d['did']),
        'Insistent, -idid:         ' + str(args_d['idid']),
        'xisl, -xisl:              ' + str(args_d['xisl']),
        'Switch type, -type:       ' + str(args_d['type']),
        'Ports-, -ports:           ' + str(args_d['ports']),
        'GE Ports, -ge_ports:      ' + str(args_d['ge_ports']),
        ]
    brcdapi_log.log(ml, echo=True)

    port_l = gen_util.sp_range_to_list(args_d['ports'])
    ge_port_l = gen_util.sp_range_to_list(args_d['ge_ports'])

    return pseudo_main(args_d['ip'], args_d['id'], args_d['pw'], args_d['s'], args_d['fid'], args_d['name'],
                       args_d['did'], args_d['idid'], args_d['xisl'], args_d['type'], port_l, ge_port_l)


###################################################################
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
