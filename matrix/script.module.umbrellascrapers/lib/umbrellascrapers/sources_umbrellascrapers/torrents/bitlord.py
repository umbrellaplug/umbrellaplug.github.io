# -*- coding: utf-8 -*-
# created by   for Umbrellascrapers (updated 3-02-2022)
"""
	Umbrellascrapers Project
"""

from json import loads as jsloads
import re
from urllib.parse import quote_plus, unquote_plus
from umbrellascrapers.modules import cache
from umbrellascrapers.modules import client
from umbrellascrapers.modules import source_utils
from umbrellascrapers.modules import workers


class source:
	priority = 2
	pack_capable = True
	hasMovies = True
	hasEpisodes = True
	def __init__(self):
		self.language = ['en']
		self.base_link = "http://www.bitlordsearch.com"
		self.search_link = '/search?q=%s'
		self.api_search_link = '/get_list'
		self.min_seeders = 0

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
			url = '%s%s' % (self.base_link, self.search_link % quote_plus(query))
			# log_utils.log('url = %s' % url)
			api_url = '%s%s' % (self.base_link, self.api_search_link)
			headers = cache.get(self._get_token_and_cookies, 1)
			if not headers: return sources
			headers.update({'Referer': url})
			query_data = {
				'query': query,
				'offset': 0,
				'limit': 99,
				'filters[field]': 'seeds',
				'filters[sort]': 'desc',
				'filters[time]': 4,
				'filters[category]': 3 if 'tvshowtitle' not in data else 4,
				'filters[adult]': False,
				'filters[risky]': False}
			results = client.request(api_url, post=query_data, headers=headers, timeout=5)
			if not results: return sources
			files = jsloads(results)
			if files.get('error'): return sources
			undesirables = source_utils.get_undesirables()
			check_foreign_audio = source_utils.check_foreign_audio()
		except:
			source_utils.scraper_error('BITLORD')
			return sources

		for file in files.get('content'):
			try:
				name = source_utils.clean_name(file.get('name'))
				if not source_utils.check_title(title, aliases, name, hdlr, year): continue
				name_info = source_utils.info_from_name(name, title, year, hdlr, episode_title)
				if source_utils.remove_lang(name_info, check_foreign_audio): continue
				if undesirables and source_utils.remove_undesirables(name_info, undesirables): continue

				url = unquote_plus(file.get('magnet')).replace('&amp;', '&').replace(' ', '.')
				url = re.sub(r'(&tr=.+)&dn=', '&dn=', url) # some links on bitlord &tr= before &dn=
				url = url.split('&tr=')[0].split('&xl=')[0]
				hash = re.search(r'btih:(.*?)&', url, re.I).group(1)

				if not episode_title: #filter for eps returned in movie query (rare but movie and show exists for Run in 2020)
					ep_strings = [r'[.-]s\d{2}e\d{2}([.-]?)', r'[.-]s\d{2}([.-]?)', r'[.-]season[.-]?\d{1,2}[.-]?']
					name_lower = name.lower()
					if any(re.search(item, name_lower) for item in ep_strings): continue

				try:
					seeders = file.get('seeds')
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					size = file.get('size')
					size = str(size) + ' GB' if len(str(size)) <= 2 else str(size) + ' MB' # bitlord size is all over the place between MB and GB
					dsize, isize = source_utils._size(size)
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				append({'provider': 'bitlord', 'source': 'torrent', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info,
								'quality': quality, 'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize})
			except:
				source_utils.scraper_error('BITLORD')
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
			self.headers = cache.get(self._get_token_and_cookies, 1)

			query = re.sub(r'[^A-Za-z0-9\s\.-]+', '', self.title)
			if search_series:
				queries = [
						quote_plus(query + ' Season'),
						quote_plus(query + ' Complete')]
			else:
				queries = [
						quote_plus(query + ' S%s' % self.season_xx),
						quote_plus(query + ' Season %s' % self.season_x)]
			threads = []
			append = threads.append
			for url in queries:
				link = ('%s%s' % (self.base_link, self.search_link % url)).replace('+', '-')
				append(workers.Thread(self.get_sources_packs, link, url.replace('+', '-')))
			[i.start() for i in threads]
			[i.join() for i in threads]
			return self.sources
		except:
			source_utils.scraper_error('BITLORD')
			return self.sources

	def get_sources_packs(self, link, url):
		try:
			self.headers.update({'Referer': link})
			query_data = {
				'query': url,
				'offset': 0,
				'limit': 99,
				'filters[field]': 'seeds',
				'filters[sort]': 'desc',
				'filters[time]': 4,
				'filters[category]': 4,
				'filters[adult]': False,
				'filters[risky]': False}
			api_url = '%s%s' % (self.base_link, self.api_search_link)
			rjson = client.request(api_url, post=query_data, headers=self.headers, timeout=5)
			if not rjson: return
			files = jsloads(rjson)
			if files.get('error'): return
		except:
			source_utils.scraper_error('BITLORD')
			return

		for file in files.get('content'):
			try:
				name = source_utils.clean_name(file.get('name'))
				url = unquote_plus(file.get('magnet')).replace('&amp;', '&').replace(' ', '.')
				url = re.sub(r'(&tr=.+)&dn=', '&dn=', url) # some links on bitlord &tr= before &dn=
				url = url.split('&tr=')[0].split('&xl=')[0]
				hash = re.search(r'btih:(.*?)&', url, re.I).group(1)

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
					seeders = file.get('seeds')
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					size = file.get('size')
					size = str(size) + ' GB' if len(str(size)) <= 2 else str(size) + ' MB' # bitlord size is all over the place between MB and GB
					dsize, isize = source_utils._size(size)
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				item = {'provider': 'bitlord', 'source': 'torrent', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info, 'quality': quality,
							'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'package': package}
				if self.search_series: item.update({'last_season': last_season})
				elif episode_start: item.update({'episode_start': episode_start, 'episode_end': episode_end}) # for partial season packs
				self.sources_append(item)
			except:
				source_utils.scraper_error('BITLORD')

	def _get_token_and_cookies(self):
		headers = None
		try:
			# returned from client (result, response_code, response_headers, headers, cookie)
			post = client.request(self.base_link, output='extended', timeout=10)
			if not post: return headers
			token_id = re.findall(r'token\: (.*)\n', post[0])[0]
			token = ''.join(re.findall(token_id + r" ?\+?\= ?'(.*)'", post[0]))
			headers = post[3]
			headers.update({'Cookie': post[4].replace('SameSite=Lax, ', ''), 'X-Request-Token': token})
			return headers
		except:
			source_utils.scraper_error('BITLORD')
			return headers