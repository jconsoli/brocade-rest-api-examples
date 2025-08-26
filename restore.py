#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Copyright 2024, 2025 Consoli Solutions, LLC.  All rights reserved.

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

Restores a switch to a previously captured chassis DB

TODO enable effective zone configuration

**Prominent Data Structures**

A dictionary, local_control_d, is created in pseudo_main() and passed to functions as parameter cd. It is defined as
follows:

+---------------+---------------+-----------------------------------------------------------------------------------+
| Key           | Type          | Description                                                                       |
+===============+===============+===================================================================================+
| session       | dict          | Session object returned from brcdapi.fos_auth.login()                             |
+---------------+---------------+-----------------------------------------------------------------------------------+
| t_proj_obj    | ProjectObj    | Project object for the target chassis                                             |
+---------------+---------------+-----------------------------------------------------------------------------------+
| r_proj_obj    | ProjectObj    | Project object for the restore project                                            |
+---------------+---------------+-----------------------------------------------------------------------------------+
| r_chassis_obj | ChassisObj    | Chassis object for the restore chassis                                            |
+---------------+---------------+-----------------------------------------------------------------------------------+
| r_default_fid | int           | Fabric ID of the default fabric of the restore chassis                            |
+---------------+---------------+-----------------------------------------------------------------------------------+
| act_d         | dict          | See description where _action_l is defined                                        |
+---------------+---------------+-----------------------------------------------------------------------------------+
| fid_map_d     | dict          | See function description for _build_fid_map()                                     |
+---------------+---------------+-----------------------------------------------------------------------------------+
| args_cli      | str           | Not yet implemented. Intended as a file name for CLI commands to restore a        |
|               |               | chassis                                                                           |
+---------------+---------------+-----------------------------------------------------------------------------------+
| summary_d     | dict          | See description below                                                             |
+---------------+---------------+-----------------------------------------------------------------------------------+

A summary of changes is maintained in local_control_d as summary_d. The keys are 'chassis' and the switch names for
each logical switch acted on.

    chassis

    +---------------+---------------+-------------------------------------------------------------------------------+
    | Key           | Type          | Description                                                                   |
    +===============+===============+===============================================================================+
    | Users         | list          | User names added.                                                             |
    +---------------+---------------+-------------------------------------------------------------------------------+
    | VF Enable     | bool          | If True, virtual fabrics was enabled.                                         |
    +---------------+---------------+-------------------------------------------------------------------------------+

    Switch WWN

    +-------------------+---------------+---------------------------------------------------------------------------+
    | Key               | Type          | Description                                                               |
    +===================+===============+===========================================================================+
    | Removed           | bool          | True if the logical switch was removed                                    |
    +-------------------+---------------+---------------------------------------------------------------------------+
    | Added             | bool          | True if the logical switch was added                                      |
    +-------------------+---------------+---------------------------------------------------------------------------+
    | Ports Removed     | int           | Number of ports removed.                                                  |
    +-------------------+---------------+---------------------------------------------------------------------------+
    | Ports Added       | int           | Number of ports added.                                                    |
    +-------------------+---------------+---------------------------------------------------------------------------+
    | Ports Add Fail    | int           | Number of ports that failed to be added.                                  |
    +-------------------+---------------+---------------------------------------------------------------------------+
    | Zone Changes      | bool          | True if zoning changes were made.                                         |
    +-------------------+---------------+---------------------------------------------------------------------------+
    | MAPS Changes      | bool          | True if MAPS changes were made.                                           |
    +-------------------+---------------+---------------------------------------------------------------------------+

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 06 Mar 2024   | Initial Launch                                                                        |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 09 Mar 2024   | Added tip for -scan option. Fixed errors when target switch does not exist.           |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 03 Apr 2024   | Added version numbers of imported libraries.                                          |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.3     | 16 Apr 2024   | Fix: restore was operating on fabrics, not switches.                                  |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.4     | 15 May 2024   | Declared _scan_action_l global in pseudo_main().                                      |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.5     | 16 Jun 2024   | Fixed grammar mistakes in help messages.                                              |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.6     | 29 Oct 2024   | Added more error checking.                                                            |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.7     | 06 Dec 2024   | Fixed spelling mistake in message.                                                    |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.8     | 26 Dec 2024   | Removed unused import. Added SCC policy warning.                                      |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.9     | 12 Apr 2025   | FOS 9.2 updates.                                                                      |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.1.0     | 25 Aug 2025   | Use brcddb.util.util.get_import_modules to dynamically determined imported libraries. |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2024, 2025 Consoli Solutions, LLC'
__date__ = '25 Aug 2025'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.1.0'

import collections
import pprint
import signal
import sys
import os
import datetime
import copy
import base64
import brcdapi.log as brcdapi_log
import brcdapi.fos_auth as fos_auth
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.gen_util as gen_util
import brcdapi.util as brcdapi_util
import brcdapi.file as brcdapi_file
import brcdapi.switch as brcdapi_switch
import brcdapi.port as brcdapi_port
import brcdapi.fos_cli as fos_cli
import brcddb.brcddb_common as brcddb_common
import brcddb.brcddb_project as brcddb_project
import brcddb.brcddb_chassis as brcddb_chassis
import brcddb.brcddb_fabric as brcddb_fabric
import brcddb.brcddb_switch as brcddb_switch
import brcddb.classes.util as class_util
import brcddb.api.interface as api_int
import brcddb.api.zone as api_zone
import brcddb.util.maps as util_maps
import brcddb.util.compare as brcddb_compare

# debug input (for copy and paste into Run->Edit Configurations->script parameters):
# -ip 10.144.72.15 -id admin -pw AdminPassw0rd! -s self -i _capture_2024_01_12_06_30_39/combined -p * -log _logs

_DOC_STRING = False  # Should always be False. Prohibits any code execution. Only useful for building documentation
_DEBUG = False   # When True, prints status to the log and console
# _STAND_ALONE: True: Executes as a standalone module taking input from the command line. False: Does not automatically
# execute. This is useful when importing this module into another module that calls psuedo_main().
_STAND_ALONE = True  # See note above

_input_d = gen_util.parseargs_login_false_d.copy()
_input_d['i'] = dict(
    r=False, d=None,
    h='Required unless using -scan or -eh options. Captured data file from the output of capture.py, combine.py, or '
      'multi_capture.py. ".json" is automatically appended.')
_input_d['wwn'] = dict(
    r=False, d=None,
    h='Optional (required if multiple chassis are in the captured data, -i). WWN of chassis in the input file, -i, to '
      'be restored to the chassis specified with -ip. NOTE: When capturing data from a single chassis, additional '
      'chassis may have been discovered if any of the logical switches were in a fabric. Use the -scan option to '
      'determine all discovered chassis.')
_input_d['p'] = dict(
    r=False, d=None,
    h='Required unless using -scan or -eh options. CSV list of option parameters. This determines what is to be '
      'restored. Use * for all parameters. Invoke with -eh for details.')
_input_d['fm'] = dict(r=False, d=None, h='Optional. FID Map. Re-run with -eh for details.')
_input_d.update(gen_util.parseargs_scan_d.copy())
_input_d.update(gen_util.parseargs_eh_d.copy())
_input_d.update(gen_util.parseargs_log_d.copy())
_input_d.update(gen_util.parseargs_debug_d.copy())

_zonecfg_enable = False
_switch_sum_template_d = collections.OrderedDict()
_switch_sum_template_d['Added'] = False
_switch_sum_template_d['Removed'] = False
_switch_sum_template_d['Ports Removed'] = 0
_switch_sum_template_d['Ports Added'] = 0
_switch_sum_template_d['Ports Add Fail'] = 0
_switch_sum_template_d['Zone Changes'] = False
_switch_sum_template_d['Enabled Zone Config'] = ''
_switch_sum_template_d['MAPS Changes'] = False

_cli_change_flag = False
_DEFAULT_WAIT = 10  # Time to sleep waiting for the CLI and API to sync up
_check_log = ' Check the log for details.'
_MAX_LINE_LEN = 72  # Used to control how long help messages can be.


class FIDMapError(Exception):
    pass


class Found(Exception):
    pass


_data_collect_error_l = list()
_temp_password = 'Passw0rd!'
_basic_capture_kpi_l = [
    # 'running/' + brcdapi_util.bfsw_uri,  Done automatically in brcddb.api.interface.get_chassis()
    'running/' + brcdapi_util.bfs_uri,
    'running/' + brcdapi_util.bfc_sw_uri,
    'running/' + brcdapi_util.bfc_port_uri,
    'running/' + brcdapi_util.bifc_uri,
]
_full_capture_l = _basic_capture_kpi_l.copy()
_all_fos_cli_l = [
    'fos_cli/portcfgshow',
    'fos_cli/portbuffershow',
]

