# -*- coding: utf-8 -*-
# modified by   for Umbrellascrapers (updated 12-20-2021)
"""
	Umbrellascrapers Project
"""

import re
from urllib.parse import quote, unquote_plus
from umbrellascrapers.modules import client
from umbrellascrapers.modules import source_utils
from umbrellascrapers.modules import workers


class source:
	priority = 7
	pack_capable = False
	hasMovies = True
	hasEpisodes = True
	def __init__(self):
		self.language = ['en', 'de', 'fr', 'ko', 'pl', 'pt', 'ru']
		self.base_link = "https://1337x.to"
		self.tvsearch = '/sort-category-search/%s/TV/size/desc/1/'
		self.moviesearch = '/sort-category-search/%s/Movies/size/desc/1/'
		self.min_seeders = 1

	def sources(self, data, hostDict):
		self.sources = []
		if not data: return self.sources
		self.sources_append = self.sources.append
		self.items = []
		self.items_append = self.items.append
		try:
			self.title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
			self.title = self.title.replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
			self.aliases = data['aliases']
			self.episode_title = data['title'] if 'tvshowtitle' in data else None
			self.year = data['year']
			self.hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else self.year
			self.undesirables = source_utils.get_undesirables()
			self.check_foreign_audio = source_utils.check_foreign_audio()

			query = '%s %s' % (self.title, self.hdlr)
			query = re.sub(r'[^A-Za-z0-9\s\.-]+', '', query)
			urls = []
			if 'tvshowtitle' in data: urls.append('%s%s' % (self.base_link, self.tvsearch % quote(query)))
			else: urls.append('%s%s' % (self.base_link, self.moviesearch % quote(query)))
			url2 = ''.join(urls).replace('/1/', '/2/')
			urls.append(url2)
			# log_utils.log('urls = %s' % urls)

			threads = []
			append = threads.append
			for url in urls:
				append(workers.Thread(self.get_items, url))
			[i.start() for i in threads]
			[i.join() for i in threads]

			threads2 = []
			append2 = threads2.append
			for i in self.items:
				append2(workers.Thread(self.get_sources, i))
			[i.start() for i in threads2]
			[i.join() for i in threads2]
			return self.sources
		except:
			source_utils.scraper_error('1337X')
			return self.sources

	def get_items(self, url):
		try:
			results = client.request(url, timeout=7)
			if not results or '<tbody' not in results: return
			table = client.parseDOM(results, 'tbody')[0]
			rows = client.parseDOM(table, 'tr')
		except:
			source_utils.scraper_error('1337X')
			return
		for row in rows:
			try:
				columns = re.findall(r'<td.*?>(.+?)</td>', row, re.DOTALL)

				link = '%s%s' % (self.base_link, client.parseDOM(columns[0], 'a', ret='href')[1])
				name = unquote_plus(client.parseDOM(columns[0], 'a')[1])
				if '__cf_email__' in name: continue
				name = source_utils.clean_name(name)


				if not source_utils.check_title(self.title, self.aliases, name, self.hdlr, self.year): continue
				name_info = source_utils.info_from_name(name, self.title, self.year, self.hdlr, self.episode_title)
				if source_utils.remove_lang(name_info, self.check_foreign_audio): continue
				if self.undesirables and source_utils.remove_undesirables(name_info, self.undesirables): continue

				if not self.episode_title: #filter for eps returned in movie query (rare but movie and show exists for Run in 2020)
					ep_strings = [r'[.-]s\d{2}e\d{2}([.-]?)', r'[.-]s\d{2}([.-]?)', r'[.-]season[.-]?\d{1,2}[.-]?']
					name_lower = name.lower()
					if any(re.search(item, name_lower) for item in ep_strings): continue

				try:
					seeders = int(columns[1].replace(',', ''))
					if self.min_seeders > seeders: continue
				except: seeders = 0

				try:
					dsize, isize = source_utils._size(columns[4].split('<')[0])
				except: isize = '0' ; dsize = 0
				self.items_append((name, name_info, link, isize, dsize, seeders))
			except:
				source_utils.scraper_error('1337X')

	def get_sources(self, item):
		try:
			quality, info = source_utils.get_release_quality(item[1], item[2])
			if item[3] != '0': info.insert(0, item[3])
			info = ' | '.join(info)
			data = client.request(item[2], timeout=7)
			url = re.search(r'href\s*=\s*["\'](magnet:.+?)["\']', data, re.I).group(1)
			url = unquote_plus(url).replace('&amp;', '&').split('&tr')[0].replace(' ', '.')
			hash = re.search(r'btih:(.*?)&', url, re.I).group(1)
			self.sources_append({'provider': '1337x', 'source': 'torrent', 'seeders': item[5], 'hash': hash, 'name': item[0], 'name_info': item[1],
												'quality': quality, 'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': item[4]})
		except:
			source_utils.scraper_error('1337X')