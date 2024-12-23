# -*- coding: utf-8 -*-
"""
	Umbrella Add-on Updated 10-6-24
"""

from datetime import datetime, timedelta
from json import dumps as jsdumps, loads as jsloads
import re
from sys import exit as sysexit
from threading import Thread
from time import time
from urllib.parse import unquote, quote_plus
from sqlite3 import dbapi2 as database
from resources.lib.database import metacache, providerscache
from resources.lib.modules import cleandate
from resources.lib.modules import control
from resources.lib.modules import debrid
from resources.lib.modules import log_utils
from resources.lib.modules import string_tools
from resources.lib.modules.source_utils import supported_video_extensions, getFileType, aliases_check
from resources.lib.cloud_scrapers import cloudSources
from resources.lib.internal_scrapers import internalSources

homeWindow = control.homeWindow
playerWindow = control.playerWindow
getLS = control.lang
getSetting = control.setting
sourceFile = control.providercacheFile
single_expiry = timedelta(hours=6)
season_expiry = timedelta(hours=48)
show_expiry = timedelta(hours=48)
video_extensions = supported_video_extensions()
internal_scrapers_clouds_list = [('realdebrid', 'rd_cloud', 'rd'), ('premiumize', 'pm_cloud', 'pm'), ('alldebrid', 'ad_cloud', 'ad'),('torbox', 'tb_cloud', 'tb'),('offcloud', 'oc_cloud', 'oc')]

