#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2020, 2021, 2022 Jack Consoli.  All rights reserved.
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
:mod:`switch_create.py` - Examples on how to create a logical switch with some basic configuration

Scroll all the way to the bottom to find the entry point.

**Description**

    Examples on how to create a logical switch, add ports, and make some basic configuration changes. There is a user
    interface but if you are hacking this code, you are probably going to just take create_ls().

    If the FID already exists, the existing switch is modified. Any parameter that requires the switch to be disabled
    is skipped. There is no check to see if the switch is already disabled.

    While the simplistic approach used in this module is useful as a programming example, there isn't much validation.
    If the only time you ever plan on creating logical switches is for new switch deployment, that's probably good
    enough. More checking should be done for switches in production. For example, ports to be added to the switch are
    automatically found, set to the default state (which is disabled) and moved to the specified switch. In a production
    switch, it would be more appropriate to check to see if the port was in use (online) first. See
    applications/switch_config.py.

**Examples**

    To create a FICON switch with DID 10 on a fixed port switch with ports 0-11 and enable the switch ane the ports when
    done:

    py switch_create.py -ip 10.8.105.10 -id admin -pw password -s self -echo -fid 20 -name FICON_switch -did 10 -ficon \
            -ports 0-11 -se -pe

    To create a standard switch, FID 21, with an insistent DID of 11 on an 8 slot chassis switch with all ports on all
    blades except the core blades (ICL ports) and enable all the ports, it has to be done in 2 steps because the user
    interface in this module only allows a range of slot and port numbers.

    py switch_create.py -ip 10.8.105.10 -id admin -pw password -s self -echo -fid 21 -name Test_switch_21 -did 11 \
            -ports 3-6/0-47 -idid -pe
    py switch_create.py -ip 10.8.105.10 -id admin -pw password -s self -echo -fid 21 -ports 9-12/0-47 -se -pe

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 3.0.0     | 27 Nov 2020   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.1     | 09 Jan 2021   | Opened log file.                                                                  |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.2     | 13 Feb 2021   | Added # -*- coding: utf-8 -*-                                                     |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.3     | 14 Nov 2021   | Deprecated pyfos_auth                                                             |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.4     | 31 Dec 2021   | Updated comments only.                                                            |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.5     | 28 Apr 2022   | Added "running"                                                                   |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2020, 2021, 2022 Jack Consoli'
__date__ = '28 Apr 2022'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.5'

import argparse
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as brcdapi_auth
import brcdapi.log as brcdapi_log
import brcdapi.switch as brcdapi_switch
import brcdapi.port as brcdapi_port

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation
_DEBUG = False  # When True, use _DEBUG_IP, _DEBUG_ID, _DEBUG_PW, _DEBUG_OUTF, and _DEBUG_VERBOSE
_DEBUG_IP = '10.x.xxx.xx'
_DEBUG_ID = 'admin'
_DEBUG_PW = 'password'
_DEBUG_SEC = 'self'  # Use None or 'none' for HTTP. Use the certificate if HTTPS and not self signed
_DEBUG_FID = '20'  # A number from 1-128. For debug mode, it doesn't have to be a string
_DEBUG_NAME = 'FICON_Switch'
_DEBUG_DID = '10'  # This is decimal. For debug mode, it doesn't have to be a string
_DEBUG_IDID = True
_DEBUG_XISL = True
_DEBUG_FICON = True
_DEBUG_BASE = None
_DEBUG_PORTS = '0-11'
_DEBUG_GE_PORTS = None
_DEBUG_SE = True
_DEBUG_PE = False
_DEBUG_ECHO = True  # When true, echoes details of ports being moved.
_DEBUG_VERBOSE = False  # When True, all content and responses are formatted and printed (pprint).
_DEBUG_BANNER = "This is a test banner."  # FOS only allows 0-9, a-z, A-Z, and - in the banner.
_DEBUG_FAB_NAME = "Fabric_0"


