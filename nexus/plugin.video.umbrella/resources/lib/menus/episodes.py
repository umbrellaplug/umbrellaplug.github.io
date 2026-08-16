# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from datetime import datetime, timedelta
from json import dumps as jsdumps, loads as jsloads
import re
from threading import Thread
from urllib.parse import quote_plus, urlencode, parse_qsl, urlparse, urlsplit
from resources.lib.database import cache, fanarttv_cache, traktsync, customtraktsync, floppysync, scrobsync
from resources.lib.database import artwork as customArtwork
from resources.lib.indexers.tmdb import TVshows as tmdb_indexer
from resources.lib.indexers.fanarttv import FanartTv
from resources.lib.modules import cleangenre
from resources.lib.modules import client
from resources.lib.modules import control
from resources.lib.modules import tools
from resources.lib.modules import trakt
from resources.lib.modules import simkl
from resources.lib.modules import mdblist
from resources.lib.modules import customtrakt
from resources.lib.modules import floppy
from resources.lib.modules import scrob
from resources.lib.modules import views
from resources.lib.modules.playcount import getTVShowIndicators, getEpisodeOverlay, getShowCount, getSeasonIndicators
from resources.lib.modules.player import Bookmarks
from concurrent.futures import ThreadPoolExecutor, as_completed
from resources.lib.modules import simkl

getLS = control.lang
getSetting = control.setting
KODI_VERSION = control.getKodiVersion()


