"""
Copyright 2023, 2024 Consoli Solutions, LLC.  All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
the License. You may also obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
language governing permissions and limitations under the License.

The license is free for single customer use (internal applications). Use of this module in the production,
redistribution, or service delivery for commerce requires an additional license. Contact jack@consoli-solutions.com for
details.

**Description**

Provides a single interface, _api_request(), to the RESTConf API in FOS.

Methods in this module are used to establish, modify, send requests, and terminate sessions. Also does the following:

    * Errors indicating zero length lists are converted to 0 length lists.
    * Errors for HA requests on fixed port switches are converted to 0 length lists.
    * Service unavailable - sleep 4 seconds and retry request up to 5 times
    * Fabric busy - wait 10 seconds and retry request up to 5 times
    * Service unavailable - wait 30 seconds and retry request
    * Debug mode allows for off-line work. Used with GET only
    * Raise KeyboardInterrupt, wait for requests to complete first if any

This is a thin interface. Logging is only performed in debug mode. It is the responsibility of the next higher layer,
such as the brcddb libraries, to control what gets printed to the log.

**Public Methods**

+-----------------------+-------------------------------------------------------------------------------------------+
| Method                | Description                                                                               |
+=======================+===========================================================================================+
| api_request()         | Single interface to the FOS REST API. Performs a Rest API request. Handles lowlevel       |
|                       | protocol errors and retries when the switch is busy. Also cleans up empty responses that  |
|                       | are returned as errors when they are just empty lists.                                    |
+-----------------------+-------------------------------------------------------------------------------------------+
| get_request()         | Fill out full URI and add debug wrapper around a GET before calling api_request()         |
+-----------------------+-------------------------------------------------------------------------------------------+
| login()               | Adds a wrapper around brcdapi.fos_auth.login()                                            |
+-----------------------+-------------------------------------------------------------------------------------------+
| logout()              | Adds a wrapper around brcdapi.fos_auth.logout()                                           |
+-----------------------+-------------------------------------------------------------------------------------------+
| send_request()        | Performs a Rest API request. Use get_request() for GET. Use this for all other            |
|                       | '/rest/running/' requests                                                                 |
+-----------------------+-------------------------------------------------------------------------------------------+
| set_url_options()     | Sets or clears the flag to issue an OPTIONS request prior to making any requests          |
+-----------------------+-------------------------------------------------------------------------------------------+
| operations_request()  | Performs an operations branch Rest API request and polls for status completion            |
+-----------------------+-------------------------------------------------------------------------------------------+

**Version Control**

+-----------+---------------+---------------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                           |
+===========+===============+=======================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                             |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Removed deprecated vfid_to_str()                                                      |
+-----------+---------------+---------------------------------------------------------------------------------------+
| 4.0.2     | 06 Dec 2024   | Replaced old header format with standard file header.                                 |
+-----------+---------------+---------------------------------------------------------------------------------------+
"""

__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2023, 2024 Consoli Solutions, LLC'
__date__ = '06 Dec 2024'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack@consoli-solutions.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.2'

import http.client
import re
import json
import time
import pprint
import os
import brcdapi.fos_cli as fos_cli
import brcdapi.fos_auth as fos_auth
import brcdapi.log as brcdapi_log
import brcdapi.util as brcdapi_util
import brcdapi.gen_util as gen_util

_OPTIONS_CHECK = False  # When True, makes sure OPTIONS was requested for each URI
_MAX_RETRIES = 5  # Maximum number of times to retry a request
_SVC_UNAVAIL_WAIT = 4  # Time, in seconds, to wait before retrying a request that returned 503, service unavailable
_FABRIC_BUSY_WAIT = 10  # Time, in seconds, to wait before retrying a request due to a fabric busy

_DEBUG = False
# _DEBUG_MODE is only used when _DEBUG == True as follows:
# 0 - Perform all requests normally. Write all responses to a file
# 1 - Do not perform any I/O. Read all responses from file into response and fake a successful login
_DEBUG_MODE = 1
# _DEBUG_PREFIX is only used when _DEBUG == True. Folder where all the json dumps of API requests are read/written.
_DEBUG_PREFIX = '200802_raw/'
_verbose_debug = False  # When True, prints data structures. Only useful for debugging.
_req_pending = False  # When True, the script is waiting for a response from a switch
_control_c_pend = False  # When True, a keyboard interrupt is pending a request to complete

