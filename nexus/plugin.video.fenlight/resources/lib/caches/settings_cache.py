# -*- coding: utf-8 -*-
import json
from modules import kodi_utils
from caches.base_cache import connect_database
# logger = kodi_utils.logger

numeric_input = kodi_utils.numeric_input
kodi_dialog, ok_dialog, select_dialog, confirm_dialog = kodi_utils.kodi_dialog, kodi_utils.ok_dialog, kodi_utils.select_dialog, kodi_utils.confirm_dialog
default_addon_fanart, get_property, set_property, notification = kodi_utils.addon_fanart(), kodi_utils.get_property, kodi_utils.set_property, kodi_utils.notification
tmdb_default_api, trakt_default_id, trakt_default_secret = kodi_utils.tmdb_default_api, kodi_utils.trakt_default_id, kodi_utils.trakt_default_secret
boolean_dict = {'true': 'false', 'false': 'true'}

BASE_GET = 'SELECT setting_value from settings WHERE setting_id = ?'
GET_MANY = 'SELECT setting_id, setting_value FROM settings WHERE setting_id in (%s)'
GET_ALL = 'SELECT setting_id, setting_value FROM settings'
BASE_SET = 'INSERT OR REPLACE INTO settings VALUES (?, ?, ?, ?)'
BASE_DELETE = 'DELETE FROM settings WHERE setting_id = ?'
CLEAR_SETTINGS = 'DELETE FROM settings'

class SettingsCache:
	def get(self, setting_id):
		try:
			dbcon = connect_database('settings_db')
			setting_id = setting_id.replace('fenlight.', '')
			setting_value = dbcon.execute(BASE_GET, (setting_id,)).fetchone()[0]
			self.set_memory_cache(setting_id, setting_value)
		except: setting_value = None
		return setting_value

	def remove_setting(self, setting_id):
		dbcon = connect_database('settings_db')
		dbcon.execute(BASE_DELETE, (setting_id,))

	def get_many(self, settings_list):
		try:
			dbcon = connect_database('settings_db')
			results = dict(dbcon.execute(GET_MANY % (', '.join('?' for _ in settings_list)), settings_list).fetchall())
			return results
		except: results = {}
		return results

	def get_all(self):
		dbcon = connect_database('settings_db')
		try: all_settings = dict(dbcon.execute(GET_ALL).fetchall())
		except: all_settings = {}
		return all_settings

	def set(self, setting_id, setting_value=None):
		dbcon = connect_database('settings_db')
		setting_info = default_setting_values(setting_id)
		setting_type, setting_default = setting_info['setting_type'], setting_info['setting_default']
		if setting_value is None: setting_value = setting_default
		dbcon.execute(BASE_SET, (setting_id, setting_type, setting_default, setting_value))
		self.set_memory_cache(setting_id, setting_value)
		if setting_type == 'action' and 'settings_options' in setting_info:
			name_setting_id = '%s_name' % setting_id
			name_setting_value = setting_info['settings_options'][setting_value]
			dbcon.execute(BASE_SET, (name_setting_id, 'name', '', name_setting_value))
			self.set_memory_cache(name_setting_id, name_setting_value)

	def set_many(self, settings_list):
		dbcon = connect_database('settings_db')
		dbcon.executemany(BASE_SET, settings_list)
		for item in settings_list: self.set_memory_cache(item[0], item[3] or item[2])

	def set_memory_cache(self, setting_id, setting_value):
		set_property('fenlight.%s' % setting_id, setting_value)

	def delete_memory_cache(self, setting_id):
		clear_property('fenlight.%s' % setting_id)

	def setting_info(self, setting_id):
		return [i for i in default_settings if i['setting_id'] == setting_id][0]

	def clean_database(self):
		try:
			dbcon = connect_database('settings_db')
			dbcon.execute('VACUUM')
			return True
		except: return False

settings_cache = SettingsCache()

def set_setting(setting_id, value):
	settings_cache.set(setting_id, value)

def get_setting(setting_id, fallback=''):
	return get_property(setting_id) or settings_cache.get(setting_id) or fallback

def get_many(settings_list):
	return settings_cache.get_many(settings_list)

