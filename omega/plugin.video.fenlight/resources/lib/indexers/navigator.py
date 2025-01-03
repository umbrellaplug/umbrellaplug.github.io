# -*- coding: utf-8 -*-
import sys
import json
from urllib.parse import unquote
from caches.main_cache import main_cache
from caches.navigator_cache import navigator_cache as nc
from caches.settings_cache import get_setting, set_setting
from modules import meta_lists as ml, kodi_utils as k, settings as s
from modules.watched_status import get_recently_watched
# logger = k.logger

tp, build_url, notification, addon, make_listitem, list_dirs = k.translate_path, k.build_url, k.notification, k.addon, k.make_listitem, k.list_dirs
add_item, set_content, end_directory, set_view_mode, add_items, get_infolabel = k.add_item, k.set_content, k.end_directory, k.set_view_mode, k.add_items, k.get_infolabel
set_sort_method, set_category, container_refresh_input, current_window_object = k.set_sort_method, k.set_category, k.container_refresh_input, k.current_window_object
close_all_dialog, sleep, home, get_property, set_property, fanart = k.close_all_dialog, k.sleep, k.home, k.get_property, k.set_property, k.get_addon_fanart()
download_directory, easynews_authorized, get_icon, container_refresh = s.download_directory, s.easynews_authorized, k.get_icon, k.container_refresh
get_shortcut_folders, currently_used_list, get_shortcut_folder_contents = nc.get_shortcut_folders, nc.currently_used_list, nc.get_shortcut_folder_contents
get_main_lists, authorized_debrid_check, trakt_user_active = nc.get_main_lists, s.authorized_debrid_check, s.trakt_user_active
log_loc, old_log_loc = tp('special://logpath/kodi.log'), tp('special://logpath/kodi.old.log')
folder_icon = get_icon('folder')
random_test = '[COLOR red][RANDOM][/COLOR]'
run_plugin = 'RunPlugin(%s)'
random_list_dict = {'movie': nc.random_movie_lists, 'tvshow': nc.random_tvshow_lists, 'anime': nc.random_anime_lists, 'trakt': nc.random_trakt_lists,
'because_you_watched': nc.random_because_you_watched_lists}
search_mode_dict = {'movie': ('movie_queries', {'mode': 'search.get_key_id', 'media_type': 'movie', 'isFolder': 'false'}),
				'tvshow': ('tvshow_queries', {'mode': 'search.get_key_id', 'media_type': 'tv_show', 'isFolder': 'false'}),
				'anime': ('anime_queries', {'mode': 'search.get_key_id', 'media_type': 'anime', 'isFolder': 'false'}),
				'people': ('people_queries', {'mode': 'search.get_key_id', 'search_type': 'people', 'isFolder': 'false'}),
				'tmdb_keyword_movie': ('keyword_tmdb_movie_queries', {'mode': 'search.get_key_id', 'search_type': 'tmdb_keyword', 'media_type': 'movie', 'isFolder': 'false'}),
				'tmdb_keyword_tvshow': ('keyword_tmdb_tvshow_queries', {'mode': 'search.get_key_id', 'search_type': 'tmdb_keyword', 'media_type': 'tvshow', 'isFolder': 'false'}),
				'easynews_video': ('easynews_video_queries', {'mode': 'search.get_key_id', 'search_type': 'easynews_video', 'isFolder': 'false'}),
				'easynews_image': ('easynews_image_queries', {'mode': 'search.get_key_id', 'search_type': 'easynews_image', 'isFolder': 'false'}),
				'trakt_lists': ('trakt_list_queries', {'mode': 'search.get_key_id', 'search_type': 'trakt_lists', 'isFolder': 'false'})}

