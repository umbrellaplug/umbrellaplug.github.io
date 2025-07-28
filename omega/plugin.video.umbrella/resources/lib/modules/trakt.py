# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from datetime import datetime
from json import dumps as jsdumps, loads as jsloads
import re
import requests
from requests.adapters import HTTPAdapter
from threading import Thread
from urllib3.util.retry import Retry
from urllib.parse import urljoin
from resources.lib.database import cache, traktsync
from resources.lib.modules import cleandate
from resources.lib.modules import control
from resources.lib.modules import log_utils
import time

getLS = control.lang
getSetting = control.setting
setSetting = control.setSetting
BASE_URL = 'https://api.trakt.tv'
headers = {'Content-Type': 'application/json', 'trakt-api-key': '', 'trakt-api-version': '2'}
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
session = requests.Session()
retries = Retry(total=4, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 524, 530])
session.mount('https://api.trakt.tv', HTTPAdapter(max_retries=retries, pool_maxsize=100))
highlight_color = getSetting('highlight.color')
server_notification = getSetting('trakt.server.notifications') == 'true'
service_syncInterval = int(getSetting('background.service.syncInterval')) if getSetting('background.service.syncInterval') else 15
trakt_icon = control.joinPath(control.artPath(), 'trakt.png')
#trakt_qr = control.joinPath(control.artPath(), 'traktqr.png')
trakt_token = getSetting('trakt.user.token')

def getTrakt(url, post=None, extended=False, silent=False, reauth_attempts=0):
	try:
		if not url.startswith(BASE_URL): url = urljoin(BASE_URL, url)
		if headers['trakt-api-key'] == '': headers['trakt-api-key']=traktClientID()
		if post: post = jsdumps(post)
		if getTraktCredentialsInfo(): 
			current_token = getSetting('trakt.user.token')
			headers['Authorization'] = 'Bearer %s' % current_token
		if post:
			response = session.post(url, data=post, headers=headers, timeout=20)
		else:
			response = session.get(url, headers=headers, timeout=20)
		status_code = str(response.status_code)

		error_handler(url, response, status_code, silent=silent)
		if response and status_code in ('200', '201'):
			if extended: return response, response.headers
			else: return response
		elif status_code == '401': # Re-Auth token
			if response.headers.get('x-private-user') == 'true':
				#log_utils.log('URL:%s Has a Private User Header:Ignoring' % url, level=log_utils.LOGWARNING)
				return None
			# Prevent infinite re-auth loops
			if reauth_attempts >= 2:
				log_utils.log('TRAKT: Too many re-auth attempts, stopping to prevent infinite loop', level=log_utils.LOGWARNING)
				return None
			log_utils.log('TRAKT: %s Status Code Returned on call to url: %s. Token Used: %s (attempt %d)' % (status_code, url, current_token, reauth_attempts + 1), level=log_utils.LOGINFO)
			success = re_auth(headers)
			if success: return getTrakt(url, extended=extended, silent=silent, reauth_attempts=reauth_attempts + 1)
		elif status_code == '429':
			if 'Retry-After' in response.headers: # API REQUESTS ARE BEING THROTTLED, INTRODUCE WAIT TIME (1000 get requests every 5 minutes, 1 post/put/delte every per second)
				throttleTime = response.headers['Retry-After']
				if not silent and server_notification and not control.condVisibility('Player.HasVideo'):
					control.notification(title=32315, message='Trakt Throttling Applied, Sleeping for %s seconds' % throttleTime) # message lang code 33674
				control.sleep((int(throttleTime) + 1) * 1000)
				return getTrakt(url, extended=extended, silent=silent, reauth_attempts=reauth_attempts)
		else: return None
	except: log_utils.error('getTrakt Error: ')
	return None

def error_handler(url, response, status_code, silent=False):
	if status_code.startswith('5') or (response and isinstance(response, str) and '<html' in response) or not str(response): # covers Maintenance html responses
		log_utils.log('Temporary Trakt Server Problem: %s:%s' % (status_code, response), level=log_utils.LOGINFO)
		if (not silent) and server_notification: control.notification(title=32315, message=33676)
	elif status_code == '423':
		response_text = response.text if not isinstance(response, str) and hasattr(response, 'text') else str(response)
		log_utils.log('Locked User Account - Contact Trakt Support: %s' % response_text, level=log_utils.LOGWARNING)
		if (not silent) and server_notification: control.notification(title=32315, message=33675)
	elif status_code == '404':
		response_text = response.text if not isinstance(response, str) and hasattr(response, 'text') else str(response)
		log_utils.log('getTrakt() (404:NOT FOUND): URL=(%s): %s' % (url, response_text), level=log_utils.LOGWARNING)

def getTraktAsJson(url, post=None, silent=False):
	try:
		res_headers = {}
		r = getTrakt(url=url, post=post, extended=True, silent=silent)
		if not r: return None
		if isinstance(r, tuple) and len(r) == 2: r, res_headers = r[0], r[1]
		if not r: return None
		r = r.json()
		if 'X-Sort-By' in res_headers and 'X-Sort-How' in res_headers:
			r = sort_list(res_headers['X-Sort-By'], res_headers['X-Sort-How'], r)
		return r
	except Exception as e: 
		log_utils.log('TRAKT: Error in getTraktAsJson: %s' % str(e), level=log_utils.LOGWARNING)
		return None

def re_auth(headers):
	try:
		oauth = urljoin(BASE_URL, '/oauth/token')
		opost = {'client_id': traktClientID(), 'client_secret': traktClientSecret(), 'redirect_uri': REDIRECT_URI, 'grant_type': 'refresh_token', 'refresh_token': getSetting('trakt.refreshtoken')}
		log_utils.log('TRAKT: Re-Authenticating Refresh Token: %s Trakt Token: %s' % (getSetting('trakt.refreshtoken'),getSetting('trakt.user.token')), level=log_utils.LOGINFO)
		response = session.post(url=oauth, data=jsdumps(opost), headers=headers, timeout=20)
		status_code = str(response.status_code)

		error_handler(oauth, response, status_code)
		if status_code not in ('401', '403', '405'):
			try: 
				response_json = response.json()
			except Exception as e:
				log_utils.log('TRAKT: JSON decode error in re_auth: %s - Response text: %s' % (str(e), response.text), level=log_utils.LOGWARNING)
				return False
			
			if 'error' in response_json and response_json['error'] == 'invalid_grant':
				log_utils.log('Please Re-Authorize your Trakt Account: %s : %s' % (status_code, str(response_json)), __name__, level=log_utils.LOGWARNING)
				control.notification(title=32315, message=33677)
				# Clear invalid tokens to force re-authorization
				control.homeWindow.setProperty('umbrella.updateSettings', 'false')
				setSetting('trakt.isauthed', 'false')
				setSetting('trakt.user.token', '')
				setSetting('trakt.refreshtoken', '')
				setSetting('trakt.token.expires', '')
				control.homeWindow.setProperty('umbrella.updateSettings', 'true')
				return False
			
			token, refresh = response_json['access_token'], response_json['refresh_token']
			log_utils.log('TRAKT: Response Token: %s Response Refresh Token: %s ' % (token, refresh), level=log_utils.LOGINFO)
			# Use Trakt's provided expiration time instead of hardcoded 24 hours
			expires_from_trakt = response_json['expires_in']
			expires = str(time.time() + expires_from_trakt)
			log_utils.log('TRAKT: Umbrella Trakt Expire: %s Trakt Expire: %s' % (str(expires),str(expires_from_trakt)), level=log_utils.LOGINFO)
			control.homeWindow.setProperty('umbrella.updateSettings', 'false')
			setSetting('trakt.isauthed', 'true')
			setSetting('trakt.user.token', token)
			setSetting('trakt.refreshtoken', refresh)
			control.homeWindow.setProperty('umbrella.updateSettings', 'true')
			setSetting('trakt.token.expires', expires)
			#control.addon('script.module.myaccounts').setSetting('trakt.user.token', token)
			#control.addon('script.module.myaccounts').setSetting('trakt.refreshtoken', refresh)
			#control.addon('script.module.myaccounts').setSetting('trakt.token.expires', expires)
			log_utils.log('Trakt Token Successfully Re-Authorized: expires on %s' % str(datetime.fromtimestamp(float(expires))), level=log_utils.LOGDEBUG)
			return True
		else:
			log_utils.log('Error while Re-Authorizing Trakt Token: %s : %s' % (status_code, response.text), level=log_utils.LOGWARNING)
			# If we get 401/403/405 on refresh, the refresh token is invalid
			if status_code in ('401', '403'):
				log_utils.log('TRAKT: Refresh token appears to be invalid, clearing tokens', level=log_utils.LOGWARNING)
				control.homeWindow.setProperty('umbrella.updateSettings', 'false')
				setSetting('trakt.isauthed', 'false')
				setSetting('trakt.user.token', '')
				setSetting('trakt.refreshtoken', '')
				setSetting('trakt.token.expires', '')
				control.homeWindow.setProperty('umbrella.updateSettings', 'true')
			return False
	except Exception as e: 
		log_utils.log('TRAKT: Exception in re_auth: %s' % str(e), level=log_utils.LOGWARNING)
		return False

def traktAuth(fromSettings=0):
	try:
		traktDeviceCode = getTraktDeviceCode()
		deviceCode = getTraktDeviceToken(traktDeviceCode)
		if deviceCode:
			deviceCode = deviceCode.json()
			# Use Trakt's provided expiration time instead of hardcoded 24 hours
			expires_from_trakt = deviceCode.get('expires_in', 86400)  # fallback to 24 hours if not provided
			expires_at = time.time() + expires_from_trakt
			control.homeWindow.setProperty('umbrella.updateSettings', 'false')
			control.setSetting('trakt.token.expires', str(expires_at))
			control.setSetting('trakt.user.token', deviceCode["access_token"])
			control.setSetting('trakt.scrobble', 'true')
			control.setSetting('resume.source', '1')
			control.setSetting('trakt.isauthed', 'true')
			control.homeWindow.setProperty('umbrella.updateSettings', 'true')
			control.setSetting('trakt.refreshtoken', deviceCode["refresh_token"])
			control.sleep(1000)
			try:
				headers['Authorization'] = 'Bearer %s' % trakt_token
				user = getTrakt('users/me', post=None)
				username = user.json()
				control.setSetting('trakt.user.name', str(username['username']))
			except: pass
			control.notification(message=40107, icon=trakt_icon)
			if fromSettings == 1:
				control.openSettings('8.0', 'plugin.video.umbrella')
			if not control.yesnoDialog('Do you want to set Trakt as your service for your watched and unwatched indicators?','','','Indicators', 'No', 'Yes'): return True
			control.homeWindow.setProperty('umbrella.updateSettings', 'false')
			control.setSetting('indicators.alt', '1')
			control.homeWindow.setProperty('umbrella.updateSettings', 'true')
			control.setSetting('indicators', 'Trakt')
			return True
		if fromSettings == 1:
				control.openSettings('8.0', 'plugin.video.umbrella')
		control.notification(message=40108, icon=trakt_icon)
		return False
	except:
		log_utils.error()

def traktRevoke(fromSettings=0):
		data = {"token": control.setting('trakt.user.token')}
		try: 
			getTrakt('oauth/revoke', post=data)
		except: pass
		control.homeWindow.setProperty('umbrella.updateSettings', 'false')
		control.setSetting('trakt.user.name', '')
		control.setSetting('trakt.token.expires', '')
		control.setSetting('trakt.user.token', '')
		control.setSetting('trakt.scrobble', 'false')
		control.setSetting('resume.source', '0')
		control.setSetting('trakt.isauthed','')
		control.homeWindow.setProperty('umbrella.updateSettings', 'true')
		control.setSetting('trakt.refreshtoken', '')
		try:	
			from resources.lib.database import traktsync
			clr_traktSync = {'bookmarks': True, 'hiddenProgress': True, 'liked_lists': True, 'movies_collection': True, 'movies_watchlist': True, 'popular_lists': True,
					'public_lists': True, 'shows_collection': True, 'shows_watchlist': True, 'trending_lists': True, 'user_lists': True, 'watched': True}
			cleared = traktsync.delete_tables(clr_traktSync)
			if cleared:
				log_utils.log('Trakt tables cleared after revoke.', level=log_utils.LOGINFO)
			if getSetting('indicators.alt') == '1':
				control.setSetting('indicators.alt', '0')
				control.setSetting('indicators', 'Local')
			if fromSettings == 1:
				control.openSettings('8.0', 'plugin.video.umbrella')
				control.dialog.ok(control.lang(32315), control.lang(40109))
		except:
			log_utils.error()


