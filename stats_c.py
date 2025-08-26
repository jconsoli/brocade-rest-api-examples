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

Collects port statistics at a user specified interval

Initially collects switch and name server information plus the first sample. This is done to make it so that ports can
be associated with what is logged in. From thereafter, only port statistics are gathered. All data collected from the
switch is stored in a standard brcddb project. The initial switch is stored with it's WWN as is normal; however, each
additional sample is stored with the WWN and the sample number appended.

This script is pretty simple. It doesn't log out and re-login between polls so the poll cycle has to be short enough
such that the switch doesn't automatically log you out. I believe the default logout for a switch login via the API is
5 minutes. To maintain the poll cycle a sleep is introduced that is calculated by:

sleep = poll cycle time - (poll finish time - poll start time)

epoch time of the server where the script is run is used for the formula above. The accuracy of the poll cycle will
depend on several factors, most notably networking delays and CPU activity. The time stamp of the data comes from the
time stamp returned with the switch response.Keep in mind that most data centers use a time clock server which is often
UTC. As of this writing, time-generated returned with the port statistics was the time on the switch when the request
was made, not when the statistics were captured by FOS. For Gen6 & Gen7, FOS polls the port statistics every 2 seconds
so the accuracy of the timestamp is within 2 seconds. A new parameter, time-refreshed, was added in one of the 9.x
released, but to maintain support with older versions of FOS, time-generated is still used. Given that the minimum
interval is 2.1 sec, this is moot.

Only fibre channel port statistics are collected at this time. A JSON dump of the counters (only differences of
cumulative counters are stored, which are most of the counters) in a plain text file. Use stats_g.py to convert to an
Excel Workbook

Control-C is supported so data collection can be terminated without incident prior to the maximum number of samples
being collected.

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Set verbose debug via brcdapi.brcdapi_rest.verbose_debug()                            |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 03 Apr 2024   | Added version numbers of imported libraries.                                          |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.3     | 16 Jun 2024   | Improved help messages.                                                               |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.4     | 29 Oct 2024   | Added debug capabilities.                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.5     | 06 Dec 2024   | Fixed spelling mistake in message.                                                    |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.6     | 25 Aug 2025   | Use brcddb.util.util.get_import_modules to dynamically determined imported libraries. |
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

import http.client
import sys
import os
import signal
import time
import datetime
import brcdapi.gen_util as gen_util
import brcdapi.util as brcdapi_util
import brcdapi.log as brcdapi_log
import brcdapi.fos_auth as fos_auth
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.file as brcdapi_file
import brcddb.brcddb_common as brcddb_common
import brcddb.brcddb_project as brcddb_project
import brcddb.brcddb_chassis as brcddb_chassis
import brcddb.util.copy as brcddb_copy
import brcddb.api.interface as brcddb_int
import brcddb.classes.util as class_util

_DOC_STRING = False  # Should always be False. Prohibits any code execution. Only useful for building documentation
# _STAND_ALONE: True: Executes as a standalone module taking input from the command line. False: Does not automatically
# execute. This is useful when importing this module into another module that calls psuedo_main().
_STAND_ALONE = True  # See note above
_DEBUG = False  # True: skip the sleep between sample collection. Useful when simulating in brcdapi.brcdapi_restapi.py

"""_MIN_POLL is the minimum time in seconds the command line will accept. It is actually the time to sleep between each
request for statistical data. Additional comments regarding the poll cycles are in the Overview section in the module
header. Picking a sleep time that results in a poll that guarantees the poll cycle of FOS is impossible. This is why
0.1 is added. Keep in mind that if you poll a switch twice within the same internal switch poll cycle, all the
statistical counters will be the same as the previous poll but the time stamp will be different."""
_MIN_POLL = 2.1  # See comments above
_EXCEPTION_MSG = 'This normally occurs when data collection is terminated with Control-C keyboard interrupt or a '\
    'network error occurred. All data collected up to this point will be saved.'
_DEFAULT_POLL_INTERVAL = 10.0  # Default poll interval, -p
_DEFAULT_MAX_SAMPLE = 100  # Default number of samples, -m
_MIN_SAMPLES = 5  # A somewhat arbitrary minimum number of samples.

