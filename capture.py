#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Copyright 2023, 2024, 2025 Jack Consoli.  All rights reserved.

**License**

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
the License. You may also obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
language governing permissions and limitations under the License.

The license is free for single customer use (internal applications). Use of this module in the production,
redistribution, or service delivery for commerce requires an additional license. Contact jack@consoli-solutions.com for
details.

**Description**

Except for login and logout, only performs GET operations. The KPIs to GET are specified by a command line parameter.
The options are:

    * A user supplied list of KPIs
    * All requests the chassis supports
    * A default list which are the resources the report.py module uses

The process is as follows:

    * GET the data
    * Add the data to the appropriated brcddb class using brcdapi.util.uri_map.area to determine which class
    * Once all data is captured, convert the brcddb.classes.project.ProjectObj to a plain dict and JSON dump to a file.

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+===================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Added collection of maps URIs, -clr, -nm option, CLI command processing.              |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 03 Apr 2024   | Explicitly defined parameters in call to api_int.get_batch(). Added version numbers   |
|           |               | of imported libraries.                                                                |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.3     | 16 Jun 2024   | Improved help messages.                                                               |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.4     | 06 Dec 2024   | Updated comments only.                                                                |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.5     | 12 Apr 2025   | FOS 9.2 updates.                                                                      |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.6     | 25 Aug 2025   | Added capture of active SCC policy and management ethernet address.                   |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2024, 2025 Consoli Solutions, LLC'
__date__ = '25 Aug 2025'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.6'

import signal
import sys
import datetime
import os
import brcdapi.log as brcdapi_log
import brcdapi.gen_util as gen_util
import brcdapi.fos_auth as fos_auth
import brcdapi.util as brcdapi_util
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.file as brcdapi_file
import brcdapi.port as brcdapi_port
import brcdapi.fos_cli as fos_cli
import brcddb.brcddb_project as brcddb_project
import brcddb.util.copy as brcddb_copy
import brcddb.api.interface as api_int
import brcddb.brcddb_common as brcddb_common

_DOC_STRING = False  # Should always be False. Prohibits any code execution. Only useful for building documentation
# _STAND_ALONE: True: Executes as a standalone module taking input from the command line. False: Does not automatically
# execute. This is useful when importing this module into another module that calls psuedo_main().
_STAND_ALONE = True  # See note above
_WRITE = True  # Should always be True. Used for debug only. Prevents the output file from being written when False

_report_kpi_l = [
    # 'running/brocade-fabric/fabric-switch',  Done automatically in brcddb.api.interface.get_chassis()
    # 'running/brocade-logging/audit-log',  # $ToDo Fix - FOS encounters an error which I'm assuming is when it wraps
    'running/brocade-logging/error-log',
    'running/brocade-fibrechannel-switch/fibrechannel-switch',
    'running/brocade-fibrechannel-switch/topology-domain',
    'running/brocade-fibrechannel-switch/topology-route',
    'running/brocade-interface/fibrechannel',
    'running/brocade-interface/fibrechannel-statistics',
    # 'running/brocade-interface/logical-e-port',
    'running/brocade-media/media-rdp',
    # 'running/brocade-fabric/access-gateway',
    'running/brocade-fibrechannel-routing/routing-configuration',
    'running/brocade-fibrechannel-routing/lsan-zone',
    'running/brocade-fibrechannel-routing/lsan-device',
    'running/brocade-fibrechannel-routing/edge-fabric-alias',
    'running/brocade-zone/defined-configuration',
    'running/brocade-zone/effective-configuration',
    'running/brocade-zone/fabric-lock',
    'running/brocade-fdmi/hba',
    'running/brocade-fdmi/port',
    'running/brocade-name-server/fibrechannel-name-server',
    'running/brocade-fabric-traffic-controller/fabric-traffic-controller-device',
    'running/brocade-fibrechannel-configuration/switch-configuration',
    'running/brocade-fibrechannel-configuration/f-port-login-settings',
    'running/brocade-fibrechannel-configuration/port-configuration',
    'running/brocade-fibrechannel-configuration/zone-configuration',
    'running/brocade-fibrechannel-configuration/fabric',
    'running/brocade-fibrechannel-configuration/chassis-config-settings',
    'running/brocade-fibrechannel-configuration/fos-settings',
    'running/brocade-ficon/cup',
    'running/brocade-ficon/logical-path',
    'running/brocade-ficon/rnid',
    'running/brocade-ficon/switch-rnid',
    'running/brocade-ficon/lirr',
    'running/brocade-ficon/rlir',
    'running/brocade-firmware/firmware-history',  # Still needed for pre-FOS 9.2.
    'running/brocade-fru/power-supply',
    'running/brocade-fru/fan',
    'running/brocade-fru/blade',
    'running/brocade-fru/history-log',
    'running/brocade-fru/sensor',
    'running/brocade-fru/wwn',
    'running/brocade-chassis/chassis',
    'running/brocade-chassis/ha-status',
    'running/brocade-chassis/version',
    'running/brocade-chassis/management-ethernet-interface',
    'running/brocade-maps/maps-config',
    'running/brocade-maps/rule',
    'running/brocade-maps/maps-policy',
    'running/brocade-maps/group',
    'running/brocade-maps/dashboard-rule',
    'running/brocade-maps/dashboard-history',
    'running/brocade-maps/dashboard-misc',
    # 'running/brocade-maps/system-resources',
    # 'running/brocade-maps/paused-cfg',
    # 'running/brocade-maps/monitoring-system-matrix',
    # 'running/brocade-maps/switch-status-policy-report',
    # 'running/brocade-maps/fpi-profile',
    'running/brocade-time/clock-server',
    'running/brocade-time/time-zone',
    'running/brocade-license/license',
    'running/brocade-security/active-scc-policy-member-list',
    'running/brocade-security/defined-scc-policy-member-list',
    'running/brocade-security/policy-distribution-config',
]
_all_fos_cli_l = [
    'fos_cli/portcfgshow',
    'fos_cli/portbuffershow',
]
_report_kpi_l.extend(_all_fos_cli_l)

