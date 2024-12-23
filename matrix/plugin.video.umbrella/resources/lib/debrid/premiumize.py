# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

import re
import requests
from requests.adapters import HTTPAdapter
from sys import argv, exit as sysexit
from urllib3.util.retry import Retry
from urllib.parse import quote_plus, urlencode
from resources.lib.database import cache
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules import string_tools
from resources.lib.modules.source_utils import supported_video_extensions

getLS = control.lang
getSetting = control.setting
CLIENT_ID = '149408327' # used to auth
BaseUrl = 'https://www.premiumize.me/api'
folder_list_url = '%s/folder/list' % BaseUrl
folder_rename_url = '%s/folder/rename' % BaseUrl
folder_delete_url = '%s/folder/delete' % BaseUrl
item_listall_url = '%s/item/listall' % BaseUrl
item_details_url = '%s/item/details' % BaseUrl
item_delete_url = '%s/item/delete' % BaseUrl
item_rename_url = '%s/item/rename' % BaseUrl
transfer_create_url = '%s/transfer/create' % BaseUrl
transfer_directdl_url = '%s/transfer/directdl' % BaseUrl
transfer_list_url = '%s/transfer/list' % BaseUrl
transfer_clearfinished_url = '%s/transfer/clearfinished' % BaseUrl
transfer_delete_url = '%s/transfer/delete' % BaseUrl
account_info_url = '%s/account/info' % BaseUrl
cache_check_url = '%s/cache/check' % BaseUrl
list_services_path_url = '%s/services/list' % BaseUrl
pm_icon = control.joinPath(control.artPath(), 'premiumize.png')
pm_qr = control.joinPath(control.artPath(), 'premiumizeqr.png')
addonFanart = control.addonFanart()
invalid_extensions = ('.bmp', '.exe', '.gif', '.jpg', '.nfo', '.part', '.png', '.rar', '.sample.', '.srt', '.txt', '.zip', '.clpi', '.mpls', '.bdmv', '.xml', '.crt', 'crl', 'sig')

session = requests.Session()
retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
session.mount('https://www.premiumize.me', HTTPAdapter(max_retries=retries, pool_maxsize=100))