_restore_parameters = dict(
    m='Mandatory. This action is always taken whether specified with -p or not.',
    vfc='Virtual Fabrics Clear. Virtual fabrics will be enabled if necessary; however, virtual fabrics will not be '
        'disabled. Deletes all non-default logical switches. Set all ports in all FIDs, including the default logical '
        'switch, to the default configuration.',
    vfs='Virtual Fabric Switches. Create any logical switch that doesn\'t already exist. Unless specified otherwise '
        'with the -fm option, the FID, DID, fabric name, and switch name will match that of the restore chassis.',
    vfp='Virtual Fabric Ports. Remove any ports that do not belong in the target logical switch. Add any ports not '
        'present that do belong to the logical switch. Typically not used when restoring to a different chassis type.',
    c='Chassis. All chassis settings except virtual fabrics, users, and security features. It does include enabling '
      'FCR but no other FCR configuration settings are available at this time.',
    s='Switch. All logical switch configuration settings except MAPS, user friendly switch name, or the domain ID. '
      'The user friendly name and DID are set with the vfs parameter.',
    p='Port. All port configuration settings except FCR and FCIP. Typically not used when restoring to a different '
      'chassis type.',
    maps='MAPS. All MAPS custom (non-default) rules and policies. Groups are not modified.',
    u='User accounts. Creates non-default users only. Existing user accounts in the target chassis are not deleted and '
      'passwords for existing accounts are not modified.',
    # sec='Security features.',
    # l='Logging. WIP',
    # fcr='Fibre Channel Routing. WIP',
    # ficon='FICON. WIP',
    # fcip='Fibre Channel Over IP. WIP',
    z='Zoning. Restores the zoning configurations for each logical fabric. If "ze" is not specified and a zone '
      'configuration is enabled in the target switch, the active zones and associated aliases will remain unchanged.',
    ze='Zone Enable. Enables the zone configuration that was active in the restore fabric. If "z" is not specified, '
       'this option does nothing. If "e" is specified, the switch enable action occurs first.',
    e='Enable. Enable all the switches and ports in the target switch that were enabled in the restore switch.',
)
_eh = [
    dict(b=('**Overview**', '____________', '')),
    dict(b='The intended purpose is to use previously collected data from a chassis as a template to be applied to a '
           'different chassis. The -p option allows you to selectively chose what parameters to restore. For example, '
           'if all you want to do is copy MAPS policies and rules: -p maps.'),
    dict(b=''),
    dict(b='When using the script input, -i, as a template to create new logical switches, the fabric map, -fm, '
           'allows you to limit the restore to specific logical switches. It also allows you to change the FID, DID, '
           'fabric name, and switch name. '),
    dict(b=''),
    dict(b=('', 'The typical use for this module is to modify a chassis for:', '')),
    dict(b=('A service action replacement', 'An upgrade', 'Reallocation of a SAN resource', 'Template',), p='  * '),
    dict(b=('It may be useful to configure chassis and switches to use as a template and make further modifications '
            'via other modules.', 'The most common use as a template is to distribute MAPS policies'), p='      - '),
    dict(b=('', 'Nomenclature:', '')),
    dict(b='Refers to the reference chassis (chassis being restored from).', p='Restore  '),
    dict(b=''),
    dict(b='Refers to the chassis being rebuilt.', p='Target   '),
    dict(b=('',
            'The intended purpose of this script is primarily to be used as a template either for deploying new or '
            'reallocating resources. It may be desirable therefore to only update certain configuration parameters, '
            'certain FIDs, or to map FIDs on the restore chassis to different FIDs on the target chassis. The options '
            '-p and -fm are used for this purpose.',
            '')),
    dict(b=('A capture must be performed from the restore chassis prior to using this module. It is not necessary to '
            'collect all data; however, keep in mind that whatever data wasn\'t collected can\'t be restored.',
            '',
            '**Theory of Operation**',
            '_______________________',
            '')),
    dict(b=('', 'The general process is:', '')),
    dict(b='Read the input file, -i, for the restore chassis', p='1.  '),
    dict(b='A GET request is issued for each URI associated with \'k\' in the action list.', p='2.  '),
    dict(b='The action list is then processed in the order:', p='3.  '),
    dict(b=('Virtual fabrics',
            'Chassis parameters',
            'User accounts',
            'Logical switches',
            'Add/remove ports to/from logical switches',
            'Configure ports',
            'MAPS',
            'Zoning',
            'Chassis enable',
            'Switch enable',
            'Port enable'),
         p='    - '),
    dict(b=('', 'All non-default users are re-created with default password:')),
    dict(b=(_temp_password, '', 'FID MAP, -fm', '____________', '')),
    dict(b=('This option defines the source data and destination FID for actions specified with -p. Except for the vf '
            'option, only FIDs specified in the FID map are acted on. When vf is included with the -p options, all '
            'non-default FIDs in the target chassis are deleted whether in the FID map or not. Only FIDs defined in '
            'the fid map are acted on. When not specified, the default is to act on all FIDs.',
            '',
            'The operand is a CSV list embedded in a semicolon separated list. When no value is specified, the '
            'value from the restore chassis is used. The values are (by index into the CSV list):',
            '')),
    dict(b='The restore chassis FID.', p='  0  '),
    dict(b='The FID to be created or modified in the target chassis.', p='  1  '),
    dict(b='The fabric name to be defined in the target chassis. Only applicable when vfs is specified with the -p '
           'parameter', p='  2  '),
    dict(b='The switch DID in decimal to be defined in the target chassis. Only applicable when vfs is specified with '
           'the -p parameter', p='  3  '),
    dict(b='The switch name to be defined in the target chassis. Only applicable when vfs is specified with the -p '
           'parameter', p='  4  '),
    dict(b=('',
            'Example 1: Restore FID 1 to the target chassis with the same FID, fabric name DID, and switch name as in '
            'the restore chassis. Restore FID 20 to FID 3. Set the fabric name to match the fabric name of the restore '
            'switch, the DID to 23, and the switch name to switch_23. Also, restore FID 20 to FID 24 but do not set '
            'the fabric name. Set the DID to 24 and the switch name to switch_24.',
            '',
            'Note that "None" is a special name used to indicate that the parameter should not be set while no value '
            'is used to indicate that the parameter should be taken form the restore switch. Not setting the fabric '
            'name is useful when the intent is to merge the logical switch with another fabric that is named.',
            '',
            '-fm 1;20,3,,23,switch_23;20,4,None,24,switch_24',
            '',
            'Example 2: Replicate the switch parameters from FID 1 of the restore chassis to FIDs 3, 5, and 7 of the '
            'target chassis. The typical use case for this is for copying MAPS policies. Note that switch and port '
            'configurations are only modified on the target switch when vf is specified with the -p parameter.',
            '',
            '-fm 1,3;1,5;1,7',
            '',
            'Example 3: Similar to Example 2 but using a range instead of explicit FIDs. Note that if a FID doesn\'t '
            'exist in the target switch it is ignored. Replicate the switch parameters from FID 1 or the restore '
            'chassis to all FIDs in the target chassis except FID 128.',
            '',
            '-fm 1,1-127',
            '',
            '**Exceptions and Important Notes**',
            '__________________________________',
            '')),
    dict(b=('Fabric security policies, such as the SCC policy used in FICON fabrics, is not restored. This is because '
            'logical switches are not necessarily recreated with the same WWN. When using this script as a template, '
            'it is certain that logical switches will have different WWNs. For single switch FICON fabrics, this is '
            'not a problem because the SCC policy is automatically created with WWN of the logical switch. For '
            'cascaded FICON fabrics, use scc_policy.py to create the appropriate SCC policy.',
            'All switch and port configurations are completed before enabling them. Ports are only disabled with "-p '
            'vfc". Port settings that require the port to be offline therefore will only get updated if the port is '
            'disabled.',
            'All errors are reported but otherwise ignored. The intent is to restore as much as possible.',
            'Ports from the previous data capture that do not exist in the target chassis are ignored,',
            'Ports that do not exist in the previous data are left in the default switch.',
            'Some actions require the affected switch or port to be disabled. If vf was not specified, you may need '
            'to disable ports in the target switch.',
            'When the zone database is replaced, z, zones and associated aliases in the effective zone are preserved. '
            'If the zone configuration is enabled, ze, any zone and aliases not in the zone database being restored '
            'are then deleted.',
            'The FID map is built once after the initial data capture. Logical switches added to the target chassis '
            'afterwards are not included in the FID map',),
         p='  * '),
    dict(b=('', '**Parameter, -p, options:**', '______________________________', '', '*       All (full restore)')),
    ]

for _key, _buf in _restore_parameters.items():
    if _key != 'm':
        _eh.append(dict(b=''))
        _eh.append(dict(b=_buf, p=gen_util.pad_string(str(_key), 8, ' ', append=True)))
_eh.append(dict(b=('',
                   'Not responsible for errors. There are too many potential configurations to fully test. Manual '
                   'validation is highly recommended.')))


###################################################################
#
#           Support Methods for Branch Actions
#
###################################################################
def _send_request(session, http_method, key, content, fid=None):
    """Generic method to send requests used by the Branch Actions

    :param session: Session object, or list of session objects, returned from brcdapi.fos_auth.login()
    :type session: dict
    :param http_method: HTTP method. PATCH, POST, ...
    :type http_method: str
    :param key: Reference key into _control_d in slash notation.
    :type key: str
    :param content: Content to send to switch. If content is None or empty, nothing is sent to the switch
    :type content: None, dict, list
    :return: Error messages.
    :rtype: list
    """
    el = list()
    if content is None or len(content) == 0:
        return el
    uri = 'running/' + key
    obj = brcdapi_rest.send_request(session, uri, http_method, {key.split('/').pop(): content}, fid=fid)
    if fos_auth.is_error(obj):
        el.extend(['Error updating chassis URI:', '  ' + uri, 'FOS error:', fos_auth.formatted_error_msg(obj)])

    return el


def _enable_disable_chassis(session, state, e_text):
    """Disables or Enables the chassis

    :param session: Session object, or list of session objects, returned from brcdapi.fos_auth.login()
    :type session: dict
    :param state: If Ture, enable the chassis. Otherwise, disable the chassis
    :type state: bool
    :param e_text: Text to append to error messages
    :type e_text: str
    :return: List of error messages
    :rtype: list
    """
    return _send_request(session, 'PATCH', brcdapi_util.bcc_uri, dict(chassis={'chassis-enabled': state}))


def _fmt_errors(to_format, full=False):
    """Formats the standard inputs to the branch actions for error reporting.

    :param to_format: List of objects to format.
    :type to_format: list, str
    :return: Formatted text in list entries
    :rtype: list
    """
    rl = list()
    for obj in gen_util.convert_to_list(to_format):
        rl.extend(class_util.format_obj(obj, full=full))
    return rl


def _patch_content(r_obj, t_obj, d):
    """ Builds a dictionary with just the differences between the restore object and target object

    :param r_obj: Restore object
    :type r_obj: brcddb.classes.chassis.ChassisObj, brcddb.classes.switch.SwitchObj
    :param t_obj: Restore object
    :type t_obj: brcddb.classes.chassis.ChassisObj, brcddb.classes.switch.SwitchObj
    :param d: Actions to take. This is a dictionary from _control_d
    :type d: dict
    :return: List of error messages as str encountered.
    :rtype: list
    :return content_d: Dictionary differences
    :rtype content_d: dict()
    """
    global _check_log

    el, obj, rd, content_d = list(), None, dict(), dict()
    try:
        key, rw_d = d['k'], d.get('rw')

        # Validate the input
        for obj in (r_obj, t_obj):
            obj_type = str(class_util.get_simple_class_type(obj))
            if obj_type not in ('ChassisObj', 'SwitchObj'):
                el.append('Invalid object type: ' + obj_type + '. ' + d['e'] + '.' + _check_log)
        if type(r_obj) is not type(t_obj):
            el.append('Object types do not match. ' + d['e'] + '.' + _check_log)
        if key is None:
            el.append('Missing k in dictionary for ' + d['e'] + '.' + _check_log)
        if not isinstance(rw_d, dict):
            el.append('rw missing in dictionary for ' + d['e'] + '.' + _check_log)

        # Figure out the differences
        if len(el) == 0:
            for k, method in rw_d.items():
                r_val, t_val = method(r_obj, d['k'], k), method(t_obj, d['k'], k)
                if r_val is not None:
                    if t_val is None or type(t_val) is not type(r_val) or r_val != t_val:
                        content_d.update({k: r_val})

        # Figure out what the return content should be
        if len(content_d) > 0:
            rd.update({key.split('/').pop(): content_d})

    except BaseException as e:
        brcdapi_log.exception(_fmt_errors(['Exception:', e, d, obj, r_obj, t_obj], full=True))
        el.append('Software error. Check the log for details')

    return el, rd


def _post_content(r_obj, d):
    """Creates a copy of the restore object with just values in d['rw']

    :param r_obj: Restore object
    :type r_obj: brcddb.classes.chassis.ChassisObj, brcddb.classes.switch.SwitchObj
    :param d: Actions to take. This is a dictionary from _control_d
    :type d: dict
    :return: List of error messages as str encountered.
    :rtype: list
    :return content_d: Dictionary differences
    :rtype content_d: dict()
    """
    el, rd, content_d = list(), dict(), dict()
    try:
        key, rw_d = d['k'], d.get('rw')

        # Validate the input
        obj_type = str(class_util.get_simple_class_type(r_obj))
        if obj_type not in ('ChassisObj', 'SwitchObj'):
            el.append('Invalid object type: ' + obj_type + '. ' + d['e'])
        if key is None:
            el.append('Missing k in dictionary for ' + d['e'])
        if not isinstance(rw_d, dict):
            el.append('rw missing in dictionary for ' + d['e'])

        # Figure out what the return content should be
        for key in [k for k, v in rw_d.items() if v]:
            rd.update({key.split('/').pop(): _conv_lookup_act(r_obj, key)})

    except BaseException as e:
        brcdapi_log.exception(_fmt_errors(['Exception:', e, d, r_obj], full=True))
        el.append('Software error. Check the log for details')

    return el, rd


def _switch_summary(cd, switch_name):
    """Returns the switch summary for the switch. One will be created if not yet added

    :param cd: Session, project info, etc. See local_control_d in pseudo_main()
    :type cd: dict
    :param switch_name: Name of switch
    :type switch_name: str
    """
    global _switch_sum_template_d

    switch_d = cd['summary'].get(switch_name)
    if switch_d is None:
        switch_d = _switch_sum_template_d.copy()
        cd['summary'].update({switch_name: switch_d})
    return switch_d


###################################################################
#
#         Leaf Actions (see rw in _action_l)
#
###################################################################
def _conv_none_act(obj, key, sub_key=None):
    """ Always returns None
    
    :param obj: chassis or switch object
    :type obj: brcddb.classes.chassis.ChassisObj, brcddb.classes.switch.SwitchObj
    :param key: The branch Key in obj to lookup. If just one key, use this and make sub_key None
    :type key: str
    :param sub_key: The leaf name
    :type sub_key: str, None
    :return: Value in obj associated with key
    :rtype: None, str, float, bool, int, list, dict
    """
    return None


def _conv_lookup_act(obj, key, sub_key=None):
    """Simple lookup. See _conv_none_act() for parameters"""
    try:
        full_key = key if sub_key is None else key + '/' + sub_key
        return copy.deepcopy(gen_util.get_key_val(obj, full_key))
    except BaseException as e:
        ml = _fmt_errors(['Exception:', e, 'Key: ' + str(key), 'sub_key: ' + str(sub_key), obj], full=True)
        brcdapi_log.exception(ml, echo=True)
    return None


def _conv_ficon_lookup_act(obj, key, sub_key=None):
    """Returns None of any parameter with a FICON switch that must not be set. See _conv_none_act() for parameters"""
    try:
        if obj.r_get('r_is_ficon', False):
            return None
        full_key = key if sub_key is None else key + '/' + sub_key
        return copy.deepcopy(gen_util.get_key_val(obj, full_key))
    except BaseException as e:
        ml = ['Key: ' + str(key), 'sub_key: ' + str(sub_key), str(type(e)) + ': ' + str(e)]
        ml.extend(_fmt_errors(obj, full=True))
        brcdapi_log.exception(ml, echo=True)
    return None


