# -*- coding: utf-8 -*-
from datetime import date
from modules import kodi_utils, settings
from modules.sources import Sources
from modules.metadata import episodes_meta, all_episodes_meta
from modules.watched_status import get_next_episodes, get_watched_info_tv, get_hidden_progress_items
from modules.utils import adjust_premiered_date, get_datetime, make_thread_list, title_key
# logger = kodi_utils.logger

Thread, get_property, set_property, add_dir, add_items = kodi_utils.Thread, kodi_utils.get_property, kodi_utils.set_property, kodi_utils.add_dir, kodi_utils.add_items
make_listitem, set_content, end_directory, set_view_mode = kodi_utils.make_listitem, kodi_utils.set_content, kodi_utils.end_directory, kodi_utils.set_view_mode
get_icon, addon_fanart, random = kodi_utils.get_icon, kodi_utils.addon_fanart, kodi_utils.random
ls, sys, build_url, json, notification = kodi_utils.local_string, kodi_utils.sys, kodi_utils.build_url, kodi_utils.json, kodi_utils.notification 
watched_indicators, ignore_articles = settings.watched_indicators, settings.ignore_articles
hidden_ind_str, hidden_str, heading, window_prop = ' [COLOR=red][B][%s][/B][/COLOR]', ls(32804).upper(), ls(32806), 'fen.random_episode_history'

