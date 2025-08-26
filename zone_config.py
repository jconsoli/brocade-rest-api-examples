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

Examples on how to create, modify and delete zone objects using the brcdapi.zone library. It's also a good walk through
to determine considerations for adding, deleting, modifying, and creating zone objects

I never thought anyone would zone form a workbook, but I needed something to validate zone changes ahead of a change
control window. So I created this module. A common use for it is to validate zone changes before attempting to make the
changes.

The operation is essentially the same as how FOS handles zoning in that zoning transactions are stored in memory and
then applied to the switch all at once. Specifically:

    1.  The zone database is read from the switch and added to the brcddb database referred to herein as the “local
        database”.
    2.  Actions specified in the input workbook are tested against the local database and if there are no errors, the
        local database is updated. (the ability to do is what supports the test mode, -t option).
    3.  A zone configuration activation (equivalent to cfgenable) or save (equivalent to cfgsave) then write the revised
        zone database to the switch.

**Common Data Structures**

*input_d*

input_d is passed to all action functions. It is used for tracking and control as defined below.

Note: My apologies for the like named data structures _input_d and input_d. _input_d is used for command line input.
input_d is used for input from the worksheet and some control information.

+-----------+-----------+-------------------------------------------------------------------------------------------+
| Key       | Type      | Description                                                                               |
+===========+===========+===========================================================================================+
| fab_obj   | FabricObj | Fabric object                                                                             |
+-----------+-----------+-------------------------------------------------------------------------------------------+
| zone_d    | dict      | Entry in the list returned from _parse_zone_workbook                                      |
+-----------+-----------+-------------------------------------------------------------------------------------------+
| search_d  | dict      | Search terms. See search_d in pseudo_main() for details.                                  |
+-----------+-----------+-------------------------------------------------------------------------------------------+
| el        | list      | Running list of error messages.                                                           |
+-----------+-----------+-------------------------------------------------------------------------------------------+
| wl        | list      | Running list of warning messages.                                                         |
+-----------+-----------+-------------------------------------------------------------------------------------------+
| cli_in    | bool      | True if the command line option -cli is used.                                             |
+-----------+-----------+-------------------------------------------------------------------------------------------+
| no_cli    | bool,     | If True, no CLI is generated. This is useful because there isn't a one for one mapping of |
|           |           | CLI commands to API requests. With expunge commands for example, there is one CLI command |
|           |           | to remove the zone object from all zone objects it is a member of and then delete the     |
|           |           | object. There is no need to do that in the API, so there isn't and equivalent API request.|
+-----------+-----------+-------------------------------------------------------------------------------------------+
| purge     | bool      | If True, after completing all actions, delete the zone object if the membership count is  |
|           |           | 0. At the time this was written, it applied to zone (not alias or zone configurations)    |
|           |           | objects only.                                                                             |
+-----------+-----------+-------------------------------------------------------------------------------------------+

*_tracking_d*

_tracking_d: Used for error reporting as follows:

    +---- _tracking_d
         +---- alias
              +---- {alias name}
                   +---- error_l    list    List of error messages (str)
                   +---- purge      bool    Not used
                   +---- purge_l    list    Not used
                   +---- row_l      list    List of relevant Worksheet row numbers
                   +---- warning_l  list    List of warning messages (str)
         +---- zone
              +---- {zone name}
                   +---- error_l    list    List of error messages (str)
                   +---- purge      bool    If True, this zone was effected by a full_purge action and should be
                                            deleted if the remaining membership count is 0
                   +---- purge_l    list    Filled in by _finish_purges(). List of remaining zone members that prevented
                                            the zone from being deleted as part of a purge action.
                   +---- row_l      list    List of relevant Worksheet row numbers
                   +---- warning_l  list    List of warning messages (str)
         +---- zone_cfg
              +---- {zone_cfg name}
                   +---- error_l    list    List of error messages (str)
                   +---- purge      bool    If True, this zone was effected by a full_purge action and should be
                                            deleted if the remaining membership count is 0
                   +---- purge_l    list    Not used
                   +---- row_l      list    List of relevant Worksheet row numbers
                   +---- warning_l  list    List of warning messages (str)
         +---- general
              +---- {area name}
                   +---- error_l    list    List of error messages (str)
                   +---- warning_l  list    List of warning messages (str)

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Removed deprecated parameter in enable_zonecfg()                                      |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 03 Apr 2024   | Renamed to zone_config.py from zone_config_x.py, Added version numbers of imported    |
|           |               | libraries. Added zone by sheet name, -sheet. Added -cli                               |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.3     | 15 May 2024   | Added migration and purge capabilities.                                               |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.4     | 16 Jun 2024   | Fixed name of sample workbook in help messages.                                       |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.5     | 29 Oct 2024   | Improved error messages.                                                              |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.6     | 26 Dec 2024   | Allow aliases to be added on separate rows with just additional members.              |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.7     | 04 Jan 2025   | Removed requirement for login credentials or input file. This way, just a test of the |
|           |               | zone configuration workbook is done and, optionally, a CLI file generated.            |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.8     | 04 Feb 2025   | Added copy, rename, replace, and ability to do a full_purge on zone configurations.   |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.9     | 01 Mar 2025   | Added support for "comment" Zone_Object. Fixed warning for members that cannot talk   |
|           |               | to other members. Removed redundant zoneadd in cli.                                   |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.1.0     | 25 Aug 2025   | Use brcddb.util.util.get_import_modules to dynamically determined imported libraries. |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2023, 2024, 2025 Consoli Solutions, LLC'
__date__ = '25 Aug 2025'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.1.0'

import collections
import sys
import os
import pprint
import datetime
import copy
import brcdapi.gen_util as gen_util
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as fos_auth
import brcdapi.log as brcdapi_log
import brcdapi.file as brcdapi_file
import brcdapi.util as brcdapi_util
import brcdapi.excel_util as excel_util
import brcdapi.zone as brcdapi_zone
import brcddb.brcddb_common as brcddb_common
import brcddb.brcddb_project as brcddb_project
import brcddb.brcddb_fabric as brcddb_fabric
import brcddb.brcddb_port as brcddb_port
import brcddb.brcddb_login as brcddb_login
import brcddb.api.interface as api_int
import brcddb.api.zone as api_zone
import brcddb.util.obj_convert as obj_convert

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation
# _STAND_ALONE: True: Executes as a standalone module taking input from the command line. False: Does not automatically
# execute. This is useful when importing this module into another module that calls psuedo_main().
_STAND_ALONE = True  # Typically True. See note above
_debug = False  # Adds run-time debug information. Gets set when -d is specified on the command line

_input_d = gen_util.parseargs_login_nr_d
_input_d['fid'] = dict(
    r=False, d=None, t='int', v=gen_util.range_to_list('1-128'),
    h='Optional. Fabric ID of logical switch. Required when -i is not specified and -ip is specified.')
_input_d['i'] = dict(
    r=False, d=None,
    h='Optional. Output of capture.py, multi_capture.py, or combine.py. When this option is specified, -ip, -id, -pw, '
      '-s, and -a are ignored. This is for offline test purposes only.')
_input_d['wwn'] = dict(r=False, d=None, h='Optional. Fabric WWN. Required when -i is specified. Otherwise not used.')
_input_d['z'] = dict(
    r=False, d=None,
    h='Required unless using -scan. Workbook with zone definitions. ".xlsx" is automatically appended. See '
      'zone_config_sample.xlsx.')
_input_d['sheet'] = dict(
    r=False, d=None,
    h='Required unless using -scan. Sheet name in workbook, -z, to use for zoning definitions.')
_input_d['a'] = dict(r=False, d=None, h='Optional. Name of zone configuration to activate (enable).')
_input_d['save'] = dict(
    r=False, d=False, t='bool',
    h='Optional. Save changes to the switch. By default, this module is in test mode only. Activating a zone '
      'configuration, -a, automatically saves changes.')
_input_d['cli'] = dict(
    r=False, d=None,
    h='Optional. Name of the file for CLI commands. ".txt" is automatically appended if a "." is not found in the file '
      'name. CLI commands are generated whether -save is specified or not.')
_input_d['strict'] = dict(
    r=False, d=False, t='bool',
    h='Optional. When set, warnings are treated as errors. Warnings are for inconsequential errors, such as deleting a '
      'zone that doesn\'t exist. The determination of a warning vs. an error is done on a row-by-row basis. Not all '
      'errors that are inconsequential will be treated as warnings. For example, when creating a zone that already '
      'exists, other rows are not examined to see if has the same members, so it will always be an error.')
_input_d.update(gen_util.parseargs_scan_d.copy())
_input_d.update(gen_util.parseargs_eh_d.copy())
_input_d.update(gen_util.parseargs_log_d.copy())
_input_d.update(gen_util.parseargs_debug_d.copy())

_eff_zone_l, _eff_mem_l = list(), list()
_pertinent_headers = ('Zone_Object', 'Action', 'Name', 'Match', 'Member', 'Principal Member', 'Comments')
_zone_kpis = (
    'running/brocade-fibrechannel-switch/fibrechannel-switch',
    'running/brocade-interface/fibrechannel',
    'running/brocade-zone/defined-configuration',
    'running/brocade-zone/effective-configuration',
    'running/brocade-fibrechannel-configuration/zone-configuration',
    'running/brocade-fibrechannel-configuration/fabric',
)
_pending_flag = False  # Updates were made to the brcddb zone database that have not been written to the switch yet.
# See _tracking_d in Common Data Structures
_tracking_d = dict(alias=dict(), zone=dict(), zone_cfg=dict(), general=dict())
for _key in ('purge', 'process'):
    _tracking_d['general'][_key] = dict(error_l=list(), warning_l=list())
_tracking_hdr_d = collections.OrderedDict(alias='Alias', zone='Zone', zone_cfg='Zone Configuration')
_default_zone_d = dict(row_l=list(), error_l=list(), warning_l=list(), purge=False, purge_l=list())

# _ignore_mem_d: Remaining zone members of a zone effected by a purge action to ignore when determining if it should be
# # deleted. The key is the alias, WWN, or d,i. Value is True. Currently, only alias is used.
_ignore_mem_d = dict(alias=dict(), zone=dict(), zone_cfg=dict())  # see note above
_cli_l = list()  # CLI commands
_MAX_ROWS = 20
_P1_MAX = 80  # Maximum character length for extended help.

