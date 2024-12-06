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

    A collection of methods to perform common switch functions. For examples on how to use these functions, see
    api_examples/switch_delete.py and api_examples/switch_create.py. While most of the API requests are pretty
    straight forward and don't need a driver, there are a few things that need special attention and therefore have a
    library method:

**Public Methods**

+-----------------------+-------------------------------------------------------------------------------------------+
| Method                | Description                                                                               |
+=======================+===========================================================================================+
| add_ports             | Move ports to a logical switch. Ports cannot be moved if they have any special            |
|                       | configurations so this method automatically sets all ports to be moved back to the        |
|                       | factory default setting. Furthermore, moving ports takes a long time. So as not to incur  |
|                       | an HTTP session timeout, this method breaks up port moves into smaller chunks.            |
+-----------------------+-------------------------------------------------------------------------------------------+
| create_switch         | Create a logical switch. Creating a logical switch requires that the chassis be VF        |
|                       | enabled. It's easier to set the switch type at switch creation time. This method is a     |
|                       | little more convenient to use.                                                            |
+-----------------------+-------------------------------------------------------------------------------------------+
| delete_switch         | Sets all ports to their default configuration, moves those ports to the default switch    |
|                       | and then deletes the switch.                                                              |
+-----------------------+-------------------------------------------------------------------------------------------+
| disable_switch        | Disable a logical switch                                                                  |
+-----------------------+-------------------------------------------------------------------------------------------+
| enable_switch         | Enable a logical switch                                                                   |
+-----------------------+-------------------------------------------------------------------------------------------+
| fibrechannel_switch   | Set switch configuration parameters for                                                   |
|                       | brocade-fibrechannel-switch/fibrechannel-switch. Some requests require the WWN and some   |
|                       | require an ordered dictionary. This method automatically finds the switch WWN if it's not |
|                       | already known and handles the ordered dictionary. I'm sure I went over board with the     |
|                       | ordered list but rather than figure out what needed the ordered list and needed a WWN,    |
|                       | since I have this method I use it for everything except enabling and disabling switches.  |
+-----------------------+-------------------------------------------------------------------------------------------+
| logical_switches      | Returns a list of logical switches with the default switch first. It's fairly common to   |
|                       | need a list of logical switches with the ability to discern which one is the default, so  |
|                       | this method is provided as a convenience.                                                 |
+-----------------------+-------------------------------------------------------------------------------------------+
| switch_wwn            | Reads and returns the logical switch WWN from the API. I needed this method for           |
|                       | fibrechannel_switch() so I figured I may as well make it public.                          |
+-----------------------+-------------------------------------------------------------------------------------------+

**WARNING**
    * Circuits and tunnels are not automatically removed from GE ports when moving them to another logical switch
      Testing with GE ports was minimal
    * When enabling or disabling a switch, brocade-fibrechannel-switch/fibrechannel-switch/is-enabled-state, other
      actions may not take effect. The methods herein take this into account but programmers hacking this script cannot
      improve on efficiency by combining these operations. I think that if you put the enable action last, it will get
      processed last, but I stopped experimenting with ordered dictionaries and just broke the two operations out. I
      left all the ordered dictionaries in because once I got everything working, I did not want to change anything.
    * The address of a port in a FICON logical switch must be bound. As of FOS 9.0.b, there was no ability to bind the
      port addresses. This module can be used to create a FICON switch but if you attempt to enable the ports, you an
      error is returned stating "Port enable failed because port not bound in FICON LS".

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Changed add_ports() to return counts of successful and failed port moves. Added       |
|           |               | best flag and skip_default to add_ports().                                            |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 06 Dec 2024   | Fixed case where SSH login was not performed. Effected debug modes only.              |
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

import pprint
import collections
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as brcdapi_auth
import brcdapi.log as brcdapi_log
import brcdapi.port as brcdapi_port
import brcdapi.util as brcdapi_util
import brcdapi.fos_cli as fos_cli

# It takes about 10 sec + 500 msec per port to move per API request. MAX_PORTS_TO_MOVE defines the number of ports that
# can be moved in any single Rest request so as not to encounter an HTTP connection timeout.
MAX_PORTS_TO_MOVE = 32
_cli_wait_time = 20  # It takes a while for the API and the CLI to sync up

