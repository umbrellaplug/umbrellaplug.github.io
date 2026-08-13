# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""
# Scrob (self-hosted media tracker, github.com/ellite/scrob).

from datetime import datetime
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urljoin, urlencode, quote_plus
from json import dumps as jsdumps
from resources.lib.database import scrobsync
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

scrob_icon = control.joinPath(control.artPath(), 'scrob.png')
_last_request_time = 0.0


def scrobBaseUrl():
	url = getSetting('scrob.baseurl').strip()
	if url and not url.startswith(('http://', 'https://')): url = 'https://' + url
	url = url.rstrip('/')
	if url and not url.endswith('/api/proxy'): url = url + '/api/proxy'
	return url


def getScrobCredentialsInfo():
	return bool(scrobBaseUrl() and getSetting('scrob.apikey'))


def getScrobWriteCredentialsInfo():
	return bool(getScrobCredentialsInfo() and getSetting('scrob.username') and getSetting('scrob.password'))


def getScrobIndicatorsInfo():
	return getSetting('indicators.alt') == '6'


#### Core request ####

def getScrob(url, post=None, method=None, auth='api_key', silent=False, _retried=False):
	
	try:
		global _last_request_time
		base = scrobBaseUrl()
		if not base: return None
		token = None
		if auth == 'jwt':
			token = _getScrobJWT()
			if not token: return None
		if time.time() - _last_request_time > 300:
			session.close()
		full_url = url if url.startswith(base) else urljoin(base + '/', url.lstrip('/'))
		req_headers = dict(headers)
		
		sep = '&' if '?' in full_url else '?'
		request_url = full_url + sep + 'api_key=' + quote_plus(getSetting('scrob.apikey'))
		if auth == 'jwt':
			req_headers['Authorization'] = 'Bearer %s' % token
		body = jsdumps(post) if post is not None else None
		if not method: method = 'POST' if post is not None else 'GET'
		method = method.upper()
		for _attempt in range(2):
			try:
				if method == 'POST':
					response = session.post(request_url, data=body, headers=req_headers, timeout=20)
				elif method == 'PATCH':
					response = session.patch(request_url, data=body, headers=req_headers, timeout=20)
				elif method == 'DELETE':
					response = session.delete(request_url, headers=req_headers, timeout=20)
				else:
					response = session.get(request_url, headers=req_headers, timeout=20)
				_last_request_time = time.time()
				break
			except requests.exceptions.ConnectionError:
				if _attempt == 0:
					log_utils.log('SCROB: connection reset, retrying with fresh connection...', level=log_utils.LOGDEBUG)
					session.close()
				else:
					raise
		status_code = response.status_code
		if status_code == 429:
			if 'Retry-After' in response.headers:
				throttleTime = response.headers['Retry-After']
				control.sleep((int(throttleTime) + 1) * 1000)
				return getScrob(url, post=post, method=method, auth=auth, silent=silent, _retried=_retried)
		if status_code == 401:
			if auth == 'jwt' and not _retried:
				setSetting('scrob.accesstoken', '')
				setSetting('scrob.tokenexpiry', '')
				return getScrob(url, post=post, method=method, auth=auth, silent=silent, _retried=True)
			if not silent: log_utils.log_force('SCROB: request unauthorized url=%s' % url, level=log_utils.LOGWARNING)
		elif status_code >= 500 and not silent:
			log_utils.log('SCROB: temporary server problem: %s url=%s' % (status_code, url), level=log_utils.LOGINFO)
		return response
	except Exception as e:
		if not silent: log_utils.log_force('SCROB: getScrob exception url=%s error=%s' % (url, e), level=log_utils.LOGWARNING)
		return None


def getScrobAsJson(url, post=None, method=None, auth='api_key', silent=False):
	try:
		response = getScrob(url, post=post, method=method, auth=auth, silent=silent)
		if response is None or response.status_code not in (200, 201): return None
		return response.json()
	except Exception as e:
		if not silent: log_utils.log('SCROB: Error in getScrobAsJson: %s' % str(e), level=log_utils.LOGWARNING)
		return None


def get_all_pages(url, silent=False):
	# GET /history's confirmed response shape: {'page','page_size','total_results','total_pages','results':[...]}
	try:
		sep = '&' if '?' in url else '?'
		page = 1
		page_size = 100
		results = []
		while True:
			page_url = url + sep + 'page=%d&page_size=%d' % (page, page_size)
			data = getScrobAsJson(page_url, auth='api_key', silent=silent)
			if not data: break
			page_results = data.get('results', []) if isinstance(data, dict) else data
			if not page_results: break
			results.extend(page_results)
			total_pages = data.get('total_pages') if isinstance(data, dict) else None
			if total_pages is not None:
				if page >= total_pages: break
			elif len(page_results) < page_size:
				break
			page += 1
			if page > 1000:
				log_utils.log('SCROB: get_all_pages reached safety limit for URL: %s' % url, level=log_utils.LOGWARNING)
				break
		return results
	except Exception as e:
		log_utils.log('SCROB: Error in get_all_pages: %s' % str(e), level=log_utils.LOGWARNING)
		return None


#### JWT session management (obtained via username+password login; no refresh endpoint exists server-side) ####

def _getScrobJWT():
	try:
		token = getSetting('scrob.accesstoken')
		expiry = getSetting('scrob.tokenexpiry')
		if token and expiry:
			try:
				if int(expiry) - 300 > int(time.time()): return token
			except: pass
		return _scrobLogin(silent=True)
	except:
		log_utils.error()
		return None


