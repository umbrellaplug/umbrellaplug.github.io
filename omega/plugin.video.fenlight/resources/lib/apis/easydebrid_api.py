# -*- coding: utf-8 -*-
# Thanks to kodifitzwell for allowing me to borrow his code
import json
import requests
from urllib.parse import urlencode
from caches.settings_cache import get_setting, set_setting
from modules.kodi_utils import make_session, kodi_dialog, notification, ok_dialog, confirm_dialog
from modules.source_utils import supported_video_extensions, seas_ep_filter, EXTRAS
# from modules.kodi_utils import logger

base_url = 'https://easydebrid.com/api/v1/'
download = 'link/generate'
stats = 'user/details'
cache = 'link/lookup'
user_agent = 'Fen Light for Kodi'
timeout = 20.0
session = make_session(base_url)


class EasyDebridAPI:

	def __init__(self):
		self.token = get_setting('fenlight.ed.token')

	def _get(self, url, data={}):
		if self.token in ('empty_setting', ''): return None
		url = base_url + url
		response = session.get(url, data=data, headers=self.headers(), timeout=timeout)
		return response.json()

	def _post(self, url, params=None, json=None, data=None):
		if self.token in ('empty_setting', '') and not 'token' in url: return None
		url = base_url + url
		response = session.post(url, params=params, json=json, data=data, headers=self.headers(), timeout=timeout)
		return response.json()

	def account_info(self):
		return self._get(stats)

	def add_magnet(self, magnet):
		data = {'url': magnet}
		return self._post(download, json=data)

	def check_cache_single(self, _hash):
		return self._post(self.cache, json={'urls': [_hash]})

	def check_cache(self, hashlist):
		data = {'urls': hashlist}
		return self._post(cache, json=data)

	def create_transfer(self, magnet_url):
		result = self.add_magnet(magnet_url)
		if not 'files' in result: return ''
		return result.get('files', '')

	def resolve_magnet(self, magnet_url, info_hash, store_to_cloud, title, season, episode):
		try:
			file_url, match = None, False
			extensions = supported_video_extensions()
			torrent = self.add_magnet(magnet_url)
			torrent_files = torrent['files']
			torrent_files = [item for item in torrent_files if item['filename'].lower().endswith(tuple(extensions))]
			if not torrent_files: return None
			if season:
				torrent_files = [i for i in torrent_files if seas_ep_filter(season, episode, i['filename'])]
				if not torrent_files: return None
			else:
				if self._m2ts_check(torrent_files): return None
				torrent_files = [i for i in torrent_files if not any(x in i['filename'] for x in EXTRAS)]
				torrent_files.sort(key=lambda k: k['size'], reverse=True)
			file_url = torrent_files[0]['url']
			return self.add_headers_to_url(file_url)
		except: return None

	def display_magnet_pack(self, magnet_url, info_hash):
		try:
			extensions = supported_video_extensions()
			torrent = self.add_magnet(magnet_url)
			torrent_files = [{'link': item['url'], 'filename': item['filename'], 'size': item['size']} \
							for item in torrent['files'] if item['filename'].lower().endswith(tuple(extensions))]
			return torrent_files or None
		except: return None

	def add_headers_to_url(self, url):
		return url + '|' + urlencode(self.headers())

	def headers(self):
		return {'User-Agent': user_agent, 'Authorization': 'Bearer %s' % self.token}

	def _m2ts_check(self, folder_items):
		for item in folder_items:
			if item['filename'].endswith('.m2ts'): return True
		return False

	def auth(self):
		api_key = kodi_dialog().input('EasyDebrid API Key:')
		if not api_key: return
		self.token = api_key
		response = self.account_info()
		try:
			customer = response['id']
			set_setting('ed.token', api_key)
			set_setting('ed.enabled', 'true')
			message = 'Success'
		except: message = 'Failed'
		ok_dialog(text=message)

	def revoke(self):
		if not confirm_dialog(): return
		set_setting('ed.token', 'empty_setting')
		set_setting('ed.enabled', 'false')
		notification('Easy Debrid Authorization Reset', 3000)

	def clear_cache(self, clear_hashes=True):
		try:
			from caches.debrid_cache import debrid_cache
			from caches.base_cache import connect_database
			dbcon = connect_database('maincache_db')
			# USER CLOUD
			try:
				dbcon.execute("""DELETE FROM maincache WHERE id=?""", ('ed_user_cloud',))
				dbcon.execute("""DELETE FROM maincache WHERE id LIKE ?""", ('ed_user_cloud%',))
				user_cloud_success = True
			except: user_cloud_success = False
			# HASH CACHED STATUS
			if clear_hashes:
				try:
					debrid_cache.clear_debrid_results('ed')
					hash_cache_status_success = True
				except: hash_cache_status_success = False
			else: hash_cache_status_success = True
		except: return False
		if False in (user_cloud_success, hash_cache_status_success): return False
		return True

