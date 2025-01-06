# -*- coding: utf-8 -*-
from modules.kodi_utils import sleep, confirm_dialog, close_all_dialog, trakt_db, database, Thread
# from modules.kodi_utils import logger

SELECT = 'SELECT id FROM trakt_data'
DELETE = 'DELETE FROM trakt_data WHERE id=?'
DELETE_LIKE = 'DELETE FROM trakt_data WHERE id LIKE "%s"'
WATCHED_INSERT = 'INSERT OR IGNORE INTO watched_status VALUES (?, ?, ?, ?, ?, ?)'
WATCHED_DELETE = 'DELETE FROM watched_status WHERE db_type = ?'
PROGRESS_INSERT = 'INSERT OR IGNORE INTO progress VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
PROGRESS_DELETE = 'DELETE FROM progress WHERE db_type = ?'
BASE_DELETE = 'DELETE FROM %s'
TC_BASE_GET = 'SELECT data FROM trakt_data WHERE id = ?'
TC_BASE_SET = 'INSERT OR REPLACE INTO trakt_data (id, data) VALUES (?, ?)'
TC_BASE_DELETE = 'DELETE FROM trakt_data WHERE id = ?'
timeout = 60

class TraktWatched:
	def __init__(self):
		self._connect_database()
		self._set_PRAGMAS()

	def set_bulk_movie_watched(self, insert_list):
		self._delete(WATCHED_DELETE, ('movie',))
		self._executemany(WATCHED_INSERT, insert_list)

	def set_bulk_tvshow_watched(self, insert_list):
		self._delete(WATCHED_DELETE, ('episode',))
		self._executemany(WATCHED_INSERT, insert_list)

	def set_bulk_movie_progress(self, insert_list):
		self._delete(PROGRESS_DELETE, ('movie',))
		self._executemany(PROGRESS_INSERT, insert_list)

	def set_bulk_tvshow_progress(self, insert_list):
		self._delete(PROGRESS_DELETE, ('episode',))
		self._executemany(PROGRESS_INSERT, insert_list)

	def _executemany(self, command, insert_list):
		self.dbcur.executemany(command, insert_list)

	def _delete(self, command, args):
		self.dbcur.execute(command, args)
		self.dbcur.execute('VACUUM')

	def _connect_database(self):
		self.dbcon = database.connect(trakt_db, timeout=timeout, isolation_level=None)

	def _set_PRAGMAS(self):
		self.dbcur = self.dbcon.cursor()
		self.dbcur.execute('''PRAGMA synchronous = OFF''')
		self.dbcur.execute('''PRAGMA journal_mode = OFF''')

class TraktCache:
	def get(self, string):
		result = None
		try:
			dbcon = self.connect_database()
			dbcur = self.set_PRAGMAS(dbcon)
			dbcur.execute(TC_BASE_GET, (string,))
			cache_data = dbcur.fetchone()
			if cache_data: result = eval(cache_data[0])
		except: pass
		return result

	def set(self, string, data):
		try:
			dbcon = self.connect_database()
			dbcur = self.set_PRAGMAS(dbcon)
			dbcur.execute(TC_BASE_SET, (string, repr(data)))
		except: return None

	def delete(self, string, dbcon=None):
		try:
			if not dbcon: self.connect_database()
			dbcur = self.set_PRAGMAS(dbcon)
			dbcur.execute(TC_BASE_DELETE, (string,))
		except: pass

	def connect_database(self):
		return database.connect(trakt_db, timeout=timeout, isolation_level=None)

	def set_PRAGMAS(self, dbcon):
		dbcur = dbcon.cursor()
		dbcur.execute('''PRAGMA synchronous = OFF''')
		dbcur.execute('''PRAGMA journal_mode = OFF''')
		return dbcur

_cache = TraktCache()

def cache_trakt_object(function, string, url):
	cache = _cache.get(string)
	if cache: return cache
	result = function(url)
	_cache.set(string, result)
	return result

def reset_activity(latest_activities):
	string = 'trakt_get_activity'
	cached_data = None
	try:
		dbcon = _cache.connect_database()
		dbcur = _cache.set_PRAGMAS(dbcon)
		dbcur.execute(TC_BASE_GET, (string,))
		cached_data = dbcur.fetchone()
		if cached_data: cached_data = eval(cached_data[0])
		else: cached_data = default_activities()
		dbcur.execute(DELETE, (string,))
		_cache.set(string, latest_activities)
	except: pass
	return cached_data

def clear_trakt_hidden_data(list_type):
	string = 'trakt_hidden_items_%s' % list_type
	try:
		dbcon = _cache.connect_database()
		dbcur = _cache.set_PRAGMAS(dbcon)
		dbcur.execute(DELETE, (string,))
	except: pass

def clear_trakt_collection_watchlist_data(list_type, media_type):
	if media_type == 'movies': media_type = 'movie' 
	if media_type in ('tvshows', 'shows'): media_type = 'tvshow' 
	string = 'trakt_%s_%s' % (list_type, media_type)
	if media_type == 'movie': clear_trakt_movie_sets()
	try:
		dbcon = _cache.connect_database()
		dbcur = _cache.set_PRAGMAS(dbcon)
		dbcur.execute(DELETE, (string,))
	except: pass

