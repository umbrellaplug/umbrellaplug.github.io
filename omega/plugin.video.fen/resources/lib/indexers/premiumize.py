# -*- coding: utf-8 -*-
import re
import math
from datetime import datetime
from apis.premiumize_api import PremiumizeAPI
from modules import kodi_utils
from modules.source_utils import supported_video_extensions
from modules.utils import clean_file_name, normalize
# logger = kodi_utils.logger

json, make_listitem, build_url, ls, sys = kodi_utils.json, kodi_utils.make_listitem, kodi_utils.build_url, kodi_utils.local_string, kodi_utils.sys
add_items, set_content, end_directory = kodi_utils.add_items, kodi_utils.set_content, kodi_utils.end_directory
show_busy_dialog, hide_busy_dialog, show_text, set_view_mode = kodi_utils.show_busy_dialog, kodi_utils.hide_busy_dialog, kodi_utils.show_text, kodi_utils.set_view_mode
confirm_dialog, ok_dialog, kodi_refresh, dialog = kodi_utils.confirm_dialog, kodi_utils.ok_dialog, kodi_utils.kodi_refresh, kodi_utils.dialog
default_pm_icon, fanart = kodi_utils.get_icon('premiumize'), kodi_utils.addon_fanart
folder_str, file_str, down_str = ls(32742).upper(), ls(32743).upper(), '[B]%s[/B]' % ls(32747)
extensions = supported_video_extensions()
Premiumize = PremiumizeAPI()

def pm_torrent_cloud(folder_id=None, folder_name=None):
	def _builder():
		for count, item in enumerate(cloud_files, 1):
			try:
				cm = []
				cm_append = cm.append
				file_type = item['type']
				name = clean_file_name(item['name']).upper()
				listitem = make_listitem()
				if file_type == 'folder':
					is_folder = True
					display = '%02d | [B]%s[/B] | [I]%s [/I]' % (count, folder_str, name)
					url_params = {'mode': 'premiumize.pm_torrent_cloud', 'id': item['id'], 'folder_name': normalize(item['name']), 'name': item['name']}
				else:
					is_folder = False
					url_link, size = item['link'], item['size']
					if url_link.startswith('/'): url_link = 'https' + url_link
					display_size = float(int(size))/1073741824
					display = '%02d | [B]%s[/B] | %.2f GB | [I]%s [/I]' % (count, file_str, display_size, name)
					url_params = {'mode': 'playback.video', 'url': url_link, 'obj': 'video'}
					down_file_params = {'mode': 'downloader', 'name': item['name'], 'url': url_link, 'action': 'cloud.premiumize', 'image': default_pm_icon}
					cm_append((down_str, 'RunPlugin(%s)' % build_url(down_file_params)))
					listitem.setProperty('fen.context_main_menu_params', build_url({'mode': 'menu_editor.edit_menu_external', 'name': name, 'iconImage': default_pm_icon,
										'action': 'cloud.premiumize'}))
				url = build_url(url_params)
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt({'icon': default_pm_icon, 'poster': default_pm_icon, 'thumb': default_pm_icon, 'fanart': fanart, 'banner': default_pm_icon})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				yield (url, listitem, is_folder)
			except: pass
	try:
		cloud_files = Premiumize.user_cloud(folder_id)['content']
		cloud_files = [i for i in cloud_files if ('link' in i and i['link'].lower().endswith(tuple(extensions))) or i['type'] == 'folder']
		cloud_files.sort(key=lambda k: k['name'])
		cloud_files.sort(key=lambda k: k['type'], reverse=True)
	except: cloud_files = []
	handle = int(sys.argv[1])
	add_items(handle, list(_builder()))
	set_content(handle, 'files')
	end_directory(handle, False)
	set_view_mode('view.premium')

def pm_transfers():
	def _builder():
		for count, item in enumerate(transfer_files, 1):
			try:
				cm = []
				file_id, status, progress, name = item['file_id'], item['status'], item['progress'], clean_file_name(item['name']).upper()
				file_type = 'folder' if file_id is None else 'file'
				if status == 'finished': progress = 100
				else:
					try: progress = re.findall(r'\.{0,1}(\d+)', str(progress))[0][:2]
					except: progress = ''
				if file_type == 'folder':
					is_folder = True if status == 'finished' else False
					display = '%02d | %s%% | [B]%s[/B] | [I]%s [/I]' % (count, str(progress), folder_str, name)
					url_params = {'mode': 'premiumize.pm_torrent_cloud', 'id': item['folder_id'], 'folder_name': normalize(item['name'])}
				else:
					is_folder = False
					details = Premiumize.get_item_details(file_id)
					url_link, size = details['link'], details['size']
					if url_link.startswith('/'): url_link = 'https' + url_link
					display_size = float(int(size))/1073741824
					display = '%02d | %s%% | [B]%s[/B] | %.2f GB | [I]%s [/I]' % (count, str(progress), file_str, display_size, name)
					url_params = {'mode': 'playback.video', 'url': url_link, 'obj': 'video'}
					down_file_params = {'mode': 'downloader', 'name': item['name'], 'url': url_link, 'media_type': 'cloud.premiumize', 'image': default_pm_icon}
					cm.append((down_str,'RunPlugin(%s)' % build_url(down_file_params)))
				url = build_url(url_params)
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt({'icon': default_pm_icon, 'poster': default_pm_icon, 'thumb': default_pm_icon, 'fanart': fanart, 'banner': default_pm_icon})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				yield (url, listitem, is_folder)
			except: pass
	try: transfer_files = Premiumize.transfers_list()['transfers']
	except: transfer_files = []
	handle = int(sys.argv[1])
	add_items(handle, list(_builder()))
	set_content(handle, 'files')
	end_directory(handle, False)
	set_view_mode('view.premium')

def pm_account_info():
	try:
		show_busy_dialog()
		account_info = Premiumize.account_info()
		customer_id = account_info['customer_id']
		expires = datetime.fromtimestamp(account_info['premium_until'])
		days_remaining = (expires - datetime.today()).days
		points_used = int(math.floor(float(account_info['space_used']) / 1073741824.0))
		space_used = float(int(account_info['space_used']))/1073741824
		percentage_used = str(round(float(account_info['limit_used']) * 100.0, 1))
		body = []
		append = body.append
		append(ls(32749) % customer_id)
		append(ls(32750) % expires)
		append(ls(32751) % days_remaining)
		append(ls(32752) % points_used)
		append(ls(32753) % space_used)
		append(ls(32754) % (percentage_used + '%'))
		hide_busy_dialog()
		return show_text(ls(32061).upper(), '\n\n'.join(body), font_size='large')
	except: hide_busy_dialog()


def active_days():
	try:
		account_info = Premiumize.account_info()
		expires = datetime.fromtimestamp(account_info['premium_until'])
		days_remaining = (expires - datetime.today()).days
	except: days_remaining = 0
	return days_remaining