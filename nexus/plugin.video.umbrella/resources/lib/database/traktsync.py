# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from ast import literal_eval
from hashlib import md5
from re import sub as re_sub
from time import time

from datetime import datetime
from sqlite3 import dbapi2 as db
from resources.lib.modules import cleandate
from resources.lib.modules.control import existsPath, dataPath, makeFile, traktSyncFile, setting as getSetting


def fetch_bookmarks(imdb, tmdb='', tvdb='', season=None, episode=None, ret_all=None, ret_type='movies'):
	progress = '0'
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name='bookmarks';''').fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS bookmarks (tvshowtitle TEXT, title TEXT, resume_id TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, season TEXT, episode TEXT, genre TEXT, mpaa TEXT, 
									studio TEXT, duration TEXT, percent_played TEXT, paused_at TEXT, UNIQUE(resume_id, imdb, tmdb, tvdb, season, episode));''')
			dbcur.connection.commit()
			return progress
		if ret_all:
			if ret_type == 'movies':
				match = dbcur.execute('''SELECT * FROM bookmarks WHERE (tvshowtitle='')''').fetchall()
				progress = [{'title': i[1], 'resume_id': i[2], 'imdb': i[3], 'tmdb': i[4], 'duration': int(i[11]), 'progress': i[12], 'paused_at': i[13]} for i in match]
			else:
				match = dbcur.execute('''SELECT * FROM bookmarks WHERE NOT (tvshowtitle='')''').fetchall()
				progress = [{'tvshowtitle': i[0], 'title': i[1], 'resume_id': i[2], 'imdb': i[3], 'tmdb': i[4], 'tvdb': i[5], 'season': int(i[6]), 'episode': int(i[7]), 'genre': i[8], 'mpaa': i[9],
									'studio': i[10], 'duration': int(i[11]), 'progress': i[12], 'paused_at': i[13]} for i in match]
		else:
			if not episode:
				try: # Lookup both IMDb and TMDb first for more accurate movie match.
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
				try: # Lookup both IMDb and TVDb first for more accurate episode match.
					match = dbcur.execute('''SELECT * FROM bookmarks WHERE (imdb=? AND tvdb=? AND season=? AND episode=? AND NOT imdb='' AND NOT tvdb='')''', (imdb, tvdb, season, episode)).fetchone()
					if ret_type == 'resume_info': 
						progress = (match[0], match[2])
						log_utils.log('Getting resume from database imdb. Match: %s' % (str(match)),1)
					else: progress = match[12]
				except:
					try:
						match = dbcur.execute('''SELECT * FROM bookmarks WHERE (tvdb=? AND season=? AND episode=? AND NOT tvdb='')''', (tvdb, season, episode)).fetchone()
						if ret_type == 'resume_info': 
							progress = (match[0], match[2])
							log_utils.log('Getting resume from database tvdb. Match: %s' % (str(match)),1)
						else: progress = match[12]
					except: pass
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()
	return progress

