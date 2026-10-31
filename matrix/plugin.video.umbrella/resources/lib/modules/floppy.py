# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""
# Floppy (self-hosted media tracker). Built against the dannyvfilms/Floppy
# fork's /api/v1/ 
# OAuth device authorization with API-key compatibility.

from datetime import datetime
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urljoin
from json import dumps as jsdumps
from resources.lib.database import floppysync
from resources.lib.modules import control
from resources.lib.modules import log_utils

getLS = control.lang
getSetting = control.setting
setSetting = control.setSetting

headers = {'Content-Type': 'application/json'}
session = requests.Session()
retries = Retry(total=4, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 524, 530])
session.mount('https://', HTTPAdapter(max_retries=retries, pool_maxsize=100))
session.mount('http://', HTTPAdapter(max_retries=retries, pool_maxsize=100))

floppy_icon = control.joinPath(control.artPath(), 'floppy.png')
_last_request_time = 0.0

# Status codes (MEDIA_STATUS_MAP in Floppy's api/helpers.py)
STATUS_PLANNING = 0
STATUS_WATCHING = 1
STATUS_ONHOLD = 2
STATUS_COMPLETED = 3
STATUS_DROPPED = 4


def floppyBaseUrl():
	url = getSetting('floppy.baseurl').strip()
	if url and not url.startswith(('http://', 'https://')): url = 'https://' + url
	url = url.rstrip('/')
	if url and not url.endswith('/api/v1'): url = url + '/api/v1'
	return url


def getFloppyCredentialsInfo():
	return bool(floppyBaseUrl() and getSetting('floppy.token'))


def getFloppyIndicatorsInfo():
	return getSetting('indicators.alt') == '5'


def isReadOnly():
	"""True when another add-on owns automatic Floppy playback reporting."""
	return getSetting('floppy.readonly') == 'true'


#### Core request plumbing (mirrors customtrakt.py's getCustom, minus the reauth loop) ####

def getFloppy(url, post=None, method=None, silent=False):
	# Returns the raw requests.Response (even for 404/4xx so callers can branch on
	# status_code, e.g. PATCH-then-POST-fallback for untracked items), or None on a
	# hard failure (no base url configured, or an unrecoverable connection error).
	try:
		global _last_request_time
		base = floppyBaseUrl()
		if not base: return None
		if time.time() - _last_request_time > 300:
			session.close()
		if not url.startswith(base): url = urljoin(base + '/', url.lstrip('/'))
		from resources.lib.modules import floppyauth
		identity = floppyauth.identity()
		token = floppyauth.access_token(base, session, expected_identity=identity)
		if not token: return None
		req_headers = dict(headers)
		req_headers['Authorization'] = 'Bearer %s' % token
		body = jsdumps(post) if post is not None else None
		if not method: method = 'POST' if post is not None else 'GET'
		method = method.upper()
		for _attempt in range(2):
			try:
				if method == 'POST':
					response = session.post(url, data=body, headers=req_headers, timeout=20)
				elif method == 'PATCH':
					response = session.patch(url, data=body, headers=req_headers, timeout=20)
				elif method == 'PUT':
					response = session.put(url, data=body, headers=req_headers, timeout=20)
				elif method == 'DELETE':
					response = session.delete(url, headers=req_headers, timeout=20)
				else:
					response = session.get(url, headers=req_headers, timeout=(10, 60))
				_last_request_time = time.time()
				break
			except requests.exceptions.ConnectionError:
				if _attempt == 0:
					log_utils.log('FLOPPY: connection reset, retrying with fresh connection...', level=log_utils.LOGDEBUG)
					session.close()
				else:
					raise
		if response.status_code == 401:
			new_token = floppyauth.access_token(base, session, failed_token=token, expected_identity=identity)
			if new_token and new_token != token:
				req_headers['Authorization'] = 'Bearer %s' % new_token
				response = session.request(method, url, data=body, headers=req_headers, timeout=(10, 60))
		status_code = response.status_code
		if status_code == 401 and not silent:
			log_utils.log_force('FLOPPY: request unauthorized (invalid/expired token) url=%s' % url, level=log_utils.LOGWARNING)
		elif status_code >= 500 and not silent:
			log_utils.log('FLOPPY: temporary server problem: %s url=%s' % (status_code, url), level=log_utils.LOGINFO)
		return response
	except Exception as e:
		if not silent: log_utils.log_force('FLOPPY: getFloppy exception url=%s error=%s' % (url, e), level=log_utils.LOGWARNING)
		return None


def getFloppyAsJson(url, post=None, method=None, silent=False):
	try:
		response = getFloppy(url, post=post, method=method, silent=silent)
		if response is None or response.status_code not in (200, 201): return None
		return response.json()
	except Exception as e:
		if not silent: log_utils.log('FLOPPY: Error in getFloppyAsJson: %s' % str(e), level=log_utils.LOGWARNING)
		return None


def _compact_tracking_entry(entry):
	"""Retain sync fields, without accumulating catalog metadata across pages."""
	fields = ('id', 'tracked', 'status', 'end_date', 'progressed_at', 'created_at', 'created', 'score', 'collected_at')
	item_fields = ('id', 'media_id', 'source', 'ids', 'title', 'release_datetime', 'season_number', 'episode_number', 'image')
	result = {key: entry[key] for key in fields if key in entry}
	item = entry.get('item')
	if isinstance(item, dict): result['item'] = {key: item[key] for key in item_fields if key in item}
	return result


def get_all_pages(url, silent=False, compact=False):
	"""Return a complete collection, or None; never publish a partial page set."""
	try:
		sep = '&' if '?' in url else '?'
		limit, offset = 200, 0
		results = []
		while True:
			if control.monitor.abortRequested(): return None
			data = getFloppyAsJson(url + sep + 'limit=%d&offset=%d' % (limit, offset), silent=silent)
			if data is None: return None
			if isinstance(data, list):
				page_results, pagination = data, None
			elif isinstance(data, dict) and isinstance(data.get('results'), list):
				page_results, pagination = data['results'], data.get('pagination')
			else: return None
			if pagination is not None and not isinstance(pagination, dict): return None
			page_count = len(page_results)
			results.extend((_compact_tracking_entry(entry) for entry in page_results) if compact else page_results)
			# Release the raw page before requesting/decoding the next one.
			data = page_results = None
			if pagination is not None:
				if not pagination.get('next'):
					if pagination.get('total') is not None and len(results) != int(pagination['total']): return None
					return results
			elif page_count < limit:
				return results
			if not page_count: return None
			offset += page_count
			if offset > 100000: return None
	except Exception:
		log_utils.error()
		return None


#### OAuth device authorization and legacy API-key validation ####

def floppyAuth(fromSettings=0, useOAuth=True):
	try:
		if fromSettings == 1: control.make_settings_dict()
		if useOAuth:
			from resources.lib.modules import floppyauth
			if not floppyBaseUrl():
				control.notification(message='Enter a Floppy server URL first', icon=floppy_icon)
				return False
			if not floppyauth.authorize(floppyBaseUrl(), session): return False
		else:
			if not getFloppyCredentialsInfo():
				control.notification(message='Enter a Floppy server URL and token first', icon=floppy_icon)
				return False
			response = getFloppy('/media/movie/?limit=1', method='GET', silent=True)
			if response is None or response.status_code != 200:
				control.notification(message='Floppy Authorization Error - Check URL/Token', icon=floppy_icon)
				return False
			payload = response.json()
			if not isinstance(payload, dict) or not isinstance(payload.get('results'), list):
				control.notification(message='Floppy Authorization Error - Invalid API response', icon=floppy_icon)
				return False
		setSetting('floppy.isauthed', 'true')
		control.notification(message='Floppy Authorized Successfully', icon=floppy_icon)
		if control.yesnoDialog('Do you want to set Floppy as your service for your watched and unwatched indicators?', '', '', 'Indicators', 'No', 'Yes'):
			control.homeWindow.setProperty('umbrella.updateSettings', 'false')
			try:
				setSetting('indicators.alt', '5')
				setSetting('scrobble.source', '5')
				setSetting('scrobble', 'Floppy')
				setSetting('indicators', 'Floppy')
			finally:
				control.homeWindow.setProperty('umbrella.updateSettings', 'true')
		# The long-lived service owns this work; a settings plugin must not spawn it.
		control.make_settings_dict()
		control.homeWindow.setProperty('umbrella.floppy.syncRequested', 'true')
		return True
	except Exception as error:
		from resources.lib.modules.floppyauth import AuthError
		if isinstance(error, AuthError):
			control.notification(title='Floppy', message=str(error), icon=floppy_icon)
		else:
			log_utils.log('FLOPPY: authorization failed (%s)' % type(error).__name__, level=log_utils.LOGWARNING)
			control.notification(title='Floppy', message='Unable to authorize Floppy. Please check the server connection.', icon=floppy_icon)
		return False
	finally:
		if fromSettings == 1: control.openSettings('5.6', 'plugin.video.umbrella')


