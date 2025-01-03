# -*- coding: utf-8 -*-
import re
import json
from windows.base_window import open_window, create_window
from caches.base_cache import refresh_cached_data
from caches.episode_groups_cache import episode_groups_cache
from caches.settings_cache import get_setting, set_setting, set_default, default_setting_values
from modules.downloader import manager
from modules import kodi_utils, settings, metadata
from modules.source_utils import clear_scrapers_cache, get_aliases_titles, make_alias_dict, audio_filter_choices, source_filters
from modules.utils import get_datetime, title_key, adjust_premiered_date, append_module_to_syspath, manual_module_import
# logger = kodi_utils.logger

ok_dialog, container_content, close_all_dialog, external = kodi_utils.ok_dialog, kodi_utils.container_content, kodi_utils.close_all_dialog, kodi_utils.external
set_property, get_icon, kodi_dialog, open_settings = kodi_utils.set_property, kodi_utils.get_icon, kodi_utils.kodi_dialog, kodi_utils.open_settings
show_busy_dialog, hide_busy_dialog, notification, confirm_dialog = kodi_utils.show_busy_dialog, kodi_utils.hide_busy_dialog, kodi_utils.notification, kodi_utils.confirm_dialog
external_scraper_settings, kodi_refresh, autoscrape_next_episode = kodi_utils.external_scraper_settings, kodi_utils.kodi_refresh, settings.autoscrape_next_episode
select_dialog, autoplay_next_episode, quality_filter = kodi_utils.select_dialog, settings.autoplay_next_episode, settings.quality_filter
numeric_input, container_update, activate_window, folder_path = kodi_utils.numeric_input, kodi_utils.container_update, kodi_utils.activate_window, kodi_utils.folder_path
poster_empty, audio_filters, mpaa_region, preferred_autoplay = kodi_utils.empty_poster, settings.audio_filters, settings.mpaa_region, settings.preferred_autoplay
extras_button_label_values, jsonrpc_get_addons, tmdb_api_key = kodi_utils.extras_button_label_values, kodi_utils.jsonrpc_get_addons, settings.tmdb_api_key
extras_enabled_menus, active_internal_scrapers, auto_play = settings.extras_enabled_menus, settings.active_internal_scrapers, settings.auto_play
quality_filter, date_offset, trakt_user_active = settings.quality_filter, settings.date_offset, settings.trakt_user_active
single_ep_list, scraper_names = kodi_utils.single_ep_list, kodi_utils.scraper_names

def preferred_autoplay_choice(params):
	def _default_choices():
		return [{'name': '1st Sort', 'value': 'Choose 1st Sort Param'}, {'name': '2nd Sort', 'value': 'Choose 2nd Sort Param'},
				{'name': '3rd Sort', 'value': 'Choose 3rd Sort Param'}, {'name': '4th Sort', 'value': 'Choose 4th Sort Param'},
				{'name': '5th Sort', 'value': 'Choose 5th Sort Param'}]
	def _beginning_choices():
		defaults = _default_choices()
		for count, item in enumerate(preferred_autoplay()): defaults[count]['value'] = item
		return defaults
	def _rechoose_checker(choice):
		if choice['value'].startswith('Choose'): return (choice, True)
		clear_choice = confirm_dialog(heading='Current Param Active', text='This sort slot is already filled.[CR]Please choose what action to take.',
						ok_label='Remake Slot', cancel_label='Clear Slot')
		if clear_choice == None: new_default, ask_params = (choice, False)
		else:
			choice_index = choices.index(choice)
			new_default = _default_choices()[choice_index]
			choices[choice_index] = new_default
		return (new_default, clear_choice)
	def _param_choices(choice):
		used_filters = [i['value'] for i in choices if not i['value'].startswith('Choose')]
		unused_filters = [i for i in filters_choice if not i[1] in used_filters]
		param_list_items = [{'line1': i[0], 'line2': i[1]} for i in unused_filters]
		param_kwargs = {'items': json.dumps(param_list_items), 'multi_line': 'true', 'heading': 'Choose Sort to Top Params for Autoplay', 'narrow_window': 'true'}
		param_choice = select_dialog(unused_filters, **param_kwargs)
		if param_choice == None: return ''
		choice['value'] = param_choice[1]
		return choice
	def _make_settings():
		new_settings = [i['value'] for i in choices if not i['value'].startswith('Choose')]
		if not new_settings: set_setting('preferred_autoplay', 'empty_setting')
		else: set_setting('preferred_autoplay', ', '.join(new_settings))
	filters_choice = [(i[0], i[1].replace('[B]', '').replace('[/B]', '')) for i in source_filters]
	choices = params.get('choices') or _beginning_choices()
	list_items = [{'line1': i['name'], 'line2': i['value']} for i in choices]
	kwargs = {'items': json.dumps(list_items), 'multi_line': 'true', 'heading': 'Choose Sort to Top Params for Autoplay', 'narrow_window': 'true'}
	choice = select_dialog(choices, **kwargs)
	if choice == None: return _make_settings()
	choice, ask_params = _rechoose_checker(choice)
	if not ask_params: return preferred_autoplay_choice({'choices': choices})
	param_choice = _param_choices(choice)
	if not param_choice: return preferred_autoplay_choice({'choices': choices})
	choices[choices.index(choice)] = param_choice
	return preferred_autoplay_choice({'choices': choices})

def tmdb_api_check_choice(params):
	from apis.tmdb_api import movie_details
	data = movie_details('299534', tmdb_api_key())
	if not data.get('success', True): text = 'There is an issue with your API Key.[CR][B]"Error: %s"[/B]' % data.get('status_message', '')
	else: text = 'Your TMDb API Key is enabled and working'
	return ok_dialog(text=text)

