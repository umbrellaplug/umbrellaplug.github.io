# -*- coding: utf-8 -*-
from threading import Thread
from caches.base_cache import connect_database
from modules.kodi_utils import sleep, confirm_dialog, close_all_dialog
# from modules.kodi_utils import logger

SELECT = 'SELECT id FROM trakt_data'
DELETE = 'DELETE FROM trakt_data WHERE id=?'
DELETE_LIKE = 'DELETE FROM trakt_data WHERE id LIKE "%s"'
WATCHED_INSERT = 'INSERT OR IGNORE INTO watched VALUES (?, ?, ?, ?, ?, ?)'
WATCHED_DELETE = 'DELETE FROM watched WHERE db_type = ?'
PROGRESS_INSERT = 'INSERT OR IGNORE INTO progress VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
PROGRESS_DELETE = 'DELETE FROM progress WHERE db_type = ?'
STATUS_INSERT = 'INSERT INTO watched_status VALUES (?, ?, ?)'
STATUS_DELETE = 'DELETE FROM watched_status'
BASE_DELETE = 'DELETE FROM %s'
TC_BASE_GET = 'SELECT data FROM trakt_data WHERE id = ?'
TC_BASE_SET = 'INSERT OR REPLACE INTO trakt_data (id, data) VALUES (?, ?)'
TC_BASE_DELETE = 'DELETE FROM trakt_data WHERE id = ?'
DELETE_LISTS_WITH_MEDIA = 'SELECT id FROM maincache WHERE id LIKE %s'

class TraktCache:	
	def get(self, string):
		result = None
		try:
			dbcon = connect_database('trakt_db')
			cache_data = dbcon.execute(TC_BASE_GET, (string,)).fetchone()
			if cache_data: result = eval(cache_data[0])
		except: pass
		return result

	def set(self, string, data):
		try:
			dbcon = connect_database('trakt_db')
			dbcon.execute(TC_BASE_SET, (string, repr(data)))
		except: return None

	def delete(self, string):
		try:
			dbcon = connect_database('trakt_db')
			dbcon.execute(TC_BASE_DELETE, (string,))
		except: pass

trakt_cache = TraktCache()

class TraktWatched():
	def set_bulk_tvshow_status(self, insert_list):
		self._delete(STATUS_DELETE, ())
		self._executemany(STATUS_INSERT, insert_list)

	def set_tvshow_status(self, insert_dict):
		dbcon = connect_database('trakt_db')
		dbcon.execute('INSERT OR REPLACE INTO trakt_data (id, data) VALUES (?, ?)', ('trakt_tvshow_status', repr(insert_dict),))

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
		dbcon = connect_database('trakt_db')
		dbcon.executemany(command, insert_list)

	def _delete(self, command, args):
		dbcon = connect_database('trakt_db')
		dbcon.execute(command, args)
		dbcon.execute('VACUUM')

trakt_watched_cache = TraktWatched()

def cache_trakt_object(function, string, url):
	cache = trakt_cache.get(string)
	if cache: return cache
	result = function(url)
	trakt_cache.set(string, result)
	return result

def reset_activity(latest_activities):
	string = 'trakt_get_activity'
	try:
		dbcon = connect_database('trakt_db')
		data = dbcon.execute(TC_BASE_GET, (string,)).fetchone()
		if data: cached_data = eval(data[0])
		else: cached_data = default_activities()
		dbcon.execute(DELETE, (string,))
		trakt_cache.set(string, latest_activities)
	except: cached_data = default_activities()
	return cached_data

def clear_daily_cache():
	clear_trakt_calendar()
	clear_trakt_list_contents_data('my_lists')
	clear_trakt_list_contents_data('liked_lists')
	clear_trakt_list_contents_data('user_lists')

def clear_trakt_hidden_data(list_type):
	string = 'trakt_hidden_items_%s' % list_type
	try:
		dbcon = connect_database('trakt_db')
		dbcon.execute(DELETE, (string,))
	except: pass

def clear_trakt_collection_watchlist_data(list_type, media_type):
	if media_type == 'movies': media_type = 'movie'
	if media_type in ('tvshows', 'shows'): media_type = 'tvshow'
	string = 'trakt_%s_%s' % (list_type, media_type)
	try:
		dbcon = connect_database('trakt_db')
		dbcon.execute(DELETE, (string,))
	except: pass

def clear_trakt_calendar():
	try:
		dbcon = connect_database('trakt_db')
		dbcon.execute(DELETE_LIKE % 'trakt_get_my_calendar_%')
	except: return

def clear_trakt_list_contents_data(list_type):
	string = 'trakt_list_contents_' + list_type + '_%'
	try:
		dbcon = connect_database('trakt_db')
		dbcon.execute(DELETE_LIKE % string)
	except: pass

def clear_trakt_list_data(list_type):
	string = 'trakt_%s' % list_type
	try:
		dbcon = connect_database('trakt_db')
		dbcon.execute(DELETE, (string,))
	except: pass

def clear_trakt_recommendations():
	try:
		dbcon = connect_database('trakt_db')
		dbcon.execute(DELETE_LIKE % 'trakt_recommendations_%')
	except: return

def clear_trakt_favorites():
	try:
		dbcon = connect_database('trakt_db')
		dbcon.execute(DELETE_LIKE % 'trakt_favorites_%')
	except: return

def clear_all_trakt_cache_data(silent=False, refresh=True):
	try:
		start = silent or confirm_dialog()
		if not start: return False
		from caches.main_cache import main_cache
		main_cache_dbcon = connect_database('maincache_db')
		lists_with_media = main_cache_dbcon.execute(DELETE_LISTS_WITH_MEDIA % "'trakt_lists_with_media_%'").fetchall()
		for item in lists_with_media:
			try: main_cache.delete(item[0])
			except: pass
		main_cache.clean_database()
		dbcon = connect_database('trakt_db')
		for table in ('trakt_data', 'progress', 'watched', 'watched_status'): dbcon.execute(BASE_DELETE % table)
		dbcon.execute('VACUUM')
		if refresh:
			from apis.trakt_api import trakt_sync_activities
			Thread(target=trakt_sync_activities).start()
		return True
	except: return False

def default_activities():
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
	