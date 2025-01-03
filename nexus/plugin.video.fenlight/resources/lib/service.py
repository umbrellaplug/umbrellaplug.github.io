# -*- coding: utf-8 -*-
import xbmc, xbmcgui
import json
from threading import Thread

pause_services_prop = 'fenlight.pause_services'
firstrun_update_prop = 'fenlight.firstrun_update'
current_skin_prop = 'fenlight.current_skin'
trakt_service_string = 'TraktMonitor Service Update %s - %s'
trakt_success_line_dict = {'success': 'Trakt Update Performed', 'no account': '(Unauthorized) Trakt Update Performed'}
update_string = 'Next Update in %s minutes...'

def logger(heading, function):
	xbmc.log('###%s###: %s' % (heading, function), 1)

class SetAddonConstants:
	def run(self):
		logger('Fen Light', 'SetAddonConstants Service Starting')
		import xbmcgui, xbmcaddon, xbmcvfs
		addon_object = xbmcaddon.Addon('plugin.video.fenlight')
		self.window = xbmcgui.Window(10000)
		_info = addon_object.getAddonInfo
		addon_items = [('fenlight.addon_version', _info('version')),
					('fenlight.addon_path', _info('path')),
					('fenlight.addon_profile', xbmcvfs.translatePath(_info('profile'))),
					('fenlight.addon_icon', xbmcvfs.translatePath(_info('icon'))),
					('fenlight.addon_fanart', xbmcvfs.translatePath(_info('fanart')))]
		for item in addon_items: self.set_property(*item)
		return logger('Fen Light', 'SetAddonConstants Service Finished')

	def set_property(self, prop, value):
		self.window.setProperty(prop, value)

class DatabaseMaintenance:
	def run(self):
		logger('Fen Light', 'DatabaseMaintenance Service Starting')
		from caches.base_cache import make_databases
		make_databases()
		return logger('Fen Light', 'DatabaseMaintenance Service Finished')

class SyncSettings:
	def run(self):
		logger('Fen Light', 'SyncSettings Service Starting')
		from caches.settings_cache import sync_settings
		sync_settings()
		logger('Fen Light', 'SyncSettings Service Finished')

class CustomFonts:
	def run(self):
		logger('Fen Light', 'CustomFonts Service Starting')
		from windows.base_window import FontUtils
		monitor, player, window = xbmc.Monitor(), xbmc.Player(), xbmcgui.Window(10000)
		wait_for_abort, is_playing = monitor.waitForAbort, player.isPlayingVideo
		window.clearProperty(current_skin_prop)
		font_utils = FontUtils()
		while not monitor.abortRequested():
			font_utils.execute_custom_fonts()
			if window.getProperty(pause_services_prop) == 'true' or is_playing(): sleep = 20
			else: sleep = 10
			wait_for_abort(sleep)
		try: del monitor
		except: pass
		try: del player
		except: pass
		return logger('Fen Light', 'CustomFonts Service Finished')

class TraktMonitor:
	def run(self):
		logger('Fen Light', 'TraktMonitor Service Starting')
		from apis.trakt_api import trakt_sync_activities
		from caches.settings_cache import get_setting
		from modules.kodi_utils import run_plugin
		from modules.settings import trakt_sync_interval
		monitor, player, window = xbmc.Monitor(), xbmc.Player(), xbmcgui.Window(10000)
		wait_for_abort, is_playing = monitor.waitForAbort, player.isPlayingVideo
		while not monitor.abortRequested():
			while is_playing() or window.getProperty(pause_services_prop) == 'true': wait_for_abort(10)
			wait_time = 1800
			try:
				sync_interval, wait_time = trakt_sync_interval()
				next_update_string = update_string % sync_interval
				status = trakt_sync_activities()
				if status == 'failed': logger('Fen Light', trakt_service_string % ('Failed. Error from Trakt', next_update_string))
				else:
					if status in ('success', 'no account'): logger('Fen Light', trakt_service_string % ('Success. %s' % trakt_success_line_dict[status], next_update_string))
					else: logger('Fen Light', trakt_service_string % ('Success. No Changes Needed', next_update_string))# 'not needed'
					if status == 'success' and get_setting('fenlight.trakt.refresh_widgets', 'false') == 'true': run_plugin({'mode': 'kodi_refresh'})
			except Exception as e: logger('Fen Light', trakt_service_string % ('Failed', 'The following Error Occured: %s' % str(e)))
			wait_for_abort(wait_time)
		try: del monitor
		except: pass
		try: del player
		except: pass
		return logger('Fen Light', 'TraktMonitor Service Finished')

