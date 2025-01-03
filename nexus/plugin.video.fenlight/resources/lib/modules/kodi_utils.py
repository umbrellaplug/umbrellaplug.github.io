# -*- coding: utf-8 -*-
# TRUMP WON
import xbmc, xbmcgui, xbmcplugin, xbmcvfs, xbmcaddon
from os import path as osPath
from urllib.parse import urlencode
from modules import icons
try: xbmc_actor = xbmc.Actor
except: xbmc_actor = None
xbmc_player, numeric_input, xbmc_monitor, translatePath = xbmc.Player, 1, xbmc.Monitor, xbmcvfs.translatePath
ListItem, getSkinDir, log, getCurrentWindowId, Window = xbmcgui.ListItem, xbmc.getSkinDir, xbmc.log, xbmcgui.getCurrentWindowId, xbmcgui.Window
File, exists, copy, delete, rmdir, rename = xbmcvfs.File, xbmcvfs.exists, xbmcvfs.copy, xbmcvfs.delete, xbmcvfs.rmdir, xbmcvfs.rename
get_infolabel, get_visibility, execute_JSON, window_xml_dialog = xbmc.getInfoLabel, xbmc.getCondVisibility, xbmc.executeJSONRPC, xbmcgui.WindowXMLDialog
executebuiltin, xbmc_sleep, convertLanguage, getSupportedMedia, PlayList = xbmc.executebuiltin, xbmc.sleep, xbmc.convertLanguage, xbmc.getSupportedMedia, xbmc.PlayList
progressDialogBG = xbmcgui.DialogProgressBG
endOfDirectory, addSortMethod, listdir, mkdir, mkdirs = xbmcplugin.endOfDirectory, xbmcplugin.addSortMethod, xbmcvfs.listdir, xbmcvfs.mkdir, xbmcvfs.mkdirs
addDirectoryItem, addDirectoryItems, setContent, setCategory = xbmcplugin.addDirectoryItem, xbmcplugin.addDirectoryItems, xbmcplugin.setContent, xbmcplugin.setPluginCategory
path_join = osPath.join
img_url = 'https://i.imgur.com/%s.png'
invoker_switch_dict = {'true': 'false', 'false': 'true'}
empty_poster, nextpage = img_url % icons.box_office, img_url % icons.nextpage
nextpage_landscape = img_url % icons.nextpage_landscape
tmdb_default_api = 'b370b60447737762ca38457bd77579b3'
trakt_default_id = '1038ef327e86e7f6d39d80d2eb5479bff66dd8394e813c5e0e387af0f84d89fb'
trakt_default_secret = '8d27a92e1d17334dae4a0590083a4f26401cb8f721f477a79fd3f218f8534fd1'
myvideos_db_paths = {19: '119', 20: '121', 21: '124'}
sort_method_dict = {'episodes': 24, 'files': 5, 'label': 2, 'none': 0}
playlist_type_dict = {'music': 0, 'video': 1}
tmdb_dict_removals = ('adult', 'backdrop_path', 'genre_ids', 'original_language', 'original_title', 'overview', 'popularity', 'vote_count', 'video', 'origin_country', 'original_name')
with_media_removals = ('description', 'privacy', 'type', 'share_link', 'display_numbers', 'allow_comments', 'sort_by', 'sort_how', 'created_at', 'updated_at', 'comment_count')
single_ep_list = ('episode.progress', 'episode.recently_watched', 'episode.next_trakt', 'episode.next_fenlight', 'episode.trakt_recently_aired', 'episode.trakt_calendar')
scraper_names = ['EXTERNAL SCRAPERS', 'EASYNEWS', 'RD CLOUD', 'PM CLOUD', 'AD CLOUD', 'OC CLOUD', 'TB CLOUD', 'FOLDERS 1-5']
random_valid_type_check = {'build_movie_list': 'movie', 'build_tvshow_list': 'tvshow', 'build_season_list': 'season', 'build_episode_list': 'episode',
				'build_in_progress_episode': 'single_episode', 'build_recently_watched_episode': 'single_episode', 'build_next_episode': 'single_episode',
				'build_my_calendar': 'single_episode', 'build_trakt_lists': 'trakt_list', 'trakt.list.build_trakt_list': 'trakt_list', 'build_trakt_my_lists_contents': 'trakt_list'}