def insert_bookmarks(items, new_scrobble=False):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS bookmarks (tvshowtitle TEXT, title TEXT, resume_id TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, season TEXT, episode TEXT, genre TEXT, mpaa TEXT, 
								studio TEXT, duration TEXT, percent_played TEXT, paused_at TEXT, UNIQUE(resume_id, imdb, tmdb, tvdb, season, episode));''')
		dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
		if not new_scrobble:
			dbcur.execute('''DELETE FROM bookmarks''') # this just wipes the data but if table is corrupt this won't allow write to work
			dbcur.connection.commit() # added this for what looks like a 19 bug not found in 18, normal commit is at end
			dbcur.execute('''VACUUM''')
		for i in items:
			tvshowtitle, tvdb, season, episode = '', '', '', ''
			if i.get('type') == 'episode':
				ids = i.get('show').get('ids')
				tvshowtitle, title, imdb, tmdb, tvdb, season, episode, mpaa, studio, duration = i.get('show').get('title'), i.get('episode').get('title'), str(ids.get('imdb', '')), str(ids.get('tmdb', '')), str(ids.get('tvdb', '')), \
				str(i.get('episode').get('season')), str(i.get('episode').get('number')), i.get('show').get('certification') or 'NR', i.get('show').get('network'), i.get('show').get('runtime')
				try: genre = ' / '.join([x.title() for x in i.get('show', {}).get('genres')]) or 'NA'
				except: genre = 'NA'
			else:
				ids = i.get('movie').get('ids')
				title, imdb, tmdb, mpaa, studio, duration = i.get('movie').get('title'), str(ids.get('imdb', '')), str(ids.get('tmdb', '')), i.get('movie').get('certification') or 'NR', '', i.get('movie').get('runtime')
				try: genre = ' / '.join([x.title() for x in i.get('movie', {}).get('genres')]) or 'NA'
				except: genre = 'NA'
			dbcur.execute('''INSERT OR REPLACE INTO bookmarks Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (tvshowtitle, title, i.get('id', ''), imdb, tmdb, tvdb, season, episode, genre, mpaa, studio, duration, i.get('progress', ''), i.get('paused_at', '')))
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_paused_at', timestamp))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def delete_bookmark(items):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name='bookmarks';''').fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS bookmarks (tvshowtitle TEXT, title TEXT, resume_id TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, season TEXT, episode TEXT, genre TEXT, mpaa TEXT, 
									studio TEXT, duration TEXT, percent_played TEXT, paused_at TEXT, UNIQUE(resume_id, imdb, tmdb, tvdb, season, episode));''')
			dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
			dbcur.connection.commit()
			return
		for i in items:
			if i.get('type') == 'episode':
				ids = i.get('show').get('ids')
				imdb, tvdb, season, episode, = str(ids.get('imdb', '')), str(ids.get('tvdb', '')), str(i.get('episode').get('season')), str(i.get('episode').get('number'))
			else:
				tvdb, season, episode = '', '', ''
				ids = i.get('movie').get('ids')
				imdb = str(ids.get('imdb', ''))
			try:
				dbcur.execute('''DELETE FROM bookmarks WHERE (imdb=? AND tvdb=? AND season=? AND episode=?)''', (imdb, tvdb, season, episode))
				dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_paused_at', i.get('paused_at', '')))
				dbcur.connection.commit()
			except: pass
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def fetch_liked_list(trakt_id, ret_all=False):
	liked_list = ''
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name='liked_lists';''').fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS liked_lists (list_owner TEXT, list_owner_slug TEXT, list_name TEXT, trakt_id TEXT, content_type TEXT, item_count INTEGER, likes INTEGER, UNIQUE(trakt_id));''')
			dbcur.connection.commit()
			return liked_list
		if ret_all:
			try:
				match = dbcur.execute('''SELECT * FROM liked_lists WHERE NOT trakt_id=""''').fetchall()
				liked_list = [{'list_owner': i[0], 'list_owner_slug': i[1], 'list_name': i[2], 'trakt_id': i[3], 'content_type': i[4], 'item_count': i[5], 'likes': i[6]} for i in match]
			except: pass
		else:
			try:
				match = dbcur.execute('''SELECT * FROM liked_lists WHERE trakt_id=?;''', (trakt_id,)).fetchone()
				liked_list = match[3]
			except: pass
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()
	return liked_list

def insert_liked_lists(items, new_sync=True):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS liked_lists (list_owner TEXT, list_owner_slug TEXT, list_name TEXT, trakt_id TEXT, content_type TEXT, item_count INTEGER, likes INTEGER, UNIQUE(trakt_id));''')
		dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
		if new_sync:
			dbcur.execute('''DELETE FROM liked_lists''')
			dbcur.connection.commit() # added this for what looks like a 19 bug not found in 18, normal commit is at end
			dbcur.execute('''VACUUM''')
		for item in items:
			try:
				list_item = item.get('list', {})
				list_owner = list_item.get('user', {}).get('username', '')
				list_owner_slug = list_item.get('user', {}).get('ids', {}).get('slug', '')

				list_name = list_item.get('name', '')
				trakt_id = list_item.get('ids', {}).get('trakt', '')
				content_type = list_item.get('content_type', '')
				item_count = list_item.get('item_count', '')
				likes = list_item.get('likes', '')
				dbcur.execute('''INSERT OR REPLACE INTO liked_lists Values (?, ?, ?, ?, ?, ?, ?)''', (list_owner, list_owner_slug, list_name, trakt_id, content_type, item_count, likes))
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_liked_at', timestamp))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def delete_liked_list(trakt_id):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name='liked_lists';''').fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS liked_lists (list_owner TEXT, list_owner_slug TEXT, list_name TEXT, trakt_id TEXT, item_count INTEGER, likes INTEGER, UNIQUE(trakt_id));''')
			dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
			dbcur.connection.commit()
			return
		dbcur.execute('''DELETE FROM liked_lists WHERE trakt_id=?;''', (trakt_id,))
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_liked_at', timestamp))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def fetch_hidden_progress():
	list = ''
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name='hiddenProgress';''').fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS hiddenProgress (title TEXT, year TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, trakt TEXT, hidden_at TEXT, UNIQUE(imdb, tmdb, tvdb, trakt));''')
			dbcur.connection.commit()
			return list
		try:
			match = dbcur.execute('''SELECT * FROM hiddenProgress WHERE NOT title=""''').fetchall()
			list = [{'title': i[0], 'year': i[1], 'imdb': i[2], 'tmdb': i[3], 'tvdb': i[4], 'trakt': i[5], 'added': i[6]} for i in match]
		except: pass
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()
	return list

def insert_hidden_progress(items, new_sync=True):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS hiddenProgress (title TEXT, year TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, trakt TEXT, hidden_at TEXT, UNIQUE(imdb, tmdb, tvdb, trakt));''')
		dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
		if new_sync:
			dbcur.execute('''DELETE FROM hiddenProgress''')
			dbcur.connection.commit() # added this for what looks like a 19 bug not found in 18, normal commit is at end
			dbcur.execute('''VACUUM''')
		for i in items:
			try:
				item = i.get('show')
				title = item.get('title')
				year = item.get('year', '') or ''
				ids = item.get('ids')
				imdb = ids.get('imdb', '')
				tmdb = ids.get('tmdb', '')
				tvdb = ids.get('tvdb', '')
				trakt = ids.get('trakt', '')
				hidden_at = i.get('hidden_at', '')
				dbcur.execute('''INSERT OR REPLACE INTO hiddenProgress Values (?, ?, ?, ?, ?, ?, ?)''', (title, year, imdb, tmdb, tvdb, trakt, hidden_at))
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_hiddenProgress_at', timestamp))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def delete_hidden_progress(items):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name='hiddenProgress';''').fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS hiddenProgress (title TEXT, year TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, trakt TEXT, hidden_at TEXT, UNIQUE(imdb, tmdb, tvdb, trakt));''')
			dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
			dbcur.connection.commit()
			return
		for item in items: # item is tvdb_id in list
			try:
				dbcur.execute('''DELETE FROM hiddenProgress WHERE tvdb=?;''', (item,))
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_hiddenProgress_at', timestamp))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def fetch_collection(table):
	list = ''
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', (table,)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, trakt TEXT, rating FLOAT, votes INTEGER, collected_at TEXT, UNIQUE(imdb, tmdb, tvdb, trakt));''' % table)
			dbcur.connection.commit()
			return list
		try:
			match = dbcur.execute('''SELECT * FROM %s WHERE NOT title=""''' % table).fetchall()
			list = [{'title': i[0], 'year': i[1], 'premiered': i[2], 'imdb': i[3], 'tmdb': i[4], 'tvdb': i[5], 'trakt': i[6], 'rating': i[7], 'votes': i[8], 'added': i[9]} for i in match]
		except: pass
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()
	return list

