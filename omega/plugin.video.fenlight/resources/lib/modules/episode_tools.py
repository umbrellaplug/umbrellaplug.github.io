# -*- coding: utf-8 -*-
import sys
import json
import random
from datetime import date
from modules import kodi_utils, settings
from modules.sources import Sources
from modules.metadata import episodes_meta, all_episodes_meta
from modules.watched_status import get_next_episodes, get_hidden_progress_items, watched_info_episode, get_next
from modules.utils import adjust_premiered_date, get_datetime, make_thread_list, title_key
# logger = kodi_utils.logger

get_property, set_property, add_items = kodi_utils.get_property, kodi_utils.set_property, kodi_utils.add_items
make_listitem, set_content, end_directory, set_view_mode = kodi_utils.make_listitem, kodi_utils.set_content, kodi_utils.end_directory, kodi_utils.set_view_mode
get_icon, addon_fanart = kodi_utils.get_icon, kodi_utils.get_addon_fanart()
build_url, notification = kodi_utils.build_url, kodi_utils.notification 
watched_indicators, date_offset = settings.watched_indicators, settings.date_offset
window_prop = 'fenlight.random_episode_history'

class EpisodeTools:
	def __init__(self, meta, nextep_settings=None):
		self.meta = meta
		self.meta_get = self.meta.get
		self.nextep_settings = nextep_settings

	def next_episode_info(self):
		try:
			play_type = self.nextep_settings['play_type']
			current_date = get_datetime()
			season_data = self.meta_get('season_data')
			current_season, current_episode = int(self.meta_get('season')), int(self.meta_get('episode'))
			season, episode = get_next(current_season, current_episode, watched_info_episode(self.meta_get('tmdb_id')), season_data, 0)
			ep_data = episodes_meta(season, self.meta)
			if not ep_data: return 'no_next_episode'
			ep_data = next((i for i in ep_data if i['episode'] == episode), None)
			if not ep_data: return 'no_next_episode'
			airdate = ep_data['premiered']
			d = airdate.split('-')
			episode_date = date(int(d[0]), int(d[1]), int(d[2]))
			if current_date < episode_date: return 'no_next_episode'
			custom_title = self.meta_get('custom_title', None)
			title = custom_title or self.meta_get('title')
			display_name = '%s - %dx%.2d' % (title, int(season), int(episode))
			self.meta.update({'media_type': 'episode', 'rootname': display_name, 'season': season, 'ep_name': ep_data['title'], 'ep_thumb': ep_data.get('thumb', None),
							'episode': episode, 'premiered': airdate, 'plot': ep_data['plot']})
			url_params = {'media_type': 'episode', 'tmdb_id': self.meta_get('tmdb_id'), 'tvshowtitle': self.meta_get('rootname'), 'season': season,
						'episode': episode, 'background': 'true', 'nextep_settings': self.nextep_settings, 'play_type': play_type}
			if play_type == 'autoscrape_nextep': url_params['prescrape'] = 'false'
			if custom_title: url_params['custom_title'] = custom_title
			if 'custom_year' in self.meta: url_params['custom_year'] = self.meta_get('custom_year')
		except: url_params = 'error'
		return url_params

	def get_random_episode(self, continual=False, first_run=True):
		try:
			adjust_hours, current_date = date_offset(), get_datetime()
			tmdb_id = self.meta_get('tmdb_id')
			tmdb_key = str(tmdb_id)
			episodes_data = [i for i in all_episodes_meta(self.meta) if i['premiered'] and adjust_premiered_date(i['premiered'], adjust_hours)[0] <= current_date]
			if continual:
				episode_list = []
				try:
					episode_history = json.loads(get_property(window_prop))
					if tmdb_key in episode_history: episode_list = episode_history[tmdb_key]
					else: set_property(window_prop, '')
				except: set_property(window_prop, '')
				episodes_data = [i for i in episodes_data if not i in episode_list]
				if not episodes_data:
					set_property(window_prop, '')
					return self.get_random_episode(continual=True)
			chosen_episode = random.choice(episodes_data)
			if continual:
				episode_list.append(chosen_episode)
				episode_history = {tmdb_key: episode_list}
				set_property(window_prop, json.dumps(episode_history))
			title, season, episode = self.meta['title'], int(chosen_episode['season']), int(chosen_episode['episode'])
			query = title + ' S%.2dE%.2d' % (season, episode)
			display_name = '%s - %dx%.2d' % (title, season, episode)
			ep_name, plot = chosen_episode['title'], chosen_episode['plot']
			ep_thumb = chosen_episode.get('thumb', None)
			try: premiered = adjust_premiered_date(chosen_episode['premiered'], adjust_hours)[1]
			except: premiered = chosen_episode['premiered']
			self.meta.update({'media_type': 'episode', 'rootname': display_name, 'season': season, 'ep_name': ep_name, 'ep_thumb': ep_thumb,
							'episode': episode, 'premiered': premiered, 'plot': plot})
			url_params = {'mode': 'playback.media', 'media_type': 'episode', 'tmdb_id': tmdb_id, 'tvshowtitle': self.meta_get('rootname'), 'season': season, 'episode': episode,
						'autoplay': 'true'}
			if continual: url_params['random_continual'] = 'true'
			else: url_params['random'] = 'true'
			if not first_run:
				url_params['background'] = 'true'
				url_params['play_type'] = 'random_continual'
		except: url_params = 'error'
		return url_params

	def play_random(self):
		url_params = self.get_random_episode()
		if url_params == 'error': return notification('Single Random Play Error', 3000)
		return Sources().playback_prep(url_params)

	def play_random_continual(self, first_run=True):
		url_params = self.get_random_episode(continual=True, first_run=first_run)
		if url_params == 'error': return notification('Continual Random Play Error', 3000)
		return Sources().playback_prep(url_params)

	def auto_nextep(self):
		url_params = self.next_episode_info()
		if url_params == 'error': return notification('Next Episode Error', 3000)
		elif url_params == 'no_next_episode': return
		return Sources().playback_prep(url_params)

