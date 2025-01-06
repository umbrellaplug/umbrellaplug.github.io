# -*- coding: utf-8 -*-
import datetime
from caches.main_cache import cache_object
from caches.meta_cache import cache_function
from modules.settings import tmdb_api_key, get_meta_filter, get_language, generic_list_sorting
from modules.kodi_utils import make_session, tmdb_dict_removals, remove_keys
# from modules.kodi_utils import logger

EXPIRY_4_HOURS, EXPIRY_1_DAY, EXPIRY_2_DAYS, EXPIRY_1_WEEK = 4, 24, 48, 168
base_url = 'https://api.themoviedb.org/3'
movies_append = 'external_ids,videos,credits,release_dates,alternative_titles,translations,images'
tvshows_append = 'external_ids,videos,credits,content_ratings,alternative_titles,translations,images'
timeout = 20.0
session = make_session(base_url)

def tmdb_network_details(network_id):
	string = 'tmdb_network_details_%s' % network_id
	url = '%s/network/%s?api_key=%s' % (base_url, network_id, tmdb_api_key())
	return cache_object(get_tmdb, string, url, expiration=EXPIRY_1_WEEK)

def tmdb_keywords_by_query(query):
	string = 'tmdb_keywords_by_query_%s' % query
	url = '%s/search/keyword?api_key=%s&query=%s' % (base_url, tmdb_api_key(), query)
	return cache_object(get_tmdb, string, url, expiration=EXPIRY_1_WEEK)

def tmdb_movie_keywords(tmdb_id):
	string = 'tmdb_movie_keywords_%s' % tmdb_id
	url = '%s/movie/%s/keywords?api_key=%s' % (base_url, tmdb_id, tmdb_api_key())
	return cache_object(get_tmdb, string, url, expiration=EXPIRY_1_WEEK)

def tmdb_tv_keywords(tmdb_id):
	string = 'tmdb_tv_keywords_%s' % tmdb_id
	url = '%s/tv/%s/keywords?api_key=%s' % (base_url, tmdb_id, tmdb_api_key())
	return cache_object(get_tmdb, string, url, expiration=EXPIRY_1_WEEK)

