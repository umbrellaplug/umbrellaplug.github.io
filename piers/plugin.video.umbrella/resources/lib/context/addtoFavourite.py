# -*- coding: utf-8 -*-

import sys
import xbmc
try: #Py2
	from urlparse import parse_qsl
except ImportError: #Py3
	from urllib.parse import parse_qsl, quote_plus
from json import loads as jsloads, dumps as jsdumps
from sqlite3 import dbapi2 as database
import xbmcvfs
import xbmcaddon
import os

if __name__ == '__main__':
	item = sys.listitem
	
	# message = item.getLabel()
	path = item.getPath()
	plugin = 'plugin://plugin.video.umbrella/'
	args = path.split(plugin, 1)
	params = dict(parse_qsl(args[1].replace('?', '')))
	poster = params.get('poster')
	if params.get('meta'):
		meta = jsloads(params.get('meta'))
	else:
		meta = dict()
		if params.get('title') == '' or params.get('title') == None: 
			meta.update({'title': params.get('tvshowtitle')})
		else: 
			meta.update({'title': params.get('title')})
		if params.get('tvshowtitle') != '':
			if params.get('action') == 'seasons':
				meta.update({'mediatype': 'tvshow'})
			else:
				meta.update({'mediatype': 'episode'})
		else:
			meta.update({'mediatype': 'movie'})
		meta.update({'year' : params.get('year')})
		try:
			meta.update({'poster': jsloads(params.get('art')).get('poster')})
		except:
			pass
		try:
			meta.update({'imdb': params.get('imdb')})
		except:
			pass
		try:
			meta.update({'tmdb': params.get('tmdb')})
		except:
			pass
		try:
			meta.update({'tvdb': params.get('tvdb')})
		except:
			pass
		try:
			meta.update({'season': params.get('season')})
		except:
			pass
		try:
			meta.update({'episode': params.get('episode')})
		except:
			pass
	content = meta.get('mediatype')
	sysmeta = jsdumps(meta)
	addonInfo = xbmcaddon.Addon().getAddonInfo
	try: dataPath = xbmcvfs.translatePath(addonInfo('profile')).decode('utf-8')
	except: dataPath = xbmcvfs.translatePath(addonInfo('profile'))
	favouritesFile = os.path.join(dataPath, 'favourites.db')
	if content == 'movie':
		content = 'movies'
		try:
			dbcon = database.connect(favouritesFile)
			dbcur = dbcon.cursor()
			items = dbcur.execute("SELECT * FROM %s" % content).fetchall()
			items = [(i[0], eval(i[1])) for i in items]
		except: items = []
		finally:
			dbcur.close() ; dbcon.close()
		items = [x[1].get('imdb') for x in items]
		imdb = meta.get('imdb')
		if imdb in items:
			xbmc.executebuiltin('RunPlugin(%s?action=remove_favorite&meta=%s&content=%s)' % (plugin, quote_plus(sysmeta), content))
		else:
			xbmc.executebuiltin('RunPlugin(%s?action=add_favorite&meta=%s&content=%s)' % (plugin, quote_plus(sysmeta), content))
	if content == 'tvshow':
		content = 'tvshows'
		try:
			dbcon = database.connect(favouritesFile)
			dbcur = dbcon.cursor()
			items = dbcur.execute("SELECT * FROM %s" % content).fetchall()
			items = [(i[0], eval(i[1])) for i in items]
		except: items = []
		finally:
			dbcur.close() ; dbcon.close()
		items = [x[1].get('imdb') for x in items]
		tmdb = meta.get('imdb')
		if tmdb in items:
			xbmc.executebuiltin('RunPlugin(%s?action=remove_favorite&meta=%s&content=%s)' % (plugin, quote_plus(sysmeta), content))
		else:
			xbmc.executebuiltin('RunPlugin(%s?action=add_favorite&meta=%s&content=%s)' % (plugin, quote_plus(sysmeta), content))
	if content == 'episode':
		content = 'episode'
		try:
			dbcon = database.connect(favouritesFile)
			dbcur = dbcon.cursor()
			items = dbcur.execute("SELECT * FROM %s" % content).fetchall()
			items = [(i[0], i[1], i[2], eval(i[3])) for i in items]
		except: items = []
		finally:
			dbcur.close() ; dbcon.close()
		items = [x[0] for x in items]
		id = meta.get('imdb') + str(meta.get('season'))+ str(meta.get('episode'))
		if (id) in items:
			xbmc.executebuiltin('RunPlugin(%s?action=remove_favorite&meta=%s&content=%s)' % (plugin, quote_plus(sysmeta), content))
		else:
			xbmc.executebuiltin('RunPlugin(%s?action=add_favorite_episode&meta=%s&content=%s)' % (plugin, quote_plus(sysmeta), content))
	
	#if favorite
	
	