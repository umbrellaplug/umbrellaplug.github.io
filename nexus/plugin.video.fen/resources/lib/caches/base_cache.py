# -*- coding: utf-8 -*-
import time
from datetime import datetime, timedelta
from modules.kodi_utils import get_property, set_property, clear_property, database
from modules import kodi_utils
from modules.utils import make_thread_list
logger = kodi_utils.logger

database, delete_file, navigator_db, watched_db, favorites_db = kodi_utils.database, kodi_utils.delete_file, kodi_utils.navigator_db, kodi_utils.watched_db, kodi_utils.favorites_db
trakt_db, maincache_db, metacache_db, debridcache_db = kodi_utils.trakt_db, kodi_utils.maincache_db, kodi_utils.metacache_db, kodi_utils.debridcache_db
ls, notification, confirm_dialog, ok_dialog, open_file = kodi_utils.local_string, kodi_utils.notification, kodi_utils.confirm_dialog, kodi_utils.ok_dialog, kodi_utils.open_file
external_db, databases_path, current_dbs, kodi_refresh, sleep = kodi_utils.external_db, kodi_utils.databases_path, kodi_utils.current_dbs, kodi_utils.kodi_refresh, kodi_utils.sleep
path_exists, list_dirs, progress_dialog, make_directory = kodi_utils.path_exists, kodi_utils.list_dirs, kodi_utils.progress_dialog, kodi_utils.make_directory
show_busy_dialog, hide_busy_dialog = kodi_utils.show_busy_dialog, kodi_utils.hide_busy_dialog

BASE_GET = 'SELECT expires, data FROM %s WHERE id = ?'
BASE_SET = 'INSERT OR REPLACE INTO %s(id, data, expires) VALUES (?, ?, ?)'
BASE_DELETE = 'DELETE FROM %s WHERE id = ?'

def check_databases():
	if not path_exists(databases_path): make_directory(databases_path)
	remove_old_caches()
	#Navigator
	dbcon = database.connect(navigator_db)
	dbcon.execute("""CREATE TABLE IF NOT EXISTS navigator
				(list_name text, list_type text, list_contents text, unique(list_name, list_type))""")
	dbcon.close()
	# Watched Status
	dbcon = database.connect(watched_db)
	dbcon.execute("""CREATE TABLE IF NOT EXISTS watched_status
					(db_type text, media_id text, season integer, episode integer, last_played text, title text, unique(db_type, media_id, season, episode))""")
	dbcon.execute("""CREATE TABLE IF NOT EXISTS progress
					(db_type text, media_id text, season integer, episode integer, resume_point text, curr_time text,
					last_played text, resume_id integer, title text, unique(db_type, media_id, season, episode))""")
	dbcon.close()
	# Favorites
	dbcon = database.connect(favorites_db)
	dbcon.execute("""CREATE TABLE IF NOT EXISTS favourites (db_type text, tmdb_id text, title text, unique (db_type, tmdb_id))""")
	dbcon.close()
	# Trakt
	dbcon = database.connect(trakt_db)
	dbcon.execute("""CREATE TABLE IF NOT EXISTS trakt_data (id text unique, data text)""")
	dbcon.execute("""CREATE TABLE IF NOT EXISTS watched_status
					(db_type text, media_id text, season integer, episode integer, last_played text, title text, unique(db_type, media_id, season, episode))""")
	dbcon.execute("""CREATE TABLE IF NOT EXISTS progress
					(db_type text, media_id text, season integer, episode integer, resume_point text, curr_time text,
					last_played text, resume_id integer, title text, unique(db_type, media_id, season, episode))""")
	dbcon.close()
	# Main Cache
	dbcon = database.connect(maincache_db)
	dbcon.execute("""CREATE TABLE IF NOT EXISTS maincache (id text unique, data text, expires integer)""")
	dbcon.close()
	# Meta Cache
	dbcon = database.connect(metacache_db)
	dbcon.execute("""CREATE TABLE IF NOT EXISTS metadata
					  (db_type text not null, tmdb_id text not null, imdb_id text, tvdb_id text, meta text, expires integer, unique (db_type, tmdb_id))""")
	dbcon.execute("""CREATE TABLE IF NOT EXISTS season_metadata (tmdb_id text not null unique, meta text, expires integer)""")
	dbcon.execute("""CREATE TABLE IF NOT EXISTS function_cache (string_id text not null, data text, expires integer)""")
	dbcon.close()
	# Debrid Cache
	dbcon = database.connect(debridcache_db)
	dbcon.execute("""CREATE TABLE IF NOT EXISTS debrid_data (hash text not null, debrid text not null, cached text, expires integer, unique (hash, debrid))""")
	dbcon.close()
	# External Providers Cache
	dbcon = database.connect(external_db)
	dbcon.execute("""CREATE TABLE IF NOT EXISTS results_data
					(provider text, db_type text, tmdb_id text, title text, year integer, season text, episode text, results text,
					expires integer, unique (provider, db_type, tmdb_id, title, year, season, episode))""")
	dbcon.close()

