# -*- coding: utf-8 -*-
"""
	Umbrella Add-on - TMDB Watchlist Context Script (widget context menu)
"""

import sys
from xbmc import executebuiltin

try:  # Py2
	from urlparse import parse_qsl
	from urllib import quote_plus
except ImportError:  # Py3
	from urllib.parse import parse_qsl, quote_plus

if __name__ == '__main__':
	item = sys.listitem
	path = item.getPath()

	plugin = 'plugin://plugin.video.umbrella/'
	args = path.split(plugin, 1)
	params = dict(parse_qsl(args[1].replace('?', '')))

	name = params.get('tvshowtitle') or params.get('title', '')
	tmdb = params.get('tmdb', '')
	mediatype = 'tv' if params.get('tvshowtitle') else 'movie'

	executebuiltin('RunPlugin(%s?action=tmdb_v4_watchlist_toggle&tmdb=%s&mediatype=%s)' % (
		plugin, tmdb, mediatype))
