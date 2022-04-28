#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2021, 2022 Jack Consoli.  All rights reserved.
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
:mod:`cli_poll_to_api` - RESTConf API GET examples. Includes a GET for most requests supported in FOS v8.2.1c

**Description**

    This module is specifically targeted for customers monitoring their SAN fabrics by CLI polling who want to convert
    to API polling. Although much of this module is redundant to what is in api_get_examples.py, this module is focused
    on common CLI commands used for polling with additional commenting pertaining to the differences between CLI
    commands and API requests. It is intended as a set of examples to help programmers get started.

    To capture data from logical switches, it's necessary to know what the logical switches are so FID data is parsed
    out of the request response but for all other requests, the response is printed to the log but no other action is.
    taken.

    For those new to RESTConf APIs, an API works through an HTTP(S) interface. For purposes of monitoring and polling,
    only GET requests are performed. A GET request is equivalent to show commands in that they only return information.
    They do not make any changes in the environment.

    The intent is that programmers will copy this module, search for whatever CLI command they are looking for and
    comment out whatever they don't want to look at in _chassis_rest_data and _switch_rest_data. In additional to
    illustrating how to login and handle login errors, being able to login allows you to set breakpoints to examine data
    structures.

**Requirements**

    * Python 3.3 or higher
    * FOS 8.2.1c or higher (some features require a more recent version of FOS
    * brcdapi library

**Perl To Python**

    Most CLI parsing scripts were written in Perl. Python has become the language of choice for automation. The reasons
    for that are beyond the scope of this module. What is pertinent is that there is no simple way to convert Perl to
    Python. You should plan on a code re-write. Even if there was a simple way to convert Perl to Python:

    * Much of CLI scripting is dedicated to parsing output which is no longer necessary with an API.
    * Data is organized differently in the API
    * There are some features of Python that don't exist in Perl that may be useful.

    I inserted a few comments where there is a Python construct that is new for a scripting language but these comments
    are very limited. You will need to learn Python syntax.

**Tips**

    *Before you start*

    * Use lib_check.py to validate the required libraries are accessible
    * Use login_test.py to validate that a Rest API session can be established
    * Read FOS_API_Tips, especially “Environment: Important Python Environment Notes: shebang Line & Encoding”,
      “API Throttling”, and “API Protocol: HTTP Connection Timeout”.
    * Get an Integrated Development Environment. They are relatively inexpensive and save considerable time. I use
      PyCharm from JetBrains, https://www.jetbrains.com/pycharm

    *lib_check.py*

    This module displays the Python version, library paths, and validates that the required libraries are accessible.

    This module is in the brocade-rest-api-applications folder.

    Note: lib_check.py may fail because fos_cli.py imports paramiko which is not included in most standard Python lib
    packages. fos_cli.py is only required for certain configuration scripts which are not used for any of the GET
    operations associated with fabric monitoring so error messages from lib_check.py for fos_cli.py can be ignored.

    If you are not using brcddb, you can ignore any import failures for that library. Likewise, if you are not using any
    of the applications in brocade-rest-api-applications, you can ignore any import failures used by the applications.

    *lib_validate.py*

    Can be used on any Python module. Performs an in-depth recursive search for all the imported libraries required by a
    specified module. Typically only used when lib_check.py fails.

    This module is in the brocade-rest-api-applications folder.

    *FOS_API_Tips*

    The supplemental documentation, FOS_API_Tips.pdf, is available in the Documentation folder. The README in that
    folder is just an introduction to FOS_API_Tips.

    Some of this documentation is now available in published Brocade documentation. It contains several tips based on my
    own personal experience.

    *Logging*

    Rather than use Python “print” statements, programmers are encouraged to use brcdapi.log. In addition to echoing all
    responses to STD_IO, it creates a time stamped log. When enabled, all API activity is logged. For programmers, it
    includes an exception method which adds a stack trace dump to the log. Search this module for _DEBUG_EXCEPTION.

**Debugging & Code Development**

    *brcdapi_rest*

    The brcdapi_rest module in the brcdapi folder is the single interface to the switch API. It contains two features
    intended to support code development:

    GET request learning: There isn’t a software emulator for a FOS switch which means an actual switch is required to
    perform any GET requests. This feature memorizes responses to requests. Its typical use is to make all requests
    without any processing and then use the memorized responses while developing code. In addition to speeding up
    responses, this eliminates the need for a physical switch during code development. For further information, read
    section “Drivers & Samples: brcdapi: Local Debug” in FOS_API_Tips. Search this module for _DEBUG_MODE.

    Verbose logging: Verbose logging logs all requests and responses via the API as pprint would display the objects.
    For further information, read section “Drivers & Samples: brcdapi: Verbose Logging” in FOS_API_Tips. Search this
    module for _DEBUG_VERBOSE.

    *_DEBUG*

    All modules in brocade-rest-api-examples and brocade-rest-api-applications have a debug mode. Search any module for
    _DEBUG. When enabled, any parameter normally passed when invoking the module through a shell (equivalent of a DOS
    prompt in Windows speak). Setting this mode allows you to run the script in an IDE.

**CLI to API**

    There isn’t a one-to-one correlation between CLI commands and API requests, although in most cases, only a single
    API request is needed for the equivalent information. Rather than provide exhaustive documentation, a separate
    method for each CLI command was created with comments. Simply search this document for the show command you are
    looking for.

    Lists in _chassis_rest_data and _switch_rest_data include everything, although some stuff I commented out. The
    intent was to let you pick and choose which one's you want to keep. Equivalent FOS commands are in the comments
    next to each so you can just search this module for the FOS command you are looking for. Since there isn't a 1:1
    mapping of CLI commands to API requests, what you're looking for may appear in multiple places.

    At this time, FEC corrected and uncorrected blocks, fec_uncor_detected and fec_cor_detected, were not exposed in the
    API. Note that FEC corrected bits, fec_cor_detected, are handled entirely in the hardware in Gen 7 so there is no
    equivalent in FOS running on Gen 7 hardware.

**Porting BNA to SANnav or FOS API**

    Many of the features that were supported by Network Advisor shifted to the FOS API. Furthermore, there are
    significant differences between the SANnav API and the Network Advisor API. SANnav does has Kafka streams for
    port statistics. If all you are polling for is port statistics, in most cases setting up a Kafka receiver is the
    better way to monitor port statistics. You probably will still need to do an initial poll or slower poll of the
    switch directly via the FOS API interface to pick up port configuration details and other information typically
    included with port statistical gathering.

**A Few Notes Regarding Folders at https://github.com/jconsoli**

    *brcdapi*

    brcdapi is a simple driver. As is typical of a driver, it builds complete URIs, adds headers to requests, handles
    low level errors, and has the aforementioned debug features. This library is used for all examples in this module.

    *brcddb*

    The brcddb objects and libraries store data and make relationships. For example, to perform maintenance on a storage
    port, you need to know all of the servers zoned to that port so you can notify the server team what applications
    will be affected. To do this, information about the port, logins, and zoning must be retrieved from multiple API
    requests. There is a utility in brcddb that accepts a list of requests, executes them, and stores the data in
    objects. The objects have methods associated with them to easily retrieve all the logins zoned to that port which
    would be used to determine what server admins need to be notified.

    If you are converting a script written to use CLI commands, you probably have your own database already and don’t
    need this; however, there may be some reasons for downloading it. The most common reason is to use report.py in
    brocade-rest-api-applications.

    *brocade-rest-api-examples*

    This is the folder where this module came from.

    Although some of the modules in brocade-rest-api-examples are useful as stand-alone modules to perform certain
    functions, the primary purpose of those methods are to provide programmers with examples on how to use the API. As
    such, a more verbose coding style was used as well as more commenting than traditional production code would have.
    Furthermore, there are some debugging features and validation modules.

    *brocade-rest-api-applications*

    While the modules in brocade-rest-api-examples are examples of how to execute individual API requests using the
    driver modules in brcdapi, the modules in brocade-rest-api-applications are examples on how to perform SAN tasks
    such as generate reports, create logical switches, merge zones, and more. To accomplish complete tasks, the data
    from multiple API requests must be collected and correlated. The modules in here are examples on how to use the
    brcddb library to perform these tasks.

**Feedback**

    Feed back is always appreciated. Search for __email__ in the module header.

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 1.0.0     | 14 Nov 2021   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 1.0.1     | 31 Dec 2021   | Use explicit exception clauses                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 1.0.2     | 28 Apr 2022   | Added "running" to URI                                                            |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2021, 2022 Jack Consoli'
__date__ = '28 Apr 2022'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '1.0.2'

import pprint
import brcdapi.brcdapi_rest as brcdapi_rest
import brcdapi.fos_auth as brcdapi_auth
import brcdapi.log as brcdapi_log
import brcdapi.util as brcdapi_util

_DOC_STRING = False  # Should always be False. Prohibits any actual I/O. Only useful for building documentation
_DEBUG_IP = '10.xxx.x.xxx'
_DEBUG_ID = 'admin'
_DEBUG_PW = 'password'
_DEBUG_SEC = None  # None or 'none' for HTTP, 'self' for self signed certificates. Otherwise, the certificate
"""What the rest of these global variables do:
+-------------------+-------------------------------------------------------------------------------------------+
| Variable          | Description                                                                               |
+===================+===========================================================================================+
| _DEBUG_VERBOSE    | When True, all content and responses are formatted and printed (pprint) to the log and    |
|                   | console. In this module there is a pprint with all the responses and the requests are     |
|                   | simple so setting this True might be a useful one time exercise to see what it does but   |
|                   | in this module its essentially redundant so you should leave it False.                    |
+-------------------+-------------------------------------------------------------------------------------------+
| _DEBUG_LOG        | Directory where log file is to be created. The default is to use the current directory.   |
|                   | The log file name will always be "Log_xxxx" where xxxx is a time and date stamp. I        |
|                   | usually create a folder _logs so that my work folder doesn't get cluttered with logs.     |
|                   |                                                                                           |
|                   | The folder is not automatically created. You must create the log folder if you intend to  |
|                   | use it.                                                                                   |
+-------------------+-------------------------------------------------------------------------------------------+
| _DEBUG_NL         | When True, a log file is not created. Since this module is to provide sample output, you  |
|                   | should leave it False. Not creating a log file is useful with some automation programs.   |
+-------------------+-------------------------------------------------------------------------------------------+
| _DEBUG_SUP        | When True, suppresses echo to the console when writing to the log. Note that with all     |
|                   | calls to brcdapi.log.log() in this module have the text to print to the log as well as    |
|                   | True. The True instructs the logging method to echo whatever is being printed to the log  |
|                   | to STD_OUT. This provides a simple means to suppress all console printing regardless of   |
|                   | how brcdapi.log.log() was called. This feature is part of the log module to support       |
|                   | certain automation programs with restricted console printing. It provides the ability to  |
|                   | programmatically turn off console printing with a single call to the log module without   |
|                   | having to modify any of the script.                                                       |
|                   |                                                                                           |
|                   | For purposes of this script, this should always be False.
+-------------------+-------------------------------------------------------------------------------------------+
| _DEBUG_EXCEPTION  | When True, prints a test message with a stack trace to the log.                           |
+-------------------+-------------------------------------------------------------------------------------------+
| _DEBUG_API        | Set False for normal operation. When True, read and write requests based on _DEBUG_MODE.  |
|                   | Read section “Drivers & Samples: brcdapi: Verbose Logging” in FOS_API_Tips for additional |
|                   | detail.                                                                                   |
+-------------------+-------------------------------------------------------------------------------------------+
| _DEBUG_MODE       | When None, debug mode in brcdapi_rest is disabled. When an int:                           |
|                   | 0 - Perform all requests normally. Write all responses to a file in the folder specified  |
|                   |     by _DEBUG_FOLDER                                                                      |
|                   | 1 - Do not perform any I/O. Read all responses from file into response and fake a         |
|                   |     successful login and logout.                                                          |
+-------------------+-------------------------------------------------------------------------------------------+
| _DEBUG_FOLDER     | The name of the folder where requests are written to or read from. If the folder does not |
|                   | it is created.                                                                            |
+-------------------+-------------------------------------------------------------------------------------------+
"""
_DEBUG_VERBOSE = False
_DEBUG_LOG = None
_DEBUG_NL = False
_DEBUG_SUP = False
_DEBUG_EXCEPTION = False
_DEBUG_API = False
_DEBUG_MODE = 0
_DEBUG_FOLDER = 'raw_data'  # Can be any valid folder name. The folder is not created. It must already
# exist. This is where all the json dumps of API requests are read/written.

_chassis_rest_data = [
    'running/brocade-fibrechannel-logical-switch/fibrechannel-logical-switch',  # switchshow
    'running/brocade-chassis/chassis',  # chassisshow
    'running/brocade-chassis/ha-status',  # hashow
    'running/brocade-fru/blade',  # Blade status as reported with chassisshow
    'running/brocade-fru/fan',  # Blower (fan) status as reported with chassisshow
    'running/brocade-fru/power-supply',  # Power supply status as reported with chassisshow
    'running/brocade-license/license',  # Equivalent to licenseshow. Note: licenseshow has been deprecated in FOS 9.x
    # 'running/brocade-security/ipfilter-policy',
    # 'running/brocade-security/ipfilter-rule',
    # 'running/brocade-security/user-specific-password-cfg',
    # 'running/brocade-security/password-cfg',
    # 'running/brocade-security/user-config',
    # 'running/brocade-security/radius-server',
    # 'running/brocade-security/tacacs-server',
    # 'running/brocade-security/ldap-server',
    # 'running/brocade-security/ldap-role-map',
    # 'running/brocade-security/sec-crypto-cfg-template',
    # 'running/brocade-security/sec-crypto-cfg',
    # 'running/brocade-security/sshutil',
    # 'running/brocade-security/sshutil-key',
    # 'running/brocade-security/sshutil-public-key',
    # 'running/brocade-security/security-certificate',
    'running/brocade-snmp/system',
    'running/brocade-snmp/mib-capability',
    'running/brocade-snmp/trap-capability',
    'running/brocade-snmp/v1-account',
    'running/brocade-snmp/v1-trap',
    'running/brocade-snmp/v3-account',
    'running/brocade-snmp/v3-trap',
    'running/brocade-snmp/access-control',
    'running/brocade-time/time-zone',
    'running/brocade-time/clock-server',
    # 'running/brocade-module-version',  # Gets executed immediately after login and is attached to the session object
]

_switch_rest_data = [
    'running/brocade-fabric/fabric-switch',  # chassisshow, firmwareshow, switchshow, version
    'running/brocade-fibrechannel-switch/fibrechannel-switch',  # switchshow, configshow, chassisshow
    'running/brocade-interface/fibrechannel-statistics',  # portstatshow, portstats64hsow
    'running/brocade-interface/fibrechannel',  # switchshow, portshow, portcfgshow
    'running/brocade-interface/extension-ip-interface',
    'running/brocade-interface/gigabitethernet',
    'running/brocade-interface/gigabitethernet-statistics',
    'running/brocade-zone/defined-configuration',  # cfgshow, alishow, defzone, zoneshow
    'running/brocade-zone/effective-configuration',  # cfgshow, alishow, defzone, zoneshow
    'running/brocade-fdmi/hba',  # fdmishow
    'running/brocade-fdmi/port',  # fdmishow
    'running/brocade-name-server/fibrechannel-name-server',  # nsshow
    'running/brocade-fibrechannel-configuration/fabric',  # fabricshow
    'running/brocade-fibrechannel-configuration/port-configuration',  # portshow, portcfgshow
    'running/brocade-fibrechannel-configuration/zone-configuration',
    'running/brocade-fibrechannel-configuration/switch-configuration',  # switchshow
    'running/brocade-fibrechannel-configuration/f-port-login-settings',  # portcfgshow
    'running/brocade-fibrechannel-trunk/trunk',  # trunkshow
    'running/brocade-fibrechannel-trunk/performance',  # trunkshow
    'running/brocade-fibrechannel-trunk/trunk-area',  # trunkshow
    'running/brocade-logging/audit',  # auditdump
    # 'running/brocade-logging/syslog-server',
    # 'running/brocade-logging/log-quiet-control',
    # 'running/brocade-logging/log-setting',
    'running/brocade-logging/raslog',  # errdump
    'running/brocade-logging/raslog-module',
    # 'running/brocade-logging/rule',    # Requires additional parameters. Not testing this at this time
    'running/brocade-maps/maps-config',  # mapspolicy, mapsconfig, mapsrule
    'running/brocade-maps/dashboard-misc',  # mapspolicy, mapsconfig, mapsrule
    'running/brocade-maps/dashboard-rule',  # mapspolicy, mapsconfig, mapsrule
    'running/brocade-maps/group',  # mapspolicy, mapsconfig, mapsrule
    'running/brocade-maps/rule',  # mapspolicy, mapsconfig, mapsrule
    'running/brocade-maps/maps-policy',  # mapspolicy, mapsconfig, mapsrule
    'running/brocade-maps/monitoring-system-matrix',  # mapspolicy, mapsconfig, mapsrule
    'running/brocade-maps/switch-status-policy-report',  # mapspolicy, mapsconfig, mapsrule
    'running/brocade-maps/paused-cfg',  # mapspolicy, mapsconfig, mapsrule
    'running/brocade-maps/system-resources',  # mapspolicy, mapsconfig, mapsrule
    'running/brocade-media/media-rdp',  # sfpshow
    'running/brocade-access-gateway/device-list',  # agshow
    'running/brocade-access-gateway/f-port-list',  # agshow
    'running/brocade-access-gateway/n-port-map',  # agshow
    'running/brocade-access-gateway/n-port-settings',  # agshow
    'running/brocade-access-gateway/policy',  # agshow
    'running/brocade-access-gateway/port-group',  # agshow
    'running/brocade-extension-ip-route/extension-ip-route',
    'running/brocade-extension-ip-route/brocade-extension-ipsec-policy',
    'running/brocade-extension-tunnel/extension-circuit',
    'running/brocade-extension-tunnel/extension-circuit-statistics',
    'running/brocade-extension-tunnel/extension-tunnel',
    'running/brocade-extension-tunnel/extension-tunnel-statistics',
    'running/brocade-fibrechannel-diagnostics/fibrechannel-diagnostics',
    'running/brocade-security/auth-spec',
    'running/brocade-fibrechannel/topology-domain',  # topologyshow
    'running/brocade-ficon/logical-path',  # ficonshow
    'running/brocade-ficon/cup',  # ficoncupshow
    'running/brocade-ficon/logical-path',    # ficonshow
    'running/brocade-ficon/rnid',    # ficonshow
    'running/brocade-ficon/switch-rnid',  # ficonshow
    'running/brocade-ficon/lirr',    # ficonshow
    'running/brocade-ficon/rlir',    # ficonshow
]


def _setup_log(folder, no_log):
    """Demonstrate setup and provide examples on use of the logging methods
    
    :param folder: The folder to put log files in. If None, use the local directory
    :type folder: str, None
    :param no_log: If True, do not create a log file
    :type no_log: bool
    """
    global _DEBUG_IP, _DEBUG_ID, _DEBUG_VERBOSE, __version__, _DEBUG_EXCEPTION

    # Set up the folder to use for logging.
    if not no_log:
        brcdapi_log.open_log(folder)
        
    # As an example, echo the module variables
    ml = ['Module    : cli_poll_to_api', 
          'Version   : ' + __version__,
          'User ID   : ' + _DEBUG_ID,
          'Password  : xxxxxx',
          'IP address: ' + brcdapi_util.mask_ip_addr(_DEBUG_IP, keep_last=True)]
    # Every call to brcdapi_log.log is preceded with a time stamp so this list gets onetime stamp
    brcdapi_log.log(ml, echo=True)
    if _DEBUG_VERBOSE:
        brcdapi_log.log('Verbose debug enabled', True)  # This gets it's own time stampe
        
    # exception() precedes the message, or list of message, with a stack trace, calls log(), and flushes the file cache.
    if _DEBUG_EXCEPTION:
        buf = 'Ignore the preceding stack trace. It is only to illustrate the use of the brcdapi.log.expection() method'
        brcdapi_log.exception(buf, True)


def _get_chassis_data(session):
    """Capture chassis data as would be returned from (not all chassis data is being captured):

    :param session: The session object returned from brcdapi.fos_auth.login()
    :type session: dict
    :return: FID list
    :rtype: list
    """
    global _chassis_rest_data

    # Get all the chassis data
    # Note that in Gen 6 and above, the license ID, brocade-chassis/chassis/license-id, may not be the chassis WWN
    for kpi in _chassis_rest_data:  # See comments with _chassis_rest_data above
        ml = ['', kpi]  # The first member as '' inserts a blank line before the KPI
        obj = brcdapi_rest.get_request(session, kpi)
        if brcdapi_auth.is_error(obj):
            ml.append(brcdapi_auth.formatted_error_msg(obj))
        else:
            ml.append(pprint.pformat(obj))
        brcdapi_log.log(ml, True)

    """This is essentially a hybrid of lscfg --show and switchshow. This is where all the logical switches and ports
    associated with those logical switches are reported. I broke this out from _chassis_rest_data because we need to
    pick out the fabric IDs of all the logical switches."""

    kpi = 'running/brocade-fibrechannel-logical-switch/fibrechannel-logical-switch'
    ml = ['', kpi]
    obj = brcdapi_rest.get_request(session, kpi)
    if brcdapi_auth.is_error(obj):
        ml.append(brcdapi_auth.formatted_error_msg(obj))
        brcdapi_log.log(ml, True)
        return list()  # A return in the middle of a method is common in Python after an error is encountered.

    ml.append(pprint.pformat(obj))

    """Normally, I would build a dictionary of the ports so I could treat them as objects and add port
    configuration, port statistics, and anything else port specific to the object.
    
    I don't recall how a non-VF enabled switch responds but I don't think 'fabric-id' is present in the response.

    If you are new to Python, there is a construct referred to as a list comprehension which allows you to build a
    list in a single line of code. The code that follows this comment is equivalent to:
    
    fid_list = list()
    for ls in obj['fibrechannel-logical-switch']:
        if ls.get('fabric-id') is not None:
            fid_list.append(ls.get('fabric-id'))
    return fid_list"""

    return [ls.get('fabric-id') for ls in obj['fibrechannel-logical-switch'] if ls.get('fabric-id') is not None]


def _get_switch_data(session, fid):
    """Capture switch, fabric, and port data as would be returned from (not all data is being captured):

    :param session: The session object returned from brcdapi.fos_auth.login()
    :type session: dict
    :param fid: Fabric ID to execute the switch level commands against. Use None for non-VF enabled switches
    :type fid: int, None
    """
    global _switch_rest_data

    for kpi in _switch_rest_data:  # See comments with _switch_rest_data above
        ml = ['', kpi]  # The first member as '' inserts a blank line before the KPI
        obj = brcdapi_rest.get_request(session, kpi, fid)
        if brcdapi_auth.is_error(obj):
            ml.append(brcdapi_auth.formatted_error_msg(obj))
        else:
            ml.append(pprint.pformat(obj))
        brcdapi_log.log(ml, True)


def pseudo_main():
    """Basically the main(). Did it this way to use with IDE

    :return: Exit code
    :rtype: int
    """
    global _DEBUG_IP, _DEBUG_ID, _DEBUG_PW, _DEBUG_SEC, _DEBUG_SUP, _DEBUG_LOG, _DEBUG_NL, _DEBUG_VERBOSE, __version__
    global _DEBUG_API, _DEBUG_MODE, _DEBUG_FOLDER

    ec = 0  # Return error code

    # Set up the log file
    _setup_log(_DEBUG_LOG, _DEBUG_NL)

    if _DEBUG_VERBOSE:
        brcdapi_rest.verbose_debug = True  # A proper Python method would set this via a method in brcdapi_rest

    if _DEBUG_API:
        brcdapi_rest.set_debug(_DEBUG_API, _DEBUG_MODE, _DEBUG_FOLDER)

    # Login
    sec = 'none' if _DEBUG_SEC is None else _DEBUG_SEC
    brcdapi_log.log('Attempting login')
    session = brcdapi_rest.login(_DEBUG_ID, _DEBUG_PW, _DEBUG_IP, sec)
    if brcdapi_auth.is_error(session):
        brcdapi_log.log(['Login failed:', brcdapi_auth.formatted_error_msg(session)], echo=True)
        return -1
    else:
        brcdapi_log.log('Login Succeeded', echo=True)

    """ I always put code after the login and before the logout in between try & except. It is especially useful during
    code development because if there is a bug in your code, you still logout. If you are new to Python, try says
    try to execute this code and if an error is encountered, execute what comes after "except:". Its common in
    Python scripting to just "let it rip" and handle errors in an exception but the intent in that case is that you
    know what the potential errors will be. Each exception has it's own type. For example, if you attempt to read a
    file that doesn't exist, the exception code is FileNotFoundError so the code would look something like:
    
    try:
        f = open(file, 'rb')
    except FileNotFoundError:
        brcdapi_log('File ' + file + ' not found', True
          
    So the idea is that you have some idea about what you are tyring to do. Its a bit of a fau pax in Python to have
    just "except:". This is referred to as a "bare except". Since this is for code development, I don't care what the
    exception is. I just want to fall through to ensure I logout. Otherwise, if my script crashed I have to use the CLI
    to determine what my login session ID is and then use another CLI command to terminate the session. So the bare
    except below is frowned upon by the purest but, IMO, it's a reasonable in this case."""

    try:
        # Before anything can be done with switches, you need to know what the switches are. Since the order of other
        # chassis data doesn't matter, we may as well capture all the chassis data at once.
        fid_list = _get_chassis_data(session)
        if len(fid_list) == 0:
            # If the switch is not VF enabled, fid_list is empty. I'm appending None here so that the loop below that
            # gets switch data is executed. Note that None type is used in the driver for non-VF enabled switches.
            fid_list.append(None)

        # Now get the switch data, fabric, and port data.
        for fid in fid_list:
            _get_switch_data(session, fid)

    except BaseException as e:
        brcdapi_log.log(['Encountered a programming error.', 'Exception is: ' + str(e)], True)
        ec = -1

    # Logout
    obj = brcdapi_rest.logout(session)
    if brcdapi_auth.is_error(obj):
        brcdapi_log.log(['Logout failed:', brcdapi_auth.formatted_error_msg(obj)], True)
        ec = -1

    return ec


###################################################################
#
#                    Main Entry Point
#
###################################################################
if _DOC_STRING:
    print('_DOC_STRING set. No processing')
    exit(0)

_ec = pseudo_main()
brcdapi_log.close_log('Processing Complete. Exit code: ' + str(_ec))
exit(_ec)
