import os
import traceback
import xbmc
import xbmcaddon
import xbmcgui

LOG_HEADER = '## LibreELEC Addon ##'
SOCKET = '/var/run/service.libreelec.settings.sock'

ADDON = xbmcaddon.Addon()
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_STRING = ADDON.getLocalizedString


def log_function(function):
    def wrapper(*args, **kwargs):
        header = f'{LOG_HEADER} {function.__qualname__}'
        try:
            xbmc.log(f'{header} enter_function', xbmc.LOGDEBUG)
            return function(*args, **kwargs)
            xbmc.log(f'{header} exit_function', xbmc.LOGDEBUG)
        except Exception as e:
            xbmc.log(f'{header} ERROR: {repr(e)}', xbmc.LOGFATAL)
            xbmc.log(traceback.format_exc(), xbmc.LOGFATAL)
    return wrapper


@log_function
def notification(heading, message, icon=ADDON_ICON):
    xbmcgui.Dialog().notification(heading, message, icon)
