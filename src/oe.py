################################################################################
#      This file is part of OpenELEC - http://www.openelec.tv
#      Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
#      Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)
#
#  This program is dual-licensed; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with OpenELEC; see the file COPYING.  If not, see
#  <http://www.gnu.org/licenses/>.
#
#  Alternatively, you can license this library under a commercial license,
#  please contact OpenELEC Licensing for more information.
#
#  For more information contact:
#  OpenELEC Licensing  <license@openelec.tv>  http://www.openelec.tv
################################################################################
# -*- coding: utf-8 -*-
################################# variables ##################################

import xbmc
import xbmcaddon
import xbmcgui
import os
import re
import locale
import sys
import urllib2
import time
import tarfile
import traceback
import subprocess
import dbus
import dbus.mainloop.glib
import defaults

from xml.dom import minidom

__author__ = 'LibreELEC'
__scriptid__ = 'service.libreelec.settings'
__addon__ = xbmcaddon.Addon(id=__scriptid__)
__cwd__ = __addon__.getAddonInfo('path')
__oe__ = sys.modules[globals()['__name__']]
__media__ = '%s/resources/skins/Default/media' % __cwd__

is_service = False
conf_lock = False
__busy__ = 0
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

try:
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
except:
    pass

dbusSystemBus = dbus.SystemBus()

###############################################################################
########################## initialize module ##################################
## append resource subfolders to path

