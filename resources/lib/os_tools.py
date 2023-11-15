# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2020-present Team LibreELEC (https://libreelec.tv)

'''This module holds support functions for interacting with the underlying OS.

Support functions are grouped by purpose:
1. File access: read / write / copy / move / download
2. System access: executing system commands
'''

import os
import subprocess

import log


### FILE ACCESS ###
def read_shell_setting(file, default):
    setting = default
    if os.path.isfile(file):
        with open(file) as input:
            setting = input.readline().strip()
    return setting


def read_shell_settings(file, defaults={}):
    settings = defaults
    if os.path.isfile(file):
        with open(file) as input:
            for line in input:
                name, value = line.strip().split('=', 1)
                if len(value) and value[0] in ['"', '"'] and value[0] == value[-1]:
                    value = value[1:-1]
                settings[name] = value
    return settings


### SYSTEM ACCESS ###
def execute(command, get_result=False, output_err_msg=True):
    '''Run command, waiting for it to finish. Returns: command output, empty string or None'''
    log.log(f'Executing command: {command}', log.DEBUG)
    try:
        cmd_status = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        if output_err_msg:
            log.log(f'Command failed: {command}', log.ERROR)
            log.log(f'Executed command: {e.cmd}', log.DEBUG)
            log.log(f'\nSTART COMMAND OUTPUT:\n{e.stdout.decode()}\nEND COMMAND OUTPUT', log.ERROR)
        # return empty string if result wanted to match old behaviour
        return '' if get_result else None
    # return output if requested, otherwise return None
    return cmd_status.stdout.decode() if get_result else None


def get_rpi_device_type():
    '''Ask kernel for RPi revision to get device type'''
    if os.path.isfile('/proc/device-tree/system/linux,revision'):
        with open('/proc/device-tree/system/linux,revision', mode='rb') as data:
            revision = int(data.read().hex(), 16)
        new_revision_format = (revision >> 23) & 0x1
        if new_revision_format:
            device_type = str((revision >> 4) & 0xff)
            return device_type
        else:
            # old style revision format means older than RPi2; noop for now as no firmware for this hardware
            # if needed in future, see: https://github.com/raspberrypi/documentation/blob/develop/documentation/asciidoc/computers/raspberry-pi/revision-codes.adoc
            return None
    return None
