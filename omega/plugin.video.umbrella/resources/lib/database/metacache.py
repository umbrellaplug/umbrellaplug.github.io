# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from time import time
from sqlite3 import dbapi2 as db
from resources.lib.modules.control import existsPath, dataPath, makeFile, metacacheFile


def fetch(items, lang='en', user=''):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name='meta';''').fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS meta (imdb TEXT, tmdb TEXT, tvdb TEXT, lang TEXT, user TEXT, item TEXT, time TEXT,
			UNIQUE(imdb, tmdb, tvdb, lang, user));''')
			dbcur.connection.commit()
			dbcur.close() ; dbcon.close()
			return items
		t2 = int(time())
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	for i in range(0, len(items)):
		try:
			try: # First lookup by TVDb and IMDb, since there are some incorrect shows on Trakt that have the same IMDb ID, but different TVDb IDs (eg: Gotham, Supergirl).
				match = dbcur.execute('''SELECT * FROM meta WHERE (imdb=? AND tvdb=? AND lang=? AND user=? AND NOT imdb='' AND NOT tvdb='')''',
					(items[i].get('imdb', ''), items[i].get('tvdb', ''), lang, user)).fetchone()
				t1 = int(match[6])
			except:
				try: # Lookup both IMDb and TMDb for more accurate match.
					match = dbcur.execute('''SELECT * FROM meta WHERE (imdb=? AND tmdb=? AND lang=? AND user=? AND not imdb='' AND NOT tmdb='')''',
						(items[i].get('imdb', ''), items[i].get('tmdb', ''), lang, user)).fetchone()
					t1 = int(match[6])
				except:
					try: # Last resort single ID lookup.
						match = dbcur.execute('''SELECT * FROM meta WHERE (imdb=? AND lang=? AND user=? AND NOT imdb='') OR (tmdb=? AND lang=? AND user=? AND NOT tmdb='') OR (tvdb=? AND lang=? AND user=? AND NOT tvdb='')''',
							(items[i].get('imdb', ''), lang, user, items[i].get('tmdb', ''), lang, user, items[i].get('tvdb', ''), lang, user)).fetchone()
						t1 = int(match[6])
					except: pass
			if match:
				update = (abs(t2 - t1) / 3600) >= 720 # 30 days? for airing shows this is to much.
				if update: continue
				item = eval(match[5])

				if item['mediatype'] == 'tvshow':
					status = item['status'].lower()
					if not any(value in status for value in ('ended', 'canceled')):
						from resources.lib.modules.cleandate import timestamp_from_string
						next_episode_to_air = timestamp_from_string(item.get('next_episode_to_air', {}).get('air_date', ''))
						if not next_episode_to_air:
							update = (abs(t2 - t1) / 3600) >= 168 # 7 days for returning shows with None for next_episode_to_air
							if update: continue
						else:
							if next_episode_to_air+(18*3600) <= t2 and (abs(t2 - t1) / 3600) >= 1: # refresh meta when next_episode_to_air is less than or equal to system date, every 1hr starting at 6pm till it flips
								from resources.lib.database.traktsync import cache_existing
								from resources.lib.modules.trakt import syncTVShows
								imdb = item.get('imdb', '')
								indicators = cache_existing(syncTVShows)
								watching = [i[0] for i in indicators if i[0] == imdb]
								if watching:
									from resources.lib.modules.trakt import cachesyncSeasons
									cachesyncSeasons(imdb) # refreshes only shows you are "watching"
								continue
				item = dict((k, v) for k, v in iter(item.items()) if v is not None and v != '')
				items[i].update(item)
				items[i].update({'metacache': True})
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
	try: dbcur.close() ; dbcon.close()
	except: pass
	return items

def insert(meta):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS meta (imdb TEXT, tmdb TEXT, tvdb TEXT, lang TEXT, user TEXT, item TEXT, time TEXT,
		UNIQUE(imdb, tmdb, tvdb, lang, user));''')
		t = int(time())
		for m in meta:
			if "user" not in m: m["user"] = ''
			if "lang" not in m: m["lang"] = 'en'
			i = repr(m['item'])
			try: dbcur.execute('''INSERT OR REPLACE INTO meta Values (?, ?, ?, ?, ?, ?, ?)''', (m.get('imdb', ''), m.get('tmdb', ''), m.get('tvdb', ''), m['lang'], m['user'], i, t))
			except: pass
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def cache_clear_meta():
	cleared = False
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''DROP TABLE IF EXISTS meta''')
		dbcur.execute('''VACUUM''')
		dbcur.connection.commit()
		cleared = True
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		cleared = False
	finally:
		dbcur.close() ; dbcon.close()
	return cleared

def get_connection():
	if not existsPath(dataPath): makeFile(dataPath)
	dbcon = db.connect(metacacheFile, timeout=60) # added timeout 3/23/21 for concurrency with threads
	dbcon.execute('''PRAGMA page_size = 32768''')
	dbcon.execute('''PRAGMA journal_mode = OFF''')
	dbcon.execute('''PRAGMA synchronous = OFF''')
	dbcon.execute('''PRAGMA temp_store = memory''')
	dbcon.execute('''PRAGMA mmap_size = 30000000000''')
	# dbcon.row_factory = _dict_factory # not needed for metacache
	return dbcon

def get_connection_cursor(dbcon):
	dbcur = dbcon.cursor()
	return dbcur