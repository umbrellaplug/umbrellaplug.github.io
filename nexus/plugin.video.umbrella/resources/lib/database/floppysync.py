# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""
# Local cache DB for the Floppy service (dannyvfilms/Floppy fork).
# Floppy's data model is a single 'status' field per tracked item
# (Planning/In progress/Paused/Completed/Dropped) rather than Trakt's
# separate watchlist/collection/history, so this mirrors simklsync.py's
# 5-bucket status-list layout more than customtraktsync.py's shape,
# while reusing customtraktsync.py's cache/bookmark table patterns.

import re
import hashlib
from ast import literal_eval
from sqlite3 import dbapi2 as db
from datetime import datetime
from time import time
from resources.lib.modules.control import existsPath, dataPath, makeFile, floppySyncFile
from resources.lib.modules import cleandate

def get_connection(setRowFactory=False):
	if not existsPath(dataPath): makeFile(dataPath)
	dbcon = db.connect(floppySyncFile, timeout=60)
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


#Status-bucket tables (Watchlist/Watching/On Hold/Completed/Dropped/Collection) — generic list-cache shape

def fetch_status_list(table):
	result = []
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', (table,)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, tmdb TEXT, item_id TEXT, image TEXT, score TEXT, listed_at TEXT, UNIQUE(tmdb));''' % table)
			dbcur.connection.commit()
			return result
		match = dbcur.execute('''SELECT * FROM %s WHERE NOT title=""''' % table).fetchall()
		# imdb/tvdb/premiered/rating/votes aren't available from Floppy (tmdb-native,
		# unified status model) but are included as blanks for compatibility with the
		# generic worker()/movieDirectory() pipeline shared with the other providers.
		result = [{'title': i[0], 'year': i[1], 'premiered': '', 'imdb': '', 'tmdb': i[2], 'tvdb': '', 'item_id': i[3], 'image': i[4], 'rating': '', 'votes': '', 'score': i[5], 'added': i[6]} for i in match]
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass
	return result

def insert_status_list(items, table, new_sync=True):
	# items: list of Floppy MediaSerializer objects, i.e.
	# {'id': <item pk>, 'item': {'media_id','source','media_type','title','image',...}, 'status': int, 'score': float, ...}
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, tmdb TEXT, item_id TEXT, image TEXT, score TEXT, listed_at TEXT, UNIQUE(tmdb));''' % table)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
		if new_sync:
			dbcur.execute('''DELETE FROM %s''' % table)
			dbcur.connection.commit()
			dbcur.execute('''VACUUM''')
		for i in items:
			try:
				if not i: continue
				item = i.get('item') or {}
				tmdb = str(item.get('media_id') or '')
				if not tmdb: continue
				title = item.get('title', '')
				image = item.get('image', '') or ''
				score = str(i.get('score', '') or '')
				item_id = str(i.get('id', '') or '')
				listed_at = i.get('created_at', '') or ''
				dbcur.execute('''INSERT OR REPLACE INTO %s Values (?, ?, ?, ?, ?, ?, ?)''' % table, (title, '', tmdb, item_id, image, score, listed_at))
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_%s_sync_at' % table, timestamp))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def delete_floppy_tables(tables):
	# Delete and vacuum the specified Floppy tables, and reset their service timestamps.
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		if 'floppy_watched_movies' in tables or 'floppy_watched_episodes' in tables:
			# Drop the watched cursor first (and commit it): if we die mid-clear, the next sync takes a
			# fresh snapshot instead of applying a delta onto a half-emptied cache.
			dbcur.execute(_SYNC_STATE_DDL)
			dbcur.execute('''DELETE FROM floppy_sync_state WHERE key=?''', (_WATCHED_CURSOR,))
			dbcur.connection.commit()
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
		for key in ('last_history_at', 'last_watched_movies_at', 'last_watched_episodes_at'):
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


#Watched movies / episodes tables (aggregated client-side, mirrors customtraktsync.py's shape).
#Floppy is TMDB-native so imdb/tvdb columns are kept for cross-lookup convenience but tmdb is authoritative.

def _ensure_watched_tables(dbcur):
	dbcur.execute('''CREATE TABLE IF NOT EXISTS floppy_watched_movies (imdb TEXT, tmdb TEXT, title TEXT, year TEXT, last_watched_at TEXT, UNIQUE(tmdb));''')
	dbcur.execute('''CREATE TABLE IF NOT EXISTS floppy_watched_episodes (show_imdb TEXT, show_tmdb TEXT, show_tvdb TEXT, season INTEGER, episode INTEGER, last_watched_at TEXT, UNIQUE(show_tmdb, season, episode));''')
	dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')

def upsert_watched_movie(imdb='', tmdb='', title='', year='', last_watched_at=''):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_watched_tables(dbcur)
		dbcur.execute('''INSERT OR REPLACE INTO floppy_watched_movies Values (?, ?, ?, ?, ?)''', (imdb, str(tmdb), title, str(year), last_watched_at))
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
		dbcur.execute('''INSERT OR REPLACE INTO floppy_watched_episodes Values (?, ?, ?, ?, ?, ?)''', (show_imdb, str(show_tmdb), str(show_tvdb), int(season), int(episode), last_watched_at))
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
		dbcur.execute('''DELETE FROM floppy_watched_movies WHERE tmdb=?''', (str(tmdb),))
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
		dbcur.execute('''DELETE FROM floppy_watched_episodes WHERE show_tmdb=? AND season=? AND episode=?''', (str(show_tmdb), int(season), int(episode)))
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
		rows = dbcur.execute("SELECT imdb FROM floppy_watched_movies WHERE imdb != ''").fetchall()
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
	# Full rows (imdb, tmdb, title, year, last_watched_at) for the dedicated Watched
	# list — get_watched_movies() above only selects imdb for the indicator-matching
	# path and can't be reused for a real history-sorted list.
	result = []
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		_ensure_watched_tables(dbcur)
		rows = dbcur.execute('''SELECT imdb, tmdb, title, year, last_watched_at FROM floppy_watched_movies''').fetchall()
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
		rows = dbcur.execute('''SELECT show_imdb, show_tmdb, show_tvdb, season, episode FROM floppy_watched_episodes''').fetchall()
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
			FROM floppy_watched_episodes GROUP BY show_tmdb ORDER BY last_watched_at DESC''').fetchall()
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


