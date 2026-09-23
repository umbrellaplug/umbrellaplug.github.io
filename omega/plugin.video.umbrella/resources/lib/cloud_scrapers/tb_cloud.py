# created by kodifitzwell (added to umbrella 12-15-2024) 
"""
	Umbrella Add-on
"""

import re
from threading import Thread
from time import time as gettime
from resources.lib.cloud_scrapers import cloud_utils
from resources.lib.database import cache
from resources.lib.debrid.torbox import TorBox
from resources.lib.modules.control import setting as getSetting
from resources.lib.modules.source_utils import supported_video_extensions
from resources.lib.modules import scrape_utils as sc_utils


def _folder_matches_show(title, aliases, folder_name, year=None):
	"""Conservative folder match: exact title or title-prefixed release name."""
	try:
		folder = cloud_utils.release_title_format(folder_name).strip('.')
		if not folder: return False
		candidates = [title] + cloud_utils.aliases_to_array(aliases)
		matched = False
		for candidate in candidates:
			candidate = cloud_utils.release_title_format(candidate).strip('.')
			if candidate and (folder == candidate or folder.startswith(candidate + '.')):
				matched = True
				break
		if not matched: return False
		folder_years = re.findall(r'(?<!\d)((?:19|20)\d{2})(?!\d)', folder_name)
		if folder_years and year and str(year) not in folder_years: return False
		return True
	except:
		return False


def _folder_contains_episode(folder_name, video_files, season, episode):
	"""Reject explicit season conflicts without excluding irregular generic packs."""
	try:
		season = int(season)
		episode = int(episode)
		normalize = lambda value: re.sub(r'[^a-z0-9]+', '.', value.lower()).strip('.')
		folder = normalize(folder_name)
		folder_seasons = {int(value) for value in re.findall(
			r'(?:^|\.)(?:s|season)[.-]?0*(\d{1,2})(?=\.|$)', folder)}
		# An explicitly labelled season pack must never leak into another season's scrape.
		if folder_seasons and season not in folder_seasons: return False
		# Generic/complete packs often use absolute episode numbers or titles rather than
		# SxxExx. Their strong show-title match is sufficient because the row is browse-only.
		if not folder_seasons: return True
		season_episode = re.compile(
			r'(?:^|\.)(?:s0*%d[.-]?e(?:p)?[.-]?0*%d|0*%dx0*%d|season[.-]?0*%d[.-]?episode[.-]?0*%d)(?=\.|$)'
			% (season, episode, season, episode, season, episode))
		if any(season_episode.search(normalize(item.get('short_name', ''))) for item in video_files):
			return True
		# A season-labelled folder may contain files named only by episode number.
		if season in folder_seasons:
			episode_only = re.compile(r'(?:^|\.)(?:e(?:p)?|episode)[.-]?0*%d(?=\.|$)' % episode)
			return any(episode_only.search(normalize(item.get('short_name', ''))) for item in video_files)
		return False
	except:
		return False


class source:
	priority = 0
	pack_capable = False # to avoid being added to pack scrape threads
	hasMovies = True
	hasEpisodes = True
	def __init__(self):
		self.language = ['en']

	def sources(self, data, hostDict):
		sources = []
		if not data: return sources
		try:
			title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
			title = title.replace('&', 'and').replace('Special Victims Unit', 'SVU')
			aliases = data['aliases']
			episode_title = data['title'] if 'tvshowtitle' in data else None
			self.year = data['year']
			hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else self.year
			self.season = str(data['season']) if 'tvshowtitle' in data else None
			self.episode = str(data['episode']) if 'tvshowtitle' in data else None
			query_list = self.episode_query_list() if 'tvshowtitle' in data else self.year_query_list()
			# log_utils.log('query_list = %s' % query_list)
			folders = []
			deadline = gettime() + 30
			threads = [
				Thread(target=self._scraper, args=(TorBox().user_cloud, folders, 'torent')),
				Thread(target=self._scraper, args=(TorBox().user_cloud_usenet, folders, 'usenet')),
				Thread(target=self._scraper, args=(TorBox().user_cloud_webdl, folders, 'webdl'))
			]
			[i.start() for i in threads]
			for t in threads:
				t.join(timeout=max(0, deadline - gettime()))
			if not folders: return sources
			extras_filter = cloud_utils.extras_filter()
		except:
			from resources.lib.modules import log_utils
			log_utils.error('TB_CLOUD: ')
			return sources

		for folder in folders:
			try:
				folder_name = folder.get('name', '')