class Navigator:
	def __init__(self, params):
		self.params = params
		self.params_get = self.params.get
		self.category_name = self.params_get('name', 'Fen Light')
		self.list_name = self.params_get('action', 'RootList')
		self.is_home = home()

	def main(self):
		if self.params_get('full_list', 'false') == 'true': browse_list = get_main_lists(self.list_name)[0]
		else: browse_list = currently_used_list(self.list_name)
		for count, item in enumerate(browse_list):
			iconImage = item.get('iconImage')
			icon, original_image = (iconImage, True) if iconImage.startswith('http') else (iconImage, False)
			cm_items = [('[B]Move[/B]', run_plugin % build_url({'mode': 'menu_editor.move', 'active_list': self.list_name, 'position': count})),
						('[B]Remove[/B]', run_plugin % build_url({'mode': 'menu_editor.remove', 'active_list': self.list_name, 'position': count})),
						('[B]Add Content[/B]', run_plugin % build_url({'mode': 'menu_editor.add', 'active_list': self.list_name, 'position': count})),
						('[B]Restore Menu[/B]', run_plugin % build_url({'mode': 'menu_editor.restore', 'active_list': self.list_name, 'position': count})),
						('[B]Check for New Menu Items[/B]', run_plugin % build_url({'mode': 'menu_editor.update', 'active_list': self.list_name, 'position': count})),
						('[B]Reload Menu[/B]', run_plugin % build_url({'mode': 'menu_editor.reload', 'active_list': self.list_name, 'position': count})),
						('[B]Browse Removed items[/B]', run_plugin % build_url({'mode': 'menu_editor.browse', 'active_list': self.list_name, 'position': count}))]
			self.add(item, item.get('name', ''), icon, original_image, cm_items=cm_items)
		self.end_directory()

	def discover(self):
		self.add({'mode': 'navigator.discover_contents', 'media_type': 'movie'}, 'Movies', 'movies')
		self.add({'mode': 'navigator.discover_contents', 'media_type': 'tvshow'}, 'TV Shows', 'tv')
		self.end_directory()

	def premium(self):
		if authorized_debrid_check('rd'): self.add({'mode': 'navigator.real_debrid'}, 'Real Debrid', 'realdebrid')
		if authorized_debrid_check('pm'): self.add({'mode': 'navigator.premiumize'}, 'Premiumize', 'premiumize')
		if authorized_debrid_check('ad'): self.add({'mode': 'navigator.alldebrid'}, 'All Debrid', 'alldebrid')
		if authorized_debrid_check('oc'): self.add({'mode': 'navigator.offcloud'}, 'Off Cloud', 'offcloud')
		if authorized_debrid_check('tb'): self.add({'mode': 'navigator.torbox'}, 'TorBox', 'torbox')
		if easynews_authorized(): self.add({'mode': 'navigator.easynews'}, 'Easynews', 'easynews')
		self.end_directory()

	def easynews(self):
		self.add({'mode': 'navigator.search_history', 'action': 'easynews_video'}, 'Search Videos', 'search')
		self.add({'mode': 'navigator.search_history', 'action': 'easynews_image'}, 'Search Images', 'search')
		self.add({'mode': 'easynews.account_info', 'isFolder': 'false'}, 'Account Info', 'easynews')
		self.end_directory()

	def real_debrid(self):
		self.add({'mode': 'real_debrid.rd_cloud'}, 'Cloud Storage', 'realdebrid')
		self.add({'mode': 'real_debrid.rd_downloads'}, 'History', 'realdebrid')
		self.add({'mode': 'real_debrid.rd_account_info', 'isFolder': 'false'}, 'Account Info', 'realdebrid')
		self.end_directory()

	def premiumize(self):
		self.add({'mode': 'premiumize.pm_cloud'}, 'Cloud Storage', 'premiumize')
		self.add({'mode': 'premiumize.pm_transfers'}, 'History', 'premiumize')
		self.add({'mode': 'premiumize.pm_account_info', 'isFolder': 'false'}, 'Account Info', 'premiumize')
		self.end_directory()

	def alldebrid(self):
		self.add({'mode': 'alldebrid.ad_cloud'}, 'Cloud Storage', 'alldebrid')
		self.add({'mode': 'alldebrid.ad_account_info', 'isFolder': 'false'}, 'Account Info', 'alldebrid')
		self.end_directory()

	def offcloud(self):
		self.add({'mode': 'offcloud.oc_cloud'}, 'Cloud Storage', 'offcloud')
		self.add({'mode': 'offcloud.oc_account_info', 'isFolder': 'false'}, 'Account Info', 'offcloud')
		self.end_directory()

	def torbox(self):
		self.add({'mode': 'torbox.tb_cloud'}, 'Cloud Storage', 'torbox')
		self.add({'mode': 'torbox.tb_account_info', 'isFolder': 'false'}, 'Account Info', 'torbox')
		self.end_directory()

	def favorites(self):
		self.add({'mode': 'build_movie_list', 'action': 'favorites_movies', 'name': 'Movies'}, 'Movies', 'movies')
		self.add({'mode': 'build_tvshow_list', 'action': 'favorites_tvshows', 'name': 'TV Shows'}, 'TV Shows', 'tv')
		self.add({'mode': 'build_tvshow_list', 'action': 'favorites_anime_tvshows', 'name': 'Anime'}, 'Anime', 'anime')
		self.add({'mode': 'favorite_people', 'isFolder': 'false', 'name': 'People'}, 'People', 'genre_family')
		self.end_directory()

	def my_content(self):
		if trakt_user_active():
			self.add({'mode': 'navigator.trakt_collections'}, 'Trakt Collection', 'trakt')
			self.add({'mode': 'navigator.trakt_watchlists'}, 'Trakt Watchlist', 'trakt')
			self.add({'mode': 'trakt.list.get_trakt_lists', 'list_type': 'my_lists', 'category_name': 'My Lists'}, 'Trakt My Lists', 'trakt')
			self.add({'mode': 'trakt.list.get_trakt_lists', 'list_type': 'liked_lists', 'category_name': 'Liked Lists'}, 'Trakt Liked Lists', 'trakt')
			self.add({'mode': 'navigator.trakt_favorites', 'category_name': 'Favorites'}, 'Trakt Favorites', 'trakt')
			self.add({'mode': 'navigator.trakt_recommendations', 'category_name': 'Recommended'}, 'Trakt Recommended', 'trakt')
			self.add({'mode': 'build_my_calendar'}, 'Trakt Calendar', 'trakt')
		self.add({'mode': 'trakt.list.get_trakt_trending_popular_lists', 'list_type': 'trending', 'category_name': 'Trending User Lists'}, 'Trending User Lists', 'trakt')
		self.add({'mode': 'trakt.list.get_trakt_trending_popular_lists', 'list_type': 'popular', 'category_name': 'Popular User Lists'}, 'Popular User Lists', 'trakt')
		self.add({'mode': 'navigator.search_history', 'action': 'trakt_lists'}, 'Search User Lists', 'search')
		self.end_directory()

	def random_lists(self):
		self.add({'mode': 'navigator.build_random_lists', 'menu_type': 'movie'}, 'Movie Lists', 'movies')
		self.add({'mode': 'navigator.build_random_lists', 'menu_type': 'tvshow'}, 'TV Show Lists', 'tv')
		self.add({'mode': 'navigator.build_random_lists', 'menu_type': 'anime'}, 'Anime Lists', 'anime')
		self.add({'mode': 'navigator.build_random_lists', 'menu_type': 'because_you_watched'}, 'Because You Watched', 'because_you_watched')
		if trakt_user_active(): self.add({'mode': 'navigator.build_random_lists', 'menu_type': 'trakt'}, 'Trakt Lists', 'trakt')
		self.end_directory()

	def trakt_collections(self):
		self.category_name = 'Collection'
		self.add({'mode': 'build_movie_list', 'action': 'trakt_collection', 'category_name': 'Movies Collection'}, 'Movies', 'trakt')
		self.add({'mode': 'build_tvshow_list', 'action': 'trakt_collection', 'category_name': 'TV Shows Collection'}, 'TV Shows', 'trakt')
		self.add({'mode': 'build_movie_list', 'action': 'trakt_collection_lists', 'new_page': 'recent', 'category_name': 'Recently Added Movies'}, 'Recently Added Movies', 'trakt')
		self.add({'mode': 'build_tvshow_list', 'action': 'trakt_collection_lists', 'new_page': 'recent', 'category_name': 'Recently Added TV Shows'},
					'Recently Added TV Shows', 'trakt')
		self.add({'mode': 'build_my_calendar', 'recently_aired': 'true'}, 'Recently Aired Episodes', 'trakt')
		self.end_directory()

	def trakt_watchlists(self):
		self.category_name = 'Watchlist'
		self.add({'mode': 'build_movie_list', 'action': 'trakt_watchlist', 'category_name': 'Movies Watchlist'}, 'Movies', 'trakt')
		self.add({'mode': 'build_tvshow_list', 'action': 'trakt_watchlist', 'category_name': 'TV Shows Watchlist'}, 'TV Shows', 'trakt')
		self.add({'mode': 'build_movie_list', 'action': 'trakt_watchlist_lists', 'new_page': 'recent', 'category_name': 'Recently Added Movies'}, 'Recently Added Movies', 'trakt')
		self.add({'mode': 'build_tvshow_list', 'action': 'trakt_watchlist_lists', 'new_page': 'recent', 'category_name': 'Recently Added TV Shows'},
					'Recently Added TV Shows', 'trakt')
		self.end_directory()

	def trakt_recommendations(self):
		self.category_name = 'Recommended'
		self.add({'mode': 'build_movie_list', 'action': 'trakt_recommendations', 'category_name': 'Recommended Movies'}, 'Movies', 'trakt')
		self.add({'mode': 'build_tvshow_list', 'action': 'trakt_recommendations', 'category_name': 'Recommended TV Shows'}, 'TV Shows', 'trakt')
		self.end_directory()

	def trakt_favorites(self):
		self.category_name = 'Favorites'
		self.add({'mode': 'build_movie_list', 'action': 'trakt_favorites', 'category_name': 'Favorite Movies'}, 'Movies', 'trakt')
		self.add({'mode': 'build_tvshow_list', 'action': 'trakt_favorites', 'category_name': 'Favorite TV Shows'}, 'TV Shows', 'trakt')
		self.end_directory()

	def people(self):
		self.add({'mode': 'build_tmdb_people', 'action': 'popular', 'isFolder': 'false', 'name': 'Popular'}, 'Popular', 'popular')
		self.add({'mode': 'build_tmdb_people', 'action': 'day', 'isFolder': 'false', 'name': 'Trending'}, 'Trending', 'trending')
		self.add({'mode': 'build_tmdb_people', 'action': 'week', 'isFolder': 'false', 'name': 'Trending This Week'}, 'Trending This Week', 'trending_recent')
		self.end_directory()

	def search(self):
		self.add({'mode': 'navigator.search_history', 'action': 'movie', 'name': 'Search History Movies'}, 'Movies', 'search_movie')
		self.add({'mode': 'navigator.search_history', 'action': 'tvshow', 'name': 'Search History TV Shows'}, 'TV Shows', 'search_tv')
		self.add({'mode': 'navigator.search_history', 'action': 'anime', 'name': 'Search History Anime'}, 'Anime', 'search_anime')
		self.add({'mode': 'navigator.search_history', 'action': 'people', 'name': 'Search History People'}, 'People', 'search_people')
		self.add({'mode': 'navigator.search_history', 'action': 'tmdb_keyword_movie', 'name': 'Search History Keywords (Movies)'}, 'Keywords (Movies)', 'search_tmdb')
		self.add({'mode': 'navigator.search_history', 'action': 'tmdb_keyword_tvshow', 'name': 'Search History Keywords (TV Shows)'}, 'Keywords (TV Shows)', 'search_tmdb')
		self.end_directory()

	def downloads(self):
		self.add({'mode': 'downloader.manager', 'name': 'Download Manager', 'isFolder': 'false'}, 'Download Manager', 'downloads')
		self.add({'mode': 'downloader.viewer', 'folder_type': 'movie', 'name': 'Movies'}, 'Movies', 'movies')
		self.add({'mode': 'downloader.viewer', 'folder_type': 'episode', 'name': 'TV Shows'}, 'TV Shows', 'tv')
		self.add({'mode': 'downloader.viewer', 'folder_type': 'premium', 'name': 'Premium Files'}, 'Premium Files', 'premium')
		self.add({'mode': 'browser_image', 'folder_path': download_directory('image'), 'isFolder': 'false'}, 'Images', 'people')
		self.end_directory()

	def tools(self):
		self.add({'mode': 'open_settings', 'isFolder': 'false'}, 'Settings', 'settings')
		if get_setting('fenlight.external_scraper.module') not in ('empty_setting', ''):
			self.add({'mode': 'open_external_scraper_settings', 'isFolder': 'false'}, 'External Scraper Settings', 'settings')
		self.add({'mode': 'navigator.tips'}, 'Tips for Use', 'settings2')
		if get_setting('fenlight.use_viewtypes', 'true') == 'true' and not get_setting('fenlight.manual_viewtypes', 'false') == 'true':
			self.add({'mode': 'navigator.set_view_modes'}, 'Set Views', 'settings2')
		self.add({'mode': 'navigator.changelog_utils'}, 'Changelog & Log Utils', 'settings2')
		self.add({'mode': 'build_next_episode_manager'}, 'TV Shows Progress Manager', 'settings2')
		self.add({'mode': 'navigator.shortcut_folders'}, 'Shortcut Folders Manager', 'settings2')
		self.add({'mode': 'navigator.maintenance'}, 'Database & Cache Maintenance', 'settings2')
		self.add({'mode': 'navigator.update_utils'}, 'Update Utilities', 'settings2')
		self.add({'mode': 'toggle_language_invoker', 'isFolder': 'false'}, 'Toggle Language Invoker (ADVANCED!!)', 'settings2')
		self.end_directory()

	def maintenance(self):
		self.add({'mode': 'check_databases_integrity_cache', 'isFolder': 'false'}, 'Check for Corrupt Databases', 'settings')
		self.add({'mode': 'clean_databases_cache', 'isFolder': 'false'}, 'Clean Databases', 'settings')
		self.add({'mode': 'sync_settings', 'silent': 'false', 'isFolder': 'false'}, 'Remake Settings Cache', 'settings')
		self.add({'mode': 'clear_all_cache', 'isFolder': 'false'}, 'Clear All Cache (Excluding Favorites)', 'settings')
		self.add({'mode': 'clear_favorites_choice', 'isFolder': 'false'}, 'Clear Favorites Cache', 'settings')
		self.add({'mode': 'search.clear_search', 'isFolder': 'false'}, 'Clear Search History Cache', 'settings')
		self.add({'mode': 'clear_cache', 'cache': 'main', 'isFolder': 'false'}, 'Clear Main Cache', 'settings')
		self.add({'mode': 'clear_cache', 'cache': 'meta', 'isFolder': 'false'}, 'Clear Meta Cache', 'settings')
		self.add({'mode': 'clear_cache', 'cache': 'list', 'isFolder': 'false'}, 'Clear Lists Cache', 'settings')
		self.add({'mode': 'clear_cache', 'cache': 'trakt', 'isFolder': 'false'}, 'Clear Trakt Cache', 'settings')
		self.add({'mode': 'clear_cache', 'cache': 'imdb', 'isFolder': 'false'}, 'Clear IMDb Cache', 'settings')
		self.add({'mode': 'clear_cache', 'cache': 'internal_scrapers', 'isFolder': 'false'}, 'Clear Internal Scrapers Cache', 'settings')
		self.add({'mode': 'clear_cache', 'cache': 'external_scrapers', 'isFolder': 'false'}, 'Clear External Scrapers Cache', 'settings')
		self.add({'mode': 'clear_cache', 'cache': 'rd_cloud', 'isFolder': 'false'}, 'Clear Real Debrid Cache', 'settings')
		self.add({'mode': 'clear_cache', 'cache': 'pm_cloud', 'isFolder': 'false'}, 'Clear Premiumize Cache', 'settings')
		self.add({'mode': 'clear_cache', 'cache': 'ad_cloud', 'isFolder': 'false'}, 'Clear All Debrid Cache', 'settings')
		self.add({'mode': 'clear_cache', 'cache': 'oc_cloud', 'isFolder': 'false'}, 'Clear Off Cloud Cache', 'settings')
		self.add({'mode': 'clear_cache', 'cache': 'ed_cloud', 'isFolder': 'false'}, 'Clear Easy Debrid Cache', 'settings')
		self.add({'mode': 'clear_cache', 'cache': 'tb_cloud', 'isFolder': 'false'}, 'Clear TorBox Cache', 'settings')
		self.end_directory()

	def set_view_modes(self):
		self.add({'mode': 'navigator.choose_view', 'view_type': 'view.main', 'content': '', 'name': 'menus'}, 'Set Menus', 'folder')
		self.add({'mode': 'navigator.choose_view', 'view_type': 'view.movies', 'content': 'movies'}, 'Set Movies', 'movies')
		self.add({'mode': 'navigator.choose_view', 'view_type': 'view.tvshows', 'content': 'tvshows'}, 'Set TV Shows', 'tv')
		self.add({'mode': 'navigator.choose_view', 'view_type': 'view.seasons', 'content': 'seasons'}, 'Set Seasons', 'ontheair')
		self.add({'mode': 'navigator.choose_view', 'view_type': 'view.episodes', 'content': 'episodes'}, 'Set Episodes', 'next_episodes')
		self.add({'mode': 'navigator.choose_view', 'view_type': 'view.episodes_single', 'content': 'episodes', 'name': 'episode lists'}, 'Set Episode Lists', 'calender')
		self.add({'mode': 'navigator.choose_view', 'view_type': 'view.premium', 'content': 'files', 'name': 'premium files'}, 'Set Premium Files', 'premium')
		self.end_directory()

	def update_utils(self):
		self.add({'mode': 'updater.update_check', 'isFolder': 'false'}, 'Check For Updates', 'github')
		# self.add({'mode': 'updater.rollback_check', 'isFolder': 'false'}, 'Rollback to a Previous Version', 'github')
		self.add({'mode': 'updater.get_changes', 'isFolder': 'false'}, 'Check Online Version Changelog', 'github')
		self.end_directory()

	def changelog_utils(self):
		fenlight_clogpath = tp('special://home/addons/plugin.video.fenlight/resources/text/changelog.txt')
		self.add({'mode': 'show_text', 'heading': 'Changelog', 'file': fenlight_clogpath, 'font_size': 'large', 'isFolder': 'false'}, 'Changelog', 'lists')
		self.add({'mode': 'show_text', 'heading': 'Kodi Log Viewer', 'file': log_loc, 'kodi_log': 'true', 'isFolder': 'false'}, 'Kodi Log Viewer', 'lists')
		self.add({'mode': 'show_text', 'heading': 'Kodi Log Viewer (Old)', 'file': old_log_loc, 'kodi_log': 'true', 'isFolder': 'false'}, 'Kodi Log Viewer (Old)', 'lists')
		self.add({'mode': 'upload_logfile', 'isFolder': 'false'}, 'Upload Kodi Log to Pastebin', 'lists')
		self.end_directory()

	def certifications(self):
		menu_type = self.params_get('menu_type')
		if menu_type == 'movie': mode, action, certifications = 'build_movie_list', 'tmdb_movies_certifications', ml.movie_certifications
		else:
			mode, certifications = 'build_tvshow_list', ml.tvshow_certifications
			if menu_type == 'tvshow': action = 'trakt_tv_certifications'
			else: action = 'trakt_anime_certifications'
		for i in certifications: self.add({'mode': mode, 'action': action, 'key_id': i['id'], 'name': i['name']}, i['name'], 'certifications')
		self.end_directory()

	def languages(self):
		menu_type = self.params_get('menu_type')
		if menu_type == 'movie': mode, action = 'build_movie_list', 'tmdb_movies_languages'
		else: mode, action = 'build_tvshow_list', 'tmdb_tv_languages'
		for i in ml.languages: self.add({'mode': mode, 'action': action, 'key_id': i['id'], 'name': i['name']}, i['name'], 'languages')
		self.end_directory()

	def years(self):
		menu_type = self.params_get('menu_type')
		if menu_type == 'movie': years, mode, action = ml.years_movies, 'build_movie_list', 'tmdb_movies_year'
		else:
			mode = 'build_tvshow_list'
			if menu_type == 'tvshow': years, action = ml.years_tvshows, 'tmdb_tv_year'
			else: years, action = ml.years_anime, 'tmdb_anime_year'
		for i in years: self.add({'mode': mode, 'action': action, 'key_id': i['id'], 'name': i['name']}, i['name'], 'calender')
		self.end_directory()

	def decades(self):
		menu_type = self.params_get('menu_type')
		if menu_type == 'movie': decades, mode, action = ml.decades_movies, 'build_movie_list', 'tmdb_movies_decade'
		else:
			mode = 'build_tvshow_list'
			if menu_type == 'tvshow': decades, action = ml.decades_tvshows, 'tmdb_tv_decade'
			else: decades, action = ml.decades_anime, 'tmdb_anime_decade'
		for i in decades: self.add({'mode': mode, 'action': action, 'key_id': i['id'], 'name': i['name']}, i['name'], 'calendar_decades')
		self.end_directory()

	def networks(self):
		menu_type = self.params_get('menu_type')
		if menu_type == 'movie': return
		mode, action, networks = 'build_tvshow_list', 'tmdb_tv_networks', sorted(ml.networks, key=lambda k: k['name'])
		for i in networks: self.add({'mode': mode, 'action': action, 'key_id': i['id'], 'name': i['name']}, i['name'], i['icon'])
		self.end_directory()

	def providers(self):
		menu_type = self.params_get('menu_type')
		image_insert = 'https://image.tmdb.org/t/p/original/%s'
		if menu_type == 'movie': mode, action, providers = 'build_movie_list', 'tmdb_movies_providers', ml.watch_providers_movies
		else:
			mode, providers = 'build_tvshow_list', ml.watch_providers_tvshows
			if menu_type == 'tvshow': action = 'tmdb_tv_providers'
			else: action = 'tmdb_anime_providers'
		for i in providers: self.add({'mode': mode, 'action': action, 'key_id': i['id'], 'name': i['name']}, i['name'], image_insert % i['icon'], original_image=True)
		self.end_directory()

	def genres(self):
		menu_type = self.params_get('menu_type')
		if menu_type == 'movie': genre_list, mode, action = ml.movie_genres, 'build_movie_list', 'tmdb_movies_genres'
		else:
			mode = 'build_tvshow_list'
			if menu_type == 'tvshow': genre_list, action = ml.tvshow_genres, 'tmdb_tv_genres'
			else: genre_list, action = ml.anime_genres, 'tmdb_anime_genres'
		for i in genre_list: self.add({'mode': mode, 'action': action, 'key_id': i['id'], 'name': i['name']}, i['name'], i['icon'])
		self.end_directory()

	def search_history(self):
		setting_id, action_dict = search_mode_dict[self.list_name]
		url_params = dict(action_dict)
		data = main_cache.get(setting_id) or []
		self.add(action_dict, '[B]NEW SEARCH...[/B]', 'search_new')
		for i in data:
			try:
				key_id = unquote(i)
				url_params['key_id'] = key_id
				url_params['setting_id'] = setting_id
				cm_items = [('[B]Remove from history[/B]', 'RunPlugin(%s)' % build_url({'mode': 'search.remove', 'setting_id':setting_id, 'key_id': key_id})),
							('[B]Clear All History[/B]', 'RunPlugin(%s)' % build_url({'mode': 'search.clear_all', 'setting_id':setting_id, 'refresh': 'true'}))]
				self.add(url_params, key_id, 'search_history', cm_items=cm_items)
			except: pass
		self.category_name = self.params_get('name') or 'History'
		self.end_directory()

	def keyword_results(self):
		from apis.tmdb_api import tmdb_keywords_by_query
		media_type, key_id = self.params_get('media_type'), self.params_get('key_id') or self.params_get('query')
		try: page_no = int(self.params_get('new_page', '1'))
		except: page_no = self.params_get('new_page')
		mode = 'build_movie_list' if media_type == 'movie' else 'build_tvshow_list'
		action = 'tmdb_movie_keyword_results' if media_type == 'movie' else 'tmdb_tv_keyword_results'
		data = tmdb_keywords_by_query(key_id, page_no)
		for item in data['results']:
			name = item['name'].upper()
			self.add({'mode': mode, 'action': action, 'key_id': item['id'], 'iconImage': 'tmdb', 'category_name': name}, name, iconImage='tmdb')
		if data['total_pages'] > page_no:
			new_page = {'mode': 'navigator.keyword_results', 'key_id': key_id, 'category_name': self.category_name, 'new_page': str(data['page'] + 1)}
			self.add(new_page, 'Next Page (%s) >>' % new_page['new_page'], 'nextpage', False)
		self.category_name = 'Search Results for %s' % key_id.upper()
		self.end_directory()

	def choose_view(self):
		handle = int(sys.argv[1])
		content = self.params['content']
		view_type, name = self.params['view_type'], self.params.get('name') or content
		self.add({'mode': 'navigator.set_view', 'view_type': view_type, 'name': name, 'isFolder': 'false'}, 'Set view and then click here', 'settings')
		set_content(handle, content)
		end_directory(handle)
		set_view_mode(view_type, content, False)

	def set_view(self):
		set_setting(self.params['view_type'], str(current_window_object().getFocusId()))
		notification('%s: %s' % (self.params['name'].upper(), get_infolabel('Container.Viewmode').upper()), time=500)

	def shortcut_folders(self):
		folders = get_shortcut_folders()
		if folders:
			for i in folders:
				name = i[0]
				convert_sr = '[B]Remove Random[/B]' if random_test in name else '[B]Make Random[/B]'
				cm_items = [('[B]Rename[/B]', run_plugin % build_url({'mode': 'menu_editor.shortcut_folder_rename'})),
							('[B]Delete Shortcut Folder[/B]' , run_plugin % build_url({'mode': 'menu_editor.shortcut_folder_delete'})),
							('[B]Make New Shortcut Folder[/B]' , run_plugin % build_url({'mode': 'menu_editor.shortcut_folder_make'})),
							(convert_sr , run_plugin % build_url({'mode': 'menu_editor.shortcut_folder_convert', 'name': name}))]
				self.add({'mode': 'navigator.build_shortcut_folder_contents', 'name': name, 'iconImage': 'folder'}, name, 'folder', cm_items=cm_items)
		else: self.add({'mode': 'menu_editor.shortcut_folder_make', 'isFolder': 'false'}, '[I]Make New Shortcut Folder...[/I]', 'new')
		self.category_name = 'Shortcut Folders'
		self.end_directory()

	def build_shortcut_folder_contents(self):
		list_name = self.params_get('name')
		is_random = random_test in list_name
		contents = get_shortcut_folder_contents(list_name)
		if is_random:
			from indexers.random_lists import random_shortcut_folders
			return random_shortcut_folders(list_name.replace(' [COLOR red][RANDOM][/COLOR]', ''), contents)
		if contents:
			for count, item in enumerate(contents):
				item_get = item.get
				iconImage = item_get('iconImage', None)
				if iconImage: icon, original_image = iconImage, True if iconImage.startswith('http') else False
				else: icon, original_image = folder_icon, False
				cm_items = [
					('[B]Move[/B]', run_plugin % build_url({'mode': 'menu_editor.shortcut_folder_edit', 'active_list': list_name, 'position': count, 'action': 'move'})),
					('[B]Remove[/B]' , run_plugin % build_url({'mode': 'menu_editor.shortcut_folder_edit', 'active_list': list_name, 'position': count, 'action': 'remove'})),
					('[B]Add Content[/B]' , run_plugin % build_url({'mode': 'menu_editor.shortcut_folder_add', 'name': list_name})),
					('[B]Rename[/B]' , run_plugin % build_url({'mode': 'menu_editor.shortcut_folder_edit', 'active_list': list_name, 'position': count, 'action': 'rename'})),
					('[B]Clear All[/B]' , run_plugin % build_url({'mode': 'menu_editor.shortcut_folder_edit', 'active_list': list_name, 'position': count, 'action': 'clear'}))]
				self.add(item, item_get('name'), icon, original_image, cm_items=cm_items)
		elif is_random: pass
		else: self.add({'mode': 'menu_editor.shortcut_folder_add', 'name': list_name, 'isFolder': 'false'}, '[I]Add Content...[/I]', 'new')
		self.end_directory()

	def discover_contents(self):
		from caches.discover_cache import discover_cache
		action, media_type = self.params_get('action', ''), self.params_get('media_type')
		if not action:
			self.add({'mode': 'discover_choice', 'media_type': media_type, 'isFolder': 'false'}, '[I]Make New Discover List...[/I]', 'new')
			results = discover_cache.get_all(media_type)
			if media_type == 'movie': mode, action = 'build_movie_list', 'tmdb_movies_discover'
			else: mode, action = 'build_tvshow_list', 'tmdb_tv_discover'
			for item in results:
				name, data = item['id'], item['data']
				cm_items = [('[B]Remove from history[/B]', 'RunPlugin(%s)' % build_url({'mode': 'navigator.discover_contents', 'action':'delete_one', 'name': name})),
							('[B]Clear All History[/B]', 'RunPlugin(%s)' % build_url({'mode': 'navigator.discover_contents', 'action':'clear_cache', 'media_type': media_type}))]
				if '[random]' in data:
					self.add({'mode': 'random.%s' % mode, 'action': action, 'name': name, 'url': data, 'new_page': 'random', 'random': 'true'},
								name, 'discover', cm_items=cm_items)
				else:
					self.add({'mode': mode, 'action': action, 'name': name, 'url': data}, name, 'discover', cm_items=cm_items)
			self.end_directory()
		else:
			if action == 'delete_one': discover_cache.delete_one(self.params_get('name'))
			elif action == 'clear_cache': discover_cache.clear_cache(media_type)
			container_refresh()

	def exit_media_menu(self):
		params = get_property('fenlight.exit_params')
		if params: return container_refresh_input(params)

	def tips(self):
		tips_location = 'special://home/addons/plugin.video.fenlight/resources/text/tips'
		files = sorted(list_dirs(tips_location)[1])
		tips_location += '/%s'
		tips_list = []
		tips_append = tips_list.append
		for item in files:
			tip = item.replace('.txt', '')[4:]
			if '!!HELP!!' in tip: tip, sort_order = tip.replace('!!HELP!!', '[COLOR crimson][B]HELP!!![/B][/COLOR] '), 0
			elif '!!NEW!!' in tip: tip, sort_order = tip.replace('!!NEW!!', '[COLOR chartreuse][B]NEW!![/B][/COLOR] '), 1
			elif '!!SPOTLIGHT!!' in tip: tip, sort_order = tip.replace('!!SPOTLIGHT!!', '[COLOR orange][B]SPOTLIGHT![/B][/COLOR] '), 2
			else: sort_order = 3
			params = {'mode': 'show_text', 'heading': tip, 'file': tp(tips_location % item), 'font_size': 'large', 'isFolder': 'false'}
			tips_append((params, tip, sort_order))
		item_list = sorted(tips_list, key=lambda x: x[2])
		for c, i in enumerate(item_list, 1): self.add(i[0], '[B]%02d. [/B]%s' % (c, i[1]), 'information')
		self.end_directory()

	def because_you_watched(self):
		recommend_type = s.recommend_service()
		menu_type = self.params_get('menu_type')
		if menu_type == 'movie':
			mode, action, media_type = 'build_movie_list', 'tmdb_movies_recommendations' if recommend_type == 0 else 'imdb_more_like_this', 'movie'
		else: mode, action, media_type = 'build_tvshow_list', 'tmdb_tv_recommendations' if recommend_type == 0 else 'imdb_more_like_this', 'episode'
		recently_watched = get_recently_watched(media_type, short_list=0)
		for item in recently_watched:
			if media_type == 'movie': name, tmdb_id = item['title'], item['media_id']
			else: name, tmdb_id = '%s - %sx%s' % (item['title'], str(item['season']), str(item['episode'])), item['media_ids']['tmdb']
			params = {'mode': mode, 'action': action, 'key_id': tmdb_id, 'name': 'Because You Watched %s' % name}
			if recommend_type == 1: params['get_imdb'] = 'true'
			self.add(params, name, 'because_you_watched')
		self.end_directory()

	def build_random_lists(self):
		menu_type = self.params_get('menu_type')
		self.category_name = 'Movie Lists' if menu_type == 'movie' else 'TV Show Lists' if menu_type == 'tvshow' else 'Anime Lists' if menu_type == 'anime' \
								else 'Trakt Lists' if menu_type == 'trakt' else 'Because You Watched Lists'
		for item in random_list_dict[menu_type](): self.add(item, item['name'], item['iconImage'])
		self.end_directory()

	def add(self, url_params, list_name, iconImage='folder', original_image=False, cm_items=[]):
		isFolder = url_params.get('isFolder', 'true') == 'true'
		if original_image: icon = iconImage
		else: icon = get_icon(iconImage)
		url_params['iconImage'] = icon
		url = build_url(url_params)
		listitem = make_listitem()
		listitem.setLabel(list_name)
		listitem.setArt({'icon': icon, 'poster': icon, 'thumb': icon, 'fanart': fanart, 'banner': icon, 'landscape': icon})
		info_tag = listitem.getVideoInfoTag()
		info_tag.setPlot(' ')
		if cm_items and not self.is_home: listitem.addContextMenuItems(cm_items)
		add_item(int(sys.argv[1]), url, listitem, isFolder)

	def end_directory(self):
		handle = int(sys.argv[1])
		set_content(handle, '')
		set_category(handle, self.category_name)
		end_directory(handle)
		set_view_mode('view.main', '')
