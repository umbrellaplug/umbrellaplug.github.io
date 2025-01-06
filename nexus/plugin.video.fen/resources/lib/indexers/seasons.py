# -*- coding: utf-8 -*-
from modules import kodi_utils, settings
from modules.metadata import tvshow_meta
from modules.utils import adjust_premiered_date, get_datetime
from modules.watched_status import get_watched_info_tv, get_watched_status_season
# logger = kodi_utils.logger

sys, add_items, set_content, end_directory, set_view_mode = kodi_utils.sys, kodi_utils.add_items, kodi_utils.set_content, kodi_utils.end_directory, kodi_utils.set_view_mode
poster_empty, fanart_empty, xbmc_actor, set_category = kodi_utils.empty_poster, kodi_utils.addon_fanart, kodi_utils.xbmc_actor, kodi_utils.set_category
make_listitem, build_url, external, ls = kodi_utils.make_listitem, kodi_utils.build_url, kodi_utils.external, kodi_utils.local_string
adjust_premiered_date_function, get_datetime_function, get_watched_status, get_watched_info = adjust_premiered_date, get_datetime, get_watched_status_season, get_watched_info_tv
get_art_provider, show_specials, use_season_title_info, date_offset_info = settings.get_art_provider, settings.show_specials, settings.use_season_title, settings.date_offset
metadata_user_info, watched_indicators_info, show_unaired_info = settings.metadata_user_info, settings.watched_indicators, settings.show_unaired
fen_str, trakt_str, season_str, watched_str, unwatched_str, season_str = ls(32036), ls(32037), ls(32537), ls(32642), ls(32643), ls(32537)
extras_str, options_str, refr_widg_str = ls(32645), ls(32646), '[B]%s[/B]' % ls(32611)
string, run_plugin, unaired_label, tmdb_poster_prefix = str, 'RunPlugin(%s)', '[COLOR red][I]%s[/I][/COLOR]', 'https://image.tmdb.org/t/p/'
view_mode, content_type = 'view.seasons', 'seasons'
season_name_str = '%s %s'

