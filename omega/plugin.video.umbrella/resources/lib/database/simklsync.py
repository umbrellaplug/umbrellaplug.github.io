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
				# Normalize all IDs to strings — insert_bookmarks stores TEXT, but meta may pass integers
				_imdb = str(imdb or '')
				_tmdb = str(tmdb or '')
				_tvdb = str(tvdb or '')
				_season = str(season or '')
				_episode = str(episode or '')
				try: # Priority 1 — imdb + tvdb
					match = dbcur.execute('''SELECT * FROM bookmarks WHERE (imdb=? AND tvdb=? AND season=? AND episode=? AND NOT imdb='' AND NOT tvdb='')''', (_imdb, _tvdb, _season, _episode)).fetchone()
					if ret_type == 'resume_info':
						progress = (match[0], match[2])
						log_utils.log('Getting resume from database imdb+tvdb. Match: %s' % (str(match)),1)
					else: progress = match[12]
				except:
					try: # Priority 2 — tvdb only
						match = dbcur.execute('''SELECT * FROM bookmarks WHERE (tvdb=? AND season=? AND episode=? AND NOT tvdb='')''', (_tvdb, _season, _episode)).fetchone()
						if ret_type == 'resume_info':
							progress = (match[0], match[2])
							log_utils.log('Getting resume from database tvdb. Match: %s' % (str(match)),1)
						else: progress = match[12]
					except:
						try: # Priority 3 — imdb + tmdb (Simkl does not store tvdb)
							match = dbcur.execute('''SELECT * FROM bookmarks WHERE (imdb=? AND tmdb=? AND season=? AND episode=? AND NOT imdb='' AND NOT tmdb='')''', (_imdb, _tmdb, _season, _episode)).fetchone()
							if ret_type == 'resume_info':
								progress = (match[0], match[2])
								log_utils.log('Getting resume from database imdb+tmdb. Match: %s' % (str(match)), 1)
							else: progress = match[12]
						except:
							try: # Priority 4 — imdb only
								match = dbcur.execute('''SELECT * FROM bookmarks WHERE (imdb=? AND season=? AND episode=? AND NOT imdb='')''', (_imdb, _season, _episode)).fetchone()
								if ret_type == 'resume_info':
									progress = (match[0], match[2])
									log_utils.log('Getting resume from database imdb+season+episode. Match: %s' % (str(match)), 1)
								else: progress = match[12]
							except:
								try: # Priority 5 — tmdb only (imdb may be absent from Simkl /sync/playback response)
									match = dbcur.execute('''SELECT * FROM bookmarks WHERE (tmdb=? AND season=? AND episode=? AND NOT tmdb='')''', (_tmdb, _season, _episode)).fetchone()
									if ret_type == 'resume_info':
										progress = (match[0], match[2])
										log_utils.log('Getting resume from database tmdb+season+episode. Match: %s' % (str(match)), 1)
									else: progress = match[12]
								except:
									try: # Priority 6 — season+episode only, no ID guard (all IDs may be absent from Simkl /sync/playback; table has at most 1 active episode)
										match = dbcur.execute('''SELECT * FROM bookmarks WHERE (season=? AND episode=? AND NOT percent_played='0' AND NOT percent_played='')''', (_season, _episode)).fetchone()
										if ret_type == 'resume_info':
											progress = (match[0], match[2])
											log_utils.log('Getting resume from database season+episode only. Match: %s' % (str(match)), 1)
										else: progress = match[12]
									except: pass
	except:

		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass
	return progress

