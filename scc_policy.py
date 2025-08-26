#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Copyright 2025 Consoli Solutions, LLC.  All rights reserved.

**License**

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
the License. You may also obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
language governing permissions and limitations under the License.

The license is free for single customer use (internal applications). Use of this module in the production,
redistribution, or service delivery for commerce requires an additional license. Contact jack_consoli@yahoo.com for
details.

**Description**

Creates, modifies, and distributes and SCC_POLICY

**Important Programming Note**

During development, I ran into a FOS issue whereby an SCC_POLICY could not be defined or activated in a non-FICON
switch. When I first ran into the problem, I noticed a discrepancy between secpolicyshow and reading the membership
lists via the API. Having run into sync issues between the CLI and the API before, I tried logging out and back in. That
didn't work. I then tried the CLI which had problems as well. The script was working fine on logical switches defined as
FICON. Other than the problem with non-FICON logical switches, final test was successful, so I did not go back and
remove all the logging in and out. As a result, the script runs slower than it could. Given the nature of how this
script is used, taking less than a minute longer wasn't an issue, so I left it alone.

**SCC_POLICY Notes**

The SCC_POLICY defines a list of switches, by WWN, that are allowed to join the fabric. The SCC_POLICY is stored in each
switch. Anytime another switch is connected, the WWN of that switch is checked against the SCC_POLICY. If the WWN of
that is not in the SCC_POLICY membership list, the connection is rejected and that switch is not allowed to join the
fabric. Since a switch with an SCC_POLICY must be able to join its own fabric, an SCC_POLICY must contain at least the
WWN of the host switch.

An SCC_POLICY is used primarily for FICON environments. FICON is a protocol used by mainframes. It is rare, if ever,
that an SCC_POLICY is used in any fabric other than a mainframe environment.

An SCC_POLICY is required anytime a mainframe channel with 2-byte addressing defined logs into the switch. If an
SCC_POLICY is not active, the mainframe I/O system puts the channel in an “Invalid Attached” state. In the “Invalid
Attached” state, CHPIDs cannot use the channel. This is a security feature to ensure that unauthorized switches cannot
join the fabric.

As with zoning, changes to the SCC_POLICY are made in a buffer. This buffer is referred to as the defined SCC_POLICY.
Unlike zoning, however, changes cannot be aborted. Changes are automatically saved to the defined membership list. It is
not in effect until it is distributed to the fabric. Once it is distributed to the fabric, additional changes must be
activated.

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 1.0.0     | 25 Aug 2025   | Initial launch                                                                        |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2025 Consoli Solutions, LLC'
__date__ = '25 Aug 2025'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '1.0.0'

import sys
import datetime
import os
import time
import brcdapi.log as brcdapi_log
import brcdapi.fos_auth as fos_auth
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.util as brcdapi_util
import brcdapi.file as brcdapi_file
import brcdapi.excel_util as excel_util
import brcdapi.gen_util as gen_util
import brcddb.brcddb_project as brcddb_project
import brcddb.brcddb_common as brcddb_common
import brcddb.brcddb_chassis as brcddb_chassis
import brcddb.brcddb_switch as brcddb_switch
import brcddb.api.interface as api_int
import brcddb.util.compare as brcddb_compare

_DOC_STRING = False  # Should always be False. Prohibits any code execution. Only useful for building documentation
# _STAND_ALONE: True: Executes as a standalone module taking input from the command line. False: Does not automatically
# execute. This is useful when importing this module into another module that calls psuedo_main().
_STAND_ALONE = True  # See note above

_input_d = dict(
    i=dict(h='Required. Workbook with SCC policy instructions. See zone_merge_sample.xlsx for details. ".xlsx" is '
             'automatically appended. zone_merge_sample.xlsx is not a mistake. The same workbook is used for setting '
             'the SCC policy. Only cells in columns "user_id", "pw", "ip_addr", "security", and "fid" are read. All '
             'other cells are ignored.'),
    sheet=dict(h='Required. Specifies the sheet name in the workbook specified with -i to be used.'),
    add=dict(r=False,
             h='Optional. List of switch WWNs to add to the SCC_POLICY. The intended purpose is to add members to the '
               'SCC_POLICY for switches that are not accessible.'),
    remove=dict(r=False,
                h='Optional. List of switch WWNs to remove from the SCC_POLICY.'),
    clr=dict(r=False, t='bool', d=False,
             h='Optional. No parameters. By default, WWNs are added to the existing SCC_POLICY membership list. When'
               '-clr is specified, the existing policy is cleared and replaced.'),
    api=dict(r=False, t='bool', d=False,
             h='Optional. No parameters. By default, only the equivalent CLI commands are output. This option '
               'instructs the script to make the changes via the API as well.'),
    activate=dict(r=False, t='bool', d=False,
                  h='Optional. No parameters. Only used when -api is set. Typically set when -api is set. When set, '
                    'the SCC_POLICY is activated in the fabric. Equivalent to the FOS CLI command '
                    '"fddcfg --fabwideset".'),
)
_input_d.update(gen_util.parseargs_log_d.copy())
_input_d.update(gen_util.parseargs_debug_d.copy())

# Time in seconds to sleep between logging in and logging out. In some cases, FOS gets a little wierd. The only way to
# pickup changes is to log out and back in
_WAIT_TIME = 3
_check_login_l = ('user_id', 'pw', 'ip_addr', 'fid')
_row_str = '0'  # Global so that if an exception occurs, we know what row we were working on.

