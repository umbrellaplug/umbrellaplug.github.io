# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from sys import exit as sysexit
from urllib.parse import quote_plus
from resources.lib.modules import control
from resources.lib.modules.trakt import getTraktCredentialsInfo, getTraktIndicatorsInfo
from resources.lib.modules import simkl
from resources.lib.modules import mdblist
from resources.lib.modules import customtrakt
from resources.lib.modules import floppy
from resources.lib.modules import scrob
from resources.lib.modules.tmdb4 import getTMDbV4CredentialsInfo
from resources.lib.modules import favourites
from json import loads as jsloads

getLS = control.lang
getSetting = control.setting
decades = ['1930-1939', '1940-1949','1950-1959', '1960-1969', '1970-1979', '1980-1989', '1990-1999', '2000-2009', '2010-2019','2020-2029']


class Navigator:
	def __init__(self, lightweight=False):
		self.artPath = control.artPath()
		self.iconLogos = getSetting('icon.logos') != 'Traditional'
		self.indexLabels = getSetting('index.labels') == 'true'
		self.traktCredentials = getTraktCredentialsInfo()
		self.simklCredentials = simkl.getSimKLCredentialsInfo()
		self.mdblistCredentials = mdblist.getMDBListCredentialsInfo()
		self.customCredentials = customtrakt.getCustomCredentialsInfo()
		self.floppyCredentials = floppy.getFloppyCredentialsInfo()
		self.scrobCredentials = scrob.getScrobCredentialsInfo()
		self.traktIndicators = getTraktIndicatorsInfo()
		self.simklIndicators = simkl.getSimKLIndicatorsInfo()
		self.mdblistIndicators = mdblist.getMDBListIndicatorsInfo()
		self.customIndicators = customtrakt.getCustomIndicatorsInfo()
		self.floppyIndicators = floppy.getFloppyIndicatorsInfo()
		self.scrobIndicators = scrob.getScrobIndicatorsInfo()
		self.tmdbCredentials = getTMDbV4CredentialsInfo()
		self.simkltoken = getSetting('simkltoken') != ''
		self.alldebridCredentials = getSetting('alldebridtoken') != ''
		self.easynewsCredentials = getSetting('easynews.user') != ''
		self.offcloudCredentials = getSetting('offcloudtoken') != ''
		self.torboxCredentials = getSetting('torboxtoken') != ''
		self.premiumizeCredentials = getSetting('premiumizetoken') != ''
		self.realdebridCredentials = getSetting('realdebridtoken') != ''
		self.tmdbSessionID = getSetting('tmdb.sessionid') != ''
		self.reuselanguageinv = getSetting('reuse.languageinvoker') == 'true'
		self.highlight_color = getSetting('highlight.color')
		self.useContainerTitles = getSetting('enable.containerTitles') == 'true'
		if lightweight:
			self.hasLibMovies = False
			self.favoriteMovie = False
			self.favoriteTVShows = False
			self.favoriteEpisodes = False
			return
		self.hasLibMovies = len(jsloads(control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": { "limits": { "start" : 0, "end": 1 }, "properties" : ["title", "genre", "uniqueid", "art", "rating", "thumbnail", "playcount", "file"] }, "id": "1"}'))['result']['movies']) > 0
		self.favoriteMovie = favourites.checkForFavourites(content='movies')
		self.favoriteTVShows = favourites.checkForFavourites(content='tvshows')
		self.favoriteEpisodes = favourites.checkForFavourites(content='episode')

	def root(self):
		from resources.lib.database import menu as menu_db
		menu_db.initialize('root')
		rendered = 0
		for item in menu_db.get_menu_items('root'):
			if not self._eval_item_condition(item['item_id']):
				continue
			raw_label = item['label']
			if not self.indexLabels and item.get('alt_label'):
				raw_label = item['alt_label']
			label = getLS(int(raw_label)) if raw_label.isdigit() else raw_label
			icon_file = item['icon'] if self.iconLogos else item['poster']
			action = '%s&folderName=%s' % (item['action'], quote_plus(label)) if item['is_folder'] else item['action']
			self.addDirectoryItem(label, action, icon_file, icon_file,
				isFolder=bool(item['is_folder']), isAction=bool(item['is_action']),
				multi_context=[('Edit Main Menu', 'mainMenuEditor&menu_name=root')])
			rendered += 1
		if rendered == 0:
			tools_label = getLS(32008)
			self.addDirectoryItem(tools_label, 'tools_toolNavigator&folderName=%s' % quote_plus(tools_label),
				'tools.png', 'tools.png', multi_context=[('Edit Main Menu', 'mainMenuEditor&menu_name=root')])
		self.endDirectory()

	def _eval_item_condition(self, item_id):
		if item_id == 'favourites':
			return bool(favourites.checkForFavourites())
		if item_id == 'downloads':
			if getSetting('downloads') != 'true':
				return False
			return (len(control.listDir(getSetting('movie.download.path'))[0]) > 0 or
				len(control.listDir(getSetting('tv.download.path'))[0]) > 0)
		return True

	def _eval_condition_key(self, key, lite=False):
		if key == 'not_lite':                return not lite
		if key == 'simkl_token':             return bool(self.simkltoken)
		if key == 'simkl_credentials':       return bool(self.simklCredentials)
		if key == 'simkl_with_indicators':   return bool(self.simklCredentials and (self.simklIndicators or getSetting('simkl.markwatched') == 'true'))
		if key == 'trakt_credentials':       return bool(self.traktCredentials)
		if key == 'trakt_with_indicators':   return bool(self.traktCredentials and (self.traktIndicators or getSetting('trakt.markwatched') == 'true'))
		if key == 'mdblist_token':           return bool(getSetting('mdblist.token'))
		if key == 'mdblist_credentials':     return bool(self.mdblistCredentials)
		if key == 'mdblist_with_indicators': return bool(self.mdblistCredentials and (self.mdblistIndicators or getSetting('mdblist.markwatched') == 'true'))
		if key == 'custom_token':            return bool(getSetting('dev.enable.custom') == 'true' and getSetting('custom.user.token'))
		if key == 'custom_credentials':      return bool(self.customCredentials)
		if key == 'custom_with_indicators':  return bool(self.customCredentials and (self.customIndicators or getSetting('custom.markwatched') == 'true'))
		if key == 'floppy_token':          return bool(getSetting('floppy.token'))
		if key == 'floppy_credentials':    return bool(self.floppyCredentials)
		if key == 'floppy_with_indicators':return bool(self.floppyCredentials and (self.floppyIndicators or getSetting('floppy.markwatched') == 'true'))
		if key == 'scrob_apikey':          return bool(getSetting('scrob.apikey'))
		if key == 'scrob_credentials':     return bool(self.scrobCredentials)
		if key == 'scrob_with_indicators': return bool(self.scrobCredentials and (self.scrobIndicators or getSetting('scrob.markwatched') == 'true'))
		if key == 'tmdb_v4_token':           return bool(getSetting('tmdb.v4.accesstoken'))
		if key == 'has_lib_movies':          return bool(self.hasLibMovies)
		if key == 'favorite_movie':          return bool(self.favoriteMovie)
		if key == 'favorite_tvshows':        return bool(self.favoriteTVShows)
		if key == 'favorite_episodes':       return bool(self.favoriteEpisodes)
		if key == 'local_scrobble':          return getSetting('indicators.alt') == '0' and getSetting('scrobble.source') == '0'
		return True

	def _renderDbMenu(self, menu_name, editor_action, editor_label, lite=False, folderName=''):
		from resources.lib.database import menu as menu_db
		menu_db.initialize(menu_name)
		editor_label = self._MENU_EDITOR_LABELS.get(menu_name, editor_label)
		rendered = 0
		for item in menu_db.get_menu_items(menu_name):
			ck = item.get('condition_key')
			if ck and not self._eval_condition_key(ck, lite=lite):
				continue
			raw_label = item['label']
			if not self.indexLabels and item.get('alt_label'):
				raw_label = item['alt_label']
			label = getLS(int(raw_label)) if raw_label.isdigit() else raw_label
			if item['item_id'].startswith(('mytv_custom_', 'mymv_custom_')):
				from resources.lib.modules import customtrakt
				custom_name = customtrakt.getCustomServiceName()
				if custom_name != 'Custom':
					label = label.replace('Custom', custom_name)
			icon_file = item['icon'] if self.iconLogos else item['poster']
			action = '%s&folderName=%s' % (item['action'], quote_plus(label)) if item['is_folder'] else item['action']
			self.addDirectoryItem(label, action, icon_file, icon_file,
				isFolder=bool(item['is_folder']), isAction=bool(item['is_action']),
				queue=bool(item['queue']),
				multi_context=[(editor_label, '%s&menu_name=%s' % (editor_action, menu_name))])
			rendered += 1
		if rendered == 0:
			self.addDirectoryItem(editor_label, '%s&menu_name=%s' % (editor_action, menu_name),
				'tools.png', 'tools.png', isFolder=False, isAction=True)
		if self.useContainerTitles: control.setContainerName(folderName)
		self.endDirectory()

	_MENU_EDITOR_LABELS = {
		'root':      'Edit Main Menu',
		'movies':    'Edit Movies Menu',
		'mymovies':  'Edit My Movies Menu',
		'tvshows':   'Edit TV Shows Menu',
		'mytvshows': 'Edit My TV Shows Menu',
		'mymovies_mdblist':  'Edit My Movies: MDBList',
		'mymovies_custom':   'Edit My Movies: Custom',
		'mymovies_tmdb':     'Edit My Movies: TMDb',
		'mymovies_simkl':    'Edit My Movies: Simkl',
		'mymovies_trakt':    'Edit My Movies: Trakt',
		'mymovies_floppy': 'Edit My Movies: Floppy',
		'mymovies_scrob': 'Edit My Movies: Scrob',
		'mymovies_local': 'Edit My Movies: Local',
		'mytvshows_mdblist':  'Edit My TV Shows: MDBList',
		'mytvshows_custom':   'Edit My TV Shows: Custom',
		'mytvshows_tmdb':     'Edit My TV Shows: TMDb',
		'mytvshows_simkl':    'Edit My TV Shows: Simkl',
		'mytvshows_trakt':    'Edit My TV Shows: Trakt',
		'mytvshows_floppy': 'Edit My TV Shows: Floppy',
		'mytvshows_scrob': 'Edit My TV Shows: Scrob',
		'mytvshows_local': 'Edit My TV Shows: Local',
	}

	def mainMenuEditor(self, menu_name='root'):
		from resources.lib.database import menu as menu_db
		menu_db.initialize(menu_name)
		heading = self._MENU_EDITOR_LABELS.get(menu_name, 'Edit Menu')
		while True:
			all_items = menu_db.get_all_menu_items(menu_name)
			display = []
			for it in all_items:
				lbl = getLS(int(it['label'])) if it['label'].isdigit() else it['label']
				dot = '[COLOR lime]●[/COLOR] ' if it['enabled'] else '[COLOR red]○[/COLOR] '
				display.append(dot + lbl)
			display.append('[COLOR yellow]Add Custom Item...[/COLOR]')
			display.append('[COLOR red]Reset to Defaults[/COLOR]')
			display.append('Done')
			sel = control.selectDialog(display, heading=heading)
			if sel < 0:
				break
			n = len(all_items)
			if sel == n:
				self._mainMenuAddCustomItem(menu_name, menu_db)
			elif sel == n + 1:
				if control.yesnoDialog('Reset the main menu to its default items and order?', '', ''):
					menu_db.reset_to_defaults(menu_name)
			elif sel == n + 2:
				break
			else:
				item = all_items[sel]
				item_lbl = getLS(int(item['label'])) if item['label'].isdigit() else item['label']
				sub_options = ['Disable' if item['enabled'] else 'Enable', 'Re-order']
				if item['is_custom']:
					sub_options += ['Edit', 'Delete']
				sub_options.append('Back')
				sub_sel = control.selectDialog(sub_options, heading=item_lbl)
				if sub_sel < 0:
					continue
				chosen = sub_options[sub_sel]
				if chosen in ('Enable', 'Disable'):
					menu_db.toggle_item(menu_name, item['item_id'])
				elif chosen == 'Re-order':
					self.mainMenuReorderEditor(menu_name, preselected_id=item['item_id'])
				elif chosen == 'Edit':
					self._mainMenuEditCustomItem(menu_name, item, menu_db)
				elif chosen == 'Delete':
					if control.yesnoDialog('Delete "%s"?' % item_lbl, '', ''):
						menu_db.delete_item(menu_name, item['item_id'])
		control.refresh()

	def _mainMenuAddCustomItem(self, menu_name, menu_db):
		label = control.dialog.input('Enter Label')
		if not label:
			return
		url = self._browseForPath('Select Path')
		if not url:
			return
		action, is_folder, is_action = self._parseCustomUrl(url)
		icon = self._browseForIcon(self.artPath) or 'DefaultFolder.png'
		menu_db.add_custom_item(menu_name, label, action, icon, icon, is_folder=is_folder, is_action=is_action)

	@staticmethod
	def _parseCustomUrl(url):
		import re
		if '://' in url:
			return url, 1, 0
		if re.match(r'^[A-Za-z]\w*\(.*\)$', url):
			return 'runBuiltin&cmd=%s' % url, 0, 1
		return url, 1, 1

	@staticmethod
	def _browseForPath(heading='Select Path', default_for_manual=''):
		TOP = [
			('Add-ons',             'addons://sources/video/'),
			('Video Library',       'library://video/'),
			('My Shortcut Folders', '__shortcut_folders__'),
			('Kodi Commands',       '__kodi_commands__'),
			('Enter Manually',      '__manual__'),
		]
		sel = control.selectDialog([t[0] for t in TOP], heading=heading)
		if sel < 0:
			return None
		_, start = TOP[sel]
		if start == '__manual__':
			result = control.dialog.input(heading, defaultt=default_for_manual)
			return result.strip() if result else None
		if start == '__kodi_commands__':
			return Navigator._browseKodiCommands()
		if start == '__shortcut_folders__':
			return Navigator._browseShortcutFolders()
		return Navigator._browseDirectory(start, [])

	@staticmethod
	def _browseShortcutFolders():
		from resources.lib.database import menu as menu_db
		menu_db.initialize('root')
		folders = menu_db.get_custom_folders()
		if not folders:
			control.dialog.ok('My Shortcut Folders', 'No shortcut folders found. Create one via Tools > Shortcut Folder Manager.')
			return None
		sel = control.selectDialog([f['folder_name'] for f in folders], heading='My Shortcut Folders')
		if sel < 0:
			return None
		return 'customFolderNavigator&folder_id=%s' % folders[sel]['folder_id']

	@staticmethod
	def _browseDirectory(path, history):
		import json
		rpc = json.loads(control.jsonrpc(json.dumps({
			'jsonrpc': '2.0', 'method': 'Files.GetDirectory',
			'params': {'directory': path, 'media': 'files', 'properties': ['title']},
			'id': 1
		})))
		files = rpc.get('result', {}).get('files', [])
		if not files:
			return path.rstrip('/')
		display = []
		if history:
			display.append('[B]<< Back[/B]')
		display.append('[COLOR lime]>> Select This Location[/COLOR]')
		display += [f['label'] for f in files]
		sel = control.selectDialog(display, heading='Select Path')
		if sel < 0:
			return None
		back_offset = 1 if history else 0
		if history and sel == 0:
			return Navigator._browseDirectory(history[-1], history[:-1])
		if sel == back_offset:
			return path.rstrip('/')
		item = files[sel - back_offset - 1]
		if item.get('filetype') == 'directory':
			return Navigator._browseDirectory(item['file'], history + [path])
		return item.get('file', path).rstrip('/')

	@staticmethod
	def _browseKodiCommands():
		COMMANDS = [
			('Home',                 'ActivateWindow(Home)'),
			('Movies Library',       'ActivateWindow(VideoLibrary,Movies)'),
			('TV Shows Library',     'ActivateWindow(VideoLibrary,TvShows)'),
			('Music Library',        'ActivateWindow(MusicLibrary)'),
			('Add-ons Browser',      'ActivateWindow(AddonBrowser)'),
			('File Manager',         'ActivateWindow(FileManager)'),
			('Settings',             'ActivateWindow(Settings)'),
			('Favourites',           'ActivateWindow(Favourites)'),
			('Shutdown Menu',        'ActivateWindow(ShutdownMenu)'),
			('Suspend',              'Suspend()'),
			('Reboot',               'Reboot()'),
			('Quit Kodi',            'Quit()'),
			('Update Video Library', 'UpdateLibrary(video)'),
			('Update Music Library', 'UpdateLibrary(music)'),
			('Toggle Debug Logging', 'ToggleDebug()'),
		]
		sel = control.selectDialog([c[0] for c in COMMANDS], heading='Kodi Commands')
		return COMMANDS[sel][1] if 0 <= sel < len(COMMANDS) else None

	@staticmethod
	def _browseForIcon(art_path):
		import xbmcgui
		_SKIN = 'special://skin/'
		choice = control.selectDialog(['Browse for Image', 'Enter URL', 'Umbrella Icons'], heading='Select Icon')
		if choice < 0:
			return None
		if choice == 0:
			result = xbmcgui.Dialog().browse(2, 'Select Icon', 'files', '.png|.jpg|.gif', False, False, _SKIN)
			return result if result and result != _SKIN else None
		if choice == 1:
			result = control.dialog.input('Enter Icon URL or Path')
			return result.strip() if result else None
		try:
			icon_files = sorted([f for f in control.listDir(art_path)[1] if f.lower().endswith('.png')])
			list_items = []
			for f in icon_files:
				li = xbmcgui.ListItem(label=f)
				icon_path = control.joinPath(art_path, f)
				li.setArt({'icon': icon_path, 'thumb': icon_path})
				list_items.append(li)
			icon_sel = control.selectDialog(list_items, 'Select Icon', useDetails=True)
			if 0 <= icon_sel < len(icon_files):
				return control.joinPath(art_path, icon_files[icon_sel])
		except Exception:
			pass
		return None

	def _mainMenuEditCustomItem(self, menu_name, item, menu_db):
		item_lbl = item['label']
		while True:
			sub = control.selectDialog(['Edit Name', 'Edit Path', 'Edit Icon', 'Back'], heading='Edit: %s' % item_lbl)
			if sub < 0 or sub == 3:
				break
			if sub == 0:
				new_label = control.dialog.input('Edit Label', defaultt=item_lbl)
				if new_label and new_label != item_lbl:
					menu_db.update_custom_item(menu_name, item['item_id'], label=new_label)
					item_lbl = new_label
			elif sub == 1:
				stored = item['action']
				display_url = stored[len('runBuiltin&cmd='):] if stored.startswith('runBuiltin&cmd=') else stored
				new_url = self._browseForPath('Edit Path', default_for_manual=display_url)
				if new_url and new_url != display_url:
					new_action, new_is_folder, new_is_action = self._parseCustomUrl(new_url)
					menu_db.update_custom_item(menu_name, item['item_id'],
						action=new_action, is_folder=new_is_folder, is_action=new_is_action)
					item['action'] = new_action
					item['is_folder'] = new_is_folder
					item['is_action'] = new_is_action
			elif sub == 2:
				new_icon = self._browseForIcon(self.artPath)
				if new_icon:
					menu_db.update_custom_item(menu_name, item['item_id'], icon=new_icon, poster=new_icon)

	def mainMenuReorderEditor(self, menu_name='root', preselected_id=None):
		from resources.lib.database import menu as menu_db
		all_enabled = menu_db.get_menu_items(menu_name)
		# Only offer items that actually render (pass condition_key) for reordering,
		# otherwise moving an item relative to a hidden one produces no visible change
		# in the real menu, which looks like the reorder didn't stick.
		enabled = [it for it in all_enabled if not (it.get('condition_key') and not self._eval_condition_key(it['condition_key']))]
		if preselected_id is not None:
			sel = next((i for i, it in enumerate(enabled) if it['item_id'] == preselected_id), -1)
			if sel < 0:
				control.refresh()
				return
		else:
			display = [getLS(int(it['label'])) if it['label'].isdigit() else it['label'] for it in enabled]
			sel = control.selectDialog(display, heading='Re-order: Select item to move')
			if sel < 0:
				control.refresh()
				return
		item = enabled[sel]
		lbl = getLS(int(item['label'])) if item['label'].isdigit() else item['label']
		pos_display = []
		for idx, it in enumerate(enabled):
			it_lbl = getLS(int(it['label'])) if it['label'].isdigit() else it['label']
			marker = '  <<' if it['item_id'] == item['item_id'] else ''
			pos_display.append('%d.  %s%s' % (idx + 1, it_lbl, marker))
		target = control.selectDialog(pos_display, heading='Move "%s" to:' % lbl, preselect=sel)
		if target >= 0 and target != sel:
			new_visible_ids = [it['item_id'] for it in enabled]
			new_visible_ids.remove(item['item_id'])
			new_visible_ids.insert(target, item['item_id'])
			visible_id_set = set(new_visible_ids)
			new_visible_iter = iter(new_visible_ids)
			# Re-weave the reordered visible ids back into the full enabled list so
			# hidden (condition_key-filtered) items keep their existing relative position.
			current_ids = [next(new_visible_iter) if it['item_id'] in visible_id_set else it['item_id'] for it in all_enabled]
			menu_db.reorder_enabled_items(menu_name, current_ids)
		control.refresh()

	def movies(self, lite=False, folderName=''):
		self._renderDbMenu('movies', 'movieNavigatorEditor', 'Edit Movies Menu', lite=lite, folderName=folderName)

	def mymovies(self, lite=False, folderName=''):
		self.accountCheck()
		self._renderDbMenu('mymovies', 'myMoviesNavigatorEditor', 'Edit My Movies Menu', lite=lite, folderName=folderName)

	def mymovies_mdblist(self, folderName=''):
		self._renderDbMenu('mymovies_mdblist', 'myMoviesNavigatorEditor', 'Edit My Movies Menu', folderName=folderName)

	def mymovies_custom(self, folderName=''):
		self._renderDbMenu('mymovies_custom', 'myMoviesNavigatorEditor', 'Edit My Movies Menu', folderName=folderName)

	def mymovies_tmdb(self, folderName=''):
		self._renderDbMenu('mymovies_tmdb', 'myMoviesNavigatorEditor', 'Edit My Movies Menu', folderName=folderName)

	def mymovies_simkl(self, folderName=''):
		self._renderDbMenu('mymovies_simkl', 'myMoviesNavigatorEditor', 'Edit My Movies Menu', folderName=folderName)

	def mymovies_trakt(self, folderName=''):
		self._renderDbMenu('mymovies_trakt', 'myMoviesNavigatorEditor', 'Edit My Movies Menu', folderName=folderName)

	def mymovies_floppy(self, folderName=''):
		self._renderDbMenu('mymovies_floppy', 'myMoviesNavigatorEditor', 'Edit My Movies Menu', folderName=folderName)

	def mymovies_scrob(self, folderName=''):
		self._renderDbMenu('mymovies_scrob', 'myMoviesNavigatorEditor', 'Edit My Movies Menu', folderName=folderName)

	def mymovies_local(self, folderName=''):
		self._renderDbMenu('mymovies_local', 'myMoviesNavigatorEditor', 'Edit My Movies Menu', folderName=folderName)

	def tvshows(self, lite=False, folderName=''):
		self._renderDbMenu('tvshows', 'tvNavigatorEditor', 'Edit TV Shows Menu', lite=lite, folderName=folderName)

	def mytvshows(self, lite=False, folderName=''):
		self.accountCheck()
		self._renderDbMenu('mytvshows', 'myTVShowsNavigatorEditor', 'Edit My TV Shows Menu', lite=lite, folderName=folderName)

	def mytvshows_mdblist(self, folderName=''):
		self._renderDbMenu('mytvshows_mdblist', 'myTVShowsNavigatorEditor', 'Edit My TV Shows Menu', folderName=folderName)

	def mytvshows_custom(self, folderName=''):
		self._renderDbMenu('mytvshows_custom', 'myTVShowsNavigatorEditor', 'Edit My TV Shows Menu', folderName=folderName)

	def mytvshows_tmdb(self, folderName=''):
		self._renderDbMenu('mytvshows_tmdb', 'myTVShowsNavigatorEditor', 'Edit My TV Shows Menu', folderName=folderName)

	def mytvshows_simkl(self, folderName=''):
		self._renderDbMenu('mytvshows_simkl', 'myTVShowsNavigatorEditor', 'Edit My TV Shows Menu', folderName=folderName)

	def mytvshows_trakt(self, folderName=''):
		self._renderDbMenu('mytvshows_trakt', 'myTVShowsNavigatorEditor', 'Edit My TV Shows Menu', folderName=folderName)

	def mytvshows_floppy(self, folderName=''):
		self._renderDbMenu('mytvshows_floppy', 'myTVShowsNavigatorEditor', 'Edit My TV Shows Menu', folderName=folderName)

	def mytvshows_scrob(self, folderName=''):
		self._renderDbMenu('mytvshows_scrob', 'myTVShowsNavigatorEditor', 'Edit My TV Shows Menu', folderName=folderName)

	def mytvshows_local(self, folderName=''):
		self._renderDbMenu('mytvshows_local', 'myTVShowsNavigatorEditor', 'Edit My TV Shows Menu', folderName=folderName)

	def anime(self, lite=False, folderName=''):
		self.addDirectoryItem(32001, 'anime_Movies&url=anime&folderName=%s' % quote_plus(getLS(32001)), 'movies.png', 'DefaultMovies.png')
		self.addDirectoryItem(32002, 'anime_TVshows&url=anime&folderName=%s' % quote_plus(getLS(32002)), 'tvshows.png', 'DefaultTVShows.png')
		if self.useContainerTitles: control.setContainerName(folderName)
		self.endDirectory()

	def trakt_genre(self, mediatype='', genre='',url='',lite=False, folderName=''):
		genre = str(genre)
		mediatype = str(mediatype)
		if mediatype == 'TVShows':
			displayMediaType = 'TV Shows'
		else:
			displayMediaType = 'Movies'
		self.addDirectoryItem(getLS(40494) % (genre, displayMediaType), 'trakt_genre&listtype=trending&mediatype=%s&genre=%s&url=%s&folderName=%s' % (mediatype, genre, url, quote_plus(getLS(40494) % (genre, displayMediaType))), 'trakt.png', 'trakt.png', queue=True)
		self.addDirectoryItem(getLS(40495) % (genre, displayMediaType), 'trakt_genre&listtype=popular&mediatype=%s&genre=%s&url=%s&folderName=%s' % (mediatype, genre, url, quote_plus(getLS(40495) % (genre, displayMediaType))), 'trakt.png', 'trakt.png', queue=True)
		self.addDirectoryItem(getLS(40496) % (genre, displayMediaType), 'trakt_genre&listtype=mostplayed&mediatype=%s&genre=%s&url=%s&folderName=%s' % (mediatype, genre, url, quote_plus(getLS(40496) % (genre, displayMediaType))), 'trakt.png', 'trakt.png', queue=True)
		self.addDirectoryItem(getLS(40497) % (genre, displayMediaType), 'trakt_genre&listtype=mostwatched&mediatype=%s&genre=%s&url=%s&folderName=%s' % (mediatype, genre, url, quote_plus(getLS(40497) % (genre, displayMediaType))), 'trakt.png', 'trakt.png', queue=True)
		self.addDirectoryItem(getLS(40498) % (genre, displayMediaType), 'trakt_genre&listtype=anticipated&mediatype=%s&genre=%s&url=%s&folderName=%s' % (mediatype, genre, url, quote_plus(getLS(40498) % (genre, displayMediaType))), 'trakt.png', 'trakt.png', queue=True)
		self.addDirectoryItem(getLS(40499) % (genre, displayMediaType), 'trakt_genre&listtype=decades&mediatype=%s&genre=%s&url=%s&folderName=%s' % (mediatype, genre, url, quote_plus(getLS(40498) % (genre, displayMediaType))), 'trakt.png', 'trakt.png', queue=True)
		if self.useContainerTitles: control.setContainerName(folderName)
		self.endDirectory()

	def trakt_decades(self, mediatype='', genre='',url='',lite=False, folderName=''):
		mediatype = str(mediatype)
		if mediatype == 'TVShows':
			displayMediaType = 'TV Shows'
		else:
			displayMediaType = 'Movies'
		for i in decades:
			self.addDirectoryItem(getLS(40500) % (str(i), genre, displayMediaType), 'trakt_genre_decades&decades=%s&mediatype=%s&genre=%s&url=%s&folderName=%s' % (str(i), mediatype, genre, url, quote_plus(getLS(40500) % (str(i), genre, displayMediaType))), 'trakt.png', 'trakt.png', queue=True)
		if self.useContainerTitles: control.setContainerName(folderName)
		self.endDirectory()

	def trakt_genre_decade(self, mediatype='', decade='', genre='',url='',lite=False, folderName=''):
		genre = str(genre)
		mediatype = str(mediatype)
		if mediatype == 'TVShows':
			displayMediaType = 'TV Shows'
		else:
			displayMediaType = 'Movies'
		self.addDirectoryItem(getLS(40494) % (genre, displayMediaType)+' ('+decade+')', 'trakt_genre_decade&listtype=trending&decades=%s&mediatype=%s&genre=%s&url=%s&folderName=%s' % (str(decade), mediatype, genre, url, quote_plus(getLS(40494) % (genre, displayMediaType))), 'trakt.png', 'trakt.png', queue=True)
		self.addDirectoryItem(getLS(40495) % (genre, displayMediaType)+' ('+decade+')', 'trakt_genre_decade&listtype=popular&decades=%s&mediatype=%s&genre=%s&url=%s&folderName=%s' % (str(decade), mediatype, genre, url, quote_plus(getLS(40495) % (genre, displayMediaType))), 'trakt.png', 'trakt.png', queue=True)
		self.addDirectoryItem(getLS(40496) % (genre, displayMediaType)+' ('+decade+')', 'trakt_genre_decade&listtype=mostplayed&decades=%s&mediatype=%s&genre=%s&url=%s&folderName=%s' % (str(decade), mediatype, genre, url, quote_plus(getLS(40496) % (genre, displayMediaType))), 'trakt.png', 'trakt.png', queue=True)
		self.addDirectoryItem(getLS(40497) % (genre, displayMediaType)+' ('+decade+')', 'trakt_genre_decade&listtype=mostwatched&decades=%s&mediatype=%s&genre=%s&url=%s&folderName=%s' % (str(decade), mediatype, genre, url, quote_plus(getLS(40497) % (genre, displayMediaType))), 'trakt.png', 'trakt.png', queue=True)
		if self.useContainerTitles: control.setContainerName(folderName)
		self.endDirectory()

	def traktLists(self, lite=False, folderName=''):
		self.addDirectoryItem(getLS(32001)+' - '+getLS(32417), 'movies_PublicLists&url=trakt_popularLists&folderName=%s' % quote_plus(getLS(32417)), 'trakt.png' if self.iconLogos else 'movies.png', 'DefaultMovies.png')
		self.addDirectoryItem(getLS(32001)+' - '+getLS(32418), 'movies_PublicLists&url=trakt_trendingLists&folderName=%s' % quote_plus(getLS(32418)), 'trakt.png' if self.iconLogos else 'movies.png', 'DefaultMovies.png')
		self.addDirectoryItem(getLS(32001)+' - '+getLS(32419), 'movies_SearchLists&media_type=movies', 'trakt.png' if self.iconLogos else 'movies.png', 'DefaultMovies.png', isFolder=False)
		self.addDirectoryItem('My Liked Movie Lists', 'movies_LikedLists&folderName=My Liked Movie Lists', 'trakt.png', 'trakt.png', queue=True)
		self.addDirectoryItem(getLS(32002)+ ' - '+getLS(32417), 'tv_PublicLists&url=trakt_popularLists&folderName=%s' % quote_plus(getLS(32417)), 'trakt.png' if self.iconLogos else 'tvshows.png', 'DefaultMovies.png')
		self.addDirectoryItem(getLS(32002)+ ' - '+getLS(32418), 'tv_PublicLists&url=trakt_trendingLists&folderName=%s' % quote_plus(getLS(32418)), 'trakt.png' if self.iconLogos else 'tvshows.png', 'DefaultMovies.png')
		self.addDirectoryItem(getLS(32002)+ ' - '+getLS(32419), 'tv_SearchLists&media_type=shows', 'trakt.png' if self.iconLogos else 'tvshows.png', 'DefaultMovies.png', isFolder=False)	
		self.addDirectoryItem('My Liked TV Show Lists', 'shows_LikedLists&folderName=My Liked TV Show Lists', 'trakt.png', 'trakt.png', queue=True)
		self.endDirectory()

	def traktSearchLists(self, media_type):
		k = control.keyboard('', getLS(32010))
		k.doModal()
		q = k.getText() if k.isConfirmed() else None
		if not q: return control.closeAll()
		page_limit = getSetting('page.item.limit')
		url = 'https://api.trakt.tv/search/list?limit=%s&page=1&query=' % page_limit + quote_plus(q)
		control.closeAll()
		if media_type == 'movies': control.execute('ActivateWindow(Videos,plugin://plugin.video.umbrella/?action=movies_PublicLists&url=%s,return)' % (quote_plus(url)))
		else: control.execute('ActivateWindow(Videos,plugin://plugin.video.umbrella/?action=tv_PublicLists&url=%s,return)' % (quote_plus(url)))

	def traktSearchListsTerm(self, search, media_type):
		if search:
			page_limit = getSetting('page.item.limit')
			url = 'https://api.trakt.tv/search/list?limit=%s&page=1&query=' % page_limit + quote_plus(search)
			if media_type == 'movies':
				from resources.lib.menus import movies
				movies.Movies().getTraktPublicLists(url, folderName='')
			else:
				from resources.lib.menus import tvshows
				tvshows.TVshows().getTraktPublicLists(url, folderName='')

	def customFolder(self, folder_id, folderName=''):
		from resources.lib.database import menu as menu_db
		menu_db.initialize(folder_id)
		self._renderDbMenu(folder_id, 'customFolderEditor', 'Edit Folder', folderName=folderName)

	def customFolderManager(self):
		from resources.lib.database import menu as menu_db
		menu_db.initialize('root')
		addon_url = 'plugin://plugin.video.umbrella/?action=customFolderNavigator&folder_id='
		while True:
			folders = menu_db.get_custom_folders()
			display = ['[COLOR yellow]+ Create New Folder...[/COLOR]']
			display += [f['folder_name'] for f in folders]
			display.append('Done')
			sel = control.selectDialog(display, heading='Shortcut Folder Manager')
			if sel < 0 or sel == len(display) - 1:
				break
			if sel == 0:
				name = control.dialog.input('Folder Name')
				if name:
					menu_db.create_custom_folder(name)
				continue
			folder = folders[sel - 1]
			fid = folder['folder_id']
			fname = folder['folder_name']
			widget_url = addon_url + fid
			action_str = 'customFolderNavigator&folder_id=%s' % fid
			sub = control.selectDialog(
				['Edit Items', 'Show Widget URL', 'Rename', 'Delete', 'Back'],
				heading=fname
			)
			if sub < 0 or sub == 4:
				continue
			if sub == 0:
				self.mainMenuEditor(fid)
			elif sub == 1:
				control.dialog.ok(fname,
					'[B]Widget URL:[/B]\n%s\n\n[B]Menu Item Action:[/B]\n%s' % (widget_url, action_str))
			elif sub == 2:
				new_name = control.dialog.input('Rename Folder', defaultt=fname)
				if new_name and new_name != fname:
					menu_db.rename_custom_folder(fid, new_name)
			elif sub == 3:
				if control.yesnoDialog('Delete folder "%s" and all its items?' % fname, '', ''):
					menu_db.delete_custom_folder(fid)

	def tools(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		self.addDirectoryItem(32510, 'cache_Navigator&folderName=%s' % quote_plus(getLS(40462)), 'settings.png', 'DefaultAddonService.png', isFolder=True)
		#self.addDirectoryItem(32609, 'tools_openMyAccount', 'MyAccounts.png', 'DefaultAddonService.png', isFolder=False)
		#self.addDirectoryItem(32506, 'tools_contextUmbrellaSettings', 'icon.png', 'DefaultAddonProgram.png', isFolder=False)
		#-- Providers - 
		#self.addDirectoryItem(32651, 'tools_cocoScrapersSettings', 'cocoscrapers.png', 'DefaultAddonService.png', isFolder=False)
		#-- General - 0
		self.addDirectoryItem(32043, 'tools_openSettings&query=0.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		#-- Sorting and Filtering - 3
		self.addDirectoryItem(40162, 'tools_openSettings&query=3.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		#-- Online Services - 5
		self.addDirectoryItem(40611, 'tools_openSettings&query=5.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		#-- Accounts (Debrid) - 6
		self.addDirectoryItem(32044, 'tools_openSettings&query=6.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		#-- Providers - 7
		self.addDirectoryItem(40452, 'tools_openSettings&query=7.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		#-- Accounts (Meta) - 8
		self.addDirectoryItem(40124, 'tools_openSettings&query=8.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		#self.addDirectoryItem(40559, 'tools_openSettings&query=9.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		#self.addDirectoryItem(40123, 'tools_openSettings&query=9.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem('[B]Shortcut Folder Manager[/B]', 'customFolderManager', 'tools.png', 'DefaultAddonService.png', isFolder=False, isAction=True)
		if self.simklCredentials: self.addDirectoryItem(40551, 'tools_simklToolsNavigator&folderName=%s' % quote_plus(getLS(40552)), 'tools.png', 'DefaultAddonService.png', isFolder=True)
		if self.traktCredentials: self.addDirectoryItem(35057, 'tools_traktToolsNavigator&folderName=%s' % quote_plus(getLS(40461)), 'tools.png', 'DefaultAddonService.png', isFolder=True)
		if self.mdblistCredentials: self.addDirectoryItem(40635, 'tools_mdblistToolsNavigator&folderName=%s' % quote_plus(getLS(40636)), 'tools.png', 'DefaultAddonService.png', isFolder=True)
		if self.customCredentials:
			_custom_tools_label = '%s Management Tools' % customtrakt.getCustomServiceName()
			self.addDirectoryItem('[B]%s[/B]' % _custom_tools_label, 'tools_customToolsNavigator&folderName=%s' % quote_plus(_custom_tools_label), 'tools.png', 'DefaultAddonService.png', isFolder=True)
		if self.floppyCredentials: self.addDirectoryItem('[B]Floppy Management Tools[/B]', 'tools_floppyToolsNavigator&folderName=%s' % quote_plus('Floppy Management Tools'), 'tools.png', 'DefaultAddonService.png', isFolder=True)
		if self.scrobCredentials: self.addDirectoryItem('[B]Scrob Management Tools[/B]', 'tools_scrobToolsNavigator&folderName=%s' % quote_plus('Scrob Management Tools'), 'tools.png', 'DefaultAddonService.png', isFolder=True)
		#-- Playback - 2
		self.addDirectoryItem(32045, 'tools_openSettings&query=2.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		#-- Downloads - 10
		self.addDirectoryItem(32048, 'tools_openSettings&query=10.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		#-- Subtitles - 11
		self.addDirectoryItem(32046, 'tools_openSettings&query=11.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(32556, 'library_Navigator&folderName=%s' % quote_plus(getLS(32541)), 'tools.png', 'DefaultAddonService.png', isFolder=True)
		self.addDirectoryItem(32049, 'tools_viewTypesNavigator', 'settings.png', 'DefaultAddonService.png', isFolder=True)
		self.addDirectoryItem(32361, 'tools_resetViewTypes', 'settings.png', 'DefaultAddonService.png', isFolder=False)
		#reuselanguage
		if self.reuselanguageinv: 
			self.addDirectoryItem(40179, 'tools_LanguageInvoker&name=False', 'settings.png', 'DefaultAddonProgram.png', isFolder=False)
		else:
			self.addDirectoryItem(40180, 'tools_LanguageInvoker&name=False', 'settings.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32083, 'tools_cleanSettings', 'settings.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(40334, 'tools_deleteSettings', 'settings.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32523, 'tools_loggingNavigator&folderName=%s' % quote_plus(getLS(40460)), 'tools.png', 'DefaultAddonService.png')		
		self.endDirectory()

	def traktTools(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		self.addDirectoryItem(35058, 'shows_traktHiddenManager', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(35059, 'movies_traktUnfinishedManager', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(35060, 'episodes_traktUnfinishedManager', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(35061, 'movies_traktWatchListManager', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(35062, 'shows_traktWatchListManager', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(35063, 'movies_traktCollectionManager', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(35064, 'shows_traktCollectionManager', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(35065, 'tools_traktLikedListManager', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		#self.addDirectoryItem(40217, 'tools_traktImportListManager', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(35066, 'tools_forceTraktSync', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(35067, 'tools_deleteTraktSyncDatabase', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def viewTypeNavigator(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		self.addDirectoryItem(40591, 'tools_viewsNavigator&url=movies', 'settings.png', 'DefaultAddonService.png', isFolder=True)
		self.addDirectoryItem(40592, 'tools_viewsNavigator&url=tvshows', 'settings.png', 'DefaultAddonService.png', isFolder=True)
		self.addDirectoryItem(40593, 'tools_viewsNavigator&url=seasons', 'settings.png', 'DefaultAddonService.png', isFolder=True)
		self.addDirectoryItem(40594, 'tools_viewsNavigator&url=episodes', 'settings.png', 'DefaultAddonService.png', isFolder=True)
		self.endDirectory()

	def simklTools(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		self.addDirectoryItem(getLS(40788) % self.highlight_color, 'movies_simklPlantowatchManager', 'simkl.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(40789) % self.highlight_color, 'shows_simklPlantowatchManager', 'simkl.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(40790) % self.highlight_color, 'shows_simklOnholdManager', 'simkl.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(40786) % self.highlight_color, 'movies_simklDroppedManager', 'simkl.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(40787) % self.highlight_color, 'shows_simklDroppedManager', 'simkl.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(40553, 'tools_forceSimklSync', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def mdblistTools(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		if not self.mdblistCredentials:
			self.addDirectoryItem(40669, 'mdblistAuth', 'mdblist.png', 'DefaultAddonService.png', isFolder=False)
		else:
			self.addDirectoryItem(40670, 'mdblistRevoke', 'mdblist.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(40638, 'movies_mdblistWatchlistManager', 'mdblist.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(40639, 'shows_mdblistWatchlistManager', 'mdblist.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(40709) % self.highlight_color, 'movies_mdblistCollectionManager', 'mdblist.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(40710) % self.highlight_color, 'shows_mdblistCollectionManager', 'mdblist.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(35059) % self.highlight_color, 'movies_mdblistUnfinishedManager', 'mdblist.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(35060) % self.highlight_color, 'episodes_mdblistUnfinishedManager', 'mdblist.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(40714, 'shows_mdblistDroppedManager', 'mdblist.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(40637, 'tools_forceMDBListSync', 'mdblist.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def customTools(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		self.addDirectoryItem(getLS(35061) % self.highlight_color, 'movies_customWatchlistManager', 'icon.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(35062) % self.highlight_color, 'shows_customWatchlistManager', 'icon.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(35063) % self.highlight_color, 'movies_customCollectionManager', 'icon.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(35064) % self.highlight_color, 'shows_customCollectionManager', 'icon.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(40786) % self.highlight_color, 'movies_customDroppedManager', 'icon.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(40787) % self.highlight_color, 'shows_customDroppedManager', 'icon.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(35059) % self.highlight_color, 'movies_customUnfinishedManager', 'icon.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(35060) % self.highlight_color, 'episodes_customUnfinishedManager', 'icon.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem('[COLOR %s][B]Force %s Sync to local database[/B][/COLOR]' % (self.highlight_color, customtrakt.getCustomServiceName()), 'tools_forceCustomSync', 'icon.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def floppyTools(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		if not self.floppyCredentials:
			self.addDirectoryItem('Authorize Floppy', 'floppyAuth', 'floppy.png', 'DefaultAddonService.png', isFolder=False)
		else:
			self.addDirectoryItem('Revoke Floppy', 'floppyRevoke', 'floppy.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(35061) % self.highlight_color, 'movies_floppyWatchlistManager', 'floppy.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(35062) % self.highlight_color, 'shows_floppyWatchlistManager', 'floppy.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(35063) % self.highlight_color, 'movies_floppyCollectionManager', 'floppy.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(35064) % self.highlight_color, 'shows_floppyCollectionManager', 'floppy.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(40786) % self.highlight_color, 'movies_floppyDroppedManager', 'floppy.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(40787) % self.highlight_color, 'shows_floppyDroppedManager', 'floppy.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(35059) % self.highlight_color, 'movies_floppyUnfinishedManager', 'floppy.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(35060) % self.highlight_color, 'episodes_floppyUnfinishedManager', 'floppy.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem('Force Floppy Sync', 'tools_forceFloppySync', 'floppy.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def scrobTools(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		if not self.scrobCredentials:
			self.addDirectoryItem('Authorize Scrob', 'scrobAuth', 'scrob.png', 'DefaultAddonService.png', isFolder=False)
		else:
			self.addDirectoryItem('Revoke Scrob', 'scrobRevoke', 'scrob.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(35059) % self.highlight_color, 'movies_scrobUnfinishedManager', 'scrob.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(getLS(35060) % self.highlight_color, 'episodes_scrobUnfinishedManager', 'scrob.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem('Force Scrob Sync', 'tools_forceScrobSync', 'scrob.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def loggingNavigator(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		self.addDirectoryItem(32524, 'tools_viewLogFile&name=Umbrella', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32525, 'tools_clearLogFile', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32526, 'tools_ShowChangelog&name=Umbrella', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32529, 'tools_ShowFullChangelog&name=Umbrella', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32527, 'tools_uploadLogFile&name=Umbrella', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32532, 'tools_viewLogFile&name=Kodi', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32198, 'tools_uploadLogFile&name=Kodi', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.endDirectory()

	def cf(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		self.addDirectoryItem(32610, 'cache_clearAll', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(32611, 'cache_clearSources', 'settings.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(32612, 'cache_clearMeta', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(32613, 'cache_clearCache', 'settings.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(40519, 'cache_fanart', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(40402, 'cache_clearMovieCache', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(32614, 'cache_clearSearch', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(32615, 'cache_clearBookmarks', 'settings.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(40078, 'cache_clearThumbnails', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def library(self, folderName=''): # -- Library - 9
		if self.useContainerTitles: control.setContainerName(folderName)
		##self.addDirectoryItem(32557, 'tools_openSettings&query=13.0', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32558, 'library_update', 'library_update.png', 'DefaultAddonLibrary.png', isFolder=False)
		self.addDirectoryItem(32676, 'library_clean', 'library_update.png', 'DefaultAddonLibrary.png', isFolder=False)
		self.addDirectoryItem(32559, getSetting('library.movie'), 'movies.png', 'DefaultMovies.png', isAction=False)
		self.addDirectoryItem(32560, getSetting('library.tv'), 'tvshows.png', 'DefaultTVShows.png', isAction=False)
		#if self.traktCredentials:
			#self.addDirectoryItem(32561, 'library_moviesToLibrary&url=traktcollection&name=traktcollection', 'trakt.png', 'DefaultMovies.png', isFolder=False)
			#self.addDirectoryItem(32562, 'library_moviesToLibrary&url=traktwatchlist&name=traktwatchlist', 'trakt.png', 'DefaultMovies.png', isFolder=False)
			#self.addDirectoryItem(32672, 'library_moviesListToLibrary&url=traktlists', 'trakt.png', 'DefaultMovies.png', isFolder=False)
			#self.addDirectoryItem(32673, 'library_moviesListToLibrary&url=traktlikedlists', 'trakt.png', 'DefaultMovies.png', isFolder=False)
		if self.tmdbSessionID:
			self.addDirectoryItem('TMDb: Import Movie Watchlist...', 'library_moviesToLibrary&url=tmdb_watchlist&name=tmdb_watchlist', 'tmdb.png', 'DefaultMovies.png', isFolder=False)
			self.addDirectoryItem('TMDb: Import Movie Favorites...', 'library_moviesToLibrary&url=tmdb_favorites&name=tmdb_favorites', 'tmdb.png', 'DefaultMovies.png', isFolder=False)
			self.addDirectoryItem('TMDb: Import Movie User list...', 'library_moviesListToLibrary&url=tmdb_userlists', 'tmdb.png', 'DefaultMovies.png', isFolder=False)
		# if self.traktCredentials:
		# 	self.addDirectoryItem(32563, 'library_tvshowsToLibrary&url=traktcollection&name=traktcollection', 'trakt.png', 'DefaultTVShows.png', isFolder=False)
		# 	self.addDirectoryItem(32564, 'library_tvshowsToLibrary&url=traktwatchlist&name=traktwatchlist', 'trakt.png', 'DefaultTVShows.png', isFolder=False)
		# 	self.addDirectoryItem(32674, 'library_tvshowsListToLibrary&url=traktlists', 'trakt.png', 'DefaultMovies.png', isFolder=False)
		# 	self.addDirectoryItem(32675, 'library_tvshowsListToLibrary&url=traktlikedlists', 'trakt.png', 'DefaultMovies.png', isFolder=False)
		if self.tmdbSessionID:
			self.addDirectoryItem('TMDb: Import TV Watchlist...', 'library_tvshowsToLibrary&url=tmdb_watchlist&name=tmdb_watchlist', 'tmdb.png', 'DefaultMovies.png', isFolder=False)
			self.addDirectoryItem('TMDb: Import TV Favorites...', 'library_tvshowsToLibrary&url=tmdb_favorites&name=tmdb_favorites', 'tmdb.png', 'DefaultMovies.png', isFolder=False)
			self.addDirectoryItem('TMDb: Import TV User list...', 'library_tvshowsListToLibrary&url=tmdb_userlists', 'tmdb.png', 'DefaultMovies.png', isFolder=False)
		self.endDirectory()

	def downloads(self, folderName=''):
		movie_downloads = getSetting('movie.download.path')
		tv_downloads = getSetting('tv.download.path')
		if len(control.listDir(movie_downloads)[0]) > 0: self.addDirectoryItem(32001, movie_downloads, 'movies.png', 'DefaultMovies.png', isAction=False)
		if len(control.listDir(tv_downloads)[0]) > 0: self.addDirectoryItem(32002, tv_downloads, 'tvshows.png', 'DefaultTVShows.png', isAction=False)
		if self.useContainerTitles: control.setContainerName(folderName)
		self.endDirectory()

	def favourites(self, folderName=''):
		if self.favoriteMovie: self.addDirectoryItem(getLS(40465), 'getFavouritesMovies&url=favourites_movies&folderName=%s' % (quote_plus(getLS(40465))), 'movies.png', 'DefaultMovies.png')
		if self.favoriteTVShows: self.addDirectoryItem(getLS(40466), 'getFavouritesTVShows&url=favourites_tvshows&folderName=%s' % (quote_plus(getLS(40466))), 'tvshows.png', 'DefaultTVShows.png')
		if self.favoriteEpisodes: self.addDirectoryItem(getLS(40467), 'getFavouritesEpisodes&folderName=%s' % (quote_plus(getLS(40467))), 'tvshows.png', 'DefaultTVShows.png')
		if self.useContainerTitles: control.setContainerName(folderName)
		self.endDirectory()

	def premium_services(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		if self.alldebridCredentials:  self.addDirectoryItem(40059, 'ad_ServiceNavigator&folderName=%s' % quote_plus(getLS(40059)), 'alldebrid.png', 'alldebrid.png')
		if self.easynewsCredentials:   self.addDirectoryItem(32327, 'en_ServiceNavigator&folderName=%s' % quote_plus(getLS(32327)), 'easynews.png', 'easynews.png')
		if self.offcloudCredentials:   self.addDirectoryItem(40540, 'oc_ServiceNavigator&folderName=%s' % quote_plus(getLS(40540)), 'offcloud.png', 'offcloud.png')
		if self.premiumizeCredentials: self.addDirectoryItem(40057, 'pm_ServiceNavigator&folderName=%s' % quote_plus(getLS(40057)), 'premiumize.png', 'premiumize.png')
		if self.realdebridCredentials: self.addDirectoryItem(40058, 'rd_ServiceNavigator&folderName=%s' % quote_plus(getLS(40058)), 'realdebrid.png', 'realdebrid.png')
		if self.torboxCredentials:     self.addDirectoryItem(40529, 'tb_ServiceNavigator&folderName=%s' % quote_plus(getLS(35539)), 'torbox.png', 'torbox.png')
		self.endDirectory()

	def alldebrid_service(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		if getSetting('alldebridtoken'):
			self.addDirectoryItem('All-Debrid: Cloud Storage', 'ad_CloudStorage', 'alldebrid.png', 'DefaultAddonService.png')
			self.addDirectoryItem('All-Debrid: Transfers', 'ad_Transfers', 'alldebrid.png', 'DefaultAddonService.png')
			self.addDirectoryItem('All-Debrid: Account Info', 'ad_AccountInfo', 'alldebrid.png', 'DefaultAddonService.png', isFolder=False)
		else:
			self.addDirectoryItem('[I]Please setup in Settings.[/I]', 'tools_openSettings&query=6.1', 'alldebrid.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def easynews_service(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		if getSetting('easynews.user'):
			self.addDirectoryItem('Easy News: Search', 'en_Search', 'search.png', 'DefaultAddonsSearch.png')
			self.addDirectoryItem('Easy News: Account Info', 'en_AccountInfo', 'easynews.png', 'DefaultAddonService.png', isFolder=False)
		else:
			self.addDirectoryItem('[I]Please setup in Settings.[/I]', 'tools_openSettings&query=7.3', 'easynews.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def offcloud_service(self):
		if getSetting('offcloudtoken'):
			self.addDirectoryItem('Offcloud: Cloud Storage', 'oc_CloudStorage', 'offcloud.png', 'DefaultAddonService.png')
			self.addDirectoryItem('Offcloud: Account Info', 'oc_AccountInfo', 'offcloud.png', 'DefaultAddonService.png', isFolder=False)
			self.addDirectoryItem('Offcloud: Clear Cloud Storage', 'oc_UserCloudClear', 'offcloud.png', 'DefaultAddonService.png', isFolder=False)
		else:
			self.addDirectoryItem('[I]Please setup in Accounts[/I]', 'tools_openSettings&query=6.3', 'offcloud.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def torbox_service(self):
		if getSetting('torboxtoken'):
			self.addDirectoryItem('TorBox: Cloud Storage', 'tb_CloudStorage', 'torbox.png', 'DefaultAddonService.png')
			self.addDirectoryItem('TorBox: Account Info', 'tb_AccountInfo', 'torbox.png', 'DefaultAddonService.png', isFolder=False)
			self.addDirectoryItem('TorBox: Delete All Cloud Files', 'tb_DeleteCloud', 'torbox.png', 'DefaultAddonService.png', isFolder=False)
		else:
			self.addDirectoryItem('[I]Please setup in Accounts[/I]', 'tools_openSettings&query=6.6', 'torbox.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def premiumize_service(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		if getSetting('premiumizetoken'):
			self.addDirectoryItem('Premiumize: My Files', 'pm_MyFiles', 'premiumize.png', 'DefaultAddonService.png')
			self.addDirectoryItem('Premiumize: Transfers', 'pm_Transfers', 'premiumize.png', 'DefaultAddonService.png')
			self.addDirectoryItem('Premiumize: Account Info', 'pm_AccountInfo', 'premiumize.png', 'DefaultAddonService.png', isFolder=False)
		else:
			self.addDirectoryItem('[I]Please setup in Settings.[/I]', 'tools_openSettings&query=6.4', 'premiumize.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def realdebrid_service(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		if getSetting('realdebridtoken'):
			self.addDirectoryItem('Real-Debrid: Torrent Transfers', 'rd_UserTorrentsToListItem', 'realdebrid.png', 'DefaultAddonService.png')
			self.addDirectoryItem('Real-Debrid: My Downloads', 'rd_MyDownloads&query=1', 'realdebrid.png', 'DefaultAddonService.png')
			self.addDirectoryItem('Real-Debrid: Account Info', 'rd_AccountInfo', 'realdebrid.png', 'DefaultAddonService.png', isFolder=False )
		else:
			self.addDirectoryItem('[I]Please setup in Settings.[/I]', 'tools_openSettings&query=6.5', 'realdebrid.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def search(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		self.addDirectoryItem(33042, 'movieSearch&folderName=%s' % quote_plus(getLS(33042)), 'trakt.png' if self.iconLogos else 'search.png', 'DefaultAddonsSearch.png')
		self.addDirectoryItem(33043, 'tvSearch&folderName=%s' % quote_plus(getLS(33043)), 'trakt.png' if self.iconLogos else 'search.png', 'DefaultAddonsSearch.png')
		self.addDirectoryItem(33044, 'moviePerson', 'imdb.png' if self.iconLogos else 'people-search.png', 'DefaultAddonsSearch.png', isFolder=False)
		self.addDirectoryItem(33045, 'tvPerson', 'imdb.png' if self.iconLogos else 'people-search.png', 'DefaultAddonsSearch.png', isFolder=False)
		if getSetting('easynews.user'):
			self.addDirectoryItem('Easy News: Search', 'en_Search', 'search.png', 'DefaultAddonsSearch.png')
		#if getSetting('mdblist.token') != '':
			#self.addDirectoryItem(40088, 'mdbListSearch', 'mdblist.png' if self.iconLogos else 'search.png', 'DefaultAddonsSearch.png')
		self.endDirectory()

	# def views(self, folderName=''):
	# 	try:
	# 		from sys import argv # some functions throw invalid handle -1 unless this is imported here.
	# 		syshandle = int(argv[1])
	# 		control.hide()
	# 		items = [(getLS(32001), 'movies'), (getLS(32002), 'tvshows'), (getLS(32054), 'seasons'), (getLS(32326), 'episodes') ]
	# 		select = control.selectDialog([i[0] for i in items], getLS(32049))
	# 		if select == -1: return
	# 		content = items[select][1]
	# 		title = getLS(32059)
	# 		url = 'plugin://plugin.video.umbrella/?action=tools_addView&content=%s' % content
	# 		poster, banner, fanart = control.addonPoster(), control.addonBanner(), control.addonFanart()
	# 		item = control.item(label=title, offscreen=True)
	# 		#item.setInfo(type='video', infoLabels = {'title': title})
	# 		meta = {'title': title}
	# 		control.set_info(item, meta)
	# 		item.setArt({'icon': poster, 'thumb': poster, 'poster': poster, 'fanart': fanart, 'banner': banner})
	# 		control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
	# 		control.content(syshandle, content)
	# 		control.directory(syshandle, cacheToDisc=True)
	# 		from resources.lib.modules import views
	# 		views.setView(content, {})
	# 	except:
	# 		from resources.lib.modules import log_utils
	# 		log_utils.error()
	# 		return

	def views(self, folderName='', content=None):
		try:
			from sys import argv # some functions throw invalid handle -1 unless this is imported here.
			syshandle = int(argv[1])
			control.hide()
			if not content: return
			title = getLS(32059)
			url = 'plugin://plugin.video.umbrella/?action=tools_addView&content=%s' % content
			poster, banner, fanart = control.addonPoster(), control.addonBanner(), control.addonFanart()
			item = control.item(label=title, offscreen=True)
			#item.setInfo(type='video', infoLabels = {'title': title})
			meta = {'title': title}
			control.set_info(item, meta)
			item.setArt({'icon': poster, 'thumb': poster, 'poster': poster, 'fanart': fanart, 'banner': banner})
			control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
			control.content(syshandle, content)
			control.directory(syshandle, cacheToDisc=True)
			from resources.lib.modules import views
			views.setView(content, {})
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return

	def accountCheck(self):
		if (not self.traktCredentials and not self.simklCredentials and not self.tmdbCredentials and not self.mdblistCredentials
				and not self.customCredentials and not self.floppyCredentials and not self.scrobCredentials
				and not (getSetting('indicators.alt') == '0' and getSetting('scrobble.source') == '0')):
			control.hide()
			control.notification(message=32042, icon='WARNING')
			sysexit()

	def clearCacheAll(self):
		control.hide()
		if not control.yesnoDialog(getLS(32077), '', ''): return
		try:
			def cache_clear_all():
				try:
					from resources.lib.database import cache, providerscache, metacache
					providerscache.cache_clear_providers()
					metacache.cache_clear_meta()
					cache.cache_clear()
					cache.cache_clear_search()
					# cache.cache_clear_bookmarks()
					from resources.lib.database import fanarttv_cache
					fanarttv_cache.cache_clear()
					return True
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
			if cache_clear_all(): control.notification(message=32089)
			else: control.notification(message=33586)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def clearCacheProviders(self):
		control.hide()
		if not control.yesnoDialog(getLS(32056), '', ''): return
		try:
			from resources.lib.database import providerscache
			if providerscache.cache_clear_providers(): control.notification(message=32090)
			else: control.notification(message=33586)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def clearMovieCache(self):
		control.hide()
		if not control.yesnoDialog(getLS(32056), '', ''): return
		try:
			from resources.lib.database import cache
			if cache.clearMovieCache(): control.notification(message=40520)
			else: control.notification(message=33586)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def clearCacheMeta(self):
		control.hide()
		if not control.yesnoDialog(getLS(32076), '', ''): return
		try:
			from resources.lib.database import metacache
			if metacache.cache_clear_meta(): control.notification(message=32091)
			else: control.notification(message=33586)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def clearCache(self):
		control.hide()
		if not control.yesnoDialog(getLS(32056), '', ''): return
		try:
			from resources.lib.database import cache
			if cache.cache_clear(): control.notification(message=32092)
			else: control.notification(message=33586)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def clearFanart(self):
		control.hide()
		if not control.yesnoDialog(getLS(32056), '', ''): return
		try:
			from resources.lib.database import fanarttv_cache
			if fanarttv_cache.cache_clear():control.notification(message=40518)
			else: control.notification(message=33586)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def clearMetaAndCache(self):
		control.hide()
		if not control.yesnoDialog(getLS(35531), '', ''): return
		try:
			def cache_clear_both():
				try:
					from resources.lib.database import cache, metacache
					metacache.cache_clear_meta()
					cache.cache_clear()
					return True
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
			if cache_clear_both(): control.notification(message=35532)
			else: control.notification(message=33586)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def clearCacheSearch(self):
		control.hide()
		if not control.yesnoDialog(getLS(32056), '', ''): return
		try:
			from resources.lib.database import cache
			if cache.cache_clear_search(): control.notification(message=32093)
			else: control.notification(message=33586)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def clearCacheSearchPhrase(self, table, name):
		control.hide()
		if not control.yesnoDialog(getLS(32056), '', ''): return
		try:
			from resources.lib.database import cache
			if cache.cache_clear_SearchPhrase(table, name): control.notification(message=32094)
			else: control.notification(message=33586)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def clearBookmarks(self):
		control.hide()
		if not control.yesnoDialog(getLS(32056), '', ''): return
		try:
			from resources.lib.database import cache
			if cache.cache_clear_bookmarks(): control.notification(message=32100)
			else: control.notification(message=33586)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
	
	def clearThumbnails(self):
		control.hide()
		if not control.yesnoDialog(getLS(32056), '', ''): return
		try:
			from resources.lib.database import cache
			if cache.cache_clear_thumbnails(): control.notification(message=40079)
			else: control.notification(message=33586)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def clearBookmark(self, name, year):
		control.hide()
		if not control.yesnoDialog(getLS(32056), '', ''): return
		try:
			from resources.lib.database import cache
			if cache.cache_clear_bookmark(name, year): control.notification(title=name, message=32102)
			else: control.notification(message=33586)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def addDirectoryItem(self, name, query, poster, icon, context=None, queue=False, isAction=True, isFolder=True, isPlayable=False, isSearch=False, table='', multi_context=None):
		try:
			from sys import argv # some functions like ActivateWindow() throw invalid handle less this is imported here.
			if isinstance(name, int): name = getLS(name)
			url = 'plugin://plugin.video.umbrella/?action=%s' % query if isAction else query
			_abs = lambda p: '://' in p or p.startswith('/') or (len(p) > 1 and p[1] == ':')
			poster = control.themedIcon(poster) if self.artPath and not _abs(poster) else (poster or icon)
			if not icon.startswith('Default') and not _abs(icon): icon = control.themedIcon(icon)
			cm = []
			queueMenu = getLS(32065)
			if queue: cm.append((queueMenu, 'RunPlugin(plugin://plugin.video.umbrella/?action=playlist_QueueItem)'))
			if context: cm.append((getLS(context[0]), 'RunPlugin(plugin://plugin.video.umbrella/?action=%s)' % context[1]))
			if isSearch: cm.append(('Clear Search Phrase', 'RunPlugin(plugin://plugin.video.umbrella/?action=cache_clearSearchPhrase&source=%s&name=%s)' % (table, quote_plus(name))))
			if multi_context:
				for ctx_label, ctx_action in multi_context:
					cm.append((ctx_label, 'RunPlugin(plugin://plugin.video.umbrella/?action=%s)' % ctx_action))
			cm.append(('[COLOR %s]Umbrella Settings[/COLOR]' % self.highlight_color, 'RunPlugin(plugin://plugin.video.umbrella/?action=tools_openSettings)'))
			item = control.item(label=name, offscreen=True)
			item.addContextMenuItems(cm)
			if isPlayable: item.setProperty('IsPlayable', 'true')
			item.setArt({'icon': icon, 'poster': poster, 'thumb': poster, 'fanart': control.addonFanart(), 'banner': poster})
			#item.setInfo(type='video', infoLabels={'plot': name}) #k20setinfo
			meta = dict({'plot': name})#k20setinfo
			control.set_info(item, meta)#k20setinfo
			control.addItem(handle=int(argv[1]), url=url, listitem=item, isFolder= isFolder)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def endDirectory(self):
		from sys import argv # some functions throw invalid handle -1 unless this is imported here.
		syshandle = int(argv[1])
		content = 'addons' if control.skin == 'skin.auramod' else ''
		control.content(syshandle, content) # some skins use their own thumb for things like "genres" when content type is set here
		control.directory(syshandle, cacheToDisc=True)