def tmdb_movie_keyword_results(tmdb_id, page_no):
	string = 'tmdb_movie_keyword_results_%s' % page_no
	url = '%s/discover/movie?api_key=%s&language=en-US&with_keywords=%s&page=%s' % (base_url, tmdb_api_key(), tmdb_id, page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_tv_keyword_results(tmdb_id, page_no):
	string = 'tmdb_tv_keyword_results_%s' % page_no
	url = '%s/discover/tv?api_key=%s&language=en-US&with_keywords=%s&page=%s' % (base_url, tmdb_api_key(), tmdb_id, page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_company_id(query):
	string = 'tmdb_company_id_%s' % query
	url = '%s/search/company?api_key=%s&query=%s' % (base_url, tmdb_api_key(), query)
	return cache_object(get_tmdb, string, url, expiration=EXPIRY_1_WEEK)

def tmdb_media_images(media_type, tmdb_id):
	if media_type == 'movies': media_type = 'movie'
	string = 'tmdb_media_images_%s_%s' % (media_type, tmdb_id)
	url = '%s/%s/%s/images?api_key=%s' % (base_url, media_type, tmdb_id, tmdb_api_key())
	return cache_object(get_tmdb, string, url, expiration=EXPIRY_1_WEEK)

def tmdb_media_videos(media_type, tmdb_id):
	if media_type == 'movies': media_type = 'movie'
	if media_type in ('tvshow', 'tvshows'): media_type = 'tv'
	string = 'tmdb_media_videos_%s_%s' % (media_type, tmdb_id)
	url = '%s/%s/%s/videos?api_key=%s' % (base_url, media_type, tmdb_id, tmdb_api_key())
	return cache_object(get_tmdb, string, url, expiration=EXPIRY_1_WEEK)

def tmdb_movies_discover(query, page_no):
	string = url = query % page_no
	return cache_object(get_tmdb, string, url)

def tmdb_movies_popular(page_no):
	string = 'tmdb_movies_popular_%s' % page_no
	url = '%s/movie/popular?api_key=%s&language=en-US&region=US&with_original_language=en&page=%s' % (base_url, tmdb_api_key(), page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_movies_popular_today(page_no):
	string = 'tmdb_movies_popular_today_%s' % page_no
	url = '%s/trending/movie/day?api_key=%s&language=en-US&region=US&with_original_language=en&page=%s' % (base_url, tmdb_api_key(), page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_1_DAY)

def tmdb_movies_blockbusters(page_no):
	string = 'tmdb_movies_blockbusters_%s' % page_no
	url = '%s/discover/movie?api_key=%s&language=en-US&region=US&with_original_language=en&sort_by=revenue.desc&page=%s' % (base_url, tmdb_api_key(), page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_movies_in_theaters(page_no):
	string = 'tmdb_movies_in_theaters_%s' % page_no
	url = '%s/movie/now_playing?api_key=%s&language=en-US&region=US&with_original_language=en&page=%s' % (base_url, tmdb_api_key(), page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_movies_upcoming(page_no):
	current_date, future_date = get_dates(31, reverse=False)
	string = 'tmdb_movies_upcoming_%s' % page_no
	url = '%s/discover/movie?api_key=%s&language=en-US&region=US&with_original_language=en&release_date.gte=%s&release_date.lte=%s&with_release_type=3|2|1&page=%s' \
							% (base_url, tmdb_api_key(), current_date, future_date, page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_movies_latest_releases(page_no):
	current_date, previous_date = get_dates(31, reverse=True)
	string = 'tmdb_movies_latest_releases_%s' % page_no
	url = '%s/discover/movie?api_key=%s&language=en-US&region=US&with_original_language=en&release_date.gte=%s&release_date.lte=%s&with_release_type=4|5|6&page=%s' \
							% (base_url, tmdb_api_key(), previous_date, current_date, page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_movies_premieres(page_no):
	current_date, previous_date = get_dates(31, reverse=True)
	string = 'tmdb_movies_premieres_%s' % page_no
	url = '%s/discover/movie?api_key=%s&language=en-US&region=US&with_original_language=en&release_date.gte=%s&release_date.lte=%s&with_release_type=1|3|2&page=%s' \
							% (base_url, tmdb_api_key(), previous_date, current_date, page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_movies_genres(genre_id, page_no):
	sort_type = generic_list_sorting('movies.genres')
	string = 'tmdb_movies_genres_%s_%s_%s' % (genre_id, sort_type, page_no)
	url = '%s/discover/movie?api_key=%s&with_genres=%s&language=en-US&region=US&with_original_language=en&sort_by=%s&release_date.lte=%s&page=%s' \
			% (base_url, tmdb_api_key(), genre_id, sort_type, get_current_date(), page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_movies_languages(language, page_no):
	sort_type = generic_list_sorting('movies.languages')
	string = 'tmdb_movies_languages_%s_%s_%s' % (language, sort_type, page_no)
	url = '%s/discover/movie?api_key=%s&language=en-US&with_original_language=%s&sort_by=%s&release_date.lte=%s&page=%s' \
			% (base_url, tmdb_api_key(), language, sort_type, get_current_date(), page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_movies_certifications(certification, page_no):
	sort_type = generic_list_sorting('movies.certifications')
	string = 'tmdb_movies_certifications_%s_%s_%s' % (certification, sort_type, page_no)
	url = '%s/discover/movie?api_key=%s&language=en-US&region=US&with_original_language=en&certification_country=US&certification=%s&sort_by=%s&release_date.lte=%s&page=%s' \
							% (base_url, tmdb_api_key(), certification, sort_type, get_current_date(), page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_movies_year(year, page_no):
	sort_type = generic_list_sorting('movies.years')
	string = 'tmdb_movies_year_%s_%s_%s' % (year, sort_type, page_no)
	url = '%s/discover/movie?api_key=%s&language=en-US&region=US&with_original_language=en&certification_country=US&primary_release_year=%s&sort_by=%s&page=%s' \
							% (base_url, tmdb_api_key(), year, sort_type, page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_movies_decade(decade, page_no):
	sort_type = generic_list_sorting('movies.decades')
	string = 'tmdb_movies_decade_%s_%s_%s' % (decade, sort_type, page_no)
	start = '%s-01-01' % decade
	end = get_dates(2)[0] if decade == '2020' else '%s-12-31' % str(int(decade) + 9)
	url = '%s/discover/movie?api_key=%s&language=en-US&region=US&with_original_language=en&certification_country=US&primary_release_date.gte=%s' \
			'&primary_release_date.lte=%s&sort_by=%s&page=%s' % (base_url, tmdb_api_key(), start, end, sort_type, page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_movies_networks(network, page_no):
	sort_type = generic_list_sorting('movies.networks')
	string = 'tmdb_movies_networks_%s_%s_%s' % (network, sort_type, page_no)
	url = '%s/discover/movie?api_key=%s&watch_region=US&with_watch_providers=%s&sort_by=%s&vote_count.gte=100&page=%s' % (base_url, tmdb_api_key(), network, sort_type, page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_movies_recommendations(tmdb_id, page_no):
	string = 'tmdb_movies_recommendations_%s_%s' % (tmdb_id, page_no)
	url = '%s/movie/%s/recommendations?api_key=%s&language=en-US&region=US&with_original_language=en&page=%s' % (base_url, tmdb_id, tmdb_api_key(), page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_movies_search(query, page_no):
	meta_filter = get_meta_filter()
	if '|' in query:
		query, year = query.split('|')
		string = 'tmdb_movies_search_%s_%s_%s_%s' % (query, year, page_no, meta_filter)
		url = '%s/search/movie?api_key=%s&language=en-US&include_adult=%s&query=%s&year=%s&page=%s' % (base_url, tmdb_api_key(), meta_filter, query, year, page_no)
	else:
		string = 'tmdb_movies_search_%s_%s_%s' % (query, page_no, meta_filter)
		url = '%s/search/movie?api_key=%s&language=en-US&include_adult=%s&query=%s&page=%s' % (base_url, tmdb_api_key(), meta_filter, query, page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_movies_search_sets(query, page_no):
	string = 'tmdb_movies_search_sets_%s_%s' % (query, page_no)
	url = '%s/search/collection?api_key=%s&language=en-US&query=%s&page=%s' % (base_url, tmdb_api_key(), query, page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_1_WEEK)

def tmdb_movies_companies(company_id, page_no):
	string = 'tmdb_movies_companies_%s_%s' % (company_id, page_no)
	url = '%s/discover/movie?api_key=%s&language=en-US&region=US&with_original_language=en&sort_by=popularity.desc&certification_country=US&with_companies=%s&page=%s' \
							% (base_url, tmdb_api_key(), company_id, page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_movies_reviews(tmdb_id, page_no):
	url = '%s/movie/%s/reviews?api_key=%s&page=%s' % (base_url, tmdb_id, tmdb_api_key(), page_no)
	return get_tmdb(url).json()

def tmdb_tv_discover(query, page_no):
	string = url = query % page_no
	return cache_object(get_tmdb, string, url)

def tmdb_tv_popular(page_no):
	string = 'tmdb_tv_popular_%s' % page_no
	url = '%s/tv/popular?api_key=%s&language=en-US&region=US&with_original_language=en&page=%s' % (base_url, tmdb_api_key(), page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_tv_popular_today(page_no):
	string = 'tmdb_tv_popular_today_%s' % page_no
	url = '%s/trending/tv/day?api_key=%s&language=en-US&region=US&with_original_language=en&page=%s' % (base_url, tmdb_api_key(), page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_1_DAY)

def tmdb_tv_premieres(page_no):
	current_date, previous_date = get_dates(31, reverse=True)
	string = 'tmdb_tv_premieres_%s' % page_no
	url = '%s/discover/tv?api_key=%s&language=en-US&region=US&with_original_language=en&sort_by=popularity.desc&include_null_first_air_dates=false&first_air_date.gte=%s' \
			'&first_air_date.lte=%s&page=%s' % (base_url, tmdb_api_key(), previous_date, current_date, page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_tv_airing_today(page_no):
	string = 'tmdb_tv_airing_today_%s' % page_no
	url = '%s/tv/airing_today?api_key=%s&language=en-US&region=US&with_original_language=en&page=%s' % (base_url, tmdb_api_key(), page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_tv_on_the_air(page_no):
	string = 'tmdb_tv_on_the_air_%s' % page_no
	url = '%s/tv/on_the_air?api_key=%s&language=en-US&region=US&with_original_language=en&page=%s' % (base_url, tmdb_api_key(), page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_tv_upcoming(page_no):
	current_date, future_date = get_dates(31, reverse=False)
	string = 'tmdb_tv_upcoming_%s' % page_no
	url = '%s/discover/tv?api_key=%s&language=en-US&region=US&with_original_language=en&sort_by=popularity.desc&include_null_first_air_dates=false&first_air_date.gte=%s' \
	'&first_air_date.lte=%s&page=%s' % (base_url, tmdb_api_key(), current_date, future_date, page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_tv_genres(genre_id, page_no):
	sort_type = generic_list_sorting('tvshows.genres')
	string = 'tmdb_tv_genres_%s_%s_%s' % (genre_id, sort_type, page_no)
	url = '%s/discover/tv?api_key=%s&with_genres=%s&language=en-US&region=US&with_original_language=en&include_null_first_air_dates=false&sort_by=%s&first_air_date.lte=%s&page=%s' \
							% (base_url, tmdb_api_key(), genre_id, sort_type, get_current_date(), page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_tv_languages(language, page_no):
	sort_type = generic_list_sorting('tvshows.languages')
	string = 'tmdb_tv_languages_%s_%s_%s' % (language, sort_type, page_no)
	url = '%s/discover/tv?api_key=%s&language=en-US&include_null_first_air_dates=false&with_original_language=%s&sort_by=%s&include_null_first_air_dates=false&first_air_date.lte=%s' \
			'&page=%s' % (base_url, tmdb_api_key(), language, sort_type, get_current_date(), page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_tv_networks(network_id, page_no):
	sort_type = generic_list_sorting('tvshows.networks')
	string = 'tmdb_tv_networks_%s_%s_%s' % (network_id, sort_type, page_no)
	url = '%s/discover/tv?api_key=%s&language=en-US&region=US&with_original_language=en&include_null_first_air_dates=false&with_networks=%s&sort_by=%s&first_air_date.lte=%s&page=%s' \
							% (base_url, tmdb_api_key(), network_id, sort_type, get_current_date(), page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_tv_year(year, page_no):
	sort_type = generic_list_sorting('tvshows.years')
	string = 'tmdb_tv_year_%s_%s_%s' % (year, sort_type, page_no)
	url = '%s/discover/tv?api_key=%s&language=en-US&region=US&with_original_language=en&include_null_first_air_dates=false&first_air_date_year=%s&sort_by=%s&page=%s' \
							% (base_url, tmdb_api_key(), year, sort_type, page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_tv_decade(decade, page_no):
	sort_type = generic_list_sorting('tvshows.decades')
	string = 'tmdb_tv_decade_%s_%s_%s' % (decade, sort_type, page_no)
	start = '%s-01-01' % decade
	end = get_dates(2)[0] if decade == '2020' else '%s-12-31' % str(int(decade) + 9)
	url = '%s/discover/tv?api_key=%s&language=en-US&region=US&with_original_language=en&include_null_first_air_dates=false&first_air_date.gte=%s' \
			'&first_air_date.lte=%s&sort_by=%s&page=%s' % (base_url, tmdb_api_key(), start, end, sort_type, page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_tv_recommendations(tmdb_id, page_no):
	string = 'tmdb_tv_recommendations_%s_%s' % (tmdb_id, page_no)
	url = '%s/tv/%s/recommendations?api_key=%s&language=en-US&region=US&with_original_language=en&page=%s' % (base_url, tmdb_id, tmdb_api_key(), page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_tv_search(query, page_no):
	meta_filter = get_meta_filter()
	if '|' in query:
		query, year = query.split('|')
		string = 'tmdb_tv_search_%s_%s_%s_%s' % (query, year, page_no, meta_filter)
		url = '%s/search/tv?api_key=%s&language=en-US&include_adult=%s&query=%s&first_air_date_year=%s&page=%s' % (base_url, tmdb_api_key(), meta_filter, query, year, page_no)
	else:
		string = 'tmdb_tv_search_%s_%s_%s' % (query, page_no, meta_filter)
		url = '%s/search/tv?api_key=%s&language=en-US&include_adult=%s&query=%s&page=%s' % (base_url, tmdb_api_key(), meta_filter, query, page_no)
	return cache_object(get_data, string, url, json=False, expiration=EXPIRY_2_DAYS)

def tmdb_tv_reviews(tmdb_id, page_no):
	url = '%s/tv/%s/reviews?api_key=%s&page=%s' % (base_url, tmdb_id, tmdb_api_key(), page_no)
	return get_tmdb(url).json()

def tmdb_popular_people(page_no):
	string = 'tmdb_popular_people_%s' % page_no
	url = '%s/person/popular?api_key=%s&language=en-US&page=%s' % (base_url, tmdb_api_key(), page_no)
	return cache_object(get_tmdb, string, url)

def tmdb_people_full_info(actor_id, language=None):
	if not language: language = get_language()
	string = 'tmdb_people_full_info_%s_%s' % (actor_id, language)
	url = '%s/person/%s?api_key=%s&language=%s&append_to_response=external_ids,combined_credits,images,tagged_images' % (base_url, actor_id, tmdb_api_key(), language)
	return cache_object(get_tmdb, string, url, expiration=EXPIRY_1_WEEK)

def tmdb_people_info(query):
	meta_filter = get_meta_filter()
	string = 'tmdb_people_info_%s_%s' % (query, meta_filter)
	url = '%s/search/person?api_key=%s&language=en-US&include_adult=%s&query=%s' % (base_url, tmdb_api_key(), meta_filter, query)
	return cache_object(get_tmdb, string, url, expiration=EXPIRY_4_HOURS)['results']

def movie_details(tmdb_id, language, tmdb_api=None):
	try:
		url = '%s/movie/%s?api_key=%s&language=%s&append_to_response=%s' % (base_url, tmdb_id, get_tmdb_api(tmdb_api), language, movies_append)
		return get_tmdb(url).json()
	except: return None

def tvshow_details(tmdb_id, language, tmdb_api=None):
	try:
		url = '%s/tv/%s?api_key=%s&language=%s&append_to_response=%s' % (base_url, tmdb_id, get_tmdb_api(tmdb_api), language, tvshows_append)
		return get_tmdb(url).json()
	except: return None

def movie_set_details(collection_id, tmdb_api=None):
	try:
		url = '%s/collection/%s?api_key=%s&language=en-US' % (base_url, collection_id, get_tmdb_api(tmdb_api))
		return get_tmdb(url).json()
	except: return None

def season_episodes_details(tmdb_id, season_no, language, tmdb_api=None):
	try:
		url = '%s/tv/%s/season/%s?api_key=%s&language=%s&append_to_response=credits' % (base_url, tmdb_id, season_no, get_tmdb_api(tmdb_api), language)
		return get_tmdb(url).json()
	except: return None

def movie_external_id(external_source, external_id, tmdb_api=None):
	try:
		string = 'movie_external_id_%s_%s' % (external_source, external_id)
		url = '%s/find/%s?api_key=%s&external_source=%s' % (base_url, external_id, get_tmdb_api(tmdb_api), external_source)
		result = cache_function(get_tmdb, string, url)
		result = result['movie_results']
		if result: return result[0]
		else: return None
	except: return None

def tvshow_external_id(external_source, external_id, tmdb_api=None):
	try:
		string = 'tvshow_external_id_%s_%s' % (external_source, external_id)
		url = '%s/find/%s?api_key=%s&external_source=%s' % (base_url, external_id, get_tmdb_api(tmdb_api), external_source)
		result = cache_function(get_tmdb, string, url)
		result = result['tv_results']
		if result: return result[0]
		else: return None
	except: return None

def english_translation(media_type, tmdb_id, tmdb_api=None):
	try:
		string = 'english_translation_%s_%s' % (media_type, tmdb_id)
		url = '%s/%s/%s/translations?api_key=%s' % (base_url, media_type, tmdb_id, get_tmdb_api(tmdb_api))
		result = cache_function(get_tmdb, string, url)['']
		try: result = result['translations']
		except: result = None
		return result
	except: return None

def get_dates(days, reverse=True):
	current_date = get_current_date(return_str=False)
	if reverse: new_date = (current_date - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
	else: new_date = (current_date + datetime.timedelta(days=days)).strftime('%Y-%m-%d')
	return str(current_date), new_date

def get_current_date(return_str=True):
	if return_str: return str(datetime.date.today())
	else: return datetime.date.today()

def get_data(url):
	data = get_tmdb(url).json()
	data['results'] = [remove_keys(i, tmdb_dict_removals) for i in data['results']]
	return data

def get_reviews_data(media_type, tmdb_id):
	def make_reviews(media_type, tmdb_id):
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
	return cache_object(make_reviews, string, url, json=False, expiration=EXPIRY_1_WEEK)

def get_tmdb_api(tmdb_api=None):
	return tmdb_api or tmdb_api_key()

def get_tmdb(url):
	try: response = session.get(url, timeout=timeout)
	except: response = None
	return response
