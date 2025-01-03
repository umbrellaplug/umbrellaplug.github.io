# -*- coding: utf-8 -*-
from datetime import datetime
from threading import Thread
from apis.trakt_api import trakt_watched_status_mark, trakt_official_status, trakt_progress, trakt_get_hidden_items
from caches.base_cache import connect_database, database, get_timestamp
from caches.main_cache import main_cache, cache_object
from caches.trakt_cache import clear_trakt_collection_watchlist_data
from modules import kodi_utils, settings, metadata
from modules.utils import get_datetime, adjust_premiered_date, sort_for_article, make_thread_list
# logger = kodi_utils.logger

watched_indicators_function, lists_sort_order, date_offset, nextep_method = settings.watched_indicators, settings.lists_sort_order, settings.date_offset, settings.nextep_method
sleep, progressDialogBG, get_video_database_path = kodi_utils.sleep, kodi_utils.progressDialogBG, kodi_utils.get_video_database_path
notification, kodi_refresh, tmdb_api_key, mpaa_region = kodi_utils.notification, kodi_utils.kodi_refresh, settings.tmdb_api_key, settings.mpaa_region
tv_progress_location = settings.tv_progress_location
progress_db_string, indicators_dict = 'fenlight_hidden_progress_items', {0: 'watched_db', 1: 'trakt_db'}
finished_show_check = ('Ended', 'Canceled')

def get_database(watched_indicators=None):
	return connect_database(indicators_dict[watched_indicators or watched_indicators_function()])

# def cache_watched_tvshow_status(function, status_type, watched_indicators=None):
# 	watched_indicators = watched_indicators or watched_indicators_function()
# 	dbcon = get_database(watched_indicators)
# 	cache = dbcon.execute('SELECT media_id, status FROM watched_status WHERE db_type = ?', (status_type,)).fetchone()
# 	if cache is not None:
# 		expiration, result = cache
# 		if int(expiration) > get_timestamp(): return eval(result)
# 		clear_cache_watched_tvshow_status(watched_indicators, (status_type,))
# 	result = function(status_type)
# 	dbcon.execute('INSERT OR REPLACE INTO watched_status VALUES (?, ?, ?)', (status_type, get_timestamp(12), repr(result)))
# 	return result or []

# def clear_cache_watched_tvshow_status(watched_indicators=None, status_types=('watched', 'progress')):
# 	try:
# 		watched_indicators = watched_indicators or watched_indicators_function()
# 		dbcon = get_database()
# 		for status in status_types: dbcon.execute('DELETE FROM watched_status WHERE db_type = ?', (status,))
# 		dbcon.execute('VACUUM')
# 		return True
# 	except: return False

def hide_unhide_progress_items(params):
	action, media_id = params['action'], int(params.get('media_id', '0'))
	current_items = main_cache.get(progress_db_string) or []
	if action == 'hide': current_items.append(media_id)
	else: current_items.remove(media_id)
	main_cache.set(progress_db_string, current_items, 1825)
	return kodi_refresh()

def get_last_played_value(watched_indicators):
	if watched_indicators == 0: return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
	else: return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')

def make_batch_insert(action, media_type, media_id, season, episode, last_played, title):
	if action == 'mark_as_watched': return (media_type, media_id, season, episode, last_played, title)
	else: return (media_type, media_id, season, episode)

def refresh_container(refresh=True):
	if refresh: kodi_refresh()

def active_tvshows_information(status_type):
	def _process(item):
		media_id = item['media_id']
		meta = metadata.tvshow_meta('tmdb_id', media_id, api_key, mpaa_region_value, get_datetime())
		watched_status = get_watched_status_tvshow(watched_info[media_id], meta.get('total_aired_eps'))[0]
		airing_status = meta.get('status', '')
		if status_type == 'watched':
			if watched_status == 1:
				if not include_other and airing_status not in finished_show_check: return
				results_append(item)
		else:
			if watched_status == 0: results_append(item)
			elif include_other and airing_status not in finished_show_check: results_append(item)
	results = []
	results_append = results.append
	watched_indicators = watched_indicators_function()
	watched_info = watched_info_tvshow()
	api_key, mpaa_region_value = tmdb_api_key(), mpaa_region()
	data = [v for k, v in watched_info.items()]
	progress_location = tv_progress_location()
	if status_type == 'watched': include_other = progress_location in (0, 2)
	else: include_other = progress_location in (1, 2)
	threads = list(make_thread_list(_process, data))
	[i.join() for i in threads]
	return results

