# -*- coding: utf-8 -*-
# Thanks to kodifitzwell for allowing me to borrow his code
from threading import Thread
from apis.torbox_api import TorBoxAPI
from modules import source_utils
from modules.utils import clean_file_name, normalize
from modules.settings import enabled_debrids_check, filter_by_name
# from modules.kodi_utils import logger


internal_results, check_title, clean_title, get_aliases_titles = source_utils.internal_results, source_utils.check_title, source_utils.clean_title, source_utils.get_aliases_titles
get_file_info, release_info_format, seas_ep_filter = source_utils.get_file_info, source_utils.release_info_format, source_utils.seas_ep_filter
TorBox = TorBoxAPI()
extensions = source_utils.supported_video_extensions()

class source:
	def __init__(self):
		self.scrape_provider = 'tb_cloud'
		self.sources = []

	def results(self, info):
		try:
			if not enabled_debrids_check('tb'): return internal_results(self.scrape_provider, self.sources)
			self.folder_results, self.scrape_results = [], []
			filter_title = filter_by_name(self.scrape_provider)
			self.media_type, title = info.get('media_type'), info.get('title')
			self.year, self.season, self.episode = int(info.get('year')), info.get('season'), info.get('episode')
			self.tmdb_id = info.get('tmdb_id')
			self.folder_query = clean_title(normalize(title))
			self._scrape_cloud()
			self._scrape_cloud_usenet()
			if not self.scrape_results: return internal_results(self.scrape_provider, self.sources)
			self.aliases = get_aliases_titles(info.get('aliases', []))
			def _process():
				for item in self.scrape_results:
					try:
						file_name = normalize(item['name'])
						if filter_title and not check_title(title, file_name, self.aliases, self.year, self.season, self.episode): continue
						display_name = clean_file_name(file_name).replace('html', ' ').replace('+', ' ').replace('-', ' ')
						direct_debrid_link = item.get('direct_debrid_link', False)
						file_dl, size = '%d,%d' % (int(item['folder_id']), item['id']), round(float(int(item['size']))/1073741824, 2)
						video_quality, details = get_file_info(name_info=release_info_format(file_name))
						source_item = {'name': file_name, 'display_name': display_name, 'quality': video_quality, 'size': size, 'size_label': '%.2f GB' % size,
									'extraInfo': details, 'url_dl': file_dl, 'id': file_dl, 'downloads': False, 'direct': True, 'source': self.scrape_provider,
									'scrape_provider': self.scrape_provider, 'direct_debrid_link': direct_debrid_link}
						yield source_item
					except: pass
			self.sources = list(_process())
		except Exception as e:
			from modules.kodi_utils import logger
			logger('torbox scraper Exception', str(e))
		internal_results(self.scrape_provider, self.sources)
		return self.sources

	def _scrape_cloud(self):
		try:
			append = self.scrape_results.append
			year_query_list = self._year_query_list()
			try: my_cloud_files = TorBox.user_cloud()
			except: return self.sources
			for item in my_cloud_files['data']:
				if not item['download_finished']: continue
				if not self.folder_query in clean_title(normalize(item['name'])): continue
				folder_id = item['id']
				for file in item['files']:
					if not file['short_name'].endswith(tuple(extensions)): continue
					normalized = normalize(file['short_name'])
					folder_name = clean_title(normalized)
					if self.media_type == 'movie':
						if not any(x in normalized for x in year_query_list): continue
					elif not seas_ep_filter(self.season, self.episode, normalized): continue
					file['folder_id'] = folder_id
					append(file)
		except: return

	def _scrape_cloud_usenet(self):
		try:
			append = self.scrape_results.append
			year_query_list = self._year_query_list()
			try: my_cloud_files_usenet = TorBox.user_cloud_usenet()
			except: return self.sources
			for item in my_cloud_files_usenet['data']:
				if not item['download_finished']: continue
				if not self.folder_query in clean_title(normalize(item['name'])): continue
				folder_id = item['id']
				for file in item['files']:
					if not file['short_name'].endswith(tuple(extensions)): continue
					normalized = normalize(file['short_name'])
					folder_name = clean_title(normalized)
					if self.media_type == 'movie':
						if not any(x in normalized for x in year_query_list): continue
					elif not seas_ep_filter(self.season, self.episode, normalized): continue
					file['folder_id'] = folder_id
					file['direct_debrid_link'] = True
					append(file)
		except: return

	def _year_query_list(self):
		return (str(self.year), str(self.year+1), str(self.year-1))