def create_ls(session, fid, name, did, idid, xisl, base, ficon, ports, ge_ports, es, ep, echo):
    """Create a logical switch. Includes options to set a few basic parameters

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number to be created.
    :type fid: int
    :param name: User friendly name for the switch. Use None for FOS default switch name
    :type name: None, str
    :param did: Domain ID Use None for FOS default DID.
    :type did: None, int
    :param idid: If True, sets the DID to be insistent
    :type idid: None, bool
    :param xisl: If True, sets the allow XISL bit.
    :type xisl: None, bool
    :param base: If True, set the switch type to be a base switch
    :type base: None, bool
    :param ficon: If True set the switch type to be a FICON switch
    :type ficon: None, bool
    :param ports: Dictionary of ports to add to the switch. Key: FID where the ports reside. Value: list of ports
    :type ports: None, dict
    :param ge_ports: Same as ports but for GE ports
    :type ge_ports: None, dict
    :param es: If True, enable the switch. Otherwise, the switch is left disabled.
    :type es: None, bool
    :param ep: If True, enables all the ports in the switch. Otherwise, they are left disabled.
    :type ep: None, bool
    :param echo: If True, step-by-step activity (each request) is echoed to STD_OUT
    :type echo: None, bool
    :return: Error code. 0 - Success, -1 - failure
    :rtype: int
    """
    ec = 0

    # Does the switch already exist?
    switch_list = brcdapi_switch.logical_switches(session, echo)
    if brcdapi_auth.is_error(switch_list):
        brcdapi_log.log(['Error capturing switch list. Ports not added to FID ' + str(fid),
                         brcdapi_auth.formatted_error_msg(switch_list)], True)
        return -1
    fid_list = [switch_d['fabric-id'] for switch_d in switch_list]

    # Create the switch if it doesn't already exist
    if fid in fid_list:
        brcdapi_log.log('Modifying FID ' + str(fid))
    else:
        buf = 'Creating FID ' + str(fid) + '. This will take about 20 sec per switch + 25 sec per group of 32 ports.'
        brcdapi_log.log(buf, True)
        obj = brcdapi_switch.create_switch(session, fid, base, ficon, echo)
        if brcdapi_auth.is_error(obj):
            brcdapi_log.exception(['Error creating FID ' + str(fid), brcdapi_auth.formatted_error_msg(obj)], True)
            return -1

    # Set switch configuration parameters. Note: brocade-fibrechannel-switch/fibrechannel-switch requires the WWN and
    # must be an ordered dictionary. To save a little work, the ability to look up the WWN if it's not known and
    # setting up an ordered dictionary was built into one of the driver methods.
    sub_content = dict()
    if did is not None:
        if fid in fid_list:
            brcdapi_log.log('Cannot modify the domain ID in an existing switch.', True)
        else:
            sub_content.update({'domain-id': did})
    if name is not None:
        sub_content.update({'user-friendly-name': name})
    if ficon:
        sub_content.update({'in-order-delivery-enabled': True, 'dynamic-load-sharing': 'two-hop-lossless-dls'})
    # I didn't bother with a fabric name or banner in the shell interface. I have no idea why the fabric name is set and
    # read in the switch parameters, but it is.
    if _DEBUG_FAB_NAME is not None:
        sub_content.update({'fabric-user-friendly-name': _DEBUG_FAB_NAME})
    if _DEBUG_BANNER is not None:
        sub_content.update({'banner': _DEBUG_BANNER})
    # If there is nothing to update, the library will do nothing and return good status.
    obj = brcdapi_switch.fibrechannel_switch(session, fid, sub_content, None, echo)
    if brcdapi_auth.is_error(obj):
        brcdapi_log.exception(['Failed to configure FID ' + str(fid), brcdapi_auth.formatted_error_msg(obj)], True)
        ec = -1

    # Set the fabric parameters. Note: Setting up fabric parameters is pretty straight forward so there is no driver
    # method for it.
    if fid in fid_list:
        brcdapi_log.log('Changing XISL use in an existing switch is not supported by this utility.', True)
    elif not xisl:  # XISL (ability to use the base switch for ISLs) is enabled by default so we only need to disable it
        obj = brcdapi_rest.send_request(session,
                                        'running/brocade-fibrechannel-configuration/switch-configuration',
                                        'PATCH',
                                        {'switch-configuration': {'xisl-enabled': False}},
                                        fid)
        if brcdapi_auth.is_error(obj):
            ml = ['Failed to disable XISL for FID ' + str(fid),
                  brcdapi_auth.formatted_error_msg(obj),
                  'Enabling and disabling of XISLs via the API was not supported until FOS v9.0.',
                  'Unless there are other error messages, all other operations are or will be completed as expected.']
            brcdapi_log.exception(ml, True)
            ec = -1

    # Insistent domain ID is set automatically with FICON switches. The API returns an error if you try to set it.
    if idid and not ficon:
        obj = brcdapi_rest.send_request(session,
                                        'running/brocade-fibrechannel-configuration/fabric',
                                        'PATCH',
                                        {'fabric': {'insistent-domain-id-enabled': True}},
                                        fid)
        if brcdapi_auth.is_error(obj):
            brcdapi_log.exception(['Failed to set insistent domain id for FID ' + str(fid),
                                   brcdapi_auth.formatted_error_msg(obj)], True)
            ec = -1

    # Add the ports to the switch. This has to be done one FID at a time.
    tl = list(ports.keys())  # The keys are the FIDs so this is the list of all FIDs that have ports to be moved.
    tl.extend([k for k in ge_ports.keys() if k not in tl])  # Add FIDs for GE ports
    for k in tl:  # For every FID with ports to move
        obj = brcdapi_switch.add_ports(session, fid, k, ports.get(k), ge_ports.get(k), echo)
        if brcdapi_auth.is_error(obj):
            brcdapi_log.log(['Error adding ports from FID ' + str(k), brcdapi_auth.formatted_error_msg(obj)], True)
            ec = -1

    # Enable the switch
    if es is not None and es:
        obj = brcdapi_switch.fibrechannel_switch(session, fid, {'is-enabled-state': True}, None, echo)
        if brcdapi_auth.is_error(obj):
            brcdapi_log.log(['Failed to enable FID ' + str(fid), brcdapi_auth.formatted_error_msg(obj)], True)
            ec = -1

    # Enable the ports we just added
    if ep is not None and ep:
        for k in tl:
            obj = brcdapi_port.enable_port(session, fid, True, ports.get(k) + ge_ports.get(k), True)
            if brcdapi_auth.is_error(obj):
                brcdapi_log.log(['Failed to enable ports on FID ' + str(fid), brcdapi_auth.formatted_error_msg(obj)],
                                True)
                ec = -1

    return ec


