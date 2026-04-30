# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from resources.lib.modules import control, log_utils
from sys import version_info, platform as sys_platform
from threading import Thread
import time
from datetime import timedelta
window = control.homeWindow
pythonVersion = '{}.{}.{}'.format(version_info[0], version_info[1], version_info[2])
plugin = 'plugin://plugin.video.umbrella/'
LOGINFO = log_utils.LOGINFO
LOGDEBUG = log_utils.LOGDEBUG

properties = [
	'context.umbrella.settings',
	'context.umbrella.addtoLibrary',
	'context.umbrella.addtoFavourite',
	'context.umbrella.artworkCustomize',
	'context.umbrella.playTrailer',
	'context.umbrella.playTrailerSelect',
	'context.umbrella.traktManager',
	'context.umbrella.mdblistManager',
	'context.umbrella.simklManager',
	'context.umbrella.tmdbListManager',
	'context.umbrella.tmdbWatchlist',
	'context.umbrella.clearProviders',
	'context.umbrella.clearBookmark',
	'context.umbrella.rescrape',
	'context.umbrella.playFromHere',
	'context.umbrella.autoPlay',
	'context.umbrella.sourceSelect',
	'context.umbrella.findSimilar',
	'context.umbrella.browseSeries',
	'context.umbrella.browseEpisodes',
	'context.umbrella.libMdblistManager',
	'context.umbrella.addLibtoFavourite']

class CheckSettingsFile:
	def run(self):
		try:
			control.log('[ plugin.video.umbrella ]  CheckSettingsFile Service Starting...', LOGINFO)
			window.clearProperty('umbrella_settings')
			profile_dir = control.dataPath
			if not control.existsPath(profile_dir):
				success = control.makeDirs(profile_dir)
				if success: control.log('%s : created successfully' % profile_dir, LOGINFO)
			else: control.log('%s : already exists' % profile_dir, LOGINFO)
			settings_xml = control.joinPath(profile_dir, 'settings.xml')
			if not control.existsPath(settings_xml):
				control.setSetting('trakt.message2', '')
				control.log('%s : created successfully' % settings_xml, LOGINFO)
			else: control.log('%s : already exists' % settings_xml, LOGINFO)
			return control.log('[ plugin.video.umbrella ]  Finished CheckSettingsFile Service', LOGINFO)
		except Exception:
			log_utils.error()

class SettingsMonitor(control.monitor_class):
	def __init__ (self):
		control.monitor_class.__init__(self)
		control.refresh_playAction()
		control.refresh_libPath()
		window.setProperty('umbrella.debug.reversed', str(control.setting('debug.reversed')))
		window.setProperty('umbrella.updateSettings', 'true')
		for id in properties:
			if control.setting(id) == 'true':
				window.setProperty(id, 'true')
				#xbmc.log('[ plugin.video.umbrella.context ]  menu item enabled: {0}'.format(id), LOGINFO)
		control.log('[ plugin.video.umbrella ]  Settings Monitor Service Starting...', LOGINFO)

	def onSettingsChanged(self):
		if window.getProperty('umbrella.updateSettings') != 'true':
			return control.log('[ plugin.video.umbrella ]  Settings Monitor is off.', LOGINFO)
		window.setProperty('umbrella.updateSettings','false')

		try:
			window.clearProperty('umbrella_settings') # Kodi callback when the addon settings are changed
		except Exception:
			control.log('[ plugin.video.umbrella ]  Exception clearing settings property...', LOGDEBUG)

		try:
			control.refresh_playAction()
		except Exception:
			control.log('[ plugin.video.umbrella ]  Exception making refreshing playAction...', LOGDEBUG)
		try:
			control.refresh_libPath()
		except Exception:
			control.log('[ plugin.video.umbrella ]  Exception refreshing libpath...', LOGDEBUG)
		#try:
			#control.checkPlayNextEpisodes()
		#except:
			#control.log('[ plugin.video.umbrella ]  Exception checking playnext episodes...', LOGDEBUG)
		try:
			control.refresh_debugReversed()
		except Exception:
			control.log('[ plugin.video.umbrella ]  Exception checking debug reversed', LOGDEBUG)
		try:
			control.setContextColors()
		except Exception:
			control.log('[ plugin.video.umbrella ]  Exception setting context colors...', LOGDEBUG)
		try:
			control.checkModules()
		except Exception:
			control.log('[ plugin.video.umbrella ]  Exception checking modules...', LOGDEBUG)
		try:
			control.sleep(50)
			control.make_settings_dict()
			window.setProperty('umbrella.updateSettings','true')
		except Exception:
			control.log('[ plugin.video.umbrella ]  Exception making settings dict...', LOGDEBUG)
		try:
			for id in properties:
				if control.setting(id) == 'true':
					window.setProperty(id, 'true')
				else:
					window.clearProperty(id)
					#xbmc.log('[ plugin.video.umbrella.context ]  menu item disabled: {0}'.format(id), LOGINFO)
		except Exception:
			log_utils.error()