def getTraktDeviceCode():
	try:
		data = {'client_id': traktClientID()}
		dCode = getTrakt('oauth/device/code', post=data)
		result = dCode.json()
		return result
	except: 
		log_utils.error()
		return ''

def getTraktDeviceToken(traktDeviceCode):
	try:
		data = {"code": traktDeviceCode["device_code"],
				"client_id": traktClientID(),
				"client_secret": traktClientSecret()}
		start = time.time()
		expires_in = traktDeviceCode['expires_in']
		verification_url = control.lang(32513) % (highlight_color, str(traktDeviceCode['verification_url']))
		user_code = control.lang(32514) % (highlight_color, str(traktDeviceCode['user_code']))
		line = '%s\n%s\n%s'
		if control.setting('dialogs.useumbrelladialog') == 'true':
			from resources.lib.modules import tools
			trakt_qr = tools.make_qr(f"https://trakt.tv/activate?code={str(traktDeviceCode['user_code'])}")
			progressDialog = control.getProgressWindow(getLS(32073), trakt_qr, 1)
			progressDialog.set_controls()
			progressDialog.update(0, control.progress_line % (verification_url, user_code))
		else:
			progressDialog = control.progressDialog
			progressDialog.create(control.lang(32073), control.progress_line % (verification_url, user_code))
		try:
			time_passed = 0
			while not progressDialog.iscanceled() and time_passed < expires_in:
				try:
					#response = getTrakt('oauth/device/token', post=data, silent=True)
					url = urljoin(BASE_URL, 'oauth/device/token')
					response = requests.post(url, json=data,headers=headers, timeout=20)
					if response.status_code == 400:
						time_passed = time.time() - start
						progress = int(100)-int(100 * time_passed / expires_in)
						progressDialog.update(progress, control.progress_line % (verification_url, user_code))
						control.sleep(max(traktDeviceCode['interval'], 1)*1000)
				except requests.HTTPError as e:
					log_utils.log('Request Error: %s' % str(e), __name__, log_utils.LOGDEBUG)
					if e.response.status_code != 400: raise e
					progress = int(100)-int(100 * time_passed / expires_in)
					progressDialog.update(progress)
					control.sleep(max(traktDeviceCode['interval'], 1)*1000)
				else:
					if not response: continue
					else: return response
		finally:
			progressDialog.close()
		return None
	except:
		log_utils.error()