#				if not cloud_utils.cloud_check_title(title, aliases, folder_name): continue
				mediatype = folder.get('mediatype', '')
				request_id = folder.get('id', '')
				folder_files = folder.get('files')
				if not folder_files:
					torrent_func = TorBox().user_cloud_usenet if mediatype == 'usenet' else TorBox().user_cloud
					result = torrent_func(request_id)
					if not result or not isinstance(result.get('data'), dict): continue
					folder_files = result['data'].get('files', [])
				if not folder_files: continue
			except:
				from resources.lib.modules import log_utils
				log_utils.error('TB_CLOUD: ')
				continue

			video_files = [item for item in folder_files
					if item.get('short_name', '').lower().endswith(tuple(supported_video_extensions()))]
			if ('tvshowtitle' in data and len(video_files) > 1
					and _folder_matches_show(title, aliases, folder_name, self.year)
					and _folder_contains_episode(folder_name, video_files, self.season, self.episode)):
				try:
					total_size = sum(float(item.get('size') or 0) for item in video_files)
					dsize, isize = sc_utils.convert_size(total_size, to='GB')
					average_size = dsize / len(video_files)
				except: average_size, isize = 0, ''
				quality, info = sc_utils.get_release_quality(folder_name, folder_name)
				info = [isize, 'CLOUD FOLDER', '%d FILES' % len(video_files)] + info
				sources.append({
					'provider': 'tb_cloud', 'source': 'cloud folder', 'debrid': 'TorBox',
					# A folder row is navigation, not a cache-check result. Do not attach the
					# torrent hash or direct-source dedupe can replace the matched episode.
					'seeders': '', 'hash': '', 'name': folder_name,
					'name_info': folder_name, 'quality': quality, 'language': 'en',
					'url': '%s,,%s' % (request_id, mediatype), 'info': ' / '.join(filter(None, info)),
					# Source size filters are per episode. Using the total pack size here would
					# hide large, valid show folders; the total remains visible in info above.
					'direct': True, 'debridonly': True, 'size': average_size, 'cloud_folder': True
				})

			for file in video_files:
				try:
					name = file['short_name']
					rt = cloud_utils.release_title_format(name)
					if any(value in rt for value in extras_filter): continue
					if name.endswith('m2ts'):
						continue
#						if ignoreM2ts: continue
#						name = folder_name
#						rt = cloud_utils.release_title_format(name)
#						if name in str(sources): continue
#						if all(not bool(re.search(i, rt)) for i in query_list): continue  # check if this newly added causes any movie titles that do not have the year to get dropped
#						is_m2ts = True
#						largest = sorted(folder_files, key=lambda k: k['bytes'], reverse=True)[0]
#						index_pos = folder_files.index(largest)
#						size = largest['bytes']
#						try: link = torrent_info['links'][index_pos]
#						except: link = torrent_info['links'][0]
					else:
						if all(not bool(re.search(i, rt)) for i in query_list):
							if 'tvshowtitle' in data:
								season_folder_list = self.season_folder_list()
								nl = name.lower()
								if all(not bool(re.search(i, nl)) for i in season_folder_list): continue
								episode_list = self.episode_list()
								if all(not bool(re.search(i, rt)) for i in episode_list): continue
							else:
								if all(not bool(re.search(i, folder_name)) for i in query_list): continue
								name = folder_name

