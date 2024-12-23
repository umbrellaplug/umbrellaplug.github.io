# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from datetime import datetime, timedelta
import time
import calendar
from json import dumps as jsdumps, loads as jsloads
import re
import xbmc
from threading import Thread
from urllib.parse import quote_plus, urlencode, parse_qsl, urlparse, urlsplit
from resources.lib.database import cache, metacache, fanarttv_cache, traktsync
from resources.lib.indexers.tmdb import Movies as tmdb_indexer
from resources.lib.indexers.fanarttv import FanartTv
from resources.lib.modules.simkl import SIMKL as simkl
from resources.lib.modules import cleangenre
from resources.lib.modules import client
from resources.lib.modules import control
from resources.lib.modules.playcount import getMovieIndicators, getMovieOverlay
from resources.lib.modules import tools, log_utils
from resources.lib.modules import trakt
from resources.lib.modules import views
from resources.lib.modules import mdblist
from sqlite3 import dbapi2 as database
from json import loads as jsloads
from operator import itemgetter
import random

getLS = control.lang
getSetting = control.setting
LOGINFO = log_utils.LOGINFO
homeWindow = control.homeWindow

class Movies:
	def __init__(self, notifications=True):
		self.list = []
		self.page_limit = getSetting('page.item.limit')
		self.genre_limit = getSetting('limit.imdb.genres')
		self.search_page_limit = getSetting('search.page.limit')
		self.notifications = notifications
		self.date_time = datetime.now()
		res = calendar.monthrange(datetime.now().year, datetime.now().month)
		self.first_day_of_month = datetime.now().replace(day=1)	
		self.last_day_of_month = res[1]
		self.today_date = (self.date_time).strftime('%Y-%m-%d')
		self.yesterday_date = datetime.now() - timedelta(days=1)
		self.hidecinema = getSetting('hidecinema') == 'true'
		self.trakt_user = getSetting('trakt.user.name').strip()
		self.traktCredentials = trakt.getTraktCredentialsInfo()
		self.lang = control.apiLanguage()['trakt']
		self.imdb_user = getSetting('imdbuser').replace('ur', '')
		self.tmdb_key = getSetting('tmdb.apikey')
		if not self.tmdb_key: self.tmdb_key = 'edde6b5e41246ab79a2697cd125e1781'
		self.tmdb_session_id = getSetting('tmdb.sessionid')
		# self.user = str(self.imdb_user) + str(self.tmdb_key)
		self.user = str(self.tmdb_key)
		self.enable_fanarttv = getSetting('enable.fanarttv') == 'true'
		self.prefer_tmdbArt = getSetting('prefer.tmdbArt') == 'true'
		self.unairedcolor = getSetting('movie.unaired.identify')
		self.useContainerTitles = getSetting('enable.containerTitles') == 'true'
		self.highlight_color = getSetting('highlight.color')
		use_tmdb = getSetting('tmdb.baseaddress') == 'true'
		if use_tmdb:
			tmdb_base = "https://api.tmdb.org"
			self.tmdb_link = 'https://api.tmdb.org'
		else:
			tmdb_base = "https://api.themoviedb.org"
			self.tmdb_link = 'https://api.themoviedb.org'
		
		self.tmdb_popular_link = tmdb_base+'/3/movie/popular?api_key=%s&language=en-US&region=US&page=1'
		self.tmdb_toprated_link = tmdb_base+'/3/movie/top_rated?api_key=%s&page=1'
		self.tmdb_upcoming_link = tmdb_base+'/3/discover/movie?api_key=%s&language=en-US&region=US&primary_release_date.gte=%s&with_release_type=3|2|1&sort_by=popularity.desc&page=1' % ('%s', (self.date_time + timedelta(days=1)).strftime('%Y-%m-%d'))
		self.tmdb_nowplaying_link = tmdb_base+'/3/movie/now_playing?api_key=%s&language=en-US&region=US&page=1'
		self.tmdb_boxoffice_link = tmdb_base+'/3/discover/movie?api_key=%s&language=en-US&region=US&sort_by=revenue.desc&page=1'
		self.tmdb_userlists_link = tmdb_base+'/3/account/{account_id}/lists?api_key=%s&language=en-US&session_id=%s&page=1' % ('%s', self.tmdb_session_id) # used by library import only
		self.tmdb_genre_link = tmdb_base+'/3/discover/movie?api_key=%s&language=en-US&region=US&primary_release_date.lte=%s&with_genres=%s&sort_by=%s&page=1' % ('%s', self.today_date, '%s', self.tmdb_DiscoverSort())
		self.tmdb_year_link = tmdb_base+'/3/discover/movie?api_key=%s&language=en-US&region=US&primary_release_date.lte=%s&certification_country=US&primary_release_year=%s&sort_by=%s&page=1' % ('%s', self.today_date, '%s', self.tmdb_DiscoverSort())
		self.tmdb_certification_link = tmdb_base+'/3/discover/movie?api_key=%s&language=en-US&region=US&primary_release_date.lte=%s&certification_country=US&certification=%s&sort_by=%s&page=1' % ('%s', self.today_date, '%s', self.tmdb_DiscoverSort())
		self.tmdb_recommendations = tmdb_base+'/3/movie/%s/recommendations?api_key=%s&language=en-US&region=US&page=1'
		self.tmdb_similar = tmdb_base+'/3/movie/%s/similar?api_key=%s&language=en-US&region=US&page=1'
		self.tmdb_discovery_this_month_link = tmdb_base+'/3/discover/movie?api_key=%s&language=en-US&region=US&release_date.gte=%s&release_date.lte=%s&with_release_type=2|3&page=1'% ('%s', self.first_day_of_month.strftime('%Y-%m-%d'), datetime.now().replace(day=self.last_day_of_month).strftime('%Y-%m-%d'))
		self.tmdb_discovery_this_month_released_link = tmdb_base+'/3/discover/movie?api_key=%s&language=en-US&region=US&release_date.gte=%s&release_date.lte=%s&with_release_type=4|5&page=1'% ('%s', self.first_day_of_month.strftime('%Y-%m-%d'), datetime.now().replace(day=self.last_day_of_month).strftime('%Y-%m-%d'))
		self.tmdb_discovery_released_link = tmdb_base+'/3/discover/movie?api_key=%s&language=en-US&region=US&release_date.gte=%s&release_date.lte=%s&with_release_type=2|3&page=1'% ('%s', (self.yesterday_date-timedelta(days=30)).strftime('%Y-%m-%d'), self.yesterday_date.strftime('%Y-%m-%d'))
		self.tmdb_recentday = tmdb_base+'/3/trending/movie/day?api_key=%s&language=en-US&region=US&page=1'
		self.tmdb_recentweek = tmdb_base+'/3/trending/movie/week?api_key=%s&language=en-US&region=US&page=1'
		self.search_tmdb_link = tmdb_base+'/3/search/movie?api_key=%s&language=en-US&query=%s&region=US&page=1'% ('%s','%s')
		self.tmdb_person_search = tmdb_base+'/3/search/person?api_key=%s&query=%s&language=en-US&page=1&include_adult=true' % ('%s','%s')

		self.imdb_link = 'https://www.imdb.com'
		self.persons_link = 'https://www.imdb.com/search/name/?count=100&name='
		self.personlist_link = 'https://www.imdb.com/search/name/?count=100&gender=male,female'
		self.person_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&production_status=released&role=%s&sort=year,desc&count=%s&start=1' % ('%s', self.genre_limit)
		self.keyword_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie,documentary&num_votes=100,&keywords=%s&sort=%s&count=%s&start=1' % ('%s', self.imdb_sort(), self.genre_limit)
		self.oscars_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&production_status=released&groups=oscar_best_picture_winners&sort=year,desc&count=%s&start=1' % self.genre_limit
		self.oscarsnominees_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&production_status=released&groups=oscar_best_picture_nominees&sort=year,desc&count=%s&start=1' % self.genre_limit
		self.theaters_link = 'https://www.imdb.com/search/title/?title_type=feature&num_votes=500,&release_date=date[90],date[0]&languages=en&sort=release_date,desc&count=%s&start=1' % self.genre_limit
		self.imdb_comingsoon_link = 'https://www.imdb.com/calendar/?ref_=rlm&region=US&type=MOVIE'
		self.year_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&num_votes=100,&production_status=released&year=%s,%s&sort=moviemeter,asc&count=%s&start=1' % ('%s', '%s', self.genre_limit)
		if self.hidecinema:
			hidecinema_rollback = str(int(getSetting('hidecinema.rollback')) * 30)
			self.mostpopular_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&num_votes=1000,&production_status=released&groups=top_1000&release_date=,date[%s]&sort=moviemeter,asc&count=%s&start=1' % (hidecinema_rollback, self.genre_limit )
			self.mostvoted_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&num_votes=1000,&production_status=released&release_date=,date[%s]&sort=num_votes,desc&count=%s&start=1' % (hidecinema_rollback, self.genre_limit )
			self.featured_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&num_votes=1000,&production_status=released&release_date=,date[%s]&sort=moviemeter,asc&count=%s&start=1' % (hidecinema_rollback, self.genre_limit )
			self.genre_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie,documentary&num_votes=3000,&release_date=,date[%s]&genres=%s&sort=%s&count=%s&start=1' % (hidecinema_rollback, '%s', self.imdb_sort(type='imdbmovies'), self.genre_limit)
			self.language_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&num_votes=100,&production_status=released&primary_language=%s&release_date=,date[%s]&sort=%s&count=%s&start=1' % ('%s', hidecinema_rollback, self.imdb_sort(type='imdbmovies'), self.genre_limit)
			self.certification_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&num_votes=100,&production_status=released&certificates=%s&release_date=,date[%s]&sort=%s&count=%s&start=1' % ('%s', hidecinema_rollback, self.imdb_sort(type='imdbmovies'), self.genre_limit)
			self.imdbboxoffice_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&production_status=released&sort=boxoffice_gross_us,desc&release_date=,date[%s]&count=%s&start=1' % (hidecinema_rollback, self.genre_limit)
		else:
			self.mostpopular_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&num_votes=1000,&production_status=released&groups=top_1000&sort=moviemeter,asc&count=%s&start=1' % self.genre_limit
			self.mostvoted_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&num_votes=1000,&production_status=released&sort=num_votes,desc&count=%s&start=1' % self.genre_limit
			self.featured_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&num_votes=1000,&production_status=released&sort=moviemeter,asc&count=%s&start=1' % self.genre_limit
			self.genre_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&num_votes=3000,&release_date=,date[0]&genres=%s&sort=%s&count=%s&start=1' % ('%s', self.imdb_sort(type='imdbmovies'), self.genre_limit)
			self.language_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&num_votes=100,&production_status=released&primary_language=%s&sort=%s&count=%s&start=1' % ('%s', self.imdb_sort(type='imdbmovies'), self.genre_limit)
			self.certification_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&num_votes=100,&production_status=released&certificates=%s&sort=%s&count=%s&start=1' % ('%s', self.imdb_sort(type='imdbmovies'), self.genre_limit)
			self.imdbboxoffice_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&production_status=released&sort=boxoffice_gross_us,desc&count=%s&start=1' % self.genre_limit
		self.imdbwatchlist_link = 'https://www.imdb.com/user/ur%s/watchlist/?sort=date_added,desc&title_type=feature' % self.imdb_user # only used to get users watchlist ID
		self.imdbwatchlist2_link = 'https://www.imdb.com/list/%s/?view=detail&sort=%s&title_type=movie&start=1' % ('%s', self.imdb_sort(type='movies.watchlist'))
		self.imdblists_link = 'https://www.imdb.com/user/ur%s/lists?tab=all&sort=mdfd&order=desc&filter=titles' % self.imdb_user
		self.imdblist_link = 'https://www.imdb.com/list/%s/?view=detail&sort=%s&title_type=movie,short,video,tvShort,tvMovie,tvSpecial&start=1' % ('%s', self.imdb_sort())
		self.imdbratings_link = 'https://www.imdb.com/user/ur%s/ratings?sort=your_rating,desc&mode=detail&start=1' % self.imdb_user # IMDb ratings does not take title_type so filter is in imdb_list() function
		self.anime_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&keywords=anime-animation,anime'


		self.trakt_link = 'https://api.trakt.tv'
		self.search_link = 'https://api.trakt.tv/search/movie?limit=%s&page=1&query=' % self.search_page_limit
		self.traktlistsearch_link = 'https://api.trakt.tv/search/list?limit=%s&page=1&query=' % self.page_limit
		self.traktlists_link = 'https://api.trakt.tv/users/me/lists'
		self.traktlikedlists_link = 'https://api.trakt.tv/users/likes/lists?limit=1000000' # used by library import only
		self.traktwatchlist_link = 'https://api.trakt.tv/users/me/watchlist/movies?limit=%s&page=1' % self.page_limit # this is now a dummy link for pagination to work
		self.traktcollection_link = 'https://api.trakt.tv/users/me/collection/movies?limit=%s&page=1' % self.page_limit # this is now a dummy link for pagination to work
		self.trakthistory_link = 'https://api.trakt.tv/users/me/history/movies?limit=%s&page=1' % self.page_limit
		self.traktlist_link = 'https://api.trakt.tv/users/%s/lists/%s/items/movies?limit=%s&page=1' % ('%s', '%s', self.page_limit) # local pagination, limit and page used to advance, pulled from request
		self.traktunfinished_link = 'https://api.trakt.tv/sync/playback/movies?limit=40'
		self.traktanticipated_link = 'https://api.trakt.tv/movies/anticipated?limit=%s&page=1' % self.page_limit
		if datetime.today().month > 6:
			traktyears='years='+str(datetime.today().year)
		else:
			traktyears='years='+str(int(datetime.today().year-1))+'-'+str(datetime.today().year)
		if getSetting('trakt.useLanguage') == 'true':
			self.trakttrending_link = 'https://api.trakt.tv/movies/trending?limit=%s&page=1&languages=%s' % (self.page_limit,self.lang)
			self.traktmostplayed_link = 'https://api.trakt.tv/movies/played/weekly?limit=%s&page=1&languages=%s' % (self.page_limit,self.lang)
			self.traktmostwatched_link = 'https://api.trakt.tv/movies/watched/weekly?limit=%s&page=1&languages=%s' % (self.page_limit,self.lang)
			self.trakttrending_recent_link = 'https://api.trakt.tv/movies/trending?limit=%s&page=1&%s' % (self.page_limit, traktyears)
			self.traktboxoffice_link = 'https://api.trakt.tv/movies/boxoffice?languages=%s' % self.lang # Returns the top 10 grossing movies in the U.S. box office last weekend
			self.traktpopular_link = 'https://api.trakt.tv/movies/popular?limit=%s&page=1&languages=%s' % (self.page_limit, self.lang)
			self.traktrecommendations_link = 'https://api.trakt.tv/recommendations/movies?limit=40&languages=%s' % self.lang
			self.trakt_similiar = 'https://api.trakt.tv/movies/%s/related?limit=%s&page=1&languages=%s' % ('%s', self.page_limit, self.lang)
		else:
			self.trakttrending_link = 'https://api.trakt.tv/movies/trending?limit=%s&page=1' % self.page_limit
			self.traktmostplayed_link = 'https://api.trakt.tv/movies/played/weekly?limit=%s&page=1' % self.page_limit
			self.traktmostwatched_link = 'https://api.trakt.tv/movies/watched/weekly?limit=%s&page=1' % self.page_limit
			self.trakttrending_recent_link = 'https://api.trakt.tv/movies/trending?limit=%s&page=1&%s' % (self.page_limit, traktyears)
			self.traktboxoffice_link = 'https://api.trakt.tv/movies/boxoffice' # Returns the top 10 grossing movies in the U.S. box office last weekend
			self.traktpopular_link = 'https://api.trakt.tv/movies/popular?limit=%s&page=1' % self.page_limit
			self.traktrecommendations_link = 'https://api.trakt.tv/recommendations/movies?limit=40'
			self.trakt_similiar = 'https://api.trakt.tv/movies/%s/related?limit=%s&page=1' % ('%s', self.page_limit)
		self.trakt_genres = 'https://api.trakt.tv/genres/movies/'
		self.trakt_popularLists_link = 'https://api.trakt.tv/lists/popular?limit=%s&page=1' % self.page_limit
		self.trakt_trendingLists_link = 'https://api.trakt.tv/lists/trending?limit=%s&page=1' % self.page_limit
		self.mbdlist_list_items = 'https://mdblist.com/api/lists/%s/items?apikey=%s&page=1' % ('%s', mdblist.mdblist_api)
		self.simkltrendingtoday_link = 'https://api.simkl.com/movies/trending/today?client_id=%s&extended=tmdb' % '%s'
		self.simkltrendingweek_link = 'https://api.simkl.com/movies/trending/week?client_id=%s&extended=tmdb' % '%s'
		self.simkltrendingmonth_link = 'https://api.simkl.com/movies/trending/month?client_id=%s&extended=tmdb'% '%s'
		self.imdblist_hours = int(getSetting('cache.imdblist'))
		self.trakt_hours = int(getSetting('cache.traktother'))
		self.traktpopular_hours = int(getSetting('cache.traktpopular'))
		self.trakttrending_hours = int(getSetting('cache.trakttrending'))
		self.traktuserlist_hours = int(getSetting('cache.traktuserlist'))
		self.tmdbrecentday_hours = int(getSetting('cache.tmdbrecentday'))
		self.tmdbrecentweek_hours = int(getSetting('cache.tmdbrecentweek'))
		self.simkl_hours = int(getSetting('cache.simkl'))
		self.mdblist_hours = int(getSetting('cache.mdblist'))
		self.showwatchedlib = getSetting('showwatchedlib')
		self.hide_watched_in_widget = getSetting('enable.umbrellahidewatched') == 'true'
		self.useFullContext = getSetting('enable.umbrellawidgetcontext') == 'true'
		self.useContainerTitles = getSetting('enable.containerTitles') == 'true'
		self.useReleaseYear = getSetting('movies.showyear') == 'true'
		self.lang = control.apiLanguage()['trakt']

	def get(self, url, idx=True, create_directory=True, folderName=''):
		self.list = []
		try:
			try: url = getattr(self, url + '_link')
			except: pass
			try: u = urlparse(url).netloc.lower()
			except: pass
			if url == 'favourites_movies':
				return self.favouriteMovies(folderName=folderName)
			elif url == 'traktbasedonrecent':
				return self.trakt_based_on_recent(folderName=folderName)
			elif url == 'traktbasedonsimilar':
				return self.trakt_based_on_similar(folderName=folderName)
			elif url == 'tmdbrecentday':
				return self.tmdb_trending_recentday(folderName=folderName)
			elif url == 'tmdbrecentweek':
				return self.tmdb_trending_recentweek(folderName=folderName)
			elif u in self.search_tmdb_link and url != 'tmdbrecentday' and url != 'tmdbrecentweek' and url != 'favourites_movies':
				return self.getTMDb(url, folderName=folderName)
			elif u in self.simkltrendingweek_link or u in self.simkltrendingmonth_link or u in self.simkltrendingtoday_link:
				return self.getSimkl(url, folderName=folderName)
			elif u in self.trakt_link and '/users/' in url:
				try:
					isTraktHistory = (url.split('&page=')[0] in self.trakthistory_link)
					if '/users/me/' not in url: raise Exception()
					if '/collection/' in url: return self.traktCollection(url, folderName=folderName)
					if '/watchlist/' in url: return self.traktWatchlist(url, folderName=folderName)
					if trakt.getActivity() > cache.timeout(self.trakt_list, url, self.trakt_user, folderName):
						self.list = cache.get(self.trakt_list, 0, url, self.trakt_user, folderName)
					else: self.list = cache.get(self.trakt_list, 720, url, self.trakt_user, folderName)
				except:
					self.list = self.trakt_userList(url, create_directory=False)
				if isTraktHistory and self.list:
					for i in range(len(self.list)): self.list[i]['traktHistory'] = True
				if idx: self.worker()
				if not isTraktHistory: self.sort()
			elif u in self.trakt_link and self.search_link in url:
				self.list = cache.get(self.trakt_list, 6, url, self.trakt_user, folderName)
				if idx: self.worker()
			elif u in self.trakt_link and 'trending' in url:
				self.list = cache.get(self.trakt_list,self.trakttrending_hours, url, self.trakt_user, folderName) #trakt trending
				if idx: self.worker()
			elif u in self.trakt_link:
				self.list = cache.get(self.trakt_list,self.trakt_hours, url, self.trakt_user, folderName) #trakt other
				if idx: self.worker()
			elif u in self.imdb_link and ('/user/' in url or '/list/' in url):
				isRatinglink = True if self.imdbratings_link in url else False
				self.list = cache.get(self.imdb_list, 0, url, isRatinglink, folderName)
				if idx: self.worker()
				# self.sort() # switched to request sorting for imdb
			elif u in self.imdb_link:
				if 'genres' in url:
					self.list = cache.get(self.imdb_genre_list, self.imdblist_hours, url, folderName)
				elif 'calendar' in url:
					self.list = cache.get(self.imdb_list, self.imdblist_hours, url, True, folderName)
				else: self.list = cache.get(self.imdb_genre_list, self.imdblist_hours, url, folderName)
				if idx: self.worker()
			elif u in self.mbdlist_list_items:
				self.list = self.mdb_list_items(url, create_directory=False)
				if idx: self.worker()
			if self.list is None: self.list = []
			if idx and create_directory: self.movieDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				is_widget = 'plugin' not in control.infoLabel('Container.PluginName')
				if self.notifications and is_widget != True:
					control.notification(title=32001, message=33049)

	def getTMDb(self, url, create_directory=True, folderName=''):
		self.list = []
		try:
			try: url = getattr(self, url + '_link')
			except: pass
			try: u = urlparse(url).netloc.lower()
			except: pass
			if u in self.tmdb_link and '/list/' in url:
				self.list = tmdb_indexer().tmdb_collections_list(url) # caching handled in list indexer
				self.sort()
			elif u in self.tmdb_link and '/list/' not in url:
				self.list = tmdb_indexer().tmdb_list(url) # caching handled in list indexer
			if self.list is None: self.list = []
			if create_directory: self.movieDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				is_widget = 'plugin' not in control.infoLabel('Container.PluginName')
				if self.notifications and is_widget != True: 
					control.notification(title=32001, message=33049)
	
	def getMBDTopLists(self, create_directory=True, folderName=''): 
		self.list = []
		try:

			self.list = cache.get(self.mbd_top_lists, self.mdblist_hours)
			if self.list is None: self.list = []
			if create_directory: self.addDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
	def mbd_top_lists(self):
		try:
			listType = 'movie'
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
				label = '%s - (%s)' % (list_name, list_count)
				self.list.append({'name': label, 'url': list_url, 'list_owner': list_owner, 'list_name': list_name, 'list_id': list_id, 'context': list_url, 'next': next, 'image': 'mdblist.png', 'icon': 'mdblist.png', 'action': 'movies&folderName=%s' % quote_plus(list_name)})
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		return self.list
	def getMDBUserList(self, create_directory=True, folderName=''): 
		self.list = []
		try:
			self.list = cache.get(self.mbd_user_lists, self.mdblist_hours)
			if self.list is None: self.list = []
			return self.addDirectory(self.list, folderName=folderName)

		except:
			from resources.lib.modules import log_utils
			log_utils.error()
	def mbd_user_lists(self):
		try:
			listType = 'movie'
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
				self.list.append({'name': label, 'url': list_url, 'list_owner': list_owner, 'list_name': list_name, 'list_id': list_id, 'context': list_url, 'next': next, 'image': 'mdblist.png', 'icon': 'mdblist.png', 'action': 'movies&folderName=%s' % quote_plus(list_name)})
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		return self.list
	def getTraktPublicLists(self, url, create_directory=True, folderName=''):
		self.list = []
		try:
			try: url = getattr(self, url + '_link')
			except: pass
			if '/popular' in url:
				self.list = cache.get(self.trakt_public_list, self.traktpopular_hours, url)
			elif '/trending' in url:
				self.list = cache.get(self.trakt_public_list, self.trakttrending_hours, url)
			else:
				self.list = cache.get(self.trakt_public_list, self.trakt_hours, url)
			if self.list is None: self.list = []
			if create_directory: self.addDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def mdb_list_items(self, url, create_directory=True, folderName=''):
		self.list = []
		q = dict(parse_qsl(urlsplit(url).query))
		index = int(q['page']) - 1
		def mbdList_totalItems(url):
			items = mdblist.getMDBItems(url)
			if not items: return
			for item in items:
				try:
					values = {}
					values['title'] = item.get('title', '')
					values['originaltitle'] = item.get('title', '')
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
		self.list = mbdList_totalItems(url)
		if not self.list: return
		self.sort() # sort before local pagination
		total_pages = 1
		if len(self.list) == int(self.page_limit):
			useNext = False
		else:
			useNext = True
		paginated_ids = [self.list[x:x + int(self.page_limit)] for x in range(0, len(self.list), int(self.page_limit))]
		total_pages = len(paginated_ids)
		self.list = paginated_ids[index]
		try:
			if useNext == False: raise Exception()
			if int(self.page_limit) != len(self.list): raise Exception()
			if int(q['page']) == total_pages: raise Exception()
			q.update({'page': str(int(q['page']) + 1)})
			q = (urlencode(q)).replace('%2C', ',')
			next = url.replace('?' + urlparse(url).query, '') + '?' + q
			next = next + '&folderName=%s' % quote_plus(folderName)
		except: next = ''
		for i in range(len(self.list)): self.list[i]['next'] = next
		self.worker()
		if self.list is None: self.list = []
		if create_directory: self.movieDirectory(self.list, folderName=folderName)
		return self.list

	def favouriteMovies(self, create_directory=True, folderName=''):
		self.list = []
		try:
			from resources.lib.modules import favourites
			results = favourites.getFavourites('movies')
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
			if self.list is None: self.list = []
			self.sort(type="movies.favourites")
			if create_directory: self.movieDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return []

	def trakt_based_on_recent(self, create_directory=True, folderName=''):
		self.list = []
		try:
			historyurl = 'https://api.trakt.tv/users/me/history/movies?limit=20&page=1'
			randomItems = self.trakt_list(historyurl, self.trakt_user, folderName)
			if not randomItems: return
			item = randomItems[random.randint(0, len(randomItems) - 1)]
			url = self.tmdb_recommendations % (item.get('tmdb'), '%s')
			self.list = tmdb_indexer().tmdb_list(url)
			try: 
				folderName = quote_plus(getLS(40257)+' '+item.get('title'))
				control.setHomeWindowProperty('umbrella.movierecent', str(getLS(40257)+' '+item.get('title')))
			except: pass
			next = ''
			for i in range(len(self.list)): self.list[i]['next'] = next
			self.worker()
			if self.list is None: self.list = []
			if create_directory: self.movieDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return

	def trakt_based_on_similar(self, create_directory=True, folderName=''):
		self.list = []
		try:
			historyurl = 'https://api.trakt.tv/users/me/history/movies?limit=20&page=1'
			randomItems = self.trakt_list(historyurl, self.trakt_user, folderName)
			if not randomItems: return
			item = randomItems[random.randint(0, len(randomItems) - 1)]
			url = self.tmdb_similar % (item.get('tmdb'), '%s')
			self.list = tmdb_indexer().tmdb_list(url)
			try: 
				folderName = quote_plus(getLS(40259)+' '+item.get('title'))
				control.setHomeWindowProperty('umbrella.moviesimilar', str(getLS(40259)+' '+item.get('title')))
			except: pass
			next = ''
			for i in range(len(self.list)): self.list[i]['next'] = next
			self.worker()
			if self.list is None: self.list = []
			if create_directory: self.movieDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return

	def tmdb_released_formats(self, create_directory=True, folderName=''):
		self.list = []
		try:
			url = self.tmdb_released
			self.list = tmdb_indexer().tmdb_list(url)
			next = ''
			for i in range(len(self.list)): self.list[i]['next'] = next
			self.worker()
			if self.list is None: self.list = []
			if create_directory: self.movieDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return

	def tmdb_trending_recentday(self, create_directory=True, folderName=''):
		self.list = []
		try:
			url = self.tmdb_recentday
			self.list = cache.get(tmdb_indexer().tmdb_list, self.tmdbrecentday_hours, url)
			next = ''
			for i in range(len(self.list)): self.list[i]['next'] = next
			self.worker()
			if self.list is None: self.list = []
			if create_directory: self.movieDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return

	def tmdb_trending_recentweek(self, create_directory=True, folderName=''):
		self.list = []
		try:
			url = self.tmdb_recentweek
			self.list = cache.get(tmdb_indexer().tmdb_list, self.tmdbrecentweek_hours, url)
			#self.list = tmdb_indexer().tmdb_list(url)
			next = ''
			for i in range(len(self.list)): self.list[i]['next'] = next
			self.worker()
			if self.list is None: self.list = []
			if create_directory: self.movieDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return

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
			if create_directory: self.movieDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			if not self.list:
				control.hide()
				is_widget = 'plugin' not in control.infoLabel('Container.PluginName')
				if self.notifications and is_widget != True: control.notification(title=32001, message=33049)

	def unfinished(self, url, idx=True, create_directory=True, folderName=''):
		self.list = []
		try:
			self.list = traktsync.fetch_bookmarks(imdb='', ret_all=True, ret_type='movies')
			if idx: self.worker()
			self.list = sorted(self.list, key=lambda k: k['paused_at'], reverse=True)
			if self.list is None: self.list = []
			if create_directory: self.movieDirectory(self.list, unfinished=True, next=False, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def unfinishedManager(self):
		try:
			control.busy()
			list = self.unfinished(url='traktunfinished', create_directory=False)
			control.hide()
			from resources.lib.windows.traktmovieprogress_manager import TraktMovieProgressManagerXML
			window = TraktMovieProgressManagerXML('traktmovieprogress_manager.xml', control.addonPath(control.addonId()), results=list)
			selected_items = window.run()
			del window
			if selected_items:
				refresh = 'plugin.video.umbrella' in control.infoLabel('Container.PluginName')
				trakt.scrobbleResetItems(imdb_ids=selected_items, refresh=refresh, widgetRefresh=True)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def collectionManager(self):
		try:
			control.busy()
			self.list = traktsync.fetch_collection('movies_collection')
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
				trakt.removeCollectionItems('movies', selected_items)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			control.hide()

	def watchlistManager(self):
		try:
			control.busy()
			self.list = traktsync.fetch_watch_list('movies_watchlist')
			self.worker()
			self.sort(type='movies.watchlist')
			# self.list = sorted(self.list, key=lambda k: re.sub(r'(^the |^a |^an )', '', k['tvshowtitle'].lower()), reverse=False)
			control.hide()
			from resources.lib.windows.traktbasic_manager import TraktBasicManagerXML
			window = TraktBasicManagerXML('traktbasic_manager.xml', control.addonPath(control.addonId()), results=self.list)
			selected_items = window.run()
			del window
			if selected_items:
				# refresh = 'plugin.video.umbrella' in control.infoLabel('Container.PluginName')
				trakt.removeWatchlistItems('movies', selected_items)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			control.hide()

	def likedListsManager(self):
		try:
			items = traktsync.fetch_liked_list('', True)
			from resources.lib.windows.traktlikedlist_manager import TraktLikedListManagerXML
			window = TraktLikedListManagerXML('traktlikedlist_manager.xml', control.addonPath(control.addonId()), results=items)
			selected_items = window.run()
			del window
			if selected_items:
				# refresh = 'plugin.video.umbrella' in control.infoLabel('Container.PluginName')
				trakt.remove_liked_lists(selected_items)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def sort(self, type='movies'):
		try:
			if not self.list: return
			attribute = int(getSetting('sort.%s.type' % type))
			reverse = int(getSetting('sort.%s.order' % type)) == 1
			if attribute == 0: reverse = False # Sorting Order is not enabled when sort method is "Default"
			if attribute > 0:
				if attribute == 1:
					try: self.list = sorted(self.list, key=lambda k: re.sub(r'(^the |^a |^an )', '', k['title'].lower()), reverse=reverse)
					except: self.list = sorted(self.list, key=lambda k: k['title'].lower(), reverse=reverse)
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
					for i in range(len(self.list)):
						if 'lastplayed' not in self.list[i]: self.list[i]['lastplayed'] = ''
					self.list = sorted(self.list, key=lambda k: k['lastplayed'], reverse=reverse)
			elif reverse:
				self.list = list(reversed(self.list))
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def imdb_sort(self, type='movies'):
		sort = int(getSetting('sort.%s.type' % type))
		imdb_sort = 'list_order' if type == 'movies.watchlist' else 'moviemeter'
		if sort == 1: imdb_sort = 'alpha'
		elif sort == 2: imdb_sort = 'user_rating'
		elif sort == 3: imdb_sort = 'num_votes'
		elif sort == 4: imdb_sort = 'release_date'
		elif sort in (5, 6): imdb_sort = 'date_added'
		imdb_sort_order = ',asc' if (int(getSetting('sort.%s.order' % type)) == 0 or sort == 0) else ',desc'
		sort_string = imdb_sort + imdb_sort_order
		return sort_string

	def tmdb_DiscoverSort(self):
		sort = int(getSetting('sort.movies.type'))
		tmdb_sort = 'popularity' # default sort=0
		if sort == 1: tmdb_sort = 'title'
		elif sort == 2: tmdb_sort = 'vote_average'
		elif sort == 3: tmdb_sort = 'vote_count'
		elif sort in (4, 5, 6): tmdb_sort = 'primary_release_date'
		tmdb_sort_order = '.asc' if (int(getSetting('sort.movies.order')) == 0) else '.desc'
		sort_string = tmdb_sort + tmdb_sort_order
		if sort == 2: sort_string = sort_string + '&vote_count.gte=500'
		return sort_string

	def search(self, folderName=''):
		from resources.lib.menus import navigator
		navigator.Navigator().addDirectoryItem(getLS(32603) % self.highlight_color, 'movieSearchnew', 'search.png', 'DefaultAddonsSearch.png', isFolder=False)
		if self.useContainerTitles: control.setContainerName(folderName)
		from sqlite3 import dbapi2 as database
		try:
			if not control.existsPath(control.dataPath): control.makeFile(control.dataPath)
			dbcon = database.connect(control.searchFile)
			dbcur = dbcon.cursor()
			dbcur.executescript('''CREATE TABLE IF NOT EXISTS movies (ID Integer PRIMARY KEY AUTOINCREMENT, term);''')
			dbcur.execute('''SELECT * FROM movies ORDER BY ID DESC''')
			dbcur.connection.commit()
			lst = []
			delete_option = False
			for (id, term) in sorted(dbcur.fetchall(), key=lambda k: re.sub(r'(^the |^a |^an )', '', k[1].lower()), reverse=False):
				if term not in str(lst):
					delete_option = True
					navigator.Navigator().addDirectoryItem(term, 'movieSearchterm&name=%s' % term, 'search.png', 'DefaultAddonsSearch.png', isSearch=True, table='movies')
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
			dbcur.execute('''INSERT INTO movies VALUES (?,?)''', (None, q))
			dbcur.connection.commit()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
		#need debugger here
		if self.traktCredentials:
			if getSetting('searchmovie.indexer')== '1':
				url = self.search_link + quote_plus(q)
			else:
				url = self.search_tmdb_link % ('%s', quote_plus(q))
		else:
			url = self.search_tmdb_link % ('%s', quote_plus(q))
		control.closeAll()
		control.execute('ActivateWindow(Videos,plugin://plugin.video.umbrella/?action=movies&url=%s,return)' % (quote_plus(url)))

	def search_term(self, name):
		if name:
			if self.traktCredentials:
				if getSetting('searchmovie.indexer')== '1':
					url = self.search_link + quote_plus(name)
				else:
					url = self.search_tmdb_link % ('%s', quote_plus(name))
			else:
				url = self.search_tmdb_link % ('%s', quote_plus(name))
			self.get(url)
		else:
			return


	def person(self):
		k = control.keyboard('', getLS(32010))
		k.doModal()
		q = k.getText().strip() if k.isConfirmed() else None
		if not q: return control.closeAll()
		#url = self.persons_link + quote_plus(q)
		url = self.tmdb_person_search % ('%s', quote_plus(q))
		control.closeAll()
		control.execute('ActivateWindow(Videos,plugin://plugin.video.umbrella/?action=moviePersons&url=%s,return)' % (quote_plus(url)))

	def persons(self, url, folderName=''):
		if url is None: self.list = cache.get(self.imdb_person_list, 24, self.personlist_link)

		else: self.list = cache.get(self.imdb_person_list, 1, url)
		if self.list is None: self.list = []
		if self.list:
			for i in range(0, len(self.list)): self.list[i].update({'content': 'actors', 'icon': 'DefaultActor.png', 'action': 'movies&folderName=%s' % quote_plus(self.list[i]['name'])})
		self.addDirectory(self.list, folderName=folderName)
		return self.list

	def persons_tmdb(self, url, folderName=''):
		if url is None: return None
		from resources.lib.indexers import tmdb
		self.list = tmdb.Movies().actorSearch(url)
		if self.list:
			for i in range(0, len(self.list)): self.list[i].update({'content': 'actors', 'icon': 'DefaultActor.png', 'action': 'movies&folderName=%s' % quote_plus(self.list[i]['name'])})
		self.addDirectory(self.list, folderName=folderName)
		return self.list

	def genres(self, url, folderName=''):
		try: url = getattr(self, url + '_link')
		except: pass
		genres = [
			('Action', 'action', True, '28'), ('Adventure', 'adventure', True, '12'), ('Animation', 'animation', True, '16'),
			('Biography', 'biography', True), ('Comedy', 'comedy', True, '35'), ('Crime', 'crime', True, '80'),
			('Documentary', 'documentary', True, '99'), ('Drama', 'drama', True, '18'), ('Family', 'family', True, '10751'),
			('Fantasy', 'fantasy', True, '14'), ('Film-Noir', 'film-noir', True), ('History', 'history', True, '36'),
			('Horror', 'horror', True, '27'), ('Music', 'music', True, '10402'), ('Musical', 'musical', True),
			('Mystery', 'mystery', True, '9648'), ('Romance', 'romance', True, '10749'), ('Science Fiction', 'sci-fi', True, '878'),
			('Sport', 'sport', True), ('Thriller', 'thriller', True, '53'), ('War', 'war', True, '10752'), ('Western', 'western', True, '37')]
		if 'trakt_movie_genre' in url:
				titems = trakt.getTraktAsJson(self.trakt_genres)
				for l in titems:
					if l.get('name') != 'None':
						self.list.append({'content': 'genres', 'name': l.get('name'), 'url':l.get('slug'), 'image': l.get('name') + '.jpg', 'icon': l.get('name') + '.png', 'action': 'trakt_movie_genre&mediatype=Movies&genre=%s&folderName=%s' % (l.get('name'),cleangenre.lang(l.get('name'), self.lang))})
		else:
			for i in genres:
				if self.imdb_link in url:
					for j in re.findall(r'date\[(\d+)\]', url):
						url = url.replace('date[%s]' % j, (self.date_time - timedelta(days=int(j))).strftime('%Y-%m-%d'))
					self.list.append({'content': 'genres', 'name': cleangenre.lang(i[0], self.lang), 'url': url % i[1] if i[2] else self.keyword_link % i[1], 'image': i[0] + '.jpg', 'icon': i[0] + '.png', 'action': 'movies&folderName=%s' % cleangenre.lang(i[0], self.lang)})
				if self.tmdb_link in url:
					try: self.list.append({'content': 'genres', 'name': cleangenre.lang(i[0], self.lang), 'url': url % ('%s', i[3]), 'image': i[0] + '.jpg', 'icon': i[0] + '.png', 'action': 'tmdbmovies&folderName=%s' % cleangenre.lang(i[0], self.lang)})
					except: pass
		self.addDirectory(self.list, folderName=folderName)
		return self.list

	def languages(self, folderName=''):
		languages = [('Arabic', 'ar'), ('Bosnian', 'bs'), ('Bulgarian', 'bg'), ('Chinese', 'zh'), ('Croatian', 'hr'), ('Dutch', 'nl'),
			('English', 'en'), ('Finnish', 'fi'), ('French', 'fr'), ('German', 'de'), ('Greek', 'el'),('Hebrew', 'he'), ('Hindi ', 'hi'),
			('Hungarian', 'hu'), ('Icelandic', 'is'), ('Italian', 'it'), ('Japanese', 'ja'), ('Korean', 'ko'), ('Macedonian', 'mk'),
			('Norwegian', 'no'), ('Persian', 'fa'), ('Polish', 'pl'), ('Portuguese', 'pt'), ('Punjabi', 'pa'), ('Romanian', 'ro'),
			('Russian', 'ru'), ('Serbian', 'sr'), ('Slovenian', 'sl'), ('Spanish', 'es'), ('Swedish', 'sv'), ('Turkish', 'tr'), ('Ukrainian', 'uk')]
		for i in languages:
			self.list.append({'content': 'countries', 'name': str(i[0]), 'url': self.language_link % i[1], 'image': 'languages.png', 'icon': 'DefaultAddonLanguage.png', 'action': 'movies&folderName=%s' % quote_plus(str(i[0]))})
		self.addDirectory(self.list, folderName=folderName)
		return self.list

	def certifications(self, url, folderName=''):
		try: url = getattr(self, url + '_link')
		except: pass
		certificates = [
			('General Audience (G)', 'US%3AG', 'G'),
			('Parental Guidance (PG)', 'US%3APG', 'PG'),
			('Parental Caution (PG-13)', 'US%3APG-13', 'PG-13'),
			('Parental Restriction (R)', 'US%3AR', 'R'),
			('Mature Audience (NC-17)', 'US%3ANC-17', 'NC-17')]
		for i in certificates:
			if self.imdb_link in url: self.list.append({'content': 'tags', 'name': str(i[0]), 'url': url % i[1], 'image': 'certificates.png', 'icon': 'certificates.png', 'action': 'movies&folderName=%s' % quote_plus(str(i[0]))})
			if self.tmdb_link in url: self.list.append({'content': 'tags', 'name': str(i[0]), 'url': url % ('%s', i[2]), 'image': 'certificates.png', 'icon': 'certificates.png', 'action': 'tmdbmovies&folderName=%s' % quote_plus(str(i[0]))})
		self.addDirectory(self.list, folderName=folderName)
		return self.list

	def years(self, url, folderName=''):
		try: url = getattr(self, url + '_link')
		except: pass
		year = (self.date_time.strftime('%Y'))
		for i in range(int(year)-0, 1900, -1):
			if url == 'traktyears':
				self.list.append({'content': 'years', 'name': str(i), 'url': url % (str(i), str(i)), 'image': 'years.png', 'icon': 'DefaultYear.png', 'action': 'traktYear&folderName=%s'% quote_plus(str(i))})
			if self.imdb_link in url: self.list.append({'content': 'years', 'name': str(i), 'url': url % (str(i), str(i)), 'image': 'years.png', 'icon': 'DefaultYear.png', 'action': 'movies&folderName=%s'% quote_plus(str(i))})
			if self.tmdb_link in url: self.list.append({'content': 'years', 'name': str(i), 'url': url % ('%s', str(i)), 'image': 'years.png', 'icon': 'DefaultYear.png', 'action': 'tmdbmovies&folderName=%s' % quote_plus(str(i))})
		self.addDirectory(self.list, folderName=folderName)
		return self.list

	def moviesListToLibrary(self, url):
		url = getattr(self, url + '_link')
		u = urlparse(url).netloc.lower()
		try:
			control.hide()
			# if u in self.tmdb_link: items = tmdb_indexer.TMDb().userlists(url)
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
			library.libmovies().range(link, list_name)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

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
			navigator.Navigator().trakt_decades(genre=genre, mediatype='Movies',url=url, folderName=folderName)
		if self.list: self.worker()
		if self.list: self.movieDirectory(self.list, folderName=folderName)
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
		if self.list: self.movieDirectory(self.list, folderName=folderName)
		if self.list is None: self.list = []
		return self.list

	
	def multiMoviesListToLibrary(self, url):
		url = getattr(self, url + '_link')
		u = urlparse(url).netloc.lower()
		try:
			control.hide()
			# if u in self.tmdb_link: items = tmdb_indexer.TMDb().userlists(url)
			#if u in self.tmdb_link: items = tmdb_indexer().userlists(url)
			if u in self.trakt_link:
				if url in self.traktlikedlists_link:
					items = self.traktLlikedlists()
				else: items = self.trakt_user_lists(url, self.trakt_user)
			# items = [(i['name'], i['url']) for i in items]
			# message = 32663
			# select = control.selectDialog([i[0] for i in items], getLS(message))
			# list_name = items[select][0]
			# if select == -1: return
			# link = items[select][1]
			# link = link.split('&sort_by')[0]
			# link = link.split('?limit=')[0]
			#from resources.lib.modules import library
			#library.libmovies().range(link, list_name)
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
			except:
				lists += cache.get(self.trakt_user_lists, 0, self.traktlists_link, self.trakt_user)
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
			# lists = cache.get(tmdb_indexer.TMDb().userlists, 0, url)
			lists = cache.get(tmdb_indexer().userlists, 0, url)
			for i in range(len(lists)): lists[i].update({'image': 'tmdb.png', 'icon': 'DefaultVideoPlaylists.png', 'action': 'tmdbmovies&folderName=%s' % quote_plus(lists[i]['name'])})
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
			url = self.tmdb_link + '/3/account/{account_id}/favorite/movies?api_key=%s&session_id=%s&sort_by=created_at.asc&page=1' % ('%s', self.tmdb_session_id) 
			self.list.insert(0, {'name': getLS(32026), 'url': url, 'image': 'tmdb.png', 'icon': 'DefaultVideoPlaylists.png', 'action': 'tmdbmovies'})
		if self.tmdb_session_id != '': # TMDb Watchlist
			url = self.tmdb_link + '/3/account/{account_id}/watchlist/movies?api_key=%s&session_id=%s&sort_by=created_at.asc&page=1' % ('%s', self.tmdb_session_id)
			self.list.insert(0, {'name': getLS(32033), 'url': url, 'image': 'tmdb.png', 'icon': 'DefaultVideoPlaylists.png', 'action': 'tmdbmovies'})
		if self.imdb_user != '': # imdb Watchlist
			self.list.insert(0, {'name': getLS(32033), 'url': self.imdbwatchlist_link, 'image': 'imdb.png', 'icon': 'DefaultVideoPlaylists.png', 'action': 'movies&folderName=%s' % quote_plus(getLS(32033))})
		if self.imdb_user != '': # imdb My Ratings
			self.list.insert(0, {'name': getLS(32025), 'url': self.imdbratings_link, 'image': 'imdb.png', 'icon': 'DefaultVideoPlaylists.png', 'action': 'movies&folderName=%s' % quote_plus(getLS(32025))})
		if create_directory: self.addDirectory(self.list, queue=True, folderName=folderName)
		return self.list

	def traktCollection(self, url, create_directory=True, folderName=''):
		self.list = []
		try:
			try:
				q = dict(parse_qsl(urlsplit(url).query))
				index = int(q['page']) - 1
			except:
				q = dict(parse_qsl(urlsplit(url).query))
			self.list = traktsync.fetch_collection('movies_collection')
			useNext = True
			if create_directory:
				self.sort() # sort before local pagination
				if getSetting('trakt.paginate.lists') == 'true' and self.list:
					if len(self.list) == int(self.page_limit):
						useNext = False
					paginated_ids = [self.list[x:x + int(self.page_limit)] for x in range(0, len(self.list), int(self.page_limit))]
					self.list = paginated_ids[index]
			try:
				if useNext == False: raise Exception()
				if int(q['limit']) != len(self.list): raise Exception()
				q.update({'page': str(int(q['page']) + 1)})
				q = (urlencode(q)).replace('%2C', ',')
				next = url.replace('?' + urlparse(url).query, '') + '?' + q
				next = next + '&folderName=%s' % quote_plus(folderName)
			except: next = ''
			for i in range(len(self.list)): self.list[i]['next'] = next
			self.worker()
			if self.list is None: self.list = []
			if create_directory: self.movieDirectory(self.list, folderName=folderName)
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
			self.list = traktsync.fetch_watch_list('movies_watchlist')
			useNext = True
			if create_directory:
				self.sort(type='movies.watchlist') # sort before local pagination
				if getSetting('trakt.paginate.lists') == 'true' and self.list:
					if len(self.list) == int(self.page_limit):
						useNext = False
					paginated_ids = [self.list[x:x + int(self.page_limit)] for x in range(0, len(self.list), int(self.page_limit))]
					self.list = paginated_ids[index]
			try:
				if useNext == False: raise Exception()
				if int(q['limit']) != len(self.list): raise Exception()
				q.update({'page': str(int(q['page']) + 1)})
				q = (urlencode(q)).replace('%2C', ',')
				next = url.replace('?' + urlparse(url).query, '') + '?' + q
				next = next + '&folderName=%s' % quote_plus(folderName)
			except: next = ''
			for i in range(len(self.list)): self.list[i]['next'] = next
			self.worker()
			if self.list is None: self.list = []
			if create_directory: self.movieDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def traktLlikedlists(self, create_directory=True, folderName=''):
		items = traktsync.fetch_liked_list('', True)
		for item in items:
			try:
				if item['content_type'] == 'shows': continue
				listAction = 'movies'
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
		for item in items: # rating and votes via TMDb, or I must use "extended=full" and it slows down
			try:
				values = {}
				values['next'] = next 
				values['added'] = item.get('listed_at', '')
				values['paused_at'] = item.get('paused_at', '') # for unfinished
				try: values['progress'] = item['progress']
				except: values['progress'] = ''
				try: values['lastplayed'] = item['watched_at'] # for history
				except: values['lastplayed'] = ''
				movie = item.get('movie') or item
				values['title'] = movie.get('title')
				values['originaltitle'] = values['title']
				values['year'] = str(movie.get('year', '')) if movie.get('year') else ''
				ids = movie.get('ids', {})
				values['imdb'] = str(ids.get('imdb', '')) if ids.get('imdb') else ''
				values['tmdb'] = str(ids.get('tmdb', '')) if ids.get('tmdb') else ''
				values['tvdb'] = ''
				values['mediatype'] = 'movies'
				self.list.append(values)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		return self.list

	def trakt_list_mixed(self, url, user):
		self.list = []
		tvsurl = url.split('movies')[0]
		tvsurl = tvsurl + 'shows'
		mitems = trakt.getTraktAsJson(url)
		tvitems = trakt.getTraktAsJson(tvsurl)
		if not mitems and not tvitems: return
		for item in mitems: # rating and votes via TMDb, or I must use "extended=full" and it slows down
				try:
					values = {}
					values['next'] = next 
					values['added'] = item.get('listed_at', '')
					values['paused_at'] = item.get('paused_at', '') # for unfinished
					try: values['progress'] = item['progress']
					except: values['progress'] = ''
					try: values['lastplayed'] = item['watched_at'] # for history
					except: values['lastplayed'] = ''
					movie = item.get('movie') or item
					values['title'] = movie.get('title')
					values['originaltitle'] = values['title']
					values['year'] = str(movie.get('year', '')) if movie.get('year') else ''
					ids = movie.get('ids', {})
					values['imdb'] = str(ids.get('imdb', '')) if ids.get('imdb') else ''
					values['tmdb'] = str(ids.get('tmdb', '')) if ids.get('tmdb') else ''
					values['tvdb'] = ''
					values['mediatype'] = 'movies'
					self.list.append(values)
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
		for item in tvitems:
				try:
					values = {}
					values['next'] = next 
					values['added'] = item.get('listed_at', '')
					values['paused_at'] = item.get('paused_at', '') # for unfinished
					try: values['progress'] = item['progress']
					except: values['progress'] = ''
					try: values['lastplayed'] = item['watched_at'] # for history
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


	def trakt_userList(self, url, create_directory=True, folderName=''):
		self.list = []
		q = dict(parse_qsl(urlsplit(url).query))
		index = int(q['page']) - 1
		def userList_totalItems(url):
			items = trakt.getTraktAsJson(url)
			if not items: return
			for item in items:
				try:
					values = {}
					values['added'] = item.get('listed_at', '')
					movie = item['movie']
					values['title'] = movie.get('title')
					values['originaltitle'] = values['title']
					try: values['premiered'] = movie.get('released', '')[:10]
					except: values['premiered'] = ''
					values['year'] = str(movie.get('year', '')) if movie.get('year') else ''
					if not values['year']:
						try: values['year'] = str(values['premiered'][:4])
						except: values['year'] = ''
					ids = movie.get('ids', {})
					values['imdb'] = str(ids.get('imdb', '')) if ids.get('imdb') else ''
					values['tmdb'] = str(ids.get('tmdb', '')) if ids.get('tmdb') else ''
					values['rating'] = movie.get('rating')
					values['votes'] = movie.get('votes')
					values['mediatype'] = 'movies'
					self.list.append(values)
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
			return self.list
		self.list = cache.get(userList_totalItems, self.traktuserlist_hours, url.split('limit')[0] + 'extended=full')
		if not self.list: return
		self.sort() # sort before local pagination
		total_pages = 1
		useNext = True
		if getSetting('trakt.paginate.lists') == 'true':
			if len(self.list) == int(self.page_limit):
				useNext = False
			paginated_ids = [self.list[x:x + int(self.page_limit)] for x in range(0, len(self.list), int(self.page_limit))]
			total_pages = len(paginated_ids)
			self.list = paginated_ids[index]
		try:
			if useNext == False: raise Exception()
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
		if create_directory: self.movieDirectory(self.list, folderName=folderName)
		return self.list

	def trakt_user_lists(self, url, user):
		items = traktsync.fetch_user_lists('', True)
		for item in items:
			try:
				if item['content_type'] == 'shows': continue
				listAction = 'movies'
				if item['content_type'] == 'mixed':
					listAction = 'mixed'
				list_name = item['list_name']
				listAction = listAction+'&folderName=%s' % re.sub(r"[^a-zA-Z0-9 ]", "", list_name)
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
				self.list.append({'name': label, 'url': list_url, 'list_owner': list_owner, 'list_owner_slug': list_owner_slug, 'list_name': list_name, 'list_id': list_id, 'context': list_url, 'next': next, 'list_count': list_count,'image': 'trakt.png', 'icon': 'DefaultVideoPlaylists.png', 'action': listAction})
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
					if list_content.get('content_type', '') == 'shows': continue

				list_owner = list_item.get('user', {}).get('username', '')
				list_owner_slug = list_item.get('user', {}).get('ids', {}).get('slug', '')
				if not list_owner_slug: list_owner_slug = list_owner.lower()
				if any(list_item.get('privacy', '') == value for value in ('private', 'friends')): continue

				if list_owner_slug == 'trakt': list_url = 'https://api.trakt.tv/lists/%s/items/?limit=%s&page=1' % (list_id, self.page_limit)
				else: list_url = self.traktlist_link % (list_owner_slug, list_id)

				if getSetting('trakt.lists.showowner') == 'true':
					label = '%s - [COLOR %s]%s[/COLOR]' % (list_name, self.highlight_color, list_owner)
				else:
					label = '%s' % (list_name)
				self.list.append({'name': label, 'list_type': 'traktPulicList', 'url': list_url, 'list_owner': list_owner, 'list_name': list_name, 'list_id': list_id, 'context': list_url, 'next': next, 'image': 'trakt.png', 'icon': 'trakt.png', 'action': 'movies&folderName=%s' % quote_plus(list_name)})
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		return self.list

	def imdb_list(self, url, comingSoon=False, isRatinglink=False, folderName=''):
		from resources.lib.modules import log_utils
		log_utils.log('Umbrella IMDB list generation. URL: %s'% str(url), 1)
		list = []
		try:
			for i in re.findall(r'date\[(\d+)\]', url):
				url = url.replace('date[%s]' % i, (self.date_time - timedelta(days=int(i))).strftime('%Y-%m-%d'))
			result = client.request(url).replace('\n', ' ')
			items = client.parseDOM(result, 'div', attrs = {'class': '.+? lister-item'}) + client.parseDOM(result, 'div', attrs = {'class': 'lister-item .+?'})
			items += client.parseDOM(result, 'div', attrs = {'class': 'list_item.+?'})
			items += client.parseDOM(result, 'li', attrs = {'class': 'ipc-metadata-list-summary-item'})
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return
		next = ''
		try:
			# HTML syntax error, " directly followed by attribute name. Insert space in between. parseDOM can otherwise not handle it.
			result = result.replace('"class="lister-page-next', '" class="lister-page-next')
			next = client.parseDOM(result, 'a', ret='href', attrs = {'class': '.*?lister-page-next.*?'})
			if len(next) == 0:
				next = client.parseDOM(result, 'div', attrs = {'class': 'pagination'})[0]
				next = zip(client.parseDOM(next, 'a', ret='href'), client.parseDOM(next, 'a'))
				next = [i[0] for i in next if 'Next' in i[1]]
			next = url.replace(urlparse(url).query, urlparse(next[0]).query)
			next = client.replaceHTMLCodes(next)
			next = next + '&folderName=%s' % quote_plus(folderName)
		except: next = ''
		if not next:
			try:
				next = client.parseDOM(result, 'div', attrs = {'class': 'see-more'})
				next = client.parseDOM(next, 'a', ret='href')[1]
				next = self.imdb_link + next
			except: next = ''

		for item in items:
			try:
				#main_title = client.replaceHTMLCodes(client.parseDOM(item, 'a')[1])
				main_title = client.replaceHTMLCodes(client.parseDOM(item, 'h3')[0])
				#title = main_title.split(' (')[0]
				title = main_title.split('. ')[1]
				#year = client.parseDOM(item, 'span', attrs = {'class': 'lister-item-year.+?'})
				year = client.parseDOM(item, 'span', attrs ={'class': '.*?dli-title-metadata-item'})[0]
				if not year: year = [main_title]
				#try: year = re.findall(r'(\d{4})', year[0])[0]
				#except: continue
				if not year: continue
				if not comingSoon:
					if int(year) > int((self.date_time).strftime('%Y')): continue
				imdb = client.parseDOM(item, 'a', ret='href')[0]
				imdb = re.findall(r'(tt\d*)', imdb)[0]
				try: show = '–'.decode('utf-8') in str(year).decode('utf-8') or '-'.decode('utf-8') in str(year).decode('utf-8') # check with Matrix
				except: show = False
				if show or ('Episode:' in item): raise Exception() # Some lists contain TV shows.
				rating = votes = ''
				try:
					#rating = client.parseDOM(item, 'div', attrs = {'class': 'ratings-bar'})
					#rating = client.parseDOM(rating, 'strong')[0]
					ratingItem = client.parseDOM(item, 'div', attrs = {'class': '.*?dli-ratings-container'})
					rating = re.findall(r'(?<=</svg>).*?(?=<span)', ratingItem[0])
				except:
					try:
						rating = client.parseDOM(item, 'span', attrs = {'class': 'rating-rating'})
						rating = client.parseDOM(rating, 'span', attrs = {'class': 'value'})[0]
					except:
						try: rating = client.parseDOM(item, 'div', ret='data-value', attrs = {'class': '.*?imdb-rating'})[0] 
						except:
							try: rating = client.parseDOM(item, 'span', attrs = {'class': 'ipl-rating-star__rating'})[0]
							except: rating = ''
				try: 
					#votes = client.parseDOM(item, 'span', attrs = {'name': 'nv'})[0]
					votes = re.findall(r'(?<=-->).*?(?=<)', ratingItem[0])[0]
				except:
					try: votes = client.parseDOM(item, 'div', ret='title', attrs = {'class': '.*?rating-list'})[0]
					except:
						try: votes = re.findall(r'\((.+?) vote(?:s|)\)', votes)[0]
						except: votes = ''
				list.append({'title': title, 'originaltitle': title, 'year': year, 'imdb': imdb, 'tmdb': '', 'tvdb': '', 'rating': rating, 'votes': votes, 'next': next}) # just let super_info() TMDb request provide the meta and pass min to retrieve it
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		return list

	def imdb_genre_list(self, url, comingSoon=False, isRatinglink=False, folderName=''):
			from resources.lib.modules import log_utils
			log_utils.log('Umbrella Genre IMDB list generation. URL: %s'% str(url), 1)
			list = []
			try:
				for i in re.findall(r'date\[(\d+)\]', url):
					url = url.replace('date[%s]' % i, (self.date_time - timedelta(days=int(i))).strftime('%Y-%m-%d'))
				def imdb_watchlist_id(url):
					return client.parseDOM(client.request(url), 'meta', ret='content', attrs = {'property': 'pageId'})[0]
				if url == self.imdbwatchlist_link:
					url = cache.get(imdb_watchlist_id, 8640, url)
					url = self.imdbwatchlist2_link % url
				result = client.request(url).replace('\n', ' ')
				items = client.parseDOM(result, 'div', attrs = {'class': 'ipc-metadata-list-summary-item__tc'})
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
				return

			next = ''

			for item in items:
				try:
					main_title = client.parseDOM(item, 'h3', attrs = {'class': 'ipc-title__text'})
					title = main_title[0].split('. ')[1]
					year = client.parseDOM(item, 'span', attrs = {'class': '.*?dli-title-metadata-item'})[0]
					if not year: continue
					if not comingSoon:
						if int(year) > int((self.date_time).strftime('%Y')): continue
					imdb = client.parseDOM(item, 'a', ret='href')[0]
					imdb = re.findall(r'(tt\d*)', imdb)[0]
					try: show = '–'.decode('utf-8') in str(year).decode('utf-8') or '-'.decode('utf-8') in str(year).decode('utf-8') # check with Matrix
					except: show = False
					if show or ('Episode:' in item): raise Exception() # Some lists contain TV shows.
					rating = votes = ''
					rating = ''
					list.append({'title': title, 'originaltitle': title, 'year': year, 'imdb': imdb, 'tmdb': '', 'tvdb': '', 'rating': rating, 'votes': votes, 'next': next}) # just let super_info() TMDb request provide the meta and pass min to retrieve it
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
			return list

	def imdb_person_list(self, url):
		self.list = []
		try:
			result = client.request(url)
			#items = client.parseDOM(result, 'div', attrs = {'class': '.+?etail'})
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
				self.list.append({'name': name, 'url': url, 'image': image})
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		return self.list

	def imdb_user_list(self, url):
		list = []
		try:
			result = client.request(url)
			items = client.parseDOM(result, 'li', attrs={'class': 'ipc-metadata-list-summary-item'})
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		for item in items:
			try:
				#name = client.parseDOM(item, 'a')[0]
				#name = client.replaceHTMLCodes(name)
				name = client.parseDOM(item, 'a', attrs={'class': 'ipc-metadata-list-summary-item__t'})[0]
				url = client.parseDOM(item, 'a', ret='href')[0]
				url = url.split('/list/', 1)[-1].strip('/')
				url = self.imdblist_link % url
				url = client.replaceHTMLCodes(url)
				list.append({'name': name, 'url': url, 'context': url, 'image': 'imdb.png', 'icon': 'DefaultVideoPlaylists.png', 'action': 'movies&folderName=%s' % quote_plus(name)})
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		list = sorted(list, key=lambda k: re.sub(r'(^the |^a |^an )', '', k['name'].lower()))
		return list

	def dvdReleaseList(self, create_directory=True, folderName=''):
		self.list = cache.get(Movies().getDvdReleaseList, 96)
		self.worker()
		if self.list is None: self.list = []
		if create_directory: self.movieDirectory(self.list, folderName=folderName)

	def getDvdReleaseList(self):
		self.list = []
		try:
			url = 'https://www.dvdsreleasedates.com/digital-releases/'
			result = client.request(url).replace('\n', ' ')
			items = client.parseDOM(result,'table', attrs = {'class': 'fieldtable-inner'})
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return
		next = ''
		for count, item in enumerate(items):
			try:
				
				item0 = client.parseDOM(items[count], 'td', attrs = {'class': 'reldate past'})
				if len(item0) == 0:
					item0 = client.parseDOM(items[count], 'td', attrs = {'class': 'reldate '})
				item0 = str(item0)
				char1 = '</a>'
				char2 = '<div '
				dateitem = str(item0[item0.find(char1)+4 : item0.find(char2)])
				#Friday September 1, 2023
				try:
					item0date = time.strptime(dateitem, '%A %B %d, %Y')
				except:
					dateitem = str(item0[2 : item0.find(char2)])
					item0date = time.strptime(dateitem, '%A %B %d, %Y')
				item2 = client.parseDOM(item, 'td', attrs = {'class': 'dvdcell'})
				for x in item2:
					title = client.parseDOM(x, 'a')[1]
					year = datetime.fromtimestamp(time.mktime(item0date)).year
					imdb = client.parseDOM(x, 'a', ret='href')[2]
					imdb = imdb[imdb.find('title/')+6: -1]
					self.list.append({'title': title, 'originaltitle': title, 'year': year, 'imdb': imdb, 'tmdb': '', 'tvdb': '', 'next': next}) # just let super_info() TMDb request provide the meta and pass min to retrieve it
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		return self.list

	def reccomendedFromLibrary(self, folderName=''):
		#from resources.lib.modules import log_utils
		#log_utils.log('Rec List From Library', 1)
		try:
			self.list = []
			#get recommended movies - library movies with score higher than 7
			hasLibMovies = len(jsloads(control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": { "limits": { "start" : 0, "end": 1 }, "properties" : ["title", "genre", "uniqueid", "art", "rating", "thumbnail", "playcount", "file"] }, "id": "1"}'))['result']['movies']) > 0
			if not hasLibMovies:
				control.notification('No Movies', 'No movies found in library to use.')
				return self.list
			else:
				self.list = jsloads(control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"sort": {"method": "rating", "order": "descending"}, "filter": {"and":[{"operator": "greaterthan", "field": "rating", "value": "7"}, {"operator": "lessthan", "field": "playcount", "value": "1"}]}, "properties" : ["title", "genre", "uniqueid", "art", "rating", "thumbnail", "playcount", "file"] }, "id": "1"}'))['result']['movies']
				random.shuffle(self.list)
				self.list[:50]
				for x in self.list:
					x['tmdb'] = x.get('uniqueid').get('tmdb')
					x['imdb'] = x.get('uniqueid').get('imdb')
					x['next'] = ''
				self.worker()
		except:
			self.list  = []
		self.movieDirectory(self.list, folderName=folderName)
		return self.list


	def similarFromLibrary(self, tmdb=None, create_directory=True, folderName=''):
		#from resources.lib.modules import log_utils
		#log_utils.log('Similiar List From Library', 1)
		try:
			historyurl = 'https://api.trakt.tv/users/me/history/movies?limit=50&page=1'
			if tmdb == None:
				if self.traktCredentials:
					randomItems = self.trakt_list(historyurl, self.trakt_user, folderName)
				else:
					randomItems = None
			else:
				randomItems = {"tmdb": tmdb}
			if not randomItems:
				#no random item found from trakt history check library history
				randomMovies = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": { "filter": {"field": "playcount", "operator": "is", "value": "0"}, "properties" : ["art", "rating", "thumbnail", "playcount", "file", "uniqueid"], "sort": { "order": "ascending", "method": "label", "ignorearticle": true } }, "id": "libMovies"}')
				randomMovies = jsloads(randomMovies)['result']['movies']
				randomItems = [({"tmdb": x.get('uniqueid').get('tmdb')}) for x in randomMovies]
			if not randomItems:
				originalMovie = None
				control.notification('No History', 'No watch history found to use.')
			else:
				item = randomItems[random.randint(0, len(randomItems) - 1)]
				originalMovie = tmdb_indexer().get_movie_meta(item.get('tmdb'))
			self.list = []
			all_titles = list()
			if originalMovie:
				#log_utils.log('[plugin.video.umbrella] Original Movie properties %s.'% str(originalMovie),1)
				# get all movies for the genres in the movie
				neOriginal = originalMovie['genre'].split('/')
				genres = [x.strip() for x in neOriginal]
				similar_title = originalMovie["title"]
				
				########################################## more than 1 genre
				if len(genres) > 1:
					#contruct a batch for jsonrpc instead of a bunch of calls.
					orFilterGenre = ''
					localCache = ''
					for genre in genres:
						if genre == genres[0]:
							orFilterGenre += '{"operator": "is", "field": "genre", "value": "%s"},' % genre
							localCache += 'genre like "%' + genre + '%"' #localCache += 'genre like "%' + genre + '%"'
						elif genre == genres[-1]:
							orFilterGenre += '{"operator": "is", "field": "genre", "value": "%s"}' % genre
							#localCache += 'OR genre like %%s%' % genre
							localCache += 'OR genre like "%' + genre + '%"'
						else:
							orFilterGenre += '{"operator": "is", "field": "genre", "value": "%s"},' % genre
							#localCache += 'OR genre like %%s% ' % genre
							localCache += 'OR genre like "%' + genre + '%"'
					if control.setting('library.cachesimilar') == 'false':
						genreResults = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"filter": {"or": [%s]}, "properties" : ["title", "genre", "uniqueid", "art", "rating", "thumbnail", "playcount", "file", "director", "writer", "year", "mpaa", "set", "studio", "cast"] }, "id": "1"}'% orFilterGenre)
					#without watched
					#genreResults = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": { "filter": {"and": [{"or": [%s]},{"operator": "lessthan", "field": "playcount", "value": "1"}]},  "properties": ["title", "genre", "uniqueid", "art", "rating", "thumbnail", "playcount", "file", "director", "writer", "year", "mpaa"]}, "id": "libGenresUnwatched"}'% orFilterGenre)
						sameGenreMovies = jsloads(genreResults)['result']['movies']
					else:
						try:
							if not control.existsPath(control.dataPath): control.makeFile(control.dataPath)
							dbcon = database.connect(control.libCacheSimilar)
							dbcur = dbcon.cursor()
							dbcur.execute('''CREATE TABLE IF NOT EXISTS movies (title TEXT, genre TEXT, uniqueid TEXT UNIQUE, rating TEXT, thumbnail TEXT, playcount TEXT, file TEXT, director TEXT, writer TEXT, year TEXT, mpaa TEXT, "set" TEXT, studio TEXT, cast TEXT);''')
							dbcur.connection.commit()
						except: 
							from resources.lib.modules import log_utils
							log_utils.error()
						try:
							sameGenreMoviesSelect = dbcur.execute('''SELECT * FROM movies WHERE %s;'''% localCache).fetchall()
							if not sameGenreMoviesSelect: 
								return
							sameGenreMoviesStr = ''
							sameGenreMovies = []
							for dick in sameGenreMoviesSelect:
								sameGenreMoviesStr = ''
								sameGenreMoviesStr += '{"title":"'+ dick[0] +'",'
								batman = dick[1].split(",")
								batman = ', '.join(map(str, map(lambda x: f'"{x}"' if isinstance(x, str) else x, batman)))
								sameGenreMoviesStr += '"genre":['+ batman +'],'
								robin = dick[2].replace("'",'"').replace("{","").replace("}","")
								sameGenreMoviesStr += '"uniqueid":{'+ robin +'},'
								sameGenreMoviesStr += '"rating":'+ dick[3] +','
								alfred = dick[7].split(",")
								alfred = ', '.join(map(str, map(lambda x: f'"{x}"' if isinstance(x, str) else x, alfred)))
								sameGenreMoviesStr += '"director":['+ alfred +'],'
								penguin = dick[8].split(",")
								penguin = ', '.join(map(str, map(lambda x: f'"{x}"' if isinstance(x, str) else x, penguin)))
								sameGenreMoviesStr += '"writer":['+ penguin +'],'
								sameGenreMoviesStr += '"year":"'+ dick[9] +'",'
								sameGenreMoviesStr += '"mpaa":"'+ dick[10] +'",'
								sameGenreMoviesStr += '"set":"'+ dick[11] +'",'
								joker = dick[12].split(",")
								mrfreeze = []
								for x in joker: x = mrfreeze.append(x.replace('"',""))
								mrfreeze = ', '.join(map(str, map(lambda x: f'"{x}"' if isinstance(x, str) else x, mrfreeze)))
								sameGenreMoviesStr += '"studio":['+ mrfreeze +'],'
								castor = dick[13].split(",")
								for count, dicks in enumerate(castor):
									castor[count] = {"name": str(dicks).replace("'",'').replace('"','')}
								castor = ', '.join(map(str, map(lambda x: f'"{x}"' if isinstance(x, str) else x, castor)))
								castor = castor.replace("'",'"')
								sameGenreMoviesStr += '"cast":['+ castor +']}'
								try:
									#trying to append value
									sameGenreMovies.append(jsloads(sameGenreMoviesStr))
								except:
									from resources.lib.modules import log_utils
									if control.setting('debug.level') == '1':
										log_utils.log('sameGenreMoviesStr: %s' % sameGenreMoviesStr, level=log_utils.LOGDEBUG)
									log_utils.error()
						except: 
							from resources.lib.modules import log_utils
							log_utils.error()
						finally:
							dbcur.close() ; dbcon.close()
				########################################## 1 genre
				else:
					if control.setting('library.cachesimilar') == 'false':
						genreResults = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"filter": %s, "properties" : ["title", "genre", "uniqueid", "art", "rating", "thumbnail", "playcount", "file", "director", "writer", "year", "mpaa", "set", "studio", "cast"] }, "id": "1"}'% genre)
					#without watched
					#genreResults = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": { "filter": {"and": [{"or": [%s]},{"operator": "lessthan", "field": "playcount", "value": "1"}]},  "properties": ["title", "genre", "uniqueid", "art", "rating", "thumbnail", "playcount", "file", "director", "writer", "year", "mpaa"]}, "id": "libGenresUnwatched"}'% orFilterGenre)
						sameGenreMovies = jsloads(genreResults)['result']['movies']
					else:
						try:
							if not control.existsPath(control.dataPath): control.makeFile(control.dataPath)
							dbcon = database.connect(control.libCacheSimilar)
							dbcur = dbcon.cursor()
							dbcur.execute('''CREATE TABLE IF NOT EXISTS movies (title TEXT, genre TEXT, uniqueid TEXT UNIQUE, rating TEXT, thumbnail TEXT, playcount TEXT, file TEXT, director TEXT, writer TEXT, year TEXT, mpaa TEXT, "set" TEXT, studio TEXT, cast TEXT);''')
							dbcur.connection.commit()
						except: 
							from resources.lib.modules import log_utils
							log_utils.error()
						try:
							localGenre = 'genre like "%' + genres[0] + '%"'
							sameGenreMoviesSelect = dbcur.execute('''SELECT * FROM movies WHERE %s;'''% localGenre).fetchall()
							if not sameGenreMoviesSelect: 
								return
							sameGenreMoviesStr = ''
							sameGenreMovies = []
							for dick in sameGenreMoviesSelect:
								sameGenreMoviesStr = ''
								sameGenreMoviesStr += '{"title":"'+ dick[0] +'",'
								batman = dick[1].split(",")
								batman = ', '.join(map(str, map(lambda x: f'"{x}"' if isinstance(x, str) else x, batman)))
								sameGenreMoviesStr += '"genre":['+ batman +'],'
								robin = dick[2].replace("'",'"').replace("{","").replace("}","")
								sameGenreMoviesStr += '"uniqueid":{'+ robin +'},'
								sameGenreMoviesStr += '"rating":'+ dick[3] +','
								alfred = dick[7].split(",")
								alfred = ', '.join(map(str, map(lambda x: f'"{x}"' if isinstance(x, str) else x, alfred)))
								sameGenreMoviesStr += '"director":['+ alfred +'],'
								penguin = dick[8].split(",")
								penguin = ', '.join(map(str, map(lambda x: f'"{x}"' if isinstance(x, str) else x, penguin)))
								sameGenreMoviesStr += '"writer":['+ penguin +'],'
								sameGenreMoviesStr += '"year":"'+ dick[9] +'",'
								sameGenreMoviesStr += '"mpaa":"'+ dick[10] +'",'
								sameGenreMoviesStr += '"set":"'+ dick[11] +'",'
								joker = dick[12].split(",")
								mrfreeze = []
								for x in joker: x = mrfreeze.append(x.replace('"',""))
								mrfreeze = ', '.join(map(str, map(lambda x: f'"{x}"' if isinstance(x, str) else x, mrfreeze)))
								sameGenreMoviesStr += '"studio":['+ mrfreeze +'],'
								castor = dick[13].split(",")
								for count, dicks in enumerate(castor):
									castor[count] = {"name": str(dicks).replace("'",'').replace('"','')}
								castor = ', '.join(map(str, map(lambda x: f'"{x}"' if isinstance(x, str) else x, castor)))
								castor = castor.replace("'",'"')
								sameGenreMoviesStr += '"cast":['+ castor +']}'
								try:
									#trying to append value
									sameGenreMovies.append(jsloads(sameGenreMoviesStr))
								except:
									from resources.lib.modules import log_utils
									if control.setting('debug.level') == '1':
										log_utils.log('sameGenreMoviesStr: %s' % sameGenreMoviesStr, level=log_utils.LOGDEBUG)
									log_utils.error()
						except: 
							from resources.lib.modules import log_utils
							log_utils.error()
						finally:
							dbcur.close() ; dbcon.close()
				set_genres = set(genres)
				set_directors = set([originalMovie["director"]])
				set_writers = set([originalMovie["writer"]])
				castList = [x["name"] for x in originalMovie["castandart"]]
				set_cast = set(castList)
				for item in sameGenreMovies:
					# prevent duplicates so skip reference movie and titles already in the list
					if not item["title"] in all_titles and not item["title"] == similar_title:
						item['tmdb'] = item.get('uniqueid').get('tmdb')
						item['imdb'] = item.get('uniqueid').get('imdb')
						itemcastList = [x["name"] for x in item["cast"]]
						genre_score = 0 if not set_genres else (float(len(set_genres.intersection(item["genre"])) / len(set_genres.union(item["genre"])))) * 1
						director_score = 0 if not set_directors else float(len(set_directors.intersection(item["director"]))) / len(set_directors.union(item["director"]))
						writer_score = 0 if not set_writers else float(len(set_writers.intersection(item["writer"]))) / len(set_writers.union(item["writer"]))
						if originalMovie["rating"] and item["rating"] and abs(float(originalMovie["rating"])-item["rating"]) < 3:
							rating_score = 1 - abs(float(originalMovie["rating"])-item["rating"])//3
						else:
							rating_score = 0
						#studio
						try:
							studio_score = 1 if originalMovie["studio"] and originalMovie["studio"] == str(item.get("studio")[0]) else 0
							#log_utils.log('item similar scores item:%s studio score: %s original studio: %s compare studio: %s'% (item["title"], studio_score,originalMovie["studio"], item.get("studio")[0]))
						except:
							studio_score = 0
							#log_utils.log('EXCEPTION: item similar scores item:%s studio score: %s original studio: %s compare studio: %s'% (item["title"], studio_score,originalMovie["studio"], item.get("studio")))
						
						#cast score
						try:
							cast_score = 0 if not set_cast else (float(len(set_cast.intersection(set(itemcastList)))) / len(set_cast.union(set(itemcastList)))) *1
						except:
							cast_score = 0
						#log_utils.log('item similar scores item:%s cast score: %s'% (item["title"], cast_score))
						try:
							set_score = 1 if originalMovie["belongs_to_collection"] and originalMovie["belongs_to_collection"]["name"] == item["set"] else 0
						except:
							set_score = 0
						# year_score is "closeness" in release year, scaled to 1 (0 if not from same decade)
						if int(originalMovie["year"]) and int(item["year"]) and abs(float(originalMovie["rating"])-int(item["year"])) < 10:
							year_score = 1 - abs(originalMovie["year"]-int(item["year"]))//10
						else:
							year_score = 0
						# mpaa_score gets 1 if same mpaa rating, otherwise 0
						mpaa_score = 1 if originalMovie["mpaa"] and ('Rated '+str(originalMovie["mpaa"])) == item["mpaa"] else 0
						# calculate overall score using weighted average
						similarscore = .75*set_score+.5*genre_score + .15*director_score + .1*writer_score +.1*cast_score+.025*studio_score+ .05*rating_score + .075*year_score + .025*mpaa_score
						item["similarscore"] = similarscore
						item["cast"] = None
						self.list.append(item) 
						all_titles.append(item["title"])
			# return the list sorted by number of matching genres then rating
			similar_score_dict = {}
			self.list = sorted(self.list, key=itemgetter("similarscore"), reverse=True)
			for item in self.list:
				similar_score = item['similarscore']
				if not similar_score in similar_score_dict:
					matches = [i for i in self.list if i['similarscore'] == similar_score]
					similar_score_dict[similar_score] = matches
			similar_list = []
			if len(similar_score_dict)>1:
				#for x in similar_score_dict:
				for count, x in enumerate(similar_score_dict):
					if len(similar_list) > 200 and count > 0: break
					for z in similar_score_dict[x]:
						similar_list.append(z)
				self.list = similar_list
			else:
				if control.setting('debug.level') == '1':
					from resources.lib.modules import log_utils
					log_utils.log('Only one similar score found.',level=log_utils.LOGDEBUG)

			random.shuffle(self.list)
			self.list = self.list[:50]
			self.list = sorted(self.list, key=itemgetter("similarscore"), reverse=True)
			next = ''
			for i in range(len(self.list)): 
				self.list[i]['next'] = next
				#log_utils.log('item similar scores item:%s score: %s'% (self.list[i]["title"], self.list[i]["similarscore"]))
			#self.list = [x for x in self.list if x.get('playcount') == 0]
			self.worker()
			if originalMovie:
				try: 
					folderName = getLS(40257)+' '+originalMovie["title"]
					control.setHomeWindowProperty('umbrella.moviesimilarlibrary', str(getLS(40257)+' '+originalMovie["title"]))
				except: pass
			if self.list is None: self.list = []
			is_widget = 'plugin' not in control.infoLabel('Container.PluginName')
			if create_directory: self.movieDirectory(self.list, folderName=folderName)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return

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
			self.list = [i for i in self.list if i.get('tmdb')]
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def super_info(self, i):
		try:
			if self.list[i]['metacache']: return
			imdb, tmdb = self.list[i].get('imdb', ''), self.list[i].get('tmdb', '')
