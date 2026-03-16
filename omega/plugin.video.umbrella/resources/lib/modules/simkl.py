# -*- coding: utf-8 -*-
"""
	Umbrella Add-on (added by Umbrella Dev 12/23/22)
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from resources.lib.modules import control
from resources.lib.database import simklsync, cache
from resources.lib.modules import log_utils
from datetime import datetime
from threading import Thread, Lock
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
from resources.lib.modules import cleandate
import json
from itertools import islice
import time
import calendar

getLS = control.lang
getSetting = control.setting
BASE_URL = 'https://api.simkl.com'
oauth_base_url = 'https://api.simkl.com/oauth/pin'
simkl_icon = control.joinPath(control.artPath(), 'simkl.png')
simklclientid = 'cecec23773dff71d940876860a316a4b74666c4c31ad719fe0af8bb3064a34ab'
session = requests.Session()
retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
session.mount('https://api.simkl.com', HTTPAdapter(max_retries=retries, pool_maxsize=100))
#sim_qr = control.joinPath(control.artPath(), 'simklqr.png')
highlightColor = control.setting('highlight.color')
headers = {}
last_request_time = 0.0
request_lock = Lock()

class SIMKL:
	name = "Simkl"
	def __init__(self):
		self.hosters = None
		self.hosts = None
		self.token = getSetting('simkltoken')
		self.secret = getSetting('simkl')
		self.device_code = ''
		self.user_code = ''
		self.auth_timeout = 0
		self.auth_step = 0
		

	def auth_loop(self, fromSettings=0):
		control.sleep(self.auth_step*1000)
		url = '/%s?client_id=%s&redirect_uri=urn:ietf:wg:oauth:2.0:oob' % (self.user_code, self.client_ID)
		url = oauth_base_url + url
		response = session.get(url)
		if response.status_code == 200:
			responseJson = response.json()
			if responseJson.get('result') == 'KO':
				return #
			else:
				try:
					self.progressDialog.close()
					self.secret = responseJson['access_token']
				except:
					log_utils.error()
					control.okDialog(title='default', message=40347)
					if fromSettings == 1:
						control.openSettings('8.2', 'plugin.video.umbrella')
				return
		else:
			log_utils.error()
			return

	def auth(self, fromSettings=0):
		self.secret = ''
		self.client_ID = simklclientid
        #https://api.simkl.com/oauth/pin?client_id=xxxxxxxxxxxx&redirect_uri=urn:ietf:wg:oauth:2.0:oob
        #https://api.simkl.com/oauth/pin/YYYYY?client_id=xxxxxxxxxxxx
		url = '?client_id=%s&redirect_uri=urn:ietf:wg:oauth:2.0:oob' % self.client_ID
		url = oauth_base_url + url
		response = session.get(url).json()
		line = '%s\n%s\n%s'
		if control.setting('dialogs.useumbrelladialog') == 'true':
			from resources.lib.modules import tools
			sim_qr = tools.make_qr(f"https://simkl.com/pin/{response['user_code']}", 'simkl_qr.png')
			self.progressDialog = control.getProgressWindow(getLS(40346), sim_qr, 1)
			self.progressDialog.set_controls()
		else:
			self.progressDialog = control.progressDialog
			self.progressDialog.create(getLS(40346))
		self.progressDialog.update(-1, line % (getLS(32513) % (highlightColor, 'https://simkl.com/pin/'), getLS(32514) % (highlightColor,response['user_code']), getLS(40390)))
		self.auth_timeout = int(response['expires_in'])
		self.auth_step = int(response['interval'])
		self.device_code = response['device_code']
		self.user_code = response['user_code']        
		while self.secret == '':
			if self.progressDialog.iscanceled():
				self.progressDialog.close()
				break
			self.auth_loop(fromSettings=fromSettings)
		if self.secret: self.save_token(fromSettings=fromSettings)

	def save_token(self, fromSettings=0):
		try:
			self.token = self.secret
			control.sleep(500)
			control.setSetting('simkltoken', self.token)
			username, joindate = self.get_account_info(self.token)
			control.notification(message="Simkl Authorized", icon=simkl_icon)
			if not control.yesnoDialog('Do you want to set Simkl as your service for your watched and unwatched indicators?','','','Indicators', 'No', 'Yes'):
				if fromSettings == 1:
					control.openSettings('8.2', 'plugin.video.umbrella')
				force_simklSync(silent=True)
				return True, None
			force_simklSync(silent=True)
			control.homeWindow.setProperty('umbrella.updateSettings', 'false')
			control.setSetting('indicators.alt', '2')
			control.homeWindow.setProperty('umbrella.updateSettings', 'true')
			control.setSetting('indicators', 'Simkl')
			if fromSettings == 1:
				control.openSettings('8.2', 'plugin.video.umbrella')
			return True, None
		except:
			log_utils.error('Simkl Authorization Failed : ')
			if fromSettings == 1:
				control.openSettings('8.2', 'plugin.video.umbrella')
			return False, None

	def reset_authorization(self, fromSettings=0):
		try:
			control.setSetting('simkltoken', '')
			control.setSetting('simklusername', '')
			control.setSetting('simkljoindate', '')
			from resources.lib.database import simklsync
			clr_simklsync = {
                    'movies_plantowatch': True,
                    'shows_plantowatch': True,
                    'shows_watching': True,
                    'shows_hold': True,
                    'movies_dropped': True,
                    'shows_dropped': True,
                    'watched': True,
                    'movies_completed': True,
                    'shows_completed': True
                }
			simklsync.delete_tables(clr_simklsync)
			if getSetting('indicators.alt') == '2':
				control.setSetting('indicators.alt', '0')
				control.setSetting('indicators', 'Local')
			if fromSettings == 1:
				control.openSettings('8.2', 'plugin.video.umbrella')
			control.dialog.ok(getLS(40342), getLS(32320))
		except: log_utils.error()

	def get_account_info(self, token=None):
		try:
			url = "https://api.simkl.com/users/settings"
			if token:
				headers['Authorization'] = 'Bearer %s' % token
			else:
				headers['Authorization'] = 'Bearer %s' % getSetting('simkltoken')
			headers['simkl-api-key'] = simklclientid
			headers['User-Agent'] = 'Umbrella/%s' % control.addon('plugin.video.umbrella').getAddonInfo('version')
			response = session.post(url, headers=headers, timeout=20)
			if response.status_code == 200:
				response = response.json()
				account_info = response.get('user')
				joined = account_info.get('joined_at')
				user = account_info.get('name','')
				control.setSetting('simklusername', account_info.get('name',''))
				control.setSetting('simkljoindate', joined)
				return user, str(joined)
			else:
				log_utils.error()
				return None, None
		except: log_utils.error()

	def acount_info_dialog(self):
		try:
			if not getSetting('simklusername'):
				username, joined = self.get_account_info()
				control.sleep(1000)
			else:
				username = getSetting('simklusername')
				joined = getSetting('simkljoindate')
			heading = getLS(40342).upper()
			items = []
			items += ['Name: %s' % username]
			items += ['Joined: %s' % joined]
			return control.selectDialog(items, heading=heading)
		except: log_utils.error()

def throttle():
	"""Ensure at most 1 Simkl API request per second to avoid rate limiting."""
	global last_request_time
	with request_lock:
		now = time.time()
		wait = 1.0 - (now - last_request_time)
		if wait > 0:
			time.sleep(wait)
		last_request_time = time.time()

def get_request(url):
	throttle()
	try:
		if not url.startswith(BASE_URL): url = urljoin(BASE_URL, url)
		_version = control.addon('plugin.video.umbrella').getAddonInfo('version')
		if '?' not in url:
			url += '?client_id=%s&app-name=umbrella&app-version=%s' % (simklclientid, _version)
		else:
			url += '&client_id=%s&app-name=umbrella&app-version=%s' % (simklclientid, _version)
		headers['Authorization'] = 'Bearer %s' % getSetting('simkltoken')
		headers['simkl-api-key'] = simklclientid
		headers['User-Agent'] = 'Umbrella/%s' % _version
		try: response = session.get(url, headers=headers, timeout=20)
		except requests.exceptions.SSLError:
			response = session.get(url, headers=headers, verify=False)
	except requests.exceptions.ConnectionError:
		control.notification(message=40349)
		log_utils.error()
		return None
	try:
		if response.status_code in (200, 201): return response.json()
		elif response.status_code == 404:
			if getSetting('debug.level') == '1':
				log_utils.log('Simkl get_request() failed: (404:NOT FOUND) - URL: %s' % url, level=log_utils.LOGDEBUG)
			return '404:NOT FOUND'
		elif 'Retry-After' in response.headers: # API REQUESTS ARE BEING THROTTLED, INTRODUCE WAIT TIME (TMDb removed rate-limit on 12-6-20)
			throttleTime = response.headers['Retry-After']
			control.notification(message='SIMKL Throttling Applied, Sleeping for %s seconds' % throttleTime)
			control.sleep((int(throttleTime) + 1) * 1000)
			return get_request(url)
		else:
			if getSetting('debug.level') == '1':
				log_utils.log('SIMKL get_request() failed: URL: %s\n                       msg : SIMKL Response: %s' % (url, response.text), __name__, log_utils.LOGDEBUG)
			return None
	except:
		log_utils.error()
		return None

def getSimklAsJson(url, post=None, silent=False):
	try:
		from resources.lib.modules import simkl
		if post: r = simkl.post_request(url, data=post)
		else: r = get_request(url)
		if not r: return
		if '/sync/all-items/shows/watching' in url: return r['shows']
		r = r.json()
		return r
	except: log_utils.error()

def simkl_list(url):
	if not url: return
	url = url % simklclientid
	try:
		#result = cache.get(self.get_request, 96, url % self.API_key)
		result = get_request(url)
		if result is None: return
		items = result
	except: return
	simkllist = [] ; sortList = []
	next = ''
	for item in items:
		try:
			values = {}
			values['next'] = next 
			values['tmdb'] = str(item.get('ids').get('tmdb')) if item.get('ids').get('tmdb') else ''
			sortList.append(values['tmdb'])
			values['imdb'] = ''
			values['tvdb'] = ''
			values['metacache'] = False 
			simkllist.append(values)
		except:
			log_utils.error()
	return simkllist

def simklCompleted(url):
	if not url: return
	try:
		#result = cache.get(self.get_request, 96, url % self.API_key)
		result = get_request(url)
		if result is None: return
		items = result['movies']
	except: return
	simkllist = [] ; sortList = []
	next = ''
	for item in items:
		try:
			values = {}
			values['next'] = next 
			values['tmdb'] = str(item['movie'].get('ids').get('tmdb')) if item['movie'].get('ids').get('tmdb') else ''
			sortList.append(values['tmdb'])
			values['imdb'] = item['movie'].get('ids').get('imdb')
			values['tvdb'] = item['movie'].get('ids').get('tvdb')
			values['metacache'] = False 
			simkllist.append(values)
		except:
			log_utils.error()
	return simkllist

def simklPlantowatch(url):
	if not url: return
	try:
		#result = cache.get(self.get_request, 96, url % self.API_key)
		result = get_request(url)
		if result is None: return
		items = result['movies']
	except: return
	simkllist = [] ; sortList = []
	next = ''
	for item in items:
		try:
			values = {}
			values['next'] = next 
			values['tmdb'] = str(item['movie'].get('ids').get('tmdb')) if item['movie'].get('ids').get('tmdb') else ''
			sortList.append(values['tmdb'])
			values['imdb'] = item['movie'].get('ids').get('imdb')
			values['tvdb'] = item['movie'].get('ids').get('tvdb')
			values['metacache'] = False 
			simkllist.append(values)
		except:
			log_utils.error()
	return simkllist


def watch(content_type, name, imdb=None, tvdb=None, season=None, episode=None, refresh=True):
	control.busy()
	success = False
	if content_type == 'movie':
		success = markMovieAsWatched(imdb)
		if success: update_syncMovies(imdb)
	elif content_type == 'tvshow':
		success = markTVShowAsWatched(imdb, tvdb)
		if success: cachesyncTV(imdb, tvdb)
	elif content_type == 'season':
		success = markSeasonAsWatched(imdb, tvdb, season)
		if success: cachesyncTV(imdb, tvdb)
	elif content_type == 'episode':
		success = markEpisodeAsWatched(imdb, tvdb, season, episode)
		cachesyncTV(imdb, tvdb)  # refresh regardless — episode may already be in history
	else: success = False
	control.hide()
	if refresh: control.refresh()
	control.trigger_widget_refresh()
	if season and not episode: name = '%s-Season%s...' % (name, season)
	if season and episode: name = '%s-S%sxE%02d...' % (name, season, int(episode))
	if getSetting('simkl.general.notifications') == 'true':
		if success is True: control.notification(title=40342, message=getLS(40561) % ('[COLOR %s]%s[/COLOR]' % (highlightColor, name)))
		else: control.notification(title=40342, message=getLS(40560) % ('[COLOR %s]%s[/COLOR]' % (highlightColor, name)))
	if not success: log_utils.log(getLS(40560) % name + ' : ids={imdb: %s, tvdb: %s}' % (imdb, tvdb), __name__, level=log_utils.LOGDEBUG)

def unwatch(content_type, name, imdb=None, tvdb=None, season=None, episode=None, refresh=True):
	control.busy()
	success = False
	if content_type == 'movie':
		success = markMovieAsNotWatched(imdb)
		update_syncMovies(imdb, remove_id=True)
	elif content_type == 'tvshow':
		success = markTVShowAsNotWatched(imdb, tvdb)
		cachesyncTV(imdb, tvdb) 
	elif content_type == 'season':
		success = markSeasonAsNotWatched(imdb, tvdb, season)
		cachesyncTV(imdb, tvdb)
	elif content_type == 'episode':
		success = markEpisodeAsNotWatched(imdb, tvdb, season, episode)
		cachesyncTV(imdb, tvdb)
	else: success = False
	control.hide()
	if refresh: control.refresh()
	control.trigger_widget_refresh()
	if season and not episode: name = '%s-Season%s...' % (name, season)
	if season and episode: name = '%s-S%sxE%02d...' % (name, season, int(episode))
	if getSetting('simkl.general.notifications') == 'true':
		if success is True: control.notification(title=40342, message=getLS(40563) % ('[COLOR %s]%s[/COLOR]' % (highlightColor, name)))
		else: control.notification(title=40342, message=getLS(40562) % ('[COLOR %s]%s[/COLOR]' % (highlightColor, name)))
	if not success: log_utils.log(getLS(40562) % name + ' : ids={imdb: %s, tvdb: %s}' % (imdb, tvdb), __name__, level=log_utils.LOGDEBUG)

def _ts_to_iso(unix_ts):
	"""Convert Unix timestamp int to ISO8601 string for Simkl date_from parameter."""
	return datetime.utcfromtimestamp(unix_ts).strftime('%Y-%m-%dT%H:%M:%SZ')

def getSimKLCredentialsInfo():
	token = getSetting('simkltoken')
	if (token == ''): return False
	return True

def getSimKLIndicatorsInfo():
	indicators = getSetting('indicators.alt')
	indicators = True if indicators == '2' else False
	return indicators

def post_request(url, data=None):
	throttle()
	if type(data) == dict or type(data) == list: data = json.dumps(data)
	if not url.startswith(BASE_URL): url = urljoin(BASE_URL, url)
	_version = control.addon('plugin.video.umbrella').getAddonInfo('version')
	if '?' not in url:
		url += '?client_id=%s&app-name=umbrella&app-version=%s' % (simklclientid, _version)
	else:
		url += '&client_id=%s&app-name=umbrella&app-version=%s' % (simklclientid, _version)
	headers['Authorization'] = 'Bearer %s' % getSetting('simkltoken')
	headers['simkl-api-key'] = simklclientid
	headers['User-Agent'] = 'Umbrella/%s' % _version
	try:
		response = session.post(url, data=data, headers=headers, timeout=20)
	except requests.exceptions.ConnectionError:
		control.notification(message=40349)
		log_utils.error()
		return None
	try:
		if response.status_code in (200, 201): 
			return response.json()
		else:
			if getSetting('debug.level') == '1':
				log_utils.log('SIMKL post_request() failed: URL: %s\n                       msg : SIMKL Response: %s' % (url, response.text), __name__, log_utils.LOGDEBUG)
			return None
	except:
		log_utils.error()
		return None

def markMovieAsWatched(imdb):
	try:
		timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		data = {"movies": [{"watched_at": timestamp,"ids": {"imdb": imdb}}]}
		from resources.lib.modules import simkl
		result = simkl.post_request('/sync/history', data)
		if not result: return False
		result = len(result.get('not_found', {}).get('movies', [])) == 0
		if result: simklsync.remove_plan_to_watch(imdb, 'movies_plantowatch')
		if getSetting('debug.level') == '1':
			log_utils.log('SimKL markMovieAsWatched IMDB: %s Result: %s' % (imdb, result), level=log_utils.LOGDEBUG)
		return result
	except: log_utils.error()

def markMovieAsNotWatched(imdb):
	try:
		from resources.lib.modules import simkl
		result = simkl.post_request('/sync/history/remove', {"movies": [{"ids": {"imdb": imdb}}]})
		return result['deleted']['movies'] != 0
	except: log_utils.error()

def markTVShowAsWatched(imdb, tvdb):
	try:
		from resources.lib.modules import simkl
		#result = simkl.post_request('/sync/history', {"shows": [{"ids": {"imdb": imdb, "tvdb": tvdb}}]})
		result = simkl.post_request('/sync/add-to-list', {"shows": [{"to": "completed", "ids": {"imdb": imdb, "tvdb": tvdb}}]})
		if not result: return False
		if result.get('not_found', {}).get('shows') and tvdb: # show not found, retry with tvdb only
			control.sleep(1000) # POST 1 call per sec rate-limit
			result = simkl.post_request('/sync/history', {"shows": [{"ids": {"tvdb": tvdb}}]})
			if not result: return False
		success = len(result.get('not_found', {}).get('shows', [])) == 0
		if success:
			simklsync.remove_hold_item(imdb)
			simklsync.remove_plan_to_watch(imdb, 'shows_plantowatch')
		return success
	except: log_utils.error()

def markTVShowAsNotWatched(imdb, tvdb):
	try:
		from resources.lib.modules import simkl
		result = simkl.post_request('/sync/history/remove', {"shows": [{"ids": {"imdb": imdb, "tvdb": tvdb}}]})
		if not result: return False
		if result.get('not_found', {}).get('shows') and tvdb: # show not found, retry with tvdb only
			control.sleep(1000) # POST 1 call per sec rate-limit
			result = simkl.post_request('/sync/history/remove', {"shows": [{"ids": {"tvdb": tvdb}}]})
			if not result: return False
		return len(result.get('not_found', {}).get('shows', [])) == 0
	except: log_utils.error()

def markSeasonAsWatched(imdb, tvdb, season):
	try:
		from resources.lib.modules import simkl
		season = int('%01d' % int(season))
		result = simkl.post_request('/sync/history', {"shows": [{"seasons": [{"number": season}], "ids": {"imdb": imdb, "tvdb": tvdb}}]})
		if not result: return False
		if result.get('not_found', {}).get('shows') and tvdb: # show not found, retry with tvdb only
			control.sleep(1000) # POST 1 call per sec rate-limit
			result = simkl.post_request('/sync/history', {"shows": [{"seasons": [{"number": season}], "ids": {"tvdb": tvdb}}]})
			if not result: return False
		success = len(result.get('not_found', {}).get('shows', [])) == 0
		if success:
			simklsync.remove_hold_item(imdb)
			simklsync.remove_plan_to_watch(imdb, 'shows_plantowatch')
		return success
	except: log_utils.error()

def markSeasonAsNotWatched(imdb, tvdb, season):
	try:
		from resources.lib.modules import simkl
		season = int('%01d' % int(season))
		result = simkl.post_request('/sync/history/remove', {"shows": [{"seasons": [{"number": season}], "ids": {"imdb": imdb, "tvdb": tvdb}}]})
		if not result: return False
		if result['deleted']['episodes'] == 0 and tvdb: # fail, trying again with tvdb as fallback
			control.sleep(1000) # POST 1 call per sec rate-limit
			result = SIMKL.post_request('/sync/history/remove', {"shows": [{"seasons": [{"number": season}], "ids": {"tvdb": tvdb}}]})
			if not result: return False
		return result['deleted']['episodes'] != 0
	except: log_utils.error()

def _simkl_resolve_episode(simkl_mod, tvdb, imdb, tmdb_season, tmdb_episode):
	"""Translate TMDB season/episode to TVDB via:
	   1. TVDB episode ID from TMDB external_ids (fastest, most accurate)
	   2. Airdate matching against Simkl episode list (fallback)
	   Returns Simkl post_request result dict, or None if all lookups fail."""
	try:
		from resources.lib.database import cache as _cache
		from resources.lib.indexers import tmdb as _tmdb
		# Get TMDB show ID (cached from browsing)
		tmdb_result = _cache.get(_tmdb.TVshows().IdLookup, 96, imdb, tvdb)
		if not tmdb_result:
			return None
		tmdb_id = str(tmdb_result.get('id', ''))
		if not tmdb_id:
			return None
		tmdb_obj = _tmdb.TVshows()

		# Method 1: TVDB episode ID from TMDB external_ids
		ext_ids = tmdb_obj.get_request('%stv/%s/season/%s/episode/%s/external_ids?api_key=%s' % (_tmdb.base_link, tmdb_id, tmdb_season, tmdb_episode, tmdb_obj.API_key))
		tvdb_ep_id = ext_ids.get('tvdb_id') if ext_ids else None
		if tvdb_ep_id:
			# M1a: episode-level TVDB ID only (developer-confirmed format)
			control.sleep(1000)
			result = simkl_mod.post_request('/sync/history', {"episodes": [{"ids": {"tvdb": tvdb_ep_id}}]})
			if result and result.get('added', {}).get('episodes', 0):
				return result
			# M1b: episode-level TVDB ID nested inside show IDs (no season/episode numbers)
			control.sleep(1000)
			show_ids = {}
			if imdb: show_ids['imdb'] = imdb
			if tvdb: show_ids['tvdb'] = tvdb
			result = simkl_mod.post_request('/sync/history', {"shows": [{"ids": show_ids, "episodes": [{"ids": {"tvdb": tvdb_ep_id}}]}]})
			if result and result.get('added', {}).get('episodes', 0):
				return result

		# Method 2: Airdate-based matching against Simkl episode list
		raw = _cache.get(tmdb_obj.get_season_request, 96, tmdb_id, tmdb_season)
		tmdb_airdate = ''
		tmdb_ep_title = ''
		for ep in (raw or {}).get('episodes', []):
			if int(ep.get('episode_number', -1)) == tmdb_episode:
				tmdb_airdate = ep.get('air_date', '')[:10]
				tmdb_ep_title = (ep.get('name') or '').strip().lower()
				break
		if not tmdb_airdate:
			return None
		# Find Simkl show ID — try tvdb first (reliable for TV), fall back to imdb
		simkl_info = None
		if tvdb:
			simkl_info = simkl_mod.get_request('/search/id?source=tvdb&id=%s&extended=full' % tvdb)
		if not simkl_info and imdb:
			simkl_info = simkl_mod.get_request('/search/id?source=imdb&id=%s&extended=full' % imdb)
		if not simkl_info:
			return None
		simkl_id = simkl_info[0].get('ids', {}).get('simkl') if isinstance(simkl_info, list) else None
		if not simkl_id:
			return None
		# Search nearby seasons for matching airdate
		for try_season in [tmdb_season, tmdb_season - 1, tmdb_season + 1, tmdb_season + 2]:
			if try_season < 0: continue
			control.sleep(500)
			eps = simkl_mod.get_request('/tv/%s/episodes/%s?extended=full' % (simkl_id, try_season))
			if not eps: continue
			date_matches = [e for e in eps if str(e.get('date', ''))[:10] == tmdb_airdate]
			if not date_matches: continue
			# Disambiguate when multiple episodes share the same airdate
			if len(date_matches) == 1:
				chosen = date_matches[0]
			else:
				# Tiebreaker 1: exact title match (case-insensitive)
				chosen = None
				if tmdb_ep_title:
					title_hits = [e for e in date_matches if (e.get('title') or '').strip().lower() == tmdb_ep_title]
					if len(title_hits) == 1:
						chosen = title_hits[0]
				# Tiebreaker 2: closest episode number to TMDB episode number
				if not chosen:
					chosen = min(date_matches, key=lambda e: abs(int(e.get('episode', tmdb_episode)) - tmdb_episode))
			tvdb_s = int(chosen.get('season', try_season))
			tvdb_e = int(chosen.get('episode', tmdb_episode))
			corrected_body = {"seasons": [{"episodes": [{"number": tvdb_e}], "number": tvdb_s}]}
			control.sleep(1000)
			return simkl_mod.post_request('/sync/history', {"shows": [{**corrected_body, "ids": {"tvdb": tvdb}}]})
	except: log_utils.error()
	return None

def markEpisodeAsWatched(imdb, tvdb, season, episode):
	try:
		season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
		from resources.lib.modules import simkl
		ep_body = {"seasons": [{"episodes": [{"number": episode}], "number": season}]}
		# Attempt 1: imdb + tvdb (TMDB episode numbers)
		result = simkl.post_request('/sync/history', {"shows": [{**ep_body, "ids": {"imdb": imdb, "tvdb": tvdb}}]})
		if not result: result = {}
		if result.get('added', {}).get('episodes', 0) == 0:
			# Attempt 2: tvdb only
			if tvdb:
				control.sleep(1000)
				result = simkl.post_request('/sync/history', {"shows": [{**ep_body, "ids": {"tvdb": tvdb}}]})
				if not result: result = {}
			if result.get('added', {}).get('episodes', 0) == 0:
				# Attempt 3: TVDB episode ID (bypasses numbering mismatch) then airdate fallback
				resolved = _simkl_resolve_episode(simkl, tvdb, imdb, season, episode)
				if resolved: result = resolved
		if result.get('added', {}).get('episodes', 0) > 0:
			result = True
		elif not result.get('not_found', {}).get('shows') and not result.get('not_found', {}).get('episodes'):
			result = True  # episode already in Simkl history — Simkl deduplicates
		else:
			result = False
		if result:
			simklsync.remove_hold_item(imdb)
			simklsync.remove_plan_to_watch(imdb, 'shows_plantowatch')
		if getSetting('debug.level') == '1':
			log_utils.log('SimKL markEpisodeAsWatched IMDB: %s TVDB: %s Season: %s Episode: %s Result: %s' % (imdb, tvdb, season, episode, result), level=log_utils.LOGDEBUG)
		return result
	except: log_utils.error()

def markEpisodeAsNotWatched(imdb, tvdb, season, episode):
	try:
		season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
		from resources.lib.modules import simkl
		result = simkl.post_request('/sync/history/remove', {"shows": [{"seasons": [{"episodes": [{"number": episode}], "number": season}], "ids": {"imdb": imdb, "tvdb": tvdb}}]})
		if not result: return False
		if result['deleted']['episodes'] == 0 and tvdb:
			control.sleep(1000)
			result = simkl.post_request('/sync/history/remove', {"shows": [{"seasons": [{"episodes": [{"number": episode}], "number": season}], "ids": {"tvdb": tvdb}}]})
			if not result: return False
		return result['deleted']['episodes'] !=0
	except: log_utils.error()

def seasonCount(imdb, tvdb): # return counts for all seasons of a show from simklsync.db
	try:
		counts = simklsync.cache_existing(syncSeasons, imdb, tvdb)
		if not counts: return
		return counts[1]
	except:
		log_utils.error()
		return None

def timeoutsyncSeasons(imdb, tvdb):
	try:
		timeout = simklsync.timeout(syncSeasons, imdb, tvdb, returnNone=True) # returnNone must be named arg or will end up considered part of "*args"
		return timeout
	except: log_utils.error()

def update_syncMovies(imdb, remove_id=False):
	try:
		indicators = simklsync.cache_existing(syncMovies)
		if remove_id: indicators.remove(imdb)
		else: indicators.append(imdb)
		key = simklsync._hash_function(syncMovies, ())
		simklsync.cache_insert(key, repr(indicators))
	except: log_utils.error()

def cachesyncMovies(timeout=0):
	indicators = simklsync.get(syncMovies, timeout)
	return indicators

def syncMovies():
	try:
		from resources.lib.modules import simkl
		if not getSimKLCredentialsInfo(): return
		from resources.lib.modules import simkl
		indicators = simkl.post_request('/sync/all-items/movies/completed') #only need completed status for movies
		if not indicators: return None
		indicators = indicators['movies']
		indicators = [i['movie']['ids'] for i in indicators]
		indicators = [str(i['imdb']) for i in indicators if 'imdb' in i]
		return indicators
	except: log_utils.error()

def cachesyncTV(imdb, tvdb):  # Sync full watched shows then sync imdb_id "season indicators" and "season counts"
	try:
		with ThreadPoolExecutor() as executor:
			# Submit tasks to the thread pool
			executor.submit(cachesyncTVShows)
			executor.submit(cachesyncSeasons, imdb, tvdb)
		simklsync.insert_syncSeasons_at()
	except Exception as e:
		log_utils.error(f"Error in cachesyncTV: {e}")

def cachesyncTVShows(timeout=0):
	try:
		indicators = simklsync.get(syncTVShows, timeout)
		return indicators
	except:
		indicators = ''
		return indicators

def syncTVShows(): # sync all watched shows ex. [({'imdb': 'tt12571834', 'tvdb': '384435', 'tmdb': '105161', 'trakt': '163639'}, 16, [(1, 16)]), ({'imdb': 'tt11761194', 'tvdb': '377593', 'tmdb': '119845', 'trakt': '158621'}, 2, [(1, 1), (1, 2)])]
	try:
		from resources.lib.modules import simkl
		if not getSimKLCredentialsInfo():
			return
		data = simkl.post_request('/sync/all-items/shows/?extended=full', None)
		if not data:
			return None
		valid_statuses = {"watching", "completed", "hold", "dropped", "plantowatch"}

		indicators = [
			(
				{
					'imdb': show['show']['ids'].get('imdb', None),
					'tvdb': str(show['show']['ids'].get('tvdb', '')),
					'tmdb': str(show['show']['ids'].get('tmdb', '')),
					'simkl': str(show['show']['ids'].get('simkl', '')),
				},
				show['total_episodes_count'] - show['not_aired_episodes_count'],
				[
					(season['number'], episode['number'])
					for season in show.get('seasons', [])  # Default to an empty list if 'seasons' is missing
					for episode in season.get('episodes', [])  # Default to an empty list if 'episodes' is missing
				],
			)
			for show in data.get('shows', [])  # Default to an empty list if 'shows' is missing
			if show.get('status') in valid_statuses  # Check if status is in the set of valid statuses
		]

		indicators = [(i[0], int(i[1]), i[2]) for i in indicators]
		return indicators
	except: log_utils.error()

def chunked_iterator(iterable, size):
    iterator = iter(iterable)
    while chunk := list(islice(iterator, size)):
        yield chunk

def batchCacheSyncSeason(data):
    #Process all items in data in chunks because simkl api had limit of 100 items per request
    extended_param = 'full,specials' if getSetting('tv.specials') == 'true' else 'full'

    for chunk in chunked_iterator(data, 100):  # Process chunks sequentially to avoid request bursts
        formatted_data = [show for show in chunk]
        results = post_request(f'/sync/watched?extended={extended_param}', data=formatted_data)
        if not results:
            continue
        with ThreadPoolExecutor() as executor:  # Parallel cache writes only (no API calls)
            for show in chunk:
                imdb = show.get('imdb')
                tvdb = show.get('tvdb')
                simkl_id = show.get('simkl')
                executor.submit(cachesyncSeasons, imdb, tvdb, simkl_id, 0, results)

def cachesyncSeasons(imdb, tvdb, simkl_id=None, timeout=0, data=None):
	try:
		imdb = imdb or ''
		tvdb = tvdb or ''
		indicators = simklsync.get(syncSeasons, timeout, imdb, tvdb, simkl_id=simkl_id, data=data) # named var and data not included in function md5_hash
		return indicators
	except: log_utils.error()

def syncSeasons(imdb, tvdb, simkl_id=None, data=None): # season indicators and counts for watched shows ex. [['1', '2', '3'], {1: {'total': 8, 'watched': 8, 'unwatched': 0}, 2: {'total': 10, 'watched': 10, 'unwatched': 0}}]
	indicators_and_counts = []
	try:
		if all(not value for value in (imdb, tvdb, simkl_id)): return
		from resources.lib.modules import simkl
		if not getSimKLCredentialsInfo() : return
		id = imdb or simkl_id
		if not id and tvdb:
			log_utils.log('syncSeasons missing imdb_id, pulling simkl id from watched shows database', level=log_utils.LOGDEBUG)
			db_watched = simklsync.cache_existing(syncTVShows) # pull simkl ID from db because imdb ID is missing
			ids = [i[0] for i in db_watched if i[0].get('tvdb') == tvdb]
			id = ids[0].get('simkl', '') if ids[0].get('simkl') else ''
			if not id:
				log_utils.log("syncSeasons FAILED: missing required imdb and simkl ID's for tvdb=%s" % tvdb, level=log_utils.LOGDEBUG)
				return
		if not data:
			if getSetting('tv.specials') == 'true':
				data = [{"imdb": id}]
				#/sync/watched?extended=counters
				from resources.lib.modules import simkl
				results = simkl.post_request('/sync/watched?extended=full,specials', data=data)
			else:
				
				data = [{"imdb": id}]
				from resources.lib.modules import simkl
				results = simkl.post_request('/sync/watched?extended=full', data=data)
			if not results: return
		else:
			results = data
		show_data = results
		for show in show_data:
			show_imdb = show.get('imdb')
			show_tvdb = str(show.get('tvdb', ''))
			if show_imdb != imdb and show_tvdb != str(tvdb or ''):
				continue
			seasons = show.get('seasons', [])

			indicators = [(season['number'], [ep['watched'] for ep in season.get('episodes', [])]) for season in seasons]
			indicators = ['%01d' % int(season[0]) for season in indicators if all(season[1])]
			indicators_and_counts.append(indicators)

			counts = {}
			for season in seasons:
				s_num = season['number']
				eps = season.get('episodes', [])
				total = season.get('episodes_aired', len(eps))
				watched_ct = season.get('episodes_watched', sum(1 for ep in eps if ep.get('watched')))
				counts[s_num] = {
					'total': total,
					'watched': watched_ct,
					'unwatched': max(0, total - watched_ct)
				}
			indicators_and_counts.append(counts)
		
		# indicators = [(i['number'], [x['completed'] for x in i['episodes']]) for i in seasons]
		# indicators = ['%01d' % int(i[0]) for i in indicators if False not in i[1]]
		# indicators_and_counts.append(indicators)
		# counts = {season['number']: {'total': season['aired'], 'watched': season['completed'], 'unwatched': season['aired'] - season['completed']} for season in seasons}
		# indicators_and_counts.append(counts)
		return indicators_and_counts
	except:
		log_utils.error()
		return None

def timeoutsyncTVShows():
	timeout = simklsync.timeout(syncTVShows)
	return timeout

def getProgressActivity(activities=None):
	try:
		if activities: i = activities
		else: i = get_request('/sync/activities')
		if not i: return 0
		if type(i) != dict: activities_dict = json.loads(i)
		else: activities_dict = i
		tv_shows_watching = activities_dict["tv_shows"].get("watching")
		if not tv_shows_watching:
			return 0
		try:
			# First attempt using datetime.strptime
			#watching_timestamp = int(datetime.strptime(tv_shows_watching[:-1], "%Y-%m-%dT%H:%M:%S").timestamp())
			refdatim = datetime.fromtimestamp(time.mktime(time.strptime(tv_shows_watching[:-1], "%Y-%m-%dT%H:%M:%S")))
			watching_timestamp = int(refdatim.timestamp())
		except Exception as e:
			log_utils.error('Exception in getProgressActivity: %s' % str(e), log_utils.LOGINFO)
		return watching_timestamp
	except: 
		log_utils.error() 
		return 0

def getPlantowatchActivity(activities=None):
	try:
		if activities: i = activities
		else: i = getSimklAsJson('/sync/activities')
		if not i: return 0
		if type(i) != dict: activities_dict = json.loads(i)
		else: activities_dict = i
		movies_plantowatch = activities_dict["movies"].get("plantowatch")
		tv_shows_plantowatch = activities_dict["tv_shows"].get("plantowatch")
		timestamps = []
		for dt in [movies_plantowatch, tv_shows_plantowatch]:
			if dt:
				try:
					#timestamps.append(datetime.strptime(dt[:-1], "%Y-%m-%dT%H:%M:%S"))
					timestamps.append(datetime.fromtimestamp(time.mktime(time.strptime(dt[:-1], "%Y-%m-%dT%H:%M:%S"))))
				except Exception as e:
					log_utils.error('Exception in getPlantowatchActivity: %s' % str(e), log_utils.LOGINFO)
					
		newest_timestamp = int(max(timestamps).timestamp()) if timestamps else None
		if not newest_timestamp:
			return 0
		return newest_timestamp
	except: 
		return 0

def getHistoryListedActivity(activities=None):
	try:
		if activities: i = activities
		else: i = getSimklAsJson('/sync/activities')
		if not i: return 0
		if type(i) != dict: activities_dict = json.loads(i)
		else: activities_dict = i
		movies_completed = activities_dict["movies"].get("completed")
		tv_shows_completed = activities_dict["tv_shows"].get("completed")
		timestamps = []
		for dt in [movies_completed, tv_shows_completed]:
			if dt:
				try:
					#timestamps.append(datetime.strptime(dt[:-1], "%Y-%m-%dT%H:%M:%S"))
					timestamps.append(datetime.fromtimestamp(time.mktime(time.strptime(dt[:-1], "%Y-%m-%dT%H:%M:%S"))))
				except Exception as e:
					log_utils.error('Exception in getHistoryListedActivity: %s' % str(e), log_utils.LOGINFO)
		newest_timestamp = int(max(timestamps).timestamp()) if timestamps else None
		if not newest_timestamp:
			return 0
		return newest_timestamp
	except: 
		return 0

def getEpisodesWatchedActivity(activities=None):
	try:
		if activities: i = activities
		else: i = getSimklAsJson('/sync/activities')
		if not i: return 0
		if type(i) != dict: activities_dict = json.loads(i)
		else: activities_dict = i
		tv_shows_watching = activities_dict["tv_shows"].get("all")
		try:
			# First attempt using datetime.strptime
			refdatim = datetime.fromtimestamp(time.mktime(time.strptime(tv_shows_watching[:-1], "%Y-%m-%dT%H:%M:%S")))
			watching_timestamp = int(refdatim.timestamp())
		except Exception as e:
			log_utils.error('Exception in getEpisodesWatchedActivity: %s' % str(e), log_utils.LOGINFO)
		if not watching_timestamp:
			return 0
		return watching_timestamp
	except: 
		log_utils.error() 
		return 0

def getMoviesWatchedActivity(activities=None):
	try:
		if activities: i = activities
		else: i = getSimklAsJson('/sync/activities')
		if not i: return 0
		if type(i) != dict: activities_dict = json.loads(i)
		else: activities_dict = i
		movies_watching = activities_dict["movies"].get("completed")
		try:
			refdatim = datetime.fromtimestamp(time.mktime(time.strptime(movies_watching[:-1], "%Y-%m-%dT%H:%M:%S")))
			watching_timestamp = int(refdatim.timestamp())
			#watching_timestamp = int(datetime.strptime(movies_watching[:-1], "%Y-%m-%dT%H:%M:%S").timestamp())
		except Exception as e:
			log_utils.error('Exception in getMoviesWatchedActivity: %s' % str(e), log_utils.LOGINFO)

		if not watching_timestamp:
			return 0
		return watching_timestamp
	except: 
		log_utils.error() 
		return 0

def getWatchingActivity(activities=None):
	try:
		if activities: i = activities
		else: i = getSimklAsJson('/sync/activities')
		if not i: return 0
		if type(i) != dict: activities_dict = json.loads(i)
		else: activities_dict = i
		movies_watching = activities_dict["tv_shows"].get("watching")
		try:
			refdatim = datetime.fromtimestamp(time.mktime(time.strptime(movies_watching[:-1], "%Y-%m-%dT%H:%M:%S")))
			watching_timestamp = int(refdatim.timestamp())
			#watching_timestamp = int(datetime.strptime(movies_watching[:-1], "%Y-%m-%dT%H:%M:%S").timestamp())
		except Exception as e:
			log_utils.error('Exception in getWatchingActivity: %s' % str(e), log_utils.LOGINFO)

		if not watching_timestamp:
			return 0
		return watching_timestamp
	except: 
		log_utils.error() 
		return 0

def getHoldActivity(activities=None):
	try:
		if activities: i = activities
		else: i = getSimklAsJson('/sync/activities')
		if not i: return 0
		if type(i) != dict: activities_dict = json.loads(i)
		else: activities_dict = i
		shows_hold = activities_dict["tv_shows"].get("hold")
		shows_watching = activities_dict["tv_shows"].get("watching")
		timestamps = []
		for dt in [shows_hold, shows_watching]:
			if dt:
				try:
					#timestamps.append(datetime.strptime(dt[:-1], "%Y-%m-%dT%H:%M:%S"))
					timestamps.append(datetime.fromtimestamp(time.mktime(time.strptime(dt[:-1], "%Y-%m-%dT%H:%M:%S"))))
				except Exception as e:
					log_utils.error('Exception in getHoldActivity: %s' % str(e), log_utils.LOGINFO)
		newest_timestamp = int(max(timestamps).timestamp()) if timestamps else None
		if not newest_timestamp:
			return 0
		return newest_timestamp
	except: 
		log_utils.error() 
		return 0

def getDroppedActivity(activities=None):
	try:
		if activities: i = activities
		else: i = getSimklAsJson('/sync/activities')
		if not i: return 0
		if type(i) != dict: activities_dict = json.loads(i)
		else: activities_dict = i
		movies_completed = activities_dict["movies"].get("dropped")
		tv_shows_completed = activities_dict["tv_shows"].get("dropped")
		tv_shows_watching = activities_dict["tv_shows"].get("watching")
		timestamps = []
		for dt in [movies_completed, tv_shows_completed]:
			if dt:
				try:
					#timestamps.append(datetime.strptime(dt[:-1], "%Y-%m-%dT%H:%M:%S"))
					timestamps.append(datetime.fromtimestamp(time.mktime(time.strptime(dt[:-1], "%Y-%m-%dT%H:%M:%S"))))
				except Exception as e:
					log_utils.error('Exception in getDroppedActivity: %s' % str(e), log_utils.LOGINFO)
		newest_timestamp = int(max(timestamps).timestamp()) if timestamps else None
		if not newest_timestamp:
			return 0
		return newest_timestamp
	except: 
		return 0

def sync_watchedProgress(activities=None, forced=False):
	try:
		from resources.lib.menus import episodes
		direct = getSetting('simkl.directProgress.scrape') == 'true'
		url = '/sync/all-items/shows/watching?extended=full'
		progressActivity = getProgressActivity(activities)
		local_listCache = cache.timeout(episodes.Episodes().simkl_progress_list, url, direct)
		if forced or (progressActivity > local_listCache) or progressActivity == 0:
			cache.get(episodes.Episodes().simkl_progress_list, 0, url, direct)
			if forced: log_utils.log('Forced - SimKl Progress List Sync Complete', __name__, log_utils.LOGDEBUG)
			else:
				log_utils.log('SimKl Progress List Sync Update...(local db latest "list_cached_at" = %s, simkl api latest "progress_activity" = %s)' % \
									(str(local_listCache), str(progressActivity)), __name__, log_utils.LOGDEBUG)
			control.trigger_widget_refresh()
	except: log_utils.error()

def sync_plantowatch(activities=None, forced=False):
    try:
        def full_sync():
            clr = {'movies_plantowatch': True, 'shows_plantowatch': True, 'shows_watching': False,
                   'shows_hold': False, 'movies_dropped': False, 'shows_dropped': False,
                   'watched': False, 'movies_completed': False, 'shows_completed': False}
            simklsync.delete_tables(clr)
            for category, table in [('movies', 'movies_plantowatch'), ('shows', 'shows_plantowatch')]:
                response = get_request('/sync/all-items/%s/plantowatch' % category)
                if response and isinstance(response, dict):
                    items = response.get(category, [])
                    if items:
                        simklsync.insert_plantowatch(items, table, new_sync=False)

        def delta_sync(db_ts):
            date_from = _ts_to_iso(db_ts)
            for category, table in [('movies', 'movies_plantowatch'), ('shows', 'shows_plantowatch')]:
                response = get_request('/sync/all-items/%s/plantowatch?date_from=%s' % (category, date_from))
                if response and isinstance(response, dict):
                    items = response.get(category, [])
                    if items:
                        simklsync.upsert_items(items, table, 'last_plantowatch_at', 'plantowatch')

        if forced:
            full_sync()
        else:
            db_last = simklsync.last_sync('last_plantowatch_at')
            plantoWatch = getPlantowatchActivity(activities)
            if (plantoWatch - db_last >= 60) or plantoWatch == 0:
                log_utils.log('Simkl (plantowatch) Sync Update...(local db = %s, api = %s)' % (str(db_last), str(plantoWatch)), __name__, log_utils.LOGINFO)
                if db_last == 0:
                    full_sync()
                else:
                    delta_sync(db_last)
    except Exception as e:
        log_utils.error('Error in sync_plantowatch: %s' % str(e))

def sync_completed(activities=None, forced=False):
    try:
        def full_sync():
            clr = {'movies_plantowatch': False, 'shows_plantowatch': False, 'shows_watching': False,
                   'shows_hold': False, 'movies_dropped': False, 'shows_dropped': False,
                   'watched': False, 'movies_completed': True, 'shows_completed': True}
            simklsync.delete_tables(clr)
            for category, table in [('movies', 'movies_completed'), ('shows', 'shows_completed')]:
                response = get_request('/sync/all-items/%s/completed' % category)
                if response and isinstance(response, dict):
                    items = response.get(category, [])
                    if items:
                        simklsync.insert_completed(items, table, new_sync=False)

        def delta_sync(db_ts):
            date_from = _ts_to_iso(db_ts)
            for category, table in [('movies', 'movies_completed'), ('shows', 'shows_completed')]:
                response = get_request('/sync/all-items/%s/completed?date_from=%s' % (category, date_from))
                if response and isinstance(response, dict):
                    items = response.get(category, [])
                    if items:
                        simklsync.upsert_items(items, table, 'last_completed_at', 'completed')

        if forced:
            full_sync()
        else:
            db_last = simklsync.last_sync('last_completed_at')
            historyListActivity = getHistoryListedActivity(activities)
            if (historyListActivity - db_last >= 60) or historyListActivity == 0:
                log_utils.log('Simkl (completed) Sync Update...(local db = %s, api = %s)' % (str(db_last), str(historyListActivity)), __name__, log_utils.LOGINFO)
                if db_last == 0:
                    full_sync()
                else:
                    delta_sync(db_last)
    except Exception as e:
        log_utils.error('Error in sync_completed: %s' % str(e))

def sync_watching(activities=None, forced=False):
    try:
        def full_sync():
            clr = {'movies_plantowatch': False, 'shows_plantowatch': False, 'shows_watching': True,
                   'shows_hold': False, 'movies_dropped': False, 'shows_dropped': False,
                   'watched': False, 'movies_completed': False, 'shows_completed': False}
            simklsync.delete_tables(clr)
            response = get_request('/sync/all-items/shows/watching')
            if response and isinstance(response, dict):
                items = response.get('shows', [])
                if items:
                    simklsync.insert_watching(items, 'shows_watching', new_sync=False)

        def delta_sync(db_ts):
            date_from = _ts_to_iso(db_ts)
            response = get_request('/sync/all-items/shows/watching?date_from=%s' % date_from)
            if response and isinstance(response, dict):
                items = response.get('shows', [])
                if items:
                    simklsync.upsert_items(items, 'shows_watching', 'last_watching_at', 'watching')

        if forced:
            full_sync()
        else:
            db_last = simklsync.last_sync('last_watching_at')
            watching = getWatchingActivity(activities)
            if (watching - db_last >= 60) or watching == 0:
                log_utils.log('Simkl (watching) Sync Update...(local db = %s, api = %s)' % (str(db_last), str(watching)), __name__, log_utils.LOGINFO)
                if db_last == 0:
                    full_sync()
                else:
                    delta_sync(db_last)
    except Exception as e:
        log_utils.error('Error in sync_watching: %s' % str(e))
        
def sync_hold(activities=None, forced=False):
    try:
        def full_sync():
            clr = {'movies_plantowatch': False, 'shows_plantowatch': False, 'shows_watching': False,
                   'shows_hold': True, 'movies_dropped': False, 'shows_dropped': False,
                   'watched': False, 'movies_completed': False, 'shows_completed': False}
            simklsync.delete_tables(clr)
            response = get_request('/sync/all-items/shows/hold')
            if response and isinstance(response, dict):
                items = response.get('shows', [])
                if items:
                    simklsync.insert_hold(items, 'shows_hold', new_sync=False)

        def delta_sync(db_ts):
            date_from = _ts_to_iso(db_ts)
            response = get_request('/sync/all-items/shows/hold?date_from=%s' % date_from)
            if response and isinstance(response, dict):
                items = response.get('shows', [])
                if items:
                    simklsync.upsert_items(items, 'shows_hold', 'last_hold_at', 'hold')

        if forced:
            full_sync()
        else:
            db_last = simklsync.last_sync('last_hold_at')
            hold = getHoldActivity(activities)
            if (hold - db_last >= 60) or hold == 0:
                log_utils.log('Simkl (hold) Sync Update...(local db = %s, api = %s)' % (str(db_last), str(hold)), __name__, log_utils.LOGINFO)
                if db_last == 0:
                    full_sync()
                else:
                    delta_sync(db_last)
    except Exception as e:
        log_utils.error('Error in sync_hold: %s' % str(e))

def _get_all_watchlists_activity(activities=None):
	"""Return the newest watchlist activity timestamp across all watchlist categories."""
	try:
		if activities: i = activities
		else: i = get_request('/sync/activities')
		if not i: return 0
		if type(i) != dict: d = json.loads(i)
		else: d = i
		movies = d.get('movies', {})
		shows = d.get('tv_shows', {})
		timestamps = []
		for ts_str in [
			movies.get('plantowatch'), movies.get('completed'), movies.get('dropped'),
			shows.get('plantowatch'), shows.get('completed'), shows.get('watching'),
			shows.get('hold'), shows.get('dropped')
		]:
			if ts_str:
				try:
					timestamps.append(int(calendar.timegm(time.strptime(ts_str[:-1], "%Y-%m-%dT%H:%M:%S"))))
				except: pass
		return max(timestamps) if timestamps else 0
	except:
		log_utils.error()
		return 0


def sync_all_watchlists(activities=None, forced=False):
	"""Unified watchlist sync. Delta path: 1 request to /sync/all-items/?date_from instead of 8.
	Forced/full path delegates to individual sync functions unchanged."""
	try:
		if forced:
			sync_plantowatch(forced=True)
			sync_completed(forced=True)
			sync_watching(forced=True)
			sync_hold(forced=True)
			sync_dropped(forced=True)
			return

		last_syncs = {
			'last_plantowatch_at': simklsync.last_sync('last_plantowatch_at'),
			'last_completed_at':   simklsync.last_sync('last_completed_at'),
			'last_watching_at':    simklsync.last_sync('last_watching_at'),
			'last_hold_at':        simklsync.last_sync('last_hold_at'),
			'last_dropped_at':     simklsync.last_sync('last_dropped_at'),
		}

		# Any table that has never been synced needs a full sync first
		needs_full = [k for k, v in last_syncs.items() if v == 0]
		if needs_full:
			if 'last_plantowatch_at' in needs_full: sync_plantowatch(forced=True)
			if 'last_completed_at' in needs_full:   sync_completed(forced=True)
			if 'last_watching_at' in needs_full:    sync_watching(forced=True)
			if 'last_hold_at' in needs_full:        sync_hold(forced=True)
			if 'last_dropped_at' in needs_full:     sync_dropped(forced=True)
			# Advance timestamps for empty-category cases so 1970 never persists
			for k in needs_full:
				simklsync.set_sync_time(k)
			return

		# All tables have existing data; check if anything changed
		api_latest = _get_all_watchlists_activity(activities)
		date_from_ts = min(last_syncs.values())
		if api_latest <= date_from_ts:
			return  # Nothing changed since our oldest sync

		date_from = _ts_to_iso(date_from_ts)
		log_utils.log('Simkl watchlists delta sync (1 request from %s)' % date_from, __name__, log_utils.LOGINFO)
		response = get_request('/sync/all-items/?date_from=%s' % date_from)
		if response is None: return

		# Map (media_type, status) → (table, timestamp_col)
		dispatch = {
			('movies', 'plantowatch'): ('movies_plantowatch', 'last_plantowatch_at'),
			('movies', 'completed'):   ('movies_completed',   'last_completed_at'),
			('movies', 'dropped'):     ('movies_dropped',     'last_dropped_at'),
			('shows',  'plantowatch'): ('shows_plantowatch',  'last_plantowatch_at'),
			('shows',  'completed'):   ('shows_completed',    'last_completed_at'),
			('shows',  'watching'):    ('shows_watching',     'last_watching_at'),
			('shows',  'hold'):        ('shows_hold',         'last_hold_at'),
			('shows',  'dropped'):     ('shows_dropped',      'last_dropped_at'),
		}

		from collections import defaultdict
		buckets = defaultdict(list)
		for item in response.get('movies', []):
			status = item.get('status')
			if ('movies', status) in dispatch: buckets[('movies', status)].append(item)
		for item in response.get('shows', []):
			status = item.get('status')
			if ('shows', status) in dispatch: buckets[('shows', status)].append(item)

		for key, items in buckets.items():
			if items:
				table, ts_col = dispatch[key]
				simklsync.upsert_items(items, table, ts_col, key[1])

		# Advance every service timestamp so min() never regresses on next sync
		for ts_col in last_syncs:
			simklsync.set_sync_time(ts_col)

	except Exception as e:
		log_utils.error('Error in sync_all_watchlists: %s' % str(e))


def sync_dropped(activities=None, forced=False):
    try:
        def full_sync():
            clr = {'movies_plantowatch': False, 'shows_plantowatch': False, 'shows_watching': False,
                   'shows_hold': False, 'movies_dropped': True, 'shows_dropped': True,
                   'watched': False, 'movies_completed': False, 'shows_completed': False}
            simklsync.delete_tables(clr)
            for category, table in [('shows', 'shows_dropped'), ('movies', 'movies_dropped')]:
                response = get_request('/sync/all-items/%s/dropped' % category)
                if response and isinstance(response, dict):
                    items = response.get(category, [])
                    if items:
                        simklsync.insert_dropped(items, table, new_sync=False)

        def delta_sync(db_ts):
            date_from = _ts_to_iso(db_ts)
            for category, table in [('shows', 'shows_dropped'), ('movies', 'movies_dropped')]:
                response = get_request('/sync/all-items/%s/dropped?date_from=%s' % (category, date_from))
                if response and isinstance(response, dict):
                    items = response.get(category, [])
                    if items:
                        simklsync.upsert_items(items, table, 'last_dropped_at', 'dropped')

        if forced:
            full_sync()
        else:
            db_last = simklsync.last_sync('last_dropped_at')
            dropped_activity = getDroppedActivity(activities)
            if (dropped_activity - db_last >= 60) or dropped_activity == 0:
                log_utils.log('Simkl (dropped) Sync Update...(local db = %s, api = %s)' % (str(db_last), str(dropped_activity)), __name__, log_utils.LOGINFO)
                if db_last == 0:
                    full_sync()
                else:
                    delta_sync(db_last)
    except Exception as e:
        log_utils.error('Error in sync_dropped: %s' % str(e))


def service_syncSeasons(): # season indicators and counts for watched shows ex. [['1', '2', '3'], {1: {'total': 8, 'watched': 8, 'unwatched': 0}, 2: {'total': 10, 'watched': 10, 'unwatched': 0}}]
	try:
		log_utils.log('Service - Simkl Watched Shows Season Sync...', __name__, log_utils.LOGDEBUG)
		indicators = simklsync.cache_existing(syncTVShows) # use cached data from service cachesyncTVShows() just written fresh
		batch = []
		for indicator in indicators:
			imdb = indicator[0].get('imdb', '') if indicator[0].get('imdb') else ''
			tvdb = str(indicator[0].get('tvdb', '')) if indicator[0].get('tvdb') else ''
			simkl_id = str(indicator[0].get('simkl', '')) if indicator[0].get('simkl') else ''
			batch.append({'imdb': imdb, 'tvdb': tvdb})
			#threads.append(Thread(target=cachesyncSeasons, args=(imdb, tvdb, simkl_id))) # season indicators and counts for an entire show
		#[i.start() for i in threads]
		#[i.join() for i in threads]
		#cachesyncSeasons('tt2152112', None, None)
		batchCacheSyncSeason(batch)
	except: log_utils.error()

def _merge_watched_movies(db_ts):
	"""Fetch only movies changed since db_ts and merge into existing watched cache."""
	try:
		date_from = _ts_to_iso(db_ts)
		delta = post_request('/sync/all-items/movies/completed?date_from=%s' % date_from)
		if not delta: return
		delta_movies = delta.get('movies', [])
		if not delta_movies: return
		delta_imdb = {str(i['movie']['ids'].get('imdb')) for i in delta_movies if i.get('movie', {}).get('ids', {}).get('imdb')}
		existing = simklsync.cache_existing(syncMovies) or []
		merged = [imdb for imdb in existing if imdb not in delta_imdb]
		merged.extend(str(i['movie']['ids']['imdb']) for i in delta_movies if i.get('movie', {}).get('ids', {}).get('imdb'))
		key = simklsync._hash_function(syncMovies, ())
		simklsync.cache_insert(key, repr(merged))
	except: log_utils.error()

def _merge_watched_tvshows(db_ts):
	"""Fetch only shows changed since db_ts and merge into existing watched cache."""
	try:
		date_from = _ts_to_iso(db_ts)
		delta = post_request('/sync/all-items/shows/?extended=full&date_from=%s' % date_from)
		if not delta: return
		valid_statuses = {"watching", "completed", "hold", "dropped", "plantowatch"}
		delta_indicators = [
			(
				{'imdb': s['show']['ids'].get('imdb'), 'tvdb': str(s['show']['ids'].get('tvdb', '')),
				 'tmdb': str(s['show']['ids'].get('tmdb', '')), 'simkl': str(s['show']['ids'].get('simkl', ''))},
				s['total_episodes_count'] - s['not_aired_episodes_count'],
				[(season['number'], ep['number']) for season in s.get('seasons', []) for ep in season.get('episodes', [])]
			)
			for s in delta.get('shows', []) if s.get('status') in valid_statuses
		]
		delta_imdb = {i[0].get('imdb') for i in delta_indicators if i[0].get('imdb')}
		existing = simklsync.cache_existing(syncTVShows) or []
		merged = [i for i in existing if i[0].get('imdb') not in delta_imdb]
		merged.extend(delta_indicators)
		key = simklsync._hash_function(syncTVShows, ())
		simklsync.cache_insert(key, repr(merged))
	except: log_utils.error()

def sync_watched(activities=None, forced=False):
	try:
		if forced:
			cachesyncMovies()
			cachesyncTVShows()
			control.sleep(5000)
			service_syncSeasons() # syncs all watched shows season indicators and counts
			simklsync.insert_syncSeasons_at()
		else:
			moviesWatchedActivity = getMoviesWatchedActivity(activities)
			db_movies_last_watched = timeoutsyncMovies()
			if (moviesWatchedActivity - db_movies_last_watched >= 30) or moviesWatchedActivity == 0:
				log_utils.log('Simkl Watched Movie Sync Update...(local db = %s, api = %s)' % (str(db_movies_last_watched), str(moviesWatchedActivity)), __name__, log_utils.LOGDEBUG)
				if db_movies_last_watched == 0:
					cachesyncMovies()
				else:
					_merge_watched_movies(db_movies_last_watched)
			episodesWatchedActivity = getEpisodesWatchedActivity(activities)
			if episodesWatchedActivity == 0:
				episodesWatchedActivity = 10000000
			db_last_syncTVShows = timeoutsyncTVShows()
			db_last_syncSeasons = simklsync.last_sync('last_syncSeasons_at')
			if any(episodesWatchedActivity > value for value in (db_last_syncTVShows, db_last_syncSeasons)):
				older_ts = min(db_last_syncTVShows, db_last_syncSeasons)
				log_utils.log('Simkl Watched Shows Sync Update...(local db = %s, api = %s)' % (str(older_ts), str(episodesWatchedActivity)), __name__, log_utils.LOGDEBUG)
				if older_ts == 0:
					cachesyncTVShows()
					control.sleep(5000)
					service_syncSeasons()
				else:
					_merge_watched_tvshows(older_ts)
					control.sleep(2000)
					service_syncSeasons()
				simklsync.insert_syncSeasons_at()
	except: log_utils.error()

def timeoutsyncMovies():
	timeout = simklsync.timeout(syncMovies)
	return timeout

def manager(name, imdb=None, tvdb=None, season=None, episode=None, refresh=True, watched=None, unfinished=False, tvshow=None):
	try:
		if season: season = int(season)
		if episode: episode = int(episode)
		media_type = 'Show' if tvdb else 'Movie'
		if watched is not None:
			if watched is True:
				items = [(getLS(33652) % highlightColor, 'unwatch')]
			else:
				items = [(getLS(33651) % highlightColor, 'watch')]
		else:
			items = [(getLS(33651) % highlightColor, 'watch')]
			items += [(getLS(33652) % highlightColor, 'unwatch')]
		if getSetting('scrobble.source') == '2' or getSetting('simkl.markwatched') == 'true':
			if media_type == 'Movie' or episode:
				items += [(getLS(40076) % highlightColor, 'scrobbleReset')]
		if media_type == 'Show':
			items += [(getLS(40570) % highlightColor, '/sync/plantowatch')] #add to show plan to watch
			items += [(getLS(40571) % highlightColor, '/sync/plantowatch/remove')] #remove show from plan to watch
			items += [(getLS(40582) % highlightColor, '/sync/hold')] #add to show plan to watch
			items += [(getLS(40583) % highlightColor, '/sync/hold/remove')] #remove show from plan to watch
			items += [(getLS(40580) % highlightColor, '/sync/dropped')] #add to show plan to watch
			items += [(getLS(40581) % highlightColor, '/sync/dropped/remove')] #remove show from plan to watch
		else: 
			items += [(getLS(40574) % highlightColor, '/sync/plantowatch')] #add movie
			items += [(getLS(40575) % highlightColor, '/sync/plantowatch/remove')] #remove movie
			items += [(getLS(40578) % highlightColor, '/sync/hold')] #add hold
			items += [(getLS(40579) % highlightColor, '/sync/hold/remove')] # remove hold


		control.hide()
		select = control.selectDialog([i[0] for i in items], heading=control.addonInfo('name') + ' - ' + getLS(40576))

		if select == -1: return
		if select >= 0:
			if items[select][1] == 'watch':
				watch(control.infoLabel('Container.ListItem.DBTYPE'), name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=refresh)
			elif items[select][1] == 'unwatch':
				unwatch(control.infoLabel('Container.ListItem.DBTYPE'), name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=refresh)
			elif items[select][1] == 'scrobbleReset':
				scrobbleReset(imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=True, clear_local=getSetting('indicators.alt') == '2')
			else:
				if items[select][1] == '/sync/plantowatch':
					listname = "Plan to Watch"
					add_item = add_to_list(listname="plantowatch", imdb=imdb, tvdb=tvdb, mediatype=media_type)
					if add_item: 
						sync_plantowatch(forced=True)
						simklsync.delete_dropped_items([tvdb], 'shows_hold', 'tvdb')
				if items[select][1] == '/sync/plantowatch/remove':
					listname = "Plan to Watch"
					if media_type == 'Movie': 
						simklsync.delete_plantowatch_items([imdb], 'movies_plantowatch', 'imdb')
					else: 
						simklsync.delete_plantowatch_items([tvdb], 'shows_plantowatch', 'tvdb')
					remove_item = add_to_list(imdb=imdb, tvdb=tvdb, mediatype=media_type, listname="dropped")
					if remove_item: 
						sync_dropped(forced=True)
						sync_hold(forced=True)
				if items[select][1] == '/sync/dropped':
					listname = "Dropped"
					add_item = add_to_list(listname="dropped", imdb=imdb, tvdb=tvdb, mediatype=media_type)
					if add_item: 
						sync_dropped(forced=True)
						simklsync.delete_dropped_items([tvdb], 'shows_hold', 'tvdb')
				if items[select][1] == '/sync/dropped/remove':
					listname = "Dropped"
					if media_type == 'Movie': 
						simklsync.delete_dropped_items([imdb], 'movies_dropped', 'imdb')
					else: 
						simklsync.delete_dropped_items([tvdb], 'shows_dropped', 'tvdb')
					remove_item_from_list(imdb=imdb, tvdb=tvdb, mediatype=media_type, listname=listname)
				if items[select][1] == '/sync/hold':
					listname = "Hold"
					add_item = add_to_list(listname="hold", imdb=imdb, tvdb=tvdb, mediatype=media_type)
					if add_item: 
						sync_hold(forced=True)
						simklsync.delete_plantowatch_items([tvdb], 'shows_plantowatch', 'tvdb')
						sync_plantowatch(forced=True)

				if items[select][1] == '/sync/hold/remove':
					listname = "Hold"
					simklsync.delete_dropped_items([tvdb], 'shows_hold', 'tvdb')
					remove_item = add_to_list(imdb=imdb, tvdb=tvdb, mediatype=media_type, listname="dropped")
					if remove_item: 
						sync_hold(forced=True)
				control.hide()
				message = getLS(40585) if 'remove' in items[select][1] else getLS(40584)
				if items[select][0].startswith('Add'): refresh = False
				control.hide()
				if refresh: control.refresh()
				control.trigger_widget_refresh()
				if getSetting('simkl.general.notifications') == 'true': control.notification(title=name, message=message + ' (%s)' % listname)
	except:
		log_utils.error()
		control.hide()

def remove_item_from_list(**kwargs):
	try:
		link = '/sync/history/remove' #post
		listname = kwargs.get('listname')
		imdb = kwargs.get('imdb')
		tvdb = kwargs.get('tvdb')
		mediatype = kwargs.get('mediatype')
		if mediatype == 'Movie':
			post = {"movies":[{"ids":{"imdb":imdb}}]}
		else:
			post = {"shows":[{"ids":{"imdb":imdb,"tvdb":tvdb}}]}
		response = post_request(link, data=post)
		if response: return True
		else: return None
	except:
		log_utils.error()

def add_to_list(**kwargs):
	try:
		link = '/sync/add-to-list' #post
		listname = kwargs.get('listname')
		imdb = kwargs.get('imdb')
		tvdb = kwargs.get('tvdb')
		mediatype = kwargs.get('mediatype')
		if mediatype == 'Movie':
			post = {"movies":[{"to":listname,"ids":{"imdb":imdb}}]}
		else:
			post = {"shows":[{"to":listname,"ids":{"imdb":imdb,"tvdb":tvdb}}]}
		response = post_request(link, data=post)
		if response:
			result = response.get('added').get(mediatype.lower() +'s')
		if result: return True
		else: return None
	except:
		log_utils.error()

def scrobbleMovie(title, year, imdb, tmdb, watched_percent):
	log_utils.log('Simkl Scrobble Movie Called. title: %s imdb: %s tmdb: %s watched_percent: %s' % (title, imdb, tmdb, watched_percent), level=log_utils.LOGDEBUG)
	try:
		data = {'progress': watched_percent, 'movie': {'title': title, 'year': int(year) if year else 0, 'ids': {'imdb': imdb, 'tmdb': int(tmdb) if tmdb else None}}}
		success = post_request('/scrobble/pause', data)
		if success:
			log_utils.log('Simkl Scrobble Movie Success: imdb: %s' % imdb, level=log_utils.LOGDEBUG)
			if getSetting('scrobble.notify') == 'true': control.notification(message=40656)
			control.sleep(1000)
			sync_playbackProgress(forced=True)
			control.trigger_widget_refresh()
		else: control.notification(message=32130)
	except: log_utils.error()

def scrobbleEpisode(tvshowtitle, year, imdb, tmdb, tvdb, season, episode, watched_percent):
	log_utils.log('Simkl Scrobble Episode Called. tvshowtitle: %s imdb: %s season: %s episode: %s watched_percent: %s' % (tvshowtitle, imdb, season, episode, watched_percent), level=log_utils.LOGDEBUG)
	try:
		season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
		data = {'progress': watched_percent, 'show': {'title': tvshowtitle, 'year': int(year) if year else 0, 'ids': {'imdb': imdb}}, 'episode': {'season': season, 'number': episode}}
		success = post_request('/scrobble/pause', data)
		if success:
			log_utils.log('Simkl Scrobble Episode Success: imdb: %s S%02dE%02d' % (imdb, season, episode), level=log_utils.LOGDEBUG)
			if getSetting('scrobble.notify') == 'true': control.notification(message=40656)
			control.sleep(1000)
			sync_playbackProgress(forced=True)
			control.trigger_widget_refresh()
		else: control.notification(message=32130)
	except: log_utils.error()

def scrobbleStart(media_type, title='', tvshowtitle='', year='0', imdb='', tmdb='', tvdb='', season='', episode='', watched_percent=0):
	log_utils.log('Simkl Scrobble Start Called. media_type: %s imdb: %s' % (media_type, imdb), level=log_utils.LOGDEBUG)
	try:
		if media_type == 'movie':
			data = {'progress': watched_percent, 'movie': {'title': title, 'year': int(year) if year else 0, 'ids': {'imdb': imdb, 'tmdb': int(tmdb) if tmdb else None}}}
		else:
			data = {'progress': watched_percent, 'show': {'title': tvshowtitle, 'year': int(year) if year else 0, 'ids': {'imdb': imdb}}, 'episode': {'season': int('%01d' % int(season)) if season else 0, 'number': int('%01d' % int(episode)) if episode else 0}}
		success = post_request('/scrobble/start', data)
		if success:
			log_utils.log('Simkl Scrobble Start Success: imdb: %s' % imdb, level=log_utils.LOGDEBUG)
		else:
			log_utils.log('Simkl Scrobble Start Failed: imdb: %s' % imdb, level=log_utils.LOGDEBUG)
	except: log_utils.error()

def scrobbleReset(imdb, tmdb='', tvdb='', season=None, episode=None, refresh=False, clear_local=True):
	if not getSimKLCredentialsInfo(): return
	if not control.player.isPlaying(): control.busy()
	try:
		resume_info = simklsync.fetch_bookmarks(imdb, tmdb, tvdb, season, episode, ret_type='resume_info')
		if resume_info == '0':
			control.hide()
			return
		label_string, resume_id = resume_info[0], resume_info[1]
		if episode: label_string = label_string + ' - ' + 'S%02dE%02d' % (int(season), int(episode))
		_version = control.addon('plugin.video.umbrella').getAddonInfo('version')
		delete_headers = {
			'Authorization': 'Bearer %s' % getSetting('simkltoken'),
			'simkl-api-key': simklclientid,
			'User-Agent': 'Umbrella/%s' % _version
		}
		url = '%s/sync/playback/%s?client_id=%s' % (BASE_URL, resume_id, simklclientid)
		success = session.delete(url, headers=delete_headers, timeout=20).status_code == 204
		control.hide()
		if success:
			if clear_local: simklsync.delete_bookmark(resume_id)
			if refresh: control.refresh()
			if getSetting('scrobble.notify') == 'true':
				control.notification(title=32315, message='Successfully Removed Simkl playback progress: [COLOR %s]%s[/COLOR]' % (highlightColor, label_string))
			log_utils.log('Successfully Removed Simkl Playback Progress: %s with resume_id=%s' % (label_string, str(resume_id)), __name__, level=log_utils.LOGDEBUG)
		else:
			log_utils.log('Failed to Remove Simkl Playback Progress: %s with resume_id=%s' % (label_string, str(resume_id)), __name__, level=log_utils.LOGDEBUG)
	except: log_utils.error()

def sync_playbackProgress(activities=None, forced=False):
	try:
		link = '/sync/playback'
		if forced:
			items = get_request(link)
			if items: simklsync.insert_bookmarks(items)
		else:
			db_last_paused = simklsync.last_sync('last_paused_at')
			sync_interval = int(getSetting('simkl.service.syncInterval')) if getSetting('simkl.service.syncInterval') else 30
			if db_last_paused == 0 or (int(time.time()) - db_last_paused) >= (60 * sync_interval):
				items = get_request(link)
				if items: simklsync.insert_bookmarks(items)
	except: log_utils.error()

def force_simklSync(silent=False):
	if not silent:
		if not control.yesnoDialog(getLS(32056), '', ''): return
		control.busy()

	# wipe all tables and start fresh
	clr_simkl = {'movies_plantowatch': True, 'shows_plantowatch': True, 'shows_watching': True, 'shows_hold': True, 'movies_dropped': True, 'shows_dropped': True, 'watched': True, 'movies_completed': True, 'shows_completed': True}
	simklsync.delete_tables(clr_simkl)

	sync_plantowatch(forced=True)
	sync_completed(forced=True)
	sync_watched(forced=True) #simkl counts
	sync_watchedProgress(forced=True) # simkl progress sync
	sync_watching(forced=True)
	sync_hold(forced=True)
	sync_dropped(forced=True)
	if not silent: 
		control.hide()
		control.notification(message='Forced Simkl Sync Complete')