# -*- coding: utf-8 -*-

# import sys
import xbmc
from xbmcvfs import File as openFile
try: #Py2
	from urlparse import parse_qsl
	from urllib import quote_plus
except ImportError: #Py3
	from urllib.parse import parse_qsl, quote_plus
# import tmdb as idlookup
import xbmcaddon

def get_infolabel(infolabel):
	return xbmc.getInfoLabel(u'ListItem.{}'.format(infolabel))


if __name__ == '__main__':
	try:
		# item = sys.listitem
		# message = item.getLabel()
		dbid = get_infolabel('dbid')
		dbtype = get_infolabel('dbtype')

		strm_file = xbmc.getInfoLabel(u'Container.ListItem.FileNameAndPath')
		file = openFile(strm_file)
		strm_read = file.read()
		file.close()

		if not strm_read.startswith('plugin://plugin.video.umbrella'):
			import xbmcgui
			xbmcgui.Dialog().notification(heading='Umbrella', message='.strm file failure')
		params = dict(parse_qsl(strm_read.replace('?','')))
		title = params.get('title', '')
		systitle = quote_plus(title)
		year = params.get('year', '')
		imdb = params.get('imdb', '')
		tmdb = params.get('tmdb', '')
		tvdb = params.get('tvdb', '')
		season = params.get('season', '')
		episode = params.get('episode', '')
		tvshowtitle = params.get('tvshowtitle', '')
		systvshowtitle = quote_plus(tvshowtitle)
		premiered = params.get('premiered', '')
		sysmeta = ''
	except:
		import traceback
		traceback.print_exc()

	plugin = 'plugin://plugin.video.umbrella/'
	# path = 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&rescrape=true)' % (
	# 								plugin, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, premiered, sysmeta)
	# xbmc.executebuiltin(path)
	if xbmcaddon.Addon().getSetting("context.umbrella.rescrape2") == 'true':
		rescrape_method = xbmcaddon.Addon().getSetting("context.umbrella.rescrape3")
		if rescrape_method == '0':
			path = 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&rescrape=true&select=1)' % (
									plugin, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, premiered, sysmeta)
		if rescrape_method == '1':
			path = 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&rescrape=true&select=0)' % (
									plugin, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, premiered, sysmeta)
		if rescrape_method == '2':
			path = 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&rescrape=true&all_providers=true&select=1)' % (
									plugin, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, premiered, sysmeta)
		if rescrape_method == '3':
			path = 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&rescrape=true&all_providers=true&select=0)' % (
									plugin, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, premiered, sysmeta)
	else:
		path = 'PlayMedia(%s?action=rescrapeMenu&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s)' % (
									plugin, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, premiered, sysmeta)

	xbmc.executebuiltin(path)