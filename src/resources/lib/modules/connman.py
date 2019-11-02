# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
# Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)
# Copyright (C) 2017-present Team LibreELEC

import os
import xbmc
import time
import dbus
import dbus.service
import uuid
import xbmcgui
import threading
import oeWindows
import ConfigParser
import random
import string


####################################################################
## Connection properties class
####################################################################

class connmanService(object):

    menu = {}

    def __init__(self, servicePath, oeMain):
        try:
            oeMain.dbg_log('connmanService::__init__', 'enter_function', 0)
            oeMain.set_busy(1)
            self.struct = {
                'AutoConnect': {
                    'order': 1,
                    'name': 32110,
                    'type': 'Boolean',
                    'menuLoader': 'menu_network_configuration',
                    'settings': {'AutoConnect': {
                        'order': 1,
                        'name': 32109,
                        'value': '',
                        'type': 'bool',
                        'dbus': 'Boolean',
                        'action': 'set_value',
                        }},
                    },
                'IPv4': {
                    'order': 2,
                    'name': 32111,
                    'type': 'Dictionary',
                    'settings': {
                        'Method': {
                            'order': 1,
                            'name': 32113,
                            'value': '',
                            'type': 'multivalue',
                            'dbus': 'String',
                            'values': [
                                'dhcp',
                                'manual',
                                'off',
                                ],
                            'action': 'set_value',
                            },
                        'Address': {
                            'order': 2,
                            'name': 32114,
                            'value': '',
                            'type': 'ip',
                            'dbus': 'String',
                            'parent': {
                                'entry': 'Method',
                                'value': ['manual'],
                                },
                            'action': 'set_value',
                            },
                        'Netmask': {
                            'order': 3,
                            'name': 32115,
                            'value': '',
                            'type': 'ip',
                            'dbus': 'String',
                            'parent': {
                                'entry': 'Method',
                                'value': ['manual'],
                                },
                            'action': 'set_value',
                            },
                        'Gateway': {
                            'order': 4,
                            'name': 32116,
                            'value': '',
                            'type': 'ip',
                            'dbus': 'String',
                            'parent': {
                                'entry': 'Method',
                                'value': ['manual'],
                                },
                            'action': 'set_value',
                            },
                        },
                    },
                'IPv6': {
                    'order': 3,
                    'name': 32112,
                    'type': 'Dictionary',
                    'settings': {
                        'Method': {
                            'order': 1,
                            'name': 32113,
                            'value': '',
                            'type': 'multivalue',
                            'dbus': 'String',
                            'values': [
                                'auto',
                                'manual',
                                '6to4',
                                'off',
                                ],
                            'action': 'set_value',
                            },
                        'Address': {
                            'order': 2,
                            'name': 32114,
                            'value': '',
                            'type': 'text',
                            'dbus': 'String',
                            'parent': {
                                'entry': 'Method',
                                'value': ['manual'],
                                },
                            'action': 'set_value',
                            },
                        'PrefixLength': {
                            'order': 4,
                            'name': 32117,
                            'value': '',
                            'type': 'text',
                            'dbus': 'Byte',
                            'parent': {
                                'entry': 'Method',
                                'value': ['manual'],
                                },
                            'action': 'set_value',
                            },
                        'Gateway': {
                            'order': 3,
                            'name': 32116,
                            'value': '',
                            'type': 'text',
                            'dbus': 'String',
                            'parent': {
                                'entry': 'Method',
                                'value': ['manual'],
                                },
                            'action': 'set_value',
                            },
                        'Privacy': {
                            'order': 5,
                            'name': 32118,
                            'value': '',
                            'type': 'multivalue',
                            'dbus': 'String',
                            'parent': {
                                'entry': 'Method',
                                'value': ['manual'],
                                },
                            'values': [
                                'disabled',
                                'enabled',
                                'prefered',
                                ],
                            'action': 'set_value',
                            },
                        },
                    },
                'Nameservers': {
                    'order': 4,
                    'name': 32119,
                    'type': 'Array',
                    'settings': {
                        '0': {
                            'order': 1,
                            'name': 32120,
                            'value': '',
                            'type': 'ip',
                            'dbus': 'String',
                            'action': 'set_value_checkdhcp',
                            },
                        '1': {
                            'order': 2,
                            'name': 32121,
                            'value': '',
                            'type': 'ip',
                            'dbus': 'String',
                            'action': 'set_value_checkdhcp',
                            },
                        '2': {
                            'order': 3,
                            'name': 32122,
                            'value': '',
                            'type': 'ip',
                            'dbus': 'String',
                            'action': 'set_value_checkdhcp',
                            },
                        },
                    },
                'Timeservers': {
                    'order': 6,
                    'name': 32123,
                    'type': 'Array',
                    'settings': {
                        '0': {
                            'order': 1,
                            'name': 32124,
                            'value': '',
                            'type': 'text',
                            'dbus': 'String',
                            'action': 'set_value_checkdhcp',
                            },
                        '1': {
                            'order': 2,
                            'name': 32125,
                            'value': '',
                            'type': 'text',
                            'dbus': 'String',
                            'action': 'set_value_checkdhcp',
                            },
                        '2': {
                            'order': 3,
                            'name': 32126,
                            'value': '',
                            'type': 'text',
                            'dbus': 'String',
                            'action': 'set_value_checkdhcp',
                            },
                        },
                    },
                'Domains': {
                    'order': 5,
                    'name': 32127,
                    'type': 'Array',
                    'settings': {
                        '0': {
                            'order': 1,
                            'name': 32128,
                            'value': '',
                            'type': 'text',
                            'dbus': 'String',
                            'action': 'set_value_checkdhcp',
                            },
                        '1': {
                            'order': 2,
                            'name': 32129,
                            'value': '',
                            'type': 'text',
                            'dbus': 'String',
                            'action': 'set_value_checkdhcp',
                            },
                        '2': {
                            'order': 3,
                            'name': 32130,
                            'value': '',
                            'type': 'text',
                            'dbus': 'String',
                            'action': 'set_value_checkdhcp',
                            },
                        },
                    },
                }

            self.datamap = {
                0: {'AutoConnect': 'AutoConnect'},
                1: {'IPv4': 'IPv4'},
                2: {'IPv4.Configuration': 'IPv4'},
                3: {'IPv6': 'IPv6'},
                4: {'IPv6.Configuration': 'IPv6'},
                5: {'Nameservers': 'Nameservers'},
                6: {'Nameservers.Configuration': 'Nameservers'},
                7: {'Domains': 'Domains'},
                8: {'Domains.Configuration': 'Domains'},
                9: {'Timeservers': 'Timeservers'},
                10: {'Timeservers.Configuration': 'Timeservers'},
                }
            self.oe = oeMain
            self.winOeCon = oeWindows.mainWindow('service-LibreELEC-Settings-mainWindow.xml', self.oe.__cwd__, 'Default', oeMain=oeMain, isChild=True)
            self.servicePath = servicePath
            self.oe.dictModules['connmanNetworkConfig'] = self
            self.service = dbus.Interface(self.oe.dbusSystemBus.get_object('net.connman', servicePath), 'net.connman.Service')
            self.service_properties = self.service.GetProperties()
            for entry in sorted(self.datamap):
                for (key, value) in self.datamap[entry].iteritems():
                    if self.struct[value]['type'] == 'Boolean':
                        if key in self.service_properties:
                            self.struct[value]['settings'][value]['value'] = self.service_properties[key]
                    if self.struct[value]['type'] == 'Dictionary':
                        if key in self.service_properties:
                            for setting in self.struct[value]['settings']:
                                if setting in self.service_properties[key]:
                                    self.struct[value]['settings'][setting]['value'] = self.service_properties[key][setting]
                    if self.struct[value]['type'] == 'Array':
                        if key in self.service_properties:
                            for setting in self.struct[value]['settings']:
                                if int(setting) < len(self.service_properties[key]):
                                    self.struct[value]['settings'][setting]['value'] = self.service_properties[key][int(setting)]
            self.winOeCon.show()
            for strEntry in sorted(self.struct, key=lambda x: self.struct[x]['order']):
                dictProperties = {
                    'modul': 'connmanNetworkConfig',
                    'listTyp': self.oe.listObject['list'],
                    'menuLoader': 'menu_loader',
                    'category': strEntry,
                    }
                self.winOeCon.addMenuItem(self.struct[strEntry]['name'], dictProperties)
            self.oe.set_busy(0)
            self.winOeCon.doModal()
            del self.winOeCon
            del self.oe.dictModules['connmanNetworkConfig']
            self.oe.dbg_log('connmanService::__init__', 'exit_function', 0)
        except Exception as e:
            self.oe.set_busy(0)
            self.oe.dbg_log('connmanService::__init__', 'ERROR: (' + repr(e) + ')', 4)

    def cancel(self):
        try:
            self.oe.dbg_log('connmanService::cancel', 'exit_function', 0)
            self.oe.set_busy(1)
            self.winOeCon.close()
            self.oe.set_busy(0)
            self.oe.dbg_log('connmanService::cancel', 'exit_function', 0)
        except Exception as e:
            self.oe.set_busy(0)
            self.oe.dbg_log('connmanService::cancel', 'ERROR: (' + repr(e) + ')', 4)

    def menu_loader(self, menuItem):
        try:
            self.oe.dbg_log('connmanService::menu_loader', 'enter_function', 0)
            self.winOeCon.showButton(1, 32140, 'connmanNetworkConfig', 'save_network')
            self.winOeCon.showButton(2, 32212, 'connmanNetworkConfig', 'cancel')
            self.winOeCon.build_menu(self.struct, fltr=[menuItem.getProperty('category')])
            self.oe.dbg_log('connmanService::menu_loader', 'exit_function', 0)
        except Exception as e:
            self.oe.dbg_log('connmanService::menu_loader', 'ERROR: (' + repr(e) + ')', 4)

    def set_value_checkdhcp(self, listItem):
        try:
            if self.struct['IPv4']['settings']['Method']['value'] == 'dhcp':
                ok_window = xbmcgui.Dialog()
                answer = ok_window.ok('Not allowed', 'IPv4 method is set to dhcp','changing this option is not allowed')
                return
            self.oe.dbg_log('connmanService::set_value_checkdhcp', 'enter_function', 0)
            self.struct[listItem.getProperty('category')]['settings'][listItem.getProperty('entry')]['value'] = listItem.getProperty('value')
            self.struct[listItem.getProperty('category')]['settings'][listItem.getProperty('entry')]['changed'] = True
            self.oe.dbg_log('connmanService::set_value_checkdhcp', 'exit_function', 0)
        except Exception as e:
            self.oe.dbg_log('connmanService::set_value_checkdhcp', 'ERROR: (' + repr(e) + ')', 4)

    def set_value(self, listItem):
        try:
            self.oe.dbg_log('connmanService::set_value', 'enter_function', 0)
            self.struct[listItem.getProperty('category')]['settings'][listItem.getProperty('entry')]['value'] = listItem.getProperty('value')
            self.struct[listItem.getProperty('category')]['settings'][listItem.getProperty('entry')]['changed'] = True
            self.oe.dbg_log('connmanService::set_value', 'exit_function', 0)
        except Exception as e:
            self.oe.dbg_log('connmanService::set_value', 'ERROR: (' + repr(e) + ')', 4)

    def dbus_config(self, category):
        try:
            value = None
            postfix = ''
            if self.struct[category]['type'] == 'Dictionary':
                value = {}
                postfix = '.Configuration'
            elif self.struct[category]['type'] == 'Array':
                value = dbus.Array([], signature=dbus.Signature('s'), variant_level=1)
                postfix = '.Configuration'
            for entry in sorted(self.struct[category]['settings'], key=lambda x: self.struct[category]['settings'][x]['order']):
                setting = self.struct[category]['settings'][entry]
                if (setting['value'] != '' or hasattr(setting, 'changed')) and not 'parent' in setting or 'parent' in setting \
                    and self.struct[category]['settings'][setting['parent']['entry']]['value'] in setting['parent']['value']:
                    if setting['dbus'] == 'Array':
                        value = dbus.Array(dbus.String(setting['value'], variant_level=1).split(','), signature=dbus.Signature('s'),
                                           variant_level=1)
                    else:
                        if self.struct[category]['type'] == 'Boolean':
                            if setting['value'] == '1' or setting['value'] == dbus.Boolean(True, variant_level=1):
                                setting['value'] = True
                            else:
                                setting['value'] = False
                            value = getattr(dbus, setting['dbus'])(setting['value'], variant_level=1)
                        elif self.struct[category]['type'] == 'Dictionary':
                            value[entry] = getattr(dbus, setting['dbus'])(setting['value'], variant_level=1)
                        elif self.struct[category]['type'] == 'Array':
                            value.append(getattr(dbus, setting['dbus'])(setting['value'], variant_level=1))
            return (category + postfix, value)
        except Exception as e:
            self.oe.dbg_log('connmanService::dbus_config', 'ERROR: (' + repr(e) + ')', 4)

    def save_network(self):
        try:
            self.oe.set_busy(1)
            self.oe.dbg_log('connmanService::save_network', 'enter_function', 0)
            if self.struct['IPv4']['settings']['Method']['value'] == 'dhcp':
                for setting in self.struct['Nameservers']['settings']:
                    self.struct['Nameservers']['settings'][setting]['changed'] = True
                    self.struct['Nameservers']['settings'][setting]['value'] = ''
                for setting in self.struct['Timeservers']['settings']:
                    self.struct['Timeservers']['settings'][setting]['changed'] = True
                    self.struct['Timeservers']['settings'][setting]['value'] = ''
                for setting in self.struct['Domains']['settings']:
                    self.struct['Domains']['settings'][setting]['changed'] = True
                    self.struct['Domains']['settings'][setting]['value'] = ''
            for category in [
                'AutoConnect',
                'IPv4',
                'IPv6',
                'Nameservers',
                'Timeservers',
                'Domains',
                ]:
                (category, value) = self.dbus_config(category)
                if value != None:
                    self.service.SetProperty(dbus.String(category), value)
            self.oe.dbg_log('connmanService::save_network', 'exit_function', 0)
            self.oe.set_busy(0)
            return 'close'
        except Exception as e:
            self.oe.set_busy(0)
            self.oe.dbg_log('connmanService::save_network', 'ERROR: (' + repr(e) + ')', 4)
            return 'close'

    def delete_network(self):
        try:
            self.oe.dbg_log('connmanService::delete_network', 'enter_function', 0)
            self.oe.dictModules['connman'].delete_network(None)
            self.oe.dbg_log('connmanService::delete_network', 'exit_function', 0)
            return 'close'
        except Exception as e:
            self.oe.dbg_log('connmanService::delete_network', 'ERROR: (' + repr(e) + ')', 4)
            return 'close'

    def connect_network(self):
        try:
            self.oe.dbg_log('connmanService::connect_network', 'enter_function', 0)
            self.oe.dictModules['connman'].connect_network(None)
            self.oe.dbg_log('connmanService::connect_network', 'exit_function', 0)
            return 'close'
        except Exception as e:
            self.oe.dbg_log('connmanService::connect_network', 'ERROR: (' + repr(e) + ')', 4)
            return 'close'

    def disconnect_network(self):
        try:
            self.oe.dbg_log('connmanService::disconnect_network', 'enter_function', 0)
            self.oe.dictModules['connman'].disconnect_network(None)
            self.oe.dbg_log('connmanService::disconnect_network', 'exit_function', 0)
            return 'close'
        except Exception as e:
            self.oe.dbg_log('connmanService::disconnect_network', 'ERROR: (' + repr(e) + ')', 4)
            return 'close'


