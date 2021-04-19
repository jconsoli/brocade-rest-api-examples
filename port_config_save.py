#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2019, 2020, 2021 Jack Consoli.  All rights reserved.
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

    Illustrates how to change parameters available in the 'brocade-interface/fibrechannel'. This specific example
    changes the user friendly port name and sets LOS TOV mode.

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 1.x.x     | 03 Jul 2019   | Experimental                                                                      |
    | 2.x.x     |               |                                                                                   |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.0     |               | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.1     | 27 Nov 2020   | Added examples using the brcdapi.port library.                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.2     | 09 Jan 2021   | Open log file.                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.3     | 13 Feb 2021   | Added # -*- coding: utf-8 -*-                                                     |
    |           |               | Broke out examples into seperate modules.                                         |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2019, 2020, 2021 Jack Consoli'
__date__ = '13 Feb 2021'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.3'

import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.pyfos_auth as pyfos_auth
import brcdapi.log as brcdapi_log
import brcdapi.port as brcdapi_port

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation

# Login credentials
_DEBUG_IP = '10.8.105.10'
_DEBUG_ID = 'admin'
_DEBUG_PW = 'password'
_DEBUG_SEC = 'self'  # 'none'
_DEBUG_FID = 21
_DEBUG_LOG = '_logs'
_DEBUG_NL = False

# Program control parameters
_DEBUG_VERBOSE = False  # When True, all content and responses are formatted and printed.
_DEBUG_CONFIGURE_PORTS = False  # Call configure_ports()
_DEBUG_ENABLE_ALL_PORTS = False  # Enable all ports in the specified FID
_DEBUG_DISABLE_ALL_PORTS = False  # Disable all ports in the specified FID
_DEBUG_CLEAR_STATS = True  # Clear statistical counters for all ports in the specified FID
_DEBUG_ALL_PORTS_DEFAULT = False  # Disables all ports and sets them to the factory default configuration


def get_ge_port_list(session, fid):
    """Returns the list of GE ports in a logical switch

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical switch FID number
    :type fid: int
    :return: List of GE ports
    :rtype: list
    """
    obj = brcdapi_rest.get_request(
        session, 'brocade-fibrechannel-logical-switch/fibrechannel-logical-switch/fabric-id/' + str(fid))
    if pyfos_auth.is_error(obj):
        brcdapi_log.log(pyfos_auth.formatted_error_msg(obj), True)
        return list()
    if 'fibrechannel-logical-switch' in obj and 'ge-port-member-list' in obj['fibrechannel-logical-switch']:
        pl = obj['fibrechannel-logical-switch']['ge-port-member-list'].get('port-member')
        return list() if pl is None else pl
    return list()


def configure_ports(session, fid, port_list):
    """Sample how to modify port configurations.

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number
    :type fid: int
    :param port_list: list of ports to configure
    :type port_list: list
    :return: brcdapi_rest status object
    :rtype: dict
    """
    # More robust code would check to make sure the ports are disabled if changes require the port to be disabled.
    pl = []
    content = {'fibrechannel': pl}
    for p in port_list:
        d = {}
        d.update({'name': p})
        d.update({'user-friendly-name': 'port_' + p.replace('/', '_')})  # Give the port a user friendly name
        d.update({'los-tov-mode-enabled': 2})  # Enable LOS_TOV for both fixed speed and auto-negotiated ports
        # For other port configuration parameters, search the Rest API Guide or Yang models for
        # brocade-interface/fibrechannel
        pl.append(d)
    # PATCH only changes specified leaves in the content for this URI. It does not replace all resources
    return brcdapi_rest.send_request(session, 'brocade-interface/fibrechannel', 'PATCH', content, fid)


