# -*- coding: utf-8 -*-
# modified by   for Umbrellascrapers (updated 3-30-2022)
"""
	Umbrellascrapers Project
"""

import re
from urllib.parse import quote_plus, unquote_plus
from umbrellascrapers.modules import client
from umbrellascrapers.modules import source_utils


class source:
	priority = 3
	pack_capable = True
	hasMovies = False
	hasEpisodes = True
	def __init__(self):
		self.language = ['en']
		self.base_link = "https://eztv.wf"
		# eztv has api but it sucks. Site query returns more results vs. api (eztv db seems to be missing the imdb_id for many so they are dropped)
		self.search_link = '/search/%s'
		self.min_seeders = 0

	def sources(self, data, hostDict):
		sources = []
		if not data: return sources
		sources_append = sources.append
		try:
			title = data['tvshowtitle'].replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
			aliases = data['aliases']
			episode_title = data['title']
			year = data['year']
			hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode']))

			query = '%s %s' % (title, hdlr)
			# query = re.sub(r'[^A-Za-z0-9\s\.-]+', '', query) #eztv has issues with dashes in titles
			query = re.sub(r'[^A-Za-z0-9\s\.]+', '', query)
			url = self.search_link % quote_plus(query).replace('+', '-')
			url = '%s%s' % (self.base_link, url)
			# log_utils.log('url = %s' % url)
			results = client.request(url, timeout=5)
			if not results: return sources
			rows = client.parseDOM(results, 'tr')
			if not rows: return sources
			undesirables = source_utils.get_undesirables()
			check_foreign_audio = source_utils.check_foreign_audio()
		except:
			source_utils.scraper_error('EZTV')
			return sources

		for row in rows:
			try:
				if 'magnet:' not in row: continue
				try:
					columns = re.findall(r'<td\s.+?>(.*?)</td>', row, re.DOTALL)
					link = re.findall(r'href\s*=\s*["\'](magnet:[^"\']+)["\'].*?title\s*=\s*["\'](.+?)["\']', columns[2], re.DOTALL | re.I)[0]
				except: continue

				url = unquote_plus(client.replaceHTMLCodes(link[0])).split('&tr')[0]
				hash = re.search(r'btih:(.*?)(?:&|$)', url, re.I).group(1)
				if len(hash) != 40: # eztv has some base32 encoded hashes
					from umbrellascrapers.modules import log_utils
					hash = source_utils.base32_to_hex(hash, 'EZTV')
					log_utils.log('url with base32 hash:  "%s" ' % url, __name__, log_utils.LOGDEBUG)
					url = re.sub(re.search(r'btih:(.*?)(?:&|$)', url).group(1), hash, url)
					log_utils.log('url converted to hex40 hash:  "%s" ' % url, __name__, log_utils.LOGDEBUG)

				name = ''.join(link[1].partition('[eztv]')[:2]).replace(' Torrent: Magnet Link', '')
				name = source_utils.clean_name(name)

				if not source_utils.check_title(title, aliases, name, hdlr, year): continue
				name_info = source_utils.info_from_name(name, title, year, hdlr, episode_title)
				if source_utils.remove_lang(name_info, check_foreign_audio): continue
				if undesirables and source_utils.remove_undesirables(name_info, undesirables): continue

				try:
					seeders = int(re.search(r'>(\d+|\d+\,\d+)<', columns[5]).group(1).replace(',', ''))
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					dsize, isize = source_utils._size(columns[3])
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				sources_append({'provider': 'eztv', 'source': 'torrent', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info,
								'quality': quality, 'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize})
			except:
				source_utils.scraper_error('EZTV')
		return sources

	def sources_packs(self, data, hostDict, search_series=False, total_seasons=None, bypass_filter=False):
		sources = []
		if search_series: return sources # eztz does not have showPacks
		if not data: return sources
		sources_append = sources.append
		try:
			title = data['tvshowtitle'].replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
			aliases = data['aliases']
			year = data['year']
			season_x = data['season']
			season_xx = season_x.zfill(2)

			# query = re.sub(r'[^A-Za-z0-9\s\.-]+', '', title) #eztv has issues with dashes in titles
			query = re.sub(r'[^A-Za-z0-9\s\.]+', '', title)
			url = self.search_link % quote_plus(query + ' S%s' % season_xx).replace('+', '-')
			url = '%s%s' % (self.base_link, url)
			results = client.request(url, timeout=5)
			if not results: return
			rows = client.parseDOM(results, 'tr')
			if not rows: return
			undesirables = source_utils.get_undesirables()
			check_foreign_audio = source_utils.check_foreign_audio()
		except:
			source_utils.scraper_error('EZTV')
			return sources

		for row in rows:
			try:
				if 'magnet:' not in row: continue
				try:
					columns = re.findall(r'<td\s.+?>(.*?)</td>', row, re.DOTALL)
					link = re.findall(r'href\s*=\s*["\'](magnet:[^"\']+)["\'].*?title\s*=\s*["\'](.+?)["\']', columns[2], re.DOTALL | re.I)[0]
				except: continue

				url = unquote_plus(client.replaceHTMLCodes(link[0])).split('&tr')[0]
				hash = re.search(r'btih:(.*?)(?:&|$)', url, re.I).group(1)
				if len(hash) != 40: # eztv has some base32 encoded hashes
					from umbrellascrapers.modules import log_utils
					hash = source_utils.base32_to_hex(hash, 'EZTV')
					log_utils.log('url with base32 hash:  "%s" ' % url, __name__, log_utils.LOGDEBUG)
					url = re.sub(re.search(r'btih:(.*?)(?:&|$)', url).group(1), hash, url)
					log_utils.log('url converted to hex40 hash:  "%s" ' % url, __name__, log_utils.LOGDEBUG)

				name = ''.join(link[1].partition('[eztv]')[:2]).replace(' Torrent: Magnet Link', '')
				name = source_utils.clean_name(name)

				episode_start, episode_end = 0, 0
				if not bypass_filter:
					valid, episode_start, episode_end = source_utils.filter_season_pack(title, aliases, year, season_x, name)
					if not valid: continue
				package = 'season'

				name_info = source_utils.info_from_name(name, title, year, season=season_x, pack=package)
				if source_utils.remove_lang(name_info, check_foreign_audio): continue
				if undesirables and source_utils.remove_undesirables(name_info, undesirables): continue
				try:
					seeders = int(re.search(r'>(\d+|\d+\,\d+)<', columns[5]).group(1).replace(',', ''))
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					dsize, isize = source_utils._size(columns[3])
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				item = {'provider': 'eztv', 'source': 'torrent', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info, 'quality': quality,
							'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'package': package}
				if episode_start: item.update({'episode_start': episode_start, 'episode_end': episode_end}) # for partial season packs
				sources_append(item)
			except:
				source_utils.scraper_error('EZTV')
		return sources