_eh_l = [
    dict(p1_max=_P1_MAX),
    dict(p1=''),
    dict(p1='**Overview**'),
    dict(p1=''),
    dict(p1='Performs and validates zoning operations defined in an Excel Workbook. Although all zoning operations are '
            'supported, the primary purpose of this script is to support decommissioning or upgrading servers and '
            'storage. Since it has a test mode which can operate on offline data, it is also useful for validating '
            'zoning changes in advance of a zone change control window'),
    dict(p1=''),
    dict(p1='In addition to the standard create, delete, add member, and remove member zoning operations, it has the '
            'following features:'),
    dict(p1='', b1_char='a'),
    dict(b1='Rename zone objects'),
    dict(b1='Copy zone objects'),
    dict(b1='Use wild cards, ReGex matching, and ReGex searching on alias and zone names'),
    dict(b1='Purge zone objects. The report includes a purge fault summary, which is typically used to determine what '
            'zones and zone configurations are affected by a purge action.'),
    dict(b1='Generate CLI output for service personnel without script access'),
    dict(p1=''),
    dict(p1='**Supported Actions**'),
    dict(p1='', b1_prefix='', b1_char='add_mem    '),
    dict(b1='Adds a member to an alias, zone, or zone configuration membership list.'),
    dict(p1='', b1_prefix='', b1_char='copy       '),
    dict(b1='Copies an alias, zone, or zone configuration.'),
    dict(p1='', b1_prefix='', b1_char='create     '),
    dict(b1='Creates an alias, zone, or zone configuration.'),
    dict(p1='', b1_prefix='', b1_char='delete     '),
    dict(b1='Deletes an alias, zone, or zone configuration.'),
    dict(p1='', b1_prefix='', b1_char='purge      '),
    dict(b1='Supported for alias and zone actions only. The value in the "Member" cell is used to define the alias or '
            'zone for the purge action to act on. This is the equivalent to the CLI zoneobjectexpunge command.'),
    dict(p1='', b2_prefix='            ', b2_char='alias   '),
    dict(b2='Removes the alias, d,i, or WWN in the "Member" cell from any zone it is used in. Typically, a full_purge '
            'action is used to remove no longer needed aliases to avoid runt zones.'),
    dict(p1='', b2_prefix='            ', b2_char='zone    '),
    dict(b2='Removes the zone in the "Member" cell from any zone configuration it is used in.'),
    dict(p1='', b1_prefix='', b1_char='full_purge '),
    dict(b1='The value in the "Member" cell is used to define the alias, zone, or zone configuration for the '
            'full_purge action to act on.'),
    dict(p1='', b2_prefix='            ', b2_char='alias   '),
    dict(b2='Executes a purge action on the alias. A full_purge is then executed on any zone affected by the alias '
            'purge that has no remaining members. See “Ignore” for additional details.'),
    dict(p1='', b2_prefix='            ', b2_char='zone    '),
    dict(b2='After executing a purge action on the zone, any affected zone configuration with no remaining members is '
            'deleted. Any alias not used in any other zone is also deleted.'),
    dict(p1='', b2_prefix='            ', b2_char='zone_cfg'),
    dict(b2='Deletes the zone configuration. A full_purge action is executed on any affected zone that is not used in '
            'any other zone configuration.'),
    dict(p1='', b1_prefix='', b1_char='ignore     '),
    dict(b1='Typically not used. Effects the alias full_purge action only. Unless all aliases used in a zone are '
            'purged or deleted, the zone will have other members. Often, the desired result is to delete the zone even '
            'though members remain. Typically, the summary report is used to identify these zones and the members. The '
            'zone configuration worksheet is then updated manually to explicitly delete the zones. This forces you to '
            'look at the affected zones rather than automatically delete them.'),
    dict(p1='', b1_prefix='', b1_char='           '),
    dict(b1='The ignore action allows you to instruct the script to ignore certain zone members when counting zone '
            'membership so that they will be automatically deleted.'),
    dict(p1=''),
    dict(b1='Typical use cases are:'),
    dict(p1='', b2_prefix='            ', b2_char='*'),
    dict(b2='A server is being decommissioned and all that remains in the zone is the storage.'),
    dict(p1=''),
    dict(b2='A storage array is being decommissioned. The server member (alias, d,i, or WWN) is being used in other '
            'zones, but the applications using the storage in this zone have been decommissioned.'),
    dict(p1='', b1_prefix='', b1_char='remove_mem '),
    dict(b1='Deletes a member from an alias, zone, or zone configuration membership list.'),
    dict(p1='', b1_prefix='', b1_char='rename    '),
    dict(b1='Renames the zone object specified in the "Member" cell with the name specified in the "Principal Member" '
            'cell.'),
    dict(p1='', b1_prefix='', b1_char='replace    '),
    dict(b1='For alias, replaces all instances of the alias, WWN, or d,i specified in the "Member" cell with what is '
            'specified in the "Principal Member" cell in every zone where used. Similarly, zones are replaced in every '
            'zone configuration where used.'),
    dict(p1=''),
    dict(p1='**Tips & Notes**'),
    dict(p1=''),
    dict(p1='*Effective Zone*'),
    dict(p1=''),
    dict(p1='To avoid conflicts with the effective zone configuration, create and activate a new zone configuration.'),
    dict(p1=''),
    dict(p1='*Use*'),
    dict(p1=''),
    dict(p1='Typically, the initial evaluation is done from previously collected data using the -i option. This is '
            'especially so when using the purge actions to decommission storage arrays and server clusters. Since an '
            'error is generated anytime you attempt to delete a zone object used in another zone object, the error '
            'report in the summary is useful for determining zones and zone configurations effected by decommissioning '
            'storage and servers. You can also copy and paste the error list into the zone configuration workbook for '
            'an ignore action.'),
    dict(p1=''),
    dict(p1='*Removing Unused Aliases & Zones*'),
    dict(p1=''),
    dict(p1='The “Unused Aliases and Zones” worksheets in the output of report.py were created such that they can '
            'easily be copied to a zone configuration workbook. Remember to delete any rows in that workbook for zones '
            'or aliases you want to keep for later use.'),
    dict(p1=''),
    dict(p1='*Input Is Not Required*'),
    dict(p1=''),
    dict(p1='Specifying login credentials or an input file are only required for validating the zone changes against '
            'an existing zone database. If there is no input, the zone database is only validated against what is in '
            'the workbook. The intended purpose of allowing this script to be run without any input is to generate CLI '
            'only for what was specified in the workbook.'),
    dict(p1=''),
    dict(p1='*Order of Actions, Ignore, and Purging Zones*'),
    dict(p1=''),
    dict(p1='All actions are taken in the order they appear in the worksheet, beginning with row 2, except deleting '
            'zones and zone configurations as a result of a full_purge. Upon completion of all actions defined in the '
            'worksheet, any zone configuration that had at least one member deleted as a result of a purge will be '
            'deleted if is is not the effective zone configuration and there are no remaining members. A full_purge '
            'action will be taken on zones that had at least one member deleted as a result of a full purge and there '
            'are no remaining members that are not in the ignore list.'),
    dict(p1=''),
    dict(p1='*Full Purge*'),
    dict(p1=''),
    dict(p1='The purge action is equivalent to the CLI command "zoneobjectexpunge". A full purge is different in '
            'that:'),
    dict(p1=''),
    dict(p1='', b1_char='a'),
    dict(b1='The zone an alias was purged from is also deleted and purged from any zone configuration it was used in '
            'and if the zone has no members after the full purge is completed.'),
    dict(b1='All aliases not used in other zones are deleted as a result of a zone full purge.'),
    dict(b1='The full_purge action acts on zone configurations. The "zoneobjectexpunge" command does not act on zone '
            'configurations'),
    dict(p1=''),
]


class Found(Exception):
    pass


class FOSError(Exception):
    pass


def _reference_rows(object_type, object_name):
    """Formats the reference rows for error reporting.

    :param object_type: Object type, first key in _tracking_d
    :type object_type: str, key, None
    :param object_name: Name of zone object, second key into _tracking_d
    :type object_name: str, key, None
    :return: Empty string or CSV of row numbers if row numbers were found
    :rtype: str
    """
    global _tracking_d

    try:
        row_l = gen_util.remove_duplicates(_tracking_d[object_type][object_name]['row_l'])
        row_l.sort()
    except KeyError:
        row_l = list()

    return ' Rows: None' if len(row_l) == 0 else ' Rows: ' + ', '.join([str(i) for i in row_l])


def _add_to_tracking(key, input_d, error, warning, cli=None):
    """Adds an item to the tracking dictionary, _tracking_d

    :param key: 'comment', 'alias', 'zone', or 'zone_cfg'
    :type key: str
    :param input_d: See function header in _invalid_action()
    :type input_d: dict
    :param error: Error message(s) for this event
    :type error: str, list, None
    :param warning: Warning message(s) for this event
    :type warning: None, str, list
    :rtype: None
    """
    global _tracking_d, _default_zone_d, _cli_l

    d, zone_d = dict(error_l=list(), warning_l=list()), input_d['zone_d']

    # Add to tracking
    if key != 'comment':
        d = _tracking_d[key].get(zone_d['Name'])
        if d is None:
            d = copy.deepcopy(_default_zone_d)
            _tracking_d[key].update({zone_d['Name']: d})
        if isinstance(zone_d.get('row'), int):
            d['row_l'].extend(gen_util.convert_to_list(zone_d['row']))
        d['error_l'].extend(gen_util.convert_to_list(error))
        d['warning_l'].extend(gen_util.convert_to_list(warning))

    # Add CLI
    if isinstance(cli, str) and not input_d.get('no_cli', False):
        if key == 'comment':
            _cli_l.extend(['', '# ' + cli])
        else:
            buf, add_blank_line = '', False
            for e_buf in d['error_l']:
                buf, add_blank_line = '# ', True
                _cli_l.extend(['', '# Error: ' + e_buf])
            for e_buf in d['warning_l']:
                add_blank_line = True
                _cli_l.extend(['', '# Warning: ' + e_buf])
            _cli_l.extend(gen_util.convert_to_list(cli))
            if add_blank_line:
                _cli_l.append('')


def _set_purge(obj_type, obj_name):
    """Sets the purge attribute in _tracking_d.

    :param obj_type: This is the first key into _tracking_d
    :type obj_type: key, str
    :param obj_name: The name of the zone object, second key into _tracking_d
    """
    global _tracking_d, _default_zone_d

    zone_d = _tracking_d[obj_type].get(obj_name)
    if zone_d is None:
        zone_d = copy.deepcopy(_default_zone_d)
        _tracking_d[obj_type][obj_name] = zone_d
    zone_d['purge'] = True


def _build_cli_file(cli_file, fid):
    """Write the CLI commands to a file

    :param cli_file: Name of CLI file
    :type cli_file: str, None
    :param fid: Fabric ID
    :type fid: int, str, None
    :return: Error messages
    :rtype: list
    """
    global _cli_l, _MAX_ROWS

    if not isinstance(cli_file, str):
        return list()
    cli_l = list()

    # Insert setcontext if necessary
    if isinstance(fid, (str, int)):
        cli_l.extend(['setcontext ' + str(fid), ''])

    # Insert a blank line periodically
    i = 0
    for buf in _cli_l:
        cli_l.append(buf)
        i = 0 if len(buf) == 0 else i + 1
        if i >= _MAX_ROWS:
            cli_l.append('')
            i = 0

    return brcdapi_file.write_file(cli_file, cli_l)


