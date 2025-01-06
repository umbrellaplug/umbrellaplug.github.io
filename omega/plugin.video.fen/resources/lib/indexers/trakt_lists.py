# -*- coding: utf-8 -*-
from apis import trakt_api
from indexers.movies import Movies
from indexers.tvshows import TVShows
from modules import kodi_utils
from modules.utils import paginate_list, sort_for_article
from modules.settings import paginate, page_limit, jump_to_enabled, ignore_articles
# logger = kodi_utils.logger

ls, sys, make_listitem, build_url, Thread, add_items = kodi_utils.local_string, kodi_utils.sys, kodi_utils.make_listitem, kodi_utils.build_url, kodi_utils.Thread, kodi_utils.add_items
add_dir, external, dialog, sleep, json, get_icon = kodi_utils.add_dir, kodi_utils.external, kodi_utils.dialog, kodi_utils.sleep, kodi_utils.json, kodi_utils.get_icon
trakt_icon, fanart, add_item, set_property = get_icon('trakt'), kodi_utils.addon_fanart, kodi_utils.add_item, kodi_utils.set_property
set_content, set_sort_method, set_view_mode, end_directory = kodi_utils.set_content, kodi_utils.set_sort_method, kodi_utils.set_view_mode, kodi_utils.end_directory
set_category, home, folder_path = kodi_utils.set_category, kodi_utils.home, kodi_utils.folder_path
trakt_fetch_collection_watchlist, get_trakt_list_contents = trakt_api.trakt_fetch_collection_watchlist, trakt_api.get_trakt_list_contents
trakt_trending_popular_lists, trakt_get_lists = trakt_api.trakt_trending_popular_lists, trakt_api.trakt_get_lists
trakt_search_lists, trakt_fetch_movie_sets = trakt_api.trakt_search_lists, trakt_api.trakt_fetch_movie_sets
nextpage_landscape = kodi_utils.nextpage_landscape
add2menu_str, add2folder_str, likelist_str, unlikelist_str = ls(32730), ls(32731), ls(32776), ls(32783)
newlist_str, deletelist_str, nextpage_str, jump2_str = ls(32780), ls(32781), ls(32799), ls(32964)

def search_trakt_lists(params):
	def _builder():
		for item in lists:
			try:
				list_key = item['type']
				list_info = item[list_key]
				if list_key == 'officiallist': continue
				item_count = list_info['item_count']
				if list_info['privacy'] in ('private', 'friends') or item_count == 0: continue
				list_name, user, slug = list_info['name'], list_info['username'], list_info['ids']['slug']
				list_name_upper = list_name.upper()
				if not slug: continue
				cm = []
				cm_append = cm.append
				display = '%s | [I]%s (x%s)[/I]' % (list_name_upper, user, str(item_count))
				editor_display = '%s | %s' % (list_name_upper, user)
				url = build_url({'mode': 'trakt.list.build_trakt_list', 'user': user, 'slug': slug, 'list_type': 'user_lists', 'list_name': list_name})
				cm_append((add2menu_str,'RunPlugin(%s)' % build_url({'mode': 'menu_editor.add_external', 'name': editor_display, 'iconImage': 'trakt'})))
				cm_append((add2folder_str,'RunPlugin(%s)' % build_url({'mode': 'menu_editor.shortcut_folder_add_item', 'name': editor_display, 'iconImage': 'trakt'})))
				cm_append((likelist_str,'RunPlugin(%s)' % build_url({'mode': 'trakt.trakt_like_a_list', 'user': user, 'list_slug': slug})))
				cm_append((unlikelist_str,'RunPlugin(%s)' % build_url({'mode': 'trakt.trakt_unlike_a_list', 'user': user, 'list_slug': slug})))
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.setArt({'icon': trakt_icon, 'poster': trakt_icon, 'thumb': trakt_icon, 'fanart': fanart, 'banner': trakt_icon})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				listitem.addContextMenuItems(cm)
				listitem.setProperty('fen.context_main_menu_params', build_url({'mode': 'menu_editor.edit_menu_external', 'name': editor_display, 'iconImage': 'trakt'}))
				yield (url, listitem, True)
			except: pass
	handle, search_title = int(sys.argv[1]), ''
	try:
		mode = params.get('mode')
		page = params.get('new_page', '1')
		search_title = params.get('query')
		lists, pages = trakt_search_lists(search_title, page)
		add_items(handle, list(_builder()))
		if pages > page:
			new_page = str(int(page) + 1)
			add_dir({'mode': mode, 'query': search_title, 'new_page': new_page}, nextpage_str % new_page, handle, 'nextpage', nextpage_landscape)
	except: pass
	set_content(handle, 'files')
	set_category(handle, search_title.capitalize())
	end_directory(handle)
	set_view_mode('view.main')

