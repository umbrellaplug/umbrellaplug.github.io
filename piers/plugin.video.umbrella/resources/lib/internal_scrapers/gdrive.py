# -*- coding: utf-8 -*-
# (updated 12-14-2021)
'''
	Umbrella Internal Scrapers
'''

import re
import requests
from urllib.parse import unquote, quote_plus
from resources.lib.modules.control import setting as getSetting
from resources.lib.modules import source_utils
from resources.lib.modules import scrape_utils

cloudflare_worker_url = getSetting('gdrivetoken').strip()


def getResults(searchTerm):
	url = '{}/searchjson/{}'.format(cloudflare_worker_url, searchTerm)
	if not url.startswith("https://"): url = "https://" + url
	# log_utils.log('query url = %s' % url)
	results = requests.get(url).json()
	return results

class source:
	priority = 1
	pack_capable = False
	hasMovies = True
	hasEpisodes = True
	def __init__(self):
		self.language = ['en']
		self.title_chk = (getSetting('gdrive.title.chk') == 'true')

	def sources(self, data, hostDict):
		sources = []
		if not data: return sources
		append = sources.append
		try:
			title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
			title = title.replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
			aliases = data['aliases']
			episode_title = data['title'] if 'tvshowtitle' in data else None
			year = data['year']
			hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else year

			query = '%s %s' % (title, hdlr)
			query = quote_plus(re.sub(r'[^A-Za-z0-9\s\.-]+', '', query))
			if cloudflare_worker_url == '': return sources
			results = getResults(query)
			if not results: return sources
		except:
			source_utils.scraper_error('GDRIVE')
			return sources

		for result in results:
			try:
				link = result["link"]
				name = unquote(link.rsplit("/")[-1])
				if self.title_chk:
					if not scrape_utils.check_title(title, aliases, name, hdlr, year): continue
				name_info = scrape_utils.info_from_name(name, title, year, hdlr, episode_title)

				quality, info = scrape_utils.get_release_quality(name_info, link)
				try:
					size = str(result["size_gb"]) + ' GB'
					dsize, isize = scrape_utils._size(size)
					if isize: info.insert(0, isize)
				except:
					source_utils.scraper_error('GDRIVE')
					dsize = 0
				info = ' | '.join(info)

				append({'provider': 'gdrive', 'source': 'direct', 'name': name, 'name_info': name_info,
								'quality': quality, 'language': 'en', 'url': link, 'info': info,  'direct': True, 'debridonly': False, 'size': dsize})
			except:
				source_utils.scraper_error('GDRIVE')
		return sources