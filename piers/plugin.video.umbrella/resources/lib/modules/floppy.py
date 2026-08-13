# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""
# Floppy (self-hosted media tracker). Built against the dannyvfilms/Floppy
# fork's /api/v1/ 
# Auth is a single static bearer token pasted from the
# Floppy web UI (Integrations settings) — there is no device-code flow uses API

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
		req_headers = dict(headers)
		req_headers['Authorization'] = 'Bearer %s' % getSetting('floppy.token')
		body = jsdumps(post) if post is not None else None
		if not method: method = 'POST' if post is not None else 'GET'
		method = method.upper()
		for _attempt in range(2):
			try:
				if method == 'POST':
					response = session.post(url, data=body, headers=req_headers, timeout=20)
				elif method == 'PATCH':
					response = session.patch(url, data=body, headers=req_headers, timeout=20)
				elif method == 'DELETE':
					response = session.delete(url, headers=req_headers, timeout=20)
				else:
					response = session.get(url, headers=req_headers, timeout=20)
				_last_request_time = time.time()
				break
			except requests.exceptions.ConnectionError:
				if _attempt == 0:
					log_utils.log('FLOPPY: connection reset, retrying with fresh connection...', level=log_utils.LOGDEBUG)
					session.close()
				else:
					raise
		status_code = response.status_code
		if status_code == 429:
			if 'Retry-After' in response.headers:
				throttleTime = response.headers['Retry-After']
				control.sleep((int(throttleTime) + 1) * 1000)
				return getFloppy(url, post=post, method=method, silent=silent)
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


def get_all_pages(url, silent=False):
	# Confirmed pagination shape: {'pagination': {'total','limit','offset','next','previous'}, 'results': [...]}
	try:
		sep = '&' if '?' in url else '?'
		limit = 250
		offset = 0
		results = []
		while True:
			page_url = url + sep + 'limit=%d&offset=%d' % (limit, offset)
			data = getFloppyAsJson(page_url, silent=silent)
			if not data: break
			page_results = data.get('results', []) if isinstance(data, dict) else data
			if not page_results: break
			results.extend(page_results)
			if len(page_results) < limit: break
			offset += limit
			if offset > 100000:
				log_utils.log('FLOPPY: get_all_pages reached safety limit for URL: %s' % url, level=log_utils.LOGWARNING)
				break
		return results
	except Exception as e:
		log_utils.log('FLOPPY: Error in get_all_pages: %s' % str(e), level=log_utils.LOGWARNING)
		return None


#### Auth: static bearer token pasted from the Floppy web UI ####

def floppyAuth(fromSettings=0):
	try:
		base = floppyBaseUrl()
		token = getSetting('floppy.token')
		if not base or not token:
			if fromSettings == 1: control.openSettings('5.6', 'plugin.video.umbrella')
			control.notification(message='Enter a Floppy server URL and token first', icon=floppy_icon)
			return False
		response = getFloppy('/media/movie/?limit=1', method='GET', silent=True)
		if not response or response.status_code != 200:
			control.notification(message='Floppy Authorization Error - Check URL/Token', icon=floppy_icon)
			if fromSettings == 1: control.openSettings('5.6', 'plugin.video.umbrella')
			return False
		setSetting('floppy.isauthed', 'true')
		control.notification(message='Floppy Authorized Successfully', icon=floppy_icon)
		if fromSettings == 1: control.openSettings('5.6', 'plugin.video.umbrella')
		if not control.yesnoDialog('Do you want to set Floppy as your service for your watched and unwatched indicators?', '', '', 'Indicators', 'No', 'Yes'): return True
		control.homeWindow.setProperty('umbrella.updateSettings', 'false')
		setSetting('indicators.alt', '5')
		setSetting('scrobble.source', '5')
		control.homeWindow.setProperty('umbrella.updateSettings', 'true')
		setSetting('scrobble', 'Floppy')
		setSetting('indicators', 'Floppy')
		control.notification(message='Floppy Indicators Enabled - Syncing Watched Data...')
		from threading import Thread
		Thread(target=sync_watched, kwargs={'forced': True}).start()
		return True
	except:
		log_utils.error()
		return False


