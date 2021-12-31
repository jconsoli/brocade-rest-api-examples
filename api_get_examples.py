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
:mod:`api_get_examples` - RESTConf API GET examples. Includes a GET for most requests supported in FOS v8.2.1c

**Description**

    Examples on how to use the brcdapi driver to make GET requests. The typical use is to gain an understanding of how
    a GET request is made or to evaluate GET request responses. To do this with a debugger, set _DEBUG True. Directly
    under _DEBUG you will see the input parameters. Search for "Set breakpoint" to see where to set a breakpoint to
    evaluate responses. To just print responses to the log and console, you can launch from a command shell (DOS Window
    for Windows environments) with the -d option.

    Search for "_chassis_rest_data" to modify chassis level requests and "fid_rest_data" to modify switch level
    requests.

    cli_poll_to_api.py began as a copy of this module. Many comments were added for people familiar with the CLI.

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 1.x.x     | 03 Jul 2019   | Experimental                                                                      |
    | 2.x.x     |               |                                                                                   |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.0     | 14 Nov 2020   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.1     | 27 Nov 2020   | Comment changes only.                                                             |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.2     | 09 Jan 2021   | Open log file.                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.3     | 13 Feb 2021   | Added # -*- coding: utf-8 -*-                                                     |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.4     | 14 Nov 2021   | Deprecated pyfos_auth                                                             |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.5     | 31 Dec 2021   | Use explicit exception clauses                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2019, 2020, 2021 Jack Consoli'
__date__ = '31 Dec 2021'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.5'

import argparse
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as brcdapi_auth
import brcdapi.log as brcdapi_log

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation
_DEBUG = False   # When True, use _DEBUG_ip, _DEBUG_id, _DEBUG_pw, _DEBUG_OUTF, and _DEBUG_d
_DEBUG_ip = 'xx.xxx.x.xxx'
_DEBUG_id = 'admin'
_DEBUG_pw = 'password'
_DEBUG_sec = None  # 'self'  # Use None or 'none' for HTTP. Use the certificate if HTTPS and not self signed
_DEBUG_fid = '128'
_DEBUG_d = False  # When True, all content and responses are formatted and printed (pprint).
_DEBUG_log = '_logs'
_DEBUG_nl = False

_chassis_rest_data = [
    # 'logical-switch/fibrechannel-logical-switch',  # Deprecated in FOS 8.2.1b. See below for replacement
    'brocade-fibrechannel-logical-switch/fibrechannel-logical-switch',
    'brocade-chassis/chassis',
    'brocade-chassis/ha-status',
    'brocade-fru/blade',
    'brocade-fru/fan',
    'brocade-fru/power-supply',
    'brocade-license/license',
    'brocade-security/auth-spec',
    # 'brocade-security/ipfilter-policy',
    # 'brocade-security/ipfilter-rule',
    # 'brocade-security/user-specific-password-cfg',
    # 'brocade-security/password-cfg',
    # 'brocade-security/user-config',
    # 'brocade-security/radius-server',
    # 'brocade-security/tacacs-server',
    # 'brocade-security/ldap-server',
    # 'brocade-security/ldap-role-map',
    # 'brocade-security/sec-crypto-cfg-template',
    # 'brocade-security/sec-crypto-cfg',
    # 'brocade-security/sshutil',
    # 'brocade-security/sshutil-key',
    # 'brocade-security/sshutil-public-key',
    # 'brocade-security/security-certificate',
    'brocade-snmp/system',
    'brocade-snmp/mib-capability',
    'brocade-snmp/trap-capability',
    'brocade-snmp/v1-account',
    'brocade-snmp/v1-trap',
    'brocade-snmp/v3-account',
    'brocade-snmp/v3-trap',
    'brocade-snmp/access-control',
    'brocade-time/time-zone',
    'brocade-time/clock-server',
    # 'brocade-module-version',
]
fid_rest_data = [
    'brocade-fabric/fabric-switch',
    'brocade-fibrechannel-switch/fibrechannel-switch',
    'brocade-interface/fibrechannel-statistics',
    'brocade-interface/fibrechannel',
    'brocade-interface/extension-ip-interface',
    'brocade-interface/gigabitethernet',
    'brocade-interface/gigabitethernet-statistics',
    'brocade-zone/defined-configuration',
    'brocade-zone/effective-configuration',
    'brocade-fdmi/hba',
    'brocade-fdmi/port',
    'brocade-name-server/fibrechannel-name-server',
    'brocade-fibrechannel-configuration/fabric',
    'brocade-fibrechannel-configuration/port-configuration',
    'brocade-fibrechannel-configuration/zone-configuration',
    'brocade-fibrechannel-configuration/switch-configuration',
    'brocade-fibrechannel-configuration/f-port-login-settings',
    # 'brocade-fibrechannel-trunk/trunk',
    # 'brocade-fibrechannel-trunk/performance',
    # 'brocade-fibrechannel-trunk/trunk-area',
    'brocade-logging/audit',
    # 'brocade-logging/syslog-server',
    # 'brocade-logging/log-quiet-control',
    # 'brocade-logging/log-setting',
    'brocade-logging/raslog',
    'brocade-logging/raslog-module',
    # 'brocade-logging/rule',    # Requires additional parameters. Not testing this at this time
    'brocade-maps/maps-config',
    'brocade-maps/dashboard-misc',
    'brocade-maps/dashboard-rule',
    'brocade-maps/group',
    'brocade-maps/rule',
    'brocade-maps/maps-policy',
    'brocade-maps/monitoring-system-matrix',
    'brocade-maps/switch-status-policy-report',
    'brocade-maps/paused-cfg',
    'brocade-maps/system-resources',
    'brocade-media/media-rdp',
    # 'brocade-access-gateway/device-list',
    # 'brocade-access-gateway/f-port-list',
    # 'brocade-access-gateway/n-port-map',
    # 'brocade-access-gateway/n-port-settings',
    # 'brocade-access-gateway/policy',
    # 'brocade-access-gateway/port-group',
    # 'brocade-extension-ip-route/extension-ip-route',
    # 'brocade-extension-ip-route/brocade-extension-ipsec-policy',
    # 'brocade-extension-tunnel/extension-circuit',
    # 'brocade-extension-tunnel/extension-circuit-statistics',
    # 'brocade-extension-tunnel/extension-tunnel',
    # 'brocade-extension-tunnel/extension-tunnel-statistics',
    # 'brocade-fibrechannel-diagnostics/fibrechannel-diagnostics',
    'brocade-security/auth-spec'
    ]


