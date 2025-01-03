# -*- coding: utf-8 -*-
# Thanks to kodifitzwell for allowing me to borrow his code
from threading import Thread
from apis.offcloud_api import OffcloudAPI
from modules import source_utils
from modules.utils import clean_file_name, normalize
from modules.settings import enabled_debrids_check, filter_by_name
# from modules.kodi_utils import logger

internal_results, check_title, clean_title = source_utils.internal_results, source_utils.check_title, source_utils.clean_title
get_file_info, release_info_format, seas_ep_filter = source_utils.get_file_info, source_utils.release_info_format, source_utils.seas_ep_filter
Offcloud = OffcloudAPI()
extensions = source_utils.supported_video_extensions()

class source:
	def __init__(self):
		self.scrape_provider = 'oc_cloud'
		self.sources = []

	def results(self, info):
		try:
			if not enabled_debrids_check('oc'): return internal_results(self.scrape_provider, self.sources)
			self.scrape_results = []
			filter_title = filter_by_name(self.scrape_provider)
			self.media_type, title = info.get('media_type'), info.get('title')
			self.year, self.season, self.episode = int(info.get('year')), info.get('season'), info.get('episode')
			self.folder_query, self.year_query_list = clean_title(normalize(title)), tuple(map(str, range(self.year - 1, self.year + 2)))
			self._scrape_cloud()
			if not self.scrape_results: return internal_results(self.scrape_provider, self.sources)
			self.aliases = source_utils.get_aliases_titles(info.get('aliases', []))
			def _process():
				for item in self.scrape_results:
					try:
						file_name = item['filename']
						if filter_title and not check_title(title, file_name, self.aliases, self.year, self.season, self.episode): continue
						display_name = clean_file_name(file_name).replace('html', ' ').replace('+', ' ').replace('-', ' ')
						file_dl, size = Offcloud.requote_uri(item['url']), 0
						video_quality, details = get_file_info(name_info=release_info_format(file_name))
						source_item = {'name': file_name, 'display_name': display_name, 'quality': video_quality, 'size': size, 'size_label': '%.2f GB' % size,
									'extraInfo': details, 'url_dl': file_dl, 'id': file_dl, 'downloads': False, 'direct': True, 'source': self.scrape_provider,
									'scrape_provider': self.scrape_provider, 'direct_debrid_link': True}
						yield source_item
					except: pass
			self.sources = list(_process())
		except Exception as e:
			from modules.kodi_utils import logger
			logger('offcloud scraper Exception', e)
		internal_results(self.scrape_provider, self.sources)
		return self.sources

	def _scrape_cloud(self):
		try:
			threads = []
			append = threads.append
			results_append = self.scrape_results.append
			try: my_cloud_files = Offcloud.user_cloud()
			except: return self.sources
			for item in my_cloud_files:
				if item['status'] != 'downloaded': continue
				if item['isDirectory']: append(Thread(target=self._scrape_folders, args=(item['requestId'],)))
				else:
					if not item['fileName'].endswith(tuple(extensions)): continue
					match = False
					normalized = normalize(item['fileName'])
					filename = clean_title(normalized)
					if self.media_type == 'movie':
						if any(x in filename for x in self.year_query_list) and self.folder_query in filename: match = True
					elif seas_ep_filter(self.season, self.episode, normalized): match = True
					if match: results_append({'filename': normalized, 'url': Offcloud.build_url(item['server'], item['requestId'], item['fileName'])})
			[i.start() for i in threads]
			[i.join() for i in threads]
		except: return

	def _scrape_folders(self, folder_info):
		try:
			results_append = self.scrape_results.append
			torrent_info = Offcloud.torrent_info(folder_info)
			for item in torrent_info:
				try:
					if not item.endswith(tuple(extensions)): continue
					match = False
					normalized = normalize(item.split('/')[-1])
					filename = clean_title(normalized)
					if self.media_type == 'movie':
						if any(x in filename for x in self.year_query_list) and self.folder_query in filename: match = True
					elif seas_ep_filter(self.season, self.episode, normalized): match = True
					if match: results_append({'filename': normalized, 'url': item})
				except: continue
		except: return