# Programmer's Tip: If there is significant activity on the switch from other sources (AMP, BNA, SANNav, ...) it may
# take a long time for a response. Also, some operations, such as logical switch creation, can take 20-30 sec. If the
# timeout, _TIMEOUT, is too short, HTTP connect lib raises an exception but the session is not terminated on the switch.
_TIMEOUT = 60   # Number of seconds to wait for a response from the API.
_clean_debug_file = re.compile(r'[?=/]')


def _format_op_status(obj):
    """Formats an operations status response into a list of human-readable text. Intended for error reporting

    :param obj: Response from GET 'operations/show-status/message-id/'
    :type obj: dict
    :return error_l: List of object parameters (type str)
    :rtype: list
    """
    rl, status_d = list(), dict()

    # Get and validate the status response
    try:
        status_d = obj['show-status']
    except KeyError:
        rl.append('show-status missing in status response')
    except (AttributeError, TypeError):
        rl.append('Invalid status response type: ' + str(type(obj)))
    if len(rl) > 0:
        rl.append('Check the log for details')
        brcdapi_log.exception([rl[0], pprint.pformat(obj)])
        return rl

    for k0, v0 in status_d.items():
        if isinstance(v0, dict):
            for k1, v1 in v0.items():
                if k1 == 'message':
                    rl.extend(gen_util.convert_to_list(v1))
                else:  # Future proofing or bug in FOS
                    rl.append('Unknown key: ' + str(k1))
                    rl.extend([b.rstrip() for b in pprint.pformat(v1).replace('\r\n', '\n').split('\n')])
        else:
            rl.append(str(k0) + str(v0))

    return rl


def login(user_id, pw, ip_addr, https='none'):
    """Performs a login to the device using fos_auth.login

    :param user_id: User ID
    :type user_id: str
    :param pw: Password
    :type pw: str
    :param ip_addr: IP address
    :type ip_addr: str
    :param https: If 'CA' or 'self', uses https to login. Otherwise, http.
    :type https: str
    :return: Session object from brcdapi.fos_auth.login()
    :rtype: dict
    """
    global _DEBUG, _DEBUG_MODE

    # Login
    if _DEBUG and _DEBUG_MODE == 1:
        session = dict(_debug_name=ip_addr.replace('.', '_'), debug=True, uri_map=brcdapi_util.default_uri_map)
    else:
        session = fos_auth.login(user_id, pw, ip_addr, https)
        if isinstance(session, dict):
            if fos_auth.is_error(session):
                return session
        else:
            buf = 'Error. Additional info may be in the log. This typically occurs when the connection times out.'
            return fos_auth.create_error(brcdapi_util.HTTP_NOT_FOUND, buf, brcdapi_util.mask_ip_addr(ip_addr))
        if _DEBUG:
            session.update(_debug_name=ip_addr.replace('.', '_'))

    # Build the URI map. This map is used to build a full URI.
    obj = get_request(session, 'brocade-module-version')
    if fos_auth.is_error(obj):
        brcdapi_log.exception(brcdapi_util.mask_ip_addr(ip_addr) + ' ERROR: ' + fos_auth.formatted_error_msg(obj),
                              echo=True)
    else:
        try:
            brcdapi_util.add_uri_map(session, obj)
        except BaseException as e:
            logout(session)
            session = fos_auth.create_error(brcdapi_util.HTTP_INT_SERVER_ERROR,
                                            'Programming error encountered in brcdapi_util.add_uri_map.',
                                            msg=str(type(e)) + ': ' + str(e))

    return session


def logout(session):
    """Logout of a Rest API session using fos_auth.logout

    :param session: FOS session object
    :type session: dict
    """
    return fos_auth.logout(session) if not (_DEBUG and _DEBUG_MODE == 1) else dict()


def _set_methods(session, uri, op):
    """Set the value in the uri_map['op'] for the uri. Intended for error handling only.

    :param session: FOS session object
    :type session: dict
    :param uri: full URI
    :type uri: str
    :param op: Value to set in uri_map['op'].
    """
    cntl_d = brcdapi_util.session_cntl(session, uri)
    if isinstance(cntl_d, dict):
        cntl_d.update(op=op)


