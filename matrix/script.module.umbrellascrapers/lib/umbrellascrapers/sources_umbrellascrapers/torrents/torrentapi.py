# -*- coding: utf-8 -*-
# modified by   for Umbrellascrapers (updated 3-02-2022)
"""
	Umbrellascrapers Project
"""

import re
from urllib.parse import unquote_plus
from umbrellascrapers.modules import cache
from umbrellascrapers.modules import cfscrape
from umbrellascrapers.modules import source_utils
from umbrellascrapers.modules import workers


class source:
	priority = 1
	pack_capable = True
	hasMovies = True
	hasEpisodes = True

	def __init__(self):
		self.language = ['en']
		self.base_link = "https://torrentapi.org" # just to satisfy scraper_test
		self.tvsearch = 'https://torrentapi.org/pubapi_v2.php?app_id=Torapi&token={0}&mode=search&search_string={1}&ranked=0&limit=100&format=json_extended' # string query (NOT USED)
		self.tvshowsearch = 'https://torrentapi.org/pubapi_v2.php?app_id=Torapi&token={0}&mode=search&search_imdb={1}&search_string={2}&ranked=0&limit=100&format=json_extended' # imdb_id + string query
		self.msearch = 'https://torrentapi.org/pubapi_v2.php?app_id=Torapi&token={0}&mode=search&search_imdb={1}&ranked=0&limit=100&format=json_extended'
		self.getToken_url = 'https://torrentapi.org/pubapi_v2.php?app_id=Torapi&get_token=get_token'
		self.min_seeders = 0

	def _get_token(self):
		token = '3qk6aj27ws'
		try:
			token = self.scraper.get(self.getToken_url).json()
			token = token['token']
		except: pass
		return token

	def sources(self, data, hostDict):
		sources = []
		if not data: return sources
		append = sources.append
		try:
			self.scraper = cfscrape.create_scraper()
			key = cache.get(self._get_token, 0.2) # 800 secs token is valid for

			title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
			title = title.replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
			aliases = data['aliases']
			episode_title = data['title'] if 'tvshowtitle' in data else None
			year = data['year']
			hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else year

			query = '%s %s' % (title, hdlr)
			query = re.sub(r'[^A-Za-z0-9\s\.-]+', '', query)
			if 'tvshowtitle' in data:
				search_link = self.tvshowsearch.format(key, data['imdb'], hdlr)
			else:
				search_link = self.msearch.format(key, data['imdb'])
			# log_utils.log('search_link = %s' % str(search_link))
			rjson = self.scraper.get(search_link, timeout=5)
			if rjson.status_code == 200: rjson = rjson.json()
			else: return sources
			if 'torrent_results' not in rjson: return sources
			files = rjson['torrent_results']
			undesirables = source_utils.get_undesirables()
			check_foreign_audio = source_utils.check_foreign_audio()
		except:
			source_utils.scraper_error('TORRENTAPI')
			return sources

		for file in files:
			try:
				url = file["download"].split('&tr')[0]
				hash = re.search(r'btih:(.*?)&', url, re.I).group(1)
				name = source_utils.clean_name(unquote_plus(file["title"]))

				if not source_utils.check_title(title, aliases, name, hdlr, year): continue
				name_info = source_utils.info_from_name(name, title, year, hdlr, episode_title)
				if source_utils.remove_lang(name_info, check_foreign_audio): continue
				if undesirables and source_utils.remove_undesirables(name_info, undesirables): continue

				if not episode_title: #filter for eps returned in movie query (rare but movie and show exists for Run in 2020)
					ep_strings = [r'[.-]s\d{2}e\d{2}([.-]?)', r'[.-]s\d{2}([.-]?)', r'[.-]season[.-]?\d{1,2}[.-]?']
					name_lower = name.lower()
					if any(re.search(item, name_lower) for item in ep_strings): continue

				try:
					seeders = int(file["seeders"])
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					dsize, isize = source_utils.convert_size(file["size"], to='GB')
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				append({'provider': 'torrentapi', 'source': 'torrent', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info,
								'quality': quality, 'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize})
			except:
				source_utils.scraper_error('TORRENTAPI')
		return sources

	def sources_packs(self, data, hostDict, search_series=False, total_seasons=None, bypass_filter=False):
		sources = []
		if search_series: return sources # torrentapi does not have showPacks
		if not data: return sources
		sources_append = sources.append
		try:
			self.scraper = cfscrape.create_scraper()
			key = cache.get(self._get_token, 0.2) # 800 secs token is valid for

			title = data['tvshowtitle'].replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
			aliases = data['aliases']
			year = data['year']
			season = data['season']
			season_xx = season.zfill(2)

			search_link = self.tvshowsearch.format(key, data['imdb'], 'S%s' % season_xx)
			rjson = self.scraper.get(search_link, timeout=5)
			if rjson.status_code == 200: rjson = rjson.json()
			else: return sources
			if 'torrent_results' not in rjson: return sources
			files = rjson['torrent_results']
			undesirables = source_utils.get_undesirables()
			check_foreign_audio = source_utils.check_foreign_audio()
		except:
			source_utils.scraper_error('TORRENTAPI')
			return sources

		for file in files:
			try:
				url = file["download"].split('&tr')[0]
				hash = re.search(r'btih:(.*?)&', url, re.I).group(1)
				name = source_utils.clean_name(unquote_plus(file["title"]))

				episode_start, episode_end = 0, 0
				if not bypass_filter:
					valid, episode_start, episode_end = source_utils.filter_season_pack(title, aliases, year, season, name)
					if not valid: continue
				package = 'season'

				name_info = source_utils.info_from_name(name, title, year, season=season, pack=package)
				if source_utils.remove_lang(name_info, check_foreign_audio): continue
				if undesirables and source_utils.remove_undesirables(name_info, undesirables): continue
				try:
					seeders = int(file["seeders"])
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					dsize, isize = source_utils.convert_size(file["size"], to='GB')
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				item = {'provider': 'torrentapi', 'source': 'torrent', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info, 'quality': quality,
								'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'package': package}
				if episode_start: item.update({'episode_start': episode_start, 'episode_end': episode_end}) # for partial season packs
				sources_append(item)
			except:
				source_utils.scraper_error('TORRENTAPI')
		return sources