_buf = '(Optional) Samples are collected until this maximum is reached or a Control-C keyboard interrupt is received. '
_buf += '"-m 0" picks the default which is equivalent to -p ' + str(_DEFAULT_MAX_SAMPLE) + '. The minimum number of '
_buf += 'samples is ' + str(_MIN_SAMPLES) + '.'
_input_d = gen_util.parseargs_login_d.copy()
_input_d.update(
    o=dict(h='Required. Name of output file where raw data is to be stored. ".json" extension is automatically '
             'appended.'),
    fid=dict(r=False, t='int', v=gen_util.range_to_list('1-128'),
             h='(Optional) Virtual Fabric ID (1 - 128) of switch to read statistics from. Omit this option if the '
               'chassis is not VF enabled. If omitted in a VF enabled chassis, the default is 128'),
    p=dict(r=False, t='float', d=_DEFAULT_POLL_INTERVAL,
           h='(Optional) Polling interval in seconds. Since fractions of a second are supported, this is a floating '
             'point number. "-p 0.0" picks the default which is equivalent to -p ' + str(_DEFAULT_POLL_INTERVAL) +
             '. The minimum is ' + str(_MIN_POLL) + ' seconds. WARNING: If the poll time is >= 15 sec, disable the '
             'HTTP timeout. You can use the -https_dis parameter with app_config.py to do this.'
           ),
    m=dict(r=False, t='int', h=_buf),
)
_input_d.update(gen_util.parseargs_log_d.copy())
_input_d.update(gen_util.parseargs_debug_d.copy())
_required_input = ('ip', 'id', 'pw', 'fid', 'wwn')

# URIs
_uris = (
    # Don't forget that if NPIV is enabled, there may be multiple logins per port. I took the liberty of assuming you
    # may also want to know other information such as the name of the switch a port is in, alias of attached login,
    # and zone the logins are in,
    'running/brocade-fibrechannel-switch/fibrechannel-switch',  # Switch name, DID, etc...
    'running/brocade-interface/fibrechannel',  # Base port information + average frame size
 )
_uris_2 = (  # Execute if there is a fabric principal
    # 'running/brocade-fibrechannel-configuration/port-configuration',  # Port configuration
    'running/brocade-name-server/fibrechannel-name-server',  # Name server login registration information
    'running/brocade-fibrechannel-configuration/zone-configuration',  # Alias and zoning associated with login
    'running/brocade-zone/defined-configuration',
    'running/brocade-zone/effective-configuration',
    'running/brocade-fdmi/hba',  # FDMI node data
    'running/brocade-fdmi/port',  # FDMI port data
)

