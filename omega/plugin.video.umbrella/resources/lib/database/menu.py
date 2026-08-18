# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

import sqlite3 as db
from resources.lib.modules import control

menuFile = control.joinPath(control.dataPath, 'menu.db')

# Tuple format:
# (item_id, label, action, icon, poster, is_folder, is_action, enabled, sort_order, is_custom, condition_key, queue, alt_label)
# label     = string ID used when "Add meta provider labels" is ON  (e.g. "TMDb: Popular")
# alt_label = string ID used when the setting is OFF (e.g. "Popular"); None means same as label

_ROOT_DEFAULTS = [
	('searchMovies',    '33042', 'movieSearch',                            'trakt.png',        'searchmovies.png', 1, 1, 1, 0,  0, None, 0, None),
	('searchTVShows',   '33043', 'tvSearch',                               'trakt.png',        'searchtv.png',     1, 1, 1, 1,  0, None, 0, None),
	('movies',          '33046', 'movieNavigator',                         'movies.png',       'movies.png',       1, 1, 1, 2,  0, None, 0, None),
	('tvshows',         '33047', 'tvNavigator',                            'tvshows.png',      'tvshows.png',      1, 1, 1, 3,  0, None, 0, None),
	('anime',           'Anime', 'anime_Navigator',                        'boxsets.png',      'boxsets.png',      1, 1, 1, 4,  0, None, 0, None),
	('myMovies',        '32003', 'mymovieNavigator',                       'mymovies.png',     'mymovies.png',     1, 1, 1, 5,  0, None, 0, None),
	('myTVShows',       '32004', 'mytvNavigator',                          'mytvshows.png',    'mytvshows.png',    1, 1, 1, 6,  0, None, 0, None),
	('youtube',         'YouTube Videos', 'youtube',                       'youtube.png',      'youtube.png',      1, 1, 1, 7,  0, None, 0, None),
	('search',          '32010', 'tools_searchNavigator',                  'search.png',       'search.png',       1, 1, 1, 8,  0, None, 0, None),
	('tools',           '32008', 'tools_toolNavigator',                    'tools.png',        'tools.png',        1, 1, 1, 9,  0, None, 0, None),
	('downloads',       '32009', 'downloadNavigator',                      'downloads.png',    'downloads.png',    1, 1, 1, 10, 0, None, 0, None),
	('favourites',      '40464', 'favouriteNavigator',                     'highly-rated.png', 'highly-rated.png', 1, 1, 1, 11, 0, None, 0, None),
	('premiumServices', 'Premium Services', 'premiumNavigator',            'premium.png',      'premium.png',      1, 1, 1, 12, 0, None, 0, None),
	('changelog',       '32014', 'tools_ShowChangelog&name=Umbrella',      'changelog.png',    'changelog.png',    0, 1, 0, 13, 0, None, 0, None),
	('fullChangelog',   '40589', 'tools_ShowFullChangelog&name=Umbrella',  'changelog.png',    'changelog.png',    0, 1, 0, 14, 0, None, 0, None),
]

_MOVIES_DEFAULTS = [
	('mv_tmdb_nowplaying',     '32423', 'tmdbmovies&url=tmdb_nowplaying',                    'tmdb.png',        'in-theaters.png',   1, 1, 1,  0, 0, None,             0, '32422'),
	('mv_trakt_anticipated',   '32425', 'movies&url=traktanticipated',                        'trakt.png',       'in-theaters.png',   1, 1, 1,  1, 0, None,             0, '32424'),
	('mv_tmdb_upcoming',       '32427', 'tmdbmovies&url=tmdb_upcoming',                       'tmdb.png',        'in-theaters.png',   1, 1, 1,  2, 0, None,             0, '32426'),
	('mv_tmdb_disc_released',  '40268', 'tmdbmovies&url=tmdb_discovery_released',             'tmdb.png',        'trending.png',      1, 1, 1,  3, 0, None,             0, '40269'),
	('mv_tmdb_disc_month',     '40410', 'tmdbmovies&url=tmdb_discovery_this_month',           'tmdb.png',        'trending.png',      1, 1, 1,  4, 0, None,             0, '40411'),
	('mv_tmdb_disc_month_rel', '40412', 'tmdbmovies&url=tmdb_discovery_this_month_released',  'tmdb.png',        'trending.png',      1, 1, 1,  5, 0, None,             0, '40413'),
	('mv_dvd_release',         '40474', 'dvdReleaseList',                                     'tmdb.png',        'trending.png',      1, 1, 1,  6, 0, None,             0, '40475'),
	('mv_tmdb_popular',        '32431', 'tmdbmovies&url=tmdb_popular',                        'tmdb.png',        'most-popular.png',  1, 1, 1,  7, 0, None,             0, '32430'),
	('mv_trakt_popular',       '32433', 'movies&url=traktpopular',                            'trakt.png',       'most-popular.png',  1, 1, 1,  8, 0, None,             0, '32430'),
	('mv_tmdb_boxoffice',      '32436', 'tmdbmovies&url=tmdb_boxoffice',                      'tmdb.png',        'box-office.png',    1, 1, 1,  9, 0, None,             0, '32434'),
	('mv_trakt_boxoffice',     '32437', 'movies&url=traktboxoffice',                          'trakt.png',       'box-office.png',    1, 1, 1, 10, 0, None,             0, '32434'),
	('mv_tmdb_toprated',       '32441', 'tmdbmovies&url=tmdb_toprated',                       'tmdb.png',        'most-voted.png',    1, 1, 1, 11, 0, None,             0, '32440'),
	('mv_trakt_trending',      '32443', 'movies&url=trakttrending',                           'trakt.png',       'trending.png',      1, 1, 1, 12, 0, None,             0, '32442'),
	('mv_trakt_trend_recent',  '40388', 'movies&url=trakttrending_recent',                    'trakt.png',       'trending.png',      1, 1, 1, 13, 0, None,             0, '40389'),
	('mv_simkl_today',         '40350', 'simklMovies&url=simkltrendingtoday',                 'simkl.png',       'trending.png',      1, 1, 1, 14, 0, 'simkl_token',    0, '40351'),
	('mv_simkl_week',          '40352', 'simklMovies&url=simkltrendingweek',                  'simkl.png',       'trending.png',      1, 1, 1, 15, 0, 'simkl_token',    0, '40353'),
	('mv_simkl_month',         '40354', 'simklMovies&url=simkltrendingmonth',                 'simkl.png',       'trending.png',      1, 1, 1, 16, 0, 'simkl_token',    0, '40355'),
	('mv_tmdb_trend_day',      '40330', 'movies&url=tmdbrecentday',                           'tmdb.png',        'trending.png',      1, 1, 1, 17, 0, None,             0, '40702'),
	('mv_tmdb_trend_week',     '40331', 'movies&url=tmdbrecentweek',                          'tmdb.png',        'trending.png',      1, 1, 1, 18, 0, None,             0, '40703'),
	('mv_trakt_recommended',   '32445', 'movies&url=traktrecommendations',                    'trakt.png',       'highly-rated.png',  1, 1, 1, 19, 0, None,             0, '32444'),
	('mv_lib_similar',         '40392', 'moviesimilarFromLibrary',                            'most-popular.png','most-popular.png',  1, 1, 1, 20, 0, 'has_lib_movies', 0, None),
	('mv_lib_recommended',     '40393', 'movierecommendedFromLibrary',                        'featured.png',    'featured.png',      1, 1, 1, 21, 0, 'has_lib_movies', 0, None),
	('mv_trakt_recent',        '40255', 'movies&url=traktbasedonrecent',                      'trakt.png',       'years.png',         1, 1, 1, 22, 0, None,             0, '40256'),
	('mv_trakt_similar',       '40260', 'movies&url=traktbasedonsimilar',                     'trakt.png',       'years.png',         1, 1, 1, 23, 0, None,             0, '40261'),
	('mv_oscar_nominees',      '32452', 'movies&url=oscars',                                  'trakt.png',       'oscar-winners.png', 1, 1, 1, 24, 0, None,             0, '32451'),
	('mv_tmdb_genres',         '32486', 'movieGenres&url=tmdb_genre',                         'tmdb.png',        'genres.png',        1, 1, 1, 25, 0, None,             0, '32455'),
	('mv_trakt_genres',        '40493', 'movieGenres&url=trakt_movie_genre',                  'trakt.png',       'genres.png',        1, 1, 1, 26, 0, None,             0, '32455'),
	('mv_tmdb_years',          '32485', 'movieYears&url=tmdb_year',                           'tmdb.png',        'years.png',         1, 1, 1, 27, 0, None,             0, '32457'),
	('mv_tmdb_certs',          '32487', 'movieCertificates&url=tmdb_certification',           'tmdb.png',        'certificates.png',  1, 1, 1, 28, 0, None,             0, '32463'),
	('mv_collections',         '32000', 'collections_Navigator',                              'boxsets.png',     'boxsets.png',       1, 1, 1, 29, 0, None,             0, None),
	('mv_mdb_top_lists',       '40084', 'mdbTopListMovies',                                   'mdblist.png',     'movies.png',        1, 1, 1, 30, 0, 'mdblist_token',  0, None),
	('mv_mdb_official',        '40711', 'mdbOfficialListMovies',                              'mdblist.png',     'movies.png',        1, 1, 1, 31, 0, 'mdblist_token',  0, None),
	('mv_trakt_pop_lists',     '32417', 'movies_PublicLists&url=trakt_popularLists',          'trakt.png',       'movies.png',        1, 1, 1, 32, 0, None,             0, None),
	('mv_trakt_trend_lists',   '32418', 'movies_PublicLists&url=trakt_trendingLists',         'trakt.png',       'movies.png',        1, 1, 1, 33, 0, None,             0, None),
	('mv_trakt_search_lists',  '32419', 'movies_SearchLists&media_type=movies',               'trakt.png',       'movies.png',        0, 1, 1, 34, 0, None,             0, None),
	('mv_mylists_widget',      '32003', 'mymovieliteNavigator',                               'mymovies.png',    'mymovies.png',      1, 1, 1, 35, 0, 'not_lite',       0, None),
	('mv_fav_movies',          '40465', 'getFavouritesMovies&url=favourites_movies',          'movies.png',      'movies.png',        1, 1, 1, 36, 0, 'favorite_movie', 0, None),
	('mv_person_search',       '33044', 'moviePerson',                                        'imdb.png',        'people-search.png', 0, 1, 1, 37, 0, 'not_lite',       0, None),
	('mv_movie_search',        '33042', 'movieSearch',                                        'trakt.png',       'search.png',        1, 1, 1, 38, 0, 'not_lite',       0, None),
]