def build_next_episode_manager():
	def _process(item):
		try:
			listitem = make_listitem()
			tmdb_id, title = item['media_ids']['tmdb'], item['title']
			if int(tmdb_id) in hidden_list: display, action = 'Unhide [B]%s[/B] [COLOR=red][HIDDEN][/COLOR]' % title, 'unhide'
			else: display, action = 'Hide [B]%s[/B]' % title, 'hide'
			url_params = {'mode': mode, 'action': action, 'media_type': 'shows', 'media_id': tmdb_id, 'section': 'progress_watched'}
			url = build_url(url_params)
			listitem.setLabel(display)
			listitem.setArt({'poster': icon, 'fanart': addon_fanart, 'icon': icon})
			info_tag = listitem.getVideoInfoTag()
			info_tag.setPlot(' ')
			append({'listitem': (url, listitem, False), 'sort_title': title})
		except: pass
	handle = int(sys.argv[1])
	list_items = []
	append = list_items.append
	indicators = watched_indicators()
	show_list = get_next_episodes(0)
	hidden_list = get_hidden_progress_items(indicators)
	if indicators == 0: icon, mode = get_icon('folder'), 'hide_unhide_progress_items'
	else: icon, mode = get_icon('trakt'), 'trakt.hide_unhide_progress_items'
	threads = list(make_thread_list(_process, show_list))
	[i.join() for i in threads]
	item_list = sorted(list_items, key=lambda k: (title_key(k['sort_title'])), reverse=False)
	item_list = [i['listitem'] for i in item_list]
	add_items(handle, item_list)
	set_content(handle, '')
	end_directory(handle, cacheToDisc=False)
	set_view_mode('view.main', '')