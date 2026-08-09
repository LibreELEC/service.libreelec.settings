# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
# Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)
# Copyright (C) 2019-present Team LibreELEC (https://libreelec.tv)

import json
import subprocess
import threading
import time
import weakref

import xbmc
import xbmcgui
from dbussy import DBusError

import dbus_bluez
import dbus_obex
import hostname
import log
import modules
import oe
import oeWindows

BT_DEVICES_LIST_REFRESH_INTERVAL_SECONDS = 5
BT_MANUAL_DISCOVERY_TIMEOUT_SECONDS = 15
BT_AUDIO_SINK_UUID = '0000110b-0000-1000-8000-00805f9b34fb'
BT_AUDIO_AUTO_CONNECT_INTERVALS_SECONDS = (5, 10, 20, 40, 80)
BT_LAST_AUDIO_DEVICE_SETTING = 'last_audio_device'
BT_AUDIO_WATCHDOG_SETTING = 'audio_watchdog'
BT_AUDIO_RECOVERY_MONITOR_SECONDS = 90
BT_AUDIO_RECOVERY_SAMPLE_INTERVAL_SECONDS = 0.5
BT_AUDIO_RECOVERY_BAD_LATENCY_DELTA_USEC = 9000
BT_AUDIO_RECOVERY_BAD_SAMPLES = 2
BT_AUDIO_RECOVERY_STABLE_LATENCY_DELTA_USEC = 1000
BT_AUDIO_RECOVERY_STABLE_SAMPLES = 4
BT_AUDIO_PROFILE_RESET_PAUSE_SECONDS = 2
BT_AUDIO_WATCHDOG_SAMPLE_INTERVAL_SECONDS = 10
BT_AUDIO_WATCHDOG_BAD_SAMPLES = 2
BT_AUDIO_WATCHDOG_STABLE_SAMPLES = 2
BT_AUDIO_WATCHDOG_RECOVERY_COOLDOWN_SECONDS = 600
BT_AUDIO_WATCHDOG_MAX_RESETS_PER_CONNECTION = 3


