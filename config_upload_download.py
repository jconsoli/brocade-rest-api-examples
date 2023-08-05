#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2023 Consoli Solutions, LLC.  All rights reserved.
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
:mod:`config_upload_download.py` - configupload/download examples.

**Description**

    Examples on how to upload and download configuration data in-band using the operations/configupload and
    operations/configdownload URI branches in the FOS API. It is equivalent to the FOS configupload and configdownload
    commands.

    Primary methods of interest are:

    * _action_upload()
    * _action_download()

    To set break points for experimentation purposes, search for _DEBUG. This allows you to simulate command line input.

**WARNINGS**

    * These are programming examples on how to use the interface and set the request options only. It is up to the
      programmer using these examples to determine if the options are valid or make sense.
    * Certain test scenarios always returned "in-progress" status with 0% complete. FOS 9.2.0 is recommended.
    * The "operations/show-status/message-id/xxxx" returns status for the show-status request, not the original request.
      Status and error messages associated with original request are embedded in human readable format in the "message"
      portion of the response. This means an operations/configupload or operations/configdownload request can fail with
      status=200. Human intervention is required to determine if the config upload/download completed successfully.
    * Testing was limited to the mechanics of the protocol interface only. Certain observations made during that testing
      is reported in these comments but should not be construed as more extensive testing.

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 4.0.0     | 04 Aug 2023   | Re-Launch                                                                         |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""

__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2023 Consoli Solutions, LLC'
__date__ = '04 August 2023'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack_consoli@yahoo.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.0'

import argparse
import pprint
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as fos_auth
import brcdapi.log as brcdapi_log
import brcdapi.util as brcdapi_util
import brcdapi.file as brcdapi_file

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation
_DEBUG = False   # When True, use _DEBUG_xxx below instead of parameters passed from the command line.
_DEBUG_ip = 'xx.xxx.x.xxx'
_DEBUG_id = 'admin'
_DEBUG_pw = 'password'
_DEBUG_s = 'self'  # Use None or 'none' for HTTP.
_DEBUG_fid = '1'
_DEBUG_sfid = None
_DEBUG_a = 'down'
_DEBUG_scope = 'fabric-id'
_DEBUG_pa = False
_DEBUG_f = 'test/fid_1'
_DEBUG_d = False  # When True, all content and responses are formatted and printed (pprint) to the log.
_DEBUG_sup = False
_DEBUG_log = '_logs'
_DEBUG_nl = False

_MAX_CHECK = 13  # Maximum number of times to poll the switch for configupload/download completion status
_WAIT = 10  # Wait time before each status poll check

# _scope_d: Key are the possible values for "config-upload-download-option". Value: True: add "vf-id" & "source-vf-id"
_scope_d = {'chassis': False, 'switch': True, 'virtual-fabric': True, 'fabric-id': True, 'all': False}


####################################################################
#
#       Action methods for _action_tbl_d
#
####################################################################
def _action_upload(param_d):
    """Uploads the configuration from the chassis.

    :param param_d: Dictionary of input parameters
    :type param_d: dict
    :return: List of error messages
    :rtype: list
    """
    global _scope_d

    el = list()  # Return error message list

    # Upload the configuration
    content_d = {'configupload-parameters': {'config-upload-download-option': param_d['scope'],
                                             'port-to-area': param_d['pa']}}
    # content_d = {'configupload-parameters': {'config-upload-download-option': param_d['scope']}}
    if _scope_d[param_d['scope']]:
        content_d['configupload-parameters'].update({'vf-id': param_d['fid']})
    brcdapi_log.log('Uploading configuration', echo=True)
    obj = brcdapi_rest.operations_request(param_d['session'], 'operations/configupload', 'POST', content_d)
    if fos_auth.is_error(obj):
        el.extend(['FOS Error:', fos_auth.formatted_error_msg(obj), 'Failed to upload configuration.'])
        return el

    try:
        with open(param_d['file'], 'w') as f:
            f.write(obj['configupload-operation-status']['config-output-buffer'])
        f.close()
    except (FileExistsError, FileNotFoundError):
        el.append('The path specified in ' + param_d['file'] + ' does not exist.')
    except PermissionError:
        el.append('You do not have access rights to write to the path specified in ' + param_d['file'])
    except (AttributeError, KeyError):
        el.extend(['Invalid response from FOS:', pprint.pformat(obj)])

    return el


