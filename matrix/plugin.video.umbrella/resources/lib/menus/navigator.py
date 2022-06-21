# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from sys import exit as sysexit
from urllib.parse import quote_plus
from resources.lib.modules import control
from resources.lib.modules.trakt import getTraktCredentialsInfo, getTraktIndicatorsInfo

getLS = control.lang
getSetting = control.setting
getMenuEnabled = control.getMenuEnabled


class Navigator:
	def __init__(self):
		self.artPath = control.artPath()
		self.iconLogos = getSetting('icon.logos') != 'Traditional'
		self.indexLabels = getSetting('index.labels') == 'true'
		self.traktCredentials = getTraktCredentialsInfo()
		self.traktIndicators = getTraktIndicatorsInfo()
		self.imdbCredentials = getSetting('imdb.user') != ''
		self.tmdbSessionID = getSetting('tmdb.session_id') != ''
		self.highlight_color = control.getHighlightColor()

	def root(self):
		self.addDirectoryItem(33046, 'movieNavigator', 'movies.png', 'DefaultMovies.png')
		self.addDirectoryItem(33047, 'tvNavigator', 'tvshows.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.anime'): self.addDirectoryItem('Anime', 'anime_Navigator', 'boxsets.png', 'DefaultFolder.png')
		if getMenuEnabled('mylists.widget'):
			self.addDirectoryItem(32003, 'mymovieNavigator', 'mymovies.png', 'DefaultVideoPlaylists.png')
			self.addDirectoryItem(32004, 'mytvNavigator', 'mytvshows.png', 'DefaultVideoPlaylists.png')
		if getMenuEnabled('navi.youtube'): self.addDirectoryItem('You Tube Videos', 'youtube', 'youtube.png', 'youtube.png')
		self.addDirectoryItem(32010, 'tools_searchNavigator', 'search.png', 'DefaultAddonsSearch.png')
		self.addDirectoryItem(32008, 'tools_toolNavigator', 'tools.png', 'tools.png')
		downloads = True if getSetting('downloads') == 'true' and (len(control.listDir(getSetting('movie.download.path'))[0]) > 0 or len(control.listDir(getSetting('tv.download.path'))[0]) > 0) else False
		if downloads: self.addDirectoryItem(32009, 'downloadNavigator', 'downloads.png', 'DefaultFolder.png')
		if getMenuEnabled('navi.prem.services'): self.addDirectoryItem('Premium Services', 'premiumNavigator', 'premium.png', 'DefaultFolder.png')
		if getMenuEnabled('navi.news'): self.addDirectoryItem(32013, 'tools_ShowNews', 'icon.png', 'DefaultAddonHelper.png', isFolder=False)
		if getMenuEnabled('navi.changelog'): self.addDirectoryItem(32014, 'tools_ShowChangelog&name=Umbrella', 'icon.png', 'DefaultAddonHelper.png', isFolder=False)
		self.endDirectory()

	def movies(self, lite=False):
		if getMenuEnabled('navi.movie.imdb.intheater'):
			self.addDirectoryItem(32421 if self.indexLabels else 32420, 'movies&url=theaters', 'imdb.png' if self.iconLogos else 'in-theaters.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.tmdb.nowplaying'):
			self.addDirectoryItem(32423 if self.indexLabels else 32422, 'tmdbmovies&url=tmdb_nowplaying', 'tmdb.png' if self.iconLogos else 'in-theaters.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.imdb.comingsoon'):
			self.addDirectoryItem(32215 if self.indexLabels else 32214, 'movies&url=imdb_comingsoon', 'imdb.png' if self.iconLogos else 'in-theaters.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.trakt.anticipated'):
			self.addDirectoryItem(32425 if self.indexLabels else 32424, 'movies&url=traktanticipated', 'trakt.png' if self.iconLogos else 'in-theaters.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.tmdb.upcoming'):
			self.addDirectoryItem(32427 if self.indexLabels else 32426, 'tmdbmovies&url=tmdb_upcoming', 'tmdb.png' if self.iconLogos else 'in-theaters.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.imdb.popular'):
			self.addDirectoryItem(32429 if self.indexLabels else 32428, 'movies&url=mostpopular', 'imdb.png' if self.iconLogos else 'most-popular.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.tmdb.popular'):
			self.addDirectoryItem(32431 if self.indexLabels else 32430, 'tmdbmovies&url=tmdb_popular', 'tmdb.png' if self.iconLogos else 'most-popular.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.trakt.popular'):
			self.addDirectoryItem(32433 if self.indexLabels else 32430, 'movies&url=traktpopular', 'trakt.png' if self.iconLogos else 'most-popular.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.imdb.boxoffice'):
			self.addDirectoryItem(32435 if self.indexLabels else 32434, 'movies&url=imdbboxoffice', 'imdb.png' if self.iconLogos else 'box-office.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.tmdb.boxoffice'):
			self.addDirectoryItem(32436 if self.indexLabels else 32434, 'tmdbmovies&url=tmdb_boxoffice', 'tmdb.png' if self.iconLogos else 'box-office.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.trakt.boxoffice'):
			self.addDirectoryItem(32437 if self.indexLabels else 32434, 'movies&url=traktboxoffice', 'trakt.png' if self.iconLogos else 'box-office.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.imdb.mostvoted'):
			self.addDirectoryItem(32439 if self.indexLabels else 32438, 'movies&url=mostvoted', 'imdb.png' if self.iconLogos else 'most-voted.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.tmdb.toprated'):
			self.addDirectoryItem(32441 if self.indexLabels else 32440, 'tmdbmovies&url=tmdb_toprated', 'tmdb.png' if self.iconLogos else 'most-voted.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.trakt.trending'):
			self.addDirectoryItem(32443 if self.indexLabels else 32442, 'movies&url=trakttrending', 'trakt.png' if self.iconLogos else 'trending.png', 'trending.png')
		if getMenuEnabled('navi.movie.trakt.recommended'):
			self.addDirectoryItem(32445 if self.indexLabels else 32444, 'movies&url=traktrecommendations', 'trakt.png' if self.iconLogos else 'highly-rated.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.imdb.featured'):
			self.addDirectoryItem(32447 if self.indexLabels else 32446, 'movies&url=featured', 'imdb.png' if self.iconLogos else 'movies.png', 'movies.png')
		if getMenuEnabled('navi.movie.imdb.oscarwinners'):
			self.addDirectoryItem(32452 if self.indexLabels else 32451, 'movies&url=oscars', 'imdb.png' if self.iconLogos else 'oscar-winners.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.imdb.oscarnominees'):
			self.addDirectoryItem(32454 if self.indexLabels else 32453, 'movies&url=oscarsnominees', 'imdb.png' if self.iconLogos else 'oscar-winners.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.imdb.genres'):
			self.addDirectoryItem(32456 if self.indexLabels else 32455, 'movieGenres&url=genre', 'imdb.png' if self.iconLogos else 'genres.png', 'DefaultGenre.png')
		if getMenuEnabled('navi.movie.tmdb.genres'):
			self.addDirectoryItem(32486 if self.indexLabels else 32455, 'movieGenres&url=tmdb_genre', 'tmdb.png' if self.iconLogos else 'genres.png', 'DefaultGenre.png')
		if getMenuEnabled('navi.movie.imdb.years'):
			self.addDirectoryItem(32458 if self.indexLabels else 32457, 'movieYears&url=year', 'imdb.png' if self.iconLogos else 'years.png', 'DefaultYear.png')
		if getMenuEnabled('navi.movie.tmdb.years'):
			self.addDirectoryItem(32485 if self.indexLabels else 32457, 'movieYears&url=tmdb_year', 'tmdb.png' if self.iconLogos else 'years.png', 'DefaultYear.png')
		if getMenuEnabled('navi.movie.imdb.people'):
			self.addDirectoryItem(32460 if self.indexLabels else 32459, 'moviePersons', 'imdb.png' if self.iconLogos else 'people.png', 'DefaultActor.png')
		if getMenuEnabled('navi.movie.imdb.languages'):
			self.addDirectoryItem(32462 if self.indexLabels else 32461, 'movieLanguages', 'imdb.png' if self.iconLogos else 'languages.png', 'DefaultAddonLanguage.png')
		if getMenuEnabled('navi.movie.imdb.certificates'):
			self.addDirectoryItem(32464 if self.indexLabels else 32463, 'movieCertificates&url=certification', 'imdb.png' if self.iconLogos else 'certificates.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.tmdb.certificates'):
			self.addDirectoryItem(32487 if self.indexLabels else 32463, 'movieCertificates&url=tmdb_certification', 'tmdb.png' if self.iconLogos else 'certificates.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.collections'):
			self.addDirectoryItem(32000, 'collections_Navigator', 'boxsets.png', 'DefaultSets.png')
		if getMenuEnabled('navi.movie.trakt.popularList'):
			self.addDirectoryItem(32417, 'movies_PublicLists&url=trakt_popularLists', 'trakt.png' if self.iconLogos else 'movies.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.trakt.trendingList'):
			self.addDirectoryItem(32418, 'movies_PublicLists&url=trakt_trendingLists', 'trakt.png' if self.iconLogos else 'movies.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.trakt.searchList'):
			self.addDirectoryItem(32419, 'movies_SearchLists&media_type=movies', 'trakt.png' if self.iconLogos else 'movies.png', 'DefaultMovies.png', isFolder=False)
		if not lite:
			if getMenuEnabled('mylists.widget'): self.addDirectoryItem(32003, 'mymovieliteNavigator', 'mymovies.png', 'DefaultMovies.png')
			self.addDirectoryItem(33044, 'moviePerson', 'imdb.png' if self.iconLogos else 'people-search.png', 'DefaultAddonsSearch.png', isFolder=False)
			self.addDirectoryItem(33042, 'movieSearch', 'trakt.png' if self.iconLogos else 'search.png', 'DefaultAddonsSearch.png')
		self.endDirectory()

	def mymovies(self, lite=False):
		self.accountCheck()
		self.addDirectoryItem(32039, 'movieUserlists', 'userlists.png', 'DefaultVideoPlaylists.png')
		if self.traktCredentials:
			if self.traktIndicators:
				self.addDirectoryItem(35308, 'moviesUnfinished&url=traktunfinished', 'trakt.png', 'trakt.png', queue=True)
				self.addDirectoryItem(32036, 'movies&url=trakthistory', 'trakt.png', 'trakt.png', queue=True)
			self.addDirectoryItem(32683, 'movies&url=traktwatchlist', 'trakt.png', 'trakt.png', queue=True, context=(32551, 'library_moviesToLibrary&url=traktwatchlist&name=traktwatchlist'))
			self.addDirectoryItem(32032, 'movies&url=traktcollection', 'trakt.png', 'trakt.png', queue=True, context=(32551, 'library_moviesToLibrary&url=traktcollection&name=traktcollection'))
			self.addDirectoryItem('My Liked Lists', 'movies_LikedLists', 'trakt.png', 'trakt.png', queue=True)
		if self.imdbCredentials: self.addDirectoryItem(32682, 'movies&url=imdbwatchlist', 'imdb.png', 'imdb.png', queue=True)
		if not lite:
			self.addDirectoryItem(32031, 'movieliteNavigator', 'movies.png', 'DefaultMovies.png')
			self.addDirectoryItem(33044, 'moviePerson', 'imdb.png' if self.iconLogos else 'people-search.png', 'DefaultAddonsSearch.png', isFolder=False)
			self.addDirectoryItem(33042, 'movieSearch', 'search.png' if self.iconLogos else 'search.png', 'DefaultAddonsSearch.png')
		self.endDirectory()

	def tvshows(self, lite=False):
		if getMenuEnabled('navi.originals'):
			self.addDirectoryItem(40077 if self.indexLabels else 40070, 'tvOriginals', 'tvmaze.png' if self.iconLogos else 'networks.png', 'DefaultNetwork.png')
		if getMenuEnabled('navi.tv.imdb.popular'):
			self.addDirectoryItem(32429 if self.indexLabels else 32428, 'tvshows&url=popular', 'imdb.png' if self.iconLogos else 'most-popular.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.tv.tmdb.popular'):
			self.addDirectoryItem(32431 if self.indexLabels else 32430, 'tmdbTvshows&url=tmdb_popular', 'tmdb.png' if self.iconLogos else 'most-popular.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.tv.trakt.popular'):
			self.addDirectoryItem(32433 if self.indexLabels else 32430, 'tvshows&url=traktpopular', 'trakt.png' if self.iconLogos else 'most-popular.png', 'DefaultTVShows.png', queue=True)
		if getMenuEnabled('navi.tv.imdb.mostvoted'):
			self.addDirectoryItem(32439 if self.indexLabels else 32438, 'tvshows&url=views', 'imdb.png' if self.iconLogos else 'most-voted.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.tv.tmdb.toprated'):
			self.addDirectoryItem(32441 if self.indexLabels else 32440, 'tmdbTvshows&url=tmdb_toprated', 'tmdb.png' if self.iconLogos else 'most-voted.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.tv.trakt.trending'):
			self.addDirectoryItem(32443 if self.indexLabels else 32442, 'tvshows&url=trakttrending', 'trakt.png' if self.iconLogos else 'trending.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.tv.imdb.highlyrated'):
			self.addDirectoryItem(32449 if self.indexLabels else 32448, 'tvshows&url=rating', 'imdb.png' if self.iconLogos else 'highly-rated.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.tv.trakt.recommended'):
			self.addDirectoryItem(32445 if self.indexLabels else 32444, 'tvshows&url=traktrecommendations', 'trakt.png' if self.iconLogos else 'highly-rated.png', 'DefaultTVShows.png', queue=True)
		if getMenuEnabled('navi.tv.imdb.genres'):
			self.addDirectoryItem(32456 if self.indexLabels else 32455, 'tvGenres&url=genre', 'imdb.png' if self.iconLogos else 'genres.png', 'DefaultGenre.png')
		if getMenuEnabled('navi.tv.tmdb.genres'):
			self.addDirectoryItem(32486 if self.indexLabels else 32455, 'tvGenres&url=tmdb_genre', 'tmdb.png' if self.iconLogos else 'genres.png', 'DefaultGenre.png')
		if getMenuEnabled('navi.tv.tvmaze.networks'):
			self.addDirectoryItem(32468 if self.indexLabels else 32469, 'tvNetworks', 'tmdb.png' if self.iconLogos else 'networks.png', 'DefaultNetwork.png')
		if getMenuEnabled('navi.tv.imdb.languages'):
			self.addDirectoryItem(32462 if self.indexLabels else 32461, 'tvLanguages', 'imdb.png' if self.iconLogos else 'languages.png', 'DefaultAddonLanguage.png')
		if getMenuEnabled('navi.tv.imdb.certificates'):
			self.addDirectoryItem(32464 if self.indexLabels else 32463, 'tvCertificates', 'imdb.png' if self.iconLogos else 'certificates.png', 'DefaultTVShows.png')
		# if getMenuEnabled('navi.tv.tmdb.certificates'):
		if getMenuEnabled('navi.tv.imdb.years'):
			self.addDirectoryItem(32458 if self.indexLabels else 32457, 'tvYears&url=year', 'imdb.png' if self.iconLogos else 'years.png', 'DefaultYear.png')
		if getMenuEnabled('navi.tv.tmdb.years'):
			self.addDirectoryItem(32485 if self.indexLabels else 32457, 'tvYears&url=tmdb_year', 'tmdb.png' if self.iconLogos else 'years.png', 'DefaultYear.png')
		if getMenuEnabled('navi.tv.tmdb.airingtoday'):
			self.addDirectoryItem(32467 if self.indexLabels else 32465, 'tmdbTvshows&url=tmdb_airingtoday', 'tmdb.png' if self.iconLogos else 'airing-today.png', 'DefaultRecentlyAddedEpisodes.png')
		if getMenuEnabled('navi.tv.imdb.airingtoday'):
			self.addDirectoryItem(32466 if self.indexLabels else 32465, 'tvshows&url=airing', 'imdb.png' if self.iconLogos else 'airing-today.png', 'DefaultRecentlyAddedEpisodes.png')
		if getMenuEnabled('navi.tv.tmdb.ontv'):
			self.addDirectoryItem(32472 if self.indexLabels else 32471, 'tmdbTvshows&url=tmdb_ontheair', 'tmdb.png' if self.iconLogos else 'new-tvshows.png', 'DefaultRecentlyAddedEpisodes.png')
		if getMenuEnabled('navi.tv.imdb.returningtvshows'):
			self.addDirectoryItem(32474 if self.indexLabels else 32473, 'tvshows&url=active', 'imdb.png' if self.iconLogos else 'returning-tvshows.png', 'DefaultRecentlyAddedEpisodes.png')
		if getMenuEnabled('navi.tv.imdb.newtvshows'):
			self.addDirectoryItem(32476 if self.indexLabels else 32475, 'tvshows&url=premiere', 'imdb.png' if self.iconLogos else 'new-tvshows.png', 'DefaultRecentlyAddedEpisodes.png')
		if getMenuEnabled('navi.tv.tvmaze.calendar'):
			self.addDirectoryItem(32450 if self.indexLabels else 32027, 'calendars', 'tvmaze.png' if self.iconLogos else 'calendar.png', 'DefaultYear.png')
		if getMenuEnabled('navi.tv.trakt.popularList'):
			self.addDirectoryItem(32417, 'tv_PublicLists&url=trakt_popularLists', 'trakt.png' if self.iconLogos else 'tvshows.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.tv.trakt.trendingList'):
			self.addDirectoryItem(32418, 'tv_PublicLists&url=trakt_trendingLists', 'trakt.png' if self.iconLogos else 'tvshows.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.tv.trakt.searchList'):
			self.addDirectoryItem(32419, 'tv_SearchLists&media_type=shows', 'trakt.png' if self.iconLogos else 'tvshows.png', 'DefaultMovies.png', isFolder=False)
		if not lite:
			if getMenuEnabled('mylists.widget'): self.addDirectoryItem(32004, 'mytvliteNavigator', 'mytvshows.png', 'DefaultTVShows.png')
			self.addDirectoryItem(33045, 'tvPerson', 'imdb.png' if self.iconLogos else 'people-search.png', 'DefaultAddonsSearch.png', isFolder=False)
			self.addDirectoryItem(33043, 'tvSearch', 'trakt.png' if self.iconLogos else 'search.png', 'DefaultAddonsSearch.png')
		self.endDirectory()

	def mytvshows(self, lite=False):
		self.accountCheck()
		self.addDirectoryItem(32040, 'tvUserlists', 'userlists.png', 'DefaultVideoPlaylists.png')
		if self.traktCredentials:
			if self.traktIndicators:
				self.addDirectoryItem(35308, 'episodesUnfinished&url=traktunfinished', 'trakt.png', 'trakt.png', queue=True)
				self.addDirectoryItem(32037, 'calendar&url=progress', 'trakt.png', 'trakt.png', queue=True)
				self.addDirectoryItem(32019, 'upcomingProgress&url=progress', 'trakt.png', 'trakt.png', queue=True)
				self.addDirectoryItem(32202, 'calendar&url=mycalendarRecent', 'trakt.png', 'trakt.png', queue=True)
				self.addDirectoryItem(32203, 'calendar&url=mycalendarUpcoming', 'trakt.png', 'trakt.png', queue=True)
				self.addDirectoryItem(32204, 'calendar&url=mycalendarPremiers', 'trakt.png', 'trakt.png', queue=True)
				self.addDirectoryItem(32036, 'calendar&url=trakthistory', 'trakt.png', 'trakt.png', queue=True)
			self.addDirectoryItem(32683, 'tvshows&url=traktwatchlist', 'trakt.png', 'trakt.png', context=(32551, 'library_tvshowsToLibrary&url=traktwatchlist&name=traktwatchlist'))
			self.addDirectoryItem(32032, 'tvshows&url=traktcollection', 'trakt.png', 'trakt.png', context=(32551, 'library_tvshowsToLibrary&url=traktcollection&name=traktcollection'))
			self.addDirectoryItem('My Liked Lists', 'shows_LikedLists', 'trakt.png', 'trakt.png', queue=True)
		if self.imdbCredentials: self.addDirectoryItem(32682, 'tvshows&url=imdbwatchlist', 'imdb.png', 'imdb.png')
		if not lite:
			self.addDirectoryItem(32031, 'tvliteNavigator', 'tvshows.png', 'DefaultTVShows.png')
			self.addDirectoryItem(33045, 'tvPerson', 'imdb.png' if self.iconLogos else 'people-search.png', 'DefaultAddonsSearch.png', isFolder=False)
			self.addDirectoryItem(33043, 'tvSearch', 'trakt.png' if self.iconLogos else 'search.png', 'DefaultAddonsSearch.png')
		self.endDirectory()

	def anime(self, lite=False):
		self.addDirectoryItem(32001, 'anime_Movies&url=anime', 'movies.png', 'DefaultMovies.png')
		self.addDirectoryItem(32002, 'anime_TVshows&url=anime', 'tvshows.png', 'DefaultTVShows.png')
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

	def tools(self):
		if self.traktCredentials: self.addDirectoryItem(35057, 'tools_traktToolsNavigator', 'tools.png', 'DefaultAddonService.png', isFolder=True)
		self.addDirectoryItem(32510, 'cache_Navigator', 'tools.png', 'DefaultAddonService.png', isFolder=True)
		self.addDirectoryItem(32609, 'tools_openMyAccount', 'MyAccounts.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(32506, 'tools_contextUmbrellaSettings', 'icon.png', 'DefaultAddonProgram.png', isFolder=False)
		#-- Providers - 4
		self.addDirectoryItem(32651, 'tools_umbrellascrapersSettings', 'umbrellascrapers.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(32523, 'tools_loggingNavigator', 'tools.png', 'DefaultAddonService.png')
		self.addDirectoryItem(32083, 'tools_cleanSettings', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		#-- General - 0
		self.addDirectoryItem(32043, 'tools_openSettings&query=0.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		#-- Navigation - 1
		self.addDirectoryItem(32362, 'tools_openSettings&query=1.1', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		#-- Playback - 3
		self.addDirectoryItem(32045, 'tools_openSettings&query=3.1', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		#-- Accounts - 7
		self.addDirectoryItem(32044, 'tools_openSettings&query=7.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		#-- Downloads - 10
		self.addDirectoryItem(32048, 'tools_openSettings&query=10.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		#-- Subtitles - 11
		self.addDirectoryItem(32046, 'tools_openSettings&query=11.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(32556, 'library_Navigator', 'tools.png', 'DefaultAddonService.png', isFolder=True)
		self.addDirectoryItem(32049, 'tools_viewsNavigator', 'tools.png', 'DefaultAddonService.png', isFolder=True)
		self.addDirectoryItem(32361, 'tools_resetViewTypes', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def traktTools(self):
		self.addDirectoryItem(35058, 'shows_traktHiddenManager', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(35059, 'movies_traktUnfinishedManager', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(35060, 'episodes_traktUnfinishedManager', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(35061, 'movies_traktWatchListManager', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(35062, 'shows_traktWatchListManager', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(35063, 'movies_traktCollectionManager', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(35064, 'shows_traktCollectionManager', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(35065, 'tools_traktLikedListManager', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(35066, 'tools_forceTraktSync', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def loggingNavigator(self):
		self.addDirectoryItem(32524, 'tools_viewLogFile&name=Umbrella', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32525, 'tools_clearLogFile', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32526, 'tools_ShowChangelog&name=Umbrella', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32527, 'tools_uploadLogFile&name=Umbrella', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32528, 'tools_viewLogFile&name=MyAccounts', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32529, 'tools_ShowChangelog&name=MyAccounts', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32530, 'tools_viewLogFile&name=umbrellascrapers', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32531, 'tools_ShowChangelog&name=umbrellascrapers', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32532, 'tools_viewLogFile&name=Kodi', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32198, 'tools_uploadLogFile&name=Kodi', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.endDirectory()

	def cf(self):
		self.addDirectoryItem(32610, 'cache_clearAll', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(32611, 'cache_clearSources', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(32612, 'cache_clearMeta', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(32613, 'cache_clearCache', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(32614, 'cache_clearSearch', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(32615, 'cache_clearBookmarks', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def library(self): # -- Library - 9
		self.addDirectoryItem(32557, 'tools_openSettings&query=9.0', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32558, 'library_update', 'library_update.png', 'DefaultAddonLibrary.png', isFolder=False)
		self.addDirectoryItem(32676, 'library_clean', 'library_update.png', 'DefaultAddonLibrary.png', isFolder=False)
		self.addDirectoryItem(32559, getSetting('library.movie'), 'movies.png', 'DefaultMovies.png', isAction=False)
		self.addDirectoryItem(32560, getSetting('library.tv'), 'tvshows.png', 'DefaultTVShows.png', isAction=False)
		if self.traktCredentials:
			self.addDirectoryItem(32561, 'library_moviesToLibrary&url=traktcollection&name=traktcollection', 'trakt.png', 'DefaultMovies.png', isFolder=False)
			self.addDirectoryItem(32562, 'library_moviesToLibrary&url=traktwatchlist&name=traktwatchlist', 'trakt.png', 'DefaultMovies.png', isFolder=False)
			self.addDirectoryItem(32672, 'library_moviesListToLibrary&url=traktlists', 'trakt.png', 'DefaultMovies.png', isFolder=False)
			self.addDirectoryItem(32673, 'library_moviesListToLibrary&url=traktlikedlists', 'trakt.png', 'DefaultMovies.png', isFolder=False)
		if self.tmdbSessionID:
			self.addDirectoryItem('TMDb: Import Movie Watchlist...', 'library_moviesToLibrary&url=tmdb_watchlist&name=tmdb_watchlist', 'tmdb.png', 'DefaultMovies.png', isFolder=False)
			self.addDirectoryItem('TMDb: Import Movie Favorites...', 'library_moviesToLibrary&url=tmdb_favorites&name=tmdb_favorites', 'tmdb.png', 'DefaultMovies.png', isFolder=False)
			self.addDirectoryItem('TMDb: Import Movie User list...', 'library_moviesListToLibrary&url=tmdb_userlists', 'tmdb.png', 'DefaultMovies.png', isFolder=False)
		if self.traktCredentials:
			self.addDirectoryItem(32563, 'library_tvshowsToLibrary&url=traktcollection&name=traktcollection', 'trakt.png', 'DefaultTVShows.png', isFolder=False)
			self.addDirectoryItem(32564, 'library_tvshowsToLibrary&url=traktwatchlist&name=traktwatchlist', 'trakt.png', 'DefaultTVShows.png', isFolder=False)
			self.addDirectoryItem(32674, 'library_tvshowsListToLibrary&url=traktlists', 'trakt.png', 'DefaultMovies.png', isFolder=False)
			self.addDirectoryItem(32675, 'library_tvshowsListToLibrary&url=traktlikedlists', 'trakt.png', 'DefaultMovies.png', isFolder=False)
		if self.tmdbSessionID:
			self.addDirectoryItem('TMDb: Import TV Watchlist...', 'library_tvshowsToLibrary&url=tmdb_watchlist&name=tmdb_watchlist', 'tmdb.png', 'DefaultMovies.png', isFolder=False)
			self.addDirectoryItem('TMDb: Import TV Favorites...', 'library_tvshowsToLibrary&url=tmdb_favorites&name=tmdb_favorites', 'tmdb.png', 'DefaultMovies.png', isFolder=False)
			self.addDirectoryItem('TMDb: Import TV User list...', 'library_tvshowsListToLibrary&url=tmdb_userlists', 'tmdb.png', 'DefaultMovies.png', isFolder=False)
		self.endDirectory()

	def downloads(self):
		movie_downloads = getSetting('movie.download.path')
		tv_downloads = getSetting('tv.download.path')
		if len(control.listDir(movie_downloads)[0]) > 0: self.addDirectoryItem(32001, movie_downloads, 'movies.png', 'DefaultMovies.png', isAction=False)
		if len(control.listDir(tv_downloads)[0]) > 0: self.addDirectoryItem(32002, tv_downloads, 'tvshows.png', 'DefaultTVShows.png', isAction=False)
		self.endDirectory()

	def premium_services(self):
		if getMenuEnabled('navi.alldebrid'): self.addDirectoryItem(40059, 'ad_ServiceNavigator', 'alldebrid.png', 'alldebrid.png')
		if getMenuEnabled('navi.easynews'): self.addDirectoryItem(32327, 'en_ServiceNavigator', 'easynews.png', 'easynews.png')
		if getMenuEnabled('navi.furk'): self.addDirectoryItem('Furk.net', 'furk_ServiceNavigator', 'furk.png', 'furk.png')
		if getMenuEnabled('navi.premiumize'): self.addDirectoryItem(40057, 'pm_ServiceNavigator', 'premiumize.png', 'premiumize.png')
		if getMenuEnabled('navi.realdebrid'): self.addDirectoryItem(40058, 'rd_ServiceNavigator', 'realdebrid.png', 'realdebrid.png')
		self.endDirectory()

	def alldebrid_service(self):
		if getSetting('alldebrid.token'):
			self.addDirectoryItem('All-Debrid: Cloud Storage', 'ad_CloudStorage', 'alldebrid.png', 'DefaultAddonService.png')
			self.addDirectoryItem('All-Debrid: Transfers', 'ad_Transfers', 'alldebrid.png', 'DefaultAddonService.png')
			self.addDirectoryItem('All-Debrid: Account Info', 'ad_AccountInfo', 'alldebrid.png', 'DefaultAddonService.png', isFolder=False)
		else:
			self.addDirectoryItem('[I]Please visit My Accounts for setup[/I]', 'tools_openMyAccount&amp;query=1.4', 'alldebrid.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def easynews_service(self):
		if getSetting('easynews.username'):
			self.addDirectoryItem('Easy News: Search', 'en_Search', 'search.png', 'DefaultAddonsSearch.png')
			self.addDirectoryItem('Easy News: Account Info', 'en_AccountInfo', 'easynews.png', 'DefaultAddonService.png', isFolder=False)
		else:
			self.addDirectoryItem('[I]Please visit My Accounts for setup[/I]', 'tools_openMyAccount&amp;query=3.5', 'easynews.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def furk_service(self):
		if getSetting('furk.api'):
			self.addDirectoryItem('Furk: Search', 'furk_Search', 'search.png', 'DefaultAddonsSearch.png')
			self.addDirectoryItem('Furk: User Files', 'furk_UserFiles', 'furk.png', 'DefaultAddonService.png')
			self.addDirectoryItem('Furk: Account Info', 'furk_AccountInfo', 'furk.png', 'DefaultAddonService.png', isFolder=False)
		else:
			self.addDirectoryItem('[I]Please visit My Accounts for setup[/I]', 'tools_openMyAccount&amp;query=3.5', 'furk.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def premiumize_service(self):
		if getSetting('premiumize.token'):
			self.addDirectoryItem('Premiumize: My Files', 'pm_MyFiles', 'premiumize.png', 'DefaultAddonService.png')
			self.addDirectoryItem('Premiumize: Transfers', 'pm_Transfers', 'premiumize.png', 'DefaultAddonService.png')
			self.addDirectoryItem('Premiumize: Account Info', 'pm_AccountInfo', 'premiumize.png', 'DefaultAddonService.png', isFolder=False)
		else:
			self.addDirectoryItem('[I]Please visit My Accounts for setup[/I]', 'tools_openMyAccount&amp;query=1.11', 'premiumize.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def realdebrid_service(self):
		if getSetting('realdebrid.token'):
			self.addDirectoryItem('Real-Debrid: Torrent Transfers', 'rd_UserTorrentsToListItem', 'realdebrid.png', 'DefaultAddonService.png')
			self.addDirectoryItem('Real-Debrid: My Downloads', 'rd_MyDownloads&query=1', 'realdebrid.png', 'DefaultAddonService.png')
			self.addDirectoryItem('Real-Debrid: Account Info', 'rd_AccountInfo', 'realdebrid.png', 'DefaultAddonService.png', isFolder=False )
		else:
			self.addDirectoryItem('[I]Please visit My Accounts for setup[/I]', 'tools_openMyAccount&amp;query=1.18', 'realdebrid.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def search(self):
		self.addDirectoryItem(33042, 'movieSearch', 'trakt.png' if self.iconLogos else 'search.png', 'DefaultAddonsSearch.png')
		self.addDirectoryItem(33043, 'tvSearch', 'trakt.png' if self.iconLogos else 'search.png', 'DefaultAddonsSearch.png')
		self.addDirectoryItem(33044, 'moviePerson', 'imdb.png' if self.iconLogos else 'people-search.png', 'DefaultAddonsSearch.png', isFolder=False)
		self.addDirectoryItem(33045, 'tvPerson', 'imdb.png' if self.iconLogos else 'people-search.png', 'DefaultAddonsSearch.png', isFolder=False)
		self.endDirectory()

	def views(self):
		try:
			from sys import argv # some functions throw invalid handle -1 unless this is imported here.
			syshandle = int(argv[1])
			control.hide()
			items = [(getLS(32001), 'movies'), (getLS(32002), 'tvshows'), (getLS(32054), 'seasons'), (getLS(32326), 'episodes') ]
			select = control.selectDialog([i[0] for i in items], getLS(32049))
			if select == -1: return
			content = items[select][1]
			title = getLS(32059)
			url = 'plugin://plugin.video.umbrella/?action=tools_addView&content=%s' % content
			poster, banner, fanart = control.addonPoster(), control.addonBanner(), control.addonFanart()
			item = control.item(label=title, offscreen=True)
			item.setInfo(type='video', infoLabels = {'title': title})
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
		if not self.traktCredentials and not self.imdbCredentials:
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

	def addDirectoryItem(self, name, query, poster, icon, context=None, queue=False, isAction=True, isFolder=True, isPlayable=False, isSearch=False, table=''):
		try:
			from sys import argv # some functions like ActivateWindow() throw invalid handle less this is imported here.
			if isinstance(name, int): name = getLS(name)
			url = 'plugin://plugin.video.umbrella/?action=%s' % query if isAction else query
			poster = control.joinPath(self.artPath, poster) if self.artPath else icon
			if not icon.startswith('Default'): icon = control.joinPath(self.artPath, icon)
			cm = []
			queueMenu = getLS(32065)
			if queue: cm.append((queueMenu, 'RunPlugin(plugin://plugin.video.umbrella/?action=playlist_QueueItem)'))
			if context: cm.append((getLS(context[0]), 'RunPlugin(plugin://plugin.video.umbrella/?action=%s)' % context[1]))
			if isSearch: cm.append(('Clear Search Phrase', 'RunPlugin(plugin://plugin.video.umbrella/?action=cache_clearSearchPhrase&source=%s&name=%s)' % (table, quote_plus(name))))
			cm.append(('[COLOR red]Umbrella Settings[/COLOR]', 'RunPlugin(plugin://plugin.video.umbrella/?action=tools_openSettings)'))
			item = control.item(label=name, offscreen=True)
			item.addContextMenuItems(cm)
			if isPlayable: item.setProperty('IsPlayable', 'true')
			item.setArt({'icon': icon, 'poster': poster, 'thumb': poster, 'fanart': control.addonFanart(), 'banner': poster})
			item.setInfo(type='video', infoLabels={'plot': name})
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