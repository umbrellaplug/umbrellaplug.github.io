# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from json import loads as jsloads
from sqlite3 import dbapi2 as database
from resources.lib.modules import control

dataPath = control.transPath(control.addonInfo('path'))
favouritesFile = control.joinPath(dataPath, 'favourites.db')
progressFile = control.joinPath(dataPath, 'progress.db')


def getFavourites(content):
	try:
		dbcon = database.connect(favouritesFile)
		dbcur = dbcon.cursor()
		items = dbcur.execute("SELECT * FROM %s" % content).fetchall()
		items = [(i[0], eval(i[1])) for i in items]
	except: items = []
	finally:
		dbcur.close() ; dbcon.close()
	return items

def getProgress(content):
	try:
		dbcon = database.connect(progressFile)
		dbcur = dbcon.cursor()
		items = dbcur.execute("SELECT * FROM %s" % content).fetchall()
		items = [(i[0], eval(i[1])) for i in items]
	except: items = []
	finally:
		dbcur.close() ; dbcon.close()
	return items

def addFavourite(meta, content):
	try:
		item = dict()
		meta = jsloads(meta)
		try: id = meta['imdb']
		except: id = meta['tvdb']

		if 'title' in meta: title = item['title'] = meta['title']
		if 'tvshowtitle' in meta: title = item['title'] = meta['tvshowtitle']
		if 'year' in meta: item['year'] = meta['year']
		if 'poster' in meta: item['poster'] = meta['poster']
		if 'fanart' in meta: item['fanart'] = meta['fanart']
		if 'clearart' in meta: item['clearart'] = meta['clearart']
		if 'clearlogo' in meta: item['clearlogo'] = meta['clearlogo']
		if 'discart' in meta: item['discart'] = meta['discart']
		if 'imdb' in meta: item['imdb'] = meta['imdb']
		if 'tmdb' in meta: item['tmdb'] = meta['tmdb']
		if 'tvdb' in meta: item['tvdb'] = meta['tvdb']

		control.makeFile(dataPath)
		dbcon = database.connect(favouritesFile)
		dbcur = dbcon.cursor()
		dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (id TEXT, items TEXT, UNIQUE(id));''' % content)
		dbcur.execute('''DELETE FROM %s WHERE id = "%s"''' % (content, id))
		dbcur.execute('''INSERT INTO %s Values (?, ?)''' % content, (id, repr(item)))
		dbcur.connection.commit()
		control.refresh()
		control.notification(title=title, message=32117)
	except: return
	finally:
		dbcur.close() ; dbcon.close()

def addEpisodes(meta, content):
	try:
		item = dict()
		meta = jsloads(meta)
		content = "episode"
		try: id = meta.get('imdb', '') or meta.get('tvdb', '')
		except: id = meta['episodeIDS']['trakt']
		if 'title' in meta: title = item['title'] = meta['title']
		if 'tvshowtitle' in meta: title = item['tvshowtitle'] = meta['tvshowtitle']
		if 'year' in meta: item['year'] = meta['year']
		if 'poster' in meta: item['poster'] = meta['poster']
		if 'fanart' in meta: item['fanart'] = meta['fanart']
		if 'clearart' in meta: item['clearart'] = meta['clearart']
		if 'clearlogo' in meta: item['clearlogo'] = meta['clearlogo']
		if 'imdb' in meta: item['imdb'] = meta['imdb']
		if 'tmdb' in meta: item['tmdb'] = meta['tmdb']
		if 'tvdb' in meta: item['tvdb'] = meta['tvdb']
		if 'episodeIDS' in meta: item['episodeIDS'] = meta['episodeIDS']
		if 'episode' in meta: item['episode'] = meta['episode']
		if 'season' in meta: item['season'] = meta['season']
		if 'premiered' in meta: item['premiered'] = meta['premiered']
		if 'original_year' in meta: item['original_year'] = meta['original_year']
		control.makeFile(dataPath)
		dbcon = database.connect(favouritesFile)
		dbcur = dbcon.cursor()
		dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (id TEXT, items TEXT, UNIQUE(id));''' % content)
		dbcur.execute('''DELETE FROM %s WHERE id = "%s"''' % (content, id))
		dbcur.execute('''INSERT INTO %s Values (?, ?)''' % content, (id, repr(item)))
		dbcur.connection.commit()
		control.refresh()
		control.notification(title=title, message=32117)
	except: return
	finally:
		dbcur.close() ; dbcon.close()

def deleteFavourite(meta, content):
	try:
		meta = jsloads(meta)
		if 'title' in meta: title = meta['title']
		if 'tvshowtitle' in meta: title = meta['tvshowtitle']
		dbcon = database.connect(favouritesFile)
		dbcur = dbcon.cursor()
		dbcur.execute('''DELETE FROM %s WHERE id = "%s"''' % (content, meta['imdb']))
		dbcur.execute('''DELETE FROM %s WHERE id = "%s"''' % (content, meta['tvdb']))
		dbcur.execute('''DELETE FROM %s WHERE id = "%s"''' % (content, meta['tmdb']))
		dbcur.connection.commit()
		control.refresh()
		control.notification(title=title, message=32118)
	except: return
	finally:
		dbcur.close() ; dbcon.close()

def deleteProgress(meta, content):
	try:
		meta = jsloads(meta)
		dbcon = database.connect(progressFile)
		dbcur = dbcon.cursor()
		dbcur.execute('''DELETE FROM %s WHERE id = "%s"''' % (content, meta['imdb']))
		dbcur.execute('''DELETE FROM %s WHERE id = "%s"''' % (content, meta['tvdb']))
		dbcur.execute('''DELETE FROM %s WHERE id = "%s"''' % (content, meta['tmdb']))
		dbcur.connection.commit()
		control.refresh()
	except: return
	finally:
		dbcur.close() ; dbcon.close()