#Transactional watched-cache primitives (fast sync).
#get_connection() runs with journal_mode=OFF, where ROLLBACK is undefined, so these use their own
#connection with journal_mode=DELETE / synchronous=NORMAL (same switch as scrobsync.store_watched_history()).
#Rows arrive already normalised as tuples: movies (imdb, tmdb, title, year, last_watched_at), episodes
#(show_imdb, show_tmdb, show_tvdb, season, episode, last_watched_at). No VACUUM and no modern-SQLite-only
#syntax (ON CONFLICT DO UPDATE / RETURNING / STRICT) so the oldest Kodi SQLite builds keep working.

_SYNC_STATE_DDL = '''CREATE TABLE IF NOT EXISTS floppy_sync_state (key TEXT PRIMARY KEY, value TEXT);'''
_WATCHED_CURSOR = 'watched_cursor'
_SYNC_CURSOR_KEYS = {'watched': _WATCHED_CURSOR}

def _tx_connection():
	# isolation_level=None: Python never opens an implicit transaction, so BEGIN IMMEDIATE below is ours alone.
	dbcon = get_connection()
	try:
		dbcon.isolation_level = None
		dbcon.execute('''PRAGMA journal_mode = DELETE''')
		dbcon.execute('''PRAGMA synchronous = NORMAL''')
		dbcur = dbcon.cursor()
		_ensure_watched_tables(dbcur)
		dbcur.execute(_SYNC_STATE_DDL)
		dbcur.close()
	except:
		dbcon.close()
		raise
	return dbcon

def _cursor_text(value):
	# Cursors are integers on the wire and TEXT in the state table; None means "no cursor".
	if value is None: return None
	if isinstance(value, (bool, float)): raise TypeError('invalid cursor: %r' % (value,))
	number = int(value)
	if number < 0: raise ValueError('invalid cursor: %r' % (value,))
	return str(number)

def _required_text(value):
	value = '' if value is None else str(value)
	if not value: raise ValueError('missing tmdb id')
	return value

def _movie_row(row):
	imdb, tmdb, title, year, last_watched_at = row
	return ('' if imdb is None else str(imdb), _required_text(tmdb), '' if title is None else title,
		'' if year is None else str(year), '' if last_watched_at is None else last_watched_at)

def _episode_row(row):
	show_imdb, show_tmdb, show_tvdb, season, episode, last_watched_at = row
	return ('' if show_imdb is None else str(show_imdb), _required_text(show_tmdb), '' if show_tvdb is None else str(show_tvdb),
		int(season), int(episode), '' if last_watched_at is None else last_watched_at)

