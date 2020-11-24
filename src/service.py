# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
# Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)
# Copyright (C) 2019-present Team LibreELEC (https://libreelec.tv)

import oe
import xbmc
import threading
import socket
import os


class ServiceThread(threading.Thread):

    def __init__(self, oeMain):
        try:
            oeMain.dbg_log('_service_::__init__', 'enter_function', oeMain.LOGDEBUG)
            self.oe = oeMain
            self.wait_evt = threading.Event()
            self.socket_file = '/var/run/service.libreelec.settings.sock'
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.setblocking(1)
            if os.path.exists(self.socket_file):
                os.remove(self.socket_file)
            self.sock.bind(self.socket_file)
            self.sock.listen(1)
            self.stopped = False
            threading.Thread.__init__(self)
            self.daemon = True
            self.oe.dbg_log('_service_::__init__', 'exit_function', self.oe.LOGDEBUG)
        except Exception as e:
            self.oe.dbg_log('_service_::__init__', 'ERROR: (' + repr(e) + ')')

    def stop(self):
        try:
            self.oe.dbg_log('_service_::stop', 'enter_function', self.oe.LOGDEBUG)
            self.stopped = True
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(self.socket_file)
            sock.send(bytes('exit', 'utf-8'))
            sock.close()
            self.sock.close()
            self.oe.dbg_log('_service_::stop', 'exit_function', self.oe.LOGDEBUG)
        except Exception as e:
            self.oe.dbg_log('_service_::stop', 'ERROR: (' + repr(e) + ')')

    def run(self):
        try:
            self.oe.dbg_log('_service_::run', 'enter_function', self.oe.LOGDEBUG)
            if self.oe.read_setting('libreelec', 'wizard_completed') == None:
                threading.Thread(target=self.oe.openWizard).start()
            while self.stopped == False:
                self.oe.dbg_log('_service_::run', 'WAITING:', self.oe.LOGINFO)
                conn, addr = self.sock.accept()
                message = (conn.recv(1024)).decode('utf-8')
                self.oe.dbg_log('_service_::run', 'MESSAGE:' + message, self.oe.LOGINFO)
                conn.close()
                if message == 'openConfigurationWindow':
                    if not hasattr(self.oe, 'winOeMain'):
                        threading.Thread(target=self.oe.openConfigurationWindow).start()
                    else:
                        if self.oe.winOeMain.visible != True:
                            threading.Thread(target=self.oe.openConfigurationWindow).start()
                if message == 'exit':
                    self.stopped = True
            self.oe.dbg_log('_service_::run', 'exit_function', self.oe.LOGDEBUG)
        except Exception as e:
            self.oe.dbg_log('_service_::run', 'ERROR: (' + repr(e) + ')')


class cxbmcm(xbmc.Monitor):

    def onScreensaverActivated(self):
        oe.__oe__.dbg_log('c_xbmcm::onScreensaverActivated', 'enter_function', oe.__oe__.LOGDEBUG)
        if oe.__oe__.read_setting('bluetooth', 'standby'):
            threading.Thread(target=oe.__oe__.standby_devices).start()
        oe.__oe__.dbg_log('c_xbmcm::onScreensaverActivated', 'exit_function', oe.__oe__.LOGDEBUG)

    def onDPMSActivated(self):
        oe.__oe__.dbg_log('c_xbmcm::onDPMSActivated', 'enter_function', oe.__oe__.LOGDEBUG)
        if oe.__oe__.read_setting('bluetooth', 'standby'):
            threading.Thread(target=oe.__oe__.standby_devices).start()
        oe.__oe__.dbg_log('c_xbmcm::onDPMSActivated', 'exit_function', oe.__oe__.LOGDEBUG)


xbmcm = cxbmcm()
oe.load_modules()
oe.start_service()
monitor = ServiceThread(oe.__oe__)
monitor.start()

while not xbmcm.abortRequested():
    if xbmcm.waitForAbort(60):
        break

    if not oe.__oe__.read_setting('bluetooth', 'standby'):
        continue

    timeout = oe.__oe__.read_setting('bluetooth', 'idle_timeout')
    if not timeout:
        continue

    try:
        timeout = int(timeout)
    except:
        continue

    if timeout < 1:
        continue

    if xbmc.getGlobalIdleTime() / 60 >= timeout:
        oe.__oe__.dbg_log('service', 'idle timeout reached', oe.__oe__.LOGDEBUG)
        oe.__oe__.standby_devices()

if hasattr(oe, 'winOeMain') and hasattr(oe.winOeMain, 'visible'):
    if oe.winOeMain.visible == True:
        oe.winOeMain.close()

oe.stop_service()
monitor.stop()