_input_c_help = ('Optional. Name of file with list of KPIs to capture and/or FOS commands to execute. Note that FOS '
                 'commands are executed on all logical switches specified with the -fid option. FOS commands must '
                 'begin with "fos_cli/". Use * to capture all data the chassis supports + ' + ', '.join(_all_fos_cli_l))
_input_c_help += ' all FOS. The default is to capture all KPIs and FOS commands required for the report.'
_input_d = gen_util.parseargs_login_d.copy()
_input_d.update(
    f=dict(h='Required. Output file for captured data. ".json" is automatically appended.'),
    c=dict(r=False, h=_input_c_help),
    fid=dict(r=False,
             h='Optional. CSV list or range of FIDs to capture logical switch specific data. The default is to '
               'automatically determine all logical switch FIDs defined in the chassis.'),
    clr=dict(r=False, t='bool', d=False,
             h='Optional. No parameters. Clear port statistics after successful capture'),
    nm=dict(r=False, t='bool', d=False,
            h='Optional. No parameters. By default, all but the last octet of IP addresses are masked before being '
              'stored in the output file. This option preserves the full IP address. This is useful for having full '
              'IP addresses in reports and when using restore_all.py.'),
)
_input_d.update(gen_util.parseargs_log_d.copy())
_input_d.update(gen_util.parseargs_debug_d.copy())


def _kpi_list(session, c_file):
    """Returns the list of KPIs to capture

    :param session: Session object returned from brcdapi.fos_auth.login()
    :type session: dict
    :param c_file: Name of file with KPIs to read
    :type c_file: str, None
    :return: List of KPIs
    :rtype: list
    """
    global _report_kpi_l, _all_fos_cli_l

    kpi_l = _report_kpi_l if c_file is None else brcdapi_util.uris_for_method(session, 'GET', uri_d_flag=False) if \
        c_file == '*' else brcdapi_file.read_file(c_file)
    if c_file == '*':
        kpi_l.extend(_all_fos_cli_l)
    rl = list()
    for kpi in kpi_l:
        if isinstance(fos_cli.parse_cli(kpi), str):
            rl.append(kpi)
        else:
            uri_d = brcdapi_util.uri_d(session, kpi)
            if uri_d is not None:
                if 'GET' in uri_d['methods'] and uri_d['area'] != brcdapi_util.NULL_OBJ:
                    rl.append(kpi)
            else:
                # Different versions of FOS support different KPIs so log it but don't pester the operator with it.
                brcdapi_log.log(':UNKNOWN KPI: ' + kpi)

    return rl