def _default_user_pw_act(obj, key, sub_key=None):
    """Returns an encoded default new user password: _temp_password. See _conv_none_act() for parameters"""
    global _temp_password
    return base64.b64encode(_temp_password.encode('utf-8')).decode('utf-8')


def _true_act(obj, key, sub_key=None):
    """Returns logical True. See _conv_none_act() for parameters"""
    return True


###################################################################
#
#             Support Actions for _build_fid_map
#
###################################################################
def _fm_switch_obj(ml, chassis_obj, fid_map_d, v, fm_index):
    """Fills in r_switch_obj and r_fid in the fid_map_d

    :param ml: running list of error messages
    :type ml: list
    :param chassis_obj: Chassis object of restore chassis
    :type chassis_obj: brcddb.classes.chassis.ChassisObj
    :param fid_map_d: FID map as described in _build_fid_map()
    :type fid_map_d: dict
    :param v: Command line input value
    :type v: int,str,None
    :param fm_index: Index into the command line split on ';'. Used for error messages only
    :type fm_index: int
    :rtype: None
    """
    if v is None:
        ml.append('No parameters specified with -fm option at index ' + str(fm_index))
    else:
        try:
            fid_map_d.update(r_switch_obj=chassis_obj.r_switch_obj_for_fid(int(v)))
            if fid_map_d['r_switch_obj'] is None:
                ml.append('Resource FID, ' + v + ', is not present in the restore chassis.')
            else:
                fid_map_d.update(r_fid=int(v))
                return
        except ValueError:
            ml.append('Resource FID, ' + v + ', must be an integer in the range: 1-128 at index ' + str(fm_index))
    fid_map_d.update(r_switch_obj=None)  # If we got this far, we didn't find the switch object


def _fm_fid(ml, chassis_obj, fid_map_d, v, fm_index):
    """Fills in t_fid in the fid_map_d. See _fm_switch_obj() for parameter definitions"""
    for fid in gen_util.range_to_list(v):
        if fid < 1 or fid > 128:
            ml.append('Target FID, ' + v + ', in -fm parameter must be an integer in the range: 1-128 at index ' +
                      str(fm_index))
            continue
        else:
            fid_map_d['t_fid'] = fid
    if v is None or fid_map_d['r_switch_obj'] is None:
        fid_map_d.update(t_fid=fid_map_d.get('r_fid'))
        return
    try:
        fid = int(v)
        if fid < 1 or fid > 128:
            raise ValueError
        fid_map_d.update(t_fid=fid)
        return
    except ValueError:
        ml.append('Target FID, ' + v + ', in -fm parameter must be an integer in the range: 1-128 at index ' +
                  str(fm_index))


def _fm_fabric_name(ml, chassis_obj, fid_map_d, v, fm_index):
    """Fills in fab_name in the fid_map_d. See _fm_switch_obj() for parameter definitions"""
    if fid_map_d['r_switch_obj'] is None:
        return
    if v is None or len(v) == 0:
        fabric_name = brcddb_fabric.best_fab_name(fid_map_d['r_switch_obj'].r_fabric_obj())
        if ':' in fabric_name:
            fabric_name = None  # The WWN is returned if the fabric isn't named
        fid_map_d.update(fab_name=fabric_name)
    else:
        fid_map_d.update(fab_name=v)


def _fm_did(ml, chassis_obj, fid_map_d, v, fm_index):
    """Fills in did in the fid_map_d. See _fm_switch_obj() for parameter definitions"""
    if fid_map_d['r_switch_obj'] is None:
        return
    if v is None:
        fid_map_d.update(did=fid_map_d['r_switch_obj'].r_did())
        return
    try:
        did = int(v)
        if did < 1 or did > 239:
            raise ValueError
        fid_map_d.update(did=did)
    except ValueError:
        ml.append('Target DID, ' + v + ', must be an integer in the range: 1-239 at index ' + str(fm_index))


def _fm_switch_name(ml, chassis_obj, fid_map_d, v, fm_index):
    """Fills in switch_name in the fid_map_d. See _fm_switch_obj() for parameter definitions"""
    if fid_map_d['r_switch_obj'] is None:
        return
    if v is None or len(v) == 0:
        switch_name = brcddb_switch.best_switch_name(fid_map_d['r_switch_obj'])
        if ':' in switch_name:
            switch_name = None  # The WWN is returned if the switch isn't named
        fid_map_d.update(switch_name=switch_name)
    else:
        fid_map_d.update(switch_name=v)


# _fm_conversion_d is used to build the FID map. The key is the index into the CSV split of the command line input.
# The value is the method to call to determine the value. Used in _build_fid_map()
_fm_conversion_d = {
    0: _fm_switch_obj,  # Converts the resource FID to a switch object
    1: _fm_fid,  # FID to be created in the target chassis.
    2: _fm_fabric_name,  # Fabric name to be defined in the target chassis.
    3: _fm_did,  # switch DID in decimal to be defined in the target chassis.
    4: _fm_switch_name,  # Switch name to be defined in the target chassis.
}


###################################################################
#
#                        Branch Actions
#
###################################################################
def _data_capture(cd, d):
    """Captures a list of URIs from the target chassis

    :param cd: Session, project info, etc. See local_control_d in pseudo_main()
    :type cd: dict
    :param d: Actions to take. This is a dictionary from _control_d
    :type d: dict
    :return: List of error messages as str encountered.
    :rtype: list
    """
    global _data_collect_error_l

    if cd['session'] is None:
        return list()  # This only happens with -scan. If -scan was not specified, the error is reported in _get_input()

    try:
        if api_int.get_batch(cd['session'], cd['t_proj_obj'], d['rl']):
            cd['t_chassis_obj'] = cd['t_proj_obj'].r_chassis_obj(cd['session']['chassis_wwn'])
        else:
            _data_collect_error_l.append('Error(s) capturing data. Check the log for details')

    except BaseException as e:
        brcdapi_log.exception(_fmt_errors(['Exception:', e, d]))
        _data_collect_error_l.append('Software error. Check the log for details')

    if len(_data_collect_error_l) > 0:
        raise FIDMapError

    return list()


def _build_fid_map(cd, d):
    """Builds the FID map as a dictionary. See _data_capture() for parameter definitions.
    
    Key is the target switch FID. Value is a dictionary as follows:

    +---------------+-----------+-------------------------------------------------------------------------------+
    | Key           | Type      | Description                                                                   |
    +===============+===========+===============================================================================+
    | r_switch_obj  | SwitchObj | Switch object of corresponding restore switch. If None, something went wrong  |
    |               | None      | and the remaining keys are not present.                                       |
    +---------------+-----------+-------------------------------------------------------------------------------+
    | r_fid         | int, None | FID of corresponding restore switch.                                          |
    +---------------+-----------+-------------------------------------------------------------------------------+
    | t_fab_name    | str, None | Fabric name. None if the fabric isn't named.                                  |
    +---------------+-----------+-------------------------------------------------------------------------------+
    | t_did         | int       | Domain ID of the target switch. None if something went wrong                  |
    +---------------+-----------+-------------------------------------------------------------------------------+
    | t_switch_name | str, None | Switch name. None if the fabric isn't named.                                  |
    +---------------+-----------+-------------------------------------------------------------------------------+
    """
    global _fm_conversion_d

    fm_index, ml, wl, r_fid_l = 0, list(), list(), list()
    fid_range_buf = ', must be a decimal integer or range of integers from 1-128.'
    did_range_buf = ', is not a valid DID. DIDs must be a decimal integer from 1-239'
    r_chassis_obj, t_chassis_obj, fid_map_d = cd['r_chassis_obj'], cd['t_chassis_obj'], cd['fid_map_d']
    if r_chassis_obj is None:
        ml.append('A chassis object was not found in the project.')
    else:
        r_fid_l = r_chassis_obj.r_fid_list()
        if len(r_fid_l) == 0:
            ml.append('No logical switches found in the chassis. This typically occurs with non-VF enabled chassis')
    if len(ml) > 0:
        return ml, fid_map_d

    args_fm = cd['args_fm'] if isinstance(cd['args_fm'], str) else ';'.join([str(b) for b in r_fid_l])
    for fid_l in [v.split(',') for v in args_fm.replace(' ', '').split(';')]:

        # Get the restore switch FID and switch object
        try:
            r_fid = int(fid_l[0])
        except IndexError:
            ml.append('There are no parameters at index ' + str(fm_index) + ' after splitting -fm input by ";"')
            fm_index += 1
            continue
        except ValueError:
            ml.append('The restore FID at index ' + str(fm_index) + ', ' + fid_l[0] + fid_range_buf)
            fm_index += 1
            continue
        r_switch_obj = r_chassis_obj.r_switch_obj_for_fid(r_fid)
        if r_switch_obj is None:
            ml.append('FID ' + fid_l[0] + ' does not exist in the restore chassis.')
            fm_index += 1
            continue

        # Fill in and get the default parameters
        if len(fid_l) < 2:
            fid_l.append(fid_l[0])
        while len(fid_l) < 5:
            fid_l.append('')
        r_fab_name = r_switch_obj.r_get(brcdapi_util.bfs_fab_user_name)
        if isinstance(r_fab_name, str) and len(r_fab_name) == 0:
            r_fab_name = None
        r_switch_name = r_switch_obj.r_get(brcdapi_util.bfs_sw_user_name,
                                           r_switch_obj.r_get(brcdapi_util.bf_sw_user_name))
        if isinstance(r_switch_name, str) and len(r_switch_name) == 0:
            r_switch_name = None

        # Get the target chassis parameters
        t_fid_l = list()  # Just to keep the IDE warnings down
        try:
            t_fid_l = gen_util.range_to_list(fid_l[1])
        except ValueError:
            ml.append('The target FID, ' + fid_l[1] + ', at index ' + str(fm_index) + fid_range_buf)
        for t_fid in t_fid_l:
            if t_fid < 1 or t_fid > 128:
                ml.append('The target FID, ' + str(t_fid) + ', at index ' + str(fm_index) + fid_range_buf)
            # t_switch_obj = t_chassis_obj.r_switch_obj_for_fid(t_fid)
            # if t_switch_obj is None:
            #     wl.append(t_fid)
            #     fm_index += 1
            #     continue
            try:
                t_did = r_switch_obj.r_did() if len(fid_l[3]) == 0 else int(fid_l[3])
            except ValueError:
                ml.append('The target DID, ' + str(fid_l[3]) + did_range_buf)
                fm_index += 1
                continue
            if t_did < 1 or t_did > 239:
                ml.append('The target DID, ' + str(t_did) + did_range_buf)
                fm_index += 1
                continue
            fid_map_d.update({t_fid: dict(
                r_switch_obj=r_switch_obj,
                r_fid=r_fid,
                t_fab_name=r_fab_name if len(fid_l[2]) == 0 else None if fid_l[2].lower() == 'none' else fid_l[2],
                t_did=t_did,
                t_switch_name=r_switch_name if len(fid_l[4]) == 0 else None if fid_l[4].lower() == 'none' else fid_l[4]
            )})

        fm_index += 1

    if len(ml) > 0:
        brcdapi_log.log(ml, echo=True)
        raise FIDMapError

    return list()


def _data_clear(cd, d):
    """Clears all data from captured session. See _data_capture() for parameter definitions"""
    el = list()
    try:
        cd['t_proj_obj'].s_del_chassis(cd['session'].pop('chassis_wwn'))
        try:
            for key in ('t_chassis_obj', 't_fid', 'fid_map_d'):
                cd.pop(key)
        except AttributeError:
            pass
    except KeyError:
        pass  # chassis_wwn and perhaps t_proj_obj does not exist if no data has been captured yet.
    except BaseException as e:
        brcdapi_log.exception(_fmt_errors(['Exception:', e, d, cd]))
        el.append('Software error. Check the log for details')
    return el


def _del_switches(cd, d):
    """Deletes all logical switches except the default logical switch. See _data_capture() for parameter definitions"""
    el, obj = list(), None
    try:
        for switch_obj in [o for o in cd['t_chassis_obj'].r_switch_objects() if not o.r_is_default()]:
            switch_name = brcddb_switch.best_switch_name(switch_obj, fid=True)
            fid = switch_obj.r_fid()
            obj = brcdapi_switch.delete_switch(cd['session'], fid, echo=True)
            if fos_auth.is_error(obj):
                el.extend(['Error deleting ' + switch_name, fos_auth.formatted_error_msg(obj)])
            else:
                _switch_summary(cd, switch_name)['Removed'] = True
    except BaseException as e:
        brcdapi_log.exception(_fmt_errors(['Exception:', e, d, cd, obj], full=True))
        el.append('Software error. Check the log for details')
    return el


