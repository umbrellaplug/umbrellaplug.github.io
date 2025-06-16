# mdbsync.py
import os
import json
from sqlite3 import dbapi2 as db
from datetime import datetime
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
		dbcur.close() ; dbcon.close()
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
				if 'show' in i:
					item = i.get('show')
					try: premiered = item.get('first_aired', '').split('T')[0]
					except: premiered = ''
				else:
					item = i.get('movie')
					premiered = item.get('released', '') or ''
				title = item.get('title')
				year = item.get('year', '') or ''
				ids = item.get('ids')
				imdb = ids.get('imdb', '')
				tmdb = ids.get('tmdb', '')
				tvdb = ids.get('tvdb', '')
				mdblist = ids.get('mdblist', '')
				rating = item.get('rating', '')
				votes = item.get('votes', '')
				listed_at = i.get('listed_at', '')
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
		dbcur.close() ; dbcon.close()

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
		dbcur.close() ; dbcon.close()

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
		dbcur.close() ; dbcon.close()
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