extras_button_label_values = {
				'movie':
					{'movies_play': 'Playback', 'show_trailers': 'Trailer', 'show_images': 'Images',  'show_extrainfo': 'Extra Info', 'show_genres': 'Genres',
					'show_director': 'Director', 'show_options': 'Options', 'show_recommended': 'Recommended', 'show_more_like_this': 'More Like This',
					'show_trakt_manager': 'Trakt Manager', 'playback_choice': 'Playback Options', 'show_favorites_manager': 'Favorites Manager', 'show_plot': 'Plot',
					'show_keywords': 'Keywords', 'show_in_trakt_lists': 'In Trakt Lists', 'close_all': 'Close All Dialogs'},
				'tvshow':
					{'tvshow_browse': 'Browse', 'show_trailers': 'Trailer', 'show_images': 'Images', 'show_extrainfo': 'Extra Info', 'show_genres': 'Genres',
					'play_nextep': 'Play Next', 'show_options': 'Options', 'show_recommended': 'Recommended', 'show_more_like_this': 'More Like This',
					'show_trakt_manager': 'Trakt Manager', 'play_random_episode': 'Play Random', 'show_favorites_manager': 'Favorites Manager', 'show_plot': 'Plot',
					'show_keywords': 'Keywords', 'show_in_trakt_lists': 'In Trakt Lists', 'close_all': 'Close All Dialogs'}}
video_extensions = ('m4v', '3g2', '3gp', 'nsv', 'tp', 'ts', 'ty', 'pls', 'rm', 'rmvb', 'mpd', 'ifo', 'mov', 'qt', 'divx', 'xvid', 'bivx', 'vob', 'nrg', 'img', 'iso', 'udf', 'pva',
					'wmv', 'asf', 'asx', 'ogm', 'm2v', 'avi', 'bin', 'dat', 'mpg', 'mpeg', 'mp4', 'mkv', 'mk3d', 'avc', 'vp3', 'svq3', 'nuv', 'viv', 'dv', 'fli', 'flv', 'wpl',
					'xspf', 'vdr', 'dvr-ms', 'xsp', 'mts', 'm2t', 'm2ts', 'evo', 'ogv', 'sdp', 'avs', 'rec', 'url', 'pxml', 'vc1', 'h264', 'rcv', 'rss', 'mpls', 'mpl', 'webm',
					'bdmv', 'bdm', 'wtv', 'trp', 'f4v', 'pvr', 'disc')
image_extensions = ('jpg', 'jpeg', 'jpe', 'jif', 'jfif', 'jfi', 'bmp', 'dib', 'png', 'gif', 'webp', 'tiff', 'tif',
					'psd', 'raw', 'arw', 'cr2', 'nrw', 'k25', 'jp2', 'j2k', 'jpf', 'jpx', 'jpm', 'mj2')

def kodi_dialog():
	return xbmcgui.Dialog()

def addon_info(info):
	return xbmcaddon.Addon('plugin.video.fenlight').getAddonInfo(info)

def addon_version():
	return get_property('fenlight.addon_version') or addon_info('version')

def addon_path():
	return get_property('fenlight.addon_path') or addon_info('path')

def addon_profile():
	return get_property('fenlight.addon_profile') or translatePath(addon_info('profile'))

def addon_icon():
	return get_property('fenlight.addon_icon') or addon_info('icon')

def addon_fanart():
	return get_property('fenlight.addon_fanart') or addon_info('fanart')

def get_icon(image_name):
	return img_url % getattr(icons, image_name, 'I1JJhji')

def get_addon_fanart():
	return get_property('fenlight.default_addon_fanart') or addon_fanart()

def build_url(url_params):
	return 'plugin://plugin.video.fenlight/?%s' % urlencode(url_params)

def add_dir(url_params, list_name, handle, iconImage='folder', fanartImage=None, isFolder=True):
	fanart = fanartImage or get_addon_fanart()
	icon = get_icon(iconImage)
	url = build_url(url_params)
	listitem = make_listitem()
	listitem.setLabel(list_name)
	listitem.setArt({'icon': icon, 'poster': icon, 'thumb': icon, 'fanart': fanart, 'banner': fanart})
	info_tag = listitem.getVideoInfoTag()
	info_tag.setPlot(' ')
	add_item(handle, url, listitem, isFolder)

def make_listitem():
	return ListItem(offscreen=True)

def add_item(handle, url, listitem, isFolder):
	addDirectoryItem(handle, url, listitem, isFolder)

def add_items(handle, item_list):
	addDirectoryItems(handle, item_list)

def set_content(handle, content):
	setContent(handle, content)

def set_category(handle, label):
	setCategory(handle, label)

def end_directory(handle, cacheToDisc=True):
	endOfDirectory(handle, cacheToDisc=cacheToDisc)

