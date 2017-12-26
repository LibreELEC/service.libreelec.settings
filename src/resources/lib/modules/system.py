################################################################################
#      This file is part of OpenELEC - http://www.openelec.tv
#      Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
#      Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)
#
#  This program is dual-licensed; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with OpenELEC; see the file COPYING.  If not, see
#  <http://www.gnu.org/licenses/>.
#
#  Alternatively, you can license this library under a commercial license,
#  please contact OpenELEC Licensing for more information.
#
#  For more information contact:
#  OpenELEC Licensing  <license@openelec.tv>  http://www.openelec.tv
################################################################################
# -*- coding: utf-8 -*-

import os
import re
import glob
import time
import json
import xbmc
import xbmcgui
import tarfile
import oeWindows
import threading
import subprocess
import shutil
from xml.dom import minidom


class system:

    ENABLED = False
    KERNEL_CMD = None
    UPDATE_REQUEST_URL = None
    UPDATE_DOWNLOAD_URL = None
    LOCAL_UPDATE_DIR = None
    XBMC_RESET_FILE = None
    LIBREELEC_RESET_FILE = None
    KEYBOARD_INFO = None
    UDEV_KEYBOARD_INFO = None
    NOX_KEYBOARD_INFO = None
    BACKUP_DIRS = None
    BACKUP_DESTINATION = None
    RESTORE_DIR = None
    GET_CPU_FLAG = None
    SET_CLOCK_CMD = None
    menu = {'1': {
        'name': 32002,
        'menuLoader': 'load_menu',
        'listTyp': 'list',
        'InfoText': 700,
        }}

    def __init__(self, oeMain):
        try:
            oeMain.dbg_log('system::__init__', 'enter_function', 0)
            self.oe = oeMain
            self.struct = {
                'ident': {
                    'order': 1,
                    'name': 32189,
                    'settings': {'hostname': {
                        'order': 1,
                        'name': 32190,
                        'value': '',
                        'action': 'set_hostname',
                        'type': 'text',
                        'validate': '^([a-zA-Z0-9](?:[a-zA-Z0-9-\.]*[a-zA-Z0-9]))$',
                        'InfoText': 710,
                        }},
                    },
                'keyboard': {
                    'order': 2,
                    'name': 32009,
                    'settings': {
                        'KeyboardLayout1': {
                            'order': 1,
                            'name': 32010,
                            'value': 'us',
                            'action': 'set_keyboard_layout',
                            'type': 'multivalue',
                            'values': [],
                            'InfoText': 711,
                            },
                        'KeyboardVariant1': {
                            'order': 2,
                            'name': 32386,
                            'value': '',
                            'action': 'set_keyboard_layout',
                            'type': 'multivalue',
                            'values': [],
                            'InfoText': 753,
                            },
                        'KeyboardLayout2': {
                            'order': 3,
                            'name': 32010,
                            'value': 'us',
                            'action': 'set_keyboard_layout',
                            'type': 'multivalue',
                            'values': [],
                            'InfoText': 712,
                            },
                        'KeyboardVariant2': {
                            'order': 4,
                            'name': 32387,
                            'value': '',
                            'action': 'set_keyboard_layout',
                            'type': 'multivalue',
                            'values': [],
                            'InfoText': 754,
                            },
                        'KeyboardType': {
                            'order': 5,
                            'name': 32330,
                            'value': 'pc105',
                            'action': 'set_keyboard_layout',
                            'type': 'multivalue',
                            'values': [],
                            'InfoText': 713,
                            },
                        },
                    },
                'update': {
                    'order': 3,
                    'name': 32013,
                    'settings': {
                        'AutoUpdate': {
                            'name': 32014,
                            'value': 'auto',
                            'action': 'set_auto_update',
                            'type': 'multivalue',
                            'values': ['auto', 'manual'],
                            'InfoText': 714,
                            'order': 1,
                            },
                        'UpdateNotify': {
                            'name': 32365,
                            'value': '1',
                            'action': 'set_value',
                            'type': 'bool',
                            'InfoText': 715,
                            'order': 2,
                            },
                        'ShowCustomChannels': {
                            'name': 32016,
                            'value': '0',
                            'action': 'set_custom_channel',
                            'type': 'bool',
                            'parent': {
                                'entry': 'AutoUpdate',
                                'value': ['manual'],
                                },
                            'InfoText': 761,
                            'order': 3,
                            },
                        'CustomChannel1': {
                            'name': 32017,
                            'value': '',
                            'action': 'set_custom_channel',
                            'type': 'text',
                            'parent': {
                                'entry': 'ShowCustomChannels',
                                'value': ['1'],
                                },
                            'InfoText': 762,
                            'order': 4,
                            },
                        'CustomChannel2': {
                            'name': 32018,
                            'value': '',
                            'action': 'set_custom_channel',
                            'type': 'text',
                            'parent': {
                                'entry': 'ShowCustomChannels',
                                'value': ['1'],
                                },
                            'InfoText': 762,
                            'order': 5,
                            },
                        'CustomChannel3': {
                            'name': 32019,
                            'value': '',
                            'action': 'set_custom_channel',
                            'type': 'text',
                            'parent': {
                                'entry': 'ShowCustomChannels',
                                'value': ['1'],
                                },
                            'InfoText': 762,
                            'order': 6,
                            },
                        'Channel': {
                            'name': 32015,
                            'value': '',
                            'action': 'set_channel',
                            'type': 'multivalue',
                            'parent': {
                                'entry': 'AutoUpdate',
                                'value': ['manual'],
                                },
                            'values': [],
                            'InfoText': 760,
                            'order': 7,
                            },
                        'Build': {
                            'name': 32020,
                            'value': '',
                            'action': 'do_manual_update',
                            'type': 'multivalue',
                            'parent': {
                                'entry': 'AutoUpdate',
                                'value': ['manual'],
                                },
                            'values': [],
                            'InfoText': 770,
                            'order': 8,
                            },
                        },
                    },
                'backup': {
                    'order': 7,
                    'name': 32371,
                    'settings': {
                        'backup': {
                            'name': 32372,
                            'value': '0',
                            'action': 'do_backup',
                            'type': 'button',
                            'InfoText': 722,
                            'order': 1,
                            },
                        'restore': {
                            'name': 32373,
                            'value': '0',
                            'action': 'do_restore',
                            'type': 'button',
                            'InfoText': 723,
                            'order': 2,
                            },
                        },
                    },
                'reset': {
                    'order': 8,
                    'name': 32323,
                    'settings': {
                        'xbmc_reset': {
                            'name': 32324,
                            'value': '0',
                            'action': 'reset_xbmc',
                            'type': 'button',
                            'InfoText': 724,
                            'order': 1,
                            },
                        'oe_reset': {
                            'name': 32325,
                            'value': '0',
                            'action': 'reset_oe',
                            'type': 'button',
                            'InfoText': 725,
                            'order': 2,
                            },
                        },
                    },
                'debug': {
                    'order': 9,
                    'name': 32376,
                    'settings': {
                        'paste_system': {
                            'name': 32377,
                            'value': '0',
                            'action': 'do_send_system_logs',
                            'type': 'button',
                            'InfoText': 718,
                            'order': 1,
                            },
                        'paste_crash': {
                            'name': 32378,
                            'value': '0',
                            'action': 'do_send_crash_logs',
                            'type': 'button',
                            'InfoText': 719,
                            'order': 2,
                            },
                        },
                    },
                }

            self.keyboard_layouts = False
            self.nox_keyboard_layouts = False
            self.last_update_check = 0
            self.arrVariants = {}
            self.oe.dbg_log('system::__init__', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::__init__', 'ERROR: (' + repr(e) + ')')

    def start_service(self):
        try:
            self.oe.dbg_log('system::start_service', 'enter_function', 0)
            self.is_service = True
            self.load_values()
            self.set_hostname()
            self.set_keyboard_layout()
            self.set_hw_clock()
            self.set_auto_update()
            del self.is_service
            self.oe.dbg_log('system::start_service', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::start_service', 'ERROR: (' + repr(e) + ')')

    def stop_service(self):
        try:
            self.oe.dbg_log('system::stop_service', 'enter_function', 0)
            if hasattr(self, 'update_thread'):
                self.update_thread.stop()
            self.oe.dbg_log('system::stop_service', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::stop_service', 'ERROR: (' + repr(e) + ')')

    def do_init(self):
        try:
            self.oe.dbg_log('system::do_init', 'enter_function', 0)
            self.oe.dbg_log('system::do_init', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::do_init', 'ERROR: (' + repr(e) + ')')

    def exit(self):
        self.oe.dbg_log('system::exit', 'enter_function', 0)
        self.oe.dbg_log('system::exit', 'exit_function', 0)
        pass

    def load_values(self):
        try:
            self.oe.dbg_log('system::load_values', 'enter_function', 0)

            # CPU x64 flag

            self.cpu_lm_flag = self.oe.execute(self.GET_CPU_FLAG, 1)

            # Keyboard Layout

            (
                arrLayouts,
                arrTypes,
                self.arrVariants,
                ) = self.get_keyboard_layouts()
            if not arrTypes is None:
                self.struct['keyboard']['settings']['KeyboardType']['values'] = arrTypes
                value = self.oe.read_setting('system', 'KeyboardType')
                if not value is None:
                    self.struct['keyboard']['settings']['KeyboardType']['value'] = value
            if not arrLayouts is None:
                self.struct['keyboard']['settings']['KeyboardLayout1']['values'] = arrLayouts
                self.struct['keyboard']['settings']['KeyboardLayout2']['values'] = arrLayouts
                value = self.oe.read_setting('system', 'KeyboardLayout1')
                if not value is None:
                    self.struct['keyboard']['settings']['KeyboardLayout1']['value'] = value
                value = self.oe.read_setting('system', 'KeyboardVariant1')
                if not value is None:
                    self.struct['keyboard']['settings']['KeyboardVariant1']['value'] = value
                value = self.oe.read_setting('system', 'KeyboardLayout2')
                if not value is None:
                    self.struct['keyboard']['settings']['KeyboardLayout2']['value'] = value
                value = self.oe.read_setting('system', 'KeyboardVariant2')
                if not value is None:
                    self.struct['keyboard']['settings']['KeyboardVariant2']['value'] = value
                if not arrTypes == None:
                    self.keyboard_layouts = True

            if not os.path.exists('/usr/bin/setxkbmap'):
                self.struct['keyboard']['settings']['KeyboardLayout2']['hidden'] = 'true'
                self.struct['keyboard']['settings']['KeyboardType']['hidden'] = 'true'
                self.struct['keyboard']['settings']['KeyboardVariant1']['hidden'] = 'true'
                self.struct['keyboard']['settings']['KeyboardVariant2']['hidden'] = 'true'
                self.nox_keyboard_layouts = True

            # Hostname

            value = self.oe.read_setting('system', 'hostname')
            if not value is None:
                self.struct['ident']['settings']['hostname']['value'] = value
            else:
                self.struct['ident']['settings']['hostname']['value'] = self.oe.DISTRIBUTION

            # AutoUpdate

            value = self.oe.read_setting('system', 'AutoUpdate')
            if not value is None:
                self.struct['update']['settings']['AutoUpdate']['value'] = value
            value = self.oe.read_setting('system', 'UpdateNotify')
            if not value is None:
                self.struct['update']['settings']['UpdateNotify']['value'] = value
            if os.path.isfile('%s/SYSTEM' % self.LOCAL_UPDATE_DIR):
                self.update_in_progress = True

            # Manual Update

            value = self.oe.read_setting('system', 'Channel')
            if not value is None:
                self.struct['update']['settings']['Channel']['value'] = value
            value = self.oe.read_setting('system', 'ShowCustomChannels')
            if not value is None:
                self.struct['update']['settings']['ShowCustomChannels']['value'] = value

            value = self.oe.read_setting('system', 'CustomChannel1')
            if not value is None:
                self.struct['update']['settings']['CustomChannel1']['value'] = value
            value = self.oe.read_setting('system', 'CustomChannel2')
            if not value is None:
                self.struct['update']['settings']['CustomChannel2']['value'] = value
            value = self.oe.read_setting('system', 'CustomChannel3')
            if not value is None:
                self.struct['update']['settings']['CustomChannel3']['value'] = value

            self.update_json = self.build_json()

            self.struct['update']['settings']['Channel']['values'] = self.get_channels()
            self.struct['update']['settings']['Build']['values'] = self.get_available_builds()

            # AutoUpdate = manual by environment var.

            if os.path.exists('/dev/.update_disabled'):
                self.update_disabled = True
                self.struct['update']['hidden'] = 'true'
                self.struct['update']['settings']['AutoUpdate']['value'] = 'manual'
                self.struct['update']['settings']['UpdateNotify']['value'] = '0'
            self.oe.dbg_log('system::load_values', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::load_values', 'ERROR: (' + repr(e) + ')')

    def load_menu(self, focusItem):
        try:
            self.oe.dbg_log('system::load_menu', 'enter_function', 0)
            self.oe.winOeMain.build_menu(self.struct)
            self.oe.dbg_log('system::load_menu', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::load_menu', 'ERROR: (' + repr(e) + ')')

    def set_value(self, listItem):
        try:
            self.oe.dbg_log('system::set_value', 'enter_function', 0)
            self.struct[listItem.getProperty('category')]['settings'][listItem.getProperty('entry')]['value'] = listItem.getProperty('value')
            self.oe.write_setting('system', listItem.getProperty('entry'), unicode(listItem.getProperty('value')))
            self.oe.dbg_log('system::set_value', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::set_value', 'ERROR: (' + repr(e) + ')')

    def set_keyboard_layout(self, listItem=None):
        try:
            self.oe.dbg_log('system::set_keyboard_layout', 'enter_function', 0)
            if not listItem == None:
                if listItem.getProperty('entry') == 'KeyboardLayout1':
                    if self.struct['keyboard']['settings']['KeyboardLayout1']['value'] != listItem.getProperty('value'):
                        self.struct['keyboard']['settings']['KeyboardVariant1']['value'] = ''
                if listItem.getProperty('entry') == 'KeyboardLayout2':
                    if self.struct['keyboard']['settings']['KeyboardLayout2']['value'] != listItem.getProperty('value'):
                        self.struct['keyboard']['settings']['KeyboardVariant2']['value'] = ''
                self.set_value(listItem)
            if self.keyboard_layouts == True:
                self.struct['keyboard']['settings']['KeyboardVariant1']['values'] = self.arrVariants[self.struct['keyboard']['settings'
                        ]['KeyboardLayout1']['value']]
                self.struct['keyboard']['settings']['KeyboardVariant2']['values'] = self.arrVariants[self.struct['keyboard']['settings'
                        ]['KeyboardLayout2']['value']]
                self.oe.dbg_log('system::set_keyboard_layout', unicode(self.struct['keyboard']['settings']['KeyboardLayout1']['value']) + ','
                                + unicode(self.struct['keyboard']['settings']['KeyboardLayout2']['value']) + ' ' + '-model '
                                + unicode(self.struct['keyboard']['settings']['KeyboardType']['value']), 1)
                if not os.path.exists(os.path.dirname(self.UDEV_KEYBOARD_INFO)):
                    os.makedirs(os.path.dirname(self.UDEV_KEYBOARD_INFO))
                config_file = open(self.UDEV_KEYBOARD_INFO, 'w')
                config_file.write('XKBMODEL="' + self.struct['keyboard']['settings']['KeyboardType']['value'] + '"\n')
                config_file.write('XKBVARIANT="%s,%s"\n' % (self.struct['keyboard']['settings']['KeyboardVariant1']['value'],
                                  self.struct['keyboard']['settings']['KeyboardVariant2']['value']))
                config_file.write('XKBLAYOUT="' + self.struct['keyboard']['settings']['KeyboardLayout1']['value'] + ',' + self.struct['keyboard'
                                  ]['settings']['KeyboardLayout2']['value'] + '"\n')
                config_file.write('XKBOPTIONS="grp:alt_shift_toggle"\n')
                config_file.close()
                parameters = [
                    '-display ' + os.environ['DISPLAY'],
                    '-layout ' + self.struct['keyboard']['settings']['KeyboardLayout1']['value'] + ',' + self.struct['keyboard']['settings'
                            ]['KeyboardLayout2']['value'],
                    '-variant ' + self.struct['keyboard']['settings']['KeyboardVariant1']['value'] + ',' + self.struct['keyboard']['settings'
                            ]['KeyboardVariant2']['value'],
                    '-model ' + unicode(self.struct['keyboard']['settings']['KeyboardType']['value']),
                    '-option "grp:alt_shift_toggle"',
                    ]
                self.oe.execute('setxkbmap ' + ' '.join(parameters))
            elif self.nox_keyboard_layouts == True:
                self.oe.dbg_log('system::set_keyboard_layout', unicode(self.struct['keyboard']['settings']['KeyboardLayout1']['value']), 1)
                parameter = self.struct['keyboard']['settings']['KeyboardLayout1']['value']
                command = 'loadkmap < `ls -1 %s/*/%s.bmap`' % (self.NOX_KEYBOARD_INFO, parameter)
                self.oe.dbg_log('system::set_keyboard_layout', command, 1)
                self.oe.execute(command)
            self.oe.dbg_log('system::set_keyboard_layout', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::set_keyboard_layout', 'ERROR: (' + repr(e) + ')')

    def set_hostname(self, listItem=None):
        try:
            self.oe.dbg_log('system::set_hostname', 'enter_function', 0)
            self.oe.set_busy(1)
            if not listItem == None:
                self.set_value(listItem)
            if not self.struct['ident']['settings']['hostname']['value'] is None and not self.struct['ident']['settings']['hostname']['value'] \
                == '':
                self.oe.dbg_log('system::set_hostname', self.struct['ident']['settings']['hostname']['value'], 1)
                hostname = open('/proc/sys/kernel/hostname', 'w')
                hostname.write(self.struct['ident']['settings']['hostname']['value'])
                hostname.close()
                hostname = open('%s/hostname' % self.oe.CONFIG_CACHE, 'w')
                hostname.write(self.struct['ident']['settings']['hostname']['value'])
                hostname.close()
                hosts = open('/etc/hosts', 'w')
                user_hosts_file = os.environ['HOME'] + '/.config/hosts.conf'
                if os.path.isfile(user_hosts_file):
                    user_hosts = open(user_hosts_file, 'r')
                    hosts.write(user_hosts.read())
                    user_hosts.close()
                hosts.write('127.0.0.1\tlocalhost %s\n' % self.struct['ident']['settings']['hostname']['value'])
                hosts.write('::1\tlocalhost ip6-localhost ip6-loopback %s\n' % self.struct['ident']['settings']['hostname']['value'])
                hosts.close()
            else:
                self.oe.dbg_log('system::set_hostname', 'is empty', 1)
            self.oe.set_busy(0)
            self.oe.dbg_log('system::set_hostname', 'exit_function', 0)
        except Exception, e:
            self.oe.set_busy(0)
            self.oe.dbg_log('system::set_hostname', 'ERROR: (' + repr(e) + ')')

    def set_auto_update(self, listItem=None):
        try:
            self.oe.dbg_log('system::set_auto_update', 'enter_function', 0)
            if not listItem == None:
                self.set_value(listItem)
            if not hasattr(self, 'update_disabled'):
                if not hasattr(self, 'update_thread'):
                    self.update_thread = updateThread(self.oe)
                    self.update_thread.start()
                else:
                    self.update_thread.wait_evt.set()
                self.oe.dbg_log('system::set_auto_update', unicode(self.struct['update']['settings']['AutoUpdate']['value']), 1)
            self.oe.dbg_log('system::set_auto_update', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::set_auto_update', 'ERROR: (' + repr(e) + ')')

    def get_keyboard_layouts(self):
        try:
            self.oe.dbg_log('system::get_keyboard_layouts', 'enter_function', 0)
            arrLayouts = []
            arrVariants = {}
            arrTypes = []
            if os.path.exists(self.KEYBOARD_INFO):
                objXmlFile = open(self.KEYBOARD_INFO, 'r')
                strXmlText = objXmlFile.read()
                objXmlFile.close()
                xml_conf = minidom.parseString(strXmlText)
                for xml_layout in xml_conf.getElementsByTagName('layout'):
                    for subnode_1 in xml_layout.childNodes:
                        if subnode_1.nodeName == 'configItem':
                            for subnode_2 in subnode_1.childNodes:
                                if subnode_2.nodeName == 'name':
                                    if hasattr(subnode_2.firstChild, 'nodeValue'):
                                        value = subnode_2.firstChild.nodeValue
                                if subnode_2.nodeName == 'description':
                                    if hasattr(subnode_2.firstChild, 'nodeValue'):
                                        arrLayouts.append(subnode_2.firstChild.nodeValue + ':' + value)
                        if subnode_1.nodeName == 'variantList':
                            arrVariants[value] = [':']
                            for subnode_vl in subnode_1.childNodes:
                                if subnode_vl.nodeName == 'variant':
                                    for subnode_v in subnode_vl.childNodes:
                                        if subnode_v.nodeName == 'configItem':
                                            for subnode_ci in subnode_v.childNodes:
                                                if subnode_ci.nodeName == 'name':
                                                    if hasattr(subnode_ci.firstChild, 'nodeValue'):
                                                        vvalue = subnode_ci.firstChild.nodeValue.replace(',', '')
                                                if subnode_ci.nodeName == 'description':
                                                    if hasattr(subnode_ci.firstChild, 'nodeValue'):
                                                        try:
                                                            arrVariants[value].append(subnode_ci.firstChild.nodeValue + ':' + vvalue)
                                                        except:
                                                            pass
                for xml_layout in xml_conf.getElementsByTagName('model'):
                    for subnode_1 in xml_layout.childNodes:
                        if subnode_1.nodeName == 'configItem':
                            for subnode_2 in subnode_1.childNodes:
                                if subnode_2.nodeName == 'name':
                                    if hasattr(subnode_2.firstChild, 'nodeValue'):
                                        value = subnode_2.firstChild.nodeValue
                                if subnode_2.nodeName == 'description':
                                    if hasattr(subnode_2.firstChild, 'nodeValue'):
                                        arrTypes.append(subnode_2.firstChild.nodeValue + ':' + value)
                arrLayouts.sort()
                arrTypes.sort()
            elif os.path.exists(self.NOX_KEYBOARD_INFO):
                for layout in glob.glob(self.NOX_KEYBOARD_INFO + '/*/*.bmap'):
                    if os.path.isfile(layout):
                        arrLayouts.append(layout.split('/')[-1].split('.')[0])
                arrLayouts.sort()
                arrTypes = None
            else:
                self.oe.dbg_log('system::get_keyboard_layouts', 'exit_function (no keyboard layouts found)', 0)
                return (None, None, None)
            self.oe.dbg_log('system::get_keyboard_layouts', 'exit_function', 0)
            return (
                arrLayouts,
                arrTypes,
                arrVariants,
                )
        except Exception, e:
            self.oe.dbg_log('system::get_keyboard_layouts', 'ERROR: (' + repr(e) + ')')

    def set_channel(self, listItem=None):
        try:
            self.oe.dbg_log('system::set_channel', 'enter_function', 0)
            if not listItem == None:
                self.set_value(listItem)
            self.struct['update']['settings']['Build']['values'] = self.get_available_builds()
            self.oe.dbg_log('system::set_channel', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::set_channel', 'ERROR: (' + repr(e) + ')')

    def set_custom_channel(self, listItem=None):
        try:
            self.oe.dbg_log('system::set_custom_channel', 'enter_function', 0)
            if not listItem == None:
                self.set_value(listItem)
            if listItem.getProperty('entry') != 'ShowCustomChannels':
                if self.get_json(listItem.getProperty('value')) is None:
                    xbmcDialog = xbmcgui.Dialog()
                    xbmcDialog.ok('LibreELEC Update', self.oe._(32191).encode('utf-8'))
                    xbmcDialog = None
                    del xbmcDialog
            self.update_json = self.build_json()
            self.struct['update']['settings']['Channel']['values'] = self.get_channels()
            if not self.struct['update']['settings']['Channel']['values'] is None:
                if not self.struct['update']['settings']['Channel']['value'] in self.struct['update']['settings']['Channel']['values']:
                    self.struct['update']['settings']['Channel']['value'] = None
            self.struct['update']['settings']['Build']['values'] = self.get_available_builds()
            self.oe.dbg_log('system::set_custom_channel', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::set_custom_channel', 'ERROR: (' + repr(e) + ')')

    def get_channels(self):
        try:
            self.oe.dbg_log('system::get_channels', 'enter_function', 0)
            channels = []
            self.oe.dbg_log('system::get_channels', unicode(self.update_json), 0)
            if not self.update_json is None:
                for channel in self.update_json:
                    channels.append(channel)
            self.oe.dbg_log('system::get_channels', 'exit_function', 0)
            return channels
        except Exception, e:
            self.oe.dbg_log('system::get_channels', 'ERROR: (' + repr(e) + ')')

    def do_manual_update(self, listItem=None):
        try:
            self.oe.dbg_log('system::do_manual_update', 'enter_function', 0)
            channel = self.struct['update']['settings']['Channel']['value']
            regex = re.compile(self.update_json[channel]['prettyname_regex'])
            longname = '-'.join([self.oe.DISTRIBUTION, self.oe.ARCHITECTURE, self.oe.VERSION])
            if regex.search(longname):
                version = regex.findall(longname)[0]
            else:
                version = self.oe.VERSION
            if not listItem == None:
                self.struct['update']['settings']['Build']['value'] = listItem.getProperty('value')
            if self.struct['update']['settings']['Build']['value'] != '':
                self.update_file = self.update_json[self.struct['update']['settings']['Channel']['value']]['url'] + self.get_available_builds(self.struct['update']['settings']['Build']['value'])
                xbmcDialog = xbmcgui.Dialog()
                answer = xbmcDialog.yesno('LibreELEC Update', self.oe._(32188).encode('utf-8') + ':  ' + version.encode('utf-8'),
                                      self.oe._(32187).encode('utf-8') + ':  ' + self.struct['update']['settings']['Build']['value'].encode('utf-8'),
                                      self.oe._(32180).encode('utf-8'))
                xbmcDialog = None
                del xbmcDialog
                if answer:
                    self.update_in_progress = True
                    self.do_autoupdate()
            self.struct['update']['settings']['Build']['value'] = ''
            self.oe.dbg_log('system::do_manual_update', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::do_manual_update', 'ERROR: (' + repr(e) + ')')

    def get_json(self, url=None):
        try:
            self.oe.dbg_log('system::get_json', 'enter_function', 0)
            if url is None:
                url = self.UPDATE_DOWNLOAD_URL % ('releases', 'releases.json')
            if url.split('/')[-1] != 'releases.json':
                url = url + '/releases.json'
            data = self.oe.load_url(url)
            if not data is None:
                update_json = json.loads(data)
            else:
                update_json = None
            self.oe.dbg_log('system::get_json', 'exit_function', 0)
            return update_json
        except Exception, e:
            self.oe.dbg_log('system::get_json', 'ERROR: (' + repr(e) + ')')

    def build_json(self):
        try:
            self.oe.dbg_log('system::build_json', 'enter_function', 0)
            update_json = self.get_json()
            if self.struct['update']['settings']['ShowCustomChannels']['value'] == '1':
                custom_urls = []
                for i in 1,2,3:
                    custom_urls.append(self.struct['update']['settings']['CustomChannel' + str(i)]['value'])
                for custom_url in custom_urls:
                    if custom_url != '':
                        custom_update_json = self.get_json(custom_url)
                        if not custom_update_json is None:
                            for channel in custom_update_json:
                                update_json[channel] = custom_update_json[channel]
            self.oe.dbg_log('system::build_json', 'exit_function', 0)
            return update_json
        except Exception, e:
            self.oe.dbg_log('system::build_json', 'ERROR: (' + repr(e) + ')')

    def get_available_builds(self, shortname=None):
        try:
            self.oe.dbg_log('system::get_available_builds', 'enter_function', 0)
            channel = self.struct['update']['settings']['Channel']['value']
            update_files = []
            build = None
            if not self.update_json is None:
                if channel != '':
                    if channel in self.update_json:
                        regex = re.compile(self.update_json[channel]['prettyname_regex'])
                        if self.oe.ARCHITECTURE in self.update_json[channel]['project']:
                            for i in sorted(self.update_json[channel]['project'][self.oe.ARCHITECTURE]['releases'], key=int, reverse=True):
                                if shortname is None:
                                    update_files.append(regex.findall(self.update_json[channel]['project'][self.oe.ARCHITECTURE]['releases'][i]['file']['name'])[0].strip('.tar'))
                                else:
                                    build = self.update_json[channel]['project'][self.oe.ARCHITECTURE]['releases'][i]['file']['name']
                                    if shortname in build:
                                        break
            self.oe.dbg_log('system::get_available_builds', 'exit_function', 0)
            if build is None:
                return update_files
            else:
                return build
        except Exception, e:
            self.oe.dbg_log('system::get_available_builds', 'ERROR: (' + repr(e) + ')')

    def check_updates_v2(self, force=False):
        try:
            self.oe.dbg_log('system::check_updates_v2', 'enter_function', 0)
            if hasattr(self, 'update_in_progress'):
                self.oe.dbg_log('system::check_updates_v2', 'Update in progress (exit)', 0)
                return
            url = '%s?i=%s&d=%s&pa=%s&v=%s&l=%s' % (
                self.UPDATE_REQUEST_URL,
                self.oe.SYSTEMID,
                self.oe.DISTRIBUTION,
                self.oe.ARCHITECTURE,
                self.oe.VERSION,
                self.cpu_lm_flag,
                )
            self.oe.dbg_log('system::check_updates_v2', 'URL: %s' % url, 0)
            update_json = self.oe.load_url(url)
            self.oe.dbg_log('system::check_updates_v2', 'RESULT: %s' % repr(update_json), 0)
            if update_json != '':
                update_json = json.loads(update_json)
                self.last_update_check = time.time()
                if 'update' in update_json['data'] and 'folder' in update_json['data']:
                    self.update_file = self.UPDATE_DOWNLOAD_URL % (update_json['data']['folder'], update_json['data']['update'])
                    if self.struct['update']['settings']['UpdateNotify']['value'] == '1':
                        self.oe.notify(self.oe._(32363).encode('utf-8'), self.oe._(32364).encode('utf-8'))
                    if self.struct['update']['settings']['AutoUpdate']['value'] == 'auto' and force == False:
                        self.update_in_progress = True
                        self.do_autoupdate(None, True)
            self.oe.dbg_log('system::check_updates_v2', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::check_updates_v2', 'ERROR: (' + repr(e) + ')')

    def do_autoupdate(self, listItem=None, silent=False):
        try:
            self.oe.dbg_log('system::do_autoupdate', 'enter_function', 0)
            if hasattr(self, 'update_file'):
                if not os.path.exists(self.LOCAL_UPDATE_DIR):
                    os.makedirs(self.LOCAL_UPDATE_DIR)
                downloaded = self.oe.download_file(self.update_file, self.oe.TEMP + 'update_file', silent)
                if not downloaded is None:
                    self.update_file = self.update_file.split('/')[-1]
                    if self.struct['update']['settings']['UpdateNotify']['value'] == '1':
                        self.oe.notify(self.oe._(32363), self.oe._(32366))
                    shutil.move(self.oe.TEMP + 'update_file', self.LOCAL_UPDATE_DIR + self.update_file)
                    subprocess.call('sync', shell=True, stdin=None, stdout=None, stderr=None)
                    if silent == False:
                        self.oe.winOeMain.close()
                        time.sleep(1)
                        xbmc.executebuiltin('Reboot')
                else:
                    delattr(self, 'update_in_progress')

            self.oe.dbg_log('system::do_autoupdate', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::do_autoupdate', 'ERROR: (' + repr(e) + ')')

    def set_hw_clock(self):
        try:
            self.oe.dbg_log('system::set_hw_clock', 'enter_function', 0)
            self.oe.execute(self.SET_CLOCK_CMD)
            self.oe.dbg_log('system::set_hw_clock', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::set_hw_clock', 'ERROR: (' + repr(e) + ')', 4)

    def reset_xbmc(self, listItem=None):
        try:
            self.oe.dbg_log('system::reset_xbmc', 'enter_function', 0)
            if self.ask_sure_reset('Soft') == 1:
                self.oe.set_busy(1)
                reset_file = open(self.XBMC_RESET_FILE, 'w')
                reset_file.write('reset')
                reset_file.close()
                self.oe.winOeMain.close()
                time.sleep(1)
                xbmc.executebuiltin('Reboot')
            self.oe.set_busy(0)
            self.oe.dbg_log('system::reset_xbmc', 'exit_function', 0)
        except Exception, e:
            self.oe.set_busy(0)
            self.oe.dbg_log('system::reset_xbmc', 'ERROR: (' + repr(e) + ')', 4)

    def reset_oe(self, listItem=None):
        try:
            self.oe.dbg_log('system::reset_oe', 'enter_function', 0)
            if self.ask_sure_reset('Hard') == 1:
                self.oe.set_busy(1)
                reset_file = open(self.LIBREELEC_RESET_FILE, 'w')
                reset_file.write('reset')
                reset_file.close()
                self.oe.winOeMain.close()
                time.sleep(1)
                xbmc.executebuiltin('Reboot')
                self.oe.set_busy(0)
            self.oe.dbg_log('system::reset_oe', 'exit_function', 0)
        except Exception, e:
            self.oe.set_busy(0)
            self.oe.dbg_log('system::reset_oe', 'ERROR: (' + repr(e) + ')', 4)

    def ask_sure_reset(self, part):
        try:
            self.oe.dbg_log('system::ask_sure_reset', 'enter_function', 0)
            xbmcDialog = xbmcgui.Dialog()
            answer = xbmcDialog.yesno(part + ' Reset', self.oe._(32326).encode('utf-8'), self.oe._(32328).encode('utf-8'))
            if answer == 1:
                if self.oe.reboot_counter(30, self.oe._(32323)) == 1:
                    return 1
                else:
                    return 0
            self.oe.dbg_log('system::ask_sure_reset', 'exit_function', 0)
        except Exception, e:
            self.oe.set_busy(0)
            self.oe.dbg_log('system::ask_sure_reset', 'ERROR: (' + repr(e) + ')', 4)

    def do_backup(self, listItem=None):
        try:
            self.oe.dbg_log('system::do_backup', 'enter_function', 0)
            self.total_backup_size = 1
            self.done_backup_size = 1

            try:
                self.oe.set_busy(1)
                for directory in self.BACKUP_DIRS:
                    self.get_folder_size(directory)
                self.oe.set_busy(0)
            except:
                self.oe.set_busy(0)

            xbmcDialog = xbmcgui.Dialog()
            bckDir = xbmcDialog.browse( 0, 
                                        self.oe._(32371).encode('utf-8'),
                                        'files', 
                                        '', 
                                        False, 
                                        False, 
                                        self.BACKUP_DESTINATION )

            if bckDir and os.path.exists(bckDir): 
                # free space check
                try:
                    folder_stat = os.statvfs(bckDir)
                    free_space = folder_stat.f_bsize * folder_stat.f_bavail
                    if self.total_backup_size > free_space:
                        txt = self.oe.split_dialog_text(self.oe._(32379).encode('utf-8'))
                        xbmcDialog = xbmcgui.Dialog()
                        answer = xbmcDialog.ok('Backup', txt[0], txt[1], txt[2])
                        return 0
                except:
                    pass
                    
                self.backup_dlg = xbmcgui.DialogProgress()
                self.backup_dlg.create('LibreELEC', self.oe._(32375).encode('utf-8'), ' ', ' ')
                if not os.path.exists(self.BACKUP_DESTINATION):
                    os.makedirs(self.BACKUP_DESTINATION)
                self.backup_file = self.oe.timestamp() + '.tar'
                tar = tarfile.open(bckDir + self.backup_file, 'w')
                for directory in self.BACKUP_DIRS:
                    self.tar_add_folder(tar, directory)
                tar.close()
                self.backup_dlg.close()
                del self.backup_dlg
            self.oe.dbg_log('system::do_backup', 'exit_function', 0)

        except Exception, e:
            self.backup_dlg.close()
            self.oe.dbg_log('system::do_backup', 'ERROR: (' + repr(e) + ')')

    def do_restore(self, listItem=None):
        try:
            self.oe.dbg_log('system::do_restore', 'enter_function', 0)
            copy_success = 0
            xbmcDialog = xbmcgui.Dialog()
            restore_file_path = xbmcDialog.browse( 1, 
                                              self.oe._(32373).encode('utf-8'),
                                              'files', 
                                              '??????????????.tar', 
                                              False, 
                                              False, 
                                              self.BACKUP_DESTINATION )
            
            restore_file_name = restore_file_path.split('/')[-1]
            
            if not os.path.exists(self.RESTORE_DIR):
                os.makedirs(self.RESTORE_DIR)
            else:
                self.oe.execute('rm -rf %s' % self.RESTORE_DIR)
                os.makedirs(self.RESTORE_DIR)
            folder_stat = os.statvfs(self.RESTORE_DIR)
            file_size = os.path.getsize(restore_file_path)
            free_space = folder_stat.f_bsize * folder_stat.f_bavail
            if free_space > file_size * 2:
                if os.path.exists(self.RESTORE_DIR + restore_file_name):
                    os.remove(self.RESTORE_DIR + restore_file_name)
                if self.oe.copy_file(restore_file_path, self.RESTORE_DIR + restore_file_name) != None:
                    copy_success = 1
                else:
                    self.oe.execute('rm -rf %s' % self.RESTORE_DIR)
            else:
                txt = self.oe.split_dialog_text(self.oe._(32379).encode('utf-8'))
                xbmcDialog = xbmcgui.Dialog()
                answer = xbmcDialog.ok('Restore', txt[0], txt[1], txt[2])
            if copy_success == 1:
                txt = self.oe.split_dialog_text(self.oe._(32380).encode('utf-8'))
                xbmcDialog = xbmcgui.Dialog()
                answer = xbmcDialog.yesno('Restore', txt[0], txt[1], txt[2])
                if answer == 1:
                    if self.oe.reboot_counter(10, self.oe._(32371)) == 1:
                        self.oe.winOeMain.close()
                        time.sleep(1)
                        xbmc.executebuiltin('Reboot')
                else:
                    self.oe.dbg_log('system::do_restore', 'User Abort!', 0)
                    self.oe.execute('rm -rf %s' % self.RESTORE_DIR)
            self.oe.dbg_log('system::do_restore', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::do_restore', 'ERROR: (' + repr(e) + ')')

    def cat_file(self, tmp, filen, description=None):
        if os.path.exists(filen):
            if description:
                self.oe.execute('echo "========== %s ==========" >> %s' % (description, tmp))
            else:
                self.oe.execute('echo "========== %s ==========" >> %s' % (filen, tmp))
            self.oe.execute('cat %s >> %s' % (filen, tmp))

    def do_send_system_logs(self, listItem=None):
        try:
            self.oe.dbg_log('system::do_send_system_logs', 'enter_function', 0)
            if self.oe.BOOT_STATUS == 'SAFE':
               self.do_send_logs('System', '/storage/.kodi.FAILED', 'kodi.log')
            else:
               self.do_send_logs('System', '/storage/.kodi', 'kodi.log')
            self.oe.dbg_log('system::do_send_system_logs', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::do_do_send_system_logs', 'ERROR: (' + repr(e) + ')')

    def do_send_crash_logs(self, listItem=None):
        try:
            self.oe.dbg_log('system::do_send_crash_logs', 'enter_function', 0)
            if self.oe.BOOT_STATUS == 'SAFE':
               self.do_send_logs('Crash', '/storage/.kodi.FAILED', 'kodi_crash.log')
            else:
               self.do_send_logs('Crash', '/storage/.kodi', 'kodi_crash.log')
            self.oe.dbg_log('system::do_send_crash_logs', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::do_do_send_crash_logs', 'ERROR: (' + repr(e) + ')')

    def do_send_logs(self, log_type, kodi_root, kodi_log):
        try:
            self.oe.dbg_log('system::do_send_logs', 'enter_function', 0)

            self.oe.execute('echo "%s log output for: $(lsb_release)" > /storage/.kodi/temp/paste.tmp' % log_type)

            if self.oe.ARCHITECTURE.endswith('.x86_64'):
                if os.path.exists('/sys/firmware/efi'):
                    self.oe.execute('echo "Firmware Boot Mode: EFI" >> /storage/.kodi/temp/paste.tmp')
                else:
                    self.oe.execute('echo "Firmware Boot Mode: BIOS" >> /storage/.kodi/temp/paste.tmp')

            self.cat_file('/storage/.kodi/temp/paste.tmp', '/flash/config.txt') # RPi
            self.cat_file('/storage/.kodi/temp/paste.tmp', '/flash/cmdline.txt') # RPi
            self.cat_file('/storage/.kodi/temp/paste.tmp', '/flash/syslinux.cfg') # x86 BIOS
            self.cat_file('/storage/.kodi/temp/paste.tmp', '/flash/EFI/BOOT/syslinux.cfg') # x86 EFI
            self.cat_file('/storage/.kodi/temp/paste.tmp', '/flash/extlinux.conf') # x86 legacy
            self.cat_file('/storage/.kodi/temp/paste.tmp', '/flash/extlinux/extlinux.conf') # u-boot
            self.cat_file('/storage/.kodi/temp/paste.tmp', '%s/temp/%s' % (kodi_root, kodi_log))
            self.oe.execute('journalctl -a > /storage/.kodi/temp/journalctl.txt')
            self.cat_file('/storage/.kodi/temp/paste.tmp', '/storage/.kodi/temp/journalctl.txt', 'journalctl -a')
            self.cat_file('/storage/.kodi/temp/paste.tmp', '%s/.smb/smb.conf' % kodi_root)
            self.cat_file('/storage/.kodi/temp/paste.tmp', '%s/.smb/user.conf' % kodi_root)
            self.cat_file('/storage/.kodi/temp/paste.tmp', '/run/samba/smb.conf')
            self.do_pastebin()
            os.remove('/storage/.kodi/temp/journalctl.txt')
            os.remove('/storage/.kodi/temp/paste.tmp')
            self.oe.dbg_log('system::do_send_logs', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::do_do_send_logs', 'ERROR: (' + repr(e) + ')')

    def do_pastebin(self):
        try:
            self.oe.dbg_log('system::do_pastebin', 'enter_function', 0)
            paste_dlg = xbmcgui.DialogProgress()
            paste_dlg.create('Pasting log files', 'Pasting...', ' ', ' ')
            result = self.oe.execute('PASTEUSR=libreelec PASTEPWD=libreelec paste /storage/.kodi/temp/paste.tmp', 1)
            if not paste_dlg.iscanceled():
                paste_dlg.close()
                link = result.find('http')
                done_dlg = xbmcgui.Dialog()
                if link > 0:
                    self.oe.dbg_log('system::do_pastebin', result[link:], 2)
                    done_dlg.ok('Paste complete', 'Log files pasted to ' + result[link:])
                else:
                    done_dlg.ok('Failed paste', 'Failed to paste log files, try again')
            self.oe.dbg_log('system::do_pastebin', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::do_pastebin', 'ERROR: (' + repr(e) + ')')

    def tar_add_folder(self, tar, folder):
        try:
            for item in os.listdir(folder):
                if item == self.backup_file:
                    continue
                if self.backup_dlg.iscanceled():
                    try:
                        os.remove(self.BACKUP_DESTINATION + self.backup_file)
                    except:
                        pass
                    return 0
                itempath = os.path.join(folder, item)
                if os.path.islink(itempath):
                    tar.add(itempath)
                elif os.path.ismount(itempath):
                    tar.add(itempath, recursive=False)
                elif os.path.isdir(itempath):
                    if os.listdir(itempath) == []:
                        tar.add(itempath)
                    else:
                        self.tar_add_folder(tar, itempath)
                else:
                    self.done_backup_size += os.path.getsize(itempath)
                    tar.add(itempath)
                    if hasattr(self, 'backup_dlg'):
                        progress = round(1.0 * self.done_backup_size / self.total_backup_size * 100)
                        self.backup_dlg.update(int(progress), folder, item)
        except Exception, e:
            self.backup_dlg.close()
            self.oe.dbg_log('system::tar_add_folder', 'ERROR: (' + repr(e) + ')')

    def get_folder_size(self, folder):
        for item in os.listdir(folder):
            itempath = os.path.join(folder, item)
            if os.path.isfile(itempath):
                self.total_backup_size += os.path.getsize(itempath)
            elif os.path.ismount(itempath):
                continue
            elif os.path.isdir(itempath):
                self.get_folder_size(itempath)

    def do_wizard(self):
        try:
            self.oe.dbg_log('system::do_wizard', 'enter_function', 0)
            self.oe.winOeMain.set_wizard_title(self.oe._(32003))
            self.oe.winOeMain.set_wizard_text(self.oe._(32304))
            self.oe.winOeMain.set_wizard_button_title(self.oe._(32308))
            self.oe.winOeMain.set_wizard_button_1(self.struct['ident']['settings']['hostname']['value'], self, 'wizard_set_hostname')
            self.oe.dbg_log('system::do_wizard', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::do_wizard', 'ERROR: (' + repr(e) + ')')

    def wizard_set_hostname(self):
        try:
            self.oe.dbg_log('system::wizard_set_hostname', 'enter_function', 0)
            currentHostname = self.struct['ident']['settings']['hostname']['value']
            xbmcKeyboard = xbmc.Keyboard(currentHostname)
            result_is_valid = False
            while not result_is_valid:
                xbmcKeyboard.doModal()
                if xbmcKeyboard.isConfirmed():
                    result_is_valid = True
                    validate_string = self.struct['ident']['settings']['hostname']['validate']
                    if validate_string != '':
                        if not re.search(validate_string, xbmcKeyboard.getText()):
                            result_is_valid = False
                else:
                    result_is_valid = True
            if xbmcKeyboard.isConfirmed():
                self.struct['ident']['settings']['hostname']['value'] = xbmcKeyboard.getText()
                self.set_hostname()
                self.oe.winOeMain.getControl(1401).setLabel(self.struct['ident']['settings']['hostname']['value'])
                self.oe.write_setting('system', 'hostname', self.struct['ident']['settings']['hostname']['value'])
            self.oe.dbg_log('system::wizard_set_hostname', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::wizard_set_hostname', 'ERROR: (' + repr(e) + ')')


class updateThread(threading.Thread):

    def __init__(self, oeMain):
        try:
            oeMain.dbg_log('system::updateThread::__init__', 'enter_function', 0)
            self.oe = oeMain
            self.stopped = False
            self.wait_evt = threading.Event()
            threading.Thread.__init__(self)
            self.oe.dbg_log('system::updateThread', 'Started', 1)
            self.oe.dbg_log('system::updateThread::__init__', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::updateThread::__init__', 'ERROR: (' + repr(e) + ')')

    def stop(self):
        try:
            self.oe.dbg_log('system::updateThread::stop()', 'enter_function', 0)
            self.stopped = True
            self.wait_evt.set()
            self.oe.dbg_log('system::updateThread::stop()', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::updateThread::stop()', 'ERROR: (' + repr(e) + ')')

    def run(self):
        try:
            self.oe.dbg_log('system::updateThread::run', 'enter_function', 0)
            while self.stopped == False:
                if not xbmc.Player().isPlaying():
                    self.oe.dictModules['system'].check_updates_v2()
                if not hasattr(self.oe.dictModules['system'], 'update_in_progress'):
                    self.wait_evt.wait(21600)
                else:
                    self.oe.notify(self.oe._(32363).encode('utf-8'), self.oe._(32364).encode('utf-8'))
                    self.wait_evt.wait(3600)
                self.wait_evt.clear()
            self.oe.dbg_log('system::updateThread', 'Stopped', 1)
            self.oe.dbg_log('system::updateThread::run', 'exit_function', 0)
        except Exception, e:
            self.oe.dbg_log('system::updateThread::run', 'ERROR: (' + repr(e) + ')')