def floppyRevoke(fromSettings=0):
	try:
		from resources.lib.modules import floppyauth
		floppyauth.disconnect(session)
	except Exception:
		control.notification(title='Floppy', message='Could not revoke the Floppy connection. Please check the server and try again.', icon=floppy_icon)
		if fromSettings == 1: control.openSettings('5.6', 'plugin.video.umbrella')
		return False
	control.homeWindow.setProperty('umbrella.updateSettings', 'false')
	setSetting('floppy.user.name', '')
	setSetting('floppy.token', '')
	setSetting('floppy.isauthed', '')
	control.make_settings_dict()
	control.homeWindow.clearProperty('umbrella.floppy.syncRequested')
	control.homeWindow.setProperty('umbrella.updateSettings', 'true')
	try:
		clr_tables = ('bookmarks', 'floppy_watched_movies', 'floppy_watched_episodes',
			'movies_plantowatch', 'shows_plantowatch', 'movies_watching', 'shows_watching',
			'movies_hold', 'shows_hold', 'movies_completed', 'shows_completed',
			'movies_dropped', 'shows_dropped', 'movies_collection', 'shows_collection')
		floppysync.delete_floppy_tables(clr_tables)
		if getSetting('indicators.alt') == '5':
			setSetting('indicators.alt', '0')
			setSetting('indicators', 'Local')
		if getSetting('scrobble.source') == '5':
			setSetting('scrobble.source', '0')
			setSetting('scrobble', 'Local')
		setSetting('floppy.markwatched', 'false')
		if fromSettings == 1:
			control.openSettings('5.6', 'plugin.video.umbrella')
			control.dialog.ok('Floppy', 'Floppy Authorization Revoked')
	except:
		log_utils.error()


#### TMDb id resolution (Floppy is TMDB-native; Umbrella calls into these with imdb/tvdb) ####

def _resolve_tmdb(media_type, imdb='', tvdb=''):
	try:
		if not imdb and not tvdb: return ''
		from resources.lib.database import cache as _cache
		from resources.lib.indexers import tmdb as _tmdb
		if media_type == 'movie':
			result = _cache.get(_tmdb.Movies().IdLookup, 96, imdb) if imdb else None
		else:
			result = _cache.get(_tmdb.TVshows().IdLookup, 96, imdb, tvdb)
		return str(result.get('id', '')) if result else ''
	except:
		log_utils.error()
		return ''


def _now_iso():
	return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')


#### URL helpers ####

def _movie_url(tmdb): return '/media/movie/tmdb/%s/' % tmdb
def _tv_url(tmdb): return '/media/tv/tmdb/%s/' % tmdb
def _season_url(tmdb, season): return '/media/tv/tmdb/%s/%s/' % (tmdb, season)
def _episode_url(tmdb, season, episode): return '/media/tv/tmdb/%s/%s/%s/' % (tmdb, season, episode)
def _episode_watch_url(tmdb, season, episode): return '/media/tv/tmdb/%s/%s/episodes/%s/watch/' % (tmdb, season, episode)
def _episode_drop_url(tmdb, season, episode): return '/media/tv/tmdb/%s/%s/episodes/%s/drop/' % (tmdb, season, episode)


def _patch_or_create(detail_url, media_type, tmdb, body, season_number=None):
	# Try PATCH on the already-tracked item first; if it isn't tracked yet (404),
	# fall back to POST to create it. Returns True on success.
	response = getFloppy(detail_url, post=body, method='PATCH', silent=True)
	if response is not None and response.status_code == 200: return True
	if response is None or response.status_code != 404: return False
	create_body = dict(body)
	create_body['source'] = 'tmdb'
	create_body['media_id'] = str(tmdb)
	if season_number is not None: create_body['season_number'] = int(season_number)
	response = getFloppy('/media/%s/' % media_type, post=create_body, method='POST', silent=True)
	return bool(response is not None and response.status_code in (200, 201))


#### Watch/unwatch + mark watched ####

def markMovieAsWatched(imdb, tmdb=''):
	try:
		if not tmdb: tmdb = _resolve_tmdb('movie', imdb=imdb)
		if not tmdb:
			log_utils.log('FLOPPY: markMovieAsWatched IMDB=%s aborted â€” could not resolve a tmdb id' % imdb, level=log_utils.LOGWARNING)
			return False
		success = _patch_or_create(_movie_url(tmdb), 'movie', tmdb, {'status': STATUS_COMPLETED})
		if success:
			floppysync.upsert_watched_movie(imdb=imdb or '', tmdb=str(tmdb), last_watched_at=_now_iso())
			floppysync.cache_delete(floppysync._hash_function(syncMovies, ()))
		if getSetting('debug.level') == '1':
			log_utils.log('FLOPPY: markMovieAsWatched IMDB=%s TMDB=%s Result=%s' % (imdb, tmdb, success), level=log_utils.LOGDEBUG)
		return success
	except:
		log_utils.error()
		return False

def markMovieAsNotWatched(imdb, tmdb=''):
	try:
		if not tmdb: tmdb = _resolve_tmdb('movie', imdb=imdb)
		if not tmdb:
			log_utils.log('FLOPPY: markMovieAsNotWatched IMDB=%s aborted â€” could not resolve a tmdb id' % imdb, level=log_utils.LOGWARNING)
			return False
		# PATCH back to Planning rather than DELETE, so score/notes/dates the user
		# set aren't destroyed by an unwatch action.
		response = getFloppy(_movie_url(tmdb), post={'status': STATUS_PLANNING}, method='PATCH', silent=True)
		success = bool(response is not None and response.status_code == 200)
		if success:
			floppysync.delete_watched_movie(tmdb)
			floppysync.cache_delete(floppysync._hash_function(syncMovies, ()))
		if getSetting('debug.level') == '1':
			log_utils.log('FLOPPY: markMovieAsNotWatched IMDB=%s TMDB=%s Result=%s' % (imdb, tmdb, success), level=log_utils.LOGDEBUG)
		return success
	except:
		log_utils.error()
		return False

def markTVShowAsWatched(imdb, tvdb):
	try:
		tmdb = _resolve_tmdb('tv', imdb=imdb, tvdb=tvdb)
		if not tmdb: return False
		success = _patch_or_create(_tv_url(tmdb), 'tv', tmdb, {'status': STATUS_COMPLETED})
		if success:
			rows = _sync_episode_tracking_for_show(imdb, tmdb)
			if rows is None: return False
			if not floppysync.store_watched_history([], rows, replace=False): return False
			floppysync.cache_delete(floppysync._hash_function(syncTVShows, ()))
			floppysync.cache_delete(floppysync._hash_function(_fetchShowProgress, (tmdb,)))
		return success
	except:
		log_utils.error()
		return False