class bluetooth(modules.Module):

    menu = {'6': {
        'name': 32331,
        'menuLoader': 'menu_connections',
        'listTyp': 'btlist',
        'InfoText': 704,
        }}
    ENABLED = False
    OBEX_ROOT = None
    OBEX_DAEMON = None
    BLUETOOTH_DAEMON = None
    D_OBEXD_ROOT = None

    # type 1=int, 2=string, 3=array, 4=bool
    properties = {
        0: {
            'type': 4,
            'value': 'Paired',
        },
        1: {
            'type': 2,
            'value': 'Adapter',
        },
        2: {
            'type': 4,
            'value': 'Connected',
        },
        3: {
            'type': 2,
            'value': 'Address',
        },
        5: {
            'type': 1,
            'value': 'Class',
        },
        6: {
            'type': 4,
            'value': 'Trusted',
        },
        7: {
            'type': 2,
            'value': 'Icon',
        },
    }

    @log.log_function()
    def __init__(self, oeMain):
        super().__init__()
        self.oe = oeMain
        self.visible = False
        self.listItems = {}
        self.dbusBluezAdapter = None
        self.discovering = False
        self.manual_discovery_deadline = 0
        self.found_devices = frozenset()
        self.audio_reset_threads = {}
        self.audio_connected_paths = set()
        self.audio_recovery_lock = threading.Lock()
        self.audio_recovery_threads = {}
        self.audio_profile_reset_guards = {}

    @log.log_function()
    def do_init(self):
        self.visible = True

    @log.log_function()
    def start_service(self):
        self.bluez_agent = Bluez_Agent(self)
        self.obex_agent = Obex_Agent(self)
        self.bluez_listener = Bluez_Listener(self)
        self.obex_listener = Obex_Listener(self)
        self.find_adapter()
        for path, properties in (self.get_devices() or {}).items():
            self.finalize_audio_connection(path, properties)
        self.audio_auto_connect_thread = audioAutoConnectThread(self)
        self.audio_auto_connect_thread.start()

    @log.log_function()
    def stop_service(self):
        if hasattr(self, 'audio_auto_connect_thread'):
            self.audio_auto_connect_thread.stop()
            self.audio_auto_connect_thread.join()
            del self.audio_auto_connect_thread
        for thread in self.audio_reset_threads.values():
            thread.stop()
        for thread in self.audio_reset_threads.values():
            thread.join()
        self.audio_reset_threads.clear()
        for thread in self.audio_recovery_threads.values():
            thread.stop()
        for thread in self.audio_recovery_threads.values():
            thread.join()
        self.audio_recovery_threads.clear()
        self.audio_connected_paths.clear()
        self.audio_profile_reset_guards.clear()
        if hasattr(self, 'dbusBluezAdapter') and self.dbusBluezAdapter is not None:
            self.bluez_agent.unregister_agent()
        if hasattr(self, 'discovery_thread'):
            try:
                self.discovery_thread.stop()
                self.discovery_thread.join()
                del self.discovery_thread
            except AttributeError:
                pass
        if hasattr(self, 'dbusBluezAdapter'):
            self.dbusBluezAdapter = None

    @log.log_function()
    def exit(self):
        if hasattr(self, 'discovery_thread'):
            try:
                self.discovery_thread.stop()
                self.discovery_thread.join()
                del self.discovery_thread
            except AttributeError:
                pass
        self.clear_list()
        self.visible = False

    # ###################################################################
    # # Bluetooth Adapter
    # ###################################################################

    @log.log_function()
    def find_adapter(self):
        self.dbusBluezAdapter = dbus_bluez.find_adapter()
        if self.dbusBluezAdapter:
            self.init_adapter()

    @log.log_function()
    def init_adapter(self):
        dbus_bluez.adapter_set_alias(self.dbusBluezAdapter, hostname.get_hostname())
        dbus_bluez.adapter_set_powered(self.dbusBluezAdapter, True)

    @log.log_function()
    def start_discovery(self):
        if self.discovering:
            return

        self.discovering = True
        dbus_bluez.adapter_start_discovery(self.dbusBluezAdapter)

    @log.log_function()
    def stop_discovery(self):
        if self.discovering:
            dbus_bluez.adapter_stop_discovery(self.dbusBluezAdapter)
            self.discovering = False

    @log.log_function()
    def update_discovery(self):
        devices = self.get_devices()
        audio_connected = any(
            properties.get('Connected')
            and self.has_audio_sink(properties)
            for properties in (devices or {}).values()
        )
        if audio_connected:
            self.manual_discovery_deadline = 0
            self.stop_discovery()
        else:
            self.start_discovery()

    @log.log_function()
    def scan_devices(self, listItem=None):
        devices = self.get_devices() or {}
        audio_connected = any(
            properties.get('Connected')
            and self.has_audio_sink(properties)
            for properties in devices.values()
        )
        if (audio_connected
                and not xbmcgui.Dialog().yesno(
                    oe._(32331),
                    oe._(32423),
                    nolabel=oe._(32212),
                    yeslabel=oe._(32421),
                    defaultbutton=xbmcgui.DLG_YESNO_NO_BTN,
                )):
            return
        self.manual_discovery_deadline = (
            time.monotonic() + BT_MANUAL_DISCOVERY_TIMEOUT_SECONDS
        )
        self.start_discovery()
        self.discover_devices()

    # ###################################################################
    # # Bluetooth Device
    # ###################################################################

    @log.log_function()
    def get_devices(self):
        return dbus_bluez.find_devices()

    @staticmethod
    def has_audio_sink(properties):
        uuids = {
            str(uuid).lower() for uuid in properties.get('UUIDs', ())
        }
        return (str(properties.get('Icon', '')).startswith('audio-')
                or BT_AUDIO_SINK_UUID in uuids)

    @classmethod
    def is_audio_device(cls, properties):
        return (properties.get('Paired')
                and properties.get('Trusted')
                and cls.has_audio_sink(properties))

    @log.log_function()
    def remember_audio_device(self, path, properties=None):
        if properties is None:
            properties = (self.get_devices() or {}).get(path, {})
        if self.is_audio_device(properties):
            oe.write_setting('bluetooth', BT_LAST_AUDIO_DEVICE_SETTING, path)

    def monitor_audio_connection(self, path):
        with self.audio_recovery_lock:
            if path in self.audio_connected_paths:
                return
            self.audio_connected_paths.add(path)
            reset_guard = self.audio_profile_reset_guards.setdefault(
                path, audioProfileResetGuard())
            thread = audioRecoveryThread(path, reset_guard)
            self.audio_recovery_threads[path] = thread
            thread.start()
        log.log(f'Started initial PulseAudio A2DP monitor for {path}',
                log.INFO)

    def end_audio_connection(self, path):
        with self.audio_recovery_lock:
            was_connected = path in self.audio_connected_paths
            self.audio_connected_paths.discard(path)
            thread = self.audio_recovery_threads.pop(path, None)
        if thread is not None:
            thread.stop()
        if was_connected:
            log.log(f'Rearmed PulseAudio A2DP monitor for {path}', log.INFO)

    def set_audio_watchdog_enabled(self, enabled):
        log.log(f'Continuous Bluetooth audio auto-recovery enabled={enabled}',
                log.INFO)
        if not enabled:
            return
        devices = self.get_devices() or {}
        for path, properties in devices.items():
            if (not properties.get('Connected')
                    or not self.is_audio_device(properties)):
                continue
            with self.audio_recovery_lock:
                thread = self.audio_recovery_threads.get(path)
                if thread is not None and thread.is_alive():
                    continue
                self.audio_connected_paths.add(path)
                reset_guard = self.audio_profile_reset_guards.setdefault(
                    path, audioProfileResetGuard())
                thread = audioRecoveryThread(
                    path, reset_guard, startup_monitor=False)
                self.audio_recovery_threads[path] = thread
                thread.start()

    @log.log_function()
    def finalize_audio_connection(self, path, properties=None):
        if properties is None:
            properties = (self.get_devices() or {}).get(path, {})
        if not properties.get('Connected') or not self.is_audio_device(properties):
            return False
        self.remember_audio_device(path, properties)
        self.manual_discovery_deadline = 0
        self.stop_discovery()
        self.monitor_audio_connection(path)
        return True

    @log.log_function()
    def init_device(self, listItem=None):
        if listItem is None:
            listItem = oe.winOeMain.getControl(oe.listObject['btlist']).getSelectedItem()
        if listItem is None:
            return
        if listItem.getProperty('Paired') != '1':
            self.pair_device(listItem.getProperty('entry'))
        else:
            self.connect_device(listItem.getProperty('entry'))

    @log.log_function()
    def trust_connect_device(self, listItem=None):
        # ########################################################
        # # This function is used to Pair PS3 Remote without auth
        # ########################################################
        if listItem is None:
            listItem = oe.winOeMain.getControl(oe.listObject['btlist']).getSelectedItem()
        if listItem is None:
            return
        self.trust_device(listItem.getProperty('entry'))
        self.connect_device(listItem.getProperty('entry'))

    @log.log_function()
    def enable_device_standby(self, listItem=None):
        devices = oe.read_setting('bluetooth', 'standby')
        if devices is not None:
            devices = devices.split(',')
        else:
            devices = []
        if not listItem.getProperty('entry') in devices:
            devices.append(listItem.getProperty('entry'))
        oe.write_setting('bluetooth', 'standby', ','.join(devices))

    @log.log_function()
    def disable_device_standby(self, listItem=None):
        devices = oe.read_setting('bluetooth', 'standby')
        if devices is not None:
            devices = devices.split(',')
        else:
            devices = []
        if listItem.getProperty('entry') in devices:
            devices.remove(listItem.getProperty('entry'))
        oe.write_setting('bluetooth', 'standby', ','.join(devices))

    @log.log_function()
    def pair_device(self, path):
        try:
            dbus_bluez.device_pair(path)
            listItem = oe.winOeMain.getControl(oe.listObject['btlist']).getSelectedItem()
            if listItem is None:
                return
            self.trust_device(listItem.getProperty('entry'))
            self.connect_device(listItem.getProperty('entry'))
            self.menu_connections()
        except DBusError as e:
            self.dbus_error_handler(e)

    @log.log_function()
    def trust_device(self, path):
        dbus_bluez.device_set_trusted(path, True)

    @log.log_function()
    def connect_device(self, path):
        try:
            dbus_bluez.device_connect(path)
            self.finalize_audio_connection(path)
            self.menu_connections()
        except DBusError as e:
            self.dbus_error_handler(e)

    @log.log_function()
    def disconnect_device(self, listItem=None):
        if listItem is None:
            listItem = self.oe.winOeMain.getControl(self.oe.listObject['btlist']).getSelectedItem()
        if listItem is None:
            return
        self.disconnect_device_by_path(listItem.getProperty('entry'))

    @log.log_function()
    def disconnect_device_by_path(self, path):
        try:
            dbus_bluez.device_disconnect(path)
            self.menu_connections()
        except DBusError as e:
            self.dbus_error_handler(e)

    @log.log_function()
    def reset_audio_connection(self, listItem=None):
        if listItem is None:
            listItem = self.oe.winOeMain.getControl(
                self.oe.listObject['btlist']).getSelectedItem()
        if listItem is None:
            return
        path = listItem.getProperty('entry')
        thread = self.audio_reset_threads.get(path)
        if thread is not None and thread.is_alive():
            return
        with self.audio_recovery_lock:
            reset_guard = self.audio_profile_reset_guards.setdefault(
                path, audioProfileResetGuard())
        thread = audioProfileResetThread(path, reset_guard)
        self.audio_reset_threads[path] = thread
        thread.start()

    @log.log_function()
    def remove_device(self, listItem=None):
        if listItem is None:
            listItem = oe.winOeMain.getControl(oe.listObject['btlist']).getSelectedItem()
        if listItem is None:
            return
        log.log(f"remove_device->entry: {listItem.getProperty('entry')}", log.DEBUG)
        path = listItem.getProperty('entry')
        dbus_bluez.adapter_remove_device(self.dbusBluezAdapter, path)
        if oe.read_setting('bluetooth', BT_LAST_AUDIO_DEVICE_SETTING) == path:
            oe.write_setting('bluetooth', BT_LAST_AUDIO_DEVICE_SETTING, '')
        self.disable_device_standby(listItem)
        self.menu_connections()

    # ###################################################################
    # # Bluetooth Error Handler
    # ###################################################################

    @log.log_function()
    def dbus_error_handler(self, error):
        log.log(f'error message: {repr(error.message)}', log.DEBUG)
        oe.notify('Bluetooth error', error.message.split('.')[0], 'bt')
        if hasattr(self, 'pinkey_window'):
            self.close_pinkey_window()

    # ###################################################################
    # # Bluetooth GUI
    # ###################################################################

    @log.log_function()
    def clear_list(self):
        for entry in list(self.listItems.keys()):
            del self.listItems[entry]
        self.listItems = {}

    @log.log_function()
    def menu_connections(self, focusItem=None):
        self.discover_devices()
        oe.winOeMain.showButton(
            1,
            32421,
            'bluetooth',
            'scan_devices',
            onup=oe.listObject['btlist'],
            ondown=oe.listObject['btlist'],
            onleft=oe.listObject['btlist'],
            wrap_down=True,
        )
        if self.dbusBluezAdapter is not None and (not hasattr(self, 'discovery_thread') or self.discovery_thread.stopped):
            if hasattr(self, 'discovery_thread') and self.discovery_thread.stopped:
                del self.discovery_thread
            self.update_discovery()
            self.discovery_thread = discoveryThread(self)
            self.discovery_thread.start()

    @log.log_function()
    def rssi_to_percentage(self, rssi):
        min_rssi = -100  # Worst possible signal
        max_rssi = -30    # Best possible signal
        if rssi <= min_rssi:
            return 0
        elif rssi >= max_rssi:
            return 100
        ratio = (rssi - min_rssi) / (max_rssi - min_rssi)

        return round((ratio ** 1.8) * 100)

    @log.log_function()
    def discover_devices(self):
        if not hasattr(oe, 'winOeMain'):
            return
        if not oe.winOeMain.visible:
            return
        control_list = oe.winOeMain.getControl(int(oe.listObject['btlist']))
        if not dbus_bluez.system_has_bluez():
            oe.winOeMain.getControl(1301).setLabel(oe._(32346))
            control_list.reset()
            self.clear_list()
            log.log('exit_function (BT Disabled)', log.DEBUG)
            oe.winOeMain.setProperty('show_bt_label', 'true')
            return
        if self.dbusBluezAdapter is None:
            oe.winOeMain.getControl(1301).setLabel(oe._(32338))
            control_list.reset()
            self.clear_list()
            log.log('exit_function (No Adapter)', log.DEBUG)
            oe.winOeMain.setProperty('show_bt_label', 'true')
            return
        if not dbus_bluez.adapter_get_powered(self.dbusBluezAdapter):
            oe.winOeMain.getControl(1301).setLabel(oe._(32338))
            control_list.reset()
            self.clear_list()
            oe.winOeMain.setProperty('show_bt_label', 'true')
            log.log('exit_function (No Adapter Powered)', log.DEBUG)
            return

        self.dbusDevices = self.get_devices()
        if self.dbusDevices and not self.discovering:
            self.dbusDevices = {
                path: properties
                for path, properties in self.dbusDevices.items()
                if properties.get('Paired') or properties.get('Connected')
            }
        if self.dbusDevices:
            oe.winOeMain.clearProperty('show_bt_label')
            oe.winOeMain.getControl(1301).setLabel('')
            found_devices = frozenset(self.dbusDevices.keys())
            existing_devices = frozenset(self.listItems.keys())
            new_devices = found_devices - existing_devices
            deactivated_devices = existing_devices - found_devices
        else:
            control_list.reset()
            self.clear_list()
            oe.winOeMain.getControl(1301).setLabel(oe._(32339))
            oe.winOeMain.setProperty('show_bt_label', 'true')
            return

        selected_dbus_device = None
        selected_item = control_list.getSelectedItem()
        if selected_item:
            selected_dbus_device = selected_item.getProperty('entry')
        for dbusDevice, device_properties in self.dbusDevices.items():
            dictProperties = {}
            apName = device_properties.get('Name') or device_properties.get('Alias', '')
            dictProperties['entry'] = dbusDevice
            dictProperties['modul'] = self.__class__.__name__
            dictProperties['action'] = 'open_context_menu'
            if not 'Icon' in device_properties:
                dictProperties['Icon'] = 'default'
            if 'RSSI' in device_properties:
                rssi = int(device_properties['RSSI'])
                dictProperties['Strength'] = str(self.rssi_to_percentage(rssi))
            for prop in self.properties:
                name = self.properties[prop]['value']
                if name in device_properties:
                    value = device_properties[name]
                    if name == 'Connected':
                        if value:
                            dictProperties['ConnectedState'] = oe._(32334)
                        else:
                            dictProperties['ConnectedState'] = oe._(32335)
                    if self.properties[prop]['type'] == 1:
                        value = str(int(value))
                    if self.properties[prop]['type'] == 2:
                        value = str(value)
                    if self.properties[prop]['type'] == 3:
                        value = str(len(value))
                    if self.properties[prop]['type'] == 4:
                        value = str(int(value))
                    dictProperties[name] = value
            if dbusDevice in new_devices:
                self.listItems[dbusDevice] = oe.winOeMain.addConfigItem(apName, dictProperties, oe.listObject['btlist'])
            else:
                if dbusDevice in self.listItems:
                    self.listItems[dbusDevice].setLabel(apName)
                    for dictProperty in dictProperties:
                        try:
                            self.listItems[dbusDevice].setProperty(dictProperty, dictProperties[dictProperty])
                        except KeyError as e:
                            log.log(f'Suppressed error: {repr(e)}', log.INFO)
            for dbusDevice in deactivated_devices:
                for i in range(control_list.size()):
                    list_item = control_list.getListItem(i)
                    if list_item.getProperty('entry') == dbusDevice and dbusDevice in self.listItems:
                        control_list.removeItem(i)
                        try:
                            del self.listItems[dbusDevice]
                        except KeyError as e:
                            log.log(f'Suppressed error: {repr(e)}', log.INFO)
                        break
            if (new_devices or deactivated_devices) and selected_dbus_device is not None:
                for i in range(control_list.size()):
                    list_item = control_list.getListItem(i)
                    if list_item.getProperty('entry') == selected_dbus_device:
                        control_list.selectItem(i)
                        break

    @log.log_function()
    def open_context_menu(self, listItem):
        values = {}
        if listItem is None:
            listItem = oe.winOeMain.getControl(oe.listObject['btlist']).getSelectedItem()
        device_path = listItem.getProperty('entry')
        device_properties = (self.get_devices() or {}).get(device_path, {})
        connected = listItem.getProperty('Connected') == '1'
        if listItem.getProperty('Paired') != '1':
            values[1] = {
                'text': oe._(32145),
                'action': 'init_device',
                }
            if listItem.getProperty('Trusted') != '1':
                values[2] = {
                    'text': oe._(32358),
                    'action': 'trust_connect_device',
                    }
        if connected:
            if self.has_audio_sink(device_properties):
                values[3] = {
                    'text': oe._(32422),
                    'action': 'reset_audio_connection',
                    }
            devices = oe.read_setting('bluetooth', 'standby')
            if devices is not None:
                devices = devices.split(',')
            else:
                devices = []
            if listItem.getProperty('entry') in devices:
                values[4] = {
                    'text': oe._(32389),
                    'action': 'disable_device_standby',
                    }
            else:
                values[4] = {
                    'text': oe._(32388),
                    'action': 'enable_device_standby',
                    }
        elif listItem.getProperty('Paired') == '1':
            values[1] = {
                'text': oe._(32144),
                'action': 'init_device',
                }
        elif listItem.getProperty('Trusted') == '1':
            values[2] = {
                'text': oe._(32144),
                'action': 'trust_connect_device',
                }
        values[5] = {
            'text': oe._(32141),
            'action': 'remove_device',
            }
        if connected:
            values[7] = {
                'text': oe._(32143),
                'action': 'disconnect_device',
                }
        items = []
        actions = []
        for key in list(values.keys()):
            items.append(values[key]['text'])
            actions.append(values[key]['action'])
        select_window = xbmcgui.Dialog()
        title = oe._(32012)
        result = select_window.select(title, items)
        if result >= 0:
            getattr(self, actions[result])(listItem)

    @log.log_function()
    def open_pinkey_window(self, runtime=60, title=32343):
        self.pinkey_window = oeWindows.pinkeyWindow('service-LibreELEC-Settings-getPasskey.xml', oe.__cwd__, 'Default')
        self.pinkey_window.show()
        self.pinkey_window.set_title(oe._(title))
        self.pinkey_timer = pinkeyTimer(self, runtime)
        self.pinkey_timer.start()

    @log.log_function()
    def close_pinkey_window(self):
        if hasattr(self, 'pinkey_timer'):
            self.pinkey_timer.stop()
            self.pinkey_timer.join()
            self.pinkey_timer = None
            del self.pinkey_timer
        if hasattr(self, 'pinkey_window'):
            self.pinkey_window.close()
            self.pinkey_window = None
            del self.pinkey_window

    def standby_devices(self):
        if self.dbusBluezAdapter:
            devices = oe.read_setting('bluetooth', 'standby')
            if devices:
                for device in devices.split(','):
                    if dbus_bluez.device_get_connected(device):
                        self.disconnect_device_by_path(device)


