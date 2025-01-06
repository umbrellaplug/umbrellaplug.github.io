# -*- coding: utf-8 -*-
from modules import kodi_utils, settings
from modules.metadata import tvshow_meta
from modules.utils import manual_function_import, get_datetime, make_thread_list_enumerate, make_thread_list_multi_arg, get_current_timestamp, paginate_list
from modules.watched_status import get_watched_info_tv, get_watched_status_tvshow
# logger = kodi_utils.logger

sleep, meta_function, get_datetime_function, add_item, xbmc_actor, home = kodi_utils.sleep, tvshow_meta, get_datetime, kodi_utils.add_item, kodi_utils.xbmc_actor, kodi_utils.home
get_watched_function, get_watched_info_function, set_category, json = get_watched_status_tvshow, get_watched_info_tv, kodi_utils.set_category, kodi_utils.json
set_content, end_directory, set_view_mode, folder_path = kodi_utils.set_content, kodi_utils.end_directory, kodi_utils.set_view_mode, kodi_utils.folder_path
string, ls, sys, external, add_items, add_dir = str, kodi_utils.local_string, kodi_utils.sys, kodi_utils.external, kodi_utils.add_items, kodi_utils.add_dir
make_listitem, build_url, remove_keys, dict_removals = kodi_utils.make_listitem, kodi_utils.build_url, kodi_utils.remove_keys, kodi_utils.tvshow_dict_removals
metadata_user_info, watched_indicators, jump_to_enabled, paginate = settings.metadata_user_info, settings.watched_indicators, settings.jump_to_enabled, settings.paginate
extras_open_action, get_art_provider, default_all_episodes, page_limit = settings.extras_open_action, settings.get_art_provider, settings.default_all_episodes, settings.page_limit
poster_empty, fanart_empty, include_year_in_title, set_property = kodi_utils.empty_poster, kodi_utils.addon_fanart, settings.include_year_in_title, kodi_utils.set_property
nextpage_landscape = kodi_utils.nextpage_landscape
max_threads, widget_hide_next_page = settings.max_threads, settings.widget_hide_next_page
fen_str, trakt_str, watched_str, unwatched_str, exit_str, nextpage_str, browse_str, jump2_str = ls(32036), ls(32037), ls(32642), ls(32643), ls(32650), ls(32799), ls(33137), ls(32964)
extras_str, options_str, refr_widg_str = ls(32645), ls(32646), '[B]%s[/B]' % ls(32611)
run_plugin, container_update = 'RunPlugin(%s)', 'Container.Update(%s)'
tmdb_main = ('tmdb_tv_popular', 'tmdb_tv_popular_today', 'tmdb_tv_premieres', 'tmdb_tv_airing_today','tmdb_tv_on_the_air','tmdb_tv_upcoming')
tmdb_special = {'tmdb_tv_languages': 'language', 'tmdb_tv_networks': 'network_id', 'tmdb_tv_year': 'year', 'tmdb_tv_decade': 'decade', 'tmdb_tv_recommendations': 'tmdb_id',
					'tmdb_tv_genres': 'genre_id', 'tmdb_tv_search': 'query'}
trakt_main = ('trakt_tv_trending', 'trakt_tv_trending_recent', 'trakt_recommendations', 'trakt_tv_most_watched')
trakt_personal = ('trakt_collection', 'trakt_watchlist', 'trakt_collection_lists', 'trakt_favorites')
imdb_all = ('imdb_watchlist', 'imdb_user_list_contents', 'imdb_keywords_list_contents')
personal = {'in_progress_tvshows': ('modules.watched_status', 'get_in_progress_tvshows'), 'favorites_tvshows': ('modules.favorites', 'get_favorites'),
				'watched_tvshows': ('modules.watched_status', 'get_watched_items')}
view_mode, content_type = 'view.tvshows', 'tvshows'
internal_nav_check = ('build_season_list', 'build_episode_list')

