# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2020-present Team LibreELEC

import dbussy
import ravel

import dbus_utils


BUS_NAME = 'org.bluez'
ERROR_REJECTED = 'org.bluez.Error.Rejected'
INTERFACE_ADAPTER = 'org.bluez.Adapter1'
INTERFACE_AGENT = 'org.bluez.Agent1'
INTERFACE_AGENT_MANAGER = 'org.bluez.AgentManager1'
INTERFACE_DEVICE = 'org.bluez.Device1'
PATH_BLUEZ = '/org/bluez'
PATH_AGENT = '/kodi/agent/bluez'


@ravel.interface(ravel.INTERFACE.SERVER, name=INTERFACE_AGENT)
class Agent(dbus_utils.Agent):

    def __init__(self):
        super().__init__(BUS_NAME, PATH_AGENT)

    def manager_register_agent(self):
        dbus_utils.call_method(BUS_NAME, PATH_BLUEZ, INTERFACE_AGENT_MANAGER,
                               'RegisterAgent', PATH_AGENT, 'KeyboardDisplay')

    def manager_unregister_agent(self):
        dbus_utils.call_method(BUS_NAME, PATH_BLUEZ, INTERFACE_AGENT_MANAGER,
                               'UnregisterAgent', PATH_AGENT)

    @ravel.method(
        in_signature='os',
        out_signature='',
        arg_keys=['device', 'uuid']
    )
    def AuthorizeService(self, device, uuid):
        self.authorize_service(device, uuid)

    @ravel.method(
        in_signature='',
        out_signature=''
    )
    def Cancel(self):
        self.cancel()

    @ravel.method(
        in_signature='ouq',
        out_signature='',
        arg_keys=['device', 'passkey', 'entered']
    )
    def DisplayPasskey(self, device, passkey, entered):
        self.display_passkey(device, passkey, entered)

    @ravel.method(
        in_signature='os',
        out_signature='',
        arg_keys=['device', 'pincode']
    )
    def DisplayPinCode(self, device, pincode):
        self.display_pincode(device, pincode)

    @ravel.method(
        in_signature='',
        out_signature=''
    )
    def Release(self):
        raise NotImplementedError

    @ravel.method(
        in_signature='o',
        out_signature='',
        arg_keys=['device']
    )
    def RequestAuthorization(self, device):
        self.request_authorization(device)

    @ravel.method(
        in_signature='ou',
        out_signature='',
        arg_keys=['device', 'passkey']
    )
    def RequestConfirmation(self, device, passkey):
        self.request_confirmation(device, passkey)

    @ravel.method(
        in_signature='o',
        out_signature='u',
        arg_keys=['device'],
        result_keyword='reply'
    )
    def RequestPasskey(self, device):
        passkey = self.request_passkey(device)
        reply[0] = (dbussy.DBUS.Signature('u'), passkey)

    @ravel.method(
        in_signature='o',
        out_signature='s',
        arg_keys=['device'],
        result_keyword='reply'
    )
    def RequestPinCode(self, device, reply):
        pincode = self.request_pincode(device)
        reply[0] = (dbussy.DBUS.Signature('s'), pincode)

    def reject(self, message):
        raise dbussy.DBusError(ERROR_REJECTED, message)

