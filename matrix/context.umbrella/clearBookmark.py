# -*- coding: utf-8 -*-

import sys
import xbmc
try: #Py2
	from urlparse import parse_qsl
	from urllib import quote_plus
except ImportError: #Py3
	from urllib.parse import parse_qsl, quote_plus

if __name__ == '__main__':
	item = sys.listitem
	path = item.getPath()
	plugin = 'plugin://plugin.video.umbrella/'
	args = path.split(plugin, 1)
	params = dict(parse_qsl(args[1].replace('?', '')))

	year = params.get('year')
	name = params.get('title') + ' (%s)' % year

	if 'tvshowtitle' in params:
		season = params.get('season', '')
		episode = params.get('episode', '')
		name = params.get('tvshowtitle') + ' S%02dE%02d' % (int(season), int(episode))
	sysname = quote_plus(name)

	umbrella_path = 'RunPlugin(%s?action=cache_clearBookmark&name=%s&year=%s&opensettings=false)' % (plugin, sysname, year)
	xbmc.executebuiltin(umbrella_path)

	path = path.split('&meta=')[0]
	kodi_path = 'RunPlugin(%s?action=cache_clearKodiBookmark&url=%s)' % (plugin, quote_plus(path))
	xbmc.executebuiltin(kodi_path)
	xbmc.executebuiltin('UpdateLibrary(video,special://skin/foo)')