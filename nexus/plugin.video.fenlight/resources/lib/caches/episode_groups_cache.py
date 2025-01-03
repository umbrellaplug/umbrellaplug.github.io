# -*- coding: utf-8 -*-
from caches.base_cache import connect_database
# from modules.kodi_utils import logger

SET = 'INSERT OR REPLACE INTO groups_data VALUES (?, ?)'
GET = 'SELECT data FROM groups_data WHERE tmdb_id = ?'
DELETE = 'DELETE FROM groups_data where tmdb_id=?'
DELETE_ALL = 'DELETE FROM groups_data'
string = str

class EpisodeGroupsCache:
	def get(self, tmdb_id):
		try: data = eval(connect_database('episode_groups_db').execute(GET, (string(tmdb_id),)).fetchone()[0])
		except: data = {}
		return data

	def set(self, tmdb_id, data):
		connect_database('episode_groups_db').execute(SET, (string(tmdb_id), repr(data)))

	def delete(self, tmdb_id):
		dbcon = connect_database('episode_groups_db')
		dbcon.execute(DELETE, (string(tmdb_id),))
		dbcon.execute('VACUUM')

	def clear_cache(self):
		dbcon = connect_database('episode_groups_db')
		dbcon.execute(DELETE_ALL)
		dbcon.execute('VACUUM')

episode_groups_cache = EpisodeGroupsCache()
