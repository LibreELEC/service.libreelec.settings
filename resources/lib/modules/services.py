# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
# Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)
# Copyright (C) 2019-present Team LibreELEC (https://libreelec.tv)

import os
import shutil
import subprocess

import xbmcgui

import log
import modules
import oe


xbmcDialog = xbmcgui.Dialog()

class services(modules.Module):

    ENABLED = False
    SAMBA_NMDB = None
    SAMBA_SMDB = None
    D_SAMBA_SECURE = None
    D_SAMBA_WORKGROUP = None
    D_SAMBA_USERNAME = None
    D_SAMBA_PASSWORD = None
    D_SAMBA_MINPROTOCOL = None
    D_SAMBA_MAXPROTOCOL = None
    D_SAMBA_AUTOSHARE = None
    KERNEL_CMD = None
    SSH_DAEMON = None
    D_SSH_DISABLE_PW_AUTH = None
    OPT_SSH_NOPASSWD = None
    AVAHI_DAEMON = None
    CRON_DAEMON = None
    menu = {'7': {
        'name': 32001,
        'menuLoader': 'load_menu',
        'listTyp': 'list',
        'InfoText': 703,
        }}

    @log.log_function()
    def __init__(self, oeMain):
        super().__init__()
        self.struct = {
            'samba': {
                'order': 1,
                'name': 32200,
                'not_supported': [],
                'settings': {
                    'samba_autostart': {
                        'order': 1,
                        'name': 32204,
                        'value': None,
                        'action': 'initialize_samba',
                        'type': 'bool',
                        'InfoText': 738,
                        },
                    'samba_workgroup': {
                        'order': 2,
                        'name': 32215,
                        'value': "WORKGROUP",
                        'action': 'initialize_samba',
                        'type': 'text',
                        'parent': {
                            'entry': 'samba_autostart',
                            'value': ['1'],
                            },
                        'InfoText': 758,
                        },
                    'samba_secure': {
                        'order': 3,
                        'name': 32202,
                        'value': None,
                        'action': 'initialize_samba',
                        'type': 'bool',
                        'parent': {
                            'entry': 'samba_autostart',
                            'value': ['1'],
                            },
                        'InfoText': 739,
                        },
                    'samba_username': {
                        'order': 4,
                        'name': 32106,
                        'value': None,
                        'action': 'initialize_samba',
                        'type': 'text',
                        'parent': {
                            'entry': 'samba_secure',
                            'value': ['1'],
                            },
                        'InfoText': 740,
                        },
                    'samba_password': {
                        'order': 5,
                        'name': 32107,
                        'value': None,
                        'action': 'initialize_samba',
                        'type': 'text',
                        'parent': {
                            'entry': 'samba_secure',
                            'value': ['1'],
                            },
                        'InfoText': 741,
                        },
                    'samba_minprotocol': {
                        'order': 6,
                        'name': 32217,
                        'value': 'SMB2',
                        'action': 'initialize_samba',
                        'type': 'multivalue',
                        'values': [
                            'SMB1',
                            'SMB2',
                            'SMB3',
                            ],
                        'parent': {
                            'entry': 'samba_autostart',
                            'value': ['1'],
                            },
                        'InfoText': 756,
                        },
                    'samba_maxprotocol': {
                        'order': 7,
                        'name': 32218,
                        'value': 'SMB3',
                        'action': 'initialize_samba',
                        'type': 'multivalue',
                        'values': [
                            'SMB1',
                            'SMB2',
                            'SMB3',
                            ],
                        'parent': {
                            'entry': 'samba_autostart',
                            'value': ['1'],
                            },
                        'InfoText': 757,
                        },
                    'samba_autoshare': {
                        'order': 8,
                        'name': 32216,
                        'value': None,
                        'action': 'initialize_samba',
                        'type': 'bool',
                        'parent': {
                            'entry': 'samba_autostart',
                            'value': ['1'],
                            },
                        'InfoText': 755,
                        },
                    },
                },
            'ssh': {
                'order': 2,
                'name': 32201,
                'not_supported': [],
                'settings': {
                    'ssh_autostart': {
                        'order': 1,
                        'name': 32205,
                        'value': None,
                        'action': 'initialize_ssh',
                        'type': 'bool',
                        'InfoText': 742,
                        },
                    'ssh_secure': {
                        'order': 2,
                        'name': 32203,
                        'value': None,
                        'action': 'initialize_ssh',
                        'type': 'bool',
                        'parent': {
                            'entry': 'ssh_autostart',
                            'value': ['1'],
                            },
                        'InfoText': 743,
                        },
                    'ssh_passwd': {
                        'order': 3,
                        'name': 32209,
                        'value': None,
                        'action': 'do_sshpasswd',
                        'type': 'button',
                        'parent': {
                            'entry': 'ssh_secure',
                            'value': ['0'],
                            },
                        'InfoText': 746,
                        },
                    },
                },
            'avahi': {
                'order': 3,
                'name': 32207,
                'not_supported': [],
                'settings': {'avahi_autostart': {
                    'order': 1,
                    'name': 32206,
                    'value': None,
                    'action': 'initialize_avahi',
                    'type': 'bool',
                    'InfoText': 744,
                    }},
                },
            'cron': {
                'order': 4,
                'name': 32319,
                'not_supported': [],
                'settings': {'cron_autostart': {
                    'order': 1,
                    'name': 32320,
                    'value': None,
                    'action': 'initialize_cron',
                    'type': 'bool',
                    'InfoText': 745,
                    }},
                },
            'bluez': {
                'order': 6,
                'name': 32331,
                'not_supported': [],
                'settings': {
                    'enabled': {
                        'order': 1,
                        'name': 32344,
                        'value': None,
                        'action': 'initialize_bluetooth',
                        'type': 'bool',
                        'InfoText': 720,
                        },
                    'obex_enabled': {
                        'order': 2,
                        'name': 32384,
                        'value': None,
                        'action': 'initialize_obex',
                        'type': 'bool',
                        'parent': {
                            'entry': 'enabled',
                            'value': ['1'],
                            },
                        'InfoText': 751,
                        },
                    'obex_root': {
                        'order': 3,
                        'name': 32385,
                        'value': None,
                        'action': 'initialize_obex',
                        'type': 'folder',
                        'parent': {
                            'entry': 'obex_enabled',
                            'value': ['1'],
                            },
                        'InfoText': 752,
                        },
                    'idle_timeout': {
                        'order': 4,
                        'name': 32400,
                        'value': None,
                        'action': 'idle_timeout',
                        'type': 'multivalue',
                        'values': [
                            '0',
                            '1',
                            '3',
                            '5',
                            '15',
                            '30',
                            '60',
                            ],
                        'parent': {
                            'entry': 'enabled',
                            'value': ['1'],
                            },
                        'InfoText': 773,
                        },
                    },
                },
            }

    @log.log_function()
    def start_service(self):
        self.load_values()
        self.initialize_samba(service=1)
        self.initialize_ssh(service=1)
        self.initialize_avahi(service=1)
        self.initialize_cron(service=1)
        self.initialize_bluetooth(service=1)

    @log.log_function()
    def do_init(self):
        self.load_values()

    @log.log_function()
    def set_value(self, listItem):
        self.struct[listItem.getProperty('category')]['settings'][listItem.getProperty('entry')]['value'] = listItem.getProperty('value')

    @log.log_function()
    def load_menu(self, focusItem):
        oe.winOeMain.build_menu(self.struct)

    @log.log_function()
    def load_values(self):
        # SAMBA
        if os.path.isfile(self.SAMBA_NMDB) and os.path.isfile(self.SAMBA_SMDB):
            self.struct['samba']['settings']['samba_autostart']['value'] = oe.get_service_state('samba')
            self.struct['samba']['settings']['samba_workgroup']['value'] = oe.get_service_option('samba', 'SAMBA_WORKGROUP',
                    self.D_SAMBA_WORKGROUP).replace('"', '')
            self.struct['samba']['settings']['samba_secure']['value'] = oe.get_service_option('samba', 'SAMBA_SECURE',
                    self.D_SAMBA_SECURE).replace('true', '1').replace('false', '0').replace('"', '')
            self.struct['samba']['settings']['samba_username']['value'] = self.sh_unesc_str(oe.get_service_option('samba', 'SAMBA_USERNAME',
                    self.D_SAMBA_USERNAME).replace('"', ''))
            self.struct['samba']['settings']['samba_password']['value'] = self.sh_unesc_str(oe.get_service_option('samba', 'SAMBA_PASSWORD',
                    self.D_SAMBA_PASSWORD).replace('"', ''))
            self.struct['samba']['settings']['samba_minprotocol']['value'] = oe.get_service_option('samba', 'SAMBA_MINPROTOCOL',
                    self.D_SAMBA_MINPROTOCOL).replace('"', '')
            self.struct['samba']['settings']['samba_maxprotocol']['value'] = oe.get_service_option('samba', 'SAMBA_MAXPROTOCOL',
                    self.D_SAMBA_MAXPROTOCOL).replace('"', '')
            self.struct['samba']['settings']['samba_autoshare']['value'] = oe.get_service_option('samba', 'SAMBA_AUTOSHARE',
                    self.D_SAMBA_AUTOSHARE).replace('true', '1').replace('false', '0').replace('"', '')
        else:
            self.struct['samba']['hidden'] = 'true'
        # SSH
        if os.path.isfile(self.SSH_DAEMON):
            self.struct['ssh']['settings']['ssh_autostart']['value'] = oe.get_service_state('sshd')
            self.struct['ssh']['settings']['ssh_secure']['value'] = oe.get_service_option('sshd', 'SSHD_DISABLE_PW_AUTH',
                    self.D_SSH_DISABLE_PW_AUTH).replace('true', '1').replace('false', '0').replace('"', '')
            # hide ssh settings if Kernel Parameter is set
            with open(self.KERNEL_CMD, 'r') as cmd_file:
                cmd_args = cmd_file.read().split(' ')
            if 'ssh' in cmd_args:
                self.struct['ssh']['settings']['ssh_autostart']['value'] = '1'
                self.struct['ssh']['settings']['ssh_autostart']['hidden'] = 'true'
        else:
            self.struct['ssh']['hidden'] = 'true'
        # AVAHI
        if os.path.isfile(self.AVAHI_DAEMON):
            self.struct['avahi']['settings']['avahi_autostart']['value'] = oe.get_service_state('avahi')
        else:
            self.struct['avahi']['hidden'] = 'true'
        # CRON
        if os.path.isfile(self.CRON_DAEMON):
            self.struct['cron']['settings']['cron_autostart']['value'] = oe.get_service_state('crond')
        else:
            self.struct['cron']['hidden'] = 'true'
        # BLUEZ / OBEX
        if 'bluetooth' in oe.dictModules:
            if os.path.isfile(oe.dictModules['bluetooth'].BLUETOOTH_DAEMON):
                self.struct['bluez']['settings']['enabled']['value'] = oe.get_service_state('bluez')
                if os.path.isfile(oe.dictModules['bluetooth'].OBEX_DAEMON):
                    self.struct['bluez']['settings']['obex_enabled']['value'] = oe.get_service_state('obexd')
                    self.struct['bluez']['settings']['obex_root']['value'] = oe.get_service_option('obexd', 'OBEXD_ROOT',
                            oe.dictModules['bluetooth'].D_OBEXD_ROOT).replace('"', '')
                else:
                    self.struct['bluez']['settings']['obex_enabled']['hidden'] = True
                    self.struct['bluez']['settings']['obex_root']['hidden'] = True

                value = oe.read_setting('bluetooth', 'idle_timeout')
                if not value:
                    value = '0'
                self.struct['bluez']['settings']['idle_timeout']['value'] = value
            else:
                self.struct['bluez']['hidden'] = 'true'

    @log.log_function()
    def initialize_samba(self, **kwargs):
        if 'listItem' in kwargs:
            self.set_value(kwargs['listItem'])
        options = {}
        if self.struct['samba']['settings']['samba_autostart']['value'] == '1':
            state = 1
            if 'hidden' in self.struct['samba']['settings']['samba_username']:
                del self.struct['samba']['settings']['samba_username']['hidden']
            if 'hidden' in self.struct['samba']['settings']['samba_password']:
                del self.struct['samba']['settings']['samba_password']['hidden']
            if self.struct['samba']['settings']['samba_secure']['value'] == '1':
                val_secure = 'true'
            else:
                val_secure = 'false'
            if self.struct['samba']['settings']['samba_autoshare']['value'] == '1':
                val_autoshare = 'true'
            else:
                val_autoshare = 'false'
            options['SAMBA_WORKGROUP'] = self.struct['samba']['settings']['samba_workgroup']['value']
            options['SAMBA_SECURE'] = val_secure
            options['SAMBA_AUTOSHARE'] = val_autoshare
            options['SAMBA_MINPROTOCOL'] = self.struct['samba']['settings']['samba_minprotocol']['value']
            options['SAMBA_MAXPROTOCOL'] = self.struct['samba']['settings']['samba_maxprotocol']['value']
            options['SAMBA_USERNAME'] = self.sh_esc_str(self.struct['samba']['settings']['samba_username']['value'])
            options['SAMBA_PASSWORD'] = self.sh_esc_str(self.struct['samba']['settings']['samba_password']['value'])
        else:
            state = 0
            self.struct['samba']['settings']['samba_username']['hidden'] = True
            self.struct['samba']['settings']['samba_password']['hidden'] = True
        oe.set_service('samba', options, state)

    @log.log_function()
    def initialize_ssh(self, **kwargs):
        if 'listItem' in kwargs:
            self.set_value(kwargs['listItem'])
        options = {}
        if self.struct['ssh']['settings']['ssh_autostart']['value'] == '1':
            state = 1
            if self.struct['ssh']['settings']['ssh_secure']['value'] == '1':
                val = 'true'
                options['SSH_ARGS'] = self.OPT_SSH_NOPASSWD
            else:
                val = 'false'
                options['SSH_ARGS'] = '""'
            options['SSHD_DISABLE_PW_AUTH'] = val
        else:
            state = 0
        oe.set_service('sshd', options, state)

    @log.log_function()
    def initialize_avahi(self, **kwargs):
        if 'listItem' in kwargs:
            self.set_value(kwargs['listItem'])
        options = {}
        if self.struct['avahi']['settings']['avahi_autostart']['value'] == '1':
            state = 1
        else:
            state = 0
        oe.set_service('avahi', options, state)

    @log.log_function()
    def initialize_cron(self, **kwargs):
        if 'listItem' in kwargs:
            self.set_value(kwargs['listItem'])
        options = {}
        if self.struct['cron']['settings']['cron_autostart']['value'] == '1':
            state = 1
        else:
            state = 0
        oe.set_service('crond', options, state)

    @log.log_function()
    def initialize_bluetooth(self, **kwargs):
        if 'listItem' in kwargs:
            self.set_value(kwargs['listItem'])
        options = {}
        if self.struct['bluez']['settings']['enabled']['value'] == '1':
            state = 1
            if 'hidden' in self.struct['bluez']['settings']['obex_enabled']:
                del self.struct['bluez']['settings']['obex_enabled']['hidden']
            if 'hidden' in self.struct['bluez']['settings']['obex_root']:
                del self.struct['bluez']['settings']['obex_root']['hidden']
        else:
            state = 0
            self.struct['bluez']['settings']['obex_enabled']['hidden'] = True
            self.struct['bluez']['settings']['obex_root']['hidden'] = True
        oe.set_service('bluez', options, state)

    @log.log_function()
    def initialize_obex(self, **kwargs):
        if 'listItem' in kwargs:
            self.set_value(kwargs['listItem'])
        options = {}
        if self.struct['bluez']['settings']['obex_enabled']['value'] == '1':
            state = 1
            options['OBEXD_ROOT'] = self.struct['bluez']['settings']['obex_root']['value']
        else:
            state = 0
        oe.set_service('obexd', options, state)

    @log.log_function()
    def idle_timeout(self, **kwargs):
        if 'listItem' in kwargs:
            self.set_value(kwargs['listItem'])
        oe.write_setting('bluetooth', 'idle_timeout', self.struct['bluez']['settings']['idle_timeout']['value'])

    @log.log_function()
    def do_wizard(self):
        oe.winOeMain.set_wizard_title(oe._(32311))

        # Enable samba
        self.struct['samba']['settings']['samba_autostart']['value'] = '1'
        self.initialize_samba()

        if hasattr(self, 'samba'):
            oe.winOeMain.set_wizard_text(f'{oe._(32313)}[CR][CR]{oe._(32312)}')
        else:
            oe.winOeMain.set_wizard_text(oe._(32312))
        oe.winOeMain.set_wizard_button_title(oe._(32316))
        self.set_wizard_buttons()

    @log.log_function()
    def set_wizard_buttons(self):
        if self.struct['ssh']['settings']['ssh_autostart']['value'] == '1':
            oe.winOeMain.set_wizard_radiobutton_1(oe._(32201), self, 'wizard_set_ssh', True)
        else:
            oe.winOeMain.set_wizard_radiobutton_1(oe._(32201), self, 'wizard_set_ssh')
        if not 'hidden' in self.struct['samba']:
            if self.struct['samba']['settings']['samba_autostart']['value'] == '1':
                oe.winOeMain.set_wizard_radiobutton_2(oe._(32200), self, 'wizard_set_samba', True)
            else:
                oe.winOeMain.set_wizard_radiobutton_2(oe._(32200), self, 'wizard_set_samba')

    @log.log_function()
    def wizard_set_ssh(self):
        if self.struct['ssh']['settings']['ssh_autostart']['value'] == '1':
            self.struct['ssh']['settings']['ssh_autostart']['value'] = '0'
        else:
            self.struct['ssh']['settings']['ssh_autostart']['value'] = '1'
        # ssh button does nothing if "ssh" set on kernel commandline
        with open(self.KERNEL_CMD, 'r') as cmd_file:
            cmd_args = cmd_file.read().split(' ')
        if 'ssh' in cmd_args:
            oe.notify('ssh', 'ssh enabled as boot parameter. can not disable')
        self.initialize_ssh()
        self.load_values()
        if self.struct['ssh']['settings']['ssh_autostart']['value'] == '1':
            self.wizard_sshpasswd()
        self.set_wizard_buttons()

    @log.log_function()
    def wizard_set_samba(self):
        if self.struct['samba']['settings']['samba_autostart']['value'] == '1':
            self.struct['samba']['settings']['samba_autostart']['value'] = '0'
        else:
            self.struct['samba']['settings']['samba_autostart']['value'] = '1'
        self.initialize_samba()
        self.load_values()
        self.set_wizard_buttons()

    @log.log_function()
    def wizard_sshpasswd(self):
        SSHresult = False
        while SSHresult == False:
            changeSSH = xbmcDialog.yesno(oe._(32209), oe._(32210), yeslabel=oe._(32213), nolabel=oe._(32214))
            if changeSSH:
                SSHresult = True
            else:
                changeSSHresult = self.do_sshpasswd()
                if changeSSHresult:
                    SSHresult = True
        return

    @log.log_function()
    def do_sshpasswd(self, **kwargs):
        SSHchange = False
        newpwd = xbmcDialog.input(oe._(746))
        if newpwd:
            if newpwd == "libreelec":
                if os.path.isfile('/storage/.cache/shadow'):
                    os.remove('/storage/.cache/shadow')
                shutil.copy2('/usr/cache/shadow', '/storage/.cache/shadow')
                readout3 = "Retype password"
            else:
                ssh = subprocess.Popen(["passwd"], shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=0)
                readout1 = ssh.stdout.readline()
                ssh.stdin.write(f'{newpwd}\n')
                readout2 = ssh.stdout.readline()
                ssh.stdin.write(f'{newpwd}\n')
                readout3 = ssh.stdout.readline()
            if "Bad password" in readout3:
                xbmcDialog.ok(oe._(32220), oe._(32221))
                log.log('Password too weak')
                return
            elif "Retype password" in readout3:
                xbmcDialog.ok(oe._(32222), oe._(32223))
                SSHchange = True
            else:
                xbmcDialog.ok(oe._(32224), oe._(32225))
        else:
            log.log('User cancelled')
        return SSHchange

    def sh_esc_str(self, string):
        escape = ''
        for c in string:
            escape += '\\' + c
        return escape

    def sh_unesc_str(self, string):
        size = len(string)
        if size % 2:
            return string
        if string[0::2] != '\\' * (size // 2):
            return string
        return string[1::2]