def clear_sources_folder_choice(params):
	setting_id = params['setting_id']
	set_default(['%s.display_name' % setting_id, '%s.movies_directory' % setting_id, '%s.tv_shows_directory' % setting_id])

def widget_refresh_timer_choice(params):
	choices = [{'name': 'OFF', 'value': '0'}]
	choices.extend([{'name': 'Every %s Minutes' % i, 'value': str(i)} for i in range(5,25,5)])
	choices.extend([{'name': 'Every %s Minutes' % i, 'value': str(i)} for i in range(30,65,10)])
	choices.extend([{'name': 'Every %s Hours' % (float(i)/60), 'value': str(i)} for i in range(90,720,30)])
	list_items = [{'line1': i['name']} for i in choices]
	kwargs = {'items': json.dumps(list_items), 'narrow_window': 'true'}
	choice = select_dialog(choices, **kwargs)
	if choice == None: return
	set_setting('widget_refresh_timer', choice['value'])
	set_setting('widget_refresh_timer_name', choice['name'])

def external_scraper_choice(params):
	try: results = jsonrpc_get_addons('xbmc.python.module')
	except: return
	list_items = [{'line1': i['name'], 'icon': i['thumbnail']} for i in results]
	kwargs = {'items': json.dumps(list_items)}
	choice = select_dialog(results, **kwargs)
	if choice == None: return
	module_id, module_name = choice['addonid'], choice['name']
	try:
		append_module_to_syspath('special://home/addons/%s/lib' % module_id)
		main_folder_name = module_id.split('.')[-1]
		manual_module_import('%s.sources_%s' % (main_folder_name, main_folder_name))
		success = True
	except: success = False
	if success:
		try:
			set_setting('external_scraper.module', module_id)
			set_setting('external_scraper.name', module_name)
			set_setting('provider.external', 'true')
			ok_dialog(text='Success.[CR][B]%s[/B] set as External Scraper' % module_name)
		except: ok_dialog(text='Error')
	else:
		ok_dialog(text='The [B]%s[/B] Module is not compatible.[CR]Please choose a different Module...' % module_name.upper())
		return external_scraper_choice(params)

def audio_filters_choice(params={}):
	icon = get_icon('audio')
	list_items = [{'line1': item[0], 'line2': item[1], 'icon': icon} for item in audio_filter_choices]
	try: preselect = [audio_filter_choices.index(item) for item in audio_filter_choices if item[1] in audio_filters()]
	except: preselect = []
	kwargs = {'items': json.dumps(list_items), 'heading': 'Choose Audio Properties to Exclude', 'multi_choice': 'true', 'multi_line': 'true', 'preselect': preselect}
	selection = select_dialog([i[1] for i in audio_filter_choices], **kwargs)
	if selection == None: return
	if selection == []: set_setting('filter_audio', 'empty_setting')
	else: set_setting('filter_audio', ', '.join(selection))

def genres_choice(params):
	genres_list, genres, poster = params['genres_list'], params['genres'], params['poster']
	genre_list = [i for i in genres_list if i['name'] in genres]
	if not genre_list:
		notification('No Results', 2500)
		return None
	list_items = [{'line1': i['name'], 'icon': poster} for i in genre_list]
	kwargs = {'items': json.dumps(list_items)}
	return select_dialog([i['id'] for i in genre_list], **kwargs)

def keywords_choice(params):
	media_type, meta = params['media_type'], params['meta']
	keywords, tmdb_id, poster = meta.get('keywords', []), meta['tmdb_id'], meta['poster']
	if keywords: keywords = keywords['keywords']
	else:
		show_busy_dialog()
		from apis.tmdb_api import tmdb_movie_keywords, tmdb_tv_keywords
		if media_type == 'movie': function, key = tmdb_movie_keywords, 'keywords'
		else: function, key = tmdb_tv_keywords, 'results'
		try: keywords = function(tmdb_id)[key]
		except: keywords = []
		hide_busy_dialog()
	if not keywords:
		notification('No Results', 2500)
		return None
	list_items = [{'line1': i['name'], 'icon': poster} for i in keywords]
	kwargs = {'items': json.dumps(list_items)}
	return select_dialog([i['id'] for i in keywords], **kwargs)

def random_choice(params):
	meta, poster, return_choice = params.get('meta'), params.get('poster'), params.get('return_choice', 'false')
	meta = params.get('meta', None)	
	list_items = [{'line1': 'Single Random Play', 'icon': poster}, {'line1': 'Continual Random Play', 'icon': poster}]
	choices = ['play_random', 'play_random_continual']
	kwargs = {'items': json.dumps(list_items), 'heading': 'Choose Random Play Type...'}
	choice = select_dialog(choices, **kwargs)
	if return_choice == 'true': return choice
	if choice == None: return
	from modules.episode_tools import EpisodeTools
	exec('EpisodeTools(meta).%s()' % choice)

def trakt_manager_choice(params):
	if not trakt_user_active(): return notification('No Active Trakt Account', 3500)
	icon = params.get('icon', None) or get_icon('trakt')
	choices = [('Add To Trakt List...', 'Add'), ('Remove From Trakt List...', 'Remove')]
	list_items = [{'line1': item[0], 'icon': icon} for item in choices]
	kwargs = {'items': json.dumps(list_items), 'heading': 'Trakt Lists Manager'}
	choice = select_dialog([i[1] for i in choices], **kwargs)
	if choice == None: return
	from apis import trakt_api
	if choice == 'Add': trakt_api.trakt_add_to_list(params)
	else: trakt_api.trakt_remove_from_list(params)