_TVSHOWS_DEFAULTS = [
	('tv_originals',          '40077', 'tvOriginals',                             'tvmaze.png',  'networks.png',     1, 1, 1,  0, 0, None,              0, '40070'),
	('tv_tmdb_popular',       '32431', 'tmdbTvshows&url=tmdb_popular',            'tmdb.png',    'most-popular.png', 1, 1, 1,  1, 0, None,              1, '32430'),
	('tv_trakt_popular',      '32433', 'tvshows&url=traktpopular',                'trakt.png',   'most-popular.png', 1, 1, 1,  2, 0, None,              1, '32430'),
	('tv_tmdb_toprated',      '32441', 'tmdbTvshows&url=tmdb_toprated',           'tmdb.png',    'most-voted.png',   1, 1, 1,  3, 0, None,              0, '32440'),
	('tv_trakt_trending',     '32443', 'tvshows&url=trakttrending',               'trakt.png',   'trending.png',     1, 1, 1,  4, 0, None,              0, '32442'),
	('tv_trakt_trend_recent', '40388', 'tvshows&url=trakttrending_recent',        'trakt.png',   'trending.png',     1, 1, 1,  5, 0, None,              0, '40389'),
	('tv_simkl_today',        '40350', 'simklTvshows&url=simkltrendingtoday',     'simkl.png',   'trending.png',     1, 1, 1,  6, 0, 'simkl_token',     0, '40351'),
	('tv_simkl_week',         '40352', 'simklTvshows&url=simkltrendingweek',      'simkl.png',   'trending.png',     1, 1, 1,  7, 0, 'simkl_token',     0, '40353'),
	('tv_simkl_month',        '40354', 'simklTvshows&url=simkltrendingmonth',     'simkl.png',   'trending.png',     1, 1, 1,  8, 0, 'simkl_token',     0, '40355'),
	('tv_tmdb_trend_day',     '40330', 'tvshows&url=tmdbrecentday',               'tmdb.png',    'trending.png',     1, 1, 1,  9, 0, None,              0, '40702'),
	('tv_tmdb_trend_week',    '40331', 'tvshows&url=tmdbrecentweek',              'tmdb.png',    'trending.png',     1, 1, 1, 10, 0, None,              0, '40703'),
	('tv_trakt_recommended',  '32445', 'tvshows&url=traktrecommendations',        'trakt.png',   'highly-rated.png', 1, 1, 1, 11, 0, None,              1, '32444'),
	('tv_trakt_recent',       '40255', 'tvshows&url=traktbasedonrecent',          'trakt.png',   'years.png',        1, 1, 1, 12, 0, None,              0, '40256'),
	('tv_trakt_similar',      '40260', 'tvshows&url=traktbasedonsimilar',         'trakt.png',   'years.png',        1, 1, 1, 13, 0, None,              0, '40261'),
	('tv_tmdb_genres',        '32486', 'tvGenres&url=tmdb_genre',                 'tmdb.png',    'genres.png',       1, 1, 1, 14, 0, None,              0, '32455'),
	('tv_trakt_genres',       '40493', 'tvGenres&url=trakt_tvshow_genre',         'trakt.png',   'genres.png',       1, 1, 1, 15, 0, None,              0, '32455'),
	('tv_networks',           '32468', 'tvNetworks',                              'tmdb.png',    'networks.png',     1, 1, 1, 16, 0, None,              0, '32469'),
	('tv_tmdb_years',         '32485', 'tvYears&url=tmdb_year',                   'tmdb.png',    'years.png',        1, 1, 1, 17, 0, None,              0, '32457'),
	('tv_tmdb_airing',        '32467', 'tmdbTvshows&url=tmdb_airingtoday',        'tmdb.png',    'airing-today.png', 1, 1, 1, 18, 0, None,              0, '32465'),
	('tv_tmdb_onair',         '32472', 'tmdbTvshows&url=tmdb_ontheair',           'tmdb.png',    'new-tvshows.png',  1, 1, 1, 19, 0, None,              0, '32471'),
	('tv_tmdb_newshows',      '40661', 'tvshows&url=tmdb_newshows',               'tmdb.png',    'new-tvshows.png',  1, 1, 1, 20, 0, None,              0, '32475'),
	('tv_calendar',           '32450', 'calendars',                               'tvmaze.png',  'calendar.png',     1, 1, 1, 21, 0, None,              0, '32027'),
	('tv_mdb_top_lists',      '40084', 'mdbTopListTV',                            'mdblist.png', 'tvshows.png',      1, 1, 1, 22, 0, 'mdblist_token',   0, None),
	('tv_mdb_official',       '40711', 'mdbOfficialListTV',                       'mdblist.png', 'tvshows.png',      1, 1, 1, 23, 0, 'mdblist_token',   0, None),
	('tv_trakt_pop_lists',    '32417', 'tv_PublicLists&url=trakt_popularLists',   'trakt.png',   'tvshows.png',      1, 1, 1, 24, 0, None,              0, None),
	('tv_trakt_trend_lists',  '32418', 'tv_PublicLists&url=trakt_trendingLists',  'trakt.png',   'tvshows.png',      1, 1, 1, 25, 0, None,              0, None),
	('tv_trakt_search_lists', '32419', 'tv_SearchLists&media_type=shows',         'trakt.png',   'tvshows.png',      0, 1, 1, 26, 0, None,              0, None),
	('tv_mylists_widget',     '32004', 'mytvliteNavigator',                       'mytvshows.png','mytvshows.png',   1, 1, 1, 27, 0, 'not_lite',        0, None),
	('tv_fav_tvshows',        '40466', 'getFavouritesTVShows&url=favourites_tvshows','tvshows.png','tvshows.png',    1, 1, 1, 28, 0, 'favorite_tvshows', 0, None),
	('tv_person_search',      '33045', 'tvPerson',                                'imdb.png',    'people-search.png',0, 1, 1, 29, 0, 'not_lite',        0, None),
	('tv_search',             '33043', 'tvSearch',                                'trakt.png',   'search.png',       1, 1, 1, 30, 0, 'not_lite',        0, None),
]

_MYMOVIES_DEFAULTS = [
	('mymv_userlists',        '32039', 'movieUserlists',                                   'userlists.png', 'userlists.png', 1, 1, 1,  0, 0, None,                   0, None),
	('mymv_fav_movies',       '40465', 'getFavouritesMovies&url=favourites_movies',        'movies.png',    'movies.png',    1, 1, 1,  1, 0, 'favorite_movie',       0, None),
	('mymv_mdblist_folder',   'MDBList',  'mymovies_mdblistNavigator',                     'mdblist.png',   'mdblist.png',   1, 1, 1,  2, 0, 'mdblist_token',        0, None),
	('mymv_custom_folder',    'Custom',   'mymovies_customNavigator',                      'icon.png',      'icon.png',      1, 1, 1,  3, 0, 'custom_token',         0, None),
	('mymv_tmdb_folder',      'TMDb',     'mymovies_tmdbNavigator',                        'tmdb.png',      'tmdb.png',      1, 1, 1,  4, 0, 'tmdb_v4_token',        0, None),
	('mymv_simkl_folder',     'Simkl',    'mymovies_simklNavigator',                       'simkl.png',     'simkl.png',     1, 1, 1,  5, 0, 'simkl_token',          0, None),
	('mymv_trakt_folder',     'Trakt',    'mymovies_traktNavigator',                       'trakt.png',     'trakt.png',     1, 1, 1,  6, 0, 'trakt_credentials',    0, None),
	('mymv_floppy_folder',  'Floppy', 'mymovies_floppyNavigator',                    'floppy.png',  'floppy.png',  1, 1, 1,  7, 0, 'floppy_credentials', 0, None),
	('mymv_local_folder',   'Local',    'mymovies_localNavigator',                       'icon.png',      'icon.png',      1, 1, 1,  8, 0, 'local_scrobble',       0, None),
	('mymv_movies_menu',      '32031', 'movieliteNavigator',                               'movies.png',    'movies.png',    1, 1, 1,  9, 0, 'not_lite',             0, None),
	('mymv_person_search',    '33044', 'moviePerson',                                      'imdb.png',      'people-search.png', 0, 1, 1, 10, 0, 'not_lite',         0, None),
	('mymv_movie_search',     '33042', 'movieSearch',                                      'search.png',    'search.png',    1, 1, 1, 11, 0, 'not_lite',             0, None),
	('mymv_scrob_folder',     'Scrob',    'mymovies_scrobNavigator',                      'scrob.png',     'scrob.png',     1, 1, 1, 12, 0, 'scrob_credentials',    0, None),
]

_MYMOVIES_MDBLIST_DEFAULTS = [
	('mymv_mdb_userlist',     '40681', 'mdbUserListMovies',                                'mdblist.png',   'mdblist.png',   1, 1, 1,  0, 0, 'mdblist_token',        0, '40699'),
	('mymv_mdb_watchlist',    '40682', 'mdbUserWatchListMovies',                           'mdblist.png',   'mdblist.png',   1, 1, 1,  1, 0, 'mdblist_token',        0, '40700'),
	('mymv_mdb_collection',   '40706', 'mdbUserCollectionMovies',                          'mdblist.png',   'mdblist.png',   1, 1, 1,  2, 0, 'mdblist_token',        0, None),
	('mymv_mdb_liked',        '40683', 'mdbLikedListMovies',                               'mdblist.png',   'mdblist.png',   1, 1, 1,  3, 0, 'mdblist_token',        0, '40701'),
	('mymv_mdb_unfinished',   '40686', 'mdblistMoviesUnfinished',                          'mdblist.png',   'mdblist.png',   1, 1, 1,  4, 0, 'mdblist_with_indicators', 1, '35308'),
	('mymv_mdb_watched',      '40716', 'mdblist_movies_watched&url=mdblistwatchedmv',      'mdblist.png',   'mdblist.png',   1, 1, 1,  5, 0, 'mdblist_with_indicators', 1, None),
]