#### -- Missing id's lookup -- ####
			if not tmdb and imdb:
				try:
					# result = cache.get(tmdb_indexer.Movies().IdLookup, 96, imdb)
					result = cache.get(tmdb_indexer().IdLookup, 96, imdb)
					tmdb = str(result.get('id', '')) if result.get('id') else ''
				except: tmdb = ''
			if not tmdb and imdb:
				trakt_ids = trakt.IdLookup('imdb', imdb, 'movie') # "trakt.IDLookup()" caches item
				if trakt_ids: tmdb = str(trakt_ids.get('tmdb', '')) if trakt_ids.get('tmdb') else ''
			if not tmdb and not imdb:
				try:
					results = trakt.SearchMovie(title=quote_plus(self.list[i]['title']), year=self.list[i]['year'], fields='title', full=False) # "trakt.SearchMovie()" caches item
					if results[0]['movie']['title'] != self.list[i]['title'] or results[0]['movie']['year'] != self.list[i]['year']: return
					ids = results[0].get('movie', {}).get('ids', {})
					if not tmdb: tmdb = str(ids.get('tmdb', '')) if ids.get('tmdb') else ''
					if not imdb: imdb = str(ids.get('imdb', '')) if ids.get('imdb') else ''
				except: pass
#################################
			if not tmdb: return
			# movie_meta = tmdb_indexer.Movies().get_movie_meta(tmdb)
			movie_meta = tmdb_indexer().get_movie_meta(tmdb)
			if not movie_meta or '404:NOT FOUND' in movie_meta: return # trakt search turns up alot of junk with wrong tmdb_id's causing 404's
			values = {}
			values.update(movie_meta)
			if 'rating' in self.list[i] and self.list[i]['rating']: values['rating'] = self.list[i]['rating'] # prefer imdb,trakt rating and votes if set
			if 'votes' in self.list[i] and self.list[i]['votes']: values['votes'] = self.list[i]['votes']
			if 'year' in self.list[i] and self.list[i]['year'] != values.get('year'): values['year'] = self.list[i]['year']
			if not imdb: imdb = values.get('imdb', '')
			if not values.get('imdb'): values['imdb'] = imdb
			if not values.get('tmdb'): values['tmdb'] = tmdb
			if self.lang != 'en':
				try:
					if 'available_translations' in self.list[i] and self.lang not in self.list[i]['available_translations']: raise Exception()
					trans_item = trakt.getMovieTranslation(imdb, self.lang, full=True)
					if trans_item:
						if trans_item.get('title'): values['title'] = trans_item.get('title')
						if trans_item.get('overview'): values['plot'] =trans_item.get('overview')
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
			if self.enable_fanarttv:
				extended_art = fanarttv_cache.get(FanartTv().get_movie_art, 336, imdb, tmdb)
				if extended_art: values.update(extended_art)
			values = dict((k, v) for k, v in iter(values.items()) if v is not None and v != '') # remove empty keys so .update() doesn't over-write good meta with empty values.
			self.list[i].update(values)
			meta = {'imdb': imdb, 'tmdb': tmdb, 'tvdb': '', 'lang': self.lang, 'user': self.user, 'item': values}
			self.meta.append(meta)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def movieDirectory(self, items, unfinished=False, next=True, folderName=''):
		from sys import argv # some functions like ActivateWindow() throw invalid handle less this is imported here.
		is_widget = 'plugin' not in control.infoLabel('Container.PluginName')
		if not items: # with reuselanguageinvoker on an empty directory must be loaded, do not use sys.exit()
			control.hide()
			if is_widget != True: control.notification(title=32001, message=33049)
		if self.useContainerTitles: control.setContainerName(folderName)
		from resources.lib.modules.player import Bookmarks
		sysaddon, syshandle = 'plugin://plugin.video.umbrella/', int(argv[1])
		play_mode = getSetting('play.mode.movie')
		rescrape_useDefault = getSetting('rescrape.default') == 'true'
		rescrape_method = getSetting('rescrape.default2')
		
		settingFanart = getSetting('fanart') == 'true'
		addonPoster, addonFanart, addonBanner = control.addonPoster(), control.addonFanart(), control.addonBanner()
		indicators = getMovieIndicators() # refresh not needed now due to service sync
		if play_mode == '1': playbackMenu = getLS(32063)
		else: playbackMenu = getLS(32064)
		if trakt.getTraktIndicatorsInfo(): watchedMenu, unwatchedMenu = getLS(32068), getLS(32069)
		else: watchedMenu, unwatchedMenu = getLS(32066), getLS(32067)
		playlistManagerMenu, queueMenu, trailerMenu = getLS(35522), getLS(32065), getLS(40431)
		traktManagerMenu, addToLibrary, addToFavourites, removeFromFavourites = getLS(32070), getLS(32551), getLS(40463), getLS(40468)
		nextMenu, clearSourcesMenu = getLS(32053), getLS(32611)
		rescrapeMenu, findSimilarMenu = getLS(32185), getLS(32184)
		from resources.lib.modules import favourites
		favoriteItems = favourites.getFavourites(content='movies')
		favoriteItems = [x[1].get('imdb') for x in favoriteItems]
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
				imdb, tmdb, title, year = i.get('imdb', ''), i.get('tmdb', ''), i['title'], i.get('year', '')
				trailer, runtime = i.get('trailer'), i.get('duration')
				if self.useReleaseYear:
					label = '%s (%s)' % (title, year)
				else:
					label = '%s' % title
				try: labelProgress = label + '[COLOR %s]  [%s][/COLOR]' % (self.highlight_color, str(round(float(i['progress']), 1)) + '%')
				except: labelProgress = label
				try:
					if int(re.sub(r'[^0-9]', '', str(i['premiered']))) > int(re.sub(r'[^0-9]', '', str(self.today_date))): 
						if self.hidecinema:
							continue
						else:
							labelProgress = '[COLOR %s][I]%s[/I][/COLOR]' % (self.unairedcolor, labelProgress)
				except: pass
				if i.get('traktHistory') is True: # uses Trakt lastplayed
					try:
						air_datetime = tools.convert_time(stringTime=i.get('lastplayed', ''), zoneFrom='utc', zoneTo='local', formatInput='%Y-%m-%dT%H:%M:%S.000Z', formatOutput='%b %d %Y %I:%M %p', remove_zeroes=True)
						labelProgress = labelProgress + '[COLOR %s]  [%s][/COLOR]' % (self.highlight_color, air_datetime)
					except: pass
				sysname, systitle = quote_plus(label), quote_plus(title)
				meta = dict((k, v) for k, v in iter(i.items()) if v is not None and v != '')
				meta.update({'code': imdb, 'imdbnumber': imdb, 'mediatype': 'movie', 'tag': [imdb, tmdb]})
				try: meta.update({'genre': cleangenre.lang(meta['genre'], self.lang)})
				except: pass
				#since you are so bored you are reading my comments in my code from my test repo. below is how you do it correctly. when you figure out a variable it is important to actually apply it. you can fix yours by putting clearlogo in the art.update below or just copy what I did here. "i am mad about comments in your code" cannot wait for that one.
				if self.prefer_tmdbArt: 
					poster = meta.get('poster3') or meta.get('poster') or meta.get('poster2') or addonPoster
					clearlogo = meta.get('tmdblogo') or meta.get('clearlogo','')
					meta.update({'clearlogo': clearlogo})
				else: 
					poster = meta.get('poster2') or meta.get('poster3') or meta.get('poster') or addonPoster
					clearlogo = meta.get('clearlogo') or meta.get('tmdblogo','')
					meta.update({'clearlogo': clearlogo})
				fanart = ''
				if settingFanart:
					if self.prefer_tmdbArt: fanart = meta.get('fanart3') or meta.get('fanart') or meta.get('fanart2') or addonFanart
					else: fanart = meta.get('fanart2') or meta.get('fanart3') or meta.get('fanart') or addonFanart
				landscape = meta.get('landscape') or fanart
				thumb = meta.get('thumb') or poster or landscape
				icon = meta.get('icon') or poster
				banner = meta.get('banner3') or meta.get('banner2') or meta.get('banner') or addonBanner
				art = {}
				art.update({'icon': icon, 'thumb': thumb, 'banner': banner, 'poster': poster, 'fanart': fanart, 'landscape': landscape, 'clearlogo': meta.get('clearlogo', ''),
								'clearart': meta.get('clearart', ''), 'discart': meta.get('discart', ''), 'keyart': meta.get('keyart', '')})
				for k in ('metacache', 'poster2', 'poster3', 'fanart2', 'fanart3', 'banner2', 'banner3', 'trailer'): meta.pop(k, None)
				meta.update({'poster': poster, 'fanart': fanart, 'banner': banner})
				sysmeta, sysart = quote_plus(jsdumps(meta)), quote_plus(jsdumps(art))
				url = '%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&meta=%s' % (sysaddon, systitle, year, imdb, tmdb, sysmeta)
				#url = '%s?action=play_info&title=%s&year=%s&imdb=%s&tmdb=%s&meta=%s' % (sysaddon, systitle, year, imdb, tmdb, sysmeta)
				sysurl = quote_plus(url)