def pseudo_main(ip, user_id, pw, outf, sec, c_file, fid_l, args_clr, args_nm):
    """Basically the main(). Did it this way so that it can be imported and called from another program.

    :param ip: IP address
    :type ip: str
    :param user_id: User ID
    :type user_id: str
    :param pw: Password
    :type pw: str
    :param outf: Name of output file
    :type outf: str
    :param sec: Type of HTTP security. Should be 'none' or 'self'
    :type sec: str
    :param c_file: Name of file containing URIs to GET.
    :type c_file: str, None
    :param fid_l: CSV list of FIDs to capture data for
    :type fid_l: list, None
    :param args_clr: If True, clear port stats after a capture
    :type: bool
    :param args_nm:
    :type args_nm: bool
    :return: Exit code. See exist codes in brcddb.brcddb_common
    :rtype: int
    """
    global __version__

    signal.signal(signal.SIGINT, brcdapi_rest.control_c)

    ec, write_file = None, False

    # Create project
    proj_obj = brcddb_project.new("Captured_data", datetime.datetime.now().strftime('%d %b %Y %H:%M:%S'))
    proj_obj.s_python_version(sys.version)
    proj_obj.s_description("This is a test")

    # Login
    session = api_int.login(user_id, pw, ip, sec, proj_obj)
    if fos_auth.is_error(session):
        return brcddb_common.EXIT_STATUS_API_ERROR

    # Collect the data
    try:
        api_int.get_batch(session, proj_obj, _kpi_list(session, c_file), fid=fid_l, no_mask=args_nm)
        write_file = _WRITE
        if args_clr:
            for chassis_obj in proj_obj.r_chassis_objects():  # There should only be one chassis object
                for fid in gen_util.convert_to_list(fid_l):
                    switch_obj = chassis_obj.r_switch_obj_for_fid(fid)
                    if switch_obj is not None:
                        brcdapi_port.clear_stats(session, fid, switch_obj.r_port_keys())
    except KeyboardInterrupt:
        brcdapi_log.log('Processing terminated by user.', echo=True)
        write_file = False
        ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
    except RuntimeError:
        brcdapi_log.log('Programming error encountered. See previous message', echo=True)
        write_file = False
        ec = brcddb_common.EXIT_STATUS_ERROR
    except FileNotFoundError:
        brcdapi_log.log('Input file, ' + str(c_file) + ', not found', echo=True)
        write_file = False
        ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
    except FileExistsError:
        brcdapi_log.log('Folder in ' + str(c_file) + ' does not exist', echo=True)
        write_file = False
        ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
    except PermissionError:
            brcdapi_log.log('Permission error writing ' + str(c_file), echo=True)
            ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
    except brcdapi_util.VirtualFabricIdError:
        brcdapi_log.log('Software error. Search the log for "Invalid FID" for details.', echo=True)
        ec = brcddb_common.EXIT_STATUS_API_ERROR
    except BaseException as e:
        brcdapi_log.log('Programming error encountered.: ' + str(type(e)) + ': ' + str(e), echo=True)
        write_file = False
        ec = brcddb_common.EXIT_STATUS_ERROR

    ec = ec if ec is not None else proj_obj.r_exit_code()

    # Logout
    brcdapi_log.log(api_int.logout(session), echo=True)

    # Dump the database to a file
    if write_file:
        brcdapi_log.log('Saving project to: ' + outf, echo=True)
        plain_copy = dict()
        brcddb_copy.brcddb_to_plain_copy(proj_obj, plain_copy)
        try:
            brcdapi_file.write_dump(plain_copy, outf)
            brcdapi_log.log('Save complete', echo=True)
        except FileNotFoundError:
            brcdapi_log.log('Input file, ' + outf + ', not found', echo=True)  # I don't think this can happen
            ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
        except FileExistsError:
            brcdapi_log.log('Folder in ' + outf + ' does not exist', echo=True)
            ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
        except PermissionError:
            brcdapi_log.log('Permission error writing ' + outf, echo=True)
            ec = brcddb_common.EXIT_STATUS_INPUT_ERROR

    return ec


def _get_input():
    """Parses the module load command line

    :return ec: Error code
    :rtype ec: int
    """
    global __version__, _input_d

    ec = brcddb_common.EXIT_STATUS_OK

    # Get command line input
    args_d = gen_util.get_input('Capture (GET) requests from a chassis', _input_d)

    # Set up logging
    brcdapi_rest.verbose_debug(args_d['d'])
    brcdapi_log.open_log(
        folder=args_d['log'],
        suppress=args_d['sup'],
        no_log=args_d['nl'],
        version_d=brcdapi_util.get_import_modules()
    )

    # Is the FID or FID range valid?
    args_fid_l = gen_util.range_to_list(args_d['fid']) if isinstance(args_d['fid'], str) else None
    args_fid_help = brcdapi_util.validate_fid(args_fid_l)
    if len(args_fid_help) > 0:
        ec = brcddb_common.EXIT_STATUS_INPUT_ERROR

    # Command line feedback
    ml = [
        os.path.basename(__file__) + ', ' + __version__,
        'IP, -ip:             ' + brcdapi_util.mask_ip_addr(args_d['ip'], keep_last=True),
        'ID, -id:             ' + args_d['id'],
        'Security, -s:        ' + args_d['s'],
        'Output file, -f:     ' + args_d['f'],
        'KPI file, -c:        ' + str(args_d['c']),
        'FID List, -fid:      ' + str(args_d['fid']),
        'Clear stats, -clr:   ' + str(args_d['clr']),
        'Log, -log:           ' + str(args_d['log']),
        'No log, -nl:         ' + str(args_d['nl']),
        'Debug, -d:           ' + str(args_d['d']),
        'Suppress, -sup:      ' + str(args_d['sup']),
        '',
    ]
    brcdapi_log.log(ml, echo=True)

    if ec != brcddb_common.EXIT_STATUS_OK:
        return ec

    args_f = brcdapi_file.full_file_name(args_d['f'], '.json')
    return pseudo_main(args_d['ip'], args_d['id'], args_d['pw'], args_f, args_d['s'], args_d['c'], args_fid_l,
                       args_d['clr'], args_d['nm'])


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