_basic_capture_uris = (
    'running/brocade-fibrechannel-switch/fibrechannel-switch',
    'running/brocade-interface/fibrechannel',
    'running/brocade-fibrechannel-configuration/fabric',
    'running/brocade-security/policy-distribution-config',
    'running/brocade-security/active-scc-policy-member-list',
    'running/brocade-security/defined-scc-policy-member-list',
)
_scc_policy_capture_uris = (
    'running/brocade-security/policy-distribution-config',
    'running/brocade-security/active-scc-policy-member-list',
    'running/brocade-security/defined-scc-policy-member-list',
)

_cli_l = [
    '',
    '# Equivalent CLI Commands',
    '# Some commands require a response, so copy and paste one at a time.',
    '# The typical use case for this script is when merging single switch fabrics.',
    '# In that case, you will simply copy and paste these commands into a CLI session.',
    '# Since some commands operate on all switches in the fabric, you may need to use',
    '# secpolicyshow to determine which commands and members are necessary when merging',
    '# fabrics that have multiple switches.'
    '',
    '$switch',  # Insert the individual switch commands here.
    '# Tips & Validation',
    '# All switches should have these, and only these, WWNs in the SCC_POLICY:'
    '$scc_wwn_l',  # Insert the expected membership list here.
    '',
    '# Useful commands:',
    'setcontext fid',
    'secpolicyshow',
    'secpolicycreate "SCC_POLICY" "wwn_1;wwn_2"',
    'secpolicyadd "SCC_POLICY" "wwn_1;wwn_2"',
    'secpolicyremove "SCC_POLICY" "wwn_1;wwn_2"',
    'secpolicyabort',
    'secpolicysave',
    'fddcfg --fabwideset "SCC:S"',
    '',
]


class HaltProcessing(Exception):
    pass


def _compare_membership(hdr, title_a, a_l, title_b, b_l, disp=True):
    """Compares two lists. If different, prints the formatted differences to the log

    :param hdr: Header for report when a_l != b_l
    :type hdr: None, str, list
    :param title_a: Report title for a_l if a_l != b_l
    :type title_a: None, str
    :param a_l: Membership list to compare against b_l
    :type a_l: list
    :param title_b: Report title for b_l if a_l != b_l
    :type title_b: None, str
    :param b_l: Membership list to compare against a_l
    :type b_l: list
    :param title_b: Report title for b_l if a_l != b_l
    :param disp: Display report if there is a mismatch.
    :type disp: bool
    :return: True if the membership lists match
    :rtype: bool
    """
    r_val = gen_util.compare_lists(a_l, b_l)
    if not r_val and disp:
        buf_l = gen_util.convert_to_list(hdr)
        if isinstance(title_a, str):
            buf_l.append(title_a)
        buf_l.extend(['  ' + buf for buf in a_l])
        if isinstance(title_b, str):
            buf_l.append(title_b)
        buf_l.extend(['  ' + buf for buf in b_l])
        brcdapi_log.log(buf_l, echo=True)

    return r_val


def _login_and_capture(proj_obj, row_str, ip_addr, user_id, pw, sec):
    """ Login and capture SCC policy data

    :param proj_obj: Project object
    :type proj_obj: brcddb.classes.project.ProjectObj
    :param row_str: Row number as text. Used for error messages
    :type row_str: str
    :param ip_addr: IP address
    :type ip_addr: str
    :param user_id: User ID
    :type user_id: str
    :param pw: Password
    :type pw: str
    :param sec: Type of HTTP security. Should be 'none' or 'self'
    :type sec: str
    :return ec: Exit status code. See brcddb_common.EXIT_STATUS for details
    :rtype ec: int
    :return session: Login session object
    :rtype session: dict
    :return chassis_obj: Chassis object
    :rtype chassis_obj: brcddb.classes.chassis.ChassisObj
    """
    global _basic_capture_uris

    chassis_wwn_d = dict()
    # I'm going to let api_int.get_batch() capture everything I need. Below gets a list of chassis keys already
    # captured. The one that isn't in this dictionary when I'm done is the new one.
    for wwn in proj_obj.r_chassis_keys():
        chassis_wwn_d[wwn] = True

    # Login
    session = api_int.login(user_id, pw, ip_addr, sec, proj_obj)
    if fos_auth.is_error(session):
        brcdapi_log.log(
            ['Row ' + row_str + ': ' + 'Login failed. Error message is:', fos_auth.formatted_error_msg(session)],
            echo=True)
        return brcddb_common.EXIT_STATUS_API_ERROR, session, None

    # Collect the data
    api_int.get_batch(session, proj_obj, _basic_capture_uris + _scc_policy_capture_uris)

    # Figure out which chassis object is the one we just collected.
    for chassis_obj in proj_obj.r_chassis_objects():
        if chassis_obj.r_obj_key() not in chassis_wwn_d:
            return brcddb_common.EXIT_STATUS_OK, session, chassis_obj

    # If we fell out of the for loop above, the chassis object couldn't be found
    brcdapi_log.log(
        'Error encountered collecting chassis data: ' + brcdapi_util.mask_ip_addr(ip_addr, keep_last=True),
        echo=True
    )

    return brcddb_common.EXIT_STATUS_API_ERROR, session, None