_MYMOVIES_CUSTOM_DEFAULTS = [
	('mymv_custom_watchlist', '40736', 'custom_movies_watchlist&url=custommovieswatchlist',   'icon.png',   'icon.png',      1, 1, 1,  0, 0, 'custom_token',           0, None),
	('mymv_custom_collection','40737', 'custom_movies_collection&url=custommoviescollection', 'icon.png',   'icon.png',      1, 1, 1,  1, 0, 'custom_token',           0, None),
	('mymv_custom_unfinished','40741', 'custom_movies_unfinished&url=custommoviesunfinished', 'icon.png',   'icon.png',      1, 1, 1,  2, 0, 'custom_with_indicators', 1, '35308'),
	('mymv_custom_watched',   '40745', 'custom_movies_watched&url=custommovieswatched',       'icon.png',   'icon.png',      1, 1, 1,  3, 0, 'custom_with_indicators', 1, None),
	('mymv_custom_userlists', '40782', 'custom_movies_userlists',                             'icon.png',   'icon.png',      1, 1, 1,  4, 0, 'custom_token',           1, None),
	# sort_order 99 (not 5): existing users' DBs already have mymv_custom_userlists at
	# position 4 and won't retroactively re-sort it (only label/icon/poster/alt_label sync
	# across an upgrade, per _sync_defaults()'s _field_sync) — a low sort_order here would
	# collide with whatever already occupies position 5 in their menu.
	('mymv_custom_dropped',   '40783', 'custom_movies_dropped&url=custommoviesdropped',       'icon.png',   'icon.png',      1, 1, 1, 99, 0, 'custom_token',           0, None),
]

_MYMOVIES_TMDB_DEFAULTS = [
	('mymv_tmdb_userlists',   'TMDb User Lists', 'tmdbUserListsMovies',                    'tmdb.png',      'tmdb.png',      1, 1, 1,  0, 0, 'tmdb_v4_token',        0, None),
	('mymv_tmdb_watchlist',   '40612', 'tmdbV4WatchlistMovies',                            'tmdb.png',      'tmdb.png',      1, 1, 1,  1, 0, 'tmdb_v4_token',        0, None),
]

_MYMOVIES_SIMKL_DEFAULTS = [
	('mymv_simkl_completed',  '40548', 'movies&url=simklhistory',                          'simkl.png',     'simkl.png',     1, 1, 1,  0, 0, 'simkl_token',          0, None),
	('mymv_simkl_watchlist',  '40550', 'movies&url=simklwatchlist',                        'simkl.png',     'simkl.png',     1, 1, 1,  1, 0, 'simkl_token',          0, None),
	('mymv_simkl_dropped',    'Dropped (Simkl)', 'movies&url=simkldropped',                 'simkl.png',     'simkl.png',     1, 1, 1,  2, 0, 'simkl_token',          0, None),
]

_MYMOVIES_TRAKT_DEFAULTS = [
	('mymv_trakt_unfinished', '40687', 'moviesUnfinished&url=traktunfinished',             'trakt.png',     'trakt.png',     1, 1, 1,  0, 0, 'trakt_with_indicators', 1, '35308'),
	('mymv_trakt_history',    '40695', 'movies&url=trakthistory',                          'trakt.png',     'trakt.png',     1, 1, 1,  1, 0, 'trakt_with_indicators', 1, '32036'),
	('mymv_trakt_watchlist',  '40696', 'movies&url=traktwatchlist',                        'trakt.png',     'trakt.png',     1, 1, 1,  2, 0, 'trakt_credentials',    0, '40700'),
	('mymv_trakt_collection', '40697', 'movies&url=traktcollection',                       'trakt.png',     'trakt.png',     1, 1, 1,  3, 0, 'trakt_credentials',    0, '32032'),
	('mymv_trakt_liked',      '40698', 'movies_LikedLists',                               'trakt.png',     'trakt.png',     1, 1, 1,  4, 0, 'trakt_credentials',     1, 'My Liked Lists'),
]

_MYMOVIES_FLOPPY_DEFAULTS = [
	('mymv_floppy_watching',   'Watching (Floppy)',   'floppy_movies_watching&url=floppymovieswatching',     'floppy.png', 'floppy.png', 1, 1, 1,  0, 0, 'floppy_credentials', 0, None),
	('mymv_floppy_watchlist',  'Watchlist (Floppy)',  'floppy_movies_watchlist&url=floppymovieswatchlist',   'floppy.png', 'floppy.png', 1, 1, 1,  1, 0, 'floppy_credentials', 0, None),
	('mymv_floppy_onhold',     'On Hold (Floppy)',    'floppy_movies_onhold&url=floppymoviesonhold',         'floppy.png', 'floppy.png', 1, 1, 1,  2, 0, 'floppy_credentials', 0, None),
	('mymv_floppy_completed',  'Completed (Floppy)',  'floppy_movies_watched&url=floppymovieswatched',   'floppy.png', 'floppy.png', 1, 1, 1,  3, 0, 'floppy_credentials', 0, None),
	('mymv_floppy_dropped',    'Dropped (Floppy)',    'floppy_movies_dropped&url=floppymoviesdropped',       'floppy.png', 'floppy.png', 1, 1, 1,  4, 0, 'floppy_credentials', 0, None),
	('mymv_floppy_collection', 'Collection (Floppy)', 'floppy_movies_collection&url=floppymoviescollection', 'floppy.png', 'floppy.png', 1, 1, 1,  5, 0, 'floppy_credentials', 0, None),
	('mymv_floppy_unfinished', 'Unfinished (Floppy)', 'floppy_movies_unfinished&url=floppymoviesunfinished', 'floppy.png', 'floppy.png', 1, 1, 1,  6, 0, 'floppy_credentials', 1, '35308'),
	('mymv_floppy_userlists',  'User Lists (Floppy)', 'floppy_movies_userlists', 'floppy.png', 'floppy.png', 1, 1, 1,  7, 0, 'floppy_credentials', 0, None),
]

_MYMOVIES_SCROB_DEFAULTS = [
	('mymv_scrob_watched', 'Watched (Scrob)', 'scrob_movies_watched&url=scrobmovieswatched', 'scrob.png', 'scrob.png', 1, 1, 1, 0, 0, 'scrob_with_indicators', 1, None),
	('mymv_scrob_unfinished', 'Unfinished (Scrob)', 'scrob_movies_unfinished&url=scrobmoviesunfinished', 'scrob.png', 'scrob.png', 1, 1, 1, 1, 0, 'scrob_credentials', 1, '35308'),
	('mymv_scrob_userlists', '40781', 'scrob_movies_userlists', 'scrob.png', 'scrob.png', 1, 1, 1, 2, 0, 'scrob_credentials', 1, None),
]

_MYMOVIES_LOCAL_DEFAULTS = [
	('mymv_local_finish', 'Local: Finish Watching', 'local_finish_watching_movies', 'icon.png', 'icon.png', 1, 1, 1, 0, 0, 'local_scrobble', 1, None),
]

_MYTVSHOWS_DEFAULTS = [
	('mytv_userlists',         '32040', 'tvUserlists',                                          'userlists.png', 'userlists.png', 1, 1, 1,  0, 0, None,                    0, None),
	('mytv_fav_tvshows',       '40466', 'getFavouritesTVShows&url=favourites_tvshows',          'tvshows.png',   'tvshows.png',   1, 1, 1,  1, 0, 'favorite_tvshows',      0, None),
	('mytv_fav_episodes',      '40467', 'getFavouritesEpisodes',                                'tvshows.png',   'tvshows.png',   1, 1, 1,  2, 0, 'favorite_episodes',     0, None),
	('mytv_mdblist_folder',    'MDBList',  'mytvshows_mdblistNavigator',                        'mdblist.png',   'mdblist.png',   1, 1, 1,  3, 0, 'mdblist_token',         0, None),
	('mytv_custom_folder',     'Custom',   'mytvshows_customNavigator',                         'icon.png',      'icon.png',      1, 1, 1,  4, 0, 'custom_token',          0, None),
	('mytv_local_folder',      'Local',    'mytvshows_localNavigator',                          'icon.png',      'icon.png',      1, 1, 1,  5, 0, 'local_scrobble',        0, None),
	('mytv_tmdb_folder',       'TMDb',     'mytvshows_tmdbNavigator',                           'tmdb.png',      'tmdb.png',      1, 1, 1,  8, 0, 'tmdb_v4_token',         0, None),
	('mytv_simkl_folder',      'Simkl',    'mytvshows_simklNavigator',                          'simkl.png',     'simkl.png',     1, 1, 1,  9, 0, 'simkl_credentials',     0, None),
	('mytv_trakt_folder',      'Trakt',    'mytvshows_traktNavigator',                          'trakt.png',     'trakt.png',     1, 1, 1, 10, 0, 'trakt_credentials',     0, None),
	('mytv_floppy_folder',   'Floppy', 'mytvshows_floppyNavigator',                       'floppy.png',  'floppy.png',  1, 1, 1, 11, 0, 'floppy_credentials',  0, None),
	('mytv_tv_menu',           '32031', 'tvliteNavigator',                                     'tvshows.png',   'tvshows.png',   1, 1, 1, 12, 0, 'not_lite',              0, None),
	('mytv_person_search',     '33045', 'tvPerson',                                            'imdb.png',      'people-search.png', 0, 1, 1, 13, 0, 'not_lite',          0, None),
	('mytv_tv_search',         '33043', 'tvSearch',                                            'trakt.png',     'search.png',    1, 1, 1, 14, 0, 'not_lite',              0, None),
	('mytv_scrob_folder',      'Scrob',    'mytvshows_scrobNavigator',                         'scrob.png',     'scrob.png',     1, 1, 1, 15, 0, 'scrob_credentials',     0, None),
]

