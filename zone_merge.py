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

Merges the zones from multiple fabrics

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Use brcddb_project.scan() with -scan option. Removed deprecated parameter in          |
|           |               | enable_zonecfg()                                                                      |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 03 Apr 2024   | Added version numbers of imported libraries.                                          |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.3     | 16 Jun 2024   | Improved help messages.                                                               |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.4     | 06 Dec 2024   | Updated comments only.                                                                |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.5     | 01 Mar 2025   | Error message enhancements.                                                           |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.6     | 25 Aug 2025   | Use brcddb.util.util.get_import_modules to dynamically determined imported libraries. |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2023, 2024, 2025 Consoli Solutions, LLC'
__date__ = '25 Aug 2025'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.6'

import sys
import datetime
import os
from os.path import isfile
import subprocess
import collections
import brcdapi.log as brcdapi_log
import brcdapi.fos_auth as fos_auth
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.zone as brcdapi_zone
import brcdapi.util as brcdapi_util
import brcdapi.file as brcdapi_file
import brcdapi.excel_util as excel_util
import brcdapi.gen_util as gen_util
import brcddb.brcddb_project as brcddb_project
import brcddb.brcddb_common as brcddb_common
import brcddb.brcddb_fabric as brcddb_fabric
import brcddb.util.compare as brcddb_compare
import brcddb.api.interface as api_int
import brcddb.api.zone as api_zone
import brcddb.util.copy as brcddb_copy
import brcddb.util.util as brcddb_util

_DOC_STRING = False  # Should always be False. Prohibits any code execution. Only useful for building documentation
# _STAND_ALONE: True: Executes as a standalone module taking input from the command line. False: Does not automatically
# execute. This is useful when importing this module into another module that calls psuedo_main().
_STAND_ALONE = True  # See note above

_input_d = dict(
    i=dict(h='Required. Workbook with zone merge instructions. See zone_merge_sample.xlsx for details. ".xlsx" is '
             'automatically appended.'),
    cfg=dict(r=False,
             h='Optional. Typically used. The specified zone configuration is a merge of all zone configuration '
               'defined in the workbook specified with the -i parameter. If the zone configuration does not exist, it '
               'is created in all fabrics where the "Update" column in the workbook is "Yes". When this option is not '
               'used, only the aliases and zones are copied.'),
    a=dict(r=False, d=False, t='bool',
           h='Optional. No parameters. Activates the zone configuration specified with the -cfg option.'),
    t=dict(r=False, d=False, t='bool',
           h='Optional. No parameters. Perform the merge test only. No fabric changes are made.'),
    cli=dict(r=False, d=False, t='bool',
             h='Optional. No parameters. Prints the zone merge CLI commands to the log and console whether -t is '
               'specified or not.'),
)
_input_d.update(gen_util.parseargs_scan_d.copy())
_input_d.update(gen_util.parseargs_log_d.copy())
_input_d.update(gen_util.parseargs_debug_d.copy())

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

# Used in _condition_input() to translate column header names in the Workbook to input names used by capture.py
_check_d = dict(user_id='id',
                pw='pw',
                ip_addr='ip',
                security='sec',
                fid='fid',
                fab_wwn='fab_wwn',
                cfg='cfg',
                row='row',
                c_file='c_file')


def _zone_cli(proj_obj):
    """Prints the zoning commands to the log

    :param proj_obj: Project object
    :type proj_obj: brcddb.classes.project.ProjectObj
    :return: List of CLI commands
    :rtype: list
    """
    rl = ['', '# To avoid input buffer overflow, copy and paste 20 commands at a time']
    base_fab_obj = proj_obj.r_get('zone_merge_fabric')
    for fab_obj in proj_obj.r_fabric_objects():
        zd = fab_obj.r_get('zone_merge')
        if zd is not None:
            rl.extend(brcddb_util.zone_cli(base_fab_obj, fab_obj))

    return rl


