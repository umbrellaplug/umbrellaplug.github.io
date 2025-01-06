# -*- coding: utf-8 -*-
from modules.kodi_utils import database, favorites_db
# from modules.kodi_utils import logger

INSERT_FAV = 'INSERT INTO favourites VALUES (?, ?, ?)'
DELETE_FAV = 'DELETE FROM favourites where db_type=? and tmdb_id=?'
SELECT_FAV = 'SELECT tmdb_id, title FROM favourites WHERE db_type=?'
DELETE_TYPE = 'DELETE FROM favourites WHERE db_type=?'

class Favorites:
	def __init__(self):
		self.make_database_connection()
		self.set_PRAGMAS()

	def set_favourite(self, media_type, tmdb_id, title):
		try:
			self.dbcur.execute(INSERT_FAV, (media_type, str(tmdb_id), title))
			return True
		except: return False

	def delete_favourite(self, media_type, tmdb_id, title):
		try:
			self.dbcur.execute(DELETE_FAV, (media_type, str(tmdb_id)))
			return True
		except: return False

	def get_favorites(self, media_type):
		self.dbcur.execute(SELECT_FAV, (media_type,))
		result = self.dbcur.fetchall()
		result = [{'tmdb_id': str(i[0]), 'title': str(i[1])} for i in result]
		return result

	def clear_favorites(self, media_type):
		self.dbcur.execute(DELETE_TYPE, (media_type,))
		self.dbcur.execute('VACUUM')

	def make_database_connection(self):
		self.dbcon = database.connect(favorites_db, timeout=40.0, isolation_level=None)

	def set_PRAGMAS(self):
		self.dbcur = self.dbcon.cursor()
		self.dbcur.execute('''PRAGMA synchronous = OFF''')
		self.dbcur.execute('''PRAGMA journal_mode = OFF''')

favorites = Favorites()
