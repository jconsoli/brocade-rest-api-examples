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

Used for:

* Defining common HTTP status & messages
* CLI to API conversion for MAPS rules
* Action tables, see discussion below

In FOS 8.2.1c, module-version was introduced but as of v9.2.0, still contained scant information about each module. The
table uri_map is a hard coded table to serve applications and other libraries that need to know how to build a full URI
and define the behavior of each exposed in the API. The hope is that some day, this information will be available
through the API allowing uri_map to be built dynamically.

**WARNING**

Only GET is valid in the 'methods' leaf of uti_map

**Public Methods & Data**

+-----------------------+---------------------------------------------------------------------------------------+
| Method                | Description                                                                           |
+=======================+=======================================================================================+
| HTTP_xxx              | Several comon status codes and reasons for synthesizing API responses. Typically this |
|                       | used for logic that determines an issue whereby the request can't be sent to the      |
|                       | switch API based on problems found with the input to the method.                      |
+-----------------------+---------------------------------------------------------------------------------------+
| add_uri_map           | Builds out the URI map and adds it to the session. Intended to be called once         |
|                       | immediately after login                                                               |
+-----------------------+---------------------------------------------------------------------------------------+
| format_uri            | Formats a full URI                                                                    |
+-----------------------+---------------------------------------------------------------------------------------+
| fos_to_dict           | Converts a FOS version into a dictionary to be used for comparing for version numbers |                                                                  |
+-----------------------+---------------------------------------------------------------------------------------+
| mask_ip_addr          | Replaces IP address with xxx.xxx.xxx.123 or all x depending on keep_last              |
+-----------------------+---------------------------------------------------------------------------------------+
| session_cntl          | Returns the control dictionary (uri map) for the uri                                  |
+-----------------------+---------------------------------------------------------------------------------------+
| split_uri             | Strips out leading '/rest/'. Optionally remove 'running' and 'operations'             |
+-----------------------+---------------------------------------------------------------------------------------+
| uri_d                 | Returns the dictionary in the URI map for a specified URI                             |
+-----------------------+---------------------------------------------------------------------------------------+
| validate_fid          | Validates a FID or list of FIDs                                                       |
+-----------------------+---------------------------------------------------------------------------------------+
| vfid_to_str           | Converts a FID to a string, '?vf-id=xx' to be appended to a URI that requires a FID   |
+-----------------------+---------------------------------------------------------------------------------------+

**Version Control**

+-----------+---------------+-----------------------------------------------------------------------------------+
| Version   | Last Edit     | Description                                                                       |
+===========+===============+===================================================================================+
| 4.0.0     | 04 Aug 2023   | Re-Launch                                                                         |
+-----------+---------------+-----------------------------------------------------------------------------------+
| 4.0.1     | 06 Mar 2024   | Added brocade-maps and brocade-fibrechannel-routing to common URIs. Added         |
|           |               | validate_fid()                                                                    |
+-----------+---------------+-----------------------------------------------------------------------------------+
| 4.0.2     | 26 Jun 2024   | Moved fos_to_dict() from brcddb.util.util to here.                                |
+-----------+---------------+-----------------------------------------------------------------------------------+
| 4.0.3     | 20 Oct 2024   | Added several URIs.                                                               |
+-----------+---------------+-----------------------------------------------------------------------------------+
| 4.0.4     | 06 Dec 2024   | Use stats_uri instead of explicit values for fibrechannel-statistics. Added       |
|           |               | bc_support_sn                                                                     |
+-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2023, 2024 Consoli Solutions, LLC'
__date__ = '06 Dec 2024'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack@consoli-solutions.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '4.0.4'

import pprint
import copy
import brcdapi.log as brcdapi_log
import brcdapi.gen_util as gen_util

# Common HTTP error codes and reason messages
HTTP_OK = 200
HTTP_NO_CONTENT = 204
HTTP_BAD_REQUEST = 400
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_REQUEST_TIMEOUT = 408
HTTP_REQUEST_CONFLICT = 409
HTTP_PRECONDITION_REQUIRED = 428
HTTP_INT_SERVER_ERROR = 500
HTTP_INT_SERVER_UNAVAIL = 503
HTTP_REASON_MISSING_OPERAND = 'Missing operand'
HTTP_REASON_MAL_FORMED_CMD = 'Malformed command'
HTTP_REASON_MAL_FORMED_OBJ = 'Malformed object'
HTTP_REASON_NOT_FOUND = 'Referenced resource not found'
HTTP_REASON_MISSING_PARAM = 'Missing parameter'
HTTP_REASON_UNEXPECTED_RESP = 'Unexpected response'
HTTP_REASON_PENDING_UPDATES = 'Unsaved changes'
HTTP_REASON_USER_ABORT = 'User terminated session, ctl-C'

GOOD_STATUS_OBJ = dict(_raw_data=dict(status=HTTP_OK, reason='OK'))
encoding_type = 'utf-8'  # Unless running these scripts on a mainframe, this will always be utf-8.

