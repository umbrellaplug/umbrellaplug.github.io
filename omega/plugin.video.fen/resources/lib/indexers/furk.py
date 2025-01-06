# -*- coding: utf-8 -*-
from apis.furk_api import FurkAPI
from modules import kodi_utils
from modules.utils import clean_file_name
# logger = kodi_utils.logger

add_items, set_content, show_text, unquote = kodi_utils.add_items, kodi_utils.set_content, kodi_utils.show_text, kodi_utils.unquote
show_busy_dialog, hide_busy_dialog, set_view_mode, end_directory = kodi_utils.show_busy_dialog, kodi_utils.hide_busy_dialog, kodi_utils.set_view_mode, kodi_utils.end_directory
confirm_dialog, notification, kodi_refresh = kodi_utils.confirm_dialog, kodi_utils.notification, kodi_utils.kodi_refresh
ls, sys, build_url, make_listitem = kodi_utils.local_string, kodi_utils.sys, kodi_utils.build_url, kodi_utils.make_listitem
furk_icon, fanart = kodi_utils.get_icon('furk'), kodi_utils.addon_fanart
remove_str, prot_str, unprot_str, speed_str, files_str = ls(32766), ls(32767), ls(32768), ls(32775), ls(32493).upper()
down_str, add_str = '[B]%s[/B]' % ls(32747), '[B]%s[/B]' % ls(32769)
Furk = FurkAPI()

def search_furk(params):
	handle = int(sys.argv[1])
	query = clean_file_name(unquote(params.get('query')))
	try:
		search_method = 'search' if 'accurate_search' in params else 'direct_search'
		files = Furk.direct_search(query) if search_method == 'direct_search' else Furk.search(query)
		files = [i for i in files if int(i.get('files_num_video', '0')) > 0 and 'url_dl' in i]
		furk_folder_browser(files, 'search', handle)
	except: pass
	set_content(handle, 'files')
	end_directory(handle, False)
	set_view_mode('view.premium')

def my_furk_files(params):
	handle = int(sys.argv[1])
	try:
		files = Furk.file_get_video()
		furk_folder_browser(files, 'file_browse', handle)
	except: pass
	set_content(handle, 'files')
	end_directory(handle)
	set_view_mode('view.premium')

def furk_folder_browser(files, display_mode, handle):
	def _builder():
		for count, item in enumerate(files, 1):
			try:
				item_get = item.get
				cm = []
				cm_append = cm.append
				name, size, info_hash = clean_file_name(item_get('name')).upper(), item_get('size'), item_get('info_hash')
				item_id, url_dl, files_num_video, is_protected = item_get('id'), item_get('url_dl'), item_get('files_num_video'), item_get('is_protected')
				try: thumb = [i for i in item_get('ss_urls', []) if i][0]
				except: thumb = furk_icon
				display_size = str(round(float(size)/1048576000, 1))
				duration = int(int(item['duration'])/60.0)
				header, footer = ('[COLOR=green]', '[/COLOR]') if is_protected == '1' else ('', '')
				display = '%02d %s| [B]%sGB | %s %s | %sMINS | %s[/B][I]%s[/I]' % (count, header, display_size, files_num_video, files_str, duration, footer, name)
				download_archive = build_url({'mode': 'downloader', 'name': name, 'url': url_dl, 'action': 'archive', 'image': furk_icon})
				add_to_files = build_url({'mode': 'furk.add_to_files', 'item_id': item_id})
				remove_files = build_url({'mode': 'furk.remove_from_files', 'item_id': item_id})
				url = build_url({'mode': 'furk.furk_t_file_browser', 'name': name, 'url': url_dl, 'item_id': item_id})
				cm_append((down_str, 'RunPlugin(%s)' % download_archive))
				if display_mode == 'search': cm_append((add_str,'RunPlugin(%s)' % add_to_files))
				else: cm_append((remove_str, 'RunPlugin(%s)' % remove_files))
				if is_protected == '0':
					cm_append((prot_str, 'RunPlugin(%s)' % build_url({'mode': 'furk.myfiles_protect_unprotect', 'action': 'protect', 'name': name, 'item_id': item_id})))
				elif is_protected == '1':
					cm_append((unprot_str, 'RunPlugin(%s)' % build_url({'mode': 'furk.myfiles_protect_unprotect', 'action': 'unprotect', 'name': name, 'item_id': item_id})))
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt({'icon': thumb, 'poster': thumb, 'thumb': thumb, 'fanart': fanart, 'banner': furk_icon})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				listitem.setProperty('fen.context_main_menu_params', build_url({'mode': 'menu_editor.edit_menu_external', 'name': name, 'iconImage': furk_icon,
									'action': 'archive', 'display_mode': display_mode, 'is_protected': is_protected}))
				yield (url, listitem, True)
			except: pass
	add_items(handle, list(_builder()))

