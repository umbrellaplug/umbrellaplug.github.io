# -*- coding: utf-8 -*-
"""
	Scrapers Utility Module adapted from FS Umbrella Dev 08/21/23
"""

import re

RES_4K = ('2160', '216o', '.4k', 'ultrahd', 'ultra.hd', '.uhd.')
RES_1080 = ('1080', '1o8o', '108o', '1o80', '.fhd.')
RES_720 = ('720', '72o')
SCR = ('dvdscr', 'screener', '.scr.', '.r5', '.r6')
CAM = ('1xbet', 'betwin', '.cam.', 'camrip', 'cam.rip', 'dvdcam', 'dvd.cam', 'dvdts', 'hdcam', '.hd.cam', '.hctc', '.hc.tc', '.hdtc',
				'.hd.tc', 'hdts', '.hd.ts', 'hqcam', '.hg.cam', '.tc.', '.tc1', '.tc7', '.ts.', '.ts1', '.ts7', 'tsrip', 'telecine', 'telesync', 'tele.sync')

def info_from_name(release_title, title, year, hdlr=None, episode_title=None, season=None, pack=None):
	try:
		release_title = release_title.lower().replace('&', 'and').replace("'", "")
		release_title = re.sub(r'[^a-z0-9]+', '.', release_title)
		title = title.lower().replace('&', 'and').replace("'", "")
		title = re.sub(r'[^a-z0-9]+', '.', title)
		name_info = release_title.replace(title, '').replace(year, '')
		if hdlr: name_info = name_info.replace(hdlr.lower(), '')
		if episode_title:
			episode_title = episode_title.lower().replace('&', 'and').replace("'", "")
			episode_title = re.sub(r'[^a-z0-9]+', '.', episode_title)
			name_info = name_info.replace(episode_title, '')
		if pack:
			if pack == 'season':
				season_fill = season.zfill(2)
				str1_replace = ('.s%s' % season, '.s%s' % season_fill, '.season.%s' % season, '.season%s' % season, '.season.%s' % season_fill, '.season%s' % season_fill, 'complete')
				for i in str1_replace: name_info = name_info.replace(i, '')
			elif pack == 'show':
				str2_replace = ('.all.seasons', 'seasons', 'season', 'the.complete', 'complete', 'all.torrent', 'total.series', 'tv.series', 'series', 'edited', 's1', 's01')
				for i in str2_replace: name_info = name_info.replace(i, '')
		name_info = name_info.lstrip('.').rstrip('.')
		name_info = '.%s.' % name_info
		return name_info
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return release_title

def get_qual(term):
	if any(i in term for i in SCR): return 'SCR'
	elif any(i in term for i in CAM): return 'CAM'
	elif any(i in term for i in RES_720): return '720p'
	elif any(i in term for i in RES_1080): return '1080p'
	elif any(i in term for i in RES_4K): return '4K'
	elif '.hd.' in term: return '720p'
	else: return 'SD'

def get_release_quality(release_info, release_link=None):
	try:
		quality = None ; info = []
		if release_info: quality = get_qual(release_info)
		if not quality:
			if release_link:
				release_link = release_link.lower()
				quality = get_qual(release_link)
				if not quality: quality = 'SD'
			else: quality = 'SD'
		return quality, info
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return 'SD', []

def convert_size(size_bytes, to='GB'):
	try:
		import math
		if size_bytes == 0: return 0, ''
		power = {'B' : 0, 'KB': 1, 'MB' : 2, 'GB': 3, 'TB' : 4, 'EB' : 5, 'ZB' : 6, 'YB': 7}
		i = power[to]
		p = math.pow(1024, i)
		float_size = round(size_bytes / p, 2)
		# if to == 'B' or to  == 'KB': return 0, ''
		str_size = "%s %s" % (float_size, to)
		return float_size, str_size
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return 0, ''