# -*- coding: utf-8 -*-
from apis import tmdb_api, fanarttv_api
from caches.meta_cache import metacache
from modules.utils import jsondate_to_datetime, subtract_dates
# from modules.kodi_utils import logger

movie_data, tvshow_data, english_translation = tmdb_api.movie_details, tmdb_api.tvshow_details, tmdb_api.english_translation
default_fanart_movies, default_fanart_tvshows = fanarttv_api.default_fanart_nometa_movies, fanarttv_api.default_fanart_nometa_tv
movie_external, tvshow_external, season_episodes_details = tmdb_api.movie_external_id, tmdb_api.tvshow_external_id, tmdb_api.season_episodes_details, 
movie_set_data, metacache_get, metacache_set, fanarttv_get = tmdb_api.movie_set_details, metacache.get, metacache.set, fanarttv_api.get
metacache_get_season, metacache_set_season = metacache.get_season, metacache.set_season
backup_resolutions = {'poster': 'w780', 'fanart': 'w1280', 'still': 'original', 'profile': 'h632', 'clearlogo': 'original'}
default_custom_artwork = {'custom_poster': '', 'custom_fanart': '', 'custom_clearlogo': ''}
writer_credits = ('Author', 'Writer', 'Screenplay', 'Characters')
alt_titles_check, trailers_check, finished_show_check, empty_value_check = ('US', 'GB', 'UK', ''), ('Trailer', 'Teaser'), ('Ended', 'Canceled'), ('', 'None', None)
tmdb_image_url, youtube_url, date_format = 'https://image.tmdb.org/t/p/%s%s', 'plugin://plugin.video.youtube/play/?video_id=%s', '%Y-%m-%d'
EXPIRES_1_DAYS, EXPIRES_4_DAYS, EXPIRES_7_DAYS, EXPIRES_14_DAYS, EXPIRES_30_DAYS, EXPIRES_182_DAYS = 1, 4, 7, 14, 30, 182
invalid_error_codes = (6, 34, 37)

