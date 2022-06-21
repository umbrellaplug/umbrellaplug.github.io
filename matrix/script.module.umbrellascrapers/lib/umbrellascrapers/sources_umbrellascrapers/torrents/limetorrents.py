# -*- coding: utf-8 -*-
# modified by   for Umbrellascrapers (updated 3-30-2022)
"""
	Umbrellascrapers Project
"""

import re
from urllib.parse import quote_plus
from umbrellascrapers.modules import cfscrape
from umbrellascrapers.modules import client
from umbrellascrapers.modules import source_utils
from umbrellascrapers.modules import workers


class source:
	priority = 5
	pack_capable = True
	hasMovies = True
	hasEpisodes = True
	def __init__(self):
		self.language = ['en']
		self.base_link = "https://www.limetorrents.lol"
		# self.base_link = "https://limetorrents.proxyninja.org" # if ever needed
		self.tvsearch = '/search/tv/{0}/1/'
		self.moviesearch = '/search/movies/{0}/1/'
		self.min_seeders = 0

	def sources(self, data, hostDict):
		self.sources = []
		if not data: return self.sources
		self.sources_append = self.sources.append
		try:
			self.scraper = cfscrape.create_scraper()

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
			if 'tvshowtitle' in data: url = self.tvsearch.format(quote_plus(query))
			else: url = self.moviesearch.format(quote_plus(query))
			urls.append(url)

			url2 = url.replace('/1/', '/2/')
			urls.append(url2)
			threads = []
			append = threads.append
			for url in urls:
				link = ('%s%s' % (self.base_link, url)).replace('+', '-')
				append(workers.Thread(self.get_sources, link))
			[i.start() for i in threads]
			[i.join() for i in threads]
			return self.sources
		except:
			source_utils.scraper_error('LIMETORRENTS')
			return self.sources

	def get_sources(self, link):
		# log_utils.log('link = %s' % link)
		try:
			results = self.scraper.get(link, timeout=10).text
			if '503 Service Temporarily Unavailable' in results:
				from umbrellascrapers.modules import log_utils
				log_utils.log('LIMETORRENTS (Single request failure): 503 Service Temporarily Unavailable')
				return
			if not results or '<table' not in results: return
			table = client.parseDOM(results, 'table', attrs={'class': 'table2'})[0]
			rows = client.parseDOM(table, 'tr')
			if not rows: return
		except:
			source_utils.scraper_error('LIMETORRENTS')
			return

		for row in rows:
			try:
				if '<th' in row: continue
				columns = re.findall(r'<td.*?>(.+?)</td>', row, re.DOTALL)

				hash = re.search(r'/torrent/(.+?).torrent', columns[0], re.I).group(1)
				name = re.search(r'title\s*=\s*(.+?)["\']', columns[0], re.I).group(1)
				name = source_utils.clean_name(name)

				if not source_utils.check_title(self.title, self.aliases, name, self.hdlr, self.year): continue
				name_info = source_utils.info_from_name(name, self.title, self.year, self.hdlr, self.episode_title)
				if source_utils.remove_lang(name_info, self.check_foreign_audio): continue
				if self.undesirables and source_utils.remove_undesirables(name_info, self.undesirables): continue

				if not self.episode_title: #filter for eps returned in movie query (rare but movie and show exists for Run in 2020)
					ep_strings = [r'[.-]s\d{2}e\d{2}([.-]?)', r'[.-]s\d{2}([.-]?)', r'[.-]season[.-]?\d{1,2}[.-]?']
					name_lower = name.lower()
					if any(re.search(item, name_lower) for item in ep_strings): continue

				url = 'magnet:?xt=urn:btih:%s&dn=%s' % (hash, name)
				try:
					seeders = int(columns[3].replace(',', ''))
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					dsize, isize = source_utils._size(columns[2])
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				self.sources_append({'provider': 'limetorrents', 'source': 'torrent', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info,
												'quality': quality, 'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize})
			except:
				source_utils.scraper_error('LIMETORRENTS')

	def sources_packs(self, data, hostDict, search_series=False, total_seasons=None, bypass_filter=False):
		self.sources = []
		if not data: return self.sources
		self.sources_append = self.sources.append
		try:
			self.scraper = cfscrape.create_scraper()
			self.search_series = search_series
			self.total_seasons = total_seasons
			self.bypass_filter = bypass_filter

			self.title = data['tvshowtitle'].replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
			self.aliases = data['aliases']
			self.imdb = data['imdb']
			self.year = data['year']
			self.season_x = data['season']
			self.season_xx = self.season_x.zfill(2)
			self.undesirables = source_utils.get_undesirables()
			self.check_foreign_audio = source_utils.check_foreign_audio()

			query = re.sub(r'[^A-Za-z0-9\s\.-]+', '', self.title)
			if search_series:
				queries = [
						self.tvsearch.format(quote_plus(query + ' Season')),
						self.tvsearch.format(quote_plus(query + ' Complete'))]
			else:
				queries = [
							self.tvsearch.format(quote_plus(query + ' S%s' % self.season_xx)),
							self.tvsearch.format(quote_plus(query + ' Season %s' % self.season_x))]
			threads = []
			append = threads.append
			for url in queries:
				link = ('%s%s' % (self.base_link, url)).replace('+', '-')
				append(workers.Thread(self.get_sources_packs, link))
			[i.start() for i in threads]
			[i.join() for i in threads]
			return self.sources
		except:
			source_utils.scraper_error('LIMETORRENTS')
			return self.sources

	def get_sources_packs(self, link):
		try:
			results = self.scraper.get(link, timeout=10).text
			if '503 Service Temporarily Unavailable' in results:
				from umbrellascrapers.modules import log_utils
				req_type = 'SHOW' if self.search_series else 'SEASON'
				log_utils.log('LIMETORRENTS (%s Pack request failure): 503 Service Temporarily Unavailable' % req_type)
				return
			if not results or '<table' not in results: return
			table = client.parseDOM(results, 'table', attrs={'class': 'table2'})[0]
			rows = client.parseDOM(table, 'tr')
			if not rows: return
		except:
			source_utils.scraper_error('LIMETORRENTS')
			return

		for row in rows:
			try:
				if '<th' in row: continue
				columns = re.findall(r'<td.*?>(.+?)</td>', row, re.DOTALL)

				hash = re.search(r'/torrent/(.+?).torrent', columns[0], re.I).group(1)
				name = re.search(r'title\s*=\s*(.+?)["\']', columns[0], re.I).group(1)
				name = source_utils.clean_name(name)

				episode_start, episode_end = 0, 0
				if not self.search_series:
					if not self.bypass_filter:
						valid, episode_start, episode_end = source_utils.filter_season_pack(self.title, self.aliases, self.year, self.season_x, name)
						if not valid: continue
					package = 'season'

				elif self.search_series:
					if not self.bypass_filter:
						valid, last_season = source_utils.filter_show_pack(self.title, self.aliases, self.imdb, self.year, self.season_x, name, self.total_seasons)
						if not valid: continue
					else: last_season = self.total_seasons
					package = 'show'

				name_info = source_utils.info_from_name(name, self.title, self.year, season=self.season_x, pack=package)
				if source_utils.remove_lang(name_info, self.check_foreign_audio): continue
				if self.undesirables and source_utils.remove_undesirables(name_info, self.undesirables): continue

				url = 'magnet:?xt=urn:btih:%s&dn=%s' % (hash, name)
				try:
					seeders = int(columns[3].replace(',', ''))
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					dsize, isize = source_utils._size(columns[2])
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				item = {'provider': 'limetorrents', 'source': 'torrent', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info, 'quality': quality,
							'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'package': package}
				if self.search_series: item.update({'last_season': last_season})
				elif episode_start: item.update({'episode_start': episode_start, 'episode_end': episode_end}) # for partial season packs
				self.sources_append(item)
			except:
				source_utils.scraper_error('LIMETORRENTS')