sys.path.append(xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')))
sys.path.append(xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib', 'modules')))

## set default encoding

encoding = locale.getpreferredencoding(do_setlocale=True)
reload(sys)
sys.setdefaultencoding(encoding)

## load oeSettings modules

import oeWindows
xbmc.log('## LibreELEC Addon ## ' + unicode(__addon__.getAddonInfo('version')))


def _(code):
    return __addon__.getLocalizedString(code)


def dbg_log(source, text, level=4):
    if os.environ.get('DEBUG', 'no') == 'no':
        return
    xbmc.log('## LibreELEC Addon ## ' + source + ' ## ' + text, level)
    xbmc.log(traceback.format_exc())


def notify(title, message, icon='icon'):
    try:
        dbg_log('oe::notify', 'enter_function', 0)
        msg = 'Notification("%s", "%s", 5000, "%s/icons/%s.png")' % (
            title,
            message[0:64],
            __media__,
            icon,
            )
        xbmc.executebuiltin(msg)
        dbg_log('oe::notify', 'exit_function', 0)
    except Exception, e:
        dbg_log('oe::notify', 'ERROR: (' + repr(e) + ')')


def execute(command_line, get_result=0):
    try:
        dbg_log('oe::execute', 'enter_function', 0)
        dbg_log('oe::execute::command', command_line, 0)
        if get_result == 0:
            process = subprocess.Popen(command_line, shell=True, close_fds=True)
            process.wait()
        else:
            result = ''
            process = subprocess.Popen(command_line, shell=True, close_fds=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            process.wait()
            for line in process.stdout.readlines():
                result = result + line
            return result
        dbg_log('oe::execute', 'exit_function', 0)
    except Exception, e:
        dbg_log('oe::execute', 'ERROR: (' + repr(e) + ')')


def enable_service(service):
    try:
        if os.path.exists('%s/services/%s' % (CONFIG_CACHE, service)):
            pass
        if os.path.exists('%s/services/%s.disabled' % (CONFIG_CACHE, service)):
            pass
        service_file = '%s/services/%s' % (CONFIG_CACHE, service)
    except Exception, e:
        dbg_log('oe::set_service_cmd', 'ERROR: (' + repr(e) + ')')


def set_service_option(service, option, value):
    try:
        lines = []
        changed = False
        conf_file_name = '%s/services/%s.conf' % (CONFIG_CACHE, service)
        if os.path.isfile(conf_file_name):
            with open(conf_file_name, 'r') as conf_file:
                for line in conf_file:
                    if option in line:
                        line = '%s=%s' % (option, value)
                        changed = True
                    lines.append(line.strip())
        if changed == False:
            lines.append('%s=%s' % (option, value))
        with open(conf_file_name, 'w') as conf_file:
            conf_file.write('\n'.join(lines) + '\n')
    except Exception, e:
        dbg_log('oe::set_service_option', 'ERROR: (' + repr(e) + ')')


def get_service_option(service, option, default=None):
    try:
        lines = []
        conf_file_name = ''
        if os.path.exists('%s/services/%s.conf' % (CONFIG_CACHE, service)):
            conf_file_name = '%s/services/%s.conf' % (CONFIG_CACHE, service)
        if os.path.exists('%s/services/%s.disabled' % (CONFIG_CACHE, service)):
            conf_file_name = '%s/services/%s.disabled' % (CONFIG_CACHE, service)
        if os.path.exists(conf_file_name):
            with open(conf_file_name, 'r') as conf_file:
                for line in conf_file:
                    if option in line:
                        if '=' in line:
                            default = line.strip().split('=')[-1]
        return default
    except Exception, e:
        dbg_log('oe::get_service_option', 'ERROR: (' + repr(e) + ')')


def get_service_state(service):
    try:
        if os.path.exists('%s/services/%s.conf' % (CONFIG_CACHE, service)):
            return '1'
        else:
            return '0'
    except Exception, e:
        dbg_log('oe::get_service_state', 'ERROR: (' + repr(e) + ')')


def set_service(service, options, state):
    try:
        dbg_log('oe::set_service', 'enter_function')
        config = {}
        changed = False

        # Service Enabled

        if state == 1:

            # Is Service alwys enabled ?

            if get_service_state(service) == '1':
                cfn = '%s/services/%s.conf' % (CONFIG_CACHE, service)
                cfo = cfn
            else:
                cfn = '%s/services/%s.conf' % (CONFIG_CACHE, service)
                cfo = '%s/services/%s.disabled' % (CONFIG_CACHE, service)
            if os.path.exists(cfo) and not cfo == cfn:
                os.remove(cfo)
            with open(cfn, 'w') as cf:
                for option in options:
                    cf.write('%s=%s\n' % (option, options[option]))
        else:

        # Service Disabled

            cfo = '%s/services/%s.conf' % (CONFIG_CACHE, service)
            cfn = '%s/services/%s.disabled' % (CONFIG_CACHE, service)
            if os.path.exists(cfo):
                os.rename(cfo, cfn)
        if not __oe__.is_service:
            if service in defaults._services:
                for svc in defaults._services[service]:
                    execute('systemctl restart %s' % svc)
        dbg_log('oe::set_service', 'exit_function')
    except Exception, e:
        dbg_log('oe::set_service_option', 'ERROR: (' + repr(e) + ')')


def load_file(filename):
    try:
        if os.path.isfile(filename):
            objFile = open(filename, 'r')
            content = objFile.read()
            objFile.close()
        else:
            content = ''
        return content.strip()
    except Exception, e:
        dbg_log('oe::load_file(' + filename + ')', 'ERROR: (' + repr(e) + ')')


def load_url(url):
    try:
        request = urllib2.Request(url)
        response = urllib2.urlopen(request)
        content = response.read()
        return content.strip()
    except Exception, e:
        dbg_log('oe::load_url(' + url + ')', 'ERROR: (' + repr(e) + ')')


def download_file(source, destination, silent=False):
    try:
        local_file = open(destination, 'wb')
        if silent == False:
            download_dlg = xbmcgui.DialogProgress()
            download_dlg.create('LibreELEC', _(32181).encode('utf-8'), ' ', ' ')
        response = urllib2.urlopen(source)
        total_size = int(response.info().getheader('Content-Length').strip())
        minutes = 0
        seconds = 0
        rest = 0
        speed = 1
        start = time.time()
        size = 0
        part_size = 0
        last_percent = 0
        while 1:
            part = response.read(32768)
            part_size += len(part)
            if time.time() > start + 2:
                speed = int((part_size - size) / (time.time() - start) / 1024)
                start = time.time()
                size = part_size
                rest = total_size - part_size
                minutes = rest / 1024 / speed / 60
                seconds = rest / 1024 / speed - minutes * 60
            percent = int(part_size * 100.0 / total_size)
            if silent == False:
                download_dlg.update(percent, _(32181) + ':  %s' % source.rsplit('/', 1)[1], _(32182) + ':  %d KB/s' % speed, _(32183)
                                    + ':  %d m %d s' % (minutes, seconds))
                if download_dlg.iscanceled():
                    os.remove(destination)
                    local_file.close()
                    response.close()
                    return None
            else:
                if percent > last_percent + 5:
                    dbg_log('oe::download_file(' + destination + ')', '%d percent with %d KB/s' % (percent, speed))
                    last_percent = percent
            if not part or xbmc.abortRequested:
                break
            local_file.write(part)
        local_file.close()
        response.close()
        return destination
    except Exception, e:
        dbg_log('oe::download_file(' + source + ', ' + destination + ')', 'ERROR: (' + repr(e) + ')')


def extract_file(filename, extract, destination, silent=False):
    try:
        if tarfile.is_tarfile(filename):
            if silent == False:
                extract_dlg = xbmcgui.DialogProgress()
                extract_dlg.create('LibreELEC ', _(32186).encode('utf-8'), ' ', ' ')
                extract_dlg.update(0)
            compressed = tarfile.open(filename)
            if silent == False:
                xbmc.executebuiltin('ActivateWindow(busydialog)')
            names = compressed.getnames()
            if silent == False:
                xbmc.executebuiltin('Dialog.Close(busydialog)')
            for name in names:
                for search in extract:
                    if search in name:
                        fileinfo = compressed.getmember(name)
                        response = compressed.extractfile(fileinfo)
                        local_file = open(destination + name.rsplit('/', 1)[1], 'wb')
                        total_size = fileinfo.size
                        minutes = 0
                        seconds = 0
                        rest = 1
                        speed = 1
                        start = time.time()
                        size = 1
                        part_size = 1
                        last_percent = 0
                        while 1:
                            part = response.read(32768)
                            part_size += len(part)
                            if silent == False:
                                if extract_dlg.iscanceled():
                                    local_file.close()
                                    response.close()
                                    return None
                            if not part or xbmc.abortRequested:
                                break
                            if time.time() > start + 2:
                                speed = int((part_size - size) / (time.time() - start) / 1024)
                                start = time.time()
                                size = part_size
                                rest = total_size - part_size
                                minutes = rest / 1024 / speed / 60
                                seconds = rest / 1024 / speed - minutes * 60
                            percent = int(part_size * 100.0 / total_size)
                            if silent == False:
                                extract_dlg.update(percent, _(32184) + ':  %s' % name.rsplit('/', 1)[1], _(32185) + ':  %d KB/s' % speed,
                                                   _(32183) + ':  %d m %d s' % (minutes, seconds))
                                if extract_dlg.iscanceled():
                                    local_file.close()
                                    response.close()
                                    return None
                            else:
                                if percent > last_percent + 5:
                                    dbg_log('oe::extract_file(' + destination + name.rsplit('/', 1)[1] + ')', '%d percent with %d KB/s'
                                            % (percent, speed))
                                    last_percent = percent
                            local_file.write(part)
                        local_file.close()
                        response.close()
        return 1
    except Exception, e:
        dbg_log('oe::extract_file', 'ERROR: (' + repr(e) + ')')


def copy_file(source, destination, silent=False):
    try:
        dbg_log('oe::copy_file', 'SOURCE: %s, DEST: %s' % (source, destination))
        source_file = open(source, 'rb')
        destination_file = open(destination, 'wb')
        if silent == False:
            copy_dlg = xbmcgui.DialogProgress()
            copy_dlg.create('LibreELEC', _(32181).encode('utf-8'), ' ', ' ')
        total_size = os.path.getsize(source)
        minutes = 0
        seconds = 0
        rest = 0
        speed = 1
        start = time.time()
        size = 0
        part_size = 0
        last_percent = 0
        while 1:
            part = source_file.read(32768)
            part_size += len(part)
            if time.time() > start + 2:
                speed = int((part_size - size) / (time.time() - start) / 1024)
                start = time.time()
                size = part_size
                rest = total_size - part_size
                minutes = rest / 1024 / speed / 60
                seconds = rest / 1024 / speed - minutes * 60
            percent = int(part_size * 100.0 / total_size)
            if silent == False:
                copy_dlg.update(percent, _(32181) + ':  %s' % source.rsplit('/', 1)[1], _(32182) + ':  %d KB/s' % speed, _(32183)
                                + ':  %d m %d s' % (minutes, seconds))
                if copy_dlg.iscanceled():
                    source_file.close()
                    destination_file.close()
                    return None
            else:
                if percent > last_percent + 5:
                    dbg_log('oe::copy_file(' + destination + ')', '%d percent with %d KB/s' % (percent, speed))
                    last_percent = percent
            if not part or xbmc.abortRequested:
                break
            destination_file.write(part)
        source_file.close()
        destination_file.close()
        return destination
    except Exception, e:
        dbg_log('oe::copy_file(' + source + ', ' + destination + ')', 'ERROR: (' + repr(e) + ')')


def set_busy(state):
    global __busy__, __oe__, input_request, is_service
    try:
        if not is_service:
            if state == 1:
                __busy__ = __busy__ + 1
            else:
                __busy__ = __busy__ - 1
            dbg_log('oe::set_busy', '__busy__ = ' + unicode(__busy__), 0)
            if __busy__ > 0:
                if not input_request:
                    xbmc.executebuiltin('ActivateWindow(busydialog)')
            else:
                xbmc.executebuiltin('Dialog.Close(busydialog)')
    except Exception, e:
        dbg_log('oe::set_busy', 'ERROR: (' + repr(e) + ')', 4)


def start_service():
    global dictModules, __oe__
    try:
        __oe__.is_service = True
        for strModule in sorted(dictModules, key=lambda x: dictModules[x].menu.keys()):
            if hasattr(dictModules[strModule], 'start_service'):
                dictModules[strModule].start_service()
        __oe__.is_service = False
    except Exception, e:
        dbg_log('oe::start_service', 'ERROR: (' + repr(e) + ')')


def stop_service():
    global dictModules
    try:
        for strModule in dictModules:
            if hasattr(dictModules[strModule], 'stop_service'):
                dictModules[strModule].stop_service()
        xbmc.log('## LibreELEC Addon ## STOP SERVICE DONE !')
    except Exception, e:
        dbg_log('oe::stop_service', 'ERROR: (' + repr(e) + ')')


def openWizard():
    global winOeMain, __cwd__, __oe__
    try:
        winOeMain = oeWindows.wizard('wizard.xml', __cwd__, 'Default', oeMain=__oe__)
        winOeMain.doModal()
        winOeMain = oeWindows.mainWindow('mainWindow.xml', __cwd__, 'Default', oeMain=__oe__)  # None
    except Exception, e:
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        dbg_log('oe::openWizard', 'ERROR: (' + repr(e) + ')')


def openConfigurationWindow():
    global winOeMain, __cwd__, __oe__, dictModules
    try:
        winOeMain = oeWindows.mainWindow('mainWindow.xml', __cwd__, 'Default', oeMain=__oe__)
        winOeMain.doModal()
        for strModule in dictModules:
            dictModules[strModule].exit()
        winOeMain = None
        del winOeMain
    except Exception, e:
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        dbg_log('oe::openConfigurationWindow', 'ERROR: (' + repr(e) + ')')


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
    except Exception, e:
        dbg_log('oe::load_config', 'ERROR: (' + repr(e) + ')')


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
    except Exception, e:
        dbg_log('oe::save_config', 'ERROR: (' + repr(e) + ')')


def read_module(module):
    try:
        xml_conf = load_config()
        xml_settings = xml_conf.getElementsByTagName('settings')
        for xml_setting in xml_settings:
            for xml_modul in xml_setting.getElementsByTagName(module):
                return xml_modul
    except Exception, e:
        dbg_log('oe::read_module', 'ERROR: (' + repr(e) + ')')


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
    except Exception, e:
        dbg_log('oe::read_node', 'ERROR: (' + repr(e) + ')')


def remove_node(node_name):
    try:
        xml_conf = load_config()
        xml_node = xml_conf.getElementsByTagName(node_name)
        for xml_main_node in xml_node:
            xml_main_node.parentNode.removeChild(xml_main_node)
        save_config(xml_conf)
    except Exception, e:
        dbg_log('oe::remove_node', 'ERROR: (' + repr(e) + ')')


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
    except Exception, e:
        dbg_log('oe::read_setting', 'ERROR: (' + repr(e) + ')')


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
    except Exception, e:
        dbg_log('oe::write_setting', 'ERROR: (' + repr(e) + ')')


def load_modules():

  # # load libreelec configuration modules

    try:
        global dictModules, __oe__, __cwd__, init_done
        for strModule in dictModules:
            dictModules[strModule] = None
        dict_names = {}
        dictModules = {}
        for file_name in sorted(os.listdir(__cwd__ + '/resources/lib/modules')):
            if not file_name.startswith('__') and (file_name.endswith('.py') or file_name.endswith('.pyo')):
                (name, ext) = file_name.split('.')
                dict_names[name] = None
        for module_name in dict_names:
            try:
                if not module_name in dictModules:
                    dictModules[module_name] = getattr(__import__(module_name), module_name)(__oe__)
                    if hasattr(defaults, module_name):
                        for key in getattr(defaults, module_name):
                            setattr(dictModules[module_name], key, getattr(defaults, module_name)[key])
            except Exception, e:
                dbg_log('oe::MAIN(loadingModules)(strModule)', 'ERROR: (' + repr(e) + ')')
    except Exception, e:
        dbg_log('oe::MAIN(loadingModules)', 'ERROR: (' + repr(e) + ')')


def timestamp():
    now = time.time()
    localtime = time.localtime(now)
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
    reboot_dlg.create('LibreELEC %s' % title, ' ', ' ', ' ')
    reboot_dlg.update(0)
    wait_time = seconds
    while seconds >= 0 and not reboot_dlg.iscanceled():
        progress = round(1.0 * seconds / wait_time * 100)
        reboot_dlg.update(int(progress), _(32329) % seconds)
        time.sleep(1)
        seconds = seconds - 1
    if not reboot_dlg.iscanceled():
        return 1
    else:
        return 0


def exit():
    global WinOeSelect, winOeMain, __addon__, __cwd__, __oe__, _, dbusSystemBus, dictModules
    dbusSystemBus.close()
    dbusSystemBus = None

    # del winOeMain

    del dbusSystemBus
    del dictModules
    del __addon__
    del __oe__
    del _


# fix for xml printout

def fixed_writexml(self, writer, indent='', addindent='', newl=''):
    writer.write(indent + '<' + self.tagName)
    attrs = self._get_attributes()
    a_names = attrs.keys()
    a_names.sort()
    for a_name in a_names:
        writer.write(' %s="' % a_name)
        minidom._write_data(writer, attrs[a_name].value)
        writer.write('"')
    if self.childNodes:
        if len(self.childNodes) == 1 and self.childNodes[0].nodeType == minidom.Node.TEXT_NODE:
            writer.write('>')
            self.childNodes[0].writexml(writer, '', '', '')
            writer.write('</%s>%s' % (self.tagName, newl))
            return
        writer.write('>%s' % newl)
        for node in self.childNodes:
            if node.nodeType is not minidom.Node.TEXT_NODE:
                node.writexml(writer, indent + addindent, addindent, newl)
        writer.write('%s</%s>%s' % (
            indent,
            self.tagName,
            newl,
            ))
    else:
        writer.write('/>%s' % newl)


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
    distribution = version = architecture = build = ''
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
        return (
            distribution,
            version,
            architecture,
            build,
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
DOWNLOAD_DIR = '/storage/downloads'
XBMC_USER_HOME = os.environ.get('XBMC_USER_HOME', '/storage/.kodi')
CONFIG_CACHE = os.environ.get('CONFIG_CACHE', '/storage/.cache')
USER_CONFIG = os.environ.get('USER_CONFIG', '/storage/.config')
TEMP = '%s/temp/' % XBMC_USER_HOME
winOeMain = oeWindows.mainWindow('mainWindow.xml', __cwd__, 'Default', oeMain=__oe__)
if os.path.exists('/etc/machine-id'):
    SYSTEMID = load_file('/etc/machine-id')
else:
    SYSTEMID = os.environ.get('SYSTEMID', '')

############################################################################################

try:
    configFile = '%s/userdata/addon_data/service.libreelec.settings/oe_settings.xml' % XBMC_USER_HOME
    if os.path.exists('%s/userdata/addon_data/service.openelec.settings' % XBMC_USER_HOME):
        os.rename(('%s/userdata/addon_data/service.openelec.settings' % XBMC_USER_HOME), ('%s/userdata/addon_data/service.libreelec.settings' % XBMC_USER_HOME))
    if not os.path.exists('%s/userdata/addon_data/service.libreelec.settings' % XBMC_USER_HOME):
        os.makedirs('%s/userdata/addon_data/service.libreelec.settings' % XBMC_USER_HOME)
    if not os.path.exists('%s/services' % CONFIG_CACHE):
        os.makedirs('%s/services' % CONFIG_CACHE)
except:
    pass
