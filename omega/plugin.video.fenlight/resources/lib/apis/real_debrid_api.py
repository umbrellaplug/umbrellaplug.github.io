# -*- coding: utf-8 -*-
import re
import sys
import time
import requests
from threading import Thread
from caches.main_cache import cache_object
from caches.settings_cache import get_setting, set_setting
from modules.utils import copy2clip
from modules.source_utils import supported_video_extensions, seas_ep_filter, EXTRAS
from modules import kodi_utils
# logger = kodi_utils.logger

sleep, confirm_dialog, ok_dialog, xbmc_monitor = kodi_utils.sleep, kodi_utils.confirm_dialog, kodi_utils.ok_dialog, kodi_utils.xbmc_monitor
progress_dialog, get_icon, notification = kodi_utils.progress_dialog, kodi_utils.get_icon, kodi_utils.notification
base_url = 'https://api.real-debrid.com/rest/1.0/'
auth_url = 'https://api.real-debrid.com/oauth/v2/'
device_url = 'device/code?%s'
credentials_url = 'device/credentials?%s'
icon = get_icon('realdebrid')
timeout = 20.0

class RealDebridAPI:
	def __init__(self):
		self.client_ID = get_setting('fenlight.rd.client_id', 'empty_setting')
		if self.client_ID in ('empty_setting', ''): self.client_ID = 'X245A4XAIBGVM'
		self.token = get_setting('fenlight.rd.token', 'empty_setting')
		self.secret = get_setting('fenlight.rd.secret', 'empty_setting')
		self.refresh = get_setting('fenlight.rd.refresh', 'empty_setting')
		self.device_code = ''
		self.refresh_retries = 0
		self.break_auth_loop = False

	def auth(self):
		self.secret = ''
		self.client_ID = 'X245A4XAIBGVM'
		url = auth_url + device_url % 'client_id=%s&new_credentials=yes' % self.client_ID
		response = requests.get(url, timeout=timeout).json()
		user_code = response['user_code']
		try: copy2clip(user_code)
		except: pass
		content = 'Authorize Debrid Services[CR]Navigate to: [B]https://real-debrid.com/device[/B][CR]Enter the following code: [B]%s[/B]' % user_code
		progressDialog = progress_dialog('Real Debrid Authorize', get_icon('rd_qrcode'))
		progressDialog.update(content, 0)
		expires_in = int(response['expires_in'])
		sleep_interval = int(response['interval'])
		device_code = response['device_code']
		poll_url = auth_url + credentials_url % 'client_id=%s&code=%s' % (self.client_ID, device_code)
		start, time_passed = time.time(), 0
		while not progressDialog.iscanceled() and time_passed < expires_in and not self.secret:
			sleep(1000 * sleep_interval)
			try: response = requests.get(poll_url, timeout=timeout).json()
			except: continue
			if 'error' in response:
				time_passed = time.time() - start
				progress = int(100 * time_passed/float(expires_in))
				progressDialog.update(content, progress)
				continue
			try:
				set_setting('rd.client_id', response['client_id'])
				set_setting('rd.secret', response['client_secret'])
				self.secret = response['client_secret']
				self.client_ID = response['client_id']
				progressDialog.close()
			except:
				ok_dialog(text='Error')
				break
		try: progressDialog.close()
		except: pass
		if self.secret:
			data = {'client_id': self.client_ID, 'client_secret': self.secret, 'code': device_code, 'grant_type': 'http://oauth.net/grant_type/device/1.0'}
			url = '%stoken' % auth_url
			response = requests.post(url, data=data, timeout=timeout).json()
			self.token = response['access_token']
			self.refresh = response['refresh_token']
			username = self.account_info()['username']
			set_setting('rd.token', self.token)
			set_setting('rd.refresh', self.refresh)
			set_setting('rd.account_id', username)
			set_setting('rd.enabled', 'true')
			ok_dialog(text='Success')

	def refresh_token(self):
		try:
			url = auth_url + 'token'
			data = {'client_id': self.client_ID, 'client_secret': self.secret, 'code': self.refresh, 'grant_type': 'http://oauth.net/grant_type/device/1.0'}
			response = requests.post(url, data=data).json()
			self.token = response['access_token']
			self.refresh = response['refresh_token']
			set_setting('rd.token', self.token)
			set_setting('rd.refresh', self.refresh)
			return True
		except: return False

	def revoke(self):
		set_setting('rd.client_id', 'empty_setting')
		set_setting('rd.secret', 'empty_setting')
		set_setting('rd.refresh', 'empty_setting')
		set_setting('rd.token', 'empty_setting')
		set_setting('rd.account_id', 'empty_setting')
		set_setting('rd.enabled', 'false')
		notification('Real Debrid Authorization Reset', 3000)

	def account_info(self):
		url = 'user'
		return self._get(url)

	def check_cache(self, hashes):
		hash_string = '/'.join(hashes)
		url = 'torrents/instantAvailability/%s' % hash_string
		return self._get(url)

	def check_hash(self, hash_string):
		url = 'torrents/instantAvailability/%s' % hash_string
		return self._get(url)

	def check_single_magnet(self, hash_string):
		cache_info = self.check_hash(hash_string)
		cached = False
		if hash_string in cache_info:
			info = cache_info[hash_string]
			if isinstance(info, dict) and len(info.get('rd')) > 0:
				cached = True
		return cached

	def torrents_activeCount(self):
		url = 'torrents/activeCount'
		return self._get(url)

	def user_cloud(self):
		string = 'rd_user_cloud'
		url = 'torrents?limit=500'
		return cache_object(self._get, string, url, False, 0.03)

	def user_cloud_check(self):
		url = 'torrents?limit=500'
		return self._get(url)

	def downloads(self):
		string = 'rd_downloads'
		url = 'downloads?limit=500'
		return cache_object(self._get, string, url, False, 0.03)

	def user_cloud_info(self, file_id):
		string = 'rd_user_cloud_info_%s' % file_id
		url = 'torrents/info/%s' % file_id
		return cache_object(self._get, string, url, False, 0.03)

	def user_cloud_info_check(self, file_id):
		url = 'torrents/info/%s' % file_id
		return self._get(url)

	def torrent_info(self, file_id):
		url = 'torrents/info/%s' % file_id
		return self._get(url)

	def unrestrict_link(self, link):
		url = 'unrestrict/link'
		post_data = {'link': link}
		response = self._post(url, post_data)
		try: return response['download']
		except: return None

	def add_magnet(self, magnet):
		post_data = {'magnet': magnet}
		url = 'torrents/addMagnet'
		return self._post(url, post_data)

	def create_transfer(self, magnet_url):
		from modules.source_utils import supported_video_extensions
		try:
			extensions = supported_video_extensions()
			torrent = self.add_magnet(magnet_url)
			torrent_id = torrent['id']
			info = self.torrent_info(torrent_id)
			files = info['files']
			torrent_keys = [str(item['id']) for item in files if item['path'].lower().endswith(tuple(extensions))]
			torrent_keys = ','.join(torrent_keys)
			self.add_torrent_select(torrent_id, torrent_keys)
			return 'success'
		except:
			self.delete_torrent(torrent_id)
			return 'failed'

	def add_torrent_select(self, torrent_id, file_ids):
		self.clear_cache(clear_hashes=False)
		url = 'torrents/selectFiles/%s' % torrent_id
		post_data = {'files': file_ids}
		return self._post(url, post_data)

	def delete_torrent(self, folder_id):
		if self.token in ('empty_setting', ''): return None
		url = 'torrents/delete/%s&auth_token=%s' % (folder_id, self.token)
		response = requests.delete(base_url + url, timeout=timeout)
		return response

	def delete_download(self, download_id):
		if self.token in ('empty_setting', ''): return None
		url = 'downloads/delete/%s&auth_token=%s' % (download_id, self.token)
		response = requests.delete(base_url + url, timeout=timeout)
		return response

	def resolve_magnet(self, magnet_url, info_hash, store_to_cloud, title, season, episode):
		compare_title = re.sub(r'[^A-Za-z0-9]+', '.', title.replace('\'', '').replace('&', 'and').replace('%', '.percent')).lower()
		elapsed_time, transfer_finished = 0, False
		extensions = supported_video_extensions()
		torrent_id = None
		try:
			torrent = self.add_magnet(magnet_url)
			if 'error' in torrent: return None
			torrent_id = torrent['id']
			self.add_torrent_select(torrent_id, 'all')
			torrent_info = self.user_cloud_info_check(torrent_id)
			if not torrent_info['links'] or 'error' in torrent_info:
				self.delete_torrent(torrent_id)
				return None
			sleep(200)
			while elapsed_time <= 4 and not transfer_finished:
				active_count = self.torrents_activeCount()
				active_list = active_count['list']
				elapsed_time += 1
				if info_hash in active_list: sleep(1000)
				else: transfer_finished = True
			if not transfer_finished:
				self.delete_torrent(torrent_id)
				return None
			selected_files = [(idx, i) for idx, i in enumerate([i for i in torrent_info['files'] if i['selected'] == 1 and i['path'].lower().endswith(tuple(extensions))])]
			selected_files = sorted(selected_files, key=lambda x: x[1]['bytes'], reverse=True)
			match = False
			if season:
				correct_files = []
				correct_file_check = False
				for value in selected_files:
					correct_file_check = seas_ep_filter(season, episode, value[1]['path'])
					if correct_file_check: correct_files.append(value[1]); break
				if len(correct_files) == 0: match = False
				else:
					for i in correct_files:
						compare_link = seas_ep_filter(season, episode, i['path'], split=True)
						compare_link = re.sub(compare_title, '', compare_link)
						if any(x in compare_link for x in EXTRAS): continue
						else: match = True; break
				if match: index = [i[0] for i in selected_files if i[1]['path'] == correct_files[0]['path']][0]
			else:
				if self._m2ts_check(selected_files): self.delete_torrent(torrent_id) ; return None
				for value in selected_files:
					filename = re.sub(r'[^A-Za-z0-9-]+', '.', value[1]['path'].rsplit('/', 1)[1].replace('\'', '').replace('&', 'and').replace('%', '.percent')).lower()
					filename_info = filename.replace(compare_title, '')
					if any(x in filename_info for x in EXTRAS): continue
					match, index = True, value[0]; break
			if match:
				rd_link = torrent_info['links'][index]
				file_url = self.unrestrict_link(rd_link)
				if file_url.endswith('rar'): file_url = None
				if not any(file_url.lower().endswith(x) for x in extensions): file_url = None
				if not store_to_cloud: Thread(target=self.delete_torrent, args=(torrent_id,)).start()
				return file_url
			else: self.delete_torrent(torrent_id)
		except:
			if torrent_id: self.delete_torrent(torrent_id)
			return None

	def display_magnet_pack(self, magnet_url, info_hash):
		try:
			torrent_id = None
			torrent = self.add_magnet(magnet_url)
			torrent_id = torrent['id']
			self.add_torrent_select(torrent_id, 'all')
			torrent_info = self.user_cloud_info_check(torrent_id)
			if not torrent_info['links'] or 'error' in torrent_info:
				self.delete_torrent(torrent_id)
				return None
			sleep(1000)
			elapsed_time, transfer_finished = 0, False
			while elapsed_time <= 4 and not transfer_finished:
				active_count = self.torrents_activeCount()
				active_list = active_count['list']
				elapsed_time += 1
				if info_hash in active_list: sleep(1000)
				else: transfer_finished = True
			if not transfer_finished:
				self.delete_torrent(torrent_id)
				return None
			list_file_items = [dict(i, **{'link': torrent_info['links'][idx]}) for idx, i in enumerate([i for i in torrent_info['files'] if i['selected'] == 1])]
			list_file_items = [{'link': i['link'], 'filename': i['path'].replace('/', ''), 'size': i['bytes']} for i in list_file_items]
			self.delete_torrent(torrent_id)
			return list_file_items
		except:
			if torrent_id: self.delete_torrent(torrent_id)
			return None

	def video_only(self, storage_variant, extensions):
		return False if len([i for i in storage_variant.values() if not i['filename'].lower().endswith(tuple(extensions))]) > 0 else True

	def name_check(self, storage_variant, season, episode, seas_ep_filter):
		return len([i for i in storage_variant.values() if seas_ep_filter(season, episode, i['filename'])]) > 0

	def sort_cache_list(self, unsorted_list):
		sorted_list = sorted(unsorted_list, key=lambda x: x[1], reverse=True)
		return [i[0] for i in sorted_list]

	def _m2ts_check(self, folder_details):
		for idx, item in folder_details:
			if item['path'].endswith('.m2ts'): return True
		return False

	def _get(self, url):
		original_url = url
		url = base_url + url
		if self.token in ('empty_setting', ''): return None
		if '?' not in url: url += '?auth_token=%s' % self.token
		else: url += '&auth_token=%s' % self.token
		response = requests.get(url, timeout=timeout)
		if any(value in response.text for value in ('bad_token', 'Bad Request')):
			if self.refresh_token(): response = self._get(original_url)
			else: return None
		try: return response.json()
		except: return response

	def _post(self, url, post_data):
		original_url = url
		url = base_url + url
		if self.token in ('empty_setting', ''): return None
		if '?' not in url: url += '?auth_token=%s' % self.token
		else: url += '&auth_token=%s' % self.token
		response = requests.post(url, data=post_data, timeout=timeout)
		if any(value in response.text for value in ('bad_token', 'Bad Request')):
			if self.refresh_token(): response = self._post(original_url, post_data)
			else: return None
		try: return response.json()
		except: return response

	def clear_cache(self, clear_hashes=True):
		try:
			from caches.debrid_cache import debrid_cache
			from caches.base_cache import connect_database
			dbcon = connect_database('maincache_db')
			user_cloud_success = False
			# USER CLOUD
			try:
				try:
					user_cloud_info_caches = [eval(i[0])['id'] for i in dbcon.execute("""SELECT data FROM maincache WHERE id LIKE ?""", ('rd_user_cloud_info_%',)).fetchall()]
				except:
					user_cloud_success = True
				if not user_cloud_success:
					dbcon.execute("""DELETE FROM maincache WHERE id=?""", ('rd_user_cloud',))
					for i in user_cloud_info_caches:
						dbcon.execute("""DELETE FROM maincache WHERE id=?""", ('rd_user_cloud_info_%s' % i,))
					user_cloud_success = True
			except: user_cloud_success = False
			# DOWNLOAD LINKS
			try:
				dbcon.execute("""DELETE FROM maincache WHERE id=?""", ('rd_downloads',))
				download_links_success = True
			except: download_links_success = False
			# HASH CACHED STATUS
			if clear_hashes:
				try:
					debrid_cache.clear_debrid_results('rd')
					hash_cache_status_success = True
				except: hash_cache_status_success = False
			else: hash_cache_status_success = True
		except: return False
		if False in (user_cloud_success, download_links_success, hash_cache_status_success): return False
		return True

