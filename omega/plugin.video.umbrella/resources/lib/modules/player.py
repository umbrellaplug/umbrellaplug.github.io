# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from hashlib import md5
from json import dumps as jsdumps, loads as jsloads
from sys import argv, exit as sysexit
from sqlite3 import dbapi2 as database
from urllib.parse import unquote
import xbmc
from resources.lib.database.cache import clear_local_bookmarks
from resources.lib.database.metacache import fetch as fetch_metacache
from resources.lib.database.traktsync import fetch_bookmarks
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules import playcount
from resources.lib.modules import trakt
from resources.lib.modules import opensubs
from difflib import SequenceMatcher
from resources.lib.modules.source_utils import seas_ep_filter
from urllib.request import urlopen, Request
import fnmatch
import os

LOGINFO = 1
getLS = control.lang
getSetting = control.setting
homeWindow = control.homeWindow
playerWindow = control.playerWindow


class Player(xbmc.Player):
	def __init__(self):
		xbmc.Player.__init__(self)
		self.play_next_triggered = False
		self.preScrape_triggered = False
		self.playbackStopped_triggered = False
		self.playback_resumed = False
		self.onPlayBackStopped_ran = False
		self.media_type = None
		self.DBID = None
		self.offset = '0'
		self.media_length = 0
		self.current_time = 0
		self.meta = {}
		self.enable_playnext = getSetting('enable.playnext') == 'true'
		self.playnext_time = int(getSetting('playnext.time')) or 60
		self.playnext_percentage = int(getSetting('playnext.percent')) or 80
		self.markwatched_percentage = int(getSetting('markwatched.percent')) or 85
		self.traktCredentials = trakt.getTraktCredentialsInfo()
		self.prefer_tmdbArt = getSetting('prefer.tmdbArt') == 'true'
		self.subtitletime = None
		self.debuglog = getSetting('debug.level') == '1'
		self.multi_season = getSetting('umbrella.multiSeason') == 'true'
		self.playnext_method = getSetting('playnext.method')
		self.playnext_theme = getSetting('playnext.theme')
		self.playnext_min = getSetting('playnext.min.seconds')
		playerWindow.setProperty('umbrella.playnextPlayPressed', str(0))

	def play_source(self, title, year, season, episode, imdb, tmdb, tvdb, url, meta, debridPackCall=False):
		
		#if self.debuglog:
			#try:
				#log_utils.log('play_source Title: %s Type: %s' % (str(title), type(title)), level=log_utils.LOGDEBUG)
				#log_utils.log('play_source Year: %s Type: %s' % (str(year), type(year)), level=log_utils.LOGDEBUG)
				#log_utils.log('play_source Season: %s Type: %s' % (str(season), type(season)), level=log_utils.LOGDEBUG)
				#log_utils.log('play_source Episode: %s Type: %s' % (str(episode), type(episode)), level=log_utils.LOGDEBUG)
				#log_utils.log('play_source IMDB: %s Type: %s TMDB: %s Type: %s TVDB: %s Type: %s' % (str(imdb), type(imdb), str(tmdb), type(tmdb), str(tvdb), type(tvdb)), level=log_utils.LOGDEBUG)
				#log_utils.log('play_source URL: %s Type: %s' % (str(url), type(url)), level=log_utils.LOGDEBUG)
				#log_utils.log('play_source Meta: %s Type: %s' % (str(self.meta), type(self.meta)), level=log_utils.LOGDEBUG)
			#except:
				#log_utils.error()
		try:
			from sys import argv # some functions like ActivateWindow() throw invalid handle less this is imported here.
			if not url: raise Exception
			# if self.debuglog:
			# 	log_utils.log('Play Source Received title: %s year: %s metatype: %s' % (title, year, type(meta)), level=log_utils.LOGDEBUG)
			self.media_type = 'movie' if season is None or episode is None else 'episode'
			self.title, self.year = title, str(year)
			if self.media_type == 'movie':
				self.name, self.season, self.episode = '%s (%s)' % (title, self.year), None, None
			
			elif self.media_type == 'episode':
				self.name, self.season, self.episode = '%s S%02dE%02d' % (title, int(season), int(episode)), '%01d' % int(season), '%01d' % int(episode)
			self.imdb, self.tmdb, self.tvdb = imdb or '', tmdb or '', tvdb or ''
			self.ids = {'imdb': self.imdb, 'tmdb': self.tmdb, 'tvdb': self.tvdb}