def _finish_purges(fab_obj):
    """Validates the zone database

    :param fab_obj: Fabric object
    :type fab_obj: brcddb.classes.fabric.FabricObj
    :rtype: None
    """
    global _tracking_d, _ignore_mem_d

    if fab_obj is None:
        _tracking_d['general']['purge']['warning_l'].append('No fabric object. Unable to complete purges.')

    # Check for zone configuration purges
    for name, track_d in _tracking_d['zone_cfg'].items():
        zonecfg_obj = fab_obj.r_zonecfg_obj(name)
        if zonecfg_obj is not None:
            if track_d.get('purge', False) and len(zonecfg_obj.r_members()) == 0:
                _zonecfg_delete(dict(zone_d=dict(Name=name), fab_obj=fab_obj))

    # Check for zone purges
    for name, track_d in _tracking_d['zone'].items():
        zone_obj = fab_obj.r_zone_obj(name)
        if zone_obj is not None:
            if track_d.get('purge', False):
                mem_l = zone_obj.r_members() + zone_obj.r_pmembers()
                temp_l = [m for m in mem_l if not _ignore_mem_d['alias'].get(m, False)]
                if len(temp_l) == 0:
                    _zone_delete(dict(zone_d=dict(Name=name), fab_obj=fab_obj))
                else:
                    track_d['purge_l'].extend(temp_l)


def _validation_check(args_d, fab_obj):
    """Validates the zone database

    :param args_d: Input arguments. See _input_d for details.
    :type args_d: dict
    :param fab_obj: Fabric object
    :type fab_obj: brcddb.classes.fabric.FabricObj
    :rtype: None
    """
    global _tracking_d

    if fab_obj is None:
        return

    # Make sure all the zones and aliases used in each configuration still exist
    for zonecfg_obj in [obj for obj in fab_obj.r_zonecfg_objects() if obj.r_obj_key() != '_effective_zone_cfg']:
        zonecfg = zonecfg_obj.r_obj_key()
        zone_obj_l = zonecfg_obj.r_zone_objects()
        if zonecfg in _tracking_d['zone_cfg'] and len(zone_obj_l) == 0:
            _add_to_tracking('zone_cfg',
                             dict(zone_d=dict(Name=zonecfg), fab_obj=fab_obj),
                             None,
                             'Does not contain any members.')
        for zone_obj in zonecfg_obj.r_zone_objects():
            zone = zone_obj.r_obj_key()
            if fab_obj.r_zone_obj(zone) is None:
                if zone in _tracking_d['zone']:
                    row_l = _tracking_d['zone_cfg'].get(zonecfg, dict(row_l=list())).get('row_l', list())
                    row_l.extend(_tracking_d['zone'].get(zone, dict(row_l=list())).get('row_l', list()))
                    _add_to_tracking('zone_cfg',
                                     dict(zone_d=dict(Name=zonecfg, row=row_l), fab_obj=fab_obj),
                                     'Zone member does not exist.',
                                     None)
            else:
                # Make sure all the aliases exist
                for alias in zone_obj.r_members() + zone_obj.r_pmembers():
                    if alias in _tracking_d['alias']:
                        if gen_util.is_valid_zone_name(alias) and fab_obj.r_alias_obj(alias) is None:
                            row_l = _tracking_d['zone_cfg'].get(zonecfg, dict(row_l=list())).get('row_l', list())
                            row_l.extend(_tracking_d['alias'].get(alias, dict(row_l=list())).get('row_l', list()))
                            buf = 'Alias ' + alias + ', used in ' + zone + ' does not exist.'
                            _add_to_tracking('zone_cfg',
                                             dict(zone_d=dict(Name=zonecfg, row=row_l), fab_obj=fab_obj),
                                             buf,
                                             None)
                # Are there any devices that cannot communicate with each other?
                if zone in _tracking_d['zone']:
                    try:
                        if zone_obj.r_is_peer():
                            if len(zone_obj.r_members()) == 0 and len(zone_obj.r_pmembers()) == 0:
                                raise Found
                        elif len(zone_obj.r_members()) < 0:
                            raise Found
                    except Found:
                        _add_to_tracking(
                            'zone',
                            dict(zone_d=dict(Name=zone), fab_obj=fab_obj),
                            None,
                            'Does not contain any members that can talk to each other.'
                        )

    # Is a new zone configuration being activated and if so, does it exist?
    if isinstance(args_d['a'], str):
        cli = 'cfgenable "' + args_d['a'] + '" -f'
        buf = 'Specified with -a. Does not exist.' if fab_obj.r_zonecfg_obj(args_d['a']) is None else None
        _add_to_tracking('zone_cfg', dict(zone_d=dict(Name=args_d['a'])), buf, None, cli=cli)
    else:
        # Does the effective zone configuration match the defined zone configuration?
        eff_zone_cfg_obj = fab_obj.r_defined_eff_zonecfg_obj()
        if eff_zone_cfg_obj is not None:
            eff_zonecfg_name = fab_obj.r_defined_eff_zonecfg_key()
            zonecfg_obj = fab_obj.r_zonecfg_obj(eff_zonecfg_name)
            if zonecfg_obj is None:
                buf = 'Effective zone configuration. Defined zone configuration no longer exists.'
                _add_to_tracking('zone_cfg', dict(zone_d=dict(Name=eff_zonecfg_name)), buf, None)
            else:
                # ToDo - Add warnings for mismatches between the effective and defined zone configurations
                # All I'm checking for right now are errors that would prevent FOS from accepting the changes.
                pass
            for zone_obj in eff_zone_cfg_obj.r_zone_objects():
                zone = zone_obj.r_obj_key()
                if fab_obj.r_zone_obj(zone) is None:
                    e_buf = 'Effective zone configuration. Zone ' + zone + ' no longer exists.'
                    _add_to_tracking('zone_cfg', dict(zone_d=dict(Name=zone)), e_buf, None)
                else:  # Make sure all the aliases still exist
                    alias_l = [m for m in zone_obj.r_members()+zone_obj.r_pmembers() if gen_util.is_valid_zone_name(m)]
                    for alias in [m for m in alias_l if fab_obj.r_alias_obj(m) is None]:
                        e_buf = 'Effective zone configuration. Alias ' + alias + ' used in zone ' + zone
                        e_buf += ' does not exist.'
                        _add_to_tracking('zone_cfg', dict(zone_d=dict(Name=eff_zonecfg_name)), e_buf, None)


#################################################
#                                               #
#         Actions for _zone_action_d            #
#                                               #
#################################################
def _invalid_action(input_d):
    """Error handler for "Actions" not supported by the "Zone_Object"
    
    :param input_d: See **Common Data Structures**, *input_d*, in the module header
    :type input_d: dict
    """
    zone_d = input_d.get('zone_d', dict())
    if 'Name' not in zone_d:
        zone_d['Name'] = 'Unknown'
    buf = '"' + str(zone_d.get('Action')) + '" is not a valid Action for Zone_Object "' + str(zone_d.get('Zone_Object'))
    buf += '" for match type "' + str(zone_d.get('Match')) + '"'
    _add_to_tracking(zone_d.get('Zone_Object', 'general'), input_d, buf, None)


def _alias_create(input_d):
    """Create an alias. See _invalid_action() for parameter descriptions"""
    global _pending_flag

    # If it's a previous action, members are being added
    if input_d['zone_d']['name_c']:
        return _alias_add_mem(input_d)

    el, wl = list(), list()
    name, member, fab_obj = input_d['zone_d']['Name'], input_d['zone_d']['Member'], input_d['fab_obj']

    # Make sure it's a valid alias definition
    if isinstance(input_d['zone_d']['Principal Member'], str):  # Principal members are not supported in an alias
        el.append('Principal members not supported in alias.')
    elif not gen_util.is_valid_zone_name(name):  # Is it a valid alias name?
        el.append('Invalid name, ' + name + '.')
    elif not gen_util.is_wwn(member, full_check=True) and not gen_util.is_di(member):  # Valid WWN?
        el.append('Invalid member, ' + member + '.')
    elif fab_obj is not None:
        alias_obj = fab_obj.r_alias_obj(name)
        if alias_obj is None:
            fab_obj.s_add_alias(name, member)
            _pending_flag = True
        else:
            el.append('Already exists.')

    _add_to_tracking('alias', input_d, el, None, cli='alicreate "' + name + '", "' + member + '"')


def _alias_copy(input_d):
    """Copy an alias. See _invalid_action() for parameter descriptions"""
    global _pending_flag

    el, wl = list(), list()
    name, member, fab_obj = input_d['zone_d']['Name'], input_d['zone_d']['Member'], input_d['fab_obj']
    pmember = input_d['zone_d']['Principal Member']

    # Make sure it's a valid alias definition
    if pmember is not None:  # Principal members are not supported with alias copy
        el.append('Principal members not supported in alias.')
    elif not gen_util.is_valid_zone_name(member):  # Is it a valid alias name?
        el.append('Invalid alias name, ' + member + '.')
    elif fab_obj is not None:
        alias_obj = fab_obj.r_alias_obj(name)
        if alias_obj is None:
            el.append('Alias ' + name + ' does not exists.')
        else:
            copy_alias_obj = fab_obj.r_alias_obj(member)
            if copy_alias_obj is not None:
                el.append('Alias ' + member + ' already exists.')
            else:  # Create the alias and add the members
                fab_obj.s_add_alias(member, alias_obj.r_members())
                _pending_flag = True

    _add_to_tracking('alias', input_d, el, wl, cli='zoneobjectcopy "' + name + '", "' + member + '"')


def _alias_delete(input_d):
    """Delete an alias. See _invalid_action() for parameter descriptions"""
    global _pending_flag

    el, wl = list(), list()
    name, fab_obj = input_d['zone_d']['Name'], input_d['fab_obj']

    if fab_obj is not None:
        alias_obj = fab_obj.r_alias_obj(name)
        if alias_obj is None:
            buf = 'Alias ' + name + ' does not exist.'
            if not gen_util.is_valid_zone_name(name):
                buf += ' Did you intend to set a match type in the "Match" column?'
            wl.append(buf)
        else:
            fab_obj.s_del_alias(name)
            _pending_flag = True

    _add_to_tracking('alias', input_d, el, wl, cli='alidelete "' + name + '"')


def _alias_delete_m(input_d):
    """Delete aliases based on a regex or wild card match. See _invalid_action() for parameter descriptions"""
    name = input_d['zone_d']['Name']

    for alias in gen_util.match_str(input_d['search_d']['alias_l'], name, stype=input_d['zone_d']['Match']):
        input_d['zone_d']['Name'] = alias
        _alias_delete(input_d)
    input_d['zone_d']['Name'] = name