def _parse_ports(session, fid, i_ports, i_ge_ports, echo):
    """This method has nothing to do with configuring switches. It is for parsing the user input used in this module
    only. It creates a dictionary, key is the FID number and value is the list of ports. This dictionary is used in
    ls_create() to determine the ports associated with each FID that is to be moved to the new FID.

    :param session: Session object returned from brcdapi.brcdapi_auth.login()
    :type session: dict
    :param fid: Logical FID number to be created.
    :type fid: int
    :param i_ports: The value for -ports as it was passed in the command shell.
    :type i_ports: str
    :param i_ge_ports: The value for -ge_ports as it was passed in the command shell.
    :type i_ge_ports: str
    :param echo: If True, step-by-step activity (each request) is echoed to STD_OUT
    :type echo: None, bool
    :return port_d: Dictionary whose key is the FID and value a list of ports in that FID to be moved
    :rtype port_d: dict
    :return ge_port_d: Dictionary whose key is the FID and value a list of ports in that FID to be moved
    :rtype ge_port_d: dict
    """

    """This module and it's user interface was intended as a means to provide an example of how to use the library, not
    an end all module for configuring switches. As such, the user interface is limited to contiguous slots and ports;
    however, the library accepts a list of ports in any order.

    When moving ports via the CLI, lscfg --config xxx -port y, the ports being moved cannot have any special
    configuration parameters. Otherwise, an error is returned and the user must set the ports to their default
    configuration. To change the port configurations, the user must know what FID each port is in. The library must
    do the same thing.

    Automation programs do not have a user so the program must be able to figure out where the ports are. The
    brcdapi_switch.add_ports() method checks the configuration of each port and, if necessary, sets them to
    their default configuration before moving them. The input to brcdapi_switch.add_ports() is simplistic. The
    caller is responsible for figuring out where the ports to move are. It takes two dictionaries, one for standard
    FC ports and the other for IP ports, as input. In each dictionary, the key is the FID number and the value is
    the list of ports, in standard s/p format.
    
    Your code can derive the list of ports anyway it wants. The user interface was just a mechanism to illustrate how to
    use the API for creating a logical switch so not much time was spent developing it. You could use
    switch_add_ports.py to add additional ports as a quick solution to creating logical switches but keep in mind that
    the primary intent of this script is to provide programming examples.
    
    The code below does the following:

    1. Creates a list of ports in s/p notation that matches the user input.
    2. Reads all the ports for all FIDs in the chassis
    3. Builds a dictionary whose key if the FID number and whose value is the list of ports in that FID that are
       also in the list created in step 1. This is the structure that is passed to create_ls()
    """
    port_d = dict(
        ports=dict(input=i_ports, ref='port-member-list', port_l=list(), ports=dict()),
        ge_ports=dict(input=i_ge_ports, ref='ge-port-member-list', port_l=list(), ports=dict())
    )

    # Step 1: Create list of ports that match the user input
    if isinstance(i_ports, str) or isinstance(i_ge_ports, str):
        for k, d in port_d.items():
            if isinstance(d['input'], str):
                tl = d['input'].split('/')
                if len(tl) == 1:
                    input_slots = '0'
                    input_ports = tl[0]
                else:
                    input_slots = tl[0]
                    input_ports = tl[1]
                tl = input_slots.split('-')
                slot_l = tl[0] if len(tl) == 1 else [str(i) for i in range(int(tl[0]), int(tl[1]) + 1)]
                tl = input_ports.split('-')
                port_l = tl[0] if len(tl) == 1 else [str(i) for i in range(int(tl[0]), int(tl[1]) + 1)]
                for s in slot_l:
                    d['port_l'].extend([s + '/' + p for p in port_l])

        # Step 2: Read the port list for each FID
        switch_list = brcdapi_switch.logical_switches(session, echo)
        if brcdapi_auth.is_error(switch_list):
            brcdapi_log.log(['Error capturing switch list. Ports not added to FID ' + str(fid),
                             brcdapi_auth.formatted_error_msg(switch_list)], True)

        # Step 3: Build the dictionaries for input to brcdapi_switch.add_ports()
        else:
            # Build the dictionaries with the list of ports that match the user input by FID.
            for k, d in port_d.items():
                for switch_d in switch_list:
                    x_fid = switch_d['fabric-id']
                    # We haven't created the logical switch yet so x_fid will never == fid in the test below. This
                    # check is here to remind programmers who are using this module as an example of how to build a
                    # switch that you may need to perform this check. FOS will return an error if you try to move a
                    # port to the FID the port already is in.
                    if x_fid != fid:
                        tl = list() if switch_d[d['ref']].get('port-member') is None else \
                            switch_d[d['ref']].get('port-member')
                        d['ports'].update({x_fid: [p for p in tl if p in d['port_l']]})

    return port_d['ports']['ports'], port_d['ge_ports']['ports']