def build_season_list(params):
	def _process():
		running_ep_count = total_aired_eps
		for item in season_data:
			try:
				listitem = make_listitem()
				set_properties = listitem.setProperties
				cm = []
				cm_append, item_get = cm.append, item.get
				name, overview, poster_path, air_date = item_get('name'), item_get('overview'), item_get('poster_path'), item_get('air_date')
				season_number, episode_count = item_get('season_number'), item_get('episode_count')
				first_airdate, premiered = adjust_premiered_date_function(air_date, adjust_hours)
				tmdb_poster = '%s%s%s' % (tmdb_poster_prefix, image_resolution, poster_path) if poster_path is not None else show_poster
				if fanart_enabled:
					banner, thumb = season_art.get('seasonbanner_%s' % season_number, '') or show_banner, season_art.get('seasonthumb_%s' % season_number, '') or show_fanart
					if fanart_default: poster = season_art.get('seasonposter_%s' % season_number, '') or tmdb_poster
					else: poster = tmdb_poster
				else: poster, banner, thumb = tmdb_poster, show_banner, show_fanart
				if season_number == 0: unaired = False
				elif episode_count == 0: unaired = True
				elif season_number != total_seasons: unaired = False
				else:
					if not first_airdate or current_date < first_airdate: unaired = True
					else: unaired = False
				if unaired:
					if not show_unaired: continue
					episode_count = 0
				elif not season_number == 0:
					running_ep_count -= episode_count
					if running_ep_count < 0: episode_count = running_ep_count + episode_count
				try: year = air_date.split('-')[0]
				except: year = show_year or '2050'
				plot = overview or show_plot
				title = name if use_season_title and name else season_name_str % (season_str, season_number)
				if unaired: title = unaired_label % title
				playcount, overlay, watched, unwatched = get_watched_status(watched_info, str_tmdb_id, season_number, episode_count)
				try: progress = int((float(watched)/episode_count)*100)
				except: progress = 0
				url_params = build_url({'mode': 'build_episode_list', 'tmdb_id': tmdb_id, 'season': season_number})
				extras_params = build_url({'mode': 'extras_menu_choice', 'tmdb_id': tmdb_id, 'media_type': 'tvshow', 'is_external': is_external})
				options_params = build_url({'mode': 'options_menu_choice', 'content': 'season', 'tmdb_id': tmdb_id, 'poster': show_poster, 'playcount': playcount,
											'progress': progress, 'season': season_number, 'is_external': is_external, 'season_poster': poster})
				cm_append((extras_str, run_plugin % extras_params))
				cm_append((options_str, run_plugin % options_params))
				if not playcount:
					cm_append((watched_str % watched_title, run_plugin % build_url({'mode': 'watched_status.mark_season', 'action': 'mark_as_watched', 'title': show_title,
																				'year': show_year, 'tmdb_id': tmdb_id, 'tvdb_id': tvdb_id, 'season': season_number, 'icon': poster})))
				if progress:
					if hide_watched: continue
					cm_append((unwatched_str % watched_title, run_plugin % build_url({'mode': 'watched_status.mark_season', 'action': 'mark_as_unwatched', 'title': show_title,
																				'year': show_year, 'tmdb_id': tmdb_id, 'tvdb_id': tvdb_id, 'season': season_number, 'icon': poster})))
				set_properties({'watchedepisodes': string(watched), 'unwatchedepisodes': string(unwatched)})
				set_properties({'totalepisodes': string(episode_count), 'watchedprogress': string(progress), 'fen.extras_params': extras_params, 'fen.options_params': options_params})
				if is_external:
					cm_append((refr_widg_str, run_plugin % build_url({'mode': 'kodi_refresh'})))
					set_properties({'fen.external': 'true'})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setMediaType('season')
				info_tag.setTitle(title)
				info_tag.setOriginalTitle(orig_title)
				info_tag.setTvShowTitle(show_title)
				info_tag.setTvShowStatus(status)
				info_tag.setSeason(season_number)
				info_tag.setPlot(plot)
				info_tag.setYear(int(year))
				info_tag.setRating(rating)
				info_tag.setVotes(votes)
				info_tag.setMpaa(mpaa)
				info_tag.setCountries(country)
				info_tag.setDuration(episode_run_time)
				info_tag.setTrailer(trailer)
				info_tag.setFirstAired(premiered)
				info_tag.setStudios((studio or '',))
				info_tag.setUniqueIDs({'imdb': imdb_id, 'tmdb': str_tmdb_id, 'tvdb': str_tvdb_id})
				info_tag.setIMDBNumber(imdb_id)
				info_tag.setGenres(genre.split(', '))
				info_tag.setCast([xbmc_actor(name=item['name'], role=item['role'], thumbnail=item['thumbnail']) for item in cast])
				info_tag.setPlaycount(playcount)
				listitem.setLabel(title)
				listitem.setArt({'poster': poster, 'season.poster': poster, 'icon': thumb, 'thumb': thumb, 'fanart': show_fanart, 'banner': banner, 'landscape': show_landscape,
							'clearlogo': show_clearlogo, 'clearart': show_clearart, 'tvshow.poster': poster, 'tvshow.clearlogo': show_clearlogo, 'tvshow.clearart': show_clearart})
				listitem.addContextMenuItems(cm)
				yield (url_params, listitem, True)
			except: pass
	handle, is_external, category_name = int(sys.argv[1]), external(), season_str
	meta_user_info, watched_indicators, show_unaired, adjust_hours = metadata_user_info(), watched_indicators_info(), show_unaired_info(), date_offset_info()
	watched_info, current_date, use_season_title = get_watched_info(watched_indicators), get_datetime_function(), use_season_title_info()
	image_resolution, hide_watched = meta_user_info['image_resolution']['poster'], is_external and meta_user_info['widget_hide_watched']
	fanart_enabled = meta_user_info['extra_fanart_enabled']
	meta = tvshow_meta('tmdb_id', params['tmdb_id'], meta_user_info, current_date)
	meta_get = meta.get
	tmdb_id, tvdb_id, imdb_id, show_title, show_year = meta_get('tmdb_id'), meta_get('tvdb_id'), meta_get('imdb_id'), meta_get('title'), meta_get('year') or '2050'
	orig_title, status, show_plot, total_aired_eps = meta_get('original_title', ''), meta_get('status'), meta_get('plot'), meta_get('total_aired_eps')
	str_tmdb_id, str_tvdb_id, rating, genre = string(tmdb_id), string(tvdb_id), meta_get('rating'), meta_get('genre')
	cast, mpaa, votes, trailer, studio, country = meta_get('cast', []), meta_get('mpaa'), meta_get('votes'), string(meta_get('trailer')), meta_get('studio'), meta_get('country')
	episode_run_time, season_data, total_seasons = meta_get('duration'), meta_get('season_data'), meta_get('total_seasons')
	poster_main, poster_backup, fanart_main, fanart_backup, clearlogo_main, clearlogo_backup = get_art_provider()
	fanart_default = poster_main == 'poster2'
	show_poster = meta_get('custom_poster') or meta_get(poster_main) or meta_get(poster_backup) or poster_empty
	show_fanart = meta_get('custom_fanart') or meta_get(fanart_main) or meta_get(fanart_backup) or fanart_empty
	show_clearlogo = meta_get('custom_clearlogo') or meta_get(clearlogo_main) or meta_get(clearlogo_backup) or ''
	if fanart_enabled:
		show_banner = meta_get('custom_banner') or meta_get('banner') or ''
		show_clearart = meta_get('custom_clearart') or meta_get('clearart') or ''
		show_landscape = meta_get('custom_landscape') or meta_get('landscape') or ''
		season_art = meta_get('season_art', {})
	else: show_banner, show_clearart, show_landscape, season_art = '', '', '', {}

	if not show_specials(): season_data = [i for i in season_data if not i['season_number'] == 0]
	season_data.sort(key=lambda k: (k['season_number'] == 0, k['season_number']))
	watched_title = trakt_str if watched_indicators == 1 else fen_str
	add_items(handle, list(_process()))
	category_name = show_title
	set_content(handle, content_type)
	set_category(handle, category_name)
	end_directory(handle, False if is_external else None)
	set_view_mode(view_mode, content_type, is_external)