def _evaluate_scc(switch_obj, scc_wwn_l):
    """Determines if the SCC_POLICY needs to be created, what WWNs need to be added to the membership list, and which
    WWNs need to be removed from the membership list. This information is added to the switch object in a dictionary
    named scc_policy_d. scc_policy_d is defined as follows:
    
    +---------------+-------+---------------------------------------------------------------------------------------+
    | Key           | Type  | Description                                                                           |
    +===============+=======+=======================================================================================+
    | add_l         | list  | List of WWNs that need to be added to the membership list.                            |                 
    +---------------+-------+---------------------------------------------------------------------------------------+
    | create_bool   | bool  | If True, the SCC_POLICY does not exist and therefore needs to be created.             |
    +---------------+-------+---------------------------------------------------------------------------------------+
    | fabwide_bool  | bool  | If True, the SCC_POLICY has not been distributed to the fabric and therefore needs to |
    |               |       | added.                                                                                |
    +---------------+-------+---------------------------------------------------------------------------------------+
    | remove_l      | list  | List of WWNs that need to be removed from the membership list.                        |
    +---------------+-------+---------------------------------------------------------------------------------------+
    | defined       | str   | Status of changes to the defined SCC_POLICY membership list. Possible values are:     |
    |               |       |   'not_attempted': Not attempted yet.                                                 |
    |               |       |   'success': Successfully updated.                                                    |
    |               |       |   'fail': Failed to update.                                                           |
    |               |       |   'match': No need to change.                                                         |
    |               |       |   'create_success': Successfully created.                                             |
    |               |       |   'create_fail': Failed to create.                                                    |
    |               |       |   'skip': Skipped due to previous errors. Used with activated only                    |
    |               |       |   'no_activate': Skipped because -activate not specified. Used with activated only.   |
    +---------------+-------+---------------------------------------------------------------------------------------+
    | activated     | str   | Status of changes to the activated SCC_POLICY membership list. See "defined" for      |
    |               | str   | possible values.                                                                      |
    +---------------+-------+---------------------------------------------------------------------------------------+

    :param switch_obj: Switch object
    :type switch_obj: brcddb.class.switch.SwitchObj
    :param scc_wwn_l: SCC_POLICY membership
    :type scc_wwn_l: list
    :return: Dictionary as described above
    :rtype: dict
    """
    # full_scc_wwn_d is so that I don't have to spin the list everytime. As a practical matter, this list will be so
    # small that the performance difference will be insignificant. I just did this out of force of habit. Rather than
    # back it out after I tested the code, I left it in and added this comment.
    full_scc_wwn_d = dict()
    for wwn in scc_wwn_l:
        full_scc_wwn_d[wwn] = True
        
    scc_policy_d = dict(
        create_bool=False,
        fabwide_bool=False,
        add_l=list(),
        remove_l=list(),
        defined='not_attempted',  # See above
        activated='not_attempted'  # See as above
    )

    # Determine if the policy needs to be created, pushed to the fabric, and what members to add and remove.
    defined_scc_l = switch_obj.r_defined_scc(list())
    if len(defined_scc_l) == 0:
        scc_policy_d['create_bool'] = True
        scc_policy_d['fabwide_bool'] = True
        scc_policy_d['add_l'] = scc_wwn_l
    else:
        defined_scc_d = dict()
        for wwn in defined_scc_l:
            defined_scc_d[wwn] = True
        scc_policy_d['add_l'] = [wwn for wwn in scc_wwn_l if wwn not in defined_scc_d]
        scc_policy_d['remove_l'] = [wwn for wwn in defined_scc_l if wwn not in full_scc_wwn_d]
        if len(switch_obj.r_active_scc(list())) == 0:
            scc_policy_d['fabwide_bool'] = True

    return scc_policy_d


def _generate_cli(switch_obj_l, scc_wwn_l):
    """Creates a list of CLI commands to copy and paste into an SSH session.

    :param switch_obj_l: Switch objects: brcddb.class.switch.SwitchObj
    :type switch_obj_l: list
    :param scc_wwn_l: Expected defined SCC_POLICY membership
    :type scc_wwn_l: list
    :return: CLI commands to make the modifications to the SCC_POLICY
    :rtype: list
    """
    global _cli_l, _row_str

    cli_l = list()
    for buf in _cli_l:

        if buf == '$switch':

            for switch_obj in switch_obj_l:
                _row_str = switch_obj.r_chassis_obj().r_get('scc_login_d/row_str')
                # See _evaluate_scc() for a definition of scc_d.
                scc_d = switch_obj.r_get('initial_scc_policy_d')
                temp_cli_l = list()
                comment = '# Chassis: ' + brcddb_chassis.best_chassis_name(switch_obj.r_chassis_obj()) + ', Switch: '
                comment += brcddb_switch.best_switch_name(switch_obj, fid=True, did=True, wwn=True)
    
                if scc_d['create_bool']:
                    temp_cli_l.append('secpolicycreate "SCC_POLICY" "' + ';'.join(scc_d['add_l']) + '"')
                else:
                    if len(scc_d['add_l']) > 0:
                        temp_cli_l.append('secpolicyadd "SCC_POLICY" "' + ';'.join(scc_d['add_l']) + '"')
                    if len(scc_d['remove_l']) > 0:
                        temp_cli_l.append('secpolicyremove "SCC_POLICY" "' + ';'.join(scc_d['remove_l']) + '"')
                active_scc_l = switch_obj.r_active_scc(list())
                defined_scc_l = switch_obj.r_defined_scc(list())
                if _compare_membership(None, None, active_scc_l, None, defined_scc_l, disp=False):
                    temp_cli_l.append('# Active SCC_POLICY matches defined SCC_POLICY. No changes required.')
                else:
                    if len(active_scc_l) > 0:
                        temp_cli_l.append('secpolicyactivate')
                    else:
                        if len(temp_cli_l) > 0:
                            temp_cli_l.append('secpolicysave')
                        temp_cli_l.append('fddcfg --fabwideset "SCC:S"')

                # Wrap up
                if len(temp_cli_l) == 0:
                    temp_cli_l.append('# No changes to the SCC_POLICY required.')
                else:
                    temp_cli_l.insert(0, 'setcontext ' + str(switch_obj.r_fid()))
                    temp_cli_l.append('secpolicyshow')
                temp_cli_l.insert(0, comment)
                temp_cli_l.append('')
                cli_l.extend(temp_cli_l)

        elif buf == '$scc_wwn_l':
            for wwn in scc_wwn_l:
                cli_l.append('# ' + wwn)

        else:
            cli_l.append(buf)

    return cli_l