def _action_download(param_d):
    """Configuration download. See _action_upload for input/return values"""
    global _WAIT, _MAX_CHECK, _scope_d

    el = list()  # Return error message list

    # Read the configuration file
    try:
        with open(param_d['file']) as f:
            config = f.read()
        f.close()

    except FileNotFoundError:
        el.append('File ' + param_d['file'] + ' not found.')
        return el
    except FileExistsError:
        el.append('The path specified in ' + param_d['file'] + ' does not exist.')
        return el
    except PermissionError:
        el.append('You do not have access rights to read ' + param_d['file'])
        return el

    # Download the configuration
    fid = param_d['fid']  # Just to save some typing
    brcdapi_log.log('Downloading config for FID ' + str(fid), echo=True)
    content_d = {'configdownload-parameters': {
        'config-upload-download-option': param_d['scope'],
        'port-to-area': param_d['pa'],
        'config-input-buffer': config}
    }
    if _scope_d[param_d['scope']]:
        content_d['configdownload-parameters'].update({'vf-id': fid, 'source-vf-id': param_d['sfid']})
    obj = brcdapi_rest.operations_request(param_d['session'],
                                          'operations/configdownload',
                                          'POST',
                                          content_d,
                                          wait_time=_WAIT,
                                          max_try=_MAX_CHECK)
    if fos_auth.is_error(obj):
        brcdapi_log.log(['Error downloading config for FID ' + str(fid),
                         fos_auth.formatted_error_msg(obj)])
        el.append('Failed to restore FID ' + str(fid) + '. Check the log for details.')
    else:
        el.append('Successfully restored FID ' + str(fid))

    return el


_action_tbl_d = dict(up=_action_upload, upload=_action_upload, down=_action_download, download=_action_download)


def _get_input():
    """Parses the module load command line

    :return ip: Switch IP address
    :rtype ip: str
    :return id: User ID
    :rtype id: str
    :return pw: User password
    :rtype ip: str
    :return sec: Secure method. None for HTTP, otherwise the certificate or 'self' if self signed
    :rtype sec: str, None
    :return fid: FID associated with the ports, port_l
    :rtype fid: str
    :return port_l: List of ports to operate on
    :rtype port_l: list
    :return action: List of actions to take
    :rtype action: list
    """
    global _scope_d, _action_tbl_d, _DEBUG, _DEBUG_ip, _DEBUG_id, _DEBUG_pw, _DEBUG_s, _DEBUG_f, _DEBUG_fid
    global _DEBUG_sfid, _DEBUG_a, _DEBUG_scope, _DEBUG_pa, _DEBUG_d, _DEBUG_sup, _DEBUG_log, _DEBUG_nl

    ec = 0  # Return error code
    valid_actions = ', '.join([str(k) for k in _action_tbl_d.keys()])

    if _DEBUG:
        args_ip, args_id, args_pw, args_s, args_f, args_fid, args_sfid, args_a, args_scope = \
            _DEBUG_ip, _DEBUG_id, _DEBUG_pw, _DEBUG_s, _DEBUG_f, _DEBUG_fid, _DEBUG_sfid, _DEBUG_a, _DEBUG_scope
        args_pa, args_d, args_sup, args_log, args_nl = _DEBUG_pa, _DEBUG_d, _DEBUG_sup, _DEBUG_log, _DEBUG_nl
    else:
        buf = 'Initially developed as programming examples. A shell interface was added to be run as a stand-alone '\
              'utility to modify configurations.'
        parser = argparse.ArgumentParser(description=buf)
        parser.add_argument('-ip', help='(Required) IP address', required=True)
        parser.add_argument('-id', help='(Required) User ID', required=True)
        parser.add_argument('-pw', help='(Required) Password', required=True)
        parser.add_argument('-s', help="(Optional) Default is HTTP. Use -s self for HTTPS mode.", required=False)
        parser.add_argument('-f', help='(Required) upload/download file name. ".txt" is automatically appended',
                            required=True)
        buf = 'Required when -scope is: ' + ', '.join([str(k) for k in _scope_d.keys() if _scope_d[k]])
        parser.add_argument('-fid', help=buf, required=False)
        buf = 'Optional. Source FID. Relevant to download action only. See -fid. This parameter allows you to specify '\
              'a different source FID to download from. By default, the source FID and the target FID are the same.'
        parser.add_argument('-sfid', help=buf, required=False)
        parser.add_argument('-a', help='(Required) Action. Options are: ' + valid_actions, required=True)
        buf = ', '.join([str(k) for k in _scope_d.keys()])
        parser.add_argument('-scope', help='(Required) Scope. Options are: ' + buf, required=True)
        buf = '(Optional) No parameters. If set, include the port-to-area addressing mode. Typically only used for '\
              'switches configured for ficon (mainframe).'
        parser.add_argument('-pa', help=buf, action='store_true', required=False)
        buf = '(Optional) Enable debug logging. Prints the formatted data structures (pprint) to the log and console.'
        parser.add_argument('-d', help=buf, action='store_true', required=False)
        buf = '(Optional) No parameters. Suppress all output to STD_IO except the exit message. Useful with batch '\
              'processing'
        parser.add_argument('-sup', help=buf, action='store_true', required=False)
        buf = '(Optional) Directory where log file is to be created. Default is to use the current directory. The log' \
              ' file name will always be "Log_xxxx" where xxxx is a time and date stamp.'
        parser.add_argument('-log', help=buf, required=False, )
        buf = '(Optional) No parameters. When set, a log file is not created. The default is to create a log file.'
        parser.add_argument('-nl', help=buf, action='store_true', required=False)
        args = parser.parse_args()
        args_ip, args_id, args_pw, args_s, args_f, args_fid, args_sfid, args_a, args_scope, args_pa = \
            args.ip, args.id, args.pw, args.s, args.f, args.fid, args.sfid, args.a, args.scope, args.pa
        args_d, args_sup, args_log, args_nl = args.d, args.sup, args.log, args.nl

    # Set up the log and debug parameters
    if args_d:
        brcdapi_rest.verbose_debug = True
    if args_sup:
        brcdapi_log.set_suppress_all()
    if not args_nl:
        brcdapi_log.open_log(args_log)

    # Validate actions, -a
    action_buf = args_a
    if args_a not in _action_tbl_d:
        action_buf += ' INVALID. Valid actions are: ' + valid_actions
        ec = -1

    # Validate scope, -scope
    scope_buf = args_scope
    if args_scope not in _scope_d:
        scope_buf += ' INVALID. Valid scope values are: ' + ', '.join([str(k) for k in _scope_d.keys()])
        ec = -1

    # Validate the FID, -fid
    fid_buf, sfid_buf, fid, sfid = str(args_fid), str(args_sfid), None, None
    if isinstance(args_fid, str):
        fid = int(args_fid) if args_fid.isnumeric() else 0
        if fid < 1 or fid > 128:
            fid_buf += ' INVALID: Fabric ID must be an integer in the range 1-128'
    elif bool(_scope_d.get(args_scope)):
            fid_buf = ' Missing. Required for this action.'
            ec = -1
    if isinstance(args_sfid, str):
        sfid = int(args_sfid) if args_sfid.isnumeric() else 0
        if sfid < 1 or fid > 128:
            sfid_buf += ' INVALID: Fabric ID must be an integer in the range 1-128'
    else:
        sfid = fid

    # User feedback
    ml = ['config_upload_download.py: ' + __version__,
          'IP address, -ip:           ' + brcdapi_util.mask_ip_addr(args_ip),
          'ID, -id:                   ' + args_id,
          'Secure, -s:                ' + str(args_s),
          'File, -f:                  ' + args_f,
          'Fabric ID, -fid:           ' + fid_buf,
          'Source Fabric ID, -sfid:   ' + sfid_buf,
          'Actions, -a:               ' + action_buf,
          'Scope, -scope:             ' + args_scope + scope_buf,
          'port-to-area, -pa:         ' + str(args_pa)]
    if _DEBUG:
        ml.insert(0, 'WARNING!!! Debug is enabled')
    brcdapi_log.log(ml, echo=True)

    param_d = dict(ip=args_ip,
                   id=args_id,
                   pw=args_pw,
                   sec=args_s,
                   file=brcdapi_file.full_file_name(args_f, '.txt'),
                   fid=fid,
                   sfid=sfid,
                   action=args_a,
                   scope=args_scope,
                   pa=args_pa)

    return ec, param_d


