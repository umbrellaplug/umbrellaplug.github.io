# -*- coding: utf-8 -*-
from windows.base_window import BaseDialog, window_manager, window_player
from apis.tmdb_api import tmdb_people_info, tmdb_people_full_info
from apis.imdb_api import imdb_videos, imdb_people_trivia
from indexers import dialogs
from indexers.images import Images
from modules import kodi_utils, settings
from modules.utils import calculate_age, get_datetime
# logger = kodi_utils.logger

addon_fanart, Thread, empty_poster, execute_builtin, ls = kodi_utils.addon_fanart, kodi_utils.Thread, kodi_utils.empty_poster, kodi_utils.execute_builtin, kodi_utils.local_string
notification, show_busy_dialog, hide_busy_dialog, get_icon = kodi_utils.notification, kodi_utils.show_busy_dialog, kodi_utils.hide_busy_dialog, kodi_utils.get_icon
get_resolution, metadata_user_info, extras_windowed_playback = settings.get_resolution, settings.metadata_user_info, settings.extras_windowed_playback
extras_enable_scrollbars, extras_exclude_non_acting = settings.extras_enable_scrollbars, settings.extras_exclude_non_acting
tmdb_image_base = 'https://image.tmdb.org/t/p/%s%s'
backup_cast_thumbnail = get_icon('genre_family')
roles_exclude = ('himself', 'herself', 'self', 'narrator', 'voice', 'voice (voice)')
button_ids = [10, 11, 50]
genres_exclude = (10763, 10764, 10767)		
gender_dict = {0: '', 1: ls(32844), 2: ls(32843), 3: ''}
more_from_movies_id, more_from_tvshows_id, trivia_id, videos_id, more_from_director_id = 2050, 2051, 2052, 2053, 2054
tmdb_list_ids = (more_from_movies_id, more_from_tvshows_id, more_from_director_id)
empty_check = (None, 'None', '')
separator, count_insert = '[COLOR %s][B]  •  [/B][/COLOR]', 'x%s'
_images = Images().run

