# -*- coding: utf-8 -*-

import sys
import xbmc
try: #Py2
	from urlparse import parse_qsl
except ImportError: #Py3
	from urllib.parse import parse_qsl, quote_plus

if __name__ == '__main__':
	item = sys.listitem
	info = item.getVideoInfoTag()
	type = info.getMediaType()
	name = info.getTitle()
	tvshowtitle = info.getTVShowTitle()
	if tvshowtitle:
		name = tvshowtitle
	# season = info.getSeason() # may utilize for season specific trailer search
	year = info.getYear()

	#trailer.Trailer().play_select(type, name, year, windowedtrailer=0)
	xbmc.executebuiltin('RunPlugin(plugin://plugin.video.umbrella/?action=play_Trailer_Select&type=%s&name=%s&year=%s&windowedtrailer=0,return)' % (type, name, year))