class UpdateCheck:
	def run(self):
		window = xbmcgui.Window(10000)
		if window.getProperty(firstrun_update_prop) == 'true': return
		logger('Fen Light', 'UpdateCheck Service Starting')
		from time import time
		from modules.updater import update_check
		from modules.settings import update_action, update_delay
		end_pause = time() + update_delay()
		monitor, player = xbmc.Monitor(), xbmc.Player()
		wait_for_abort, is_playing = monitor.waitForAbort, player.isPlayingVideo
		while not monitor.abortRequested():
			while time() < end_pause: wait_for_abort(1)
			while window.getProperty(pause_services_prop) == 'true' or is_playing(): wait_for_abort(1)
			update_check(update_action())
			break
		window.setProperty(firstrun_update_prop, 'true')
		try: del monitor
		except: pass
		try: del player
		except: pass
		return logger('Fen Light', 'UpdateCheck Service Finished')

class WidgetRefresher:
	def run(self):
		logger('Fen Light', 'WidgetRefresher Service Starting')
		from time import time
		from caches.settings_cache import get_setting
		from modules.kodi_utils import home, run_plugin
		monitor, player = xbmc.Monitor(), xbmc.Player()
		wait_for_abort, self.is_playing = monitor.waitForAbort, player.isPlayingVideo
		self.window = xbmcgui.Window(10000)
		self.get_setting = get_setting
		self.home = home
		self.window.setProperty('fenlight.refresh_widgets', 'true')
		self.set_next_refresh(time())
		wait_for_abort(20)
		while not monitor.abortRequested():
			try:
				wait_for_abort(10)
				self.window.clearProperty('fenlight.refresh_widgets')
				offset = int(self.get_setting('fenlight.widget_refresh_timer', '60'))
				if offset != self.offset:
					self.set_next_refresh(time())
					continue
				if self.condition_check(): continue
				if self.next_refresh < time():
					run_plugin({'mode': 'refresh_widgets', 'show_notification': self.get_setting('fenlight.widget_refresh_notification', 'false')}, block=True)
					logger('Fen Light', 'WidgetRefresher Service - Widgets Refreshed')
					self.set_next_refresh(time())
			except: pass
		try: del monitor
		except: pass
		try: del player
		except: pass
		return logger('Fen Light', 'WidgetRefresher Service Finished')

	def condition_check(self):
		if not self.home(): return True
		if self.next_refresh == None or self.is_playing() or self.window.getProperty(pause_services_prop) == 'true': return True
		if self.window.getProperty('fenlight.window_loaded') == 'true': return True 
		try:
			window_stack = json.loads(self.window.getProperty('fenlight.window_stack'))
			if window_stack or window_stack == []: return True
		except: pass
		return False

	def set_next_refresh(self, _time):
		self.offset = int(self.get_setting('fenlight.widget_refresh_timer', '60'))
		if self.offset: self.next_refresh = _time + (self.offset*60)
		else: self.next_refresh = None

class AutoStart:
	def run(self):
		logger('Fen Light', 'AutoStart Service Starting')
		from modules.settings import auto_start_fenlight
		if auto_start_fenlight():
			from modules.kodi_utils import run_addon
			run_addon()
		return logger('Fen Light', 'AutoStart Service Finished')

class FenLightMonitor(xbmc.Monitor):
	def __init__ (self):
		xbmc.Monitor.__init__(self)
		self.startServices()

	def startServices(self):
		SetAddonConstants().run()
		DatabaseMaintenance().run()
		SyncSettings().run()
		Thread(target=CustomFonts().run).start()
		Thread(target=TraktMonitor().run).start()
		Thread(target=UpdateCheck().run).start()
		Thread(target=WidgetRefresher().run).start()
		AutoStart().run()

	def onNotification(self, sender, method, data):
		if method in ('GUI.OnScreensaverActivated', 'System.OnSleep'):
			xbmcgui.Window(10000).setProperty(pause_services_prop, 'true')
			logger('OnNotificationActions', 'PAUSING Fen Light Services Due to Device Sleep')
		elif method in ('GUI.OnScreensaverDeactivated', 'System.OnWake'):
			xbmcgui.Window(10000).clearProperty(pause_services_prop)
			logger('OnNotificationActions', 'UNPAUSING Fen Light Services Due to Device Awake')

logger('Fen Light', 'Main Monitor Service Starting')
FenLightMonitor().waitForAbort()
logger('Fen Light', 'Main Monitor Service Finished')
