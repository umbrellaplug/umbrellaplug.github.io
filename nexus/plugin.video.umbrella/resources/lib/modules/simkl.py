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
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
from resources.lib.modules import cleandate
import json
from itertools import islice
import time

getLS = control.lang
getSetting = control.setting
BASE_URL = 'https://api.simkl.com'
oauth_base_url = 'https://api.simkl.com/oauth/pin'
simkl_icon = control.joinPath(control.artPath(), 'simkl.png')
simklclientid = 'cecec23773dff71d940876860a316a4b74666c4c31ad719fe0af8bb3064a34ab'
session = requests.Session()
retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
session.mount('https://api.simkl.com', HTTPAdapter(max_retries=retries, pool_maxsize=100))
sim_qr = control.joinPath(control.artPath(), 'simklqr.png')
highlightColor = control.setting('highlight.color')
headers = {}

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
						control.openSettings('9.0', 'plugin.video.umbrella')
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
					control.openSettings('9.0', 'plugin.video.umbrella')
				force_simklSync(silent=True)
				return True, None
			force_simklSync(silent=True)
			control.homeWindow.setProperty('umbrella.updateSettings', 'false')
			control.setSetting('indicators.alt', '2')
			control.homeWindow.setProperty('umbrella.updateSettings', 'true')
			control.setSetting('indicators', 'Simkl')
			if fromSettings == 1:
				control.openSettings('9.0', 'plugin.video.umbrella')
			return True, None
		except:
			log_utils.error('Simkl Authorization Failed : ')
			if fromSettings == 1:
				control.openSettings('9.0', 'plugin.video.umbrella')
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
				control.openSettings('9.0', 'plugin.video.umbrella')
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

def get_request(url):
	try:
		if not url.startswith(BASE_URL): url = urljoin(BASE_URL, url)
		if '?' not in url:
			url += '?client_id=%s' % simklclientid
		else:
			url += '&client_id=%s' % simklclientid
		headers['Authorization'] = 'Bearer %s' % getSetting('simkltoken')
		headers['simkl-api-key'] = simklclientid
		headers['User-Agent'] = 'Umbrella/%s' % control.addon('plugin.video.umbrella').getAddonInfo('version')
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
		if post or 'sync/activities' in url: r = simkl.post_request(url, data=post)
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
		if success: cachesyncTV(imdb, tvdb)
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

def getSimKLCredentialsInfo():
	token = getSetting('simkltoken')
	if (token == ''): return False
	return True

def getSimKLIndicatorsInfo():
	indicators = getSetting('indicators.alt')
	indicators = True if indicators == '2' else False
	return indicators

def post_request(url, data=None):
	if type(data) == dict or type(data) == list: data = json.dumps(data)
	if not url.startswith(BASE_URL): url = urljoin(BASE_URL, url)
	if '?' not in url:
		url += '?client_id=%s' % simklclientid
	else:
		url += '&client_id=%s' % simklclientid
	headers['Authorization'] = 'Bearer %s' % getSetting('simkltoken')
	headers['simkl-api-key'] = simklclientid
	headers['User-Agent'] = 'Umbrella/%s' % control.addon('plugin.video.umbrella').getAddonInfo('version')
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
		result = result['added']['movies'] != 0
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
		if result['not_found']['shows'] == 0 and tvdb: # fail, trying again with tvdb as fallback
			control.sleep(1000) # POST 1 call per sec rate-limit
			result = simkl.post_request('/sync/history', {"shows": [{"ids": {"tvdb": tvdb}}]})
			if not result: return False
		if len(result.get('added').get('shows', 0)) != 0: 
			simklsync.remove_hold_item(imdb)
			simklsync.remove_plan_to_watch(imdb, 'shows_plantowatch')
		return len(result.get('added').get('shows', 0)) != 0
	except: log_utils.error()

def markTVShowAsNotWatched(imdb, tvdb):
	try:
		from resources.lib.modules import simkl
		result = simkl.post_request('/sync/history/remove', {"shows": [{"ids": {"imdb": imdb, "tvdb": tvdb}}]})
		if not result: return False
		if result['not_found']['shows'] == 0 and tvdb: # fail, trying again with tvdb as fallback
			control.sleep(1000) # POST 1 call per sec rate-limit
			result = simkl.post_request('/sync/history/remove', {"shows": [{"ids": {"tvdb": tvdb}}]})
			if not result: return False
		return result['deleted']['shows'] != 0
	except: log_utils.error()

