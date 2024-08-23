# -*- coding: utf-8 -*-
# created by kodifitzwell
"""
	Umbrella Add-on
"""

import datetime
import time
from sqlite3 import dbapi2 as db
from resources.lib.modules.control import watchedcacheFile
# from resources.lib.modules.control import log


class WatchedCache:
	def __init__(self):
		self.__connect_database()
		self.__set_PRAGMAS()
		self.__create_cache_db()

	def __connect_database(self):
		self.dbcon = db.connect(watchedcacheFile, timeout=60, isolation_level=None)
		self.dbcon.row_factory = db.Row # return results indexed by field names and not numbers so we can convert to dict

	def __set_PRAGMAS(self):
		self.dbcur = self.dbcon.cursor()
		self.dbcur.execute('''PRAGMA journal_mode = OFF''')
		self.dbcur.execute('''PRAGMA synchronous = OFF''')

	def __del__(self):
		try:
			self.dbcur.close()
			self.dbcon.close()
		except: pass

	def __create_cache_db(self):
		# Create Watched table
		sql_create = """CREATE TABLE IF NOT EXISTS watched
		(media_type TEXT, imdb_id TEXT, tmdb_id TEXT, season INTEGER, episode INTEGER, title TEXT, last_played TEXT, overlay INTEGER, UNIQUE
		(imdb_id, tmdb_id, season, episode));"""
		self.dbcur.execute(sql_create)

		# Create Progress table
		sql_create = """CREATE TABLE IF NOT EXISTS progress
		(media_type TEXT, imdb_id TEXT, tmdb_id TEXT, season INTEGER, episode INTEGER, title TEXT, resume_point TEXT, curr_time TEXT, last_played TEXT, resume_id INTEGER, UNIQUE
		(imdb_id, tmdb_id, season, episode));"""
		self.dbcur.execute(sql_create)

	def select_single(self, query):
		try:
			self.dbcur.execute(query)
			return self.dbcur.fetchone()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def select_all(self, query, parms=None):
		try:
			if parms:
				self.dbcur.execute(query, parms)
			else:
				self.dbcur.execute(query)
			return self.dbcur.fetchall()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def insert(self, query, values):
		try:
			self.dbcur.execute(query, values)
			self.dbcon.commit()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()


def get_current_time():
	return int(time.mktime(datetime.datetime.now().timetuple()))


def get_watched(media_type, imdb_id, tmdb_id):
	sql_select = ''
	if media_type == 'movie':
		if imdb_id:
			sql_select = "SELECT * FROM watched WHERE imdb_id = '%s'" % imdb_id
		else:
			sql_select = "SELECT * FROM watched WHERE tmdb_id = '%s'" % tmdb_id
	elif media_type == 'tvshow':
		sql_select = "SELECT * FROM watched WHERE imdb_id = '%s'" % imdb_id
	elif media_type == 'season':
		sql_select = "SELECT * FROM watched WHERE imdb_id = '%s' AND season = %s" % (imdb_id, season)

	matchedrow = watched_cache.select_single(sql_select)
	if matchedrow: return dict(matchedrow)['overlay']
	else: return 4


def get_watched_episode(media_type, imdb_id, tmdb_id, season='', episode=''):
	if imdb_id:
		sql_select = "SELECT * FROM watched WHERE imdb_id = '%s'"  % imdb_id
	else:
		sql_select = "SELECT * FROM watched WHERE tmdb_id = '%s'"  % tmdb_id
	sql_select += ' AND season = %s AND episode = %s' % (season, episode)

	matchedrow = watched_cache.select_single(sql_select)
	if matchedrow: return dict(matchedrow)['overlay']
	else: return 4


def get_episodes_watched(media_type, imdb_id, tmdb_id):
	if imdb_id:
		sql_select = "SELECT * FROM watched WHERE imdb_id = '%s'"  % imdb_id
	else:
		sql_select = "SELECT * FROM watched WHERE tmdb_id = '%s'"  % tmdb_id

	matchedrow = watched_cache.select_all(sql_select)
	if matchedrow: return [dict(i) for i in matchedrow]
	else: return []


def change_watched(media_type, imdb_id, tmdb_id, season='', episode='', title='', watched=''):
	def _update_watched(media_type, imdb_id, tmdb_id, season='', episode='', title='', watched=''):
		last_played = get_current_time()
		if watched == 4:
			sql_update = "DELETE FROM watched WHERE media_type = ? AND imdb_id = ? AND season = ? and episode = ?"
			vals = (media_type, imdb_id, season, episode)
		else:
			sql_update = "INSERT OR REPLACE INTO watched VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
			vals = (media_type, imdb_id, tmdb_id, season, episode, title, last_played, watched)

		try:
			watched_cache.insert(sql_update, vals)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
	if media_type == 'movie':
		if not watched:
			watched = get_watched(media_type, imdb_id, tmdb_id)
			if watched == 4: watched = 5
			else: watched = 4
		# _update_watched(media_type, imdb_id, tmdb_id, season=0, episode=0, title=title, watched=watched)
		_update_watched(media_type, imdb_id, tmdb_id, title=title, watched=watched)
	elif media_type == 'episode':
		if not watched:
			watched = get_watched_episode(media_type, imdb_id, tmdb_id, season=season, episode=episode)
			if watched == 4: watched = 5
			else: watched = 4
		_update_watched(media_type, imdb_id, tmdb_id, season=season, episode=episode, title=title, watched=watched)


watched_cache = WatchedCache()
