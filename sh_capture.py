#!/usr/bin/python
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

The equivalent of capture.py but instead of reading data directly from a switch, the data is read from a SAN Health
report.

The primary purpose, and therefore best tested, of this script is for:

    * Determining HBA types
    * Determining HBA and storage trends
    * Determining SFP requirements for upgrades
    * Merging and migrating zones
    * Evaluating new SFP MAPS rules

**Required Libraries**

    Available With PIP install but no included with standard Python:

    openpyxl

    From https://github.com/jconsoli

    brcdapi
    brcddb

**Why Not Just Read CSV File?**

At the time this was written, there was a bug in the output of that file. I don't recall what it was but since I had a
utility to read workbooks, it was relatively easy to just read the report workbook. That bug was fixed, but I already
had this written and I figured it would be good to be able to read older SAN Health reports, so I never went back and
changed anything.

**Important Notes**

    * The SAN Health report is in Excel 1997-2003 format. It must be converted to the latest version of Excel.
    * Only those aspects of the SAN Health report needed for zone analysis and collecting port statistics was
      implemented
    * The SAN Health report is read into memory. Due to how the openpyxl utility stores Excel Workbooks, the memory
      requirement is considerably greater than the Workbook size. For example, a 74MB workbook requires about 5G of
      memory. Make sure you have adequate free memory.
    * HBAs and storage interfaces do not always provide detailed name server information. This has more to do with the
      SFP. 
    * Remote optical speed capabilities are only determined for Emulex and Q-Logic HBAs and only.
    * Peer zones are not interpreted
    * Large SAN Health reports can take several hours

**General Notes**

Older versions of SAN Health counted logins. This script only counts ports.

The Q-Logic and Emulex part numbers are read from the name server information and a lookup table is used to determine
the remote speed capability. This is useful when upgrading from older SAN switches because SFP requirements are
dependent on the attached device capability. the login speed may have been limited by the switch in which case a higher
speed (newer) SFP.

The easiest way to determine which HBAs could have logged in at a higher data rate is to run report.py against the
output of this script. The best practice workbook, -bp option in report.py, should have LOGIN_SPEED_NOT_MAX_W and
SWITCH_LIMITED_SPEED set True. For a summary of just remote HBAs that did not log in at the fastest speed, set all other
parameters to FALSE.

Although the current version of SAN Health reads peer zones, it was not included in SAN Health reports at the time this
was written. Use ss_capture.py for analyzing peer zones.

Use the output of this script with port_count.py to determine port counts.

**NX-OS (Cisco) Notes**

VSANs are converted to FIDs. You may need to provide a map of VSANs to FIDs if the VSAN number is not a valid FID. Cisco
does not have a direct equivalent to peer zones and have a few other differences. Review “Cisco_Zone_Migration”, posted
on Centcom, before doing any NX-OS to FOS zone migrations.

The scripts for migrating NX-OS to FOS zones were written for a specific customer. That customer did not use inter-VSAN
routing (IVR) or smart zones so no time was spent developing code to handle IVR or smart zones.

**Tech Notes**

    * sup-fcx ports were converted to 98/x
    * Trunks were converted to 99/x

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 1.0       | 13 Mar 2021   | Initial launch                                                                        |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 1.0.1     | 09 Dec 2022   | Fixed case in _port_details() when no ports are on the sheet. Fixed missed effective  |
|           |               | zone configuration. Fixed port number determination in Cisco switches. Added          |
|           |               | determination of remote SFP speed capabilities based on name server info.             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 1.0.2     | 03 Jun 2023   | Added 'san_health' to the port object                                                 |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 1.0.3     | 25 Aug 2025   | Use brcddb.util.util.get_import_modules to dynamically determined imported libraries. |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2023, 2024, 2025 Consoli Solutions, LLC'
__date__ = '25 Aug 2025'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '1.0.3'

import sys
import os
import datetime
import argparse
import collections
import copy
import re
import brcdapi.log as brcdapi_log
import brcdapi.gen_util as gen_util
import brcdapi.excel_util as excel_util
import brcdapi.file as brcdapi_file
import brcdapi.util as brcdapi_util
import brcddb.brcddb_common as brcddb_common
import brcddb.brcddb_project as brcddb_project
import brcddb.brcddb_port as brcddb_port
import brcddb.util.copy as brcddb_copy
import brcddb.report.utils as report_utils
import brcddb.util.util as brcddb_util
import brcddb.util.search as brcddb_search
import brcddb.classes.util as class_util
import brcddb.util.obj_convert as brcddb_convert
import brcddb.brcddb_fabric as brcddb_fabric
import brcddb.util.parse_cli as parse_cli

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation
_DEBUG = False  # When True, use _DEBUG_* below instead of passed arguments.
_DEBUG_i = 'test/Greg_Bricker_230613_0751_Verizon_IT_Security'  # Name of SAN Health report.
_DEBUG_o = 'test/test_out'  # Name of output file
_DEBUG_ucs = None
_DEBUG_dm = 3
_DEBUG_sup = False
_DEBUG_log = '_logs'
_DEBUG_nl = False

# Keys that should be string but may have been read as an integer
_int_to_str_keys = ('node-symbolic-name',)
_full_flag = False
_port_num = re.compile('[^0-9/]')
_non_int = re.compile(r'[^\d]+')
_act_objects = dict()
for _key in class_util.simple_class_type:
    _act_objects.update({_key: None})
# _port_seen: Key is switch WWN. Value is a dict whose key is the port number and the value is True if the port has been
# processed once already. Otherwise, false. This is to prevent port information from being updated after the base login
# has been processed.
_port_seen = dict()
_zs_match = dict()  # Match a zone sheet to fabric object Key: Zone sheet name, value: Fabric object
_target_dev_types = ('disk', 'tape')
_initiator_dev_types = ('fchost', 'gateway')
_cisco_isl_count = 0
# The remote speed is determined by the HBA type. Only initiators use this table. All comparisons are upper case.
_remote_speed_d = {
    2: ('2GB', 'BL25', 'QLA2340'),
    4: ('4GB', 'LPE1105', 'LPE1101', 'LPE1100', 'A8003A', 'QLE2460'),
    8: ('8GB', 'AJ763B', 'AH403A', 'LPE1200', 'AJ763B', 'AH403A', 'AJ762B', 'AH402A', 'LPE1205', 'QLE2562', 'QLE2692',
        'QLE2560'),
    16: ('16GB', 'SN1200E', '7101684', 'SN1100Q', 'QLE2694L', 'QLE2690', 'LPE1600'),
    32: ('32GB', 'SN1600Q', 'SN1600E', 'P9M75A', 'QLE2742'),
    64: ('64GB',),
}
_remote_speed_key_l = [int(_k) for _k in _remote_speed_d.keys()]
_remote_speed_key_l.sort(reverse=True)
_speed_list_d = {
    2: [1, 2],
    4: [1, 2, 4],
    8: [2, 4, 8],
    16: [4, 8, 16],
    32: [8, 16, 32],
    64: [16, 32, 64],
}