def get_trakt_lists(params):
	def _process():
		for item in lists:
			try:
				if list_type == 'liked_lists': item = item['list']
				cm = []
				cm_append = cm.append
				list_name, user, slug, item_count = item['name'], item['user']['ids']['slug'], item['ids']['slug'], item['item_count']
				list_name_upper = list_name.upper()
				url = build_url({'mode': 'trakt.list.build_trakt_list', 'user': user, 'slug': slug, 'list_type': list_type, 'list_name': list_name})
				if list_type == 'liked_lists':
					display = '%s | [I]%s (x%s)[/I]' % (list_name_upper, user, str(item_count))
					editor_display = '%s | %s' % (list_name_upper, user)
					cm_append((unlikelist_str,'RunPlugin(%s)' % build_url({'mode': 'trakt.trakt_unlike_a_list', 'user': user, 'list_slug': slug})))
				else:
					display = '%s [I](x%s)[/I]' % (list_name_upper, str(item_count))
					editor_display = list_name
					cm_append((newlist_str,'RunPlugin(%s)' % build_url({'mode': 'trakt.make_new_trakt_list'})))
					cm_append((deletelist_str,'RunPlugin(%s)' % build_url({'mode': 'trakt.delete_trakt_list', 'user': user, 'list_slug': slug})))
				cm_append((add2menu_str,'RunPlugin(%s)' % build_url({'mode': 'menu_editor.add_external', 'name': editor_display, 'iconImage': 'trakt'})))
				cm_append((add2folder_str,'RunPlugin(%s)' % build_url({'mode': 'menu_editor.shortcut_folder_add_item', 'name': editor_display, 'iconImage': 'trakt'})))
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.setArt({'icon': trakt_icon, 'poster': trakt_icon, 'thumb': trakt_icon, 'fanart': fanart, 'banner': trakt_icon})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				listitem.addContextMenuItems(cm)
				listitem.setProperty('fen.context_main_menu_params', build_url({'mode': 'menu_editor.edit_menu_external', 'name': editor_display, 'iconImage': 'trakt'}))
				yield (url, listitem, True)
			except: pass
	handle = int(sys.argv[1])
	try:
		list_type = params['list_type']
		lists = trakt_get_lists(list_type)
		add_items(handle, list(_process()))
	except: pass
	set_content(handle, 'files')
	set_category(handle, params.get('category_name', ''))
	set_sort_method(handle, 'label')
	end_directory(handle)
	set_view_mode('view.main')

def get_trakt_trending_popular_lists(params):
	def _process():
		for _list in lists:
			try:
				cm = []
				cm_append = cm.append
				item = _list['list']
				item_count = item.get('item_count', 0)
				if item['user']['private'] or item_count == 0: continue
				list_name, user, slug = item['name'], item['user']['ids']['slug'], item['ids']['slug']
				list_name_upper = list_name.upper()
				if not slug: continue
				if item['type'] == 'official': user = 'Trakt Official'
				if not user: continue
				display = '%s | [I]%s (x%s)[/I]' % (list_name_upper, user, str(item_count))
				editor_display = '%s | %s' % (list_name_upper, user)
				url = build_url({'mode': 'trakt.list.build_trakt_list', 'user': user, 'slug': slug, 'list_type': 'user_lists', 'list_name': list_name})
				listitem = make_listitem()
				cm_append((add2menu_str,'RunPlugin(%s)' % build_url({'mode': 'menu_editor.add_external', 'name': editor_display, 'iconImage': 'trakt'})))
				cm_append((add2folder_str,'RunPlugin(%s)' % build_url({'mode': 'menu_editor.shortcut_folder_add_item', 'name': editor_display, 'iconImage': 'trakt'})))
				if not user == 'Trakt Official':
					cm_append((likelist_str,'RunPlugin(%s)' % build_url({'mode': 'trakt.trakt_like_a_list', 'user': user, 'list_slug': slug})))
					cm_append((unlikelist_str,'RunPlugin(%s)' % build_url({'mode': 'trakt.trakt_unlike_a_list', 'user': user, 'list_slug': slug})))
				listitem.addContextMenuItems(cm)
				listitem.setLabel(display)
				listitem.setArt({'icon': trakt_icon, 'poster': trakt_icon, 'thumb': trakt_icon, 'fanart': fanart, 'banner': trakt_icon})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				listitem.setProperty('fen.context_main_menu_params', build_url({'mode': 'menu_editor.edit_menu_external', 'name': editor_display, 'iconImage': 'trakt'}))
				yield (url, listitem, True)
			except: pass
	handle = int(sys.argv[1])
	try:
		page = params.get('new_page', '1')
		new_page = str(int(page) + 1)
		list_type = params['list_type']
		lists = trakt_trending_popular_lists(list_type, page)
		add_items(handle, list(_process()))
		add_dir({'mode': 'trakt.list.get_trakt_trending_popular_lists', 'list_type': 'trending', 'new_page': new_page}, nextpage_str % new_page,
					handle, 'nextpage', nextpage_landscape)
	except: pass
	set_content(handle, 'files')
	set_category(handle, params.get('category_name', 'Trakt Lists'))
	end_directory(handle)
	set_view_mode('view.main')