def floppyRevoke(fromSettings=0):
	control.homeWindow.setProperty('umbrella.updateSettings', 'false')
	setSetting('floppy.user.name', '')
	setSetting('floppy.token', '')
	setSetting('floppy.isauthed', '')
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
			log_utils.log('FLOPPY: markMovieAsWatched IMDB=%s aborted — could not resolve a tmdb id' % imdb, level=log_utils.LOGWARNING)
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
			log_utils.log('FLOPPY: markMovieAsNotWatched IMDB=%s aborted — could not resolve a tmdb id' % imdb, level=log_utils.LOGWARNING)
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
			_watch_all_episodes_remote(tmdb, season=None)
			if _sync_episode_tracking_for_show(imdb, tmdb) is None:
				_mark_all_episodes_watched_locally(imdb, tmdb, season=None) # hard API failure fallback
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
			# PATCHing status doesn't itself untrack episodes server-side (mirrors why
			# markTVShowAsWatched has to explicitly (un)watch every episode) — without
			# this, the next full sync would just re-discover them as still tracked and
			# silently undo the unwatch.
			for (si, st, sv, s, e) in floppysync.get_watched_episodes():
				if st == tmdb:
					getFloppy(_episode_url(tmdb, int(s), int(e)), method='DELETE', silent=True)
					floppysync.delete_watched_episode(st, s, e)
			floppysync.cache_delete(floppysync._hash_function(syncTVShows, ()))
			floppysync.cache_delete(floppysync._hash_function(_fetchShowProgress, (tmdb,)))
		return success
	except:
		log_utils.error()
		return False

def markSeasonAsWatched(imdb, tvdb, season):
	try:
		tmdb = _resolve_tmdb('tv', imdb=imdb, tvdb=tvdb)
		if not tmdb: return False
		season = int('%01d' % int(season))
		success = _patch_or_create(_season_url(tmdb, season), 'season', tmdb, {'status': STATUS_COMPLETED}, season_number=season)
		if success:
			_watch_all_episodes_remote(tmdb, season=season)
			if _sync_episode_tracking_for_show(imdb, tmdb) is None:
				_mark_all_episodes_watched_locally(imdb, tmdb, season=season) # hard API failure fallback
			floppysync.cache_delete(floppysync._hash_function(syncTVShows, ()))
			floppysync.cache_delete(floppysync._hash_function(_fetchShowProgress, (tmdb,)))
		return success
	except:
		log_utils.error()
		return False

def markSeasonAsNotWatched(imdb, tvdb, season):
	try:
		tmdb = _resolve_tmdb('tv', imdb=imdb, tvdb=tvdb)
		if not tmdb: return False
		season = int('%01d' % int(season))
		response = getFloppy(_season_url(tmdb, season), post={'status': STATUS_PLANNING}, method='PATCH', silent=True)
		success = bool(response is not None and response.status_code == 200)
		if success:
			for (si, st, sv, s, e) in floppysync.get_watched_episodes():
				if st == tmdb and int(s) == season:
					getFloppy(_episode_url(tmdb, int(s), int(e)), method='DELETE', silent=True)
					floppysync.delete_watched_episode(st, s, e)
			floppysync.cache_delete(floppysync._hash_function(syncTVShows, ()))
			floppysync.cache_delete(floppysync._hash_function(_fetchShowProgress, (tmdb,)))
		return success
	except:
		log_utils.error()
		return False

def markEpisodeAsWatched(imdb, tvdb, season, episode):
	try:
		tmdb = _resolve_tmdb('tv', imdb=imdb, tvdb=tvdb)
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

def markEpisodeAsNotWatched(imdb, tvdb, season, episode):
	try:
		tmdb = _resolve_tmdb('tv', imdb=imdb, tvdb=tvdb)
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


def watch(content_type, name, imdb=None, tvdb=None, season=None, episode=None, refresh=True):
	control.busy()
	success = False
	if content_type == 'movie': success = markMovieAsWatched(imdb)
	elif content_type == 'tvshow': success = markTVShowAsWatched(imdb, tvdb)
	elif content_type == 'season': success = markSeasonAsWatched(imdb, tvdb, season)
	elif content_type == 'episode': success = markEpisodeAsWatched(imdb, tvdb, season, episode)
	control.hide()
	if refresh: control.refresh()
	control.trigger_widget_refresh()
	if season and not episode: name = '%s-Season%s...' % (name, season)
	if season and episode: name = '%s-S%sxE%02d...' % (name, season, int(episode))
	if getSetting('floppy.general.notifications') == 'true':
		if success is True: control.notification(title='Floppy', message='%s Marked as Watched on Floppy' % name)
		else: control.notification(title='Floppy', message='%s Failed to Mark as Watched on Floppy' % name)