"""**Table Definitions & Methods**

The methods that follow are used as values for the 'a' or 'conv' keys in the tables defined after the method
definitions. Some or all of these keys are used.
+-------+-----------------------------------------------------------------------------------------------------------+
| key   | Description                                                                                               |
+=======+===========================================================================================================+
| a     | Same as conv but methods only.                                                                            |
+-------+-----------------------------------------------------------------------------------------------------------+
| c     | Cell content header                                                                                       |
+-------+-----------------------------------------------------------------------------------------------------------+
| l     | A list of dictionaries containing any of 'a', 'c', 'kpi', 'conv', or 'd'. It is used to perform multiple  |
|       | actions on an item.                                                                                       |
+-------+-----------------------------------------------------------------------------------------------------------+
| kpi   | The KPI (Unique portion of the FOS API URL)                                                               |
+-------+-----------------------------------------------------------------------------------------------------------+
| conv  | Conversion table or method to call to convert the value to the equivalent KPI value. If None, the value   |
|       | the cell is used as it.                                                                                   |
+-------+-----------------------------------------------------------------------------------------------------------+
| d     | Default value if value not found in conversion table, conv. If None or not present, the default is the    |
|       | cell value.                                                                                               |
+-------+-----------------------------------------------------------------------------------------------------------+
"""
# Used in _port_frame_error_act() to determine the columns for all the frame error counts
_frame_error_col_hdr = {  # Search for "Table Definitions & Methods"
    # 'Port': 'fibrechannel/index'
    # 'Name / Alias / Zone':  There is no guarantee whether this is name, alias, or zone so do nothing
    # 'Port World Wide Name':  The attached logins will get picked up in the PORT DETAILS section
    'Transmit': brcdapi_util.stats_out_frames,
    'Receive': brcdapi_util.stats_in_frames,
    'Enc In': brcdapi_util.stats_enc_disp,
    'CRC': brcdapi_util.stats_crc,
    'Short': brcdapi_util.stats_tunc,
    'Long': brcdapi_util.stats_long,
    'EndFrame': brcdapi_util.stats_bad_eof,
    'Enc Out': brcdapi_util.stats_enc,
    'Class3D': brcdapi_util.stats_c3,
    'Link Fail': brcdapi_util.stats_link_fail,
    'losSync': brcdapi_util.stats_loss_sync,
    'losSig': brcdapi_util.stats_loss_sig,
    'Reject': brcdapi_util.stats_p_rjt,
    'Busy': brcdapi_util.stats_p_busy,
}
_proj_obj = brcddb_project.new("Captured_data", datetime.datetime.now().strftime('%d %b %Y %H:%M:%S'))
_proj_obj.s_python_version(sys.version)
_act_objects.update(ProjectObj=_proj_obj)
_working_fab_obj = None
_working_switch_obj = None
_working_chassis_obj = None
_working_port_obj = None
_working_login_obj = None
_first_port = False
_reverse_port_status = dict()
for _key, _val in brcddb_common.port_conversion_tbl[brcdapi_util.fc_op_status].items():
    _reverse_port_status.update({_val: _key})
_reverse_port_type = dict()
for _key, _val in brcddb_common.port_conversion_tbl[brcdapi_util.fc_port_type].items():
    _reverse_port_type.update({_val: _key})
_reverse_port_type.update({'TE-Port': 7})  # Cisco E-Port


class Found(Exception):
    pass


def _remote_port_speed():
    """Adds the remote port speed to all ports if HBA is known"""
    global _proj_obj, _remote_speed_d, _remote_speed_key_l

    brcdapi_log.log('Determining remote port speed capabilities', echo=True)
    for port_obj in _proj_obj.r_port_objects():

        if port_obj.c_login_type() != 'F-Port':
            continue
        try:
            for login_obj in port_obj.r_login_objects():
                fc4 = login_obj.r_get(brcdapi_util.bns_fc4_features)
                if isinstance(fc4, str) and 'initiator' in fc4.lower():
                    buf = login_obj.r_get(brcdapi_util.bns_node_symbol, '').upper()
                    for k in _remote_speed_key_l:
                        for hba in _remote_speed_d[k]:
                            if hba in buf:
                                class_util.get_or_add(port_obj, brcdapi_util.sfp_remote_speed, _speed_list_d[k])
                                raise Found
        except Found:
            continue

    return


def _get_port_num(val):
    """Get the port number from [ PORT... on the SWITCH SUMMARY DETAILS sheet

    :param val: Cell with [ PORT in it
    :type val: str
    :return port_num: Port number in s/p notation
    :rtype port_num: str
    :return port_index: Port index
    :rtype port_index: int
    """
    global _cisco_isl_count

    # Figure out what the port number is in s/p notation. val is in the form "[ PORT 228 Device 8 Slot8/Port36 ]..." for
    # bladed switches and "[ PORT 1 ]..." for fixed port switches. Note that for fixed port switches, the port number
    # and port index is the same and therefore not broken out as a seperate parameter.
    port, port_index, tl = None, None, list()

    # This is a bit of a kludge
    buf_l = val.split(' ')
    for buf in buf_l:
        if buf == ']' or buf == 'Device':
            break
        if buf != '[' and buf != 'PORT' and buf != 'prt-chl':
            tl.append(buf)
            if 'Slot' in val:
                for buf in buf_l:
                    if 'Slot' in buf:
                        tl.append(buf)
                        break

    if 'Cisco Switch ISL' in val:
        if len(tl) > 0:
            tl = tl[0:1]
            tl.append('99/' + tl[0])
        else:
            tl = list()
    elif 'prt-chl' in val:  # It's a Cisco port channel
        if len(tl) > 1:
            tl[1] = tl[0] + '/' + tl[1]

    if len(tl) > 0:
        port_index = int(gen_util.non_decimal.sub('', tl[0]))
        if len(tl) > 1:
            port_l = tl[1].split('/')
            if len(port_l) == 1:
                port = '0/' + gen_util.non_decimal.sub('', tl[0])
            else:
                port = gen_util.non_decimal.sub('', port_l[0]) + '/' + gen_util.non_decimal.sub('', port_l[1])
        else:
            port = '0/' + str(port_index)

    if port is None or port_index is None:
        brcdapi_log.exception('Cannot decipher port or port index from ' + val, echo=True)

    return port, port_index


def _clean_val(key, val):
    """Replaces any values that are type None with '' and sets integers to strings for keys that require a string

    :param key: Key associated with the value, val
    :type key: str
    :param val: The value to clean up
    :type val: int, float, str, list, tuple, dict, None
    :return: val with all None type values replaced with ''
    :rtype: int, float, str, list, tuple, dict, None
    """
    global _int_to_str_keys

    # Convert all values of type None to ''
    if val is None:
        return ''
    if isinstance(val, list):
        return [_clean_val(key, obj) for obj in val]
    if isinstance(val, dict):
        rd = dict()
        for k, obj in val.items():
            rd.update({k: _clean_val(key, obj)})
        return rd

    # Convert integers to strings
    if isinstance(val, int):
        for k0 in _int_to_str_keys:
            if k0 in key:
                return str(val)

    return val


def _add_keys(in_obj, in_keys, val, concatenate=False):
    """Processes key adds for the action methods in _sheet_action_d

    :param in_obj: brcddb class object
    :type in_obj: brcddb.classes.chassis.ChassisObj,  brcddb.classes.fabric.FabricObj, brcddb.classes.switch.SwitchObj,\
                brcddb.classes.login.LoginObj,  brcddb.classes.port.PortObj,  brcddb.classes.zone.ZoneCfgObj, \
                ZoneCfgObj.zone.ZoneObj, ZoneObj.zone.AliasObj
    :param in_keys: Key or list of keys to be added to the objects
    :type in_keys: dict, list, tuple
    :param val: The value associated with the key
    :type val: int, float, str, list, tuple, dict, None
    :param concatenate: If True, concatenate to the existing value - only works for str types
    :type concatenate: bool
    """
    for key in gen_util.convert_to_list(in_keys):
        for k, key_list in key.items():
            obj_l = brcddb_convert.obj_extract(in_obj, k)
            for obj in obj_l:
                for k1 in gen_util.convert_to_list(key_list):
                    if val is not None:
                        new_val = _clean_val(k1, val)
                        if concatenate and isinstance(new_val, str) and \
                                class_util.get_simple_class_type(obj) is not None:
                            buf = obj.r_get(k1)
                            if buf is not None:
                                new_val = buf + ', ' + new_val
                        brcddb_util.add_to_obj(obj, k1, new_val)


