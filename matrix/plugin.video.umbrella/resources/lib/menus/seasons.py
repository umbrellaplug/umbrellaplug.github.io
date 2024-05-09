# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from datetime import datetime
from json import dumps as jsdumps, loads as jsloads
import re
from urllib.parse import quote_plus
from resources.lib.database import cache
from resources.lib.indexers.tmdb import TVshows as tmdb_indexer
from resources.lib.indexers.fanarttv import FanartTv
from resources.lib.modules import cleangenre
from resources.lib.modules import control
from resources.lib.modules.playcount import getSeasonIndicators, getSeasonOverlay, getSeasonCount
from resources.lib.modules import trakt
from resources.lib.modules import views

getLS = control.lang
getSetting = control.setting


class Seasons:
	def __init__(self):
		self.list = []
		self.lang = control.apiLanguage()['tmdb']
		self.enable_fanarttv = getSetting('enable.fanarttv') == 'true'
		self.prefer_tmdbArt = getSetting('prefer.tmdbArt') == 'true'
		self.date_time = datetime.now()
		self.today_date = (self.date_time).strftime('%Y-%m-%d')
		self.tmdb_poster_path = 'https://image.tmdb.org/t/p/w342'
		self.trakt_user = getSetting('trakt.user.name').strip()
		self.traktCredentials = trakt.getTraktCredentialsInfo()
		self.showunaired = getSetting('showunaired') == 'true'
		self.unairedcolor = getSetting('unaired.identify')
		self.showspecials = getSetting('tv.specials') == 'true'
		self.tmdblist_hours = int(getSetting('cache.tmdblist'))
		self.hide_watched_in_widget = getSetting('enable.umbrellahidewatched') == 'true'
		self.useFullContext = getSetting('enable.umbrellawidgetcontext') == 'true'

	def get(self, tvshowtitle, year, imdb, tmdb, tvdb, art, idx=True, create_directory=True): # may need to add a cache duration over-ride param to pass
		self.list = []
		if idx:
			self.list = cache.get(self.tmdb_list, 720, tvshowtitle, imdb, tmdb, tvdb, art)
			if self.list:
				if not self.list[0]['status'].lower() in ('ended', 'canceled'):
					self.list = cache.get(self.tmdb_list, self.tmdblist_hours, tvshowtitle, imdb, tmdb, tvdb, art)
			if self.list is None: self.list = []
			if create_directory: self.seasonDirectory(self.list)
			return self.list
		else:
			self.list = self.tmdb_list(tvshowtitle, imdb, tmdb, tvdb, art)
			return self.list

	def tmdb_list(self, tvshowtitle, imdb, tmdb, tvdb, art):
#### -- Missing id's lookup -- ####
		trakt_ids = None
		if (not tmdb or not tvdb) and imdb: trakt_ids = trakt.IdLookup('imdb', imdb, 'show')
		elif (not tmdb or not imdb) and tvdb: trakt_ids = trakt.IdLookup('tvdb', tvdb, 'show')
		if trakt_ids:
			if not imdb: imdb = str(trakt_ids.get('imdb', '')) if trakt_ids.get('imdb') else ''
			if not tmdb: tmdb = str(trakt_ids.get('tmdb', '')) if trakt_ids.get('tmdb') else ''
			if not tvdb: tvdb = str(trakt_ids.get('tvdb', '')) if trakt_ids.get('tvdb') else ''
		if not tmdb and (imdb or tvdb):
			try:
				result = cache.get(tmdb_indexer().IdLookup, 96, imdb, tvdb)
				tmdb = str(result.get('id')) if result else ''
			except:
				if getSetting('debug.level') != '1': return
				from resources.lib.modules import log_utils
				return log_utils.log('tvshowtitle: (%s) missing tmdb_id: ids={imdb: %s, tmdb: %s, tvdb: %s}' % (tvshowtitle, imdb, tmdb, tvdb), __name__, log_utils.LOGDEBUG) # log TMDb shows that they do not have