def watched_info_movie(watched_db=None):
	if not watched_db: watched_db = get_database()
	try:
		watched_info = watched_db.execute('SELECT media_id, title, last_played FROM watched WHERE db_type = ?', ('movie',)).fetchall()
		return dict([(i[0], {'media_id': i[0], 'title': i[1], 'last_played': i[2]}) for i in watched_info])
	except: return {}

def get_watched_status_movie(watched_info, media_id):
	if not watched_info: return 0
	try:
		watched = 1 if media_id in watched_info else 0
		return watched
	except: return 0

def get_bookmarks_movie(watched_db=None):
	if not watched_db: watched_db = get_database()
	try:
		info = watched_db.execute('SELECT media_id, resume_point, curr_time, resume_id FROM progress WHERE db_type = ?', ('movie',)).fetchall()
		info = dict([(i[0], {'media_id': i[0], 'resume_point': i[1], 'curr_time': i[2], 'resume_id': i[3]}) for i in info])
	except: info = {}
	return info

def get_progress_status_movie(progress_info, media_id):
	try: percent = str(round(float(progress_info[media_id]['resume_point'])))
	except: percent = None
	return percent

def watched_info_tvshow(watched_db=None):
	if not watched_db: watched_db = get_database()
	try:
		data = watched_db.execute('SELECT media_id, season, episode, title, MAX(last_played), COUNT(*) AS COUNTER FROM watched WHERE db_type = ? GROUP BY media_id',
								('episode',)).fetchall()
		return dict([(i[0], {'media_id': i[0], 'season': i[1], 'episode': i[2], 'title': i[3], 'last_played': i[4], 'total_played': i[5]}) for i in data])
	except: return {}

def get_watched_status_tvshow(watched_info, aired_eps):
	if not watched_info: return 0, 0, aired_eps
	try:
		watched = min(watched_info['total_played'], aired_eps)
		unwatched = aired_eps - watched
		if watched >= aired_eps: playcount = 1
		else: playcount = 0
		return playcount, watched, unwatched
	except: return 0, 0, aired_eps

def get_progress_status_tvshow(watched, aired_eps):
	try: progress = int((float(watched)/aired_eps)*100) or 1
	except: progress = 1
	return progress

def watched_info_season(media_id, watched_db=None):
	if not watched_db: watched_db = get_database()
	try: watched_info = dict(watched_db.execute('SELECT season, COUNT(*) AS COUNTER FROM watched WHERE db_type = ? AND media_id = ? GROUP BY media_id, season',
							('episode', str(media_id))).fetchall())
	except: watched_info = {}
	return watched_info

def get_watched_status_season(watched_info, aired_eps):
	if not watched_info: return 0, 0, aired_eps
	try:
		watched = min(watched_info, aired_eps)
		unwatched = aired_eps - watched
		if watched >= aired_eps: playcount = 1
		else: playcount = 0
		return playcount, watched, unwatched
	except: return 0, 0, aired_eps

def get_progress_status_season(watched, aired_eps):
	try: progress = int((float(watched)/aired_eps)*100)
	except: progress = 0
	return progress

def watched_info_episode(media_id, watched_db=None):
	if not watched_db: watched_db = get_database()
	try: watched_info = watched_db.execute('SELECT season, episode FROM watched WHERE db_type = ? AND media_id = ?', ('episode', str(media_id))).fetchall()
	except: watched_info = []
	return watched_info

def get_watched_status_episode(watched_info, season_episode):
	if season_episode in watched_info: return 1
	return 0