def set_view_mode(view_type, content='files', is_external=None):
	if not get_property('fenlight.use_viewtypes') == 'true': return
	if is_external == None: is_external = external()
	if is_external: return
	view_id = get_property('fenlight.%s' % view_type) or None
	if not view_id: return
	try:
		hold = 0
		sleep(100)
		while not container_content() == content:
			hold += 1
			if hold < 3000: sleep(1)
			else: return
		execute_builtin('Container.SetViewMode(%s)' % view_id)
	except: return

def remove_keys(dict_item, dict_removals):
	for k in dict_removals: dict_item.pop(k, None)
	return dict_item

def append_path(_path):
	import sys
	sys.path.append(translatePath(_path))

def logger(heading, function):
	log('###%s###: %s' % (heading, function), 1)

def kodi_window():
	return Window(10000)

def get_property(prop):
	return kodi_window().getProperty(prop)

def set_property(prop, value):
	return kodi_window().setProperty(prop, value)

def clear_property(prop):
	return kodi_window().clearProperty(prop)

def clear_all_properties():
	return kodi_window().clearProperties()

def addon(addon_id='plugin.video.fenlight'):
	return xbmcaddon.Addon(id=addon_id)

def addon_installed(addon_id):
	return get_visibility('System.HasAddon(%s)' % addon_id)

def addon_enabled(addon_id):
	return get_visibility('System.AddonIsEnabled(%s)' % addon_id)

def container_content():
	return get_infolabel('Container.Content')

def set_sort_method(handle, method):
	addSortMethod(handle, sort_method_dict[method])

def make_session(url='https://'):
	import requests
	session = requests.Session()
	session.mount(url, requests.adapters.HTTPAdapter(pool_maxsize=100))
	return session	

def make_playlist(playlist_type='video'):
	return PlayList(playlist_type_dict[playlist_type])

def convert_language(lang):
	return convertLanguage(lang, 1)

def supported_media():
	return getSupportedMedia('video')

def path_exists(path):
	return exists(path)

def open_file(_file, mode='r'):
	return File(_file, mode)

def copy_file(source, destination):
	return copy(source, destination)

def delete_file(_file):
	delete(_file)

def delete_folder(_folder, force=False):
	rmdir(_folder, force)

def rename_file(old, new):
	rename(old, new)

def list_dirs(location):
	return listdir(location)

def make_directory(path):
	mkdir(path)

def make_directories(path):
	mkdirs(path)

def translate_path(path):
	return translatePath(path)

def sleep(time):
	return xbmc_sleep(time)

def execute_builtin(command, block=False):
	return executebuiltin(command, block)

def current_skin():
	return getSkinDir()

def get_window_id():
	return getCurrentWindowId()

def current_window_object():
	return Window(get_window_id())

def kodi_version():
	return int(get_infolabel('System.BuildVersion')[0:2])

def get_video_database_path():
	return translate_path('special://profile/Database/MyVideos%s.db' % myvideos_db_paths[kodi_version()])

def show_busy_dialog():
	return execute_builtin('ActivateWindow(busydialognocancel)')

def hide_busy_dialog():
	execute_builtin('Dialog.Close(busydialognocancel)')
	execute_builtin('Dialog.Close(busydialog)')

def close_dialog(dialog, block=False):
	execute_builtin('Dialog.Close(%s,true)' % dialog, block)

def close_all_dialog():
	execute_builtin('Dialog.Close(all,true)')

def run_addon(addon='plugin.video.fenlight', block=False):
	return execute_builtin('RunAddon(%s)' % addon, block)

def external():
	return 'fenlight' not in get_infolabel('Container.PluginName')

def home():
	return getCurrentWindowId() == 10000

def folder_path():
	return get_infolabel('Container.FolderPath')

def path_check(string):
	return string in folder_path()

def reload_skin():
	execute_builtin('ReloadSkin()')

def kodi_refresh():
	execute_builtin('UpdateLibrary(video,special://skin/foo)')

def refresh_widgets(show_notification='false'):
	set_property('fenlight.refresh_widgets', 'true')
	sleep(250)
	run_plugin({'mode': 'kodi_refresh'}, block=True)
	if show_notification == 'true': notification('Widgets Refreshed', 2500)
	sleep(5000)
	clear_property('fenlight.refresh_widgets')

def run_plugin(params, block=False):
	if isinstance(params, dict): params = build_url(params)
	return execute_builtin('RunPlugin(%s)' % params, block)

def container_update(params, block=False):
	if isinstance(params, dict): params = build_url(params)
	return execute_builtin('Container.Update(%s)' % params, block)

