# -*- coding: utf-8 -*-
from caches.base_cache import BaseCache, get_timestamp
# from modules.kodi_utils import logger

GET_ALL = 'SELECT id FROM maincache'
DELETE_ALL = 'DELETE FROM maincache'
LIKE_SELECT = 'SELECT id from maincache where id LIKE %s'
LIKE_DELETE = 'DELETE FROM maincache WHERE id LIKE %s'
CLEAN = 'DELETE from maincache WHERE CAST(expires AS INT) <= ?'

class MainCache(BaseCache):
	def __init__(self):
		BaseCache.__init__(self, 'maincache_db', 'maincache')

	def delete_all(self):
		try:
			dbcon = self.manual_connect('maincache_db')
			for i in dbcon.execute(GET_ALL): self.delete_memory_cache(str(i[0]))
			dbcon.execute(DELETE_ALL)
			dbcon.execute('VACUUM')
			return True
		except: return False

	def delete_all_folderscrapers(self):
		dbcon = self.manual_connect('maincache_db')
		remove_list = [str(i[0]) for i in dbcon.execute(LIKE_SELECT % "'FOLDERSCRAPER_%'").fetchall()]
		if not remove_list: return True
		try:
			dbcon.execute(LIKE_DELETE % "'FOLDERSCRAPER_%'")
			dbcon.execute('VACUUM')
			for item in remove_list: self.delete_memory_cache(str(item))
			return True
		except: return False

	def clean_database(self):
		try:
			dbcon = self.manual_connect('maincache_db')
			dbcon.execute(CLEAN, (get_timestamp(),))
			dbcon.execute('VACUUM')
			return True
		except: return False

main_cache = MainCache()

def cache_object(function, string, args, json=True, expiration=24):
	cache = main_cache.get(string)
	if cache is not None: return cache
	if isinstance(args, list): args = tuple(args)
	else: args = (args,)
	if json: result = function(*args).json()
	else: result = function(*args)
	main_cache.set(string, result, expiration=expiration)
	return result
