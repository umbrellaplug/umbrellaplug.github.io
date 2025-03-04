# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from datetime import datetime, timedelta
from json import loads as jsloads
import re
import _strptime # import _strptime to workaround python 2 bug with threads
from sys import exit as sysexit
from sqlite3 import dbapi2 as database
from urllib.parse import parse_qsl, quote_plus
from resources.lib.modules import control
from resources.lib.modules import cleandate
from resources.lib.modules import cleantitle
from resources.lib.modules import library_sources
from resources.lib.modules import log_utils
from resources.lib.modules import string_tools
from resources.lib.modules.control import yesnoDialog
from resources.lib.modules import trakt


folder_setup = False
service_update = control.setting('library.service.update') == 'true'
service_notification = control.setting('library.service.notification') == 'true'
general_notification = control.setting('library.general.notification') == 'true'
include_unaired = control.setting('library.include_unaired') == 'true'
auto_import_on = control.setting('library.autoimportlists') == 'true'
tmdb_session_id = control.setting('tmdb.sessionid')
getLS = control.lang
trakt_user = control.setting('trakt.user.name').strip()
LOGINFO = log_utils.LOGINFO
use_tmdb = control.setting('tmdb.baseaddress') == 'true'
if use_tmdb:
	tmdb_base = "https://api.tmdb.org"
else:
	tmdb_base = "https://api.themoviedb.org"