def episode_groups_choice(params):
	episode_group_types = {1: 'Original Air Date', 2: 'Absolute', 3: 'DVD', 4: 'Digital', 5: 'Story Arc', 6: 'Production', 7: 'TV'}
	meta = params.get('meta')
	poster = params.get('poster') or empty_poster
	groups = metadata.episode_groups(meta['tmdb_id'])
	if not groups:
		notification('No Episode Groups to choose from.')
		return None
	list_items = [{'line1': '%s | %s Order | %d Groups | %02d Episodes' % (item['name'], episode_group_types[item['type']], item['group_count'], item['episode_count']),
					'line2': item['description'], 'icon': poster} for item in groups]
	kwargs = {'items': json.dumps(list_items), 'heading': 'Episode Groups', 'enable_context_menu': 'true', 'enumerate': 'true', 'multi_line': 'true'}
	choice = select_dialog([i['id'] for i in groups], **kwargs)
	return choice

def assign_episode_group_choice(params):
	tmdb_id = params['meta']['tmdb_id']
	current_group = episode_groups_cache.get(tmdb_id)
	if current_group:
		action = confirm_dialog(text='Set new Group or Clear Current Group?', ok_label='Set New', cancel_label='Clear', default_control=10)
		if action == None: return
		if not action:
			episode_groups_cache.delete(tmdb_id)
			return notification('Success', 2000)
	choice = episode_groups_choice(params)
	if choice == None: return
	group_details = metadata.group_details(choice)
	group_data = {'name': group_details['name'], 'id': group_details['id']}
	episode_groups_cache.set(tmdb_id, group_data)
	notification('Success', 2000)

