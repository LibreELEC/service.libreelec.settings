# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
# Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)

import xbmc
import socket
import xbmcaddon

__scriptid__ = 'service.libreelec.settings'
__addon__ = xbmcaddon.Addon(id=__scriptid__)
__cwd__ = __addon__.getAddonInfo('path')
__media__ = '%s/resources/skins/Default/media' % __cwd__
_ = __addon__.getLocalizedString

try:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect('/var/run/service.libreelec.settings.sock')
    sock.send('openConfigurationWindow')
    sock.close()
except Exception as e:
    xbmc.executebuiltin('Notification("LibreELEC", "%s", 5000, "%s/icon.png")' % (_(32390).encode('utf-8'), __media__))