####################################################################
## Bluez Listener class
####################################################################
class Bluez_Listener(dbus_bluez.Listener):

    @log.log_function()
    def __init__(self, parent):
        self.parent = weakref.proxy(parent)
        super().__init__()

    @log.log_function()
    def rssi_to_percentage(self, rssi):
        min_rssi = -100  # Worst possible signal
        max_rssi = -30    # Best possible signal
        if rssi <= min_rssi:
            return 0
        elif rssi >= max_rssi:
            return 100
        ratio = (rssi - min_rssi) / (max_rssi - min_rssi)

        return round((ratio ** 1.8) * 100)

    @log.log_function()
    def on_interfaces_added(self, path, interfaces):
        if dbus_bluez.INTERFACE_ADAPTER in interfaces:
            self.parent.dbusBluezAdapter = path
            self.parent.init_adapter()
        if hasattr(self.parent, 'pinkey_window'):
            if path == self.parent.pinkey_window.device:
                self.parent.close_pinkey_window()
        if self.parent.visible:
            self.parent.discover_devices()

    @log.log_function()
    def on_interfaces_removed(self, path, interfaces):
        if dbus_bluez.INTERFACE_ADAPTER in interfaces:
            self.parent.dbusBluezAdapter = None
        if self.parent.visible and not hasattr(self.parent, 'discovery_thread'):
            self.parent.discover_devices()

    @log.log_function()
    def on_properties_changed(self, interface, changed, invalidated, path):
        device_state_changed = (
            interface == dbus_bluez.INTERFACE_DEVICE
            and any(prop in changed for prop in (
                'Connected', 'Paired', 'Trusted', 'Icon', 'UUIDs'))
        )
        if (interface == dbus_bluez.INTERFACE_DEVICE
                and 'Connected' in changed
                and not changed['Connected']):
            self.parent.end_audio_connection(path)
        audio_connected = False
        if device_state_changed:
            devices = self.parent.get_devices() or {}
            audio_connected = self.parent.finalize_audio_connection(
                path, devices.get(path, {}))
        if self.parent.visible:
            if (device_state_changed
                    and not audio_connected
                    and hasattr(self.parent, 'discovery_thread')
                    and not self.parent.discovery_thread.stopped):
                self.parent.update_discovery()
            properties = [
                'Paired',
                'Adapter',
                'Connected',
                'Address',
                'Class',
                'Trusted',
                'Icon',
                ]
            if path in self.parent.listItems:
                for prop in changed:
                    if prop in properties:
                        self.parent.listItems[path].setProperty(str(prop), str(changed[prop]))
                if 'RSSI' in changed:
                    rssi = int(changed['RSSI'])
                    self.parent.listItems[path].setProperty('Strength', str(self.rssi_to_percentage(rssi)))
            else:
                self.parent.discover_devices()