####################################################################
## Connman main class
####################################################################

class connman:

    ENABLED = False
    CONNMAN_DAEMON = None
    WAIT_CONF_FILE = None
    NF_CUSTOM_PATH = "/storage/.config/iptables/"
    connect_attempt = 0
    log_error = 1
    net_disconnected = 0
    notify_error = 1
    menu = {
        '3': {
            'name': 32101,
            'menuLoader': 'menu_loader',
            'listTyp': 'list',
            'InfoText': 701,
            },
        '4': {
            'name': 32100,
            'menuLoader': 'menu_connections',
            'listTyp': 'netlist',
            'InfoText': 702,
            },
        }

    def __init__(self, oeMain):
        try:
            oeMain.dbg_log('connman::__init__', 'enter_function', 0)
            self.listItems = {}
            self.struct = {
                '/net/connman/technology/wifi': {
                    'hidden': 'true',
                    'order': 1,
                    'name': 32102,
                    'dbus': 'Dictionary',
                    'settings': {
                        'Powered': {
                            'order': 1,
                            'name': 32105,
                            'value': '',
                            'action': 'set_technologie',
                            'type': 'bool',
                            'dbus': 'Boolean',
                            'InfoText': 726,
                            },
                        'Tethering': {
                            'order': 2,
                            'name': 32108,
                            'value': '',
                            'action': 'set_technologie',
                            'type': 'bool',
                            'dbus': 'Boolean',
                            'parent': {
                                'entry': 'Powered',
                                'value': ['1'],
                                },
                            'InfoText': 727,
                            },
                        'TetheringIdentifier': {
                            'order': 3,
                            'name': 32198,
                            'value': 'LibreELEC-AP',
                            'action': 'set_technologie',
                            'type': 'text',
                            'dbus': 'String',
                            'parent': {
                                'entry': 'Tethering',
                                'value': ['1'],
                                },
                            'validate': '^([a-zA-Z0-9](?:[a-zA-Z0-9-\.]*[a-zA-Z0-9]))$',
                            'InfoText': 728,
                            },
                        'TetheringPassphrase': {
                            'order': 4,
                            'name': 32107,
                            'value': ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(10)),
                            'action': 'set_technologie',
                            'type': 'text',
                            'dbus': 'String',
                            'parent': {
                                'entry': 'Tethering',
                                'value': ['1'],
                                },
                            'validate': '^[\\x00-\\x7F]{8,64}$',
                            'InfoText': 729,
                            },
                        },
                    'order': 0,
                    },
                '/net/connman/technology/ethernet': {
                    'hidden': 'true',
                    'order': 2,
                    'name': 32103,
                    'dbus': 'Dictionary',
                    'settings': {'Powered': {
                        'order': 1,
                        'name': 32105,
                        'value': '',
                        'action': 'set_technologie',
                        'type': 'bool',
                        'dbus': 'Boolean',
                        'InfoText': 730,
                        }},
                    'order': 1,
                    },
                'Timeservers': {
                    'order': 4,
                    'name': 32123,
                    'dbus': 'Array',
                    'settings': {
                        '0': {
                            'order': 1,
                            'name': 32124,
                            'value': '',
                            'action': 'set_timeservers',
                            'type': 'text',
                            'dbus': 'String',
                            'validate': '^([a-zA-Z0-9](?:[a-zA-Z0-9-\.]*[a-zA-Z0-9]))$|^$',
                            'InfoText': 732,
                            },
                        '1': {
                            'order': 2,
                            'name': 32125,
                            'value': '',
                            'action': 'set_timeservers',
                            'type': 'text',
                            'dbus': 'String',
                            'validate': '^([a-zA-Z0-9](?:[a-zA-Z0-9-\.]*[a-zA-Z0-9]))$|^$',
                            'InfoText': 733,
                            },
                        '2': {
                            'order': 3,
                            'name': 32126,
                            'value': '',
                            'action': 'set_timeservers',
                            'type': 'text',
                            'dbus': 'String',
                            'validate': '^([a-zA-Z0-9](?:[a-zA-Z0-9-\.]*[a-zA-Z0-9]))$|^$',
                            'InfoText': 734,
                            },
                        },
                    'order': 2,
                    },
                'advanced': {
                    'order': 6,
                    'name': 32368,
                    'settings': {
                        'wait_for_network': {
                            'order': 1,
                            'name': 32369,
                            'value': '0',
                            'action': 'set_network_wait',
                            'type': 'bool',
                            'InfoText': 736,
                            },
                        'wait_for_network_time': {
                            'order': 2,
                            'name': 32370,
                            'value': '10',
                            'action': 'set_network_wait',
                            'type': 'num',
                            'parent': {
                                'entry': 'wait_for_network',
                                'value': ['1'],
                                },
                            'InfoText': 737,
                            },
                        'netfilter': {
                            'order': 3,
                            'name': 32395,
                            'type': 'multivalue',
                            'values': [],
                            'action': 'init_netfilter',
                            'InfoText': 771,
                            },
                        },
                    'order': 4,
                    },
                }

            self.busy = 0
            self.oe = oeMain
            self.visible = False
            self.oe.dbg_log('connman::__init__', 'exit_function', 0)
        except Exception as e:
            self.oe.dbg_log('connman::__init__', 'ERROR: (' + repr(e) + ')', 4)

    def clear_list(self):
        try:
            remove = [entry for entry in self.listItems]
            for entry in remove:
                self.listItems[entry] = None
                del self.listItems[entry]
        except Exception as e:
            self.oe.dbg_log('connman::clear_list', 'ERROR: (' + repr(e) + ')', 4)

    def do_init(self):
        try:
            self.oe.dbg_log('connman::do_init', 'enter_function', 0)
            self.visible = True
            self.oe.dbg_log('connman::do_init', 'exit_function', 0)
        except Exception as e:
            self.oe.dbg_log('connman::do_init', 'ERROR: (' + repr(e) + ')', 4)

    def exit(self):
        try:
            self.oe.dbg_log('connman::exit', 'enter_function', 0)
            self.visible = False
            self.clear_list()
            self.oe.dbg_log('connman::exit', 'exit_function', 0)
        except Exception as e:
            self.oe.dbg_log('connman::exit', 'ERROR: (' + repr(e) + ')', 4)

    def load_values(self):
        try:
            self.oe.dbg_log('connman::load_values', 'enter_function', 0)

            # Network Wait

            self.struct['advanced']['settings']['wait_for_network']['value'] = '0'
            self.struct['advanced']['settings']['wait_for_network_time']['value'] = '10'
            if os.path.exists(self.WAIT_CONF_FILE):
                wait_file = open(self.WAIT_CONF_FILE, 'r')
                for line in wait_file:
                    if 'WAIT_NETWORK=' in line:
                        if line.split('=')[-1].lower().strip().replace('"', '') == 'true':
                            self.struct['advanced']['settings']['wait_for_network']['value'] = '1'
                        else:
                            self.struct['advanced']['settings']['wait_for_network']['value'] = '0'
                    if 'WAIT_NETWORK_TIME=' in line:
                        self.struct['advanced']['settings']['wait_for_network_time']['value'] = line.split('=')[-1].lower().strip().replace('"',
                                '')
                wait_file.close()
            # IPTABLES
            nf_values = [self.oe._(32397), self.oe._(32398), self.oe._(32399)]
            nf_custom_rules = [self.NF_CUSTOM_PATH + "rules.v4" , self.NF_CUSTOM_PATH + "rules.v6"]
            for custom_rule in nf_custom_rules:
                if os.path.exists(custom_rule):
                    nf_values.append(self.oe._(32396))
                    break
            self.struct['advanced']['settings']['netfilter']['values'] = nf_values
            if self.oe.get_service_state('iptables') == '1':
                nf_option = self.oe.get_service_option('iptables', 'RULES', 'home')
                if nf_option == "custom":
                    nf_option_str = self.oe._(32396)
                elif nf_option == "home":
                    nf_option_str = self.oe._(32398)
                elif nf_option == "public":
                    nf_option_str = self.oe._(32399)
            else:
                nf_option_str = self.oe._(32397)
            self.struct['advanced']['settings']['netfilter']['value'] = nf_option_str

            self.oe.dbg_log('connman::load_values', 'exit_function', 0)
        except Exception as e:
            self.oe.dbg_log('connman::load_values', 'ERROR: (' + repr(e) + ')')

    def menu_connections(self, focusItem, services={}, removed={}, force=False):
        try:
            self.oe.dbg_log('connman::menu_connections', 'enter_function', 0)
            self.oe.set_busy(1)

            # type 1=int, 2=string, 3=array

            properties = {
                0: {
                    'flag': 0,
                    'type': 2,
                    'values': ['State'],
                    },
                1: {
                    'flag': 0,
                    'type': 1,
                    'values': ['Strength'],
                    },
                2: {
                    'flag': 0,
                    'type': 1,
                    'values': ['Favorite'],
                    },
                3: {
                    'flag': 0,
                    'type': 3,
                    'values': ['Security'],
                    },
                4: {
                    'flag': 0,
                    'type': 2,
                    'values': ['IPv4', 'Method'],
                    },
                5: {
                    'flag': 0,
                    'type': 2,
                    'values': ['IPv4', 'Address'],
                    },
                6: {
                    'flag': 0,
                    'type': 2,
                    'values': ['IPv4.Configuration', 'Method'],
                    },
                7: {
                    'flag': 0,
                    'type': 2,
                    'values': ['IPv4.Configuration', 'Address'],
                    },
                8: {
                    'flag': 0,
                    'type': 2,
                    'values': ['Ethernet', 'Interface'],
                    },
                }

            dbusConnmanManager = dbus.Interface(self.oe.dbusSystemBus.get_object('net.connman', '/'), 'net.connman.Manager')
            dbusServices = dbusConnmanManager.GetServices()
            dbusConnmanManager = None
            rebuildList = 0
            if len(dbusServices) != len(self.listItems) or force:
                rebuildList = 1
                self.oe.winOeMain.getControl(int(self.oe.listObject['netlist'])).reset()
            else:
                for (dbusServicePath, dbusServiceValues) in dbusServices:
                    if dbusServicePath not in self.listItems:
                        rebuildList = 1
                        self.oe.winOeMain.getControl(int(self.oe.listObject['netlist'])).reset()
                        break
            for (dbusServicePath, dbusServiceProperties) in dbusServices:
                dictProperties = {}
                if rebuildList == 1:
                    if 'Name' in dbusServiceProperties:
                        apName = dbusServiceProperties['Name']
                    else:
                        if 'Security' in dbusServiceProperties:
                            apName = self.oe._(32208) + ' (' + unicode(dbusServiceProperties['Security'][0]) + ')'
                        else:
                            apName = ''
                    if apName != '':
                        dictProperties['entry'] = dbusServicePath
                        dictProperties['modul'] = self.__class__.__name__
                        if 'Type' in dbusServiceProperties:
                            dictProperties['netType'] = dbusServiceProperties['Type']
                            dictProperties['action'] = 'open_context_menu'
                for prop in properties:
                    result = dbusServiceProperties
                    for value in properties[prop]['values']:
                        if value in result:
                            result = result[value]
                            properties[prop]['flag'] = 1
                        else:
                            properties[prop]['flag'] = 0
                    if properties[prop]['flag'] == 1:
                        if properties[prop]['type'] == 1:
                            result = unicode(int(result))
                        if properties[prop]['type'] == 2:
                            result = unicode(result)
                        if properties[prop]['type'] == 3:
                            if any(x in result for x in ['psk','ieee8021x','wep']):
                                result = unicode('1')
                            elif 'none' in result:
                                result = unicode('0')
                            else:
                                result = unicode('-1')
                        if rebuildList == 1:
                            dictProperties[value] = result
                        else:
                            if self.listItems[dbusServicePath] != None:
                                self.listItems[dbusServicePath].setProperty(value, result)
                if rebuildList == 1:
                    self.listItems[dbusServicePath] = self.oe.winOeMain.addConfigItem(apName, dictProperties, self.oe.listObject['netlist'])
            self.oe.set_busy(0)
            self.oe.dbg_log('connman::menu_connections', 'exit_function', 0)
        except Exception as e:
            self.oe.set_busy(0)
            self.oe.dbg_log('connman::menu_connections', 'ERROR: (' + repr(e) + ')', 4)

    def menu_loader(self, menuItem=None):
        try:
            self.oe.dbg_log('connman::menu_loader', 'enter_function0', 0)
            self.oe.set_busy(1)
            if menuItem == None:
                menuItem = self.oe.winOeMain.getControl(self.oe.winOeMain.guiMenList).getSelectedItem()
            dbusConnmanManager = dbus.Interface(self.oe.dbusSystemBus.get_object('net.connman', '/'), 'net.connman.Manager')
            self.technologie_properties = dbusConnmanManager.GetTechnologies()
            dbusConnmanManager = None
            self.clock = dbus.Interface(self.oe.dbusSystemBus.get_object('net.connman', '/'), 'net.connman.Clock')
            self.clock_properties = self.clock.GetProperties()
            self.struct['/net/connman/technology/wifi']['hidden'] = 'true'
            self.struct['/net/connman/technology/ethernet']['hidden'] = 'true'
            for (path, technologie) in self.technologie_properties:
                if path in self.struct:
                    if 'hidden' in self.struct[path]:
                        del self.struct[path]['hidden']
                    for entry in self.struct[path]['settings']:
                        if entry in technologie:
                            self.struct[path]['settings'][entry]['value'] = unicode(technologie[entry])
            for setting in self.struct['Timeservers']['settings']:
                if 'Timeservers' in self.clock_properties:
                    if int(setting) < len(self.clock_properties['Timeservers']):
                        self.struct['Timeservers']['settings'][setting]['value'] = self.clock_properties['Timeservers'][int(setting)]
                else:
                    self.struct['Timeservers']['settings'][setting]['value'] = ''
            self.oe.winOeMain.build_menu(self.struct)
            self.oe.set_busy(0)
            self.oe.dbg_log('connman::menu_loader', 'exit_function', 0)
        except Exception as e:
            self.oe.set_busy(0)
            self.oe.dbg_log('connman::menu_loader', 'ERROR: (' + repr(e) + ')', 4)

    def open_context_menu(self, listItem):
        try:
            self.oe.dbg_log('connman::open_context_menu', 'enter_function', 0)
            values = {}
            if listItem is None:
                listItem = self.oe.winOeMain.getControl(self.oe.listObject['netlist']).getSelectedItem()
            if listItem is None:
                self.oe.dbg_log('connman::open_context_menu', 'exit_function (listItem=None)', 0)
                return
            if listItem.getProperty('State') in ['ready', 'online']:
                values[1] = {
                    'text': self.oe._(32143),
                    'action': 'disconnect_network',
                    }
            else:
                values[1] = {
                    'text': self.oe._(32144),
                    'action': 'connect_network',
                    }
            if listItem.getProperty('Favorite') == '1':
                values[2] = {
                    'text': self.oe._(32150),
                    'action': 'configure_network',
                    }
            if listItem.getProperty('Favorite') == '1' and listItem.getProperty('netType') == 'wifi':
                values[3] = {
                    'text': self.oe._(32141),
                    'action': 'delete_network',
                    }
            if hasattr(self, 'technologie_properties'):
                for (path, technologie) in self.technologie_properties:
                    if path == '/net/connman/technology/wifi':
                        values[4] = {
                            'text': self.oe._(32142),
                            'action': 'refresh_network',
                            }
                        break
            items = []
            actions = []
            for key in values.keys():
                items.append(values[key]['text'])
                actions.append(values[key]['action'])
            select_window = xbmcgui.Dialog()
            title = self.oe._(32012).encode('utf-8')
            result = select_window.select(title, items)
            if result >= 0:
                getattr(self, actions[result])(listItem)
            self.oe.dbg_log('connman::open_context_menu', 'exit_function', 0)
        except Exception as e:
            self.oe.dbg_log('connman::open_context_menu', 'ERROR: (' + repr(e) + ')', 4)

    def set_timeservers(self, **kwargs):
        try:
            self.oe.set_busy(1)
            if 'listItem' in kwargs:
                self.set_value(kwargs['listItem'])
            self.oe.dbg_log('connman::set_timeservers', 'enter_function', 0)
            self.clock = dbus.Interface(self.oe.dbusSystemBus.get_object('net.connman', '/'), 'net.connman.Clock')
            timeservers = dbus.Array([], signature=dbus.Signature('s'), variant_level=1)
            for setting in sorted(self.struct['Timeservers']['settings']):
                if self.struct['Timeservers']['settings'][setting]['value'] != '':
                    timeservers.append(self.struct['Timeservers']['settings'][setting]['value'])
            self.clock.SetProperty(dbus.String('Timeservers'), timeservers)
            self.oe.dbg_log('connman::set_timeservers', 'exit_function', 0)
            self.oe.set_busy(0)
        except Exception as e:
            self.oe.set_busy(0)
            self.oe.dbg_log('connman::set_timeservers', 'ERROR: (' + repr(e) + ')', 4)

    def set_value(self, listItem=None):
        try:
            self.oe.dbg_log('connman::set_value', 'enter_function', 0)
            self.struct[listItem.getProperty('category')]['settings'][listItem.getProperty('entry')]['value'] = listItem.getProperty('value')
            self.struct[listItem.getProperty('category')]['settings'][listItem.getProperty('entry')]['changed'] = True
            self.oe.dbg_log('connman::set_value', 'exit_function', 0)
        except Exception as e:
            self.oe.dbg_log('connman::set_value', 'ERROR: (' + repr(e) + ')', 4)

    def set_technologie(self, **kwargs):
        try:
            self.oe.dbg_log('connman::set_technologies', 'enter_function', 0)
            self.oe.set_busy(1)
            if 'listItem' in kwargs:
                self.set_value(kwargs['listItem'])
            dbusConnmanManager = dbus.Interface(self.oe.dbusSystemBus.get_object('net.connman', '/'), 'net.connman.Manager')
            self.technologie_properties = dbusConnmanManager.GetTechnologies()
            dbusConnmanManager = None
            techPath = '/net/connman/technology/wifi'
            for (path, technologie) in self.technologie_properties:
                if path == techPath:
                    for setting in self.struct[techPath]['settings']:
                        settings = self.struct[techPath]['settings']
                        self.Technology = dbus.Interface(self.oe.dbusSystemBus.get_object('net.connman', techPath), 'net.connman.Technology')
                        if settings['Powered']['value'] == '1':
                            if technologie['Powered'] != True:
                                self.Technology.SetProperty('Powered', dbus.Boolean(True, variant_level=1))
                            if settings['Tethering']['value'] == '1' and dbus.String(settings['TetheringIdentifier']['value']) != '' \
                                and dbus.String(settings['TetheringPassphrase']['value']) != '':
                                time.sleep(5)
                                self.Technology.SetProperty('TetheringIdentifier', dbus.String(settings['TetheringIdentifier']['value'],
                                                            variant_level=1))
                                self.Technology.SetProperty('TetheringPassphrase', dbus.String(settings['TetheringPassphrase']['value'],
                                                            variant_level=1))
                                if technologie['Tethering'] != True:
                                    self.Technology.SetProperty('Tethering', dbus.Boolean(True, variant_level=1))
                            else:
                                if technologie['Tethering'] != False:
                                    self.Technology.SetProperty('Tethering', dbus.Boolean(False, variant_level=1))
                        else:
                            xbmc.log('####' + repr(technologie['Powered']))
                            if technologie['Powered'] != False:
                                self.Technology.SetProperty('Powered', dbus.Boolean(False, variant_level=1))
                        break
            techPath = '/net/connman/technology/ethernet'
            for (path, technologie) in self.technologie_properties:
                if path == techPath:
                    for setting in self.struct[techPath]['settings']:
                        settings = self.struct[techPath]['settings']
                        self.Technology = dbus.Interface(self.oe.dbusSystemBus.get_object('net.connman', techPath), 'net.connman.Technology')
                        if settings['Powered']['value'] == '1':
                            if technologie['Powered'] != True:
                                self.Technology.SetProperty('Powered', dbus.Boolean(True, variant_level=1))
                        else:
                            if technologie['Powered'] != False:
                                self.Technology.SetProperty('Powered', dbus.Boolean(False, variant_level=1))
                        break
            self.technologie_properties = None
            self.menu_loader(None)
            self.oe.set_busy(0)
            self.oe.dbg_log('connman::set_technologies', 'exit_function', 0)
        except Exception as e:
            self.oe.set_busy(0)
            self.oe.dbg_log('connman::set_technologies', 'ERROR: (' + repr(e) + ')', 4)

    def configure_network(self, listItem=None):
        try:
            self.oe.dbg_log('connman::configure_network', 'enter_function', 0)
            if listItem == None:
                listItem = self.oe.winOeMain.getControl(self.oe.listObject['netlist']).getSelectedItem()
            self.configureService = connmanService(listItem.getProperty('entry'), self.oe)
            del self.configureService
            self.menu_connections(None)
            self.oe.dbg_log('connman::configure_network', 'exit_function', 0)
        except Exception as e:
            self.oe.dbg_log('connman::configure_network', 'ERROR: (' + repr(e) + ')', 4)

    def connect_network(self, listItem=None):
        try:
            self.oe.dbg_log('connman::connect_network', 'enter_function', 0)
            self.oe.set_busy(1)
            self.connect_attempt += 1
            if listItem == None:
                listItem = self.oe.winOeMain.getControl(self.oe.listObject['netlist']).getSelectedItem()
            service_object = self.oe.dbusSystemBus.get_object('net.connman', listItem.getProperty('entry'))
            dbus.Interface(service_object, 'net.connman.Service').Connect(reply_handler=self.connect_reply_handler,
                    error_handler=self.dbus_error_handler)
            service_object = None
            self.oe.dbg_log('connman::connect_network', 'exit_function', 0)
        except Exception as e:
            self.oe.set_busy(0)
            self.oe.dbg_log('connman::connect_network', 'ERROR: (' + repr(e) + ')', 4)

    def connect_reply_handler(self):
        try:
            self.oe.dbg_log('connman::connect_reply_handler', 'enter_function', 0)
            self.oe.set_busy(0)
            self.menu_connections(None)
            self.oe.dbg_log('connman::connect_reply_handler', 'exit_function', 0)
        except Exception as e:
            self.oe.set_busy(0)
            self.oe.dbg_log('connman::connect_reply_handler', 'ERROR: (' + repr(e) + ')', 4)

    def dbus_error_handler(self, error):
        try:
            self.oe.dbg_log('connman::dbus_error_handler', 'enter_function', 0)
            self.oe.set_busy(0)
            err_name = error.get_dbus_name()
            if 'InProgress' in err_name:
                if self.net_disconnected != 1:
                    self.disconnect_network()
                else:
                    self.net_disconnected = 0
                self.connect_network()
            else:
                err_message = error.get_dbus_message()
                if 'Operation aborted' in err_message or 'Input/output error' in err_message:
                    if self.connect_attempt == 1:
                        self.log_error = 0
                        self.notify_error = 0
                        time.sleep(5)
                        self.connect_network()
                    else:
                        self.log_error = 1
                        self.notify_error = 1
                elif 'Did not receive a reply' in err_message:
                    self.log_error = 1
                    self.notify_error = 0
                else:
                    self.log_error = 1
                    self.notify_error = 1
                if self.notify_error == 1:
                    self.oe.notify('Network Error', err_message)
                else:
                    self.notify_error = 1
                if self.log_error == 1:
                    self.oe.dbg_log('connman::dbus_error_handler', 'ERROR: (' + err_message + ')', 4)
                else:
                    self.log_error = 1
            self.oe.dbg_log('connman::dbus_error_handler', 'exit_function', 0)
        except Exception as e:
            self.oe.set_busy(0)
            self.oe.dbg_log('connman::dbus_error_handler', 'ERROR: (' + repr(e) + ')', 4)

    def disconnect_network(self, listItem=None):
        try:
            self.oe.dbg_log('connman::disconnect_network', 'enter_function', 0)
            self.oe.set_busy(1)
            self.connect_attempt = 0
            self.net_disconnected = 1
            if listItem == None:
                listItem = self.oe.winOeMain.getControl(self.oe.listObject['netlist']).getSelectedItem()
            service_object = self.oe.dbusSystemBus.get_object('net.connman', listItem.getProperty('entry'))
            dbus.Interface(service_object, 'net.connman.Service').Disconnect()
            service_object = None
            del service_object
            self.oe.set_busy(0)
            self.oe.dbg_log('connman::disconnect_network', 'exit_function', 0)
        except Exception as e:
            self.oe.set_busy(0)
            self.oe.dbg_log('connman::disconnect_network', 'ERROR: (' + repr(e) + ')', 4)

    def delete_network(self, listItem=None):
        try:
            self.oe.dbg_log('connman::delete_network', 'enter_function', 0)
            self.oe.set_busy(1)
            self.connect_attempt = 0
            if listItem == None:
                listItem = self.oe.winOeMain.getControl(self.oe.listObject['netlist']).getSelectedItem()
            service_path = listItem.getProperty('entry')
            network_type = listItem.getProperty('netType')
            service_object = self.oe.dbusSystemBus.get_object('net.connman', service_path)
            dbus.Interface(service_object, 'net.connman.Service').Remove()
            service_object = None
            del service_object
            self.oe.set_busy(0)
            self.oe.dbg_log('connman::delete_network', 'exit_function', 0)
        except Exception as e:
            self.oe.set_busy(0)
            self.oe.dbg_log('connman::delete_network', 'ERROR: (' + repr(e) + ')', 4)

    def refresh_network(self, listItem=None):
        try:
            self.oe.dbg_log('connman::refresh_network', 'enter_function', 0)
            self.oe.set_busy(1)
            wifi = self.oe.dbusSystemBus.get_object('net.connman', '/net/connman/technology/wifi')
            dbus.Interface(wifi, 'net.connman.Technology').Scan()
            wifi = None
            del wifi
            self.oe.set_busy(0)
            self.menu_connections(None)
            self.oe.dbg_log('connman::refresh_network', 'exit_function', 0)
        except Exception as e:
            self.oe.set_busy(0)
            self.oe.dbg_log('connman::refresh_network', 'ERROR: (' + repr(e) + ')', 4)

    def get_service_path(self):
        try:
            self.oe.dbg_log('connman::get_service_path', 'enter_function', 0)
            if hasattr(self, 'winOeCon'):
                return self.winOeCon.service_path
            else:
                listItem = self.oe.winOeMain.getControl(self.oe.listObject['netlist']).getSelectedItem()
                return listItem.getProperty('entry')
            self.oe.dbg_log('connman::get_service_path', 'exit_function', 0)
        except Exception as e:
            self.oe.dbg_log('connman::get_service_path', 'ERROR: (' + repr(e) + ')', 4)

    def start_service(self):
        try:
            self.oe.dbg_log('connman::start_service', 'enter_function', 0)
            self.load_values()
            self.init_netfilter(service=1)
            self.oe.dbg_log('connman::start_service', 'exit_function', 0)
        except Exception as e:
            self.oe.dbg_log('connman::start_service', 'ERROR: (' + repr(e) + ')')

    def stop_service(self):
        try:
            self.oe.dbg_log('connman::stop_service', 'enter_function', 0)
            if hasattr(self, 'dbusConnmanManager'):
                self.dbusConnmanManager = None
                del self.dbusConnmanManager
            self.oe.dbg_log('connman::stop_service', 'exit_function', 0)
        except Exception as e:
            self.oe.dbg_log('system::stop_service', 'ERROR: (' + repr(e) + ')')

    def set_network_wait(self, **kwargs):
        try:
            self.oe.dbg_log('connman::set_network_wait', 'enter_function', 0)
            if 'listItem' in kwargs:
                self.set_value(kwargs['listItem'])
            if self.struct['advanced']['settings']['wait_for_network']['value'] == '0':
                if os.path.exists(self.WAIT_CONF_FILE):
                    os.remove(self.WAIT_CONF_FILE)
                return
            else:
                if not os.path.exists(os.path.dirname(self.WAIT_CONF_FILE)):
                    os.makedirs(os.path.dirname(self.WAIT_CONF_FILE))
                wait_conf = open(self.WAIT_CONF_FILE, 'w')
                wait_conf.write('WAIT_NETWORK="true"\n')
                wait_conf.write('WAIT_NETWORK_TIME="%s"\n' % self.struct['advanced']['settings']['wait_for_network_time']['value'])
                wait_conf.close()
            self.oe.dbg_log('connman::set_network_wait', 'exit_function', 0)
        except Exception as e:
            self.oe.dbg_log('system::set_network_wait', 'ERROR: (' + repr(e) + ')')

    def init_netfilter(self, **kwargs):
        try:
            self.oe.dbg_log('connman::init_netfilter', 'enter_function', 0)
            self.oe.set_busy(1)
            if 'listItem' in kwargs:
                self.set_value(kwargs['listItem'])
            state = 1
            options = {}
            if self.struct['advanced']['settings']['netfilter']['value'] == self.oe._(32396):
                options['RULES'] = "custom"
            elif self.struct['advanced']['settings']['netfilter']['value'] == self.oe._(32398):
                options['RULES'] = "home"
            elif self.struct['advanced']['settings']['netfilter']['value'] == self.oe._(32399):
                options['RULES'] = "public"
            else:
                state = 0
            self.oe.set_service('iptables', options, state)
            self.oe.set_busy(0)
            self.oe.dbg_log('connman::init_netfilter', 'exit_function', 0)
        except Exception as e:
            self.oe.dbg_log('system::init_netfilter', 'ERROR: (' + repr(e) + ')')

    def do_wizard(self):
        try:
            self.oe.dbg_log('connman::do_wizard', 'enter_function', 0)
            self.oe.winOeMain.set_wizard_title(self.oe._(32305))
            self.oe.winOeMain.set_wizard_text(self.oe._(32306))
            self.oe.winOeMain.set_wizard_button_title('')
            self.oe.winOeMain.set_wizard_list_title(self.oe._(32309))
            self.oe.winOeMain.getControl(1391).setLabel('show')

            self.oe.winOeMain.getControl(self.oe.winOeMain.buttons[2]['id'
                                         ]).controlUp(self.oe.winOeMain.getControl(self.oe.winOeMain.guiNetList))
            self.oe.winOeMain.getControl(self.oe.winOeMain.buttons[2]['id'
                                         ]).controlRight(self.oe.winOeMain.getControl(self.oe.winOeMain.buttons[1]['id']))
            self.oe.winOeMain.getControl(self.oe.winOeMain.buttons[1]['id'
                                         ]).controlUp(self.oe.winOeMain.getControl(self.oe.winOeMain.guiNetList))
            self.oe.winOeMain.getControl(self.oe.winOeMain.buttons[1]['id'
                                         ]).controlLeft(self.oe.winOeMain.getControl(self.oe.winOeMain.buttons[2]['id']))

            self.menu_connections(None)
            self.oe.dbg_log('connman::do_wizard', 'exit_function', 0)
        except Exception as e:
            self.oe.dbg_log('connman::do_wizard', 'ERROR: (' + repr(e) + ')')

    class monitor:

        def __init__(self, oeMain, parent):
            try:
                oeMain.dbg_log('connman::monitor::__init__', 'enter_function', 0)
                self.oe = oeMain
                self.signal_receivers = []
                self.NameOwnerWatch = None
                self.parent = parent
                self.wifiAgentPath = '/LibreELEC/agent_wifi'
                self.oe.dbg_log('connman::monitor::__init__', 'exit_function', 0)
            except Exception as e:
                self.oe.dbg_log('connman::monitor::__init__', 'ERROR: (' + repr(e) + ')')

        def add_signal_receivers(self):
            try:
                self.oe.dbg_log('connman::monitor::add_signal_receivers', 'enter_function', 0)
                self.signal_receivers.append(self.oe.dbusSystemBus.add_signal_receiver(self.propertyChanged, bus_name='net.connman',
                                             dbus_interface='net.connman.Manager', signal_name='PropertyChanged', path_keyword='path'))
                self.signal_receivers.append(self.oe.dbusSystemBus.add_signal_receiver(self.servicesChanged, bus_name='net.connman',
                                             dbus_interface='net.connman.Manager', signal_name='ServicesChanged'))
                self.signal_receivers.append(self.oe.dbusSystemBus.add_signal_receiver(self.propertyChanged, bus_name='net.connman',
                                             dbus_interface='net.connman.Service', signal_name='PropertyChanged', path_keyword='path'))
                self.signal_receivers.append(self.oe.dbusSystemBus.add_signal_receiver(self.technologyChanged, bus_name='net.connman',
                                             dbus_interface='net.connman.Technology', signal_name='PropertyChanged', path_keyword='path'))
                self.signal_receivers.append(self.oe.dbusSystemBus.add_signal_receiver(self.managerPropertyChanged, bus_name='net.connman',
                                             signal_name='PropertyChanged', path_keyword='path', interface_keyword='interface'))
                self.conNameOwnerWatch = self.oe.dbusSystemBus.watch_name_owner('net.connman', self.conNameOwnerChanged)
                self.oe.dbg_log('connman::monitor::add_signal_receivers', 'exit_function', 0)
            except Exception as e:
                self.oe.dbg_log('connman::monitor::add_signal_receivers', 'ERROR: (' + repr(e) + ')', 4)

        def remove_signal_receivers(self):
            try:
                self.oe.dbg_log('connman::monitor::remove_signal_receivers', 'enter_function', 0)
                for signal_receiver in self.signal_receivers:
                    signal_receiver.remove()
                    signal_receiver = None
                self.conNameOwnerWatch.cancel()
                self.conNameOwnerWatch = None
                if hasattr(self, 'wifiAgent'):
                    self.remove_agent()
                self.oe.dbg_log('connman::monitor::remove_signal_receivers', 'exit_function', 0)
            except Exception as e:
                self.oe.dbg_log('connman::monitor::remove_signal_receivers', 'ERROR: (' + repr(e) + ')', 4)

        def conNameOwnerChanged(self, proxy):
            try:
                self.oe.dbg_log('connman::monitor::nameOwnerChanged', 'enter_function', 0)
                if proxy:
                    self.initialize_agent()
                else:
                    self.remove_agent()
                self.oe.dbg_log('connman::monitor::nameOwnerChanged', 'exit_function', 0)
            except Exception as e:
                self.oe.dbg_log('connman::monitor::nameOwnerChanged', 'ERROR: (' + repr(e) + ')', 4)

        def initialize_agent(self):
            try:
                self.oe.dbg_log('connman::monitor::initialize_agent', 'enter_function', 0)
                if not hasattr(self, 'wifiAgent'):
                    dbusConnmanManager = dbus.Interface(self.oe.dbusSystemBus.get_object('net.connman', '/'), 'net.connman.Manager')
                    self.wifiAgent = connmanWifiAgent(self.oe.dbusSystemBus, self.wifiAgentPath)
                    self.wifiAgent.oe = self.oe
                    dbusConnmanManager.RegisterAgent(self.wifiAgentPath)
                    dbusConnmanManager = None
                self.oe.dbg_log('connman::monitor::initialize_agent', 'exit_function', 0)
            except Exception as e:
                self.oe.dbg_log('connman::monitor::initialize_agent', 'ERROR: (' + repr(e) + ')', 4)

        def remove_agent(self):
            try:
                self.oe.dbg_log('connman::monitor::remove_agent', 'enter_function', 0)
                if hasattr(self, 'wifiAgent'):
                    self.wifiAgent.remove_from_connection(self.oe.dbusSystemBus, self.wifiAgentPath)
                    try:
                        dbusConnmanManager = dbus.Interface(self.oe.dbusSystemBus.get_object('net.connman', '/'), 'net.connman.Manager')
                        dbusConnmanManager.UnregisterAgent(self.wifiAgentPath)
                        dbusConnmanManager = None
                    except:
                        dbusConnmanManager = None
                    del self.wifiAgent
                self.oe.dbg_log('connman::monitor::remove_agent', 'exit_function', 0)
            except Exception as e:
                self.oe.dbg_log('connman::monitor::remove_agent', 'ERROR: (' + repr(e) + ')', 4)

        def managerPropertyChanged(self, name, value, path, interface):
            try:
                self.oe.dbg_log('connman::monitor::managerPropertyChanged', 'enter_function', 0)
                self.oe.dbg_log('connman::monitor::managerPropertyChanged::name', repr(name), 0)
                self.oe.dbg_log('connman::monitor::managerPropertyChanged::value', repr(value), 0)
                self.oe.dbg_log('connman::monitor::managerPropertyChanged::path', repr(path), 0)
                self.oe.dbg_log('connman::monitor::managerPropertyChanged::interface', repr(interface), 0)
                self.oe.dbg_log('connman::monitor::managerPropertyChanged', 'exit_function', 0)
            except Exception as e:
                self.oe.dbg_log('connman::monitor::managerPropertyChanged', 'ERROR: (' + repr(e) + ')', 4)

        def propertyChanged(self, name, value, path):
            try:
                self.oe.dbg_log('connman::monitor::propertyChanged', 'enter_function', 0)
                self.oe.dbg_log('connman::monitor::propertyChanged::name', repr(name), 0)
                self.oe.dbg_log('connman::monitor::propertyChanged::value', repr(value), 0)
                self.oe.dbg_log('connman::monitor::propertyChanged::path', repr(path), 0)
                if self.parent.visible:
                    self.updateGui(name, value, path)
                self.oe.dbg_log('connman::monitor::propertyChanged', 'exit_function', 0)
            except Exception as e:
                self.oe.dbg_log('connman::monitor::propertyChanged', 'ERROR: (' + repr(e) + ')', 4)

        def technologyChanged(self, name, value, path):
            try:
                self.oe.dbg_log('connman::monitor::technologyChanged', 'enter_function', 0)
                self.oe.dbg_log('connman::monitor::technologyChanged::name', repr(name), 0)
                self.oe.dbg_log('connman::monitor::technologyChanged::value', repr(value), 0)
                self.oe.dbg_log('connman::monitor::technologyChanged::path', repr(path), 0)
                if self.parent.visible:
                    if self.parent.oe.winOeMain.lastMenu == 1:
                        self.parent.oe.winOeMain.lastMenu = -1
                        self.parent.oe.winOeMain.onFocus(self.parent.oe.winOeMain.guiMenList)
                    else:
                        self.updateGui(name, value, path)
                self.oe.dbg_log('connman::monitor::technologyChanged', 'exit_function', 0)
            except Exception as e:
                self.oe.dbg_log('connman::monitor::technologyChanged', 'ERROR: (' + repr(e) + ')', 4)

        def servicesChanged(self, services, removed):
            try:
                self.oe.dbg_log('connman::monitor::servicesChanged', 'enter_function', 0)
                self.oe.dbg_log('connman::monitor::servicesChanged::services', repr(services), 0)
                self.oe.dbg_log('connman::monitor::servicesChanged::removed', repr(removed), 0)
                if self.parent.visible:
                    self.parent.menu_connections(None, services, removed, force=True)
                self.oe.dbg_log('connman::monitor::servicesChanged', 'exit_function', 0)
            except Exception as e:
                self.oe.dbg_log('connman::monitor::servicesChanged', 'ERROR: (' + repr(e) + ')', 4)

        def updateGui(self, name, value, path):
            try:
                self.oe.dbg_log('connman::monitor::updateGui', 'enter_function', 0)
                if name == 'Strength':
                    value = unicode(int(value))
                    self.parent.listItems[path].setProperty(name, value)
                    self.forceRender()
                elif name == 'State':
                    value = unicode(value)
                    self.parent.listItems[path].setProperty(name, value)
                    self.forceRender()
                elif name == 'IPv4':
                    if 'Address' in value:
                        value = unicode(value['Address'])
                        self.parent.listItems[path].setProperty('Address', value)
                    if 'Method' in value:
                        value = unicode(value['Method'])
                        self.parent.listItems[path].setProperty('Address', value)
                    self.forceRender()
                elif name == 'Favorite':
                    value = unicode(int(value))
                    self.parent.listItems[path].setProperty(name, value)
                    self.forceRender()
                if hasattr(self.parent, 'is_wizard'):
                    self.parent.menu_connections(None, {}, {}, force=True)
                self.oe.dbg_log('connman::monitor::updateGui', 'exit_function', 0)
            except KeyError:
                self.oe.dbg_log('connman::monitor::updateGui', 'exit_function (KeyError)', 0)
                self.parent.menu_connections(None, {}, {}, force=True)
            except Exception as e:
                self.oe.dbg_log('connman::monitor::updateGui', 'ERROR: (' + repr(e) + ')', 4)

        def forceRender(self):
            try:
                self.oe.dbg_log('connman::monitor::forceRender', 'enter_function', 0)
                focusId = self.oe.winOeMain.getFocusId()
                self.oe.winOeMain.setFocusId(self.oe.listObject['netlist'])
                self.oe.winOeMain.setFocusId(focusId)
                self.oe.dbg_log('connman::monitor::forceRender', 'exit_function', 0)
            except Exception as e:
                self.oe.dbg_log('connman::monitor::forceRender', 'ERROR: (' + repr(e) + ')', 4)


