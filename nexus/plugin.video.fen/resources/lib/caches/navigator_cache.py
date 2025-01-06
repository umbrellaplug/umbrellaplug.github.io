# -*- coding: utf-8 -*-
from modules.kodi_utils import get_property, set_property, clear_property, database, navigator_db
# from modules.kodi_utils import logger

GET_LIST = 'SELECT list_contents FROM navigator WHERE list_name = ? AND list_type = ?'
SET_LIST = 'INSERT OR REPLACE INTO navigator VALUES (?, ?, ?)'
DELETE_LIST = 'DELETE FROM navigator WHERE list_name=? and list_type=?'
GET_FOLDERS = 'SELECT list_name, list_contents FROM navigator WHERE list_type = ?'
GET_FOLDER_CONTENTS = 'SELECT list_contents FROM navigator WHERE list_name = ? AND list_type = ?'
prop_dict = {'default': 'fen_%s_default', 'edited': 'fen_%s_edited', 'shortcut_folder': 'fen_%s_shortcut_folder'}
timeout = 60

root_list = [
				{'name': 32028,
				'iconImage': 'movies',
				'mode': 'navigator.main',
				'action': 'MovieList'},
				{'name': 32029,
				'iconImage': 'tv',
				'mode': 'navigator.main',
				'action': 'TVShowList'},
				{'name': 32450,
				'iconImage': 'search',
				'mode': 'navigator.search'},
				{'name': 32451,
				'iconImage': 'discover',
				'mode': 'navigator.discover_main'},
				{'name': 32452,
				'iconImage': 'genre_family',
				'mode': 'build_popular_people',
				'isFolder': 'false'},
				{'name': 32453,
				'iconImage': 'favorites',
				'mode': 'navigator.favorites'},
				{'name': 32107,
				'iconImage': 'downloads',
				'mode': 'navigator.downloads'},
				{'name': 32454,
				'iconImage': 'lists',
				'mode': 'navigator.my_content'},
				{'name': 32455,
				'iconImage': 'premium',
				'mode': 'navigator.premium'},
				{'name': 32456,
				'iconImage': 'settings2',
				'mode': 'navigator.tools'}
			]

movie_list = [
				{'name': 32458,
				'iconImage': 'trending',
				'mode': 'build_movie_list',
				'action': 'trakt_movies_trending'},
				{'name': 33067,
				'iconImage': 'trending_recent',
				'mode': 'build_movie_list',
				'action': 'trakt_movies_trending_recent'},
				{'name': 32459,
				'iconImage': 'popular',
				'mode': 'build_movie_list',
				'action': 'tmdb_movies_popular'},
				{'name': 33010,
				'iconImage': 'popular_today',
				'mode': 'build_movie_list',
				'action': 'tmdb_movies_popular_today'},
				{'name': 32460,
				'action': 'tmdb_movies_premieres',
				'iconImage': 'fresh',
				'mode': 'build_movie_list'},
				{'name': 32461,
				'iconImage': 'dvd',
				'mode': 'build_movie_list',
				'action': 'tmdb_movies_latest_releases'},
				{'name': 32043,
				'iconImage': 'most_watched',
				'mode': 'build_movie_list',
				'action': 'trakt_movies_most_watched'},
				{'name': 32462,
				'action': 'trakt_movies_top10_boxoffice',
				'iconImage': 'box_office',
				'mode': 'build_movie_list'},
				{'name': 32463,
				'iconImage': 'most_voted',
				'mode': 'build_movie_list',
				'action': 'tmdb_movies_blockbusters'},
				{'name': 32464,
				'iconImage': 'intheatres',
				'mode': 'build_movie_list',
				'action': 'tmdb_movies_in_theaters'},
				{'name': 32469,
				'iconImage': 'lists',
				'mode': 'build_movie_list',
				'action': 'tmdb_movies_upcoming'},
				{'name': 32468,
				'iconImage': 'oscar_winners',
				'mode': 'build_movie_list',
				'action': 'imdb_movies_oscar_winners'},
				{'name': 32470,
				'iconImage': 'genres',
				'mode': 'navigator.genres',
				'menu_type': 'movie'},
				{'name': 32480,
				'iconImage': 'networks',
				'mode': 'navigator.networks',
				'menu_type': 'movie'},
				{'name': 32471,
				'iconImage': 'languages',
				'mode': 'navigator.languages',
				'menu_type': 'movie'},
				{'name': 32472,
				'iconImage': 'calender',
				'mode': 'navigator.years',
				'menu_type': 'movie'},
				{'name': 33085,
				'iconImage': 'calendar_decades',
				'mode': 'navigator.decades',
				'menu_type': 'movie'},
				{'name': 32473,
				'iconImage': 'certifications',
				'mode': 'navigator.certifications',
				'menu_type': 'movie'},
				{'name': 32474,
				'iconImage': 'because_you_watched',
				'mode': 'navigator.because_you_watched',
				'menu_type': 'movie'},
				{'name': 32475,
				'iconImage': 'watched_1',
				'mode': 'build_movie_list',
				'action': 'watched_movies'},
				{'name': 32226,
				'iconImage': 'watched_recent',
				'mode': 'build_movie_list',
				'action': 'recent_watched_movies'},
				{'name': 32476,
				'iconImage': 'player',
				'mode': 'build_movie_list',
				'action': 'in_progress_movies'}
			]
	
