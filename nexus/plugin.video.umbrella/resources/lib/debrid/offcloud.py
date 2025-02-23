import re
import requests
from sys import argv, exit as sysexit
from threading import Thread
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules import string_tools
from resources.lib.modules.source_utils import supported_video_extensions

getLS = control.lang
getSetting = control.setting
base_url = 'https://offcloud.com/api'
oc_icon = control.joinPath(control.artPath(), 'offcloud.png')
addonFanart = control.addonFanart()

session = requests.Session()
session.mount(base_url, requests.adapters.HTTPAdapter(max_retries=1))

class Offcloud:
	download = 'https://%s.offcloud.com/cloud/download/%s/%s'
	zip = 'https://%s.offcloud.com/cloud/zip/%s/%s.zip'
	remove = 'https://offcloud.com/cloud/remove/%s' # undocumented
	stats = '/account/stats' # undocumented
	history = '/cloud/history' # undocumented
	explore = '/cloud/explore/%s'
	files = '/cloud/list/%s'
	status = '/cloud/status'
	cache = '/cache'
	cloud = '/cloud'

	def __init__(self):
		self.name = 'Offcloud'
		self.api_key = getSetting('offcloudtoken')
		self.sort_priority = getSetting('offcloud.priority')
		self.timeout = 3.05

	def _request(self, method, path, params=None, data=None):
		if not self.api_key: pass
		elif not params: params = {'key': self.api_key}
		else: params['key'] = self.api_key
		full_path = '%s%s' % (base_url, path)
		r = session.request(method, full_path, params=params, json=data, timeout=self.timeout)
		try: r.raise_for_status()
		except Exception as e: log_utils.log('offcloud error %s' % str(e))
		try: r = r.json()
		except: r = {}
		return r

	def _GET(self, url):
		return self._request('get', url)

	def _POST(self, url, data=None):
		return self._request('post', url, data=data)

	@staticmethod
	def requote_uri(url):
		return requests.utils.requote_uri(url)

	def build_url(self, server, request_id, file_name):
		return self.download % (server, request_id, file_name)

	def build_zip(self, server, request_id, file_name):
		return self.zip % (server, request_id, file_name)

	def requestid_from_url(self, url):
		match = re.search(r'download/[A-Za-z0-9]+/', url)
		if not match: return None
		request_id = match.group(0).split('/')[-2]
		return request_id

	def account_info(self):
		return self._GET(self.stats)

	def torrent_info(self, request_id=''):
		url = self.explore % request_id
		return self._GET(url)

	def delete_torrent(self, request_id=''):
		params = {'key': self.api_key}
		url = self.remove % request_id
		r = session.get(url, params=params, timeout=self.timeout)
		try: r = r.json()
		except: r = {}
		return r

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
			file_url, match = None, False
			extensions = supported_video_extensions()
			extras_filtering_list = extras_filter()
			match = info_hash.lower() in self.check_cache([info_hash]).get('cachedItems', [])
			if not match: return None
			torrent = self.add_magnet(magnet_url)
			if not torrent['status'] == 'downloaded': return None
			single_file_torrent = '%s/%s' % (torrent['url'], torrent['fileName'])
			torrent_id = torrent['requestId']
			torrent_files = self.torrent_info(torrent_id)
			if not isinstance(torrent_files, list): torrent_files = [single_file_torrent]
			selected_files = [
				{'link': i, 'filename': i.split('/')[-1], 'size': 0}
				for i in torrent_files if i.lower().endswith(tuple(extensions))
			]
			if not selected_files: return None
			if season:
				selected_files = [i for i in selected_files if seas_ep_filter(season, episode, i['filename'])]
			else:
				if self._m2ts_check(selected_files): raise Exception('_m2ts_check failed')
				selected_files = [i for i in selected_files if not any(x in i['filename'] for x in extras_filtering_list)]
			if not selected_files: return None
			file_key = selected_files[0]['link']
			file_url = self.requote_uri(file_key) # requote, oc why give us a list of urls that may have spaces in name
			return file_url
		except Exception as e:
			log_utils.error('Offcloud: Error RESOLVE MAGNET "%s" ' % magnet_url)
			if torrent_id: self.delete_torrent(torrent_id)
			return None

	def display_magnet_pack(self, magnet_url, info_hash):
		try:
			extensions = supported_video_extensions()
			torrent = self.add_magnet(magnet_url)
			if not torrent['status'] == 'downloaded': return None
			torrent_id = torrent['requestId']
			torrent_files = self.torrent_info(torrent_id)
			torrent_files = [
				{'link': self.requote_uri(item), 'filename': item.split('/')[-1], 'size': 0}
				for item in torrent_files if item.lower().endswith(tuple(extensions))
			]
			#self.delete_torrent(torrent_id) # cannot delete the torrent, play link will not persist, will return 502
			return torrent_files
		except Exception:
			if torrent_id: self.delete_torrent(torrent_id)
			return None

	def add_uncached_torrent(self, magnet_url, pack=False):
		control.busy()
		result = self.create_transfer(magnet_url)
		control.hide()
		if result: control.okDialog(title='default', message=getLS(40017) % 'Offcloud')
		else: control.okDialog(title=getLS(40018), message=getLS(33586))
		if result['status'] == 'downloaded': return True
		return None

	def _m2ts_check(self, folder_items):
		for item in folder_items:
			if item['filename'].endswith('.m2ts'): return True
		return False

	def auth(self):
		username = control.dialog.input('Offcloud Email:')
		password = control.dialog.input('Offcloud Password:', option=2)
		if not all((username, password)): return
		data = {'username': username, 'password': password}
		r = self._POST('/login', data=data)
		user_id = r.get('userId')
		if not user_id: control.notification(message='Offcloud Authorization Failed') ; return False
		r = self._POST('/key')
		api_key = r.get('apiKey')
		if not api_key: control.notification(message='Offcloud Authorization Failed') ; return False
		self.api_key = api_key
		control.setSetting('offcloudtoken', api_key)
		control.setSetting('offcloud.username', user_id)
		control.notification(message='Offcloud succesfully authorized', icon=oc_icon)
		control.openSettings('10.3', 'plugin.video.umbrella')
		return True

	def remove_auth(self):
		try:
			self.api_key = ''
			control.setSetting('offcloudtoken', '')
			control.setSetting('offcloud.username', '')
			control.okDialog(title='Offcloud', message=40009)
			control.openSettings('10.3', 'plugin.video.umbrella')
		except: log_utils.error()

	def account_info_to_dialog(self):
		try:
			account_info = self.account_info()
			items = []
			append = items.append
			append('[B]Email[/B]: %s' % account_info['email'])
			append('[B]userId[/B]: %s' % account_info['userId'])
			append('[B]Premium[/B]: %s' % account_info['isPremium'])
			append('[B]Expires[/B]: %s' % account_info['expirationDate'])
			append('[B]Cloud Limit[/B]: {:,}'.format(account_info['limits']['cloud']))
			return control.selectDialog(items, 'Offcloud')
		except: log_utils.error()

	def user_cloud(self):
		url = self.history
		return self._GET(url)

	def user_cloud_clear(self):
		if not control.yesnoDialog(getLS(32056), '', ''): return
		files = self.user_cloud()
		if not files: return
		threads = []
		append = threads.append
		len_files = len(files)
		progressBG = control.progressDialogBG
		progressBG.create('Offcloud', 'Clearing cloud files')
		for count, req in enumerate(files, 1):
			try:
				i = Thread(target=self.delete_torrent, args=(req['requestId'],))
				append(i)
				i.start()
				progressBG.update(int(count / len_files * 100), 'Deleting %s...' % req['fileName'])
				control.sleep(200)
			except: pass
		[i.join() for i in threads]
		try: progressBG.close()
		except: pass

	def user_cloud_to_listItem(self, folder_id=None):
		sysaddon, syshandle = 'plugin://plugin.video.umbrella/', int(argv[1])
		quote_plus = requests.utils.quote
		highlight_color = getSetting('highlight.color')
		folder_str, deleteMenu = getLS(40046).upper(), getLS(40050)
		file_str, downloadMenu = getLS(40047).upper(), getLS(40048)
		cloud_dict = self.user_cloud()
		cloud_dict = [i for i in cloud_dict if i['status'] == 'downloaded']
		for count, item in enumerate(cloud_dict, 1):
			try:
				cm = []
				is_folder = item['isDirectory']
				folder_name = string_tools.strip_non_ascii_and_unprintable(item['fileName'])
				request_id, server = item['requestId'], item['server']
				status_str = '[COLOR %s]%s[/COLOR]' % (highlight_color, item['status'].capitalize())
				cm.append((deleteMenu % 'Torrent', 'RunPlugin(%s?action=oc_DeleteUserTorrent&id=%s&name=%s)' %
					(sysaddon, request_id, quote_plus(folder_name))))
				if is_folder:
					label = '%02d | [B]%s[/B] | [B]%s[/B] | [I]%s [/I]' % (count, status_str, folder_str, folder_name)
					url = '%s?action=oc_BrowseUserTorrents&id=%s' % (sysaddon, request_id)
				else:
					label = '%02d | [B]%s[/B] | [B]%s[/B] | [I]%s [/I]' % (count, status_str, file_str, folder_name)
					link = self.requote_uri(self.build_url(server, request_id, folder_name))
					url = '%s?action=play_URL&url=%s&caller=offcloud&type=direct' % (sysaddon, link)
					cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&url=%s&caller=offcloud&type=direct)' %
						(sysaddon, quote_plus(name), quote_plus(oc_icon), link)))
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': oc_icon, 'poster': oc_icon, 'thumb': oc_icon, 'fanart': addonFanart, 'banner': oc_icon})
				item.setInfo(type='video', infoLabels='')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def browse_user_torrents(self, folder_id):
		sysaddon, syshandle = 'plugin://plugin.video.umbrella/', int(argv[1])
		quote_plus = requests.utils.quote
		extensions = supported_video_extensions()
		file_str, downloadMenu = getLS(40047).upper(), getLS(40048)
		torrent_files = self.torrent_info(folder_id)
		video_files = [i for i in torrent_files if i.lower().endswith(tuple(extensions))]
		for count, item in enumerate(video_files, 1):
			try:
				cm = []
				name = string_tools.strip_non_ascii_and_unprintable(item.split('/')[-1])
				label = '%02d | [B]%s[/B] | %.2f GB | [I]%s [/I]' % (count, file_str, 0, name)
				item = self.requote_uri(item)
				url = '%s?action=play_URL&url=%s&caller=offcloud&type=direct' % (sysaddon, item)
				cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&url=%s&caller=offcloud&type=direct)' %
					(sysaddon, quote_plus(name), quote_plus(oc_icon), item)))
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': oc_icon, 'poster': oc_icon, 'thumb': oc_icon, 'fanart': addonFanart, 'banner': oc_icon})
				item.setInfo(type='video', infoLabels='')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def delete_user_torrent(self, request_id, name):
		if not control.yesnoDialog(getLS(40050) % '?\n' + name, '', ''): return
		result = self.delete_torrent(request_id)
		if 'success' in result:
			control.notification(message='Offcloud: %s was removed' % name, icon=oc_icon)
			control.refresh()