def playback_choice(params):
	media_type, season, episode = params.get('media_type'), params.get('season', ''), params.get('episode', '')
	episode_id = params.get('episode_id', None)
	meta = params.get('meta')
	try: meta = json.loads(meta)
	except: pass
	if not isinstance(meta, dict):
		function = metadata.movie_meta if media_type == 'movie' else metadata.tvshow_meta
		meta = function('tmdb_id', meta, tmdb_api_key(), mpaa_region(), get_datetime())
	poster = meta.get('poster') or empty_poster
	aliases = get_aliases_titles(make_alias_dict(meta, meta['title']))
	items = [{'line': 'Select Source', 'function': 'scrape'},
			{'line': 'Rescrape & Select Source', 'function': 'clear_and_rescrape'},
			{'line': 'Scrape with DEFAULT External Scrapers', 'function': 'scrape_with_default'},
			{'line': 'Scrape with ALL External Scrapers', 'function': 'scrape_with_disabled'},
			{'line': 'Scrape With All Filters Ignored', 'function': 'scrape_with_filters_ignored'}]
	if media_type == 'episode': items.append({'line': 'Scrape with Custom Episode Groups Value', 'function': 'scrape_with_episode_group'})
	if aliases: items.append({'line': 'Scrape with an Alias', 'function': 'scrape_with_aliases'})
	items.append({'line': 'Scrape with Custom Values', 'function': 'scrape_with_custom_values'})
	list_items = [{'line1': i['line'], 'icon': poster} for i in items]
	kwargs = {'items': json.dumps(list_items), 'heading': 'Playback Options'}
	choice = select_dialog([i['function'] for i in items], **kwargs)
	if choice == None: return notification('Cancelled', 2500)
	if choice in ('clear_and_rescrape', 'scrape_with_custom_values'):
		show_busy_dialog()
		from caches.base_cache import clear_cache
		from caches.external_cache import ExternalCache
		clear_cache('internal_scrapers', silent=True)
		ExternalCache().delete_cache_single(media_type, str(meta['tmdb_id']))
		hide_busy_dialog()
	if choice == 'scrape':
		if media_type == 'movie': play_params = {'mode': 'playback.media', 'media_type': 'movie', 'tmdb_id': meta['tmdb_id'], 'autoplay': 'false'}
		else: play_params = {'mode': 'playback.media', 'media_type': 'episode', 'tmdb_id': meta['tmdb_id'], 'season': season, 'episode': episode, 'autoplay': 'false'}
	elif choice == 'clear_and_rescrape':
		if media_type == 'movie': play_params = {'mode': 'playback.media', 'media_type': 'movie', 'tmdb_id': meta['tmdb_id'], 'autoplay': 'false'}
		else: play_params = {'mode': 'playback.media', 'media_type': 'episode', 'tmdb_id': meta['tmdb_id'], 'season': season, 'episode': episode, 'autoplay': 'false'}
	elif choice == 'scrape_with_default':
		if media_type == 'movie': play_params = {'mode': 'playback.media', 'media_type': 'movie', 'tmdb_id': meta['tmdb_id'],
												'default_ext_only': 'true', 'prescrape': 'false', 'autoplay': 'false'}
		else: play_params = {'mode': 'playback.media', 'media_type': 'episode', 'tmdb_id': meta['tmdb_id'], 'season': season,
							'episode': episode, 'default_ext_only': 'true', 'prescrape': 'false', 'autoplay': 'false'}
	elif choice == 'scrape_with_disabled':
		if media_type == 'movie': play_params = {'mode': 'playback.media', 'media_type': 'movie', 'tmdb_id': meta['tmdb_id'],
												'disabled_ext_ignored': 'true', 'prescrape': 'false', 'autoplay': 'false'}
		else: play_params = {'mode': 'playback.media', 'media_type': 'episode', 'tmdb_id': meta['tmdb_id'], 'season': season,
							'episode': episode, 'disabled_ext_ignored': 'true', 'prescrape': 'false', 'autoplay': 'false'}
	elif choice == 'scrape_with_filters_ignored':
		if media_type == 'movie': play_params = {'mode': 'playback.media', 'media_type': 'movie', 'tmdb_id': meta['tmdb_id'],
												'ignore_scrape_filters': 'true', 'prescrape': 'false', 'autoplay': 'false'}
		else: play_params = {'mode': 'playback.media', 'media_type': 'episode', 'tmdb_id': meta['tmdb_id'], 'season': season,
							'episode': episode, 'ignore_scrape_filters': 'true', 'prescrape': 'false', 'autoplay': 'false'}
		set_property('fs_filterless_search', 'true')
	elif choice == 'scrape_with_episode_group':
		choice = episode_groups_choice({'meta': meta, 'poster': poster})
		if choice == None: return playback_choice(params)
		episode_details = metadata.group_episode_data(metadata.group_details(choice), episode_id, season, episode)
		if not episode_details:
			notification('No matching episode')
			return playback_choice(params)
		play_params = {'mode': 'playback.media', 'media_type': 'episode', 'tmdb_id': meta['tmdb_id'], 'season': season, 'episode': episode, 'prescrape': 'false',
		'custom_season': episode_details['season'], 'custom_episode': episode_details['episode']}
	elif choice == 'scrape_with_aliases':
		if len(aliases) == 1: custom_title = aliases[0]
		else:
			list_items = [{'line1': i, 'icon': poster} for i in aliases]
			kwargs = {'items': json.dumps(list_items)}
			custom_title = select_dialog(aliases, **kwargs)
			if custom_title == None: return notification('Cancelled', 2500)
		custom_title = kodi_dialog().input('Title', defaultt=custom_title)
		if not custom_title: return notification('Cancelled', 2500)
		if media_type in ('movie', 'movies'): play_params = {'mode': 'playback.media', 'media_type': 'movie', 'tmdb_id': meta['tmdb_id'],
						'custom_title': custom_title, 'prescrape': 'false'}
		else: play_params = {'mode': 'playback.media', 'media_type': 'episode', 'tmdb_id': meta['tmdb_id'], 'season': season, 'episode': episode,
							'custom_title': custom_title, 'prescrape': 'false'}
	elif choice == 'scrape_with_custom_values':
		default_title, default_year = meta['title'], str(meta['year'])
		if media_type in ('movie', 'movies'): play_params = {'mode': 'playback.media', 'media_type': 'movie', 'tmdb_id': meta['tmdb_id'], 'prescrape': 'false'}
		else: play_params = {'mode': 'playback.media', 'media_type': 'episode', 'tmdb_id': meta['tmdb_id'], 'season': season, 'episode': episode, 'prescrape': 'false'}
		if aliases:
			if len(aliases) == 1: alias_title = aliases[0]
			list_items = [{'line1': i, 'icon': poster} for i in aliases]
			kwargs = {'items': json.dumps(list_items)}
			alias_title = select_dialog(aliases, **kwargs)
			if alias_title: custom_title = kodi_dialog().input('Title', defaultt=alias_title)
			else: custom_title = kodi_dialog().input('Title', defaultt=default_title)
		else: custom_title = kodi_dialog().input('Title', defaultt=default_title)
		if not custom_title: return notification('Cancelled', 2500)
		def _process_params(default_value, custom_value, param_value):
			if custom_value and custom_value != default_value: play_params[param_value] = custom_value
		_process_params(default_title, custom_title, 'custom_title')
		custom_year = kodi_dialog().input('Year', type=numeric_input, defaultt=default_year)
		_process_params(default_year, custom_year, 'custom_year')
		if media_type == 'episode':
			custom_season = kodi_dialog().input('Season', type=numeric_input, defaultt=season)
			_process_params(season, custom_season, 'custom_season')
			custom_episode = kodi_dialog().input('Episode', type=numeric_input, defaultt=episode)
			_process_params(episode, custom_episode, 'custom_episode')
			if any(i in play_params for i in ('custom_season', 'custom_episode')):
				if autoplay_next_episode(): _process_params('', 'true', 'disable_autoplay_next_episode')
		all_choice = confirm_dialog(heading=meta.get('rootname', ''), text='Scrape with ALL External Scrapers?', ok_label='Yes', cancel_label='No')
		if all_choice == None: return notification('Cancelled', 2500)
		if not all_choice:
			default_choice = confirm_dialog(heading=meta.get('rootname', ''), text='Scrape with DEFAULT External Scrapers?', ok_label='Yes', cancel_label='No')
			if default_choice == None: return notification('Cancelled', 2500)
			if default_choice: _process_params('', 'true', 'default_ext_only')
		else:  _process_params('', 'true', 'disabled_ext_ignored')
		disable_filters_choice = confirm_dialog(heading=meta.get('rootname', ''), text='Disable All Filters for Search?', ok_label='Yes', cancel_label='No')
		if disable_filters_choice == None: return notification('Cancelled', 2500)
		if disable_filters_choice:
			_process_params('', 'true', 'ignore_scrape_filters')
			set_property('fs_filterless_search', 'true')
	else:
		from modules.metadata import episodes_meta
		episodes_data = episodes_meta(orig_season, meta)
	from modules.sources import Sources
	Sources().playback_prep(play_params)

def set_quality_choice(params):
	quality_setting = params.get('setting_id')
	icon = params.get('icon', None) or ''
	dl = ['Include SD', 'Include 720p', 'Include 1080p', 'Include 4K']
	fl = ['SD', '720p', '1080p', '4K']
	try: preselect = [fl.index(i) for i in get_setting('fenlight.%s' % quality_setting).split(', ')]
	except: preselect = []
	list_items = [{'line1': item, 'icon': icon} for item in dl]
	kwargs = {'items': json.dumps(list_items), 'multi_choice': 'true', 'preselect': preselect}
	choice = select_dialog(fl, **kwargs)
	if choice is None: return
	if choice == []:
		ok_dialog(text='Error')
		return set_quality_choice(params)
	set_setting(quality_setting, ', '.join(choice))