def remove_old_caches():
	try:
		files = list_dirs(databases_path)[1]
		for item in files:
			if not item in current_dbs:
				try: delete_file(databases_path + item)
				except: pass
	except: pass

def clean_databases(current_time=None, database_check=True, silent=False):
	def _process(args):
		try:
			dbcon = database.connect(args[0], timeout=60.0)
			dbcur = dbcon.cursor()
			dbcur.execute('''PRAGMA synchronous = OFF''')
			dbcur.execute('''PRAGMA journal_mode = OFF''')
			dbcur.execute(args[1], (current_time,))
			dbcon.commit()
			dbcur.execute('VACUUM')
		except: pass
	if database_check: check_databases()
	if not current_time: current_time = get_current_time()
	command_base = 'DELETE from %s WHERE CAST(%s AS INT) <= ?'
	functions_list = ((external_db, command_base % ('results_data', 'expires')),
					(maincache_db, command_base % ('maincache', 'expires')),
					(metacache_db, command_base % ('metadata', 'expires')),
					(metacache_db, command_base % ('function_cache', 'expires')),
					(metacache_db, command_base % ('season_metadata', 'expires')),
					(debridcache_db, command_base % ('debrid_data', 'expires')))
	threads = list(make_thread_list(_process, functions_list))
	[i.join() for i in threads]
	limit_metacache_database()
	if not silent: notification(32576, time=2000)

def check_corrupt_databases():
	def _process(args):
		try:
			dbcon = database.connect(args[0])
			for db_table in args[1]: dbcon.execute(command_base % db_table)
		except:
			database_errors.append(args[2])
			if path_exists(args[0]):
				try: dbcon.close()
				except: pass
				delete_file(args[0])
	show_busy_dialog()
	command_base = 'SELECT * FROM %s LIMIT 1'
	database_errors = []
	functions_list = (
		(navigator_db, ('navigator',), 'NAVIGATOR'),
		(watched_db, ('watched_status', 'progress'), 'WATCHED'),
		(favorites_db, ('favourites',), 'FAVORITES'),
		(trakt_db, ('trakt_data', 'watched_status', 'progress'), 'TRAKT'),
		(maincache_db, ('maincache',), 'MAIN'),
		(metacache_db, ('metadata', 'season_metadata', 'function_cache'), 'META'),
		(debridcache_db, ('debrid_data',), 'DEBRID'),
		(external_db, ('results_data',), 'EXTERNAL SCRAPERS')
		)
	threads = list(make_thread_list(_process, functions_list))
	[i.join() for i in threads]
	check_databases()
	hide_busy_dialog()
	if database_errors: ok_dialog(text='%s[CR][CR]%s' % (ls(32213), ', '.join(database_errors)))
	else: notification(ls(32237), time=3000)

def limit_metacache_database(max_size=60):
	with open_file(metacache_db) as f: s = f.size()
	size = round(float(s)/1048576, 1)
	if size < max_size: return
	dbcon = database.connect(metacache_db, timeout=60.0)
	dbcur = dbcon.cursor()
	dbcur.execute('''PRAGMA synchronous = OFF''')
	dbcur.execute('''PRAGMA journal_mode = OFF''')
	dbcur.execute('DELETE FROM metadata WHERE ROWID IN (SELECT ROWID FROM metadata ORDER BY ROWID DESC LIMIT -1 OFFSET 4000)')
	dbcur.execute('DELETE FROM function_cache WHERE ROWID IN (SELECT ROWID FROM function_cache ORDER BY ROWID DESC LIMIT -1 OFFSET 100)')
	dbcur.execute('DELETE FROM season_metadata WHERE ROWID IN (SELECT ROWID FROM season_metadata ORDER BY ROWID DESC LIMIT -1 OFFSET 100)')
	dbcon.commit()
	dbcon.execute('VACUUM')

def get_current_time():
	return int(time.mktime(datetime.now().timetuple()))