# In _stat_counter_hdrs, the key is for a local reference in _process_san_ports(). The value is a dict as follows:
# c     Enough of the column header to find a match in the SH report.
# t     Conversion type: 0 or None - No conversion, 1 - int, 2 - standard port notation (s/p)
# o     Standard object type for the brcddb object that the value gets added to
# k     The key in the object that the value gets added to.
_STATS_TYPE_INT = 1
_STATS_TYPE_SP = 2
_stat_counter_hdrs = dict(
    did=dict(c='Dom', t=_STATS_TYPE_INT),
    area=dict(c='Area'),
    sp=dict(c='Slot/Port', t=_STATS_TYPE_SP),
    pid=dict(c='Port ID'),
    desc=dict(c='Description'),
    naz=dict(c='Name / Alias/ Zone'),
    model=dict(c='Model'),
    fw=dict(c='Firmware'),
    driver=dict(c='Driver'),
    pwwn=dict(c='Port World Wide Name'),
    # addl_info=dict(c='Additional Information',
    #                k=dict(LoginObj=brcdapi_util.bns_node_symbol)),
    tx_frames=dict(c='Frames Tx', t=_STATS_TYPE_INT),
    rx_frames=dict(c='Frames Rx', t=_STATS_TYPE_INT),
    enc_in=dict(c='EncErr In Frms', t=_STATS_TYPE_INT),
    crc=dict(c='Frms CRC Errs', t=_STATS_TYPE_INT),
    enc_out=dict(c='EncErr Out Frms', t=_STATS_TYPE_INT),
    c3_rx_disc=dict(c='C3 Rx Discd', t=_STATS_TYPE_INT),
    c3_tx_disc=dict(c='C3 Tx Discd', t=_STATS_TYPE_INT),
    crc_eof=dict(c='CRC Err EOF Good', t=_STATS_TYPE_INT),
    zero_bc=dict(c='Tim Txcrd Z', t=_STATS_TYPE_INT, k=dict(PortObj='fibrechannel-statistics/bb-credit-zero')),
    vc0=dict(c='VC0', t=_STATS_TYPE_INT),
    vc1=dict(c='VC1', t=_STATS_TYPE_INT),
    vc2=dict(c='VC2', t=_STATS_TYPE_INT),
    vc3=dict(c='VC3', t=_STATS_TYPE_INT),
    vc4=dict(c='VC4', t=_STATS_TYPE_INT),
    vc5=dict(c='VC5', t=_STATS_TYPE_INT),
    vc6=dict(c='VC6', t=_STATS_TYPE_INT),
    vc7=dict(c='VC7', t=_STATS_TYPE_INT),
    vc8=dict(c='VC8', t=_STATS_TYPE_INT),
    vc9=dict(c='VC9', t=_STATS_TYPE_INT),
    vc10=dict(c='VC10', t=_STATS_TYPE_INT),
    vc11=dict(c='VC11', t=_STATS_TYPE_INT),
    vc12=dict(c='VC12', t=_STATS_TYPE_INT),
    vc13=dict(c='VC13', t=_STATS_TYPE_INT),
    vc14=dict(c='VC14', t=_STATS_TYPE_INT),
    vc15=dict(c='VC15', t=_STATS_TYPE_INT),
)


def _process_san_ports(sheet):
    """Parses the Summary sheet and adds details to the project object

    :param sheet: Worksheet contents as extracted from excel_util.read_workbook()
    :type sheet: dict
    :return: Status. See EXIT status codes in brcddb.common
    :rtype: int
    """
    global _proj_obj, _non_int, _full_flag

    error_l = list()  # Running list of error messages

    # Find each header for each fabric
    for fabric_d in brcddb_search.match_test(sheet['sl'], dict(k='val', v='Name / Alias/ Zone', t='exact', i=False)):

        # Get the fabric object
        row = int(gen_util.non_decimal.sub('', fabric_d['cell']))
        try:
            fab_obj = brcddb_project.fab_obj_for_user_name(_proj_obj, sheet['al'][row-2][0])[0]
        except IndexError:
            continue  # brcddb_project.fab_obj_for_user_name() return an empty list for access gateways

        # Find all the columns
        header_row = sheet['al'][row-1]
        col_d = dict()
        for k, v in _stat_counter_hdrs.items():
            for col in range(0, len(header_row)):
                if isinstance(header_row[col], str) and v['c'] in header_row[col]:
                    col_d.update({k: col})
                    break

        # Find all the values
        last_pid, port_d_l = None, list()
        while row < len(sheet['al']):
            full_row = sheet['al'][row]

            if _full_flag:
                # Check for WWNs that didn't show up on the detailed switch sheets. I think this only happens when the
                # SAN Health report is from a Cisco fabric and the WWN is part of a UCS port channel group but the WWN
                # didn't register with the name server. I'm assuming that means the associated blade is offline.
                pid = '' if full_row[col_d['pid']] is None else full_row[col_d['pid']]
                if len(pid) == 6:
                    last_pid = pid
                elif last_pid is not None:
                    port_obj_l = brcddb_port.port_objects_for_addr(_proj_obj, '0x' + last_pid)
                    if len(port_obj_l) == 1:  # Assume it's on the same port as the last known PID
                        port_obj_l[0].s_add_login(full_row[col_d['pwwn']])
                    else:
                        error_l.append('Could not resolve address ' + pid + ' on "SAN Ports" sheet.')

            if not isinstance(full_row[col_d['sp']], str):
                break
            port_d = dict()
            for k, v in _stat_counter_hdrs.items():

                if k not in col_d:
                    continue

                val = full_row[col_d[k]]
                if val is not None:
                    v_type = 0 if v.get('t') is None else v.get('t')
                    if v_type == _STATS_TYPE_INT:
                        if isinstance(val, (int, float)):
                            port_d.update({k: val})
                        elif isinstance(val, str) and val.isnumeric():
                            port_d.update({k: int(val)})
                        else:
                            port_d.update({k: 0})
                    elif v_type == _STATS_TYPE_SP:
                        tl = [_non_int.sub('', buf) for buf in val.replace('sup-', '98/').split('/')]
                        if len(tl) == 1:
                            tl.insert(0, '0')
                        port_d.update({k: '/'.join(tl)})
                    else:
                        port_d.update({k: val})
            port_d_l.append(port_d)
            row += 1

        # Add all the ports and data
        for port_d in port_d_l:
            switch_obj = brcddb_fabric.switch_for_did(fab_obj, port_d['did'])
            if switch_obj is None:
                brcdapi_log.log('Could not find switch for DID: ' + str(port_d['did']) + ', port: ' + port_d['sp'],
                                True)
                continue
            port_obj = switch_obj.s_add_port(port_d['sp'])
            for k in _stat_counter_hdrs.keys():
                if port_d.get(k) is not None:
                    _add_keys(port_obj, _stat_counter_hdrs[k].get('k'), port_d[k])
    return brcddb_common.EXIT_STATUS_OK


def _process_fabric(sheet):
    """Get a fabric object for the next zone page

    :param sheet: Worksheet contents as extracted from excel_util.read_workbook()
    :type sheet: dict
    :return: Status. See EXIT status codes in brcddb.common
    :rtype: int
    """
    global _proj_obj, _working_fab_obj, _zs_match

    ml = brcddb_search.match_test(sheet['sl'], dict(k='val', v='World Wide Name', t='exact', i=False))
    if len(ml) == 0:
        brcdapi_log.exception('Could not find a switch WWN on ' + str(sheet.get('sheet')), echo=True)
        return brcddb_common.EXIT_STATUS_ERROR
    col = excel_util.col_to_num(ml[0]['cell']) - 1
    row = int(gen_util.non_decimal.sub('', ml[0]['cell']))
    _zs_match.update({'Z' + sheet['sheet'][1:]: _proj_obj.r_switch_obj(sheet['al'][row][col]).r_fabric_obj()})


