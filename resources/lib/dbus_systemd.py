# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2020-present Team LibreELEC

import dbus_utils

BUS_NAME = 'org.freedesktop.systemd1'
PATH_SYSTEMD = '/org/freedesktop/systemd1'
INTERFACE_SYSTEMD_MANAGER = 'org.freedesktop.systemd1.Manager'

def restart_unit(name, mode='replace'):
    return dbus_utils.call_method(BUS_NAME, PATH_SYSTEMD, INTERFACE_SYSTEMD_MANAGER, 'RestartUnit', name, mode)

def reboot():
    return dbus_utils.call_method(BUS_NAME, PATH_SYSTEMD, INTERFACE_SYSTEMD_MANAGER, 'Reboot')