def markTVShowAsNotWatched(imdb, tvdb):
	try:
		tmdb = _resolve_tmdb('tv', imdb=imdb, tvdb=tvdb)
		if not tmdb: return False
		response = getFloppy(_tv_url(tmdb), post={'status': STATUS_PLANNING}, method='PATCH', silent=True)
		success = bool(response is not None and response.status_code == 200)
		if success:
			# Planning does not remove stored episode watches. Retain local
			# watched flags when the corresponding remote delete fails.
			for (si, st, sv, s, e) in floppysync.get_watched_episodes():
				if st == tmdb:
					response = getFloppy(_episode_url(tmdb, int(s), int(e)), method='DELETE', silent=True)
					if response is None or response.status_code not in (200, 204, 404):
						success = False
						continue
					floppysync.delete_watched_episode(st, s, e)
			floppysync.cache_delete(floppysync._hash_function(syncTVShows, ()))
			floppysync.cache_delete(floppysync._hash_function(_fetchShowProgress, (tmdb,)))
		return success
	except:
		log_utils.error()
		return False

def markSeasonAsWatched(imdb, tvdb, season, tmdb=''):
	try:
		tmdb = str(tmdb) if tmdb else _resolve_tmdb('tv', imdb=imdb, tvdb=tvdb)
		if not tmdb: return False
		season = int('%01d' % int(season))
		success = _patch_or_create(_season_url(tmdb, season), 'season', tmdb, {'status': STATUS_COMPLETED}, season_number=season)
		if success:
			rows = _sync_episode_tracking_for_show(imdb, tmdb)
			if rows is None: return False
			if not floppysync.store_watched_history([], rows, replace=False): return False
			floppysync.cache_delete(floppysync._hash_function(syncTVShows, ()))
			floppysync.cache_delete(floppysync._hash_function(_fetchShowProgress, (tmdb,)))
		return success
	except:
		log_utils.error()
		return False

def markSeasonAsNotWatched(imdb, tvdb, season, tmdb=''):
	try:
		tmdb = str(tmdb) if tmdb else _resolve_tmdb('tv', imdb=imdb, tvdb=tvdb)
		if not tmdb: return False
		season = int('%01d' % int(season))
		response = getFloppy(_season_url(tmdb, season), post={'status': STATUS_PLANNING}, method='PATCH', silent=True)
		success = bool(response is not None and response.status_code == 200)
		if success:
			for (si, st, sv, s, e) in floppysync.get_watched_episodes():
				if st == tmdb and int(s) == season:
					response = getFloppy(_episode_url(tmdb, int(s), int(e)), method='DELETE', silent=True)
					if response is None or response.status_code not in (200, 204, 404):
						success = False
						continue
					floppysync.delete_watched_episode(st, s, e)
			floppysync.cache_delete(floppysync._hash_function(syncTVShows, ()))
			floppysync.cache_delete(floppysync._hash_function(_fetchShowProgress, (tmdb,)))
		return success
	except:
		log_utils.error()
		return False

def markEpisodeAsWatched(imdb, tvdb, season, episode, tmdb=''):
	try:
		tmdb = str(tmdb) if tmdb else _resolve_tmdb('tv', imdb=imdb, tvdb=tvdb)
		if not tmdb: return False
		season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
		response = getFloppy(_episode_watch_url(tmdb, season, episode), post={}, method='POST', silent=True)
		success = bool(response is not None and response.status_code in (200, 201))
		if success:
			floppysync.upsert_watched_episode(show_imdb=imdb or '', show_tmdb=tmdb, show_tvdb=str(tvdb or ''), season=season, episode=episode, last_watched_at=_now_iso())
			floppysync.cache_delete(floppysync._hash_function(syncTVShows, ()))
			floppysync.cache_delete(floppysync._hash_function(_fetchShowProgress, (tmdb,)))
		if getSetting('debug.level') == '1':
			log_utils.log('FLOPPY: markEpisodeAsWatched IMDB=%s TMDB=%s S%02dE%02d Result=%s HTTP=%s' % (imdb, tmdb, season, episode, success, response.status_code if response is not None else 'None'), level=log_utils.LOGDEBUG)
		return success
	except:
		log_utils.error()
		return False

def markEpisodeAsNotWatched(imdb, tvdb, season, episode, tmdb=''):
	try:
		tmdb = str(tmdb) if tmdb else _resolve_tmdb('tv', imdb=imdb, tvdb=tvdb)
		if not tmdb: return False
		season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
		response = getFloppy(_episode_url(tmdb, season, episode), method='DELETE', silent=True)
		success = bool(response is not None and response.status_code in (200, 204))
		if success:
			floppysync.delete_watched_episode(tmdb, season, episode)
			floppysync.cache_delete(floppysync._hash_function(syncTVShows, ()))
			floppysync.cache_delete(floppysync._hash_function(_fetchShowProgress, (tmdb,)))
		if getSetting('debug.level') == '1':
			log_utils.log('FLOPPY: markEpisodeAsNotWatched IMDB=%s TMDB=%s S%02dE%02d Result=%s HTTP=%s' % (imdb, tmdb, season, episode, success, response.status_code if response is not None else 'None'), level=log_utils.LOGDEBUG)
		return success
	except:
		log_utils.error()
		return False


def watch(content_type, name, imdb=None, tvdb=None, season=None, episode=None, refresh=True, tmdb=''):
	if content_type != 'movie' and tmdb:
		from resources.lib.modules import episode_mapping, anthology_tracking
		if episode_mapping.supported(tmdb):
			return anthology_tracking.manager_write('floppy', tmdb, season, episode, False, refresh)
	control.busy()
	success = False
	if content_type == 'movie': success = markMovieAsWatched(imdb, tmdb=tmdb)
	elif content_type == 'tvshow': success = markTVShowAsWatched(imdb, tvdb)
	elif content_type == 'season': success = markSeasonAsWatched(imdb, tvdb, season, tmdb=tmdb)
	elif content_type == 'episode': success = markEpisodeAsWatched(imdb, tvdb, season, episode, tmdb=tmdb)
	control.hide()
	if refresh: control.refresh()
	control.trigger_widget_refresh()
	if season and not episode: name = '%s-Season%s...' % (name, season)
	if season and episode: name = '%s-S%sxE%02d...' % (name, season, int(episode))
	if getSetting('services.general.notifications') == 'true':
		if success is True: control.notification(title='Floppy', message='%s Marked as Watched on Floppy' % name)
		else: control.notification(title='Floppy', message='%s Failed to Mark as Watched on Floppy' % name)

def unwatch(content_type, name, imdb=None, tvdb=None, season=None, episode=None, refresh=True, tmdb=''):
	if content_type != 'movie' and tmdb:
		from resources.lib.modules import episode_mapping, anthology_tracking
		if episode_mapping.supported(tmdb):
			return anthology_tracking.manager_write('floppy', tmdb, season, episode, True, refresh)
	control.busy()
	success = False
	if content_type == 'movie': success = markMovieAsNotWatched(imdb, tmdb=tmdb)
	elif content_type == 'tvshow': success = markTVShowAsNotWatched(imdb, tvdb)
	elif content_type == 'season': success = markSeasonAsNotWatched(imdb, tvdb, season, tmdb=tmdb)
	elif content_type == 'episode': success = markEpisodeAsNotWatched(imdb, tvdb, season, episode, tmdb=tmdb)
	control.hide()
	if refresh: control.refresh()
	control.trigger_widget_refresh()
	if season and not episode: name = '%s-Season%s...' % (name, season)
	if season and episode: name = '%s-S%sxE%02d...' % (name, season, int(episode))
	if getSetting('services.general.notifications') == 'true':
		if success is True: control.notification(title='Floppy', message='%s Marked as Unwatched on Floppy' % name)
		else: control.notification(title='Floppy', message='%s Failed to Mark as Unwatched on Floppy' % name)


#### Scrobble: live playback reports; saved resume points sync via /playback/progress/. ####


