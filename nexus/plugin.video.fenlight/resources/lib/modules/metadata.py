# -*- coding: utf-8 -*-
from apis import tmdb_api
from caches.meta_cache import meta_cache
from modules.utils import jsondate_to_datetime, subtract_dates
# from modules.kodi_utils import logger

movie_details, tvshow_details, season_episodes_details = tmdb_api.movie_details, tmdb_api.tvshow_details, tmdb_api.season_episodes_details
movie_set_details, movie_external_id, tvshow_external_id = tmdb_api.movie_set_details, tmdb_api.movie_external_id, tmdb_api.tvshow_external_id
episode_groups_data, episode_group_details = tmdb_api.episode_groups_data, tmdb_api.episode_group_details
metacache_get, metacache_set, metacache_get_season, metacache_set_season = meta_cache.get, meta_cache.set, meta_cache.get_season, meta_cache.set_season
writer_credits = ('Author', 'Writer', 'Screenplay', 'Characters')
alt_titles_check, finished_show_check, empty_value_check = ('US', 'GB', 'UK', ''), ('Ended', 'Canceled'), ('', 'None', None)
tmdb_image_url, youtube_url, date_format = 'https://image.tmdb.org/t/p/%s%s', 'plugin://plugin.video.youtube/play/?video_id=%s', '%Y-%m-%d'
EXPIRES_1_DAYS, EXPIRES_4_DAYS, EXPIRES_7_DAYS, EXPIRES_14_DAYS, EXPIRES_30_DAYS, EXPIRES_182_DAYS = 24, 96, 168, 336, 720, 4368
invalid_error_codes = (6, 34, 37)

