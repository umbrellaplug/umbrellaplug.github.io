# -*- coding: utf-8 -*-

import sys
import xbmc
try: #Py2
	from urlparse import parse_qsl
except ImportError: #Py3
	from urllib.parse import parse_qsl, quote_plus

if __name__ == '__main__':
	item = sys.listitem
	# message = item.getLabel()
	path = item.getPath()
	plugin = 'plugin://plugin.video.umbrella/'
	args = path.split(plugin, 1)
	params = dict(parse_qsl(args[1].replace('?', '')))
	imdb = params.get('imdb', '')
	tmdb = params.get('tmdb', '')
	tvdb = params.get('tvdb', '')
	season = params.get('season', '')
	episode = params.get('episode', '')
	tvshowtitle = params.get('tvshowtitle', '')
	title = params.get('title','')
	year = params.get('year', '')
	sysname = item.getLabel()
	if tvshowtitle:
		systvshowtitle = quote_plus(tvshowtitle)
	else:
		systvshowtitle = ''
	if title:
		systitle = quote_plus(title)
	else:
		systitle = ''

	action = 'tvshows' if 'tvshowtitle' in params else 'movies'
	if action == 'tvshows':
		xbmc.executebuiltin('RunPlugin(%s?action=library_tvshowToLibrary&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s)' % (plugin, systvshowtitle, year, imdb, tmdb, tvdb))
	elif action == 'movies':
		xbmc.executebuiltin('RunPlugin(%s?action=library_movieToLibrary&name=%s&title=%s&year=%s&imdb=%s&tmdb=%s)' % (plugin, sysname, systitle, year, imdb, tmdb))