_summary_d = dict(  # Used in _summary()
    create_fail='Failed to create.',
    create_success='Successfully created.',
    fail='Failed to update.',
    match='Already matched.',
    no_activate='Not attempted. -activate not specified.',
    not_attempted='Not attempted.',
    skip='Skipped due to previous errors.',
    success='Successfully updated.',
    validation_fail='Failed final validation check.',
)


def _summary(args_d, switch_obj_l):
    """ Returns a list of text that summarizes the actions taken

    :param args_d: Parsed arguments. See _input_d for details.
    :type args_d: dict
    :param switch_obj_l: Switch objects: brcddb.class.switch.SwitchObj
    :type switch_obj_l: list
    :return: Summary of actions taken
    :rtype: list
    """
    global _summary_d

    summary_l = ['', 'Summary']

    if args_d['api']:
        # Get a list of successes and failures by switch
        for switch_obj in switch_obj_l:
            summary_l.append(brcddb_switch.best_switch_name(switch_obj, did=True, wwn=True, fid=True))
            scc_policy_d = switch_obj.r_get('scc_policy_d')
            summary_l.append('  Defined SCC_POLICY: ' + _summary_d[scc_policy_d['defined']])
            summary_l.append('  Active SCC_POLICY:  ' + _summary_d[scc_policy_d['activated']])
    else:
        summary_l.append('-api not specified. No actions taken.')

    return summary_l