# The following methods are called from _sheet_essential_values to update the project object.

_brcddb_template = dict(proj_obj=None, switch_obj=None, fabric_obj=None, zone_obj=None, port_obj=None)


def _create_switch(keys, val):
    """Create a logical switch object"""
    global _working_fab_obj, _working_switch_obj, _port_seen
    _working_switch_obj = _working_fab_obj.s_add_switch(val)
    _port_seen.update({val: dict()})
    _add_keys(_working_switch_obj, keys, val)


def _fabric_for_switch(keys, val):
    """Create a fabric object"""
    global _proj_obj, _working_fab_obj, _working_switch_obj
    _working_fab_obj = _proj_obj.s_add_fabric(val)
    _proj_obj.r_switch_obj(val)
    _add_keys(_working_fab_obj, keys, val)


def _switch_status(keys, val):
    """Add the switch status to the _working_switch_obj"""
    global _working_switch_obj
    _add_keys(_working_switch_obj, keys, 2 if val.lower() == 'online' else 3)


def _create_chassis(keys, val):
    """Create a chassis object from the value associated with "Chassis Serial Num" """
    global _working_fab_obj, _working_chassis_obj, _working_switch_obj
    _working_chassis_obj = _proj_obj.s_add_chassis(val)
    _working_chassis_obj.s_add_switch(_working_switch_obj.r_obj_key())
    _add_keys(_working_chassis_obj, keys, val)
    _add_keys(_working_chassis_obj, dict(ChassisObj=brcdapi_util.bc_mfg),
              'Brocade Communications Systems LLC')
    _add_keys(_working_chassis_obj, dict(ChassisObj=brcdapi_util.bc_vf), True)


def _switch_id(keys, val):
    """Adds the domain ID to _working_switch_obj"""
    global _working_switch_obj
    _add_keys(_working_switch_obj, keys, '0x' + val)


def _switch_insistent_did(keys, val):
    """Adds the insistent domain ID flag _working_switch_obj"""
    global _working_switch_obj
    _add_keys(_working_switch_obj, keys, False if val == '0' else True)


def _switch_role(keys, val):
    """Sets the switch role for _working_switch_obj"""
    global _working_switch_obj
    _add_keys(_working_switch_obj, keys, 1 if val.lower() == 'principal' else 0)


def _switch_num(keys, val):
    """Adds the domain ID to _working_switch_obj"""
    global _working_switch_obj
    _add_keys(_working_switch_obj, keys, gen_util.str_to_num(val))


def _switch_add(keys, val):
    """Generic add key/value pairs to _working_switch_obj"""
    global _working_switch_obj
    _add_keys(_working_switch_obj, keys, val)


def _port_status(keys, val):
    """Add the port status to _working_port_obj"""
    global _working_switch_obj, _working_port_obj, _first_port
    if _working_port_obj is None or not _first_port:
        return
    v = _reverse_port_status.get('Offline') if _reverse_port_status.get(val) is None else _reverse_port_status.get(val)
    _add_keys(_working_port_obj, keys, v)
    _add_keys(_working_port_obj, dict(PortObj=brcdapi_util.fc_enabled), True if v == 2 else False)


def _port_type(keys, val):
    """Add the port type to _working_port_obj"""
    global _working_port_obj, _first_port
    if _working_port_obj is None or not _first_port:
        return
    port_type = _reverse_port_type.get(val)
    _add_keys(_working_port_obj, keys, _reverse_port_type.get('Unknown') if port_type is None else port_type)


def _device_type(keys, in_val):
    """Add the FC4 type to _working_port_obj if 'Info From NS' is not present"""
    global _working_port_obj, _working_login_obj, _first_port, _target_dev_types

    if _working_port_obj is None or not _first_port:
        return
    if _working_login_obj is not None and _working_login_obj.r_get(brcdapi_util.bns_fc4_features) is not None:
        return  # The FC4 type was already picked up with 'Info From NS'
    if isinstance(in_val, str):
        val = in_val.lower()
        v = 'FCP-Target' if val in _target_dev_types else 'FCP-Initiator' if val in _initiator_dev_types else None
        if v is not None:
            _add_keys(_working_login_obj, keys, v)


def _login_features(keys, in_val):
    """Add the FC4 type to _working_port_obj"""
    global _working_port_obj, _first_port

    if _working_port_obj is None or not _first_port:
        return
    if isinstance(in_val, str):
        val = in_val.lower()  # I've never seen anything other than the first letter upper followed by all lower
        if 'unknown' in val:
            return
        v = '' 'FCP-Target' if 'target' in val else 'FCP-Initiator' if 'initiator' in val else ''
    else:
        v = ''
    _add_keys(_working_port_obj, keys, v)


def _login_simple_concatenate(keys, val):
    """Just add the key/value pair as specified from the table"""
    global _working_login_obj
    if _working_login_obj is None:
        return
    _add_keys(_working_login_obj, keys, val, True)


def _port_speed(keys, val):
    """Add the port type to _working_port_obj. $ ToDo - Figure out 'fibrechannel/auto-negotiate'"""
    global _working_port_obj, _first_port
    speed = gen_util.non_decimal.sub('', val)
    if _working_port_obj is None or not _first_port or not speed.isdigit():
        return
    _add_keys(_working_port_obj, keys, int(speed)*1000000000)


def _port_id(keys, val):
    """Action for FC Address"""
    global _working_port_obj
    _add_keys(_working_port_obj, keys, '0x' + str(val))  # Some addresses are interpreted as numbers in SAN Health


def _port_neighbor(keys, val):
    """Add a login"""
    global _working_port_obj, _working_login_obj
    port_type = _working_port_obj.r_get(brcdapi_util.fc_port_type)
    if port_type is not None and port_type in\
            (brcddb_common.PORT_TYPE_F, brcddb_common.PORT_TYPE_N, brcddb_common.PORT_TYPE_L):
        buf = _working_port_obj.r_get(brcdapi_util.fc_fcid_hex)
        d = {'port-name': val, 'port-id': '' if buf is None else buf}
        buf = _working_port_obj.r_get(brcdapi_util.fc_neighbor_node_wwn)
        if buf is not None:
            d.update({'node-name': buf})
        buf = _working_port_obj.r_get(brcdapi_util.fc_index)
        if buf is not None:
            d.update({'port-index': buf})
        _working_login_obj = _working_port_obj.r_fabric_obj().s_add_login(val)
        brcddb_util.add_to_obj(_working_login_obj, brcdapi_util.bns_uri, d)
        nl = _working_port_obj.r_get(brcdapi_util.fc_neighbor_wwn)
        if nl is None:
            nl = list()
            brcddb_util.add_to_obj(_working_port_obj, brcdapi_util.fc_neighbor_wwn, nl)
        nl.append(val)
        _add_keys(_working_port_obj, keys, val)


def _port_media_distance(keys, val):
    """$ToDo - WIP"""
    global _working_port_obj, _first_port
    if _working_port_obj is None or not _first_port:
        return
    _add_keys(_working_port_obj, keys, gen_util.non_decimal.sub('', val))


def _port_speed_capability(keys, val):
    """Add the SFP speed capabilities as a list of integers"""
    global _working_port_obj, _first_port

    if _working_port_obj is None or not _first_port:
        return

    val_l = [val] if isinstance(val, int) else \
        [int(buf) for buf in val.replace('_MB/s', '').replace('0', '').split(',')] if '_MB/s' in val else \
        [int(buf) for buf in str(val).replace('_Gbps', '').split(',')]
    _add_keys(_working_port_obj, keys, dict(speed=val_l))


def _port_simple(keys, val):
    """Just add the key/value pair as specified from the table"""
    global _working_port_obj, _first_port
    if _working_port_obj is None or not _first_port:
        return
    _add_keys(_working_port_obj, keys, val)


