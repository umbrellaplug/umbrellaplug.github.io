# -*- coding: utf-8 -*-
import json
from urllib.parse import unquote
from caches.main_cache import main_cache
from indexers.people import person_search
from indexers.easynews import search_easynews_image
from modules import kodi_utils
# logger = kodi_utils.logger

close_all_dialog, external = kodi_utils.close_all_dialog, kodi_utils.external
build_url, kodi_dialog, execute_builtin, select_dialog = kodi_utils.build_url, kodi_utils.kodi_dialog, kodi_utils.execute_builtin, kodi_utils.select_dialog
notification, kodi_refresh = kodi_utils.notification, kodi_utils.kodi_refresh
clear_history_list = [('Clear Movie Search History', 'movie_queries'),
					('Clear TV Show Search History', 'tvshow_queries'),
					('Clear Anime Search History', 'anime_queries'),
					('Clear People Search History', 'people_queries'),
					('Clear Keywords Movie Search History', 'keyword_tmdb_movie_queries'),
					('Clear Keywords TV Show Search History', 'keyword_tmdb_tvshow_queries'),
					('Clear Easynews Search History', 'easynews_video_queries'),
					('Clear Easynews Search History', 'easynews_image_queries'),
					('Clear Trakt List Search History', 'trakt_list_queries')]

def get_key_id(params):
	close_all_dialog()
	params_key_id = params.get('key_id', None)
	key_id = params_key_id or kodi_dialog().input('')
	if not key_id: return
	key_id = unquote(key_id)
	media_type = params.get('media_type', '')
	search_type = params.get('search_type', 'media_title')
	string = None
	if search_type == 'media_title':
		if media_type == 'movie': url_params, string = {'mode': 'build_movie_list', 'action': 'tmdb_movies_search'}, 'movie_queries'
		elif media_type == 'tv_show': url_params, string = {'mode': 'build_tvshow_list', 'action': 'tmdb_tv_search'}, 'tvshow_queries'
		else: url_params, string = {'mode': 'build_tvshow_list', 'action': 'tmdb_anime_search'}, 'anime_queries'
	elif search_type == 'people': string = 'people_queries'
	elif search_type == 'tmdb_keyword':
		url_params, string = {'mode': 'navigator.keyword_results', 'media_type': media_type}, 'keyword_tmdb_%s_queries' % media_type
	elif search_type == 'easynews_video':
		url_params, string = {'mode': 'easynews.search_easynews'}, 'easynews_video_queries'
	elif search_type == 'easynews_image':
		url_params, string = {'mode': 'easynews.search_easynews_image'}, 'easynews_image_queries'
	elif search_type == 'trakt_lists':
		url_params, string = {'mode': 'trakt.list.search_trakt_lists'}, 'trakt_list_queries'
	if string: add_to_search(key_id, string)
	if search_type == 'people': return person_search(key_id)
	if search_type == 'easynews_image': return search_easynews_image(key_id)
	url_params.update({'query': key_id, 'key_id': key_id, 'name': 'Search Results for %s' % key_id})
	action = 'ActivateWindow(Videos,%s,return)' if external() else 'Container.Update(%s)'
	return execute_builtin(action % build_url(url_params))

def add_to_search(search_name, search_list):
	try:
		result = []
		cache = main_cache.get(search_list)
		if cache: result = cache
		if search_name in result: result.remove(search_name)
		result.insert(0, search_name)
		result = result[:50]
		main_cache.set(search_list, result, expiration=8760)
	except: return

def remove_from_search(params):
	try:
		result = main_cache.get(params['setting_id'])
		result.remove(params.get('key_id'))
		main_cache.set(params['setting_id'], result, expiration=8760)
		notification('Success', 2500)
		kodi_refresh()
	except: return

def clear_search():
	try:
		list_items = [{'line1': item[0]} for item in clear_history_list]
		kwargs = {'items': json.dumps(list_items), 'narrow_window': 'true'}
		setting_id = select_dialog([item[1] for item in clear_history_list], **kwargs)
		if setting_id == None: return
		clear_all(setting_id)
	except: return

def clear_all(setting_id, refresh='false'):
	main_cache.set(setting_id, '', expiration=365)
	notification('Success', 2500)
	if refresh == 'true': kodi_refresh()

	