def unwatch(content_type, name, imdb=None, tvdb=None, season=None, episode=None, refresh=True):
	control.busy()
	success = False
	if content_type == 'movie': success = markMovieAsNotWatched(imdb)
	elif content_type == 'tvshow': success = markTVShowAsNotWatched(imdb, tvdb)
	elif content_type == 'season': success = markSeasonAsNotWatched(imdb, tvdb, season)
	elif content_type == 'episode': success = markEpisodeAsNotWatched(imdb, tvdb, season, episode)
	control.hide()
	if refresh: control.refresh()
	control.trigger_widget_refresh()
	if season and not episode: name = '%s-Season%s...' % (name, season)
	if season and episode: name = '%s-S%sxE%02d...' % (name, season, int(episode))
	if getSetting('floppy.general.notifications') == 'true':
		if success is True: control.notification(title='Floppy', message='%s Marked as Unwatched on Floppy' % name)
		else: control.notification(title='Floppy', message='%s Failed to Mark as Unwatched on Floppy' % name)


#### Scrobble (real POST /scrobble/ endpoint — start/pause update the server's live
#### Now Playing card only; local resume/bookmark state is tracked client-side since
#### Floppy has no queryable "in progress playback" list to pull from). ####

def _scrobble_seconds(watched_percent, current_time, total_time):
	# position_seconds/duration_seconds are meant to be real elapsed/total playback
	# seconds — every call site now has Kodi's actual getTime()/getTotalTime() available
	# and passes them through. Without them (current_time/total_time not provided), this
	# used to send the 0-100 percent value itself as "seconds" with a hardcoded 100-second
	# "duration" — Floppy's own Now Playing card then displayed e.g. 38 seconds of a
	# 1:40 (100s) runtime for what was really 38% into a much longer episode. The percent
	# fallback below only exists for any caller that still can't supply real seconds.
	if total_time:
		return int(current_time or 0), int(total_time)
	return int(watched_percent), 100

def scrobbleStart(media_type, title='', tvshowtitle='', year='0', imdb='', tmdb='', tvdb='', season='', episode='', watched_percent=0, current_time=0, total_time=0):
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
	try:
		ids = {}
		if tmdb: ids['tmdb'] = str(tmdb)
		if imdb: ids['imdb'] = str(imdb)
		position_seconds, duration_seconds = _scrobble_seconds(watched_percent, current_time, total_time)
		# already_watched means markMovieDuringPlayback() already recorded this as watched
		# mid-playback (see playcount.py) — sending completed=True here too would write a
		# second, duplicate watched-history entry server-side. Still send the stop action
		# itself unconditionally (that's what closes Floppy's live "Now Playing" session —
		# skipping this call entirely left that card stuck on every normal watch-to-
		# completion), just with completed forced False so it's a no-op for history.
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

def scrobbleReset(imdb, tmdb=None, tvdb=None, season=None, episode=None, refresh=True, widgetRefresh=False, clear_local=True):
	if not getFloppyCredentialsInfo(): return
	try:
		if clear_local: floppysync.delete_bookmark(imdb or '', tvdb=tvdb or '', tmdb=str(tmdb or ''), season=season or '', episode=episode or '')
		if refresh: control.refresh()
		if widgetRefresh: control.trigger_widget_refresh()
	except: log_utils.error()


#### Status-bucket sync (Watchlist/Watching/On Hold/Completed/Dropped/Collection) ####

_STATUS_TABLES = {
	STATUS_PLANNING: ('movies_plantowatch', 'shows_plantowatch'),
	STATUS_WATCHING: ('movies_watching', 'shows_watching'),
	STATUS_ONHOLD:   ('movies_hold', 'shows_hold'),
	STATUS_COMPLETED:('movies_completed', 'shows_completed'),
	STATUS_DROPPED:  ('movies_dropped', 'shows_dropped'),
}

def _fetch_status_bucket(media_type, status):
	items = get_all_pages('/media/%s/?status=%s' % (media_type, status), silent=True)
	return items or []

def _resolve_movie_imdb(tmdb):
	# Floppy is TMDB-native and never hands back an imdb id directly — reverse-resolve
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