def movie_meta(id_type, media_id, user_info, current_date, current_time=None):
	if id_type == 'trakt_dict':
		if media_id.get('tmdb', None): id_type, media_id = 'tmdb_id', media_id['tmdb']
		elif media_id.get('imdb', None): id_type, media_id = 'imdb_id', media_id['imdb']
		else: id_type, media_id = None, None
	if media_id == None: return None
	extra_fanart_enabled, fanart_client_key = user_info['extra_fanart_enabled'], user_info['fanart_client_key']
	language = user_info['language']
	meta, custom_artwork = metacache_get('movie', id_type, media_id, current_time)
	if meta:
		if not meta.get('fanart_added', False) and extra_fanart_enabled:
			fanart_data, all_fanart_images = fanarttv_get('movies', language, meta['tmdb_id'], fanart_client_key)
			meta.update(fanart_data)
			all_images = meta['images']
			meta['images'].update({'poster': all_images['poster'] + all_fanart_images['poster'], 'fanart': all_images['fanart'] + all_fanart_images['fanart'],
								'clearlogo': all_images['clearlogo'] + all_fanart_images['clearlogo'], 'banner': all_fanart_images['banner'],
								'clearart': all_fanart_images['clearart'], 'landscape': all_fanart_images['landscape'], 'discart': all_fanart_images['discart'],
								'keyart': all_fanart_images['keyart']})
			metacache_set('movie', id_type, meta, movie_expiry(current_date, meta), current_time)
		return meta
	try:
		tmdb_api = user_info['tmdb_api']
		if id_type in ('tmdb_id', 'imdb_id'): data = movie_data(media_id, language, tmdb_api)
		else:
			external_result = movie_external(id_type, media_id, tmdb_api)
			if not external_result: data = None
			else: data = movie_data(external_result['id'], language, tmdb_api)
		if not data: return None
		elif data.get('status_code') in invalid_error_codes:
			if id_type == 'tmdb_id': meta = {'tmdb_id': media_id, 'imdb_id': 'tt0000000', 'tvdb_id': '0000000', 'fanart_added': True, 'blank_entry': True}
			else: meta = {'tmdb_id': '0000000', 'imdb_id': media_id, 'tvdb_id': '0000000', 'fanart_added': True, 'blank_entry': True}
			metacache_set('movie', id_type, meta, EXPIRES_1_DAYS, current_time)
			return meta
		if language != 'en':
			if data['overview'] in empty_value_check:
				media_id, id_type = data['id'], 'tmdb_id'
				eng_data = movie_data(media_id, 'en', tmdb_api)
				data['overview'] = eng_data['overview']
				if 'videos' in data:
					all_trailers = data['videos']['results']
					if all_trailers:
						try: trailer_test = [i for i in all_trailers if i['site'] == 'YouTube' and i['type'] in trailers_check][0]
						except: trailer_test = False
					else: trailer_test = False
				else: trailer_test = False
				if not trailer_test:
					if 'videos' in eng_data:
						eng_all_trailers = eng_data['videos']['results']
						if eng_all_trailers: data['videos']['results'] = eng_all_trailers
		if extra_fanart_enabled: fanart_data, all_fanart_images = fanarttv_get('movies', language, data['id'], fanart_client_key)
		else: fanart_data, all_fanart_images = None, None
		image_resolution = user_info.get('image_resolution', backup_resolutions)
		data_get = data.get
		images = {'poster': [], 'fanart': [], 'clearlogo': []}
		cast, all_trailers, country, country_codes = [], [], [], []
		writer, mpaa, director, trailer, studio = '', '', '', '', ''
		tmdb_id, imdb_id = data_get('id', ''), data_get('imdb_id', '')
		rating, votes = data_get('vote_average', ''), data_get('vote_count', '')
		plot, tagline, premiered = data_get('overview', ''), data_get('tagline', ''), data_get('release_date', '')
		extra_images = data_get('images', {})
		if extra_images:
			images['poster'] = [tmdb_image_url % (image_resolution['poster'], (i['file_path'] if i['file_path'].endswith('jpg') \
								else i['file_path'].replace(i['file_path'].split('.')[-1], 'jpg'))) for i in extra_images['posters']]
			images['fanart'] = [tmdb_image_url % (image_resolution['fanart'], (i['file_path'] if i['file_path'].endswith('jpg') \
								else i['file_path'].replace(i['file_path'].split('.')[-1], 'jpg'))) for i in extra_images['backdrops']]
			images['clearlogo'] = [tmdb_image_url % (image_resolution['clearlogo'], (i['file_path'] if i['file_path'].endswith('png') \
								else i['file_path'].replace(i['file_path'].split('.')[-1], 'png'))) for i in extra_images['logos']]
		images_get = images.get
		poster_path = data_get('poster_path', None)
		if poster_path: default_poster = tmdb_image_url % (image_resolution['poster'], poster_path)
		else: default_poster = ''
		try: extra_poster = images_get('poster')[0]
		except: extra_poster = ''
		poster = default_poster or extra_poster
		if default_poster and not default_poster in images['poster']: images['poster'].insert(0, default_poster)
		backdrop_path = data_get('backdrop_path', None)
		if backdrop_path: default_fanart = tmdb_image_url % (image_resolution['fanart'], backdrop_path)
		else: default_fanart = ''
		try: extra_fanart = images_get('fanart')[0]
		except: extra_fanart = ''
		fanart = default_fanart or extra_fanart
		if default_fanart and not default_fanart in images['fanart']: images['fanart'].insert(0, default_fanart)
		try: clearlogo = images_get('clearlogo')[0]
		except: clearlogo = ''
		title, original_title = data_get('title'), data_get('original_title')
		try: english_title = [i['data']['title'] for i in data_get('translations')['translations'] if i['iso_639_1'] == 'en'][0]
		except: english_title = None
		try: year = str(data_get('release_date').split('-')[0])
		except: year = ''
		try: duration = int(data_get('runtime', '90') * 60)
		except: duration = 0
		try: genre = ', '.join([i['name'] for i in data_get('genres')])
		except: genre == []
		rootname = '%s (%s)' % (title, year)
		companies = data_get('production_companies')
		if companies:
			if len(companies) == 1: studio = [i['name'] for i in companies][0]
			else:
				try: studio = [i['name'] for i in companies if i['logo_path'] not in empty_value_check][0] or [i['name'] for i in companies][0]
				except: pass
		production_countries = data_get('production_countries', None)
		if production_countries:
			country = [i['name'] for i in production_countries]
			country_codes = [i['iso_3166_1'] for i in production_countries]
		release_dates = data_get('release_dates')
		if release_dates:
			try: mpaa = [x['certification'] for i in release_dates['results'] for x in i['release_dates'] \
						if i['iso_3166_1'] == user_info['mpaa_region'] and x['certification'] != '' and x['note'] == ''][0]
			except: pass
		credits = data_get('credits')
		if credits:
			all_cast = credits.get('cast', None)
			if all_cast:
				try: cast = [{'name': i['name'], 'role': i['character'], 'thumbnail': tmdb_image_url % (image_resolution['profile'], i['profile_path'])if i['profile_path'] else ''}\
							for i in all_cast]
				except: pass
			crew = credits.get('crew', None)
			if crew:
				try: writer = ', '.join([i['name'] for i in crew if i['job'] in writer_credits])
				except: pass
				try: director = [i['name'] for i in crew if i['job'] == 'Director'][0]
				except: pass
		alternative_titles = data_get('alternative_titles', [])
		if alternative_titles:
			alternatives = alternative_titles['titles']
			alternative_titles = [i['title'] for i in alternatives if i['iso_3166_1'] in alt_titles_check]
		else: alternative_titles = []
		videos = data_get('videos', None)
		if videos:
			all_trailers = videos['results']
			try: trailer = [youtube_url % i['key'] for i in all_trailers if i['site'] == 'YouTube' and i['type'] in trailers_check][0]
			except: pass
		status, homepage = data_get('status', 'N/A'), data_get('homepage', 'N/A')
		belongs_to_collection = data_get('belongs_to_collection')
		if belongs_to_collection: ei_collection_name, ei_collection_id = belongs_to_collection['name'], belongs_to_collection['id']
		else: ei_collection_name, ei_collection_id = None, None
		try: ei_budget = '${:,}'.format(data_get('budget'))
		except: ei_budget = '$0'
		try: ei_revenue = '${:,}'.format(data_get('revenue'))
		except: ei_revenue = '$0'
		if fanart_data: images.update({'poster': images['poster'] + all_fanart_images['poster'], 'fanart': images['fanart'] + all_fanart_images['fanart'],
									'clearlogo': images['clearlogo'] + all_fanart_images['clearlogo'], 'banner': all_fanart_images['banner'],
									'clearart': all_fanart_images['clearart'], 'landscape': all_fanart_images['landscape'], 'discart': all_fanart_images['discart'],
									'keyart': all_fanart_images['keyart']})
		extra_info = {'status': status, 'budget': ei_budget, 'revenue': ei_revenue, 'homepage': homepage, 'collection_name': ei_collection_name, 'collection_id': ei_collection_id}
		meta = {'tmdb_id': tmdb_id, 'imdb_id': imdb_id, 'rating': rating, 'tagline': tagline, 'votes': votes, 'premiered': premiered, 'imdbnumber': imdb_id, 'trailer': trailer,
				'poster': poster, 'fanart': fanart, 'genre': genre, 'title': title, 'original_title': original_title, 'english_title': english_title, 'year': year, 'cast': cast,
				'duration': duration, 'rootname': rootname, 'country': country, 'country_codes': country_codes, 'mpaa': mpaa,'writer': writer, 'all_trailers': all_trailers,
				'director': director, 'alternative_titles': alternative_titles, 'plot': plot, 'studio': studio, 'extra_info': extra_info, 'mediatype': 'movie', 'tvdb_id': 'None',
				'clearlogo': clearlogo, 'images': images}
		meta.update(fanart_data or default_fanart_movies)
		meta.update(custom_artwork or default_custom_artwork)
		metacache_set('movie', id_type, meta, movie_expiry(current_date, meta), current_time)
	except: pass
	return meta