class TVShows:
	def __init__(self, params):
		self.params = params
		self.params_get = self.params.get
		self.category_name = self.params_get('category_name', None) or self.params_get('name', None) or 32029
		self.id_type, self.list, self.action = self.params_get('id_type', 'tmdb_id'), self.params_get('list', []), self.params_get('action', None)
		self.items, self.new_page, self.total_pages, self.is_external, self.is_home, self.max_threads = [], {}, None, external(), home(), max_threads()
		self.widget_hide_next_page = False if not self.is_home else widget_hide_next_page()
		self.custom_order = self.params_get('custom_order', 'false') == 'true'
		self.paginate_start = int(self.params_get('paginate_start', '0'))
		self.in_progress_menu = 'true' if self.action == 'in_progress_tvshows' else 'false'
		self.append = self.items.append
	
	def fetch_list(self):
		handle = int(sys.argv[1])
		try:
			mode = self.params_get('mode')
			try: page_no = int(self.params_get('new_page', '1'))
			except: page_no = self.params_get('new_page')
			if page_no == 1 and not self.is_external:
				folderpath = folder_path()
				if not any([x in folderpath for x in internal_nav_check]): set_property('fen.exit_params', folderpath)
			if self.action in personal: var_module, import_function = personal[self.action]
			else: var_module, import_function = 'apis.%s_api' % self.action.split('_')[0], self.action
			try: function = manual_function_import(var_module, import_function)
			except: pass
			if self.action in tmdb_main:
				data = function(page_no)
				self.list = [i['id'] for i in data['results']]
				if data['total_pages'] > page_no: self.new_page = {'new_page': string(page_no + 1)}
			elif self.action in tmdb_special:
				key = tmdb_special[self.action]
				function_var = self.params_get(key, None)
				if not function_var: return
				data = function(function_var, page_no)
				self.list = [i['id'] for i in data['results']]
				if data['total_pages'] > page_no: self.new_page = {'new_page': string(page_no + 1), key: function_var}
			elif self.action in personal:
				data = function('tvshow', page_no)
				data, all_pages, total_pages = self.paginate_list(data, page_no)
				self.list = [i['media_id'] for i in data]
				if total_pages > 2: self.total_pages = total_pages
				if total_pages > page_no: self.new_page = {'new_page': string(page_no + 1), 'paginate_start': self.paginate_start}
			elif self.action in trakt_main:
				self.id_type = 'trakt_dict'
				data = function(page_no)
				try: self.list = [i['show']['ids'] for i in data]
				except: self.list = [i['ids'] for i in data]
				if self.action != 'trakt_recommendations': self.new_page = {'new_page': string(page_no + 1)}
			elif self.action in trakt_personal:
				self.id_type = 'trakt_dict'
				data = function('shows', page_no)
				if self.action in ('trakt_collection_lists', 'trakt_favorites'): all_pages, total_pages = '', 1
				else: data, all_pages, total_pages = self.paginate_list(data, page_no)
				self.list = [i['media_ids'] for i in data]
				if total_pages > 2: self.total_pages = total_pages
				try:
					if total_pages > page_no: self.new_page = {'new_page': string(page_no + 1), 'paginate_start': self.paginate_start}
				except: pass
			elif self.action in imdb_all:
				self.id_type = 'imdb_id'
				list_id = self.params_get('list_id', None)
				data, next_page = function('tvshow', list_id, page_no)
				self.list = [i['imdb_id'] for i in data]
				if next_page: self.new_page = {'list_id': list_id, 'new_page': string(page_no + 1)}
			elif self.action == 'tmdb_tv_discover':
				from indexers.discover import set_history
				name, query = self.params['name'], self.params['query']
				if page_no == 1: set_history('tvshow', name, query)
				data = function(query, page_no)
				self.list = [i['id'] for i in data['results']]
				if data['page'] < data['total_pages']: self.new_page = {'query': query, 'name': name, 'new_page': string(data['page'] + 1)}
			elif self.action == 'trakt_tv_certifications':
				self.id_type = 'trakt_dict'
				data = function(self.params['certification'], page_no)
				self.list = [i['show']['ids'] for i in data]
				self.new_page = {'new_page': string(page_no + 1), 'certification': self.params['certification']}
			add_items(handle, self.worker())
			if self.total_pages and not self.is_external:
				jump_to = jump_to_enabled()
				if jump_to != 3:
					url_params = json.dumps({**self.new_page, **{'mode': mode, 'action': self.action, 'category_name': self.category_name}})
					add_dir({'mode': 'navigate_to_page_choice', 'current_page': page_no, 'total_pages': self.total_pages, 'all_pages': all_pages,
							'jump_to_enabled': jump_to, 'paginate_start': self.paginate_start, 'url_params': url_params}, jump2_str, handle, 'item_jump', isFolder=False)
			if self.new_page and not self.widget_hide_next_page:
						self.new_page.update({'mode': mode, 'action': self.action, 'category_name': self.category_name})
						add_dir(self.new_page, nextpage_str % self.new_page['new_page'], handle, 'nextpage', nextpage_landscape)
		except: pass
		set_content(handle, content_type)
		set_category(handle, ls(self.category_name))
		end_directory(handle, False if self.is_external else None)
		if not self.is_external:
			if self.params_get('refreshed') == 'true': sleep(1000)
			set_view_mode(view_mode, content_type, self.is_external)

	def build_tvshow_content(self, _position, _id):
		try:
			meta = meta_function(self.id_type, _id, self.meta_user_info, self.current_date, self.current_time)
			if not meta or 'blank_entry' in meta: return
			meta_get = meta.get
			tmdb_id, total_seasons, total_aired_eps = meta_get('tmdb_id'), meta_get('total_seasons'), meta_get('total_aired_eps')
			playcount, overlay, total_watched, total_unwatched = get_watched_function(self.watched_info, string(tmdb_id), total_aired_eps)
			if total_watched:
				try: progress = int((float(total_watched)/total_aired_eps)*100) or 1
				except: progress = 1
			else: progress = 0
			cm = []
			cm_append = cm.append
			listitem = make_listitem()
			set_properties = listitem.setProperties
			rootname, trailer, title, year = meta_get('rootname'), meta_get('trailer'), meta_get('title'), meta_get('year') or '2050'
			tvdb_id, imdb_id = meta_get('tvdb_id'), meta_get('imdb_id')
			poster = meta_get('custom_poster') or meta_get(self.poster_main) or meta_get(self.poster_backup) or poster_empty
			fanart = meta_get('custom_fanart') or meta_get(self.fanart_main) or meta_get(self.fanart_backup) or fanart_empty
			clearlogo = meta_get('custom_clearlogo') or meta_get(self.clearlogo_main) or meta_get(self.clearlogo_backup) or ''
			if self.fanart_enabled:
				banner, clearart = meta_get('custom_banner') or meta_get('banner') or '', meta_get('custom_clearart') or meta_get('clearart') or ''
				landscape = meta_get('custom_landscape') or meta_get('landscape') or ''
			else: banner, clearart, landscape = '', '', ''
			options_params = build_url({'mode': 'options_menu_choice', 'content': 'tvshow', 'tmdb_id': tmdb_id, 'poster': poster, 'playcount': playcount,
										'progress': progress, 'is_external': self.is_external, 'in_progress_menu': self.in_progress_menu})
			extras_params = build_url({'mode': 'extras_menu_choice', 'tmdb_id': tmdb_id, 'media_type': 'tvshow', 'is_external': self.is_external})
			if self.all_episodes:
				if self.all_episodes == 1 and total_seasons > 1: url_params = build_url({'mode': 'build_season_list', 'tmdb_id': tmdb_id})
				else: url_params = build_url({'mode': 'build_episode_list', 'tmdb_id': tmdb_id, 'season': 'all'})
			else: url_params = build_url({'mode': 'build_season_list', 'tmdb_id': tmdb_id})
			if self.open_extras:
				cm_append((browse_str, container_update % url_params))
				url_params = extras_params
			else: cm_append((extras_str, run_plugin % extras_params))
			cm_append((options_str, run_plugin % options_params))
			if not playcount:
				cm_append((watched_str % self.watched_title, run_plugin % build_url({'mode': 'watched_status.mark_tvshow', 'action': 'mark_as_watched', 'title': title, 'year': year,
																					'tmdb_id': tmdb_id, 'tvdb_id': tvdb_id, 'icon': poster})))
			elif self.home_hide_watched: return
			if progress:
				cm_append((unwatched_str % self.watched_title, run_plugin % build_url({'mode': 'watched_status.mark_tvshow', 'action': 'mark_as_unwatched', 'title': title,
																						'year': year, 'tmdb_id': tmdb_id, 'tvdb_id': tvdb_id, 'icon': poster})))
				set_properties({'watchedepisodes': string(total_watched), 'unwatchedepisodes': string(total_unwatched)})
			set_properties({'watchedprogress': string(progress), 'totalepisodes': string(total_aired_eps), 'totalseasons': string(total_seasons)})
			if self.is_external:
				cm_append((refr_widg_str, run_plugin % build_url({'mode': 'kodi_refresh'})))
				set_properties({'fen.external': 'true'})
			else: cm_append((exit_str, run_plugin % build_url({'mode': 'navigator.exit_media_menu'})))
			display = rootname if self.include_year else title
			listitem.setLabel(display)
			listitem.addContextMenuItems(cm)
			listitem.setArt({'poster': poster, 'fanart': fanart, 'icon': poster, 'banner': banner, 'clearart': clearart, 'clearlogo': clearlogo, 'thumb': landscape,
							'landscape': landscape, 'tvshow.poster': poster, 'tvshow.clearart': clearart, 'tvshow.clearlogo': clearlogo})
			info_tag = listitem.getVideoInfoTag()
			info_tag.setMediaType('tvshow')
			info_tag.setTitle(display)
			info_tag.setTvShowTitle(title)
			info_tag.setOriginalTitle(meta_get('original_title'))
			info_tag.setTvShowStatus(meta_get('status'))
			info_tag.setPlot(meta_get('plot'))
			info_tag.setYear(int(year))
			info_tag.setRating(meta_get('rating'))
			info_tag.setVotes(meta_get('votes'))
			info_tag.setMpaa(meta_get('mpaa'))
			info_tag.setDuration(meta_get('duration'))
			info_tag.setCountries(meta_get('country'))
			info_tag.setTrailer(meta_get('trailer'))
			info_tag.setPremiered(meta_get('premiered'))
			info_tag.setTagLine(meta_get('tagline'))
			info_tag.setStudios((meta_get('studio') or '',))
			info_tag.setUniqueIDs({'imdb': imdb_id, 'tmdb': string(tmdb_id), 'tvdb': string(tvdb_id)})
			info_tag.setIMDBNumber(imdb_id)
			info_tag.setGenres(meta_get('genre').split(', '))
			info_tag.setWriters(meta_get('writer').split(', '))
			info_tag.setDirectors(meta_get('director').split(', '))
			info_tag.setCast([xbmc_actor(name=item['name'], role=item['role'], thumbnail=item['thumbnail']) for item in meta_get('cast', [])])
			info_tag.setPlaycount(playcount)
			set_properties({'fen.extras_params': extras_params, 'fen.options_params': options_params})
			self.append(((url_params, listitem, self.is_folder), _position))
		except: pass

	def worker(self):
		self.current_date, self.current_time = get_datetime_function(), get_current_timestamp()
		self.meta_user_info, self.watched_indicators, self.include_year = metadata_user_info(), watched_indicators(), include_year_in_title('tvshow')
		self.watched_info, self.all_episodes, self.open_extras = get_watched_info_function(self.watched_indicators), default_all_episodes(), extras_open_action('tvshow')
		self.fanart_enabled, self.home_hide_watched = self.meta_user_info['extra_fanart_enabled'], self.is_home and self.meta_user_info['widget_hide_watched']
		self.is_folder, self.watched_title = False if self.open_extras else True, trakt_str if self.watched_indicators == 1 else fen_str
		self.poster_main, self.poster_backup, self.fanart_main, self.fanart_backup, self.clearlogo_main, self.clearlogo_backup = get_art_provider()
		if self.custom_order:
			threads = list(make_thread_list_multi_arg(self.build_tvshow_content, self.list, self.max_threads))
			[i.join() for i in threads]
		else:
			threads = list(make_thread_list_enumerate(self.build_tvshow_content, self.list, self.max_threads))
			[i.join() for i in threads]
			self.items.sort(key=lambda k: k[1])
			self.items = [i[0] for i in self.items]
		return self.items

	def paginate_list(self, data, page_no):
		if paginate(self.is_home):
			limit = page_limit(self.is_home)
			data, all_pages, total_pages = paginate_list(data, page_no, limit, self.paginate_start)
			if self.is_home: self.paginate_start = limit
		else: all_pages, total_pages = '', 1
		return data, all_pages, total_pages
