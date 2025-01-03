# -*- coding: utf-8 -*-
import re
import time
import requests
from threading import Thread
from caches.main_cache import cache_object
from caches.settings_cache import get_setting, set_setting
from modules.utils import copy2clip
from modules.source_utils import supported_video_extensions, seas_ep_filter, EXTRAS
from modules import kodi_utils
# logger = kodi_utils.logger

path_exists, get_icon = kodi_utils.path_exists, kodi_utils.get_icon
show_busy_dialog, confirm_dialog = kodi_utils.show_busy_dialog, kodi_utils.confirm_dialog
sleep, ok_dialog = kodi_utils.sleep, kodi_utils.ok_dialog
progress_dialog, notification, hide_busy_dialog, xbmc_monitor = kodi_utils.progress_dialog, kodi_utils.notification, kodi_utils.hide_busy_dialog, kodi_utils.xbmc_monitor
base_url = 'https://api.alldebrid.com/v4/'
user_agent = 'Fen Light for Kodi'
timeout = 20.0
icon = get_icon('alldebrid')

class AllDebridAPI:
	def __init__(self):
		self.token = get_setting('fenlight.ad.token', 'empty_setting')
		self.break_auth_loop = False

	def auth(self):
		self.token = ''
		url = base_url + 'pin/get?agent=%s' % user_agent
		response = requests.get(url, timeout=timeout).json()
		response = response['data']
		expires_in = int(response['expires_in'])
		poll_url = response['check_url']
		user_code = response['pin']
		try: copy2clip(user_code)
		except: pass
		sleep_interval = 5
		content = 'Authorize Debrid Services[CR]Navigate to: [B]%s[/B][CR]Enter the following code: [B]%s[/B]' % (response.get('base_url'), user_code)
		progressDialog = progress_dialog('All Debrid Authorize', get_icon('ad_qrcode'))
		progressDialog.update(content, 0)
		start, time_passed = time.time(), 0
		sleep(2000)
		while not progressDialog.iscanceled() and time_passed < expires_in and not self.token:
			sleep(1000 * sleep_interval)
			response = requests.get(poll_url, timeout=timeout).json()
			response = response['data']
			activated = response['activated']
			if not activated:
				time_passed = time.time() - start
				progress = int(100 * time_passed/float(expires_in))
				progressDialog.update(content, progress)
				continue
			try:
				progressDialog.close()
				self.token = str(response['apikey'])
				set_setting('ad.token', self.token)
			except:
				ok_dialog(text='Error')
				break
		try: progressDialog.close()
		except: pass
		if self.token:
			sleep(2000)
			account_info = self._get('user')
			set_setting('ad.account_id', str(account_info['user']['username']))
			set_setting('ad.enabled', 'true')
			ok_dialog(text='Success')

	def revoke(self):
		set_setting('ad.token', 'empty_setting')
		set_setting('ad.account_id', 'empty_setting')
		set_setting('ad.enabled', 'false')
		notification('All Debrid Authorization Reset', 3000)

	def account_info(self):
		response = self._get('user')
		return response

	def check_cache(self, hashes):
		data = {'magnets[]': hashes}
		response = self._post('magnet/instant', data)
		return response

	def check_single_magnet(self, hash_string):
		cache_info = self.check_cache(hash_string)['magnets'][0]
		return cache_info['instant']

	def user_cloud(self):
		url = 'magnet/status'
		string = 'ad_user_cloud'
		return cache_object(self._get, string, url, False, 0.03)

	def unrestrict_link(self, link):
		url = 'link/unlock'
		url_append = '&link=%s' % link
		response = self._get(url, url_append)
		try: return response['link']
		except: return None

	def create_transfer(self, magnet):
		url = 'magnet/upload'
		url_append = '&magnet=%s' % magnet
		result = self._get(url, url_append)
		result = result['magnets'][0]
		return result.get('id', '')

	def list_transfer(self, transfer_id):
		url = 'magnet/status'
		url_append = '&id=%s' % transfer_id
		result = self._get(url, url_append)
		result = result['magnets']
		return result

	def delete_transfer(self, transfer_id):
		url = 'magnet/delete'
		url_append = '&id=%s' % transfer_id
		result = self._get(url, url_append)
		return result.get('message', '') == 'Magnet was successfully deleted'

	def resolve_magnet(self, magnet_url, info_hash, store_to_cloud, title, season, episode):
		try:
			file_url, media_id, transfer_id = None, None, None
			extensions = supported_video_extensions()
			correct_files = []
			correct_files_append = correct_files.append
			transfer_id = self.create_transfer(magnet_url)
			elapsed_time, transfer_finished = 0, False
			sleep(1000)
			while elapsed_time <= 4 and not transfer_finished:
				transfer_info = self.list_transfer(transfer_id)
				if not transfer_info: break
				status_code = transfer_info['statusCode']
				if status_code > 4: break
				elapsed_time += 1
				if status_code == 4: transfer_finished = True
				elif status_code < 4: sleep(1000)
			if not transfer_finished:
				self.delete_transfer(transfer_id)
				return None
			valid_results = [i for i in transfer_info['links'] if any(i.get('filename').lower().endswith(x) for x in extensions) and not i.get('link', '') == '']
			if valid_results:
				if season:
					correct_files = [i for i in valid_results if seas_ep_filter(season, episode, i['filename'])]
					if correct_files:
						extras = [i for i in EXTRAS if not i == title.lower()]
						episode_title = re.sub(r'[^A-Za-z0-9-]+', '.', title.replace('\'', '').replace('&', 'and').replace('%', '.percent')).lower()
						try: media_id = [i['link'] for i in correct_files if not any(x in re.sub(episode_title, '', seas_ep_filter(season, episode, i['filename'], split=True)) \
											for x in extras)][0]
						except: media_id = None
				else: media_id = max(valid_results, key=lambda x: x.get('size')).get('link', None)
			if not store_to_cloud: Thread(target=self.delete_transfer, args=(transfer_id,)).start()
			if media_id:
				file_url = self.unrestrict_link(media_id)
				if not any(file_url.lower().endswith(x) for x in extensions): file_url = None
			return file_url
		except:
			try:
				if transfer_id: self.delete_transfer(transfer_id)
			except: pass
			return None
	
	def display_magnet_pack(self, magnet_url, info_hash):
		from modules.source_utils import supported_video_extensions
		try:
			transfer_id = None
			extensions = supported_video_extensions()
			transfer_id = self.create_transfer(magnet_url)
			elapsed_time, transfer_finished = 0, False
			sleep(1000)
			while elapsed_time <= 4 and not transfer_finished:
				transfer_info = self.list_transfer(transfer_id)
				if not transfer_info: break
				status_code = transfer_info['statusCode']
				if status_code > 4: break
				elapsed_time += 1
				if status_code == 4: transfer_finished = True
				elif status_code < 4: sleep(1000)
			if not transfer_finished:
				self.delete_transfer(transfer_id)
				return None
			end_results = []
			append = end_results.append
			for item in transfer_info.get('links'):
				if any(item.get('filename').lower().endswith(x) for x in extensions) and not item.get('link', '') == '':
					append({'link': item['link'], 'filename': item['filename'], 'size': item['size']})
			self.delete_transfer(transfer_id)
			return end_results
		except:
			try:
				if transfer_id: self.delete_transfer(transfer_id)
			except: pass
			return None

	def _get(self, url, url_append=''):
		result = None
		try:
			if self.token in ('empty_setting', ''): return None
			url = base_url + url + '?agent=%s&apikey=%s' % (user_agent, self.token) + url_append
			result = requests.get(url, timeout=timeout).json()
			if result.get('status') == 'success' and 'data' in result: result = result['data']
		except: pass
		return result

	def _post(self, url, data={}):
		result = None
		try:
			if self.token in ('empty_setting', ''): return None
			url = base_url + url + '?agent=%s&apikey=%s' % (user_agent, self.token)
			result = requests.post(url, data=data, timeout=timeout).json()
			if result.get('status') == 'success' and 'data' in result: result = result['data']
		except: pass
		return result

	def clear_cache(self, clear_hashes=True):
		try:
			from caches.debrid_cache import debrid_cache
			from caches.base_cache import connect_database
			dbcon = connect_database('maincache_db')
			# USER CLOUD
			try:
				dbcon.execute("""DELETE FROM maincache WHERE id=?""", ('ad_user_cloud',))
				user_cloud_success = True
			except: user_cloud_success = False
			# HASH CACHED STATUS
			if clear_hashes:
				try:
					debrid_cache.clear_debrid_results('ad')
					hash_cache_status_success = True
				except: hash_cache_status_success = False
			else: hash_cache_status_success = True
		except: return False
		if False in (user_cloud_success, hash_cache_status_success): return False
		return True