def _patch_zone_db(proj_obj, eff_cfg):
    """Replaces the zoning in the fabric(s).

    :param proj_obj: Project object
    :type proj_obj: brcddb.classes.project.ProjectObj
    :param eff_cfg: Name of zone configuration to activate. None if no zone configuration to activate.
    :type eff_cfg: str, None
    :return: List of error messages. Empty list if no errors found
    :rtype: list()
    """
    rl = list()  # List of error messages to return
    base_fab_obj = proj_obj.r_fabric_obj('zone_merge_fabric')

    update_count = 0
    for fab_obj in proj_obj.r_fabric_objects():

        # Get the login credentials
        ip_addr = fab_obj.r_get('zone_merge/ip')
        user_id = fab_obj.r_get('zone_merge/id')
        pw = fab_obj.r_get('zone_merge/pw')
        sec = fab_obj.r_get('zone_merge/sec')
        fid = fab_obj.r_get('zone_merge/fid')
        update = fab_obj.r_get('zone_merge/update')
        if ip_addr is None or user_id is None or pw is None or sec is None or fid is None or not update:
            continue

        # Login
        session = api_int.login(user_id, pw, ip_addr, sec, proj_obj=proj_obj)
        if fos_auth.is_error(session):
            rl.append(fos_auth.formatted_error_msg(session))
            return rl

        # Send the changes to the switch
        brcdapi_log.log('Sending zone updates to ' + brcddb_fabric.best_fab_name(fab_obj, wwn=True, fid=True),
                        echo=True)
        try:
            obj = api_zone.replace_zoning(session, base_fab_obj, fid)
            if fos_auth.is_error(obj):
                rl.append(fos_auth.formatted_error_msg(obj))
            else:
                update_count += 1
                if isinstance(eff_cfg, str):
                    obj = api_zone.enable_zonecfg(session, fid, eff_cfg)
                    if fos_auth.is_error(obj):
                        rl.append(fos_auth.formatted_error_msg(obj))
        except BaseException as e:
            brcdapi_log.log('Unexpected error. Aborting zone transaction. Current zone state unknown.', echo=True)
            brcdapi_zone.abort(session, fid)
            rl.extend(['Software fault in api_zone.replace_zoning().', str(type(e)) + ': ' + str(e)])

        # Logout
        obj = brcdapi_rest.logout(session)
        if fos_auth.is_error(obj):
            rl.append(fos_auth.formatted_error_msg(obj))

        brcdapi_log.log(str(update_count) + ' switch(es) updated.', echo=True)

    return rl


