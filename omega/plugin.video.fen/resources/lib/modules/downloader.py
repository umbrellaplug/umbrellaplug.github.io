# -*- coding: utf-8 -*-
import os
import ssl
from urllib.request import Request, urlopen
from modules import kodi_utils
from modules.sources import Sources
from modules.settings import download_directory, get_art_provider, metadata_user_info
from modules.utils import clean_file_name, clean_title, safe_string, remove_accents, normalize
# logger = kodi_utils.logger

json, Thread, ls, urlparse, parse_qsl, notification = kodi_utils.json, kodi_utils.Thread, kodi_utils.local_string, kodi_utils.urlparse, kodi_utils.parse_qsl, kodi_utils.notification
video_extensions, image_extensions, get_icon, dialog, unquote = kodi_utils.video_extensions, kodi_utils.image_extensions, kodi_utils.get_icon, kodi_utils.dialog, kodi_utils.unquote
sleep, set_category, poster_empty, get_setting, select_dialog = kodi_utils.sleep, kodi_utils.set_category, kodi_utils.empty_poster, kodi_utils.get_setting, kodi_utils.select_dialog
add_items, set_sort_method, set_content, end_directory, sys = kodi_utils.add_items, kodi_utils.set_sort_method, kodi_utils.set_content, kodi_utils.end_directory, kodi_utils.sys
player, confirm_dialog, ok_dialog, addon_fanart, build_url = kodi_utils.player, kodi_utils.confirm_dialog, kodi_utils.ok_dialog, kodi_utils.addon_fanart, kodi_utils.build_url
show_busy_dialog, hide_busy_dialog, make_directory, open_file = kodi_utils.show_busy_dialog, kodi_utils.hide_busy_dialog, kodi_utils.make_directory, kodi_utils.open_file
set_view_mode, make_listitem, list_dirs = kodi_utils.set_view_mode, kodi_utils.make_listitem, kodi_utils.list_dirs
sources = Sources()
ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
levels =['../../../..', '../../..', '../..', '..']

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
		threads = []
		append = threads.append
		provider = params['provider']
		if provider == 'furk':
			try:
				t_files = sources.furkPacks(params['file_name'], params['file_id'], download=True)
				pack_choices = [dict(params, **{'pack_files':{'link': item['url_dl'], 'filename': item['name'], 'size': item['size']}}) for item in t_files]
				icon = 'furk'
			except: return notification(32692)
		else:
			try:
				debrid_files, debrid_function = sources.debridPacks(provider, params['name'], params['magnet_url'], params['info_hash'], download=True)
				pack_choices = [dict(params, **{'pack_files':item}) for item in debrid_files]
				icon = {'Real-Debrid': 'realdebrid', 'Premiumize.me': 'premiumize', 'AllDebrid': 'alldebrid'}[provider]
			except: return notification(32692)
		default_icon = get_icon(icon)
		chosen_list = select_pack_item(pack_choices, default_icon)
		if not chosen_list: return
		if provider == 'furk': show_package = True
		else: show_package = json.loads(params['source']).get('package') == 'show'
		meta  = json.loads(chosen_list[0].get('meta'))
		art_provider = get_art_provider()
		image = meta.get('custom_poster') or meta.get(art_provider[0]) or meta.get(art_provider[1]) or poster_empty
		default_name = '%s (%s)' % (clean_file_name(get_title(meta)), get_year(meta))
		default_foldername = dialog.input(ls(32228), defaultt=default_name)
		for item in chosen_list:
			if show_package:
				season = find_season_in_release_title(item['pack_files']['filename'])
				if season:
					meta['season'] = season
					item['meta'] = json.dumps(meta)
					item['default_foldername'] = default_foldername
			append(Thread(target=Downloader(item).run))
		download_threads_manager(threads, image)
	else: Downloader(params).run()

def download_threads_manager(threads, image):
	notification(32134, 3500, image)
	for thread in threads:
		while len([x for x in threads if x.is_alive()]) >= 2: sleep(2000)
		thread.start()

