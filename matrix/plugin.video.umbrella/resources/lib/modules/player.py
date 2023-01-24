# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from hashlib import md5
from json import dumps as jsdumps, loads as jsloads
from sys import argv, exit as sysexit
from sqlite3 import dbapi2 as database
from urllib.parse import quote_plus
import xbmc
from resources.lib.database.cache import clear_local_bookmarks
from resources.lib.database.metacache import fetch as fetch_metacache
from resources.lib.database.traktsync import fetch_bookmarks
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules import playcount
from resources.lib.modules import trakt

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
		self.playlist_built = False
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
		self.onPlayBackEnded_ran = False
		self.prefer_tmdbArt = getSetting('prefer.tmdbArt') == 'true'
		self.playeronly = getSetting('use.playeronly') == 'true'
		self.subtitletime = None
		

	def play_source(self, title, year, season, episode, imdb, tmdb, tvdb, url, meta, debridPackCall=False):
		try:
			from sys import argv # some functions like ActivateWindow() throw invalid handle less this is imported here.
			if not url: raise Exception
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
			if not self.tmdb_key: self.tmdb_key = 'bc96b19479c7db6c8ae805744d0bdfe2'
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
			self.offset = Bookmarks().get(name=self.name, imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, year=self.year, runtime=meta.get('duration') if meta else 0)
			if self.offset == '-1':
				log_utils.log('User requested playback cancel', level=log_utils.LOGDEBUG)
				control.notification(message=32328)
				return control.cancelPlayback()

			item = control.item(path=url)
			item.setUniqueIDs(self.ids)
			if self.media_type == 'episode':
				item.setArt({'tvshow.clearart': clearart, 'tvshow.clearlogo': clearlogo, 'tvshow.discart': discart, 'thumb': thumb, 'tvshow.poster': season_poster, 'season.poster': season_poster, 'tvshow.fanart': fanart})
			else:
				item.setArt({'clearart': clearart, 'clearlogo': clearlogo, 'discart': discart, 'thumb': thumb, 'poster': poster, 'fanart': fanart})
			if 'castandart' in meta: item.setCast(meta.get('castandart', ''))
			item.setInfo(type='video', infoLabels=control.metadataClean(meta))
			item.setProperty('IsPlayable', 'true')
			if int(control.playlist.size()) < 1 and self.media_type == 'episode' and self.enable_playnext: #this is the change made for play next from widget.
				try:
					episodelabel = '%sx%02d %s' % (int(season), int(episode), self.meta.get('title'))
					if self.meta.get('title'):
						item.setLabel(episodelabel) #set the episode name here.
						control.playlist.add(url, item)
						playerWindow.setProperty('umbrella.playlistStart_position', str(0))
						control.player.play(control.playlist)
						log_utils.log('[ plugin.video.umbrella ] Played file as playlist', level=log_utils.LOGDEBUG)
					else:
						if debridPackCall and not self.playeronly: 
							control.player.play(url, item) # seems this is only way browseDebrid pack files will play and have meta marked as watched
							log_utils.log('Played file as player.play', level=log_utils.LOGDEBUG)
						elif self.playeronly:
							control.player.play(url) # using for crashing bug testing.
							log_utils.log('Played file as player.play with only the url', level=log_utils.LOGDEBUG)
						else: control.resolve(int(argv[1]), True, item)
				except:
					if debridPackCall and not self.playeronly: 
						control.player.play(url, item) # seems this is only way browseDebrid pack files will play and have meta marked as watched
						log_utils.log('Played file as player.play', level=log_utils.LOGDEBUG)
					elif self.playeronly:
						control.player.play(url) # using for crashing bug testing.
						log_utils.log('Played file as player.play with only the url', level=log_utils.LOGDEBUG)
					else: control.resolve(int(argv[1]), True, item)
			elif debridPackCall and not self.playeronly: 
				control.player.play(url, item) # seems this is only way browseDebrid pack files will play and have meta marked as watched
				log_utils.log('Played file as player.play', level=log_utils.LOGDEBUG)
			elif self.playeronly:
				control.player.play(url) # using for crashing bug testing.
				log_utils.log('Played file as player.play with only the url', level=log_utils.LOGDEBUG)
			else: 
				control.resolve(int(argv[1]), True, item)
				log_utils.log('Played file as resolve.', level=log_utils.LOGDEBUG)
			homeWindow.setProperty('script.trakt.ids', jsdumps(self.ids))
			self.keepAlive()
			homeWindow.clearProperty('script.trakt.ids')
		except:
			log_utils.error()
			return control.cancelPlayback()

	def getMeta(self, meta):
		try:
			if not meta or ('videodb' in control.infoLabel('ListItem.FolderPath')): raise Exception()
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
			return (poster, thumb, season_poster, fanart, banner, clearart, clearlogo, discart, meta)
		except: log_utils.error()
		try:
			def cleanLibArt(art):
				from urllib.parse import unquote
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
			meta = [i for i in meta if (i.get('uniqueid', []).get('imdb', '') == self.imdb) or (i.get('uniqueid', []).get('unknown', '') == self.imdb)] # scraper now using "unknown"
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

	def getWatchedPercent(self):
		if self.isPlayback():
			try:
				position = self.getTime()
				if position != 0: self.current_time = position
				total_length = self.getTotalTime()
				if total_length != 0: self.media_length = total_length
			except: pass
		current_position = self.current_time
		total_length = self.media_length
		watched_percent = 0
		if int(total_length) != 0:
			try:
				watched_percent = float(current_position) / float(total_length) * 100
				if watched_percent > 100: watched_percent = 100
			except: log_utils.error()
		return watched_percent

	def getRemainingTime(self):
		remaining_time = 0
		if self.isPlayback():
			try:
				current_position = self.getTime()
				remaining_time = int(self.media_length) - int(current_position)
			except: pass
		return remaining_time

	def keepAlive(self):
		pname = '%s.player.overlay' % control.addonInfo('id')
		homeWindow.clearProperty(pname)
		for i in range(0, 500):
			if self.isPlayback():
				control.closeAll()
				break
			xbmc.sleep(200)

		xbmc.sleep(5000)
		playlist_skip = False
		self.onPlayBackEnded_ran = False
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
							playcount.markMovieDuringPlayback(self.imdb, '5')
					except: pass
					xbmc.sleep(2000)
				elif self.media_type == 'episode':
					try:
						if watcher and property != '5':
							homeWindow.setProperty(pname, '5')
							playcount.markEpisodeDuringPlayback(self.imdb, self.tvdb, self.season, self.episode, '5')
						if self.enable_playnext and not self.play_next_triggered:
							if int(control.playlist.size()) > 1:
								if self.preScrape_triggered == False:
									xbmc.executebuiltin('RunPlugin(plugin://plugin.video.umbrella/?action=play_preScrapeNext)')
									self.preScrape_triggered = True
								remaining_time = self.getRemainingTime()
								if getSetting('playnext.method')== '0':
									if remaining_time < (self.playnext_time + 1) and remaining_time != 0:
										xbmc.executebuiltin('RunPlugin(plugin://plugin.video.umbrella/?action=play_nextWindowXML)')
										self.play_next_triggered = True
								elif getSetting('playnext.method')== '1':	
									if self.getWatchedPercent() >= int(self.playnext_percentage) and remaining_time != 0:
										xbmc.executebuiltin('RunPlugin(plugin://plugin.video.umbrella/?action=play_nextWindowXML)')
										self.play_next_triggered = True
								elif getSetting('playnext.method')== '2':
									if self.subtitletime is None:
										self.subtitletime = Subtitles().downloadForPlayNext(self.name, self.imdb, self.season, self.episode, self.media_length)
									if str(self.subtitletime) == 'default':
										if getSetting('playnext.sub.backupmethod')== '0': #subtitle failed use seconds as backup
											subtitletimeumb = int(getSetting('playnext.sub.seconds'))
											if remaining_time < (subtitletimeumb + 1) and remaining_time != 0:
												xbmc.executebuiltin('RunPlugin(plugin://plugin.video.umbrella/?action=play_nextWindowXML)')
												self.play_next_triggered = True
										elif getSetting('playnext.sub.backupmethod') == '1': #subtitle failed use percentage as backup
											subtitletimeumb = int(getSetting('playnext.sub.percent'))
											if self.getWatchedPercent() >= int(subtitletimeumb) and remaining_time != 0:
												xbmc.executebuiltin('RunPlugin(plugin://plugin.video.umbrella/?action=play_nextWindowXML)')
												self.play_next_triggered = True
									elif self.subtitletime != None and str(self.subtitletime) != 'default':
										if remaining_time < (int(self.subtitletime) + 1) and remaining_time != 0:
											xbmc.executebuiltin('RunPlugin(plugin://plugin.video.umbrella/?action=play_nextWindowXML)')
											self.play_next_triggered = True
									else:
										log_utils.error()
								else:
									log_utils.log('No match found for playnext method.', level=log_utils.LOGDEBUG)
							if int(control.playlist.size()) == 1 and self.playlist_built == False:
								self.buildPlaylist()
								self.playlist_built = True
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
			elif self.getWatchedPercent() >= int(self.markwatched_percentage): self._end_playback()

	def buildPlaylist(self):
		seasonPlaynext = False
		currentEpisode = self.episode
		currentSeason = self.season
		from resources.lib.menus import episodes
		items = episodes.Episodes().get(self.meta.get('tvshowtitle'), self.meta.get('year'), self.imdb, self.tmdb, self.tvdb, self.meta, self.season, create_directory=True)
		sysaddon, syshandle = 'plugin://plugin.video.umbrella/', int(argv[1])
		try:
			for count, i in enumerate(items):
				try:
					tvshowtitle, title, imdb, tmdb, tvdb = i.get('tvshowtitle'), i.get('title'), i.get('imdb', ''), i.get('tmdb', ''), i.get('tvdb', '')
					year, season, episode, premiered = i.get('year', ''), i.get('season'), i.get('episode'), i.get('premiered', '')
					runtime = i.get('duration')
					if 'label' not in i: i['label'] = title
					if (not i['label'] or i['label'] == '0'): label = '%sx%02d  %s %s' % (season, int(episode), 'Episode', episode)
					else: label = '%sx%02d  %s' % (season, int(episode), i['label'])
					systitle, systvshowtitle, syspremiered = quote_plus(title), quote_plus(tvshowtitle), quote_plus(premiered)
					meta = dict((k, v) for k, v in iter(i.items()) if v is not None and v != '')
					mediatype = 'episode'
					meta.update({'code': imdb, 'imdbnumber': imdb, 'mediatype': mediatype, 'tag': [imdb, tmdb]}) # "tag" and "tagline" for movies only, but works in my skin mod so leave
					try: meta.update({'title': i['label']})
					except: pass
					if self.prefer_tmdbArt: poster = meta.get('poster3') or meta.get('poster') or meta.get('poster2')
					else: poster = meta.get('poster2') or meta.get('poster3') or meta.get('poster')
					season_poster = meta.get('season_poster') or poster
					landscape = meta.get('landscape')
					fanart = ''
					thumb = meta.get('thumb') or landscape or fanart or season_poster
					icon = meta.get('icon') or season_poster or poster
					banner = meta.get('banner')
					art = {}
					art.update({'poster': season_poster, 'tvshow.poster': poster, 'season.poster': season_poster, 'fanart': fanart, 'icon': icon, 'thumb': thumb, 'banner': banner,
							'clearlogo': meta.get('clearlogo', ''), 'tvshow.clearlogo': meta.get('clearlogo', ''), 'clearart': meta.get('clearart', ''), 'tvshow.clearart': meta.get('clearart', ''), 'landscape': thumb})
					for k in ('metacache', 'poster2', 'poster3', 'fanart2', 'fanart3', 'banner2', 'banner3', 'trailer'): meta.pop(k, None)
					meta.update({'poster': poster, 'fanart': fanart, 'banner': banner, 'thumb': thumb, 'icon': icon})
					sysmeta = quote_plus(jsdumps(meta))
					url = '%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s' % (
											sysaddon, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, syspremiered, sysmeta)
					item = control.item(label=label, offscreen=True)
					if 'castandart' in i: item.setCast(i['castandart'])
					item.setUniqueIDs({'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb})
					info = {'episode': int(episode), 'sortepisode': int(episode), 'season': int(season), 'sortseason': int(season), 'year': str(year), 'premiered': i.get('premiered', ''), 'aired': meta.get('airtime', ''), 'imdbnumber': imdb, 'duration': runtime, 'dateadded': '', 'rating': i.get('rating'), 'votes': i.get('votes'), 'mediatype': self.media_type, 'title': i.get('title'), 'originaltitle': i.get('title'), 'sorttitle': i.get('title'), 'plot': i.get('plot'), 'plotoutline': i.get('plot'), 'tvshowtitle': tvshowtitle, 'director': [i.get('director')], 'writer': [i.get('writer')], 'genre': [i.get('genre')], 'studio': [i.get('studio')], 'playcount': 0}
					if int(episode) > int(currentEpisode):
						if not i.get('unaired')== 'true':
							item.setContentLookup(False)
							item.addStreamInfo("video", {})
							cm = []
							item.addContextMenuItems(cm)
							item.setInfo("video", info)
							item.setArt(art)
							item.setProperty('IsPlayable', 'true')
							item.setProperty('tvshow.tmdb_id', tmdb)
							control.playlist.add(url=url, listitem=item)
				except:
					log_utils.error()
		except:
			log_utils.error()

	def isPlayingFile(self):
		if self._running_path is None or self._running_path.startswith("plugin://"):
			return False

	def isPlayback(self):
		# Kodi often starts playback where isPlaying() is true and isPlayingVideo() is false, since the video loading is still in progress, whereas the play is already started.
		return self.isPlaying() and self.isPlayingVideo() and self.getTime() >= 0

	def libForPlayback(self):
		if self.DBID is None: return
		try:
			if self.media_type == 'movie':
				rpc = '{"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": {"movieid": %s, "playcount": 1 }, "id": 1 }' % str(self.DBID)
			elif self.media_type == 'episode':
				rpc = '{"jsonrpc": "2.0", "method": "VideoLibrary.SetEpisodeDetails", "params": {"episodeid": %s, "playcount": 1 }, "id": 1 }' % str(self.DBID)
			control.jsonrpc(rpc)
		except: log_utils.error()

	def _end_playback(self):
		self.onPlayBackEnded()
		self.onPlayBackEnded_ran = True

### Kodi player callback methods ###
	def onAVStarted(self): # Kodi docs suggests "Use onAVStarted() instead of onPlayBackStarted() as of v18"
		for i in range(0, 500):
			if self.isPlayback():
				control.closeAll()
				break
			else: control.sleep(200)
		if self.offset != '0' and self.playback_resumed is False:
			control.sleep(200)
			if getSetting('trakt.scrobble') == 'true' and getSetting('resume.source') == '1': # re-adjust the resume point since dialog is based on meta runtime vs. getTotalTime() and inaccurate
				try:
					total_time = self.getTotalTime()
					progress = float(fetch_bookmarks(self.imdb, self.tmdb, self.tvdb, self.season, self.episode))
					self.offset = (progress / 100) * total_time
				except: pass
			self.seekTime(self.offset)
			self.playback_resumed = True
		if getSetting('subtitles') == 'true': Subtitles().get(self.name, self.imdb, self.season, self.episode)
		if self.traktCredentials:
			trakt.scrobbleReset(imdb=self.imdb, tmdb=self.tmdb, tvdb=self.tvdb, season=self.season, episode=self.episode, refresh=False) # refresh issues container.refresh()
		log_utils.log('onAVStarted callback', level=log_utils.LOGDEBUG)

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
			clear_local_bookmarks() # clear all umbrella bookmarks from kodi database
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
				control.playlist.clear()
				#control.trigger_widget_refresh() # skinshortcuts handles widget refresh
				#control.checkforSkin(action='off')
				log_utils.log('onPlayBackStopped callback', level=log_utils.LOGDEBUG)
		except: log_utils.error()

	def onPlayBackEnded(self):
		if self.onPlayBackEnded_ran: return
		Bookmarks().reset(self.current_time, self.media_length, self.name, self.year)
		self.libForPlayback()
		if control.playlist.getposition() == control.playlist.size() or control.playlist.size() == 1:
			control.playlist.clear()
		log_utils.log('onPlayBackEnded callback', level=log_utils.LOGDEBUG)
		#control.checkforSkin(action='off')

	def onPlayBackError(self):
		playerWindow.clearProperty('umbrella.preResolved_nextUrl')
		playerWindow.clearProperty('umbrella.playlistStart_position')

		Bookmarks().reset(self.current_time, self.media_length, self.name, self.year)
		log_utils.error()
		log_utils.log('onPlayBackError callback', level=log_utils.LOGDEBUG)
		#control.checkforSkin(action='off')
		sysexit(1)
##############################

class PlayNext(xbmc.Player):
	def __init__(self):
		super(PlayNext, self).__init__()
		self.enable_playnext = getSetting('enable.playnext') == 'true'
		self.stillwatching_count = int(getSetting('stillwatching.count'))
		self.playing_file = None
		self.providercache_hours = int(getSetting('cache.providers'))

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
		playlistStart_position = int(playerWindow.getProperty('umbrella.playlistStart_position'))
		if playlistStart_position: still_watching = float(control.playlist.getposition() - playlistStart_position + 1) / self.stillwatching_count
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
									'tmdb': item.get('tmdb'), 'tvdb': item.get('tvdb'), 'rating': item.get('rating'), 'landscape': '', 'fanart': item.get('fanart'), 'thumb': item.get('thumb'), 'duration': item.get('duration')}
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
			if not next_meta: raise Exception()
			#some changes here for playnext and themes.
			from resources.lib.windows.playnext import PlayNextXML
			if getSetting('playnext.theme') == '2'and control.skin in ('skin.auramod'):
				window = PlayNextXML('auraplaynext.xml', control.addonPath(control.addonId()), meta=next_meta)
			if getSetting('playnext.theme') == '2'and control.skin not in ('skin.auramod'):
				window = PlayNextXML('auraplaynext2.xml', control.addonPath(control.addonId()), meta=next_meta)
			elif getSetting('playnext.theme') == '1' and control.skin in ('skin.arctic.horizon.2'):
				window = PlayNextXML('ahplaynext.xml', control.addonPath(control.addonId()), meta=next_meta)
			elif getSetting('playnext.theme') == '1' and control.skin not in ('skin.arctic.horizon.2'):
				window = PlayNextXML('ahplaynext2.xml', control.addonPath(control.addonId()), meta=next_meta)
			else:
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
			from resources.lib.windows.playnext_stillwatching import StillWatchingXML
			if getSetting('playnext.theme') == '2'and control.skin not in ('skin.auramod'):
				window = StillWatchingXML('auraplaynext_stillwatching2.xml', control.addonPath(control.addonId()), meta=next_meta)
			if getSetting('playnext.theme') == '2'and control.skin in ('skin.auramod'):
				window = StillWatchingXML('auraplaynext_stillwatching.xml', control.addonPath(control.addonId()), meta=next_meta)
			elif getSetting('playnext.theme') == '1' and control.skin in ('skin.arctic.horizon.2'):
				window = StillWatchingXML('ahplaynext_stillwatching.xml', control.addonPath(control.addonId()), meta=next_meta)
			elif getSetting('playnext.theme') == '1' and control.skin not in ('skin.arctic.horizon.2'):
				window = StillWatchingXML('ahplaynext_stillwatching2.xml', control.addonPath(control.addonId()), meta=next_meta)
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
	def get(self, name, imdb, season, episode):
		try:
			import gzip, codecs
			from io import BytesIO
			import re, base64
			import xmlrpc.client as xmlrpc_client
		except: return log_utils.error()
		try:
			langDict = {'Afrikaans': 'afr', 'Albanian': 'alb', 'Arabic': 'ara', 'Armenian': 'arm', 'Basque': 'baq', 'Bengali': 'ben',
			'Bosnian': 'bos', 'Breton': 'bre', 'Bulgarian': 'bul', 'Burmese': 'bur', 'Catalan': 'cat', 'Chinese': 'chi', 'Croatian': 'hrv',
			'Czech': 'cze', 'Danish': 'dan', 'Dutch': 'dut', 'English': 'eng', 'Esperanto': 'epo', 'Estonian': 'est', 'Finnish': 'fin',
			'French': 'fre', 'Galician': 'glg', 'Georgian': 'geo', 'German': 'ger', 'Greek': 'ell', 'Hebrew': 'heb', 'Hindi': 'hin',
			'Hungarian': 'hun', 'Icelandic': 'ice', 'Indonesian': 'ind', 'Italian': 'ita', 'Japanese': 'jpn', 'Kazakh': 'kaz', 'Khmer': 'khm',
			'Korean': 'kor', 'Latvian': 'lav', 'Lithuanian': 'lit', 'Luxembourgish': 'ltz', 'Macedonian': 'mac', 'Malay': 'may',
			'Malayalam': 'mal', 'Manipuri': 'mni', 'Mongolian': 'mon', 'Montenegrin': 'mne', 'Norwegian': 'nor', 'Occitan': 'oci',
			'Persian': 'per', 'Polish': 'pol', 'Portuguese': 'por,pob', 'Portuguese(Brazil)': 'pob,por', 'Romanian': 'rum', 'Russian': 'rus',
			'Serbian': 'scc', 'Sinhalese': 'sin', 'Slovak': 'slo', 'Slovenian': 'slv', 'Spanish': 'spa', 'Swahili': 'swa', 'Swedish': 'swe',
			'Syriac': 'syr', 'Tagalog': 'tgl', 'Tamil': 'tam', 'Telugu': 'tel', 'Thai': 'tha', 'Turkish': 'tur', 'Ukrainian': 'ukr', 'Urdu': 'urd'}
			codePageDict = {'ara': 'cp1256', 'ar': 'cp1256', 'ell': 'cp1253', 'el': 'cp1253', 'heb': 'cp1255',
									'he': 'cp1255', 'tur': 'cp1254', 'tr': 'cp1254', 'rus': 'cp1251', 'ru': 'cp1251'}
			quality = ['bluray', 'hdrip', 'brrip', 'bdrip', 'dvdrip', 'webrip', 'hdtv']

			langs = langDict[getSetting('subtitles.lang.1')].split(',')
			langs = langs + langDict[getSetting('subtitles.lang.2')].split(',')

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

			server = xmlrpc_client.Server('https://api.opensubtitles.org/xml-rpc', verbose=0)
			token = server.LogIn('', '', 'en', 'XBMC_Subtitles_Unofficial_v5.2.14') # service.subtitles.opensubtitles_by_opensubtitles
			if 'token' not in token:
				return log_utils.log('OpenSubtitles Login failed: token=%s' % token, level=log_utils.LOGWARNING)
			else: 
				token = token['token']

			sublanguageid = ','.join(langs)
			imdbid = re.sub(r'[^0-9]', '', imdb)
			if not (season is None or episode is None):
				result = server.SearchSubtitles(token, [{'sublanguageid': sublanguageid, 'imdbid': imdbid, 'season': season, 'episode': episode}])['data']
				fmt = ['hdtv']
			else:
				result = server.SearchSubtitles(token, [{'sublanguageid': sublanguageid, 'imdbid': imdbid}])['data']
				try: vidPath = xbmc.Player().getPlayingFile()
				except: vidPath = ''
				fmt = re.split(r'\.|\(|\)|\[|\]|\s|\-', vidPath)
				fmt = [i.lower() for i in fmt]
				fmt = [i for i in fmt if i in quality]
			filter = []
			result = [i for i in result if i['SubSumCD'] == '1']
			for lang in langs:
				filter += [i for i in result if i['SubLanguageID'] == lang and any(x in i['MovieReleaseName'].lower() for x in fmt)]
				filter += [i for i in result if i['SubLanguageID'] == lang and any(x in i['MovieReleaseName'].lower() for x in quality)]
				filter += [i for i in result if i['SubLanguageID'] == lang]
			if not filter: return control.notification(message=getLS(32395))

			try: lang = xbmc.convertLanguage(filter[0]['SubLanguageID'], xbmc.ISO_639_1)
			except: lang = filter[0]['SubLanguageID']
			filename = filter[0]['SubFileName']
			log_utils.log('downloaded subtitle=%s' % filename, level=log_utils.LOGDEBUG)

			content = [filter[0]['IDSubtitleFile'],]
			content = server.DownloadSubtitles(token, content)
			content = base64.b64decode(content['data'][0]['data'])
			content = gzip.GzipFile(fileobj=BytesIO(content)).read()
			download_path = 'special://temp/'
			subtitle = control.transPath(download_path)
			subtitle = control.joinPath(subtitle, 'TemporarySubs.%s.srt' % lang)

			if getSetting('subtitles.utf') == 'true':
				codepage = codePageDict.get(lang, '')
				if codepage and not filter[0].get('SubEncoding', '').lower() == 'utf-8':
					try:
						content_encoded = codecs.decode(content, codepage)
						content = codecs.encode(content_encoded, 'utf-8')
					except: pass
			file = control.openFile(subtitle, 'w')
			file.write(content)
			file.close()
			xbmc.sleep(1000)
			xbmc.Player().setSubtitles(subtitle)
			if getSetting('subtitles.notification') == 'true':
				if Player().isPlayback():
					control.sleep(500)
					control.notification(title=filename, message=getLS(32191) % lang.upper())
			if getSetting('playnext.method')== '2' and getSetting('enable.playnext')== 'true' and Player().subtitletime == None: #added to check for playnext using subtitles if downloaded.
				times = []
				pattern = r'(\d{2}:\d{2}:\d{2},d{3}$)|(\d{2}:\d{2}:\d{2})'
				with control.openFile(subtitle) as file:
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

	def downloadForPlayNext(self, name, imdb, season, episode, media_length):
		try:
			import gzip
			from io import BytesIO
			import re, base64
			import xmlrpc.client as xmlrpc_client
		except: 
			log_utils.error()
			return 'default'
		langDict = {'English': 'eng','Spanish': 'esp'}
		quality = ['bluray', 'hdrip', 'brrip', 'bdrip', 'dvdrip', 'webrip', 'hdtv']
		langs = langDict['English'].split(',')
		try:
			server = xmlrpc_client.Server('https://api.opensubtitles.org/xml-rpc', verbose=0)
			token = server.LogIn('', '', 'en', 'XBMC_Subtitles_Unofficial_v5.2.14') # service.subtitles.opensubtitles_by_opensubtitles
			if 'token' not in token:
				log_utils.log('OpenSubtitles Login failed: token=%s' % token, level=log_utils.LOGWARNING)
				return 'default'
			else: 
				token = token['token']
			sublanguageid = ','.join(langs)
			imdbid = re.sub(r'[^0-9]', '', imdb)
			if not (season is None or episode is None):
				result = server.SearchSubtitles(token, [{'sublanguageid': sublanguageid, 'imdbid': imdbid, 'season': season, 'episode': episode}])['data']
				fmt = ['hdtv']
			else:
				result = server.SearchSubtitles(token, [{'sublanguageid': sublanguageid, 'imdbid': imdbid}])['data']
				try: vidPath = xbmc.Player().getPlayingFile()
				except: vidPath = ''
				fmt = re.split(r'\.|\(|\)|\[|\]|\s|\-', vidPath)
				fmt = [i.lower() for i in fmt]
				fmt = [i for i in fmt if i in quality]
			filter = []
			result = [i for i in result if i['SubSumCD'] == '1']
			for lang in langs:
				filter += [i for i in result if i['SubLanguageID'] == lang and any(x in i['MovieReleaseName'].lower() for x in fmt)]
				filter += [i for i in result if i['SubLanguageID'] == lang and any(x in i['MovieReleaseName'].lower() for x in quality)]
				filter += [i for i in result if i['SubLanguageID'] == lang]
			if not filter: 
				log_utils.log('nothing found for playnext subtitle that matches use fallback', level=log_utils.LOGDEBUG)
				return 'default'
			try: lang = xbmc.convertLanguage(filter[0]['SubLanguageID'], xbmc.ISO_639_1)
			except: lang = filter[0]['SubLanguageID']
			filename = filter[0]['SubFileName']
			content = [filter[0]['IDSubtitleFile'],]
			content = server.DownloadSubtitles(token, content)
			content = base64.b64decode(content['data'][0]['data'])
			content = gzip.GzipFile(fileobj=BytesIO(content)).read()
			download_path = jsloads(control.jsonrpc('{"jsonrpc":"2.0", "method":"Settings.GetSettingValue", "params":{"setting":"subtitles.custompath"}, "id":1}')).get('result').get('value')
			download_path = 'special://subtitles/' if download_path != '' else 'special://temp/'
			subtitle = control.joinPath(download_path, 'TemporarySubs.%s.srt' % lang)
			file = control.openFile(subtitle, 'w')
			file.write(content)
			file.close()
			xbmc.sleep(1000)
			times = []
			pattern = r'(\d{2}:\d{2}:\d{2},d{3}$)|(\d{2}:\d{2}:\d{2})'
			with control.openFile(subtitle) as file:
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
			return playnextTime
		except:
			log_utils.error()
			return 'default'


class Bookmarks:
	def get(self, name, imdb=None, tmdb=None, tvdb=None, season=None, episode=None, year='0', runtime=None, ck=False):
		markwatched_percentage = int(getSetting('markwatched.percent')) or 85
		offset = '0'
		scrobbble = 'Local Bookmark'
		if getSetting('bookmarks') != 'true': return offset
		if getSetting('trakt.scrobble') == 'true' and getSetting('resume.source') == '1':
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