def parse_args():
    """Parses the module load command line

    :return ip: Switch IP address
    :rtype ip: str
    :return id: User ID
    :rtype id: str
    :return pw: User password
    :rtype ip: str
    :return sec: Secure method. None for HTTP, otherwise the certificate or 'self' if self signed
    :rtype sec: str, None
    :return fids: FID(s) to delete
    :rtype fids: str
    :return vd: Verbose debug flag.
    :rtype vd: bool
    """
    global _DEBUG_IP, _DEBUG_ID, _DEBUG_PW, _DEBUG_SEC, _DEBUG_FID, _DEBUG_NAME, _DEBUG_DID, _DEBUG_IDID, _DEBUG_XISL,\
        _DEBUG_BASE, _DEBUG_FICON, _DEBUG_PORTS, _DEBUG_GE_PORTS, _DEBUG_SE, _DEBUG_PE, _DEBUG_ECHO, _DEBUG_VERBOSE, \
        _DEBUG_LOG, _DEBUG_NL

    if _DEBUG:
        return _DEBUG_IP, _DEBUG_ID, _DEBUG_PW, _DEBUG_SEC, _DEBUG_FID, _DEBUG_NAME, _DEBUG_DID, _DEBUG_IDID, \
               _DEBUG_XISL, _DEBUG_FICON, _DEBUG_BASE, _DEBUG_PORTS, _DEBUG_GE_PORTS, _DEBUG_SE, _DEBUG_PE, \
               _DEBUG_ECHO, _DEBUG_VERBOSE, _DEBUG_LOG, _DEBUG_NL
    else:
        parser = argparse.ArgumentParser(description='Create a logical switch.')
        parser.add_argument('-ip', help='(Required) IP address', required=True)
        parser.add_argument('-id', help='(Required) User ID', required=True)
        parser.add_argument('-pw', help='(Required) Password', required=True)
        parser.add_argument('-s', help="(Optional) Default is HTTP. CA or self for HTTPS mode.", required=False)
        parser.add_argument('-fid', help='(Required) Virtual Fabric IDs to create.', required=True)
        buf = '(Optional) Switch user friendly name. Default is "switchxx" where "xx" is the domain ID.'
        parser.add_argument('-name', help=buf, required=False)
        parser.add_argument('-did', help='(Optional) Sets the switch domain ID. Default is 1', required=False)
        buf = '(Optional) No parameters. When set, makes the domain ID insistent.'
        parser.add_argument('-idid', help=buf, action='store_true', required=False)
        buf = '(Optional) No parameters. When set, permits use of ISL in base switch.'
        parser.add_argument('-xisl', help=buf, action='store_true', required=False)
        buf = '(Optional) No parameters. When set, defines the switch as a base switch.'
        parser.add_argument('-base', help=buf, action='store_true', required=False)
        buf = '(Optional) No parameters. When set, defines the switch as a FICON (mainframe) switch.'
        parser.add_argument('-ficon', help=buf, action='store_true', required=False)
        buf = '(Optional) Ports to add. Default is none. Accepts a range. For example, for all ports of slots 3 & 4'\
              ' you can enter "-ports 3-4/0-47".'
        parser.add_argument('-ports', help=buf, required=False)
        parser.add_argument('-ge_ports', help='(Optional) Same as -ports but for GE ports.', required=False)
        parser.add_argument('-se', help="(Optional) Enable switch. Default is disabled.", action='store_true',
                            required=False)
        parser.add_argument('-pe', help="(Optional) Enable ports. Default is disabled.", action='store_true',
                            required=False)
        buf = '(Optional) Echoes activity detail to STD_OUT. Recommended because there are multiple operations that '\
              'can be very time consuming.'
        parser.add_argument('-echo', help=buf, action='store_true', required=False)
        buf = '(Optional) Enable debug logging. Prints the formatted data structures (pprint) to the log and console.'
        parser.add_argument('-d', help=buf, action='store_true', required=False)
        buf = '(Optional) Directory where log file is to be created. Default is to use the current directory. The log ' \
              'file name will always be "Log_xxxx" where xxxx is a time and date stamp.'
        parser.add_argument('-log', help=buf, required=False, )
        buf = '(Optional) No parameters. When set, a log file is not created. The default is to create a log file.'
        parser.add_argument('-nl', help=buf, action='store_true', required=False)
        args = parser.parse_args()
        return args.ip, args.id, args.pw, args.s, args.fid, args.name, args.did, args.idid, args.xisl, args.base, \
               args.ficon, args.ports, args.ge_ports, args.se, args.pe, args.echo, args.d, args.log, args.nl