def parse_args():
    """Parses the module load command line

    :return: ip, id, pw, file
    :rtype: (str, str, str, str)
    """
    global _DEBUG_ip, _DEBUG_id, _DEBUG_pw, _DEBUG_sec, _DEBUG_fid, _DEBUG_d, _DEBUG_log, _DEBUG_nl

    if _DEBUG:
        return _DEBUG_ip, _DEBUG_id, _DEBUG_pw, _DEBUG_sec, _DEBUG_fid, _DEBUG_d, _DEBUG_log, _DEBUG_nl
    else:
        parser = argparse.ArgumentParser(description='GET request examples.')
        parser.add_argument('-ip', help='IP address', required=True)
        parser.add_argument('-id', help='User ID', required=True)
        parser.add_argument('-pw', help='Password', required=True)
        parser.add_argument('-fid', help='Virtual Fabric IDs. Separate multiple FIDs with a comma',
                            required=True)
        parser.add_argument('-s', help="(Optional) Default is HTTP. CA or self for HTTPS mode.", required=False,)
        buf = 'Enable debug logging. Prints the formatted data structures (pprint) to the log and console.'
        parser.add_argument('-d', help=buf, action='store_true', required=False)
        buf = '(Optional) Directory where log file is to be created. Default is to use the current directory. The ' \
              'log file name will always be "Log_xxxx" where xxxx is a time and date stamp.'
        parser.add_argument('-log', help=buf, required=False, )
        buf = '(Optional) No parameters. When set, a log file is not created. The default is to create a log file.'
        parser.add_argument('-nl', help=buf, action='store_true', required=False)
        args = parser.parse_args()
        return args.ip, args.id, args.pw, args.s, args.fid, args.d, args.log, args.nl


def pseudo_main():
    """Basically the main(). Did it this way to use with IDE
    :return: Exit code
    :rtype: int
    """
    ml = ['WARNING!!! Debug is enabled'] if _DEBUG else list()
    ip, user_id, pw, sec, fids, vd, log, nl = parse_args()
    if vd:
        brcdapi_rest.verbose_debug = True
    if sec is None:
        sec = 'none'
    if not nl:
        brcdapi_log.open_log(log)
    fl = [int(f) for f in fids.split(',')]
    ml.append('FIDs: ' + fids)
    brcdapi_log.log(ml, True)

    # Login
    session = brcdapi_rest.login(user_id, pw, ip, sec)
    if brcdapi_auth.is_error(session):
        brcdapi_log.log('Login failed:\n' + brcdapi_auth.formatted_error_msg(session), True)
        return -1

    # Get the Chassis data
    brcdapi_log.log('Chassis Data\n------------', True)
    for uri in _chassis_rest_data:
        brcdapi_log.log('URI: ' + uri, True)
        try:
            obj = brcdapi_rest.get_request(session, uri)
            if brcdapi_auth.is_error(obj):  # Set breakpoint here to inspect response
                brcdapi_log.log(brcdapi_auth.formatted_error_msg(obj), True)
        except BaseException as e:
            brcdapi_log.exception(['Error requesting ' + uri, 'Exception: ' + str(e)], True)

    # Get the Switch data
    for vf_id in fl:
        brcdapi_log.log('Switch data. FID: ' + str(vf_id) + '\n---------------------', True)
        for buf in fid_rest_data:
            brcdapi_log.log('URI: ' + buf, True)
            try:
                obj = brcdapi_rest.get_request(session, buf, vf_id)
                if brcdapi_auth.is_error(obj):  # Set breakpoint here to inspect response
                    brcdapi_log.log(brcdapi_auth.formatted_error_msg(obj), True)
            except BaseException as e:
                brcdapi_log.exception(['Error requesting ' + buf, 'Exception: ' + str(e)], True)

    # Logout
    obj = brcdapi_rest.logout(session)
    if brcdapi_auth.is_error(obj):
        brcdapi_log.log('Logout failed:\n' + brcdapi_auth.formatted_error_msg(obj), True)
        return -1

    return 0


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
