# -*- coding: utf-8 -*-
# Thanks to kodifitzwell for allowing me to borrow his code
import sys
from apis.offcloud_api import OffcloudAPI
from modules import kodi_utils
from modules.source_utils import supported_video_extensions
from modules.utils import clean_file_name, normalize
# logger = kodi_utils.logger

make_listitem, build_url, show_busy_dialog, hide_busy_dialog = kodi_utils.make_listitem, kodi_utils.build_url, kodi_utils.show_busy_dialog, kodi_utils.hide_busy_dialog
show_text, confirm_dialog, notification, execute_builtin = kodi_utils.show_text, kodi_utils.confirm_dialog, kodi_utils.notification, kodi_utils.execute_builtin
add_items, set_content, end_directory, set_view_mode = kodi_utils.add_items, kodi_utils.set_content, kodi_utils.end_directory, kodi_utils.set_view_mode
default_oc_icon, fanart = kodi_utils.get_icon('offcloud'), kodi_utils.get_addon_fanart()
extensions = supported_video_extensions()
Offcloud = OffcloudAPI()

def oc_cloud():
	def _builder():
		for count, item in enumerate(folders, 1):
			try:
				cm = []
				cm_append = cm.append
				is_folder = item['isDirectory']
				request_id, folder_name, server = item['requestId'], item['fileName'], item['server']
				delete_params = {'mode': 'offcloud.delete', 'folder_id': request_id}
				if is_folder:
					display = '%02d | [B]FOLDER[/B] | [I]%s [/I]' % (count, clean_file_name(normalize(folder_name)).upper())
					url_params = {'mode': 'offcloud.browse_oc_cloud', 'folder_id': request_id}
					cm_append(('[B]Delete Folder[/B]', 'RunPlugin(%s)' % build_url(delete_params)))
				else:
					display = '%02d | [B]File[/B] | [I]%s [/I]' % (count, clean_file_name(normalize(folder_name)).upper())
					link = Offcloud.requote_uri(Offcloud.build_url(server, request_id, folder_name))
					url_params = {'mode': 'offcloud.resolve_oc', 'url': link, 'play': 'true'}
					down_file_params = {'mode': 'downloader', 'action': 'cloud.offcloud_direct', 'name': folder_name, 'url': link, 'image': default_oc_icon}
					cm_append(('[B][B]Delete File[/B][/B]', 'RunPlugin(%s)' % build_url(delete_params)))
					cm.append(('[B]Download File[/B]','RunPlugin(%s)' % build_url(down_file_params)))
				url = build_url(url_params)
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt({'icon': default_oc_icon, 'poster': default_oc_icon, 'thumb': default_oc_icon, 'fanart': fanart, 'banner': default_oc_icon})
				yield (url, listitem, is_folder)
			except: pass
	cloud_folders = Offcloud.user_cloud()
	folders = [i for i in cloud_folders if i['status'] == 'downloaded']
	handle = int(sys.argv[1])
	add_items(handle, list(_builder()))
	set_content(handle, 'files')
	end_directory(handle)
	set_view_mode('view.premium')

def browse_oc_cloud(folder_id):
	def _builder():
		for count, item in enumerate(video_files, 1):
			try:
				cm = []
				name = item.split('/')[-1]
				name = clean_file_name(name).upper()
				link = Offcloud.requote_uri(item)
				display = '%02d | [B]FILE[/B] | [I]%s [/I]' % (count, name)
				url_params = {'mode': 'offcloud.resolve_oc', 'url': link, 'play': 'true'}
				url = build_url(url_params)
				down_file_params = {'mode': 'downloader', 'action': 'cloud.offcloud_direct', 'name': name, 'url': link, 'image': default_oc_icon}
				cm.append(('[B]Download File[/B]','RunPlugin(%s)' % build_url(down_file_params)))
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt({'icon': default_oc_icon, 'poster': default_oc_icon, 'thumb': default_oc_icon, 'fanart': fanart, 'banner': default_oc_icon})
				listitem.setInfo('video', {})
				yield (url, listitem, False)
			except: pass
	torrent_files = Offcloud.user_cloud_info(folder_id)
	video_files = [i for i in torrent_files if i.lower().endswith(tuple(extensions))]
	handle = int(sys.argv[1])
	add_items(handle, list(_builder()))
	set_content(handle, 'files')
	end_directory(handle)
	set_view_mode('view.premium')

def oc_delete(folder_id):
	if not confirm_dialog(): return
	result = Offcloud.delete_torrent(folder_id)
	if 'success' not in result: return notification('Error')
	Offcloud.clear_cache()
	execute_builtin('Container.Refresh')

def resolve_oc(params):
	url = params['url']
	if params.get('play', 'false') != 'true' : return url
	from modules.player import FenLightPlayer
	FenLightPlayer().run(url, 'video')

def oc_account_info():
	try:
		show_busy_dialog()
		account_info = Offcloud.account_info()
		body = []
		append = body.append
		append('[B]Email[/B]: %s' % account_info['email'])
		append('[B]User ID[/B]: %s' % account_info['userId'])
		append('[B]Premium[/B]: %s' % account_info['isPremium'])
		append('[B]Expires[/B]: %s' % account_info['expirationDate'])
		append('[B]Cloud Limit[/B]: {:,}'.format(account_info['limits']['cloud']))
		hide_busy_dialog()
		return show_text('OFFCLOUD', '\n\n'.join(body), font_size='large')
	except: hide_busy_dialog()