def markSeasonAsWatched(imdb, tvdb, season):
	try:
		from resources.lib.modules import simkl
		season = int('%01d' % int(season))
		result = simkl.post_request('/sync/history', {"shows": [{"seasons": [{"number": season}], "ids": {"imdb": imdb, "tvdb": tvdb}}]})
		if not result: return False
		if  result['not_found']['shows'] == 0 and tvdb: # # fail, trying again with tvdb as fallback
			control.sleep(1000) # POST 1 call per sec rate-limit
			result = simkl.post_request('/sync/history', {"shows": [{"seasons": [{"number": season}], "ids": {"tvdb": tvdb}}]})
			if not result: return False
		if result['not_found']['shows'] == []:
			simklsync.remove_hold_item(imdb)
			simklsync.remove_plan_to_watch(imdb, 'shows_plantowatch')
		return result['added']['episodes'] != 0
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

def markEpisodeAsWatched(imdb, tvdb, season, episode):
	try:
		season, episode = int('%01d' % int(season)), int('%01d' % int(episode)) #same
		from resources.lib.modules import simkl
		result = simkl.post_request('/sync/history', {"shows": [{"seasons": [{"episodes": [{"number": episode}], "number": season}], "ids": {"imdb": imdb, "tvdb": tvdb}}]})
		if not result: result = False
		if (result['not_found']['episodes'] == 0 or result['not_found']['shows'] == 0) and tvdb:
			control.sleep(1000)
			result = simkl.post_request('/sync/history', {"shows": [{"seasons": [{"episodes": [{"number": episode}], "number": season}], "ids": {"tvdb": tvdb}}]})
			if not result: result = False
			result = result['added']['episodes'] !=0
		else:
			result = result['added']['episodes'] !=0
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
		if (result['not_found']['episodes'] == 0 or result['not_found']['shows'] == 0) and tvdb:
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

    def process_chunk(chunk):
        #Handles API request and season syncing for a batch.
        formatted_data = [show for show in chunk]  # Format each batch
        results = post_request(f'/sync/watched?extended={extended_param}', data=formatted_data)
        if not results:
            return
        with ThreadPoolExecutor() as executor:
            for show in chunk:
                imdb = show.get('imdb')
                tvdb = show.get('tvdb')
                simkl_id = show.get('simkl')
                executor.submit(cachesyncSeasons, imdb, tvdb, simkl_id, 0, results)

    with ThreadPoolExecutor() as executor:
        for chunk in chunked_iterator(data, 100):  # Process 100 items at a time
            executor.submit(process_chunk, chunk)