def movie_meta(id_type, media_id, api_key, mpaa_region, current_date, current_time=None):
	if id_type == 'trakt_dict':
		if media_id.get('tmdb', None): id_type, media_id = 'tmdb_id', media_id['tmdb']
		elif media_id.get('imdb', None): id_type, media_id = 'imdb_id', media_id['imdb']
		else: id_type, media_id = None, None
	if media_id == None: return None
	meta = metacache_get('movie', id_type, media_id, current_time)
	if meta: return meta
	try:
		if id_type in ('tmdb_id', 'imdb_id'): data = movie_details(media_id, api_key)
		else:
			external_result = movie_external_id(id_type, media_id, api_key)
			if not external_result: data = None
			else: data = movie_details(external_result['id'], api_key)
		if not data: return None
		elif data.get('status_code') in invalid_error_codes:
			if id_type == 'tmdb_id': meta = {'tmdb_id': media_id, 'imdb_id': 'tt0000000', 'tvdb_id': '0000000', 'blank_entry': True}
			else: meta = {'tmdb_id': '0000000', 'imdb_id': media_id, 'tvdb_id': '0000000', 'blank_entry': True}
			metacache_set('movie', id_type, meta, EXPIRES_1_DAYS, current_time)
			return meta
		data_get = data.get
		cast, writer, director, all_trailers, country, country_codes, studio = [], [], [], [], [], [], []
		mpaa, trailer, spoken_language = '', '', ''
		tmdb_id, imdb_id = data_get('id', ''), data_get('imdb_id', '')
		rating, votes = data_get('vote_average', ''), data_get('vote_count', '')
		plot, tagline, premiered = data_get('overview', ''), data_get('tagline', ''), data_get('release_date', '')
		poster_path = data_get('poster_path', '')
		if poster_path: poster = tmdb_image_url % ('w780', poster_path)
		else: poster = ''
		backdrop_path = data_get('backdrop_path', '')
		if backdrop_path: fanart = tmdb_image_url % ('w1280', backdrop_path)
		else: fanart = ''
		images = data_get('images', {})
		if images:
			try:
				logo_path = images.get('logos')[0].get('file_path')
				if logo_path.endswith('png'): clearlogo = tmdb_image_url % ('original', logo_path)
				else: clearlogo = tmdb_image_url % ('original', logo_path.replace(logo_path.split('.')[-1], 'png'))
			except: clearlogo = ''
			try:
				landscape_path = images.get('backdrops')[0].get('file_path')
				landscape = tmdb_image_url % ('w1280', landscape_path)
			except: landscape = ''
		else: clearlogo, landscape = '', ''
		title, original_title = data_get('title'), data_get('original_title')
		try: english_title = next(i['data']['title'] for i in data_get('translations')['translations'] if i['iso_639_1'] == 'en')
		except: english_title = None
		try: year = str(data_get('release_date').split('-')[0])
		except: year = ''
		try: duration = int(data_get('runtime', '90') * 60)
		except: duration = 0
		try: genre = [i['name'] for i in data_get('genres')]
		except: genre == []
		rootname = '%s (%s)' % (title, year)
		companies = data_get('production_companies')
		if companies:
			if len(companies) == 1: studio = ([i['name'] for i in companies][0],)
			else:
				try: studio = (next(i['name'] for i in companies if i['logo_path'] not in empty_value_check) or next(i['name'] for i in companies),)
				except: pass
		production_countries = data_get('production_countries', None)
		if production_countries:
			country = [i['name'] for i in production_countries]
			country_codes = [i['iso_3166_1'] for i in production_countries]
		release_dates = data_get('release_dates')
		if release_dates:
			try: mpaa = next(x['certification'] for i in release_dates['results'] for x in i['release_dates'] if i['iso_3166_1'] == mpaa_region and x['certification'] != '')
			except: pass
		credits = data_get('credits')
		if credits:
			all_cast = credits.get('cast', None)
			if all_cast:
				try: cast = [{'name': i['name'], 'role': i['character'], 'thumbnail': tmdb_image_url % ('h632', i['profile_path'])if i['profile_path'] else ''}\
							for i in all_cast[:10]]
				except: pass
			crew = credits.get('crew', None)
			if crew:
				try: writer = [i['name'] for i in crew if i['job'] in writer_credits]
				except: pass
				try: director = [i['name'] for i in crew if i['job'] == 'Director']
				except: pass
		alternative_titles = data_get('alternative_titles', [])
		if alternative_titles:
			alternatives = alternative_titles['titles']
			alternative_titles = [i['title'] for i in alternatives if i['iso_3166_1'] in alt_titles_check]
		else: alternative_titles = []
		spoken_languages = data_get('spoken_languages', [])
		if spoken_languages:
			try: spoken_language = spoken_languages[0]['english_name']
			except: spoken_language = ''
		videos = data_get('videos', None)
		if videos:
			try:
				all_trailers = sorted([i for i in videos['results'] if i['site'] == 'YouTube'], key=lambda x: x['name'])
				if all_trailers:
					trailer = next((youtube_url % i['key'] for i in all_trailers if i['official'] and i['type'] == 'Trailer' and 'official trailer' in i['name'].lower()), None) or \
					next((youtube_url % i['key'] for i in all_trailers if i['official'] and i['type'] == 'Trailer'), None) or \
					next((youtube_url % i['key'] for i in all_trailers if i['type'] == 'Trailer'), None) or \
					next((youtube_url % i['key'] for i in all_trailers if 'trailer' in i['name'].lower()), None) or \
					next((youtube_url % i['key'] for i in all_trailers), None) or ''
				else: trailler = ''
			except: pass
		keywords = data_get('keywords', None)
		status, homepage = data_get('status', 'N/A'), data_get('homepage', 'N/A')
		belongs_to_collection = data_get('belongs_to_collection')
		if belongs_to_collection: ei_collection_name, ei_collection_id = belongs_to_collection['name'], belongs_to_collection['id']
		else: ei_collection_name, ei_collection_id = None, None
		try: ei_budget = '${:,}'.format(data_get('budget'))
		except: ei_budget = '$0'
		try: ei_revenue = '${:,}'.format(data_get('revenue'))
		except: ei_revenue = '$0'
		extra_info = {'status': status, 'budget': ei_budget, 'revenue': ei_revenue, 'homepage': homepage, 'collection_name': ei_collection_name, 'collection_id': ei_collection_id}
		meta = {'tmdb_id': tmdb_id, 'imdb_id': imdb_id, 'rating': rating, 'tagline': tagline, 'votes': votes, 'premiered': premiered, 'imdbnumber': imdb_id, 'trailer': trailer,
				'poster': poster, 'fanart': fanart, 'genre': genre, 'title': title, 'original_title': original_title, 'english_title': english_title, 'year': year, 'cast': cast,
				'duration': duration, 'rootname': rootname, 'country': country, 'country_codes': country_codes, 'mpaa': mpaa,'writer': writer, 'all_trailers': all_trailers,
				'director': director, 'alternative_titles': alternative_titles, 'plot': plot, 'studio': studio, 'extra_info': extra_info, 'mediatype': 'movie', 'tvdb_id': 'None',
				'clearlogo': clearlogo, 'landscape': landscape, 'spoken_language': spoken_language, 'keywords': keywords}
		metacache_set('movie', id_type, meta, movie_expiry(current_date, meta), current_time)
	except: pass
	return meta

