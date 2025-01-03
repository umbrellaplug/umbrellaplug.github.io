# -*- coding: utf-8 -*-
import os
import sys
import ssl
import json
from threading import Thread
from urllib.request import Request, urlopen
from urllib.parse import parse_qsl, urlparse, unquote
from caches.settings_cache import get_setting
from modules import kodi_utils
from modules.sources import Sources
from modules.settings import download_directory
from modules.source_utils import clean_title
from modules.utils import clean_file_name, safe_string, remove_accents, normalize
# logger = kodi_utils.logger

video_extensions, image_extensions, get_icon, kodi_dialog = kodi_utils.video_extensions, kodi_utils.image_extensions, kodi_utils.get_icon, kodi_utils.kodi_dialog
add_items, set_sort_method, set_content, end_directory = kodi_utils.add_items, kodi_utils.set_sort_method, kodi_utils.set_content, kodi_utils.end_directory
show_busy_dialog, hide_busy_dialog, make_directory, open_file = kodi_utils.show_busy_dialog, kodi_utils.hide_busy_dialog, kodi_utils.make_directory, kodi_utils.open_file
notification = kodi_utils.notification
confirm_dialog, ok_dialog, build_url, get_visibility = kodi_utils.confirm_dialog, kodi_utils.ok_dialog, kodi_utils.build_url, kodi_utils.get_visibility
sleep, set_category, poster_empty, select_dialog = kodi_utils.sleep, kodi_utils.set_category, kodi_utils.empty_poster, kodi_utils.select_dialog
get_property, set_property, clear_property = kodi_utils.get_property, kodi_utils.set_property, kodi_utils.clear_property
set_view_mode, make_listitem, list_dirs = kodi_utils.set_view_mode, kodi_utils.make_listitem, kodi_utils.list_dirs
fanart = kodi_utils.get_addon_fanart()
sources = Sources()
ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
icons = {'Real-Debrid': 'realdebrid', 'Premiumize.me': 'premiumize', 'AllDebrid': 'alldebrid', 'Offcloud': 'offcloud', 'EasyDebrid': 'easydebrid', 'Torbox': 'torbox'}
levels =['../../../..', '../../..', '../..', '..']
status_property_string = 'fenlight.download_status.%s'

def runner(params):
	action = params.get('action')
	if action == 'image':
		for item in ('thumb_url', 'image_url'):
			image_params = params
			image_params['url'] = params.pop(item)
			image_params['media_type'] = item
			Downloader(image_params).run()
	elif action == 'meta.pack':
		from modules.source_utils import find_season_in_release_title
		provider = params['provider']
		try:
			debrid_files, debrid_function = sources.debridPacks(provider, params['name'], params['magnet_url'], params['info_hash'], download=True)
			pack_choices = [dict(params, **{'pack_files':item}) for item in debrid_files]
			icon = icons[provider]
		except: return notification('No URL found for Download. Pick another Source.')
		default_icon = get_icon(icon)
		chosen_list = select_pack_item(pack_choices, default_icon)
		if not chosen_list: return
		show_package = json.loads(params['source']).get('package') == 'show'
		meta  = json.loads(chosen_list[0].get('meta'))
		image = meta.get('poster') or poster_empty
		default_name = '%s (%s)' % (clean_file_name(get_title(meta)), get_year(meta))
		default_foldername = kodi_dialog().input('Title', defaultt=default_name)
		multi_downloads = []
		multi_downloads_append = multi_downloads.append
		for item in chosen_list:
			if show_package:
				season = find_season_in_release_title(item['pack_files']['filename'])
				if season:
					meta['season'] = season
					item['meta'] = json.dumps(meta)
					item['default_foldername'] = default_foldername
			multi_downloads_append((Thread(target=Downloader(item).run), clean_file_name(item['pack_files']['filename'])))
		download_threads_manager(multi_downloads, image)
	else: Downloader(params).run()

def download_threads_manager(multi_downloads, image):
	notification('Multi File Pack Download Started...', 3500, image)
	started_downloads = []
	started_downloads_append = started_downloads.append
	for item in multi_downloads:
		while len([x for x in multi_downloads if x[0].is_alive()]) >= 2:
			sleep(2000)
			continue
		item[0].start()
		started_downloads_append(item)
		remaining_downloads = [x[1] for x in multi_downloads if not x in started_downloads]
		set_property('fenlight.active_queued_downloads', json.dumps(remaining_downloads))
	clear_property('fenlight.active_queued_downloads')

