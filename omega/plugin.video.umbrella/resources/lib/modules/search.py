# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""
from resources.lib.modules import control
from resources.lib.modules import client
import re
from urllib.parse import quote_plus

class Search:

	def combined_search(self):
		control.execute('ActivateWindow(Videos,plugin://plugin.video.umbrella/?action=combinedSearchHistory,return)')

	def combined_history(self):
		from sqlite3 import dbapi2 as database
		from contextlib import closing
		from resources.lib.menus.navigator import Navigator
		from resources.lib.modules import log_utils
		nav = Navigator()
		nav.addDirectoryItem(control.lang(32603) % control.setting('highlight.color'), 'combinedSearchnew', 'search.png', 'DefaultAddonsSearch.png', isFolder=False)
		terms = []
		try:
			control.makeFile(control.dataPath)
			with closing(database.connect(control.searchFile)) as dbcon:
				with dbcon:
					dbcon.execute('CREATE TABLE IF NOT EXISTS combined (ID INTEGER PRIMARY KEY AUTOINCREMENT, term)')
					terms = [row[0] for row in dbcon.execute('SELECT DISTINCT term FROM combined ORDER BY term COLLATE NOCASE')]
		except Exception:
			log_utils.error()
		for term in terms:
			nav.addDirectoryItem(term, 'combinedSearchResults&name=%s' % quote_plus(term), 'search.png', 'DefaultAddonsSearch.png', isSearch=True, table='combined')
		if terms:
			nav.addDirectoryItem(32605, 'cache_clearSearch', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		nav.endDirectory()

	def save_combined_term(self, term):
		from sqlite3 import dbapi2 as database
		from contextlib import closing
		from resources.lib.modules import log_utils
		try:
			control.makeFile(control.dataPath)
			with closing(database.connect(control.searchFile)) as dbcon:
				with dbcon:
					for table in ('combined', 'movies', 'tvshow'):
						dbcon.execute('CREATE TABLE IF NOT EXISTS %s (ID INTEGER PRIMARY KEY AUTOINCREMENT, term)' % table)
						dbcon.execute('INSERT INTO %s (term) VALUES (?)' % table, (term,))
		except Exception:
			log_utils.error()

	def combined_search_new(self):
		keyboard = control.keyboard('', control.lang(40829) or 'Search Movies & TV Shows...')
		keyboard.doModal()
		term = keyboard.getText().strip() if keyboard.isConfirmed() else ''
		if not term: return control.closeAll()
		self.save_combined_term(term)
		control.closeAll()
		control.execute('ActivateWindow(Videos,plugin://plugin.video.umbrella/?action=combinedSearchResults&name=%s,return)' % quote_plus(term))

	def combined_results(self, term, urls=None):
		from json import dumps, loads
		from sys import argv
		from resources.lib.menus.movies import Movies
		from resources.lib.menus.tvshows import TVshows
		from resources.lib.modules import log_utils

		movie_menu, tv_menu = Movies(), TVshows()
		if urls:
			links = loads(urls)
		else:
			links = {}
			for kind, menu, setting in (('movies', movie_menu, 'searchmovie.indexer'), ('tvshows', tv_menu, 'searchtv.indexer')):
				if menu.traktCredentials and control.setting(setting) == '1':
					links[kind] = menu.search_link + quote_plus(term)
				else:
					links[kind] = menu.search_tmdb_link % ('%s', quote_plus(term))
		next_links = {}
		found = False
		for kind, menu in (('movies', movie_menu), ('tvshows', tv_menu)):
			link = links.get(kind)
			if not link: continue
			try:
				if '/3/search/' in link:
					items = menu.getTMDb(link, create_directory=False) or []
				else:
					items = menu.get(link, create_directory=False) or []
				if not items: continue
				found = True
				next_link = items[0].get('next')
				if next_link: next_links[kind] = next_link
				if kind == 'movies':
					menu.movieDirectory(items, next=False, finalize=False, label_media=True, folderName=term)
				else:
					menu.tvshowDirectory(items, next=False, finalize=False, label_media=True, folderName=term)
			except Exception:
				log_utils.error()
		handle = int(argv[1])
		if next_links:
			link = 'plugin://plugin.video.umbrella/?action=combinedSearchResults&name=%s&url=%s' % (quote_plus(term), quote_plus(dumps(next_links)))
			item = control.item(label=control.lang(32053), offscreen=True)
			item.setArt({'icon': control.addonNext(), 'thumb': control.addonNext()})
			item.setProperty('SpecialSort', 'bottom')
			control.addItem(handle=handle, url=link, listitem=item, isFolder=True)
		if not found: control.notification(message=33049)
		control.hide()
		control.content(handle, 'videos')
		control.directory(handle, cacheToDisc=False)

	def init(self):
		self.page_limit = control.getSetting('page.item.limit')
		self.keyword_link = 'https://www.imdb.com/search/keyword/?keywords=%s&sort=moviemeter&title_type=%s&count=%s' % ('%s', '%s', self.page_limit)

	def imdb_list(self, url, media):
		list = []
		try:
			result = client.request(url)
			items = client.parseDOM(result, 'li', attrs={'class': 'ipl-zebra-list__item user-list'})
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		for item in items:
			try:
				name = client.parseDOM(item, 'a')[0]
				name = client.replaceHTMLCodes(name)
				url = client.parseDOM(item, 'a', ret='href')[0]
				url = url.split('/list/', 1)[-1].strip('/')
				url = self.imdblist_link % url
				url = client.replaceHTMLCodes(url)
				list.append({'name': name, 'url': url, 'context': url, 'image': 'imdb.png', 'icon': 'DefaultVideoPlaylists.png', 'action': media+'&folderName=%s' % quote_plus(name)})
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		list = sorted(list, key=lambda k: re.sub(r'(^the |^a |^an )', '', k['name'].lower()))
		return list
	def movieKeywordSearch(self, keywords):
		result = None
		if keywords:
			keywords = keywords.replace(' ', '-')
			try:
				url = self.keyword_link(quote_plus(keywords), 'movie')
				result = self.imdb_list(url, media='movie')
				return result
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
				return result

	def tvShowKeywordSearch(self, keywords):
		result = None
		if keywords:
			keywords = keywords.replace(' ', '-')
			try:
				url = self.keyword_link(quote_plus(keywords), 'tvshows')
				result = self.imdb_list(url, media='tvshows')
				return result
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
				return result
