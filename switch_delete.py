#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2020, 2021 Jack Consoli.  All rights reserved.
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
:mod:`switch_delete.py` - Examples on how to delete a logical switch.

Scroll all the way to the bottom to find the entry point.

**WARNING**

    This module was written to provide programming examples. It does not have a full user interface or robust error
    checking. It has not undergone the type of rigorous testing that a supported product would undergo.

**Description**

    Example on how to delete a logical switch. Since the brcdapi.switch.delete_switch() method does everything you need
    to delete a switch, this can be used as a stand alone module. Deletes a logical switch. To incorporate this
    functionality into your own code, just follow pseudo_main().

    Although GE ports can be deleted, at this time there isn't an example of how to tear down the circuits and tunnels.
    Tearing down the circuits and tunnels is required before the ports can be moved to another logical switch.

    Switch delete notes (this is all checked and taken care of in brcdapi.switch.delete_switch():

    * You cannot delete the default logical switch.
    * All ports in the switch being deleted must be moved to another logical switch. brcdapi.switch.delete_switch()
      moves them to the default logical switch.
    * Ports must be at there factory default configuration before they can be moved.

**Example**

To delete the logical switch whose FID is 20:

py switch_delete.py -ip xx.x.xxx.10 -id admin -pw password -s self -echo -fid 20

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 3.0.0     | 27 Nov 2020   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.1     | 09 Jan 2021   | Open log file.                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 3.0.2     | 13 Feb 2021   | Added # -*- coding: utf-8 -*-                                                     |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2020, 2021 Jack Consoli'
__date__ = '13 Feb 2021'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '3.0.2'

import argparse
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.pyfos_auth as pyfos_auth
import brcdapi.log as brcdapi_log
import brcdapi.switch as brcdapi_switch

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation
_DEBUG = False   # When True, use _DEBUG_IP, _DEBUG_ID, _DEBUG_PW, _DEBUG_OUTF, and _DEBUG_VERBOSE
_DEBUG_IP = '10.8.105.10'
_DEBUG_ID = 'admin'
_DEBUG_PW = 'password'
_DEBUG_SEC = 'self'  # Use None or 'none' for HTTP. Use the certificate if HTTPS and not self signed
_DEBUG_FID = '21'
_DEBUG_ECHO = True  # When true, echoes details of ports being moved.
_DEBUG_VERBOSE = False  # When True, all content and responses are formatted and printed (pprint).
_DEBUG_LOG = '_logs'
_DEBUG_NL = False


def parse_args():
    """Parses the module load command line

    :return ip: Switch IP address
    :rtype ip: str
    :return id: User ID
    :rtype id: str
    :return pw: User password
    :rtype ip: str
    :return sec: Secure method. None for HTTP, otherwise the certificate or 'self' if self signed
    :rtype sec: str, None
    :return fids: FID(s) to delete
    :rtype fids: str
    :return vd: Verbose debug flag.
    :rtype vd: bool
    """
    global _DEBUG_IP, _DEBUG_ID, _DEBUG_PW, _DEBUG_SEC, _DEBUG_FID, _DEBUG_ECHO, _DEBUG_VERBOSE, _DEBUG_LOG, _DEBUG_NL

    if _DEBUG:
        return _DEBUG_IP, _DEBUG_ID, _DEBUG_PW, _DEBUG_SEC, _DEBUG_FID, _DEBUG_ECHO, _DEBUG_VERBOSE, _DEBUG_LOG, \
               _DEBUG_NL
    else:
        parser = argparse.ArgumentParser(description='Delete a logical switch.')
        parser.add_argument('-ip', help='(Required) IP address', required=True)
        parser.add_argument('-id', help='(Required) User ID', required=True)
        parser.add_argument('-pw', help='(Required) Password', required=True)
        parser.add_argument('-fid', help='(Required) Virtual Fabric ID to delete.', required=True)
        parser.add_argument('-s', help="(Optional) Default is HTTP. CA or self for HTTPS mode.", required=False)
        buf = '(Optional) Echoes activity detail to STD_OUT. Recommended because there are multiple operations that '\
              'can be very time consuming.'
        parser.add_argument('-echo', help=buf, action='store_true', required=False)
        buf = '(Optional) Enable debug logging. Prints the formatted data structures (pprint) to the log and console.'
        parser.add_argument('-d', help=buf, action='store_true', required=False)
        buf = '(Optional) Directory where log file is to be created. Default is to use the current directory. The log ' \
              'file name will always be "Log_xxxx" where xxxx is a time and date stamp.'
        parser.add_argument('-log', help=buf, required=False, )
        buf = '(Optional) No parameters. When set, a log file is not created. The default is to create a log file.'
        parser.add_argument('-nl', help=buf, action='store_true', required=False)
        args = parser.parse_args()
        return args.ip, args.id, args.pw, args.s, args.fid, args.echo, args.d, args.log, args.nl


def pseudo_main():
    """Basically the main().

    :return: Exit code
    :rtype: int
    """
    ec = 0

    # Get and condition the command line input
    ml = ['WARNING!!! Debug is enabled'] if _DEBUG else list()
    ip, user_id, pw, sec, fid, echo, vd, log, nl = parse_args()
    if vd:
        brcdapi_rest.verbose_debug = True
    if sec is None:
        sec = 'none'
        ml.append('Access:    HTTP')
    else:
        ml.append('Access:    HTTPS')
    if not nl:
        brcdapi_log.open_log(log)
    try:
        fid = int(fid)
        if fid < 1 or fid > 128:
            raise
    except:
        brcdapi_log.log('Invalid fid. FID must be an integer between 1-128', True)
        return -1
    ml.append('FID:       ' + str(fid))
    brcdapi_log.log(ml, True)
    echo = False if echo is None else echo

    # Login
    brcdapi_log.log('Attempting login', True)
    session = brcdapi_rest.login(user_id, pw, ip, sec)
    if pyfos_auth.is_error(session):
        brcdapi_log.log(['Login failed. API error message is:', pyfos_auth.formatted_error_msg(session)], True)
        return -1
    brcdapi_log.log('Login succeeded.', True)

    # Delete the switch
    try:  # I always do a try in code development so that if there is a code bug, I still log out.
        buf = 'Deleting FID ' + str(fid) + '. This will take about 20 sec per switch + 25 sec per group of 32 ports.'
        brcdapi_log.log(buf, True)
        obj = brcdapi_switch.delete_switch(session, fid, echo)
        if pyfos_auth.is_error(obj):
            ml = ['Error deleting FID ' + str(fid)]
            ml.append(pyfos_auth.formatted_error_msg(obj))
            brcdapi_log.log(ml, True)
            ec = -1

    except:
        brcdapi_log.log('Encountered a programming error', True)
        ec = -1

    # Logout
    obj = brcdapi_rest.logout(session)
    if pyfos_auth.is_error(obj):
        brcdapi_log.log(['Logout failed. API error message is:',  pyfos_auth.formatted_error_msg(obj)], True)
    return ec

###################################################################
#
#                    Main Entry Point
#
###################################################################


_ec = 0
if _DOC_STRING:
    print('_DOC_STRING is True. No processing')
else:
    _ec = pseudo_main()
    brcdapi_log.close_log('Processing complete. Exit status: ' + str(_ec), True)
exit(_ec)