def build_trakt_list(params):
	def _process(function, _list):
		item_list_extend(function(_list).worker())
	def _paginate_list(data, page_no, paginate_start):
		if paginate(is_home):
			limit = page_limit(is_home)
			data, all_pages, total_pages = paginate_list(data, page_no, limit, paginate_start)
			if is_home: paginate_start = limit
		else: all_pages, total_pages = '', 1
		return data, all_pages, total_pages, paginate_start
	handle, is_external, is_home, content, list_name = int(sys.argv[1]), external(), home(), 'movies', params.get('list_name')
	try:
		threads, item_list = [], []
		item_list_extend = item_list.extend
		user, slug, list_type = params.get('user'), params.get('slug'), params.get('list_type')
		page_no, paginate_start = int(params.get('new_page', '1')), int(params.get('paginate_start', '0'))
		if page_no == 1 and not is_external: set_property('fen.exit_params', folder_path())
		with_auth = list_type == 'my_lists'
		result = get_trakt_list_contents(list_type, user, slug, with_auth)
		process_list, all_pages, total_pages, paginate_start = _paginate_list(result, page_no, paginate_start)
		new_params = {'mode': 'trakt.list.build_trakt_list', 'list_type': list_type, 'list_name': list_name,
						'user': user, 'slug': slug, 'paginate_start': paginate_start}
		movie_list = {'list': [(i['order'], i['media_ids']) for i in process_list if i['type'] == 'movie'], 'id_type': 'trakt_dict', 'custom_order': 'true'}
		tvshow_list = {'list': [(i['order'], i['media_ids']) for i in process_list if i['type'] == 'show'], 'id_type': 'trakt_dict', 'custom_order': 'true'}
		content = 'movies' if len(movie_list['list']) > len(tvshow_list['list']) else 'tvshows'
		for item in ((Movies, movie_list), (TVShows, tvshow_list)):
			if not item[1]['list']: continue
			threaded_object = Thread(target=_process, args=item)
			threaded_object.start()
			threads.append(threaded_object)
		[i.join() for i in threads]
		item_list.sort(key=lambda k: k[1])
		add_items(handle, [i[0] for i in item_list])
		if total_pages > 2 and not is_external:
				jump_to = jump_to_enabled()
				if jump_to != 3:
					add_dir({'mode': 'navigate_to_page_choice', 'current_page': page_no, 'total_pages': total_pages, 'all_pages': all_pages,
							'jump_to_enabled': jump_to, 'paginate_start': paginate_start, 'url_params': json.dumps(new_params)},
							jump2_str, handle, 'item_jump', isFolder=False)
		if total_pages > page_no:
			new_page = str(page_no + 1)
			new_params['new_page'] = new_page
			add_dir(new_params, nextpage_str % new_page, handle, 'nextpage', nextpage_landscape)
	except: pass
	set_content(handle, content)
	set_category(handle, list_name)
	end_directory(handle, False if is_external else None)
	if not is_external:
		if params.get('refreshed') == 'true': sleep(1000)
		set_view_mode('view.%s' % content, content, is_external)

def build_trakt_movie_sets(params):
	handle, content, is_external = int(sys.argv[1]), 'movies', external()
	try: add_items(handle, Movies({'list': [i['id'] for i in sort_for_article(trakt_fetch_movie_sets(), 'title', ignore_articles())]}).movie_sets_worker())
	except: pass
	set_content(handle, content)
	set_category(handle, params.get('category_name', ''))
	end_directory(handle, False if is_external else None)
	set_view_mode('view.%s' % content, content, is_external)
