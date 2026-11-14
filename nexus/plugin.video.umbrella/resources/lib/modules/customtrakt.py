# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""
#trakt clone

from datetime import datetime
from hashlib import md5
from json import dumps as jsdumps
import time
from threading import Lock
from resources.lib.modules.lazy_network import requests, LazySession
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode
from resources.lib.database import cache, customtraktsync
from resources.lib.modules import control
from resources.lib.modules import log_utils

getLS = control.lang
getSetting = control.setting
setSetting = control.setSetting

headers = {'Content-Type': 'application/json'}
session = LazySession(dict(total=4, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 524, 530]), ('https://', 'http://'))
read_session = LazySession(dict(total=0), ('https://', 'http://'))

custom_icon = control.joinPath(control.artPath(), 'icon.png')
custom_token = getSetting('custom.user.token')
_reauth_lock = Lock()
_reauth_failed = False
_REAUTH_BUSY_PROP = 'umbrella.custom.reauth.busy'
_CUSTOM_TOKEN_PROP = 'umbrella.custom.access_token'
_last_request_time = 0.0
control.homeWindow.setProperty(_CUSTOM_TOKEN_PROP, getSetting('custom.user.token') or '')


def customBaseUrl():
	url = getSetting('custom.baseurl').strip()
	if url and not url.startswith(('http://', 'https://')): url = 'https://' + url
	return url.rstrip('/')


def getCustomServiceName():
	name = getSetting('custom.servicename').strip()
	return name if name else 'Custom'


def customClientID():
	client_id = getSetting('custom.clientid').strip()
	return client_id if client_id else '78008cde858e3a324fb0df6f4be9986e'


def customClientSecret():
	client_secret = getSetting('custom.clientsecret').strip()
	return client_secret if client_secret else '6QpPI5nel0XTHOcr-x4Hzq1WU-tRJxplf1QBTcF4XJI'


def getCustomCredentialsInfo():
	if getSetting('dev.enable.custom') != 'true': return False
	username, token = getSetting('custom.user.name').strip(), getSetting('custom.user.token')
	if not (customBaseUrl() and username and token): return False
	return True


def getCustomIndicatorsInfo():
	if getSetting('dev.enable.custom') != 'true': return False
	return getSetting('indicators.alt') == '4'


#### Core request plumbing (mirrors trakt.py's getTrakt/getTraktAsJson/get_all_pages) ####

def _custom_reads_paused(base):
	key = 'umbrella.custom.read_backoff.' + md5(base.encode('utf-8')).hexdigest()
	try: return float(control.homeWindow.getProperty(key) or 0) > time.time()
	except (TypeError, ValueError): return False


def _custom_read(url, base):
	# Share an outage cooldown across plugin invocations. Repeated progress
	# lookups must not multiply connection retries for every show and episode.
	key = 'umbrella.custom.read_backoff.' + md5(base.encode('utf-8')).hexdigest()
	if _custom_reads_paused(base): return None
	try:
		response = read_session.get(url, headers=headers, timeout=(3, 5))
	except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
		control.homeWindow.setProperty(key, str(time.time() + 30))
		log_utils.log_force('CUSTOM: read unavailable (%s); pausing reads for 30 seconds' % type(exc).__name__, level=log_utils.LOGWARNING)
		return None
	if response.status_code == 429 or response.status_code >= 500:
		control.homeWindow.setProperty(key, str(time.time() + 30))
	return response


def getCustom(url, post=None, extended=False, silent=False, reauth_attempts=0, method=None, fast=False):
	# fast=True is for lookups made while a directory is being built: short
	# timeout, no retries, shared outage cooldown. Syncs and writes keep the
	# patient retrying transport so a slow server cannot leave watched state stale.
	try:
		global _last_request_time
		base = customBaseUrl()
		if not base: return None
		if time.time() - _last_request_time > 300:
			session.close()
		if not url.startswith(base): url = urljoin(base + '/', url.lstrip('/'))
		if post and not isinstance(post, str): post = jsdumps(post)
		if getCustomCredentialsInfo():
			current_token = control.homeWindow.getProperty(_CUSTOM_TOKEN_PROP) or getSetting('custom.user.token')
			headers['Authorization'] = 'Bearer %s' % current_token
		_req_start = time.time()
		for _attempt in range(2):
			try:
				if method == 'DELETE':
					response = session.delete(url, headers=headers, timeout=20)
				elif post:
					response = session.post(url, data=post, headers=headers, timeout=20)
				elif fast:
					response = _custom_read(url, base)
					if response is None: return None
				else:
					response = session.get(url, headers=headers, timeout=20)
				_last_request_time = time.time()
				break
			except requests.exceptions.ConnectionError:
				if _attempt == 0 and not post:
					log_utils.log('getCustom: connection reset, retrying with fresh connection...', level=log_utils.LOGDEBUG)
					session.close()
				else:
					raise
		status_code = str(response.status_code)
		error_handler(url, response, status_code, silent=silent)
		if response and status_code in ('200', '201', '204'):
			if extended: return response, response.headers
			else: return response
		elif status_code == '409':
			if extended: return response, response.headers
			else: return response
		elif status_code == '401':
			if reauth_attempts >= 2:
				log_utils.log('CUSTOM: Too many re-auth attempts, stopping to prevent infinite loop', level=log_utils.LOGWARNING)
				return None
			success = re_auth(headers)
			if success: return getCustom(url, post=post, extended=extended, silent=silent, reauth_attempts=reauth_attempts + 1, method=method, fast=fast)
		elif status_code == '429':
			if fast: return None
			if 'Retry-After' in response.headers:
				throttleTime = response.headers['Retry-After']
				control.sleep((int(throttleTime) + 1) * 1000)
				return getCustom(url, post=post, extended=extended, silent=silent, reauth_attempts=reauth_attempts, method=method)
		else:
			response_text = response.text[:300] if hasattr(response, 'text') else str(response)[:300]
			log_utils.log_force('CUSTOM: request failed url=%s status=%s response=%s' % (url, status_code, response_text), level=log_utils.LOGWARNING)
			return None
	except Exception as e:
		log_utils.log_force('CUSTOM: getCustom exception url=%s error=%s' % (url, e), level=log_utils.LOGWARNING)
		try: log_utils.error('getCustom Error: ')
		except: pass
	return None


def error_handler(url, response, status_code, silent=False):
	if status_code.startswith('5') or (response and isinstance(response, str) and '<html' in response) or not str(response):
		log_utils.log('CUSTOM: temporary server problem: %s:%s' % (status_code, response), level=log_utils.LOGINFO)
	elif status_code == '404':
		response_text = response.text if not isinstance(response, str) and hasattr(response, 'text') else str(response)
		log_utils.log('getCustom() (404:NOT FOUND): URL=(%s): %s' % (url, response_text), level=log_utils.LOGWARNING)


def getCustomAsJson(url, post=None, silent=False, fast=False):
	try:
		r = getCustom(url=url, post=post, extended=False, silent=silent, fast=fast)
		if not r: return None
		return r.json()
	except Exception as e:
		log_utils.log('CUSTOM: Error in getCustomAsJson: %s' % str(e), level=log_utils.LOGWARNING)
		return None