def _define_activate_scc_policy(switch_obj, scc_wwn_l, activate_flag):
    """
    Set the SCC policy in each chassis
    
    :param switch_obj: Switch object
    :type switch_obj: brcddb.class.switch.SwitchObj
    :param scc_wwn_l: Expected defined SCC_POLICY membership
    :type scc_wwn_l: list
    :param activate_flag: If True, activate the SCC_POLICY
    :type activate_flag: bool
    :return: All updates made to the switch object
    :rtype: None
    """
    global _scc_policy_capture_uris, _WAIT_TIME, _row_str

    fid = switch_obj.r_fid()
    switch_name = brcddb_switch.best_switch_name(switch_obj, wwn=True, did=True, fid=True)
    chassis_obj = switch_obj.r_chassis_obj()
    login_d = chassis_obj.r_get('scc_login_d')
    _row_str = login_d['row_str']

    # Login
    time.sleep(_WAIT_TIME)
    session = api_int.login(login_d['user_id'], login_d['pw'], login_d['ip_addr'], login_d['sec'])
    if fos_auth.is_error(session):
        brcdapi_log.log(['Failed to login to: ' + switch_name, fos_auth.formatted_error_msg(session)], echo=True)
        raise HaltProcessing

    # Capture SCC_POLICY data and evaluate it.
    api_int.get_batch(session, switch_obj.r_project_obj(), _scc_policy_capture_uris, fid=switch_obj.r_fid())
    scc_policy_d = _evaluate_scc(switch_obj, scc_wwn_l)
    switch_obj.s_new_key('scc_policy_d', scc_policy_d, f=True)

    # If the SCC_POLICY doesn't exist, create it with the membership list
    if scc_policy_d['create_bool']:
        obj = brcdapi_rest.operations_request(
            session,
            'operations/security-acl-policy',
            'POST',
            {
                'security-policy-parameters': {
                    'policy-name': 'SCC_POLICY',
                    'members': dict(member=scc_policy_d['add_l']),
                    'action': 'create',
                }
            },
            fid=fid
        )
        if fos_auth.is_error(obj):
            scc_policy_d['defined'] = 'create_fail'
            buf = 'Row: ' + _row_str + '. Failed to create SCC_POLICY for: ' + switch_name
            brcdapi_log.log([buf, fos_auth.formatted_error_msg(obj)], echo=True)
            api_int.logout(session)
            raise HaltProcessing

        api_int.logout(session)
        time.sleep(_WAIT_TIME)
        session = api_int.login(login_d['user_id'], login_d['pw'], login_d['ip_addr'], login_d['sec'])
        if fos_auth.is_error(session):
            buf = 'Row: ' + _row_str + '. Failed to login to: ' + switch_name
            brcdapi_log.log([buf, fos_auth.formatted_error_msg(session)], echo=True)
            raise HaltProcessing

    # Add all the WWNs that need to be added.
    else:
        if len(scc_policy_d['add_l']) > 0:
            obj = brcdapi_rest.operations_request(
                session,
                'operations/security-acl-policy',
                'POST',
                {
                    'security-policy-parameters': {
                        'policy-name': 'SCC_POLICY',
                        'members': dict(member=scc_policy_d['add_l']),
                        'action': 'add',
                    }
                },
                fid=fid
            )
            if fos_auth.is_error(obj):
                scc_policy_d['defined'] = 'fail'
                buf = 'Row: ' + _row_str + '. Error adding to WWNs ' ', '.join(scc_policy_d['add_l'])
                buf += ' to SCC_POLICY for switch ' + switch_name
                brcdapi_log.log([buf, fos_auth.formatted_error_msg(obj)], echo=True)
                api_int.logout(session)
                raise HaltProcessing
            scc_policy_d['defined'] = 'success'

        # Remove all the WWNs that do not belong in the policy
        if len(scc_policy_d['remove_l']) > 0:
            obj = brcdapi_rest.operations_request(
                session,
                'operations/security-acl-policy',
                'POST',
                {
                    'security-policy-parameters': {
                        'policy-name': 'SCC_POLICY',
                        'members': dict(member=scc_policy_d['remove_l']),
                        'action': 'remove',
                    }
                },
                fid=fid
            )
            if fos_auth.is_error(obj):
                scc_policy_d['defined'] = 'fail'
                buf = 'Row: ' + _row_str + '. Error removing ' + ', '.join(scc_policy_d['remove_l'])
                buf += ' from SCC_POLICY for switch ' + switch_name
                brcdapi_log.log([buf, fos_auth.formatted_error_msg(obj)], echo=True)
                api_int.logout(session)
                raise HaltProcessing
            scc_policy_d['defined'] = 'success'

    # If we got this far without a success or fail, it's because the policy already matched the expected policy.
    if scc_policy_d['defined'] == 'not_attempted':
        scc_policy_d['defined'] = 'match'
    else:  # We modified the policy, so logout and back in to pick up the changes
        api_int.logout(session)
        time.sleep(_WAIT_TIME)
        session = api_int.login(login_d['user_id'], login_d['pw'], login_d['ip_addr'], login_d['sec'])
        if fos_auth.is_error(session):
            buf = 'Row: ' + _row_str + '. Failed to login to: ' + switch_name
            brcdapi_log.log([buf, fos_auth.formatted_error_msg(session)], echo=True)
            api_int.logout(session)
            raise HaltProcessing
        api_int.get_batch(session, switch_obj.r_project_obj(), _scc_policy_capture_uris, fid=switch_obj.r_fid())

    # Activate the SCC_POLICY
    if activate_flag:

        # A quick sanity check to ensure the defined SCC_POLICY is what we expect it to be before distributing it.
        active_scc_l = switch_obj.r_active_scc(list())
        if not _compare_membership(
                'Activation Check',
                'Defined',
                switch_obj.r_defined_scc(list()),
                'Expected',
                scc_wwn_l
        ):
            scc_policy_d['defined'] = 'fail'
            scc_policy_d['activated'] = 'skip'
            brcdapi_log.log('Row: ' + _row_str + '. Read back failed for ' + switch_name, echo=True)
            api_int.logout(session)
            raise HaltProcessing

        # If an SCC_POLICY hasn't been distributed to the fabric, create one and activate it
        if len(active_scc_l) == 0:
            obj = brcdapi_rest.operations_request(
                session,
                'operations/security-fabric-wide-policy-distribute',
                'POST',
                {
                    'distribute-parameters': {
                        'policy-types': dict(type='strict-scc'),
                    }
                },
                fid=switch_obj.r_fid()
            )
            if fos_auth.is_error(obj):
                scc_policy_d['activated'] = 'create_fail'
                buf = 'Row: ' + _row_str + 'Error distributing SCC_POLICY for switch: ' + switch_name
                brcdapi_log.log([buf, fos_auth.formatted_error_msg(obj)], echo=True)
                api_int.logout(session)
                raise HaltProcessing
            scc_policy_d['activated'] = 'create_success'

        else:
            if not _compare_membership(
                    None,
                    None,
                    active_scc_l,
                    None,
                    switch_obj.r_defined_scc(list()),
                    disp=False
            ):
                # Activate the current defined SCC_POLICY
                obj = brcdapi_rest.operations_request(
                    session,
                    'operations/security-acl-policy',
                    'POST',
                    {
                        'security-policy-parameters': {
                            'action': 'activate',
                        }
                    },
                    fid=fid
                )
                if fos_auth.is_error(obj):
                    scc_policy_d['activated'] = 'fail'
                    buf = 'Row: ' + _row_str + 'Error activating ' + ', '.join(scc_policy_d['remove_l'])
                    buf += ' from SCC_POLICY for switch ' + switch_name
                    brcdapi_log.log([buf, fos_auth.formatted_error_msg(obj)], echo=True)
                    api_int.logout(session)
                    raise HaltProcessing
                scc_policy_d['activated'] = 'success'
            else:
                scc_policy_d['activated'] = 'match'
    else:
        scc_policy_d['activated'] = 'no_activate'