def cachesyncSeasons(imdb, tvdb, simkl_id=None, timeout=0, data=None):
	try:
		imdb = imdb or ''
		tvdb = tvdb or ''
		indicators = simklsync.get(syncSeasons, timeout, imdb, tvdb, simkl_id, data) # named var and data not included in function md5_hash
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
			if show.get('imdb') != imdb:
				continue
			seasons = show.get('seasons', [])
        
			indicators = [(season['number'], [ep['watched'] for ep in season['episodes']]) for season in seasons]
			indicators = ['%01d' % int(season[0]) for season in indicators if all(season[1])]
			indicators_and_counts.append(indicators)

			counts = {
				season['number']: {
					'total': season['episodes_aired'],
					'watched': season['episodes_watched'],
					'unwatched': season['episodes_aired'] - season['episodes_watched']
				}
				for season in seasons
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
		else: i = post_request('/sync/activities')
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
	except: log_utils.error()

def sync_plantowatch(activities=None, forced=False):
    
    try:
        link = '/sync/all-items/%s/plantowatch'
        
        def fetch_and_insert(category, table_name):
            response = get_request(link % category)
            if response and isinstance(response, dict):  # Ensure response is not None and is a dictionary
                items = response.get(category, [])
                if items:
                    simklsync.insert_plantowatch(items, table_name)

        if forced:
            fetch_and_insert('movies', 'movies_plantowatch')
            fetch_and_insert('shows', 'shows_plantowatch')
        else:
            db_last_watchList = simklsync.last_sync('last_plantowatch_at')
            plantoWatch = getPlantowatchActivity(activities)
            
            if (plantoWatch - db_last_watchList >= 60) or plantoWatch == 0:  # Ensure at least 1-minute difference
                log_utils.log(
                    'Simkl (plantowatch) Sync Update...(local db latest "plantowatch_at" = %s, simkl api latest "last_plantowatch_at" = %s)' %
                    (str(db_last_watchList), str(plantoWatch)),
                    __name__, log_utils.LOGINFO
                )
                
                clr_simklsync = {
                    'movies_plantowatch': True,
                    'shows_plantowatch': True,
                    'shows_watching': False,
                    'shows_hold': False,
                    'movies_dropped': False,
                    'shows_dropped': False,
                    'watched': False,
                    'movies_completed': False,
                    'shows_completed': False
                }
                simklsync.delete_tables(clr_simklsync)
                
                fetch_and_insert('movies', 'movies_plantowatch')
                fetch_and_insert('shows', 'shows_plantowatch')

    except Exception as e:
        log_utils.error('Error in sync_plantowatch: %s' % str(e), log_utils.LOGINFO)

def sync_completed(activities=None, forced=False):
    try:
        link = '/sync/all-items/%s/completed'

        def fetch_and_insert(category, table_name):
            response = get_request(link % category)
            if response and isinstance(response, dict):  # Ensure response is not None and is a dictionary
                items = response.get(category, [])
                if items:
                    simklsync.insert_completed(items, table_name)

        if forced:
            fetch_and_insert('movies', 'movies_completed')
            fetch_and_insert('shows', 'shows_completed')
        else:
            db_last_historyList = simklsync.last_sync('last_completed_at')
            historyListActivity = getHistoryListedActivity(activities)

            if (historyListActivity - db_last_historyList >= 60) or historyListActivity == 0:  # Ensure at least 1-minute difference
                log_utils.log(
                    'Simkl Completed Sync Update...(local db latest "last_completed_at" = %s, simkl api latest "last_completed_at" = %s)' %
                    (str(db_last_historyList), str(historyListActivity)),
                    __name__, log_utils.LOGINFO
                )

                clr_simklsync = {
                    'movies_plantowatch': False,
                    'shows_plantowatch': False,
                    'shows_watching': False,
                    'shows_hold': False,
                    'movies_dropped': False,
                    'shows_dropped': False,
                    'watched': False,
                    'movies_completed': True,
                    'shows_completed': True
                }
                simklsync.delete_tables(clr_simklsync)

                fetch_and_insert('movies', 'movies_completed')
                fetch_and_insert('shows', 'shows_completed')

    except Exception as e:
        log_utils.error('Error in sync_completed: %s' % str(e), log_utils.LOGINFO)

def sync_watching(activities=None, forced=False):
    try:
        link = '/sync/all-items/%s/watching'
        
        def fetch_and_insert(category, table_name):
            response = get_request(link % category)
            if response and isinstance(response, dict):  # Ensure response is not None and is a dictionary
                items = response.get(category, [])
                if items:
                    simklsync.insert_watching(items, table_name)

        if forced:
            fetch_and_insert('shows', 'shows_watching')
        else:
            db_last_watchList = simklsync.last_sync('last_watching_at')
            watching = getWatchingActivity(activities)
            
            if (watching - db_last_watchList >= 60) or watching == 0:  # Ensure at least 1-minute difference
                log_utils.log(
                    'Simkl (watching) Sync Update...(local db latest "watching_at" = %s, simkl api latest "last_watching_at" = %s)' %
                    (str(db_last_watchList), str(watching)),
                    __name__, log_utils.LOGINFO
                )
                
                clr_simklsync = {
                    'movies_plantowatch': False,
                    'shows_plantowatch': False,
                    'shows_watching': True,
                    'shows_hold': False,
                    'movies_dropped': False,
                    'shows_dropped': False,
                    'watched': False,
                    'movies_completed': False,
                    'shows_completed': False
                }
                simklsync.delete_tables(clr_simklsync)
                
                fetch_and_insert('shows', 'shows_watching')

    except Exception as e:
        log_utils.error('Error in sync_watching: %s' % str(e), log_utils.LOGINFO)
        
def sync_hold(activities=None, forced=False):
    try:
        link = '/sync/all-items/%s/hold'
        
        def fetch_and_insert(category, table_name):
            response = get_request(link % category)
            if response and isinstance(response, dict):  # Ensure response is not None and is a dictionary
                items = response.get(category, [])
                if items:
                    simklsync.insert_hold(items, table_name)

        if forced:
            fetch_and_insert('shows', 'shows_hold')
        else:
            db_last_watchList = simklsync.last_sync('last_hold_at')
            hold = getHoldActivity(activities)
            
            if (hold - db_last_watchList >= 60) or hold == 0:  # Ensure at least 1-minute difference
                log_utils.log(
                    'Simkl (hold) Sync Update...(local db latest "hold_at" = %s, simkl api latest "last_hold_at" = %s)' %
                    (str(db_last_watchList), str(hold)),
                    __name__, log_utils.LOGINFO
                )
                
                clr_simklsync = {
                    'movies_plantowatch': False,
                    'shows_plantowatch': False,
                    'shows_watching': False,
                    'shows_hold': True,
                    'movies_dropped': False,
                    'shows_dropped': False,
                    'watched': False,
                    'movies_completed': False,
                    'shows_completed': False
                }
                simklsync.delete_tables(clr_simklsync)
                
                fetch_and_insert('shows', 'shows_hold')

    except Exception as e:
        log_utils.error('Error in sync_hold: %s' % str(e), log_utils.LOGINFO)

def sync_dropped(activities=None, forced=False):
    try:
        link = '/sync/all-items/%s/dropped'
        
        def fetch_and_insert(category, table_name):
            response = get_request(link % category)
            if response and isinstance(response, dict):  # Ensure response is not None and is a dictionary
                items = response.get(category, [])
                if items:
                    simklsync.insert_dropped(items, table_name)

        if forced:
            fetch_and_insert('shows', 'shows_dropped')
            fetch_and_insert('movies', 'movies_dropped')
        else:
            db_last_dropped = simklsync.last_sync('last_dropped_at')
            hold = getDroppedActivity(activities)
            
            if (hold - db_last_dropped >= 60) or hold == 0:  # Ensure at least 1-minute difference
                log_utils.log(
                    'Simkl (dropped) Sync Update...(local db latest "dropped_at" = %s, simkl api latest "last_dropped_at" = %s)' %
                    (str(db_last_dropped), str(hold)),
                    __name__, log_utils.LOGINFO
                )
                
                clr_simklsync = {
                    'movies_plantowatch': False,
                    'shows_plantowatch': False,
                    'shows_watching': False,
                    'shows_hold': False,
                    'movies_dropped': True,
                    'shows_dropped': True,
                    'watched': False,
                    'movies_completed': False,
                    'shows_completed': False
                }
                simklsync.delete_tables(clr_simklsync)
                
                fetch_and_insert('shows', 'shows_dropped')
                fetch_and_insert('movies', 'movies_dropped')

    except Exception as e:
        log_utils.error('Error in sync_hold: %s' % str(e), log_utils.LOGINFO)


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
			if (moviesWatchedActivity - db_movies_last_watched >= 30) or moviesWatchedActivity == 0: # do not sync unless 30secs more to allow for variation between simkl post and local db update.
				log_utils.log('Simkl Watched Movie Sync Update...(local db latest "watched_at" = %s, simkl api latest "watched_at" = %s)' % \
								(str(db_movies_last_watched), str(moviesWatchedActivity)), __name__, log_utils.LOGDEBUG)
				cachesyncMovies()
			episodesWatchedActivity = getEpisodesWatchedActivity(activities)
			if episodesWatchedActivity == 0:
				episodesWatchedActivity = 10000000
			db_last_syncTVShows = timeoutsyncTVShows()
			db_last_syncSeasons = simklsync.last_sync('last_syncSeasons_at')
			if any(episodesWatchedActivity > value for value in (db_last_syncTVShows, db_last_syncSeasons)):
				log_utils.log('Simkl Watched Shows Sync Update...(local db latest "watched_at" = %s, simkl api latest "watched_at" = %s)' % \
								(str(min(db_last_syncTVShows, db_last_syncSeasons)), str(episodesWatchedActivity)), __name__, log_utils.LOGDEBUG)
				cachesyncTVShows()
				control.sleep(5000)
				service_syncSeasons() # syncs all watched shows season indicators and counts
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