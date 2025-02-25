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
from resources.lib.modules.control import existsPath, dataPath, makeFile, simKLSyncFile, setting as getSetting
from resources.lib.modules import log_utils


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
		
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def fetch_plantowatch(table):
	list = ''
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', (table,)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, simkl TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, UNIQUE(imdb, tmdb, tvdb, simkl));''' % table)
			dbcur.connection.commit()
			return list
		try:
			match = dbcur.execute('''SELECT * FROM %s WHERE NOT title=""''' % table).fetchall()
			list = [{'title': i[0], 'year': i[1], 'premiered': i[2], 'imdb': i[3], 'tmdb': i[4], 'tvdb': i[5], 'simkl': i[6], 'rating': i[7], 'votes': i[8], 'added': i[9]} for i in match]
		except: pass
	except:
		
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()
	return list

def insert_plantowatch(items, table, new_sync=True):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, simkl TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, UNIQUE(imdb, tmdb, tvdb, simkl));''' % table)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
		if new_sync:
			dbcur.execute('''DELETE FROM %s''' % table)
			dbcur.connection.commit() # added this for what looks like a 19 bug not found in 18, normal commit is at end
			dbcur.execute('''VACUUM''')
		type = items[0].get('show')
		if type: type = 'Show'
		else: type = 'Movie'
		
		log_utils.log('Simkl inserting plantowatch items. Number of items: %s Item Type: %s' % (len(items), type),1)
		for i in items:
			try:
				if 'show' in i:
					item = i.get('show')
					try: premiered = item.get('first_aired', '').split('T')[0]
					except: premiered = ''
				else:
					item = i.get('movie')
					premiered = ''
				title = item.get('title')
				year = item.get('year', '') or ''
				ids = item.get('ids')
				imdb = ids.get('imdb', '')
				tmdb = ids.get('tmdb', '')
				tvdb = ids.get('tvdb', '')
				simkl = ids.get('simkl', '')
				rating = item.get('rating', '')
				votes = item.get('votes', '')
				dstr = i.get('added_to_watchlist_at')
				if not dstr:  # Check if it's missing or blank
					dstr = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
				else:
					date_part, time_part = dstr.rstrip('Z').split('T')
					dstr = f"{date_part}T{time_part}.000000Z"
				listed_at = dstr
				dbcur.execute('''INSERT OR REPLACE INTO %s Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''' % table, (title, year, premiered, imdb, tmdb, tvdb, simkl, rating, votes, listed_at))
			except Exception as e:
				log_utils.log("Error inserting item: %s. Exception: %s" % (str(i), str(e)), 1)  # Log the problematic item
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_plantowatch_at', timestamp))
		dbcur.connection.commit()
	except:
		
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def fetch_watching(table):
	list = ''
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', (table,)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, simkl TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, last_watch_at TEXT, UNIQUE(imdb, tmdb, tvdb, simkl));''' % table)
			dbcur.connection.commit()
			return list
		try:
			match = dbcur.execute('''SELECT * FROM %s WHERE NOT title=""''' % table).fetchall()
			list = [{'title': i[0], 'year': i[1], 'premiered': i[2], 'imdb': i[3], 'tmdb': i[4], 'tvdb': i[5], 'simkl': i[6], 'rating': i[7], 'votes': i[8], 'added': i[9], 'lastplayed': i[10]} for i in match]
		except: pass
	except:
		
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()
	return list

def insert_watching(items, table, new_sync=True):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, simkl TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, last_watched_at TEXT, UNIQUE(imdb, tmdb, tvdb, simkl));''' % table)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
		if new_sync:
			dbcur.execute('''DELETE FROM %s''' % table)
			dbcur.connection.commit() # added this for what looks like a 19 bug not found in 18, normal commit is at end
			dbcur.execute('''VACUUM''')
		type = items[0].get('show')
		if type: type = 'Show'
		else: type = 'Movie'
		
		log_utils.log('Simkl inserting watching items. Number of items: %s Item Type: %s' % (len(items), type),1)
		for i in items:
			try:
				if 'show' in i:
					item = i.get('show')
					try: premiered = item.get('first_aired', '').split('T')[0]
					except: premiered = ''
				else:
					item = i.get('movie')
					premiered = ''
				title = item.get('title')
				year = item.get('year', '') or ''
				ids = item.get('ids')
				imdb = ids.get('imdb', '')
				tmdb = ids.get('tmdb', '')
				tvdb = ids.get('tvdb', '')
				simkl = ids.get('simkl', '')
				rating = item.get('rating', '')
				votes = item.get('votes', '')
				dstr = i.get('added_to_watchlist_at')
				last_watched_at = i.get('last_watched_at','')
				if last_watched_at:
					date_part, time_part = last_watched_at.rstrip('Z').split('T')
					last_watched_at = f"{date_part}T{time_part}.000000Z"
				if not dstr:  # Check if it's missing or blank
					dstr = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
				else:
					date_part, time_part = dstr.rstrip('Z').split('T')
					dstr = f"{date_part}T{time_part}.000000Z"
				listed_at = dstr
				dbcur.execute('''INSERT OR REPLACE INTO %s Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''' % table, (title, year, premiered, imdb, tmdb, tvdb, simkl, rating, votes, listed_at, last_watched_at))
			except Exception as e:
				log_utils.log("Error inserting item: %s. Exception: %s" % (str(i), str(e)), 1)  # Log the problematic item
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_watching_at', timestamp))
		dbcur.connection.commit()
	except:
		
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def fetch_hold(table):
	list = ''
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', (table,)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, simkl TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, UNIQUE(imdb, tmdb, tvdb, simkl));''' % table)
			dbcur.connection.commit()
			return list
		try:
			match = dbcur.execute('''SELECT * FROM %s WHERE NOT title=""''' % table).fetchall()
			list = [{'title': i[0], 'year': i[1], 'premiered': i[2], 'imdb': i[3], 'tmdb': i[4], 'tvdb': i[5], 'simkl': i[6], 'rating': i[7], 'votes': i[8], 'added': i[9]} for i in match]
		except: pass
	except:
		
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()
	return list