def _get_project(sl, pl, addl_parms):
    """Reads or captures project data

    :param sl: Switches to poll via the API
    :type sl: list
    :param pl: Project files to combine
    :type pl: list
    :param addl_parms: Additional parameters (debug and logging) to be passed to capture.py.
    :type addl_parms: list
    :return rl: Error messages
    :rtype: list
    :return proj_obj: Project object. None if there was an error obtaining the project object
    :rtype proj_obj: brcddb.classes.project.ProjObj, None
    """
    global _ZONE_KPI_FILE, _kpis_for_capture

    rl = list()  # Error messages

    # Create project
    proj_obj = brcddb_project.new('zone_merge', datetime.datetime.now().strftime('%d %b %Y %H:%M:%S'))
    proj_obj.s_python_version(sys.version)
    proj_obj.s_description('Zone merge')

    # Get a unique folder name for multi_capture.py and combine.py
    folder_l = [f for f in os.listdir('.') if not isfile(f)]
    file_name, base_folder, i = '', '_zone_merge_work_folder_', 0
    work_folder = base_folder + str(i)
    while work_folder in folder_l:
        i += 1
        work_folder = base_folder + str(i)
    os.mkdir(work_folder)

    # Add the KPI file for the captures
    zone_kpi_file = work_folder + '/' + _ZONE_KPI_FILE
    f = open(zone_kpi_file, 'w')
    f.write('\n'.join(_kpis_for_capture) + '\n')
    f.close()

    # Start all the data captures for the switches to be polled so that multiple switches can be captured in parallel
    if len(sl) > 0:
        brcdapi_log.log('Collecting zoning data from switches', echo=True)
    captured_d = dict()
    pid_l, sub_d_l = list(), list()
    for sub_d in sl:
        ip_addr = sub_d['ip']
        file_name = work_folder + '/switch_' + ip_addr.split('.').pop() + '_' + str(len(pid_l))
        sub_d.update(file=file_name)
        file_name = brcdapi_file.full_file_name(file_name, '.json')
        d = captured_d.get(ip_addr)
        if d is None:
            captured_d.update({ip_addr: dict(sub_d_l=sub_d_l, file=file_name)})
            params = ['python.exe',
                      'capture.py',
                      '-ip', ip_addr,
                      '-id', sub_d['id'],
                      '-pw', sub_d['pw'],
                      '-s', 'none' if sub_d['sec'] is None else sub_d['sec'],
                      '-f', file_name,
                      '-c', zone_kpi_file] + addl_parms
            pid_l.append(dict(p=subprocess.Popen(params), file_name=file_name, ip=ip_addr))
        sub_d_l.append(sub_d)

    # Add the data read from this chassis to the project object
    for pid_d in pid_l:  # Wait for all captures to complete before continuing
        pid_d.update(s=pid_d['p'].wait())
        brcdapi_log.log('Completed capture for ' + pid_d['file_name'] + '. Ending status: ' + str(pid_d['s']),
                        echo=True)
    for pid_d in pid_l:
        try:
            obj = brcdapi_file.read_dump(pid_d['file_name'])
        except FileNotFoundError:
            obj = None
        if obj is None:
            rl.append('Capture for ' + file_name + '. failed.')
        else:
            brcddb_copy.plain_copy_to_brcddb(obj, proj_obj)
            captured_d[pid_d['ip']].update(fab_keys=obj['_fabric_objs'].keys())
    if len(rl) > 0:
        return rl, proj_obj

    # Figure out the fabric WWN for all the FIDs for the polled switches
    for d in captured_d.values():
        fab_obj_l = [proj_obj.r_fabric_obj(k) for k in d['fab_keys']]
        for fab_obj in fab_obj_l:
            if fab_obj.r_get('zone_merge') is None:  # I can't think of a reason why it wouldn't be None
                fab_obj.s_new_key('zone_merge', dict(file=d['file']))
        for sub_d in d['sub_d_l']:
            found = False
            fid = sub_d['fid']
            if isinstance(fid, int):  # If the user is just running a scan, there won't be a fid
                for fab_obj in fab_obj_l:
                    if fid in brcddb_fabric.fab_fids(fab_obj):
                        s_buf = 'none' if sub_d['sec'] is None else sub_d['sec']
                        zm_d = fab_obj.r_get('zone_merge')
                        zm_d.update(fab_wwn=fab_obj.r_obj_key(), sec=s_buf)
                        for k in ('update', 'cfg', 'fid', 'ip', 'id', 'pw', 'row', 'c_file'):
                            zm_d.update({k: sub_d[k]})
                        fab_obj.s_new_key('zone_merge', zm_d)
                        found = True
                        break
                if not found:
                    rl.append('Could not find FID ' + str(fid) + ' in ' +
                              brcdapi_util.mask_ip_addr(sub_d['ip'], keep_last=True))

    # Read all the project files
    if len(pl) > 0:
        brcdapi_log.log('Reading project files', echo=True)
    for sub_d in pl:
        file_name = brcdapi_file.full_file_name(sub_d['project_file'], '.json')
        try:
            obj = brcdapi_file.read_dump(file_name)
        except FileExistsError:
            rl.append('A folder in the path "' + file_name + '" does not exist.')
            return rl, None
        except FileNotFoundError:
            rl.append(file_name + ' does not exist.')
            return rl, None
        brcddb_copy.plain_copy_to_brcddb(obj, proj_obj)
        for fab_obj in [proj_obj.r_fabric_obj(k) for k in obj['_fabric_objs'].keys()]:
            if fab_obj.r_get('zone_merge') is None:  # It should be None. This is just future proofing.
                fab_obj.s_new_key('zone_merge', dict(file=file_name))
        fab_obj = proj_obj.r_fabric_obj(sub_d.get('fab_wwn'))
        if fab_obj is None:
            rl.append('Could not find fabric WWN ' + str(sub_d.get('fab_wwn')) + ' in ' + file_name)
        elif fab_obj.r_zonecfg_obj(sub_d.get('cfg')) is None:
            rl.append('Couldn\'t find zone configuration ' + sub_d['cfg'] + ' in ' + file_name)
        else:
            fab_obj.r_get('zone_merge').update(fab_wwn=fab_obj.r_obj_key(), update=False, cfg=sub_d['cfg'])

    return rl, proj_obj