def extras_buttons_choice(params):
	media_type, button_dict, orig_button_dict = params.get('media_type', None), params.get('button_dict', {}), params.get('orig_button_dict', {})
	if not orig_button_dict:
		for _type in ('movie', 'tvshow'):
			setting_id_base = 'extras.%s.button' % _type
			for item in range(10, 18):
				setting_id = setting_id_base + str(item)
				try:
					button_action = get_setting('fenlight.%s' % setting_id)
					button_label = extras_button_label_values[_type][button_action]
				except:
					set_setting(setting_id.replace('fenlight.', ''), default_setting_values(setting_id.replace('fenlight.', ''))['setting_default'])
					button_action = get_setting('fenlight.%s' % setting_id)
					button_label = extras_button_label_values[_type][button_action]
				button_dict[setting_id] = {'button_action': button_action, 'button_label': button_label, 'button_name': 'Button %s' % str(item - 9)}
				orig_button_dict[setting_id] = {'button_action': button_action, 'button_label': button_label, 'button_name': 'Button %s' % str(item - 9)}
	if media_type == None:
		choices = [('Set [B]Movie[/B] Buttons', 'movie'),
					('Set [B]TV Show[/B] Buttons', 'tvshow'),
					('Restore [B]Movie[/B] Buttons to Default', 'restore.movie'),
					('Restore [B]TV Show[/B] Buttons to Default', 'restore.tvshow'),
					('Restore [B]Movie & TV Show[/B] Buttons to Default', 'restore.both')]
		list_items = [{'line1': i[0]} for i in choices]
		kwargs = {'items': json.dumps(list_items), 'heading': 'Choose Media Type to Set Buttons', 'narrow_window': 'true'}
		choice = select_dialog(choices, **kwargs)
		if choice == None:
			if button_dict != orig_button_dict:
				for k, v in button_dict.items():
					set_setting(k, v['button_action'])
				return ok_dialog(text='Success')
			return
		media_type = choice[1]
		if 'restore' in media_type:
			restore_type = media_type.split('.')[1]
			if restore_type in ('movie', 'both'):
				for item in [(i, default_setting_values(i)['setting_default']) for i in ('extras.movie.button%s' % i for i in range(10,18))]:
					set_setting(item[0], item[1])
			if restore_type in ('tvshow', 'both'):
				for item in [(i, default_setting_values(i)['setting_default']) for i in ('extras.tvshow.button%s' % i for i in range(10,18))]:
					set_setting(item[0], item[1])
			return ok_dialog(text='Success')
	choices = [('[B]%s[/B]   |   %s' % (v['button_name'], v['button_label']), v['button_name'], v['button_label'], k) for k, v in button_dict.items() if media_type in k]
	list_items = [{'line1': i[0]} for i in choices]
	kwargs = {'items': json.dumps(list_items), 'heading': 'Choose Button to Set', 'narrow_window': 'true'}
	choice = select_dialog(choices, **kwargs)
	if choice == None: return extras_buttons_choice({'button_dict': button_dict, 'orig_button_dict': orig_button_dict})
	button_name, button_label, button_setting = choice[1:]
	choices = [(v, k) for k, v in extras_button_label_values[media_type].items() if not v == button_label]
	choices = [i for i in choices if not i[0] == button_label]
	list_items = [{'line1': i[0]} for i in choices]
	kwargs = {'items': json.dumps(list_items), 'heading': 'Choose Action For %s' % button_name, 'narrow_window': 'true'}
	choice = select_dialog(choices, **kwargs)
	if choice == None: return extras_buttons_choice({'button_dict': button_dict, 'orig_button_dict': orig_button_dict, 'media_type': media_type})
	button_label, button_action = choice
	button_dict[button_setting] = {'button_action': button_action, 'button_label': button_label, 'button_name': button_name}
	return extras_buttons_choice({'button_dict': button_dict, 'orig_button_dict': orig_button_dict, 'media_type': media_type})

def extras_lists_choice(params={}):
	choices = [('Plot', 2000), ('Cast', 2050), ('Recommended', 2051), ('More Like This', 2052), ('Reviews', 2053), ('Comments', 2054), ('Trivia', 2055),
			('Blunders', 2056), ('Parental Guide', 2057), ('In Trakt Lists', 2058), ('Videos', 2059), ('More from Year', 2060), ('More from Genres', 2061),
			('More from Networks', 2062), ('More from Collection', 2063)]
	list_items = [{'line1': i[0]} for i in choices]
	current_settings = extras_enabled_menus()
	try: preselect = [choices.index(i) for i in choices if i[1] in current_settings]
	except: preselect = []
	kwargs = {'items': json.dumps(list_items), 'heading': 'Enable Content for Extras Lists', 'multi_choice': 'true', 'preselect': preselect}
	selection = select_dialog(choices, **kwargs)
	if selection  == []: return set_setting('extras.enabled', 'noop')
	elif selection == None: return
	selection = [str(i[1]) for i in selection]
	set_setting('extras.enabled', ','.join(selection))

def set_language_filter_choice(params):
	from modules.meta_lists import language_choices
	filter_setting_id, multi_choice, include_none = params.get('filter_setting_id'), params.get('multi_choice', 'false'), params.get('include_none', 'false')
	lang_choices = language_choices
	if include_none == 'false': lang_choices.pop('None')
	dl, fl = list(lang_choices.keys()), list(lang_choices.values())
	try: preselect = [fl.index(i) for i in get_setting('fenlight.%s' % filter_setting_id).split(', ')]
	except: preselect = []
	list_items = [{'line1': item} for item in dl]
	kwargs = {'items': json.dumps(list_items), 'multi_choice': multi_choice, 'preselect': preselect}
	choice = select_dialog(fl, **kwargs)
	if choice == None: return
	if multi_choice == 'true':
		if choice == []: set_setting(filter_setting_id, 'eng')
		else: set_setting(filter_setting_id, ', '.join(choice))
	else: set_setting(filter_setting_id, choice)