def _initial_capture(proj_obj, poll_l):

    """ Login to each chassis and capture basic information

    :param proj_obj: Project object
    :type proj_obj: brcddb.classes.project.ProjectObj
    :param poll_l: Switches to poll as read from the input Workbook
    :type poll_l: list
    :return: Switch objects whose SCC policy is to be updated
    :rtype: list
    """
    global _basic_capture_uris, _scc_policy_capture_uris, _row_str

    switch_obj_l = list()

    # chassis_track_d: Used to make sure we don't poll the same chassis twice. Note that lab environments may disable
    # fid checking. Key: Chassis IP address. Value: Session object.
    chassis_track_d = dict()

    # Login and capture the data
    for d in poll_l:
        # Frequently used:
        ip_addr, user_id, pw, sec = d['ip_addr'], d['user_id'], d['pw'], d['security']
        _row_str, fid = str(d['row']), d['fid']
        brcdapi_log.log('Processing row: ' + _row_str, echo=True)
        session = chassis_track_d.get(ip_addr, None)
        if session is None:

            # Login
            session = api_int.login(user_id, pw, ip_addr, sec, proj_obj)
            if fos_auth.is_error(session):
                brcdapi_log.log(
                    ['Row ' + _row_str + ': ' + 'Login failed. Error message is:',
                     fos_auth.formatted_error_msg(session)],
                    echo=True)
                ec = brcddb_common.EXIT_STATUS_API_ERROR
                break
            chassis_track_d[ip_addr] = session

            # Capture basic chassis and logical switch information
            try:
                api_int.get_batch(session, proj_obj, _basic_capture_uris + _scc_policy_capture_uris)
            except BaseException as e:
                brcdapi_log.log(
                    'Row ' + _row_str + ': Unexpected error encountered.: ' + str(type(e)) + ': ' + str(e),
                    echo=True
                )
                ec = brcddb_common.EXIT_STATUS_API_ERROR
                break

        # Add the login credentials to the chassis object
        chassis_obj = proj_obj.r_chassis_obj(session['chassis_wwn'])
        chassis_obj.s_new_key(
            'scc_login_d',
            dict(user_id=user_id, ip_addr=ip_addr, pw=pw, sec=sec, row_str=_row_str),
            f=True
        )

        # Find the switch object.
        try:
            switch_obj = chassis_obj.r_switch_obj_for_fid(fid)
            if switch_obj is None:
                brcdapi_log.log('Row: ' + _row_str + 'Could not find a switch matching fid: ' + str(fid), echo=True)
                ec = brcddb_common.EXIT_STATUS_API_ERROR
                break
            switch_obj_l.append(switch_obj)
        except BaseException as e:
            brcdapi_log.log(
                'Row ' + _row_str + ': Unexpected error encountered.: ' + str(type(e)) + ': ' + str(e),
                echo=True
            )
            break

    # Logout
    for session in chassis_track_d.values():
        api_int.logout(session)

    return switch_obj_l


def _determine_scc_membership(scc_switch_obj_l, add_l, remove_l, clr_flag):
    """Determines the membership list for the SCC policy as well as the processing order

    :param scc_switch_obj_l: Switch objects for SCC policy
    :type scc_switch_obj_l: list
    :param add_l: WWNs to add from the -add option
    :type add_l: list
    :param remove_l: WWNs to remove from the -remove option
    :type remove_l: list
    :param clr_flag: If True, do not include the existing policy members
    :tye clr_flag: bool
    :return scc_wwn_l: Absolute list of WWNs for the SCC policy
    :rtype scc_wwn_l: list
    :return process_l: Switch objects in the order they are to be processed. Fabric principal is first.
    """
    global _row_str

    process_obj_l = list()  # Switch objects from workbook in process order (fabric principal first).
    secondary_obj_l = list()  # Non-principal switch object to add to process_obj_l
    # Determine what WWNs should be in the SCC policy based on the input workbook
    scc_obj_d = dict()  # Switches from workbook. Key: Switch WWN. Value: Switch object
    scc_wwn_l = add_l  # Absolute list of WWNs that should be in the SCC_POLICY membership list
    for switch_obj in scc_switch_obj_l:
        _row_str = switch_obj.r_chassis_obj().r_get('scc_login_d/row_str')
        wwn = switch_obj.r_obj_key()
        scc_obj_d[wwn] = switch_obj
        scc_wwn_l.append(wwn)
        if not clr_flag:
            scc_wwn_l.extend(switch_obj.r_defined_scc(list()))
        if switch_obj.r_is_principal():
            process_obj_l.append(switch_obj)
        else:
            secondary_obj_l.append(switch_obj)
    process_obj_l.extend(secondary_obj_l)

    # Remove WWNs based on the -remove shell parameter
    for wwn in remove_l:
        switch_obj = scc_obj_d[wwn]
        if switch_obj is not None:
            buf = 'Row: ' + _row_str + '. Cannot remove ' + wwn
            buf += ' because it is the WWN of ' + brcddb_switch.best_switch_name(switch_obj, fid=True, did=True)
            brcdapi_log.log(buf, echo=True)
            raise HaltProcessing
        try:
            scc_wwn_l.remove(wwn)
        except ValueError:
            pass  # Just ignore it if the WWN doesn't exist.
    scc_wwn_l.sort()

    # Determine the switch objects and order they should be processed in
    process_l = [obj for obj in scc_switch_obj_l if obj.r_is_principal()]
    process_l.extend([obj for obj in scc_switch_obj_l if not obj.r_is_principal()])

    return scc_wwn_l, process_l


