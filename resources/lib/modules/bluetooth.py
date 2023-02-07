# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
# Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)
# Copyright (C) 2019-present Team LibreELEC (https://libreelec.tv)

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
        self.found_devices = frozenset()

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

    @log.log_function()
    def stop_service(self):
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
        self.found_devices = frozenset()
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

    # ###################################################################
    # # Bluetooth Device
    # ###################################################################

    @log.log_function()
    def get_devices(self):
        return dbus_bluez.find_devices()

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
    def enable_device_autoconnect(self, listItem=None):
        devices = oe.read_setting('bluetooth', 'autoconnect')
        devices = devices.split(',') if devices else []
        if not listItem.getProperty('entry') in devices:
            devices.append(listItem.getProperty('entry'))
        oe.write_setting('bluetooth', 'autoconnect', ','.join(devices))

    @log.log_function()
    def disable_device_autoconnect(self, listItem=None):
        devices = oe.read_setting('bluetooth', 'autoconnect')
        devices = devices.split(',') if devices else []
        if listItem.getProperty('entry') in devices:
            devices.remove(listItem.getProperty('entry'))
        oe.write_setting('bluetooth', 'autoconnect', ','.join(devices))

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
    def remove_device(self, listItem=None):
        if listItem is None:
            listItem = oe.winOeMain.getControl(oe.listObject['btlist']).getSelectedItem()
        if listItem is None:
            return
        oe.dbg_log('bluetooth::remove_device->entry::', listItem.getProperty('entry'), oe.LOGDEBUG)
        path = listItem.getProperty('entry')
        dbus_bluez.adapter_remove_device(self.dbusBluezAdapter, path)
        self.disable_device_standby(listItem)
        self.menu_connections()

    # ###################################################################
    # # Bluetooth Error Handler
    # ###################################################################

    @log.log_function()
    def dbus_error_handler(self, error):
        oe.dbg_log('bluetooth::dbus_error_handler::err_message', repr(error.message), oe.LOGDEBUG)
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
        if self.dbusBluezAdapter is not None and (not hasattr(self, 'discovery_thread') or self.discovery_thread.stopped):
            if hasattr(self, 'discovery_thread') and self.discovery_thread.stopped:
                del self.discovery_thread
            self.start_discovery()
            self.discovery_thread = discoveryThread(self)
            self.discovery_thread.start()

    @log.log_function()
    def discover_devices(self):
        if not hasattr(oe, 'winOeMain'):
            return
        if not oe.winOeMain.visible:
            return
        if not dbus_bluez.system_has_bluez():
            self.found_devices = frozenset()
            oe.winOeMain.getControl(1301).setLabel(oe._(32346))
            oe.winOeMain.getControl(int(oe.listObject['btlist'])).reset()
            self.clear_list()
            oe.dbg_log('bluetooth::menu_connections', 'exit_function (BT Disabled)', oe.LOGDEBUG)
            oe.winOeMain.setProperty('show_bt_label', 'true')
            return
        if self.dbusBluezAdapter is None:
            self.found_devices = frozenset()
            oe.winOeMain.getControl(1301).setLabel(oe._(32338))
            oe.winOeMain.getControl(int(oe.listObject['btlist'])).reset()
            self.clear_list()
            oe.dbg_log('bluetooth::menu_connections', 'exit_function (No Adapter)', oe.LOGDEBUG)
            oe.winOeMain.setProperty('show_bt_label', 'true')
            return
        if not dbus_bluez.adapter_get_powered(self.dbusBluezAdapter):
            self.found_devices = frozenset()
            oe.winOeMain.getControl(1301).setLabel(oe._(32338))
            oe.winOeMain.getControl(int(oe.listObject['btlist'])).reset()
            self.clear_list()
            oe.winOeMain.setProperty('show_bt_label', 'true')
            oe.dbg_log('bluetooth::menu_connections', 'exit_function (No Adapter Powered)', oe.LOGDEBUG)
            return

        rebuildList = False
        self.dbusDevices = self.get_devices()
        if self.dbusDevices:
            oe.winOeMain.clearProperty('show_bt_label')
            oe.winOeMain.getControl(1301).setLabel('')
            found_devices = frozenset(self.dbusDevices.keys())
            if found_devices != self.found_devices:
                self.found_devices = found_devices
                rebuildList = True
                oe.winOeMain.getControl(int(oe.listObject['btlist'])).reset()
                self.clear_list()
        else:
            self.found_devices = frozenset()
            oe.winOeMain.getControl(1301).setLabel(oe._(32339))
            oe.winOeMain.setProperty('show_bt_label', 'true')
        for dbusDevice, device_properties in self.dbusDevices.items():
            dictProperties = {}
            apName = ''
            dictProperties['entry'] = dbusDevice
            dictProperties['modul'] = self.__class__.__name__
            dictProperties['action'] = 'open_context_menu'
            if 'Name' in device_properties:
                apName = device_properties['Name']
            if not 'Icon' in device_properties:
                dictProperties['Icon'] = 'default'
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
            if rebuildList:
                self.listItems[dbusDevice] = oe.winOeMain.addConfigItem(apName, dictProperties, oe.listObject['btlist'])
            else:
                if dbusDevice in self.listItems:
                    self.listItems[dbusDevice].setLabel(apName)
                    for dictProperty in dictProperties:
                        try:
                            self.listItems[dbusDevice].setProperty(dictProperty, dictProperties[dictProperty])
                        except KeyError as e:
                            log.log(f'Suppressed error: {repr(e)}', log.INFO)

    @log.log_function()
    def open_context_menu(self, listItem):
        values = {}
        if listItem is None:
            listItem = oe.winOeMain.getControl(oe.listObject['btlist']).getSelectedItem()
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
        if listItem.getProperty('Connected') == '1':
            values[3] = {
                'text': oe._(32143),
                'action': 'disconnect_device',
                }
            devices = oe.read_setting('bluetooth', 'standby')
            devices = devices.split(',') if devices else []
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

            devices = oe.read_setting('bluetooth', 'autoconnect')
            devices = devices.split(',') if devices else []
            if listItem.getProperty('entry') in devices:
                values[7] = {
                    'text': oe._(32391),
                    'action': 'disable_device_autoconnect',
                    }
            else:
                values[7] = {
                    'text': oe._(32392),
                    'action': 'enable_device_autoconnect',
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
        values[6] = {
            'text': oe._(32142),
            'action': 'menu_connections',
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

    def autoconnect_devices(self):
        if not self.dbusBluezAdapter:
            return
        devices = oe.read_setting('bluetooth', 'autoconnect')
        if not devices:
            return
        for path in devices.split(','):
            if not dbus_bluez.device_get_connected(path) and dbus_bluez.device_get_trusted(path):
                try:
                    dbus_bluez.device_connect(path)
                except DBusError as e:
                    pass

####################################################################
## Bluez Listener class
####################################################################
class Bluez_Listener(dbus_bluez.Listener):

    @log.log_function()
    def __init__(self, parent):
        self.parent = weakref.proxy(parent)
        super().__init__()

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
        if self.parent.visible:
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
        oe.dbg_log('bluetooth::obexAgent::AuthorizePush::answer=', repr(answer), oe.LOGDEBUG)
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
            current_time = time.time()
            if (self.main_menu.getSelectedItem().getProperty('modul') == 'bluetooth'
                    and current_time > self.last_run + 5):
                self.parent.discover_devices()
                self.last_run = current_time
            elif self.main_menu.getSelectedItem().getProperty('modul') != 'bluetooth':
                self.stop()
            oe.xbmcm.waitForAbort(1)


class pinkeyTimer(threading.Thread):

    def __init__(self, parent, runtime=60):
        self.parent = weakref.proxy(parent)
        self.start_time = time.time()
        self.last_run = time.time()
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
            current_time = time.time()
            percent = round(100 / self.runtime * (self.endtime - current_time), 0)
            self.parent.pinkey_window.getControl(1704).setPercent(percent)
            if current_time >= self.endtime:
                self.stopped = True
                self.parent.close_pinkey_window()
            else:
                oe.xbmcm.waitForAbort(1)
