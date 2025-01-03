# -*- coding: utf-8 -*-
from caches.base_cache import connect_database, get_timestamp
# from modules.kodi_utils import logger

SELECT_RESULTS = 'SELECT results, expires FROM results_data WHERE provider = ? AND db_type = ? AND tmdb_id = ? AND title = ? AND year = ? AND season = ? AND episode = ?'
DELETE_RESULTS = 'DELETE FROM results_data WHERE provider = ? AND db_type = ? AND tmdb_id = ? AND title = ? AND year = ? AND season = ? AND episode = ?'
INSERT_RESULTS = 'INSERT OR REPLACE INTO results_data VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
SINGLE_DELETE = 'DELETE FROM results_data WHERE db_type=? AND tmdb_id=?'
FULL_DELETE = 'DELETE FROM results_data'
CLEAN = 'DELETE from results_data WHERE CAST(expires AS INT) <= ?'

class ExternalCache(object):
	def get(self, source, media_type, tmdb_id, title, year, season, episode):
		result = None
		try:
			cache_data = self._execute(SELECT_RESULTS, (source, media_type, tmdb_id, title, year, season, episode)).fetchone()
			if cache_data:
				if cache_data[1] > get_timestamp(): result = eval(cache_data[0])
				else: self.delete(source, media_type, title, year, tmdb_id, season, episode)
		except: pass
		return result

	def set(self, source, media_type, tmdb_id, title, year, season, episode, results, expire_time):
		try:
			expires = get_timestamp(expire_time)
			self._execute(INSERT_RESULTS, (source, media_type, tmdb_id, title, year, season, episode, repr(results or []), int(expires)))
		except: pass

	def delete(self, source, media_type, tmdb_id, title, season, episode):
		try:
			self._execute(DELETE_RESULTS, (source, media_type, tmdb_id, title, season, episode))
		except: return

	def delete_cache_single(self, media_type, tmdb_id):
		try:
			self._execute(SINGLE_DELETE, (media_type, tmdb_id))
			self._vacuum()
			return True
		except: return False

	def clear_cache(self):
		try:
			self._execute(FULL_DELETE, ())
			self._vacuum()
			return True
		except: return False

	def _execute(self, command, params):
		self.dbcon = connect_database('external_db')
		return self.dbcon.execute(command, params)

	def clean_database(self):
		try:
			dbcon = connect_database('external_db')
			dbcon.execute(CLEAN, (get_timestamp(),))
			dbcon.close()
			self._vacuum()
			return True
		except: return False

	def _vacuum(self):
		dbcon = connect_database('external_db')
		dbcon.execute('VACUUM')
		dbcon.close()

external_cache = ExternalCache()