def activate_window(params, block=False):
	if isinstance(params, dict): params = build_url(params)
	return execute_builtin('ActivateWindow(Videos,%s,return)' % params, block)

def container_refresh():
	return execute_builtin('Container.Refresh')

def container_refresh_input(params, block=False):
	if isinstance(params, dict): params = build_url(params)
	return execute_builtin('Container.Refresh(%s)' % params, block)

def replace_window(params, block=False):
	if isinstance(params, dict): params = build_url(params)
	return execute_builtin('ReplaceWindow(Videos,%s)' % params, block)

def disable_enable_addon(addon_name='plugin.video.fenlight'):
	import json
	try:
		execute_JSON(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'Addons.SetAddonEnabled', 'params': {'addonid': addon_name, 'enabled': False}}))
		execute_JSON(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'Addons.SetAddonEnabled', 'params': {'addonid': addon_name, 'enabled': True}}))
	except: pass

def update_local_addons():
	execute_builtin('UpdateLocalAddons', True)
	sleep(2500)
 
def update_kodi_addons_db(addon_name='plugin.video.fenlight'):
	import time
	import sqlite3 as database
	try:
		date = time.strftime('%Y-%m-%d %H:%M:%S')
		dbcon = database.connect(translate_path('special://database/Addons33.db'), timeout=40.0)
		dbcon.execute("INSERT OR REPLACE INTO installed (addonID, enabled, lastUpdated) VALUES (?, ?, ?)", (addon_name, 1, date))
		dbcon.close()
	except: pass

def get_jsonrpc(request):
	import json
	response = execute_JSON(json.dumps(request))
	result = json.loads(response)
	return result.get('result', None)

def jsonrpc_get_directory(directory, properties=['title', 'file', 'thumbnail']):
	command = {'jsonrpc': '2.0', 'id': 1, 'method': 'Files.GetDirectory', 'params': {'directory': directory, 'media': 'files', 'properties': properties}}
	try: results = [i for i in get_jsonrpc(command).get('files') if i['file'].startswith('plugin://') and i['filetype'] == 'directory']
	except: results = None
	return results

def jsonrpc_get_addons(_type, properties=['thumbnail', 'name']):
	command = {'jsonrpc': '2.0', 'method': 'Addons.GetAddons','params':{'type':_type, 'properties': properties}, 'id': '1'}
	results = get_jsonrpc(command).get('addons')
	return results

def jsonrpc_get_system_setting(setting_id, setting_value=''):
	command = {'jsonrpc': '2.0', 'id': 1, 'method': 'Settings.GetSettingValue', 'params': {'setting': setting_id}}
	try: result = get_jsonrpc(command)['value']
	except: result = setting_value
	return result

def open_settings():
	from windows.base_window import open_window
	open_window(('windows.settings_manager', 'SettingsManager'), 'settings_manager.xml')

def external_scraper_settings():
	try:
		external = get_property('fenlight.external_scraper.module')
		if external in ('empty_setting', ''): return
		execute_builtin('Addon.OpenSettings(%s)' % external)
	except: pass

def progress_dialog(heading='', icon=None):
	from threading import Thread
	from windows.base_window import create_window
	progress_dialog = create_window(('windows.progress', 'Progress'), 'progress.xml', heading=heading, icon=icon or addon_icon())
	Thread(target=progress_dialog.run).start()
	return progress_dialog

def select_dialog(function_list, **kwargs):
	from windows.base_window import open_window
	selection = open_window(('windows.default_dialogs', 'Select'), 'select.xml', **kwargs)
	if selection in (None, []): return selection
	if kwargs.get('multi_choice', 'false') == 'true': return [function_list[i] for i in selection]
	return function_list[selection]

def confirm_dialog(heading='', text='Are you sure?', ok_label='OK', cancel_label='Cancel', default_control=11):
	from windows.base_window import open_window
	kwargs = {'heading': heading, 'text': text, 'ok_label': ok_label, 'cancel_label': cancel_label, 'default_control': default_control}
	return open_window(('windows.default_dialogs', 'Confirm'), 'confirm.xml', **kwargs)

def ok_dialog(heading='', text='No Results', ok_label='OK'):
	from windows.base_window import open_window
	kwargs = {'heading': heading, 'text': text, 'ok_label': ok_label}
	return open_window(('windows.default_dialogs', 'OK'), 'ok.xml', **kwargs)