def select_pack_item(pack_choices, icon):
	list_items = [{'line1': '%.2f GB | %s' % (float(item['pack_files']['size'])/1073741824, clean_file_name(item['pack_files']['filename']).upper()), 'icon': icon} \
				for item in pack_choices]
	heading = 'Choose Files to Download - %s' % clean_file_name(json.loads(pack_choices[0].get('source')).get('name'))
	kwargs = {'items': json.dumps(list_items), 'heading': heading, 'enumerate': 'true', 'multi_choice': 'true'}
	return select_dialog(pack_choices, **kwargs)

def get_title(meta):
	title = meta.get('custom_title', None) or meta.get('english_title') or meta.get('title')	
	return title

def get_year(meta):
	return meta.get('custom_year', None) or meta.get('year')

def get_season(meta):
		season = meta.get('custom_season', None) or meta.get('season')
		return int(season) if season else None

class Downloader:
	def __init__(self, params):
		self.params = params
		self.params_get = self.params.get

	def run(self):
		self.download_prep()
		if not self.action == 'meta.pack': show_busy_dialog()
		self.get_url_and_headers()
		if self.url in (None, 'None', ''): return self.return_notification(_notification='No URL found for Download. Pick another Source')
		self.get_filename()
		self.get_extension()
		if not self.download_check():
			if self.media_type == 'thumb_url': return
			return self.return_notification(_ok_dialog='Failed')
		if not self.confirm_download(): return self.return_notification(_notification='Cancelled')
		self.get_download_folder()
		if not self.get_destination_folder(): return self.return_notification(_notification='Cancelled')
		self.download_runner()

	def download_prep(self):
		if 'meta' in self.params:
			self.meta = json.loads(self.params_get('meta'))
			self.meta_get = self.meta.get
			self.media_type = self.meta_get('media_type')
			self.title = clean_file_name(get_title(self.meta))
			self.year = get_year(self.meta)
			self.season = get_season(self.meta)
			self.image = self.meta_get('poster') or poster_empty
			self.name = self.params_get('name')
		else:
			self.meta, self.name, self.year, self.season = None, None, None, None
			self.media_type = self.params_get('media_type')
			self.title = clean_file_name(self.params_get('name'))
			self.image = self.params_get('image')
		self.provider = self.params_get('provider')
		self.action = self.params_get('action')
		self.source = self.params_get('source')
		self.final_name = None

	def download_runner(self):
		self.final_destination = os.path.join(self.final_destination, self.final_name + self.extension)
		self.add_active_download()
		self.start_download()

	def get_active_downloads(self):
		return json.loads(get_property('fenlight.active_downloads') or '[]')

	def add_active_download(self):
		if self.action == 'image': return
		active_downloads = self.get_active_downloads()
		active_downloads.append(self.final_name)
		set_property('fenlight.active_downloads', json.dumps(active_downloads))

	def remove_active_download(self):
		if self.action == 'image': return
		active_downloads = self.get_active_downloads()
		try: active_downloads.remove(self.final_name)
		except: pass
		if active_downloads: set_property('fenlight.active_downloads', json.dumps(active_downloads))
		else: self.clear_active_downloads()

	def clear_active_downloads(self):
		clear_property('fenlight.active_downloads')

	def set_percent_property(self, percent):
		set_property('fenlight.%s' % self.final_name, str(percent))

	def check_status(self):
		status = get_property(status_property_string % self.final_name)
		if status in ('unpaused', 'cancelled'): clear_property(status_property_string % self.final_name)
		return status

	def get_url_and_headers(self):
		url = self.params_get('url')
		if url in (None, 'None', ''):
			if self.action == 'meta.single':
				try:
					source = json.loads(self.source)
					if source.get('scrape_provider', '') == 'easynews': source['url_dl'] = source['down_url']
					url = sources.resolve_sources(source, meta=self.meta)
					if 'torbox' in url:
						from apis.torbox_api import TorBoxAPI
						url = TorBoxAPI().add_headers_to_url(url)
				except: pass
			elif self.action == 'meta.pack':
				if self.provider == 'Real-Debrid':
					from apis.real_debrid_api import RealDebridAPI as debrid_function
				elif self.provider == 'Premiumize.me':
					from apis.premiumize_api import PremiumizeAPI as debrid_function
				elif self.provider == 'AllDebrid':
					from apis.alldebrid_api import AllDebridAPI as debrid_function
				elif self.provider == 'TorBox':
					from apis.torbox_api import TorBoxAPI as debrid_function
				url = self.params_get('pack_files')['link']
				if self.provider in ('Real-Debrid', 'AllDebrid'):
					url = debrid_function().unrestrict_link(url)
				elif self.provider == 'Premiumize.me':
					url = debrid_function().add_headers_to_url(url)
				elif self.provider == 'TorBox':
					url = debrid_function().unrestrict_link(url)
					url = debrid_function().add_headers_to_url(url)
		else:
			if self.action.startswith('cloud'):
				if '_direct' in self.action:
					url = self.params_get('url')
				elif 'realdebrid' in self.action:
					from indexers.real_debrid import resolve_rd
					url = resolve_rd(self.params)
				elif 'alldebrid' in self.action:
					from indexers.alldebrid import resolve_ad
					url = resolve_ad(self.params)
				elif 'premiumize' in self.action:
					from apis.premiumize_api import PremiumizeAPI
					url = PremiumizeAPI().add_headers_to_url(url)
				elif 'torbox' in self.action:
					from apis.torbox_api import TorBoxAPI
					from indexers.torbox import resolve_tb
					url = resolve_tb(self.params)
					url = TorBoxAPI().add_headers_to_url(url)
				elif 'easynews' in self.action:
					from indexers.easynews import resolve_easynews
					url = resolve_easynews(self.params)
		try: headers = dict(parse_qsl(url.rsplit('|', 1)[1]))
		except: headers = dict('')
		try: url = url.split('|')[0]
		except: pass
		self.url = url
		self.headers = headers

	def get_download_folder(self):
		self.down_folder = download_directory(self.media_type)
		if self.media_type == 'thumb_url': self.down_folder = os.path.join(self.down_folder, '.thumbs')
		for level in levels:
			try: make_directory(os.path.abspath(os.path.join(self.down_folder, level)))
			except: pass

	def get_destination_folder(self):
		if self.action == 'image':
			self.final_destination = self.down_folder
		elif self.action in ('meta.single', 'meta.pack'):
			default_name = '%s (%s)' % (self.title, self.year)
			if self.action == 'meta.single': folder_rootname = kodi_dialog().input('Title', defaultt=default_name)
			else: folder_rootname = self.params_get('default_foldername', default_name)
			if not folder_rootname: return False
			if self.media_type == 'episode':
				inter = os.path.join(self.down_folder, folder_rootname)
				make_directory(inter)
				self.final_destination = os.path.join(inter, 'Season %02d' %  int(self.season))
			else: self.final_destination = os.path.join(self.down_folder, folder_rootname)
		else: self.final_destination = self.down_folder
		make_directory(self.final_destination)
		return True

	def get_filename(self):
		if self.final_name: final_name = self.final_name
		elif self.action == 'meta.pack':
			name = self.params_get('pack_files')['filename']
			final_name = os.path.splitext(urlparse(name).path)[0].split('/')[-1]
		elif self.action == 'image':
			final_name = self.title
		else:
			name_url = unquote(self.url)
			file_name = clean_title(name_url.split('/')[-1])
			if clean_title(self.title).lower() in file_name.lower():
				final_name = os.path.splitext(urlparse(name_url).path)[0].split('/')[-1]
			else:
				try: final_name = self.name.translate(None, r'\/:*?"<>|').strip('.')
				except: final_name = os.path.splitext(urlparse(name_url).path)[0].split('/')[-1]
		self.final_name = safe_string(remove_accents(final_name))

	def get_extension(self):
		if self.action == 'archive':
			ext = 'zip'
		elif self.action == 'image':
			ext = os.path.splitext(urlparse(self.url).path)[1][1:]
			if not ext in image_extensions: ext = 'jpg'
		else:
			ext = os.path.splitext(urlparse(self.url).path)[1][1:]
			if not ext in video_extensions: ext = 'mp4'
		ext = '.%s' % ext
		self.extension = ext

	def download_check(self):
		self.resp = self.get_response()
		if not self.resp: return False
		try: self.content = int(self.resp.headers['Content-Length'])
		except: self.content = 0
		try: self.resumable = 'bytes' in self.resp.headers['Accept-Ranges'].lower()
		except: self.resumable = False
		if self.content < 1: return False
		self.size = 1024 * 1024
		self.mb = self.content / (1024 * 1024)
		if self.content < self.size: self.size = self.content
		hide_busy_dialog()
		return True

	def start_download(self):
		monitor_progress = self.action != 'image'
		total, errors, count, resume, sleep_time  = 0, 0, 0, 0, 0
		f = open_file(self.final_destination, 'w')
		chunk  = None
		chunks = []
		while True:
			downloaded = total
			for c in chunks: downloaded += len(c)
			percent = min(round(float(downloaded)*100 / self.content), 100)
			if monitor_progress:
				status = self.check_status()
				if status == 'paused':
					while status == 'paused':
						status = self.check_status()
						sleep(1000)
				if status == 'cancelled': return self.finish_download(status)
				if percent % 5 == 0: self.set_percent_property(percent)
			chunk = None
			error = False
			try:        
				chunk  = self.resp.read(self.size)
				if not chunk:
					if percent < 99:
						error = True
					else:
						while len(chunks) > 0:
							c = chunks.pop(0)
							f.write(c)
							del c
						f.close()
						return self.finish_download('success')
			except Exception as e:
				error = True
				sleep_time = 10
				errno = 0
				if hasattr(e, 'errno'):
					errno = e.errno
				if errno == 10035: # 'A non-blocking socket operation could not be completed immediately'
					pass
				if errno == 10054: #'An existing connection was forcibly closed by the remote host'
					errors = 10 #force resume
					sleep_time = 30
				if errno == 11001: # 'getaddrinfo failed'
					errors = 10 #force resume
					sleep_time = 30
			if chunk:
				errors = 0
				chunks.append(chunk)
				if len(chunks) > 5:
					c = chunks.pop(0)
					f.write(c)
					total += len(c)
					del c
			if error:
				errors += 1
				count  += 1
				sleep(sleep_time*1000)
			if (self.resumable and errors > 0) or errors >= 10:
				if (not self.resumable and resume >= 50) or resume >= 500:
					return self.finish_download('failed')
				resume += 1
				errors  = 0
				if self.resumable:
					chunks  = []
					self.resp = self.get_response(total)
				else: pass

	def get_response(self, size=0):
		try:
			headers = self.headers
			if size > 0:
				size = int(size)
				headers['Range'] = 'bytes=%d-' % size
			req = Request(self.url, headers=headers)
			resp = urlopen(req, context=ctx, timeout=30)
			return resp
		except: return None

	def finish_download(self, status):
		if self.action == 'image':
			if self.media_type == 'image_url': return notification(status.upper(), 2500, self.final_destination)
			else: return
		if not get_visibility('Window.IsActive(fullscreenvideo)'):
			notification('[B]%s[/B] %s' % (status.upper(), self.final_name.replace('.', ' ').replace('_', ' ')), 2500, self.image)
		self.remove_active_download()

	def confirm_download(self):
		return True if self.action in ('image', 'meta.pack') else confirm_dialog(heading=self.final_name, text='Complete file is [B]%dMB[/B][CR]Continue with download?' % self.mb)

	def return_notification(self, _notification=None, _ok_dialog=None):
		hide_busy_dialog()
		if _notification: notification(_notification, 2500)
		elif _ok_dialog: ok_dialog(text=_ok_dialog)
		else: return

def viewer(params):
	def _process():
		for info in results:
			try:
				path = info[0]
				url = os.path.join(folder_path, path)
				listitem = make_listitem()
				listitem.setLabel(clean_file_name(normalize(path)))
				listitem.setArt({'fanart': fanart})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				yield (url, listitem, info[1])
			except: pass
	handle = int(sys.argv[1])
	folder_path = download_directory(params['folder_type'])
	dirs, files = list_dirs(folder_path)
	results = [(i, True) for i in dirs] + [(i, False) for i in files]
	item_list = list(_process())
	add_items(handle, item_list)
	set_sort_method(handle, 'files')
	set_content(handle, '')
	set_category(handle, params.get('name'))
	end_directory(handle)
	set_view_mode('view.main', '')

def manager(foo=None):
	from windows.base_window import open_window
	kwargs = {}
	return open_window(('windows.downloads_manager', 'DownloadsManager'), 'downloads_manager.xml', **kwargs)