def _alias_add_mem(input_d):
    """Add alias members. See _invalid_action() for parameter descriptions"""
    global _pending_flag

    el, wl = list(), list()
    name, member = input_d['zone_d']['Name'], input_d['zone_d']['Member']
    pmember, fab_obj = input_d['zone_d']['Principal Member'], input_d['fab_obj']

    # Validate the members and add if OK
    if pmember is not None:
        el.append('Principal members not supported in alias.')
    elif not gen_util.is_wwn(member, full_check=True) and not gen_util.is_di(member):
        el.append('Invalid alias member, ' + member + '.')
    elif fab_obj is not None:
        alias_obj = fab_obj.r_alias_obj(name)
        if alias_obj is None:
            buf = 'Alias ' + name + ' does not exist.'
            if not gen_util.is_valid_zone_name(name):
                buf += ' Did you intend to set a match type in the "Match" column?'
            el.append(buf)
        elif member in alias_obj.r_members():
            wl.append('Member ' + member + ' is already in ' + name + '.')
        else:
            alias_obj.s_add_member(member)
            _pending_flag = True

    _add_to_tracking('alias', input_d, el, wl, cli='aliadd "' + name + '", "' + member + '"')


def _alias_remove_mem(input_d):
    """Remove alias members. See _invalid_action() for parameter descriptions"""
    global _pending_flag

    el, wl = list(), list()
    name, member, fab_obj = input_d['zone_d']['Name'], input_d['zone_d']['Member'], input_d['fab_obj']
    if fab_obj is not None:
        alias_obj = fab_obj.r_alias_obj(name)
        if alias_obj is None:
            buf = 'Alias ' + name + ' does not exist.'
            if not gen_util.is_valid_zone_name(name):
                buf += ' Did you intend to set a match type in the "Match" column?'
            el.append(buf)
        else:
            alias_obj.s_del_member(name, member)
            _pending_flag = True

    _add_to_tracking('alias', input_d, el, wl, cli='aliremove "' + name + '", "' + member + '"')


def _alias_purge(input_d):
    """Purges an alias. See _invalid_action() for parameters"""
    name, fab_obj = input_d['zone_d']['Name'], input_d['fab_obj']
    if fab_obj is not None:
        alias_obj = fab_obj.r_alias_obj(name)
        if alias_obj is not None:
            alias = alias_obj.r_obj_key()

            # Delete the alias member in every zone where it is used.
            for zone_obj in obj_convert.obj_extract(alias_obj, 'ZoneObj'):
                zone = zone_obj.r_obj_key()
                temp_input_d = dict(
                    zone_d={
                        'Name': zone,
                        'row': input_d['zone_d']['row'],
                        'Member': alias if alias in zone_obj.r_members() else None,
                        'Principal Member': alias if alias in zone_obj.r_pmembers() else None,
                    },
                    fab_obj=fab_obj,
                    no_cli=True
                )
                _zone_remove_mem(temp_input_d)

            # Delete the alias
            no_cli = input_d.get('no_cli', False)
            input_d['no_cli'] = True
            _alias_delete(input_d)
            input_d['no_cli'] = no_cli

    _add_to_tracking('alias', input_d, None, None, cli='zoneobjectexpunge "' + name + '" -f')


def _alias_full_purge(input_d):
    """Purges an alias and then a full purge on any resulting empty zones. See _invalid_action() for parameters"""
    name, fab_obj = input_d['zone_d']['Name'], input_d['fab_obj']
    alias_obj = None if fab_obj is None else fab_obj.r_alias_obj(name)
    if alias_obj is not None:
        for zone_obj in obj_convert.obj_extract(alias_obj, 'ZoneObj'):
            _set_purge('zone', zone_obj.r_obj_key())
        _alias_purge(input_d)


def _alias_purge_m(input_d):
    """Purges aliases based on a regex or wild card match. See _invalid_action() for parameters"""
    name = input_d['zone_d']['Name']
    for alias in gen_util.match_str(input_d['search_d']['alias_l'], name, stype=input_d['zone_d']['Match']):
        input_d['zone_d']['Name'] = alias
        _alias_purge(input_d)
    input_d['zone_d']['Name'] = name


def _alias_full_purge_m(input_d):
    """Performs an alias full purge based on a regex or wild card match. See _invalid_action() for parameters"""
    name = input_d['zone_d']['Name']
    for alias in gen_util.match_str(input_d['search_d']['alias_l'], name, stype=input_d['zone_d']['Match']):
        input_d['zone_d']['Name'] = alias
        _alias_full_purge(input_d)
    input_d['zone_d']['Name'] = name


def _alias_ignore(input_d):
    """Set alias to ignore. See _invalid_action() for parameters"""
    global _ignore_mem_d

    _ignore_mem_d['alias'][input_d['zone_d']['Name']] = True


def _alias_ignore_m(input_d):
    """Set aliases to ignore based on a regex or wild card match. See _invalid_action() for parameters"""
    name = input_d['zone_d']['Name']
    for alias in gen_util.match_str(input_d['search_d']['alias_l'], name, stype=input_d['zone_d']['Match']):
        _ignore_mem_d['alias'][alias] = True


def _peer_zone_create(input_d):
    """Create a peer zone. See _invalid_action() for parameter descriptions"""
    global _pending_flag, _cli_l

    el, wl = list(), list()
    name, member, fab_obj = input_d['zone_d']['Name'], input_d['zone_d']['Member'], input_d['fab_obj']
    pmember = input_d['zone_d']['Principal Member']

    # If it's a previous action, members are being added
    if input_d['zone_d']['name_c']:
        return _zone_add_mem(input_d)

    # Make sure it's a valid zone definition
    if not gen_util.is_valid_zone_name(name):
        el.append('Invalid zone name, ' + name + '.')
    elif isinstance(member, str) and \
            not gen_util.is_wwn(member, full_check=True) and \
            not gen_util.is_di(member) and \
            not gen_util.is_valid_zone_name(member):
        el.append('Invalid zone member, ' + member + '.')
    else:  # Create the peer zone
        zone_obj = fab_obj.r_zone_obj(name)
        if zone_obj is not None:
            el.append('Zone ' + name + ' already exists.')
        elif fab_obj is not None:
            fab_obj.s_add_zone(name, brcddb_common.ZONE_USER_PEER, member, pmember)
            _pending_flag = True

    buf = 'zonecreate --peerzone "' + name + '"'
    if isinstance(pmember, str):
        buf += ' -principal "' + pmember + '"'
    if isinstance(member, str):
        buf += ' -members "' + member + '"'
    _add_to_tracking('zone', input_d, el, wl, cli=buf)


def _zone_create(input_d):
    """Create a zone. See _invalid_action() for parameter descriptions"""
    global _pending_flag, _cli_l

    el, wl = list(), list()
    name, member, fab_obj = input_d['zone_d']['Name'], input_d['zone_d']['Member'], input_d['fab_obj']
    pmember = input_d['zone_d']['Principal Member']

    # If it's a previous action, members are being added
    if input_d['zone_d']['name_c']:
        return _zone_add_mem(input_d)

    # Make sure it's a valid zone definition
    if pmember is not None:  # Principal members are only supported in peer zones
        el.append('Principal members only supported in peer zones.')
    elif not gen_util.is_valid_zone_name(name):  # Is the zone name valid?
        el.append('Invalid zone name, ' + name + '.')
    elif not gen_util.is_wwn(member, full_check=True) and not gen_util.is_di(member) and \
            not gen_util.is_valid_zone_name(member):
        el.append('Invalid zone member, ' + member + '.')
    elif fab_obj is not None:
        zone_obj = fab_obj.r_zone_obj(name)
        if zone_obj is not None:
            el.append('Zone ' + name + ' already exists.')
        else:
            fab_obj.s_add_zone(name, brcddb_common.ZONE_STANDARD_ZONE, member, pmember)
            _pending_flag = True

    _add_to_tracking('zone', input_d, el, wl, cli='zonecreate "' + name + '", "' + input_d['zone_d']['Member'] + '"')


def _zone_copy(input_d):
    """Copy a zone. See _invalid_action() for parameter descriptions"""
    global _pending_flag

    el, wl = list(), list()
    name, member, fab_obj = input_d['zone_d']['Name'], input_d['zone_d']['Member'], input_d['fab_obj']
    pmember = input_d['zone_d']['Principal Member']

    # Make sure it's a valid zone definition
    if pmember is not None:  # Principal members are not supported with zone copy
        el.append('Use "Member", not "Principal Member" for zone copy.')
    elif not gen_util.is_valid_zone_name(member):  # Is it a valid zone name?
        el.append('Invalid zone name, ' + member + '.')
    elif fab_obj is not None:
        zone_obj = fab_obj.r_zone_obj(name)
        if zone_obj is None:
            el.append('Zone ' + name + ' does not exists.')
        else:
            copy_zone_obj = fab_obj.r_zone_obj(member)
            if copy_zone_obj is not None:
                el.append('Zone ' + member + ' already exists.')
            else:  # Create the zone and add the members
                fab_obj.s_add_zone(member, zone_obj.r_type(), zone_obj.r_members(), zone_obj.r_pmembers())
                _pending_flag = True

    _add_to_tracking('zone', input_d, el, wl, cli='zoneobjectcopy "' + name + '", "' + member + '"')


def _zone_delete(input_d):
    """Delete a zone. See _invalid_action() for parameter descriptions"""
    global _pending_flag

    el, wl = list(), list()
    name, fab_obj = input_d['zone_d']['Name'], input_d['fab_obj']

    if fab_obj is not None:
        if fab_obj.r_zone_obj(name) is None:
            buf = 'Zone ' + name + ' does not exist.'
            if not gen_util.is_valid_zone_name(name):
                buf += ' Did you intend to set a match type in the "Match" column?'
            wl.append(buf)
        else:
            fab_obj.s_del_zone(name)
            _pending_flag = True

    _add_to_tracking('zone', input_d, el, wl, cli='zonedelete ' + name)


def _zone_delete_m(input_d):
    """Delete zones based on a regex or wild card match. See _invalid_action() for parameters"""
    name = input_d['zone_d']['Name']
    for zone in gen_util.match_str(input_d['search_d']['zone_l'], name, stype=input_d['zone_d']['Match']):
        input_d['zone_d']['Name'] = zone
        _zone_delete(input_d)
    input_d['zone_d']['Name'] = name  # I don't think I need to do this, but just in case I'm overlooking something


