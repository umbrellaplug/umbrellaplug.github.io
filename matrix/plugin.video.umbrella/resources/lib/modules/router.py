# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from urllib.parse import quote_plus, parse_qsl
from resources.lib.modules import control


def router(argv2):
	try:
		params = dict(parse_qsl(argv2.replace('?', '')))
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		params = {}
	action = params.get('action')
	name = params.get('name')
	title = params.get('title')
	tvshowtitle = params.get('tvshowtitle')
	year = params.get('year')
	imdb = params.get('imdb')
	tmdb = params.get('tmdb')
	tvdb = params.get('tvdb')
	season = params.get('season')
	episode = params.get('episode')
	url = params.get('url')
	query = params.get('query')
	source = params.get('source')
	select = params.get('select')
	folder = params.get('folder')
	current_setting = params.get('setting')
	folderName = params.get('folderName')
	mediatype = params.get('mediatype')
	listType = params.get('listtype')
	genre = params.get('genre')
	decade = params.get('decades')
	if action is None:
		from resources.lib.menus import navigator
		isUpdate = control.homeWindow.getProperty('umbrella.updated')
		if isUpdate == 'true':
			control.execute('RunPlugin(plugin://plugin.video.umbrella/?action=tools_cleanSettings)')
			control.homeWindow.clearProperty('umbrella.updated')
			from resources.lib.modules import changelog
			changelog.get('Umbrella')
		navigator.Navigator().root()
	####################################################
	#---MOVIES
	####################################################
	# elif action and action.startswith('movies_'):
	elif action == 'movieNavigator':
		from resources.lib.menus import navigator
		navigator.Navigator().movies(folderName=folderName)
	elif action == 'movieliteNavigator':
		from resources.lib.menus import navigator
		navigator.Navigator().movies(lite=True, folderName=folderName)
	elif action == 'mymovieNavigator':
		from resources.lib.menus import navigator
		navigator.Navigator().mymovies(folderName=folderName)
	elif action == 'mymovieliteNavigator':
		from resources.lib.menus import navigator
		navigator.Navigator().mymovies(lite=True, folderName=folderName)
	elif action == 'movies':
		from resources.lib.menus import movies
		movies.Movies().get(url, folderName=folderName)
	elif action == 'simklMovies':
		from resources.lib.menus import movies
		movies.Movies().getSimkl(url, folderName=folderName)
	elif action == 'mixed' and 'movies' in url:
		from resources.lib.menus import movies
		movies.Movies().get(url, folderName=folderName)
	elif action == 'moviePage':
		from resources.lib.menus import movies
		movies.Movies().get(url, folderName=folderName)
	elif action == 'tmdbmovies':
		from resources.lib.menus import movies
		movies.Movies().getTMDb(url, folderName=folderName)
	elif action == 'tmdbmoviePage':
		from resources.lib.menus import movies
		movies.Movies().getTMDb(url, folderName=folderName)
	elif action == 'movieSearch':
		from resources.lib.menus import movies
		movies.Movies().search(folderName=folderName)
	elif action == 'movieSearchnew':
		from resources.lib.menus import movies
		movies.Movies().search_new()
	elif action == 'movieSearchterm':
		from resources.lib.menus import movies
		movies.Movies().search_term(name)
	elif action == 'movieKeywordSearch':
		from resources.lib.modules import search
		search.Search().movieKeywordSearch(name)
	#added for tmdb based searches for movies.
	elif action == 'moviePerson':
		from resources.lib.menus import movies
		movies.Movies().person()
	elif action == 'movieGenres':
		from resources.lib.menus import movies
		movies.Movies().genres(url, folderName=folderName)
	elif action == 'trakt_genre_decades':
		from resources.lib.menus import navigator
		navigator.Navigator().trakt_genre_decade(mediatype=mediatype, genre=genre, decade=decade, url=url, folderName=folderName)
	elif action =='trakt_movie_genre':
		from resources.lib.menus import navigator
		navigator.Navigator().trakt_genre(mediatype=mediatype, genre=genre, url=url, folderName=folderName)
	elif action =='trakt_tvshow_genre':
		from resources.lib.menus import navigator
		navigator.Navigator().trakt_genre(mediatype=mediatype, genre=genre, url=url, folderName=folderName)
	elif action == 'trakt_genre':
		if mediatype == 'Movies':
			from resources.lib.menus import movies
			movies.Movies().trakt_genre_list(listType=listType, genre=genre, url=url, folderName=folderName)
		if mediatype == 'TVShows':
			from resources.lib.menus import tvshows
			tvshows.TVshows().trakt_genre_list(listType=listType, genre=genre, url=url, folderName=folderName)
	elif action == 'trakt_genre_decade':
		if mediatype == 'Movies':
			from resources.lib.menus import movies
			movies.Movies().trakt_genre_list_decade(listType=listType, genre=genre, decade=decade, url=url, folderName=folderName)
		if mediatype == 'TVShows':
			from resources.lib.menus import tvshows
			tvshows.TVshows().trakt_genre_list_decade(listType=listType, genre=genre, decade=decade, url=url, folderName=folderName)
	elif action == 'movieLanguages':
		from resources.lib.menus import movies
		movies.Movies().languages(folderName=folderName)
	elif action == 'movieCertificates':
		from resources.lib.menus import movies
		movies.Movies().certifications(url, folderName=folderName)
	elif action == 'movieYears':
		from resources.lib.menus import movies
		movies.Movies().years(url, folderName=folderName)
	elif action == 'traktYear':
		from resources.lib.menus import movies
		movies.Movies().years(url, folderName=folderName)
	elif action == 'moviePersons':
		from resources.lib.menus import movies
		#movies.Movies().persons(url, folderName=folderName)
		movies.Movies().persons_tmdb(url, folderName=folderName)
	elif action == 'actorSearchMovies':
		link = 'https://www.imdb.com/search/name/?count=100&name='
		name = params.get('name')
		if name:
			name = quote_plus(name.strip())
			url = link + name
			from resources.lib.menus import movies
			movies.Movies().persons(url, folderName=folderName)
	elif action == 'dvdReleaseList':
		from resources.lib.menus import movies
		movies.Movies().dvdReleaseList(folderName='DVD Releases')
	elif action == 'moviesUnfinished':
		from resources.lib.menus import movies
		movies.Movies().unfinished(url, folderName=folderName)
	elif action == 'movieUserlists':
		from resources.lib.menus import movies
		movies.Movies().userlists(folderName=folderName, create_directory=True)
	elif action == 'traktAuth':
		from resources.lib.modules import trakt as Trakt
		Trakt.traktAuth(fromSettings=1)
	elif action == 'traktRevoke':
		from resources.lib.modules import trakt as Trakt
		Trakt.traktRevoke(fromSettings=1)
	elif action == 'traktAccountInfo':
		from resources.lib.modules import trakt as Trakt
		Trakt.getTraktAccountInfo()
	elif action == 'movies_PublicLists':
		from resources.lib.menus import movies
		movies.Movies().getTraktPublicLists(url, folderName=folderName)
	elif action == 'movies_SearchLists':
		from resources.lib.menus import navigator
		navigator.Navigator().traktSearchLists(params.get('media_type'))
	elif action == 'trakt_search_lists':
		from resources.lib.menus import navigator
		navigator.Navigator().traktSearchListsTerm(name,params.get('media_type'))
	elif action == 'movies_LikedLists':
		from resources.lib.menus import movies
		movies.Movies().traktLlikedlists(folderName=folderName)
	elif action == 'movies_traktUnfinishedManager':
		from resources.lib.menus import movies
		movies.Movies().unfinishedManager()
	elif action == 'movies_traktCollectionManager':
		from resources.lib.menus import movies
		movies.Movies().collectionManager()
	elif action == 'movies_traktWatchListManager':
		from resources.lib.menus import movies
		movies.Movies().watchlistManager()
	elif action == 'movies_favorites':
		from resources.lib.modules import favourites
		favourites.getFavouritesMoviesfromXML()
	elif action == 'getFavouritesMovies':
		from resources.lib.menus import movies
		movies.Movies().get(url, folderName=folderName)
	elif action == 'getFavouritesTVShows':
		from resources.lib.menus import tvshows
		tvshows.TVshows().get(url, folderName=folderName)
	elif action == 'mdbTopListMovies':
		from resources.lib.menus import movies
		movies.Movies().getMBDTopLists(folderName=folderName)
	elif action == 'mdbUserListMovies':
		from resources.lib.menus import movies
		movies.Movies().getMDBUserList(folderName=folderName)
	elif action == 'moviesimilarFromLibrary':
		from resources.lib.menus import movies
		movies.Movies().similarFromLibrary(tmdb=tmdb)
	elif action == 'movierecommendedFromLibrary':
		from resources.lib.menus import movies
		movies.Movies().reccomendedFromLibrary(folderName=folderName)
	####################################################
	#---Collections
	####################################################
	elif action and action.startswith('collections'):
		if action == 'collections_Navigator':
			from resources.lib.menus import collections
			collections.Collections().collections_Navigator(folderName=folderName)
		elif action == 'collections_Boxset':
			from resources.lib.menus import collections
			collections.Collections().collections_Boxset(folderName=folderName)
		elif action == 'collections_Kids':
			from resources.lib.menus import collections
			collections.Collections().collections_Kids(folderName=folderName)
		elif action == 'collections_BoxsetKids':
			from resources.lib.menus import collections
			collections.Collections().collections_BoxsetKids(folderName=folderName)
		elif action == 'collections_Superhero':
			from resources.lib.menus import collections
			collections.Collections().collections_Superhero(folderName=folderName)
		elif action == 'collections_MartialArts':
			from resources.lib.menus import collections
			collections.Collections().collections_martial_arts(folderName=folderName)
		elif action == 'collections_MartialArtsActors':
			from resources.lib.menus import collections
			collections.Collections().collections_martial_arts_actors(folderName=folderName)
		elif action == 'collections_Search':
			from resources.lib.menus import collections
			collections.Collections().search(folderName=folderName)
		elif action == 'collections_Searchnew':
			from resources.lib.menus import collections
			collections.Collections().search_new()
		elif action == 'collections_Searchterm':
			from resources.lib.menus import collections
			collections.Collections().search_term(name)
		elif action == 'collections':
			from resources.lib.menus import collections
			collections.Collections().get(url, folderName=folderName)

	####################################################
	# TV Shows
	####################################################
	# if action and action.startswith('tv_'):
	elif action == 'tvNavigator':
		from resources.lib.menus import navigator
		navigator.Navigator().tvshows(folderName=folderName)
	elif action == 'tvliteNavigator':
		from resources.lib.menus import navigator
		navigator.Navigator().tvshows(lite=True, folderName=folderName)
	elif action == 'mytvNavigator':
		from resources.lib.menus import navigator
		navigator.Navigator().mytvshows(folderName=folderName)
	elif action == 'mytvliteNavigator':
		from resources.lib.menus import navigator
		navigator.Navigator().mytvshows(lite=True, folderName=folderName)
	elif action == 'tvshows':
		from resources.lib.menus import tvshows
		tvshows.TVshows().get(url, folderName=folderName)
	elif action == 'mixed' and 'movies' not in url:
		from resources.lib.menus import tvshows
		tvshows.TVshows().get(url, folderName=folderName)
	elif action == 'tvshowPage':
		from resources.lib.menus import tvshows
		tvshows.TVshows().get(url, folderName=folderName)
	elif action == 'mdbTopListTV':
		from resources.lib.menus import tvshows
		tvshows.TVshows().getMBDTopLists(folderName=folderName)
	elif action == 'tmdbTvshows':
		from resources.lib.menus import tvshows
		tvshows.TVshows().getTMDb(url, folderName=folderName)
	elif action == 'simklTvshows':
		from resources.lib.menus import tvshows
		tvshows.TVshows().getSimkl(url, folderName=folderName)
	elif action == 'tmdbTvshowPage':
		from resources.lib.menus import tvshows
		tvshows.TVshows().getTMDb(url, folderName=folderName)
	elif action == 'tvmazeTvshows':
		from resources.lib.menus import tvshows
		tvshows.TVshows().getTVmaze(url)
	elif action == 'tvmazeTvshowPage':
		from resources.lib.menus import tvshows
		tvshows.TVshows().getTVmaze(url)
	elif action == 'tvSearch':
		from resources.lib.menus import tvshows
		tvshows.TVshows().search(folderName=folderName)
	elif action == 'tvSearchnew':
		from resources.lib.menus import tvshows
		tvshows.TVshows().search_new()
	elif action == 'tvSearchterm':
		from resources.lib.menus import tvshows
		tvshows.TVshows().search_term(name)
	elif action == 'tvPerson':
		from resources.lib.menus import tvshows
		tvshows.TVshows().person(folderName=folderName)
	elif action == 'tvGenres':
		from resources.lib.menus import tvshows
		tvshows.TVshows().genres(url, folderName=folderName)
	elif action == 'tvNetworks':
		from resources.lib.menus import tvshows
		tvshows.TVshows().networks(folderName=folderName)
	elif action == 'tvLanguages':
		from resources.lib.menus import tvshows
		tvshows.TVshows().languages(folderName=folderName)
	elif action == 'tvCertificates':
		from resources.lib.menus import tvshows
		tvshows.TVshows().certifications(folderName=folderName)
	elif action == 'tvYears':
		from resources.lib.menus import tvshows
		tvshows.TVshows().years(url, folderName=folderName)
	elif action == 'tvPersons':
		from resources.lib.menus import tvshows
		#tvshows.TVshows().persons(url)
		tvshows.TVshows().persons_tmdb(url)
	elif action == 'actorSearchTV':
		link = 'https://www.imdb.com/search/name/?count=100&name='
		name = params.get('name')
		if name:
			name = quote_plus(name.strip())
			url = link + name
			from resources.lib.menus import tvshows
			tvshows.TVshows().persons(url, folderName=folderName)
	elif action == 'tvUserlists':
		from resources.lib.menus import tvshows
		tvshows.TVshows().userlists(folderName=folderName, create_directory=True)
	elif action == 'tvOriginals':
		from resources.lib.menus import tvshows
		tvshows.TVshows().originals(folderName)
	elif action == 'tv_PublicLists':
		from resources.lib.menus import tvshows
		tvshows.TVshows().getTraktPublicLists(url, folderName=folderName)
	elif action == 'tv_SearchLists':
		from resources.lib.menus import navigator
		navigator.Navigator().traktSearchLists(params.get('media_type'))
	elif action == 'shows_LikedLists':
		from resources.lib.menus import tvshows
		tvshows.TVshows().traktLlikedlists(folderName=folderName)
	elif action == 'shows_traktHiddenManager':
		from resources.lib.menus import tvshows
		tvshows.TVshows().traktHiddenManager()
	elif action == 'shows_traktCollectionManager':
		from resources.lib.menus import tvshows
		tvshows.TVshows().collectionManager()
	elif action == 'shows_traktWatchListManager':
		from resources.lib.menus import tvshows
		tvshows.TVshows().watchlistManager()
	elif action == 'mdbUserListTV':
		from resources.lib.menus import tvshows
		tvshows.TVshows().getMDBUserList(folderName=folderName)
	elif action == 'shows_progress':
		from resources.lib.menus import tvshows
		tvshows.TVshows().tvshow_progress(url, folderName=folderName)
	elif action == 'shows_watched':
		from resources.lib.menus import tvshows
		tvshows.TVshows().tvshow_watched(url, folderName=folderName)

	####################################################
	#---Plex
	####################################################
	elif action == 'plexAuth':
		from resources.lib.modules import plex
		plex.Plex().auth()

	elif action == 'plexRevoke':
		from resources.lib.modules import plex
		plex.Plex().revoke()

	elif action == 'plexSelectShare':
		from resources.lib.modules import plex
		plex.Plex().get_plexshare_resource()

	elif action == 'plexSeeShare':
		from resources.lib.modules import plex
		plex.Plex().see_active_shares()

	####################################################
	#---SEASONS
	####################################################
	elif action == 'seasons':
		from resources.lib.menus import seasons
		seasons.Seasons().get(tvshowtitle, year, imdb, tmdb, tvdb, params.get('art'))
	####################################################
	#---RETURN FROM LISTS
	elif action == 'return_home':
		control.backToMain(folder)
	####################################################

	####################################################
	#---FAVOURITES
	####################################################
	elif action == 'add_favorite':
		from resources.lib.modules import favourites
		favourites.addFavourite(params.get('meta'), params.get('content'))
	elif action == 'remove_favorite':
		from resources.lib.modules import favourites
		favourites.deleteFavourite(params.get('meta'), params.get('content'))
	elif action == 'add_favorite_episode':
		from resources.lib.modules import favourites
		favourites.addEpisodes(params.get('meta'), params.get('content'))
	elif action == 'getFavouritesEpisodes':
		from resources.lib.menus import episodes
		episodes.Episodes().getFavoriteEpisodes(folderName=folderName)
	if action == 'favouriteNavigator':
			from resources.lib.menus import navigator
			navigator.Navigator().favourites(folderName=folderName)

	####################################################
	#---EPISODES
	####################################################
	elif action == 'episodes':
		from resources.lib.menus import episodes
		episodes.Episodes().get(tvshowtitle, year, imdb, tmdb, tvdb, params.get('meta'), season, episode)
	elif action == 'calendar':
		from resources.lib.menus import episodes
		episodes.Episodes().calendar(url, folderName=folderName)
	elif action == 'upcomingProgress':
		from resources.lib.menus import episodes
		episodes.Episodes().upcoming_progress(url, folderName=folderName)
	elif action == 'episodes_clrProgressCache':
		from resources.lib.menus import episodes
		episodes.Episodes().clr_progress_cache(url)
	elif action == 'calendars':
		from resources.lib.menus import episodes
		episodes.Episodes().calendars(folderName=folderName)
	elif action == 'episodesUnfinished':
		from resources.lib.menus import episodes
		episodes.Episodes().unfinished(url, folderName=folderName)
	elif action == 'episodes_traktUnfinishedManager':
		from resources.lib.menus import episodes
		episodes.Episodes().unfinishedManager()

	####################################################
	#---Premium Services
	####################################################
	elif action == 'premiumNavigator':
		from resources.lib.menus import navigator
		navigator.Navigator().premium_services(folderName=folderName)

	elif action and action.startswith('simkl_'):
		if action == 'simkl_Authorize':
			from resources.lib.modules import simkl
			simkl.SIMKL().auth(fromSettings=1)
		if action == 'simkl_Revoke':
			from resources.lib.modules import simkl
			simkl.SIMKL().reset_authorization(fromSettings=1) #new simkl revoke - pointless simkl never clears access tokens

	elif action and action.startswith('ad_'):
		if action == 'ad_ServiceNavigator':
			from resources.lib.menus import navigator
			navigator.Navigator().alldebrid_service(folderName=folderName)
		elif action == 'ad_AccountInfo':
			from resources.lib.debrid import alldebrid
			alldebrid.AllDebrid().account_info_to_dialog()
		elif action == 'ad_Revoke':
			from resources.lib.debrid import alldebrid
			alldebrid.AllDebrid().revoke_auth(fromSettings=1)
		elif action == 'ad_Authorize':
			from resources.lib.debrid import alldebrid
			alldebrid.AllDebrid().auth(fromSettings=1)
		elif action == 'ad_Transfers':
			from resources.lib.debrid import alldebrid
			alldebrid.AllDebrid().user_transfers_to_listItem()
		elif action == 'ad_CloudStorage':
			from resources.lib.debrid import alldebrid
			alldebrid.AllDebrid().user_cloud_to_listItem()
		elif action == 'ad_BrowseUserCloud':
			from resources.lib.debrid import alldebrid
			alldebrid.AllDebrid().browse_user_cloud(source)
		elif action == 'ad_DeleteTransfer':
			from resources.lib.debrid import alldebrid
			alldebrid.AllDebrid().delete_transfer(params.get('id'), name, silent=False)
		elif action == 'ad_RestartTransfer':
			from resources.lib.debrid import alldebrid
			alldebrid.AllDebrid().restart_transfer(params.get('id'), name, silent=False)

	elif action and action.startswith('en_'):
		if action == 'en_ServiceNavigator':
			from resources.lib.menus import navigator
			navigator.Navigator().easynews_service(folderName=folderName)
		elif action == 'en_Search':
			from resources.lib.debrid import easynews
			easynews.EasyNews().search()
		elif action == 'en_Searchnew':
			from resources.lib.debrid import easynews
			easynews.EasyNews().search_new()
		elif action == 'en_searchResults':
			from resources.lib.debrid import easynews
			easynews.EasyNews().query_results_to_dialog(query)
		elif action == 'en_resolve_forPlayback':
			from resources.lib.debrid import easynews
			easynews.EasyNews().resolve_forPlayback(url)
		elif action == 'en_AccountInfo':
			from resources.lib.debrid import easynews
			easynews.EasyNews().account_info_to_dialog()

	# elif action and action.startswith('furk_'):
	# 	if action == "furk_ServiceNavigator":
	# 		from resources.lib.menus import navigator
	# 		navigator.Navigator().furk_service()
	# 	elif action == "furk_Search":
	# 		from resources.lib.debrid import furk
	# 		furk.Furk().search()
	# 	elif action == "furk_SearchNew":
	# 		from resources.lib.debrid import furk
	# 		furk.Furk().search_new()
	# 	elif action == "furk_searchResults":
	# 		from resources.lib.debrid import furk
	# 		furk.Furk().query_results_to_dialog(query)
	# 	elif action == 'furk_resolve_forPlayback':
	# 		from resources.lib.debrid import furk
	# 		furk.Furk().resolve_forPlayback(url)
	# 	elif action == 'furk_AccountInfo':
	# 		from resources.lib.debrid import furk
	# 		furk.Furk().account_info_to_dialog()
	# 	elif action == "furk_UserFiles":
	# 		from resources.lib.debrid import furk
	# 		furk.Furk().user_files()
	# 	elif action == "furk_getApi":
	# 		from resources.lib.debrid import furk
	# 		furk.Furk().get_api()
	# 	elif action == "furk_clearApi":
	# 		from resources.lib.debrid import furk
	# 		furk.Furk().clear_api()

	elif action and action.startswith('pm_'):
		if action == 'pm_ServiceNavigator':
			from resources.lib.menus import navigator
			navigator.Navigator().premiumize_service(folderName=folderName)
		elif action == 'pm_AccountInfo':
			from resources.lib.debrid import premiumize
			premiumize.Premiumize().account_info_to_dialog()
		elif action == 'pm_Authorize':
			from resources.lib.debrid import premiumize
			premiumize.Premiumize().auth(fromSettings=1)
		elif action == 'pm_Revoke':
			from resources.lib.debrid import premiumize
			premiumize.Premiumize().revoke(fromSettings=1)
		elif action == 'pm_MyFiles':
			from resources.lib.debrid import premiumize
			premiumize.Premiumize().my_files_to_listItem(params.get('id'), name)
		elif action == 'pm_Transfers':
			from resources.lib.debrid import premiumize
			premiumize.Premiumize().user_transfers_to_listItem()
		elif action == 'pm_Rename':
			from resources.lib.debrid import premiumize
			premiumize.Premiumize().rename(params.get('type'), params.get('id'), name)
		elif action == 'pm_Delete':
			from resources.lib.debrid import premiumize
			premiumize.Premiumize().delete(params.get('type'), params.get('id'), name)
		elif action == 'pm_DeleteTransfer':
			from resources.lib.debrid import premiumize
			premiumize.Premiumize().delete_transfer(params.get('id'), name)
		elif action == 'pm_ClearFinishedTransfers': # disabled for now till PM fixes
			from resources.lib.debrid import premiumize
			premiumize.Premiumize().clear_finished_transfers()

	elif action and action.startswith('rd_'):
		if action == 'rd_ServiceNavigator':
			from resources.lib.menus import navigator
			navigator.Navigator().realdebrid_service(folderName=folderName)
		elif action == 'rd_AccountInfo':
			from resources.lib.debrid import realdebrid
			realdebrid.RealDebrid().account_info_to_dialog()
		elif action == 'rd_Authorize':
			from resources.lib.debrid import realdebrid
			realdebrid.RealDebrid().auth(fromSettings=1)
		elif action == 'rd_Revoke':
			from resources.lib.debrid import realdebrid
			realdebrid.RealDebrid().reset_authorization(fromSettings=1)
		elif action == 'rd_UserTorrentsToListItem':
			from resources.lib.debrid import realdebrid
			realdebrid.RealDebrid().user_torrents_to_listItem()
		elif action == 'rd_MyDownloads':
			from resources.lib.debrid import realdebrid
			realdebrid.RealDebrid().my_downloads_to_listItem(int(query))
		elif action == 'rd_BrowseUserTorrents':
			from resources.lib.debrid import realdebrid
			realdebrid.RealDebrid().browse_user_torrents(params.get('id'))
		elif action == 'rd_DeleteUserTorrent':
			from resources.lib.debrid import realdebrid
			realdebrid.RealDebrid().delete_user_torrent(params.get('id'), name)
		elif action == 'rd_DeleteDownload':
			from resources.lib.debrid import realdebrid
			realdebrid.RealDebrid().delete_download(params.get('id'), name)

	####################################################
	#---Anime
	####################################################
	elif action and action.startswith('anime_'):
		if action == 'anime_Navigator':
			from resources.lib.menus import navigator
			navigator.Navigator().anime(folderName=folderName)
		elif action == 'anime_Movies':
			from resources.lib.menus import movies
			movies.Movies().get(url, folderName=folderName)
		elif action == 'anime_TVshows':
			from resources.lib.menus import tvshows
			tvshows.TVshows().get(url, folderName=folderName)

	elif action == 'trakt_Navigator':
		from resources.lib.menus import navigator
		navigator.Navigator().traktLists(folderName=folderName)
	####################################################
	#---YouTube
	####################################################
	elif action == 'youtube':
		from resources.lib.menus import youtube
		id = params.get('id')
		if id is None: youtube.yt_index().root(action, folderName=folderName)
		else: youtube.yt_index().get(action, id)
	elif action == 'sectionItem':
		pass # Placeholder. This is a non-clickable menu item for notes, etc.

	####################################################
	#---Strm
	####################################################
	elif action == 'createStrm':
		caller = params.get('caller')
		image = params.get('image')
		if caller == 'sources':
				control.busy()
				try:
					from json import loads as jsloads
					from resources.lib.modules import sources
					from resources.lib.modules import downloader
					downloader.createStrm(name, image, sources.Sources().sourcesResolve(jsloads(source)[0]), title)
				except:
					import traceback
					traceback.print_exc()

	####################################################
	#---Download
	####################################################
	elif action and action.startswith('download'):
		if action == 'downloadNavigator':
			from resources.lib.menus import navigator
			navigator.Navigator().downloads(folderName=folderName)
		elif action == 'download':
			caller = params.get('caller')
			image = params.get('image')
			if control.setting('debug.level') == '1':
				from resources.lib.modules import log_utils
				log_utils.log('caller: %s' % caller, __name__)
				log_utils.log('title: %s' % title, __name__)


			if caller == 'sources': # future, move to downloader module for pack support
				control.busy()
				try:
					from json import loads as jsloads
					from resources.lib.modules import sources
					from resources.lib.modules import downloader


					if control.setting('debug.level') == '1':
						from resources.lib.modules import log_utils
						log_utils.log('source: %s' % str(source), __name__)

					info = jsloads(source)[0]
					pack = info.get('package')
					if control.setting('debug.level') == '1':
						log_utils.log('pack: %s' % pack, __name__)


					# downloader.download(name, image, sources.Sources().sourcesResolve(jsloads(source)[0]), title)
					downloader.download(name, image, sources.Sources().sourcesResolve(jsloads(source)[0]), title, pack)

				except:
					import traceback
					traceback.print_exc()
			if caller == 'alldebrid':
				control.busy()
				try:
					from resources.lib.modules import downloader
					from resources.lib.debrid import alldebrid
					downloader.download(name, image, alldebrid.AllDebrid().unrestrict_link(url.replace(' ', '%20')))
				except:
					import traceback
					traceback.print_exc()
			if caller == 'easynews':
				control.busy()
				try:
					from resources.lib.modules import downloader
					downloader.download(name, image, url)
				except:
					import traceback
					traceback.print_exc()
			if caller == 'premiumize':
				control.busy()
				try:
					from resources.lib.modules import downloader
					from resources.lib.debrid import premiumize
					downloader.download(name, image, premiumize.Premiumize().add_headers_to_url(url.replace(' ', '%20')))
				except:
					import traceback
					traceback.print_exc()
			if caller == 'realdebrid':
				control.busy()
				try:
					from resources.lib.modules import downloader
					from resources.lib.debrid import realdebrid
					if params.get('type') == 'unrestrict':
						downloader.download(name, image, realdebrid.RealDebrid().unrestrict_link(url.replace(' ', '%20')))
					else:
						downloader.download(name, image, url.replace(' ', '%20'))
				except:
					import traceback
					traceback.print_exc()
	####################################################
	#---Color Picker
	####################################################
	elif action == 'colorpicker':
		control.showColorPicker(current_setting)

	elif action == 'resetCustomBG':
		from resources.lib.modules import tools
		tools.resetCustomBG()
	####################################################
	#---Tools
	####################################################
	elif action and action.startswith('tools_'):
		if action == 'tools_ShowNews':
			from resources.lib.modules import newsinfo
			newsinfo.news()
		if action == 'tools_openSubsTest':
			from resources.lib.modules import opensubs
			opensubs.Opensubs().getAccountStatus()
		if action == 'tools_openSubsRevoke':
			from resources.lib.modules import opensubs
			opensubs.Opensubs().revokeAccess()
		elif action == 'tools_ShowChangelog':
			from resources.lib.modules import changelog
			changelog.get(name)
		elif action == 'tools_ShowHelp':
			from resources.help import help
			help.get(name)
		elif action == 'tools_LanguageInvoker':
			from resources.lib.modules import language_invoker
			language_invoker.set_reuselanguageinvoker(fromSettings=name)
		elif action == 'tools_iconPack':
			from resources.lib.modules import skin_packs
			skin_packs.iconPackHandler().show_skin_packs()
		elif action == 'tools_toolNavigator':
			from resources.lib.menus import navigator
			navigator.Navigator().tools(folderName=folderName)
		elif action == 'tools_traktToolsNavigator':
			from resources.lib.menus import navigator
			navigator.Navigator().traktTools(folderName=folderName)
		elif action == 'tools_searchNavigator':
			from resources.lib.menus import navigator
			navigator.Navigator().search(folderName=folderName)
		elif action == 'tools_viewsNavigator':
			from resources.lib.menus import navigator
			navigator.Navigator().views()
		elif action == 'tools_loggingNavigator':
			from resources.lib.menus import navigator
			navigator.Navigator().loggingNavigator(folderName=folderName)
		elif action == 'tools_addView':
			from resources.lib.modules import views
			views.addView(params.get('content'))
		elif action == 'tools_resetViewTypes':
			from resources.lib.modules import views
			views.clearViews()
		elif action == 'tools_cleanSettings':
			from resources.lib.modules import clean_settings
			clean_settings.clean_settings()
		elif action == 'tools_subsList':
			from resources.lib.modules import sources
			sources.Sources().getSubsList()
		elif action == 'tools_deleteSettings':
			control.removeCorruptSettings()
		elif action == 'tools_openSettings':
			control.openSettings(query)
		elif action == 'tools_contextUmbrellaSettings':
			control.openSettings('0.0', 'context.umbrella')
			control.trigger_widget_refresh()
		elif action == 'tools_traktManager':
			from resources.lib.modules import trakt
			watched = (params.get('watched') == 'True') if params.get('watched') else None
			unfinished = (params.get('unfinished') == 'True') if params.get('unfinished') else False
			tvshow = (params.get('tvshow') == 'tvshow')
			trakt.manager(name, imdb, tvdb, season, episode, watched=watched, unfinished=unfinished,tvshow=tvshow)
		elif action == 'tools_likeList':
			from resources.lib.modules import trakt
			trakt.like_list(params.get('list_owner'), params.get('list_name'), params.get('list_id'))
		elif action == 'tools_unlikeList':
			from resources.lib.modules import trakt
			trakt.unlike_list(params.get('list_owner'), params.get('list_name'), params.get('list_id'))
		elif action == 'tools_forceTraktSync':
			from resources.lib.modules import trakt
			trakt.force_traktSync()
		elif action == 'tools_clearLogFile':
			from resources.lib.modules import log_utils
			cleared = log_utils.clear_logFile()
			if cleared == 'canceled': return
			elif cleared: control.notification(message='Umbrella Log File Successfully Cleared')
			else: control.notification(message='Error clearing Umbrella Log File, see kodi.log for more info')
		elif action == 'tools_viewLogFile':
			from resources.lib.modules import log_utils
			log_utils.view_LogFile(name)
		elif action == 'tools_uploadLogFile':
			from resources.lib.modules import log_utils
			log_utils.upload_LogFile(name)
		elif action == 'tools_traktLikedListManager':
			from resources.lib.menus import movies
			movies.Movies().likedListsManager()
		elif action == 'tools_traktImportListManager':
			isFromSettings=False
			if query == 'settings':
				isFromSettings=True
			from resources.lib.modules import library
			library.lib_tools().importListsManager(isFromSettings)
		elif action == 'tools_traktImportListsNow':
			isFromSettings=False
			if query == 'settings':
				isFromSettings=True
			from resources.lib.modules import library
			library.lib_tools().importListsNow(isFromSettings)
		elif action == 'tools_traktImportListsNowNoSelect':
			isFromSettings=False
			if query == 'settings':
				isFromSettings=True
			from resources.lib.modules import library
			library.lib_tools().importListsNowNoSelect(isFromSettings)
		elif action == 'tools_umbrellaProper':
			from resources.lib.modules import tools
			tools.nonsense()
		elif action == 'tools_umbrellaExternalProvider':
			from resources.lib.modules import tools
			tools.external_providers()


	####################################################
	#---Play
	####################################################
	elif action and action.startswith('play_'):
		#control.checkPlayNextEpisodes()
		if action == 'play_Item':
			from resources.lib.modules import sources
			sources.Sources(params.get('all_providers')).play(title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, params.get('premiered'), params.get('meta'), params.get('select'), params.get('rescrape'))
		elif action == 'play_info':
			from resources.lib.modules import sources
			sources.Sources(params.get('all_providers')).play(title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, params.get('premiered'), params.get('meta'), params.get('select'), params.get('rescrape'))
			# import xbmc
			# if str(xbmc.getInfoLabel("Window.Property(xmlfile)")) == 'DialogVideoInfo.xml':
			# 	from resources.lib.modules import sources
			# 	sources.Sources(params.get('all_providers')).play(title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, params.get('premiered'), params.get('meta'), params.get('select'), params.get('rescrape'))
			# else: 
			# 	control.execute('Action(Info)')
		elif action == "play_preScrapeNext":
			from resources.lib.modules.player import PlayNext
			PlayNext().prescrapeNext()
		elif action == "play_nextWindowXML":
			from resources.lib.modules.player import PlayNext
			play_next = PlayNext()
			play_next.display_xml()
			del play_next
		elif action == 'play_All': # context menu works same as "Play from Here"
			control.player2().play(control.playlist) 
		elif action == 'play_URL':
			caller = params.get('caller')
			if caller == 'realdebrid':
				from resources.lib.debrid import realdebrid
				if params.get('type') == 'unrestrict':
					from resources.lib.modules import log_utils
					log_utils.log('Real-Debrid play_URL type: unrestrict with URL: %s' % str(url.replace(' ', '%20')), level=log_utils.LOGDEBUG)
					control.player.play(realdebrid.RealDebrid().unrestrict_link(url.replace(' ', '%20')))
				else:
					from resources.lib.modules import log_utils
					log_utils.log('Real-Debrid play_URL with URL: %s' % str(url.replace(' ', '%20')), level=log_utils.LOGDEBUG)
					control.player.play(url.replace(' ', '%20'))
			elif caller == 'alldebrid':
				from resources.lib.debrid import alldebrid
				if params.get('type') == 'unrestrict': control.player.play(alldebrid.AllDebrid().unrestrict_link(url.replace(' ', '%20')))
				else: control.player.play(url.replace(' ', '%20'))
			else:
				control.player.play(url.replace(' ', '%20'))
		elif action == 'play_EpisodesList': # global context option
			from json import dumps as jsdumps
			from resources.lib.menus import episodes
			items = episodes.Episodes().get(tvshowtitle, year, imdb, tmdb, tvdb, params.get('meta'), season, episode, create_directory=False)
			control.playlist.clear()
			for i in items:
				title = i['title']
				systitle = quote_plus(title)
				year = i['year']
				imdb = i['imdb']
				tmdb = i['tmdb']
				tvdb = i['tvdb']
				season = i['season']
				episode = i['episode']
				tvshowtitle = i['tvshowtitle']
				systvshowtitle = quote_plus(tvshowtitle)
				premiered = i['premiered']
				sysmeta = quote_plus(jsdumps(i))
				url = 'plugin://plugin.video.umbrella/?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&select=1' % (
										systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, premiered, sysmeta)
				item = control.item(label=title, offscreen=True)
				control.playlist.add(url=url, listitem=item)
			control.player2().play(control.playlist)

		elif action == 'play_Trailer':
			from resources.lib.modules import trailer
			windowedtrailer = params.get('windowedtrailer')
			windowedtrailer = int(windowedtrailer) if windowedtrailer in ("0","1") else 0
			trailer.Trailer().play(params.get('type'), name, year, url, imdb, windowedtrailer)
		elif action == 'play_Trailer_Context':
			from resources.lib.modules import trailer
			windowedtrailer = params.get('windowedtrailer')
			windowedtrailer = int(windowedtrailer) if windowedtrailer in ("0","1") else 0
			trailer.Trailer().playContext(params.get('type'), name, year, url, imdb, windowedtrailer)
		elif action == 'play_Trailer_Select':
			from resources.lib.modules import trailer
			windowedtrailer = params.get('windowedtrailer')
			windowedtrailer = int(windowedtrailer) if windowedtrailer in ("0","1") else 0
			trailer.Trailer().play_select(params.get('type'), name, year, windowedtrailer)
		elif action == 'play_Random':
			rtype = params.get('rtype')
			if rtype == 'movie':
				from resources.lib.menus import movies
				rlist = movies.Movies().get(url, create_directory=False)
				r = 'plugin://plugin.video.umbrella/?action=play_Item'
			elif rtype == 'episode':
				from resources.lib.menus import episodes
				rlist = episodes.Episodes().get(tvshowtitle, year, imdb, tmdb, tvdb, params.get('meta'), season, create_directory=False)
				r = 'plugin://plugin.video.umbrella/?action=play_Item'
			elif rtype == 'season':
				from resources.lib.menus import seasons
				rlist = seasons.Seasons().get(tvshowtitle, year, imdb, tmdb, tvdb, params.get('art'), create_directory=False)
				r = 'plugin://plugin.video.umbrella/?action=play_Random&rtype=episode'
			elif rtype == 'show':
				from resources.lib.menus import tvshows
				rlist = tvshows.TVshows().get(url, create_directory=False)
				r = 'plugin://plugin.video.umbrella/?action=play_Random&rtype=season'
			from random import randint
			from json import dumps as jsdumps
			try:
				rand = randint(1,len(rlist))-1
				for p in ('title', 'year', 'imdb', 'tmdb', 'tvdb', 'season', 'episode', 'tvshowtitle', 'premiered', 'select'):
					if rtype == "show" and p == "tvshowtitle":
						try: r += '&' + p + '=' + quote_plus(rlist[rand]['title'])
						except: pass
					else:
						try: r += '&' + p + '=' + quote_plus(str(rlist[rand][p]))
						except: pass
				try: r += '&meta=' + quote_plus(jsdumps(rlist[rand]))
				except: r += '&meta=' + quote_plus("{}")
				if rtype == "movie":
					try: control.notification(title=32536, message='%s (%s)' % (rlist[rand]['title'], rlist[rand]['year']))
					except: pass
				elif rtype == "episode":
					try: control.notification(title=32536, message='%s - %01dx%02d - %s' % (rlist[rand]['tvshowtitle'], int(rlist[rand]['season']), int(rlist[rand]['episode']), rlist[rand]['title']))
					except: pass
				if 'play_Item' in r: control.execute('PlayMedia(%s)' % r)
				else: control.execute('RunPlugin(%s)' % r)
			except: control.notification(message=32537)

	elif action == 'play': # for support of old style .strm library files
		from resources.lib.modules import sources
		sources.Sources(params.get('all_providers')).play(title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, params.get('premiered'), params.get('meta'), params.get('select'), params.get('rescrape'))

	####################################################
	#---Playlist
	####################################################
	elif action and action.startswith('playlist_'):
		if action == 'playlist_Manager':
			from resources.lib.modules import playlist
			playlist.playlistManager(name, url, params.get('meta'), params.get('art'))
		elif action == 'playlist_Show':
			from resources.lib.modules import playlist
			playlist.playlistShow()
		elif action == 'playlist_Clear':
			from resources.lib.modules import playlist
			playlist.playlistClear()
		elif action == 'playlist_QueueItem':
			control.queueItem()
			if name is None: control.notification(title=35515, message=35519)
			else: control.notification(title=name, message=35519)
	####################################################
	#---Account Actions
	####################################################
	elif action == 'tmdb_Auth':
		from resources.lib.indexers.tmdb import Auth as tmdb_auth
		tmdb_auth().create_session_id(fromSettings=1)
	elif action == 'tmdb_Revoke':
		from resources.lib.indexers.tmdb import Auth as tmdb_auth
		tmdb_auth().revoke_session_id(fromSettings=1)
	# elif action == 'fk_getApiKey':
	# 	from resources.lib.debrid import furk
	# 	furk.Furk().get_api()
	# elif action == 'fk_revokeApiKey':
	# 	from resources.lib.debrid import furk
	# 	furk.Furk().clear_api()
	####################################################
	#---Playcount
	####################################################
	elif action and action.startswith('playcount_'):
		if action == 'playcount_Movie':
			from resources.lib.modules import playcount
			playcount.movies(name, imdb, query)
		elif action == 'playcount_Episode':
			from resources.lib.modules import playcount
			playcount.episodes(name, imdb, tvdb, season, episode, query)
		elif action == 'playcount_TVShow':
			from resources.lib.modules import playcount
			playcount.tvshows(name, imdb, tvdb, season, query)

	####################################################
	#---Source Actions
	####################################################
	elif action == 'alterSources':
		from resources.lib.modules import sources
		sources.Sources().alterSources(url, params.get('meta'))
	elif action == 'showDebridPack':
		from resources.lib.modules.sources import Sources
		Sources().debridPackDialog(params.get('caller'), name, url, source)
	elif action == 'sourceInfo':
		from resources.lib.modules.sources import Sources
		Sources().sourceInfo(source)
	elif action == 'cacheTorrent':
		caller = params.get('caller')
		pack = True if params.get('type') == 'pack' else False
		if caller == 'Real-Debrid':
			from resources.lib.debrid.realdebrid import RealDebrid as debrid_function
		elif caller == 'Premiumize':
			from resources.lib.debrid.premiumize import Premiumize as debrid_function
		elif caller == 'AllDebrid':
			from resources.lib.debrid.alldebrid import AllDebrid as debrid_function
		success = debrid_function().add_uncached_torrent(url, pack=pack)
		if success:
			from resources.lib.modules import sources
			sources.Sources().playItem(title, params.get('items'), source, params.get('meta'))

	elif action == 'rescrapeAuto':
		from resources.lib.modules import sources
		premiered = params.get('premiered')
		meta = params.get('meta')
		sources.Sources(all_providers='true', rescrapeAll='true').play(title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, premiered, meta, select=select, rescrape='true')
	elif action == 'rescrapeMenu':
		from resources.lib.modules import sources
		premiered = params.get('premiered')
		meta = params.get('meta')
		highlight_color = control.setting('highlight.color')
		items = [
			control.lang(32207),
			control.lang(32208),
			control.lang(32209) % highlight_color, 
			control.lang(32210) % highlight_color, 
			control.lang(32216) % highlight_color, 
			control.lang(32217) % highlight_color,
			control.lang(32232) % (highlight_color, highlight_color)]
		select = control.selectDialog(items, heading=control.addonInfo('name') + ' - ' + 'Rescrape Options Menu')
		if select == -1: return control.closeAll()
		if select >= 0:
			if select == 0: sources.Sources().play(title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, premiered, meta, select='1', rescrape='true')
			elif select == 1: sources.Sources().play(title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, premiered, meta, select='0', rescrape='true')
			elif select == 2: sources.Sources(all_providers='true').play(title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, premiered, meta, select='1', rescrape='true')
			elif select == 3: sources.Sources(all_providers='true').play(title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, premiered, meta, select='0', rescrape='true')
			elif select == 4: sources.Sources(custom_query='true').play(title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, premiered, meta, select='0', rescrape='true')
			elif select == 5: sources.Sources(all_providers='true', custom_query='true').play(title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, premiered, meta, select='0', rescrape='true')
			elif select == 6: sources.Sources(all_providers='true', filterless_scrape='true').play(title, year, imdb, tmdb, tvdb, season, episode, tvshowtitle, premiered, meta, select='0', rescrape='true')
	####################################################
	#---Library Actions
	####################################################
	elif action and action.startswith('library_'):
		if action == 'library_Navigator':
			from resources.lib.menus import navigator
			navigator.Navigator().library(folderName=folderName)
		elif action == 'library_movieToLibrary':
			from resources.lib.modules import library
			library.libmovies().add(name, title, year, imdb, tmdb)
		elif action == 'library_moviesToLibrary':
			from resources.lib.modules import library
			library.libmovies().range(url, name)
		elif action == 'library_moviesListToLibrary':
			# from resources.lib.menus import movies
			# movies.Movies().moviesListToLibrary(url)
			control.notification(message=40228)
		elif action == 'library_moviesToLibrarySilent':
			from resources.lib.modules import library
			library.libmovies().silent(url)
		elif action == 'library_tvshowToLibrary':
			from resources.lib.modules import library
			library.libtvshows().add(tvshowtitle, year, imdb, tmdb, tvdb)
		elif action == 'library_tvshowsToLibrary':
			#from resources.lib.modules import library
			#library.libtvshows().range(url, name)
			control.notification(message=40228)
		elif action == 'library_tvshowsListToLibrary':
			# from resources.lib.menus import tvshows
			# tvshows.TVshows().tvshowsListToLibrary(url)
			control.notification(message=40228)
		elif action == 'library_tvshowsToLibrarySilent':
			from resources.lib.modules import library
			library.libtvshows().silent(url)
		elif action == 'library_update':
			control.notification(message=32085)
			from resources.lib.modules import library
			library.libepisodes().update()
			library.libmovies().list_update()
			library.libtvshows().list_update()
			while True:
				if control.condVisibility('Library.IsScanningVideo'):
					control.sleep(3000)
					continue
				else: break
			control.sleep(1000)
			control.notification(message=32086)
		elif action == 'library_clean':
			from resources.lib.modules import library
			library.lib_tools().clean()
		elif action == 'library_setup':
			from resources.lib.modules import library
			library.lib_tools().total_setup()
		# elif action == 'library_monitor_userlist':
		# 	from resources.lib.modules import library
		# 	library.libuserlist().userlist()

	elif action == 'testCustomOK':
		control.openSettings('0.2', 'plugin.video.umbrella')
		control.okDialog(title=control.lang(40427), message=control.lang(40428))
	elif action == 'testCustomConfirm':
		control.openSettings('0.2', 'plugin.video.umbrella')
		control.yesnoDialog(control.lang(40428),'','',"Test Confirm Dialog", 'Cancel','OK', None)
	####################################################
	#---Cache
	####################################################
	elif action and action.startswith('cache_'):
		if action == 'cache_Navigator':
			from resources.lib.menus import navigator
			navigator.Navigator().cf(folderName=folderName)
		elif action == 'cache_clearAll':
			from resources.lib.menus import navigator
			navigator.Navigator().clearCacheAll()
		elif action == 'cache_clearSources':
			from resources.lib.menus import navigator
			navigator.Navigator().clearCacheProviders()
		elif action == 'cache_clearMeta':
			from resources.lib.menus import navigator
			navigator.Navigator().clearCacheMeta()
		elif action == 'cache_clearCache':
			from resources.lib.menus import navigator
			navigator.Navigator().clearCache()
		elif action == 'cache_fanart':
			from resources.lib.menus import navigator
			navigator.Navigator().clearFanart()
		elif action == 'cache_clearMovieCache':
			from resources.lib.menus import navigator
			navigator.Navigator().clearMovieCache()
		elif action == 'cache_clearMetaAndCache':
			from resources.lib.menus import navigator
			navigator.Navigator().clearMetaAndCache()
		elif action == 'cache_clearSearch':
			from resources.lib.menus import navigator
			navigator.Navigator().clearCacheSearch() 
		elif action == 'cache_clearSearchPhrase':
			from resources.lib.menus import navigator
			navigator.Navigator().clearCacheSearchPhrase(source, name)
		elif action == 'cache_clearBookmarks':
			from resources.lib.menus import navigator
			navigator.Navigator().clearBookmarks()
		elif action == 'cache_clearBookmark':
			from resources.lib.menus import navigator
			navigator.Navigator().clearBookmark(name, year)
		elif action == 'cache_clearKodiBookmark': # context.umbrella action call only
			from resources.lib.database import cache
			cache.clear_local_bookmark(url)
		elif action == 'cache_clearThumbnails':
			from resources.lib.menus import navigator
			navigator.Navigator().clearThumbnails()