def _scrobble_seconds(watched_percent, current_time, total_time):
	# position_seconds/duration_seconds are meant to be real elapsed/total playback
	# seconds â€” every call site now has Kodi's actual getTime()/getTotalTime() available
	# and passes them through. Without them (current_time/total_time not provided), this
	# used to send the 0-100 percent value itself as "seconds" with a hardcoded 100-second
	# "duration" â€” Floppy's own Now Playing card then displayed e.g. 38 seconds of a
	# 1:40 (100s) runtime for what was really 38% into a much longer episode. The percent
	# fallback below only exists for any caller that still can't supply real seconds.
	if total_time:
		return int(current_time or 0), int(total_time)
	return int(watched_percent), 100

def scrobbleStart(media_type, title='', tvshowtitle='', year='0', imdb='', tmdb='', tvdb='', season='', episode='', watched_percent=0, current_time=0, total_time=0):
	if tmdb and media_type != 'movie':
		from resources.lib.modules.episode_mapping import supported
		if supported(tmdb): imdb, tvdb = '', ''
	if isReadOnly(): return
	try:
		ids = {}
		if tmdb: ids['tmdb'] = str(tmdb)
		if imdb: ids['imdb'] = str(imdb)
		if tvdb: ids['tvdb'] = str(tvdb)
		position_seconds, duration_seconds = _scrobble_seconds(watched_percent, current_time, total_time)
		body = {'action': 'start', 'media_type': 'movie' if media_type == 'movie' else 'episode', 'ids': ids,
			'title': title, 'series_title': tvshowtitle,
			'season_number': int(season) if season else None, 'episode_number': int(episode) if episode else None,
			'position_seconds': position_seconds, 'duration_seconds': duration_seconds}
		getFloppy('/scrobble/', post=body, method='POST', silent=True)
	except: log_utils.error()

def scrobbleMovie(imdb, tmdb, watched_percent, current_time=0, total_time=0):
	if isReadOnly(): return
	try:
		ids = {}
		if tmdb: ids['tmdb'] = str(tmdb)
		if imdb: ids['imdb'] = str(imdb)
		position_seconds, duration_seconds = _scrobble_seconds(watched_percent, current_time, total_time)
		body = {'action': 'pause', 'media_type': 'movie', 'ids': ids, 'position_seconds': position_seconds, 'duration_seconds': duration_seconds}
		response = getFloppy('/scrobble/', post=body, method='POST', silent=True)
		if response is not None and response.status_code == 200:
			floppysync.upsert_bookmark(title='', resume_id='', imdb=imdb or '', tmdb=str(tmdb or ''), percent_played=str(watched_percent), paused_at=_now_iso())
			control.trigger_widget_refresh()
	except: log_utils.error()

def scrobbleEpisode(imdb, tmdb, tvdb, season, episode, watched_percent, current_time=0, total_time=0):
	if tmdb and True:
		from resources.lib.modules.episode_mapping import supported
		if supported(tmdb): imdb, tvdb = '', ''
	if isReadOnly(): return
	try:
		season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
		ids = {}
		if tmdb: ids['tmdb'] = str(tmdb)
		if imdb: ids['imdb'] = str(imdb)
		if tvdb: ids['tvdb'] = str(tvdb)
		position_seconds, duration_seconds = _scrobble_seconds(watched_percent, current_time, total_time)
		body = {'action': 'pause', 'media_type': 'episode', 'ids': ids, 'season_number': season, 'episode_number': episode,
			'position_seconds': position_seconds, 'duration_seconds': duration_seconds}
		response = getFloppy('/scrobble/', post=body, method='POST', silent=True)
		if response is not None and response.status_code == 200:
			floppysync.upsert_bookmark(tvshowtitle='x', title='', resume_id='', imdb=imdb or '', tmdb=str(tmdb or ''), tvdb=str(tvdb or ''), season=str(season), episode=str(episode), percent_played=str(watched_percent), paused_at=_now_iso())
			control.trigger_widget_refresh()
	except: log_utils.error()

def scrobbleStopMovie(imdb, tmdb, watched_percent, completed=False, current_time=0, total_time=0, already_watched=False):
	if isReadOnly(): return
	try:
		ids = {}
		if tmdb: ids['tmdb'] = str(tmdb)
		if imdb: ids['imdb'] = str(imdb)
		position_seconds, duration_seconds = _scrobble_seconds(watched_percent, current_time, total_time)
		send_completed = bool(completed) and not already_watched
		body = {'action': 'stop', 'media_type': 'movie', 'ids': ids, 'position_seconds': position_seconds, 'duration_seconds': duration_seconds, 'completed': send_completed}
		response = getFloppy('/scrobble/', post=body, method='POST', silent=True)
		if getSetting('debug.level') == '1':
			log_utils.log('FLOPPY: scrobbleStopMovie IMDB=%s TMDB=%s Percent=%s Completed=%s AlreadyWatched=%s HTTP=%s' % (imdb, tmdb, watched_percent, send_completed, already_watched, response.status_code if response is not None else 'None'), level=log_utils.LOGDEBUG)
		if response is not None and response.status_code == 200:
			if completed:
				floppysync.delete_bookmark(imdb or '', tvdb='', tmdb=str(tmdb or ''), season='', episode='')
			else:
				floppysync.upsert_bookmark(title='', resume_id='', imdb=imdb or '', tmdb=str(tmdb or ''), percent_played=str(watched_percent), paused_at=_now_iso())
			control.trigger_widget_refresh()
	except: log_utils.error()

def scrobbleStopEpisode(imdb, tmdb, tvdb, season, episode, watched_percent, completed=False, current_time=0, total_time=0, already_watched=False):
	if tmdb and True:
		from resources.lib.modules.episode_mapping import supported
		if supported(tmdb): imdb, tvdb = '', ''
	if isReadOnly(): return
	try:
		season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
		ids = {}
		if tmdb: ids['tmdb'] = str(tmdb)
		if imdb: ids['imdb'] = str(imdb)
		if tvdb: ids['tvdb'] = str(tvdb)
		position_seconds, duration_seconds = _scrobble_seconds(watched_percent, current_time, total_time)
		# See scrobbleStopMovie() above for why already_watched forces completed=False on the wire.
		send_completed = bool(completed) and not already_watched
		body = {'action': 'stop', 'media_type': 'episode', 'ids': ids, 'season_number': season, 'episode_number': episode,
			'position_seconds': position_seconds, 'duration_seconds': duration_seconds, 'completed': send_completed}
		response = getFloppy('/scrobble/', post=body, method='POST', silent=True)
		if getSetting('debug.level') == '1':
			log_utils.log('FLOPPY: scrobbleStopEpisode IMDB=%s TMDB=%s S%02dE%02d Percent=%s Completed=%s AlreadyWatched=%s HTTP=%s' % (imdb, tmdb, season, episode, watched_percent, send_completed, already_watched, response.status_code if response is not None else 'None'), level=log_utils.LOGDEBUG)
		if response is not None and response.status_code == 200:
			if completed:
				floppysync.delete_bookmark(imdb or '', tvdb=str(tvdb or ''), tmdb=str(tmdb or ''), season=str(season), episode=str(episode))
			else:
				floppysync.upsert_bookmark(tvshowtitle='x', title='', resume_id='', imdb=imdb or '', tmdb=str(tmdb or ''), tvdb=str(tvdb or ''), season=str(season), episode=str(episode), percent_played=str(watched_percent), paused_at=_now_iso())
			control.trigger_widget_refresh()
	except: log_utils.error()

def removePlaybackProgress(imdb='', tmdb='', tvdb='', season=None, episode=None, clear_local=True):
	"""Explicit manager action; automatic playback resets remain local-only."""
	try:
		if not getFloppyCredentialsInfo(): return False
		ids = {key: str(value) for key, value in [('imdb', imdb), ('tmdb', tmdb), ('tvdb', tvdb)]
			if value not in (None, '', '0', 0, 'None')}
		if not ids: return False
		is_episode = episode not in (None, '')
		if not is_episode and season not in (None, ''): return False
		post = {'media_type': 'episode' if is_episode else 'movie', 'ids': ids, 'position_seconds': None}
		if is_episode:
			post.update(season_number=int(season), episode_number=int(episode))
		response = getFloppy('/playback/progress/', post=post, method='PUT')
		status = response.status_code if response is not None else None
		log_utils.log('FLOPPY: remove playback progress type=%s tmdb=%s season=%s episode=%s HTTP=%s' %
			(post['media_type'], tmdb, season, episode, status), level=log_utils.LOGDEBUG)
		if status not in (200, 204): return False
		if clear_local:
			floppysync.delete_bookmark(imdb or '', tvdb=tvdb or '', tmdb=str(tmdb or ''),
				season='' if not is_episode else str(season), episode='' if not is_episode else str(episode))
		return True
	except:
		log_utils.error()
		return False