def insert_collection(items, table, new_sync=True):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, trakt TEXT, rating FLOAT, votes INTEGER, collected_at TEXT, UNIQUE(imdb, tmdb, tvdb, trakt));''' % table)
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
					collected_at = i.get('last_collected_at', '')
				else:
					item = i.get('movie')
					premiered = item.get('released', '') or ''
					collected_at = i.get('collected_at', '')
				title = item.get('title')
				year = item.get('year', '') or ''
				ids = item.get('ids')
				imdb = ids.get('imdb', '')
				tmdb = ids.get('tmdb', '')
				tvdb = ids.get('tvdb', '')
				trakt = ids.get('trakt', '')
				rating = item.get('rating', '')
				votes = item.get('votes', '')
				dbcur.execute('''INSERT OR REPLACE INTO %s Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''' % table, (title, year, premiered, imdb, tmdb, tvdb, trakt, rating, votes, collected_at))
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_collected_at', timestamp))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def delete_collection_items(items, table, col_name='trakt'):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', (table,)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, trakt TEXT, rating FLOAT, votes INTEGER, collected_at TEXT, UNIQUE(imdb, tmdb, tvdb, trakt));''' % table)
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
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_collected_at', timestamp))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def fetch_watch_list(table):
	list = ''
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', (table,)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, trakt TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, UNIQUE(imdb, tmdb, tvdb, trakt));''' % table)
			dbcur.connection.commit()
			return list
		try:
			match = dbcur.execute('''SELECT * FROM %s WHERE NOT title=""''' % table).fetchall()
			list = [{'title': i[0], 'year': i[1], 'premiered': i[2], 'imdb': i[3], 'tmdb': i[4], 'tvdb': i[5], 'trakt': i[6], 'rating': i[7], 'votes': i[8], 'added': i[9]} for i in match]
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
		dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, trakt TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, UNIQUE(imdb, tmdb, tvdb, trakt));''' % table)
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
				trakt = ids.get('trakt', '')
				rating = item.get('rating', '')
				votes = item.get('votes', '')
				listed_at = i.get('listed_at', '')
				dbcur.execute('''INSERT OR REPLACE INTO %s Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''' % table, (title, year, premiered, imdb, tmdb, tvdb, trakt, rating, votes, listed_at))
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

def delete_watchList_items(items, table, col_name='trakt'):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', (table,)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, trakt TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, UNIQUE(imdb, tmdb, tvdb, trakt));''' % table)
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

