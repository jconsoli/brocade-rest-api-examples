#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2019, 2020, 2021, 2022 Jack Consoli.  All rights reserved.
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
    | 3.0.6     | 28 Apr 2022   | Added "running" to URI                                                            |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2019, 2020, 2021, 2022 Jack Consoli'
__date__ = '28 Apr 2022'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.6'

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
    'running/brocade-fibrechannel-logical-switch/fibrechannel-logical-switch',
    'running/brocade-chassis/chassis',
    'running/brocade-chassis/ha-status',
    'running/brocade-fru/blade',
    'running/brocade-fru/fan',
    'running/brocade-fru/power-supply',
    'running/brocade-license/license',
    'running/brocade-security/auth-spec',
    # 'running/brocade-security/ipfilter-policy',
    # 'running/brocade-security/ipfilter-rule',
    # 'running/brocade-security/user-specific-password-cfg',
    # 'running/brocade-security/password-cfg',
    # 'running/brocade-security/user-config',
    # 'running/brocade-security/radius-server',
    # 'running/brocade-security/tacacs-server',
    # 'running/brocade-security/ldap-server',
    # 'running/brocade-security/ldap-role-map',
    # 'running/brocade-security/sec-crypto-cfg-template',
    # 'running/brocade-security/sec-crypto-cfg',
    # 'running/brocade-security/sshutil',
    # 'running/brocade-security/sshutil-key',
    # 'running/brocade-security/sshutil-public-key',
    # 'running/brocade-security/security-certificate',
    'running/brocade-snmp/system',
    'running/brocade-snmp/mib-capability',
    'running/brocade-snmp/trap-capability',
    'running/brocade-snmp/v1-account',
    'running/brocade-snmp/v1-trap',
    'running/brocade-snmp/v3-account',
    'running/brocade-snmp/v3-trap',
    'running/brocade-snmp/access-control',
    'running/brocade-time/time-zone',
    'running/brocade-time/clock-server',
    # 'running/brocade-module-version',
]
fid_rest_data = [
    'running/brocade-fabric/fabric-switch',
    'running/brocade-fibrechannel-switch/fibrechannel-switch',
    'running/brocade-interface/fibrechannel-statistics',
    'running/brocade-interface/fibrechannel',
    'running/brocade-interface/extension-ip-interface',
    'running/brocade-interface/gigabitethernet',
    'running/brocade-interface/gigabitethernet-statistics',
    'running/brocade-zone/defined-configuration',
    'running/brocade-zone/effective-configuration',
    'running/brocade-fdmi/hba',
    'running/brocade-fdmi/port',
    'running/brocade-name-server/fibrechannel-name-server',
    'running/brocade-fibrechannel-configuration/fabric',
    'running/brocade-fibrechannel-configuration/port-configuration',
    'running/brocade-fibrechannel-configuration/zone-configuration',
    'running/brocade-fibrechannel-configuration/switch-configuration',
    'running/brocade-fibrechannel-configuration/f-port-login-settings',
    # 'running/brocade-fibrechannel-trunk/trunk',
    # 'running/brocade-fibrechannel-trunk/performance',
    # 'running/brocade-fibrechannel-trunk/trunk-area',
    'running/brocade-logging/audit',
    # 'running/brocade-logging/syslog-server',
    # 'running/brocade-logging/log-quiet-control',
    # 'running/brocade-logging/log-setting',
    'running/brocade-logging/raslog',
    'running/brocade-logging/raslog-module',
    # 'running/brocade-logging/rule',    # Requires additional parameters. Not testing this at this time
    'running/brocade-maps/maps-config',
    'running/brocade-maps/dashboard-misc',
    'running/brocade-maps/dashboard-rule',
    'running/brocade-maps/group',
    'running/brocade-maps/rule',
    'running/brocade-maps/maps-policy',
    'running/brocade-maps/monitoring-system-matrix',
    'running/brocade-maps/switch-status-policy-report',
    'running/brocade-maps/paused-cfg',
    'running/brocade-maps/system-resources',
    'running/brocade-media/media-rdp',
    # 'running/brocade-access-gateway/device-list',
    # 'running/brocade-access-gateway/f-port-list',
    # 'running/brocade-access-gateway/n-port-map',
    # 'running/brocade-access-gateway/n-port-settings',
    # 'running/brocade-access-gateway/policy',
    # 'running/brocade-access-gateway/port-group',
    # 'running/brocade-extension-ip-route/extension-ip-route',
    # 'running/brocade-extension-ip-route/brocade-extension-ipsec-policy',
    # 'running/brocade-extension-tunnel/extension-circuit',
    # 'running/brocade-extension-tunnel/extension-circuit-statistics',
    # 'running/brocade-extension-tunnel/extension-tunnel',
    # 'running/brocade-extension-tunnel/extension-tunnel-statistics',
    # 'running/brocade-fibrechannel-diagnostics/fibrechannel-diagnostics',
    'running/brocade-security/auth-spec'
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
