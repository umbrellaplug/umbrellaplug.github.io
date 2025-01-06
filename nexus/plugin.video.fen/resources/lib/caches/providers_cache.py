# -*- coding: utf-8 -*-
import time
from datetime import datetime, timedelta
from modules.kodi_utils import confirm_dialog, path_exists, database, external_db
# from modules.kodi_utils import logger

SELECT_RESULTS = 'SELECT results, expires FROM results_data WHERE provider = ? AND db_type = ? AND tmdb_id = ? AND title = ? AND year = ? AND season = ? AND episode = ?'
DELETE_RESULTS = 'DELETE FROM results_data WHERE provider = ? AND db_type = ? AND tmdb_id = ? AND title = ? AND year = ? AND season = ? AND episode = ?'
INSERT_RESULTS = 'INSERT OR REPLACE INTO results_data VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
SINGLE_DELETE = 'DELETE FROM results_data WHERE db_type=? AND tmdb_id=?'
FULL_DELETE = 'DELETE FROM results_data'
timeout = 240

class ExternalProvidersCache(object):
	def __init__(self):
		self._connect_database()
		self._set_PRAGMAS()
		self.time = datetime.now()

	def get(self, source, media_type, tmdb_id, title, year, season, episode):
		result = None
		try:
			self._execute(SELECT_RESULTS, (source, media_type, tmdb_id, title, year, season, episode))
			cache_data = self.dbcur.fetchone()
			if cache_data:
				if cache_data[1] > self._get_timestamp(self.time): result = eval(cache_data[0])
				else: self.delete(source, media_type, title, year, tmdb_id, season, episode, dbcon)
		except: pass
		return result

	def set(self, source, media_type, tmdb_id, title, year, season, episode, results, expire_time):
		try:
			expiration = timedelta(hours=expire_time)
			expires = self._get_timestamp(self.time + expiration)
			self._execute(INSERT_RESULTS, (source, media_type, tmdb_id, title, year, season, episode, repr(results or []), int(expires)))
		except: pass

	def delete(self, source, media_type, tmdb_id, title, season, episode):
		try: self._execute(DELETE_RESULTS, (source, media_type, tmdb_id, title, season, episode))
		except: return

	def _get_timestamp(self, date_time):
		return int(time.mktime(date_time.timetuple()))

	def delete_cache(self, silent=False):
		try:
			if not path_exists(external_db): return 'failure'
			if not silent and not confirm_dialog(): return 'cancelled'
			self._execute(FULL_DELETE, ())
			self._vacuum()
			return 'success'
		except: return 'failure'

	def delete_cache_single(self, media_type, tmdb_id):
		try:
			if not path_exists(external_db): return False
			self._execute(SINGLE_DELETE, (media_type, tmdb_id))
			self._vacuum()
			return True
		except: return False

	def _connect_database(self):
		self.dbcon = database.connect(external_db, timeout=timeout, isolation_level=None)

	def _execute(self, command, params):
		self.dbcur.execute(command, params)

	def _vacuum(self):
		self.dbcur.execute('VACUUM')

	def _set_PRAGMAS(self):
		self.dbcur = self.dbcon.cursor()
		self.dbcur.execute('''PRAGMA synchronous = OFF''')
		self.dbcur.execute('''PRAGMA journal_mode = OFF''')