class Sources:
	def __init__(self, all_providers=False, custom_query=False, filterless_scrape=False, rescrapeAll=False):
		self.sources = []
		self.scraper_sources = []
		self.uncached_chosen = False
		self.isPrescrape = False
		self.all_providers = all_providers
		self.custom_query = custom_query
		self.filterless_scrape = filterless_scrape
		self.time = datetime.now()
		self.getConstants()
		self.enable_playnext = getSetting('enable.playnext') == 'true'
		self.dev_mode = getSetting('dev.mode.enable') == 'true'
		self.dev_disable_single = getSetting('dev.disable.single') == 'true'
		# self.dev_disable_single_filter = getSetting('dev.disable.single.filter') == 'true'
		self.dev_disable_season_packs = getSetting('dev.disable.season.packs') == 'true'
		self.dev_disable_season_filter = getSetting('dev.disable.season.filter') == 'true'
		self.dev_disable_show_packs = getSetting('dev.disable.show.packs') == 'true'
		self.dev_disable_show_filter = getSetting('dev.disable.show.filter') == 'true'
		self.highlight_color = getSetting('scraper.dialog.color')
		
		self.rescrapeAll = rescrapeAll
		self.retryallsources = getSetting('sources.retryall') == 'true'
		self.uncached_nopopup = getSetting('sources.nocachepopup') == 'true'
		self.providercache_hours = int(getSetting('cache.providers'))
		self.debuglog = control.setting('debug.level') == '1'
		self.external_module = getSetting('external_provider.module')
		self.isHidden = getSetting('progress.dialog') == '4'
		self.useTitleSubs = getSetting('sources.useTitleSubs') == 'true'

	def play(self, title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, premiered, meta, select, rescrape=None):
		if not self.prem_providers:
			control.sleep(200) ; control.hide()
			return control.notification(message=33034)
		try:
			control.sleep(200)
			if control.playlist.getposition() == 0 or control.playlist.size() <= 1 or rescrape == 'true': 
				playerWindow.clearProperty('umbrella.preResolved_nextUrl')
			preResolved_nextUrl = playerWindow.getProperty('umbrella.preResolved_nextUrl')
			if preResolved_nextUrl != '':
				control.sleep(500)
				playerWindow.clearProperty('umbrella.preResolved_nextUrl')
				try: meta = jsloads(unquote(meta.replace('%22', '\\"')))
				except: pass
				if self.debuglog:
					log_utils.log('Playing preResolved_nextUrl = %s' % preResolved_nextUrl, level=log_utils.LOGDEBUG)
				from resources.lib.modules import player
				return player.Player().play_source(title, year, season, episode, imdb, tmdb, tvdb, preResolved_nextUrl, meta)
			if title: title = self.getTitle(title)
			if tvshowtitle: tvshowtitle = self.getTitle(tvshowtitle)
			homeWindow.clearProperty(self.metaProperty)
			homeWindow.setProperty(self.metaProperty, meta)
			homeWindow.clearProperty(self.seasonProperty)
			homeWindow.setProperty(self.seasonProperty, season)
			homeWindow.clearProperty(self.episodeProperty)
			homeWindow.setProperty(self.episodeProperty, episode)
			homeWindow.clearProperty(self.titleProperty)
			homeWindow.setProperty(self.titleProperty, title)
			homeWindow.clearProperty(self.imdbProperty)
			homeWindow.setProperty(self.imdbProperty, imdb)
			homeWindow.clearProperty(self.tmdbProperty)
			homeWindow.setProperty(self.tmdbProperty, tmdb)
			homeWindow.clearProperty(self.tvdbProperty)
			homeWindow.setProperty(self.tvdbProperty, tvdb)
			p_label = '[COLOR %s]%s (%s)[/COLOR]' % (self.highlight_color, title, year) if tvshowtitle is None else \
			'[COLOR %s]%s (S%02dE%02d)[/COLOR]' % (self.highlight_color, tvshowtitle, int(season), int(episode))
			homeWindow.clearProperty(self.labelProperty)
			homeWindow.setProperty(self.labelProperty, p_label)
			url = None
			
			self.mediatype = 'movie' if tvshowtitle is None else 'episode'
			try: meta = jsloads(unquote(meta.replace('%22', '\\"')))
			except: pass
			self.meta = meta
			if meta == None:
				if self.debuglog:
					log_utils.log('No meta was passed in. Trying to find meta now.',level=log_utils.LOGDEBUG)
				self.imdb_user = getSetting('imdbuser').replace('ur', '')
				self.tmdb_key = getSetting('tmdb.apikey')
				if not self.tmdb_key: self.tmdb_key = 'edde6b5e41246ab79a2697cd125e1781'
				self.tvdb_key = getSetting('tvdb.apikey')
				if self.mediatype == 'episode': self.user = str(self.imdb_user) + str(self.tvdb_key)
				else: self.user = str(self.tmdb_key)
				self.lang = control.apiLanguage()['tvdb']
				self.ids = {'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb}
				meta = metacache.fetch([{'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb}], self.lang, self.user)[0]
				if meta != self.ids: meta = dict((k, v) for k, v in iter(meta.items()) if v is not None and v != '')
			def checkLibMeta(): # check Kodi db for meta for library playback.
				def cleanLibArt(art):
					if not art: return ''
					art = unquote(art.replace('image://', ''))
					if art.endswith('/'): art = art[:-1]
					return art
				try:
					if self.mediatype != 'movie': raise Exception()
					# do not add IMDBNUMBER as tmdb scraper puts their id in the key value
					meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["title", "originaltitle", "uniqueid", "year", "premiered", "genre", "studio", "country", "runtime", "rating", "votes", "mpaa", "director", "writer", "cast", "plot", "plotoutline", "tagline", "thumbnail", "art", "file"]}, "id": 1}' % (year, str(int(year) + 1), str(int(year) - 1)))
					meta = jsloads(meta)['result']['movies']
					try:
						meta = [i for i in meta if i.get('uniqueid', []).get('imdb', '') == imdb]
					except:
						if self.debuglog:
							log_utils.log('Get Meta Failed in checkLibMeta: %s' % str(meta), level=log_utils.LOGDEBUG)
						meta = None
					if meta: meta = meta[0]
					else: raise Exception()
					if 'mediatype' not in meta: meta.update({'mediatype': 'movie'})
					if 'duration' not in meta: meta.update({'duration': meta.get('runtime')}) # Trakt scrobble resume needs this for lib playback
					if 'castandrole' not in meta: meta.update({'castandrole': [(i['name'], i['role']) for i in meta.get('cast')]})
					poster = cleanLibArt(meta.get('art').get('poster', '')) or self.poster
					fanart = cleanLibArt(meta.get('art').get('fanart', '')) or self.fanart
					clearart = cleanLibArt(meta.get('art').get('clearart', ''))
					clearlogo = cleanLibArt(meta.get('art').get('clearlogo', ''))
					discart = cleanLibArt(meta.get('art').get('discart'))
					meta.update({'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'poster': poster, 'fanart': fanart, 'clearart': clearart, 'clearlogo': clearlogo, 'discart': discart})
					return meta
				except:
					log_utils.error()
					meta = {}
				try:
					if self.mediatype != 'episode': raise Exception()
					# do not add IMDBNUMBER as tmdb scraper puts their id in the key value
					show_meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["title", "originaltitle", "uniqueid", "mpaa", "year", "genre", "runtime", "thumbnail", "file"]}, "id": 1}' % (year, str(int(year)+1), str(int(year)-1)))
					show_meta = jsloads(show_meta)['result']['tvshows']
					show_meta = [i for i in show_meta if i.get('uniqueid', []).get('imdb', '') == imdb]
					if show_meta: show_meta = show_meta[0]
					else: raise Exception()
					tvshowid = show_meta['tvshowid']
					meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params":{"tvshowid": %d, "filter":{"and": [{"field": "season", "operator": "is", "value": "%s"}, {"field": "episode", "operator": "is", "value": "%s"}]}, "properties": ["title", "season", "episode", "showtitle", "firstaired", "runtime", "rating", "director", "writer", "cast", "plot", "thumbnail", "art", "file"]}, "id": 1}' % (tvshowid, season, episode))
					meta = jsloads(meta)['result']['episodes']
					if meta: meta = meta[0]
					else: raise Exception()
					if 'mediatype' not in meta: meta.update({'mediatype': 'episode'})
					if 'tvshowtitle' not in meta: meta.update({'tvshowtitle': meta.get('showtitle')})
					if 'castandrole' not in meta: meta.update({'castandrole': [(i['name'], i['role']) for i in meta.get('cast')]})
					if 'genre' not in meta: meta.update({'genre': show_meta.get('genre')})
					if 'duration' not in meta: meta.update({'duration': meta.get('runtime')}) # Trakt scrobble resume needs this for lib playback but Kodi lib returns "0" for shows or episodes
					if 'mpaa' not in meta: meta.update({'mpaa': show_meta.get('mpaa')})
					if 'premiered' not in meta: meta.update({'premiered': meta.get('firstaired')})
					if 'year' not in meta: meta.update({'year': show_meta.get('year')}) # shows year not year episode aired
					poster = cleanLibArt(meta.get('art').get('season.poster', '')) or self.poster
					fanart = cleanLibArt(meta.get('art').get('tvshow.fanart', '')) or self.poster
					clearart = cleanLibArt(meta.get('art').get('tvshow.clearart', ''))
					clearlogo = cleanLibArt(meta.get('art').get('tvshow.clearlogo', ''))
					discart = cleanLibArt(meta.get('art').get('discart'))
					meta.update({'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'poster': poster, 'fanart': fanart, 'clearart': clearart, 'clearlogo': clearlogo, 'discart': discart})
					return meta
				except:
					log_utils.error()
					meta = {}
			if self.meta is None or 'videodb' in control.infoLabel('ListItem.FolderPath'):
				self.meta = checkLibMeta()
			if self.mediatype == 'movie':
				if getSetting('imdb.Moviemeta.check') == 'true': # check IMDB. TMDB and Trakt differ on a ratio of 1 in 20 and year is off by 1, some meta titles mismatch
					title, year = self.imdb_meta_chk(imdb, title, year)
				if title == 'The F**k-It List': title = 'The Fuck-It List'
			if self.mediatype == 'episode':
				if getSetting('imdb.Showmeta.check') == 'true':
					tvshowtitle, year = self.imdb_meta_chk(imdb, tvshowtitle, year)
				if tvshowtitle == 'The End of the F***ing World': tvshowtitle = 'The End of the Fucking World'
				if self.useTitleSubs:
					tvshowtitle = self.subTitle(tvshowtitle)
					if self.meta:
						self.meta.update({'tvshowtitle': tvshowtitle})
						p_label = '[COLOR %s]%s (%s)[/COLOR]' % (self.highlight_color, title, year) if tvshowtitle is None else \
						'[COLOR %s]%s (S%02dE%02d)[/COLOR]' % (self.highlight_color, tvshowtitle, int(season), int(episode))
						homeWindow.clearProperty(self.labelProperty)
						homeWindow.setProperty(self.labelProperty, p_label)
						homeWindow.clearProperty(self.metaProperty)
						homeWindow.setProperty(self.metaProperty, jsdumps(self.meta))
				self.total_seasons, self.season_isAiring = self.get_season_info(imdb, tmdb, tvdb, meta, season)
			if rescrape: self.clr_item_providers(title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, premiered)
			items = providerscache.get(self.getSources, self.providercache_hours, title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, premiered)
			if not items:
				self.url = url
				return self.errorForSources(title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, premiered)
			filter = [] ; uncached_items = []
			if getSetting('torrent.remove.uncached') == 'true':
				uncached_items += [i for i in items if re.match(r'^uncached.*torrent', i['source'])]
				filter += [i for i in items if i not in uncached_items]
				if filter: pass
				elif not filter:
					homeWindow.clearProperty('umbrella.window_keep_alive')
					if not self.uncached_nopopup:
						if control.yesnoDialog('No cached torrents returned. Would you like to view the uncached torrents to cache yourself?', '', ''):
							control.cancelPlayback()
							select = '0'
							self.uncached_chosen = True
							filter += uncached_items
				items = filter
				if not items:
					self.url = url
					return self.errorForSources(title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, premiered)
			else: uncached_items += [i for i in items if re.match(r'^uncached.*torrent', i['source'])]
			if select is None:
				if episode is not None and self.enable_playnext: select = '1'
				elif episode == None:
					select = getSetting('play.mode.movie')
				else: select = getSetting('play.mode.tv')
			title = tvshowtitle if tvshowtitle is not None else title
			self.imdb = imdb ; self.tmdb = tmdb ; self.tvdb = tvdb ; self.title = title ; self.year = year
			self.season = season ; self.episode = episode
			self.ids = {'imdb': self.imdb, 'tmdb': self.tmdb, 'tvdb': self.tvdb}
			if len(items) > 0:
				if select == '0':
					control.sleep(200)
					return self.sourceSelect(title, items, uncached_items, self.meta)
				else: url = self.sourcesAutoPlay(items)
			if url == 'close://' or url is None:
				self.url = url
				return self.errorForSources()
			#try:
			#	log_utils.log('From sources.play() Title: %s' % str(title), level=log_utils.LOGDEBUG)
			#	log_utils.log('From sources.play() Year: %s' % str(year), level=log_utils.LOGDEBUG)
			#	log_utils.log('From sources.play() Season: %s' % str(season), level=log_utils.LOGDEBUG)
			#	log_utils.log('From sources.play() Episode: %s' % str(episode), level=log_utils.LOGDEBUG)
			#	log_utils.log('From sources.play() IMDB: %s TMDB: %s TVDB: %s' % (str(imdb), str(tmdb), str(tvdb)), level=log_utils.LOGDEBUG)
			#	log_utils.log('From sources.play() URL: %s' % str(url), level=log_utils.LOGDEBUG)
			#	log_utils.log('From sources.play() Meta: %s' % str(self.meta), level=log_utils.LOGDEBUG)
			#except:
			#	log_utils.error()
			#log_utils.log('Playing from play which indicates pre-scrape or autoplay source url is: %s' % url, level=log_utils.LOGDEBUG)
			if season == 'None': season = None
			if episode == 'None': episode = None
			from resources.lib.modules import player
			player.Player().play_source(title, year, season, episode, imdb, tmdb, tvdb, url, self.meta)
		except:
			log_utils.error()
			control.cancelPlayback()

	def sourceSelect(self, title, items, uncached_items, meta):
		try:
			control.hide()
			control.playlist.clear()
			if not items:
				control.sleep(200) ; control.hide() ; sysexit()
## - compare meta received to database and use largest(eventually switch to a request to fetch missing db meta for item)
			self.imdb_user = getSetting('imdbuser').replace('ur', '')
			self.tmdb_key = getSetting('tmdb.apikey')
			if not self.tmdb_key: self.tmdb_key = 'edde6b5e41246ab79a2697cd125e1781'
			self.tvdb_key = getSetting('tvdb.apikey')
			if self.mediatype == 'episode': self.user = str(self.imdb_user) + str(self.tvdb_key)
			else: self.user = str(self.tmdb_key)
			self.lang = control.apiLanguage()['tvdb']
			meta1 = dict((k, v) for k, v in iter(meta.items()) if v is not None and v != '') if meta else None
			meta2 = metacache.fetch([{'imdb': self.imdb, 'tmdb': self.tmdb, 'tvdb': self.tvdb}], self.lang, self.user)[0]
			if meta2 != self.ids: meta2 = dict((k, v) for k, v in iter(meta2.items()) if v is not None and v != '')
			if meta1 is not None:
				try:
					if len(meta2) > len(meta1):
						meta2.update(meta1)
						meta = meta2
					else: meta = meta1
				except: log_utils.error()
			else: meta = meta2 if meta2 != self.ids else meta1
##################
			self.poster = meta.get('poster') if meta else ''
			self.fanart = meta.get('fanart') if meta else ''
			self.meta = meta
		except: log_utils.error('Error sourceSelect(): ')

		def checkLibMeta(): # check Kodi db for meta for library playback.
			def cleanLibArt(art):
				if not art: return ''
				art = unquote(art.replace('image://', ''))
				if art.endswith('/'): art = art[:-1]
				return art
			try:
				if self.mediatype != 'movie': raise Exception()
				# do not add IMDBNUMBER as tmdb scraper puts their id in the key value
				meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["title", "originaltitle", "uniqueid", "year", "premiered", "genre", "studio", "country", "runtime", "rating", "votes", "mpaa", "director", "writer", "cast", "plot", "plotoutline", "tagline", "thumbnail", "art", "file"]}, "id": 1}' % (self.year, str(int(self.year) + 1), str(int(self.year) - 1)))
				meta = jsloads(meta)['result']['movies']
				try:
					meta = [i for i in meta if i.get('uniqueid', []).get('imdb', '') == self.imdb]
				except:
					if self.debuglog:
						log_utils.log('Get Meta Failed in checkLibMeta: %s' % str(meta), level=log_utils.LOGDEBUG)
					meta = None
				if meta: meta = meta[0]
				else: raise Exception()
				if 'mediatype' not in meta: meta.update({'mediatype': 'movie'})
				if 'duration' not in meta: meta.update({'duration': meta.get('runtime')}) # Trakt scrobble resume needs this for lib playback
				if 'castandrole' not in meta: meta.update({'castandrole': [(i['name'], i['role']) for i in meta.get('cast')]})
				poster = cleanLibArt(meta.get('art').get('poster', '')) or self.poster
				fanart = cleanLibArt(meta.get('art').get('fanart', '')) or self.fanart
				clearart = cleanLibArt(meta.get('art').get('clearart', ''))
				clearlogo = cleanLibArt(meta.get('art').get('clearlogo', ''))
				discart = cleanLibArt(meta.get('art').get('discart'))
				meta.update({'imdb': self.imdb, 'tmdb': self.tmdb, 'tvdb': self.tvdb, 'poster': poster, 'fanart': fanart, 'clearart': clearart, 'clearlogo': clearlogo, 'discart': discart})
				return meta
			except:
				log_utils.error()
				meta = {}
			try:
				if self.mediatype != 'episode': raise Exception()
				# do not add IMDBNUMBER as tmdb scraper puts their id in the key value
				show_meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["title", "originaltitle", "uniqueid", "mpaa", "year", "genre", "runtime", "thumbnail", "file"]}, "id": 1}' % (self.year, str(int(self.year)+1), str(int(self.year)-1)))
				show_meta = jsloads(show_meta)['result']['tvshows']
				show_meta = [i for i in show_meta if i.get('uniqueid', []).get('imdb', '') == self.imdb]
				if show_meta: show_meta = show_meta[0]
				else: raise Exception()
				tvshowid = show_meta['tvshowid']
				meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params":{"tvshowid": %d, "filter":{"and": [{"field": "season", "operator": "is", "value": "%s"}, {"field": "episode", "operator": "is", "value": "%s"}]}, "properties": ["title", "season", "episode", "showtitle", "firstaired", "runtime", "rating", "director", "writer", "cast", "plot", "thumbnail", "art", "file"]}, "id": 1}' % (tvshowid, self.season, self.episode))
				meta = jsloads(meta)['result']['episodes']
				if meta: meta = meta[0]
				else: raise Exception()
				if 'mediatype' not in meta: meta.update({'mediatype': 'episode'})
				if 'tvshowtitle' not in meta: meta.update({'tvshowtitle': meta.get('showtitle')})
				if 'castandrole' not in meta: meta.update({'castandrole': [(i['name'], i['role']) for i in meta.get('cast')]})
				if 'genre' not in meta: meta.update({'genre': show_meta.get('genre')})
				if 'duration' not in meta: meta.update({'duration': meta.get('runtime')}) # Trakt scrobble resume needs this for lib playback but Kodi lib returns "0" for shows or episodes
				if 'mpaa' not in meta: meta.update({'mpaa': show_meta.get('mpaa')})
				if 'premiered' not in meta: meta.update({'premiered': meta.get('firstaired')})
				if 'year' not in meta: meta.update({'year': show_meta.get('year')}) # shows year not year episode aired
				poster = cleanLibArt(meta.get('art').get('season.poster', '')) or self.poster
				fanart = cleanLibArt(meta.get('art').get('tvshow.fanart', '')) or self.poster
				clearart = cleanLibArt(meta.get('art').get('tvshow.clearart', ''))
				clearlogo = cleanLibArt(meta.get('art').get('tvshow.clearlogo', ''))
				discart = cleanLibArt(meta.get('art').get('discart'))
				meta.update({'imdb': self.imdb, 'tmdb': self.tmdb, 'tvdb': self.tvdb, 'poster': poster, 'fanart': fanart, 'clearart': clearart, 'clearlogo': clearlogo, 'discart': discart})
				return meta
			except:
				log_utils.error()
				meta = {}
		if self.meta is None or 'videodb' in control.infoLabel('ListItem.FolderPath'):
			self.meta = checkLibMeta()
		try:
			def sourcesDirMeta(metadata): # pass skin minimal meta needed
				if not metadata: return metadata
				if getSetting('prefer.tmdbArt') == 'true': metadata['clearlogo'] = metadata.get('tmdblogo') or metadata.get('clearlogo', '')
				allowed = ['mediatype', 'imdb', 'tmdb', 'tvdb', 'poster', 'tvshow.poster', 'season_poster', 'season_poster', 'fanart', 'clearart', 'clearlogo', 'discart', 'thumb', 'title', 'tvshowtitle', 'year', 'premiered', 'rating', 'plot', 'duration', 'mpaa', 'season', 'episode', 'castandrole']
				return {k: v for k, v in iter(metadata.items()) if k in allowed}
			self.meta = sourcesDirMeta(self.meta)
			if getSetting('uncached.seeder.sort') == 'true':
				uncached_items = sorted(uncached_items, key=lambda k: k['seeders'], reverse=True)
				uncached_items = self.sort_byQuality(source_list=uncached_items)
			if items == uncached_items:
				from resources.lib.windows.uncached_results import UncachedResultsXML
				window = UncachedResultsXML('uncached_results.xml', control.addonPath(control.addonId()), uncached=uncached_items, meta=self.meta)
			else:
				from resources.lib.windows.source_results import SourceResultsXML
				window = SourceResultsXML('source_results.xml', control.addonPath(control.addonId()), results=items, uncached=uncached_items, meta=self.meta)
			action, chosen_source = window.run()
			del window
			if action == 'play_Item' and self.uncached_chosen != True:
				return self.playItem(title, items, chosen_source.getProperty('umbrella.source_dict'), self.meta)
			else:
				homeWindow.clearProperty('umbrella.window_keep_alive')
				try: self.window.close()
				except: pass
				control.cancelPlayback()
		except:
			log_utils.error('Error sourceSelect(): ')
			control.cancelPlayback()

	def playItem(self, title, items, chosen_source, meta):
		try:
			try: items = jsloads(items)
			except: pass
			try: meta = jsloads(meta)
			except: pass
			try:
				chosen_source = jsloads(chosen_source)
				source_index = items.index(chosen_source[0])
				source_len = len(items)
				next_end = min(source_len, source_index+41)
				sources_next = items[source_index+1:next_end]
				sources_prev = [] if next_end < source_len else items[0:41-(source_len-source_index)]
				if getSetting('sources.useonlyone')== 'true':
					resolve_items = chosen_source
				else:
					resolve_items = [i for i in chosen_source + sources_next + sources_prev]
			except: log_utils.error()
			try:
				poster = meta.get('poster')
			except:
				poster = ''
			header = homeWindow.getProperty(self.labelProperty) + ': Resolving...'
			try:
				if getSetting('progress.dialog') == '0':
					if getSetting('dialogs.useumbrelladialog') == 'true':
						progressDialog = control.getProgressWindow(header, icon=poster)
					else:
						progressDialog = control.progressDialog
						progressDialog.create(header,'')
				elif getSetting('progress.dialog') in ('2', '3', '4'):
					if homeWindow.getProperty('umbrella.window_keep_alive') != 'true':
						progressDialog = self.getWindowProgress(title, meta)
						Thread(target=self.window_monitor, args=(progressDialog,)).start()
					else: progressDialog = self.window
				else: raise Exception()
			except:
				homeWindow.clearProperty('umbrella.window_keep_alive')
				progressDialog = control.progressDialogBG
				progressDialog.create(header, '')
			for i in range(len(resolve_items)):
				try:
					resolve_index = items.index(resolve_items[i])+1
					src_provider = resolve_items[i]['debrid'] if resolve_items[i].get('debrid') else ('%s - %s' % (resolve_items[i]['source'], resolve_items[i]['provider']))
					if getSetting('progress.dialog') == '0':
						if getSetting('dialogs.useumbrelladialog') == 'true':
							label = '[COLOR %s]%s[CR]%s[CR]%s[/COLOR]' % (self.highlight_color, src_provider.upper(), resolve_items[i]['provider'].upper(), resolve_items[i]['info'])
						else:
							label = '[COLOR %s]%s[CR]%02d - %s[CR]%s[/COLOR]' % (self.highlight_color, src_provider.upper(), resolve_index, resolve_items[i]['name'], str(round(resolve_items[i]['size'], 2)) + ' GB') # using "[CR]" has some weird delay with progressDialog.update() at times
					elif getSetting('progress.dialog') == '2':
						resolveInfo = resolve_items[i]['info'].replace('/',' ')
						if meta.get('plot'):
							plotLabel = '[COLOR %s]%s[/COLOR][CR][CR]' %  (getSetting('sources.highlight.color'),meta.get('plot'))
						else:
							plotLabel = ''
						label = plotLabel + '[COLOR %s]%s[CR]%s[CR]%s[CR]%s[CR]%02d - %s[/COLOR]' % (self.highlight_color, src_provider.upper(), resolve_items[i]['provider'].upper(), resolve_items[i]['quality'].upper(), resolveInfo, resolve_index, resolve_items[i]['name'][:30])
					else:
						label = '[COLOR %s]%s[CR]%02d - %s[CR]%s[/COLOR]' % (self.highlight_color, src_provider.upper(), resolve_index, resolve_items[i]['name'], str(round(resolve_items[i]['size'], 2)) + ' GB') # using "[CR]" has some weird delay with progressDialog.update() at times
					control.sleep(100)
					try:
						if progressDialog.iscanceled(): break
						progressDialog.update(int((100 / float(len(resolve_items))) * i), label)
					except: 
						progressDialog.update(int((100 / float(len(resolve_items))) * i), '[COLOR %s]Resolving...[/COLOR]%s' % (self.highlight_color, resolve_items[i]['name']))
					w = Thread(target=self.sourcesResolve, args=(resolve_items[i],))
					w.start()
					for x in range(40):
						try:
							if control.monitor.abortRequested(): return sysexit()
							if progressDialog.iscanceled():
								control.notification(message=32398)
								control.cancelPlayback()
								progressDialog.close()
								del progressDialog
								return
						except: pass
						if not w.is_alive(): break
						control.sleep(200)
					if not self.url: continue
					# if not any(x in self.url.lower() for x in video_extensions):
					if not any(x in self.url.lower() for x in video_extensions) and 'plex.direct:' not in self.url and 'torbox' not in self.url:
						log_utils.log('Playback not supported for (playItem()): %s' % self.url, level=log_utils.LOGWARNING)
						continue
					if homeWindow.getProperty('umbrella.window_keep_alive') != 'true':
						try: progressDialog.close()
						except: pass
						del progressDialog
					from resources.lib.modules import player
					player.Player().play_source(title, self.year, self.season, self.episode, self.imdb, self.tmdb, self.tvdb, self.url, meta)
					return self.url
				except: log_utils.error()
			try: progressDialog.close()
			except: pass
			del progressDialog
			self.errorForSources()
		except: log_utils.error('Error playItem: ')

	def getSources(self, title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, premiered, meta=None, preScrape=False):
		self.window = None
		if preScrape:
			self.isPrescrape = True
			if tvshowtitle is not None:
				self.mediatype = 'episode'
				self.meta = meta
				self.total_seasons, self.season_isAiring = self.get_season_info(imdb, tmdb, tvdb, meta, season)
			return self.getSources_silent(title, year, imdb, tvdb, season, episode, tvshowtitle, premiered)
		else:
			return self.getSources_dialog(title, year, imdb, tvdb, season, episode, tvshowtitle, premiered)

	def getSources_silent(self, title, year, imdb, tvdb, season, episode, tvshowtitle, premiered, timeout=90):
		try:
			p_label = '[COLOR %s]%s (S%02dE%02d)[/COLOR]' % (self.highlight_color, tvshowtitle, int(season), int(episode))
			homeWindow.clearProperty(self.labelProperty)
			homeWindow.setProperty(self.labelProperty, p_label)
			self.prepareSources()
			sourceDict = self.sourceDict
			sourceDict = [(i[0], i[1], i[1].hasEpisodes) for i in sourceDict]
			sourceDict = [(i[0], i[1]) for i in sourceDict if i[2]]
			aliases = []
			try:
				meta = self.meta
				aliases = meta.get('aliases', [])
			except: pass
			threads = []
			scraperDict = [(i[0], i[1], '') for i in sourceDict]
			if self.season_isAiring == 'false':
				scraperDict.extend([(i[0], i[1], 'season') for i in sourceDict if i[1].pack_capable])
				scraperDict.extend([(i[0], i[1], 'show') for i in sourceDict if i[1].pack_capable])
			trakt_aliases = self.getAliasTitles(imdb, 'episode')
			try: aliases.extend([i for i in trakt_aliases if not i in aliases]) # combine TMDb and Trakt aliases
			except: pass
			try: country_codes = meta.get('country_codes', [])
			except: country_codes = []
			for i in country_codes:
				if i in ('CA', 'US', 'UK', 'GB'):
					if i == 'GB': i = 'UK'
					alias = {'title': tvshowtitle + ' ' + i, 'country': i.lower()}
					if not alias in aliases: aliases.append(alias)
			data = {'title': title, 'year': year, 'imdb': imdb, 'tvdb': tvdb, 'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle, 'aliases': aliases, 'premiered': premiered}
			if self.debrid_service: data.update({'debrid_service': self.debrid_service, 'debrid_token': self.debrid_token})
			for i in scraperDict:
				name, pack = i[0].upper(), i[2]
				if pack == 'season': name = '%s (season pack)' % name
				elif pack == 'show': name = '%s (show pack)' % name
				threads.append(Thread(target=self.getEpisodeSource, args=(imdb, season, episode, data, i[0], i[1], pack), name=name))
			[i.start() for i in threads]
			end_time = time() + timeout
		except: return log_utils.error()
		while True:
			try:
				if control.monitor.abortRequested(): return sysexit()
				try:
					info = [x.getName() for x in threads if x.is_alive() is True]
					if len(info) == 0: break
					if end_time < time(): break
				except:
					log_utils.error()
					break
				control.sleep(100)
			except: log_utils.error()
		del threads[:] # Make sure any remaining providers are stopped.
		self.sources.extend(self.scraper_sources)
		self.tvshowtitle = tvshowtitle
		self.year = year
		homeWindow.clearProperty('fs_filterless_search')
		if len(self.sources) > 0: self.sourcesFilter()
		return self.sources

	def getSources_dialog(self, title, year, imdb, tvdb, season, episode, tvshowtitle, premiered, timeout=90):
		try:
			content = 'movie' if tvshowtitle is None else 'episode'
			if self.filterless_scrape: homeWindow.setProperty('fs_filterless_search', 'true')
			if self.custom_query == 'true':
				try:
					custom_title = control.dialog.input('[COLOR %s][B]%s[/B][/COLOR]' % (self.highlight_color, getLS(32038)), defaultt=tvshowtitle if tvshowtitle else title)
					if content == 'movie':
						if custom_title: title = custom_title ; self.meta.update({'title': title})
						custom_year = control.dialog.input('[COLOR %s]%s (%s)[/COLOR]' % (self.highlight_color, getLS(32457), getLS(32488)), type=control.numeric_input, defaultt=str(year))
						if custom_year: year = str(custom_year) ; self.meta.update({'year': year})
					else:
						if custom_title: tvshowtitle = custom_title ; self.meta.update({'tvshowtitle': tvshowtitle})
						custom_season = control.dialog.input('[COLOR %s]%s (%s)[/COLOR]' % (self.highlight_color, getLS(32055), getLS(32488)), type=control.numeric_input, defaultt=str(season))
						if custom_season: season = str(custom_season) ; self.meta.update({'season': season})
						custom_episode = control.dialog.input('[COLOR %s]%s (%s)[/COLOR]' % (self.highlight_color, getLS(32325), getLS(32488)), type=control.numeric_input, defaultt=str(episode))
						if custom_episode: episode = str(custom_episode) ; self.meta.update({'episode': episode})
					p_label = '[COLOR %s]%s (%s)[/COLOR]' % (self.highlight_color, title, year) if tvshowtitle is None else '[COLOR %s]%s (S%02dE%02d)[/COLOR]' % (self.highlight_color, tvshowtitle, int(season), int(episode))
					homeWindow.clearProperty(self.labelProperty)
					homeWindow.setProperty(self.labelProperty, p_label)
					homeWindow.clearProperty(self.metaProperty)
					homeWindow.setProperty(self.metaProperty, jsdumps(self.meta))
					homeWindow.clearProperty(self.seasonProperty)
					homeWindow.setProperty(self.seasonProperty, season)
					homeWindow.clearProperty(self.episodeProperty)
					homeWindow.setProperty(self.episodeProperty, episode)
					homeWindow.clearProperty(self.titleProperty)
					homeWindow.setProperty(self.titleProperty, title)
					log_utils.log('Custom query scrape ran using: %s' % p_label, level=log_utils.LOGDEBUG)
				except: log_utils.error()
			#progressDialog = control.progressDialog if getSetting('progress.dialog') == '0' else control.progressDialogBG
			header = homeWindow.getProperty(self.labelProperty) + ': Scraping...'
			try:
				if getSetting('progress.dialog') == '0':
					if getSetting('dialogs.useumbrelladialog') == 'true':
						progressDialog = control.getProgressWindow(header, icon='')
						debrid_message = '[COLOR %s][B]Please wait...[CR]Checking Providers[/B][/COLOR]' % self.highlight_color
					else:
						progressDialog = control.progressDialog
						progressDialog.create(header,'')
						debrid_message = '[COLOR %s][B]Please wait...[CR]Checking Providers[/B][/COLOR]' % self.highlight_color
				elif getSetting('progress.dialog') in ('2', '3','4'):
					try: meta = self.meta
					except: meta = {'title': title, 'year': year, 'imdb': imdb, 'tvdb': tvdb, 'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle}
					progressDialog = self.getWindowProgress(title, meta)
					Thread(target=self.window_monitor, args=(progressDialog,)).start()
					debrid_message = '[COLOR %s][B]Please wait...[CR]Checking Providers[/B][/COLOR]' % self.highlight_color
				else: raise Exception()
			except:
				homeWindow.clearProperty('umbrella.window_keep_alive')
				progressDialog = control.progressDialogBG
				progressDialog.create(header, '')
				debrid_message = '[COLOR %s][B]Please wait...  Checking Providers[/B][/COLOR]' % self.highlight_color
			self.prepareSources()
			sourceDict = self.sourceDict
			progressDialog.update(0, getLS(32600)) # preparing sources
			if content == 'movie': sourceDict = [(i[0], i[1]) for i in sourceDict if i[1].hasMovies]
			else: sourceDict = [(i[0], i[1]) for i in sourceDict if i[1].hasEpisodes]
			if getSetting('cf.disable') == 'true': sourceDict = [(i[0], i[1]) for i in sourceDict if not any(x in i[0] for x in self.sourcecfDict)]
			if getSetting('scrapers.prioritize') == 'true': 
				sourceDict = [(i[0], i[1], i[1].priority) for i in sourceDict]
				sourceDict = sorted(sourceDict, key=lambda i: i[2]) # sorted by scraper priority
			try: aliases = self.meta.get('aliases', [])
			except: aliases = []
			threads = [] ; threads_append = threads.append

			if content == 'movie':
				trakt_aliases = self.getAliasTitles(imdb, content) # cached for 7 days in trakt module called
				try: aliases.extend([i for i in trakt_aliases if not i in aliases]) # combine TMDb and Trakt aliases
				except: pass
				data = {'title': title, 'aliases': aliases, 'year': year, 'imdb': imdb}
				if self.debrid_service: data.update({'debrid_service': self.debrid_service, 'debrid_token': self.debrid_token})
				for i in sourceDict: threads_append(Thread(target=self.getMovieSource, args=(imdb, data, i[0], i[1]), name=i[0].upper()))
			else:
				scraperDict = [(i[0], i[1], '') for i in sourceDict] if ((not self.dev_mode) or (not self.dev_disable_single)) else []
				if self.season_isAiring == 'false':
					if (not self.dev_mode) or (not self.dev_disable_season_packs): scraperDict.extend([(i[0], i[1], 'season') for i in sourceDict if i[1].pack_capable])
					if (not self.dev_mode) or (not self.dev_disable_show_packs): scraperDict.extend([(i[0], i[1], 'show') for i in sourceDict if i[1].pack_capable])
				trakt_aliases = self.getAliasTitles(imdb, content) # cached for 7 days in trakt module called
				try: aliases.extend([i for i in trakt_aliases if not i in aliases]) # combine TMDb and Trakt aliases
				except: pass
				try: country_codes = self.meta.get('country_codes', [])
				except: country_codes = []
				for i in country_codes:
					if i in ('CA', 'US', 'UK', 'GB'):
						if i == 'GB': i = 'UK'
						alias = {'title': tvshowtitle + ' ' + i, 'country': i.lower()}
						if not alias in aliases: aliases.append(alias)
				aliases = aliases_check(tvshowtitle, aliases)
				data = {'title': title, 'year': year, 'imdb': imdb, 'tvdb': tvdb, 'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle, 'aliases': aliases, 'premiered': premiered}
				if self.debrid_service: data.update({'debrid_service': self.debrid_service, 'debrid_token': self.debrid_token})
				for i in scraperDict:
					name, pack = i[0].upper(), i[2]
					if pack == 'season': name = '%s (season pack)' % name
					elif pack == 'show': name = '%s (show pack)' % name
					threads_append(Thread(target=self.getEpisodeSource, args=(imdb, season, episode, data, i[0], i[1], pack), name=name))
			[i.start() for i in threads]
			sdc = getSetting('sources.highlight.color')
			string1 = getLS(32404) % (self.highlight_color, sdc, '%s') # msgid "[COLOR %s]Time elapsed:[/COLOR]  [COLOR %s]%s seconds[/COLOR]"
			string3 = getLS(32406) % (self.highlight_color, sdc, '%s') # msgid "[COLOR %s]Remaining providers:[/COLOR] [COLOR %s]%s[/COLOR]"
			string4 = getLS(32407) % (self.highlight_color, sdc, '%s') # msgid "[COLOR %s]Unfiltered Total: [/COLOR]  [COLOR %s]%s[/COLOR]"
			#string1f = getLS(32404) % (sdc, sdc, '%s') # msgid "[COLOR %s]Time elapsed:[/COLOR]  [COLOR %s]%s seconds[/COLOR]"
			#string3f = getLS(32406) % (sdc, sdc, '%s') # msgid "[COLOR %s]Remaining providers:[/COLOR] [COLOR %s]%s[/COLOR]"
			#string4f = getLS(32407) % (sdc, sdc, '%s') # msgid "[COLOR %s]Unfiltered Total: [/COLOR]  [COLOR %s]%s[/COLOR]"


			try: timeout = int(getSetting('scrapers.timeout'))
			except: pass
			if self.all_providers == 'true': timeout = 90
			start_time = time()
			end_time = start_time + timeout
			quality = getSetting('hosts.quality') or '0'
			line1 = line2 = line3 = ""
			terminate_onCloud = getSetting('terminate.onCloud.sources') == 'true'
			pre_emp_movie = getSetting('preemptive.termination.movie') == 'true'
			pre_emp_limit_movie = int(getSetting('preemptive.limit.movie'))
			pre_emp_res_movie = getSetting('preemptive.res.movie') or '0'
			pre_emp_tv = getSetting('preemptive.termination.tv') == 'true'
			pre_emp_limit_tv = int(getSetting('preemptive.limit.tv'))
			pre_emp_res_tv = getSetting('preemptive.res.tv') or '0'
			#new settings for tv and movie isolated.
			source_4k = source_1080 = source_720 = source_sd = total = 0
			total_format = '[COLOR %s][B]%s[/B][/COLOR]'
			total_format2 = '[B]%s[/B]'
			pdiag_format = '[COLOR %s]4K:[/COLOR]  %s  |  [COLOR %s]1080p:[/COLOR]  %s  |  [COLOR %s]720p:[/COLOR]  %s  |  [COLOR %s]SD:[/COLOR]  %s' % (
				self.highlight_color, '%s', self.highlight_color, '%s', self.highlight_color, '%s', self.highlight_color, '%s')
			#pdiagfull_format = '[COLOR %s]4K:[/COLOR]  %s  |  [COLOR %s]1080p:[/COLOR]  %s  |  [COLOR %s]720p:[/COLOR]  %s  |  [COLOR %s]SD:[/COLOR]  %s' % (
			#	sdc, '%s', sdc, '%s', sdc, '%s', sdc, '%s')
			control.hide()
		except:
			log_utils.error()
			try: progressDialog.close()
			except: pass
			del progressDialog
			return

		while True:
			try:
				if control.monitor.abortRequested(): return sysexit()
				try:
					if progressDialog.iscanceled(): 
						break
				except: pass

				if terminate_onCloud:
					if len([e for e in self.scraper_sources if e['source'] == 'cloud']) > 0: break
				if content == 'movie':
					if pre_emp_movie:
						if pre_emp_res_movie == '0' and source_4k >= pre_emp_limit_movie: break
						elif pre_emp_res_movie == '1' and source_1080 >= pre_emp_limit_movie: break
						elif pre_emp_res_movie == '2' and source_720 >= pre_emp_limit_movie: break
						elif pre_emp_res_movie == '3' and source_sd >= pre_emp_limit_movie: break
				else:
					if pre_emp_tv:
						if pre_emp_res_tv == '0' and source_4k >= pre_emp_limit_tv: break
						elif pre_emp_res_tv == '1' and source_1080 >= pre_emp_limit_tv: break
						elif pre_emp_res_tv == '2' and source_720 >= pre_emp_limit_tv: break
						elif pre_emp_res_tv == '3' and source_sd >= pre_emp_limit_tv: break
				if quality == '0':
					source_4k = len([e for e in self.scraper_sources if e['quality'] == '4K'])
					source_1080 = len([e for e in self.scraper_sources if e['quality'] == '1080p'])
					source_720 = len([e for e in self.scraper_sources if e['quality'] == '720p'])
					source_sd = len([e for e in self.scraper_sources if e['quality'] in ('SD', 'SCR', 'CAM')])
				elif quality == '1':
					source_1080 = len([e for e in self.scraper_sources if e['quality'] == '1080p'])
					source_720 = len([e for e in self.scraper_sources if e['quality'] == '720p'])
					source_sd = len([e for e in self.scraper_sources if e['quality'] in ('SD', 'SCR', 'CAM')])
				elif quality == '2':
					source_720 = len([e for e in self.scraper_sources if e['quality'] == '720p'])
					source_sd = len([e for e in self.scraper_sources if e['quality'] in ('SD', 'SCR', 'CAM')])
				else:
					source_sd = len([e for e in self.scraper_sources if e['quality'] in ('SD', 'SCR', 'CAM')])
				total = source_4k + source_1080 + source_720 + source_sd

				source_4k_label = total_format2 % (source_4k) if source_4k == 0 else total_format % (sdc, source_4k)
				source_1080_label = total_format2 % (source_1080) if source_1080 == 0 else total_format % (sdc, source_1080)
				source_720_label = total_format2 % (source_720) if source_720 == 0 else total_format % (sdc, source_720)
				source_sd_label = total_format2 % (source_sd) if source_sd == 0 else total_format % (sdc, source_sd)
				source_total_label = total_format2 % (total) if total == 0 else total_format % (sdc, total)
				try:
					info = [x.getName() for x in threads if x.is_alive() is True]
					line1 = pdiag_format % (source_4k_label, source_1080_label, source_720_label, source_sd_label)
					#line2 = string4 % source_total_label + '     ' + string1 % round(time() - start_time, 1)
					line2 = string1 % round(time() - start_time, 1)
					if len(info) > 6: line3 = string3 % str(len(info))
					elif len(info) > 0: line3 = string3 % (', '.join(info))
					else: break
					current_time = time()
					current_progress = current_time - start_time
					#percent = int((current_progress / float(timeout)) * 100)
					percent = int((len(sourceDict) - len(info)) * 100 / len(sourceDict))
					if progressDialog != control.progressDialog and progressDialog != control.progressDialogBG:
						progressDialog.update(max(1, percent), line1 + '[CR]' + line2 + '[CR]' + line3)
					elif progressDialog != control.progressDialogBG: progressDialog.update(max(1, percent), line1 + '[CR]' + line2 + '[CR]' + line3)
					else: progressDialog.update(max(1, percent), line1 + '  ' + string3 % str(len(info)))
					if end_time < current_time: break
				except:
					log_utils.error()
					break
				control.sleep(25)
			except: log_utils.error()
		progressDialog.update(100, debrid_message)
		del threads[:] # Make sure any remaining providers are stopped, only deletes threads not started yet.
		self.sources.extend(self.scraper_sources)
		self.tvshowtitle = tvshowtitle
		self.year = year
		homeWindow.clearProperty('fs_filterless_search')
		if len(self.sources) > 0: self.sourcesFilter()
		if homeWindow.getProperty('umbrella.window_keep_alive') != 'true':
			try: progressDialog.close()
			except: pass
			del progressDialog
		return self.sources

	def preResolve(self, next_sources, next_meta):
		try:
			if not next_sources: raise Exception()
			homeWindow.setProperty(self.metaProperty, jsdumps(next_meta))
			if getSetting('autoplay.sd') == 'true': next_sources = [i for i in next_sources if not i['quality'] in ('4K', '1080p', '720p')]
			uncached_filter = [i for i in next_sources if re.match(r'^uncached.*torrent', i['source'])]
			next_sources = [i for i in next_sources if i not in uncached_filter]
		except:
			log_utils.error()
			return playerWindow.clearProperty('umbrella.preResolved_nextUrl')

		for i in range(len(next_sources)):
			try:
				control.sleep(1000)
				try:
					if control.monitor.abortRequested(): return sysexit()
					url = self.sourcesResolve(next_sources[i])
					if not url:
						if self.debuglog:
							log_utils.log('preResolve failed for : next_sources[i]=%s' % str(next_sources[i]), level=log_utils.LOGWARNING)
						continue
					# if not any(x in url.lower() for x in video_extensions):
					if not any(x in url.lower() for x in video_extensions) and 'plex.direct:' not in url and 'torbox' not in url:
						if self.debuglog:
							log_utils.log('preResolve Playback not supported for (sourcesAutoPlay()): %s' % url, level=log_utils.LOGWARNING)
						continue
					if url:
						control.sleep(500)
						player_hasVideo = control.condVisibility('Player.HasVideo')
						if player_hasVideo: # do not setPropery if user stops playback quickly because "onPlayBackStopped" is already called and won't be able to clear it.
							playerWindow.setProperty('umbrella.preResolved_nextUrl', url)
							if self.debuglog:
								log_utils.log('preResolved_nextUrl : %s' % url, level=log_utils.LOGDEBUG)
						else:
							if self.debuglog:
								log_utils.log('player_hasVideo = %s : skipping setting preResolved_nextUrl' % player_hasVideo, level=log_utils.LOGWARNING)
						break
				except: pass
			except: log_utils.error()
		control.sleep(200)

	def prepareSources(self):
		try:
			control.makeFile(control.dataPath)
			dbcon = database.connect(sourceFile)
			dbcur = dbcon.cursor()
			dbcur.execute('''CREATE TABLE IF NOT EXISTS rel_src (source TEXT, imdb_id TEXT, season TEXT, episode TEXT, hosts TEXT, added TEXT, UNIQUE(source, imdb_id, season, episode));''')
			dbcur.execute('''CREATE TABLE IF NOT EXISTS rel_aliases (title TEXT, aliases TEXT, UNIQUE(title));''')
			dbcur.connection.commit()
		except: log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()

	def getMovieSource(self, imdb, data, source, call):
		try:
			dbcon = database.connect(sourceFile, timeout=60)
			dbcon.execute('''PRAGMA page_size = 32768''')
			dbcon.execute('''PRAGMA journal_mode = WAL''')
			dbcon.execute('''PRAGMA synchronous = OFF''')
			dbcon.execute('''PRAGMA temp_store = memory''')
			dbcon.execute('''PRAGMA mmap_size = 30000000000''')
			dbcur = dbcon.cursor()
		except: pass
		if not imdb: # Fix to stop items passed with null IMDB_id pulling old unrelated sources from the database
			try:
				dbcur.execute('''DELETE FROM rel_src WHERE (source=? AND imdb_id='' AND season='' AND episode='')''', (source,))
				dbcur.connection.commit()
			except: log_utils.error()
		try:
			sources = []
			db_movie = dbcur.execute('''SELECT * FROM rel_src WHERE (source=? AND imdb_id=? AND season='' AND episode='')''', (source, imdb)).fetchone()
			if db_movie:
				timestamp = cleandate.datetime_from_string(str(db_movie[5]), '%Y-%m-%d %H:%M:%S.%f', False)
				db_movie_valid = abs(self.time - timestamp) < single_expiry
				if db_movie_valid:
					sources = eval(db_movie[4])
					return self.scraper_sources.extend(sources)
		except: log_utils.error()
		try:
			sources = []
			sources = call().sources(data, self.hostprDict)
			if sources:
				self.scraper_sources.extend(sources)
				dbcur.execute('''INSERT OR REPLACE INTO rel_aliases Values (?, ?)''', (data.get('title', ''), repr(data.get('aliases', ''))))
				dbcur.execute('''INSERT OR REPLACE INTO rel_src Values (?, ?, ?, ?, ?, ?)''', (source, imdb, '', '', repr(sources), datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")))
				dbcur.connection.commit()
		except: log_utils.error()

	def getEpisodeSource(self, imdb, season, episode, data, source, call, pack):
		try:
			dbcon = database.connect(sourceFile, timeout=60)
			dbcon.execute('''PRAGMA page_size = 32768''')
			dbcon.execute('''PRAGMA journal_mode = WAL''')
			dbcon.execute('''PRAGMA synchronous = OFF''')
			dbcon.execute('''PRAGMA temp_store = memory''')
			dbcon.execute('''PRAGMA mmap_size = 30000000000''')
			dbcur = dbcon.cursor()
		except: pass
		if not imdb: # Fix to stop items passed with null IMDB_id pulling old unrelated sources from the database
			try:
				dbcur.execute('''DELETE FROM rel_src WHERE (source=? AND imdb_id='' AND season=? AND episode=?)''', (source, season, episode))
				dbcur.execute('''DELETE FROM rel_src WHERE (source=? AND imdb_id='' AND season=? AND episode='')''', (source, season))
				dbcur.execute('''DELETE FROM rel_src WHERE (source=? AND imdb_id='' AND season='' AND episode='')''', (source, ))
				dbcur.connection.commit()
			except: log_utils.error()
		if not pack: # singleEpisodes db check
			try:
				db_singleEpisodes = dbcur.execute('''SELECT * FROM rel_src WHERE (source=? AND imdb_id=? AND season=? AND episode=?)''', (source, imdb, season, episode)).fetchone()
				if db_singleEpisodes:
					timestamp = cleandate.datetime_from_string(str(db_singleEpisodes[5]), '%Y-%m-%d %H:%M:%S.%f', False)
					db_singleEpisodes_valid = abs(self.time - timestamp) < single_expiry
					if db_singleEpisodes_valid:
						sources = eval(db_singleEpisodes[4])
						return self.scraper_sources.extend(sources)
			except: log_utils.error()
		elif pack == 'season': # seasonPacks db check
			try:
				db_seasonPacks = dbcur.execute('''SELECT * FROM rel_src WHERE (source=? AND imdb_id=? AND season=? AND episode='')''', (source, imdb, season)).fetchone()
				if db_seasonPacks:
					timestamp = cleandate.datetime_from_string(str(db_seasonPacks[5]), '%Y-%m-%d %H:%M:%S.%f', False)
					db_seasonPacks_valid = abs(self.time - timestamp) < season_expiry
					if db_seasonPacks_valid:
						sources = eval(db_seasonPacks[4])
						sources = [i for i in sources if not 'episode_start' in i or i['episode_start'] <= int(episode) <= i['episode_end']] # filter out range items that do not apply to current episode for return
						return self.scraper_sources.extend(sources)
			except: log_utils.error()
		elif pack == 'show': # showPacks db check
			try:
				db_showPacks = dbcur.execute('''SELECT * FROM rel_src WHERE (source=? AND imdb_id=? AND season='' AND episode='')''', (source, imdb)).fetchone()
				if db_showPacks:
					timestamp = cleandate.datetime_from_string(str(db_showPacks[5]), '%Y-%m-%d %H:%M:%S.%f', False)
					db_showPacks_valid = abs(self.time - timestamp) < show_expiry
					if db_showPacks_valid:
						sources = eval(db_showPacks[4])
						sources = [i for i in sources if i.get('last_season') >= int(season)] # filter out range items that do not apply to current season for return
						return self.scraper_sources.extend(sources)
			except: log_utils.error()

		try: #dummy write or threads wait till return from scrapers...write for each is needed
			dbcur.execute('''INSERT OR REPLACE INTO rel_src Values (?, ?, ?, ?, ?, ?)''', ('dummy write', '', '', '', '', ''))
			dbcur.connection.commit()
		except: log_utils.error()
		if not pack: # singleEpisodes scraper call
			try:
				sources = []
				sources = call().sources(data, self.hostprDict)
				if sources:
					dbcur.execute('''INSERT OR REPLACE INTO rel_src Values (?, ?, ?, ?, ?, ?)''', (source, imdb, season, episode, repr(sources), datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")))
					dbcur.connection.commit()
					return self.scraper_sources.extend(sources)
				return
			except: return log_utils.error()
		elif pack == 'season': # seasonPacks scraper call
			try:
				sources = []
				sources = call().sources_packs(data, self.hostprDict, bypass_filter=self.dev_disable_season_filter)
				if sources:
					dbcur.execute('''INSERT OR REPLACE INTO rel_src Values (?, ?, ?, ?, ?, ?)''', (source, imdb, season,'', repr(sources), datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")))
					dbcur.connection.commit()
					sources = [i for i in sources if not 'episode_start' in i or i['episode_start'] <= int(episode) <= i['episode_end']] # filter out range items that do not apply to current episode for return
					return self.scraper_sources.extend(sources)
				return
			except: return log_utils.error()
		elif pack == 'show': # showPacks scraper call
			try:
				sources = []
				sources = call().sources_packs(data, self.hostprDict, search_series=True, total_seasons=self.total_seasons, bypass_filter=self.dev_disable_show_filter)
				if sources:
					dbcur.execute('''INSERT OR REPLACE INTO rel_src Values (?, ?, ?, ?, ?, ?)''', (source, imdb, '', '', repr(sources), datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")))
					dbcur.connection.commit()
					sources = [i for i in sources if i.get('last_season') >= int(season)] # filter out range items that do not apply to current season for return
					return self.scraper_sources.extend(sources)
			except: log_utils.error()

	def sourcesFilter(self):
		if not self.isPrescrape: control.busy()
		if getSetting('remove.duplicates') == 'true': self.sources = self.filter_dupes()
		if self.mediatype == 'movie':
			if getSetting('source.filtermbysize') == '1':
				try:
					movie_minSize, movie_maxSize = float(getSetting('source.min.moviesize')), float(getSetting('source.max.moviesize'))
					self.sources = [i for i in self.sources if (i.get('size', 0) >= movie_minSize and i.get('size', 0) <= movie_maxSize)]
				except: log_utils.error()
			if getSetting('source.filtermbysize') == '2':
				try:
					duration = self.meta['duration'] or 5400
					max_size = (0.125 * (0.90 * float(getSetting('source.movie.linespeed', '20'))) * duration)/1000
					self.sources = [i for i in self.sources if (i.get('size', 0) <= max_size)]
				except: log_utils.error()
		else:
			self.sources = [i for i in self.sources if 'movie.collection' not in i.get('name_info', '')] # rare but a few retuned from "complete" show pack scrape returned as "movie.collection"
			if getSetting('source.checkReboots') == 'true':
				try:
					from resources.lib.modules.source_utils import tvshow_reboots
					reboots = tvshow_reboots()
					if self.tvshowtitle in reboots and reboots.get(self.tvshowtitle) == self.year:
						log_utils.log('tvshowtitle(%s) is a REBOOT, filtering for year match per enabled setting' % self.tvshowtitle, level= log_utils.LOGDEBUG)
						self.sources = [i for i in self.sources if self.year in i.get('name')]
				except: log_utils.error()
			if getSetting('source.filterebysize') == '1':
				try:
					episode_minSize, episode_maxSize = float(getSetting('source.min.epsize')), float(getSetting('source.max.epsize'))
					self.sources = [i for i in self.sources if (i.get('size', 0) >= episode_minSize and i.get('size', 0) <= episode_maxSize)]
				except: log_utils.error()
			if getSetting('source.filterebysize') == '2':
				try:
					duration = self.meta['duration'] or 2400
					max_size = (0.125 * (0.90 * float(getSetting('source.episode.linespeed', '20'))) * duration)/1000
					self.sources = [i for i in self.sources if (i.get('size', 0) <= max_size)]
				except: log_utils.error()
			try: self.sources = self.calc_pack_size()
			except: pass
		for i in self.sources:
			try:
				if 'name_info' in i: info_string = getFileType(name_info=i.get('name_info'))
				else: info_string = getFileType(url=i.get('url'))
				i.update({'info': (i.get('info') + ' /' + info_string).lstrip(' ').lstrip('/').rstrip('/')})
			except: log_utils.error()
		if getSetting('remove.hevc') == 'true':
			self.sources = [i for i in self.sources if 'HEVC' not in i.get('info', '')]
		if getSetting('remove.av1') == 'true':
			self.sources = [i for i in self.sources if ' AV1 ' not in i.get('info', '')]
		if getSetting('remove.atvp') == 'true':
			self.sources = [i for i in self.sources if ' APPLE-TV-PLUS ' not in i.get('info', '')]
		if getSetting('remove.avc') == 'true':
			self.sources = [i for i in self.sources if ' AVC ' not in i.get('info', '')]
		if getSetting('remove.divx') == 'true':
			self.sources = [i for i in self.sources if ' DIVX ' not in i.get('info', '')]
		if getSetting('remove.mp4') == 'true':
			self.sources = [i for i in self.sources if ' MP4 ' not in i.get('info', '')]
		if getSetting('remove.mpeg') == 'true':
			self.sources = [i for i in self.sources if ' MPEG ' not in i.get('info', '')]
		if getSetting('remove.wmv') == 'true':
			self.sources = [i for i in self.sources if ' WMV ' not in i.get('info', '')]
		if getSetting('remove.hdr') == 'true':
			self.sources = [i for i in self.sources if ' HDR ' not in i.get('info', '')] # needs space before and aft because of "HDRIP"
		if getSetting('remove.dolby.vision') == 'true':
			self.sources = [i for i in self.sources if ('DOLBY-VISION' not in i.get('info', '')) or ('DOLBY-VISION' in i.get('info', '') and ' HDR ' in i.get('info', ''))]
		if getSetting('remove.cam.sources') == 'true':
			self.sources = [i for i in self.sources if i['quality'] != 'CAM']
		if getSetting('remove.sd.sources') == 'true':
			if any(i for i in self.sources if any(value in i['quality'] for value in ('4K', '1080p', '720p'))): #only remove SD if better quality does exist
				self.sources = [i for i in self.sources if i['quality'] != 'SD']
		if getSetting('remove.3D.sources') == 'true':
			self.sources = [i for i in self.sources if '3D' not in i.get('info', '')]
		if getSetting('remove.audio.opus') == 'true':   #start of audio codec filters
			self.sources = [i for i in self.sources if ' OPUS ' not in i.get('info', '')]
		if getSetting('remove.audio.atmos') == 'true': 
			self.sources = [i for i in self.sources if ' ATMOS ' not in i.get('info', '')]
		if getSetting('remove.audio.dd') == 'true': 
			self.sources = [i for i in self.sources if ' DOLBYDIGITAL ' not in i.get('info', '')]
		if getSetting('remove.audio.ddplus') == 'true': 
			self.sources = [i for i in self.sources if ' DD+ ' not in i.get('info', '')]
		if getSetting('remove.audio.dts') == 'true': 
			self.sources = [i for i in self.sources if ' DTS ' not in i.get('info', '')]
		if getSetting('remove.audio.dtshd') == 'true': 
			self.sources = [i for i in self.sources if ' DTS-HD ' not in i.get('info', '')]
		if getSetting('remove.audio.dtshdma') == 'true': 
			self.sources = [i for i in self.sources if ' DTS-HD MA ' not in i.get('info', '')]
		if getSetting('remove.audio.dtsx') == 'true': 
			self.sources = [i for i in self.sources if ' DTS-X ' not in i.get('info', '')]
		if getSetting('remove.audio.ddtruehd') == 'true': 
			self.sources = [i for i in self.sources if ' DOLBY-TRUEHD ' not in i.get('info', '')]
		if getSetting('remove.audio.aac') == 'true': 
			self.sources = [i for i in self.sources if ' AAC ' not in i.get('info', '')]
		if getSetting('remove.audio.mp3') == 'true': 
			self.sources = [i for i in self.sources if ' MP3 ' not in i.get('info', '')]
		if getSetting('remove.channel.2ch') == 'true':  # start of audio channel filters
			self.sources = [i for i in self.sources if ' 2CH ' not in i.get('info', '')]
		if getSetting('remove.channel.6ch') == 'true':
			self.sources = [i for i in self.sources if ' 6CH ' not in i.get('info', '')]
		if getSetting('remove.channel.7ch') == 'true':
			self.sources = [i for i in self.sources if ' 7CH ' not in i.get('info', '')]
		if getSetting('remove.channel.8ch') == 'true':
			self.sources = [i for i in self.sources if ' 8CH ' not in i.get('info', '')]
		local = [i for i in self.sources if 'local' in i and i['local'] is True] # for library and videoscraper (skips cache check)
		self.sources = [i for i in self.sources if not i in local]
		direct = [i for i in self.sources if i['direct'] == True] # acct scrapers (skips cache check)
		directstart = [] # blank start for enabled only
		if getSetting('easynews.enable') == 'true':
			easynewsList = [i for i in direct if i['provider'] == 'easynews']
			directstart.extend(easynewsList)
		if getSetting('plexshare.enable') == 'true':
			plexList = [i for i in direct if i['provider'] == 'plexshare']
			directstart.extend(plexList)
		if getSetting('gdrive.enable') == 'true':
			gDriveList = [i for i in direct if i['provider'] == 'gdrive']
			directstart.extend(gDriveList)
		if getSetting('filepursuit.enable') == 'true':
			fPursuitList = [i for i in direct if i['provider'] == 'filepursuit']
			directstart.extend(fPursuitList)
		if getSetting('tb_cloud.enabled') == 'true':
			tbCloudList = [i for i in direct if i['provider'] == 'tb_cloud']
			directstart.extend(tbCloudList)
		if getSetting('oc_cloud.enabled') == 'true':
			ocCloudList = [i for i in direct if i['provider'] == 'oc_cloud']
			directstart.extend(ocCloudList)
		#direct = directstart
		self.sources = [i for i in self.sources if not i in directstart]
		from copy import deepcopy
		deepcopy_sources = deepcopy(self.sources)
		deepcopy_sources = [i for i in deepcopy_sources if 'magnet:' in i['url']]
		if deepcopy_sources: hashList = [i['hash'] for i in deepcopy_sources]
		threads = [] ; self.filter = []
		valid_hosters = set([i['source'] for i in self.sources if 'magnet:' not in i['url']])
		control.hide()

		def checkStatus(function, debrid_name, valid_hoster):
			try:
				cached = None
				if deepcopy_sources: cached = function(deepcopy_sources, hashList)
				if cached: self.filter += [dict(list(i.items()) + [('debrid', debrid_name)]) for i in cached] # this makes a new instance so no need for deepcopy beyond the one time done now
				if valid_hoster: self.filter += [dict(list(i.items()) + [('debrid', debrid_name)]) for i in self.sources if i['source'] in valid_hoster and 'magnet:' not in i['url']]
			except: log_utils.error()
		for d in self.debrid_resolvers:
			if d.name == 'Real-Debrid' and getSetting('realdebrid.enable') == 'true':
				try:
					valid_hoster = [i for i in valid_hosters if d.valid_url(i)]
					threads.append(Thread(target=checkStatus, args=(self.rd_cache_chk_list, d.name, valid_hoster)))
				except: log_utils.error()
			if d.name == 'Premiumize.me' and getSetting('premiumize.enable') == 'true':
				try:
					valid_hoster = [i for i in valid_hosters if d.valid_url(i)]
					threads.append(Thread(target=checkStatus, args=(self.pm_cache_chk_list, d.name, valid_hoster)))
				except: log_utils.error()
			if d.name == 'AllDebrid' and getSetting('alldebrid.enable') == 'true':
				try:
					valid_hoster = [i for i in valid_hosters if d.valid_url(i)]
					threads.append(Thread(target=checkStatus, args=(self.ad_cache_chk_list, d.name, valid_hoster)))
				except: log_utils.error()
			if d.name == 'Offcloud' and getSetting('offcloud.enable') == 'true':
				try:
					valid_hoster = []
					threads.append(Thread(target=checkStatus, args=(self.oc_cache_chk_list, d.name, valid_hoster)))
				except: log_utils.error()
			if d.name == 'EasyDebrid' and getSetting('easydebrid.enable') == 'true':
				try:
					valid_hoster = []
					threads.append(Thread(name=d.name.upper(), target=checkStatus, args=(self.ed_cache_chk_list, d.name, valid_hoster)))
				except: log_utils.error()
			if d.name == 'TorBox' and getSetting('torbox.enable') == 'true':
				try:
					valid_hoster = []
					threads.append(Thread(target=checkStatus, args=(self.tb_cache_chk_list, d.name, valid_hoster)))
				except: log_utils.error()
		if threads:
			[i.start() for i in threads]
			[i.join() for i in threads]
		#self.filter += direct # add direct links in to be considered in priority sorting
		self.filter += directstart
		try:
			if len(self.prem_providers) > 1: # resort for debrid/direct priorty, when more than 1 account, because of order cache check threads finish
				self.prem_providers.sort(key=lambda k: k[1])
				self.prem_providers = [i[0] for i in self.prem_providers]
				#log_utils.log('self.prem_providers sort order=%s' % self.prem_providers, level=log_utils.LOGDEBUG)
				self.filter.sort(key=lambda k: self.prem_providers.index(k['debrid'] if k.get('debrid', '') else k['provider']))
		except: log_utils.error()

		self.filter += local # library and video scraper sources
		self.sources = self.filter

		if getSetting('sources.group.sort') == '1':
			torr_filter = []
			torr_filter += [i for i in self.sources if 'torrent' in i['source']]  #torrents first
			if getSetting('sources.size.sort') == 'true': torr_filter.sort(key=lambda k: round(k.get('size', 0)), reverse=True)
			aact_filter = []
			aact_filter += [i for i in self.sources if i['direct'] == True]  #account scrapers and local/library next
			if getSetting('sources.size.sort') == 'true': aact_filter.sort(key=lambda k: round(k.get('size', 0)), reverse=True)
			prem_filter = []
			prem_filter += [i for i in self.sources if 'torrent' not in i['source'] and i['debridonly'] is True]  #prem.hosters last
			if getSetting('sources.size.sort') == 'true': prem_filter.sort(key=lambda k: round(k.get('size', 0)), reverse=True)
			self.sources = torr_filter
			self.sources += aact_filter
			self.sources += prem_filter
		elif getSetting('sources.size.sort') == 'true':
			reverse_sort = True if getSetting('sources.sizeSort.reverse') == 'false' else False
			self.sources.sort(key=lambda k: round(k.get('size', 0), 2), reverse=reverse_sort)

		if getSetting('source.prioritize.av1') == 'true': # filter to place AV1 sources first
			filter = []
			filter += [i for i in self.sources if 'AV1' in i.get('info', '')]
			filter += [i for i in self.sources if i not in filter]
			self.sources = filter

		if getSetting('source.prioritize.hevc') == 'true': # filter to place HEVC sources first
			filter = []
			filter += [i for i in self.sources if 'HEVC' in i.get('info', '')]
			filter += [i for i in self.sources if i not in filter]
			self.sources = filter

		if getSetting('source.prioritize.hdrdv') == 'true': # filter to place HDR and DOLBY-VISION sources first
			filter = []
			#will need a new setting for put dolby above hdr
			#filter += [i for i in self.sources if any(value in i.get('info', '') for value in (' HDR ', 'DOLBY-VISION'))]
			if getSetting('source.prioritize.dolbyvisionfirst')=='true':
				if not getSetting('remove.dolby.vision') == 'true':
					filter += [i for i in self.sources if 'DOLBY-VISION' in i.get('info', '')] #dolby first... going to need to check on hdr to make sure it is not added twice
				if not getSetting('remove.hdr') == 'true':
					filter += [i for i in self.sources if ' HDR ' in i.get('info', '') and i not in filter] #warning about the spaces above.
			else:
				filter += [i for i in self.sources if any(value in i.get('info', '') for value in (' HDR ', 'DOLBY-VISION'))]
			filter += [i for i in self.sources if i not in filter]
			self.sources = filter

		self.sources = self.sort_byQuality(source_list=self.sources)

		filter = [] # filter to place cloud files first
		filter += [i for i in self.sources if i['source'] == 'cloud']
		filter += [i for i in self.sources if i not in filter]
		self.sources = filter

		if getSetting('source.prioritize.direct') == 'true': # filter to place plex sources first
			filter = [] # filter to place cloud files first
			filter += [i for i in self.sources if i['source'] == 'direct']
			filter += [i for i in self.sources if i not in filter]
			self.sources = filter

		self.sources = self.sources[:4000]
		control.hide()
		return self.sources

	def filter_dupes(self):
		filter = []
		append = filter.append
		remove = filter.remove
		log_dupes = getSetting('remove.duplicates.logging') == 'false'
		for i in self.sources:
			larger = False
			a = i['url'].lower()
			for sublist in filter:
				try:
					if i['source'] == 'cloud':
						break
					b = sublist['url'].lower()
					if 'magnet:' in a:
						if i['hash'].lower() in b:
							if sublist['provider'] == 'torrentio' or (len(sublist['name']) > len(i['name']) and i['provider'] != 'torrentio'): # favor "torrentio" or keep matching hash with longer name for possible more info
								larger = True
								break
							remove(sublist)
							if log_dupes: log_utils.log('Removing %s - %s (DUPLICATE TORRENT) ALREADY IN :: %s' % (sublist['provider'], b, i['provider']), level=log_utils.LOGDEBUG)
							break
					elif a == b:
						remove(sublist)
						if log_dupes: log_utils.log('Removing %s - %s (DUPLICATE LINK) ALREADY IN :: %s' % (sublist['source'], i['url'], i['provider']), level=log_utils.LOGDEBUG)
						break
				except: log_utils.error('Error filter_dupes: ')
			if not larger: append(i) # sublist['name'] len() was larger, or "torrentio" so do not append
		item_title = homeWindow.getProperty(self.labelProperty)
		if (self.mediatype == 'movie' or (self.mediatype == 'episode' and not self.enable_playnext)):
			if getSetting('remove.duplicates.popup') != 'true':
				control.notification(title=item_title, message='Removed %s duplicate sources from list' % (len(self.sources) - len(filter)))
		if self.debuglog:
			log_utils.log('Removed %s duplicate sources for (%s) from list' % (len(self.sources) - len(filter), item_title), level=log_utils.LOGDEBUG)
		return filter

	def sourcesAutoPlay(self, items):
		#control.hide()
		#control.sleep(200)
		if getSetting('autoplay.sd') == 'true': items = [i for i in items if not i['quality'] in ('4K', '1080p', '720p')]
		header = homeWindow.getProperty(self.labelProperty) + ': Resolving...'
		try:
			poster = self.meta.get('poster')
		except:
			poster = ''
		try:
			if getSetting('progress.dialog') == '0':
				if getSetting('dialogs.useumbrelladialog') == 'true':
					progressDialog = control.getProgressWindow(header, icon=poster)
				else:
					progressDialog = control.progressDialog
					progressDialog.create(header,'')
			elif getSetting('progress.dialog') in ('2', '3', '4'):
				if homeWindow.getProperty('umbrella.window_keep_alive') != 'true':
					progressDialog = self.getWindowProgress(self.title, self.meta)
					Thread(target=self.window_monitor, args=(progressDialog,)).start()
				else: progressDialog = self.window
			else: raise Exception()
		except:
			homeWindow.clearProperty('umbrella.window_keep_alive')
			progressDialog = control.progressDialogBG
			progressDialog.create(header, '')
		for i in range(len(items)):
			try:
				src_provider = items[i]['debrid'] if items[i].get('debrid') else ('%s - %s' % (items[i]['source'], items[i]['provider']))
				if getSetting('progress.dialog') == '2':
					resolveInfo = items[i]['info'].replace('/',' ')
					if self.meta.get('plot'):
						plotLabel = '[COLOR %s]%s[/COLOR][CR][CR]' % (getSetting('sources.highlight.color'), self.meta.get('plot'))
					else:
						plotLabel = ''
					label = plotLabel + '[B][COLOR %s]%s[CR]%s[CR]%s[CR]%s[/COLOR][/B]' % (self.highlight_color, src_provider.upper(), items[i]['provider'].upper(),items[i]['quality'].upper(), resolveInfo)
				else:
					label = '[B][COLOR %s]%s[CR]%s[CR]%s[/COLOR][/B]' % (self.highlight_color, src_provider.upper(), items[i]['provider'].upper(), items[i]['info'])
				control.sleep(100)
				try:
					if progressDialog.iscanceled(): break
					progressDialog.update(int((100 / float(len(items))) * i), label)
				except: progressDialog.update(int((100 / float(len(items))) * i), '[COLOR %s]Resolving...[/COLOR]%s' % (self.highlight_color, items[i]['name']))
				try:
					if control.monitor.abortRequested(): return sysexit()
					url = self.sourcesResolve(items[i])
					# if not any(x in url.lower() for x in video_extensions):
					if not any(x in url.lower() for x in video_extensions) and 'plex.direct:' not in url and 'torbox' not in url:
						log_utils.log('Playback not supported for (sourcesAutoPlay()): %s' % url, level=log_utils.LOGWARNING)
						continue
					if url:
						break
				except: pass
			except: log_utils.error()
		if homeWindow.getProperty('umbrella.window_keep_alive') != 'true':
			try: progressDialog.close()
			except: pass
			del progressDialog
		return url

	def sourcesResolve(self, item):
		try:
			url = item['url']
			self.url = None
			debrid_provider = item['debrid'] if item.get('debrid') else ''
		except: log_utils.error()
		if 'magnet:' in url:
			if not 'uncached' in item['source']:
				try:
					meta = homeWindow.getProperty(self.metaProperty) # need for CM "download" action
					if meta:
						meta = jsloads(unquote(meta.replace('%22', '\\"')))
						season, episode, title = meta.get('season'), meta.get('episode'), meta.get('title')
					else:
						season = homeWindow.getProperty(self.seasonProperty)
						episode = homeWindow.getProperty(self.episodeProperty)
						title = homeWindow.getProperty(self.titleProperty)
					if debrid_provider == 'Real-Debrid':
						from resources.lib.debrid.realdebrid import RealDebrid as debrid_function
					elif debrid_provider == 'Premiumize.me':
						from resources.lib.debrid.premiumize import Premiumize as debrid_function
					elif debrid_provider == 'AllDebrid':
						from resources.lib.debrid.alldebrid import AllDebrid as debrid_function
					elif debrid_provider == 'Offcloud':
						from resources.lib.debrid.offcloud import Offcloud as debrid_function
					elif debrid_provider == 'EasyDebrid':
						from resources.lib.debrid.easydebrid import EasyDebrid as debrid_function
					elif debrid_provider == 'TorBox':
						from resources.lib.debrid.torbox import TorBox as debrid_function
					else: return
					
					url = debrid_function().resolve_magnet(url, item['hash'], season, episode, title)
					self.url = url
					return url
				except:
					log_utils.error()
					return
		else:
			try:
				direct = item['direct']
				if direct:
					direct_sources = ('ad_cloud', 'oc_cloud', 'pm_cloud', 'rd_cloud', 'tb_cloud')
					if item['provider'] in direct_sources:
						try:
							call = [i[1] for i in self.sourceDict if i[0] == item['provider']][0]
							url = call().resolve(url)
							self.url = url
							return url
						except: pass
					else:
						self.url = url
						return url
				else: # hosters
					if debrid_provider == 'Real-Debrid':
						from resources.lib.debrid.realdebrid import RealDebrid as debrid_function
					elif debrid_provider == 'Premiumize.me':
						from resources.lib.debrid.premiumize import Premiumize as debrid_function
					elif debrid_provider == 'AllDebrid':
						from resources.lib.debrid.alldebrid import AllDebrid as debrid_function
					#elif debrid_provider == 'TorBox':
					#	from resources.lib.debrid.torbox import TorBox as debrid_function
					url = debrid_function().unrestrict_link(url)
					self.url = url
					return url
			except:
				log_utils.error()
				return

	def debridPackDialog(self, provider, name, magnet_url, info_hash):
		try:
			if provider in ('Real-Debrid', 'RD'):
				from resources.lib.debrid.realdebrid import RealDebrid as debrid_function
			elif provider in ('Premiumize.me', 'PM'):
				from resources.lib.debrid.premiumize import Premiumize as debrid_function
			elif provider in ('AllDebrid', 'AD'):
				from resources.lib.debrid.alldebrid import AllDebrid as debrid_function
			elif provider in ('Offcloud', 'OC'):
				from resources.lib.debrid.offcloud import Offcloud as debrid_function
			elif provider in ('EasyDebrid', 'ED'):
				from resources.lib.debrid.easydebrid import EasyDebrid as debrid_function
			elif provider in ('TorBox', 'TB'):
				from resources.lib.debrid.torbox import TorBox as debrid_function
			else: return
			debrid_files = None
			control.busy()
			try: debrid_files = debrid_function().display_magnet_pack(magnet_url, info_hash)
			except: pass
			if not debrid_files:
				control.hide()
				return control.notification(message=32399)
			debrid_files = sorted(debrid_files, key=lambda k: k['filename'].lower())
			display_list = ['%02d | [B]%.2f GB[/B] | [I]%s[/I]' % (count, i['size'], i['filename'].upper()) for count, i in enumerate(debrid_files, 1)]
			control.hide()
			chosen = control.selectDialog(display_list, heading=name)
			if chosen < 0: return None
			if control.condVisibility("Window.IsActive(source_results.xml)"): # close "source_results.xml" here after selection is made and valid
				control.closeAll()
			control.busy()
			chosen_result = debrid_files[chosen]
			if provider in ('Real-Debrid', 'RD'):
				self.url = debrid_function().unrestrict_link(chosen_result['link'])
			elif provider in ('Premiumize.me', 'PM'):
				self.url = debrid_function().add_headers_to_url(chosen_result['link'])
			elif provider in ('AllDebrid', 'AD'):
				self.url = debrid_function().unrestrict_link(chosen_result['link'])
			elif provider in ('Offcloud', 'OC'):
				self.url = chosen_result['link']
			elif provider in ('EasyDebrid', 'ED'):
				self.url = debrid_function().unrestrict_link(chosen_result['link'])
			elif provider in ('TorBox', 'TB'):
				self.url = debrid_function().unrestrict_link(chosen_result['link'])
			from resources.lib.modules import player
			meta = jsloads(unquote(homeWindow.getProperty(self.metaProperty).replace('%22', '\\"'))) # needed for CM "showDebridPack" action
			title = meta['tvshowtitle']
			year = meta['year'] if 'year' in meta else None
			season = meta['season'] if 'season' in meta else None
			episode = meta['episode'] if 'episode' in meta else None
			imdb = meta['imdb'] if 'imdb' in meta else None
			tmdb = meta['tmdb'] if 'tmdb' in meta else None
			tvdb = meta['tvdb'] if 'tvdb' in meta else None
			release_title = chosen_result['filename']
			control.hide()
			from resources.lib.modules import source_utils
			if source_utils.seas_ep_filter(season, episode, release_title):
				return player.Player().play_source(title, year, season, episode, imdb, tmdb, tvdb, self.url, meta, debridPackCall=True) # hack fix for setResolvedUrl issue
			else:
				return player.Player().play(self.url)
		except:
			log_utils.error('Error debridPackDialog: ')
			control.hide()

	def sourceInfo(self, item):
		try:
			from sys import platform as sys_platform
			supported_platform = any(value in sys_platform for value in ('win32', 'linux2'))
			source = jsloads(item)[0]
			list = [('[COLOR %s]url:[/COLOR]  %s' % (self.highlight_color, source.get('url')), source.get('url'))]
			if supported_platform: list += [('[COLOR %s]  -- Copy url To Clipboard[/COLOR]' % self.highlight_color, ' ')] # "&" in magnets causes copy2clip to fail .replace('&', '^&').strip() used in copy2clip() method
			list += [('[COLOR %s]name:[/COLOR]  %s' % (self.highlight_color, source.get('name')), source.get('name'))]
			if supported_platform: list += [('[COLOR %s]  -- Copy name To Clipboard[/COLOR]' % self.highlight_color, ' ')]
			list += [('[COLOR %s]info:[/COLOR]  %s' % (self.highlight_color, source.get('info')), ' ')]
			if 'magnet:' in source.get('url'):
				list += [('[COLOR %s]hash:[/COLOR]  %s' % (self.highlight_color, source.get('hash')), source.get('hash'))]
				if supported_platform: list += [('[COLOR %s]  -- Copy hash To Clipboard[/COLOR]' % self.highlight_color, ' ')]
				list += [('[COLOR %s]seeders:[/COLOR]  %s' % (self.highlight_color, source.get('seeders')), ' ')]
			select = control.selectDialog([i[0] for i in list], 'Source Info')
			if any(x in list[select][0] for x in ('Copy url To Clipboard', 'Copy name To Clipboard', 'Copy hash To Clipboard')):
				from resources.lib.modules.source_utils import copy2clip
				copy2clip(list[select - 1][1])
			return
		except: log_utils.error('Error sourceInfo: ' )

	def alterSources(self, url, meta):
		try:
			if getSetting('play.mode.tv') == '1' or (self.enable_playnext and 'episode' in meta) or getSetting('play.mode.movie') == '1': url += '&select=0'
			else: url += '&select=1'
			control.execute('PlayMedia(%s)' % url)
		except: log_utils.error()

	def errorForSources(self,title=None, year=None, imdb=None, tmdb=None, tvdb=None, season=None, episode=None, tvshowtitle=None, premiered=None):
		try:
			
			homeWindow.clearProperty('umbrella.window_keep_alive')
			control.sleep(200)
			control.hide()
			if self.url == 'close://': control.notification(message=32400)
			elif self.retryallsources:
				if self.rescrapeAll == 'true':
					control.notification(message=32401)
				else:
					control.notification(message=40404)
					control.cancelPlayback()
					control.sleep(200)
					plugin = 'plugin://plugin.video.umbrella/'
					select = getSetting('play.mode.movie') if self.mediatype == 'movie' else getSetting('play.mode.tv')
					systitle, sysmeta = quote_plus(title), quote_plus(jsdumps(self.meta))
					if tvshowtitle:
						url = '%s?action=rescrapeAuto&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&select=%s' % (
								plugin, systitle, year, imdb, tmdb, tvdb, season, episode, quote_plus(tvshowtitle), premiered, sysmeta, select)
					else:
						url = '%s?action=rescrapeAuto&title=%s&year=%s&imdb=%s&tmdb=%s&premiered=%s&meta=%s&select=%s' % (
								plugin, systitle, year, imdb, tmdb, premiered, sysmeta, select)
					return control.execute('PlayMedia(%s)' % url)
#					Sources(all_providers='true', rescrapeAll='true').play(title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, premiered, self.meta, select=select, rescrape='true')
			else: control.notification(message=32401)
			control.cancelPlayback()
		except: log_utils.error()

	def getAliasTitles(self, imdb, content):
		try:
			if content == 'movie':
				from resources.lib.modules.trakt import getMovieAliases
				t = getMovieAliases(imdb)
			else:
				from resources.lib.modules.trakt import getTVShowAliases
				t = getTVShowAliases(imdb)
			if not t: return []
			t = [i for i in t if i.get('country', '').lower() in ('en', '', 'ca', 'us', 'uk', 'gb')]
			return t
		except:
			log_utils.error()
			return []

	def getTitle(self, title):
		title = string_tools.normalize(title)
		return title

	def subTitle(self, tvshowtitle):
		#need to make a table and check for substitutions.
		if tvshowtitle:
			try:
				from resources.lib.database import titlesubs
				subtvshowtitle = titlesubs.substitute_get(tvshowtitle)
				if subtvshowtitle:
					tvshowtitle = subtvshowtitle
			except:
				tvshowtitle = tvshowtitle
			return tvshowtitle
		else:
			return None

	def getSubsList(self):
		try:
			control.hide()
			from resources.lib.database import titlesubs
			addedSubs = titlesubs.all_substitutes(self)
			items = [{'originalTitle': i['originalTitle'],'subTitle':i['subTitle']} for i in addedSubs]
			from resources.lib.windows.title_sublist_manager import TitleSublistManagerXML
			window = TitleSublistManagerXML('title_sublist_manager.xml', control.addonPath(control.addonId()), results=items)
			selected_items = window.run()
			if selected_items:
				self.removeSubs(selected_items)
			del window
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def addNewSub(self):
		original_title = control.dialog.input('[COLOR %s]%s[/COLOR]' % (self.highlight_color,  getLS(40245)), type=control.alpha_input)
		if original_title: 
			sub_title = control.dialog.input('[COLOR %s]%s[/COLOR]' % (self.highlight_color, getLS(40247)), type=control.alpha_input)
			if sub_title:
				from resources.lib.database import titlesubs
				addedSubs = titlesubs.sub_insert(original_title, sub_title)
				if addedSubs: control.notification(message=40248)


	def removeSubs(self, items):
		try:
			if len(items) > 0:
				for v in items:
					removeitem = str(v.get('originalTitle'))
					from resources.lib.database import titlesubs
					titlesubs.clear_substitute('substitle', removeitem)
		except:
			log_utils.error()

	def getConstants(self):
		self.metaProperty = 'plugin.video.umbrella.container.meta'
		self.seasonProperty = 'plugin.video.umbrella.container.season'
		self.episodeProperty = 'plugin.video.umbrella.container.episode'
		self.titleProperty = 'plugin.video.umbrella.container.title'
		self.imdbProperty = 'plugin.video.umbrella.container.imdb'
		self.tmdbProperty = 'plugin.video.umbrella.container.tmdb'
		self.tvdbProperty = 'plugin.video.umbrella.container.tvdb'
		self.labelProperty = 'plugin.video.umbrella.container.label'
		if getSetting('provider.external.enabled') == 'true':
			if getSetting('external_provider.module', '') == '':
				#no external_provider_module
				control.notification(message=control.lang(40447))
				self.sourceDict = internalSources()
				self.sourceDict.extend(cloudSources())
			else:
				try:
					from sys import path
					path.append(control.transPath('special://home/addons/%s/lib' % getSetting('external_provider.module', '')))
					from importlib import import_module
					fs_sources = getattr(import_module(getSetting('external_provider.name')), 'sources')
					if self.all_providers == 'true':
						self.sourceDict = fs_sources(ret_all=True)
						self.sourceDict.extend(internalSources())
					else:
						self.sourceDict = fs_sources()
						self.sourceDict.extend(cloudSources())
						self.sourceDict.extend(internalSources())
				except:
					control.notification(message=control.lang(40448))
					self.sourceDict = internalSources()
					self.sourceDict.extend(cloudSources())
		else:
			self.sourceDict = internalSources()
			self.sourceDict.extend(cloudSources())
		from resources.lib.debrid import premium_hosters
		self.debrid_resolvers = debrid.debrid_resolvers()
		for resolver in ('Real-Debrid', 'Premiumize.me', 'AllDebrid'):
			try:
				options = ((i.name, i.token) for i in self.debrid_resolvers if i.name == resolver)
				if resolver := next(options, None):
					self.debrid_service, self.debrid_token = (*resolver,)
					break
			except: pass
		else: self.debrid_service, self.debrid_token = '', ''
		self.prem_providers = [] # for sorting by debrid and direct source links priority
		if control.setting('easynews.user'): self.prem_providers += [('easynews', int(getSetting('easynews.priority')))]
		if control.setting('filepursuittoken'): self.prem_providers += [('filepursuit', int(getSetting('filepursuit.priority')))]
		#if control.setting('furk.user_name'): self.prem_providers += [('furk', int(getSetting('furk.priority')))]
		if control.setting('gdrivetoken'): self.prem_providers += [('gdrive', int(getSetting('gdrive.priority')))]
		if control.setting('plexsharetoken'): self.prem_providers += [('plexshare', int(getSetting('plexshare.priority')))]
		self.prem_providers += [(d.name, int(d.sort_priority)) for d in self.debrid_resolvers]

		def cache_prDict():
			try:
				hosts = []
				for d in self.debrid_resolvers: hosts += d.get_hosts()[d.name]
				return list(set(hosts))
			except: return premium_hosters.hostprDict
		self.hostprDict = providerscache.get(cache_prDict, 168)
		self.sourcecfDict = premium_hosters.sourcecfDict
	def calc_pack_size(self):
		seasoncount, counts = None, None
		try:
			if self.meta: seasoncount, counts = self.meta.get('seasoncount', None), self.meta.get('counts', None)
		except: log_utils.error()
		if not seasoncount or not counts: # check metacache, 2nd fallback
			try:
				imdb_user = getSetting('imdbuser').replace('ur', '')
				tvdb_key = getSetting('tvdb.apikey')
				user = str(imdb_user) + str(tvdb_key)
				meta_lang = control.apiLanguage()['tvdb']
				if self.meta: imdb, tmdb, tvdb = self.meta.get('imdb', ''), self.meta.get('tmdb', ''), self.meta.get('tvdb', '')
				else: imdb, tmdb, tvdb = homeWindow.getProperty(self.imdbProperty), homeWindow.getProperty(self.tmdbProperty), homeWindow.getProperty(self.tvdbProperty)
				ids = [{'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb}]
				meta2 = metacache.fetch(ids, meta_lang, user)[0]
				if not seasoncount: seasoncount = meta2.get('seasoncount', None)
				if not counts: counts = meta2.get('counts', None)
			except: log_utils.error()
		if not seasoncount or not counts: # make request, 3rd fallback
			try:
				if self.meta: season = self.meta.get('season')
				else: season = homeWindow.getProperty(self.seasonProperty)
				from resources.lib.indexers import tmdb as tmdb_indexer
				counts = tmdb_indexer.TVshows().get_counts(tmdb)
				seasoncount = counts[str(season)]
			except:
				log_utils.error()
				return self.sources
		for i in self.sources:
			try:
#				if i['provider'] == 'torrentio' or i['provider'] == 'selfhosted' or i['provider'] == 'elfhosted': continue # torrentio return file size based on episode query already so bypass re-calc
				if i['provider'] in ('torrentio', 'comet', 'knightcrawler', 'mediafusion', 'selfhosted'): continue # torrentio return file size based on episode query already so bypass re-calc
				if 'package' in i:
					dsize = i.get('size')
					if not dsize: continue
					if i['package'] == 'season':
						divider = int(seasoncount)
						if not divider: continue
					else:
						if not counts: continue
						season_count = 1 ; divider = 0
						while season_count <= int(i['last_season']):
							divider += int(counts[str(season_count)])
							season_count += 1
					float_size = float(dsize) / divider
					if round(float_size, 2) == 0: continue
					str_size = '%.2f GB' % float_size
					info = i['info']
					try: info = [i['info'].split(' / ', 1)[1]]
					except: info = []
					info.insert(0, str_size)
					info = ' / '.join(info)
					i.update({'size': float_size, 'info': info})
				else:
					continue
			except: log_utils.error()
		return self.sources

	def ad_cache_chk_list(self, torrent_List, hashList):
		#if len(torrent_List) == 0: return
		try:
			# from resources.lib.debrid.alldebrid import AllDebrid
			# cached = AllDebrid().check_cache(hashList)
			# if not cached: return None
			# cached = cached['magnets']
			count = 0
			for i in torrent_List:
				# if 'error' in cached[count]: # list index out of range
				# 	count += 1
				# 	continue
				# if cached[count]['instant'] is False:
				# 	if 'package' in i: i.update({'source': 'uncached (pack) torrent'})
				# 	else: i.update({'source': 'uncached torrent'})
				# else:
				# 	if 'package' in i: i.update({'source': 'cached (pack) torrent'})
				# 	else: i.update({'source': 'cached torrent'})
				i.update({'source': 'unchecked'})
				count += 1
			return torrent_List
		except: log_utils.error()

	def oc_cache_chk_list(self, torrent_List, hashList):
		if len(torrent_List) == 0: return
		try:
			from resources.lib.debrid.offcloud import Offcloud
			cached = Offcloud().check_cache(hashList)
			if not cached: return None
			cached = cached['cachedItems']
			for i in torrent_List:
				if i['hash'].lower() in cached:
					if 'package' in i: i.update({'source': 'cached (pack) torrent'})
					else: i.update({'source': 'cached torrent'})
				else:
					if 'package' in i: i.update({'source': 'uncached (pack) torrent'})
					else: i.update({'source': 'uncached torrent'})
			return torrent_List
		except: log_utils.error()

	def ed_cache_chk_list(self, torrent_List, hashList):
		if len(torrent_List) == 0: return
		try:
			from resources.lib.debrid.easydebrid import EasyDebrid
			cached = EasyDebrid().check_cache(hashList)
			if not cached: return None
			cached = cached['cached']
			for i, is_cached in zip(torrent_List, cached):
				if i['hash'].lower() and is_cached:
					if 'package' in i: i.update({'source': 'cached (pack) torrent'})
					else: i.update({'source': 'cached torrent'})
				else:
					if 'package' in i: i.update({'source': 'uncached (pack) torrent'})
					else: i.update({'source': 'uncached torrent'})
			return torrent_List
		except: log_utils.error()

	def tb_cache_chk_list(self, torrent_List, hashList):
		if len(torrent_List) == 0: return
		try:
			from resources.lib.debrid.torbox import TorBox
			cached = TorBox().check_cache(hashList)
			if not cached: return None
			cached = [i['hash'] for i in cached['data']]
			for i in torrent_List:
				if i['hash'].lower() in cached:
					if 'package' in i: i.update({'source': 'cached (pack) torrent'})
					else: i.update({'source': 'cached torrent'})
				else:
					if 'package' in i: i.update({'source': 'uncached (pack) torrent'})
					else: i.update({'source': 'uncached torrent'})
			return torrent_List
		except: log_utils.error()


	def pm_cache_chk_list(self, torrent_List, hashList):
		if len(torrent_List) == 0: return
		try:
			from resources.lib.debrid.premiumize import Premiumize
			cached = Premiumize().check_cache_list(hashList)
			if not cached: return None
			count = 0
			for i in torrent_List:
				if cached[count] is False:
					if 'package' in i: i.update({'source': 'uncached (pack) torrent'})
					else: i.update({'source': 'uncached torrent'})
				else:
					if 'package' in i: i.update({'source': 'cached (pack) torrent'})
					else: i.update({'source': 'cached torrent'})
				count += 1
			return torrent_List
		except: log_utils.error()

	def rd_cache_chk_list(self, torrent_List, hashList):
		if len(torrent_List) == 0: return
		try:
			for i in torrent_List:
				i.update({'source': 'unchecked'})
			return torrent_List
		except: log_utils.error()

	def clr_item_providers(self, title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, premiered):
		providerscache.remove(self.getSources, title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, premiered) # function cache removal of selected item ONLY
		try:
			dbcon = database.connect(sourceFile)
			dbcur = dbcon.cursor()
			dbcur.execute('''SELECT count(name) FROM sqlite_master WHERE type='table' AND name='rel_src';''') # table exists so both will
			if dbcur.fetchone()[0] == 1:
				dbcur.execute('''DELETE FROM rel_src WHERE imdb_id=?''', (imdb,)) # DEL the "rel_src" list of cached links
				dbcur.connection.commit()
		except: log_utils.error()
		finally: dbcur.close() ; dbcon.close()

	def imdb_meta_chk(self, imdb, title, year):
		try:
			if not imdb or imdb == '0': return title, year
			from resources.lib.modules.client import _basic_request
			result = _basic_request('https://v2.sg.media-imdb.com/suggestion/t/{}.json'.format(imdb))
			if not result: return title, year
			result = jsloads(result)['d'][0]
			year_ck = str(result.get('y', ''))
			title_ck = self.getTitle(result['l'])
			if not year_ck or not title_ck: return title, year
			if self.mediatype == 'movie':
				if getSetting('imdb.Movietitle.check') == 'true' and (title != title_ck):
					log_utils.log('IMDb Movie title_ck: (%s) does not match meta Movie title passed: (%s)' % (title_ck, title), __name__, level=log_utils.LOGDEBUG)
					title = title_ck
				if getSetting('imdb.Movieyear.check') == 'true' and (year != year_ck):
					log_utils.log('IMDb Movie year_ck: (%s) does not match meta Movie year passed: (%s) for title: (%s)' % (year_ck, year, title), __name__, level=log_utils.LOGDEBUG)
					year = year_ck
			else:
				if getSetting('imdb.Showtitle.check') == 'true' and (title != title_ck):
					log_utils.log('IMDb Show title_ck: (%s) does not match meta tvshowtitle title passed: (%s)' % (title_ck, title), __name__, level=log_utils.LOGDEBUG)
					title = title_ck
				if getSetting('imdb.Showyear.check') == 'true' and (year != year_ck):
					log_utils.log('IMDb Show year_ck: (%s) does not match meta tvshowtitle year passed: (%s) for title: (%s)' % (year_ck, year, title), __name__, level=log_utils.LOGDEBUG)
					year = year_ck
			return title, year
		except:
			log_utils.error()
			return title, year

	def get_season_info(self, imdb, tmdb, tvdb, meta, season):
		total_seasons = None
		season_isAiring = None
		try:
			total_seasons = meta.get('total_seasons', None)
			season_isAiring = meta.get('season_isAiring', None)
		except: pass
		if not total_seasons or season_isAiring is None: # check metacache, 2nd fallback
			try:
				imdb_user = getSetting('imdbuser').replace('ur', '')
				tvdb_key = getSetting('tvdb.apikey')
				user = str(imdb_user) + str(tvdb_key)
				meta_lang = control.apiLanguage()['tvdb']
				ids = [{'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb}]
				meta2 = metacache.fetch(ids, meta_lang, user)[0]
				if not total_seasons: total_seasons = meta2.get('total_seasons', None)
				if season_isAiring is None: season_isAiring = meta2.get('season_isAiring', None)
			except: log_utils.error()
		if not total_seasons: # make request, 3rd fallback
			try:
				from resources.lib.modules.trakt import getSeasons
				total_seasons = getSeasons(imdb, full=False)
				if total_seasons:
					total_seasons = [i['number'] for i in total_seasons]
					season_special = True if 0 in total_seasons else False
					total_seasons = len(total_seasons)
					if season_special: total_seasons = total_seasons - 1
			except: log_utils.error()
		if season_isAiring is None:
			try:
				from resources.lib.indexers import tmdb as tmdb_indexer
				season_isAiring = tmdb_indexer.TVshows().get_season_isAiring(tmdb, season)
				if not season_isAiring: season_isAiring = 'false'
			except: log_utils.error()
		return total_seasons, season_isAiring

	def sort_byQuality(self, source_list):
		filter = []
		quality = getSetting('hosts.quality') or '0'
		if quality == '0': filter += [i for i in source_list if i['quality'] == '4K']
		if quality in ('0', '1'): filter += [i for i in source_list if i['quality'] == '1080p']
		if quality in ('0', '1', '2'): filter += [i for i in source_list if i['quality'] == '720p']
		filter += [i for i in source_list if i['quality'] == 'SCR']
		filter += [i for i in source_list if i['quality'] == 'SD']
		filter += [i for i in source_list if i['quality'] == 'CAM']
		return filter

	def getWindowProgress(self, title, meta):
		from resources.lib.windows.source_progress import WindowProgress
		window = WindowProgress('source_progress.xml', control.addonPath(control.addonId()), title=title, meta=meta)
		Thread(target=window.run).start()
		return window

	def window_monitor(self, window=None):
		if window is None: return
		self.window = window
		homeWindow.setProperty('umbrella.window_keep_alive', 'true')
		while homeWindow.getProperty('umbrella.window_keep_alive') == 'true': control.sleep(200)
		homeWindow.clearProperty('umbrella.window_keep_alive')
		try: self.window.close()
		except: pass
		self.window = None

	def get_internal_scrapers(self):
		settings = ['provider.external', 'provider.plex', 'provider.gdrive']
		#rd_cloud.enabled
		#pm_cloud.enabled
		#ad_cloud.enabled
		#internal_scrapers_clouds_list = [('realdebrid', 'rd_cloud', 'rd'), ('premiumize', 'pm_cloud', 'pm'), ('alldebrid', 'ad_cloud', 'ad')]
		settings_append = settings.append
		for item in internal_scrapers_clouds_list:
			if self.enabled_debrid_check(item[0], item[2]): settings_append(item[1])
		active = [i.split('.')[1] for i in settings if getSetting('%s.enabled' % i) == 'true']
		return active

	def enabled_debrid_check(self, debrid_service, short_name):
		#premiumize.enable
		#realdebrid.enable
		#alldebrid.enable
		if not getSetting('%s.enable' % debrid_service) == 'true': return False
		return self.has_debrid_token(short_name)

	def has_debrid_token(self, debrid_service):
		if debrid_service == 'rd':
			if getSetting('realdebridtoken') in (None, ''): return False
		else:
			if getSetting('%s.token' % debrid_service) in (None, ''): return False
		return True