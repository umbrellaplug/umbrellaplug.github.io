# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from datetime import datetime, timedelta
import time, calendar
import _strptime # import _strptime to workaround python 2 bug with threads
from resources.lib.modules import cleandate
from resources.lib.externals import pytz
from resources.lib.modules import control
from resources.lib.modules.control import lang as getLS, setting as getSetting
import json
from resources.lib.modules import trakt
from resources.lib.modules import simkl
from resources.lib.modules import mdblist
from resources.lib.modules import customtrakt
from resources.lib.modules import floppy
from resources.lib.modules import scrob
from resources.lib.database import traktsync

ZoneUtc = 'utc'
ZoneLocal = 'local'
FormatDateTime = '%Y-%m-%d %H:%M:%S'
FormatDate = '%Y-%m-%d'
FormatTime = '%H:%M:%S'
FormatTimeShort = '%H:%M'
service_syncInterval = int(getSetting('background.service.syncInterval')) if getSetting('background.service.syncInterval') else 30
simkl_syncInterval = int(getSetting('simkl.service.syncInterval')) if getSetting('simkl.service.syncInterval') else 30
mdblist_syncInterval = int(getSetting('mdblist.service.syncInterval')) if getSetting('mdblist.service.syncInterval') else 30
custom_syncInterval = int(getSetting('custom.service.syncInterval')) if getSetting('custom.service.syncInterval') else 30
floppy_syncInterval = int(getSetting('floppy.service.syncInterval')) if getSetting('floppy.service.syncInterval') else 30
scrob_syncInterval = int(getSetting('scrob.service.syncInterval')) if getSetting('scrob.service.syncInterval') else 30

# def datetime_from_string(self, string, format=FormatDateTime):
	# try:
		# return datetime.strptime(string, format)
	# except:
		# # Older Kodi Python versions do not have the strptime function.
		# # http://forum.kodi.tv/showthread.php?tid=112916
		# return datetime.fromtimestamp(time.mktime(time.strptime(string, format)))

def localZone():
	try:
		if time.daylight: # 1 if defined as DST zone
			local_time = time.localtime()
			if local_time.tm_isdst: offsetHour = time.altzone / 3600
			else: offsetHour = time.timezone / 3600
		else: offsetHour = time.timezone / 3600
		return 'Etc/GMT%+d' % offsetHour
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def convert_time(stringTime, stringDay=None, abbreviate=False, formatInput=FormatTimeShort, formatOutput=None, zoneFrom=ZoneUtc, zoneTo=ZoneLocal, remove_zeroes=False):
	result = ''
	try:
		# If only time is given, the date will be set to 1900-01-01 and there are conversion problems if this goes down to 1899.
		if formatInput == '%H:%M':
			stringTime = '%s %s' % (datetime.now().strftime('%Y-%m-%d'), stringTime) # Use current datetime.now() to accomodate for daylight saving time.
			formatNew = '%Y-%m-%d %H:%M'
		else: formatNew = formatInput

		if zoneFrom == ZoneUtc: zoneFrom = pytz.timezone('UTC')
		elif zoneFrom == ZoneLocal: zoneFrom = pytz.timezone(localZone())
		else: zoneFrom = pytz.timezone(zoneFrom)

		if zoneTo == ZoneUtc: zoneTo = pytz.timezone('UTC')
		elif zoneTo == ZoneLocal: zoneTo = pytz.timezone(localZone())
		else: zoneTo = pytz.timezone(zoneTo)

		timeobject = cleandate.datetime_from_string(string_date=stringTime, format=formatNew, date_only=False)

		if stringDay:
			stringDay = stringDay.lower()
			if stringDay.startswith('mon'): weekday = 0
			elif stringDay.startswith('tue'): weekday = 1
			elif stringDay.startswith('wed'): weekday = 2
			elif stringDay.startswith('thu'): weekday = 3
			elif stringDay.startswith('fri'): weekday = 4
			elif stringDay.startswith('sat'): weekday = 5
			else: weekday = 6
			weekdayCurrent = datetime.now().weekday()
			timeobject += timedelta(days=weekday) - timedelta(days=weekdayCurrent)

		timeobject = zoneFrom.localize(timeobject)
		timeobject = timeobject.astimezone(zoneTo)

		if not formatOutput: formatOutput = formatInput

		stringTime = timeobject.strftime(formatOutput)
		if remove_zeroes: stringTime = stringTime.replace(' 0', ' ').replace(':00 ', '')

		if stringDay:
			if abbreviate: stringDay = calendar.day_abbr[timeobject.weekday()]
			else: stringDay = calendar.day_name[timeobject.weekday()]
			return (stringTime, stringDay)
		else: return stringTime
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return stringTime