def _mark_all_episodes_watched_locally(imdb, tmdb, season=None):
	# Fallback only (network/API failure) — assumes every TMDb-listed episode of the
	# season/show was watched. NOT used as the primary path: live testing against the
	# real server confirmed a season's own 'tracked'/'status' fields do NOT reliably
	# reflect its episodes' real watched state (a season can show tracked=false while
	# individual episodes underneath it are tracked=true), so _sync_episode_tracking_
	# for_show() (real per-episode data) is used everywhere this matters.
	try:
		from resources.lib.database import cache as _cache
		from resources.lib.indexers import tmdb as _tmdb
		now = _now_iso()
		today = datetime.utcnow().strftime('%Y-%m-%d')
		if season is not None:
			raw = _cache.get(_tmdb.TVshows().get_season_request, 96, tmdb, int(season))
			for ep in (raw or {}).get('episodes', []):
				en = int(ep.get('episode_number', 0))
				air_date = ep.get('air_date')
				if en > 0 and air_date and air_date <= today:
					floppysync.upsert_watched_episode(show_imdb=imdb, show_tmdb=tmdb, show_tvdb='', season=int(season), episode=en, last_watched_at=now)
		else:
			meta = _cache.get(_tmdb.TVshows().get_showSeasons_meta, 96, tmdb)
			status = (meta.get('status') or '').lower() if meta else ''
			ended = status in ('ended', 'canceled', 'cancelled')
			last_ep = (meta.get('last_episode_to_air') or {}) if meta else {}
			last_aired_sn = int(last_ep.get('season_number', 0)) if last_ep else 0
			last_aired_ep = int(last_ep.get('episode_number', 0)) if last_ep else 0
			for s_item in (meta or {}).get('seasons', []):
				sn = int(s_item.get('season_number', 0))
				ec = int(s_item.get('episode_count', 0))
				if sn <= 0 or ec <= 0: continue
				# Same last-aired-boundary capping _fetchShowProgress() uses — episode_count
				# is the season's full *planned* count, not what's actually aired yet.
				if ended or not last_aired_sn or sn < last_aired_sn:
					cap = ec
				elif sn == last_aired_sn:
					cap = last_aired_ep if last_aired_ep > 0 else ec
				else:
					continue  # future/unaired season
				for en in range(1, cap + 1):
					floppysync.upsert_watched_episode(show_imdb=imdb, show_tmdb=tmdb, show_tvdb='', season=sn, episode=en, last_watched_at=now)
	except: log_utils.error()

def _watch_all_episodes_remote(tmdb, season=None):
	# Setting a show/season's 'status' to Completed does NOT itself mark its episodes
	# tracked on the server — confirmed via live testing, episode 'tracked' is a fully
	# separate per-episode record. So actually "watching" a whole show/season requires
	# hitting POST .../episodes/{n}/watch/ for every one of its episodes individually,
	# same as markEpisodeAsWatched does for a single episode. Episode numbers come from
	# TMDb season metadata since Floppy has no "list all episode numbers" shortcut.
	try:
		from resources.lib.database import cache as _cache
		from resources.lib.indexers import tmdb as _tmdb
		if season is not None:
			season_numbers = [int(season)]
		else:
			meta = _cache.get(_tmdb.TVshows().get_showSeasons_meta, 96, tmdb)
			season_numbers = [int(s.get('season_number', 0)) for s in (meta or {}).get('seasons', []) if s.get('season_number', 0) > 0]
		today = datetime.utcnow().strftime('%Y-%m-%d')
		for sn in season_numbers:
			raw = _cache.get(_tmdb.TVshows().get_season_request, 96, tmdb, sn)
			for ep in (raw or {}).get('episodes', []):
				en = ep.get('episode_number')
				if en is None: continue
				# Skip episodes that haven't aired yet — a "watch this whole show/season"
				# action was previously sending a real watch request to Floppy's own
				# server for every TMDb-listed episode regardless of air date, which for
				# a currently-airing season meant marking not-yet-released episodes
				# watched server-side. air_date is null for genuinely unannounced dates,
				# and compares fine as a plain 'YYYY-MM-DD' string otherwise.
				air_date = ep.get('air_date')
				if not air_date or air_date > today: continue
				getFloppy(_episode_watch_url(tmdb, sn, int(en)), post={}, method='POST', silent=True)
	except: log_utils.error()