def show_text(heading, text=None, file=None, font_size='small', kodi_log=False):
	from windows.base_window import open_window
	heading = heading.replace('[B]', '').replace('[/B]', '')
	if file:
		with open(file, encoding='utf-8') as r: text = r.readlines()
	if kodi_log:
		confirm = confirm_dialog(text='Show Log Errors Only?', ok_label='Yes', cancel_label='No')
		if confirm == None: return
		if confirm: text = [i for i in text if any(x in i.lower() for x in ('exception', 'error', '[test]'))]
	text = ''.join(text)
	return open_window(('windows.textviewer', 'TextViewer'), 'textviewer.xml', heading=heading, text=text, font_size=font_size)

def notification(line1, time=5000, icon=None):
	kodi_dialog().notification('Fen Light', line1, icon or addon_icon(), time)

def timeIt(func):
	# Thanks to 123Venom
	import time
	fnc_name = func.__name__
	def wrap(*args, **kwargs):
		started_at = time.time()
		result = func(*args, **kwargs)
		logger('%s.%s' % (__name__ , fnc_name), (time.time() - started_at))
		return result
	return wrap

def volume_checker():
	# 0% == -60db, 100% == 0db
	try:
		if get_property('fenlight.playback.volumecheck_enabled') == 'false' or get_visibility('Player.Muted'): return
		from modules.utils import string_alphanum_to_num
		max_volume = min(int(get_property('fenlight.playback.volumecheck_percent') or '50'), 100)
		if int(100 - (float(string_alphanum_to_num(get_infolabel('Player.Volume').split('.')[0]))/60)*100) > max_volume: execute_builtin('SetVolume(%d)' % max_volume)
	except: pass

def focus_index(index):
	current_window = current_window_object()
	focus_id = current_window.getFocusId()
	try: current_window.getControl(focus_id).selectItem(index)
	except: pass

def get_all_icon_vars(include_values=False):
	if include_values: return [(k, v) for k, v in vars(icons).items() if not k.startswith('__')]
	else: return [k for k, v in vars(icons).items() if not k.startswith('__')]

def toggle_language_invoker():
	from xml.dom.minidom import parse as mdParse
	close_all_dialog()
	addon_xml = translate_path('special://home/addons/plugin.video.fenlight/addon.xml')
	root = mdParse(addon_xml)
	invoker_instance = root.getElementsByTagName('reuselanguageinvoker')[0].firstChild
	current_invoker_setting = invoker_instance.data
	new_value = invoker_switch_dict[current_invoker_setting]
	if not confirm_dialog(text='Turn [B]Reuse Langauage Invoker[/B] %s?' % ('On' if new_value == 'true' else 'Off')): return
	invoker_instance.data = new_value
	new_xml = str(root.toxml()).replace('<?xml version="1.0" ?>', '')
	with open(addon_xml, 'w') as f: f.write(new_xml)
	execute_builtin('ActivateWindow(Home)', True)
	update_local_addons()
	disable_enable_addon()

def upload_logfile(params):
	import json
	import requests
	log_files = [('Current Kodi Log', 'kodi.log'), ('Previous Kodi Log', 'kodi.old.log')]
	list_items = [{'line1': i[0]} for i in log_files]
	kwargs = {'items': json.dumps(list_items), 'heading': 'Choose Which Log File to Upload', 'narrow_window': 'true'}
	log_file = select_dialog(log_files, **kwargs)
	if log_file == None: return
	log_name, log_file = log_file
	if not confirm_dialog(heading=log_name): return
	show_busy_dialog()
	url = 'https://paste.kodi.tv/'
	log_file = translate_path('special://logpath/%s' % log_file)
	if not path_exists(log_file): return ok_dialog(text='Error. Log Upload Failed')
	try:
		with open_file(log_file) as f: text = f.read()
		UserAgent = 'Fenlight %s' % addon_version()
		response = requests.post('%s%s' % (url, 'documents'), data=text.encode('utf-8', errors='ignore'), headers={'User-Agent': UserAgent}).json()
		user_code = response['key']
		if 'key' in response:
			try:
				from modules.utils import copy2clip
				copy2clip('%s%s' % (url, user_code))
			except: pass
			ok_dialog(text='%s%s' % (url, user_code))
		else: ok_dialog(text='Error. Log Upload Failed')
	except: ok_dialog(text='Error. Log Upload Failed')
	hide_busy_dialog()

def fetch_kodi_imagecache(image):
	import sqlite3 as database
	result = None
	try:
		dbcon = database.connect(translate_path('special://database/Textures13.db'), timeout=40.0)
		dbcur = dbcon.cursor()
		dbcur.execute("SELECT cachedurl FROM texture WHERE url = ?", (image,))
		result = dbcur.fetchone()[0]
	except: pass
	return result
