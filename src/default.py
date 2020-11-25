# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
# Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)
# Copyright (C) 2019-present Team LibreELEC (https://libreelec.tv)

import le
import socket
import xbmc
import xbmcaddon

__scriptid__ = 'service.libreelec.settings'
__addon__ = xbmcaddon.Addon(id=__scriptid__)
__cwd__ = __addon__.getAddonInfo('path')
__media__ = '%s/resources/skins/Default/media' % __cwd__
_ = __addon__.getLocalizedString

try:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(le.SOCKET)
    sock.send(bytes('openConfigurationWindow', 'utf-8'))
    sock.close()
except Exception as e:
    xbmc.executebuiltin('Notification("LibreELEC", "%s", 5000, "%s/icon.png")' % (_(32390), __media__))