def insert_hold(items, table, new_sync=True):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, simkl TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, UNIQUE(imdb, tmdb, tvdb, simkl));''' % table)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
		if new_sync:
			dbcur.execute('''DELETE FROM %s''' % table)
			dbcur.connection.commit() # added this for what looks like a 19 bug not found in 18, normal commit is at end
			dbcur.execute('''VACUUM''')
		type = items[0].get('show')
		if type: type = 'Show'
		else: type = 'Movie'
		
		log_utils.log('Simkl inserting hold items. Number of items: %s Item Type: %s' % (len(items), type),1)
		for i in items:
			try:
				if 'show' in i:
					item = i.get('show')
					try: premiered = item.get('first_aired', '').split('T')[0]
					except: premiered = ''
				else:
					item = i.get('movie')
					premiered = ''
				title = item.get('title')
				year = item.get('year', '') or ''
				ids = item.get('ids')
				imdb = ids.get('imdb', '')
				tmdb = ids.get('tmdb', '')
				tvdb = ids.get('tvdb', '')
				simkl = ids.get('simkl', '')
				rating = item.get('rating', '')
				votes = item.get('votes', '')
				dstr = i.get('added_to_watchlist_at')
				if not dstr:  # Check if it's missing or blank
					dstr = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
				else:
					date_part, time_part = dstr.rstrip('Z').split('T')
					dstr = f"{date_part}T{time_part}.000000Z"
				listed_at = dstr
				dbcur.execute('''INSERT OR REPLACE INTO %s Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''' % table, (title, year, premiered, imdb, tmdb, tvdb, simkl, rating, votes, listed_at))
			except Exception as e:
				log_utils.log("Error inserting item: %s. Exception: %s" % (str(i), str(e)), 1)  # Log the problematic item
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_hold_at', timestamp))
		dbcur.connection.commit()
	except:
		
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def remove_hold_item(tvdb):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		table = 'shows_hold'
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', (table,)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, simkl TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, UNIQUE(imdb, tmdb, tvdb, simkl));''' % table)
			dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
			dbcur.connection.commit()
			return

		try:
			dbcur.execute('''DELETE FROM %s WHERE %s=?;''' % (table, 'tvdb'), (tvdb,))
		except:
			
			log_utils.error()
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_plantowatch_at', timestamp))
		dbcur.connection.commit()
	except:
		
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def remove_plan_to_watch(imdb, table):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', (table,)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, simkl TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, UNIQUE(imdb, tmdb, tvdb, simkl));''' % table)
			dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
			dbcur.connection.commit()
			return

		try:
			dbcur.execute('''DELETE FROM %s WHERE %s=?;''' % (table, 'imdb'), (imdb,))
		except:
			
			log_utils.error()
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_plantowatch_at', timestamp))
		dbcur.connection.commit()
	except:
		
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def fetch_dropped(table):
	list = ''
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', (table,)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, simkl TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, UNIQUE(imdb, tmdb, tvdb, simkl));''' % table)
			dbcur.connection.commit()
			return list
		try:
			match = dbcur.execute('''SELECT * FROM %s WHERE NOT title=""''' % table).fetchall()
			list = [{'title': i[0], 'year': i[1], 'premiered': i[2], 'imdb': i[3], 'tmdb': i[4], 'tvdb': i[5], 'simkl': i[6], 'rating': i[7], 'votes': i[8], 'added': i[9]} for i in match]
		except: pass
	except:
		
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()
	return list

