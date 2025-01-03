# -*- coding: utf-8 -*-
import sys
import json
import random
from threading import Thread
from apis import trakt_api
from indexers.movies import Movies
from indexers.tvshows import TVShows
from indexers.seasons import single_seasons
from indexers.episodes import build_single_episode
from modules import kodi_utils
from modules.utils import paginate_list
from modules.settings import paginate, page_limit
# logger = kodi_utils.logger

add_dir, external, sleep, get_icon = kodi_utils.add_dir, kodi_utils.external, kodi_utils.sleep, kodi_utils.get_icon
trakt_icon, fanart, add_item, set_property = get_icon('trakt'), kodi_utils.get_addon_fanart(), kodi_utils.add_item, kodi_utils.set_property
set_content, set_sort_method, set_view_mode, end_directory = kodi_utils.set_content, kodi_utils.set_sort_method, kodi_utils.set_view_mode, kodi_utils.end_directory
make_listitem, build_url, add_items = kodi_utils.make_listitem, kodi_utils.build_url, kodi_utils.add_items
nextpage_landscape, get_property, clear_property, focus_index = kodi_utils.nextpage_landscape, kodi_utils.get_property, kodi_utils.clear_property, kodi_utils.focus_index
set_category, home, folder_path = kodi_utils.set_category, kodi_utils.home, kodi_utils.folder_path
trakt_trending_popular_lists, trakt_get_lists, trakt_search_lists = trakt_api.trakt_trending_popular_lists, trakt_api.trakt_get_lists, trakt_api.trakt_search_lists
trakt_fetch_collection_watchlist, get_trakt_list_contents = trakt_api.trakt_fetch_collection_watchlist, trakt_api.get_trakt_list_contents
trakt_lists_with_media = trakt_api.trakt_lists_with_media

def search_trakt_lists(params):
	def _builder():
		for item in lists:
			try:
				list_key = item['type']
				list_info = item[list_key]
				if list_key == 'officiallist': continue
				item_count = list_info['item_count']
				if list_info['privacy'] == 'private' or item_count == 0: continue
				list_name, user, slug = list_info['name'], list_info['username'], list_info['ids']['slug']
				list_name_upper = list_name.upper()
				if not slug: continue
				cm = []
				cm_append = cm.append
				display = '%s | [I]%s (x%s)[/I]' % (list_name_upper, user, str(item_count))
				url = build_url({'mode': 'trakt.list.build_trakt_list', 'user': user, 'slug': slug, 'list_type': 'user_lists', 'list_name': list_name})
				cm_append(('[B]Like List[/B]', 'RunPlugin(%s)' % build_url({'mode': 'trakt.trakt_like_a_list', 'user': user, 'list_slug': slug})))
				cm_append(('[B]Unlike List[/B]', 'RunPlugin(%s)' % build_url({'mode': 'trakt.trakt_unlike_a_list', 'user': user, 'list_slug': slug})))
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.setArt({'icon': trakt_icon, 'poster': trakt_icon, 'thumb': trakt_icon, 'fanart': fanart, 'banner': fanart})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				listitem.addContextMenuItems(cm)
				yield (url, listitem, True)
			except: pass
	handle, search_title = int(sys.argv[1]), ''
	try:
		mode = params.get('mode')
		page = params.get('new_page', '1')
		search_title = params.get('key_id') or params.get('query')
		lists, pages = trakt_search_lists(search_title, page)
		add_items(handle, list(_builder()))
		if pages > page:
			new_page = str(int(page) + 1)
			add_dir({'mode': mode, 'key_id': search_title, 'new_page': new_page}, 'Next Page (%s) >>' % new_page, handle, 'nextpage', nextpage_landscape)
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
				list_name_upper = " ".join(w.capitalize() for w in list_name.split())
				mode = 'random.build_trakt_my_lists_contents' if randomize_contents == 'true' else 'trakt.list.build_trakt_list'
				url_params = {'mode': mode, 'user': user, 'slug': slug, 'list_type': list_type, 'list_name': list_name}
				if randomize_contents: url_params['random'] = 'true'
				elif shuffle: url_params['shuffle'] = 'true'
				url = build_url(url_params)
				if list_type == 'liked_lists':
					display = '%s | [I]%s (x%s)[/I]' % (list_name_upper, user, str(item_count))
					cm_append(('[B]Unlike List[/B]', 'RunPlugin(%s)' % build_url({'mode': 'trakt.trakt_unlike_a_list', 'user': user, 'list_slug': slug})))
				else:
					display = '%s [I](x%s)[/I]' % (list_name_upper, str(item_count))
					cm_append(('[B]Make New List[/B]', 'RunPlugin(%s)' % build_url({'mode': 'trakt.make_new_trakt_list'})))
					cm_append(('[B]Delete List[/B]', 'RunPlugin(%s)' % build_url({'mode': 'trakt.delete_trakt_list', 'user': user, 'list_slug': slug})))
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.setArt({'icon': trakt_icon, 'poster': trakt_icon, 'thumb': trakt_icon, 'fanart': fanart, 'banner': fanart})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				listitem.addContextMenuItems(cm)
				yield (url, listitem, True)
			except: pass
	handle = int(sys.argv[1])
	list_type, randomize_contents, shuffle = params['list_type'], params.get('random', 'false'), params.get('shuffle', 'false') == 'true'
	returning_to_list = False
	try:
		lists = trakt_get_lists(list_type)
		if shuffle:
			returning_to_list = 'trakt.list.build_trakt_list' in folder_path()
			if returning_to_list:
				try: lists = json.loads(get_property('fenlight.trakt.lists.order'))
				except: pass
			else:
				random.shuffle(lists)
				set_property('fenlight.trakt.lists.order', json.dumps(lists))
			sort_method = 'none'
		else:
			clear_property('fenlight.trakt.lists.order')
			sort_method = 'label'
		add_items(handle, list(_process()))
	except: pass
	set_content(handle, 'files')
	set_category(handle, params.get('category_name', ''))
	set_sort_method(handle, sort_method)
	end_directory(handle)
	set_view_mode('view.main')
	if shuffle and not returning_to_list: focus_index(0)

