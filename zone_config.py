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
:mod:`zone_config.py` - Examples on how to create, modify and delete zone objects using the brcdapi.zone library.

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 1.x.x     | 03 Jul 2019   | Experimental                                                                      |
    | 2.x.x     |               |                                                                                   |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.0     | 29 Jul 2020   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.1     | 09 Jan 2021   | Open log file.                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.2     | 13 Feb 2021   | Added # -*- coding: utf-8 -*-                                                     |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2019, 2020, 2021 Jack Consoli'
__date__ = '13 Feb 2021'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.2'

import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.pyfos_auth as pyfos_auth
import brcdapi.log as brcdapi_log
import brcdapi.zone as brcdapi_zone

# Not all combinations of the control flags below make sense. Some combinations may cause conflicts.
_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation
_DEBUG_CREATE_ALIASES = True
_DEBUG_CREATE_ZONES = True
_DEBUG_CREATE_ZONECFGS = True
_DEBUG_DELETE_ZONECFGS = False
_DEBUG_DELETE_ZONES = False
_DEBUG_DELETE_ALIASES = False
_DEBUG_MODIFY_ZONE = False
_DEBUG_MODIFY_ZONECFG = True
_DEBUG_ZONECFG = 'zonecfg_for_delete'  # Zone configuration to enable when _DEBUG_ENABLE_ZONECFG is True
_DEBUG_ENABLE_ZONECFG = False
_DEBUG_DISABLE_ZONECFG = False
_DEBUG_LOG = '_logs'
_DEBUG_NL = False

# Sample data for creating zones below:
_DEBUG_ALIAS_LIST = [
    dict(name='Target_0', members=['50:0c:00:11:0d:bb:42:00']),
    dict(name='Target_1', members=['50:0c:00:11:0d:bb:42:01']),
    dict(name='Server_0', members=['10:00:00:90:fa:f0:93:00']),
    dict(name='Server_1', members=['10:0c:00:11:0d:bb:42:01']),
    dict(name='Server_2', members=['10:0c:00:11:0d:bb:42:02']),
    dict(name='Server_3', members=['10:0c:00:11:0d:bb:42:03']),
    dict(name='alias_0_for_delete', members=['20:0c:00:11:0d:bb:42:00']),
    dict(name='alias_1_for_delete', members=['20:0c:00:11:0d:bb:42:01']),
]
_DEBUG_ZONE_LIST = [
    dict(name='T0_S0', type=0, members=['Target_0', 'Server_0']),
    dict(name='T0_S1', type=0, members=['Target_0', 'Server_1']),
    dict(name='Peer_T1_S2_S3', type=1, members=['Server_2', 'Server_3'], pmembers=['Target_1']),
    dict(name='zone_0_for_delete', type=0, members=['alias_0_for_delete', 'alias_1_for_delete']),
]
_DEBUG_ZONECFG_LIST = {
    'zonecfg_0': ['T0_S0', 'T0_S1', 'zone_0_for_delete'],
    'zonecfg_1': ['T0_S0', 'Peer_T1_S2_S3'],
    'zonecfg_for_delete': ['zone_0_for_delete'],
}
_DEBUG_ZONECFG_DEL_LIST = ['zonecfg_for_delete', ]
_DEBUG_ZONE_DEL_LIST = ['zone_0_for_delete', ]
_DEBUG_ALIAS_DEL_LIST = ['alias_0_for_delete', 'alias_1_for_delete', ]
_DEBUG_ALIAS_MODIFY_LIST = [dict(name='Server_3', members=['10:0c:00:11:0d:bb:42:ff'])]
_DEBUG_ZONE_MODIFY = 'Peer_T1_S2_S3'
_DEBUG_ZONE_ADD_MEMS = ['Server_1', 'Server_0']  # Members to add to _DEBUG_ZONE_MODIFY when _DEBUG_MODIFY_ZONE is True
_DEBUG_ZONE_DEL_MEMS = ['Server_2']  # Members to remove from _DEBUG_ZONE_MODIFY when _DEBUG_MODIFY_ZONE is True
_DEBUG_ZONE_ADD_PMEMS = ['Target_2']  # Principal members to add to _DEBUG_ZONE_MODIFY when _DEBUG_MODIFY_ZONE is True
_DEBUG_ZONE_DEL_PMEMS = ['Target_1']   # Principal members to remove from _DEBUG_ZONE_MODIFY, _DEBUG_MODIFY_ZONE is True
_DEBUG_ZONECFG_MODIFY = 'zonecfg_0'
_DEBUG_ZONECFG_ADD_MEMS = ['Peer_T1_S2_S3']
_DEBUG_ZONECFG_DEL_MEMS = ['zone_0_for_delete']