def _add_methods(session, http_response, in_uri):
    """Adds supported methods to the session

    :param session: FOS session object
    :type session: dict
    :param http_response: HTTPConnection.getresponse()
    :type http_response: HTTPResponse
    :param in_uri: full URI
    :type in_uri: str
    """
    i = in_uri.find('?')
    uri = in_uri[0:i].replace('/rest/', '') if i > 0 else in_uri.replace('/rest/', '')
    cntl_d = brcdapi_util.session_cntl(session, uri)
    if not isinstance(cntl_d, dict):
        return

    header_l = http_response.getheaders()
    if isinstance(header_l, (list, tuple)):
        for t in header_l:
            if len(t) >= 2:
                if isinstance(t[0], str) and t[0] == 'Allow':
                    cntl_d.update(op=brcdapi_util.op_yes, methods=t[1].replace(' ', '').split(','))
                    return
    cntl_d.update(op=brcdapi_util.op_not_supported)


def _check_methods(session, in_uri):
    """Checks to see if the supported methods for the uri have been added and if not, captures and adds them

    :param session: FOS session object
    :type session: dict
    :param in_uri: full URI
    :type in_uri: str
    :return: True if supported methods should be checked.
    :rtype: bool
    """
    global _OPTIONS_CHECK

    if not _OPTIONS_CHECK:
        return False

    i = in_uri.find('?')
    uri = in_uri[0:i].replace('/rest/', '') if i > 0 else in_uri.replace('/rest/', '')
    d = gen_util.get_key_val(session.get('uri_map'), uri)
    if d is None:
        d = gen_util.get_key_val(session.get('uri_map'), 'running/' + uri)  # The old way didn't include 'running/'
    if isinstance(d, dict):
        supported_methods = d.get('op')
        if isinstance(supported_methods, int):
            if supported_methods == brcdapi_util.op_no:
                return True
    elif 'brocade-module-version' not in uri:  # We haven't built the map yet so 'brocade-module-version' won't be there
        brcdapi_log.log('UNKNOWN URI: ' + uri + '. Check the log for details.', echo=True)  # For the user
        brcdapi_log.exception('UNKNOWN URI: ' + uri)  # For the log

    return False


