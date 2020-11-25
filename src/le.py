import os
import traceback
import xbmc

LOG_HEADER = '## LibreELEC Addon ##'


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