def insert_bookmarks(items):
	# items = list from GET /sync/playback — Simkl API format
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS bookmarks (tvshowtitle TEXT, title TEXT, resume_id TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, season TEXT, episode TEXT, genre TEXT, mpaa TEXT,
								studio TEXT, duration TEXT, percent_played TEXT, paused_at TEXT, UNIQUE(resume_id, imdb, tmdb, tvdb, season, episode));''')
		dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
		dbcur.execute('''DELETE FROM bookmarks''')
		dbcur.connection.commit()
		dbcur.execute('''VACUUM''')
		for i in items:
			tvshowtitle, tvdb, season, episode, genre, mpaa, studio, duration = '', '', '', '', 'NA', 'NR', '', ''
			resume_id = str(i.get('id', ''))
			percent_played = str(i.get('progress', '0'))
			paused_at = i.get('paused_at', '')
			if i.get('type') == 'episode':
				show_ids = i.get('show', {}).get('ids', {})
				ep = i.get('episode', {})
				tvshowtitle = i.get('show', {}).get('title', '')
				title = ep.get('title', '')
				imdb = str(show_ids.get('imdb', ''))
				tmdb = str(show_ids.get('tmdb', ''))
				season = str(ep.get('season', ''))
				episode = str(ep.get('number', ep.get('episode', '')))  # Simkl GET /sync/playback uses "number" key
			else:
				movie_ids = i.get('movie', {}).get('ids', {})
				title = i.get('movie', {}).get('title', '')
				imdb = str(movie_ids.get('imdb', ''))
				tmdb = str(movie_ids.get('tmdb', ''))
			dbcur.execute('''INSERT OR REPLACE INTO bookmarks Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (tvshowtitle, title, resume_id, imdb, tmdb, tvdb, season, episode, genre, mpaa, studio, duration, percent_played, paused_at))
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', ('last_paused_at', timestamp))
		dbcur.connection.commit()
	except:
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def delete_bookmark(resume_id):
	# resume_id is the Simkl playback session id (string)
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name='bookmarks';''').fetchone()
		if not ck_table:
			return
		dbcur.execute('''DELETE FROM bookmarks WHERE resume_id=?''', (str(resume_id),))
		dbcur.connection.commit()
	except:
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

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
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass
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
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def fetch_watching(table):
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
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass
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
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

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
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass
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
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

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
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

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
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

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
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass
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
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

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
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

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
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

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
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

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
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass
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
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

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
			else: dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', (type, '1970-01-01T00:00:00.000Z'))
		else: dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
		dbcur.connection.commit()
	except:
		
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass
	return last_sync_at

def set_sync_time(service_key):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', (service_key, timestamp))
		dbcur.connection.commit()
	except:
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

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
				dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', (service_dict[table], '1970-01-01T00:00:00.000Z'))
				dbcur.connection.commit()
				cleared = True
	except:
		
		log_utils.error()
		cleared = False
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass
	return cleared

def upsert_items(items, table, service_key, table_type='plantowatch'):
	"""Delete each item by ID from ALL status tables, then insert into target table.
	Per Simkl dev recommendation for date_from delta syncing — avoids full table wipes."""
	all_status_tables = [
		'movies_plantowatch', 'shows_plantowatch', 'shows_watching',
		'shows_hold', 'movies_dropped', 'shows_dropped',
		'movies_completed', 'shows_completed'
	]
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting));''')
		needs_last_watched = table.startswith('shows_') or table == 'movies_completed'
		if needs_last_watched:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, simkl TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, last_watched_at TEXT, UNIQUE(imdb, tmdb, tvdb, simkl));''' % table)
			try:
				dbcur.execute('ALTER TABLE %s ADD COLUMN last_watched_at TEXT' % table)
				dbcur.connection.commit()
			except: pass
		else:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (title TEXT, year TEXT, premiered TEXT, imdb TEXT, tmdb TEXT, tvdb TEXT, simkl TEXT, rating FLOAT, votes INTEGER, listed_at TEXT, UNIQUE(imdb, tmdb, tvdb, simkl));''' % table)
		for i in items:
			item = i.get('show') or i.get('movie')
			if not item: continue
			ids = item.get('ids', {})
			simkl_id = str(ids.get('simkl', ''))
			imdb = ids.get('imdb', '')
			for t in all_status_tables:
				try:
					if simkl_id:
						dbcur.execute('DELETE FROM %s WHERE simkl=?' % t, (simkl_id,))
					elif imdb:
						dbcur.execute('DELETE FROM %s WHERE imdb=?' % t, (imdb,))
				except: pass
			title = item.get('title', '')
			year = str(item.get('year', '') or '')
			try: premiered = item.get('first_aired', '').split('T')[0] if 'show' in i else ''
			except: premiered = ''
			tmdb = str(ids.get('tmdb', ''))
			tvdb = str(ids.get('tvdb', ''))
			simkl = str(ids.get('simkl', ''))
			rating = item.get('rating', '')
			votes = item.get('votes', '')
			dstr = i.get('added_to_watchlist_at') or datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
			listed_at = dstr
			try:
				if needs_last_watched:
					last_watched_at = i.get('last_watched_at', '')
					dbcur.execute('''INSERT OR REPLACE INTO %s Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''' % table,
						(title, year, premiered, imdb, tmdb, tvdb, simkl, rating, votes, listed_at, last_watched_at))
				else:
					dbcur.execute('''INSERT OR REPLACE INTO %s Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''' % table,
						(title, year, premiered, imdb, tmdb, tvdb, simkl, rating, votes, listed_at))
			except Exception as e:
				log_utils.log("upsert_items error on item: %s. Exception: %s" % (str(i), str(e)), 1)
		timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
		dbcur.execute('''INSERT OR REPLACE INTO service Values (?, ?)''', (service_key, timestamp))
		dbcur.connection.commit()
	except:
		log_utils.error()
	finally:
		dbcur.close(); dbcon.close()

def get_connection(setRowFactory=False):
	if not existsPath(dataPath): makeFile(dataPath)
	dbcon = db.connect(simKLSyncFile, timeout=60)
	dbcon.execute('''PRAGMA page_size = 32768''')
	dbcon.execute('''PRAGMA journal_mode = OFF''')
	dbcon.execute('''PRAGMA synchronous = OFF''')
	dbcon.execute('''PRAGMA temp_store = memory''')
	dbcon.execute('''PRAGMA mmap_size = 30000000000''')
	if setRowFactory: dbcon.row_factory = dict_factory
	return dbcon

def get_connection_cursor(dbcon):
	dbcur = dbcon.cursor()
	return dbcur

def dict_factory(cursor, row):
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
		key = hash_function(function, args)
		cache_result = cache_get(key)
		if cache_result:
			try: result = literal_eval(cache_result['value'])
			except: result = None
			if is_cache_valid(cache_result['date'], duration): return result
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

def is_cache_valid(cached_time, cache_timeout):
	now = int(time())
	diff = now - cached_time
	return (cache_timeout * 3600) > diff

def timeout(function, *args, returnNone=False):
	try:
		key = hash_function(function, args)
		result = cache_get(key)
		if not result and returnNone: return None
		else: return int(result['date']) if result else 0
	except:
		
		log_utils.error()
		return None if returnNone else 0

def cache_existing(function, *args):
	try:
		cache_result = cache_get(hash_function(function, args))
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
		
		log_utils.error()
	finally:
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

def remove(function, *args):
	try:
		key = hash_function(function, args)
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

def hash_function(function_instance, *args):
	return get_function_name(function_instance) + generate_md5(args)

def get_function_name(function_instance):
	return re_sub(r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', repr(function_instance))

def generate_md5(*args):
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
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass

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
		try: dbcur.close()
		except: pass
		try: dbcon.close()
		except: pass