def _port_sfp_type(keys, val):
    """Add the SFP speed capabilities"""
    global _working_port_obj, _first_port
    if _working_port_obj is None or not _first_port:
        return
    _add_keys(_working_port_obj, keys, 850 if 'Short' in val or 'swl' in val else 1310)


def _port_db(keys, val):
    """Action for SFP Tx Power dBm and SFP Rx Power dBm"""
    global _working_port_obj
    _add_keys(_working_port_obj, keys, gen_util.dBm_to_absolute(val, 1))
    try:
        tl = keys['PortObj'].split('/')
        sh_d = _working_port_obj.r_get('san_health')
        if sh_d is None:
            sh_d = dict()
            _working_port_obj.s_new_key('san_health', sh_d)
        d = sh_d.get('media-rdp')
        if d is None:
            d = dict()
            sh_d.update({'media-rdp': d})
        d.update({tl.pop(): val})
    except KeyError:
        pass


"""The tables define the actions to be taken on the worksheets. The key is the value in the worksheet cell. The lookup
value is a dictionary or list of dictionaries that define the action to take as defined below. The action table contains
a list of these dictionaries so that multiple actions can be defined for each cell.

    +-----------+-----------------------------------------------------------------------------------------------+
    | Key       | Value                                                                                         |
    +===========+===============================================================================================+
    | keys      | Not required. If present, a dictionary or list of dictionaries whose key matches a simple     |
    |           | brcddb.classes.utils.simple_class_type type and whose value is the KPI to add to the          |
    |           | associated object with the cell contents as the value.                                        |
    +-----------+-----------------------------------------------------------------------------------------------+
    | a         | If not None, the method to call to process the sheet cell.                                    |
    +-----------+-----------------------------------------------------------------------------------------------+
"""
_sheet_essential_values = collections.OrderedDict()
_sheet_essential_values['Fabric Principal'] = dict(a=_fabric_for_switch)
_sheet_essential_values['World Wide Name'] = dict(keys=dict(
    SwitchObj=[brcdapi_util.bf_sw_wwn,
               brcdapi_util.bfls_sw_wwn,
               brcdapi_util.ficon_sw_wwn]),
    a=_create_switch)
_sheet_essential_values['Chassis Serial Num'] = dict(keys=dict(ChassisObj=brcdapi_util.bc_serial_num),
                                                     a=_create_chassis)
_sheet_essential_values['Switch Name'] = dict(keys=dict(
    SwitchObj=[brcdapi_util.bf_sw_user_name, brcdapi_util.bfs_sw_user_name]), a=_switch_add)
_sheet_essential_values['Fabric Name'] = dict(keys=dict(SwitchObj=brcdapi_util.bfs_fab_user_name), a=_switch_add)
_sheet_essential_values['Switch State'] = dict(keys=dict(SwitchObj=brcdapi_util.bfs_op_status), a=_switch_status)
_sheet_essential_values['Domain ID'] = dict(keys=dict(SwitchObj=brcdapi_util.bfs_did), a=_switch_num)
_sheet_essential_values['Switch Role'] = dict(keys=dict(SwitchObj=brcdapi_util.bfs_principal), a=_switch_role)
_sheet_essential_values['Model Name'] = dict(keys=dict(ChassisObj=brcdapi_util.bc_product_name), a=_switch_add)

_sheet_additional_values = collections.OrderedDict()
_sheet_additional_values['Switch ID'] = dict(keys=dict(SwitchObj=brcdapi_util.bfs_fcid_hex), a=_switch_id)
_sheet_additional_values['Insistent Domain'] = dict(keys=dict(SwitchObj=brcdapi_util.bfc_idid),
                                                    a=_switch_insistent_did)

_sheet_port_detail = collections.OrderedDict()  # Search for "Table Definitions & Methods"
_sheet_port_detail['Port Status'] = dict(keys=dict(PortObj=brcdapi_util.fc_op_status), a=_port_status)
_sheet_port_detail['Port Type'] = dict(keys=dict(PortObj=brcdapi_util.fc_port_type), a=_port_type)
_sheet_port_detail['FC Address'] = dict(keys=dict(PortObj=brcdapi_util.fc_fcid_hex), a=_port_id)
_sheet_port_detail['Port Speed'] = dict(keys=dict(PortObj=brcdapi_util.fc_speed), a=_port_speed)
_sheet_port_detail['Port Name'] = dict(keys=dict(PortObj=brcdapi_util.fc_user_name), a=_port_simple)
_sheet_port_detail['Node WWN'] = dict(keys=dict(PortObj=brcdapi_util.fc_neighbor_node_wwn), a=_port_simple)
_sheet_port_detail['Port WWN'] = dict(a=_port_neighbor)
_sheet_port_detail['Info From NS'] = dict(keys=dict(LoginObj=brcdapi_util.bns_fc4_features), a=_login_features)
_sheet_port_detail['Device Type'] = dict(keys=dict(LoginObj=brcdapi_util.bns_fc4_features), a=_device_type)
_sheet_port_detail['Description'] = dict(keys=dict(LoginObj=brcdapi_util.bns_node_symbol), a=_login_simple_concatenate)
_sheet_port_detail['Information'] = dict(keys=dict(LoginObj=brcdapi_util.bns_node_symbol), a=_login_simple_concatenate)
_sheet_port_detail['Model Number'] = dict(keys=dict(LoginObj=brcdapi_util.bns_node_symbol), a=_login_simple_concatenate)
_sheet_port_detail['Device Name'] = dict(keys=dict(LoginObj=brcdapi_util.bns_node_symbol), a=_login_simple_concatenate)
_sheet_port_detail['SFP Type'] = dict(keys=dict(PortObj=brcdapi_util.sfp_wave), a=_port_sfp_type)
_sheet_port_detail['SFP Vendor'] = dict(keys=dict(PortObj=brcdapi_util.sfp_vendor), a=_port_simple)
_sheet_port_detail['SFP Serial Num'] = dict(keys=dict(PortObj=brcdapi_util.sfp_sn), a=_port_simple)
_sheet_port_detail['SFP Capable Of'] = dict(keys=dict(PortObj='media-rdp/media-speed-capability'),
                                            a=_port_speed_capability)
_sheet_port_detail['SFP Vendor OUI'] = dict(keys=dict(PortObj=brcdapi_util.sfp_oui), a=_port_simple)
_sheet_port_detail['SFP Vendor PN'] = dict(keys=dict(PortObj=brcdapi_util.sfp_pn), a=_port_simple)
_sheet_port_detail['SFP Rx Power dBm'] = dict(keys=dict(PortObj=brcdapi_util.sfp_rx_pwr), a=_port_db)
_sheet_port_detail['SFP Tx Power dBm'] = dict(keys=dict(PortObj=brcdapi_util.sfp_tx_pwr), a=_port_db)

_sheet_port_frame_errors = collections.OrderedDict()  # Search for "Table Definitions & Methods"


def _sheet_act(sheet, start_i, end_i, act_tbl):
    """Action in _switch_sheet which is called in _process_switch() to extract sheet detail to the project object

    :param sheet: Worksheet contents as extracted from excel_util.read_workbook()
    :type sheet: dict
    :param start_i: Starting index in the list of sheet['sl'] where the Essential Switch Attributes begins.
    :type start_i: int
    :param end_i: Ending index in the list of sheet['sl'] where the Essential Switch Attributes ends.
    :type end_i: int
    :param act_tbl: List of action tables, such as _sheet_essential_values, to process the sheet contents
    :type act_tbl: list, tuple, None
    """
    sd = sheet['sl'][start_i: end_i]
    for action_tbl in gen_util.convert_to_list(act_tbl):
        for key, action in action_tbl.items():
            switch_d = report_utils.get_next_switch_d(sd, key, 'exact', True)
            if switch_d is not None:
                value = switch_d.get('val')
                for sub_action in gen_util.convert_to_list(action_tbl[key]):
                    sub_action['a'](sub_action.get('keys'), value)