class SyncMyAccounts:
	def run(self):
		control.log('[ plugin.video.umbrella ]  Sync Accounts with Scraper Starting...', LOGINFO)
		control.syncAccounts()
		return control.log('[ plugin.video.umbrella ]  Finished Sync with Scraper', LOGINFO)

class SyncMovieLibrary:
	def run(self):
		if control.setting('library.cachesimilar') == 'true':
			control.log('[ plugin.video.umbrella ]  Sync Library Movies with Umbrella...', LOGINFO)
			from resources.lib.modules import library
			library.lib_tools().cacheLibraryforSimilar() 
			return control.log('[ plugin.video.umbrella ]  Sync Library Movies with Umbrella Done', LOGINFO)
		else:
			return

class checkAutoStart:
	def run(self):
		control.log('[ plugin.video.umbrella ]  Checking for AutoStart....', LOGINFO)
		if control.setting('umbrella.autostart') == 'true': 
			control.execute('RunAddon(plugin.video.umbrella)')
		return control.log('[ plugin.video.umbrella ]  Finished AutoStart Check', LOGINFO)


class ReuseLanguageInvokerCheck:
	def run(self):
		control.log('[ plugin.video.umbrella ]  ReuseLanguageInvokerCheck Service Starting...', LOGINFO)
		try:
			import xml.etree.ElementTree as ET
			from resources.lib.modules.language_invoker import gen_file_hash
			addon_xml = control.joinPath(control.addonPath('plugin.video.umbrella'), 'addon.xml')
			tree = ET.parse(addon_xml)
			root = tree.getroot()
			current_addon_setting = control.addon('plugin.video.umbrella').getSetting('reuse.languageinvoker')
			try: current_xml_setting = [str(i.text) for i in root.iter('reuselanguageinvoker')][0]
			except Exception: return control.log('[ plugin.video.umbrella ]  ReuseLanguageInvokerCheck failed to get settings.xml value', LOGINFO)
			if current_addon_setting == '':
				current_addon_setting = 'true'
				control.setSetting('reuse.languageinvoker', current_addon_setting)
			if current_xml_setting == current_addon_setting:
				return control.log('[ plugin.video.umbrella ]  ReuseLanguageInvokerCheck Service Finished', LOGINFO)
			control.okDialog(message='%s\n%s' % (control.lang(33023), control.lang(33020)))
			for item in root.iter('reuselanguageinvoker'):
				item.text = current_addon_setting
				hash_start = gen_file_hash(addon_xml)
				tree.write(addon_xml)
				hash_end = gen_file_hash(addon_xml)
				control.log('[ plugin.video.umbrella ]  ReuseLanguageInvokerCheck Service Finished', LOGINFO)
				if hash_start != hash_end:
					current_profile = control.infoLabel('system.profilename')
					control.execute('LoadProfile(%s)' % current_profile)
				else: control.okDialog(title='default', message=33022)
			return
		except Exception:
			log_utils.error()

class AddonCheckUpdate:
	def run(self):
		control.log('[ plugin.video.umbrella ]  Addon checking available updates', LOGINFO)
		try:
			import re
			import requests
			local_version = control.getUmbrellaVersion() # 5 char max so pre-releases do try to compare more chars than github version 6.5.941
			if len(local_version) > 6: #test version
				repo_xml = requests.get('https://raw.githubusercontent.com/umbrellakodi/umbrellakodi.github.io/master/matrix/plugin.video.umbrella/addon.xml')
			else:
				repo_xml = requests.get('https://raw.githubusercontent.com/umbrellaplug/umbrellaplug.github.io/master/matrix/plugin.video.umbrella/addon.xml')
			if not repo_xml.status_code == 200:
				return control.log('[ plugin.video.umbrella ]  Could not connect to remote repo XML: status code = %s' % repo_xml.status_code, LOGINFO)
			repo_version = re.findall(r'<addon id=\"plugin.video.umbrella\".+version=\"(\d*.\d*.\d*)\"', repo_xml.text)[0]
			def check_version_numbers(current, new): # Compares version numbers and return True if github version is newer
				current = current.split('.')
				new = new.split('.')
				step = 0
				for i in current:
					if int(new[step]) > int(i): return True
					if int(i) > int(new[step]): return False
					if int(i) == int(new[step]):
						step += 1
						continue
				return False
			if check_version_numbers(local_version, repo_version):
				while control.condVisibility('Library.IsScanningVideo'):
					control.sleep(10000)
				control.log('[ plugin.video.umbrella ]  A newer version is available. Installed Version: v%s, Repo Version: v%s' % (local_version, repo_version), LOGINFO)
				control.notification(message=control.lang(35523) % repo_version)
			return control.log('[ plugin.video.umbrella ]  Addon update check complete', LOGINFO)
		except Exception:
			log_utils.error()