def pseudo_main():
    """Basically the main().

    :return: Exit code
    :rtype: int
    """
    # Get and validate command line input
    ec, param_d = _get_input()
    if ec != 0:
        return ec

    # Login
    brcdapi_log.log('Attempting login', echo=True)
    param_d['session'] = brcdapi_rest.login(param_d['id'], param_d['pw'], param_d['ip'], param_d['sec'])
    if fos_auth.is_error(param_d['session']):
        brcdapi_log.log(['Login failed:', fos_auth.formatted_error_msg(param_d['session'])], echo=True)
        return -1
    brcdapi_log.log('Login succeeded', echo=True)

    try:  # I always do a try in code development so that if there is a code bug, I still log out.
        brcdapi_log.log(_action_tbl_d[param_d['action']](param_d), echo=True)

    except BaseException as e:
        brcdapi_log.log(['Programming error encountered. Exception is:', pprint.pformat(e)], echo=True)
        ec = -1

    # Logout
    obj = brcdapi_rest.logout(param_d['session'])
    if fos_auth.is_error(obj):
        brcdapi_log.log(['Logout failed:', fos_auth.formatted_error_msg(obj)], echo=True)
    else:
        brcdapi_log.log('Logout succeeded', echo=True)

    return ec


###################################################################
#
#                    Main Entry Point
#
###################################################################
if _DOC_STRING:
    print('_DOC_STRING is True. No processing')
    exit(0)

_ec = pseudo_main()
brcdapi_log.close_log('Processing complete. Exit status: ' + str(_ec), echo=True)
exit(_ec)