def get_all_pages(url, silent=False):
	# Confirmed spec paginates with page (default 1) / limit (default 50).
	try:
		sep = '&' if '?' in url else '?'
		limit = 1000
		page = 1
		results = []
		previous_page = None
		while True:
			page_url = url + sep + 'page=%d&limit=%d' % (page, limit)
			response = getCustom(page_url, silent=silent)
			if not response:
				if page == 1: return None
				break
			try:
				page_results = response.json()
			except Exception as e:
				log_utils.log('CUSTOM: get_all_pages JSON decode error on page %d: %s' % (page, str(e)), level=log_utils.LOGWARNING)
				if page == 1: return None
				break
			response_data = page_results
			if isinstance(page_results, dict):
				# Some endpoints likely wrap results (e.g. {"items": [...], "pagination": {...}}) â€”
				# unwrap the first list-valued field found, matching the confirmed pagination shape.
				unwrapped = next((v for v in page_results.values() if isinstance(v, list)), None)
				if unwrapped is None:
					log_utils.log('CUSTOM: get_all_pages page %d: dict response with no list-valued field (keys=%s) url=%s' % (page, list(page_results.keys()), page_url), level=log_utils.LOGWARNING)
				page_results = unwrapped if unwrapped is not None else []
			if not page_results:
				if page == 1: return page_results if page_results is not None else []
				break
			# A few Trakt-compatible servers accept page/limit but return page 1 for
			# every request. Without this guard the same records are appended 400
			# times and the endpoint is hammered until the safety limit is reached.
			if previous_page is not None and page_results == previous_page:
				log_utils.log('CUSTOM: get_all_pages stopped on repeated page %d for URL: %s' % (page, url), level=log_utils.LOGWARNING)
				break
			previous_page = page_results
			results.extend(page_results)
			pagination = response_data.get('pagination') if isinstance(response_data, dict) else None
			if isinstance(pagination, dict):
				total_pages = pagination.get('total_pages') or pagination.get('page_count')
				if total_pages is not None and page >= int(total_pages): break
				if 'next' in pagination and not pagination.get('next'): break
			else:
				try: total_pages = int(response.headers.get('X-Pagination-Page-Count', ''))
				except: total_pages = 0
				if total_pages and page >= total_pages: break
			page += 1
			if page > 400:
				log_utils.log('CUSTOM: get_all_pages reached safety limit of 400 pages for URL: %s' % url, level=log_utils.LOGWARNING)
				break
		return results
	except Exception as e:
		log_utils.log('CUSTOM: Error in get_all_pages: %s' % str(e), level=log_utils.LOGWARNING)
		return None


#### Auth: OAuth device-code flow (confirmed to match Trakt's own contract) ####

def re_auth(headers):
	global _reauth_failed
	if _reauth_failed: return False
	expired_token = headers.get('Authorization', '').replace('Bearer ', '').strip()
	with _reauth_lock:
		if _reauth_failed: return False
		for _ in range(10):
			if control.homeWindow.getProperty(_REAUTH_BUSY_PROP) != 'true': break
			control.sleep(500)
		current_token = control.homeWindow.getProperty(_CUSTOM_TOKEN_PROP)
		if current_token and expired_token and current_token != expired_token:
			return True
		control.homeWindow.setProperty(_REAUTH_BUSY_PROP, 'true')
		try:
			base = customBaseUrl()
			if not base: return False
			oauth = urljoin(base + '/', 'oauth/token')
			opost = {'client_id': customClientID(), 'client_secret': customClientSecret(), 'grant_type': 'refresh_token', 'refresh_token': getSetting('custom.refreshtoken')}
			log_utils.log('CUSTOM: Re-Authenticating with refresh token', level=log_utils.LOGINFO)
			response = session.post(url=oauth, data=jsdumps(opost), headers=headers, timeout=20)
			status_code = str(response.status_code)
			if status_code not in ('401', '403', '405'):
				try:
					response_json = response.json()
				except Exception as e:
					log_utils.log('CUSTOM: JSON decode error in re_auth: %s' % str(e), level=log_utils.LOGWARNING)
					_reauth_failed = True
					return False
				if 'access_token' not in response_json:
					log_utils.log('CUSTOM: Please re-authorize your Custom service account: %s : %s' % (status_code, str(response_json)), level=log_utils.LOGWARNING)
					control.notification(title=getCustomServiceName(), message=33677)
					_clear_custom_auth_settings()
					_reauth_failed = True
					return False
				token, refresh = response_json['access_token'], response_json.get('refresh_token', getSetting('custom.refreshtoken'))
				expires_from_server = response_json.get('expires_in', 0)
				expires = str(time.time() + expires_from_server) if expires_from_server else ''
				control.homeWindow.setProperty('umbrella.updateSettings', 'false')
				setSetting('custom.isauthed', 'true')
				setSetting('custom.user.token', token)
				setSetting('custom.refreshtoken', refresh)
				control.homeWindow.setProperty('umbrella.updateSettings', 'true')
				setSetting('custom.token.expires', expires)
				control.homeWindow.setProperty(_CUSTOM_TOKEN_PROP, token)
				log_utils.log('CUSTOM: Re-authentication successful', level=log_utils.LOGINFO)
				return True
			else:
				log_utils.log('CUSTOM: Error while re-authorizing: %s : %s' % (status_code, response.text), level=log_utils.LOGWARNING)
				if status_code in ('401', '403'):
					control.notification(
						title=getCustomServiceName(),
						message='Authorization expired. Please re-authorize in Umbrella settings.',
						icon=custom_icon)
					_clear_custom_auth_settings()
				_reauth_failed = True
				return False
		except Exception as e:
			log_utils.log('CUSTOM: Exception in re_auth: %s' % str(e), level=log_utils.LOGWARNING)
			return False
		finally:
			control.homeWindow.setProperty(_REAUTH_BUSY_PROP, '')


def _clear_custom_auth_settings():
	control.homeWindow.setProperty('umbrella.updateSettings', 'false')
	setSetting('custom.isauthed', 'false')
	setSetting('custom.user.token', '')
	setSetting('custom.refreshtoken', '')
	setSetting('custom.token.expires', '')
	control.homeWindow.setProperty('umbrella.updateSettings', 'true')


def getCustomDeviceCode():
	try:
		base = customBaseUrl()
		if not base:
			control.notification(message='Set a server URL in Custom service settings first', icon=custom_icon)
			return None
		client_id = customClientID()
		data = jsdumps({'client_id': client_id})
		url = urljoin(base + '/', 'oauth/device/code')
		response = session.post(url, data=data, headers=headers, timeout=20)
		if response.status_code == 200:
			return response.json()
		log_utils.log('CUSTOM: getCustomDeviceCode failed: %s' % response.status_code, level=log_utils.LOGWARNING)
		return None
	except:
		log_utils.error()
		return None


def getCustomDeviceToken(deviceCode):
	try:
		if not deviceCode or not isinstance(deviceCode, dict): return None
		base = customBaseUrl()
		data = {'code': deviceCode['device_code'], 'client_id': customClientID(), 'client_secret': customClientSecret()}
		start = time.time()
		expires_in = deviceCode.get('expires_in', 600)
		verification_url_raw = str(deviceCode.get('verification_url') or base)
		verification_url = control.lang(32513) % (getSetting('highlight.color'), verification_url_raw)
		user_code = control.lang(32514) % (getSetting('highlight.color'), str(deviceCode['user_code']))
		if control.setting('dialogs.useumbrelladialog') == 'true':
			from resources.lib.modules import tools
			parts = urlsplit(verification_url_raw)
			query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != 'user_code']
			query.append(('user_code', str(deviceCode['user_code'])))
			qr_target = urlunsplit(parts._replace(query=urlencode(query)))
			custom_qr = tools.make_qr(qr_target, 'custom_qr.png')
			progressDialog = control.getProgressWindow('%s Service' % getCustomServiceName(), custom_qr, 1)
			progressDialog.set_controls()
			progressDialog.update(0, control.progress_line % (verification_url, user_code))
		else:
			progressDialog = control.progressDialog
			progressDialog.create('%s Service' % getCustomServiceName(), control.progress_line % (verification_url, user_code))
		token_url = urljoin(base + '/', 'oauth/device/token')
		try:
			time_passed = 0
			while not progressDialog.iscanceled() and time_passed < expires_in:
				try:
					response = requests.post(token_url, json=data, headers=headers, timeout=20)
					if response.status_code == 400:
						time_passed = time.time() - start
						progress = int(100) - int(100 * time_passed / expires_in)
						progressDialog.update(progress, control.progress_line % (verification_url, user_code))
						control.sleep(max(deviceCode.get('interval', 5), 1) * 1000)
					else:
						return response
				except requests.HTTPError as e:
					if e.response.status_code != 400: raise e
					control.sleep(max(deviceCode.get('interval', 5), 1) * 1000)
		finally:
			progressDialog.close()
		return None
	except:
		log_utils.error()