def tvshow_meta(id_type, media_id, api_key, mpaa_region, current_date, current_time=None):
	if id_type == 'trakt_dict':
		if media_id.get('tmdb', None): id_type, media_id = 'tmdb_id', media_id['tmdb']
		elif media_id.get('imdb', None): id_type, media_id = 'imdb_id', media_id['imdb']
		elif media_id.get('tvdb', None): id_type, media_id = 'tvdb_id', media_id['tvdb']
		else: id_type, media_id = None, None
	if media_id == None: return None
	meta = metacache_get('tvshow', id_type, media_id, current_time)
	if meta: return meta
	try:
		if id_type == 'tmdb_id': data = tvshow_details(media_id, api_key)
		else:
			external_result = tvshow_external_id(id_type, media_id, api_key)
			if not external_result: data = None
			else: data = tvshow_details(external_result['id'], api_key)
		if not data or data.get('status_code', '') in invalid_error_codes:
			if id_type == 'tmdb_id': meta = {'tmdb_id': media_id, 'imdb_id': 'tt0000000', 'tvdb_id': '0000000', 'blank_entry': True}
			elif id_type == 'imdb_id': meta = {'tmdb_id': '0000000', 'imdb_id': media_id, 'tvdb_id': '0000000', 'blank_entry': True}
			else: meta = {'tmdb_id': '0000000', 'imdb_id': 'tt0000000', 'tvdb_id': media_id, 'blank_entry': True}
			metacache_set('tvshow', id_type, meta, EXPIRES_1_DAYS, current_time)
			return meta
		data_get = data.get
		cast, writer, director, studio, all_trailers, country, country_codes = [], [], [], [], [], [], []
		mpaa, trailer, spoken_language = '', '', ''
		external_ids = data_get('external_ids')
		tmdb_id, imdb_id, tvdb_id = data_get('id', ''), external_ids.get('imdb_id', ''), external_ids.get('tvdb_id', 'None')
		rating, votes = data_get('vote_average', ''), data_get('vote_count', '')
		plot, tagline, premiered = data_get('overview', ''), data_get('tagline', ''), data_get('first_air_date', '')
		season_data, total_seasons = data_get('seasons'), data_get('number_of_seasons')
		poster_path = data_get('poster_path', '')
		if poster_path: poster = tmdb_image_url % ('w780', poster_path)
		else: poster = ''
		backdrop_path = data_get('backdrop_path', '')
		if backdrop_path: fanart = tmdb_image_url % ('w1280', backdrop_path)
		else: fanart = ''
		images = data_get('images', {})
		if images:
			try:
				logo_path = images.get('logos')[0].get('file_path')
				if logo_path.endswith('png'): clearlogo = tmdb_image_url % ('original', logo_path)
				else: clearlogo = tmdb_image_url % ('original', logo_path.replace(logo_path.split('.')[-1], 'png'))
			except: clearlogo = ''
			try:
				landscape_path = images.get('backdrops')[0].get('file_path')
				landscape = tmdb_image_url % ('w1280', landscape_path)
			except: landscape = ''
		else: clearlogo, landscape = '', ''
		title, original_title = data_get('name'), data_get('original_name')
		try: english_title = [i['data']['name'] for i in data_get('translations')['translations'] if i['iso_639_1'] == 'en'][0]
		except: english_title = None
		try: year = str(data_get('first_air_date').split('-')[0]) or ''
		except: year = ''
		try: duration = min(data_get('episode_run_time'))*60
		except: duration = 0
		try: genre = [i['name'] for i in data_get('genres')]
		except: genre = []
		rootname = '%s (%s)' % (title, year)
		networks = data_get('networks', None)
		if networks:
			if len(networks) == 1: studio = ([i['name'] for i in networks][0],)
			else:
				try: studio = (next(i['name'] for i in networks if i['logo_path'] not in empty_value_check) or next(i['name'] for i in network),)
				except: pass
		production_countries = data_get('production_countries', None)
		if production_countries:
			country = [i['name'] for i in production_countries]
			country_codes = [i['iso_3166_1'] for i in production_countries]
		content_ratings = data_get('content_ratings', None)
		if content_ratings:
			try: mpaa = next(i['rating'] for i in content_ratings['results'] if i['iso_3166_1'] == mpaa_region)
			except: pass
		spoken_languages = data_get('spoken_languages', [])
		if spoken_languages:
			try: spoken_language = spoken_languages[0]['english_name']
			except: spoken_language = ''
		credits = data_get('credits')
		if credits:
			all_cast = credits.get('cast', None)
			if all_cast:
				try: cast = [{'name': i['name'], 'role': i['character'], 'thumbnail': tmdb_image_url % ('h632', i['profile_path']) if i['profile_path'] else ''} \
							for i in all_cast[:10]]
				except: pass
			crew = credits.get('crew', None)
			if crew:
				try: writer = [i['name'] for i in crew if i['job'] in writer_credits]
				except: pass
				try: director = [i['name'] for i in crew if i['job'] == 'Director']
				except: pass
		alternative_titles = data_get('alternative_titles', [])
		if alternative_titles:
			alternatives = alternative_titles['results']
			alternative_titles = [i['title'] for i in alternatives if i['iso_3166_1'] in alt_titles_check]
		videos = data_get('videos', None)
		if videos:
			try:
				all_trailers = sorted([i for i in videos['results'] if i['site'] == 'YouTube'], key=lambda x: x['name'])
				if all_trailers:
					trailer = next((youtube_url % i['key'] for i in all_trailers if i['official'] and i['type'] == 'Trailer' and 'official trailer' in i['name'].lower()), None) or \
					next((youtube_url % i['key'] for i in all_trailers if i['official'] and i['type'] == 'Trailer'), None) or \
					next((youtube_url % i['key'] for i in all_trailers if i['type'] == 'Trailer'), None) or \
					next((youtube_url % i['key'] for i in all_trailers if 'trailer' in i['name'].lower()), None) or \
					next((youtube_url % i['key'] for i in all_trailers), None) or ''
				else: trailler = ''
			except: pass
		keywords = data_get('keywords', None)
		status, _type, homepage = data_get('status', 'N/A'), data_get('type', 'N/A'), data_get('homepage', 'N/A')
		created_by = data_get('created_by', None)
		if created_by:
			try: ei_created_by = ', '.join([i['name'] for i in created_by])
			except: ei_created_by = 'N/A'
		else: ei_created_by = 'N/A'
		ei_next_ep, ei_last_ep = data_get('next_episode_to_air', None), data_get('last_episode_to_air', None)
		if ei_last_ep and not status in finished_show_check:
			total_aired_eps = sum([i['episode_count'] for i in season_data if i['season_number'] < ei_last_ep['season_number'] \
																		and i['season_number'] != 0]) + ei_last_ep['episode_number']
		else: total_aired_eps = data_get('number_of_episodes')
		extra_info = {'status': status, 'type': _type, 'homepage': homepage, 'created_by': ei_created_by, 'next_episode_to_air': ei_next_ep, 'last_episode_to_air': ei_last_ep}
		meta = {'tmdb_id': tmdb_id, 'tvdb_id': tvdb_id, 'imdb_id': imdb_id, 'rating': rating, 'plot': plot, 'tagline': tagline, 'votes': votes, 'premiered': premiered, 'year': year,
				'poster': poster, 'fanart': fanart, 'genre': genre, 'title': title, 'original_title': original_title, 'english_title': english_title, 'season_data': season_data,
				'alternative_titles': alternative_titles, 'duration': duration, 'rootname': rootname, 'imdbnumber': imdb_id, 'country': country, 'mpaa': mpaa, 'trailer': trailer,
				'country_codes': country_codes, 'writer': writer, 'director': director, 'all_trailers': all_trailers, 'cast': cast, 'studio': studio, 'extra_info': extra_info,
				'total_aired_eps': total_aired_eps, 'mediatype': 'tvshow', 'total_seasons': total_seasons, 'tvshowtitle': title, 'status': status, 'clearlogo': clearlogo,
				'landscape': landscape, 'spoken_language': spoken_language, 'keywords': keywords}
		metacache_set('tvshow', id_type, meta, tvshow_expiry(current_date, meta), current_time)
	except: pass
	return meta