# Commonly used URIs: brocade-name-server
bns_uri = 'brocade-name-server/fibrechannel-name-server'
bns_fc4_features = bns_uri + '/fc4-features'
bns_node_symbol = bns_uri + '/node-symbolic-name'
bns_port_symbol = bns_uri + '/port-symbolic-name'
bns_share_area = bns_uri + '/share-area'
bns_redirection = bns_uri + '/frame-redirection'
bns_partial = bns_uri + '/partial'
bns_lsan = bns_uri + '/lsan'
bns_cascade_ag = bns_uri + '/cascaded-ag'
bns_connect_ag = bns_uri + '/connected-through-ag'
bns_dev_behind_ag = bns_uri + '/real-device-behind-ag'
bns_fcoe_dev = bns_uri + '/fcoe-device'
bns_sddq = bns_uri + '/slow-drain-device-quarantine'
bns_port_id = bns_uri + '/port-id'
bns_port_name = bns_uri + '/port-name'
bns_link_speed = bns_uri + '/link-speed'
bns_ns_dev_type = bns_uri + '/name-server-device-type'
bns_node_name = bns_uri + '/node-name'
bns_scr = bns_uri + '/state-change-registration'
bns_fab_port_name = bns_uri + '/fabric-port-name'
bns_perm_port_name = bns_uri + '/permanent-port-name'
bns_port_index = bns_uri + '/port-index'
# Commonly used URIs: brocade-fibrechannel-switch
bfs_uri = 'brocade-fibrechannel-switch/fibrechannel-switch'
bfs_name = bfs_uri + '/name'
bfs_did = bfs_uri + '/domain-id'
bfs_fcid_hex = bfs_uri + '/fcid-hex'
bfs_principal = bfs_uri + '/principal'
bfs_isprincipal = bfs_uri + '/is-principal'
bfs_op_status = bfs_uri + '/operational-status'
bfs_op_status_str = bfs_uri + '/operational-status-string'
bfs_fab_user_name = bfs_uri + '/fabric-user-friendly-name'
bfs_sw_user_name = bfs_uri + '/user-friendly-name'
bfs_banner = bfs_uri + '/banner'
bfs_fw_version = bfs_uri + '/firmware-version'
bfs_adv_tuning = bfs_uri + '/advanced-performance-tuning-policy'
bfs_dls = bfs_uri + '/dynamic-load-sharing'
bfs_domain_name = bfs_uri + '/domain-name'
bfs_model = bfs_uri + '/model'
bfs_vf_id = bfs_uri + '/vf-id'
bfs_ag_mode = bfs_uri + '/ag-mode'  # Depracated
bfs_ag_mode_str = bfs_uri + '/ag-mode-string'
bfs_enabled_state = bfs_uri + '/is-enabled-state'
bfc_up_time = bfs_uri + '/up-time'
# Commonly used URIs: brocade-fibrechannel-configuration
bfc_uri = 'brocade-fibrechannel-configuration/fabric'
bfc_idid = bfc_uri + '/insistent-domain-id-enabled'
bfc_principal_en = bfc_uri + '/principal-selection-enabled'
bfc_principal_pri = bfc_uri + '/principal-priority'
bfc_port_uri = 'brocade-fibrechannel-configuration/port-configuration'
bfc_portname_mode = bfc_port_uri + '/portname-mode'
bfc_portname_format = bfc_port_uri + '/dynamic-portname-format'
# Commonly used URIs: brocade-fibrechannel-configuration/f-port-login-settings
bfcfp_uri = 'brocade-fibrechannel-configuration/f-port-login-settings'
bfc_max_logins = bfcfp_uri + '/max-logins'
bfc_max_flogi_rate = bfcfp_uri + '/max-flogi-rate-per-switch'
bfc_stage_interval = bfcfp_uri + '/stage-interval'
bfc_free_fdisc = bfcfp_uri + '/free-fdisc'
bfc_max_flogi_rate_port = bfcfp_uri + '/max-flogi-rate-per-port'
bfc_fport_enforce_login = bfcfp_uri + '/enforce-login'  # Depracated
bfc_fport_enforce_login_str = bfcfp_uri + '/enforce-login-string'
# Commonly used URIs: brocade-fibrechannel-configuration/switch-configuration
bfc_sw_uri = 'brocade-fibrechannel-configuration/switch-configuration'
bfc_xisl_en = bfc_sw_uri + '/xisl-enabled'
bfc_area_mode = bfc_sw_uri + '/area-mode'
bfc_port_id_mode = bfc_sw_uri + '/wwn-port-id-mode'
bfs_edge_hold = bfc_sw_uri + '/edge-hold-time'
# Commonly used URIs: brocade-fru
fru_uri = 'brocade-fru'
fru_blade = fru_uri + '/blade'
fru_fan = fru_uri + '/fan'
fru_ps = fru_uri + '/power-supply'
fru_sensor = fru_uri + '/sensor'
fru_wwn = fru_uri + '/wwn'
fru_blade_pn = fru_uri + '/blade/part-number'
# Commonly used URIs: brocade-chassis/chassis
bcc_uri = 'brocade-chassis/chassis'
bc_mfg = bcc_uri + '/manufacturer'
bc_product_name = bcc_uri + '/product-name'  # product-name
bc_serial_num = bcc_uri + '/serial-number'
bc_support_sn = bcc_uri + '/entitlement-serial-number'  # S/N for entitlement
bc_vf = bcc_uri + '/vf-supported'
bc_time_alive = bcc_uri + '/time-alive'
bc_time_awake = bcc_uri + '/time-awake'
bc_fcr_en = bcc_uri + '/fcr-enabled'
bc_fcr_supported = bcc_uri + '/fcr-supported'
bc_user_name = bcc_uri + '/chassis-user-friendly-name'
bc_wwn = bcc_uri + '/chassis-wwn'
bc_license_id = bcc_uri + '/license-id'
bc_org_name = bcc_uri + '/registered-organization-name'
bc_org_reg_date = bcc_uri + '/organization-registration-date'
bc_pn = bcc_uri + '/part-number'
bc_vendor_pn = bcc_uri + '/vendor-part-number'
bc_max_blades = bcc_uri + '/max-blades-supported'
bc_vendor_sn = bcc_uri + '/vendor-serial-number'
bc_vendor_rev_num = bcc_uri + '/vendor-revision-number'
bc_date = bcc_uri + '/date'
bc_enabled = bcc_uri + '/chassis-enabled'
bc_motd = bcc_uri + '/message-of-the-day'
bc_shell_to = bcc_uri + '/shell-timeout'
bc_session_to = bcc_uri + '/session-timeout'
bc_usb_enbled = bcc_uri + '/usb-device-enabled'
bc_usb_avail_space = bcc_uri + '/usb-available-space'
bc_tcp_to_level = bcc_uri + '/tcp-timeout-level'
bc_bp_rev = bcc_uri + '/backplane-revision'
bp_vf_enabled = bcc_uri + '/vf-enabled'
# Commonly used URIs: brocade-chassis/ha-status
bcha_uri = 'brocade-chassis/ha-status'
bc_ha = bcha_uri + '/ha-enabled'
bc_heartbeat = bcha_uri + '/heartbeat-up'
bc_active_cp = bcha_uri + '/active-cp'
bc_active_slot = bcha_uri + '/active-slot'
bc_ha_recovery = bcha_uri + '/recovery-type'
bc_ha_standby_cp = bcha_uri + '/standby-cp'
bc_ha_standby_health = bcha_uri + '/standby-health'
bc_ha_standby_slot = bcha_uri + '/standby-slot'
bc_ha_enabled = bcha_uri + '/ha-enabled'
bc_ha_sync = bcha_uri + '/ha-synchronized'
bc_sync = bc_ha_sync  # This used to be 'brocade-chassis/chassis/ha-synchronized' which was deprecated early in 8.2.x
# Commonly used URIs: brocade-chassis/management-interface-configuration
bcmic_uri = 'brocade-chassis/management-interface-configuration'
bc_rest_enabled = bcmic_uri + '/rest-enabled'
bc_https_enabled = bcmic_uri + '/https-protocol-enabled'
bc_eff_protocol = bcmic_uri + '/effective-protocol'
bc_max_rest = bcmic_uri + '/max-rest-sessions'
bc_https_ka = bcmic_uri + '/https-keep-alive-enabled'
bc_https_ka_to = bcmic_uri + '/https-keep-alive-timeout'
# Commonly used URIs: brocade-fabric/fabric-switch
bfsw_uri = 'brocade-fabric/fabric-switch'  # I think this entire branch is depracated
bf_sw_user_name = bfsw_uri + '/switch-user-friendly-name'  # Depracated? Use bfs_sw_user_name
bf_sw_wwn = bfsw_uri + '/name'
bf_fw_version = bfsw_uri + '/firmware-version'  # Depracated?
bfsw_ipv4 = bfsw_uri + '/ip-address'
bfsw_mask =  bfsw_uri + '/subnet-mask'
bfsw_ipv6 = bfsw_uri + '/ipv6-address'
# Commonly used URIs: brocade-fibrechannel-logical-switch
bfls_uri = 'brocade-fibrechannel-logical-switch/fibrechannel-logical-switch'
bfls_sw_wwn = bfls_uri + '/switch-wwn'
bfls_fid = bfls_uri + '/fabric-id'
bfls_base_sw_en = bfls_uri + '/base-switch-enabled'
bfls_def_sw_status = bfls_uri + '/default-switch-status'
bfls_ficon_mode_en = bfls_uri + '/ficon-mode-enabled'
bfls_isl_enabled = bfls_uri + '/logical-isl-enabled'
bfls_mem_list = bfls_uri + '/port-member-list'
bfls_ge_mem_list = bfls_uri + '/ge-port-member-list'
# Commonly used URIs: brocade-maps
maps_uri = 'brocade-maps'
maps_db_hist = maps_uri + '/dashboard-history'
maps_db_misc = maps_uri + '/dashboard-misc'
maps_db_rule = maps_uri + '/dashboard-rule'
maps_group = maps_uri + '/group'
maps_config = maps_uri + '/maps-config'
maps_policy = maps_uri + '/maps-policy'
maps_rule = maps_uri + '/rule'
# Commonly used URIs: brocade-ficon
ficon_cup_uri = 'brocade-ficon/cup'
ficon_cup_en = ficon_cup_uri + '/fmsmode-enabled'
ficon_posc = ficon_cup_uri + '/programmed-offline-state-control'
ficon_uam = ficon_cup_uri + '/user-alert-mode'
ficon_asm = ficon_cup_uri + '/active-equal-saved-mode'
ficon_dcam = ficon_cup_uri + '/director-clock-alert-mode'
ficon_mihpto = ficon_cup_uri + '/mihpto'
ficon_uam_fru = ficon_cup_uri + '/unsolicited-alert-mode-fru-enabled'
ficon_uam_hsc = ficon_cup_uri + '/unsolicited-alert-mode-hsc-enabled'
ficon_uam_invalid_attach = ficon_cup_uri + '/unsolicited-alert-mode-invalid-attach-enabled'
ficon_sw_wwn = 'brocade-ficon/switch-rnid/switch-wwn'
ficon_sw_rnid_flags = 'brocade-ficon/switch-rnid/flags'
ficon_sw_node_params = 'brocade-ficon/switch-rnid/node-parameters'
ficon_sw_rnid_type = 'brocade-ficon/switch-rnid/type-number'
ficon_sw_rnid_model = 'brocade-ficon/switch-rnid/model-number'
ficon_sw_rnid_mfg = 'brocade-ficon/switch-rnid/manufacturer'
ficon_sw_rnid_pant = 'brocade-ficon/switch-rnid/plant'
ficon_sw_rnid_seq = 'brocade-ficon/switch-rnid/sequence-number'
ficon_sw_rnid_tag = 'brocade-ficon/switch-rnid/tag'

