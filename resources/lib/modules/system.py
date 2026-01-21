# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
# Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)
# Copyright (C) 2019-present Team LibreELEC (https://libreelec.tv)

import glob
import os
import re
import shutil
import tarfile
from xml.dom import minidom

import xbmc
import xbmcgui

import hostname
import log
import modules
import oe
import os_tools
import timezone


xbmcDialog = xbmcgui.Dialog()

class system(modules.Module):

    ENABLED = False
    KERNEL_CMD = None
    XBMC_RESET_FILE = None
    LIBREELEC_RESET_FILE = None
    KEYBOARD_INFO = None
    UDEV_KEYBOARD_INFO = None
    NOX_KEYBOARD_INFO = None
    BACKUP_DIRS = None
    BACKUP_FILTER = None
    BACKUP_DESTINATION = None
    RESTORE_DIR = None
    SET_CLOCK_CMD = None
    JOURNALD_CONFIG_FILE = None
    menu = {'1': {
        'name': 32002,
        'menuLoader': 'load_menu',
        'listTyp': 'list',
        'InfoText': 700,
        }}

    @log.log_function()
    def __init__(self, oeMain):
        super().__init__()
        self.keyboard_layouts = False
        self.nox_keyboard_layouts = False
        self.backup_dlg = None
        self.backup_file = None
        self.total_backup_size = 0
        self.done_backup_size = 0
        self.arrVariants = {}
        self.struct = {
            'ident': {
                'order': 1,
                'name': 32189,
                'settings': {
                    'hostname': {
                        'order': 1,
                        'name': 32190,
                        'value': '',
                        'action': 'set_hostname',
                        'type': 'text',
                        'validate': '^([a-zA-Z0-9](?:[a-zA-Z0-9-\.]*[a-zA-Z0-9]))$',
                        'InfoText': 710,
                        },
                    'timezone': {
                        'order': 2,
                        'name': 32420,
                        'value': '',
                        'action': 'set_timezone',
                        'type': 'button',
                        'InfoText': 709,
                        },
                    },
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
            'pinlock': {
                'order': 3,
                'name': 32192,
                'settings': {
                    'pinlock_enable': {
                        'order': 1,
                        'name': 32193,
                        'value': '0',
                        'action': 'init_pinlock',
                        'type': 'bool',
                        'InfoText': 747,
                        },
                    'pinlock_pin': {
                        'order': 2,
                        'name': 32194,
                        'value': '',
                        'action': 'set_pinlock',
                        'type': 'button',
                        'InfoText': 748,
                        'parent': {
                            'entry': 'pinlock_enable',
                            'value': ['1'],
                            },
                        },
                    },
                },
            'backup': {
                'order': 4,
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
                'order': 5,
                'name': 32323,
                'settings': {
                    'xbmc_reset': {
                        'name': 32324,
                        'value': '0',
                        'action': 'reset_soft',
                        'type': 'button',
                        'InfoText': 724,
                        'order': 1,
                        },
                    'oe_reset': {
                        'name': 32325,
                        'value': '0',
                        'action': 'reset_hard',
                        'type': 'button',
                        'InfoText': 725,
                        'order': 2,
                        },
                    },
                },
            'debug': {
                'order': 6,
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
            'journal': {
                'order': 7,
                'name': 32410,
                'settings': {
                    'journal_persistent': {
                        'order': 1,
                        'name': 32411,
                        'value': '0',
                        'action': 'do_journald',
                        'type': 'bool',
                        'InfoText': 32412,
                    },
                    'journal_size': {
                        'order': 2,
                        'name': 32413,
                        'value': '30 MiB',
                        'action': 'do_journald',
                        'type': 'multivalue',
                        'values': [
                            '30 MiB', '60 MiB', '100 MiB',
                            '150 MiB', '200 MiB', '300 MiB'
                        ],
                        'InfoText': 32414,
                        'parent': {
                            'entry': 'journal_persistent',
                            'value': ['1'],
                        },
                    },
                    'journal_rate_limit': {
                        'order': 2,
                        'name': 32415,
                        'value': '1',
                        'action': 'do_journald',
                        'type': 'bool',
                        'InfoText': 32416,
                        'parent': {
                            'entry': 'journal_persistent',
                            'value': ['1'],
                        },
                    },
                },
            },
        }

    @log.log_function()
    def start_service(self):
        self.is_service = True
        self.load_values()
        self.set_keyboard_layout()
        self.set_hw_clock()
        del self.is_service

    @log.log_function()
    def stop_service(self):
        if hasattr(self, 'update_thread'):
            self.update_thread.stop()

    @log.log_function()
    def load_values(self):
        # Keyboard Layout
        (
            arrLayouts,
            arrTypes,
            self.arrVariants,
            ) = self.get_keyboard_layouts()
        if not arrTypes is None:
            self.struct['keyboard']['settings']['KeyboardType']['values'] = arrTypes
            value = oe.read_setting('system', 'KeyboardType')
            if not value is None:
                self.struct['keyboard']['settings']['KeyboardType']['value'] = value
        if not arrLayouts is None:
            self.struct['keyboard']['settings']['KeyboardLayout1']['values'] = arrLayouts
            self.struct['keyboard']['settings']['KeyboardLayout2']['values'] = arrLayouts
            value = oe.read_setting('system', 'KeyboardLayout1')
            if not value is None:
                self.struct['keyboard']['settings']['KeyboardLayout1']['value'] = value
            value = oe.read_setting('system', 'KeyboardVariant1')
            if not value is None:
                self.struct['keyboard']['settings']['KeyboardVariant1']['value'] = value
            value = oe.read_setting('system', 'KeyboardLayout2')
            if not value is None:
                self.struct['keyboard']['settings']['KeyboardLayout2']['value'] = value
            value = oe.read_setting('system', 'KeyboardVariant2')
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
        self.struct['ident']['settings']['hostname']['value'] = hostname.get_hostname()
        # Timezone
        self.struct['ident']['settings']['timezone']['value'] = timezone.get_timezone()
        self.struct['ident']['settings']['timezone']['name'] = f"{oe._(32420)} ({self.struct['ident']['settings']['timezone']['value']})"
        # PIN Lock
        self.struct['pinlock']['settings']['pinlock_enable']['value'] = '1' if oe.PIN.isEnabled() else '0'

        # Journal
        self.get_setting('journal', 'journal_persistent')
        self.get_setting('journal', 'journal_size')
        self.get_setting('journal', 'journal_rate_limit')

    @log.log_function()
    def load_menu(self, focusItem):
        oe.winOeMain.build_menu(self.struct)

    def get_setting(self, group, setting, allowEmpty=False):
        value = oe.read_setting('system', setting)
        if not value is None and not (allowEmpty == False and value == ''):
            self.struct[group]['settings'][setting]['value'] = value

    @log.log_function()
    def set_value(self, listItem):
        self.struct[listItem.getProperty('category')]['settings'][listItem.getProperty('entry')]['value'] = listItem.getProperty('value')
        oe.write_setting('system', listItem.getProperty('entry'), str(listItem.getProperty('value')))

    @log.log_function()
    def set_keyboard_layout(self, listItem=None):
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
            log.log(str(self.struct['keyboard']['settings']['KeyboardLayout1']['value']) + ','
                            + str(self.struct['keyboard']['settings']['KeyboardLayout2']['value']) + ' ' + '-model '
                            + str(self.struct['keyboard']['settings']['KeyboardType']['value']), log.INFO)
            if not os.path.exists(os.path.dirname(self.UDEV_KEYBOARD_INFO)):
                os.makedirs(os.path.dirname(self.UDEV_KEYBOARD_INFO))
            config_file = open(self.UDEV_KEYBOARD_INFO, 'w')
            config_file.write(f"XKBMODEL=\"{self.struct['keyboard']['settings']['KeyboardType']['value']}\"\n")
            config_file.write(f"XKBVARIANT=\"{self.struct['keyboard']['settings']['KeyboardVariant1']['value']}, \
                                             {self.struct['keyboard']['settings']['KeyboardVariant2']['value']}\"\n")
            config_file.write(f"XKBLAYOUT=\"{self.struct['keyboard']['settings']['KeyboardLayout1']['value']}, {self.struct['keyboard']['settings']['KeyboardLayout2']['value']}\"\n")
            config_file.write('XKBOPTIONS="grp:alt_shift_toggle"\n')
            config_file.close()
            parameters = [
                '-display ' + os.environ['DISPLAY'],
                '-layout ' + self.struct['keyboard']['settings']['KeyboardLayout1']['value'] + ',' + self.struct['keyboard']['settings'
                        ]['KeyboardLayout2']['value'],
                '-variant ' + self.struct['keyboard']['settings']['KeyboardVariant1']['value'] + ',' + self.struct['keyboard']['settings'
                        ]['KeyboardVariant2']['value'],
                '-model ' + str(self.struct['keyboard']['settings']['KeyboardType']['value']),
                '-option "grp:alt_shift_toggle"',
                ]
            os_tools.execute('setxkbmap ' + ' '.join(parameters))
        elif self.nox_keyboard_layouts == True:
            parameter = self.struct['keyboard']['settings']['KeyboardLayout1']['value']
            log.log(f'Settings keyboard layout: {parameter}', log.INFO)
            path_to_bmap = None
            for dirpath, dirnames, filenames in os.walk(self.NOX_KEYBOARD_INFO):
                for f in filenames:
                    if f == f'{parameter}.bmap':
                        path_to_bmap = f'{dirpath}/{f}'
                        log.log(f'Found keyboard layout: {path_to_bmap}', log.INFO)
                        break
                if path_to_bmap:
                    break
            if path_to_bmap:
                command = f'loadkmap < {path_to_bmap}'
                log.log(f'Executing {command}', log.INFO)
                os_tools.execute(command)
            else:
                log.log('No keyboard layout found.', log.INFO)

    @log.log_function()
    def set_hostname(self, listItem=None):
        if listItem is not None:
            self.set_value(listItem)
        value = self.struct['ident']['settings']['hostname']['value']
        if value is not None and value != '':
            hostname.set_hostname(value)


    @log.log_function()
    def set_timezone(self, listItem=None):
        timezones = timezone.list_timezones()
        guessed_timezone = timezone.guess_timezone()
        current_timezone = self.struct['ident']['settings']['timezone']['value']
        if current_timezone != 'UTC' and current_timezone in timezones:
            menu_position = timezones.index(current_timezone)
        elif guessed_timezone in timezones:
            menu_position = timezones.index(guessed_timezone)
        else:
            menu_position = 0
        xbmcDialog = xbmcgui.Dialog()
        timezone_select = xbmcDialog.select(heading=oe._(32420), list=timezones, preselect=menu_position)
        log.log(f'timezone_select: {timezone_select}', log.DEBUG)
        if timezone_select > -1:
            listItem = timezones[timezone_select]
            log.log(f'listItem: {listItem}', log.DEBUG)
            self.struct['ident']['settings']['timezone']['value'] = listItem
            self.struct['ident']['settings']['timezone']['name'] = f"{oe._(32420)} ({listItem})"
            log.log(f'Setting timezone to: {timezone}', log.DEBUG)
            timezone.set_timezone(listItem)
        xbmcDialog = None
        del xbmcDialog


    @log.log_function()
    def get_keyboard_layouts(self):
        arrLayouts = []
        arrVariants = {}
        arrTypes = []
        if os.path.exists(self.NOX_KEYBOARD_INFO):
            for layout in glob.glob(f'{self.NOX_KEYBOARD_INFO}/*/*.bmap'):
                if os.path.isfile(layout):
                    arrLayouts.append(layout.split('/')[-1].split('.')[0])
            arrLayouts.sort()
            arrTypes = None
        elif os.path.exists(self.KEYBOARD_INFO):
            objXmlFile = open(self.KEYBOARD_INFO, 'r', encoding='utf-8')
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
        else:
            log.log('No keyboard layouts found)')
            return (None, None, None)
        return (
            arrLayouts,
            arrTypes,
            arrVariants,
            )

    @log.log_function()
    def set_hw_clock(self):
        # does device have an RTC?
        if os.path.exists('/proc/driver/rtc'):
            os_tools.execute(f'{self.SET_CLOCK_CMD} 2>/dev/null')

    @log.log_function()
    def reset_soft(self, listItem=None):
        if self.ask_sure_reset('Soft') == 1:
            open(self.XBMC_RESET_FILE, 'a').close()
            oe.winOeMain.close()
            oe.xbmcm.waitForAbort(1)
            os_tools.execute('/usr/bin/systemctl --no-block reboot')

    @log.log_function()
    def reset_hard(self, listItem=None):
        if self.ask_sure_reset('Hard') == 1:
            open(self.LIBREELEC_RESET_FILE, 'a').close()
            oe.winOeMain.close()
            oe.xbmcm.waitForAbort(1)
            os_tools.execute('/usr/bin/systemctl --no-block reboot')


    @log.log_function()
    def ask_sure_reset(self, part):
        answer = xbmcDialog.yesno(f'{part} Reset', f'{oe._(32326)}\n\n{oe._(32328)}')
        if answer == 1:
            if oe.reboot_counter(30, oe._(32323)) == 1:
                return 1
            else:
                return 0

    @log.log_function()
    def do_backup(self, listItem=None):
        try:
            self.total_backup_size = 1
            self.done_backup_size = 1
            try:
                for directory in self.BACKUP_DIRS:
                    self.get_folder_size(directory)
                log.log(f'Uncompressed backup size: {total_backup_size}', log.DEBUG)
            except:
                pass
            bckDir = xbmcDialog.browse( 0,
                                        oe._(32371),
                                        'files',
                                        '',
                                        False,
                                        False,
                                        self.BACKUP_DESTINATION )
            log.log(f'Directory for backup: {bckDir}', log.INFO)

            if bckDir and os.path.exists(bckDir):
                # free space check
                try:
                    folder_stat = os.statvfs(bckDir)
                    free_space = folder_stat.f_frsize * folder_stat.f_bavail
                    log.log(f'Available free space for backup: {free_space}', log.DEBUG)
                    if self.total_backup_size > free_space:
                        txt = oe.split_dialog_text(oe._(32379))
                        answer = xbmcDialog.ok('Backup', f'{txt[0]}\n{txt[1]}\n{txt[2]}')
                        return 0
                except:
                    log.log('Unable to determine free space available for backup.', log.DEBUG)
                    pass
                self.backup_dlg = xbmcgui.DialogProgress()
                self.backup_dlg.create('LibreELEC', oe._(32375))
                if not os.path.exists(self.BACKUP_DESTINATION):
                    os.makedirs(self.BACKUP_DESTINATION)
                self.backup_file = f'{hostname.get_hostname()}-{oe.timestamp()}.tar'
                log.log(f'Backup file: {bckDir + self.backup_file}', log.INFO)
                tar = tarfile.open(bckDir + self.backup_file, 'w', format=tarfile.GNU_FORMAT)
                for directory in self.BACKUP_DIRS:
                    self.tar_add_folder(tar, directory)
                    if self.backup_dlg is None or self.backup_dlg.iscanceled():
                        break
                tar.close()
                if self.backup_dlg is None or self.backup_dlg.iscanceled():
                    try:
                        os.remove(self.BACKUP_DESTINATION + self.backup_file)
                    except:
                        pass
                else:
                    self.backup_dlg.update(100, oe._(32401))
                os.sync()
        finally:
            # possibly already closed by tar_add_folder if an error occurred
            try:
                self.backup_dlg.close()
            except:
                pass
            self.backup_dlg = None

    @log.log_function()
    def do_restore(self, listItem=None):
            copy_success = 0
            restore_file_path = xbmcDialog.browse( 1,
                                                   oe._(32373),
                                                   'files',
                                                   '',
                                                   False,
                                                   False,
                                                   self.BACKUP_DESTINATION )
            # Do nothing if the dialog is cancelled - path will be the backup destination
            if not os.path.isfile(restore_file_path):
                return
            # file selected that won't trigger busybox's backup restoration
            if not restore_file_path.endswith(('.tar', '.tar.gz', '.tar.bz2', '.tar.xz')):
                log.log(f'Error: Invalid backup file: {restore_file_path}', log.ERROR)
                xbmcDialog.ok(oe._(32373), oe._(32374))
                return

            log.log(f'Restore file: {restore_file_path}', log.INFO)
            restore_file_name = restore_file_path.split('/')[-1]
            if os.path.exists(self.RESTORE_DIR):
                shutil.rmtree(self.RESTORE_DIR)
            os.makedirs(self.RESTORE_DIR)
            folder_stat = os.statvfs(self.RESTORE_DIR)
            file_size = os.path.getsize(restore_file_path)
            free_space = folder_stat.f_frsize * folder_stat.f_bavail
            if free_space > file_size * 2:
                if os.path.exists(self.RESTORE_DIR + restore_file_name):
                    os.remove(self.RESTORE_DIR + restore_file_name)
                if oe.copy_file(restore_file_path, self.RESTORE_DIR + restore_file_name) != None:
                    copy_success = 1
                    log.log('Restore file successfully copied.', log.INFO)
                else:
                    log.log(f'Failed to copy restore file to: {self.RESTORE_DIR}', log.ERROR)
                    if os.path.exists(self.RESTORE_DIR):
                        shutil.rmtree(self.RESTORE_DIR)
            else:
                txt = oe.split_dialog_text(oe._(32379))
                answer = xbmcDialog.ok('Restore', f'{txt[0]}\n{txt[1]}\n{txt[2]}')
            if copy_success == 1:
                txt = oe.split_dialog_text(oe._(32380))
                answer = xbmcDialog.yesno('Restore', f'{txt[0]}\n{txt[1]}\n{txt[2]}')
                if answer == 1:
                    if oe.reboot_counter(10, oe._(32371)) == 1:
                        oe.winOeMain.close()
                        oe.xbmcm.waitForAbort(1)
                        os_tools.execute('/usr/bin/systemctl --no-block reboot')
                else:
                    log.log('User Abort!')
                    if os.path.exists(self.RESTORE_DIR):
                        shutil.rmtree(self.RESTORE_DIR)

    @log.log_function()
    def do_send_system_logs(self, listItem=None):
        self.do_send_logs('/usr/bin/pastekodi')

    @log.log_function()
    def do_send_crash_logs(self, listItem=None):
        self.do_send_logs('/usr/bin/pastecrash')

    @log.log_function()
    def do_send_logs(self, log_cmd):
        paste_dlg = xbmcgui.DialogProgress()
        paste_dlg.create(oe._(32376), oe._(32417))
        result = os_tools.execute(log_cmd, get_result=True)
        if not paste_dlg.iscanceled():
            paste_dlg.close()
            if result:
                link = result.find('http')
                if link != -1:
                    log.log(result[link:], log.WARNING)
                    xbmcDialog.ok(oe._(32376), f'{oe._(32418)} {result[link:]}')
                else:
                    xbmcDialog.ok(oe._(32376), oe._(32419))
            else:
                xbmcDialog.ok(oe._(32376), oe._(32419))

    @log.log_function()
    def tar_add_folder(self, tar, folder):
        try:
            print_folder = log.asciify(folder)
            try:
                fsr = os.lstat(folder)
            except:
                pass
            else:
                if fsr.st_mode != 0o40755 or fsr.st_uid or fsr.st_gid:
                    tar.add(folder, recursive=False)
            for item in os.listdir(folder):
                if item == self.backup_file:
                    continue
                if self.backup_dlg.iscanceled():
                    return
                itempath = os.path.join(folder, item)
                if itempath in self.BACKUP_FILTER:
                    continue
                elif os.path.islink(itempath):
                    tar.add(itempath)
                elif os.path.ismount(itempath):
                    tar.add(itempath, recursive=False)
                elif os.path.isdir(itempath):
                    if os.listdir(itempath) == []:
                        tar.add(itempath)
                    else:
                        self.tar_add_folder(tar, itempath)
                        if self.backup_dlg is None:
                            return
                else:
                    self.done_backup_size += os.path.getsize(itempath)
                    log.log(f'Adding to backup: {log.asciify(itempath)}', log.DEBUG)
                    tar.add(itempath)
                    if hasattr(self, 'backup_dlg'):
                        progress = round(1.0 * self.done_backup_size / self.total_backup_size * 100)
                        self.backup_dlg.update(int(progress), f'{print_folder}\n{log.asciify(item)}')
        except:
            self.backup_dlg.close()
            self.backup_dlg = None
            xbmcDialog.ok(oe._(32371), oe._(32402))
            raise

    @log.log_function()
    def get_folder_size(self, folder):
        for item in os.listdir(folder):
            itempath = os.path.join(folder, item)
            if itempath in self.BACKUP_FILTER or os.path.islink(itempath):
                continue
            elif os.path.isfile(itempath):
                self.total_backup_size += os.path.getsize(itempath)
            elif os.path.ismount(itempath):
                continue
            elif os.path.isdir(itempath):
                self.get_folder_size(itempath)

    @log.log_function()
    def init_pinlock(self, listItem=None):
        if not listItem == None:
            self.set_value(listItem)
        if self.struct['pinlock']['settings']['pinlock_enable']['value'] == '1':
            oe.PIN.enable()
        else:
            oe.PIN.disable()
        if oe.PIN.isEnabled() and oe.PIN.isSet() == False:
            self.set_pinlock()

    @log.log_function()
    def set_pinlock(self, listItem=None):
        newpin = xbmcDialog.input(oe._(32226), type=xbmcgui.INPUT_NUMERIC)
        if len(newpin) == 4 :
           newpinConfirm = xbmcDialog.input(oe._(32227), type=xbmcgui.INPUT_NUMERIC)
           if newpin != newpinConfirm:
               xbmcDialog.ok(oe._(32228), oe._(32229))
           else:
               oe.PIN.set(newpin)
               xbmcDialog.ok(oe._(32230), f'{oe._(32231)}\n\n{newpin}')
        else:
            xbmcDialog.ok(oe._(32232), oe._(32229))
        if oe.PIN.isSet() == False:
            self.struct['pinlock']['settings']['pinlock_enable']['value'] = '0'
            oe.PIN.disable()

    @log.log_function()
    def do_journald(self, listItem=None):
        if not listItem == None:
            self.set_value(listItem)
            if self.struct['journal']['settings']['journal_persistent']['value'] == '0':
                if os.path.isfile(self.JOURNALD_CONFIG_FILE):
                    os.remove(self.JOURNALD_CONFIG_FILE)
            else:
                size = self.struct['journal']['settings']['journal_size']['value'].replace(' MiB', 'M')
                journal_config = f"""\
# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2021-present Team LibreELEC (https://libreelec.tv)

# This file is generated automatically. Do not modify.

[Journal]
SystemMaxUse={size}
MaxRetentionSec=0
{'RateLimitInterval=0' if self.struct['journal']['settings']['journal_rate_limit']['value'] == '1' else ''}
{'RateLimitBurst=0' if self.struct['journal']['settings']['journal_rate_limit']['value'] == '1' else ''}
"""
                # remove trailing whitespace, then add one new line
                journal_config = f'{journal_config.rstrip()}{chr(10)}'
                with open(self.JOURNALD_CONFIG_FILE, 'w') as config_file:
                    config_file.write(journal_config)

    @log.log_function()
    def do_wizard(self):
        oe.winOeMain.set_wizard_title(oe._(32003))
        oe.winOeMain.set_wizard_text(oe._(32304))
        oe.winOeMain.set_wizard_button_title(oe._(32308))
        oe.winOeMain.set_wizard_button_1(self.struct['ident']['settings']['hostname']['value'], self, 'wizard_set_hostname')

    @log.log_function()
    def wizard_set_hostname(self):
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
            oe.winOeMain.getControl(1401).setLabel(self.struct['ident']['settings']['hostname']['value'])