def movieset_meta(media_id, api_key, current_time=None):
	if media_id == None: return None
	id_type = 'tmdb_id'
	meta = metacache_get('movie_set', id_type, media_id, current_time)
	if meta: return meta
	try:
		data = movie_set_details(media_id, api_key)
		if not data: return None
		elif 'status_code' in data and data.get('status_code') in invalid_error_codes:
			meta = {'tmdb_id': media_id, 'fanart_added': True, 'blank_entry': True}
			metacache_set('movie_set', id_type, meta, EXPIRES_1_DAYS, current_time)
			return meta
		data_get = data.get
		title, tmdb_id, plot = data_get('name'), data_get('id'), data_get('overview', '')
		poster_path = data_get('poster_path', None)
		if poster_path: poster = tmdb_image_url % ('w780', poster_path)
		else: poster = ''
		backdrop_path = data_get('backdrop_path', None)
		if backdrop_path: fanart = tmdb_image_url % ('w1280', backdrop_path)
		else: fanart = ''
		parts = data_get('parts')
		meta = {'tmdb_id': tmdb_id, 'title': title, 'plot': plot, 'poster': poster, 'fanart': fanart, 'parts': parts, 'imdb_id': 'None', 'tvdb_id': 'None'}
		metacache_set('movie_set', id_type, meta, EXPIRES_30_DAYS, current_time)
	except: pass
	return meta

