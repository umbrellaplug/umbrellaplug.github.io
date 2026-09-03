# -*- coding: utf-8 -*-

import sys
from xbmc import getInfoLabel, executebuiltin
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
	name = params['tvshowtitle'] if 'tvshowtitle' in params else params['title']
	sysname = quote_plus(name)

	imdb = params.get('imdb', '')
	tvdb = params.get('tvdb', '')
	tmdb = params.get('tmdb', '')
	season = params.get('season', '')
	episode = params.get('episode', '')

	playcount = getInfoLabel('ListItem.Playcount')
	watched = (int(playcount) >= 1) if playcount else False

	tvshow = '&tvshow=tvshow' if 'tvshowtitle' in params and not season and not episode else ''
	path = 'RunPlugin(%s?action=tools_scrobManager&name=%s&imdb=%s&tvdb=%s&tmdb=%s&season=%s&episode=%s&watched=%s%s)' % (
				plugin, sysname, imdb, tvdb, tmdb, season, episode, watched, tvshow)
	executebuiltin(path)
