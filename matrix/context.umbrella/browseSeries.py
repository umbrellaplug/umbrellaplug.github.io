# -*- coding: utf-8 -*-

from json import dumps as jsdumps, loads as jsloads
import sys
import xbmc
try: #Py2
	from urlparse import parse_qsl
	from urllib import quote_plus
except ImportError: #Py3
	from urllib.parse import parse_qsl, quote_plus

if __name__ == '__main__':
	item = sys.listitem
	# message = item.getLabel()
	path = item.getPath()
	plugin = 'plugin://plugin.video.umbrella/'
	args = path.split(plugin, 1)
	params = dict(parse_qsl(args[1].replace('?', '')))

	year = params.get('year', '')
	imdb = params.get('imdb', '')
	tmdb = params.get('tmdb', '')
	tvdb = params.get('tvdb', '')
	tvshowtitle = params.get('tvshowtitle', '')
	systvshowtitle = quote_plus(tvshowtitle)
	sysart = quote_plus(params.get('art', '')) if params.get('art') else ''
	if not sysart and 'meta' in params:
		meta = jsloads(params['meta'])
		art = {}
		art['fanart'] = meta.get('fanart', '')
		art['icon'] = meta.get('icon', '')
		art['thumb'] = meta.get('thumb', '')
		art['banner'] = meta.get('banner', '')
		art['clearlogo'] = meta.get('clearlogo', '')
		art['clearart'] = meta.get('clearart', '')
		art['landscape'] = meta.get('landscape', '')
		art['tvshow.poster'] = meta.get('tvshow_poster', '')
		sysart = quote_plus(jsdumps(art))

	xbmc.executebuiltin('ActivateWindow(Videos,plugin://plugin.video.umbrella/?action=seasons&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&art=%s,return)' % (systvshowtitle, year, imdb, tmdb, tvdb, sysart))