_DEBUG_IP = '10.8.105.10'
_DEBUG_ID = 'admin'
_DEBUG_PW = 'password'
_DEBUG_SEC = 'self'  # 'none'
_DEBUG_FID = 20
_DEBUG_VERBOSE = False  # When True, all content and responses are formatted and printed.


def _is_error(session, fid, obj):
    """Tests to see if the API returned an error and aborts the zoning transaction if it did

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    :param fid: Logical FID number to be created. Valid FISs are 1-128. Will return an error if the FID already exists
    :type fid: int
    :return: True if an error was returned
    :rtype: bool
    """
    if pyfos_auth.is_error(obj):
        # Commented out code below is redundant because brcdapi.zone methods already print formatted error messages to
        # the log. Should you need to format error objects into human readable text:
        # brcdapi_log.log(pyfos_auth.formatted_error_msg(obj), True)
        brcdapi_zone.abort(session, fid, True)
        return True
    else:
        return False


def _logout(session):
    """Logout and post message if the logout failed

    :param session: Session object returned from brcdapi.pyfos_auth.login()
    :type session: dict
    """
    obj = brcdapi_rest.logout(session)
    if pyfos_auth.is_error(obj):
        brcdapi_log.log('Logout failed:\n' + pyfos_auth.formatted_error_msg(obj), True)