def _vf_enable(cd, d):
    """Enable/Disable virtual fabrics. See _data_capture() for parameter definitions"""
    el, obj = list(), None
    try:
        el, content_d = _patch_content(cd['r_chassis_obj'], cd['t_chassis_obj'], d)
        if len(content_d) > 0:
            el.extend(_enable_disable_chassis(cd['session'], False, '_vf_enable, index: ' + d['e']))  # Disable chassis
            if len(el) == 0:
                # Set VF
                obj = brcdapi_rest.send_request(cd['session'], d['k'], d['m'], content_d)
                if fos_auth.is_error(obj):
                    el.extend(['Error updating chassis URI: ' + d['k'] + ', Index: ' + d['e'],
                               'FOS error:',
                               fos_auth.formatted_error_msg(obj)])
                else:
                    cd['summary']['chassis']['VF Enable'] = True
                # Re-enable chassis. Note: If the chassis was disabled from the start, we wouldn't have gotten this far
                el.extend(_enable_disable_chassis(cd['session'], True, '_vf_enable, index: ' + d['e']))
    except BaseException as e:
        brcdapi_log.exception(_fmt_errors(['Exception:', e, d, cd, obj], full=True))
        el.append('Software error. Check the log for details')
    return el


def _restore_switches(cd, d):
    """Re-creates logical switches. See _data_capture() for parameter definitions"""
    el = list()

    try:
        for t_fid, fm_d in cd['fid_map_d'].items():
            if cd['t_chassis_obj'].r_switch_obj_for_fid(t_fid) is None:
                switch_name = fm_d['t_switch_name'] + ' FID: ' + str(t_fid)
                # Create the logical switch
                r_switch_obj = fm_d['r_switch_obj']
                obj = brcdapi_switch.create_switch(cd['session'],
                                                   t_fid,
                                                   r_switch_obj.r_is_base(),
                                                   r_switch_obj.r_is_ficon(),
                                                   echo=True)
                if fos_auth.is_error(obj):
                    el.extend(['Error creating ' + switch_name + ', ' + d['e'], fos_auth.formatted_error_msg(obj)])
                else:
                    _switch_summary(cd, switch_name)['Added'] = True

                # Error reporting uses the DID and switch name from the switch so set that up now
                content_d = {
                    'domain-id': fm_d['t_did'],
                    'user-friendly-name': fm_d['t_switch_name']
                }
                obj = brcdapi_switch.fibrechannel_switch(cd['session'], t_fid, content_d)
                if fos_auth.is_error(obj):
                    buf = 'Error setting Domain ID, ' + str(fm_d['t_did']) + ' and switch name ' + switch_name +\
                          fm_d['t_switch_name'] + ' for FID ' + str(t_fid)
                    el.extend([buf, d['e'] + ': FOS error is:', fos_auth.formatted_error_msg(obj)])

    except BaseException as e:
        brcdapi_log.exception(_fmt_errors(['Exception:', e, 'Parameter d:', d], full=True))
        el.append('Software error. Check the log for details')

    return el


def _restore_ports(cd, d):
    """Move ports from default switch to logical switch. See _data_capture() for parameter definitions"""
    el, t_fid, t_chassis_obj, success_l = list(), 0, cd['t_chassis_obj'], list()
    try:
        for t_fid, fm_d in cd['fid_map_d'].items():
            r_switch_obj = fm_d['r_switch_obj']
            t_switch_obj = t_chassis_obj.r_switch_obj_for_fid(t_fid)
            if t_switch_obj is None:
                el.append('Could not restore ports. FID ' + str(t_fid) + ' does not exist')
                continue
            switch_name = fm_d['t_switch_name'] + ' FID: ' + str(t_fid)

            # Figure out where the ports are to add. If vfc wasn't specified, they might not be in the default switch
            fid_ports_d = dict()
            for t in ('p', 'g'):
                port_l = [p for p in r_switch_obj.r_port_keys() if t_switch_obj.r_port_obj(p) is None] if t == 'p' \
                    else [p for p in r_switch_obj.r_ge_port_keys() if t_switch_obj.r_ge_port_obj(p) is None]
                for port in port_l:
                    port_obj = t_chassis_obj.r_port_obj(port) if t == 'p' else t_chassis_obj.r_ge_port_obj(port)
                    if port_obj is not None:
                        fid = port_obj.r_switch_obj().r_fid()
                        if fid is not None:
                            fid_d = fid_ports_d.get(fid)
                            if fid_d is None:
                                fid_d = dict(p=list(), g=list())
                                fid_ports_d.update({fid: fid_d})
                            fid_ports_d[fid][t].append(port)
                        
            # Move the ports to the target switch
            success_l, fault_l = list(), list()
            for s_fid, fid_d in fid_ports_d.items():
                success_l, fault_l = brcdapi_switch.add_ports(cd['session'],
                                                              t_fid,
                                                              s_fid,
                                                              fid_d['p'],
                                                              fid_d['g'],
                                                              echo=True,
                                                              best=True,
                                                              skip_default=cd['act_d'].get('vfc', False))
                if len(fault_l) > 0:
                    el.extend(['Error adding ports to ' + switch_name, '  ' + d['e'], '  Ports: ' + ', '.join(fault_l)])

            switch_sum_d = _switch_summary(cd, switch_name)
            switch_sum_d['Ports Added'] += len(success_l)
            switch_sum_d['Ports Add Fail'] += len(fault_l)
            switch_sum_d = _switch_summary(cd,
                                           brcddb_switch.best_switch_name(cd['t_chassis_obj'].r_default_switch_obj()))
            switch_sum_d['Ports Removed'] += len(success_l)

            # Bind any addresses that need to be bound.
            if brcddb_switch.switch_type(t_switch_obj) == 'FICON':
                port_d = dict()
                for port in success_l:
                    r_port_obj = r_switch_obj.r_port_obj(port)
                    if r_port_obj is not None:
                        bind_l = r_port_obj.r_get('fibrechannel/bound-address-list/bound-address', list())
                        if len(bind_l) > 0:
                            port_d.update({port: bind_l[0]})
                if len(port_d) > 0:
                    brcdapi_port.bind_addresses(cd['session'], t_fid, port_d)

    except BaseException as e:
        brcdapi_log.exception(['Software error. Exception:'] + _fmt_errors(['Exception:', e, 't_fid :' + str(t_fid)]))
        el.append('Software error. Check the log for "Software error. Exception:"')

    return el


def _none_act(cd, d):
    return list()


def _fibrechannel_switch(cd, d):
    """Actions for brocade-fibrechannel-switch. See _data_capture() for parameter definitions"""
    el = list()
    try:
        brcdapi_log.log('_fibrechannel_switch', echo=True)
        el.append('WIP: _fibrechannel_switch')
    except BaseException as e:
        brcdapi_log.exception(['Software error. Exception:'] + _fmt_errors(e))
        el.append('Software error. Check the log for details')
    return el


def _trunk_act(cd, d):
    """Re-create trunk groups. See _data_capture() for parameter definitions"""
    el = list()
    try:
        el.append('WIP: _trunk_act')
    except BaseException as e:
        brcdapi_log.exception(['Software error. Exception:'] + _fmt_errors(e))
        el.append('Software error. Check the log for details')
    return el
    # rl = [{'trunk-index': d['trunk-index'], 'trunk-members': d['trunk-members']} for d in
    #       gen_util.convert_to_list(d['r_obj'].r_get(d['key']))]
    # return None if len(rl) == 0 else rl


def _user_act(cd, d):
    """Re-create non-default users. See _data_capture() for parameter definitions"""
    global _temp_password
    
    el, content_l = list(), list()
    try:
        key, rw_d, t_chassis_obj = d['k'], d['rw'], cd['t_chassis_obj']
        t_user_l = cd['t_chassis_obj'].r_get(key, list())
        if len(t_user_l) > 0:
            existing_user_d = dict(root=True)  # Newer versions of FOS don't support root. Make sure root gets skipped
            for td in t_chassis_obj.r_get(key, list()):
                existing_user_d.update({td['name']: True})
            for rd in cd['r_chassis_obj'].r_get(key, list()):
                if not existing_user_d.get(rd['name'], False):
                    content_d = collections.OrderedDict() if isinstance(rw_d, collections.OrderedDict) else dict()
                    for k in rw_d.keys():
                        content_d.update({k: rw_d[k](rd, k)})
                        if k == 'password':
                            cd['summary']['chassis']['Users'].append('ID: ' + str(rw_d.get('name')) + '. Password: ' +
                                                                     _temp_password)
                    content_l.append(content_d)
        if len(content_l) > 0:
            return _send_request(cd['session'], d['m'], key, content_l)
    except BaseException as e:
        brcdapi_log.exception(_fmt_errors(['Exception:', e, d, cd], full=True))
        el.append('Software error. Check the log for details')
        
    return el


def _zone_restore(cd, d):
    """Restore zoning if there are zoning differences. See _data_capture() for parameter definitions"""
    global _zonecfg_enable

    el, t_chassis_obj, control_d = list(), cd['t_chassis_obj'], dict(_effective_zone_cfg=dict(skip=True))
    for t_fid, fm_d in cd['fid_map_d'].items():

        # Make sure the switch exists in both chassis and that it's online in the target chassis
        r_fab_obj = fm_d['r_switch_obj'].r_fabric_obj()
        if r_fab_obj is None:
            continue
        t_switch_obj = t_chassis_obj.r_switch_obj_for_fid(t_fid)
        error_preamble = 'Could not restore zone configuration for FID ' + str(t_fid)
        if t_switch_obj is None:
            el.append(error_preamble + '. FID does not exist in target switch.')
            continue
        t_fab_obj = t_switch_obj.r_fabric_obj()
        if t_fab_obj is None:
            if t_switch_obj.r_is_enabled():
                el.append('Software error. ' + error_preamble + '. Fabric for switch does not exist.')
            else:
                el.append(error_preamble + ' because the switch is disabled.')
            continue

        # Check for differences and if there are differences, update the zoning.
        try:
            for d in [
                dict(r=r_fab_obj.r_alias_objs(), t=t_fab_obj.r_alias_objs()),
                dict(r=r_fab_obj.r_zone_objs(), t=t_fab_obj.r_zone_objs()),
                dict(r=r_fab_obj.r_zonecfg_objs(), t=t_fab_obj.r_zonecfg_objs()),
            ]:
                change_count, change_d = brcddb_compare.compare(d['r'], d['t'], control_tbl=control_d)
                if change_count > 0:
                    raise Found
        except Found:
            eff_zone_config = None
            if _zonecfg_enable:
                eff_zone_config = r_fab_obj.r_defined_eff_zonecfg_key()
            obj = api_zone.replace_zoning(cd['session'], r_fab_obj, t_fid, eff=eff_zone_config)
            if fos_auth.is_error(obj):
                buf = 'Failed to replace zoning in FID ' + str(t_fid)
                brcdapi_log.log([buf] + _fmt_errors(fos_auth.formatted_error_msg(obj)), echo=True)
                el.append('Failed to replace zoning in FID ' + str(t_fid))
            else:
                _switch_summary(cd, fm_d['t_switch_name'] + ' FID: ' + str(t_fid))['Zone Changes'] = True

    return el


def _zone_enable(cd, d):
    """Restore zoning if there are zoning differences. See _data_capture() for parameter definitions"""
    global _zonecfg_enable
    _zonecfg_enable = True
    return list()