def enable_scrapers_choice(params={}):
	icon = params.get('icon', None) or get_icon('fenlight')
	scrapers = ['external', 'easynews', 'rd_cloud', 'pm_cloud', 'ad_cloud', 'oc_cloud', 'tb_cloud', 'folders']
	cloud_scrapers = {'rd_cloud': 'rd.enabled', 'pm_cloud': 'pm.enabled', 'ad_cloud': 'ad.enabled', 'oc_cloud': 'oc.enabled', 'tb_cloud': 'tb.enabled'}
	preselect = [scrapers.index(i) for i in active_internal_scrapers()]
	list_items = [{'line1': item, 'icon': icon} for item in scraper_names]
	kwargs = {'items': json.dumps(list_items), 'multi_choice': 'true', 'preselect': preselect}
	choice = select_dialog(scrapers, **kwargs)
	if choice is None: return
	for i in scrapers:
		set_setting('provider.%s' % i, ('true' if i in choice else 'false'))
		if i in cloud_scrapers and i in choice: set_setting(cloud_scrapers[i], 'true')

def sources_folders_choice(params):
	return open_window(('windows.settings_manager', 'SettingsManagerFolders'), 'settings_manager_folders.xml')

def results_sorting_choice(params={}):
	choices = [('Quality, Provider, Size', '0'), ('Quality, Size, Provider', '1'),
				('Provider, Quality, Size', '2'), ('Provider, Size, Quality', '3'),
				('Size, Quality, Provider', '4'), ('Size, Provider, Quality', '5')]
	list_items = [{'line1': item[0]} for item in choices]
	kwargs = {'items': json.dumps(list_items), 'narrow_window': 'true'}
	choice = select_dialog(choices, **kwargs)
	if choice:
		set_setting('results.sort_order_display', choice[0])
		set_setting('results.sort_order', choice[1])

def results_format_choice(params={}):
	choice = open_window(('windows.sources', 'SourcesChoice'), 'sources_choice.xml')
	if choice: set_setting('results.list_format', choice)

def clear_favorites_choice(params={}):
	fl = [('Clear Movies Favorites', 'movie'), ('Clear TV Show Favorites', 'tvshow'), ('Clear Anime Favorites', 'anime'), ('Clear People Favorites', 'people')]
	list_items = [{'line1': item[0]} for item in fl]
	kwargs = {'items': json.dumps(list_items), 'narrow_window': 'true'}
	media_type = select_dialog([item[1] for item in fl], **kwargs)
	if media_type == None: return
	if not confirm_dialog(): return
	from caches.favorites_cache import favorites_cache
	favorites_cache.clear_favorites(media_type)
	notification('Success', 3000)

def favorites_choice(params):
	from caches.favorites_cache import favorites_cache
	media_type, tmdb_id, title = params.get('media_type'), params.get('tmdb_id'), params.get('title')
	if media_type == 'tvshow':
		if params.get('is_anime', None) in (True, 'True', 'true'): media_type = 'anime'
		elif metadata.is_anime_check(tmdb_id): media_type = 'anime'
	current_favorites = favorites_cache.get_favorites(media_type)
	people_favorite = media_type == 'people'
	current_favorite = any(i['tmdb_id'] == tmdb_id for i in current_favorites)
	if current_favorite:
		function, text = favorites_cache.delete_favourite, 'Remove From Favorites?'
		param_refresh = params.get('refresh', None)
		if param_refresh == None: refresh = any(i in folder_path() for i in ('action=favorites_movies', 'action=favorites_tvshows', 'action=favorites_anime_tvshows'))
		else: refresh = param_refresh == 'true'
	else: function, text, refresh = favorites_cache.set_favourite, 'Add To Favorites?', False
	heading = title.split('|')[0] if people_favorite else title
	if not confirm_dialog(heading=heading, text=text): return
	success = function(media_type, tmdb_id, title)
	if success:
		if refresh: kodi_refresh()
		notification('Success', 3500)
	else: notification('Error', 3500)
	if people_favorite and success: return text

def scraper_color_choice(params):
	setting = params.get('setting_id')
	current_setting, original_highlight = get_setting('fenlight.%s' % setting), default_setting_values(setting)['setting_default']
	if current_setting != original_highlight:
		action = confirm_dialog(text='Set new Highlight or Restore Default Highlight?', ok_label='Set New', cancel_label='Restore Default', default_control=10)
		if action == None: return
		if not action: return set_setting(setting, original_highlight)
	chosen_color = color_choice({'current_setting': current_setting})
	if chosen_color: set_setting(setting, chosen_color)

def color_choice(params):
	return open_window(('windows.color', 'SelectColor'), 'color.xml', current_setting=params.get('current_setting', None))

def mpaa_region_choice(params={}):
	from modules.meta_lists import regions
	regions.sort(key=lambda x: x['name'])
	list_items = [{'line1': i['name']} for i in regions]
	kwargs = {'items': json.dumps(list_items), 'heading': 'Set MPAA Region', 'narrow_window': 'true'}
	choice = select_dialog(regions, **kwargs)
	if choice == None: return None
	from caches.meta_cache import delete_meta_cache
	set_setting('mpaa_region', choice['id'])
	set_setting('mpaa_region_display_name', choice['name'])
	delete_meta_cache(silent=True)