def sync_settings(params={}):
	silent = params.get('silent', 'true') == 'true'
	insert_list = []
	insert_list_append = insert_list.append
	currentsettings = settings_cache.get_all()
	defaultsettings_ids = [i['setting_id'] for i in default_settings]
	defaultsettings_names = [i['setting_id'] for i in default_settings if 'settings_options' in i]
	defaultsettings_ids.extend(['%s_name' % i for i in defaultsettings_names])
	try:
		obsoletesettings_ids = [k for k, v in currentsettings.items() if not k in defaultsettings_ids]
		if obsoletesettings_ids:
			for item in obsoletesettings_ids: settings_cache.remove_setting(item)
	except: pass
	if currentsettings:
		for k, v  in currentsettings.items(): settings_cache.set_memory_cache(k, v)
	for item in default_settings:
		setting_id = item['setting_id']
		if setting_id in currentsettings: continue
		setting_type = item['setting_type']
		setting_default = item['setting_default']
		if setting_type == 'action' and 'settings_options' in item:
			name_default = item['settings_options'][setting_default]
			insert_list_append(('%s_name' % setting_id, 'name', name_default, name_default))
		insert_list_append((setting_id, setting_type, setting_default, setting_default))
	if insert_list: settings_cache.set_many(insert_list)
	settings_cache.clean_database()
	if not silent: notification('Settings Cache Remade')

def set_default(setting_ids):
	if not isinstance(setting_ids, list): setting_ids = [setting_ids]
	if not confirm_dialog(text='Are You Sure?', ok_label='Yes', cancel_label='No', default_control=11): return
	for setting_id in setting_ids:
		try: set_setting(setting_id, default_setting_values(setting_id)['setting_default'])
		except: pass

def set_boolean(params):
	setting = params['setting_id']
	set_setting(setting, boolean_dict[get_setting('fenlight.%s' % setting)])

def set_string(params):
	current_value = get_setting('fenlight.%s' % params['setting_id'])
	current_value = current_value.replace('empty_setting', '')
	new_value = kodi_dialog().input('', defaultt=current_value)
	if not new_value and not confirm_dialog(text='Enter Blank Value?', ok_label='Yes', cancel_label='Re-Enter Value', default_control=11): return set_string(params)
	set_setting(params['setting_id'], new_value)

def set_numeric(params):
	setting_id = params['setting_id']
	setting_values = default_setting_values(setting_id)
	values_get = setting_values.get
	min_value, max_value = int(values_get('min_value', '0')), int(values_get('max_value', '100000000000000'))
	negative_included = any((n < 0 for n in [min_value, max_value]))
	if negative_included:
		multiplier_values = [('Positive(+)', 1), ('Negative(-)', -1)]
		list_items = [{'line1': item[0]} for item in multiplier_values]
		kwargs = {'items': json.dumps(list_items), 'narrow_window': 'true', 'heading': 'Will this be a positive or negative number?'}
		multiplier = select_dialog(multiplier_values, **kwargs)
	else: multiplier = None
	new_value = kodi_dialog().input('Range [B]%s - %s[/B].' % (min_value, max_value), type=numeric_input)
	if not new_value: return
	if multiplier: new_value = str(int(float(new_value) * multiplier[1]))
	if int(new_value) < min_value or int(new_value) > max_value:
		ok_dialog(text='Please Choose Between the Range [B]%s - %s[/B].' % (min_value, max_value))
		return set_numeric(params)
	set_setting(setting_id, new_value)

def set_path(params):
	setting_id = params['setting_id']
	browse_mode = int(default_setting_values(setting_id)['browse_mode'])
	new_value = kodi_dialog().browse(browse_mode, '', '', defaultt=get_setting('fenlight.%s' % setting_id))
	set_setting(setting_id, new_value)

def set_from_list(params):
	setting_id = params['setting_id']
	settings_list = [(v, k) for k, v in default_setting_values(setting_id)['settings_options'].items()]
	new_value = select_dialog(settings_list, **{'items': json.dumps([{'line1': item[0]} for item in settings_list]), 'narrow_window': 'true'})
	if not new_value: return
	setting_value = new_value[1]
	set_setting(setting_id, setting_value)

def set_source_folder_path(params):
	setting_id = params['setting_id']
	current_setting = get_setting('fenlight.%s' % setting_id)
	if current_setting not in (None, 'None', ''):
		if confirm_dialog(text='Enter Blank Value?', ok_label='Yes', cancel_label='Re-Enter Value', default_control=11): return set_setting(setting_id, 'None')
	return set_path(params)