## - compare meta received to database and use largest(eventually switch to a request to fetch missing db meta for item)
			self.imdb_user = getSetting('imdbuser').replace('ur', '')
			self.tmdb_key = getSetting('tmdb.apikey')
			if not self.tmdb_key: self.tmdb_key = 'edde6b5e41246ab79a2697cd125e1781'
			self.tvdb_key = getSetting('tvdb.apikey')
			if self.media_type == 'episode': self.user = str(self.imdb_user) + str(self.tvdb_key)
			else: self.user = str(self.tmdb_key)
			self.lang = control.apiLanguage()['tvdb']
			meta1 = dict((k, v) for k, v in iter(meta.items()) if v is not None and v != '') if meta else None
			meta2 = fetch_metacache([{'imdb': self.imdb, 'tmdb': self.tmdb, 'tvdb': self.tvdb}], self.lang, self.user)[0]
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
			poster, thumb, season_poster, fanart, banner, clearart, clearlogo, discart, meta = self.getMeta(meta)
			try:
				self.offset = Bookmarks().get(name=self.name, imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, year=self.year, runtime=meta.get('duration') if meta else 0)
			except:
				if self.debuglog:
					log_utils.log('Get offset failed in player play_source name:%s imdb: %s tmdb: %s tvdb: %s' % (str(self.name), imdb, tmdb, tvdb),1)
				self.offset = '0'
			if self.offset == '-1':
				if self.debuglog:
					log_utils.log('User requested playback cancel', level=log_utils.LOGDEBUG)
				control.notification(message=32328)
				return control.cancelPlayback()
			item = control.item(path=url)
			#item.setUniqueIDs(self.ids) #changed for kodi20 setinfo method
			setUniqueIDs = self.ids #changed for kodi20 setinfo method
			if self.media_type == 'episode':
				item.setArt({'tvshow.clearart': clearart, 'tvshow.clearlogo': clearlogo, 'tvshow.discart': discart, 'thumb': thumb, 'tvshow.poster': season_poster, 'season.poster': season_poster, 'tvshow.fanart': fanart})
			else:
				item.setArt({'clearart': clearart, 'clearlogo': clearlogo, 'discart': discart, 'thumb': thumb, 'poster': poster, 'fanart': fanart})
			#if 'castandart' in meta: item.setCast(meta.get('castandart', '')) #changed for kodi20 setinfo method
			#item.setInfo(type='video', infoLabels=control.metadataClean(meta))
			control.set_info(item, meta, setUniqueIDs=setUniqueIDs, fileNameandPath=url) #changed for kodi20 setinfo method

			item.setProperty('IsPlayable', 'true')
			playlistAdded = self.checkPlaylist(item)
			if debridPackCall: 
				control.player.play(url, item) # seems this is only way browseDebrid pack files will play and have meta marked as watched
				if self.debuglog:
					log_utils.log('debridPackCallPlayed file as player.play', level=log_utils.LOGDEBUG)
			else:
				if playlistAdded:
					control.player.play(control.playlist)
				else:
					control.resolve(int(argv[1]), True, item)
				if self.media_type == 'episode' and self.enable_playnext: self.addEpisodetoPlaylist()
				if self.debuglog:
					log_utils.log('Played file as resolve.', level=log_utils.LOGDEBUG)
			homeWindow.setProperty('script.trakt.ids', jsdumps(self.ids))
			self.keepAlive()
			homeWindow.clearProperty('script.trakt.ids')
		except:
			log_utils.error()
			return control.cancelPlayback()

	def addEpisodetoPlaylist(self):
		try:
			from resources.lib.menus import seasons, episodes
			seasons = seasons.Seasons().tmdb_list(tvshowtitle='', imdb='', tmdb=self.tmdb, tvdb='', art=None)
			seasons = [int(i['season']) for i in seasons]
			ep_data = [episodes.Episodes().get(self.meta.get('tvshowtitle'), self.meta.get('year'), self.imdb, self.tmdb, self.tvdb, self.meta, season=i, create_directory=False) for i in seasons]
			items = [i for e in ep_data for i in e if i.get('unaired') != 'true']
			index = next((idx for idx, i in enumerate(items) if i['season'] == int(self.season) and i['episode'] == int(self.episode)), None)
			if index is None: return
			try: item = items[index+1]
			except: return
			if item.get('season') and item.get('season') > int(self.season) and not self.multi_season: return
			items = episodes.Episodes().episodeDirectory([item], next=False, playlist=True)
			for url, li, folder in items: control.playlist.add(url=url, listitem=li)
		except: log_utils.error()

	def getMeta(self, meta):
		try:
			if not meta or ('videodb' in control.infoLabel('ListItem.FolderPath')): raise Exception()
			#
			def getDBID(meta):
				try:
					if self.media_type == 'movie':
						meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["title", "originaltitle", "uniqueid", "year", "premiered", "genre", "studio", "country", "runtime", "rating", "votes", "mpaa", "director", "writer", "cast", "plot", "plotoutline", "tagline", "thumbnail", "art", "file"]}, "id": 1}' % (self.year, str(int(self.year) + 1), str(int(self.year) - 1)))
						meta = jsloads(meta)['result']['movies']
						try:
							meta = [i for i in meta if (i.get('uniqueid', []).get('imdb', '') == self.imdb) or (i.get('uniqueid', []).get('unknown', '') == self.imdb)] # scraper now using "unknown"
						except:
							if self.debuglog:
								log_utils.log('Get Meta Failed in getMeta: %s' % str(meta), level=log_utils.LOGDEBUG)
							meta = None
						if meta: meta = meta[0]
						else: raise Exception()
						return meta.get('movieid')
					if self.media_type == 'episode':
						show_meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["title", "originaltitle", "uniqueid", "mpaa", "year", "genre", "runtime", "thumbnail", "file"]}, "id": 1}' % (self.year, str(int(self.year)+1), str(int(self.year)-1)))
						show_meta = jsloads(show_meta)['result']['tvshows']
						show_meta = [i for i in show_meta if i['uniqueid']['imdb'] == self.imdb]
						show_meta = [i for i in show_meta if (i.get('uniqueid', []).get('imdb', '') == self.imdb) or (i.get('uniqueid', []).get('unknown', '') == self.imdb)] # scraper now using "unknown"
						if show_meta: show_meta = show_meta[0]
						else: raise Exception()
						tvshowid = show_meta['tvshowid']
						if tvshowid:
							dbidmetameta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params":{"tvshowid": %d, "filter":{"and": [{"field": "season", "operator": "is", "value": "%s"}, {"field": "episode", "operator": "is", "value": "%s"}]}, "properties": ["showtitle", "title", "season", "episode", "firstaired", "runtime", "rating", "director", "writer", "cast", "plot", "thumbnail", "art", "file"]}, "id": 1}' % (tvshowid, self.season, self.episode))
							dbidmetameta = jsloads(meta)['result']['episodes']
						if dbidmetameta: meta = meta[0]
						else: raise Exception()
						return meta.get('episodeid')
				except:
					log_utils.error()
					return ''
			poster = meta.get('poster3') or meta.get('poster2') or meta.get('poster') #poster2 and poster3 may not be passed anymore
			thumb = meta.get('thumb')
			thumb = thumb or poster or control.addonThumb()
			season_poster = meta.get('season_poster') or poster
			fanart = meta.get('fanart')
			banner = meta.get('banner')
			clearart = meta.get('clearart')
			clearlogo = meta.get('clearlogo')
			discart = meta.get('discart')
			if 'mediatype' not in meta:
				meta.update({'mediatype': 'episode' if self.episode else 'movie'})
				if self.episode: meta.update({'tvshowtitle': self.title, 'season': self.season, 'episode': self.episode})
			self.DBID = getDBID(meta)
			return (poster, thumb, season_poster, fanart, banner, clearart, clearlogo, discart, meta)
		except: log_utils.error()
		try:
			def cleanLibArt(art):
				if not art: return ''
				art = unquote(art.replace('image://', ''))
				if art.endswith('/'): art = art[:-1]
				return art
			def sourcesDirMeta(metadata): # pass player minimal meta needed from lib pull
				if not metadata: return metadata
				allowed = ['mediatype', 'imdb', 'tmdb', 'tvdb', 'poster', 'season_poster', 'fanart', 'banner', 'clearart', 'clearlogo', 'discart', 'thumb', 'title', 'tvshowtitle', 'year', 'premiered', 'rating', 'plot', 'duration', 'mpaa', 'season', 'episode', 'castandrole']
				return {k: v for k, v in iter(metadata.items()) if k in allowed}
			poster, thumb, season_poster, fanart, banner, clearart, clearlogo, discart, meta = '', '', '', '', '', '', '', '', {'title': self.name}
			if self.media_type != 'movie': raise Exception()
			# do not add IMDBNUMBER as tmdb scraper puts their id in the key value
			meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["title", "originaltitle", "uniqueid", "year", "premiered", "genre", "studio", "country", "runtime", "rating", "votes", "mpaa", "director", "writer", "cast", "plot", "plotoutline", "tagline", "thumbnail", "art", "file"]}, "id": 1}' % (self.year, str(int(self.year) + 1), str(int(self.year) - 1)))
			meta = jsloads(meta)['result']['movies']
			try:
				meta = [i for i in meta if (i.get('uniqueid', []).get('imdb', '') == self.imdb) or (i.get('uniqueid', []).get('unknown', '') == self.imdb)] # scraper now using "unknown"
			except:
				if self.debuglog:
					log_utils.log('Get Meta Failed in getMeta: %s' % str(meta), level=log_utils.LOGDEBUG)
				meta = None
			if meta: meta = meta[0]
			else: raise Exception()
			if 'mediatype' not in meta: meta.update({'mediatype': 'movie'})
			if 'duration' not in meta: meta.update({'duration': meta.get('runtime')}) # Trakt scrobble resume needs this for lib playback
			if 'castandrole' not in meta: meta.update({'castandrole': [(i['name'], i['role']) for i in meta.get('cast')]})
			thumb = cleanLibArt(meta.get('art').get('thumb', ''))
			poster = cleanLibArt(meta.get('art').get('poster', '')) or self.poster
			fanart = cleanLibArt(meta.get('art').get('fanart', '')) or self.fanart
			banner = cleanLibArt(meta.get('art').get('banner', '')) # not sure this is even used by player
			clearart = cleanLibArt(meta.get('art').get('clearart', ''))
			clearlogo = cleanLibArt(meta.get('art').get('clearlogo', ''))
			discart = cleanLibArt(meta.get('art').get('discart'))
			if 'plugin' not in control.infoLabel('Container.PluginName'):
				self.DBID = meta.get('movieid')
			meta = sourcesDirMeta(meta)
			return (poster, thumb, '', fanart, banner, clearart, clearlogo, discart, meta)
		except: log_utils.error()
		try:
			if self.media_type != 'episode': raise Exception()
			# do not add IMDBNUMBER as tmdb scraper puts their id in the key value
			show_meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["title", "originaltitle", "uniqueid", "mpaa", "year", "genre", "runtime", "thumbnail", "file"]}, "id": 1}' % (self.year, str(int(self.year)+1), str(int(self.year)-1)))
			show_meta = jsloads(show_meta)['result']['tvshows']
			show_meta = [i for i in show_meta if i['uniqueid']['imdb'] == self.imdb]
			show_meta = [i for i in show_meta if (i.get('uniqueid', []).get('imdb', '') == self.imdb) or (i.get('uniqueid', []).get('unknown', '') == self.imdb)] # scraper now using "unknown"
			if show_meta: show_meta = show_meta[0]
			else: raise Exception()
			tvshowid = show_meta['tvshowid']
			meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params":{"tvshowid": %d, "filter":{"and": [{"field": "season", "operator": "is", "value": "%s"}, {"field": "episode", "operator": "is", "value": "%s"}]}, "properties": ["showtitle", "title", "season", "episode", "firstaired", "runtime", "rating", "director", "writer", "cast", "plot", "thumbnail", "art", "file"]}, "id": 1}' % (tvshowid, self.season, self.episode))
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
			thumb = cleanLibArt(meta.get('art').get('thumb', ''))
			season_poster = poster = cleanLibArt(meta.get('art').get('season.poster', '')) or self.poster
			fanart = cleanLibArt(meta.get('art').get('tvshow.fanart', '')) or self.poster
			banner = cleanLibArt(meta.get('art').get('tvshow.banner', '')) # not sure this is even used by player
			clearart = cleanLibArt(meta.get('art').get('tvshow.clearart', ''))
			clearlogo = cleanLibArt(meta.get('art').get('tvshow.clearlogo', ''))
			discart = cleanLibArt(meta.get('art').get('discart'))
			if 'plugin' not in control.infoLabel('Container.PluginName'):
				self.DBID = meta.get('episodeid')
			meta = sourcesDirMeta(meta)
			return (poster, thumb, season_poster, fanart, banner, clearart, clearlogo, discart, meta)
		except:
			log_utils.error()
			return (poster, thumb, season_poster, fanart, banner, clearart, clearlogo, discart, meta)

	def checkPlaylist(self, item):
		#just checking here for an empty playlist.
		try:
			#check if no playlist is currently added.
			if control.playlist.getposition() == -1 and self.media_type == 'episode':
				control.player.stop()
				control.playlist.clear()
				return self.singleItemPlaylist(item)
			else:
				return False
		except:
			return False

	def singleItemPlaylist(self, item):
		log_utils.log('singleItemPlaylist() started.', level=log_utils.LOGDEBUG)
		try:
			control.cancelPlayback()
			episodelabel = '%sx%02d %s' % (int(self.season), int(self.episode), self.meta.get('title'))
			if self.meta.get('title'):
				item.setLabel(episodelabel)
			from sys import argv
			newurl = item.getVideoInfoTag().getFilenameAndPath()
			log_utils.log('singleItemPlaylist() url: %s' % str(newurl), level=log_utils.LOGDEBUG)
			control.playlist.add(url=newurl, listitem=item)
			log_utils.log('singleItemPlaylist() returning true.', level=log_utils.LOGDEBUG)
			return True
		except:
			log_utils.log('singleItemPlaylist() exception: returning false', level=log_utils.LOGDEBUG)
			return False

	def getWatchedPercent(self):
		try:
			if self.isPlayback():
				try:
					position = self.getTime()
					if position != 0: self.current_time = position
					total_length = self.getTotalTime()
					if total_length != 0: self.media_length = total_length
				except: pass
			current_position = self.current_time
			#log_utils.log('getWatchedPercent() current_position: %s' % current_position, level=log_utils.LOGDEBUG)
			total_length = self.media_length
			#log_utils.log('getWatchedPercent() total_length: %s' % total_length, level=log_utils.LOGDEBUG)
			watched_percent = 0
			if int(total_length) != 0:
				try:
					watched_percent = float(current_position) / float(total_length) * 100
					if watched_percent > 100: watched_percent = 100
				except: log_utils.error()
			return watched_percent
		except:
			log_utils.error()
			return 0

	def getRemainingTime(self):
		remaining_time = 0
		if self.isPlayback():
			try:
				current_position = self.getTime()
				remaining_time = int(self.media_length) - int(current_position)
			except: pass
		return remaining_time

	def keepAlive(self):
		control.hide()
		control.sleep(200)
		pname = '%s.player.overlay' % control.addonInfo('id')
		homeWindow.clearProperty(pname)
		for i in range(0, 500):
			if self.isPlayback():
				control.closeAll()
				break
			xbmc.sleep(200)

		xbmc.sleep(5000)
		playlist_skip = False
		try: running_path = self.getPlayingFile() # original video that playlist playback started with
		except: running_path = ''
		if playerWindow.getProperty('umbrella.playlistStart_position'): pass
		else:
			if control.playlist.size() > 1: playerWindow.setProperty('umbrella.playlistStart_position', str(control.playlist.getposition()))

		while self.isPlayingVideo() and not control.monitor.abortRequested():
			try:
				if running_path != self.getPlayingFile(): # will not match if user hits "Next" so break from keepAlive()
					playlist_skip = True
					break

				try:
					self.current_time = self.getTime()
					self.media_length = self.getTotalTime()
				except: pass
				watcher = (self.getWatchedPercent() >= int(self.markwatched_percentage))
				property = homeWindow.getProperty(pname)

				if self.media_type == 'movie':
					try:
						if watcher and property != '5':
							homeWindow.setProperty(pname, '5')
							if self.debuglog:
								log_utils.log('Sending Movie to be marked as watched. IMDB: %s Title: %s Watch Percentage Used: %s Current Percentage: %s' % (self.imdb, self.title, self.markwatched_percentage, self.getWatchedPercent()), level=log_utils.LOGDEBUG)
							playcount.markMovieDuringPlayback(self.imdb, '5')
					except: pass
					xbmc.sleep(2000)
				elif self.media_type == 'episode':
					try:
						if watcher and property != '5':
							homeWindow.setProperty(pname, '5')
							if self.debuglog:
								log_utils.log('Sending Episode to be marked as watched. IMDB: %s TVDB: %s Season: %s Episode: %s Title: %s Watch Percentage Used: %s Current Percentage: %s' % (self.imdb, self.tvdb, self.season, self.episode, self.title, self.markwatched_percentage, self.getWatchedPercent()), level=log_utils.LOGDEBUG)
							playcount.markEpisodeDuringPlayback(self.imdb, self.tvdb, self.season, self.episode, '5')
						if self.enable_playnext and not self.play_next_triggered:
							if int(control.playlist.size()) > 1:
								if self.preScrape_triggered == False:
									xbmc.executebuiltin('RunPlugin(plugin://plugin.video.umbrella/?action=play_preScrapeNext)')
									self.preScrape_triggered = True
								remaining_time = self.getRemainingTime()
								if self.playnext_method== '0':
									if remaining_time < (self.playnext_time + 1) and remaining_time != 0:
										if self.debuglog:
											log_utils.log('Playnext triggered by method time. IMDB: %s Title: %s Time Used: %s Remaining Time: %s' % (self.imdb, self.title, self.playnext_time, remaining_time), level=log_utils.LOGDEBUG)
										xbmc.executebuiltin('RunPlugin(plugin://plugin.video.umbrella/?action=play_nextWindowXML)')
										self.play_next_triggered = True
								elif self.playnext_method== '1':	
									if self.getWatchedPercent() >= int(self.playnext_percentage) and remaining_time != 0:
										if self.debuglog:
											log_utils.log('Playnext triggered by method percentage. IMDB: %s Title: %s Percentage Used: %s Current Percentage: %s' % (self.imdb, self.title, self.playnext_percentage, self.getWatchedPercent()), level=log_utils.LOGDEBUG)
										xbmc.executebuiltin('RunPlugin(plugin://plugin.video.umbrella/?action=play_nextWindowXML)')
										self.play_next_triggered = True
								elif self.playnext_method== '2':
									if self.subtitletime is None:
										self.subtitletime = Subtitles().downloadForPlayNext(self.title, self.year, self.imdb, self.season, self.episode, self.media_length)
									if str(self.subtitletime) == 'default':
										if getSetting('playnext.sub.backupmethod')== '0': #subtitle failed use seconds as backup
											subtitletimeumb = int(getSetting('playnext.sub.seconds'))
											if remaining_time < (subtitletimeumb + 1) and remaining_time != 0:
												if self.debuglog:
													log_utils.log('Playnext triggered by method subtitle backup. IMDB: %s Title: %s Time Used: %s Current Time: %s' % (self.imdb, self.title, subtitletimeumb, remaining_time), level=log_utils.LOGDEBUG)
												xbmc.executebuiltin('RunPlugin(plugin://plugin.video.umbrella/?action=play_nextWindowXML)')
												self.play_next_triggered = True
										elif getSetting('playnext.sub.backupmethod') == '1': #subtitle failed use percentage as backup
											subtitletimeumb = int(getSetting('playnext.sub.percent'))
											if self.getWatchedPercent() >= int(subtitletimeumb) and remaining_time != 0:
												if self.debuglog:
													log_utils.log('Playnext triggered by method subtitle backup. IMDB: %s Title: %s Percent Used: %s Current Percent: %s' % (self.imdb, self.title, subtitletimeumb, self.getWatchedPercent()), level=log_utils.LOGDEBUG)
												xbmc.executebuiltin('RunPlugin(plugin://plugin.video.umbrella/?action=play_nextWindowXML)')
												self.play_next_triggered = True
									elif self.subtitletime != None and str(self.subtitletime) != 'default':
										if int(self.subtitletime) < 0:
											#negative time for subtitles
											self.subtitletime = int(getSetting('playnext.sub.seconds'))
										if int(self.subtitletime > 600 ):
											#subtitle time is greater than 10 minutes we need to use the default now.
											log_utils.log('Playnext triggered by method subtitle but the time is over 10 minutes. IMDB: %s Title: %s Time Attempting to Use Was: %s Changed to: %s Current Time: %s' % (self.imdb, self.title, self.subtitletime, int(getSetting('playnext.sub.seconds')), remaining_time), level=log_utils.LOGDEBUG)
											self.subtitletime = int(getSetting('playnext.sub.seconds'))
										if (remaining_time < (int(self.subtitletime) + 1) or remaining_time < int(self.playnext_min)) and remaining_time != 0:
											if self.debuglog:
													log_utils.log('Playnext triggered by method subtitle. IMDB: %s Title: %s Subtitle Time Used: %s Current Time: %s' % (self.imdb, self.title, self.subtitletime, remaining_time), level=log_utils.LOGDEBUG)
											xbmc.executebuiltin('RunPlugin(plugin://plugin.video.umbrella/?action=play_nextWindowXML)')
											self.play_next_triggered = True
									else:
										log_utils.error()
								else:
									if self.debuglog:
										log_utils.log('No match found for playnext method.', level=log_utils.LOGDEBUG)
					except: log_utils.error()
					xbmc.sleep(1000)

			except:
				log_utils.error()
				xbmc.sleep(1000)
		homeWindow.clearProperty(pname)
		if playlist_skip: pass
		else:
			if (int(self.current_time) > 180 and (self.getWatchedPercent() < int(self.markwatched_percentage))): # kodi is unreliable issuing callback "onPlayBackStopped" and "onPlayBackEnded"
				self.playbackStopped_triggered = True
				self.onPlayBackStopped()
			
	def isPlayingFile(self):
		if self._running_path is None or self._running_path.startswith("plugin://"):
			return False

	def isPlayback(self):
		# Kodi often starts playback where isPlaying() is true and isPlayingVideo() is false, since the video loading is still in progress, whereas the play is already started.
		try:
			playing = self.isPlaying()
		except:
			playing = False
		try:
			playingvideo = self.isPlayingVideo()
		except:
			playingvideo = False
		try:
			playTime = self.getTime() >= 0
		except:
			playTime = False
		#log_utils.log('isPlayBack Call isPlaying: %s isPlayingVideo: %s self.getTime: %s' % (playing, playingvideo, playTime))
		return playing and playingvideo and playTime

	def libForPlayback(self):
		if self.DBID is None: return
		try:
			if self.media_type == 'movie':
				rpc = '{"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": {"movieid": %s, "playcount": 1 }, "id": 1 }' % str(self.DBID)
			elif self.media_type == 'episode':
				rpc = '{"jsonrpc": "2.0", "method": "VideoLibrary.SetEpisodeDetails", "params": {"episodeid": %s, "playcount": 1 }, "id": 1 }' % str(self.DBID)
			control.jsonrpc(rpc)
		except: log_utils.error()