####################################################################
## Obex Listener class
####################################################################

class Obex_Listener(dbus_obex.Listener):

    @log.log_function()
    def __init__(self, parent):
        self.parent = weakref.proxy(parent)
        super().__init__()

    # unused for now
    # @log.log_function()
    # def TransferChanged(self, path, interface, dummy):
    #     if 'Status' in interface:
    #         if interface['Status'] == 'active':
    #             self.parent.download_start = time.time()
    #             self.parent.download = xbmcgui.DialogProgress()
    #             self.parent.download.create('Bluetooth Filetransfer', f'{oe._(32181)}: {self.parent.download_file}')
    #         else:
    #             if hasattr(self.parent, 'download'):
    #                 self.parent.download.close()
    #                 del self.parent.download
    #                 del self.parent.download_path
    #                 del self.parent.download_size
    #                 del self.parent.download_start
    #             if interface['Status'] == 'complete':
    #                 xbmcDialog = xbmcgui.Dialog()
    #                 answer = xbmcDialog.yesno('Bluetooth Filetransfer', oe._(32383))
    #                 if answer == 1:
    #                     fil = f'{oe.DOWNLOAD_DIR}/{self.parent.download_file}'
    #                     if 'image' in self.parent.download_type:
    #                         xbmc.executebuiltin(f'showpicture({fil})')
    #                     else:
    #                         xbmc.Player().play(fil)
    #                 del self.parent.download_type
    #                 del self.parent.download_file
    #     if hasattr(self.parent, 'download'):
    #         if 'Transferred' in interface:
    #             transferred = int(interface['Transferred'] / 1024)
    #             speed = transferred / (time.time() - self.parent.download_start)
    #             percent = int(round(100 / self.parent.download_size * (interface['Transferred'] / 1024), 0))
    #             message = f'{oe._(32181)}: {self.parent.download_file}\n{oe._(32382)}: {speed} KB/s'
    #             self.parent.download.update(percent, message)
    #         if self.parent.download.iscanceled():
    #             obj = LEGACY_SYSTEM_BUS.get_object('org.bluez.obex', self.parent.download_path)
    #             itf = dbus.Interface(obj, 'org.bluez.obex.Transfer1')
    #             itf.Cancel()
    #             obj = None
    #             itf = None


