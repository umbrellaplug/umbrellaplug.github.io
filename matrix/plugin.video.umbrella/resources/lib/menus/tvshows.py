# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from datetime import datetime, timedelta
import time
from json import dumps as jsdumps
import re
import xbmc
from threading import Thread
from urllib.parse import quote_plus, urlencode, parse_qsl, urlparse, urlsplit
from resources.lib.database import cache, metacache, fanarttv_cache, traktsync
from resources.lib.indexers.tmdb import TVshows as tmdb_indexer
from resources.lib.modules.simkl import SIMKL as simkl
from resources.lib.indexers.fanarttv import FanartTv
from resources.lib.modules import cleangenre, log_utils
from resources.lib.modules import client
from resources.lib.modules import control
from resources.lib.modules.playcount import getTVShowOverlay, getShowCount, getSeasonIndicators
from resources.lib.modules import trakt
from resources.lib.modules import views
from resources.lib.modules import mdblist
from resources.lib.modules import tools

getLS = control.lang
getSetting = control.setting
LOGINFO = log_utils.LOGINFO
homeWindow = control.homeWindow

class TVshows:
	def __init__(self, notifications=True):
		self.list = []
		self.page_limit = getSetting('page.item.limit')
		self.genre_limit = getSetting('limit.imdb.genres')
		self.search_page_limit = getSetting('search.page.limit')
		self.lang = control.apiLanguage()['tmdb']
		self.notifications = notifications
		self.enable_fanarttv = getSetting('enable.fanarttv') == 'true'
		self.prefer_tmdbArt = getSetting('prefer.tmdbArt') == 'true'
		self.unairedcolor = getSetting('unaired.identify')
		self.showunaired = getSetting('showunaired') == 'true'
		self.highlight_color = control.setting('highlight.color')
		self.date_time = datetime.now()
		self.today_date = (self.date_time).strftime('%Y-%m-%d')
		self.imdb_user = getSetting('imdbuser').replace('ur', '')
		self.tvdb_key = getSetting('tvdb.apikey')
		self.user = str(self.imdb_user) + str(self.tvdb_key)
		self.useContainerTitles = getSetting('enable.containerTitles') == 'true'
		self.trakt_directProgressScrape = getSetting('trakt.directProgress.scrape') == 'true'
		self.trakt_progress_hours = int(getSetting('cache.traktprogress'))
		self.watched_progress = getSetting('tvshows.progress.watched') == 'true'
		if datetime.today().month > 6:
			traktyears='years='+str(datetime.today().year)
		else:
			traktyears='years='+str(int(datetime.today().year-1))+'-'+str(datetime.today().year)
		self.imdb_link = 'https://www.imdb.com'
		self.persons_link = 'https://www.imdb.com/search/name/?count=100&name='
		self.personlist_link = 'https://www.imdb.com/search/name/?count=100&gender=male,female'
		self.popular_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&num_votes=100,&release_date=,date[0]&sort=moviemeter,asc&count=%s&start=1' % self.genre_limit
		self.airing_link = 'https://www.imdb.com/search/title/?title_type=tv_episode&release_date=date[1],date[0]&sort=moviemeter,asc&count=%s&start=1' % self.genre_limit
		self.active_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&num_votes=10,&production_status=active&sort=moviemeter,asc&count=%s&start=1' % self.genre_limit
		self.premiere_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&languages=en&num_votes=10,&release_date=date[60],date[0]&sort=release_date,desc&count=%s&start=1' % self.genre_limit
		self.rating_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&num_votes=5000,&release_date=,date[0]&sort=user_rating,desc&count=%s&start=1' % self.genre_limit
		self.views_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&num_votes=100,&release_date=,date[0]&sort=num_votes,desc&count=%s&start=1' % self.genre_limit
		self.person_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&release_date=,date[0]&role=%s&sort=year,desc&count=%s&start=1' % ('%s', self.genre_limit)
		self.genre_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&num_votes=3000,&release_date=,date[0]&genres=%s&sort=%s&count=%s&start=1' % ('%s', self.imdb_sort(type='imdbshows'), self.genre_limit)
		self.keyword_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&release_date=,date[0]&keywords=%s&sort=%s&count=%s&start=1' % ('%s', self.imdb_sort(type='imdbshows'),self.genre_limit)
		self.language_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&num_votes=100,&production_status=released&primary_language=%s&sort=%s&count=%s&start=1' % ('%s', self.imdb_sort(type='imdbshows'), self.genre_limit)
		self.certification_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&release_date=,date[0]&certificates=%s&sort=%s&count=%s&start=1' % ('%s', self.imdb_sort(type='imdbshows'), self.genre_limit)
		self.year_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&num_votes=100,&production_status=released&year=%s,%s&sort=moviemeter,asc&count=%s&start=1' % ('%s', '%s', self.genre_limit)
		self.imdbwatchlist_link = 'https://www.imdb.com/user/ur%s/watchlist?sort=date_added,desc' % self.imdb_user # only used to get users watchlist ID
		self.imdbwatchlist2_link = 'https://www.imdb.com/list/%s/?view=detail&sort=%s&title_type=tvSeries&start=1' % ('%s', self.imdb_sort(type='shows.watchlist'))
		self.imdblists_link = 'https://www.imdb.com/user/ur%s/lists?tab=all&sort=mdfd&order=desc&filter=titles' % self.imdb_user
		self.imdblist_link = 'https://www.imdb.com/list/%s/?view=detail&sort=%s&title_type=tvSeries,tvMiniSeries&start=1' % ('%s', self.imdb_sort())
		self.imdbratings_link = 'https://www.imdb.com/user/ur%s/ratings?sort=your_rating,desc&mode=detail&start=1' % self.imdb_user # IMDb ratings does not take title_type so filter in imdb_list() function
		self.anime_link = 'https://www.imdb.com/search/keyword/?keywords=anime&title_type=tvSeries,miniSeries&release_date=,date[0]&sort=moviemeter,asc&count=%s&start=1' % self.genre_limit

		self.trakt_user = getSetting('trakt.user.name').strip()
		self.traktCredentials = trakt.getTraktCredentialsInfo()
		self.trakt_link = 'https://api.trakt.tv'
		self.search_link = 'https://api.trakt.tv/search/show?limit=%s&page=1&query=' % self.search_page_limit
		self.traktlists_link = 'https://api.trakt.tv/users/me/lists'
		self.traktlikedlists_link = 'https://api.trakt.tv/users/likes/lists?limit=1000000' # used by library import only
		self.traktwatchlist_link = 'https://api.trakt.tv/users/me/watchlist/shows?limit=%s&page=1' % self.page_limit # this is now a dummy link for pagination to work
		self.traktcollection_link = 'https://api.trakt.tv/users/me/collection/shows?limit=%s&page=1' % self.page_limit # this is now a dummy link for pagination to work
		self.traktlist_link = 'https://api.trakt.tv/users/%s/lists/%s/items/shows?limit=%s&page=1' % ('%s', '%s', self.page_limit) # local pagination, limit and page used to advance, pulled from request
		self.progress_link = 'https://api.trakt.tv/sync/watched/shows?extended=noseasons'
		self.progresstv_link = 'https://api.trakt.tv/users/me/watched/shows'
		self.trakt_genres = 'https://api.trakt.tv/genres/shows/'
		self.traktanticipated_link = 'https://api.trakt.tv/shows/anticipated?limit=%s&page=1' % self.page_limit 
		self.trakttrending_link = 'https://api.trakt.tv/shows/trending?limit=%s&page=1' % self.page_limit
		self.traktmostplayed_link = 'https://api.trakt.tv/shows/played/weekly?limit=%s&page=1' % self.page_limit
		self.traktmostwatched_link = 'https://api.trakt.tv/shows/watched/weekly?limit=%s&page=1' % self.page_limit
		self.trakttrending_link = 'https://api.trakt.tv/shows/trending?page=1&limit=%s' % self.page_limit
		self.showspecials = getSetting('tv.specials') == 'true'
		
		self.trakttrending_recent_link = 'https://api.trakt.tv/shows/trending?page=1&limit=%s&%s' % (self.page_limit, traktyears)
		self.traktpopular_link = 'https://api.trakt.tv/shows/popular?page=1&limit=%s' % self.page_limit
		self.traktrecommendations_link = 'https://api.trakt.tv/recommendations/shows?limit=40'
		self.trakt_popularLists_link = 'https://api.trakt.tv/lists/popular?limit=40&page=1' # use limit=40 due to filtering out Movie only lists
		self.trakt_trendingLists_link = 'https://api.trakt.tv/lists/trending?limit=40&page=1'
		self.tmdb_similar = 'https://api.themoviedb.org/3/tv/%s/similar?api_key=%s&language=en-US&region=US&page=1'
		self.tmdb_recentday = 'https://api.themoviedb.org/3/trending/tv/day?api_key=%s&language=en-US&region=US&page=1'
		self.tmdb_recentweek = 'https://api.themoviedb.org/3/trending/tv/week?api_key=%s&language=en-US&region=US&page=1'
		self.search_tmdb_link = 'https://api.themoviedb.org/3/search/tv?api_key=%s&language=en-US&query=%s&region=US&page=1'% ('%s','%s')

		self.tvmaze_link = 'https://www.tvmaze.com'
		self.tmdb_key = getSetting('tmdb.apikey')
		if self.tmdb_key == '' or self.tmdb_key is None:
			self.tmdb_key = 'edde6b5e41246ab79a2697cd125e1781'
		self.tmdb_session_id = getSetting('tmdb.sessionid')
		self.tmdb_link = 'https://api.themoviedb.org'
		self.tmdb_userlists_link = 'https://api.themoviedb.org/3/account/{account_id}/lists?api_key=%s&language=en-US&session_id=%s&page=1' % ('%s', self.tmdb_session_id) # used by library import only
		self.tmdb_popular_link = 'https://api.themoviedb.org/3/tv/popular?api_key=%s&language=en-US&region=US&page=1'
		self.tmdb_toprated_link = 'https://api.themoviedb.org/3/tv/top_rated?api_key=%s&language=en-US&region=US&page=1'
		self.tmdb_ontheair_link = 'https://api.themoviedb.org/3/tv/on_the_air?api_key=%s&language=en-US&region=US&page=1'
		self.tmdb_airingtoday_link = 'https://api.themoviedb.org/3/tv/airing_today?api_key=%s&language=en-US&region=US&page=1'
		self.tmdb_networks_link = 'https://api.themoviedb.org/3/discover/tv?api_key=%s&with_networks=%s&sort_by=%s&page=1' % ('%s', '%s', self.tmdb_DiscoverSort())
		self.tmdb_genre_link = 'https://api.themoviedb.org/3/discover/tv?api_key=%s&with_genres=%s&include_null_first_air_dates=false&sort_by=%s&page=1' % ('%s', '%s', self.tmdb_DiscoverSort())
		self.tmdb_year_link = 'https://api.themoviedb.org/3/discover/tv?api_key=%s&language=en-US&include_null_first_air_dates=false&first_air_date_year=%s&sort_by=%s&page=1' % ('%s', '%s', self.tmdb_DiscoverSort())
		self.tmdb_recommendations = 'https://api.themoviedb.org/3/tv/%s/recommendations?api_key=%s&language=en-US&region=US&page=1'
		self.mbdlist_list_items = 'https://mdblist.com/api/lists/%s/items?apikey=%s&limit=%s&page=1' % ('%s', mdblist.mdblist_api, self.page_limit)
		self.simkltrendingtoday_link = 'https://api.simkl.com/tv/trending/today?client_id=%s&extended=tmdb' % '%s'
		self.simkltrendingweek_link = 'https://api.simkl.com/tv/trending/week?client_id=%s&extended=tmdb' % '%s'
		self.simkltrendingmonth_link = 'https://api.simkl.com/tv/trending/month?client_id=%s&extended=tmdb'% '%s'
		self.imdblist_hours = int(getSetting('cache.imdblist'))
		self.trakt_hours = int(getSetting('cache.traktother'))
		self.traktpopular_hours = int(getSetting('cache.traktpopular'))
		self.trakttrending_hours = int(getSetting('cache.trakttrending'))
		self.traktuserlist_hours = int(getSetting('cache.traktuserlist'))
		self.tmdbrecentday_hours = int(getSetting('cache.tmdbrecentday'))
		self.tmdbrecentweek_hours = int(getSetting('cache.tmdbrecentweek'))
		self.simkl_hours = int(getSetting('cache.simkl'))
		self.mdblist_hours = int(getSetting('cache.mdblist'))
		# Ticket is in to add this feature but currently not available
		# self.tmdb_certification_link = 'https://api.themoviedb.org/3/discover/tv?api_key=%s&language=en-US&certification_country=US&certification=%s&sort_by=%s&page=1' % ('%s', '%s', self.tmdb_DiscoverSort())
		self.hide_watched_in_widget = getSetting('enable.umbrellahidewatched') == 'true'
		self.useFullContext = getSetting('enable.umbrellawidgetcontext') == 'true'
		self.showCounts = getSetting('tvshows.episodecount') == 'true'
		self.useContainerTitles = getSetting('enable.containerTitles') == 'true'
		self.is_widget = 'plugin' not in control.infoLabel('Container.PluginName')

	def get(self, url, idx=True, create_directory=True, folderName=''):
		self.list = []
		try:
			try: url = getattr(self, url + '_link')
			except: pass
			try: u = urlparse(url).netloc.lower()
			except: pass
			if url == 'favourites_tvshows':
				return self.favouriteTVShows(folderName=folderName)
			if url == 'traktbasedonrecent':
				return self.trakt_based_on_recent(folderName=folderName)
			elif url == 'traktbasedonsimilar':
				return self.trakt_based_on_similar(folderName=folderName)
			elif url == 'tmdbrecentday':
				return self.tmdb_trending_recentday(folderName=folderName)
			elif url == 'tmdbrecentweek':
				return self.tmdb_trending_recentweek(folderName=folderName)
			elif u in self.search_tmdb_link and url != 'tmdbrecentday' and url != 'tmdbrecentweek' and url != 'favourites_tvshows':
				return self.getTMDb(url, folderName=folderName)
			elif u in (self.simkltrendingweek_link or u in self.simkltrendingmonth_link or u in self.simkltrendingtoday_link) and url != 'favourites_tvshows':
				return self.getSimkl(url, folderName=folderName)
			if u in self.trakt_link and '/users/' in url:
				try:
					if '/users/me/' not in url: raise Exception()
					if '/collection/' in url: return self.traktCollection(url, folderName=folderName)
					if '/watchlist/' in url: return self.traktWatchlist(url, folderName=folderName)
					if trakt.getActivity() > cache.timeout(self.trakt_list, url, self.trakt_user, folderName):
						self.list = cache.get(self.trakt_list, 0, url, self.trakt_user, folderName)
					else: self.list = cache.get(self.trakt_list, 720, url, self.trakt_user, folderName)
				except: self.list = self.trakt_userList(url, create_directory=False)
				if idx: self.worker()
				self.sort()
			elif u in self.trakt_link and self.search_link in url:
				self.list = cache.get(self.trakt_list, 0, url, self.trakt_user, folderName)
				if idx: self.worker()
			elif u in self.trakt_link and 'trending' in url:
				from resources.lib.modules import log_utils
				self.list = cache.get(self.trakt_list, self.trakttrending_hours, url, self.trakt_user, folderName) #trakt trending
				if idx: self.worker()
			elif u in self.trakt_link:
				from resources.lib.modules import log_utils
				self.list = cache.get(self.trakt_list, self.trakt_hours, url, self.trakt_user, folderName) #trakt other
				if idx: self.worker()
			elif u in self.imdb_link and ('/user/' in url or '/list/' in url):
				isRatinglink=True if self.imdbratings_link in url else False
				self.list = cache.get(self.imdb_list, 0, url, isRatinglink, folderName)
				if idx: self.worker()
				# self.sort() # switched to request sorting for imdb
			elif u in self.imdb_link:
				self.list = cache.get(self.imdb_genre_list, self.imdblist_hours, url, folderName)
				if idx: self.worker()
			elif u in self.mbdlist_list_items:
				self.list = self.mdb_list_items(url, create_directory=False, folderName=folderName)
				if idx: self.worker()
			if self.list is None: self.list = []
			if len(self.list) > 0:
				if create_directory: self.tvshowDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications and self.is_widget != True: control.notification(title=32002, message=33049)
	def getMBDTopLists(self, create_directory=True, folderName=''):
		self.list = []
		try:
			self.list = cache.get(self.mbd_top_lists, 6)
			#self.list = self.mbd_top_lists()
			if self.list is None: self.list = []
			if create_directory: self.addDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
	def getTMDb(self, url, create_directory=True, folderName=''):
		self.list = []
		try:
			try: url = getattr(self, url + '_link')
			except: pass
			try: u = urlparse(url).netloc.lower()
			except: pass
			if u in self.tmdb_link and '/list/' in url:
				self.list = cache.get(tmdb_indexer().tmdb_collections_list, 0, url)
			elif u in self.tmdb_link and not '/list/' in url:
				self.list = tmdb_indexer().tmdb_list(url) # caching handled in list indexer
			if self.list is None: self.list = []
			if create_directory: self.tvshowDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications and self.is_widget != True: control.notification(title=32002, message=33049)
    
	def getSimkl(self, url, create_directory=True, folderName=''):
		self.list = []
		try:
			try: url = getattr(self, url + '_link')
			except: pass
			try: u = urlparse(url).netloc.lower()
			except: pass
			if u in self.simkltrendingweek_link or u in self.simkltrendingmonth_link or u in self.simkltrendingtoday_link:
				self.list = cache.get(simkl().simkl_list, self.simkl_hours, url)
			if self.list is None: self.list = []
			next = ''
			for i in range(len(self.list)): self.list[i]['next'] = next
			self.worker()
			if create_directory: self.tvshowDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications and self.is_widget != True: control.notification(title=32002, message=33049)

	def getTVmaze(self, url, idx=True, folderName=''):
		from resources.lib.indexers import tvmaze
		self.list = []
		try:
			try: url = getattr(self, url + '_link')
			except: pass
			self.list = cache.get(tvmaze.TVshows().tvmaze_list, 168, url)
			# if idx: self.worker() ## TVMaze has it's own full list builder.
			if self.list is None: self.list = []
			if idx: self.tvshowDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications: control.notification(title=32002, message=33049)

	def getTraktPublicLists(self, url, create_directory=True, folderName=''):
		self.list = []
		try:
			try: url = getattr(self, url + '_link')
			except: pass
			if '/popular' in url:
				self.list = cache.get(self.trakt_public_list, self.traktpopular_hours, url)
			elif '/trending' in url:
				from resources.lib.modules import log_utils
				log_utils.log('TraktPublicLists Hours Used: %s' % str(self.trakttrending_hours), log_utils.LOGDEBUG)
				self.list = cache.get(self.trakt_public_list, self.trakttrending_hours, url)
			else:
				self.list = cache.get(self.trakt_public_list, self.trakt_hours, url) #trakt other
			if self.list is None: self.list = []
			if create_directory: self.addDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
	
	def trakt_based_on_recent(self, create_directory=True, folderName=''):
		self.list = []
		try:
			historyurl = 'https://api.trakt.tv/users/me/history/shows?limit=20&page=1'
			randomItems = self.trakt_list(historyurl, self.trakt_user, folderName)
			if not randomItems: return
			import random
			item = randomItems[random.randint(0, len(randomItems) - 1)]
			url = self.tmdb_recommendations % (item.get('tmdb'), '%s')
			self.list = tmdb_indexer().tmdb_list(url)
			if self.useContainerTitles:
				try: 
					folderName=getLS(40257)+' '+item.get('title')
					control.setHomeWindowProperty('umbrella.tvrecent', str(getLS(40257)+' '+item.get('title')))
				except: pass
			next = ''
			for i in range(len(self.list)): self.list[i]['next'] = next
			self.worker()
			if self.list is None: self.list = []
			if create_directory: self.tvshowDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return

	def trakt_based_on_similar(self, create_directory=True, folderName=''):
		self.list = []
		try:
			historyurl = 'https://api.trakt.tv/users/me/history/shows?limit=20&page=1'
			randomItems = self.trakt_list(historyurl, self.trakt_user, folderName)
			if not randomItems: return
			import random
			item = randomItems[random.randint(0, len(randomItems) - 1)]
			url = self.tmdb_similar % (item.get('tmdb'), '%s')
			self.list = tmdb_indexer().tmdb_list(url)
			if self.useContainerTitles:
				try: 
					folderName=getLS(40259)+' '+item.get('title')
					control.setHomeWindowProperty('umbrella.tvsimilar', str(getLS(40257)+' '+item.get('title')))
				except: pass
			next = ''
			for i in range(len(self.list)): self.list[i]['next'] = next
			self.worker()
			if self.list is None: self.list = []
			if create_directory: self.tvshowDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return self.list

	def tmdb_trending_recentday(self, create_directory=True, folderName=''):
		self.list = []
		try:
			url = self.tmdb_recentday
			#self.list = tmdb_indexer().tmdb_list(url)
			self.list = cache.get(tmdb_indexer().tmdb_list,self.tmdbrecentday_hours, url)
			next = ''
			for i in range(len(self.list)): self.list[i]['next'] = next
			self.worker()
			if self.list is None: self.list = []
			if create_directory: self.tvshowDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return

	def tmdb_trending_recentweek(self, create_directory=True, folderName=''):
		self.list = []
		try:
			url = self.tmdb_recentweek
			#self.list = tmdb_indexer().tmdb_list(url)
			self.list = cache.get(tmdb_indexer().tmdb_list,self.tmdbrecentweek_hours, url)
			next = ''
			for i in range(len(self.list)): self.list[i]['next'] = next
			self.worker()
			if self.list is None: self.list = []
			if create_directory: self.tvshowDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return

	def traktHiddenManager(self, idx=True):
		control.busy()
		folderName = ''
		try:
			if trakt.getProgressActivity() > cache.timeout(self.trakt_list, self.progress_link, self.trakt_user, folderName): raise Exception()
			self.list = cache.get(self.trakt_list, 24, self.progress_link, self.trakt_user, folderName)
		except: self.list = cache.get(self.trakt_list, 0, self.progress_link, self.trakt_user, folderName)

		if self.list is None: self.list = []
		for i in self.list:
			imdb, tvdb = i.get('imdb'), i.get('tvdb')
			try: indicators = getSeasonIndicators(imdb, tvdb)
			except: indicators = None
			count = getShowCount(indicators[1], imdb, tvdb) if indicators else None
			i.update({'watched_count': count})
		try:
			hidden = traktsync.fetch_hidden_progress()
			hidden = [str(i['tvdb']) for i in hidden]
			for i in self.list: i.update({'isHidden': 'true'}) if i['tvdb'] in hidden else i.update({'isHidden': ''})
			if idx: self.worker()
			self.list = sorted(self.list, key=lambda k: re.sub(r'(^the |^a |^an )', '', k['tvshowtitle'].lower()), reverse=False)
			self.list = sorted(self.list, key=lambda k: k['isHidden'], reverse=True)
			control.hide()
			from resources.lib.windows.trakthidden_manager import TraktHiddenManagerXML
			window = TraktHiddenManagerXML('trakthidden_manager.xml', control.addonPath(control.addonId()), results=self.list)
			chosen_hide, chosen_unhide = window.run()
			del window
			if chosen_unhide:
				success = trakt.unHideItems(chosen_unhide)
				if success: control.notification(title='Trakt Hidden Progress Manager', message='Successfully Unhid %s Item%s' % (len(chosen_unhide), 's' if len(chosen_unhide) >1 else ''))
			if chosen_hide:
				success = trakt.hideItems(chosen_hide)
				if success: control.notification(title='Trakt Hidden Progress Manager', message='Successfully Hid %s Item%s' % (len(chosen_hide), 's' if len(chosen_hide) >1 else ''))
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			control.hide()

	def collectionManager(self):
		try:
			control.busy()
			self.list = traktsync.fetch_collection('shows_collection')
			self.worker()
			self.sort()
			# self.list = sorted(self.list, key=lambda k: re.sub(r'(^the |^a |^an )', '', k['tvshowtitle'].lower()), reverse=False)
			control.hide()
			from resources.lib.windows.traktbasic_manager import TraktBasicManagerXML
			window = TraktBasicManagerXML('traktbasic_manager.xml', control.addonPath(control.addonId()), results=self.list)
			selected_items = window.run()
			del window
			if selected_items:
				# refresh = 'plugin.video.umbrella' in control.infoLabel('Container.PluginName')
				trakt.removeCollectionItems('shows', selected_items)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			control.hide()

	def watchlistManager(self):
		try:
			control.busy()
			self.list = traktsync.fetch_watch_list('shows_watchlist')
			self.worker()
			self.sort(type='shows.watchlist')
			# self.list = sorted(self.list, key=lambda k: re.sub(r'(^the |^a |^an )', '', k['tvshowtitle'].lower()), reverse=False)
			control.hide()
			from resources.lib.windows.traktbasic_manager import TraktBasicManagerXML
			window = TraktBasicManagerXML('traktbasic_manager.xml', control.addonPath(control.addonId()), results=self.list)
			selected_items = window.run()
			del window
			if selected_items:
				# refresh = 'plugin.video.umbrella' in control.infoLabel('Container.PluginName')
				trakt.removeWatchlistItems('shows', selected_items)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			control.hide()

	def sort(self, type='shows'):
		try:
			if not self.list: return
			attribute = int(getSetting('sort.%s.type' % type))
			reverse = int(getSetting('sort.%s.order' % type)) == 1
			if attribute == 0: 
				if type == 'progress':
					reverse = True
					attribute = 6
				else:
					reverse = False # Sorting Order is not enabled when sort method is "Default"
			if attribute > 0:
				if attribute == 1:
					try: self.list = sorted(self.list, key=lambda k: re.sub(r'(^the |^a |^an )', '', k['tvshowtitle'].lower()), reverse=reverse)
					except: self.list = sorted(self.list, key=lambda k: re.sub(r'(^the |^a |^an )', '', k['title'].lower()), reverse=reverse)
				elif attribute == 2: self.list = sorted(self.list, key=lambda k: float(k['rating']), reverse=reverse)
				elif attribute == 3: self.list = sorted(self.list, key=lambda k: int(str(k['votes']).replace(',', '')), reverse=reverse)
				elif attribute == 4:
					for i in range(len(self.list)):
						if 'premiered' not in self.list[i]: self.list[i]['premiered'] = ''
					self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=reverse)
				elif attribute == 5:
					for i in range(len(self.list)):
						if 'added' not in self.list[i]: self.list[i]['added'] = ''
					self.list = sorted(self.list, key=lambda k: k['added'], reverse=reverse)
				elif attribute == 6:
					nolastPlayed = []
					for i in range(len(self.list)):
						if 'lastplayed' not in self.list[i]: 
							self.list[i]['lastplayed'] = ''
							from resources.lib.modules import log_utils
							log_utils.log('TVShow Last Played Blank Title: %' % self.list[i]['title'], 1)
					#self.list = sorted(self.list, key=lambda k: k['lastplayed'], reverse=reverse)
					if self.list:
						self.list = sorted(self.list, key=lambda k: time.strptime(k['lastplayed'], "%Y-%m-%dT%H:%M:%S.%fZ"), reverse=reverse)
			elif reverse:
				self.list = list(reversed(self.list))
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def imdb_sort(self, type='shows'):
		sort = int(getSetting('sort.%s.type' % type))
		imdb_sort = 'list_order' if type == 'shows.watchlist' else 'moviemeter'
		if sort == 1: imdb_sort = 'alpha'
		elif sort == 2: imdb_sort = 'user_rating'
		elif sort == 3: imdb_sort = 'num_votes'
		elif sort == 4: imdb_sort = 'release_date'
		elif sort in (5, 6): imdb_sort = 'date_added'
		imdb_sort_order = ',asc' if (int(getSetting('sort.%s.order' % type)) == 0 or sort == 0) else ',desc'
		sort_string = imdb_sort + imdb_sort_order
		return sort_string

	def tmdb_DiscoverSort(self):
		sort = int(getSetting('sort.shows.type'))
		tmdb_sort = 'popularity' # default sort=0
		if sort == 1: tmdb_sort = 'title'
		elif sort == 2: tmdb_sort = 'vote_average'
		elif sort == 3: tmdb_sort = 'vote_count'
		elif sort in (4, 5, 6): tmdb_sort = 'primary_release_date'
		tmdb_sort_order = '.asc' if (int(getSetting('sort.shows.order')) == 0) else '.desc'
		sort_string = tmdb_sort + tmdb_sort_order
		if sort == 2: sort_string = sort_string + '&vote_count.gte=500'
		return sort_string

	def search(self, folderName=''):
		from resources.lib.menus import navigator
		navigator.Navigator().addDirectoryItem(getLS(32603) % self.highlight_color, 'tvSearchnew', 'search.png', 'DefaultAddonsSearch.png', isFolder=False)
		if self.useContainerTitles: control.setContainerName(folderName)
		from sqlite3 import dbapi2 as database
		try:
			if not control.existsPath(control.dataPath): control.makeFile(control.dataPath)
			dbcon = database.connect(control.searchFile)
			dbcur = dbcon.cursor()
			dbcur.executescript('''CREATE TABLE IF NOT EXISTS tvshow (ID Integer PRIMARY KEY AUTOINCREMENT, term);''')
			dbcur.execute('''SELECT * FROM tvshow ORDER BY ID DESC''')
			dbcur.connection.commit()
			lst = []
			delete_option = False
			for (id, term) in sorted(dbcur.fetchall(), key=lambda k: re.sub(r'(^the |^a |^an )', '', k[1].lower()), reverse=False):
				if term not in str(lst):
					delete_option = True
					navigator.Navigator().addDirectoryItem(term, 'tvSearchterm&name=%s' % term, 'search.png', 'DefaultAddonsSearch.png', isSearch=True, table='tvshow')
					lst += [(term)]
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
		if delete_option: navigator.Navigator().addDirectoryItem(32605, 'cache_clearSearch', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		navigator.Navigator().endDirectory()

	def search_new(self):
		k = control.keyboard('', getLS(32010))
		k.doModal()
		q = k.getText() if k.isConfirmed() else None
		if not q: return control.closeAll()
		from sqlite3 import dbapi2 as database
		try:
			dbcon = database.connect(control.searchFile)
			dbcur = dbcon.cursor()
			dbcur.execute('''INSERT INTO tvshow VALUES (?,?)''', (None, q))
			dbcur.connection.commit()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
		if self.traktCredentials:
			if getSetting('searchtv.indexer')== '1':
				url = self.search_link + quote_plus(q)
			else:
				url = self.search_tmdb_link % ('%s', quote_plus(q))
		else:
			url = self.search_tmdb_link % ('%s', quote_plus(q))
		control.closeAll()
		control.execute('ActivateWindow(Videos,plugin://plugin.video.umbrella/?action=tvshows&url=%s,return)' % (quote_plus(url)))

	def search_term(self, name):
		if name:
			if self.traktCredentials:
				if getSetting('searchtv.indexer')== '1':
					url = self.search_link + quote_plus(name)
				else:
					url = self.search_tmdb_link % ('%s', quote_plus(name))
			else:
				url = self.search_tmdb_link % ('%s', quote_plus(name))
			self.get(url)
		else:
			return

	def person(self, folderName=''):
		k = control.keyboard('', getLS(32010))
		k.doModal()
		q = k.getText().strip() if k.isConfirmed() else None
		if not q: return control.closeAll()
		url = self.persons_link + quote_plus(q)
		control.closeAll()
		control.execute('ActivateWindow(Videos,plugin://plugin.video.umbrella/?action=tvPersons&url=%s,return)' % (quote_plus(url)))

	def persons(self, url, folderName=''):
		if url is None: self.list = cache.get(self.imdb_person_list, 24, self.personlist_link)
		else: self.list = cache.get(self.imdb_person_list, 1, url)
		if self.list is None: self.list = []
		if self.list:
			for i in range(0, len(self.list)): self.list[i].update({'content': 'actors', 'icon': 'DefaultActor.png', 'action': 'tvshows&folderName=%s' % quote_plus(self.list[i]['name'])})
		self.addDirectory(self.list, folderName=folderName)
		return self.list

	def genres(self, url, folderName=''):
		try: url = getattr(self, url + '_link')
		except: pass
		genres = [
			('Action', 'action', True, '10759'), ('Adventure', 'adventure', True), ('Animation', 'animation', True, '16'), ('Anime', 'anime', False),
			('Biography', 'biography', True), ('Comedy', 'comedy', True, '35'), ('Crime', 'crime', True, '80'), ('Drama', 'drama', True, '18'),
			('Family', 'family', True, '10751'), ('Fantasy', 'fantasy', True), ('Game-Show', 'game_show', True), ('History', 'history', True),
			('Horror', 'horror', True), ('Music', 'music', True), ('Musical', 'musical', True), ('Mystery', 'mystery', True, '9648'),
			('News', 'news', True, '10763'), ('Romance', 'romance', True), ('Science Fiction', 'sci_fi', True, '10765'),
			('Sport', 'sport', True), ('Talk-Show', 'talk_show', True, '10767'), ('Thriller', 'thriller', True), ('War', 'war', True, '10768'), ('Western', 'western', True, '37')]
		if 'trakt_tvshow_genre' in url:
				titems = trakt.getTraktAsJson(self.trakt_genres)
				for l in titems:
					if l.get('name') != 'None':
						self.list.append({'content': 'genres', 'name': l.get('name'), 'url':l.get('slug'), 'image': l.get('name') + '.jpg', 'icon': l.get('name') + '.png', 'action': 'trakt_tvshow_genre&mediatype=TVShows&genre=%s&folderName=%s' % (l.get('name'),cleangenre.lang(l.get('name'), self.lang))})
		else:	
			for i in genres:
				if self.imdb_link in url: self.list.append({'content': 'genres', 'name': cleangenre.lang(i[0], self.lang), 'url': url % i[1] if i[2] else self.keyword_link % i[1], 'image': i[0] + '.jpg', 'icon': i[0] + '.png', 'action': 'tvshows&folderName=%s' % cleangenre.lang(i[0], self.lang)})
				if self.tmdb_link in url:
					try: self.list.append({'content': 'genres', 'name': cleangenre.lang(i[0], self.lang), 'url': url % ('%s', i[3]), 'image': i[0] + '.jpg', 'icon': i[0] + '.png', 'action': 'tmdbTvshows&folderName=%s' % cleangenre.lang(i[0], self.lang)})
					except: pass
		self.addDirectory(self.list, folderName=folderName)
		return self.list

	def trakt_genre_list(self, listType='', genre='', url='', folderName=''):
		if self.lang == 'en':
			filterLang = 'en'
		else:
			filterLang = self.lang+',en'
		genreslug = url
		if listType == 'trending':
			url = self.trakttrending_link +'&genres=%s&language=%s'% (genreslug, filterLang)
			self.list = cache.get(self.trakt_list,self.trakt_hours, url, self.trakt_user, folderName) #trakt trending with genre
		if listType == 'popular':
			url = self.traktpopular_link +'&genres=%s&language=%s'% (genreslug, filterLang)
			self.list = cache.get(self.trakt_list,self.trakt_hours, url, self.trakt_user, folderName) #trakt popular with genre.
		if listType =='mostplayed':
			url =self.traktmostplayed_link +'&genres=%s&language=%s'% (genreslug, filterLang)
			self.list = cache.get(self.trakt_list,self.trakt_hours, url, self.trakt_user, folderName) #trakt mostplayed with genre.
		if listType == 'mostwatched':
			url = self.traktmostwatched_link +'&genres=%s&language=%s'% (genreslug, filterLang)
			self.list = cache.get(self.trakt_list,self.trakt_hours, url, self.trakt_user, folderName) #trakt mostwatched with genre.
		if listType == 'anticipated':
			url = self.traktanticipated_link +'&genres=%s&language=%s'% (genreslug, filterLang)
			self.list = cache.get(self.trakt_list,self.trakt_hours, url, self.trakt_user, folderName) #trakt most anticipated with genre.
		if listType == 'decades':
			from resources.lib.menus import navigator
			navigator.Navigator().trakt_decades(genre=genre, mediatype='TVShows',url=url, folderName=folderName)
		if self.list: self.worker()
		if self.list: self.tvshowDirectory(self.list, folderName=folderName)
		if self.list is None: self.list = []
		return self.list

	def trakt_genre_list_decade(self, decade='', listType='', genre='', url='', folderName=''):
		if self.lang == 'en':
			filterLang = 'en'
		else:
			filterLang = self.lang+',en'
		genreslug = url
		decade = decade
		folderName = folderName + ' ('+decade+')'
		if decade == '1930-1939':
			decades = '1930-1939'
		elif decade == '1940-1949':
			decades = '1940-1949'
		elif decade == '1950-1959':
			decades = '1950-1959'
		elif decade == '1960-1969':
			decades = '1960-1969'
		elif decade == '1970-1979':
			decades = '1970-1979'
		elif decade == '1980-1989':
			decades = '1980-1989'
		elif decade == '1990-1999':
			decades = '1990-1999'
		elif decade == '2000-2009':
			decades = '2000-2009'
		elif decade == '2010-2019':
			decades = '2010-2019'
		elif decade == '2020-2029':
			decades = '2020-2024'
		if listType == 'trending':
			url = self.trakttrending_link +'&genres=%s&years=%s&languages=%s'% (genreslug, decades, filterLang)
			self.list = cache.get(self.trakt_list,self.trakt_hours, url, self.trakt_user, folderName) #trakt trending with genre
		if listType == 'popular':
			url = self.traktpopular_link+'&genres=%s&years=%s&languages=%s'% (genreslug, decades, filterLang)
			self.list = cache.get(self.trakt_list,self.trakt_hours, url, self.trakt_user, folderName) #trakt popular with genre.
		if listType =='mostplayed':
			url =self.traktmostplayed_link+'&genres=%s&years=%s&languages=%s'% (genreslug, decades, filterLang)
			self.list = cache.get(self.trakt_list,self.trakt_hours, url, self.trakt_user, folderName) #trakt mostplayed with genre.
		if listType == 'mostwatched':
			url = self.traktmostwatched_link+'&genres=%s&years=%s&languages=%s'% (genreslug, decades, filterLang)
			self.list = cache.get(self.trakt_list,self.trakt_hours, url, self.trakt_user, folderName) #trakt mostwatched with genre.
		if self.list: self.worker()
		if self.list: self.tvshowDirectory(self.list, folderName=folderName)
		if self.list is None: self.list = []
		return self.list

	def networks(self, folderName=''):
		networks = tmdb_indexer().get_networks()
		for i in networks:
			self.list.append({'content': 'studios', 'name': i[0], 'url': self.tmdb_networks_link % ('%s', i[1]), 'image': i[2], 'icon': i[2], 'action': 'tmdbTvshows&folderName=%s' % quote_plus(i[0])})
		self.addDirectory(self.list, folderName=folderName)
		return self.list

	def originals(self, folderName=''):
		originals = tmdb_indexer().get_originals()
		for i in originals:
			self.list.append({'content': 'studios', 'name': i[0], 'url': self.tmdb_networks_link % ('%s', i[1]), 'image': i[2], 'icon': i[2], 'action': 'tmdbTvshows&folderName=%s' % quote_plus(i[0])})
		self.addDirectory(self.list, folderName=folderName)
		return self.list

	def languages(self, folderName=''):
		languages = [
			('Arabic', 'ar'), ('Bosnian', 'bs'), ('Bulgarian', 'bg'), ('Chinese', 'zh'), ('Croatian', 'hr'), ('Dutch', 'nl'), ('English', 'en'), ('Finnish', 'fi'),
			('French', 'fr'), ('German', 'de'), ('Greek', 'el'), ('Hebrew', 'he'), ('Hindi ', 'hi'), ('Hungarian', 'hu'), ('Icelandic', 'is'), ('Italian', 'it'),
			('Japanese', 'ja'), ('Korean', 'ko'), ('Norwegian', 'no'), ('Persian', 'fa'), ('Polish', 'pl'), ('Portuguese', 'pt'), ('Punjabi', 'pa'),
			('Romanian', 'ro'), ('Russian', 'ru'), ('Serbian', 'sr'), ('Spanish', 'es'), ('Swedish', 'sv'), ('Turkish', 'tr'), ('Ukrainian', 'uk')]
		for i in languages:
			self.list.append({'content': 'countries', 'name': str(i[0]), 'url': self.language_link % i[1], 'image': 'languages.png', 'icon': 'DefaultAddonLanguage.png', 'action': 'tvshows&folderName=%s' % quote_plus(str(i[0]))})
		self.addDirectory(self.list, folderName=folderName)
		return self.list

	def certifications(self, folderName=''):
		certificates = [
			('Child Audience (TV-Y)', 'US%3ATV-Y'),
			('Young Audience (TV-Y7)', 'US%3ATV-Y7'),
			('General Audience (TV-G)', 'US%3ATV-G'),
			('Parental Guidance (TV-PG)', 'US%3ATV-PG'),
			('Youth Audience (TV-14)', 'US%3ATV-14'),
			('Mature Audience (TV-MA)', 'US%3ATV-MA')]
		for i in certificates:
			self.list.append({'content': 'tags', 'name': str(i[0]), 'url': self.certification_link % i[1], 'image': 'certificates.png', 'icon': 'certificates.png', 'action': 'tvshows&folderName=%s' % quote_plus(str(i[0]))})
		self.addDirectory(self.list, folderName=folderName)
		return self.list

	def years(self, url, folderName=''):
		try: url = getattr(self, url + '_link')
		except: pass
		year = (self.date_time.strftime('%Y'))
		for i in range(int(year)-0, 1900, -1):
			if self.imdb_link in url: self.list.append({'content': 'years', 'name': str(i), 'url': url % (str(i), str(i)), 'image': 'years.png', 'icon': 'DefaultYear.png', 'action': 'tvshows&folderName=%s' % quote_plus(str(i))})
			if self.tmdb_link in url: self.list.append({'content': 'years', 'name': str(i), 'url': url % ('%s', str(i)), 'image': 'years.png', 'icon': 'DefaultYear.png', 'action': 'tmdbTvshows&folderName=%s' % quote_plus(str(i))})
		self.addDirectory(self.list, folderName=folderName)
		return self.list

	def tvshowsListToLibrary(self, url):
		url = getattr(self, url + '_link')
		u = urlparse(url).netloc.lower()
		try:
			control.hide()
			if u in self.tmdb_link: items = tmdb_indexer().userlists(url)
			elif u in self.trakt_link:
				if url in self.traktlikedlists_link:
					items = self.traktLlikedlists()
				else: items = self.trakt_user_lists(url, self.trakt_user)
			items = [(i['name'], i['url']) for i in items]
			message = 32663
			if 'themoviedb' in url: message = 32681
			select = control.selectDialog([i[0] for i in items], getLS(message))
			list_name = items[select][0]
			if select == -1: return
			link = items[select][1]
			link = link.split('&sort_by')[0]
			link = link.split('?limit=')[0]
			from resources.lib.modules import library
			library.libtvshows().range(link, list_name)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def userlists(self, create_directory=False, folderName=''):
		userlists = []
		try:
			if not self.traktCredentials: raise Exception()
			activity = trakt.getActivity()
			self.list = [] ; lists = []
			try:
				if activity > cache.timeout(self.trakt_user_lists, self.traktlists_link, self.trakt_user): raise Exception()
				lists += cache.get(self.trakt_user_lists, 720, self.traktlists_link, self.trakt_user)
			except: lists += cache.get(self.trakt_user_lists, 0, self.traktlists_link, self.trakt_user)
			userlists += lists
		except: pass
		try:
			if not self.imdb_user: raise Exception()
			self.list = []
			lists = cache.get(self.imdb_user_list, 0, self.imdblists_link)
			userlists += lists
		except: pass
		try:
			if self.tmdb_session_id == '': raise Exception()
			self.list = []
			url = self.tmdb_link + '/3/account/{account_id}/lists?api_key=%s&language=en-US&session_id=%s&page=1' % ('%s', self.tmdb_session_id)
			lists = cache.get(tmdb_indexer().userlists, 0, url)
			for i in range(len(lists)): lists[i].update({'image': 'tmdb.png', 'icon': 'DefaultVideoPlaylists.png', 'action': 'tmdbTvshows'})
			userlists += lists
		except: pass
		self.list = []
		for i in range(len(userlists)): # Filter the user's own lists that were
			contains = False
			adapted = userlists[i]['url'].replace('/me/', '/%s/' % self.trakt_user)
			for j in range(len(self.list)):
				if adapted == self.list[j]['url'].replace('/me/', '/%s/' % self.trakt_user):
					contains = True
					break
			if not contains: self.list.append(userlists[i])
		if self.tmdb_session_id != '': # TMDb Favorites
			url = self.tmdb_link + '/3/account/{account_id}/favorite/tv?api_key=%s&session_id=%s&sort_by=created_at.asc&page=1' % ('%s', self.tmdb_session_id)
			self.list.insert(0, {'name': getLS(32026), 'url': url, 'image': 'tmdb.png', 'icon': 'DefaultVideoPlaylists.png', 'action': 'tmdbTvshows'})
		if self.tmdb_session_id != '': # TMDb Watchlist
			url = self.tmdb_link + '/3/account/{account_id}/watchlist/tv?api_key=%s&session_id=%s&sort_by=created_at.asc&page=1' % ('%s', self.tmdb_session_id)
			self.list.insert(0, {'name': getLS(32033), 'url': url, 'image': 'tmdb.png', 'icon': 'DefaultVideoPlaylists.png', 'action': 'tmdbTvshows'})
		if self.imdb_user != '': # imdb Watchlist
			self.list.insert(0, {'name': getLS(32033), 'url': self.imdbwatchlist_link, 'image': 'imdb.png', 'icon': 'DefaultVideoPlaylists.png', 'action': 'tvshows&folderName=%s' % quote_plus(getLS(32033))})
		if self.imdb_user != '': # imdb My Ratings
			self.list.insert(0, {'name': getLS(32025), 'url': self.imdbratings_link, 'image': 'imdb.png', 'icon': 'DefaultVideoPlaylists.png', 'action': 'tvshows&folderName=%s' % quote_plus(getLS(32025))})
		if create_directory: self.addDirectory(self.list, folderName=folderName)
		return self.list

	def traktCollection(self, url, create_directory=True, folderName=''):
		self.list = []
		try:
			try:
				q = dict(parse_qsl(urlsplit(url).query))
				index = int(q['page']) - 1
			except:
				q = dict(parse_qsl(urlsplit(url).query))
			self.list = traktsync.fetch_collection('shows_collection')
			if create_directory:
				self.sort() # sort before local pagination
				if getSetting('trakt.paginate.lists') == 'true' and self.list:
					paginated_ids = [self.list[x:x + int(self.page_limit)] for x in range(0, len(self.list), int(self.page_limit))]
					self.list = paginated_ids[index]
			try:
				if int(q['limit']) != len(self.list): raise Exception()
				q.update({'page': str(int(q['page']) + 1)})
				q = (urlencode(q)).replace('%2C', ',')
				next = url.replace('?' + urlparse(url).query, '') + '?' + q
				next = next + '&folderName=%s' % quote_plus(folderName)
			except: next = ''
			for i in range(len(self.list)): self.list[i]['next'] = next
			self.worker()
			if self.list is None: self.list = []
			if create_directory: self.tvshowDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def traktWatchlist(self, url, create_directory=True, folderName=''):
		self.list = []
		try:
			try:
				q = dict(parse_qsl(urlsplit(url).query))
				index = int(q['page']) - 1
			except:
				q = dict(parse_qsl(urlsplit(url).query))
			self.list = traktsync.fetch_watch_list('shows_watchlist')
			if create_directory:
				self.sort(type='shows.watchlist') # sort before local pagination
				if getSetting('trakt.paginate.lists') == 'true' and self.list:
					paginated_ids = [self.list[x:x + int(self.page_limit)] for x in range(0, len(self.list), int(self.page_limit))]
					self.list = paginated_ids[index]
			try:
				if int(q['limit']) != len(self.list): raise Exception()
			
				q.update({'page': str(int(q['page']) + 1)})
				q = (urlencode(q)).replace('%2C', ',')
				next = url.replace('?' + urlparse(url).query, '') + '?' + q
				next = next + '&folderName=%s' % quote_plus(folderName)
			except: next = ''
			for i in range(len(self.list)): self.list[i]['next'] = next
			self.worker()
			if self.list is None: self.list = []
			if create_directory: self.tvshowDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def traktLlikedlists(self, create_directory=True, folderName=''):
		items = traktsync.fetch_liked_list('', True)
		showOwnerShow = getSetting('trakt.lists.showowner') == 'true'
		for item in items:
			try:
				if item['content_type'] == 'movies': continue
				if item['content_type'] == 'mixed': continue
				list_name = item['list_name']
				listAction = 'tvshows'
				listAction = listAction+'&folderName=%s' % quote_plus(list_name)
				list_owner = item['list_owner']
				list_owner_slug = item['list_owner_slug']
				list_id = item['trakt_id']
				list_url = self.traktlist_link % (list_owner_slug, list_id)
				list_count = item['item_count']
				next = ''
				if showOwnerShow:
					label = '%s - [COLOR %s]%s[/COLOR]' % (list_name, self.highlight_color, list_owner)
				else:
					label = '%s' % (list_name)
				self.list.append({'name': label, 'list_type': 'traktPulicList', 'url': list_url, 'list_owner': list_owner, 'list_owner_slug': list_owner_slug, 'list_name': list_name, 'list_id': list_id, 'context': list_url, 'next': next, 'list_count': list_count, 'image': 'trakt.png', 'icon': 'DefaultVideoPlaylists.png', 'action': listAction})
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		self.list = sorted(self.list, key=lambda k: re.sub(r'(^the |^a |^an )', '', k['name'].lower()))
		if create_directory: self.addDirectory(self.list, queue=True, folderName=folderName)
		return self.list

	def trakt_list(self, url, user, folderName):
		self.list = []
		if ',return' in url: url = url.split(',return')[0]
		items = trakt.getTraktAsJson(url)
		if not items: return
		try:
			q = dict(parse_qsl(urlsplit(url).query))
			if int(q['limit']) != len(items): raise Exception()
			q.update({'page': str(int(q['page']) + 1)})
			q = (urlencode(q)).replace('%2C', ',')
			next = url.replace('?' + urlparse(url).query, '') + '?' + q
			next = next + '&folderName=%s' % quote_plus(folderName)
		except: next = ''
		for item in items: # rating and votes via TMDb, or I must use `extended=full and it slows down
			try:
				values = {}
				values['next'] = next 
				values['added'] = item.get('listed_at', '')
				values['paused_at'] = item.get('paused_at', '') # for unfinished
				try: values['progress'] = item['progress']
				except: values['progress'] = ''
				try: values['lastplayed'] = item['last_watched_at'] # for history
				except: values['lastplayed'] = ''
				show = item.get('show') or item
				values['title'] = show.get('title')
				values['originaltitle'] = values['title']
				values['tvshowtitle'] = values['title']
				values['year'] = str(show.get('year')) if show.get('year') else ''
				ids = show.get('ids', {})
				values['imdb'] = str(ids.get('imdb', '')) if ids.get('imdb') else ''
				values['tmdb'] = str(ids.get('tmdb', '')) if ids.get('tmdb') else ''
				values['tvdb'] = str(ids.get('tvdb', '')) if ids.get('tvdb') else ''
				values['mediatype'] = 'tvshows'
				self.list.append(values)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		return self.list

	def favouriteTVShows(self, create_directory=True, folderName=''):
			self.list = []
			try:
				from resources.lib.modules import favourites
				results = favourites.getFavourites('tvshows')
				if results:
					for item in results:
						try:
							values = {}
							values['title'] = item[1].get('title','')
							values['premiered'] = item[1].get('year','')
							values['year'] = item[1].get('year','')
							values['imdb'] = item[1].get('imdb','')
							values['tmdb'] = item[1].get('tmdb','')
							self.list.append(values)
						except:
							from resources.lib.modules import log_utils
							log_utils.error()
				next = ''
				for i in range(len(self.list)): self.list[i]['next'] = next
				self.worker()
				self.sort(type="shows.favourite")
				if len(self.list) > 0:
					if create_directory: self.tvshowDirectory(self.list, folderName=folderName)
				return self.list
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
				return []

	def trakt_userList(self, url, create_directory=True, folderName=''):
		self.list = []
		q = dict(parse_qsl(urlsplit(url).query))
		index = int(q['page']) - 1
		def userList_totalItems(url):
			items = trakt.getTraktAsJson(url)
			if not items: return
			watchedItems = trakt.watchedShows()
			for item in items:
				try:
					values = {}
					values['added'] = item.get('listed_at', '')
					show = item['show']
					values['title'] = show.get('title')
					values['originaltitle'] = values['title']
					values['tvshowtitle'] = values['title']
					try: values['premiered'] = show.get('first_aired', '')[:10]
					except: values['premiered'] = ''
					values['year'] = str(show.get('year', '')) if show.get('year') else ''
					if not values['year']:
						try: values['year'] = str(values['premiered'][:4])
						except: values['year'] = ''
					ids = show.get('ids', {})
					values['imdb'] = str(ids.get('imdb', '')) if ids.get('imdb') else ''
					values['tmdb'] = str(ids.get('tmdb', '')) if ids.get('tmdb') else ''
					values['tvdb'] = str(ids.get('tvdb')) if ids.get('tvdb', '') else ''
					values['rating'] = show.get('rating')
					values['votes'] = show.get('votes')
					airs = show.get('airs', {})
					values['airday'] = airs['day']
					values['airtime'] = airs['time']
					values['airzone'] = airs['timezone']
					values['mediatype'] = 'tvshows'
					try:
						item_list = [item for item in watchedItems if item.get('show').get('title') == show.get('title')]
					except:
						item_list = None
					if item_list:
						try: values['lastplayed'] = item_list[0].get('last_watched_at') # for by date sorting
						except: values['lastplayed'] = ''
					self.list.append(values)
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
			return self.list
		self.list = cache.get(userList_totalItems, self.traktuserlist_hours, url.split('limit')[0] + 'extended=full')
		if not self.list: return
		self.sort() # sort before local pagination
		total_pages = 1
		if getSetting('trakt.paginate.lists') == 'true':
			paginated_ids = [self.list[x:x + int(self.page_limit)] for x in range(0, len(self.list), int(self.page_limit))]
			total_pages = len(paginated_ids)
			self.list = paginated_ids[index]
		try:
			if int(q['limit']) != len(self.list): raise Exception()
			if int(q['page']) == total_pages: raise Exception()
			q.update({'page': str(int(q['page']) + 1)})
			q = (urlencode(q)).replace('%2C', ',')
			next = url.replace('?' + urlparse(url).query, '') + '?' + q
			next = next + '&folderName=%s' % quote_plus(folderName)
		except: next = ''
		for i in range(len(self.list)): self.list[i]['next'] = next
		self.worker()
		if self.list is None: self.list = []
		if create_directory: self.tvshowDirectory(self.list, folderName=folderName)
		return self.list

	def trakt_user_lists(self, url, user):
		items = traktsync.fetch_user_lists('', True)
		for item in items:
			try:
				if item['content_type'] == 'movies': continue
				listAction = 'tvshows'
				if item['content_type'] == 'mixed':
					listAction = 'mixed'
				list_name = item['list_name']
				listAction = listAction+'&folderName=%s' % quote_plus(list_name)
				list_owner = item['list_owner']
				list_owner_slug = item['list_owner_slug']
				list_id = item['trakt_id']
				list_url = self.traktlist_link % (list_owner_slug, list_id)
				list_count = item['item_count']
				next = ''
				if getSetting('trakt.lists.showowner') == 'true':
					label = '%s - [COLOR %s]%s[/COLOR]' % (list_name, self.highlight_color, list_owner)
				else:
					label = '%s' % (list_name)
				self.list.append({'name': label, 'url': list_url, 'list_owner': list_owner, 'list_owner_slug': list_owner_slug, 'list_name': list_name, 'list_id': list_id, 'context': list_url, 'next': next, 'list_count': list_count, 'image': 'trakt.png', 'icon': 'DefaultVideoPlaylists.png', 'action': listAction})
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		self.list = sorted(self.list, key=lambda k: re.sub(r'(^the |^a |^an )', '', k['name'].lower()))
		return self.list

	def trakt_public_list(self, url):
		try:
			items = trakt.getTrakt(url).json()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		try:
			q = dict(parse_qsl(urlsplit(url).query))
			if int(q['limit']) != len(items): raise Exception()
			q.update({'page': str(int(q['page']) + 1)})
			q = (urlencode(q)).replace('%2C', ',')
			next = url.replace('?' + urlparse(url).query, '') + '?' + q
		except: next = ''

		for item in items:
			try:
				list_item = item.get('list', {})
				list_name = list_item.get('name', '')
				list_id = list_item.get('ids', {}).get('trakt', '')

				list_content = traktsync.fetch_public_list(list_id)
				if not list_content: pass
				else: 
					if list_content.get('content_type', '') == 'movies': continue

				list_owner = list_item.get('user', {}).get('username', '')
				list_owner_slug = list_item.get('user', {}).get('ids', {}).get('slug', '')
				if not list_owner_slug: list_owner_slug = list_owner.lower()
				if any(list_item.get('privacy', '') == value for value in ('private', 'friends')): continue
				if list_item.get('user', {}).get('private') is True: continue

				if list_owner_slug == 'trakt': list_url = 'https://api.trakt.tv/lists/%s/items/?limit=%s&page=1' % (list_id, self.page_limit)
				else: list_url = self.traktlist_link % (list_owner_slug, list_id)
				if getSetting('trakt.lists.showowner') == 'true':
					label = '%s - [COLOR %s]%s[/COLOR]' % (list_name, self.highlight_color, list_owner)
				else:
					label = '%s' % (list_name)
				self.list.append({'name': label, 'list_type': 'traktPulicList', 'url': list_url, 'list_owner': list_owner, 'list_name': list_name, 'list_id': list_id, 'context': list_url, 'next': next, 'image': 'trakt.png', 'icon': 'trakt.png', 'action': 'tvshows&folderName=%s' % quote_plus(list_name)})
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		return self.list
	def mbd_top_lists(self):
		try:
			listType = 'show'
			items = mdblist.getMDBTopList(self, listType)
			next = ''
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		for item in items:
			try:
				list_name = item.get('params', {}).get('list_name', '')
				list_id = item.get('params', {}).get('list_id', '')
				list_owner = item.get('unique_ids', {}).get('user', '')
				list_count = item.get('params', {}).get('list_count', '')
				list_url = self.mbdlist_list_items % (list_id)
				label = '%s - %s shows' % (list_name, list_count)
				self.list.append({'name': label, 'url': list_url, 'list_owner': list_owner, 'list_name': list_name, 'list_id': list_id, 'context': list_url, 'next': next, 'image': 'mdblist.png', 'icon': 'mdblist.png', 'action': 'tvshows&folderName=%s' % quote_plus(list_name)})
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		return self.list
	def mdb_list_items(self, url, create_directory=True, folderName=''):
		self.list = []
		q = dict(parse_qsl(urlsplit(url).query))
		index = int(q['page']) - 1
		def userList_totalItems(url):
			items = mdblist.getMDBItems(url)
			if not items: return
			for item in items:
				try:
					values = {}
					values['title'] = item.get('title', '')
					values['originaltitle'] = item.get('title', '')
					values['tvshowtitle'] = item.get('title', '')
					try: values['premiered'] = item['release_year']
					except: values['premiered'] = ''
					values['year'] = str(item.get('release_year', '')) if item.get('release_year') else ''
					values['imdb'] = str(item.get('imdb', '')) if item.get('imdb') else ''
					values['rank'] = item.get('rank')
					self.list.append(values)
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
			return self.list
		self.list = userList_totalItems(url)
		if not self.list: return
		self.sort() # sort before local pagination
		total_pages = 1
		paginated_ids = [self.list[x:x + int(self.page_limit)] for x in range(0, len(self.list), int(self.page_limit))]
		total_pages = len(paginated_ids)
		self.list = paginated_ids[index]
		try:
			if int(q['limit']) != len(self.list): raise Exception()
			if int(q['page']) == total_pages: raise Exception()
			q.update({'page': str(int(q['page']) + 1)})
			q = (urlencode(q)).replace('%2C', ',')
			next = url.replace('?' + urlparse(url).query, '') + '?' + q
			next = next + '&folderName=%s' % quote_plus(folderName)
		except: next = ''
		for i in range(len(self.list)): self.list[i]['next'] = next
		self.worker()
		if self.list is None: self.list = []
		if create_directory: self.tvshowDirectory(self.list, folderName=folderName)
		return self.list
	def getMDBUserList(self, create_directory=True, folderName=''):
		
		self.list = []
		try:
			#self.list = cache.get(self.mbd_top_lists, 0)
			self.list = cache.get(self.mbd_user_lists, self.mdblist_hours)
			#self.list = self.mbd_user_lists()
			if self.list is None: self.list = []
			return self.addDirectory(self.list, folderName=folderName)

		except:
			from resources.lib.modules import log_utils
			log_utils.error()
	def mbd_user_lists(self):
		try:
			listType = 'show'
			items = mdblist.getMDBUserList(self, listType)
			next = ''
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		for item in items:
			try:
				list_name = item.get('params', {}).get('list_name', '')
				list_id = item.get('params', {}).get('list_id', '')
				list_owner = item.get('unique_ids', {}).get('user', '')
				list_count = item.get('params', {}).get('list_count', '')
				list_url = self.mbdlist_list_items % (list_id)
				label = '%s - (%s)' % (list_name, list_count)
				folderN = quote_plus(list_name)
				self.list.append({'name': label, 'url': list_url, 'list_owner': list_owner, 'list_name': list_name, 'list_id': list_id, 'context': list_url, 'next': next, 'image': 'mdblist.png', 'icon': 'mdblist.png','folderName': folderN, 'action': 'tvshows'})
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		return self.list

	def imdb_list(self, url, isRatinglink=False, folderName=''):
		list = [] ; items = [] ; dupes = []
		try:
			for i in re.findall(r'date\[(\d+)\]', url):
				url = url.replace('date[%s]' % i, (self.date_time - timedelta(days=int(i))).strftime('%Y-%m-%d'))
			def imdb_watchlist_id(url):
				return client.parseDOM(client.request(url), 'meta', ret='content', attrs = {'property': 'pageId'})[0]
			if url == self.imdbwatchlist_link:
				url = cache.get(imdb_watchlist_id, 8640, url)
				url = self.imdbwatchlist2_link % url
			result = client.request(url)
			result = result.replace('\n', ' ')
			items = client.parseDOM(result, 'div', attrs = {'class': '.+? lister-item'}) + client.parseDOM(result, 'div', attrs = {'class': 'lister-item .+?'})
			items += client.parseDOM(result, 'div', attrs = {'class': 'list_item.+?'})
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return
		try:
			# HTML syntax error, " directly followed by attribute name. Insert space in between. parseDOM can otherwise not handle it.
			result = result.replace('"class="lister-page-next', '" class="lister-page-next')
			next = client.parseDOM(result, 'a', ret='href', attrs = {'class': 'lister-page-next.+?'})
			if len(next) == 0:
				next = client.parseDOM(result, 'div', attrs = {'class': 'pagination'})[0]
				next = zip(client.parseDOM(next, 'a', ret='href'), client.parseDOM(next, 'a'))
				next = [i[0] for i in next if 'Next' in i[1]]
			next = url.replace(urlparse(url).query, urlparse(next[0]).query)
			next = client.replaceHTMLCodes(next)
			next = next + '&folderName=%s' % quote_plus(folderName)
		except: next = ''
		for item in items:
			try:
				title = client.replaceHTMLCodes(client.parseDOM(item, 'a')[1])
				year = client.parseDOM(item, 'span', attrs = {'class': 'lister-item-year.+?'})
				year += client.parseDOM(item, 'span', attrs = {'class': 'year_type'})
				year = re.findall(r'(\d{4})', year[0])[0]
				if int(year) > int((self.date_time).strftime('%Y')): raise Exception()
				imdb = client.parseDOM(item, 'a', ret='href')[0]
				imdb = re.findall(r'(tt\d*)', imdb)[0]
				if imdb in dupes: raise Exception()
				dupes.append(imdb)
				rating = votes = ''
				try:
					rating = client.parseDOM(item, 'div', attrs = {'class': 'ratings-bar'})
					rating = client.parseDOM(rating, 'strong')[0]
				except:
					try:
						rating = client.parseDOM(item, 'span', attrs = {'class': 'rating-rating'})
						rating = client.parseDOM(rating, 'span', attrs = {'class': 'value'})[0]
					except:
						try: rating = client.parseDOM(item, 'div', ret='data-value', attrs = {'class': '.*?imdb-rating'})[0] 
						except:
							try: rating = client.parseDOM(item, 'span', attrs = {'class': 'ipl-rating-star__rating'})[0]
							except: rating = ''
				try: votes = client.parseDOM(item, 'span', attrs = {'name': 'nv'})[0]
				except:
					try: votes = client.parseDOM(item, 'div', ret='title', attrs = {'class': '.*?rating-list'})[0]
					except:
						try: votes = re.findall(r'\((.+?) vote(?:s|)\)', votes)[0]
						except: votes = ''
				list.append({'title': title, 'tvshowtitle': title, 'originaltitle': title, 'year': year, 'imdb': imdb, 'tmdb': '', 'tvdb': '', 'rating': rating, 'votes': votes, 'next': next})
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		return list

	def imdb_genre_list(self, url, isRatinglink=False, folderName=''):
			list = [] ; items = [] ; dupes = []
			try:
				for i in re.findall(r'date\[(\d+)\]', url):
					url = url.replace('date[%s]' % i, (self.date_time - timedelta(days=int(i))).strftime('%Y-%m-%d'))
				def imdb_watchlist_id(url):
					return client.parseDOM(client.request(url), 'meta', ret='content', attrs = {'property': 'pageId'})[0]
				if url == self.imdbwatchlist_link:
					url = cache.get(imdb_watchlist_id, 8640, url)
					url = self.imdbwatchlist2_link % url
				result = client.request(url)
				result = result.replace('\n', ' ')
				items = client.parseDOM(result, 'div', attrs = {'class': 'ipc-metadata-list-summary-item__tc'})
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
				return
			next= ''
			for item in items:
				try:
					main_title = client.parseDOM(item, 'h3', attrs = {'class': 'ipc-title__text'})
					title = main_title[0].split('. ')[1]
					year = client.parseDOM(item, 'span', attrs = {'class': '.*?dli-title-metadata-item'})[0]
					year = year[:4]
					if int(year) > int((self.date_time).strftime('%Y')): raise Exception()
					imdb = client.parseDOM(item, 'a', ret='href')[0]
					imdb = re.findall(r'(tt\d*)', imdb)[0]
					if imdb in dupes: raise Exception()
					dupes.append(imdb)
					rating = votes = ''
					list.append({'title': title, 'tvshowtitle': title, 'originaltitle': title, 'year': year, 'imdb': imdb, 'tmdb': '', 'tvdb': '', 'rating': rating, 'votes': votes, 'next': next})
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
			return list

	def imdb_person_list(self, url):
		list = []
		try:
			result = client.request(url)
			#items = client.parseDOM(result, 'div', attrs = {'class': '.+? mode-detail'})
			items = client.parseDOM(result, 'div', attrs = {'class': 'ipc-metadata-list-summary-item__tc'})
		except: return
		for item in items:
			try:
				name = client.parseDOM(item, 'img', ret='alt')[0]
				url = client.parseDOM(item, 'a', ret='href')[0]
				url = re.findall(r'(nm\d*)', url, re.I)[0]
				url = self.person_link % url
				url = client.replaceHTMLCodes(url)
				image = client.parseDOM(item, 'img', ret='src')[0]
				image = re.sub(r'(?:_SX|_SY|_UX|_UY|_CR|_AL)(?:\d+|_).+?\.', '_SX500.', image)
				image = client.replaceHTMLCodes(image)
				list.append({'name': name, 'url': url, 'image': image})
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		return list

	def imdb_user_list(self, url):
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
				list.append({'name': name, 'url': url, 'context': url, 'image': 'imdb.png', 'icon': 'DefaultVideoPlaylists.png', 'action': 'tvshows&folderName=%s' % quote_plus(name)})
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		list = sorted(list, key=lambda k: re.sub(r'(^the |^a |^an )', '', k['name'].lower()))
		return list

	def tvshow_progress(self, url, folderName=''):
		self.list = []
		try:
			cache.get(self.trakt_tvshow_progress, 0, folderName)
			self.sort(type='progress')
			if self.list is None: self.list = []
			hasNext = False
			self.tvshowDirectory(self.list, next=hasNext, isProgress=True, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications and self.is_widget != True: control.notification(title=32326, message=33049)

	def trakt_tvshow_progress(self, create_directory=True, folderName=''):
		self.list = []
		try:
			historyurl = 'https://api.trakt.tv/users/me/watched/shows'
			self.list = self.trakt_list(historyurl, self.trakt_user, folderName)
			next = ''
			for i in range(len(self.list)): self.list[i]['next'] = next
			self.worker()
			if self.list is None: self.list = []
			try:
				hidden = traktsync.fetch_hidden_progress()
				hidden = [str(i['tvdb']) for i in hidden]
				self.list = [i for i in self.list if i['tvdb'] not in hidden] # removes hidden progress items
				prior_week = int(re.sub(r'[^0-9]', '', (self.date_time - timedelta(days=7)).strftime('%Y-%m-%d')))
				sorted_list = []
				top_items = [i for i in self.list if i['premiered'] and (int(re.sub(r'[^0-9]', '', str(i['premiered']))) >= prior_week)]
				sorted_list.extend(top_items)
				sorted_list.extend([i for i in self.list if i not in top_items])
				self.list = sorted_list
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
			#if create_directory: self.tvshowDirectory(self.list)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		return self.list

	def tvshow_watched(self, url, folderName=''):
		self.list = []
		try:
			cache.get(self.trakt_tvshow_watched, 0, folderName)
			self.sort(type='watched')
			if self.list is None: self.list = []
			hasNext = False
			self.tvshowDirectory(self.list, next=hasNext, isProgress=False, isWatched=True, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				if self.notifications and self.is_widget != True: control.notification(title=32326, message=33049)

	def trakt_tvshow_watched(self, create_directory=True, folderName=''):
		self.list = []
		try:
			historyurl = 'https://api.trakt.tv/users/me/watched/shows'
			self.list = self.trakt_list(historyurl, self.trakt_user, folderName)
			next = ''
			for i in range(len(self.list)): self.list[i]['next'] = next
			self.worker()
			if self.list is None: self.list = []
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		return self.list

	def worker(self):
		try:
			if not self.list: return
			self.meta = []
			total = len(self.list)
			for i in range(0, total): self.list[i].update({'metacache': False})
			self.list = metacache.fetch(self.list, self.lang, self.user)
			for r in range(0, total, 40):
				threads = []
				append = threads.append
				for i in range(r, r + 40):
					if i < total: append(Thread(target=self.super_info, args=(i,)))
				[i.start() for i in threads]
				[i.join() for i in threads]
			if self.meta: metacache.insert(self.meta)
			self.list = [i for i in self.list if i.get('tmdb')] # to rid missing tmdb_id's because season list can not load without
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def super_info(self, i):
		try:
			if self.list[i]['metacache']: return
			imdb, tmdb, tvdb = self.list[i].get('imdb', ''), self.list[i].get('tmdb', ''), self.list[i].get('tvdb', '')
			#from resources.lib.modules import log_utils
			#log_utils.log('TV Show Super Function: ids={imdb: %s, tmdb: %s, tvdb: %s} ' % (self.list[i].get('imdb', ''), self.list[i].get('tmdb', ''), self.list[i].get('tvdb', '')), __name__, log_utils.LOGDEBUG) # newlognov
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
					tmdb = str(result.get('id', '')) if result.get('id') else ''
				except: tmdb = ''
			if not imdb or not tmdb or not tvdb:
				try:
					results = trakt.SearchTVShow(quote_plus(self.list[i]['title']), self.list[i]['year'], full=False)
					if results[0]['show']['title'].lower() != self.list[i]['title'].lower() or int(results[0]['show']['year']) != int(self.list[i]['year']): return # Trakt has "THEM" and "Them" twice for same show, use .lower()
					ids = results[0].get('show', {}).get('ids', {})
					if not imdb: imdb = str(ids.get('imdb', '')) if ids.get('imdb') else ''
					if not tmdb: tmdb = str(ids.get('tmdb', '')) if ids.get('tmdb') else ''
					if not tvdb: tvdb = str(ids.get('tvdb', '')) if ids.get('tvdb') else ''
				except: pass
#################################
			if not tmdb:
				if getSetting('debug.level') != '1': return
				from resources.lib.modules import log_utils
				#return log_utils.log('tvshowtitle: (%s) missing tmdb_id: ids={imdb: %s, tmdb: %s, tvdb: %s}' % (self.list[i]['title'], imdb, tmdb, tvdb), __name__, log_utils.LOGDEBUG) # log TMDb shows that they do not have
				return None
			showSeasons = tmdb_indexer().get_showSeasons_meta(tmdb)
			if not showSeasons or '404:NOT FOUND' in showSeasons: return # trakt search turns up alot of junk with wrong tmdb_id's
			values = {}
			values.update(showSeasons)
			if 'rating' in self.list[i] and self.list[i]['rating']: values['rating'] = self.list[i]['rating'] # prefer imdb,trakt rating and votes if set
			if 'votes' in self.list[i] and self.list[i]['votes']: values['votes'] = self.list[i]['votes']
			if 'year' in self.list[i] and self.list[i]['year'] != values.get('year'): values['year'] = self.list[i]['year']
			if not tvdb: tvdb = values.get('tvdb', '')
			if not values.get('imdb'): values['imdb'] = imdb
			if not values.get('tmdb'): values['tmdb'] = tmdb
			if not values.get('tvdb'): values['tvdb'] = tvdb
			if self.lang != 'en':
				try:
					if 'available_translations' in self.list[i] and self.lang not in self.list[i]['available_translations']: raise Exception()
					trans_item = trakt.getTVShowTranslation(imdb, lang=self.lang, full=True)
					if trans_item:
						if trans_item.get('title'):
							values['tvshowtitle'] = trans_item.get('title')
							values['title'] = trans_item.get('title')
						if trans_item.get('overview'): values['plot'] =trans_item.get('overview')
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
			if self.enable_fanarttv:
				extended_art = fanarttv_cache.get(FanartTv().get_tvshow_art, 336, tvdb)
				if extended_art: values.update(extended_art)
			values = dict((k, v) for k, v in iter(values.items()) if v is not None and v != '') # remove empty keys so .update() doesn't over-write good meta with empty values.
			if values.get('imdb') != imdb:
				values['imdb'] = imdb
			self.list[i].update(values)
			meta = {'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'lang': self.lang, 'user': self.user, 'item': values}
			self.meta.append(meta)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def tvshowDirectory(self, items, next=True, isProgress=False, isWatched=False, folderName='Umbrella'):
		from sys import argv # some functions like ActivateWindow() throw invalid handle less this is imported here.
		if self.useContainerTitles: control.setContainerName(folderName)
		returnHome = control.folderPath()
		control.setHomeWindowProperty('umbrella.returnhome', returnHome)
		if getSetting('trakt.directProgress.scrape') == 'true' and getSetting('enable.playnext') == 'true':
			pass
		else:
			control.playlist.clear()
		if not items: # with reuselanguageinvoker on an empty directory must be loaded, do not use sys.exit()
			control.hide()
			if self.is_widget != True:
				control.notification(title=32002, message=33049)
		sysaddon, syshandle = 'plugin://plugin.video.umbrella/', int(argv[1])
		is_widget = 'plugin' not in control.infoLabel('Container.PluginName')
		settingFanart = getSetting('fanart') == 'true'
		addonPoster, addonFanart, addonBanner = control.addonPoster(), control.addonFanart(), control.addonBanner()
		flatten = int(getSetting('flatten.tvshows'))
		if trakt.getTraktIndicatorsInfo(): watchedMenu, unwatchedMenu = getLS(32068), getLS(32069)
		else: watchedMenu, unwatchedMenu = getLS(32066), getLS(32067)
		traktManagerMenu, queueMenu = getLS(32070), getLS(32065)
		showPlaylistMenu, clearPlaylistMenu = getLS(35517), getLS(35516)
		playRandom, addToLibrary, addToFavourites, removeFromFavourites = getLS(32535), getLS(32551), getLS(40463), getLS(40468)
		nextMenu, findSimilarMenu, trailerMenu = getLS(32053), getLS(32184), getLS(40431)
		from resources.lib.modules import favourites
		favoriteItems = favourites.getFavourites(content='tvshows')
		favoriteItems = [x[1].get('tmdb') for x in favoriteItems]
		try:
			nexturl = items[0]['next']
			url_params = dict(parse_qsl(urlsplit(nexturl).query))
			if 'imdb.com' in nexturl and 'start' in url_params: page = int(((int(url_params.get('start')) - 1) / int(self.page_limit)) + 1)
			elif 'www.imdb.com/movies-coming-soon/' in nexturl: page = int(re.search(r'(\d{4}-\d{2})', nexturl).group(1))
			else: page = int(url_params.get('page'))
		except:
			page = 1
		for i in items:
			try:
				imdb, tmdb, tvdb, year, trailer = i.get('imdb', ''), i.get('tmdb', ''), i.get('tvdb', ''), i.get('year', ''), i.get('trailer', '')
				title = label = i.get('tvshowtitle') or i.get('title')
				systitle = quote_plus(title)
				if isProgress:
					pass
				else:
					try:
						premiered = i['premiered']
						if (not premiered and i['status'] in ('Rumored', 'Planned', 'In Production', 'Post Production', 'Upcoming')) or (int(re.sub('[^0-9]', '', premiered)) > int(re.sub('[^0-9]', '', str(self.today_date)))):
							if self.showunaired: label = '[COLOR %s]%s [I][Coming Soon][/I][/COLOR]' % (self.unairedcolor, label)
							else: continue
					except: pass
				try: indicators = getSeasonIndicators(imdb, tvdb)
				except: indicators = None
				meta = dict((k, v) for k, v in iter(i.items()) if v is not None and v != '')
				meta.update({'code': imdb, 'imdbnumber': imdb, 'mediatype': 'tvshow', 'tag': [imdb, tmdb]}) # "tag" and "tagline" for movies only, but works in my skin mod so leave
				try: meta.update({'genre': cleangenre.lang(meta['genre'], self.lang)})
				except: pass
				try:
					if 'tvshowtitle' not in meta: meta.update({'tvshowtitle': title})
				except: pass
				if self.prefer_tmdbArt: 
					poster = meta.get('poster3') or meta.get('poster') or meta.get('poster2') or addonPoster
					clearlogo = meta.get('tmdblogo') or meta.get('clearlogo', '')
					meta.update({'clearlogo': clearlogo})
				else: 
					poster = meta.get('poster2') or meta.get('poster3') or meta.get('poster') or addonPoster
					clearlogo = meta.get('clearlogo') or meta.get('tmdblogo', '')
					meta.update({'clearlogo': clearlogo})
				landscape = meta.get('landscape')
				fanart = ''
				if settingFanart:
					if self.prefer_tmdbArt: fanart = meta.get('fanart3') or meta.get('fanart') or meta.get('fanart2') or addonFanart
					else: fanart = meta.get('fanart2') or meta.get('fanart3') or meta.get('fanart') or addonFanart
				thumb = meta.get('thumb') or poster or landscape
				icon = meta.get('icon') or poster
				banner = meta.get('banner3') or meta.get('banner2') or meta.get('banner') or None #changed due to some skins using banner.
				art = {}
				art.update({'poster': poster, 'tvshow.poster': poster, 'fanart': fanart, 'icon': icon, 'thumb': thumb, 'banner': banner, 'clearlogo': meta.get('clearlogo', ''),
						'tvshow.clearlogo': meta.get('clearlogo', ''), 'clearart': meta.get('clearart', ''), 'tvshow.clearart': meta.get('clearart', ''), 'landscape': landscape})
				for k in ('metacache', 'poster2', 'poster3', 'fanart2', 'fanart3', 'banner2', 'banner3', 'trailer'): meta.pop(k, None)
				meta.update({'poster': poster, 'fanart': fanart, 'banner': banner, 'thumb': thumb, 'icon': icon})
				sysmeta, sysart = quote_plus(jsdumps(meta)), quote_plus(jsdumps(art))
				if flatten > 0:
					total_seasons = meta.get('total_seasons')
					if flatten == 2 and total_seasons < 2: url = '%s?action=episodes&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&meta=%s' % (sysaddon, systitle, year, imdb, tmdb, tvdb, sysmeta)
					elif flatten == 1: url = '%s?action=episodes&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&meta=%s' % (sysaddon, systitle, year, imdb, tmdb, tvdb, sysmeta)
					else: url = '%s?action=seasons&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&art=%s' % (sysaddon, systitle, year, imdb, tmdb, tvdb, sysart)
				else: url = '%s?action=seasons&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&art=%s' % (sysaddon, systitle, year, imdb, tmdb, tvdb, sysart)

####-Context Menu and Overlays-####
				cm = []
				if trailer:
					cm.append((trailerMenu, 'RunPlugin(%s?action=play_Trailer_Context&type=%s&name=%s&year=%s&imdb=%s&url=%s)' % (sysaddon, 'show', systitle, year, imdb, trailer)))
				try:
					watched = (getTVShowOverlay(indicators[1], imdb, tvdb) == '5') if indicators else False
					if self.traktCredentials:
						cm.append((traktManagerMenu, 'RunPlugin(%s?action=tools_traktManager&name=%s&imdb=%s&tvdb=%s&watched=%s&tvshow=tvshow)' % (sysaddon, systitle, imdb, tvdb, watched)))
					if watched:
						meta.update({'playcount': 1, 'overlay': 5})
						cm.append((unwatchedMenu, 'RunPlugin(%s?action=playcount_TVShow&name=%s&imdb=%s&tvdb=%s&query=4)' % (sysaddon, systitle, imdb, tvdb)))
					else:
						meta.update({'playcount': 0, 'overlay': 4})
						cm.append((watchedMenu, 'RunPlugin(%s?action=playcount_TVShow&name=%s&imdb=%s&tvdb=%s&query=5)' % (sysaddon, systitle, imdb, tvdb)))
				except: pass
				cm.append((findSimilarMenu, 'Container.Update(%s?action=tvshows&url=%s)' % (sysaddon, quote_plus('https://api.trakt.tv/shows/%s/related?limit=20&page=1,return' % imdb))))
				cm.append((playRandom, 'RunPlugin(%s?action=play_Random&rtype=season&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&art=%s)' % (sysaddon, systitle, year, imdb, tmdb, tvdb, sysart)))
				# cm.append((queueMenu, 'RunPlugin(%s?action=playlist_QueueItem&name=%s)' % (sysaddon, systitle)))
				# cm.append((showPlaylistMenu, 'RunPlugin(%s?action=playlist_Show)' % sysaddon))
				# cm.append((clearPlaylistMenu, 'RunPlugin(%s?action=playlist_Clear)' % sysaddon))
				cm.append((addToLibrary, 'RunPlugin(%s?action=library_tvshowToLibrary&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s)' % (sysaddon, systitle, year, imdb, tmdb, tvdb)))
				if favoriteItems:
					if tmdb in favoriteItems:
						cm.append((removeFromFavourites, 'RunPlugin(%s?action=remove_favorite&meta=%s&content=%s)' % (sysaddon, sysmeta, 'tvshows')))
					else:
						cm.append((addToFavourites, 'RunPlugin(%s?action=add_favorite&meta=%s&content=%s)' % (sysaddon, sysmeta, 'tvshows')))
				else:
					cm.append((addToFavourites, 'RunPlugin(%s?action=add_favorite&meta=%s&content=%s)' % (sysaddon, sysmeta, 'tvshows')))
				if not is_widget and page > 2:
					cm.append((getLS(40477), 'RunPlugin(%s?action=return_home&folder=%s)' % (sysaddon, 'tvshows')))
				cm.append(('[COLOR red]Umbrella Settings[/COLOR]', 'RunPlugin(%s?action=tools_openSettings)' % sysaddon))
####################################
				if trailer: meta.update({'trailer': trailer}) # removed temp so it's not passed to CM items, only skin
				else: meta.update({'trailer': '%s?action=play_Trailer&type=%s&name=%s&year=%s&imdb=%s' % (sysaddon, 'show', systitle, year, imdb)})
				item = control.item(label=label, offscreen=True)
				#if 'castandart' in i: item.setCast(i['castandart'])
				if 'castandart' in i: meta.update({"cast": ['castandart']}) #changed for kodi20 setinfo method
				item.setArt(art)
				try: 
					count = getShowCount(indicators[1], imdb, tvdb) if indicators else None # if indicators and no matching imdb_id in watched items then it returns None and we use TMDb meta to avoid Trakt request
					if self.showCounts:
						if count:
							if int(count['watched']) > 0 and (str(count['watched']) != str(count['total'])): #watched but not 100%
								item.setProperties({'WatchedEpisodes': str(count['watched']), 'UnWatchedEpisodes': str(count['unwatched'])})
								item.setProperty('WatchedProgress', str(int(float(count['watched']) / float(count['total']) * 100)))
							elif int(count['watched']) > 0 and (str(count['watched']) == str(count['total'])): #watched 100%
								item.setProperties({'WatchedEpisodes': str(count['watched']), 'UnWatchedEpisodes': str(count['unwatched'])})
								item.setProperty('WatchedProgress', str(int(float(count['watched']) / float(count['total']) * 100)))
							else:
								item.setProperties({'UnWatchedEpisodes': str(count['unwatched'])})
								item.setProperty('WatchedProgress', str(0))
							item.setProperties({'TotalSeasons': str(meta.get('total_seasons', '')), 'TotalEpisodes': str(count['total'])})
							
						else:
							if control.getKodiVersion() >= 20:
								item.setProperties({'UnWatchedEpisodes': ''}) # for shows never watched
								pass #do not set watched status on shows that have nothing watched.
							else:
								item.setProperties({'WatchedEpisodes': '0', 'UnWatchedEpisodes': str(meta.get('total_aired_episodes', ''))}) # for shows never watched
							item.setProperties({'TotalSeasons': str(meta.get('total_seasons', '')), 'TotalEpisodes': str(meta.get('total_aired_episodes', ''))})
					else:
						if count:
							if int(count['watched']) > 0:
								item.setProperties({'WatchedEpisodes': str(count['watched']), 'UnWatchedEpisodes': str(count['unwatched'])})
							else:
								item.setProperties({'UnWatchedEpisodes': str(count['unwatched'])})
							item.setProperties({'TotalSeasons': str(meta.get('total_seasons', '')), 'TotalEpisodes': str(count['total'])})
							item.setProperty('WatchedProgress', str(int(float(count['watched']) / float(count['total']) * 100)))
						else:
							if control.getKodiVersion() >= 20:
								item.setProperties({'UnWatchedEpisodes': str(meta.get('total_aired_episodes', ''))}) # for shows never watched
							else:
								item.setProperties({'WatchedEpisodes': '0', 'UnWatchedEpisodes': str(meta.get('total_aired_episodes', ''))}) # for shows never watched
							item.setProperties({'TotalSeasons': str(meta.get('total_seasons', '')), 'TotalEpisodes': str(meta.get('total_aired_episodes', ''))})
				except: pass
				item.setProperty('tmdb_id', str(tmdb))
				if is_widget: 
					item.setProperty('isUmbrella_widget', 'true')
					if self.hide_watched_in_widget and str(xbmc.getInfoLabel("Window.Property(xmlfile)")) != 'Custom_1114_Search.xml':
						if str(meta.get('playcount')) == '1':
							continue
				if isProgress:
					#check for watched removal in progress for shows here.
					if self.watched_progress:
						pass
					else:
						if str(meta.get('playcount')) == '1':
							continue
				if isWatched:
					if str(meta.get('playcount')) != '1':
						continue
				setUniqueIDs = {'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb} #k20setinfo
				#item.setInfo(type='video', infoLabels=control.metadataClean(meta))
				control.set_info(item, meta, setUniqueIDs)
				if is_widget and control.getKodiVersion() > 19.5 and self.useFullContext != True:
					pass
				else:
					item.addContextMenuItems(cm)
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		if next:
			try:
				if not items: raise Exception()
				url = items[0]['next']
				if not url: raise Exception()
				url_params = dict(parse_qsl(urlsplit(url).query))
				if 'imdb.com' in url and 'start' in url_params:
					page = '  [I](%s)[/I]' % str(int(((int(url_params.get('start')) - 1) / int(self.page_limit)) + 1))
				else: page = '  [I](%s)[/I]' % url_params.get('page')
				nextMenu = '[COLOR skyblue]' + nextMenu + page + '[/COLOR]'
				u = urlparse(url).netloc.lower()
				if u in self.imdb_link or u in self.trakt_link:
					url = '%s?action=tvshowPage&url=%s&folderName=%s' % (sysaddon, quote_plus(url), quote_plus(folderName))
				elif u in self.tmdb_link:
					url = '%s?action=tmdbTvshowPage&url=%s&folderName=%s' % (sysaddon, quote_plus(url), quote_plus(folderName))
				elif u in self.tvmaze_link:
					url = '%s?action=tvmazeTvshowPage&url=%s&folderName=%s' % (sysaddon, quote_plus(url), quote_plus(folderName))
				elif u in self.mbdlist_list_items:
					url = '%s?action=tvshowPage&url=%s&folderName=%s' % (sysaddon, quote_plus(url), quote_plus(folderName))
				item = control.item(label=nextMenu, offscreen=True)
				icon = control.addonNext()
				item.setArt({'icon': icon, 'thumb': icon, 'poster': icon, 'banner': icon})
				item.setProperty ('SpecialSort', 'bottom')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		control.content(syshandle, 'tvshows')
		control.directory(syshandle, cacheToDisc=False) # disable cacheToDisc so unwatched counts loads fresh data counts if changes made
		views.setView('tvshows', {'skin.estuary': 55, 'skin.confluence': 500})

	def addDirectory(self, items, queue=False, folderName='Umbrella'):
		from sys import argv # some functions like ActivateWindow() throw invalid handle less this is imported here.
		control.playlist.clear()
		if not items: # with reuselanguageinvoker on an empty directory must be loaded, do not use sys.exit()
			content = ''
			control.hide()
			if self.is_widget != True: control.notification(title=32002, message=33049)
		if self.useContainerTitles: control.setContainerName(folderName)
		sysaddon, syshandle = 'plugin://plugin.video.umbrella/', int(argv[1])
		addonThumb = control.addonThumb()
		artPath = control.artPath()
		queueMenu, playRandom, addToLibrary, addToFavourites = getLS(32065), getLS(32535), getLS(32551), getLS(40463)
		likeMenu, unlikeMenu = getLS(32186), getLS(32187)
		for i in items:
			try:
				content = i.get('content', '')
				name = i['name']
				if i['image'].startswith('http'): poster = i['image']
				elif artPath: poster = control.joinPath(artPath, i['image'])
				else: poster = addonThumb
				if content == 'genres':
					icon = control.joinPath(control.genreIconPath(), i['icon']) or 'DefaultFolder.png'
					poster = control.joinPath(control.genrePosterPath(), i['image']) or addonThumb
				else:
					icon = i['icon']
					if icon.startswith('http'): pass
					elif not icon.startswith('Default'): icon = control.joinPath(artPath, icon)
				url = '%s?action=%s' % (sysaddon, i['action'])
				try: url += '&url=%s' % quote_plus(i['url'])
				except: pass
				try: url += '&folderName=%s' % quote_plus(name)
				except: pass
				cm = []
				if (i.get('list_type', '') == 'traktPulicList') and self.traktCredentials:
					liked = traktsync.fetch_liked_list(i['list_id'])
					if not liked:
						cm.append((likeMenu, 'RunPlugin(%s?action=tools_likeList&list_owner=%s&list_name=%s&list_id=%s)' % (sysaddon, quote_plus(i['list_owner']), quote_plus(i['list_name']), i['list_id'])))
					else:
						name = '[COLOR %s][Liked][/COLOR] %s' % (self.highlight_color, name)
						cm.append((unlikeMenu, 'RunPlugin(%s?action=tools_unlikeList&list_owner=%s&list_name=%s&list_id=%s)' % (sysaddon, quote_plus(i['list_owner']), quote_plus(i['list_name']), i['list_id'])))
				cm.append((playRandom, 'RunPlugin(%s?action=play_Random&rtype=show&url=%s)' % (sysaddon, quote_plus(i['url']))))
				if queue: cm.append((queueMenu, 'RunPlugin(%s?action=playlist_QueueItem)' % sysaddon))
				try:
					if getSetting('library.service.update') == 'true':
						cm.append((addToLibrary, 'RunPlugin(%s?action=library_tvshowsToLibrary&url=%s&name=%s)' % (sysaddon, quote_plus(i['context']), name)))
				except: pass
				cm.append(('[COLOR red]Umbrella Settings[/COLOR]', 'RunPlugin(%s?action=tools_openSettings)' % sysaddon))
				item = control.item(label=name, offscreen=True)
				item.setArt({'icon': icon, 'poster': poster, 'thumb': icon, 'fanart': control.addonFanart(), 'banner': poster})
				#item.setInfo(type='video', infoLabels={'plot': name}) #k20setinfo
				meta = dict({'plot': name})
				control.set_info(item, meta)
				is_widget = 'plugin' not in control.infoLabel('Container.PluginName')
				if is_widget and control.getKodiVersion() > 19.5 and self.useFullContext != True:
					pass
				else:
					item.addContextMenuItems(cm)
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		try:
			if not items: raise Exception()
			url = items[0].get('next', '')
			if url == '': raise Exception()
			url_params = dict(parse_qsl(urlsplit(url).query))
			nextMenu = getLS(32053)
			page = '  [I](%s)[/I]' % url_params.get('page')
			nextMenu = '[COLOR skyblue]' + nextMenu + page + '[/COLOR]'
			icon = control.addonNext()
			url = '%s?action=tv_PublicLists&url=%s' % (sysaddon, quote_plus(url))
			item = control.item(label=nextMenu, offscreen=True)
			item.setArt({'icon': icon, 'thumb': icon, 'poster': icon, 'banner': icon})
			item.setProperty ('SpecialSort', 'bottom')
			control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

		skin = control.skin
		if skin in ('skin.arctic.horizon', 'skin.arctic.horizon.2'): pass
		elif skin in ('skin.estuary', 'skin.aeon.nox.silvo','skin.pellucid'): content = ''
		elif skin == 'skin.auramod':
			if content not in ('actors', 'genres'): content = 'addons'
			else: content = ''
		control.content(syshandle, content) # some skins use their own thumb for things like "genres" when content type is set here
		control.directory(syshandle, cacheToDisc=True)