def _final_validation(scc_switch_obj_l, scc_wwn_l, activate_flag):
    """Read back the SSC_POLICY and make sure they are as expected.

    :param scc_switch_obj_l: Switch objects for SCC policy
    :type scc_switch_obj_l: list
    :param scc_wwn_l: Expected defined SCC_POLICY membership
    :type scc_wwn_l: list
    :param activate_flag: If True, the active policy should match the defined policy
    :type activate_flag: bool
    """
    global _scc_policy_capture_uris, _WAIT_TIME, _row_str

    for switch_obj in scc_switch_obj_l:
        _row_str = switch_obj.r_chassis_obj().r_get('scc_login_d/row_str')
        scc_policy_d = switch_obj.r_get('scc_policy_d')

        # Login
        time.sleep(_WAIT_TIME)
        login_d = switch_obj.r_chassis_obj().r_get('scc_login_d')
        session = api_int.login(login_d['user_id'], login_d['pw'], login_d['ip_addr'], login_d['sec'])
        if fos_auth.is_error(session):
            buf = 'Row ' + login_d['row_str'] + ': ' + 'Login failed during final validation. Error message is:'
            brcdapi_log.log([buf, fos_auth.formatted_error_msg(session)], echo=True)
            scc_policy_d['defined'] = 'validation_fail'
            if activate_flag:
                scc_policy_d['activated'] = 'validation_fail'
            continue

        # Capture the SCC_POLICY data
        api_int.get_batch(session, switch_obj.r_project_obj(), _scc_policy_capture_uris, fid=switch_obj.r_fid())
        switch_name = brcddb_switch.best_switch_name(switch_obj, wwn=True, did=True, fid=True)
        hdr = 'Unexpected Defined SCC_POLICY for ' + switch_name
        if not _compare_membership(hdr, 'Defined', switch_obj.r_defined_scc(list()), 'Expected', scc_wwn_l):
            scc_policy_d['defined'] = 'validation_fail'
        hdr = 'Unexpected Active SCC_POLICY for ' + switch_name
        if activate_flag:
            if not _compare_membership(hdr, 'Active', switch_obj.r_active_scc(list()), 'Expected', scc_wwn_l):
                scc_policy_d['activated'] = 'validation_fail'

        # Logout
        api_int.logout(session)

    return


def pseudo_main(poll_l, add_l, remove_l, args_d):
    """Basically the main(). Did it this way so that it can easily be used as a standalone module or called externally.

    :param poll_l: Switches to poll as read from the input Workbook
    :type poll_l: list
    :param add_l: WWNs to add manually
    :type add_l: list
    :param remove_l: WWNs to add manually
    :type remove_l: list
    :param args_d: Parsed arguments. See _input_d for details.
    :type args_d: dict
    :return: Exit code. See exit codes in brcddb.brcddb_common
    :rtype: int
    """
    global _basic_capture_uris, _row_str

    ec = brcddb_common.EXIT_STATUS_OK

    scc_wwn_d, scc_switch_obj_l = dict(), list()

    # Create a project
    proj_obj = brcddb_project.new('sec_policy', datetime.datetime.now().strftime('%d %b %Y %H:%M:%S'))
    proj_obj.s_python_version(sys.version)
    proj_obj.s_description('SCC Policy')

    try:

        # Capture initial chassis data and determine what the switch objects are.
        brcdapi_log.log('**Begin login and data capture for each switch.**', echo=True)
        scc_switch_obj_l = _initial_capture(proj_obj, poll_l)

        # Determine what WWNs should be in the SCC_POLICY membership list and in what order to process the workbook in.
        scc_wwn_l, process_l = _determine_scc_membership(scc_switch_obj_l, add_l, remove_l, args_d['clr'])

        # Add the initial SCC_POLICY data to each switch object. Used in _generate_cli()
        for switch_obj in scc_switch_obj_l:
            switch_obj.s_new_key('initial_scc_policy_d', _evaluate_scc(switch_obj, scc_wwn_l), f=True)

        # Make the changes via the API
        if args_d['api']:
            for switch_obj in scc_switch_obj_l:
                _define_activate_scc_policy(switch_obj, scc_wwn_l, args_d['activate'])

        # Validate it
        if args_d['api']:
            _final_validation(scc_switch_obj_l, scc_wwn_l, args_d['activate'])

        # Display the CLI commands & a summary
        brcdapi_log.log(_generate_cli(scc_switch_obj_l, scc_wwn_l), echo=True)
        brcdapi_log.log(_summary(args_d, scc_switch_obj_l), echo=True)

    except KeyboardInterrupt:
        brcdapi_log.log('Processing terminated by user.', echo=True)
        ec = brcddb_common.EXIT_STATUS_API_ERROR
    except RuntimeError:
        brcdapi_log.log('Row ' + _row_str + ': Programming error encountered. See previous message', echo=True)
        ec = brcddb_common.EXIT_STATUS_API_ERROR
    except brcdapi_util.VirtualFabricIdError:
        brcdapi_log.log('Row ' + _row_str + ': Software error. Search the log for "Invalid FID" for details.', echo=True)
        ec = brcddb_common.EXIT_STATUS_API_ERROR
    except HaltProcessing:
        if ec == brcddb_common.EXIT_STATUS_OK:
            ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
    # except BaseException as e:
    #     brcdapi_log.log(
    #         'Row ' + _row_str + ': Programming error encountered.: ' + str(type(e)) + ': ' + str(e),
    #         echo=True
    #     )
    #     ec = brcddb_common.EXIT_STATUS_API_ERROR

    return ec


