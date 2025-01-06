# -*- coding: utf-8 -*-
from datetime import datetime
from modules.utils import datetime_workaround
from apis.real_debrid_api import RealDebridAPI
from modules import kodi_utils
from modules.source_utils import supported_video_extensions, gather_assigned_content, test_assigned_content
from modules.utils import clean_file_name, normalize, jsondate_to_datetime
# logger = kodi_utils.logger

show_busy_dialog, hide_busy_dialog, show_text, set_view_mode = kodi_utils.show_busy_dialog, kodi_utils.hide_busy_dialog, kodi_utils.show_text, kodi_utils.set_view_mode
add_items, set_content, end_directory = kodi_utils.add_items, kodi_utils.set_content, kodi_utils.end_directory
default_rd_icon, fanart = kodi_utils.get_icon('realdebrid'), kodi_utils.addon_fanart
ls, sys, make_listitem, build_url = kodi_utils.local_string, kodi_utils.sys, kodi_utils.make_listitem, kodi_utils.build_url
folder_str, file_str, down_str = ls(32742).upper(), ls(32743).upper(), '[B]%s[/B]' % ls(32747)
linked_str, addlink_str, clearlink_str = ls(33074).upper(), ls(33078), ls(33079)
extensions = supported_video_extensions()
RealDebrid = RealDebridAPI()

def rd_torrent_cloud():
	def _builder():
		for count, item in enumerate(cloud_files, 1):
			try:
				cm = []
				cm_append = cm.append
				folder_name, folder_id = item['filename'], item['id']
				clean_folder_name = clean_file_name(normalize(folder_name)).upper()
				linked_folder = test_assigned_content('FEN_RD_%s' % folder_id, assigned_content)
				if linked_folder: display = '%02d | [B]%s | [COLOR limegreen]%s | %s[/B][/COLOR] | [I]%s[/I]' % (count, folder_str, linked_str, linked_folder, clean_folder_name)
				else: display = '%02d | [B]%s[/B] | [I]%s [/I]' % (count, folder_str, clean_folder_name)
				url_params = {'mode': 'real_debrid.browse_rd_cloud', 'id': folder_id}
				link_folders_add = {'mode': 'link_folders_choice', 'service': 'RD', 'folder_id': folder_id, 'action': 'add'}
				link_folders_remove = {'mode': 'link_folders_choice', 'service': 'RD', 'folder_id': folder_id, 'action': 'remove'}
				url = build_url(url_params)
				cm_append((addlink_str,'RunPlugin(%s)' % build_url(link_folders_add)))
				cm_append((clearlink_str,'RunPlugin(%s)' % build_url(link_folders_remove)))
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt({'icon': default_rd_icon, 'poster': default_rd_icon, 'thumb': default_rd_icon, 'fanart': fanart, 'banner': default_rd_icon})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				listitem.setProperty('fen.context_main_menu_params', build_url({'mode': 'menu_editor.edit_menu_external', 'name': clean_folder_name, 'iconImage': default_rd_icon,
									'service': 'RD'}))
				yield (url, listitem, True)
			except: pass
	try: cloud_files = [i for i in RealDebrid.user_cloud() if i['status'] == 'downloaded']
	except: cloud_files = []
	if cloud_files: assigned_content = gather_assigned_content("'FEN_RD_%'")
	handle = int(sys.argv[1])
	add_items(handle, list(_builder()))
	set_content(handle, 'files')
	end_directory(handle, False)
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
				down_file_params = {'mode': 'downloader', 'name': name, 'url': url_link, 'action': 'cloud.realdebrid_direct', 'image': default_rd_icon}
				cm_append((down_str,'RunPlugin(%s)' % build_url(down_file_params)))
				url = build_url(url_params)
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt({'icon': default_rd_icon, 'poster': default_rd_icon, 'thumb': default_rd_icon, 'fanart': fanart, 'banner': default_rd_icon})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				listitem.setProperty('fen.context_main_menu_params', build_url({'mode': 'menu_editor.edit_menu_external', 'name': name, 'iconImage': default_rd_icon,
									'action': 'cloud.realdebrid_direct'}))
				yield (url, listitem, True)
			except: pass
	try: downloads = [i for i in RealDebrid.downloads() if i['download'].lower().endswith(tuple(extensions))]
	except: downloads = []
	handle = int(sys.argv[1])
	add_items(handle, list(_builder()))
	set_content(handle, 'files')
	end_directory(handle, False)
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
				display = '%02d | [B]%s[/B] | %.2f GB | [I]%s [/I]' % (count, file_str, size, name)
				url_params = {'mode': 'real_debrid.resolve_rd', 'url': url_link, 'play': 'true'}
				url = build_url(url_params)
				down_file_params = {'mode': 'downloader', 'name': name, 'url': url_link, 'action': 'cloud.realdebrid', 'image': default_rd_icon}
				cm.append((down_str,'RunPlugin(%s)' % build_url(down_file_params)))
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt({'icon': default_rd_icon, 'poster': default_rd_icon, 'thumb': default_rd_icon, 'fanart': fanart, 'banner': default_rd_icon})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				listitem.setProperty('fen.context_main_menu_params', build_url({'mode': 'menu_editor.edit_menu_external', 'name': name, 'iconImage': default_rd_icon,
									'action': 'cloud.realdebrid'}))
				yield (url, listitem, False)
			except: pass
	handle = int(sys.argv[1])
	torrent_files = RealDebrid.user_cloud_info(folder_id)
	files = [i for i in torrent_files['files'] if i['selected'] == 1 and i['path'].lower().endswith(tuple(extensions))]
	file_info = [dict(i, **{'url_link': torrent_files['links'][idx]}) for idx, i in enumerate(files)]
	pack_info = sorted(file_info, key=lambda k: k['path'])
	add_items(handle, list(_builder()))
	set_content(handle, 'files')
	end_directory(handle, False)
	set_view_mode('view.premium')

def resolve_rd(params):
	url = params['url']
	resolved_link = RealDebrid.unrestrict_link(url)
	if params.get('play', 'false') != 'true' : return resolved_link
	from modules.player import FenPlayer
	FenPlayer().run(resolved_link, 'video')

def rd_account_info():
	try:
		show_busy_dialog()
		account_info = RealDebrid.account_info()
		expires = datetime_workaround(account_info['expiration'], '%Y-%m-%dT%H:%M:%S.%fZ')
		days_remaining = (expires - datetime.today()).days
		body = []
		append = body.append
		append(ls(32758) % account_info['email'])
		append(ls(32755) % account_info['username'])
		append(ls(32757) % account_info['type'].capitalize())
		append(ls(32750) % expires)
		append(ls(32751) % days_remaining)
		append(ls(32759) % account_info['points'])
		hide_busy_dialog()
		return show_text(ls(32054).upper(), '\n\n'.join(body), font_size='large')
	except: hide_busy_dialog()

def active_days():
	try:
		account_info = RealDebrid.account_info()
		expires = datetime_workaround(account_info['expiration'], '%Y-%m-%dT%H:%M:%S.%fZ')
		days_remaining = (expires - datetime.today()).days
	except: days_remaining = 0
	return days_remaining