def _chassis_update_act(cd, d):
    """Updates that do not have any special considerations. See _data_capture() for parameter definitions"""
    el, content_l = list(), list()
    try:
        key, rw_d, r_chassis_obj, t_chassis_obj = d['k'], d['rw'], cd['r_chassis_obj'], cd['t_chassis_obj']
        r_name, t_name =\
            brcddb_chassis.best_chassis_name(r_chassis_obj), brcddb_chassis.best_chassis_name(t_chassis_obj)
        rd, td = r_chassis_obj.r_get(key), t_chassis_obj.r_get(key)
        if rd is not None and type(td) is not type(rd):
            el.append(key + ' not supported in target chassis ' + t_name)
        elif td is not None and not isinstance(rd, type(td)):
            el.append(key + ' not supported in restore chassis ' + r_name)
        if len(el) > 0:
            return el
        for k, method in rw_d.items():
            r_val, t_val = method(rd, k), method(td, k)
            if t_val is not None and type(r_val) is not type(t_val):
                el.append(key + '/' + str(k) + ' not supported in restore chassis ' + r_name)
                continue
            elif r_val is not None and type(t_val) is not type(r_val):
                el.append(key + '/' + str(k) + ' not supported in target chassis ' + t_name)
                continue
            if d['m'] == 'POST':
                content_l.append({k: r_val})
            elif d['m'] == 'PATCH' and (str(r_val) != str(t_val)):
                content_l.append({k: r_val})
        if len(content_l) > 0:
            return _send_request(cd['session'], d['m'], key, content_l)
    except BaseException as e:
        brcdapi_log.exception(_fmt_errors(['Exception:', e, d, cd], full=True))
        el.append('Software error. Check the log for details')
    return el


def _switch_update_act(cd, d):
    """Switch updates that do not have any special considerations. See _data_capture() for parameter definitions"""
    el, content_d = list(), dict()

    for t_fid, fm_d in cd['fid_map_d'].items():
        t_switch_obj = cd['t_chassis_obj'].r_switch_obj_for_fid(t_fid)
        if t_switch_obj is None:
            el.append('Could not update switch configuration. FID ' + str(t_fid) + ' does not exist')
            continue
        r_switch_obj = cd['fid_map_d'][t_fid]['r_switch_obj']
        try:
            key, rw_d = d['k'], d['rw']

            # Prepare the content for the target switch
            for k, method in rw_d.items():
                r_val, t_val = method(r_switch_obj, key, k), method(t_switch_obj, key, k)
                if t_val is not None and type(r_val) is not type(t_val):
                    el.append(key + '/' + str(k) + ' missing in restore switch ' +
                              brcddb_switch.best_switch_name(r_switch_obj, fid=True))
                    continue
                elif r_val is not None and type(t_val) is not type(r_val):
                    el.append(key + '/' + str(k) + ' not supported in target chassis ' +
                              brcddb_switch.best_switch_name(t_switch_obj, fid=True))
                    continue
                if d['m'] == 'POST':
                    content_d.update({k: r_val})
                elif d['m'] == 'PATCH' and (str(r_val) != str(t_val)):
                    content_d.update({k: r_val})

            # Send the changes to the target switch
            if len(content_d) > 0:
                if 'brocade-fibrechannel-switch' in key:
                    obj = brcdapi_switch.fibrechannel_switch(cd['session'], t_fid, content_d, t_switch_obj.r_obj_key())
                    if fos_auth.is_error(obj):
                        el.extend(['Error updating chassis URI:',
                                   '  ' + key,
                                   pprint.pformat(content_d),
                                   'FOS error:',
                                   fos_auth.formatted_error_msg(obj)])
                else:
                    el.extend(_send_request(cd['session'], d['m'], key, content_d, fid=t_fid))

        except BaseException as e:
            brcdapi_log.exception(_fmt_errors(['Exception:', e, d, cd], full=True))
            el.append('Software error. Check the log for details')

    return el


def _fcr_update_act(cd, d):
    """Switch updates that do not have any special considerations. See _data_capture() for parameter definitions"""
    el = list()

    for t_fid, fm_d in cd['fid_map_d'].items():
        t_switch_type = brcddb_switch.switch_type(cd['t_chassis_obj'].r_switch_obj_for_fid(t_fid))
        r_switch_type = brcddb_switch.switch_type(cd['fid_map_d'][t_fid]['r_switch_obj'])
        if isinstance(t_switch_type, str) and isinstance(r_switch_type, str):
            if r_switch_type == 'Base' and t_switch_type == 'Base':
                # Modify the FID map in cd so _switch_update_act() can be called
                fcr_cd = cd.copy()
                fcr_cd.update(fid_map_d=dict())
                for k, fid_map_d in cd['fid_map_d'].items():
                    if k == t_fid:
                        fcr_cd['fid_map_d'].update({k: fid_map_d})
                el.extend(_switch_update_act(fcr_cd, d))

    return el


def _port_config_cli(el, r_port_obj, t_port_obj):
    # ToDo This is a hack until long distance modes are supported in the API
    # Since there is no way to determine what the -distance setting was for LS mode, treat it like LD mode with the
    # current number of reserved buffers for the port. The flaw with this is that if the link speed is ever changed
    # the number of reserved buffers will not be correct. There is no way to tell if -distance was specified with the
    # portcfglongdistance command or what the value was. Similarly, there is no way to determine if -buffers was
    # specified with LD mode, so I'm just assuming it wasn't.

    cli_l = list()
    if r_port_obj is None or t_port_obj is None:
        return cli_l

    r_portcfgshow_d = r_port_obj.r_get('fos_cli/portcfgshow')
    t_portcfgshow_d = t_port_obj.r_get('fos_cli/portcfgshow', dict())
    r_portbuffershow_d = r_port_obj.r_get('fos_cli/portbuffershow')
    if r_portcfgshow_d is None or r_portbuffershow_d is None:
        return cli_l
    t_port_num = fos_cli.cli_port(t_port_obj.r_obj_key())
    if isinstance(r_portcfgshow_d, dict) and isinstance(r_portbuffershow_d, dict):

        # Locked E-Port
        r_val, t_val = r_portcfgshow_d.get('Locked E_Port', None), t_portcfgshow_d.get('Locked E_Port', None)
        if r_val is not None:
            if type(r_val) is not type(t_val) or r_val != t_val:
                buf = '2' if r_val == 'ON' else '1'
                cli_l.append('portcfgeport ' + t_port_num + ' -p ' + buf)

        # Long distance mode
        r_val, t_val = r_portcfgshow_d.get('Long Distance', None), t_portcfgshow_d.get('Long Distance', None)
        if r_val is not None:
            if r_val == 'LS':
                r_val = 'LD'  # Treating LS and LD the same
            r_vc_link_init = str(r_port_obj.r_get('fibrechannel/vc-link-init'))
            t_vc_link_init = str(t_port_obj.r_get('fibrechannel/vc-link-init'))
            r_buffers = str(r_port_obj.r_get('fibrechannel/reserved-buffers') - 6)
            t_buffers = str(r_port_obj.r_get('fibrechannel/reserved-buffers') - 6)
            try:
                if type(r_val) is not type(t_val) or r_val != t_val:
                    raise Found
                if type(r_vc_link_init) is not type(t_vc_link_init) or r_vc_link_init != t_vc_link_init:
                    raise Found
                if type(r_buffers) is not type(t_buffers) or r_buffers != t_buffers:
                    raise Found
            except Found:
                if r_val == '..':
                    cli_l.append('portcfglongdistance ' + t_port_num + ' L0')
                elif r_val == 'LS' or r_val == 'LD':
                    cli_l.append('portcfglongdistance ' + t_port_num + ' LD ' + r_vc_link_init + ' -buffers ' +
                                 r_buffers)
                elif r_val == 'LE':
                    cli_l.append('portcfglongdistance ' + t_port_num + ' LE ' + r_vc_link_init)

        # ISL R_RDY Mode
        r_val, t_val = r_portcfgshow_d.get('ISL R_RDY Mode', None), t_portcfgshow_d.get('ISL R_RDY Mode', None)
        if r_val is not None:
            if type(r_val) is not type(t_val) or r_val != t_val:
                buf = '1' if r_val == 'ON' else '0'
                cli_l.append('portcfgislmode ' + t_port_num + ' ' + buf)

    return cli_l


def _port_update_act(cd, d):
    """Port updates that do not have any special considerations. See _data_capture() for parameter definitions"""
    el, content_d = list(), dict()
    try:
        rw_d, key = d['rw'], d['k'].replace('brocade-interface/', '')
        for t_fid, fm_d in cd['fid_map_d'].items():
            t_switch_obj = cd['t_chassis_obj'].r_switch_obj_for_fid(t_fid)
            if t_switch_obj is None:
                el.append('Could not update port configurations. FID ' + str(t_fid) + ' does not exist')
                continue
            r_switch_obj = cd['fid_map_d'][t_fid]['r_switch_obj']

            # Update the ports
            content_l, cli_l = list(), list()
            for r_port_obj in r_switch_obj.r_port_objects():
                t_port_obj = t_switch_obj.r_port_obj(r_port_obj.r_obj_key())
                if t_port_obj is None:
                    continue

                # Figure out the API Content
                sub_d = dict(name=t_port_obj.r_obj_key())
                for k, method in rw_d.items():
                    r_val, t_val = method(r_port_obj, key, k), method(t_port_obj, key, k)
                    if r_val is None and t_val is None:
                        continue
                    if r_val is None or t_val is None:
                        el.append(key + '/' + str(k) + ' not restored in port ' + t_port_obj.r_obj_key())
                        continue
                    if d['m'] == 'POST':
                        sub_d.update({k: r_val})
                    elif d['m'] == 'PATCH' and (str(r_val) != str(t_val)):
                        sub_d.update({k: r_val})
                if len(sub_d) > 1:
                    content_l.append(sub_d)

            # Send the API updates
            if len(content_l) > 0:
                el.extend(_send_request(cd['session'], d['m'], d['k'], content_l, fid=t_fid))

    except BaseException as e:
        brcdapi_log.exception(_fmt_errors(['Exception:', e, d, cd], full=True))
        el.append('Software error. Check the log for details')
    return el


def _port_cli_wait_act(cd, d):
    """Checks to see if CLI commands were issued and sleeps to allow the API and CLI to sync up. See _data_capture() \
    for parameter definitions"""
    global _cli_change_flag, _DEFAULT_WAIT
    if _cli_change_flag:
        fos_cli.cli_wait(_DEFAULT_WAIT)
        _cli_change_flag = False
    return list()


def _port_cli_update_act(cd, d):
    """Port updates that must be done via the CLI. See _data_capture() for parameter definitions"""
    global _cli_change_flag

    el = list()

    for t_fid, fm_d in cd['fid_map_d'].items():
        cli_l = list()
        t_switch_obj = cd['t_chassis_obj'].r_switch_obj_for_fid(t_fid)
        if t_switch_obj is None:
            el.append('Could not update port configurations. FID ' + str(t_fid) + ' does not exist')
            continue
        for r_port_obj in cd['fid_map_d'][t_fid]['r_switch_obj'].r_port_objects():
            cli_l.extend(_port_config_cli(el, r_port_obj, t_switch_obj.r_port_obj(r_port_obj.r_obj_key())))

        # Send the CLI updates
        if len(cli_l) > 0:
            _cli_change_flag = True
            for buf in cli_l:
                fos_cli.send_command(cd['session'], t_fid, buf)

    return el


def _maps_act(cd, d):
    """Updates for rule and policies if there are differences. See _data_capture() for parameter definitions"""
    el = list()

    try:
        t_chassis_obj = cd['t_chassis_obj']

        # The MAPS utility was originally designed for creating MAPS rules, policies, and groups from a workbook. It
        # updates MAPS based on one restore switch at a time and replicates MAPS to target switches based on a map,
        # fid_map_l. That's the reverse flow used herein. Below sets up data structures for use with the MAPS utility.

        for r_switch_obj in cd['r_chassis_obj'].r_switch_objects():
            fid_map_l = [0 for f in range(0, 129)]  # The target FID is the index and the value the restore FID
            r_fid = r_switch_obj.r_fid()
            for t_fid, d in cd['fid_map_d'].items():
                if d['r_fid'] == r_fid:
                    fid_map_l[t_fid] = r_fid

            # Send the updates.
            error_l, changes = util_maps.update_maps(cd['session'], t_chassis_obj, r_switch_obj, fid_map_l, echo=True)
            el.extend(error_l)
            if changes > 0:
                # TODO When mapped to multiple FIDs IDK which FID the changes are associated with
                # Below marks MAPS changes to all the mapped FIDs but it may not have been all of them.
                for t_fid in range(0, len(fid_map_l)):
                    if fid_map_l[t_fid] == r_fid:
                        _switch_summary(cd, d['t_switch_name'] + ' FID: ' + str(t_fid))['MAPS Changes'] = True

    except BaseException as e:
        brcdapi_log.exception(_fmt_errors(['Exception:', e, d, cd]))
        el.append('Software error. Check the log for details')

    return el


