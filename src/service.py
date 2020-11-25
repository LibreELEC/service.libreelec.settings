# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
# Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)
# Copyright (C) 2019-present Team LibreELEC (https://libreelec.tv)

import le
import oe
import os
import socket
import threading
import xbmc


class ServiceThread(threading.Thread):

    @le.log_function
    def __init__(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.setblocking(1)
        if os.path.exists(le.SOCKET):
            os.remove(le.SOCKET)
        self.sock.bind(le.SOCKET)
        self.sock.listen(1)
        self.stopped = False
        threading.Thread.__init__(self)
        self.daemon = True

    @le.log_function
    def run(self):
        if oe.read_setting('libreelec', 'wizard_completed') == None:
            threading.Thread(target=oe.openWizard).start()
        while self.stopped == False:
            oe.dbg_log('_service_::run', 'WAITING:', oe.LOGINFO)
            conn, addr = self.sock.accept()
            message = (conn.recv(1024)).decode('utf-8')
            oe.dbg_log('_service_::run', 'MESSAGE:' +
                       message, oe.LOGINFO)
            conn.close()
            if message == 'openConfigurationWindow':
                if not hasattr(oe, 'winOeMain'):
                    threading.Thread(
                        target=oe.openConfigurationWindow).start()
                else:
                    if oe.winOeMain.visible != True:
                        threading.Thread(
                            target=oe.openConfigurationWindow).start()
            if message == 'exit':
                self.stopped = True

    @le.log_function
    def stop(self):
        self.stopped = True
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(le.SOCKET)
        sock.send(bytes('exit', 'utf-8'))
        sock.close()
        self.sock.close()


class Monitor(xbmc.Monitor):

    @le.log_function
    def onDPMSActivated(self):
        if oe.read_setting('bluetooth', 'standby'):
            threading.Thread(target=oe.standby_devices).start()

    @le.log_function
    def onScreensaverActivated(self):
        if oe.read_setting('bluetooth', 'standby'):
            threading.Thread(target=oe.standby_devices).start()


monitor = Monitor()
oe.load_modules()
oe.start_service()
service_thread = ServiceThread()
service_thread.start()

while not monitor.abortRequested():
    if monitor.waitForAbort(60):
        break

    if not oe.read_setting('bluetooth', 'standby'):
        continue

    timeout = oe.read_setting('bluetooth', 'idle_timeout')
    if not timeout:
        continue

    try:
        timeout = int(timeout)
    except:
        continue

    if timeout < 1:
        continue

    if xbmc.getGlobalIdleTime() / 60 >= timeout:
        oe.dbg_log('service', 'idle timeout reached', oe.LOGDEBUG)
        oe.standby_devices()

if hasattr(oe, 'winOeMain') and hasattr(oe.winOeMain, 'visible'):
    if oe.winOeMain.visible == True:
        oe.winOeMain.close()

oe.stop_service()
service_thread.stop()