### Kodi player callback methods ###
	def onAVStarted(self): # Kodi docs suggests "Use onAVStarted() instead of onPlayBackStarted() as of v18"
		#control.sleep(200)
		for i in range(0, 500):
			if self.isPlayback():
				#control.closeAll() #i cannot remember what this was for.
				break
			else: control.sleep(200)
		homeWindow.clearProperty('umbrella.window_keep_alive')
		if self.offset != '0' and self.playback_resumed is False:
			control.sleep(200)
			if self.traktCredentials and getSetting('resume.source') == '1': # re-adjust the resume point since dialog is based on meta runtime vs. getTotalTime() and inaccurate
				try:
					total_time = self.getTotalTime()
					progress = float(fetch_bookmarks(self.imdb, self.tmdb, self.tvdb, self.season, self.episode))
					self.offset = (progress / 100) * total_time
				except: pass
			try:
				self.seekTime(self.offset)
			except:
				log_utils.log('Exception trying to seekTime() offset: %s'% self.offset, level=log_utils.LOGDEBUG)
			self.playback_resumed = True
		if getSetting('subtitles') == 'true': Subtitles().get(self.title, self.year, self.imdb, self.season, self.episode)
		if self.traktCredentials:
			trakt.scrobbleReset(imdb=self.imdb, tmdb=self.tmdb, tvdb=self.tvdb, season=self.season, episode=self.episode, refresh=False) # refresh issues container.refresh()
		log_utils.log('onAVStarted callback', level=log_utils.LOGDEBUG)

	def onPlayBackStarted(self):
		control.hide() #this is new.

	def onPlayBackSeek(self, time, seekOffset):
		seekOffset /= 1000

	def onPlayBackSeekChapter(self, chapter):
		log_utils.log('onPlayBackSeekChapter callback', level=log_utils.LOGDEBUG)

	def onQueueNextItem(self):
		log_utils.log('onQueueNextItem callback', level=log_utils.LOGDEBUG)

	def onPlayBackStopped(self):
		try:
			playerWindow.clearProperty('umbrella.preResolved_nextUrl')
			playerWindow.clearProperty('umbrella.playlistStart_position')
			homeWindow.clearProperty('umbrella.window_keep_alive')
			clear_local_bookmarks() # clear all umbrella bookmarks from kodi database
			control.playlist.clear()
			if not self.onPlayBackStopped_ran or (self.playbackStopped_triggered and not self.onPlayBackStopped_ran): # Kodi callback unreliable and often not issued
				self.onPlayBackStopped_ran = True
				self.playbackStopped_triggered = False
				Bookmarks().reset(self.current_time, self.media_length, self.name, self.year)
				if self.traktCredentials and (getSetting('trakt.scrobble') == 'true'):
					Bookmarks().set_scrobble(self.current_time, self.media_length, self.media_type, self.imdb, self.tmdb, self.tvdb, self.season, self.episode)
				watcher = self.getWatchedPercent()
				seekable = (int(self.current_time) > 180 and (watcher < int(self.markwatched_percentage)))
				if watcher >= int(self.markwatched_percentage): self.libForPlayback() # only write playcount to local lib
				if getSetting('crefresh') == 'true' and seekable:
					log_utils.log('container.refresh issued', level=log_utils.LOGDEBUG)
					control.refresh() #not all skins refresh after playback stopped
				#control.trigger_widget_refresh() # skinshortcuts handles widget refresh
				#control.checkforSkin(action='off')
				try:
					from resources.lib.modules import tools
					tools.delete_all_subs()
				except:
					log_utils.error()
				log_utils.log('onPlayBackStopped callback', level=log_utils.LOGDEBUG)
		except: log_utils.error()

	def onPlayBackEnded(self):
		Bookmarks().reset(self.current_time, self.media_length, self.name, self.year)
		self.libForPlayback()
		try:
			playingfile = Player.isPlaying()
		except:
			playingfile = False
		log_utils.log('onPlayBackEnded Playlist Position: %s isPlaying: %s' % (control.playlist.getposition(), playingfile), level=log_utils.LOGDEBUG)
		if control.playlist.getposition() == control.playlist.size() or control.playlist.size() == 1 or (control.playlist.getposition() == 0 and playerWindow.getProperty('playnextPlayPressed') == '0'):
			control.playlist.clear()
		log_utils.log('onPlayBackEnded callback', level=log_utils.LOGDEBUG)
		#control.checkforSkin(action='off')

	def onPlayBackError(self):
		playerWindow.clearProperty('umbrella.preResolved_nextUrl')
		playerWindow.clearProperty('umbrella.playlistStart_position')
		homeWindow.clearProperty('umbrella.window_keep_alive')

		Bookmarks().reset(self.current_time, self.media_length, self.name, self.year)
		log_utils.error()
		log_utils.log('onPlayBackError callback', level=log_utils.LOGDEBUG)
		#control.checkforSkin(action='off')
		sysexit(1)

	def onPlayBackPaused(self):
		log_utils.log('onPlayBackPaused callback', level=log_utils.LOGDEBUG)

