# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcplugin, xbmcvfs
import xbmcaddon
import time
import datetime
from windows.base_window import FontUtils
from caches.base_cache import check_databases, clean_databases
from apis.trakt_api import trakt_sync_activities
from indexers import real_debrid, premiumize, alldebrid, furk, easynews
from modules.updater import update_check
from modules import kodi_utils, settings
from modules.utils import jsondate_to_datetime, datetime_workaround

disable_enable_addon, update_local_addons, get_infolabel, run_plugin = kodi_utils.disable_enable_addon, kodi_utils.update_local_addons, kodi_utils.get_infolabel, kodi_utils.run_plugin
ls, translate_path, custom_context_main_menu_prop, mdParse = kodi_utils.local_string, kodi_utils.translate_path, kodi_utils.custom_context_main_menu_prop, kodi_utils.mdParse
custom_context_prop, custom_info_prop, addon_object, user_settings = kodi_utils.custom_context_prop, kodi_utils.custom_info_prop, kodi_utils.addon_object, kodi_utils.user_settings
pause_services_prop, xbmc_monitor, xbmc_player, userdata_path = kodi_utils.pause_services_prop, kodi_utils.xbmc_monitor, kodi_utils.xbmc_player, kodi_utils.userdata_path
get_window_id, Thread, kodi_version, check_premium = kodi_utils.get_window_id, kodi_utils.Thread, kodi_utils.kodi_version, settings.check_premium_account_status
make_directories, path_exists, update_action, update_delay = kodi_utils.make_directories, kodi_utils.path_exists, settings.update_action, settings.update_delay
get_setting, set_setting, external, make_settings_props = kodi_utils.get_setting, kodi_utils.set_setting, kodi_utils.external, kodi_utils.make_settings_props
logger, run_addon, confirm_dialog, close_dialog = kodi_utils.logger, kodi_utils.run_addon, kodi_utils.confirm_dialog, kodi_utils.close_dialog
get_property, set_property, clear_property, get_visibility = kodi_utils.get_property, kodi_utils.set_property, kodi_utils.clear_property, kodi_utils.get_visibility
trakt_sync_interval, trakt_sync_refresh_widgets, auto_start_fen = settings.trakt_sync_interval, settings.trakt_sync_refresh_widgets, settings.auto_start_fen
kodi_refresh, list_dirs, delete_file = kodi_utils.kodi_refresh, kodi_utils.list_dirs, kodi_utils.delete_file
current_skin_prop, use_skin_fonts_prop, notification, ok_dialog = kodi_utils.current_skin_prop, kodi_utils.use_skin_fonts_prop, kodi_utils.notification, kodi_utils.ok_dialog
pause_settings_prop, enabled_debrids_check = kodi_utils.pause_settings_prop, settings.enabled_debrids_check
fen_str, window_top_str, listitem_property_str = ls(32036), 'Window.IsTopMost(%s)', 'ListItem.Property(%s)'
movieinformation_str, contextmenu_str = 'movieinformation', 'contextmenu'
media_windows = (10000, 10025, 11121)

class InitializeDatabases:
	def run(self):
		logger(fen_str, 'InitializeDatabases Service Starting')
		check_databases()
		return logger(fen_str, 'InitializeDatabases Service Finished')

class CheckSettings:
	def run(self):
		logger(fen_str, 'CheckSettingsFile Service Starting')
		if not path_exists(userdata_path): make_directories(userdata_path)
		addon_object.setSetting('dummy_setting', 'foo')
		return logger(fen_str, 'CheckSettingsFile Service Finished')

class DatabaseMaintenance:
	def run(self):
		logger(fen_str, 'Database Maintenance Service Starting')
		time = datetime.datetime.now()
		current_time = self._get_timestamp(time)
		due_clean = int(get_setting('fen.database.maintenance.due', '0'))
		if due_clean == 0:
			next_clean = str(int(self._get_timestamp(time + datetime.timedelta(days=3))))
			set_setting('database.maintenance.due', next_clean)
			return logger(fen_str, 'Database Maintenance Service First Run - Skipping')
		if current_time >= due_clean:
			clean_databases(current_time, database_check=False, silent=True)
			next_clean = str(int(self._get_timestamp(time + datetime.timedelta(days=3))))
			set_setting('database.maintenance.due', next_clean)
			return logger(fen_str, 'Database Maintenance Service Finished')
		else: return logger(fen_str, 'Database Maintenance Service Finished - Not Run')

	def _get_timestamp(self, date_time):
		return int(time.mktime(date_time.timetuple()))