def tvshow_meta(id_type, media_id, user_info, current_date, current_time=None):
	if id_type == 'trakt_dict':
		if media_id.get('tmdb', None): id_type, media_id = 'tmdb_id', media_id['tmdb']
		elif media_id.get('imdb', None): id_type, media_id = 'imdb_id', media_id['imdb']
		elif media_id.get('tvdb', None): id_type, media_id = 'tvdb_id', media_id['tvdb']
		else: id_type, media_id = None, None
	if media_id == None: return None
	extra_fanart_enabled, fanart_client_key = user_info['extra_fanart_enabled'], user_info['fanart_client_key']
	language = user_info['language']
	meta, custom_artwork = metacache_get('tvshow', id_type, media_id, current_time)
	if meta:
		if not meta.get('fanart_added', False) and extra_fanart_enabled:
			fanart_data, all_fanart_images = fanarttv_get('tv', language, meta['tvdb_id'], fanart_client_key)
			meta.update(fanart_data)
			all_images = meta['images']
			meta['images'].update({'poster': all_images['poster'] + all_fanart_images['poster'], 'fanart': all_images['fanart'] + all_fanart_images['fanart'],
								'clearlogo': all_images['clearlogo'] + all_fanart_images['clearlogo'], 'banner': all_fanart_images['banner'],
								'clearart': all_fanart_images['clearart'], 'landscape': all_fanart_images['landscape']})
			metacache_set('tvshow', id_type, meta, tvshow_expiry(current_date, meta), current_time)
		return meta
	try:
		tmdb_api = user_info['tmdb_api']
		if id_type == 'tmdb_id': data = tvshow_data(media_id, language, tmdb_api)
		else:
			external_result = tvshow_external(id_type, media_id, tmdb_api)
			if not external_result: data = None
			else: data = tvshow_data(external_result['id'], language, tmdb_api)
		if not data: return None
		elif 'status_code' in data and data.get('status_code') in invalid_error_codes:
			if id_type == 'tmdb_id': meta = {'tmdb_id': media_id, 'imdb_id': 'tt0000000', 'tvdb_id': '0000000', 'fanart_added': True, 'blank_entry': True}
			elif id_type == 'imdb_id': meta = {'tmdb_id': '0000000', 'imdb_id': media_id, 'tvdb_id': '0000000', 'fanart_added': True, 'blank_entry': True}
			else: meta = {'tmdb_id': '0000000', 'imdb_id': 'tt0000000', 'tvdb_id': media_id, 'fanart_added': True, 'blank_entry': True}
			metacache_set('tvshow', id_type, meta, EXPIRES_1_DAYS, current_time)
			return meta
		if language != 'en':
			if data['overview'] in empty_value_check:
				media_id, id_type = data['id'], 'tmdb_id'
				eng_data = tvshow_data(media_id, 'en', tmdb_api)
				data['overview'] = eng_data['overview']
				if 'videos' in data:
					all_trailers = data['videos']['results']
					if all_trailers:
						try: trailer_test = [i for i in all_trailers if i['site'] == 'YouTube' and i['type'] in trailers_check][0]
						except: trailer_test = False
					else: trailer_test = False
				else: trailer_test = False
				if not trailer_test:
					if 'videos' in eng_data:
						eng_all_trailers = eng_data['videos']['results']
						if eng_all_trailers: data['videos']['results'] = eng_all_trailers
		if extra_fanart_enabled: fanart_data, all_fanart_images = fanarttv_get('tv', language, data['external_ids']['tvdb_id'], fanart_client_key)
		else: fanart_data, all_fanart_images = None, None
		image_resolution = user_info.get('image_resolution', backup_resolutions)
		data_get = data.get
		images = {'poster': [], 'fanart': [], 'clearlogo': []}
		cast, all_trailers, country, country_codes = [], [], [], []
		writer, mpaa, director, trailer, studio = '', '', '', '', ''
		external_ids = data_get('external_ids')
		tmdb_id, imdb_id, tvdb_id = data_get('id', ''), external_ids.get('imdb_id', ''), external_ids.get('tvdb_id', 'None')
		rating, votes = data_get('vote_average', ''), data_get('vote_count', '')
		plot, tagline, premiered = data_get('overview', ''), data_get('tagline', ''), data_get('first_air_date', '')
		season_data, total_seasons = data_get('seasons'), data_get('number_of_seasons')
		extra_images = data_get('images', {})
		if extra_images:
			images['poster'] = [tmdb_image_url % (image_resolution['poster'], (i['file_path'] if i['file_path'].endswith('jpg') \
								else i['file_path'].replace(i['file_path'].split('.')[-1], 'jpg'))) for i in extra_images['posters']]
			images['fanart'] = [tmdb_image_url % (image_resolution['fanart'], (i['file_path'] if i['file_path'].endswith('jpg') \
								else i['file_path'].replace(i['file_path'].split('.')[-1], 'jpg'))) for i in extra_images['backdrops']]
			images['clearlogo'] = [tmdb_image_url % (image_resolution['clearlogo'], (i['file_path'] if i['file_path'].endswith('png') \
								else i['file_path'].replace(i['file_path'].split('.')[-1], 'png'))) for i in extra_images['logos']]
		images_get = images.get
		poster_path = data_get('poster_path', None)
		if poster_path: default_poster = tmdb_image_url % (image_resolution['poster'], poster_path)
		else: default_poster = ''
		try: extra_poster = images_get('poster')[0]
		except: extra_poster = ''
		poster = default_poster or extra_poster
		if default_poster and not default_poster in images['poster']: images['poster'].insert(0, default_poster)
		backdrop_path = data_get('backdrop_path', None)
		if backdrop_path: default_fanart = tmdb_image_url % (image_resolution['fanart'], backdrop_path)
		else: default_fanart = ''
		try: extra_fanart = images_get('fanart')[0]
		except: extra_fanart = ''
		fanart = default_fanart or extra_fanart
		if default_fanart and not default_fanart in images['fanart']: images['fanart'].insert(0, default_fanart)
		try: clearlogo = images_get('clearlogo')[0]
		except: clearlogo = ''
		title, original_title = data_get('name'), data_get('original_name')
		try: english_title = [i['data']['name'] for i in data_get('translations')['translations'] if i['iso_639_1'] == 'en'][0]
		except: english_title = None
		try: year = str(data_get('first_air_date').split('-')[0]) or ''
		except: year = ''
		try: duration = min(data_get('episode_run_time'))*60
		except: duration = 0
		try: genre = ', '.join([i['name'] for i in data_get('genres')])
		except: genre = []
		rootname = '%s (%s)' % (title, year)
		networks = data_get('networks', None)
		if networks:
			if len(networks) == 1: studio = [i['name'] for i in networks][0]
			else:
				try: studio = [i['name'] for i in networks if i['logo_path'] not in empty_value_check][0] or [i['name'] for i in networks][0]
				except: pass
		production_countries = data_get('production_countries', None)
		if production_countries:
			country = [i['name'] for i in production_countries]
			country_codes = [i['iso_3166_1'] for i in production_countries]
		content_ratings = data_get('content_ratings', None)
		release_dates = data_get('release_dates', None)
		if content_ratings:
			try: mpaa = [i['rating'] for i in content_ratings['results'] if i['iso_3166_1'] == user_info['mpaa_region']][0]
			except: pass
		elif release_dates:
			try: mpaa = [i['release_dates'][0]['certification'] for i in release_dates['results'] if i['iso_3166_1'] == user_info['mpaa_region']][0]
			except: pass
		credits = data_get('credits')
		if credits:
			all_cast = credits.get('cast', None)
			if all_cast:
				try: cast = [{'name': i['name'], 'role': i['character'],
							'thumbnail': tmdb_image_url % (image_resolution['profile'], i['profile_path']) if i['profile_path'] else ''}\
							for i in all_cast]
				except: pass
			crew = credits.get('crew', None)
			if crew:
				try: writer = ', '.join([i['name'] for i in crew if i['job'] in writer_credits])
				except: pass
				try: director = [i['name'] for i in crew if i['job'] == 'Director'][0]
				except: pass
		alternative_titles = data_get('alternative_titles', [])
		if alternative_titles:
			alternatives = alternative_titles['results']
			alternative_titles = [i['title'] for i in alternatives if i['iso_3166_1'] in alt_titles_check]
		videos = data_get('videos', None)
		if videos:
			all_trailers = videos['results']
			try: trailer = [youtube_url % i['key'] for i in all_trailers if i['site'] == 'YouTube' and i['type'] in trailers_check][0]
			except: pass
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
		if fanart_data: images.update({'poster': images['poster'] + all_fanart_images['poster'], 'fanart': images['fanart'] + all_fanart_images['fanart'],
									'clearlogo': images['clearlogo'] + all_fanart_images['clearlogo'], 'banner': all_fanart_images['banner'],
									'clearart': all_fanart_images['clearart'], 'landscape': all_fanart_images['landscape']})
		extra_info = {'status': status, 'type': _type, 'homepage': homepage, 'created_by': ei_created_by, 'next_episode_to_air': ei_next_ep, 'last_episode_to_air': ei_last_ep}
		meta = {'tmdb_id': tmdb_id, 'tvdb_id': tvdb_id, 'imdb_id': imdb_id, 'rating': rating, 'plot': plot, 'tagline': tagline, 'votes': votes, 'premiered': premiered, 'year': year,
				'poster': poster, 'fanart': fanart, 'genre': genre, 'title': title, 'original_title': original_title, 'english_title': english_title, 'season_data': season_data,
				'alternative_titles': alternative_titles, 'duration': duration, 'rootname': rootname, 'imdbnumber': imdb_id, 'country': country, 'mpaa': mpaa, 'trailer': trailer,
				'country_codes': country_codes, 'writer': writer, 'director': director, 'all_trailers': all_trailers, 'cast': cast, 'studio': studio, 'extra_info': extra_info,
				'total_aired_eps': total_aired_eps, 'mediatype': 'tvshow', 'total_seasons': total_seasons, 'tvshowtitle': title, 'status': status, 'clearlogo': clearlogo,
				'images': images}
		meta.update(fanart_data or default_fanart_tvshows)
		meta.update(custom_artwork or default_custom_artwork)
		metacache_set('tvshow', id_type, meta, tvshow_expiry(current_date, meta), current_time)
	except: pass
	return meta