def _api_request(session, uri, http_method, content):
    """Single interface to the FOS REST API. Performs a Rest API request. Only tested with GET, PATCH, POST, and DELETE.

    :param session: FOS session object
    :type session: dict
    :param uri: full URI
    :type uri: str
    :param http_method: Method for HTTP connect. 'GET', 'PATCH', 'POST', etc.
    :type http_method: str
    :param content: The content, in Python dict, to be converted to JSON and sent to switch.
    :type content: dict, None
    :return: Response and status in fos_auth.is_error() and fos_auth.formatted_error_msg() friendly format
    :rtype: dict
    """
    global _DEBUG, _DEBUG_MODE, _req_pending, _control_c_pend, _verbose_debug

    if _DEBUG and _DEBUG_MODE == 1 and http_method == 'OPTIONS':
        return dict(_raw_data=dict(status=brcdapi_util.HTTP_NO_CONTENT, reason='OK'))

    if http_method != 'OPTIONS' and _check_methods(session, uri):
        _api_request(session, uri, 'OPTIONS', dict())

    if _verbose_debug:
        buf = ['_api_request() - Send:', 'Method: ' + http_method, 'URI: ' + uri, 'content:', pprint.pformat(content)]
        brcdapi_log.log(buf, echo=True)

    # Set up the headers and JSON data
    header = session.get('credential')
    if header is None:
        return fos_auth.create_error(brcdapi_util.HTTP_FORBIDDEN, 'No login session')
    header.update({'Accept': 'application/yang-data+json'})
    header.update({'Content-Type': 'application/yang-data+json'})
    json_data = json.dumps(content) if content is not None and len(content) > 0 else None

    # Send the request and get the response
    http_response, _req_pending, conn = None, True, session.get('conn')
    try:
        conn.request(http_method, uri, json_data, header)
    except BaseException as e:
        obj = fos_auth.create_error(brcdapi_util.HTTP_NOT_FOUND,
                                    'Not Found',
                                    msg=['Typical of switch going offline or pre-FOS 8.2.1c',
                                         str(type(e)) + ': ' + str(e)])
        _req_pending = False
        if _control_c_pend:
            _control_c_pend = False
            raise KeyboardInterrupt
        
        if 'ip_addr' in session:
            obj.update(ip_addr=session.get('ip_addr'))
        return obj
    try:
        http_response = conn.getresponse()
        json_data = fos_auth.basic_api_parse(http_response)
        if isinstance(json_data, dict):
            if http_method == 'OPTIONS':
                if fos_auth.is_error(json_data):
                    _set_methods(session, uri, brcdapi_util.op_not_supported)
                else:
                    _add_methods(session, http_response, uri)
            if _verbose_debug:
                brcdapi_log.log(['_api_request() - Response:', pprint.pformat(json_data)], echo=True)
    except TimeoutError:
        buf = 'Time out processing ' + uri + '. Method: ' + http_method
        return fos_auth.create_error(brcdapi_util.HTTP_REQUEST_TIMEOUT, buf)
    except TypeError:
        # Apparently, the http lib intercepts Control-C. A TypeError is a by-product of how it's handled.
        _control_c_pend = True
    except http.client.RemoteDisconnected:
        buf = 'Disconnect while processing ' + uri + '. Method: ' + http_method
        return fos_auth.create_error(brcdapi_util.HTTP_REQUEST_TIMEOUT, buf)
    except BaseException as e:
        e_buf = str(type(e)) + ': ' + str(e)
        http_buf = 'http_response: '
        http_buf += 'None' if http_response is None else \
            http_response.decode(encoding=brcdapi_util.encoding_type, errors='ignore')
        json_buf = 'json_data: '
        json_buf += 'None' if json_data is None else \
            json_data.decode(encoding=brcdapi_util.encoding_type, errors='ignore')
        ml = ['Unexpected error:',
              'Exception: ' + e_buf,
              'Unexpected error, ' + e_buf,
              http_buf,
              json_buf]
        brcdapi_log.exception(ml, echo=True)
        return fos_auth.create_error(brcdapi_util.HTTP_REQUEST_TIMEOUT,
                                     'Unexpected error:',
                                     msg=e_buf.split('\n'))
    
    _req_pending = False
    if _control_c_pend:
        _control_c_pend = False
        raise KeyboardInterrupt

    # Do some basic parsing of the response
    tl = uri.split('?')[0].split('/')
    cmd = tl[len(tl) - 1]
    if fos_auth.is_error(json_data):
        msg = ''
        try:
            if isinstance(json_data['errors']['error'], list):
                msg = '\n'.join([d['error-message'] for d in json_data['errors']['error']])
            else:
                msg = json_data['errors']['error']['error-message']
        except BaseException as e0:
            e0_buf = str(type(e0)) + ': ' + str(e0)
            if '_raw_data' not in json_data:  # Make sure it's not an error without any detail
                try:
                    # The purpose of capturing the message is to support the code below that works around a defect in
                    # FOS whereby empty lists or no change PATCH requests are returned as errors. In the case of
                    # multiple errors, I'm assuming the first error is the same for all errors. For any code I wrote,
                    # that will be true. Since I know this will be fixed in a future version of FOS, I took the easy way
                    msg = json_data['errors']['error'][0]['error-message']
                except BaseException as e1:
                    e1_buf = str(type(e1)) + ': ' + str(e1)
                    brcdapi_log.exception(['Invalid data returned from FOS:', e0_buf, e1_buf], echo=True)
                    msg = ''
        try:
            if http_method == 'GET' and json_data['_raw_data']['status'] == brcdapi_util.HTTP_NOT_FOUND and \
                    json_data['_raw_data']['reason'] == 'Not Found':
                ret_obj = dict(cmd=list())  # It's really just an empty list
            elif http_method == 'GET' and json_data['_raw_data']['status'] == brcdapi_util.HTTP_BAD_REQUEST and \
                    msg == 'No entries in the FDMI database':
                ret_obj = dict(cmd=list())  # It's really just an empty list
            elif http_method == 'GET' and json_data['_raw_data']['status'] == brcdapi_util.HTTP_BAD_REQUEST and \
                    json_data['_raw_data']['reason'] == 'Bad Request' and 'Not supported on this platform' in msg:
                ret_obj = dict(cmd=list())  # It's really just an empty list
            elif http_method == 'PATCH' and json_data['_raw_data']['status'] == brcdapi_util.HTTP_BAD_REQUEST and \
                    json_data['_raw_data']['reason'] == 'Bad Request' and \
                    ('No Change in Configuration' in msg or 'Same configuration' in msg):
                # Sometimes FOS 8.2.1 returns no change as this error and sometimes it doesn't. Expected fix for no
                # change with PATCH is to always return good status (204). Note that according to RFC 5789, no change is
                # not considered an error.
                ret_obj = dict(cmd=list())
            else:
                ret_obj = json_data
        except (TypeError, KeyError):
            try:
                status = json_data['_raw_data']['status']
            except (TypeError, KeyError):
                status = 0
                msg = 'No status provided.'
            try:
                reason = json_data['_raw_data']['reason']
            except (TypeError, KeyError):
                reason = 'No reason provided'
            ret_obj = fos_auth.create_error(status, reason, msg=msg)
    elif 'Response' in json_data:
        obj = json_data.get('Response')
        ret_obj = obj if bool(obj) else {cmd: list()}
    else:
        raw_data = json_data.get('_raw_data')
        if raw_data is not None:
            status = brcdapi_util.HTTP_BAD_REQUEST if raw_data.get('status') is None else raw_data.get('status')
            reason = '' if raw_data.get('reason') is None else raw_data.get('reason')
        else:
            status = brcdapi_util.HTTP_BAD_REQUEST
            reason = 'Invalid response from the API'
        if status < 200 or status >= 300:
            ret_obj = fos_auth.create_error(status, reason)
        else:
            ret_obj = dict()

    return ret_obj