def finishProgressRemoval(succeeded, total):
	failed = total - succeeded
	message = 'Removed playback progress for %s item(s).' % succeeded
	if failed: message += ' Failed to remove %s item(s); check the log and Floppy authorization.' % failed
	control.notification(title='Floppy', message=message)
	if succeeded:
		control.trigger_widget_refresh(force=True)
		if 'plugin.video.umbrella' in control.infoLabel('Container.PluginName'): control.refresh()


def scrobbleReset(imdb, tmdb=None, tvdb=None, season=None, episode=None, refresh=True, widgetRefresh=False, clear_local=True, remote=True):
	try:
		# Explicit resets clear the provider record. Player lifecycle cleanup opts
		# out: playback start must not erase remote resume, and stop owns completion.
		if remote:
			if not removePlaybackProgress(imdb, tmdb, tvdb, season, episode, clear_local=clear_local):
				control.notification(title='Floppy', message='Failed to clear playback progress. Check the log and Floppy authorization.')
				return False
			if refresh or widgetRefresh:
				control.notification(title='Floppy', message='Playback progress cleared.')
				control.trigger_widget_refresh(force=True)
		else:
			if not getFloppyCredentialsInfo(): return False
			if clear_local:
				floppysync.delete_bookmark(imdb or '', tvdb=tvdb or '', tmdb=str(tmdb or ''),
					season='' if season is None else str(season), episode='' if episode is None else str(episode))
		if refresh: control.refresh()
		if widgetRefresh and not remote: control.trigger_widget_refresh()
		return True
	except:
		log_utils.error()
		return False


#### Status-bucket sync (Watchlist/Watching/On Hold/Completed/Dropped/Collection) ####

_STATUS_TABLES = {
	STATUS_PLANNING: ('movies_plantowatch', 'shows_plantowatch'),
	STATUS_WATCHING: ('movies_watching', 'shows_watching'),
	STATUS_ONHOLD:   ('movies_hold', 'shows_hold'),
	STATUS_COMPLETED:('movies_completed', 'shows_completed'),
	STATUS_DROPPED:  ('movies_dropped', 'shows_dropped'),
}

def _fetch_status_bucket(media_type, status):
	items = get_all_pages('/media/%s/?status=%s' % (media_type, status), silent=True, compact=True)
	return items

def _resolve_movie_imdb(tmdb):
	# Resolve missing IMDb IDs on older servers â€” reverse-resolve
	# it via TMDb so getMovieOverlay()'s imdb-keyed matching (shared with every other
	# provider) actually finds these rows.
	try:
		from resources.lib.database import cache as _cache
		from resources.lib.indexers import tmdb as _tmdb
		result = _cache.get(_tmdb.Movies().get_external_ids, 96, tmdb, '')
		return str(result.get('imdb_id', '') or '') if result else ''
	except:
		return ''

def _resolve_tv_imdb(tmdb):
	try:
		from resources.lib.database import cache as _cache
		from resources.lib.indexers import tmdb as _tmdb
		result = _cache.get(_tmdb.TVshows().get_external_ids, 96, tmdb)
		return str(result.get('imdb_id', '') or '') if result else ''
	except:
		return ''

def _episode_last_watch(entry, tmdb, season, episode):
	if entry.get('status') == STATUS_COMPLETED:
		return True, entry.get('end_date') or entry.get('progressed_at') or entry.get('created_at') or ''
	# A new unfinished rewatch must not erase an earlier completed viewing.
	history = get_all_pages('/media/tv/tmdb/%s/%s/%s/history/' % (tmdb, season, episode), silent=True)
	if history is None: return None
	completed = [h for h in history if h.get('status') == STATUS_COMPLETED]
	return bool(completed), max((h.get('end_date') or h.get('progressed_at') or h.get('created') or '' for h in completed), default='')


def _sync_episode_tracking_for_show(imdb, tmdb):
	"""Read individual tracked episodes; season progress cannot describe gaps."""
	detail = getFloppyAsJson(_tv_url(tmdb), silent=True)
	if not isinstance(detail, dict) or not isinstance(detail.get('related'), dict): return None
	seasons = detail['related'].get('seasons')
	if not isinstance(seasons, list): return None
	rows = []
	for season in seasons:
		if control.monitor.abortRequested(): return None
		sn = (season.get('item') or {}).get('season_number')
		if sn is None: return None
		data = getFloppyAsJson(_season_url(tmdb, sn), silent=True)
		if not isinstance(data, dict): return None
		episodes = (data.get('related') or {}).get('episodes')
		if not isinstance(episodes, list): return None
		for entry in episodes:
			if not entry.get('tracked'): continue
			en = (entry.get('item') or {}).get('episode_number')
			if en is None: return None
			state = _episode_last_watch(entry, tmdb, sn, en)
			if state is None: return None
			watched, last = state
			if not watched: continue
			rows.append((imdb, str(tmdb), '', int(sn), int(en), last))
	return rows


def _sync_watched_episodes_from_shows(progress_callback=None):
	entries = get_all_pages('/media/tv/', silent=True, compact=True)
	if entries is None: return None
	shows = {}
	for entry in entries:
		item = entry.get('item') or {}
		if item.get('source') not in (None, '', 'tmdb'): continue
		tmdb = str(item.get('media_id') or '')
		if not tmdb: return None
		shows[tmdb] = item
	probe = getFloppy('/media/episode/?limit=1', silent=True)
	if probe is None: return None
	rows = {}
	if probe.status_code in (404, 405):
		for idx, (tmdb, item) in enumerate(shows.items()):
			if control.monitor.abortRequested(): return None
			ids = item.get('ids') or {}
			imdb = str(ids.get('imdb') or '') or _resolve_tv_imdb(tmdb)
			show_rows = _sync_episode_tracking_for_show(imdb, tmdb)
			if show_rows is None: return None
			for r in show_rows:
				rows[(r[1], r[3], r[4])] = (r[0], r[1], str(ids.get('tvdb') or ''), r[3], r[4], r[5])
			if progress_callback: progress_callback('Syncing watched shows', idx + 1, len(shows))
		return list(rows.values())
	if probe.status_code != 200: return None
	# Do not filter status on the server: some versions filter episodes by the
	# parent season's status. The episode's own returned status is authoritative.
	episodes = get_all_pages('/media/episode/', silent=True, compact=True)
	if episodes is None: return None
	ids_by_show = {}
	for idx, entry in enumerate(episodes):
		if control.monitor.abortRequested(): return None
		item = entry.get('item') or {}
		if item.get('source') not in (None, '', 'tmdb'): continue
		if entry.get('tracked') is False: continue
		tmdb = str(item.get('media_id') or '')
		sn, en = item.get('season_number'), item.get('episode_number')
		if not tmdb or sn is None or en is None: return None
		if int(sn) < 0 or int(en) < 1: return None
		state = _episode_last_watch(entry, tmdb, sn, en)
		if state is None: return None
		watched, last = state
		if not watched: continue
		if tmdb not in ids_by_show:
			ids = shows.get(tmdb, {}).get('ids') or {}
			ids_by_show[tmdb] = (str(ids.get('imdb') or '') or _resolve_tv_imdb(tmdb), str(ids.get('tvdb') or ''))
		imdb, tvdb = ids_by_show[tmdb]
		key = (tmdb, int(sn), int(en))
		if key not in rows or last > rows[key][5]:
			rows[key] = (imdb, tmdb, tvdb, int(sn), int(en), last)
		if progress_callback: progress_callback('Syncing watched episodes', idx + 1, len(episodes))
	return list(rows.values())