def get_bookmarks_episode(media_id, season, watched_db=None):
	if not watched_db: watched_db = get_database()
	try:
		info = watched_db.execute('SELECT resume_point, curr_time, resume_id, episode FROM progress WHERE db_type = ? AND media_id = ? AND season = ?',
			('episode', str(media_id), int(season))).fetchall()
		info = dict([(i[3], {'resume_point': i[0], 'curr_time': i[1], 'resume_id': i[2]}) for i in info])
	except: info = {}
	return info

def get_bookmarks_all_episode(media_id, total_seasons, watched_db=None):
	if not watched_db: watched_db = get_database()
	all_seasons_info = {}
	for season in range(1, total_seasons + 1):
		try:
			season_info = get_bookmarks_episode(media_id, season, watched_db)
			all_seasons_info[season] = season_info
		except: pass
	return all_seasons_info

def get_progress_status_episode(progress_info, episode):
	try: percent = str(round(float(progress_info[episode]['resume_point'])))
	except: percent = None
	return percent

def get_progress_status_all_episode(progress_info, season, episode):
	try: percent = str(round(float(progress_info[season][episode]['resume_point'])))
	except: percent = None
	return percent

def clear_local_bookmarks():
	try:
		dbcon = database.connect(get_video_database_path())
		file_ids = dbcon.execute("SELECT idFile FROM files WHERE strFilename LIKE 'plugin.video.fenlight%'").fetchall()
		for i in ('bookmark', 'streamdetails', 'files'): dbcon.executemany("DELETE FROM %s WHERE idFile=?" % i, file_ids)
	except: pass

def erase_bookmark(media_type, media_id, season='', episode='', refresh='false'):
	try:
		watched_indicators = watched_indicators_function()
		watched_db = get_database(watched_indicators)
		if watched_indicators == 1:
			try:
				if media_type == 'episode': resume_id = get_bookmarks_episode(str(media_id), season, watched_db)[int(episode)]['resume_id']
				else: resume_id = get_bookmarks_movie()[str(media_id)]['resume_id']
				sleep(1000)
				trakt_progress('clear_progress', media_type, media_id, 0, season, episode, resume_id)
			except: pass
		watched_db.execute('DELETE FROM progress where db_type = ? and media_id = ? and season = ? and episode = ?', (media_type, media_id, season, episode))
		refresh_container(refresh == 'true')
	except: pass

def batch_erase_bookmark(watched_indicators, insert_list, action):
	try:
		watched_db = get_database(watched_indicators)
		if action == 'mark_as_watched': modified_list = [(i[0], i[1], i[2], i[3]) for i in insert_list]
		else: modified_list = insert_list
		if watched_indicators == 1:
			def _process():
				for i in insert_list:
					try:
						media_id, season, episode = i[1], i[2], i[3]
						resume_id = get_bookmarks_episode(str(media_id), season, watched_db)[int(episode)]['resume_id']
						sleep(1000)
						trakt_progress('clear_progress', i[0], i[1], 0, i[2], i[3], resume_id)
					except: pass
			Thread(target=_process).start()
		watched_db.executemany('DELETE FROM progress where db_type = ? and media_id = ? and season = ? and episode = ?', modified_list)
	except: pass

def set_bookmark(params):
	try:
		media_type, tmdb_id, curr_time, total_time = params.get('media_type'), params.get('tmdb_id'), params.get('curr_time'), params.get('total_time')
		refresh = False if params.get('from_playback', 'false') == 'true' else True
		title, season, episode = params.get('title'), params.get('season'), params.get('episode')
		adjusted_current_time = float(curr_time) - 5
		resume_point = round(adjusted_current_time/float(total_time)*100,1)
		watched_indicators = watched_indicators_function()
		if watched_indicators == 1:
			if trakt_official_status(media_type) == False: return
			else: trakt_progress('set_progress', media_type, tmdb_id, resume_point, season, episode, refresh_trakt=True)
		else:
			erase_bookmark(media_type, tmdb_id, season, episode)
			last_played = get_last_played_value(watched_indicators)
			dbcon = get_database(watched_indicators)
			dbcon.execute('INSERT OR REPLACE INTO progress VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
						(media_type, tmdb_id, season, episode, str(resume_point), str(curr_time), last_played, 0, title))
		refresh_container(refresh)
	except: pass