def pseudo_main(user_id, pw, ip, sec, vd, log, nl):
    """Basically the main().

    :param user_id: User ID
    :type user_id: str
    :param pw: Password
    :type pw: str
    :param ip: IP address
    :type ip: str
    :param sec: Security. 'none' for HTTP, 'self' for self signed certificate, 'CA' for signed certificate
    :type sec: str
    :param vd: When True, enables debug logging
    :type vd: bool
    :return: Exit code
    :rtype: int
    """
    fid = _DEBUG_FID
    save_flag = False

    if vd:
        brcdapi_rest.verbose_debug = True
    if not nl:
        brcdapi_log.open_log(log)

    # Login
    brcdapi_log.log('Attempting login', True)
    session = brcdapi_rest.login(user_id, pw, ip, sec)
    if pyfos_auth.is_error(session):
        brcdapi_log.log('Login failed', True)
        brcdapi_log.log(pyfos_auth.formatted_error_msg(session), True)
        return -1
    brcdapi_log.log('Login succeeded', True)

    # A check sum is needed to save any updates
    checksum, obj = brcdapi_zone.checksum(session, fid, True)
    if checksum is None:
        _logout(session)
        return -1

    # try/except was so that during development a bug would not cause an abort and skip the logout
    try:
        # Create aliases
        if _DEBUG_CREATE_ALIASES:
            save_flag = True
            brcdapi_log.log('Creating aliases for fid: ' + str(fid), True)
            if _is_error(session, fid, brcdapi_zone.create_aliases(session, fid, _DEBUG_ALIAS_LIST, True)):
                _logout(session)
                return -1

        # Create zones
        if _DEBUG_CREATE_ZONES:
            save_flag = True
            brcdapi_log.log('Creating zones for fid: ' + str(fid), True)
            if _is_error(session, fid, brcdapi_zone.create_zones(session, fid, _DEBUG_ZONE_LIST, True)):
                _logout(session)
                return -1

        # Create zone configurations
        if _DEBUG_CREATE_ZONECFGS:
            save_flag = True
            brcdapi_log.log('Creating zone configurations for fid: ' + str(fid), True)
            for k, v in _DEBUG_ZONECFG_LIST.items():
                if _is_error(session, fid, brcdapi_zone.create_zonecfg(session, fid, k, v, True)):
                    _logout(session)
                    return -1

        # Delete zone configurations. If you are also deleting zones and a zone is in a defined configuration, the
        # delete will fail. This is why the zone configuration delete is first.
        if _DEBUG_DELETE_ZONECFGS:
            save_flag = True
            brcdapi_log.log('Deleting zone configurations for fid: ' + str(fid), True)
            for k in _DEBUG_ZONECFG_DEL_LIST:
                if _is_error(session, fid, brcdapi_zone.del_zonecfg(session, fid, k, True)):
                    _logout(session)
                    return -1

        # Delete zones. If you are also deleting aliases and an alias is in a defined zone, the delete will fail. This
        # is why the zone delete is before the alias delete.
        if _DEBUG_DELETE_ZONES:
            save_flag = True
            brcdapi_log.log('Deleting zones for fid: ' + str(fid), True)
            if _is_error(session, fid, brcdapi_zone.del_zones(session, fid, _DEBUG_ZONE_DEL_LIST, True)):
                _logout(session)
                return -1

        # Delete aliases
        if _DEBUG_DELETE_ALIASES:
            save_flag = True
            brcdapi_log.log('Deleting aliases for fid: ' + str(fid), True)
            if _is_error(session, fid, brcdapi_zone.del_aliases(session, fid, _DEBUG_ALIAS_DEL_LIST, True)):
                _logout(session)
                return -1

        if _DEBUG_MODIFY_ZONE:
            save_flag = True
            brcdapi_log.log('Modifying ZONE ' + _DEBUG_ZONE_MODIFY + ' in fid: ' + str(fid), True)
            if _is_error(session, fid,
                         brcdapi_zone.modify_zone(session, fid, _DEBUG_ZONE_MODIFY, _DEBUG_ZONE_ADD_MEMS,
                                                  _DEBUG_ZONE_DEL_MEMS, _DEBUG_ZONE_ADD_PMEMS, _DEBUG_ZONE_DEL_PMEMS,
                                                  True)):
                _logout(session)
                return -1

        if _DEBUG_MODIFY_ZONECFG:
            save_flag = True
            brcdapi_log.log('Modifying zone configuration ' + _DEBUG_ZONECFG_MODIFY + ' in fid: ' + str(fid), True)
            if len(_DEBUG_ZONECFG_ADD_MEMS) > 0:
                if _is_error(session, fid, brcdapi_zone.zonecfg_add(
                        session, fid, _DEBUG_ZONECFG_MODIFY, _DEBUG_ZONECFG_ADD_MEMS, True)):
                    _logout(session)
                    return -1
            if len(_DEBUG_ZONECFG_DEL_MEMS) > 0:
                if _is_error(session, fid, brcdapi_zone.zonecfg_remove(
                        session, fid, _DEBUG_ZONECFG_MODIFY, _DEBUG_ZONECFG_DEL_MEMS, True)):
                    _logout(session)
                    return -1

        if _DEBUG_DISABLE_ZONECFG:
            brcdapi_log.log('Disabling zone configuration ' + _DEBUG_ZONECFG + ', fid: ' + str(fid), True)
            if _is_error(session, fid, brcdapi_zone.disable_zonecfg(session, checksum, fid, _DEBUG_ZONECFG, True)):
                _logout(session)
                return -1
            save_flag = False  # Enabling a zone configuration does a configuration save

        if _DEBUG_ENABLE_ZONECFG:
            brcdapi_log.log('Enabling zone configuration ' + _DEBUG_ZONECFG + ', fid: ' + str(fid), True)
            if _is_error(session, fid, brcdapi_zone.enable_zonecfg(session, checksum, fid, _DEBUG_ZONECFG, True)):
                _logout(session)
                return -1
            save_flag = False  # Enabling a zone configuration does a configuration save

        if save_flag:
            if _is_error(session, fid, brcdapi_zone.save(session, fid, checksum, True)):
                _logout(session)
                return -1

    except:
        brcdapi_log.log('Logging out', True)
        _logout(session)
        brcdapi_log.exception('Exception', True)
        return -1

    brcdapi_log.log('Logging out', True)
    _logout(session)
    return 0


###################################################################
#
#                    Main Entry Point
#
###################################################################
if not _DOC_STRING:
    brcdapi_log.close_log(str(pseudo_main(_DEBUG_ID, _DEBUG_PW, _DEBUG_IP, _DEBUG_SEC, _DEBUG_VERBOSE, _DEBUG_LOG,
                                          _DEBUG_NL)))