def _merge_aliases(change_d, base_fab_obj, add_fab_obj, zl):
    """Merges the aliases from two fabrics

    :param change_d: Dictionary of alias changes as returned from brcddb.util.compare.compare()
    :type change_d: dict
    :param base_fab_obj: brcddb fabric object for the fabric we are adding the aliases from add_fab_obj to
    :type base_fab_obj: brcddb.classes.fabric.FabricObj
    :param add_fab_obj: brcddb fabric object with the aliases to be added to base_fab_obj
    :type add_fab_obj: brcddb.classes.fabric.FabricObj
    :param zl: Running list of zone changes
    :type zl: list
    :return: Error message list. If empty, no errors encountered
    :rtype: list
    """
    # Basic prep - initialize variables
    rl = list()
    if change_d is None:
        return rl
    base_fab_name = brcddb_fabric.best_fab_name(base_fab_obj, wwn=True, fid=True)
    add_fab_name = brcddb_fabric.best_fab_name(add_fab_obj, wwn=True, fid=True)
    zl.extend(['', 'Alias Changes:', '  From: ' + add_fab_name, '  To:   ' + base_fab_name])

    # Add what needs to be added or report differences
    for alias, change_obj in change_d.items():
        change_type = change_obj.get('r')
        if change_type is None or change_type == 'Changed':  # This is a simple pass/fail. No need to look further
            rl.append('Alias ' + alias + ' in ' + base_fab_name + ' does not match the same alias in ' + add_fab_name)
            zl.append('  Fault: ' + alias + ' (Membership list does not match)')
            ml = [d['c'] for d in gen_util.convert_to_list(change_obj.get('_members')) if len(d['c']) > 0]
            zl.append('    From: ' + ', '.join(ml))
            ml = [d['b'] for d in gen_util.convert_to_list(change_obj.get('_members')) if len(d['b']) > 0]
            zl.append('    To:   ' + ', '.join(ml))
        elif change_type == 'Added':
            add_obj = add_fab_obj.r_alias_obj(change_obj['c'])
            ml = add_obj.r_members()
            base_fab_obj.s_add_alias(alias, ml)
            zl.append('  Add: ' + alias + ' (' + ', '.join(ml) + ')')

    return rl


def _merge_zones(change_d, base_fab_obj, add_fab_obj, zl):
    """Merges the zones from two fabrics. See _merge_aliases() for parameter definitions"""
    # Basic prep
    rl = list()
    if change_d is None:
        return rl
    base_fab_name = brcddb_fabric.best_fab_name(base_fab_obj, wwn=True, fid=True)
    add_fab_name = brcddb_fabric.best_fab_name(add_fab_obj, wwn=True, fid=True)
    zl.extend(['', 'Zone Changes:', '  From: ' + add_fab_name, '  To:   ' + base_fab_name])

    # Add what needs to be added or report differences
    for zone, change_obj in change_d.items():
        change_type = change_obj.get('r')
        if change_type is None or change_type == 'Changed':  # This is a simple pass/fail. No need to look further
            rl.append('Zone ' + zone + ' in ' + base_fab_name + ' does not match the same zone in ' + add_fab_name)
            zl.append('  Fault: ' + zone + ' (Membership list does not match)')
            ml = [d['c'] for d in gen_util.convert_to_list(change_obj.get('_members')) if len(d['c']) > 0]
            zl.append('    From: ' + ', '.join(ml))
            ml = [d['b'] for d in gen_util.convert_to_list(change_obj.get('_members')) if len(d['b']) > 0]
            zl.append('    To:   ' + ', '.join(ml))
        elif change_type == 'Added':
            add_obj = add_fab_obj.r_zone_obj(zone)
            ml, pl = add_obj.r_members(), add_obj.r_pmembers()
            base_fab_obj.s_add_zone(zone, add_obj.r_type(), ml, pl)
            zl.append('  Add: ' + zone)
            zl.extend(['    ' + b for b in ml])
            zl.extend(['    (Peer Principal) ' + b for b in pl])

    return rl