def sync_watchedProgress(activities=None, forced=False, progress_callback=None):
	lock = None
	try:
		if not getFloppyCredentialsInfo(): return False
		lock = floppysync.acquire_sync_lock()
		if lock is None: return False
		credentials = (floppyBaseUrl(), getSetting('floppy.token'))
		revision = floppysync.get_revision('history')
		items = _fetch_status_bucket('movie', STATUS_COMPLETED)
		if items is None:
			log_utils.log('FLOPPY: movie fetch incomplete; keeping previous watched history', level=log_utils.LOGWARNING)
			return False
		movies = []
		for idx, entry in enumerate(items):
			if control.monitor.abortRequested(): return False
			item = entry.get('item') or {}
			tmdb = str(item.get('media_id') or '')
			if item.get('source') not in (None, '', 'tmdb'): continue
			if not tmdb: return False
			imdb = str((item.get('ids') or {}).get('imdb') or '') or _resolve_movie_imdb(tmdb)
			last = entry.get('end_date') or entry.get('progressed_at') or entry.get('created_at') or ''
			movies.append((imdb, tmdb, item.get('title', ''), (item.get('release_datetime') or '')[:4], last))
			if progress_callback: progress_callback('Syncing watched movies', idx + 1, len(items))
		episodes = _sync_watched_episodes_from_shows(progress_callback=progress_callback)
		if episodes is None or control.monitor.abortRequested():
			log_utils.log('FLOPPY: episode fetch incomplete or cancelled; keeping previous watched history', level=log_utils.LOGWARNING)
			return False
		if credentials != (floppyBaseUrl(), getSetting('floppy.token')): return False
		if not floppysync.store_watched_history(movies, episodes, expected_revision=revision): return False
		floppysync.clear_cache()
		log_utils.log('FLOPPY: watched sync complete (%s movies, %s episodes)' % (len(movies), len(episodes)), level=log_utils.LOGINFO)
		control.trigger_widget_refresh()
		return True
	except:
		log_utils.error()
		return False
	finally:
		if lock is not None: lock.close()


def sync_watched(activities=None, forced=False, progress_callback=None):
	return sync_watchedProgress(activities=activities, forced=forced, progress_callback=progress_callback)


def sync_watch_list(activities=None, forced=False):
	try:
		if not getFloppyCredentialsInfo(): return False
		credentials = (floppyBaseUrl(), getSetting('floppy.token'))
		snapshots = {}
		for status, (mv_table, tv_table) in _STATUS_TABLES.items():
			for media, table in (('movie', mv_table), ('tv', tv_table)):
				items = _fetch_status_bucket(media, status)
				if items is None or control.monitor.abortRequested(): return False
				snapshots[table] = items
		if credentials != (floppyBaseUrl(), getSetting('floppy.token')): return False
		return floppysync.store_status_lists(snapshots)
	except:
		log_utils.error()
		return False


def sync_collection(activities=None, forced=False):
	try:
		if not getFloppyCredentialsInfo(): return False
		credentials = (floppyBaseUrl(), getSetting('floppy.token'))
		snapshots = {}
		for media, table in (('movie', 'movies_collection'), ('tv', 'shows_collection')):
			items = get_all_pages('/collection/?item_media_type=' + media, silent=True, compact=True)
			if items is None or control.monitor.abortRequested(): return False
			snapshots[table] = [{'id': (i.get('item') or {}).get('id'), 'item': i.get('item'),
				'score': None, 'created_at': i.get('collected_at')} for i in items]
		if credentials != (floppyBaseUrl(), getSetting('floppy.token')): return False
		return floppysync.store_status_lists(snapshots)
	except:
		log_utils.error()
		return False


def get_collection_entries(media_type='movie'):
	results = []
	try:
		media_param = 'movie' if media_type == 'movie' else 'tv'
		items = get_all_pages('/collection/?item_media_type=%s' % media_param, silent=True) or []
		for i in items:
			try:
				item = i.get('item') or {}
				entry_id = i.get('id')
				if entry_id is None: continue
				results.append({
					'entry_id': str(entry_id),
					'title': item.get('title', ''),
					'year': str(item.get('year', '') or ''),
					'tmdb': str(item.get('media_id') or ''),
					'imdb': '', 'tvdb': '', 'premiered': '',
					'trakt': str(entry_id),
				})
			except: log_utils.error()
	except: log_utils.error()
	return results

def sync_playbackProgress(activities=None, forced=False):
	lock = None
	try:
		if not getFloppyCredentialsInfo(): return False
		lock = floppysync.acquire_sync_lock()
		if lock is None: return False
		credentials = (floppyBaseUrl(), getSetting('floppy.token'))
		revision = floppysync.get_revision('bookmarks')
		items = get_all_pages('/playback/progress/', silent=True)
		if items is None: return False
		rows = []
		for item in items:
			if control.monitor.abortRequested(): return False
			if item.get('completed') or item.get('media_type') not in ('movie', 'episode'): continue
			if item.get('source') not in (None, '', 'tmdb'): continue
			ids = item.get('ids') or {}
			tmdb, imdb, tvdb = str(ids.get('tmdb') or item.get('media_id') or ''), str(ids.get('imdb') or ''), str(ids.get('tvdb') or '')
			if not tmdb: return False
			duration, position = float(item.get('duration_seconds') or 0), float(item.get('position_seconds') or 0)
			if duration <= 0 or position <= 0: continue
			season, episode = '', ''
			if item.get('media_type') == 'episode':
				if item.get('season_number') is None or item.get('episode_number') is None: return False
				season, episode = str(int(item['season_number'])), str(int(item['episode_number']))
			percent = str(round(min(position / duration, 1) * 100, 2))
			from hashlib import md5
			resume_id = md5(repr((imdb, tmdb, tvdb, season, episode)).encode('utf-8')).hexdigest()
			rows.append((item.get('series_title') or '', item.get('title') or '', resume_id, imdb, tmdb, tvdb,
				season, episode, '', '', '', str(duration), percent, item.get('updated_at') or ''))
		if credentials != (floppyBaseUrl(), getSetting('floppy.token')): return False
		return floppysync.store_bookmarks(rows, expected_revision=revision)
	except:
		log_utils.error()
		return False
	finally:
		if lock is not None: lock.close()


def force_floppySync():
	if not control.yesnoDialog(control.lang(32056), '', ''): return
	dialog = control.progressDialog
	dialog.create(control.addonName(), 'Preparing Floppy sync...')
	def _progress(phase, done=None, total=None):
		try:
			if done is not None and total:
				dialog.update(min(int(100.0 * done / total), 100), '%s... (%s/%s)' % (phase, done, total))
			elif done is not None:
				dialog.update(0, '%s... (%s synced)' % (phase, done))
			else:
				dialog.update(0, '%s...' % phase)
		except: pass
	success = False
	try:
		_progress('Syncing watchlist/watching/on-hold/etc')
		lists_ok = sync_watch_list(forced=True)
		_progress('Syncing collection')
		collection_ok = sync_collection(forced=True)
		history_ok = sync_watchedProgress(forced=True, progress_callback=_progress)
		resume_ok = True
		if getSetting('bookmarks') == 'true' and getSetting('scrobble.source') == '5':
			_progress('Syncing resume points')
			resume_ok = sync_playbackProgress(forced=True)
		success = lists_ok and collection_ok and history_ok and resume_ok
	except:
		log_utils.error()
	finally:
		dialog.close()
	control.notification(title='Floppy', message='Forced Floppy Sync Complete' if success else 'Floppy sync incomplete - previous data retained for failed requests')


#### Indicators (movies/shows watched state, seasons/episodes progress) ####

def syncMovies():
	try:
		if not getFloppyCredentialsInfo(): return None
		return floppysync.get_watched_movies() or []
	except:
		log_utils.error()
		return None