class Episodes:
	def __init__(self, notifications=True):
		self.list = []
		self.count = getSetting('page.item.limit')
		self.lang = control.apiLanguage()['tmdb']
		self.notifications = notifications
		self.enable_fanarttv = getSetting('enable.fanarttv') == 'true'
		self.prefer_tmdbArt = getSetting('prefer.tmdbArt') == 'true'
		self.progress_showunaired = getSetting('trakt.progress.showunaired') == 'true'
		self.progress_showunairedSimkl = getSetting('simkl.progress.showunaired') == 'true'
		self.progress_showunairedMDBList = getSetting('mdblist.progress.showunaired') == 'true'
		self.showunaired = getSetting('showunaired') == 'true'
		self.unairedcolor = getSetting('unaired.identify')
		self.showspecials = getSetting('tv.specials') == 'true'

		self.highlight_color = control.setting('highlight.color')
		self.date_time = datetime.now()
		self.today_date = (self.date_time).strftime('%Y-%m-%d')
		self.trakt_user = getSetting('trakt.user.name').strip()
		self.traktCredentials = trakt.getTraktCredentialsInfo()
		self.simklCredentials = simkl.getSimKLCredentialsInfo()
		self.mdblist_authed = getSetting('mdblist.token') != ''
		self.customCredentials = customtrakt.getCustomCredentialsInfo()
		self.floppyCredentials = floppy.getFloppyCredentialsInfo()
		self.scrobCredentials = scrob.getScrobCredentialsInfo()
		self.trakt_directProgressScrape = getSetting('trakt.directProgress.scrape') == 'true'
		self.simkl_directProgressScrape = getSetting('simkl.directProgress.scrape') == 'true'
		self.mdblist_directProgressScrape = getSetting('mdblist.directProgress.scrape') == 'true'
		self.trakt_progressFlatten = getSetting('trakt.progressFlatten') == 'true'
		self.simkl_progressFlatten = getSetting('simkl.progressFlatten') == 'true'
		self.mdblist_progressFlatten = getSetting('mdblist.progressFlatten') == 'true'
		self.trakt_link = 'https://api.trakt.tv'
		self.trakthistory_link = 'https://api.trakt.tv/users/me/history/shows?limit=%s&page=1' % self.count
		self.progress_link = 'https://api.trakt.tv/users/me/watched/shows'
		self.mycalendarRecent_link = 'https://api.trakt.tv/calendars/my/shows/date[30]/33/'
		self.mycalendarUpcoming_link = 'https://api.trakt.tv/calendars/my/shows/date[0]/33/'
		self.mycalendarPremiers_link = 'https://api.trakt.tv/calendars/my/shows/premieres/date[0]/33'
		self.traktunfinished_link = 'https://api.trakt.tv/sync/playback/episodes?limit=40'
		self.tvmaze_link = 'https://api.tvmaze.com'
		self.added_link = 'https://api.tvmaze.com/schedule'
		self.calendar_link = 'https://api.tvmaze.com/schedule?date=%s'
		self.trakt_unfinished_hours = int(getSetting('cache.traktunfinished'))
		self.trakt_progress_hours = int(getSetting('cache.traktprogress'))
		self.trakt_history_hours = int(getSetting('cache.trakthistory'))
		self.simkl_hours = int(getSetting('cache.simkl'))
		self.mdblist_hours = int(getSetting('cache.mdblist'))
		self.hide_watched_in_widget = getSetting('enable.umbrellahidewatched') == 'true'
		self.useFullContext = getSetting('enable.umbrellawidgetcontext') == 'true'
		self.useContainerTitles = getSetting('enable.containerTitles') == 'true'
		self.simkl_link = 'https://api.simkl.com'
		self.prefer_fanArt = getSetting('prefer.fanarttv') == 'true'

	def get(self, tvshowtitle, year, imdb, tmdb, tvdb, meta, season=None, episode=None, create_directory=True):
		self.list = []
		def get_episodes(tvshowtitle, imdb, tmdb, tvdb, meta, season):
			episodes = cache.get(self.tmdb_list, 168, tvshowtitle, imdb, tmdb, tvdb, meta, season)
			if not episodes: pass
			elif episodes[0]['season_isAiring'] == 'true':
				if int(re.sub(r'[^0-9]', '', str(episodes[0]['next_episode_to_air']['air_date']))) <= int(re.sub(r'[^0-9]', '', str(self.today_date))):
					episodes = cache.get(self.tmdb_list, 3, tvshowtitle, imdb, tmdb, tvdb, meta, season)
			all_episodes.extend(episodes)
		try:
			if season is None and episode is None: # for "flatten" setting
				all_episodes = []
				if not isinstance(meta, dict):
					showSeasons = jsloads(meta)
				else:
					showSeasons = meta
				try:
					_unlimited = getSetting('dev.batch.unlimited') == 'true'
					_bs = None if _unlimited else max(int(getSetting('dev.batch.size') or '10'), 1)
					with ThreadPoolExecutor(max_workers=_bs) as executor:
						futures = [
							executor.submit(get_episodes, tvshowtitle, imdb, tmdb, tvdb, meta, season['season_number'])
							for season in showSeasons['seasons']
							if self.showspecials or season['season_number'] != 0
						]
						for future in as_completed(futures):
							try:
								result = future.result()
								if result:
									all_episodes.extend(result)  # Ensure results are collected properly
							except Exception as e:
								from resources.lib.modules import log_utils
								log_utils.error(f"Error processing season: {e}")
					# Sort episodes based on setting
					reverse_sort = getSetting('flatten.desc') == 'true'
					self.list = sorted(all_episodes, key=lambda k: (k['season'], k['episode']), reverse=reverse_sort)
				except Exception as e:
					from resources.lib.modules import log_utils
					log_utils.error(f"Error processing episodes: {e}")
			elif season and episode: # for "trakt progress-non direct progress scrape" setting
				self.list = cache.get(self.tmdb_list, 168, tvshowtitle, imdb, tmdb, tvdb, meta, season)
				if not self.list: pass
				elif self.list[0]['season_isAiring'] == 'true':
					if int(re.sub(r'[^0-9]', '', str(self.list[0]['next_episode_to_air']['air_date']))) <= int(re.sub(r'[^0-9]', '', str(self.today_date))):
						self.list = cache.get(self.tmdb_list, 3, tvshowtitle, imdb, tmdb, tvdb, meta, season)
				num = [x for x, y in enumerate(self.list) if y['season'] == int(season) and y['episode'] == int(episode)][-1]
				self.list = [y for x, y in enumerate(self.list) if x >= num]
				try:
					from resources.lib.modules.playcount import getTVShowIndicators, getEpisodeOverlay
					_progress_ind = getTVShowIndicators()
					if _progress_ind:
						while self.list and getEpisodeOverlay(_progress_ind, self.list[0].get('imdb', ''), str(self.list[0].get('tvdb', '')), self.list[0].get('season', 0), self.list[0].get('episode', 0)) == '5':
							self.list = self.list[1:]
				except: pass
				if self.trakt_progressFlatten or self.mdblist_progressFlatten:
					all_episodes = []

					if not isinstance(meta, dict):
						showSeasons = jsloads(meta)
					else:
						showSeasons = meta

					try:
						_unlimited = getSetting('dev.batch.unlimited') == 'true'
						_bs = None if _unlimited else max(int(getSetting('dev.batch.size') or '10'), 1)
						with ThreadPoolExecutor(max_workers=_bs) as executor:
							futures = [
								executor.submit(get_episodes, tvshowtitle, imdb, tmdb, tvdb, meta, s['season_number'])
								for s in showSeasons['seasons']
								if s['season_number'] > int(season)  # Filter out unwanted seasons
							]

							for future in as_completed(futures):
								try:
									result = future.result()
									if result:
										all_episodes.extend(result)  # Ensure results are collected properly
								except Exception as e:
									from resources.lib.modules import log_utils
									log_utils.error(f"Error processing season: {e}")

						self.list += all_episodes
						self.list = sorted(self.list, key=lambda k: (k['season'], k['episode']))
					except Exception as e:
						from resources.lib.modules import log_utils
						log_utils.error(f"Error processing episodes: {e}")
			else: # normal full episode list
				self.list = cache.get(self.tmdb_list, 168, tvshowtitle, imdb, tmdb, tvdb, meta, season)
				if not self.list: pass
				elif self.list[0]['season_isAiring'] == 'true':
					if int(re.sub(r'[^0-9]', '', str(self.list[0]['next_episode_to_air']['air_date']))) <= int(re.sub(r'[^0-9]', '', str(self.today_date))):
						self.list = cache.get(self.tmdb_list, 3, tvshowtitle, imdb, tmdb, tvdb, meta, season)
			if self.list is None: self.list = []
			if create_directory: self.episodeDirectory(self.list)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def unfinished(self, url, create_directory=True, folderName=''):
		self.list = []
		try:
			url = url or 'traktunfinished'
			base_url = url.split('?')[0] if '?' in url else url
			try: api_url = getattr(self, base_url + '_link')
			except: api_url = url
			items = traktsync.fetch_bookmarks(imdb='', ret_all=True, ret_type='episodes')
			if trakt.getPausedActivity() > cache.timeout(self.trakt_episodes_list, api_url, self.trakt_user, self.lang, items):
				self.list = cache.get(self.trakt_episodes_list, 0, api_url, self.trakt_user, self.lang, items)
			else: self.list = cache.get(self.trakt_episodes_list, self.trakt_unfinished_hours, api_url, self.trakt_user, self.lang, items)
			if self.list is None: self.list = []
			self.list = sorted(self.list, key=lambda k: k['paused_at'], reverse=True)
			if self.list and not self.showunaired:
				self.list = [i for i in self.list if i.get('unaired', '') != 'true']
			is_widget = 'plugin' not in control.infoLabel('Container.PluginName')
			if self.list and is_widget and getSetting('enable.umbrellahidewatched') == 'true':
				self.list = [i for i in self.list if str(i.get('playcount', '0')) != '1']
			useNext = True
			next_url = ''
			page_limit = max(1, int(self.count) if self.count else 20)
			if create_directory and getSetting('trakt.paginate.lists') == 'true' and self.list and len(self.list) > page_limit:
				try:
					q = dict(parse_qsl(urlsplit(url).query)) if '?' in url else {}
					index = int(q.get('page', 1)) - 1
				except:
					index = 0
				paginated_ids = [self.list[x:x + page_limit] for x in range(0, len(self.list), page_limit)]
				total_pages = len(paginated_ids)
				self.list = paginated_ids[index] if index < total_pages else (paginated_ids[0] if paginated_ids else [])
				try:
					if index + 1 < total_pages:
						next_page = index + 2
						next_url = 'plugin://plugin.video.umbrella/?action=episodesUnfinished&url=%s&page=%s&folderName=%s' % (
							quote_plus('traktunfinished?limit=%s&page=%s' % (page_limit, next_page)),
							str(next_page), quote_plus(folderName))
				except: pass
			for i in range(len(self.list)): self.list[i]['next'] = next_url
			hasNext = bool(next_url)
			if create_directory: self.episodeDirectory(self.list, unfinished=True, next=hasNext, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def mdblist_unfinished(self, url=None, create_directory=True, folderName=''):
		self.list = []
		try:
			from resources.lib.database import mdbsync
			from resources.lib.modules import mdblist
			items = mdbsync.fetch_bookmarks(imdb='', ret_all=True, ret_type='episodes')
			if not items:
				if create_directory: self.episodeDirectory(self.list, unfinished=True, next=False, folderName=folderName)
				return self.list
			cache_key = 'mdblistunfinished'
			if mdblist.getWatchedActivity() > cache.timeout(self.trakt_episodes_list, cache_key, self.trakt_user, self.lang, items):
				self.list = cache.get(self.trakt_episodes_list, 0, cache_key, self.trakt_user, self.lang, items)
			else:
				self.list = cache.get(self.trakt_episodes_list, self.trakt_unfinished_hours, cache_key, self.trakt_user, self.lang, items)
			if self.list is None: self.list = []
			self.list = sorted(self.list, key=lambda k: k['paused_at'], reverse=True)
			try:
				dropped = mdbsync.fetch_dropped('shows_dropped')
				if dropped:
					dropped_tmdb = {str(i['tmdb']) for i in dropped if i.get('tmdb')}
					dropped_imdb = {str(i['imdb']) for i in dropped if i.get('imdb')}
					self.list = [i for i in self.list if not (
						(i.get('tmdb') and str(i['tmdb']) in dropped_tmdb) or
						(i.get('imdb') and str(i['imdb']) in dropped_imdb)
					)]
			except: pass
			if self.list and not self.showunaired:
				self.list = [i for i in self.list if i.get('unaired', '') != 'true']
			if create_directory: self.episodeDirectory(self.list, unfinished=True, next=False, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def mdblistUnfinishedManager(self):
		try:
			control.busy()
			list = self.mdblist_unfinished(create_directory=False)
			control.hide()
			from resources.lib.windows.traktepisodeprogress_manager import TraktEpisodeProgressManagerXML
			window = TraktEpisodeProgressManagerXML('traktepisodeprogress_manager.xml', control.addonPath(control.addonId()), results=list)
			selected_items = window.run()
			del window
			if selected_items:
				for i in selected_items:
					mdblist.scrobbleReset(imdb=i.get('imdb', ''), tvdb=i.get('tvdb', ''), season=i.get('season'), episode=i.get('episode'), refresh=False)
				control.trigger_widget_refresh()
				if 'plugin.video.umbrella' in control.infoLabel('Container.PluginName'): control.refresh()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			control.hide()

	def floppy_unfinished(self, url=None, create_directory=True, folderName=''):
		# Confirmed via GET /api/v1/playback/progress/ (not previously known when
		# Floppy was first integrated) — same idea as scrob_unfinished() below, but
		# season/episode/ids all come straight off the live item, no imdb resolution
		# needed unless the ids block is missing it.
		self.list = []
		try:
			raw_items = floppy.get_all_pages('/playback/progress/', silent=True) or []
			items = []
			for item in raw_items:
				try:
					if item.get('media_type') != 'episode': continue
					ids = item.get('ids') or {}
					show_tmdb = str(ids.get('tmdb') or '')
					season, episode = item.get('season_number'), item.get('episode_number')
					if not show_tmdb or season is None or episode is None: continue
					show_tvdb = str(ids.get('tvdb') or '')
					show_imdb = str(ids.get('imdb') or '') or floppy._resolve_tv_imdb(show_tmdb)
					position = float(item.get('position_seconds') or 0)
					duration = float(item.get('duration_seconds') or 0)
					progress = round((position / duration) * 100, 1) if duration else 0
					items.append({
						'tvshowtitle': item.get('series_title', '') or '', 'title': item.get('title', '') or '',
						'imdb': show_imdb, 'tmdb': show_tmdb, 'tvdb': show_tvdb,
						'season': int(season), 'episode': int(episode),
						'genre': '', 'mpaa': '', 'studio': '', 'duration': 0,
						'progress': str(progress),
						'paused_at': item.get('updated_at', '') or '',
					})
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
			if not items:
				if create_directory: self.episodeDirectory(self.list, unfinished=True, next=False, folderName=folderName)
				return self.list
			cache_key = 'floppyunfinished'
			self.list = cache.get(self.trakt_episodes_list, 0, cache_key, self.trakt_user, self.lang, items)
			if self.list is None: self.list = []
			self.list = sorted(self.list, key=lambda k: k['paused_at'], reverse=True)
			if self.list and not self.showunaired:
				self.list = [i for i in self.list if i.get('unaired', '') != 'true']
			if create_directory: self.episodeDirectory(self.list, unfinished=True, next=False, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def floppyUnfinishedManager(self):
		try:
			control.busy()
			list = self.floppy_unfinished(create_directory=False)
			control.hide()
			from resources.lib.windows.traktepisodeprogress_manager import TraktEpisodeProgressManagerXML
			window = TraktEpisodeProgressManagerXML('traktepisodeprogress_manager.xml', control.addonPath(control.addonId()), results=list)
			selected_items = window.run()
			del window
			if selected_items:
				for i in selected_items:
					item = next((x for x in list if x.get('imdb') == i.get('imdb') and str(x.get('season')) == str(i.get('season')) and str(x.get('episode')) == str(i.get('episode'))), {})
					floppy.scrobbleReset(imdb=i.get('imdb', ''), tmdb=item.get('tmdb', ''), tvdb=i.get('tvdb', ''), season=i.get('season'), episode=i.get('episode'), refresh=False)
				control.trigger_widget_refresh()
				if 'plugin.video.umbrella' in control.infoLabel('Container.PluginName'): control.refresh()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			control.hide()

	def custom_unfinished(self, url=None, create_directory=True, folderName=''):
		self.list = []
		try:
			items = customtraktsync.fetch_bookmarks(imdb='', ret_all=True, ret_type='episodes')
			if not items:
				if create_directory: self.episodeDirectory(self.list, unfinished=True, next=False, folderName=folderName)
				return self.list
			cache_key = 'customunfinished'
			if customtrakt.getActivity() > cache.timeout(self.trakt_episodes_list, cache_key, self.trakt_user, self.lang, items):
				self.list = cache.get(self.trakt_episodes_list, 0, cache_key, self.trakt_user, self.lang, items)
			else:
				self.list = cache.get(self.trakt_episodes_list, self.trakt_unfinished_hours, cache_key, self.trakt_user, self.lang, items)
			if self.list is None: self.list = []
			self.list = sorted(self.list, key=lambda k: k['paused_at'], reverse=True)
			if self.list and not self.showunaired:
				self.list = [i for i in self.list if i.get('unaired', '') != 'true']
			if create_directory: self.episodeDirectory(self.list, unfinished=True, next=False, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def customUnfinishedManager(self):
		try:
			control.busy()
			list = self.custom_unfinished(create_directory=False)
			control.hide()
			from resources.lib.windows.traktepisodeprogress_manager import TraktEpisodeProgressManagerXML
			window = TraktEpisodeProgressManagerXML('traktepisodeprogress_manager.xml', control.addonPath(control.addonId()), results=list)
			selected_items = window.run()
			del window
			if selected_items:
				for i in selected_items:
					customtrakt.scrobbleReset(imdb=i.get('imdb', ''), tvdb=i.get('tvdb', ''), season=i.get('season'), episode=i.get('episode'), refresh=False)
				control.trigger_widget_refresh()
				if 'plugin.video.umbrella' in control.infoLabel('Container.PluginName'): control.refresh()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			control.hide()

	def scrob_unfinished(self, url=None, create_directory=True, folderName=''):
		# Unlike the other providers' "Unfinished" (which read local client-tracked
		# bookmarks), Scrob has a real server-side "in progress playback" endpoint —
		# reading it directly here means this reflects a pause point set from ANY
		# client reporting to the same Scrob account, not just what Umbrella itself
		# has seen. Season/episode numbers come straight from the live item, so unlike
		# scrob_progress_list()'s "next episode" guess, no TMDb-episode-matching by
		# number is needed beyond trakt_episodes_list()'s normal art/plot enrichment.
		self.list = []
		try:
			raw_items = scrob.get_continue_watching()
			items = []
			for item in raw_items:
				try:
					media = item.get('media') or {}
					if media.get('type') != 'episode': continue
					show_tmdb = str(media.get('show_tmdb_id') or '')
					season, episode = media.get('season_number'), media.get('episode_number')
					if not show_tmdb or season is None or episode is None: continue
					show_tvdb = str(media.get('show_tvdb_id') or '')
					show_imdb = scrob._resolve_tv_imdb(show_tmdb)
					items.append({
						'tvshowtitle': media.get('show_title', '') or '', 'title': media.get('title', '') or '',
						'imdb': show_imdb, 'tmdb': show_tmdb, 'tvdb': show_tvdb,
						'season': int(season), 'episode': int(episode),
						'genre': '', 'mpaa': '', 'studio': '', 'duration': 0,
						'progress': str(round(float(item.get('progress_percent') or 0) * 100, 1)),
						'paused_at': item.get('watched_at', '') or '',
					})
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
			if not items:
				if create_directory: self.episodeDirectory(self.list, unfinished=True, next=False, folderName=folderName)
				return self.list
			cache_key = 'scrobunfinished'
			self.list = cache.get(self.trakt_episodes_list, 0, cache_key, self.trakt_user, self.lang, items)
			if self.list is None: self.list = []
			self.list = sorted(self.list, key=lambda k: k['paused_at'], reverse=True)
			if self.list and not self.showunaired:
				self.list = [i for i in self.list if i.get('unaired', '') != 'true']
			if create_directory: self.episodeDirectory(self.list, unfinished=True, next=False, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def scrobUnfinishedManager(self):
		try:
			control.busy()
			list = self.scrob_unfinished(create_directory=False)
			control.hide()
			from resources.lib.windows.traktepisodeprogress_manager import TraktEpisodeProgressManagerXML
			window = TraktEpisodeProgressManagerXML('traktepisodeprogress_manager.xml', control.addonPath(control.addonId()), results=list)
			selected_items = window.run()
			del window
			if selected_items:
				for i in selected_items:
					scrob.scrobbleReset(imdb=i.get('imdb', ''), tvdb=i.get('tvdb', ''), season=i.get('season'), episode=i.get('episode'), refresh=False)
				control.trigger_widget_refresh()
				if 'plugin.video.umbrella' in control.infoLabel('Container.PluginName'): control.refresh()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			control.hide()

	def local_finish_watching(self, url='', folderName=''):
		self.list = []
		try:
			from resources.lib.database import watchedcache as wc
			import datetime as _dt
			items = wc.get_episodes_in_progress()
			if not items:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)
				return

			def build_item(item):
				imdb_id = item.get('imdb_id', '')
				tmdb_id = item.get('tmdb_id', '')
				season = int(item.get('season', 0))
				episode_num = int(item.get('episode', 0))
				try:
					ts = int(item.get('last_played', 0))
					dt = _dt.datetime.utcfromtimestamp(ts)
					lp = dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
				except:
					lp = ''
				try:
					tvdb_id = ''
					if not tmdb_id and imdb_id:
						tmdb_result = cache.get(tmdb_indexer().IdLookup, 96, imdb_id, '')
						tmdb_id = str(tmdb_result.get('id')) if tmdb_result else ''
						tvdb_id = str(tmdb_result.get('tvdb', '')) if tmdb_result else ''
					if not tmdb_id:
						return
					showSeasons = cache.get(tmdb_indexer().get_showSeasons_meta, 96, tmdb_id)
					if not showSeasons:
						return
					seasonEpisodes = tmdb_indexer().get_seasonEpisodes_meta_checked(tmdb_id, season)
					if not seasonEpisodes:
						return
					episode_list = seasonEpisodes.get('episodes', [])
					try:
						episode_meta = [x for x in episode_list if x.get('episode') == episode_num][0]
					except:
						return
					values = {}
					values['imdb'] = imdb_id
					values['tmdb'] = tmdb_id
					values['tvdb'] = tvdb_id or showSeasons.get('tvdb', '')
					values['lastplayed'] = lp
					values['paused_at'] = lp
					values['progress'] = item.get('resume_point', '0')
					if not episode_meta.get('plot'):
						episode_meta['plot'] = showSeasons.get('plot', '')
					values.update(showSeasons)
					values.update(seasonEpisodes)
					values.update(episode_meta)
					for k in ('episodes', 'snum', 'enum'):
						values.pop(k, None)
					if not values.get('season'):
						values['season'] = season
					if not values.get('episode'):
						values['episode'] = episode_num
					if self.enable_fanarttv:
						tvdb = values.get('tvdb', '')
						extended_art = fanarttv_cache.get(FanartTv().get_tvshow_art, 336, tvdb)
						if extended_art:
							values.update(extended_art)
					values['next'] = ''
					values['localProgress'] = True
					self.list.append(values)
				except:
					from resources.lib.modules import log_utils
					log_utils.error()

			threads = []
			for item in items:
				threads.append(Thread(target=build_item, args=(item,)))
			[t.start() for t in threads]
			[t.join() for t in threads]
			if self.list is None:
				self.list = []
			self.list = sorted(self.list, key=lambda k: k.get('paused_at', ''), reverse=True)
			for i in range(len(self.list)):
				self.list[i]['next'] = ''
			self.episodeDirectory(self.list, unfinished=True, next=False, folderName=folderName)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications:
					control.notification(title=32326, message=33049)

	def unfinishedManager(self):
		try:
			control.busy()
			list = self.unfinished(url='traktunfinished', create_directory=False)
			control.hide()
			from resources.lib.windows.traktepisodeprogress_manager import TraktEpisodeProgressManagerXML
			window = TraktEpisodeProgressManagerXML('traktepisodeprogress_manager.xml', control.addonPath(control.addonId()), results=list)
			selected_items = window.run()
			del window
			if selected_items:
				refresh = 'plugin.video.umbrella' in control.infoLabel('Container.PluginName')
				trakt.scrobbleResetItems(imdb_ids=None, tvdb_dicts=selected_items, refresh=refresh, widgetRefresh=True)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			control.hide()

	def upcoming_progress(self, url, folderName=''):
		self.list = []
		try:
			try: url = getattr(self, url + '_link')
			except: pass
			if self.trakt_link in url and url == self.progress_link:
				if trakt.getProgressActivity() > cache.timeout(self.trakt_progress_list, url, self.trakt_user, self.lang, self.trakt_directProgressScrape, True):
					self.list = cache.get(self.trakt_progress_list, 0, url, self.trakt_user, self.lang, self.trakt_directProgressScrape, True)
				else: self.list = cache.get(self.trakt_progress_list, self.trakt_progress_hours, url, self.trakt_user, self.lang, self.trakt_directProgressScrape, True)
				try:
					hidden_prog = traktsync.fetch_hidden_progress()
					hidden_tvdb_set = {str(i['tvdb']) for i in hidden_prog if i.get('tvdb')}
					self.list = [i for i in (self.list or []) if i.get('tvdb') not in hidden_tvdb_set]
				except: pass
				try:
					if not self.list: raise Exception()
					for i in range(len(self.list)):
						if 'premiered' not in self.list[i]: self.list[i]['premiered'] = ''
						if 'airtime' not in self.list[i]: self.list[i]['airtime'] = ''
					self.list = sorted(self.list, key=lambda k: (k['premiered'] if k['premiered'] else '3021-01-01', k['airtime'])) # "3021" date hack to force unknown premiered dates to bottom of list
				except: pass
			if self.list is None: self.list = []
			self.episodeDirectory(self.list, unfinished=False, next=False, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def clr_progress_cache(self, url):
		if url == 'mdbprogress':
			cache.remove(self.mdblist_progress_list, '/upnext', self.mdblist_directProgressScrape)
			cache.remove(self.mdblist_progress_list, url, self.mdblist_directProgressScrape)
			control.sleep(200)
			return control.refresh()
		try: url = getattr(self, url + '_link')
		except: pass
		cache.remove(self.trakt_progress_list, url, self.trakt_user, self.lang, self.trakt_directProgressScrape)
		cache.remove(self.simkl_progress_list, url, self.simkl_directProgressScrape)
		control.sleep(200)
		control.refresh()

	def calendar(self, url, folderName=''):
		self.list = []
		try:
			url_param = url or 'progress'
			base_url = url_param.split('?')[0] if url_param else 'progress'
			try: url = getattr(self, base_url + '_link')
			except: url = url_param
			isTraktHistory = (url.split('&page=')[0] in self.trakthistory_link) if url else False
			isProgressView = (base_url == 'progress')
			try:
				q = dict(parse_qsl(urlsplit(url_param).query)) if '?' in url_param else {}
				index = int(q.get('page', 1)) - 1
				page_limit = max(1, int(q['limit'])) if q.get('limit') else max(1, int(self.count) if self.count else 20)
			except:
				index = 0
				page_limit = max(1, int(self.count) if self.count else 20)
			if isProgressView or (self.trakt_link in str(url) and url == self.progress_link):
				api_url = self.progress_link
				if trakt.getProgressActivity() > cache.timeout(self.trakt_progress_list, api_url, self.trakt_user, self.lang, self.trakt_directProgressScrape):
					self.list = cache.get(self.trakt_progress_list, 0, api_url, self.trakt_user, self.lang, self.trakt_directProgressScrape)
				else: self.list = cache.get(self.trakt_progress_list, self.trakt_progress_hours, api_url, self.trakt_user, self.lang, self.trakt_directProgressScrape)
				try:
					hidden_prog = traktsync.fetch_hidden_progress()
					hidden_tvdb_set = {str(i['tvdb']) for i in hidden_prog if i.get('tvdb')}
					self.list = [i for i in (self.list or []) if i.get('tvdb') not in hidden_tvdb_set]
				except: pass
				self.sort(type='progress')
				if self.list is None: self.list = []
				# place new season ep1's at top of list for 1 week
				prior_week = int(re.sub(r'[^0-9]', '', (self.date_time - timedelta(days=7)).strftime('%Y-%m-%d')))
				sorted_list = []
				top_items = [i for i in self.list if i['episode'] == 1 and i['premiered'] and (int(re.sub(r'[^0-9]', '', str(i['premiered']))) >= prior_week)]
				sorted_list.extend(top_items)
				sorted_list.extend([i for i in self.list if i not in top_items])
				self.list = sorted_list
			elif self.trakt_link in url and (url == self.mycalendarRecent_link) or (url == self.mycalendarUpcoming_link) or (url == self.mycalendarPremiers_link):
				if trakt.getActivity() > cache.timeout(self.trakt_episodes_list, url, self.trakt_user, self.lang):
					self.list = cache.get(self.trakt_episodes_list, 0, url, self.trakt_user, self.lang)
				else: self.list = cache.get(self.trakt_episodes_list, 1, url, self.trakt_user, self.lang)
				try:
					hidden_prog = traktsync.fetch_hidden_progress()
					hidden_imdb = {str(i['imdb']) for i in hidden_prog if i.get('imdb')}
					hidden_tvdb = {str(i['tvdb']) for i in hidden_prog if i.get('tvdb')}
					self.list = [i for i in (self.list or []) if not (
						(i.get('imdb') and str(i['imdb']) in hidden_imdb) or
						(i.get('tvdb') and str(i['tvdb']) in hidden_tvdb)
					)]
				except: pass
				if (url == self.mycalendarUpcoming_link) or (url == self.mycalendarPremiers_link):
					if self.list:
						self.list = [i for i in self.list if int(re.sub(r'[^0-9]', '', str(i['premiered']).split('T')[0])) >= int(re.sub(r'[^0-9]', '', str(self.today_date)))]
						for i in range(len(self.list)): self.list[i]['calendar_unaired'] = True
						self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=False)
				elif url == self.mycalendarRecent_link:
					if self.list:
						self.list = [i for i in self.list if int(re.sub(r'[^0-9]', '', str(i['premiered']).split('T')[0])) <= int(re.sub(r'[^0-9]', '', str(self.today_date)))]
						for i in range(len(self.list)): self.list[i]['calendar_recent'] = True
						self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=True)
			elif isTraktHistory:
				if trakt.getActivity() > cache.timeout(self.trakt_episodes_list, url, self.trakt_user, self.lang):
					self.list = cache.get(self.trakt_episodes_list, 0, url, self.trakt_user, self.lang)
				else: self.list = cache.get(self.trakt_episodes_list, self.trakt_history_hours, url, self.trakt_user, self.lang)
				if self.list:
					for i in range(len(self.list)): self.list[i]['traktHistory'] = True
					self.list = sorted(self.list, key=lambda k: k['lastplayed'], reverse=True)
					result = []
					for i in self.list:
						notAdded = True
						for j in result:
							if i.get('episodeIDS') == j.get('episodeIDS'):
								notAdded = False
						if notAdded == True:
							result.append(i)
					self.list = result
			elif self.tvmaze_link in url and url == self.added_link:
				urls = [i['url'] for i in self.calendars(idx=False)][:5]
				self.list = []
				for url in urls: self.list += cache.get(self.tvmaze_list, 720, url, True)
			elif self.tvmaze_link in url:
				self.list = cache.get(self.tvmaze_list, 1, url, False)
			if self.list is None: self.list = []
			if isProgressView and not self.progress_showunaired:
				self.list = [i for i in self.list if i.get('unaired', '') != 'true']
			hasNext = True if isTraktHistory else False
			next_url = ''
			if isProgressView and getSetting('trakt.paginate.lists') == 'true' and self.list:
				paginated_ids = [self.list[x:x + page_limit] for x in range(0, len(self.list), page_limit)]
				total_pages = len(paginated_ids)
				self.list = paginated_ids[index] if index < total_pages else []
				try:
					if index + 1 >= total_pages: raise Exception()
					next_page = index + 2
					next_url = 'plugin://plugin.video.umbrella/?action=calendar&url=%s&page=%s&folderName=%s' % (
						quote_plus('progress?limit=%s&page=%s' % (page_limit, next_page)),
						str(next_page), quote_plus(folderName))
					hasNext = True
				except: pass
			for i in range(len(self.list)): self.list[i]['next'] = next_url
			self.episodeDirectory(self.list, unfinished=False, next=hasNext, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def simkl_calendar(self, url, folderName=''):
		self.list = []
		try:
			url_param = url or '/sync/all-items/shows/watching'
			try:
				q = dict(parse_qsl(urlsplit(url_param).query)) if '?' in url_param else {}
				index = int(q.get('page', 1)) - 1
				page_limit = max(1, int(q['limit'])) if q.get('limit') else max(1, int(self.count) if self.count else 20)
			except:
				index = 0
				page_limit = max(1, int(self.count) if self.count else 20)
			base_api_url = url_param.split('?')[0]
			try: api_url = getattr(self, base_api_url + '_link')
			except: api_url = base_api_url
			if '/sync/all-items/shows/watching' in api_url:
				if simkl.getProgressActivity() > cache.timeout(self.simkl_progress_list, api_url, self.simkl_directProgressScrape):
					self.list = cache.get(self.simkl_progress_list, 0, api_url, self.simkl_directProgressScrape)
				else: self.list = cache.get(self.simkl_progress_list, self.simkl_hours, api_url, self.simkl_directProgressScrape)
				self.sort(type='progress')
				if self.list is None: self.list = []
				# place new season ep1's at top of list for 1 week
				prior_week = int(re.sub(r'[^0-9]', '', (self.date_time - timedelta(days=7)).strftime('%Y-%m-%d')))
				sorted_list = []
				top_items = [i for i in self.list if i['episode'] == 1 and i['premiered'] and (int(re.sub(r'[^0-9]', '', str(i['premiered']))) >= prior_week)]
				sorted_list.extend(top_items)
				sorted_list.extend([i for i in self.list if i not in top_items])
				self.list = sorted_list
				try:
					from resources.lib.database import simklsync as _simklsync
					dropped = _simklsync.fetch_dropped('shows_dropped')
					if dropped:
						dropped_tmdb = {str(i['tmdb']) for i in dropped if i.get('tmdb')}
						dropped_imdb = {str(i['imdb']) for i in dropped if i.get('imdb')}
						self.list = [i for i in self.list if not (
							(i.get('tmdb') and str(i['tmdb']) in dropped_tmdb) or
							(i.get('imdb') and str(i['imdb']) in dropped_imdb)
						)]
				except: pass
			if self.list is None: self.list = []
			if not self.progress_showunairedSimkl:
				self.list = [i for i in self.list if i.get('unaired', '') != 'true']
			hasNext = False
			next_url = ''
			if getSetting('simkl.paginate.lists') == 'true' and self.list:
				paginated_ids = [self.list[x:x + page_limit] for x in range(0, len(self.list), page_limit)]
				total_pages = len(paginated_ids)
				self.list = paginated_ids[index] if index < total_pages else []
				try:
					if index + 1 >= total_pages: raise Exception()
					next_page = index + 2
					next_url = 'plugin://plugin.video.umbrella/?action=simkl_calendar&url=%s&page=%s&folderName=%s' % (
						quote_plus('/sync/all-items/shows/watching?page=%s' % next_page),
						str(next_page), quote_plus(folderName))
					hasNext = True
				except: pass
			for i in range(len(self.list)): self.list[i]['next'] = next_url
			self.episodeDirectory(self.list, unfinished=False, next=hasNext, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def mdblist_calendar(self, url, folderName=''):
		self.list = []
		try:
			if mdblist.getWatchedActivity() > cache.timeout(self.mdblist_progress_list, url, self.mdblist_directProgressScrape):
				self.list = cache.get(self.mdblist_progress_list, 0, url, self.mdblist_directProgressScrape)
			else:
				self.list = cache.get(self.mdblist_progress_list, self.mdblist_hours, url, self.mdblist_directProgressScrape)
			self.sort(type='progress')
			if self.list is None: self.list = []
			# place new season ep1's at top of list for 1 week
			prior_week = int(re.sub(r'[^0-9]', '', (self.date_time - timedelta(days=7)).strftime('%Y-%m-%d')))
			sorted_list = []
			top_items = [i for i in self.list if i.get('episode') == 1 and i.get('premiered') and (int(re.sub(r'[^0-9]', '', str(i['premiered']))) >= prior_week)]
			sorted_list.extend(top_items)
			sorted_list.extend([i for i in self.list if i not in top_items])
			self.list = sorted_list
			try:
				from resources.lib.database import mdbsync as _mdbsync
				dropped = _mdbsync.fetch_dropped('shows_dropped')
				if dropped:
					dropped_tmdb = {str(i['tmdb']) for i in dropped if i.get('tmdb')}
					dropped_imdb = {str(i['imdb']) for i in dropped if i.get('imdb')}
					self.list = [i for i in self.list if not (
						(i.get('tmdb') and str(i['tmdb']) in dropped_tmdb) or
						(i.get('imdb') and str(i['imdb']) in dropped_imdb)
					)]
			except: pass
			if self.list is None: self.list = []
			if not self.progress_showunairedMDBList:
				self.list = [i for i in self.list if i.get('unaired', '') != 'true']
			hasNext = False
			next_url = ''
			if getSetting('mdblist.paginate.lists') == 'true' and self.list:
				try:
					q = dict(parse_qsl(urlsplit(url).query)) if '?' in url else {}
					index = int(q.get('page', 1)) - 1
					page_limit = max(1, int(q['limit'])) if q.get('limit') else max(1, int(self.count) if self.count else 20)
				except:
					index = 0
					page_limit = max(1, int(self.count) if self.count else 20)
				paginated_ids = [self.list[x:x + page_limit] for x in range(0, len(self.list), page_limit)]
				total_pages = len(paginated_ids)
				self.list = paginated_ids[index] if index < total_pages else []
				try:
					if index + 1 >= total_pages: raise Exception()
					next_page = index + 2
					next_url = 'plugin://plugin.video.umbrella/?action=mdblist_calendar&url=%s&page=%s&folderName=%s' % (
						quote_plus('mdbprogress?limit=%s&page=%s' % (page_limit, next_page)),
						str(next_page), quote_plus(folderName))
					hasNext = True
				except: pass
			for i in range(len(self.list)): self.list[i]['next'] = next_url
			self.episodeDirectory(self.list, unfinished=False, next=hasNext, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def mdblist_progress_list(self, url='/upnext', direct=False):
		# MDBList's own /upnext endpoint (get_up_next()) was returning S1E1 for shows
		# watched out of order — it depends on MDBList's server-side watched-history
		# tracking for the show, which doesn't reliably reflect out-of-order watching.
		# Reconstructed locally instead, from mdbsync's watched-episode table, the same
		# "furthest watched episode + 1" approach floppy_progress_list() uses (matches
		# real Trakt's own progress semantics: resume from your furthest point, not the
		# first unwatched episode in chronological order).
		self.list = []
		try:
			from resources.lib.database import mdbsync
			episodes = mdbsync.get_watched_episodes()
			if not episodes: return self.list
			shows = {}
			for (show_imdb, show_tmdb, show_tvdb, season, episode) in episodes:
				key = show_imdb or show_tmdb
				if not key: continue
				shows.setdefault(key, {'imdb': show_imdb, 'tmdb': show_tmdb, 'tvdb': show_tvdb, 'watched_set': set()})
				shows[key]['watched_set'].add((int(season), int(episode)))
			try:
				for (show_imdb, show_tmdb, show_tvdb, last_watched_at) in mdbsync.get_watched_shows():
					key = show_imdb or show_tmdb
					if key in shows: shows[key]['lastplayed'] = last_watched_at
			except: pass
			items = list(shows.values())
		except: return self.list
		if not items: return self.list

		def items_list(i):
			imdb_id = i.get('imdb', '')
			tmdb_id = i.get('tmdb', '')
			watched_set = i.get('watched_set', set())
			try:
				candidates = watched_set if self.showspecials else set((s, e) for (s, e) in watched_set if s != 0)
				if not candidates: return
				furthest_season = max(s for (s, e) in candidates)
				furthest_episode = max(e for (s, e) in candidates if s == furthest_season)
				tmdb = tmdb_id
				if not tmdb and imdb_id:
					tmdb_result = cache.get(tmdb_indexer().IdLookup, 96, imdb_id, i.get('tvdb', ''))
					tmdb = str(tmdb_result.get('id')) if tmdb_result else ''
				if not tmdb: return
				showSeasons = cache.get(tmdb_indexer().get_showSeasons_meta, 96, tmdb)
				if not showSeasons: return
				seasons_meta = {s.get('season_number'): s for s in showSeasons.get('seasons', [])}
				season_meta = seasons_meta.get(furthest_season)
				# Not capped to TMDb's last-aired boundary (last_episode_to_air) — that
				# show-level field lags behind reality right around an episode's actual air
				# date/time, which caused this to silently drop shows whose next episode had
				# genuinely already released but TMDb hadn't flipped last_episode_to_air to
				# yet (e.g. next_episode_to_air.air_date == today). The per-episode "unaired"
				# check below (using that specific episode's own air_date, refreshed via
				# get_seasonEpisodes_meta_checked) is the precise signal for whether an episode
				# is actually out yet; a "renewed but next season not released" show is still
				# correctly excluded by the seasons_meta membership check right after this.
				raw_count = season_meta.get('episode_count', 0) if season_meta else 0
				if raw_count and furthest_episode < raw_count:
					next_season_num, next_episode_num = furthest_season, furthest_episode + 1
				else:
					next_season_num, next_episode_num = furthest_season + 1, 1
				if next_season_num not in seasons_meta: return  # no further known season — fully caught up
				values = {}
				values['imdb'] = imdb_id
				values['tmdb'] = tmdb
				values['tvdb'] = i.get('tvdb', '')
				values['lastplayed'] = i.get('lastplayed', '')
				try:
					show_summary = trakt.getTVShowSummary(imdb_id, full=False) if imdb_id else None
					airs = (show_summary or {}).get('airs', {}) or {}
					values['airday'] = airs.get('day', '')
					values['airtime'] = airs.get('time', '')
					values['airzone'] = airs.get('timezone', '')
				except: pass
				if not self.showspecials and next_season_num == 0: return
				seasonEpisodes = tmdb_indexer().get_seasonEpisodes_meta_checked(tmdb, next_season_num)
				if not seasonEpisodes: return
				seasonEpisodes = dict((k, v) for k, v in iter(seasonEpisodes.items()) if v is not None and v != '')
				try: episode_meta = [x for x in seasonEpisodes.get('episodes') if x.get('episode') == next_episode_num][0]
				except: return
				if not episode_meta.get('plot'): episode_meta['plot'] = showSeasons.get('plot', '')
				values.update(showSeasons)
				values.update(seasonEpisodes)
				values.update(episode_meta)
				for k in ('episodes', 'snum', 'enum'): values.pop(k, None)
				duration = values.get('duration')
				if duration:
					try: values['duration'] = int(duration) * 60
					except: pass
				air_date = values.get('premiered', '')
				values['unaired'] = ''
				try:
					if values.get('status', '').lower() == 'ended': pass
					elif not air_date: values['unaired'] = 'true'
					elif int(re.sub(r'[^0-9]', '', air_date)) > int(re.sub(r'[^0-9]', '', str(self.today_date))):
						values['unaired'] = 'true'
				except: pass
				if self.enable_fanarttv:
					tvdb = values.get('tvdb', '')
					extended_art = fanarttv_cache.get(FanartTv().get_tvshow_art, 336, tvdb)
					if extended_art: values.update(extended_art)
				if not direct: values['action'] = 'episodes'
				values['mdblistProgress'] = True
				values['extended'] = True
				self.list.append(values)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()

		threads = []
		for i in items:
			threads.append(Thread(target=items_list, args=(i,)))
		_unlimited = getSetting('dev.batch.unlimited') == 'true'
		_bs = max(int(getSetting('dev.batch.size') or '10'), 1)
		_chunk = max(len(threads), 1) if _unlimited else _bs
		for i in range(0, len(threads), _chunk):
			if control.monitor.abortRequested(): break
			batch = threads[i:i + _chunk]
			[t.start() for t in batch]
			[t.join() for t in batch]
		return self.list

	def mdblist_calendar_items(self, days=33, start_date=None):
		# Flat episode-reference items from MDBList's own /calendar/events — personalized
		# to the user's watchlist/tracked shows, confirmed live against a real account.
		# Mapped into the same shape trakt_list() produces so trakt_episodes_list can
		# enrich them with TMDb data unmodified, mirroring custom_calendar_items() exactly.
		# Confirmed schema: {type: 'episode'|'movie', title: <show title>, episode_title,
		# show_tmdb, season_number, episode_number, start: 'YYYY-MM-DD'} — MDBList's
		# calendar has no imdb/tvdb on the event itself, only show_tmdb.
		items = []
		try:
			start = start_date or self.date_time.strftime('%Y-%m-%d')
			# datetime.strptime() is unreliable on some embedded Python builds (confirmed:
			# broke on a Firecube Android TV device with 'NoneType' object is not callable —
			# strptime's lazy _strptime import isn't thread-safe there) — every other date
			# computation in this file already avoids it, this was the one new usage.
			# datetime(y, m, d) needs no lazy import, so build the date manually instead.
			y, m, d = (int(x) for x in start.split('-')[:3])
			end = (datetime(y, m, d) + timedelta(days=days)).strftime('%Y-%m-%d')
			raw = mdblist.get_calendar(start, end)
			if not raw: return items
			for i in raw:
				try:
					if i.get('type') != 'episode': continue
					season, episode = i.get('season_number'), i.get('episode_number')
					if season is None or episode is None: continue
					if not self.showspecials and season == 0: continue
					tvshowtitle = i.get('title')
					if not tvshowtitle: continue
					tmdb = str(i.get('show_tmdb') or '')
					if not tmdb: continue
					values = {
						'title': i.get('episode_title') or '', 'season': season, 'episode': episode,
						'tvshowtitle': tvshowtitle, 'year': '',
						'premiered': i.get('start') or '',
						'imdb': '', 'tmdb': tmdb, 'tvdb': '',
						'next': '',
					}
					items.append(values)
				except: pass
			try:
				from resources.lib.database import mdbsync as _mdbsync
				dropped = _mdbsync.fetch_dropped('shows_dropped')
				if dropped:
					dropped_tmdb = {str(i['tmdb']) for i in dropped if i.get('tmdb')}
					items = [i for i in items if not (i.get('tmdb') and str(i['tmdb']) in dropped_tmdb)]
			except: pass
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		return items

	def mdblist_calendar_recent(self, url, folderName=''):
		# "Recent" needs a window that actually reaches into the past — mirrors
		# custom_calendar_recent()'s date-window override for the same reason.
		self.list = []
		try:
			recent_start = (self.date_time - timedelta(days=30)).strftime('%Y-%m-%d')
			items = cache.get(self.mdblist_calendar_items, 1, 33, recent_start)
			self.list = self.trakt_episodes_list('mdblistcalendarrecent', self.trakt_user, self.lang, items=items)
			if self.list:
				self.list = [i for i in self.list if int(re.sub(r'[^0-9]', '', str(i['premiered']).split('T')[0])) <= int(re.sub(r'[^0-9]', '', str(self.today_date)))]
				for i in range(len(self.list)): self.list[i]['calendar_recent'] = True
				self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=True)
			if self.list is None: self.list = []
			self.episodeDirectory(self.list, unfinished=False, next=False, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def mdblist_calendar_upcoming(self, url, folderName=''):
		self.list = []
		try:
			items = cache.get(self.mdblist_calendar_items, 1, 33)
			self.list = self.trakt_episodes_list('mdblistcalendarupcoming', self.trakt_user, self.lang, items=items)
			if self.list:
				self.list = [i for i in self.list if int(re.sub(r'[^0-9]', '', str(i['premiered']).split('T')[0])) >= int(re.sub(r'[^0-9]', '', str(self.today_date)))]
				for i in range(len(self.list)): self.list[i]['calendar_unaired'] = True
				self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=False)
			if self.list is None: self.list = []
			self.episodeDirectory(self.list, unfinished=False, next=False, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def mdblist_calendar_premieres(self, url, folderName=''):
		self.list = []
		try:
			items = cache.get(self.mdblist_calendar_items, 1, 33)
			self.list = self.trakt_episodes_list('mdblistcalendarpremieres', self.trakt_user, self.lang, items=items)
			if self.list:
				self.list = [i for i in self.list if i.get('episode') == 1 and
					int(re.sub(r'[^0-9]', '', str(i['premiered']).split('T')[0])) >= int(re.sub(r'[^0-9]', '', str(self.today_date)))]
				for i in range(len(self.list)): self.list[i]['calendar_unaired'] = True
				self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=False)
			if self.list is None: self.list = []
			self.episodeDirectory(self.list, unfinished=False, next=False, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def local_calendar(self, url, folderName=''):
		self.list = []
		try:
			self.list = cache.get(self.local_progress_list, 0, url)
			self.sort(type='progress')
			if self.list is None: self.list = []
			prior_week = int(re.sub(r'[^0-9]', '', (self.date_time - timedelta(days=7)).strftime('%Y-%m-%d')))
			sorted_list = []
			top_items = [i for i in self.list if i.get('episode') == 1 and i.get('premiered') and (int(re.sub(r'[^0-9]', '', str(i['premiered']))) >= prior_week)]
			sorted_list.extend(top_items)
			sorted_list.extend([i for i in self.list if i not in top_items])
			self.list = sorted_list
			if self.list is None: self.list = []
			if not getSetting('local.progress.showunaired') == 'true':
				self.list = [i for i in self.list if i.get('unaired', '') != 'true']
			for i in range(len(self.list)): self.list[i]['next'] = ''
			self.episodeDirectory(self.list, unfinished=False, next=False, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def local_progress_list(self, url='', direct=False):
		self.list = []
		try:
			from resources.lib.database import watchedcache as wc
			show_ids = wc.get_in_progress_show_imdb_ids()
			if not show_ids: return self.list
			items = []
			for imdb_id, last_played in show_ids:
				try:
					watched_eps = wc.get_watched_episode_ids(imdb_id)
					if not watched_eps: continue
					try:
						import datetime as _dt
						ts = int(last_played)
						dt = _dt.datetime.utcfromtimestamp(ts)
						lp = dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
					except: lp = ''
					watched_set = {(ep[0], ep[1]) for ep in watched_eps}
					items.append({'imdb': imdb_id, 'watched_set': watched_set, 'lastplayed': lp})
				except: pass
			if not items: return self.list

			def items_list(i):
				imdb_id = i.get('imdb', '')
				watched_set = i.get('watched_set', set())
				try:
					tmdb_result = cache.get(tmdb_indexer().IdLookup, 96, imdb_id, '')
					tmdb_id = str(tmdb_result.get('id')) if tmdb_result else ''
					if not tmdb_id: return
					showSeasons = cache.get(tmdb_indexer().get_showSeasons_meta, 96, tmdb_id)
					if not showSeasons: return
					# Find the first unwatched episode in chronological order
					next_season = None
					next_episode = None
					for s in sorted(showSeasons.get('seasons', []), key=lambda x: x.get('season_number', 0)):
						snum = s.get('season_number', 0)
						if snum == 0 and not self.showspecials: continue
						for enum in range(1, s.get('episode_count', 0) + 1):
							if (snum, enum) not in watched_set:
								next_season = snum
								next_episode = enum
								break
						if next_season is not None: break
					if next_season is None: return  # fully watched
					seasonEpisodes = tmdb_indexer().get_seasonEpisodes_meta_checked(tmdb_id, next_season)
					if not seasonEpisodes: return
					episode_list = seasonEpisodes.get('episodes', [])
					try: episode_meta = [x for x in episode_list if x.get('episode') == next_episode][0]
					except: return
					values = {}
					values['imdb'] = imdb_id
					values['tmdb'] = tmdb_id
					values['tvdb'] = tmdb_result.get('tvdb', '') if tmdb_result else ''
					values['lastplayed'] = i.get('lastplayed', '')
					values['snum'] = next_season
					values['enum'] = next_episode
					if not episode_meta.get('plot'): episode_meta['plot'] = showSeasons.get('plot', '')
					values.update(showSeasons)
					values.update(seasonEpisodes)
					values.update(episode_meta)
					for k in ('episodes', 'snum', 'enum'): values.pop(k, None)
					duration = values.get('duration')
					if duration:
						try: values['duration'] = int(duration) * 60
						except: pass
					air_date = values.get('premiered', '')
					values['unaired'] = ''
					try:
						if values.get('status', '').lower() == 'ended': pass
						elif not air_date: values['unaired'] = 'true'
						elif int(re.sub(r'[^0-9]', '', air_date)) > int(re.sub(r'[^0-9]', '', str(self.today_date))):
							values['unaired'] = 'true'
					except: pass
					if self.enable_fanarttv:
						tvdb = values.get('tvdb', '')
						extended_art = fanarttv_cache.get(FanartTv().get_tvshow_art, 336, tvdb)
						if extended_art: values.update(extended_art)
					if not direct: values['action'] = 'episodes'
					values['localProgress'] = True
					values['extended'] = True
					self.list.append(values)
				except:
					from resources.lib.modules import log_utils
					log_utils.error()

			threads = []
			for i in items:
				threads.append(Thread(target=items_list, args=(i,)))
			[t.start() for t in threads]
			[t.join() for t in threads]
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		return self.list

	def custom_calendar(self, url, folderName=''):
		self.list = []
		try:
			self.list = cache.get(self.custom_progress_list, 0, url)
			self.sort(type='progress')
			if self.list is None: self.list = []
			prior_week = int(re.sub(r'[^0-9]', '', (self.date_time - timedelta(days=7)).strftime('%Y-%m-%d')))
			sorted_list = []
			top_items = [i for i in self.list if i.get('episode') == 1 and i.get('premiered') and (int(re.sub(r'[^0-9]', '', str(i['premiered']))) >= prior_week)]
			sorted_list.extend(top_items)
			sorted_list.extend([i for i in self.list if i not in top_items])
			self.list = sorted_list
			if self.list is None: self.list = []
			if not getSetting('custom.progress.showunaired') == 'true':
				self.list = [i for i in self.list if i.get('unaired', '') != 'true']
			for i in range(len(self.list)): self.list[i]['next'] = ''
			self.episodeDirectory(self.list, unfinished=False, next=False, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def custom_upcoming_progress(self, url, folderName=''):
		self.list = []
		try:
			self.list = cache.get(self.custom_progress_list, 0, url, False, True)
			if self.list:
				self.list = sorted(self.list, key=lambda k: (k['premiered'] if k.get('premiered') else '3021-01-01', k.get('airtime', '')))
			if self.list is None: self.list = []
			self.episodeDirectory(self.list, unfinished=False, next=False, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def custom_progress_list(self, url='', direct=False, upcoming=False):
		# Uses GET /shows/{imdb}/progress/watched (confirmed to match real Trakt's
		# shape) for each show's authoritative next_episode when an imdb id is known;
		# falls back to walking the first unwatched episode in chronological order
		# from the local watched-episode set when no imdb id or progress data exists.
		self.list = []
		try:
			episodes = customtraktsync.get_watched_episodes()
			if not episodes: return self.list
			shows = {}
			for (show_imdb, show_tmdb, show_tvdb, season, episode) in episodes:
				shows.setdefault(show_imdb, {'imdb': show_imdb, 'tmdb': show_tmdb, 'tvdb': show_tvdb, 'watched_set': set()})
				shows[show_imdb]['watched_set'].add((int(season), int(episode)))
			try:
				for (show_imdb, show_tmdb, show_tvdb, last_watched_at) in customtraktsync.get_watched_shows():
					if show_imdb in shows: shows[show_imdb]['lastplayed'] = last_watched_at
			except: pass
			items = list(shows.values())
			if not items: return self.list

			def items_list(i):
				imdb_id = i.get('imdb', '')
				tmdb_id = i.get('tmdb', '')
				watched_set = i.get('watched_set', set())
				try:
					# "Next episode" = the episode after the highest-numbered watched
					# episode in the highest-numbered season with any watched episode —
					# matches real Trakt's own progress semantics (resume from your
					# furthest point), not the first unwatched episode in chronological
					# order. A show watched out of order (e.g. S2E5 watched, S2E1-4
					# never watched) should resume at S2E6, not jump back to S1E1.
					candidates = watched_set if self.showspecials else set((s, e) for (s, e) in watched_set if s != 0)
					if not candidates: return
					furthest_season = max(s for (s, e) in candidates)
					furthest_episode = max(e for (s, e) in candidates if s == furthest_season)
					if not tmdb_id and imdb_id:
						tmdb_result = cache.get(tmdb_indexer().IdLookup, 96, imdb_id, i.get('tvdb', ''))
						tmdb_id = str(tmdb_result.get('id')) if tmdb_result else ''
					if not tmdb_id: return
					showSeasons = cache.get(tmdb_indexer().get_showSeasons_meta, 96, tmdb_id)
					if not showSeasons: return
					seasons_meta = {s.get('season_number'): s for s in showSeasons.get('seasons', [])}
					season_meta = seasons_meta.get(furthest_season)
					if season_meta and furthest_episode < season_meta.get('episode_count', 0):
						next_season, next_episode = furthest_season, furthest_episode + 1
					else:
						next_season, next_episode = furthest_season + 1, 1
					if next_season not in seasons_meta: return  # no further known season — fully caught up
					seasonEpisodes = tmdb_indexer().get_seasonEpisodes_meta_checked(tmdb_id, next_season)
					if not seasonEpisodes: return
					episode_list = seasonEpisodes.get('episodes', [])
					try: episode_meta = [x for x in episode_list if x.get('episode') == next_episode][0]
					except: return
					values = {}
					values['imdb'] = imdb_id
					values['tmdb'] = tmdb_id
					values['tvdb'] = i.get('tvdb', '')
					values['lastplayed'] = i.get('lastplayed', '')
					values['snum'] = next_season
					values['enum'] = next_episode
					try:
						show_summary = trakt.getTVShowSummary(imdb_id, full=False) if imdb_id else None
						airs = (show_summary or {}).get('airs', {}) or {}
						values['airday'] = airs.get('day', '')
						values['airtime'] = airs.get('time', '')
						values['airzone'] = airs.get('timezone', '')
					except: pass
					if not episode_meta.get('plot'): episode_meta['plot'] = showSeasons.get('plot', '')
					values.update(showSeasons)
					values.update(seasonEpisodes)
					values.update(episode_meta)
					for k in ('episodes', 'snum', 'enum'): values.pop(k, None)
					duration = values.get('duration')
					if duration:
						try: values['duration'] = int(duration) * 60
						except: pass
					air_date = values.get('premiered', '')
					values['unaired'] = ''
					if upcoming:
						values['customUpcomingProgress'] = True
						try:
							if values.get('status', '').lower() == 'ended': return
							elif not air_date: values['unaired'] = 'true'
							elif int(re.sub(r'[^0-9]', '', air_date)) > int(re.sub(r'[^0-9]', '', str(self.today_date))):
								values['unaired'] = 'true'
							else: return  # already aired (today or earlier) - not "upcoming"
						except:
							from resources.lib.modules import log_utils
							log_utils.error('tvshowtitle = %s' % values.get('tvshowtitle', ''))
					else:
						values['customProgress'] = True
						try:
							if values.get('status', '').lower() == 'ended': pass
							elif not air_date: values['unaired'] = 'true'
							elif int(re.sub(r'[^0-9]', '', air_date)) > int(re.sub(r'[^0-9]', '', str(self.today_date))):
								values['unaired'] = 'true'
						except: pass
					if self.enable_fanarttv:
						tvdb = values.get('tvdb', '')
						extended_art = fanarttv_cache.get(FanartTv().get_tvshow_art, 336, tvdb)
						if extended_art: values.update(extended_art)
					if not direct: values['action'] = 'episodes'
					values['extended'] = True
					self.list.append(values)
				except:
					from resources.lib.modules import log_utils
					log_utils.error()

			threads = []
			for i in items:
				threads.append(Thread(target=items_list, args=(i,)))
			# Batched: each thread may need a TMDb lookup/season-meta fetch — throttled
			# to avoid hammering the TMDb cache layer with too many threads at once.
			_unlimited = getSetting('dev.batch.unlimited') == 'true'
			_bs = max(int(getSetting('dev.batch.size') or '10'), 1)
			_chunk = max(len(threads), 1) if _unlimited else _bs
			for i in range(0, len(threads), _chunk):
				if control.monitor.abortRequested(): break
				batch = threads[i:i + _chunk]
				[t.start() for t in batch]
				[t.join() for t in batch]
			try:
				dropped = customtraktsync.fetch_dropped('shows_dropped')
				if dropped:
					dropped_tmdb = {str(i['tmdb']) for i in dropped if i.get('tmdb')}
					dropped_imdb = {str(i['imdb']) for i in dropped if i.get('imdb')}
					self.list = [i for i in self.list if not (
						(i.get('tmdb') and str(i['tmdb']) in dropped_tmdb) or
						(i.get('imdb') and str(i['imdb']) in dropped_imdb)
					)]
			except: pass
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		return self.list

	def floppy_calendar(self, url, folderName=''):
		# Paginated the same way Trakt's own Progress list is (calendar(), above) — this
		# was unconditionally rendering every in-progress show's next episode on one
		# screen (next=False), unlike every other provider's episode progress list.
		self.list = []
		try:
			try:
				if '?' not in url:
					url = 'floppyepisodesprogress?limit=%s&page=1' % (self.count or 20)
				q = dict(parse_qsl(urlsplit(url).query))
				index = int(q.get('page', 1)) - 1
				page_limit = max(1, int(q['limit'])) if q.get('limit') else max(1, int(self.count) if self.count else 20)
			except:
				index = 0
				page_limit = max(1, int(self.count) if self.count else 20)
			self.list = cache.get(self.floppy_progress_list, 0, url)
			self.sort(type='progress')
			if self.list is None: self.list = []
			prior_week = int(re.sub(r'[^0-9]', '', (self.date_time - timedelta(days=7)).strftime('%Y-%m-%d')))
			sorted_list = []
			top_items = [i for i in self.list if i.get('episode') == 1 and i.get('premiered') and (int(re.sub(r'[^0-9]', '', str(i['premiered']))) >= prior_week)]
			sorted_list.extend(top_items)
			sorted_list.extend([i for i in self.list if i not in top_items])
			self.list = sorted_list
			if self.list is None: self.list = []
			if not getSetting('floppy.progress.showunaired') == 'true':
				self.list = [i for i in self.list if i.get('unaired', '') != 'true']
			next_url = ''
			hasNext = False
			if getSetting('floppy.paginate.lists') == 'true' and self.list:
				paginated_ids = [self.list[x:x + page_limit] for x in range(0, len(self.list), page_limit)]
				total_pages = len(paginated_ids)
				self.list = paginated_ids[index] if index < total_pages else []
				try:
					if index + 1 >= total_pages: raise Exception()
					next_page = index + 2
					next_url = 'plugin://plugin.video.umbrella/?action=floppy_episodes_progress&url=%s&page=%s&folderName=%s' % (
						quote_plus('floppyepisodesprogress?limit=%s&page=%s' % (page_limit, next_page)),
						str(next_page), quote_plus(folderName))
					hasNext = True
				except: pass
			for i in range(len(self.list)): self.list[i]['next'] = next_url
			self.episodeDirectory(self.list, unfinished=False, next=hasNext, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def floppy_upcoming_progress(self, url, folderName=''):
		self.list = []
		try:
			self.list = cache.get(self.floppy_progress_list, 0, url, False, True)
			if self.list:
				self.list = sorted(self.list, key=lambda k: (k['premiered'] if k.get('premiered') else '3021-01-01', k.get('airtime', '')))
			if self.list is None: self.list = []
			self.episodeDirectory(self.list, unfinished=False, next=False, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def floppy_progress_list(self, url='', direct=False, upcoming=False):
		# Floppy has no aggregated per-show "next episode" endpoint (unlike Custom's
		# /shows/{imdb}/progress/watched), so this is built entirely from the locally
		# synced watched-episode set (floppysync) — the season-level /history/ progress
		# counts are already expanded into individual (season, episode) rows during sync
		# (_sync_episode_tracking_for_show), so the exact same "furthest watched episode"
		# resume logic as Custom's progress list applies unmodified.
		self.list = []
		try:
			episodes = floppysync.get_watched_episodes()
			if not episodes: return self.list
			shows = {}
			for (show_imdb, show_tmdb, show_tvdb, season, episode) in episodes:
				shows.setdefault(show_imdb, {'imdb': show_imdb, 'tmdb': show_tmdb, 'tvdb': show_tvdb, 'watched_set': set()})
				shows[show_imdb]['watched_set'].add((int(season), int(episode)))
			try:
				for (show_imdb, show_tmdb, show_tvdb, last_watched_at) in floppysync.get_watched_shows():
					if show_imdb in shows: shows[show_imdb]['lastplayed'] = last_watched_at
			except: pass
			items = list(shows.values())
			if not items: return self.list

			def items_list(i):
				imdb_id = i.get('imdb', '')
				tmdb_id = i.get('tmdb', '')
				watched_set = i.get('watched_set', set())
				try:
					# "Next episode" = the episode after the highest-numbered watched
					# episode in the highest-numbered season with any watched episode —
					# matches real Trakt's own progress semantics (resume from your
					# furthest point), not the first unwatched episode in chronological
					# order. A show watched out of order (e.g. S2E5 watched, S2E1-4
					# never watched) should resume at S2E6, not jump back to S1E1.
					candidates = watched_set if self.showspecials else set((s, e) for (s, e) in watched_set if s != 0)
					if not candidates: return
					furthest_season = max(s for (s, e) in candidates)
					furthest_episode = max(e for (s, e) in candidates if s == furthest_season)
					if not tmdb_id and imdb_id:
						tmdb_result = cache.get(tmdb_indexer().IdLookup, 96, imdb_id, i.get('tvdb', ''))
						tmdb_id = str(tmdb_result.get('id')) if tmdb_result else ''
					if not tmdb_id: return
					showSeasons = cache.get(tmdb_indexer().get_showSeasons_meta, 96, tmdb_id)
					if not showSeasons: return
					seasons_meta = {s.get('season_number'): s for s in showSeasons.get('seasons', [])}
					season_meta = seasons_meta.get(furthest_season)
					if season_meta and furthest_episode < season_meta.get('episode_count', 0):
						next_season, next_episode = furthest_season, furthest_episode + 1
					else:
						next_season, next_episode = furthest_season + 1, 1
					if next_season not in seasons_meta: return  # no further known season — fully caught up
					seasonEpisodes = tmdb_indexer().get_seasonEpisodes_meta_checked(tmdb_id, next_season)
					if not seasonEpisodes: return
					episode_list = seasonEpisodes.get('episodes', [])
					try: episode_meta = [x for x in episode_list if x.get('episode') == next_episode][0]
					except: return
					values = {}
					values['imdb'] = imdb_id
					values['tmdb'] = tmdb_id
					values['tvdb'] = i.get('tvdb', '')
					values['lastplayed'] = i.get('lastplayed', '')
					values['snum'] = next_season
					values['enum'] = next_episode
					try:
						show_summary = trakt.getTVShowSummary(imdb_id, full=False) if imdb_id else None
						airs = (show_summary or {}).get('airs', {}) or {}
						values['airday'] = airs.get('day', '')
						values['airtime'] = airs.get('time', '')
						values['airzone'] = airs.get('timezone', '')
					except: pass
					if not episode_meta.get('plot'): episode_meta['plot'] = showSeasons.get('plot', '')
					values.update(showSeasons)
					values.update(seasonEpisodes)
					values.update(episode_meta)
					for k in ('episodes', 'snum', 'enum'): values.pop(k, None)
					duration = values.get('duration')
					if duration:
						try: values['duration'] = int(duration) * 60
						except: pass
					air_date = values.get('premiered', '')
					values['unaired'] = ''
					if upcoming:
						values['floppyUpcomingProgress'] = True
						try:
							if values.get('status', '').lower() == 'ended': return
							elif not air_date: values['unaired'] = 'true'
							elif int(re.sub(r'[^0-9]', '', air_date)) > int(re.sub(r'[^0-9]', '', str(self.today_date))):
								values['unaired'] = 'true'
							else: return  # already aired (today or earlier) - not "upcoming"
						except:
							from resources.lib.modules import log_utils
							log_utils.error('tvshowtitle = %s' % values.get('tvshowtitle', ''))
					else:
						values['floppyProgress'] = True
						try:
							if values.get('status', '').lower() == 'ended': pass
							elif not air_date: values['unaired'] = 'true'
							elif int(re.sub(r'[^0-9]', '', air_date)) > int(re.sub(r'[^0-9]', '', str(self.today_date))):
								values['unaired'] = 'true'
						except: pass
					if self.enable_fanarttv:
						tvdb = values.get('tvdb', '')
						extended_art = fanarttv_cache.get(FanartTv().get_tvshow_art, 336, tvdb)
						if extended_art: values.update(extended_art)
					if not direct: values['action'] = 'episodes'
					values['extended'] = True
					self.list.append(values)
				except:
					from resources.lib.modules import log_utils
					log_utils.error()

			threads = []
			for i in items:
				threads.append(Thread(target=items_list, args=(i,)))
			_unlimited = getSetting('dev.batch.unlimited') == 'true'
			_bs = max(int(getSetting('dev.batch.size') or '10'), 1)
			_chunk = max(len(threads), 1) if _unlimited else _bs
			for i in range(0, len(threads), _chunk):
				if control.monitor.abortRequested(): break
				batch = threads[i:i + _chunk]
				[t.start() for t in batch]
				[t.join() for t in batch]
			try:
				dropped = floppysync.fetch_status_list('shows_dropped')
				if dropped:
					dropped_tmdb = {str(i['tmdb']) for i in dropped if i.get('tmdb')}
					self.list = [i for i in self.list if not (i.get('tmdb') and str(i['tmdb']) in dropped_tmdb)]
			except: pass
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		return self.list

	def scrob_calendar(self, url, folderName=''):
		# Same paginated shape as floppy_calendar() — ported verbatim, sourced from
		# scrobsync instead of floppysync.
		self.list = []
		try:
			try:
				if '?' not in url:
					url = 'scrobepisodesprogress?limit=%s&page=1' % (self.count or 20)
				q = dict(parse_qsl(urlsplit(url).query))
				index = int(q.get('page', 1)) - 1
				page_limit = max(1, int(q['limit'])) if q.get('limit') else max(1, int(self.count) if self.count else 20)
			except:
				index = 0
				page_limit = max(1, int(self.count) if self.count else 20)
			self.list = cache.get(self.scrob_progress_list, 0, url)
			self.sort(type='progress')
			if self.list is None: self.list = []
			prior_week = int(re.sub(r'[^0-9]', '', (self.date_time - timedelta(days=7)).strftime('%Y-%m-%d')))
			sorted_list = []
			top_items = [i for i in self.list if i.get('episode') == 1 and i.get('premiered') and (int(re.sub(r'[^0-9]', '', str(i['premiered']))) >= prior_week)]
			sorted_list.extend(top_items)
			sorted_list.extend([i for i in self.list if i not in top_items])
			self.list = sorted_list
			if self.list is None: self.list = []
			self.list = [i for i in self.list if i.get('unaired', '') != 'true']
			next_url = ''
			hasNext = False
			if getSetting('scrob.paginate.lists') == 'true' and self.list:
				paginated_ids = [self.list[x:x + page_limit] for x in range(0, len(self.list), page_limit)]
				total_pages = len(paginated_ids)
				self.list = paginated_ids[index] if index < total_pages else []
				try:
					if index + 1 >= total_pages: raise Exception()
					next_page = index + 2
					next_url = 'plugin://plugin.video.umbrella/?action=scrob_episodes_progress&url=%s&page=%s&folderName=%s' % (
						quote_plus('scrobepisodesprogress?limit=%s&page=%s' % (page_limit, next_page)),
						str(next_page), quote_plus(folderName))
					hasNext = True
				except: pass
			for i in range(len(self.list)): self.list[i]['next'] = next_url
			self.episodeDirectory(self.list, unfinished=False, next=hasNext, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def scrob_upcoming_progress(self, url, folderName=''):
		self.list = []
		try:
			self.list = cache.get(self.scrob_progress_list, 0, url, False, True)
			if self.list:
				self.list = sorted(self.list, key=lambda k: (k['premiered'] if k.get('premiered') else '3021-01-01', k.get('airtime', '')))
			if self.list is None: self.list = []
			self.episodeDirectory(self.list, unfinished=False, next=False, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def scrob_progress_list(self, url='', direct=False, upcoming=False):
		# Ported verbatim from floppy_progress_list() — Scrob's GET /history/next-up
		# is server-computed, but doesn't carry the TMDb-enriched fields (plot/art/
		# premiered) episodeDirectory() needs, so this still builds "next episode" the
		# same locally-reconstructed way from the synced watched-episode set.
		self.list = []
		try:
			episodes = scrobsync.get_watched_episodes()
			if not episodes: return self.list
			shows = {}
			for (show_imdb, show_tmdb, show_tvdb, season, episode) in episodes:
				shows.setdefault(show_imdb, {'imdb': show_imdb, 'tmdb': show_tmdb, 'tvdb': show_tvdb, 'watched_set': set()})
				shows[show_imdb]['watched_set'].add((int(season), int(episode)))
			try:
				for (show_imdb, show_tmdb, show_tvdb, last_watched_at) in scrobsync.get_watched_shows():
					if show_imdb in shows: shows[show_imdb]['lastplayed'] = last_watched_at
			except: pass
			items = list(shows.values())
			if not items: return self.list

			def items_list(i):
				imdb_id = i.get('imdb', '')
				tmdb_id = i.get('tmdb', '')
				watched_set = i.get('watched_set', set())
				try:
					candidates = watched_set if self.showspecials else set((s, e) for (s, e) in watched_set if s != 0)
					if not candidates: return
					furthest_season = max(s for (s, e) in candidates)
					furthest_episode = max(e for (s, e) in candidates if s == furthest_season)
					if not tmdb_id and imdb_id:
						tmdb_result = cache.get(tmdb_indexer().IdLookup, 96, imdb_id, i.get('tvdb', ''))
						tmdb_id = str(tmdb_result.get('id')) if tmdb_result else ''
					if not tmdb_id: return
					showSeasons = cache.get(tmdb_indexer().get_showSeasons_meta, 96, tmdb_id)
					if not showSeasons: return
					seasons_meta = {s.get('season_number'): s for s in showSeasons.get('seasons', [])}
					season_meta = seasons_meta.get(furthest_season)
					if season_meta and furthest_episode < season_meta.get('episode_count', 0):
						next_season, next_episode = furthest_season, furthest_episode + 1
					else:
						next_season, next_episode = furthest_season + 1, 1
					if next_season not in seasons_meta: return  # no further known season — fully caught up
					seasonEpisodes = tmdb_indexer().get_seasonEpisodes_meta_checked(tmdb_id, next_season)
					if not seasonEpisodes: return
					episode_list = seasonEpisodes.get('episodes', [])
					try: episode_meta = [x for x in episode_list if x.get('episode') == next_episode][0]
					except: return
					values = {}
					values['imdb'] = imdb_id
					values['tmdb'] = tmdb_id
					values['tvdb'] = i.get('tvdb', '')
					values['lastplayed'] = i.get('lastplayed', '')
					values['snum'] = next_season
					values['enum'] = next_episode
					try:
						show_summary = trakt.getTVShowSummary(imdb_id, full=False) if imdb_id else None
						airs = (show_summary or {}).get('airs', {}) or {}
						values['airday'] = airs.get('day', '')
						values['airtime'] = airs.get('time', '')
						values['airzone'] = airs.get('timezone', '')
					except: pass
					if not episode_meta.get('plot'): episode_meta['plot'] = showSeasons.get('plot', '')
					values.update(showSeasons)
					values.update(seasonEpisodes)
					values.update(episode_meta)
					for k in ('episodes', 'snum', 'enum'): values.pop(k, None)
					duration = values.get('duration')
					if duration:
						try: values['duration'] = int(duration) * 60
						except: pass
					air_date = values.get('premiered', '')
					values['unaired'] = ''
					if upcoming:
						values['scrobUpcomingProgress'] = True
						try:
							if values.get('status', '').lower() == 'ended': return
							elif not air_date: values['unaired'] = 'true'
							elif int(re.sub(r'[^0-9]', '', air_date)) > int(re.sub(r'[^0-9]', '', str(self.today_date))):
								values['unaired'] = 'true'
							else: return  # already aired (today or earlier) - not "upcoming"
						except:
							from resources.lib.modules import log_utils
							log_utils.error('tvshowtitle = %s' % values.get('tvshowtitle', ''))
					else:
						values['scrobProgress'] = True
						try:
							if values.get('status', '').lower() == 'ended': pass
							elif not air_date: values['unaired'] = 'true'
							elif int(re.sub(r'[^0-9]', '', air_date)) > int(re.sub(r'[^0-9]', '', str(self.today_date))):
								values['unaired'] = 'true'
						except: pass
					if self.enable_fanarttv:
						tvdb = values.get('tvdb', '')
						extended_art = fanarttv_cache.get(FanartTv().get_tvshow_art, 336, tvdb)
						if extended_art: values.update(extended_art)
					if not direct: values['action'] = 'episodes'
					values['extended'] = True
					self.list.append(values)
				except:
					from resources.lib.modules import log_utils
					log_utils.error()

			threads = []
			for i in items:
				threads.append(Thread(target=items_list, args=(i,)))
			_unlimited = getSetting('dev.batch.unlimited') == 'true'
			_bs = max(int(getSetting('dev.batch.size') or '10'), 1)
			_chunk = max(len(threads), 1) if _unlimited else _bs
			for i in range(0, len(threads), _chunk):
				if control.monitor.abortRequested(): break
				batch = threads[i:i + _chunk]
				[t.start() for t in batch]
				[t.join() for t in batch]
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		return self.list

	def custom_calendar_items(self, media_type='shows', days=33, start_date=None):
		# Flat episode-reference items from Custom's /calendars/my/shows/{date}/{days},
		# mapped into the same shape trakt_list() produces so trakt_episodes_list can
		# enrich them with TMDb data unmodified. Confirmed schema: ShowCalendarItem =
		# {first_aired, episode: EpisodeOut, show: ShowOut} — first_aired lives on the
		# calendar item itself, not on the nested episode object.
		items = []
		try:
			raw = customtrakt.get_calendar(media_type, days, start_date=start_date)
			if not raw: return items
			for item in raw:
				try:
					show = item.get('show', {})
					ep = item.get('episode', {})
					season, episode = ep.get('season'), ep.get('number')
					if season is None or episode is None: continue
					if not self.showspecials and season == 0: continue
					tvshowtitle = show.get('title')
					if not tvshowtitle: continue
					ids = show.get('ids', {})
					values = {
						'title': ep.get('title') or '', 'season': season, 'episode': episode,
						'tvshowtitle': tvshowtitle, 'year': str(show.get('year', '')) if show.get('year') else '',
						'premiered': item.get('first_aired') or ep.get('first_aired') or ep.get('premiered', ''),
						'imdb': str(ids.get('imdb', '')) if ids.get('imdb') else '',
						'tmdb': str(ids.get('tmdb', '')) if ids.get('tmdb') else '',
						'tvdb': str(ids.get('tvdb', '')) if ids.get('tvdb') else '',
						'next': '',
					}
					items.append(values)
				except: pass
			try:
				dropped = customtraktsync.fetch_dropped('shows_dropped')
				if dropped:
					dropped_tmdb = {str(i['tmdb']) for i in dropped if i.get('tmdb')}
					dropped_imdb = {str(i['imdb']) for i in dropped if i.get('imdb')}
					items = [i for i in items if not (
						(i.get('tmdb') and str(i['tmdb']) in dropped_tmdb) or
						(i.get('imdb') and str(i['imdb']) in dropped_imdb)
					)]
			except: pass
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		return items

	def custom_calendar_recent(self, url, folderName=''):
		# "Recent" needs a window that actually reaches into the past — Trakt's own
		# equivalent link (mycalendarRecent_link) requests date[30] (today minus 30
		# days) then locally filters down to premiered<=today. custom_calendar_items()
		# defaults to starting *today* when no start_date is given (matching Upcoming/
		# Premieres, which correctly want a future-only window), so without an explicit
		# override here every item in the [today, today+33] window gets thrown away by
		# the premiered<=today filter below, leaving Recent empty.
		self.list = []
		try:
			recent_start = (self.date_time - timedelta(days=30)).strftime('%Y-%m-%d')
			items = cache.get(self.custom_calendar_items, 1, 'shows', 33, recent_start)
			self.list = self.trakt_episodes_list('customcalendarrecent', self.trakt_user, self.lang, items=items)
			if self.list:
				self.list = [i for i in self.list if int(re.sub(r'[^0-9]', '', str(i['premiered']).split('T')[0])) <= int(re.sub(r'[^0-9]', '', str(self.today_date)))]
				for i in range(len(self.list)): self.list[i]['calendar_recent'] = True
				self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=True)
			if self.list is None: self.list = []
			self.episodeDirectory(self.list, unfinished=False, next=False, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def custom_calendar_upcoming(self, url, folderName=''):
		self.list = []
		try:
			items = cache.get(self.custom_calendar_items, 1, 'shows', 33)
			self.list = self.trakt_episodes_list('customcalendarupcoming', self.trakt_user, self.lang, items=items)
			if self.list:
				self.list = [i for i in self.list if int(re.sub(r'[^0-9]', '', str(i['premiered']).split('T')[0])) >= int(re.sub(r'[^0-9]', '', str(self.today_date)))]
				for i in range(len(self.list)): self.list[i]['calendar_unaired'] = True
				self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=False)
			if self.list is None: self.list = []
			self.episodeDirectory(self.list, unfinished=False, next=False, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def custom_calendar_premieres(self, url, folderName=''):
		self.list = []
		try:
			items = cache.get(self.custom_calendar_items, 1, 'shows', 33)
			self.list = self.trakt_episodes_list('customcalendarpremieres', self.trakt_user, self.lang, items=items)
			if self.list:
				self.list = [i for i in self.list if i.get('episode') == 1 and
					int(re.sub(r'[^0-9]', '', str(i['premiered']).split('T')[0])) >= int(re.sub(r'[^0-9]', '', str(self.today_date)))]
				for i in range(len(self.list)): self.list[i]['calendar_unaired'] = True
				self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=False)
			if self.list is None: self.list = []
			self.episodeDirectory(self.list, unfinished=False, next=False, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32326, message=33049)

	def sort(self, type='shows'):
		try:
			if not self.list: return
			attribute = int(getSetting('sort.%s.type' % type))
			reverse = int(getSetting('sort.%s.order' % type)) == 1
			if attribute == 0: reverse = False # Sorting Order is not enabled when sort method is "Default"
			if attribute > 0:
				if attribute == 1:
					try: self.list = sorted(self.list, key=lambda k: re.sub(r'(^the |^a |^an )', '', k['tvshowtitle'].lower()), reverse=reverse)
					except: self.list = sorted(self.list, key=lambda k: k['title'].lower(), reverse=reverse)
				elif attribute == 2: self.list = sorted(self.list, key=lambda k: float(k['rating']), reverse=reverse)
				elif attribute == 3: self.list = sorted(self.list, key=lambda k: int(k['votes'].replace(',', '')), reverse=reverse)
				elif attribute == 4:
					for i in range(len(self.list)):
						if 'premiered' not in self.list[i]: self.list[i]['premiered'] = ''
					self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=reverse)
				elif attribute == 5:
					for i in range(len(self.list)):
						if 'added' not in self.list[i]: self.list[i]['added'] = ''
					self.list = sorted(self.list, key=lambda k: k['added'], reverse=reverse)
				elif attribute == 6:
					for i in range(len(self.list)):
						if 'lastplayed' not in self.list[i]: self.list[i]['lastplayed'] = ''
					self.list = sorted(self.list, key=lambda k: k['lastplayed'], reverse=reverse)
			elif reverse:
				self.list = list(reversed(self.list))
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def calendars(self, create_directory=True, folderName=''):
		m = getLS(32060).split('|')
		try: months = [(m[0], 'January'), (m[1], 'February'), (m[2], 'March'), (m[3], 'April'), (m[4], 'May'), (m[5], 'June'), (m[6], 'July'),
					(m[7], 'August'), (m[8], 'September'), (m[9], 'October'), (m[10], 'November'), (m[11], 'December')]
		except: months = []
		d = getLS(32061).split('|')
		try: days = [(d[0], 'Monday'), (d[1], 'Tuesday'), (d[2], 'Wednesday'), (d[3], 'Thursday'), (d[4], 'Friday'), (d[5], 'Saturday'), (d[6], 'Sunday')]
		except: days = []
		for i in range(0, 30):
			try:
				name = (self.date_time - timedelta(days=i))
				name = (getLS(32062) % (name.strftime('%A'), name.strftime('%d %B')))
				for m in months: name = name.replace(m[1], m[0])
				for d in days: name = name.replace(d[1], d[0])
				url = self.calendar_link % (self.date_time - timedelta(days=i)).strftime('%Y-%m-%d')
				self.list.append({'name': name, 'url': url, 'image': 'calendar.png', 'icon': 'DefaultYear.png', 'action': 'calendar'})
			except: pass
		if create_directory: self.addDirectory(self.list, folderName=folderName)
		return self.list

	def tmdb_list(self, tvshowtitle, imdb, tmdb, tvdb, meta, season):
		if not tmdb and (imdb or tvdb):
			try:
				result = cache.get(tmdb_indexer().IdLookup, 96, imdb, tvdb)
				tmdb = str(result.get('id')) if result.get('id') else ''
			except:
				if getSetting('debug.level') != '1': return
				from resources.lib.modules import log_utils
				return log_utils.log('tvshowtitle: (%s) missing tmdb_id: ids={imdb: %s, tmdb: %s, tvdb: %s}' % (tvshowtitle, imdb, tmdb, tvdb), __name__, log_utils.LOGDEBUG) # log TMDb shows that they do not have
		seasonEpisodes = tmdb_indexer().get_seasonEpisodes_meta(tmdb, season)

		if not seasonEpisodes: return
		if not isinstance(meta, dict): showSeasons = jsloads(meta)
		else: showSeasons = meta
		list = []
		unaired_count = 0
		for item in seasonEpisodes['episodes']:
			try:
				values = {}
				values.update(seasonEpisodes)
				values.update(item)
				values['tvshowtitle'] = tvshowtitle
				values['year'] = showSeasons.get('year')
				values['trailer'] = showSeasons.get('trailer')
				values['imdb'] = imdb or ''
				values['tvdb'] = tvdb or ''
				values['aliases'] = showSeasons.get('aliases', [])
				values['country_codes'] = showSeasons.get('country_codes', [])
				values['total_seasons'] = showSeasons.get('total_seasons')
				values['counts'] = showSeasons.get('counts')
				values['studio'] = showSeasons.get('studio')
				values['genre'] = showSeasons.get('genre')
				try: values['duration'] = (int(seasonEpisodes.get('episodes')[(int(item.get('episode'))-1)].get('duration'))*60) # showSeasons already converted to seconds
				except: values['duration'] = ''
				values['mpaa'] = showSeasons.get('mpaa')
				values['status'] = showSeasons.get('status','')
				values['unaired'] = ''
				try:
					if values['status'].lower() == 'ended': pass
					elif not values['premiered']:
						values['unaired'] = 'true'
						unaired_count += 1
						pass
					elif int(re.sub(r'[^0-9]', '', str(values['premiered']))) > int(re.sub(r'[^0-9]', '', str(self.today_date))):
						values['unaired'] = 'true'
						unaired_count += 1
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
				values['poster'] = item.get('poster') or showSeasons.get('poster')
				values['episode_type'] = item.get('episode_type')
				values['season_poster'] = item.get('season_poster') or showSeasons.get('season_poster')
				values['fanart'] = showSeasons.get('fanart')
				values['icon'] = showSeasons.get('icon')
				values['banner'] = showSeasons.get('banner')
				values['clearlogo'] = showSeasons.get('clearlogo')
				values['clearart'] = showSeasons.get('clearart')
				values['landscape'] = showSeasons.get('landscape')
				values['extended'] = True # used to bypass calling "super_info()", super_info() no longer used as of 4-12-21 so this could be removed.
				for k in ('episodes',): values.pop(k, None) # pop() keys from seasonEpisodes that are not needed anymore
				list.append(values)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		for i in range(0, len(list)): list[i].update({'season_isAiring': 'true' if unaired_count >0 else 'false'}) # update for if "season_isAiring", needed for season pack scraping
		if unaired_count >0:
			for i in range(0, len(list)): list[i].update({'next_episode_to_air': {'air_date': '2022-02-10', 'episode_number': 7}})
		return list

	def trakt_progress_list(self, url, user, lang, direct=False, upcoming=False):
		#https://api.trakt.tv/users/me/watched/shows?extended=full

		try:
			url += ('&' if '?' in url else '?') + 'extended=progress'
			result = trakt.get_all_pages(url)
			if not result: return
		except: return
		items = []
		# progress_showunaired = getSetting('trakt.progress.showunaired') == 'true'
		for item in result:
			try:
				values = {}
				num_1 = sum(len(item['seasons'][i]['episodes']) for i in range(len(item['seasons'])) if item['seasons'][i]['number'] > 0)
				num_2 = int(item['show'].get('aired_episodes', 0)) # trakt slow to update "aired_episodes" count on day item airs
				values['has_next_episode'] = num_1 < num_2
				if not upcoming and item['show'].get('status', '').lower() == 'ended': # only chk ended cases for all watched otherwise airing today cases get dropped.
					if num_1 >= num_2: continue
				season_sort = sorted(item['seasons'][:], key=lambda k: k['number'], reverse=False) # trakt sometimes places season0 at end and episodes out of order. So we sort it to be sure.
				values['snum'] = season_sort[-1]['number']
				episode = [x for x in season_sort[-1]['episodes'] if 'number' in x]
				episode = sorted(episode, key=lambda x: x['number'])
				values['enum'] = episode[-1]['number']
				values['added'] = item.get('show').get('updated_at')
				try: values['lastplayed'] = item.get('last_watched_at')
				except: values['lastplayed'] = ''
				values['tvshowtitle'] = item['show']['title']
				if not values['tvshowtitle']: continue
				ids = item.get('show', {}).get('ids', {})
				values['imdb'] = str(ids.get('imdb', '')) if ids.get('imdb') else ''
				values['tmdb'] = str(ids.get('tmdb', '')) if ids.get('tmdb') else ''
				values['tvdb'] = str(ids.get('tvdb', '')) if ids.get('tvdb') else ''
				try: duration = (int(item['episode']['runtime']) * 60)
				except:
					try:duration = (int(item['show']['runtime']) * 60)
					except: duration = ''
				values['duration'] = duration
				try: values['trailer'] = control.trailer % item['show']['trailer'].split('v=')[1]
				except: values['trailer'] = ''
				try:
					airs = item['show']['airs']
					values['airday'] = airs.get('day', '')
					values['airtime'] = airs.get('time', '')[:5] # Trakt rarely, but does, include seconds in it's airtime.
					values['airzone'] = airs.get('timezone', '')
				except: pass
				items.append(values)

			except: pass
		def items_list(i):
			values = i
			imdb, tmdb, tvdb = i.get('imdb'), i.get('tmdb'), i.get('tvdb')
			if not tmdb and (imdb or tvdb):
				try:
					result = cache.get(tmdb_indexer().IdLookup, 96, imdb, tvdb)
					values['tmdb'] = str(result.get('id', '')) if result.get('id') else ''
				except: pass
			try:
				showSeasons = cache.get(tmdb_indexer().get_showSeasons_meta, 96, tmdb)
				if not showSeasons: return
				key = i['snum'] - 1 if showSeasons['seasons'][0]['season_number'] != 0 else i['snum']
				try: next_episode_num = i['enum'] + 1 if showSeasons['seasons'][key]['episode_count'] > i['enum'] else 1
				except: return
				next_season_num = i['snum'] if next_episode_num == i['enum'] + 1 else i['snum'] + 1
				if next_season_num > showSeasons['total_seasons']: return
				if not self.showspecials and next_season_num == 0: return
				seasonEpisodes = tmdb_indexer().get_seasonEpisodes_meta_checked(tmdb, next_season_num)
				if not seasonEpisodes: return
				seasonEpisodes = dict((k,v) for k, v in iter(seasonEpisodes.items()) if v is not None and v != '') # remove empty keys so .update() doesn't over-write good meta with empty values.
				try: episode_meta = [x for x in seasonEpisodes.get('episodes') if x.get('episode') == next_episode_num][0] # to pull just the episode meta we need
				except: return
				if not episode_meta['plot']: episode_meta['plot'] = showSeasons['plot'] # some plots missing for eps so use season level plot
				values.update(showSeasons)
				values.update(seasonEpisodes)
				values.update(episode_meta)
				# if not self.trakt_progressFlatten or self.trakt_directProgressScrape:
					# for k in ('seasons', 'episodes', 'snum', 'enum'): values.pop(k, None) # pop() keys from showSeasons and seasonEpisodes that are not needed anymore
				for k in ('episodes', 'snum', 'enum'): values.pop(k, None) # pop() keys from showSeasons and seasonEpisodes that are not needed anymore

				try:
					if values.get('premiered') and i.get('airtime'): combined = '%sT%s' % (values['premiered'], values['airtime'])
					else: raise Exception()
					air_datetime_list = tools.convert_time(stringTime=combined, zoneFrom=i.get('airzone', ''), zoneTo='local', formatInput='%Y-%m-%dT%H:%M', formatOutput='%Y-%m-%dT%H:%M').split('T')
					air_date, air_time = air_datetime_list[0], air_datetime_list[1]
				except: air_date, air_time = values.get('premiered', '') if values.get('premiered') else '', i.get('airtime', '') if i.get('airtime') else ''
				values['unaired'] = ''
				if upcoming:
					values['traktUpcomingProgress'] = True
					try:
						if values['status'].lower() == 'ended': return
						elif not air_date: values['unaired'] = 'true'
						elif int(re.sub(r'[^0-9]', '', air_date)) > int(re.sub(r'[^0-9]', '', str(self.today_date))): values['unaired'] = 'true'
						elif int(re.sub(r'[^0-9]', '', air_date)) == int(re.sub(r'[^0-9]', '', str(self.today_date))):
							if air_time:
								time_now = (self.date_time).strftime('%X')
								if int(re.sub(r'[^0-9]', '', air_time)) > int(re.sub(r'[^0-9]', '', str(time_now))[:4]): values['unaired'] = 'true'
								else: return
							else: pass
						else: return
					except:
						from resources.lib.modules import log_utils
						log_utils.error('tvshowtitle = %s' % i['tvshowtitle'])
				else:
					try:
						if values['status'].lower() == 'ended': pass
						elif not air_date:
							values['unaired'] = 'true'
						elif int(re.sub(r'[^0-9]', '', air_date)) > int(re.sub(r'[^0-9]', '', str(self.today_date))):
							values['unaired'] = 'true'
						elif int(re.sub(r'[^0-9]', '', air_date)) == int(re.sub(r'[^0-9]', '', str(self.today_date))):
							if air_time:
								time_now = (self.date_time).strftime('%X')
								if int(re.sub(r'[^0-9]', '', air_time)) > int(re.sub(r'[^0-9]', '', str(time_now))[:4]):
									values['unaired'] = 'true'
							else: pass
					except:
						from resources.lib.modules import log_utils
						log_utils.error('tvshowtitle = %s' % i['tvshowtitle'])
				if not direct: values['action'] = 'episodes' # for direct progress scraping
				values['traktProgress'] = True # for direct progress scraping and multi episode watch counts indicators
				values['extended'] = True # used to bypass calling "super_info()", super_info() no longer used as of 4-12-21 so this could be removed.
				duration = values['duration']
				if duration:
					values.update({'duration': int(duration)*60})
				if self.enable_fanarttv:
					extended_art = fanarttv_cache.get(FanartTv().get_tvshow_art, 336, tvdb)
					if extended_art: values.update(extended_art)
				self.list.append(values)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		threads = []
		append = threads.append
		for i in items:
			append(Thread(target=items_list, args=(i,)))
		from resources.lib.modules import log_utils
		_unlimited = getSetting('dev.batch.unlimited') == 'true'
		_bs = max(int(getSetting('dev.batch.size') or '10'), 1)
		_chunk = max(len(threads), 1) if _unlimited else _bs
		log_utils.log('trakt_progress_list: processing %s shows in batches of %s' % (len(threads), 'unlimited' if _unlimited else _bs), __name__, log_utils.LOGINFO)
		for i in range(0, len(threads), _chunk):
			if control.monitor.abortRequested(): break
			batch = threads[i:i + _chunk]
			[t.start() for t in batch]
			[t.join() for t in batch]
		return self.list

	def trakt_list(self, url, user, folderName):
		itemlist = []
		try:
			for i in re.findall(r'date\[(\d+)\]', url): url = url.replace('date[%s]' % i, (self.date_time - timedelta(days=int(i))).strftime('%Y-%m-%d'))
			q = dict(parse_qsl(urlsplit(url).query))
			q.update({'extended': 'full'})
			q = (urlencode(q)).replace('%2C', ',')
			u = url.replace('?' + urlparse(url).query, '') + '?' + q
			items = trakt.getTraktAsJson(u)
		except: return
		try:
			q = dict(parse_qsl(urlsplit(url).query)) # should not need this a 2nd time
			if int(q['limit']) != len(items): raise Exception()
			q.update({'page': str(int(q['page']) + 1)})
			q = (urlencode(q)).replace('%2C', ',')
			next = url.replace('?' + urlparse(url).query, '') + '?' + q
			next = next + '&folderName=%s' % quote_plus(folderName)
		except: next = ''
		for item in items:
			try:
				if 'show' not in item or 'episode' not in item: continue
				title = item['episode']['title']
				if not title: continue
				try:
					season = item['episode']['season']
					episode = item['episode']['number']
				except: continue
				if not self.showspecials and season == 0: continue
				tvshowtitle = item.get('show').get('title')
				if not tvshowtitle: continue
				year = str(item.get('show').get('year'))
				try: progress = item['progress']
				except: progress = None
				ids = item.get('show', {}).get('ids', {})
				imdb = str(ids.get('imdb', '')) if ids.get('imdb') else ''
				tmdb = str(ids.get('tmdb', '')) if ids.get('tmdb') else ''
				tvdb = str(ids.get('tvdb', '')) if ids.get('tvdb') else ''
				episodeIDS = item.get('episode').get('ids', {}) # not used anymore
				premiered = item.get('episode').get('first_aired') #leave timestamp for better sort of same day items
				added = item['episode']['updated_at'] or item.get('show').get('updated_at', '')
				try: lastplayed = item.get('watched_at', '')
				except: lastplayed = ''
				paused_at = item.get('paused_at', '')
				studio = item.get('show').get('network')
				try: genre = ' / '.join([x.title() for x in item.get('show', {}).get('genres')]) or 'NA'
				except: genre = 'NA'
				try: duration = int(item['episode']['runtime']) * 60
				except:
					try:duration = int(item.get('show').get('runtime')) * 60
					except: duration = ''
				rating = str(item.get('episode').get('rating'))
				votes = str(format(int(item.get('episode').get('votes')),',d'))
				mpaa = item.get('show').get('certification')
				plot = item['episode']['overview'] or item['show']['overview']
				if self.lang != 'en':
					try:
						trans_item = trakt.getTVShowTranslation(imdb, lang=self.lang, season=season, episode=episode, full=True)
						title = trans_item.get('title') or title
						plot = trans_item.get('overview') or plot
						tvshowtitle = trakt.getTVShowTranslation(imdb, lang=self.lang) or tvshowtitle
					except:
						from resources.lib.modules import log_utils
						log_utils.error()
				try: trailer = control.trailer % item['show']['trailer'].split('v=')[1]
				except: trailer = ''
				values = {'title': title, 'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered,
							'added': added, 'lastplayed': lastplayed, 'progress': progress, 'paused_at': paused_at, 'status': 'Continuing',
							'studio': studio, 'genre': genre, 'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa, 'plot': plot,
							'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'trailer': trailer, 'episodeIDS': episodeIDS, 'next': next}
				try:
					airs = item['show']['airs']
					values['airday'] = airs.get('day', '')
					values['airtime'] = airs.get('time', '')
					values['airzone'] = airs.get('timezone', '')
				except: pass
				itemlist.append(values)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		return itemlist

	def trakt_episodes_list(self, url, user, lang, items=None, direct=True):
		self.list = []
		folderName=''
		if not items: items = self.trakt_list(url, user, folderName)
		def items_list(i):
			values = i
			tmdb, tvdb = i['tmdb'], i['tvdb']
			try:
				itemyear = tmdb_indexer().get_showSeasons_meta(tmdb)
				seasonEpisodes = tmdb_indexer().get_seasonEpisodes_meta_checked(tmdb, i['season'])
				if not seasonEpisodes:
					from resources.lib.modules import log_utils
					log_utils.log('CALENDAR: dropped %s S%sE%s (tmdb=%s) - no TMDb season data' % (i.get('tvshowtitle'), i.get('season'), i.get('episode'), tmdb), level=log_utils.LOGWARNING)
					return
				try: episode_meta = [x for x in seasonEpisodes.get('episodes') if x.get('episode') == i['episode']][0] # to pull just the episode meta we need
				except:
					from resources.lib.modules import log_utils
					log_utils.log('CALENDAR: dropped %s S%sE%s (tmdb=%s) - no matching episode in TMDb season data' % (i.get('tvshowtitle'), i.get('season'), i.get('episode'), tmdb), level=log_utils.LOGWARNING)
					return
				if 'premiered' in values and values.get('premiered'):
					episode_meta.pop('premiered') # prefer Trakt premiered because TMDb is fucked for some shows like Family Law off by months
					seasonEpisodes.pop('premiered') # this is series premiered so pop
				values.update(seasonEpisodes)
				values.update(episode_meta)
				values['year'] = itemyear.get('year')
				duration = values['duration']
				if duration:
					values.update({'duration': int(duration)*60})
				for k in ('episodes',): values.pop(k, None) # pop() keys from seasonEpisodes that are not needed anymore
				try: # used for fanart fetch since not available in seasonEpisodes request
					art = cache.get(tmdb_indexer().get_art, 96, tmdb)
					values.update(art)
				except: pass
				if self.enable_fanarttv:
					extended_art = fanarttv_cache.get(FanartTv().get_tvshow_art, 336, tvdb)
					if extended_art: values.update(extended_art)
				values['extended'] = True # used to bypass calling "super_info()", super_info() no longer used as of 4-12-21 so this could be removed.
				if not direct: values['action'] = 'episodes'
				self.list.append(values)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		threads = []
		append = threads.append
		for i in items:
			append(Thread(target=items_list, args=(i,)))
		[i.start() for i in threads]
		[i.join() for i in threads]
		return self.list

	def getFavoriteEpisodes(self, create_directory=True, folderName=''):
		self.list = []
		from resources.lib.modules import favourites
		items = favourites.getFavourites(content='episode')
		def items_list(i):
			values = i[3]
			tmdb, tvdb = i[3].get('tmdb'), i[3].get('tvdb')
			try:
				itemyear = tmdb_indexer().get_showSeasons_meta(tmdb)
				seasonEpisodes = tmdb_indexer().get_seasonEpisodes_meta_checked(tmdb, i[3].get('season'))
				if not seasonEpisodes: return
				try: episode_meta = [x for x in seasonEpisodes.get('episodes') if int(x.get('episode')) == int(i[3].get('episode'))][0] # to pull just the episode meta we need
				except: return
				if 'premiered' in values and values.get('premiered'):
					episode_meta.pop('premiered') # prefer Trakt premiered because TMDb is fucked for some shows like Family Law off by months
					seasonEpisodes.pop('premiered') # this is series premiered so pop
				values.update(seasonEpisodes)
				values.update(episode_meta)
				values['year'] = itemyear.get('year')
				duration = values['duration']
				if duration:
					values.update({'duration': int(duration)*60})
				for k in ('episodes',): values.pop(k, None) # pop() keys from seasonEpisodes that are not needed anymore
				try: # used for fanart fetch since not available in seasonEpisodes request
					art = cache.get(tmdb_indexer().get_art, 96, tmdb)
					values.update(art)
				except: pass
				if self.enable_fanarttv:
					extended_art = fanarttv_cache.get(FanartTv().get_tvshow_art, 336, tvdb)
					if extended_art: values.update(extended_art)
				values['extended'] = True # used to bypass calling "super_info()", super_info() no longer used as of 4-12-21 so this could be removed.
				self.list.append(values)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		threads = []
		append = threads.append
		for i in items:
			append(Thread(target=items_list, args=(i,)))
		[i.start() for i in threads]
		[i.join() for i in threads]
		if self.list is None: self.list = []
		if create_directory: self.episodeDirectory(self.list, folderName=folderName)
		return self.list

	def tvmaze_list(self, url, limit):
		try:
			result = client.request(url, error=True)
			result = jsloads(result)
		except: return
		items = []
		for item in result:
			values = {}
			try:
				if not item['show']['language']: continue
				if 'english' not in item['show']['language'].lower(): continue
				if limit and 'scripted' not in item['show']['type'].lower(): continue
				values['title'] = item.get('name')
				values['season'] = item['season']
				if not values['season']: continue
				if not self.showspecials and values['season'] == 0: continue
				values['episode'] = item['number']
				if values['episode'] is None: continue
				values['premiered'] = item.get('airdate', '')
				try: values['year'] = str(item.get('show', {}).get('premiered', ''))[:4] # shows year
				except: values['year'] = ''
				values['tvshowtitle'] = item.get('show', {}).get('name')
				ids = item.get('show', {}).get('externals', {})
				imdb = str(ids.get('imdb', '')) if ids.get('imdb') else ''
				tmdb = '' # TVMaze does not have tmdb in their api
				tvdb = str(ids.get('thetvdb', '')) if ids.get('thetvdb') else ''
				try: values['poster'] = item['show']['image']['original']
				except: values['poster'] = ''
				try: values['thumb'] = item['image']['original']
				except: values['thumb'] = ''
				if not values['thumb']: values['thumb'] = values['poster']
				studio = item.get('show').get('webChannel') or item.get('show').get('network')
				values['studio'] = studio.get('name') or ''
				values['genre'] = []
				for i in item['show']['genres']: values['genre'].append(i.title())
				try: values['duration'] = int(item.get('show', {}).get('runtime', '')) * 60
				except: values['duration'] = ''
				values['rating'] = str(item.get('show', {}).get('rating', {}).get('average', ''))
				try: values['status'] = str(item.get('show', {}).get('status', ''))
				except: values['status'] = 'Continuing'
				try:
					plot = item.get('show', {}).get('summary', '')
					values['plot'] = re.sub(r'<.+?>|</.+?>|\n', '', plot)
				except: values['plot'] = ''
				try: values['airday'] = item['show']['schedule']['days'][0]
				except: values['airday'] = ''
				values['airtime'] = item['airtime'] or ''
				try: values['airzone'] = item['show']['network']['country']['timezone']
				except: values['airzone'] = ''
				values['extended'] = True
				values['ForceAirEnabled'] = True
				if getSetting('tvshows.calendar.extended') == 'true':
					if imdb: 
						trakt_ids = trakt.IdLookup('imdb', imdb, 'show')
						if trakt_ids:
							if not tvdb: tvdb = str(trakt_ids.get('tvdb', '')) if trakt_ids.get('tvdb') else ''
							tmdb = str(trakt_ids.get('tmdb', '')) if trakt_ids.get('tmdb') else ''
					elif not imdb and tvdb:
						trakt_ids = trakt.IdLookup('tvdb', tvdb, 'show')
						if trakt_ids:
							imdb = str(trakt_ids.get('imdb', '')) if trakt_ids.get('imdb') else ''
							tmdb = str(trakt_ids.get('tmdb', '')) if trakt_ids.get('tmdb') else ''
					if not values['poster'] or not values['thumb']:
						try:
							art = cache.get(tmdb_indexer().get_art, 96, tmdb)
							if not values['poster']: values['poster'] = art['poster3'] or ''
							if not values['thumb']: values['thumb'] = art['fanart3'] or ''
						except: pass
					if not values['thumb']: values['thumb'] = values['poster']
					values['fanart'] = values['thumb']
					values['season_poster'] = values['poster']
					if self.enable_fanarttv:
						extended_art = fanarttv_cache.get(FanartTv().get_tvshow_art, 336, tvdb)
						if extended_art: values.update(extended_art)
				values['imdb'] = imdb
				values['tmdb'] = tmdb
				values['tvdb'] = tvdb
				items.append(values)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		return items

	def simkl_progress_list(self, url, direct=False, upcoming=False):
		#https://api.simkl.com/sync/all-items/shows/watching?extended=full
		# Simkl treats anime as a separate content bucket from "shows" — querying only
		# the shows endpoint silently excluded every in-progress anime title.
		try:
			shows_result = simkl.getSimklAsJson('/sync/all-items/shows/watching?extended=full') or []
			anime_result = simkl.getSimklAsJson('/sync/all-items/anime/watching?extended=full') or []
			result = shows_result + anime_result
		except: return
		if not result: return
		items = []
		# progress_showunaired = getSetting('trakt.progress.showunaired') == 'true'
		for item in result:
			try:
				values = {} ; num_1 = 0
				#season_sort = sorted(item['seasons'][:], key=lambda k: k['number'], reverse=False) # simkl sometimes places season0 at end and episodes out of order. So we sort it to be sure.
				season_sort = sorted(item.get('seasons', []), key=lambda k: k.get('number', 0), reverse=False)
				values['snum'] = season_sort[-1]['number']
				episode = [x for x in season_sort[-1]['episodes'] if 'number' in x]
				episode = sorted(episode, key=lambda x: x['number'])
				values['enum'] = episode[-1]['number']
				try: values['lastplayed'] = item.get('last_watched_at')
				except: values['lastplayed'] = ''
				values['tvshowtitle'] = item['show']['title']
				if not values['tvshowtitle']: continue
				ids = item.get('show', {}).get('ids', {})
				values['imdb'] = str(ids.get('imdb', '')) if ids.get('imdb') else ''
				values['tmdb'] = str(ids.get('tmdb', '')) if ids.get('tmdb') else ''
				values['tvdb'] = str(ids.get('tvdb', '')) if ids.get('tvdb') else ''
				values['duration'] = ''
				items.append(values)
				
			except: pass

		def items_list(i):
			values = i
			imdb, tmdb, tvdb = i.get('imdb'), i.get('tmdb'), i.get('tvdb')
			if not tmdb and (imdb or tvdb):
				try:
					result = cache.get(tmdb_indexer().IdLookup, 96, imdb, tvdb)
					values['tmdb'] = str(result.get('id', '')) if result.get('id') else ''
				except:
					if getSetting('debug.level') == '1':
						from resources.lib.modules import log_utils
						return log_utils.log('tvshowtitle: (%s) missing tmdb_id: ids={imdb: %s, tmdb: %s, tvdb: %s}' % (i['tvshowtitle'], imdb, tmdb, tvdb), __name__, log_utils.LOGDEBUG) # log TMDb shows that they do not have
			try:
				showSeasons = cache.get(tmdb_indexer().get_showSeasons_meta, 96, tmdb)
				if not showSeasons: return
				key = i['snum'] - 1 if showSeasons['seasons'][0]['season_number'] != 0 else i['snum']
				try: next_episode_num = i['enum'] + 1 if showSeasons['seasons'][key]['episode_count'] > i['enum'] else 1
				except: return
				next_season_num = i['snum'] if next_episode_num == i['enum'] + 1 else i['snum'] + 1
				if next_season_num > showSeasons['total_seasons']: return
				if not self.showspecials and next_season_num == 0: return
				seasonEpisodes = tmdb_indexer().get_seasonEpisodes_meta_checked(tmdb, next_season_num)
				if not seasonEpisodes: return
				seasonEpisodes = dict((k,v) for k, v in iter(seasonEpisodes.items()) if v is not None and v != '') # remove empty keys so .update() doesn't over-write good meta with empty values.
				try: episode_meta = [x for x in seasonEpisodes.get('episodes') if x.get('episode') == next_episode_num][0] # to pull just the episode meta we need
				except: return
				if not episode_meta['plot']: episode_meta['plot'] = showSeasons['plot'] # some plots missing for eps so use season level plot
				values.update(showSeasons)
				values.update(seasonEpisodes)
				values.update(episode_meta)
				# if not self.trakt_progressFlatten or self.trakt_directProgressScrape:
					# for k in ('seasons', 'episodes', 'snum', 'enum'): values.pop(k, None) # pop() keys from showSeasons and seasonEpisodes that are not needed anymore
				for k in ('episodes', 'snum', 'enum'): values.pop(k, None) # pop() keys from showSeasons and seasonEpisodes that are not needed anymore

				try:
					if values.get('premiered') and i.get('airtime'): combined = '%sT%s' % (values['premiered'], values['airtime'])
					else: raise Exception()
					air_datetime_list = tools.convert_time(stringTime=combined, zoneFrom=i.get('airzone', ''), zoneTo='local', formatInput='%Y-%m-%dT%H:%M', formatOutput='%Y-%m-%dT%H:%M').split('T')
					air_date, air_time = air_datetime_list[0], air_datetime_list[1]
				except: air_date, air_time = values.get('premiered', '') if values.get('premiered') else '', i.get('airtime', '') if i.get('airtime') else ''
				values['unaired'] = ''
				if upcoming:
					values['simklUpcomingProgress'] = True
					try:
						if values['status'].lower() == 'ended': return
						elif not air_date: values['unaired'] = 'true'
						elif int(re.sub(r'[^0-9]', '', air_date)) > int(re.sub(r'[^0-9]', '', str(self.today_date))): values['unaired'] = 'true'
						elif int(re.sub(r'[^0-9]', '', air_date)) == int(re.sub(r'[^0-9]', '', str(self.today_date))):
							if air_time:
								time_now = (self.date_time).strftime('%X')
								if int(re.sub(r'[^0-9]', '', air_time)) > int(re.sub(r'[^0-9]', '', str(time_now))[:4]): values['unaired'] = 'true'
								else: return
							else: pass
						else: return
					except:
						from resources.lib.modules import log_utils
						log_utils.error('tvshowtitle = %s' % i['tvshowtitle'])
				else:
					try:
						if values['status'].lower() == 'ended': pass
						elif not air_date:
							values['unaired'] = 'true'
						elif int(re.sub(r'[^0-9]', '', air_date)) > int(re.sub(r'[^0-9]', '', str(self.today_date))):
							values['unaired'] = 'true'
						elif int(re.sub(r'[^0-9]', '', air_date)) == int(re.sub(r'[^0-9]', '', str(self.today_date))):
							if air_time:
								time_now = (self.date_time).strftime('%X')
								if int(re.sub(r'[^0-9]', '', air_time)) > int(re.sub(r'[^0-9]', '', str(time_now))[:4]):
									values['unaired'] = 'true'
							else: pass
					except:
						from resources.lib.modules import log_utils
						log_utils.error('tvshowtitle = %s' % i['tvshowtitle'])
				if not direct: values['action'] = 'episodes' # for direct progress scraping
				values['simklProgress'] = True # for direct progress scraping and multi episode watch counts indicators
				values['extended'] = True # used to bypass calling "super_info()", super_info() no longer used as of 4-12-21 so this could be removed.
				duration = values['duration']
				if duration:
					values.update({'duration': int(duration)*60})
				if self.enable_fanarttv:
					extended_art = fanarttv_cache.get(FanartTv().get_tvshow_art, 336, tvdb)
					if extended_art: values.update(extended_art)
				self.list.append(values)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		threads = []
		append = threads.append
		for i in items:
			append(Thread(target=items_list, args=(i,)))
		[i.start() for i in threads]
		[i.join() for i in threads]
		return self.list

	def episodeDirectory(self, items, unfinished=False, next=True, playlist=False, folderName=''):
		from sys import argv # some functions like ActivateWindow() throw invalid handle less this is imported here.
		if self.useContainerTitles: control.setContainerName(folderName)
		if not items: # with reuselanguageinvoker on an empty directory must be loaded, do not use sys.exit()
			control.hide() ; control.notification(title=32326, message=33049)
		sysaddon, syshandle = 'plugin://plugin.video.umbrella/', int(argv[1])
		is_widget = 'plugin' not in control.infoLabel('Container.PluginName')
		if not is_widget and not playlist: control.playlist.clear()
		settingFanart = getSetting('fanart') == 'true'
		addonPoster, addonFanart, addonBanner = control.addonPoster(), control.addonFanart(), control.addonBanner()


		try: traktUpcomingProgress = False if 'traktUpcomingProgress' not in items[0] else True
		except: traktUpcomingProgress = False
		try: simklUpcomingProgress = False if 'simklUpcomingProgress' not in items[0] else True
		except: simklUpcomingProgress = False
		try: mdblistUpcomingProgress = False if 'mdblistUpcomingProgress' not in items[0] else True
		except: mdblistUpcomingProgress = False
		try: customUpcomingProgress = False if 'customUpcomingProgress' not in items[0] else True
		except: customUpcomingProgress = False
		try: floppyUpcomingProgress = False if 'floppyUpcomingProgress' not in items[0] else True
		except: floppyUpcomingProgress = False
		try: scrobUpcomingProgress = False if 'scrobUpcomingProgress' not in items[0] else True
		except: scrobUpcomingProgress = False



		try: traktProgress = False if 'traktProgress' not in items[0] else True
		except: traktProgress = False
		try: simklProgress = False if 'simklProgress' not in items[0] else True
		except: simklProgress = False
		try: mdblistProgress = False if 'mdblistProgress' not in items[0] else True
		except: mdblistProgress = False
		if simklProgress and self.simkl_directProgressScrape: progressMenu = getLS(32016)
		if traktProgress and self.trakt_directProgressScrape: progressMenu = getLS(32016)
		elif mdblistProgress and self.mdblist_directProgressScrape: progressMenu = getLS(32016)
		else: progressMenu = getLS(32015)
		if traktProgress: isMultiList = True
		elif simklProgress: isMultiList = True
		elif mdblistProgress: isMultiList = True
		else:
			try: multi = [i['tvshowtitle'] for i in items]
			except: multi = []
			isMultiList = True if len([x for y, x in enumerate(multi) if x not in multi[:y]]) > 1 else False
			try:
				if '/users/me/history/' in items[0]['next']: isMultiList = True
			except: pass
		upcoming_prependDate = getSetting('trakt.UpcomingProgress.prependDate') == 'true'
		upcoming_prependDate2 = getSetting('simkl.UpcomingProgress.prependDate') == 'true'
		upcoming_prependDate3 = getSetting('mdblist.UpcomingProgress.prependDate') == 'true'
		upcoming_prependDate4 = getSetting('custom.UpcomingProgress.prependDate') == 'true'
		upcoming_prependDate5 = getSetting('floppy.UpcomingProgress.prependDate') == 'true'
		try: sysaction = items[0]['action']
		except: sysaction = ''
		multi_unwatchedEnabled = getSetting('multi.unwatched.enabled') == 'true'
		try: airEnabled = getSetting('tvshows.air.enabled') if 'ForceAirEnabled' not in items[0] else 'true'
		except: airEnabled = 'false'
		play_mode = getSetting('play.mode.tv')
		rescrape_useDefault = getSetting('rescrape.default') == 'true'
		rescrape_method = getSetting('rescrape.default2')
		enable_playnext = getSetting('enable.playnext') == 'true'
		indicators = getTVShowIndicators() # gives breakdown of (season, ep) watched
		isFolder = False if sysaction != 'episodes' else True
		if airEnabled == 'true':
			airZone, airLocation = getSetting('tvshows.air.zone'), getSetting('tvshows.air.location')
			airFormat, airFormatDay = getSetting('tvshows.air.format'), getSetting('tvshows.air.day')
			airFormatTime, airBold = getSetting('tvshows.air.time'), getSetting('tvshows.air.bold')
			airLabel = getLS(35032)
		if play_mode == '1' or enable_playnext: playbackMenu = getLS(32063)
		else: playbackMenu = getLS(32064)
		_indicators_alt = getSetting('indicators.alt')
		_trakt_marks = self.traktCredentials and (_indicators_alt == '1' or getSetting('trakt.markwatched') == 'true')
		_simkl_marks = self.simklCredentials and (_indicators_alt == '2' or getSetting('simkl.markwatched') == 'true')
		_mdblist_marks = self.mdblist_authed and (_indicators_alt == '3' or getSetting('mdblist.markwatched') == 'true')
		if _indicators_alt == '0':
			watchedMenu, unwatchedMenu = getLS(32066), getLS(32067)
		elif sum([bool(_trakt_marks), bool(_simkl_marks), bool(_mdblist_marks)]) > 1:
			watchedMenu, unwatchedMenu = getLS(40564), getLS(40565)
		elif _trakt_marks:
			watchedMenu, unwatchedMenu = getLS(32068), getLS(32069)
		elif _simkl_marks:
			watchedMenu, unwatchedMenu = getLS(40554), getLS(40555)
		elif _mdblist_marks:
			watchedMenu, unwatchedMenu = getLS(40631), getLS(40632)
		else:
			watchedMenu, unwatchedMenu = getLS(32066), getLS(32067)
		traktManagerMenu, playlistManagerMenu, queueMenu = '[COLOR %s]Trakt Manager[/COLOR]' % self.highlight_color, getLS(35522), getLS(32065)
		simklManagerMenu = '[COLOR %s]Simkl Manager[/COLOR]' % self.highlight_color
		mdblistManagerMenu = '[COLOR %s]MDBList Manager[/COLOR]' % self.highlight_color
		customManagerMenu = '[COLOR %s]%s Manager[/COLOR]' % (self.highlight_color, customtrakt.getCustomServiceName())
		floppyManagerMenu = '[COLOR %s]Floppy Manager[/COLOR]' % self.highlight_color
		scrobManagerMenu = '[COLOR %s]Scrob Manager[/COLOR]' % self.highlight_color
		tvshowBrowserMenu, addToLibrary, addToFavourites, removeFromFavourites = getLS(32071), getLS(32551), getLS(40463), getLS(40468)
		clearSourcesMenu, rescrapeMenu, progressRefreshMenu = getLS(32611), getLS(32185), getLS(32194)
		trailerMenu = getLS(40431)
		from resources.lib.modules import favourites
		favoriteItems = favourites.getFavourites(content='episode')
		favoriteItems = [(x[0]) for x in favoriteItems]
		if playlist: listitems = [] ; append = listitems.append
		for i in items:
			try:


				if traktUpcomingProgress: pass
				elif simklUpcomingProgress: pass
				elif mdblistUpcomingProgress: pass
				elif customUpcomingProgress: pass
				elif floppyUpcomingProgress: pass
				elif scrobUpcomingProgress: pass
				elif traktProgress:
					if not self.progress_showunaired and i.get('unaired', '') == 'true': continue
				elif simklProgress:
					if not self.progress_showunairedSimkl and i.get('unaired', '') == 'true': continue
				elif mdblistProgress:
					if not self.progress_showunairedMDBList and i.get('unaired', '') == 'true': continue
				else:
					if not self.showunaired and i.get('unaired', '') == 'true': continue
				

				tvshowtitle, title, imdb, tmdb, tvdb = i.get('tvshowtitle'), i.get('title'), i.get('imdb', ''), i.get('tmdb', ''), i.get('tvdb', '')
				year, season, episode, premiered = i.get('year', ''), i.get('season'), i.get('episode'), i.get('premiered', '')
				trailer, runtime = i.get('trailer', ''), i.get('duration')
				episodeType = i.get('episode_type')
				if int(season) == 1 and int(episode) == 1: episodeType = 'series_premiere'
				if int(episode) == 1 and int(season) != 1: episodeType = 'season_premiere'
				
				
				
				if 'label' not in i: i['label'] = title
				if (not i['label'] or i['label'] == '0'): label = '%sx%02d . %s %s' % (season, int(episode), 'Episode', episode)
				else: label = '%sx%02d. %s' % (season, int(episode), i['label'])
				if is_widget:
					labelProgress = label
				else:
					if isMultiList: label = '[COLOR %s]%s[/COLOR] - %s' % (self.highlight_color, tvshowtitle, label)
				try: labelProgress = label + '[COLOR %s]  [%s][/COLOR]' % (self.highlight_color, str(round(float(i['progress']), 1)) + '%')
				except: labelProgress = label
				isUnaired = False
				try:
					if i['unaired'] == 'true': 
						labelProgress = '[COLOR %s][I]%s[/I][/COLOR]' % (self.unairedcolor, labelProgress)
						isUnaired = True
				except: 
					isUnaired = False
				if i.get('traktHistory') is True: # uses Trakt lastplayed in utc
					try:
						air_datetime = tools.convert_time(stringTime=i.get('lastplayed', ''), zoneFrom='utc', zoneTo='local', formatInput='%Y-%m-%dT%H:%M:%S.000Z', formatOutput='%b %d %Y %I:%M %p', remove_zeroes=True)
						labelProgress = labelProgress + '[COLOR %s]  [%s][/COLOR]' % (self.highlight_color, air_datetime)
					except: pass


				if (upcoming_prependDate and traktUpcomingProgress is True) or (upcoming_prependDate2 and simklUpcomingProgress) or (upcoming_prependDate3 and mdblistUpcomingProgress) or (upcoming_prependDate4 and customUpcomingProgress) or (upcoming_prependDate5 and floppyUpcomingProgress): # uses TMDb premiered


					try:
						if premiered and i.get('airtime'): combined='%sT%s' % (premiered, i.get('airtime', ''))
						else: raise Exception()
						air_datetime = tools.convert_time(stringTime=combined, zoneFrom=i.get('airzone', ''), zoneTo='local', formatInput='%Y-%m-%dT%H:%M', formatOutput='%b %d %I:%M %p', remove_zeroes=True)
						labelProgress = labelProgress + '[COLOR %s]  [%s][/COLOR]' % (self.highlight_color, air_datetime)
					except: pass
				if i.get('calendar_unaired') is True: # uses Trakt premiered in utc
					try:
						air_datetime = tools.convert_time(stringTime=premiered, zoneFrom='utc', zoneTo='local', formatInput='%Y-%m-%dT%H:%M:%S.000Z', formatOutput='%b %d %I:%M %p', remove_zeroes=True)
						labelProgress = labelProgress + '[COLOR %s]  [%s][/COLOR]' % (self.highlight_color, air_datetime)
						new_date = tools.convert_time(stringTime=premiered, zoneFrom='utc', zoneTo='local', formatInput='%Y-%m-%dT%H:%M:%S.000Z', formatOutput='%Y-%m-%d')
						i.update({'premiered': new_date}) # adjust for Trakt utc
					except: pass
				if i.get('calendar_recent') is True: # uses Trakt premiered in utc
					try:
						new_date = tools.convert_time(stringTime=premiered, zoneFrom='utc', zoneTo='local', formatInput='%Y-%m-%dT%H:%M:%S.000Z', formatOutput='%Y-%m-%d')
						i.update({'premiered': new_date}) # adjust for Trakt utc
					except: pass
				systitle, systvshowtitle, syspremiered = quote_plus(title), quote_plus(tvshowtitle), quote_plus(premiered)
				meta = dict((k, v) for k, v in iter(i.items()) if v is not None and v != '')
				if isMultiList and multi_unwatchedEnabled: mediatype = 'tvshow'
				else: mediatype = 'episode'
				meta.update({'code': imdb, 'imdbnumber': imdb, 'mediatype': mediatype, 'tag': [imdb, tmdb]}) # "tag" and "tagline" for movies only, but works in my skin mod so leave
				try: meta.update({'genre': cleangenre.lang(meta['genre'], self.lang)})
				except: pass
				try: meta.update({'title': i['label']})
				except: pass
				if airEnabled == 'true':
					air = [] ; airday = None ; airtime = None
					if 'airday' in meta and not meta['airday'] is None and meta['airday'] != '': 
						airday = meta['airday']
					if 'airtime' in meta and not meta['airtime'] is None and meta['airtime'] != '':
						airtime = meta['airtime']
						if 'airzone' in meta and not meta['airzone'] is None and meta['airzone'] != '':
							if airZone == '1': zoneTo = meta['airzone']
							elif airZone == '2': zoneTo = 'utc'
							else: zoneTo = 'local'
							if airFormatTime == '1': formatOutput = '%I:%M'
							elif airFormatTime == '2': formatOutput = '%I:%M %p'
							else: formatOutput = '%H:%M'
							abbreviate = airFormatDay == '1'
							airtime = tools.convert_time(stringTime=airtime, stringDay=airday, zoneFrom=meta['airzone'], zoneTo=zoneTo, abbreviate=abbreviate, formatOutput=formatOutput)
							if airday: airday, airtime = airtime[1], airtime[0]
					if airday: air.append(airday)
					if airtime: air.append(airtime)
					if len(air) > 0:
						if airFormat == '0': air = airtime
						elif airFormat == '1': air = airday
						elif airFormat == '2': air = air = ' '.join(air)
						#if airLocation == '0' or airLocation == '1': air = '[COLOR skyblue][%s][/COLOR]' % air
						if airLocation == '0' or airLocation == '1': air = '[COLOR %s][%s][/COLOR]' % (self.highlight_color, air)
						if airBold == 'true': air = '[B]%s[/B]' % str(air)
						if airLocation == '0': labelProgress = '%s %s' % (air, labelProgress)
						elif airLocation == '1': labelProgress = '%s %s' % (labelProgress, air)
						elif airLocation == '2': meta['plot'] = '%s%s\r\n%s' % (airLabel, air, meta['plot'])
						elif airLocation == '3': meta['plot'] = '%s\r\n%s%s' % (meta['plot'], airLabel, air)
				if self.prefer_tmdbArt: poster = meta.get('poster3') or meta.get('poster') or meta.get('poster2') or addonPoster
				else: poster = meta.get('poster2') or meta.get('poster3') or meta.get('poster') or addonPoster
				season_poster = meta.get('season_poster') or poster
				landscape = meta.get('landscape')
				fanart = ''
				if settingFanart:
					if self.prefer_tmdbArt: fanart = meta.get('fanart3') or meta.get('fanart') or meta.get('fanart2') or addonFanart
					else: fanart = meta.get('fanart2') or meta.get('fanart3') or meta.get('fanart') or addonFanart
				#thumb = meta.get('thumb') or landscape or fanart or season_poster
				if self.prefer_fanArt:
					if fanart: thumb = fanart or meta.get('thumb') or landscape or season_poster
					else:
						thumb = meta.get('thumb') or landscape or fanart or season_poster
				else:
					thumb = meta.get('thumb') or landscape or fanart or season_poster
				if isUnaired:
					if self.prefer_fanArt: thumb = fanart or landscape or season_poster
					else: thumb = landscape or fanart or season_poster
				icon = season_poster or poster
				banner = meta.get('banner') or addonBanner
				clearart = meta.get('clearart', '')
				clearlogo = meta.get('clearlogo', '')
				ep_custom = None
				show_custom = None
				try:
					ep_custom = customArtwork.fetch_episode(imdb, tmdb, tvdb, season, episode)
				except Exception:
					pass
				try:
					show_custom = customArtwork.fetch_show(imdb, tvdb)
				except Exception:
					pass
				if ep_custom or show_custom:
					allowed_keys = {"thumb", "poster", "fanart", "landscape", "banner", "clearart", "clearlogo"}
					for key in allowed_keys:
						value = ep_custom[0].get(key) if ep_custom else None
						if value in (None, "", " ") and show_custom:
							value = show_custom[0].get(key)
						if value not in (None, "", " "):
							if key == 'thumb': thumb = value
							if key == 'poster': season_poster = value
							if key == 'fanart': fanart = value
							if key == 'landscape': landscape = value
							if key == 'banner': banner = value
							if key == 'clearart': clearart = value
							if key == 'clearlogo': clearlogo = value
				art = {}
				art.update({'poster': season_poster, 'tvshow.poster': poster, 'season.poster': season_poster, 'fanart': fanart, 'icon': icon, 'thumb': thumb, 'banner': banner,
						'tvshow.clearlogo': clearlogo, 'clearart': clearart, 'tvshow.clearart': clearart, 'landscape': thumb})
				for k in ('metacache', 'poster2', 'poster3', 'fanart2', 'fanart3', 'banner2', 'banner3', 'trailer'): meta.pop(k, None)
				meta.update({'poster': poster, 'fanart': fanart, 'banner': banner, 'thumb': thumb, 'icon': icon})
				sysmeta, sysart, syslabelProgress = quote_plus(jsdumps(meta)), quote_plus(jsdumps(art)), quote_plus(labelProgress)
				url = '%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s' % (
										sysaddon, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, syspremiered, sysmeta)
				sysurl = quote_plus(url)
####-Context Menu and Overlays-####
				cm = []
				try:
					watched = getEpisodeOverlay(indicators, imdb, tvdb, season, episode) == '5'
					if self.traktCredentials:
						cm.append((traktManagerMenu, 'RunPlugin(%s?action=tools_traktManager&name=%s&imdb=%s&tvdb=%s&season=%s&episode=%s&watched=%s&unfinished=%s)' % (sysaddon, systvshowtitle, imdb, tvdb, season, episode, watched, unfinished)))
					if self.simklCredentials:
						cm.append((simklManagerMenu, 'RunPlugin(%s?action=tools_simklManager&name=%s&imdb=%s&tvdb=%s&season=%s&episode=%s&watched=%s)' % (sysaddon, systvshowtitle, imdb, tvdb, season, episode, watched)))
					if self.mdblist_authed:
						cm.append((mdblistManagerMenu, 'RunPlugin(%s?action=tools_mdbWatchlist&name=%s&imdb=%s&tvdb=%s&tmdb=%s&season=%s&episode=%s&watched=%s)' % (sysaddon, systvshowtitle, imdb, tvdb, tmdb, season, episode, watched)))
					if self.customCredentials:
						cm.append((customManagerMenu, 'RunPlugin(%s?action=tools_customManager&name=%s&imdb=%s&tvdb=%s&tmdb=%s&season=%s&episode=%s&watched=%s&unfinished=%s)' % (sysaddon, systvshowtitle, imdb, tvdb, tmdb, season, episode, watched, unfinished)))
					if self.floppyCredentials:
						cm.append((floppyManagerMenu, 'RunPlugin(%s?action=tools_floppyManager&name=%s&imdb=%s&tvdb=%s&tmdb=%s&season=%s&episode=%s&watched=%s&unfinished=%s)' % (sysaddon, systvshowtitle, imdb, tvdb, tmdb, season, episode, watched, unfinished)))
					if self.scrobCredentials:
						cm.append((scrobManagerMenu, 'RunPlugin(%s?action=tools_scrobManager&name=%s&imdb=%s&tvdb=%s&tmdb=%s&season=%s&episode=%s&watched=%s&unfinished=%s)' % (sysaddon, systvshowtitle, imdb, tvdb, tmdb, season, episode, watched, unfinished)))
					if watched:
						meta.update({'playcount': 1, 'overlay': 5})
						cm.append((unwatchedMenu, 'RunPlugin(%s?action=playcount_Episode&name=%s&imdb=%s&tvdb=%s&season=%s&episode=%s&query=4)' % (sysaddon, systvshowtitle, imdb, tvdb, season, episode)))
					else:
						meta.update({'playcount': 0, 'overlay': 4})
						cm.append((watchedMenu, 'RunPlugin(%s?action=playcount_Episode&name=%s&imdb=%s&tvdb=%s&season=%s&episode=%s&query=5)' % (sysaddon, systvshowtitle, imdb, tvdb, season, episode)))
				except: pass
				Folderurl = '%s?action=episodes&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&meta=%s&season=%s&episode=%s&art=%s' % (sysaddon, systvshowtitle, year, imdb, tmdb, tvdb, sysmeta, season, episode, sysart)
				if traktProgress and is_widget == False:
					cm.append((progressRefreshMenu, 'RunPlugin(%s?action=episodes_clrProgressCache&url=progress)' % sysaddon))
				if simklProgress and is_widget == False:
					cm.append((progressRefreshMenu, 'RunPlugin(%s?action=episodes_clrProgressCache&url=progress)' % sysaddon))	
				if mdblistProgress and is_widget == False:
					cm.append((progressRefreshMenu, 'RunPlugin(%s?action=episodes_clrProgressCache&url=mdbprogress)' % sysaddon))
				if isFolder:
					if (traktProgress or simklProgress or mdblistProgress) and is_widget == False:
						cm.append((progressMenu, 'PlayMedia(%s)' % url))
					url = '%s?action=episodes&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&meta=%s&season=%s&episode=%s&art=%s' % (sysaddon, systvshowtitle, year, imdb, tmdb, tvdb, sysmeta, season, episode, sysart)
				cm.append((playlistManagerMenu, 'RunPlugin(%s?action=playlist_Manager&name=%s&url=%s&meta=%s&art=%s)' % (sysaddon, syslabelProgress, sysurl, sysmeta, sysart)))
				cm.append((queueMenu, 'RunPlugin(%s?action=playlist_QueueItem&name=%s)' % (sysaddon, syslabelProgress)))
				cm.append((addToLibrary, 'RunPlugin(%s?action=library_tvshowToLibrary&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s)' % (sysaddon, systvshowtitle, year, imdb, tmdb, tvdb)))
				if favoriteItems:
					if (imdb+str(season)+str(episode)) in favoriteItems:
						cm.append((removeFromFavourites, 'RunPlugin(%s?action=remove_favorite&meta=%s&content=%s)' % (sysaddon, sysmeta, 'episode')))
					else:
						cm.append((addToFavourites, 'RunPlugin(%s?action=add_favorite_episode&meta=%s&content=%s)' % (sysaddon, sysmeta, 'episode')))
				else:
					cm.append((addToFavourites, 'RunPlugin(%s?action=add_favorite_episode&meta=%s&content=%s)' % (sysaddon, sysmeta, 'episode')))
				if isMultiList and is_widget == False:
					cm.append((tvshowBrowserMenu, 'Container.Update(%s?action=seasons&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&art=%s,return)' % (sysaddon, systvshowtitle, year, imdb, tmdb, tvdb, sysart)))
					# cm.append((tvshowBrowserMenu, 'Container.Update(%s?action=episodes&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&meta=%s,return)' % (sysaddon, systvshowtitle, year, imdb, tmdb, tvdb, sysmeta)))

				if not isFolder:
					if (traktProgress or simklProgress or mdblistProgress) and is_widget == False: cm.append((progressMenu, 'Container.Update(%s)' % Folderurl))
					#cm.append((playbackMenu, 'RunPlugin(%s?action=alterSources&url=%s&meta=%s)' % (sysaddon, sysurl, sysmeta)))
					if not rescrape_useDefault:
						cm.append(('Rescrape Options ------>', 'PlayMedia(%s?action=rescrapeMenu&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s)' % (
											sysaddon, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, syspremiered, sysmeta)))
					else:
						if rescrape_method == '0':
							cm.append((rescrapeMenu, 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&rescrape=true&select=1)' % (
											sysaddon, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, syspremiered, sysmeta)))
						if rescrape_method == '1':
							cm.append((rescrapeMenu, 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&rescrape=true&select=0)' % (
											sysaddon, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, syspremiered, sysmeta)))
						if rescrape_method == '2':
							cm.append((rescrapeMenu, 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&rescrape=true&all_providers=true&select=1)' % (
											sysaddon, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, syspremiered, sysmeta)))
						if rescrape_method == '3':
							cm.append((rescrapeMenu, 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&rescrape=true&all_providers=true&select=0)' % (
											sysaddon, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, syspremiered, sysmeta)))
				cm.append(('Customize Artwork', 'RunPlugin(%s?action=customizeArt&mediatype=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&thumb=%s&poster=%s&fanart=%s&landscape=%s&banner=%s&clearart=%s&clearlogo=%s)' % (sysaddon, 'episode', imdb, tmdb, tvdb, season, episode, thumb, season_poster, fanart, landscape, banner, clearart, clearlogo)))
				cm.append((clearSourcesMenu, 'RunPlugin(%s?action=cache_clearSources)' % sysaddon))
				cm.append(('[COLOR %s]Umbrella Settings[/COLOR]' % self.highlight_color, 'RunPlugin(%s?action=tools_openSettings)' % sysaddon))
####################################
				if trailer: meta.update({'trailer': trailer}) # removed temp so it's not passed to CM items, only infoLabels for skin
				else: meta.update({'trailer': '%s?action=play_Trailer&type=%s&name=%s&year=%s&imdb=%s' % (sysaddon, 'show', syslabelProgress, year, imdb)})
				item = control.item(label=labelProgress, offscreen=True)
				#if 'castandart' in i: item.setCast(i['castandart'])
				if 'castandart' in i: meta.update({"cast": ['castandart']}) #changed for kodi20 setinfo method
				item.setArt(art)
				if isMultiList and multi_unwatchedEnabled:
					if 'ForceAirEnabled' not in i:
						try:
							try: count = getShowCount(getSeasonIndicators(imdb, tvdb, has_next_episode=i.get('has_next_episode', False), tmdb_total_aired=meta.get('total_aired_episodes'))[1], imdb, tvdb) # if indicators and no matching imdb_id in watched items then it returns None and we use TMDb meta to avoid Trakt request
							except: count = None
							if count:
								total_aired = int(meta.get('total_aired_episodes') or 0)
								if total_aired > count['total']:
									count['total'] = total_aired
									count['unwatched'] = max(0, total_aired - count['watched'])
								# Fallback: Trakt live API confirmed a new episode (has_next_episode) but both
								# local syncSeasons cache and TMDb meta are stale (user fully caught up, no new
								# watched activity to trigger a cache refresh)
								if i.get('has_next_episode') and int(count.get('unwatched', 0)) == 0:
									count['total'] += 1
									count['unwatched'] = 1
								if int(count['watched']) > 0:
									item.setProperties({'WatchedEpisodes': str(count['watched']), 'UnWatchedEpisodes': str(count['unwatched'])})
								else:
									item.setProperties({'WatchedEpisodes': '0', 'UnWatchedEpisodes': str(count['unwatched'])})
								item.setProperties({'TotalSeasons': str(meta.get('total_seasons', '')), 'TotalEpisodes': str(count['total'])})
								item.setProperty('WatchedProgress', str(int(float(count['watched']) / float(count['total']) * 100)))
							else:
								item.setProperties({'WatchedEpisodes': '0', 'UnWatchedEpisodes': str(meta.get('total_aired_episodes', ''))}) # for shows never watched
								item.setProperties({'TotalSeasons': str(meta.get('total_seasons', '')), 'TotalEpisodes': str(meta.get('total_aired_episodes', ''))})
						except:
							from resources.lib.modules import log_utils
							log_utils.error()
				item.setProperty('IsPlayable', 'true')
				item.setProperty('tvshow.tmdb_id', tmdb)
				item.setProperty('episode_type', episodeType)
				if unfinished: item.setProperty('unfinished', 'true') 
				if is_widget: 
					item.setProperty('isUmbrella_widget', 'true')
					if self.hide_watched_in_widget:
						if str(meta.get('playcount', 0)) == '1':
							continue
				blabel = tvshowtitle + ' S%02dE%02d' % (int(season), int(episode))
				if not i.get('unaired') == 'true':
					if not runtime: runtime = 2700
					resumetime = Bookmarks().get(name=blabel, imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, year=str(year), runtime=runtime, ck=True)
					# item.setProperty('TotalTime', str(runtime)) # Adding this property causes the Kodi bookmark CM items to be added
					#item.setProperty('ResumeTime', str(resumetime))
					try: item.setProperty('WatchedProgress', str(int(float(resumetime) / float(runtime) * 100))) # resumetime and runtime are both in minutes
					except: pass
				else:
					resumetime = ''  # reset so unaired episodes don't inherit resume point from previous iteration

				try: # Year is the shows year, not the seasons year. Extract year from premier date for infoLabels to have "season_year."
					season_year = re.findall(r'(\d{4})', i.get('premiered', ''))[0]
					meta.update({'year': season_year})
				except: pass
				setUniqueIDs={'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb}

				if (upcoming_prependDate and traktUpcomingProgress is True) or (upcoming_prependDate2 and simklUpcomingProgress) or (upcoming_prependDate3 and mdblistUpcomingProgress) or (upcoming_prependDate4 and customUpcomingProgress) or (upcoming_prependDate5 and floppyUpcomingProgress):
					try:
						if premiered and meta.get('airtime'): combined='%sT%s' % (premiered, meta.get('airtime', ''))
						else: raise Exception()
						air_datetime = tools.convert_time(stringTime=combined, zoneFrom=meta.get('airzone', ''), zoneTo='local', formatInput='%Y-%m-%dT%H:%M', formatOutput='%b %d %I:%M %p', remove_zeroes=True)
						new_title = '[COLOR %s][%s]  [/COLOR]' % (self.highlight_color, air_datetime) + title
						meta.update({'title': new_title})
					except: pass
				#item.setInfo(type='video', infoLabels=control.metadataClean(meta))
				try:
					resumetime = resumetime
				except:
					resumetime = ''
				
				control.set_info(item, meta, setUniqueIDs=setUniqueIDs, resumetime=resumetime)
				if is_widget and KODI_VERSION > 19.5 and not self.useFullContext:
					pass
				else:
					item.addContextMenuItems(cm)
				if playlist: append((url, item, isFolder))
				else: control.addItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		if next:
			try:
				if not items: raise Exception()
				url = items[0]['next']
				if not url: raise Exception()
				nextMenu = getLS(32053)
				url_params = dict(parse_qsl(url))
				if 'imdb.com' in url:
					start = int(url_params.get('start'))
					page = '  [I](%s)[/I]' % str(((start - 1) / int(self.count)) + 1)
				else:
					page = url_params.get('page')
					page = '  [I](%s)[/I]' % page
				nextColor = '[COLOR %s]' % getSetting('highlight.color')
				nextMenu = nextColor + nextMenu + page + '[/COLOR]'
				if '/users/me/history/' in url: url = '%s?action=calendar&url=%s&folderName=%s' % (sysaddon, quote_plus(url), quote_plus(folderName))
				item = control.item(label=nextMenu, offscreen=True)
				icon = control.addonNext()
				item.setArt({'icon': icon, 'thumb': icon, 'poster': icon, 'banner': icon})
				item.setProperty ('SpecialSort', 'bottom')
				if playlist: append((url, item, True))
				else: control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except: pass
		if playlist: return listitems
		if isMultiList and multi_unwatchedEnabled: # Show multi episodes as show, in order to display unwatched count if enabled.
			control.content(syshandle, 'tvshows')
			control.directory(syshandle, cacheToDisc=False) # disable cacheToDisc so unwatched counts loads fresh data counts if changes made
			views.setView('tvshows', {'skin.estuary': 55, 'skin.confluence': 500})
		else:
			control.content(syshandle, 'episodes')
			control.directory(syshandle, cacheToDisc=False) # disable cacheToDisc so unwatched counts loads fresh data counts if changes made
			views.setView('episodes', {'skin.estuary': 55, 'skin.confluence': 504})

	def addDirectory(self, items, queue=False, folderName=''):
		from sys import argv # some functions like ActivateWindow() throw invalid handle less this is imported here.
		if not items: # with reuselanguageinvoker on an empty directory must be loaded, do not use sys.exit()
			control.hide() ; control.notification(title=32326, message=33049)
		if self.useContainerTitles: control.setContainerName(folderName)
		syshandle = int(argv[1])
		addonThumb = control.addonThumb()
		artPath = control.artPath()
		queueMenu = getLS(32065)
		for i in items:
			try:
				name = i['name']
				if i['image'].startswith('http'): poster = i['image']
				elif artPath: poster = control.joinPath(artPath, i['image'])
				else: poster = addonThumb
				icon = i.get('icon', '') or 'DefaultFolder.png'
				if not icon.startswith('Default'): icon = control.joinPath(self.artPath, icon)
				url = 'plugin://plugin.video.umbrella/?action=%s' % i['action']
				try: url += '&url=%s' % quote_plus(i['url'])
				except: pass
				cm = []
				if queue: cm.append((queueMenu, 'RunPlugin(plugin://plugin.video.umbrella/?action=playlist_QueueItem)'))
				cm.append(('[COLOR %s]Umbrella Settings[/COLOR]' % self.highlight_color, 'RunPlugin(plugin://plugin.video.umbrella/?action=tools_openSettings)'))
				item = control.item(label=name, offscreen=True)
				item.setArt({'icon': icon, 'poster': poster, 'thumb': poster, 'fanart': control.addonFanart(), 'banner': poster})
				#item.setInfo(type='video', infoLabels={'plot': name})
				meta = dict({'plot': name})
				control.set_info(item, meta)
				is_widget = 'plugin' not in control.infoLabel('Container.PluginName')
				if is_widget and KODI_VERSION > 19.5 and self.useFullContext != True:
					pass
				else:
					item.addContextMenuItems(cm)
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		content = 'addons' if control.skin == 'skin.auramod' else ''
		control.content(syshandle, content) # some skins use their own thumb for things like "genres" when content type is set here
		control.directory(syshandle, cacheToDisc=True)