class VersionIsUpdateCheck:
	def run(self):
		try:
			from resources.lib.database import cache
			isUpdate = False
			oldVersion, isUpdate = cache.update_cache_version()

			if isUpdate:
				window.setProperty('umbrella.updated', 'true')
				curVersion = control.getUmbrellaVersion()
				clearDB_version = '6.7.60' # set to desired version to force any db clearing needed
				do_cacheClear = (int(oldVersion.replace('.', '')) < int(clearDB_version.replace('.', '')) <= int(curVersion.replace('.', '')))
				if do_cacheClear:
					clr_fanarttv = False
					cache.clrCache_version_update(clr_providers=False, clr_metacache=False, clr_cache=False, clr_search=False, clr_bookmarks=False)
					from resources.lib.database import traktsync
					clr_traktSync = {'bookmarks': False, 'hiddenProgress': True, 'liked_lists': False, 'movies_collection': False, 'movies_watchlist': False, 'popular_lists': False,
											'public_lists': False, 'shows_collection': False, 'shows_watchlist': False, 'trending_lists': False, 'user_lists': False, 'watched': False}
					cleared = traktsync.delete_tables(clr_traktSync)
					from resources.lib.database import simklsync
					clr_simklsync = {'movies_plantowatch': False, 'shows_plantowatch': False, 'shows_watching': False, 'shows_hold': False, 'movies_dropped': False, 'shows_dropped': False, 'watched': False, 'movies_completed': False, 'shows_completed': False}
					cleared2 = simklsync.delete_tables(clr_simklsync)
					if cleared:
						control.notification(message='Forced traktsync clear for version update complete.')
						control.log('[ plugin.video.umbrella ]  Forced traktsync clear for version update complete.', LOGINFO)
					if cleared2:
						control.notification(message='Forced simklsync clear for version update complete.')
						control.log('[ plugin.video.umbrella ]  Forced simklsync clear for version update complete.', LOGINFO)
					if clr_fanarttv:
						from resources.lib.database import fanarttv_cache
						cleared = fanarttv_cache.cache_clear()
						control.notification(message='Forced fanarttv.db clear for version update complete.')
						control.log('[ plugin.video.umbrella ]  Forced fanarttv.db clear for version update complete.', LOGINFO)
				control.setSetting('trakt.message2', '') # force a settings write for any added settings that may have been added in new version
				control.log('[ plugin.video.umbrella ]  Forced new User Data settings.xml saved', LOGINFO)
				control.log('[ plugin.video.umbrella ]  Plugin updated to v%s' % curVersion, LOGINFO)
		except Exception:
			log_utils.error()

class SyncTraktCollection:
	def run(self):
		control.log('[ plugin.video.umbrella ]  Trakt Collection Sync Import Disabled...', LOGINFO)
		#control.log('[ plugin.video.umbrella ]  Trakt Collection Sync Starting...', LOGINFO)
		#control.execute('RunPlugin(%s?action=library_tvshowsToLibrarySilent&url=traktcollection)' % plugin)
		#control.log('[ plugin.video.umbrella ]  Trakt Collection Sync TV Shows Complete', LOGINFO)
		#control.execute('RunPlugin(%s?action=library_moviesToLibrarySilent&url=traktcollection)' % plugin)
		#control.log('[ plugin.video.umbrella ]  Trakt Collection Sync Movies Complete', LOGINFO)
		#control.log('[ plugin.video.umbrella ]  Trakt Collection Sync Complete', LOGINFO)