def _scan_act(cd, d):
    """Returns basic logical switch information. See _data_capture() for parameter definitions"""
    el = ['', 'Restore', '']
    if cd['r_proj_obj'] is None:
        el.append('-i, not specified.')
    else:
        el.extend(brcddb_project.scan(cd['r_proj_obj'], fab_only=False, logical_switch=True))
    el.extend(['', 'Target', ''])
    if cd['session'] is None:
        el.append('  Login credentials not specified.')
    else:
        el.extend(brcddb_project.scan(cd['t_proj_obj'], fab_only=False, logical_switch=True))
    el.append('')
    return el


def _enable(cd, d):
    """Enable all the switches and ports in the target switch that were enabled in the restore switch.

    :param cd: Session, project info, etc. See local_control_d in pseudo_main()
    :type cd: dict
    :return: List of error messages as str encountered.
    :rtype: list
    """
    el = list()
    try:
        for t_switch_obj in cd['t_chassis_obj'].r_switch_objects():

            # Make sure it's one of the FIDs to be restored before continuing
            t_fid = t_switch_obj.r_fid()
            fid_map_d = cd['fid_map_d'].get(t_fid)
            if fid_map_d is None:
                continue
            r_switch_obj = fid_map_d['r_switch_obj']
            if not r_switch_obj.r_is_enabled():
                continue

            # Enable the switch
            obj = brcdapi_switch.enable_switch(cd['session'], t_fid)
            if fos_auth.is_error(obj):
                el.extend(['Failed to enable FID ' + str(t_fid), fos_auth.formatted_error_msg(obj)])
                # A disabled switch is not in a fabric and nothing else can be enabled in a disabled switch
                continue

            # Enable the ports
            port_l = [p for p in t_switch_obj.r_port_keys() + t_switch_obj.r_ge_port_keys() if
                      r_switch_obj.r_port_obj(p) is not None and r_switch_obj.r_port_obj(p).r_is_enabled()]
            obj = brcdapi_port.enable_port(cd['session'], t_fid, port_l, persistent=True, echo=False)
            if fos_auth.is_error(obj):
                el.extend(['Failed to enable FID ' + str(t_fid), fos_auth.formatted_error_msg(obj)])

    except BaseException as e:
        brcdapi_log.exception(_fmt_errors(['Exception:', e, cd]))
        el.append('Software error. Check the log for details')

    return el


"""_control_d is a dictionary of dictionaries. The first key is the highest level branch (right after running) and
the second is the next branch level URI. The final dictionary instructs the machine in psuedo_main() how to act on
the URI branch as noted in the table below.

Ordered dictionaries were used because in some cases the order of operations is significant. For example, user IDs must
be created before they can be modified.

Special keys begin with '_'. Special keys are different in that they are not processed as a simple compare and update
differences. Special keys are used to capture, refresh, and create switches. Creating switches and adding ports are
treated as special circumstances abe they have timing and other considerations which are addressed by modules in the
brcdapi library. 

+-------+-----------+-----------------------------------------------------------------------------------------------+
| Key   | Type      | Description                                                                                   |
+=======+===========+===============================================================================================+
| a     | method    | Pointer to method to call when interpreting the branch. If None or not present, the URI is    |
|       |           | put in _full_capture_l, so a GET is performed, but no action is taken.                        |
+-------+-----------+-----------------------------------------------------------------------------------------------+
| e     | str       | Text to append to error messages. Only useful for trouble shooting.                           |
+-------+-----------+-----------------------------------------------------------------------------------------------+
| k     | str       | KPI (URI not including the leading 'running/' or anything prior). Only used if the action     |
|       |           | method needs to access an API resource. May be a CSV if multiple KPIs are required.           |
+-------+-----------+-----------------------------------------------------------------------------------------------+
| m     | HTTP      | HTTP method                                                                                   |
+-------+-----------+-----------------------------------------------------------------------------------------------+
| p     | None, str | If None, always execute this action. Otherwise, the entry is only executed if specified with  |
|       |           | the -p option on the command line. See -p options in _restore_parameters for details.         |
+-------+-----------+-----------------------------------------------------------------------------------------------+
| rl    | str, list | Data specific to the action method.                                                           |
+-------+-----------+-----------------------------------------------------------------------------------------------+
| rw    | dict      | Dictionary of leaf names that support read and write. The value is a pointer to a method that |
|       |           | interprets the value for the leaf. At the time this was written, there were only two options: |
|       |           |                                                                                               |
|       |           |   _conv_none_act      Always returns None. None is assumed for any leaf not in the            |
|       |           |                       dictionary so this is only useful as a place holder for a leaf you may  |
|       |           |                       want to change at a future date.                                        |
|       |           |                                                                                               |
|       |           |   _conv_lookup_act    A simple deepcopy of what ever the value for the leaf is.               |
+-------+-----------+-----------------------------------------------------------------------------------------------+
| skip  | bool      | If True, skip this item. Essentially comments out this entry. Set True for all untested       |
|       |           | entries.                                                                                      |
+-------+-----------+-----------------------------------------------------------------------------------------------+

A basic capture (capture_0) is required for deleting (_del_switches), creating logical switches (_restore_switches),
and restoring ports (_restore_ports). Data should always be cleared (_data_clear) before capturing (_data_capture) a
fresh set of data. A fresh set of data should always be captured after making changes that may effect other
operations.

For a partial restore, comment out any entries in _control_d you don't want to modify.

The following key/value pairs are added to the dictionaries in _control_d as data is collected:

+-------------------+---------------+-------------------------------------------------------------------------------+
| Key               | Type          | Description                                                                   |
+===================+===============+===============================================================================+
| session           | dict          | Session object returned from brcdapi.fos_auth.login()                         |
+-------------------+---------------+-------------------------------------------------------------------------------+
| r_chassis_obj     | ChassisObj    | Restore from chassis object.                                                  |
+-------------------+---------------+-------------------------------------------------------------------------------+
| t_chassis_obj     | ChassisObj    | Target chassis object.                                                        |
+-------------------+---------------+-------------------------------------------------------------------------------+
| r_default_fid     | int           | Restore chassis default FID                                                   |
+-------------------+---------------+-------------------------------------------------------------------------------+
| t_fid_d           | dict          | Key value pairs are:                                                          |
|                   |               |   default         List with one entry, the default switch FID of the target   |
|                   |               |                   chassis                                                     |
|                   |               |   all             List of all FIDs in the target chassis                      |
|                   |               |   all_non_default List of all FIDs in the target chassis except the default   |
|                   |               |                   FID                                                         |
+-------------------+---------------+-------------------------------------------------------------------------------+
| act_d             | dict          | Keys are the same keys in _restore_parameters. Value is True if entered in    |
|                   |               | the shell prompt.                                                             |
+-------------------+---------------+-------------------------------------------------------------------------------+

WARNING: This is a template with some suggestions. Anything with _conv_none_act or _none_act in most cases is a work
         in progress
"""

_scan_action_l = [
    dict(a=_data_capture, rl=_basic_capture_kpi_l, e='Basic Capture 0', p='m'),
    dict(a=_scan_act, e='Scan', p='m'),
    ]