""" _synthetic_values_d allows you to synthesize input data. _synthetic_values_d is a dictionaries of dictionaries. The
primary key is the port number. The value is a dictionary as described below. If the port number returned from the API
is not in _synthetic_values_d, all values for that port are as returned from FOS. I originally did this when developing
stats_g.py and left it in for potential future use.

+-----------+-------+-----------------------------------------------------------------------------------------------+
| Key       | Type  | Description                                                                                   |
+===========+=======+===============================================================================================+
| i         | int   | The running index into value_l. It is reset to 0 when it exceeds the length of value_l.       |
+-----------+-------+-----------------------------------------------------------------------------------------------+
| value_l   | list  | A list of dictionaries that define what values are to be used in place of the values read.    |
|           |       | The keys are the FOS API keys in fibrechannel-statistics. The value is the value to be used   |
|           |       | when polling for statistics instead of the actual value returned. The actual data returned    |
|           |       | from the switch is used when the corresponding leaf is not in the dictionary.                 |
|           |       |                                                                                               |
|           |       | For full simulation, add 'time-generated' to each entry. You will also need to modify the     |
|           |       | _DEBUG, _DEBUG_MODE, AND _DEBUG_PREFIX in brcddb.brcddb_rest.py when doing this.              |
+-----------+-------+-----------------------------------------------------------------------------------------------+
"""
_synthetic_values_d = dict()  # See note above
# _temp_d = {  # Used to build _synthetic_values_d. Stats here are incremental but running when returned from FOS
#     '0/0': dict(
#         i=0,
#         value_l=[
#             {'in-crc-errors': 0, 'in-frames': 1000, 'out-frames': 10, 'time-generated': 1729695579},
#             {'in-crc-errors': 0, 'in-frames': 5000, 'out-frames': 50, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 10000, 'out-frames': 100, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 10000, 'out-frames': 100, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 11000, 'out-frames': 110, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 12000, 'out-frames': 120, 'time-generated': 10},
#             {'in-crc-errors': 1, 'in-frames': 13000, 'out-frames': 130, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 13100, 'out-frames': 131, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 13200, 'out-frames': 132, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 13100, 'out-frames': 131, 'time-generated': 10},
#             {'in-crc-errors': 1, 'in-frames': 13200, 'out-frames': 132, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 13100, 'out-frames': 131, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 14000, 'out-frames': 140, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 15000, 'out-frames': 150, 'time-generated': 10},
#             {'in-crc-errors': 2, 'in-frames': 16000, 'out-frames': 160, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 15000, 'out-frames': 150, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 14000, 'out-frames': 140, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 13000, 'out-frames': 130, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 12000, 'out-frames': 120, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 11000, 'out-frames': 110, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 10000, 'out-frames': 100, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 9000, 'out-frames': 90, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 8000, 'out-frames': 80, 'time-generated': 10},
#         ]
#     ),
#     '0/1': dict(
#         i=0,
#         value_l=[
#             {'in-crc-errors': 0, 'in-frames': 1200, 'out-frames': 10, 'time-generated': 1729695579},
#             {'in-crc-errors': 0, 'in-frames': 5040, 'out-frames': 50, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 30000, 'out-frames': 100, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 35000, 'out-frames': 100, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 23000, 'out-frames': 110, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 78000, 'out-frames': 120, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 45000, 'out-frames': 130, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 26100, 'out-frames': 131, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 13890, 'out-frames': 132, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 13100, 'out-frames': 131, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 13400, 'out-frames': 132, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 16700, 'out-frames': 131, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 49000, 'out-frames': 140, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 26000, 'out-frames': 150, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 16000, 'out-frames': 160, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 17000, 'out-frames': 150, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 14800, 'out-frames': 140, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 52123, 'out-frames': 130, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 19283, 'out-frames': 120, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 12000, 'out-frames': 110, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 13000, 'out-frames': 100, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 5000, 'out-frames': 90, 'time-generated': 10},
#             {'in-crc-errors': 0, 'in-frames': 900, 'out-frames': 80, 'time-generated': 10},
#         ]
#     ),
# }
# for _port, _d0 in _temp_d.items():
#     _synthetic_values_d.update({_port: dict(i=0, value_l=[_d0['value_l'][0].copy()])})
#     _last_i = 0
#     for _d1 in _d0['value_l'][1:]:
#         _stats_d = dict()
#         for _key, _value in _d1.items():
#             _stats_d.update({_key: _value + _synthetic_values_d[_port]['value_l'][_last_i][_key]})
#         _synthetic_values_d[_port]['value_l'].append(_stats_d)
#         _last_i += 1


def _wrap_up(session, proj_obj, base_switch_wwn, switch_obj_l, exit_code, out_f):
    """Write out the collected data in JSON to a plain text file.

    :param session: FOS session object
    :type session: dict
    :param proj_obj: Project object
    :type proj_obj: brcddb.classes.project.ProjectObj
    :param base_switch_wwn: WWN of base switch object
    :type base_switch_wwn: str
    :param switch_obj_l: List of switch objects for each poll
    :type switch_obj_l: list
    :param exit_code: Initial exit code
    :type exit_code: int
    :param out_f:  Name of output file where raw data is to be stored
    :type out_f: str
    :return: Exit code. See exist codes in brcddb.brcddb_common
    :rtype: int
    """
    ec = exit_code
    if session is not None:
        try:
            obj = brcdapi_rest.logout(session)
            if fos_auth.is_error(obj):
                brcdapi_log.log(['Logout failed. Error is:', fos_auth.formatted_error_msg(obj)], echo=True)
            else:
                brcdapi_log.log('Logout succeeded', echo=True)
        except (http.client.CannotSendRequest, http.client.ResponseNotReady):
            brcdapi_log.log(['Could not logout. You may need to terminate this session via the CLI',
                             'mgmtapp --showsessions, mgmtapp --terminate'], echo=True)
            ec = brcddb_common.EXIT_STATUS_INPUT_ERROR

    try:
        proj_obj.s_new_key('base_switch_wwn', base_switch_wwn)
        proj_obj.s_new_key('switch_list', [obj.r_obj_key() for obj in switch_obj_l])
        plain_copy = dict()
        brcddb_copy.brcddb_to_plain_copy(proj_obj, plain_copy)
        brcdapi_file.write_dump(plain_copy, out_f)
    except BaseException as e:
        brcdapi_log.exception(str(type(e)) + ': ' + str(e), echo=True)
    return ec


