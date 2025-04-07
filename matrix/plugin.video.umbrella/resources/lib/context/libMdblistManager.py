# -*- coding: utf-8 -*-

import sys
import xbmc
try: #Py2
	from urlparse import parse_qsl
	from urllib import quote_plus
except ImportError: #Py3
	from urllib.parse import parse_qsl, quote_plus
from xbmcvfs import File as openFile
def get_infolabel(infolabel):
	return xbmc.getInfoLabel(u'ListItem.{}'.format(infolabel))

if __name__ == '__main__':
	dbid = get_infolabel('dbid')
	dbtype = get_infolabel('dbtype')
	plugin = 'plugin://plugin.video.umbrella/'
	strm_file = xbmc.getInfoLabel(u'Container.ListItem.FileNameAndPath')
	file = openFile(strm_file)
	strm_read = file.read()
	file.close()

	if not strm_read.startswith('plugin://plugin.video.umbrella'):
		import xbmcgui
		xbmcgui.Dialog().notification(heading='Umbrella', message='.strm file failure')
	params = dict(parse_qsl(strm_read.replace('?','')))
	meta = dict()
	if params.get('title') == '' or params.get('title') == None: 
		meta.update({'title': params.get('tvshowtitle')})
	else: 
		meta.update({'title': params.get('title')})
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

	plugin = 'plugin://plugin.video.umbrella/'
	name = meta.get('title')
	sysname = quote_plus(name)

	imdb = meta.get('imdb', '')
	tvdb = meta.get('tvdb', '')
	tmdb = meta.get('tmdb', '')


	path = 'RunPlugin(%s?action=tools_mdbWatchlist&name=%s&imdb=%s&tvdb=%s&tmdb=%s)' % (
				plugin, sysname, imdb, tvdb, tmdb)
	xbmc.executebuiltin(path)