_MYTVSHOWS_MDBLIST_DEFAULTS = [
	('mytv_mdb_userlist',      '40681', 'mdbUserListTV',                                        'mdblist.png',   'mdblist.png',   1, 1, 1,  0, 0, 'mdblist_token',         0, '40699'),
	('mytv_mdb_watchlist',     '40682', 'mdbUserWatchListTVShows',                              'mdblist.png',   'mdblist.png',   1, 1, 1,  1, 0, 'mdblist_token',         0, '40700'),
	('mytv_mdb_collection',    '40706', 'mdbUserCollectionTVShows',                             'mdblist.png',   'mdblist.png',   1, 1, 1,  2, 0, 'mdblist_token',         0, None),
	('mytv_mdb_liked',         '40683', 'mdbLikedListShows',                                    'mdblist.png',   'mdblist.png',   1, 1, 1,  3, 0, 'mdblist_token',         0, '40701'),
	('mytv_mdb_shows_prog',    '40684', 'mdblist_shows_progress&url=mdbprogress',               'mdblist.png',   'mdblist.png',   1, 1, 1,  4, 0, 'mdblist_with_indicators',1, '40401'),
	('mytv_mdb_ep_prog',       '40685', 'mdblist_calendar&url=mdbprogress',                     'mdblist.png',   'mdblist.png',   1, 1, 1,  5, 0, 'mdblist_with_indicators',1, '32037'),
	('mytv_mdb_unfinished',    '40686', 'mdblistEpisodesUnfinished',                            'mdblist.png',   'mdblist.png',   1, 1, 1,  6, 0, 'mdblist_with_indicators',1, '35308'),
	('mytv_mdb_watched',       '40715', 'mdblist_shows_watched&url=mdblistwatchedtv',           'mdblist.png',   'mdblist.png',   1, 1, 1,  7, 0, 'mdblist_with_indicators',1, '40433'),
	('mytv_mdb_events_recent', '40778', 'mdblist_events_recent&url=mdblisteventsrecent',        'mdblist.png',   'mdblist.png',   1, 1, 1,  8, 0, 'mdblist_with_indicators',1, '32202'),
	('mytv_mdb_events_upcoming','40779','mdblist_events_upcoming&url=mdblisteventsupcoming',    'mdblist.png',   'mdblist.png',   1, 1, 1,  9, 0, 'mdblist_with_indicators',1, '32203'),
	('mytv_mdb_events_premiers','40780','mdblist_events_premieres&url=mdblisteventspremieres',  'mdblist.png',   'mdblist.png',   1, 1, 1, 10, 0, 'mdblist_with_indicators',1, '32204'),
]

_MYTVSHOWS_CUSTOM_DEFAULTS = [
	('mytv_custom_watchlist',  '40736', 'custom_shows_watchlist&url=customshowswatchlist',       'icon.png',      'icon.png',      1, 1, 1,  0, 0, 'custom_token',           0, None),
	('mytv_custom_collection', '40737', 'custom_shows_collection&url=customshowscollection',     'icon.png',      'icon.png',      1, 1, 1,  1, 0, 'custom_token',           0, None),
	('mytv_custom_watched',    '40738', 'custom_shows_watched&url=customshowswatched',           'icon.png',      'icon.png',      1, 1, 1,  2, 0, 'custom_with_indicators', 1, '40433'),
	('mytv_custom_show_prog',  '40739', 'custom_shows_progress&url=customshowsprogress',         'icon.png',      'icon.png',      1, 1, 1,  3, 0, 'custom_with_indicators', 1, '40401'),
	('mytv_custom_ep_prog',    '40740', 'custom_episodes_progress&url=customepisodesprogress',   'icon.png',      'icon.png',      1, 1, 1,  4, 0, 'custom_with_indicators', 1, '32037'),
	('mytv_custom_unfinished', '40741', 'customEpisodesUnfinished&url=customepisodesunfinished', 'icon.png',      'icon.png',      1, 1, 1,  5, 0, 'custom_with_indicators', 1, '35308'),
	('mytv_custom_cal_recent', '40742', 'custom_calendar_recent&url=customcalendarrecent',       'icon.png',      'icon.png',      1, 1, 1,  6, 0, 'custom_with_indicators', 1, '32202'),
	('mytv_custom_cal_upcoming','40743','custom_calendar_upcoming&url=customcalendarupcoming',   'icon.png',      'icon.png',      1, 1, 1,  7, 0, 'custom_with_indicators', 1, '32203'),
	('mytv_custom_cal_premiers','40744','custom_calendar_premieres&url=customcalendarpremieres', 'icon.png',      'icon.png',      1, 1, 1,  8, 0, 'custom_with_indicators', 1, '32204'),
	('mytv_custom_upcoming',   '40753', 'custom_upcoming_progress&url=customupcomingprogress',   'icon.png',      'icon.png',      1, 1, 1,  9, 0, 'custom_with_indicators', 1, '32019'),
	('mytv_custom_userlists',  '40782', 'custom_shows_userlists',                                'icon.png',      'icon.png',      1, 1, 1, 10, 0, 'custom_token',           1, None),
	# sort_order 99 — see mymv_custom_dropped's comment above for why this can't safely
	# reuse position 11.
	('mytv_custom_dropped',    '40783', 'custom_shows_dropped&url=customshowsdropped',           'icon.png',      'icon.png',      1, 1, 1, 99, 0, 'custom_token',           0, None),
]

_MYTVSHOWS_TMDB_DEFAULTS = [
	('mytv_tmdb_userlists',    'TMDb User Lists', 'tmdbUserListsTV',                            'tmdb.png',      'tmdb.png',      1, 1, 1,  0, 0, 'tmdb_v4_token',         0, None),
	('mytv_tmdb_watchlist',    '40612', 'tmdbV4WatchlistTV',                                    'tmdb.png',      'tmdb.png',      1, 1, 1,  1, 0, 'tmdb_v4_token',         0, None),
]

_MYTVSHOWS_SIMKL_DEFAULTS = [
	('mytv_simkl_ep_prog',     'Progress Episodes (Simkl)', 'simkl_calendar&url=/sync/all-items/shows/watching', 'simkl.png', 'simkl.png', 1, 1, 1, 0, 0, 'simkl_credentials', 1, None),
	('mytv_simkl_show_prog',   'Progress Shows (Simkl)', 'simkl_shows_progress&url=simklshowsprogress', 'simkl.png', 'simkl.png', 1, 1, 1,  1, 0, 'simkl_credentials',     1, None),
	('mytv_simkl_watching',    'Watching (Simkl)', 'tvshows&url=simklwatching',                  'simkl.png',     'simkl.png',     1, 1, 1,  2, 0, 'simkl_credentials',     1, None),
	('mytv_simkl_watchlist',   'Plan to Watch (Simkl)', 'tvshows&url=simklwatchlist',             'simkl.png',     'simkl.png',     1, 1, 1,  3, 0, 'simkl_credentials',     0, None),
	('mytv_simkl_onhold',      'On Hold (Simkl)', 'tvshows&url=simklonhold',                     'simkl.png',     'simkl.png',     1, 1, 1,  4, 0, 'simkl_credentials',     0, None),
	('mytv_simkl_completed',   'Completed (Simkl)', 'tvshows&url=simklhistory',                  'simkl.png',     'simkl.png',     1, 1, 1,  5, 0, 'simkl_credentials',     0, None),
	('mytv_simkl_dropped',     'Dropped (Simkl)', 'tvshows&url=simkldropped',                   'simkl.png',     'simkl.png',     1, 1, 1,  6, 0, 'simkl_credentials',     0, None),
]

_MYTVSHOWS_TRAKT_DEFAULTS = [
	('mytv_trakt_unfinished',  '40687', 'episodesUnfinished&url=traktunfinished',               'trakt.png',     'trakt.png',     1, 1, 1,  0, 0, 'trakt_with_indicators',  1, '35308'),
	('mytv_trakt_ep_prog',     '40688', 'calendar&url=progress',                                'trakt.png',     'trakt.png',     1, 1, 1,  1, 0, 'trakt_with_indicators',  1, '32037'),
	('mytv_trakt_show_prog',   '40689', 'shows_progress&url=progresstv',                       'trakt.png',     'trakt.png',     1, 1, 1,  2, 0, 'trakt_with_indicators',  1, '40401'),
	('mytv_trakt_watched',     '40690', 'shows_watched&url=watchedtv',                         'trakt.png',     'trakt.png',     1, 1, 1,  3, 0, 'trakt_with_indicators',  1, '40433'),
	('mytv_trakt_upcoming',    '40691', 'upcomingProgress&url=progress',                       'trakt.png',     'trakt.png',     1, 1, 1,  4, 0, 'trakt_with_indicators',  1, '32019'),
	('mytv_trakt_cal_recent',  '40692', 'calendar&url=mycalendarRecent',                       'trakt.png',     'trakt.png',     1, 1, 1,  5, 0, 'trakt_with_indicators',  1, '32202'),
	('mytv_trakt_cal_upcoming','40693', 'calendar&url=mycalendarUpcoming',                     'trakt.png',     'trakt.png',     1, 1, 1,  6, 0, 'trakt_with_indicators',  1, '32203'),
	('mytv_trakt_cal_premiers','40694', 'calendar&url=mycalendarPremiers',                     'trakt.png',     'trakt.png',     1, 1, 1,  7, 0, 'trakt_with_indicators',  1, '32204'),
	('mytv_trakt_history',     '40695', 'calendar&url=trakthistory',                           'trakt.png',     'trakt.png',     1, 1, 1,  8, 0, 'trakt_with_indicators',  1, '32036'),
	('mytv_trakt_watchlist',   '40696', 'tvshows&url=traktwatchlist',                          'trakt.png',     'trakt.png',     1, 1, 1,  9, 0, 'trakt_credentials',     0, '40700'),
	('mytv_trakt_collection',  '40697', 'tvshows&url=traktcollection',                         'trakt.png',     'trakt.png',     1, 1, 1, 10, 0, 'trakt_credentials',     0, '32032'),
	('mytv_trakt_liked',       '40698', 'shows_LikedLists',                                    'trakt.png',     'trakt.png',     1, 1, 1, 11, 0, 'trakt_credentials',      1, 'My Liked Lists'),
]