def clear_cache(cache_type, silent=False):
	def _confirm(): return silent or confirm_dialog()
	success = True
	if cache_type == 'meta':
		from caches.trakt_cache import clear_trakt_movie_sets
		from caches.meta_cache import delete_meta_cache
		clear_trakt_movie_sets()
		success = delete_meta_cache(silent=silent)
	elif cache_type == 'internal_scrapers':
		if not _confirm(): return
		from apis import furk_api, easynews_api
		furk_api.clear_media_results_database()
		easynews_api.clear_media_results_database()
		for item in ('pm_cloud', 'rd_cloud', 'ad_cloud', 'folders'): clear_cache(item, silent=True)
	elif cache_type == 'external_scrapers':
		from caches.providers_cache import ExternalProvidersCache
		from caches.debrid_cache import debrid_cache
		data = ExternalProvidersCache().delete_cache(silent=silent)
		clear_debrid_result = debrid_cache.clear_database()
		success = (data, clear_debrid_result) == ('success', 'success')
	elif cache_type == 'trakt':
		from caches.trakt_cache import clear_all_trakt_cache_data
		success = clear_all_trakt_cache_data(silent=silent)
	elif cache_type == 'imdb':
		if not _confirm(): return
		from apis.imdb_api import clear_imdb_cache
		success = clear_imdb_cache()
	elif cache_type == 'pm_cloud':
		if not _confirm(): return
		from apis.premiumize_api import PremiumizeAPI
		success = PremiumizeAPI().clear_cache()
	elif cache_type == 'rd_cloud':
		if not _confirm(): return
		from apis.real_debrid_api import RealDebridAPI
		success = RealDebridAPI().clear_cache()
	elif cache_type == 'ad_cloud':
		if not _confirm(): return
		from apis.alldebrid_api import AllDebridAPI
		success = AllDebridAPI().clear_cache()
	elif cache_type == 'folders':
		from caches.main_cache import main_cache
		main_cache.delete_all_folderscrapers()
	else: # 'list'
		if not _confirm(): return
		from caches.main_cache import main_cache
		main_cache.delete_all_lists()
	if not silent and success: notification(32576)

def clear_all_cache():
	if not confirm_dialog(): return
	progressDialog = progress_dialog()
	line = '%s....[CR]%s'
	caches = (('meta', '%s %s' % (ls(32527), ls(32524))), ('internal_scrapers', '%s %s' % (ls(32096), ls(32524))), ('external_scrapers', '%s %s' % (ls(32118), ls(32524))),
			('trakt', ls(32087)), ('imdb', '%s %s' % (ls(32064), ls(32524))), ('list', '%s %s' % (ls(32815), ls(32524))),
			('pm_cloud', '%s %s' % (ls(32061), ls(32524))), ('rd_cloud', '%s %s' % (ls(32054), ls(32524))), ('ad_cloud', '%s %s' % (ls(32063), ls(32524))))
	for count, cache_type in enumerate(caches, 1):
		try:
			progressDialog.update(line % (ls(32816), cache_type[1]), int(float(count) / float(len(caches)) * 100))
			clear_cache(cache_type[0], silent=True)
			sleep(1000)
		except: pass
	progressDialog.close()
	sleep(100)
	ok_dialog(text=32576)

def refresh_cached_data(meta):
	from caches.meta_cache import metacache
	media_type, tmdb_id, imdb_id = meta['mediatype'], meta['tmdb_id'], meta['imdb_id']
	try: metacache.delete(media_type, 'tmdb_id', tmdb_id, meta)
	except: return notification(32574)
	from apis.imdb_api import refresh_imdb_meta_data
	refresh_imdb_meta_data(imdb_id)
	notification(32576)
	kodi_refresh()

class BaseCache(object):
	def __init__(self, dbfile, table):
		self.dbfile = dbfile
		self.table = table
		self.time = datetime.now()
		self.timeout = 240

	def get(self, string):
		result = None
		try:
			current_time = self._get_timestamp(self.time)
			result = self.get_memory_cache(string, current_time)
			if result is None:
				dbcon = self.connect_database()
				dbcur = self.set_PRAGMAS(dbcon)
				dbcur.execute(BASE_GET % self.table, (string,))
				cache_data = dbcur.fetchone()
				if cache_data:
					if cache_data[0] > current_time:
						result = eval(cache_data[1])
						self.set_memory_cache(result, string, cache_data[1])
					else:
						self.delete(string, dbcon)
		except: pass
		return result

	def set(self, string, data, expiration=timedelta(days=30)):
		try:
			expires = self._get_timestamp(self.time + expiration)
			dbcon = self.connect_database()
			dbcur = self.set_PRAGMAS(dbcon)
			dbcur.execute(BASE_SET % self.table, (string, repr(data), int(expires)))
			self.set_memory_cache(data, string, int(expires))
		except: return None

	def get_memory_cache(self, string, current_time):
		result = None
		try:
			cachedata = get_property(string)
			if cachedata:
				cachedata = eval(cachedata)
				if cachedata[0] > current_time: result = cachedata[1]
		except: pass
		return result

	def set_memory_cache(self, data, string, expires):
		try:
			cachedata = (expires, data)
			cachedata_repr = repr(cachedata)
			set_property(string, cachedata_repr)
		except: pass

	def delete(self, string, dbcon=None):
		try:
			if not dbcon: self.connect_database()
			dbcur = dbcon.cursor()
			dbcur.execute(BASE_DELETE % self.table, (string,))
			self.delete_memory_cache(string)
		except: pass

	def delete_memory_cache(self, string):
		clear_property(string)

	def connect_database(self):
		return database.connect(self.dbfile, timeout=self.timeout, isolation_level=None)

	def set_PRAGMAS(self, dbcon):
		dbcur = dbcon.cursor()
		dbcur.execute('''PRAGMA synchronous = OFF''')
		dbcur.execute('''PRAGMA journal_mode = OFF''')
		return dbcur

	def _get_timestamp(self, date_time):
		return int(time.mktime(date_time.timetuple()))