def _stats_diff(old_obj, new_obj):
    """Builds a structure that looks like 'brocade-interface/fibrechannel-statistics' but just the differences

    :param old_obj: Previous list returned from 'brocade-interface/fibrechannel-statistics'
    :type old_obj: dict
    :param new_obj: New list returned from 'brocade-interface/fibrechannel-statistics'
    :type new_obj: dict
    :return: Port statistics differences in the format returned from 'brocade-interface/fibrechannel-statistics'
    :rtype: dict
    """
    new_list = list()
    ret_obj = {brcdapi_util.stats_uri: new_list}

    # I'm not sure if it's a guarantee to get the ports in the same order, but I need to account for a port going
    # offline anyway so the code below creates a map (dict) of old ports to their respective stats
    old_ports_d = dict()
    for port_d in old_obj.get(brcdapi_util.stats_uri):
        old_ports_d.update({port_d.get('name'): port_d})

    # Get the differences
    for port_d in new_obj.get(brcdapi_util.stats_uri):
        if port_d is None:
            break  # This can happen when the user Control-C out. I have no idea why, but I've seen it happen
        new_stats = dict()
        port_num = port_d.get('name')
        old_stats = old_ports_d.get(port_num)
        if old_stats is None:
            new_stats = port_d
        else:
            for k, v in port_d.items():
                if k not in ('sampling-interval', 'time-generated') and 'rate' not in k and isinstance(v, (int, float)):
                    new_stats.update({k: v - old_stats.get(k)})
                elif isinstance(v, dict):
                    d1 = dict()
                    for k1, v1 in v.items():
                        d1.update({k1: v1 - v.get(k1)})
                    new_stats.update({k: d1})
                else:
                    new_stats.update({k: v})
        new_list.append(new_stats)
    return ret_obj


