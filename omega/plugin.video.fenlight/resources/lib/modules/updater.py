# -*- coding: utf-8 -*-
import json
import requests
import shutil
import time
import sqlite3 as database
from zipfile import ZipFile
from caches.settings_cache import get_setting, set_setting
from modules.utils import string_alphanum_to_num, unzip
from modules import kodi_utils 
# logger = kodi_utils.logger

translate_path, osPath, delete_file, execute_builtin, get_icon = kodi_utils.translate_path, kodi_utils.osPath, kodi_utils.delete_file, kodi_utils.execute_builtin, kodi_utils.get_icon
update_kodi_addons_db, notification, show_text, confirm_dialog = kodi_utils.update_kodi_addons_db, kodi_utils.notification, kodi_utils.show_text, kodi_utils.confirm_dialog
addon_version, confirm_dialog, ok_dialog = kodi_utils.addon_version, kodi_utils.confirm_dialog, kodi_utils.ok_dialog
update_local_addons, disable_enable_addon, close_all_dialog = kodi_utils.update_local_addons, kodi_utils.disable_enable_addon, kodi_utils.close_all_dialog
select_dialog, show_busy_dialog, hide_busy_dialog = kodi_utils.select_dialog, kodi_utils.show_busy_dialog, kodi_utils.hide_busy_dialog

packages_dir = translate_path('special://home/addons/packages/')
home_addons_dir = translate_path('special://home/addons/')
destination_check = translate_path('special://home/addons/plugin.video.fenlight/')
changelog_location = translate_path('special://home/addons/plugin.video.fenlight/resources/text/changelog.txt')
downloads_icon = get_icon('downloads')
addon_dir = 'plugin.video.fenlight'
zipfile_name = 'plugin.video.fenlight-%s.zip'
heading_str = 'Fen Light Updater'
error_str = 'Error'
notification_occuring_str = 'Fen Light Update Occuring'
notification_available_str = 'Fen Light Update Available'
notification_updating_str = 'Fen Light Performing Update'
notification_rollback_str = 'Fen Light Performing Rollback'
result_str = 'Installed Version: [B]%s[/B][CR]Online Version: [B]%s[/B][CR][CR] %s'
no_update_str = '[B]No Update Available[/B]'
update_available_str = '[B]An Update is Available[/B][CR]Perform Update?'
continue_confirm_str = 'Continue with Update After Viewing Changes?'
success_str = '[CR]Success.[CR]Fen Light updated to version [B]%s[/B]'
rollback_heading_str = 'Choose Rollback Version'
success_rollback_str = '[CR]Success.[CR]Fen Light rolled back to version [B]%s[/B]'
confirm_rollback_str = 'Are you sure?[CR]Version [B]%s[/B] will overwrite your current installed version.' \
						'[CR]Fen Light will set your update action to [B]OFF[/B] if rollback is successful'
no_rollback_str = 'No previous versions found.[CR]Please install rollback manually'
error_update_str = 'Error Updating.[CR]Please install new update manually'
error_rollback_str = 'Error rolling back.[CR]Please install rollback manually'
changes_heading_str = 'New Online Release (v.%s) Changelog'
view_changes_str = 'Do you want to view the changelog for the new release before installing?'
no_changes_str = 'You are running the current version of Fen Light.[CR][CR]There is no new version changelog to view.'

def get_location(insert=''):
	return 'https://github.com/%s/%s/raw/main/packages/%s' % (get_setting('fenlight.update.username'), get_setting('update.location'), insert)

def get_versions():
	try:
		result = requests.get(get_location('fen_light_version'))
		if result.status_code != 200: return None, None
		online_version = result.text.replace('\n', '')
		current_version = addon_version()
		return current_version, online_version
	except: return None, None

