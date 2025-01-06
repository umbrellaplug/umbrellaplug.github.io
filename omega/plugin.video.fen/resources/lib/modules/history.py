# -*- coding: utf-8 -*-
from datetime import timedelta
from caches.main_cache import main_cache
from indexers.people import person_search
from modules import kodi_utils
from modules.settings import use_year_in_search
# logger = kodi_utils.logger

json, ls, close_all_dialog, external = kodi_utils.json, kodi_utils.local_string, kodi_utils.close_all_dialog, kodi_utils.external
build_url, dialog, unquote, execute_builtin, select_dialog = kodi_utils.build_url, kodi_utils.dialog, kodi_utils.unquote, kodi_utils.execute_builtin, kodi_utils.select_dialog
notification, kodi_refresh, numeric_input = kodi_utils.notification, kodi_utils.kodi_refresh, kodi_utils.numeric_input
insert_string_4, insert_string_5 = '%s %s %s %s', '%s %s %s %s %s'
delete_str, search_str, hist_str, vid_str, mov_str, key_str = ls(32785), ls(32450), ls(32486), ls(32491), ls(32028), ls(32092)
tv_str, furk_str, easy_str, peop_str, imdb_str, coll_str = ls(32029), ls(32069), ls(32070), ls(32507), ls(32064), ls(33080)
clear_history_list = [(insert_string_4 % (delete_str, mov_str, search_str, hist_str), 'movie_queries'),
					(insert_string_4 % (delete_str, tv_str, search_str, hist_str), 'tvshow_queries'), 
					(insert_string_4 % (delete_str, peop_str, search_str, hist_str), 'people_queries'),
					(insert_string_5 % (delete_str, imdb_str, key_str, mov_str, hist_str), 'keyword_imdb_movie_queries'),
					(insert_string_5 % (delete_str, imdb_str, key_str, tv_str, hist_str), 'keyword_imdb_tvshow_queries'),
					(insert_string_5 % (delete_str, furk_str, vid_str, search_str, hist_str), 'furk_video_queries'), 
					(insert_string_4 % (delete_str, easy_str, search_str, hist_str), 'easynews_video_queries'), 
					(insert_string_4 % (delete_str, coll_str, search_str, hist_str), 'tmdb_movie_sets_queries')]

def get_search_term(params):
	close_all_dialog()
	media_type = params.get('media_type', '')
	search_type = params.get('search_type', 'media_title')
	string = None
	if search_type == 'media_title':
		mode, action, string = ('build_movie_list', 'tmdb_movies_search', 'movie_queries') if media_type == 'movie' else ('build_tvshow_list', 'tmdb_tv_search', 'tvshow_queries')
		url_params = {'mode': mode, 'action': action}
	elif search_type == 'people': string = 'people_queries'
	elif search_type == 'imdb_keyword':
		url_params, string = {'mode': 'imdb_build_keyword_results', 'media_type': media_type}, 'keyword_imdb_%s_queries' % media_type
	elif search_type == 'furk_direct':
		url_params, string = {'mode': 'furk.search_furk', 'media_type': media_type}, 'furk_video_queries'
	elif search_type == 'easynews_video':
		url_params, string = {'mode': 'easynews.search_easynews'}, 'easynews_video_queries'
	elif search_type == 'tmdb_movie_sets':
		url_params, string = {'mode': 'build_movie_list', 'action': 'tmdb_movies_search_sets'}, 'tmdb_movie_sets_queries'
	elif search_type == 'trakt_lists':
		url_params, string = {'mode': 'trakt.list.search_trakt_lists'}, ''
	params_query = params.get('query', None)
	query = params_query or dialog.input('')
	if not query: return
	query = unquote(query)
	if search_type == 'media_title' and not params_query and use_year_in_search():
		year = dialog.input('%s (%s)' % (ls(32543), ls(32669)), type=numeric_input)
		if year: query = '%s|%s' % (query, year)
	if string: add_to_search_history(query, string)
	if search_type == 'people':
		kodi_refresh()
		return person_search(query)
	url_params['query'] = query
	action = 'ActivateWindow(Videos,%s,return)' if external() else 'Container.Update(%s)'
	return execute_builtin(action % build_url(url_params))

def add_to_search_history(search_name, search_list):
	try:
		result = []
		cache = main_cache.get(search_list)
		if cache: result = cache
		if search_name in result: result.remove(search_name)
		result.insert(0, search_name)
		result = result[:50]
		main_cache.set(search_list, result, expiration=timedelta(days=365))
	except: return

def remove_from_search_history(params):
	try:
		result = main_cache.get(params['setting_id'])
		result.remove(params.get('query'))
		main_cache.set(params['setting_id'], result, expiration=timedelta(days=365))
		notification(32576, 2500)
		kodi_refresh()
	except: return

def clear_search_history():
	try:
		list_items = [{'line1': item[0]} for item in clear_history_list]
		kwargs = {'items': json.dumps(list_items), 'narrow_window': 'true'}
		setting_id = select_dialog([item[1] for item in clear_history_list], **kwargs)
		if setting_id == None: return
		clear_all_history(setting_id)
	except: return

def clear_all_history(setting_id, refresh='false'):
	main_cache.set(setting_id, '', expiration=timedelta(days=365))
	notification(32576, 2500)
	if refresh == 'true': kodi_refresh()

	