_MYTVSHOWS_FLOPPY_DEFAULTS = [
	('mytv_floppy_watching',   'Watching (Floppy)',   'floppy_shows_watching&url=floppyshowswatching',     'floppy.png', 'floppy.png', 1, 1, 1,  0, 0, 'floppy_credentials', 0, None),
	('mytv_floppy_watchlist',  'Watchlist (Floppy)',  'floppy_shows_watchlist&url=floppyshowswatchlist',   'floppy.png', 'floppy.png', 1, 1, 1,  1, 0, 'floppy_credentials', 0, None),
	('mytv_floppy_onhold',     'On Hold (Floppy)',    'floppy_shows_onhold&url=floppyshowsonhold',         'floppy.png', 'floppy.png', 1, 1, 1,  2, 0, 'floppy_credentials', 0, None),
	('mytv_floppy_completed',  'Completed (Floppy)',  'floppy_shows_completed&url=floppyshowscompleted',   'floppy.png', 'floppy.png', 1, 1, 1,  3, 0, 'floppy_credentials', 0, None),
	('mytv_floppy_dropped',    'Dropped (Floppy)',    'floppy_shows_dropped&url=floppyshowsdropped',       'floppy.png', 'floppy.png', 1, 1, 1,  4, 0, 'floppy_credentials', 0, None),
	('mytv_floppy_collection', 'Collection (Floppy)', 'floppy_shows_collection&url=floppyshowscollection', 'floppy.png', 'floppy.png', 1, 1, 1,  5, 0, 'floppy_credentials', 0, None),
	('mytv_floppy_show_prog',  'Progress Shows (Floppy)', 'floppy_shows_progress&url=floppyshowsprogress',   'floppy.png', 'floppy.png', 1, 1, 1,  6, 0, 'floppy_with_indicators', 1, None),
	('mytv_floppy_ep_prog',    'Progress Episodes (Floppy)', 'floppy_episodes_progress&url=floppyepisodesprogress', 'floppy.png', 'floppy.png', 1, 1, 1,  7, 0, 'floppy_with_indicators', 1, None),
	('mytv_floppy_upcoming',   'Upcoming Progress (Floppy)', 'floppy_upcoming_progress&url=floppyupcomingprogress', 'floppy.png', 'floppy.png', 1, 1, 1,  8, 0, 'floppy_with_indicators', 1, None),
	('mytv_floppy_unfinished', 'Unfinished (Floppy)', 'floppy_episodes_unfinished&url=floppyepisodesunfinished', 'floppy.png', 'floppy.png', 1, 1, 1,  9, 0, 'floppy_credentials', 1, '35308'),
	('mytv_floppy_userlists',  'User Lists (Floppy)', 'floppy_shows_userlists', 'floppy.png', 'floppy.png', 1, 1, 1, 10, 0, 'floppy_credentials', 0, None),
]

_MYTVSHOWS_SCROB_DEFAULTS = [
	('mytv_scrob_show_prog',  'Progress Shows (Scrob)', 'scrob_shows_progress&url=scrobshowsprogress',     'scrob.png', 'scrob.png', 1, 1, 1,  0, 0, 'scrob_with_indicators', 1, None),
	('mytv_scrob_ep_prog',    'Progress Episodes (Scrob)', 'scrob_episodes_progress&url=scrobepisodesprogress', 'scrob.png', 'scrob.png', 1, 1, 1,  1, 0, 'scrob_with_indicators', 1, None),
	('mytv_scrob_upcoming',   'Upcoming Progress (Scrob)', 'scrob_upcoming_progress&url=scrobupcomingprogress', 'scrob.png', 'scrob.png', 1, 1, 1,  2, 0, 'scrob_with_indicators', 1, None),
	('mytv_scrob_unfinished', 'Unfinished (Scrob)', 'scrob_episodes_unfinished&url=scrobepisodesunfinished', 'scrob.png', 'scrob.png', 1, 1, 1,  3, 0, 'scrob_credentials', 1, '35308'),
	('mytv_scrob_userlists', '40781', 'scrob_tvshows_userlists', 'scrob.png', 'scrob.png', 1, 1, 1,  4, 0, 'scrob_credentials', 1, None),
]

_MYTVSHOWS_LOCAL_DEFAULTS = [
	('mytv_local_shows_prog', '40658', 'local_shows_progress&url=localprogress', 'icon.png', 'icon.png', 1, 1, 1, 0, 0, 'local_scrobble', 1, None),
	('mytv_local_calendar',   '40659', 'local_calendar&url=localprogress',       'icon.png', 'icon.png', 1, 1, 1, 1, 0, 'local_scrobble', 1, None),
	('mytv_local_finish',     'Local: Finish Watching', 'local_finish_watching_episodes', 'icon.png', 'icon.png', 1, 1, 1, 2, 0, 'local_scrobble', 1, None),
]

MENU_DEFAULTS = {
	'root':      _ROOT_DEFAULTS,
	'movies':    _MOVIES_DEFAULTS,
	'tvshows':   _TVSHOWS_DEFAULTS,
	'mymovies':  _MYMOVIES_DEFAULTS,
	'mytvshows': _MYTVSHOWS_DEFAULTS,
	'mymovies_mdblist':  _MYMOVIES_MDBLIST_DEFAULTS,
	'mymovies_custom':   _MYMOVIES_CUSTOM_DEFAULTS,
	'mymovies_tmdb':     _MYMOVIES_TMDB_DEFAULTS,
	'mymovies_simkl':    _MYMOVIES_SIMKL_DEFAULTS,
	'mymovies_trakt':    _MYMOVIES_TRAKT_DEFAULTS,
	'mymovies_floppy': _MYMOVIES_FLOPPY_DEFAULTS,
	'mymovies_scrob': _MYMOVIES_SCROB_DEFAULTS,
	'mymovies_local': _MYMOVIES_LOCAL_DEFAULTS,
	'mytvshows_mdblist':  _MYTVSHOWS_MDBLIST_DEFAULTS,
	'mytvshows_custom':   _MYTVSHOWS_CUSTOM_DEFAULTS,
	'mytvshows_tmdb':     _MYTVSHOWS_TMDB_DEFAULTS,
	'mytvshows_simkl':    _MYTVSHOWS_SIMKL_DEFAULTS,
	'mytvshows_trakt':    _MYTVSHOWS_TRAKT_DEFAULTS,
	'mytvshows_floppy': _MYTVSHOWS_FLOPPY_DEFAULTS,
	'mytvshows_scrob': _MYTVSHOWS_SCROB_DEFAULTS,
	'mytvshows_local': _MYTVSHOWS_LOCAL_DEFAULTS,
}

# item_id -> alt_label for migrating existing DB rows
_ALT_LABEL_MAP = {
	row[0]: row[12]
	for defaults in MENU_DEFAULTS.values()
	for row in defaults
	if row[12] is not None
}


_session_defaults_synced = False
_defaults_version_file = control.joinPath(control.dataPath, 'menu_defaults.v')
# Bump this whenever _sync_defaults()/_NEW_DEFAULT_ITEMS needs to re-run for everyone
# regardless of addon version (e.g. to fix a migration bug) — the on-disk marker below
# is keyed on addonVersion+this, not addonVersion alone, so incrementing it forces one
# more sync pass even for users already marked up to date on the current addon version.
_MENU_SCHEMA_REVISION = '13'


def _read_synced_version():
	try:
		with open(_defaults_version_file, 'r') as f:
			return f.read().strip()
	except Exception:
		return None


def _write_synced_version(version):
	try:
		if not control.existsPath(control.dataPath):
			control.makeFile(control.dataPath)
		with open(_defaults_version_file, 'w') as f:
			f.write(version)
	except Exception:
		pass


def _get_connection():
	if not control.existsPath(control.dataPath):
		control.makeFile(control.dataPath)
	dbcon = db.connect(menuFile, timeout=60)
	try:
		dbcon.execute('PRAGMA journal_mode = WAL')
		dbcon.execute('PRAGMA synchronous = NORMAL')
	except db.OperationalError:
		dbcon.execute('PRAGMA journal_mode = OFF')
		dbcon.execute('PRAGMA synchronous = OFF')
	dbcon.execute('PRAGMA temp_store = memory')
	dbcon.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
	return dbcon


def _populate_defaults(dbcon, menu_name):
	defaults = MENU_DEFAULTS.get(menu_name, [])
	dbcon.executemany(
		'INSERT OR IGNORE INTO menu_items '
		'(menu_name, item_id, label, action, icon, poster, is_folder, is_action, enabled, sort_order, is_custom, condition_key, queue, alt_label) '
		'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
		[(menu_name,) + row for row in defaults]
	)
	dbcon.commit()


def _migrate_schema(dbcon):
	# Add columns introduced after the original schema to pre-existing databases.
	for col_def in [
		('condition_key', 'TEXT'),
		('queue',         'INTEGER NOT NULL DEFAULT 0'),
		('alt_label',     'TEXT'),
	]:
		try:
			dbcon.execute('ALTER TABLE menu_items ADD COLUMN %s %s' % col_def)
		except db.OperationalError:
			pass
	dbcon.commit()