class Failed(dbus.DBusException):

    _dbus_error_name = 'net.connman.Error.Failed'


class Canceled(dbus.DBusException):

    _dbus_error_name = 'net.connman.Error.Canceled'


class Retry(dbus.DBusException):

    _dbus_error_name = 'net.connman.Agent.Error.Retry'


class LaunchBrowser(dbus.DBusException):

    _dbus_error_name = 'net.connman.Agent.Error.LaunchBrowser'


class connmanWifiAgent(dbus.service.Object):

    def busy(self):
        self.oe.input_request = False

    @dbus.service.method('net.connman.Agent', in_signature='', out_signature='')
    def Release(self):
        self.oe.dbg_log('connman::connmanWifiAgent::Release', 'enter_function', 0)
        self.oe.dbg_log('connman::connmanWifiAgent::Release', 'exit_function', 0)
        return {}

    @dbus.service.method('net.connman.Agent', in_signature='oa{sv}', out_signature='a{sv}')
    def RequestInput(self, path, fields):
        try:
            self.oe.dbg_log('connman::connmanWifiAgent::RequestInput', 'enter_function', 0)
            self.oe.input_request = True
            response = {}
            if fields.has_key('Name'):
                xbmcKeyboard = xbmc.Keyboard('', self.oe._(32146).encode('utf-8'))
                xbmcKeyboard.doModal()
                if xbmcKeyboard.isConfirmed():
                    if xbmcKeyboard.getText() != '':
                        response['Name'] = xbmcKeyboard.getText()
                    else:
                        self.busy()
                        raise Canceled('canceled')
                        return response
                else:
                    self.busy()
                    raise Canceled('canceled')
                    return response
            if fields.has_key('Passphrase'):
                xbmcKeyboard = xbmc.Keyboard('', self.oe._(32147).encode('utf-8'))
                xbmcKeyboard.doModal()
                if xbmcKeyboard.isConfirmed():
                    if xbmcKeyboard.getText() != '':
                        response['Passphrase'] = xbmcKeyboard.getText()
                        if fields.has_key('Identity'):
                            response['Identity'] = xbmcKeyboard.getText()
                        if fields.has_key('wpspin'):
                            response['wpspin'] = xbmcKeyboard.getText()
                    else:
                        self.busy()
                        raise Canceled('canceled')
                        return response
                else:
                    self.busy()
                    raise Canceled('canceled')
                    return response
            if fields.has_key('Username'):
                xbmcKeyboard = xbmc.Keyboard('', self.oe._(32148).encode('utf-8'))
                xbmcKeyboard.doModal()
                if xbmcKeyboard.isConfirmed():
                    if xbmcKeyboard.getText() != '':
                        response['Username'] = xbmcKeyboard.getText()
                    else:
                        self.busy()
                        raise Canceled('canceled')
                        return response
                else:
                    self.busy()
                    raise Canceled('canceled')
                    return response
            if fields.has_key('Password'):
                xbmcKeyboard = xbmc.Keyboard('', self.oe._(32148).encode('utf-8'), True)
                xbmcKeyboard.doModal()
                if xbmcKeyboard.isConfirmed():
                    if xbmcKeyboard.getText() != '':
                        response['Password'] = xbmcKeyboard.getText()
                    else:
                        self.busy()
                        raise Canceled('canceled')
                        return response
                else:
                    self.busy()
                    raise Canceled('canceled')
                    return response
            self.busy()
            self.oe.dbg_log('connman::connmanWifiAgent::RequestInput', 'exit_function', 0)
            return response
        except Exception as e:
            self.oe.dbg_log('connman::connmanWifiAgent::RequestInput', 'ERROR: (' + repr(e) + ')', 4)

    @dbus.service.method('net.connman.Agent', in_signature='os', out_signature='')
    def RequestBrowser(self, path, url):
        self.oe.dbg_log('connman::connmanWifiAgent::RequestBrowser', 'enter_function', 0)
        self.oe.dbg_log('connman::connmanWifiAgent::RequestBrowser', 'exit_function', 0)
        return

    @dbus.service.method('net.connman.Agent', in_signature='os', out_signature='')
    def ReportError(self, path, error):
        self.oe.dbg_log('connman::connmanWifiAgent::ReportError', 'enter_function', 0)
        self.oe.dbg_log('connman::connmanWifiAgent::ReportError', 'exit_function (CANCELED)', 0)
        raise Failed()
        return

    @dbus.service.method('net.connman.Agent', in_signature='', out_signature='')
    def Cancel(self):
        self.oe.dbg_log('connman::connmanWifiAgent::Cancel', 'enter_function', 0)
        self.oe.dbg_log('connman::connmanWifiAgent::Cancel', 'exit_function', 0)
        return
