import requests
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules.source_utils import supported_video_extensions

getLS = control.lang
getSetting = control.setting
base_url = 'https://easydebrid.com/api/v1'
ed_icon = control.joinPath(control.artPath(), 'easydebrid.png')
addonFanart = control.addonFanart()

session = requests.Session()
session.mount(base_url, requests.adapters.HTTPAdapter(max_retries=1))

class EasyDebrid:
	download = '/link/generate'
	stats = '/user/details'
	cache = '/link/lookup'

	def __init__(self):
		self.name = 'EasyDebrid'
		self.api_key = getSetting('easydebridtoken')
		self.sort_priority = getSetting('easydebrid.priority')
		self.timeout = 10

	def _request(self, method, path, params=None, json=None, data=None):
		if not self.api_key: return
		session.headers['Authorization'] = 'Bearer %s' % self.api_key
		full_path = '%s%s' % (base_url, path)
		response = session.request(method, full_path, params=params, json=json, data=data, timeout=self.timeout)
		try: response.raise_for_status()
		except Exception as e: log_utils.log('easydebrid error %s' % str(e))
		try: result = response.json()
		except: result = {}
		return result

	def _GET(self, url, params=None):
		return self._request('get', url, params=params)

	def _POST(self, url, params=None, json=None, data=None):
		return self._request('post', url, params=params, json=json, data=data)

	def account_info(self):
		return self._GET(self.stats)

	def check_cache_single(self, hash):
		return self._POST(self.cache, json={'urls': [hash]})

	def check_cache(self, hashlist):
		data = {'urls': hashlist}
		return self._POST(self.cache, json=data)

	def add_magnet(self, magnet):
		data = {'url': magnet}
		return self._POST(self.download, json=data)

	def create_transfer(self, magnet_url):
		result = self.add_magnet(magnet_url)
		if not 'files' in result: return ''
		return result.get('files', '')

	def resolve_magnet(self, magnet_url, info_hash, season, episode, title):
		from resources.lib.modules.source_utils import seas_ep_filter, extras_filter
		try:
			file_url, match = None, False
			extensions = supported_video_extensions()
			extras_filtering_list = tuple(i for i in extras_filter() if not i in title.lower())
			check = self.check_cache_single(info_hash)
			match = 'cached' in check and check['cached'][0]
			if not match: return None
			torrent = self.add_magnet(magnet_url)
			torrent_files = torrent['files']
			selected_files = [i for i in torrent_files if i['filename'].lower().endswith(tuple(extensions))]
			if not selected_files: return None
			if season:
				selected_files = [i for i in selected_files if seas_ep_filter(season, episode, i['filename'])]
			else:
				if self._m2ts_check(selected_files): raise Exception('_m2ts_check failed')
				selected_files = [i for i in selected_files if not any(x in i['filename'] for x in extras_filtering_list)]
				selected_files.sort(key=lambda k: k['size'], reverse=True)
			if not selected_files: return None
			file_url = selected_files[0]['url']
			return file_url
		except Exception as e:
			log_utils.error('EasyDebrid: Error RESOLVE MAGNET "%s" ' % magnet_url)
			return None

	def display_magnet_pack(self, magnet_url, info_hash):
		try:
			extensions = supported_video_extensions()
			torrent = self.add_magnet(magnet_url)
			if not torrent: return None
			torrent_files = [
				{'link': item['url'], 'filename': item['filename'], 'size': item['size'] / 1073741824}
				for item in torrent['files'] if item['filename'].lower().endswith(tuple(extensions))
			]
			return torrent_files
		except Exception:
			return None

	def add_uncached_torrent(self, magnet_url, pack=False):
		return control.okDialog(title=getLS(40018), message=getLS(33586))

	def _m2ts_check(self, folder_items):
		for item in folder_items:
			if item['filename'].endswith('.m2ts'): return True
		return False

	def auth(self):
		api_key = control.dialog.input('EasyDebrid API Key:')
		if not api_key: return
		self.api_key = api_key
		r = self.account_info()
		customer = r['id']
		control.setSetting('easydebridtoken', api_key)
		control.notification(title='EasyDebrid',message=40539, icon=ed_icon)
		control.openSettings('9.2', 'plugin.video.umbrella')
		return True

	def remove_auth(self):
		try:
			self.api_key = ''
			control.setSetting('easydebridtoken', '')
			control.okDialog(title='EasyDebrid', message=40009)
			control.openSettings('9.2', 'plugin.video.umbrella')
		except: log_utils.error()

	def account_info_to_dialog(self):
		try:
			control.busy()
			account_info = self.account_info()
			items = []
			items += ['[B]ID[/B]: %s' % account_info['id']]
			items += ['[B]Expires[/B]: %s' % account_info['paid_until']]
			control.hide()
			return control.selectDialog(items, 'TorBox')
		except: log_utils.error()

	def account_info(self):
		return self._GET(self.stats)