class Premiumize:
	name = "Premiumize.me"
	sort_priority = getSetting('premiumize.priority')
	def __init__(self):
		self.hosts = []
		self.patterns = []
		self.token = getSetting('premiumizetoken')
		self.headers = {'User-Agent': 'Umbrella for Kodi', 'Authorization': 'Bearer %s' % self.token}
		self.server_notifications = getSetting('premiumize.server.notifications')
		self.store_to_cloud = getSetting('premiumize.saveToCloud') == 'true'
		self.highlightColor = control.setting('highlight.color')

	def _get(self, url):
		response = None
		try:
			if self.token == '':
				log_utils.log('No Premiumize.me Token Found')
				return None
			response = session.get(url, headers=self.headers, timeout=15).json()
			# if response.status_code in (200, 201): response = response.json() # need status code checking for server maintenance
			if 'status' in response:
				if response.get('status') == 'success': return response
				if response.get('status') == 'error':
					if self.server_notifications: control.notification(message=response.get('message'), icon=pm_icon)
					log_utils.log('Premiumize.me: %s' % response.get('message'), level=log_utils.LOGWARNING)
		except: log_utils.error()
		return response

	def _post(self, url, data={}):
		response = None
		if self.token == '': return None
		try:
			response = session.post(url, data, headers=self.headers, timeout=45).json() # disgusting temp timeout change to fix server response lag
			# if response.status_code in (200, 201): response = response.json() # need status code checking for server maintenance
			if 'status' in response:
				if response.get('status') == 'success': return response
				if response.get('status') == 'error':
					if 'You already have this job added' in response.get('message'): return None
					if self.server_notifications: control.notification(message=response.get('message'), icon=pm_icon)
					log_utils.log('Premiumize.me: %s' % response.get('message'), level=log_utils.LOGWARNING)
		except: log_utils.error()
		return response

	def auth(self, fromSettings=0):
		data = {'client_id': CLIENT_ID, 'response_type': 'device_code'}
		token = session.post('https://www.premiumize.me/token', data=data, timeout=15).json()
		expiry = float(token['expires_in'])
		token_ttl = token['expires_in']
		poll_again = True
		success = False
		line = '%s\n%s%s'
		#progressDialog = control.progressDialog
		#progressDialog.create(getLS(40054))
		if control.setting('dialogs.useumbrelladialog') == 'true':
			self.progressDialog = control.getProgressWindow(getLS(40054), pm_qr, 1)
			self.progressDialog.set_controls()
		else:
			self.progressDialog = control.progressDialog
			self.progressDialog.create(getLS(40054))
			self.progressDialog.update(-1, line % (getLS(32513) % (self.highlightColor,token['verification_uri']), getLS(32514) % (self.highlightColor, token['user_code']), getLS(40390)))
		# try:
		# 	from resources.lib.modules.source_utils import copy2clip
		# 	copy2clip(token['user_code'])
		# except:
		# 	log_utils.error()
		while poll_again and not token_ttl <= 0 and not self.progressDialog.iscanceled():
			poll_again, success = self.poll_token(token['device_code'], fromSettings=fromSettings)
			progress_percent = 100 - int((float((expiry - token_ttl) / expiry) * 100))
			self.progressDialog.update(progress_percent, line % (getLS(32513) % (self.highlightColor,token['verification_uri']), getLS(32514) % (self.highlightColor, token['user_code']), getLS(40390)))
			control.sleep(token['interval'] * 1000)
			token_ttl -= int(token['interval'])
		self.progressDialog.close()
		if success:
			if fromSettings == 1:
				control.openSettings('10.1', 'plugin.video.umbrella')
			control.notification(message=40052, icon=pm_icon)
			log_utils.log('Premiumize.me Successfully Authorized', level=log_utils.LOGDEBUG)

	def poll_token(self, device_code, fromSettings=0):
		data = {'client_id': CLIENT_ID, 'code': device_code, 'grant_type': 'device_code'}
		token = session.post('https://www.premiumize.me/token', data=data, timeout=15).json()
		if 'error' in token:
			if token['error'] == "access_denied":
				control.okDialog(title='default', message=getLS(40020))
				if fromSettings == 1:
					control.openSettings('10.1', 'plugin.video.umbrella')
				return False, False
			return True, False
		self.token = token['access_token']
		self.headers = {'User-Agent': 'Umbrella for Kodi', 'Authorization': 'Bearer %s' % self.token}
		control.sleep(500)
		account_info = self.account_info()
		control.setSetting('premiumizetoken', token['access_token'])
		control.setSetting('premiumizeusername', str(account_info['customer_id']))
		return False, True

	def add_headers_to_url(self, url):
		return url + '|' + urlencode(self.headers)

	def account_info(self):
		try:
			accountInfo = self._get(account_info_url)
			return accountInfo
		except: log_utils.error()
		return None

	def account_info_to_dialog(self):
		from datetime import datetime
		import math
		try:
			accountInfo = self.account_info()
			expires = datetime.fromtimestamp(accountInfo['premium_until'])
			days_remaining = (expires - datetime.today()).days
			expires = expires.strftime("%A, %B %d, %Y")
			points_used = int(math.floor(float(accountInfo['space_used']) / 1073741824.0))
			space_used = float(int(accountInfo['space_used'])) / 1073741824
			percentage_used = str(round(float(accountInfo['limit_used']) * 100.0, 1))
			items = []
			items += [getLS(40040) % accountInfo['customer_id']]
			items += [getLS(40041) % expires]
			items += [getLS(40042) % days_remaining]
			items += [getLS(40043) % points_used]
			items += [getLS(40044) % space_used]
			items += [getLS(40045) % percentage_used]
			return control.selectDialog(items, 'Premiumize')
		except: log_utils.error()
		return

	def valid_url(self, host):
		try:
			self.hosts = self.get_hosts()
			if not self.hosts['Premiumize.me']: return False
			if any(host in item for item in self.hosts['Premiumize.me']): return True
			return False
		except: log_utils.error()

	def get_hosts(self):
		
		hosts_dict = {'Premiumize.me': []}
		hosts = []
		append = hosts.append
		try:
			result = cache.get(self._get, 168, list_services_path_url)
			for x in result['directdl']:
				for alias in result['aliases'][x]: append(alias)
			hosts_dict['Premiumize.me'] = list(set(hosts))
		except: log_utils.error()
		return hosts_dict

	def unrestrict_link(self, link):
		try:
			data = {'src': link}
			response = self._post(transfer_directdl_url, data)
			try: return self.add_headers_to_url(response['content'][0]['link'])
			except: return None
		except: log_utils.error()

	def resolve_magnet(self, magnet_url, info_hash, season, episode, ep_title):
		from resources.lib.modules.source_utils import seas_ep_filter, extras_filter
		try:
			failed_reason, file_url, correct_files = 'Unknown', None, []
			append = correct_files.append
			extensions = supported_video_extensions()
			extras_filtering_list = extras_filter()
			data = {'src': magnet_url}
			response = self._post(transfer_directdl_url, data)
			if not response: return log_utils.log('Premiumize.me: Error RESOLVE MAGNET "%s" : (Server Failed to respond)' % magnet_url, __name__, log_utils.LOGWARNING)
			if not 'status' in response or response['status'] != 'success': raise Exception()
			# valid_results = [i for i in response.get('content') if any(i.get('path').lower().endswith(x) for x in extensions) and not i.get('link', '') == '']
			valid_results = [i for i in response.get('content') if not any(i.get('path').lower().endswith(x) for x in invalid_extensions) and not i.get('link', '') == '']
			if not valid_results: failed_reason = 'No valid video extension found'
			if season:
				episode_title = re.sub(r'[^A-Za-z0-9-]+', '.', ep_title.replace('\'', '')).lower()
				for item in valid_results:
					if '.m2ts' in str(item.get('path')):
						failed_reason = 'Can not resolve .m2ts season disk episode'
						continue
					if seas_ep_filter(season, episode, item['path'].split('/')[-1]):
						# log_utils.log('item[path].split(/)[-1]=%s' %  item['path'].split('/')[-1])
						append(item)
					else: failed_reason = 'no matching season/episode found'
					if len(correct_files) == 0: continue
					for i in correct_files:
						compare_link = seas_ep_filter(season, episode, i['path'], split=True)
						compare_link = re.sub(episode_title, '', compare_link)
						if not any(x in compare_link for x in extras_filtering_list):
							file_url = i['link']
							break
			else: file_url = max(valid_results, key=lambda x: int(x.get('size'))).get('link', None)
			if file_url:
				if self.store_to_cloud: self.create_transfer(magnet_url)
				return self.add_headers_to_url(file_url)
			else:
				log_utils.log('Premiumize.me: FAILED TO RESOLVE MAGNET "%s" : (%s)' % (magnet_url, failed_reason), __name__, log_utils.LOGWARNING)
		except: log_utils.error('Premiumize.me: Error RESOLVE MAGNET "%s" ' % magnet_url)

	def display_magnet_pack(self, magnet_url, info_hash):
		end_results = []
		try:
			append = end_results.append
			extensions = supported_video_extensions()
			data = {'src': magnet_url}
			result = self._post(transfer_directdl_url, data=data)
			if not result: return log_utils.log('Premiumize.me Error display_magnet_pack: %s : Server Failed to respond' % magnet_url)
			if not 'status' in result or result['status'] != 'success': raise Exception()
			for item in result.get('content'):
				if any(item.get('path').lower().endswith(x) for x in extensions) and not item.get('link', '') == '':
					try: path = item['path'].split('/')[-1]
					except: path = item['path']
					append({'link': item['link'], 'filename': path, 'size': float(item['size']) / 1073741824})
			return end_results
		except: log_utils.error('Premiumize.me Error display_magnet_pack: %s' % magnet_url, __name__, log_utils.LOGDEBUG)


	def add_uncached_torrent(self, magnet_url, pack=False):
		def _transfer_info(transfer_id):
			info = self.list_transfer()
			if 'status' in info and info['status'] == 'success':
				for item in info['transfers']:
					if item['id'] == transfer_id: return item
			return {}
		def _return_failed(message=getLS(33586)):
			try: self.progressDialog.close()
			except: pass
			self.delete_transfer(transfer_id)
			control.hide()
			control.sleep(500)
			control.okDialog(title=getLS(40018), message=message)
			return False
		control.busy()
		extensions = supported_video_extensions()
		transfer_id = self.create_transfer(magnet_url)
		if not transfer_id: return control.hide()
		if not transfer_id['status'] == 'success': return _return_failed()
		transfer_id = transfer_id['id']
		transfer_info = _transfer_info(transfer_id)
		if not transfer_info: return _return_failed()
		# if pack:
			# control.hide()
			# control.okDialog(title='default', message=getLS(40017) % getLS(40057))
			# return True
		interval = 5
		line = '%s\n%s\n%s'
		line1 = '%s...' % (getLS(40017) % getLS(40057))
		line2 = transfer_info['name']
		line3 = transfer_info['message']
		#####################################
		if control.setting('dialogs.useumbrelladialog') == 'true':
			self.progressDialog = control.getProgressWindow(getLS(40018), None, 0)
			self.progressDialog.set_controls()
			self.progressDialog.update(0, line % (line1, line2, line3))
		else:
			self.progressDialog = control.progressDialog
			self.progressDialog.create(getLS(40018), line % (line1, line2, line3))
		while not transfer_info['status'] == 'seeding':
			control.sleep(1000 * interval)
			transfer_info = _transfer_info(transfer_id)
			line3 = transfer_info['message']
			self.progressDialog.update(int(float(transfer_info['progress']) * 100), line % (line1, line2, line3))
			if control.monitor.abortRequested(): return sysexit()
			try:
				if self.progressDialog.iscanceled():
					if control.yesnoDialog('Delete PM download also?', 'No will continue the download', 'but close dialog','Premiumize','No','Yes'):
						return _return_failed(getLS(40014))
					else:
						self.progressDialog.close()
						control.hide()
						return False
			except: pass
			if transfer_info.get('status') == 'stalled':
				return _return_failed()
		control.sleep(1000 * interval)
		try:
			self.progressDialog.close()
		except: log_utils.error()
		control.hide()
		return True

	def check_cache_item(self, media_id):
		try:
			media_id = media_id.encode('ascii', errors='ignore').decode('ascii', errors='ignore')
			media_id = media_id.replace(' ', '')
			url = '%s?items[]=%s' % (cache_check_url, media_id)
			result = session.get(url, headers=self.headers)
			if any(value in response for value in ('500', '502', '504')):
				log_utils.log('Premiumize.me Service Unavailable: %s' % response, __name__, log_utils.LOGDEBUG)
			else: response = response.json()
			if 'status' in result:
				if result.get('status') == 'success':
					response = result.get('response', False)
					if isinstance(response, list): return response[0]
				if result.get('status') == 'error':
					if self.server_notifications: control.notification(message=result.get('message'), icon=pm_icon)
					log_utils.log('Premiumize.me: %s' % response.get('message'), __name__, log_utils.LOGDEBUG)
		except: log_utils.error()
		return False

	def check_cache_list(self, hashList):
		try:
			postData = {'items[]': hashList}
			response = session.post(cache_check_url, data=postData, headers=self.headers, timeout=10)
			if any(value in response for value in ('500', '502', '504')):
				log_utils.log('Premiumize.me Service Unavailable: %s' % response, __name__, log_utils.LOGDEBUG)
			else: response = response.json()
			if 'status' in response:
				if response.get('status') == 'success':
					response = response.get('response', False)
					if isinstance(response, list): return response
		except: log_utils.error()
		return False

	def list_transfer(self):
		return self._get(transfer_list_url)

	def create_transfer(self, src,  folder_id=0):
		try:
			data = {'src': src, 'folder_id': folder_id}
			log_utils.log('Premiumize.me: Sending MAGNET to cloud: "%s" ' % src, __name__, log_utils.LOGDEBUG)
			return self._post(transfer_create_url, data)
		except: log_utils.error()

	def clear_finished_transfers(self):
		try:
			response = self._post(transfer_clearfinished_url)
			if not response: return
			if 'status' in response:
				if response.get('status') == 'success':
					log_utils.log('Finished transfers successfully cleared from the Premiumize.me cloud', __name__, log_utils.LOGDEBUG)
					control.refresh()
					return
		except: log_utils.error()
		return

	def delete_transfer(self, media_id, folder_name=None, silent=True):
		try:
			if not silent:
				if not control.yesnoDialog(getLS(40050) % '?\n' + folder_name, '', ''): return
			data = {'id': media_id}
			response = self._post(transfer_delete_url, data)
			if silent: return
			else:
				if response and response.get('status') == 'success':
					if self.server_notifications: control.notification(message='%s successfully deleted from the Premiumize.me cloud' % folder_name, icon=pm_icon)
					log_utils.log('%s successfully deleted from the Premiumize.me cloud' % folder_name, __name__, log_utils.LOGDEBUG)
					control.refresh()
					return
		except: log_utils.error()

	def my_files(self, folder_id=None):
		try:
			if folder_id: url = folder_list_url + '?id=%s' % folder_id
			else: url = folder_list_url
			response = self._get(url)
			if response: return response.get('content')
		except: log_utils.error()

	def my_files_all(self):
		try:
			response = self._get(item_listall_url)
			if response: return response.get('files')
		except: log_utils.error()

	def my_files_to_listItem(self, folder_id=None, folder_name=None):
		try:
			sysaddon, syshandle = 'plugin://plugin.video.umbrella/', int(argv[1])
			extensions = supported_video_extensions()
			cloud_files = self.my_files(folder_id)
			if not cloud_files:
				if self.server_notifications: control.notification(message='Request Failure-Empty Content', icon=pm_icon)
				log_utils.log('Premiumize.me: Request Failure-Empty Content', __name__, log_utils.LOGDEBUG)
				return
			cloud_files = [i for i in cloud_files if ('link' in i and i['link'].lower().endswith(tuple(extensions))) or i['type'] == 'folder']
			cloud_files = sorted(cloud_files, key=lambda k: k['name'])
			cloud_files = sorted(cloud_files, key=lambda k: k['type'], reverse=True)
		except: return log_utils.error()
		folder_str, file_str, downloadMenu, renameMenu, deleteMenu = getLS(40046).upper(), getLS(40047).upper(), getLS(40048), getLS(40049), getLS(40050)
		for count, item in enumerate(cloud_files, 1):
			try:
				cm = []
				content_type = item['type']
				name = string_tools.strip_non_ascii_and_unprintable(item['name'])
				if content_type == 'folder':
					isFolder = True
					size = 0
					label = '%02d | [B]%s[/B] | [I]%s [/I]' % (count, folder_str, name)
					url = '%s?action=pm_MyFiles&id=%s&name=%s' % (sysaddon, item['id'], quote_plus(name))
				else:
					isFolder = False
					url_link = item['link']
					if url_link.startswith('/'): url_link = 'https' + url_link
					size = item['size']
					display_size = float(int(size)) / 1073741824
					label = '%02d | [B]%s[/B] | %.2f GB | [I]%s [/I]' % (count, file_str, display_size, name)
					url = '%s?action=play_URL&url=%s' % (sysaddon, url_link)
					cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&url=%s&caller=premiumize)' %
								(sysaddon, quote_plus(name), quote_plus(pm_icon), url_link)))
				cm.append((renameMenu % content_type.capitalize(), 'RunPlugin(%s?action=pm_Rename&type=%s&id=%s&name=%s)' %
								(sysaddon, content_type, item['id'], quote_plus(name))))
				cm.append((deleteMenu % content_type.capitalize(), 'RunPlugin(%s?action=pm_Delete&type=%s&id=%s&name=%s)' %
								(sysaddon, content_type, item['id'], quote_plus(name))))
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': pm_icon, 'poster': pm_icon, 'thumb': pm_icon, 'fanart': addonFanart, 'banner': pm_icon})
				#item.setInfo(type='video', infoLabels='')
				meta = {}
				control.set_info(item, meta)
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def user_transfers(self):
		try:
			response = self._get(transfer_list_url)
			if response: return response.get('transfers')
		except: log_utils.error()

	def user_transfers_to_listItem(self):
		try:
			sysaddon, syshandle = 'plugin://plugin.video.umbrella/', int(argv[1])
			extensions = supported_video_extensions()
			transfer_files = self.user_transfers()
			if not transfer_files:
				if self.server_notifications: control.notification(message='Request Failure-Empty Content', icon=pm_icon)
				log_utils.log('Premiumize.me: Request Failure-Empty Content', __name__, log_utils.LOGDEBUG)
				return
		except: return log_utils.error()
		folder_str, file_str, downloadMenu, renameMenu, deleteMenu, clearFinishedMenu = getLS(40046).upper(), getLS(40047).upper(), getLS(40048), getLS(40049), getLS(40050), getLS(40051)
		for count, item in enumerate(transfer_files, 1):
			try:
				cm = []
				content_type = 'folder' if item['file_id'] is None else 'file'
				name = string_tools.strip_non_ascii_and_unprintable(item['name'])
				status = item['status']
				progress = item['progress']
				if status == 'finished': progress = 100
				else:
					try: progress = re.findall(r'(?:\d{0,1}\.{0,1})(\d+)', str(progress))[0][:2]
					except: progress = 'UNKNOWN'
				if content_type == 'folder':
					isFolder = True if status == 'finished' else False
					status_str = '[COLOR %s]%s[/COLOR]' % (self.highlightColor, status.capitalize())
					label = '%02d | [B]%s[/B] - %s | [B]%s[/B] | [I]%s [/I]' % (count, status_str, str(progress) + '%', folder_str, name)
					url = '%s?action=pm_MyFiles&id=%s&name=%s' % (sysaddon, item['folder_id'], quote_plus(name))

					# Till PM addresses issue with item also being removed from public acess if item not accessed for 60 days this option is disabled.
					# cm.append((clearFinishedMenu, 'RunPlugin(%s?action=pm_ClearFinishedTransfers)' % sysaddon))
				else:
					isFolder = False
					details = self.item_details(item['file_id'])
					if not details:
						if self.server_notifications: control.notification(message='Request Failure-Empty Content', icon=pm_icon)
						log_utils.log('Premiumize.me: Request Failure-Empty Content', __name__, log_utils.LOGDEBUG)
						return
					url_link = details['link']
					if url_link.startswith('/'):
						url_link = 'https' + url_link
					size = details['size']
					display_size = float(int(size)) / 1073741824
					label = '%02d | %s%% | [B]%s[/B] | %.2f GB | [I]%s [/I]' % (count, str(progress), file_str, display_size, name)
					url = '%s?action=play_URL&url=%s' % (sysaddon, url_link)
					cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&url=%s&caller=premiumize)' %
								(sysaddon, quote_plus(name), quote_plus(pm_icon), url_link)))

				cm.append((deleteMenu % 'Transfer', 'RunPlugin(%s?action=pm_DeleteTransfer&id=%s&name=%s)' %
							(sysaddon, item['id'], quote_plus(name))))
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': pm_icon, 'poster': pm_icon, 'thumb': pm_icon, 'fanart': addonFanart, 'banner': pm_icon})
				#item.setInfo(type='video', infoLabels='')
				meta = {}
				control.set_info(item, meta)
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def item_details(self, item_id):
		try:
			data = {'id': item_id}
			itemDetails = self._post(item_details_url, data)
			return itemDetails
		except: log_utils.error()
		return None

	def rename(self, type, folder_id=None, folder_name=None):
		try:
			if type == 'folder':
				url = folder_rename_url
				t = getLS(40049) % type
			else:
				if not control.yesnoDialog(getLS(40049) % folder_name + ': [B](YOU MUST ENTER MATCHING FILE EXT.)[/B]', '', ''): return
				url = item_rename_url
				t = getLS(40049) % type + ': [B](YOU MUST ENTER MATCHING FILE EXT.)[/B]'
			k = control.keyboard('', t)
			k.doModal()
			q = k.getText() if k.isConfirmed() else None
			if not q: return
			data = {'id': folder_id, 'name': q}
			response = self._post(url, data=data)
			if not response: return
			if 'status' in response:
				if response.get('status') == 'success': control.refresh()
		except: log_utils.error()

	def delete(self, type, folder_id=None, folder_name=None):
		try:
			if type == 'folder': url = folder_delete_url
			else: url = item_delete_url
			if not control.yesnoDialog(getLS(40050) % folder_name, '', ''): return
			data = {'id': folder_id}
			response = self._post(url, data=data)
			if not response: return
			if 'status' in response:
				if response.get('status') == 'success': control.refresh()
		except: log_utils.error()

	def revoke(self, fromSettings=0):
		try:
			control.setSetting('premiumizetoken', '')
			control.setSetting('premiumizeusername', '')
			control.dialog.ok(control.lang(40057), control.lang(40009))
			if fromSettings == 1:
				control.openSettings('10.1', 'plugin.video.umbrella')
		except:
			log_utils.error()