class lib_tools:
	@staticmethod
	def create_folder(folder):
		try:
			folder = control.legalFilename(folder)
			control.makeFile(folder)
			try:
				if 'ftp://' not in folder: raise Exception()
				from ftplib import FTP
				ftparg = re.compile(r'ftp://(.+?):(.+?)@(.+?):?(\d+)?/(.+/?)').findall(folder)
				ftp = FTP(ftparg[0][2], ftparg[0][0], ftparg[0][1])
				try: ftp.cwd(ftparg[0][4])
				except: ftp.mkd(ftparg[0][4])
				ftp.quit()
			except: log_utils.error()
		except: log_utils.error()

	@staticmethod
	def write_file(path, content):
		try:
			path = control.legalFilename(path)
			if not isinstance(content, str):
				content = str(content)
			file = control.openFile(path, 'w')
			file.write(str(content))
			file.close()
		except: log_utils.error()

	@staticmethod
	def nfo_url(media_string, ids):
		tvdb_url = 'https://thetvdb.com/?tab=series&id=%s'
		imdb_url = 'https://www.imdb.com/title/%s/'
		tmdb_url = 'https://www.themoviedb.org/%s/%s'
		if 'tvdb' in ids: return tvdb_url % (str(ids['tvdb']))
		elif 'imdb' in ids: return imdb_url % (str(ids['imdb']))
		elif 'tmdb' in ids: return tmdb_url % (media_string, str(ids['tmdb']))
		else: return ''

	@staticmethod
	def legal_filename(filename):
		try:
			filename = filename.strip().replace("'", '').replace('&', 'and')
			filename = re.sub(r'(?!%s)[^\w\-_\.]', '.', filename)
			filename = re.sub(r'\.+', '.', filename)
			filename = re.sub(re.compile(r'(CON|PRN|AUX|NUL|COM\d|LPT\d)\.', re.I), '\\1_', filename)
			# control.legalFilename(filename) # without a var assingment this does jack shit but all exo forks doing it..lol...logs the same but breaks using below an adds trailing "/"
			# filename = control.legalFilename(filename)
			filename = filename.lstrip('.')
			return filename
		except:
			log_utils.error()
			return filename

	@staticmethod
	def make_path(base_path, title, year = '', season = ''):
		try:
			foldername = title.strip().replace("'", '').replace('&', 'and')
			foldername = re.sub(r'[^\w\-_\. ]', '_', foldername)
			foldername = '%s (%s)' % (foldername, year) if year else foldername
			path = control.joinPath(base_path, foldername)
			if season: path = control.joinPath(path, 'Season %s' % season)
			return path
		except: log_utils.error()

	@staticmethod
	def clean():
		control.execute('CleanLibrary(video)')

	@staticmethod
	def total_setup():
		try:
			# control.execute('CleanLibrary(video)')
			libmovies().auto_movie_setup()
			libtvshows().auto_tv_setup()
			control.notification(message=32110)
		except:
			log_utils.error()
			control.notification(message=32111)

	def ckKodiSources(self, paths=None):
		contains = False
		try:
			if paths is None:
				paths = []
				movie_LibraryFolder = control.joinPath(control.transPath(control.setting('library.movie')), '')
				special_movie_LibraryFolder = control.joinPath(control.setting('library.movie'), '')
				paths.append(movie_LibraryFolder)
				paths.append(special_movie_LibraryFolder)
				tvShows_LibraryFolder = control.joinPath(control.transPath(control.setting('library.tv')),'')
				speical_tvShows_LibraryFolder = control.joinPath(control.setting('library.tv'),'')
				paths.append(tvShows_LibraryFolder)
				paths.append(speical_tvShows_LibraryFolder)
			paths = [i.rstrip('/').rstrip('\\') for i in paths]
			result = control.jsonrpc('{"jsonrpc": "2.0", "method": "Files.GetSources", "params": {"media" : "video"}, "id": 1}')
			result = jsloads(result)['result']['sources']
			for i in result:
				if i['file'].rstrip('/').rstrip('\\') in paths:
					contains = True
					break
		except: log_utils.error()
		if not contains:
			try:
				global folder_setup
				global service_update
				if control.setting('library.service.update') == 'false' or service_update is False: return contains
				if folder_setup:
					contains = True
					return contains
				msg = 'Your Library Folders do not exist in Kodi Sources.  Would you like to run full setup of Library Folders to Kodi Sources now?'
				if control.yesnoDialog(msg, '', ''):
					lib_tools.total_setup()
					folder_setup = True
					contains = True
				else:
					msg = 'Would you like to turn off Library Auto Update Service?'
					if control.yesnoDialog(msg, '', ''):
						service_update = False
						control.setSetting('library.service.update', 'false')
						contains = False
						control.notification(message=32112)
						# control.refresh()
			except: log_utils.error()
		return contains

	def service(self):
		self.property = '%s_service_property' % control.addonInfo('name').lower()
		try:
			lib_tools.create_folder(control.joinPath(control.transPath(control.setting('library.movie')), ''))
			lib_tools.create_folder(control.joinPath(control.transPath(control.setting('library.tv')), ''))
		except: pass
		try:
			control.makeFile(control.dataPath)
			dbcon = database.connect(control.libcacheFile)
			dbcur = dbcon.cursor()
			dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
			dbcur.connection.commit()
			fetch = dbcur.execute('''SELECT * FROM service WHERE setting="last_run"''').fetchone()
			if not fetch:
				last_service = "1970-01-01 23:59:00.000000"
				dbcur.execute('''INSERT INTO service Values (?, ?)''', ('last_run', last_service))
				dbcur.connection.commit()
			else: last_service = str(fetch[1])
		except: log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
		try: control.homeWindow.setProperty(self.property, last_service)
		except: return log_utils.error()
		while not control.monitor.abortRequested():
			try:
				last_service = control.homeWindow.getProperty(self.property)
				try:
					library_hours = float(control.setting('library.import.hours'))
				except:
					library_hours = int(6)
				t1 = timedelta(hours=library_hours)
				t2 = cleandate.datetime_from_string(str(last_service), '%Y-%m-%d %H:%M:%S.%f', False)
				t3 = datetime.now()
				check = abs(t3 - t2) >= t1
				if not check: continue
				if (control.player.isPlaying() or control.condVisibility('Library.IsScanningVideo')): continue
				last_service = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
				last_service_setting = datetime.now().strftime('%Y-%m-%d %H:%M')
				control.homeWindow.setProperty(self.property, last_service)
				try:
					dbcon = database.connect(control.libcacheFile)
					dbcur = dbcon.cursor()
					dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
					dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_run', last_service))
					dbcur.connection.commit()
				except: log_utils.error()
				finally:
					dbcur.close() ; dbcon.close()
				try:
					control.setSetting('library.autoimportlists_last', str(last_service_setting))
					self.updateSettings()
				except: log_utils.error()
				if control.setting('library.service.update') == 'false' or service_update is False: continue
				libepisodes().update()
				if auto_import_on:
					libmovies().list_update()
					libtvshows().list_update()
					last_service_setting = datetime.now().strftime('%Y-%m-%d %H:%M')
					control.setSetting('library.autoimportlists_last', str(last_service_setting))
					lib_tools().updateSettings()
				#libuserlist().check_update_time()
				if control.monitor.waitForAbort(60*15): break
				#if control.monitor.waitForAbort(120): break
			except:
				log_utils.error()
    
	def importNow(self, selected_items, select=True):
		
		if control.setting('library.autoimportlists_last') == getLS(40224):
			from resources.lib.modules.control import lang
			if not yesnoDialog(getLS(40227), '', ''): return
		control.setSetting('library.autoimportlists_last', getLS(40224))
		if service_notification:
			control.notification(message=40210)
		try:
			allTraktItems = lib_tools().getAllTraktLists()
			if select: lib_tools().updateLists(selected_items, allTraktItems)
			libepisodes().update()
			libmovies().list_update()
			libtvshows().list_update()
			last_service_setting = datetime.now().strftime('%Y-%m-%d %H:%M')
			control.setSetting('library.autoimportlists_last', str(last_service_setting))
			lib_tools().updateSettings()
			if service_notification:
				control.notification(message=40229)
		except:
			control.setSetting('library.autoimportlists_last', 'Error')
			from resources.lib.modules import log_utils
			log_utils.error()
			if service_notification:
				control.notification(message=40230)

	def clearListfromDB(self, listId):
		try:
			if 'watchlist' in str(listId) or 'me/collection' in str(listId):
				listId = listId
			else:
				listId = 'list'+str(listId)

			dbcon = database.connect(control.libcacheFile)
			dbcur = dbcon.cursor()
			query = '''DROP TABLE IF EXISTS %s;''' % listId
			dbcur.execute(query)
			dbcur.connection.commit()
			control.notification(message=40225)
		except: 
			from resources.lib.modules import log_utils
			log_utils.error()
			return control.notification(message=40226)
		finally:
			dbcur.close() ; dbcon.close()
			return
			

	def importListsManager(self, fromSettings=False):
		try:
			allTraktItems = self.getAllTraktLists()
			for z in allTraktItems:
				z['selected'] = ''
			dbItems = self.getDBItems()
			if len(dbItems) == 0:
				self.createDBItems(allTraktItems)
			else:
				for y in allTraktItems:
					for x in dbItems:
						if x[5] == y['list_id']:
							y['selected'] = x[6]
			items = allTraktItems
			from resources.lib.windows.traktimportlist_manager import TraktImportListManagerXML
			window = TraktImportListManagerXML('traktimportlist_manager.xml', control.addonPath(control.addonId()), results=items)
			selected_items = window.run()
			del window
			if selected_items:
				selected = len(selected_items)
				control.setSetting('library.autoimportlists.number', str(selected))
			if fromSettings == True:
				control.openSettings('12.2', 'plugin.video.umbrella')
			self.updateLists(selected_items, allTraktItems)
				
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def importListsNow(self, fromSettings=False):
		try:
			allTraktItems = self.getAllTraktLists()
			for z in allTraktItems:
				z['selected'] = ''
			items = allTraktItems
			from resources.lib.windows.traktimportlists_now import TraktImportListsNowXML
			window = TraktImportListsNowXML('traktimportlists_now.xml', control.addonPath(control.addonId()), results=items)
			window.run()
			del window
			if fromSettings == True:
				control.openSettings('12.2', 'plugin.video.umbrella')
				
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def importListsNowNoSelect(self, fromSettings=False):
		try:
			libepisodes().update()
			libmovies().list_update()
			libtvshows().list_update()
			last_service_setting = datetime.now().strftime('%Y-%m-%d %H:%M')
			control.setSetting('library.autoimportlists_last', str(last_service_setting))
			lib_tools().updateSettings()
			if fromSettings == True:
				control.openSettings('12.2', 'plugin.video.umbrella')
				
		except:
			from resources.lib.modules import log_utils
			log_utils.error()


	def getDBItems(self):
		try:
			if not control.existsPath(control.dataPath): control.makeFile(control.dataPath)
			dbcon = database.connect(control.libcacheFile)
			dbcur = dbcon.cursor()
			dbcur.execute('''CREATE TABLE IF NOT EXISTS available_import_lists (item_count INT, type TEXT, list_owner TEXT, list_owner_slug TEXT, list_name TEXT, list_id TEXT, selected TEXT, url TEXT, UNIQUE(list_id));''')
			dbcur.connection.commit()
		except: 
			from resources.lib.modules import log_utils
			log_utils.error()
		try:
			results = dbcur.execute('''SELECT * FROM available_import_lists;''').fetchall()
			if not results:
				results = []
		except: 
			from resources.lib.modules import log_utils
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
		return results
	def updateSettings(self):
		try:
			if not control.existsPath(control.dataPath): control.makeFile(control.dataPath)
			dbcon = database.connect(control.libcacheFile)
			dbcur = dbcon.cursor()
			dbcur.execute('''CREATE TABLE IF NOT EXISTS lists (type TEXT, list_name TEXT, url TEXT, UNIQUE(type, list_name, url));''')
			dbcur.connection.commit()
		except: 
			from resources.lib.modules import log_utils
			log_utils.error()
		try:
			results = dbcur.execute('''SELECT * FROM lists;''').fetchall()
			if not results:
				results = []
		except: 
			from resources.lib.modules import log_utils
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
		length = len(results)
		control.setSetting('library.autoimportlists.number', str(length))

	def createDBItems(self, items):
		try:
			control.makeFile(control.dataPath)
			dbcon = database.connect(control.libcacheFile)
			dbcur = dbcon.cursor()
			dbcur.execute('''CREATE TABLE IF NOT EXISTS available_import_lists (item_count INT, type TEXT, list_owner TEXT, list_owner_slug TEXT, list_name TEXT, list_id TEXT, selected TEXT, url TEXT, UNIQUE(list_id));''')
			length = len(items)
			for i in range(length):
				dbcur.execute('''INSERT OR REPLACE INTO available_import_lists Values (?, ?, ?, ?, ?, ?, ?, ?)''', (items[i]['list_count'], items[i]['action'], items[i]['list_owner'], items[i]['list_owner_slug'], items[i]['list_name'], items[i]['list_id'], '', items[i]['url']))
			dbcur.connection.commit()
		except: 
			from resources.lib.modules import log_utils
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()

	def getAllTraktLists(self):
		full_list = []
		try:
			if not control.player.isPlaying(): control.busy()
			from resources.lib.menus import tvshows
			#wltv_items = control.timeFunction(lib_tools().getTVShowWatchlist)
			wltv_items = self.getTVShowWatchlist()
			wltv_items_count = len(wltv_items)
			wltv_item = {'name': 'Watchlist (TV Shows)', 'url': 'https://api.trakt.tv/users/me/watchlist/shows', 'list_owner': 'me', 'list_owner_slug': 'me', 'list_name': 'Watchlist (TV Shows)', 'list_id': 'watchlistTVshows', 'context':'https://api.trakt.tv/users/me/watchlist/shows', 'next': '', 'list_count': wltv_items_count, 'image': 'trakt.png', 'icon': 'DefaultVideoPlaylists.png', 'action': 'tvshows'}
			tv_items = tvshows.TVshows().trakt_user_lists('trakt_list', trakt_user)
			#tv_items = control.timeFunction(tvshows.TVshows().trakt_user_lists, 'trakt_list', trakt_user)
			coltv_items = self.getTVShowCollection()
			#coltv_items = control.timeFunction(lib_tools().getTVShowCollection)
			coltv_items_count = len(coltv_items)
			coltv_item = {'name': 'Collection (TV Shows)', 'url': 'https://api.trakt.tv/users/me/collection/shows', 'list_owner': 'me', 'list_owner_slug': 'me', 'list_name': 'Collection (TV Shows)', 'list_id': 'collectionTVshows', 'context':'https://api.trakt.tv/users/me/watchlist/shows', 'next': '', 'list_count': coltv_items_count, 'image': 'trakt.png', 'icon': 'DefaultVideoPlaylists.png', 'action': 'tvshows'}
			#ltv_items = control.timeFunction(lib_tools().getTraktTVLikedLists)
			ltv_items = self.getTraktTVLikedLists()
			from resources.lib.menus import movies
			#movie_items = control.timeFunction(movies.Movies().trakt_user_lists, 'trakt_list', trakt_user)
			movie_items = movies.Movies().trakt_user_lists('trakt_list', trakt_user)
			#lmovie_items = movies.Movies().traktLlikedlists(create_directory=None)
			lmovie_items = self.getTraktMovieLikedLists()
			#lmovie_items = control.timeFunction(lib_tools().getTraktMovieLikedLists)
			#wlm_items = control.timeFunction(lib_tools().getMovieWatchlist)
			wlm_items = self.getMovieWatchlist()
			wlm_items_count = len(wlm_items)
			wlm_item = {'name': 'Watchlist (Movies)', 'url': 'https://api.trakt.tv/users/me/watchlist/movies', 'list_owner': 'me', 'list_owner_slug': 'me', 'list_name': 'Watchlist (Movies)', 'list_id': 'watchlistMovie', 'context': 'https://api.trakt.tv/users/me/watchlist/movies', 'next': '', 'list_count': wlm_items_count, 'image': 'trakt.png', 'icon': 'DefaultVideoPlaylists.png', 'action': 'movies'}
			colm_items = self.getMovieCollection()
			#colm_items = control.timeFunction(lib_tools().getMovieCollection)
			colm_items_count = len(colm_items)
			colm_item = {'name': 'Collection (Movies)', 'url': 'https://api.trakt.tv/users/me/collection/movies', 'list_owner': 'me', 'list_owner_slug': 'me', 'list_name': 'Collection (Movies)', 'list_id': 'collectionMovie', 'context':'https://api.trakt.tv/users/me/collection/movies', 'next': '', 'list_count': colm_items_count, 'image': 'trakt.png', 'icon': 'DefaultVideoPlaylists.png', 'action': 'movies'}
			if wlm_items_count > 0:
				full_list.append(wlm_item)
			if wltv_items_count > 0:
				full_list.append(wltv_item)
			if coltv_items_count > 0:
				full_list.append(coltv_item)
			if colm_items_count > 0:
				full_list.append(colm_item)
			full_list.extend(tv_items)
			full_list.extend(movie_items)
			full_list.extend(ltv_items)
			full_list.extend(lmovie_items)
			#myfull_list = [i for n, i in enumerate(full_list) if i not in full_list[:n]]
			full_list = [i for n, i in enumerate(full_list) if i.get('list_id') not in [y.get('list_id') for y in full_list[n + 1:]]]
			control.hide()
		except:
			full_list = []
			control.hide()
		return full_list

	def getMovieCollection(self):
		try:
			link = '/users/me/collection/%s?extended=full'
			items = trakt.getTraktAsJson(link % 'movies', silent=True)
		except:
			items = []
		return items

	def getMovieWatchlist(self):
		try:
			link = '/users/me/watchlist/%s?extended=full'
			items = trakt.getTraktAsJson(link % 'movies', silent=True)
		except:
			items = []
		return items

	def getTVShowCollection(self):
		try:
			link = '/users/me/collection/%s?extended=full'
			items = trakt.getTraktAsJson(link % 'shows', silent=True)
		except:
			items = []
		return items

	def getTVShowWatchlist(self):
		try:
			link = '/users/me/watchlist/%s?extended=full'
			items = trakt.getTraktAsJson(link % 'shows', silent=True)
		except:
			items = []
		return items

	def getTraktTVLikedLists(self):
		self.list = []
		try:
			link = '/users/me/likes/lists'
			items = trakt.getTraktAsJson(link, silent=True)
		except:
			items = []
		showOwnerShow = control.setting('trakt.lists.showowner') == 'true'
		self.page_limit = control.setting('page.item.limit')
		self.traktlist_link = 'https://api.trakt.tv/users/%s/lists/%s/items/shows?limit=%s&page=1' % ('%s', '%s', self.page_limit)
		self.highlight_color = control.setting('highlight.color')
		for item in items:
			try:
				list_link = '/users/%s/lists/%s/items/%s'
				trakt_id = item['list']['ids'].get('trakt')
				list_owner_slug = item['list'].get('user').get('ids').get('slug')
				list_items = trakt.getTraktAsJson(list_link % (list_owner_slug, trakt_id, 'shows'), silent=True)
				item['list']['content_type'] = ''
				if not list_items or list_items == '[]': continue
				else: item['list']['content_type'] = 'movies'
				list_name = item['list']['name']
				list_owner = item['list']['user'].get('username')
				list_url = self.traktlist_link % (list_owner_slug, trakt_id)
				list_count = item['list']['item_count']
				if showOwnerShow:
					label = '%s - [COLOR %s]%s[/COLOR]' % (list_name, self.highlight_color, list_owner)
				else:
					label = '%s' % (list_name)
				self.list.append({'name': label, 'list_type': 'traktPulicList', 'url': list_url, 'list_owner': list_owner, 'list_owner_slug': list_owner_slug, 'list_name': list_name, 'list_id': trakt_id, 'context': list_url, 'list_count': list_count, 'image': 'trakt.png', 'icon': 'DefaultVideoPlaylists.png', 'action': 'tvshows'})
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		self.list = sorted(self.list, key=lambda k: re.sub(r'(^the |^a |^an )', '', k['name'].lower()))
		return self.list

	def getTraktMovieLikedLists(self):
		self.list = []
		try:
			link = '/users/me/likes/lists'
			items = trakt.getTraktAsJson(link, silent=True)
		except:
			items = []
		showOwnerShow = control.setting('trakt.lists.showowner') == 'true'
		self.page_limit = control.setting('page.item.limit')
		#self.traktlist_link = 'https://api.trakt.tv/users/%s/lists/%s/items/shows?limit=%s&page=1' % ('%s', '%s', self.page_limit)
		self.traktlist_link = 'https://api.trakt.tv/users/%s/lists/%s/items/movies?limit=%s&page=1' % ('%s', '%s', self.page_limit)
		self.highlight_color = control.setting('highlight.color')
		for item in items:
			try:
				
				list_link = '/users/%s/lists/%s/items/%s'
				trakt_id = item['list']['ids'].get('trakt')
				list_owner_slug = item['list'].get('user').get('ids').get('slug')
				item['list']['content_type'] = ''
				list_items = trakt.getTraktAsJson(list_link % (list_owner_slug, trakt_id, 'movies'), silent=True)
				if not list_items or list_items == '[]': continue
				else: item['list']['content_type'] = 'movies'
				list_items = trakt.getTraktAsJson(list_link % (list_owner_slug, trakt_id, 'shows'), silent=True)
				if not list_items or list_items == '[]': pass
				else: item['list']['content_type'] = 'mixed' if item['list']['content_type'] == 'movies' else 'shows'
				list_name = item['list']['name']
				list_owner = item['list']['user'].get('username')
				list_url = self.traktlist_link % (list_owner_slug, trakt_id)
				list_count = item['list']['item_count']
				if showOwnerShow:
					label = '%s - [COLOR %s]%s[/COLOR]' % (list_name, self.highlight_color, list_owner)
				else:
					label = '%s' % (list_name)
				self.list.append({'name': label, 'list_type': 'traktPulicList', 'url': list_url, 'list_owner': list_owner, 'list_owner_slug': list_owner_slug, 'list_name': list_name, 'list_id': trakt_id, 'context': list_url, 'list_count': list_count, 'image': 'trakt.png', 'icon': 'DefaultVideoPlaylists.png', 'action': 'movies'})
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		self.list = sorted(self.list, key=lambda k: re.sub(r'(^the |^a |^an )', '', k['name'].lower()))
		return self.list

	def updateLists(self, items, allItems):
		if items == None: return
		length = len(allItems)
		itemLength = len(items)
		for j in range(length):
			allItems[j]['selected'] = ''
			for k in range(itemLength):
				if allItems[j]['url'] == items[k]['url']:
					allItems[j]['selected'] = 'true'
		try:
			control.makeFile(control.dataPath)
			dbcon = database.connect(control.libcacheFile)
			dbcur = dbcon.cursor()
			dbcur.execute('''DROP TABLE IF EXISTS available_import_lists;''')
			dbcur.execute('''CREATE TABLE IF NOT EXISTS available_import_lists (item_count INT, type TEXT, list_owner TEXT, list_owner_slug TEXT, list_name TEXT, list_id TEXT, selected TEXT, url TEXT, UNIQUE(list_id));''')
			length = len(allItems)
			for i in range(length):
				dbcur.execute('''INSERT OR REPLACE INTO available_import_lists Values (?, ?, ?, ?, ?, ?, ?, ?)''', (allItems[i]['list_count'], allItems[i]['action'], allItems[i]['list_owner'], allItems[i]['list_owner_slug'], allItems[i]['list_name'], allItems[i]['list_id'], allItems[i]['selected'], allItems[i]['url']))
			dbcur.connection.commit()
		except: 
			from resources.lib.modules import log_utils
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
		try:
			control.makeFile(control.dataPath)
			dbcon = database.connect(control.libcacheFile)
			dbcur = dbcon.cursor()
			dbcur.execute('''DROP TABLE IF EXISTS lists;''')
			dbcur.execute('''CREATE TABLE IF NOT EXISTS lists (type TEXT, list_name TEXT, url TEXT, UNIQUE(type, list_name, url));''')
			lengthItm = len(items)
			for l in range(lengthItm):
				dbcur.execute('''INSERT OR REPLACE INTO lists Values (?, ?, ?)''', (items[l]['type'], items[l]['list_name'], items[l]['url']))
			dbcur.connection.commit()
		except: 
			from resources.lib.modules import log_utils
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()

	def cacheLibraryforSimilar(self):
		#used to cache movies for large library.
		if control.setting('debug.level') == '1':
			log_utils.log('Cache Library for Similar.', level=log_utils.LOGDEBUG)
		recordsLib = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "id": "1"}')
		recordsLib = jsloads(recordsLib)['result']['limits']['total']
		if control.setting('debug.level') == '1':
			log_utils.log('Library Movie Records: %s' % int(recordsLib), level=log_utils.LOGDEBUG)
		control.makeFile(control.dataPath)
		dbcon = database.connect(control.libCacheSimilar)
		dbcur = dbcon.cursor()
		dbcur.execute('''CREATE TABLE IF NOT EXISTS movies (title TEXT, genre TEXT, uniqueid TEXT UNIQUE, rating TEXT, thumbnail TEXT, playcount TEXT, file TEXT, director TEXT, writer TEXT, year TEXT, mpaa TEXT, "set" TEXT, studio TEXT, cast TEXT);''')
		results = dbcur.execute('''SELECT * FROM movies;''').fetchall()
		if not results:
			results = 0
		else:
			results = len(results)
		if control.setting('debug.level') == '1':
			log_utils.log('Library Movie Cached Records: %s' % int(results), level=log_utils.LOGDEBUG)
		if int(results) != int(recordsLib):
			try:
				control.makeFile(control.dataPath)
				dbcon = database.connect(control.libCacheSimilar)
				dbcur = dbcon.cursor()
				dbcur.execute('''DROP TABLE IF EXISTS movies_temp;''')
				dbcur.execute('''CREATE TABLE IF NOT EXISTS movies_temp (title TEXT, genre TEXT, uniqueid TEXT UNIQUE, rating TEXT, thumbnail TEXT, playcount TEXT, file TEXT, director TEXT, writer TEXT, year TEXT, mpaa TEXT, "set" TEXT, studio TEXT, cast TEXT);''')
				#"properties" : ["title", "genre", "uniqueid", "art", "rating", "thumbnail", "playcount", "file", "director", "writer", "year", "mpaa", "set", "studio", "cast"]
				movies = control.jsonrpc('{"jsonrpc":"2.0","method":"VideoLibrary.GetMovies","params":{"properties":["title","genre","uniqueid", "rating","thumbnail","playcount","file","director","writer","year","mpaa","set","studio","cast"]},"id":"42"}')
				items = jsloads(movies)['result']['movies']
				lengthItm = len(items)
				for l in range(lengthItm):
					myGenre =''
					uniqueids =''
					directors=''
					writers = ''
					casts = ''
					studios = ''
					for p in items[l]['genre']:
						if p == items[l]['genre'][-1]:
							myGenre += p
						else:
							myGenre += p +","
					for q in items[l]['uniqueid']:
						uniqueids = str({"imdb": items[l]['uniqueid'].get('imdb'), "tmdb": items[l]['uniqueid'].get('tmdb')})
					for ut in items[l]['director']:
						if ut == items[l]['director'][-1]:
							directors += ut
						else:
							directors += ut +","
					for uy in items[l]['writer']:
						if uy == items[l]['writer'][-1]:
							writers += uy
						else:
							writers += uy +","
					for ud in items[l]['studio']:
						if ud == items[l]['studio'][-1]:
							studios += ud
						else:
							studios += ud +","
					for uw in items[l]['cast']:
						if uw == items[l]['cast'][-1]:
							casts += uw['name']
						else:
							casts += uw['name'] +","
					try:
						dbcur.execute('''INSERT INTO movies_temp Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (items[l]['title'], myGenre, uniqueids, items[l]['rating'], items[l]['thumbnail'], items[l]['playcount'], items[l]['file'], directors, writers, items[l]['year'], items[l]['mpaa'], items[l]['set'], studios, casts))
					except:
						log_utils.log('Cannot add title to movies_temp. Title: %s UniqueID: %s' % (items[l]['title'], uniqueids ), level=log_utils.LOGDEBUG)
				if control.setting('debug.level') == '1':
					log_utils.log('Adding new movies into cache list.', level=log_utils.LOGDEBUG)
				#dbcur.execute('''DROP TABLE IF EXISTS movies;''') #we are not going to drop the table anymore.
				#dbcur.execute('''CREATE TABLE IF NOT EXISTS movies (title TEXT, genre TEXT, uniqueid TEXT, rating TEXT, thumbnail TEXT, playcount TEXT, file TEXT, director TEXT, writer TEXT, year TEXT, mpaa TEXT, "set" TEXT, studio TEXT, cast TEXT);''')
				dbcur.execute('''INSERT OR REPLACE INTO movies SELECT * FROM movies_temp;''')
				dbcur.connection.commit()
				control.refresh()
			except: log_utils.error()
			finally:
				dbcur.close() ; dbcon.close()
				self.syncDeletedfromCache()



	def syncDeletedfromCache(self):
		try:
			control.makeFile(control.dataPath)
			dbcon = database.connect(control.libCacheSimilar)
			dbcur = dbcon.cursor()
			#remove duplicates.....
			#dbcur.execute('''DELETE FROM movies WHERE rowid > (SELECT MIN(rowid) FROM movies p2 WHERE movies.title = p2.title AND movies.genre = p2.genre);''')
			#delete everything not in movies_temp
			dbcur.execute('''DELETE FROM movies WHERE title NOT IN (SELECT title from movies_temp);''')
			if control.setting('debug.level') == '1':
				log_utils.log('Deleting items that are no longer in library from cache.', level=log_utils.LOGDEBUG)
			dbcur.connection.commit()
		except: log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()




class libmovies:
	def __init__(self):
		self.library_folder = control.joinPath(control.transPath(control.setting('library.movie')), '')
		self.library_update = control.setting('library.update') or 'true' 
		self.dupe_chk = control.setting('library.check') or 'true'
		self.movie_cache = control.setting('library.cachesimilar') or 'false'

	def auto_movie_setup(self):
		try:
			control.makeFile(self.library_folder)
			#source_content = "('%s','movies','metadata.themoviedb.org','',2147483647,1,'<settings version=\"2\"><setting id=\"certprefix\" default=\"true\">Rated </setting><setting id=\"fanart\">true</setting><setting id=\"imdbanyway\">true</setting><setting id=\"keeporiginaltitle\" default=\"true\">false</setting><setting id=\"language\" default=\"true\">en</setting><setting id=\"RatingS\" default=\"true\">TMDb</setting><setting id=\"tmdbcertcountry\" default=\"true\">us</setting><setting id=\"trailer\">true</setting></settings>',0,0,NULL,NULL)" % self.library_folder
			#source_content = "('%s','movies','metadata.themoviedb.org','',2147483647,1,'<settings version=\"2\"><setting id=\"keeporiginaltitle\" default=\"true\">false</setting><setting id=\"fanart\">true</setting><setting id=\"landscape\" default=\"true\">false</setting><setting id=\"trailer\">true</setting><setting id=\"language\" default=\"true\">en</setting><setting id=\"tmdbcertcountry\" default=\"true\">us</setting><setting id=\"RatingS\" default=\"true\">TMDb</setting><setting id=\"imdbanyway\" default=\"true\">false</setting><setting id=\"certprefix\" default=\"true\">Rated </setting></settings>',0,0,NULL,NULL)" % self.library_folder
			source_content = "('%s','movies','metadata.themoviedb.org.python','',2147483647,1,'<settings version=\"2\"><setting id=\"keeporiginaltitle\" default=\"true\">false</setting><setting id=\"language\" default=\"true\">en-US</setting><setting id=\"searchlanguage\" default=\"true\">en-US</setting><setting id=\"fanart\" default=\"true\">true</setting><setting id=\"landscape\" default=\"true\">true</setting><setting id=\"trailer\" default=\"true\">true</setting><setting id=\"tmdbcertcountry\" default=\"true\">us</setting><setting id=\"certprefix\" default=\"true\">Rated </setting><setting id=\"RatingS\" default=\"true\">TMDb</setting><setting id=\"imdbanyway\" default=\"true\">false</setting><setting id=\"traktanyway\" default=\"true\">false</setting><setting id=\"multiple_studios\" default=\"true\">false</setting><setting id=\"add_tags\" default=\"true\">true</setting><setting id=\"lastUpdated\" default=\"true\">0</setting><setting id=\"originalUrl\" default=\"true\" /><setting id=\"previewUrl\" default=\"true\" /><setting id=\"enable_fanarttv_artwork\" default=\"true\">true</setting><setting id=\"fanarttv_language\" default=\"true\">en</setting><setting id=\"prioritize_fanarttv_artwork\" default=\"true\">false</setting><setting id=\"fanarttv_clientkey\" default=\"true\" /></settings>',0,0,NULL,NULL)" % self.library_folder
			library_sources.add_source('Umbrella Movies', self.library_folder, source_content, 'DefaultMovies.png')
		except: log_utils.error()

	def list_update(self):
		contains = lib_tools().ckKodiSources()
		if not contains: return
		try:
			if not control.existsPath(control.dataPath): control.makeFile(control.dataPath)
			dbcon = database.connect(control.libcacheFile)
			dbcur = dbcon.cursor()
			dbcur.execute('''CREATE TABLE IF NOT EXISTS lists (type TEXT, list_name TEXT, url TEXT, UNIQUE(type, list_name, url));''')
			dbcur.connection.commit()
		except: log_utils.error()
		try:
			results = dbcur.execute('''SELECT * FROM lists WHERE type LIKE "movies%" OR type LIKE "mixed%";''').fetchall()
			if not results: 
				if service_notification and general_notification:
					return #control.notification(message=32113)
				else:
					return
		except: log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
		total_added = 0
		for list in results:
			type, list_name, url = list[0].split("&")[0], list[1], list[2]
			try:
				url = url.split('&page')[0]
				url = url.split('?limit')[0]
			except:
				url = url
			try:
				if 'trakt' in url and type=="mixed":
					from resources.lib.menus import movies
					items = movies.Movies().trakt_list_mixed(url, control.setting('trakt.user.name').strip())
					items = self.checkListDB(items, url)
				if 'trakt' in url and type=="movies" and 'watchlist' not in url and 'me/collection' not in url:
					from resources.lib.menus import movies
					items = movies.Movies().trakt_list(url, control.setting('trakt.user.name').strip(), folderName='Trakt Watchlist')
					items = self.checkListDB(items, url)
				if 'trakt' in url and type=="movies" and 'watchlist' in url:
					from resources.lib.menus import movies
					items = movies.Movies().traktWatchlist(url, create_directory=None, folderName='Trakt Movies')
					items = self.checkListDB(items, url)
				if 'trakt' in url and type=="movies" and 'me/collection' in url:
					from resources.lib.menus import movies
					items = movies.Movies().traktCollection(url, create_directory=None, folderName='Trakt Collection')
					items = self.checkListDB(items, url)
				if 'themoviedb' in url:
					from resources.lib.indexers import tmdb
					if '/list/' not in url: items = tmdb.Movies().tmdb_list(url)
					else: items = tmdb.Movies().tmdb_collections_list(url)
			except: log_utils.error()
			if not items: continue
			if service_notification and not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo'):
				control.notification(title='Updating from list: ' + list_name + ' - ' + type, message=32552)
			for i in items:
				if control.monitor.abortRequested(): return sysexit()
				try:
					content = i['mediatype']
				except:
					content = None
				if content == 'movies' or content == None or content == 'movie':
					try:
						files_added = self.add('%s (%s)' % (i['title'], i['year']), i['title'], i['year'], i['imdb'], i['tmdb'], range=True)
						if general_notification and files_added > 0: control.notification(title='%s (%s)' % (i['title'], i['year']), message=32554)
						if files_added > 0: total_added += 1
					except: log_utils.error()
				elif content == 'tvshows' or content == 'tvshow':
					try:
						files_added = libtvshows().add(i['title'], i['year'], i['imdb'], i['tmdb'], i['tvdb'], range=True)
						if files_added is None: continue
						if general_notification and files_added > 0: control.notification(title=i['title'], message=32554)
						if files_added > 0: total_added += 1
					except: log_utils.error()
		if self.library_update == 'true' and not control.condVisibility('Library.IsScanningVideo') and total_added > 0:
			if contains:
				control.sleep(10000)
				control.execute('UpdateLibrary(video)')
			elif service_notification: control.notification(message=32103)
		# if self.movie_cache == 'true':
		# 	lib_tools().cacheLibraryforSimilar()

	def checkListDB(self, items, url):
		if not items: return
		try:
			control.makeFile(control.dataPath)
			dbcon = database.connect(control.libcacheFile)
			dbcur = dbcon.cursor()
			if 'watchlist' not in url and 'me/collection' not in url:
				try:
					listId = url.split('/items')[0]
					listId = listId.split('/lists/')[1]
					listId = re.sub('[^A-Za-z0-9]+', '', listId)
					listId = 'list'+listId
				except:
					listId = ''
			else:
				if 'watchlist' in url:
					try:
						url = url.split('/watchlist/')[1]
						if url == 'shows':
							listId = 'watchlistTVshows'
						if url == 'movies':
							listId = 'watchlistMovie'
					except:
						listId = ''
				else:
					try:
						url = url.split('/collection/')[1]
						if url == 'shows':
							listId = 'collectionTVshows'
						if url == 'movies':
							listId = 'collectionMovie'
					except:
						listId = ''
			if listId == '': return control.notification(message=33586)
			query = '''CREATE TABLE IF NOT EXISTS %s (item_title TEXT, tmdb TEXT, imdb TEXT, last_import DATE, UNIQUE(imdb));''' % listId
			dbcur.execute(query)
			dbcur.connection.commit()
		except: 
			from resources.lib.modules import log_utils
			log_utils.error()
		try:
			control.makeFile(control.dataPath)
			dbcon = database.connect(control.libcacheFile)
			dbcur = dbcon.cursor()
			query2 = '''SELECT * FROM %s;''' % listId
			results = dbcur.execute(query2).fetchall()
			if not results: #need to build a table here for the list none exists.
				length = len(items)
				for i in range(length):
					dateImported = datetime.now()
					query = '''INSERT OR REPLACE INTO %s Values ("%s", "%s", "%s", "%s")''' % (listId, items[i].get('title'), items[i].get('tmdb'), items[i].get('imdb'), dateImported)
					dbcur.execute(query)
				dbcur.connection.commit()
				return items
			else:
				#go through the items in database and compare to list now.
				backitems = items.copy()
				length = len(items)
				length2 = len(results)
				for i in range(length):
					for j in range(length2):
						if items[i].get('title') == results[j][0] and items[i].get('tmdb') == results[j][1] and items[i].get('imdb') == results[j][2]:
							#check each item here and see if new episodes have been released before removing it from items to be returned.
							if items[i].get('mediatype') == 'tvshows':
								if libtvshows().dbepisodeCheck(items[i], results[j][3]) == False:
									backitems.remove(items[i])
							else:
								backitems.remove(items[i])
				if len(backitems) > 0:
					dateImported = datetime.now()
					query3 = '''DROP TABLE IF EXISTS %s;''' % listId
					dbcur.execute(query3)
					query4 = '''CREATE TABLE IF NOT EXISTS %s (item_title TEXT, tmdb TEXT, imdb TEXT, last_import DATE, UNIQUE(imdb));''' % listId
					dbcur.execute(query4)
					for i in range(length):
						query = '''INSERT OR REPLACE INTO %s Values ("%s", "%s", "%s", "%s")''' % (listId, items[i].get('title'), items[i].get('tmdb'), items[i].get('imdb'), dateImported)
						dbcur.execute(query)
				else:
					dateImported = datetime.now()
					query5 = '''UPDATE %s SET last_import = "%s"''' % (listId, dateImported)
					dbcur.execute(query5)
				dbcur.connection.commit()
			return backitems
		except: 
			from resources.lib.modules import log_utils
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()

	def add(self, name, title, year, imdb, tmdb, range=False):
		try:
			contains = lib_tools().ckKodiSources()
			if general_notification:
				if not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo'):
					control.notification(title=name, message=32552)
			try:
				if not self.dupe_chk == 'true': raise Exception()
				id = [imdb, tmdb] if tmdb else [imdb]
				lib = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["imdbnumber", "title", "originaltitle", "year"]}, "id": 1}' % (year, str(int(year)+1), str(int(year)-1)))
				lib = jsloads(lib)['result']['movies']
				lib = [i for i in lib if str(i['imdbnumber']) in id or (cleantitle.get(title) in (cleantitle.get(i['title']), cleantitle.get(i['originaltitle'])) and str(i['year']) == year)]
			except: lib = []
			files_added = 0
			try:
				if lib != []: raise Exception()
				self.strmFile({'name': name, 'title': title, 'year': year, 'imdb': imdb, 'tmdb': tmdb})
				files_added += 1
			except: pass
			if files_added == 0 and general_notification: control.notification(title=name, message=32652)
			if range: return files_added
			if self.library_update == 'true' and not control.condVisibility('Library.IsScanningVideo') and files_added > 0:
				if contains:
					if general_notification: control.notification(title=name, message=32554)
					control.sleep(10000)
					control.execute('UpdateLibrary(video)')
				elif general_notification: control.notification(title=name, message=32104)
			# if self.movie_cache == 'true':
			# 	lib_tools().cacheLibraryforSimilar()
		except: pass

	def silent(self, url):
		control.hide()
		contains = lib_tools().ckKodiSources()
		if service_notification and not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo'):
			control.notification(message=32645)
		from resources.lib.menus import movies
		items = movies.Movies().get(url, create_directory=False)
		if not items: items = []
		total_added = 0
		for i in items:
			try:
				if control.monitor.abortRequested(): return sysexit()
				files_added = self.add('%s (%s)' % (i['title'], i['year']), i['title'], i['year'], i['imdb'], i['tmdb'], range=True)
				if general_notification and files_added > 0: control.notification(title='%s (%s)' % (i['title'], i['year']), message=32554)
				if files_added > 0: total_added += 1
			except: log_utils.error()
		if self.library_update == 'true' and not control.condVisibility('Library.IsScanningVideo') and total_added > 0:
			if contains:
				control.sleep(10000)
				control.execute('UpdateLibrary(video)')
			elif general_notification: control.notification(message=32103)
		if service_notification: control.notification(message=32105)
		# if self.movie_cache == 'true':
		# 	lib_tools().cacheLibraryforSimilar()

	def range(self, url, list_name, silent=None):
		#control.hide()
		#if not control.yesnoDialog(control.lang(32555), '', ''): return
		try:
			if 'traktcollection' in url: message = 32661
			elif 'traktwatchlist' in url: message = 32662
			elif all(i in url for i in ('trakt', '/me/', '/lists/')): message = 32663
			elif all(i in url for i in ('trakt', '/lists/')) and '/me/' not in url: message = 32664
			elif 'tmdb_watchlist' in url: message = 32679
			elif 'tmdb_favorites' in url: message = 32680
			elif all(i in url for i in ('themoviedb', '/list/')): message = 32681
			else: message = 'list import'
		except: log_utils.error()
		if general_notification:
			if not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo'):
				control.notification(message=message)
		items = []
		try:
			if 'trakt' in url:
				if 'traktcollection' in url: url = 'https://api.trakt.tv/users/me/collection/movies'
				if 'traktwatchlist' in url: url = 'https://api.trakt.tv/users/me/watchlist/movies'
				from resources.lib.menus import movies
				items = movies.Movies().trakt_list(url, control.setting('trakt.user.name').strip(),'Trakt Movie List')
			if 'tmdb' in url:
				if 'tmdb_watchlist' in url:
					url = tmdb_base+'/3/account/{account_id}/watchlist/movies?api_key=%s&session_id=%s' % ('%s', tmdb_session_id)
				if 'tmdb_favorites' in url: 
					url = tmdb_base+'/3/account/{account_id}/favorite/movies?api_key=%s&session_id=%s' % ('%s', tmdb_session_id) 
				from resources.lib.indexers import tmdb
				items = tmdb.Movies().tmdb_list(url)
			if (all(i in url for i in ('themoviedb', '/list/'))):
				url = url.split('&sort_by')[0]
				from resources.lib.indexers import tmdb
				items = tmdb.Movies().tmdb_collections_list(url)
		except: log_utils.error()
		if not items:
			if general_notification: return control.notification(title=message, message=33049)
		contains = lib_tools().ckKodiSources()
		total_added = 0
		numitems = len(items)
		if silent == False:
			if not control.yesnoDialog((getLS(40213) % (list_name, numitems)), '', ''): return
		importmessage = ('Starting import of %s' % list_name)
		control.notification(title='Importing', message=importmessage)
		for i in items:
			if control.monitor.abortRequested(): return sysexit()
			try:
				files_added = self.add('%s (%s)' % (i['title'], i['year']), i['title'], i['year'], i['imdb'], i['tmdb'], range=True)
				if general_notification and files_added > 0: control.notification(title='%s (%s)' % (i['title'], i['year']), message=32554)
				if files_added > 0: total_added += 1
			except: log_utils.error()
		try:
			content_type = 'movies'
			control.makeFile(control.dataPath)
			dbcon = database.connect(control.libcacheFile)
			dbcur = dbcon.cursor()
			dbcur.execute('''CREATE TABLE IF NOT EXISTS lists (type TEXT, list_name TEXT, url TEXT, UNIQUE(type, list_name, url));''')
			dbcur.execute('''INSERT OR REPLACE INTO lists Values (?, ?, ?)''', (content_type, list_name, url))
			dbcur.connection.commit()
		except: log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
		if self.library_update == 'true' and not control.condVisibility('Library.IsScanningVideo') and total_added > 0:
			if contains:
				control.sleep(10000)
				control.execute('UpdateLibrary(video)')
				control.notification(title='Import Complete', message='[B]%s[/B] Items imported from [B]%s[/B]' % (total_added, list_name))
			elif general_notification: 
				control.notification(message=32103)
				control.notification(title='Import Complete', message='[B]%s[/B] items imported from [B]%s[/B] with some strm errors.' % (total_added, list_name))
		#libuserlist().set_update_dateTime()
		# if self.movie_cache == 'true':
		# 	lib_tools().cacheLibraryforSimilar()

	def strmFile(self, i):
		try:
			title, year, imdb, tmdb = i['title'], i['year'], i['imdb'], i['tmdb']
			systitle = quote_plus(title)
			try: transtitle = title.translate(None, '\/:*?"<>|')
			except: transtitle = title.translate(title.maketrans('', '', '\/:*?"<>|'))
			transtitle = string_tools.normalize(transtitle)
			if control.setting('library.strm.use_tmdbhelper') == 'true':
				content = 'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=movie&islocal=True&tmdb_id=%s' % tmdb
			else:
				content = 'plugin://plugin.video.umbrella/?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s' % (systitle, year, imdb, tmdb)
			folder = lib_tools.make_path(self.library_folder, transtitle, year)
			lib_tools.create_folder(folder)
			lib_tools.write_file(control.joinPath(folder, lib_tools.legal_filename(transtitle) + '.' + year + '.strm'), content)
			lib_tools.write_file(control.joinPath(folder, lib_tools.legal_filename(transtitle) + '.' + year + '.nfo'), lib_tools.nfo_url('movie', i))
		except: log_utils.error()


class libtvshows:
	def __init__(self):
		self.library_folder = control.joinPath(control.transPath(control.setting('library.tv')),'')
		self.library_update = control.setting('library.update') or 'true'
		self.dupe_chk = control.setting('library.check') or 'true'
		self.include_special = control.setting('library.include_special') or 'true'
		self.include_unknown = control.setting('library.include_unknown') or 'true'
		self.date_time = datetime.utcnow()
		if control.setting('library.importdelay') != 'true': self.date = self.date_time.strftime('%Y%m%d')
		else: self.date = (self.date_time - timedelta(hours=24)).strftime('%Y%m%d')
		self.block = False

	def auto_tv_setup(self):
		try:
			control.makeFile(self.library_folder)
			# icon = control.joinPath(control.artPath(), 'libtv.png')
			source_name = 'Umbrella TV Shows'
			# TVDb scraper
			#source_content = "('%s','tvshows','metadata.tvdb.com','',0,0,'<settings version=\"2\"><setting id=\"absolutenumber\" default=\"true\">false</setting><setting id=\"alsoimdb\">true</setting><setting id=\"dvdorder\" default=\"true\">false</setting><setting id=\"fallback\">true</setting><setting id=\"fallbacklanguage\">es</setting><setting id=\"fanart\">true</setting><setting id=\"language\" default=\"true\">en</setting><setting id=\"RatingS\" default=\"true\">TheTVDB</setting><setting id=\"usefallbacklanguage1\">true</setting></settings>',0,0,NULL,NULL)" % self.library_folder
			source_content = "('%s','tvshows','metadata.tvshows.themoviedb.org.python','',0,0,'<settings version=\"2\"><setting id=\"language\" default=\"true\">en-US</setting><setting id=\"tmdbcertcountry\" default=\"true\">us</setting><setting id=\"usecertprefix\" default=\"true\">true</setting><setting id=\"certprefix\" default=\"true\">Rated </setting><setting id=\"keeporiginaltitle\" default=\"true\">false</setting><setting id=\"cat_landscape\" default=\"true\">true</setting><setting id=\"studio_country\" default=\"true\">false</setting><setting id=\"enab_trailer\" default=\"true\">true</setting><setting id=\"players_opt\" default=\"true\">Tubed</setting><setting id=\"ratings\" default=\"true\">TMDb</setting><setting id=\"imdbanyway\" default=\"true\">false</setting><setting id=\"traktanyway\" default=\"true\">false</setting><setting id=\"tmdbanyway\" default=\"true\">true</setting><setting id=\"enable_fanarttv\" default=\"true\">true</setting><setting id=\"fanarttv_clientkey\" default=\"true\" /><setting id=\"verboselog\" default=\"true\">false</setting><setting id=\"lastUpdated\" default=\"true\">0</setting><setting id=\"originalUrl\" default=\"true\" /><setting id=\"previewUrl\" default=\"true\" /></settings>',0,0,NULL,NULL)" % self.library_folder
			# TMDb scraper
			# source_content = "('%s','tvshows','metadata.tvshows.themoviedb.org','',0,0,'<settings version=\"2\"><setting id=\"alsoimdb\" default=\"true\">false</setting><setting id=\"certprefix\" default=\"true\"></setting><setting id=\"fallback\">true</setting><setting id=\"fanarttvart\">true</setting><setting id=\"keeporiginaltitle\" default=\"true\">false</setting><setting id=\"language\" default=\"true\">en</setting><setting id=\"RatingS\" default=\"true\">Themoviedb</setting><setting id=\"tmdbart\">true</setting><setting id=\"tmdbcertcountry\" default=\"true\">us</setting></settings>',0,0,NULL,NULL)" % self.library_folder
			# control.add_source(source_name, self.library_folder, source_content, icon)
			library_sources.add_source(source_name, self.library_folder, source_content, 'DefaultTVShows.png')
		except: log_utils.error()

	def list_update(self):
		contains = lib_tools().ckKodiSources()
		if not contains: return
		try:
			if not control.existsPath(control.dataPath): control.makeFile(control.dataPath)
			dbcon = database.connect(control.libcacheFile)
			dbcur = dbcon.cursor()
			dbcur.execute('''CREATE TABLE IF NOT EXISTS lists (type TEXT, list_name TEXT, url TEXT, UNIQUE(type, list_name, url));''')
			dbcur.connection.commit()
		except: log_utils.error()
		try:
			results = dbcur.execute('''SELECT * FROM lists WHERE type LIKE "tvshows%";''').fetchall()
			if not results: 
				if service_notification and general_notification:
					return #control.notification(message=32124)
				else:
					return
		except: log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
		total_added = 0 ; items = []
		for list in results:
			type, list_name, url = list[0].split("&")[0], list[1], list[2]
			try:
				url = url.split('&page')[0]
				url = url.split('?limit')[0]
			except:
				url = url
			try:
				if 'trakt' in url and 'watchlist' not in url and 'me/collection' not in url:
					from resources.lib.menus import tvshows
					items = tvshows.TVshows().trakt_list(url, control.setting('trakt.user.name').strip(), folderName='Trakt List')
					items = libmovies().checkListDB(items, url)
				if 'trakt' in url and 'watchlist' in url:
					from resources.lib.menus import tvshows
					items = tvshows.TVshows().traktWatchlist(url, create_directory=None, folderName='Trakt Watchlist')
					items = libmovies().checkListDB(items, url)
				if 'trakt' in url and 'me/collection' in url:
					from resources.lib.menus import tvshows
					items = tvshows.TVshows().traktCollection(url, create_directory=None, folderName='Trakt Collection')
					items = libmovies().checkListDB(items, url)
				if 'themoviedb' in url:
					from resources.lib.indexers import tmdb
					if '/list/' not in url: items = tmdb.TVshows().tmdb_list(url)
					else: items = tmdb.TVshows().tmdb_collections_list(url)
			except: log_utils.error()
			if not items: continue
			if service_notification and not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo'):
				control.notification(title='Updating from list: ' + list_name + ' - ' + type, message=32552)
			for i in items:
				if control.monitor.abortRequested(): return sysexit()
				try:
					files_added = self.add(i['title'], i['year'], i['imdb'], i['tmdb'], i['tvdb'], range=True)
					if files_added is None: continue
					if general_notification and files_added > 0: control.notification(title=i['title'], message=32554)
					if files_added > 0: total_added += 1
				except: log_utils.error()
		if self.library_update == 'true' and not control.condVisibility('Library.IsScanningVideo') and total_added > 0:
			if contains:
				control.sleep(10000)
				control.execute('UpdateLibrary(video)')
			elif service_notification: control.notification(message=32103)

	def dbepisodeCheck(self, item, lastimport):
		newEpisode = False
		try:
			from resources.lib.menus import seasons, episodes
			seasons = seasons.Seasons().tmdb_list(item.get('tvshowtitle'), item.get('imdb'), item.get('tmdb'), item.get('tvdb'), art=None) # fetch fresh meta (uncached)
			# status = seasons[0]['status'].lower()
		except:
			log_utils.error()
			return newEpisode
		for season in seasons:
			try: items = episodes.Episodes().tmdb_list(item.get('tvshowtitle'), item.get('imdb'), item.get('tmdb'), item.get('tvdb'), meta=season, season=season['season'])
			except:
				log_utils.error()
				return newEpisode
			try: items = [{'title': i['title'], 'year': i['year'], 'imdb': i['imdb'], 'tmdb': i['tmdb'], 'tvdb': i['tvdb'], 'season': i['season'], 'episode': i['episode'], 'tvshowtitle': i['tvshowtitle'], 'premiered': i['premiered']} for i in items]
			except: items = []
			if not items: return False
			for i in items:
				premiered = i.get('premiered', '')
				if premiered:
					lastimportshort = lastimport.split(' ')[0]
					if datetime.strptime(premiered, '%Y-%m-%d').date() < datetime.now().date() and datetime.strptime(premiered, '%Y-%m-%d').date()> datetime.strptime(lastimportshort, '%Y-%m-%d').date():
						return True
				else:
					return False

	def add(self, tvshowtitle, year, imdb, tmdb, tvdb, range=False):
		try:
			contains = lib_tools().ckKodiSources()
			if general_notification:
				if not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo'):
					control.notification(title=tvshowtitle, message=32552)
			try:
				from resources.lib.menus import seasons, episodes
				seasons = seasons.Seasons().tmdb_list(tvshowtitle, imdb, tmdb, tvdb, art=None) # fetch fresh meta (uncached)
				# status = seasons[0]['status'].lower()
			except: return log_utils.error()
			files_added = 0
			for season in seasons:
				try: items = episodes.Episodes().tmdb_list(tvshowtitle, imdb, tmdb, tvdb, meta=season, season=season['season'])
				except: return log_utils.error()
				try: items = [{'title': i['title'], 'year': i['year'], 'imdb': i['imdb'], 'tmdb': i['tmdb'], 'tvdb': i['tvdb'], 'season': i['season'], 'episode': i['episode'], 'tvshowtitle': i['tvshowtitle'], 'premiered': i['premiered']} for i in items]
				except: items = []
				if not items: return
				try:
					if self.dupe_chk != 'true': raise Exception()
					id = [items[0]['imdb'], items[0]['tvdb']] # imdbnumber is all that it compares from kodi library
					lib = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties": ["imdbnumber", "title", "year"]}, "id": 1}' % (year, str(int(year)+1), str(int(year)-1)))
					lib = jsloads(lib)['result']['tvshows']
					lib = [i['title'] for i in lib if str(i['imdbnumber']) in id or (i['title'] == items[0]['tvshowtitle'] and str(i['year']) == items[0]['year'])][0]
					lib = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"filter":{"and": [{"field": "tvshow", "operator": "is", "value": "%s"}]}, "properties": ["season", "episode"]}, "id": 1}' % lib)
					lib = jsloads(lib)['result']['episodes']
					lib = ['S%02dE%02d' % (int(i['season']), int(i['episode'])) for i in lib]
					items = [i for i in items if not 'S%02dE%02d' % (int(i['season']), int(i['episode'])) in lib]
				except: lib = []
				for i in items:
					if lib != []: continue # this prevents missing eps to get added if item is aded back
					if control.monitor.abortRequested(): return sysexit()
					try:
						if str(i.get('season')) == '0' and self.include_special == 'false': continue
						premiered = i.get('premiered', '')
						if not premiered and self.include_unknown == 'false': continue
						if not include_unaired:
							if premiered == None or premiered =='':
								continue
							try:
								if datetime.strptime(premiered, '%Y-%m-%d').date() > datetime.now().date():
									continue
							except:
								log_utils.error()
								continue
						self.strmFile(i)
						files_added += 1
					except: log_utils.error()
			if files_added == 0 and general_notification: control.notification(title=tvshowtitle, message=32652)
			if range: return files_added
			if self.library_update == 'true' and not control.condVisibility('Library.IsScanningVideo') and files_added > 0:
				if contains:
					if general_notification: control.notification(title=tvshowtitle, message=32554)
					control.execute('UpdateLibrary(video)')
				elif general_notification: control.notification(title=tvshowtitle, message=32104)
		except: log_utils.error()

	def silent(self, url):
		control.hide()
		contains = lib_tools().ckKodiSources()
		if service_notification and not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo'):
			control.notification(message=32645)		
		from resources.lib.menus import tvshows
		items = tvshows.TVshows().get(url, idx=False)
		if not items: items = []
		total_added = 0
		for i in items:
			if control.monitor.abortRequested(): return sysexit()
			try:
				files_added = self.add(i['title'], i['year'], i['imdb'], i['tmdb'], i['tvdb'], range=True)
				if general_notification and files_added > 0: control.notification(title=i['title'], message=32554)
				if files_added:
					if files_added > 0: total_added += 1
			except Exception as e: 
				from resources.lib.modules import log_utils
				log_utils.log('tvshowtitle: (%s) ids={imdb: %s, tmdb: %s, tvdb: %s} was not added due to exception: %s:' % (i['title'], i['imdb'], i['tmdb'], i['tvdb'], str(e)), __name__, log_utils.LOGINFO) # log show that had issues.
		if self.library_update == 'true' and not control.condVisibility('Library.IsScanningVideo') and total_added > 0:
			if contains:
				control.sleep(10000)
				control.execute('UpdateLibrary(video)')
			elif service_notification: control.notification(message=32103)
		if service_notification: control.notification(message='Trakt TV Show Sync Complete')

	def range(self, url, list_name, silent=False):
		#control.hide()
		#if not control.yesnoDialog(control.lang(32555), '', ''): return
		try:
			if 'traktcollection' in url: message = 32661
			elif 'traktwatchlist' in url: message = 32662
			elif all(i in url for i in ('trakt', '/me/', '/lists/')): message = 32663
			elif all(i in url for i in ('trakt', '/lists/')) and '/me/' not in url: message = 32664
			elif 'tmdb_watchlist' in url: message = 32679
			elif 'tmdb_favorites' in url: message = 32680
			elif all(i in url for i in ('themoviedb', '/list/')): message = 32681
			else: message = 'list import'
		except: log_utils.error()
		if general_notification:
			if not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo'):
				control.notification(message=message)
		items = []
		try:
			if 'trakt' in url:
				if 'traktcollection' in url: url = 'https://api.trakt.tv/users/me/collection/shows'
				if 'traktwatchlist' in url: url = 'https://api.trakt.tv/users/me/watchlist/shows'
				from resources.lib.menus import tvshows
				items = tvshows.TVshows().trakt_list(url, control.setting('trakt.user.name').strip(),'Trakt TV Collection')
			if 'tmdb' in url:
				if 'tmdb_watchlist' in url:
					url = tmdb_base+'/3/account/{account_id}/watchlist/tv?api_key=%s&session_id=%s' % ('%s', tmdb_session_id)
				if 'tmdb_favorites' in url: 
					url = tmdb_base+'/3/account/{account_id}/favorite/tv?api_key=%s&session_id=%s' % ('%s', tmdb_session_id) 
				from resources.lib.indexers import tmdb
				items = tmdb.TVshows().tmdb_list(url)
			if (all(i in url for i in ('themoviedb', '/list/'))):
				url = url.split('&sort_by')[0]
				from resources.lib.indexers import tmdb
				items = tmdb.TVshows().tmdb_collections_list(url)
		except: log_utils.error()
		if not items:
			if general_notification: return control.notification(title=message, message=33049)
		contains = lib_tools().ckKodiSources()
		total_added = 0
		numitems = len(items)
		if silent == False:
			if not control.yesnoDialog((getLS(40213) % (list_name, numitems)), '', ''): return
		importmessage = ('Starting import of %s' % list_name)
		control.notification(title='Importing', message=importmessage)
		for i in items:
			if control.monitor.abortRequested(): return sysexit()
			try:
				if i.get('title','') == '':
					myTitle = {'title': i.get('tvshowtitle')}
					i.update(myTitle)
				files_added = self.add(i['title'], i['year'], i['imdb'], i['tmdb'], i['tvdb'], range=True)
				if general_notification and files_added > 0: control.notification(title=i['title'], message=32554)
				if files_added:
					if files_added > 0: total_added += 1
				
			except: log_utils.error()
		try:
			content_type = 'tvshows'
			control.makeFile(control.dataPath)
			dbcon = database.connect(control.libcacheFile)
			dbcur = dbcon.cursor()
			dbcur.execute('''CREATE TABLE IF NOT EXISTS lists (type TEXT, list_name TEXT, url TEXT, UNIQUE(type, list_name, url));''')
			dbcur.execute('''INSERT OR REPLACE INTO lists Values (?, ?, ?)''', (content_type, list_name, url))
			dbcur.connection.commit()
		except: log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
		if self.library_update == 'true' and not control.condVisibility('Library.IsScanningVideo') and total_added > 0:
			if contains:
				control.sleep(10000)
				control.execute('UpdateLibrary(video)')
				control.notification(title='Import Complete', message='[B]%s[/B] Items imported from [B]%s[/B]' % (total_added, list_name))
			elif general_notification: 
				control.notification(message=32103)
				control.notification(title='Import Complete', message='[B]%s[/B] items imported from [B]%s[/B] with some strm errors.' % (total_added, list_name))
		#libuserlist().set_update_dateTime()

	def strmFile(self, i):
		try:
			title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, premiered = i['title'], i['year'], i['imdb'], i['tmdb'], i['tvdb'], i['season'], i['episode'], i['tvshowtitle'], i['premiered']
			systitle = quote_plus(title)
			systvshowtitle, syspremiered = quote_plus(tvshowtitle), quote_plus(premiered)
			try: transtitle = tvshowtitle.translate(None, '\/:*?"<>|')
			except: transtitle = tvshowtitle.translate(tvshowtitle.maketrans('', '', '\/:*?"<>|'))
			transtitle = string_tools.normalize(transtitle)
			if control.setting('library.strm.use_tmdbhelper') == 'true':
				content = 'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&islocal=True&tmdb_id=%s&season=%s&episode=%s&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&tvshowtitle=%s&premiered=%s' % (
							tmdb, season, episode, systitle, year, imdb, tmdb, tvdb, systvshowtitle, syspremiered)
			else:
				content = 'plugin://plugin.video.umbrella/?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s' % (
							systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, syspremiered)

			folder = lib_tools.make_path(self.library_folder, transtitle, year)
			if not control.isfilePath(control.joinPath(folder, 'tvshow.nfo')):
				lib_tools.create_folder(folder)
				lib_tools.write_file(control.joinPath(folder, 'tvshow.nfo'), lib_tools.nfo_url('tv', i))
			folder = lib_tools.make_path(self.library_folder, transtitle, year, season)
			lib_tools.create_folder(folder)
			lib_tools.write_file(control.joinPath(folder, lib_tools.legal_filename('%s S%02dE%02d' % (transtitle, int(season), int(episode))) + '.strm'), content)
		except: log_utils.error()


class libepisodes:
	def __init__(self):
		self.library_folder = control.joinPath(control.transPath(control.setting('library.tv')),'')
		self.library_update = control.setting('library.update') or 'true'
		self.include_special = control.setting('library.include_special') or 'true'
		self.include_unknown = control.setting('library.include_unknown') or 'true'
		self.date_time = datetime.utcnow()
		if control.setting('library.importdelay') != 'true': self.date = self.date_time.strftime('%Y%m%d')
		else: self.date = (self.date_time - timedelta(hours=24)).strftime('%Y%m%d')

	def update(self):
		# if control.setting('library.service.update') == 'false': control.notification(message=32106)
		contains = lib_tools().ckKodiSources()
		if not contains: return control.notification(message=32107)
		try:
			items, season, episode = [], [], []
			show = [control.joinPath(self.library_folder, i) for i in control.listDir(self.library_folder)[0]]
			if show == []:
				return control.notification(message=32108)
			for s in show:
				try: season += [control.joinPath(s, i) for i in control.listDir(s)[0]]
				except: pass
			for s in season:
				try: episode.append([control.joinPath(s, i) for i in control.listDir(s)[1] if i.endswith('.strm')][-1])
				except: pass
			for file in episode:
				try:
					file = control.openFile(file)
					read = file.read()
					file.close()
					if not read.startswith(('plugin://plugin.video.themoviedb.helper', 'plugin://plugin.video.umbrella')): continue
					params = dict(parse_qsl(read.replace('?','')))
					try: tvshowtitle = params['tvshowtitle']
					except:
						try: tvshowtitle = params['show'] # this does not appear written to .strm files...?
						except: tvshowtitle = None
					if not tvshowtitle: continue
					year, imdb, tvdb, tmdb = params['year'], params.get('imdb', ''), params.get('tvdb', ''), params.get('tmdb', '')
					items.append({'tvshowtitle': tvshowtitle, 'year': year, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb})
				except: pass
			items = [i for x, i in enumerate(items) if i not in items[x + 1:]]
			if len(items) == 0: return
		except:
			log_utils.error()
			return
		try:
			lib = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["imdbnumber", "title", "year"]}, "id": 1 }')
			# lib = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties": ["imdbnumber", "title", "year"]}, "id": 1}' % (year, str(int(year)+1), str(int(year)-1)))
			lib = jsloads(lib)['result']['tvshows']
		except:
			log_utils.error()
			return
		# if service_notification and not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo'):
		# 	control.notification(message=32553)
		try:
			control.makeFile(control.dataPath)
			dbcon = database.connect(control.libcacheFile)
			dbcur = dbcon.cursor()
			dbcur.execute('''CREATE TABLE IF NOT EXISTS tvshows (id TEXT, items TEXT, UNIQUE(id));''')
			dbcur.connection.commit()
			from resources.lib.menus import seasons as seasonsX
			from resources.lib.menus import episodes as episodesX
		except:
			log_utils.error()
			try: dbcur.close() ; dbcon.close()
			except: pass
			return
		files_added = 0
		# __init__ doesn't get called from services so self.date never gets updated and new episodes are not added to the library
		self.date_time = datetime.now()
		if control.setting('library.importdelay') != 'true': self.date = self.date_time.strftime('%Y%m%d')
		else: self.date = (self.date_time - timedelta(hours=24)).strftime('%Y%m%d')
		for item in items:
			it = None
			if control.monitor.abortRequested():
				try: dbcur.close() ; dbcon.close()
				except: pass
				return sysexit()
			try:
				fetch = dbcur.execute('''SELECT * FROM tvshows WHERE id=?''', (item['tvdb'],)).fetchone()
				if fetch: it = eval(fetch[1])
			except: log_utils.error()
			try:
				if it: raise Exception()
				seasons = seasonsX.Seasons().tmdb_list(item['tvshowtitle'], item['imdb'], item['tmdb'], item['tvdb'], art=None) # fetch fresh meta (uncached)
				if not seasons: continue
				status = seasons[0]['status'].lower()
				it = []
				for season in seasons:
					episodes = episodesX.Episodes().tmdb_list(item['tvshowtitle'], item['imdb'], item['tmdb'], item['tvdb'], meta=season, season=season['season']) # fetch fresh meta (uncached)
					it += [{'tvshowtitle': i['tvshowtitle'], 'status': status, 'title': i['title'], 'year': i['year'], 'imdb': i['imdb'], 'tmdb': i['tmdb'], 'tvdb': i['tvdb'], 'season': i['season'], 'episode': i['episode'], 'premiered': i['premiered']} for i in episodes]
					# it += [{'tvshowtitle': i['tvshowtitle'], 'status': status, 'title': i['title'], 'year': i['year'], 'imdb': i['imdb'], 'tmdb': i['tmdb'], 'tvdb': i['tvdb'], 'season': i['season'], 'episode': i['episode'], 'premiered': i['premiered'], 'aliases': i['aliases'], 'country_codes': i['country_codes']} for i in episodes]
				# if not status or any(value in status for value in ('continuing', 'returning series')): raise Exception() # only write db entry for completed(Ended) shows
				if status == 'ended':
					dbcur.execute('''INSERT INTO tvshows Values (?, ?)''', (item['tvdb'], repr(it)))
					dbcur.connection.commit()
			except: log_utils.error()
			try:
				id = [item['imdb'], item['tvdb']]
				if item['tmdb']: id += [item['tmdb']]
				ep = [x['title'] for x in lib if str(x['imdbnumber']) in id or (x['title'] == item['tvshowtitle'] and str(x['year']) == item['year'])][0]
				ep = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"filter":{"and": [{"field": "tvshow", "operator": "is", "value": "%s"}]}, "properties": ["season", "episode"]}, "id": 1}' % ep)
				ep = jsloads(ep).get('result', {}).get('episodes', {})
				ep = [{'season': int(i['season']), 'episode': int(i['episode'])} for i in ep]
				ep = sorted(ep, key = lambda x: (x['season'], x['episode']))[-1]
				num = [x for x,y in enumerate(it) if str(y['season']) == str(ep['season']) and str(y['episode']) == str(ep['episode'])][-1]
				it = [y for x,y in enumerate(it) if x > num]
				if len(it) == 0: continue
			except: continue
			for i in it:
				if control.monitor.abortRequested(): return sysexit()
				try:
					if str(i.get('season')) == '0' and self.include_special == 'false': continue
					premiered = i.get('premiered', '') if i.get('premiered') else ''
					if premiered == None or premiered == '':
						if self.include_unknown == 'false': continue
					elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub(r'[^0-9]', '', str(self.date))): continue
					libtvshows().strmFile(i)
					files_added += 1
					if service_notification and general_notification: control.notification(title=item['tvshowtitle'], message=32678)
				except: log_utils.error()
		try: dbcur.close() ; dbcon.close()
		except: pass
		#if files_added == 0 and service_notification: control.notification(message=32109)
		if self.library_update == 'true' and not control.condVisibility('Library.IsScanningVideo') and files_added > 0:
			if contains:
				if service_notification and general_notification: control.notification(message=32554)
				control.sleep(10000)
				control.execute('UpdateLibrary(video)')
			elif service_notification and general_notification: control.notification(message=32103)