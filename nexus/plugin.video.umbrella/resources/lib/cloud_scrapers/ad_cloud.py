# -*- coding: utf-8 -*-
# created by Umbrella (updated 4-03-2022)
"""
	Umbrella Add-on
"""

import re
from resources.lib.cloud_scrapers import cloud_utils
from resources.lib.database import cache
from resources.lib.debrid.alldebrid import AllDebrid
from resources.lib.modules.control import setting as getSetting
# from resources.lib.modules.source_utils import supported_video_extensions
from resources.lib.modules import scrape_utils as sc_utils

invalid_extensions = ('.bmp', '.gif', '.jpg', '.nfo', '.part', '.png', '.rar', '.sample.', '.srt', '.txt', '.zip')

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

			ad = AllDebrid()  # reuse one instance

			try:
				cloud_folders = ad.user_cloud()['magnets']
			except:
				return sources
			if not cloud_folders: return sources
			cloud_folders = [i for i in cloud_folders if i.get('statusCode') == 4]
			if not cloud_folders: return sources

			ignoreM2ts = getSetting('ad_cloud.ignore.m2ts') == 'true'
			extras_filter = cloud_utils.extras_filter()

			mf_local = {}        # magnet_id -> files_tree
			unlock_local = {}    # link -> unlock_info
			seen = set()         # (link, name) to dedup results

			def get_magnet_tree(magnet_id):
				if magnet_id in mf_local:
					return mf_local[magnet_id]
				tree = cache.get(ad._get_magnet_files, 48, magnet_id) or []
				mf_local[magnet_id] = tree
				return tree

			def unlock_info(link):
				if not link:
					return {}
				if link in unlock_local:
					return unlock_local[link]
				info = cache.get(ad.unrestrict_link, 48, link, True) or {}
				unlock_local[link] = info
				return info

			def _flatten(tree, prefix=''):
				for node in (tree or []):
					n = node.get('n')
					if not n: 
						continue
					if 'e' in node:  # folder
						new_prefix = (prefix + '/' + n) if prefix else n
						for x in _flatten(node.get('e', []), new_prefix):
							yield x
					else:            # file
						yield {
							'filename': n,
							'size': int(node.get('s') or 0),
							'link': node.get('l') or '',
							'path': prefix.lower() if prefix else ''
						}

		except:
			from resources.lib.modules import log_utils
			log_utils.error('AD_CLOUD: ')
			return sources

		for folder in cloud_folders:
			is_m2ts = False
			try:
				folder_name = folder.get('filename', '')
				if not cloud_utils.cloud_check_title(title, aliases, folder_name):
					continue

				files_tree = get_magnet_tree(folder.get('id'))
				flat_files = list(_flatten(files_tree))
				files = [i for i in flat_files if not i['filename'].lower().endswith(invalid_extensions)]
				if not files:
					continue

				path = folder_name.lower()
			except:
				from resources.lib.modules import log_utils
				log_utils.error('AD_CLOUD: ')
				return sources

			for file in files:
				try:
					name = file.get('filename', '') or ''
					if name.lower().endswith(invalid_extensions):
						continue

					rt = cloud_utils.release_title_format(name)
					if any(value in rt for value in extras_filter):
						continue

					# m2ts handling
					if '.m2ts' in name.lower():
						if ignoreM2ts:
							continue
						same_name = [i for i in files if i.get('filename') == name]
						largest = max(same_name, key=lambda k: int(k.get('size') or 0)) if same_name else file
						link = largest.get('link', '')
						size = int(largest.get('size') or 0)
						if (link, name) in seen:
							continue
						if all(not bool(re.search(i, rt)) for i in query_list):
							continue
						is_m2ts = True
					else:
						# enforce matching logic for shows vs movies
						if all(not bool(re.search(i, rt)) for i in query_list):
							if 'tvshowtitle' in data:
								season_folder_list = self.season_folder_list()
								file_path = (file.get('path') or '')
								if any(bool(re.search(i, file_path)) for i in season_folder_list):
									episode_list = self.episode_list()
									if name != folder_name:
										if all(not bool(re.search(i, rt)) for i in episode_list):
											continue
									else:
										li = unlock_info(file.get('link', ''))
										name2 = li.get('filename', '')
										if name2:
											if name2.lower().endswith(invalid_extensions):
												continue
											rt2 = cloud_utils.release_title_format(name2)
											if any(value in rt2 for value in extras_filter):
												continue
											if all(not bool(re.search(i, rt2)) for i in query_list):
												continue
											name = name2
											file['size'] = int(li.get('filesize') or file.get('size') or 0)
								else:
									continue
							else:
								file_path = (file.get('path') or '')
								if all(not bool(re.search(i, file_path)) for i in query_list):
									if rt.startswith('.etrg.'):
										continue
									name = folder.get('filename', '') or name

						link = file.get('link', '') or ''
						size = int(file.get('size') or 0)

					if (link, name) in seen:
						continue
					seen.add((link, name))

					name_info = sc_utils.info_from_name(name, title, self.year, hdlr, episode_title)
					hash_ = folder.get('hash', '')
					seeders = folder.get('seeders', '')

					quality, info = sc_utils.get_release_quality(name_info, name)
					try:
						dsize, isize = sc_utils.convert_size(size, to='GB')
						info.insert(0, isize)
					except:
						dsize = 0
					if is_m2ts:
						info.append('M2TS')
					info = ' / '.join(info)

					sources.append({
						'provider': 'ad_cloud',
						'source': 'cloud',
						'debrid': 'AllDebrid',
						'seeders': seeders,
						'hash': hash_,
						'name': name,
						'name_info': name_info,
						'quality': quality,
						'language': 'en',
						'url': link,
						'info': info,
						'direct': True,
						'debridonly': True,
						'size': dsize
					})
				except:
					from resources.lib.modules import log_utils
					log_utils.error('AD_CLOUD: ')
					return sources

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
			url = cache.get(AllDebrid().unrestrict_link, 48, url)
			return url
		except:
			from resources.lib.modules import log_utils
			log_utils.error('AD_CLOUD: ')
			return None