def customAuth(fromSettings=0):
	try:
		deviceCode = getCustomDeviceCode()
		if not deviceCode:
			if fromSettings == 1: control.openSettings('14.2', 'plugin.video.umbrella')
			control.notification(message='%s Service Authorization Error' % getCustomServiceName(), icon=custom_icon)
			return False
		tokenResponse = getCustomDeviceToken(deviceCode)
		if tokenResponse:
			tokenResponse = tokenResponse.json()
			if 'access_token' not in tokenResponse:
				control.notification(message='%s Service Authorization Error' % getCustomServiceName(), icon=custom_icon)
				return False
			expires_from_server = tokenResponse.get('expires_in', 0)
			expires_at = time.time() + expires_from_server if expires_from_server else ''
			control.homeWindow.setProperty('umbrella.updateSettings', 'false')
			control.setSetting('custom.token.expires', str(expires_at))
			control.setSetting('custom.user.token', tokenResponse['access_token'])
			control.homeWindow.setProperty(_CUSTOM_TOKEN_PROP, tokenResponse['access_token'])
			control.setSetting('custom.isauthed', 'true')
			control.homeWindow.setProperty('umbrella.updateSettings', 'true')
			control.setSetting('custom.refreshtoken', tokenResponse.get('refresh_token', ''))
			control.sleep(1000)
			try:
				headers['Authorization'] = 'Bearer %s' % tokenResponse['access_token']
				account_info = getCustomAsJson('users/settings')
				if account_info and account_info.get('user', {}).get('username'):
					control.setSetting('custom.user.name', str(account_info['user']['username']))
			except: pass
			control.notification(message='%s Service Authorized Successfully' % getCustomServiceName(), icon=custom_icon)
			if fromSettings == 1: control.openSettings('14.2', 'plugin.video.umbrella')
			if not control.yesnoDialog('Do you want to set %s as your service for your watched and unwatched indicators?' % getCustomServiceName(), '', '', 'Indicators', 'No', 'Yes'): return True
			global _reauth_failed
			_reauth_failed = False
			control.homeWindow.setProperty(_REAUTH_BUSY_PROP, '')
			control.homeWindow.setProperty('umbrella.updateSettings', 'false')
			control.setSetting('indicators.alt', '4')
			control.setSetting('scrobble.source', '4')
			control.homeWindow.setProperty('umbrella.updateSettings', 'true')
			control.setSetting('scrobble', getCustomServiceName())
			control.setSetting('indicators', getCustomServiceName())
			control.notification(message='%s Indicators Enabled - Syncing Watched Data...' % getCustomServiceName())
			from threading import Thread
			Thread(target=sync_watched, kwargs={'forced': True}).start()
			return True
		if fromSettings == 1: control.openSettings('14.2', 'plugin.video.umbrella')
		control.notification(message='%s Service Authorization Error' % getCustomServiceName(), icon=custom_icon)
		return False
	except:
		log_utils.error()


def customRevoke(fromSettings=0):
	data = {'token': getSetting('custom.user.token'), 'client_id': customClientID(), 'client_secret': customClientSecret()}
	try: getCustom('oauth/revoke', post=data)
	except: pass
	control.homeWindow.setProperty('umbrella.updateSettings', 'false')
	control.setSetting('custom.user.name', '')
	control.setSetting('custom.token.expires', '')
	control.setSetting('custom.user.token', '')
	control.setSetting('custom.isauthed', '')
	control.homeWindow.setProperty('umbrella.updateSettings', 'true')
	control.setSetting('custom.refreshtoken', '')
	try:
		clr_customSync = ('bookmarks', 'custom_watched_movies', 'custom_watched_episodes', 'movies_watchlist', 'shows_watchlist', 'movies_collection', 'shows_collection', 'movies_dropped', 'shows_dropped', 'watched')
		customtraktsync.delete_custom_tables(clr_customSync)
		if getSetting('indicators.alt') == '4':
			control.setSetting('indicators.alt', '0')
			control.setSetting('indicators', 'Local')
		if getSetting('scrobble.source') == '4':
			control.setSetting('scrobble.source', '0')
			control.setSetting('scrobble', 'Local')
		control.setSetting('custom.markwatched', 'false')
		global _reauth_failed
		_reauth_failed = False
		control.homeWindow.setProperty(_REAUTH_BUSY_PROP, '')
		control.homeWindow.setProperty(_CUSTOM_TOKEN_PROP, '')
		if fromSettings == 1:
			control.openSettings('14.2', 'plugin.video.umbrella')
			control.dialog.ok(getCustomServiceName(), '%s Service Authorization Revoked' % getCustomServiceName())
	except:
		log_utils.error()


#### Activity polling (delta-sync gating via the confirmed /sync/last_activities) ####

def getActivities():
	return cache.get(getCustomAsJson, 0, '/sync/last_activities') if getCustomCredentialsInfo() else None


def getActivity(activities=None):
	try:
		i = activities if activities else getActivities()
		if not i: return 0
		from resources.lib.modules import cleandate
		val = i.get('all') or i.get('history', {}).get('movies') or i.get('history', {}).get('episodes')
		return int(cleandate.iso_2_utc(val) or 0) if val else 0
	except: return 0


#### Calendar (GET /calendars/my/{movies|shows}/{start_date}/{days}) ####
# Response schema isn't typed in the confirmed OpenAPI spec â€” assumed to mirror
# Trakt's own calendar shape ([{'show'/'movie': {...}, 'episode': {...}}, ...]),
# consistent with every other assumption made throughout this integration.

def get_calendar(media_type, days=33, start_date=None):
	try:
		if not start_date: start_date = datetime.utcnow().strftime('%Y-%m-%d')
		media = 'movies' if media_type == 'movies' else 'shows'
		url = '/calendars/my/%s/%s/%s' % (media, start_date, days)
		return getCustomAsJson(url) or []
	except:
		log_utils.error()
		return []


#### Watch/unwatch + mark watched (via POST /sync/history, /sync/history/remove) ####
# Unlike Trakt, there's no aggregated "watched" endpoint to re-query for fresh state
# (see Design notes), so â€” mirroring mdblist.py's markMovieAsWatched/etc. exactly â€”
# each of these also upserts/deletes the local customtraktsync cache directly and
# invalidates the syncMovies/syncTVShows cache key, so indicators update immediately
# instead of waiting on the next background /sync/history pull.

def _now_iso():
	return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')

def markMovieAsWatched(imdb, tmdb=''):
	try:
		result = getCustomAsJson('/sync/history', {'movies': [{'ids': {'imdb': imdb}}]})
		if not result: return False
		success = _history_write_succeeded(result, 'added', 'movies')
		if success:
			customtraktsync.bump_history_revision()
			customtraktsync.upsert_watched_movie(imdb=imdb, tmdb=str(tmdb), last_watched_at=_now_iso())
			customtraktsync.cache_delete(customtraktsync._hash_function(syncMovies, ()))
		return success
	except: log_utils.error()

def markMovieAsNotWatched(imdb):
	try:
		result = getCustomAsJson('/sync/history/remove', {'movies': [{'ids': {'imdb': imdb}}]})
		if not result: return False
		success = _history_write_succeeded(result, 'deleted', 'movies')
		if success:
			customtraktsync.bump_history_revision()
			customtraktsync.delete_watched_movie(imdb)
			customtraktsync.cache_delete(customtraktsync._hash_function(syncMovies, ()))
		return success
	except: log_utils.error()