def clear_trakt_list_contents_data(list_type):
	string = 'trakt_list_contents_' + list_type + '_%'
	try:
		dbcon = _cache.connect_database()
		dbcur = _cache.set_PRAGMAS(dbcon)
		dbcur.execute(DELETE_LIKE % string)
	except: pass

def clear_trakt_list_data(list_type):
	string = 'trakt_%s' % list_type
	try:
		dbcon = _cache.connect_database()
		dbcur = _cache.set_PRAGMAS(dbcon)
		dbcur.execute(DELETE, (string,))
	except: pass

def clear_trakt_calendar():
	try:
		dbcon = _cache.connect_database()
		dbcur = _cache.set_PRAGMAS(dbcon)
		dbcur.execute(DELETE_LIKE % 'trakt_get_my_calendar_%')
	except: return

def clear_trakt_recommendations():
	try:
		dbcon = _cache.connect_database()
		dbcur = _cache.set_PRAGMAS(dbcon)
		dbcur.execute(DELETE_LIKE % 'trakt_recommendations_%')
	except: return

def clear_trakt_favorites():
	try:
		dbcon = _cache.connect_database()
		dbcur = _cache.set_PRAGMAS(dbcon)
		dbcur.execute(DELETE_LIKE % 'trakt_favorites_%')
	except: return

def clear_trakt_movie_sets():
	string = 'trakt_movie_sets'
	try:
		dbcon = _cache.connect_database()
		dbcur = _cache.set_PRAGMAS(dbcon)
		dbcur.execute(DELETE, (string,))
	except: pass

def clear_all_trakt_cache_data(silent=False, refresh=True):
	try:
		start = silent or confirm_dialog()
		if not start: return False
		dbcon = _cache.connect_database()
		dbcur = _cache.set_PRAGMAS(dbcon)
		for table in ('trakt_data', 'progress', 'watched_status'): dbcur.execute(BASE_DELETE % table)
		dbcur.execute('VACUUM')
		if refresh:
			from apis.trakt_api import trakt_sync_activities
			Thread(target=trakt_sync_activities).start()
		return True
	except: return False

def default_activities():
	'2020-01-01T00:00:01.000Z'
	return {
			'all': '2024-01-22T00:22:21.000Z',
			'movies':
				{
				'watched_at': '2020-01-01T00:00:01.000Z',
				'collected_at': '2020-01-01T00:00:01.000Z',
				'rated_at': '2020-01-01T00:00:01.000Z',
				'watchlisted_at': '2020-01-01T00:00:01.000Z',
				'favorited_at': '2020-01-01T00:00:01.000Z',
				'recommendations_at': '2020-01-01T00:00:01.000Z',
				'commented_at': '2020-01-01T00:00:01.000Z',
				'paused_at': '2020-01-01T00:00:01.000Z',
				'hidden_at': '2020-01-01T00:00:01.000Z'
				},
			'episodes':
				{
				'watched_at': '2020-01-01T00:00:01.000Z',
				'collected_at': '2020-01-01T00:00:01.000Z',
				'rated_at': '2020-01-01T00:00:01.000Z',
				'watchlisted_at': '2020-01-01T00:00:01.000Z',
				'commented_at': '2020-01-01T00:00:01.000Z',
				'paused_at': '2020-01-01T00:00:01.000Z'
				},
			'shows':
				{
				'rated_at': '2020-01-01T00:00:01.000Z',
				'watchlisted_at': '2020-01-01T00:00:01.000Z',
				'favorited_at': '2020-01-01T00:00:01.000Z',
				'recommendations_at': '2020-01-01T00:00:01.000Z',
				'commented_at': '2020-01-01T00:00:01.000Z',
				'hidden_at': '2020-01-01T00:00:01.000Z'
				},
			'seasons':
				{
				'rated_at': '2020-01-01T00:00:01.000Z',
				'watchlisted_at': '2020-01-01T00:00:01.000Z',
				'commented_at': '2020-01-01T00:00:01.000Z',
				'hidden_at': '2020-01-01T00:00:01.000Z'
				},
			'comments':
				{
				'liked_at': '2020-01-01T00:00:01.000Z',
				'blocked_at': '2020-01-01T00:00:01.000Z'
				},
			'lists':
				{
				'liked_at': '2020-01-01T00:00:01.000Z',
				'updated_at': '2020-01-01T00:00:01.000Z',
				'commented_at': '2020-01-01T00:00:01.000Z'
				},
			'watchlist':
				{
				'updated_at': '2020-01-01T00:00:01.000Z'
				},
			'favorites':
				{
				'updated_at': '2020-01-01T00:00:01.000Z'
				},
			'recommendations':
				{
				'updated_at': '2020-01-01T00:00:01.000Z'
				},
			'collaborations':
				{
				'updated_at': '2020-01-01T00:00:01.000Z'
				},
			'account':
				{
				'settings_at': '2020-01-01T00:00:01.000Z',
				'followed_at': '2020-01-01T00:00:01.000Z',
				'following_at': '2020-01-01T00:00:01.000Z',
				'pending_at': '2020-01-01T00:00:01.000Z',
				'requested_at': '2020-01-01T00:00:01.000Z'
				},
			'saved_filters':
				{
				'updated_at': '2020-01-01T00:00:01.000Z'
				},
			'notes':
				{
				'updated_at': '2020-01-01T00:00:01.000Z'
				}
			}
	