"""
    tknorris shared module
    Copyright (C) 2016 tknorris

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import json
import xbmc
import xbmcaddon
from xbmc import LOGDEBUG, LOGERROR, LOGFATAL, LOGINFO, LOGNONE, LOGWARNING  # @UnusedImport

from metahandler.lib.modules import constants

addon_meta = xbmcaddon.Addon(constants.addon_id)

def execute_jsonrpc(command):
    if not isinstance(command, str):
        command = json.dumps(command)
    response = xbmc.executeJSONRPC(command)
    return json.loads(response)

def _is_debugging():
    command = {'jsonrpc': '2.0', 'id': 1, 'method': 'Settings.getSettings', 'params': {'filter': {'section': 'system', 'category': 'logging'}}}
    js_data = execute_jsonrpc(command)
    for item in js_data.get('result', {}).get('settings', {}):
        if item['id'] == 'debug.showloginfo':
            return item['value']
    
    return False

class Logger(object):
    __loggers = {}
    __name = addon_meta.getAddonInfo('name')
    __addon_debug = addon_meta.getSetting('addon_debug') == 'true'
    __debug_on = _is_debugging()
    __disabled = set()
    
    @staticmethod
    def get_logger(name=None):
        if name not in Logger.__loggers:
            Logger.__loggers[name] = Logger()
        
        return Logger.__loggers[name]
        
    def disable(self):
        if self not in Logger.__disabled:
            Logger.__disabled.add(self)
    
    def enable(self):
        if self in Logger.__disabled:
            Logger.__disabled.remove(self)
            
    def log(self, msg, level=LOGDEBUG):
        # if debug isn't on, skip disabled loggers unless addon_debug is on
        if not self.__debug_on:
            if self in self.__disabled:
                return
            elif level == LOGDEBUG:
                if self.__addon_debug:
                    level = LOGINFO
                else:
                    return
        
        try:
            if isinstance(msg, str):
                msg = '%s (ENCODED)' % (msg.encode('utf-8'))
    
            xbmc.log('%s: %s' % (self.__name, msg), level)
                
        except Exception as e:
            try: xbmc.log('Logging Failure: %s' % (e), level)
            except: pass  # just give up
    
    def log_debug(self, msg):
        self.log(msg, level=LOGDEBUG)
    
    def log_info(self, msg):
        self.log(msg, level=LOGINFO)
    
    def log_warning(self, msg):
        self.log(msg, level=LOGWARNING)
    
    def log_error(self, msg):
        self.log(msg, level=LOGERROR)