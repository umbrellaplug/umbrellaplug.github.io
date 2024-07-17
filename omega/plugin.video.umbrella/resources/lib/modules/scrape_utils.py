# -*- coding: utf-8 -*-
"""
	Scrapers Utility Module adapted from FS Umbrella Dev 08/21/23
"""

import re
from resources.lib.modules import cleantitle
from string import printable

RES_4K = ('2160', '216o', '.4k', 'ultrahd', 'ultra.hd', '.uhd.')
RES_1080 = ('1080', '1o8o', '108o', '1o80', '.fhd.')
RES_720 = ('720', '72o')
SCR = ('dvdscr', 'screener', '.scr.', '.r5', '.r6')
CAM = ('1xbet', 'betwin', '.cam.', 'camrip', 'cam.rip', 'dvdcam', 'dvd.cam', 'dvdts', 'hdcam', '.hd.cam', '.hctc', '.hc.tc', '.hdtc',
				'.hd.tc', 'hdts', '.hd.ts', 'hqcam', '.hg.cam', '.tc.', '.tc1', '.tc7', '.ts.', '.ts1', '.ts7', 'tsrip', 'telecine', 'telesync', 'tele.sync')

unwanted_tags = ('tamilrockers.com', 'www.tamilrockers.com', 'www.tamilrockers.ws', 'www.tamilrockers.pl',
			'www-tamilrockers-cl', 'www.tamilrockers.cl', 'www.tamilrockers.li', 'www-tamilrockers-tw',
			'www.tamilrockerrs.pl',
			'www.tamilmv.bid', 'www.tamilmv.biz', 'www.1tamilmv.org',
			'gktorrent-bz', 'gktorrent-com',
			'www.torrenting.com', 'www.torrenting.org', 'www-torrenting-com', 'www-torrenting-org',
			'katmoviehd.pw', 'katmoviehd-pw',
			'www.torrent9.nz', 'www-torrent9-uno', 'torrent9-cz', 'torrent9.cz', 'torrent9-red', 'torrent9-bz',
			'agusiq-torrents-pl',
			'oxtorrent-bz', 'oxtorrent-com', 'oxtorrent.com', 'oxtorrent-sh', 'oxtorrent-vc',
			'www.movcr.tv', 'movcr-com', 'www.movcr.to',
			'(imax)', 'imax',
			'xtorrenty.org', 'nastoletni.wilkoak', 'www.scenetime.com', 'kst-vn',
			'www.movierulz.vc', 'www-movierulz-ht', 'www.2movierulz.ac', 'www.2movierulz.ms',
			'www.3movierulz.com', 'www.3movierulz.tv', 'www.3movierulz.ws', 'www.3movierulz.ms',
			'www.7movierulz.pw', 'www.8movierulz.ws',
			'mkvcinemas.live', 'torrentcounter-to',
			'www.bludv.tv', 'ramin.djawadi', 'extramovies.casa', 'extramovies.wiki',
			'13+', '18+', 'taht.oyunlar', 'crazy4tv.com', 'karibu', '989pa.com',
			'best-torrents-net', '1-3-3-8.com', 'ssrmovies.club',
			'va:', 'zgxybbs-fdns-uk', 'www.tamilblasters.mx',
			'www.1tamilmv.work', 'www.xbay.me',
			'crazy4tv-com', '(es)')

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

def check_title(title, aliases, release_title, hdlr, year, years=None): # non pack file title check, single eps and movies
	if years: # for movies only, scraper to pass None for episodes
		if not any(value in release_title for value in years): return False
	else: 
		if not re.search(r'%s' % hdlr, release_title, re.I): return False
	aliases = aliases_to_array(aliases)
	title_list = []
	title_list_append = title_list.append
	if aliases:
		for item in aliases:
			try:
				alias = item.replace('&', 'and').replace(year, '')
				if years: # for movies only, scraper to pass None for episodes
					for i in years: alias = alias.replace(i, '')
				if alias in title_list: continue
				title_list_append(alias)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
	try:
		
		title = title.replace('&', 'and').replace(year, '') # year only in meta title if an addon custom query added it
		if title not in title_list: title_list_append(title)
		release_title = re.sub(r'([(])(?=((19|20)[0-9]{2})).*?([)])', '\\2', release_title) #remove parenthesis only if surrounding a 4 digit date
		t = re.split(r'%s' % hdlr, release_title, 1, re.I)[0].replace(year, '').replace('&', 'and')
		if years:
			for i in years: t = t.split(i)[0]
		t = re.split(r'2160p|216op|4k|1080p|1o8op|108op|1o80p|720p|72op|480p|48op', t, 1, re.I)[0]
		cleantitle_t = cleantitle.get(t)
		if all(cleantitle.get(i) != cleantitle_t for i in title_list): return False