# Commonly used URIs: media-rdp
sfp_speed = 'media-rdp/media-speed-capability/speed'
sfp_wave = 'media-rdp/wavelength'
sfp_vendor = 'media-rdp/vendor-name'
sfp_sn = 'media-rdp/serial-number'
sfp_oui = 'media-rdp/vendor-oui'
sfp_pn = 'media-rdp/part-number'
sfp_volt = 'media-rdp/voltage'
sfp_current = 'media-rdp/current'
sfp_temp = 'media-rdp/temperature'
sfp_rx_pwr = 'media-rdp/rx-power'
sfp_tx_pwr = 'media-rdp/tx-power'
sfp_state = 'media-rdp/physical-state'
sfp_distance = 'media-rdp/media-distance/distance'
sfp_power_on = 'media-rdp/power-on-time'
sfp_remote_speed = 'media-rdp/remote-media-speed-capability/speed'
sfp_cur_high_alarm = 'media-rdp/remote-media-tx-bias-alert/high-alarm'
sfp_cur_high_warn = 'media-rdp/remote-media-tx-bias-alert/high-warning'
sfp_cur_low_alarm = 'media-rdp/remote-media-tx-bias-alert/low-alarm'
sfp_cur_low_warn = 'media-rdp/remote-media-tx-bias-alert/low-warning'
sfp_volt_high_alarm = 'media-rdp/remote-media-voltage-alert/high-alarm'
sfp_volt_high_warn = 'media-rdp/remote-media-voltage-alert/high-warning'
sfp_volt_low_alarm = 'media-rdp/remote-media-voltage-alert/low-alarm'
sfp_volt_low_warn = 'media-rdp/remote-media-voltage-alert/low-warning'
sfp_temp_high_alarm = 'media-rdp/remote-media-temperature-alert/high-alarm'
sfp_temp_high_warn = 'media-rdp/remote-media-temperature-alert/high-warning'
sfp_temp_low_alarm = 'media-rdp/remote-media-temperature-alert/low-alarm'
sfp_temp_low_warn = 'media-rdp/remote-media-temperature-alert/low-warning'
sfp_txp_high_alarm = 'media-rdp/remote-media-tx-power-alert/high-alarm'
sfp_txp_high_warn = 'media-rdp/remote-media-tx-power-alert/high-warning'
sfp_txp_low_alarm = 'media-rdp/remote-media-tx-power-alert/low-alarm'
sfp_txp_low_warn = 'media-rdp/remote-media-tx-power-alert/low-warning'
sfp_rxp_high_alarm = 'media-rdp/remote-media-rx-power-alert/high-alarm'
sfp_rxp_high_warn = 'media-rdp/remote-media-rx-power-alert/high-warning'
sfp_rxp_low_alarm = 'media-rdp/remote-media-rx-power-alert/low-alarm'
sfp_rxp_low_warn = 'media-rdp/remote-media-rx-power-alert/low-warning'
# Commonly used URIs: fibrechannel-statistics
stats_uri = 'fibrechannel-statistics'
stats_addr = stats_uri + '/address-errors'
stats_delimiter = stats_uri + '/delimiter-errors'
stats_out_frames = stats_uri + '/out-frames'
stats_in_frames = stats_uri + '/in-frames'
stats_enc_disp = stats_uri + '/encoding-disparity-errors'
stats_crc = stats_uri + '/crc-errors'
stats_in_crc = stats_uri + '/in-crc-errors'
stats_ios = stats_uri + '/invalid-ordered-sets'
stats_fec_un = stats_uri + '/fec-uncorrected'
stats_tunc = stats_uri + '/truncated-frames'
stats_long = stats_uri + '/frames-too-long'
stats_bad_eof = stats_uri + '/bad-eofs-received'
stats_enc = stats_uri + '/encoding-errors-outside-frame'
stats_c3 = stats_uri + '/class-3-discards'
stats_c3_out = stats_uri + '/class3-out-discards'
stats_c3_in = stats_uri + '/class3-in-discards'
stats_itw = stats_uri + '/invalid-transmission-words'
stats_link_fail = stats_uri + '/link-failures'
stats_in_reset = stats_uri + '/in-link-resets'
stats_loss_sync = stats_uri + '/loss-of-sync'
stats_loss_sig = stats_uri + '/loss-of-signal'
stats_off_seq = stats_uri + '/in-offline-sequences'
stats_out_off_seq = stats_uri + '/out-offline-sequences'
stats_out_reset = stats_uri + '/out-link-resets'
stats_p_rjt = stats_uri + '/p-rjt-frames'
stats_p_busy = stats_uri + '/p-busy-frames'
stats_bb_credit = stats_uri + '/bb-credit-zero'
stats_seq = stats_uri + '/primitive-sequence-protocol-error'
stats_rdy = stats_uri + '/too-many-rdys'
stats_multicast_to = stats_uri + '/multicast-timeouts'
stats_in_lcs = stats_uri + '/in-lcs'
stats_buf_full = stats_uri + '/input-buffer-full'
stats_f_busy = stats_uri + '/f-busy-frames'
stats_f_rjt = stats_uri + '/f-rjt-frames'
stats_lli = stats_uri + '/ink-level-interrupts'
stats_fpr = stats_uri + '/frames-processing-required'
stats_to = stats_uri + '/frames-timed-out'
stats_trans = stats_uri + '/frames-transmitter-unavailable-errors'
stats_nos_in = stats_uri + '/non-operational-sequences-in'
stats_nos_out = stats_uri + '/non-operational-sequences-out'
stats_time = stats_uri + '/time-generated'
# Commonly used URIs: brocade-interface/fibrechannel
bifc_uri = 'brocade-interface/fibrechannel'
bifc_pod = bifc_uri + '/pod-license-state'
# Commonly used URIs: fibrechannel
fc_auto_neg = 'fibrechannel/auto-negotiate'
fc_name = 'fibrechannel/name'  # The port number in s/p notation
fc_enabled = 'fibrechannel/is-enabled-state'
fc_op_status = 'fibrechannel/operational-status'  # Depracated
fc_op_status_str = 'fibrechannel/operational-status-string'
fc_state = 'fibrechannel/physical-state'
fc_port_type = 'fibrechannel/port-type'  # Depracated
fc_port_type_str = 'fibrechannel/port-type-string'
fc_fcid_hex = 'fibrechannel/fcid-hex'
fc_neighbor_node_wwn = 'fibrechannel/neighbor-node-wwn'
fc_neighbor = 'fibrechannel/neighbor'
fc_neighbor_wwn = 'fibrechannel/neighbor/wwn'
fc_index = 'fibrechannel/index'
fc_speed = 'fibrechannel/speed'
fc_max_speed = 'fibrechannel/max-speed'
fc_user_name = 'fibrechannel/user-friendly-name'
fc_los_tov = 'fibrechannel/los-tov-mode-enabled'
fc_eport_credit = 'fibrechannel/e-port-credit'
fc_fport_buffers = 'fibrechannel/f-port-buffers'
fc_fcid = 'fibrechannel/fcid'
fc_long_distance = 'fibrechannel/long-distance'
fc_npiv_pp_limit = 'fibrechannel/npiv-pp-limit'
fc_speed_combo = 'fibrechannel/octet-speed-combo'
fc_rate_limited_en = 'fibrechannel/rate-limit-enabled'
fc_wwn = 'fibrechannel/wwn'
fc_chip_buf_avail = 'fibrechannel/chip-buffers-available'
fc_chip_instance = 'fibrechannel/chip-instance'
fc_encrypt = 'fibrechannel/encryption-enabled'
fc_comp_act = 'fibrechannel/compression-active'
fc_comp_en = 'fibrechannel/compression-configured'
fc_credit_recov_act = 'fibrechannel/credit-recovery-active'
fc_credit_recov_en = 'fibrechannel/credit-recovery-enabled'
fc_d_port_en = 'fibrechannel/d-port-enable'
fc_e_port_dis = 'fibrechannel/e-port-disable'
fc_npiv_en = 'fibrechannel/npiv-enabled'
# Commonly used URIs: brocade-zone
bz_def_alias = 'brocade-zone/defined-configuration/alias'
bz_def_cfg = 'brocade-zone/defined-configuration/cfg'
bz_eff_cfg = 'brocade-zone/effective-configuration/cfg-name'
bz_eff_db_avail = 'brocade-zone/effective-configuration/db-avail'
bz_eff_checksum = 'brocade-zone/effective-configuration/checksum'
bz_eff_db_committed = 'brocade-zone/effective-configuration/db-committed'
bz_eff_cfg_action = 'brocade-zone/effective-configuration/cfg-action'
bz_eff_db_max = 'brocade-zone/effective-configuration/db-max'
bz_eff_default_zone = 'brocade-zone/effective-configuration/default-zone-access'
bz_eff_db_trans = 'brocade-zone/effective-configuration/db-transaction'
bz_eff_trans_token = 'brocade-zone/effective-configuration/transaction-token'
bz_eff_db_chassis_committed = 'brocade-zone/effective-configuration/db-chassis-wide-committed'
bz_def_zone = 'brocade-zone/defined-configuration/zone'
# Commonly used URIs: brocade-fdmi
fdmi_port_sym = 'brocade-fdmi/port-symbolic-name'
fdmi_node_sym = 'brocade-fdmi/node-symbolic-name'
# Commonly used URIs: brocade-fibrechannel-routing
bfr_uri = 'brocade-fibrechannel-routing'
bfr_rc = bfr_uri + '/routing-configuration'
bfr_rc_lc = bfr_rc + '/maximum-lsan-count'
bfr_rc_bfid = bfr_rc + '/backbone-fabric-id'
bfr_rc_ifl = bfr_rc + '/shortest-ifl'
bfr_rc_en_tags = '/lsan-enforce-tags'
bfr_rc_sp_tags = bfr_rc + '/lsan-speed-tag'
bfr_rc_mm = bfr_rc + '/migration-mode'
bfr_rc_ptde = bfr_rc + '/persistent-translate-domain-enabled'
bfr_lz = bfr_uri + '/lsan-zone'
bfr_ld = bfr_uri + '/lsan-device'
bfr_efa = bfr_uri + '/edge-fabric-alias'
bfr_fcr = bfr_uri + '/fibrechannel-router'
bfr_stats = bfr_uri + '/router-statistics'
bfr_stats_lz_in_use = bfr_stats + '/lsan-zones-in-use'
bfr_stats_mld = bfr_stats + '/maximum-lsan-devices'
bfr_stats_ld_in_use = bfr_stats + '/lsan-devices-in-use'
bfr_stats_mpds = bfr_stats + '/maximum-proxy-device-slots'
bfr_stats_pds_in_use = bfr_stats + '/proxy-device-slots-in-use'
bfr_stats_mpd = bfr_stats + '/maximum-proxy-devices'
bfr_stats_max_nr = bfr_stats + '/maximum-nr-ports'
bfr_pc = bfr_uri + '/proxy-config'
bfr_tdc = bfr_uri + '/translate-domain-config'
bfr_std = bfr_uri + '/stale-translate-domain'


