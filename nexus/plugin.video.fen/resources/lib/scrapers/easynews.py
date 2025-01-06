# -*- coding: utf-8 -*-
import sys
from apis.easynews_api import import_easynews
from modules import source_utils
from modules.utils import clean_file_name, normalize
from modules.settings import filter_by_name, easynews_language_filter
# from modules.kodi_utils import logger

EasyNews = import_easynews()
internal_results, check_title, get_aliases_titles, extras = source_utils.internal_results, source_utils.check_title, source_utils.get_aliases_titles, source_utils.EXTRAS
get_file_info, release_info_format = source_utils.get_file_info, source_utils.release_info_format

class source:
	def __init__(self):
		self.scrape_provider = 'easynews'
		self.sources = []

	def results(self, info):
		try:
			filter_lang, lang_filters = easynews_language_filter()
			filter_title = filter_by_name('easynews')
			self.media_type, title, self.year, self.season, self.episode = info.get('media_type'), info.get('title'), int(info.get('year')), info.get('season'), info.get('episode')
			self.search_title = clean_file_name(title).replace('&', 'and')
			files = EasyNews.search(self._search_name(), info.get('expiry_times')[0])
			if not files: return internal_results(self.scrape_provider, self.sources)
			self.aliases = get_aliases_titles(info.get('aliases', []))
			def _process():
				for item in files:
					try:
						if item.get('short_vid', False): continue
						file_name = normalize(item['name'])
						if any(x in file_name.lower() for x in extras): continue
						if filter_title and not check_title(title, file_name, self.aliases, self.year, self.season, self.episode): continue
						if filter_lang and not any(i in lang_filters for i in item['language']) : continue
						display_name = clean_file_name(file_name).replace('html', ' ').replace('+', ' ').replace('-', ' ')
						url_dl, size = item['url_dl'], round(float(int(item['rawSize']))/1073741824, 2)
						video_quality, details = get_file_info(name_info=release_info_format(file_name), default_quality=self._quality_estimate(int(item.get('width', 0))))
						source_item = {'name': file_name, 'display_name': display_name, 'quality': video_quality, 'size': size, 'size_label': '%.2f GB' % size,
									'extraInfo': details, 'url_dl': url_dl, 'down_url': item['down_url'], 'id': url_dl, 'local': False, 'direct': True, 'source': self.scrape_provider,
									'scrape_provider': self.scrape_provider}
						yield source_item
					except Exception as e:
						from modules.kodi_utils import logger
						logger('FEN easynews scraper yield source error', str(e))
			self.sources = list(_process())
		except Exception as e:
			from modules.kodi_utils import logger
			logger('FEN easynews scraper Exception', str(e))
		internal_results(self.scrape_provider, self.sources)
		return self.sources

	def _quality_estimate(self, width):
		if width > 1920: return '4K'
		if 1280 < width <= 1920: return '1080p'
		if 720 < width <= 1280: return '720p'
		return 'SD'

	def _search_name(self):
		if self.media_type == 'movie': return '%s %d' % (self.search_title, self.year)
		else: return '%s S%02dE%02d' % (self.search_title,  self.season, self.episode)