def fetch_user_lists(trakt_id, ret_all=False):
	user_lists = ''
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name='user_lists';''').fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS user_lists (list_owner TEXT, list_owner_slug TEXT, list_name TEXT, trakt_id TEXT, content_type TEXT, item_count INTEGER, likes INTEGER, UNIQUE(trakt_id));''')
			dbcur.connection.commit()
			return user_lists
		if ret_all:
			try:
				match = dbcur.execute('''SELECT * FROM user_lists WHERE NOT trakt_id=""''').fetchall()
				user_lists = [{'list_owner': i[0], 'list_owner_slug': i[1], 'list_name': i[2], 'trakt_id': i[3], 'content_type': i[4], 'item_count': i[5], 'likes': i[6]} for i in match]
			except: pass
		else:
			try:
				match = dbcur.execute('''SELECT * FROM user_lists WHERE trakt_id=?;''', (trakt_id,)).fetchone()
				user_lists = match[3]
			except: pass
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()
	return user_lists

def insert_user_lists(items, new_sync=True):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS user_lists (list_owner TEXT, list_owner_slug TEXT, list_name TEXT, trakt_id TEXT, content_type TEXT, item_count INTEGER, likes INTEGER, UNIQUE(trakt_id));''')
		dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
		if new_sync:
			dbcur.execute('''DELETE FROM user_lists''')
			dbcur.connection.commit() # added this for what looks like a 19 bug not found in 18, normal commit is at end
			dbcur.execute('''VACUUM''')
		for item in items:
			try:
				list_owner = item.get('user', {}).get('username', '')
				list_owner_slug = item.get('user', {}).get('ids', {}).get('slug', '')
				list_name = item.get('name', '')
				trakt_id = item.get('ids', {}).get('trakt', '')
				content_type = item.get('content_type', '')
				item_count = item.get('item_count', '')
				likes = item.get('likes', '')
				dbcur.execute('''INSERT OR REPLACE INTO user_lists Values (?, ?, ?, ?, ?, ?, ?)''', (list_owner, list_owner_slug, list_name, trakt_id, content_type, item_count, likes))
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_lists_updatedat', timestamp))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()


# def delete_user_list(trakt_id):
# def fetch_user_list_items(trakt_id, ret_all=False):
# def insert_user_list_items(items, new_sync=True):
# def delete_user_list_items(trakt_id):


def fetch_public_list(trakt_id, ret_all=False):
	public_list = ''
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name='public_lists';''').fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS public_lists (list_owner TEXT, list_owner_slug TEXT, list_name TEXT, trakt_id TEXT, content_type TEXT, item_count INTEGER, likes INTEGER, updated_at TEXT, UNIQUE(trakt_id));''')
			dbcur.connection.commit()
			return public_list
		if ret_all:
			try:
				match = dbcur.execute('''SELECT * FROM public_lists WHERE NOT trakt_id=""''').fetchall()
				public_list = [{'list_owner': i[0], 'list_owner_slug': i[1], 'list_name': i[2], 'trakt_id': i[3], 'content_type': i[4], 'item_count': i[5], 'likes': i[6], 'updated_at': i[7]} for i in match]
			except: pass
		else:
			try:
				match = dbcur.execute('''SELECT * FROM public_lists WHERE trakt_id=?;''', (trakt_id,)).fetchone()
				public_list = {'list_owner': match[0], 'list_owner_slug': match[1], 'list_name': match[2], 'trakt_id': match[3], 'content_type': match[4], 'item_count': match[5], 'likes': match[6], 'updated_at': match[7]}
			except: pass
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()
	return public_list

def insert_public_lists(items, service_type='last_popularlist_at', new_sync=True):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS public_lists (list_owner TEXT, list_owner_slug TEXT, list_name TEXT, trakt_id TEXT, content_type TEXT, item_count INTEGER, likes INTEGER, updated_at TEXT, UNIQUE(trakt_id));''')
		dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
		if new_sync:
			dbcur.execute('''DELETE FROM public_lists''')
			dbcur.connection.commit() # added this for what looks like a 19 bug not found in 18, normal commit is at end
			dbcur.execute('''VACUUM''')
		for item in items:
			try:
				list_item = item.get('list', {})
				list_owner = list_item.get('user', {}).get('username', '')
				list_owner_slug = list_item.get('user', {}).get('ids', {}).get('slug', '')
				list_name = list_item.get('name', '')
				trakt_id = list_item.get('ids', {}).get('trakt', '')
				content_type = list_item.get('content_type', '')
				item_count = list_item.get('item_count', '')
				likes = list_item.get('likes', '')
				updated_at = list_item.get('updated_at', '')
				dbcur.execute('''INSERT OR REPLACE INTO public_lists Values (?, ?, ?, ?, ?, ?, ?, ?)''', (list_owner, list_owner_slug, list_name, trakt_id, content_type, item_count, likes, updated_at))
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', (service_type, timestamp))
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