def nonsense():
	try:
		if not control.condVisibility('System.HasAddon(plugin.video.fen)'):
			control.okDialog(title='Add Fen', message='It appears you currently do not have Fen installed. Please add "https://tikipeter.github.io" as a source and add the Fen repository and addon.')
		else:
			control.notification(message='Launching Fen...')
			control.sleep(200)
			return control.execute('RunAddon(plugin.video.fen)')
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def external_providers():
	try:
		results = control.jsonrpc_get_addons()
		chosen = control.selectDialog([i.get('name') for i in results], 'Select external provider module:')
		if chosen == None or chosen < 0: 
			control.homeWindow.setProperty('umbrella.updateSettings', 'false')
			control.setSetting('provider.external.enabled', 'false')
			control.setSetting('external_provider.name', '')
			control.homeWindow.setProperty('umbrella.updateSettings', 'true')
			control.setSetting('external_provider.module', '')
			return
		try:
			from sys import path
			path.append(control.transPath('special://home/addons/%s/lib' % results[chosen].get('addonid')))
			from importlib import import_module
			getattr(import_module(results[chosen].get('addonid').split('.')[-1]), 'sources')
			success = True
		except:
			success = False
		if success:
			control.homeWindow.setProperty('umbrella.updateSettings', 'false')
			control.setSetting('external_provider.name' , results[chosen].get('addonid').split('.')[-1])
			control.homeWindow.setProperty('umbrella.updateSettings', 'true')
			control.setSetting('external_provider.module', results[chosen].get('addonid'))
			control.notification(title=results[chosen].get('addonid').split('.')[-1], message=getLS(40449))
		else:
			control.okDialog(title=33586, message=getLS(40446) % results[chosen].get('addonid').upper())
			return external_providers()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def delete_all_subs():
	import os, fnmatch
	try:
		#from resources.lib.modules import log_utils
		#log_utils.log('removing all subtitle files.', level=log_utils.LOGDEBUG)
		download_path = control.subtitlesPath
		subtitle = download_path
		def find(pattern, path):
			result = []
			for root, dirs, files in os.walk(path):
				for name in files:
					if fnmatch.fnmatch(name, pattern):
						result.append(os.path.join(root, name))
			return result

		subtitles = find('*.*', subtitle)
		for x in subtitles:
			try:
				os.remove(x)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def resetCustomBG():
	try:
		control.setSetting('custombg','')
		control.openSettings('0.5', 'plugin.video.umbrella')
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def setIndicatorService():
	try:
		import xbmcgui
		currentSetting = control.setting('indicators.alt')
		service_map = [('Local', control.themedIcon('icon.png'), '0')]
		if trakt.getTraktCredentialsInfo():
			service_map.append(('Trakt', control.themedIcon('trakt.png'), '1'))
		if simkl.getSimKLCredentialsInfo():
			service_map.append(('Simkl', control.themedIcon('simkl.png'), '2'))
		if mdblist.getMDBListCredentialsInfo():
			service_map.append(('MDBList', control.themedIcon('mdblist.png'), '3'))
		if customtrakt.getCustomCredentialsInfo():
			service_map.append((customtrakt.getCustomServiceName(), control.themedIcon('icon.png'), '4'))
		if floppy.getFloppyCredentialsInfo():
			service_map.append(('Floppy', control.themedIcon('floppy.png'), '5'))
		if scrob.getScrobCredentialsInfo():
			service_map.append(('Scrob', control.themedIcon('scrob.png'), '6'))
		current_index = next((i for i, (_, _, v) in enumerate(service_map) if v == currentSetting), -1)
		items = []
		for i, (label, icon, _) in enumerate(service_map):
			li = xbmcgui.ListItem(label=label, label2='[COLOR lime]Active[/COLOR]' if i == current_index else '')
			li.setArt({'icon': icon, 'thumb': icon})
			items.append(li)
		select = control.selectDialog(items, 'Please select service to use for indicators:', useDetails=True)
		if select == -1: control.openSettings('5.0', 'plugin.video.umbrella'); return
		selection, _, optionVal = service_map[select]

		if currentSetting != optionVal:
			# DialogProgress (modal, center-screen) rather than DialogProgressBG (small
			# corner toast) — the toast is easy to miss entirely once Settings closes and
			# focus shifts back to whatever screen was behind it.
			dialog = control.progressDialog
			dialog.create(control.addonName(), 'Syncing watch history...')
			def _progress(phase, done=None, total=None):
				try:
					if done is not None and total:
						dialog.update(min(int(100.0 * done / total), 100), '%s... (%s/%s)' % (phase, done, total))
					elif done is not None:
						dialog.update(0, '%s... (%s synced)' % (phase, done))
					else:
						dialog.update(0, '%s...' % phase)
				except: pass
			try:
				if optionVal == '1':
					trakt.sync_watched(forced=True, progress_callback=_progress)
				if optionVal == '2':
					simkl.sync_watched(forced=True, progress_callback=_progress)
				if optionVal == '4':
					customtrakt.sync_watched(forced=True, progress_callback=_progress)
				if optionVal == '5':
					floppy.sync_watched(forced=True, progress_callback=_progress)
				if optionVal == '6':
					scrob.sync_watched(forced=True, progress_callback=_progress)
			finally:
				dialog.close()
		control.homeWindow.setProperty('umbrella.updateSettings', 'false')
		control.setSetting('indicators.alt', optionVal)
		control.homeWindow.setProperty('umbrella.updateSettings', 'true')
		control.setSetting('indicators', str(selection))
		control.openSettings('5.0', 'plugin.video.umbrella')
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def setScrobbleService():
	try:
		import xbmcgui
		currentSetting = control.setting('scrobble.source')
		service_map = [('Local', control.themedIcon('icon.png'), '0')]
		if trakt.getTraktCredentialsInfo():
			service_map.append(('Trakt', control.themedIcon('trakt.png'), '1'))
		if simkl.getSimKLCredentialsInfo():
			service_map.append(('Simkl', control.themedIcon('simkl.png'), '2'))
		if mdblist.getMDBListCredentialsInfo():
			service_map.append(('MDBList', control.themedIcon('mdblist.png'), '3'))
		if customtrakt.getCustomCredentialsInfo():
			service_map.append((customtrakt.getCustomServiceName(), control.themedIcon('icon.png'), '4'))
		if floppy.getFloppyCredentialsInfo():
			service_map.append(('Floppy', control.themedIcon('floppy.png'), '5'))
		if scrob.getScrobCredentialsInfo():
			service_map.append(('Scrob', control.themedIcon('scrob.png'), '6'))
		current_index = next((i for i, (_, _, v) in enumerate(service_map) if v == currentSetting), -1)
		items = []
		for i, (label, icon, _) in enumerate(service_map):
			li = xbmcgui.ListItem(label=label, label2='[COLOR lime]Active[/COLOR]' if i == current_index else '')
			li.setArt({'icon': icon, 'thumb': icon})
			items.append(li)
		select = control.selectDialog(items, getLS(40623), useDetails=True)
		if select == -1: control.openSettings('5.0', 'plugin.video.umbrella'); return
		selection, _, optionVal = service_map[select]
		control.homeWindow.setProperty('umbrella.updateSettings', 'false')
		control.setSetting('scrobble.source', optionVal)
		control.homeWindow.setProperty('umbrella.updateSettings', 'true')
		control.setSetting('scrobble', str(selection))
		control.openSettings('5.0', 'plugin.video.umbrella')
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def services_syncs():
	last_simkl_sync = 0
	last_mdblist_sync = 0
	last_custom_sync = 0
	last_floppy_sync = 0
	last_scrob_sync = 0
	while not control.monitor.abortRequested():
		control.sleep(5000) # wait 5sec in case of device wake from sleep
		try:
			internets = control.condVisibility('System.InternetState') #added for some systems have removed Internet State apparently.
			if internets == False:
				internets = control.condVisibility('System.HasNetwork')
		except:
			internets = None
			from resources.lib.modules import log_utils
			log_utils.error()
		if control.monitor.abortRequested(): break
		if internets and trakt.getTraktCredentialsInfo(): # run service in case user auth's trakt later
			from resources.lib.modules import log_utils
			if control.condVisibility('Player.HasVideo'):
				log_utils.log('Trakt Sync: skipping — video is playing', 1)
			else:
				log_utils.log('Trakt Sync Service is running.', 1)
				activities = trakt.getTraktAsJson('/sync/last_activities', silent=True)
				all_activity_ts = activities.get('all', '') if activities else ''
				all_ts = int(cleandate.iso_2_utc(all_activity_ts)) if all_activity_ts else 0
				last_all_ts = traktsync.last_sync('last_all_activity')
				if all_ts > 0 and all_ts <= last_all_ts:
					log_utils.log('Trakt Sync: no changes since last sync, skipping all', 1)
				else:
					if all_ts > 0: traktsync.insert_service('last_all_activity', all_activity_ts)
					if not control.monitor.abortRequested():
						if getSetting('bookmarks') == 'true' and getSetting('scrobble.source') == '1':
							trakt.sync_playbackProgress(activities)
						trakt.sync_watchedProgress(activities, trigger_refresh=False)
					if not control.monitor.abortRequested():
						if getSetting('indicators.alt') == '1':
							trakt.sync_watched(activities) # writes to traktsync.db as of 1-19-2022
						trakt.sync_user_lists(activities)
						trakt.sync_liked_lists(activities)
						trakt.sync_hidden_progress(activities)
						trakt.sync_collection(activities)
						trakt.sync_watch_list(activities)
						trakt.sync_popular_lists()
						trakt.sync_trending_lists()
		if control.monitor.abortRequested(): break
		if internets and simkl.getSimKLCredentialsInfo():
			current_time = time.time()
			if (current_time - last_simkl_sync) >= (60 * simkl_syncInterval):
				activities = simkl.get_request('/sync/activities')
				activities = json.dumps(activities)
				from resources.lib.modules import log_utils
				log_utils.log('SimKl Sync Service is running.', 1)
				if not control.monitor.abortRequested():
					if getSetting('bookmarks') == 'true' and getSetting('scrobble.source') == '2':
						simkl.sync_playbackProgress(forced=True)
					simkl.sync_watchedProgress(activities)
				if not control.monitor.abortRequested():
					if getSetting('indicators.alt') == '2':
						simkl.sync_watched(activities) #
					simkl.sync_all_watchlists(activities)
				last_simkl_sync = current_time
		if control.monitor.abortRequested(): break
		if internets and mdblist.getMDBListCredentialsInfo():
			current_time = time.time()
			if (current_time - last_mdblist_sync) >= (60 * mdblist_syncInterval):
				activities = mdblist.getActivities()
				from resources.lib.modules import log_utils
				log_utils.log('MDBList Sync Service is running.', 1)
				if not control.monitor.abortRequested():
					# Unconditional like Trakt/Custom/Floppy's equivalents — this feeds
					# mdb_watched_episodes, which the MDBList Episode Progress widget reads
					# from regardless of whether MDBList is the active indicators source.
					# Gating it behind indicators.alt=='3' left that table stale for anyone
					# using the widget with a different indicators source selected.
					mdblist.sync_watchedProgress(activities)
					mdblist.sync_watch_list(activities)
					mdblist.sync_collection(activities)
					mdblist.sync_dropped(activities)
				if not control.monitor.abortRequested():
					if getSetting('bookmarks') == 'true' and getSetting('scrobble.source') == '3':
						mdblist.sync_playbackProgress()
				last_mdblist_sync = current_time
		if control.monitor.abortRequested(): break
		if internets and customtrakt.getCustomCredentialsInfo():
			current_time = time.time()
			if (current_time - last_custom_sync) >= (60 * custom_syncInterval):
				activities = customtrakt.getActivities()
				from resources.lib.modules import log_utils
				log_utils.log('%s Service Sync is running.' % customtrakt.getCustomServiceName(), 1)
				if not control.monitor.abortRequested():
					if getSetting('bookmarks') == 'true' and getSetting('scrobble.source') == '4':
						customtrakt.sync_playbackProgress(activities, forced=True)
					customtrakt.sync_watchedProgress(activities)
				if not control.monitor.abortRequested():
					customtrakt.sync_watch_list(activities, forced=True)
					customtrakt.sync_collection(activities, forced=True)
					customtrakt.sync_dropped(activities, forced=True)
				last_custom_sync = current_time
		if control.monitor.abortRequested(): break
		if internets and floppy.getFloppyCredentialsInfo():
			current_time = time.time()
			if (current_time - last_floppy_sync) >= (60 * floppy_syncInterval):
				from resources.lib.modules import log_utils
				log_utils.log('Floppy Service Sync is running.', 1)
				if not control.monitor.abortRequested():
					if getSetting('bookmarks') == 'true' and getSetting('scrobble.source') == '5':
						floppy.sync_playbackProgress()
					floppy.sync_watchedProgress(forced=True)
				if not control.monitor.abortRequested():
					floppy.sync_watch_list(forced=True)
					floppy.sync_collection(forced=True)
				last_floppy_sync = current_time
		if control.monitor.abortRequested(): break
		if internets and scrob.getScrobCredentialsInfo():
			current_time = time.time()
			if (current_time - last_scrob_sync) >= (60 * scrob_syncInterval):
				from resources.lib.modules import log_utils
				log_utils.log('Scrob Service Sync is running.', 1)
				if not control.monitor.abortRequested():
					if getSetting('bookmarks') == 'true' and getSetting('scrobble.source') == '6':
						scrob.sync_playbackProgress()
					scrob.sync_watchedProgress(forced=True)
				if not control.monitor.abortRequested():
					scrob.sync_user_lists(forced=True)
				last_scrob_sync = current_time
		if control.monitor.waitForAbort(60*service_syncInterval): break