def _retry(obj):
    """Determines if a request should be retried.

    :param obj: Object returned from _api_request()
    :type obj: dict
    :return retry_flag: True - request should be retried. False - request should not be retried.
    :rtype retry_flag: bool
    :return delay: Time, in seconds, to wait for retrying the request
    :rtype delay: int
    """
    global _SVC_UNAVAIL_WAIT, _FABRIC_BUSY_WAIT

    status, reason = fos_auth.obj_status(obj), fos_auth.obj_reason(obj)
    if isinstance(status, int) and status == 503 and isinstance(reason, str) and 'Service Unavailable' in reason:
        brcdapi_log.log('FOS API services unavailable. Will retry in ' + str(_SVC_UNAVAIL_WAIT) + ' seconds.', True)
        return True, _SVC_UNAVAIL_WAIT
    if status == brcdapi_util.HTTP_BAD_REQUEST and 'The Fabric is busy' in fos_auth.formatted_error_msg(obj):
        brcdapi_log.log('Fabric is busy. Will retry in ' + str(_FABRIC_BUSY_WAIT) + ' seconds.', echo=True)
        return True, _FABRIC_BUSY_WAIT

    return False, 0


def api_request(session, uri, http_method, content):
    """Interface in front of _api_request to handle retries when services are unavailable

    :param session: Session object returned from login()
    :type session: dict
    :param uri: full URI
    :type uri: str
    :param http_method: Method for HTTP connect.
    :param content: The content, in Python dict, to be converted to JSON and sent to switch.
    :type content: dict, None
    :return: Response and status in fos_auth.is_error() and fos_auth.formatted_error_msg() friendly format
    :rtype: dict
    """
    global _MAX_RETRIES

    if uri is None:  # An error occurred in brcdapi_util.format_uri()
        buf = 'Missing URI'
        brcdapi_log.exception(buf, echo=True)
        return fos_auth.create_error(brcdapi_util.HTTP_BAD_REQUEST, 'Missing URI', msg=buf)
    obj = _api_request(session, uri, http_method, content)
    retry_count = _MAX_RETRIES
    retry_flag, wait_time = _retry(obj)
    while retry_flag and retry_count > 0:
        time.sleep(wait_time)
        obj = _api_request(session, uri, http_method, content)
        retry_count -= 1
        retry_flag, wait_time = _retry(obj)
    return obj