def _watched_show_payload(imdb, tvdb, season=None):
	"""Name every aired episode: some Custom servers expand only stored rows."""
	from resources.lib.indexers import tmdb as _tmdb
	api = _tmdb.TVshows()
	lookup = cache.get(api.IdLookup, 96, imdb, tvdb)
	tmdb = str((lookup or {}).get('id') or '')
	if not tmdb: raise ValueError('Cannot resolve show for watched action')
	today = datetime.utcnow().strftime('%Y-%m-%d')
	if season is not None:
		seasons = [int(season)]
	else:
		meta = cache.get(api.get_showSeasons_meta, 96, tmdb)
		if not isinstance(meta, dict) or not isinstance(meta.get('seasons'), list):
			raise ValueError('Cannot read show seasons for watched action')
		seasons = [int(item['season_number']) for item in meta['seasons']
			if (int(item['season_number']) > 0 or getSetting('tv.specials') == 'true')
			and item.get('air_date') and item['air_date'] <= today]
	rows = []
	for sn in seasons:
		raw = cache.get(api.get_season_request, 96, tmdb, sn)
		if not isinstance(raw, dict) or not isinstance(raw.get('episodes'), list):
			raise ValueError('Cannot read episodes for watched action')
		episodes = [{'number': int(ep['episode_number'])} for ep in raw['episodes']
			if int(ep.get('episode_number') or 0) > 0 and ep.get('air_date') and ep['air_date'] <= today]
		if episodes: rows.append({'number': sn, 'episodes': episodes})
	if not rows: raise ValueError('No aired episodes found for watched action')
	ids = {key: value for key, value in (('imdb', imdb), ('tvdb', tvdb), ('tmdb', tmdb)) if value not in (None, '')}
	return {'shows': [{'ids': ids, 'seasons': rows}]}


def _confirm_watched_show_payload(payload):
	show = payload['shows'][0]
	ids = show['ids']
	progress = getCustomAsJson('shows/%s/progress/watched' % ids['imdb'], silent=True)
	if not isinstance(progress, dict): return False
	watched = {(int(s['number']), int(e['number'])) for s in progress.get('seasons', [])
		for e in s.get('episodes', []) if e.get('completed')}
	targets = {(int(s['number']), int(e['number'])) for s in show['seasons'] for e in s['episodes']}
	if not targets.issubset(watched): return False
	customtraktsync.bump_history_revision()
	for sn, en in targets:
		customtraktsync.upsert_watched_episode(show_imdb=ids['imdb'], show_tmdb=ids['tmdb'],
			show_tvdb=str(ids.get('tvdb') or ''), season=sn, episode=en, last_watched_at=_now_iso())
	customtraktsync.cache_delete(customtraktsync._hash_function(syncTVShows, ()))
	customtraktsync.cache_delete(customtraktsync._hash_function(_fetchShowProgress, (ids['imdb'],)))
	for args in ((ids['imdb'], ids.get('tvdb') or ''), (ids['imdb'], ids.get('tvdb') or '', ids['tmdb'])):
		customtraktsync.cache_delete(customtraktsync._hash_function(syncSeasons, args))
	return True


def markTVShowAsWatched(imdb, tvdb):
	try:
		payload = _watched_show_payload(imdb, tvdb)
		result = getCustomAsJson('/sync/history', payload)
		return _history_write_succeeded(result, 'added', 'episodes') and _confirm_watched_show_payload(payload)
	except:
		log_utils.error()
		return False


def markTVShowAsNotWatched(imdb, tvdb):
	try:
		result = getCustomAsJson('/sync/history/remove', {'shows': [{'ids': {'imdb': imdb, 'tvdb': tvdb}}]})
		if not result: return False
		success = _history_write_succeeded(result, 'deleted', 'episodes')
		if success:
			customtraktsync.bump_history_revision()
			for (si, st, sv, s, e) in customtraktsync.get_watched_episodes():
				if (imdb and si == imdb) or (tvdb and sv == tvdb): customtraktsync.delete_watched_episode(si, s, e)
			customtraktsync.cache_delete(customtraktsync._hash_function(syncTVShows, ()))
			customtraktsync.cache_delete(customtraktsync._hash_function(_fetchShowProgress, (imdb,)))
		return success
	except: log_utils.error()

def markSeasonAsWatched(imdb, tvdb, season):
	try:
		payload = _watched_show_payload(imdb, tvdb, season=int(season))
		result = getCustomAsJson('/sync/history', payload)
		return _history_write_succeeded(result, 'added', 'episodes') and _confirm_watched_show_payload(payload)
	except:
		log_utils.error()
		return False


def markSeasonAsNotWatched(imdb, tvdb, season):
	try:
		season = int('%01d' % int(season))
		result = getCustomAsJson('/sync/history/remove', {'shows': [{'seasons': [{'number': season}], 'ids': {'imdb': imdb, 'tvdb': tvdb}}]})
		if not result: return False
		success = _history_write_succeeded(result, 'deleted', 'episodes')
		if success:
			customtraktsync.bump_history_revision()
			for (si, st, sv, s, e) in customtraktsync.get_watched_episodes():
				if ((imdb and si == imdb) or (tvdb and sv == tvdb)) and int(s) == season: customtraktsync.delete_watched_episode(si, s, e)
			customtraktsync.cache_delete(customtraktsync._hash_function(syncTVShows, ()))
			customtraktsync.cache_delete(customtraktsync._hash_function(_fetchShowProgress, (imdb,)))
		return success
	except: log_utils.error()

def _history_write_succeeded(result, action, kind):
	from resources.lib.modules.history_result import succeeded
	return succeeded(result, action, kind)


def markEpisodeAsWatched(imdb, tvdb, season, episode):
	try:
		season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
		result = getCustomAsJson('/sync/history', {'shows': [{'seasons': [{'episodes': [{'number': episode}], 'number': season}], 'ids': {'imdb': imdb, 'tvdb': tvdb}}]})
		if not result:
			log_utils.log('Custom markEpisodeAsWatched IMDB: %s S%sE%s Result: False (empty response)' % (imdb, season, episode), level=log_utils.LOGDEBUG)
			return False
		success = _history_write_succeeded(result, 'added', 'episodes')
		log_utils.log('Custom markEpisodeAsWatched IMDB: %s S%sE%s Result: %s' % (imdb, season, episode, success), level=log_utils.LOGDEBUG)
		if success:
			customtraktsync.bump_history_revision()
			customtraktsync.upsert_watched_episode(show_imdb=imdb, show_tvdb=str(tvdb), season=season, episode=episode, last_watched_at=_now_iso())
			customtraktsync.delete_bookmark(imdb, str(tvdb or ''), season, episode)
			customtraktsync.cache_delete(customtraktsync._hash_function(syncTVShows, ()))
			customtraktsync.cache_delete(customtraktsync._hash_function(_fetchShowProgress, (imdb,)))
		return success
	except: log_utils.error()

def markEpisodeAsNotWatched(imdb, tvdb, season, episode):
	try:
		season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
		result = getCustomAsJson('/sync/history/remove', {'shows': [{'seasons': [{'episodes': [{'number': episode}], 'number': season}], 'ids': {'imdb': imdb, 'tvdb': tvdb}}]})
		if not result: return False
		success = _history_write_succeeded(result, 'deleted', 'episodes')
		if success:
			customtraktsync.bump_history_revision()
			customtraktsync.delete_watched_episode(imdb, season, episode)
			customtraktsync.cache_delete(customtraktsync._hash_function(syncTVShows, ()))
			customtraktsync.cache_delete(customtraktsync._hash_function(_fetchShowProgress, (imdb,)))
		return success
	except: log_utils.error()


def watch(content_type, name, imdb=None, tvdb=None, season=None, episode=None, refresh=True, tmdb=''):
	if content_type != 'movie' and tmdb:
		from resources.lib.modules import episode_mapping, anthology_tracking
		if episode_mapping.supported(tmdb):
			return anthology_tracking.manager_write('customtrakt', tmdb, season, episode, False, refresh)
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
	if getSetting('services.general.notifications') == 'true':
		if success is True: control.notification(title=getCustomServiceName(), message=getLS(40729) % ('[COLOR %s]%s[/COLOR]' % (getSetting('highlight.color'), name), getCustomServiceName()))
		else: control.notification(title=getCustomServiceName(), message=getLS(40730) % ('[COLOR %s]%s[/COLOR]' % (getSetting('highlight.color'), name), getCustomServiceName()))