def _get_input():
    """Retrieves the command line input, reads the input Workbook, and minimally validates the input

    :return: Exit code. See exit codes in brcddb.brcddb_common
    :rtype: int
    """
    global __version__, _input_d, _check_login_l

    # Initialize the return and working variables
    ec = brcddb_common.EXIT_STATUS_OK
    poll_l, add_wwn_l, remove_wwn_l = list(), list(), list()

    # Get command line input
    buf = 'The scc_policy utility is used primarily in mainframe environments. By default, the scc_policy is defined '\
          'when creating a ficon logical switch with just the WWN of that switch, so it is rare, if ever, that this '\
          'would be used for a single switch fabric. The typical use case is when merging two or more switches in a '\
          'cascaded FICON environment.'
    args_d = gen_util.get_input(buf, _input_d)

    # Set up logging
    brcdapi_rest.verbose_debug(args_d['d'])
    brcdapi_log.open_log(
        folder=args_d['log'],
        suppress=args_d['sup'],
        no_log=args_d['nl'],
        version_d=brcdapi_util.get_import_modules()
    )

    # Default help messages for input validation
    help_i, help_sheet, help_add_wwn, sheet_error_l = '', '', '', list()

    # Read the input workbook and worksheet
    c_file = brcdapi_file.full_file_name(args_d['i'], '.xlsx')
    try:
        switch_l = excel_util.parse_parameters(sheet_name=args_d['sheet'], hdr_row=0, wb_name=c_file)['content']
        if len(switch_l) == 0:
            sheet_error_l.append('Sheet does not exist or does not contain any parameters.')
        row = 2
        for switch_d in switch_l:
            switch_d['row'] = row

            # Validate the input parameters for this row
            i, temp_error_l = 0, list()
            for key in _check_login_l:
                if switch_d.get(key) is None:
                    temp_error_l.append('  Row ' + str(row) + ': missing parameter: ' + key)
                else:
                    i += 1
            if i == 0:
                row += 1
                continue  # It's just a blank line
            elif i < len(_check_login_l):
                sheet_error_l.extend(temp_error_l)
                row += 1
                continue
            fid_buf = brcdapi_util.validate_fid(switch_d['fid'])
            if len(fid_buf) > 0:
                sheet_error_l.append('  Row ' + str(row) + ': Invalid FID, ' + str(switch_d['fid']) + '.' + fid_buf)
                row += 1
                continue

            # If we got this far, it's good. Add the dictionary to the list of chassis to be polled.
            poll_l.append(switch_d)
            row += 1

        # If there are any errors, add them to the help text displayed with user feedback.
        if len(sheet_error_l) > 0:
            help_sheet = ' ERRORS. See below for details:'
            buf = '  Only one FID (with login credentials) or one fabric WWN (with a project file) per row  is '
            buf += 'permitted'
            sheet_error_l.append(buf)
            ec = brcddb_common.EXIT_STATUS_INPUT_ERROR

    # Process any file read errors
    except FileExistsError:
        help_i = ' ERROR: Specified path does not exist.'
        ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
    except FileNotFoundError:
        help_i = ' ERROR: File does not exist.'
        ec = brcddb_common.EXIT_STATUS_INPUT_ERROR

    # Add WWNs specified with the -add option
    if isinstance(args_d['add'], str):
        help_add_wwn, bad_wwn_l = args_d['add'], list()
        for wwn in args_d['add'].split(','):
            if gen_util.is_wwn(wwn):
                add_wwn_l.append(wwn)
            else:
                bad_wwn_l.append(wwn)
        if len(bad_wwn_l) > 0:
            help_add_wwn += ' Invalid WWNs: ' + ', '.join(bad_wwn_l)
            ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
    else:
        help_add_wwn = 'None'

    # Remove WWNs specified with the -remove option
    if isinstance(args_d['remove'], str):
        help_remove_wwn, bad_wwn_l = args_d['remove'], list()
        for wwn in args_d['remove'].split(','):
            if gen_util.is_wwn(wwn):
                remove_wwn_l.append(wwn)
            else:
                bad_wwn_l.append(wwn)
        if len(bad_wwn_l) > 0:
            help_remove_wwn += ' Invalid WWNs: ' + ', '.join(bad_wwn_l)
            ec = brcddb_common.EXIT_STATUS_INPUT_ERROR
    else:
        help_remove_wwn = 'None'

    # Command line feedback
    ml = [
        os.path.basename(__file__) + ', ' + __version__,
        'Input file, -i:        ' + str(c_file) + help_i,
        'Sheet, -sheet:         ' + str(args_d['sheet']) + help_sheet,
        ]
    ml.extend(sheet_error_l)
    ml.extend([
        'WWNs to add, -add:              ' + help_add_wwn,
        'WWNs to remove, -remove:        ' + help_remove_wwn,
        'Clear flag, -clr:               ' + str(args_d['clr']),
        'Set via API, -api:              ' + str(args_d['api']),
        'Activate SCC_POLICY, -activate: ' + str(args_d['activate']),
        'Log, -log:                      ' + str(args_d['log']),
        'No log, -nl:                    ' + str(args_d['nl']),
        'Debug, -d:                      ' + str(args_d['d']),
        'Suppress, -sup:                 ' + str(args_d['sup']),
        '',
    ])
    brcdapi_log.log(ml, echo=True)

    return ec if ec != brcddb_common.EXIT_STATUS_OK else pseudo_main(poll_l, add_wwn_l, remove_wwn_l, args_d)


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
