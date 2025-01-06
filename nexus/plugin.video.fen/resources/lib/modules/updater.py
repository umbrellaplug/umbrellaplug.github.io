# -*- coding: utf-8 -*-
import shutil
import time
import sqlite3 as database
from zipfile import ZipFile
from modules import kodi_utils 
# logger = kodi_utils.logger

requests, addon_info, unzip, confirm_dialog, ok_dialog = kodi_utils.requests, kodi_utils.addon_info, kodi_utils.unzip, kodi_utils.confirm_dialog, kodi_utils.ok_dialog
translate_path, osPath, delete_file, execute_builtin = kodi_utils.translate_path, kodi_utils.osPath, kodi_utils.delete_file, kodi_utils.execute_builtin
update_local_addons, disable_enable_addon, close_all_dialog = kodi_utils.update_local_addons, kodi_utils.disable_enable_addon, kodi_utils.close_all_dialog
update_kodi_addons_db, notification, ls = kodi_utils.update_kodi_addons_db, kodi_utils.notification, kodi_utils.local_string

packages_dir = translate_path('special://home/addons/packages/')
home_addons_dir = translate_path('special://home/addons/')
destination_check = translate_path('special://home/addons/plugin.video.fen/')

def get_versions():
	result = requests.get('https://github.com/Tikipeter/tikipeter.github.io/raw/main/packages/fen_version')
	if result.status_code != 200: return
	online_version = result.text.replace('\n', '')
	current_version = addon_info('version')
	return current_version, online_version

def update_check(action=4):
	if action == 3: return
	current_version, online_version = get_versions()
	line = ls(33177) % (current_version, online_version)
	if current_version == online_version:
		if action == 4: return ok_dialog(heading=33176, text=line + ls(33178))
		return
	if action in (0, 4):
		if not confirm_dialog(heading=33176, text=line + ls(33179)): return
	if action == 1: notification(33181)
	if action == 2: return notification(33182)
	return update_addon(online_version, action)

def update_addon(new_version, action):
	close_all_dialog()
	execute_builtin('ActivateWindow(Home)', True)
	zip_name = 'plugin.video.fen-%s.zip' % new_version
	url = 'https://github.com/Tikipeter/tikipeter.github.io/raw/main/packages/%s' % zip_name
	result = requests.get(url, stream=True)
	if result.status_code != 200: return ok_dialog(heading=33176, text=33183)
	zip_location = osPath.join(packages_dir, zip_name)
	with open(zip_location, 'wb') as f: shutil.copyfileobj(result.raw, f)
	shutil.rmtree(osPath.join(home_addons_dir, 'plugin.video.fen'))
	success = unzip(zip_location, home_addons_dir, destination_check)
	delete_file(zip_location)
	if not success: return ok_dialog(heading=33176, text=33183)
	if action in (0, 4): ok_dialog(heading=33176, text=ls(33184) % new_version)
	update_local_addons()
	disable_enable_addon()
	update_kodi_addons_db()