def get_request(session, ruri, fid=None):
    """Fill out full URI and add debug wrapper around a GET before calling api_request().

    :param session: Session object returned from login()
    :type session: dict
    :param ruri: URI. The prefix, such as '/rest/running/', is added so do not include.
    :type ruri: str
    :param fid: Fabric ID
    :type fid: int, None
    :return: Response and status in fos_auth.is_error() and fos_auth.formatted_error_msg() friendly format
    :rtype: dict
    """
    global _DEBUG, _verbose_debug

    # Only used if _DEBUG is True
    if _DEBUG:
        buf = '' if fid is None else brcdapi_util.vfid_to_str(fid)
        file = _DEBUG_PREFIX + _clean_debug_file.sub('_', session.get('_debug_name') + '_' +
                                                     ruri.replace('running/', '') + buf + '.txt')

    if _DEBUG and _DEBUG_MODE == 1:
        try:
            f = open(file, "r")
            json_data = json.load(f)
            f.close()
            if _verbose_debug:
                ml = ['api_request() - Send:',
                      'Method: GET', 'URI: ' + brcdapi_util.format_uri(session, ruri, fid),
                      'api_request() - Response:',
                      pprint.pformat(json_data)]
                brcdapi_log.log(ml, echo=True)
        except (FileNotFoundError, FileExistsError):
            return fos_auth.create_error(brcdapi_util.HTTP_NOT_FOUND, 'File not found: ', msg=[file])
        except BaseException as e:
            brcdapi_log.log('Unknown error, ' + str(type(e)) + ': ' + str(e) + ' encountered opening ' + file,
                            echo=True)
            raise RuntimeError
    else:
        json_data = api_request(session, brcdapi_util.format_uri(session, ruri, fid), 'GET', dict())
    if _DEBUG and _DEBUG_MODE == 0:
        try:
            with open(file, 'w') as f:
                f.write(json.dumps(json_data))
            f.close()
        except FileNotFoundError:
            brcdapi_log.log('\nThe folder for ' + file + ' does not exist.', echo=True)

    return json_data


def send_request(session, ruri, http_method, content, fid=None):
    """Performs a Rest API request. Use get_request() for GET. Use this for all other '/rest/running/' requests

    :param session: Session object returned from login()
    :type session: dict
    :param ruri: URI less 'ip-addr/rest/'
    :type ruri: str
    :param http_method: Method (PATCH, POST, DELETE, PUT ...) for HTTP connect.
    :param content: The content, in Python dict, to be converted to JSON and sent to switch.
    :type content: dict, None
    :param fid: Fabric ID
    :type fid: int, None
    :return: Response and status in is_error() and fos_auth.formatted_error_msg() friendly format
    :rtype: dict
    """
    return api_request(session, brcdapi_util.format_uri(session, ruri, fid), http_method, content)


def set_debug(debug, debug_mode=None, debug_folder=None):
    """Programmatically set _DEBUG, _DEBUG_MODE, _DEBUG_PREFIX

    :param debug: Set _DEBUG. If True, use debug_mode. If False, debug_mode and debug_folder are ignored.
    :type debug: bool
    :param debug_mode: If debug is True. 0: Process requests normally and write to debug_folder. 1: Do not perform any \
        requests. Read all requests from data stored when debug_mode was 0 and debug True.
    :type debug_mode: int, None
    :param debug_folder: Folder name where all the json dumps of API requests are read/written. If the folder does not \
        exist it is created with 777 access (that means all access rights).
    :type debug_folder: str, None
    :return: Status. If true, debug mode was successfully set.
    :rtype: bool
    """
    global _DEBUG, _DEBUG_MODE, _DEBUG_PREFIX

    _DEBUG = debug
    if debug:
        if isinstance(debug_mode, int) and 0 <= debug_mode <= 1:
            _DEBUG_MODE = debug_mode
            x = len(debug_folder) if isinstance(debug_folder, str) else 0
            if x > 0:
                _DEBUG_PREFIX = debug_folder[0:x-1] if debug_folder[x-1] == '/' or debug_folder[x-1] == '\\' \
                    else debug_folder
                try:
                    os.mkdir(_DEBUG_PREFIX)
                except FileExistsError:
                    pass
                _DEBUG_PREFIX += '/'
            else:
                buf = 'Invalid debug_folder type. debug_folder type must be str. Type is: ' + str(type(debug_folder))
                brcdapi_log.exception(buf, echo=True)
                return False
        else:
            buf = 'Invalid debug_mode. debug_mode must be an integer of value 0 or 1. debug_mode type: ' + \
                  str(type(debug_mode)) + ', value: ' + str(debug_mode)
            brcdapi_log.exception(buf, echo=True)
            return False

    return True