def _port_act(port_l, act_tbl):
    """Port detail actions on switch sheet

    :param port_l: Worksheet contents as extracted from excel_util.read_workbook() for this port
    :type port_l: list
    :param act_tbl: List of action tables, such as _sheet_essential_values, to process the sheet contents
    :type act_tbl: list, tuple, None
    """
    global _working_switch_obj, _working_port_obj, _first_port, _port_seen, _working_login_obj

    # Add the port to the switch
    port, port_index = _get_port_num(port_l[0]['val'])
    _working_login_obj = None
    if port is None or port_index is None:
        return  # An error occurred in _get_port_num(). It is reported by _get_port_num()

    _working_port_obj = _working_switch_obj.s_add_port(port)
    if _working_port_obj is None:
        return  # SAN Health flakes out sometimes and returns an invalid port.

    if port in _port_seen[_working_switch_obj.r_obj_key()]:
        _first_port = False
    else:
        _first_port = True
        _port_seen[_working_switch_obj.r_obj_key()].update({port: True})
        brcddb_util.add_to_obj(_working_port_obj, brcdapi_util.fc_index, port_index)

    # Now process the port information
    for action_tbl in gen_util.convert_to_list(act_tbl):
        for key, action in action_tbl.items():
            for i in range(1, len(port_l)-1):
                if port_l[i]['val'] == key:
                    value = port_l[i+1]['val']
                    for sub_action in gen_util.convert_to_list(action_tbl[key]):
                        sub_action['a'](sub_action.get('keys'), value)
                    break


def _port_cfg_details_act(sheet, start_i, end_i, act_tbl):
    """Action in _switch_sheet which is called in _process_switch() to extract port detail to the project object

    :param sheet: Worksheet contents as extracted from excel_util.read_workbook()
    :type sheet: dict
    :param start_i: Starting index in the list of sheet['sl'] where the Essential Switch Attributes begins.
    :type start_i: int
    :param end_i: Ending index in the list of sheet['sl'] where the Essential Switch Attributes ends.
    :type end_i: int
    :param act_tbl: List of action tables, such as _sheet_essential_values, to process the sheet contents
    :type act_tbl: list, tuple, None
    """
    return  # $ToDo - Finish this


def _port_details(sheet, start_i, end_i, act_tbl):
    """Action in _switch_sheet which is called in _process_switch() to extract port detail to the project object

    :param sheet: Worksheet contents as extracted from excel_util.read_workbook()
    :type sheet: dict
    :param start_i: Starting index in the list of sheet['sl'] where the Essential Switch Attributes begins.
    :type start_i: int
    :param end_i: Ending index in the list of sheet['sl'] where the Essential Switch Attributes ends.
    :type end_i: int
    :param act_tbl: List of action tables, such as _sheet_essential_values, to process the sheet contents
    :type act_tbl: list, tuple, None
    """
    # Find the first port
    port_start_i = None
    sd = sheet['sl'][start_i: end_i]
    for port_start in range(0, len(sd)):  # Find the first port
        if '[ PORT' in sd[port_start]['val']:
            port_start_i = port_start
            break
    if port_start is None or port_start >= len(sd) or port_start_i is None:
        return  # This happens when there are no ports in the switch

    for i in range(min(port_start+1, len(sd)), len(sd)):
        if '[ PORT' in str(sd[i]['val']):
            _port_act(sd[port_start_i:i], act_tbl)  # Process the previous port
            port_start_i = i
    if i - port_start_i > 5:
        _port_act(sd[port_start_i:i], act_tbl)  # The last port


def _port_frame_error_act(sheet, start_i, end_i, act_tbl):
    """Action in _switch_sheet which is called in _process_switch() to extract frame errors from sheet detail

    parameters and return are the same as with _sheet_act()
    """
    global _frame_error_col_hdr, _working_switch_obj, _port_num

    # Figure out where all the columns are.
    row = int(gen_util.non_decimal.sub('', sheet['sl'][start_i+1]['cell']))
    try:
        last_row = int(gen_util.non_decimal.sub('', sheet['sl'][end_i]['cell'])) - 1
    except (TypeError, ValueError, IndexError):
        pass
    port_col = None
    full_row = sheet['al'][row]
    col_ref = dict()
    for col in range(0, len(full_row)):
        k = full_row[col]
        if isinstance(k, str):
            i = k.find('(')
            k = k.strip() if i < 0 else k[0: i].strip()
            if k == 'Slot/Port':
                port_col = col
            elif k in _frame_error_col_hdr:
                col_ref.update({_frame_error_col_hdr[k]: col})
    if port_col is None:
        brcdapi_log.exception('Could not find port number in FRAME ERROR COUNTS section of ' + sheet['sheet'],
                              echo=True)

    # Get all the port statistics
    for full_row in [sheet['al'][r] for r in range(row+1, last_row)]:
        if not isinstance(full_row[port_col], str):
            continue
        port_num = _port_num.sub('', full_row[port_col])
        port_obj = _working_switch_obj.s_add_port(port_num if '/' in port_num else '0/' + port_num)
        port_obj.s_new_key('fibrechannel', dict(neighbor=dict(wwn=list())))
        for k, col in col_ref.items():
            v = full_row[col]
            if isinstance(v, str):
                m = gen_util.multiplier.get(gen_util.decimal.sub('', v))
                # I think the only time this happens is when v == 'N/A'
                val = 0 if m is None else int(float(gen_util.non_decimal.sub('', v)) * m)
            else:
                val = 0 if v is None else v
            brcddb_util.add_to_obj(port_obj, k, val)


_switch_sheet = [
    dict(val='ESSENTIAL SWITCH ATTRIBUTES', search_type='exact', ignore_case=False, act=_sheet_act,
         act_tbls=_sheet_essential_values, required=True),
    dict(val='ADDITIONAL SWITCH ATTRIBUTES', search_type='exact', ignore_case=False, act=_sheet_act,
         act_tbls=_sheet_additional_values, required=True),
    dict(val='SWITCH COMPONENTS', search_type='exact', ignore_case=False, act=_sheet_act, act_tbls=None),
    dict(val='ISL / TRUNK SUMMARY', search_type='exact', ignore_case=False, act=_sheet_act, act_tbls=None),
    dict(val='IMPORTANT ALERTS AND WARNINGS', search_type='exact', ignore_case=False, act=_sheet_act, act_tbls=None),
    dict(val='FRAME ERROR COUNTS', search_type='exact', ignore_case=False, act=_port_frame_error_act, act_tbls=None),
    dict(val='PORT CONFIGURATION DETAILS', search_type='exact', ignore_case=False, act=_port_cfg_details_act,
         act_tbls=_sheet_port_frame_errors),
    dict(val='PORT DETAILS FOR', search_type='regex-m', ignore_case=False, act=_port_details,
         act_tbls=_sheet_port_detail),
]


