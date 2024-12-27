import requests
from sys import argv, exit as sysexit
from threading import Thread
from urllib.parse import urlencode
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules import string_tools
from resources.lib.modules.source_utils import supported_video_extensions

getLS = control.lang
getSetting = control.setting
base_url = 'https://api.torbox.app/v1/api'
tb_icon = control.joinPath(control.artPath(), 'torbox.png')
addonFanart = control.addonFanart()

session = requests.Session()
session.mount(base_url, requests.adapters.HTTPAdapter(max_retries=1))

class TorBox:
	download = '/torrents/requestdl'
	download_usenet = '/usenet/requestdl'
	remove = '/torrents/controltorrent'
	remove_usenet = '/usenet/controlusenetdownload'
	stats = '/user/me'
	history = '/torrents/mylist'
	history_usenet = '/usenet/mylist'
	explore = '/torrents/mylist?id=%s'
	explore_usenet = '/usenet/mylist?id=%s'
	cache = '/torrents/checkcached'
	cloud = '/torrents/createtorrent'
	queued = '/torrents/getqueued'
	removeQueued = '/torrents/controlqueued'

	def __init__(self):
		self.name = 'TorBox'
		self.user_agent = 'Mozilla/5.0'
		self.api_key = getSetting('torboxtoken')
		self.sort_priority = getSetting('torbox.priority')
		self.store_to_cloud = getSetting('torbox.saveToCloud') == 'true'
		self.timeout = 28.0

	def _request(self, method, path, params=None, json=None, data=None):
		if not self.api_key: return
		session.headers['Authorization'] = 'Bearer %s' % self.api_key
		full_path = '%s%s' % (base_url, path)
		response = session.request(method, full_path, params=params, json=json, data=data, timeout=self.timeout)
		try: response.raise_for_status()
		except Exception as e: log_utils.log('torbox error', f"{e}\n{response.text}")
		try: result = response.json()
		except: result = {}
		return result

	def _GET(self, url, params=None):
		return self._request('get', url, params=params)

	def _POST(self, url, params=None, json=None, data=None):
		return self._request('post', url, params=params, json=json, data=data)

	def add_headers_to_url(self, url):
		return url + '|' + urlencode(self.headers())

	def headers(self):
		return {'User-Agent': self.user_agent}

	def account_info(self):
		return self._GET(self.stats)

	def torrent_info(self, request_id=''):
		url = self.explore % request_id
		return self._GET(url)

	def delete_torrent(self, request_id=''):
		data = {'torrent_id': request_id, 'operation': 'delete'}
		return self._POST(self.remove, json=data)

	def delete_torrent_queued(self, request_id=''):
		data = {'torrent_id': request_id, 'operation': 'delete'}
		return self._POST(self.removeQueued, json=data)
		
	def delete_usenet(self, request_id=''):
		data = {'usenet_id': request_id, 'operation': 'delete'}
		return self._POST(self.remove_usenet, json=data)
		
	def unrestrict_link(self, file_id):
		torrent_id, file_id = file_id.split(',')
		params = {'token': self.api_key, 'torrent_id': torrent_id, 'file_id': file_id}
		try: return self._GET(self.download, params=params)['data']
		except: return None
		
	def unrestrict_usenet(self, file_id):
		usenet_id, file_id = file_id.split(',')
		params = {'token': self.api_key, 'usenet_id': usenet_id, 'file_id': file_id}
		try: return self._GET(self.download_usenet, params=params)['data']
		except: return None

	def check_cache_single(self, hash):
		return self._GET(self.cache, params={'hash': hash, 'format': 'list'})

	def check_cache(self, hashlist):
		data = {'hashes': hashlist}
		return self._POST(self.cache, params={'format': 'list'}, json=data)

	def add_magnet(self, magnet):
		data = {'magnet': magnet, 'seed': 3, 'allow_zip': False}
		return self._POST(self.cloud, data=data)

	def create_transfer(self, magnet_url):
		result = self.add_magnet(magnet_url)
		if not result['success']: return ''
		return result['data'].get('torrent_id', '')

	def resolve_magnet(self, magnet_url, info_hash, season, episode, title):
		from resources.lib.modules.source_utils import seas_ep_filter, extras_filter
		try:
			file_url, match = None, False
			extensions = supported_video_extensions()
			extras_filtering_list = tuple(i for i in extras_filter() if not i in title.lower())
			check = self.check_cache_single(info_hash)
			match = info_hash in [i['hash'] for i in check['data']]
			if not match: return None
			torrent = self.add_magnet(magnet_url)
			if not torrent['success']: return None
			torrent_id = torrent['data']['torrent_id']
			torrent_files = self.torrent_info(torrent_id)
			selected_files = [
				{'link': '%d,%d' % (torrent_id, i['id']), 'filename': i['short_name'], 'size': i['size']}
				for i in torrent_files['data']['files'] if i['short_name'].lower().endswith(tuple(extensions))
			]
			if not selected_files: return None
			if season:
				selected_files = [i for i in selected_files if seas_ep_filter(season, episode, i['filename'])]
			else:
				if self._m2ts_check(selected_files): raise Exception('_m2ts_check failed')
				selected_files = [i for i in selected_files if not any(x in i['filename'] for x in extras_filtering_list)]
				selected_files.sort(key=lambda k: k['size'], reverse=True)
			if not selected_files: return None
			file_key = selected_files[0]['link']
			file_url = self.unrestrict_link(file_key)
			if not self.store_to_cloud: Thread(target=self.delete_torrent, args=(torrent_id,)).start()
			return file_url
		except Exception as e:
			log_utils.error('TorBox: Error RESOLVE MAGNET "%s" ' % magnet_url)
			if torrent_id: Thread(target=self.delete_torrent, args=(torrent_id,)).start()
			return None

	def display_magnet_pack(self, magnet_url, info_hash):
		try:
			extensions = supported_video_extensions()
			torrent = self.add_magnet(magnet_url)
			if not torrent['success']: return None
			torrent_id = torrent['data']['torrent_id']
			torrent_files = self.torrent_info(torrent_id)
			torrent_files = [
				{'link': '%d,%d' % (torrent_id, item['id']), 'filename': item['short_name'], 'size': item['size'] / 1073741824}
				for item in torrent_files['data']['files'] if item['short_name'].lower().endswith(tuple(extensions))
			]
			self.delete_torrent(torrent_id)
			return torrent_files
		except Exception:
			if torrent_id: self.delete_torrent(torrent_id)
			return None

	def add_uncached_torrent(self, magnet_url, pack=False):
		def _return_failed(message=getLS(33586)):
			try: self.progressDialog.close()
			except: pass
			self.delete_torrent(transfer_id)
			control.hide()
			control.sleep(500)
			control.okDialog(title=getLS(40018), message=message)
			return False
		control.busy()
		transfer_id = self.create_transfer(magnet_url)
		if not transfer_id: return _return_failed()
		transfer_info = self.list_transfer(transfer_id)
		if not transfer_info: return _return_failed()
		interval = 5
		line = '%s\n%s\n%s'
		line1 = '%s...' % (getLS(40017) % getLS(40529))
		line2 = transfer_info['name']
		if transfer_info['download_state'] == 'metaDL':
			line3 = 'Downloading torrent metadata from TorBox'
		else:
			line3 = transfer_info['download_state']
		if control.setting('dialogs.useumbrelladialog') == 'true':
			self.progressDialog = control.getProgressWindow(getLS(40018), None, 0)
			self.progressDialog.set_controls()
			self.progressDialog.update(0, line % (line1, line2, line3))
		else:
			self.progressDialog = control.progressDialog
			self.progressDialog.create(getLS(40018), line % (line1, line2, line3))
		while not transfer_info['download_state'] == 'completed':
			control.sleep(1000 * interval)
			transfer_info = self.list_transfer(transfer_id)
			file_size = transfer_info['size']
			line2 = transfer_info['name']
			if transfer_info['download_state'] == 'downloading':
				download_speed = round(float(transfer_info['download_speed']) / (1000**2), 2)
				progress = int(float(transfer_info['total_downloaded']) / file_size * 100) if file_size > 0 else 0
				line3 = getLS(40016) % (download_speed, transfer_info['seeds'], progress, round(float(file_size) / (1000 ** 3), 2))
			elif transfer_info['download_state'] == 'uploading':
				upload_speed = round(float(transfer_info['upload_speed']) / (1000 ** 2), 2)
				progress = int(float(transfer_info['total_uploaded']) / file_size * 100) if file_size > 0 else 0
				line3 = getLS(40015) % (upload_speed, progress, round(float(file_size) / (1000 ** 3), 2))
			elif transfer_info['download_state'] == 'stalledDL':
				line3 = 'Downloading is currently stalled. There are no seeds.'
				progress = int(float(transfer_info['total_downloaded']) / file_size * 100) if file_size > 0 else 0
			else:
				if transfer_info['download_state'] == 'metaDL':
					line3 = 'Downloading torrent metadata from TorBox'
				else:
					line3 = transfer_info['download_state']
				progress = 0
			self.progressDialog.update(progress, line % (line1, line2, line3))
			if control.monitor.abortRequested(): return sysexit()
			try:
				if self.progressDialog.iscanceled():
					if control.yesnoDialog('Delete TorBox download also?', 'No will continue the download', 'but close dialog','TorBox','No','Yes'):
						return _return_failed(getLS(40014))
					else:
						self.progressDialog.close()
						control.hide()
						return False
			except: pass
		control.sleep(1000 * interval)
		try: self.progressDialog.close()
		except: pass
		control.hide()
		return True

	def list_transfer(self, transferid):
		torrent_info = self.torrent_info(transferid)
		torrent_info = torrent_info['data']
		return torrent_info


	def _m2ts_check(self, folder_items):
		for item in folder_items:
			if item['filename'].endswith('.m2ts'): return True
		return False

	def auth(self):
		api_key = control.dialog.input('TorBox API Key:')
		if not api_key: return
		self.api_key = api_key
		try:
			r = self.account_info()
			customer = r['data']['customer']
			control.setSetting('torboxtoken', api_key)
			control.setSetting('torbox.username', customer)
			control.notification(message='TorBox succesfully authorized', icon=tb_icon)
			control.openSettings('10.4', 'plugin.video.umbrella')
			return True
		except:
			control.openSettings('10.4', 'plugin.video.umbrella')
			return control.notification(message='Error Authorizing TorBox', icon=tb_icon)

	def remove_auth(self):
		try:
			self.api_key = ''
			control.setSetting('torboxtoken', '')
			control.setSetting('torbox.username', '')
			control.notification(title='TorBox', message=40009, icon=tb_icon)
			control.openSettings('10.4', 'plugin.video.umbrella')
		except: log_utils.error()

	def account_info_to_dialog(self):
		try:
			control.busy()
			plans = {0: 'Free plan', 1: 'Essential plan', 2: 'Pro plan', 3: 'Standard plan'}
			account_info = self.account_info()
			account_info = account_info['data']
			items = []
			items += ['[B]Email[/B]: %s' % account_info['email']]
			items += ['[B]Customer[/B]: %s' % account_info['customer']]
			items += ['[B]Plan[/B]: %s' % plans[account_info['plan']]]
			items += ['[B]Expires[/B]: %s' % account_info['premium_expires_at']]
			items += ['[B]Downloaded[/B]: %s' % account_info['total_downloaded']]
			control.hide()
			return control.selectDialog(items, 'TorBox')
		except: log_utils.error()

	def user_cloud(self, request_id=None):
		url = self.explore % request_id if request_id else self.history
		return self._GET(url)

	def user_cloud_usenet(self, request_id=None):
		url = self.explore_usenet % request_id if request_id else self.history_usenet
		return self._GET(url)

	def user_cloud_clear(self):
		if not control.yesnoDialog(getLS(32056), '', ''): return
		data = {'all': True, 'operation': 'delete'}
		self._POST(self.remove, json=data)
		self._POST(self.remove_usenet, json=data)

	def user_cloud_to_listItem(self, folder_id=None):
		sysaddon, syshandle = 'plugin://plugin.video.umbrella/', int(argv[1])
		quote_plus = requests.utils.quote
		highlight_color = getSetting('highlight.color')
		folder_str, deleteMenu = getLS(40046).upper(), getLS(40050)
		file_str, downloadMenu = getLS(40047).upper(), getLS(40048)
		folders = []
		try: folders += [{**i, 'mediatype': 'torent'} for i in self.user_cloud()['data'] if i['download_finished']]
		except: pass
		try: folders += [{**i, 'mediatype': 'usenet'} for i in self.user_cloud_usenet()['data'] if i['download_finished']]
		except: pass
		folders.sort(key=lambda k: k['updated_at'], reverse=True)
		for count, item in enumerate(folders, 1):
			try:
				cm = []
				folder_name = string_tools.strip_non_ascii_and_unprintable(item['name'])
				status_str = '[COLOR %s]%s[/COLOR]' % (highlight_color, item['download_state'].capitalize())
				cm.append((deleteMenu % 'Torrent', 'RunPlugin(%s?action=tb_DeleteUserTorrent&id=%s&mediatype=%s&name=%s)' %
					(sysaddon, item['id'], item['mediatype'], quote_plus(folder_name))))
				label = '%02d | [B]%s[/B] | [B]%s[/B] | [I]%s [/I]' % (count, status_str, folder_str, folder_name)
				url = '%s?action=tb_BrowseUserTorrents&id=%s&mediatype=%s' % (sysaddon, item['id'], item['mediatype'])
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': tb_icon, 'poster': tb_icon, 'thumb': tb_icon, 'fanart': addonFanart, 'banner': tb_icon})
				item.setInfo(type='video', infoLabels='')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def browse_user_torrents(self, folder_id, mediatype):
		sysaddon, syshandle = 'plugin://plugin.video.umbrella/', int(argv[1])
		quote_plus = requests.utils.quote
		extensions = supported_video_extensions()
		file_str, downloadMenu = getLS(40047).upper(), getLS(40048)
		files = self.user_cloud_usenet(folder_id) if mediatype == 'usenet' else self.user_cloud(folder_id)
		video_files = [i for i in files['data']['files'] if i['short_name'].lower().endswith(tuple(extensions))]
		for count, item in enumerate(video_files, 1):
			try:
				cm = []
				name = string_tools.strip_non_ascii_and_unprintable(item['short_name'])
				size = item['size']
				display_size = float(int(size)) / 1073741824
				label = '%02d | [B]%s[/B] | %.2f GB | [I]%s [/I]' % (count, file_str, display_size, name)
				item = '%d,%d' % (int(folder_id), item['id'])
				url = '%s?action=play_URL&url=%s&caller=torbox&mediatype=%s&type=unrestrict' % (sysaddon, item, mediatype)
				cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&url=%s&caller=torbox&mediatype=%s&type=unrestrict)' %
					(sysaddon, quote_plus(name), quote_plus(tb_icon), item, mediatype)))
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': tb_icon, 'poster': tb_icon, 'thumb': tb_icon, 'fanart': addonFanart, 'banner': tb_icon})
				item.setInfo(type='video', infoLabels='')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def delete_user_torrent(self, request_id, mediatype, name, multi=False):
		if multi == False:
			if not control.yesnoDialog(getLS(40050) % '?\n' + name, '', ''): return
		result = self.delete_usenet(request_id) if mediatype == 'usenet' else self.delete_torrent(request_id)
		if result['success']:
			control.notification(message='TorBox: %s was removed' % name, icon=tb_icon)
			if not multi: control.refresh()

	def delete_queued_torrent(self, request_id, name, multi=False):
		if multi == False:
			if not control.yesnoDialog(getLS(40050) % '?\n' + name, '', ''): return
		result = self.delete_torrent(request_id)
		if result['success']:
			control.notification(message='TorBox: %s was removed' % name, icon=tb_icon)
			if not multi: control.refresh()

	def queued_torrents(self):
		url = self.queued
		return self._GET(url)

	def delete_all_user_torrents(self):
		files = self.user_cloud().get('data', [])
		que_files = self.queued_torrents().get('data', [])
		list_len = int(len(files)) + int(len(que_files))
		if list_len < 1: return control.notification(title='Torbox', message='No Files found to remove.', icon=tb_icon)
		threads = []
		append = threads.append
		len_files = len(files)
		len_que_files = len(que_files)
		progressBG = control.progressDialogBG
		progressBG.create('TorBox', 'Clearing cloud files')
		for count, req in enumerate(files, 1):
			try:
				i = Thread(target=self.delete_torrent, args=(req['id'],))
				append(i)
				i.start()
				progressBG.update(int(count / len_files * 100), 'Deleting %s...' % req['name'])
				control.sleep(200)
			except: pass
		for count, req in enumerate(que_files, 1):
			try:
				i = Thread(target=self.delete_torrent, args=(req['id'],))
				append(i)
				i.start()
				progressBG.update(int(count / len_que_files * 100), 'Deleting %s...' % req['name'])
				control.sleep(200)
			except: pass
		[i.join() for i in threads]
		try: progressBG.close()
		except: pass

	def delete_active_torrents(self, data):
		if not control.yesnoDialog(getLS(40543), '', ''): return
		data = data.get('data',[])
		for torrent in data:
			name = torrent.get('name','Unknown')
			request_id = torrent.get('id')
			mediatype = torrent.get('mediatype')
			self.delete_user_torrent(request_id, mediatype, name, multi=True)

	def delete_queued_torrents(self, data):
		if not control.yesnoDialog(getLS(40544), '', ''): return
		data = data.get('data',[])
		for torrent in data:
			name = torrent.get('name','Unknown')
			request_id = torrent.get('id')
			self.delete_torrent(request_id, name, multi=True)