def _make_episode_ranges(ep_nums_sorted):
	if not ep_nums_sorted: return []
	ranges = []
	start = end = ep_nums_sorted[0]
	for ep in ep_nums_sorted[1:]:
		if ep == end + 1: end = ep
		else:
			ranges.append((start, end))
			start = end = ep
	ranges.append((start, end))
	return ranges

def syncTVShows():
	try:
		if not getFloppyCredentialsInfo(): return None
		episodes = floppysync.get_watched_episodes()
		if not episodes: return []
		shows = {}
		for (show_imdb, show_tmdb, show_tvdb, season, episode) in episodes:
			if show_tmdb not in shows:
				shows[show_tmdb] = {'ids': {'imdb': show_imdb, 'tmdb': show_tmdb, 'tvdb': show_tvdb}, 'by_season': {}}
			s = int(season)
			shows[show_tmdb]['by_season'].setdefault(s, []).append(int(episode))
		indicators = []
		for v in shows.values():
			ep_ranges = {s: _make_episode_ranges(sorted(eps)) for s, eps in v['by_season'].items()}
			total = sum(e - s + 1 for ranges in ep_ranges.values() for s, e in ranges)
			indicators.append((v['ids'], total, ep_ranges))
		return indicators
	except:
		log_utils.error()
		return None

def getShowProgress(tmdb):
	try:
		if not tmdb: return None
		return floppysync.get(_fetchShowProgress, 15, tmdb)
	except:
		log_utils.error()
		return None

def _fetchShowProgress(tmdb):
	try:
		include_specials = getSetting('tv.specials') == 'true'
		episodes = floppysync.get_watched_episodes()
		show_eps = [(s, e) for (si, st, sv, s, e) in (episodes or []) if st == tmdb]
		from collections import defaultdict
		by_season = defaultdict(list)
		for (s, e) in show_eps:
			s = int(s)
			if s == 0 and not include_specials: continue
			by_season[s].append(int(e))
		from resources.lib.database import cache as _cache
		from resources.lib.indexers import tmdb as _tmdb
		season_counts = {}
		try:
			showSeasons = _cache.get(_tmdb.TVshows().get_showSeasons_meta, 96, tmdb)
			if showSeasons:
				status = (showSeasons.get('status') or '').lower()
				ended = status in ('ended', 'canceled', 'cancelled')
				last_ep = showSeasons.get('last_episode_to_air') or {}
				last_aired_sn = int(last_ep.get('season_number', 0)) if last_ep else 0
				last_aired_ep = int(last_ep.get('episode_number', 0)) if last_ep else 0
				for s in showSeasons.get('seasons', []):
					sn = s.get('season_number')
					if sn is None: continue
					if sn == 0 and not include_specials: continue
					ep_count = s.get('episode_count', 0)
					if ended or not last_aired_sn or sn < last_aired_sn:
						season_counts[sn] = ep_count
					elif sn == last_aired_sn:
						season_counts[sn] = last_aired_ep if last_aired_ep > 0 else ep_count
					# sn > last_aired_sn: future/unaired season â€” omit
		except: pass
		if not season_counts and not by_season: return [[], {}]
		result_counts = {}
		fully_watched = []
		for s, watched_eps in by_season.items():
			total = season_counts.get(s, len(set(watched_eps)))
			watched = len(set(watched_eps))
			result_counts[s] = {'total': total, 'watched': watched, 'unwatched': max(total - watched, 0)}
			if watched >= total: fully_watched.append(s)
		for sn, total in season_counts.items():
			if sn not in result_counts:
				result_counts[sn] = {'total': total, 'watched': 0, 'unwatched': total}
		return [[str(s) for s in sorted(fully_watched)], result_counts]
	except:
		log_utils.error()
		return None

def syncSeasons(imdb, tvdb):
	try:
		if not getFloppyCredentialsInfo(): return None
		if not imdb and not tvdb: return None
		tmdb = _resolve_tmdb('tv', imdb=imdb, tvdb=tvdb)
		if not tmdb: return [[], {}]
		progress = getShowProgress(tmdb)
		return progress if progress else [[], {}]
	except:
		log_utils.error()
		return None

def getMoviesWatchedActivity():
	try: return floppysync.last_sync('last_history_at')
	except: log_utils.error()
	return 0

def getEpisodesWatchedActivity():
	try: return floppysync.last_sync('last_history_at')
	except: log_utils.error()
	return 0

def timeoutsyncMovies():
	return floppysync.timeout(syncMovies)

def timeoutsyncTVShows():
	return floppysync.timeout(syncTVShows)

def timeoutsyncSeasons(imdb, tvdb):
	try: return floppysync.timeout(syncSeasons, imdb, tvdb, returnNone=True)
	except: log_utils.error()

def cachesyncMovies(timeout=720):
	try: return floppysync.get(syncMovies, timeout)
	except: log_utils.error()

def cachesyncTVShows(timeout=720):
	try: return floppysync.get(syncTVShows, timeout)
	except: log_utils.error()

def cachesyncTV(imdb, tvdb):
	try:
		from threading import Thread as _Thread
		threads = [_Thread(target=cachesyncTVShows, args=(0,)), _Thread(target=cachesyncSeasons, args=(imdb, tvdb, 0))]
		[i.start() for i in threads]
		[i.join() for i in threads]
	except: log_utils.error()

def cachesyncSeasons(imdb, tvdb='', timeout=720):
	try:
		imdb = imdb or ''
		tvdb = tvdb or ''
		return floppysync.get(syncSeasons, timeout, imdb, tvdb)
	except: log_utils.error()

def seasonCount(imdb, tvdb):
	try:
		result = syncSeasons(imdb, tvdb)
		if result and len(result) > 1: return result[1]
		return {}
	except: log_utils.error()


#### Custom lists (GET /lists/, GET /lists/{id}/items/ â€” confirmed via live Postman
#### testing against a real instance 2026-08-16) ####

def get_user_lists():
	try:
		if not getFloppyCredentialsInfo(): return []
		return get_all_pages('/lists/', silent=True) or []
	except:
		log_utils.error()
		return []

def get_list_items(list_id):
	results = []
	try:
		items = get_all_pages('/lists/%s/items/' % list_id, silent=True) or []
		for i in items:
			try:
				item = i.get('item') or {}
				results.append({
					'entry_id': str(i.get('id', '') or ''),
					'tmdb': str(item.get('media_id') or ''),
					'media_type': 'movie' if item.get('media_type') == 'movie' else 'tv',
					'title': item.get('title', ''),
					'premiered': (item.get('release_datetime') or '')[:10],
					'year': (item.get('release_datetime') or '')[:4],
				})
			except: pass
	except:
		log_utils.error()
	return results

def add_to_list(list_id, tmdb='', media_type='movie'):
	try:
		media = 'movie' if media_type == 'movie' else 'tv'
		response = getFloppy('/media/%s/tmdb/%s/lists/%s/' % (media, tmdb, list_id), post={}, method='PUT', silent=True)
		return bool(response is not None and response.status_code in (200, 201, 409))
	except:
		log_utils.error()
		return False

def remove_from_list(list_id, tmdb='', media_type='movie'):
	try:
		media = 'movie' if media_type == 'movie' else 'tv'
		response = getFloppy('/media/%s/tmdb/%s/lists/%s/' % (media, tmdb, list_id), method='DELETE', silent=True)
		return bool(response is not None and response.status_code in (200, 204))
	except:
		log_utils.error()
		return False

def create_list(name):
	try:
		response = getFloppy('/lists/', post={'name': name}, method='POST', silent=True)
		if response is None or response.status_code not in (200, 201): return None
		result = response.json()
		return str(result.get('id', '') or '') or None
	except:
		log_utils.error()
		return None


#### Watchlist / Collection membership (context-menu actions) ####