def _process_switch(sheet_d):
    """Parses a switch detail sheet and adds it to the project object

    :param sheet_d: Worksheet contents as extracted from excel_util.read_workbook()
    :type sheet_d: dict
    :return: Status. See EXIT status codes in brcddb.common
    :rtype: int
    """
    global _act_objects, _proj_obj, _switch_sheet, _working_fab_obj, _working_chassis_obj, _working_switch_obj

    # If the sheet name is "S_n_xxxx" where n is an integer, it's a continuation of the previous sheet
    sheet_name = sheet_d.get('sheet')
    tl = sheet_name.split('_')
    continue_flag = True if len(tl) > 1 and tl[1].isnumeric() else False

    # First, figure out where the beginning and end of each section is. The sections match section headers in the SAN
    # Health report. The section headers, how to search for them, and what actions to take are defined in _switch_sheet.
    switch_sheet = copy.deepcopy(_switch_sheet)
    previous_d = None
    for d in switch_sheet:

        # Find the section header in the searchable data portion of object sheet
        ml = brcddb_search.match_test(sheet_d['sl'],
                                      dict(k='val', v=d['val'], t=d['search_type'], i=d['ignore_case']))
        if len(ml) == 0:
            if 'required' in d and d['required'] and not continue_flag:
                brcdapi_log.exception('Could not find ' + d['val'] + ' on ' + sheet_name, echo=True)
                return brcddb_common.EXIT_STATUS_ERROR
            continue

        # Find where this cell is in the array of row and column data
        cell = ml[len(ml)-1]['cell']  # len(ml) == 2 if the section is continued on the next sheet
        i = 0
        for switch_d in sheet_d['sl']:
            if switch_d['cell'] == cell:
                break
            i += 1
        if previous_d is not None:
            previous_d.update(end=i)
        previous_d = d
        d.update(start=i)

    # Process each section found - note that 'start' does not get added if the section wasn't found
    for switch_d in [d for d in switch_sheet if d.get('start') is not None]:
        switch_d['act'](sheet_d, switch_d.get('start'), switch_d.get('end'), switch_d['act_tbls'])

    return brcddb_common.EXIT_STATUS_OK


# ZONING
def _alias_act(name_col, sheet_data):
    global _working_fab_obj

    name, mem_l, alias_l = None, list(), _working_fab_obj.r_get(brcdapi_util.bz_def_alias)
    for row_l in sheet_data:
        if isinstance(row_l[name_col], str) and len(row_l[name_col]) > 0:
            if isinstance(name, str):
                obj = _working_fab_obj.s_add_alias(name, mem_l)
                alias_l.append({'alias-name': name, 'member-entry': {'alias-entry-name': mem_l}})
            name = row_l[name_col]
            mem_l = [row_l[col] for col in range(name_col+1, len(row_l)) if isinstance(row_l[col], str)]
        else:
            mem_l.extend([row_l[col] for col in range(name_col+1, len(row_l)) if isinstance(row_l[col], str)])

    return


def _zone_act(name_col, sheet_data):
    global _working_fab_obj

    name, zone_mem_l = None, list()
    for row_l in sheet_data:
        if isinstance(row_l[name_col], str) and len(row_l[name_col]) > 0:
            if name is not None:  # It's a new zone so add the previous zone
                zone_type, mem_l, pmem_l = parse_cli.cfgshow_zone_gen(_working_fab_obj, zone_mem_l)
                _working_fab_obj.s_add_zone(name, zone_type, mem_l, pmem_l)
            name = row_l[name_col]
            zone_mem_l = [buf for buf in row_l[name_col+1:] if isinstance(buf, str)]
        else:
            zone_mem_l.extend([buf for buf in row_l[name_col+1:] if isinstance(buf, str)])

    return


def _zonecfg_act(name_col, sheet_data):
    global _working_fab_obj

    cfg_l = _working_fab_obj.r_get(brcdapi_util.bz_def_cfg)
    name, mem_l = None, list()
    for row_l in sheet_data:
        if isinstance(row_l[name_col], str) and len(row_l[name_col]) > 0:
            if isinstance(name, str):
                vsan = '(' + name.split('(')[1] if '(vsan' in name else ''
                # vsan is for Cisco fabrics. I've never seen the zone name followed by (vsanxxx) in the zone
                # configuration section of the SAN Health report so checking to make sure (vsanxxx) doesn't get added
                # twice is just in case that ever changes. The best way to handle VSANs would be to make them FIDs, but
                # I'll probably never get around to doing that. Note that elsewhere in the SAN Health report the zone
                # is defined with (vsanxxx) in the name. Adding (vsanxxx) to the zone name when adding it to the zone
                # configuration was a quick and dirty expedient.
                _working_fab_obj.s_add_zonecfg(name, [mem if '(' in mem else mem+vsan for mem in mem_l])
                cfg_l.append({'cfg-name': name, 'member-zone': {'zone-name': mem_l}})
            name = row_l[name_col]
            mem_l = [row_l[col] for col in range(name_col+1, len(row_l)) if isinstance(row_l[col], str)]
        else:
            mem_l.extend([row_l[col] for col in range(name_col+1, len(row_l)) if isinstance(row_l[col], str)])


def _active_zone_act(name_col, sheet_data):
    global _working_fab_obj

    mem_l = list()
    for row_l in sheet_data:
        if isinstance(row_l[name_col], str) and len(row_l[name_col]) > 0:
            name = row_l[name_col]
            mem_l = [row_l[col] for col in range(name_col+1, len(row_l)) if isinstance(row_l[col], str) and
                     (gen_util.is_wwn(row_l[col]) or gen_util.is_di(row_l[col]))]
            if isinstance(name, str):
                _working_fab_obj.s_add_eff_zone(name, 0, mem_l)
        else:
            mem_l.extend([row_l[col] for col in range(name_col+1, len(row_l)) if isinstance(row_l[col], str) and
                          (gen_util.is_wwn(row_l[col]) or gen_util.is_di(row_l[col]))])


_zone_sheet = [dict(h='Alias Name', a=_alias_act),
               dict(h='Zone Name', a=_zone_act),
               dict(h='Config Name', a=_zonecfg_act),
               dict(h='Active Zones', a=_active_zone_act)]


def _process_zone(sheet_d):
    """Parses a zoning detail sheet and adds it to the fabric object for the fabric associated with the sheet

    :param sheet_d: Worksheet contents as extracted from excel_util.read_workbook()
    :type sheet_d: dict
    :return: Status. See EXIT status codes in brcddb.common
    :rtype: int
    """
    global _zone_sheet, _working_fab_obj, _zs_match

    # Get the active zone configuration name and set up the API zone dictionaries in the fabric object
    _working_fab_obj = _zs_match.get(sheet_d['sheet'])
    if _working_fab_obj is None:
        brcdapi_log.log('Could not find fabrics for ' + str(_zs_match.get(sheet_d['sheet'])))
        return brcddb_common.EXIT_STATUS_ERROR
    ml = brcddb_search.match_test(sheet_d['sl'], dict(k='val', v='RUNNING CONFIG*', t='wild', i=False))
    if len(ml) > 0:  # A zone configuration may not be active
        brcddb_util.add_to_obj(_working_fab_obj, brcdapi_util.bz_eff_cfg, ml[0]['val'].split('"')[1])
        buf = ml[0].get('val')
        if buf is not None:
            tl = buf.split('"')
            if len(tl) > 1:
                _working_fab_obj.s_add_eff_zonecfg()
    brcddb_util.add_to_obj(_working_fab_obj, brcdapi_util.bz_def_alias, list())
    brcddb_util.add_to_obj(_working_fab_obj, brcdapi_util.bz_def_cfg, list())
    brcddb_util.add_to_obj(_working_fab_obj, brcdapi_util.bz_def_zone, list())

    # First, figure out where the beginning and end of each section is. The sections match section headers in the SAN
    # Health report. The section headers, how to search for them, and what actions to take are defined in _zone_sheet.
    zone_sheet = copy.deepcopy(_zone_sheet)
    previous_d = None
    for d in zone_sheet:
        ml = brcddb_search.match_test(sheet_d['sl'], dict(k='val', v=d['h'], t='exact', i=False))
        if len(ml) == 0:
            brcdapi_log.exception('Could not find ' + d['h'] + ' on ' + str(sheet_d.get('sheet')), echo=True)
            return brcddb_common.EXIT_STATUS_ERROR
        start_i = int(gen_util.non_decimal.sub('', ml[0]['cell']))
        d.update(name_col=excel_util.col_to_num(ml[0]['cell']) - 1, start=start_i)
        if previous_d is not None:
            previous_d['a'](previous_d['name_col'], sheet_d['al'][previous_d['start']:start_i-1])
        previous_d = d

    # The last section is the effective zone configuration
    previous_d['a'](previous_d['name_col'], sheet_d['al'][previous_d['start']:])

    return brcddb_common.EXIT_STATUS_OK


