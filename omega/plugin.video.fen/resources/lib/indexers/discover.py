# -*- coding: utf-8 -*-
from datetime import timedelta
from apis import tmdb_api
from caches.main_cache import main_cache, cache_object
from modules import kodi_utils, meta_lists
from modules.settings import tmdb_api_key
from modules.utils import safe_string, remove_accents
# logger = kodi_utils.logger

sys, json, translate_path, database, get_icon = kodi_utils.sys, kodi_utils.json, kodi_utils.translate_path, kodi_utils.database, kodi_utils.get_icon
get_property, dialog, notification, select_dialog, run_plugin = kodi_utils.get_property, kodi_utils.dialog, kodi_utils.notification, kodi_utils.select_dialog, kodi_utils.run_plugin
add_items, show_text, container_refresh, focus_index, add_item = kodi_utils.add_items, kodi_utils.show_text, kodi_utils.container_refresh, kodi_utils.focus_index, kodi_utils.add_item
ls, build_url, make_listitem, set_property, set_content = kodi_utils.local_string, kodi_utils.build_url, kodi_utils.make_listitem, kodi_utils.set_property, kodi_utils.set_content
end_directory, set_view_mode, maincache_db = kodi_utils.end_directory, kodi_utils.set_view_mode, kodi_utils.maincache_db
clear_property, confirm_dialog, numeric_input = kodi_utils.clear_property, kodi_utils.confirm_dialog, kodi_utils.numeric_input
default_icon, fanart, default_poster, default_cast = get_icon('discover'), kodi_utils.addon_fanart, 'box_office', get_icon('genre_family')
set_category = kodi_utils.set_category
years_movies, years_tvshows, movie_genres, tvshow_genres = meta_lists.years_movies, meta_lists.years_tvshows, meta_lists.movie_genres, meta_lists.tvshow_genres
languages, regions, movie_certifications, networks = meta_lists.languages, meta_lists.regions, meta_lists.movie_certifications, meta_lists.networks
inc_str, ex_str, heading_base = '%s %s' % (ls(32188), '%s'), '%s %s' % (ls(32189), '%s'), '%s - %s' % (ls(32451), '%s')
add_menu_str, add_folder_str, remove_str, clear_str = ls(32730), ls(32731), ls(32698), ls(32699)
base_str, window_prop = '[B]%s:[/B]  [I]%s[/I]', 'fen.%s_discover_params'
lower_certs = ('PG', 'PG-13', 'R', 'NC-17')
position = {'recommended': 0, 'year_start': 2, 'year_end': 3, 'with_genres': 4, 'without_genres': 5, 'with_keywords': 6, 'without_keywords': 7, 'language': 8,
			'region': 9, 'network': 9, 'companies': 10, 'rating': 10, 'certification': 11, 'rating_votes': 11, 'rating_movie': 12, 'sort_by': 12, 'rating_votes_movie': 13,
			'cast': 14, 'sort_by_movie': 15, 'adult': 16}
url_params = ('year_start', 'year_end', 'with_genres', 'without_genres', 'with_keywords', 'without_keywords', 'companies', 'language', 'region', 'rating', 'rating_votes',
			'certification', 'cast', 'network', 'adult', 'sort_by')
tmdb_url = 'https://api.themoviedb.org/3/%s'