_action_l = [  # See block comments above for definitions
    
    # Start with a full data capture and build the FID map
    dict(a=_data_capture, rl=_basic_capture_kpi_l, e='Initial Capture', p='m'),
    dict(a=_build_fid_map, e='Build FID map', p='m'),

    # Virtual Fabrics
    dict(k=brcdapi_util.bcc_uri, a=_vf_enable, e='_vf_enable', p='vfc', rw={'vf-enabled': _conv_lookup_act}),
    dict(a=_del_switches, e='_del_switches', p='vfc'),
    dict(a=_data_clear, e='_data_clear 1', p='vfs'),
    dict(a=_data_capture, rl=_basic_capture_kpi_l, e='Basic Capture vfs', p='vfs'),
    dict(k=brcdapi_util.bfsw_uri, a=_restore_switches, e='_restore_switches', p='vfs'),
    dict(a=_data_clear, e='_data_clear 2', p='vfp'),
    dict(a=_data_capture, rl=_basic_capture_kpi_l, e='Basic Capture 2', p='vfp'),
    dict(k=brcdapi_util.bifc_uri, a=_restore_ports, e='_restore_ports', p='vfp'),

    # Capture a full set of data before continuing.
    dict(a=_data_clear, e='_data_clear 3', p='m'),
    dict(a=_data_capture, rl=_full_capture_l, e='Full Capture', p='m'),

    # c: Chassis parameters
    dict(k=brcdapi_util.bcc_uri, a=_chassis_update_act, m='PATCH', p='c', rw={
        'chassis-user-friendly-name': _conv_lookup_act,
        'fcr-enabled': _conv_lookup_act,
        'chassis-enabled': _conv_none_act,
        'shell-timeout': _conv_lookup_act,
        'session-timeout': _conv_lookup_act,
        'tcp-timeout-level': _conv_lookup_act,
    }),
    # Minimally tested
    dict(k=brcdapi_util.bcmic_uri, a=_none_act, m='PATCH', p='c', skip=True, rw={
        'rest-enabled,https-protocol-enabled': _conv_lookup_act,
        'max-rest-sessions': _conv_lookup_act,
        'https-keep-alive-enabled': _conv_none_act,
        'cp-name': _conv_lookup_act,
        'interface-name': _conv_lookup_act,
        'auto-negotiate': _conv_lookup_act,
        'speed': _conv_lookup_act,
        'lldp-enabled': _conv_lookup_act,
    }),
    # Minimally tested
    dict(k='brocade-chassis/management-port-track-configuration', a=_none_act, m='PATCH', p='c', skip=True, rw={
        'tracking-enabled,scan-interval': _conv_lookup_act,
    }),
    # Minimally tested
    dict(k='brocade-chassis/credit-recovery', a=_none_act, m='PATCH', p='c', skip=True, rw={
        'mode': _conv_lookup_act,
        'link-reset-threshold': _conv_lookup_act,
        'fault-option': _conv_lookup_act,
        'backend-credit-loss-enabled': _conv_lookup_act,
        'backend-loss-of-sync-enabled': _conv_lookup_act,
    }),

    # FCR: Minimally tested - TODO Finish this.
    dict(k=brcdapi_util.bfr_rc, a=_fcr_update_act, m='PATCH', p='fcr', rw={
        'maximum-lsan-count': _conv_lookup_act,
        'backbone-fabric-id': _conv_lookup_act,
        'shortest-ifl': _conv_lookup_act,
        'lsan-enforce-tags': _conv_lookup_act,
        'lsan-speed-tag': _conv_lookup_act,
        'migration-mode': _conv_lookup_act,
        'persistent-translate-domain-enabled': _conv_lookup_act,
    }),
    dict(k=brcdapi_util.bfr_efa, a=_fcr_update_act, m='PATCH', p='fcr', rw={
        'edge-fabric-id': _conv_lookup_act,
        'alias-name': _conv_lookup_act,
    }),
    dict(k=brcdapi_util.bfr_pc, a=_fcr_update_act, m='PATCH', p='fcr', rw={
        'imported-fabric-id': _conv_lookup_act,
        'device-wwn': _conv_lookup_act,
        'proxy-device-slot': _conv_lookup_act,
    }),
    dict(k=brcdapi_util.bfr_tdc, a=_fcr_update_act, m='PATCH', p='fcr', rw={
        'imported-fabric-id': _conv_lookup_act,
        'exported-fabric-id': _conv_lookup_act,
        'preferred-translate-domain-id': _conv_lookup_act,
    }),
    dict(k=brcdapi_util.bfr_std, a=_fcr_update_act, m='PATCH', p='fcr', rw={
        'imported-fabric-id': _conv_lookup_act,
        'stale-translate-domain-id': _conv_lookup_act,
    }),

    # Logical Switch: Trunking
    dict(k='brocade-fibrechannel-trunk/trunk-area', a=_switch_update_act, m='PATCH', p='fcr', rw={
        'trunk-index': _conv_lookup_act,
    }),

    # u: Users
    dict(k='brocade-security/user-config', a=_user_act, m='POST', p='u', rw={
        'name': _conv_lookup_act,
        'password': _default_user_pw_act,
        # 'role': _conv_lookup_act,  # In the Rest API Guide but not present in FOS
        'account-description': _conv_lookup_act,
        'account-enabled': _conv_lookup_act,
        'password-change-enforced': _true_act,
        # 'account-locked': _conv_lookup_act,  # FOS defect? I get an error no matter how I set this
        'access-start-time': _conv_lookup_act,
        'access-end-time': _conv_lookup_act,
        'home-virtual-fabric': _conv_lookup_act,
        'chassis-access-role': _conv_lookup_act,
        'virtual-fabric-role-id-list': _conv_lookup_act,
    }),
    dict(k='brocade-security/user-specific-password-cfg', a=_none_act, m='POST', p='u', skip=True),  # Not tested
    dict(k='brocade-security/auth-spec', a=_none_act, m='POST', p='sec', skip=True),  # Not tested
    dict(k='brocade-lldp/lldp-global', a=_switch_update_act, m='PATCH', p='sec', skip=True, rw={  # Not tested
        'multiplier': _conv_lookup_act,
        'tx-interval': _conv_lookup_act,
        'system-name': _conv_lookup_act,
        'system-description': _conv_lookup_act,
        'enabled-state': _conv_lookup_act,
        'optional-tlvs': _conv_lookup_act,
    }),
    dict(k='brocade-lldp/lldp-profile', a=_none_act, m='PATCH', p='sec', skip=True, rw={  # Not tested
        'name': _conv_lookup_act,
        'multiplier': _conv_lookup_act,
        'tx-interval': _conv_lookup_act,
        'enabled-tlvs': _conv_lookup_act,
    }),

    # Logging
    dict(k='brocade-logging/audit', a=_none_act, m='PATCH', p='l', skip=True, rw={  # Not tested
        'audit-enabled': _conv_lookup_act,
        'severity-level': _conv_lookup_act,
        'filter-class-list': _conv_lookup_act,
    }),
    dict(k='brocade-logging/syslog-server', a=_none_act, m='PATCH', p='sec', skip=True, rw={  # Not tested
        'server': _conv_lookup_act,
        'port': _conv_lookup_act,
        'secure-mode': _conv_lookup_act,
    }),
    dict(k='brocade-logging/raslog', a=_none_act, m='PATCH', p='sec', skip=True, rw={  # Not tested
        'audit-enabled': _conv_lookup_act,
        'severity-level': _conv_lookup_act,
        'filter-class-list': _conv_lookup_act,
    }),
    dict(k='brocade-logging/raslog-module', a=_none_act, m='PATCH', p='sec', skip=True, rw={  # Not tested
        'module-id': _conv_lookup_act,
        'log-enabled': _conv_lookup_act,
    }),
    dict(k='brocade-logging/log-quiet-control', a=_none_act, m='PATCH', p='sec', skip=True, rw={  # Not tested
        'log-type': _conv_lookup_act,
        'quiet-enabled': _conv_lookup_act,
        'start-time': _conv_lookup_act,
        'end-time': _conv_lookup_act,
        'days-of-week': _conv_lookup_act,
    }),
    dict(k='brocade-logging/log-setting', a=_none_act, m='PATCH', p='sec', skip=True, rw={  # Not tested
        'syslog-facility-level': _conv_lookup_act,
        'keep-alive-period': _conv_lookup_act,
        'clear-log': _conv_lookup_act,
    }),
    dict(k='brocade-logging/supportftp', a=_none_act, m='PATCH', p='sec', skip=True, rw={  # Not tested
        'host': _conv_lookup_act,
        'user-name': _conv_lookup_act,
        'password': _conv_lookup_act,
        'remote-directory': _conv_lookup_act,
        'auto-enabled': _conv_lookup_act,
        'protocol': _conv_lookup_act,
        'port': _conv_lookup_act,
        'connectivity-check-interval': _conv_lookup_act,
    }),

    # Logical Switch Configurations: brocade-fibrechannel-logical-switch/fibrechannel-logical-switch
    dict(k=brcdapi_util.bfls_uri, a=_switch_update_act, m='PATCH', rl='name', p='s',
         rw={  # domain-id and switch-user-friendly-name set in _restore_switches()
             'principal': _conv_lookup_act
         }),

    # Logical Switch Configurations: brocade-fibrechannel-switch/fibrechannel-switch
    dict(k=brcdapi_util.bfs_uri, a=_switch_update_act, m='PATCH', rl='name', p='s',
         rw={
             # 'domain-id': _conv_lookup_act,  # Done in _restore_switches()
             # 'user-friendly-name': _conv_lookup_act,  # Done in _restore_switches()
             # 'ip-address': _conv_lookup_act,  # Not changing the management IP interface
             # 'ip-static-gateway-list': _conv_lookup_act,  # Not changing the management IP interface
             # 'subnet-mask': _conv_lookup_act,  # Not changing the management IP interface
             # 'ipfc-address': _conv_lookup_act,  # Not changing the management IP interface
             # 'ipfc-subnet-mask': _conv_lookup_act,  # Not changing the management IP interface
             # 'domain-name': _conv_lookup_act,  # Not changing the management IP interface
             # 'dns-servers': _conv_lookup_act,  # Not changing the management IP interface
             'fabric-user-friendly-name': _conv_lookup_act,
             'ag-mode': _conv_lookup_act,
             'ag-mode-string': _conv_lookup_act,  # WIP
             'banner': _conv_lookup_act,
             'in-order-delivery-enabled': _conv_lookup_act,
             'dynamic-load-sharing': _conv_lookup_act,
             'advanced-performance-tuning-policy': _conv_lookup_act,
             'lacp-system-priority': _conv_lookup_act,
             'switch-persistent-enabled': _conv_lookup_act,
         }),
    dict(k=brcdapi_util.bfc_sw_uri, a=_switch_update_act, m='PATCH', rl='name', p='s',
         rw={
             'trunk-enabled': _conv_lookup_act,
             'wwn-port-id-mode': _conv_lookup_act,
             'edge-hold-time': _conv_lookup_act,
             'area-mode': _conv_lookup_act,
             'xisl-enabled': _conv_lookup_act,
         }),
    dict(k=brcdapi_util.bfcfp_uri, a=_switch_update_act, m='PATCH', rl='name', p='s',
         rw={
             'max-logins': _conv_lookup_act,
             'max-flogi-rate-per-switch': _conv_lookup_act,
             'stage-interval': _conv_lookup_act,
             'free-fdisc': _conv_lookup_act,
             'enforce-login': _conv_lookup_act,
             'enforce-login-string': _conv_none_act,
             'max-flogi-rate-per-port': _conv_lookup_act,
         }),
    dict(k=brcdapi_util.bfc_port_uri, a=_switch_update_act, m='PATCH', rl='name', p='s',
         rw={
             'portname-mode': _conv_lookup_act,
             'dynamic-portname-format': _conv_lookup_act,
             'dynamic-d-port-enabled': _conv_lookup_act,
             'on-demand-d-port-enabled': _conv_lookup_act,
         }),
    dict(k='brocade-fibrechannel-configuration/zone-configuration', a=_switch_update_act, m='PATCH', rl='name', p='s',
         rw={
             'node-name-zoning-enabled': _conv_lookup_act,
             'fabric-lock-timeout': _conv_lookup_act,
         }),
    dict(k=brcdapi_util.bfc_uri, a=_switch_update_act, m='PATCH', rl='name', p='s', rw={
        'insistent-domain-id-enabled': _conv_ficon_lookup_act,
        'principal-selection-enabled': _conv_lookup_act,
        'principal-priority': _conv_lookup_act,
        'preserved-domain-id-mode-enabled': _conv_lookup_act,
    }),

    # MAPS
    dict(k=brcdapi_util.maps_rule, a=_maps_act, m='PATCH', p='maps', rw={
        'name': _conv_lookup_act,
        'is-rule-on-rule': _conv_lookup_act,
        'monitoring-system': _conv_lookup_act,
        'time-base': _conv_lookup_act,
        'logical-operator': _conv_lookup_act,
        'threshold-value': _conv_lookup_act,
        'actions': _conv_lookup_act,
        'event-severity': _conv_lookup_act,
        'toggle-time': _conv_lookup_act,
        'quiet-time': _conv_lookup_act,
        'un-quarantine-timeout': _conv_lookup_act,
        'un-quarantine-clear': _conv_lookup_act,
    }),

    # Logical Switch: FICON
    dict(k=brcdapi_util.ficon_cup_uri, a=_switch_update_act, m='PATCH', p='ficon', rw={
        'fmsmode-enabled': _conv_lookup_act,
        'programmed-offline-state-control': _conv_lookup_act,
        'active-equal-saved-mode': _conv_lookup_act,
        'director-clock-alert-mode': _conv_lookup_act,
        'unsolicited-alert-mode-fru-enabled': _conv_lookup_act,
        'unsolicited-alert-mode-hsc-enabled': _conv_lookup_act,
        'unsolicited-alert-mode-invalid-attach-enabled': _conv_lookup_act,
    }),
    dict(k='brocade-ficon/logical-path', a=_switch_update_act, m='PATCH', p='ficon', rw={
        'link-address': _conv_lookup_act,
        'channel-image-id': _conv_lookup_act,
        'reporting-path-state': _conv_lookup_act,
    }),

    # Logical Switch Port Configurations: FCIP
    dict(k='brocade-interface/extension-ip-interface', a=_switch_update_act, m='PATCH', p='fcip', rw={
        'name': _conv_lookup_act,
        'dp-id': _conv_lookup_act,
        'ip-address': _conv_lookup_act,
        'ip-prefix-length': _conv_lookup_act,
        'mtu-siz': _conv_lookup_act,
        'vlan-id': _conv_lookup_act,
    }),

    # Port Configurations: General port configurations
    # Some port configurations require the port to be reserved so do that first
    dict(k=brcdapi_util.bifc_uri, a=_port_update_act, rl='ports', m='PATCH', p='p', rw={
        'pod-license-state': _conv_lookup_act,
    }),
    dict(k='fos_cli/portcfgshow', a=_port_cli_update_act, p='p'),
    dict(a=_port_cli_wait_act, p='p', e='CLI wait'),
    dict(a=_data_clear, e='_data_clear 3', p='p'),
    dict(a=_data_capture, rl=_full_capture_l, e='Full Capture', p='p'),
    dict(k=brcdapi_util.bifc_uri, a=_port_update_act, rl='ports', m='PATCH', p='p', rw={
        'application-header-enabled': _conv_lookup_act,
        'clean-address-enabled': _conv_lookup_act,
        'compression-configured': _conv_lookup_act,
        'congestion-signal-enabled': _conv_lookup_act,
        'credit-recovery-enabled': _conv_lookup_act,
        'csctl-mode-enabled': _conv_lookup_act,
        'd-port-enable': _conv_lookup_act,
        'e-port-credit': _conv_lookup_act,
        'e-port-disable': _conv_lookup_act,
        'edge-fabric-id': _conv_lookup_act,
        'encryption-enabled': _conv_lookup_act,
        'ex-port-enabled': _conv_lookup_act,
        'f-port-buffers': _conv_lookup_act,
        'fault-delay-enabled': _conv_lookup_act,
        'fc-router-port-cost': _conv_lookup_act,
        'fec-enabled': _conv_lookup_act,
        'g-port-locked': _conv_lookup_act,
        'isl-ready-mode-enabled': _conv_lookup_act,
        'los-tov-mode-enabled': _conv_lookup_act,
        # 'los-tov-mode-enabled-string': _conv_none_act,
        'mirror-port-enabled': _conv_lookup_act,
        'ms-acl-application-server-access': _conv_lookup_act,
        'ms-acl-enhanced-fabric-configuration-server-access': _conv_lookup_act,
        'ms-acl-fabric-configuration-server-access': _conv_lookup_act,
        'ms-acl-fabric-device-management-interface-access': _conv_lookup_act,
        'ms-acl-fabric-zone-server-access': _conv_lookup_act,
        'ms-acl-unzoned-name-server-access': _conv_lookup_act,
        'n-port-enabled': _conv_lookup_act,
        'npiv-enabled': _conv_lookup_act,
        'npiv-pp-limit': _conv_lookup_act,
        'octet-speed-combo': _conv_lookup_act,
        # 'octet-speed-combo-string': _conv_none_act,
        'persistent-disable': _conv_lookup_act,
        'port-autodisable-enabled': _conv_lookup_act,
        # 'port-generation-number': _conv_none_act,  # Relevant for rebuild?
        'port-peer-beacon-enabled': _conv_lookup_act,
        # 'port-scn': _conv_none_act,  # Relevant for rebuild?
        # 'preferred-front-domain-id': _conv_lookup_act,
        # 'protocol-speed': _conv_lookup_act,
        'qos-enabled': _conv_lookup_act,
        'rscn-suppression-enabled': _conv_lookup_act,
        'sim-port-enabled': _conv_lookup_act,
        'speed': _conv_lookup_act,
        'target-driven-zoning-enable': _conv_lookup_act,
        'trunk-port-enabled': _conv_lookup_act,
        'user-friendly-name': _conv_lookup_act,
    }),
    dict(k='brocade-interface/gigabitethernet', a=_port_update_act, rl='ge_ports', m='PATCH', p='p', rw={
        'name': _conv_lookup_act,
        'speed': _conv_lookup_act,
        'protocol-speed': _conv_none_act,
        'persistent-disable': _conv_lookup_act,
        'protocol': _conv_lookup_act,
        'auto-negotiation-enabled': _conv_lookup_act,
        'portchannel-member-timeout': _conv_lookup_act,
        'lldp-profile': _conv_lookup_act,
        'lldp-enabled-state': _conv_lookup_act,
    }),
    dict(k='brocade-interface/portchannel', a=_port_update_act, rl='ports', m='PATCH', p='p', rw={
        'name': _conv_lookup_act,
        'key': _conv_lookup_act,
        'portchannel-type': _conv_lookup_act,
        'admin-state-enabled': _conv_lookup_act,
        'auto-negotiation-enabled': _conv_lookup_act,
        'gigabit-ethernet-member-ports': _conv_lookup_act,
    }),

    # Zone configuration enable
    dict(a=_zone_enable, e='_zone_enable', p='ze'),

    # Zoning
    dict(a=_zone_restore, e='_zone_restore', p='z'),

    # Enable
    dict(a=_enable, e='_enable', p='e'),

]
for _d in _action_l:
    if 'e' not in _d:
        _d.update(e=str(_d.get('k')))


