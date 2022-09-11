# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
# Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)
# Copyright (C) 2019-present Team LibreELEC (https://libreelec.tv)

################################# variables ##################################

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import os
import re
import locale
import sys
import urllib.request, urllib.error, urllib.parse
import time
import tarfile
import traceback
import subprocess
import defaults
import shutil
import hashlib, binascii
import dbus_systemd

from xml.dom import minidom
import imp

from xbmc import LOGDEBUG, LOGINFO, LOGWARNING, LOGERROR

__author__ = 'LibreELEC'
__scriptid__ = 'service.libreelec.settings'
__addon__ = xbmcaddon.Addon(id=__scriptid__)
__cwd__ = __addon__.getAddonInfo('path')
__oe__ = sys.modules[globals()['__name__']]
__media__ = f'{__cwd__}/resources/skins/Default/media'
xbmcDialog = xbmcgui.Dialog()

xbmcm = xbmc.Monitor()

is_service = False
conf_lock = False
xbmcIsPlaying = 0
input_request = False
dictModules = {}
listObject = {
    'list': 1100,
    'netlist': 1200,
    'btlist': 1300,
    'other': 1900,
    'test': 900,
    }
CANCEL = (
    9,
    10,
    216,
    247,
    257,
    275,
    61467,
    92,
    61448,
    )

###############################################################################
########################## initialize module ##################################
## set default encoding

try:
    encoding = locale.getpreferredencoding(do_setlocale=True)
    imp.reload(sys)
    # sys.setdefaultencoding(encoding)
except Exception as e:
    xbmc.log(f'## LibreELEC Addon ## oe:encoding: ERROR: ({repr(e)})', LOGERROR)

## load oeSettings modules

import oeWindows
xbmc.log(f"## LibreELEC Addon ## {str(__addon__.getAddonInfo('version'))}")

class PINStorage:
    def __init__(self, module='system', prefix='pinlock', maxAttempts=4, delay=300):
        self.module = module
        self.prefix = prefix
        self.maxAttempts = maxAttempts
        self.delay = delay

        self.now = 0.0

        self.enabled = self.read('enable')
        self.salthash = self.read('pin')
        self.numFail = self.read('numFail')
        self.timeFail = self.read('timeFail')

        self.enabled = '0' if (self.enabled is None or self.enabled != '1') else '1'
        self.salthash = None if (self.salthash is None or self.salthash == '') else self.salthash
        self.numFail = 0 if (self.numFail is None or int(self.numFail) < 0) else int(self.numFail)
        self.timeFail = 0.0 if (self.timeFail is None or float(self.timeFail) <= 0.0) else float(self.timeFail)

        # Remove impossible configurations - if enabled we must have a valid hash, and vice versa.
        if self.isEnabled() != self.isSet():
            self.disable()

    def read(self, item):
        value = read_setting(self.module, f'{self.prefix}_{item}')
        return None if value == '' else value

    def write(self, item, value):
        return write_setting(self.module, f'{self.prefix}_{item}', str(value) if value else '')

    def isEnabled(self):
        return self.enabled == '1'

    def isSet(self):
        return self.salthash is not None

    def enable(self):
        if not self.isEnabled():
            self.enabled = '1'
            self.write('enable', self.enabled)

    def disable(self):
        if self.isEnabled():
            self.enabled = '0'
            self.write('enable', self.enabled)
        self.set(None)

    def set(self, value):
        oldSaltHash = self.salthash

        if value:
            salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
            newhash = hashlib.pbkdf2_hmac('sha512', value.encode('utf-8'), salt, 100000)
            newhash = binascii.hexlify(newhash)
            self.salthash = (salt + newhash).decode('ascii')
        else:
            self.salthash = None

        if self.salthash != oldSaltHash:
            self.write('pin', self.salthash)

    def verify(self, value):
        salt = self.salthash[:64].encode('ascii')
        oldhash = self.salthash[64:]
        newhash = hashlib.pbkdf2_hmac('sha512', value.encode('utf-8'), salt, 100000)
        newhash = binascii.hexlify(newhash).decode('ascii')
        return oldhash == newhash

    def fail(self):
        self.numFail += 1
        self.timeFail = time.time()
        self.write('numFail', self.numFail)
        self.write('timeFail', self.timeFail)

    def success(self):
        if self.numFail != 0 or self.timeFail != 0.0:
            self.numFail = 0
            self.timeFail = 0.0
            self.write('numFail', self.numFail)
            self.write('timeFail', self.timeFail)

    def isDelayed(self):
        self.now = time.time()

        if self.attemptsRemaining() > 0:
            return False

        if self.delayRemaining() > 0.0:
            return True

        self.success()
        return False

    def delayRemaining(self):
        elapsed = self.now - self.timeFail
        return (self.delay - elapsed) if elapsed < self.delay else 0.0

    def attemptsRemaining(self):
        return (self.maxAttempts - self.numFail)