def _sync_episode_tracking_for_show(imdb, tmdb):
	# Confirmed against a live Floppy instance (real Postman testing, not guesswork):
	# the per-episode 'tracked' flag on /media/tv/tmdb/{id}/{season}/episodes/ items is
	# NOT reliable — it read false for every episode of a season the web UI showed as
	# 10/10 watched. The real signal is each season's consumption HISTORY record: GET
	# /media/tv/tmdb/{id}/{season}/history/ returns entries with an integer 'progress'
	# field (how many episodes of that season have been watched, sequential from
	# episode 1 — e.g. progress=6 means episodes 1-6), which matched the web UI exactly
	# in testing (season 2 progress=6 of 9; show-level progress=16 = 10+6 across both
	# seasons). This mirrors the same sequential-progress model already used for every
	# other provider's season/episode indicators.
	# Returns None on a hard API/network failure (caller should consider a fallback),
	# or an int count of watched episodes actually written (0 is a legitimate,
	# successful result — e.g. a show the user hasn't actually watched any of yet).
	try:
		detail = getFloppyAsJson(_tv_url(tmdb), silent=True)
		if detail is None: return None
		seasons = (detail.get('related') or {}).get('seasons') or []
		now = _now_iso()
		tracked_count = 0
		for s in seasons:
			# Each season is independent: one season's request/parse failure (e.g. a
			# Season 0 "Specials" entry with no real history, or any other per-season
			# quirk) must not abort the whole show and wipe out seasons that would
			# otherwise have synced fine.
			try:
				s_item = s.get('item') or {}
				s_num = s_item.get('season_number')
				if s_num is None: continue
				history = get_all_pages('/media/tv/tmdb/%s/%s/history/' % (tmdb, s_num), silent=True) or []
				if not history: continue
				progress = max((int(h.get('progress') or 0) for h in history), default=0)
				if progress <= 0: continue
				last = max((h.get('progressed_at') or h.get('created') or '' for h in history), default=now) or now
				for en in range(1, progress + 1):
					tracked_count += 1
					floppysync.upsert_watched_episode(show_imdb=imdb, show_tmdb=tmdb, show_tvdb='', season=int(s_num), episode=en, last_watched_at=last)
			except:
				log_utils.log('FLOPPY: episode sync failed for TMDB=%s season=%s' % (tmdb, s.get('item', {}).get('season_number')), level=log_utils.LOGWARNING)
				log_utils.error()
		return tracked_count
	except:
		log_utils.error()
		return None

def _sync_watched_episodes_from_shows(progress_callback=None):
	# Floppy has no confirmed global "episode watch history" endpoint, so this is the
	# only way watched-episode state ever reaches Umbrella for shows tracked/marked
	# directly through Floppy itself (rather than marked from within Umbrella, which
	# already upserts individual episodes live via markEpisodeAsWatched).
	try:
		floppysync.delete_floppy_tables(('floppy_watched_episodes',))
		# Any status besides Planning (0) can have real watch history behind it — e.g. a
		# show paused between seasons (On Hold) or one the user stopped on (Dropped)
		# might still have episodes actually watched. Only querying Completed/Watching
		# meant shows sitting in any other status showed up as completely unwatched
		# regardless of real history.
		shows = (_fetch_status_bucket('tv', STATUS_COMPLETED) + _fetch_status_bucket('tv', STATUS_WATCHING)
			+ _fetch_status_bucket('tv', STATUS_ONHOLD) + _fetch_status_bucket('tv', STATUS_DROPPED))
		total = len(shows)
		total_tracked, failed_shows = 0, 0
		for idx, i in enumerate(shows):
			item = i.get('item') or {}
			tmdb = str(item.get('media_id') or '')
			if tmdb:
				imdb = _resolve_tv_imdb(tmdb)
				result = _sync_episode_tracking_for_show(imdb, tmdb)
				if result is None:
					failed_shows += 1
					if i.get('status') == STATUS_COMPLETED:
						# Hard API/network failure, not "genuinely no tracked episodes" —
						# fall back to the TMDb-based assumption so a Completed show doesn't
						# end up with zero local data on a transient error.
						_mark_all_episodes_watched_locally(imdb, tmdb, season=None)
				else:
					total_tracked += result
			if progress_callback:
				try: progress_callback('Syncing watched shows', idx + 1, total)
				except: pass
		log_utils.log('FLOPPY: episode sync — %s shows checked, %s tracked episodes found, %s shows failed to query' % (len(shows), total_tracked, failed_shows), level=log_utils.LOGINFO)
	except: log_utils.error()