def _change_op(op):
	kind, payload = op
	if kind == 'upsert_movie': return (kind, _movie_row(payload))
	if kind == 'upsert_episode': return (kind, _episode_row(payload))
	if kind == 'delete_movie': return (kind, _required_text(payload))
	if kind == 'delete_episode':
		show_tmdb, season, episode = payload
		return (kind, (_required_text(show_tmdb), int(season), int(episode)))
	raise ValueError('unknown change op: %r' % (kind,))

def _read_state(dbcur, key):
	row = dbcur.execute('''SELECT value FROM floppy_sync_state WHERE key=?''', (key,)).fetchone()
	return row[0] if row else None

def _write_state(dbcur, key, value):
	dbcur.execute('''INSERT OR REPLACE INTO floppy_sync_state VALUES (?, ?)''', (key, value))

def _mark_history_changed(dbcur):
	# Readers (playcount) only rebuild their indicator cache when last_history_at is newer than the cache row.
	timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
	dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_history_at', timestamp))
	if dbcur.execute('''SELECT 1 FROM sqlite_master WHERE type='table' AND name='watched';''').fetchone():
		dbcur.execute('''DELETE FROM watched''')

def _rollback(dbcon):
	try: dbcon.execute('''ROLLBACK''')
	except: pass

def get_sync_state(key, default=None):
	value = default
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		if dbcur.execute('''SELECT 1 FROM sqlite_master WHERE type='table' AND name='floppy_sync_state';''').fetchone():
			row = dbcur.execute('''SELECT value FROM floppy_sync_state WHERE key=?''', (key,)).fetchone()
			if row: value = row[0]
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass
	return value

def set_sync_state(key, value):
	# Raises on failure: callers (instance key, identity) need to know the value was not stored.
	dbcon = _tx_connection()
	try:
		_write_state(dbcon.cursor(), key, None if value is None else str(value))
	finally:
		dbcon.close()

def reset_sync_cursors(which=('watched',)):
	# Next sync must start from a fresh snapshot. Other state (instance key etc.) is kept.
	keys = [_SYNC_CURSOR_KEYS[name] for name in which]
	dbcon = _tx_connection()
	try:
		dbcur = dbcon.cursor()
		dbcon.execute('''BEGIN IMMEDIATE''')
		try:
			for key in keys: dbcur.execute('''DELETE FROM floppy_sync_state WHERE key=?''', (key,))
			dbcon.execute('''COMMIT''')
		except:
			_rollback(dbcon)
			raise
	finally:
		dbcon.close()

def replace_watched_snapshot(movies, episodes, cursor, expected_cursor=None):
	# Atomically replace both watched tables and the cursor with a complete snapshot.
	# expected_cursor is compared with the stored cursor inside the transaction (None = no stored cursor);
	# returns False, changing nothing, if it differs. Any other failure rolls back and re-raises.
	cursor_text = _cursor_text(cursor)
	if cursor_text is None: raise ValueError('snapshot needs a cursor')
	expected_text = _cursor_text(expected_cursor)
	new_movies = {}
	for row in movies:
		row = _movie_row(row)
		new_movies[row[1]] = row
	new_episodes = {}
	for row in episodes:
		row = _episode_row(row)
		new_episodes[(row[1], row[3], row[4])] = row
	dbcon = _tx_connection()
	try:
		dbcur = dbcon.cursor()
		dbcon.execute('''BEGIN IMMEDIATE''')
		try:
			if _read_state(dbcur, _WATCHED_CURSOR) != expected_text:
				dbcon.execute('''ROLLBACK''')
				return False
			old_movies = dict((r[1], r) for r in dbcur.execute('''SELECT imdb, tmdb, title, year, last_watched_at FROM floppy_watched_movies''').fetchall())
			old_episodes = dict(((r[1], r[3], r[4]), r) for r in dbcur.execute('''SELECT show_imdb, show_tmdb, show_tvdb, season, episode, last_watched_at FROM floppy_watched_episodes''').fetchall())
			# Carry a known imdb forward when the snapshot has none (Floppy is tmdb-native).
			movie_imdb = dict((k, r[0]) for k, r in old_movies.items() if r[0])
			show_imdb = dict((r[1], r[0]) for r in old_episodes.values() if r[0])
			for key, row in list(new_movies.items()):
				if not row[0] and key in movie_imdb: new_movies[key] = (movie_imdb[key],) + row[1:]
			for key, row in list(new_episodes.items()):
				if not row[0] and row[1] in show_imdb: new_episodes[key] = (show_imdb[row[1]],) + row[1:]
			changed = new_movies != old_movies or new_episodes != old_episodes
			if changed:
				dbcur.execute('''DELETE FROM floppy_watched_movies''')
				dbcur.execute('''DELETE FROM floppy_watched_episodes''')
				dbcur.executemany('''INSERT OR REPLACE INTO floppy_watched_movies Values (?, ?, ?, ?, ?)''', list(new_movies.values()))
				dbcur.executemany('''INSERT OR REPLACE INTO floppy_watched_episodes Values (?, ?, ?, ?, ?, ?)''', list(new_episodes.values()))
				_mark_history_changed(dbcur)
			_write_state(dbcur, _WATCHED_CURSOR, cursor_text)
			dbcon.execute('''COMMIT''')
			return True
		except:
			_rollback(dbcon)
			raise
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		raise
	finally:
		dbcon.close()

