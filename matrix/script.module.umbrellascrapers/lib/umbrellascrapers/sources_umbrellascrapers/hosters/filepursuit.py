# -*- coding: UTF-8 -*-
# (updated 01-02-2022)
'''
	Umbrellascrapers Project
'''

from json import loads as jsloads
import re
from urllib.parse import quote_plus
from umbrellascrapers.modules.control import setting as getSetting
from umbrellascrapers.modules import client
from umbrellascrapers.modules import source_utils


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
			api_key = getSetting('filepursuit.api')
			if api_key == '': return sources
			headers = {"x-rapidapi-host": "filepursuit.p.rapidapi.com", "x-rapidapi-key": api_key}

			title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
			title = title.replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
			aliases = data['aliases']
			episode_title = data['title'] if 'tvshowtitle' in data else None
			year = data['year']
			hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else year

			query = '%s %s' % (title, hdlr)
			query = re.sub(r'(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', query)
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

		undesirables = source_utils.get_undesirables()
		check_foreign_audio = source_utils.check_foreign_audio()
		for item in results:
			try:
				url = item['file_link']
				try: size = int(item['file_size_bytes'])
				except: size = 0
				try: name = item['file_name']
				except: name = item['file_link'].split('/')[-1]
				name = source_utils.clean_name(name)

				if not source_utils.check_title(title, aliases, name, hdlr, year): continue
				name_info = source_utils.info_from_name(name, title, year, hdlr, episode_title)
				if source_utils.remove_lang(name_info, check_foreign_audio): continue
				if undesirables and source_utils.remove_undesirables(name_info, undesirables): continue

				# link_header = client.request(url, output='headers', timeout=5) # to slow to check validity of links
				# if not any(value in str(link_header) for value in ('stream', 'video/mkv')): continue

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					dsize, isize = source_utils.convert_size(size, to='GB')
					if isize: info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				append({'provider': 'filepursuit', 'source': 'direct', 'quality': quality, 'name': name, 'name_info': name_info, 'language': "en",
							'url': url, 'info': info, 'direct': True, 'debridonly': False, 'size': dsize})
			except:
				source_utils.scraper_error('FILEPURSUIT')
		return sources