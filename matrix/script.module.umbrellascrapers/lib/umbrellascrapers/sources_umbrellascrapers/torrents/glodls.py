# -*- coding: utf-8 -*-
# modified by umbrealla for umbrellascrapers (updated 6-20-2022)
"""
	umbrellascrapers Project
"""

import re
from urllib.parse import quote_plus, unquote_plus
from umbrellascrapers.modules import client
from umbrellascrapers.modules import source_utils
from umbrellascrapers.modules import workers


class source:
	priority = 3
	pack_capable = True
	hasMovies = True
	hasEpisodes = True
	def __init__(self):
		self.language = ['en']
		self.base_link = "https://www.gtdb.to"
		self.moviesearch = '/search_results.php?search={0}&cat=1&incldead=0&inclexternal=0&lang=1&sort=size&order=desc'
		self.tvsearch = '/search_results.php?search={0}&cat=41&incldead=0&inclexternal=0&lang=1&sort=seeders&order=desc'
		self.tvsearch_pack = '/search_results.php?search={0}&cat=41,72&incldead=0&inclexternal=0&lang=1&sort=seeders&order=desc' # cat=72 timeout
		# cat=1 is (Movies:all) ; cat=41 is (TV:all) ; cat=71 is (Videos:all) ; cat=72 is (Packs:all)
		self.min_seeders = 0 # to many items with no value but cached links

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
			query = re.sub(r'[^A-Za-z0-9\s\.-]+', '', query)
			if 'tvshowtitle' in data: url = self.tvsearch.format(quote_plus(query))
			else: url = self.moviesearch.format(quote_plus(query))
			url = '%s%s' % (self.base_link, url)
			# log_utils.log('url = %s' % url)
			result = client.request(url, timeout=10)
			if not result: return sources
			rows = client.parseDOM(result, 'tr', attrs={'class': 't-row'})
			if not rows: return sources
			rows = [i for i in rows if 'racker:' not in i]
			undesirables = source_utils.get_undesirables()
			check_foreign_audio = source_utils.check_foreign_audio()
		except:
			source_utils.scraper_error('GLODLS')
			return sources

		for row in rows:
			try:
				columns = re.findall(r'<td.*?>(.+?)</td>', row, re.DOTALL)

				url = unquote_plus(columns[3]).replace('&amp;', '&')
				url = re.search(r'(magnet:.+?)&tr=', url, re.I).group(1).replace(' ', '.')
				hash = re.search(r'btih:(.*?)&', url, re.I).group(1)
				name = client.parseDOM(columns[1], 'a', ret='title')[0].replace('/', '').replace('  ', ' ')

				if not source_utils.check_title(title, aliases, name, hdlr, year): continue
				name_info = source_utils.info_from_name(name, title, year, hdlr, episode_title)
				if source_utils.remove_lang(name_info, check_foreign_audio): continue
				if undesirables and source_utils.remove_undesirables(name_info, undesirables): continue

				if not episode_title: #filter for eps returned in movie query (rare but movie and show exists for Run in 2020)
					ep_strings = [r'[.-]s\d{2}e\d{2}([.-]?)', r'[.-]s\d{2}([.-]?)', r'[.-]season[.-]?\d{1,2}[.-]?']
					name_lower = name.lower()
					if any(re.search(item, name_lower) for item in ep_strings): continue

				try:
					seeders = int(re.search(r'>(\d+|\d+\,\d+)<', columns[5]).group(1).replace(',', ''))
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					dsize, isize = source_utils._size(columns[4])
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				append({'provider': 'glodls', 'source': 'torrent', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info,
							'quality': quality, 'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize})
			except:
				source_utils.scraper_error('GLODLS')
		return sources

	def sources_packs(self, data, hostDict, search_series=False, total_seasons=None, bypass_filter=False):
		self.sources = []
		if not data: return self.sources
		self.sources_append = self.sources.append
		try:
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
						self.tvsearch_pack.format(quote_plus(query + ' Season')),
						self.tvsearch_pack.format(quote_plus(query + ' Complete'))]
			else:
				queries = [
						self.tvsearch_pack.format(quote_plus(query + ' S%s' % self.season_xx)),
						self.tvsearch_pack.format(quote_plus(query + ' Season %s' % self.season_x))]
			threads = []
			append = threads.append
			for url in queries:
				link = '%s%s' % (self.base_link, url)
				append(workers.Thread(self.get_sources_packs, link))
			[i.start() for i in threads]
			[i.join() for i in threads]
			return self.sources
		except:
			source_utils.scraper_error('GLODLS')
			return self.sources

	def get_sources_packs(self, link):
		try:
			result = client.request(link, timeout=10)
			if not result: return
			rows = client.parseDOM(result, 'tr', attrs={'class': 't-row'})
			if not rows: return
			rows = [i for i in rows if 'racker:' not in i]
		except:
			source_utils.scraper_error('GLODLS')
			return

		for row in rows:
			try:
				columns = re.findall(r'<td.*?>(.+?)</td>', row, re.DOTALL)
				url = unquote_plus(columns[3]).replace('&amp;', '&')
				url = re.search(r'(magnet:.+?)&tr=', url, re.I).group(1).replace(' ', '.')
				hash = re.search(r'btih:(.*?)&', url, re.I).group(1)
				name = client.parseDOM(columns[1], 'a', ret='title')[0].replace('/', '').replace('  ', ' ') # glotorrents seems to fix incomplete packs as a range in html title tag

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
				try:
					seeders = int(re.search(r'>(\d+|\d+\,\d+)<', columns[5]).group(1).replace(',', ''))
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					dsize, isize = source_utils._size(columns[4])
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				item = {'provider': 'glodls', 'source': 'torrent', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info, 'quality': quality,
							'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'package': package}
				if self.search_series: item.update({'last_season': last_season})
				elif episode_start: item.update({'episode_start': episode_start, 'episode_end': episode_end}) # for partial season packs
				self.sources_append(item)
			except:
				source_utils.scraper_error('GLODLS')