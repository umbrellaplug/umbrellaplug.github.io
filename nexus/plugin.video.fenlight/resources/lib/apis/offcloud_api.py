# -*- coding: utf-8 -*-
# Thanks to kodifitzwell for allowing me to borrow his code
import requests
from threading import Thread
from caches.main_cache import cache_object
from caches.settings_cache import get_setting, set_setting
from modules.source_utils import supported_video_extensions, seas_ep_filter, EXTRAS
from modules.kodi_utils import make_session, kodi_dialog, ok_dialog, notification
# from modules.kodi_utils import logger

base_url = 'https://offcloud.com/api/'
login = 'login'
key = 'key'
stats = 'account/stats'
cloud = 'cloud'
history = 'cloud/history'
explore = 'cloud/explore/%s'
cache = 'cache'
download = 'https://%s.offcloud.com/cloud/download/%s/%s'
remove = 'https://offcloud.com/cloud/remove/%s'
session = make_session(base_url)
timeout = 20.0

class OffcloudAPI:
	def __init__(self):
		self.token = get_setting('fenlight.oc.token', 'empty_setting')

	def ok_message(self, message='An Error Occurred'):
		return ok_dialog(text=message)

	def auth(self):
		username = kodi_dialog().input('Enter Email:')
		password = kodi_dialog().input('Enter Password:')
		if not all((username, password)): return self.ok_message('You need a valid Email & Password for Off Cloud')
		try:
			url = base_url + login
			response = session.post(url, data={'username': username, 'password': password}, timeout=timeout).json()
			url = base_url + key
			response = session.post(url, timeout=timeout).json()
			token = response['apiKey']
			set_setting('oc.token', token)
			set_setting('oc.enabled', 'true')
			message = 'Success'
		except: message = 'An Error Occurred'
		self.ok_message(message)

	def revoke(self):
		set_setting('oc.token', 'empty_setting')
		set_setting('oc.enabled', 'false')
		notification('Off Cloud Authorization Reset', 3000)

	def user_cloud(self):
		url = history
		string = 'oc_user_cloud'
		return cache_object(self._get, string, url, False, 0.03)

	def user_cloud_check(self):
		url = history
		return self._get(url)

	def user_cloud_info(self, request_id=''):
		string = 'oc_user_cloud_%s' % request_id
		url = explore % request_id
		return cache_object(self._get, string, url, False, 0.03)

	def account_info(self):
		return self._get(stats)

	def check_cache(self, hashlist):
		return self._post(cache, data={'hashes': hashlist})

	def create_transfer(self, magnet_url):
		result = self.add_magnet(magnet_url)
		if not result['status'] in ('created', 'downloaded'): return ''
		return result.get('requestId', '')

	def add_magnet(self, magnet):
		return self._post(cloud, data={'url': magnet})

	def torrent_info(self, request_id=''):
		url = explore % request_id
		return self._get(url)

	def delete_torrent(self, request_id=''):
		url = remove % request_id
		response = session.get(url, params={'key': self.token}, timeout=timeout)
		try: response = response.json()
		except: response = {}
		return response

	def resolve_magnet(self, magnet_url, info_hash, store_to_cloud, title, season, episode):
		try:
			file_url, match, torrent_id = None, False, None
			extensions = supported_video_extensions()
			torrent = self.add_magnet(magnet_url)
			if not torrent['status'] == 'downloaded': return None
			single_file_torrent = '%s/%s' % (torrent['url'], torrent['fileName'])
			torrent_id = torrent['requestId']
			torrent_files = self.torrent_info(torrent_id)
			if not isinstance(torrent_files, list): torrent_files = [single_file_torrent]
			torrent_files = [{'url': item, 'filename': item.split('/')[-1], 'size': 0} for item in torrent_files if item.lower().endswith(tuple(extensions))]
			if not torrent_files: return None
			if season:
				torrent_files = [i for i in torrent_files if seas_ep_filter(season, episode, i['filename'])]
				if not torrent_files: return None
			else:
				if self._m2ts_check(torrent_files): self.delete_torrent(torrent_id) ; return None
				torrent_files = [i for i in torrent_files if not any(x in i['filename'] for x in EXTRAS)]
			file_key = torrent_files[0]['url']
			file_url = self.requote_uri(file_key)
			return file_url
		except:
			if torrent_id: self.delete_torrent(torrent_id)
			return None

	def display_magnet_pack(self, magnet_url, info_hash):
		from modules.source_utils import supported_video_extensions
		try:
			torrent_id = None
			extensions = supported_video_extensions()
			torrent = self.add_magnet(magnet_url)
			if not torrent['status'] == 'downloaded': return None
			torrent_id = torrent['requestId']
			torrent_files = self.torrent_info(torrent_id)
			torrent_files = [{'link': self.requote_uri(item), 'filename': item.split('/')[-1], 'size': 0} for item in torrent_files if item.lower().endswith(tuple(extensions))]
			return torrent_files or None
		except Exception:
			if torrent_id: self.delete_torrent(torrent_id)
			return None

	def _get(self, url):
		url = base_url + url
		if self.token in ('empty_setting', ''): return None
		if '?' not in url: url += '?key=%s' % self.token
		else: url += '&key=%s' % self.token
		response = session.get(url, timeout=timeout)
		try: return response.json()
		except: return response

	def _post(self, url, data):
		url = base_url + url
		if self.token in ('empty_setting', ''): return None
		if '?' not in url: url += '?key=%s' % self.token
		else: url += '&key=%s' % self.token
		response = session.post(url, data=data, timeout=timeout)
		try: return response.json()
		except: return response

	def requote_uri(self, url):
		return requests.utils.requote_uri(url)

	def build_url(self, server, request_id, file_name):
		return self.download % (server, request_id, file_name)

	def _m2ts_check(self, folder_items):
		for item in folder_items:
			if item['filename'].endswith('.m2ts'): return True
		return False

	def clear_played_torrent(self, played_item):
		played_url = played_item['url']
		user_cloud = self.user_cloud_check()
		correct_torrent = next((i for i in user_cloud if i['originalLink'] == played_url), None)
		if correct_torrent: self.delete_torrent(correct_torrent['requestId'])

	def clear_cache(self, clear_hashes=True):
		try:
			from caches.debrid_cache import debrid_cache
			from caches.base_cache import connect_database
			dbcon = connect_database('maincache_db')
			# USER CLOUD
			try:
				dbcon.execute("""DELETE FROM maincache WHERE id=?""", ('oc_user_cloud',))
				dbcon.execute("""DELETE FROM maincache WHERE id LIKE ?""", ('oc_user_cloud%',))
				user_cloud_success = True
			except: user_cloud_success = False
			# HASH CACHED STATUS
			if clear_hashes:
				try:
					debrid_cache.clear_debrid_results('oc')
					hash_cache_status_success = True
				except: hash_cache_status_success = False
			else: hash_cache_status_success = True
		except: return False
		if False in (user_cloud_success, hash_cache_status_success): return False
		return True