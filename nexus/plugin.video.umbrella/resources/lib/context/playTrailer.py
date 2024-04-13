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
	trailer = info.getTrailer()
	try:
		if trailer:
			xbmc.executebuiltin("RunPlugin(%s,1)" % (trailer))
	except:
		from resources.lib.modules import log_utils
		log_utils.error()