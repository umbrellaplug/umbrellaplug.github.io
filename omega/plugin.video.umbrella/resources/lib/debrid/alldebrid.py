# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from json import dumps as jsdumps, loads as jsloads
import re
import requests
from requests.adapters import HTTPAdapter
from sys import argv, exit as sysexit
from urllib3.util.retry import Retry
from urllib.parse import quote_plus
from resources.lib.database import cache
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules import string_tools
from resources.lib.modules.source_utils import supported_video_extensions

getLS = control.lang
getSetting = control.setting
base_url = 'https://api.alldebrid.com/v4/'
base_url_2 = 'https://api.alldebrid.com/v4.1/'
user_agent = 'Umbrella'
ad_icon = control.joinPath(control.artPath(), 'alldebrid.png')
ad_qr = control.joinPath(control.artPath(), 'alldebridqr.png')
addonFanart = control.addonFanart()
invalid_extensions = ('.bmp', '.exe', '.gif', '.jpg', '.nfo', '.part', '.png', '.rar', '.sample.', '.srt', '.txt', '.zip', '.clpi', '.mpls', '.bdmv', '.xml', '.crt', 'crl', 'sig')

session = requests.Session()
retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
session.mount('https://api.alldebrid.com', HTTPAdapter(max_retries=retries, pool_maxsize=100))