def add_to_watchlist(tmdb='', media_type='movie', season_number=None):
	try:
		media = 'movie' if media_type == 'movie' else ('season' if season_number is not None else 'tv')
		body = {'source': 'tmdb', 'media_id': str(tmdb), 'status': STATUS_PLANNING}
		if season_number is not None: body['season_number'] = int(season_number)
		response = getFloppy('/media/%s/' % media, post=body, method='POST', silent=True)
		return bool(response is not None and response.status_code in (200, 201, 409))
	except:
		log_utils.error()
		return False

def remove_from_watchlist(tmdb='', media_type='movie'):
	try:
		url = _movie_url(tmdb) if media_type == 'movie' else _tv_url(tmdb)
		response = getFloppy(url, method='DELETE', silent=True)
		return bool(response is not None and response.status_code in (200, 204))
	except:
		log_utils.error()
		return False

def _resolve_item_pk(tmdb, media_type='movie'):
	try:
		url = _movie_url(tmdb) if media_type == 'movie' else _tv_url(tmdb)
		result = getFloppyAsJson(url, silent=True)
		if not result: return None
		return result.get('id')
	except:
		log_utils.error()
		return None

def add_to_collection(tmdb='', media_type='movie'):
	try:
		item_pk = _resolve_item_pk(tmdb, media_type)
		if not item_pk: return False
		response = getFloppy('/collection/', post={'item_id': item_pk}, method='POST', silent=True)
		return bool(response is not None and response.status_code in (200, 201))
	except:
		log_utils.error()
		return False

def remove_from_collection(entry_id):
	try:
		response = getFloppy('/collection/%s/' % entry_id, method='DELETE', silent=True)
		return bool(response is not None and response.status_code in (200, 204))
	except:
		log_utils.error()
		return False

def set_status(tmdb='', media_type='movie', status=STATUS_PLANNING):
	try:
		success = _patch_or_create(_movie_url(tmdb) if media_type == 'movie' else _tv_url(tmdb), media_type, tmdb, {'status': status})
		return success
	except:
		log_utils.error()
		return False


#### Context-menu manager (mirrors customtrakt.manager()/simkl.manager()) ####

def manager(name, imdb=None, tvdb=None, tmdb=None, season=None, episode=None, refresh=True, watched=None, unfinished=False, tvshow=None):
	try:
		if season: season = int(season)
		if episode: episode = int(episode)
		if episode: content_type = 'episode'
		elif season: content_type = 'season'
		elif tvdb and tvdb != 'None': content_type = 'tvshow'
		else: content_type = 'movie'
		media_type = 'movie' if content_type == 'movie' else 'tv'
		hc = getSetting('highlight.color')
		items = []
		if watched is not None:
			items += [('[COLOR %s]Unwatch[/COLOR]' % hc, 'unwatch')] if watched else [('[COLOR %s]Watch[/COLOR]' % hc, 'watch')]
		else:
			items += [('[COLOR %s]Watch[/COLOR]' % hc, 'watch')]
			items += [('[COLOR %s]Unwatch[/COLOR]' % hc, 'unwatch')]
		if content_type in ('movie', 'episode'):
			items += [('[COLOR %s]Clear Scrobble Progress[/COLOR]' % hc, 'scrobbleReset')]
		if content_type in ('movie', 'tvshow'):
			items += [('[COLOR %s]Add to Watchlist[/COLOR]' % hc, 'watchlist_add')]
			items += [('[COLOR %s]Remove from Watchlist[/COLOR]' % hc, 'watchlist_remove')]
			items += [('[COLOR %s]Set to Watching[/COLOR]' % hc, 'set_watching')]
			items += [('[COLOR %s]Set to On Hold[/COLOR]' % hc, 'set_onhold')]
			items += [('[COLOR %s]Set to Dropped[/COLOR]' % hc, 'set_dropped')]
			items += [('[COLOR %s]Add to Collection[/COLOR]' % hc, 'collection_add')]
			items += [('[COLOR %s]Add to List[/COLOR]' % hc, 'list_add')]
			items += [('[COLOR %s]Remove from List[/COLOR]' % hc, 'list_remove')]
		control.hide()
		select = control.selectDialog([i[0] for i in items], heading=control.addonInfo('name') + ' - Floppy')
		if select == -1: return
		action_key = items[select][1]
		if action_key == 'watch':
			watch(content_type, name, imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, refresh=refresh)
		elif action_key == 'unwatch':
			unwatch(content_type, name, imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, refresh=refresh)
		elif action_key == 'scrobbleReset':
			scrobbleReset(imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, refresh=True)
		elif action_key == 'watchlist_add':
			resolved_tmdb = tmdb or _resolve_tmdb(media_type, imdb=imdb, tvdb=tvdb)
			if resolved_tmdb and add_to_watchlist(tmdb=resolved_tmdb, media_type=media_type):
				sync_watch_list(forced=True)
				if refresh: control.refresh()
		elif action_key == 'watchlist_remove':
			resolved_tmdb = tmdb or _resolve_tmdb(media_type, imdb=imdb, tvdb=tvdb)
			if resolved_tmdb and remove_from_watchlist(tmdb=resolved_tmdb, media_type=media_type):
				sync_watch_list(forced=True)
				if refresh: control.refresh()
		elif action_key in ('set_watching', 'set_onhold', 'set_dropped'):
			resolved_tmdb = tmdb or _resolve_tmdb(media_type, imdb=imdb, tvdb=tvdb)
			status_map = {'set_watching': STATUS_WATCHING, 'set_onhold': STATUS_ONHOLD, 'set_dropped': STATUS_DROPPED}
			if resolved_tmdb and set_status(tmdb=resolved_tmdb, media_type=media_type, status=status_map[action_key]):
				sync_watch_list(forced=True)
				if refresh: control.refresh()
		elif action_key == 'collection_add':
			resolved_tmdb = tmdb or _resolve_tmdb(media_type, imdb=imdb, tvdb=tvdb)
			if resolved_tmdb and add_to_collection(tmdb=resolved_tmdb, media_type=media_type):
				sync_collection(forced=True)
				if refresh: control.refresh()
		elif action_key == 'list_add':
			notify = getSetting('services.general.notifications') == 'true'
			resolved_tmdb = tmdb or _resolve_tmdb(media_type, imdb=imdb, tvdb=tvdb)
			if not resolved_tmdb: return
			lists = get_user_lists()
			options = [l.get('name', '') for l in lists] + ['[COLOR %s]+ New List[/COLOR]' % hc]
			list_select = control.selectDialog(options, heading=control.addonInfo('name') + ' - Floppy Lists')
			if list_select == -1: return
			if list_select == len(lists):
				new_name = control.dialog.input(getLS(32520))
				if not new_name: return
				list_id = create_list(new_name)
				if not list_id:
					if notify: control.notification(title='Floppy', message='Failed to create list')
					return
			else:
				list_id = str(lists[list_select].get('id', '') or '')
			if list_id and add_to_list(list_id, tmdb=resolved_tmdb, media_type=media_type):
				if notify: control.notification(title='Floppy', message='Added to list')
				if refresh: control.refresh()
			else:
				if notify: control.notification(title='Floppy', message='Failed to add to list')
		elif action_key == 'list_remove':
			notify = getSetting('services.general.notifications') == 'true'
			resolved_tmdb = tmdb or _resolve_tmdb(media_type, imdb=imdb, tvdb=tvdb)
			if not resolved_tmdb: return
			lists = get_user_lists()
			if not lists:
				if notify: control.notification(title='Floppy', message='No lists found')
				return
			list_select = control.selectDialog([l.get('name', '') for l in lists], heading=control.addonInfo('name') + ' - Remove From List')
			if list_select == -1: return
			list_id = str(lists[list_select].get('id', '') or '')
			if list_id and remove_from_list(list_id, tmdb=resolved_tmdb, media_type=media_type):
				if notify: control.notification(title='Floppy', message='Removed from list')
				if refresh: control.refresh()
			else:
				if notify: control.notification(title='Floppy', message='Failed to remove from list')
	except: log_utils.error()