class FirstRunActions:
	def run(self):
		logger(fen_str, 'FirstRunActions Service Starting')
		if kodi_version() < 20:
			ok_dialog(fen_str, 'Kodi 20 or above required[CR]Please update Kodi or uninstall Fen')
			return logger(fen_str, 'FirstRunActions Service Finished - Running on Incompatible Kodi Version')
		addon_version, settings_version =  self.remove_alpha(addon_object.getAddonInfo('version')), self.remove_alpha(addon_object.getSetting('version_number'))
		if addon_version != settings_version:
			logger(fen_str, 'FirstRunActions Running Update Actions....')
			addon_object.setSetting('version_number', addon_version)
			self.update_action(addon_version)
		if get_setting('first_use', 'false') == 'true':
			lines = ('By default, Fen has [B]Local Folders[/B], [B]Debrid Cloud[/B], [B]Furk[/B] and [B]Easynews[/B] scrapers.',
			'These scrapers are designed for use on media you have purchased and organized through these services.',
			'Fen is [B]unable[/B] to search online for sources outside of these services.',
			'If you wish to use an external scraper package within Fen, you must select a module at[CR][B]Fen Settings->Providers->Choose External Scrapers Module.[/B]',
			'The use of external scrapers is outside of the intended use of Fen, and will not be supported by Fen.')
			for count, line in enumerate(lines, 1):
				button_label = 'Finish' if count == 5 else 'Continue'
				heading = '%s - %s/5.' % (ls(32522), count)
				ok_dialog(heading, line, button_label)
			set_setting('first_use', 'false')
		return logger(fen_str, 'FirstRunActions Service Finished')

	def update_action(self, addon_version):
		''' Put code that needs to run once on update here'''
		return

	def remove_alpha(self, string):
		try: result = ''.join(c for c in string if (c.isdigit() or c =='.'))
		except: result = ''
		return result

class ReuseLanguageInvokerCheck:
	def run(self):
		logger(fen_str, 'ReuseLanguageInvokerCheck Service Starting')
		addon_xml = translate_path('special://home/addons/plugin.video.fen/addon.xml')
		current_addon_setting = get_setting('fen.reuse_language_invoker', None)
		if current_addon_setting is None: return logger(fen_str, 'ReuseLanguageInvokerCheck Service Error. No current setting detected. Finished')
		root = mdParse(addon_xml)
		invoker_instance = root.getElementsByTagName('reuselanguageinvoker')[0].firstChild
		if invoker_instance.data != current_addon_setting:
			invoker_instance.data = current_addon_setting
			new_xml = str(root.toxml()).replace('<?xml version="1.0" ?>', '')
			with open(addon_xml, 'w') as f: f.write(new_xml)
			if not get_setting('fen.auto_invoker_fix') == 'true' and not confirm_dialog(text='%s[CR]%s' % (ls(33021), ls(33020))):
				return logger(fen_str, 'ReuseLanguageInvokerCheck Service Finished')
			execute_builtin('ActivateWindow(Home)', True)
			update_local_addons()
			disable_enable_addon()
		return logger(fen_str, 'ReuseLanguageInvokerCheck Service Finished')