def get_trakt_trending_popular_lists(params):
	def _process():
		for _list in lists:
			try:
				cm = []
				cm_append = cm.append
				item = _list['list']
				item_count = item.get('item_count', 0)
				if item_count == 0: continue
				list_name, user, slug = item['name'], item['user']['ids']['slug'], item['ids']['slug']
				list_name_upper = list_name.upper()
				if not slug: continue
				if item['type'] == 'official': user = 'Trakt Official'
				if not user: continue
				display = '%s | [I]%s (x%s)[/I]' % (list_name_upper, user, str(item_count))
				url = build_url({'mode': 'trakt.list.build_trakt_list', 'user': user, 'slug': slug, 'list_type': 'user_lists', 'list_name': list_name})
				listitem = make_listitem()
				if not user == 'Trakt Official':
					cm_append(('[B]Like List[/B]', 'RunPlugin(%s)' % build_url({'mode': 'trakt.trakt_like_a_list', 'user': user, 'list_slug': slug})))
					cm_append(('[B]Unlike List[/B]', 'RunPlugin(%s)' % build_url({'mode': 'trakt.trakt_unlike_a_list', 'user': user, 'list_slug': slug})))
				listitem.addContextMenuItems(cm)
				listitem.setLabel(display)
				listitem.setArt({'icon': trakt_icon, 'poster': trakt_icon, 'thumb': trakt_icon, 'fanart': fanart, 'banner': fanart})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				yield (url, listitem, True)
			except: pass
	handle = int(sys.argv[1])
	try:
		page = params.get('new_page', '1')
		new_page = str(int(page) + 1)
		list_type = params['list_type']
		lists = trakt_trending_popular_lists(list_type, page)
		add_items(handle, list(_process()))
		add_dir({'mode': 'trakt.list.get_trakt_trending_popular_lists', 'list_type': 'trending', 'new_page': new_page},
				'Next Page (%s) >>' % new_page, handle, 'nextpage', nextpage_landscape)
	except: pass
	set_content(handle, 'files')
	set_category(handle, params.get('category_name', 'Trakt Lists'))
	end_directory(handle)
	set_view_mode('view.main')