def _merge_zone_cfgs(change_d, base_fab_obj, add_fab_obj, zl):
    """Merges the zone configurations from two fabrics. See _merge_aliases() for parameter definitions"""
    # Basic prep
    rl = list()
    if change_d is None:
        return rl
    base_fab_name = brcddb_fabric.best_fab_name(base_fab_obj, wwn=True, fid=True)
    add_fab_name = brcddb_fabric.best_fab_name(add_fab_obj, wwn=True, fid=True)
    zl.extend(['', 'Zone Configuration Changes:', '  From: ' + add_fab_name, '  To:   ' + base_fab_name])

    # Add what needs to be added or report differences
    for zonecfg, change_obj in change_d.items():
        if zonecfg != '_effective_zone_cfg':
            change_type = change_obj.get('r')
            if isinstance(change_type, str) and change_type == 'Added':
                add_obj = add_fab_obj.r_zonecfg_obj(zonecfg)
                ml = add_obj.r_members()
                base_fab_obj.s_add_zonecfg(zonecfg, ml)
                zl.append('  Add: ' + zonecfg)
                zl.extend(['    ' + b for b in ml])

    return rl


def _create_zone_cfg(change_d, base_fab_obj, add_fab_obj, zl):
    """Merges the zone configurations from two fabrics. See _merge_aliases() for parameter definitions"""
    # Basic prep
    rl = list()
    if change_d is None:
        return rl
    base_fab_name = brcddb_fabric.best_fab_name(base_fab_obj, wwn=True, fid=True)
    add_fab_name = brcddb_fabric.best_fab_name(add_fab_obj, wwn=True, fid=True)
    zl.extend(['', 'Zone Configuration Changes:', '  From: ' + add_fab_name, '  To:   ' + base_fab_name])

    # Add what needs to be added or report differences
    for zonecfg, change_obj in change_d.items():
        if zonecfg != '_effective_zone_cfg':
            change_type = change_obj.get('r')
            if isinstance(change_type, str) and change_type == 'Added':
                add_obj = add_fab_obj.r_zonecfg_obj(zonecfg)
                ml = add_obj.r_members()
                base_fab_obj.s_add_zonecfg(zonecfg, ml)
                zl.append('  Add: ' + zonecfg)
                zl.extend(['    ' + b for b in ml])

    return rl


_merge_case = collections.OrderedDict()  # Used essentially as case statement actions in _merge_zone_db()
_merge_case['_alias_objs'] = _merge_aliases
_merge_case['_zone_objs'] = _merge_zones
_merge_case['_zonecfg_objs'] = _merge_zone_cfgs


def _merge_zone_db(proj_obj, new_zone_cfg, a_flag):
    """Merges the zones for the fabrics specified with -i

    :param proj_obj: Project object
    :type proj_obj: brcddb.classes.project.ProjectObj
    :param new_zone_cfg: Name of zone configuration to add
    :type new_zone_cfg: str, None
    :param a_flag: If True, make new_zone_cfg the effective zone configuration
    :type a_flag: bool
    :return rl: Error message. If empty, no errors encountered
    :rtype rl: list
    :return zl: Zone merge report in lists of text messages to print
    :rtype zl: list
    """
    global _merge_case

    rl, zl, fab_l, new_zonecfg_obj = list(), list(), list(), None

    # Get a list of fabrics to work on
    fab_l = [obj for obj in proj_obj.r_fabric_objects() if obj.r_get('zone_merge').get('fab_wwn') is not None]
    if len(fab_l) < 2:
        rl.append('Found ' + str(len(fab_l)) + ' fabrics to merge. Must have at least two fabrics to merge.')

    # Create a fabric to contain the merged zone database.
    base_fab_obj = proj_obj.s_add_fabric('zone_merge_fabric')
    if isinstance(new_zone_cfg, str):
        new_zonecfg_obj = base_fab_obj.s_add_zonecfg(new_zone_cfg)

    for fab_obj in fab_l:
        zd = fab_obj.r_get('zone_merge')

        # The compare utility checks lists 1 for 1 (each item at each index must match) so sort all membership lists
        for obj_l in [fab_obj.r_alias_objects(), fab_obj.r_zone_objects(), fab_obj.r_zonecfg_objects()]:
            for obj in obj_l:
                obj.s_sort_members()

        # Validate what to merge
        change_count, change_d = brcddb_compare.compare(base_fab_obj, fab_obj, brcddb_control_tbl=_control_tables)
        for local_key, action in _merge_case.items():
            rl.extend(action(change_d.get(local_key), base_fab_obj, fab_obj, zl))

        # Add the zones to the merged zone configuration
        if new_zonecfg_obj is not None and isinstance(zd['cfg'], str):
            zonecfg_obj = fab_obj.r_zonecfg_obj(zd['cfg'])
            if zonecfg_obj is None:
                rl.append('Zone configuration ' + zd['cfg'] + ' does not exist. File: ' + zd['c_file'] + ' Row: ' +
                          zd['row'])
            else:
                new_zonecfg_obj.s_add_member(zonecfg_obj.r_members())

    # If the new zone configuration is to be enabled, set it as the effective zone configuration
    if a_flag:
        base_fab_obj.s_add_eff_zonecfg(new_zonecfg_obj.r_members())

    return rl, zl


