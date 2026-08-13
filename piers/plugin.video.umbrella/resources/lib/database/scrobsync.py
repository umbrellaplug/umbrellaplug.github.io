# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""
# Local cache DB for the Scrob service (self-hosted, github.com/ellite/scrob).
# Unlike Floppy/Trakt/Simkl, Scrob has no watchlist/collection/status-bucket concept
# at all (its List/ListItem model is just arbitrary user-named lists with no
# canonical "watchlist" flag) — so this mirrors only the watched-movies/episodes +
# cache + bookmarks portion of floppysync.py, with no status-bucket tables.

import re
import hashlib
from ast import literal_eval
from sqlite3 import dbapi2 as db
from datetime import datetime
from time import time
from resources.lib.modules.control import existsPath, dataPath, makeFile, scrobSyncFile
from resources.lib.modules import cleandate

def get_connection(setRowFactory=False):
	if not existsPath(dataPath): makeFile(dataPath)
	dbcon = db.connect(scrobSyncFile, timeout=60)
	dbcon.execute('''PRAGMA page_size = 32768''')
	dbcon.execute('''PRAGMA journal_mode = OFF''')
	dbcon.execute('''PRAGMA synchronous = OFF''')
	dbcon.execute('''PRAGMA temp_store = memory''')
	dbcon.execute('''PRAGMA mmap_size = 30000000000''')
	if setRowFactory: dbcon.row_factory = _dict_factory
	return dbcon

def get_connection_cursor(dbcon):
	return dbcon.cursor()

def _dict_factory(cursor, row):
	d = {}
	for idx, col in enumerate(cursor.description): d[col[0]] = row[idx]
	return d


#Service key/value table (last-sync timestamps) — same shape used by every other provider's sync db.

def delete_scrob_tables(tables):
	# Delete and vacuum the specified Scrob tables, and reset their service timestamps.
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
		dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
		epoch = '1970-01-01T00:00:00.000Z'
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_history_at', epoch))
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

#User-created custom lists (List/ListItem) — full-overwrite local cache, mirroring floppysync.py's
#status-bucket shape, but keyed by list_id instead of one table per bucket since Scrob's lists are
#arbitrary and user-named rather than a fixed Watchlist/Watching/etc set. No activity/last-modified
#signal exists for this endpoint (unlike Trakt), so this is polled on scrob_syncInterval and always
#fully replaced rather than incrementally diffed.

def fetch_user_lists(media_type):
	result = []
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name='scrob_lists';''').fetchone()
		if not ck_table: return result
		match = dbcur.execute('''SELECT list_id, list_name, COUNT(*) FROM scrob_lists WHERE media_type=? GROUP BY list_id, list_name''', (media_type,)).fetchall()
		result = [{'id': i[0], 'name': i[1], 'item_count': i[2]} for i in match]
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass
	return result

def fetch_list_items(list_id, media_type):
	result = []
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name='scrob_lists';''').fetchone()
		if not ck_table: return result
		match = dbcur.execute('''SELECT title, year, tmdb, item_id, listed_at FROM scrob_lists WHERE list_id=? AND media_type=?''', (str(list_id), media_type)).fetchall()
		result = [{'title': i[0], 'year': i[1], 'tmdb': i[2], 'item_id': i[3], 'listed_at': i[4]} for i in match]
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass
	return result