class ProgressDialog:
    def __init__(self, label1=32181, label2=32182, label3=32183, minSampleInterval=1.0, maxUpdatesPerSecond=5):
        self.label1 = _(label1)
        self.label2 = _(label2)
        self.label3 = _(label3)
        self.minSampleInterval = minSampleInterval
        self.maxUpdatesPerSecond = 1 / maxUpdatesPerSecond

        self.dialog = None

        self.source = None
        self.total_size = 0

        self.reset()

    def reset(self):
        self.percent = 0
        self.speed = 0

        self.partial_size = 0
        self.prev_size = 0

        self.start = 0
        self.last_update = 0
        self.minutes = 0
        self.seconds = 0

        self.cancelled = False

    def setSource(self, source):
        self.source = source

    def setSize(self, total_size):
        self.total_size = total_size

    def getPercent(self):
        return self.percent

    def getSpeed(self):
        return self.speed

    def open(self, heading='LibreELEC', line1='', line2='', line3=''):
        self.dialog = xbmcgui.DialogProgress()
        self.dialog.create(heading, f'{line1}\n{line2}\n{line3}')
        self.reset()

    def update(self, chunk):
        if self.dialog and self.needsUpdate(chunk):
            line1 = f'{self.label1}: {self.source.rsplit("/", 1)[1]}'
            line2 = f'{self.label2}: {self.speed:,} KB/s'
            line3 = f'{self.label3}: {self.minutes} m {self.seconds} s'
            self.dialog.update(self.percent, f'{line1}\n{line2}\n{line3}')
            self.last_update = time.time()

    def close(self):
        if self.dialog:
            self.dialog.close()
        self.dialog = None

    # Calculate current speed at regular intervals, or upon completion
    def sample(self, chunk):
        self.partial_size += len(chunk)

        now = time.time()
        if self.start == 0:
            self.start = now

        if (now - self.start) >= self.minSampleInterval or not chunk:
            self.speed = max(int((self.partial_size - self.prev_size) / (now - self.start) / 1024), 1)
            remain = self.total_size - self.partial_size
            self.minutes = int(remain / 1024 / self.speed / 60)
            self.seconds = int(remain / 1024 / self.speed) % 60
            self.prev_size = self.partial_size
            self.start = now

        if self.total_size != 0:
            self.percent = int(self.partial_size * 100.0 / self.total_size)

    # Update the progress dialog when required, or upon completion
    def needsUpdate(self, chunk):
        if not chunk:
            return True
        else:
            return ((time.time() - self.last_update) >= self.maxUpdatesPerSecond)

    def iscanceled(self):
        if self.dialog:
            self.cancelled = self.dialog.iscanceled()
        return self.cancelled

def _(code):
    wizardComp = read_setting('libreelec', 'wizard_completed')
    if wizardComp == "True":
        codeNew = __addon__.getLocalizedString(code)
    else:
        curLang = read_setting("system", "language")
        if curLang is not None:
            lang_file = os.path.join(__cwd__, 'resources', 'language', str(curLang), 'strings.po')
            with open(lang_file, encoding='utf-8') as fp:
                contents = fp.read().split('\n\n')
                for strings in contents:
                    if str(code) in strings:
                        subString = strings.split('msgstr ')[1]
                        subStringClean = re.sub('"', '', subString)
                        codeNew = subStringClean
                        break
                    else:
                        codeNew = __addon__.getLocalizedString(code)
        else:
            codeNew = __addon__.getLocalizedString(code)
    return codeNew


def dbg_log(source, text, level=LOGERROR):
    if level == LOGDEBUG and os.environ.get('DEBUG', 'no') == 'no':
        return
    xbmc.log(f"## LibreELEC Addon ## {source} ## {text}", level)
    if level == LOGERROR:
        tracedata = traceback.format_exc()
        if tracedata != "NoneType: None\n":
            xbmc.log(tracedata, level)

def notify(title, message, icon='icon'):
    try:
        dbg_log('oe::notify', 'enter_function', LOGDEBUG)
        msg = f'Notification("{title}", "{message[0:64]}", 5000, "{__media__}/{icon}.png")'
        xbmc.executebuiltin(msg)
        dbg_log('oe::notify', 'exit_function', LOGDEBUG)
    except Exception as e:
        dbg_log('oe::notify', f'ERROR: ({repr(e)})')