class PlayNext(xbmc.Player):
	def __init__(self):
		super(PlayNext, self).__init__()
		self.enable_playnext = getSetting('enable.playnext') == 'true'
		self.stillwatching_count = int(getSetting('stillwatching.count'))
		self.playing_file = None
		self.providercache_hours = int(getSetting('cache.providers'))
		self.debuglog = control.setting('debug.level') == '1'
		self.playnext_method = control.setting('playnext.method')
		self.playnext_theme = getSetting('playnext.theme')

	def display_xml(self):
		try:
			self.playing_file = self.getPlayingFile()
		except:
			log_utils.error("Kodi did not return a playing file, killing playnext xml's")
			return
		if control.playlist.size() > 0 and control.playlist.getposition() != (control.playlist.size() - 1):
			if self.isStill_watching(): target = self.show_stillwatching_xml
			elif self.enable_playnext: target = self.show_playnext_xml
			else: return
			if self.playing_file != self.getPlayingFile(): return
			if not self.isPlayingVideo(): return
			if control.getCurrentWindowId != 12005: return
			target()

	def isStill_watching(self):
		# still_watching = float(control.playlist.getposition() + 1) / self.stillwatching_count # this does not work if you start playback on a divisible position with "stillwatching_count"
		playlistStart_position = playerWindow.getProperty('umbrella.playlistStart_position')
		if playlistStart_position: still_watching = float(control.playlist.getposition() - int(playlistStart_position) + 1) / self.stillwatching_count
		else: still_watching = float(control.playlist.getposition() + 1) / self.stillwatching_count
		if still_watching == 0: return False
		return still_watching.is_integer()

	def getNext_meta(self):
		try:
			
			from urllib.parse import parse_qsl
			current_position = control.playlist.getposition()
			next_url = control.playlist[current_position + 1].getPath()
			# next_url=videodb://tvshows/titles/16/2/571?season=2&tvshowid=16 # library playback returns this
			params = dict(parse_qsl(next_url.replace('?', '')))
			#next_meta = jsloads(params.get('meta')) if params.get('meta') else '' # not available for library playback
			next_meta = {}
			#tmdbhelperbs
			if 'plugin.video.themoviedb.helper' in next_url and not control.addonInstalled('service.upnext'):
				tmdb = params.get('tmdb_id')
				helper_season = params.get('season')
				helper_episode = params.get('episode')
				from resources.lib.menus import seasons, episodes
				seasons = seasons.Seasons().tmdb_list(tvshowtitle='', imdb='', tmdb=tmdb, tvdb='', art=None)
				for season in seasons:
					if season.get('season') != helper_season: continue
					else: break
				items = episodes.Episodes().tmdb_list(tvshowtitle=season.get('tvshowtitle'), imdb=season.get('imdb'), tmdb=tmdb, tvdb=season.get('tvdb'), meta=season, season=helper_season)
				for item in items:
					if str(item.get('episode')) != helper_episode: continue #episode is a string.... important to note.
					else: break
				next_meta = {'tvshowtitle': item.get('tvshowtitle'), 'title': item.get('title'), 'year': item.get('year'), 'premiered': item.get('premiered'), 'season': helper_season, 'episode': helper_episode, 'imdb': item.get('imdb'),
									'tmdb': item.get('tmdb'), 'tvdb': item.get('tvdb'), 'rating': item.get('rating'), 'landscape': '', 'fanart': item.get('fanart'), 'thumb': item.get('thumb'), 'duration': item.get('duration'), 'episode_type': item.get('episode_type')}
			elif 'plugin.video.umbrella' in next_url:
				next_meta = jsloads(params.get('meta')) if params.get('meta') else ''
			elif 'videob://' in next_url and not control.addonInstalled('service.upnext'):
				log_utils.log('Library not supported currently.', level=log_utils.LOGDEBUG)
		except:
			log_utils.error()
		return next_meta

	def show_playnext_xml(self):
		try:
			next_meta = self.getNext_meta()
			if not next_meta:
				log_utils.log('Next Meta Missing TMDB: %s Season: %s Episode: %s' % str(self.title, self.season, self.episode), level=log_utils.LOGDEBUG)
				raise Exception()
			#some changes here for playnext and themes.
			from resources.lib.windows.playnext import PlayNextXML
			if self.playnext_theme == '2'and control.skin in ('skin.auramod'):
				if self.debuglog:
					log_utils.log('Show Playnext Theme Netflix with Auramod Skin.', level=log_utils.LOGDEBUG)
				window = PlayNextXML('auraplaynext.xml', control.addonPath(control.addonId()), meta=next_meta)
			elif self.playnext_theme == '2'and control.skin not in ('skin.auramod'):
				if self.debuglog:
					log_utils.log('Show Playnext Theme Netflix No Aura.', level=log_utils.LOGDEBUG)
				window = PlayNextXML('auraplaynext2.xml', control.addonPath(control.addonId()), meta=next_meta)
			elif self.playnext_theme == '1' and (control.skin in ('skin.arctic.horizon.2')):
				if self.debuglog:
					log_utils.log('Show Playnext Theme AH2 with AH2 Skin', level=log_utils.LOGDEBUG)
				window = PlayNextXML('ahplaynext2.xml', control.addonPath(control.addonId()), meta=next_meta)
			elif self.playnext_theme == '1' and control.skin in ('skin.arctic.fuse'):
				if self.debuglog:
					log_utils.log('Show Playnext Theme AH2 with Arctic Fuse Skin.', level=log_utils.LOGDEBUG)
				window = PlayNextXML('ahplaynext3.xml', control.addonPath(control.addonId()), meta=next_meta)
			elif self.playnext_theme == '1' and control.skin not in ('skin.arctic.horizon.2') and control.skin not in ('skin.arctic.fuse'):
				if self.debuglog:
					log_utils.log('Show Playnext Theme AH2 without AH2 or AF.', level=log_utils.LOGDEBUG)
				window = PlayNextXML('ahplaynext2.xml', control.addonPath(control.addonId()), meta=next_meta)
			elif self.playnext_theme == '3':
				if self.debuglog:
					log_utils.log('Show Playnext Theme Arctic Fuse.', level=log_utils.LOGDEBUG)
				window = PlayNextXML('ahplaynext4.xml', control.addonPath(control.addonId()), meta=next_meta)
			else:
				if self.debuglog:
					log_utils.log('Show Playnext Theme Default Theme.', level=log_utils.LOGDEBUG)
				window = PlayNextXML('playnext.xml', control.addonPath(control.addonId()), meta=next_meta)
			window.run()
			del window
			self.play_next_triggered = True
		except:
			log_utils.error()
			self.play_next_triggered = True

	def show_stillwatching_xml(self):
		try:
			next_meta = self.getNext_meta()
			if not next_meta: raise Exception()
			if self.debuglog:
				log_utils.log('Show Playnext Still Watching. Meta is: %s' % str(next_meta), level=log_utils.LOGDEBUG)
			from resources.lib.windows.playnext_stillwatching import StillWatchingXML
			if self.playnext_theme == '2'and control.skin in ('skin.auramod'):
				window = StillWatchingXML('auraplaynext_stillwatching.xml', control.addonPath(control.addonId()), meta=next_meta)
			elif self.playnext_theme == '2'and control.skin not in ('skin.auramod'):
				window = StillWatchingXML('auraplaynext_stillwatching2.xml', control.addonPath(control.addonId()), meta=next_meta)
			elif self.playnext_theme == '1' and control.skin in ('skin.arctic.horizon.2'):
				window = StillWatchingXML('ahplaynext_stillwatching2.xml', control.addonPath(control.addonId()), meta=next_meta)
			elif self.playnext_theme == '1' and control.skin in ('skin.arctic.fuse'):
				window = StillWatchingXML('ahplaynext_stillwatching3.xml', control.addonPath(control.addonId()), meta=next_meta)
			elif self.playnext_theme == '1' and control.skin not in ('skin.arctic.horizon.2') and control.skin not in ('skin.arctic.fuse'):
				window = StillWatchingXML('ahplaynext_stillwatching2.xml', control.addonPath(control.addonId()), meta=next_meta)
			elif self.playnext_theme == '3':
				window = StillWatchingXML('ahplaynext_stillwatching4.xml', control.addonPath(control.addonId()), meta=next_meta)
			else:
				window = StillWatchingXML('playnext_stillwatching.xml', control.addonPath(control.addonId()), meta=next_meta)
			window.run()
			del window
			self.play_next_triggered = True
		except:
			log_utils.error()
			self.play_next_triggered = True

	def prescrapeNext(self):
		try:
			if control.playlist.size() > 0 and control.playlist.getposition() != (control.playlist.size() - 1):
				from resources.lib.modules import sources
				from resources.lib.database import providerscache
				next_meta=self.getNext_meta()
				if not next_meta: raise Exception()
				title = next_meta.get('title')
				year = next_meta.get('year')
				imdb = next_meta.get('imdb')
				tmdb = next_meta.get('tmdb')
				tvdb = next_meta.get('tvdb')
				season = next_meta.get('season')
				episode = next_meta.get('episode')
				tvshowtitle = next_meta.get('tvshowtitle')
				premiered = next_meta.get('premiered')
				next_sources = providerscache.get(sources.Sources().getSources, self.providercache_hours, title, year, imdb, tmdb, tvdb, str(season), str(episode), tvshowtitle, premiered, next_meta, True)
				if not self.isPlayingVideo():
					return playerWindow.clearProperty('umbrella.preResolved_nextUrl')
				sources.Sources().preResolve(next_sources, next_meta)
			else:
				playerWindow.clearProperty('umbrella.preResolved_nextUrl')
		except:
			log_utils.error()
			playerWindow.clearProperty('umbrella.preResolved_nextUrl')