def make_port_changes(session, fid):
    """Make the port configuration calls.

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number.
    :type fid: int
    :return: 0: Successfully configured switch. -1: Failed to configure switch
    :rtype: int
    """

    # Read FC port configurations
    obj = brcdapi_rest.get_request(session, 'brocade-interface/fibrechannel', fid)
    if pyfos_auth.is_error(obj):
        brcdapi_log.log('Failed to read brocade-interface/fibrechannel for fid ' + str(fid), True)
        return obj

    """Get the list of fibre channel ports in the logical switch. If you are new to Python, below is what is referred to
    as a list comprehension. It is the equivalent of:
    fc_plist = list()  # This is the more Pythonic way to say fc_plist = []
    for port in obj['fibrechannel']:
        fc_plist.append(port['name'])
    """
    fc_plist = [port['name'] for port in obj['fibrechannel']]  # See comments in get_ge_port_list() for an alternative
    if len(fc_plist) == 0:
        brcdapi_log.log('No port found in FID ' + str(fid) + '.', True)
        return 0
    ge_plist = get_ge_port_list(session, fid)


    """Put all the ports in a dictionary for easy lookup
    The examples herein are intended to illustrate how to perform certain port functions. They are simple and focused on
    just the specific port operation for the intended example. In most cases, the examples are hard coded. For a useful
    automation project, you may read in the port configurations and act on them based on what was returned. Building a
    dictionary referenced by port number is often useful so as not to have to scroll through a list of ports and match
    the name.
    
    I don't use port_d anywhere in this module, it's just here as an example. If all I wanted was the port
    list, see the comments in get_ge_port_list()."""
    port_d = dict()
    for port in obj['fibrechannel']:
        port_d.update({port['name']: port})

    # Configure the ports
    if _DEBUG_CONFIGURE_PORTS:
        brcdapi_log.log('Configuring ports of fid: ' + str(fid), True)
        obj = configure_ports(session, fid, fc_plist)
        if pyfos_auth.is_error(obj):
            brcdapi_log.log(pyfos_auth.formatted_error_msg(obj), True)
            return -1
        else:
            brcdapi_log.log('Successfully configured ports for FID ' + str(fid), True)

    # Enable all ports
    if _DEBUG_ENABLE_ALL_PORTS:
        brcdapi_log.log('Enabling all FC ports of fid: ' + str(fid), True)
        obj = brcdapi_port.port_enable_disable(session, fid, fc_plist, True)
        if pyfos_auth.is_error(obj):
            brcdapi_log.log(pyfos_auth.formatted_error_msg(obj), True)
            return -1
        else:
            brcdapi_log.log('Successfully enabled all ports for FID ' + str(fid), True)

    # Disable all ports
    if _DEBUG_DISABLE_ALL_PORTS:
        brcdapi_log.log('Disabling all FC ports of fid: ' + str(fid), True)
        obj = brcdapi_port.port_enable_disable(session, fid, fc_plist, False)
        if pyfos_auth.is_error(obj):
            brcdapi_log.log(pyfos_auth.formatted_error_msg(obj), True)
            return -1
        else:
            brcdapi_log.log('Successfully disabled all ports for FID ' + str(fid), True)

    # Clear statistics on all ports
    if _DEBUG_CLEAR_STATS:
        brcdapi_log.log('Clearing statistics for all ports of fid: ' + str(fid), True)
        obj = brcdapi_port.clear_stats(session, fid, fc_plist, ge_plist)
        if pyfos_auth.is_error(obj):
            brcdapi_log.log('Error clearing stats for ports for FID ' + str(fid), True)
            brcdapi_log.log(pyfos_auth.formatted_error_msg(obj), True)
            return -1
        else:
            brcdapi_log.log('Successfully cleared stats for all ports for FID ' + str(fid), True)

    # Set ports to default state
    if _DEBUG_ALL_PORTS_DEFAULT:  # This only does FC ports. Examples for GE ports is on the wish list
        brcdapi_log.log('Disabling all ports of fid: ' + str(fid) + ' and setting to default configuration', True)
        obj = brcdapi_port.default_port_config(session, fid, fc_plist)
        if pyfos_auth.is_error(obj):
            brcdapi_log.log('Set ports to default for FID ' + str(fid) + ' failed', True)
            brcdapi_log.log(pyfos_auth.formatted_error_msg(obj), True)
            return -1
        else:
            brcdapi_log.log('Successfully set all ports for FID ' + str(fid) + ' to the default configuration', True)

    return 0


def pseudo_main(user_id, pw, ip, sec, vd, log, nl):
    """Basically the main().

    :param user_id: User ID
    :type user_id: str
    :param pw: Password
    :type pw: str
    :param ip: IP address
    :type ip: str
    :param sec: Security. 'none' for HTTP, 'self' for self signed certificate, 'CA' for signed certificate
    :type sec: str
    :param vd: When True, enables debug logging
    :type vd: bool
    :return: Exit code
    :rtype: int
    """
    if not nl:
        brcdapi_log.open_log(log)
    if vd:
        brcdapi_rest.verbose_debug = True

    # Login
    brcdapi_log.log('Attempting login', True)
    session = brcdapi_rest.login(user_id, pw, ip, sec)
    if pyfos_auth.is_error(session):
        brcdapi_log.log('Login failed', True)
        brcdapi_log.log(pyfos_auth.formatted_error_msg(session), True)
        return -1

    else:
        try:  # I always do a try in code development so that if there is a code bug, I still log out.
            brcdapi_log.log('Login succeeded', True)
            ec = make_port_changes(session, _DEBUG_FID)
        except:
            brcdapi_log.log('Encountered a programming error', True)
            ec = -1

    obj = brcdapi_rest.logout(session)
    if pyfos_auth.is_error(obj):
        brcdapi_log.log('Logout failed:\n' + pyfos_auth.formatted_error_msg(obj), True)
    return ec

###################################################################
#
#                    Main Entry Point
#
###################################################################


if not _DOC_STRING:
    brcdapi_log.close_log(str(pseudo_main(_DEBUG_ID, _DEBUG_PW, _DEBUG_IP, _DEBUG_SEC, _DEBUG_VERBOSE, _DEBUG_LOG,
                                          _DEBUG_NL)))