def _sync_defaults(dbcon):
	# Full defaults resync.
	_field_sync = {
		row[0]: (row[1], row[3], row[4], row[12])
		for defaults in MENU_DEFAULTS.values()
		for row in defaults
	}
	for item_id, (label, icon, poster, alt_label) in _field_sync.items():
		dbcon.execute(
			'UPDATE menu_items SET label=?, icon=?, poster=?, alt_label=? WHERE item_id=? AND is_custom=0',
			(label, icon, poster, alt_label, item_id)
		)
	dbcon.commit()
	# Move existing users' account-exclusive provider rows out of the flat
	# mymovies/mytvshows buckets into the new per-provider submenu buckets.
	# item_id is preserved, only menu_name changes, so enabled/sort_order/
	# condition_key (i.e. all user customization) survives untouched.
	_REGROUPED_ITEM_MOVES = {
		'mymv_mdb_userlist':      ('mymovies', 'mymovies_mdblist'),
		'mymv_mdb_watchlist':     ('mymovies', 'mymovies_mdblist'),
		'mymv_mdb_collection':    ('mymovies', 'mymovies_mdblist'),
		'mymv_mdb_liked':         ('mymovies', 'mymovies_mdblist'),
		'mymv_mdb_unfinished':    ('mymovies', 'mymovies_mdblist'),
		'mymv_mdb_watched':       ('mymovies', 'mymovies_mdblist'),
		'mymv_custom_watchlist':  ('mymovies', 'mymovies_custom'),
		'mymv_custom_collection': ('mymovies', 'mymovies_custom'),
		'mymv_custom_unfinished': ('mymovies', 'mymovies_custom'),
		'mymv_custom_watched':    ('mymovies', 'mymovies_custom'),
		'mymv_tmdb_userlists':    ('mymovies', 'mymovies_tmdb'),
		'mymv_tmdb_watchlist':    ('mymovies', 'mymovies_tmdb'),
		'mymv_simkl_completed':   ('mymovies', 'mymovies_simkl'),
		'mymv_simkl_watchlist':   ('mymovies', 'mymovies_simkl'),
		'mymv_simkl_dropped':     ('mymovies', 'mymovies_simkl'),
		'mymv_trakt_unfinished':  ('mymovies', 'mymovies_trakt'),
		'mymv_trakt_history':     ('mymovies', 'mymovies_trakt'),
		'mymv_trakt_watchlist':   ('mymovies', 'mymovies_trakt'),
		'mymv_trakt_collection':  ('mymovies', 'mymovies_trakt'),
		'mymv_trakt_liked':       ('mymovies', 'mymovies_trakt'),
		'mymv_local_finish':      ('mymovies', 'mymovies_local'),
		'mytv_mdb_userlist':      ('mytvshows', 'mytvshows_mdblist'),
		'mytv_mdb_watchlist':     ('mytvshows', 'mytvshows_mdblist'),
		'mytv_mdb_collection':    ('mytvshows', 'mytvshows_mdblist'),
		'mytv_mdb_liked':         ('mytvshows', 'mytvshows_mdblist'),
		'mytv_mdb_shows_prog':    ('mytvshows', 'mytvshows_mdblist'),
		'mytv_mdb_ep_prog':       ('mytvshows', 'mytvshows_mdblist'),
		'mytv_mdb_unfinished':    ('mytvshows', 'mytvshows_mdblist'),
		'mytv_mdb_watched':       ('mytvshows', 'mytvshows_mdblist'),
		'mytv_mdb_events_recent': ('mytvshows', 'mytvshows_mdblist'),
		'mytv_mdb_events_upcoming': ('mytvshows', 'mytvshows_mdblist'),
		'mytv_mdb_events_premiers': ('mytvshows', 'mytvshows_mdblist'),
		'mytv_custom_watchlist':   ('mytvshows', 'mytvshows_custom'),
		'mytv_custom_collection':  ('mytvshows', 'mytvshows_custom'),
		'mytv_custom_watched':     ('mytvshows', 'mytvshows_custom'),
		'mytv_custom_show_prog':   ('mytvshows', 'mytvshows_custom'),
		'mytv_custom_ep_prog':     ('mytvshows', 'mytvshows_custom'),
		'mytv_custom_unfinished':  ('mytvshows', 'mytvshows_custom'),
		'mytv_custom_cal_recent':  ('mytvshows', 'mytvshows_custom'),
		'mytv_custom_cal_upcoming':('mytvshows', 'mytvshows_custom'),
		'mytv_custom_cal_premiers':('mytvshows', 'mytvshows_custom'),
		'mytv_custom_upcoming':    ('mytvshows', 'mytvshows_custom'),
		'mytv_tmdb_userlists':    ('mytvshows', 'mytvshows_tmdb'),
		'mytv_tmdb_watchlist':    ('mytvshows', 'mytvshows_tmdb'),
		'mytv_simkl_ep_prog':     ('mytvshows', 'mytvshows_simkl'),
		'mytv_simkl_watching':    ('mytvshows', 'mytvshows_simkl'),
		'mytv_simkl_watchlist':   ('mytvshows', 'mytvshows_simkl'),
		'mytv_simkl_onhold':      ('mytvshows', 'mytvshows_simkl'),
		'mytv_simkl_completed':   ('mytvshows', 'mytvshows_simkl'),
		'mytv_simkl_dropped':     ('mytvshows', 'mytvshows_simkl'),
		'mytv_trakt_unfinished':  ('mytvshows', 'mytvshows_trakt'),
		'mytv_trakt_ep_prog':     ('mytvshows', 'mytvshows_trakt'),
		'mytv_trakt_show_prog':   ('mytvshows', 'mytvshows_trakt'),
		'mytv_trakt_watched':     ('mytvshows', 'mytvshows_trakt'),
		'mytv_trakt_upcoming':    ('mytvshows', 'mytvshows_trakt'),
		'mytv_trakt_cal_recent':  ('mytvshows', 'mytvshows_trakt'),
		'mytv_trakt_cal_upcoming':('mytvshows', 'mytvshows_trakt'),
		'mytv_trakt_cal_premiers':('mytvshows', 'mytvshows_trakt'),
		'mytv_trakt_history':     ('mytvshows', 'mytvshows_trakt'),
		'mytv_trakt_watchlist':   ('mytvshows', 'mytvshows_trakt'),
		'mytv_trakt_collection':  ('mytvshows', 'mytvshows_trakt'),
		'mytv_trakt_liked':       ('mytvshows', 'mytvshows_trakt'),
		'mytv_local_shows_prog':  ('mytvshows', 'mytvshows_local'),
		'mytv_local_calendar':    ('mytvshows', 'mytvshows_local'),
		'mytv_local_finish':      ('mytvshows', 'mytvshows_local'),
	}
	for item_id, (old_menu, new_menu) in _REGROUPED_ITEM_MOVES.items():
		# UPDATE OR IGNORE: if the target bucket was already auto-populated with its
		# default row for this item_id (e.g. the user opened the new per-provider
		# submenu, which self-populates via initialize(), before this migration ran),
		# a plain UPDATE would violate the UNIQUE(menu_name, item_id) constraint.
		dbcon.execute(
			'UPDATE OR IGNORE menu_items SET menu_name=? WHERE menu_name=? AND item_id=? AND is_custom=0',
			(new_menu, old_menu, item_id)
		)
		# If the row above didn't move (target already had it), drop the now-redundant
		# old-bucket copy so it doesn't linger as an orphaned duplicate.
		dbcon.execute(
			'DELETE FROM menu_items WHERE menu_name=? AND item_id=? AND is_custom=0',
			(old_menu, item_id)
		)
	dbcon.commit()
	# The Yamtrack fork this integration targets was renamed to "Floppy" by its
	# developer, so every yamtrack_* item_id/menu_name/condition_key was renamed to
	# floppy_* to match. Old rows under the pre-rename names are dead weight (nothing
	# renders menu_name='mymovies_yamtrack'/'mytvshows_yamtrack' anymore, and
	# condition_key='yamtrack_credentials' is no longer recognized) — drop them so
	# the fresh floppy_* defaults populate cleanly instead of leaving orphans behind.
	dbcon.execute("DELETE FROM menu_items WHERE menu_name IN ('mymovies_yamtrack', 'mytvshows_yamtrack') AND is_custom=0")
	dbcon.execute("DELETE FROM menu_items WHERE item_id IN ('mymv_yamtrack_folder', 'mytv_yamtrack_folder') AND is_custom=0")
	dbcon.commit()
	# mytv_mdb_cal_upcoming (TMDb next_episode_to_air per watchlisted show) is superseded
	# by mytv_mdb_events_upcoming (MDBList's own personalized /calendar/events) — both
	# rendered under the identical label "Upcoming Episodes (MDBList)", which read as one
	# broken duplicated entry rather than two different features. Drop the old one.
	dbcon.execute("DELETE FROM menu_items WHERE item_id='mytv_mdb_cal_upcoming' AND is_custom=0")
	dbcon.commit()
	# mymv_simkl_unfinished (My Movies > Simkl > Unfinished) is the same list as
	# mymv_simkl_watchlist (Plan to Watch) — Simkl has no separate "in-progress"
	# concept for movies the way it does for shows, so this was a pure duplicate. Drop it.
	dbcon.execute("DELETE FROM menu_items WHERE item_id='mymv_simkl_unfinished' AND is_custom=0")
	dbcon.commit()
	# mymv_floppy_completed previously routed through the generic status-bucket
	# floppyList() (same 'movies.watchlist' sort as Watchlist/On Hold/Dropped, and only
	# each item's first-tracked date rather than a real watched date) — point it at the
	# new dedicated floppyWatched() handler instead, which sorts by actual watch history
	# like every other provider's Watched list.
	dbcon.execute("UPDATE menu_items SET action=? WHERE item_id='mymv_floppy_completed' AND is_custom=0", ('floppy_movies_watched&url=floppymovieswatched',))
	dbcon.commit()
	# Insert items added after initial release for existing users
	_NEW_DEFAULT_ITEMS = [
		('mymovies', 'mymv_mdblist_folder',  'MDBList',  'mymovies_mdblistNavigator',  'mdblist.png',  'mdblist.png',  1, 1, 1, 2, 0, 'mdblist_token',        0, None),
		('mymovies', 'mymv_custom_folder',   'Custom',   'mymovies_customNavigator',   'icon.png',     'icon.png',     1, 1, 1, 3, 0, 'custom_token',         0, None),
		('mymovies', 'mymv_tmdb_folder',     'TMDb',     'mymovies_tmdbNavigator',     'tmdb.png',     'tmdb.png',     1, 1, 1, 4, 0, 'tmdb_v4_token',        0, None),
		('mymovies', 'mymv_simkl_folder',    'Simkl',    'mymovies_simklNavigator',    'simkl.png',    'simkl.png',    1, 1, 1, 5, 0, 'simkl_token',          0, None),
		('mymovies', 'mymv_trakt_folder',    'Trakt',    'mymovies_traktNavigator',    'trakt.png',    'trakt.png',    1, 1, 1, 6, 0, 'trakt_credentials',    0, None),
		('mymovies', 'mymv_floppy_folder', 'Floppy', 'mymovies_floppyNavigator', 'floppy.png', 'floppy.png', 1, 1, 1, 7, 0, 'floppy_credentials', 0, None),
		('mytvshows', 'mytv_mdblist_folder',  'MDBList',  'mytvshows_mdblistNavigator',  'mdblist.png',  'mdblist.png',  1, 1, 1, 3,  0, 'mdblist_token',        0, None),
		('mytvshows', 'mytv_custom_folder',   'Custom',   'mytvshows_customNavigator',   'icon.png',     'icon.png',     1, 1, 1, 4,  0, 'custom_token',         0, None),
		('mytvshows', 'mytv_tmdb_folder',     'TMDb',     'mytvshows_tmdbNavigator',     'tmdb.png',     'tmdb.png',     1, 1, 1, 8,  0, 'tmdb_v4_token',        0, None),
		('mytvshows', 'mytv_simkl_folder',    'Simkl',    'mytvshows_simklNavigator',    'simkl.png',    'simkl.png',    1, 1, 1, 9,  0, 'simkl_credentials',    0, None),
		('mytvshows', 'mytv_trakt_folder',    'Trakt',    'mytvshows_traktNavigator',    'trakt.png',    'trakt.png',    1, 1, 1, 10, 0, 'trakt_credentials',    0, None),
		('mytvshows', 'mytv_floppy_folder', 'Floppy', 'mytvshows_floppyNavigator', 'floppy.png', 'floppy.png', 1, 1, 1, 11, 0, 'floppy_credentials', 0, None),
		('mymovies', 'mymv_scrob_folder', 'Scrob', 'mymovies_scrobNavigator', 'scrob.png', 'scrob.png', 1, 1, 1, 12, 0, 'scrob_credentials', 0, None),
		('mytvshows', 'mytv_scrob_folder', 'Scrob', 'mytvshows_scrobNavigator', 'scrob.png', 'scrob.png', 1, 1, 1, 15, 0, 'scrob_credentials', 0, None),
		('mymovies_scrob', 'mymv_scrob_unfinished', 'Unfinished (Scrob)', 'scrob_movies_unfinished&url=scrobmoviesunfinished', 'scrob.png', 'scrob.png', 1, 1, 1, 99, 0, 'scrob_credentials', 1, '35308'),
		('mytvshows_scrob', 'mytv_scrob_unfinished', 'Unfinished (Scrob)', 'scrob_episodes_unfinished&url=scrobepisodesunfinished', 'scrob.png', 'scrob.png', 1, 1, 1, 99, 0, 'scrob_credentials', 1, '35308'),
		('mymovies_scrob', 'mymv_scrob_userlists', '40781', 'scrob_movies_userlists', 'scrob.png', 'scrob.png', 1, 1, 1, 100, 0, 'scrob_credentials', 1, None),
		('mytvshows_scrob', 'mytv_scrob_userlists', '40781', 'scrob_tvshows_userlists', 'scrob.png', 'scrob.png', 1, 1, 1, 100, 0, 'scrob_credentials', 1, None),
		('mymovies_floppy', 'mymv_floppy_unfinished', 'Unfinished (Floppy)', 'floppy_movies_unfinished&url=floppymoviesunfinished', 'floppy.png', 'floppy.png', 1, 1, 1, 99, 0, 'floppy_credentials', 1, '35308'),
		('mytvshows_floppy', 'mytv_floppy_unfinished', 'Unfinished (Floppy)', 'floppy_episodes_unfinished&url=floppyepisodesunfinished', 'floppy.png', 'floppy.png', 1, 1, 1, 99, 0, 'floppy_credentials', 1, '35308'),
		('mymovies_floppy', 'mymv_floppy_userlists', 'User Lists (Floppy)', 'floppy_movies_userlists', 'floppy.png', 'floppy.png', 1, 1, 1, 100, 0, 'floppy_credentials', 0, None),
		('mytvshows_floppy', 'mytv_floppy_userlists', 'User Lists (Floppy)', 'floppy_shows_userlists', 'floppy.png', 'floppy.png', 1, 1, 1, 101, 0, 'floppy_credentials', 0, None),
		('mymovies_mdblist',  'mymv_mdb_unfinished',  '40686',  'mdblistMoviesUnfinished',          'mdblist.png', 'mdblist.png', 1, 1, 1, 99, 0, 'mdblist_with_indicators', 1, '35308'),
		('mytvshows_mdblist', 'mytv_mdb_unfinished',  '40686',  'mdblistEpisodesUnfinished',         'mdblist.png', 'mdblist.png', 1, 1, 1, 99, 0, 'mdblist_with_indicators', 1, '35308'),
		('mymovies',  'mymv_local_folder',    'Local', 'mymovies_localNavigator',  'icon.png',    'icon.png',    1, 1, 1, 99, 0, 'local_scrobble',          0, None),
		('mytvshows', 'mytv_local_folder',    'Local', 'mytvshows_localNavigator', 'icon.png',    'icon.png',    1, 1, 1, 99, 0, 'local_scrobble',          0, None),
		('mymovies_mdblist',  'mymv_mdb_collection',  '40706',  'mdbUserCollectionMovies',           'mdblist.png', 'mdblist.png', 1, 1, 1, 100, 0, 'mdblist_token',           0, None),
		('mytvshows_mdblist', 'mytv_mdb_collection',  '40706',  'mdbUserCollectionTVShows',          'mdblist.png', 'mdblist.png', 1, 1, 1, 100, 0, 'mdblist_token',           0, None),
		('movies',    'mv_mdb_official',      '40711',  'mdbOfficialListMovies',             'mdblist.png', 'mdblist.png', 1, 1, 1, 99, 0, 'mdblist_token',           0, None),
		('tvshows',   'tv_mdb_official',      '40711',  'mdbOfficialListTV',                 'mdblist.png', 'mdblist.png', 1, 1, 1, 99, 0, 'mdblist_token',           0, None),
		('mytvshows_mdblist', 'mytv_mdb_watched',     '40715',  'mdblist_shows_watched&url=mdblistwatchedtv', 'mdblist.png', 'mdblist.png', 1, 1, 1, 101, 0, 'mdblist_with_indicators', 1, '40433'),
		('mymovies_mdblist',  'mymv_mdb_watched',     '40716',  'mdblist_movies_watched&url=mdblistwatchedmv', 'mdblist.png', 'mdblist.png', 1, 1, 1, 101, 0, 'mdblist_with_indicators', 1, None),
		('mytvshows_mdblist', 'mytv_mdb_events_recent', '40778', 'mdblist_events_recent&url=mdblisteventsrecent', 'mdblist.png', 'mdblist.png', 1, 1, 1, 102, 0, 'mdblist_with_indicators', 1, '32202'),
		('mytvshows_mdblist', 'mytv_mdb_events_upcoming', '40779', 'mdblist_events_upcoming&url=mdblisteventsupcoming', 'mdblist.png', 'mdblist.png', 1, 1, 1, 103, 0, 'mdblist_with_indicators', 1, '32203'),
		('mytvshows_mdblist', 'mytv_mdb_events_premiers', '40780', 'mdblist_events_premieres&url=mdblisteventspremieres', 'mdblist.png', 'mdblist.png', 1, 1, 1, 104, 0, 'mdblist_with_indicators', 1, '32204'),
		('mytvshows_custom', 'mytv_custom_watchlist',   '40736', 'custom_shows_watchlist&url=customshowswatchlist',       'icon.png', 'icon.png', 1, 1, 1, 99, 0, 'custom_token',           0, None),
		('mytvshows_custom', 'mytv_custom_collection',  '40737', 'custom_shows_collection&url=customshowscollection',     'icon.png', 'icon.png', 1, 1, 1, 100, 0, 'custom_token',           0, None),
		('mytvshows_custom', 'mytv_custom_watched',     '40738', 'custom_shows_watched&url=customshowswatched',           'icon.png', 'icon.png', 1, 1, 1, 101, 0, 'custom_with_indicators', 1, '40433'),
		('mytvshows_custom', 'mytv_custom_show_prog',   '40739', 'custom_shows_progress&url=customshowsprogress',         'icon.png', 'icon.png', 1, 1, 1, 102, 0, 'custom_with_indicators', 1, '40401'),
		('mytvshows_custom', 'mytv_custom_ep_prog',     '40740', 'custom_episodes_progress&url=customepisodesprogress',   'icon.png', 'icon.png', 1, 1, 1, 103, 0, 'custom_with_indicators', 1, '32037'),
		('mytvshows_custom', 'mytv_custom_unfinished',  '40741', 'customEpisodesUnfinished&url=customepisodesunfinished', 'icon.png', 'icon.png', 1, 1, 1, 104, 0, 'custom_with_indicators', 1, '35308'),
		('mytvshows_custom', 'mytv_custom_cal_recent',  '40742', 'custom_calendar_recent&url=customcalendarrecent',       'icon.png', 'icon.png', 1, 1, 1, 105, 0, 'custom_with_indicators', 1, '32202'),
		('mytvshows_custom', 'mytv_custom_cal_upcoming','40743', 'custom_calendar_upcoming&url=customcalendarupcoming',   'icon.png', 'icon.png', 1, 1, 1, 106, 0, 'custom_with_indicators', 1, '32203'),
		('mytvshows_custom', 'mytv_custom_cal_premiers','40744', 'custom_calendar_premieres&url=customcalendarpremieres','icon.png', 'icon.png', 1, 1, 1, 107, 0, 'custom_with_indicators', 1, '32204'),
		('mytvshows_custom', 'mytv_custom_upcoming',    '40753', 'custom_upcoming_progress&url=customupcomingprogress',   'icon.png', 'icon.png', 1, 1, 1, 108, 0, 'custom_with_indicators', 1, '32019'),
		('mymovies_custom',  'mymv_custom_watchlist',   '40736', 'custom_movies_watchlist&url=custommovieswatchlist',     'icon.png', 'icon.png', 1, 1, 1, 99, 0, 'custom_token',           0, None),
		('mymovies_custom',  'mymv_custom_collection',  '40737', 'custom_movies_collection&url=custommoviescollection',   'icon.png', 'icon.png', 1, 1, 1, 100, 0, 'custom_token',           0, None),
		('mymovies_custom',  'mymv_custom_unfinished',  '40741', 'custom_movies_unfinished&url=custommoviesunfinished',   'icon.png', 'icon.png', 1, 1, 1, 101, 0, 'custom_with_indicators', 1, '35308'),
		('mymovies_custom',  'mymv_custom_watched',     '40745', 'custom_movies_watched&url=custommovieswatched',         'icon.png', 'icon.png', 1, 1, 1, 102, 0, 'custom_with_indicators', 1, None),
	]
	for row in _NEW_DEFAULT_ITEMS:
		dbcon.execute(
			'INSERT OR IGNORE INTO menu_items '
			'(menu_name, item_id, label, action, icon, poster, is_folder, is_action, enabled, sort_order, is_custom, condition_key, queue, alt_label) '
			'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', row
		)
	dbcon.commit()