def insert_user_lists(rows):
	# rows: [{'list_id','list_name','item_id','tmdb','title','year','media_type','listed_at'}, ...]
	# Always a full replace — see module-level comment above for why (no activity signal to diff against).
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS scrob_lists (list_id TEXT, list_name TEXT, item_id TEXT, tmdb TEXT, title TEXT, year TEXT, media_type TEXT, listed_at TEXT, UNIQUE(list_id, tmdb, media_type));''')
		dbcur.execute('''DELETE FROM scrob_lists''')
		dbcur.connection.commit()
		for r in rows:
			try:
				dbcur.execute('''INSERT OR REPLACE INTO scrob_lists Values (?, ?, ?, ?, ?, ?, ?, ?)''',
					(r['list_id'], r['list_name'], r['item_id'], r['tmdb'], r['title'], r['year'], r['media_type'], r['listed_at']))
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_lists_sync_at', timestamp))
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

def update_last_watched_at(key='last_history_at'):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
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


#Watched movies / episodes tables (aggregated client-side, mirrors floppysync.py's shape).
#Scrob is TMDB-native so imdb/tvdb columns are kept for cross-lookup convenience but tmdb is authoritative.

def _ensure_watched_tables(dbcur):
	dbcur.execute('''CREATE TABLE IF NOT EXISTS scrob_watched_movies (imdb TEXT, tmdb TEXT, title TEXT, year TEXT, last_watched_at TEXT, UNIQUE(tmdb));''')
	dbcur.execute('''CREATE TABLE IF NOT EXISTS scrob_watched_episodes (show_imdb TEXT, show_tmdb TEXT, show_tvdb TEXT, season INTEGER, episode INTEGER, last_watched_at TEXT, UNIQUE(show_tmdb, season, episode));''')
	dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')

def upsert_watched_movie(imdb='', tmdb='', title='', year='', last_watched_at=''):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_watched_tables(dbcur)
		dbcur.execute('''INSERT OR REPLACE INTO scrob_watched_movies Values (?, ?, ?, ?, ?)''', (imdb, str(tmdb), title, str(year), last_watched_at))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def upsert_watched_episode(show_imdb='', show_tmdb='', show_tvdb='', season=0, episode=0, last_watched_at=''):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_watched_tables(dbcur)
		dbcur.execute('''INSERT OR REPLACE INTO scrob_watched_episodes Values (?, ?, ?, ?, ?, ?)''', (show_imdb, str(show_tmdb), str(show_tvdb), int(season), int(episode), last_watched_at))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def bulk_upsert_watched_movies(rows):
	# rows: list of (imdb, tmdb, title, year, last_watched_at) tuples. A full sync can
	# involve thousands of rows — upsert_watched_movie() above opens and closes a
	# fresh sqlite connection per call, which is fine for one-off writes but is the
	# actual bottleneck on a full resync (confirmed: on a resource-constrained device,
	# ~14,000 individual connection cycles for a large watched-episode history caused
	# the sync to never finish). Batch the whole set into one connection/transaction.
	if not rows: return
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_watched_tables(dbcur)
		dbcur.executemany('''INSERT OR REPLACE INTO scrob_watched_movies Values (?, ?, ?, ?, ?)''', rows)
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def bulk_upsert_watched_episodes(rows):
	# rows: list of (show_imdb, show_tmdb, show_tvdb, season, episode, last_watched_at)
	# tuples. Same rationale as bulk_upsert_watched_movies() above.
	if not rows: return
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_watched_tables(dbcur)
		dbcur.executemany('''INSERT OR REPLACE INTO scrob_watched_episodes Values (?, ?, ?, ?, ?, ?)''', rows)
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def delete_watched_movie(tmdb):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_watched_tables(dbcur)
		dbcur.execute('''DELETE FROM scrob_watched_movies WHERE tmdb=?''', (str(tmdb),))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def delete_watched_episode(show_tmdb, season, episode):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_watched_tables(dbcur)
		dbcur.execute('''DELETE FROM scrob_watched_episodes WHERE show_tmdb=? AND season=? AND episode=?''', (str(show_tmdb), int(season), int(episode)))
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
		# getMovieOverlay() (playcount.py) matches this list against a real imdb id, not
		# tmdb, so this must select imdb — even though tmdb is the table's unique key.
		rows = dbcur.execute("SELECT imdb FROM scrob_watched_movies WHERE imdb != ''").fetchall()
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

def get_watched_movies_full():
	result = []
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_watched_tables(dbcur)
		rows = dbcur.execute("SELECT imdb, tmdb, title, year, last_watched_at FROM scrob_watched_movies WHERE NOT imdb='' ORDER BY last_watched_at DESC").fetchall()
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

def get_watched_episodes():
	result = []
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_watched_tables(dbcur)
		rows = dbcur.execute('''SELECT show_imdb, show_tmdb, show_tvdb, season, episode FROM scrob_watched_episodes''').fetchall()
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

def get_watched_shows():
	result = []
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_watched_tables(dbcur)
		rows = dbcur.execute('''SELECT show_imdb, show_tmdb, show_tvdb, MAX(last_watched_at) AS last_watched_at
			FROM scrob_watched_episodes GROUP BY show_tmdb ORDER BY last_watched_at DESC''').fetchall()
		result = [(r[0], r[1], r[2], r[3]) for r in rows]
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass
	return result


#Cache table (indicator/progress cache — same key/value/date shape used by every other provider's sync db)

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

def clear_cache():
	# Truncates the whole cache table without touching the service-timestamp table —
	# delete_scrob_tables() also resets last_history_at to epoch as a side effect, which
	# would fight a just-written update_last_watched_at() call if reused for this.
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name='watched';''').fetchone()
		if ck:
			dbcur.execute('''DELETE FROM watched''')
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


#Bookmarks table (local resume points — Scrob has no queryable server-side "in
#progress playback" list either, only start/pause/stop scrobble events, so this is
#populated purely from local scrobbleMovie/scrobbleEpisode calls, same as Floppy).

def _ensure_bookmarks_table(dbcur):
	dbcur.execute('''CREATE TABLE IF NOT EXISTS bookmarks (tvshowtitle TEXT, title TEXT, resume_id TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, season TEXT, episode TEXT, genre TEXT, mpaa TEXT, studio TEXT, duration TEXT, percent_played TEXT, paused_at TEXT, UNIQUE(imdb, tmdb, tvdb, season, episode));''')
	dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')

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
					match = dbcur.execute('''SELECT * FROM bookmarks WHERE (tmdb=? AND NOT tmdb='')''', (tmdb,)).fetchone()
					if ret_type == 'resume_info': progress = (match[1], match[2])
					else: progress = match[12]
				except: pass
			else:
				try:
					match = dbcur.execute('''SELECT * FROM bookmarks WHERE (tmdb=? AND season=? AND episode=? AND NOT tmdb='')''', (tmdb, str(season), str(episode))).fetchone()
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

def delete_bookmark(imdb, tvdb='', tmdb='', season='', episode=''):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_bookmarks_table(dbcur)
		dbcur.execute('''DELETE FROM bookmarks WHERE (tmdb=? AND season=? AND episode=?)''', (tmdb, str(season) if season else '', str(episode) if episode else ''))
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
	# Dedicated to just the bookmarks table — delete_scrob_tables() also resets
	# last_history_at as a side effect, which is unrelated here and would wrongly make
	# the watched-history sync think it needs a full resync.
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
