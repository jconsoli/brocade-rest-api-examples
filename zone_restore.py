#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Copyright 2023, 2024, 2025 Consoli Solutions, LLC.  All rights reserved.

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

Sets the zone configuration DB to that of a previously captured zone DB

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Removed deprecated parameter in enable_zonecfg()                                      |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 03 Apr 2024   | Added version numbers of imported libraries. Fixed user ID.                           |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.3     | 15 May 2024   | Improved -scan output.                                                                |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.4     | 16 Jun 2024   | Made -fid not required when using -scan option.                                       |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.5     | 29 Oct 2024   | Fixed -fid help message.                                                              |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.6     | 06 Dec 2024   | Fixed spelling mistake in help message.                                               |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.7     | 25 Aug 2025   | Use brcddb.util.util.get_import_modules to dynamically determined imported libraries. |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2023, 2024, 2025 Consoli Solutions, LLC'
__date__ = '25 Aug 2025'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.7'

import signal
import os
import brcdapi.gen_util as gen_util
import brcdapi.log as brcdapi_log
import brcdapi.fos_auth as fos_auth
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.util as brcdapi_util
import brcdapi.file as brcdapi_file
import brcddb.brcddb_project as brcddb_project
import brcddb.brcddb_common as brcddb_common
import brcddb.brcddb_fabric as brcddb_fabric
import brcddb.api.interface as api_int
import brcddb.api.zone as api_zone

_DOC_STRING = False  # Should always be False. Prohibits any code execution. Only useful for building documentation
# _STAND_ALONE: True: Executes as a standalone module taking input from the command line. False: Does not automatically
# execute. This is useful when importing this module into another module that calls psuedo_main().
_STAND_ALONE = True  # See note above

_input_d = gen_util.parseargs_login_false_d.copy()
_input_d.update(
    fid=dict(r=False, t='int', v=gen_util.range_to_list('1-128'),
             h='Required unless using -scan. Fabric ID of logical switch whose zone database is be restored (target '
               'switch).'),
    i=dict(h='Required. Captured data file from the output of capture.py, combine.py, or multi_capture.py.'),
    wwn=dict(r=False,
             h='Optional with -scan. Otherwise, required. Fabric WWN for the source zone database in the file '
               'specified with -i.'),
    a=dict(r=False,
           h='Optional. Specifies the zone zone configuration to activate. If not specified, no change is made to the '
             'effective configuration. If a zone configuration is in effect and this option is not specified, the '
             'effective zone may result in the defined zone configuration being inconsistent with the effective zone '
             'configuration.'),
    cli=dict(r=False,
             h='Optional. Name of file for CLI commands.')
)
_input_d.update(gen_util.parseargs_scan_d.copy())
_input_d.update(gen_util.parseargs_log_d.copy())
_input_d.update(gen_util.parseargs_debug_d.copy())
_required_input = ('ip', 'id', 'pw', 'fid', 'wwn')

_kpis_for_capture = ('running/brocade-fibrechannel-switch/fibrechannel-switch',
                     'running/brocade-interface/fibrechannel',
                     'running/brocade-zone/defined-configuration',
                     'running/brocade-zone/effective-configuration',
                     'running/brocade-fibrechannel-configuration/zone-configuration',
                     'running/brocade-fibrechannel-configuration/fabric')
_ZONE_KPI_FILE = '_zone_merge_kpis.txt'

_control_tables = {
    'FabricObj': {
        '/_(obj_key|project_obj|alerts|base_logins|port_map|eff_zone_objs|switch_keys|login_objs)': dict(skip=True),
        '/_(fdmi_node_objs|fdmi_port_objs|flags|port_map|flags|reserved_keys)': dict(skip=True),
        '/brocade-zone/(.*)': dict(skip=True),  # Everything in brocade-zone is already in the object
    },
    'ZoneCfgObj': {
        '/_(obj_key|project_obj|alerts|flags|fabric_key|reserved_keys)': dict(skip=True),
    },
    'ZoneObj': {
        '/_(obj_key|project_obj|alerts|flags|fabric_key|reserved_keys)': dict(skip=True),
    },
    'AliasObj': {
        '/_(obj_key|project_obj|alerts|flags|fabric_key|reserved_keys)': dict(skip=True),
    },
}

_MAX_ZONE_MEM = 4
_MAX_LINES = 20
_cli_hdr_0 = ['########################################################',
              '#                                                      #']
_cli_hdr_1 = ['#                                                      #',
              '########################################################',
              '']


def _cli_commands(fab_obj):
    """Generate CLI commands

    :param fab_obj: Fabric object
    :type fab_obj: brcddb.classes.fabric.FabricObj
    :return: Status code
    :rtype: int
    """
    global _cli_hdr_0, _cli_hdr_1

    ec, rl = brcddb_common.EXIT_STATUS_OK, list()
    control_l = (
        dict(disp='#                 Aliases                              #',
             cmd='alicreate',
             add='aliadd',
             obj_l=fab_obj.r_alias_objects(),
             zone_flag=False),
        dict(disp='#                 Zones                                #',
             cmd='zonecreate',
             add='zoneadd',
             obj_l=fab_obj.r_zone_objects(),
             zone_flag=True),
        dict(disp='#           Zone Configurations                        #',
             cmd='cfgcreate',
             add='cfgadd',
             obj_l=fab_obj.r_zonecfg_objects(),
             zone_flag=False)
    )

    # Generate the CLI commands
    for control_d in control_l:

        # Add the header
        rl.extend(_cli_hdr_0)
        rl.append(control_d['disp'])
        rl.extend(_cli_hdr_1)

        line = 0
        for obj in control_d['obj_l']:
            if obj.r_obj_key() == '_effective_zone_cfg':
                continue

            # Figure out what the command parameters are
            buf, add_buf, name_start, name_end, add_mem_buf = control_d['cmd'], control_d['add'], ' "', '", ', ''
            mem_l = obj.r_members()
            if control_d['zone_flag']:
                zone_type = obj.r_type()
                if zone_type == brcddb_common.ZONE_TARGET_PEER:
                    continue
                if zone_type == brcddb_common.ZONE_USER_PEER:
                    # Add a line space if necessary
                    if line >= _MAX_LINES:
                        rl.append('')
                        line = 0
                    else:
                        line += 1
                    name_start = ' --peerzone "'
                    name_end = '" -members '
                    rl.append(buf + name_start + obj.r_obj_key() + '" -principal "' + ';'.join(obj.r_pmembers()) + '"')
                    buf = add_buf + name_start + obj.r_obj_key() + name_end
                else:
                    buf += name_start + obj.r_obj_key() + name_end
            else:
                buf += name_start + obj.r_obj_key() + name_end

            # Add the members
            mem_len = len(mem_l)
            i, x = 0, min(_MAX_ZONE_MEM, mem_len)

            # Add a line space if necessary
            if line >= _MAX_LINES:
                rl.append('')
                line = 0
            else:
                line += 1

            rl.append(buf + '"' + ';'.join(mem_l[i:x]) + '"')
            i = x
            while i < mem_len:
                x = i + min(_MAX_ZONE_MEM, mem_len)

                # Add a line space if necessary
                if line >= _MAX_LINES:
                    rl.append('')
                    line = 0
                else:
                    line += 1

                rl.append(add_buf + name_start + obj.r_obj_key() + name_end + '"' + ';'.join(mem_l[i:x]) + '"')
                i = x
        rl.append('')

    return rl


def pseudo_main(ip, user_id, pw, sec, scan_flag, fid, cfile, wwn, zone_cfg, cli_file):
    """Basically the main(). Did it this way so that it can easily be used as a standalone module or called externally.

    :param ip: IP address
    :type ip: str
    :param user_id: User ID
    :type user_id: str
    :param pw: Password
    :type pw: str
    :param sec: Type of HTTP security. Should be 'none' or 'self'
    :type sec: str
    :param scan_flag: If True, do not make any zoning changes. Just scan the fabrics
    :type scan_flag: bool
    :param fid: Fabric ID
    :type fid: int
    :param cfile: Captured data file name
    :type cfile: str
    :param wwn: WWN
    :type wwn: str
    :param zone_cfg: Name of zone configuration file
    :type zone_cfg: str
    :param cli_file: Name of file containing the CLI commands
    :type cli_file: None, str
    :return: Exit code. See exit codes in brcddb.brcddb_common
    :rtype: int
    """
    ec = brcddb_common.EXIT_STATUS_OK

    # Read the project file
    proj_obj = brcddb_project.read_from(cfile)
    if proj_obj is None:
        return brcddb_common.EXIT_STATUS_ERROR

    fab_obj = proj_obj.r_fabric_obj(wwn)
    if scan_flag:
        brcdapi_log.log(brcddb_project.scan(proj_obj), echo=True)
        return brcddb_common.EXIT_STATUS_OK
    elif fab_obj is None:
        brcdapi_log.log(wwn + ' does not exist in ' + cfile + '. Try using the -scan option', echo=True)
        return brcddb_common.EXIT_STATUS_INPUT_ERROR

    if isinstance(cli_file, str):
        try:
            with open(cli_file, 'w') as f:
                f.write('\n'.join(_cli_commands(fab_obj)))
            f.close()
        except FileNotFoundError:
            brcdapi_log.log(['', 'Folder in path ' + cli_file + ' does not exist.', ''], echo=True)
            ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
        except PermissionError:
            brcdapi_log.log(['', 'Permission error writing ' + cli_file + '.', ''], echo=True)
            ec = brcddb_common.EXIT_STATUS_INPUT_ERROR

        return ec

    # Login
    session = api_int.login(user_id, pw, ip, sec, proj_obj)
    if fos_auth.is_error(session):
        brcdapi_log.log(fos_auth.formatted_error_msg(session), echo=True)
        return brcddb_common.EXIT_STATUS_ERROR

    try:
        # Make the zoning change
        brcdapi_log.log('Sending zone updates to FID ' + str(fid), echo=True)
        obj = api_zone.replace_zoning(session, fab_obj, fid, fab_obj.r_defined_eff_zonecfg_key())
        if fos_auth.is_error(obj):
            brcdapi_log.log(fos_auth.formatted_error_msg(obj), echo=True)
        else:
            brcdapi_log.log('Zone restore completed successfully.', echo=True)

        # Activate the zone configuration
        if zone_cfg is not None:
            brcdapi_log.log('Enabling zone configuration ' + zone_cfg + ', fid: ' + str(fid), echo=True)
            api_zone.enable_zonecfg(session, fid, zone_cfg)

    except FileNotFoundError:
        pass
    except BaseException as e:
        brcdapi_log.log(['', 'Software error.', str(type(e)) + ': ' + str(e)], echo=True)

    # Logout
    obj = brcdapi_rest.logout(session)
    if fos_auth.is_error(obj):
        brcdapi_log.log(fos_auth.formatted_error_msg(obj), echo=True)

    return ec


