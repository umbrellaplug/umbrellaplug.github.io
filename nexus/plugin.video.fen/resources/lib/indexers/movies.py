# -*- coding: utf-8 -*-
from modules import kodi_utils, settings
from modules.meta_lists import oscar_winners
from modules.metadata import movie_meta, movieset_meta
from modules.utils import manual_function_import, get_datetime, make_thread_list_enumerate, make_thread_list_multi_arg, adjust_premiered_date, get_current_timestamp, paginate_list
from modules.watched_status import get_watched_info_movie, get_watched_status_movie, get_bookmarks, get_progress_percent
# logger = kodi_utils.logger

meta_function, get_datetime_function, add_item, home, item_jump_landscape = movie_meta, get_datetime, kodi_utils.add_item, kodi_utils.home, kodi_utils.item_jump_landscape
progress_percent_function, get_watched_function, get_watched_info_function = get_progress_percent, get_watched_status_movie, get_watched_info_movie
set_content, end_directory, set_view_mode, folder_path = kodi_utils.set_content, kodi_utils.end_directory, kodi_utils.set_view_mode, kodi_utils.folder_path
sleep, xbmc_actor, set_category, json = kodi_utils.sleep, kodi_utils.xbmc_actor, kodi_utils.set_category, kodi_utils.json
string, ls, sys, external, add_items, add_dir = str, kodi_utils.local_string, kodi_utils.sys, kodi_utils.external, kodi_utils.add_items, kodi_utils.add_dir
make_listitem, build_url, remove_keys, dict_removals = kodi_utils.make_listitem, kodi_utils.build_url, kodi_utils.remove_keys, kodi_utils.movie_dict_removals
poster_empty, fanart_empty, set_property, nextpage_landscape = kodi_utils.empty_poster, kodi_utils.addon_fanart, kodi_utils.set_property, kodi_utils.nextpage_landscape
metadata_user_info, watched_indicators, jump_to_enabled, date_offset = settings.metadata_user_info, settings.watched_indicators, settings.jump_to_enabled, settings.date_offset
extras_open_action, get_art_provider, get_resolution, page_limit = settings.extras_open_action, settings.get_art_provider, settings.get_resolution, settings.page_limit
max_threads, widget_hide_next_page, include_year_in_title, paginate = settings.max_threads, settings.widget_hide_next_page, settings.include_year_in_title, settings.paginate
fen_str, trakt_str, watched_str, unwatched_str, extras_str, options_str = ls(32036), ls(32037), ls(32642), ls(32643), ls(32645), ls(32646)
hide_str, exit_str, clearprog_str, nextpage_str, jump2_str, play_str = ls(32648), ls(32649), ls(32651), ls(32799), ls(32964), '[B]%s...[/B]' % ls(32174)
addmenu_str, addshortcut_str, add_coll_str, refr_widg_str, play_options_str = ls(32730), ls(32731), ls(33081), '[B]%s[/B]' % ls(32611), '[B]%s...[/B]' % ls(32187)
run_plugin = 'RunPlugin(%s)'
tmdb_main = ('tmdb_movies_popular', 'tmdb_movies_popular_today','tmdb_movies_blockbusters','tmdb_movies_in_theaters',
				'tmdb_movies_upcoming', 'tmdb_movies_latest_releases', 'tmdb_movies_premieres')
tmdb_special = {'tmdb_movies_languages': 'language', 'tmdb_movies_networks': 'network_id', 'tmdb_movies_year': 'year', 'tmdb_movies_decade': 'decade',
				'tmdb_movies_certifications': 'certification', 'tmdb_movies_recommendations': 'tmdb_id', 'tmdb_movies_genres': 'genre_id', 'tmdb_movies_search': 'query',
				'tmdb_movies_search_sets': 'query'}
personal = {'favorites_movies': ('modules.favorites', 'get_favorites'), 'in_progress_movies': ('modules.watched_status', 'get_in_progress_movies'), 
				'watched_movies': ('modules.watched_status', 'get_watched_items'), 'recent_watched_movies': ('modules.watched_status', 'get_recently_watched')}
