# -*- coding: utf-8 -*-
"""
	Umbrella Add-on Added 10-1 by umbrella
"""
from sqlite3 import dbapi2 as db
from time import time
from resources.lib.modules import control
import xbmc
import xbmcvfs
import os

getLS = control.getLangString


def substitute_get(key):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name='substitle';''').fetchone()
		if not ck_table: return key
		keyLower = str(key).lower()
		results = dbcur.execute('''SELECT * FROM substitle WHERE originalTitle=?''', (keyLower,)).fetchone()
		if results:
			return results.get('subTitle','')
		else:
			return key
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return None
	finally:
		dbcur.close() ; dbcon.close()

def all_substitutes(self):
	results = []
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		sub_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name='substitle';''').fetchone()
		if not sub_table: return results
		results1 = dbcur.execute('''SELECT * FROM substitle''').fetchall()
		if results1:
			results = results1
		return results
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return results
	finally:
		dbcur.close() ; dbcon.close()

def sub_insert(originalTitle, subTitle):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		dbcur.execute('''CREATE TABLE IF NOT EXISTS substitle (ID Integer PRIMARY KEY AUTOINCREMENT, originalTitle TEXT, subTitle TEXT);''')
		key = str(originalTitle).lower()
		dbcur.execute('''INSERT OR REPLACE INTO substitle Values (?, ?, ?)''', (None, key, subTitle))
		dbcur.connection.commit()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def get_connection():
	if not control.existsPath(control.dataPath): control.makeFile(control.dataPath)
	dbcon = db.connect(control.subsFile, timeout=60)
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

def clear_substitute(table, key):
	cleared = False
	try:
		dbcon = get_connection()
		dbcur = dbcon.cursor()
		dbcur.execute('''DELETE FROM {} WHERE originalTitle=?;'''.format(table), (key,))
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

def get_connection_subs():
	control.makeFile(control.dataPath)
	conn = db.connect(control.subsFile)
	conn.row_factory = _dict_factory
	return conn
#added to clear old artwork