####################################################################
## Bluetooth Agent class
####################################################################

class Bluez_Agent(dbus_bluez.Agent):

    @log.log_function()
    def __init__(self, parent):
        self.parent = weakref.proxy(parent)
        super().__init__()

    @log.log_function()
    def authorize_service(self, device, uuid):
        xbmcDialog = xbmcgui.Dialog()
        answer = xbmcDialog.yesno('Bluetooth', f'Authorize service {uuid}?')
        if answer == 1:
            oe.dictModules['bluetooth'].trust_device(device)
        else:
            self.reject('Connection rejected!')

    @log.log_function()
    def request_pincode(self, device):
        xbmcKeyboard = xbmc.Keyboard('', 'Enter PIN code')
        xbmcKeyboard.doModal()
        pincode = xbmcKeyboard.getText()
        return pincode

    @log.log_function()
    def request_passkey(self, device):
        xbmcDialog = xbmcgui.Dialog()
        passkey = int(xbmcDialog.numeric(0, 'Enter passkey (number in 0-999999)', '0'))
        return passkey

    @log.log_function()
    def display_passkey(self, device, passkey, entered):
        if not hasattr(self.parent, 'pinkey_window'):
            self.parent.open_pinkey_window()
            self.parent.pinkey_window.device = device
            self.parent.pinkey_window.set_label1('Passkey: %06u' % passkey)

    @log.log_function()
    def display_pincode(self, device, pincode):
        if hasattr(self.parent, 'pinkey_window'):
            self.parent.close_pinkey_window()
        self.parent.open_pinkey_window(runtime=30)
        self.parent.pinkey_window.device = device
        self.parent.pinkey_window.set_label1(f'PIN code: {pincode}')

    @log.log_function()
    def request_confirmation(self, device, passkey):
        xbmcDialog = xbmcgui.Dialog()
        answer = xbmcDialog.yesno('Bluetooth', f'Confirm passkey {passkey}')
        if answer == 1:
            oe.dictModules['bluetooth'].trust_device(device)
        else:
            self.reject('Passkey does not match')

    @log.log_function()
    def RequestAuthorization(self, device):
        xbmcDialog = xbmcgui.Dialog()
        answer = xbmcDialog.yesno('Bluetooth', 'Accept pairing?')
        if answer == 1:
            oe.dictModules['bluetooth'].trust_device(device)
        else:
            self.reject('Pairing rejected')

    @log.log_function()
    def Cancel(self):
        if hasattr(self.parent, 'pinkey_window'):
            self.parent.close_pinkey_window()


