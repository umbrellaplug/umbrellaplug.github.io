# -*- coding: utf-8 -*-
from caches.base_cache import connect_database
# from modules.kodi_utils import logger

INSERT_ONE = 'INSERT OR REPLACE INTO discover VALUES (?, ?, ?)'
DELETE_ONE = 'DELETE FROM discover where id=?'
SELECT_TYPE = 'SELECT * FROM discover WHERE db_type == ?'
DELETE_TYPE = 'DELETE FROM discover WHERE db_type=?'

class DiscoverCache:
	def insert_one(self, _id, db_type, data):
		dbcon = connect_database('discover_db')
		dbcon.execute(INSERT_ONE, (_id, db_type, data))

	def delete_one(self, _id):
		dbcon = connect_database('discover_db')
		dbcon.execute(DELETE_ONE, (_id,))
		dbcon.execute('VACUUM')

	def get_all(self, db_type):
		dbcon = connect_database('discover_db')
		return [{'id': i[0], 'data': i[2]} for i in reversed(dbcon.execute(SELECT_TYPE, (db_type,)).fetchall())]

	def clear_cache(self, db_type):
		dbcon = connect_database('discover_db')
		dbcon.execute(DELETE_TYPE, (db_type,))
		dbcon.execute('VACUUM')

discover_cache = DiscoverCache()