class VirtualFabricIdError(Exception):
    pass


_VF_ID = '?vf-id='
# sfp_rules.xlsx actions may have been entered using CLI syntax so this table converts the CLI syntax to API syntax.
# Note that only actions with different syntax are converted. Actions not in this table are assumed to be correct API
# syntax.
_cli_to_api_convert = dict(
    fence='port-fence',
    snmp='snmp-trap',
    unquar='un-quarantine',
    decom='decommission',
    toggle='port-toggle',
    email='e-mail',
    uninstall_vtap='vtap-uninstall',
    sw_marginal='sw-marginal',
    sw_critical='sw-critical',
    sfp_marginal='sfp-marginal',
)
# Used in area in default_uri_map
NULL_OBJ = 0  # Actions on this KPI are either not supported or I didn't know what to do with them yet.
SESSION_OBJ = NULL_OBJ + 1
CHASSIS_OBJ = SESSION_OBJ + 1  # URI is associated with a physical chassis
CHASSIS_SWITCH_OBJ = CHASSIS_OBJ + 1   # URI is associated with a physical chassis containing switch objects
SWITCH_OBJ = CHASSIS_SWITCH_OBJ + 1  # URI is associated with a logical switch
SWITCH_PORT_OBJ = SWITCH_OBJ + 1  # URI is associated with a logical switch containing port objects
FABRIC_OBJ = SWITCH_PORT_OBJ + 1  # URI is associated with a fabric
FABRIC_SWITCH_OBJ = FABRIC_OBJ + 1  # URI is associated with a fabric containing switch objects
FABRIC_ZONE_OBJ = FABRIC_SWITCH_OBJ + 1  # URI is associated with a fabric containing zoning objects