class LibraryService:
	def run(self):
		try:
			library_hours = float(control.setting('library.import.hours'))
		except Exception:
			library_hours = int(6)
		control.log('[ plugin.video.umbrella ]  Library Update Service Starting (Runs Every %s Hours)...' % library_hours,  LOGINFO)
		from resources.lib.modules import library
		library.lib_tools().service() # method contains control.monitor().waitForAbort() while loop every 6hrs

class SyncServices:
	def run(self):
		service_syncInterval = control.setting('background.service.syncInterval') or '15'
		control.log('[ plugin.video.umbrella ]  Account Sync Service Starting (sync check every %s minutes)...' % service_syncInterval, LOGINFO)
		#from resources.lib.modules import trakt
		#trakt.trakt_service_sync() # method contains "control.monitor().waitForAbort()" while loop every "service_syncInterval" minutes
		from resources.lib.modules import tools
		tools.services_syncs()

try:
	testUmbrella = False
	if control.setting('indicators') == '0':
		control.setSetting('indicators', 'Local') #fix for making this setting a string.
	_alt_map = {'0': 'Local', '1': 'Trakt', '2': 'Simkl', '3': 'MDBList'}
	_alt_val = control.setting('indicators.alt')
	_ind_val = control.setting('indicators')
	if _alt_val in _alt_map and _ind_val != _alt_map[_alt_val]:
		control.setSetting('indicators', _alt_map[_alt_val]) # sync display label with backing integer on upgrade
	_scrobble_map = {'0': 'Local', '1': 'Trakt', '2': 'Simkl', '3': 'MDBList'}
	_scrobble_val = control.setting('scrobble.source')
	_scrobble_disp = control.setting('scrobble')
	if _scrobble_val in _scrobble_map and _scrobble_disp != _scrobble_map[_scrobble_val]:
		control.setSetting('scrobble', _scrobble_map[_scrobble_val]) # sync display label with backing integer on upgrade
	kodiVersion = control.getKodiVersion(full=True)
	addonVersion = control.addon('plugin.video.umbrella').getAddonInfo('version')
	if len(str(control.getUmbrellaVersion())) > 6:
		repoVersion = control.addon('repository.umbrellakodi').getAddonInfo('version')
		repoName = 'repository.umbrellakodi'
		testUmbrella = True
	else:
		try:
			repoVersion = control.addon('repository.umbrella').getAddonInfo('version')
			repoName = 'repository.umbrella'
		except Exception:
			repoVersion = 'unknown'
			repoName = 'Unknown Repo'

	log_utils.log('########   CURRENT Umbrella VERSIONS REPORT   ########', level=LOGINFO)
	if testUmbrella == True:
		log_utils.log('########   TEST Umbrella Version   ########', level=LOGINFO)
	log_utils.log('##   Platform: %s' % str(sys_platform), level=LOGINFO)
	log_utils.log('##   Kodi Version: %s' % str(kodiVersion), level=LOGINFO)
	log_utils.log('##   python Version: %s' % pythonVersion, level=LOGINFO)
	log_utils.log('##   plugin.video.umbrella Version: %s' % str(addonVersion), level=LOGINFO)
	log_utils.log('##   %s Version: %s' % (str(repoName), str(repoVersion)), level=LOGINFO)
	log_utils.log('######   UMBRELLA SERVICE ENTERING KEEP ALIVE   #####', level=LOGINFO)
except Exception:
	log_utils.log('## ERROR GETTING Umbrella VERSION - Missing Repo or failed Install ', level=LOGINFO)