class People(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
		self.control_id = None
		self.current_year = get_datetime(string=True).split('-')[0]
		self.set_starting_constants(kwargs)
		self.make_person_data()
		self.set_properties()
		self.tasks = (self.set_infoline1, self.make_trivia, self.make_videos, self.make_movies, self.make_tvshows, self.make_director)

	def onInit(self):
		self.set_home_property('window_loaded', 'true')
		for i in self.tasks: Thread(target=i).start()
		self.set_default_focus()
		if self.starting_position:
			try:
				window_id, focus = self.starting_position
				self.sleep(750)
				self.setFocusId(window_id)
				self.select_item(window_id, focus)
			except: self.set_default_focus()
		else: self.set_default_focus()

	def set_default_focus(self):
		try: self.setFocusId(10)
		except: self.close()

	def run(self):
		self.doModal()
		self.clearProperties()

	def onClick(self, controlID):
		self.control_id = None
		if controlID in button_ids:
			if controlID == 10:
				_images({'mode': 'people_image_results', 'actor_name': self.person_name, 'actor_id': self.person_id, 'actor_imdb_id': self.person_imdb_id,
							'actor_image': self.person_image, 'page_no': 1, 'rolling_count_list': [0]})
			elif controlID == 11:
				_images({'mode': 'people_tagged_image_results', 'actor_name': self.person_name, 'actor_id': self.person_id})
			elif controlID == 50:
				self.show_text_media(text=self.person_biography)
		else: self.control_id = controlID

	def onAction(self, action):
		if action in self.closing_actions: return window_manager(self)
		if action == self.info_action:
			focus_id = self.getFocusId()
			tmdb_list_ids = (more_from_movies_id, more_from_tvshows_id, more_from_director_id)
			if not focus_id in tmdb_list_ids: return
			show_busy_dialog()
			from modules.metadata import movie_meta, tvshow_meta
			chosen_listitem = self.get_listitem(focus_id)
			media_type = 'movie' if focus_id in (more_from_movies_id, more_from_director_id) else 'tvshow'
			function = movie_meta if media_type == 'movie' else tvshow_meta
			meta = function('tmdb_id', chosen_listitem.getProperty('tmdb_id'), metadata_user_info(), get_datetime())
			hide_busy_dialog()
			self.show_extrainfo(media_type, meta, meta.get('poster', empty_poster))
		if not self.control_id: return
		if action in self.selection_actions:
			chosen_listitem = self.get_listitem(self.control_id)
			chosen_var = chosen_listitem.getProperty(self.item_action_dict[self.control_id])
			if self.control_id in (more_from_movies_id, more_from_tvshows_id, more_from_director_id):
				if self.control_id in (more_from_movies_id, more_from_director_id): media_type = 'movie'
				else: media_type = 'tvshow'
				self.set_current_params()
				self.new_params = {'mode': 'extras_menu_choice', 'tmdb_id': chosen_var, 'media_type': media_type, 'is_external': self.is_external, 'stacked': 'true'}
				return window_manager(self)
			elif self.control_id == trivia_id:
				end_index = self.show_text_media(text=self.get_attribute(self, chosen_var), current_index=self.get_position(self.control_id))
				self.select_item(self.control_id, end_index)
			elif self.control_id == videos_id:
				thumb = chosen_listitem.getProperty('thumbnail')
				chosen = dialogs.imdb_videos_choice(self.get_attribute(self, chosen_var)[self.get_position(self.control_id)]['videos'], thumb)
				if not chosen: return
				if extras_windowed_playback(): return self.open_window(('windows.videoplayer', 'VideoPlayer'), 'videoplayer.xml', video=chosen)
				self.set_current_params()
				self.window_player_url = chosen
				return window_player(self)

	def set_infoline1(self):
		gender, age = self.person_gender or None, '%syo' % self.person_age if self.person_age else None
		birthday = self.person_birthday
		if birthday and self.person_deathday: birthday += '  [B]-[/B]  %s' % self.person_deathday
		self.set_label(2001, self.separator.join([i for i in (gender, age, birthday) if i]))

	def make_movies(self):
		self.make_more_from('movie')

	def make_tvshows(self):
		self.make_more_from('tvshow')

	def make_director(self):
		self.make_more_from('director')

	def show_extrainfo(self, media_type, meta, poster):
		text = dialogs.media_extra_info_choice({'media_type': media_type, 'meta': meta})
		return self.show_text_media(text=text, poster=poster)

	def make_person_data(self):
		if self.query not in empty_check:
			try:
				data = tmdb_people_info(self.query)
				if len(data) > 1 and self.reference_tmdb_id not in empty_check:
					for item in data:
						known_for = item.get('known_for', [])
						if known_for:
							known_for_tmdb_ids = [i['id'] for i in known_for]
							if self.reference_tmdb_id in known_for_tmdb_ids:
								self.person_id = item['id']
								break
				if not self.person_id:
					try: self.person_id = data[0]['id']
					except: pass
			except: self.person_id = self.actor_id
		else: self.person_id = self.actor_id
		if not self.person_id:
			notification(32760)
			return self.close()
		person_info = tmdb_people_full_info(self.person_id)
		if person_info.get('biography', None) in ('', None): person_info = tmdb_people_full_info(self.person_id, 'en')
		self.person_imdb_id = person_info['imdb_id']
		self.person_name = person_info['name']
		image_path = person_info['profile_path']
		if image_path: self.person_image = tmdb_image_base % ('h632', image_path)
		else: self.person_image = backup_cast_thumbnail
		try: self.person_gender = gender_dict[person_info.get('gender')]
		except: self.person_gender = ''
		place_of_birth = person_info.get('place_of_birth')
		if place_of_birth: self.person_place_of_birth = place_of_birth
		else: self.person_place_of_birth = ''
		biography = person_info.get('biography', None)
		if biography: self.person_biography = biography
		else: self.person_biography = ''
		birthday = person_info.get('birthday')
		if birthday: self.person_birthday = birthday
		else: self.person_birthday = ''
		deathday = person_info.get('deathday')
		if deathday: self.person_deathday = deathday
		else: self.person_deathday = ''
		if self.person_deathday: self.person_age = calculate_age(self.person_birthday, '%Y-%m-%d', self.person_deathday)
		elif self.person_birthday: self.person_age = calculate_age(self.person_birthday, '%Y-%m-%d')
		else:self.person_age = ''
		self.imdb_id = person_info['imdb_id']
		try:
			more_from_data = person_info['combined_credits']
			acting_data = more_from_data['cast']
			directing_data = more_from_data['crew']
			self.movie_data = [i for i in acting_data if i['media_type'] == 'movie']
			self.tvshow_data = [i for i in acting_data if i['media_type'] == 'tv']
			self.director_data = [i for i in directing_data if i['job'].lower() == 'director']
		except: self.movie_data, self.tvshow_data, self.director_data = [], [], []

	def make_more_from(self, media_type):
		try:
			if media_type == 'movie':
				list_type, _id, data, date_key = media_type, more_from_movies_id, self.movie_data, 'release_date'
				if self.exclude_non_acting:
					try: data = [i for i in data if not 99 in i['genre_ids'] and not i['character'].lower() in roles_exclude]
					except: pass
			elif media_type == 'tvshow':
				list_type, _id, data, date_key = media_type, more_from_tvshows_id, self.tvshow_data, 'first_air_date'
				if self.exclude_non_acting:
					try: data = [i for i in data if not any(x in genres_exclude for x in i['genre_ids']) and not i['character'].lower() in roles_exclude]
					except: pass
			else: list_type, _id, data, date_key = 'movie', more_from_director_id, self.director_data, 'release_date'
			data = self.sort_items_by_release(data, date_key)
			item_list = list(self.make_tmdb_listitems(data, list_type))
			self.setProperty('more_from_%s.number' % media_type, count_insert % len(item_list))
			self.item_action_dict[_id] = 'tmdb_id'
			self.add_items(_id, item_list)
		except: pass

	def make_videos(self):
		def builder():
			for item in self.all_videos:
				try:
					listitem = self.make_listitem()
					listitem.setProperty('name', item['title'])
					listitem.setProperty('thumbnail', item['poster'])
					listitem.setProperty('content_list', 'all_videos')
					yield listitem
				except: pass
		try:
			self.all_videos = imdb_videos(self.imdb_id)
			item_list = list(builder())
			self.setProperty('imdb_videos.number', count_insert % len(item_list))
			self.item_action_dict[videos_id] = 'content_list'
			self.add_items(videos_id, item_list)
		except: pass

	def make_trivia(self):
		if not self.person_imdb_id: return
		def builder():
			for item in self.all_trivia:
				try:
					listitem = self.make_listitem()
					listitem.setProperty('text', item)
					listitem.setProperty('content_list', 'all_trivia')
					yield listitem
				except: pass
		try:
			self.all_trivia = imdb_people_trivia(self.person_imdb_id)
			item_list = list(builder())
			self.setProperty('imdb_trivia.number', count_insert % len(item_list))
			self.item_action_dict[trivia_id] = 'content_list'
			self.add_items(trivia_id, item_list)
		except: pass

	def make_tmdb_listitems(self, data, media_type):
		used_ids = []
		append = used_ids.append
		name_key = 'title' if media_type == 'movie' else 'name'
		release_key = 'release_date' if media_type == 'movie' else 'first_air_date'
		for item in data:
			try:
				tmdb_id = item['id']
				if tmdb_id in used_ids: continue
				listitem = self.make_listitem()
				poster_path = item['poster_path']
				if not poster_path: thumbnail = empty_poster
				else: thumbnail = tmdb_image_base % (self.poster_resolution, poster_path)
				year = item.get(release_key)
				if year in (None, ''): year = 'N/A'
				else:
					try: year = year.split('-')[0]
					except: pass
				listitem.setProperty('name', item[name_key])
				listitem.setProperty('release_date', year)
				listitem.setProperty('vote_average', '%.1f' % item['vote_average'])
				listitem.setProperty('thumbnail', thumbnail)
				listitem.setProperty('tmdb_id', str(tmdb_id))
				append(tmdb_id)
				yield listitem
			except: pass

	def sort_items_by_release(self, data, key):
		blank = [i for i in data if not i.get(key, None)]
		data = [i for i in data if not i in blank]
		future = sorted([i for i in data if i[key].split('-')[0] > self.current_year], key=lambda x: x[key], reverse=True)
		present = sorted([i for i in data if i[key] and i not in future], key=lambda x: x[key], reverse=True)
		return present + future + blank

	def show_text_media(self, text='', poster=None, current_index=None):
		return self.open_window(('windows.extras', 'ShowTextMedia'), 'textviewer_media.xml', text=text, poster=poster or self.person_image, current_index=current_index)

	def set_current_params(self, set_starting_position=True):
		self.current_params = {'mode': 'person_data_dialog', 'query': self.query, 'actor_name': self.person_name, 'actor_image': self.person_image, 'stacked': 'true',
								'actor_id': self.person_id, 'reference_tmdb_id': self.reference_tmdb_id, 'is_external': self.is_external}
		if set_starting_position: self.current_params['starting_position'] = [self.control_id, self.get_position(self.control_id)]

	def set_starting_constants(self, kwargs):
		self.separator = separator % self.highlight_var()
		self.item_action_dict = {}
		self.current_params, self.new_params = {}, {}
		self.person_id = None
		self.is_external = kwargs.get('is_external', 'false').lower()
		self.query = kwargs.get('query', '')
		self.actor_id = kwargs.get('actor_id', '')
		self.reference_tmdb_id = kwargs.get('reference_tmdb_id', '')
		self.starting_position = kwargs.get('starting_position', None)
		self.enable_scrollbars = extras_enable_scrollbars()
		self.exclude_non_acting = extras_exclude_non_acting()
		self.poster_resolution = get_resolution()['poster']

	def set_properties(self):
		self.setProperty('name', self.person_name)
		self.setProperty('id', str(self.person_id))
		self.setProperty('image', self.person_image)
		self.setProperty('fanart', addon_fanart)
		self.setProperty('gender', self.person_gender)
		self.setProperty('place_of_birth', self.person_place_of_birth)
		self.setProperty('biography', self.person_biography)
		self.setProperty('birthday', self.person_birthday)
		self.setProperty('deathday', self.person_deathday)
		self.setProperty('age', str(self.person_age))
		self.setProperty('enable_scrollbars', self.enable_scrollbars)