def movieset_meta(media_id, user_info, current_time=None):
	if media_id == None: return None
	id_type = 'tmdb_id'
	extra_fanart_enabled, fanart_client_key = user_info['extra_fanart_enabled'], user_info['fanart_client_key']
	meta, custom_artwork = metacache_get('movie_set', id_type, media_id, current_time)
	if meta:
		if not meta.get('fanart_added', False) and extra_fanart_enabled:
			fanart_data, all_fanart_images = fanarttv_get('movies', '', meta['tmdb_id'], fanart_client_key)
			meta.update(fanart_data)
			metacache_set('movie_set', id_type, meta, EXPIRES_30_DAYS, current_time)
		return meta
	try:
		tmdb_api = user_info['tmdb_api']
		data = movie_set_data(media_id, tmdb_api)
		if not data: return None
		elif 'status_code' in data and data.get('status_code') in invalid_error_codes:
			meta = {'tmdb_id': media_id, 'fanart_added': True, 'blank_entry': True}
			metacache_set('movie_set', id_type, meta, EXPIRES_1_DAYS, current_time)
			return meta
		if extra_fanart_enabled: fanart_data, all_fanart_images = fanarttv_get('movies', '', data['id'], fanart_client_key)
		else: fanart_data, all_fanart_images = None, None
		image_resolution = user_info.get('image_resolution', backup_resolutions)
		data_get = data.get
		title, tmdb_id, plot = data_get('name'), data_get('id'), data_get('overview', '')
		poster_path = data_get('poster_path', None)
		if poster_path: poster = tmdb_image_url % (image_resolution['poster'], poster_path)
		else: poster = ''
		backdrop_path = data_get('backdrop_path', None)
		if backdrop_path: fanart = tmdb_image_url % (image_resolution['fanart'], backdrop_path)
		else: fanart = ''
		parts = data_get('parts')
		meta = {'tmdb_id': tmdb_id, 'title': title, 'plot': plot, 'poster': poster, 'fanart': fanart, 'parts': parts, 'imdb_id': 'None', 'tvdb_id': 'None'}
		meta.update(fanart_data or default_fanart_movies)
		metacache_set('movie_set', id_type, meta, EXPIRES_30_DAYS, current_time)
	except: pass
	return meta

