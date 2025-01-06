# -*- coding: utf-8 -*-
from caches.main_cache import main_cache
from modules import kodi_utils
# logger = kodi_utils.logger

add_dir, add_items, set_content, end_directory = kodi_utils.add_dir, kodi_utils.add_items, kodi_utils.set_content, kodi_utils.end_directory
ls, sys, build_url, make_listitem, get_icon = kodi_utils.local_string, kodi_utils.sys, kodi_utils.build_url, kodi_utils.make_listitem, kodi_utils.get_icon
set_view_mode, unquote, set_category, icon, fanart = kodi_utils.set_view_mode, kodi_utils.unquote, kodi_utils.set_category, get_icon('search_history'), kodi_utils.addon_fanart
history_str, remove_str, remove_all_str = '[B]%s:[/B] [I]%s[/I]' % (ls(32486).upper(), '%s'), ls(32786), '[B]%s[/B]' % ls(32699)
new_search_str = '[B]%s %s...[/B]' % (ls(32857).upper(), ls(32450).upper())
mode_dict = {'movie': ('movie_queries', {'mode': 'get_search_term', 'media_type': 'movie'}),
			'tvshow': ('tvshow_queries', {'mode': 'get_search_term', 'media_type': 'tv_show'}),
			'people': ('people_queries', {'mode': 'get_search_term', 'search_type': 'people'}),
			'tmdb_movie_sets': ('tmdb_movie_sets_queries', {'mode': 'get_search_term', 'search_type': 'tmdb_movie_sets', 'media_type': 'movie'}),
			'imdb_keyword_movie': ('keyword_imdb_movie_queries', {'mode': 'get_search_term', 'search_type': 'imdb_keyword', 'media_type': 'movie'}),
			'imdb_keyword_tvshow': ('keyword_imdb_tvshow_queries', {'mode': 'get_search_term', 'search_type': 'imdb_keyword', 'media_type': 'tvshow'}),
			'furk_video': ('furk_video_queries', {'mode': 'get_search_term', 'search_type': 'furk_direct', 'media_type': 'video'}),
			'easynews_video': ('easynews_video_queries', {'mode': 'get_search_term', 'search_type': 'easynews_video'})}

def search_history(params):
	def _builder():
		for i in main_cache.get(setting_id):
			try:
				cm = []
				query = unquote(i)
				url_params['query'] = query
				url_params['setting_id'] = setting_id
				if '|' in query: display = history_str % '%s (%s)' % tuple(query.split('|'))
				else: display = history_str % query
				url = build_url(url_params)
				cm.append((remove_str, 'RunPlugin(%s)' % build_url({'mode': 'history.remove', 'setting_id':setting_id, 'query': query})))
				cm.append((remove_all_str, 'RunPlugin(%s)' % build_url({'mode': 'history.clear_all', 'setting_id':setting_id, 'refresh': 'true'})))
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt({'icon': icon, 'poster': icon, 'thumb': icon, 'fanart': fanart, 'banner': icon})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				listitem.setProperty('fen.context_main_menu_params', build_url({'mode': 'menu_editor.edit_menu_external'}))
				yield (url, listitem, False)
			except: pass
	handle = int(sys.argv[1])
	setting_id, action_dict = mode_dict[params['action']]
	url_params = dict(action_dict)
	add_dir(action_dict, new_search_str, handle, iconImage='search_new', isFolder=False)
	try: add_items(handle, list(_builder()))
	except: pass
	set_content(handle, '')
	set_category(handle, params.get('name') or ls(32486))
	end_directory(handle, False)
	set_view_mode('view.main', '')
	