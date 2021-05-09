# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2020-present Team LibreELEC

import dbus_utils
import dbussy
import ravel

BUS_NAME = 'org.pulseaudio.Server'
PATH_PULSEAUDIO_CORE = '/org/pulseaudio/core1'
INTERFACE_PULSEAUDIO_CORE = 'org.PulseAudio.Core1'
INTERFACE_PULSEAUDIO_CARD = 'org.PulseAudio.Core1.Card'
INTERFACE_PULSEAUDIO_CARDPROFILE = 'org.PulseAudio.Core1.CardProfile'
INTERFACE_PULSEAUDIO_DEVICE = 'org.PulseAudio.Core1.Device'

def core_get_property(name):
    return call_method(BUS_NAME, PATH_PULSEAUDIO_CORE, dbussy.DBUS.INTERFACE_PROPERTIES, 'Get', INTERFACE_PULSEAUDIO_CORE, name)

def core_set_property(name, value):
    return call_method(BUS_NAME, PATH_PULSEAUDIO_CORE, dbussy.DBUS.INTERFACE_PROPERTIES, 'Set', INTERFACE_PULSEAUDIO_CORE, name, value)

def core_set_fallback_sink(sink):
    return core_set_property('FallbackSink', (dbussy.DBUS.Signature('o'), sink))

def card_get_properties(path):
    return call_method(BUS_NAME, path, dbussy.DBUS.INTERFACE_PROPERTIES, 'GetAll', INTERFACE_PULSEAUDIO_CARD)

def card_get_property(path, name):
    return call_method(BUS_NAME, path, dbussy.DBUS.INTERFACE_PROPERTIES, 'Get', INTERFACE_PULSEAUDIO_CARD, name)

def card_set_property(path, name, value):
    return call_method(BUS_NAME, path, dbussy.DBUS.INTERFACE_PROPERTIES, 'Set', INTERFACE_PULSEAUDIO_CARD, name, value)

def card_set_active_profile(path, profile):
    return card_set_property(path, "ActiveProfile",  (dbussy.DBUS.Signature('o'), profile))

def profile_get_property(path, name):
    return call_method(BUS_NAME, path, dbussy.DBUS.INTERFACE_PROPERTIES, 'Get', INTERFACE_PULSEAUDIO_CARDPROFILE, name)

def sink_get_property(path, name):
    return call_method(BUS_NAME, path, dbussy.DBUS.INTERFACE_PROPERTIES, 'Get', INTERFACE_PULSEAUDIO_DEVICE, name)

def system_has_pulseaudio():
    return conn is not None

def call_method(bus_name, path, interface, method_name, *args, **kwargs):
    interface = BUS[bus_name][path].get_interface(interface)
    method = getattr(interface, method_name)
    result = method(*args, **kwargs)
    first = next(iter(result or []), None)
    return dbus_utils.convert_from_dbussy(first)

try:
    conn = dbussy.Connection.open('unix:path=/var/run/pulse/dbus-socket', private=False)
    conn.bus_unique_name = 'PulseAudio'
    BUS = ravel.Connection(conn)
except Exception as e:
    pass