def unwatch(content_type, name, imdb=None, tvdb=None, season=None, episode=None, refresh=True, tmdb=''):
	if content_type != 'movie' and tmdb:
		from resources.lib.modules import episode_mapping, anthology_tracking
		if episode_mapping.supported(tmdb):
			return anthology_tracking.manager_write('customtrakt', tmdb, season, episode, True, refresh)
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
	if getSetting('services.general.notifications') == 'true':
		if success is True: control.notification(title=getCustomServiceName(), message=getLS(40731) % ('[COLOR %s]%s[/COLOR]' % (getSetting('highlight.color'), name), getCustomServiceName()))
		else: control.notification(title=getCustomServiceName(), message=getLS(40732) % ('[COLOR %s]%s[/COLOR]' % (getSetting('highlight.color'), name), getCustomServiceName()))


#### Scrobble (POST /scrobble/start, /scrobble/pause, /scrobble/stop; DELETE /sync/playback/{id}) ####

def scrobbleMovie(imdb, tmdb, watched_percent):
	try:
		if imdb and not imdb.startswith('tt'): imdb = 'tt' + imdb
		success = getCustom('/scrobble/pause', {'movie': {'ids': {'imdb': imdb}}, 'progress': watched_percent})
		if success:
			control.sleep(1000)
			sync_playbackProgress(forced=True)
			control.trigger_widget_refresh()
	except: log_utils.error()

def scrobbleEpisode(imdb, tmdb, tvdb, season, episode, watched_percent):
	try:
		season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
		post = {'show': {'ids': {'tvdb': tvdb, 'imdb': imdb}}, 'episode': {'season': season, 'number': episode}, 'progress': watched_percent}
		from resources.lib.modules.episode_mapping import scrobble_payload
		post = scrobble_payload(post, 'customtrakt', tmdb)
		success = getCustom('/scrobble/pause', post)
		if success:
			control.sleep(1000)
			sync_playbackProgress(forced=True)
			control.trigger_widget_refresh()
	except: log_utils.error()

def scrobbleStart(media_type, title='', tvshowtitle='', year='0', imdb='', tmdb='', tvdb='', season='', episode='', watched_percent=0):
	try:
		if media_type == 'movie':
			post = {'movie': {'title': title, 'year': int(year) if year else 0, 'ids': {'imdb': imdb, 'tmdb': int(tmdb) if tmdb else None}}, 'progress': float(watched_percent)}
		else:
			post = {'show': {'title': tvshowtitle or title, 'year': int(year) if year else 0, 'ids': {'tvdb': int(tvdb) if tvdb else None, 'imdb': imdb}},
					'episode': {'season': int(season) if season else 1, 'number': int(episode) if episode else 1}, 'progress': float(watched_percent)}
		from resources.lib.modules.episode_mapping import scrobble_payload
		post = scrobble_payload(post, 'customtrakt', tmdb)
		getCustom('/scrobble/start', post)
	except: log_utils.error()

def finishProgressRemoval(succeeded, total):
	if succeeded < total:
		control.notification(title=getCustomServiceName(), message='Removed playback progress for %s of %s items. Some requests failed; their local progress was retained.' % (succeeded, total))
	return succeeded == total


def scrobbleReset(imdb, tmdb=None, tvdb=None, season=None, episode=None, refresh=True, widgetRefresh=False, clear_local=True):
	if not getCustomCredentialsInfo(): return False
	if not control.player.isPlaying(): control.busy()
	try:
		resume_info = customtraktsync.fetch_bookmarks(imdb, tmdb, tvdb, season, episode, ret_type='resume_info')
		if resume_info == '0':
			if not sync_playbackProgress(forced=True): return False
			resume_info = customtraktsync.fetch_bookmarks(imdb, tmdb, tvdb, season, episode, ret_type='resume_info')
			if resume_info == '0': return True
		response = getCustom('/sync/playback/%s' % resume_info[1], method='DELETE')
		success = response is not None
		if not success:
			remaining = get_all_pages('/sync/playback?extended=full', silent=True)
			success = remaining is not None and not any(str(i.get('id')) == str(resume_info[1]) for i in remaining)
		if not success:
			if refresh: control.notification(title=getCustomServiceName(), message='Failed to remove playback progress')
			return False
		if clear_local: customtraktsync.delete_bookmark(imdb, tvdb or '', season if season is not None else '', episode if episode is not None else '', tmdb=tmdb)
		if refresh: control.refresh()
		if widgetRefresh or refresh: control.trigger_widget_refresh()
		return True
	except:
		log_utils.error()
		return False
	finally:
		control.hide()


#### In-progress / continue-watching (GET /sync/playback) ####

def sync_playbackProgress(activities=None, forced=False):
	try:
		activity = getActivity(activities)
		if not forced:
			db_last = customtraktsync.last_sync('last_paused_at')
			if activity and activity <= db_last: return True
		items = get_all_pages('/sync/playback?extended=full', silent=True)
		if items is None: return False
		result = customtraktsync.insert_bookmarks(items, sync_at=datetime.utcfromtimestamp(activity).strftime('%Y-%m-%dT%H:%M:%S.000Z'))
		if result is False: return False
		return True
	except:
		log_utils.error()
		return False


#### Watched-history aggregation (no aggregated "watched" endpoint on the server) ####

def sync_watchedProgress(activities=None, forced=False, progress_callback=None):
	try:
		db_last = customtraktsync.last_sync('last_history_at')
		api_last = getActivity(activities)
		if not forced and api_last and db_last and api_last <= db_last: return True
		# The server's history endpoint is paginated but does not support since
		# or deletion tombstones. Reconcile a complete snapshot, atomically.
		revision = customtraktsync.history_revision()
		items, previous = [], None
		limit = 1000
		for page in range(1, 401):
			data = getCustomAsJson('/sync/history?limit=%s&page=%s' % (limit, page))
			if data is None: return False
			batch = data if isinstance(data, list) else data.get('items')
			if not isinstance(batch, list): return False
			if batch and batch == previous: return False
			items.extend(batch)
			if progress_callback: progress_callback('Syncing watch history', len(items), None)
			if len(batch) < limit: break
			previous = batch
		else: return False
		if not customtraktsync.replace_watched_history(items, expected_revision=revision): return False
		customtraktsync.update_last_watched_at('last_history_at', timestamp=datetime.utcfromtimestamp(api_last).strftime('%Y-%m-%dT%H:%M:%S.000Z'))
		customtraktsync.cache_delete(customtraktsync._hash_function(syncMovies, ()))
		customtraktsync.cache_delete(customtraktsync._hash_function(syncTVShows, ()))
		control.trigger_widget_refresh()
		return True
	except:
		log_utils.error()
		return False


def sync_watched(activities=None, forced=False, progress_callback=None):
	sync_watchedProgress(activities=activities, forced=forced, progress_callback=progress_callback)

def syncMovies():
	try:
		if not getCustomCredentialsInfo(): return None
		return customtraktsync.get_watched_movies() or []
	except: log_utils.error()

def watchedMovies():
	try:
		if not getCustomCredentialsInfo(): return None
		return customtraktsync.get_watched_movies_full() or []
	except: log_utils.error()

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
		if not getCustomCredentialsInfo(): return None
		episodes = customtraktsync.get_watched_episodes()
		if not episodes: return []
		from resources.lib.modules.progress_identity import group_watched_shows
		indicators = []
		for show in group_watched_shows(episodes):
			by_season = {}
			for season, episode in show['watched_set']:
				by_season.setdefault(season, []).append(episode)
			ep_ranges = {s: _make_episode_ranges(sorted(eps)) for s, eps in by_season.items()}
			ids = {field: show[field] for field in ('imdb', 'tmdb', 'tvdb')}
			indicators.append((ids, len(show['watched_set']), ep_ranges))
		return indicators
	except: log_utils.error()