def select_pack_item(pack_choices, icon):
	list_items = [{'line1': '%.2f GB | %s' % (float(item['pack_files']['size'])/1073741824, clean_file_name(item['pack_files']['filename']).upper()), 'icon': icon} \
				for item in pack_choices]
	heading = '%s - %s' % (ls(32031), clean_file_name(json.loads(pack_choices[0].get('source')).get('name')))
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
		if self.url in (None, 'None', ''): return self.return_notification(_notification=32692)
		self.get_filename()
		self.get_extension()
		if not self.download_check(): return self.return_notification(_ok_dialog=32490)
		if not self.confirm_download(): return self.return_notification(_notification=32736)
		self.get_download_folder()
		if not self.get_destination_folder(): return self.return_notification(_notification=32736)
		self.download_runner()

	def download_prep(self):
		if 'meta' in self.params:
			art_provider = get_art_provider()
			self.meta = json.loads(self.params_get('meta'))
			self.meta_get = self.meta.get
			self.media_type = self.meta_get('media_type')
			self.title = clean_file_name(get_title(self.meta))
			self.year = get_year(self.meta)
			self.season = get_season(self.meta)
			self.image = self.meta_get('custom_poster') or self.meta_get(art_provider[0]) or self.meta_get(art_provider[1]) or poster_empty
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
		self.start_download()

	def get_url_and_headers(self):
		url = self.params_get('url')
		if url in (None, 'None', ''):
			if self.action == 'meta.single':
				source = json.loads(self.source)
				if source.get('scrape_provider', '') == 'easynews': source['url_dl'] = source['down_url']
				url = sources.resolve_sources(source, meta=self.meta)
			elif self.action == 'meta.pack':
				if self.provider == 'Real-Debrid':
					from apis.real_debrid_api import RealDebridAPI as debrid_function
				elif self.provider == 'Premiumize.me':
					from apis.premiumize_api import PremiumizeAPI as debrid_function
				elif self.provider == 'AllDebrid':
					from apis.alldebrid_api import AllDebridAPI as debrid_function
				url = self.params_get('pack_files')['link']
				if self.provider in ('Real-Debrid', 'AllDebrid'):
					url = debrid_function().unrestrict_link(url)
				elif self.provider == 'Premiumize.me':
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
		if self.media_type == 'thumb_url':
			self.down_folder = os.path.join(self.down_folder, '.thumbs')
		for level in levels:
			try: make_directory(os.path.abspath(os.path.join(self.down_folder, level)))
			except: pass

	def get_destination_folder(self):
		if self.action == 'image':
			self.final_destination = self.down_folder
		elif self.action in ('meta.single', 'meta.pack'):
			default_name = '%s (%s)' % (self.title, self.year)
			if self.action == 'meta.single': folder_rootname = dialog.input(ls(32228), defaultt=default_name)
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
		if self.action not in ('image', 'meta.pack'):
			show_notifications = True
			notification_frequency = 25
		else:
			show_notifications = False
			notification_frequency = 0
		notify, total, errors, count, resume, sleep_time  = 25, 0, 0, 0, 0, 0
		f = open_file(self.final_destination, 'w')
		chunk  = None
		chunks = []
		while True:
			downloaded = total
			for c in chunks: downloaded += len(c)
			percent = min(round(float(downloaded)*100 / self.content), 100)
			if show_notifications:
				if percent >= notify:
					notify += notification_frequency
					try:
						line1 = '%s - [I]%s[/I]' % (str(percent)+'%', self.final_name)
						if not player.isPlaying(): notification(line1, 3000, self.image)
					except: pass
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
						return self.finish_download(True)
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
					return self.finish_download(False)
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

	def finish_download(self, downloaded):
		if self.action == 'meta.pack' or self.media_type == 'thumb_url': return
		if self.media_type == 'image_url': return notification('[I]%s[/I]' % ls(32576) if downloaded else ls(32691), 2500, self.image)
		text = '[B]%s[/B] : %s' % (self.final_name.replace('.', ' ').replace('_', ' '), '%s %s' % (ls(32107), ls(32576) if downloaded else ls(32490)))
		if downloaded and not player.isPlaying(): ok_dialog(text=text)

	def confirm_download(self):
		return True if self.action in ('image', 'meta.pack') else confirm_dialog(heading=self.final_name, text='%s[CR]%s' % (ls(32688) % self.mb, ls(32689)))

	def return_notification(self, _notification=None, _ok_dialog=None):
		hide_busy_dialog()
		if _notification: notification(_notification, 2500)
		elif _ok_dialog: ok_dialog(text=_ok_dialog)
		else: return

def download_manager(params):
	def _process():
		for info in results:
			try:
				path = info[0]
				url = os.path.join(folder_path, path)
				listitem = make_listitem()
				listitem.setLabel(clean_file_name(normalize(path)))
				listitem.setArt({'fanart': addon_fanart})
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