trakt_main = ('trakt_movies_trending', 'trakt_movies_trending_recent', 'trakt_movies_most_watched', 'trakt_movies_top10_boxoffice', 'trakt_recommendations')
trakt_personal = ('trakt_collection', 'trakt_watchlist', 'trakt_collection_lists', 'trakt_favorites')
imdb_all  = ('imdb_watchlist', 'imdb_user_list_contents', 'imdb_keywords_list_contents', 'imdb_movies_oscar_winners')
view_mode, content_type = 'view.movies', 'movies'

class Movies:
	def __init__(self, params):
		self.params = params
		self.params_get = self.params.get
		self.category_name = self.params_get('category_name', None) or self.params_get('name', None) or 32028
		self.id_type, self.list, self.action = self.params_get('id_type', 'tmdb_id'), self.params_get('list', []), self.params_get('action', None)
		self.items, self.new_page, self.total_pages, self.is_external, self.is_home, self.max_threads = [], {}, None, external(), home(), max_threads()
		self.widget_hide_next_page = False if not self.is_home else widget_hide_next_page()
		self.custom_order = self.params_get('custom_order', 'false') == 'true'
		self.paginate_start = int(self.params_get('paginate_start', '0'))
		self.append = self.items.append

	def fetch_list(self):
		handle = int(sys.argv[1])
		# try:
		builder, mode = self.worker, self.params_get('mode')
		try: page_no = int(self.params_get('new_page', '1'))
		except: page_no = self.params_get('new_page')
		if page_no == 1 and not self.is_external: set_property('fen.exit_params', folder_path())
		if self.action in personal: var_module, import_function = personal[self.action]
		else: var_module, import_function = 'apis.%s_api' % self.action.split('_')[0], self.action
		try: function = manual_function_import(var_module, import_function)
		except: pass
		if self.action in tmdb_main:
			data = function(page_no)
			self.list = [i['id'] for i in data['results']]
			self.new_page = {'new_page': string(data['page'] + 1)}
		elif self.action in tmdb_special:
			if self.action == 'tmdb_movies_search_sets': builder = self.movie_sets_worker
			key = tmdb_special[self.action]
			function_var = self.params_get(key, None)
			if not function_var: return
			data = function(function_var, page_no)
			self.list = [i['id'] for i in data['results']]
			if data['total_pages'] > page_no: self.new_page = {'new_page': string(data['page'] + 1), key: function_var}
		elif self.action in personal:
			data = function('movie', page_no)
			if self.action == 'recent_watched_movies': all_pages, total_pages = '', 1
			else: data, all_pages, total_pages = self.paginate_list(data, page_no)
			self.list = [i['media_id'] for i in data]
			if total_pages > 2: self.total_pages = total_pages
			if total_pages > page_no: self.new_page = {'new_page': string(page_no + 1), 'paginate_start': self.paginate_start}
		elif self.action in trakt_main:
			self.id_type = 'trakt_dict'
			data = function(page_no)
			try: self.list = [i['movie']['ids'] for i in data]
			except: self.list = [i['ids'] for i in data]
			if self.action not in ('trakt_movies_top10_boxoffice', 'trakt_recommendations'): self.new_page = {'new_page': string(page_no + 1)}
		elif self.action in trakt_personal:
			self.id_type = 'trakt_dict'
			data = function('movies', page_no)
			if self.action in ('trakt_collection_lists', 'trakt_favorites'): all_pages, total_pages = '', 1
			else: data, all_pages, total_pages = self.paginate_list(data, page_no)
			self.list = [i['media_ids'] for i in data]
			if total_pages > 2: self.total_pages = total_pages
			try:
				if total_pages > page_no: self.new_page = {'new_page': string(page_no + 1), 'paginate_start': self.paginate_start}
			except: pass
		elif self.action in imdb_all:
			if self.action == 'imdb_movies_oscar_winners':
				data = oscar_winners
				self.list = data[page_no-1]
				if len(data) > page_no: self.new_page = {'new_page': string(page_no + 1)}
			else:
				self.id_type = 'imdb_id'
				list_id = self.params_get('list_id', None)
				data, next_page = function('movie', list_id, page_no)
				self.list = [i['imdb_id'] for i in data]
				if next_page: self.new_page = {'list_id': list_id, 'new_page': string(page_no + 1)}
		elif self.action == 'tmdb_movies_discover':
			name, query = self.params_get('name'), self.params_get('query')
			if page_no == 1:
				from indexers.discover import set_history
				set_history('movie', name, query)
			data = function(query, page_no)
			self.list = [i['id'] for i in data['results']]
			if data['total_pages'] > page_no: self.new_page = {'query': query, 'name': name, 'new_page': string(data['page'] + 1)}
		elif self.action  == 'tmdb_movies_sets':
			data = sorted(movieset_meta(self.params_get('tmdb_id'), metadata_user_info())['parts'], key=lambda k: k['release_date'] or '2050')
			self.list = [i['id'] for i in data]
		add_items(handle, builder())
		if self.total_pages and not self.is_external:
			jump_to = jump_to_enabled()
			if jump_to != 3:
				url_params = json.dumps({**self.new_page, **{'mode': mode, 'action': self.action, 'category_name': self.category_name}})
				add_dir({'mode': 'navigate_to_page_choice', 'current_page': page_no, 'total_pages': self.total_pages, 'all_pages': all_pages,
						'jump_to_enabled': jump_to, 'paginate_start': self.paginate_start, 'url_params': url_params}, jump2_str, handle, 'item_jump', item_jump_landscape,
						isFolder=False)
		if self.new_page and not self.widget_hide_next_page:
				self.new_page.update({'mode': mode, 'action': self.action, 'category_name': self.category_name})
				add_dir(self.new_page, nextpage_str % self.new_page['new_page'], handle, 'nextpage', nextpage_landscape)
		# except: pass
		set_content(handle, content_type)
		set_category(handle, ls(self.category_name))
		end_directory(handle, False if self.is_external else None)
		if not self.is_external:
			if self.params_get('refreshed') == 'true': sleep(1000)
			set_view_mode(view_mode, content_type, self.is_external)
		
	def build_movie_content(self, _position, _id):
		try:
			meta = meta_function(self.id_type, _id, self.meta_user_info, self.current_date, self.current_time)
			if not meta or 'blank_entry' in meta: return
			meta_get = meta.get
			playcount, overlay = get_watched_function(self.watched_info, string(meta_get('tmdb_id')))
			cm = []
			cm_append = cm.append
			listitem = make_listitem()
			set_properties = listitem.setProperties
			clearprog_params, watched_status_params = '', ''
			rootname, title, year = meta_get('rootname'), meta_get('title'), meta_get('year') or '2050'
			tmdb_id, imdb_id = meta_get('tmdb_id'), meta_get('imdb_id')
			poster = meta_get('custom_poster') or meta_get(self.poster_main) or meta_get(self.poster_backup) or poster_empty
			fanart = meta_get('custom_fanart') or meta_get(self.fanart_main) or meta_get(self.fanart_backup) or fanart_empty
			clearlogo = meta_get('custom_clearlogo') or meta_get(self.clearlogo_main) or meta_get(self.clearlogo_backup) or ''
			if self.fanart_enabled:
				banner, clearart = meta_get('custom_banner') or meta_get('banner') or '', meta_get('custom_clearart') or meta_get('clearart') or ''
				landscape, discart = meta_get('custom_landscape') or meta_get('landscape') or '', meta_get('custom_discart') or meta_get('discart') or ''
				keyart = meta_get('custom_keyart') or meta_get('keyart') or ''
			else: banner, clearart, landscape, discart, keyart = '', '', '', '', ''
			progress = progress_percent_function(self.bookmarks, tmdb_id)
			if playcount:
				if self.home_hide_watched: return
				watched_action, watchedstr = 'mark_as_unwatched', unwatched_str
			else: watched_action, watchedstr = 'mark_as_watched', watched_str
			watched_status_params = build_url({'mode': 'watched_status.mark_movie', 'action': watched_action, 'tmdb_id': tmdb_id, 'title': title, 'year': year})
			play_params = build_url({'mode': 'playback.media', 'media_type': 'movie', 'tmdb_id': tmdb_id})
			extras_params = build_url({'mode': 'extras_menu_choice', 'media_type': 'movie', 'tmdb_id': tmdb_id, 'is_external': self.is_external})
			play_options_params = build_url({'mode': 'playback_choice', 'media_type': 'movie', 'poster': poster, 'meta': tmdb_id})
			options_params = build_url({'mode': 'options_menu_choice', 'content': 'movie', 'tmdb_id': tmdb_id, 'poster': poster, 'playcount': playcount,
										'progress': progress, 'is_external': self.is_external})
			if self.open_extras:
				url_params = extras_params
				cm_append((play_str, run_plugin % play_params))
			else:
				url_params = play_params
				cm_append((extras_str, run_plugin % extras_params))
			cm_append((options_str, run_plugin % options_params))
			cm_append((play_options_str, run_plugin % play_options_params))
			if progress:
				clearprog_params = build_url({'mode': 'watched_status.erase_bookmark', 'media_type': 'movie', 'tmdb_id': tmdb_id, 'refresh': 'true'})
				cm_append((clearprog_str, run_plugin % clearprog_params))
			cm_append((watchedstr % self.watched_title, run_plugin % watched_status_params))
			if self.is_external:
				cm_append((refr_widg_str, run_plugin % build_url({'mode': 'kodi_refresh'})))
				set_properties({'fen.external': 'true'})
			else: cm_append((exit_str, run_plugin % build_url({'mode': 'navigator.exit_media_menu'})))
			display = rootname if self.include_year else title
			info_tag = listitem.getVideoInfoTag()
			info_tag.setMediaType('movie')
			info_tag.setTitle(display)
			info_tag.setOriginalTitle(meta_get('original_title'))
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
			info_tag.setUniqueIDs({'imdb': imdb_id, 'tmdb': string(tmdb_id)})
			info_tag.setIMDBNumber(imdb_id)
			info_tag.setGenres(meta_get('genre').split(', '))
			info_tag.setWriters(meta_get('writer').split(', '))
			info_tag.setDirectors(meta_get('director').split(', '))
			info_tag.setCast([xbmc_actor(name=item['name'], role=item['role'], thumbnail=item['thumbnail']) for item in meta_get('cast', [])])
			info_tag.setPlaycount(playcount)
			if progress:
				info_tag.setResumePoint(float(progress))
				set_properties({'WatchedProgress': progress})
			listitem.setLabel(display)
			listitem.addContextMenuItems(cm)
			listitem.setArt({'poster': poster, 'fanart': fanart, 'icon': poster, 'banner': banner, 'clearart': clearart,
							'clearlogo': clearlogo, 'landscape': landscape, 'thumb': landscape, 'discart': discart, 'keyart': keyart})
			set_properties({'fen.extras_params': extras_params, 'fen.clearprog_params': clearprog_params, 'fen.options_params': options_params,
							'fen.unwatched_params': watched_status_params, 'fen.watched_params': watched_status_params})
			self.append(((url_params, listitem, False), _position))
		except: pass

	def worker(self):
		self.current_date, self.current_time = get_datetime_function(), get_current_timestamp()
		self.meta_user_info, self.watched_indicators, self.include_year = metadata_user_info(), watched_indicators(), include_year_in_title('movie')
		self.watched_info, self.bookmarks = get_watched_info_function(self.watched_indicators), get_bookmarks(self.watched_indicators, 'movie')
		self.open_extras, self.watched_title = extras_open_action('movie'), trakt_str if self.watched_indicators == 1 else fen_str
		self.fanart_enabled, self.home_hide_watched = self.meta_user_info['extra_fanart_enabled'], self.is_home and self.meta_user_info['widget_hide_watched']
		self.poster_main, self.poster_backup, self.fanart_main, self.fanart_backup, self.clearlogo_main, self.clearlogo_backup = get_art_provider()
		if self.custom_order:
			threads = list(make_thread_list_multi_arg(self.build_movie_content, self.list, self.max_threads))
			[i.join() for i in threads]
		else:
			threads = list(make_thread_list_enumerate(self.build_movie_content, self.list, self.max_threads))
			[i.join() for i in threads]
			self.items.sort(key=lambda k: k[1])
			self.items = [i[0] for i in self.items]
		return self.items

	def build_movie_sets_content(self, _position, _id):
		try:
			cm = []
			cm_append = cm.append
			meta = movieset_meta(_id, self.meta_user_info, self.current_date)
			if not meta or 'blank_entry' in meta: return
			meta_get = meta.get
			parts = meta_get('parts')
			if len(parts) <= 1: return
			if len([i for i in parts if i['release_date'] and adjust_premiered_date(i['release_date'], self.adjust_hours)[0] <= self.current_date]) <= 1: return
			title, plot, tmdb_id = meta_get('title'), meta_get('plot'), meta_get('tmdb_id')
			poster = meta_get(self.poster_main) or meta_get(self.poster_backup) or poster_empty
			fanart = meta_get(self.fanart_main) or meta_get(self.fanart_backup) or fanart_empty
			clearlogo = meta_get('clearlogo2') or ''
			if self.fanart_enabled:
				banner, clearart = meta_get('custom_banner') or meta_get('banner') or '', meta_get('custom_clearart') or meta_get('clearart') or ''
				landscape, discart = meta_get('custom_landscape') or meta_get('landscape') or '', meta_get('custom_discart') or meta_get('discart') or ''
				keyart = meta_get('custom_keyart') or meta_get('keyart') or ''
			else: banner, clearart, landscape, discart, keyart = '', '', '', '', ''
			url = build_url({'mode': 'build_movie_list', 'action': 'tmdb_movies_sets', 'tmdb_id': tmdb_id})
			listitem = make_listitem()
			set_property = listitem.setProperty
			cm_append((addmenu_str, run_plugin % build_url({'mode': 'menu_editor.add_external', 'name': title, 'iconImage': poster})))
			cm_append((addshortcut_str, run_plugin % build_url({'mode': 'menu_editor.shortcut_folder_add_item', 'name': title, 'iconImage': poster})))
			cm_append((add_coll_str, run_plugin % build_url({'mode': 'movie_sets_to_collection_choice', 'collection_id': tmdb_id})))
			if self.is_external:
				cm_append((refr_widg_str, run_plugin % build_url({'mode': 'kodi_refresh'})))
				set_property('fen.external', 'true')
			info_tag = listitem.getVideoInfoTag()
			info_tag.setMediaType('movie')
			info_tag.setPlot(plot)
			listitem.setLabel(title)
			listitem.addContextMenuItems(cm)
			listitem.setArt({'poster': poster, 'fanart': fanart, 'icon': poster, 'banner': banner, 'clearart': clearart, 'landscape': landscape,
							'thumb': landscape, 'discart': discart, 'keyart': keyart})
			set_property('fen.context_main_menu_params', build_url({'mode': 'menu_editor.edit_menu_external', 'name': title, 'iconImage': poster}))
			self.append(((url, listitem, True), _position))
		except: pass

	def movie_sets_worker(self):
		self.meta_user_info, self.current_date, self.current_time, self.adjust_hours = metadata_user_info(), get_datetime_function(), get_current_timestamp(), date_offset()
		self.fanart_enabled = self.meta_user_info['extra_fanart_enabled']
		self.poster_main, self.poster_backup, self.fanart_main, self.fanart_backup = get_art_provider()[0:4]
		threads = list(make_thread_list_enumerate(self.build_movie_sets_content, self.list, self.max_threads))
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
