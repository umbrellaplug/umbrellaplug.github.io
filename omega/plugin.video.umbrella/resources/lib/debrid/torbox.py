import requests
from sys import argv, exit as sysexit
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed
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
	history_webdl = '/webdl/mylist'
	explore = '/torrents/mylist?id=%s'
	explore_usenet = '/usenet/mylist?id=%s'
	explore_webdl = '/webdl/mylist?id=%s'
	cache = '/torrents/checkcached'
	cloud = '/torrents/createtorrent'
	queued = '/torrents/getqueued'
	removeQueued = '/torrents/controlqueued'
	download_webdl = '/webdl/requestdl'
	remove_webdl = '/webdl/controlwebdownload'

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
		except Exception as e: 
			log_utils.log('torbox error', f"{e}\n{response.text}")
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

	def delete_webdl(self, request_id=''):
		data = {'webdl_id': request_id, 'operation': 'delete'}
		return self._POST(self.remove_webdl, json=data)
		
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

	def unrestrict_webdl(self, file_id):
		webdl_id, file_id = file_id.split(',')
		params = {'token': self.api_key, 'web_id': webdl_id, 'file_id': file_id}
		try: return self._GET(self.download_webdl, params=params)['data']
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
			match = info_hash.lower() in [i['hash'].lower() for i in check['data']]
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
			#self.delete_torrent(torrent_id)
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
		show_popup = control.setting('torrent.cacheprogress.dialog') != 'false'
		if show_popup:
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
			if show_popup:
				self.progressDialog.update(progress, line % (line1, line2, line3))
			if control.monitor.abortRequested(): return sysexit()
			if show_popup:
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
		if show_popup:
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
		highlight_color = getSetting('highlight.color')
		line = '%s\n%s\n%s'
		try:
			response = requests.get('%s/user/auth/device/start?app=Umbrella' % base_url, timeout=self.timeout)
			response.raise_for_status()
			result = response.json()
			if not result.get('success'):
				return control.notification(message='TorBox: Failed to start authorization', icon=tb_icon)
			data = result['data']
			device_code = data['device_code']
			user_code = data['code']
			verify_url = data.get('friendly_verification_url', data.get('verification_url', 'https://torbox.app/oauth/device'))
			interval = int(data.get('interval', 5))
			token_ttl = 600
			expiry = token_ttl
			if getSetting('dialogs.useumbrelladialog') == 'true':
				from resources.lib.modules import tools
				tb_qr = tools.make_qr(verify_url, 'tb_qr.png')
				self.progressDialog = control.getProgressWindow('TorBox', tb_qr, 1 if tb_qr else 0)
				self.progressDialog.set_controls()
			else:
				self.progressDialog = control.progressDialog
				self.progressDialog.create('TorBox')
			self.progressDialog.update(0, line % (getLS(32513) % (highlight_color, verify_url), getLS(32514) % (highlight_color, user_code), getLS(40390)))
			access_token = None
			while not access_token and token_ttl > 0 and not self.progressDialog.iscanceled():
				control.sleep(interval * 1000)
				token_ttl -= interval
				progress_percent = 100 - int(float(expiry - token_ttl) / expiry * 100)
				self.progressDialog.update(progress_percent, line % (getLS(32513) % (highlight_color, verify_url), getLS(32514) % (highlight_color, user_code), getLS(40390)))
				try:
					poll = requests.post('%s/user/auth/device/token' % base_url, json={'device_code': device_code}, timeout=self.timeout)
					poll_result = poll.json()
					if poll_result.get('success') and isinstance(poll_result.get('data'), dict):
						access_token = poll_result['data'].get('access_token')
				except: pass
			self.progressDialog.close()
			if not access_token:
				return control.notification(message='TorBox: Authorization timed out or cancelled', icon=tb_icon)
			self.api_key = access_token
			r = self.account_info()
			customer = r['data']['customer']
			control.setSetting('torboxtoken', access_token)
			control.setSetting('torbox.username', customer)
			control.notification(message='TorBox successfully authorized', icon=tb_icon)
			control.openSettings('9.6', 'plugin.video.umbrella')
			return True
		except:
			log_utils.error('TorBox auth: ')
			try: self.progressDialog.close()
			except: pass
			control.notification(message='Error Authorizing TorBox', icon=tb_icon)

	def remove_auth(self):
		try:
			self.api_key = ''
			control.setSetting('torboxtoken', '')
			control.setSetting('torbox.username', '')
			control.notification(title='TorBox', message=40009, icon=tb_icon)
			control.openSettings('9.6', 'plugin.video.umbrella')
		except: log_utils.error()

	def referral_link(self):
		highlight_color = getSetting('highlight.color')
		referral_url = 'https://torbox.app/subscription?referral=6463de7b-29aa-4efb-bc5b-3deda767faa6'
		token_ttl = 15
		expiry = token_ttl
		progressDialog = None
		try:
			if getSetting('dialogs.useumbrelladialog') == 'true':
				from resources.lib.modules import tools
				tb_qr = tools.make_qr(referral_url, 'tb_referral_qr.png')
				progressDialog = control.getProgressWindow(getLS(40671), tb_qr, 1 if tb_qr else 0)
				progressDialog.set_controls()
			else:
				progressDialog = control.progressDialog
				progressDialog.create(getLS(40671))
			line = '%s\n%s' % ('[COLOR %s][B]Umbrella Torbox Referral Link[/B][/COLOR]' % highlight_color, referral_url)
			progressDialog.update(0, line)
			while token_ttl > 0 and not progressDialog.iscanceled():
				control.sleep(1000)
				token_ttl -= 1
				progress_percent = int(float(expiry - token_ttl) / expiry * 100)
				progressDialog.update(progress_percent, line)
			progressDialog.close()
		except:
			log_utils.error('TorBox referral_link: ')
			try: progressDialog.close()
			except: pass

	def account_info_to_dialog(self):
		try:
			control.busy()
			plans = {0: 'Free plan', 1: 'Essential plan', 2: 'Pro plan', 3: 'Standard plan'}
			account_info = self.account_info()
			account_info = account_info['data']
			items = []
			items += ['[B]Email[/B]: %s' % account_info['email']]
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

	def user_cloud_webdl(self, request_id=None):
		url = self.explore_webdl % request_id if request_id else self.history_webdl
		return self._GET(url)

	def user_cloud_clear(self):
		if not control.yesnoDialog(getLS(32056), '', ''): return
		data = {'all': True, 'operation': 'delete'}
		self._POST(self.remove, json=data)
		self._POST(self.remove_usenet, json=data)
		self._POST(self.remove_webdl, json=data)

	def user_cloud_to_listItem(self, folder_id=None):
		sysaddon, syshandle = 'plugin://plugin.video.umbrella/', int(argv[1])
		quote_plus = requests.utils.quote
		highlight_color = getSetting('highlight.color')
		folder_str, deleteMenu = getLS(40046).upper(), getLS(40050)
		file_str, downloadMenu = getLS(40047).upper(), getLS(40048)
		folders = []
		try:
			torrent_response = self.user_cloud()
			folders += [{**i, 'mediatype': 'torent'} for i in (torrent_response['data'] or []) if i.get('download_finished') or i.get('download_state') == 'completed']
		except: pass
		try:
			usenet_response = self.user_cloud_usenet()
			folders += [{**i, 'mediatype': 'usenet'} for i in (usenet_response['data'] or []) if i.get('download_finished') or i.get('download_state') == 'completed']
		except: pass
		try:
			webdl_response = self.user_cloud_webdl()
			folders += [{**i, 'mediatype': 'webdl'} for i in (webdl_response['data'] or []) if i.get('download_finished') or i.get('download_state') == 'completed']
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
		if mediatype == 'usenet': files = self.user_cloud_usenet(folder_id)
		elif mediatype == 'webdl': files = self.user_cloud_webdl(folder_id)
		else: files = self.user_cloud(folder_id)
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
		if mediatype == 'usenet': result = self.delete_usenet(request_id)
		elif mediatype == 'webdl': result = self.delete_webdl(request_id)
		else: result = self.delete_torrent(request_id)
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
		if not control.yesnoDialog(getLS(40546), '', ''):
			return

		files = self.user_cloud().get('data', [])
		que_files = self.queued_torrents().get('data', [])
		usenet_files = self.user_cloud_usenet().get('data', [])
		webdl_files = self.user_cloud_webdl().get('data', [])
		all_files = [
			{'type': 'torrent', 'id': req['id'], 'name': req['name']}
			for req in (files or [])
		] + [
			{'type': 'queue', 'id': req['id'], 'name': req['name']}
			for req in (que_files or [])
		] + [
			{'type': 'usenet', 'id': req['id'], 'name': req['name']}
			for req in (usenet_files or [])
		] + [
			{'type': 'webdl', 'id': req['id'], 'name': req['name']}
			for req in (webdl_files or [])
		]

		total_files = len(all_files)
		if total_files < 1:
			return control.notification(title='Torbox', message='No Files found to remove.', icon=tb_icon)

		progressBG = control.progressDialogBG
		progressBG.create('TorBox', 'Clearing cloud files')

		_unlimited = control.setting('dev.batch.unlimited') == 'true'
		_bs = None if _unlimited else max(int(control.setting('dev.batch.size') or '10'), 1)
		try:
			with ThreadPoolExecutor(max_workers=_bs) as executor:
				futures = {}
				for count, req in enumerate(all_files, 1):
					if req['type'] == 'torrent' or req['type'] == 'queue':
						futures[executor.submit(self.delete_torrent, req['id'])] = req
					elif req['type'] == 'usenet':
						futures[executor.submit(self.delete_usenet, req['id'])] = req
					elif req['type'] == 'webdl':
						futures[executor.submit(self.delete_webdl, req['id'])] = req

				for completed_count, future in enumerate(as_completed(futures), 1):
					req = futures[future]
					try:
						future.result()  # Ensure thread execution errors are handled
						progressBG.update(
							int(completed_count / total_files * 100),
							f"Deleting {req['name']}..."
						)
						control.sleep(200)
					except Exception as e:
						log_utils.error(f"Error deleting file {req['name']}: {str(e)}")
		except Exception as e:
			log_utils.error(f"Error deleting all user torrents: {str(e)}")
		finally:
			try:
				progressBG.close()
			except:
				pass

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