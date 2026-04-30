# mdbsync.py
import os
import json
import hashlib
import re
from ast import literal_eval
from sqlite3 import dbapi2 as db
from datetime import datetime
from time import time
from resources.lib.modules.control import existsPath, dataPath, makeFile, mdbSyncFile, setting as getSetting
from resources.lib.modules import cleandate

def fetch_watch_list(table):
	list = ''
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', (table,)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, mdblist TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, UNIQUE(imdb, tmdb, tvdb, mdblist));''' % table)
			dbcur.connection.commit()
			return list
		try:
			match = dbcur.execute('''SELECT * FROM %s WHERE NOT title=""''' % table).fetchall()
			list = [{'title': i[0], 'year': i[1], 'premiered': i[2], 'imdb': i[3], 'tmdb': i[4], 'tvdb': i[5], 'mdblist': i[6], 'rating': i[7], 'votes': i[8], 'added': i[9]} for i in match]
		except: pass
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass
	return list

def insert_watch_list(items, table, new_sync=True):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, mdblist TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, UNIQUE(imdb, tmdb, tvdb, mdblist));''' % table)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
		if new_sync:
			dbcur.execute('''DELETE FROM %s''' % table)
			dbcur.connection.commit() # added this for what looks like a 19 bug not found in 18, normal commit is at end
			dbcur.execute('''VACUUM''')
		for i in items:
			try:
				if i is None: continue
				if 'show' in i or 'movie' in i:
					# Trakt-nested format: {'show': {'title': ..., 'ids': {...}}} / {'movie': ...}
					if 'show' in i:
						item = i.get('show', {})
						try: premiered = item.get('first_aired', '').split('T')[0]
						except: premiered = ''
					else:
						item = i.get('movie', {})
						premiered = item.get('released', '') or ''
					title = item.get('title')
					year = item.get('year', '') or ''
					ids = item.get('ids') or {}
					imdb = ids.get('imdb', '')
					tmdb = ids.get('tmdb', '')
					tvdb = ids.get('tvdb', '')
					mdblist = ids.get('mdblist', '')
					rating = item.get('rating', '')
					votes = item.get('votes', '')
					listed_at = i.get('listed_at', '')
				else:
					# Flat MDBList format: {'imdb': ..., 'title': ..., 'release_year': ..., 'added': ...}
					title = i.get('title', '')
					year = str(i.get('release_year', '') or '')
					premiered = ''
					imdb = i.get('imdb', '')
					tmdb = str(i.get('tmdb', '') or '')
					tvdb = str(i.get('tvdb', '') or '')
					mdblist = str(i.get('id', '') or '')
					rating = i.get('rating', '')
					votes = i.get('votes', '')
					listed_at = i.get('added', '')
				dbcur.execute('''INSERT OR REPLACE INTO %s Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''' % table, (title, year, premiered, imdb, tmdb, tvdb, mdblist, rating, votes, listed_at))
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_watchlisted_at', timestamp))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def delete_watchList_items(items, table, col_name='mdblist'):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', (table,)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, mdblist TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, UNIQUE(imdb, tmdb, tvdb, mdblist));''' % table)
			dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
			dbcur.connection.commit()
			return
		for item in items:
			try:
				dbcur.execute('''DELETE FROM %s WHERE %s=?;''' % (table, col_name), (item,))
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_watchlisted_at', timestamp))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def delete_mdb_tables(tables):
	#Delete and vacuum the specified MDBList tables, and reset their service timestamps.
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		for table in tables:
			try:
				ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', (table,)).fetchone()
				if ck_table:
					dbcur.execute('DELETE FROM %s' % table)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		# Reset service timestamps so next sync is treated as first-run
		epoch = '1970-01-01T00:00:00.000Z'
		for key in ('last_watched_at', 'last_watched_movies_at', 'last_watched_episodes_at', 'last_watchlisted_at'):
			dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', (key, epoch))
		dbcur.connection.commit()
		dbcur.execute('''VACUUM''')
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def last_sync(type):
	last_sync_at = 0
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name='service';''').fetchone()
		if ck_table:
			match = dbcur.execute('''SELECT * FROM service WHERE setting=?;''', (type,)).fetchone()
			if match: last_sync_at = int(cleandate.iso_2_utc(match[1]))
			else: dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', (type, '1970-01-01T20:00:00.000Z'))
		else: dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass
	return last_sync_at

def get_connection(setRowFactory=False):
	if not existsPath(dataPath): makeFile(dataPath)
	dbcon = db.connect(mdbSyncFile, timeout=60) # added timeout 3/23/21 for concurrency with threads
	dbcon.execute('''PRAGMA page_size = 32768''')
	dbcon.execute('''PRAGMA journal_mode = OFF''')
	dbcon.execute('''PRAGMA synchronous = OFF''')
	dbcon.execute('''PRAGMA temp_store = memory''')
	dbcon.execute('''PRAGMA mmap_size = 30000000000''')
	if setRowFactory: dbcon.row_factory = _dict_factory
	return dbcon

def get_connection_cursor(dbcon):
	dbcur = dbcon.cursor()
	return dbcur

def _dict_factory(cursor, row):
	d = {}
	for idx, col in enumerate(cursor.description): d[col[0]] = row[idx]
	return d

#Watched movies table

def _ensure_watched_tables(dbcur):
	dbcur.execute('''CREATE TABLE IF NOT EXISTS mdb_watched_movies (imdb TEXT, tmdb TEXT, title TEXT, year TEXT, last_watched_at TEXT, UNIQUE(imdb));''')
	dbcur.execute('''CREATE TABLE IF NOT EXISTS mdb_watched_episodes (show_imdb TEXT, show_tmdb TEXT, show_tvdb TEXT, season INTEGER, episode INTEGER, last_watched_at TEXT, UNIQUE(show_imdb, season, episode));''')
	dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')

def upsert_watched_movie(imdb, tmdb='', title='', year='', last_watched_at=''):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_watched_tables(dbcur)
		dbcur.execute('''INSERT OR REPLACE INTO mdb_watched_movies Values (?, ?, ?, ?, ?)''', (imdb, str(tmdb), title, str(year), last_watched_at))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def upsert_watched_episode(show_imdb, show_tmdb='', show_tvdb='', season=0, episode=0, last_watched_at=''):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_watched_tables(dbcur)
		dbcur.execute('''INSERT OR REPLACE INTO mdb_watched_episodes Values (?, ?, ?, ?, ?, ?)''', (show_imdb, str(show_tmdb), str(show_tvdb), int(season), int(episode), last_watched_at))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def delete_watched_movie(imdb):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_watched_tables(dbcur)
		dbcur.execute('''DELETE FROM mdb_watched_movies WHERE imdb=?''', (imdb,))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def delete_watched_episode(show_imdb, season, episode):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_watched_tables(dbcur)
		dbcur.execute('''DELETE FROM mdb_watched_episodes WHERE show_imdb=? AND season=? AND episode=?''', (show_imdb, int(season), int(episode)))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def get_watched_movies():
	result = []
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_watched_tables(dbcur)
		rows = dbcur.execute("SELECT imdb FROM mdb_watched_movies WHERE imdb != ''").fetchall()
		result = [r[0] for r in rows]
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass
	return result

def get_watched_episodes():
	result = []
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_watched_tables(dbcur)
		rows = dbcur.execute('''SELECT show_imdb, show_tmdb, show_tvdb, season, episode FROM mdb_watched_episodes''').fetchall()
		result = [(r[0], r[1], r[2], r[3], r[4]) for r in rows]
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass
	return result

def update_last_watched_at(key='last_watched_at'):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_watched_tables(dbcur)
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', (key, timestamp))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

#Cache table (watched indicators cache)

def _hash_function(function_instance, args=()):
	name = re.sub(r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', repr(function_instance))
	md5 = hashlib.md5(repr(args).encode('utf-8')).hexdigest()
	return name + md5

def cache_get(key):
	try:
		dbcon = get_connection(setRowFactory=True)
		dbcur = get_connection_cursor(dbcon)
		ck = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name='watched';''').fetchone()
		if not ck: return None
		return dbcur.execute('''SELECT * FROM watched WHERE key=?''', (key,)).fetchone()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return None
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def cache_insert(key, value):
	try:
		dbcon = get_connection(setRowFactory=True)
		dbcur = get_connection_cursor(dbcon)
		now = int(time())
		dbcur.execute('''CREATE TABLE IF NOT EXISTS watched (key TEXT, value TEXT, date INTEGER, UNIQUE(key));''')
		dbcur.execute('''INSERT OR REPLACE INTO watched Values (?, ?, ?)''', (key, value, now))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def cache_delete(key):
	try:
		dbcon = get_connection(setRowFactory=True)
		dbcur = get_connection_cursor(dbcon)
		ck = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name='watched';''').fetchone()
		if ck:
			dbcur.execute('''DELETE FROM watched WHERE key=?''', (key,))
			dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def cache_existing(function, *args):
	try:
		result = cache_get(_hash_function(function, args))
		if result: return literal_eval(result['value'])
		return None
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return None

def get(function, duration, *args):
	#Returns cached value if still valid (within duration minutes), else calls function fresh.
	try:
		key = _hash_function(function, args)
		cache_result = cache_get(key)
		if cache_result and duration != 0:
			if int(time()) - cache_result['date'] < (duration * 60):
				return literal_eval(cache_result['value'])
		fresh_result = repr(function(*args))
		if fresh_result and fresh_result not in ('None', "''", '[]', '{}'):
			cache_insert(key, fresh_result)
		return literal_eval(fresh_result) if fresh_result else None
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return None

def timeout(function, *args, returnNone=False):
	#Returns the Unix timestamp when the function cache was last written, or 0/None if not cached.
	try:
		key = _hash_function(function, args)
		cache_result = cache_get(key)
		if cache_result: return cache_result['date']
		if returnNone: return None
		return 0
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return 0

#Bookmarks table (local resume points)

def _ensure_bookmarks_table(dbcur):
	dbcur.execute('''CREATE TABLE IF NOT EXISTS bookmarks (tvshowtitle TEXT, title TEXT, resume_id TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, season TEXT, episode TEXT, genre TEXT, mpaa TEXT, studio TEXT, duration TEXT, percent_played TEXT, paused_at TEXT, UNIQUE(resume_id, imdb, tmdb, tvdb, season, episode));''')
	dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')

def fetch_bookmarks(imdb, tmdb='', tvdb='', season=None, episode=None, ret_all=None, ret_type='movies'):
	progress = '0'
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_bookmarks_table(dbcur)
		dbcur.connection.commit()
		if ret_all:
			if ret_type == 'movies':
				match = dbcur.execute('''SELECT * FROM bookmarks WHERE (tvshowtitle='')''').fetchall()
				progress = [{'title': i[1], 'resume_id': i[2], 'imdb': i[3], 'tmdb': i[4], 'duration': int(i[11]) if i[11] else 0, 'progress': i[12], 'paused_at': i[13]} for i in match]
			else:
				match = dbcur.execute('''SELECT * FROM bookmarks WHERE NOT (tvshowtitle='')''').fetchall()
				progress = [{'tvshowtitle': i[0], 'title': i[1], 'resume_id': i[2], 'imdb': i[3], 'tmdb': i[4], 'tvdb': i[5], 'season': int(i[6]) if i[6] else 0, 'episode': int(i[7]) if i[7] else 0,
								'genre': i[8], 'mpaa': i[9], 'studio': i[10], 'duration': int(i[11]) if i[11] else 0, 'progress': i[12], 'paused_at': i[13]} for i in match]
		else:
			if not episode:
				try:
					match = dbcur.execute('''SELECT * FROM bookmarks WHERE (imdb=? AND tmdb=? AND NOT imdb='' AND NOT tmdb='')''', (imdb, tmdb)).fetchone()
					if ret_type == 'resume_info': progress = (match[1], match[2])
					else: progress = match[12]
				except:
					try:
						match = dbcur.execute('''SELECT * FROM bookmarks WHERE (imdb=? AND NOT imdb='')''', (imdb,)).fetchone()
						if ret_type == 'resume_info': progress = (match[1], match[2])
						else: progress = match[12]
					except: pass
			else:
				try:
					match = dbcur.execute('''SELECT * FROM bookmarks WHERE (imdb=? AND tvdb=? AND season=? AND episode=? AND NOT imdb='' AND NOT tvdb='')''', (imdb, tvdb, season, episode)).fetchone()
					if ret_type == 'resume_info': progress = (match[0], match[2])
					else: progress = match[12]
				except:
					try:
						match = dbcur.execute('''SELECT * FROM bookmarks WHERE (tvdb=? AND season=? AND episode=? AND NOT tvdb='')''', (tvdb, season, episode)).fetchone()
						if ret_type == 'resume_info': progress = (match[0], match[2])
						else: progress = match[12]
					except: pass
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass
	return progress

def upsert_bookmark(tvshowtitle='', title='', resume_id='', imdb='', tmdb='', tvdb='', season='', episode='', genre='', mpaa='', studio='', duration='', percent_played='', paused_at=''):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_bookmarks_table(dbcur)
		if not resume_id:
			import hashlib as _hl
			resume_id = _hl.md5(('%s%s%s%s' % (imdb, tvdb, season, episode)).encode('utf-8')).hexdigest()
		dbcur.execute('''INSERT OR REPLACE INTO bookmarks Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
			(tvshowtitle, title, resume_id, imdb, tmdb, tvdb, season, episode, genre, mpaa, studio, duration, percent_played, paused_at))
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_paused_at', timestamp))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def clear_bookmarks():
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_bookmarks_table(dbcur)
		dbcur.execute('''DELETE FROM bookmarks''')
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def delete_bookmark(imdb, tvdb='', season='', episode=''):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_bookmarks_table(dbcur)
		dbcur.execute('''DELETE FROM bookmarks WHERE (imdb=? AND tvdb=? AND season=? AND episode=?)''', (imdb, tvdb, str(season) if season else '', str(episode) if episode else ''))
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_paused_at', timestamp))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def delete_bookmarks_for_season(imdb, tvdb='', season=''):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_bookmarks_table(dbcur)
		dbcur.execute('''DELETE FROM bookmarks WHERE imdb=? AND tvdb=? AND season=?''', (imdb, tvdb, str(season) if season else ''))
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_paused_at', timestamp))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass