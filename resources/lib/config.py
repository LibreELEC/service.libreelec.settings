# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2020-present Team LibreELEC (https://libreelec.tv)

import os

import os_tools


OS_RELEASE = os_tools.read_shell_settings('/etc/os-release')

CONFIG_CACHE = os.environ.get('CONFIG_CACHE', '/storage/.cache')
USER_CONFIG = os.environ.get('USER_CONFIG', '/storage/.config')

HOSTNAME = os.path.join(CONFIG_CACHE, 'hostname')
HOSTS_CONF = os.path.join(USER_CONFIG, 'hosts.conf')

REGDOMAIN_CONF = os.path.join(CONFIG_CACHE, 'regdomain.conf')
SETREGDOMAIN = '/usr/lib/iw/setregdomain'

TIMEZONE = os.path.join(CONFIG_CACHE, 'timezone')