def initialize(menu_name='root'):
	global _session_defaults_synced
	dbcon = _get_connection()
	dbcon.execute('''CREATE TABLE IF NOT EXISTS menu_items (
		id            INTEGER PRIMARY KEY AUTOINCREMENT,
		menu_name     TEXT NOT NULL,
		item_id       TEXT NOT NULL,
		label         TEXT NOT NULL,
		action        TEXT NOT NULL,
		icon          TEXT NOT NULL,
		poster        TEXT NOT NULL,
		is_folder     INTEGER NOT NULL DEFAULT 1,
		is_action     INTEGER NOT NULL DEFAULT 1,
		enabled       INTEGER NOT NULL DEFAULT 1,
		sort_order    INTEGER NOT NULL,
		is_custom     INTEGER NOT NULL DEFAULT 0,
		condition_key TEXT,
		queue         INTEGER NOT NULL DEFAULT 0,
		alt_label     TEXT,
		UNIQUE(menu_name, item_id)
	)''')
	dbcon.execute('''CREATE TABLE IF NOT EXISTS custom_folders (
		id          INTEGER PRIMARY KEY AUTOINCREMENT,
		folder_id   TEXT NOT NULL UNIQUE,
		folder_name TEXT NOT NULL,
		sort_order  INTEGER NOT NULL DEFAULT 0
	)''')
	dbcon.commit()
	# Add any columns missing from pre-existing databases BEFORE inserting defaults
	_migrate_schema(dbcon)
	cur = dbcon.cursor()
	cur.execute('SELECT COUNT(*) as cnt FROM menu_items WHERE menu_name=?', (menu_name,))
	cnt = cur.fetchone()['cnt']
	if cnt < len(MENU_DEFAULTS.get(menu_name, [])):
		_populate_defaults(dbcon, menu_name)
	if not _session_defaults_synced:
		# control.addonVersion is shadowed by an unrelated function of the same name
		# elsewhere in control.py (takes a different addon as its argument) — use
		# addonInfo('version') directly here rather than the broken bare reference,
		# which was embedding a Python object repr (a per-process memory address)
		# instead of the actual version string, defeating the version-marker's whole
		# point of staying stable across restarts.
		_synced_version = '%s-%s' % (control.addonInfo('version'), _MENU_SCHEMA_REVISION)
		if _read_synced_version() != _synced_version:
			_sync_defaults(dbcon)
			_write_synced_version(_synced_version)
		_session_defaults_synced = True
	dbcon.close()