def _scrobLogin(silent=False):
	# POST /auth/login (form-encoded username+password).
	try:
		username = getSetting('scrob.username')
		password = getSetting('scrob.password')
		if not username or not password: return None
		base = scrobBaseUrl()
		if not base: return None
		login_url = urljoin(base + '/', 'auth/login') + '?api_key=' + quote_plus(getSetting('scrob.apikey'))
		req_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
		body = urlencode({'username': username, 'password': password})
		try:
			response = session.post(login_url, data=body, headers=req_headers, timeout=20)
		except Exception as e:
			if not silent: log_utils.log('SCROB: login request failed: %s' % str(e), level=log_utils.LOGWARNING)
			return None
		if response.status_code != 200:
			if not silent: control.notification(title='Scrob', message='Scrob login failed - check username/password', icon=scrob_icon)
			log_utils.log('SCROB: login failed HTTP %s' % response.status_code, level=log_utils.LOGWARNING)
			return None
		try:
			data = response.json()
		except ValueError:
			if not silent:
				control.notification(title='Scrob', message='Scrob login got an unreadable response — unwatch/lists unavailable', icon=scrob_icon)
			log_utils.log('SCROB: login HTTP 200 but response body was not valid JSON (url=%s) - is this instance reachable at the standard /api/proxy path?' % login_url, level=log_utils.LOGWARNING)
			return None
		if data.get('requires_2fa'):
			if not silent:
				control.dialog.ok('Scrob', 'This Scrob account has two-factor authentication enabled. Umbrella cannot complete a 2FA login, so username/password-only features (mark unwatched, list management) will not be available. Scrobbling, watched history, and marking items watched will still work normally via the API key.')
			log_utils.log('SCROB: account has 2FA enabled - JWT features unavailable', level=log_utils.LOGWARNING)
			return None
		token = data.get('access_token')
		if not token: return None
		setSetting('scrob.accesstoken', token)
		# Renew a bit before the real 1-week server-side expiry so a near-boundary
		# call doesn't race a token that's about to be rejected.
		setSetting('scrob.tokenexpiry', str(int(time.time()) + 7 * 24 * 60 * 60 - 3600))
		return token
	except:
		log_utils.error()
		return None


#### Auth / revoke (settings entry points, called from router.py) ####

def scrobAuth(fromSettings=0):
	try:
		base = scrobBaseUrl()
		apikey = getSetting('scrob.apikey')
		if not base or not apikey:
			if fromSettings == 1: control.openSettings('5.7', 'plugin.video.umbrella')
			control.notification(message='Enter a Scrob server URL and API key first', icon=scrob_icon)
			return False
		response = getScrob('/history?page=1&page_size=1', method='GET', auth='api_key', silent=True)
		if not response or response.status_code != 200:
			control.notification(message='Scrob Authorization Error - Check URL/API Key', icon=scrob_icon)
			if fromSettings == 1: control.openSettings('5.7', 'plugin.video.umbrella')
			return False
		setSetting('scrob.isauthed', 'true')
		control.notification(message='Scrob Authorized Successfully', icon=scrob_icon)
		if getSetting('scrob.username') and getSetting('scrob.password'):
			_scrobLogin(silent=False)
		else:
			# Explicit heads-up (not just a toast) about the two-tier auth model, since
			# the API key alone quietly can't unwatch anything or manage lists — surfaced
			# proactively here rather than discovered later as a missing menu entry.
			control.dialog.ok('Scrob', 'Scrob is connected for scrobbling, watched history, and marking items watched. To also mark items unwatched and manage lists, enter your Scrob username and password in settings (optional).')
		if fromSettings == 1: control.openSettings('5.7', 'plugin.video.umbrella')
		if not control.yesnoDialog('Do you want to set Scrob as your service for your watched and unwatched indicators?', '', '', 'Indicators', 'No', 'Yes'): return True
		control.homeWindow.setProperty('umbrella.updateSettings', 'false')
		setSetting('indicators.alt', '6')
		setSetting('scrobble.source', '6')
		control.homeWindow.setProperty('umbrella.updateSettings', 'true')
		setSetting('scrobble', 'Scrob')
		setSetting('indicators', 'Scrob')
		control.notification(message='Scrob Indicators Enabled - Syncing Watched Data...')
		from threading import Thread
		Thread(target=sync_watched, kwargs={'forced': True}).start()
		return True
	except:
		log_utils.error()
		return False


def scrobRevoke(fromSettings=0):
	control.homeWindow.setProperty('umbrella.updateSettings', 'false')
	setSetting('scrob.username', '')
	setSetting('scrob.password', '')
	setSetting('scrob.apikey', '')
	setSetting('scrob.accesstoken', '')
	setSetting('scrob.tokenexpiry', '')
	setSetting('scrob.isauthed', '')
	control.homeWindow.setProperty('umbrella.updateSettings', 'true')
	try:
		scrobsync.delete_scrob_tables(('bookmarks', 'scrob_watched_movies', 'scrob_watched_episodes', 'scrob_lists'))
		if getSetting('indicators.alt') == '6':
			setSetting('indicators.alt', '0')
			setSetting('indicators', 'Local')
		if getSetting('scrobble.source') == '6':
			setSetting('scrobble.source', '0')
			setSetting('scrobble', 'Local')
		setSetting('scrob.markwatched', 'false')
		if fromSettings == 1:
			control.openSettings('5.7', 'plugin.video.umbrella')
			control.dialog.ok('Scrob', 'Scrob Authorization Revoked')
	except:
		log_utils.error()


#### TMDb id resolution (Scrob is TMDB-native; Umbrella calls into these with imdb/tvdb) ####

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

def _resolve_movie_imdb(tmdb):
	# Scrob never hands back an imdb id anywhere in its API — reverse-resolve it via
	# TMDb so getMovieOverlay()'s imdb-keyed matching (shared with every other
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


def _now_iso():
	return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')


#### Mark watched — API-key-only, via a Kodi scrobble webhook payload ####

def _webhook_event(method, media_type, imdb='', tmdb='', tvdb='', title='', tvshowtitle='', year='0', season=None, episode=None, time_seconds=0, total_seconds=0, end=None):
	try:
		unique_id = {}
		if tmdb: unique_id['tmdb'] = str(tmdb)
		if imdb: unique_id['imdb'] = str(imdb)
		if tvdb: unique_id['tvdb'] = str(tvdb)
		item = {'type': media_type, 'uniqueid': unique_id, 'title': title}
		if media_type == 'movie':
			try: item['year'] = int(year) if year else None
			except: item['year'] = None
		else:
			item['showtitle'] = tvshowtitle or title
			item['season'] = int(season) if season is not None else None
			item['episode'] = int(episode) if episode is not None else None
		total = total_seconds or 1
		body = {'method': method, 'item': item,
			'player': {'time': _hms(time_seconds), 'totaltime': _hms(total)}}
		if method == 'Player.OnStop':
			body['params'] = {'data': {'end': bool(end)}}
		return getScrob('/webhooks/kodi', post=body, method='POST', auth='api_key', silent=True)
	except:
		log_utils.error()
		return None

