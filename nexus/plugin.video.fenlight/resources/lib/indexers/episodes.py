# -*- coding: utf-8 -*-
import sys
from apis.trakt_api import trakt_watchlist, trakt_get_my_calendar
from caches.favorites_cache import favorites_cache
from modules import kodi_utils, settings, watched_status as ws
from modules.metadata import tvshow_meta, episodes_meta, all_episodes_meta
from modules.utils import jsondate_to_datetime, adjust_premiered_date, make_day, get_datetime, title_key, date_difference, make_thread_list_enumerate
# logger = kodi_utils.logger

set_view_mode, external, home = kodi_utils.set_view_mode, kodi_utils.external, kodi_utils.home
add_items, set_content, set_sort_method, end_directory = kodi_utils.add_items, kodi_utils.set_content, kodi_utils.set_sort_method, kodi_utils.end_directory
date_offset_info, default_all_episodes, nextep_include_unwatched = settings.date_offset, settings.default_all_episodes, settings.nextep_include_unwatched
nextep_airing_today, nextep_sort_key, nextep_sort_direction = settings.nextep_airing_today, settings.nextep_sort_key, settings.nextep_sort_direction
nextep_include_unaired, ep_display_format, widget_hide_watched = settings.nextep_include_unaired, settings.single_ep_display_format, settings.widget_hide_watched
make_listitem, build_url, xbmc_actor, set_category = kodi_utils.make_listitem, kodi_utils.build_url, kodi_utils.xbmc_actor, kodi_utils.set_category
nextep_limit_history, nextep_limit, tmdb_api_key, mpaa_region = settings.nextep_limit_history, settings.nextep_limit, settings.tmdb_api_key, settings.mpaa_region
get_property, nextep_include_airdate, calendar_sort_order = kodi_utils.get_property, settings.nextep_include_airdate, settings.calendar_sort_order
watched_indicators_info, nextep_method, show_specials, flatten_episodes = settings.watched_indicators, settings.nextep_method, settings.show_specials, settings.flatten_episodes
single_ep_unwatched_episodes = settings.single_ep_unwatched_episodes
get_watched_status_episode, get_bookmarks_episode, get_progress_status_episode = ws.get_watched_status_episode, ws.get_bookmarks_episode, ws.get_progress_status_episode
get_in_progress_episodes, get_next_episodes, get_recently_watched = ws.get_in_progress_episodes, ws.get_next_episodes, ws.get_recently_watched
get_bookmarks_all_episode, get_progress_status_all_episode = ws.get_bookmarks_all_episode, ws.get_progress_status_all_episode
get_hidden_progress_items, get_database, watched_info_episode, get_next = ws.get_hidden_progress_items, ws.get_database, ws.watched_info_episode, ws.get_next
get_watched_status_tvshow, watched_info_tvshow = ws.get_watched_status_tvshow, ws.watched_info_tvshow
string =  str
poster_empty, fanart_empty = kodi_utils.empty_poster, kodi_utils.addon_fanart()
run_plugin, unaired_label, tmdb_poster = 'RunPlugin(%s)', '[COLOR red][I]%s[/I][/COLOR]', 'https://image.tmdb.org/t/p/w780%s'
upper = string.upper
content_type = 'episodes'
list_view, single_view = 'view.episodes', 'view.episodes_single'
category_name_dict = {'episode.progress': 'In Progress Episodes', 'episode.recently_watched': 'Recently Watched Episodes', 'episode.next': 'Next Episodes',
					'episode.trakt': {'true': 'Recently Aired Episodes', None: 'Trakt Calendar'}}