_FC_SWITCH = 'running/' + brcdapi_util.bfs_uri
_FC_LS = 'running/' + brcdapi_util.bfls_uri


def fibrechannel_configuration(session, fid, parms, echo=False):
    """Sets the fabric parameters for 'brocade-fibrechannel-configuration/fabric'.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number to be created.
    :type fid: int
    :param parms: Content for brocade-fibrechannel-configuration/fabric
    :type parms: dict
    :param echo: If True, step-by-step activity (each request) is echoed to STD_OUT
    :type echo: bool
    :return: Return from last request or first error encountered
    :rtype: dict
    """
    brcdapi_log.log('brocade-fibrechannel-configuration/fabric FID ' + str(fid) + ' with parms: ' +
                    ', '.join([str(buf) for buf in parms.keys()]), echo=echo)
    if len(parms.keys()) == 0:
        return brcdapi_util.GOOD_STATUS_OBJ

    # Configure the switch
    return brcdapi_rest.send_request(session, 'running/' + brcdapi_util.bfc_uri, 'PATCH', dict(fabric=parms), fid)


def enable_switch(session, fid, echo=False):
    """Enable a logical switch

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number to be created.
    :type fid: int
    :param echo: If True, step-by-step activity (each request) is echoed to STD_OUT
    :type echo: bool
    :return: Return from create switch operation or first error encountered
    :rtype: dict
    """
    return fibrechannel_switch(session, fid, {'is-enabled-state': True}, None, echo=echo)


def disable_switch(session, fid, echo=False):
    """Disable a logical switch

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number to be created.
    :type fid: int
    :param echo: If True, step-by-step activity (each request) is echoed to STD_OUT
    :type echo: bool
    :return: Return from create switch operation or first error encountered
    :rtype: dict
    """
    return fibrechannel_switch(session, fid, {'is-enabled-state': False}, None, echo=echo)


def switch_wwn(session, fid, echo=False):
    """Returns the switch WWN from the logical switch matching the specified FID.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number to be created.
    :type fid: int
    :param echo: If True, step-by-step activity (each request) is echoed to STD_OUT
    :type echo: bool
    :return: Switch WWN or return from first error encountered
    :rtype: str, dict
    """
    global _FC_SWITCH

    brcdapi_log.log('Getting switch data from brcdapi.switch.switch_wwn() for FID ' + str(fid), echo=echo)
    obj = brcdapi_rest.get_request(session, _FC_SWITCH, fid)
    if brcdapi_auth.is_error(obj):
        brcdapi_log.exception('Failed to get switch data for FID ' + str(fid), echo=echo)
        return obj
    try:
        return obj.get('fibrechannel-switch')[0].get('name')
    except (TypeError, IndexError) as e:
        buf = 'Unexpected data returned from ' + _FC_SWITCH + '. FID: ' + str(fid)
        brcdapi_log.exception(buf, echo=echo)
        return brcdapi_auth.create_error(brcdapi_util.HTTP_INT_SERVER_ERROR, e, msg=buf)


def logical_switches(session, echo=False):
    """Returns a list of logical switches with the default switch first

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param echo: When True, print details to STD_OUT
    :type echo: bool
    :return: If type dict, brcdapi_rest error status object. Otherwise, list of the FIDs in the chassis. Empty if not VF
        enabled. The default switch FID is first, [0].
    :rtype: dict, list
    """
    global _FC_LS

    # Get the chassis information
    obj = brcdapi_rest.get_request(session, 'running/brocade-chassis/chassis', None)
    if brcdapi_auth.is_error(obj):
        return obj
    rl = list()
    try:
        if obj['chassis']['vf-enabled']:
            # Get all the switches in this chassis
            obj = brcdapi_rest.get_request(session, _FC_LS, None)
            if brcdapi_auth.is_error(obj):
                return obj
            for ls in obj['fibrechannel-logical-switch']:
                if bool(ls['default-switch-status']):
                    rl.append(ls)
                    break
            rl.extend([ls for ls in obj['fibrechannel-logical-switch'] if not bool(ls['default-switch-status'])])
    except (ValueError, IndexError) as e:
        ml = ['Unexpected data returned from ' + _FC_LS]
        if isinstance(obj, dict):
            ml.append(pprint.pformat(obj) if isinstance(obj, dict) else 'Unknown programming error')
        brcdapi_log.exception(ml, echo=echo)
        return brcdapi_auth.create_error(brcdapi_util.HTTP_INT_SERVER_ERROR, 'Unknown error: ' + e)

    return rl