def restore_setting_default(params):
	silent = params.get('silent', 'false') == 'true'
	if not silent and not confirm_dialog(): return
	try:
		setting_id = params['setting_id']
		setting_default = default_setting_values(setting_id)['setting_default']
		set_setting(setting_id, setting_default)
	except:
		if not silent: ok_dialog(text='Error restoring default setting')

def default_setting_values(setting_id):
	return next((i for i in default_settings if i['setting_id'] == setting_id), None)

default_settings = [
#===============================================================================#
#====================================GENERAL====================================#
#===============================================================================#
#==================== General
{'setting_id': 'auto_start_fenlight', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'default_addon_fanart', 'setting_type': 'path', 'setting_default': default_addon_fanart, 'browse_mode': '2'},
{'setting_id': 'limit_concurrent_threads', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'max_threads', 'setting_type': 'action', 'setting_default': '60', 'min_value': '10', 'max_value': '250'},
#==================== Manage Updates
{'setting_id': 'update.action', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Prompt', '1': 'Automatic', '2': 'Notification', '3': 'Off'}},
{'setting_id': 'update.delay', 'setting_type': 'action', 'setting_default': '10', 'min_value': '10', 'max_value': '300'},
{'setting_id': 'update.username', 'setting_type': 'string', 'setting_default': 'Tikipeter'},
{'setting_id': 'update.location', 'setting_type': 'string', 'setting_default': 'tikipeter.github.io'},
#==================== Watched Indicators
{'setting_id': 'watched_indicators', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Fen Light', '1': 'Trakt'}},
#======+============= Trakt Cache
{'setting_id': 'trakt.sync_interval', 'setting_type': 'action', 'setting_default': '30', 'min_value': '5', 'max_value': '600'},
{'setting_id': 'trakt.refresh_widgets', 'setting_type': 'boolean', 'setting_default': 'true'},
#==================== UTC Time Offset
{'setting_id': 'datetime.offset', 'setting_type': 'action', 'setting_default': '0', 'min_value': '-15', 'max_value': '15'},
#==================== Downloads
{'setting_id': 'movie_download_directory', 'setting_type': 'path', 'setting_default': 'special://profile/addon_data/plugin.video.fenlight/Movies Downloads/', 'browse_mode': '0'},
{'setting_id': 'tvshow_download_directory', 'setting_type': 'path', 'setting_default': 'special://profile/addon_data/plugin.video.fenlight/TV Show Downloads/', 'browse_mode': '0'},
{'setting_id': 'premium_download_directory', 'setting_type': 'path', 'setting_default': 'special://profile/addon_data/plugin.video.fenlight/Premium Downloads/', 'browse_mode': '0'},
{'setting_id': 'image_download_directory', 'setting_type': 'path', 'setting_default': 'special://profile/addon_data/plugin.video.fenlight/Image Downloads/', 'browse_mode': '0'},


#================================================================================#
#====================================FEATURES====================================#
#================================================================================#
#==================== Extras
{'setting_id': 'extras.enable_extra_ratings', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'extras.enable_scrollbars', 'setting_type': 'boolean', 'setting_default': 'false'},
#==================== Special Open Actions
{'setting_id': 'media_open_action_movie', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'None', '1': 'Open Extras', '2': 'Open Movie Set', '3': 'Both'}},
{'setting_id': 'media_open_action_tvshow', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'None', '1': 'Open Extras'}},


#==================================================================================#
#====================================CONTENT====================================#
#==================================================================================#
#==================== Sorting - Personal Lists
{'setting_id': 'sort.progress', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Title', '1': 'Recently Watched'}},
{'setting_id': 'sort.watched', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Title', '1': 'Recently Watched'}},
{'setting_id': 'sort.collection', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Title', '1': 'Date Added', '2': 'Release Date'}},
{'setting_id': 'sort.watchlist', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Title', '1': 'Date Added', '2': 'Release Date'}},
#==================== Widgets
{'setting_id': 'widget_refresh_timer', 'setting_type': 'string', 'setting_default': '0'},
{'setting_id': 'widget_refresh_notification', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'widget_hide_watched', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'widget_hide_next_page', 'setting_type': 'boolean', 'setting_default': 'false'},
#==================== General
{'setting_id': 'paginate.lists', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Off', '1': 'Within Addon Only', '2': 'Widgets Only', '3': 'Both'}},
{'setting_id': 'paginate.limit_addon', 'setting_type': 'action', 'setting_default': '20'},
{'setting_id': 'paginate.limit_widgets', 'setting_type': 'action', 'setting_default': '20'},
{'setting_id': 'recommend_service', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Recommended (TMDb)', '1': 'More Like This (IMDb)'}},
{'setting_id': 'recommend_seed', 'setting_type': 'action', 'setting_default': '5', 'settings_options': {'1': 'Last Watched Only', '2': 'Last 2 Watched',
'3': 'Last 3 Watched', '4': 'Last 4 Watched', '5': 'Last 5 Watched'}},
{'setting_id': 'mpaa_region', 'setting_type': 'string', 'setting_default': 'US'},
{'setting_id': 'tv_progress_location', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Watched', '1': 'In Progress', '2': 'Both'}},
{'setting_id': 'show_specials', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'default_all_episodes', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Never', '1': 'If Only One Season', '2': 'Always'}},
{'setting_id': 'show_unaired_watchlist', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'meta_filter', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'use_viewtypes', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'manual_viewtypes', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'view.main', 'setting_type': 'string', 'setting_default': '55'},
{'setting_id': 'view.movies', 'setting_type': 'string', 'setting_default': '500'},
{'setting_id': 'view.tvshows', 'setting_type': 'string', 'setting_default': '500'},
{'setting_id': 'view.seasons', 'setting_type': 'string', 'setting_default': '55'},
{'setting_id': 'view.episodes', 'setting_type': 'string', 'setting_default': '55'},
{'setting_id': 'view.episodes_single', 'setting_type': 'string', 'setting_default': '55'},
{'setting_id': 'view.premium', 'setting_type': 'string', 'setting_default': '55'},
#==================================================================================#
#====================================SINGLE EPISODE LISTS====================================#
#==================================================================================#
#==================== General
{'setting_id': 'single_ep_display', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'TITLE: SxE - EPISODE', '1': 'SxE - EPISODE', '2': 'EPISODE'}},
{'setting_id': 'single_ep_display_widget', 'setting_type': 'action', 'setting_default': '1', 'settings_options': {'0': 'TITLE: SxE - EPISODE', '1': 'SxE - EPISODE', '2': 'EPISODE'}},
{'setting_id': 'single_ep_unwatched_episodes', 'setting_type': 'boolean', 'setting_default': 'false'},
#==================== Next Episodes
{'setting_id': 'nextep.method', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Last Aired', '1': 'Last Watched'}},
{'setting_id': 'nextep.sort_type', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Recently Watched', '1': 'Airdate', '2': 'Title'}},
{'setting_id': 'nextep.sort_order', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Descending', '1': 'Ascending'}},
{'setting_id': 'nextep.limit_history', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'nextep.limit', 'setting_type': 'action', 'setting_default': '20', 'min_value': '1', 'max_value': '200'},
{'setting_id': 'nextep.include_unwatched', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'None', '1': 'Watchlist', '2': 'Favorites', '3': 'Both'}},
{'setting_id': 'nextep.include_airdate', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'nextep.airing_today', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'nextep.include_unaired', 'setting_type': 'boolean', 'setting_default': 'false'},
#======+============= Trakt Calendar
{'setting_id': 'trakt.flatten_episodes', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'trakt.calendar_sort_order', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Descending', '1': 'Ascending'}},
{'setting_id': 'trakt.calendar_previous_days', 'setting_type': 'action', 'setting_default': '7', 'min_value': '0', 'max_value': '14'},
{'setting_id': 'trakt.calendar_future_days', 'setting_type': 'action', 'setting_default': '7', 'min_value': '0', 'max_value': '14'},


#=====================================================================================#
#====================================ACCOUNTS====================================#
#=====================================================================================#
#==================== Trakt
{'setting_id': 'trakt.user', 'setting_type': 'string', 'setting_default': 'empty_setting'},
{'setting_id': 'trakt.client', 'setting_type': 'string', 'setting_default': trakt_default_id},
{'setting_id': 'trakt.secret', 'setting_type': 'string', 'setting_default': trakt_default_secret},
#==================== TMDb
{'setting_id': 'tmdb_api', 'setting_type': 'string', 'setting_default': tmdb_default_api},
#==================== OMDb
{'setting_id': 'omdb_api', 'setting_type': 'string', 'setting_default': 'empty_setting'},
#==================== External
{'setting_id': 'provider.external', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'external_scraper.name', 'setting_type': 'string', 'setting_default': 'empty_setting'},
#==================== Real Debrid
{'setting_id': 'rd.token', 'setting_type': 'string', 'setting_default': 'empty_setting'},
{'setting_id': 'rd.enabled', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'rd.account_id', 'setting_type': 'string', 'setting_default': 'empty_setting'},
{'setting_id': 'store_resolved_to_cloud.real-debrid', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'None', '1': 'All', '2': 'Show Packs Only'}},
{'setting_id': 'provider.rd_cloud', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'rd_cloud.title_filter', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'check.rd_cloud', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'results.sort_rdcloud_first', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'rd.priority', 'setting_type': 'action', 'setting_default': '10', 'min_value': '1', 'max_value': '10'},
#==================== Premiumize
{'setting_id': 'pm.token', 'setting_type': 'string', 'setting_default': 'empty_setting'},
{'setting_id': 'pm.enabled', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'pm.account_id', 'setting_type': 'string', 'setting_default': 'empty_setting'},
{'setting_id': 'store_resolved_to_cloud.premiumize.me', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'None', '1': 'All', '2': 'Show Packs Only'}},
{'setting_id': 'provider.pm_cloud', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'pm_cloud.title_filter', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'check.pm_cloud', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'results.sort_pmcloud_first', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'pm.priority', 'setting_type': 'action', 'setting_default': '10', 'min_value': '1', 'max_value': '10'},
#==================== All Debrid
{'setting_id': 'ad.token', 'setting_type': 'string', 'setting_default': 'empty_setting'},
{'setting_id': 'ad.enabled', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'ad.account_id', 'setting_type': 'string', 'setting_default': 'empty_setting'},
{'setting_id': 'store_resolved_to_cloud.alldebrid', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'None', '1': 'All', '2': 'Show Packs Only'}},
{'setting_id': 'provider.ad_cloud', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'ad_cloud.title_filter', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'check.ad_cloud', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'results.sort_adcloud_first', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'ad.priority', 'setting_type': 'action', 'setting_default': '10', 'min_value': '1', 'max_value': '10'},
#==================== Off Cloud
{'setting_id': 'oc.token', 'setting_type': 'string', 'setting_default': 'empty_setting'},
{'setting_id': 'oc.enabled', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'store_resolved_to_cloud.offcloud', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'None', '1': 'All', '2': 'Show Packs Only'}},
{'setting_id': 'provider.oc_cloud', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'oc_cloud.title_filter', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'check.oc_cloud', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'results.sort_occloud_first', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'oc.priority', 'setting_type': 'action', 'setting_default': '10', 'min_value': '1', 'max_value': '10'},
#==================== Easy Debrid
{'setting_id': 'ed.token', 'setting_type': 'string', 'setting_default': 'empty_setting'},
{'setting_id': 'ed.enabled', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'ed.priority', 'setting_type': 'action', 'setting_default': '10', 'min_value': '1', 'max_value': '10'},
#==================== TorBox
{'setting_id': 'tb.token', 'setting_type': 'string', 'setting_default': 'empty_setting'},
{'setting_id': 'tb.enabled', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'store_resolved_to_cloud.torbox', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'None', '1': 'All', '2': 'Show Packs Only'}},
{'setting_id': 'provider.tb_cloud', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'tb_cloud.title_filter', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'check.tb_cloud', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'results.sort_tbcloud_first', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'tb.priority', 'setting_type': 'action', 'setting_default': '10', 'min_value': '1', 'max_value': '10'},
#==================== Easynews
{'setting_id': 'provider.easynews', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'easynews_user', 'setting_type': 'string', 'setting_default': 'empty_setting'},
{'setting_id': 'easynews_password', 'setting_type': 'string', 'setting_default': 'empty_setting'},
{'setting_id': 'easynews.title_filter', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'easynews.filter_lang', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'easynews.lang_filters', 'setting_type': 'string', 'setting_default': '0'},
{'setting_id': 'check.easynews', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'en.priority', 'setting_type': 'action', 'setting_default': '7', 'min_value': '1', 'max_value': '10'},
#=========+========== Folders
{'setting_id': 'provider.folders', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'folders.title_filter', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'check.folders', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'results.sort_folders_first', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'results.folders_ignore_filters', 'setting_type': 'boolean', 'setting_default': 'false'},


#===============================================================================#
#====================================RESULTS====================================#
#===============================================================================#
#==================== Display
{'setting_id': 'results.timeout', 'setting_type': 'action', 'setting_default': '20', 'min_value': '1'},
{'setting_id': 'results.list_format', 'setting_type': 'string', 'setting_default': 'List'},
#==================== General
{'setting_id': 'results.auto_rescrape_with_all', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Off', '1': 'Auto', '2': 'Prompt'}},
{'setting_id': 'results.auto_episode_group', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Off', '1': 'Auto', '2': 'Prompt'}},
{'setting_id': 'results.ignore_filter', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Off', '1': 'Auto', '2': 'Prompt'}},
#==================== Sorting and Filtering
{'setting_id': 'results.sort_order_display', 'setting_type': 'string', 'setting_default': 'Quality, Size, Provider'},
{'setting_id': 'results.size_sort_direction', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Descending', '1': 'Ascending'}},
{'setting_id': 'results.filter_size_method', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Off', '1': 'Use Line Speed', '2': 'Use Size'}},
{'setting_id': 'results.line_speed', 'setting_type': 'action', 'setting_default': '25', 'min_value': '1'},
{'setting_id': 'results.movie_size_max', 'setting_type': 'action', 'setting_default': '10000', 'min_value': '1'},
{'setting_id': 'results.episode_size_max', 'setting_type': 'action', 'setting_default': '3000', 'min_value': '1'},
{'setting_id': 'results.movie_size_min', 'setting_type': 'action', 'setting_default': '0', 'min_value': '0'},
{'setting_id': 'results.episode_size_min', 'setting_type': 'action', 'setting_default': '0', 'min_value': '0'},
{'setting_id': 'results.size_unknown', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'results.include.unknown.size', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'filter.include_prerelease', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Include', '1': 'Exclude'}},
{'setting_id': 'filter.hevc', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Include', '1': 'Exclude'}},
{'setting_id': 'filter.hevc.max_quality', 'setting_type': 'action', 'setting_default': '4K', 'settings_options': {'4K': '4K', '1080p': '1080p', '720p': '720p', 'SD': 'SD'}},
{'setting_id': 'filter.hevc.max_autoplay_quality', 'setting_type': 'action', 'setting_default': '4K', 'settings_options': {'4K': '4K', '1080p': '1080p', '720p': '720p', 'SD': 'SD'}},
{'setting_id': 'filter.3d', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Include', '1': 'Exclude'}},
{'setting_id': 'filter.hdr', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Include', '1': 'Exclude'}},
{'setting_id': 'filter.dv', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Include', '1': 'Exclude'}},
{'setting_id': 'filter.av1', 'setting_type': 'action', 'setting_default': '0', 'settings_options':{'0': 'Include', '1': 'Exclude'}},
{'setting_id': 'filter.enhanced_upscaled', 'setting_type': 'action', 'setting_default': '0', 'settings_options':{'0': 'Include', '1': 'Exclude'}},
{'setting_id': 'preferred_autoplay', 'setting_type': 'string', 'setting_default': 'empty_setting'},
{'setting_id': 'filter_audio', 'setting_type': 'string', 'setting_default': 'empty_setting'},
#==================== Results Color Highlights
{'setting_id': 'highlight.type', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Provider', '1': 'Quality', '2': 'Single Color'}},
{'setting_id': 'provider.easynews_highlight', 'setting_type': 'string', 'setting_default': 'FF00B3B2'},
{'setting_id': 'provider.debrid_cloud_highlight', 'setting_type': 'string', 'setting_default': 'FF7A01CC'},
{'setting_id': 'provider.folders_highlight', 'setting_type': 'string', 'setting_default': 'FFB36B00'},
{'setting_id': 'provider.rd_highlight', 'setting_type': 'string', 'setting_default': 'FF3C9900'},
{'setting_id': 'provider.pm_highlight', 'setting_type': 'string', 'setting_default': 'FFFF3300'},
{'setting_id': 'provider.ad_highlight', 'setting_type': 'string', 'setting_default': 'FFE6B800'},
{'setting_id': 'provider.oc_highlight', 'setting_type': 'string', 'setting_default': 'FF008EB2'},
{'setting_id': 'provider.ed_highlight', 'setting_type': 'string', 'setting_default': 'FF3233FF'},
{'setting_id': 'provider.tb_highlight', 'setting_type': 'string', 'setting_default': 'FF01662A'},
{'setting_id': 'scraper_4k_highlight', 'setting_type': 'string', 'setting_default': 'FFFF00FE'},
{'setting_id': 'scraper_1080p_highlight', 'setting_type': 'string', 'setting_default': 'FFE6B800'},
{'setting_id': 'scraper_720p_highlight', 'setting_type': 'string', 'setting_default': 'FF3C9900'},
{'setting_id': 'scraper_SD_highlight', 'setting_type': 'string', 'setting_default': 'FF0166FF'},
{'setting_id': 'scraper_single_highlight', 'setting_type': 'string', 'setting_default': 'FF008EB2'},


#===============================================================================#
#===================================PLAYBACK====================================#
#===============================================================================#
#==================== Playback Movies
{'setting_id': 'auto_play_movie', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'results_quality_movie', 'setting_type': 'string', 'setting_default': 'SD, 720p, 1080p, 4K'},
{'setting_id': 'autoplay_quality_movie', 'setting_type': 'string', 'setting_default': 'SD, 720p, 1080p, 4K'},
{'setting_id': 'auto_resume_movie', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Never', '1': 'Always', '2': 'Autoplay Only'}},
#==================== Playback Episodes
{'setting_id': 'auto_play_episode', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'results_quality_episode', 'setting_type': 'string', 'setting_default': 'SD, 720p, 1080p, 4K'},
{'setting_id': 'autoplay_quality_episode', 'setting_type': 'string', 'setting_default': 'SD, 720p, 1080p, 4K'},
{'setting_id': 'autoplay_next_episode', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'autoplay_default_action', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Play', '1': 'Cancel', '2': 'Pause & Wait'}},
{'setting_id': 'autoplay_alert_method', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Window', '1': 'Notification'}},
{'setting_id': 'autoplay_next_window_percentage', 'setting_type': 'action', 'setting_default': '95', 'min_value': '75', 'max_value': '99'},
{'setting_id': 'autoplay_use_chapters', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'autoscrape_next_episode', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'autoscrape_next_window_percentage', 'setting_type': 'action', 'setting_default': '95', 'min_value': '75', 'max_value': '99'},
{'setting_id': 'autoscrape_use_chapters', 'setting_type': 'boolean', 'setting_default': 'true'},
{'setting_id': 'auto_resume_episode', 'setting_type': 'action', 'setting_default': '0', 'settings_options': {'0': 'Never', '1': 'Always', '2': 'Autoplay Only'}},
#==================== Playback Utilities
{'setting_id': 'playback.limit_resolve', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'playback.volumecheck_enabled', 'setting_type': 'boolean', 'setting_default': 'false'},
{'setting_id': 'playback.volumecheck_percent', 'setting_type': 'action', 'setting_default': '50', 'min_value': '1', 'max_value': '100'},


#=========================================================================================#
#======================================HIDDEN=============================================#
#=========================================================================================#
{'setting_id': 'widget_refresh_timer_name', 'setting_type': 'string', 'setting_default': 'Off'},
{'setting_id': 'mpaa_region_display_name', 'setting_type': 'string', 'setting_default': 'United States'},
{'setting_id': 'external_scraper.module', 'setting_type': 'string', 'setting_default': 'empty_setting'},
{'setting_id': 'trakt.next_daily_clear', 'setting_type': 'string', 'setting_default': '0'},
{'setting_id': 'trakt.expires', 'setting_type': 'string', 'setting_default': '0'},
{'setting_id': 'trakt.refresh', 'setting_type': 'string', 'setting_default': '0'},
{'setting_id': 'trakt.token', 'setting_type': 'string', 'setting_default': '0'},
{'setting_id': 'rd.client_id', 'setting_type': 'string', 'setting_default': 'empty_setting'},
{'setting_id': 'rd.refresh', 'setting_type': 'string', 'setting_default': 'empty_setting'},
{'setting_id': 'rd.secret', 'setting_type': 'string', 'setting_default': 'empty_setting'},
{'setting_id': 'results.sort_order', 'setting_type': 'string', 'setting_default': '1'},
{'setting_id': 'folder1.display_name', 'setting_type': 'string', 'setting_default': 'Folder 1'},
{'setting_id': 'folder1.movies_directory', 'setting_type': 'path', 'setting_default': 'None', 'browse_mode': '0'},
{'setting_id': 'folder1.tv_shows_directory', 'setting_type': 'path', 'setting_default': 'None', 'browse_mode': '0'},
{'setting_id': 'folder2.display_name', 'setting_type': 'string', 'setting_default': 'Folder 2'},
{'setting_id': 'folder2.movies_directory', 'setting_type': 'path', 'setting_default': 'None', 'browse_mode': '0'},
{'setting_id': 'folder2.tv_shows_directory', 'setting_type': 'path', 'setting_default': 'None', 'browse_mode': '0'},
{'setting_id': 'folder3.display_name', 'setting_type': 'string', 'setting_default': 'Folder 3'},
{'setting_id': 'folder3.movies_directory', 'setting_type': 'path', 'setting_default': 'None', 'browse_mode': '0'},
{'setting_id': 'folder3.tv_shows_directory', 'setting_type': 'path', 'setting_default': 'None', 'browse_mode': '0'},
{'setting_id': 'folder4.display_name', 'setting_type': 'string', 'setting_default': 'Folder 4'},
{'setting_id': 'folder4.movies_directory', 'setting_type': 'path', 'setting_default': 'None', 'browse_mode': '0'},
{'setting_id': 'folder4.tv_shows_directory', 'setting_type': 'path', 'setting_default': 'None', 'browse_mode': '0'},
{'setting_id': 'folder5.display_name', 'setting_type': 'string', 'setting_default': 'Folder 5'},
{'setting_id': 'folder5.movies_directory', 'setting_type': 'path', 'setting_default': 'None', 'browse_mode': '0'},
{'setting_id': 'folder5.tv_shows_directory', 'setting_type': 'path', 'setting_default': 'None', 'browse_mode': '0'},
{'setting_id': 'extras.enabled', 'setting_type': 'string', 'setting_default': '2000,2050,2051,2052,2053,2054,2055,2056,2057,2058,2059,2060,2061,2062'},
{'setting_id': 'extras.tvshow.button10', 'setting_type': 'string', 'setting_default': 'tvshow_browse'},
{'setting_id': 'extras.tvshow.button11', 'setting_type': 'string', 'setting_default': 'show_trailers'},
{'setting_id': 'extras.tvshow.button12', 'setting_type': 'string', 'setting_default': 'show_keywords'},
{'setting_id': 'extras.tvshow.button13', 'setting_type': 'string', 'setting_default': 'show_images'},
{'setting_id': 'extras.tvshow.button14', 'setting_type': 'string', 'setting_default': 'show_extrainfo'},
{'setting_id': 'extras.tvshow.button15', 'setting_type': 'string', 'setting_default': 'show_genres'},
{'setting_id': 'extras.tvshow.button16', 'setting_type': 'string', 'setting_default': 'play_nextep'},
{'setting_id': 'extras.tvshow.button17', 'setting_type': 'string', 'setting_default': 'show_options'},
{'setting_id': 'extras.movie.button10', 'setting_type': 'string', 'setting_default': 'movies_play'},
{'setting_id': 'extras.movie.button11', 'setting_type': 'string', 'setting_default': 'show_trailers'},
{'setting_id': 'extras.movie.button12', 'setting_type': 'string', 'setting_default': 'show_keywords'},
{'setting_id': 'extras.movie.button13', 'setting_type': 'string', 'setting_default': 'show_images'},
{'setting_id': 'extras.movie.button14', 'setting_type': 'string', 'setting_default': 'show_extrainfo'},
{'setting_id': 'extras.movie.button15', 'setting_type': 'string', 'setting_default': 'show_genres'},
{'setting_id': 'extras.movie.button16', 'setting_type': 'string', 'setting_default': 'show_director'},
{'setting_id': 'extras.movie.button17', 'setting_type': 'string', 'setting_default': 'show_options'}
	]