def _get_input():
    """Retrieves the command line input, reads the input Workbook, and validates the input

    :return: Exit code. See exit codes in brcddb.brcddb_common
    :rtype: int
    """
    global __version__, _input_d, _required_input

    # Initialize the return variables
    ec, el = brcddb_common.EXIT_STATUS_OK, list()

    # Get command line input
    buf = 'Sets the zone database to that of a previous capture. Although typically used to restore a zone database, '\
          'this module can be used to set the zone database to that of any fabric.'
    args_d = gen_util.get_input(buf, _input_d)

    # Set up logging
    if args_d['d']:
        brcdapi_rest.verbose_debug(True)
    brcdapi_log.open_log(
        folder=args_d['log'],
        suppress=args_d['sup'],
        no_log=args_d['nl'],
        version_d=brcdapi_util.get_import_modules()
    )

    # Validate the input
    args_fid_help = ''
    if args_d['cli'] is None and not args_d['scan']:
        if args_d['fid'] is None:
            args_fid_help = ' *ERROR Required parameter when -cli or -scan is not specified.'
        for key in _required_input:
            if args_d[key] is None:
                el.append('Missing ' + key)
                ec = brcddb_common.EXIT_STATUS_INPUT_ERROR

    ml = [os.path.basename(__file__) + ', ' + __version__,
          'IP address, -ip:         ' + brcdapi_util.mask_ip_addr(args_d['ip']),
          'ID, -id:                 ' + str(args_d['id']),
          'HTTPS, -s:               ' + str(args_d['s']),
          'FID, -fid:               ' + str(args_d['fid']) + args_fid_help,
          'Input file, -i:          ' + args_d['i'],
          'WWN, -wwn:               ' + str(args_d['wwn']),
          'Activate zone cfg, -a:   ' + str(args_d['a']),
          'Scan, -scan:             ' + str(args_d['scan']),
          'CLI file, -cli:          ' + str(args_d['cli']),
          'Log, -log:               ' + str(args_d['log']),
          'No log, -nl:             ' + str(args_d['nl']),
          'Debug, -d:               ' + str(args_d['d']),
          'Suppress, -sup:          ' + str(args_d['sup']),
          '',
          ]
    brcdapi_log.log(ml, echo=True)

    if len(el) > 0:
        el.append('Use the -h option for additional help.')
        brcdapi_log.log(el, echo=True)
        return brcddb_common.EXIT_STATUS_INPUT_ERROR

    cfile = brcdapi_file.full_file_name(args_d['i'], '.json')
    cli_file = brcdapi_file.full_file_name(args_d['cli'], '.txt')

    signal.signal(signal.SIGINT, brcdapi_rest.control_c)

    return ec if ec != brcddb_common.EXIT_STATUS_OK else \
        pseudo_main(args_d['ip'], args_d['id'], args_d['pw'], args_d['s'], args_d['scan'], args_d['fid'], cfile,
                    args_d['wwn'], args_d['a'], cli_file)


##################################################################
#
#                    Main Entry Point
#
###################################################################
if _DOC_STRING:
    print('_DOC_STRING is True. No processing')
    exit(0)

if _STAND_ALONE:
    _ec = _get_input()
    brcdapi_log.close_log(['', 'Processing Complete. Exit code: ' + str(_ec)], echo=True)
    exit(_ec)
