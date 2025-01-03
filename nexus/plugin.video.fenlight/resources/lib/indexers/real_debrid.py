# -*- coding: utf-8 -*-
import sys
from datetime import datetime
from modules.utils import datetime_workaround
from apis.real_debrid_api import RealDebridAPI
from modules import kodi_utils
from modules.source_utils import supported_video_extensions
from modules.utils import clean_file_name, normalize, jsondate_to_datetime
# logger = kodi_utils.logger

show_busy_dialog, hide_busy_dialog, show_text, set_view_mode = kodi_utils.show_busy_dialog, kodi_utils.hide_busy_dialog, kodi_utils.show_text, kodi_utils.set_view_mode
add_items, set_content, end_directory = kodi_utils.add_items, kodi_utils.set_content, kodi_utils.end_directory
notification, execute_builtin, confirm_dialog = kodi_utils.notification, kodi_utils.execute_builtin, kodi_utils.confirm_dialog
default_rd_icon, fanart = kodi_utils.get_icon('realdebrid'), kodi_utils.get_addon_fanart()
make_listitem, build_url = kodi_utils.make_listitem, kodi_utils.build_url
extensions = supported_video_extensions()
RealDebrid = RealDebridAPI()

def rd_cloud():
	def _builder():
		for count, item in enumerate(cloud_files, 1):
			try:
				cm = []
				cm_append = cm.append
				folder_name, folder_id = item['filename'], item['id']
				clean_folder_name = clean_file_name(normalize(folder_name)).upper()
				display = '%02d | [B]FOLDER[/B] | [I]%s [/I]' % (count, clean_folder_name)
				url_params = {'mode': 'real_debrid.browse_rd_cloud', 'id': folder_id}
				delete_params = {'mode': 'real_debrid.delete', 'id': folder_id, 'cache_type': 'torrent'}
				cm_append(('[B]Delete Folder[/B]','RunPlugin(%s)' % build_url(delete_params)))
				url = build_url(url_params)
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt({'icon': default_rd_icon, 'poster': default_rd_icon, 'thumb': default_rd_icon, 'fanart': fanart, 'banner': default_rd_icon})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				yield (url, listitem, True)
			except: pass
	try: cloud_files = [i for i in RealDebrid.user_cloud() if i['status'] == 'downloaded']
	except: cloud_files = []
	handle = int(sys.argv[1])
	add_items(handle, list(_builder()))
	set_content(handle, 'files')
	end_directory(handle, cacheToDisc=False)
	set_view_mode('view.premium')

def rd_downloads():
	def _builder():
		for count, item in enumerate(downloads, 1):
			try:
				cm = []
				cm_append = cm.append
				datetime_object = jsondate_to_datetime(item['generated'], '%Y-%m-%dT%H:%M:%S.%fZ', remove_time=True)
				filename, size = item['filename'], float(int(item['filesize']))/1073741824
				name = clean_file_name(filename).upper()
				display = '%02d | %.2f GB | %s  | [I]%s [/I]' % (count, size, datetime_object, name)
				url_link = item['download']
				url_params = {'mode': 'playback.video', 'url': url_link, 'obj': 'video'}
				down_file_params = {'mode': 'downloader.runner', 'name': name, 'url': url_link, 'action': 'cloud.realdebrid_direct', 'image': default_rd_icon}
				delete_params = {'mode': 'real_debrid.delete', 'id': item['id'], 'cache_type': 'download'}
				cm_append(('[B]Download File[/B]','RunPlugin(%s)' % build_url(down_file_params)))
				cm_append(('[B]Delete File[/B]','RunPlugin(%s)' % build_url(delete_params)))
				url = build_url(url_params)
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt({'icon': default_rd_icon, 'poster': default_rd_icon, 'thumb': default_rd_icon, 'fanart': fanart, 'banner': default_rd_icon})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				yield (url, listitem, True)
			except: pass
	try: downloads = [i for i in RealDebrid.downloads() if i['download'].lower().endswith(tuple(extensions))]
	except: downloads = []
	handle = int(sys.argv[1])
	add_items(handle, list(_builder()))
	set_content(handle, 'files')
	end_directory(handle, cacheToDisc=False)
	set_view_mode('view.premium')

def browse_rd_cloud(folder_id):
	def _builder():
		for count, item in enumerate(pack_info, 1):
			try:
				cm = []
				name, url_link, size = item['path'], item['url_link'], float(int(item['bytes']))/1073741824
				if name.startswith('/'): name = name.split('/')[-1]
				name = clean_file_name(name).upper()
				if url_link.startswith('/'): url_link = 'http' + url_link
				display = '%02d | [B]FILE[/B] | %.2f GB | [I]%s [/I]' % (count, size, name)
				url_params = {'mode': 'real_debrid.resolve_rd', 'url': url_link, 'play': 'true'}
				url = build_url(url_params)
				down_file_params = {'mode': 'downloader.runner', 'name': name, 'url': url_link, 'action': 'cloud.realdebrid', 'image': default_rd_icon}
				cm.append(('[B]Download File[/B]','RunPlugin(%s)' % build_url(down_file_params)))
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt({'icon': default_rd_icon, 'poster': default_rd_icon, 'thumb': default_rd_icon, 'fanart': fanart, 'banner': default_rd_icon})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				yield (url, listitem, False)
			except: pass
	handle = int(sys.argv[1])
	cloud_files = RealDebrid.user_cloud_info(folder_id)
	files = [i for i in cloud_files['files'] if i['selected'] == 1 and i['path'].lower().endswith(tuple(extensions))]
	file_info = [dict(i, **{'url_link': cloud_files['links'][idx]}) for idx, i in enumerate(files)]
	pack_info = sorted(file_info, key=lambda k: k['path'])
	add_items(handle, list(_builder()))
	set_content(handle, 'files')
	end_directory(handle, cacheToDisc=False)
	set_view_mode('view.premium')

def rd_delete(file_id, cache_type):
	if not confirm_dialog(): return
	if cache_type == 'torrent': result = RealDebrid.delete_torrent(file_id)
	else: result = RealDebrid.delete_download(file_id) # cache_type: 'download'
	if result.status_code in (401, 403, 404): return notification('Error')
	RealDebrid.clear_cache()
	execute_builtin('Container.Refresh')

def resolve_rd(params):
	url = params['url']
	resolved_link = RealDebrid.unrestrict_link(url)
	if params.get('play', 'false') != 'true' : return resolved_link
	from modules.player import FenLightPlayer
	FenLightPlayer().run(resolved_link, 'video')

def rd_account_info():
	try:
		show_busy_dialog()
		account_info = RealDebrid.account_info()
		expires = datetime_workaround(account_info['expiration'], '%Y-%m-%dT%H:%M:%S.%fZ')
		days_remaining = (expires - datetime.today()).days
		body = []
		append = body.append
		append('[B]Account:[/B] %s' % account_info['email'])
		append('[B]Username:[/B] %s' % account_info['username'])
		append('[B]Status:[/B] %s' % account_info['type'].capitalize())
		append('[B]Expires:[/B] %s' % expires)
		append('[B]Days Remaining:[/B] %s' % days_remaining)
		append('[B]Fidelity Points:[/B] %s' % account_info['points'])
		hide_busy_dialog()
		return show_text('REAL DEBRID', '\n\n'.join(body), font_size='large')
	except: hide_busy_dialog()

def active_days():
	try:
		account_info = RealDebrid.account_info()
		expires = datetime_workaround(account_info['expiration'], '%Y-%m-%dT%H:%M:%S.%fZ')
		days_remaining = (expires - datetime.today()).days
	except: days_remaining = 0
	return days_remaining