def options_menu_choice(params, meta=None):
	params_get = params.get
	tmdb_id, content, poster = params_get('tmdb_id', None), params_get('content', None), params_get('poster', None)
	is_external, from_extras = params_get('is_external') in (True, 'True', 'true'), params_get('from_extras', 'false') == 'true'
	is_anime = params_get('is_anime') in (True, 'True', 'true')
	season, episode = params_get('season', ''), params_get('episode', '')
	if not content: content = container_content()[:-1]
	menu_type = content
	if content.startswith('episode.'): content = 'episode'
	if not meta:
		function = metadata.movie_meta if content == 'movie' else metadata.tvshow_meta
		meta = function('tmdb_id', tmdb_id, tmdb_api_key(), mpaa_region(), get_datetime())
	meta_get = meta.get
	rootname, title, imdb_id, tvdb_id = meta_get('rootname', None), meta_get('title'), meta_get('imdb_id', None), meta_get('tvdb_id', None)
	window_function = activate_window if is_external else container_update
	listing = []
	listing_append = listing.append
	if from_extras:
		if menu_type in ('movie', 'episode'): listing_append(('Playback Options', 'Scrapers Options', 'playback_choice'))
		if trakt_user_active(): listing_append(('Trakt Lists Manager', '', 'trakt_manager'))
		listing_append(('Favorites Manager', '', 'favorites_choice'))
	if menu_type == 'tvshow': listing_append(('Play Random', 'Based On %s' % rootname, 'random'))
	if menu_type in ('tvshow', 'season'):
		listing_append(('Assign an Episode Group to %s' % rootname, 'Currently %s' % episode_groups_cache.get(tmdb_id).get('name', 'None'), 'episode_group'))
	if menu_type in ('movie', 'episode') or menu_type in single_ep_list:
		base_str1, base_str2, on_str, off_str = '%s%s', 'Currently: [B]%s[/B]', 'On', 'Off'
		if auto_play(content): autoplay_status, autoplay_toggle, quality_setting = on_str, 'false', 'autoplay_quality_%s' % content
		else: autoplay_status, autoplay_toggle, quality_setting = off_str, 'true', 'results_quality_%s' % content
		active_int_scrapers = [i.replace('_', '') for i in active_internal_scrapers()]
		current_scrapers_status = ', '.join([i for i in active_int_scrapers]) if len(active_int_scrapers) > 0 else 'N/A'
		current_quality_status =  ', '.join(quality_filter(quality_setting))
		listing_append((base_str1 % ('Auto Play', ' (%s)' % content), base_str2 % autoplay_status, 'toggle_autoplay'))
		if menu_type == 'episode' or menu_type in single_ep_list:
			if autoplay_status == on_str:
				autoplay_next_status, autoplay_next_toggle = (on_str, 'false') if autoplay_next_episode() else (off_str, 'true')
				listing_append((base_str1 % ('Autoplay Next Episode', ''), base_str2 % autoplay_next_status, 'toggle_autoplay_next'))
			else:
				autoscrape_next_status, autoscrape_next_toggle = (on_str, 'false') if autoscrape_next_episode() else (off_str, 'true')
				listing_append((base_str1 % ('Autoscrape Next Episode', ''), base_str2 % autoscrape_next_status, 'toggle_autoscrape_next'))
		listing_append((base_str1 % ('Quality Limit', ' (%s)' % content), base_str2 % current_quality_status, 'set_quality'))
		listing_append((base_str1 % ('', 'Enable Scrapers'), base_str2 % current_scrapers_status, 'enable_scrapers'))
		if menu_type == 'episode' or menu_type in single_ep_list:
			listing_append(('Assign an Episode Group to %s' % rootname, 'Currently %s' % episode_groups_cache.get(tmdb_id).get('name', 'None'), 'episode_group'))
	if not from_extras:
		if menu_type in ('movie', 'tvshow'):
			listing_append(('Re-Cache %s Info' % ('Movies' if menu_type == 'movie' else 'TV Shows'), 'Clear %s Cache' % rootname, 'clear_media_cache'))
		if menu_type in ('movie', 'episode') or menu_type in single_ep_list: listing_append(('Clear Scrapers Cache', '', 'clear_scrapers_cache'))
		if menu_type in ('tvshow', 'season', 'episode'): listing_append(('TV Shows Progress Manager', '', 'nextep_manager'))
		listing_append(('Open Download Manager', '', 'open_download_manager'))
		listing_append(('Open Tools', '', 'open_tools'))
		if menu_type in ('movie', 'episode') or menu_type in single_ep_list: listing_append(('Open External Scraper Settings', '', 'open_external_scraper_settings'))
		listing_append(('Open Settings', '', 'open_settings'))
	list_items = [{'line1': item[0], 'line2': item[1] or item[0], 'icon': poster} for item in listing]
	heading = rootname or 'Options...'
	kwargs = {'items': json.dumps(list_items), 'heading': heading, 'multi_line': 'true'}
	choice = select_dialog([i[2] for i in listing], **kwargs)
	if choice == None: return
	if choice == 'clear_media_cache':
		close_all_dialog()
		return refresh_cached_data(meta)
	if choice == 'clear_scrapers_cache':
		return clear_scrapers_cache()
	if choice == 'open_download_manager':
		close_all_dialog()
		return manager()
	if choice == 'open_tools':
		close_all_dialog()
		return window_function({'mode': 'navigator.tools'})
	if choice == 'open_settings':
		close_all_dialog()
		return open_settings()
	if choice == 'open_external_scraper_settings':
		close_all_dialog()
		return external_scraper_settings()
	if choice == 'playback_choice':
		return playback_choice({'media_type': content, 'poster': poster, 'meta': meta, 'season': season, 'episode': episode})
	if choice == 'nextep_manager':
		return window_function({'mode': 'build_next_episode_manager'})
	if choice == 'random':
		close_all_dialog()
		return random_choice({'meta': meta, 'poster': poster})
	if choice == 'trakt_manager':
		return trakt_manager_choice({'tmdb_id': tmdb_id, 'imdb_id': imdb_id, 'tvdb_id': tvdb_id or 'None', 'media_type': content, 'icon': poster})
	if choice == 'favorites_choice':
		return favorites_choice({'media_type': content if content in ('movie', 'tvshow') else 'tvshow', 'tmdb_id': tmdb_id, 'title': title, 'is_anime': is_anime})
	if choice == 'toggle_autoplay':
		set_setting('auto_play_%s' % content, autoplay_toggle)
	elif choice == 'toggle_autoplay_next':
		set_setting('autoplay_next_episode', autoplay_next_toggle)
	elif choice == 'toggle_autoscrape_next':
		set_setting('autoscrape_next_episode', autoscrape_next_toggle)
	elif choice == 'set_quality':
		set_quality_choice({'setting_id': 'autoplay_quality_%s' % content if autoplay_status == on_str else 'results_quality_%s' % content, 'icon': poster})
	elif choice == 'enable_scrapers':
		enable_scrapers_choice({'icon': poster})
	elif choice == 'episode_group':
		assign_episode_group_choice({'meta': meta, 'poster': poster})
	options_menu_choice(params, meta=meta)

