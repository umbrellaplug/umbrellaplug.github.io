import re
import requests
from sys import argv, exit as sysexit
from concurrent.futures import ThreadPoolExecutor, as_completed
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules import string_tools
from resources.lib.modules.source_utils import supported_video_extensions

getLS = control.lang
getSetting = control.setting
base_url = 'https://offcloud.com/api'
oauth_base = 'https://offcloud.com/oauth'
oc_icon = control.joinPath(control.artPath(), 'offcloud.png')
addonFanart = control.addonFanart()

session = requests.Session()
session.mount(base_url, requests.adapters.HTTPAdapter(max_retries=1))

class Offcloud:
	remove = '/cloud/remove/%s'
	history = '/cloud/history'
	explore = '/cloud/explore/%s'
	status = '/cloud/status'
	cache = '/cache'
	cache_download = '/cache/download'
	cloud = '/cloud'

	def __init__(self):
		self.name = 'Offcloud'
		self.api_key = getSetting('offcloudtoken')
		self.sort_priority = getSetting('offcloud.priority')
		self.timeout = 3.05

	def _request(self, method, path, params=None, data=None, base=None):
		headers = {}
		if self.api_key:
			headers['Authorization'] = 'Bearer %s' % self.api_key
		full_path = '%s%s' % (base or base_url, path)
		r = session.request(method, full_path, params=params, json=data, headers=headers, timeout=self.timeout)
		try: r.raise_for_status()
		except Exception as e: log_utils.log('offcloud error %s' % str(e))
		try: r = r.json()
		except: r = {}
		return r

	def _GET(self, url, base=None):
		return self._request('get', url, base=base)

	def _POST(self, url, data=None, base=None):
		return self._request('post', url, data=data, base=base)

	@staticmethod
	def requote_uri(url):
		return requests.utils.requote_uri(url)

	def account_info(self):
		return self._GET('/account/info')

	def torrent_info(self, request_id=''):
		url = self.explore % request_id
		return self._GET(url)

	def delete_torrent(self, request_id=''):
		return self._GET(self.remove % request_id)

	def check_cache(self, hashlist):
		data = {'hashes': hashlist}
		return self._POST(self.cache, data=data)

	def add_magnet(self, magnet):
		data = {'url': magnet}
		return self._POST(self.cloud, data=data)

	def create_transfer(self, magnet_url):
		result = self.add_magnet(magnet_url)
		if result.get('status') not in ('created', 'downloaded'): return None
		return result

	def resolve_magnet(self, magnet_url, info_hash, season, episode, title):
		from resources.lib.modules.source_utils import seas_ep_filter, extras_filter
		try:
			extensions = supported_video_extensions()
			extras_filtering_list = extras_filter()
			match = info_hash.lower() in self.check_cache([info_hash]).get('cachedItems', [])
			if not match: return None
			files = self._POST(self.cache_download, data={'url': magnet_url})
			if not isinstance(files, list) or not files: return None
			selected = [f for f in files if f.get('filename', '').lower().endswith(tuple(extensions))]
			if not selected: return None
			if season:
				selected = [f for f in selected if seas_ep_filter(season, episode, f['filename'])]
			else:
				if self._m2ts_check(selected): raise Exception('_m2ts_check failed')
				selected = [f for f in selected if not any(x in f['filename'] for x in extras_filtering_list)]
			if not selected: return None
			return selected[0]['url']
		except:
			log_utils.error('Offcloud: Error RESOLVE MAGNET "%s"' % magnet_url)
			return None

	def display_magnet_pack(self, magnet_url, info_hash):
		try:
			extensions = supported_video_extensions()
			files = self._POST(self.cache_download, data={'url': magnet_url})
			if not isinstance(files, list): return None
			return [
				{'link': f['url'], 'filename': f['filename'], 'size': f.get('size', 0)}
				for f in files if f.get('filename', '').lower().endswith(tuple(extensions))
			]
		except:
			log_utils.error()
			return None

	def add_uncached_torrent(self, magnet_url, pack=False):
		control.busy()
		result = self.create_transfer(magnet_url)
		control.hide()
		if result: control.okDialog(title='default', message=getLS(40017) % 'Offcloud')
		else: control.okDialog(title=getLS(40018), message=getLS(33586))
		if result and result.get('status') == 'downloaded': return True
		return None

	def _m2ts_check(self, folder_items):
		for item in folder_items:
			if item.get('filename', '').endswith('.m2ts'): return True
		return False

	def _auth_poll(self):
		data = {
			'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
			'device_code': self.device_code
		}
		try:
			r = session.post('%s/token' % oauth_base, json=data, timeout=self.timeout)
			r = r.json()
		except: return
		error = r.get('error')
		if error == 'authorization_pending':
			return
		elif error == 'slow_down':
			self.poll_interval += 5
		elif error in ('expired_token', 'access_denied'):
			self.progressDialog.close()
			self.token = 'failed'
			control.notification(message='Offcloud: %s' % error)
		elif r.get('access_token'):
			self.progressDialog.close()
			self.token = r['access_token']

	def auth(self):
		try:
			r = session.post('%s/device/code' % oauth_base, json={}, timeout=self.timeout)
			r = r.json()
		except:
			control.notification(message='Offcloud: Failed to reach authorization server')
			return
		device_code = r.get('device_code')
		user_code = r.get('user_code')
		verify_url = r.get('verification_uri_complete') or r.get('verification_uri', 'https://offcloud.com/activate')
		expires_in = r.get('expires_in', 600)
		interval = r.get('interval', 5)
		if not device_code:
			control.notification(message='Offcloud: Authorization Failed')
			return
		highlight_color = getSetting('highlight.color')
		heading = 'Offcloud'
		if getSetting('dialogs.useumbrelladialog') == 'true':
			from resources.lib.modules import tools
			qr_image = tools.make_qr(verify_url, 'oc_qr.png')
			self.progressDialog = control.getProgressWindow(heading, qr_image, 1)
			self.progressDialog.set_controls()
		else:
			self.progressDialog = control.progressDialog
			self.progressDialog.create(heading)
		line = '%s\n%s' % (
			getLS(32513) % (highlight_color, 'https://offcloud.com/activate'),
			getLS(32514) % (highlight_color, user_code)
		)
		self.progressDialog.update(0, line)
		self.token = None
		self.device_code = device_code
		self.poll_interval = interval
		token_ttl = expires_in
		while not self.token:
			if self.progressDialog.iscanceled():
				self.progressDialog.close()
				return
			if token_ttl <= 0:
				self.progressDialog.close()
				control.notification(message='Offcloud: Authorization timed out')
				return
			control.sleep(self.poll_interval * 1000)
			token_ttl -= self.poll_interval
			self._auth_poll()
		if self.token == 'failed': return
		control.setSetting('offcloudtoken', self.token)
		self.api_key = self.token
		info = self.account_info()
		control.setSetting('offcloud.username', info.get('user_id') or info.get('userId') or info.get('email', ''))
		control.notification(message='Offcloud successfully authorized', icon=oc_icon)
		control.openSettings('9.3', 'plugin.video.umbrella')

	def remove_auth(self):
		try:
			self.api_key = ''
			control.setSetting('offcloudtoken', '')
			control.setSetting('offcloud.username', '')
			control.okDialog(title='Offcloud', message=40009)
			control.openSettings('9.3', 'plugin.video.umbrella')
		except: log_utils.error()

	def account_info_to_dialog(self):
		try:
			info = self.account_info()
			# Handle both new field names and old compatibility names
			user_id = info.get('user_id') or info.get('userId', '')
			email = info.get('email', '')
			is_premium = info.get('is_premium') if 'is_premium' in info else info.get('isPremium', '')
			expires = info.get('expiration_date') or info.get('expirationDate', '')
			can_download = info.get('can_download', '')
			cloud_limit = (info.get('limits') or {}).get('cloud', '')
			items = []
			if email: items.append('[B]Email[/B]: %s' % email)
			if user_id: items.append('[B]User ID[/B]: %s' % user_id)
			items.append('[B]Premium[/B]: %s' % is_premium)
			items.append('[B]Expires[/B]: %s' % (expires or 'N/A'))
			if can_download != '': items.append('[B]Can Download[/B]: %s' % can_download)
			if cloud_limit: items.append('[B]Cloud Limit[/B]: {:,}'.format(cloud_limit))
			if not items: return
			return control.selectDialog(items, 'Offcloud')
		except: log_utils.error()

	def user_cloud(self):
		return self._GET(self.history)

	def user_cloud_clear(self):
		if not control.yesnoDialog(getLS(32056), '', ''):
			return
		files = self.user_cloud()
		if not files:
			return
		len_files = len(files)
		progressBG = control.progressDialogBG
		progressBG.create('Offcloud', 'Clearing cloud files')
		_unlimited = control.setting('dev.batch.unlimited') == 'true'
		_bs = None if _unlimited else int(control.setting('dev.batch.size') or '10')
		try:
			with ThreadPoolExecutor(max_workers=_bs) as executor:
				futures = {
					executor.submit(self.delete_torrent, req['requestId']): req
					for req in files
				}
				for count, future in enumerate(as_completed(futures), 1):
					req = futures[future]
					try:
						future.result()
						progressBG.update(int(count / len_files * 100), 'Deleting %s...' % req['fileName'])
						control.sleep(200)
					except Exception as e:
						log_utils.error('Error deleting file %s: %s' % (req['fileName'], str(e)))
		except Exception as e:
			log_utils.error('Error clearing cloud files: %s' % str(e))
		finally:
			try: progressBG.close()
			except: pass

	def user_cloud_to_listItem(self, folder_id=None):
		sysaddon, syshandle = 'plugin://plugin.video.umbrella/', int(argv[1])
		quote_plus = requests.utils.quote
		highlight_color = getSetting('highlight.color')
		folder_str, deleteMenu = getLS(40046).upper(), getLS(40050)
		file_str, downloadMenu = getLS(40047).upper(), getLS(40048)
		try:
			cloud_dict = self.user_cloud()
		except Exception as e:
			log_utils.error('Offcloud user_cloud failed: %s' % str(e))
			control.notification(message='Offcloud: Failed to retrieve cloud items', icon=oc_icon)
			control.content(syshandle, 'files')
			control.directory(syshandle, cacheToDisc=False)
			return
		if not cloud_dict:
			control.content(syshandle, 'files')
			control.directory(syshandle, cacheToDisc=False)
			return
		cloud_dict = [i for i in cloud_dict if i.get('status') == 'downloaded']
		for count, item in enumerate(cloud_dict, 1):
			try:
				cm = []
				folder_name = string_tools.strip_non_ascii_and_unprintable(item['fileName'])
				request_id = item['requestId']
				status_str = '[COLOR %s]%s[/COLOR]' % (highlight_color, item.get('status', '').capitalize())
				cm.append((deleteMenu % 'Torrent', 'RunPlugin(%s?action=oc_DeleteUserTorrent&id=%s&name=%s)' %
					(sysaddon, request_id, quote_plus(folder_name))))
				# Use torrent_info to determine if single or multi-file
				torrent_files = self.torrent_info(request_id)
				is_folder = isinstance(torrent_files, list) and len(torrent_files) > 0
				if is_folder:
					label = '%02d | [B]%s[/B] | [B]%s[/B] | [I]%s [/I]' % (count, status_str, folder_str, folder_name)
					url = '%s?action=oc_BrowseUserTorrents&id=%s' % (sysaddon, request_id)
				else:
					# Single file — get URL via cache/download using original link
					label = '%02d | [B]%s[/B] | [B]%s[/B] | [I]%s [/I]' % (count, status_str, file_str, folder_name)
					original_link = item.get('originalLink', '')
					link = ''
					if original_link:
						dl_files = self._POST(self.cache_download, data={'url': original_link})
						if isinstance(dl_files, list) and dl_files:
							link = self.requote_uri(dl_files[0].get('url', ''))
					url = '%s?action=play_URL&url=%s&caller=offcloud&type=direct' % (sysaddon, link) if link else ''
					if link:
						cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&url=%s&caller=offcloud&type=direct)' %
							(sysaddon, quote_plus(folder_name), quote_plus(oc_icon), link)))
				listitem = control.item(label=label, offscreen=True)
				listitem.addContextMenuItems(cm)
				listitem.setArt({'icon': oc_icon, 'poster': oc_icon, 'thumb': oc_icon, 'fanart': addonFanart, 'banner': oc_icon})
				listitem.setInfo(type='video', infoLabels='')
				control.addItem(handle=syshandle, url=url, listitem=listitem, isFolder=is_folder)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def browse_user_torrents(self, folder_id):
		sysaddon, syshandle = 'plugin://plugin.video.umbrella/', int(argv[1])
		quote_plus = requests.utils.quote
		extensions = supported_video_extensions()
		file_str, downloadMenu = getLS(40047).upper(), getLS(40048)
		torrent_files = self.torrent_info(folder_id)
		if not isinstance(torrent_files, list): return
		video_files = [i for i in torrent_files if i.lower().endswith(tuple(extensions))]
		for count, item in enumerate(video_files, 1):
			try:
				cm = []
				name = string_tools.strip_non_ascii_and_unprintable(item.split('/')[-1])
				label = '%02d | [B]%s[/B] | [I]%s [/I]' % (count, file_str, name)
				item = self.requote_uri(item)
				url = '%s?action=play_URL&url=%s&caller=offcloud&type=direct' % (sysaddon, item)
				cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&url=%s&caller=offcloud&type=direct)' %
					(sysaddon, quote_plus(name), quote_plus(oc_icon), item)))
				listitem = control.item(label=label, offscreen=True)
				listitem.addContextMenuItems(cm)
				listitem.setArt({'icon': oc_icon, 'poster': oc_icon, 'thumb': oc_icon, 'fanart': addonFanart, 'banner': oc_icon})
				listitem.setInfo(type='video', infoLabels='')
				control.addItem(handle=syshandle, url=url, listitem=listitem, isFolder=False)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def delete_user_torrent(self, request_id, name):
		if not control.yesnoDialog(getLS(40050) % '?\n' + name, '', ''): return
		result = self.delete_torrent(request_id)
		if result.get('success'):
			control.notification(message='Offcloud: %s was removed' % name, icon=oc_icon)
			control.refresh()