def sync_watchedProgress(activities=None, forced=False, progress_callback=None):
	try:
		if not getFloppyCredentialsInfo(): return
		items = _fetch_status_bucket('movie', STATUS_COMPLETED)
		floppysync.delete_floppy_tables(('floppy_watched_movies',))
		total = len(items)
		resolved, unresolved = 0, 0
		for idx, i in enumerate(items):
			item = i.get('item') or {}
			tmdb = str(item.get('media_id') or '')
			if tmdb:
				imdb = _resolve_movie_imdb(tmdb)
				if imdb: resolved += 1
				else: unresolved += 1
				floppysync.upsert_watched_movie(imdb=imdb, tmdb=tmdb, title=item.get('title', ''), last_watched_at=i.get('progressed_at') or i.get('created_at') or _now_iso())
			if progress_callback:
				try: progress_callback('Syncing watched movies', idx + 1, total)
				except: pass
		log_utils.log('FLOPPY: movie sync — %s completed movies, %s resolved to imdb, %s could not be resolved' % (len(items), resolved, unresolved), level=log_utils.LOGINFO)
		_sync_watched_episodes_from_shows(progress_callback=progress_callback)
		floppysync.update_last_watched_at('last_history_at')
		# getShowProgress()/syncSeasons() are cached per-show (keyed on tmdb/imdb+tvdb) on
		# top of this — clearing only the two no-arg syncMovies/syncTVShows keys left every
		# already-viewed show's per-season progress (15 min) and cachesyncSeasons() (12 hr)
		# entries pointing at pre-sync data, so a show could show fully watched one level
		# down (season/episode lists recompute live) while the show-list widget kept
		# reporting stale remaining-episode counts for hours. Wipe the whole cache table
		# instead so every indicator recomputes against the just-synced data.
		floppysync.clear_cache()
		control.trigger_widget_refresh()
	except: log_utils.error()

def sync_watched(activities=None, forced=False, progress_callback=None):
	sync_watchedProgress(activities=activities, forced=forced, progress_callback=progress_callback)

def sync_watch_list(activities=None, forced=False):
	# Pulls all 5 status buckets (not just Planning) so every My Movies/My TV Shows
	# Floppy submenu list (Watchlist/Watching/On Hold/Completed/Dropped) is populated.
	try:
		if not getFloppyCredentialsInfo(): return
		for status, (mv_table, tv_table) in _STATUS_TABLES.items():
			floppysync.insert_status_list(_fetch_status_bucket('movie', status), mv_table)
			floppysync.insert_status_list(_fetch_status_bucket('tv', status), tv_table)
	except: log_utils.error()

def sync_collection(activities=None, forced=False):
	try:
		if not getFloppyCredentialsInfo(): return
		items = get_all_pages('/collection/?item_media_type=movie', silent=True) or []
		floppysync.insert_status_list([{'id': i.get('item', {}).get('id'), 'item': i.get('item'), 'score': None, 'created_at': i.get('collected_at')} for i in items], 'movies_collection')
		items = get_all_pages('/collection/?item_media_type=tv', silent=True) or []
		floppysync.insert_status_list([{'id': i.get('item', {}).get('id'), 'item': i.get('item'), 'score': None, 'created_at': i.get('collected_at')} for i in items], 'shows_collection')
	except: log_utils.error()