class Listener(object):

    def __init__(self):
        dbus_utils.BUS.listen_objects_added(func=self._on_interfaces_added)
        dbus_utils.BUS.listen_objects_removed(func=self._on_interfaces_removed)
        dbus_utils.BUS.listen_propchanged(
            interface=dbussy.DBUS.INTERFACE_PROPERTIES,
            fallback=True,
            func=self._on_properties_changed,
            path='/')

    @ravel.signal(name='InterfacesAdded', in_signature='oa{sa{sv}}', arg_keys=('path', 'interfaces'))
    def _on_interfaces_added(self, path, interfaces):
        interfaces = dbus_utils.convert_from_dbussy(interfaces)
        self.on_interfaces_added(path, interfaces)

    @ravel.signal(name='InterfacesRemoved', in_signature='oas', arg_keys=('path', 'interfaces'))
    def _on_interfaces_removed(self, path, interfaces):
        interfaces = dbus_utils.convert_from_dbussy(interfaces)
        self.on_interfaces_removed(path, interfaces)

    @ravel.signal(name='PropertiesChanged', in_signature='sa{sv}as', arg_keys=('interface', 'changed', 'invalidated'), path_keyword='path')
    def _on_properties_changed(self, interface, changed, invalidated, path):
        interface = dbus_utils.convert_from_dbussy(interface)
        changed = dbus_utils.convert_from_dbussy(changed)
        invalidated = dbus_utils.convert_from_dbussy(invalidated)
        self.on_properties_changed(interface, changed, invalidated, path)

def get_managed_objects():
    return dbus_utils.call_method(BUS_NAME, '/', dbussy.DBUSX.INTERFACE_OBJECT_MANAGER, 'GetManagedObjects')


def adapter_get_property(path, name):
    return dbus_utils.call_method(BUS_NAME, path, dbussy.DBUS.INTERFACE_PROPERTIES, 'Get', INTERFACE_ADAPTER, name)


def adapter_get_powered(path):
    return adapter_get_property(path, 'Powered')


def adapter_remove_device(path, device):
    return dbus_utils.call_method(BUS_NAME, path, INTERFACE_ADAPTER, 'RemoveDevice', device)


def adapter_set_property(path, name, value):
    return dbus_utils.call_method(BUS_NAME, path, dbussy.DBUS.INTERFACE_PROPERTIES, 'Set', INTERFACE_ADAPTER, name, value)


def adapter_set_alias(path, alias):
    return adapter_set_property(path, 'Alias', (dbussy.DBUS.Signature('s'), alias))


def adapter_set_powered(path, powered):
    return adapter_set_property(path, 'Powered', (dbussy.DBUS.Signature('b'), powered))


def adapter_start_discovery(path):
    return dbus_utils.call_method(BUS_NAME, path, INTERFACE_ADAPTER, 'StartDiscovery')


def adapter_stop_discovery(path):
    return dbus_utils.call_method(BUS_NAME, path, INTERFACE_ADAPTER, 'StopDiscovery')


def device_get_property(path, name):
    return dbus_utils.call_method(BUS_NAME, path, dbussy.DBUS.INTERFACE_PROPERTIES, 'Get', INTERFACE_DEVICE, name)


def device_get_connected(path):
    return device_get_property(path, 'Connected')


def device_get_trusted(path):
    return device_get_property(path, 'Trusted')


def device_connect(path):
    return dbus_utils.run_method(BUS_NAME, path, INTERFACE_DEVICE, 'Connect')


def device_disconnect(path):
    return dbus_utils.call_method(BUS_NAME, path, INTERFACE_DEVICE, 'Disconnect')


def device_pair(path):
    return dbus_utils.run_method(BUS_NAME, path, INTERFACE_DEVICE, 'Pair')


def device_set_property(path, name, value):
    return dbus_utils.call_method(BUS_NAME, path, dbussy.DBUS.INTERFACE_PROPERTIES, 'Set', INTERFACE_DEVICE, name, value)


def device_set_trusted(path, trusted):
    return device_set_property(path, 'Trusted', (dbussy.DBUS.Signature('b'), trusted))


def find_adapter():
    if system_has_bluez():
        objects = get_managed_objects()
        for path, interfaces in objects.items():
            if interfaces.get(INTERFACE_ADAPTER):
                return path


def find_devices():
    devices = {}
    objects = get_managed_objects()
    for path, interfaces in objects.items():
        if interfaces.get(INTERFACE_DEVICE):
            devices[path] = interfaces[INTERFACE_DEVICE]
    return devices


def system_has_bluez():
    return BUS_NAME in dbus_utils.list_names()
