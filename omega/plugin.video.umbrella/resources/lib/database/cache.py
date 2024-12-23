# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from ast import literal_eval
from hashlib import md5
from re import sub as re_sub
from sqlite3 import dbapi2 as db
from time import time
from resources.lib.modules import control
import sqlite3
import xbmc
import xbmcvfs
import os
import fnmatch


def get(function, duration, *args):
	"""
	:param function: Function to be executed
	:param duration: Duration of validity of cache in hours
	:param args: Optional arguments for the provided function
	"""
	try:
		key = _hash_function(function, args)
		cache_result = cache_get(key)
		if cache_result:
			from resources.lib.modules import log_utils
			try: result = literal_eval(cache_result['value'])
			except: result = None
			if _is_cache_valid(cache_result['date'], duration):
				return result

		fresh_result = repr(function(*args)) # may need a try-except block for server timeouts

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

def timeout(function, *args):
	try:
		key = _hash_function(function, args)
		result = cache_get(key)
		return int(result['date']) if result else 0
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return 0

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
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name='cache';''').fetchone()
		if not ck_table: return None
		results = dbcur.execute('''SELECT * FROM cache WHERE key=?''', (key,)).fetchone()
		return results
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return None
	finally:
		dbcur.close() ; dbcon.close()

def cache_insert(key, value):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		now = int(time())
		dbcur.execute('''CREATE TABLE IF NOT EXISTS cache (key TEXT, value TEXT, date INTEGER, UNIQUE(key));''')
		dbcur.execute('''INSERT OR REPLACE INTO cache Values (?, ?, ?)''', (key, value, now))
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
			dbcon = get_connection()
			dbcur = get_connection_cursor(dbcon)
			dbcur.execute('''DELETE FROM cache WHERE key=?''', (key,))
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
	md5_hash = md5()
	try: [md5_hash.update(str(arg)) for arg in args]
	except: [md5_hash.update(str(arg).encode('utf-8')) for arg in args]
	return str(md5_hash.hexdigest())

def cache_clear(flush_only=False):
	cleared = False
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		if flush_only:
			dbcur.execute('''DELETE FROM cache''')
			dbcur.connection.commit() # added this for what looks like a 19 bug not found in 18, normal commit is at end
			dbcur.execute('''VACUUM''')
			cleared = True
		else:
			dbcur.execute('''DROP TABLE IF EXISTS cache''')
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

def clearMovieCache():
	cleared = False
	try:
		if not control.existsPath(control.dataPath): control.makeFile(control.dataPath)
		dbcon = db.connect(control.libCacheSimilar)
		dbcur = dbcon.cursor()
		dbcur.execute('''DROP TABLE IF EXISTS movies''')
		dbcur.connection.commit()
		cleared = True
	except: 
		from resources.lib.modules import log_utils
		log_utils.error()
		cleared = False
	return cleared

def get_connection():
	if not control.existsPath(control.dataPath): control.makeFile(control.dataPath)
	dbcon = db.connect(control.cacheFile, timeout=60) # added timeout 3/23/21 for concurrency with threads
	dbcon.execute('''PRAGMA page_size = 32768''')
	dbcon.execute('''PRAGMA journal_mode = OFF''')
	dbcon.execute('''PRAGMA synchronous = OFF''')
	dbcon.execute('''PRAGMA temp_store = memory''')
	dbcon.execute('''PRAGMA mmap_size = 30000000000''')
	dbcon.row_factory = _dict_factory
	return dbcon

def get_connection_cursor(dbcon):
	dbcur = dbcon.cursor()
	return dbcur

def _dict_factory(cursor, row):
	d = {}
	for idx, col in enumerate(cursor.description): d[col[0]] = row[idx]
	return d

##################
def cache_clear_search():
	cleared = False
	try:
		dbcon = get_connection_search()
		dbcur = dbcon.cursor()
		for t in ('movies', 'tvshow', 'collections', 'furk', 'easynews'):
			dbcur.execute('''DROP TABLE IF EXISTS {}'''.format(t))
			dbcur.execute('''VACUUM''')
			dbcur.connection.commit()
			control.refresh()
			cleared = True
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		cleared = False
	finally:
		dbcur.close() ; dbcon.close()
	return cleared

def cache_clear_SearchPhrase(table, key):
	cleared = False
	try:
		dbcon = get_connection_search()
		dbcur = dbcon.cursor()
		dbcur.execute('''DELETE FROM {} WHERE term=?;'''.format(table), (key,))
		dbcur.connection.commit()
		control.refresh()
		cleared = True
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		cleared = False
	finally:
		dbcur.close() ; dbcon.close()
	return cleared

def get_connection_search():
	control.makeFile(control.dataPath)
	conn = db.connect(control.searchFile)
	conn.row_factory = _dict_factory
	return conn
#added to clear old artwork
def cache_clear_thumbnails():
	cleared = False
	thumbnailsPath = xbmcvfs.translatePath('special://profile/Thumbnails/')
	databasePath  = xbmcvfs.translatePath('special://profile/Database/')
	addonPath = xbmcvfs.translatePath('special://home/addons')
	try:
		dbcon = sqlite3.connect(databasePath+'/Textures13.db')
		dbcur = dbcon.cursor()
		icon = dbcur.execute("SELECT cachedurl FROM texture WHERE url ='" + addonPath + "/plugin.video.umbrella/icon.png';").fetchone()
		fanart = dbcur.execute("SELECT cachedurl FROM texture WHERE url ='" + addonPath + "/plugin.video.umbrella/fanart.jpg';").fetchone()
		if icon is not None:
			if xbmcvfs.exists(thumbnailsPath + icon[0]):
				xbmcvfs.delete(thumbnailsPath + icon[0])
			dbcur.execute("DELETE FROM texture WHERE url ='" + addonPath + "/plugin.video.umbrella/icon.png';") #delete the icon
		if fanart is not None:
			if xbmcvfs.exists(thumbnailsPath + fanart[0]):
				xbmcvfs.delete(thumbnailsPath + fanart[0])
			dbcur.execute("DELETE FROM texture WHERE url ='" + addonPath + "/plugin.video.umbrella/fanart.jpg';") #delete the fanart
		dbcon.close()
		cleared = True
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		cleared = False
	return cleared

##################
def cache_clear_bookmarks():
	cleared = False
	try:
		dbcon = get_connection_bookmarks()
		dbcur = dbcon.cursor()
		dbcur.execute('''DROP TABLE IF EXISTS bookmark''')
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

def cache_clear_bookmark(name, year='0'):
	cleared = False
	try:
		dbcon = get_connection_bookmarks()
		dbcur = dbcon.cursor()
		# idFile = md5()
		# for i in name: idFile.update(str(i))
		# for i in year: idFile.update(str(i))
		# idFile = str(idFile.hexdigest())
		# dbcur.execute("DELETE FROM bookmark WHERE idFile = '%s'" % idFile)
		years = [str(year), str(int(year)+1), str(int(year)-1)]
		dbcur.execute('''DELETE FROM bookmark WHERE Name="%s" AND year IN (%s)''' % (name, ','.join(i for i in years)))
		dbcur.connection.commit()
		control.refresh()
		control.trigger_widget_refresh()
		cleared = True
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		cleared = False
	finally:
		dbcur.close() ; dbcon.close()
	return cleared

def get_connection_bookmarks():
	control.makeFile(control.dataPath)
	conn = db.connect(control.bookmarksFile)
	conn.row_factory = _dict_factory
	return conn
##################
def clear_local_bookmarks(): # clear all umbrella bookmarks from kodi database
	try:
		dbcon = db.connect(get_video_database_path())
		dbcur = dbcon.cursor()
		dbcur.execute('''SELECT * FROM files WHERE strFilename LIKE "%plugin.video.umbrella%"''')
		file_ids = [str(i[0]) for i in dbcur.fetchall()]
		for table in ('bookmark', 'streamdetails', 'files'):
			dbcur.execute('''DELETE FROM {} WHERE idFile IN ({})'''.format(table, ','.join(file_ids)))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def clear_local_bookmark(url): # clear all item specific bookmarks from kodi database
	try:
		dbcon = db.connect(get_video_database_path())
		dbcur = dbcon.cursor()
		dbcur.execute('''SELECT * FROM files WHERE strFilename LIKE "%{}%"'''.format(url))
		file_ids = [str(i[0]) for i in dbcur.fetchall()]
		if not file_ids: return
		for table in ('bookmark', 'streamdetails', 'files'):
			dbcur.execute('''DELETE FROM {} WHERE idFile IN ({})'''.format(table, ','.join(file_ids)))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def get_video_database_path():
	databaseFound = False
	try:
		database_path = control.absPath(control.joinPath(control.dataPath, '..', '..', 'Database', )) # doesn't work with mysql
		# path_db = 'special://profile/Database/%s' % db_name
		def find(pattern, path):
			result = []
			for root, dirs, files in os.walk(path):
				for name in files:
					if fnmatch.fnmatch(name, pattern):
						result.append(os.path.join(root, name))
			return result
		databasefile = find('MyVideos*.db', database_path)
		databasefile.sort(reverse=True)
		database_path_final = databasefile[0]
		#from resources.lib.modules import log_utils
		#log_utils.log('Umbrella MyVideos file path: %s' % str(database_path_final), 1)
		databaseFound = True
	except:
		#from resources.lib.modules import log_utils
		#log_utils.log('Umbrella MyVideos file path exception manual selection needed', 1)
		databaseFound = False
	if databaseFound == False:
		kodi_version = control.getKodiVersion()
		if kodi_version == 17: database_path_final = control.joinPath(database_path, 'MyVideos107.db')
		elif kodi_version == 18: database_path_final = control.joinPath(database_path, 'MyVideos116.db')
		elif kodi_version == 19: database_path_final = control.joinPath(database_path, 'MyVideos119.db')
		elif kodi_version == 20: database_path_final = control.joinPath(database_path, 'MyVideos121.db')
		elif kodi_version == 21: database_path_final = control.joinPath(database_path, 'MyVideos131.db')
	return database_path_final
##################

def clrCache_version_update(clr_providers=False, clr_metacache=False, clr_cache=False, clr_search=False, clr_bookmarks=False):
	try:
		if clr_providers:
			from resources.lib.database import providerscache
			providerscache.cache_clear_providers()
		if clr_metacache:
			from resources.lib.database import metacache
			metacache.cache_clear_meta()
		if clr_cache: cache_clear(flush_only=True)
		if clr_search: cache_clear_search()
		if clr_bookmarks: cache_clear_bookmarks()
		control.notification(message='Forced cache clear for version update complete.')
		from resources.lib.modules import log_utils
		log_utils.log('Forced cache clear for version update complete.', level=log_utils.LOGDEBUG)
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def update_cache_version():
	versionFile = control.joinPath(control.dataPath, 'cache.v')
	try:
		if not control.existsPath(versionFile):
			f = open(versionFile, 'w')
			f.close()
	except:
		from resources.lib.modules import log_utils
		log_utils.log('Umbrella Addon Data Path Does not Exist. Creating Folder....', __name__, level=log_utils.LOGDEBUG)
		ad_folder = control.transPath('special://profile/addon_data/plugin.video.umbrella')
		control.makeDirs(ad_folder)
	try:
		with open(versionFile, 'r') as fh: oldVersion = fh.read()
	except: oldVersion = '0'
	try:
		curVersion = control.addon('plugin.video.umbrella').getAddonInfo('version')
		if oldVersion != curVersion:
			with open(versionFile, 'w') as fh: fh.write(curVersion)
			return oldVersion, True
		else: return oldVersion, False
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return oldVersion, False

def get_cache_version():
	versionFile = control.joinPath(control.dataPath, 'cache.v')
	try:
		if not control.existsPath(versionFile):
			f = open(versionFile, 'w')
			f.close()
	except:
		from resources.lib.modules import log_utils
		log_utils.log('Umbrella Addon Data Path Does not Exist. Creating Folder....', __name__, log_utils.LOGDEBUG)
		ad_folder = control.transPath('special://profile/addon_data/plugin.video.umbrella')
		control.makeDirs(ad_folder)
	try:
		with open(versionFile, 'r') as fh: oldVersion = fh.read()
	except: oldVersion = '0'
	return oldVersion