def pseudo_main(ip, user_id, pw, sec, fid, pct, max_p, out_f):
    """Basically the main(). Did it this way so that it can easily be used as a standalone module or called externally.

    :param ip: IP address
    :type ip: str
    :param user_id: User ID
    :type user_id: str
    :param pw: Password
    :type pw: str
    :param sec: Type of HTTP security
    :type sec: str
    :param fid: Fabric ID in chassis specified by -ip where the zoning information is to be copied to.
    :type fid: int
    :param pct: Poll Time - Poll interval in seconds
    :type pct: float
    :param max_p: Maximum number of times to poll (collect samples)
    :type max_p: int, None
    :param out_f:  Name of output file where raw data is to be stored
    :type out_f: str
    :return: Exit code. See exist codes in brcddb.brcddb_common
    :rtype: int
    """
    global _DEBUG, _DEFAULT_POLL_INTERVAL, _DEFAULT_MAX_SAMPLE, __version__, _uris, _uris_2, _synthetic_values_d

    signal.signal(signal.SIGINT, brcdapi_rest.control_c)

    # Create project
    proj_obj = brcddb_project.new('Port_Stats', datetime.datetime.now().strftime('%d %b %Y %H:%M:%S'))
    proj_obj.s_python_version(sys.version)
    proj_obj.s_description('Port statistics')

    base_switch_wwn, switch_obj_l = 'Unknown', list()

    # Login
    session = brcddb_int.login(user_id, pw, ip, sec, proj_obj)
    if fos_auth.is_error(session):
        brcdapi_log.log(fos_auth.formatted_error_msg(session), echo=True)
        return brcddb_common.EXIT_STATUS_ERROR

    try:  # I always put all code after login in a try/except in case of a code bug or network error, I still logout

        # Capture the initial switch and port information along with the first set of statistics.
        brcdapi_log.log('Capturing initial data', echo=True)
        brcddb_int.get_batch(session, proj_obj, _uris, fid)  # Captured data is put in proj_obj
        chassis_obj = proj_obj.r_chassis_obj(session.get('chassis_wwn'))
        if chassis_obj.r_is_vf_enabled():
            if fid is None:
                fid = 128
            base_switch_obj = chassis_obj.r_switch_obj_for_fid(fid)
        else:
            try:
                base_switch_obj = chassis_obj.r_switch_objects()[0]
            except IndexError:
                brcdapi_log.log('No switches found in ' + brcddb_chassis.best_chassis_name(chassis_obj, wwn=True),
                                echo=True)
                base_switch_obj = None
        if base_switch_obj is None:
            brcdapi_log.log('Switch for FID ' + str(fid) + ' not found.', echo=True)
            return _wrap_up(session, proj_obj, base_switch_wwn, switch_obj_l, brcddb_common.EXIT_STATUS_ERROR, out_f)
        base_switch_wwn = base_switch_obj.r_obj_key()
        if base_switch_obj.r_fabric_key() is None:
            base_switch_obj.s_fabric_key(base_switch_wwn)  # Fake out a fabric principal if we don't have one
            proj_obj.s_add_fabric(base_switch_wwn)
        brcddb_int.get_batch(session, proj_obj, _uris_2, fid)  # Captured data is put in proj_obj

        # Get the first sample
        stats_buf = 'running/brocade-interface/' + brcdapi_util.stats_uri
        last_time = time.time()
        last_stats = brcddb_int.get_rest(session, stats_buf, base_switch_obj, fid)
        for p in last_stats.get(brcdapi_util.stats_uri):
            base_switch_obj.r_port_obj(p.get('name')).s_new_key(brcdapi_util.stats_uri, p)

        # Now start collecting the port and interface statistics
        for i in range(0, max_p):
            x = pct - (time.time() - last_time)
            if not _DEBUG:
                time.sleep(_MIN_POLL if x < _MIN_POLL else x)
            switch_obj = proj_obj.s_add_switch(base_switch_wwn + '-' + str(i))
            last_time = time.time()

            # Get the port configuration stuff. This is only used for reporting.
            obj = brcddb_int.get_rest(session, 'running/brocade-interface/fibrechannel', switch_obj, fid)
            if fos_auth.is_error(obj):  # We typically get here when the login times out or network fails.
                brcdapi_log.log('Error encountered. Data collection limited to ' + str(i) + ' samples.',
                                echo=True)
                _wrap_up(session, proj_obj, base_switch_wwn, switch_obj_l, brcddb_common.EXIT_STATUS_ERROR, out_f)
                return brcddb_common.EXIT_STATUS_ERROR
            for port_d in obj.get('fibrechannel'):
                switch_obj.s_add_port(port_d.get('name')).s_new_key('fibrechannel', port_d)

            # Get the port statistics
            obj = brcddb_int.get_rest(session, stats_buf, switch_obj, fid)
            if fos_auth.is_error(obj):  # We typically get here when the login times out or network fails.
                brcdapi_log.log('Error encountered. Data collection limited to ' + str(i) + ' samples.',
                                echo=True)
                _wrap_up(session, proj_obj, base_switch_wwn, switch_obj_l, brcddb_common.EXIT_STATUS_ERROR, out_f)
                return brcddb_common.EXIT_STATUS_ERROR

            # Replace values with simulated values
            for port_d in obj.get('fibrechannel-statistics'):
                try:
                    temp_d = _synthetic_values_d[port_d.get('name')]
                    for key, value in temp_d['value_l'][temp_d['i']].items():
                        port_d[key] = value
                    temp_d['i'] = temp_d['i'] + 1 if temp_d['i'] < len(temp_d['value_l']) else 0
                # IndexError occurs if the port is in _synthetic_values_d with an empty list
                except (KeyError, IndexError):
                    pass

            # Add the differences to a new sample
            for port_d in _stats_diff(last_stats, obj).get(brcdapi_util.stats_uri):
                switch_obj.s_add_port(port_d.get('name')).s_new_key(brcdapi_util.stats_uri, port_d)
            switch_obj_l.append(switch_obj)
            last_stats = obj

        return _wrap_up(session, proj_obj, base_switch_wwn, switch_obj_l, brcddb_common.EXIT_STATUS_OK, out_f)

    except (KeyboardInterrupt, http.client.CannotSendRequest, http.client.ResponseNotReady):
        return _wrap_up(session, proj_obj, base_switch_wwn, switch_obj_l, brcddb_common.EXIT_STATUS_OK, out_f)
    except BaseException as e:
        brcdapi_log.log(['Error capturing statistics. ' + _EXCEPTION_MSG, 'Exception: '] + class_util.format_obj(e),
                        echo=True)
        return _wrap_up(session, proj_obj, base_switch_wwn, switch_obj_l, brcddb_common.EXIT_STATUS_ERROR, out_f)


