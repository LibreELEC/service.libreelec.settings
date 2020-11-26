# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
# Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)
# Copyright (C) 2019-present Team LibreELEC (https://libreelec.tv)

import xbmc
import xbmcgui
import xbmcaddon
import os
import time
import re
from xml.dom import minidom
from threading import Thread

xbmcDialog = xbmcgui.Dialog()

lang_str = ""
lang_new = ""
strModule = ""
prevModule = ""

class mainWindow(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        self.visible = False
        self.lastMenu = -1
        self.lastEntry = -1
        self.guiMenList = 1000
        self.guiList = 1100
        self.guiNetList = 1200
        self.guiBtList = 1300
        self.guiOther = 1900
        self.guiLists = [
            1000,
            1100,
            1200,
            1300,
            ]
        self.buttons = {
            1: {
                'id': 1500,
                'modul': '',
                'action': '',
                },
            2: {
                'id': 1501,
                'modul': '',
                'action': '',
                },
            }

        self.isChild = False
        self.oe = kwargs['oeMain']
        self.lastGuiList = -1
        self.lastListType = -1
        if 'isChild' in kwargs:
            self.isChild = True
        pass

    def onInit(self):
        self.visible = True
        try:
            if self.isChild:
                self.setFocusId(self.guiMenList)
                self.onFocus(self.guiMenList)
                return
            self.oe.set_busy(1)
            self.setProperty('arch', self.oe.ARCHITECTURE)
            self.setProperty('distri', self.oe.DISTRIBUTION)
            self.setProperty('version', self.oe.VERSION)
            self.setProperty('build', self.oe.BUILD)
            self.oe.winOeMain = self
            for strModule in sorted(self.oe.dictModules, key=lambda x: list(self.oe.dictModules[x].menu.keys())):
                module = self.oe.dictModules[strModule]
                self.oe.dbg_log('init module', strModule, self.oe.LOGDEBUG)
                if module.ENABLED:
                    if hasattr(module, 'do_init'):
                        Thread(target=module.do_init(), args=()).start()
                    for men in module.menu:
                        if 'listTyp' in module.menu[men] and 'menuLoader' in module.menu[men]:
                            dictProperties = {
                                'modul': strModule,
                                'listTyp': self.oe.listObject[module.menu[men]['listTyp']],
                                'menuLoader': module.menu[men]['menuLoader'],
                                }
                            if 'InfoText' in module.menu[men]:
                                dictProperties['InfoText'] = self.oe._(module.menu[men]['InfoText'])
                            self.addMenuItem(module.menu[men]['name'], dictProperties)
            self.setFocusId(self.guiMenList)
            self.onFocus(self.guiMenList)
            self.oe.set_busy(0)
        except Exception as e:
            self.oe.set_busy(0)
            self.oe.dbg_log('oeWindows.mainWindow::onInit', 'ERROR: (' + repr(e) + ')')

    def addMenuItem(self, strName, dictProperties):
        try:
            lstItem = xbmcgui.ListItem(label=self.oe._(strName))
            for strProp in dictProperties:
                lstItem.setProperty(strProp, str(dictProperties[strProp]))
            self.getControl(self.guiMenList).addItem(lstItem)
        except Exception as e:
            self.oe.dbg_log('oeWindows.mainWindow::addMenuItem(' + str(strName) + ')', 'ERROR: (' + repr(e) + ')')

    def addConfigItem(self, strName, dictProperties, strType):
        try:
            lstItem = xbmcgui.ListItem(label=strName)
            for strProp in dictProperties:
                lstItem.setProperty(strProp, str(dictProperties[strProp]))
            self.getControl(int(strType)).addItem(lstItem)
            return lstItem
        except Exception as e:
            self.oe.dbg_log('oeWindows.mainWindow::addConfigItem(' + strName + ')', 'ERROR: (' + repr(e) + ')')

    def build_menu(self, struct, fltr=[], optional='0'):
        try:
            self.getControl(1100).reset()
            m_menu = []
            for category in sorted(struct, key=lambda x: struct[x]['order']):
                if not 'hidden' in struct[category]:
                    if fltr == []:
                        m_entry = {}
                        m_entry['name'] = self.oe._(struct[category]['name'])
                        m_entry['properties'] = {'typ': 'separator'}
                        m_entry['list'] = 1100
                        m_menu.append(m_entry)
                    else:
                        if category not in fltr:
                            continue
                    for entry in sorted(struct[category]['settings'], key=lambda x: struct[category]['settings'][x]['order']):
                        setting = struct[category]['settings'][entry]
                        if not 'hidden' in setting:
                            dictProperties = {
                                'value': setting['value'],
                                'typ': setting['type'],
                                'entry': entry,
                                'category': category,
                                'action': setting['action'],
                                }
                            if 'InfoText' in setting:
                                dictProperties['InfoText'] = self.oe._(setting['InfoText'])
                            if 'validate' in setting:
                                dictProperties['validate'] = setting['validate']
                            if 'values' in setting:
                                dictProperties['values'] = '|'.join(setting['values'])
                            if isinstance(setting['name'], str):
                                name = setting['name']
                            else:
                                name = self.oe._(setting['name'])
                                dictProperties['menuname'] = self.oe._(setting['name'])
                            m_entry = {}
                            if not 'parent' in setting:
                                m_entry['name'] = name
                                m_entry['properties'] = dictProperties
                                m_entry['list'] = 1100
                                m_menu.append(m_entry)
                            else:
                                if struct[category]['settings'][setting['parent']['entry']]['value'] in setting['parent']['value']:
                                    if not 'optional' in setting or 'optional' in setting and optional != '0':
                                        m_entry['name'] = name
                                        m_entry['properties'] = dictProperties
                                        m_entry['list'] = 1100
                                        m_menu.append(m_entry)
            for m_entry in m_menu:
                self.addConfigItem(m_entry['name'], m_entry['properties'], m_entry['list'])
        except Exception as e:
            self.oe.dbg_log('oeWindows.mainWindow::build_menu', 'ERROR: (' + repr(e) + ')')

    def showButton(self, number, name, module, action, onup=None, onleft=None):
        try:
            self.oe.dbg_log('oeWindows::showButton', 'enter_function', self.oe.LOGDEBUG)
            button = self.getControl(self.buttons[number]['id'])
            self.buttons[number]['modul'] = module
            self.buttons[number]['action'] = action
            button.setLabel(self.oe._(name))
            if onup != None:
                button.controlUp(self.getControl(onup))
            if onleft != None:
                button.controlLeft(self.getControl(onleft))
            button.setVisible(True)
            self.oe.dbg_log('oeWindows::showButton', 'exit_function', self.oe.LOGDEBUG)
        except Exception as e:
            self.oe.dbg_log('oeWindows.mainWindow::showButton(' + str(number) + ', ' + str(action) + ')', 'ERROR: (' + repr(e) + ')')

    def onAction(self, action):
        try:
            focusId = self.getFocusId()
            actionId = int(action.getId())
            if focusId == 2222:
                if actionId == 61453:
                    return
            if actionId in self.oe.CANCEL:
                self.visible = False
                self.close()
            if focusId == self.guiList:
                curPos = self.getControl(focusId).getSelectedPosition()
                listSize = self.getControl(focusId).size()
                newPos = curPos
                nextItem = self.getControl(focusId).getListItem(newPos)
                if (curPos != self.lastGuiList or nextItem.getProperty('typ') == 'separator') and actionId in [
                    2,
                    3,
                    4,
                    ]:
                    while nextItem.getProperty('typ') == 'separator':
                        if actionId == 2:
                            newPos = newPos + 1
                        if actionId == 3:
                            newPos = newPos - 1
                        if actionId == 4:
                            newPos = newPos + 1
                        if newPos <= 0:
                            newPos = listSize - 1
                        if newPos >= listSize:
                            newPos = 0
                        nextItem = self.getControl(focusId).getListItem(newPos)
                    self.lastGuiList = newPos
                    self.getControl(focusId).selectItem(newPos)
                    self.setProperty('InfoText', nextItem.getProperty('InfoText'))
            if focusId == self.guiMenList:
                self.setFocusId(focusId)
        except Exception as e:
            self.oe.dbg_log('oeWindows.mainWindow::onAction(' + str(action) + ')', 'ERROR: (' + repr(e) + ')')
            if actionId in self.oe.CANCEL:
                self.close()

    def onClick(self, controlID):
        self.oe.dbg_log('oeWindows::onClick', 'enter_function', self.oe.LOGDEBUG)
        try:
            for btn in self.buttons:
                if controlID == self.buttons[btn]['id']:
                    modul = self.buttons[btn]['modul']
                    action = self.buttons[btn]['action']
                    if hasattr(self.oe.dictModules[modul], action):
                        if getattr(self.oe.dictModules[modul], action)() == 'close':
                            self.close()
                        return
            if controlID in self.guiLists:
                selectedPosition = self.getControl(controlID).getSelectedPosition()
                selectedMenuItem = self.getControl(self.guiMenList).getSelectedItem()
                selectedItem = self.getControl(controlID).getSelectedItem()
                strTyp = selectedItem.getProperty('typ')
                strValue = selectedItem.getProperty('value')
                if strTyp == 'multivalue':
                    items1 = []
                    items2 = []
                    for item in selectedItem.getProperty('values').split('|'):
                        if item != ':':
                            boo = item.split(':')
                            if len(boo) > 1:
                                i1 = boo[0]
                                i2 = boo[1]
                            else:
                                i1 = item
                                i2 = item
                        else:
                            i1 = ''
                            i2 = ''
                        if i2 == strValue:
                            items1.insert(0, i1)
                            items2.insert(0, i2)
                        else:
                            # move current on top of the list
                            items1.append(i1)
                            items2.append(i2)
                    select_window = xbmcgui.Dialog()
                    title = selectedItem.getProperty('menuname')
                    result = select_window.select(title, items1)
                    if result >= 0:
                        selectedItem.setProperty('value', items2[result])
                elif strTyp == 'text':
                    xbmcKeyboard = xbmc.Keyboard(strValue)
                    result_is_valid = False
                    while not result_is_valid:
                        xbmcKeyboard.doModal()
                        if xbmcKeyboard.isConfirmed():
                            result_is_valid = True
                            validate_string = selectedItem.getProperty('validate')
                            if validate_string != '':
                                if not re.search(validate_string, xbmcKeyboard.getText()):
                                    result_is_valid = False
                        else:
                            result_is_valid = True
                    if xbmcKeyboard.isConfirmed():
                        selectedItem.setProperty('value', xbmcKeyboard.getText())
                elif strTyp == 'file':
                    xbmcDialog = xbmcgui.Dialog()
                    returnValue = xbmcDialog.browse(1, 'LibreELEC.tv', 'files', '', False, False, '/')
                    if returnValue != '' and returnValue != '/':
                        selectedItem.setProperty('value', str(returnValue))
                elif strTyp == 'folder':
                    xbmcDialog = xbmcgui.Dialog()
                    returnValue = xbmcDialog.browse(0, 'LibreELEC.tv', 'files', '', False, False, '/storage')
                    if returnValue != '' and returnValue != '/':
                        selectedItem.setProperty('value', str(returnValue))
                elif strTyp == 'ip':
                    if strValue == '':
                        strValue = '0.0.0.0'
                    xbmcDialog = xbmcgui.Dialog()
                    returnValue = xbmcDialog.numeric(3, 'LibreELEC.tv', strValue)
                    if returnValue != '':
                        if returnValue == '0.0.0.0':
                            selectedItem.setProperty('value', '')
                        else:
                            selectedItem.setProperty('value', returnValue)
                elif strTyp == 'num':
                    if strValue == 'None' or strValue == '':
                        strValue = '0'
                    xbmcDialog = xbmcgui.Dialog()
                    returnValue = xbmcDialog.numeric(0, 'LibreELEC.tv', strValue)
                    if returnValue != '':
                        selectedItem.setProperty('value', returnValue)
                elif strTyp == 'bool':
                    strValue = strValue.lower()
                    if strValue == '0':
                        selectedItem.setProperty('value', '1')
                    elif strValue == '1':
                        selectedItem.setProperty('value', '0')
                    elif strValue == 'true':
                        selectedItem.setProperty('value', 'false')
                    elif strValue == 'false':
                        selectedItem.setProperty('value', 'true')
                    else:
                        selectedItem.setProperty('value', '1')
                if selectedItem.getProperty('action') != '':
                    if hasattr(self.oe.dictModules[selectedMenuItem.getProperty('modul')], selectedItem.getProperty('action')):
                        getattr(self.oe.dictModules[selectedMenuItem.getProperty('modul')], selectedItem.getProperty('action'
                                ))(listItem=selectedItem)
                        self.emptyButtonLabels()
                self.lastMenu = -1
                self.onFocus(self.guiMenList)
                self.setFocusId(controlID)
                self.getControl(controlID).selectItem(selectedPosition)
            self.oe.dbg_log('oeWindows::onClick', 'exit_function', self.oe.LOGDEBUG)
        except Exception as e:
            self.oe.dbg_log('oeWindows.mainWindow::onClick(' + str(controlID) + ')', 'ERROR: (' + repr(e) + ')')

    def onUnload(self):
        pass

    def onFocus(self, controlID):
        try:
            if controlID in self.guiLists:
                currentEntry = self.getControl(controlID).getSelectedPosition()
                selectedEntry = self.getControl(controlID).getSelectedItem()
                if controlID == self.guiList:
                    self.setProperty('InfoText', selectedEntry.getProperty('InfoText'))
                if currentEntry != self.lastGuiList:
                    self.lastGuiList = currentEntry
                    if selectedEntry is not None:
                        strHoover = selectedEntry.getProperty('hooverValidate')
                        if strHoover != '':
                            if hasattr(self.oe.dictModules[selectedEntry.getProperty('modul')], strHoover):
                                self.emptyButtonLabels()
                                getattr(self.oe.dictModules[selectedEntry.getProperty('modul')], strHoover)(selectedEntry)
            if controlID == self.guiMenList:
                lastMenu = self.getControl(controlID).getSelectedPosition()
                selectedMenuItem = self.getControl(controlID).getSelectedItem()
                self.setProperty('InfoText', selectedMenuItem.getProperty('InfoText'))
                if lastMenu != self.lastMenu:
                    if self.lastListType == int(selectedMenuItem.getProperty('listTyp')):
                        self.getControl(int(selectedMenuItem.getProperty('listTyp'))).setAnimations([('conditional',
                                'effect=fade start=100 end=0 time=100 condition=True')])
                    self.getControl(1100).setAnimations([('conditional', 'effect=fade start=0 end=0 time=1 condition=True')])
                    self.getControl(1200).setAnimations([('conditional', 'effect=fade start=0 end=0 time=1 condition=True')])
                    self.getControl(1300).setAnimations([('conditional', 'effect=fade start=0 end=0 time=1 condition=True')])
                    self.getControl(1900).setAnimations([('conditional', 'effect=fade start=0 end=0 time=1 condition=True')])
                    self.lastModul = selectedMenuItem.getProperty('Modul')
                    self.lastMenu = lastMenu
                    for btn in self.buttons:
                        self.getControl(self.buttons[btn]['id']).setVisible(False)
                    strMenuLoader = selectedMenuItem.getProperty('menuLoader')
                    objList = self.getControl(int(selectedMenuItem.getProperty('listTyp')))
                    self.getControl(controlID).controlRight(objList)
                    if strMenuLoader != '':
                        if hasattr(self.oe.dictModules[selectedMenuItem.getProperty('modul')], strMenuLoader):
                            getattr(self.oe.dictModules[selectedMenuItem.getProperty('modul')], strMenuLoader)(selectedMenuItem)
                    self.getControl(int(selectedMenuItem.getProperty('listTyp'))).setAnimations([('conditional',
                            'effect=fade start=0 end=100 time=100 condition=true')])
        except Exception as e:
            self.oe.dbg_log('oeWindows.mainWindow::onFocus(' + repr(controlID) + ')', 'ERROR: (' + repr(e) + ')')

    def emptyButtonLabels(self):
        for btn in self.buttons:
            self.getControl(self.buttons[btn]['id']).setVisible(False)


class pinkeyWindow(xbmcgui.WindowXMLDialog):

    device = ''

    def set_title(self, text):
        self.getControl(1700).setLabel(text)

    def set_label1(self, text):
        self.getControl(1701).setLabel(str(text))

    def set_label2(self, text):
        self.getControl(1702).setLabel(str(text))

    def set_label3(self, text):
        self.getControl(1703).setLabel(str(text))

    def append_label3(self, text):
        label = self.getControl(1703).getLabel()
        self.getControl(1703).setLabel(label + str(text))

    def get_label3_len(self):
        return len(self.getControl(1703).getLabel())


class wizard(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        self.visible = False
        self.lastMenu = -1
        self.guiMenList = 1000
        self.guiNetList = 1200
        self.wizTextbox = 1400
        self.wizTitle = 1399
        self.wizBtnTitle = 1403
        self.wizLstTitle = 1404
        self.wizWinTitle = 32300
        self.oe = kwargs['oeMain']
        self.guisettings = '%s/userdata/guisettings.xml' % self.oe.XBMC_USER_HOME
        self.buttons = {
            1: {
                'id': 1500,
                'modul': '',
                'action': '',
                },
            2: {
                'id': 1501,
                'modul': '',
                'action': '',
                },
            3: {
                'id': 1401,
                'modul': '',
                'action': '',
                },
            4: {
                'id': 1402,
                'modul': '',
                'action': '',
                },
            }

        self.radiobuttons = {
            1: {
                'id': 1406,
                'modul': '',
                'action': '',
                },
            2: {
                'id': 1407,
                'modul': '',
                'action': '',
                },
            }

        self.actions = {}
        self.wizards = []
        self.last_wizard = None

    def onInit(self):
        self.visible = True
        try:
            self.setProperty('arch', self.oe.ARCHITECTURE)
            self.setProperty('distri', self.oe.DISTRIBUTION)
            self.setProperty('version', self.oe.VERSION)
            self.setProperty('build', self.oe.BUILD)
            self.oe.dictModules['system'].do_init()
            self.getControl(self.wizWinTitle).setLabel(self.oe._(32300))
            self.getControl(self.buttons[3]['id']).setVisible(False)
            self.getControl(self.buttons[4]['id']).setVisible(False)
            self.getControl(self.radiobuttons[1]['id']).setVisible(False)
            self.getControl(self.radiobuttons[2]['id']).setVisible(False)
            self.getControl(self.buttons[2]['id']).setVisible(False)
            if self.oe.BOOT_STATUS == "SAFE":
              self.set_wizard_title("[COLOR red][B]%s[/B][/COLOR]" % self.oe._(32393))
              self.set_wizard_text(self.oe._(32394))
            else:
              self.set_wizard_title(self.oe._(32301))
              self.set_wizard_text(self.oe._(32302))
              self.oe.winOeMain.set_wizard_button_title(self.oe._(32310))
              cur_lang = xbmc.getLanguage()
              self.oe.winOeMain.set_wizard_button_1(cur_lang, self, 'wizard_set_language')
            self.showButton(1, 32303)
            self.setFocusId(self.buttons[1]['id'])
        except Exception as e:
            self.oe.dbg_log('oeWindows.wizard::onInit()', 'ERROR: (' + repr(e) + ')')

    def wizard_set_language(self):
        global lang_str
        global lang_new
        try:
            self.oe.dbg_log('oeWindows::wizard_set_language', 'enter_function', self.oe.LOGDEBUG)
            langCodes = {"Bulgarian":"resource.language.bg_bg","Czech":"resource.language.cs_cz","German":"resource.language.de_de","English":"resource.language.en_gb","Spanish":"resource.language.es_es","Basque":"resource.language.eu_es","Finnish":"resource.language.fi_fi","French":"resource.language.fr_fr","Hebrew":"resource.language.he_il","Hungarian":"resource.language.hu_hu","Italian":"resource.language.it_it","Lithuanian":"resource.language.lt_lt","Latvian":"resource.language.lv_lv","Norwegian":"resource.language.nb_no","Dutch":"resource.language.nl_nl","Polish":"resource.language.pl_pl","Portuguese (Brazil)":"resource.language.pt_br","Portuguese":"resource.language.pt_pt","Romanian":"resource.language.ro_ro","Russian":"resource.language.ru_ru","Slovak":"resource.language.sk_sk","Swedish":"resource.language.sv_se","Turkish":"resource.language.tr_tr","Ukrainian":"resource.language.uk_ua"}
            languagesList = sorted(list(langCodes.keys()))
            cur_lang = xbmc.getLanguage()
            for index, lang in enumerate(languagesList):
                if cur_lang in lang:
                    langIndex = index
                    break
                else:
                    pass
            selLanguage = xbmcDialog.select(self.oe._(32310), languagesList, preselect=langIndex)
            if selLanguage >= 0:
                langKey = languagesList[selLanguage]
                lang_new = langCodes[langKey]
                if lang_new == "resource.language.en_gb":
                    self.oe.write_setting("system", "language", "")
                else:
                    self.oe.write_setting("system", "language", str(lang_new))
                lang_str = 'SetGUILanguage(' + str(lang_new) + ')'
                self.getControl(self.wizWinTitle).setLabel(self.oe._(32300))
                self.set_wizard_title(self.oe._(32301))
                self.set_wizard_text(self.oe._(32302))
                self.oe.winOeMain.set_wizard_button_title(self.oe._(32310))
                self.oe.winOeMain.set_wizard_button_1(langKey, self, 'wizard_set_language')
                self.showButton(1, 32303)
                self.setFocusId(self.buttons[1]['id'])
            self.oe.dbg_log('oeWindows::wizard_set_language', 'exit_function', self.oe.LOGDEBUG)
        except Exception as e:
            self.oe.dbg_log('oeWindows::wizard_set_language', 'ERROR: (' + repr(e) + ')')

    def set_wizard_text(self, text):
        try:
            self.getControl(self.wizTextbox).setText(text)
        except Exception as e:
            self.oe.dbg_log('oeWindows.wizard::set_wizard_text()', 'ERROR: (' + repr(e) + ')')

    def set_wizard_title(self, title):
        try:
            self.getControl(self.wizTitle).setLabel(title)
        except Exception as e:
            self.oe.dbg_log('oeWindows.wizard::set_wizard_title()', 'ERROR: (' + repr(e) + ')')

    def set_wizard_button_title(self, title):
        try:
            self.getControl(self.wizBtnTitle).setLabel(title)
        except Exception as e:
            self.oe.dbg_log('oeWindows.wizard::set_wizard_button_title()', 'ERROR: (' + repr(e) + ')')

    def set_wizard_list_title(self, title):
        try:
            self.getControl(self.wizLstTitle).setLabel(title)
        except Exception as e:
            self.oe.dbg_log('oeWindows.wizard::set_wizard_list_title()', 'ERROR: (' + repr(e) + ')')

    def set_wizard_button_1(self, label, modul, action):
        try:
            self.buttons[3]['modul'] = modul
            self.buttons[3]['action'] = action
            self.getControl(self.buttons[3]['id']).setLabel(label)
            self.getControl(self.buttons[3]['id']).setVisible(True)
            self.getControl(self.buttons[3]['id']).controlRight(self.getControl(self.buttons[1]['id']))
            self.getControl(self.buttons[3]['id']).controlDown(self.getControl(self.buttons[1]['id']))
            self.getControl(self.buttons[1]['id']).controlUp(self.getControl(self.buttons[3]['id']))
            if self.buttons[2]['id']:
                self.getControl(self.buttons[1]['id']).controlLeft(self.getControl(self.buttons[2]['id']))
            else:
                self.getControl(self.buttons[1]['id']).controlLeft(self.getControl(self.buttons[3]['id']))
            self.getControl(self.buttons[2]['id']).controlUp(self.getControl(self.buttons[3]['id']))
            self.getControl(self.buttons[2]['id']).controlRight(self.getControl(self.buttons[1]['id']))
        except Exception as e:
            self.oe.dbg_log('oeWindows.wizard::set_wizard_button_1()', 'ERROR: (' + repr(e) + ')')

    def set_wizard_button_2(self, label, modul, action):
        try:
            self.buttons[4]['modul'] = modul
            self.buttons[4]['action'] = action
            self.getControl(self.buttons[4]['id']).setLabel(label)
            self.getControl(self.buttons[4]['id']).setVisible(True)
            self.getControl(self.buttons[4]['id']).controlLeft(self.getControl(self.buttons[3]['id']))
            self.getControl(self.buttons[4]['id']).controlDown(self.getControl(self.buttons[1]['id']))
            self.getControl(self.buttons[4]['id']).controlRight(self.getControl(self.buttons[1]['id']))
            self.getControl(self.buttons[1]['id']).controlUp(self.getControl(self.buttons[4]['id']))
            self.getControl(self.buttons[1]['id']).controlLeft(self.getControl(self.buttons[4]['id']))
            self.getControl(self.buttons[2]['id']).controlUp(self.getControl(self.buttons[4]['id']))
            self.getControl(self.buttons[2]['id']).controlRight(self.getControl(self.buttons[1]['id']))
            self.getControl(self.buttons[3]['id']).controlRight(self.getControl(self.buttons[4]['id']))
        except Exception as e:
            self.oe.dbg_log('oeWindows.wizard::set_wizard_button_2()', 'ERROR: (' + repr(e) + ')')

    def set_wizard_radiobutton_1(self, label, modul, action, selected=False):
        try:
            self.radiobuttons[1]['modul'] = modul
            self.radiobuttons[1]['action'] = action
            self.getControl(self.radiobuttons[1]['id']).setLabel(label)
            self.getControl(self.radiobuttons[1]['id']).setVisible(True)
            self.getControl(self.radiobuttons[1]['id']).controlRight(self.getControl(self.buttons[1]['id']))
            self.getControl(self.radiobuttons[1]['id']).controlDown(self.getControl(self.buttons[1]['id']))
            self.getControl(self.buttons[1]['id']).controlUp(self.getControl(self.buttons[3]['id']))
            self.getControl(self.buttons[1]['id']).controlLeft(self.getControl(self.buttons[2]['id']))
            self.getControl(self.buttons[2]['id']).controlUp(self.getControl(self.radiobuttons[1]['id']))
            self.getControl(self.buttons[2]['id']).controlRight(self.getControl(self.buttons[1]['id']))
            self.getControl(self.radiobuttons[1]['id']).setSelected(selected)
        except Exception as e:
            self.oe.dbg_log('oeWindows.wizard::set_wizard_button_1()', 'ERROR: (' + repr(e) + ')')

    def set_wizard_radiobutton_2(self, label, modul, action, selected=False):
        try:
            self.radiobuttons[2]['modul'] = modul
            self.radiobuttons[2]['action'] = action
            self.getControl(self.radiobuttons[2]['id']).setLabel(label)
            self.getControl(self.radiobuttons[2]['id']).setVisible(True)
            self.getControl(self.radiobuttons[2]['id']).controlLeft(self.getControl(self.radiobuttons[1]['id']))
            self.getControl(self.radiobuttons[2]['id']).controlDown(self.getControl(self.buttons[1]['id']))
            self.getControl(self.radiobuttons[2]['id']).controlRight(self.getControl(self.buttons[1]['id']))
            self.getControl(self.buttons[1]['id']).controlUp(self.getControl(self.radiobuttons[2]['id']))
            self.getControl(self.buttons[1]['id']).controlLeft(self.getControl(self.buttons[2]['id']))
            self.getControl(self.buttons[2]['id']).controlUp(self.getControl(self.radiobuttons[1]['id']))
            self.getControl(self.buttons[2]['id']).controlRight(self.getControl(self.buttons[1]['id']))
            self.getControl(self.radiobuttons[1]['id']).controlRight(self.getControl(self.radiobuttons[2]['id']))
            self.getControl(self.radiobuttons[2]['id']).setSelected(selected)
        except Exception as e:
            self.oe.dbg_log('oeWindows.wizard::set_wizard_button_2()', 'ERROR: (' + repr(e) + ')')

    def onAction(self, action):
        pass

    def onClick(self, controlID):
        global strModule
        global prevModule
        try:
            self.oe.dbg_log('wizard::onClick(' + str(controlID) + ')', 'enter_function', self.oe.LOGDEBUG)
            for btn in self.buttons:
                if controlID == self.buttons[btn]['id'] and self.buttons[btn]['id'] > 2:
                    if hasattr(self.buttons[btn]['modul'], self.buttons[btn]['action']):
                        getattr(self.buttons[btn]['modul'], self.buttons[btn]['action'])()
            for btn in self.radiobuttons:
                if controlID == self.radiobuttons[btn]['id'] and self.radiobuttons[btn]['id'] > 1:
                    if hasattr(self.radiobuttons[btn]['modul'], self.radiobuttons[btn]['action']):
                        getattr(self.radiobuttons[btn]['modul'], self.radiobuttons[btn]['action'])()
            if controlID == self.guiNetList:
                selectedItem = self.getControl(controlID).getSelectedItem()
                if selectedItem.getProperty('action') != '':
                    if hasattr(self.oe.dictModules[self.last_wizard], selectedItem.getProperty('action')):
                        getattr(self.oe.dictModules[self.last_wizard], selectedItem.getProperty('action'))(selectedItem)
                        return
            if controlID == 1501:
                self.wizards.remove(strModule)
                self.oe.remove_node(strModule)
                if strModule == "system":
                    self.onInit()
                else:
                    self.wizards.remove(prevModule)
                    self.oe.remove_node(prevModule)
                    self.onClick(1500)
                self.oe.dbg_log('wizard::onClick(' + str(controlID) + ')', 'exit_function', self.oe.LOGDEBUG)

            if controlID == 1500:
                self.getControl(1390).setLabel('1')
                self.oe.xbmcm.waitForAbort(0.5)
                self.is_last_wizard = True
                self.getControl(1391).setLabel('')
                self.getControl(self.buttons[3]['id']).setVisible(False)
                self.getControl(self.buttons[4]['id']).setVisible(False)
                self.getControl(self.radiobuttons[1]['id']).setVisible(False)
                self.getControl(self.radiobuttons[2]['id']).setVisible(False)
                self.showButton(2, 32307)
                self.set_wizard_title('')
                self.set_wizard_text('')
                self.set_wizard_list_title('')
                self.set_wizard_button_title('')

                for module in sorted(self.oe.dictModules, key=lambda x: list(self.oe.dictModules[x].menu.keys())):
                    strModule = module
                    if hasattr(self.oe.dictModules[strModule], 'do_wizard') and self.oe.dictModules[strModule].ENABLED:
                        if strModule == self.last_wizard:
                            if hasattr(self.oe.dictModules[strModule], 'exit'):
                                self.oe.dictModules[strModule].exit()
                                if hasattr(self.oe.dictModules[strModule], 'is_wizard'):
                                    del self.oe.dictModules[strModule].is_wizard
                        setting = self.oe.read_setting(strModule, 'wizard_completed')
                        if self.wizards != []:
                            prevModule = self.wizards[-1]
                        if self.oe.read_setting(strModule, 'wizard_completed') == None and strModule not in self.wizards:
                            self.last_wizard = strModule
                            if hasattr(self.oe.dictModules[strModule], 'do_init'):
                                self.oe.dictModules[strModule].do_init()
                            self.getControl(1390).setLabel('')
                            self.oe.dictModules[strModule].do_wizard()
                            self.wizards.append(strModule)
                            self.oe.write_setting(strModule, 'wizard_completed', 'True')
                            self.is_last_wizard = False
                            break
                if self.is_last_wizard == True:
                    xbmc.executebuiltin('UpdateAddonRepos')
                    langAddon = "InstallAddon(" + lang_new + ")"
                    xbmc.executebuiltin(langAddon)
                    self.oe.xbmcm.waitForAbort(0.5)
                    xbmc.executebuiltin('SendClick(10100,11)')
                    self.oe.write_setting('libreelec', 'wizard_completed', 'True')
                    self.visible = False
                    self.close()
                    xbmc.executebuiltin(lang_str)
            self.oe.dbg_log('wizard::onClick(' + str(controlID) + ')', 'exit_function', self.oe.LOGDEBUG)
        except Exception as e:
            self.oe.dbg_log('oeWindows.wizard::onClick()', 'ERROR: (' + repr(e) + ')')

    def onFocus(self, controlID):
        pass

    def showButton(self, number, name):
        try:
            button = self.getControl(self.buttons[number]['id'])
            button.setLabel(self.oe._(name))
            button.setVisible(True)
        except Exception as e:
            self.oe.dbg_log('oeWindows.wizard::showButton(' + str(number) + ')', 'ERROR: (' + repr(e) + ')')

    def addConfigItem(self, strName, dictProperties, strType):
        try:
            lstItem = xbmcgui.ListItem(label=strName)
            for strProp in dictProperties:
                lstItem.setProperty(strProp, str(dictProperties[strProp]))
            self.getControl(int(strType)).addItem(lstItem)
            return lstItem
        except Exception as e:
            self.oe.dbg_log('oeWindows.wizard::addConfigItem(' + strName + ')', 'ERROR: (' + repr(e) + ')')