def insert_dropped(items, table, new_sync=True):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, simkl TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, UNIQUE(imdb, tmdb, tvdb, simkl));''' % table)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
		if new_sync:
			dbcur.execute('''DELETE FROM %s''' % table)
			dbcur.connection.commit() # added this for what looks like a 19 bug not found in 18, normal commit is at end
			dbcur.execute('''VACUUM''')
		type = items[0].get('show')
		if type: type = 'Show'
		else: type = 'Movie'
		
		log_utils.log('Simkl inserting dropped items. Number of items: %s Item Type: %s' % (len(items), type),1)
		for i in items:
			try:
				if 'show' in i:
					item = i.get('show')
					try: premiered = item.get('first_aired', '').split('T')[0]
					except: premiered = ''
				else:
					item = i.get('movie')
					premiered = ''
				title = item.get('title')
				year = item.get('year', '') or ''
				ids = item.get('ids')
				imdb = ids.get('imdb', '')
				tmdb = ids.get('tmdb', '')
				tvdb = ids.get('tvdb', '')
				simkl = ids.get('simkl', '')
				rating = item.get('rating', '')
				votes = item.get('votes', '')
				dstr = i.get('added_to_watchlist_at')
				if not dstr:  # Check if it's missing or blank
					dstr = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
				listed_at = dstr
				dbcur.execute('''INSERT OR REPLACE INTO %s Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''' % table, (title, year, premiered, imdb, tmdb, tvdb, simkl, rating, votes, listed_at))
			except Exception as e:
				log_utils.log("Error inserting item: %s. Exception: %s" % (str(i), str(e)), 1)  # Log the problematic item
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_dropped_at', timestamp))
		dbcur.connection.commit()
	except:
		
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def delete_plantowatch_items(items, table, col_name='simkl'):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', (table,)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, simkl TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, UNIQUE(imdb, tmdb, tvdb, simkl));''' % table)
			dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
			dbcur.connection.commit()
			return
		for item in items:
			try:
				dbcur.execute('''DELETE FROM %s WHERE %s=?;''' % (table, col_name), (item,))
			except:
				
				log_utils.error()
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_plantowatch_at', timestamp))
		dbcur.connection.commit()
	except:
		
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def delete_hold_items(items, table, col_name='simkl'):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', (table,)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, simkl TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, UNIQUE(imdb, tmdb, tvdb, simkl));''' % table)
			dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
			dbcur.connection.commit()
			return
		for item in items:
			try:
				dbcur.execute('''DELETE FROM %s WHERE %s=?;''' % (table, col_name), (item,))
			except:
				
				log_utils.error()
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_hold_at', timestamp))
		dbcur.connection.commit()
	except:
		
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def delete_dropped_items(items, table, col_name='simkl'):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', (table,)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, simkl TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, UNIQUE(imdb, tmdb, tvdb, simkl));''' % table)
			dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
			dbcur.connection.commit()
			return
		for item in items:
			try:
				dbcur.execute('''DELETE FROM %s WHERE %s=?;''' % (table, col_name), (item,))
			except:
				
				log_utils.error()
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_hold_at', timestamp))
		dbcur.connection.commit()
	except:
		
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def fetch_completed(table):
	list = ''
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', (table,)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, simkl TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, last_watched_at TEXT, UNIQUE(imdb, tmdb, tvdb, simkl));''' % table)
			dbcur.connection.commit()
			return list
		try:
			match = dbcur.execute('''SELECT * FROM %s WHERE NOT title=""''' % table).fetchall()
			list = [{'title': i[0], 'year': i[1], 'premiered': i[2], 'imdb': i[3], 'tmdb': i[4], 'tvdb': i[5], 'simkl': i[6], 'rating': i[7], 'votes': i[8], 'added': i[9], 'lastplayed': i[10]} for i in match]
		except: pass
	except:
		
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()
	return list

