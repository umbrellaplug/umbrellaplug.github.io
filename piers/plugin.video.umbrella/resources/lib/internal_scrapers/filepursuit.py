# -*- coding: UTF-8 -*-
# (updated 7-19-2022)
'''
	Umbrella Internal Scrapers
'''

from json import loads as jsloads
import re
from urllib.parse import quote_plus
from resources.lib.modules.control import setting as getSetting
from resources.lib.modules import client
from resources.lib.modules import source_utils
from resources.lib.modules import scrape_utils


class source:
	priority = 23
	pack_capable = False
	hasMovies = True
	hasEpisodes = True
	def __init__(self):
		self.language = ['en']
		self.base_link = "https://filepursuit.p.rapidapi.com" # 'https://rapidapi.com/azharxes/api/filepursuit' to obtain key
		self.search_link = "/?type=video&q=%s"

	def sources(self, data, hostDict):
		sources = []
		if not data: return sources
		append = sources.append
		try:
			api_key = getSetting('filepursuittoken')
			if api_key == '': return sources
			headers = {"x-rapidapi-host": "filepursuit.p.rapidapi.com", "x-rapidapi-key": api_key}
			aliases = data['aliases']
			year = data['year']
			if 'tvshowtitle' in data:
				title = data['tvshowtitle'].replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
				episode_title = data['title']
				hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode']))
			else:
				title = data['title'].replace('&', 'and').replace('/', ' ')
				episode_title = None
				hdlr = year
			query = '%s %s' % (re.sub(r'[^A-Za-z0-9\s\.-]+', '', title), hdlr)
			url = '%s%s' % (self.base_link, self.search_link % quote_plus(query))
			# log_utils.log('url = %s' % url)
			r = client.request(url, headers=headers, timeout=5)
			if not r: return sources
			r = jsloads(r)
			if 'not_found' in r['status']: return sources
			results = r['files_found']
		except:
			source_utils.scraper_error('FILEPURSUIT')
			return sources

		for item in results:
			try:
				url = item['file_link']
				try: size = int(item['file_size_bytes'])
				except: size = 0
				try: name = item['file_name']
				except: name = item['file_link'].split('/')[-1]
				name = scrape_utils.clean_name(name)

				if not scrape_utils.check_title(title, aliases, name, hdlr, year): continue
				name_info = scrape_utils.info_from_name(name, title, year, hdlr, episode_title)
				#if source_utils.remove_lang(name_info, check_foreign_audio): continue
				#if undesirables and source_utils.remove_undesirables(name_info, undesirables): continue

				# link_header = client.request(url, output='headers', timeout=5) # to slow to check validity of links
				# if not any(value in str(link_header) for value in ('stream', 'video/mkv')): continue

				quality, info = scrape_utils.get_release_quality(name_info, url)
				try:
					dsize, isize = scrape_utils.convert_size(size, to='GB')
					if isize: info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				append({'provider': 'filepursuit', 'source': 'direct', 'quality': quality, 'name': name, 'name_info': name_info, 'language': "en",
							'url': url, 'info': info, 'direct': True, 'debridonly': False, 'size': dsize})
			except:
				source_utils.scraper_error('FILEPURSUIT')
		return sources