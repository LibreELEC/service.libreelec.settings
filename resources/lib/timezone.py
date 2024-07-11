# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2024-present Team LibreELEC (https://libreelec.tv)

'''This module holds support functions for interacting with timezones.
'''


import config
import os_tools


def get_timezone():
    '''Read timezone setting from file or return default of UTC timezone.'''
    return os_tools.read_shell_setting(config.TIMEZONE, default='TIMEZONE=UTC').split('=', 1)[1]


def list_timezones():
    '''List timezones available from tzdata.'''
    timezones = []
    with open('/usr/share/zoneinfo/tzdata.zi', mode='r', encoding='utf-8') as tz_db:
        content = tz_db.read()
    for line in content.splitlines():
        # if line starts with Z take second field
        if line.startswith('Z'):
            timezones.append(line.split(' ')[1])
    # sort and return
    timezones.sort()
    return timezones


def set_timezone(timezone):
    '''Write new timezone info to .cache file and commit change to system.'''
    current_timezone = get_timezone()
    if current_timezone != timezone or not os.path.isfile(config.TIMEZONE):
        with open(config.TIMEZONE, mode='w', encoding='utf-8') as out_file:
            out_file.write(f'TIMEZONE={timezone}\n')
        os_tools.execute('systemctl restart tz-data')