def fibrechannel_switch(session, fid, parms, wwn=None, echo=False):
    """Set parameters for brocade-fibrechannel-switch/fibrechannel-switch.

    Note: The intent of this method was to alleviate the need for programmers to have to build an ordered dictionary
    and look up the WWN of the switch.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number to be created.
    :type fid: int
    :param parms: Content for brocade-fibrechannel-switch/fibrechannel-switch
    :type parms: dict
    :param wwn: WWN of switch. If None, the WWN for the fid is read from the API.
    :type wwn: str, None
    :param echo: If True, step-by-step activity (each request) is echoed to STD_OUT
    :type echo: bool
    :return: Return from last request or first error encountered
    :rtype: dict
    """
    global _FC_SWITCH

    brcdapi_log.log([brcdapi_util.bfs_uri + ' FID ' + str(fid) + ' with params:', pprint.pformat(parms)], echo=echo)
    if len(parms.keys()) == 0:
        return brcdapi_util.GOOD_STATUS_OBJ

    if wwn is None:
        # I don't know why, but sometimes I need the WWN for brocade-fibrechannel-switch/fibrechannel-switch
        wwn = switch_wwn(session, fid, echo=echo)
        if isinstance(wwn, dict) and brcdapi_auth.is_error(wwn):
            return wwn

    # Configure the switch
    sub_content = collections.OrderedDict()  # I think 'name' must be first
    sub_content['name'] = wwn
    for k, v in parms.items():
        sub_content[k] = v
    return brcdapi_rest.send_request(session,
                                     _FC_SWITCH,
                                     'PATCH',
                                     {'fibrechannel-switch': sub_content},
                                     fid)