class Discover:
	def __init__(self, params):
		self.params = params
		self.media_type = self.params.get('media_type', None)
		self.category_name = self.params.get('name', None)
		self.key = self.params.get('key', None)
		if self.media_type: self.window_prop = window_prop % self.media_type.upper()
		else: self.window_prop = ''
		try: self.discover_params = json.loads(get_property(self.window_prop))
		except: self.discover_params = {}
		self.tmdb_api = tmdb_api_key()
		self.view = 'view.main'

	def movie(self):
		self._set_default_params()
		self.add({'mode': 'discover._clear_property', 'media_type': 'movie', 'list_name': '[B]%s[/B]' % ls(32656).upper()})
		self.add({'mode': 'discover.recommended', 'media_type': 'movie', 'list_name': '[B]%s %s:[/B]  [I]%s[/I]' % (ls(32451), ls(32593), self.gv('recommended'))})
		if not 'recommended'in self.value_names:
			self.add({'mode': 'discover.year', 'media_type': 'movie', 'key': 'year_start', 'list_name': base_str % ('%s %s' % (ls(32543), ls(32654)), self.gv('year_start'))})
			self.add({'mode': 'discover.year', 'media_type': 'movie', 'key': 'year_end', 'list_name': base_str % ('%s %s' % (ls(32543), ls(32655)), self.gv('year_end'))})
			self.add({'mode': 'discover.genres', 'media_type': 'movie', 'key': 'with_genres', 'list_name': base_str % (inc_str % ls(32470), self.gv('with_genres'))})
			self.add({'mode': 'discover.genres', 'media_type': 'movie', 'key': 'without_genres', 'list_name': base_str % (ex_str % ls(32470), self.gv('without_genres'))})
			self.add({'mode': 'discover.keywords', 'media_type': 'movie', 'key': 'with_keywords', 'list_name': base_str % (inc_str % ls(32657), self.gv('with_keywords'))})
			self.add({'mode': 'discover.keywords', 'media_type': 'movie', 'key': 'without_keywords', 'list_name': base_str % (ex_str % ls(32657), self.gv('without_keywords'))})
			self.add({'mode': 'discover.language', 'media_type': 'movie', 'list_name': base_str % (ls(32658), self.gv('language'))})
			self.add({'mode': 'discover.region', 'media_type': 'movie', 'list_name': base_str % (ls(32659), self.gv('region'))})
			self.add({'mode': 'discover.companies', 'media_type': 'movie', 'list_name': base_str % (ls(32660), self.gv('companies'))})
			self.add({'mode': 'discover.certification', 'media_type': 'movie', 'list_name': base_str % (ls(32473), self.gv('certification'))})
			self.add({'mode': 'discover.rating', 'media_type': 'movie', 'list_name': base_str % ('%s %s' % (ls(32661), ls(32621)), self.gv('rating'))})
			self.add({'mode': 'discover.rating_votes', 'media_type': 'movie', 'list_name': base_str % ('%s %s' % (ls(32661), ls(32663)), self.gv('rating_votes'))})
			self.add({'mode': 'discover.cast', 'media_type': 'movie', 'list_name': base_str % (inc_str % ls(32664), self.gv('cast'))})
			self.add({'mode': 'discover.sort_by', 'media_type': 'movie', 'list_name': base_str % (ls(32067), self.gv('sort_by'))})
			self.add({'mode': 'discover.adult', 'media_type': 'movie', 'list_name': base_str % (inc_str % ls(32665), self.gv('adult'))})
		self._add_defaults()
		self._end_directory()

	def tvshow(self):
		self._set_default_params()
		self.add({'mode': 'discover._clear_property', 'media_type': 'tvshow', 'list_name': '[B]%s[/B]' % ls(32656).upper()})
		self.add({'mode': 'discover.recommended', 'media_type': 'tvshow', 'list_name': '[B]%s %s:[/B]  [I]%s[/I]' % (ls(32451), ls(32593), self.gv('recommended'))})
		if not 'recommended'in self.value_names:
			self.add({'mode': 'discover.year', 'media_type': 'tvshow', 'key': 'year_start', 'list_name': base_str % ('%s %s' % (ls(32543), ls(32654)), self.gv('year_start'))})
			self.add({'mode': 'discover.year', 'media_type': 'tvshow', 'key': 'year_end', 'list_name': base_str % ('%s %s' % (ls(32543), ls(32655)), self.gv('year_end'))})
			self.add({'mode': 'discover.genres', 'media_type': 'tvshow', 'key': 'with_genres', 'list_name': base_str % (inc_str % ls(32470), self.gv('with_genres'))})
			self.add({'mode': 'discover.genres', 'media_type': 'tvshow', 'key': 'without_genres', 'list_name': base_str % (ex_str % ls(32470), self.gv('without_genres'))})
			self.add({'mode': 'discover.keywords', 'media_type': 'tvshow', 'key': 'with_keywords', 'list_name': base_str % (inc_str % ls(32657), self.gv('with_keywords'))})
			self.add({'mode': 'discover.keywords', 'media_type': 'tvshow', 'key': 'without_keywords', 'list_name': base_str % (ex_str % ls(32657), self.gv('without_keywords'))})
			self.add({'mode': 'discover.language', 'media_type': 'tvshow', 'list_name': base_str % (ls(32658), self.gv('language'))})
			self.add({'mode': 'discover.network', 'media_type': 'tvshow', 'list_name': base_str % (ls(32480), self.gv('network'))})
			self.add({'mode': 'discover.rating', 'media_type': 'tvshow', 'list_name': base_str % ('%s %s' % (ls(32661), ls(32621)), self.gv('rating'))})
			self.add({'mode': 'discover.rating_votes', 'media_type': 'tvshow', 'list_name': base_str % ('%s %s' % (ls(32661), ls(32663)), self.gv('rating_votes'))})
			self.add({'mode': 'discover.sort_by', 'media_type': 'tvshow', 'list_name': base_str % (ls(32067), self.gv('sort_by'))})
		self._add_defaults()
		self._end_directory()

	def recommended(self):
		key = 'recommended'
		if self._action(key) in ('clear', None): return
		query = dialog.input(heading_base % ls(32228))
		if not query: return
		if self.media_type == 'movie': function = tmdb_api.tmdb_movies_search
		else: function = tmdb_api.tmdb_tv_search
		year = dialog.input(heading_base % ('%s (%s)' % (ls(32543), ls(32669))), type=numeric_input)
		if year: query = '%s|%s' % (query, year)
		results = function(query, 1)['results']
		if len(results) == 0: return notification(32490)
		choice_list = []
		append = choice_list.append
		for item in results:
			title = item['title'] if self.media_type == 'movie' else item['name']
			try: year = item['release_date'].split('-')[0] if self.media_type == 'movie' else item['first_air_date'].split('-')[0]
			except: year = ''
			if year: rootname = '%s (%s)' % (title, year)
			else: rootname = title
			if item.get('poster_path'): icon = 'https://image.tmdb.org/t/p/w780%s' % item['poster_path']
			else: icon = get_icon(default_poster)
			append({'line1': rootname, 'icon': icon, 'rootname': rootname, 'tmdb_id': str(item['id'])})
		heading = heading_base % ('%s %s' % (ls(32193), ls(32228)))
		kwargs = {'items': json.dumps(choice_list), 'heading': heading}
		values = select_dialog([(i['tmdb_id'], i['rootname']) for i in choice_list], **kwargs)
		if values == None: return
		self._process(key, values)

	def keywords(self):
		if self._action(self.key) in ('clear', None): return
		current_key_ids = self.discover_params['value_strings'].get(self.key, [])
		current_keywords = self.discover_params['value_names'].get(self.key, [])
		key_ids_append, key_words_append = current_key_ids.append, current_keywords.append
		heading = inc_str if self.key == 'with_keywords' else ex_str
		replace_value = '&%s=' % self.key
		if not isinstance(current_key_ids, list): current_key_ids = current_key_ids.replace(replace_value, '').split(', ')
		if not isinstance(current_keywords, list): current_keywords = current_keywords.split(', ')
		keyword = dialog.input(heading_base % (heading % ls(32657)))
		if keyword:
			try:
				result = tmdb_api.tmdb_keywords_by_query(keyword)['results']
				keywords_choice = self._multiselect_dialog(heading_base % ('%s %s' % (ls(32193), ls(32657))), [i['name'].upper() for i in result], result)
				if keywords_choice != None:
					for i in keywords_choice:
						key_ids_append(str(i['id']))
						key_words_append(i['name'].upper())
			except: pass
			values = ('%s%s' % (replace_value, ','.join([i for i in current_key_ids])), ', '.join([i for i in current_keywords]))
			self._process(self.key, values)

	def year(self):
		if self._action(self.key) in ('clear', None): return
		if self.discover_params['media_type'] == 'movie': years = years_movies
		else: years = years_tvshows
		years_list = [str(i) for i in years]
		year = self._selection_dialog(years_list, years, heading_base % ('%s %s' % (ls(32655), ls(32543))))
		if year != None:
			if self.key == 'year_start': value_ending, value_date = 'gte', '01-01'
			else: value_ending, value_date = 'lte', '12-31'
			if self.discover_params['media_type'] == 'movie': value = '&primary_release_date.%s=%s-%s' % (value_ending, str(year), value_date)
			else: value = '&first_air_date.%s=%s-%s' % (value_ending, str(year), value_date)
			values = (value, str(year))
			self._process(self.key, values)

	def genres(self):
		if self._action(self.key) in ('clear', None): return
		if self.discover_params['media_type'] == 'movie': genres = movie_genres
		else: genres = tvshow_genres
		heading = inc_str if self.key == 'with_genres' else ex_str
		genre_list = [(k, v[0]) for k,v in sorted(genres.items())]
		genres_choice = self._multiselect_dialog(heading_base % (heading % ls(32470)), [i[0] for i in genre_list], genre_list)
		if genres_choice != None:
			genre_ids = ','.join([i[1] for i in genres_choice])
			genre_names = ', '.join([i[0] for i in genres_choice])
			values = ('&%s=%s' % (self.key, genre_ids), genre_names)
			self._process(self.key, values)

	def language(self):
		key = 'language'
		if self._action(key) in ('clear', None): return
		language = self._selection_dialog([i[0] for i in languages], languages, heading_base % ls(32658))
		if language != None:
			values = ('&with_original_language=%s' % str(language[1]), str(language[1]).upper())
			self._process(key, values)

	def region(self):
		key = 'region'
		if self._action(key) in ('clear', None): return
		region_names = [i['name'] for i in regions]
		region_codes = [i['code'] for i in regions]
		region = self._selection_dialog(region_names, region_codes, heading_base % ls(32659))
		if region != None:
			region_name = [i['name'] for i in regions if i['code'] == region][0]
			values = ('&region=%s' % region, region_name)
			self._process(key, values)

	def rating(self):
		key = 'rating'
		if self._action(key) in ('clear', None): return
		ratings = [i for i in range(1,11)]
		ratings_list = [str(float(i)) for i in ratings]
		rating = self._selection_dialog(ratings_list, ratings, heading_base % ('%s %s' % (ls(32661), ls(32621))))
		if rating != None:
			values = ('&vote_average.gte=%s' % str(rating), str(float(rating)))
			self._process(key, values)

	def rating_votes(self):
		key = 'rating_votes'
		if self._action(key) in ('clear', None): return
		rating_votes = [i for i in range(0,1001,50)]
		rating_votes.pop(0)
		rating_votes.insert(0, 1)
		rating_votes_list = [str(i) for i in rating_votes]
		rating_votes = self._selection_dialog(rating_votes_list, rating_votes, heading_base % ('%s %s' % (ls(32661), ls(32663))))
		if rating_votes != None:
			values = ('&vote_count.gte=%s' % str(rating_votes), str(rating_votes))
			self._process(key, values)

	def certification(self):
		key = 'certification'
		if self._action(key) in ('clear', None): return
		cert_list = [(i, '=%s' % i) for i in movie_certifications]
		[cert_list.insert(cert_list.index((item, '=%s' % item)) + 1, ('%s (and lower)' % item, '.lte=%s' % item)) for item in lower_certs]
		certification = self._selection_dialog([i[0] for i in cert_list], cert_list, heading_base % ls(32473))
		if certification != None:
			values = ('&certification_country=US&certification%s' % certification[1], certification[0])
			self._process(key, values)

	def cast(self):
		key = 'cast'
		if self._action(key) in ('clear', None): return
		result, actor_id, search_name = None, None, None
		search_name = dialog.input(heading_base % ls(32664))
		if not search_name: return
		string = '%s_%s' % ('tmdb_movies_people_search_actor_data', search_name)
		url = tmdb_url % 'search/person?api_key=%s&language=en-US&query=%s' % (self.tmdb_api, search_name)
		result = cache_object(tmdb_api.get_tmdb, string, url, 4)
		result = result['results']
		if not result: return
		actor_list = []
		append = actor_list.append
		if len(result) > 1:
			for item in result:
				name = item['name']
				known_for_list = [i.get('title', 'NA') for i in item['known_for']]
				known_for_list = [i for i in known_for_list if not i == 'NA']
				known_for = ', '.join(known_for_list) if known_for_list else ''
				if item.get('profile_path'): icon = 'https://image.tmdb.org/t/p/h632/%s' % item['profile_path']
				else: icon = default_cast
				append({'line1': name, 'line2': known_for, 'icon': icon, 'name': name, 'id': item['id']})
			heading = heading_base % ls(32664)
			kwargs = {'items': json.dumps(actor_list), 'heading': heading, 'enumerate': 'false', 'multi_choice': 'false', 'multi_line': 'true'}
			choice = select_dialog(actor_list, **kwargs)
			if choice == None: return self._set_property()
			actor_id = choice['id']
			actor_name = choice['name']
		else:
			actor_id = [item['id'] for item in result][0]
			actor_name = [item['name'] for item in result][0]
		if actor_id:
			values = ('&with_cast=%s' % str(actor_id), safe_string(remove_accents(actor_name)))
			self._process(key, values)

	def network(self):
		key = 'network'
		if self._action(key) in ('clear', None): return
		network_list = []
		append = network_list.append
		networks_info = sorted(networks, key=lambda k: k['name'])
		for item in networks:
			name = item['name']
			append({'line1': name, 'icon': item['logo'], 'name': name, 'id': item['id']})
		heading = heading_base % ls(32480)
		kwargs = {'items': json.dumps(network_list), 'heading': heading, 'enumerate': 'false', 'multi_choice': 'false', 'multi_line': 'false'}
		choice = select_dialog(network_list, **kwargs)
		if choice == None: return
		values = ('&with_networks=%s' % choice['id'], choice['name'])
		self._process(key, values)

	def companies(self):
		key = 'companies'
		if self._action(key) in ('clear', None): return
		current_company_ids = self.discover_params['value_strings'].get(key, [])
		current_companies = self.discover_params['value_names'].get(key, [])
		company_ids_append = current_company_ids.append
		company_append = current_companies.append
		if not isinstance(current_company_ids, list):
			current_company_ids = current_company_ids.replace('&with_companies=', '').split('|')
		if not isinstance(current_companies, list):
			current_companies = current_companies.split(', ')
		company = dialog.input(heading_base % ls(32660))
		if company:
			company_choice = None
			try:
				results = tmdb_api.tmdb_company_id(company)
				if results['total_results'] == 0: return None
				if results['total_results'] == 1: company_choice = results['results']
				if not company_choice:
					results = results['results']
					company_choice = self._multiselect_dialog(heading_base % ls(32660), [i['name'].upper() for i in results], results)
				if company_choice != None:
					for i in company_choice:
						company_ids_append(str(i['id']))
						company_append(i['name'].upper())
				values = ('&with_companies=%s' % '|'.join([i for i in current_company_ids]), ', '.join([i for i in current_companies]))
				self._process(key, values)
			except: pass

	def sort_by(self):
		key = 'sort_by'
		if self._action(key) in ('clear', None): return
		if self.discover_params['media_type'] == 'movie':
			sort_by_list = self._movies_sort()
		else:
			sort_by_list = self._tvshows_sort()
		sort_by_value = self._selection_dialog([i[0] for i in sort_by_list], [i[1] for i in sort_by_list], heading_base % ls(32067))
		if sort_by_value != None:
			sort_by_name = [i[0] for i in sort_by_list if i[1] == sort_by_value][0]
			values = (sort_by_value, sort_by_name)
			self._process(key, values)

	def adult(self):
		key = 'adult'
		include_adult = self._selection_dialog((ls(32859), ls(32860)), ('true', 'false'), heading_base % inc_str % ls(32665))
		if include_adult != None:
			values = ('&include_adult=%s' % include_adult, include_adult.capitalize())
			self._process(key, values)

	def export(self):
		try:
			media_type, query, name = self.discover_params['media_type'], self.discover_params['final_string'], self.discover_params['name']
			set_history(media_type, name, query)
			if media_type == 'movie': mode, action = 'build_movie_list', 'tmdb_movies_discover'
			else: mode, action = 'build_tvshow_list', 'tmdb_tv_discover'
			menu_item_json = json.dumps({'name': name, 'mode': mode, 'action': action, 'query': query, 'iconImage': 'discover'})
			if self.params['export_type'] == 'menu': mode = 'menu_editor.add_external'
			else: mode = 'menu_editor.shortcut_folder_add_item'
			run_plugin({'mode': mode, 'iconImage': 'discover', 'name': name, 'menu_item': menu_item_json})
		except: notification(32574)

	def history(self, media_type=None, display=True):
		def _builder():
			for count, item in enumerate(data):
				try:
					cm = []
					cm_append = cm.append
					data_id = history[count][0]
					name = item['name']
					url_params = {'mode': item['mode'], 'action': item['action'], 'query': item['query'], 'name': name,
									'iconImage': default_icon, 'data_id': data_id, 'media_type': media_type, 'list_type': 'discover_history'}
					display = '%s | %s' % (count+1, name)
					url = build_url(url_params)
					remove_single_params = {'mode': 'discover.remove_from_history', 'data_id': data_id, 'silent': 'false'}
					remove_all_params = {'mode': 'discover.remove_all_history', 'media_type': media_type, 'silent': 'true'}
					listitem = make_listitem()
					listitem.setLabel(display)
					listitem.setArt({'icon': default_icon, 'poster': default_icon, 'thumb': default_icon, 'fanart': fanart, 'banner': default_icon})
					info_tag = listitem.getVideoInfoTag()
					info_tag.setPlot(' ')
					cm_append(('[B]%s[/B]' % remove_str,'RunPlugin(%s)'% build_url(remove_single_params)))
					cm_append(('[B]%s[/B]' % clear_str,'RunPlugin(%s)'% build_url(remove_all_params)))
					cm_append((add_menu_str, 'RunPlugin(%s)'% build_url({'mode': 'menu_editor.add_external', 'name': name, 'iconImage': 'discover'})))
					cm_append((add_folder_str, 'RunPlugin(%s)' % build_url({'mode': 'menu_editor.shortcut_folder_add_item', 'name': name, 'iconImage': 'discover'})))
					listitem.addContextMenuItems(cm)
					listitem.setProperty('fen.context_main_menu_params', build_url({'mode': 'menu_editor.edit_menu_external', 'name': name, 'iconImage': default_icon}))
					yield (url, listitem, True)
				except: pass
		handle = int(sys.argv[1])
		media_type = media_type if media_type else self.media_type
		string = 'fen_discover_%s_%%' % media_type
		dbcon = database.connect(maincache_db, timeout=40.0, isolation_level=None)
		dbcur = dbcon.cursor()
		dbcur.execute('''PRAGMA synchronous = OFF''')
		dbcur.execute('''PRAGMA journal_mode = OFF''')
		dbcur.execute("SELECT id, data FROM maincache WHERE id LIKE ? ORDER BY rowid DESC", (string,))
		history = dbcur.fetchall()
		if not display: return [i[0] for i in history]
		data = [eval(i[1]) for i in history]
		item_list = list(_builder())
		add_items(handle, item_list)
		self._end_directory()

	def gv(self, value):
		return self.value_names.get(value, '')

	def help(self):
		text_file = translate_path('special://home/addons/plugin.video.fen/resources/text/tips/135. Discover.txt')
		return show_text(heading_base % ls(32487), file=text_file, font_size='large')

	def _set_default_params(self):
		if not 'media_type' in self.discover_params:
			self._clear_property()
			url_media_type = 'movie' if self.media_type == 'movie' else 'tv'
			param_media_type = 'Movies' if self.media_type == 'movie' else 'TV Shows'
			self.discover_params['media_type'] = self.media_type
			self.discover_params['value_strings'] = {}
			self.discover_params['value_strings']['base'] = tmdb_url % 'discover/%s?api_key=%s&language=en-US&with_original_language=en&page=%s' \
																				% (url_media_type, self.tmdb_api, '%s')
			self.discover_params['value_strings']['base_recommended'] = tmdb_url % '%s/%s/recommendations?api_key=%s&language=en-US&with_original_language=en&page=%s' \
																				% (url_media_type, '%s', self.tmdb_api, '%s')
			self.discover_params['value_names'] = {'media_type': param_media_type, 'adult': ls(32860)}
			self._set_property()
		self.value_names = self.discover_params['value_names']

	def _add_defaults(self):
		if not 'final_string' in self.discover_params: return
		if self.discover_params['media_type'] == 'movie': mode, action = 'build_movie_list', 'tmdb_movies_discover'
		else: mode, action = 'build_tvshow_list', 'tmdb_tv_discover'
		name, query, export_icon = self.discover_params.get('name', '...'), self.discover_params.get('final_string', ''), get_icon('nextpage')
		menu_export_str = ls(32730).upper().replace('[/B]', ':[/B] [I]%s[/I]' % name)
		folder_export_str = ls(32731).upper().replace('[/B]', ':[/B] [I]%s[/I]' % name)
		self.add({'mode': 'discover.export', 'media_type': self.media_type, 'export_type': 'menu', 'list_name': menu_export_str}, icon=export_icon)
		self.add({'mode': 'discover.export', 'media_type': self.media_type, 'export_type': 'folder', 'list_name': folder_export_str}, icon=export_icon)
		self.add({'mode': mode, 'action': action, 'query': query, 'name': name, 'list_name': ls(32666) % name}, isFolder=True, icon=get_icon('search'))

	def _action(self, key):
		dict_item = self.discover_params
		add_to_list = ('keyword', 'companies')
		action = ls(32602) if any(word in key for word in add_to_list) else ls(32668)
		if key in dict_item['value_names']:
			action = self._selection_dialog([action.capitalize(), ls(32671)], (action, 'clear'), heading_base % ls(32670))
		if action == None: return
		if action == 'clear':
			index = self._position(key)
			for k in ('value_strings', 'value_names'): dict_item[k].pop(key, None)
			self._process(index=index)
		return action

	def _process(self, key=None, values=None, index=None):
		if key:
			index = self._position(key)
			self.discover_params['value_strings'][key] = values[0]
			self.discover_params['value_names'][key] = values[1]
		self._build_string()
		self._build_name()
		self._set_property()
		container_refresh()
		if index: focus_index(index)

	def _clear_property(self):
		clear_property(self.window_prop)
		self.discover_params = {}
		container_refresh()

	def _set_property(self):
		return set_property(self.window_prop, json.dumps(self.discover_params))

	def add(self, params, isFolder=False, icon=None):
		handle = int(sys.argv[1])
		icon = icon or default_icon
		list_name = params.get('list_name', '')
		url = build_url(params)
		listitem = make_listitem()
		listitem.setLabel(list_name)
		listitem.setArt({'icon': icon, 'poster': icon, 'thumb': icon, 'fanart': fanart, 'banner': icon})
		info_tag = listitem.getVideoInfoTag()
		info_tag.setPlot(' ')
		add_item(handle, url, listitem, isFolder)

	def _end_directory(self):
		handle = int(sys.argv[1])
		set_content(handle, '')
		set_category(handle, self.category_name)
		end_directory(handle, cacheToDisc=False)
		set_view_mode(self.view, '')

	def _selection_dialog(self, dialog_list, function_list, string):
		list_items = [{'line1': item} for item in dialog_list]
		kwargs = {'items': json.dumps(list_items), 'heading': string, 'narrow_window': 'true'}
		return select_dialog(function_list, **kwargs)

	def _multiselect_dialog(self, string, dialog_list, function_list=None, preselect= []):
		if not function_list: function_list = dialog_list
		list_items = [{'line1': item} for item in dialog_list]
		kwargs = {'items': json.dumps(list_items), 'heading': string, 'enumerate': 'false', 'multi_choice': 'true', 'multi_line': 'false', 'preselect': preselect}
		return select_dialog(function_list, **kwargs)

	def _build_string(self):
		string_params = self.discover_params['value_strings']
		if 'recommended' in string_params: self.discover_params['final_string'] = string_params['base_recommended'] % (string_params['recommended'], '%s')
		else: self.discover_params['final_string'] = string_params['base'] + ''.join([v for k, v in string_params.items() if k in url_params])

	def _build_name(self):
		values = self.discover_params['value_names']
		media_type = values['media_type']
		db_name = ls(32028) if media_type == 'Movies' else ls(32029)
		name = '[B]%s[/B] ' % db_name
		if 'recommended' in values:
			name += '| %s %s' % (ls(32673), values['recommended'])
			self.discover_params['name'] = name
			return
		if 'year_start' in values:
			if 'year_end' in values and not values['year_start'] == values['year_end']: name += '| %s' % values['year_start']
			else: name += '| %s ' % values['year_start']
		if 'year_end' in values:
			if 'year_start' in values:
				if not values['year_start'] == values['year_end']: name += '-%s ' % values['year_end']
			else: name += '| %s ' % values['year_end']
		if 'language' in values: name += '| %s ' % values['language']
		if 'region' in values: name += '| %s ' % values['region']
		if 'network' in values: name += '| %s ' % values['network']
		if 'with_genres' in values:
			name += '| %s ' % values['with_genres']
			if 'without_genres' in values: name += '(%s %s) ' % (ls(32189).lower(), values['without_genres'])
		elif 'without_genres' in values: name += '| %s %s ' % (ls(32189).lower(), values['without_genres'])
		if 'companies' in values: name += '| %s ' % values['companies']
		if 'certification' in values: name += '| %s ' % values['certification']
		if 'rating' in values:
			name += '| %s+ ' % values['rating']
			if 'rating_votes' in values: name += '(%s) ' % values['rating_votes']
		elif 'rating_votes' in values: name += '| %s+ %s ' % (values['rating_votes'], ls(32623).lower())
		if 'cast' in values: name += '| %s %s ' % (ls(32664).lower(), values['cast'])
		if 'with_keywords' in values: name += '| %s: %s ' % (inc_str.lower() % ls(32657).lower(), values['with_keywords'])
		if 'without_keywords' in values: name += '| %s %s: %s ' % (ls(32189).lower(), ls(32657).lower(), values['without_keywords'])
		if 'sort_by' in values: name += '| %s ' % values['sort_by']
		if 'adult' in values and values['adult'] == ls(32859): name += '| %s ' % (inc_str.lower() % ls(32665).lower())
		self.discover_params['name'] = name

	def _position(self, key):
		if self.media_type == 'movie' and key in ('rating', 'rating_votes', 'sort_by'): key = '%s_movie' % key
		try: return position[key]
		except: return None

	def _movies_sort(self):
		return [
			(ls(33166), '&sort_by=popularity.asc'),            (ls(33167), '&sort_by=popularity.desc'),
			(ls(33168), '&sort_by=primary_release_date.asc'),  (ls(33169), '&sort_by=primary_release_date.desc'),
			(ls(33170), '&sort_by=revenue.asc'),               (ls(33171), '&sort_by=revenue.desc'),
			(ls(33172), '&sort_by=original_title.asc'),        (ls(33173), '&sort_by=original_title.desc'),
			(ls(33174), '&sort_by=vote_average.asc'),          (ls(33175), '&sort_by=vote_average.desc')
			]

	def _tvshows_sort(self):
		return [
			(ls(33166), '&sort_by=popularity.asc'),       (ls(33167), '&sort_by=popularity.desc'),
			(ls(33186), '&sort_by=first_air_date.asc'),  (ls(33187), '&sort_by=first_air_date.desc'),
			(ls(33174), '&sort_by=vote_average.asc'),     (ls(33175), '&sort_by=vote_average.desc')
			]

	def remove_from_history(self, params=None):
		if params is None: params = self.params
		dbcon = database.connect(maincache_db)
		dbcur = dbcon.cursor()
		dbcur.execute("DELETE FROM maincache WHERE id=?", (params['data_id'],))
		dbcon.commit()
		clear_property(params['data_id'])
		container_refresh()
		if not params['silent'] == 'true': notification(32576)

	def remove_all_history(self):
		if not confirm_dialog(): return
		all_history = self.history(display=False)
		for item in all_history: self.remove_from_history({'data_id': item, 'silent': 'true'})
		notification(32576)

def set_history(media_type, name, query):
	string = 'fen_discover_%s_%s' % (media_type, query)
	cache = main_cache.get(string)
	if cache: return
	if media_type == 'movie': mode, action = 'build_movie_list', 'tmdb_movies_discover'
	else: mode, action = 'build_tvshow_list', 'tmdb_tv_discover'
	data = {'mode': mode, 'action': action, 'name': name, 'query': query}
	main_cache.set(string, data, expiration=timedelta(days=1000))
	return