def delete_tables(tables):
	cleared = False
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		service_dict = {
			'bookmarks': 'last_paused_at',
			'hiddenProgress': 'last_hiddenProgress_at',
			'liked_lists': 'last_liked_at',
			'movies_collection': 'last_collected_at',
			'movies_watchlist': 'last_watchlisted_at',
			'popular_lists': 'last_popularlist_at',
			'public_lists': 'last_popularlist_at',
			'shows_collection': 'last_collected_at',
			'shows_watchlist': 'last_watchlisted_at',
			'trending_lists': 'last_trendinglist_at',
			'user_lists': 'last_lists_updatedat',
			'watched': 'last_syncSeasons_at'}
		for table,v in iter(tables.items()):
			if v is True:
				dbcur.execute('''DROP TABLE IF EXISTS {}'''.format(table))
				dbcur.execute('''VACUUM''')
				dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', (service_dict[table], '1970-01-01T20:00:00.000Z'))
				dbcur.connection.commit()
				cleared = True
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		cleared = False
	finally:
		dbcur.close() ; dbcon.close()
	return cleared

def get_connection(setRowFactory=False):
	if not existsPath(dataPath): makeFile(dataPath)
	dbcon = db.connect(traktSyncFile, timeout=60) # added timeout 3/23/21 for concurrency with threads
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