def furk_t_file_browser(params):
	def _builder():
		for count, item in enumerate(t_files, 1):
			try:
				cm = []
				url_params = {'mode': 'playback.video', 'url': item['url_dl'], 'obj': 'video'}
				url = build_url(url_params)
				name = clean_file_name(item['name']).upper()
				width = int(item.get('width', 0))
				if width > 1920: display_res = '4K'
				elif 1280 < width <= 1920: display_res = '1080P'
				elif 720 < width <= 1280: display_res = '720P'
				else: display_res = 'SD'
				display_name = '%02d | [B]%s[/B] | [B]%.2fGB | %sMINS | [/B][I]%s[/I]' % (count, display_res, float(item['size'])/1048576000, int(int(item['length'])/60.0), name)
				listitem = make_listitem()
				listitem.setLabel(display_name)
				down_file_params = {'mode': 'downloader', 'name': item['name'], 'url': item['url_dl'], 'action': 'cloud.furk_direct', 'image': furk_icon}
				cm.append((down_str, 'RunPlugin(%s)' % build_url(down_file_params)))
				listitem.addContextMenuItems(cm)
				listitem.setArt({'icon': furk_icon, 'poster': furk_icon, 'thumb': furk_icon, 'fanart': fanart, 'banner': furk_icon})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				listitem.setProperty('fen.context_main_menu_params', build_url({'mode': 'menu_editor.edit_menu_external', 'name': name, 'iconImage': furk_icon,
									'action': 'cloud.furk_direct'}))
				yield (url, listitem, False)
			except: pass
	handle = int(sys.argv[1])
	t_files = [i for i in Furk.t_files(params.get('item_id')) if 'video' in i['ct'] and 'bitrate' in i]
	add_items(handle, list(_builder()))
	set_content(handle, 'files')
	end_directory(handle, False)
	set_view_mode('view.premium')

def add_to_files(item_id):
	if not confirm_dialog(text=32580): return
	response = Furk.file_link(item_id)
	if Furk.check_status(response): notification(32576, 3500)
	else: notification(32574, 3500)
	return (None, None)

def remove_from_files(item_id):
	if not confirm_dialog(): return
	response = Furk.file_unlink(item_id)
	if Furk.check_status(response):
		notification(32576, 3500)
		kodi_refresh()
	else: notification(32574, 3500)
	return (None, None)

def myfiles_protect_unprotect(action, name, item_id):
	is_protected = '1' if action == 'protect' else '0'
	try:
		response = Furk.file_protect(item_id, is_protected)
		if Furk.check_status(response):
			kodi_refresh()
			return notification(32576)
		else: notification(32574)
	except: return

def resolve_furk(item_id, media_type, season, episode):
	from modules.source_utils import seas_ep_filter
	from modules.utils import clean_title, normalize
	url = None
	t_files = [i for i in Furk.t_files(item_id) if 'video' in i['ct'] and not any(x in i['name'].lower() for x in ('furk320', 'sample'))]
	if media_type == 'movie':
		try: url = [i['url_dl'] for i in t_files if 'is_largest' in i][0]
		except: pass
	else:
		try: url = [i['url_dl'] for i in t_files if seas_ep_filter(season, episode, normalize(i['name']))][0]
		except: pass
	return url

def account_info(params):
	try:
		show_busy_dialog()
		accinfo = Furk.account_info()
		account_type = accinfo['premium']['name']
		month_time_left = float(accinfo['premium']['bw_month_time_left'])/60/60/24
		try: total_time_left = float(accinfo['premium']['time_left'])/60/60/24
		except: total_time_left = ''
		try: renewal_date = accinfo['premium']['to_dt']
		except: renewal_date = ''
		try: is_not_last_month = accinfo['premium']['is_not_last_month']
		except: is_not_last_month = ''
		try: bw_used_month = float(accinfo['premium']['bw_used_month'])/1073741824
		except: bw_used_month = ''
		try: bw_limit_month = float(accinfo['premium']['bw_limit_month'])/1073741824
		except: bw_limit_month = ''
		try: rem_bw_limit_month = bw_limit_month - bw_used_month
		except: rem_bw_limit_month = ''
		heading = ls(32069).upper()
		body = []
		append = body.append
		append(ls(32758) % account_type.upper())
		append(ls(32770) % str(round(bw_limit_month, 0)))
		append(ls(32771))
		append('        - %s' % ls(32751) % str(round(month_time_left, 2)))
		append('        - %s GB' % ls(32761) % str(round(bw_used_month, 2)))
		append('        - %s GB' % ls(32762) % str(round(rem_bw_limit_month, 2)))
		if not account_type == 'LIFETIME':
			append(ls(32772))
			append('[B]        - %s' % ls(32751) % str(round(total_time_left, 0)))
			if is_not_last_month == '1': append('        - %s' % ls(32773) % renewal_date)
			else: append('        - %s' % ls(32774) % renewal_date)
		hide_busy_dialog()
		return show_text(heading, '\n\n'.join(body), font_size='large')
	except: hide_busy_dialog()

def active_days():
	try:
		accinfo = Furk.account_info()
		days_remaining = int(accinfo['premium']['time_left'])/60/60/24
	except: days_remaining = 0
	return days_remaining