class AllDebrid:
	name = "AllDebrid"
	sort_priority = getSetting('alldebrid.priority')
	def __init__(self):
		self.token = getSetting('alldebridtoken')
		self.timeout = 20
		self.server_notifications = getSetting('alldebrid.server.notifications')
		self.store_to_cloud = getSetting('alldebrid.saveToCloud') == 'true'
		self.highlight_color = control.setting('highlight.color')

	def _get(self, url, url_append=''):
		response = None
		try:
			if self.token == '':
				log_utils.log('No All-Debrid Token Found')
				return None
			if url == 'magnet/status':
				url = base_url_2 + url + '?agent=%s&apikey=%s' % (user_agent, self.token) + url_append
			else:
				url = base_url + url + '?agent=%s&apikey=%s' % (user_agent, self.token) + url_append
			response = session.get(url, timeout=self.timeout)
			if 'Response [500]' in str(response):
				log_utils.log('AllDebrid: Status code 500 – Internal Server Error', __name__, log_utils.LOGWARNING)
				return None
			if not response:
				log_utils.log('AllDebrid: No Response from server', __name__, log_utils.LOGWARNING)
				return None
			response = response.json()
			if 'status' in response:
				if response.get('status') == 'success':
					if 'data' in response: response = response['data']
				elif response.get('status') == 'error':
					if self.server_notifications: control.notification(message=response.get('error').get('message'), icon=ad_icon)
					log_utils.log('AllDebrid: %s' % response.get('error').get('message'), __name__, log_utils.LOGWARNING)
					return None
		except requests.exceptions.ConnectionError:
			if self.server_notifications: control.notification(message='Failed to connect to AllDebrid', icon=ad_icon)
			log_utils.log('Failed to connect to AllDebrid', __name__, log_utils.LOGWARNING)
			return None
		except BaseException:
			log_utils.error()
			return None
		return response

	def _post(self, url, data={}):
		response = None
		try:
			if self.token == '': return None
			url = base_url + url + '?agent=%s&apikey=%s' % (user_agent, self.token)
			response = session.post(url, data=data, timeout=self.timeout)
			if 'Response [500]' in str(response):
				log_utils.log('AllDebrid: Status code 500 – Internal Server Error', __name__, log_utils.LOGWARNING)
				return None
			if response is None:
				log_utils.log('AllDebrid: No Response from server', __name__, log_utils.LOGWARNING)
				return None
			response = response.json()
			if 'status' in response:
				if response.get('status') == 'success':
					if 'data' in response: response = response['data']
				elif response.get('status') == 'error':
					if self.server_notifications:control.notification(message=response.get('error').get('message'), icon=ad_icon)
					log_utils.log('AllDebrid: %s' % response.get('error').get('message'), __name__, log_utils.LOGWARNING)
					return None
		except requests.exceptions.ConnectionError:
			if self.server_notifications: control.notification(message='Failed to connect to AllDebrid', icon=ad_icon)
			log_utils.log('Failed to connect to AllDebrid', __name__, log_utils.LOGWARNING)
		except BaseException:
			log_utils.error()
		return response

	def auth_loop(self):
		control.sleep(5000)
		data = {'check': self.check, 'pin': self.pin}
		url = base_url + 'pin/check'
		response = session.post(url, data).json()
		response = response.get('data')
		if 'error' in response:
			self.token = 'failed'
			control.notification(message=40021, icon=ad_icon)
			log_utils.log(40021, __name__, log_utils.LOGWARNING)
			return
		if response['activated']:
			try:
				self.progressDialog.close()
				self.token = str(response['apikey'])
				control.setSetting('alldebridtoken', self.token)
			except:
				self.token = 'failed'
				control.notification(message=40021, icon=ad_icon)
				log_utils.log(40021, __name__, log_utils.LOGWARNING)
				return
		return

	def auth(self, fromSettings=0):
		self.token = ''
		url = base_url_2 + 'pin/get?agent=%s' % user_agent
		response = session.get(url, timeout=self.timeout).json()
		response = response['data']
		line = '%s\n%s'
		if control.setting('dialogs.useumbrelladialog') == 'true':
			self.progressDialog = control.getProgressWindow(getLS(40056), ad_qr, 1)
			self.progressDialog.set_controls()
		else:
			self.progressDialog = control.progressDialog
			self.progressDialog.create(getLS(40056))
		self.progressDialog.update(-1, line % (getLS(32513) % (self.highlight_color,'https://alldebrid.com/pin/'), getLS(32514) % (self.highlight_color,response['pin'])))
		self.check = response.get('check')
		self.pin = response.get('pin')
		control.sleep(2000)
		while not self.token:
			if self.progressDialog.iscanceled():
				self.progressDialog.close()
				break
			self.auth_loop()
		if self.token in (None, '', 'failed'):
			if fromSettings == 1:
				control.openSettings('10.0', 'plugin.video.umbrella')
			return
		control.sleep(2000)
		account_info = self._get('user')
		control.setSetting('alldebridusername', str(account_info['user']['username']))
		if fromSettings == 1:
			control.openSettings('10.0', 'plugin.video.umbrella')
		control.notification(message=40010, icon=ad_icon)
		log_utils.log(40010, __name__, log_utils.LOGWARNING)

	def revoke_auth(self, fromSettings=0):
		try:
			control.setSetting('alldebridtoken', '')
			control.setSetting('alldebridusername', '')
			if fromSettings == 1:
				control.openSettings('10.0', 'plugin.video.umbrella')
			control.okDialog(title=40059, message=40009)
		except: log_utils.error()

	def account_info(self):
		response = self._get('user')
		return response

	def account_info_to_dialog(self):
		from datetime import datetime
		try:
			account_info = self.account_info()['user']
			username = account_info['username']
			email = account_info['email']
			status = 'Premium' if account_info['isPremium'] else 'Not Active'
			expires = datetime.fromtimestamp(account_info['premiumUntil'])
			days_remaining = (expires - datetime.today()).days
			heading = getLS(40059).upper()
			items = []
			items += [getLS(40036) % username]
			items += [getLS(40035) % email]
			items += [getLS(40037) % status]
			items += [getLS(40041) % expires]
			items += [getLS(40042) % days_remaining]
			return control.selectDialog(items, 'AllDebrid')
		except: log_utils.error()

	def check_cache(self, hashes):
		try:
			data = {'magnets[]': hashes}
			response = self._post('magnet/instant', data)
			try: return response
			except: return None
		except: log_utils.error()

	def check_single_magnet(self, hash_string):
		try:
			cache_info = self.check_cache(hash_string)['magnets'][0]
			try: return cache_info['instant']
			except: return None
		except: log_utils.error()

	def unrestrict_link(self, link, returnAll=False):
		try:
			url = 'link/unlock'
			url_append = '&link=%s' % link
			response = self._get(url, url_append)
			if returnAll: return response
			else:
				try: return response['link']
				except: return None
		except: log_utils.error()

	def create_transfer(self, magnet):
		try:
			url = 'magnet/upload'
			url_append = '&magnet=%s' % magnet
			result = self._get(url, url_append)
			try: result = result['magnets'][0]
			except: return None
			log_utils.log('AllDebrid: Sending MAGNET to cloud: %s' % magnet, __name__, log_utils.LOGDEBUG)
			try: return result.get('id', "")
			except: return None
		except: log_utils.error()

	def list_transfer(self, transfer_id):
		try:
			url = 'magnet/status'
			url_append = '&id=%s' % transfer_id
			result = self._get(url, url_append)
			try: return result['magnets']
			except: return None
		except: log_utils.error()

	def delete_transfer(self, transfer_id, folder_name=None, silent=True):
		try:
			if not silent:
				if not control.yesnoDialog(getLS(40050) % '?\n' + folder_name, '', ''): return
			url = 'magnet/delete'
			url_append = '&id=%s' % transfer_id
			response = self._get(url, url_append)
			if silent: return
			else:
				if response and 'message' in response:
					if self.server_notifications: control.notification(message=response.get('message'), icon=ad_icon)
					log_utils.log('%s successfully deleted from the AllDebrid cloud' % folder_name, __name__, log_utils.LOGDEBUG)
					control.refresh()
					return
		except: log_utils.error()

	def restart_transfer(self, transfer_id, folder_name=None, silent=True):
		try:
			if not silent:
				if not control.yesnoDialog(getLS(40007) % '\n' + folder_name, '', ''): return
			url = 'magnet/restart'
			url_append = '&id=%s' % transfer_id
			response = self._get(url, url_append)
			if silent: return
			else:
				if response and 'message' in response:
					if self.server_notifications: control.notification(message=response.get('message'), icon=ad_icon)
					log_utils.log('AllDebrid: %s' % response.get('message'), __name__, log_utils.LOGDEBUG)
					return control.refresh()
		except: log_utils.error()

	def user_cloud(self):
		url = 'magnet/status'
		return self._get(url)

	def user_transfers_to_listItem(self):
		sysaddon, syshandle = 'plugin://plugin.video.umbrella/', int(argv[1])
		transfer_files = self.user_cloud()['magnets']
		if not transfer_files:
			if self.server_notifications: control.notification(message='Request Failure-Empty Content', icon=ad_icon)
			log_utils.log('AllDebrid: Request Failure-Empty Content', __name__, log_utils.LOGDEBUG)
			return
		folder_str, deleteMenu, restartMenu = getLS(40046).upper(), getLS(40050), getLS(40008)
		for count, item in enumerate(transfer_files, 1):
			try:
				status_code = item['statusCode'] 
				if status_code in (0,1, 2, 3):
					active = True
					downloaded = item['downloaded']
					size = item['size']
					try: percent = str(round(float(downloaded) / size * 100, 1))
					except: percent = '0'
				else: active = False
				folder_name = string_tools.strip_non_ascii_and_unprintable(item['filename'])
				id = item['id']
				status_str = '[COLOR %s]%s[/COLOR]' % (self.highlight_color, item['status'].capitalize())
				if active: label = '%02d | [B]%s[/B] - %s | [B]%s[/B]' % (count, status_str, str(percent) + '%', folder_name)
				else: label = '%02d | [B]%s[/B] | [B]%s[/B] | [I]%s [/I]' % (count, status_str, folder_str, folder_name)
				if status_code == 4:
					url = '%s?action=ad_BrowseUserCloud&source=%s' % (sysaddon, quote_plus(jsdumps(item)))
					isFolder = True
				else:
					url = ''
					isFolder = False
				cm = []
				cm.append((deleteMenu % 'Transfer', 'RunPlugin(%s?action=ad_DeleteTransfer&id=%s&name=%s)' % (sysaddon, id, folder_name)))
				if status_code in (6, 7, 9, 10):
					cm.append((restartMenu, 'RunPlugin(%s?action=ad_RestartTransfer&id=%s&name=%s)' % (sysaddon, id, folder_name)))
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': ad_icon, 'poster': ad_icon, 'thumb': ad_icon, 'fanart': addonFanart, 'banner': ad_icon})
				#item.setInfo(type='video', infoLabels='')
				meta = {}
				control.set_info(item, meta)
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def user_cloud_to_listItem(self, folder_id=None):
		sysaddon, syshandle = 'plugin://plugin.video.umbrella/', int(argv[1])
		folder_str, deleteMenu = getLS(40046).upper(), getLS(40050)
		cloud_dict = self.user_cloud()['magnets']
		cloud_dict = [i for i in cloud_dict if i['statusCode'] == 4]

		for count, item in enumerate(cloud_dict, 1):
			try:
				cm = []
				folder_name = string_tools.strip_non_ascii_and_unprintable(item['filename'])
				id = item['id']
				status_str = '[COLOR %s]%s[/COLOR]' % (self.highlight_color, item['status'].capitalize())
				label = '%02d | [B]%s[/B] | [B]%s[/B] | [I]%s [/I]' % (count, status_str, folder_str, folder_name)
				url = '%s?action=ad_BrowseUserCloud&source=%s' % (sysaddon, quote_plus(jsdumps(item)))
				cm.append((deleteMenu % 'Transfer', 'RunPlugin(%s?action=ad_DeleteTransfer&id=%s&name=%s)' %
					(sysaddon, id, folder_name)))
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': ad_icon, 'poster': ad_icon, 'thumb': ad_icon, 'fanart': addonFanart, 'banner': ad_icon})
				#item.setInfo(type='video', infoLabels='')
				meta = {}
				control.set_info(item, meta)
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def browse_user_cloud(self, folder):
		sysaddon, syshandle = 'plugin://plugin.video.umbrella/', int(argv[1])
		extensions = supported_video_extensions()
		torrent_folder = jsloads(folder)
		links = torrent_folder['links']
		# links = [i for i in links if i['filename'].lower().endswith(tuple(extensions))]
		status_code = torrent_folder['statusCode'] 
		file_str, downloadMenu, deleteMenu = getLS(40047).upper(), getLS(40048), getLS(40050)
		for count, item in enumerate(links, 1):
			try:
				cm = []
				url_link = item['link']
				name = string_tools.strip_non_ascii_and_unprintable(item['filename'])
				if name.lower().endswith(invalid_extensions): continue

				if not name.lower().endswith(tuple(extensions)):
					files = item['files']
					if not files:
						link = cache.get(self.unrestrict_link, 168, item.get('link'), True)
						name = string_tools.strip_non_ascii_and_unprintable(link['filename'])
						if name.lower().endswith(invalid_extensions): continue
						item.update({'filename': name})
						item.update({'size': link['filesize']})
					else:
						entry = files[0].get('e')
						name = entry[0].get('n') if isinstance(entry, list) else entry.get('n')
						def entry_loop(entry):
							entry = entry.get('e')
							name = entry[0].get('n') if isinstance(entry, list) else entry.get('n')
							if not name.lower().endswith(tuple(extensions)):
								return entry_loop(entry)
							else: return string_tools.strip_non_ascii_and_unprintable(name)
						if not name.lower().endswith(tuple(extensions)):
							name = entry_loop(entry)

				size = item['size']
				display_size = float(int(size)) / 1073741824
				label = '%02d | [B]%s[/B] | %.2f GB | [I]%s [/I]' % (count, file_str, display_size, name)
				if status_code == 4: url = '%s?action=play_URL&url=%s&caller=alldebrid&type=unrestrict' % (sysaddon, url_link)
				else: url = ''
				cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&url=%s&caller=alldebrid)' %
								(sysaddon, quote_plus(name), quote_plus(ad_icon), url_link)))
				item = control.item(label=label, offscreen=True)
				item.addContextMenuItems(cm)
				item.setArt({'icon': ad_icon, 'poster': ad_icon, 'thumb': ad_icon, 'fanart': addonFanart, 'banner': ad_icon})
				#item.setInfo(type='video', infoLabels='')
				meta = {}
				control.set_info(item, meta)
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
			except: log_utils.error()
		control.content(syshandle, 'files')
		control.directory(syshandle, cacheToDisc=True)

	def resolve_magnet(self, magnet_url, info_hash, season, episode, ep_title):
		from resources.lib.modules.source_utils import seas_ep_filter, extras_filter
		try:
			failed_reason, media_id, file_url = 'Unknown', None, None
			correct_files = []
			append = correct_files.append
			extensions = supported_video_extensions()
			extras_filtering_list = extras_filter()
			transfer_id = self.create_transfer(magnet_url)
			transfer_info = self.list_transfer(transfer_id)
			if not transfer_info: return log_utils.log('AllDebrid: Error RESOLVE MAGNET "%s" : (Server Failed to respond)' % magnet_url, __name__, log_utils.LOGWARNING)
			filenames = [i.get('filename') for i in transfer_info.get('links')]
			if all(i.lower().endswith('.rar') for i in filenames): failed_reason = 'AD returned unsupported .rar file'
			# valid_results = [i for i in transfer_info.get('links') if any(i.get('filename').lower().endswith(x) for x in extensions) and not i.get('link', '') == ''] #.m2ts file extension is not in "filename" so this fails
			valid_results = [i for i in transfer_info.get('links') if not any(i.get('filename').lower().endswith(x) for x in invalid_extensions) and not i.get('link', '') == '']
			if len(valid_results) == 0 and failed_reason == 'Unknown': failed_reason = 'No valid video extension found'

			if season:
				for item in valid_results:
					if '.m2ts' in str(item.get('files')):
						failed_reason = 'Can not resolve .m2ts season disk episode'
						continue

					if not item.get('files'):
						# link = self.unrestrict_link(item.get('link'), returnAll=True)
						link = cache.get(self.unrestrict_link, 168, item.get('link'), True)
						# log_utils.log('link=%s' % link, __name__)
						if seas_ep_filter(season, episode, link['filename']):
							item.update({'filename': link['filename']})
							append(item)
							# log_utils.log('revised_item=%s' % item, __name__)
					if seas_ep_filter(season, episode, item['filename']):
						append(item)

					if len(correct_files) == 0:
						failed_reason = 'no matching episode found'
						continue
					episode_title = re.sub(r'[^A-Za-z0-9-]+', '.', ep_title.replace('\'', '')).lower()
					for i in correct_files:
						try:
							compare_link = seas_ep_filter(season, episode, i['filename'], split=True)
							compare_link = re.sub(episode_title, '', compare_link)
							if not any(x in compare_link for x in extras_filtering_list):
								media_id = i['link']
								break
						except: log_utils.error()
			else:
				media_id = max(valid_results, key=lambda x: x.get('size')).get('link', None)
			if not self.store_to_cloud: self.delete_transfer(transfer_id)
			if not media_id:
				log_utils.log('AllDebrid: FAILED TO RESOLVE MAGNET "%s" : (%s)' % (magnet_url, failed_reason), __name__, log_utils.LOGWARNING)
				return None
			file_url = self.unrestrict_link(media_id)
			if not file_url:
				log_utils.log('AllDebrid: FAILED TO UNRESTRICT MAGNET "%s" ' % magnet_url, __name__, log_utils.LOGWARNING)
			return file_url
		except:
			if failed_reason != 'Unknown': log_utils.log('AllDebrid: FAILED TO RESOLVE MAGNET "%s" : (%s)' % (magnet_url, failed_reason), __name__, log_utils.LOGWARNING)
			else: log_utils.error('AllDebrid: Error RESOLVE MAGNET %s : ' % magnet_url)
			if transfer_id: self.delete_transfer(transfer_id)
			return None

	def display_magnet_pack(self, magnet_url, info_hash):
		try:
			extensions = supported_video_extensions()
			transfer_id = self.create_transfer(magnet_url)
			transfer_info = self.list_transfer(transfer_id)
			end_results = []
			append = end_results.append
			for item in transfer_info.get('links'):
				if any(item.get('filename').lower().endswith(x) for x in extensions) and not item.get('link', '') == '':
					append({'link': item['link'], 'filename': item['filename'], 'size': float(item['size']) / 1073741824})
				else:
					link = cache.get(self.unrestrict_link, 168, item.get('link'), True)
					if any(link.get('filename').lower().endswith(x) for x in extensions) and not link.get('link', '') == '':
						append({'link': item['link'], 'filename': link['filename'], 'size': float(link['filesize']) / 1073741824})
			if not self.store_to_cloud: self.delete_transfer(transfer_id) # this will keep all browsed items, should add check to see if item was already in cloud and keep it.
			return end_results
		except:
			log_utils.error()
			if transfer_id: self.delete_transfer(transfer_id)
			return None

	def add_uncached_torrent(self, magnet_url, pack=False):
		def _return_failed(message=getLS(33586)):
			try: self.progressDialog.close()
			except: pass
			self.delete_transfer(transfer_id)
			control.hide()
			control.sleep(500)
			control.okDialog(title=getLS(40018), message=message)
			return False
		control.busy()
		transfer_id = self.create_transfer(magnet_url)
		if not transfer_id: return _return_failed()
		transfer_info = self.list_transfer(transfer_id)
		if not transfer_info: return _return_failed()
		# if pack:
			# control.hide()
			# control.okDialog(title='default', message=getLS(40017) % getLS(40059))
			# return True
		interval = 5
		line = '%s\n%s\n%s'
		line1 = '%s...' % (getLS(40017) % getLS(40059))
		line2 = transfer_info['filename']
		line3 = transfer_info['status']
		if control.setting('dialogs.useumbrelladialog') == 'true':
			self.progressDialog = control.getProgressWindow(getLS(40018), None, 0)
			self.progressDialog.set_controls()
			self.progressDialog.update(0, line % (line1, line2, line3))
		else:
			self.progressDialog = control.progressDialog
			self.progressDialog.create(getLS(40018), line % (line1, line2, line3))
		while not transfer_info['statusCode'] == 4:
			control.sleep(1000 * interval)
			transfer_info = self.list_transfer(transfer_id)
			file_size = transfer_info['size']
			line2 = transfer_info['filename']
			if transfer_info['statusCode'] == 1:
				download_speed = round(float(transfer_info['downloadSpeed']) / (1000**2), 2)
				progress = int(float(transfer_info['downloaded']) / file_size * 100) if file_size > 0 else 0
				line3 = getLS(40016) % (download_speed, transfer_info['seeders'], progress, round(float(file_size) / (1000 ** 3), 2))
			elif transfer_info['statusCode'] == 3:
				upload_speed = round(float(transfer_info['uploadSpeed']) / (1000 ** 2), 2)
				progress = int(float(transfer_info['uploaded']) / file_size * 100) if file_size > 0 else 0
				line3 = getLS(40015) % (upload_speed, progress, round(float(file_size) / (1000 ** 3), 2))
			else:
				line3 = transfer_info['status']
				progress = 0
			self.progressDialog.update(progress, line % (line1, line2, line3))
			if control.monitor.abortRequested(): return sysexit()
			try:
				if self.progressDialog.iscanceled():
					if control.yesnoDialog('Delete AD download also?', 'No will continue the download', 'but close dialog','AllDebrid', 'No', 'Yes'):
						return _return_failed(getLS(40014))
					else:
						self.progressDialog.close()
						control.hide()
						return False
			except: pass
			if 5 <= transfer_info['statusCode'] <= 10: return _return_failed()
		control.sleep(1000 * interval)
		try: self.progressDialog.close()
		except: pass
		control.hide()
		return True

	def valid_url(self, host):
		try:
			self.hosts = self.get_hosts()
			if not self.hosts['AllDebrid']: return False
			if any(host in item for item in self.hosts['AllDebrid']): return True
			return False
		except: log_utils.error()

	def get_hosts(self):
		url = 'hosts'
		hosts_dict = {'AllDebrid': []}
		hosts = []
		extend = hosts.extend
		try:
			result = cache.get(self._get, 168, url)
			result = result['hosts']
			for k, v in result.items():
				try: extend(v['domains'])
				except: pass
			hosts_dict['AllDebrid'] = list(set(hosts))
		except: log_utils.error()
		return hosts_dict