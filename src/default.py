# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
# Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)
# Copyright (C) 2019-present Team LibreELEC (https://libreelec.tv)

import le
import socket

try:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(le.SOCKET)
    sock.send(bytes('openConfigurationWindow', 'utf-8'))
    sock.close()
except:
    le.notification(le.ADDON_NAME, le.ADDON_STRING(32390))