class TraktMonitor:
	def run(self):
		logger(fen_str, 'TraktMonitor Service Starting')
		monitor, player = xbmc_monitor(), xbmc_player()
		wait_for_abort, is_playing = monitor.waitForAbort, player.isPlayingVideo
		trakt_service_string = 'TraktMonitor Service Update %s - %s'
		update_string = 'Next Update in %s minutes...'
		wait_time = 30 * 60
		success_line_dict = {'success': 'Trakt Update Performed', 'no account': '(Unauthorized) Trakt Update Performed'}
		while not monitor.abortRequested():
			try:
				while is_playing() or get_property(pause_services_prop) == 'true': wait_for_abort(10)
				sync_interval, wait_time = trakt_sync_interval()
				next_update_string = update_string % sync_interval
				status = trakt_sync_activities()
				if status in ('success', 'no account'):
					logger(fen_str, trakt_service_string % ('Success', success_line_dict[status]))
					if trakt_sync_refresh_widgets():
						kodi_refresh()
						logger(fen_str, trakt_service_string % ('Widgets Refresh', 'Setting Activated. Widget Refresh Performed'))
					else: logger(fen_str, trakt_service_string % ('Widgets Refresh', 'Setting Disabled. Skipping Widget Refresh'))
				elif status == 'failed': logger(fen_str, trakt_service_string % ('Failed. Error from Trakt', next_update_string))
				else: logger(fen_str, trakt_service_string % ('Success. No Changes Needed', next_update_string))# 'not needed'
			except Exception as e: logger(fen_str, trakt_service_string % ('Failed', 'The following Error Occured: %s' % str(e)))
			wait_for_abort(wait_time)
		try: del monitor
		except: pass
		try: del player
		except: pass
		return logger(fen_str, 'TraktMonitor Service Finished')

class CustomActions:
	def run(self):
		logger(fen_str, 'CustomActions Service Starting')
		monitor, player = xbmc_monitor(), xbmc_player()
		self.wait_for_abort, abort_requested, is_playing = monitor.waitForAbort, monitor.abortRequested, player.isPlayingVideo
		while not abort_requested():
			context_visible, info_visible, run_custom = False, False, False
			while not any([context_visible, info_visible]) and not abort_requested():
				custom_context = get_property(custom_context_prop) == 'true'
				custom_main_context = get_property(custom_context_main_menu_prop) == 'true'
				custom_info = get_property(custom_info_prop) == 'true'
				if not any([custom_context, custom_main_context, custom_info]): self.wait_for_abort(5); continue
				if not get_window_id() in media_windows: self.wait_for_abort(2); continue
				if get_property(pause_services_prop) == 'true' or is_playing(): self.wait_for_abort(2); continue
				if not external() or get_infolabel(listitem_property_str % 'fen.external') == 'true':
					run_custom = True
					custom_context_params = get_infolabel(listitem_property_str % 'fen.options_params')
					custom_main_context_params = get_infolabel(listitem_property_str % 'fen.context_main_menu_params')
					custom_info_params = get_infolabel(listitem_property_str % 'fen.extras_params')
					self.wait_for_abort(0.25)
				else:
					run_custom = False
					self.wait_for_abort(1); continue
				context_visible, info_visible = get_visibility(window_top_str % contextmenu_str), get_visibility(window_top_str % movieinformation_str)
			try:
				if run_custom and any([custom_context_params, custom_main_context_params, custom_info_params]):
					if info_visible:
						if custom_info and custom_info_params: self.run_custom_action(custom_info_params, movieinformation_str)
					else:
						if all([custom_context, custom_context_params != '']) or all([custom_main_context, custom_main_context_params != '']):
							self.run_custom_action(custom_context_params or custom_main_context_params, contextmenu_str)
				else: self.wait_for_abort(1)
			except: self.wait_for_abort(2)
		try: del monitor
		except: pass
		try: del player
		except: pass
		return logger(fen_str, 'CustomActions Service Finished')

	def run_custom_action(self, action, window):
		close_dialog(window, True)
		run_plugin(action)

class CustomFonts:
	def run(self):
		logger(fen_str, 'CustomFonts Service Starting')
		monitor, player = xbmc_monitor(), xbmc_player()
		wait_for_abort, is_playing = monitor.waitForAbort, player.isPlayingVideo
		for item in (current_skin_prop, use_skin_fonts_prop): clear_property(item)
		font_utils = FontUtils()
		while not monitor.abortRequested():
			font_utils.execute_custom_fonts()
			if get_property(pause_services_prop) == 'true' or is_playing(): sleep = 20
			else: sleep = 10
			wait_for_abort(sleep)
		try: del monitor
		except: pass
		try: del player
		except: pass
		return logger(fen_str, 'CustomFonts Service Finished')