def build_episode_list(params):
	def _process():
		for item in episodes_data:
			try:
				cm = []
				cm_append = cm.append
				listitem = make_listitem()
				set_properties = listitem.setProperties
				item_get = item.get
				season, episode, ep_name = item_get('season'), item_get('episode'), item_get('title')
				season_special = season == 0
				episode_date, premiered = adjust_premiered_date(item_get('premiered'), adjust_hours)
				episode_type = item_get('episode_type') or ''
				episode_id = item_get('episode_id') or None
				thumb = item_get('thumb', None) or show_landscape or show_fanart
				try: year = premiered.split('-')[0]
				except: year = show_year or '2050'
				if not item_get('duration'): item['duration'] = show_duration
				if not episode_date or current_date < episode_date:
					display, unaired = unaired_label % ep_name, True
					item['title'] = display
				else: display, unaired = ep_name, False
				if season_special: playcount, progress = 0, None
				else:
					playcount = get_watched_status_episode(watched_info, (season, episode))
					if playcount and hide_watched: continue
					if total_seasons: progress = get_progress_status_all_episode(bookmarks, season, episode)
					else: progress = get_progress_status_episode(bookmarks, episode)
				options_params = build_url({'mode': 'options_menu_choice', 'content': 'episode', 'tmdb_id': tmdb_id, 'poster': show_poster, 'is_external': is_external})
				extras_params = build_url({'mode': 'extras_menu_choice', 'tmdb_id': tmdb_id, 'media_type': 'episode', 'is_external': is_external})
				url_params = build_url({'mode': 'playback.media', 'media_type': 'episode', 'tmdb_id': tmdb_id, 'season': season, 'episode': episode})
				cm_append(('[B]Extras[/B]', run_plugin % extras_params))
				cm_append(('[B]Options[/B]', run_plugin % options_params))
				cm_append(('[B]Playback Options[/B]', run_plugin % \
							build_url({'mode': 'playback_choice', 'media_type': 'episode', 'meta': tmdb_id, 'season': season, 'episode': episode, 'episode_id': episode_id})))
				if not unaired and not season_special:
					if playcount:
						cm_append(('[B]Mark Unwatched %s[/B]' % watched_title, run_plugin % build_url({'mode': 'watched_status.mark_episode', 'action': 'mark_as_unwatched',
													'tmdb_id': tmdb_id, 'tvdb_id': tvdb_id, 'season': season, 'episode': episode,  'title': title})))
					else: cm_append(('[B]Mark Watched %s[/B]' % watched_title, run_plugin % build_url({'mode': 'watched_status.mark_episode', 'action': 'mark_as_watched',
													'tmdb_id': tmdb_id, 'tvdb_id': tvdb_id, 'season': season, 'episode': episode,  'title': title})))
					if progress: cm_append(('[B]Clear Progress[/B]', run_plugin % build_url({'mode': 'watched_status.erase_bookmark', 'media_type': 'episode', 'tmdb_id': tmdb_id,
													'season': season, 'episode': episode, 'refresh': 'true'})))
				if is_external:
					cm_append(('[B]Refresh Widgets[/B]', run_plugin % build_url({'mode': 'refresh_widgets'})))
					cm_append(('[B]Reload Widgets[/B]', run_plugin % build_url({'mode': 'kodi_refresh'})))
				info_tag = listitem.getVideoInfoTag()
				info_tag.setMediaType('episode'), info_tag.setTitle(display), info_tag.setOriginalTitle(orig_title), info_tag.setTvShowTitle(title), info_tag.setGenres(genre)
				info_tag.setPlaycount(playcount), info_tag.setSeason(season), info_tag.setEpisode(episode), info_tag.setPlot(item_get('plot') or tvshow_plot)
				info_tag.setDuration(item_get('duration')), info_tag.setIMDBNumber(imdb_id), info_tag.setUniqueIDs({'imdb': imdb_id, 'tmdb': string(tmdb_id), 'tvdb': string(tvdb_id)})
				info_tag.setFirstAired(premiered)
				info_tag.setTvShowStatus(show_status)
				info_tag.setCountries(country), info_tag.setTrailer(trailer), info_tag.setDirectors(item_get('director'))
				info_tag.setYear(int(year)), info_tag.setRating(item_get('rating')), info_tag.setVotes(item_get('votes')), info_tag.setMpaa(mpaa)
				info_tag.setStudios(studio), info_tag.setWriters(item_get('writer'))
				info_tag.setCast([xbmc_actor(name=item['name'], role=item['role'], thumbnail=item['thumbnail']) for item in cast + item_get('guest_stars', [])])
				if progress and not unaired:
					info_tag.setResumePoint(float(progress))
					set_properties({'WatchedProgress': progress})
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt({'poster': show_poster, 'fanart': show_fanart, 'thumb': thumb, 'icon':thumb, 'clearlogo': show_clearlogo, 'landscape': show_landscape,
								'season.poster': season_poster, 'tvshow.poster': show_poster, 'tvshow.clearlogo': show_clearlogo})
				set_properties({'fenlight.extras_params': extras_params, 'fenlight.options_params': options_params, 'episode_type': episode_type})
				yield (url_params, listitem, False)
			except: pass
	handle, is_external, is_home, category_name = int(sys.argv[1]), external(), home(), 'Episodes'
	item_list = []
	append = item_list.append
	watched_indicators, adjust_hours = watched_indicators_info(), date_offset_info()
	current_date, hide_watched = get_datetime(), is_home and widget_hide_watched()
	watched_title = 'Trakt' if watched_indicators == 1 else 'Fen Light'
	meta = tvshow_meta('tmdb_id', params.get('tmdb_id'), tmdb_api_key(), mpaa_region(), current_date)
	meta_get = meta.get
	tmdb_id, tvdb_id, imdb_id, tvshow_plot, orig_title = meta_get('tmdb_id'), meta_get('tvdb_id'), meta_get('imdb_id'), meta_get('plot'), meta_get('original_title')
	title, show_year, rootname, show_duration, show_status = meta_get('title'), meta_get('year') or '2050', meta_get('rootname'), meta_get('duration'), meta_get('status')
	cast, mpaa, trailer, genre, studio, country = meta_get('cast', []), meta_get('mpaa'), string(meta_get('trailer')), meta_get('genre'), meta_get('studio'), meta_get('country')
	season = params['season']
	show_poster = meta_get('poster') or poster_empty
	show_fanart = meta_get('fanart') or fanart_empty
	show_clearlogo = meta_get('clearlogo') or ''
	show_landscape = meta_get('landscape') or ''
	watched_db = get_database(watched_indicators)
	watched_info = watched_info_episode(tmdb_id, watched_db)
	if season == 'all':
		total_seasons = meta_get('total_seasons')
		episodes_data = sorted(all_episodes_meta(meta, show_specials()), key=lambda x: (x['season'], x['episode']))
		bookmarks = get_bookmarks_all_episode(tmdb_id, total_seasons, watched_db)
		season_poster = show_poster
		category_name = 'Season %s' % season if total_seasons == 1 else 'Seasons 1-%s' % total_seasons
	else:
		total_seasons = None
		episodes_data = episodes_meta(season, meta)
		bookmarks = get_bookmarks_episode(tmdb_id, season, watched_db)
		try:
			poster_path = next((i['poster_path'] for i in meta_get('season_data') if i['season_number'] == int(season)), None)
			season_poster = tmdb_poster % poster_path if poster_path is not None else show_poster
		except: season_poster = show_poster
		category_name = 'Season %s' % season
	add_items(handle, list(_process()))
	set_sort_method(handle, content_type)
	set_content(handle, content_type)
	set_category(handle, category_name)
	end_directory(handle, cacheToDisc=False if is_external else True)
	set_view_mode(list_view, content_type, is_external)

