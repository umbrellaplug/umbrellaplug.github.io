# -*- coding: utf-8 -*-
import shutil
from zipfile import ZipFile
from datetime import timedelta
from caches.main_cache import main_cache
from modules.kodi_utils import requests, json, notification, sleep, delete_file, rename_file, quote
# from modules.kodi_utils import logger

user_agent = 'Fen v1.0'

class OpenSubtitlesAPI:
	def __init__(self):
		self.headers = {'User-Agent': user_agent}

	def search(self, query, imdb_id, language, season=None, episode=None):
		cache_name = 'opensubtitles_%s_%s' % (imdb_id, language)
		if season: cache_name += '_%s_%s' % (season, episode)
		cache = main_cache.get(cache_name)
		if cache: return cache
		url = 'https://rest.opensubtitles.org/search/imdbid-%s/query-%s%s/sublanguageid-%s' \
				% (imdb_id, quote(query), '/season-%d/episode-%d' % (season, episode) if season else '', language)
		response = self._get(url, retry=True)
		response = json.loads(response.text)
		main_cache.set(cache_name, response, expiration=timedelta(hours=24))
		return response

	def download(self, url, filepath, temp_zip, temp_path, final_path):
		result = self._get(url, stream=True, retry=True)
		with open(temp_zip, 'wb') as f: shutil.copyfileobj(result.raw, f)
		with ZipFile(temp_zip, 'r') as zip_file: zip_file.extractall(filepath)
		delete_file(temp_zip)
		rename_file(temp_path, final_path)
		return final_path

	def _get(self, url, stream=False, retry=False):
		response = requests.get(url, headers=self.headers, stream=stream)
		if '200' in str(response): return response
		elif '429' in str(response) and retry:
			notification(32740, 3500)
			sleep(10000)
			return self._get(url, stream)
		else: return