def get_menu_items(menu_name='root'):
	dbcon = _get_connection()
	cur = dbcon.cursor()
	cur.execute('SELECT * FROM menu_items WHERE menu_name=? AND enabled=1 ORDER BY sort_order', (menu_name,))
	items = cur.fetchall()
	dbcon.close()
	return items


def get_all_menu_items(menu_name='root'):
	dbcon = _get_connection()
	cur = dbcon.cursor()
	cur.execute('SELECT * FROM menu_items WHERE menu_name=? ORDER BY sort_order', (menu_name,))
	items = cur.fetchall()
	dbcon.close()
	return items


def toggle_item(menu_name, item_id):
	dbcon = _get_connection()
	dbcon.execute(
		'UPDATE menu_items SET enabled = CASE WHEN enabled=1 THEN 0 ELSE 1 END WHERE menu_name=? AND item_id=?',
		(menu_name, item_id)
	)
	dbcon.commit()
	dbcon.close()


def move_item_up(menu_name, item_id):
	dbcon = _get_connection()
	cur = dbcon.cursor()
	cur.execute('SELECT id, item_id, sort_order FROM menu_items WHERE menu_name=? ORDER BY sort_order', (menu_name,))
	rows = cur.fetchall()
	for i, row in enumerate(rows):
		if row['item_id'] == item_id and i > 0:
			prev = rows[i - 1]
			dbcon.execute('UPDATE menu_items SET sort_order=? WHERE id=?', (prev['sort_order'], row['id']))
			dbcon.execute('UPDATE menu_items SET sort_order=? WHERE id=?', (row['sort_order'], prev['id']))
			dbcon.commit()
			break
	dbcon.close()


def move_item_down(menu_name, item_id):
	dbcon = _get_connection()
	cur = dbcon.cursor()
	cur.execute('SELECT id, item_id, sort_order FROM menu_items WHERE menu_name=? ORDER BY sort_order', (menu_name,))
	rows = cur.fetchall()
	for i, row in enumerate(rows):
		if row['item_id'] == item_id and i < len(rows) - 1:
			nxt = rows[i + 1]
			dbcon.execute('UPDATE menu_items SET sort_order=? WHERE id=?', (nxt['sort_order'], row['id']))
			dbcon.execute('UPDATE menu_items SET sort_order=? WHERE id=?', (row['sort_order'], nxt['id']))
			dbcon.commit()
			break
	dbcon.close()


def reorder_enabled_items(menu_name, new_item_id_order):
	dbcon = _get_connection()
	cur = dbcon.cursor()
	cur.execute(
		'SELECT id, item_id, sort_order FROM menu_items WHERE menu_name=? AND enabled=1 ORDER BY sort_order',
		(menu_name,)
	)
	enabled_rows = cur.fetchall()
	old_sort_orders = [r['sort_order'] for r in enabled_rows]
	new_order_map = {item_id: old_sort_orders[i] for i, item_id in enumerate(new_item_id_order)}
	for row in enabled_rows:
		dbcon.execute('UPDATE menu_items SET sort_order=? WHERE id=?', (new_order_map[row['item_id']], row['id']))
	dbcon.commit()
	dbcon.close()


def move_item_to(menu_name, item_id, target_index):
	dbcon = _get_connection()
	cur = dbcon.cursor()
	cur.execute('SELECT id, item_id FROM menu_items WHERE menu_name=? ORDER BY sort_order', (menu_name,))
	rows = cur.fetchall()
	ids = [r['id'] for r in rows]
	moved_id = next((r['id'] for r in rows if r['item_id'] == item_id), None)
	if moved_id is None:
		dbcon.close()
		return
	ids.remove(moved_id)
	ids.insert(target_index, moved_id)
	for i, row_id in enumerate(ids):
		dbcon.execute('UPDATE menu_items SET sort_order=? WHERE id=?', (i, row_id))
	dbcon.commit()
	dbcon.close()


def delete_item(menu_name, item_id):
	dbcon = _get_connection()
	dbcon.execute('DELETE FROM menu_items WHERE menu_name=? AND item_id=? AND is_custom=1', (menu_name, item_id))
	dbcon.commit()
	dbcon.close()


def add_custom_item(menu_name, label, action, icon, poster, is_folder=1, is_action=1):
	dbcon = _get_connection()
	cur = dbcon.cursor()
	cur.execute('SELECT MAX(sort_order) as mx FROM menu_items WHERE menu_name=?', (menu_name,))
	row = cur.fetchone()
	next_order = (row['mx'] or 0) + 1
	import re
	base_id = 'custom_' + re.sub(r'[^a-z0-9]', '_', label.lower())[:30]
	item_id = base_id
	suffix = 1
	while True:
		cur.execute('SELECT id FROM menu_items WHERE menu_name=? AND item_id=?', (menu_name, item_id))
		if not cur.fetchone():
			break
		item_id = '%s_%d' % (base_id, suffix)
		suffix += 1
	dbcon.execute(
		'INSERT INTO menu_items (menu_name, item_id, label, action, icon, poster, is_folder, is_action, enabled, sort_order, is_custom, condition_key, queue, alt_label) '
		'VALUES (?,?,?,?,?,?,?,?,1,?,1,NULL,0,NULL)',
		(menu_name, item_id, label, action, icon, poster, is_folder, is_action, next_order)
	)
	dbcon.commit()
	dbcon.close()


def update_custom_item(menu_name, item_id, **kwargs):
	allowed = {'label', 'action', 'icon', 'poster', 'is_folder', 'is_action'}
	updates = {k: v for k, v in kwargs.items() if k in allowed}
	if not updates:
		return
	set_clause = ', '.join('%s=?' % k for k in updates)
	values = list(updates.values()) + [menu_name, item_id]
	dbcon = _get_connection()
	dbcon.execute(
		'UPDATE menu_items SET %s WHERE menu_name=? AND item_id=? AND is_custom=1' % set_clause,
		values
	)
	dbcon.commit()
	dbcon.close()


def get_custom_folders():
	dbcon = _get_connection()
	cur = dbcon.cursor()
	cur.execute('SELECT folder_id, folder_name FROM custom_folders ORDER BY sort_order, id')
	rows = cur.fetchall()
	dbcon.close()
	return rows


def create_custom_folder(folder_name):
	import re
	base = 'cf_' + re.sub(r'[^a-z0-9]', '_', folder_name.lower())[:30]
	folder_id = base
	dbcon = _get_connection()
	suffix = 1
	while True:
		cur = dbcon.cursor()
		cur.execute('SELECT id FROM custom_folders WHERE folder_id=?', (folder_id,))
		if not cur.fetchone():
			break
		folder_id = '%s_%d' % (base, suffix)
		suffix += 1
	cur.execute('SELECT MAX(sort_order) as mx FROM custom_folders')
	row = cur.fetchone()
	next_order = (row['mx'] or 0) + 1
	dbcon.execute('INSERT INTO custom_folders (folder_id, folder_name, sort_order) VALUES (?,?,?)',
		(folder_id, folder_name, next_order))
	dbcon.commit()
	dbcon.close()
	return folder_id


def rename_custom_folder(folder_id, new_name):
	dbcon = _get_connection()
	dbcon.execute('UPDATE custom_folders SET folder_name=? WHERE folder_id=?', (new_name, folder_id))
	dbcon.commit()
	dbcon.close()


def delete_custom_folder(folder_id):
	dbcon = _get_connection()
	dbcon.execute('DELETE FROM menu_items WHERE menu_name=?', (folder_id,))
	dbcon.execute('DELETE FROM custom_folders WHERE folder_id=?', (folder_id,))
	dbcon.commit()
	dbcon.close()


def reset_to_defaults(menu_name='root'):
	dbcon = _get_connection()
	dbcon.execute('DELETE FROM menu_items WHERE menu_name=? AND is_custom=0', (menu_name,))
	dbcon.commit()
	_populate_defaults(dbcon, menu_name)
	dbcon.close()