class ClearSubs:
	def run(self):
		logger(fen_str, 'Clear Subtitles Service Starting')
		sub_formats = ('.srt', '.ssa', '.smi', '.sub', '.idx', '.nfo')
		subtitle_path = 'special://temp/%s'
		files = list_dirs(translate_path('special://temp/'))[1]
		for i in files:
			if i.startswith('FENSubs_') or i.endswith(sub_formats): delete_file(translate_path(subtitle_path % i))
		return logger(fen_str, 'Clear Subtitles Service Finished')

class AutoRun:
	def run(self):
		logger(fen_str, 'AutoRun Service Starting')
		if auto_start_fen(): run_addon()
		return logger(fen_str, 'AutoRun Service Finished')

class PremiumExpiryCheck:
	def run(self):
		if not check_premium(): return
		logger(fen_str, 'Premium Expiry Check Service Starting')
		self.message, self.days_remaining = [], []
		try:
			self.run_check()
			if self.make_message(): ok_dialog('Fen - Premium Accounts Expiring...', '\n'.join(self.message))
			self.expired_premium = [i for i in self.days_remaining if i[1] == 0]
			if self.expired_premium and confirm_dialog(heading='Fen - Premium Accounts Expired', text='Disable Expired Accounts?', ok_label=32839, cancel_label=32840): self.revoke()
		except: pass
		logger(fen_str, 'Premium Expiry Check Service Finished')

	def run_check(self):
		premium_check_function_dict = {'Real-Debrid': real_debrid.active_days, 'Premiumize.me': premiumize.active_days, 'AllDebrid': alldebrid.active_days,
										'Furk': furk.active_days, 'Easynews': easynews.active_days}
		active_functions = [Thread(target=self.process, args=(premium_check_function_dict[i], i)) for i in self.active_accounts()]
		[i.start() for i in active_functions]
		[i.join() for i in active_functions]

	def active_accounts(self):
		active_accounts = [i[0] for i in [('Real-Debrid', 'rd'), ('Premiumize.me', 'pm'), ('AllDebrid', 'ad')] if enabled_debrids_check(i[1])]
		if settings.furk_active(): active_accounts.append('Furk')
		if settings.easynews_active(): active_accounts.append('Easynews')
		return active_accounts

	def make_message(self):
		if any(i in [i[1] for i in self.days_remaining] for i in (7, 5, 3, 1, 0)):
			self.message = ['[B]%s: EXPIRED[/B]' % i[0] if i[1] == 0 else '[B]%s:[/B] %s Days Remaining' % i for i in self.days_remaining]
		return self.message

	def process(self, function, name):
		expiry = function()
		if expiry <= 7: self.days_remaining.append((name, expiry))

	def revoke(self):
		premium_check_setting_dict = {'Real-Debrid': 'rd.enabled', 'Premiumize.me': 'pm.enabled', 'AllDebrid': 'ad.enabled',
										'Furk': 'provider.furk', 'Easynews': 'provider.easynews'}
		for item in self.expired_premium: set_setting(premium_check_setting_dict[item[0]], 'false')

class OnSettingsChangedActions:
	def run(self):
		if get_property(pause_settings_prop) != 'true': make_settings_props()

class UpdateCheck:
	def run(self):
		logger(fen_str, 'UpdateCheck Service Starting')
		monitor, player = xbmc_monitor(), xbmc_player()
		wait_for_abort, is_playing = monitor.waitForAbort, player.isPlayingVideo
		while not monitor.abortRequested():
			wait_for_abort(update_delay())
			while get_property(pause_services_prop) == 'true' or is_playing(): wait_for_abort(5)
			update_check(update_action())
			break
		try: del monitor
		except: pass
		try: del player
		except: pass
		return logger(fen_str, 'UpdateCheck Service Finished')

class OnNotificationActions:
	def run(self, sender, method, data):
		if sender == 'xbmc':
			if method in ('GUI.OnScreensaverActivated', 'System.OnSleep'):
				set_property(pause_services_prop, 'true')
				logger('OnNotificationActions', 'PAUSING Fen Services Due to Device Sleep')
			elif method in ('GUI.OnScreensaverDeactivated', 'System.OnWake'):
				clear_property(pause_services_prop)
				logger('OnNotificationActions', 'UNPAUSING Fen Services Due to Device Awake')
