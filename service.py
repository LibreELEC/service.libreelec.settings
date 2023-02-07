# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
# Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)
# Copyright (C) 2019-present Team LibreELEC (https://libreelec.tv)

import os
import socket
import threading

import xbmc

import syspath
import dbus_utils
import log
import oe


class Service_Thread(threading.Thread):

    SOCKET = '/var/run/service.libreelec.settings.sock'

    def __init__(self):
        threading.Thread.__init__(self)
        self.init()

    @log.log_function()
    def init(self):
        if os.path.exists(self.SOCKET):
            os.remove(self.SOCKET)
        self.daemon = True
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.setblocking(1)
        self.sock.bind(self.SOCKET)
        self.sock.listen(1)
        self.stopped = False

    @log.log_function()
    def run(self):
        if oe.read_setting('libreelec', 'wizard_completed') == None:
            threading.Thread(target=oe.openWizard).start()
        while self.stopped == False:
            log.log(f'Waiting', log.INFO)
            conn, addr = self.sock.accept()
            message = (conn.recv(1024)).decode('utf-8')
            conn.close()
            log.log(f'Received {message}', log.INFO)
            if message == 'openConfigurationWindow':
                if not hasattr(oe, 'winOeMain'):
                    threading.Thread(target=oe.openConfigurationWindow).start()
                else:
                    if oe.winOeMain.visible != True:
                        threading.Thread(
                            target=oe.openConfigurationWindow).start()
            if message == 'exit':
                self.stopped = True

    @log.log_function()
    def stop(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.SOCKET)
        sock.send(bytes('exit', 'utf-8'))
        sock.close()
        self.join()
        self.sock.close()


class Monitor(xbmc.Monitor):

    @log.log_function()
    def onScreensaverActivated(self):
        if oe.read_setting('bluetooth', 'standby'):
            threading.Thread(target=oe.standby_devices).start()

    @log.log_function()
    def onDPMSActivated(self):
        if oe.read_setting('bluetooth', 'standby'):
            threading.Thread(target=oe.standby_devices).start()

    @log.log_function()
    def run(self):
        dbus_utils.LOOP_THREAD.start()
        oe.load_modules()
        oe.start_service()
        service_thread = Service_Thread()
        service_thread.start()
        oe.autoconnect_devices()
        while not self.abortRequested():
            if self.waitForAbort(30):
                break
            standby_devices = oe.read_setting('bluetooth', 'standby')
            autoconnect_devices = oe.read_setting('bluetooth', 'autoconnect')
            timeout = None
            if standby_devices:
                try:
                    timeout = int(oe.read_setting('bluetooth', 'idle_timeout'))
                except TypeError:
                    pass
            if timeout and xbmc.getGlobalIdleTime() / 60 >= timeout:
                log.log('Idle timeout reached', log.DEBUG)
                oe.standby_devices()
            else:
                log.log('Autoconnect triggered', log.DEBUG)
                oe.autoconnect_devices()
        if hasattr(oe, 'winOeMain') and hasattr(oe.winOeMain, 'visible'):
            if oe.winOeMain.visible == True:
                oe.winOeMain.close()
        oe.stop_service()
        service_thread.stop()
        dbus_utils.LOOP_THREAD.stop()


if __name__ == '__main__':
    Monitor().run()
