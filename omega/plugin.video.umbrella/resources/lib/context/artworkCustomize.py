# -*- coding: utf-8 -*-

import sys
from xbmc import getInfoLabel, executebuiltin
try: #Py2
	from urlparse import parse_qsl
	from urllib import quote_plus
except ImportError: #Py3
	from urllib.parse import parse_qsl, quote_plus
from json import loads as jsloads
				

if __name__ == '__main__':
	item = sys.listitem
	# message = item.getLabel()
	path = item.getPath()
	plugin = 'plugin://plugin.video.umbrella/'
	args = path.split(plugin, 1)
	params = dict(parse_qsl(args[1].replace('?', '')))
	name = params['tvshowtitle'] if 'tvshowtitle' in params else params['title']
	sysname = quote_plus(name)
	imdb = params.get('imdb', '')
	tvdb = params.get('tvdb', '')
	season = params.get('season', '')
	episode = params.get('episode', '')
	tmdb = params.get('tmdb')
	art = params.get('art')
	poster = item.getArt('poster')
	fanart = item.getArt('fanart')
	landscape = item.getArt('landscape')
	banner = item.getArt('banner')
	clearart = item.getArt('clearart')
	clearlogo = item.getArt('clearlogo')
	discart = item.getArt('disart')
	keyart = item.getArt('keyart')

	if tvdb: path = 'RunPlugin(%s?action=customizeArt&mediatype=%s&imdb=%s&tmdb=%s&tvdb=%s&poster=%s&fanart=%s&landscape=%s&banner=%s&clearart=%s&clearlogo=%s)' % (
				plugin, 'show', imdb, tmdb, tvdb, poster, fanart, landscape, banner, clearart, clearlogo)
	else: path = 'RunPlugin(%s?action=customizeArt&mediatype=%s&imdb=%s&tmdb=%s&poster=%s&fanart=%s&landscape=%s&banner=%s&clearart=%s&clearlogo=%s&discart=%s&keyart=%s)' % (plugin, 'movie', imdb, tmdb, poster, fanart, landscape, banner, clearart, clearlogo, discart, keyart)

	executebuiltin(path)