def watchedShows():
	try:
		if not getCustomCredentialsInfo(): return None
		rows = customtraktsync.get_watched_shows()
		if not rows: return []
		return [{'ids': {'imdb': r[0], 'tmdb': r[1], 'tvdb': r[2]}, 'last_watched_at': r[3]} for r in rows]
	except: log_utils.error()

def getShowProgress(imdb, enrich=True):
	try:
		if not imdb: return None
		progress = customtraktsync.get(_fetchShowProgress, 15, imdb)
		if not progress and _custom_reads_paused(customBaseUrl()):
			progress = customtraktsync.cache_existing(_fetchShowProgress, imdb)
		if not progress: return None
		return _complete_progress_totals(progress, imdb) if enrich else progress
	except: log_utils.error()

def _complete_progress_totals(progress, imdb):
	"""Use catalog air dates, not the server's possibly stale aired boundary."""
	try:
		from resources.lib.database import cache as _cache
		from resources.lib.indexers import tmdb as _tmdb
		api = _tmdb.TVshows()
		lookup = _cache.get(api.IdLookup, 96, imdb, '')
		tmdb_id = str(lookup.get('id') or '') if lookup else ''
		if not tmdb_id: return progress
		meta = _cache.get(api.get_showSeasons_meta, 96, tmdb_id)
		if not isinstance(meta, dict): return progress
		seasons = {int(s['number']): s for s in progress.get('seasons', [])}
		today = datetime.utcnow().strftime('%Y-%m-%d')
		last = meta.get('last_episode_to_air') or {}
		for item in meta.get('seasons', []):
			number = int(item.get('season_number', 0))
			if not item.get('air_date') or item['air_date'] > today: continue
			if meta.get('status') == 'Returning Series' and number >= int(last.get('season_number', number)):
				raw = _cache.get(api.get_season_request, 96, tmdb_id, number)
				if not isinstance(raw, dict) or not isinstance(raw.get('episodes'), list): continue
				eligible = {int(ep['episode_number']) for ep in raw['episodes']
					if ep.get('air_date') and ep['air_date'] <= today and int(ep.get('episode_number') or 0) > 0}
			else:
				eligible = set(range(1, int(item.get('episode_count') or 0) + 1))
			season = seasons.get(number)
			if season is None:
				season = {'number': number, 'completed': 0, 'episodes': []}
				progress.setdefault('seasons', []).append(season)
				seasons[number] = season
			season['_aired_episode_numbers'] = sorted(eligible)
			season['aired'] = len(eligible)
			flags = season.get('episodes') or []
			season['completed'] = (sum(bool(ep.get('completed')) for ep in flags if int(ep.get('number', 0)) in eligible)
				if flags else min(int(season.get('completed', 0)), len(eligible)))
		included = [season for number, season in seasons.items() if number > 0 or getSetting('tv.specials') == 'true']
		progress['aired'] = sum(int(season.get('aired', 0)) for season in included)
		progress['completed'] = sum(int(season.get('completed', 0)) for season in included)
		return progress
	except:
		log_utils.error()
		return progress


def _fetchShowProgress(imdb):
	try:
		results = getCustomAsJson('shows/%s/progress/watched' % imdb, silent=True, fast=True)
		if not results or not results.get('seasons'): return None
		# Mirrors trakt.py's syncSeasons reset_at handling â€” episodes watched before
		# a reset_at timestamp don't count as completed for the current watch-through.
		reset_at = results.get('reset_at') or ''
		if reset_at:
			for s in results['seasons']:
				completed = 0
				for e in s.get('episodes', []):
					last_watched = e.get('last_watched_at') or ''
					if last_watched and last_watched >= reset_at: completed += 1
					else: e['completed'] = False
				s['completed'] = completed
		return results
	except: log_utils.error()


def syncSeasons(imdb, tvdb, tmdb=''):
	try:
		if not getCustomCredentialsInfo(): return None
		if not imdb and not tvdb and not tmdb: return None
		if imdb:
			progress = getShowProgress(imdb)
			if progress: return _seasons_from_progress(progress)
		return _local_syncSeasons(imdb, tvdb, tmdb)
	except: log_utils.error()


def _seasons_from_progress(progress):
	fully_watched = []
	counts = {}
	for s in progress.get('seasons', []):
		snum = s.get('number')
		if snum is None: continue
		if int(snum) == 0 and getSetting('tv.specials') != 'true': continue
		aired = int(s.get('aired', 0))
		episodes = s.get('episodes') or []
		# Explicit episode flags take precedence over contradictory aggregates.
		# The episode array may include scheduled, unaired episodes, so its length
		# must never increase the provider's aired count.
		last = progress.get('last_episode') or {}
		eligible = episodes
		if '_aired_episode_numbers' in s:
			eligible = [e for e in episodes if int(e.get('number', 0)) in s['_aired_episode_numbers']]
		elif last.get('season') is not None and int(last['season']) == int(snum) and last.get('number') is not None:
			eligible = [e for e in episodes if int(e.get('number', 0)) <= int(last['number'])]
		completed = sum(bool(e.get('completed')) for e in eligible) if episodes else int(s.get('completed', 0))
		if completed > aired:
			# Some servers include watched future episodes in the array. Do not
			# let those flags hide a still-unwatched aired episode.
			completed = min(completed, int(s.get('completed', completed)))
		completed = min(completed, aired)
		counts[snum] = {'total': aired, 'watched': completed, 'unwatched': max(aired - completed, 0)}
		if aired > 0 and completed == aired:
			fully_watched.append(snum)
	if not counts: return [[], {}]
	return [['%01d' % int(s) for s in sorted(fully_watched)], counts]


def _local_syncSeasons(imdb, tvdb, tmdb=''):
	try:
		episodes = customtraktsync.get_watched_episodes()
		from resources.lib.database import cache as _cache
		from resources.lib.indexers import tmdb as _tmdb
		tmdb_id = str(tmdb or '')
		if not tmdb_id and (imdb or tvdb):
			try:
				result = _cache.get(_tmdb.TVshows().IdLookup, 96, imdb, tvdb)
				tmdb_id = str(result.get('id', '')) if result else ''
			except: pass
		from resources.lib.modules.progress_identity import group_watched_shows, matches_show
		from collections import defaultdict
		by_season = defaultdict(list)
		for show in group_watched_shows(episodes or []):
			if matches_show(show, imdb, tmdb_id, tvdb):
				for s, e in show['watched_set']: by_season[s].append(e)
		season_counts = {}
		if tmdb_id:
			try:
				showSeasons = _cache.get(_tmdb.TVshows().get_showSeasons_meta, 96, tmdb_id)
				if showSeasons:
					for s in showSeasons.get('seasons', []):
						season_counts[s.get('season_number')] = s.get('episode_count', 0)
			except: pass
		result_counts = {}
		fully_watched = []
		for s in sorted(set(by_season) | set(season_counts)):
			watched_eps = by_season.get(s, [])
			if s == 0 and getSetting('tv.specials') != 'true': continue
			total = season_counts.get(s, len(set(watched_eps)))
			watched = len(set(watched_eps))
			result_counts[s] = {'total': total, 'watched': watched, 'unwatched': max(total - watched, 0)}
			if total > 0 and watched >= total: fully_watched.append(s)
		return [[str(s) for s in sorted(fully_watched)], result_counts]
	except: log_utils.error()

def getMoviesWatchedActivity():
	try: return customtraktsync.last_sync('last_history_at')
	except: log_utils.error()
	return 0

def getEpisodesWatchedActivity():
	try: return customtraktsync.last_sync('last_history_at')
	except: log_utils.error()
	return 0