def get_trakt_lists_with_media(params):
	def _process():
		for item in lists:
			try:
				cm = []
				cm_append = cm.append
				item_count = item.get('item_count', 0)
				list_name, user, slug = item['name'], item['user']['ids']['slug'], item['ids']['slug']
				list_name_upper = list_name.upper()
				display = '%s | [I]%s (x%s)[/I]' % (list_name_upper, user, str(item_count))
				url = build_url({'mode': 'trakt.list.build_trakt_list', 'user': user, 'slug': slug, 'list_type': 'user_lists', 'list_name': list_name})
				listitem = make_listitem()
				if not user == 'Trakt Official':
					cm_append(('[B]Like List[/B]', 'RunPlugin(%s)' % build_url({'mode': 'trakt.trakt_like_a_list', 'user': user, 'list_slug': slug})))
					cm_append(('[B]Unlike List[/B]', 'RunPlugin(%s)' % build_url({'mode': 'trakt.trakt_unlike_a_list', 'user': user, 'list_slug': slug})))
				listitem.addContextMenuItems(cm)
				listitem.setLabel(display)
				listitem.setArt({'icon': trakt_icon, 'poster': trakt_icon, 'thumb': trakt_icon, 'fanart': fanart, 'banner': fanart})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				yield (url, listitem, True)
			except: pass
	handle = int(sys.argv[1])
	try:
		lists = trakt_lists_with_media(params['media_type'], params['imdb_id'])
		add_items(handle, list(_process()))
	except: pass
	set_content(handle, 'files')
	set_category(handle, params.get('category_name', 'Trakt Lists'))
	end_directory(handle)
	set_view_mode('view.main')

def build_trakt_list(params):
	def _process(function, _list, _type):
		if not _list['list']: return
		if _type in ('movies', 'tvshows'): item_list_extend(function(_list).worker())
		elif _type == 'seasons': item_list_extend(function(_list['list']))
		else: item_list_extend(function('episode.trakt_list', _list['list']))
	def _paginate_list(data, page_no, paginate_start):
		if use_result: total_pages = 1
		elif paginate_enabled:
			limit = page_limit(is_home)
			data, total_pages = paginate_list(data, page_no, limit, paginate_start)
			if is_home: paginate_start = limit
		else: total_pages = 1
		return data, total_pages, paginate_start
	handle, is_external, is_home, content, list_name = int(sys.argv[1]), external(), home(), 'movies', params.get('list_name')
	try:
		threads, item_list = [], []
		item_list_extend = item_list.extend
		user, slug, list_type = '', '', ''
		paginate_enabled = paginate(is_home)
		use_result = 'result' in params
		page_no, paginate_start = int(params.get('new_page', '1')), int(params.get('paginate_start', '0'))
		if page_no == 1 and not is_external: set_property('fenlight.exit_params', folder_path())
		if use_result: result = params.get('result', [])
		else:
			user, slug, list_type = params.get('user'), params.get('slug'), params.get('list_type')
			with_auth = list_type == 'my_lists'
			result = get_trakt_list_contents(list_type, user, slug, with_auth)
		process_list, total_pages, paginate_start = _paginate_list(result, page_no, paginate_start)
		all_movies = [i for i in process_list if i['type'] == 'movie']
		all_tvshows = [i for i in process_list if i['type'] == 'show']
		all_seasons = [i for i in process_list if i['type'] == 'season']
		all_episodes = [i for i in process_list if i['type'] == 'episode']
		movie_list = {'list': [(i['order'], i['media_ids']) for i in all_movies], 'id_type': 'trakt_dict', 'custom_order': 'true'}
		tvshow_list = {'list': [(i['order'], i['media_ids']) for i in all_tvshows], 'id_type': 'trakt_dict', 'custom_order': 'true'}
		season_list = {'list': all_seasons}
		episode_list = {'list': all_episodes}
		content = max([('movies', len(all_movies)), ('tvshows', len(all_tvshows)), ('seasons', len(all_seasons)), ('episodes', len(all_episodes))], key=lambda k: k[1])[0]
		for item in ((Movies, movie_list, 'movies'), (TVShows, tvshow_list, 'tvshows'),
					(single_seasons, season_list, 'seasons'), (build_single_episode, episode_list, 'episodes')):
			threaded_object = Thread(target=_process, args=item)
			threaded_object.start()
			threads.append(threaded_object)
		[i.join() for i in threads]
		item_list.sort(key=lambda k: k[1])
		if use_result: return [i[0] for i in item_list]
		add_items(handle, [i[0] for i in item_list])
		if total_pages > page_no:
			new_page = str(page_no + 1)
			new_params = {'mode': 'trakt.list.build_trakt_list', 'list_type': list_type, 'list_name': list_name,
							'user': user, 'slug': slug, 'paginate_start': paginate_start, 'new_page': new_page}
			add_dir(new_params, 'Next Page (%s) >>' % new_page, handle, 'nextpage', nextpage_landscape)
	except: pass
	set_content(handle, content)
	set_category(handle, list_name)
	end_directory(handle, cacheToDisc=False if is_external else True)
	if not is_external:
		if params.get('refreshed') == 'true': sleep(1000)
		set_view_mode('view.%s' % content, content, is_external)