########  Here down for reading and writting watched indicators and counts  ############
def get(function, duration, *args, trakt=None):
	"""
	:param function: Function to be executed
	:param duration: Duration of validity of cache in hours
	:param args: Optional arguments for the provided function
	:named var: Optional, used by trakt module and is not counted in md5 hash
	"""
	try:
		key = _hash_function(function, args)
		cache_result = cache_get(key)
		if cache_result:
			try: result = literal_eval(cache_result['value'])
			except: result = None
			if _is_cache_valid(cache_result['date'], duration): return result
		if trakt: fresh_result = repr(function(*args, trakt=trakt)) # may need a try-except block for server timeouts
		else: fresh_result = repr(function(*args))

		if cache_result and (result and len(result) == 1) and fresh_result == '[]': # fix for syncSeason mark unwatched season when it's the last item remaining
			if result[0].isdigit():
				remove(function, *args)
				return []

		invalid = False
		try: # Sometimes None is returned as a string instead of None type for "fresh_result"
			if not fresh_result: invalid = True
			elif fresh_result == 'None' or fresh_result == '' or fresh_result == '[]' or fresh_result == '{}': invalid = True
			elif len(fresh_result) == 0: invalid = True
		except: pass

		if invalid: # If the cache is old, but we didn't get "fresh_result", return the old cache
			if cache_result: return result
			else: return None # do not cache_insert() None type, sometimes servers just down momentarily
		else:
			if '404:NOT FOUND' in fresh_result:
				cache_insert(key, None) # cache_insert() "404:NOT FOUND" cases only as None type
				return None
			else: cache_insert(key, fresh_result)
			return literal_eval(fresh_result)
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return None

def _is_cache_valid(cached_time, cache_timeout):
	now = int(time())
	diff = now - cached_time
	return (cache_timeout * 3600) > diff

def timeout(function, *args, returnNone=False):
	try:
		key = _hash_function(function, args)
		result = cache_get(key)
		if not result and returnNone: return None
		else: return int(result['date']) if result else 0
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return None if returnNone else 0

def cache_existing(function, *args):
	try:
		cache_result = cache_get(_hash_function(function, args))
		if cache_result: return literal_eval(cache_result['value'])
		else: return None
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return None

def cache_get(key):
	try:
		dbcon = get_connection(setRowFactory=True)
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name='watched';''').fetchone()
		if not ck_table: return None
		results = dbcur.execute('''SELECT * FROM watched WHERE key=?''', (key,)).fetchone()
		return results
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return None
	finally:
		dbcur.close() ; dbcon.close()

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
		dbcur.close() ; dbcon.close()

def remove(function, *args):
	try:
		key = _hash_function(function, args)
		key_exists = cache_get(key)
		if key_exists:
			dbcon = get_connection(setRowFactory=True)
			dbcur = get_connection_cursor(dbcon)
			dbcur.execute('''DELETE FROM watched WHERE key=?''', (key,))
			dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	try: dbcur.close() ; dbcon.close()
	except: pass

def _hash_function(function_instance, *args):
	return _get_function_name(function_instance) + _generate_md5(args)

def _get_function_name(function_instance):
	return re_sub(r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', repr(function_instance))

def _generate_md5(*args):
	try:
		md5_hash = md5()
		try: [md5_hash.update(str(arg)) for arg in args]
		except: [md5_hash.update(str(arg).encode('utf-8')) for arg in args]
		hash = str(md5_hash.hexdigest())
		# from resources.lib.modules import log_utils
		# log_utils.log('args=%s: hash=%s' % (args, hash), __name__)
		return hash
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def insert_syncSeasons_at():
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_syncSeasons_at', timestamp))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

# future
def insert_nextEpisode(imdb, tvdb, tmdb, trakt, next_episode):
	try:
		dbcon = get_connection(setRowFactory=True)
		dbcur = get_connection_cursor(dbcon)
		now = int(time())
		dbcur.execute('''CREATE TABLE IF NOT EXISTS next_episodes (imdb TEXT, tvdb TEXT, tmdb TEXT, trakt TEXT, next_episode TEXT, date INTEGER, UNIQUE(imdb, tvdb, tmdb, trakt));''')
		dbcur.execute('''INSERT OR REPLACE INTO next_episodes Values (?, ?, ?, ?, ?, ?)''', (imdb, tvdb, tmdb, trakt, repr(next_episode), now))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def traktClientID():
	traktId = '87e3f055fc4d8fcfd96e61a47463327ca877c51e8597b448e132611c5a677b13'
	if (getSetting('trakt.clientid') != '' and getSetting('trakt.clientid') is not None) and getSetting('traktuserkey.customenabled') == 'true':
		traktId = getSetting('trakt.clientid')
	return traktId