class Subtitles:
	def __init__(self):
		self.debuglog = control.setting('debug.level') == '1'
		self.playnext_method = getSetting('playnext.method')

	def get(self, title, year, imdb, season, episode):
		try:
			import re
		except: return log_utils.error()
		try:
			quality = ['bluray', 'hdrip', 'brrip', 'bdrip', 'dvdrip', 'webrip', 'hdtv']
			langs = []
			langs.append(getSetting('subtitles.lang.1'))
			langs.append(getSetting('subtitles.lang.2'))

			try: subLang = xbmc.Player().getSubtitles()
			except: subLang = ''
			if subLang == 'gre': subLang = 'ell'
			if subLang == langs[0]: 
				if getSetting('subtitles.notification') == 'true':
					if Player().isPlayback():
						control.sleep(1000)
						control.notification(message=getLS(32393) % subLang.upper(), time=5000)
				return log_utils.log(getLS(32393) % subLang.upper(), level=log_utils.LOGDEBUG)
			try:
				subLangs = xbmc.Player().getAvailableSubtitleStreams()
				if 'gre' in subLangs: subLangs[subLangs.index('gre')] = 'ell'
				subLang = [i for i in subLangs if i == langs[0]][0]
			except: subLangs = subLang = ''
			if subLangs and subLang == langs[0]:
				control.sleep(1000)
				xbmc.Player().setSubtitleStream(subLangs.index(subLang))
				if getSetting('subtitles.notification') == 'true':
					if Player().isPlayback():
						control.sleep(1000)
						control.notification(message=getLS(32394) % subLang.upper(), time=5000)
				return log_utils.log(getLS(32394) % subLang.upper(), level=log_utils.LOGDEBUG)
			if opensubs.Opensubs().auth():
				log_utils.log('OpenSubs Authorized.', level=log_utils.LOGDEBUG)
			else:
				return control.notification(message=getLS(40509), time=5000)
			if not (season is None or episode is None):
				#tv show

				result = opensubs.Opensubs().getSubs(title, imdb, year, season, episode)
				fmt = ['hdtv']

			else:
				#movie

				result = opensubs.Opensubs().getSubs(title, imdb, year, season, episode)
				if not result: return
				try: vidPath = xbmc.Player().getPlayingFile()
				except: vidPath = ''
				fmt = re.split(r'\.|\(|\)|\[|\]|\s|\-', vidPath)
				fmt = [i.lower() for i in fmt]
				fmt = [i for i in fmt if i in quality]
			filter = []
			try: vidPath = xbmc.Player().getPlayingFile()
			except: vidPath = ''
			pFileName = unquote(os.path.basename(vidPath))
			pFileName = os.path.splitext(pFileName)[0]
			matches = []
			if result:
				for j in result:
					if season:
							if seas_ep_filter(season, episode, j['fileName']):
								seq = SequenceMatcher(None, pFileName.lower(), j['fileName'].lower())
								matches.append({'fileName': j['fileName'], 'fileID': j['fileID'],  'ratio': seq.ratio()})
					else:
						seq = SequenceMatcher(None, pFileName.lower(), j['fileName'].lower())
						matches.append({'fileName': j['fileName'], 'fileID': j['fileID'], 'ratio': seq.ratio()})
			matches.sort(key = lambda i: i['ratio'], reverse = True)

			filter = matches
			if not filter: 
				if getSetting('subtitles.notification') == 'true':
					return control.notification(message=getLS(32395))
				else:
					return None
			
			try: lang = xbmc.convertLanguage(getSetting('subtitles.lang.1'), xbmc.ISO_639_1)
			except: lang = getSetting('subtitles.lang.1')
			filename = filter[0]['fileName']
			if self.debuglog:
				log_utils.log('downloaded subtitle=%s' % filename, level=log_utils.LOGDEBUG)
			try:
				downloadURL, downloadFileName = opensubs.Opensubs().downloadSubs(filter[0]['fileID'], filter[0]['fileName'])
			except:
				return log_utils.log('Error getting downloadurl or filename from opensubs.')
			if not control.existsPath(control.subtitlesPath): control.makeFile(control.subtitlesPath)
			download_path = control.subtitlesPath
			subtitle = download_path
			
			def find(pattern, path):
				result = []
				for root, dirs, files in os.walk(path):
					for name in files:
						if fnmatch.fnmatch(name, pattern):
							result.append(os.path.join(root, name))
				return result
			def download_opensubs(downloadURL, downloadFileName):
				log_utils.log('downloading srt file from opensubs.', level=log_utils.LOGDEBUG)
				reqqqq = Request(downloadURL, headers={'User-Agent' : "Magic Browser"})
				http_response = urlopen(reqqqq)
				response = http_response.read()
				response = response.decode('utf-8')
				srtFile = os.path.join(download_path, downloadFileName+'.srt')
				file = open(srtFile, 'w')
				file.write(response)
				file.close()
			from resources.lib.modules import tools
			tools.delete_all_subs()
			try:
				download_opensubs(downloadURL, downloadFileName)
			except:
				log_utils.error()
			subtitles = find('*.srt', subtitle)
			subtitle_matches = []
			if len(subtitles) > 1:
				if season:
					for count, i in enumerate(subtitles):
						sFileName = unquote(os.path.basename(i))
						sFileName = os.path.splitext(sFileName)[0]
						if seas_ep_filter(season, episode, sFileName.lower()):
							seq = SequenceMatcher(None, pFileName.lower(), sFileName.lower())
							subtitle_matches.append({'fullPath': subtitles[count], 'matchRatio': seq.ratio()})
				else:
					for count, i in enumerate(subtitles):
						sFileName = unquote(os.path.basename(i))
						sFileName = os.path.splitext(sFileName)[0]
						seq = SequenceMatcher(None, pFileName.lower(), sFileName.lower())
						subtitle_matches.append({'fullPath': subtitles[count], 'matchRatio': seq.ratio()})
				subtitle_matches.sort(key = lambda i: i['matchRatio'], reverse = True)
				subtitles = subtitle_matches[0]['fullPath']
			else:
				subtitles = subtitles[0]
			xbmc.sleep(1000)
			tempFileName = control.joinPath(download_path,'TemporarySubs.%s.srt' % lang)
			f = open(subtitles,"r")
			f1 = open(tempFileName,"w")
			for line in f.readlines():
				f1.write(line)
			f.close()
			f1.close()
			
		
			xbmc.Player().setSubtitles(tempFileName)
			if getSetting('subtitles.notification') == 'true':
				if Player().isPlayback():
					control.sleep(500)
					control.notification(title=filename, message=getLS(40506) % lang.upper())
			if self.playnext_method== '2' and getSetting('enable.playnext')== 'true' and Player().subtitletime == None: #added to check for playnext using subtitles if downloaded.
				times = []
				pattern = r'(\d{2}:\d{2}:\d{2},d{3}$)|(\d{2}:\d{2}:\d{2})'
				with control.openFile(subtitles) as file:
					text = file.read()
					times = re.findall(pattern, text)
					times = times[len(times)-4][-1]
					file.close()
				if len(times) > 0:
					total_time = Player().media_length
					h, m, s = str(times).split(':')
					totalSeconds =  int(h) * 3600 + int(m) * 60 + int(s)
					Player().subtitletime = int(total_time) - int(totalSeconds)
				else:
					Player().subtitletime = 'default'
		except: log_utils.error()

	def downloadForPlayNext(self,  title, year, imdb, season, episode, media_length):
		try:
			try:
				import re
			except: return log_utils.error()
			try: lang = xbmc.convertLanguage(getSetting('subtitles.lang.1'), xbmc.ISO_639_1)
			except: lang = getSetting('subtitles.lang.1')
			if not control.existsPath(control.subtitlesPath): control.makeFile(control.subtitlesPath)
			download_path = control.subtitlesPath
			try:
				tempFileName = control.joinPath(download_path,'TemporarySubs.%s.srt' % lang)
				if os.path.isfile(tempFileName):
					log_utils.log('downloaded subtitle file found. getting time from file.', level=log_utils.LOGDEBUG)
					xbmc.sleep(1000)
					times = []
					pattern = r'(\d{2}:\d{2}:\d{2},d{3}$)|(\d{2}:\d{2}:\d{2})'
					with control.openFile(tempFileName) as file:
						text = file.read()
						times = re.findall(pattern, text)
						times = times[len(times)-4][-1]
						file.close()
					if len(times) > 0:
						total_time = media_length
						h, m, s = str(times).split(':')
						totalSeconds =  int(h) * 3600 + int(m) * 60 + int(s)
						playnextTime = int(total_time) - int(totalSeconds)
					else:
						log_utils.log('subtitle time not found returning default', level=log_utils.LOGDEBUG)
						playnextTime = 'default'
					return playnextTime
			except:
				log_utils.error()
				return 'default'
			try:
				quality = ['bluray', 'hdrip', 'brrip', 'bdrip', 'dvdrip', 'webrip', 'hdtv']

				langs = []
				langs.append(getSetting('subtitles.lang.1'))
				langs.append(getSetting('subtitles.lang.2'))

				if opensubs.Opensubs().auth():
					pass
				else:
					log_utils.log('opensubs is not authorized but is set for playnext. please authorize open subs in addon. returning default', level=log_utils.LOGDEBUG)
					return 'default'
				if not (season is None or episode is None):

					result = opensubs.Opensubs().getSubs(title, imdb, year, season, episode)
					fmt = ['hdtv']
					if not result:
						log_utils.log('no results from opensubs for title: %s imdb: %s year: %s season: %s episode: %s returning default' % (title, imdb, year, season, episode), level=log_utils.LOGDEBUG)
						return 'default'
				else:
					#movie

					result = opensubs.Opensubs().getSubs(title, imdb, year, season, episode)
					if not result: return
					try: vidPath = xbmc.Player().getPlayingFile()
					except: vidPath = ''
					fmt = re.split(r'\.|\(|\)|\[|\]|\s|\-', vidPath)
					fmt = [i.lower() for i in fmt]
					fmt = [i for i in fmt if i in quality]
				filter = []
				try: vidPath = xbmc.Player().getPlayingFile()
				except: vidPath = ''
				pFileName = unquote(os.path.basename(vidPath))
				pFileName = os.path.splitext(pFileName)[0]
				matches = []
				if result:
					for j in result:
						if season:
								if seas_ep_filter(season, episode, j['fileName']):
									seq = SequenceMatcher(None, pFileName.lower(), j['fileName'].lower())
									matches.append({'fileName': j['fileName'], 'fileID': j['fileID'],  'ratio': seq.ratio()})
						else:
							seq = SequenceMatcher(None, pFileName.lower(), j['fileName'].lower())
							matches.append({'fileName': j['fileName'], 'fileID': j['fileID'], 'ratio': seq.ratio()})
				matches.sort(key = lambda i: i['ratio'], reverse = True)

				filter = matches
				if not filter: return None
				
				try: lang = xbmc.convertLanguage(getSetting('subtitles.lang.1'), xbmc.ISO_639_1)
				except: lang = getSetting('subtitles.lang.1')
				filename = filter[0]['fileName']
				if self.debuglog:
					log_utils.log('downloaded subtitle=%s' % filename, level=log_utils.LOGDEBUG)

				downloadURL, downloadFileName = opensubs.Opensubs().downloadSubs(filter[0]['fileID'], filter[0]['fileName'])
				subtitle = control.transPath(download_path)
				
				def find(pattern, path):
					result = []
					for root, dirs, files in os.walk(path):
						for name in files:
							if fnmatch.fnmatch(name, pattern):
								result.append(os.path.join(root, name))
					return result
				def download_opensubs(downloadURL, downloadFileName):
					log_utils.log('downloading srt file from opensubs.', level=log_utils.LOGDEBUG)
					reqqqq = Request(downloadURL, headers={'User-Agent' : "Magic Browser"})
					http_response = urlopen(reqqqq)
					response = http_response.read()
					response = response.decode('utf-8')
					log_utils.log('built http_response opensubs.', level=log_utils.LOGDEBUG)
					srtFile = os.path.join(download_path, downloadFileName+'.srt')
					file = open(srtFile, 'w')
					log_utils.log('opened file %s' % srtFile, level=log_utils.LOGDEBUG)
					file.write(response)
					log_utils.log('wrote to file.', level=log_utils.LOGDEBUG)
					file.close()
				from resources.lib.modules import tools
				tools.delete_all_subs()
				download_opensubs(downloadURL, downloadFileName)
				subtitles = find('*.srt', subtitle)
				subtitle_matches = []
				if len(subtitles) > 1:
					if season:
						for count, i in enumerate(subtitles):
							sFileName = unquote(os.path.basename(i))
							sFileName = os.path.splitext(sFileName)[0]
							if seas_ep_filter(season, episode, sFileName.lower()):
								seq = SequenceMatcher(None, pFileName.lower(), sFileName.lower())
								subtitle_matches.append({'fullPath': subtitles[count], 'matchRatio': seq.ratio()})
					else:
						for count, i in enumerate(subtitles):
							sFileName = unquote(os.path.basename(i))
							sFileName = os.path.splitext(sFileName)[0]
							seq = SequenceMatcher(None, pFileName.lower(), sFileName.lower())
							subtitle_matches.append({'fullPath': subtitles[count], 'matchRatio': seq.ratio()})
					subtitle_matches.sort(key = lambda i: i['matchRatio'], reverse = True)
					subtitles = subtitle_matches[0]['fullPath']
				else:
					subtitles = subtitles[0]
				xbmc.sleep(1000)
				tempFileName = control.joinPath(download_path,'TemporarySubs2.%s.srt' % lang)
				f = open(subtitles,"r")
				f1 = open(tempFileName,"a")
				for line in f.readlines():
					f1.write(line)
				f.close()
				f1.close()
				xbmc.sleep(1000)
				times = []
				pattern = r'(\d{2}:\d{2}:\d{2},d{3}$)|(\d{2}:\d{2}:\d{2})'
				with control.openFile(tempFileName) as file:
					text = file.read()
					times = re.findall(pattern, text)
					times = times[len(times)-4][-1]
					file.close()
				if len(times) > 0:
					total_time = media_length
					h, m, s = str(times).split(':')
					totalSeconds =  int(h) * 3600 + int(m) * 60 + int(s)
					playnextTime = int(total_time) - int(totalSeconds)
				else:
					playnextTime = 'default'
				log_utils.log('Playnext Returning %s for time.' % playnextTime, level=log_utils.LOGDEBUG)
				return playnextTime
			except:
				log_utils.error()
				return 'default'
		except:
			log_utils.error()
			return 'default'