####################################################################
## Obex Agent class
####################################################################

class Obex_Agent(dbus_obex.Agent):

    @log.log_function()
    def __init__(self, parent):
        self.parent = weakref.proxy(parent)
        super().__init__()

    def authorize_push(self, transfer):
        xbmcDialog = xbmcgui.Dialog()
        properties = self.transfer_get_all_properties(transfer)
        answer = xbmcDialog.yesno('Bluetooth', f"{oe._(32381)}\n\n{properties['Name']}")
        log.log(f'answer={repr(answer)}', log.DEBUG)
        if answer != 1:
            self.reject('Not Authorized')
        self.parent.download_path = transfer
        self.parent.download_file = properties['Name']
        self.parent.download_size = properties['Size'] / 1024
        if 'Type' in properties:
            self.parent.download_type = properties['Type']
        else:
            self.parent.download_type = None
        return properties['Name']


class discoveryThread(threading.Thread):

    def __init__(self, parent):
        super().__init__()
        self.parent = weakref.proxy(parent)
        self.last_run = 0
        self._stop_event = threading.Event()
        self.stopped = False
        self.main_menu = oe.winOeMain.getControl(oe.winOeMain.guiMenList)

    @property
    def stopped(self):
        return self._stop_event.is_set()

    @stopped.setter
    def stopped(self, value):
        if value:
            self._stop_event.set()
        else:
            self._stop_event.clear()

    @log.log_function()
    def stop(self):
        self.stopped = True
        self.parent.stop_discovery()

    @log.log_function()
    def run(self):
        self._stop_event.clear()
        while not self.stopped and not oe.xbmcm.abortRequested():
            current_time = time.monotonic()
            if (self.parent.manual_discovery_deadline
                    and current_time >= self.parent.manual_discovery_deadline):
                self.parent.manual_discovery_deadline = 0
                self.parent.update_discovery()
            if (self.main_menu.getSelectedItem().getProperty('modul') == 'bluetooth'
                    and current_time > self.last_run + BT_DEVICES_LIST_REFRESH_INTERVAL_SECONDS):
                self.parent.discover_devices()
                self.last_run = current_time
            elif self.main_menu.getSelectedItem().getProperty('modul') != 'bluetooth':
                self.stop()
            oe.xbmcm.waitForAbort(1)


class audioProfileResetGuard:

    def __init__(self):
        self.lock = threading.Lock()
        self.last_completed = 0


