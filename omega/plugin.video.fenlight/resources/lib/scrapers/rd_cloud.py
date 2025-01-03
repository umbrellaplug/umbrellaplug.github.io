# -*- coding: utf-8 -*-
from apis.real_debrid_api import RealDebridAPI
from modules import source_utils
from threading import Thread
from modules.utils import clean_file_name, normalize
from modules.settings import enabled_debrids_check, filter_by_name
from modules.kodi_utils import logger

RealDebrid = RealDebridAPI()
extensions = source_utils.supported_video_extensions()
internal_results, check_title, clean_title, get_aliases_titles = source_utils.internal_results, source_utils.check_title, source_utils.clean_title, source_utils.get_aliases_titles
get_file_info, release_info_format, seas_ep_filter = source_utils.get_file_info, source_utils.release_info_format, source_utils.seas_ep_filter

class source:
	def __init__(self):
		self.scrape_provider = 'rd_cloud'
		self.sources = []

	def results(self, info):
		try:
			if not enabled_debrids_check('rd'): return internal_results(self.scrape_provider, self.sources)
			self.folder_results, self.scrape_results = [], []
			filter_title = filter_by_name(self.scrape_provider)
			self.media_type, title, self.tmdb_id = info.get('media_type'), info.get('title'), info.get('tmdb_id')
			self.year, self.season, self.episode = int(info.get('year')), info.get('season'), info.get('episode')
			self.folder_query = clean_title(normalize(title))
			self._scrape_downloads()
			self._scrape_cloud()
			if not self.scrape_results: return internal_results(self.scrape_provider, self.sources)
			aliases = get_aliases_titles(info.get('aliases', []))
			def _process():
				for item in self.scrape_results:
					try:
						file_name = self._get_filename(item['path'])
						if filter_title and not check_title(title, file_name, aliases, self.year, self.season, self.episode): continue
						display_name = clean_file_name(file_name).replace('html', ' ').replace('+', ' ').replace('-', ' ')
						file_dl, size = item['url_link'], round(float(item['bytes'])/1073741824, 2)
						direct_debrid_link = item.get('direct_debrid_link', False)
						video_quality, details = get_file_info(name_info=release_info_format(file_name))
						source_item = {'name': file_name, 'display_name': display_name, 'quality': video_quality, 'size': size, 'size_label': '%.2f GB' % size,
									'extraInfo': details, 'url_dl': file_dl, 'id': file_dl, 'downloads': False, 'direct': True, 'source': self.scrape_provider,
									'scrape_provider': self.scrape_provider, 'direct_debrid_link': direct_debrid_link}
						yield source_item
					except: pass
			self.sources = list(_process())
		except Exception as e:
			from modules.kodi_utils import logger
			logger('real-debrid scraper Exception', str(e))
		internal_results(self.scrape_provider, self.sources)
		return self.sources

	def _scrape_cloud(self):
		try:
			try:
				my_cloud_files = RealDebrid.user_cloud()
				my_cloud_files = [i for i in my_cloud_files if i['status'] == 'downloaded']
			except: return self.sources
			results_append = self.folder_results.append
			year_query_list = self._year_query_list()
			for item in my_cloud_files:
				normalized = normalize(item['filename'])
				folder_name = clean_title(normalized)
				if not folder_name: results_append(item['id'])
				elif not self.folder_query in folder_name: continue
				else:
					if self.media_type == 'movie' and not any(x in normalized for x in year_query_list): continue
					results_append(item['id'])
			if not self.folder_results: return self.sources
			threads = []
			threads_append = threads.append
			for i in self.folder_results: threads_append(Thread(target=self._scrape_folders, args=(i,)))
			[i.start() for i in threads]
			[i.join() for i in threads]
		except: pass

	def _scrape_folders(self, folder_info):
		try:
			folder_files = RealDebrid.user_cloud_info(folder_info)
			contents = [i for i in folder_files['files'] if i['selected'] == 1 and i['path'].lower().endswith(tuple(extensions))]
			file_urls = folder_files['links']
			scrape_results_append = self.scrape_results.append
			for c, i in enumerate(contents):
				try: i.update({'url_link': file_urls[c]})
				except: pass
			contents.sort(key=lambda k: k['path'])
			for item in contents:
				normalized = normalize(item['path'])
				if self.media_type == 'episode' and not seas_ep_filter(self.season, self.episode, normalized): continue
				if item['path'].replace('/', '').lower() not in [d['path'].replace('/', '').lower() for d in self.scrape_results]:
					scrape_results_append(item)
		except: pass

	def _scrape_downloads(self):
		try:
			my_downloads = RealDebrid.downloads()
			my_downloads = [i for i in my_downloads if i['download'].lower().endswith(tuple(extensions))]
			scrape_results_append = self.scrape_results.append
			year_query_list = self._year_query_list()
			for item in my_downloads:
				normalized = normalize(item['filename'])
				folder_name = clean_title(normalized)
				if not self.folder_query in folder_name: continue
				if self.media_type == 'movie':
					if not any(x in normalized for x in year_query_list): continue
				elif not seas_ep_filter(self.season, self.episode, normalized): continue
				item = self.make_downloads_item(item)
				if item['path'].replace('/', '').lower() not in [d['path'].replace('/', '').lower() for d in self.scrape_results]: scrape_results_append(item)
		except: pass

	def make_downloads_item(self, item):
		return {'url_link': item['download'], 'bytes': item['filesize'], 'path': item['filename'], 'direct_debrid_link': True}

	def _get_filename(self, name):
		if name.startswith('/'): name = name.split('/')[-1]
		return normalize(name)

	def _year_query_list(self):
		return (str(self.year), str(self.year+1), str(self.year-1))