def timeoutsyncMovies():
	return customtraktsync.timeout(syncMovies)

def timeoutsyncTVShows():
	return customtraktsync.timeout(syncTVShows)

def timeoutsyncSeasons(imdb, tvdb):
	try: return customtraktsync.timeout(syncSeasons, imdb, tvdb, returnNone=True)
	except: log_utils.error()

def cachesyncMovies(timeout=720):
	try: return customtraktsync.get(syncMovies, timeout)
	except: log_utils.error()

def cachesyncTVShows(timeout=720):
	try: return customtraktsync.get(syncTVShows, timeout)
	except: log_utils.error()

def cachesyncTV(imdb, tvdb):
	# refresh both show-level and season-level indicator caches after a mark-watched action
	try:
		from threading import Thread as _Thread
		threads = [_Thread(target=cachesyncTVShows, args=(0,)), _Thread(target=cachesyncSeasons, args=(imdb, tvdb, 0))]
		[i.start() for i in threads]
		[i.join() for i in threads]
	except: log_utils.error()

def cachesyncSeasons(imdb, tvdb='', timeout=720, tmdb=''):
	try:
		imdb = imdb or ''
		tvdb = tvdb or ''
		return customtraktsync.get(syncSeasons, timeout, imdb, tvdb, tmdb) if tmdb else customtraktsync.get(syncSeasons, timeout, imdb, tvdb)
	except: log_utils.error()

def seasonCount(imdb, tvdb):
	try:
		result = syncSeasons(imdb, tvdb)
		if result and len(result) > 1: return result[1]
		return {}
	except: log_utils.error()


#### Watchlist / Collection (GET /sync/watchlist/{media_type}, /sync/collection/{media_type}) ####

def get_user_watchlist(listType):
	try:
		media_type = 'movie' if listType == 'movie' else 'show'
		items = get_all_pages('/sync/watchlist/%s?extended=full' % media_type, silent=True)
		return items or []
	except: log_utils.error()
	return []

def sync_watch_list(activities=None, forced=False):
	try:
		if forced:
			items = get_user_watchlist('movie')
			customtraktsync.insert_watch_list(items, 'movies_watchlist')
			items = get_user_watchlist('tvshow')
			customtraktsync.insert_watch_list(items, 'shows_watchlist')
	except: log_utils.error()

def get_user_collection(listType):
	try:
		media_type = 'movie' if listType == 'movie' else 'show'
		items = get_all_pages('/sync/collection/%s?extended=full' % media_type, silent=True)
		return items or []
	except: log_utils.error()
	return []

def sync_collection(activities=None, forced=False):
	try:
		if forced:
			items = get_user_collection('movie')
			customtraktsync.insert_collection(items, 'movies_collection')
			items = get_user_collection('tvshow')
			customtraktsync.insert_collection(items, 'shows_collection')
	except: log_utils.error()

def sync_dropped(activities=None, forced=False):
	# Same shape as sync_watch_list()/sync_collection() above â€” Custom's confirmed
	# /sync/last_activities payload has no per-section "hidden_at"/"dropped_at" field to
	# gate an incremental resync against (see getActivity()'s comment), so this only acts
	# on the periodic forced=True pass tools.py already uses for watchlist/collection.
	try:
		if forced:
			items = get_user_dropped('movie')
			customtraktsync.insert_dropped(items, 'movies_dropped')
			items = get_user_dropped('tvshow')
			customtraktsync.insert_dropped(items, 'shows_dropped')
	except: log_utils.error()

def force_customSync():
	if not control.yesnoDialog(control.lang(32056), '', ''): return
	dialog = control.progressDialog
	dialog.create(control.addonName(), 'Preparing %s sync...' % getCustomServiceName())
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
		clr_custom = ('custom_watched_movies', 'custom_watched_episodes', 'movies_watchlist', 'shows_watchlist', 'movies_collection', 'shows_collection', 'movies_dropped', 'shows_dropped', 'watched')
		customtraktsync.delete_custom_tables(clr_custom)
		_progress('Syncing watchlist')
		sync_watch_list(forced=True)
		_progress('Syncing collection')
		sync_collection(forced=True)
		_progress('Syncing dropped')
		sync_dropped(forced=True)
		sync_watchedProgress(forced=True, progress_callback=_progress)
	finally:
		dialog.close()
	control.notification(title=getCustomServiceName(), message='Forced %s Sync Complete' % getCustomServiceName())


#### Watchlist / Collection membership (POST /sync/watchlist[/remove], /sync/collection[/remove]) ####

def _media_post(imdb, tmdb, tvdb, media_type):
	if media_type == 'movie':
		return {'movies': [{'ids': {'imdb': imdb, 'tmdb': int(tmdb) if tmdb else None}}]}
	return {'shows': [{'ids': {'imdb': imdb, 'tmdb': int(tmdb) if tmdb else None, 'tvdb': int(tvdb) if tvdb else None}}]}

def add_to_watchlist(imdb='', tmdb='', tvdb='', media_type='movie'):
	try:
		result = getCustomAsJson('/sync/watchlist', _media_post(imdb, tmdb, tvdb, media_type))
		return bool(result)
	except:
		log_utils.error()
		return False

def remove_from_watchlist(imdb='', tmdb='', tvdb='', media_type='movie'):
	try:
		result = getCustomAsJson('/sync/watchlist/remove', _media_post(imdb, tmdb, tvdb, media_type))
		return bool(result)
	except:
		log_utils.error()
		return False

def add_to_collection(imdb='', tmdb='', tvdb='', media_type='movie'):
	try:
		result = getCustomAsJson('/sync/collection', _media_post(imdb, tmdb, tvdb, media_type))
		return bool(result)
	except:
		log_utils.error()
		return False

def remove_from_collection(imdb='', tmdb='', tvdb='', media_type='movie'):
	try:
		result = getCustomAsJson('/sync/collection/remove', _media_post(imdb, tmdb, tvdb, media_type))
		return bool(result)
	except:
		log_utils.error()
		return False


#### Dropped / Hidden Progress (GET/POST /users/hidden/dropped[/remove]) ####
# Mirrors real Trakt's /users/hidden/{section} "Drop Show" feature (see trakt.py's own
# sync_hidden_progress()) â€” hides a show from progress/calendar without touching watch
# history. Uses the same ids-based SyncRequest body as watchlist/collection above rather
# than the server's item_id-based /media/show/{item_id}/drop/{action} toggle, since every
# other write call in this module operates on imdb/tmdb/tvdb and never learns a server-side
# row id.

def get_user_dropped(listType):
	try:
		media_type = 'movie' if listType == 'movie' else 'show'
		items = get_all_pages('/users/hidden/dropped?type=%s&extended=full' % media_type, silent=True)
		return items or []
	except: log_utils.error()
	return []

def add_to_dropped(imdb='', tmdb='', tvdb='', media_type='movie'):
	try:
		result = getCustomAsJson('/users/hidden/dropped', _media_post(imdb, tmdb, tvdb, media_type))
		return bool(result)
	except:
		log_utils.error()
		return False

def remove_from_dropped(imdb='', tmdb='', tvdb='', media_type='movie'):
	try:
		result = getCustomAsJson('/users/hidden/dropped/remove', _media_post(imdb, tmdb, tvdb, media_type))
		return bool(result)
	except:
		log_utils.error()
		return False


#### User Lists (GET/POST /users/me/lists[/{slug}/items[/remove]]) ####
# Endpoint shapes aren't in the confirmed OpenAPI spec â€” assumed to mirror Trakt's own
# user-list contract exactly, consistent with every other assumption in this module.

def get_user_lists():
	# Not paginated via get_all_pages(): the server doesn't honor page/limit on this
	# endpoint (it returns the full, un-paginated list every call), which made
	# get_all_pages loop until its safety cap, repeating the same lists hundreds of
	# times. A "list of lists" is small by nature, so a single plain fetch is correct.
	try:
		result = getCustomAsJson('/users/me/lists', silent=True)
		if not result: return []
		if isinstance(result, dict):
			result = next((v for v in result.values() if isinstance(v, list)), [])
		return result or []
	except:
		log_utils.error()
		return []

