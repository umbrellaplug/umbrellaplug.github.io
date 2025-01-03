# -*- coding: utf-8 -*-
import datetime
from caches.meta_cache import cache_function
from caches.lists_cache import lists_cache_object
from modules.meta_lists import oscar_winners, years_tvshows
from modules.settings import get_meta_filter, tmdb_api_key
from modules.utils import make_thread_list_enumerate
from modules.kodi_utils import make_session, tmdb_dict_removals, remove_keys, notification
# from modules.kodi_utils import logger

EXPIRY_4_HOURS, EXPIRY_1_DAY, EXPIRY_1_WEEK = 4, 24, 168
base_url = 'https://api.themoviedb.org/3'
movies_append = 'external_ids,videos,credits,release_dates,alternative_titles,translations,images,keywords'
tvshows_append = 'external_ids,videos,credits,content_ratings,alternative_titles,translations,images,keywords'
empty_setting_check = (None, 'empty_setting', '')
session = make_session(base_url)
timeout = 20.0

def no_api_key():
	notification('Please set a valid TMDb API Key')
	return []

def movie_details(tmdb_id, api_key):
	try:
		url = '%s/movie/%s?api_key=%s&language=en&append_to_response=%s&include_image_language=en' % (base_url, tmdb_id, api_key, movies_append)
		return get_tmdb(url).json()
	except: return None

def tvshow_details(tmdb_id, api_key):
	try:
		url = '%s/tv/%s?api_key=%s&language=en&append_to_response=%s&include_image_language=en' % (base_url, tmdb_id, api_key, tvshows_append)
		return get_tmdb(url).json()
	except: return None

def episode_groups_data(tmdb_id):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'episode_groups_data_%s' % tmdb_id
	url = '%s/tv/%s/episode_groups?api_key=%s' % (base_url, tmdb_id, api_key)
	return cache_function(get_tmdb, string, url, expiration=EXPIRY_1_WEEK)

def episode_group_details(group_id):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'episode_groups_details_%s' % group_id
	url = '%s/tv/episode_group/%s?api_key=%s' % (base_url, group_id, api_key)
	return cache_function(get_tmdb, string, url, expiration=EXPIRY_1_WEEK)

def movie_set_details(collection_id, api_key):
	try:
		url = '%s/collection/%s?api_key=%s&language=en' % (base_url, collection_id, api_key)
		return get_tmdb(url).json()
	except: return None

def movie_external_id(external_source, external_id, api_key):
	try:
		string = 'movie_external_id_%s_%s' % (external_source, external_id)
		url = '%s/find/%s?api_key=%s&external_source=%s' % (base_url, external_id, api_key, external_source)
		result = cache_function(get_tmdb, string, url)
		result = result['movie_results']
		if result: return result[0]
		else: return None
	except: return None

def tvshow_external_id(external_source, external_id, api_key):
	try:
		string = 'tvshow_external_id_%s_%s' % (external_source, external_id)
		url = '%s/find/%s?api_key=%s&external_source=%s' % (base_url, external_id, api_key, external_source)
		result = cache_function(get_tmdb, string, url)
		result = result['tv_results']
		if result: return result[0]
		else: return None
	except: return None

def tmdb_movies_oscar_winners(page_no):
	return oscar_winners[page_no-1]

def tmdb_network_details(network_id):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_network_details_%s' % network_id
	url = '%s/network/%s?api_key=%s' % (base_url, network_id, api_key)
	return cache_function(get_tmdb, string, url, expiration=EXPIRY_1_WEEK)

