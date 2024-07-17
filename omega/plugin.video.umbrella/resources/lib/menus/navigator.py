# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from sys import exit as sysexit
from urllib.parse import quote_plus
from resources.lib.modules import control
from resources.lib.modules.trakt import getTraktCredentialsInfo, getTraktIndicatorsInfo
from resources.lib.modules import favourites
from json import loads as jsloads

getLS = control.lang
getSetting = control.setting
getMenuEnabled = control.getMenuEnabled
decades = ['1930-1939', '1940-1949','1950-1959', '1960-1969', '1970-1979', '1980-1989', '1990-1999', '2000-2009', '2010-2019','2020-2029']


class Navigator:
	def __init__(self):
		self.artPath = control.artPath()
		self.iconLogos = getSetting('icon.logos') != 'Traditional'
		self.indexLabels = getSetting('index.labels') == 'true'
		self.traktCredentials = getTraktCredentialsInfo()
		self.traktIndicators = getTraktIndicatorsInfo()
		self.imdbCredentials = getSetting('imdbuser') != ''
		self.simkltoken = getSetting('simkltoken') != ''
		self.tmdbSessionID = getSetting('tmdb.sessionid') != ''
		self.reuselanguageinv = getSetting('reuse.languageinvoker') == 'true'
		self.highlight_color = getSetting('highlight.color')
		self.hasLibMovies = len(jsloads(control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": { "limits": { "start" : 0, "end": 1 }, "properties" : ["title", "genre", "uniqueid", "art", "rating", "thumbnail", "playcount", "file"] }, "id": "1"}'))['result']['movies']) > 0
		self.useContainerTitles = getSetting('enable.containerTitles') == 'true'
		self.favoriteMovie = favourites.checkForFavourites(content='movies')
		self.favoriteTVShows = favourites.checkForFavourites(content='tvshows')
		self.favoriteEpisodes = favourites.checkForFavourites(content='episode')

	def root(self):
		if getMenuEnabled('navi.searchMovies'):self.addDirectoryItem(33042, 'movieSearch&folderName=%s' % quote_plus(getLS(33042)), 'trakt.png' if self.iconLogos else 'searchmovies.png', 'DefaultAddonsSearch.png')
		if getMenuEnabled('navi.searchTVShows'):self.addDirectoryItem(33043, 'tvSearch&folderName=%s' % quote_plus(getLS(33043)), 'trakt.png' if self.iconLogos else 'searchtv.png', 'DefaultAddonsSearch.png')
		self.addDirectoryItem(33046, 'movieNavigator&folderName=%s' % quote_plus(getLS(33046)), 'movies.png', 'DefaultMovies.png')
		self.addDirectoryItem(33047, 'tvNavigator&folderName=%s' % quote_plus(getLS(33047)), 'tvshows.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.anime'): self.addDirectoryItem('Anime', 'anime_Navigator&folderName=%s' % quote_plus('Anime'), 'boxsets.png', 'DefaultFolder.png')
		if getMenuEnabled('mylists.widget'):
			self.addDirectoryItem(32003, 'mymovieNavigator&folderName=%s' % quote_plus(getLS(32003)), 'mymovies.png', 'DefaultVideoPlaylists.png')
			self.addDirectoryItem(32004, 'mytvNavigator&folderName=%s' % quote_plus(getLS(32004)), 'mytvshows.png', 'DefaultVideoPlaylists.png')
		if getMenuEnabled('navi.youtube'): self.addDirectoryItem('YouTube Videos', 'youtube&folderName=%s' % quote_plus('YouTube Videos'), 'youtube.png', 'youtube.png')
		self.addDirectoryItem(32010, 'tools_searchNavigator&folderName=%s' % quote_plus(getLS(32010)), 'search.png', 'DefaultAddonsSearch.png')
		self.addDirectoryItem(32008, 'tools_toolNavigator&folderName=%s' % quote_plus(getLS(32008)), 'tools.png', 'tools.png')
		downloads = True if getSetting('downloads') == 'true' and (len(control.listDir(getSetting('movie.download.path'))[0]) > 0 or len(control.listDir(getSetting('tv.download.path'))[0]) > 0) else False
		if downloads: self.addDirectoryItem(32009, 'downloadNavigator&folderName=%s' % quote_plus(getLS(32009)), 'downloads.png', 'DefaultFolder.png')
		favorite = favourites.checkForFavourites()
		if favorite: self.addDirectoryItem(40464, 'favouriteNavigator&folderName=%s' % quote_plus(getLS(40464)), 'highly-rated.png', 'DefaultFolder.png')
		if getMenuEnabled('navi.prem.services'): self.addDirectoryItem('Premium Services', 'premiumNavigator&folderName=%s'% quote_plus('Premium Services'), 'premium.png', 'DefaultFolder.png')
		if getMenuEnabled('navi.changelog'): self.addDirectoryItem(32014, 'tools_ShowChangelog&name=Umbrella', 'changelog.png', 'DefaultAddonHelper.png', isFolder=False)
		self.endDirectory()

	def movies(self, lite=False, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		if getMenuEnabled('navi.movie.tmdb.nowplaying'):
			self.addDirectoryItem(32423 if self.indexLabels else 32422, 'tmdbmovies&url=tmdb_nowplaying&folderName=%s' % quote_plus(getLS(32423 if self.indexLabels else 32422)), 'tmdb.png' if self.iconLogos else 'in-theaters.png', 'DefaultMovies.png')
		#if getMenuEnabled('navi.movie.imdb.comingsoon'):
			#self.addDirectoryItem(32215 if self.indexLabels else 32214, 'movies&url=imdb_comingsoon&folderName=%s' % getLS(32215 if self.indexLabels else 32214), 'imdb.png' if self.iconLogos else 'in-theaters.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.trakt.anticipated'):
			self.addDirectoryItem(32425 if self.indexLabels else 32424, 'movies&url=traktanticipated&folderName=%s' % quote_plus(getLS(32425 if self.indexLabels else 32424)), 'trakt.png' if self.iconLogos else 'in-theaters.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.tmdb.upcoming'):
			self.addDirectoryItem(32427 if self.indexLabels else 32426, 'tmdbmovies&url=tmdb_upcoming&folderName=%s' % quote_plus(getLS(32427 if self.indexLabels else 32426)), 'tmdb.png' if self.iconLogos else 'in-theaters.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.tmdb.discoverreleased'):
			self.addDirectoryItem(40268 if self.indexLabels else 40269, 'tmdbmovies&url=tmdb_discovery_released&folderName=%s' % quote_plus(getLS(40268 if self.indexLabels else 40269)), 'tmdb.png' if self.iconLogos else 'trending.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.tmdb.discoverthismonth'):
			self.addDirectoryItem(40410 if self.indexLabels else 40411, 'tmdbmovies&url=tmdb_discovery_this_month&folderName=%s' % quote_plus(getLS(40410 if self.indexLabels else 40411)), 'tmdb.png' if self.iconLogos else 'trending.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.tmdb.discoverthismonthreleased'):
			self.addDirectoryItem(40412 if self.indexLabels else 40413, 'tmdbmovies&url=tmdb_discovery_this_month_released&folderName=%s' % quote_plus(getLS(40412 if self.indexLabels else 40413)), 'tmdb.png' if self.iconLogos else 'trending.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.getdvdrelease'):
			self.addDirectoryItem(40474 if self.indexLabels else 40475, 'dvdReleaseList&folderName=%s' % quote_plus(getLS(40474 if self.indexLabels else 40475)), 'tmdb.png' if self.iconLogos else 'trending.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.imdb.popular'):
			self.addDirectoryItem(32429 if self.indexLabels else 32428, 'movies&url=mostpopular&folderName=%s' % quote_plus(getLS(32429 if self.indexLabels else 32428)), 'imdb.png' if self.iconLogos else 'most-popular.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.tmdb.popular'):
			self.addDirectoryItem(32431 if self.indexLabels else 32430, 'tmdbmovies&url=tmdb_popular&folderName=%s' % quote_plus(getLS(32431 if self.indexLabels else 32430)), 'tmdb.png' if self.iconLogos else 'most-popular.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.trakt.popular'):
			self.addDirectoryItem(32433 if self.indexLabels else 32430, 'movies&url=traktpopular&folderName=%s' % quote_plus(getLS(32433 if self.indexLabels else 32430)), 'trakt.png' if self.iconLogos else 'most-popular.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.imdb.boxoffice'):
			self.addDirectoryItem(32435 if self.indexLabels else 32434, 'movies&url=imdbboxoffice&folderName=%s' % quote_plus(getLS(32435 if self.indexLabels else 32434)), 'imdb.png' if self.iconLogos else 'box-office.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.tmdb.boxoffice'):
			self.addDirectoryItem(32436 if self.indexLabels else 32434, 'tmdbmovies&url=tmdb_boxoffice&folderName=%s' % quote_plus(getLS(32436 if self.indexLabels else 32434)), 'tmdb.png' if self.iconLogos else 'box-office.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.trakt.boxoffice'):
			self.addDirectoryItem(32437 if self.indexLabels else 32434, 'movies&url=traktboxoffice&folderName=%s' % quote_plus(getLS(32437 if self.indexLabels else 32434)), 'trakt.png' if self.iconLogos else 'box-office.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.imdb.mostvoted'):
			self.addDirectoryItem(32439 if self.indexLabels else 32438, 'movies&url=mostvoted&folderName=%s' % quote_plus(getLS(32439 if self.indexLabels else 32438)), 'imdb.png' if self.iconLogos else 'most-voted.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.tmdb.toprated'):
			self.addDirectoryItem(32441 if self.indexLabels else 32440, 'tmdbmovies&url=tmdb_toprated&folderName=%s' %quote_plus( getLS(32441 if self.indexLabels else 32440)), 'tmdb.png' if self.iconLogos else 'most-voted.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.trakt.trending'):
			self.addDirectoryItem(32443 if self.indexLabels else 32442, 'movies&url=trakttrending&folderName=%s' % quote_plus(getLS(32443 if self.indexLabels else 32442)), 'trakt.png' if self.iconLogos else 'trending.png', 'trending.png')
		if getMenuEnabled('navi.movie.trakt.trendingrecent'):
			self.addDirectoryItem(40388 if self.indexLabels else 40389, 'movies&url=trakttrending_recent&folderName=%s' % quote_plus(getLS(40388 if self.indexLabels else 40389)), 'trakt.png' if self.iconLogos else 'trending.png', 'trending.png')
		if self.simkltoken:
			if getMenuEnabled('navi.movie.simkl.trendingtoday'):
				self.addDirectoryItem(40350 if self.indexLabels else 40351, 'simklMovies&url=simkltrendingtoday&folderName=%s' % quote_plus(getLS(40350 if self.indexLabels else 40351)), 'simkl.png' if self.iconLogos else 'trending.png', 'trending.png')
			if getMenuEnabled('navi.movie.simkl.trendingweek'):
				self.addDirectoryItem(40352 if self.indexLabels else 40353, 'simklMovies&url=simkltrendingweek&folderName=%s' % quote_plus(getLS(40352 if self.indexLabels else 40353)), 'simkl.png' if self.iconLogos else 'trending.png', 'trending.png')
			if getMenuEnabled('navi.movie.simkl.trendingmonth'):
				self.addDirectoryItem(40354 if self.indexLabels else 40355, 'simklMovies&url=simkltrendingmonth&folderName=%s' % quote_plus(getLS(40354 if self.indexLabels else 40355)), 'simkl.png' if self.iconLogos else 'trending.png', 'trending.png')
		if getMenuEnabled('navi.movie.tmdb.trendingday'):
			self.addDirectoryItem(40330 if self.indexLabels else 32442, 'movies&url=tmdbrecentday&folderName=%s' % quote_plus(getLS(40330 if self.indexLabels else 32442)), 'tmdb.png' if self.iconLogos else 'trending.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.movie.tmdb.trendingweek'):
			self.addDirectoryItem(40331 if self.indexLabels else 32442, 'movies&url=tmdbrecentweek&folderName=%s' % quote_plus(getLS(40331 if self.indexLabels else 32442)), 'tmdb.png' if self.iconLogos else 'trending.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.movie.trakt.recommended'):
			self.addDirectoryItem(32445 if self.indexLabels else 32444, 'movies&url=traktrecommendations&folderName=%s' % quote_plus(getLS(32445 if self.indexLabels else 32444)), 'trakt.png' if self.iconLogos else 'highly-rated.png', 'DefaultMovies.png')
		if self.hasLibMovies and getMenuEnabled('navi.movie.lib.similar'):
			self.addDirectoryItem(40392 if self.indexLabels else 40392, 'moviesimilarFromLibrary&folderName=%s' % quote_plus(getLS(40392 if self.indexLabels else 40392)), 'most-popular.png' if self.iconLogos else 'most-popular.png', 'DefaultMovies.png')
		if self.hasLibMovies and getMenuEnabled('navi.movie.lib.recommended'):	
			self.addDirectoryItem(40393 if self.indexLabels else 40393, 'movierecommendedFromLibrary&folderName=%s' % quote_plus(getLS(40393 if self.indexLabels else 40393)), 'featured.png' if self.iconLogos else 'featured.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.trakt.recentlywatched'):
			self.addDirectoryItem(40255 if self.indexLabels else 40256, 'movies&url=traktbasedonrecent&folderName=%s' % quote_plus(getLS(40255 if self.indexLabels else 40256)), 'trakt.png' if self.iconLogos else 'years.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.trakt.traktsimilar'):
			self.addDirectoryItem(40260 if self.indexLabels else 40261, 'movies&url=traktbasedonsimilar&folderName=%s' % quote_plus(getLS(40260 if self.indexLabels else 40261)), 'trakt.png' if self.iconLogos else 'years.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.imdb.featured'):
			self.addDirectoryItem(32447 if self.indexLabels else 32446, 'movies&url=featured&folderName=%s' % quote_plus(getLS(32447 if self.indexLabels else 32446)), 'imdb.png' if self.iconLogos else 'movies.png', 'movies.png')
		if getMenuEnabled('navi.movie.imdb.oscarnominees'):
			self.addDirectoryItem(32454 if self.indexLabels else 32453, 'movies&url=oscarsnominees', 'imdb.png' if self.iconLogos else 'oscar-winners.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.tmdb.genres'):
			self.addDirectoryItem(32486 if self.indexLabels else 32455, 'movieGenres&url=tmdb_genre&folderName=%s' % quote_plus(getLS(32486 if self.indexLabels else 32455)), 'tmdb.png' if self.iconLogos else 'genres.png', 'DefaultGenre.png')
		if getMenuEnabled('navi.movie.trakt.genres'):
			self.addDirectoryItem(40493 if self.indexLabels else 32455, 'movieGenres&url=trakt_movie_genre&folderName=%s' % quote_plus(getLS(40493 if self.indexLabels else 32455)), 'trakt.png' if self.iconLogos else 'genres.png', 'DefaultGenre.png')
		if getMenuEnabled('navi.movie.imdb.years'):
			self.addDirectoryItem(32458 if self.indexLabels else 32457, 'movieYears&url=year&folderName=%s' % quote_plus(getLS(32458 if self.indexLabels else 32457)), 'imdb.png' if self.iconLogos else 'years.png', 'DefaultYear.png')
		if getMenuEnabled('navi.movie.imdb.languages'):
			self.addDirectoryItem(32462 if self.indexLabels else 32461, 'movieLanguages&folderName=%s' % quote_plus(getLS(32462 if self.indexLabels else 32461)), 'imdb.png' if self.iconLogos else 'languages.png', 'DefaultAddonLanguage.png')
		if getMenuEnabled('navi.movie.tmdb.years'):
			self.addDirectoryItem(32485 if self.indexLabels else 32457, 'movieYears&url=tmdb_year&folderName=%s' % quote_plus(getLS(32485 if self.indexLabels else 32457)), 'tmdb.png' if self.iconLogos else 'years.png', 'DefaultYear.png')
		if getMenuEnabled('navi.movie.tmdb.certificates'):
			self.addDirectoryItem(32487 if self.indexLabels else 32463, 'movieCertificates&url=tmdb_certification&folderName=%s' % quote_plus(getLS(32487 if self.indexLabels else 32463)), 'tmdb.png' if self.iconLogos else 'certificates.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.collections'):
			self.addDirectoryItem(32000, 'collections_Navigator&folderName=%s' % quote_plus(getLS(32000)), 'boxsets.png', 'DefaultSets.png')
		if getMenuEnabled('navi.movie.mdblist.topList') and getSetting('mdblist.api') != '':
			self.addDirectoryItem(40084, 'mdbTopListMovies&folderName=%s' % quote_plus(getLS(40084)), 'mdblist.png' if self.iconLogos else 'movies.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.trakt.popularList'):
			self.addDirectoryItem(32417, 'movies_PublicLists&url=trakt_popularLists&folderName=%s' % quote_plus(getLS(32417)), 'trakt.png' if self.iconLogos else 'movies.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.trakt.trendingList'):
			self.addDirectoryItem(32418, 'movies_PublicLists&url=trakt_trendingLists&folderName=%s' % quote_plus(getLS(32418)), 'trakt.png' if self.iconLogos else 'movies.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.trakt.searchList'):
			self.addDirectoryItem(32419, 'movies_SearchLists&media_type=movies', 'trakt.png' if self.iconLogos else 'movies.png', 'DefaultMovies.png', isFolder=False)
		#self.addDirectoryItem('Favorite Movies', 'movies_favorites', 'trakt.png', 'DefaultMovies.png')
		if not lite:
			if getMenuEnabled('mylists.widget'): self.addDirectoryItem(32003, 'mymovieliteNavigator&folderName=%s' % quote_plus(getLS(32003)), 'mymovies.png', 'DefaultMovies.png')
			if self.favoriteMovie:
				self.addDirectoryItem(getLS(40465), 'getFavouritesMovies&url=favourites_movies&folderName=%s' % (quote_plus(getLS(40465))), 'movies.png', 'DefaultMovies.png')
			self.addDirectoryItem(33044, 'moviePerson&folderName=%s' % quote_plus(getLS(33044)), 'imdb.png' if self.iconLogos else 'people-search.png', 'DefaultAddonsSearch.png', isFolder=False)
			self.addDirectoryItem(33042, 'movieSearch&folderName=%s' % quote_plus(getLS(33042)), 'trakt.png' if self.iconLogos else 'search.png', 'DefaultAddonsSearch.png')
		self.endDirectory()

	def mymovies(self, lite=False, folderName=''):
		self.accountCheck()
		if self.useContainerTitles: control.setContainerName(folderName)
		self.addDirectoryItem(32039, 'movieUserlists&folderName=%s' % quote_plus(getLS(32039)), 'userlists.png', 'DefaultVideoPlaylists.png')
		if self.favoriteMovie:
			self.addDirectoryItem(getLS(40465), 'getFavouritesMovies&url=favourites_movies&folderName=%s' % (quote_plus(getLS(40465))), 'movies.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.movie.mdblist.userList') and getSetting('mdblist.api') != '':
			self.addDirectoryItem(40087, 'mdbUserListMovies&folderName=%s' % quote_plus(getLS(40087)), 'mdblist.png' if self.iconLogos else 'movies.png', 'DefaultMovies.png')
		if self.traktCredentials:
			if self.traktIndicators:
				self.addDirectoryItem(35308, 'moviesUnfinished&url=traktunfinished&folderName=%s' % quote_plus(getLS(35308)), 'trakt.png', 'trakt.png', queue=True)
				self.addDirectoryItem(32036, 'movies&url=trakthistory&folderName=%s' % quote_plus(getLS(32036)), 'trakt.png', 'trakt.png', queue=True)
			self.addDirectoryItem(32683, 'movies&url=traktwatchlist&folderName=%s' % quote_plus(getLS(32683)), 'trakt.png', 'trakt.png')
			self.addDirectoryItem(32032, 'movies&url=traktcollection&folderName=%s' % quote_plus(getLS(32032)), 'trakt.png', 'trakt.png')
			self.addDirectoryItem('My Liked Lists', 'movies_LikedLists&folderName=My Liked Lists', 'trakt.png', 'trakt.png', queue=True)
		if self.imdbCredentials: self.addDirectoryItem(32682, 'movies&url=imdbwatchlist&folderName=%s' % quote_plus(getLS(32682)), 'imdb.png', 'imdb.png', queue=True) #watchlist broken currently 10-2022
		

		if not lite:
			self.addDirectoryItem(32031, 'movieliteNavigator&folderName=%s' % quote_plus(getLS(32031)), 'movies.png', 'DefaultMovies.png')
			self.addDirectoryItem(33044, 'moviePerson&folderName=%s' % quote_plus(getLS(33044)), 'imdb.png' if self.iconLogos else 'people-search.png', 'DefaultAddonsSearch.png', isFolder=False)
			self.addDirectoryItem(33042, 'movieSearch&folderName=%s' % quote_plus(getLS(33042)), 'search.png' if self.iconLogos else 'search.png', 'DefaultAddonsSearch.png')
		self.endDirectory()

	def tvshows(self, lite=False, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		if getMenuEnabled('navi.originals'):
			self.addDirectoryItem(40077 if self.indexLabels else 40070, 'tvOriginals&folderName=%s' % quote_plus(getLS(40077 if self.indexLabels else 40070)), 'tvmaze.png' if self.iconLogos else 'networks.png', 'DefaultNetwork.png')
		if getMenuEnabled('navi.tv.imdb.popular'):
			self.addDirectoryItem(32429 if self.indexLabels else 32428, 'tvshows&url=popular&folderName=%s' % quote_plus(getLS(32429 if self.indexLabels else 32428)), 'imdb.png' if self.iconLogos else 'most-popular.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.tv.tmdb.popular'):
			self.addDirectoryItem(32431 if self.indexLabels else 32430, 'tmdbTvshows&url=tmdb_popular&folderName=%s' % quote_plus(getLS(32431 if self.indexLabels else 32430)), 'tmdb.png' if self.iconLogos else 'most-popular.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.tv.trakt.popular'):
			self.addDirectoryItem(32433 if self.indexLabels else 32430, 'tvshows&url=traktpopular&folderName=%s' % quote_plus(getLS(32433 if self.indexLabels else 32430)), 'trakt.png' if self.iconLogos else 'most-popular.png', 'DefaultTVShows.png', queue=True)
		if getMenuEnabled('navi.tv.imdb.mostvoted'):
			self.addDirectoryItem(32439 if self.indexLabels else 32438, 'tvshows&url=views&folderName=%s' % quote_plus(getLS(32439 if self.indexLabels else 32438)), 'imdb.png' if self.iconLogos else 'most-voted.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.tv.tmdb.toprated'):
			self.addDirectoryItem(32441 if self.indexLabels else 32440, 'tmdbTvshows&url=tmdb_toprated&folderName=%s' % quote_plus(getLS(32441 if self.indexLabels else 32440)), 'tmdb.png' if self.iconLogos else 'most-voted.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.tv.trakt.trending'):
			self.addDirectoryItem(32443 if self.indexLabels else 32442, 'tvshows&url=trakttrending&folderName=%s' % quote_plus(getLS(32443 if self.indexLabels else 32442)), 'trakt.png' if self.iconLogos else 'trending.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.tv.trakt.trendingrecent'):
			self.addDirectoryItem(40388 if self.indexLabels else 40389, 'tvshows&url=trakttrending_recent&folderName=%s' % quote_plus(getLS(40388 if self.indexLabels else 40389)), 'trakt.png' if self.iconLogos else 'trending.png', 'DefaultTVShows.png')
		if self.simkltoken:
			if getMenuEnabled('navi.tv.simkl.trendingtoday'):
				self.addDirectoryItem(40350 if self.indexLabels else 40351, 'simklTvshows&url=simkltrendingtoday&folderName=%s' % quote_plus(getLS(40350 if self.indexLabels else 40351)), 'simkl.png' if self.iconLogos else 'trending.png', 'DefaultTVShows.png')
			if getMenuEnabled('navi.tv.simkl.trendingweek'):
				self.addDirectoryItem(40352 if self.indexLabels else 40353, 'simklTvshows&url=simkltrendingweek&folderName=%s' % quote_plus(getLS(40352 if self.indexLabels else 40353)), 'simkl.png' if self.iconLogos else 'trending.png', 'DefaultTVShows.png')
			if getMenuEnabled('navi.tv.simkl.trendingweek'):	
				self.addDirectoryItem(40354 if self.indexLabels else 40355, 'simklTvshows&url=simkltrendingmonth&folderName=%s' % quote_plus(getLS(40354 if self.indexLabels else 40355)), 'simkl.png' if self.iconLogos else 'trending.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.tv.tmdb.trendingday'):
			self.addDirectoryItem(40330 if self.indexLabels else 32442, 'tvshows&url=tmdbrecentday&folderName=%s' % quote_plus(getLS(40354 if self.indexLabels else 40355)), 'tmdb.png' if self.iconLogos else 'trending.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.tv.tmdb.trendingweek'):
			self.addDirectoryItem(40331 if self.indexLabels else 32442, 'tvshows&url=tmdbrecentweek&folderName=%s' % quote_plus(getLS(40331 if self.indexLabels else 324425)), 'tmdb.png' if self.iconLogos else 'trending.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.tv.imdb.highlyrated'):
			self.addDirectoryItem(32449 if self.indexLabels else 32448, 'tvshows&url=rating&folderName=%s' % quote_plus(getLS(32449 if self.indexLabels else 32448)), 'imdb.png' if self.iconLogos else 'highly-rated.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.tv.trakt.recommended'):
			self.addDirectoryItem(32445 if self.indexLabels else 32444, 'tvshows&url=traktrecommendations&folderName=%s' % quote_plus(getLS(32445 if self.indexLabels else 32444)), 'trakt.png' if self.iconLogos else 'highly-rated.png', 'DefaultTVShows.png', queue=True)
		if getMenuEnabled('navi.tv.trakt.recentlywatched'):
			self.addDirectoryItem(40255 if self.indexLabels else 40256, 'tvshows&url=traktbasedonrecent&folderName=%s' % quote_plus(getLS(40255 if self.indexLabels else 40256)), 'trakt.png' if self.iconLogos else 'years.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.tv.trakt.traktsimilar'):
			self.addDirectoryItem(40260 if self.indexLabels else 40261, 'tvshows&url=traktbasedonsimilar&folderName=%s' % quote_plus(getLS(40260 if self.indexLabels else 40261)), 'trakt.png' if self.iconLogos else 'years.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.tv.tmdb.genres'):
			self.addDirectoryItem(32486 if self.indexLabels else 32455, 'tvGenres&url=tmdb_genre&folderName=%s' % quote_plus(getLS(32486 if self.indexLabels else 32455)), 'tmdb.png' if self.iconLogos else 'genres.png', 'DefaultGenre.png')
		if getMenuEnabled('navi.tv.trakt.genres'):
			self.addDirectoryItem(40493 if self.indexLabels else 32455, 'tvGenres&url=trakt_tvshow_genre&folderName=%s' % quote_plus(getLS(40493 if self.indexLabels else 32455)), 'trakt.png' if self.iconLogos else 'genres.png', 'DefaultGenre.png')
		if getMenuEnabled('navi.tv.tvmaze.networks'):
			self.addDirectoryItem(32468 if self.indexLabels else 32469, 'tvNetworks&folderName=%s' % quote_plus(getLS(32468 if self.indexLabels else 32469)), 'tmdb.png' if self.iconLogos else 'networks.png', 'DefaultNetwork.png')
		# if getMenuEnabled('navi.tv.tmdb.certificates'):
		if getMenuEnabled('navi.tv.tmdb.years'):
			self.addDirectoryItem(32485 if self.indexLabels else 32457, 'tvYears&url=tmdb_year&folderName=%s' % quote_plus(getLS(32485 if self.indexLabels else 32457)), 'tmdb.png' if self.iconLogos else 'years.png', 'DefaultYear.png')
		if getMenuEnabled('navi.tv.tmdb.airingtoday'):
			self.addDirectoryItem(32467 if self.indexLabels else 32465, 'tmdbTvshows&url=tmdb_airingtoday&folderName=%s' % quote_plus(getLS(32467 if self.indexLabels else 32465)), 'tmdb.png' if self.iconLogos else 'airing-today.png', 'DefaultRecentlyAddedEpisodes.png')
		if getMenuEnabled('navi.tv.tmdb.ontv'):
			self.addDirectoryItem(32472 if self.indexLabels else 32471, 'tmdbTvshows&url=tmdb_ontheair&folderName=%s' % quote_plus(getLS(32472 if self.indexLabels else 32471)), 'tmdb.png' if self.iconLogos else 'new-tvshows.png', 'DefaultRecentlyAddedEpisodes.png')
		if getMenuEnabled('navi.tv.imdb.newtvshows'):
			self.addDirectoryItem(32476 if self.indexLabels else 32475, 'tvshows&url=premiere&folderName=%s' % quote_plus(getLS(32476 if self.indexLabels else 32475)), 'imdb.png' if self.iconLogos else 'new-tvshows.png', 'DefaultRecentlyAddedEpisodes.png')
		if getMenuEnabled('navi.tv.tvmaze.calendar'):
			self.addDirectoryItem(32450 if self.indexLabels else 32027, 'calendars&folderName=%s' % quote_plus(getLS(32450 if self.indexLabels else 32027)), 'tvmaze.png' if self.iconLogos else 'calendar.png', 'DefaultYear.png')
		if getMenuEnabled('navi.tv.mdblist.topList') and getSetting('mdblist.api') != '':
			self.addDirectoryItem(40084, 'mdbTopListTV&folderName=%s' % quote_plus(getLS(40084)), 'mdblist.png' if self.iconLogos else 'tvshows.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.tv.trakt.popularList'):
			self.addDirectoryItem(32417, 'tv_PublicLists&url=trakt_popularLists&folderName=%s' % quote_plus(getLS(32417)), 'trakt.png' if self.iconLogos else 'tvshows.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.tv.trakt.trendingList'):
			self.addDirectoryItem(32418, 'tv_PublicLists&url=trakt_trendingLists&folderName=%s' % quote_plus(getLS(32418)), 'trakt.png' if self.iconLogos else 'tvshows.png', 'DefaultMovies.png')
		if getMenuEnabled('navi.tv.trakt.searchList'):
			self.addDirectoryItem(32419, 'tv_SearchLists&media_type=shows', 'trakt.png' if self.iconLogos else 'tvshows.png', 'DefaultMovies.png', isFolder=False)
		if not lite:
			if getMenuEnabled('mylists.widget'): self.addDirectoryItem(32004, 'mytvliteNavigator&folderName=%s' % quote_plus(getLS(32004)), 'mytvshows.png', 'DefaultTVShows.png')
			if self.favoriteTVShows:
				self.addDirectoryItem(getLS(40466), 'getFavouritesTVShows&url=favourites_tvshows&folderName=%s' % (quote_plus(getLS(40466))), 'tvshows.png', 'DefaultTVShows.png')
			self.addDirectoryItem(33045, 'tvPerson', 'imdb.png' if self.iconLogos else 'people-search.png', 'DefaultAddonsSearch.png', isFolder=False)
			self.addDirectoryItem(33043, 'tvSearch&folderName=%s' % quote_plus(getLS(33043)), 'trakt.png' if self.iconLogos else 'search.png', 'DefaultAddonsSearch.png')
		self.endDirectory()

	def mytvshows(self, lite=False, folderName=''):
		self.accountCheck()
		if self.useContainerTitles: control.setContainerName(folderName)
		self.addDirectoryItem(32040, 'tvUserlists&folderName=%s' % quote_plus(getLS(32040)), 'userlists.png', 'DefaultVideoPlaylists.png')
		if self.favoriteTVShows:
			self.addDirectoryItem(getLS(40466), 'getFavouritesTVShows&url=favourites_tvshows&folderName=%s' % (quote_plus(getLS(40466))), 'tvshows.png', 'DefaultTVShows.png')
		if self.favoriteEpisodes: self.addDirectoryItem(getLS(40467), 'getFavouritesEpisodes&folderName=%s' % (quote_plus(getLS(40467))), 'tvshows.png', 'DefaultTVShows.png')
		if getMenuEnabled('navi.tv.mdblist.userList') and getSetting('mdblist.api') != '':
			self.addDirectoryItem(40087, 'mdbUserListTV&folderName=%s' % quote_plus(getLS(40087)), 'mdblist.png' if self.iconLogos else 'tvshows.png', 'DefaultMovies.png')
		if self.traktCredentials:
			if self.traktIndicators:
				self.addDirectoryItem(35308, 'episodesUnfinished&url=traktunfinished&folderName=%s' % quote_plus(getLS(35308)), 'trakt.png', 'trakt.png', queue=True)
				self.addDirectoryItem(32037, 'calendar&url=progress&folderName=%s' % quote_plus(getLS(32037)), 'trakt.png', 'trakt.png', queue=True)
				self.addDirectoryItem(40401, 'shows_progress&url=progresstv&folderName=%s' % quote_plus(getLS(40401)), 'trakt.png', 'trakt.png', queue=True)
				self.addDirectoryItem(40433, 'shows_watched&url=watchedtv&folderName=%s' % quote_plus(getLS(40433)), 'trakt.png', 'trakt.png', queue=True)
				self.addDirectoryItem(32019, 'upcomingProgress&url=progress&folderName=%s' % quote_plus(getLS(32019)), 'trakt.png', 'trakt.png', queue=True)
				self.addDirectoryItem(32202, 'calendar&url=mycalendarRecent&folderName=%s' % quote_plus(getLS(32202)), 'trakt.png', 'trakt.png', queue=True)
				self.addDirectoryItem(32203, 'calendar&url=mycalendarUpcoming&folderName=%s' % quote_plus(getLS(32203)), 'trakt.png', 'trakt.png', queue=True)
				self.addDirectoryItem(32204, 'calendar&url=mycalendarPremiers&folderName=%s' % quote_plus(getLS(32204)), 'trakt.png', 'trakt.png', queue=True)
				self.addDirectoryItem(32036, 'calendar&url=trakthistory&folderName=%s' % quote_plus(getLS(32036)), 'trakt.png', 'trakt.png', queue=True)
			#self.addDirectoryItem(32683, 'tvshows&url=traktwatchlist', 'trakt.png', 'trakt.png', context=(32551, 'library_tvshowsToLibrary&url=traktwatchlist&name=traktwatchlist'))
			#self.addDirectoryItem(32032, 'tvshows&url=traktcollection', 'trakt.png', 'trakt.png', context=(32551, 'library_tvshowsToLibrary&url=traktcollection&name=traktcollection'))
			self.addDirectoryItem(32683, 'tvshows&url=traktwatchlist&folderName=%s' % quote_plus(getLS(32683)), 'trakt.png', 'trakt.png')
			self.addDirectoryItem(32032, 'tvshows&url=traktcollection&folderName=%s' % quote_plus(getLS(32032)), 'trakt.png', 'trakt.png')
			self.addDirectoryItem('My Liked Lists', 'shows_LikedLists&folderName=My Liked Lists', 'trakt.png', 'trakt.png', queue=True)
		if self.imdbCredentials: self.addDirectoryItem(32682, 'tvshows&url=imdbwatchlist&folderName=%s' % quote_plus(getLS(32682)), 'imdb.png', 'imdb.png')
		if not lite:
			self.addDirectoryItem(32031, 'tvliteNavigator&folderName=%s' % quote_plus(getLS(32031)), 'tvshows.png', 'DefaultTVShows.png')
			self.addDirectoryItem(33045, 'tvPerson', 'imdb.png' if self.iconLogos else 'people-search.png', 'DefaultAddonsSearch.png', isFolder=False)
			self.addDirectoryItem(33043, 'tvSearch&folderName=%s' % quote_plus(getLS(33043)), 'trakt.png' if self.iconLogos else 'search.png', 'DefaultAddonsSearch.png')
		self.endDirectory()

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

	def tools(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		self.addDirectoryItem(32510, 'cache_Navigator&folderName=%s' % quote_plus(getLS(40462)), 'settings.png', 'DefaultAddonService.png', isFolder=True)
		#self.addDirectoryItem(32609, 'tools_openMyAccount', 'MyAccounts.png', 'DefaultAddonService.png', isFolder=False)
		#self.addDirectoryItem(32506, 'tools_contextUmbrellaSettings', 'icon.png', 'DefaultAddonProgram.png', isFolder=False)
		#-- Providers - 
		#self.addDirectoryItem(32651, 'tools_cocoScrapersSettings', 'cocoscrapers.png', 'DefaultAddonService.png', isFolder=False)
		#-- General - 0
		self.addDirectoryItem(32043, 'tools_openSettings&query=0.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		#-- Sorting and Filtering - 4
		self.addDirectoryItem(40162, 'tools_openSettings&query=6.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		#-- Accounts - 7
		self.addDirectoryItem(32044, 'tools_openSettings&query=10.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(40452, 'tools_openSettings&query=11.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(40124, 'tools_openSettings&query=12.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(40123, 'tools_openSettings&query=8.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		if self.traktCredentials: self.addDirectoryItem(35057, 'tools_traktToolsNavigator&folderName=%s' % quote_plus(getLS(40461)), 'tools.png', 'DefaultAddonService.png', isFolder=True)
		#-- Navigation - 1
		self.addDirectoryItem(32362, 'tools_openSettings&query=1.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		#-- Playback - 3
		self.addDirectoryItem(32045, 'tools_openSettings&query=5.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		#-- Downloads - 10
		self.addDirectoryItem(32048, 'tools_openSettings&query=14.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		#-- Subtitles - 11
		self.addDirectoryItem(32046, 'tools_openSettings&query=15.0', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		self.addDirectoryItem(32556, 'library_Navigator&folderName=%s' % quote_plus(getLS(32541)), 'tools.png', 'DefaultAddonService.png', isFolder=True)
		self.addDirectoryItem(32049, 'tools_viewsNavigator', 'settings.png', 'DefaultAddonService.png', isFolder=True)
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
		self.endDirectory()

	def loggingNavigator(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		self.addDirectoryItem(32524, 'tools_viewLogFile&name=Umbrella', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32525, 'tools_clearLogFile', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(32526, 'tools_ShowChangelog&name=Umbrella', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
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
		self.addDirectoryItem(32557, 'tools_openSettings&query=13.0', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
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
		if getMenuEnabled('navi.alldebrid'): self.addDirectoryItem(40059, 'ad_ServiceNavigator&folderName=%s' % quote_plus(getLS(40059)), 'alldebrid.png', 'alldebrid.png')
		if getMenuEnabled('navi.easynews'): self.addDirectoryItem(32327, 'en_ServiceNavigator&folderName=%s' % quote_plus(getLS(32327)), 'easynews.png', 'easynews.png')
		#if getMenuEnabled('navi.furk'): self.addDirectoryItem('Furk.net', 'furk_ServiceNavigator', 'furk.png', 'furk.png')
		if getMenuEnabled('navi.premiumize'): self.addDirectoryItem(40057, 'pm_ServiceNavigator&folderName=%s' % quote_plus(getLS(40057)), 'premiumize.png', 'premiumize.png')
		if getMenuEnabled('navi.realdebrid'): self.addDirectoryItem(40058, 'rd_ServiceNavigator&folderName=%s' % quote_plus(getLS(40058)), 'realdebrid.png', 'realdebrid.png')
		self.endDirectory()

	def alldebrid_service(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		if getSetting('alldebridtoken'):
			self.addDirectoryItem('All-Debrid: Cloud Storage', 'ad_CloudStorage', 'alldebrid.png', 'DefaultAddonService.png')
			self.addDirectoryItem('All-Debrid: Transfers', 'ad_Transfers', 'alldebrid.png', 'DefaultAddonService.png')
			self.addDirectoryItem('All-Debrid: Account Info', 'ad_AccountInfo', 'alldebrid.png', 'DefaultAddonService.png', isFolder=False)
		else:
			self.addDirectoryItem('[I]Please setup in Accounts[/I]', 'tools_openSettings&query=10.0', 'alldebrid.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def easynews_service(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		if getSetting('easynews.user'):
			self.addDirectoryItem('Easy News: Search', 'en_Search', 'search.png', 'DefaultAddonsSearch.png')
			self.addDirectoryItem('Easy News: Account Info', 'en_AccountInfo', 'easynews.png', 'DefaultAddonService.png', isFolder=False)
		else:
			self.addDirectoryItem('[I]Please setup in CocoScrapers[/I]', 'tools_cocoScrapersSettings&query=EasyNews', 'easynews.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def premiumize_service(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		if getSetting('premiumizetoken'):
			self.addDirectoryItem('Premiumize: My Files', 'pm_MyFiles', 'premiumize.png', 'DefaultAddonService.png')
			self.addDirectoryItem('Premiumize: Transfers', 'pm_Transfers', 'premiumize.png', 'DefaultAddonService.png')
			self.addDirectoryItem('Premiumize: Account Info', 'pm_AccountInfo', 'premiumize.png', 'DefaultAddonService.png', isFolder=False)
		else:
			self.addDirectoryItem('[I]Please setup in Accounts[/I]', 'tools_openSettings&query=10.1', 'premiumize.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def realdebrid_service(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		if getSetting('realdebridtoken'):
			self.addDirectoryItem('Real-Debrid: Torrent Transfers', 'rd_UserTorrentsToListItem', 'realdebrid.png', 'DefaultAddonService.png')
			self.addDirectoryItem('Real-Debrid: My Downloads', 'rd_MyDownloads&query=1', 'realdebrid.png', 'DefaultAddonService.png')
			self.addDirectoryItem('Real-Debrid: Account Info', 'rd_AccountInfo', 'realdebrid.png', 'DefaultAddonService.png', isFolder=False )
		else:
			self.addDirectoryItem('[I]Please setup in Accounts[/I]', 'tools_openSettings&query=10.2', 'realdebrid.png', 'DefaultAddonService.png', isFolder=False)
		self.endDirectory()

	def search(self, folderName=''):
		if self.useContainerTitles: control.setContainerName(folderName)
		self.addDirectoryItem(33042, 'movieSearch&folderName=%s' % quote_plus(getLS(33042)), 'trakt.png' if self.iconLogos else 'search.png', 'DefaultAddonsSearch.png')
		self.addDirectoryItem(33043, 'tvSearch&folderName=%s' % quote_plus(getLS(33043)), 'trakt.png' if self.iconLogos else 'search.png', 'DefaultAddonsSearch.png')
		self.addDirectoryItem(33044, 'moviePerson', 'imdb.png' if self.iconLogos else 'people-search.png', 'DefaultAddonsSearch.png', isFolder=False)
		self.addDirectoryItem(33045, 'tvPerson', 'imdb.png' if self.iconLogos else 'people-search.png', 'DefaultAddonsSearch.png', isFolder=False)
		if getSetting('easynews.user'):
			self.addDirectoryItem('Easy News: Search', 'en_Search', 'search.png', 'DefaultAddonsSearch.png')
		#if getSetting('mdblist.api') != '':
			#self.addDirectoryItem(40088, 'mdbListSearch', 'mdblist.png' if self.iconLogos else 'search.png', 'DefaultAddonsSearch.png')
		self.endDirectory()

	def views(self, folderName=''):
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