_sheets_to_read_l = ('S_*', 'F_*', 'Z_*', 'SAN Ports')
_sheet_action_d = {
    'S_': _process_switch,
    'F_': _process_fabric,
    'Z_': _process_zone,
    'SAN Ports': _process_san_ports,
}


def _sh_to_project(debug_mode, debug_file, sh_file):
    """Reads a SAN Health Workbook and converts to a brcddb project.

    :param debug_mode: 0: process normally, 1: write to debug file, 2: read from debug file
    :type debug_mode: int
    :param debug_file: Name of debug file. Not used if debug_mode is 0
    :type debug_file: str
    :param sh_file: Name of SAN Health Workbook
    :type sh_file: str
    :return: Status. See EXIT status codes in brcddb.common
    :rtype: int
    """
    global _sheets_to_read_l, _sheet_action_d

    el, sheet_l = excel_util.read_workbook(sh_file, dm=debug_mode, sheets=_sheets_to_read_l, echo=True)
    ec = brcddb_common.EXIT_STATUS_ERROR if len(sheet_l) == 0 or len(el) > 0 else brcddb_common.EXIT_STATUS_OK
    if len(el) > 0:
        brcdapi_log.log(el, echo=True)

    if ec == brcddb_common.EXIT_STATUS_OK:
        sheet_keys_l = [str(k) for k in _sheet_action_d.keys()]
        for sheet_d in sheet_l:
            sheet_name = sheet_d['sheet']
            brcdapi_log.log('Processing sheet: ' + sheet_name, echo=True)
            try:
                for k in sheet_keys_l:
                    if sheet_name[0:len(k)] == k:
                        _sheet_action_d[k](sheet_d)
                        raise Found
            except Found:
                continue
            brcdapi_log.log('No action for sheet ' + sheet_name + '. Skipping sheet.')

    return ec


def _get_input():
    """Parses the module load command line

    :return in_file: Name of input file (Excel Workbook)
    :rtype in_file: str
    :return out_file: Name of output file
    :rtype out_file: str
    :return s_flag: Suppress flag
    :rtype s_flag: bool
    """
    global _DEBUG, _DEBUG_i, _DEBUG_o, _DEBUG_ucs, _DEBUG_dm, _DEBUG_sup, _DEBUG_log, _DEBUG_nl, _full_flag

    if _DEBUG:
        args_i, args_o, args_ucs, args_dm, args_sup, args_log, args_nl =\
            _DEBUG_i, _DEBUG_o, _DEBUG_ucs, _DEBUG_dm, _DEBUG_sup, _DEBUG_log, _DEBUG_nl
    else:
        buf = 'Converts a SAN Health report to a brcddb project (same output format as capture.py).'
        parser = argparse.ArgumentParser(description=buf)
        parser.add_argument('-i', help='Required. Name of SAN Health Report. ".xlsx is automatically appended.',
                            required=True)
        parser.add_argument('-o', help='Required. Output file name. ".json" is automatically appended.', required=True)
        buf = 'Check for WWNs that didn\'t show up on the detailed switch sheets. I think this only happens when the '\
              'SAN Health report is from a Cisco fabric and the WWN is part of a UCS port channel group but the WWN '\
              'didn\'t register with the name server. I\'m assuming that means the associated blade is offline.'
        parser.add_argument('-ucs', help=buf, required=False)
        buf = 'Optional. Sets the debug mode. 0: Read and process sheets normally. 1: Same as 0 and then do '\
              'a JSON dump to a file named as the input file with ".json" as the suffix. 2: Instead of reading and '\
              'converting the Excel Workbook, read the JSON dump when -dm was 1. 3: Default. If the .json file exists '\
              'and is newer than the .xlsx file, behave as mode 2, otherwise mode 1.'
        parser.add_argument('-dm', help=buf, required=False)
        buf = 'Optional. Suppress all library generated output to STD_IO except the exit code. Useful with batch' \
              'processing'
        parser.add_argument('-sup', help=buf, action='store_true', required=False)
        buf = '(Optional) Directory where log file is to be created. Default is to use the current directory. The log '\
              'file name will always be "Log_xxxx" where xxxx is a time and date stamp.'
        parser.add_argument('-log', help=buf, required=False,)
        buf = '(Optional) No parameters. When set, a log file is not created. The default is to create a log file.'
        parser.add_argument('-nl', help=buf, action='store_true', required=False)
        args = parser.parse_args()
        args_i, args_o, args_ucs, args_dm, args_sup, args_log, args_nl = \
            args.i, args.o, args.ucs, args.dm, args.sup, args.log, args.nl

    # Set up the log file
    if not args_nl:
        try:
            brcdapi_log.open_log(args_log, version_d=brcdapi_util.get_import_modules())
        except FileNotFoundError:
            print('The folder path specified with the -log, ' + args_log + ', option is not valid.')
            exit(brcddb_common.EXIT_STATUS_INPUT_ERROR)
        except PermissionError:
            print('You do not have access to the log folder, ' + args_log + '.')
            exit(brcddb_common.EXIT_STATUS_INPUT_ERROR)
    if args_sup:
        brcdapi_log.set_suppress_all()

    _full_flag = True if args_ucs else False

    return brcdapi_file.full_file_name(args_i, '.xlsx'), \
        brcdapi_file.full_file_name(args_o, '.json'), \
        3 if args_dm is None else int(args_dm)


def pseudo_main():
    """Basically the main().

    :return: Exit code
    :rtype: int
    """
    global _DEBUG, _proj_obj, _port_num, _cisco_isl_count, __version__

    # Get user input
    in_file, out_file, debug_mode = _get_input()
    debug_file = in_file.replace('.xlsx', '.json')
    ml = ['WARNING!!! Debug is enabled'] if _DEBUG else list()
    ml.append(os.path.basename(__file__) + ', ' + __version__)
    ml.append('Debug mode:   ' + str(debug_mode))
    if debug_mode > 3:
        brcdapi_log.log('Debug mode ' + str(debug_mode) + ' is not valid. Must be 0, 1, or 2.', echo=True)
        return brcddb_common.EXIT_STATUS_INPUT_ERROR
    ml.append('sh_capture:   ' + __version__)
    ml.append('Input file:   ' + in_file)
    ml.append('Output file:  ' + out_file)
    brcdapi_log.log(ml, echo=True)
    _proj_obj.s_description('From SAN Health: ' + in_file)
    # Read in the Workbook and convert to a brcddb project object
    ec = _sh_to_project(debug_mode, debug_file, in_file)
    if ec != brcddb_common.EXIT_STATUS_OK:
        return ec
    brcdapi_log.log('Cisco ISLs: ' + str(_cisco_isl_count), echo=True)

    # Finalize any outstanding object correlations.
    _remote_port_speed()

    # Save the project
    brcdapi_log.log("Saving project to: " + out_file, echo=True)
    plain_copy = dict()
    brcddb_copy.brcddb_to_plain_copy(_proj_obj, plain_copy)
    brcdapi_file.write_dump(plain_copy, out_file)
    brcdapi_log.log('Save complete', echo=True)

    return ec


###################################################################
#
#                    Main Entry Point
#
###################################################################
if _DOC_STRING:
    print('_DOC_STRING is True. No processing')
    exit(brcddb_common.EXIT_STATUS_OK)

_ec = pseudo_main()
brcdapi_log.close_log(['', 'Processing Complete. Exit code: ' + str(_ec)], echo=True)
exit(_ec)