def pseudo_main():
    """Basically the main().

    :return: Exit code
    :rtype: int
    """
    ec = 0

    # Get and condition the command line input
    ml = ['WARNING!!! Debug is enabled'] if _DEBUG else list()
    ip, user_id, pw, sec, fid, name, did, idid, xisl, base, ficon, i_ports, i_ge_ports, es, ep, echo, vd, log, nl = \
        parse_args()
    if vd:
        brcdapi_rest.verbose_debug = True
    if sec is None:
        sec = 'none'
        ml.append('Access:        HTTP')
    else:
        ml.append('Access:        HTTPS')
    if not nl:
        brcdapi_log.open_log(log)
    try:
        fid = int(fid)
        if fid < 1 or fid > 128:
            raise
    except:
        brcdapi_log.log('Invalid fid. FID must be an integer between 1-128', True)
        return -1
    if did is not None:
        try:
            did = int(did)
            if did < 1 or did > 239:
                raise
        except:
            brcdapi_log.log('Invalid DID. DID must be an integer between 1-239', True)
            return -1
    ml.append('FID:           ' + str(fid))
    ml.append('Name:          ' + str(name))
    ml.append('DID:           ' + str(did))
    ml.append('Insistent:     ' + str(idid))
    ml.append('xisl:          ' + str(xisl))
    ml.append('base:          ' + str(base))
    ml.append('ficon:         ' + str(ficon))
    ml.append('ports:         ' + str(i_ports))
    ml.append('ge_ports:      ' + str(i_ge_ports))
    ml.append('Enable switch: ' + str(es))
    ml.append('Enable ports:  ' + str(ep))
    brcdapi_log.log(ml, True)
    base = False if base is None else base
    ficon = False if ficon is None else ficon
    es = False if es is None else es
    ep = False if ep is None else ep
    echo = False if echo is None else echo

    # Login
    brcdapi_log.log('Attempting login', True)
    session = brcdapi_rest.login(user_id, pw, ip, sec)
    if brcdapi_auth.is_error(session):
        brcdapi_log.log(['Login failed. API error message is:', brcdapi_auth.formatted_error_msg(session)], True)
        return -1
    brcdapi_log.log('Login succeeded.', True)

    try:  # I always do a try in code development so that if there is a code bug, I still log out.

        # Get a list of ports to move to the new switch
        port_d, ge_port_d = _parse_ports(session, fid, i_ports, i_ge_ports, echo)

        # We're done with conditioning the user input. Now create the logical switch.
        ec = create_ls(session, fid, name, did, idid, xisl, base, ficon, port_d, ge_port_d, es, ep, echo)

    except:
        brcdapi_log.log('Encountered a programming error', True)
        ec = -1

    # Logout
    obj = brcdapi_rest.logout(session)
    if brcdapi_auth.is_error(obj):
        brcdapi_log.log(['Logout failed. API error message is:',  brcdapi_auth.formatted_error_msg(obj)], True)
    return ec


###################################################################
#
#                    Main Entry Point
#
###################################################################
if _DOC_STRING:
    print('_DOC_STRING set. No processing')
    exit(0)

_ec = pseudo_main()
brcdapi_log.close_log('Processing Complete. Exit code: ' + str(_ec))
exit(_ec)