def episodes_meta(season, meta):
	def _process():
		midseason_premiere = False
		for ep_data in details:
			writer, director, guest_stars = [], [], []
			ep_data_get = ep_data.get
			title, plot, premiered = ep_data_get('name'), ep_data_get('overview'), ep_data_get('air_date')
			season, episode, episode_id = ep_data_get('season_number'), ep_data_get('episode_number'), ep_data_get('id')
			try:
				if episode == 1:
					if 'premiere' in season_type: episode_type = 'series_premiere'
					else: episode_type = 'season_premiere'
				elif midseason_premiere: episode_type, midseason_premiere = 'mid_season_premiere', False
				else:
					episode_type = ep_data_get('episode_type')
					if episode_type == 'mid_season': episode_type, midseason_premiere = 'mid_season_finale', True
					elif episode_type == 'finale':
						if 'finale' in season_type: episode_type = 'series_finale'
						else: episode_type = 'season_finale'
					else: episode_type = ''
			except: episode_type = ''
			try: duration = ep_data_get('runtime')*60
			except: duration = 30*60
			rating, votes, still_path = ep_data_get('vote_average'), ep_data_get('vote_count'), ep_data_get('still_path', None)
			if still_path: thumb = tmdb_image_url % ('original', still_path)
			else: thumb = None
			cast = ep_data_get('guest_stars', [])
			if cast:
				try: guest_stars = [{'name': i['name'], 'role': i['character'], 'thumbnail': tmdb_image_url % ('h632', i['profile_path']) if i['profile_path'] else ''}\
									for i in cast[:20]]
				except: pass
			crew = ep_data_get('crew', None)
			if crew:
				try: writer = [i['name'] for i in crew if i['job'] in writer_credits]
				except: pass
				try: director = [i['name'] for i in crew if i['job'] == 'Director']
				except: pass
			yield {'writer': writer, 'director': director, 'mediatype': 'episode', 'episode_type': episode_type, 'episode_id': episode_id, 'title': title, 'plot': plot,
					'duration': duration, 'premiered': premiered, 'season': season, 'episode': episode, 'rating': rating, 'votes': votes, 'thumb': thumb, 'guest_stars': guest_stars}
	media_id, data = meta['tmdb_id'], None
	prop_string = '%s_%s' % (media_id, season)
	data = metacache_get_season(prop_string)
	if data is not None: return data
	try:
		season, tvshow_status, total_seasons = int(season), meta['status'], meta['total_seasons']
		if season == 1: season_type = 'premiere_finale' if (total_seasons == season and tvshow_status in finished_show_check) else 'premiere'
		else: season_type = 'finale' if (total_seasons == season and tvshow_status in finished_show_check) else ''
		if tvshow_status in finished_show_check or total_seasons > int(season): expiration = EXPIRES_182_DAYS
		else: expiration = EXPIRES_4_DAYS
		try:
			details = season_episodes_details(media_id, season)['episodes']
			total_episodes = len(details)
			data = list(_process())
		except: data, expiration = [], EXPIRES_4_DAYS
	except: data, expiration = [], EXPIRES_4_DAYS
	metacache_set_season(prop_string, data, expiration)
	return data