def getTraktAccountInfo():
	from datetime import datetime, timedelta
	try:
		account_info, stats = getTraktAccountSettings()
		username = account_info['user']['username']
		timezone = account_info['account']['timezone']
		joined = control.jsondate_to_datetime(account_info['user']['joined_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
		private = account_info['user']['private']
		vip = account_info['user']['vip']
		if vip: vip = '%s Years' % str(account_info['user']['vip_years'])
		total_given_ratings = stats['ratings']['total']
		movies_collected = stats['movies']['collected']
		movies_watched = stats['movies']['watched']
		movie_minutes = stats['movies']['minutes']
		if movie_minutes == 0: movies_watched_minutes = ['0 days', '0:00:00']
		elif movie_minutes < 1440: movies_watched_minutes = ['0 days', "{:0>8}".format(str(timedelta(minutes=movie_minutes)))]
		else: movies_watched_minutes = ("{:0>8}".format(str(timedelta(minutes=movie_minutes)))).split(', ')
		movies_watched_minutes = control.lang(40111) % (movies_watched_minutes[0], movies_watched_minutes[1].split(':')[0], movies_watched_minutes[1].split(':')[1])
		shows_collected = stats['shows']['collected']
		shows_watched = stats['shows']['watched']
		episodes_watched = stats['episodes']['watched']
		episode_minutes = stats['episodes']['minutes']
		if episode_minutes == 0: episodes_watched_minutes = ['0 days', '0:00:00']
		elif episode_minutes < 1440: episodes_watched_minutes = ['0 days', "{:0>8}".format(str(timedelta(minutes=episode_minutes)))]
		else: episodes_watched_minutes = ("{:0>8}".format(str(timedelta(minutes=episode_minutes)))).split(', ')
		episodes_watched_minutes = control.lang(40111) % (episodes_watched_minutes[0], episodes_watched_minutes[1].split(':')[0], episodes_watched_minutes[1].split(':')[1])
		heading = control.lang(32315)
		items = []
		items += [control.lang(40036) % username]
		items += [control.lang(40112) % timezone]
		items += [control.lang(40113) % joined]
		items += [control.lang(40114) % private]
		items += [control.lang(40115) % vip]
		items += [control.lang(40116) % str(total_given_ratings)]
		items += [control.lang(40117) % (movies_collected, movies_watched, movies_watched_minutes)]
		items += [control.lang(40118) % (shows_collected, shows_watched)]
		items += [control.lang(40119) % (episodes_watched, episodes_watched_minutes)]
		return control.selectDialog(items, heading)
	except:
		log_utils.error()
		return

def getTraktAccountSettings():
	#account_info = self.call("users/settings", with_auth=True)
	#stats = self.call("users/%s/stats" % account_info['user']['ids']['slug'], with_auth=True)
	headers['Authorization'] = 'Bearer %s' % trakt_token
	account_info = getTrakt('users/settings', post=None)
	account_info_encoded = account_info.json()
	stats = getTrakt('users/%s/stats' % account_info_encoded['user']['ids']['slug'])
	stats_encoded = stats.json()
	return account_info_encoded, stats_encoded

def getTraktCredentialsInfo():
	username, token, refresh = getSetting('trakt.user.name').strip(), getSetting('trakt.user.token'), getSetting('trakt.refreshtoken')
	if (username == '' or token == '' or refresh == ''): return False
	return True

def getTraktIndicatorsInfo():
	indicators = getSetting('indicators.alt')
	indicators = True if indicators == '1' else False
	return indicators

def getTraktAddonMovieInfo():
	try: scrobble = control.addon('script.trakt').getSetting('scrobble_movie')
	except: scrobble = ''
	try: ExcludeHTTP = control.addon('script.trakt').getSetting('ExcludeHTTP')
	except: ExcludeHTTP = ''
	try: authorization = control.addon('script.trakt').getSetting('authorization')
	except: authorization = ''
	if scrobble == 'true' and ExcludeHTTP == 'false' and authorization != '':
		return True
	else: return False

def getTraktAddonEpisodeInfo():
	try: scrobble = control.addon('script.trakt').getSetting('scrobble_episode')
	except: scrobble = ''
	try: ExcludeHTTP = control.addon('script.trakt').getSetting('ExcludeHTTP')
	except: ExcludeHTTP = ''
	try: authorization = control.addon('script.trakt').getSetting('authorization')
	except: authorization = ''
	if scrobble == 'true' and ExcludeHTTP == 'false' and authorization != '':
		return True
	else: return False

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
	if getSetting('trakt.general.notifications') == 'true':
		if success is True: control.notification(title=32315, message=getLS(35502) % ('[COLOR %s]%s[/COLOR]' % (highlight_color, name)))
		else: control.notification(title=32315, message=getLS(35504) % ('[COLOR %s]%s[/COLOR]' % (highlight_color, name)))
	if not success: log_utils.log(getLS(35504) % name + ' : ids={imdb: %s, tvdb: %s}' % (imdb, tvdb), __name__, level=log_utils.LOGDEBUG)

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
	if getSetting('trakt.general.notifications') == 'true':
		if success is True: control.notification(title=32315, message=getLS(35503) % ('[COLOR %s]%s[/COLOR]' % (highlight_color, name)))
		else: control.notification(title=32315, message=getLS(35505) % ('[COLOR %s]%s[/COLOR]' % (highlight_color, name)))
	if not success: log_utils.log(getLS(35505) % name + ' : ids={imdb: %s, tvdb: %s}' % (imdb, tvdb), __name__, level=log_utils.LOGDEBUG)

def like_list(list_owner, list_name, list_id):
	try:
		headers['Authorization'] = 'Bearer %s' % trakt_token
		# resp_code = client._basic_request('https://api.trakt.tv/users/%s/lists/%s/like' % (list_owner, list_id), headers=headers, method='POST', ret_code=True)
		resp_code = session.post('https://api.trakt.tv/users/%s/lists/%s/like' % (list_owner, list_id), headers=headers).status_code
		if resp_code == 204:
			control.notification(title=32315, message='Successfuly Liked list:  [COLOR %s]%s[/COLOR]' % (highlight_color, list_name))
			sync_liked_lists()
		else: control.notification(title=32315, message='Failed to Like list %s' % list_name)
		control.refresh()
	except: log_utils.error()

def unlike_list(list_owner, list_name, list_id):
	try:
		headers['Authorization'] = 'Bearer %s' % trakt_token
		# resp_code = client._basic_request('https://api.trakt.tv/users/%s/lists/%s/like' % (list_owner, list_id), headers=headers, method='DELETE', ret_code=True)
		resp_code = session.delete('https://api.trakt.tv/users/%s/lists/%s/like' % (list_owner, list_id), headers=headers).status_code
		if resp_code == 204:
			control.notification(title=32315, message='Successfuly Unliked list:  [COLOR %s]%s[/COLOR]' % (highlight_color, list_name))
			traktsync.delete_liked_list(list_id)
		else: control.notification(title=32315, message='Failed to UnLike list %s' % list_name)
		control.refresh()
	except: log_utils.error()

def remove_liked_lists(trakt_ids):
	if not trakt_ids: return
	success = None
	try:
		headers['Authorization'] = 'Bearer %s' % trakt_token
		for id in trakt_ids:
			list_owner = id.get('list_owner')
			list_id = id.get('trakt_id')
			list_name = id.get('list_name')
			# resp_code = client._basic_request('https://api.trakt.tv/users/%s/lists/%s/like' % (list_owner, list_id), headers=headers, method='DELETE', ret_code=True)
			resp_code = session.delete('https://api.trakt.tv/users/%s/lists/%s/like' % (list_owner, list_id), headers=headers).status_code
			if resp_code == 204:
				control.notification(title=32315, message='Successfuly Unliked list:  [COLOR %s]%s[/COLOR]' % (highlight_color, list_name))
				traktsync.delete_liked_list(list_id)
			else: control.notification(title=32315, message='Failed to UnLike list %s' % list_name)
			control.sleep(1000)
		control.refresh()
	except: log_utils.error()

def rate(imdb=None, tvdb=None, season=None, episode=None):
	return _rating(action='rate', imdb=imdb, tvdb=tvdb, season=season, episode=episode)

def unrate(imdb=None, tvdb=None, season=None, episode=None):
	return _rating(action='unrate', imdb=imdb, tvdb=tvdb, season=season, episode=episode)

def rateShow(imdb=None, tvdb=None, season=None, episode=None):
	if getSetting('trakt.rating') == 1:
		rate(imdb=imdb, tvdb=tvdb, season=season, episode=episode)

def _rating(action, imdb=None, tvdb=None, season=None, episode=None):
	control.busy()
	try:
		addon = 'script.trakt'
		if control.condVisibility('System.HasAddon(%s)' % addon):
			import importlib.util
			data = {}
			data['action'] = action
			if tvdb:
				data['video_id'] = tvdb
				if episode:
					data['media_type'] = 'episode'
					data['dbid'] = 1
					data['season'] = int(season)
					data['episode'] = int(episode)
				elif season:
					data['media_type'] = 'season'
					data['dbid'] = 5
					data['season'] = int(season)
				else:
					data['media_type'] = 'show'
					data['dbid'] = 2
			else:
				data['video_id'] = imdb
				data['media_type'] = 'movie'
				data['dbid'] = 4

			script_path = control.joinPath(control.addonPath(addon), 'resources', 'lib', 'sqlitequeue.py')
			spec = importlib.util.spec_from_file_location("sqlitequeue.py", script_path)
			sqlitequeue = importlib.util.module_from_spec(spec)
			spec.loader.exec_module(sqlitequeue)
			data = {'action': 'manualRating', 'ratingData': data}
			sqlitequeue.SqliteQueue().append(data)
		else:
			control.notification(title=32315, message=33659)
		control.hide()
	except: log_utils.error()

def unHideItems(tvdb_ids):
	if not tvdb_ids: return
	success = None
	try:
		sections = ['progress_watched', 'calendar']
		ids = []
		for id in tvdb_ids: ids.append({"ids": {"tvdb": int(id)}})
		post = {"shows": ids}
		for section in sections:
			success = getTrakt('users/hidden/%s/remove' % section, post=post)
			control.sleep(1000)
		if success:
			if 'plugin.video.umbrella' in control.infoLabel('Container.PluginName'): control.refresh()
			traktsync.delete_hidden_progress(tvdb_ids)
			control.trigger_widget_refresh()
			return True
	except:
		log_utils.error()
		return False

def hideItems(tvdb_ids):
	if not tvdb_ids: return
	success = None
	try:
		sections = ['progress_watched', 'calendar']
		ids = []
		for id in tvdb_ids: ids.append({"ids": {"tvdb": int(id)}})
		post = {"shows": ids}
		for section in sections:
			success = getTrakt('users/hidden/%s' % section, post=post)
			control.sleep(1000)
		if success:
			if 'plugin.video.umbrella' in control.infoLabel('Container.PluginName'): control.refresh()
			sync_hidden_progress(forced=True)
			control.trigger_widget_refresh()
			return True
	except:
		log_utils.error()
		return False

def hideItem(name, imdb=None, tvdb=None, season=None, episode=None, refresh=True, tvshow=None):
	success = None
	try:
		sections = ['progress_watched', 'calendar']
		sections_display = [getLS(40072), getLS(40073), getLS(32181)]
		selection = control.selectDialog([i for i in sections_display], heading=control.addonInfo('name') + ' - ' + getLS(40074))
		if selection == -1: return
		control.busy()
		if episode: post = {"shows": [{"ids": {"tvdb": tvdb}}]}
		elif tvshow: post = {"shows": [{"ids": {"tvdb": tvdb}}]}
		else: post = {"movies": [{"ids": {"imdb": imdb}}]}
		if selection in (0, 1):
			section = sections[selection]
			success = getTrakt('users/hidden/%s' % section, post=post)
		else:
			for section in sections:
				success = getTrakt('users/hidden/%s' % section, post=post)
				control.sleep(1000)
		if success:
			control.hide()
			sync_hidden_progress(forced=True)
			if refresh: control.refresh()
			control.trigger_widget_refresh()
			if getSetting('trakt.general.notifications') == 'true':
				control.notification(title=32315, message=getLS(33053) % (name, sections_display[selection]))
	except: log_utils.error()

def removeCollectionItems(type, id_list):
	if not id_list: return
	success = None
	try:
		ids = []
		total_items = len(id_list)
		for id in id_list: ids.append({"ids": {"trakt": id}})
		post = {type: ids}
		success = getTrakt('/sync/collection/remove', post=post)
		if success:
			# if 'plugin.video.umbrella' in control.infoLabel('Container.PluginName'): control.refresh()
			control.trigger_widget_refresh()
			if type == 'movies': traktsync.delete_collection_items(id_list, 'movies_collection')
			else: traktsync.delete_collection_items(id_list, 'shows_collection')
			if getSetting('trakt.general.notifications') == 'true':
				control.notification(title='Trakt Collection Manager', message='Successfuly Removed %s Item%s' % (total_items, 's' if total_items >1 else ''))
	except: log_utils.error()

def removeWatchlistItems(type, id_list):
	if not id_list: return
	success = None
	try:
		ids = []
		total_items = len(id_list)
		for id in id_list: ids.append({"ids": {"trakt": id}})
		post = {type: ids}
		success = getTrakt('/sync/watchlist/remove', post=post)
		if success:
			# if 'plugin.video.umbrella' in control.infoLabel('Container.PluginName'): control.refresh()
			control.trigger_widget_refresh()
			if type == 'movies': traktsync.delete_watchList_items(id_list, 'movies_watchlist')
			else: traktsync.delete_watchList_items(id_list, 'shows_watchlist')
			if getSetting('trakt.general.notifications') == 'true':
				control.notification(title='Trakt Watch List Manager', message='Successfuly Removed %s Item%s' % (total_items, 's' if total_items >1 else ''))
	except: log_utils.error()

def manager(name, imdb=None, tvdb=None, season=None, episode=None, refresh=True, watched=None, unfinished=False, tvshow=None):
	lists = []
	try:
		if season: season = int(season)
		if episode: episode = int(episode)
		media_type = 'Show' if tvdb else 'Movie'
		if watched is not None:
			if watched is True:
				items = [(getLS(33652) % highlight_color, 'unwatch')]
			else:
				items = [(getLS(33651) % highlight_color, 'watch')]
		else:
			items = [(getLS(33651) % highlight_color, 'watch')]
			items += [(getLS(33652) % highlight_color, 'unwatch')]
		if control.condVisibility('System.HasAddon(script.trakt)'):
			items += [(getLS(33653) % highlight_color, 'rate')]
			items += [(getLS(33654) % highlight_color, 'unrate')]
		if tvdb:
			items += [(getLS(40075) % (highlight_color, media_type), 'hideItem')]
			items += [(getLS(35058) % highlight_color, 'hiddenManager')]
		if unfinished is True:
			if media_type == 'Movie': items += [(getLS(35059) % highlight_color, 'unfinishedMovieManager')]
			elif episode: items += [(getLS(35060) % highlight_color, 'unfinishedEpisodeManager')]
		if getSetting('trakt.scrobble') == 'true' and getSetting('resume.source') == '1':
			if media_type == 'Movie' or episode:
				items += [(getLS(40076) % highlight_color, 'scrobbleReset')]
		if season or episode:
			items += [(getLS(33573) % highlight_color, '/sync/watchlist')]
			items += [(getLS(33574) % highlight_color, '/sync/watchlist/remove')]
		items += [(getLS(33577) % highlight_color, '/sync/watchlist')]
		items += [(getLS(33578) % highlight_color, '/sync/watchlist/remove')]
		items += [(getLS(33575) % highlight_color, '/sync/collection')]
		items += [(getLS(33576) % highlight_color, '/sync/collection/remove')]
		items += [(getLS(33579), '/users/me/lists/%s/items')]

		result = getTraktAsJson('/users/me/lists')
		lists = [(i['name'], i['ids']['slug']) for i in result]
		lists = [lists[i//2] for i in range(len(lists)*2)]

		for i in range(0, len(lists), 2):
			lists[i] = ((getLS(33580) % (highlight_color, lists[i][0])), '/users/me/lists/%s/items' % lists[i][1])
		for i in range(1, len(lists), 2):
			lists[i] = ((getLS(33581) % (highlight_color, lists[i][0])), '/users/me/lists/%s/items/remove' % lists[i][1])
		items += lists

		control.hide()
		select = control.selectDialog([i[0] for i in items], heading=control.addonInfo('name') + ' - ' + getLS(32515))

		if select == -1: return
		if select >= 0:
			if items[select][1] == 'watch':
				watch(control.infoLabel('Container.ListItem.DBTYPE'), name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=refresh)
			elif items[select][1] == 'unwatch':
				unwatch(control.infoLabel('Container.ListItem.DBTYPE'), name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=refresh)
			elif items[select][1] == 'rate':
				rate(imdb=imdb, tvdb=tvdb, season=season, episode=episode)
			elif items[select][1] == 'unrate':
				unrate(imdb=imdb, tvdb=tvdb, season=season, episode=episode)
			elif items[select][1] == 'hideItem':
				hideItem(name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, tvshow=tvshow)
			elif items[select][1] == 'hiddenManager':
				control.execute('RunPlugin(plugin://plugin.video.umbrella/?action=shows_traktHiddenManager)')
			elif items[select][1] == 'unfinishedEpisodeManager':
				control.execute('RunPlugin(plugin://plugin.video.umbrella/?action=episodes_traktUnfinishedManager)')
			elif items[select][1] == 'unfinishedMovieManager':
				control.execute('RunPlugin(plugin://plugin.video.umbrella/?action=movies_traktUnfinishedManager)')
			elif items[select][1] == 'scrobbleReset':
				scrobbleReset(imdb=imdb, tmdb='', tvdb=tvdb, season=season, episode=episode, widgetRefresh=True)
			else:
				if not tvdb: post = {"movies": [{"ids": {"imdb": imdb}}]}
				else:
					if episode:
						if items[select][1] == '/sync/watchlist' or items[select][1] == '/sync/watchlist/remove':
							post = {"shows": [{"ids": {"tvdb": tvdb}}]}
						else:
							post = {"shows": [{"ids": {"tvdb": tvdb}, "seasons": [{"number": season, "episodes": [{"number": episode}]}]}]}
							name = name + ' - ' + '%sx%02d' % (season, episode)
					elif season:
						if items[select][1] == '/sync/watchlist' or items[select][1] == '/sync/watchlist/remove':
							post = {"shows": [{"ids": {"tvdb": tvdb}}]}
						else:
							post = {"shows": [{"ids": {"tvdb": tvdb}, "seasons": [{"number": season}]}]}
							name = name + ' - ' + 'Season %s' % season
					else: post = {"shows": [{"ids": {"tvdb": tvdb}}]}
				if items[select][1] == '/users/me/lists/%s/items':
					slug = listAdd(successNotification=True)
					if slug: getTrakt(items[select][1] % slug, post=post)
				else: getTrakt(items[select][1], post=post)

				if items[select][1] == '/sync/watchlist': sync_watch_list(forced=True)
				if items[select][1] == '/sync/watchlist/remove':
					if media_type == 'Movie': traktsync.delete_watchList_items([imdb], 'movies_watchlist', 'imdb')
					else: traktsync.delete_watchList_items([tvdb], 'shows_watchlist', 'tvdb')
				if items[select][1] == '/sync/collection':
					sync_collection(forced=True)
				if items[select][1] == '/sync/collection/remove':
					if media_type == 'Movie': traktsync.delete_collection_items([imdb], 'movies_collection', 'imdb')
					else: traktsync.delete_collection_items([tvdb], 'shows_collection', 'tvdb')

				control.hide()
				#list = re.search('\[B](.+?)\[/B]', items[select][0]).group(1)
				list = re.search(r'\[B\](.+?)\[/B\]', items[select][0]).group(1)
				message = getLS(33583) if 'remove' in items[select][1] else getLS(33582)
				if items[select][0].startswith('Add'): refresh = False
				control.hide()
				if refresh: control.refresh()
				control.trigger_widget_refresh()
				if getSetting('trakt.general.notifications') == 'true': control.notification(title=name, message=message + ' (%s)' % list)
	except:
		log_utils.error()
		control.hide()

def listAdd(successNotification=True):
	t = getLS(32520)
	k = control.keyboard('', t) ; k.doModal()
	new = k.getText() if k.isConfirmed() else None
	if not new: return
	result = getTrakt('/users/me/lists', post = {"name" : new, "privacy" : "private"})
	try:
		slug = result.json()['ids']['slug']
		if successNotification: control.notification(title=32070, message=33661)
		return slug
	except:
		control.notification(title=32070, message=33584)
		return None

def lists(id=None):
	return cache.get(getTraktAsJson, 48, 'https://api.trakt.tv/users/me/lists' + ('' if not id else ('/' + str(id))))

def list(id):
	return lists(id=id)

def slug(name):
	name = name.strip()
	name = name.lower()
	name = re.sub(r'[^a-z0-9_]', '-', name) # check apostrophe
	name = re.sub(r'--+', '-', name)
	return name

def getActivity():
	try:
		i = getTraktAsJson('/sync/last_activities')
		if not i: return 0
		activity = []
		activity.append(i['movies']['watched_at']) # added 8/30/20
		activity.append(i['movies']['collected_at'])
		activity.append(i['movies']['watchlisted_at'])
		activity.append(i['movies']['paused_at']) # added 8/30/20
		activity.append(i['movies']['hidden_at']) # added 4/02/21
		activity.append(i['episodes']['watched_at']) # added 8/30/20
		activity.append(i['episodes']['collected_at'])
		activity.append(i['episodes']['watchlisted_at'])
		activity.append(i['episodes']['paused_at']) # added 8/30/20
		activity.append(i['shows']['watchlisted_at'])
		activity.append(i['shows']['hidden_at']) # added 4/02/21
		activity.append(i['seasons']['watchlisted_at'])
		activity.append(i['seasons']['hidden_at']) # added 4/02/21
		activity.append(i['lists']['liked_at'])
		activity.append(i['lists']['updated_at'])
		activity = [int(cleandate.iso_2_utc(i)) for i in activity]
		activity = sorted(activity, key=int)[-1]
		return activity
	except: log_utils.error()

def getHiddenActivity(activities=None):
	try:
		if activities: i = activities
		else: i = getTraktAsJson('/sync/last_activities')
		if not i: return 0
		activity = []
		activity.append(i['movies']['hidden_at'])
		activity.append(i['shows']['hidden_at'])
		activity.append(i['seasons']['hidden_at'])
		activity = [int(cleandate.iso_2_utc(i)) for i in activity]
		activity = sorted(activity, key=int)[-1]
		return activity
	except: log_utils.error()

def getWatchedActivity(activities=None):
	try:
		if activities: i = activities
		else: i = getTraktAsJson('/sync/last_activities')
		if not i: return 0
		activity = []
		activity.append(i['movies']['watched_at'])
		activity.append(i['episodes']['watched_at'])
		activity = [int(cleandate.iso_2_utc(i)) for i in activity]
		activity = sorted(activity, key=int)[-1]
		return activity
	except: log_utils.error()

def getMoviesWatchedActivity(activities=None):
	try:
		if activities: i = activities
		else: i = getTraktAsJson('/sync/last_activities')
		if not i: return 0
		activity = []
		activity.append(i['movies']['watched_at'])
		activity = [int(cleandate.iso_2_utc(i)) for i in activity]
		activity = sorted(activity, key=int)[-1]
		return activity
	except: log_utils.error()

def getEpisodesWatchedActivity(activities=None):
	try:
		if activities: i = activities
		else: i = getTraktAsJson('/sync/last_activities')
		if not i: return 0
		activity = []
		activity.append(i['episodes']['watched_at'])
		activity = [int(cleandate.iso_2_utc(i)) for i in activity]
		activity = sorted(activity, key=int)[-1]
		return activity
	except: log_utils.error()

def getCollectedActivity(activities=None):
	try:
		if activities: i = activities
		else: i = getTraktAsJson('/sync/last_activities')
		if not i: return 0
		activity = []
		activity.append(i['movies']['collected_at'])
		activity.append(i['episodes']['collected_at'])
		activity = [int(cleandate.iso_2_utc(i)) for i in activity]
		activity = sorted(activity, key=int)[-1]
		return activity
	except: log_utils.error()

def getWatchListedActivity(activities=None):
	try:
		if activities: i = activities
		else: i = getTraktAsJson('/sync/last_activities')
		if not i: return 0
		activity = []
		activity.append(i['movies']['watchlisted_at'])
		activity.append(i['episodes']['watchlisted_at'])
		activity.append(i['shows']['watchlisted_at'])
		activity.append(i['seasons']['watchlisted_at'])
		activity = [int(cleandate.iso_2_utc(i)) for i in activity]
		activity = sorted(activity, key=int)[-1]
		return activity
	except: log_utils.error()

def getPausedActivity(activities=None):
	try:
		if activities: i = activities
		else: i = getTraktAsJson('/sync/last_activities')
		if not i: return 0
		activity = []
		activity.append(i['movies']['paused_at'])
		activity.append(i['episodes']['paused_at'])
		activity = [int(cleandate.iso_2_utc(i)) for i in activity]
		activity = sorted(activity, key=int)[-1]
		return activity
	except: log_utils.error()

def getListActivity(activities=None):
	try:
		if activities: i = activities
		else: i = getTraktAsJson('/sync/last_activities')
		if not i: return 0
		activity = []
		activity.append(i['lists']['liked_at'])
		activity.append(i['lists']['updated_at'])
		activity = [int(cleandate.iso_2_utc(i)) for i in activity]
		activity = sorted(activity, key=int)[-1]
		return activity
	except: log_utils.error()

def getUserListActivity(activities=None):
	try:
		if activities: i = activities
		else: i = getTraktAsJson('/sync/last_activities')
		if not i: return 0
		activity = []
		activity.append(i['lists']['updated_at'])
		activity = [int(cleandate.iso_2_utc(i)) for i in activity]
		activity = sorted(activity, key=int)[-1]
		return activity
	except: log_utils.error()

def getProgressActivity(activities=None):
	try:
		if activities: i = activities
		else: i = getTraktAsJson('/sync/last_activities')
		if not i: return 0
		activity = []
		activity.append(i['episodes']['watched_at'])
		activity.append(i['shows']['hidden_at'])
		activity.append(i['seasons']['hidden_at'])
		activity = [int(cleandate.iso_2_utc(i)) for i in activity]
		activity = sorted(activity, key=int)[-1]
		return activity
	except: log_utils.error()

def cachesyncMovies(timeout=0):
	indicators = traktsync.get(syncMovies, timeout)
	#if getSetting('sync.watched.library') == 'true':
		#syncMoviesLibrary(indicators)
	return indicators

def syncMovies():
	try:
		if not getTraktCredentialsInfo(): return
		indicators = getTraktAsJson('/users/me/watched/movies')
		if not indicators: return None
		indicators = [i['movie']['ids'] for i in indicators]
		indicators = [str(i['imdb']) for i in indicators if 'imdb' in i]
		return indicators
	except: log_utils.error()

def timeoutsyncMovies():
	timeout = traktsync.timeout(syncMovies)
	return timeout

def syncMoviesLibrary(indicators):
	if indicators:
		try:
			libMovies = control.jsonrpc('{"jsonrpc": "2.0","method":"VideoLibrary.GetMovies","params":{"properties": ["title", "year", "lastplayed", "playcount", "uniqueid"],"sort": {"order": "ascending", "method": "title"}},"id":1}')
			libMovies = jsloads(libMovies).get('result').get('movies')
		except:
			libMovies = []
		moviebatch = []
		removeBatch = []
		for movie in libMovies:
			if str(movie.get('uniqueid').get('imdb')) not in indicators:
				if movie.get('playcount')== 1:
					removeBatch.append(jsloads('{"jsonrpc":"2.0","method":"VideoLibrary.SetMovieDetails","params":{"movieid":%s, "playcount":0}, "id":3}' % movie.get('movieid')))
					log_utils.log('Movie Marked for Playcount Removal. Movie: %s' % movie.get('label'), level=log_utils.LOGDEBUG)
			for indicator in indicators:
				if str(movie.get('uniqueid').get('imdb')) == str(indicator): #compare imdb ids in library with imdb ids in indicators

						if str(movie.get('playcount')) == '1':
							log_utils.log('Movie Already Marked. Movie: %s' % movie.get('label'),level=log_utils.LOGDEBUG)
						else:
							moviebatch.append(jsloads('{"jsonrpc":"2.0","method":"VideoLibrary.SetMovieDetails","params":{"movieid":%s, "playcount":1}, "id":2}' % movie.get('movieid')))
							log_utils.log('Marked Movie: %s' % movie.get('label'),level=log_utils.LOGDEBUG)
		if len(moviebatch) > 0 or len(removeBatch) > 0:
			moviebatch.extend(removeBatch)
			control.jsonrpc(jsdumps(moviebatch))

def watchedMovies():
	try:
		if not getTraktCredentialsInfo(): return
		return getTraktAsJson('/users/me/watched/movies?extended=full')
	except: log_utils.error()

def watchedMoviesTime(imdb):
	try:
		imdb = str(imdb)
		items = watchedMovies()
		for item in items:
			if str(item['movie']['ids']['imdb']) == imdb: return item['last_watched_at']
	except: log_utils.error()

def watchedShows():
	try:
		if not getTraktCredentialsInfo(): return
		return getTraktAsJson('/users/me/watched/shows?extended=full')
	except: log_utils.error()

def watchedShowsTime(tvdb, season, episode):
	try:
		tvdb = str(tvdb)
		season = int(season)
		episode = int(episode)
		items = watchedShows()
		for item in items:
			if str(item['show']['ids']['tvdb']) == tvdb:
				seasons = item['seasons']
				for s in seasons:
					if s['number'] == season:
						episodes = s['episodes']
						for e in episodes:
							if e['number'] == episode:
								return e['last_watched_at']
	except: log_utils.error()

def cachesyncTV(imdb, tvdb): # sync full watched shows then sync imdb_id "season indicators" and "season counts"
	try:
		threads = [Thread(target=cachesyncTVShows), Thread(target=cachesyncSeasons, args=(imdb, tvdb))]
		[i.start() for i in threads]
		[i.join() for i in threads]
		traktsync.insert_syncSeasons_at()
	except: log_utils.error()

def cachesyncTVShows(timeout=0):
	try:
		indicators = traktsync.get(syncTVShows, timeout)
		#if getSetting('sync.watched.library') == 'true':
			#syncTVShowsLibrary(indicators)
		return indicators
	except:
		indicators = ''
		return indicators

def syncTVShows(): # sync all watched shows ex. [({'imdb': 'tt12571834', 'tvdb': '384435', 'tmdb': '105161', 'trakt': '163639'}, 16, [(1, 16)]), ({'imdb': 'tt11761194', 'tvdb': '377593', 'tmdb': '119845', 'trakt': '158621'}, 2, [(1, 1), (1, 2)])]
	try:
		if not getTraktCredentialsInfo(): return
		indicators = getTraktAsJson('/users/me/watched/shows?extended=full')
		if not indicators: return None
# /shows/ID/progress/watched  endpoint only accepts imdb or trakt ID so write all ID's
		indicators = [({'imdb': i['show']['ids']['imdb'], 'tvdb': str(i['show']['ids']['tvdb']), 'tmdb': str(i['show']['ids']['tmdb']), 'trakt': str(i['show']['ids']['trakt'])}, \
											i['show']['aired_episodes'], sum([[(s['number'], e['number']) for e in s['episodes'] if i['reset_at'] is None or e['last_watched_at'] > i['reset_at']] for s in i['seasons']], [])) for i in indicators]
		# indicators = [({'imdb': i['show']['ids']['imdb'], 'tvdb': str(i['show']['ids']['tvdb']), 'tmdb': str(i['show']['ids']['tmdb']), 'trakt': str(i['show']['ids']['trakt'])}, \
		# 									i['show']['aired_episodes'], sum([[(s['number'], e['number']) for e in s['episodes']] for s in i['seasons']], [])) for i in indicators]
		indicators = [(i[0], int(i[1]), i[2]) for i in indicators]
		return indicators
	except: log_utils.error()

# def syncTVShowsLibrary(indicators):
# 	if indicators:
# 		try:
# 			libShows = control.jsonrpc('{"jsonrpc": "2.0","method":"VideoLibrary.GetTVShows","params":{"properties": ["title", "year", "lastplayed", "playcount", "uniqueid"],"sort": {"order": "ascending", "method": "title"}},"id":1}')
# 			libShows = jsloads(libShows).get('result').get('tvshows')
# 		except:
# 			libShows = []
# 		episodesMarked = []
# 		removeBatch2 = []
# 		for show in libShows:
# 			if str(show.get('uniqueid').get('imdb')) not in str(indicators):
# 				eps = control.jsonrpc('{"jsonrpc":"2.0","id":1,"method":"VideoLibrary.GetEpisodes","params":{"tvshowid":%s, "properties": ["season", "episode", "playcount"]}}' % show.get('tvshowid'))
# 				eps = jsloads(eps).get('result').get('episodes')
# 				for episodes in eps:
				
# 					if episodes.get('playcount') == 1:
# 						removeBatch2.append(jsloads(('{"jsonrpc":"2.0","method":"VideoLibrary.SetEpisodeDetails","params":{"episodeid":%s, "playcount":0}, "id":3}' % episodes.get('episodeid'))))
# 						log_utils.log('Show Marked for Playcount Removal. Show: %s' % show.get('label'),level=log_utils.LOGDEBUG)
# 			for indicator in indicators:
# 				if str(show.get('uniqueid').get('imdb')) == str(indicator[0]['imdb']): #compare imdb ids in library with imdb ids in indicators
# 					epsWatched = indicator[2]
# 					eps = control.jsonrpc('{"jsonrpc":"2.0","id":1,"method":"VideoLibrary.GetEpisodes","params":{"tvshowid":%s, "properties": ["season", "episode", "playcount"]}}' % show.get('tvshowid'))
# 					eps = jsloads(eps).get('result').get('episodes')
# 					for epis in eps:
# 						if (epis.get('season'), epis.get('episode')) not in epsWatched:
# 							if epis.get('playcount') == 1:
# 								removeBatch2.append(jsloads(('{"jsonrpc":"2.0","method":"VideoLibrary.SetEpisodeDetails","params":{"episodeid":%s, "playcount":0}, "id":3}' % epis.get('episodeid'))))
# 								log_utils.log('Marked for playcount removal show: %s season: %s episode: %s' % (show.get('label'), epis.get('season'),epis.get('episode')),level=log_utils.LOGDEBUG)
# 						for ep in epsWatched:
# 							if ep[0] == epis.get('season') and ep[1] == epis.get('episode'):
# 								if epis.get('playcount') == 0:
# 									episodesMarked.append(jsloads(('{"jsonrpc":"2.0","method":"VideoLibrary.SetEpisodeDetails","params":{"episodeid":%s, "playcount":1}, "id":2}' % epis.get('episodeid'))))
# 									log_utils.log('Marked show: %s season: %s episode: %s' % (show.get('label'), epis.get('season'),epis.get('episode')),level=log_utils.LOGDEBUG)
# 		if len(episodesMarked) > 0 or len(removeBatch2) > 0:
# 			episodesMarked.extend(removeBatch2)
# 			control.jsonrpc(jsdumps(episodesMarked))

def cachesyncSeasons(imdb, tvdb, trakt=None, timeout=0):
	try:
		imdb = imdb or ''
		tvdb = tvdb or ''
		indicators = traktsync.get(syncSeasons, timeout, imdb, tvdb, trakt=trakt) # named var not included in function md5_hash
		return indicators
	except: log_utils.error()

def syncSeasons(imdb, tvdb, trakt=None): # season indicators and counts for watched shows ex. [['1', '2', '3'], {1: {'total': 8, 'watched': 8, 'unwatched': 0}, 2: {'total': 10, 'watched': 10, 'unwatched': 0}}]
	indicators_and_counts = []
	try:
		if all(not value for value in (imdb, tvdb, trakt)): return
		if not getTraktCredentialsInfo(): return
		id = imdb or trakt
		if not id and tvdb:
			log_utils.log('syncSeasons missing imdb_id, pulling trakt id from watched shows database', level=log_utils.LOGDEBUG)
			db_watched = traktsync.cache_existing(syncTVShows) # pull trakt ID from db because imdb ID is missing
			ids = [i[0] for i in db_watched if i[0].get('tvdb') == tvdb]
			id = ids[0].get('trakt', '') if ids[0].get('trakt') else ''
			if not id:
				log_utils.log("syncSeasons FAILED: missing required imdb and trakt ID's for tvdb=%s" % tvdb, level=log_utils.LOGDEBUG)
				return
		if getSetting('tv.specials') == 'true':
			results = getTraktAsJson('/shows/%s/progress/watched?specials=true&hidden=false&count_specials=true' % id, silent=True) # only imdb or trakt ID allowed
		else:
			results = getTraktAsJson('/shows/%s/progress/watched?specials=false&hidden=false' % id, silent=True)
		if not results: return

		seasons = [{'reset_at': results['reset_at']}, results['seasons']]
		reset_at = seasons[0].get('reset_at','')
		if reset_at:           #added to cover trakt reset watching
			for x in seasons[1]:
				episodesComplete = 0
				for y in x['episodes']:
					last_watched = y.get('last_watched_at', '')
					if last_watched:
						if last_watched < reset_at:
							y['completed'] = False
						else:
							episodesComplete = episodesComplete + 1
					else:
						if last_watched:
							episodesComplete = episodesComplete + 1
				x['completed'] = episodesComplete

		seasons = seasons[1]
###--- future-need tmdb_id passed now ---###
		# next_episode = results['next_episode']
		# # log_utils.log('next_episode=%s' % next_episode)
		# db_watched = traktsync.cache_existing(syncTVShows)
		# ids = [i[0] for i in db_watched if (i[0].get('imdb') == imdb or i[0].get('tvdb') == tvdb)]
		# tmdb = str(ids[0].get('tmdb', '')) if ids[0].get('tmdb') else ''
		# trakt = str(ids[0].get('trakt', '')) if ids[0].get('trakt') else ''
		# traktsync.insert_nextEpisode(imdb, tvdb, tmdb, trakt, next_episode)
#######
		#indicators = [({'imdb': i['show']['ids']['imdb'], 'tvdb': str(i['show']['ids']['tvdb']), 'tmdb': str(i['show']['ids']['tmdb']), 'trakt': str(i['show']['ids']['trakt'])}, \
											#i['show']['aired_episodes'], sum([[(s['number'], e['number']) for e in s['episodes'] if i['reset_at'] is None or e['last_watched_at'] > i['reset_at']] for s in i['seasons']], [])) for i in indicators]
		indicators = [(i['number'], [x['completed'] for x in i['episodes']]) for i in seasons]
		indicators = ['%01d' % int(i[0]) for i in indicators if False not in i[1]]
		indicators_and_counts.append(indicators)
		counts = {season['number']: {'total': season['aired'], 'watched': season['completed'], 'unwatched': season['aired'] - season['completed']} for season in seasons}
		indicators_and_counts.append(counts)
		return indicators_and_counts
	except:
		log_utils.error()
		return None

def seasonCount(imdb, tvdb): # return counts for all seasons of a show from traktsync.db
	try:
		counts = traktsync.cache_existing(syncSeasons, imdb, tvdb) # this needs trakt ID
		if not counts: return
		return counts[1]
	except:
		log_utils.error()
		return None

def timeoutsyncTVShows():
	timeout = traktsync.timeout(syncTVShows)
	return timeout

def timeoutsyncSeasons(imdb, tvdb):
	try:
		timeout = traktsync.timeout(syncSeasons, imdb, tvdb, returnNone=True) # returnNone must be named arg or will end up considered part of "*args"
		return timeout
	except: log_utils.error()

def update_syncMovies(imdb, remove_id=False):
	try:
		indicators = traktsync.cache_existing(syncMovies)
		if remove_id: indicators.remove(imdb)
		else: indicators.append(imdb)
		key = traktsync._hash_function(syncMovies, ())
		traktsync.cache_insert(key, repr(indicators))
	except: log_utils.error()

def service_syncSeasons(): # season indicators and counts for watched shows ex. [['1', '2', '3'], {1: {'total': 8, 'watched': 8, 'unwatched': 0}, 2: {'total': 10, 'watched': 10, 'unwatched': 0}}]
	try:
		indicators = traktsync.cache_existing(syncTVShows) # use cached data from service cachesyncTVShows() just written fresh
		threads = []
		for indicator in indicators:
			imdb = indicator[0].get('imdb', '') if indicator[0].get('imdb') else ''
			tvdb = str(indicator[0].get('tvdb', '')) if indicator[0].get('tvdb') else ''
			trakt = str(indicator[0].get('trakt', '')) if indicator[0].get('trakt') else ''
			threads.append(Thread(target=cachesyncSeasons, args=(imdb, tvdb, trakt))) # season indicators and counts for an entire show
		[i.start() for i in threads]
		[i.join() for i in threads]
	except: log_utils.error()

def markMovieAsWatched(imdb):
	try:
		result = getTraktAsJson('/sync/history', {"movies": [{"ids": {"imdb": imdb}}]})
		result = result['added']['movies'] != 0
		if getSetting('debug.level') == '1':
			log_utils.log('Trakt markMovieAsWatched IMDB: %s Result: %s' % (imdb, result), level=log_utils.LOGDEBUG)
		return result
	except: log_utils.error()

def markMovieAsNotWatched(imdb):
	try:
		result = getTraktAsJson('/sync/history/remove', {"movies": [{"ids": {"imdb": imdb}}]})
		return result['deleted']['movies'] != 0
	except: log_utils.error()

def markTVShowAsWatched(imdb, tvdb):
	try:
		result = getTraktAsJson('/sync/history', {"shows": [{"ids": {"imdb": imdb, "tvdb": tvdb}}]})
		if result['added']['episodes'] == 0 and tvdb: # sometimes trakt fails to mark because of imdb_id issues, check tvdb only as fallback if it fails
			control.sleep(1000) # POST 1 call per sec rate-limit
			result = getTraktAsJson('/sync/history', {"shows": [{"ids": {"tvdb": tvdb}}]})
			if not result: return False
		return result['added']['episodes'] != 0
	except: log_utils.error()

def markTVShowAsNotWatched(imdb, tvdb):
	try:
		result = getTraktAsJson('/sync/history/remove', {"shows": [{"ids": {"imdb": imdb, "tvdb": tvdb}}]})
		if not result: return False
		if result['deleted']['episodes'] == 0 and tvdb: # sometimes trakt fails to mark because of imdb_id issues, check tvdb only as fallback if it fails
			control.sleep(1000) # POST 1 call per sec rate-limit
			result = getTraktAsJson('/sync/history/remove', {"shows": [{"ids": {"tvdb": tvdb}}]})
			if not result: return False
		return result['deleted']['episodes'] != 0
	except: log_utils.error()

def markSeasonAsWatched(imdb, tvdb, season):
	try:
		season = int('%01d' % int(season))
		result = getTraktAsJson('/sync/history', {"shows": [{"seasons": [{"number": season}], "ids": {"imdb": imdb, "tvdb": tvdb}}]})
		if not result: return False
		if result['added']['episodes'] == 0 and tvdb: # sometimes trakt fails to mark because of imdb_id issues, check tvdb only as fallback if it fails
			control.sleep(1000) # POST 1 call per sec rate-limit
			result = getTraktAsJson('/sync/history', {"shows": [{"seasons": [{"number": season}], "ids": {"tvdb": tvdb}}]})
			if not result: return False
		return result['added']['episodes'] != 0
	except: log_utils.error()

def markSeasonAsNotWatched(imdb, tvdb, season):
	try:
		season = int('%01d' % int(season))
		result = getTraktAsJson('/sync/history/remove', {"shows": [{"seasons": [{"number": season}], "ids": {"imdb": imdb, "tvdb": tvdb}}]})
		if not result: return False
		if result['deleted']['episodes'] == 0 and tvdb: # sometimes trakt fails to mark because of imdb_id issues, check tvdb only as fallback if it fails
			control.sleep(1000) # POST 1 call per sec rate-limit
			result = getTraktAsJson('/sync/history/remove', {"shows": [{"seasons": [{"number": season}], "ids": {"tvdb": tvdb}}]})
			if not result: return False
		return result['deleted']['episodes'] != 0
	except: log_utils.error()

#commented out function previously here had good information in it. :)
def markEpisodeAsWatched(imdb, tvdb, season, episode):
	try:
		season, episode = int('%01d' % int(season)), int('%01d' % int(episode)) #same
		result = getTraktAsJson('/sync/history', {"shows": [{"seasons": [{"episodes": [{"number": episode}], "number": season}], "ids": {"imdb": imdb, "tvdb": tvdb}}]})
		if not result: result = False
		if result['added']['episodes'] == 0 and tvdb:
			control.sleep(1000)
			result = getTraktAsJson('/sync/history', {"shows": [{"seasons": [{"episodes": [{"number": episode}], "number": season}], "ids": {"imdb": tvdb}}]})
			if not result: result = False
			result = result['added']['episodes'] !=0
		else:
			result = result['added']['episodes'] !=0
		if getSetting('debug.level') == '1':
			log_utils.log('Trakt markEpisodeAsWatched IMDB: %s TVDB: %s Season: %s Episode: %s Result: %s' % (imdb, tvdb, season, episode, result), level=log_utils.LOGDEBUG)
		return result
	except: log_utils.error()

def markEpisodeAsNotWatched(imdb, tvdb, season, episode):
	try:
		season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
		result = getTraktAsJson('/sync/history/remove', {"shows": [{"seasons": [{"episodes": [{"number": episode}], "number": season}], "ids": {"imdb": imdb, "tvdb": tvdb}}]})
		if not result: return False
		if result['deleted']['episodes'] == 0 and tvdb:
			control.sleep(1000)
			result = getTraktAsJson('/sync/history/remove', {"shows": [{"seasons": [{"episodes": [{"number": episode}], "number": season}], "ids": {"imdb": tvdb}}]})
			if not result: return False
		return result['deleted']['episodes'] !=0
	except: log_utils.error()

def getMovieTranslation(id, lang, full=False):
	url = '/movies/%s/translations/%s' % (id, lang)
	try:
		item = cache.get(getTraktAsJson, 96, url)
		if item: item = item[0]
		else: return None
		return item if full else item.get('title')
	except: log_utils.error()

def getTVShowTranslation(id, lang, season=None, episode=None, full=False):
	if season and episode: url = '/shows/%s/seasons/%s/episodes/%s/translations/%s' % (id, season, episode, lang)
	else: url = '/shows/%s/translations/%s' % (id, lang)
	try:
		item = cache.get(getTraktAsJson, 96, url)
		if item: item = item[0]
		else: return None
		return item if full else item.get('title')
	except: log_utils.error()

def getMovieSummary(id, full=True):
	try:
		url = '/movies/%s' % id
		if full: url += '?extended=full'
		return cache.get(getTraktAsJson, 48, url)
	except: log_utils.error()

def getTVShowSummary(id, full=True):
	try:
		url = '/shows/%s' % id
		if full: url += '?extended=full'
		return cache.get(getTraktAsJson, 48, url)
	except: log_utils.error()

def getEpisodeSummary(id, season, episode, full=True):
	try:
		url = '/shows/%s/seasons/%s/episodes/%s' % (id, season, episode)
		if full: url += '&extended=full'
		return cache.get(getTraktAsJson, 48, url)
	except: log_utils.error()

def getEpisodeType(id, season, episode, full=True):
	episodeType = ''
	try:
		url = '/shows/%s/seasons/%s/episodes/%s' % (id, season, episode)
		if full: url += '?extended=full'
		episodeMeta = cache.get(getTraktAsJson, 48, url)
		episodeType = episodeMeta.get('episode_type')
	except: 
		log_utils.error()
	return episodeType

def getSeasons(id, full=True):
	try:
		url = '/shows/%s/seasons' % (id)
		if full: url += '&extended=full'
		return cache.get(getTraktAsJson, 48, url)
	except: log_utils.error()

def sort_list(sort_key, sort_direction, list_data):
	try:
		reverse = False if sort_direction == 'asc' else True
		if sort_key == 'rank': return sorted(list_data, key=lambda x: x['rank'], reverse=reverse)
		elif sort_key == 'added': return sorted(list_data, key=lambda x: x['listed_at'], reverse=reverse)
		elif sort_key == 'title': return sorted(list_data, key=lambda x: _title_key(x[x['type']].get('title')), reverse=reverse)
		elif sort_key == 'released': return sorted(list_data, key=lambda x: _released_key(x[x['type']]), reverse=reverse)
		elif sort_key == 'runtime': return sorted(list_data, key=lambda x: x[x['type']].get('runtime', 0), reverse=reverse)
		elif sort_key == 'popularity': return sorted(list_data, key=lambda x: x[x['type']].get('votes', 0), reverse=reverse)
		elif sort_key == 'percentage': return sorted(list_data, key=lambda x: x[x['type']].get('rating', 0), reverse=reverse)
		elif sort_key == 'votes': return sorted(list_data, key=lambda x: x[x['type']].get('votes', 0), reverse=reverse)
		else: return list_data
	except: log_utils.error()

def _title_key(title):
	try:
		if not title: title = ''
		articles_en = ['the', 'a', 'an']
		articles_de = ['der', 'die', 'das']
		articles = articles_en + articles_de
		match = re.match(r'^((\w+)\s+)', title.lower())
		if match and match.group(2) in articles: offset = len(match.group(1))
		else: offset = 0
		return title[offset:]
	except: return title

def _released_key(item):
	try:
		if 'released' in item: return item['released'] or '0'
		elif 'first_aired' in item: return item['first_aired'] or '0'
		else: return '0'
	except: log_utils.error()

def getMovieAliases(id):
	try:
		return cache.get(getTraktAsJson, 168, '/movies/%s/aliases' % id)
	except:
		log_utils.error()
		return []

def getTVShowAliases(id):
	try:
		return cache.get(getTraktAsJson, 168, '/shows/%s/aliases' % id)
	except:
		log_utils.error()
		return []

def getPeople(id, content_type, full=True):
	try:
		url = '/%s/%s/people' % (content_type, id)
		if full: url += '?extended=full'
		return cache.get(getTraktAsJson, 96, url)
	except: log_utils.error()

def SearchAll(title, year, full=True):
	try:
		return SearchMovie(title, year, full) , SearchTVShow(title, year, full)
	except:
		log_utils.error()
		return

def SearchMovie(title, year, fields=None, full=True):
	try:
		url = '/search/movie?query=%s' % title
		if year: url += '&year=%s' % year
		if fields: url += '&fields=%s' % fields
		if full: url += '&extended=full'
		return cache.get(getTraktAsJson, 96, url)
	except:
		log_utils.error()
		return

def SearchTVShow(title, year, fields=None, full=True):
	try:
		url = '/search/show?query=%s' % title
		if year: url += '&year=%s' % year
		if fields: url += '&fields=%s' % fields
		if full: url += '&extended=full'
		return cache.get(getTraktAsJson, 96, url)
	except:
		log_utils.error()
		return

def SearchEpisode(title, season, episode, full=True):
	try:
		url = '/search/%s/seasons/%s/episodes/%s' % (title, season, episode)
		if full: url += '&extended=full'
		return cache.get(getTraktAsJson, 96, url)
	except:
		log_utils.error()
		return

def getGenre(content, type, type_id):
	try:
		url = '/search/%s/%s?type=%s&extended=full' % (type, type_id, content)
		result = cache.get(getTraktAsJson, 168, url)
		if not result: return []
		return result[0].get(content, {}).get('genres', [])
	except:
		log_utils.error()
		return []

def IdLookup(id_type, id, type): # ("id_type" can be trakt, imdb, tmdb, tvdb) (type can be one of "movie , show , episode , person , list")
	try:
		url = '/search/%s/%s?type=%s' % (id_type, id, type)
		result = cache.get(getTraktAsJson, 168, url)
		if not result: return None
		return result[0].get(type).get('ids')
	except:
		log_utils.error()
		return None

def scrobbleMovie(imdb, tmdb, watched_percent):
	log_utils.log('Trakt Scrobble Movie Called. Received: imdb: %s tmdb: %s watched_percent: %s' % (imdb, tmdb, watched_percent), level=log_utils.LOGDEBUG)
	try:
		if not imdb.startswith('tt'): imdb = 'tt' + imdb
		success = getTrakt('/scrobble/pause', {"movie": {"ids": {"imdb": imdb}}, "progress": watched_percent})
		if success:
			log_utils.log('Trakt Scrobble Movie Success: imdb: %s s' % (imdb), level=log_utils.LOGDEBUG)
			if getSetting('trakt.scrobble.notify') == 'true': control.notification(message=32088)
			control.sleep(1000)
			sync_playbackProgress(forced=True)
			control.trigger_widget_refresh()
		else: control.notification(message=32130)
	except: log_utils.error()

def scrobbleEpisode(imdb, tmdb, tvdb, season, episode, watched_percent):
	#log_utils.log('Trakt Scrobble Episode Called. Received: imdb: %s tmdb: %s season: %s episode: %s watched_percent: %s' % (imdb, tmdb, season, episode, watched_percent), level=log_utils.LOGDEBUG)
	try:
		season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
		success = getTrakt('/scrobble/pause', {"show": {"ids": {"tvdb": tvdb}}, "episode": {"season": season, "number": episode}, "progress": watched_percent})
		if success:
			log_utils.log('Trakt Scrobble Episode Success: imdb: %s s' % (imdb), level=log_utils.LOGDEBUG)
			if getSetting('trakt.scrobble.notify') == 'true': control.notification(message=32088)
			control.sleep(1000)
			sync_playbackProgress(forced=True)
			control.trigger_widget_refresh()
		else: control.notification(message=32130)
	except: log_utils.error()

def scrobbleReset(imdb, tmdb=None, tvdb=None, season=None, episode=None, refresh=True, widgetRefresh=False):
	if not getTraktCredentialsInfo(): return
	if not control.player.isPlaying(): control.busy()
	success = False
	try:
		content_type = 'movie' if not episode else 'episode'
		resume_info = traktsync.fetch_bookmarks(imdb, tmdb, tvdb, season, episode, ret_type='resume_info')
		if resume_info == '0': return control.hide() # returns string "0" if no data in db 
		headers['Authorization'] = 'Bearer %s' % trakt_token
		if headers['trakt-api-key'] == '': headers['trakt-api-key']=traktClientID()
		success = session.delete('https://api.trakt.tv/sync/playback/%s' % resume_info[1], headers=headers).status_code == 204
		if content_type == 'movie':
			items = [{'type': 'movie', 'movie': {'ids': {'imdb': imdb}}}]
			label_string = resume_info[0]
		else:
			items = [{'type': 'episode', 'episode': {'season': season, 'number': episode}, 'show': {'ids': {'imdb': imdb, 'tvdb': tvdb}}}]
			label_string = resume_info[0] + ' - ' + 'S%02dE%02d' % (int(season), int(episode))
		control.hide()
		if success:
			timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
			items[0].update({'paused_at': timestamp})
			traktsync.delete_bookmark(items)
			if refresh: control.refresh()
			if widgetRefresh: control.trigger_widget_refresh() # skinshortcuts handles the widget_refresh when plyback ends, but not a manual clear from Trakt Manager
			if getSetting('trakt.scrobble.notify') == 'true': control.notification(title=32315, message='Successfuly Removed playback progress:  [COLOR %s]%s[/COLOR]' % (highlight_color, label_string))
			log_utils.log('Successfuly Removed Trakt Playback Progress:  %s  with resume_id=%s' % (label_string, str(resume_info[1])), __name__, level=log_utils.LOGDEBUG)
		else:
			#if getSetting('trakt.scrobble.notify') == 'true': control.notification(title=32315, message='Failed to Remove playback progress:  [COLOR %s]%s[/COLOR]' % (highlight_color, label_string))
			log_utils.log('Failed to Remove Trakt Playback Progress:  %s  with resume_id=%s' % (label_string, str(resume_info[1])), __name__, level=log_utils.LOGDEBUG)
	except: log_utils.error()

def scrobbleResetItems(imdb_ids, tvdb_dicts=None, refresh=True, widgetRefresh=False):
	if control.player.isPlaying(): control.busy()
	success = False
	try:
		content_type = 'movie' if not tvdb_dicts else 'episode'
		if content_type == 'movie':
			total_items = len(imdb_ids)
			resume_info = traktsync.fetch_bookmarks(imdb='', ret_all=True, ret_type='movies')
			for imdb in imdb_ids:
				try:
					resume_info_index = [resume_info.index(i) for i in resume_info if i['imdb'] == imdb][0]
					resume_dict = resume_info[resume_info_index]
					resume_id = resume_dict['resume_id']
					headers['Authorization'] = 'Bearer %s' % trakt_token
					success = session.delete('https://api.trakt.tv/sync/playback/%s' % resume_id, headers=headers).status_code == 204
					if not success: raise Exception()
					items = [{'type': 'movie', 'movie': {'ids': {'imdb': imdb}}}]
					timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
					items[0].update({'paused_at': timestamp})
					traktsync.delete_bookmark(items)
					log_utils.log('Successfuly Removed Trakt Playback Progress: movie title=%s  with resume_id=%s' % (resume_dict['title'], str(resume_id)), __name__, level=log_utils.LOGDEBUG)
					control.sleep(1000)
				except: log_utils.log('Failed to Remove Trakt Playback Progress: movie title=%s  with resume_id=%s' % (resume_dict['title'], str(resume_id)), __name__, level=log_utils.LOGDEBUG)
		else:
			total_items = len(tvdb_dicts)
			resume_info = traktsync.fetch_bookmarks(imdb='', ret_all=True, ret_type='episodes')
			for dict in tvdb_dicts:
				try:
					imdb, tvdb = dict.get('imdb'), dict.get('tvdb')
					season, episode = dict.get('season'), dict.get('episode')
					resume_info_index = [resume_info.index(i) for i in resume_info if i['tvdb'] == tvdb and i['season'] == int(season) and i['episode'] == int(episode)][0]
					resume_dict = resume_info[resume_info_index]
					label_string = resume_dict['tvshowtitle'] + ' - ' + 'S%02dE%02d' % (int(season), int(episode))
					resume_id = resume_dict['resume_id']
					headers['Authorization'] = 'Bearer %s' % trakt_token
					success = session.delete('https://api.trakt.tv/sync/playback/%s' % resume_id, headers=headers).status_code == 204
					if not success: raise Exception()
					items = [{'type': 'episode', 'episode': {'season': season, 'number': episode}, 'show': {'ids': {'imdb': imdb, 'tvdb': tvdb}}}]
					timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
					items[0].update({'paused_at': timestamp})
					traktsync.delete_bookmark(items)
					log_utils.log('Successfuly Removed Trakt Playback Progress:  tvshowtitle=%s  with resume_id=%s' % (label_string, str(resume_id)), __name__, level=log_utils.LOGDEBUG)
					control.sleep(1000)
				except: log_utils.log('Failed to Remove Trakt Playback Progress:  tvshowtitle=%s  with resume_id=%s' % (label_string, str(resume_id)), __name__, level=log_utils.LOGDEBUG)
		control.hide()
		if success:
			if refresh: control.refresh()
			if widgetRefresh: control.trigger_widget_refresh() # skinshortcuts handles the widget_refresh when plyback ends, but not a manual clear from Trakt Manager
			control.notification(title='Trakt Playback Progress Manager', message='Successfuly Removed %s Item%s' % (total_items, 's' if total_items >1 else ''))
			return True
		else: return False
	except:
		log_utils.error()
		control.hide()
		return False



#############    SERVICE SYNC    ######################
def trakt_service_sync():
	while not control.monitor.abortRequested():
		control.sleep(5000) # wait 5sec in case of device wake from sleep
		try:
			internets = control.condVisibility('System.InternetState') #added for some systems have removed Internet State apparently.
			if internets == False:
				internets = control.condVisibility('System.HasNetwork')
		except:
			internets = None
			log_utils.error()
		if internets and getTraktCredentialsInfo(): # run service in case user auth's trakt later
			activities = getTraktAsJson('/sync/last_activities', silent=True)
			if getSetting('bookmarks') == 'true' and getSetting('resume.source') == '1':
				sync_playbackProgress(activities)
			sync_watchedProgress(activities)
			if getSetting('indicators.alt') == '1':
				sync_watched(activities) # writes to traktsync.db as of 1-19-2022
			sync_user_lists(activities)
			sync_liked_lists(activities)
			sync_hidden_progress(activities)
			sync_collection(activities)
			sync_watch_list(activities)
			sync_popular_lists()
			sync_trending_lists()
		if control.monitor.waitForAbort(60*service_syncInterval): break

def force_traktSync():
	if not control.yesnoDialog(getLS(32056), '', ''): return
	control.busy()

	# wipe all tables and start fresh
	clr_traktSync = {'bookmarks': True, 'hiddenProgress': True, 'liked_lists': True, 'movies_collection': True, 'movies_watchlist': True,
							'public_lists': True, 'shows_collection': True, 'shows_watchlist': True, 'user_lists': True, 'watched': True}
	traktsync.delete_tables(clr_traktSync)

	sync_playbackProgress(forced=True)
	sync_hidden_progress(forced=True)
	sync_liked_lists(forced=True)
	sync_collection(forced=True)
	sync_watch_list(forced=True)
	sync_popular_lists(forced=True)
	sync_trending_lists(forced=True)
	sync_user_lists(forced=True)
	sync_watched(forced=True) # writes to traktsync.db as of 1-19-2022
	sync_watchedProgress(forced=True) # Trakt progress sync
	control.hide()
	control.notification(message='Forced Trakt Sync Complete')

def sync_playbackProgress(activities=None, forced=False):
	#log_utils.log('Trakt Sync Playback Called Forced: %s' % (str(forced)), level=log_utils.LOGDEBUG)
	try:
		link = '/sync/playback/?extended=full'
		if forced:
			items = getTraktAsJson(link, silent=True)
			if items: traktsync.insert_bookmarks(items)
		else:
			db_last_paused = traktsync.last_sync('last_paused_at')
			activity = getPausedActivity(activities)
			#log_utils.log('Trakt Sync Playback db_last_paused: %s  activity: %s difference: %s' % (db_last_paused, activity,(activity - db_last_paused)),log_utils.LOGDEBUG)
			if activity - db_last_paused >= 120: # do not sync unless 2 min difference or more
				items = getTraktAsJson(link, silent=True)
				if items: traktsync.insert_bookmarks(items)
	except: log_utils.error()

def sync_watchedProgress(activities=None, forced=False):
	try:
		from resources.lib.menus import episodes
		trakt_user = getSetting('trakt.user.name').strip()
		lang = control.apiLanguage()['tmdb']
		direct = getSetting('trakt.directProgress.scrape') == 'true'
		url = 'https://api.trakt.tv/users/me/watched/shows'
		progressActivity = getProgressActivity(activities)
		local_listCache = cache.timeout(episodes.Episodes().trakt_progress_list, url, trakt_user, lang, direct)
		if forced or (progressActivity > local_listCache):
			cache.get(episodes.Episodes().trakt_progress_list, 0, url, trakt_user, lang, direct)
			if forced: log_utils.log('Forced - Trakt Progress List Sync Complete', __name__, log_utils.LOGDEBUG)
			else:
				log_utils.log('Trakt Progress List Sync Update...(local db latest "list_cached_at" = %s, trakt api latest "progress_activity" = %s)' % \
									(str(local_listCache), str(progressActivity)), __name__, log_utils.LOGDEBUG)
	except: log_utils.error()

def sync_watched(activities=None, forced=False): # writes to traktsync.db as of 1-19-2022
	try:
		if forced:
			cachesyncMovies()
			#log_utils.log('Forced - Trakt Watched Movie Sync Complete', __name__, log_utils.LOGDEBUG)
			cachesyncTVShows()
			control.sleep(5000)
			service_syncSeasons() # syncs all watched shows season indicators and counts
			#log_utils.log('Forced - Trakt Watched Shows Sync Complete', __name__, log_utils.LOGDEBUG)
			traktsync.insert_syncSeasons_at()
		else:
			moviesWatchedActivity = getMoviesWatchedActivity(activities)
			db_movies_last_watched = timeoutsyncMovies()
			if moviesWatchedActivity - db_movies_last_watched >= 30: # do not sync unless 30secs more to allow for variation between trakt post and local db update.
				log_utils.log('Trakt Watched Movie Sync Update...(local db latest "watched_at" = %s, trakt api latest "watched_at" = %s)' % \
								(str(db_movies_last_watched), str(moviesWatchedActivity)), __name__, log_utils.LOGDEBUG)
				cachesyncMovies()
			episodesWatchedActivity = getEpisodesWatchedActivity(activities)
			db_last_syncTVShows = timeoutsyncTVShows()
			db_last_syncSeasons = traktsync.last_sync('last_syncSeasons_at')
			if any(episodesWatchedActivity > value for value in (db_last_syncTVShows, db_last_syncSeasons)):
				log_utils.log('Trakt Watched Shows Sync Update...(local db latest "watched_at" = %s, trakt api latest "watched_at" = %s)' % \
								(str(min(db_last_syncTVShows, db_last_syncSeasons)), str(episodesWatchedActivity)), __name__, log_utils.LOGDEBUG)
				cachesyncTVShows()
				control.sleep(5000)
				service_syncSeasons() # syncs all watched shows season indicators and counts
				traktsync.insert_syncSeasons_at()
	except: log_utils.error()

def sync_user_lists(activities=None, forced=False):
	try:
		link = '/users/me/lists'
		list_link = '/users/me/lists/%s/items/%s'
		if forced:
			items = getTraktAsJson(link, silent=True)
			if not items: return
			for i in items:
				i['content_type'] = ''
				trakt_id = i['ids']['trakt']
				list_items = getTraktAsJson(list_link % (trakt_id, 'movies'), silent=True)
				if not list_items or list_items == '[]': pass
				else: i['content_type'] = 'movies'
				list_items = getTraktAsJson(list_link % (trakt_id, 'shows'), silent=True)
				if not list_items or list_items == '[]': pass
				else: i['content_type'] = 'mixed' if i['content_type'] == 'movies' else 'shows'
				control.sleep(200)
			traktsync.insert_user_lists(items)
			log_utils.log('Forced - Trakt User Lists Sync Complete', __name__, log_utils.LOGDEBUG)
		else:
			db_last_lists_updatedat = traktsync.last_sync('last_lists_updatedat')
			user_listActivity = getUserListActivity(activities)
			if user_listActivity > db_last_lists_updatedat:
				log_utils.log('Trakt User Lists Sync Update...(local db latest "lists_updatedat" = %s, trakt api latest "lists_updatedat" = %s)' % \
									(str(db_last_lists_updatedat), str(user_listActivity)), __name__, log_utils.LOGDEBUG)
				clr_traktSync = {'bookmarks': False, 'hiddenProgress': False, 'liked_lists': False, 'movies_collection': False, 'movies_watchlist': False,
							'public_lists': False, 'shows_collection': False, 'shows_watchlist': False, 'user_lists': True, 'watched': False}
				traktsync.delete_tables(clr_traktSync)
				items = getTraktAsJson(link, silent=True)
				if not items: return
				for i in items:
					i['content_type'] = ''
					trakt_id = i['ids']['trakt']
					list_items = getTraktAsJson(list_link % (trakt_id, 'movies'), silent=True)
					if not list_items or list_items == '[]': pass
					else: i['content_type'] = 'movies'
					list_items = getTraktAsJson(list_link % (trakt_id, 'shows'), silent=True)
					if not list_items or list_items == '[]': pass
					else: i['content_type'] = 'mixed' if i['content_type'] == 'movies' else 'shows'
					control.sleep(200)
				traktsync.insert_user_lists(items)
	except: log_utils.error()

def sync_liked_lists(activities=None, forced=False):
	try:
		link = '/users/likes/lists?limit=1000000'
		list_link = '/users/%s/lists/%s/items/%s'
		db_last_liked = traktsync.last_sync('last_liked_at')
		listActivity = getListActivity(activities)
		if (listActivity > db_last_liked) or forced:
			if not forced: 
					log_utils.log('Trakt Liked Lists Sync Update...(local db latest "liked_at" = %s, trakt api latest "liked_at" = %s)' % \
								(str(db_last_liked), str(listActivity)), __name__, log_utils.LOGDEBUG)
			clr_traktSync = {'bookmarks': False, 'hiddenProgress': False, 'liked_lists': True, 'movies_collection': False, 'movies_watchlist': False,
							'public_lists': False, 'shows_collection': False, 'shows_watchlist': False, 'user_lists': False, 'watched': False}
			traktsync.delete_tables(clr_traktSync)
			items = getTraktAsJson(link, silent=True)
			if not items: return
			thrd_items = []
			def items_list(i):
				list_item = i.get('list', {})
				if any(list_item.get('privacy', '') == value for value in ('private', 'friends')): return
				if list_item.get('user',{}).get('private') is True:
					#log_utils.log('(%s) has marked their list private in Trakt(Liked Lists) and is now causing you errors. Skipping this list' % list_item.get('user',{}).get('username'))
					return
				i['list']['content_type'] = ''
				list_owner_slug = list_item.get('user', {}).get('ids', {}).get('slug', '')
				trakt_id = list_item.get('ids', {}).get('trakt', '')
				list_items = getTraktAsJson(list_link % (list_owner_slug, trakt_id, 'movies'), silent=True)
				if not list_items or list_items == '[]': pass
				else: i['list']['content_type'] = 'movies'
				list_items = getTraktAsJson(list_link % (list_owner_slug, trakt_id, 'shows'), silent=True)
				if not list_items or list_items == '[]': pass
				else: i['list']['content_type'] = 'mixed' if i['list']['content_type'] == 'movies' else 'shows'
				thrd_items.append(i)
			threads = []
			for i in items:
				threads.append(Thread(target=items_list, args=(i,)))
			[i.start() for i in threads]
			[i.join() for i in threads]
			traktsync.insert_liked_lists(thrd_items)
			if forced: log_utils.log('Forced - Trakt Liked Lists Sync Complete', __name__, log_utils.LOGDEBUG)
	except: log_utils.error()

def sync_hidden_progress(activities=None, forced=False):
	try:
		link = '/users/hidden/progress_watched?limit=2000&type=show'
		if forced:
			items = getTraktAsJson(link, silent=True)
			traktsync.insert_hidden_progress(items)
			log_utils.log('Forced - Trakt Hidden Progress Sync Complete', __name__, log_utils.LOGDEBUG)
		else:
			db_last_hidden = traktsync.last_sync('last_hiddenProgress_at')
			hiddenActivity = getHiddenActivity(activities)
			if hiddenActivity > db_last_hidden:
				log_utils.log('Trakt Hidden Progress Sync Update...(local db latest "hidden_at" = %s, trakt api latest "hidden_at" = %s)' % \
									(str(db_last_hidden), str(hiddenActivity)), __name__, log_utils.LOGDEBUG)
				items = getTraktAsJson(link, silent=True)
				traktsync.insert_hidden_progress(items)
	except: log_utils.error()

def sync_collection(activities=None, forced=False):
	try:
		link = '/users/me/collection/%s?extended=full'
		if forced:
			items = getTraktAsJson(link % 'movies', silent=True)
			traktsync.insert_collection(items, 'movies_collection')
			items = getTraktAsJson(link % 'shows', silent=True)
			traktsync.insert_collection(items, 'shows_collection')
			#log_utils.log('Forced - Trakt Collection Sync Complete', __name__, log_utils.LOGDEBUG)
		else:
			db_last_collected = traktsync.last_sync('last_collected_at')
			collectedActivity = getCollectedActivity(activities)
			if collectedActivity > db_last_collected:
				log_utils.log('Trakt Collection Sync Update...(local db latest "collected_at" = %s, trakt api latest "collected_at" = %s)' % \
									(str(db_last_collected), str(collectedActivity)), __name__, log_utils.LOGDEBUG)
				clr_traktSync = {'bookmarks': False, 'hiddenProgress': False, 'liked_lists': False, 'movies_collection': True, 'movies_watchlist': False,
							'public_lists': False, 'shows_collection': True, 'shows_watchlist': False, 'user_lists': False, 'watched': False}
				traktsync.delete_tables(clr_traktSync)
				# indicators = cachesyncMovies() # could maybe check watched status here to satisfy sort method
				items = getTraktAsJson(link % 'movies', silent=True)
				traktsync.insert_collection(items, 'movies_collection')
				# indicators = cachesyncTVShows() # could maybe check watched status here to satisfy sort method
				items = getTraktAsJson(link % 'shows', silent=True)
				traktsync.insert_collection(items, 'shows_collection')
	except: log_utils.error()

def sync_watch_list(activities=None, forced=False):
	try:
		link = '/users/me/watchlist/%s?extended=full'
		if forced:
			items = getTraktAsJson(link % 'movies', silent=True)
			traktsync.insert_watch_list(items, 'movies_watchlist')
			items = getTraktAsJson(link % 'shows', silent=True)
			traktsync.insert_watch_list(items, 'shows_watchlist')
			#log_utils.log('Forced - Trakt Watch List Sync Complete', __name__, log_utils.LOGDEBUG)
		else:
			db_last_watchList = traktsync.last_sync('last_watchlisted_at')
			watchListActivity = getWatchListedActivity(activities)
			if watchListActivity - db_last_watchList >= 60: # do not sync unless 1 min difference or more
				log_utils.log('Trakt Watch List Sync Update...(local db latest "watchlist_at" = %s, trakt api latest "watchlisted_at" = %s)' % \
									(str(db_last_watchList), str(watchListActivity)), __name__, log_utils.LOGINFO)
				clr_traktSync = {'bookmarks': False, 'hiddenProgress': False, 'liked_lists': False, 'movies_collection': False, 'movies_watchlist': True,
							'public_lists': False, 'shows_collection': False, 'shows_watchlist': True, 'user_lists': False, 'watched': False}
				traktsync.delete_tables(clr_traktSync)
				items = getTraktAsJson(link % 'movies', silent=True)
				traktsync.insert_watch_list(items, 'movies_watchlist')
				items = getTraktAsJson(link % 'shows', silent=True)
				traktsync.insert_watch_list(items, 'shows_watchlist')
	except: log_utils.error()

def sync_popular_lists(forced=False):
	try:
		from datetime import timedelta
		link = '/lists/popular?limit=300'
		list_link = '/users/%s/lists/%s/items/movie,show'
		official_link = '/lists/%s/items/movie,show'
		db_last_popularList = traktsync.last_sync('last_popularlist_at')
		cache_expiry = (datetime.utcnow() - timedelta(hours=168)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
		cache_expiry = int(cleandate.iso_2_utc(cache_expiry))
		if (cache_expiry > db_last_popularList) or forced:
			if not forced: log_utils.log('Trakt Popular Lists Sync Update...(local db latest "popularlist_at" = %s, cache expiry = %s)' % \
								(str(db_last_popularList), str(cache_expiry)), __name__, log_utils.LOGDEBUG)
			items = getTraktAsJson(link, silent=True)
			if not items: return
			thrd_items = []
			def items_list(i):
				list_item = i.get('list', {})
				if any(list_item.get('privacy', '') == value for value in ('private', 'friends')): return
				if list_item.get('user',{}).get('private') is True:
					log_utils.log('(%s) has marked their list private in Trakt(Popular Lists) and would be causing you errors but we caught it and we are skipping their list.' % list_item.get('user',{}).get('username'))
					return
				trakt_id = list_item.get('ids', {}).get('trakt', '')
				exists = traktsync.fetch_public_list(trakt_id)
				if exists:
					local = int(cleandate.iso_2_utc(exists.get('updated_at', '')))
					remote = int(cleandate.iso_2_utc(list_item.get('updated_at', '')))
					if remote > local: pass
					else: return
				i['list']['content_type'] = ''
				list_owner_slug = list_item.get('user', {}).get('ids', {}).get('slug', '')
				if not list_owner_slug: list_owner_slug = list_item.get('user',{}).get('username')
				if list_item.get('type') == 'official': list_items = getTraktAsJson(official_link % trakt_id, silent=True)
				else: list_items = getTraktAsJson(list_link % (list_owner_slug, trakt_id), silent=True)
				if not list_items: return
				movie_items = [x for x in list_items if x.get('type', '') == 'movie']
				if len(movie_items) > 0: i['list']['content_type'] = 'movies'
				shows_items = [x for x in list_items if x.get('type', '') == 'show']
				if len(shows_items) > 0:
					i['list']['content_type'] = 'mixed' if i['list']['content_type'] == 'movies' else 'shows'
				thrd_items.append(i)
			threads = []
			for i in items:
				threads.append(Thread(target=items_list, args=(i,)))
			[i.start() for i in threads]
			[i.join() for i in threads]
			traktsync.insert_public_lists(thrd_items, service_type='last_popularlist_at', new_sync=False)
			if forced: log_utils.log('Forced - Trakt Popular Lists Sync Complete', __name__, log_utils.LOGDEBUG)
	except: log_utils.error()

def sync_trending_lists(forced=False):
	try:
		from datetime import timedelta
		link = '/lists/trending?limit=300'
		list_link = '/users/%s/lists/%s/items/movie,show'
		official_link = '/lists/%s/items/movie,show'

		db_last_trendingList = traktsync.last_sync('last_trendinglist_at')
		cache_expiry = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
		cache_expiry = int(cleandate.iso_2_utc(cache_expiry))
		if (cache_expiry > db_last_trendingList) or forced:
			if not forced: log_utils.log('Trakt Trending Lists Sync Update...(local db latest "trendinglist_at" = %s, cache expiry = %s)' % \
								(str(db_last_trendingList), str(cache_expiry)), __name__, log_utils.LOGDEBUG)
			items = getTraktAsJson(link, silent=True)
			if not items: return
			thrd_items = []
			def items_list(i):
				list_item = i.get('list', {})
				if any(list_item.get('privacy', '') == value for value in ('private', 'friends')): return
				if list_item.get('user',{}).get('private') is True:
					log_utils.log('(%s) has marked their list private in Trakt(Trending Lists) and is now causing you errors. Skipping this list' % list_item.get('user',{}).get('username'))
					return
				trakt_id = list_item.get('ids', {}).get('trakt', '')
				exists = traktsync.fetch_public_list(trakt_id)
				if exists:
					local = int(cleandate.iso_2_utc(exists.get('updated_at', '')))
					remote = int(cleandate.iso_2_utc(list_item.get('updated_at', '')))
					if remote > local: pass
					else: return
				i['list']['content_type'] = ''
				list_owner_slug = list_item.get('user', {}).get('ids', {}).get('slug', '')
				if not list_owner_slug: list_owner_slug = list_item.get('user', {}).get('username')
				if list_item.get('type') == 'official': list_items = getTraktAsJson(official_link % trakt_id, silent=True)
				else: list_items = getTraktAsJson(list_link % (list_owner_slug, trakt_id), silent=True)
				if not list_items: return
				movie_items = [x for x in list_items if x.get('type', '') == 'movie']
				if len(movie_items) != 0: i['list']['content_type'] = 'movies'
				shows_items = [x for x in list_items if x.get('type', '') == 'show']
				if len(shows_items) != 0:
					i['list']['content_type'] = 'mixed' if i['list']['content_type'] == 'movies' else 'shows'
				thrd_items.append(i)
			threads = []
			for i in items:
				threads.append(Thread(target=items_list, args=(i,)))
			[i.start() for i in threads]
			[i.join() for i in threads]
			traktsync.insert_public_lists(thrd_items, service_type='last_trendinglist_at', new_sync=False)
			if forced: log_utils.log('Forced - Trakt Trending Lists Sync Complete', __name__, log_utils.LOGDEBUG)
	except: log_utils.error()

def traktClientID():
	traktId = '87e3f055fc4d8fcfd96e61a47463327ca877c51e8597b448e132611c5a677b13'
	if (getSetting('trakt.clientid') != '' and getSetting('trakt.clientid') is not None) and getSetting('traktuserkey.customenabled') == 'true':
		traktId = getSetting('trakt.clientid')
	return traktId
def traktClientSecret():
	traktSecret = '4a1957a52d5feb98fafde53193e51f692fa9bdcd0cc13cf44a5e39975539edf0'
	if (getSetting('trakt.clientsecret') != '' and getSetting('trakt.clientsecret') is not None) and getSetting('traktuserkey.customenabled') == 'true':
		traktSecret = getSetting('trakt.clientsecret')
	return traktSecret