class Bookmarks:
	def __init__(self):
		self.debuglog = control.setting('debug.level') == '1'
		self.traktCredentials = trakt.getTraktCredentialsInfo()
	def get(self, name, imdb=None, tmdb=None, tvdb=None, season=None, episode=None, year='0', runtime=None, ck=False):
		markwatched_percentage = int(getSetting('markwatched.percent')) or 85
		offset = '0'
		scrobbble = 'Local Bookmark'
		if getSetting('bookmarks') != 'true': return offset
		if self.traktCredentials and getSetting('resume.source') == '1':
			scrobbble = 'Trakt Scrobble'
			try:
				if not runtime or runtime == 'None': return offset # TMDB sometimes return None as string. duration pulled from kodi library if missing from meta
				progress = float(fetch_bookmarks(imdb, tmdb, tvdb, season, episode))
				offset = (progress / 100) * runtime # runtime vs. media_length can differ resulting in 10-30sec difference using Trakt scrobble, meta providers report runtime in full minutes
				seekable = (2 <= progress <= int(markwatched_percentage))
				if not seekable: return '0'
			except:
				log_utils.error()
				return '0'
		else:
			try:
				dbcon = database.connect(control.bookmarksFile)
				dbcur = dbcon.cursor()
				dbcur.execute('''CREATE TABLE IF NOT EXISTS bookmark (idFile TEXT, timeInSeconds TEXT, Name TEXT, year TEXT, UNIQUE(idFile));''')
				if not year or year == 'None': return offset
				years = [str(year), str(int(year)+1), str(int(year)-1)]
				match = dbcur.execute('''SELECT * FROM bookmark WHERE Name="%s" AND year IN (%s)''' % (name, ','.join(i for i in years))).fetchone() # helps fix random cases where trakt and imdb, or tvdb, differ by a year for eps
			except:
				log_utils.error()
				return offset
			finally:
				dbcur.close() ; dbcon.close()
			if not match: return offset
			#offset = str(match[1]) 
			#changed to correct issue with resumes.
			offset = float(match[1])
		if ck: return offset
		minutes, seconds = divmod(float(offset), 60)
		hours, minutes = divmod(minutes, 60)
		label = '%02d:%02d:%02d' % (hours, minutes, seconds)
		label = getLS(32502) % label
		if getSetting('bookmarks.auto') == 'false':
			select = control.yesnocustomDialog(label, scrobbble, '', str(name), 'Cancel Playback', getLS(32503), getLS(32501))
			if select == 1: offset = '0'
			elif select == -1 or select == 2: offset = '-1'
		return offset

	def reset(self, current_time, media_length, name, year='0'):
		try:
			markwatched_percentage = int(getSetting('markwatched.percent')) or 85
			clear_local_bookmarks() # clear all umbrella bookmarks from kodi database
			if getSetting('bookmarks') != 'true' or media_length == 0 or current_time == 0: return
			timeInSeconds = str(current_time)
			seekable = (int(current_time) > 180 and (current_time / media_length) < (abs(float(markwatched_percentage) / 100)))
			idFile = md5()
			try: [idFile.update(str(i)) for i in name]
			except: [idFile.update(str(i).encode('utf-8')) for i in name]
			try: [idFile.update(str(i)) for i in year]
			except: [idFile.update(str(i).encode('utf-8')) for i in year]
			idFile = str(idFile.hexdigest())
			control.makeFile(control.dataPath)
			dbcon = database.connect(control.bookmarksFile)
			dbcur = dbcon.cursor()
			dbcur.execute('''CREATE TABLE IF NOT EXISTS bookmark (idFile TEXT, timeInSeconds TEXT, Name TEXT, year TEXT, UNIQUE(idFile));''')
			years = [str(year), str(int(year) + 1), str(int(year) - 1)]
			dbcur.execute('''DELETE FROM bookmark WHERE Name="%s" AND year IN (%s)''' % (name, ','.join(i for i in years))) #helps fix random cases where trakt and imdb, or tvdb, differ by a year for eps
			if seekable:
				dbcur.execute('''INSERT INTO bookmark Values (?, ?, ?, ?)''', (idFile, timeInSeconds, name, year))
				minutes, seconds = divmod(float(timeInSeconds), 60)
				hours, minutes = divmod(minutes, 60)
				label = ('%02d:%02d:%02d' % (hours, minutes, seconds))
				message = getLS(32660)
				if getSetting('localnotify') == 'true':
					control.notification(title=name, message=message + '(' + label + ')')
			dbcur.connection.commit()
			try: dbcur.close ; dbcon.close()
			except: pass
		except:
			log_utils.error()

	def set_scrobble(self, current_time, media_length, media_type, imdb='', tmdb='', tvdb='', season='', episode=''):
		try:
			markwatched_percentage = int(getSetting('markwatched.percent')) or 85
			if media_length == 0: return
			percent = float((current_time / media_length)) * 100
			seekable = (int(current_time) > 180 and (percent < int(markwatched_percentage)))
			if seekable: trakt.scrobbleMovie(imdb, tmdb, percent) if media_type == 'movie' else trakt.scrobbleEpisode(imdb, tmdb, tvdb, season, episode, percent)
			if percent >= int(markwatched_percentage): trakt.scrobbleReset(imdb, tmdb, tvdb, season, episode, refresh=False)
		except:
			log_utils.error()