def all_episodes_meta(meta, include_specials=False):
	from threading import Thread
	def _get_tmdb_episodes(season):
		try: data.extend(episodes_meta(season, meta))
		except: pass
	try:
		data = []
		seasons = [i['season_number'] for i in meta['season_data']]
		if not include_specials: seasons = [i for i in seasons if not i == 0]
		threads = [Thread(target=_get_tmdb_episodes, args=(i,)) for i in seasons]
		[i.start() for i in threads]
		[i.join() for i in threads]
	except: pass
	return data

def episode_groups(media_id):
	try: groups = episode_groups_data(media_id)['results']
	except: groups = None
	return groups or None

def group_details(group_id):
	return episode_group_details(group_id)

def group_episode_data(details, episode_id=None, season_number=None, episode_number=None):
	def _comparer(episode_item):
		if episode_id: return episode_item['id'] == int(episode_id)
		else: return episode_item['season_number'] == int(season_number) and episode_item['episode_number'] == int(episode_number)
	episode_data = next(({'season': item['order'], 'episode': i['order'] + 1} for item in details['groups'] for i in item['episodes'] if _comparer(i)), None)
	return episode_data

def is_anime_check(tmdb_id):
	from modules.utils import get_datetime
	from modules.settings import tmdb_api_key, mpaa_region
	meta = tvshow_meta('tmdb_id', tmdb_id, tmdb_api_key(), mpaa_region(), get_datetime())
	genre = meta['genre']
	if not genre or 'Animation' in genre:
		try: keywords = meta.get('keywords', None) or tmdb_api.tmdb_tv_keywords(tmdb_id)['results']
		except: return False
		if not keywords: return False
		try: is_anime = next((i for i in keywords['results'] if i['id'] == 210024), None) is not None
		except: is_anime = False
		return is_anime
	return False

def movie_meta_external_id(external_source, external_id, api_key):
	return movie_external_id(external_source, external_id, api_key)

def tvshow_meta_external_id(external_source, external_id, api_key):
	return tvshow_external_id(external_source, external_id, api_key)

def movie_expiry(current_date, meta):
	try:
		difference = subtract_dates(current_date, jsondate_to_datetime(meta['premiered'], date_format, remove_time=True))
		if difference < 0: expiration = abs(difference) + 1
		elif difference <= 14: expiration = EXPIRES_7_DAYS
		elif difference <= 30: expiration = EXPIRES_14_DAYS
		elif difference <= 180: expiration = EXPIRES_30_DAYS
		else: expiration = EXPIRES_182_DAYS
	except: return EXPIRES_30_DAYS
	return max(expiration, EXPIRES_7_DAYS)

def tvshow_expiry(current_date, meta):
	try:
		if meta['status'] in finished_show_check: expiration = EXPIRES_182_DAYS
		else:
			data = subtract_dates(jsondate_to_datetime(meta['extra_info']['next_episode_to_air']['air_date'], date_format, remove_time=True), current_date) - EXPIRES_1_DAYS
			if data <= 1: expiration = EXPIRES_1_DAYS
			else: expiration = data*24
	except: expiration = EXPIRES_4_DAYS
	return expiration