# filter to remove episode ranges that should be picked up in "filter_season_pack()" ex. "s01e01-08"
		if hdlr != year: # equal for movies but not for shows
			range_regex = (
					r's\d{1,3}e\d{1,3}[-.]e\d{1,3}',
					r's\d{1,3}e\d{1,3}[-.]\d{1,3}(?!p|bit|gb)(?!\d{1,3})',
					r's\d{1,3}[-.]e\d{1,3}[-.]e\d{1,3}',
					r'season[.-]?\d{1,3}[.-]?ep[.-]?\d{1,3}[-.]ep[.-]?\d{1,3}',
					r'season[.-]?\d{1,3}[.-]?episode[.-]?\d{1,3}[-.]episode[.-]?\d{1,3}') # may need to add "to", "thru"
			for regex in range_regex:
				if bool(re.search(regex, release_title, re.I)): return False
		return True
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return False

def aliases_to_array(aliases, filter=None):
	try:
		if all(isinstance(x, str) for x in aliases): return aliases
		if not filter: filter = []
		if isinstance(filter, str): filter = [filter]
		return [x.get('title') for x in aliases if not filter or x.get('country') in filter]
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return []

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

def get_qual(term):
	if any(i in term for i in SCR): return 'SCR'
	elif any(i in term for i in CAM): return 'CAM'
	elif any(i in term for i in RES_720): return '720p'
	elif any(i in term for i in RES_1080): return '1080p'
	elif any(i in term for i in RES_4K): return '4K'
	elif '.hd.' in term: return '720p'
	else: return 'SD'

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

def clean_name(release_title):
	try:
		release_title = re.sub(r'【.*?】', '', release_title)
		release_title = strip_non_ascii_and_unprintable(release_title).lstrip('+.-:/ ').replace(' ', '.')
		releasetitle_startswith = release_title.lower().startswith
		if releasetitle_startswith('rifftrax'): return release_title # removed by "undesirables" anyway so exit
		for i in unwanted_tags:
			if releasetitle_startswith(i):
				release_title = re.sub(r'^%s' % i.replace('+', '\+'), '', release_title, 1, re.I)
		release_title = release_title.lstrip('+.-:/ ')
		release_title = re.sub(r'^\[.*?]', '', release_title, 1, re.I)
		release_title = release_title.lstrip('.-[](){}:/')
		return release_title
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return release_title

def strip_non_ascii_and_unprintable(text):
	try:
		result = ''.join(char for char in text if char in printable)
		return result.encode('ascii', errors='ignore').decode('ascii', errors='ignore')
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return text

def _size(siz):
	try:
		if siz in ('0', 0, '', None): return 0, ''
		div = 1 if siz.lower().endswith(('gb', 'gib')) else 1024
		# if ',' in siz and siz.lower().endswith(('mb', 'mib')): siz = size.replace(',', '')
		# elif ',' in siz and siz.lower().endswith(('gb', 'gib')): siz = size.replace(',', '.')
		dec_count = len(re.findall(r'[.]', siz))
		if dec_count == 2: siz = siz.replace('.', ',', 1) # torrentproject2 likes to randomly use 2 decimals vs. a comma then a decimal
		float_size = round(float(re.sub(r'[^0-9|/.|/,]', '', siz.replace(',', ''))) / div, 2) #comma issue where 2,750 MB or 2,75 GB (sometimes replace with "." and sometimes not)
		str_size = '%.2f GB' % float_size
		return float_size, str_size
	except:
		from resources.lib.modules import log_utils
		log_utils.error('failed on siz=%s' % siz)
		return 0, ''