def mark_movie(params):
	action, media_type = params.get('action'), 'movie'
	refresh, from_playback = params.get('refresh', 'true') == 'true', params.get('from_playback', 'false') == 'true'
	if from_playback: refresh = False
	tmdb_id, title = params.get('tmdb_id'), params.get('title')
	watched_indicators = watched_indicators_function()
	if watched_indicators == 1:
		if from_playback == 'true' and trakt_official_status(media_type) == False: sleep(1000)
		elif not trakt_watched_status_mark(action, 'movies', tmdb_id): return notification('Error')
		clear_trakt_collection_watchlist_data('watchlist', media_type)
	watched_status_mark(watched_indicators, media_type, tmdb_id, action, title=title)
	refresh_container(refresh)

def mark_tvshow(params):
	title, action, tmdb_id = params.get('title', ''), params.get('action'), params.get('tmdb_id')
	try: tvdb_id = int(params.get('tvdb_id', '0'))
	except: tvdb_id = 0
	watched_indicators = watched_indicators_function()
	progress_backround = progressDialogBG()
	progress_backround.create('[B]Please Wait..[/B]', '')
	if watched_indicators == 1:
		if not trakt_watched_status_mark(action, 'shows', tmdb_id, tvdb_id): return notification('Error')
		clear_trakt_collection_watchlist_data('watchlist', 'tvshow')
	current_date = get_datetime()
	insert_list = []
	insert_append = insert_list.append
	meta = metadata.tvshow_meta('tmdb_id', tmdb_id, tmdb_api_key(), mpaa_region(), get_datetime())
	season_data = meta['season_data']
	season_data = [i for i in season_data if i['season_number'] > 0]
	total = len(season_data)
	last_played = get_last_played_value(watched_indicators)
	for count, item in enumerate(season_data, 1):
		season_number = item['season_number']
		ep_data = metadata.episodes_meta(season_number, meta)
		for ep in ep_data:
			season_number = ep['season']
			ep_number = ep['episode']
			display = '%s - S%.2dE%.2d' % (title, int(season_number), int(ep_number))
			progress_backround.update(int(float(count)/float(total)*100), '[B]Please Wait..[/B]', display)
			episode_date, premiered = adjust_premiered_date(ep['premiered'], date_offset())
			if episode_date and current_date < episode_date: continue
			insert_append(make_batch_insert(action, 'episode', tmdb_id, season_number, ep_number, last_played, title))
	batch_watched_status_mark(watched_indicators, insert_list, action)
	progress_backround.close()
	refresh_container()

def mark_season(params):
	season = int(params.get('season'))
	if season == 0: return notification('Failed')
	insert_list = []
	insert_append = insert_list.append
	action, title, tmdb_id = params.get('action'), params.get('title'), params.get('tmdb_id')
	try: tvdb_id = int(params.get('tvdb_id', '0'))
	except: tvdb_id = 0
	watched_indicators = watched_indicators_function()
	heading = '[B]Mark Watched %s[/B]' if action == 'mark_as_watched' else '[B]Mark Unwatched %s[/B]'
	if watched_indicators == 1:
		if not trakt_watched_status_mark(action, 'season', tmdb_id, tvdb_id, season): return notification('Error')
		clear_trakt_collection_watchlist_data('watchlist', 'tvshow')
	progress_backround = progressDialogBG()
	progress_backround.create('[B]Please Wait..[/B]', '')
	current_date = get_datetime()
	meta = metadata.tvshow_meta('tmdb_id', tmdb_id, tmdb_api_key(), mpaa_region(), get_datetime())
	ep_data = metadata.episodes_meta(season, meta)
	last_played = get_last_played_value(watched_indicators)
	for count, item in enumerate(ep_data, 1):
		season_number = item['season']
		ep_number = item['episode']
		display = '%s - S%.2dE%.2d' % (title, season_number, ep_number)
		episode_date, premiered = adjust_premiered_date(item['premiered'], date_offset())
		if episode_date and current_date < episode_date: continue
		progress_backround.update(int(float(count) / float(len(ep_data)) * 100), '[B]Please Wait..[/B]', display)
		insert_append(make_batch_insert(action, 'episode', tmdb_id, season_number, ep_number, last_played, title))
	batch_watched_status_mark(watched_indicators, insert_list, action)
	progress_backround.close()
	refresh_container()

