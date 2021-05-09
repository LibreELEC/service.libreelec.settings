# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2021-present Team LibreELEC (https://libreelec.tv)

import dbus_pulseaudio
import log
import modules
import oe
import xbmcgui
import dbussy

class pulseaudio(modules.Module):

    menu = {'7': {
        'name': 32500,
        'menuLoader': 'menu_connections',
        'listTyp': 'palist',
        'InfoText': 32501,
        }}
    ENABLED = False
    PULSEAUDIO_DAEMON = None

    @log.log_function()
    def __init__(self, oeMain):
        super().__init__()
        self.visible = False
        self.listItems = {}

    @log.log_function()
    def do_init(self):
        self.visible = True

    @log.log_function()
    def start_service(self):
        pass

    @log.log_function()
    def stop_service(self):
        pass

    @log.log_function()
    def exit(self):
        self.clear_list()
        self.visible = False

    # ###################################################################
    # # Pulseaudio Core
    # ###################################################################

    @log.log_function()
    def get_sinks(self):
        sinks = {}
        for sink in dbus_pulseaudio.core_get_property('Sinks'):
            sinks[sink] = {}
            try:
                sinks[sink]['Card'] = dbus_pulseaudio.sink_get_property(sink, 'Card')
            except dbussy.DBusError:
                pass
            sinks[sink]['Driver'] = dbus_pulseaudio.sink_get_property(sink, 'Driver')
            sinks[sink]['Name'] = dbus_pulseaudio.sink_get_property(sink, 'Name')
            sinks[sink]['PropertyList'] = dbus_pulseaudio.sink_get_property(sink, 'PropertyList')

        return sinks

    # ###################################################################
    # # Menu functions
    # ###################################################################

    @log.log_function()
    def set_fallback_sink(self, listItem=None):
        if listItem is None:
            listItem = oe.winOeMain.getControl(oe.listObject['palist']).getSelectedItem()
        if listItem is None:
            return

        sink = listItem.getProperty('entry')
        dbus_pulseaudio.core_set_fallback_sink(sink)

    @log.log_function()
    def change_profile(self, listItem=None):
        if listItem is None:
            listItem = oe.winOeMain.getControl(oe.listObject['palist']).getSelectedItem()
        if listItem is None:
            return

        card = listItem.getProperty('Card')
        profiles = dbus_pulseaudio.card_get_property(card, 'Profiles')
        activeProfile = dbus_pulseaudio.card_get_property(card, 'ActiveProfile')

        items = []

        # we only want to list the available profiles
        profiles = [profile for profile in profiles if dbus_pulseaudio.profile_get_property(profile, 'Available') == 1]
        items = [dbus_pulseaudio.profile_get_property(profile, 'Description') for profile in profiles]

        try:
            active = profiles.index(activeProfile)
        except ValueError:
            active = 0

        select_window = xbmcgui.Dialog()
        title = oe._(32502)
        result = select_window.select(title, items, preselect=active)
        if result >= 0:
            dbus_pulseaudio.card_set_active_profile(card, profiles[result])

    # ###################################################################
    # # Pulseaudio GUI
    # ###################################################################

    @log.log_function()
    def clear_list(self):
        remove = [entry for entry in self.listItems]
        for entry in remove:
            del self.listItems[entry]

    @log.log_function()
    def menu_connections(self, focusItem=None):
        if not hasattr(oe, 'winOeMain'):
            return 0
        if not oe.winOeMain.visible:
            return 0
        if not dbus_pulseaudio.system_has_pulseaudio():
            oe.winOeMain.getControl(1601).setLabel(oe._(32503))
            self.clear_list()
            oe.winOeMain.getControl(int(oe.listObject['palist'])).reset()
            oe.dbg_log('pulseaudio::menu_connections', 'exit_function (PA Disabled)', oe.LOGDEBUG)
            return
        oe.winOeMain.getControl(1601).setLabel(oe._(32504))
        dictProperties = {}

        # type 1=int, 2=string

        properties = [
            {
                'type': 2,
                'value': 'Driver',
            },
            {
                'type': 2,
                'value': 'Card',
            },
        ]

        rebuildList = 0
        self.dbusDevices = self.get_sinks()
        for dbusDevice in self.dbusDevices:
            rebuildList = 1
            oe.winOeMain.getControl(int(oe.listObject['palist'])).reset()
            self.clear_list()
            break

        fallbackSink = dbus_pulseaudio.core_get_property('FallbackSink')

        for dbusDevice in self.dbusDevices:
            dictProperties = {}
            sinkName = ''
            dictProperties['entry'] = dbusDevice
            dictProperties['modul'] = self.__class__.__name__
            dictProperties['action'] = 'open_context_menu'
            dictProperties['FallbackSink'] = '0'

            # find the card (if available) and active profile (if available)
            if 'Card' in self.dbusDevices[dbusDevice]:
                cardPath = self.dbusDevices[dbusDevice]['Card']
                cardProperties = dbus_pulseaudio.card_get_properties(cardPath)

                if 'ActiveProfile' in cardProperties:
                    activeProfile = cardProperties['ActiveProfile']
                    dictProperties['ActiveProfileName'] = dbus_pulseaudio.profile_get_property(activeProfile, 'Name')

            # check if the sink is the FallbackSink (for indication)
            if fallbackSink is not None and dbusDevice == fallbackSink:
                dictProperties['FallbackSink'] = '1'

            if 'PropertyList' in self.dbusDevices[dbusDevice]:
                if 'device.description' in self.dbusDevices[dbusDevice]['PropertyList']:
                    sinkName = bytearray(self.dbusDevices[dbusDevice]['PropertyList']['device.description']).decode().strip('\x00')

            # fallback to the ugly name
            if sinkName == '':
                sinkName = self.dbusDevices[dbusDevice]['Name']

            for prop in properties:
                name = prop['value']
                if name in self.dbusDevices[dbusDevice]:
                    value = self.dbusDevices[dbusDevice][name]
                    if prop['type'] == 1:
                        value = str(int(value))
                    if prop['type'] == 2:
                        value = str(value)
                    if prop['type'] == 3:
                        value = str(len(value))
                    if prop['type'] == 4:
                        value = str(int(value))
                    dictProperties[name] = value
            if rebuildList == 1:
                self.listItems[dbusDevice] = oe.winOeMain.addConfigItem(sinkName, dictProperties, oe.listObject['palist'])
            else:
                if self.listItems[dbusDevice] != None:
                    self.listItems[dbusDevice].setLabel(sinkName)
                    for dictProperty in dictProperties:
                        self.listItems[dbusDevice].setProperty(dictProperty, dictProperties[dictProperty])

    @log.log_function()
    def open_context_menu(self, listItem):
        values = {}
        if listItem is None:
            listItem = oe.winOeMain.getControl(oe.listObject['palist']).getSelectedItem()
        if listItem.getProperty('ActiveProfileName') != '':
            values[1] = {
                'text': oe._(32505),
                'action': 'change_profile',
                }
        if listItem.getProperty('FallbackSink') != '1':
            values[2] = {
                'text': oe._(32508),
                'action': 'set_fallback_sink',
                }
        items = []
        actions = []
        for key in list(values.keys()):
            items.append(values[key]['text'])
            actions.append(values[key]['action'])
        select_window = xbmcgui.Dialog()
        title = oe._(32012)
        result = select_window.select(title, items)
        if result >= 0:
            getattr(self, actions[result])(listItem)