####-Context Menu and Overlays-####
				cm = []
				if trailer:
					cm.append((trailerMenu, 'RunPlugin(%s?action=play_Trailer_Context&type=%s&name=%s&year=%s&imdb=%s&url=%s)' % (sysaddon, 'movie', sysname, year, imdb, trailer)))
				try:
					watched = getMovieOverlay(indicators, imdb) == '5'
					if self.traktCredentials:
						cm.append((traktManagerMenu, 'RunPlugin(%s?action=tools_traktManager&name=%s&imdb=%s&watched=%s&unfinished=%s)' % (sysaddon, sysname, imdb, watched, unfinished)))
					if watched:
						cm.append((unwatchedMenu, 'RunPlugin(%s?action=playcount_Movie&name=%s&imdb=%s&query=4)' % (sysaddon, sysname, imdb)))
						meta.update({'playcount': 1, 'overlay': 5})
						# meta.update({'lastplayed': trakt.watchedMoviesTime(imdb)}) # no skin support
					else:
						cm.append((watchedMenu, 'RunPlugin(%s?action=playcount_Movie&name=%s&imdb=%s&query=5)' % (sysaddon, sysname, imdb)))
						meta.update({'playcount': 0, 'overlay': 4})
				except: pass
				cm.append((playlistManagerMenu, 'RunPlugin(%s?action=playlist_Manager&name=%s&url=%s&meta=%s&art=%s)' % (sysaddon, sysname, sysurl, sysmeta, sysart)))
				cm.append((queueMenu, 'RunPlugin(%s?action=playlist_QueueItem&name=%s)' % (sysaddon, sysname)))
				cm.append((addToLibrary, 'RunPlugin(%s?action=library_movieToLibrary&name=%s&title=%s&year=%s&imdb=%s&tmdb=%s)' % (sysaddon, sysname, systitle, year, imdb, tmdb)))
				if favoriteItems:
					if imdb in favoriteItems:
						cm.append((removeFromFavourites, 'RunPlugin(%s?action=remove_favorite&meta=%s&content=%s)' % (sysaddon, sysmeta, 'movies')))
					else:
						cm.append((addToFavourites, 'RunPlugin(%s?action=add_favorite&meta=%s&content=%s)' % (sysaddon, sysmeta, 'movies')))
				else:
					cm.append((addToFavourites, 'RunPlugin(%s?action=add_favorite&meta=%s&content=%s)' % (sysaddon, sysmeta, 'movies')))
				cm.append((findSimilarMenu, 'Container.Update(%s?action=movies&url=%s)' % (sysaddon, quote_plus('https://api.trakt.tv/movies/%s/related?limit=20&page=1,return' % imdb))))
				if i.get('belongs_to_collection', ''):
					if getSetting('tmdb.baseaddress') == 'true':
						cm.append(('Browse Collection', 'Container.Update(%s?action=collections&url=%s)' % (
							sysaddon, quote_plus('https://api.tmdb.org/3/collection/%s?api_key=%s&page=1,return' % (i['belongs_to_collection']['id'], self.tmdb_key)))))
					else:
						cm.append(('Browse Collection', 'Container.Update(%s?action=collections&url=%s)' % (
							sysaddon, quote_plus('https://api.themoviedb.org/3/collection/%s?api_key=%s&page=1,return' % (i['belongs_to_collection']['id'], self.tmdb_key)))))
				cm.append((playbackMenu, 'RunPlugin(%s?action=alterSources&url=%s&meta=%s)' % (sysaddon, sysurl, sysmeta)))
				if not rescrape_useDefault:
					cm.append(('Rescrape Options ------>', 'PlayMedia(%s?action=rescrapeMenu&title=%s&year=%s&imdb=%s&tmdb=%s&meta=%s)' % (sysaddon, systitle, year, imdb, tmdb, sysmeta)))
				else:
					if rescrape_method == '0':
						cm.append((rescrapeMenu, 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&meta=%s&rescrape=true&select=1)' % (sysaddon, systitle, year, imdb, tmdb, sysmeta)))
					if rescrape_method == '1':
						cm.append((rescrapeMenu, 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&meta=%s&rescrape=true&select=0)' % (sysaddon, systitle, year, imdb, tmdb, sysmeta)))
					if rescrape_method == '2':
						cm.append((rescrapeMenu, 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&meta=%s&rescrape=true&all_providers=true&select=1)' % (sysaddon, systitle, year, imdb, tmdb, sysmeta)))
					if rescrape_method == '3':
						cm.append((rescrapeMenu, 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&meta=%s&rescrape=true&all_providers=true&select=0)' % (sysaddon, systitle, year, imdb, tmdb, sysmeta)))
				cm.append((clearSourcesMenu, 'RunPlugin(%s?action=cache_clearSources)' % sysaddon))
				if not is_widget and page > 2:
					cm.append((getLS(40476), 'RunPlugin(%s?action=return_home&folder=%s)' % (sysaddon, 'movies')))
				cm.append(('[COLOR %s]Umbrella Settings[/COLOR]' % self.highlight_color, 'RunPlugin(%s?action=tools_openSettings)' % sysaddon))
####################################
				if trailer: meta.update({'trailer': trailer}) # removed temp so it's not passed to CM items, only infoLabels for skin
				else: meta.update({'trailer': '%s?action=play_Trailer&type=%s&name=%s&year=%s&imdb=%s' % (sysaddon, 'movie', sysname, year, imdb)})
				item = control.item(label=labelProgress, offscreen=True)
				#if 'castandart' in i: item.setCast(i['castandart'])#changed for kodi20 setinfo method
				if 'castandart' in i: meta.update({'castandart':i['castandart']})
				item.setArt(art)
				#item.setUniqueIDs({'imdb': imdb, 'tmdb': tmdb}) #changed for kodi20 setinfo method
				setUniqueIDs = {'imdb': imdb, 'tmdb': tmdb}
###########################################################
				item.setProperty('IsPlayable', 'true')
				if is_widget: 
					item.setProperty('isUmbrella_widget', 'true')
					if self.hide_watched_in_widget and str(xbmc.getInfoLabel("Window.Property(xmlfile)")) != 'Custom_1114_Search.xml':
						if str(meta.get('playcount', 0)) == '1':
							continue
				if self.unairedcolor not in labelProgress:
					resumetime = Bookmarks().get(name=label, imdb=imdb, tmdb=tmdb, year=str(year), runtime=runtime, ck=True)
					# item.setProperty('TotalTime', str(meta['duration'])) # Adding this property causes the Kodi bookmark CM items to be added
					#item.setProperty('ResumeTime', str(resumetime))
					try: item.setProperty('WatchedProgress', str(int(float(resumetime) / float(runtime) * 100)))
					except: pass
				#item.setInfo(type='video', infoLabels=control.metadataClean(meta))
				try: 
					resumetime = resumetime
				except:
					resumetime = ''
				control.set_info(item, meta, setUniqueIDs=setUniqueIDs, resumetime=resumetime)

				if is_widget and control.getKodiVersion() > 19.5 and self.useFullContext != True:
					pass
				else:
					item.addContextMenuItems(cm)
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		
		if next:
			try:
				if not items: raise Exception()
				url = items[0]['next']
				if not url: raise Exception()
				url_params = dict(parse_qsl(urlsplit(url).query))
				if 'imdb.com' in url and 'start' in url_params: page = '  [I](%s)[/I]' % str(int(((int(url_params.get('start')) - 1) / int(self.page_limit)) + 1))
				elif 'www.imdb.com/movies-coming-soon/' in url: page = '  [I](%s)[/I]' % re.search(r'(\d{4}-\d{2})', url).group(1)
				else: page = '  [I](%s)[/I]' % url_params.get('page')
				if 'None' in page: page = page.split('  [I]')[0]
				nextColor ='[COLOR %s]' % getSetting('highlight.color')
				nextMenu = nextColor + nextMenu + page + '[/COLOR]'
				u = urlparse(url).netloc.lower()
				if u not in self.tmdb_link: url = '%s?action=moviePage&url=%s&folderName=%s' % (sysaddon, quote_plus(url), quote_plus(folderName))
				elif u in self.tmdb_link: url = '%s?action=tmdbmoviePage&url=%s&folderName=%s' % (sysaddon, quote_plus(url), quote_plus(folderName))
				elif u in self.mbdlist_list_items: url = '%s?action=moviePage&url=%s&folderName=%s' % (sysaddon, quote_plus(url), quote_plus(folderName))
				item = control.item(label=nextMenu, offscreen=True)
				icon = control.addonNext()
				item.setArt({'icon': icon, 'thumb': icon, 'poster': icon, 'banner': icon})
				item.setProperty ('SpecialSort', 'bottom')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		control.content(syshandle, 'movies')
		control.directory(syshandle, cacheToDisc=True)
		control.sleep(200)
		views.setView('movies', {'skin.estuary': 55, 'skin.confluence': 500})

	def addDirectory(self, items, queue=False, folderName=''):
		from sys import argv # some functions like ActivateWindow() throw invalid handle less this is imported here.
		is_widget = 'plugin' not in control.infoLabel('Container.PluginName')
		returnHome = control.folderPath()
		homeWindow.setProperty('umbrella.returnhome', returnHome)
		if not items: # with reuselanguageinvoker on an empty directory must be loaded, do not use sys.exit()
			content = ''
			control.hide()
			if is_widget != True:
				control.notification(title=32001, message=33049)
		if self.useContainerTitles: control.setContainerName(folderName)
		sysaddon, syshandle = 'plugin://plugin.video.umbrella/', int(argv[1])
		addonThumb = control.addonThumb()
		artPath = control.artPath()
		queueMenu, playRandom, addToLibrary, addToFavourites, removeFromFavourites = getLS(32065), getLS(32535), getLS(32551), getLS(40463), getLS(40468)
		likeMenu, unlikeMenu = getLS(32186), getLS(32187)
		from resources.lib.modules import favourites
		favoriteItems = favourites.getFavourites(content='movies')
		favoriteItems = [x[1].get('imdb') for x in favoriteItems]
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
				cm.append((playRandom, 'RunPlugin(%s?action=play_Random&rtype=movie&url=%s)' % (sysaddon, quote_plus(i['url']))))
				if queue: cm.append((queueMenu, 'RunPlugin(%s?action=playlist_QueueItem)' % sysaddon))
				try:
					if getSetting('library.service.update') == 'true':
						cm.append((addToLibrary, 'RunPlugin(%s?action=library_moviesToLibrary&url=%s&name=%s)' % (sysaddon, quote_plus(i['context']), name)))
				except: pass
				cm.append(('[COLOR %s]Umbrella Settings[/COLOR]' % self.highlight_color, 'RunPlugin(%s?action=tools_openSettings)' % sysaddon))
				item = control.item(label=name, offscreen=True)
				item.setArt({'icon': icon, 'poster': poster, 'thumb': icon, 'fanart': control.addonFanart(), 'banner': poster})
				#item.setInfo(type='video', infoLabels={'plot': name})#changed for kodi20 setinfo method
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
			nextColor = '[COLOR %s]' % getSetting('highlight.color')
			nextMenu = nextColor +nextMenu + page  + '[/COLOR]'
			icon = control.addonNext()
			url = '%s?action=movies_PublicLists&url=%s' % (sysaddon, quote_plus(url))
			item = control.item(label=nextMenu, offscreen=True)
			item.setArt({'icon': icon, 'thumb': icon, 'poster': icon, 'banner': icon})
			item.setProperty ('SpecialSort', 'bottom')
			control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

		skin = control.skin
		if skin in ('skin.arctic.horizon', 'skin.arctic.horizon.2'): pass
		elif skin in ('skin.estuary', 'skin.aeon.nox.silvo', 'skin.pellucid'): content = ''
		elif skin == 'skin.auramod':
			if content not in ('actors', 'genres'): content = 'addons'
			else: content = ''
		control.content(syshandle, content) # some skins use their own thumb for things like "genres" when content type is set here
		control.directory(syshandle, cacheToDisc=True)