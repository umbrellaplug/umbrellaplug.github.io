# -*- coding: utf-8 -*-

import sys
import xbmc
try: #Py2
	from urlparse import parse_qsl
except ImportError: #Py3
	from urllib.parse import parse_qsl

if __name__ == '__main__':
	item = sys.listitem
	# message = item.getLabel()
	path = item.getPath()
	plugin = 'plugin://plugin.video.umbrella/'
	args = path.split(plugin, 1)
	params = dict(parse_qsl(args[1].replace('?', '')))

	imdb = params.get('imdb', '')
	action = 'tvshows' if 'tvshowtitle' in params else 'movies'

	xbmc.executebuiltin('ActivateWindow(Videos,plugin://plugin.video.umbrella/?action=%s&url=https://api.trakt.tv/%s/%s/related,return)' % (action, 'shows' if 'tvshows' in action else 'movies', imdb))