try:
	_ind_map = {'0': 'Local Only', '1': 'Trakt', '2': 'Simkl', '3': 'MDBList'}
	_scr_map = {'0': 'Off', '1': 'Trakt', '2': 'Simkl', '3': 'MDBList'}
	_ind = control.setting('indicators.alt')
	_scr = control.setting('scrobble.source')
	_trakt_authed = bool(control.setting('trakt.user.token') and control.setting('trakt.refreshtoken') and control.setting('trakt.user.name'))
	_simkl_authed = bool(control.setting('simkltoken'))
	_mdb_authed = bool(control.setting('mdblist.api'))
	_trakt_user = control.setting('trakt.user.name') or 'N/A'
	_trakt_custom_id = bool(control.setting('trakt.clientid'))
	log_utils.log('########   UMBRELLA SERVICE CONFIGURATION   ########', level=LOGINFO)
	log_utils.log('##   [Service Selection]', level=LOGINFO)
	log_utils.log('##   Primary Indicators/Watch History: %s' % _ind_map.get(_ind, _ind), level=LOGINFO)
	log_utils.log('##   Scrobble/Resume Source: %s' % _scr_map.get(_scr, _scr), level=LOGINFO)
	log_utils.log('##   Mark Watched Threshold: %s%%' % control.setting('markwatched.percent'), level=LOGINFO)
	log_utils.log('##   [Secondary Mark-Watched]', level=LOGINFO)
	log_utils.log('##   Trakt Mark-Watched: %s' % control.setting('trakt.markwatched'), level=LOGINFO)
	log_utils.log('##   Simkl Mark-Watched: %s' % control.setting('simkl.markwatched'), level=LOGINFO)
	log_utils.log('##   MDBList Mark-Watched: %s' % control.setting('mdblist.markwatched'), level=LOGINFO)
	log_utils.log('##   [Credentials]', level=LOGINFO)
	log_utils.log('##   Trakt Authenticated: %s%s' % (_trakt_authed, ' (user: %s)' % _trakt_user if _trakt_authed else ''), level=LOGINFO)
	log_utils.log('##   Trakt Custom Client ID: %s' % _trakt_custom_id, level=LOGINFO)
	log_utils.log('##   Simkl Authenticated: %s' % _simkl_authed, level=LOGINFO)
	log_utils.log('##   MDBList Authenticated: %s' % _mdb_authed, level=LOGINFO)
	log_utils.log('##   [Sync Intervals]', level=LOGINFO)
	log_utils.log('##   Service Loop Interval: %s min' % control.setting('background.service.syncInterval'), level=LOGINFO)
	log_utils.log('##   Simkl Sync Interval: %s min' % control.setting('simkl.service.syncInterval'), level=LOGINFO)
	log_utils.log('##   MDBList Sync Interval: %s min' % control.setting('mdblist.service.syncInterval'), level=LOGINFO)
	log_utils.log('##   [Notifications]', level=LOGINFO)
	log_utils.log('##   Scrobble Notify: %s' % control.setting('scrobble.notify'), level=LOGINFO)
	log_utils.log('##   Trakt Notifications: %s' % control.setting('trakt.general.notifications'), level=LOGINFO)
	log_utils.log('##   Simkl Notifications: %s' % control.setting('simkl.general.notifications'), level=LOGINFO)
	log_utils.log('##   MDBList Notifications: %s' % control.setting('mdblist.general.notifications'), level=LOGINFO)
	log_utils.log('####################################################', level=LOGINFO)
except Exception:
	log_utils.log('## ERROR logging service configuration', level=LOGINFO)

def getTraktCredentialsInfo():
	username = control.setting('trakt.user.name').strip()
	token = control.setting('trakt.user.token')
	refresh = control.setting('trakt.refreshtoken')
	if (username == '' or token == '' or refresh == ''): return False
	return True