def _condition_input(in_d):
    global _check_d

    rd = dict(
        update=True if in_d.get('update') is not None and in_d['update'].lower() == 'yes' else False,
        sec='none' if in_d.get('security') is None else 'none' if in_d['security'] == '' else in_d['security']
    )
    for k, v in _check_d.items():
        key_val = in_d.get(k)
        rd.update({v: None if key_val is not None and key_val == '' else key_val})
    return rd


def pseudo_main(sl, pl, cfg_name, a_flag, t_flag, scan_flag, cli_flag, addl_parms):
    """Basically the main(). Did it this way so that it can easily be used as a standalone module or called externally.

    :param sl: Switches to poll as read from the input Workbook
    :type sl: list
    :param pl: Project files to combine
    :type pl: list
    :param cfg_name: Name of zone configuration file to create
    :type cfg_name: str, None
    :param a_flag: Activation flag. If True, activate the zone configuration specified by cfg_name
    :type a_flag: bool
    :param t_flag: Test flag. If True, test only. Do not make any changes
    :type t_flag: bool
    :param scan_flag: Scan flag. If True, scan files and switches for fabric information
    :type scan_flag: bool
    :param cli_flag: If True, generate CLI
    :type cli_flag: bool
    :param addl_parms: Additional parameters (logging and debug flags) to pass to multi_capture.py
    :type addl_parms: list
    :return: Exit code. See exit codes in brcddb.brcddb_common
    :rtype: int
    """
    global __version__

    # Capture the zoning data
    ec = brcddb_common.EXIT_STATUS_OK
    ml, proj_obj = _get_project(sl, pl, addl_parms)

    if proj_obj is None or len(ml) > 0:
        ml.insert(0, 'Error reading project file.')
        brcdapi_log.log(ml, echo=True)
        return brcddb_common.EXIT_STATUS_INPUT_ERROR
    if scan_flag and proj_obj is not None:
        brcdapi_log.log(brcddb_project.scan(proj_obj, fab_only=True), echo=True)
        return brcddb_common.EXIT_STATUS_OK
    if len(ml) > 0:
        ml.insert(0, 'Merge test failed:')
        ml.insert(0, '')
        brcdapi_log.log(ml, echo=True)
        return brcddb_common.EXIT_STATUS_INPUT_ERROR

    # Merge the zones logically
    ml, rl = _merge_zone_db(proj_obj, cfg_name, a_flag)
    brcdapi_log.log(['Detailed Zone Merge Report'] + rl)
    if len(ml) > 0:
        ml.insert(0, 'Merge test failed:')
        ml.insert(0, '')
        brcdapi_log.log(ml, echo=True)
        ec = brcddb_common.EXIT_STATUS_ERROR

    else:
        brcdapi_log.log('Zone merge test succeeded', echo=True)
        if not t_flag:  # Make the changes
            ml = _patch_zone_db(proj_obj, cfg_name if a_flag else None)
            brcdapi_log.log(['Zone merge complete: ' + str(len(ml)) + ' errors.'] + ml, echo=True)
            if len(ml) > 0:
                ec = brcddb_common.EXIT_STATUS_ERROR
        if len(ml) == 0 and cli_flag:
            brcdapi_log.log(_zone_cli(proj_obj), echo=True)

    brcdapi_log.log(['', 'Check the log for "Detailed Zone Merge Report" for details'], echo=True)

    return ec


