# -*- coding: utf-8 -*-
from apis.alldebrid_api import AllDebridAPI
from modules import source_utils
from modules.kodi_utils import Thread
from modules.utils import clean_file_name, normalize
from modules.settings import enabled_debrids_check, filter_by_name
# from modules.kodi_utils import logger

AllDebrid = AllDebridAPI()
extensions = source_utils.supported_video_extensions()
internal_results, check_title, clean_title, get_aliases_titles = source_utils.internal_results, source_utils.check_title, source_utils.clean_title, source_utils.get_aliases_titles
get_file_info, release_info_format, seas_ep_filter = source_utils.get_file_info, source_utils.release_info_format, source_utils.seas_ep_filter
gather_assigned_content, test_assigned_content = source_utils.gather_assigned_content, source_utils.test_assigned_content
command = 'SELECT id, data from maincache where id LIKE %s'

class source:
	def __init__(self):
		self.scrape_provider = 'ad_cloud'
		self.sources = []

	def results(self, info):
		try:
			if not enabled_debrids_check('ad'): return internal_results(self.scrape_provider, self.sources)
			self.folder_results, self.scrape_results = [], []
			filter_title = filter_by_name(self.scrape_provider)
			self.media_type, title = info.get('media_type'), info.get('title')
			self.year, self.season, self.episode = int(info.get('year')), info.get('season'), info.get('episode')
			self.tmdb_id = info.get('tmdb_id')
			self.folder_query = clean_title(normalize(title))
			self.pre_assigned_content = self._gather_assigned_content()
			self._scrape_cloud()
			if not self.scrape_results: return internal_results(self.scrape_provider, self.sources)
			self.aliases = get_aliases_titles(info.get('aliases', []))
			def _process():
				for item in self.scrape_results:
					try:
						file_name = normalize(item['filename'])
						if filter_title and not item['assigned_content'] and not check_title(title, file_name, self.aliases, self.year, self.season, self.episode): continue
						display_name = clean_file_name(file_name).replace('html', ' ').replace('+', ' ').replace('-', ' ')
						file_dl, size = item['link'], round(float(int(item['size']))/1073741824, 2)
						video_quality, details = get_file_info(name_info=release_info_format(file_name))
						source_item = {'name': file_name, 'display_name': display_name, 'quality': video_quality, 'size': size, 'size_label': '%.2f GB' % size,
									'extraInfo': details, 'url_dl': file_dl, 'id': file_dl, 'downloads': False, 'direct': True, 'source': self.scrape_provider,
									'scrape_provider': self.scrape_provider}
						yield source_item
					except: pass
			self.sources = list(_process())
		except Exception as e:
			from modules.kodi_utils import logger
			logger('FEN alldebrid scraper Exception', str(e))
		internal_results(self.scrape_provider, self.sources)
		return self.sources

	def _gather_assigned_content(self):
		pre_assigned_content = gather_assigned_content("'FEN_AD_%'")
		return [i for i in pre_assigned_content if i[1].get('media_type') == self.media_type and self.tmdb_id == i[1].get('tmdb_id')]

	def _scrape_cloud(self):
		try:
			try:
				my_cloud_files = AllDebrid.user_cloud()['magnets']
				my_cloud_files = [i for i in my_cloud_files if i['statusCode'] == 4]
			except: return self.sources
			threads = []
			results_append = self.folder_results.append
			append = threads.append
			year_query_list = self._year_query_list()
			for item in my_cloud_files:
				normalized = normalize(item['filename'])
				folder_name = clean_title(normalized)
				if test_assigned_content('FEN_AD_%s' % item['id'], self.pre_assigned_content): results_append((item, True))
				elif not folder_name: results_append((item, False))
				elif not self.folder_query in folder_name: continue
				else:
					if self.media_type == 'movie' and not any(x in normalized for x in year_query_list): continue
					results_append((item, False))
			if not self.folder_results: return self.sources
			for i in self.folder_results: append(Thread(target=self._scrape_folders, args=(i,)))
			[i.start() for i in threads]
			[i.join() for i in threads]
		except: pass

	def _scrape_folders(self, folder_info):
		try:
			links = folder_info[0]['links']
			assigned_content = folder_info[1]
			append = self.scrape_results.append
			links = [i for i in links if i['filename'].lower().endswith(tuple(extensions))]
			for item in links:
				normalized = normalize(item['filename'])
				if self.media_type == 'episode' and not seas_ep_filter(self.season, self.episode, normalized): continue
				item['assigned_content'] = assigned_content
				append(item)
		except: return

	def _year_query_list(self):
		return (str(self.year), str(self.year+1), str(self.year-1))