#################################
		list = []
		showSeasons = tmdb_indexer().get_showSeasons_meta(tmdb)
		if not showSeasons: return
		if not showSeasons.get('imdb'): showSeasons['imdb'] = imdb # use value passed from tvshows super_info() due to extensive ID lookups
		if showSeasons.get('imdb','') != imdb: showSeasons['imdb'] = imdb
		if not showSeasons.get('tvdb'): showSeasons['tvdb'] = tvdb
		if art: art = jsloads(art) # prob better off leaving this as it's own dict so seasonDirectory list builder can just pull that out and pass to .setArt()
		for item in showSeasons['seasons']: # seasons not parsed in tmdb module so ['seasons'] here is direct json response
			try:
				if not self.showspecials and item['season_number'] == 0: continue
				values = {}
				values.update(showSeasons)
				values['mediatype'] = 'season'
				values['premiered'] = str(item.get('air_date', '')) if item.get('air_date') else ''
				values['year'] = showSeasons['year'] # use show year not season year.  In seasonDirecotry send InfoLabels year pulled from premiered only.
				values['unaired'] = ''
				try:
					if values['status'].lower() == 'ended': pass # season level unaired
					elif not values['premiered']:
						values['unaired'] = 'true'
						# if not self.showunaired: continue # remove at seasonDirectory() instead so cache clear not required on setting change
						pass
					elif int(re.sub(r'[^0-9]', '', str(values['premiered']))) > int(re.sub(r'[^0-9]', '', str(self.today_date))):
						values['unaired'] = 'true'
						# if not self.showunaired: continue # remove at seasonDirectory() instead so cache clear not required on setting change
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
				values['total_episodes'] = item['episode_count'] # will be total for the specific season only
				values['season_title'] = item['name']
				values['title']= item['name']
				values['plot'] = item['overview'] or showSeasons['plot']
				try: values['poster'] = self.tmdb_poster_path + item['poster_path']
				except: values['poster'] = ''
				if not values['poster'] and art: values['poster'] = art['poster'] if 'poster' in art else ''
				values['season_poster'] = values['poster']
				values['season'] = str(int(item['season_number']))
				if self.enable_fanarttv: 
					values['season_poster2'] = FanartTv().get_season_poster(tvdb, values['season'])
					lanscapebefore = FanartTv().get_season_landscape(tvdb, values['season'])
					if lanscapebefore == '':
						values['landscape2'] = item['landscape']
					else:
						values['landscape2'] = lanscapebefore
				if art:
					values['fanart'] = art['fanart']
					values['icon'] = art['icon']
					values['thumb'] = art['thumb'] # thumb here is show_poster from show level TMDb module
					values['banner'] = art['banner']
					values['clearlogo'] = art['clearlogo']
					values['clearart'] = art['clearart']
					values['tvshow.poster'] = art['tvshow.poster'] # not used in seasonDirectory() atm
				for k in ('seasons',): values.pop(k, None) # pop() keys from showSeasons that are not needed anymore
				list.append(values)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		return list

	def seasonDirectory(self, items):
		from sys import argv # some functions like ActivateWindow() throw invalid handle less this is imported here.
		if not items: # with reuselanguageinvoker on an empty directory must be loaded, do not use sys.exit()
			control.hide() ; control.notification(title=32054, message=33049)
		sysaddon, syshandle = 'plugin://plugin.video.umbrella/', int(argv[1])
		is_widget = 'plugin' not in control.infoLabel('Container.PluginName')
		settingFanart = getSetting('fanart') == 'true'
		addonPoster, addonFanart, addonBanner = control.addonPoster(), control.addonFanart(), control.addonBanner()
		if trakt.getTraktIndicatorsInfo():
			watchedMenu, unwatchedMenu = getLS(32068), getLS(32069)
		else:
			watchedMenu, unwatchedMenu = getLS(32066), getLS(32067)
		traktManagerMenu, queueMenu = getLS(32070), getLS(32065)
		showPlaylistMenu, clearPlaylistMenu = getLS(35517), getLS(35516)
		labelMenu, playRandom = getLS(32055), getLS(32535)
		addToLibrary = getLS(32551)
		try: multi = [i['tvshowtitle'] for i in items]
		except: multi = []
		multi = True if len([x for y,x in enumerate(multi) if x not in multi[:y]]) > 1 else False
		if items:
			imdb, tmdb, tvdb = items[0]['imdb'], items[0]['tmdb'], items[0]['tvdb']
			try: indicators = getSeasonIndicators(imdb, tvdb)
			except: indicators = None
		for i in items:
			try:
				if not self.showunaired and i.get('unaired', '') == 'true': continue
				title, year, season = i.get('tvshowtitle'), i.get('year', ''), i.get('season')
				label = '%s %s' % (labelMenu, season)
				try:
					if i['unaired'] == 'true': label = '[COLOR %s][I]%s[/I][/COLOR]' % (self.unairedcolor, label)
				except: pass
				systitle = quote_plus(title)
				meta = dict((k, v) for k, v in iter(i.items()) if v is not None and v != '')
				# setting mediatype to "season" causes CM "Infomation" and "play trailer" to not be available in some skins
				meta.update({'code': imdb, 'imdbnumber': imdb, 'mediatype': 'season', 'tag': [imdb, tmdb]}) # "tag" and "tagline" for movies only, but works in my skin mod so leave
				try: meta.update({'genre': cleangenre.lang(meta['genre'], self.lang)})
				except: pass
				poster = meta.get('tvshow.poster') or addonPoster # tvshow.poster
				if self.prefer_tmdbArt: 
					season_poster = meta.get('season_poster') or meta.get('season_poster2') or poster
				else: 
					season_poster = meta.get('season_poster2') or meta.get('season_poster') or poster
				fanart = ''
				if settingFanart: fanart = meta.get('fanart') or addonFanart
				if settingFanart: landscape = meta.get('landscape2')
				else: landscape = meta.get('landscape')
				thumb = season_poster
				icon = meta.get('icon') or poster
				banner = meta.get('banner') or addonBanner
				art = {}
				art.update({'poster': season_poster, 'tvshow.poster': poster, 'season.poster': season_poster, 'fanart': fanart, 'icon': icon, 'thumb': thumb, 'banner': banner,
						'clearlogo': meta.get('clearlogo', ''), 'tvshow.clearlogo': meta.get('clearlogo', ''), 'clearart': meta.get('clearart', ''), 'tvshow.clearart': meta.get('clearart', ''), 'landscape': landscape})
				# for k in ('poster2', 'poster3', 'fanart2', 'fanart3', 'banner2', 'banner3'): meta.pop(k, None)
				meta.update({'poster': poster, 'fanart': fanart, 'banner': banner, 'thumb': thumb, 'season_poster': season_poster, 'icon': icon, 'title': label, 'clearlogo': meta.get('clearart', '')})
				sysmeta = quote_plus(jsdumps(meta))
				url = '%s?action=episodes&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&meta=%s&season=%s' % (sysaddon, systitle, year, imdb, tmdb, tvdb, sysmeta, season)