def get_collection_entries(media_type='movie'):
	# DELETE /collection/{entry_id}/ (see remove_from_collection()) is keyed on the
	# collection entry's own id, not the tracked media item's id — sync_collection()
	# only ever caches the nested item id (floppysync's generic status-bucket schema has
	# no column for a second id), so the Collection Manager needs its own live fetch that
	# keeps both ids straight rather than reading from that cache.
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
	# GET /playback/progress/ genuinely exists and works (confirmed live against a real
	# instance — the comment this replaced was based on earlier, incomplete API research).
	# Mirrors trakt.py's sync_playbackProgress()/traktsync.insert_bookmarks(): pull the
	# full server-side in-progress list and fully replace the local bookmarks table with
	# it, rather than only ever writing what *this* device paused — so a second device
	# can see a resume point another device left on Floppy's server.
	try:
		if not getFloppyCredentialsInfo(): return
		items = get_all_pages('/playback/progress/', silent=True) or []
		floppysync.clear_bookmarks()
		for item in items:
			try:
				if item.get('completed'): continue
				ids = item.get('ids') or {}
				duration = item.get('duration_seconds') or 0
				position = item.get('position_seconds') or 0
				if not duration: continue
				percent_played = str(round((position / duration) * 100, 2))
				paused_at = item.get('updated_at') or _now_iso()
				tmdb = str(ids.get('tmdb') or item.get('media_id') or '')
				imdb = str(ids.get('imdb') or '')
				if item.get('media_type') == 'movie':
					floppysync.upsert_bookmark(title=item.get('title', ''), imdb=imdb, tmdb=tmdb,
						percent_played=percent_played, paused_at=paused_at)
				elif item.get('media_type') == 'episode':
					season, episode = item.get('season_number'), item.get('episode_number')
					if season is None or episode is None: continue
					tvdb = str(ids.get('tvdb') or '')
					floppysync.upsert_bookmark(tvshowtitle=item.get('series_title', ''), title=item.get('title', ''), imdb=imdb,
						tmdb=tmdb, tvdb=tvdb, season=str(season), episode=str(episode),
						percent_played=percent_played, paused_at=paused_at)
			except: log_utils.error()
	except: log_utils.error()

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
	try:
		clr_tables = ('floppy_watched_movies', 'floppy_watched_episodes',
			'movies_plantowatch', 'shows_plantowatch', 'movies_watching', 'shows_watching',
			'movies_hold', 'shows_hold', 'movies_completed', 'shows_completed',
			'movies_dropped', 'shows_dropped', 'movies_collection', 'shows_collection')
		floppysync.delete_floppy_tables(clr_tables)
		_progress('Syncing watchlist/watching/on-hold/etc')
		sync_watch_list(forced=True)
		_progress('Syncing collection')
		sync_collection(forced=True)
		sync_watchedProgress(forced=True, progress_callback=_progress)
	finally:
		dialog.close()
	control.notification(title='Floppy', message='Forced Floppy Sync Complete')


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
	# The tv-detail response's nested season progress isn't confirmed reliable
	# enough to trust for per-season total/watched/unwatched counts, so this is
	# computed locally from floppysync's tracked-episode table plus TMDb season
	# metadata, mirroring customtrakt.py's _local_syncSeasons fallback exactly.
	try:
		# Trakt's equivalent (trakt.py syncSeasons) queries with specials=false by default
		# and only includes season 0 when the user has 'tv.specials' enabled — this had no
		# equivalent here, so Season 0/Specials (which almost nobody tracks watched episodes
		# for) was always being added below as a fully-unwatched season, permanently
		# preventing otherwise-fully-watched shows from ever reading as complete. Confirmed
		# against a real account: 19 of 40 sampled "Completed" shows had this exact mismatch,
		# nearly all with Season 0 as the only zero-watched season.
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
		# Cap each season's total at TMDb's last-aired boundary — an announced-but-
		# unreleased future season otherwise inflates 'total' past what's actually
		# aired (same fix applied to simkl.py's syncSeasons()).
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
					# sn > last_aired_sn: future/unaired season — omit
		except: pass
		if not season_counts and not by_season: return [[], {}]
		result_counts = {}
		fully_watched = []
		for s, watched_eps in by_season.items():
			total = season_counts.get(s, len(set(watched_eps)))
			watched = len(set(watched_eps))
			result_counts[s] = {'total': total, 'watched': watched, 'unwatched': max(total - watched, 0)}
			if watched >= total: fully_watched.append(s)
		# Include aired seasons with no tracked episodes at all — otherwise a show
		# with zero watched episodes reports an empty counts dict instead of 0/total,
		# leaving the "WatchedEpisodes" property unset (blank "/total" in the skin)
		# where Trakt/MDBList/Custom would show "0/total".
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
		control.hide()
		select = control.selectDialog([i[0] for i in items], heading=control.addonInfo('name') + ' - Floppy')
		if select == -1: return
		action_key = items[select][1]
		if action_key == 'watch':
			watch(content_type, name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=refresh)
		elif action_key == 'unwatch':
			unwatch(content_type, name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=refresh)
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
	except: log_utils.error()