#						name = name.split('/')
#						name = name[len(name)-1]
#						index_pos = folder_files.index(file)
#						link = torrent_info['links'][index_pos]
						link = '%d,%d,%s' % (int(request_id), file['id'], mediatype)
						size = file.get('size', '')

					if not (
						cloud_utils.cloud_check_title(title, aliases, name)
						or # because usenet obfuscation
						cloud_utils.cloud_check_title(title, aliases, folder_name)
					): continue
					name_info = sc_utils.info_from_name(name, title, self.year, hdlr, episode_title)
					hash = folder.get('hash', '')
					quality, info = sc_utils.get_release_quality(name_info, name)
					try:
						dsize, isize = sc_utils.convert_size(size, to='GB')
						info.insert(0, isize)
					except: dsize = 0
					info = ' / '.join(info)

					sources.append({'provider': 'tb_cloud', 'source': 'cloud', 'debrid': 'TorBox', 'seeders': '', 'hash': hash, 'name': name, 'name_info': name_info,
												'quality': quality, 'language': 'en', 'url': link, 'info': info, 'direct': True, 'debridonly': True, 'size': dsize})
				except:
					from resources.lib.modules import log_utils
					log_utils.error('TB_CLOUD: ')
					continue
		return sources

	def year_query_list(self):
		return [str(self.year), str(int(self.year)+1), str(int(self.year)-1)] if self.year else []

	def episode_query_list(self):
		return [
				'[.-]%d[.-]?%02d[.-]' % (int(self.season), int(self.episode)),
				'[.-]%02d[.-]%02d[.-]' % (int(self.season), int(self.episode)),
				'[.-]%dx%02d[.-]' % (int(self.season), int(self.episode)),
				'[.-]%02dx%02d[.-]' % (int(self.season), int(self.episode)),
				's%de%02d' % (int(self.season), int(self.episode)),
				's%02de%02d' % (int(self.season), int(self.episode)),
				's%dep%02d' % (int(self.season), int(self.episode)),
				's%02dep%02d' % (int(self.season), int(self.episode)),
				'season%depisode%d' % (int(self.season), int(self.episode)),
				'season%depisode%02d' % (int(self.season), int(self.episode)),
				'season%02depisode%02d' % (int(self.season), int(self.episode))]

	def season_folder_list(self):
		return [
				r'[.-]s\s?%d[\s/.-]' % int(self.season),
				r'[.-]s\s?%02d[\s/.-]' % int(self.season),
				r'season\s?%d[\s/.-]' % int(self.season),
				r'season\s?%02d[\s/.-]' % int(self.season)]

	def episode_list(self): # checks against formatted release_title with removed whitespace
		return [
				'[.-]e%d[.-]' % int(self.episode),
				'[.-]e%02d[.-]' % int(self.episode),
				'[.-]ep%d[.-]' % int(self.episode),
				'[.-]ep%02d[.-]' % int(self.episode),
				'episode[.-]?%d[.-]' % int(self.episode),
				'episode[.-]?%02d[.-]' % int(self.episode)]

	def resolve(self, url):
		try:
			url, mediatype = url.rsplit(',', 1)
			if mediatype == 'usenet': url = cache.get(TorBox().unrestrict_usenet, 1, url)
			else: url = cache.get(TorBox().unrestrict_link, 1, url)
			return url
		except:
			from resources.lib.modules import log_utils
			log_utils.error('TB_CLOUD: ')
			return None

	def _scraper(self, function, results, mediatype):
		try:
			response = function()
			if not response: return
			items = [{**i, 'mediatype': mediatype} for i in (response.get('data') or []) if i.get('download_finished') or i.get('download_state') == 'completed']
			results += items
		except:
			from resources.lib.modules import log_utils
			log_utils.error('TB_CLOUD: ')