def _get_input():
    """Retrieves the command line input, reads the input Workbook, and minimally validates the input

    :return: Exit code. See exit codes in brcddb.brcddb_common
    :rtype: int
    """
    global __version__, _input_d

    # Initialize the return variables
    ec = brcddb_common.EXIT_STATUS_OK
    sl, pl = list(), list()

    # Get command line input
    buf = 'The zone_merge utility merges the zone databases from two or more fabrics by reading the zone database from'\
          ' a project file or a live switch. All aliases, zones, and zone configurations are merged. If an alias or '\
          'zone with the same name is defined in more than one of the fabrics but have different members, an error is '\
          'reported and the zone transactions aborted. If a zone configuration with the same name is defined in '\
          'multiple fabrics, the membership lists are merged. REMINDER: If the effective zone configuration is '\
          'modified but not activated using the -cfg and -a options, the defined zone configuration will not match '\
          'the effective zone configuration.'
    args_d = gen_util.get_input(buf, _input_d)

    # Set up logging
    brcdapi_rest.verbose_debug(args_d['d'])
    brcdapi_log.open_log(
        folder=args_d['log'],
        suppress=args_d['sup'],
        no_log=args_d['nl'],
        version_d=brcdapi_util.get_import_modules()
    )

    # Command line feedback
    c_file = brcdapi_file.full_file_name(args_d['i'], '.xlsx')
    ml = [
        os.path.basename(__file__) + ', ' + __version__,
        'Input file, -i:        ' + str(c_file),
        'Common zonecfg, -cfg:  ' + str(args_d['cfg']),
        'Activate zone cfg:     ' + str(args_d['a']),
        'Scan flag, -scan:      ' + str(args_d['scan']),
        'CLI flag, -cli:        ' + str(args_d['cli']),
        'Test:                  ' + str(args_d['t']),
        'Log, -log:             ' + str(args_d['log']),
        'No log, -nl:           ' + str(args_d['nl']),
        'Debug, -d:             ' + str(args_d['d']),
        'Suppress, -sup:         ' + str(args_d['sup']),
        '',
    ]
    brcdapi_log.log(ml, echo=True)

    # Parse the input file
    ml, switch_l = list(), list()
    try:
        switch_l = excel_util.parse_parameters(sheet_name='parameters', hdr_row=0, wb_name=c_file)['content']
    except FileExistsError:
        ml.append('A folder in the path "' + c_file + '" does not exist.')
    except FileNotFoundError:
        ml.append(c_file + ' does not exist.')
    if args_d['a'] and not isinstance(args_d['cfg'], str):
        ml.append('Configuration activate flag, -a, specified without a valid zone configuration name, -cfg')
    if len(ml) == 0:
        for i in range(0, len(switch_l)):
            sub_d = switch_l[i]
            sub_d.update(row=str(i+2), c_file=c_file)  # Used for error reporting
            buf = sub_d.get('project_file')
            if buf is None:
                if sub_d['ip_addr'] is not None:  # Sometimes empty rows are returned from reading the worksheet
                    sl.append(_condition_input(sub_d))
            else:
                pl.append(sub_d)
                if not args_d['scan'] and not gen_util.is_wwn(sub_d.get('fab_wwn'), full_check=True):
                    ml.append('fab_wwn is not a valid WWN in row ' + str(i+2))
    if len(ml) > 0:
        brcdapi_log.log(ml, echo=True)
        ec = brcddb_common.EXIT_STATUS_INPUT_ERROR

    addl_parms_l = ['-' + k for k in ('nl', 'd', 'sup') if args_d[k]]
    addl_parms_l.extend(['-log', args_d['log']])

    return ec if ec != brcddb_common.EXIT_STATUS_OK else \
        pseudo_main(sl, pl, args_d['cfg'], args_d['a'], args_d['t'], args_d['scan'], args_d['cli'], addl_parms_l)


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