def add_ports(session, to_fid, from_fid, ports=None, ge_ports=None, echo=False, best=False, skip_default=False):
    """Move ports to a logical switch. Ports are set to the default configuration and disabled before moving them

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param to_fid: Logical FID number where ports are being moved to.
    :type to_fid: int
    :param from_fid: Logical FID number where ports are being moved from.
    :type from_fid: int
    :param ports: Ports to be moved to the switch specified by to_fid
    :type ports: int, str, list, tuple
    :param ge_ports: GE Ports to be moved to the switch specified by to_fid
    :type ge_ports: int, str, list, tuple
    :param echo: If True, the list of ports for each move is echoed to STD_OUT
    :type echo: bool
    :param best: If True, try moving ports one at a time if there is a failure so as many ports are moved as possible
    :type best: bool
    :param skip_default: If True, do not move the ports if the target switch is the default switch
    :type skip_default: bool
    :return success_l: Ports in s/p notation successfully added
    :rtype success_l: list
    :return fault_l: Ports in s/p notation that were not added
    :rtype fault_l: list
    """
    global _FC_LS, MAX_PORTS_TO_MOVE, _cli_wait_time

    success_l, fault_l = list(), list()
    if skip_default:
        fid_l = logical_switches(session, echo=echo)
        if len(fid_l) > 0 and fid_l[0] == to_fid:
            return success_l, fault_l

    ports_l, ge_ports_l = brcdapi_port.ports_to_list(ports), brcdapi_port.ports_to_list(ge_ports)
    if len(ports_l) + len(ge_ports_l) == 0:
        return success_l, fault_l
    buf = 'Attempting to move ' + str(len(ports_l)) + ' FC ports and ' + str(len(ge_ports_l)) + \
          ' GE ports from FID ' + str(from_fid) + ' to FID ' + str(to_fid)
    brcdapi_log.log(buf, echo=echo)

    # Set all ports to the default configuration and disable before moving.
    all_ports_l = ports_l + ge_ports_l
    obj = brcdapi_port.default_port_config(session, from_fid, ports_l + ge_ports_l)
    # Until this gets straightened out in FOS, there will always be an error if long distance settings are in place.
    # if brcdapi_auth.is_error(obj):
    #     brcdapi_log.exception('Failed to set all ports to the default configuration', echo=echo)
    #     return success_l, all_ports_l

    # Not all port configurations can be reset via the API. For now, just reset everything again via the CLI
    if len(all_ports_l) > 0:
        if not session.get('ssh_fault', False):
            for port in ports_l + ge_ports_l:
                response = fos_cli.send_command(session, from_fid, 'portcfgdefault ' + fos_cli.cli_port(port))
                # Not doing anything with the response. At least not yet anyway.
            fos_cli.cli_wait(_cli_wait_time)  # Let the API and CLI sync up

    # Move the ports, FOS returns an error if ports_l is an empty list in: 'port-member-list': {'port-member': ports_l}
    # so I have to custom build the content. Furthermore, it takes about 400 msec per port to move so to avoid an HTTP
    # connection timeout the port moves are done in batches.
    for ge_flag in (False, True):
        retry_l = list()
        local_port_l = ge_ports_l if ge_flag else ports_l
        while len(local_port_l) > 0:
            sub_content = {'fabric-id': to_fid}
            pl = local_port_l[0: MAX_PORTS_TO_MOVE] if len(local_port_l) > MAX_PORTS_TO_MOVE else local_port_l
            local_port_l = local_port_l[MAX_PORTS_TO_MOVE:]
            if ge_flag:
                sub_content.update({'ge-port-member-list': {'port-member': pl}})
            else:
                sub_content.update({'port-member-list': {'port-member': pl}})
            ml = ['Start moving ports:'] + ['  ' + buf for buf in pl]
            brcdapi_log.log(ml, echo=echo)
            obj = brcdapi_rest.send_request(session,
                                            _FC_LS,
                                            'POST',
                                            {'fibrechannel-logical-switch': sub_content})
            if brcdapi_auth.is_error(obj):
                if best:
                    retry_l.extend(pl)
                else:
                    fault_l.extend(pl)
            else:
                success_l.extend(pl)
                brcdapi_log.log('Successfully moved ports.', echo=echo)

        # Retry failures one port at a time. Otherwise, a failure one on port results in the entire list not being moved
        if len(retry_l) > 0:
            brcdapi_log.log('Retrying ports ' + ', '.join(retry_l), echo=echo)
            fos_cli.cli_wait(_cli_wait_time)  # Maybe the API and CLI aren't in sync yet.
        for port in retry_l:
            sub_content = {'fabric-id': to_fid}
            if ge_flag:
                sub_content.update({'ge-port-member-list': {'port-member': [port]}})
            else:
                sub_content.update({'port-member-list': {'port-member': [port]}})
            obj = brcdapi_rest.send_request(session,
                                            _FC_LS,
                                            'POST',
                                            {'fibrechannel-logical-switch': sub_content})
            if brcdapi_auth.is_error(obj):
                fault_l.append(port)
            else:
                success_l.append(port)

    return success_l, fault_l


def create_switch(session, fid, base, ficon, echo=False):
    """Create a logical switch with some basic configuration then disables the switch

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number to be created.
    :type fid: int
    :param base: If Ture - set switch as base switch
    :type base: bool
    :param ficon: If True - set switch as a FICON switch
    :type ficon: bool
    :param echo: If True, step-by-step activity (each request) is echoed to STD_OUT
    :type echo: bool
    :return: Return from create switch operation or first error encountered
    :rtype: dict
    """
    global _FC_LS

    # Make sure the chassis configuration supports the logical switch to create.
    switch_list = logical_switches(session)
    if isinstance(switch_list, dict):
        # The only time brcdapi_switch.logical_switches() returns a dict is when an error is encountered
        brcdapi_log.log(brcdapi_auth.formatted_error_msg(switch_list), echo=True)
        return switch_list
    if not isinstance(switch_list, list):
        return brcdapi_auth.create_error(brcdapi_util.HTTP_BAD_REQUEST, 'Chassis not VF enabled')
    if fid in switch_list:
        return brcdapi_auth.create_error(brcdapi_util.HTTP_BAD_REQUEST,
                                         'FID already present in chassis',
                                         msg=str(fid))
    if base and ficon:
        return brcdapi_auth.create_error(brcdapi_util.HTTP_BAD_REQUEST,
                                         'Switch type cannot be both base and ficon',
                                         msg=str(fid))

    # Create the logical switch
    sub_content = collections.OrderedDict()  # I'm not certain it needs to be ordered. Once bitten twice shy.
    sub_content['fabric-id'] = fid
    sub_content['base-switch-enabled'] = 0 if base is None else 1 if base else 0
    sub_content['ficon-mode-enabled'] = 0 if ficon is None else 1 if ficon else 0
    brcdapi_log.log('Creating logical switch ' + str(fid), echo=echo)
    obj = brcdapi_rest.send_request(session,
                                    _FC_LS,
                                    'POST',
                                    {'fibrechannel-logical-switch': sub_content})
    if brcdapi_auth.is_error(obj):
        return obj

    # Disable the switch
    return disable_switch(session, fid, echo=echo)