def extras_menu_choice(params):
	stacked = params.get('stacked', 'false') == 'true'
	if not stacked: show_busy_dialog()
	media_type = params['media_type']
	function = metadata.movie_meta if media_type == 'movie' else metadata.tvshow_meta
	meta = function('tmdb_id', params['tmdb_id'], tmdb_api_key(), mpaa_region(), get_datetime())
	if not stacked: hide_busy_dialog()
	open_window(('windows.extras', 'Extras'), 'extras.xml', meta=meta, is_external=params.get('is_external', 'true' if external() else 'false'), is_anime=params.get('is_anime', None),
															options_media_type=media_type, starting_position=params.get('starting_position', None))

def open_movieset_choice(params):
	hide_busy_dialog()
	window_function = activate_window if params['is_external'] in (True, 'True', 'true') else container_update
	return window_function({'mode': 'build_movie_list', 'action': 'tmdb_movies_sets', 'key_id': params['key_id'], 'name': params['name']})

def media_extra_info_choice(params):
	media_type, meta = params.get('media_type'), params.get('meta')
	extra_info, listings = meta.get('extra_info', None), []
	append = listings.append
	try:
		if media_type == 'movie':
			if meta['tagline']: append('[B]Tagline:[/B] %s' % meta['tagline'])
			aliases = get_aliases_titles(make_alias_dict(meta, meta['title']))
			if aliases: append('[B]Aliases:[/B] %s' % ', '.join(aliases))
			append('[B]Status:[/B] %s' % extra_info['status'])
			append('[B]Premiered:[/B] %s' % meta['premiered'])
			append('[B]Rating:[/B] %s (%s Votes)' % (str(round(meta['rating'], 1)), meta['votes']))
			append('[B]Runtime:[/B] %s mins' % int(float(meta['duration'])/60))
			append('[B]Genre/s:[/B] %s' % ', '.join(meta['genre']))
			append('[B]Budget:[/B] %s' % extra_info['budget'])
			append('[B]Revenue:[/B] %s' % extra_info['revenue'])
			append('[B]Director:[/B] %s' % ', '.join(meta['director']))
			append('[B]Writer/s:[/B] %s' % ', '.join(meta['writer']) or 'N/A')
			append('[B]Studio:[/B] %s' % ', '.join(meta['studio']) or 'N/A')
			if extra_info['collection_name']: append('[B]Collection:[/B] %s' % extra_info['collection_name'])
			append('[B]Homepage:[/B] %s' % extra_info['homepage'])
		else:
			append('[B]Type:[/B] %s' % extra_info['type'])
			if meta['tagline']: append('[B]Tagline:[/B] %s' % meta['tagline'])
			aliases = get_aliases_titles(make_alias_dict(meta, meta['title']))
			if aliases: append('[B]Aliases:[/B] %s' % ', '.join(aliases))
			append('[B]Status:[/B] %s' % extra_info['status'])
			append('[B]Premiered:[/B] %s' % meta['premiered'])
			append('[B]Rating:[/B] %s (%s Votes)' % (str(round(meta['rating'], 1)), meta['votes']))
			append('[B]Runtime:[/B] %d mins' % int(float(meta['duration'])/60))
			append('[B]Classification:[/B] %s' % meta['mpaa'])
			append('[B]Genre/s:[/B] %s' % ', '.join(meta['genre']))
			append('[B]Networks:[/B] %s' % ', '.join(meta['studio']))
			append('[B]Created By:[/B] %s' % extra_info['created_by'])
			try:
				last_ep = extra_info['last_episode_to_air']
				append('[B]Last Aired:[/B] %s - [B]S%.2dE%.2d[/B] - %s' \
					% (adjust_premiered_date(last_ep['air_date'], date_offset())[0].strftime('%d %B %Y'),
						last_ep['season_number'], last_ep['episode_number'], last_ep['name']))
			except: pass
			try:
				next_ep = extra_info['next_episode_to_air']
				append('[B]Next Aired:[/B] %s - [B]S%.2dE%.2d[/B] - %s' \
					% (adjust_premiered_date(next_ep['air_date'], date_offset())[0].strftime('%d %B %Y'),
						next_ep['season_number'], next_ep['episode_number'], next_ep['name']))
			except: pass
			append('[B]Seasons:[/B] %s' % meta['total_seasons'])
			append('[B]Episodes:[/B] %s' % meta['total_aired_eps'])
			append('[B]Homepage:[/B] %s' % extra_info['homepage'])
	except: return notification('Error', 2000)
	return '[CR][CR]'.join(listings)

def discover_choice(params):
	open_window(('windows.discover', 'Discover'), 'discover.xml', media_type=params['media_type'])
