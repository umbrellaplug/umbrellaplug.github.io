# -*- coding: utf-8 -*-
import os
from caches.main_cache import cache_object
from modules import source_utils
from modules.kodi_utils import list_dirs, open_file, urlparse
from modules.utils import clean_file_name, normalize, make_thread_list
from modules.settings import filter_by_name
# from modules.kodi_utils import logger

extensions = source_utils.supported_video_extensions()
internal_results, check_title, clean_title, get_aliases_titles = source_utils.internal_results, source_utils.check_title, source_utils.clean_title, source_utils.get_aliases_titles
get_file_info, release_info_format, seas_ep_filter = source_utils.get_file_info, source_utils.release_info_format, source_utils.seas_ep_filter
gather_assigned_content, test_assigned_content = source_utils.gather_assigned_content, source_utils.test_assigned_content
command = 'SELECT id, data from maincache where id LIKE %s'

class source:
	def __init__(self, scrape_provider, scraper_name, folder_path):
		self.scrape_provider = scrape_provider
		self.scraper_name = scraper_name
		self.folder_path = folder_path
		self.sources, self.scrape_results = [], []
		self.assignment_test_string = 'FEN_FOLDERS_%s_%s' % (self.scrape_provider, '%s')

	def results(self, info):
		try:
			if not self.folder_path: return internal_results(self.scraper_name, self.sources)
			filter_title = filter_by_name('folders')
			self.media_type, title, self.year = info.get('media_type'), info.get('title'), int(info.get('year'))
			self.season, self.episode = info.get('season'), info.get('episode')
			self.tmdb_id = info.get('tmdb_id')
			self.title_query = clean_title(normalize(title))
			self.folder_query = self._season_query_list() if self.media_type == 'episode' else self._year_query_list()
			self.pre_assigned_content = self._gather_assigned_content()
			self._scrape_directory((self.folder_path, False), first_run=True)
			if not self.scrape_results: return internal_results(self.scraper_name, self.sources)
			aliases = get_aliases_titles(info.get('aliases', []))
			def _process():
				for item in self.scrape_results:
					try:
						file_name = normalize(item[0])
						if filter_title and not item[3] and not check_title(title, file_name, aliases, self.year, self.season, self.episode): continue
						display_name = clean_file_name(file_name).replace('html', ' ').replace('+', ' ').replace('-', ' ')
						file_dl = item[1]
						try: size = item[2]
						except: size = self._get_size(file_dl)
						video_quality, details = get_file_info(name_info=release_info_format(file_name))
						source_item = {'name': file_name, 'display_name': display_name, 'quality': video_quality, 'size': size, 'size_label': '%.2f GB' % size,
									'extraInfo': details, 'url_dl': file_dl, 'id': file_dl, self.scrape_provider : True, 'direct': True, 'source': self.scraper_name,
									'scrape_provider': 'folders'}
						yield source_item
					except: pass
			self.sources = list(_process())
		except Exception as e:
			from modules.kodi_utils import logger
			logger('FEN folders scraper Exception', str(e))
		internal_results(self.scraper_name, self.sources)
		return self.sources

	def _gather_assigned_content(self):
		pre_assigned_content = gather_assigned_content("'FEN_FOLDERS_%s" % self.scrape_provider + "_%'")
		return [i for i in pre_assigned_content if i[1].get('media_type') == self.media_type and self.tmdb_id == i[1].get('tmdb_id')]

	def _make_dirs(self, folder_info):
		folder_files = []
		folder_files_append = folder_files.append
		folder_name, assigned_content = folder_info[0], folder_info[1]
		dirs, files =  list_dirs(folder_name)
		for i in dirs: folder_files_append((i, 'folder', assigned_content))
		for i in files: folder_files_append((i, 'file', assigned_content))
		return folder_files

	def _scrape_directory(self, folder_info, first_run=False):
		def _process(item):
			file_type = item[1]
			normalized = normalize(item[0])
			item_name = clean_title(normalized)
			if file_type == 'file':
				ext = os.path.splitext(urlparse(item[0]).path)[-1].lower()
				if ext in extensions:
					if self.media_type == 'episode' and not seas_ep_filter(self.season, self.episode, normalized): return
					url_path = self.url_path(folder_name, item[0])
					size = self._get_size(url_path)
					scrape_results_append((item[0], url_path, size, assigned_content))
			else:
				if first_run and test_assigned_content(self.assignment_test_string % item[0], self.pre_assigned_content):
					folder_results_append((os.path.join(folder_name, item[0]), True))
				elif self.title_query in item_name or any(x in item_name for x in self.folder_query):
					folder_results_append((os.path.join(folder_name, item[0]), assigned_content))
		folder_name, assigned_content = folder_info[0], folder_info[1]
		folder_results = []
		scrape_results_append = self.scrape_results.append
		folder_results_append = folder_results.append
		string = 'fen_FOLDERSCRAPER_%s_%s' % (self.scrape_provider, folder_name)
		folder_files = cache_object(self._make_dirs, string, (folder_name, assigned_content), json=False, expiration=4)
		folder_threads = list(make_thread_list(_process, folder_files))
		[i.join() for i in folder_threads]
		if not folder_results: return
		return self._scraper_worker(folder_results)

	def _scraper_worker(self, folder_results):
		scraper_threads = list(make_thread_list(self._scrape_directory, folder_results))
		[i.join() for i in scraper_threads]

	def url_path(self, folder, file):
		return os.path.join(folder, file)

	def _get_size(self, file):
		if file.endswith('.strm'): return 'strm'
		with open_file(file) as f: s = f.size()
		size = round(float(s)/1073741824, 2)
		return size

	def _year_query_list(self):
		return (str(self.year), str(self.year+1), str(self.year-1))

	def _season_query_list(self):
		return ('season%02d' % int(self.season), 'season%s' % self.season)