def _zone_add_mem(input_d):
    """Add zone members. See _invalid_action() for parameter descriptions"""
    global _pending_flag

    el, wl = list(), list()
    name, member, fab_obj = input_d['zone_d']['Name'], input_d['zone_d']['Member'], input_d['fab_obj']
    pmember = input_d['zone_d']['Principal Member']

    if fab_obj is not None:
        # Validate the parameters
        zone_obj = fab_obj.r_zone_obj(name)
        if zone_obj is None:
            buf = 'Zone ' + name + ' does not exist.'
            if not gen_util.is_valid_zone_name(name):
                buf += ' Did you intend to set a match type in the "Match" column?'
            el.append(buf)
        mem = pmember
        if isinstance(mem, str):
            if not zone_obj.r_is_peer():
                el.append('Principal members only supported in peer zones.')
            if not gen_util.is_wwn(mem, full_check=True) and \
                    not gen_util.is_di(mem) and not gen_util.is_valid_zone_name(mem):
                el.append('Invalid zone member, ' + mem + '.')
        for mem in [m for m in [member, pmember] if isinstance(m, str)]:
            if not gen_util.is_wwn(mem, full_check=True) and not gen_util.is_di(mem) and \
                    not gen_util.is_valid_zone_name(mem):
                el.append('Invalid zone member, ' + mem + '.')

        # Add the zone members
        zone_obj.s_add_member(member)
        zone_obj.s_add_pmember(pmember)
        _pending_flag = True

    buf = 'zoneadd '
    if input_d['zone_d']['Zone_Object'] == 'peer_zone':
        buf += '--peerzone '
    buf += '"' + name + '"'
    if isinstance(pmember, str):
        buf += ' -principal "' + pmember + '"'
    if isinstance(member, str):
        buf += ' -members "' + member + '"'
    _add_to_tracking('zone', input_d, el, wl, cli=buf)


def _peer_zone_remove_mem(input_d):
    """Remove zone members. See _invalid_action() for parameter descriptions"""
    global _pending_flag

    el, wl = list(), list()
    name, member, fab_obj = input_d['zone_d']['Name'], input_d['zone_d']['Member'], input_d['fab_obj']
    pmember = input_d['zone_d']['Principal Member']

    if fab_obj is not None:
        # Validate the input
        zone_obj = fab_obj.r_zone_obj(name)
        if zone_obj is None:
            buf = 'Zone ' + name + ' does not exist.'
            if not gen_util.is_valid_zone_name(name):
                buf += ' Did you intend to set a match type in the "Match" column?'
            el.append(buf)
        elif zone_obj.r_is_peer():
            if isinstance(member, str) and member not in zone_obj.r_member():
                if member in zone_obj.r_pmembers():
                    el.append('The "Member" is a "Principal Member".')
                else:
                    wl.append(member + ' is not a member of ' + name + '.')
            if isinstance(pmember, str) and pmember not in zone_obj.r_pmember():
                if pmember in zone_obj.r_members():
                    el.append('The "Principal Member" is a "Member".')
                else:
                    wl.append(pmember + ' is not a principal member of ' + name)
        else:
            el.append('Zone type mismatch. ' + name + ' is not a peer zone.')

        # Make the zoning changes
        if len(el) == 0:
            zone_obj.s_del_member(member)
            zone_obj.s_del_pmember(pmember)
            _pending_flag = True

    buf = 'zoneremove --peerzone "' + name + '"'
    if isinstance(pmember, str):
        buf += ' -principal "' + pmember + '"'
    if isinstance(member, str):
        buf += ' -members "' + member + '"'
    _add_to_tracking('zone', input_d, el, wl, cli=buf)


def _zone_remove_mem(input_d):
    """Remove zone members. See _invalid_action() for parameter descriptions"""
    global _pending_flag

    el, wl = list(), list()
    name, member, fab_obj, zone_obj = input_d['zone_d']['Name'], input_d['zone_d']['Member'], input_d['fab_obj'], None
    pmember = input_d['zone_d']['Principal Member']

    # Validate the parameters
    if pmember is not None:
        el.append('Principal members not supported in standard zone.')
    elif fab_obj is not None:
        zone_obj = fab_obj.r_zone_obj(name)
        if zone_obj is not None:
            if zone_obj.r_is_peer():
                el.append('Zone type mismatch. ' + name + ' is a peer zone.')
            elif member not in zone_obj.r_members():
                wl.append(member + ' is not a member of ' + name + '.')

    # Remove the members
    if len(el) == 0 and zone_obj is not None:
        zone_obj.s_del_member(member)
        _pending_flag = True

    _add_to_tracking('zone', input_d, el, wl, cli='zoneremove "' + name + '", ' + member)


def _zone_purge(input_d):
    """Purges a zone. See _invalid_action() for parameters"""
    el, wl = list(), list()
    name, fab_obj = input_d['zone_d']['Name'], input_d['fab_obj']

    if fab_obj is not None:
        zone_obj = fab_obj.r_zone_obj(name)
        if zone_obj is None:
            wl.append('Zone ' + name + ' does not exist.')
            _add_to_tracking('zone', input_d, el, wl)
        else:
            zone = zone_obj.r_obj_key()
            # Remove the zone from every zone configuration that it's a member of
            for zonecfg_obj in obj_convert.obj_extract(zone_obj, 'ZoneCfgObj'):
                zonecfg_obj.s_del_member(zone)
            _zone_delete(input_d)


def _zone_purge_m(input_d):
    """Purges zones based on a regex or wild card match. See _invalid_action() for parameters"""
    name = input_d['zone_d']['Name']
    for zone in gen_util.match_str(input_d['search_d']['zone_l'], name, stype=input_d['zone_d']['Match']):
        input_d['zone_d']['Name'] = zone
        _zone_purge(input_d)
    input_d['zone_d']['Name'] = name


def _zone_full_purge(input_d):
    """Full purge of a zone. See _invalid_action() for parameters"""
    el, wl = list(), list()
    name, fab_obj = input_d['zone_d']['Name'], input_d['fab_obj']
    if fab_obj is not None:

        # Make sure the zone exists
        zone_obj = fab_obj.r_zone_obj(name)
        if zone_obj is None:
            buf = 'Zone ' + name + ' does not exist.'
            if not gen_util.is_valid_zone_name(name):
                buf += ' Did you intend to set a match type in the "Match" column?'
            wl.append(buf)
            _add_to_tracking('zone', input_d, el, wl)

        else:  # The zone exists
            zonecfg_l = obj_convert.obj_extract(zone_obj, 'ZoneCfgObj')
            mem_l = zone_obj.r_members() + zone_obj.r_pmembers()
            _zone_purge(input_d)

            # Delete all aliases not used in other zones
            for mem in mem_l:
                alias_obj = fab_obj.r_alias_obj(mem)
                if alias_obj is not None:  # The member could be a d,i or WWN
                    if len(obj_convert.obj_extract(alias_obj, 'ZoneObj')) == 0:  # If it's not used elsewhere
                        input_d['zone_d']['Name'] = mem
                        _alias_delete(input_d)

            # Delete all zone configurations that are empty as a result of purging this zone
            for zonecfg_obj in [obj for obj in zonecfg_l if len(obj.r_members()) == 0]:
                input_d['zone_d']['Name'] = zonecfg_obj.r_obj_key()
                _zonecfg_delete(input_d)

    input_d['zone_d']['Name'] = name


def _zone_full_purge_m(input_d):
    """Full purge zones based on a regex or wild card match. See _invalid_action() for parameters"""
    name = input_d['zone_d']['Name']
    for zone in gen_util.match_str(input_d['search_d']['zone_l'], name, stype=input_d['zone_d']['Match']):
        input_d['zone_d']['Name'] = zone
        _zone_full_purge(input_d)
    input_d['zone_d']['Name'] = name


def _zonecfg_create(input_d):
    """Create a zone configuration. See _invalid_action() for parameter descriptions"""
    global _pending_flag

    el, wl = list(), list()
    name, member, fab_obj = input_d['zone_d']['Name'], input_d['zone_d']['Member'], input_d['fab_obj']
    pmember = input_d['zone_d']['Principal Member']

    # If it's a previous action, members are being added
    if input_d['zone_d']['name_c']:
        return _zonecfg_add_mem(input_d)

    # Validate the input
    if pmember is not None:
        el.append('Principal members not supported in zone configuration.')
    if fab_obj is not None:
        zonecfg_obj = fab_obj.r_zone_obj(name)
        if zonecfg_obj is not None:
            el.append('Zone configuration already exists.')
    if member is None:
        if input_d['cli_in']:
            buf = 'When generating CLI, there must be at least one member in the row where the zone configuration is '\
                  'created.'
            el.append(buf)
    elif fab_obj is not None and fab_obj.r_zone_obj(member) is None:
        el.append(str(member) + ' does not exist.')
    
    if len(el) == 0 and fab_obj is not None:
        fab_obj.s_add_zonecfg(name, member)
        _pending_flag = True

    # Add the CLI and tracking
    buf = 'cfgcreate "' + name + '"'
    if isinstance(member, str):
        buf += ' "' + member + '"'
    _add_to_tracking('zone_cfg', input_d, el, wl, cli='cfgcreate "' + name + '", "' + member + '"')


def _zonecfg_copy(input_d):
    """Copy a zone configuration. See _invalid_action() for parameter descriptions"""
    el, wl = list(), list()
    name, member, fab_obj = input_d['zone_d']['Name'], input_d['zone_d']['Member'], input_d['fab_obj']
    pmember = input_d['zone_d']['Principal Member']

    # Make sure it's a valid zone configuration definition
    if pmember is not None:  # Principal members are not supported with zone_cfg copy
        el.append('Principal members not supported in zone_cfg copy.')
    elif not gen_util.is_valid_zone_name(member):  # Is it a valid zone configuration name?
        el.append('Invalid zone configuration name, ' + member + '.')
    elif fab_obj is not None:
        zonecfg_obj = fab_obj.r_zonecfg_obj(name)
        if zonecfg_obj is None:
            el.append('Zone configuration ' + name + ' does not exists.')
        else:
            copy_zonecfg_obj = fab_obj.r_zonecfg_obj(member)
            if copy_zonecfg_obj is not None:
                el.append('Zone configuration ' + member + ' already exists.')
            else:  # Create the zone and add the members
                no_cli = input_d.get('no_cli', False)
                input_d['no_cli'] = True
                input_d['zone_d']['Name'] = member
                mem_l = zonecfg_obj.r_members()
                input_d['zone_d']['Member'] = None if len(mem_l) == 0 else mem_l.pop(0)
                _zonecfg_create(input_d)
                input_d['zone_d']['Name'] = name
                for mem in mem_l:
                    input_d['zone_d']['Member'] = mem
                    _zonecfg_add_mem(input_d)

                # Set input_d back to the original state
                input_d['no_cli'] = no_cli
                input_d['zone_d']['Member'] = member
                input_d['zone_d']['Name'] = name

    _add_to_tracking('zone', input_d, el, wl, cli='zoneobjectcopy "' + name + '", "' + member + '"')


def _zonecfg_delete(input_d):
    """Delete a zone config. See _invalid_action() for parameter descriptions"""
    global _pending_flag

    el, wl = list(), list()
    name, fab_obj = input_d['zone_d']['Name'], input_d['fab_obj']

    # Validate - Make sure the zone configuration exists and that it's not the effective zone.
    if fab_obj is not None:
        zonecfg_obj = fab_obj.r_zonecfg_obj(name)
        if zonecfg_obj is None:
            wl.append(name + ' does not exist.')
        else:
            fab_obj.s_del_zonecfg(name)
            _pending_flag = True

    _add_to_tracking('zone_cfg', input_d, el, wl, cli='cfgdelete "' + name + '"')