class EpisodeTools:
	def __init__(self, meta, nextep_settings=None):
		self.meta = meta
		self.meta_get = self.meta.get
		self.nextep_settings = nextep_settings

	def get_next_episode_info(self):
		try:
			play_type = self.nextep_settings['play_type']
			current_date = get_datetime()
			season_data = self.meta_get('season_data')
			current_season, current_episode = int(self.meta_get('season')), int(self.meta_get('episode'))
			curr_season_data = [i for i in season_data if i['season_number'] == current_season][0]
			season = current_season if current_episode < curr_season_data['episode_count'] else current_season + 1
			episode = current_episode + 1 if current_episode < curr_season_data['episode_count'] else 1
			ep_data = episodes_meta(season, self.meta, settings.metadata_user_info())
			if not ep_data: return 'no_next_episode'
			try: ep_data = [i for i in ep_data if i['episode'] == episode][0]
			except: return 'no_next_episode'
			airdate = ep_data['premiered']
			d = airdate.split('-')
			episode_date = date(int(d[0]), int(d[1]), int(d[2]))
			if current_date < episode_date: return 'no_next_episode'
			custom_title = self.meta_get('custom_title', None)
			title = custom_title or self.meta_get('title')
			display_name = '%s - %dx%.2d' % (title, int(season), int(episode))
			episode_type = ep_data.get('episode_type', '')
			self.meta.update({'media_type': 'episode', 'rootname': display_name, 'season': season, 'ep_name': ep_data['title'], 'ep_thumb': ep_data.get('thumb', None),
							'episode': episode, 'premiered': airdate, 'plot': ep_data['plot'], 'episode_type': episode_type})
			url_params = {'media_type': 'episode', 'tmdb_id': self.meta_get('tmdb_id'), 'tvshowtitle': self.meta_get('rootname'), 'season': season,
						'episode': episode, 'background': 'true', 'nextep_settings': self.nextep_settings, 'play_type': play_type, 'meta': json.dumps(self.meta)}
			if custom_title: url_params['custom_title'] = custom_title
			if 'custom_year' in self.meta: url_params['custom_year'] = self.meta_get('custom_year')
		except: url_params = 'error'
		return url_params

	def get_random_episode(self, continual=False, first_run=True):
		try:
			meta_user_info, adjust_hours, current_date = settings.metadata_user_info(), settings.date_offset(), get_datetime()
			tmdb_id = self.meta_get('tmdb_id')
			tmdb_key = str(tmdb_id)		
			try: episodes_data = [i for i in all_episodes_meta(self.meta, meta_user_info) if i['premiered'] and adjust_premiered_date(i['premiered'], adjust_hours)[0] <= current_date]
			except: return None
			if continual:
				episode_list = []
				try:
					episode_history = json.loads(get_property(window_prop))
					if tmdb_key in episode_history: episode_list = episode_history[tmdb_key]
					else: set_property(window_prop, '')
				except: pass
				episodes_data = [i for i in episodes_data if not i in episode_list]
				if not episodes_data:
					set_property(window_prop, '')
					return self.get_random_episode(continual=True)
			chosen_episode = random.choice(episodes_data)
			if continual:
				episode_list.append(chosen_episode)
				episode_history = {str(tmdb_id): episode_list}
				set_property(window_prop, json.dumps(episode_history))
			title, season, episode = self.meta['title'], int(chosen_episode['season']), int(chosen_episode['episode'])
			query = title + ' S%.2dE%.2d' % (season, episode)
			display_name = '%s - %dx%.2d' % (title, season, episode)
			episode_type = chosen_episode.get('episode_type', '')
			ep_name, plot = chosen_episode['title'], chosen_episode['plot']
			ep_thumb = chosen_episode.get('thumb', None)
			try: premiered = adjust_premiered_date(chosen_episode['premiered'], adjust_hours)[1]
			except: premiered = chosen_episode['premiered']
			self.meta.update({'media_type': 'episode', 'rootname': display_name, 'season': season, 'ep_name': ep_name, 'ep_thumb': ep_thumb,
							'episode': episode, 'premiered': premiered, 'plot': plot, 'episode_type': episode_type})
			url_params = {'mode': 'playback.media', 'media_type': 'episode', 'tmdb_id': tmdb_id, 'tvshowtitle': self.meta_get('rootname'), 'season': season, 'episode': episode,
						'autoplay': 'true', 'meta': json.dumps(self.meta)}
			if continual: url_params['random_continual'] = 'true'
			else: url_params['random'] = 'true'
			if not first_run:
				url_params['background'] = 'true'
				url_params['play_type'] = 'random_continual'
		except: url_params = 'error'
		return url_params

	def auto_nextep(self):
		url_params = self.get_next_episode_info()
		if url_params == 'error': return notification('%s %s' % (ls(33041), ls(32574)), 3000)
		elif url_params == 'no_next_episode': return
		return Sources().playback_prep(url_params)

	def play_random(self):
		url_params = self.get_random_episode()
		if url_params == 'error': return notification('%s %s' % (ls(32541), ls(32574)), 3000)
		return Sources().playback_prep(url_params)

	def play_random_continual(self, first_run=True):
		url_params = self.get_random_episode(continual=True, first_run=first_run)
		if url_params == 'error': return notification('%s %s' % (ls(32542), ls(32574)), 3000)
		return Sources().playback_prep(url_params)

def build_next_episode_manager():
	def _process(item):
		try:
			listitem = make_listitem()
			tmdb_id, title = item['media_ids']['tmdb'], item['title']
			if tmdb_id in hidden_list: display, action = title + hidden_ind_str % hidden_str, 'unhide'
			else: display, action = title, 'hide'
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
	show_list = get_next_episodes(get_watched_info_tv(indicators))
	hidden_list = get_hidden_progress_items(indicators)
	if indicators == 0: icon, mode = get_icon('folder'), 'hide_unhide_progress_items'
	else: icon, mode = get_icon('trakt'), 'trakt.hide_unhide_progress_items'
	threads = list(make_thread_list(_process, show_list))
	[i.join() for i in threads]
	item_list = sorted(list_items, key=lambda k: (title_key(k['sort_title'], ignore_articles())), reverse=False)
	item_list = [i['listitem'] for i in item_list]
	add_dir({'mode': 'nill'}, '[I][COLOR=grey2]%s[/COLOR][/I]' % heading.upper(), handle, iconImage='settings', isFolder=False)
	add_items(handle, item_list)
	set_content(handle, '')
	end_directory(handle, cacheToDisc=False)
	set_view_mode('view.main', '')