####-Context Menu and Overlays-####
				cm = []
				try:
					watched = getSeasonOverlay(indicators[0], imdb, tvdb, season) == '5' if indicators else False
					if self.traktCredentials:
						cm.append((traktManagerMenu, 'RunPlugin(%s?action=tools_traktManager&name=%s&imdb=%s&tvdb=%s&season=%s&watched=%s)' % (sysaddon, systitle, imdb, tvdb, season, watched)))
					if watched:
						meta.update({'playcount': 1, 'overlay': 5})
						cm.append((unwatchedMenu, 'RunPlugin(%s?action=playcount_TVShow&name=%s&imdb=%s&tvdb=%s&season=%s&query=4)' % (sysaddon, systitle, imdb, tvdb, season)))
					else: 
						meta.update({'playcount': 0, 'overlay': 4})
						cm.append((watchedMenu, 'RunPlugin(%s?action=playcount_TVShow&name=%s&imdb=%s&tvdb=%s&season=%s&query=5)' % (sysaddon, systitle, imdb, tvdb, season)))
				except: pass
				cm.append((playRandom, 'RunPlugin(%s?action=play_Random&rtype=episode&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&meta=%s&season=%s)' % (sysaddon, systitle, year, imdb, tmdb, tvdb, sysmeta, season)))
				# cm.append((queueMenu, 'RunPlugin(%s?action=playlist_QueueItem&name=%s)' % (sysaddon, systitle)))
				# cm.append((showPlaylistMenu, 'RunPlugin(%s?action=playlist_Show)' % sysaddon))
				# cm.append((clearPlaylistMenu, 'RunPlugin(%s?action=playlist_Clear)' % sysaddon))
				cm.append((addToLibrary, 'RunPlugin(%s?action=library_tvshowToLibrary&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s)' % (sysaddon, systitle, year, imdb, tmdb, tvdb)))
				cm.append(('[COLOR red]Umbrella Settings[/COLOR]', 'RunPlugin(%s?action=tools_openSettings)' % sysaddon))