def mark_episode(params):
	season, episode, title = int(params.get('season')), int(params.get('episode')), params.get('title')
	if season == 0: return notification('Failed')
	action, media_type = params.get('action'), 'episode'
	refresh, from_playback = params.get('refresh', 'true') == 'true', params.get('from_playback', 'false') == 'true'
	if from_playback: refresh = False
	tmdb_id = params.get('tmdb_id')
	try: tvdb_id = int(params.get('tvdb_id', '0'))
	except: tvdb_id = 0
	watched_indicators = watched_indicators_function()
	if watched_indicators == 1:
		if from_playback == 'true' and trakt_official_status(media_type) == False: sleep(1000)
		elif not trakt_watched_status_mark(action, media_type, tmdb_id, tvdb_id, season, episode): return notification('Error')
		clear_trakt_collection_watchlist_data('watchlist', 'tvshow')
	watched_status_mark(watched_indicators, media_type, tmdb_id, action, season, episode, title)
	refresh_container(refresh)

def watched_status_mark(watched_indicators, media_type='', media_id='', action='', season='', episode='', title=''):
	try:
		last_played = get_last_played_value(watched_indicators)
		dbcon = get_database(watched_indicators)
		if action == 'mark_as_watched':
			dbcon.execute('INSERT OR REPLACE INTO watched VALUES (?, ?, ?, ?, ?, ?)', (media_type, media_id, season, episode, last_played, title))
		elif action == 'mark_as_unwatched':
			dbcon.execute('DELETE FROM watched WHERE (db_type = ? and media_id = ? and season = ? and episode = ?)', (media_type, media_id, season, episode))
		erase_bookmark(media_type, media_id, season, episode)
		# if media_type == 'episode': clear_cache_watched_tvshow_status()
	except: notification('Error')

def batch_watched_status_mark(watched_indicators, insert_list, action):
	try:
		dbcon = get_database(watched_indicators)
		if action == 'mark_as_watched':
			dbcon.executemany('INSERT OR IGNORE INTO watched VALUES (?, ?, ?, ?, ?, ?)', insert_list)
		elif action == 'mark_as_unwatched':
			dbcon.executemany('DELETE FROM watched WHERE (db_type = ? and media_id = ? and season = ? and episode = ?)', insert_list)
		batch_erase_bookmark(watched_indicators, insert_list, action)
		# clear_cache_watched_tvshow_status()
	except: notification('Error')

def get_next_episodes(nextep_content):
	watched_db = get_database()
	if nextep_content == 0:
		data = watched_db.execute('''WITH cte AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY media_id ORDER BY season DESC, episode DESC) rn FROM watched WHERE db_type == ?)
									SELECT media_id, season, episode, title, last_played FROM cte WHERE rn = 1''', ('episode',)).fetchall()
	else:
		data = watched_db.execute('SELECT media_id, season, episode, title, MAX(last_played), COUNT(*) AS COUNTER FROM watched WHERE db_type = ? GROUP BY media_id',
								('episode',)).fetchall()
	data = [{'media_ids': {'tmdb': int(i[0])}, 'season': int(i[1]), 'episode': int(i[2]), 'title': i[3], 'last_played': i[4]} for i in data]
	data.sort(key=lambda x: (x['last_played']), reverse=True)
	return data
	