def tmdb_keywords_by_query(query, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_keywords_by_query_%s_%s' % (query, page_no)
	url = '%s/search/keyword?api_key=%s&query=%s&page=%s' % (base_url, api_key, query, page_no)
	return cache_function(get_tmdb, string, url, expiration=EXPIRY_1_WEEK)

def tmdb_movie_keywords(tmdb_id):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_movie_keywords_%s' % tmdb_id
	url = '%s/movie/%s/keywords?api_key=%s' % (base_url, tmdb_id, api_key)
	return cache_function(get_tmdb, string, url, expiration=EXPIRY_1_WEEK)

def tmdb_tv_keywords(tmdb_id):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_tv_keywords_%s' % tmdb_id
	url = '%s/tv/%s/keywords?api_key=%s' % (base_url, tmdb_id, api_key)
	return cache_function(get_tmdb, string, url, expiration=EXPIRY_1_WEEK)

def tmdb_movie_keyword_results(tmdb_id, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_movie_keyword_results_%s_%s' % (tmdb_id, page_no)
	url = '%s/discover/movie?api_key=%s&language=en-US&with_keywords=%s&page=%s' % (base_url, api_key, tmdb_id, page_no)
	return lists_cache_object(get_data, string, url)

def tmdb_tv_keyword_results(tmdb_id, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_tv_keyword_results_%s_%s' % (tmdb_id, page_no)
	url = '%s/discover/tv?api_key=%s&language=en-US&with_keywords=%s&page=%s' % (base_url, api_key, tmdb_id, page_no)
	return lists_cache_object(get_data, string, url)

def tmdb_movie_keyword_results_direct(query, page_no):
	if tmdb_api_key() in empty_setting_check: return no_api_key()
	try:
		results = tmdb_movie_keyword_results(tmdb_keywords_by_query(query, page_no)['results'][0]['id'], page_no)
		results['total_pages'] = 1
		return results
	except: return None

def tmdb_tv_keyword_results_direct(query, page_no):
	if tmdb_api_key() in empty_setting_check: return no_api_key()
	try:
		results = tmdb_tv_keyword_results(tmdb_keywords_by_query(query, page_no)['results'][0]['id'], page_no)
		results['total_pages'] = 1
		return results
	except: return None

def tmdb_company_id(query):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_company_id_%s' % query
	url = '%s/search/company?api_key=%s&query=%s' % (base_url, api_key, query)
	return cache_function(get_tmdb, string, url, expiration=EXPIRY_1_WEEK)

def tmdb_media_images(media_type, tmdb_id):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	if media_type in ('movie', 'movies'): media_type = 'movie'
	else: media_type = 'tv'
	string = 'tmdb_media_images_%s_%s' % (media_type, tmdb_id)
	url = '%s/%s/%s/images?include_image_language=en,null&api_key=%s' % (base_url, media_type, tmdb_id, api_key)
	return cache_function(get_tmdb, string, url, expiration=EXPIRY_1_WEEK)

def tmdb_media_videos(media_type, tmdb_id):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	if media_type in ('movie', 'movies'): media_type = 'movie'
	else: media_type = 'tv'
	string = 'tmdb_media_videos_%s_%s' % (media_type, tmdb_id)
	url = '%s/%s/%s/videos?api_key=%s' % (base_url, media_type, tmdb_id, api_key)
	return cache_function(get_tmdb, string, url, expiration=EXPIRY_1_WEEK)

def tmdb_movies_discover(query, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	if '[current_date]' in query: query = query.replace('[current_date]', get_current_date())
	if '[random]' in query: query = query.replace('[random]', '')
	string = url = query + '&api_key=%s&page=%s' % (api_key, page_no)
	return lists_cache_object(get_tmdb, string, url, True, EXPIRY_1_DAY)

def tmdb_movies_popular(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_movies_popular_%s' % page_no
	url = '%s/movie/popular?api_key=%s&language=en-US&region=US&with_original_language=en&page=%s' % (base_url, api_key, page_no)
	return lists_cache_object(get_data, string, url)

def tmdb_movies_popular_today(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_movies_popular_today_%s' % page_no
	url = '%s/trending/movie/day?api_key=%s&language=en-US&region=US&with_original_language=en&page=%s' % (base_url, api_key, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_DAY)

def tmdb_movies_blockbusters(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_movies_blockbusters_%s' % page_no
	url = '%s/discover/movie?api_key=%s&language=en-US&region=US&with_original_language=en&sort_by=revenue.desc&page=%s' % (base_url, api_key, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_WEEK)

def tmdb_movies_in_theaters(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_movies_in_theaters_%s' % page_no
	url = '%s/movie/now_playing?api_key=%s&language=en-US&region=US&with_original_language=en&page=%s' % (base_url, api_key, page_no)
	return lists_cache_object(get_data, string, url)

def tmdb_movies_upcoming(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	current_date, future_date = get_dates(31, reverse=False)
	string = 'tmdb_movies_upcoming_%s' % page_no
	url = '%s/discover/movie?api_key=%s&language=en-US&region=US&with_original_language=en&release_date.gte=%s&release_date.lte=%s&with_release_type=3|2|1&page=%s' \
							% (base_url, api_key, current_date, future_date, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_DAY)

def tmdb_movies_latest_releases(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	current_date, previous_date = get_dates(31, reverse=True)
	string = 'tmdb_movies_latest_releases_%s' % page_no
	url = '%s/discover/movie?api_key=%s&language=en-US&region=US&with_original_language=en&release_date.gte=%s&release_date.lte=%s&with_release_type=4|5|6&page=%s' \
							% (base_url, api_key, previous_date, current_date, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_DAY)

def tmdb_movies_premieres(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	current_date, previous_date = get_dates(31, reverse=True)
	string = 'tmdb_movies_premieres_%s' % page_no
	url = '%s/discover/movie?api_key=%s&language=en-US&region=US&with_original_language=en&release_date.gte=%s&release_date.lte=%s&with_release_type=1|3|2&page=%s' \
							% (base_url, api_key, previous_date, current_date, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_DAY)

def tmdb_movies_genres(genre_id, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_movies_genres_%s_%s' % (genre_id, page_no)
	url = '%s/discover/movie?api_key=%s&with_genres=%s&language=en-US&region=US&with_original_language=en&release_date.lte=%s&page=%s' \
			% (base_url, api_key, genre_id, get_current_date(), page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_WEEK)

def tmdb_movies_languages(language, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_movies_languages_%s_%s' % (language, page_no)
	url = '%s/discover/movie?api_key=%s&language=en-US&with_original_language=%s&release_date.lte=%s&page=%s' \
			% (base_url, api_key, language, get_current_date(), page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_WEEK)

def tmdb_movies_certifications(certification, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_movies_certifications_%s_%s' % (certification, page_no)
	url = '%s/discover/movie?api_key=%s&language=en-US&region=US&with_original_language=en&certification_country=US&certification=%s&sort_by=%s&release_date.lte=%s&page=%s' \
							% (base_url, api_key, certification, 'popularity.desc', get_current_date(), page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_WEEK)

def tmdb_movies_year(year, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_movies_year_%s_%s' % (year, page_no)
	url = '%s/discover/movie?api_key=%s&language=en-US&region=US&with_original_language=en&certification_country=US&primary_release_year=%s&page=%s' \
							% (base_url, api_key, year, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_WEEK)

def tmdb_movies_decade(decade, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_movies_decade_%s_%s' % (decade, page_no)
	start = '%s-01-01' % decade
	end = get_dates(2)[0] if decade == '2020' else '%s-12-31' % str(int(decade) + 9)
	url = '%s/discover/movie?api_key=%s&language=en-US&region=US&with_original_language=en&primary_release_date.gte=%s' \
			'&primary_release_date.lte=%s&page=%s' % (base_url, api_key, start, end, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_WEEK)

def tmdb_movies_providers(provider, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_movies_providers_%s_%s' % (provider, page_no)
	url = '%s/discover/movie?api_key=%s&watch_region=US&with_watch_providers=%s&vote_count.gte=100&page=%s' % (base_url, api_key, provider, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_WEEK)

def tmdb_movies_recommendations(tmdb_id, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_movies_recommendations_%s_%s' % (tmdb_id, page_no)
	url = '%s/movie/%s/recommendations?api_key=%s&language=en-US&region=US&with_original_language=en&page=%s' % (base_url, tmdb_id, api_key, page_no)
	return lists_cache_object(get_data, string, url)

def tmdb_movies_search(query, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	meta_filter = get_meta_filter()
	string = 'tmdb_movies_search_%s_%s_%s' % (query, meta_filter, page_no)
	url = '%s/search/movie?api_key=%s&language=en-US&include_adult=%s&query=%s&page=%s' % (base_url, api_key, meta_filter, query, page_no)
	return lists_cache_object(get_data, string, url)

def tmdb_movies_companies(company_id, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_movies_companies_%s_%s' % (company_id, page_no)
	url = '%s/discover/movie?api_key=%s&language=en-US&region=US&with_original_language=en&with_companies=%s&page=%s' \
							% (base_url, api_key, company_id, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_WEEK)

def tmdb_movies_reviews(tmdb_id, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	url = '%s/movie/%s/reviews?api_key=%s&page=%s' % (base_url, tmdb_id, api_key, page_no)
	return get_tmdb(url).json()

def tmdb_tv_discover(query, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	if '[current_date]' in query: query = query.replace('[current_date]', get_current_date())
	if '[random]' in query: query = query.replace('[random]', '')
	string = url = query + '&api_key=%s&page=%s' % (api_key, page_no)
	return lists_cache_object(get_tmdb, string, url, True, EXPIRY_1_DAY)

def tmdb_tv_popular(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_tv_popular_%s' % page_no
	url = '%s/tv/popular?api_key=%s&language=en-US&region=US&with_original_language=en&page=%s' % (base_url, api_key, page_no)
	return lists_cache_object(get_data, string, url)

def tmdb_tv_popular_today(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_tv_popular_today_%s' % page_no
	url = '%s/trending/tv/day?api_key=%s&language=en-US&region=US&with_original_language=en&page=%s' % (base_url, api_key, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_DAY)

def tmdb_tv_premieres(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	current_date, previous_date = get_dates(31, reverse=True)
	string = 'tmdb_tv_premieres_%s' % page_no
	url = '%s/discover/tv?api_key=%s&language=en-US&region=US&with_original_language=en&include_null_first_air_dates=false&first_air_date.gte=%s&first_air_date.lte=%s&page=%s' \
							% (base_url, api_key, previous_date, current_date, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_DAY)

def tmdb_tv_airing_today(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_tv_airing_today_%s' % page_no
	url = '%s/tv/airing_today?api_key=%s&language=en-US&region=US&with_original_language=en&page=%s' % (base_url, api_key, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_DAY)

def tmdb_tv_on_the_air(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_tv_on_the_air_%s' % page_no
	url = '%s/tv/on_the_air?api_key=%s&language=en-US&region=US&with_original_language=en&page=%s' % (base_url, api_key, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_DAY)

def tmdb_tv_upcoming(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	current_date, future_date = get_dates(31, reverse=False)
	string = 'tmdb_tv_upcoming_%s' % page_no
	url = '%s/discover/tv?api_key=%s&language=en-US&region=US&with_original_language=en&first_air_date.gte=%s&first_air_date.lte=%s&page=%s' \
							% (base_url, api_key, current_date, future_date, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_DAY)

def tmdb_tv_genres(genre_id, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_tv_genres_%s_%s' % (genre_id, page_no)
	url = '%s/discover/tv?api_key=%s&with_genres=%s&language=en-US&region=US&with_original_language=en&include_null_first_air_dates=false&first_air_date.lte=%s&page=%s' \
							% (base_url, api_key, genre_id, get_current_date(), page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_WEEK)

def tmdb_tv_languages(language, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_tv_languages_%s_%s' % (language, page_no)
	url = '%s/discover/tv?api_key=%s&language=en-US&include_null_first_air_dates=false&with_original_language=%s&first_air_date.lte=%s&page=%s' \
							% (base_url, api_key, language, get_current_date(), page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_WEEK)

def tmdb_tv_networks(network_id, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_tv_networks_%s_%s' % (network_id, page_no)
	url = '%s/discover/tv?api_key=%s&language=en-US&region=US&with_original_language=en&include_null_first_air_dates=false&with_networks=%s&first_air_date.lte=%s&page=%s' \
							% (base_url, api_key, network_id, get_current_date(), page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_WEEK)

def tmdb_tv_providers(provider, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_tv_providers_%s_%s' % (provider, page_no)
	url = '%s/discover/tv?api_key=%s&watch_region=US&with_watch_providers=%s&include_null_first_air_dates=false&vote_count.gte=100&first_air_date.lte=%s&page=%s' \
				% (base_url, api_key, provider, get_current_date(), page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_WEEK)

def tmdb_tv_year(year, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_tv_year_%s_%s' % (year, page_no)
	url = '%s/discover/tv?api_key=%s&language=en-US&region=US&with_original_language=en&include_null_first_air_dates=false&first_air_date_year=%s&page=%s' \
							% (base_url, api_key, year, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_WEEK)

def tmdb_tv_decade(decade, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_tv_decade_%s_%s' % (decade, page_no)
	start = '%s-01-01' % decade
	end = get_dates(2)[0] if decade == '2020' else '%s-12-31' % str(int(decade) + 9)
	url = '%s/discover/tv?api_key=%s&language=en-US&region=US&with_original_language=en&include_null_first_air_dates=false&first_air_date.gte=%s' \
			'&first_air_date.lte=%s&page=%s' % (base_url, api_key, start, end, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_WEEK)

def tmdb_tv_recommendations(tmdb_id, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_tv_recommendations_%s_%s' % (tmdb_id, page_no)
	url = '%s/tv/%s/recommendations?api_key=%s&language=en-US&region=US&with_original_language=en&page=%s' % (base_url, tmdb_id, api_key, page_no)
	return lists_cache_object(get_data, string, url)

def tmdb_tv_search(query, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	meta_filter = get_meta_filter()
	string = 'tmdb_tv_search_%s_%s_%s' % (query, meta_filter, page_no)
	url = '%s/search/tv?api_key=%s&language=en-US&include_adult=%s&query=%s&page=%s' % (base_url, api_key, meta_filter, query, page_no)
	return lists_cache_object(get_data, string, url)

def tmdb_tv_reviews(tmdb_id, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	url = '%s/tv/%s/reviews?api_key=%s&page=%s' % (base_url, tmdb_id, api_key, page_no)
	return get_tmdb(url).json()

def tmdb_anime_popular(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_tv_anime_popular_%s' % page_no
	url = '%s/discover/tv?api_key=%s&with_keywords=210024&page=%s' % (base_url, api_key, page_no)
	return lists_cache_object(get_data, string, url)

def tmdb_anime_popular_recent(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_tv_anime_popular_recent_%s' % page_no
	url = '%s/discover/tv?api_key=%s&with_keywords=210024&sort_by=first_air_date.desc&include_null_first_air_dates=false&first_air_date_year=%s&page=%s' \
							% (base_url, api_key, years_tvshows[0]['id'], page_no)
	return lists_cache_object(get_data, string, url)

def tmdb_anime_premieres(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	current_date, previous_date = get_dates(93, reverse=True)
	string = 'tmdb_anime_premieres_%s' % page_no
	url = '%s/discover/tv?api_key=%s&with_keywords=210024&include_null_first_air_dates=false&first_air_date.gte=%s&first_air_date.lte=%s&page=%s' \
							% (base_url, api_key, previous_date, current_date, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_DAY)

def tmdb_anime_upcoming(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	current_date, future_date = get_dates(93, reverse=False)
	string = 'tmdb_anime_upcoming_%s' % page_no
	url = '%s/discover/tv?api_key=%s&with_keywords=210024&first_air_date.gte=%s&first_air_date.lte=%s&sort_by=first_air_date.asc&page=%s' \
							% (base_url, api_key, current_date, future_date, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_DAY)

def tmdb_anime_on_the_air(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	current_date, future_date = get_dates(7, reverse=False)
	string = 'tmdb_anime_on_the_air_%s' % page_no
	url = '%s/discover/tv?api_key=%s&with_keywords=210024&air_date.gte=%s&air_date.lte=%s&page=%s' \
							% (base_url, api_key, current_date, future_date, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_DAY)

def tmdb_anime_genres(genre_id, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_anime_genres_%s_%s' % (genre_id, page_no)
	url = '%s/discover/tv?api_key=%s&with_keywords=210024&with_genres=%s&include_null_first_air_dates=false&first_air_date.lte=%s&page=%s' \
							% (base_url, api_key, genre_id, get_current_date(), page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_WEEK)

def tmdb_anime_providers(provider, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_anime_providers_%s_%s' % (provider, page_no)
	url = '%s/discover/tv?api_key=%s&with_keywords=210024&watch_region=US&with_watch_providers=%s&include_null_first_air_dates=false&first_air_date.lte=%s&page=%s' \
				% (base_url, api_key, provider, get_current_date(), page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_WEEK)

def tmdb_anime_year(year, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_anime_year_%s_%s' % (year, page_no)
	url = '%s/discover/tv?api_key=%s&with_keywords=210024&include_null_first_air_dates=false&first_air_date_year=%s&page=%s' % (base_url, api_key, year, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_WEEK)

def tmdb_anime_decade(decade, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_anime_decade_%s_%s' % (decade, page_no)
	start = '%s-01-01' % decade
	end = get_dates(2)[0] if decade == '2020' else '%s-12-31' % str(int(decade) + 9)
	url = '%s/discover/tv?api_key=%s&with_keywords=210024&include_null_first_air_dates=false&first_air_date.gte=%s' \
			'&first_air_date.lte=%s&page=%s' % (base_url, api_key, start, end, page_no)
	return lists_cache_object(get_data, string, url, expiration= EXPIRY_1_WEEK)

def tmdb_anime_search(query, page_no):
	def _process(foo):
		data = get_data(url)
		if data['results']:
			threads = list(make_thread_list_enumerate(_anime_checker, data['results']))
			[i.join() for i in threads]
			anime_results.sort(key=lambda k: k[0])
			data['results'] = [i[1] for i in anime_results]
		return data
	def _anime_checker(count, item):
		try: keywords = tmdb_tv_keywords(item['id'])
		except: return
		if any([x['id'] == 210024 for x in keywords['results']]): anime_results_append((count, item))
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	meta_filter = get_meta_filter()
	string = 'tmdb_anime_search_%s_%s_%s' % (query, meta_filter, page_no)
	url = '%s/search/tv?api_key=%s&include_adult=%s&query=%s&page=%s' % (base_url, api_key, meta_filter, query, page_no)
	anime_results = []
	anime_results_append = anime_results.append
	return lists_cache_object(_process, string, url)

def tmdb_popular_people(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_people_popular_%s' % page_no
	url = '%s/person/popular?api_key=%s&language=en&page=%s' % (base_url, api_key, page_no)
	return cache_function(get_tmdb, string, url, EXPIRY_1_DAY)

def tmdb_trending_people_day(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_people_trending_day_%s' % page_no
	url = '%s/trending/person/day?api_key=%s&page=%s' % (base_url, api_key, page_no)
	return cache_function(get_tmdb, string, url, EXPIRY_1_DAY)

def tmdb_trending_people_week(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_people_trending_week_%s' % page_no
	url = '%s/trending/person/week?api_key=%s&page=%s' % (base_url, api_key, page_no)
	return cache_function(get_tmdb, string, url, EXPIRY_1_WEEK)

def tmdb_people_full_info(actor_id):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	string = 'tmdb_people_full_info_%s' % actor_id
	url = '%s/person/%s?api_key=%s&language=en&append_to_response=external_ids,combined_credits,images,tagged_images' % (base_url, actor_id, api_key)
	return cache_function(get_tmdb, string, url, expiration=EXPIRY_1_WEEK)

def tmdb_people_info(query, page_no=1):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	meta_filter = get_meta_filter()
	string = 'tmdb_people_info_%s_%s_%s' % (query, meta_filter, page_no)
	url = '%s/search/person?api_key=%s&language=en&include_adult=%s&query=%s&page=%s' % (base_url, api_key, meta_filter, query, page_no)
	return cache_function(get_tmdb, string, url, expiration=EXPIRY_4_HOURS)

def season_episodes_details(tmdb_id, season_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	try:
		url = '%s/tv/%s/season/%s?api_key=%s&language=en&append_to_response=credits' % (base_url, tmdb_id, season_no, api_key)
		return get_tmdb(url).json()
	except: return None

def get_dates(days, reverse=True):
	current_date = get_current_date(return_str=False)
	if reverse: new_date = (current_date - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
	else: new_date = (current_date + datetime.timedelta(days=days)).strftime('%Y-%m-%d')
	return str(current_date), new_date

def get_current_date(return_str=True):
	if return_str: return str(datetime.date.today())
	else: return datetime.date.today()

def get_reviews_data(media_type, tmdb_id):
	def builder(media_type, tmdb_id):
		reviews_list, all_data = [], []
		template = '[B]%02d. %s%s[/B][CR][CR]%s'
		media_type = 'movie' if media_type in ('movie', 'movies') else 'tv'
		function = tmdb_movies_reviews if media_type  == 'movie' else tmdb_tv_reviews
		next_page, total_pages = 1, 1
		while next_page <= total_pages:
			data = function(tmdb_id, next_page)
			all_data += data['results']
			total_pages = data['total_pages']
			next_page = data['page'] + 1
		if all_data:
			for count, item in enumerate(all_data, 1):
				try:
					user = item['author'].upper()
					rating = item['author_details'].get('rating')
					if rating: rating = ' - %s/10' % str(rating).split('.')[0]
					else: rating = ''
					content = template % (count, user, rating, item['content'])
					reviews_list.append(content)
				except: pass
		return reviews_list
	string, url = 'tmdb_%s_reviews_%s' % (media_type ,tmdb_id), [media_type, tmdb_id]
	return cache_function(builder, string, url, json=False, expiration=EXPIRY_1_WEEK)

def get_data(url):
	data = get_tmdb(url).json()
	data['results'] = [remove_keys(i, tmdb_dict_removals) for i in data['results']]
	return data

def get_tmdb(url):
	try: response = session.get(url, timeout=timeout)
	except: response = None
	return response