def check_status(session, fid, message_id, wait_time, num_check):
    """Polls a switch for status of an operations URI

    :param session: Session object returned from login()
    :type session: dict
    :param fid: Fabric ID
    :type fid: int, None
    :param message_id: Message ID returned in the response to the operation that is being checked
    :type message_id: str, int
    :param wait_time: The length of time in seconds to wait before polling the switch for status
    :type wait_time: int
    :param num_check: Maximum number of times to poll the switch
    :type num_check: int
    """
    obj = fos_auth.create_error(brcdapi_util.HTTP_REQUEST_CONFLICT,
                                'Invalid parameter',
                                msg='num_check must be greater than 0')
    i = num_check

    while i > 0:
        time.sleep(wait_time)
        obj = send_request(session,
                           'operations/show-status/message-id/' + str(message_id),
                           'POST',
                           None,
                           fid)
        if fos_auth.is_error(obj):
            return obj  # Let the calling method deal with errors
        try:
            if obj['show-status']['status'] == 'done':
                break
        except KeyError:
            return fos_auth.create_error(brcdapi_util.HTTP_INT_SERVER_ERROR,
                                         brcdapi_util.HTTP_REASON_UNEXPECTED_RESP,
                                         msg="Missing: ['show-status']['status']")
        i -= 1

    try:
        if obj['show-status']['status'] != 'done':
            obj = fos_auth.create_error(brcdapi_util.HTTP_REQUEST_TIMEOUT,
                                        'Timeout',
                                        msg=_format_op_status(obj))
    except KeyError:
        pass

    return obj


def control_c():
    """Raises KeyboardInterrupt as soon as the request in progress completes"""
    global _req_pending, _control_c_pend

    brcdapi_log.log('Control-C detected.', echo=True)
    if _req_pending:
        brcdapi_log.log('Processing will stop as soon as the request in progress completes.', echo=True)
        _control_c_pend = True
    else:
        raise KeyboardInterrupt
    
    
def set_url_options(flag):
    """Enables of disables checking for URL OPTIONS
    
    :param flag: If True, OPTIONS for each URL are read before making any other requests
    :type flag: bool
    :rtype: None
    """
    global _OPTIONS_CHECK
    
    _OPTIONS_CHECK = False if flag else True


def operations_request(session, ruri, http_method, content_d, fid=None, wait_time=5, max_try=5):
    """Performs an operations branch Rest API request and polls for status completion

    :param session: Session object returned from login()
    :type session: dict
    :param ruri: URI less 'ip-addr/rest/'
    :type ruri: str
    :param http_method: Method (PATCH, POST, DELETE, PUT ...) for HTTP connect.
    :param content_d: The content, in Python dict, to be converted to JSON and sent to switch.
    :type content_d: dict, None
    :param fid: Fabric ID
    :type fid: int, None
    :param wait_time: Time, in seconds, to wait before polling for status
    :type wait_time: int
    :param max_try: Maximum of times to poll for status before returning an error
    :type max_try: int
    :return: Response and status in is_error() and fos_auth.formatted_error_msg() friendly format
    :rtype: dict
    """
    obj = send_request(session, ruri, http_method, content_d)
    try:
        message_id = obj['show-status']['message-id']
        if obj['show-status']['status'] != 'done':
            obj = check_status(session, fid, message_id, max_try, wait_time)
    except KeyError:  # Sometimes operations branches complete immediately or there may have been an error
        pass

    return obj


def verbose_debug(state):
    """Sets or clears verbose debugging

    :param state: True - Enable verbose debug, False - disable verbose debug
    :type state: bool
    """
    global _verbose_debug

    _verbose_debug = state
    fos_cli.verbose_debug(state)