def get_next(season, episode, watched_info, season_data, nextep_content):
	if episode == 0: episode = 1
	elif nextep_content == 0:
		try:
			episode_count = next((i['episode_count'] for i in season_data if i['season_number'] == season), None)
			season = season if episode < episode_count else season + 1
			episode = episode + 1 if episode < episode_count else 1
		except: pass
	else:
		try:
			next_episode = 0
			relevant_seasons = [i for i in season_data if i['season_number'] >= season]
			for item in relevant_seasons:
				episode_count, item_season = item['episode_count'], item['season_number']
				if season == item_season:
					if episode >= episode_count:
						item_season, next_episode = None, None
						continue
					episode_range = range(episode + 1, episode_count + 1)
				else: episode_range = range(1, episode_count + 1)
				next_episode = next((i for i in episode_range if not get_watched_status_episode(watched_info, (item_season, i))), None)
				if next_episode: break
			if not next_episode: season, episode = None, None
			season, episode = item_season, next_episode
		except: pass
	return season, episode

def get_in_progress_movies(dummy_arg, page_no):
	dbcon = get_database()
	data = dbcon.execute('SELECT media_id, title, last_played FROM progress WHERE db_type = ?', ('movie',)).fetchall()
	data = [{'media_id': i[0], 'title': i[1], 'last_played': i[2]} for i in data if not i[0] == '']
	if lists_sort_order('progress') == 0: data = sort_for_article(data, 'title')
	else: data = sorted(data, key=lambda x: x['last_played'], reverse=True)
	return data

def get_in_progress_tvshows(dummy_arg, page_no):
	# results = cache_watched_tvshow_status(active_tvshows_information, 'progress')
	results = active_tvshows_information('progress')
	hidden_items = get_hidden_progress_items(watched_indicators_function())
	results = [i for i in results if not int(i['media_id']) in hidden_items]
	if lists_sort_order('progress') == 0: results = sort_for_article(results, 'title')
	else: results = sorted(results, key=lambda x: x['last_played'], reverse=True)
	return results

def get_in_progress_episodes():
	dbcon = get_database()
	data = dbcon.execute('SELECT media_id, season, episode, resume_point, last_played, title FROM progress WHERE db_type = ?', ('episode',)).fetchall()
	if lists_sort_order('progress') == 0: data = sort_for_article(data, 5)
	else: data.sort(key=lambda k: k[4], reverse=True)
	episode_list = [{'media_ids': {'tmdb': i[0]}, 'season': int(i[1]), 'episode': int(i[2]), 'resume_point': float(i[3])} for i in data]
	return episode_list

def get_watched_items(media_type, page_no):
	if media_type == 'tvshow': results = active_tvshows_information('watched')
	else: results = [v for k,v in watched_info_movie().items()]
	if lists_sort_order('watched') == 0: results = sort_for_article(results, 'title')
	else: results = sorted(results, key=lambda x: x['last_played'], reverse=True)
	return results

def get_recently_watched(media_type, short_list=1):
	watched_indicators = watched_indicators_function()
	if media_type == 'movie':
		data = sorted([v for k,v in watched_info_movie().items()], key=lambda x: x['last_played'], reverse=True)
		if short_list: data = data[:20]
	else:
		dbcon = get_database(watched_indicators)
		if short_list:
			data = dbcon.execute('SELECT media_id, season, episode, title, last_played FROM watched WHERE db_type = ? ORDER BY last_played DESC', ('episode',)).fetchall()
			data = [{'media_ids': {'tmdb': int(i[0])}, 'season': int(i[1]), 'episode': int(i[2]), 'title': i[3], 'last_played': i[4]}
						for i in data][:20]
		else:
			seen = set()
			seen_add = seen.add
			data = dbcon.execute('SELECT media_id, season, episode, title, last_played FROM watched WHERE db_type = ?', ('episode',)).fetchall()
			data = sorted([{'media_ids': {'tmdb': int(i[0])}, 'season': int(i[1]), 'episode': int(i[2]), 'title': i[3], 'last_played': i[4]}
						for i in sorted(data, key=lambda x: (x[4], x[0], x[1], x[2]), reverse=True) if not (i[0] in seen or seen_add(i[0]))],
						key=lambda x: (x['last_played'], x['media_ids']['tmdb'], x['season'], x['episode']), reverse=True)
	return data

def get_hidden_progress_items(watched_indicators):
	try:
		if watched_indicators == 0: return main_cache.get(progress_db_string) or []
		else: return trakt_get_hidden_items('progress_watched')
	except: return []