def _zonecfg_add_mem(input_d):
    """Add zone config members. See _invalid_action() for parameter descriptions"""
    global _pending_flag

    el, wl = list(), list()
    name, member, fab_obj = input_d['zone_d']['Name'], input_d['zone_d']['Member'], input_d['fab_obj']

    if fab_obj is not None:
        zonecfg_obj = fab_obj.r_zonecfg_obj(name)
        if zonecfg_obj is None:
            el.append('Zone configuration ' + name + ' does not exist.')
        else:
            zonecfg_obj.s_add_member(member)
            _pending_flag = True

    _add_to_tracking('zone_cfg', input_d, el, wl, cli='cfgadd "' + name + '", "' + member + '"')


def _zonecfg_remove_mem(input_d):
    """Remove zone config members. See _invalid_action() for parameter descriptions"""
    global _pending_flag, _cli_l

    el, wl = list(), list()
    name, member, fab_obj = input_d['zone_d']['Name'], input_d['zone_d']['Member'], input_d['fab_obj']

    if fab_obj is not None:
        zonecfg_obj = fab_obj.r_zonecfg_obj(name)
        if zonecfg_obj is None:
            el.append('The zone configuration, ' + name + ' does not exist.')
        elif member in zonecfg_obj.r_members():
            zonecfg_obj.s_del_member(member)
            _pending_flag = True
        else:
            wl.append(input_d['zone_d']['Member'] + ' is not a member of ' + name + '.')

    _add_to_tracking('zone_cfg', input_d, el, wl, cli='cfgremove "' + name + '", "' + member + '"')


def _zonecfg_full_purge(input_d):
    """Purges a zone configuration. See _invalid_action() for parameters"""
    global _pending_flag

    el, name, fab_obj = list(), input_d['zone_d']['Name'], input_d['fab_obj']

    if fab_obj is not None:
        zone_cfg_obj = fab_obj.r_zonecfg_obj(name)
        if zone_cfg_obj is None:
            el.append('Zone configuration ' + str(name) + ' does not exist.')
        else:
            mem_l = zone_cfg_obj.r_members()
            _zonecfg_delete(input_d)
            _set_purge('zone_cfg', name)
            for mem in [m for m in mem_l if len(obj_convert.obj_extract(fab_obj.r_zone_obj(m), 'ZoneCfgObj')) == 0]:
                input_d['zone_d']['Name'] = mem
                _zone_full_purge(input_d)

    input_d['zone_d']['Name'] = name
    _add_to_tracking('zone_cfg', input_d, el, None)


def _comment(input_d):
    """Inserts comments only in CLI file"""
    _add_to_tracking('comment', input_d, None, None, cli='')


def _zonecfg_full_purge_m(input_d):
    """Performs a full purge of zone configurations based on a regex or wild card match. See _invalid_action()"""
    name = input_d['zone_d']['Name']
    for zonecfg in gen_util.match_str(input_d['search_d']['zonecfg_l'], name, stype=input_d['zone_d']['Match']):
        input_d['zone_d']['Name'] = zonecfg
        _zonecfg_full_purge(input_d)
    input_d['zone_d']['Name'] = name


"""_zone_action_d:

Zone_Object (dict):
    Action (dict):
        Match (dict):
            a (key): Pointer to the function to call to process this action.
            ? (key): I made "Match" a dictionary so that I can add other keys in the future. At this time, "a" is the
                     only key in this dictionary. 
"""
_zone_action_d = dict(
    comment=dict(a=_comment),
    alias=dict(
        create=dict(
            exact=dict(a=_alias_create),
        ),
        add_mem=dict(
            exact=dict(a=_alias_add_mem),
        ),
        copy=dict(
            exact=dict(a=_alias_copy),
        ),
        delete=dict(
            exact=dict(a=_alias_delete),
            wild=dict(a=_alias_delete_m),
            regex_m=dict(a=_alias_delete_m),
            regex_s=dict(a=_alias_delete_m),
        ),
        remove_mem=dict(
            exact=dict(a=_alias_remove_mem),
        ),
        purge=dict(
            exact=dict(a=_alias_purge),
            wild=dict(a=_alias_purge_m),
            regex_m=dict(a=_alias_purge_m),
            regex_s=dict(a=_alias_purge_m),
        ),
        full_purge=dict(
            exact=dict(a=_alias_full_purge),
            wild=dict(a=_alias_full_purge_m),
            regex_m=dict(a=_alias_full_purge_m),
            regex_s=dict(a=_alias_full_purge_m),
        ),
        ignore=dict(
            exact=dict(a=_alias_ignore),
            wild=dict(a=_alias_ignore_m),
            regex_m=dict(a=_alias_ignore_m),
            regex_s=dict(a=_alias_ignore_m),
        ),
    ),
    peer_zone=dict(
        create=dict(
            exact=dict(a=_peer_zone_create),
        ),
        copy=dict(
            exact=dict(a=_zone_copy),
        ),
        add_mem=dict(
            exact=dict(a=_zone_add_mem),
        ),
        delete=dict(
            exact=dict(a=_zone_delete),
            wild=dict(a=_zone_delete_m),
            regex_m=dict(a=_zone_delete_m),
            regex_s=dict(a=_zone_delete_m),
        ),
        remove_mem=dict(
            exact=dict(a=_peer_zone_remove_mem),
        ),
        purge=dict(
            exact=dict(a=_zone_purge),
            wild=dict(a=_zone_purge_m),
            regex_m=dict(a=_zone_purge_m),
            regex_s=dict(a=_zone_purge_m),
        ),
        full_purge=dict(
            exact=dict(a=_zone_full_purge),
            wild=dict(a=_zone_full_purge_m),
            regex_m=dict(a=_zone_full_purge_m),
            regex_s=dict(a=_zone_full_purge_m),
        ),
    ),
    zone=dict(
        create=dict(
            exact=dict(a=_zone_create),
        ),
        copy=dict(
            exact=dict(a=_zone_copy),
        ),
        add_mem=dict(
            exact=dict(a=_zone_add_mem),
        ),
        delete=dict(
            exact=dict(a=_zone_delete),
            wild=dict(a=_zone_delete_m),
            regex_m=dict(a=_zone_delete_m),
            regex_s=dict(a=_zone_delete_m),
        ),
        remove_mem=dict(
            exact=dict(a=_zone_remove_mem),
        ),
        purge=dict(
            exact=dict(a=_zone_purge),
            wild=dict(a=_zone_purge_m),
            regex_m=dict(a=_zone_purge_m),
            regex_s=dict(a=_zone_purge_m),
        ),
        full_purge=dict(
            exact=dict(a=_zone_full_purge),
            wild=dict(a=_zone_full_purge_m),
            regex_m=dict(a=_zone_full_purge_m),
            regex_s=dict(a=_zone_full_purge_m),
        ),
    ),
    zone_cfg=dict(
        create=dict(
            exact=dict(a=_zonecfg_create),
        ),
        copy=dict(
            exact=dict(a=_zonecfg_copy),
        ),
        add_mem=dict(
            exact=dict(a=_zonecfg_add_mem),
        ),
        delete=dict(
            exact=dict(a=_zonecfg_delete),
        ),
        full_purge=dict(
            exact=dict(a=_zonecfg_full_purge),
            wild=dict(a=_zonecfg_full_purge_m),
            regex_m=dict(a=_zonecfg_full_purge_m),
            regex_s=dict(a=_zonecfg_full_purge_m),
        ),
        remove_mem=dict(
            exact=dict(a=_zonecfg_remove_mem),
        ),
    ),
)


def _parse_zone_workbook(al):
    """Parse the 'zone' worksheet in the zone workbook into a list of dictionaries as follows:

    +---------------+-------+-------------------------------------------------------------------+
    | Key           | Type  | Description                                                       |
    +===============+=======+===================================================================+
    | row           | int   | Excel workbook row number. Used for error reporting               |
    +---------------+-------+-------------------------------------------------------------------+
    | zone_obj      | str   | Value in "Zone_Object" column                                     |
    +---------------+-------+-------------------------------------------------------------------+
    | zone_obj_c    | bool  | If True, the Zone_Object is the same as a previous zone object.   |
    +---------------+-------+-------------------------------------------------------------------+
    | action        | str   | Value in "Action" column                                          |
    +---------------+-------+-------------------------------------------------------------------+
    | action_c      | bool  | If True, the action is the same as a previous action              |
    +---------------+-------+-------------------------------------------------------------------+
    | name          | str   | Value in "Name" column                                            |
    +---------------+-------+-------------------------------------------------------------------+
    | name_c        | bool  | If True, the name is the same as the previous name.               |
    +---------------+-------+-------------------------------------------------------------------+
    | match         | str   | Cell contents in "Match"                                          |
    +---------------+-------+-------------------------------------------------------------------+
    | member        | str   | Cell contents in "Member"                                         |
    +---------------+-------+-------------------------------------------------------------------+
    | pmember       | str   | Cell contents of "Principal Member"                               |
    +---------------+-------+-------------------------------------------------------------------+

    :return el: List of error messages.
    :rtype el: list
    :return zone_lists_d: Dictionary as noted in the description
    :rtype zone_lists_d: dict
    """
    global _pertinent_headers

    el, rl = list(), list()

    previous_key_d = dict(Zone_Object='zone_obj_c', Action='action_c', Name='name_c')
    previous_d = collections.OrderedDict(Zone_Object=None, Action=None, Name=None)  # Keep track of the previous value

    # Find the headers
    if len(al) < 2:
        el.append('Empty zone worksheet. Nothing to process')
    hdr_d = excel_util.find_headers(al[0], hdr_l=_pertinent_headers, warn=False)
    for key in hdr_d.keys():
        if hdr_d.get(key) is None:
            el.append('Missing column "' + str(key) + '" in zone workbook.')

    # Keeping track of the row is for error reporting purposes.
    for row in range(1, len(al)):  # Starting from the row past the header.
        if isinstance(al[row][hdr_d['Zone_Object']], str) and al[row][hdr_d['Zone_Object']] == 'comment':
            rl.append(dict(Zone_Object='comment', Comments=al[row][hdr_d['Comments']], row=row+1))
            continue
        try:
            for col in hdr_d.values():  # It's a blank line if all cells are None
                if al[row][col] is not None:
                    raise Found
        except Found:
            d = dict(row=row+1)
            for k0, k1 in previous_key_d.items():
                d.update({k1: False})
            for key in _pertinent_headers:
                val = al[row][hdr_d[key]]
                if key == 'Match' and val is None:
                    val = 'exact'
                if key in previous_d:
                    if val is None:
                        val = previous_d[key]
                        if val is None:
                            el.append('Missing required key, ' + key + ' at row ' + str(row+1))
                        else:
                            temp_key = previous_key_d.get(key)
                            if isinstance(temp_key, str):
                                d[temp_key] = True
                    else:
                        previous_d[key] = val
                        # Once a required key is found, all subsequent keys are required
                        clear_flag = False
                        for p_key in previous_d.keys():
                            if clear_flag:
                                previous_d[p_key] = None
                            if p_key == key:
                                clear_flag = True
                d.update({key: val})
            if isinstance(d, dict):
                rl.append(d)

    return el, rl