def _get_input():
    """Parses the module load command line

    :return: Exit code. See exist codes in brcddb.brcddb_common
    :rtype: int
    """
    global __version__, _input_d, _MIN_POLL, _MIN_SAMPLES

    ec = brcddb_common.EXIT_STATUS_OK

    # Get command line input
    buf = 'Collect port statistics at a specified poll interval. Use Control-C to stop data collection and write report'
    try:
        args_d = gen_util.get_input(buf, _input_d)
    except TypeError:
        return brcddb_common.EXIT_STATUS_INPUT_ERROR  # gen_util.get_input() already posted the error message.

    # Set up logging
    brcdapi_rest.verbose_debug(args_d['d'])
    brcdapi_log.open_log(
        folder=args_d['log'],
        suppress=args_d['sup'],
        no_log=args_d['nl'],
        version_d=brcdapi_util.get_import_modules()
    )

    # Is the poll interval valid?
    args_p_help = ''
    if args_d['p'] < _MIN_POLL:
        args_p_help = ' *ERROR: Must be >= ' + str(_MIN_POLL) + ' seconds'
        ec = brcddb_common.EXIT_STATUS_INPUT_ERROR

    # Are the number of samples valid?
    args_m_help = ''
    if args_d['m'] == 0:
        args_m_help = ' Using the default of ' + str(_DEFAULT_MAX_SAMPLE)
        args_m = _DEFAULT_MAX_SAMPLE
    else:
        args_m = args_d['m']
        if args_m < _MIN_SAMPLES:
            args_m_help = ' *ERROR: Must be >= ' + str(_MIN_SAMPLES)
            ec = brcddb_common.EXIT_STATUS_INPUT_ERROR

    # Command line feedback
    ml = [
        os.path.basename(__file__) + ', ' + __version__,
        'IP Address, -ip:    ' + brcdapi_util.mask_ip_addr(args_d['ip']),
        'User ID, -id:       ' + args_d['id'],
        'FID:                ' + str(args_d['fid']),
        'Samples, -m:        ' + str(args_d['m']) + args_m_help,
        'Poll Interval, -p:  ' + str(args_d['p']) + args_p_help,
        'Output File, -o:    ' + args_d['o'],
        'Log, -log:          ' + str(args_d['log']),
        'No log, -nl:        ' + str(args_d['nl']),
        'Debug, -d:          ' + str(args_d['d']),
        'Suppress, -sup:     ' + str(args_d['sup']),
        '',
    ]
    brcdapi_log.log(ml, echo=True)

    return ec if ec != brcddb_common.EXIT_STATUS_OK else\
        pseudo_main(args_d['ip'], args_d['id'], args_d['pw'], args_d['s'], args_d['fid'], args_d['p'], args_m,
                    brcdapi_file.full_file_name(args_d['o'], '.json'))


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