def episodes_meta(season, meta, user_info):
	def _process():
		midseason_premiere = False
		for ep_data in details:
			writer, director, guest_stars = '', '', []
			ep_data_get = ep_data.get
			title, plot, premiered = ep_data_get('name'), ep_data_get('overview'), ep_data_get('air_date')
			season, episode = ep_data_get('season_number'), ep_data_get('episode_number')
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
			if still_path: thumb = tmdb_image_url % (still_resolution, still_path)
			else: thumb = None
			guest_stars_list = ep_data_get('guest_stars', None)
			if guest_stars_list:
				try: guest_stars = [{'name': i['name'], 'role': i['character'], 'thumbnail': tmdb_image_url % (profile_resolution, i['profile_path']) \
									if i['profile_path'] else ''} for i in guest_stars_list]
				except: pass
			crew = ep_data_get('crew', None)
			if crew:
				try: writer = ', '.join([i['name'] for i in crew if i['job'] in writer_credits])
				except: pass
				try: director = [i['name'] for i in crew if i['job'] == 'Director'][0]
				except: pass
			yield {'writer': writer, 'director': director, 'guest_stars': guest_stars, 'mediatype': 'episode', 'title': title, 'plot': plot, 'duration': duration,
					'premiered': premiered, 'season': season, 'episode': episode, 'rating': rating, 'votes': votes, 'thumb': thumb, 'episode_type': episode_type}
	media_id, data = meta['tmdb_id'], None
	prop_string = '%s_%s' % (media_id, season)
	data = metacache_get_season(prop_string)
	if data: return data
	try:
		season, tvshow_status, total_seasons = int(season), meta['status'], meta['total_seasons']
		if season == 1: season_type = 'premiere_finale' if (total_seasons == season and tvshow_status in finished_show_check) else 'premiere'
		else: season_type = 'finale' if (total_seasons == season and tvshow_status in finished_show_check) else ''
		if tvshow_status in finished_show_check or total_seasons > int(season): expiration = EXPIRES_182_DAYS
		else: expiration = EXPIRES_4_DAYS
		
		image_resolution = user_info.get('image_resolution', backup_resolutions)
		still_resolution, profile_resolution = image_resolution['still'], image_resolution['profile']
		details = season_episodes_details(media_id, season, user_info['language'], user_info['tmdb_api'])['episodes']
		data = list(_process())
		metacache_set_season(prop_string, data, expiration)
	except: pass
	return data

def all_episodes_meta(meta, user_info, include_specials=False):
	from modules.kodi_utils import Thread
	def _get_tmdb_episodes(season):
		try: data.extend(episodes_meta(season, meta, user_info))
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

def movie_meta_external_id(external_source, external_id):
	return movie_external(external_source, external_id)

def tvshow_meta_external_id(external_source, external_id):
	return tvshow_external(external_source, external_id)

def english_translation(media_type, media_id, user_info):
	key = 'title' if media_type == 'movie' else 'name'
	translations = english_translation(media_type, media_id, user_info['tmdb_api'])
	try: english = [i['data'][key] for i in translations if i['iso_639_1'] == 'en'][0]
	except: english = ''
	return english

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
			else: expiration = data
	except: expiration = EXPIRES_4_DAYS
	return expiration