op_no = 0  # Used in the op field in session
op_not_supported = 1
op_yes = 2

"""Below is the default URI map. It was built against FOS 9.1. It is necessary because there is not way to retrieve the
FID or area from the FOS API. An # RFE was submitted to get this information. This information is used to build
default_uri_map. Up to the time this was written, all keys (branches) were unique regardless of the URL type. In
FOS 9.1, a new URL type, "operations" was introduced. Although it appears that all keys are still unique, separate keys
for each type were added because it does not appear that anyone in engineering is thinking they need to be unique.

+---------------+-----------+-----------+-------+-------------------------------------------------------------------+
| Key 0         | Branch    |Key 1      | Type  | Description                                                       |
+===============+===========+===========+=======+===================================================================+
|               |           |           | dict  | URI prefix is just "/rest/"                                       |
+---------------+-----------+-----------+-------+-------------------------------------------------------------------+
|               |           | area      | int   | Used to indicate what type of object this request is associated   |
|               |           |           |       | with. Search for "Used in area in default_uri_map" above for      |
|               |           |           |       | details.                                                          |
+---------------+-----------+-----------+-------+-------------------------------------------------------------------+
|               |           | fid       | bool  | If True, this is a fabric level request and the VF ID (?vf-id=xx) |
|               |           |           |       | should be appended to the uri                                     |
+---------------+-----------+-----------+-------+-------------------------------------------------------------------+
|               |           | methods   | list  | List of supported methods. Currently, only checked for GET.       |
|               |           |           |       | Intended for future use.                                          |
+---------------+-----------+-----------+-------+-------------------------------------------------------------------+
|               |           | op        | int   | "Options Polled". 0: No, 1: OPTIONS not supported, 2: Yes         |
+---------------+-----------+-----------+-------+-------------------------------------------------------------------+
| running       |           |           | dict  | URI prefix is "/rest/running/". Sub dictionaries are area, fid,   |
|               |           |           |       | and methods as with "root".                                       |
+---------------+-----------+-----------+-------+-------------------------------------------------------------------+
| operations    |           |           | dict  | URI prefix is "/rest/operations/". Sub dictionaries are area, fid,|
|               |           |           |       | and methods as with "root".                                       |
+---------------+-----------+-----------+-------+-------------------------------------------------------------------+
"""
default_uri_map = {
    'auth-token': dict(area=NULL_OBJ, fid=True, methods=('OPTIONS', 'GET')),
    'brocade-module-version': dict(area=NULL_OBJ, fid=False, methods=()),
    'brocade-module-version/module': dict(area=NULL_OBJ, fid=False, methods=('GET', 'HEAD', 'OPTIONS')),
    'login': dict(area=SESSION_OBJ, fid=False, methods=('POST',)),
    'logout': dict(area=SESSION_OBJ, fid=False, methods=('POST',)),
    'running': {
        'brocade-fibrechannel-switch': {
            'fibrechannel-switch': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'switch-fabric-statistics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'topology-domain': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'topology-route': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'topology-error': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-application-server': {
           'application-server-device': dict(area=CHASSIS_OBJ, id=False, methods=('GET', 'HEAD', 'OPTIONS')),
        },
        'brocade-fibrechannel-logical-switch': {
            'fibrechannel-logical-switch': dict(area=CHASSIS_SWITCH_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-interface': {
            'fibrechannel': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'fibrechannel-statistics': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'fibrechannel-performance': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'fibrechannel-statistics-db': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'extension-ip-interface': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('GET', 'DELETE')),
            'fibrechannel-lag': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'gigabitethernet': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'gigabitethernet-statistics': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'logical-e-port': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'portchannel': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'portchannel-statistics': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'fibrechannel-router-statistics': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-media': {
            'media-rdp': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-fabric': {
            'access-gateway': dict(area=FABRIC_SWITCH_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'fabric-switch': dict(area=FABRIC_SWITCH_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-fibrechannel-routing': {
            'routing-configuration': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'lsan-zone': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'lsan-device': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'edge-fabric-alias': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'fibrechannel-router': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'router-statistics': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'proxy-config': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'translate-domain-config': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'stale-translate-domain': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
         },
        'brocade-zone': {
            'defined-configuration': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'effective-configuration': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'fabric-lock': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-fibrechannel-diagnostics': {
            'fibrechannel-diagnostics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-fdmi': {
            'hba': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'port': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-name-server': {
            'fibrechannel-name-server': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-fabric-traffic-controller': {
            'fabric-traffic-controller-device': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-fibrechannel-configuration': {
            'switch-configuration': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'f-port-login-settings': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'port-configuration': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'zone-configuration': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'fabric': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'chassis-config-settings': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'fos-settings': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-logging': {
            'audit': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'syslog-server': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'log-setting': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'log-quiet-control': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'raslog': dict(area=CHASSIS_OBJ, fid=False,  methods=('OPTIONS', 'GET')),
            'raslog-module': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'supportftp': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'error-log': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'audit-log': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'management-session-login-information': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-fibrechannel-trunk': {
            'trunk': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'performance': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'trunk-area': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-ficon': {
            'cup': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'logical-path': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'rnid': dict(area=SWITCH_PORT_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'switch-rnid': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'lirr': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'rlir': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-fru': {
            'power-supply': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'fan': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'blade': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'history-log': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'sensor': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'wwn': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-chassis': {
            'chassis': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'ha-status': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'credit-recovery': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'management-interface-configuration': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'management-ethernet-interface': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'management-port-track-configuration':  dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'management-port-connection-statistics': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'sn-chassis': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'version': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-maps': {
            'maps-config': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'rule': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'maps-policy': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'group': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'dashboard-rule': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'dashboard-history': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'dashboard-misc': dict(area=SWITCH_OBJ, fid=True, methods=('GET', 'PUT')),
            'credit-stall-dashboard': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'oversubscription-dashboard': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'system-resources': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'paused-cfg': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'monitoring-system-matrix': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'switch-status-policy-report': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'fpi-profile': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'maps-violation': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'backend-ports-history': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'gigabit-ethernet-ports-history': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'maps-device-login': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'quarantined-devices': dict(area=SWITCH_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-time': {
            'clock-server': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'time-zone': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'ntp-clock-server': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'ntp-clock-server-key': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-security': {
            'sec-crypto-cfg': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'sec-crypto-cfg-template': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'sec-crypto-cfg-template-action': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS',)),
            'password-cfg': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'user-specific-password-cfg': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'user-config': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'ldap-role-map': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'sshutil': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'sshutil-key': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'sshutil-known-host': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'sshutil-public-key': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'sshutil-public-key-action': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS',)),
            'password': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS',)),
            'security-certificate-generate': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS',)),
            'security-certificate-action': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'DELETE')),
            'security-certificate': dict(area=CHASSIS_OBJ, fid=False,  methods=('OPTIONS', 'GET')),
            'radius-server': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'tacacs-server': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'ldap-server': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'auth-spec': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'ipfilter-policy': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'ipfilter-rule': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'security-certificate-extension': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'role-config': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'rbac-class': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'management-rbac-map': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'security-violation-statistics': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'acl-policy': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'defined-fcs-policy-member-list': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'active-fcs-policy-member-list': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'defined-scc-policy-member-list': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'active-scc-policy-member-list': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'defined-dcc-policy-member-list': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'active-dcc-policy-member-list': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'security-policy-size': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'authentication-configuration': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'dh-chap-authentication-secret': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'policy-distribution-config': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-license': {
            'license': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'ports-on-demand-license-info': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'end-user-license-agreement': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-snmp': {
            'system': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'mib-capability': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'trap-capability': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'v1-account': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'v1-trap': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'v3-account': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'v3-trap': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'access-control': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-management-ip-interface': {
            'management-ip-interface': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'management-interface-lldp-neighbor': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'management-interface-lldp-statistics': dict(area=CHASSIS_OBJ, fid=False,  methods=('OPTIONS', 'GET')),
        },
        'brocade-firmware': {
            'firmware-history': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
            'firmware-config': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-dynamic-feature-tracking': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        'brocade-usb': {
            'usb-file': dict(area=CHASSIS_OBJ, fid=False, methods=('OPTIONS', 'GET')),
        },
        'brocade-extension-ip-route': {
            'extension-ip-route': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-extension-ipsec-policy': {
            'extension-ipsec-policy': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-extension-tunnel': {  # I think some of these should be SWITCH_PORT_OBJ
            'extension-tunnel': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'extension-tunnel-statistics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'extension-circuit': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'extension-circuit-statistics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'circuit-qos-statistics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'circuit-interval-statistics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'wan-statistics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'wan-statistics-v1': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-extension': {
            'traffic-control-list': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'dp-hcl-status': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'global-lan-statistics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'lan-flow-statistics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-lldp': {
            'lldp-neighbor': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'lldp-profile': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'lldp-statistics': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'lldp-global': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
        'brocade-supportlink': {
            'supportlink-profile': dict(area=CHASSIS_OBJ, fid=False, methods=('GET', 'PATCH', 'HEAD', 'OPTIONS')),
            'supportlink-history': dict(area=CHASSIS_OBJ, fid=False, methods=('GET', 'PATCH', 'HEAD', 'OPTIONS')),
        },
        'brocade-traffic-optimizer': {
            'performance-group-profile': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'performance-group-flows': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
            'performance-group': dict(area=FABRIC_OBJ, fid=True, methods=('OPTIONS', 'GET')),
        },
    },
    'operations': {
        'brocade-diagnostics': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'configdownload': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'configupload': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'date': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'extension': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'factory-reset': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'fibrechannel-fabric': dict(area=NULL_OBJ, fid=True,  methods=('POST', 'OPTIONS')),
        'fibrechannel-zone': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'firmwaredownload': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'lldp': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'management-ethernet-interface': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'ntp-clock-server': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'port': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'port-decommission': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'reboot': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'restart': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'sdd-quarantine': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'security-acl-policy': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'security-ipfilter': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'security-reset-violation-statistics': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'security-policy-distribute': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'security-policy-chassis-distribute': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'security-fabric-wide-policy-distribute': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'security-authentication-secret': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'security-authentication-configuration': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'security-role-clone': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'security-certificate': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'show-status': {'area': NULL_OBJ, 'fid': False, 'methods': ('POST',),
                        'message-id': dict(area=NULL_OBJ, fid=False, methods=('POST',))},
        'supportsave': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'traffic-optimizer': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'device-management': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'license': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'pcie-health': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'pcie-health-test': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'fabric': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'supportlink': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'usb-delete-file': dict(area=NULL_OBJ, fid=False, methods=('POST', 'OPTIONS')),
        'portchannel': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
        'device-login-rebalance': dict(area=NULL_OBJ, fid=True, methods=('POST', 'OPTIONS')),
    },
}


def mask_ip_addr(addr, keep_last=True):
    """Replaces IP address with xxx.xxx.xxx.123 or all x depending on keep_last

    :param addr: IP address
    :type addr: str
    :param keep_last: If true, preserves the last octet. If false, replace all octets with xxx
    :type keep_last: bool
    :return: Masked IP
    :rtype: str
    """
    tip = ''
    if isinstance(addr, str):
        tl = addr.split('.')
        for i in range(0, len(tl) - 1):
            tip += 'xxx.'
        tip += tl[len(tl) - 1] if keep_last else 'xxx'
    return tip


def vfid_to_str(vfid):
    """Converts a FID to a string, '?vf-id=xx' to be appended to a URI that requires a FID

    :param vfid: FOS session object
    :type vfid: int
    :return: '?vf-id=x' where x is the vfid converted to a str. If vfid is None then just '' is returned
    :rtype: str
    """
    if vfid is None:
        return ''
    try:  # FOS gets really hosed up if anything other than an integer is used in the URI after '?vf-id='.
        if not isinstance(vfid, int):
            raise TypeError
        if vfid < 1 or vfid > 128:
            raise TypeError
    except TypeError:
        buf = '. FIDs must be integers, type int, in the range 1-128.'
        brcdapi_log.exception('Invalid FID. Type: ' + str(type(vfid)) + '. Value: ' + str(vfid) + buf, echo=True)
        raise VirtualFabricIdError
    return _VF_ID + str(vfid)


def add_uri_map(session, rest_d):
    """Builds out the URI map and adds it to the session. Intended to be called once immediately after login

    :param session: Session dictionary returned from brcdapi.brcdapi_rest.login()
    :type session: dict
    :param rest_d: Object returned from FOS for 'brocade-module-version'
    :type rest_d: dict
    """
    global default_uri_map

    ml = list()
    try:
        mod_l = rest_d['brocade-module-version']['module']
    except KeyError:
        brcdapi_log.exception('ERROR: Invalid data in rest_d parameter.', echo=True)
        return

    # Add each item to the session uri_map
    uri_map_d = dict()
    session.update(uri_map=uri_map_d)
    for mod_d in mod_l:
        to_process_l = list()

        # Create a list of individual modules that need to be parsed
        try:
            uri = mod_d['uri']
            # The running leaves all have individual requests while all else are 1:1 requests.
            if '/rest/running/' in uri:
                add_l = mod_d['objects'].get('object')
                if isinstance(add_l, list):
                    base_l = uri.split('/')[2:]
                    for buf_l in [[buf] for buf in add_l]:
                        to_process_l.append(base_l + buf_l)
            else:
                to_process_l.append(uri.split('/')[2:])
        except (IndexError, KeyError):
            brcdapi_log.exception(['', 'ERROR: Unexpected value in: ' + pprint.pformat(mod_d), ''], echo=True)
            continue

        # Parse each module
        for uri_l in to_process_l:

            # Find the dictionary in the default URI map
            d, k, default_d, last_d = None, None, default_uri_map, uri_map_d
            for k in uri_l:
                if default_d is not None:
                    default_d = default_d.get(k)
                d = last_d.get(k)
                if d is None:
                    d = dict()
                    last_d.update({k: d})
                last_d = d

            # Add this module (API request) to the URI map, uri_map, in the session object.
            if isinstance(d, dict):
                new_mod_d = copy.deepcopy(mod_d)
                new_uri = uri + '/' + k if '/rest/running/' in uri else uri
                if isinstance(default_d, dict):
                    new_mod_d.update(area=default_d.get('area'),
                                     fid=default_d.get('fid'),
                                     methods=gen_util.convert_to_list(default_d.get('methods')),
                                     op=op_no)
                    new_mod_d['uri'] = new_uri
                    last_d.update(new_mod_d)
                else:
                    ml.append('UNKNOWN URI: ' + new_uri)
            else:
                brcdapi_log.exception(['', 'ERROR: Unexpected value in: ' + pprint.pformat(mod_d), ''], echo=True)

    if len(ml) > 0:
        brcdapi_log.log(ml, echo=True)

    return


def split_uri(uri, run_op_out=False):
    """From a URI: Removes '/rest/'. Optionally removes 'running' and 'operations'. Returns a list of elements

    :param uri: URI
    :type uri: str
    :param run_op_out: If True, also remove 'running' and 'operations'
    :type run_op_out: bool
    :return: URI split into a list with leading '/rest/' stripped out
    :rtype: list
    """
    uri_l = uri.split('/')
    if len(uri_l) > 0 and uri_l[0] == '':
        uri_l.pop(0)
    if len(uri_l) > 0 and uri_l[0] == 'rest':
        uri_l.pop(0)
    if run_op_out and len(uri_l) > 0 and uri_l[0] in ('running', 'operations'):
        uri_l.pop(0)

    return uri_l


def session_cntl(session, in_uri):
    """Returns the control dictionary (uri map) for the uri

    :param session: Dictionary of the session returned by login.
    :type session: dict
    :param in_uri: URI
    :type in_uri: str
    :return: Control dictionary associated with uri. None if not found
    :rtype: dict, None
    """
    if 'operations/show-status/message-id/' in in_uri:
        return None

    uri = '/'.join(split_uri(in_uri))
    d = gen_util.get_key_val(session.get('uri_map'), uri)
    if d is None:
        d = gen_util.get_key_val(session.get('uri_map'), 'running/' + uri)  # The old way didn't include 'running/'

    return d


def format_uri(session, uri, fid):
    """Formats a full URI.

    :param session: Session object returned from login()
    :type session: dict
    :param uri: Rest URI. Must not include IP address or '/rest/'
    :type uri: str
    :param fid: Fabric ID
    :type fid: int, None
    :return: Full URI
    :rtype: str
    """
    d = session_cntl(session, uri)

    return '/rest/' + uri if d is None else d['uri'] if d['fid'] is None else d['uri'] + vfid_to_str(fid)


def uri_d(session, uri):
    """Returns the dictionary in the URI map for a specified URI

    :param session: Session object returned from login()
    :type session: dict
    :param uri: URI in slash notation
    :type uri: str
    """
    d = gen_util.get_struct_from_obj(session.get('uri_map'), uri)
    if not isinstance(d, dict) and gen_util.get_key_val(default_uri_map, uri) is None:
        brcdapi_log.log('UNKNOWN URI: ' + uri + '. Check the log for details.', echo=True)  # For humans
        brcdapi_log.exception('UNKNOWN URI: ' + uri, echo=True)  # For the log
    return d


def _get_uri(map_d):
    rl = list()
    if isinstance(map_d, dict):
        for d in map_d.values():
            if isinstance(d, dict):
                uri = d.get('uri')
                if uri is not None:
                    rl.append('/'.join(split_uri(uri)))
                    continue
                else:
                    rl.extend(_get_uri(d))

    return rl


def uris_for_method(session, http_method, uri_d_flag=False):
    """Returns the dictionaries or URIs supporting a certain HTTP method.

    :param session: Session object returned from login()
    :type session: dict
    :param http_method: The HTTP method to look for
    :type http_method: str, None
    :param uri_d_flag: If True, return a list of the URI dictionaries. If False, just return a list of the URIs
    :type uri_d_flag: bool
    :return: List of URIs or URI dictionaries depending on uri_d_flag
    :rtype: list
    """
    rl, uri_map_d = list(), session.get('uri_map')
    if not isinstance(uri_map_d, dict):
        return rl  # Just in case someone calls this method before logging in.

    for uri in _get_uri(uri_map_d.get('running')) + _get_uri(uri_map_d.get('operations')):
        d = uri_d(session, uri)
        if http_method in gen_util.convert_to_list(d.get('methods')):
            if uri_d_flag:
                rl.append(d)
            else:
                rl.append(uri)

    return rl


def _int_dict_to_uri(convert_dict):
    """Converts a dictionary to a list of '/' separated strings. Assumes the first non-dict is the end

    :param convert_dict: Dictionary to convert
    :type convert_dict: None, str, list, tuple, int, float, dict
    :return: List of str
    :rtype: list
    """
    rl = list()
    if isinstance(convert_dict, dict):
        for k, v in convert_dict.items():
            if isinstance(v, dict):
                for uri_l in dict_to_uri(v):
                    rl.append(str(k) + '/' + '/'.join(uri_l))
            else:
                rl.append('/' + str(k))

    return rl


def dict_to_uri(convert_dict):
    """Converts a dictionary to a list of '/' separated strings. Assumes the first non-dict is the end

    :param convert_dict: Dictionary to convert
    :type convert_dict: None, str, list, tuple, int, float, dict
    :return: List of str
    :rtype: list
    """
    rl = list()
    if isinstance(convert_dict, dict):
        for k, v in convert_dict.items():
            if isinstance(v, dict):
                for buf in dict_to_uri(v):
                    rl.append(str(k) + '/' + buf)
            else:
                rl.append(str(k))

    return rl


def validate_fid(in_fid):
    """Validates a FID or list of FIDs

    :param in_fid: FID or list of FIDs as integers. None is permitted to simplify logic for the calling function.
    :type in_fid: int, list, tuple, None
    :return: Error message. Empty string if no errors.
    :rtype: str
    """
    try:
        for fid in [int(f) for f in gen_util.convert_to_list(in_fid)]:
            if fid < 1 or fid > 128:
                raise TypeError
    except TypeError:
        return ' FIDs must be integers in the range 1-128'
    return ''


# _letter_to_num_d is used in fos_to_dict() to convert a patch level release to a number for numerical comparison.
# The easy thing to do would have been to treat the letter as utf-8 and convert to it's integer value. Although that
# should work in a mainframe environment, which is EBCDIC, a mainframe wasn't available for testing.
_letter_to_num_d = dict(a=1, b=2, c=3, d=4, e=5, f=6, g=7, h=8, i=9, j=10, k=11, l=12, m=13, n=14, o=15, p=16, q=17,
                        r=18, s=19, t=20, u=21, v=22, w=23, x=24, y=25, z=26)


def fos_to_dict(version_in, valid_check=True):
    """Converts a FOS version into a dictionary to be used for comparing for version numbers

    +-----------+-------+-------------------------------------------------------------------------------+
    | Key       | Type  |Description                                                                    |
    +===========+=======+===============================================================================+
    | version   | str   | Same as version_in                                                            |
    +-----------+-------+-------------------------------------------------------------------------------+
    | major     | int   | In example 9.1.0b, this is 9                                                  |
    +-----------+-------+-------------------------------------------------------------------------------+
    | feature   | int   | In example 9.1.0b, this is 1                                                  |
    +-----------+-------+-------------------------------------------------------------------------------+
    | minor     | int   | In example 9.1.0b, this is 0                                                  |
    +-----------+-------+-------------------------------------------------------------------------------+
    | bug       | int   | In example 9.1.0b, this is 2 (converted to a numeric for easier comparisons). |
    |           |       | In example 9.1.0, this is 0.                                                  |
    +-----------+-------+-------------------------------------------------------------------------------+
    | patch     | str   | In example 9.1.0b, this is an empty str. In 9.1.0b_01, this is "_01"          |
    +-----------+-------+-------------------------------------------------------------------------------+

    :param version_in: FOS version
    :type version_in: str
    :param valid_check: If True, creates an exception entry in the log if the version of FOS is not valid
    :type valid_check: bool
    :return: Dictionary as described above
    :rtype dict
    """
    global _letter_to_num_d

    try:
        version = version_in.lower()
        if version[0] == 'v':
            version = version[1:]
        version_l = version.split('.')
        if len(version_l[2]) > 1:
            try:
                bug = _letter_to_num_d[version_l[2][1:2]]
                patch = version_l[2][2:] if len(version_l[2]) > 1 else ''
            except KeyError:
                bug = 0
                patch = version_l[2][1:]
        else:
            bug = 0
            patch = ''
        return dict(version=str(version_in),
                    major=int(version_l[0]),
                    feature=int(version_l[1]),
                    minor=int(version_l[2][0:1]),
                    bug=bug,
                    patch=patch)
    except (IndexError, TypeError, ValueError, AttributeError):
        if valid_check:
            brcdapi_log.exception(['Invalid FOS version: ' + str(version_in), 'Type: ' + str(type(version_in))],
                                  echo=True)

    return dict(version=str(version_in), major=0, feature=0, minor=0, bug=0, patch='')