def apply_watched_changes(ops, from_cursor, to_cursor):
	# Atomically apply one ordered page of feed events and advance the cursor.
	# ops: [('upsert_movie', movie_row), ('upsert_episode', episode_row), ('delete_movie', tmdb),
	#       ('delete_episode', (show_tmdb, season, episode))] applied in the order given.
	# Returns the number of rows actually changed, or None (nothing changed) if the stored cursor is not
	# from_cursor. Any other failure rolls back the whole page and re-raises.
	from_text, to_text = _cursor_text(from_cursor), _cursor_text(to_cursor)
	if from_text is None or to_text is None: raise ValueError('delta needs from and to cursors')
	if int(to_text) < int(from_text): raise ValueError('cursor cannot move backwards')
	ops = [_change_op(op) for op in ops]
	dbcon = _tx_connection()
	try:
		dbcur = dbcon.cursor()
		dbcon.execute('''BEGIN IMMEDIATE''')
		try:
			if _read_state(dbcur, _WATCHED_CURSOR) != from_text:
				dbcon.execute('''ROLLBACK''')
				return None
			changed = 0
			for kind, payload in ops:
				if kind == 'upsert_movie':
					existing = dbcur.execute('''SELECT imdb, tmdb, title, year, last_watched_at FROM floppy_watched_movies WHERE tmdb=?''', (payload[1],)).fetchone()
					if not payload[0] and existing and existing[0]: payload = (existing[0],) + payload[1:]
					if existing != payload:
						dbcur.execute('''INSERT OR REPLACE INTO floppy_watched_movies Values (?, ?, ?, ?, ?)''', payload)
						changed += 1
				elif kind == 'upsert_episode':
					existing = dbcur.execute('''SELECT show_imdb, show_tmdb, show_tvdb, season, episode, last_watched_at FROM floppy_watched_episodes WHERE show_tmdb=? AND season=? AND episode=?''', (payload[1], payload[3], payload[4])).fetchone()
					if not payload[0]:
						known = existing[0] if existing and existing[0] else None
						if not known:
							row = dbcur.execute('''SELECT show_imdb FROM floppy_watched_episodes WHERE show_tmdb=? AND show_imdb != '' LIMIT 1''', (payload[1],)).fetchone()
							known = row[0] if row else ''
						payload = (known,) + payload[1:]
					if existing != payload:
						dbcur.execute('''INSERT OR REPLACE INTO floppy_watched_episodes Values (?, ?, ?, ?, ?, ?)''', payload)
						changed += 1
				elif kind == 'delete_movie':
					dbcur.execute('''DELETE FROM floppy_watched_movies WHERE tmdb=?''', (payload,))
					if dbcur.rowcount > 0: changed += dbcur.rowcount
				else:
					dbcur.execute('''DELETE FROM floppy_watched_episodes WHERE show_tmdb=? AND season=? AND episode=?''', payload)
					if dbcur.rowcount > 0: changed += dbcur.rowcount
			if changed: _mark_history_changed(dbcur)
			_write_state(dbcur, _WATCHED_CURSOR, to_text)
			dbcon.execute('''COMMIT''')
			return changed
		except:
			_rollback(dbcon)
			raise
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		raise
	finally:
		dbcon.close()


#Cache table (indicator/progress cache — same key/value/date shape used by mdbsync.py/customtraktsync.py)

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
	# delete_floppy_tables() also resets last_history_at/etc. to epoch as a side effect,
	# which would fight a just-written update_last_watched_at() call if reused for this.
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


#Bookmarks table (local resume points — Floppy's confirmed API has no queryable
#server-side "in progress playback" list, only start/pause/stop scrobble events, so
#this is populated purely from local scrobbleMovie/scrobbleEpisode calls).

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
	# Dedicated to just the bookmarks table — delete_floppy_tables() also resets
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