def _get_fabric(args_d):
    """Returns a login session and a fabric object with an initial data capture

    :param args_d: Input arguments. See _input_d for details.
    :type args_d: dict
    :return session: Session object returned from brcdapi.brcdapi_auth.login(). None if file is specified
    :rtype session: dict, None
    :return fab_obj: Fabric object as read from the input file, -i, or from reading the fabric information from the API
    :rtype fab_obj: brcddb.classes.fabric.FabricObj, None
    """
    global _zone_kpis

    # Create a project
    proj_obj = brcddb_project.new('zone_config', datetime.datetime.now().strftime('%d %b %Y %H:%M:%S'))
    proj_obj.s_python_version(sys.version)
    proj_obj.s_description('zone_config')

    # Create an empty test fabric if there aren't any login credentials.
    for key in ('id', 'pw', 'ip'):
        if args_d.get(key) is None:
            proj_obj.s_add_fabric('test_fabric')
            return None, proj_obj.r_fabric_obj('test_fabric')

    # Login
    session = api_int.login(args_d['id'], args_d['pw'], args_d['ip'], args_d['s'], proj_obj)
    if not fos_auth.is_error(session):
        # Get some basic zoning information
        try:
            if not api_int.get_batch(session, proj_obj, _zone_kpis, args_d['fid']):
                return None, None  # api_int.get_batch() logs a detailed error message
            fab_obj_l = brcddb_project.fab_obj_for_fid(proj_obj, args_d['fid'])
            if len(fab_obj_l) == 1:
                return session, fab_obj_l[0]
            brcdapi_log.log('Fabric ID (FID), ' + str(args_d['fid']) + ', not found.', echo=True)
        except brcdapi_util.VirtualFabricIdError:
            brcdapi_log.log('Software error. Search the log for "Invalid FID" for details.', echo=True)
        except FOSError:
            brcdapi_log.log('Unexpected response from FOS. See previous messages.')
        api_int.logout(session)

    return None, None


def _item_desc(fab_obj, key, item_name):
    """Returns a description for members in the _tracking_d table for alias. Used in _summary_report()

    :param key: The key into _tracking_d
    :type key: string, key
    :param item_name: Zone configuration name, zone name, alias name, WWN, or d,i
    :type item_name: str
    :return: If key == 'alias': Description of alias, wwn, or d,i. Otherwise, just the item_name
    :rtype: str
    """
    r_buf, desc_l = item_name, list()
    if key == 'alias':
        if gen_util.is_di(item_name):
            buf = brcddb_port.port_best_desc(fab_obj.r_port_object_for_di(item_name))
            if len(buf) > 0:
                desc_l.append(buf)
        elif gen_util.is_wwn(item_name, full_check=True):
            buf = brcddb_login.login_best_port_desc(fab_obj.r_login_obj(item_name))
            if len(buf) > 0:
                desc_l.append(buf)
        # It must be an alias
        else:
            alias_obj = fab_obj.r_alias_obj(item_name)
            if alias_obj is not None:
                for mem in alias_obj.r_members():
                    buf = brcddb_login.login_best_port_desc(fab_obj.r_login_obj(mem))
                    if len(buf) > 0:
                        desc_l.append(buf)
        if len(desc_l) > 0:
            r_buf += ' (' + '; '.join(desc_l) + ') '

    return r_buf


def _summary_report(fab_obj, args_d, saved, cli_el):
    """ Print any wrap up messages to the console and log

    :param fab_obj: Fabric object
    :type fab_obj: None, brcddb.classes.fabric.FabricObj
    :param args_d: Input arguments. See _input_d for details.
    :type args_d: dict
    :param saved: If True, the zoning database was saved to the switch.
    :type saved: bool
    :param cli_el: Error messages from _build_cli_file (which are from brcdapi_file.write_file)
    :type cli_el: list
    """
    global _tracking_d, _tracking_hdr_d, _P1_MAX

    error_count = warn_count = 0

    # CLI
    summary_l = ['', '**CLI File Update Errors**']
    if len(cli_el) == 0:
        summary_l.append('None')
    else:
        summary_l.extend(cli_el)

    summary_l.extend(['', '**Error & Warning Detail**'])
    for key, hdr in _tracking_hdr_d.items():
        found = False
        summary_l.extend(['', '*' + hdr + '*'])
        for name, d in _tracking_d[key].items():
            for subkey, buf_l in collections.OrderedDict(ERROR=d['error_l'], WARNING=d['warning_l']).items():
                for buf in buf_l:
                    desc = _item_desc(fab_obj, key, name)
                    summary_l.append(subkey + ': ' + desc + ': ' + buf + _reference_rows(key, name))
                    found = True
                    if subkey == 'ERROR':
                        error_count += 1
                    elif subkey == 'WARNING':
                        warn_count += 1
        if not found:
            summary_l.append('None')

    # Zone Purges
    summary_l.extend(gen_util.format_text([dict(p1_max=_P1_MAX), dict(p1=''), dict(p1='**Purge Faults**'),]))
    purge_msg_l = [
        dict(p1=''),
        dict(
            p1='This is a list of zone members that remained in zones that were affected by an alias full purge but '
               'the zone was not purged because there were remaining members that were not in the ignore list. The '
               'zone is followed by those members. It was done this way for easy copy and paste into an ignore action '
               'in a zone configuration worksheet. Details are in the "Error & Warning Detail" section.'),
        dict(p1=''),
        dict(
            p1='The intent of the "ignore" action is to simplify purging zones when large or multiple storage arrays '
               'are being decommissioned. For a small number of zones, it may be easier to explicitly purge the '
               'zones.'),
    ]
    temp_l = list()  # Messages to add to purge_msg_l
    for zone, track_d in _tracking_d['zone'].items():
        if track_d.get('purge', False) and len(track_d['purge_l']) != 0:
            temp_l.extend([dict(p1=''), dict(p1='*' + zone + '*')] + [dict(p1=m) for m in track_d['purge_l']])
    temp_l.extend(_tracking_d['general']['purge']['error_l'] + _tracking_d['general']['purge']['warning_l'])
    if len(temp_l) > 0:
        summary_l.extend(gen_util.format_text(purge_msg_l + temp_l))
    else:
        summary_l.append('None')

    # Add a summary with error count, warning count, and fabric name
    summary_l.extend(['', '**Summary**', '', 'Errors:   ' + str(error_count), 'Warnings: ' + str(warn_count), ''])
    if args_d['i']:
        summary_l.append('Working from project file: ' + args_d['i'])
    summary_l.append('Fabric: ' + brcddb_fabric.best_fab_name(fab_obj, wwn=True, fid=True))

    # Add the disposition of the zone configuration to the summary
    if saved:
        summary_l.append('Zone changes saved.')
    elif _pending_flag:
        buf = 'Pending zone changes not saved.'
        if not args_d['save'] and not isinstance(args_d['a'], str):
            buf += ' Use -a or -save to save changes.'
        summary_l.append(buf)
    else:
        buf = 'No changes to save.'
        if not args_d['save'] and not isinstance(args_d['a'], str):
            buf += ' Use -a or -save to save changes.'
        summary_l.append(buf)

    for subkey, d in _tracking_d['general'].items():
        if subkey == 'purge':  # purge is already processed in the Purge subsection
            continue
        if len(d['error_l']) > 0:
            summary_l.extend(['', '*' + subkey + ' Errors *'])
            summary_l.extend(d['error_l'])
            summary_l.append('')
        if len(d['warning_l']) > 0:
            summary_l.extend(['', '*' + subkey + ' Warnings *'])
            summary_l.extend(d['warning_l'])
            summary_l.append('')

    brcdapi_log.log(summary_l, echo=True)