class PremAccntNotification:
	def run(self):
		from datetime import datetime
		from resources.lib.debrid import alldebrid
		from resources.lib.debrid import premiumize
		from resources.lib.debrid import realdebrid
		control.log('[ plugin.video.umbrella ] Debrid Account Expiry Notification Service Starting...', LOGINFO)
		self.duration = [(15, 10), (11, 7), (8, 4), (5, 2), (3, 0)]
		if control.setting('alldebridusername') != '' and control.setting('alldebridexpirynotice') == 'true':
			try:
				account_info = alldebrid.AllDebrid().account_info()['user']
			except Exception:
				account_info = None
				from resources.lib.modules import log_utils
				log_utils.error()
			if account_info:
				if not account_info['isSubscribed']:
					# log_utils.log('AD account_info = %s' % account_info, log_utils.LOGINFO)
					try:
						expires = datetime.fromtimestamp(account_info['premiumUntil'])
					except Exception:
						expires = datetime.today()-timedelta(days=1)
						control.notification(message='AllDebrid Account has no expiration. Invalid or free account.', icon=control.joinPath(control.artPath(), 'alldebrid.png'))
					days_remaining = (expires - datetime.today()).days # int
					if days_remaining >= 0:
						if self.withinRangeCheck('alldebrid', days_remaining):
							control.notification(message='AllDebrid Account expires in %s days' % days_remaining, icon=control.joinPath(control.artPath(), 'alldebrid.png'))

		if control.setting('premiumizeusername') != '' and control.setting('premiumizeexpirynotice') == 'true':
			account_info = premiumize.Premiumize().account_info()
			if account_info:
				# log_utils.log('PM account_info = %s' % account_info, log_utils.LOGINFO)
				try: 
					expires = datetime.fromtimestamp(account_info['premium_until'])
				except Exception:
					expires = datetime.today()-timedelta(days=1)
					control.notification(message='Premiumize.me Account has no expiration. Invalid or free account.', icon=control.joinPath(control.artPath(), 'premiumize.png'))
				days_remaining = (expires - datetime.today()).days # int
				if days_remaining >= 0:
					if self.withinRangeCheck('premiumize', days_remaining):
						control.notification(message='Premiumize.me Account expires in %s days' % days_remaining, icon=control.joinPath(control.artPath(), 'premiumize.png'))

		if control.setting('realdebridusername') != '' and control.setting('realdebridexpirynotice') == 'true':
			account_info = realdebrid.RealDebrid().account_info()
			if account_info:
				# log_utils.log('RD account_info = %s' % account_info, log_utils.LOGINFO)
				FormatDateTime = "%Y-%m-%dT%H:%M:%S.%fZ"
				try: expires = datetime.strptime(account_info['expiration'], FormatDateTime)
				except Exception: 
					try: expires = datetime(*(time.strptime(account_info['expiration'], FormatDateTime)[0:6]))
					except Exception: 
						expires = datetime.today()-timedelta(days=1)
						control.notification(message='Real-Debrid Account has no expiration. Invalid or free account.', icon=control.joinPath(control.artPath(), 'realdebrid.png'))
				days_remaining = (expires - datetime.today()).days # int
				if days_remaining >= 0:
					if self.withinRangeCheck('realdebrid', days_remaining):
						control.notification(message='Real-Debrid Account expires in %s days' % days_remaining, icon=control.joinPath(control.artPath(), 'realdebrid.png'))

	def withinRangeCheck(self, debrid_provider, days_remaining):
		if days_remaining < 15:
			try: current_notification_range = int(control.setting('%s.notification.range' % debrid_provider))
			except Exception: current_notification_range = 5
			for index, day_range in enumerate(self.duration):
				if day_range[0] > days_remaining > day_range[1] and current_notification_range != index:
					control.setSetting('%s.notification.range' % debrid_provider, str(index))
					return True
			return False
		else:
			control.setSetting('%s.notification.range' % debrid_provider, '')
			return False

def main():
	while not control.monitor.abortRequested():
		control.log('[ plugin.video.umbrella ]  Service Started', LOGINFO)
		schedTrakt = None
		libraryService = None
		CheckSettingsFile().run()
		SyncMyAccounts().run()
		PremAccntNotification().run()
		ReuseLanguageInvokerCheck().run()
		#SyncMovieLibrary().run()
		#control.checkPlayNextEpisodes()
		if control.setting('library.service.update') == 'true':
			libraryService = Thread(target=LibraryService().run)
			libraryService.start()
		if control.setting('general.checkAddonUpdates') == 'true':
			AddonCheckUpdate().run()
		VersionIsUpdateCheck().run()
		checkAutoStart().run()

		syncServices = Thread(target=SyncServices().run) # run service in case user auth's trakt later, sync will loop and do nothing without valid auth'd account
		syncServices.start()

		# if getTraktCredentialsInfo():
		# 	if control.setting('autoTraktOnStart') == 'true':
		# 		SyncTraktCollection().run()
		# 	if int(control.setting('schedTraktTime')) > 0:
		# 		import threading
		# 		log_utils.log('#################### STARTING TRAKT SCHEDULING ################', level=LOGINFO)
		# 		log_utils.log('#################### SCHEDULED TIME FRAME '+ control.setting('schedTraktTime')  + ' HOURS ###############', level=LOGINFO)
		# 		timeout = 3600 * int(control.setting('schedTraktTime'))
		# 		schedTrakt = threading.Timer(timeout, SyncTraktCollection().run) # this only runs once at the designated interval time to wait...not repeating
		# 		schedTrakt.start()
		break
	SettingsMonitor().waitForAbort()
	# start monitoring settings changes events
	control.log('[ plugin.video.umbrella ]  Settings Monitor Service Stopping...', LOGINFO)
	del syncServices # prob does not kill a running thread
	control.log('[ plugin.video.umbrella ]  Account Sync Service Stopping...', LOGINFO)
	if libraryService:
		del libraryService # prob does not kill a running thread
		control.log('[ plugin.video.umbrella ]  Library Update Service Stopping...', LOGINFO)
	if schedTrakt:
		schedTrakt.cancel()
	control.log('[ plugin.video.umbrella ]  Service Stopped', LOGINFO)

main()