def build_single_episode(list_type, params={}):
	def _get_category_name():
		try:
			cat_name = category_name_dict[list_type]
			if isinstance(cat_name, dict): cat_name = cat_name[params.get('recently_aired')]
		except: cat_name = 'Episodes'
		return cat_name
	def _process(_position, ep_data):
		try:
			ep_data_get = ep_data.get
			meta = tvshow_meta('trakt_dict', ep_data_get('media_ids'), api_key, mpaa_region_value, current_date)
			if not meta: return
			meta_get = meta.get
			cm = []
			cm_append = cm.append
			listitem = make_listitem()
			set_properties = listitem.setProperties
			orig_season, orig_episode = ep_data_get('season'), ep_data_get('episode')
			unwatched = ep_data_get('unwatched', False)
			_position = ep_data_get('custom_order', _position)
			tmdb_id, tvdb_id, imdb_id, title, show_year = meta_get('tmdb_id'), meta_get('tvdb_id'), meta_get('imdb_id'), meta_get('title'), meta_get('year') or '2050'
			season_data = meta_get('season_data')
			watched_info = watched_info_episode(meta_get('tmdb_id'), watched_db)
			if list_type_starts_with('next_'):
				orig_season, orig_episode = get_next(orig_season, orig_episode, watched_info, season_data, nextep_content)
				if not orig_season or not orig_episode: return
				playcount = 0
			episodes_data = episodes_meta(orig_season, meta)
			if not episodes_data: return
			item = next((i for i in episodes_data if i['episode'] == orig_episode), None)
			if not item: return
			item_get = item.get
			season, episode, ep_name = item_get('season'), item_get('episode'), item_get('title')
			episode_date, premiered = adjust_premiered_date(item_get('premiered'), adjust_hours)
			episode_type = item_get('episode_type') or ''
			episode_id = item_get('episode_id') or None
			if not episode_date or current_date < episode_date:
				if list_type_starts_with('next_'):
					if not episode_date: return
					if not include_unaired: return
					if not date_difference(current_date, episode_date, 7): return
				unaired = True
			else: unaired = False
			orig_title, rootname, trailer, genre, studio = meta_get('original_title'), meta_get('rootname'), string(meta_get('trailer')), meta_get('genre'), meta_get('studio')
			cast, mpaa, tvshow_plot, show_status = meta_get('cast', []), meta_get('mpaa'), meta_get('plot'), meta_get('status')
			show_poster = meta_get('poster') or poster_empty
			show_fanart = meta_get('fanart') or fanart_empty
			show_clearlogo = meta_get('clearlogo') or ''
			show_landscape = meta_get('landscape') or ''
			thumb = item_get('thumb', None) or show_landscape or show_fanart
			try: year = premiered.split('-')[0]
			except: year = show_year or '2050'
			try:
				poster_path = next((i['poster_path'] for i in season_data if i['season_number'] == int(season)), None)
				season_poster = tmdb_poster % poster_path if poster_path is not None else show_poster
			except: season_poster = show_poster
			str_season_zfill2, str_episode_zfill2 = string(season).zfill(2), string(episode).zfill(2)
			if display_format == 0: title_string = '%s: ' % title
			else: title_string = ''
			if display_format in (0, 1): seas_ep = '%sx%s - ' % (str_season_zfill2, str_episode_zfill2)
			else: seas_ep = ''
			bookmarks = get_bookmarks_episode(tmdb_id, season, watched_db)
			progress = get_progress_status_episode(bookmarks, episode)
			if not list_type_starts_with('next_'): playcount = get_watched_status_episode(watched_info, (season, episode))
			if list_type_starts_with('next_'):
				if include_airdate:
					if episode_date: display_premiered = '[%s] ' % make_day(current_date, episode_date)
					else: display_premiered = '[UNKNOWN] '
				else: display_premiered = ''
				if unwatched: highlight_start, highlight_end = '[COLOR darkgoldenrod]', '[/COLOR]'
				elif unaired: highlight_start, highlight_end = '[COLOR red]', '[/COLOR]'
				else: highlight_start, highlight_end = '', ''
				display = '%s%s%s%s%s%s' % (display_premiered, title_string, highlight_start, seas_ep, ep_name, highlight_end)
			elif list_type_compare == 'trakt_calendar':
				if episode_date: display_premiered = make_day(current_date, episode_date)
				else: display_premiered = 'UNKNOWN'
				display = '[%s] %s%s%s' % (display_premiered, title_string, seas_ep, ep_name)
			else: display = '%s%s%s' % (title_string, seas_ep, ep_name)
			if not item_get('duration'): item['duration'] = meta_get('duration')
			options_params = build_url({'mode': 'options_menu_choice', 'content': list_type, 'tmdb_id': tmdb_id, 'poster': show_poster, 'is_external': is_external})
			extras_params = build_url({'mode': 'extras_menu_choice', 'tmdb_id': tmdb_id, 'media_type': 'episode', 'is_external': is_external})
			url_params = build_url({'mode': 'playback.media', 'media_type': 'episode', 'tmdb_id': tmdb_id, 'season': season, 'episode': episode})
			cm_append(('[B]Extras[/B]', run_plugin % extras_params))
			cm_append(('[B]Options[/B]', run_plugin % options_params))
			cm_append(('[B]Playback Options[/B]', run_plugin % \
						build_url({'mode': 'playback_choice', 'media_type': 'episode', 'meta': tmdb_id, 'season': season, 'episode': episode, 'episode_id': episode_id})))
			if not unaired:
				if playcount:
					cm_append(('[B]Mark Unwatched %s[/B]' % watched_title, run_plugin % build_url({'mode': 'watched_status.mark_episode', 'action': 'mark_as_unwatched',
												'tmdb_id': tmdb_id, 'tvdb_id': tvdb_id, 'season': season, 'episode': episode,  'title': title})))
				else: cm_append(('[B]Mark Watched %s[/B]' % watched_title, run_plugin % build_url({'mode': 'watched_status.mark_episode', 'action': 'mark_as_watched',
												'tmdb_id': tmdb_id, 'tvdb_id': tvdb_id, 'season': season, 'episode': episode,  'title': title})))
				if progress:
					cm_append(('[B]Clear Progress[/B]', run_plugin % build_url({'mode': 'watched_status.erase_bookmark', 'media_type': 'episode', 'tmdb_id': tmdb_id,
												'season': season, 'episode': episode, 'refresh': 'true'})))
				if unwatched_info:
					total_aired_eps = meta_get('total_aired_eps')
					total_unwatched = get_watched_status_tvshow(watched_info_tvshow(watched_db).get(string(tmdb_id), None), total_aired_eps)[2]
					if total_aired_eps != total_unwatched: set_properties({'watchedepisodes': '1', 'unwatchedepisodes': string(total_unwatched)})
			if all_episodes:
				if all_episodes == 1 and meta_get('total_seasons') > 1: browse_params = {'mode': 'build_season_list', 'tmdb_id': tmdb_id}
				else: browse_params = {'mode': 'build_episode_list', 'tmdb_id': tmdb_id, 'season': 'all'}
			else: browse_params = {'mode': 'build_season_list', 'tmdb_id': tmdb_id}
			cm_append(('[B]Browse[/B]', window_command % build_url(browse_params)))
			if is_external:
				cm_append(('[B]Refresh Widgets[/B]', run_plugin % build_url({'mode': 'refresh_widgets'})))
				cm_append(('[B]Reload Widgets[/B]', run_plugin % build_url({'mode': 'kodi_refresh'})))
			info_tag = listitem.getVideoInfoTag()
			info_tag.setMediaType('episode'), info_tag.setOriginalTitle(orig_title), info_tag.setTvShowTitle(title), info_tag.setTitle(display), info_tag.setGenres(genre)
			info_tag.setPlaycount(playcount), info_tag.setSeason(season), info_tag.setEpisode(episode), info_tag.setPlot(item_get('plot') or tvshow_plot)
			info_tag.setDuration(item_get('duration')), info_tag.setIMDBNumber(imdb_id), info_tag.setUniqueIDs({'imdb': imdb_id, 'tmdb': string(tmdb_id), 'tvdb': string(tvdb_id)})
			info_tag.setFirstAired(premiered)
			info_tag.setCountries(meta_get('country', [])), info_tag.setTrailer(trailer), info_tag.setTvShowStatus(show_status)
			info_tag.setStudios(studio), info_tag.setWriters(item_get('writer')), info_tag.setDirectors(item_get('director'))
			info_tag.setYear(int(year)), info_tag.setRating(item_get('rating')), info_tag.setVotes(item_get('votes')), info_tag.setMpaa(mpaa)
			info_tag.setCast([xbmc_actor(name=item['name'], role=item['role'], thumbnail=item['thumbnail']) for item in cast + item_get('guest_stars', [])])
			if progress and not unaired:
				info_tag.setResumePoint(float(progress))
				set_properties({'WatchedProgress': progress})
			listitem.setLabel(display)
			listitem.addContextMenuItems(cm)
			listitem.setArt({'poster': show_poster, 'fanart': show_fanart, 'thumb': thumb, 'icon':thumb, 'clearlogo': show_clearlogo, 'landscape': show_landscape,
							'season.poster': season_poster, 'tvshow.poster': show_poster, 'tvshow.clearlogo': show_clearlogo})
			set_properties({'fenlight.extras_params': extras_params, 'fenlight.options_params': options_params, 'episode_type': episode_type})
			item_list_append({'list_items': (url_params, listitem, False), 'first_aired': premiered, 'name': '%s - %sx%s' % (title, str_season_zfill2, str_episode_zfill2),
							'unaired': unaired, 'last_played': ep_data_get('last_played', resinsert), 'sort_order': _position, 'unwatched': ep_data_get('unwatched')})
		except: pass
	handle, is_external, is_home, category_name = int(sys.argv[1]), external(), home(), 'Episodes'
	item_list, airing_today, unwatched, return_results = [], [], [], False
	resinsert = ''
	item_list_append = item_list.append
	window_command = 'ActivateWindow(Videos,%s,return)' if is_external else 'Container.Update(%s)'
	all_episodes, watched_indicators, display_format = default_all_episodes(), watched_indicators_info(), ep_display_format(is_external)
	current_date, adjust_hours, unwatched_info, hide_watched = get_datetime(), date_offset_info(), single_ep_unwatched_episodes(), is_home and widget_hide_watched()
	api_key, mpaa_region_value = tmdb_api_key(), mpaa_region()
	watched_db = get_database(watched_indicators)
	watched_title = 'Trakt' if watched_indicators == 1 else 'Fen Light'
	category_name = _get_category_name()
	if list_type == 'episode.next':
		include_unwatched, include_unaired, nextep_content = nextep_include_unwatched(), nextep_include_unaired(), nextep_method()
		sort_key, sort_direction = nextep_sort_key(), nextep_sort_direction()
		include_airdate = nextep_include_airdate()
		data = get_next_episodes(nextep_content)
		if nextep_limit_history(): data = data[:nextep_limit()]
		hidden_data = get_hidden_progress_items(watched_indicators)
		data = [i for i in data if not i['media_ids']['tmdb'] in hidden_data]
		if watched_indicators == 1: resformat, resinsert, list_type = '%Y-%m-%dT%H:%M:%S.%fZ', '2000-01-01T00:00:00.000Z', 'episode.next_trakt'
		else: resformat, resinsert, list_type = '%Y-%m-%d %H:%M:%S', '2000-01-01 00:00:00', 'episode.next_fenlight'
		if include_unwatched != 0:
			if include_unwatched in (1, 3):
				try:
					original_list = trakt_watchlist('watchlist', 'tvshow')
					unwatched.extend([{'media_ids': i['media_ids'], 'season': 1, 'episode': 0, 'unwatched': True, 'title': i['title']} for i in original_list])
				except: pass
			if include_unwatched in (2, 3):
				try: unwatched.extend([{'media_ids': {'tmdb': int(i['tmdb_id'])}, 'season': 1, 'episode': 0, 'unwatched': True, 'title': i['title']} \
									for i in favorites_cache.get_favorites('tvshow') if not int(i['tmdb_id']) in [x['media_ids']['tmdb'] for x in data]])
				except: pass
			data += unwatched
	elif list_type == 'episode.progress': data = get_in_progress_episodes()
	elif list_type == 'episode.recently_watched': data = get_recently_watched('episode')
	elif list_type == 'episode.trakt':
		recently_aired = params.get('recently_aired', None)
		data = trakt_get_my_calendar(recently_aired, get_datetime())
		list_type = 'episode.trakt_recently_aired' if recently_aired else 'episode.trakt_calendar'
		if flatten_episodes():
			try:
				duplicates = set()
				data.sort(key=lambda i: i['sort_title'])
				data = [i for i in data if not ((i['media_ids']['tmdb'], i['first_aired']) in duplicates or duplicates.add((i['media_ids']['tmdb'], i['first_aired'])))]
			except: pass
		else:
			try: data = sorted(data, key=lambda i: (i['sort_title'], i.get('first_aired', '2100-12-31')), reverse=True)
			except: data = sorted(data, key=lambda i: i['sort_title'], reverse=True)
	else: data, return_results = sorted(params, key=lambda i: i['custom_order']), True
	list_type_compare = list_type.split('episode.')[1]
	list_type_starts_with = list_type_compare.startswith
	threads = list(make_thread_list_enumerate(_process, data))
	[i.join() for i in threads]
	if return_results:
		return [(i['list_items'], i['sort_order']) for i in item_list]
	if list_type_starts_with('next_'):
		def func(function):
			if sort_key == 'name': return title_key(function)
			elif sort_key == 'last_played': return jsondate_to_datetime(function, resformat)
			else: return function
		if nextep_airing_today():
			airing_today = sorted([i for i in item_list if date_difference(current_date, jsondate_to_datetime(i.get('first_aired', '2100-12-31'), '%Y-%m-%d').date(), 0)],
									key=lambda i: func(i[sort_key]), reverse=sort_direction)
			item_list = [i for i in item_list if not i in airing_today]
		else: airing_today = []
		if sort_key == 'last_played':
			unwatched = sorted([i for i in item_list if i['unwatched']], key=lambda i: title_key(i['name']))
			item_list = sorted([i for i in item_list if not i['unwatched']], key=lambda i: func(i[sort_key]), reverse=sort_direction) + unwatched
		else: item_list = sorted(item_list, key=lambda i: func(i[sort_key]), reverse=sort_direction)
		item_list = airing_today + item_list
	else:
		item_list.sort(key=lambda i: i['sort_order'])
		if list_type_compare in ('trakt_calendar', 'trakt_recently_aired'):
			if list_type_compare == 'trakt_calendar': reverse = calendar_sort_order() == 0
			else: reverse = True
			try: item_list = sorted(item_list, key=lambda i: i.get('first_aired', '2100-12-31'), reverse=reverse)
			except:
				item_list = [i for i in item_list if i.get('first_aired') not in (None, 'None', '')]
				item_list = sorted(item_list, key=lambda i: i.get('first_aired'), reverse=reverse)
			if list_type_compare == 'trakt_calendar':
				airing_today = sorted([i for i in item_list if date_difference(current_date, jsondate_to_datetime(i.get('first_aired', '2100-12-31'), '%Y-%m-%d').date(), 0)],
										key=lambda i: i['first_aired'])
				item_list = [i for i in item_list if not i in airing_today]
				item_list = airing_today + item_list
	add_items(handle, [i['list_items'] for i in item_list])
	set_content(handle, content_type)
	set_category(handle, category_name)
	end_directory(handle, cacheToDisc=False)
	set_view_mode(single_view, content_type, is_external)