####################################
				item = control.item(label=label, offscreen=True)
				#if 'castandart' in i: item.setCast(i['castandart'])
				if 'castandart' in i: meta.update({"cast": ['castandart']}) #changed for kodi20 setinfo method
				item.setArt(art)
				try:
					count = getSeasonCount(imdb, tvdb, season)
					if count:
						if control.getKodiVersion() >= 20:
							if int(count['watched']) > 0:
								item.setProperties({'WatchedEpisodes': str(count['watched']), 'UnWatchedEpisodes': str(count['unwatched'])})
							else:
								item.setProperties({'UnWatchedEpisodes': str(count['unwatched'])})
						else:
							item.setProperties({'WatchedEpisodes': str(count['watched']), 'UnWatchedEpisodes': str(count['unwatched'])})
						item.setProperties({'TotalSeasons': str(meta.get('total_seasons', '')), 'TotalEpisodes': str(count['total'])})
						item.setProperty('WatchedProgress', str(int(float(count['watched']) / float(count['total']) * 100)))
					else:
						if meta.get('status') != 'Returning Series' or (meta.get('status') == 'Returning Series' and meta.get('last_episode_to_air', {}).get('season_number') > int(season)):
							if control.getKodiVersion() >= 20:
								item.setProperties({'UnWatchedEpisodes': str(meta.get('counts', {}).get(str(season), ''))})
							else:
								item.setProperties({'WatchedEpisodes': '0', 'UnWatchedEpisodes': str(meta.get('counts', {}).get(str(season), ''))})
							item.setProperties({'TotalSeasons': str(meta.get('total_seasons', '')), 'TotalEpisodes': str(meta.get('total_episodes', ''))})
						else:
							if meta.get('last_episode_to_air', {}).get('season_number') == int(season):
								if control.getKodiVersion() >= 20:
									item.setProperties({'UnWatchedEpisodes': str(meta.get('last_episode_to_air', {}).get('episode_number'))})
								else:
									item.setProperties({'WatchedEpisodes': '0', 'UnWatchedEpisodes': str(meta.get('last_episode_to_air', {}).get('episode_number'))})
								item.setProperties({'TotalSeasons': str(meta.get('total_seasons', '')), 'TotalEpisodes': str(meta.get('last_episode_to_air', {}).get('episode_number'))})
							else:
								if control.getKodiVersion() >= 20:
									item.setProperties({'UnWatchedEpisodes': '0'})
								else:
									item.setProperties({'WatchedEpisodes': '0', 'UnWatchedEpisodes': '0'})
								item.setProperties({'TotalSeasons': str(meta.get('total_seasons', '')), 'TotalEpisodes': '0'})
				except: pass

				if is_widget: 
					item.setProperty('isUmbrella_widget', 'true')
					if self.hide_watched_in_widget:
						if str(meta.get('playcount', 0)) == '1':
							continue
				try: # Year is the shows year, not the seasons year. Extract year from premier date for InfoLabels to have "season_year".
					season_year = re.findall(r'(\d{4})', i.get('premiered', ''))[0]
					meta.update({'year': season_year})
				except: pass
				setUniqueIDs = {'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb}
				control.set_info(item, meta, setUniqueIDs=setUniqueIDs)
				#item.setInfo(type='video', infoLabels=control.metadataClean(meta))
				if is_widget and control.getKodiVersion() > 19.5 and self.useFullContext != True:
					pass
				else:
					item.addContextMenuItems(cm)
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		try: control.property(syshandle, 'showplot', items[0]['plot'])
		except: pass
		control.content(syshandle, 'seasons')
		control.directory(syshandle, cacheToDisc=False) # disable cacheToDisc so unwatched counts loads fresh data counts if changes made
		views.setView('seasons', {'skin.estuary': 55, 'skin.confluence': 500})