def delete_switch(session, fid, echo=False):
    """Sets all ports to their default configuration, moves those ports to the default switch, and deletes the switch

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number to be deleted.
    :type fid: int
    :param echo: If True, step-by-step activity (each request) is echoed to STD_OUT
    :type echo: bool
    :return: brcdapi_rest status object for the first error encountered of the last request
    :rtype: dict
    """
    global _FC_LS

    switch_list = logical_switches(session)
    if isinstance(switch_list, dict):
        # The only time brcdapi_switch.logical_switches() returns a dict is when an error is encountered
        brcdapi_log.log(brcdapi_auth.formatted_error_msg(switch_list), True)
        return switch_list
    if not isinstance(switch_list, list):
        return brcdapi_auth.create_error(brcdapi_util.HTTP_BAD_REQUEST, 'Chassis not VF enabled')

    default_fid = switch_list[0]['fabric-id']
    brcdapi_log.log('brcdapi.switch.delete_switch(): Attempting to delete FID ' + str(fid), echo=echo)
    # Find this logical switch
    for i in range(0, len(switch_list)):
        if switch_list[i]['fabric-id'] == fid:
            if i == 0:
                return brcdapi_auth.create_error(brcdapi_util.HTTP_BAD_REQUEST,
                                                 'Cannot delete the default logical switch',
                                                 msg=str(fid))

            # Move all the ports to the default logical switch.
            d = switch_list[i].get('port-member-list')
            port_l = None if d is None else d.get('port-member')
            d = switch_list[i].get('ge-port-member-list')
            ge_port_l = None if d is None else d.get('port-member')
            success_l, fault_l = add_ports(session, default_fid, fid, port_l, ge_port_l, echo=echo)

            # Delete the switch
            if len(fault_l) > 0:
                brcdapi_log.log('Error deleting FID ' + str(fid), echo=echo)
                return brcdapi_auth.create_error(brcdapi_util.HTTP_PRECONDITION_REQUIRED,
                                                 'Cannot delete FID ' + str(fid) + ' with ports',
                                                 msg=fault_l)
            else:
                obj = brcdapi_rest.send_request(session,
                                                _FC_LS,
                                                'DELETE',
                                                {'fibrechannel-logical-switch': {'fabric-id': fid}})
                brcdapi_log.log('Error' if brcdapi_auth.is_error(obj) else 'Success' + ' deleting FID ' + str(fid),
                                echo=echo)
                return obj

    return brcdapi_auth.create_error(brcdapi_util.HTTP_BAD_REQUEST, 'FID not found', msg=str(fid))


def bind_addresses(session, fid, port_d, echo=False):
    """Binds port addresses to ports. Requires FOS 9.1 or higher. Moved to brcdapi.port.py

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Fabric ID
    :type fid: None, int
    :param port_d: Key is the port number. Value is the port address in hex (str).
    :type port_d: dict
    :param echo: If True, the list of ports for each move is echoed to STD_OUT
    :type echo: bool
    :return: brcdapi_rest status object for the first error encountered of the last request
    :rtype: dict
    """
    return brcdapi_port.bind_addresses(session, fid, port_d, echo=echo)