def pseudo_main(ip, user_id, pw, sec, r_proj_obj, r_chassis_obj, act_d, args_fm, args_cli, args_scan):
    """Basically the main(). Did it this way, so it can easily be used as a standalone module or called from another.

    :param ip: IP address of chassis to modify
    :type ip: str
    :param user_id: Login user ID
    :type user_id: str
    :param pw: Login password
    :type pw: str
    :param sec: 'none' for HTTP or 'self' for HTTPS
    :type sec: str
    :param r_proj_obj: Restore project object from -i
    :type r_proj_obj: brcddb.classes.project.ProjectObj
    :param r_chassis_obj: Chassis object to restore from
    :type r_chassis_obj: brcddb.classes.chassis.ChassisObj
    :param act_d: Restore actions
    :type act_d: dict
    :param args_fm: FID map as entered on the command line
    :type args_fm: str
    :param args_cli: Name of CLI output file
    :type args_cli: str
    :param args_scan: Scan flag
    :type args_scan: bool
    :return: Exit code. See exit codes in brcddb.brcddb_common
    :rtype: int
    """
    global _basic_capture_kpi_l, _full_capture_l, _action_l, _temp_password, _all_fos_cli_l, _scan_action_l

    ec, el, fid_map_d = brcddb_common.EXIT_STATUS_OK, list(), dict()
    action_l = _scan_action_l if args_scan else\
        [d for d in _action_l if not d.get('skip', False) and act_d.get(d['p'], False)]

    # Get a project object and some basic info for the chassis to be modified
    t_proj_obj = brcddb_project.new('Chassis to be modified', datetime.datetime.now().strftime('%d %b %Y %H:%M:%S'))
    t_proj_obj.s_python_version(sys.version)
    t_proj_obj.s_description('Scan' if r_chassis_obj is None else r_chassis_obj.r_project_obj().r_description())

    # Figure out what data to capture
    skip_p = False
    for d in action_l:
        if not d.get('skip', False):
            if not skip_p and str(d.get('p')) == 'p':
                _full_capture_l.extend(_all_fos_cli_l)
                skip_p = True
            key = d.get('k')
            if isinstance(key, str):
                for sub_key in [k for k in key.split(',') if k not in _full_capture_l]:
                    buf = sub_key if 'fos_cli' in sub_key else 'running/' + sub_key
                    _full_capture_l.append(buf)

    # Initialize the control data structure
    summary_d = dict()
    summary_d['chassis'] = collections.OrderedDict()
    summary_d['chassis']['Users'] = list()
    summary_d['chassis']['VF Enable'] = False
    local_control_d = dict(type='local_control_d',  # Search for local_control_d in header for description
                           args_fm=args_fm,
                           t_proj_obj=t_proj_obj,
                           r_proj_obj=r_proj_obj,
                           r_chassis_obj=r_chassis_obj,
                           r_default_fid=None if r_chassis_obj is None else r_chassis_obj.r_default_switch_fid(),
                           act_d=act_d,
                           fid_map_d=fid_map_d,
                           args_cli=args_cli,
                           summary=summary_d)

    # Login
    session = None
    if user_id is not None and pw is not None and ip is not None:
        session = api_int.login(user_id, pw, ip, sec, proj_obj=t_proj_obj)
        if fos_auth.is_error(session):
            brcdapi_log.log(fos_auth.formatted_error_msg(session), echo=True)
            return brcddb_common.EXIT_STATUS_ERROR
    local_control_d.update(session=session)

    d = dict()
    try:
        step = 0
        for d in action_l:
            brcdapi_log.log('step: ' + str(step) + ', restore action: ' + d['e'], echo=True)

            # Debug
            # if step == 1:
            #     print('TP_100')

            temp_el = d['a'](local_control_d, d)
            el.extend(temp_el)
            step += 1

            # Debug
            if _DEBUG and len(temp_el) > 0:
                brcdapi_log.log(['DEBUG len(el): ' + str(len(temp_el))] + temp_el, echo=True)

    except FIDMapError:
        ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
        el.extend(_data_collect_error_l)
    except KeyboardInterrupt:
        ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
        el.append('Processing terminated by user.')
    except RuntimeError:
        ec = brcddb_common.EXIT_STATUS_API_ERROR
        el.append('Programming error encountered while processing ' + str(d.get('e')) + 'See previous message')
    except brcdapi_util.VirtualFabricIdError:
        ec = brcddb_common.EXIT_STATUS_API_ERROR
        el.append('Software error. Search the log for "Invalid FID" for details.')
    except BaseException as e:
        ec = brcddb_common.EXIT_STATUS_ERROR
        el.extend(['Software error while processing:'] + _fmt_errors(d.get('e')))
        el.append(str(type(e)) + ': ' + str(e))

    # Logout
    if session is not None:
        obj = brcdapi_rest.logout(session)
        if fos_auth.is_error(obj):
            el.append(fos_auth.formatted_error_msg(obj))

    # Wrap up messages
    if len(el) > 0:
        for buf in ('_____________', 'Scan Output:' if args_scan else 'Error Detail:', ''):
            el.insert(0, buf)
    el.extend(['', 'Chassis Summary', '_______________'])
    for k, v in local_control_d['summary']['chassis'].items():
        buf = ''
        if k == 'Users':
            if len(buf) == 0:
                buf = 'None'
            else:
                buf += '\n            '.join(local_control_d['summary']['chassis']['Users'])
        else:
            buf = '\n            '.join(v) if isinstance(v, list) else str(v)
        el.append(gen_util.pad_string(str(k) + ':', 12, ' ', append=True) + buf)
    el.extend(['', 'Switch Summary', '_______________'])
    for switch_name, d in local_control_d['summary'].items():
        if switch_name != 'chassis':
            el.extend(['', switch_name])
            for k, v in d.items():
                buf = ','.join(v) if isinstance(v, list) else str(v)
                el.append('  ' + gen_util.pad_string(str(k) + ':', 20, ' ', append=True) + buf)
    brcdapi_log.log(el, echo=True)

    return ec


def _get_input():
    """Retrieves the command line input, reads the input Workbook, and validates the input

    :return ec: Error code from brcddb.brcddb_common
    :rtype ec: int
    """
    global __version__, _input_d, _eh

    # Initialize the variables for the call to pseudo_main()
    proj_obj, chassis_obj, args_p_d, ec = None, None, dict(), brcddb_common.EXIT_STATUS_OK

    # Get command line input
    buf = 'Restores a chassis configuration to a previous configuration. Intended to be used as a template'
    args_d = gen_util.get_input(buf, _input_d)
    args_d['i'] = brcdapi_file.full_file_name(args_d['i'], '.json')
    args_d['cli'] = None if args_d.get('cli') is None else brcdapi_file.full_file_name(args_d['cli'], '.txt')

    # Set up logging
    brcdapi_rest.verbose_debug(args_d['d'])
    brcdapi_log.open_log(
        folder=args_d['log'],
        suppress=args_d['sup'],
        no_log=args_d['nl'],
        version_d=brcdapi_util.get_import_modules()
    )

    # User feedback
    ml = [os.path.basename(__file__) + ', ' + __version__,
          'IP address, -ip:         ' + brcdapi_util.mask_ip_addr(args_d['ip']),
          'ID, -id:                 ' + str(args_d['id']),
          'HTTPS, -s:               ' + str(args_d['s']),
          'Input file, -i:          ' + str(args_d['i']),
          'WWN, -wwn:               ' + str(args_d['wwn']),
          'FID Map, -fm:            ' + str(args_d['fm']),
          'Option parameters, -p:   ' + str(args_d['p']),
          'Scan, -scan:             ' + str(args_d['scan']),
          'CLI file name, -cli:     ' + str(args_d['cli']),
          'Extended help, -eh:      ' + str(args_d['eh']),
          'Log, -log:               ' + str(args_d['log']),
          'No log, -nl:             ' + str(args_d['nl']),
          'Debug, -d:               ' + str(args_d['d']),
          'Suppress, -sup:          ' + str(args_d['sup']),
          '']
    brcdapi_log.log(ml, echo=True)

    # Validate the input.
    ml = list()
    if args_d['cli'] is not None:
        ml.append('The -cli option is a future consideration. It is not supported in this release.')
    if args_d['eh']:
        for d in _eh:
            ml.extend(gen_util.wrap_text(d['b'], _MAX_LINE_LEN, d.get('p')))
    elif not args_d['scan'] and args_d['cli'] is None:
        for k, v in dict(ip=args_d['ip'], id=args_d['id'], pw=args_d['pw'], i=args_d['i'], p=args_d['p']).items():
            if v is None:
                ml.append('Missing -' + k + '. Re-run with -h or -eh for additional help.')

    proj_obj, chassis_obj, chassis_obj_l = None, None, list()
    if len(ml) == 0:
        # Read the project file
        if isinstance(args_d['i'], str):
            try:
                proj_obj = brcddb_project.read_from(args_d['i'])
                if proj_obj is None:
                    ml.append('File, -i, appears to be corrupted: ' + args_d['i'])
                else:
                    chassis_obj_l = proj_obj.r_chassis_objects()
            except (FileExistsError, FileNotFoundError):
                ml.append('Input file, -i, not found: ' + args_d['i'])
            if not args_d['scan']:
                if args_d['wwn'] is not None:
                    chassis_obj = proj_obj.r_chassis_obj(args_d['wwn'])
                    if chassis_obj is None:
                        ml.append('Could not find a chassis matching ' + args_d['wwn'] + ' in ' + str(args_d['i']))
                else:
                    num_chassis = len(chassis_obj_l)
                    if num_chassis == 0:
                        ml.append('There are no chassis in the input file, -i: ' + str(args_d['i']))
                    elif num_chassis == 1:
                        chassis_obj = chassis_obj_l[0]
                    else:
                        ml.extend(['Multiple chassis found in ' + args_d['i'],
                                   'Specify with the chassis to restore from using the -wwn option.',
                                   'Re-run with -scan for a list of available chassis.'])

        # Get and validate the list of actions, -p
        if not args_d['scan'] and args_d['cli'] is None:
            if isinstance(args_d['p'], str):
                for p in _restore_parameters.keys():
                    args_p_d.update({p: False})
                args_p_l = [str(k) for k in _restore_parameters.keys()] if '*' in args_d['p'] else \
                    gen_util.remove_duplicates(args_d['p'].split(',') + ['m'])
                for p in args_p_l:
                    if p not in args_p_d:
                        ml.append('Unknown parameter, ' + p + ', in option parameters, -p')
                    else:
                        args_p_d[p] = True
            else:
                ml.append('Missing parameter -p')

    if len(ml) > 0:
        brcdapi_log.log(ml, echo=True)
        ec = brcddb_common.EXIT_STATUS_INPUT_ERROR

    if ec != brcddb_common.EXIT_STATUS_OK:
        return ec

    signal.signal(signal.SIGINT, brcdapi_rest.control_c)
    return pseudo_main(args_d['ip'], args_d['id'], args_d['pw'], args_d['s'], proj_obj, chassis_obj, args_p_d,
                       args_d['fm'], args_d['cli'], args_d['scan'])


##################################################################
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
