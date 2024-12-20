# created by kodifitzwell (imported to umbrella 12-17-2024)
"""
	Umbrella Add-on
"""

import re
from resources.lib.cloud_scrapers import cloud_utils
from resources.lib.debrid.offcloud import Offcloud
from resources.lib.modules.control import setting as getSetting
from resources.lib.modules.source_utils import supported_video_extensions
from resources.lib.modules import scrape_utils as sc_utils


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
			cloud_folders = Offcloud().user_cloud()
			if not cloud_folders: return sources
			cloud_folders = [i for i in cloud_folders if i['status'] == 'downloaded']
			if not cloud_folders: return sources
			extras_filter = cloud_utils.extras_filter()
		except:
			from resources.lib.modules import log_utils
			log_utils.error('OC_CLOUD: ')
			return sources

		for folder in cloud_folders:
			try:
				folder_name = folder.get('fileName', '')
				if not cloud_utils.cloud_check_title(title, aliases, folder_name): continue
				request_id = folder.get('requestId', '')
				if not folder['isDirectory']: folder_files = [Offcloud().build_url(folder['server'], folder['requestId'], folder['fileName'])]
				else: folder_files = Offcloud().torrent_info(request_id)
			except:
				from resources.lib.modules import log_utils
				log_utils.error('OC_CLOUD: ')
				return sources

			for file in folder_files:
				try:
					name = file.split('/')[-1]
					rt = cloud_utils.release_title_format(name)
					if not name.lower().endswith(tuple(supported_video_extensions())): continue
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
#						size = file.get('bytes', '')
						link = Offcloud().requote_uri(file)
						size = ''

					name_info = sc_utils.info_from_name(name, title, self.year, hdlr, episode_title)
#					hash = folder.get('hash', '')
					hash = ''
					quality, info = sc_utils.get_release_quality(name_info, name)
					try:
						dsize, isize = sc_utils.convert_size(size, to='GB')
						info.insert(0, isize)
					except: dsize = 0
					info = ' / '.join(info)

					sources.append({'provider': 'oc_cloud', 'source': 'cloud', 'debrid': 'Offcloud', 'seeders': '', 'hash': hash, 'name': name, 'name_info': name_info,
												'quality': quality, 'language': 'en', 'url': link, 'info': info, 'direct': True, 'debridonly': True, 'size': dsize})
				except:
					from resources.lib.modules import log_utils
					log_utils.error('OC_CLOUD: ')
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
#			url = cache.get(Offcloud().unrestrict_link, 48, url)
			return url
		except:
			from resources.lib.modules import log_utils
			log_utils.error('OC_CLOUD: ')
			return None