tvshow_list = [
				{'name': 32458,
				'action': 'trakt_tv_trending',
				'iconImage': 'trending',
				'mode': 'build_tvshow_list'},
				{'name': 33067,
				'iconImage': 'trending_recent',
				'mode': 'build_tvshow_list',
				'action': 'trakt_tv_trending_recent'},
				{'name': 32459,
				'action': 'tmdb_tv_popular',
				'iconImage': 'popular',
				'mode': 'build_tvshow_list'},
				{'name': 33010,
				'action': 'tmdb_tv_popular_today',
				'iconImage': 'popular_today',
				'mode': 'build_tvshow_list'},
				{'name': 32460,
				'action': 'tmdb_tv_premieres',
				'iconImage': 'fresh',
				'mode': 'build_tvshow_list'},
				{'name': 32043,
				'iconImage': 'most_watched',
				'mode': 'build_tvshow_list',
				'action': 'trakt_tv_most_watched'},
				{'name': 32478,
				'action': 'tmdb_tv_airing_today',
				'iconImage': 'live',
				'mode': 'build_tvshow_list'},
				{'name': 32479,
				'action': 'tmdb_tv_on_the_air',
				'iconImage': 'ontheair',
				'mode': 'build_tvshow_list'},
				{'name': 32469,
				'iconImage': 'lists',
				'mode': 'build_tvshow_list',
				'action': 'tmdb_tv_upcoming'},
				{'name': 32470,
				'iconImage': 'genres',
				'mode': 'navigator.genres',
				'menu_type': 'tvshow'},
				{'name': 32480,
				'iconImage': 'networks',
				'mode': 'navigator.networks',
				'menu_type': 'tvshow'},
				{'name': 32471,
				'iconImage': 'languages',
				'mode': 'navigator.languages',
				'menu_type': 'tvshow'},
				{'name': 32472,
				'iconImage': 'calender',
				'mode': 'navigator.years',
				'menu_type': 'tvshow'},
				{'name': 33085,
				'iconImage': 'calendar_decades',
				'mode': 'navigator.decades',
				'menu_type': 'tvshow'},
				{'name': 32473,
				'iconImage': 'certifications',
				'mode': 'navigator.certifications',
				'menu_type': 'tvshow'},
				{'name': 32474,
				'iconImage': 'because_you_watched',
				'mode': 'navigator.because_you_watched',
				'menu_type': 'tvshow'},
				{'name': 32475,
				'iconImage': 'watched_1',
				'mode': 'build_tvshow_list',
				'action': 'watched_tvshows'},
				{'name': 32481,
				'action': 'in_progress_tvshows',
				'iconImage': 'in_progress_tvshow',
				'mode': 'build_tvshow_list'},
				{'name': 32200,
				'iconImage': 'watched_recent',
				'mode': 'build_recently_watched_episode'},
				{'name': 32482,
				'iconImage': 'player',
				'mode': 'build_in_progress_episode'},
				{'name': 32483,
				'iconImage': 'next_episodes',
				'mode': 'build_next_episode'}
			]