def _hms(secs):
	secs = max(0, int(secs or 0))
	return {'hours': secs // 3600, 'minutes': (secs % 3600) // 60, 'seconds': secs % 60}

def _webhook_mark_watched(media_type, imdb='', tmdb='', tvdb='', title='', tvshowtitle='', year='0', season=None, episode=None):
	response = _webhook_event('Player.OnStop', media_type, imdb=imdb, tmdb=tmdb, tvdb=tvdb, title=title, tvshowtitle=tvshowtitle, year=year, season=season, episode=episode, time_seconds=1, total_seconds=1, end=True)
	return bool(response is not None and response.status_code in (200, 201))


def markMovieAsWatched(imdb, tmdb=''):
	try:
		if not tmdb: tmdb = _resolve_tmdb('movie', imdb=imdb)
		if not tmdb:
			log_utils.log('SCROB: markMovieAsWatched IMDB=%s aborted — could not resolve a tmdb id' % imdb, level=log_utils.LOGWARNING)
			return False
		success = _webhook_mark_watched('movie', imdb=imdb, tmdb=tmdb)
		if success:
			scrobsync.upsert_watched_movie(imdb=imdb or '', tmdb=str(tmdb), last_watched_at=_now_iso())
			scrobsync.cache_delete(scrobsync._hash_function(syncMovies, ()))
		if getSetting('debug.level') == '1':
			log_utils.log('SCROB: markMovieAsWatched IMDB=%s TMDB=%s Result=%s' % (imdb, tmdb, success), level=log_utils.LOGDEBUG)
		return success
	except:
		log_utils.error()
		return False

def markEpisodeAsWatched(imdb, tvdb, season, episode):
	try:
		tmdb = _resolve_tmdb('tv', imdb=imdb, tvdb=tvdb)
		if not tmdb: return False
		season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
		success = _webhook_mark_watched('episode', imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode)
		if success:
			scrobsync.upsert_watched_episode(show_imdb=imdb or '', show_tmdb=tmdb, show_tvdb=str(tvdb or ''), season=season, episode=episode, last_watched_at=_now_iso())
			scrobsync.cache_delete(scrobsync._hash_function(syncTVShows, ()))
			scrobsync.cache_delete(scrobsync._hash_function(_fetchShowProgress, (tmdb,)))
		if getSetting('debug.level') == '1':
			log_utils.log('SCROB: markEpisodeAsWatched IMDB=%s TMDB=%s S%02dE%02d Result=%s' % (imdb, tmdb, season, episode, success), level=log_utils.LOGDEBUG)
		return success
	except:
		log_utils.error()
		return False

def _webhook_mark_all_episodes(tmdb, tvdb='', imdb='', season=None):
	try:
		from resources.lib.database import cache as _cache
		from resources.lib.indexers import tmdb as _tmdb
		if season is not None:
			season_numbers = [int(season)]
		else:
			meta = _cache.get(_tmdb.TVshows().get_showSeasons_meta, 96, tmdb)
			season_numbers = [int(s.get('season_number', 0)) for s in (meta or {}).get('seasons', []) if s.get('season_number', 0) > 0]
		any_success = False
		now = _now_iso()
		for sn in season_numbers:
			raw = _cache.get(_tmdb.TVshows().get_season_request, 96, tmdb, sn)
			for ep in (raw or {}).get('episodes', []):
				en = ep.get('episode_number')
				if en is None: continue
				if _webhook_mark_watched('episode', imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=sn, episode=int(en)):
					any_success = True
					scrobsync.upsert_watched_episode(show_imdb=imdb or '', show_tmdb=tmdb, show_tvdb=str(tvdb or ''), season=sn, episode=int(en), last_watched_at=now)
		return any_success
	except:
		log_utils.error()
		return False

def markTVShowAsWatched(imdb, tvdb):
	try:
		tmdb = _resolve_tmdb('tv', imdb=imdb, tvdb=tvdb)
		if not tmdb: return False
		if getScrobWriteCredentialsInfo():
			response = getScrob('/history/show-all', post={'series_tmdb_id': int(tmdb), 'series_tvdb_id': int(tvdb) if tvdb else None}, method='POST', auth='jwt', silent=True)
			success = bool(response is not None and response.status_code in (200, 201))
			if success: _sync_episodes_for_show_locally(imdb, tmdb, season=None)
		else:
			success = _webhook_mark_all_episodes(tmdb, tvdb=tvdb, imdb=imdb, season=None)
		if success:
			scrobsync.cache_delete(scrobsync._hash_function(syncTVShows, ()))
			scrobsync.cache_delete(scrobsync._hash_function(_fetchShowProgress, (tmdb,)))
		return success
	except:
		log_utils.error()
		return False

def markSeasonAsWatched(imdb, tvdb, season):
	try:
		tmdb = _resolve_tmdb('tv', imdb=imdb, tvdb=tvdb)
		if not tmdb: return False
		season = int('%01d' % int(season))
		if getScrobWriteCredentialsInfo():
			response = getScrob('/history/season', post={'series_tmdb_id': int(tmdb), 'series_tvdb_id': int(tvdb) if tvdb else None, 'season_number': season}, method='POST', auth='jwt', silent=True)
			success = bool(response is not None and response.status_code in (200, 201))
			if success: _sync_episodes_for_show_locally(imdb, tmdb, season=season)
		else:
			success = _webhook_mark_all_episodes(tmdb, tvdb=tvdb, imdb=imdb, season=season)
		if success:
			scrobsync.cache_delete(scrobsync._hash_function(syncTVShows, ()))
			scrobsync.cache_delete(scrobsync._hash_function(_fetchShowProgress, (tmdb,)))
		return success
	except:
		log_utils.error()
		return False

def _sync_episodes_for_show_locally(imdb, tmdb, season=None):
	# After a server-side JWT bulk mark-watched, write matching local rows immediately
	# so indicators update without waiting for the next full sync pass.
	try:
		from resources.lib.database import cache as _cache
		from resources.lib.indexers import tmdb as _tmdb
		now = _now_iso()
		meta = _cache.get(_tmdb.TVshows().get_showSeasons_meta, 96, tmdb)
		if not meta: return
		status = (meta.get('status') or '').lower()
		ended = status in ('ended', 'canceled', 'cancelled')
		last_ep = meta.get('last_episode_to_air') or {}
		last_aired_sn = int(last_ep.get('season_number', 0)) if last_ep else 0
		last_aired_ep = int(last_ep.get('episode_number', 0)) if last_ep else 0
		season_caps = {}
		for s_item in meta.get('seasons', []):
			sn = s_item.get('season_number')
			if sn is None or sn <= 0: continue
			ec = int(s_item.get('episode_count', 0))
			if ended or not last_aired_sn or sn < last_aired_sn:
				season_caps[sn] = ec
			elif sn == last_aired_sn:
				season_caps[sn] = last_aired_ep if last_aired_ep > 0 else ec
			# sn > last_aired_sn: future/unaired season — omit entirely
		seasons_to_write = [season] if season is not None else list(season_caps.keys())
		for sn in seasons_to_write:
			sn = int(sn)
			cap = season_caps.get(sn, 0)
			if cap <= 0: continue
			for en in range(1, cap + 1):
				scrobsync.upsert_watched_episode(show_imdb=imdb, show_tmdb=tmdb, show_tvdb='', season=sn, episode=en, last_watched_at=now)
	except: log_utils.error()


#### Mark unwatched / season / show unwatched — JWT-only, no fallback ####


def markMovieAsNotWatched(imdb, tmdb=''):
	try:
		if not getScrobWriteCredentialsInfo():
			log_utils.log('SCROB: unwatch requires a Scrob username/password (JWT) — API key alone cannot unwatch', level=log_utils.LOGWARNING)
			return False
		if not tmdb: tmdb = _resolve_tmdb('movie', imdb=imdb)
		if not tmdb: return False
		response = getScrob('/history/item?tmdb_id=%s&media_type=movie' % tmdb, method='DELETE', auth='jwt', silent=True)
		success = bool(response is not None and response.status_code in (200, 204))
		if success:
			scrobsync.delete_watched_movie(tmdb)
			scrobsync.cache_delete(scrobsync._hash_function(syncMovies, ()))
		return success
	except:
		log_utils.error()
		return False

def markEpisodeAsNotWatched(imdb, tvdb, season, episode):
	try:
		if not getScrobWriteCredentialsInfo():
			log_utils.log('SCROB: unwatch requires a Scrob username/password (JWT) — API key alone cannot unwatch', level=log_utils.LOGWARNING)
			return False
		tmdb = _resolve_tmdb('tv', imdb=imdb, tvdb=tvdb)
		if not tmdb: return False
		season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
		response = getScrob('/history/item?tmdb_id=%s&media_type=episode' % tmdb, method='DELETE', auth='jwt', silent=True)
		success = bool(response is not None and response.status_code in (200, 204))
		if success:
			scrobsync.delete_watched_episode(tmdb, season, episode)
			scrobsync.cache_delete(scrobsync._hash_function(syncTVShows, ()))
			scrobsync.cache_delete(scrobsync._hash_function(_fetchShowProgress, (tmdb,)))
		return success
	except:
		log_utils.error()
		return False

def markTVShowAsNotWatched(imdb, tvdb):
	try:
		if not getScrobWriteCredentialsInfo():
			log_utils.log('SCROB: unwatch requires a Scrob username/password (JWT) — API key alone cannot unwatch', level=log_utils.LOGWARNING)
			return False
		tmdb = _resolve_tmdb('tv', imdb=imdb, tvdb=tvdb)
		if not tmdb: return False

		response = getScrob('/history/show-all?series_tmdb_id=%s' % tmdb, method='DELETE', auth='jwt', silent=True)
		success = bool(response is not None and response.status_code in (200, 204))
		if success:
			for (si, st, sv, s, e) in scrobsync.get_watched_episodes():
				if st == tmdb: scrobsync.delete_watched_episode(st, s, e)
			scrobsync.cache_delete(scrobsync._hash_function(syncTVShows, ()))
			scrobsync.cache_delete(scrobsync._hash_function(_fetchShowProgress, (tmdb,)))
		return success
	except:
		log_utils.error()
		return False

def markSeasonAsNotWatched(imdb, tvdb, season):
	try:
		if not getScrobWriteCredentialsInfo():
			log_utils.log('SCROB: unwatch requires a Scrob username/password (JWT) — API key alone cannot unwatch', level=log_utils.LOGWARNING)
			return False
		tmdb = _resolve_tmdb('tv', imdb=imdb, tvdb=tvdb)
		if not tmdb: return False
		season = int('%01d' % int(season))
		response = getScrob('/history/season?series_tmdb_id=%s&season_number=%s' % (tmdb, season), method='DELETE', auth='jwt', silent=True)
		success = bool(response is not None and response.status_code in (200, 204))
		if success:
			for (si, st, sv, s, e) in scrobsync.get_watched_episodes():
				if st == tmdb and int(s) == season: scrobsync.delete_watched_episode(st, s, e)
			scrobsync.cache_delete(scrobsync._hash_function(syncTVShows, ()))
			scrobsync.cache_delete(scrobsync._hash_function(_fetchShowProgress, (tmdb,)))
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
	if getSetting('scrob.general.notifications') == 'true':
		if success is True: control.notification(title='Scrob', message='%s Marked as Watched on Scrob' % name)
		else: control.notification(title='Scrob', message='%s Failed to Mark as Watched on Scrob' % name)

def unwatch(content_type, name, imdb=None, tvdb=None, season=None, episode=None, refresh=True):
	control.busy()
	has_write = getScrobWriteCredentialsInfo()
	success = False
	if has_write:
		if content_type == 'movie': success = markMovieAsNotWatched(imdb)
		elif content_type == 'tvshow': success = markTVShowAsNotWatched(imdb, tvdb)
		elif content_type == 'season': success = markSeasonAsNotWatched(imdb, tvdb, season)
		elif content_type == 'episode': success = markEpisodeAsNotWatched(imdb, tvdb, season, episode)
	control.hide()
	if refresh: control.refresh()
	control.trigger_widget_refresh()
	if season and not episode: name = '%s-Season%s...' % (name, season)
	if season and episode: name = '%s-S%sxE%02d...' % (name, season, int(episode))
	if not has_write:
		control.notification(title='Scrob', message='Unwatch requires a Scrob username/password (see settings)')
	elif getSetting('scrob.general.notifications') == 'true':
		if success is True: control.notification(title='Scrob', message='%s Marked as Unwatched on Scrob' % name)
		else: control.notification(title='Scrob', message='%s Failed to Mark as Unwatched on Scrob' % name)


#### Scrobble — maps directly onto Kodi's own Player.On* event names, API-key-only ####
#### (local bookmarks are tracked client-side since Scrob has no queryable ####
#### server-side "in progress playback" list either) ####

def _scrobble_seconds(watched_percent, current_time, total_time):

	if total_time:
		return int(current_time or 0), int(total_time)
	return int(watched_percent), 100

def scrobbleStart(media_type, title='', tvshowtitle='', year='0', imdb='', tmdb='', tvdb='', season='', episode='', watched_percent=0, current_time=0, total_time=0, resumed=False):
	try:
		method = 'Player.OnResume' if resumed else 'Player.OnPlay'
		time_seconds, total_seconds = _scrobble_seconds(watched_percent, current_time, total_time)
		_webhook_event(method, 'movie' if media_type == 'movie' else 'episode', imdb=imdb, tmdb=tmdb, tvdb=tvdb, title=title, tvshowtitle=tvshowtitle, year=year, season=season or None, episode=episode or None, time_seconds=time_seconds, total_seconds=total_seconds)
	except: log_utils.error()

def scrobbleProgress(media_type, imdb='', tmdb='', tvdb='', season='', episode='', watched_percent=0, current_time=0, total_time=0):
	try:
		season = int('%01d' % int(season)) if season else None
		episode = int('%01d' % int(episode)) if episode else None
		time_seconds, total_seconds = _scrobble_seconds(watched_percent, current_time, total_time)
		_webhook_event('Player.OnAVChange', 'movie' if media_type == 'movie' else 'episode', imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, time_seconds=time_seconds, total_seconds=total_seconds)
	except: log_utils.error()

def scrobbleMovie(imdb, tmdb, watched_percent, current_time=0, total_time=0):
	try:
		time_seconds, total_seconds = _scrobble_seconds(watched_percent, current_time, total_time)
		response = _webhook_event('Player.OnPause', 'movie', imdb=imdb, tmdb=tmdb, time_seconds=time_seconds, total_seconds=total_seconds)
		if response is not None and response.status_code == 200:
			scrobsync.upsert_bookmark(title='', resume_id='', imdb=imdb or '', tmdb=str(tmdb or ''), percent_played=str(watched_percent), paused_at=_now_iso())
			control.trigger_widget_refresh()
	except: log_utils.error()

def scrobbleEpisode(imdb, tmdb, tvdb, season, episode, watched_percent, current_time=0, total_time=0):
	try:
		season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
		time_seconds, total_seconds = _scrobble_seconds(watched_percent, current_time, total_time)
		response = _webhook_event('Player.OnPause', 'episode', imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, time_seconds=time_seconds, total_seconds=total_seconds)
		if response is not None and response.status_code == 200:
			scrobsync.upsert_bookmark(tvshowtitle='x', title='', resume_id='', imdb=imdb or '', tmdb=str(tmdb or ''), tvdb=str(tvdb or ''), season=str(season), episode=str(episode), percent_played=str(watched_percent), paused_at=_now_iso())
			control.trigger_widget_refresh()
	except: log_utils.error()

def scrobbleStopMovie(imdb, tmdb, watched_percent, completed=False, current_time=0, total_time=0, already_watched=False):
	try:
		time_seconds, total_seconds = _scrobble_seconds(watched_percent, current_time, total_time)
		# already_watched means markMovieDuringPlayback() already recorded this as watched
		# mid-playback (see playcount.py, and _webhook_mark_watched() above — that call is
		# itself a fake Player.OnStop with end=True). Confirmed against Scrob's own server
		# source (routers/webhooks.py): the stop handler does NOT trust our end flag alone —
		# completed = data.get("ended") or progress_percent >= 0.90, independently derived
		# from whatever position/duration we send — so a real near-complete position with
		# end=False still computes completed=True and still writes a duplicate WatchEvent.
		# Sending an exact 0 doesn't help either: 0 is falsy, so the server's own
		# `data["progress_percent"] or session.progress_percent` falls back to the live
		# session's last heartbeat (kept high by our periodic scrobbleProgress calls) and
		# reintroduces the same false completion. A small but NON-ZERO ratio (truthy, so
		# that fallback never triggers) that's also under the server's 5% "still log
		# partial progress" floor avoids every trigger — the write_watch_event call never
		# happens at all — while _close_session() still runs unconditionally as the first
		# line of that handler, so the live "Now Playing" session still closes normally.
		if already_watched:
			time_seconds, total_seconds = 1, 60
		send_completed = bool(completed) and not already_watched
		response = _webhook_event('Player.OnStop', 'movie', imdb=imdb, tmdb=tmdb, time_seconds=time_seconds, total_seconds=total_seconds, end=send_completed)
		if getSetting('debug.level') == '1':
			log_utils.log('SCROB: scrobbleStopMovie IMDB=%s TMDB=%s Percent=%s SentPercent=%s Completed=%s AlreadyWatched=%s HTTP=%s' % (imdb, tmdb, watched_percent, round(time_seconds / total_seconds, 4) if total_seconds else 0, send_completed, already_watched, response.status_code if response is not None else 'None'), level=log_utils.LOGDEBUG)
		if response is not None and response.status_code == 200:
			if completed:
				scrobsync.delete_bookmark(imdb or '', tvdb='', tmdb=str(tmdb or ''), season='', episode='')
			else:
				scrobsync.upsert_bookmark(title='', resume_id='', imdb=imdb or '', tmdb=str(tmdb or ''), percent_played=str(watched_percent), paused_at=_now_iso())
			control.trigger_widget_refresh()
	except: log_utils.error()

def scrobbleStopEpisode(imdb, tmdb, tvdb, season, episode, watched_percent, completed=False, current_time=0, total_time=0, already_watched=False):
	try:
		season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
		time_seconds, total_seconds = _scrobble_seconds(watched_percent, current_time, total_time)
		# See scrobbleStopMovie() above for the full reasoning — the server independently
		# re-derives "completed" from position/duration regardless of the end flag, and
		# falls back to the live session's own tracked progress if we send an exact 0, so a
		# small non-zero ratio is what actually avoids a duplicate WatchEvent write.
		if already_watched:
			time_seconds, total_seconds = 1, 60
		send_completed = bool(completed) and not already_watched
		response = _webhook_event('Player.OnStop', 'episode', imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, time_seconds=time_seconds, total_seconds=total_seconds, end=send_completed)
		if getSetting('debug.level') == '1':
			log_utils.log('SCROB: scrobbleStopEpisode IMDB=%s TMDB=%s S%02dE%02d Percent=%s SentPercent=%s Completed=%s AlreadyWatched=%s HTTP=%s' % (imdb, tmdb, season, episode, watched_percent, round(time_seconds / total_seconds, 4) if total_seconds else 0, send_completed, already_watched, response.status_code if response is not None else 'None'), level=log_utils.LOGDEBUG)
		if response is not None and response.status_code == 200:
			if completed:
				scrobsync.delete_bookmark(imdb or '', tvdb=str(tvdb or ''), tmdb=str(tmdb or ''), season=str(season), episode=str(episode))
			else:
				scrobsync.upsert_bookmark(tvshowtitle='x', title='', resume_id='', imdb=imdb or '', tmdb=str(tmdb or ''), tvdb=str(tvdb or ''), season=str(season), episode=str(episode), percent_played=str(watched_percent), paused_at=_now_iso())
			control.trigger_widget_refresh()
	except: log_utils.error()

def scrobbleReset(imdb, tmdb=None, tvdb=None, season=None, episode=None, refresh=True, widgetRefresh=False, clear_local=True):
	if not getScrobCredentialsInfo(): return
	try:
		if clear_local: scrobsync.delete_bookmark(imdb or '', tvdb=tvdb or '', tmdb=str(tmdb or ''), season=season or '', episode=episode or '')
		if refresh: control.refresh()
		if widgetRefresh: control.trigger_widget_refresh()
	except: log_utils.error()


#### Ratings (bonus — works API-key-only, confirmed via the same webhook auth tier) ####

def rateMovie(tmdb, imdb, title, year, rating):
	try:
		body = {'media_type': 'movie', 'title': title, 'year': int(year) if year else None, 'tmdb_id': int(tmdb) if tmdb else None, 'imdb_id': imdb or None, 'rating': float(rating)}
		response = getScrob('/webhooks/kodi/rating', post=body, method='POST', auth='api_key', silent=True)
		return bool(response is not None and response.status_code in (200, 201))
	except:
		log_utils.error()
		return False

def rateEpisode(tmdb, tvdb, series_name, season, episode, rating):
	try:
		body = {'media_type': 'episode', 'series_name': series_name, 'season_number': int(season), 'episode_number': int(episode), 'tmdb_id': int(tmdb) if tmdb else None, 'tvdb_id': tvdb or None, 'rating': float(rating)}
		response = getScrob('/webhooks/kodi/rating', post=body, method='POST', auth='api_key', silent=True)
		return bool(response is not None and response.status_code in (200, 201))
	except:
		log_utils.error()
		return False


#### Sync ####

def _threaded_resolve(unique_ids, resolver):
	from threading import Thread
	result = {}
	def _one(tmdb_id):
		result[tmdb_id] = resolver(tmdb_id)
	threads = [Thread(target=_one, args=(t,)) for t in unique_ids]
	_unlimited = getSetting('dev.batch.unlimited') == 'true'
	_bs = max(int(getSetting('dev.batch.size') or '10'), 1)
	_chunk = max(len(threads), 1) if _unlimited else _bs
	for i in range(0, len(threads), _chunk):
		if control.monitor.abortRequested(): break
		batch = threads[i:i + _chunk]
		[t.start() for t in batch]
		[t.join() for t in batch]
	return result

def sync_watchedProgress(activities=None, forced=False, progress_callback=None):
	try:
		if not getScrobCredentialsInfo(): return
		movies = get_all_pages('/history?type=movie', silent=True) or []
		completed_movies = [item for item in movies if (item.get('media') or {}).get('tmdb_id') and item.get('completed')]
		unique_movie_tmdbs = list({str((item.get('media') or {}).get('tmdb_id')) for item in completed_movies})
		movie_imdb_map = _threaded_resolve(unique_movie_tmdbs, _resolve_movie_imdb)

		total = len(movies)
		resolved, unresolved = 0, 0
		movie_rows = []
		for idx, item in enumerate(movies):
			media = item.get('media') or {}
			tmdb = str(media.get('tmdb_id') or '')
			if tmdb and item.get('completed'):
				imdb = movie_imdb_map.get(tmdb, '')
				if imdb: resolved += 1
				else: unresolved += 1
				movie_rows.append((imdb, tmdb, media.get('title', ''), str(media.get('release_date', '') or '')[:4], item.get('watched_at') or _now_iso()))
			if progress_callback:
				try: progress_callback('Syncing watched movies', idx + 1, total)
				except: pass
		scrobsync.bulk_upsert_watched_movies(movie_rows)
		log_utils.log('SCROB: movie sync — %s completed movies, %s resolved to imdb, %s could not be resolved' % (len(movies), resolved, unresolved), level=log_utils.LOGINFO)

		episodes = get_all_pages('/history?type=episode', silent=True) or []
		completed_episodes = [item for item in episodes if item.get('completed') and (item.get('media') or {}).get('show_tmdb_id')
			and (item.get('media') or {}).get('season_number') is not None and (item.get('media') or {}).get('episode_number') is not None]
		unique_show_tmdbs = list({str((item.get('media') or {}).get('show_tmdb_id')) for item in completed_episodes})
		show_imdb_map = _threaded_resolve(unique_show_tmdbs, _resolve_tv_imdb)

		total = len(episodes)
		shows_seen = set()
		episode_rows = []
		for idx, item in enumerate(episodes):
			media = item.get('media') or {}
			show_tmdb = str(media.get('show_tmdb_id') or '')
			season = media.get('season_number')
			episode = media.get('episode_number')
			if show_tmdb and item.get('completed') and season is not None and episode is not None:
				shows_seen.add(show_tmdb)
				show_imdb = show_imdb_map.get(show_tmdb, '')
				show_tvdb = str(media.get('show_tvdb_id') or '')
				episode_rows.append((show_imdb, show_tmdb, show_tvdb, int(season), int(episode), item.get('watched_at') or _now_iso()))
			if progress_callback:
				try: progress_callback('Syncing watched shows', idx + 1, total)
				except: pass
		scrobsync.bulk_upsert_watched_episodes(episode_rows)
		log_utils.log('SCROB: episode sync — %s watched episodes across %s shows' % (len(episodes), len(shows_seen)), level=log_utils.LOGINFO)

		scrobsync.update_last_watched_at('last_history_at')
		scrobsync.clear_cache()
		control.trigger_widget_refresh()
	except: log_utils.error()

def sync_watched(activities=None, forced=False, progress_callback=None):
	sync_watchedProgress(activities=activities, forced=forced, progress_callback=progress_callback)

def sync_playbackProgress(activities=None, forced=False):
	# Mirrors trakt.py's sync_playbackProgress()/traktsync.insert_bookmarks(): pull the
	# full server-side in-progress list and fully replace the local bookmarks table with
	# it, rather than only ever writing what *this* device paused. Without this, a second
	# device had no way to see a resume point another device left on Scrob's server short
	# of the live per-item fallback query in Bookmarks.get() (get_resume_percent) — that
	# fallback only fires when the local table has nothing at all, so it stays in place as
	# a safety net for the gap between sync intervals, but this is now the primary path.
	try:
		if not getScrobCredentialsInfo(): return
		items = get_continue_watching()
		scrobsync.clear_bookmarks()
		for item in items:
			try:
				media = item.get('media') or {}
				media_type = media.get('type')
				percent_played = str(round((item.get('progress_percent') or 0) * 100, 2))
				paused_at = item.get('watched_at') or _now_iso()
				if media_type == 'movie':
					scrobsync.upsert_bookmark(title=media.get('title', ''), imdb='', tmdb=str(media.get('tmdb_id') or ''),
						percent_played=percent_played, paused_at=paused_at)
				elif media_type == 'episode':
					season, episode = media.get('season_number'), media.get('episode_number')
					if season is None or episode is None: continue
					scrobsync.upsert_bookmark(tvshowtitle=media.get('show_title', ''), title=media.get('title', ''), imdb='',
						tmdb=str(media.get('show_tmdb_id') or ''), tvdb='', season=str(season), episode=str(episode),
						percent_played=percent_played, paused_at=paused_at)
			except: log_utils.error()
	except: log_utils.error()

def force_scrobSync():
	if not control.yesnoDialog(control.lang(32056), '', ''): return
	dialog = control.progressDialog
	dialog.create(control.addonName(), 'Preparing Scrob sync...')
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
		scrobsync.delete_scrob_tables(('scrob_watched_movies', 'scrob_watched_episodes', 'scrob_lists'))
		sync_watchedProgress(forced=True, progress_callback=_progress)
		_progress('Syncing user lists')
		sync_user_lists(forced=True)
	finally:
		dialog.close()
	control.notification(title='Scrob', message='Forced Scrob Sync Complete')


#### Indicators (movies/shows watched state, seasons/episodes progress) ####

def syncMovies():
	try:
		if not getScrobCredentialsInfo(): return None
		return scrobsync.get_watched_movies() or []
	except:
		log_utils.error()
		return None

def watchedMovies():
	try:
		if not getScrobCredentialsInfo(): return None
		return scrobsync.get_watched_movies_full() or []
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
		if not getScrobCredentialsInfo(): return None
		episodes = scrobsync.get_watched_episodes()
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
		return scrobsync.get(_fetchShowProgress, 15, tmdb)
	except:
		log_utils.error()
		return None

def _fetchShowProgress(tmdb):
	# Computed locally from scrobsync's tracked-episode table plus TMDb season
	# metadata — same shape as floppy.py's _fetchShowProgress fallback.
	try:
		include_specials = getSetting('tv.specials') == 'true'
		episodes = scrobsync.get_watched_episodes()
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
		# unreleased future season otherwise inflates 'total' past what's actually aired.
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
		if not getScrobCredentialsInfo(): return None
		if not imdb and not tvdb: return None
		tmdb = _resolve_tmdb('tv', imdb=imdb, tvdb=tvdb)
		if not tmdb: return [[], {}]
		progress = getShowProgress(tmdb)
		return progress if progress else [[], {}]
	except:
		log_utils.error()
		return None

def getMoviesWatchedActivity():
	try: return scrobsync.last_sync('last_history_at')
	except: log_utils.error()
	return 0

def getEpisodesWatchedActivity():
	try: return scrobsync.last_sync('last_history_at')
	except: log_utils.error()
	return 0

def timeoutsyncMovies():
	return scrobsync.timeout(syncMovies)

def timeoutsyncTVShows():
	return scrobsync.timeout(syncTVShows)

def timeoutsyncSeasons(imdb, tvdb):
	try: return scrobsync.timeout(syncSeasons, imdb, tvdb, returnNone=True)
	except: log_utils.error()

def cachesyncMovies(timeout=720):
	try: return scrobsync.get(syncMovies, timeout)
	except: log_utils.error()

def cachesyncTVShows(timeout=720):
	try: return scrobsync.get(syncTVShows, timeout)
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
		return scrobsync.get(syncSeasons, timeout, imdb, tvdb)
	except: log_utils.error()

def seasonCount(imdb, tvdb):
	try:
		result = syncSeasons(imdb, tvdb)
		if result and len(result) > 1: return result[1]
		return {}
	except: log_utils.error()


#### Continue-watching / next-up — real server-side support, simpler than Floppy's local reconstruction ####

def get_continue_watching():
	try:
		if not getScrobCredentialsInfo(): return []
		data = getScrobAsJson('/history/continue-watching', auth='api_key', silent=True)
		return (data or {}).get('continue_watching', []) if isinstance(data, dict) else []
	except:
		log_utils.error()
		return []

def get_resume_percent(tmdb, season=None, episode=None):
	# Local bookmarks (scrobsync.fetch_bookmarks) only cover the device that actually
	# paused/stopped — a second device has no local record of that at all. Scrob is the
	# one provider here with a genuine server-side continue-watching list (unlike e.g.
	# Floppy, which has no queryable equivalent), so this lets a second device pick up a
	# resume point a different device left on the server. For episodes, media.tmdb_id in
	# this response is the episode's own distinct TMDb id (not comparable to anything
	# Umbrella tracks) — match on show_tmdb_id + season/episode instead, confirmed
	# against a real account.
	try:
		if not tmdb: return 0
		for item in get_continue_watching():
			media = item.get('media') or {}
			if season is not None and episode is not None:
				if media.get('type') != 'episode': continue
				if str(media.get('show_tmdb_id') or '') != str(tmdb): continue
				if media.get('season_number') != int(season) or media.get('episode_number') != int(episode): continue
			else:
				if media.get('type') != 'movie': continue
				if str(media.get('tmdb_id') or '') != str(tmdb): continue
			return round((item.get('progress_percent') or 0) * 100, 2)
		return 0
	except:
		log_utils.error()
		return 0

def get_next_up():
	try:
		if not getScrobCredentialsInfo(): return []
		data = getScrobAsJson('/history/next-up', auth='api_key', silent=True)
		if isinstance(data, dict):
			for key in ('next_up', 'results', 'shows'):
				if key in data: return data[key]
			return []
		return data or []
	except:
		log_utils.error()
		return []


#### Simple list add/create/remove — JWT-only, no browsable list-of-lists surface ####

def get_lists():
	try:
		if not getScrobCredentialsInfo(): return []
		data = getScrobAsJson('/lists', auth='api_key', silent=True)
		return (data or {}).get('lists', []) if isinstance(data, dict) else []
	except:
		log_utils.error()
		return []

def create_list(name, description=''):
	try:
		if not getScrobWriteCredentialsInfo(): return None
		response = getScrob('/lists', post={'name': name, 'description': description or None}, method='POST', auth='jwt', silent=True)
		return getScrobAsJson('/lists', auth='api_key', silent=True) and response is not None and response.status_code == 201
	except:
		log_utils.error()
		return False

def add_to_list(list_id, tmdb, media_type='movie'):
	try:
		if not getScrobWriteCredentialsInfo(): return False
		response = getScrob('/lists/%s/items' % list_id, post={'tmdb_id': int(tmdb), 'media_type': media_type}, method='POST', auth='jwt', silent=True)
		return bool(response is not None and response.status_code == 201)
	except:
		log_utils.error()
		return False

def remove_from_list(list_id, item_id):
	try:
		if not getScrobWriteCredentialsInfo(): return False
		response = getScrob('/lists/%s/items/%s' % (list_id, item_id), method='DELETE', auth='jwt', silent=True)
		return bool(response is not None and response.status_code in (200, 204))
	except:
		log_utils.error()
		return False

def get_list_items(list_id):
	try:
		if not getScrobCredentialsInfo(): return []
		data = getScrobAsJson('/lists/%s' % list_id, auth='api_key', silent=True)
		return (data or {}).get('items', []) if isinstance(data, dict) else []
	except:
		log_utils.error()
		return []

def sync_user_lists(forced=False):
	# Locally caches every list's items (movies_watched()'s "same local-history pagination
	# shape" reasoning applies here too) — get_lists_with_type()/get_list_items() were being
	# called live, once per list, on every single "My Movies/My TV Shows > Scrob" folder open,
	# which is what made those views noticeably slower than Floppy's/Trakt's equivalent lists
	# (both already locally cached). No activity/last-modified endpoint exists for /lists, so
	# this is a full poll-and-replace on scrob_syncInterval, same as sync_watchedProgress().
	try:
		if not getScrobCredentialsInfo(): return
		rows = []
		lists = get_lists()
		for lst in lists:
			try:
				list_id = lst.get('id')
				if list_id is None: continue
				list_name = lst.get('name', '')
				for item in get_list_items(list_id):
					try:
						media = item.get('media') or {}
						media_type = media.get('type')
						if media_type not in ('movie', 'series'): continue
						tmdb = str(media.get('tmdb_id') or '')
						if not tmdb: continue
						rows.append({
							'list_id': str(list_id), 'list_name': list_name, 'item_id': str(item.get('id') or ''),
							'tmdb': tmdb, 'title': media.get('title', '') or '',
							'year': str(media.get('release_date', '') or '')[:4],
							'media_type': media_type, 'listed_at': item.get('added_at') or item.get('created_at') or '',
						})
					except: log_utils.error()
			except: log_utils.error()
		scrobsync.insert_user_lists(rows)
		log_utils.log('SCROB: user lists sync — %s lists, %s items cached' % (len(lists), len(rows)), level=log_utils.LOGINFO)
	except: log_utils.error()

def get_lists_containing(tmdb, media_type):
	try:
		tmdb = str(tmdb)
		matches = []
		for lst in get_lists():
			list_id = lst.get('id')
			if list_id is None: continue
			for item in get_list_items(list_id):
				media = item.get('media') or {}
				if str(media.get('tmdb_id') or '') == tmdb and media.get('type') == media_type:
					matches.append((list_id, lst.get('name', ''), item.get('id')))
					break
		return matches
	except:
		log_utils.error()
		return []


#### Context-menu manager (mirrors floppy.manager()/customtrakt.manager()) ####

def manager(name, imdb=None, tvdb=None, tmdb=None, season=None, episode=None, refresh=True, watched=None, unfinished=False, tvshow=None):
	try:
		if season: season = int(season)
		if episode: episode = int(episode)
		if episode: content_type = 'episode'
		elif season: content_type = 'season'
		elif tvdb and tvdb != 'None': content_type = 'tvshow'
		else: content_type = 'movie'
		media_type = 'movie' if content_type == 'movie' else 'tv'
		scrob_media_type = 'movie' if content_type == 'movie' else 'series'
		hc = getSetting('highlight.color')
		has_write = getScrobWriteCredentialsInfo()
		items = []
		if watched is not None:
			if watched:
				if has_write: items += [('[COLOR %s]Unwatch[/COLOR]' % hc, 'unwatch')]
			else:
				items += [('[COLOR %s]Watch[/COLOR]' % hc, 'watch')]
		else:
			items += [('[COLOR %s]Watch[/COLOR]' % hc, 'watch')]
			if has_write: items += [('[COLOR %s]Unwatch[/COLOR]' % hc, 'unwatch')]
		if content_type in ('movie', 'episode'):
			items += [('[COLOR %s]Clear Scrobble Progress[/COLOR]' % hc, 'scrobbleReset')]
		if has_write:
			items += [('[COLOR %s]Add to List[/COLOR]' % hc, 'list_add')]
			items += [('[COLOR %s]Remove from List[/COLOR]' % hc, 'list_remove')]
		control.hide()
		select = control.selectDialog([i[0] for i in items], heading=control.addonInfo('name') + ' - Scrob')
		if select == -1: return
		action_key = items[select][1]
		if action_key == 'watch':
			watch(content_type, name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=refresh)
		elif action_key == 'unwatch':
			unwatch(content_type, name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=refresh)
		elif action_key == 'scrobbleReset':
			scrobbleReset(imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, refresh=True)
		elif action_key == 'list_add':
			resolved_tmdb = tmdb or _resolve_tmdb(media_type, imdb=imdb, tvdb=tvdb)
			if not resolved_tmdb: return
			lists = get_lists()
			options = [l.get('name', '') for l in lists] + ['[COLOR %s]+ New List[/COLOR]' % hc]
			list_select = control.selectDialog(options, heading=control.addonInfo('name') + ' - Scrob Lists')
			if list_select == -1: return
			if list_select == len(lists):
				new_name = control.dialog.input('New List Name')
				if not new_name: return
				create_list(new_name)
				lists = get_lists()
				match = [l for l in lists if l.get('name') == new_name]
				if not match: return
				list_id = match[0].get('id')
			else:
				list_id = lists[list_select].get('id')
			if list_id and add_to_list(list_id, resolved_tmdb, media_type=scrob_media_type):
				control.notification(title='Scrob', message='Added to list')
				if refresh: control.refresh()
			else:
				control.notification(title='Scrob', message='Failed to add to list - check username/password')
		elif action_key == 'list_remove':
			resolved_tmdb = tmdb or _resolve_tmdb(media_type, imdb=imdb, tvdb=tvdb)
			if not resolved_tmdb: return
			matches = get_lists_containing(resolved_tmdb, scrob_media_type)
			if not matches:
				control.notification(title='Scrob', message='Not in any list')
				return
			list_select = control.selectDialog([m[1] for m in matches], heading=control.addonInfo('name') + ' - Remove From List')
			if list_select == -1: return
			list_id, _, item_id = matches[list_select]
			if remove_from_list(list_id, item_id):
				control.notification(title='Scrob', message='Removed from list')
				if refresh: control.refresh()
			else:
				control.notification(title='Scrob', message='Failed to remove from list - check username/password')
	except: log_utils.error()
