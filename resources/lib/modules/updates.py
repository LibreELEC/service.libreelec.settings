# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
# Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)
# Copyright (C) 2018-present Team LibreELEC (https://libreelec.tv)

import json
import os
import re
import shutil
import tempfile
import threading
import time
from datetime import datetime
from functools import cmp_to_key

import xbmc
import xbmcgui

import log
import modules
import oe
import os_tools


class updates(modules.Module):

    ENABLED = False
    KERNEL_CMD = None
    UPDATE_REQUEST_URL = None
    UPDATE_DOWNLOAD_URL = None
    LOCAL_UPDATE_DIR = None
    menu = {'2': {
        'name': 32005,
        'menuLoader': 'load_menu',
        'listTyp': 'list',
        'InfoText': 707,
    }}
    struct = {
        'update': {
            'order': 1,
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
                'SubmitStats': {
                    'name': 32021,
                    'value': '1',
                    'action': 'set_value',
                    'type': 'bool',
                    'InfoText': 772,
                    'order': 2,
                },
                'UpdateNotify': {
                    'name': 32365,
                    'value': '1',
                    'action': 'set_value',
                    'type': 'bool',
                    'InfoText': 715,
                    'order': 3,
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
                    'order': 4,
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
                    'order': 5,
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
                    'order': 6,
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
                    'order': 7,
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
                    'order': 8,
                },
                'Build': {
                    'name': 32020,
                    'value': '',
                    'action': 'do_manual_update',
                    'type': 'button',
                    'parent': {
                            'entry': 'AutoUpdate',
                        'value': ['manual'],
                    },
                    'InfoText': 770,
                    'order': 9,
                },
            },
        },
        'rpieeprom': {
            'order': 2,
            'name': 32022,
            'settings': {
                'bootloader': {
                    'name': 'dummy',
                    'value': '',
                    'action': 'set_rpi_bootloader',
                    'type': 'bool',
                    'InfoText': 32025,
                    'order': 1,
                },
                'vl805': {
                    'name': 32026,
                    'value': '',
                    'action': 'set_rpi_vl805',
                    'type': 'bool',
                    'InfoText': 32027,
                    'order': 2,
                },
            },
        },
    }

    @log.log_function()
    def __init__(self, oeMain):
        super().__init__()
        self.keyboard_layouts = False
        self.nox_keyboard_layouts = False
        self.last_update_check = 0
        self.arrVariants = {}

    @log.log_function()
    def start_service(self):
            self.is_service = True
            self.load_values()
            self.set_auto_update()
            del self.is_service

    @log.log_function()
    def stop_service(self):
        if hasattr(self, 'update_thread'):
            self.update_thread.stop()

    @log.log_function()
    def do_init(self):
        pass

    @log.log_function()
    def exit(self):
        pass

    @log.log_function()
    def lchop(self, s, prefix):
        """Remove prefix from string."""
        # TODO usage may be replaced by .removeprefix() in python >=3.9
        if prefix and s.startswith(prefix):
            return s[len(prefix):]
        return s

    @log.log_function()
    def rchop(self, s, suffix):
        """Remove suffix from string."""
        # TODO usage may be replaced by .removesuffix() in python >=3.9
        if suffix and s.endswith(suffix):
            return s[:-len(suffix)]
        return s

    # Identify connected GPU card (card0, card1 etc.)
    @log.log_function()
    def get_gpu_card(self):
        for root, dirs, files in os.walk("/sys/class/drm", followlinks=False):
            for dir in dirs:
                try:
                    with open(os.path.join(root, dir, 'status'), 'r') as infile:
                        for line in [x for x in infile if x.replace('\n', '') == 'connected']:
                            return dir.split("-")[0]
                except:
                    pass
            break
        return 'card0'

    # Return driver name, eg. 'i915', 'i965', 'nvidia', 'nvidia-legacy', 'amdgpu', 'radeon', 'vmwgfx', 'virtio-pci' etc.
    @log.log_function()
    def get_hardware_flags_x86_64(self):
        gpu_props = {}
        gpu_driver = ""
        gpu_card = self.get_gpu_card()
        log.log(f'Using card: {gpu_card}', log.DEBUG)
        gpu_path = os_tools.execute(f'/usr/bin/udevadm info --name=/dev/dri/{gpu_card} --query path 2>/dev/null', get_result=True, output_err_msg=False).replace('\n','')
        log.log(f'gpu path: {gpu_path}', log.DEBUG)
        if gpu_path:
            drv_path = os.path.dirname(os.path.dirname(gpu_path))
            props = os_tools.execute(f'/usr/bin/udevadm info --path={drv_path} --query=property 2>/dev/null', get_result=True, output_err_msg=False)
            if props:
                for key, value in [x.strip().split('=') for x in props.strip().split('\n')]:
                    gpu_props[key] = value
            log.log(f'gpu props: {gpu_props}', log.DEBUG)
            gpu_driver = gpu_props.get("DRIVER", "")
        if not gpu_driver:
            gpu_driver = os_tools.execute('lspci -k | grep -m1 -A999 "VGA compatible controller" | grep -m1 "Kernel driver in use" | cut -d" " -f5', get_result=True).replace('\n','')
        if gpu_driver == 'nvidia' and os.path.realpath('/var/lib/nvidia_drv.so').endswith('nvidia-legacy_drv.so'):
            gpu_driver = 'nvidia-legacy'
        log.log(f'gpu driver: {gpu_driver}', log.DEBUG)
        return gpu_driver if gpu_driver else "unknown"

    @log.log_function()
    def get_hardware_flags_dtflag(self):
        if os.path.exists('/usr/bin/dtflag'):
            dtflag = os_tools.execute('/usr/bin/dtflag', get_result=True).rstrip('\x00\n')
        else:
            dtflag = "unknown"
        log.log(f'ARM board: {dtflag}', log.DEBUG)
        return dtflag

    @log.log_function()
    def get_hardware_flags(self):
        if oe.PROJECT == "Generic":
            return self.get_hardware_flags_x86_64()
        elif oe.ARCHITECTURE.split('.')[1] in ['aarch64', 'arm' ]:
            return self.get_hardware_flags_dtflag()
        else:
            log.log(f'Project is {oe.PROJECT}, no hardware flag available', log.DEBUG)
            return ''

    @log.log_function()
    def load_values(self):
        # Hardware flags
        self.hardware_flags = self.get_hardware_flags()
        log.log(f'loaded hardware_flag {self.hardware_flags}', log.DEBUG)

        # AutoUpdate
        value = oe.read_setting('updates', 'AutoUpdate')
        if value:
            self.struct['update']['settings']['AutoUpdate']['value'] = value
        value = oe.read_setting('updates', 'SubmitStats')
        if value:
            self.struct['update']['settings']['SubmitStats']['value'] = value
        value = oe.read_setting('updates', 'UpdateNotify')
        if value:
            self.struct['update']['settings']['UpdateNotify']['value'] = value
        if os.path.isfile(f'{self.LOCAL_UPDATE_DIR}/SYSTEM'):
            self.update_in_progress = True

        # Manual Update
        value = oe.read_setting('updates', 'Channel')
        if value:
            self.struct['update']['settings']['Channel']['value'] = value
        value = oe.read_setting('updates', 'ShowCustomChannels')
        if value:
            self.struct['update']['settings']['ShowCustomChannels']['value'] = value

        value = oe.read_setting('updates', 'CustomChannel1')
        if value:
            self.struct['update']['settings']['CustomChannel1']['value'] = value
        value = oe.read_setting('updates', 'CustomChannel2')
        if value:
            self.struct['update']['settings']['CustomChannel2']['value'] = value
        value = oe.read_setting('updates', 'CustomChannel3')
        if value:
            self.struct['update']['settings']['CustomChannel3']['value'] = value

        self.update_json = self.build_json()

        self.struct['update']['settings']['Channel']['values'] = self.get_channels()
        self.struct['update']['settings']['Build']['values'] = self.get_available_builds()

        # RPi4/RPi400 EEPROM updating
        if config.RPI_DEVICE_TYPE in ['11', '13']:
            self.rpi_flashing_state = self.get_rpi_flashing_state()
            if self.rpi_flashing_state['incompatible']:
                self.struct['rpieeprom']['hidden'] = 'true'
            else:
                self.struct['rpieeprom']['settings']['bootloader']['value'] = self.get_rpi_eeprom('BOOTLOADER')
                self.struct['rpieeprom']['settings']['bootloader']['name'] = f"{oe._(32024)} ({self.rpi_flashing_state['bootloader']['state']})"
                self.struct['rpieeprom']['settings']['vl805']['value'] = self.get_rpi_eeprom('VL805')
                self.struct['rpieeprom']['settings']['vl805']['name'] = f"{oe._(32026)} ({self.rpi_flashing_state['vl805']['state']})"
        else:
            self.struct['rpieeprom']['hidden'] = 'true'

    @log.log_function()
    def load_menu(self, focusItem):
        oe.winOeMain.build_menu(self.struct)

    @log.log_function()
    def set_value(self, listItem):
        self.struct[listItem.getProperty('category')]['settings'][listItem.getProperty('entry')]['value'] = listItem.getProperty('value')
        oe.write_setting('updates', listItem.getProperty('entry'), str(listItem.getProperty('value')))

    @log.log_function()
    def set_auto_update(self, listItem=None):
        if listItem:
            self.set_value(listItem)
        if not hasattr(self, 'update_disabled'):
            if hasattr(self, 'update_thread'):
                self.update_thread.wait_evt.set()
            else:
                self.update_thread = updateThread(oe)
                self.update_thread.start()
            log.log(str(self.struct['update']['settings']['AutoUpdate']['value']), log.INFO)

    @log.log_function()
    def set_channel(self, listItem=None):
        if listItem:
            self.set_value(listItem)
        self.struct['update']['settings']['Build']['values'] = self.get_available_builds()

    @log.log_function()
    def set_custom_channel(self, listItem=None):
        if listItem:
            self.set_value(listItem)
        self.update_json = self.build_json()
        self.struct['update']['settings']['Channel']['values'] = self.get_channels()
        if self.struct['update']['settings']['Channel']['values']:
            if self.struct['update']['settings']['Channel']['value'] not in self.struct['update']['settings']['Channel']['values']:
                self.struct['update']['settings']['Channel']['value'] = None
        self.struct['update']['settings']['Build']['values'] = self.get_available_builds()

    @log.log_function()
    def custom_sort_train(self, a, b):
        a_items = a.split('-')
        b_items = b.split('-')

        a_builder = a_items[0]
        b_builder = b_items[0]

        if (a_builder == b_builder):
          try:
            a_float = float(a_items[1])
          except:
            log.log(f"invalid channel name: '{a}'", log.WARNING)
            a_float = 0
          try:
            b_float = float(b_items[1])
          except:
            log.log(f"invalid channel name: '{b}'", log.WARNING)
            b_float = 0
          return (b_float - a_float)
        elif (a_builder < b_builder):
          return -1
        elif (a_builder > b_builder):
          return +1

    @log.log_function()
    def get_channels(self):
        channels = []
        log.log(str(self.update_json), log.DEBUG)
        if self.update_json:
            for channel in self.update_json:
                # filter versions older than current; just add when unknown
                try:
                    channel_version = channel.split('-')[1]
                except IndexError:
                    channel_version = False
                if channel_version and channel_version.replace('.','',1).isdigit():
                    channel_version = float(channel_version)
                else:
                    channel_version = False
                if channel_version:
                    if float(oe.VERSION_ID) <= channel_version:
                        channels.append(channel)
                else:
                    channels.append(channel)
        return sorted(list(set(channels)), key=cmp_to_key(self.custom_sort_train))

    @log.log_function()
    def do_manual_update(self, listItem=None):
        self.struct['update']['settings']['Build']['value'] = ''
        update_json = self.build_json(notify_error=True)
        if not update_json:
            return
        self.update_json = update_json
        builds = self.get_available_builds()
        self.struct['update']['settings']['Build']['values'] = builds
        xbmcDialog = xbmcgui.Dialog()
        buildSel = xbmcDialog.select(oe._(32020), builds)
        if buildSel > -1:
            listItem = builds[buildSel]
            self.struct['update']['settings']['Build']['value'] = listItem
            channel = self.struct['update']['settings']['Channel']['value']
            regex = re.compile(self.update_json[channel]['prettyname_regex'])
            longname = '-'.join([oe.DISTRIBUTION, oe.ARCHITECTURE, oe.VERSION])
            if regex.search(longname):
                version = regex.findall(longname)[0]
            else:
                version = oe.VERSION
            if self.struct['update']['settings']['Build']['value']:
                self.update_file = self.update_json[self.struct['update']['settings']['Channel']['value']]['url'] + self.get_available_builds(self.struct['update']['settings']['Build']['value'])
                message = f"{oe._(32188)}: {version}\n{oe._(32187)}: {self.struct['update']['settings']['Build']['value']}\n{oe._(32180)}"
                answer = xbmcDialog.yesno('LibreELEC Update', message)
                xbmcDialog = None
                del xbmcDialog
                if answer:
                    self.update_in_progress = True
                    self.do_autoupdate()
            self.struct['update']['settings']['Build']['value'] = ''

    @log.log_function()
    def get_json(self, url=None):
        """Download and extract data from a releases.json file. Complete the URL if necessary."""
        if not url:
            url = self.UPDATE_DOWNLOAD_URL % ('releases', 'releases.json')
        if not url.startswith(('http://', 'https://', 'file://')):
            url = f'https://{url}'
        if not url.endswith('.json'):
            url = f'{url}/releases.json'
        data = oe.load_url(url)
        return json.loads(data) if data else None

    @log.log_function()
    def build_json(self, notify_error=False):
        update_json = self.get_json()
        if self.struct['update']['settings']['ShowCustomChannels']['value'] == '1':
            custom_urls = []
            for i in 1,2,3:
                custom_urls.append(self.struct['update']['settings'][f'CustomChannel{str(i)}']['value'])
            for custom_url in custom_urls:
                if custom_url:
                    custom_update_json = self.get_json(custom_url)
                    if custom_update_json:
                        for channel in custom_update_json:
                            update_json[channel] = custom_update_json[channel]
                    elif notify_error:
                        ok_window = xbmcgui.Dialog()
                        answer = ok_window.ok(oe._(32191), f'Custom URL is invalid, or currently inaccessible.\n\n{custom_url}')
                        if not answer:
                            return
        return update_json

    @log.log_function()
    def get_available_builds(self, shortname=None):
        """Parse a releases.json file. What it returns depends on how it's called:

        If called with an argument (a user selected 'shortname' of a build), then it returns the build's
        full name, with the directory subpath of its location prepended to the string when present.

        If called without an argument, return a list of compatible builds with the running image.
        """

        def pretty_filename(s):
            """Make filenames prettier to users."""
            s = self.lchop(s, f'{oe.DISTRIBUTION}-{oe.ARCHITECTURE}-')
            s = self.rchop(s, '.tar')
            s = self.rchop(s, '.img.gz')
            return s

        channel = self.struct['update']['settings']['Channel']['value']
        update_files = []
        build = ''
        break_loop = False
        if self.update_json and channel and channel in self.update_json:
            regex = re.compile(self.update_json[channel]['prettyname_regex'])
            if oe.ARCHITECTURE in self.update_json[channel]['project']:
                for i in sorted(self.update_json[channel]['project'][oe.ARCHITECTURE]['releases'], key=int, reverse=True):
                    if shortname:
                        # check tarballs, then images, then uboot images for matching file; add subpath if key is present
                        if 'file' in self.update_json[channel]['project'][oe.ARCHITECTURE]['releases'][i]:
                            build = self.update_json[channel]['project'][oe.ARCHITECTURE]['releases'][i]['file']['name']
                            if shortname in build:
                                if 'subpath' in self.update_json[channel]['project'][oe.ARCHITECTURE]['releases'][i]['file']:
                                    build = f"{self.update_json[channel]['project'][oe.ARCHITECTURE]['releases'][i]['file']['subpath']}/{build}"
                                break
                        if 'image' in self.update_json[channel]['project'][oe.ARCHITECTURE]['releases'][i]:
                            build = self.update_json[channel]['project'][oe.ARCHITECTURE]['releases'][i]['image']['name']
                            if shortname in build:
                                if 'subpath' in self.update_json[channel]['project'][oe.ARCHITECTURE]['releases'][i]['image']:
                                    build = f"{self.update_json[channel]['project'][oe.ARCHITECTURE]['releases'][i]['image']['subpath']}/{build}"
                                break
                        if 'uboot' in self.update_json[channel]['project'][oe.ARCHITECTURE]['releases'][i]:
                            for uboot_image_data in self.update_json[channel]['project'][oe.ARCHITECTURE]['releases'][i]['uboot']:
                                build = uboot_image_data['name']
                                if shortname in build:
                                    if 'subpath' in uboot_image_data:
                                        build = f"{uboot_image_data['subpath']}/{build}"
                                    break_loop = True
                                    break
                            if break_loop:
                                break
                    else:
                        matches = []
                        try:
                            matches = regex.findall(self.update_json[channel]['project'][oe.ARCHITECTURE]['releases'][i]['file']['name'])
                        except KeyError:
                            pass
                        if matches:
                            update_files.append(matches[0])
                        else:
                            # The same release could have tarballs and images. Prioritize tarball in response.
                            # images and uboot images in same release[i] entry are mutually exclusive.
                            if 'file' in self.update_json[channel]['project'][oe.ARCHITECTURE]['releases'][i]:
                                update_files.append(pretty_filename(self.update_json[channel]['project'][oe.ARCHITECTURE]['releases'][i]['file']['name']))
                                continue
                            if 'image' in self.update_json[channel]['project'][oe.ARCHITECTURE]['releases'][i]:
                                update_files.append(pretty_filename(self.update_json[channel]['project'][oe.ARCHITECTURE]['releases'][i]['image']['name']))
                                continue
                            if 'uboot' in self.update_json[channel]['project'][oe.ARCHITECTURE]['releases'][i]:
                                for uboot_image_data in self.update_json[channel]['project'][oe.ARCHITECTURE]['releases'][i]['uboot']:
                                    update_files.append(pretty_filename(uboot_image_data['name']))

        return build if build else update_files

    @log.log_function()
    def check_updates_v2(self, force=False):
        if hasattr(self, 'update_in_progress'):
            log.log('Update in progress (exit)', log.DEBUG)
            return
        if self.struct['update']['settings']['SubmitStats']['value'] == '1':
            systemid = oe.SYSTEMID
        else:
            systemid = "NOSTATS"
        if oe.BUILDER_VERSION:
            version = oe.BUILDER_VERSION
        else:
            version = oe.VERSION
        url = f'{self.UPDATE_REQUEST_URL}?i={oe.url_quote(systemid)}&d={oe.url_quote(oe.DISTRIBUTION)}&pa={oe.url_quote(oe.ARCHITECTURE)}&v={oe.url_quote(version)}&f={oe.url_quote(self.hardware_flags)}'
        if oe.BUILDER_NAME:
           url += f'&b={oe.url_quote(oe.BUILDER_NAME)}'

        log.log(f'URL: {url}', log.DEBUG)
        update_json = oe.load_url(url)
        log.log(f'RESULT: {repr(update_json)}', log.DEBUG)
        if update_json:
            update_json = json.loads(update_json)
            self.last_update_check = time.time()
            if 'update' in update_json['data'] and 'folder' in update_json['data']:
                self.update_file = self.UPDATE_DOWNLOAD_URL % (update_json['data']['folder'], update_json['data']['update'])
                if self.struct['update']['settings']['UpdateNotify']['value'] == '1':
                    # update available message
                    oe.notify(oe._(32363), oe._(32364))
                if self.struct['update']['settings']['AutoUpdate']['value'] == 'auto' and force == False:
                    self.update_in_progress = True
                    self.do_autoupdate(None, True)

    @log.log_function()
    def do_autoupdate(self, listItem=None, silent=False):
        if hasattr(self, 'update_file'):
            if not os.path.exists(self.LOCAL_UPDATE_DIR):
                os.makedirs(self.LOCAL_UPDATE_DIR)
            downloaded = oe.download_file(self.update_file, oe.TEMP + 'update_file', silent)
            if downloaded:
                self.update_file = self.update_file.split('/')[-1]
                if self.struct['update']['settings']['UpdateNotify']['value'] == '1':
                    # update download complete message
                    oe.notify(oe._(32363), oe._(32366))
                shutil.move(oe.TEMP + 'update_file', self.LOCAL_UPDATE_DIR + self.update_file)
                os.sync()
                if silent == False:
                    oe.winOeMain.close()
                    oe.xbmcm.waitForAbort(1)
                    os_tools.execute('/usr/bin/systemctl --no-block reboot')
            else:
                delattr(self, 'update_in_progress')

    def get_rpi_flashing_state(self):
        try:
            log.log('enter_function', log.DEBUG)

            jdata = {
                        'EXITCODE': 'EXIT_FAILED',
                        'BOOTLOADER_CURRENT': 0, 'BOOTLOADER_LATEST': 0,
                        'VL805_CURRENT': '', 'VL805_LATEST': ''
                    }

            state = {
                        'incompatible': True,
                        'bootloader': {'state': '', 'current': 'unknown', 'latest': 'unknown'},
                        'vl805': {'state': '', 'current': 'unknown', 'latest': 'unknown'}
                    }

            with tempfile.NamedTemporaryFile(mode='r', delete=True) as machine_out:
                console_output = os_tools.execute(f'/usr/bin/.rpi-eeprom-update.real -j -m "{machine_out.name}"', get_result=True).split('\n')
                if os.path.getsize(machine_out.name) != 0:
                    state['incompatible'] = False
                    jdata = json.load(machine_out)

            log.log(f'console output: {console_output}', log.DEBUG)
            log.log(f'json values: {jdata}', log.DEBUG)

            if jdata['BOOTLOADER_CURRENT'] != 0:
                state['bootloader']['current'] = datetime.utcfromtimestamp(jdata['BOOTLOADER_CURRENT']).strftime('%Y-%m-%d')

            if jdata['BOOTLOADER_LATEST'] != 0:
                state['bootloader']['latest'] = datetime.utcfromtimestamp(jdata['BOOTLOADER_LATEST']).strftime('%Y-%m-%d')

            if jdata['VL805_CURRENT']:
                state['vl805']['current'] = jdata['VL805_CURRENT']

            if jdata['VL805_LATEST']:
                state['vl805']['latest'] = jdata['VL805_LATEST']

            if jdata['EXITCODE'] in ['EXIT_SUCCESS', 'EXIT_UPDATE_REQUIRED']:
                if jdata['BOOTLOADER_LATEST'] > jdata['BOOTLOADER_CURRENT']:
                    state['bootloader']['state'] = oe._(32028) % (state['bootloader']['current'], state['bootloader']['latest'])
                else:
                    state['bootloader']['state'] = oe._(32029) % state['bootloader']['current']

                if jdata['VL805_LATEST'] and jdata['VL805_LATEST'] > jdata['VL805_CURRENT']:
                    state['vl805']['state'] = oe._(32028) % (state['vl805']['current'], state['vl805']['latest'])
                else:
                    state['vl805']['state'] = oe._(32029) % state['vl805']['current']

            log.log(f'state: {state}', log.DEBUG)
            log.log('exit_function', log.DEBUG)
            return state
        except Exception as e:
            log.log(f'ERROR: ({repr(e)})')
            return {'incompatible': True}

    @log.log_function()
    def get_rpi_eeprom(self, device):
        values = []
        if os.path.exists(self.RPI_FLASHING_TRIGGER):
            with open(self.RPI_FLASHING_TRIGGER, 'r') as trigger:
                values = trigger.read().split('\n')
        log.log(f'values: {values}', log.DEBUG)
        return 'true' if (f'{device}="yes"') in values else 'false'

    @log.log_function()
    def set_rpi_eeprom(self):
        bootloader = (self.struct['rpieeprom']['settings']['bootloader']['value'] == 'true')
        vl805 = (self.struct['rpieeprom']['settings']['vl805']['value'] == 'true')
        log.log(f'states: [{bootloader}], [{vl805}]', log.DEBUG)
        if bootloader or vl805:
            values = []
            values.append('BOOTLOADER="%s"' % ('yes' if bootloader else 'no'))
            values.append('VL805="%s"' % ('yes' if vl805 else 'no'))
            with open(self.RPI_FLASHING_TRIGGER, 'w') as trigger:
                trigger.write('\n'.join(values))
        else:
            if os.path.exists(self.RPI_FLASHING_TRIGGER):
                os.remove(self.RPI_FLASHING_TRIGGER)

    @log.log_function()
    def set_rpi_bootloader(self, listItem):
        value = 'false'
        if listItem.getProperty('value') == 'true':
            if xbmcgui.Dialog().yesno('Update RPi Bootloader', f'{oe._(32023)}\n\n{oe._(32326)}'):
                value = 'true'
        self.struct[listItem.getProperty('category')]['settings'][listItem.getProperty('entry')]['value'] = value
        self.set_rpi_eeprom()

    @log.log_function()
    def set_rpi_vl805(self, listItem):
        value = 'false'
        if listItem.getProperty('value') == 'true':
            if xbmcgui.Dialog().yesno('Update RPi USB3 Firmware', f'{oe._(32023)}\n\n{oe._(32326)}'):
                value = 'true'
        self.struct[listItem.getProperty('category')]['settings'][listItem.getProperty('entry')]['value'] = value
        self.set_rpi_eeprom()

class updateThread(threading.Thread):

    def __init__(self, oeMain):
        threading.Thread.__init__(self)
        self.stopped = False
        self.wait_evt = threading.Event()
        log.log('updateThread Started', log.INFO)

    @log.log_function()
    def stop(self):
        self.stopped = True
        self.wait_evt.set()

    @log.log_function()
    def run(self):
        while self.stopped == False:
            if not xbmc.Player().isPlaying():
                oe.dictModules['updates'].check_updates_v2()
            if not hasattr(oe.dictModules['updates'], 'update_in_progress'):
                self.wait_evt.wait(21600)
            else:
                # TODO this should check if update notifications are enabled too?
                if not xbmc.Player().isPlaying():
                    # update available message
                    oe.notify(oe._(32363), oe._(32364))
                self.wait_evt.wait(3600)
            self.wait_evt.clear()
        log.log('updateThread Stopped', log.INFO)