class audioProfileResetThread(threading.Thread):

    def __init__(self, path, reset_guard=None):
        super().__init__()
        self.path = path
        self.reset_guard = reset_guard or audioProfileResetGuard()
        self._stop_event = threading.Event()

    @log.log_function()
    def stop(self):
        self._stop_event.set()

    @staticmethod
    def pulse_objects(object_type):
        try:
            result = subprocess.run(
                ['/usr/bin/pactl', '--format=json', 'list', object_type],
                check=True,
                capture_output=True,
                text=True,
                timeout=3,
            )
            return json.loads(result.stdout)
        except (FileNotFoundError, json.JSONDecodeError,
                subprocess.SubprocessError) as e:
            log.log(f'Unable to inspect PulseAudio {object_type}: {e}',
                    log.ERROR)
            return []

    def find_pulse_object(self, object_type):
        for pulse_object in self.pulse_objects(object_type):
            if pulse_object.get('properties', {}).get('bluez.path') == self.path:
                return pulse_object
        return None

    def reset_profile(self, minimum_interval=0):
        if not self.reset_guard.lock.acquire(blocking=False):
            log.log(f'PulseAudio profile reset already active for {self.path}',
                    log.INFO)
            return False
        try:
            if (minimum_interval
                    and self.reset_guard.last_completed > 0
                    and time.monotonic() - self.reset_guard.last_completed
                    < minimum_interval):
                log.log(
                    f'Suppressed duplicate PulseAudio profile reset for '
                    f'{self.path}; a recent reset already completed',
                    log.INFO,
                )
                return False
            completed = self._reset_profile()
            if completed:
                self.reset_guard.last_completed = time.monotonic()
            return completed
        finally:
            self.reset_guard.lock.release()

    def _reset_profile(self):
        card = self.find_pulse_object('cards')
        if card is None:
            log.log(f'No PulseAudio card found for {self.path}', log.ERROR)
            return False
        card_name = card.get('name')
        profile = card.get('active_profile')
        if not card_name or not profile or profile == 'off':
            log.log(f'No active PulseAudio profile found for {self.path}',
                    log.ERROR)
            return False
        try:
            subprocess.run(
                ['/usr/bin/pactl', 'set-card-profile', card_name, 'off'],
                check=True,
                capture_output=True,
                timeout=3,
            )
            self._stop_event.wait(BT_AUDIO_PROFILE_RESET_PAUSE_SECONDS)
            subprocess.run(
                ['/usr/bin/pactl', 'set-card-profile', card_name, profile],
                check=True,
                capture_output=True,
                timeout=5,
            )
            log.log(f'PulseAudio A2DP profile reset completed for {self.path}',
                    log.INFO)
            return True
        except (FileNotFoundError, subprocess.SubprocessError) as e:
            log.log(f'PulseAudio profile reset failed for {self.path}: {e}',
                    log.ERROR)
            return False

    @log.log_function()
    def run(self):
        self.reset_profile()


class audioRecoveryThread(audioProfileResetThread):

    def __init__(self, path, reset_guard=None, startup_monitor=True):
        super().__init__(path, reset_guard)
        self.startup_monitor = startup_monitor

    @staticmethod
    def recovery_is_safe():
        return (not xbmc.getCondVisibility('Player.HasMedia')
                or xbmc.getCondVisibility('Player.Paused'))

    @staticmethod
    def watchdog_enabled():
        return oe.read_setting(
            'bluetooth', BT_AUDIO_WATCHDOG_SETTING) != '0'

    def configured_latency(self):
        sink = self.find_pulse_object('sinks')
        if (sink is None
                or sink.get('state') not in ('IDLE', 'RUNNING')
                or sink.get('properties', {}).get('bluetooth.codec') != 'sbc'):
            return None
        configured = sink.get('latency', {}).get('configured', 0)
        return configured if configured > 0 else None

    def wait_for_safe_recovery(self, baseline, phase):
        deferred_logged = False
        while (not self._stop_event.is_set()
                and not oe.xbmcm.abortRequested()):
            if phase == 'watchdog' and not self.watchdog_enabled():
                log.log(
                    f'Cancelled PulseAudio A2DP watchdog recovery for '
                    f'{self.path}; continuous recovery is disabled',
                    log.INFO,
                )
                return False
            if self.recovery_is_safe():
                log.log(
                    f'Resetting stabilized PulseAudio A2DP profile for '
                    f'{self.path}; phase={phase}; baseline={baseline} usec',
                    log.INFO,
                )
                return self.reset_profile(
                    BT_AUDIO_WATCHDOG_RECOVERY_COOLDOWN_SECONDS)
            if not deferred_logged:
                log.log(
                    f'Deferring PulseAudio A2DP recovery for {self.path} '
                    f'until playback is paused or stopped',
                    log.INFO,
                )
                deferred_logged = True
            if self._stop_event.wait(1):
                return False
        return False

    @log.log_function()
    def run(self):
        startup_deadline = (
            time.monotonic() + BT_AUDIO_RECOVERY_MONITOR_SECONDS)
        phase = 'startup' if self.startup_monitor else 'watchdog'
        baseline = None
        bad_samples = 0
        stable_samples = 0
        unhealthy = False
        watchdog_reset_count = 0
        cooldown_until = 0
        if phase == 'watchdog':
            if not self.watchdog_enabled():
                return
            log.log(
                f'Started low-frequency PulseAudio A2DP watchdog for '
                f'{self.path}; interval='
                f'{BT_AUDIO_WATCHDOG_SAMPLE_INTERVAL_SECONDS} seconds',
                log.INFO,
            )
        while (not self._stop_event.is_set()
                and not oe.xbmcm.abortRequested()):
            current_time = time.monotonic()
            if phase == 'startup' and current_time >= startup_deadline:
                phase = 'watchdog'
                if not self.watchdog_enabled():
                    log.log(
                        f'Skipped low-frequency PulseAudio A2DP watchdog for '
                        f'{self.path}; continuous recovery is disabled',
                        log.INFO,
                    )
                    return
                log.log(
                    f'Started low-frequency PulseAudio A2DP watchdog for '
                    f'{self.path}; interval='
                    f'{BT_AUDIO_WATCHDOG_SAMPLE_INTERVAL_SECONDS} seconds',
                    log.INFO,
                )

            if phase == 'watchdog' and not self.watchdog_enabled():
                log.log(
                    f'Stopped low-frequency PulseAudio A2DP watchdog for '
                    f'{self.path}; continuous recovery is disabled',
                    log.INFO,
                )
                return

            sample_interval = (
                BT_AUDIO_RECOVERY_SAMPLE_INTERVAL_SECONDS
                if phase == 'startup'
                else BT_AUDIO_WATCHDOG_SAMPLE_INTERVAL_SECONDS
            )
            if current_time < cooldown_until:
                if self._stop_event.wait(sample_interval):
                    return
                continue

            configured = self.configured_latency()
            if configured is not None:
                if (baseline is None
                        or (not unhealthy and configured < baseline)):
                    baseline = configured
                if (configured - baseline
                        >= BT_AUDIO_RECOVERY_BAD_LATENCY_DELTA_USEC):
                    bad_samples += 1
                else:
                    bad_samples = 0

                required_bad_samples = (
                    BT_AUDIO_RECOVERY_BAD_SAMPLES
                    if phase == 'startup'
                    else BT_AUDIO_WATCHDOG_BAD_SAMPLES
                )
                if (not unhealthy
                        and bad_samples >= required_bad_samples):
                    unhealthy = True
                    log.log(
                        f'Unhealthy PulseAudio A2DP {phase} state detected '
                        f'for {self.path}; baseline={baseline} usec; '
                        f'configured latency={configured} usec; waiting '
                        f'for transport stability',
                        log.INFO,
                    )

                if (unhealthy
                        and configured - baseline
                        <= BT_AUDIO_RECOVERY_STABLE_LATENCY_DELTA_USEC):
                    stable_samples += 1
                else:
                    stable_samples = 0

                required_stable_samples = (
                    BT_AUDIO_RECOVERY_STABLE_SAMPLES
                    if phase == 'startup'
                    else BT_AUDIO_WATCHDOG_STABLE_SAMPLES
                )
                if (unhealthy
                        and stable_samples >= required_stable_samples):
                    recovery_phase = phase
                    if self.wait_for_safe_recovery(baseline, recovery_phase):
                        if recovery_phase == 'watchdog':
                            watchdog_reset_count += 1
                    if self._stop_event.is_set():
                        return
                    if phase == 'watchdog' and not self.watchdog_enabled():
                        return
                    if (watchdog_reset_count
                            >= BT_AUDIO_WATCHDOG_MAX_RESETS_PER_CONNECTION):
                        log.log(
                            f'PulseAudio A2DP watchdog reset limit reached '
                            f'for {self.path}; manual reset remains available',
                            log.INFO,
                        )
                        return
                    phase = 'watchdog'
                    unhealthy = False
                    bad_samples = 0
                    stable_samples = 0
                    cooldown_until = (
                        time.monotonic()
                        + BT_AUDIO_WATCHDOG_RECOVERY_COOLDOWN_SECONDS)
                    log.log(
                        f'PulseAudio A2DP watchdog cooling down for '
                        f'{self.path}; seconds='
                        f'{BT_AUDIO_WATCHDOG_RECOVERY_COOLDOWN_SECONDS}',
                        log.INFO,
                    )

            if self._stop_event.wait(sample_interval):
                return