default_menu_items = ('RootList', 'MovieList', 'TVShowList')
main_menus = {'RootList': root_list, 'MovieList': movie_list, 'TVShowList': tvshow_list}
main_menu_items = {'RootList': {'name': 32457, 'iconImage': 'fen', 'mode': 'navigator.main', 'action': 'RootList'},
					'MovieList': root_list[0],
					'TVShowList': root_list[1]}

class NavigatorCache:
	def __init__(self):
		self._connect_database()
		self._set_PRAGMAS()

	def get_main_lists(self, list_name):
		default_contents = self.get_memory_cache(list_name, 'default')
		if not default_contents:
			default_contents = self.get_list(list_name, 'default')
			if default_contents == None:
				self.rebuild_database()
				return self.get_main_lists(list_name)
			try: edited_contents = self.get_list(list_name, 'edited')
			except: edited_contents = None
		else: edited_contents = self.get_memory_cache(list_name, 'edited')
		return default_contents, edited_contents

	def get_list(self, list_name, list_type):
		contents = None
		try: contents = eval(self.dbcur.execute(GET_LIST, (list_name, list_type)).fetchone()[0])
		except: pass
		return contents

	def set_list(self, list_name, list_type, list_contents):
		self.dbcur.execute(SET_LIST, (list_name, list_type, repr(list_contents)))
		self.set_memory_cache(list_name, list_type, list_contents)

	def delete_list(self, list_name, list_type):
		self.dbcur.execute(DELETE_LIST, (list_name, list_type))
		self.delete_memory_cache(list_name, list_type)
		self.dbcon.execute('VACUUM')
	
	def get_memory_cache(self, list_name, list_type):
		try: return eval(get_property(self._get_list_prop(list_type) % list_name))
		except: return None
	
	def set_memory_cache(self, list_name, list_type, list_contents):
		set_property(self._get_list_prop(list_type) % list_name, repr(list_contents))

	def delete_memory_cache(self, list_name, list_type):
		clear_property(self._get_list_prop(list_type) % list_name)

	def get_shortcut_folders(self):
		try:
			folders = self.dbcur.execute(GET_FOLDERS, ('shortcut_folder',)).fetchall()
			folders = sorted([(str(i[0]), eval(i[1])) for i in folders], key=lambda s: s[0].lower())
		except: folders = []
		return folders

	def get_shortcut_folder_contents(self, list_name):
		contents = []
		try: contents = eval(self.dbcur.execute(GET_FOLDER_CONTENTS, (list_name, 'shortcut_folder')).fetchone()[0])
		except: pass
		return contents

	def currently_used_list(self, list_name):
		default_contents, edited_contents = self.get_main_lists(list_name)
		list_items = edited_contents or default_contents
		return list_items

	def rebuild_database(self):
		for list_name in default_menu_items: self.set_list(list_name, 'default', main_menus[list_name])

	def _get_list_prop(self, list_type):
		return prop_dict[list_type]

	def _connect_database(self):
		self.dbcon = database.connect(navigator_db, timeout=timeout, isolation_level=None)

	def _set_PRAGMAS(self):
		self.dbcur = self.dbcon.cursor()
		self.dbcur.execute('''PRAGMA synchronous = OFF''')
		self.dbcur.execute('''PRAGMA journal_mode = OFF''')

navigator_cache = NavigatorCache()