def get_list_items(list_id):
	# Not paginated via get_all_pages(): same non-paginating behavior confirmed on
	# /users/me/lists (see get_user_lists() above) â€” this endpoint also ignores
	# page/limit and returns the full item set every call, so a single plain fetch
	# is both correct and avoids repeating the same items until the safety cap.
	try:
		items = getCustomAsJson('/users/me/lists/%s/items' % list_id, silent=True)
		if isinstance(items, dict):
			items = next((v for v in items.values() if isinstance(v, list)), [])
		items = items or []
	except:
		log_utils.error()
		items = []
	if items:
		try:
			sample_keys = list(items[0].keys()) if isinstance(items[0], dict) else type(items[0]).__name__
			log_utils.log('CUSTOM: get_list_items(%s): %d raw items, first item keys=%s' % (list_id, len(items), sample_keys), level=log_utils.LOGDEBUG)
		except: pass
	else:
		log_utils.log('CUSTOM: get_list_items(%s): 0 raw items returned' % list_id, level=log_utils.LOGWARNING)
	return items

def create_list(name):
	try:
		result = getCustom('/users/me/lists', post={'name': name, 'privacy': 'private'})
		if not result: return None
		return list_numeric_id(result.json())
	except:
		log_utils.error()
		return None

def list_numeric_id(lst):
	# The items/add/remove endpoints require the list's numeric id (path parsing fails
	# with 422 "unable to parse string as an integer" if given the slug) â€” unlike real
	# Trakt, which accepts either. ids.trakt mirrors Trakt's own {trakt, slug} shape;
	# ids.id is a fallback in case this clone names the numeric field differently.
	try:
		ids = (lst or {}).get('ids', {}) or {}
		return str(ids.get('trakt') or ids.get('id') or '') or None
	except:
		return None

def add_to_list(list_id, imdb='', tmdb='', tvdb='', media_type='movie'):
	try:
		return bool(getCustomAsJson('/users/me/lists/%s/items' % list_id, _media_post(imdb, tmdb, tvdb, media_type)))
	except:
		log_utils.error()
		return False

def remove_from_list(list_id, imdb='', tmdb='', tvdb='', media_type='movie'):
	try:
		return bool(getCustomAsJson('/users/me/lists/%s/items/remove' % list_id, _media_post(imdb, tmdb, tvdb, media_type)))
	except:
		log_utils.error()
		return False


#### Context-menu manager (mirrors simkl.manager()/mdblist.manager() ####

def manager(name, imdb=None, tvdb=None, tmdb=None, season=None, episode=None, refresh=True, watched=None, unfinished=False, tvshow=None):
	try:
		if season: season = int(season)
		if episode: episode = int(episode)
		if episode: content_type = 'episode'
		elif season: content_type = 'season'
		elif tvdb and tvdb != 'None': content_type = 'tvshow'
		else: content_type = 'movie'
		media_type = 'movie' if content_type == 'movie' else 'tvshow'
		hc = getSetting('highlight.color')
		items = []
		if watched is not None:
			items += [(getLS(33652) % hc, 'unwatch')] if watched else [(getLS(33651) % hc, 'watch')]
		else:
			items += [(getLS(33651) % hc, 'watch')]
			items += [(getLS(33652) % hc, 'unwatch')]
		if content_type in ('movie', 'episode'):
			items += [(getLS(40076) % hc, 'scrobbleReset')]
		if content_type in ('movie', 'tvshow'):
			service_name = getCustomServiceName()
			items += [(getLS(40746) % (hc, service_name), 'watchlist_add')]
			items += [(getLS(40747) % (hc, service_name), 'watchlist_remove')]
			items += [(getLS(40748) % (hc, service_name), 'collection_add')]
			items += [(getLS(40749) % (hc, service_name), 'collection_remove')]
			items += [(getLS(40784) % (hc, service_name), 'dropped_add')]
			items += [(getLS(40785) % (hc, service_name), 'dropped_remove')]
			items += [('[COLOR %s]Add to List[/COLOR]' % hc, 'list_add')]
			items += [('[COLOR %s]Remove from List[/COLOR]' % hc, 'list_remove')]
		control.hide()
		select = control.selectDialog([i[0] for i in items], heading=control.addonInfo('name') + ' - ' + getLS(40752) % getCustomServiceName())
		if select == -1: return
		action_key = items[select][1]
		if action_key == 'watch':
			watch(content_type, name, imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, refresh=refresh)
		elif action_key == 'unwatch':
			unwatch(content_type, name, imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, refresh=refresh)
		elif action_key == 'scrobbleReset':
			scrobbleReset(imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, refresh=True)
		elif action_key == 'watchlist_add':
			if add_to_watchlist(imdb=imdb, tmdb=tmdb, tvdb=tvdb, media_type=media_type):
				sync_watch_list(forced=True)
				if refresh: control.refresh()
		elif action_key == 'watchlist_remove':
			if remove_from_watchlist(imdb=imdb, tmdb=tmdb, tvdb=tvdb, media_type=media_type):
				sync_watch_list(forced=True)
				if refresh: control.refresh()
		elif action_key == 'collection_add':
			if add_to_collection(imdb=imdb, tmdb=tmdb, tvdb=tvdb, media_type=media_type):
				sync_collection(forced=True)
				if refresh: control.refresh()
		elif action_key == 'collection_remove':
			if remove_from_collection(imdb=imdb, tmdb=tmdb, tvdb=tvdb, media_type=media_type):
				sync_collection(forced=True)
				if refresh: control.refresh()
		elif action_key == 'dropped_add':
			if add_to_dropped(imdb=imdb, tmdb=tmdb, tvdb=tvdb, media_type=media_type):
				sync_dropped(forced=True)
				if refresh: control.refresh()
		elif action_key == 'dropped_remove':
			if remove_from_dropped(imdb=imdb, tmdb=tmdb, tvdb=tvdb, media_type=media_type):
				sync_dropped(forced=True)
				if refresh: control.refresh()
		elif action_key == 'list_add':
			notify = getSetting('services.general.notifications') == 'true'
			lists = get_user_lists()
			options = [l.get('name', '') for l in lists] + ['[COLOR %s]+ New List[/COLOR]' % hc]
			list_select = control.selectDialog(options, heading=control.addonInfo('name') + ' - %s Lists' % getCustomServiceName())
			if list_select == -1: return
			if list_select == len(lists):
				new_name = control.dialog.input(getLS(32520))
				if not new_name: return
				slug = create_list(new_name)
				if not slug:
					if notify: control.notification(title=getCustomServiceName(), message='Failed to create list')
					return
			else:
				slug = list_numeric_id(lists[list_select])
			if slug and add_to_list(slug, imdb=imdb, tmdb=tmdb, tvdb=tvdb, media_type=media_type):
				if notify: control.notification(title=getCustomServiceName(), message='Added to list')
				if refresh: control.refresh()
			else:
				if notify: control.notification(title=getCustomServiceName(), message='Failed to add to list')
		elif action_key == 'list_remove':
			notify = getSetting('services.general.notifications') == 'true'
			lists = get_user_lists()
			if not lists:
				if notify: control.notification(title=getCustomServiceName(), message='No lists found')
				return
			list_select = control.selectDialog([l.get('name', '') for l in lists], heading=control.addonInfo('name') + ' - Remove From List')
			if list_select == -1: return
			slug = list_numeric_id(lists[list_select])
			if slug and remove_from_list(slug, imdb=imdb, tmdb=tmdb, tvdb=tvdb, media_type=media_type):
				if notify: control.notification(title=getCustomServiceName(), message='Removed from list')
				if refresh: control.refresh()
			else:
				if notify: control.notification(title=getCustomServiceName(), message='Failed to remove from list')
	except: log_utils.error()