class audioAutoConnectThread(threading.Thread):

    def __init__(self, parent):
        super().__init__()
        self.parent = weakref.proxy(parent)
        self._stop_event = threading.Event()

    @log.log_function()
    def stop(self):
        self._stop_event.set()

    @log.log_function()
    def run(self):
        for interval in BT_AUDIO_AUTO_CONNECT_INTERVALS_SECONDS:
            if self._stop_event.wait(interval) or oe.xbmcm.abortRequested():
                return

            devices = self.parent.get_devices() or {}
            audio_devices = {
                path: properties for path, properties in devices.items()
                if self.parent.is_audio_device(properties)
            }
            preferred = oe.read_setting(
                'bluetooth', BT_LAST_AUDIO_DEVICE_SETTING)
            connected = sorted(
                path for path, properties in audio_devices.items()
                if properties.get('Connected')
            )
            if connected:
                target = connected[0]
                self.parent.finalize_audio_connection(
                    target, audio_devices[target])
                return

            candidates = []
            if preferred in audio_devices and preferred not in candidates:
                candidates.append(preferred)
            candidates.extend(sorted(
                path for path in audio_devices
                if path not in candidates
            ))

            for target in candidates:
                try:
                    dbus_bluez.device_connect_profile(
                        target, BT_AUDIO_SINK_UUID)
                    self.parent.finalize_audio_connection(target)
                    return
                except DBusError as e:
                    if 'AlreadyConnected' in e.name:
                        self.parent.finalize_audio_connection(
                            target, audio_devices[target])
                        return
                    log.log(
                        f'Bluetooth audio auto-connect failed for '
                        f'{target}: {e.name}: {e.message}',
                        log.DEBUG,
                    )


class pinkeyTimer(threading.Thread):

    def __init__(self, parent, runtime=60):
        self.parent = weakref.proxy(parent)
        self.start_time = time.monotonic()
        self.last_run = time.monotonic()
        self._stop_event = threading.Event()
        self.stopped = False
        self.runtime = runtime
        super().__init__()

    @property
    def stopped(self):
        return self._stop_event.is_set()

    @stopped.setter
    def stopped(self, value):
        if value:
            self._stop_event.set()
        else:
            self._stop_event.clear()

    @log.log_function()
    def stop(self):
        self.stopped = True

    @log.log_function()
    def run(self):
        self._stop_event.clear()
        self.endtime = self.start_time + self.runtime
        while not self.stopped and not oe.xbmcm.abortRequested():
            current_time = time.monotonic()
            percent = round(100 / self.runtime * (self.endtime - current_time), 0)
            self.parent.pinkey_window.getControl(1704).setPercent(percent)
            if current_time >= self.endtime:
                self.stopped = True
                self.parent.close_pinkey_window()
            else:
                oe.xbmcm.waitForAbort(1)