def execute(command_line, get_result=0):
    try:
        dbg_log('oe::execute', 'enter_function', LOGDEBUG)
        dbg_log('oe::execute::command', command_line, LOGDEBUG)
        if get_result == 0:
            process = subprocess.Popen(command_line, shell=True, close_fds=True)
            process.wait()
        else:
            result = ''
            process = subprocess.Popen(command_line, shell=True, close_fds=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            process.wait()
            for line in process.stdout.readlines():
                result = result + line.decode('utf-8')
            return result
        dbg_log('oe::execute', 'exit_function', LOGDEBUG)
    except Exception as e:
        dbg_log('oe::execute', f'ERROR: ({repr(e)})')


def enable_service(service):
    try:
        if os.path.exists(f'{CONFIG_CACHE}/services/{service}'):
            pass
        if os.path.exists(f'{CONFIG_CACHE}/services/{service}.disabled'):
            pass
        service_file = f'{CONFIG_CACHE}/services/{service}'
    except Exception as e:
        dbg_log('oe::enable_service', f'ERROR: ({repr(e)})')


def set_service_option(service, option, value):
    try:
        lines = []
        changed = False
        conf_file_name = f'{CONFIG_CACHE}/services/{service}.conf'
        if os.path.isfile(conf_file_name):
            with open(conf_file_name, 'r') as conf_file:
                for line in conf_file:
                    if option in line:
                        line = f'{option}={value}'
                        changed = True
                    lines.append(line.strip())
        if changed == False:
            lines.append(f'{option}={value}')
        with open(conf_file_name, 'w') as conf_file:
            conf_file.write('\n'.join(lines) + '\n')
    except Exception as e:
        dbg_log('oe::set_service_option', f'ERROR: ({repr(e)})')


def get_service_option(service, option, default=None):
    try:
        lines = []
        conf_file_name = ''
        if os.path.exists(f'{CONFIG_CACHE}/services/{service}.conf'):
            conf_file_name = f'{CONFIG_CACHE}/services/{service}.conf'
        if os.path.exists(f'{CONFIG_CACHE}/services/{service}.disabled'):
            conf_file_name = f'{CONFIG_CACHE}/services/{service}.disabled'
        if os.path.exists(conf_file_name):
            with open(conf_file_name, 'r') as conf_file:
                for line in conf_file:
                    if option in line:
                        if '=' in line:
                            default = line.strip().split('=')[-1]
        return default
    except Exception as e:
        dbg_log('oe::get_service_option', f'ERROR: ({repr(e)})')


def get_service_state(service):
    try:
        if os.path.exists(f'{CONFIG_CACHE}/services/{service}.conf'):
            return '1'
        else:
            return '0'
    except Exception as e:
        dbg_log('oe::get_service_state', f'ERROR: ({repr(e)})')


def set_service(service, options, state):
    try:
        dbg_log('oe::set_service', 'enter_function', LOGDEBUG)
        dbg_log('oe::set_service::service', repr(service), LOGDEBUG)
        dbg_log('oe::set_service::options', repr(options), LOGDEBUG)
        dbg_log('oe::set_service::state', repr(state), LOGDEBUG)
        config = {}
        changed = False

        # Service Enabled

        if state == 1:

            # Is Service alwys enabled ?

            if get_service_state(service) == '1':
                cfn = f'{CONFIG_CACHE}/services/{service}.conf'
                cfo = cfn
            else:
                cfn = f'{CONFIG_CACHE}/services/{service}.conf'
                cfo = f'{CONFIG_CACHE}/services/{service}.disabled'
            if os.path.exists(cfo) and not cfo == cfn:
                os.remove(cfo)
            with open(cfn, 'w') as cf:
                for option in options:
                    cf.write(f'{option}={options[option]}\n')
        else:

        # Service Disabled

            cfo = f'{CONFIG_CACHE}/services/{service}.conf'
            cfn = f'{CONFIG_CACHE}/services/{service}.disabled'
            if os.path.exists(cfo):
                os.rename(cfo, cfn)
        if not __oe__.is_service:
            if service in defaults._services:
                for svc in defaults._services[service]:
                    dbus_systemd.restart_unit(svc)
        dbg_log('oe::set_service', 'exit_function', LOGDEBUG)
    except Exception as e:
        dbg_log('oe::set_service', f'ERROR: ({repr(e)})')


def load_file(filename):
    try:
        if os.path.isfile(filename):
            objFile = open(filename, 'r', encoding='utf-8')
            content = objFile.read()
            objFile.close()
        else:
            content = ''
        return content.strip()
    except Exception as e:
        dbg_log(f'oe::load_file({filename})', f'ERROR: ({repr(e)})')

def url_quote(var):
    return urllib.parse.quote(var, safe="")

def load_url(url):
    try:
        request = urllib.request.Request(url)
        response = urllib.request.urlopen(request)
        content = response.read()
        return content.decode('utf-8').strip()
    except Exception as e:
        dbg_log(f'oe::load_url({url})', f'ERROR: ({repr(e)})')


def download_file(source, destination, silent=False):
    try:
        local_file = open(destination, 'wb')

        response = urllib.request.urlopen(urllib.parse.quote(source, safe=':/'))

        progress = ProgressDialog()
        if not silent:
            progress.open()

        progress.setSource(source)
        progress.setSize(int(response.getheader('Content-Length').strip()))

        last_percent = 0

        while not (progress.iscanceled() or xbmcm.abortRequested()):
            part = response.read(32768)

            progress.sample(part)

            if not silent:
                progress.update(part)
            else:
                if progress.getPercent() - last_percent > 5 or not part:
                    dbg_log(f'oe::download_file({destination})', f'{progress.getPercent()}%% with {progress.getSpeed()} KB/s', LOGINFO)
                    last_percent = progress.getPercent()

            if part:
                local_file.write(part)
            else:
                break

        progress.close()
        local_file.close()
        response.close()

        if progress.iscanceled() or xbmcm.abortRequested():
            os.remove(destination)
            return None

        return destination

    except Exception as e:
        dbg_log(f'oe::download_file({source},{destination})', f'ERROR: ({repr(e)})')


def copy_file(source, destination, silent=False):
    try:
        dbg_log('oe::copy_file', f'SOURCE: {source}, DEST: {destination}', LOGINFO)

        source_file = open(source, 'rb')
        destination_file = open(destination, 'wb')

        progress = ProgressDialog()
        if not silent:
            progress.open()

        progress.setSource(source)
        progress.setSize(os.path.getsize(source))

        last_percent = 0

        while not (progress.iscanceled() or xbmcm.abortRequested()):
            part = source_file.read(32768)

            progress.sample(part)

            if not silent:
                progress.update(part)
            else:
                if progress.getPercent() - last_percent > 5 or not part:
                    dbg_log(f'oe::copy_file({destination})', f'{progress.getPercent()}%% with {progress.getSpeed()} KB/s', LOGINFO)
                    last_percent = progress.getPercent()

            if part:
                destination_file.write(part)
            else:
                break

        progress.close()
        source_file.close()
        destination_file.close()

        if progress.iscanceled() or xbmcm.abortRequested():
            os.remove(destination)
            return None

        return destination

    except Exception as e:
        dbg_log(f'oe::copy_file({source},{destination})', f'ERROR: ({repr(e)})')


def start_service():
    global dictModules, __oe__
    try:
        __oe__.is_service = True
        for strModule in sorted(dictModules, key=lambda x: list(dictModules[x].menu.keys())):
            module = dictModules[strModule]
            if hasattr(module, 'start_service') and module.ENABLED:
                module.start_service()
        __oe__.is_service = False
    except Exception as e:
        dbg_log('oe::start_service', f'ERROR: ({repr(e)})')


def stop_service():
    global dictModules
    try:
        for strModule in dictModules:
            module = dictModules[strModule]
            if hasattr(module, 'stop_service') and module.ENABLED:
                module.stop_service()
        xbmc.log('## LibreELEC Addon ## STOP SERVICE DONE !')
    except Exception as e:
        dbg_log('oe::stop_service', f'ERROR: ({repr(e)})')


def openWizard():
    global winOeMain, __cwd__, __oe__
    try:
        winOeMain = oeWindows.wizard('service-LibreELEC-Settings-wizard.xml', __cwd__, 'Default', oeMain=__oe__)
        winOeMain.doModal()
        winOeMain = oeWindows.mainWindow('service-LibreELEC-Settings-mainWindow.xml', __cwd__, 'Default', oeMain=__oe__)  # None
    except Exception as e:
        dbg_log('oe::openWizard', f'ERROR: ({repr(e)})')


def openConfigurationWindow():
    global winOeMain, __cwd__, __oe__, dictModules, PIN
    try:
        match = True

        if PIN.isEnabled():
            match = False

            if PIN.isDelayed():
                timeleft = PIN.delayRemaining()
                timeleft_mins, timeleft_secs = divmod(timeleft, 60)
                timeleft_hours, timeleft_mins = divmod(timeleft_mins, 60)
                xbmcDialog.ok(_(32237), _(32238) % (timeleft_mins, timeleft_secs))
                return

            while PIN.attemptsRemaining() > 0:
                lockcode = xbmcDialog.numeric(0, _(32233), bHiddenInput=True)
                if lockcode == '':
                    break

                if PIN.verify(lockcode):
                    match = True
                    PIN.success()
                    break

                PIN.fail()

                if PIN.attemptsRemaining() > 0:
                    xbmcDialog.ok(_(32234), f'{PIN.attemptsRemaining()} {_(32235)}')

            if not match and PIN.attemptsRemaining() <= 0:
              xbmcDialog.ok(_(32234), _(32236))
              return

        if match == True:
            winOeMain = oeWindows.mainWindow('service-LibreELEC-Settings-mainWindow.xml', __cwd__, 'Default', oeMain=__oe__)
            winOeMain.doModal()
            for strModule in dictModules:
                dictModules[strModule].exit()
            winOeMain = None
            del winOeMain

    except Exception as e:
        dbg_log('oe::openConfigurationWindow', f'ERROR: ({repr(e)})')

def standby_devices():
    global dictModules
    try:
        if 'bluetooth' in dictModules:
            dictModules['bluetooth'].standby_devices()
    except Exception as e:
        dbg_log('oe::standby_devices', f'ERROR: ({repr(e)})')

def load_config():
    try:
        global conf_lock
        while conf_lock:
            time.sleep(0.2)
        conf_lock = True
        if os.path.exists(configFile):
            config_file = open(configFile, 'r')
            config_text = config_file.read()
            config_file.close()
        else:
            config_text = ''
        if config_text == '':
            xml_conf = minidom.Document()
            xml_main = xml_conf.createElement('libreelec')
            xml_conf.appendChild(xml_main)
            xml_sub = xml_conf.createElement('addon_config')
            xml_main.appendChild(xml_sub)
            xml_sub = xml_conf.createElement('settings')
            xml_main.appendChild(xml_sub)
            config_text = xml_conf.toprettyxml()
        else:
            xml_conf = minidom.parseString(config_text)
        conf_lock = False
        return xml_conf
    except Exception as e:
        dbg_log('oe::load_config', f'ERROR: ({repr(e)})')


def save_config(xml_conf):
    try:
        global configFile, conf_lock
        while conf_lock:
            time.sleep(0.2)
        conf_lock = True
        config_file = open(configFile, 'w')
        config_file.write(xml_conf.toprettyxml())
        config_file.close()
        conf_lock = False
    except Exception as e:
        dbg_log('oe::save_config', f'ERROR: ({repr(e)})')


def read_module(module):
    try:
        xml_conf = load_config()
        xml_settings = xml_conf.getElementsByTagName('settings')
        for xml_setting in xml_settings:
            for xml_modul in xml_setting.getElementsByTagName(module):
                return xml_modul
    except Exception as e:
        dbg_log('oe::read_module', f'ERROR: ({repr(e)})')


def read_node(node_name):
    try:
        xml_conf = load_config()
        xml_node = xml_conf.getElementsByTagName(node_name)
        value = {}
        for xml_main_node in xml_node:
            value[xml_main_node.nodeName] = {}
            for xml_sub_node in xml_main_node.childNodes:
                if len(xml_sub_node.childNodes) == 0:
                    continue
                value[xml_main_node.nodeName][xml_sub_node.nodeName] = {}
                for xml_value in xml_sub_node.childNodes:
                    if hasattr(xml_value.firstChild, 'nodeValue'):
                        value[xml_main_node.nodeName][xml_sub_node.nodeName][xml_value.nodeName] = xml_value.firstChild.nodeValue
                    else:
                        value[xml_main_node.nodeName][xml_sub_node.nodeName][xml_value.nodeName] = ''
        return value
    except Exception as e:
        dbg_log('oe::read_node', f'ERROR: ({repr(e)})')


def remove_node(node_name):
    try:
        xml_conf = load_config()
        xml_node = xml_conf.getElementsByTagName(node_name)
        for xml_main_node in xml_node:
            xml_main_node.parentNode.removeChild(xml_main_node)
        save_config(xml_conf)
    except Exception as e:
        dbg_log('oe::remove_node', f'ERROR: ({repr(e)})')


def read_setting(module, setting, default=None):
    try:
        xml_conf = load_config()
        xml_settings = xml_conf.getElementsByTagName('settings')
        value = default
        for xml_setting in xml_settings:
            for xml_modul in xml_setting.getElementsByTagName(module):
                for xml_modul_setting in xml_modul.getElementsByTagName(setting):
                    if hasattr(xml_modul_setting.firstChild, 'nodeValue'):
                        value = xml_modul_setting.firstChild.nodeValue
        return value
    except Exception as e:
        dbg_log('oe::read_setting', f'ERROR: ({repr(e)})')


def write_setting(module, setting, value, main_node='settings'):
    try:
        xml_conf = load_config()
        xml_settings = xml_conf.getElementsByTagName(main_node)
        if len(xml_settings) == 0:
            for xml_main in xml_conf.getElementsByTagName('libreelec'):
                xml_sub = xml_conf.createElement(main_node)
                xml_main.appendChild(xml_sub)
                xml_settings = xml_conf.getElementsByTagName(main_node)
        module_found = 0
        setting_found = 0
        for xml_setting in xml_settings:
            for xml_modul in xml_setting.getElementsByTagName(module):
                module_found = 1
                for xml_modul_setting in xml_modul.getElementsByTagName(setting):
                    setting_found = 1
        if setting_found == 1:
            if hasattr(xml_modul_setting.firstChild, 'nodeValue'):
                xml_modul_setting.firstChild.nodeValue = value
            else:
                xml_value = xml_conf.createTextNode(value)
                xml_modul_setting.appendChild(xml_value)
        else:
            if module_found == 0:
                xml_modul = xml_conf.createElement(module)
                xml_setting.appendChild(xml_modul)
            xml_setting = xml_conf.createElement(setting)
            xml_modul.appendChild(xml_setting)
            xml_value = xml_conf.createTextNode(value)
            xml_setting.appendChild(xml_value)
        save_config(xml_conf)
    except Exception as e:
        dbg_log('oe::write_setting', f'ERROR: ({repr(e)})')


def load_modules():

  # # load libreelec configuration modules

    try:
        global dictModules, __oe__, __cwd__, init_done
        for strModule in dictModules:
            dictModules[strModule] = None
        dict_names = {}
        dictModules = {}
        for file_name in sorted(os.listdir(f'{__cwd__}/resources/lib/modules')):
            if not file_name.startswith('__') and (file_name.endswith('.py') or file_name.endswith('.pyc')):
                (name, ext) = file_name.split('.')
                dict_names[name] = None
        for module_name in dict_names:
            try:
                if not module_name in dictModules:
                    dictModules[module_name] = getattr(__import__(module_name), module_name)(__oe__)
                    if hasattr(defaults, module_name):
                        for key in getattr(defaults, module_name):
                            setattr(dictModules[module_name], key, getattr(defaults, module_name)[key])
            except Exception as e:
                dbg_log('oe::MAIN(loadingModules)(strModule)', f'ERROR: ({repr(e)})')
    except Exception as e:
        dbg_log('oe::MAIN(loadingModules)', f'ERROR: ({repr(e)})')


def timestamp():
    localtime = time.localtime()
    return time.strftime('%Y%m%d%H%M%S', localtime)


def split_dialog_text(text):
    ret = [''] * 3
    txt = re.findall('.{1,60}(?:\W|$)', text)
    for x in range(0, 2):
        if len(txt) > x:
            ret[x] = txt[x]
    return ret


def reboot_counter(seconds=10, title=' '):
    reboot_dlg = xbmcgui.DialogProgress()
    reboot_dlg.create(f'LibreELEC {title}', ' ')
    reboot_dlg.update(0)
    wait_time = seconds
    while seconds >= 0 and not (reboot_dlg.iscanceled() or xbmcm.abortRequested()):
        progress = round(1.0 * seconds / wait_time * 100)
        reboot_dlg.update(int(progress), _(32329) % seconds)
        xbmcm.waitForAbort(1)
        seconds = seconds - 1
    if reboot_dlg.iscanceled() or xbmcm.abortRequested():
        return 0
    else:
        return 1


def exit():
    global WinOeSelect, winOeMain, __addon__, __cwd__, __oe__, _, dictModules

    # del winOeMain

    del dictModules
    del __addon__
    del __oe__
    del _


# fix for xml printout

def fixed_writexml(self, writer, indent='', addindent='', newl=''):
    writer.write(f'{indent}<{self.tagName}')
    attrs = self._get_attributes()
    a_names = list(attrs.keys())
    a_names.sort()
    for a_name in a_names:
        writer.write(f' {a_name}="')
        minidom._write_data(writer, attrs[a_name].value)
        writer.write('"')
    if self.childNodes:
        if len(self.childNodes) == 1 and self.childNodes[0].nodeType == minidom.Node.TEXT_NODE:
            writer.write('>')
            self.childNodes[0].writexml(writer, '', '', '')
            writer.write(f'</{self.tagName}>{newl}')
            return
        writer.write(f'>{newl}')
        for node in self.childNodes:
            if node.nodeType is not minidom.Node.TEXT_NODE:
                node.writexml(writer, indent + addindent, addindent, newl)
        writer.write(f'{indent}</{self.tagName}>{newl}')
    else:
        writer.write(f'/>{newl}')


def parse_os_release():
    os_release_fields = re.compile(r'(?!#)(?P<key>.+)=(?P<quote>[\'\"]?)(?P<value>.+)(?P=quote)$')
    os_release_unescape = re.compile(r'\\(?P<escaped>[\'\"\\])')
    try:
        with open('/etc/os-release') as f:
            info = {}
            for line in f:
                m = re.match(os_release_fields, line)
                if m is not None:
                    key = m.group('key')
                    value = re.sub(os_release_unescape, r'\g<escaped>', m.group('value'))
                    info[key] = value
            return info
    except OSError:
        return None


def get_os_release():
    distribution = version = architecture = build = project = device = builder_name = builder_version = ''
    os_release_info = parse_os_release()
    if os_release_info is not None:
        if 'NAME' in os_release_info:
            distribution = os_release_info['NAME']
        if 'VERSION_ID' in os_release_info:
            version = os_release_info['VERSION_ID']
        if 'VERSION' in os_release_info:
            version = os_release_info['VERSION']
        if 'LIBREELEC_ARCH' in os_release_info:
            architecture = os_release_info['LIBREELEC_ARCH']
        if 'LIBREELEC_BUILD' in os_release_info:
            build = os_release_info['LIBREELEC_BUILD']
        if 'LIBREELEC_PROJECT' in os_release_info:
            project = os_release_info['LIBREELEC_PROJECT']
        if 'LIBREELEC_DEVICE' in os_release_info:
            device = os_release_info['LIBREELEC_DEVICE']
        if 'BUILDER_NAME' in os_release_info:
            builder_name = os_release_info['BUILDER_NAME']
        if 'BUILDER_VERSION' in os_release_info:
            builder_version = os_release_info['BUILDER_VERSION']
        return (
            distribution,
            version,
            architecture,
            build,
            project,
            device,
            builder_name,
            builder_version
            )

minidom.Element.writexml = fixed_writexml

############################################################################################
# Base Environment
############################################################################################

os_release_data = get_os_release()
DISTRIBUTION = os_release_data[0]
VERSION = os_release_data[1]
ARCHITECTURE = os_release_data[2]
BUILD = os_release_data[3]
PROJECT = os_release_data[4]
DEVICE = os_release_data[5]
BUILDER_NAME = os_release_data[6]
BUILDER_VERSION = os_release_data[7]
DOWNLOAD_DIR = '/storage/downloads'
XBMC_USER_HOME = os.environ.get('XBMC_USER_HOME', '/storage/.kodi')
CONFIG_CACHE = os.environ.get('CONFIG_CACHE', '/storage/.cache')
USER_CONFIG = os.environ.get('USER_CONFIG', '/storage/.config')
TEMP = f'{XBMC_USER_HOME}/temp/'
winOeMain = oeWindows.mainWindow('service-LibreELEC-Settings-mainWindow.xml', __cwd__, 'Default', oeMain=__oe__)
if os.path.exists('/etc/machine-id'):
    SYSTEMID = load_file('/etc/machine-id')
else:
    SYSTEMID = os.environ.get('SYSTEMID', '')

if PROJECT == 'RPi':
  RPI_CPU_VER = execute('vcgencmd otp_dump 2>/dev/null | grep 30: | cut -c8', get_result=1).replace('\n','')
else:
  RPI_CPU_VER = ''

BOOT_STATUS = load_file('/storage/.config/boot.status')

############################################################################################

try:
    configFile = f'{XBMC_USER_HOME}/userdata/addon_data/service.libreelec.settings/oe_settings.xml'
    if not os.path.exists(f'{XBMC_USER_HOME}/userdata/addon_data/service.libreelec.settings'):
        os.makedirs(f'{XBMC_USER_HOME}/userdata/addon_data/service.libreelec.settings')
    if not os.path.exists(f'{CONFIG_CACHE}/services'):
        os.makedirs(f'{CONFIG_CACHE}/services')
except:
    pass

PIN = PINStorage()