def insert_completed(items, table, new_sync=True):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, simkl TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, last_watched_at TEXT, UNIQUE(imdb, tmdb, tvdb, simkl));''' % table)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
		if new_sync:
			dbcur.execute('''DELETE FROM %s''' % table)
			dbcur.connection.commit() # added this for what looks like a 19 bug not found in 18, normal commit is at end
			dbcur.execute('''VACUUM''')
		type = items[0].get('show')
		if type: type = 'Show'
		else: type = 'Movie'
		
		log_utils.log('Simkl inserting completed items. Number of items: %s Item Type: %s' % (len(items), type),1)
		for i in items:
			try:
				if 'show' in i:
					item = i.get('show')
					try: premiered = item.get('first_aired', '').split('T')[0]
					except: premiered = ''
				else:
					item = i.get('movie')
					premiered = ''
				title = item.get('title')
				year = item.get('year', '') or ''
				ids = item.get('ids')
				imdb = ids.get('imdb', '')
				tmdb = ids.get('tmdb', '')
				tvdb = ids.get('tvdb', '')
				simkl = ids.get('simkl', '')
				rating = item.get('rating', '')
				votes = item.get('votes', '')
				added_to_watchlist_at = i.get('added_to_watchlist_at')
				last_watched_at = i.get('last_watched_at','')
				if last_watched_at:
					date_part, time_part = last_watched_at.rstrip('Z').split('T')
					last_watched_at = f"{date_part}T{time_part}.000000Z"
				if added_to_watchlist_at:
					dstr = added_to_watchlist_at
				elif last_watched_at:
					dstr = last_watched_at
				else:
					dstr = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
				listed_at = dstr
				dbcur.execute('''INSERT OR REPLACE INTO %s Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''' % table, (title, year, premiered, imdb, tmdb, tvdb, simkl, rating, votes, listed_at, last_watched_at))
			except Exception as e:
				log_utils.log("Error inserting item: %s. Exception: %s" % (str(i), str(e)), 1)  # Log the problematic item
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_completed_at', timestamp))
		dbcur.connection.commit()
	except:
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def delete_plantowatch(items, table, col_name='simkl'):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', (table,)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, simkl TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, last_watched_at TEXT, UNIQUE(imdb, tmdb, tvdb, simkl));''' % table)
			dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
			dbcur.connection.commit()
			return
		for item in items:
			try:
				dbcur.execute('''DELETE FROM %s WHERE %s=?;''' % (table, col_name), (item,))
			except:
				
				log_utils.error()
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_history_at', timestamp))
		dbcur.connection.commit()
	except:
		
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
			'movies_hold': 'last_hold_at',
			'shows_hold': 'last_hold_at',
			'movies_plantowatch': 'last_plantowatch_at',
			'shows_plantowatch': 'last_plantowatch_at',
			'shows_watching': 'last_watching_at',
			'watched': 'last_syncSeasons_at',
			'movies_completed': 'last_completed_at',
			'shows_completed': 'last_completed_at',
			'movies_dropped': 'last_dropped_at',
			'shows_dropped': 'last_dropped_at'}
		dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
		for table,v in iter(tables.items()):
			if v is True:
				dbcur.execute('''DROP TABLE IF EXISTS {}'''.format(table))
				dbcur.execute('''VACUUM''')
				dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', (service_dict[table], '1970-01-01T20:00:00.000Z'))
				dbcur.connection.commit()
				cleared = True
	except:
		
		log_utils.error()
		cleared = False
	finally:
		dbcur.close() ; dbcon.close()
	return cleared

def get_connection(setRowFactory=False):
	if not existsPath(dataPath): makeFile(dataPath)
	dbcon = db.connect(simKLSyncFile, timeout=60)
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
def get(function, duration, *args, simkl_id=None, data=None):
	"""
	:param function: Function to be executed
	:param duration: Duration of validity of cache in hours
	:param args: Optional arguments for the provided function
	:named var: Optional, used by simkl module and is not counted in md5 hash
	:named var data: needs to be ignored for cache
	"""
	try:
		key = _hash_function(function, args)
		cache_result = cache_get(key)
		if cache_result:
			try: result = literal_eval(cache_result['value'])
			except: result = None
			if _is_cache_valid(cache_result['date'], duration): return result
		if simkl_id: fresh_result = repr(function(*args, simkl_id=simkl_id)) # may need a try-except block for server timeouts
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
		
		log_utils.error()
		return None if returnNone else 0

def cache_existing(function, *args):
	try:
		cache_result = cache_get(_hash_function(function, args))
		if cache_result: return literal_eval(cache_result['value'])
		else: return None
	except:
		
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
		if len(args[0][0]) > 2: args = ((args[0][0][:2],),) #change made to make sure the hash matches when only two arguments are passed on getCache
		try: [md5_hash.update(str(arg)) for arg in args]
		except: [md5_hash.update(str(arg).encode('utf-8')) for arg in args]
		hash = str(md5_hash.hexdigest())
		return hash
	except:
		
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
		
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

# future
def insert_nextEpisode(imdb, tvdb, tmdb, simkl, next_episode):
	try:
		dbcon = get_connection(setRowFactory=True)
		dbcur = get_connection_cursor(dbcon)
		now = int(time())
		dbcur.execute('''CREATE TABLE IF NOT EXISTS next_episodes (imdb TEXT, tvdb TEXT, tmdb TEXT, simkl TEXT, next_episode TEXT, date INTEGER, UNIQUE(imdb, tvdb, tmdb, simkl));''')
		dbcur.execute('''INSERT OR REPLACE INTO next_episodes Values (?, ?, ?, ?, ?, ?)''', (imdb, tvdb, tmdb, simkl, repr(next_episode), now))
		dbcur.connection.commit()
	except:
		
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()