def get_changes(online_version=None):
	try:
		if not online_version:
			current_version, online_version = get_versions()
			if not version_check(current_version, online_version): return ok_dialog(heading=heading_str, text=no_changes_str)
		show_busy_dialog()
		result = requests.get(get_location('fen_light_changes'))
		hide_busy_dialog()
		if result.status_code != 200: return notification(error_str, icon=downloads_icon)
		changes = result.text
		return show_text(changes_heading_str % online_version, text=changes, font_size='large')
	except:
		hide_busy_dialog()
		return notification(error_str, icon=downloads_icon)

def version_check(current_version, online_version):
	return string_alphanum_to_num(current_version) != string_alphanum_to_num(online_version)

def update_check(action=4):
	if action == 3: return
	current_version, online_version = get_versions()
	if not current_version: return
	if not version_check(current_version, online_version):
		if action == 4: return ok_dialog(heading=heading_str, text=result_str % (current_version, online_version, no_update_str))
		return
	if action in (0, 4):
		if not confirm_dialog(heading=heading_str, text=result_str % (current_version, online_version, update_available_str), ok_label='Yes', cancel_label='No'): return
		if confirm_dialog(heading=heading_str, text=view_changes_str, ok_label='Yes', cancel_label='No'):
			get_changes(online_version)
			if not confirm_dialog(heading=heading_str, text=continue_confirm_str, ok_label='Yes', cancel_label='No'): return
	if action == 1: notification(notification_occuring_str, icon=downloads_icon)
	elif action == 2: return notification(notification_available_str, icon=downloads_icon)
	return update_addon(online_version, action)

def rollback_check():
	current_version = get_versions()[0]
	url = 'https://api.github.com/repos/%s/%s/contents/packages' % ('Tikipeter', 'tikipeter.github.io')#(get_setting('update.username'), get_setting('update.location'))
	show_busy_dialog()
	results = requests.get(url)
	hide_busy_dialog()
	if results.status_code != 200: return ok_dialog(heading=heading_str, text=error_rollback_str)
	results = [i['name'].split('-')[1].replace('.zip', '') for i in results.json() if 'plugin.video.fenlight' in i['name'] \
				and not i['name'].split('-')[1].replace('.zip', '') == current_version]
	if not results: return ok_dialog(heading=heading_str, text=no_rollback_str)
	results.sort(reverse=True)
	list_items = [{'line1': item, 'icon': downloads_icon} for item in results]
	kwargs = {'items': json.dumps(list_items), 'heading': rollback_heading_str}
	rollback_version = select_dialog(results, **kwargs)
	if rollback_version == None: return
	if not confirm_dialog(heading=heading_str, text=confirm_rollback_str % rollback_version): return
	update_addon(rollback_version, 5)

def update_addon(new_version, action):
	close_all_dialog()
	execute_builtin('ActivateWindow(Home)', True)
	notification_str = notification_rollback_str if action == 5 else notification_updating_str
	notification(notification_str, icon=downloads_icon)
	zip_name = zipfile_name % new_version
	url = get_location('%s') % zip_name
	show_busy_dialog()
	result = requests.get(url, stream=True)
	hide_busy_dialog()
	if result.status_code != 200: return ok_dialog(heading=heading_str, text=error_update_str)
	zip_location = osPath.join(packages_dir, zip_name)
	with open(zip_location, 'wb') as f: shutil.copyfileobj(result.raw, f)
	shutil.rmtree(osPath.join(home_addons_dir, addon_dir))
	success = unzip(zip_location, home_addons_dir, destination_check)
	delete_file(zip_location)
	if not success: return ok_dialog(heading=heading_str, text=error_update_str)
	if action == 5:
		set_setting('update.action', '3')
		ok_dialog(heading=heading_str, text=success_rollback_str % new_version)
	elif action in (0, 4) and confirm_dialog(heading=heading_str, text=success_str % new_version, ok_label='Changelog', cancel_label='Exit', default_control=10) != False:
			show_text('Changelog', file=changelog_location, font_size='large')
	update_local_addons()
	disable_enable_addon()
	update_kodi_addons_db()