def originCountry_Select():
	countryDict = {'Australia': 'AU', 'Austria': 'AT', 'Brazil': 'BR', 'Bulgaria': 'BG', 'Canada': 'CA', 'China': 'CN', 'Denmark': 'DK', 'Estonia': 'EE',
						'Finland': 'FI', 'France': 'FR', 'Germany': 'DE', 'Greece': 'GR', 'Hungary': 'HU', 'Hong Kong SAR China': 'HK', 'India': 'IN',
						'Indonesia': 'ID', 'Ireland': 'IE', 'Italy': 'IT', 'Japan': 'JP', 'Kazakhstan': 'KZ', 'Latvia': 'LV', 'Lithuania': 'LT', 'Malaysia': 'MY',
						'Mexico': 'MX', 'Netherlands': 'NL', 'New Zealand': 'NZ', 'Norway': 'NO', 'Philippines': 'PH', 'Poland': 'PL', 'Portugal': 'PT',
						'Romania': 'RO', 'Russia': 'RU', 'Saudi Arabia': 'SA', 'Singapore': 'SG', 'Slovakia': 'SK', 'South Africa': 'ZA', 'South Korea': 'KR',
						'Spain': 'ES', 'Sweden': 'SE', 'Switzerland': 'CH', 'Taiwan': 'TW', 'Thailand': 'TH', 'Turkey': 'TR', 'Ukraine': 'UA',
						'United Arab Emirates': 'AE', 'United Kingdom': 'GB', 'United States': 'US', 'Vietnam': 'VN'}
	currentselected = getSetting('originCountry')
	try:
		currentselected = currentselected.split("|")
	except:
		currentselected = None
	if currentselected:
		country_codes = list(countryDict.values())
		selected = [country_codes.index(code) for code in currentselected if code in country_codes]
	multiselected = control.multiSelect('Select Origin Countries', countryDict, selected)
	if multiselected:
		selected = [countryDict[list(countryDict.keys())[i]] for i in multiselected]
		control.setSetting('originCountry', '|'.join(selected))

def make_qr(url, filename='qr.png'):
    #import segno and make a qr code using the url passed in. save the image. return the path.
	if url == None: return
	try:
		from resources.lib.externals import segno
		qrcode = segno.make(url, micro=False)
		dest = control.joinPath(control.dataPath, filename)
		qrcode.save(dest, scale=20)
		image = dest
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return
	return image