def pseudo_main(args_d, fab_obj, zone_wb_l):
    """Basically the main().

    :param args_d: Input arguments. See _input_d for details.
    :type args_d: dict
    :param fab_obj: Fabric object
    :type fab_obj: None, brcddb.classes.fabric.FabricObj
    :param zone_wb_l: Output of _parse_zone_workbook() - List of actions to take
    :type zone_wb_l: list
    :return: Exit code
    :rtype: int
    """
    global _zone_action_d, _pending_flag, _debug, _eff_zone_l, _eff_mem_l, _tracking_d, _tracking_hdr_d

    ec, debug_i, saved, error_flag, purge_fail_d = brcddb_common.EXIT_STATUS_OK, 0, False, False, dict()
    el = _tracking_d['general']['process']['error_l']
    session, zone_d, action, proj_obj, eff_zonecfg = None, None, None, None, None

    # Get the project object
    if fab_obj is None:
        session, fab_obj = _get_fabric(args_d)
    if fab_obj is not None:
        proj_obj = fab_obj.r_project_obj()
        # Perform all pre-processing (build cross-references, add search terms, and build effective zone tables)
        brcddb_project.build_xref(proj_obj)
        brcddb_project.add_custom_search_terms(proj_obj)
        for zone_obj in fab_obj.r_eff_zone_objects():
            _eff_zone_l.append(zone_obj.r_obj_key())
            _eff_mem_l.extend(zone_obj.r_members() + zone_obj.r_pmembers())
    if proj_obj is None:
        proj_obj = brcddb_project.new('zone_config', datetime.datetime.now().strftime('%d %b %Y %H:%M:%S'))
        proj_obj.s_python_version(sys.version)
        proj_obj.s_description('Created by zone_config.py')

    # Fill in search_d (lists of all items to use where Match is supported). Since its obvious which list to act on in
    # each function that operates on a match, I could have just used fab_obj.r_xxx_keys(). I doubt I will ever apply
    # search terms to anything other than the full list, but doing this way gives me the option to make a global change
    # in what to search for.
    search_d = dict(wwn_l=list(),
                    alias_l=list(),
                    zone_l=list(),
                    zonecfg_l=list(),
                    eff_alias_d=dict(),
                    eff_zone_d=dict(),
                    eff_zonecfg_obj=None)
    if fab_obj is not None:
        eff_zonecfg_obj = fab_obj.r_defined_eff_zonecfg_obj()
        search_d['wwn_l'] = fab_obj.r_login_keys()
        search_d['alias_l'] = fab_obj.r_alias_keys()
        search_d['zone_l'] = fab_obj.r_zone_keys()
        search_d['zonecfg_l'] = fab_obj.r_zonecfg_keys()
        search_d['eff_zonecfg_obj'] = eff_zonecfg_obj
        if eff_zonecfg_obj is not None:
            for zone_obj in eff_zonecfg_obj.r_zone_objects():
                for alias in zone_obj.r_members() + zone_obj.r_pmembers():
                    search_d['eff_alias_d'][alias] = True
                search_d['eff_zone_d'][zone_obj.r_obj_key()] = True

    try:
        # Process each action in zone_wb_l
        for zone_d in zone_wb_l:
            if _debug:
                brcdapi_log.log(['debug_i: ' + str(debug_i), pprint.pformat(zone_d)], echo=True)
                # if debug_i == 1:
                #     brcdapi_log.log('TP_100', echo=True)
                debug_i += 1
            try:
                action = _zone_action_d[zone_d['Zone_Object']]['a']
            except KeyError:
                try:
                    action = _zone_action_d[zone_d['Zone_Object']][zone_d['Action']][zone_d['Match']]['a']
                except KeyError:
                    action = _invalid_action
            action(dict(fab_obj=fab_obj,
                        zone_d=zone_d,
                        search_d=search_d,
                        cli_in=False if args_d['cli'] is None else True))

        # Finish purges
        _finish_purges(fab_obj)

        # Validate the zone database
        _validation_check(args_d, fab_obj)

        # Do we have any errors? If strict, treat all warnings as errors
        second_key = 'warning_l' if args_d.get('strict', False) else 'error_l'
        for name_d in [_tracking_d[k] for k in _tracking_hdr_d.keys()]:
            for item_d in name_d.values():
                if len(item_d.get('error_l', list())) + len(item_d.get(second_key, list())) > 0:
                    error_flag = True
                    break

        # Save the zone changes
        if not error_flag and session is not None:
            if _pending_flag:
                if args_d['save'] or isinstance(args_d['a'], str):
                    obj = api_zone.replace_zoning(session, fab_obj, args_d['fid'], args_d['a'])
                    if fos_auth.is_error(obj):
                        el.extend(['Failed to replace zoning:', fos_auth.formatted_error_msg(obj)])
                        ec = brcddb_common.EXIT_STATUS_ERROR
                    else:
                        _pending_flag, saved = False, True
                    _cli_l.extend(['', 'cfgsave -f'])
            elif isinstance(args_d['a'], str):
                obj = api_zone.enable_zonecfg(session, args_d['fid'], args_d['a'])
                if fos_auth.is_error(obj):
                    brcdapi_zone.abort(session, args_d['fid'])
                    el.extend(['Failed to enable zone config: ' + args_d['a'],
                               'FOS error is:',
                               fos_auth.formatted_error_msg(obj)])
                    ec = brcddb_common.EXIT_STATUS_ERROR
                else:
                    saved = True
                _cli_l.extend(['', 'cfgenable "' + args_d['a'] + '" -f'])

    except BaseException as e:
        el.extend(['Software error.', str(type(e)) + ': ' + str(e), 'zone_d:', pprint.pformat(zone_d)])
        ec = brcddb_common.EXIT_STATUS_ERROR
        try:
            brcdapi_zone.abort(session, args_d['fid'])
        except BaseException as e:
            el.append('Software error aborting zone DB updates while processing a previous software error.')
            el.extend([str(type(e)) + ': ' + str(e), 'zone_d:', pprint.pformat(zone_d)])

    # Log out
    if session is not None:
        brcdapi_log.log('Logging out', echo=True)
        obj = brcdapi_rest.logout(session)
        if fos_auth.is_error(obj):
            el.extend(['Logout failed', fos_auth.formatted_error_msg(obj)])
            ec = brcddb_common.EXIT_STATUS_ERROR

    # Write out the CLI file and summaries
    _summary_report(fab_obj, args_d, saved, _build_cli_file(args_d['cli'], args_d['fid']))

    return ec


def _get_input():
    """Retrieves the command line input, reads the input Workbook, and validates the input

    :return ec: Error code. See brcddb_common.EXIT_* for details
    :rtype ec: int
    """
    global __version__, _input_d, _debug, _eh_l

    ec, error_l, zone_wb_l, proj_obj, fab_obj = brcddb_common.EXIT_STATUS_OK, list(), list(), None, None
    e_buf = ' **ERROR**: Missing required input parameter'
    w_buf = 'Ignored because -i was specified.'
    args_help_d = dict(ip='', id='', pw='', s='', fid='', i='', wwn='', z='', sheet='')

    # Get command line input
    buf = 'Creates, deletes, and modifies zone objects from a workbook. See zone_sample.xlsx for details and ' \
          'examples. The purge and full purge options simplify migrating or decommissioning storage arrays and ' \
          'servers or simple zone cleanup.'
    try:
        args_d = gen_util.get_input(buf, _input_d)
    except TypeError:
        return brcddb_common.EXIT_STATUS_INPUT_ERROR  # gen_util.get_input() already posted the error message.

    # Get full file names
    args_d['i'] = brcdapi_file.full_file_name(args_d['i'], '.json')
    args_d['cli'] = brcdapi_file.full_file_name(args_d['cli'], '.txt', dot=True)

    # Set up logging
    if args_d['d']:
        _debug = True
        brcdapi_rest.verbose_debug(True)
    brcdapi_log.open_log(
        folder=args_d['log'],
        suppress=args_d['sup'],
        no_log=args_d['nl'],
        version_d=brcdapi_util.get_import_modules()
    )

    # Extended help
    if args_d['eh']:
        brcdapi_log.log(gen_util.format_text(_eh_l), echo=True)
        return brcddb_common.EXIT_STATUS_INPUT_ERROR

    # If a file name was specified, read the project object from the file.
    if isinstance(args_d['i'], str):
        try:
            proj_obj = brcddb_project.read_from(args_d['i'])
            if proj_obj is None:
                args_help_d['i'] += ' **ERROR** ' if len(args_help_d['i']) == 0 else ', '
                args_help_d['i'] += 'Unknown error. Typical of a non-JSON formatted project file.'
                ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
            elif not args_d['scan']:
                if args_d['wwn'] is None:
                    args_help_d['wwn'] = e_buf
                    ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
                else:
                    fab_obj = proj_obj.r_fabric_obj(args_d['wwn'])
                    if fab_obj is None:
                        args_help_d['wwn'] = ' **ERROR** Fabric with this WWN not found in ' + args_d['i']
                        ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
        except FileNotFoundError:
            args_help_d['i'] += ' **ERROR** ' if len(args_help_d['i']) == 0 else ', '
            args_help_d['i'] += 'Not found'
            ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
        except FileExistsError:
            args_help_d['i'] += ' **ERROR** ' if len(args_help_d['i']) == 0 else ', '
            args_help_d['i'] += 'A Folder in parameter does not exist'
            ec = brcddb_common.EXIT_STATUS_INPUT_ERROR

    # Input validation
    if not args_d['scan']:

        # Validate the login credentials.
        i, key_l = 0, list()
        for key in ['ip', 'id', 'pw']:
            if args_d['i'] is None:
                if args_d[key] is not None:
                    key_l.append(key)
                    i += 1
            else:
                if args_d[key] is not None:
                    args_help_d[key] = w_buf
        if 0 < i < 3:
            login_e_buf = ' **ERROR** Required when -' + ', -'.join(key_l) + ' is specified'
            for key in ['ip', 'id', 'pw']:
                if args_d[key] is None:
                    args_help_d[key] += login_e_buf
                    ec = brcddb_common.EXIT_STATUS_INPUT_ERROR

        # Is the fid required?
        if args_d['i'] is None and args_d['ip'] is not None and args_d['fid'] is None:
            args_help_d['fid'] = ' **ERROR** Required when -ip is specified.'
            ec = brcddb_common.EXIT_STATUS_INPUT_ERROR

        # Read in the workbook with the zone definitions
        if not isinstance(args_d['z'], str):
            args_help_d['z'] = e_buf
            ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
        if not isinstance(args_d['sheet'], str):
            args_help_d['sheet'] = e_buf
            ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
        if isinstance(args_d['z'], str) and isinstance(args_d['sheet'], str):
            args_z = brcdapi_file.full_file_name(args_d['z'], '.xlsx')
            brcdapi_log.log('Reading ' + args_z, echo=True)
            el, workbook_l = excel_util.read_workbook(args_z, dm=0, sheets=args_d['sheet'], hidden=False)
            if len(el) > 0:
                error_l.extend(el)
                args_help_d['z'] += ' **ERROR** ' + ','.join(el)
                ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
            elif len(workbook_l) != 1:
                args_help_d['sheet'] += ' **ERROR** Worksheet not found.'
                ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
            else:
                el, zone_wb_l = _parse_zone_workbook(workbook_l[0]['al'])
                if len(el) > 0:
                    error_l.extend(el)
                    args_help_d['sheet'] = ' **ERROR** Invalid. See below for details.'
                    ec = brcddb_common.EXIT_STATUS_INPUT_ERROR

    # Command line feedback
    pw_buf = 'None' if args_d['pw'] is None else '****'
    ip_buf = 'None' if args_d['ip'] is None else brcdapi_util.mask_ip_addr(args_d['ip']) + args_help_d['ip']
    ml = [
        '',
        'Script:                   ' + os.path.basename(__file__) + ', ' + __version__,
        'IP address, -ip:          ' + ip_buf,
        'ID, -id:                  ' + str(args_d['id']) + args_help_d['id'],
        'Password, -pw:            ' + pw_buf + args_help_d['pw'],
        'HTTPS, -s:                ' + str(args_d['s']),
        'Fabric ID (FID), -fid:    ' + str(args_d['fid']) + args_help_d['fid'],
        'Input file, -i:           ' + str(args_d['i']) + args_help_d['i'],
        'Fabric WWN, -wwn:         ' + str(args_d['wwn']) + args_help_d['wwn'],
        'Zone workbook, -z:        ' + str(args_d['z']) + args_help_d['z'],
        'Zone worksheet, -sheet:   ' + str(args_d['sheet']) + args_help_d['sheet'],
        'Activate, -a:             ' + str(args_d['a']),
        'Save, -save:              ' + str(args_d['save']),
        'CLI file, -cli:           ' + str(args_d['cli']),
        'Scan, -scan:              ' + str(args_d['scan']),
        'Log, -log:                ' + str(args_d['log']),
        'No log, -nl:              ' + str(args_d['nl']),
        'Debug, -d:                ' + str(args_d['d']),
        'Suppress, -sup:           ' + str(args_d['sup']),
        '',
        ]
    ml.extend(error_l)
    if args_d['scan']:
        ml.extend(['', 'Scan of ' + args_d['i'], '_________________________________________________'])
        ml.extend(brcddb_project.scan(proj_obj, fab_only=False, logical_switch=True))
        ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
    brcdapi_log.log(ml, echo=True)
    
    if isinstance(args_d['i'], str):
        args_d['a'] = False  # We're not connected to a real switch so force the zone configuration activation to False
    return ec if ec != brcddb_common.EXIT_STATUS_OK else pseudo_main(args_d, fab_obj, zone_wb_l)


###################################################################
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
