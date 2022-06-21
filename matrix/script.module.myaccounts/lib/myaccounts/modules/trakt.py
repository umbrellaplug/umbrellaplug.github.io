# -*- coding: utf-8 -*-
"""
	My Accounts
"""

import requests
import time
from myaccounts.modules import control
from myaccounts.modules import log_utils

trakt_icon = control.joinPath(control.artPath(), 'trakt.png')

class Trakt():
	def __init__(self):
		self.api_endpoint = 'https://api-v2launch.trakt.tv/%s'
		self.client_id = '9242c1fb5fe5b5fd5b5fbe14fef2f7b13312e4555f1e4b53b843eca82a9a1635'
		self.client_secret = '79787b05d31b747ad640ce761bc31a3782967a2393c5e98f034f48dce11dfb0d'
		self.expires_at = control.setting('trakt.expires')
		self.token = control.setting('trakt.token')

	def call(self, path, data=None, with_auth=True, method=None, return_str=False, suppress_error_notification=False):
		try:
			def error_notification(line1, error):
				if suppress_error_notification: return
				return control.notification(title='default', message='%s: %s' % (line1, error), icon=trakt_icon)
			def send_query():
				resp = None
				if with_auth:
					try:
						if time.time() > self.expires_at: self.refresh_token()
					except: pass
					headers['Authorization'] = 'Bearer ' + self.token
				try:
					if data is not None: resp = requests.post(self.api_endpoint % path, json=data, headers=headers, timeout=timeout)
					else: resp = requests.get(self.api_endpoint % path, headers=headers, timeout=timeout)
				except requests.exceptions.RequestException as e:
					error_notification('Trakt Error', str(e))
				except Exception as e:
					error_notification('', str(e))
				return resp
			timeout = 15.0
			headers = {'Content-Type': 'application/json', 'trakt-api-version': '2', 'trakt-api-key': self.client_id}
			response = send_query()
			response.encoding = 'utf-8'
			if return_str: return response
			try: result = response.json()
			except: result = None
			return result
		except:
			log_utils.error()

	def get_device_code(self):
		data = {'client_id': self.client_id}
		return self.call("oauth/device/code", data=data, with_auth=False)

	def get_device_token(self, device_codes):
		try:
			data = {"code": device_codes["device_code"],
					"client_id": self.client_id,
					"client_secret": self.client_secret}
			start = time.time()
			expires_in = device_codes['expires_in']
			verification_url = control.lang(32513) % str(device_codes['verification_url'])
			user_code = control.lang(32514) % str(device_codes['user_code'])
			control.progressDialog.create(control.lang(32073), control.progress_line % (verification_url, user_code, ''))
			try:
				time_passed = 0
				while not control.progressDialog.iscanceled() and time_passed < expires_in:
					try:
						response = self.call("oauth/device/token", data=data, with_auth=False, suppress_error_notification=True)
					except requests.HTTPError as e:
						log_utils.log('Request Error: %s' % str(e), __name__, log_utils.LOGDEBUG)
						if e.response.status_code != 400: raise e
						progress = int(100 * time_passed / expires_in)
						control.progressDialog.update(progress)
						control.sleep(max(device_codes['interval'], 1)*1000)
					else:
						if not response: continue
						else: return response
					time_passed = time.time() - start
			finally:
				control.progressDialog.close()
			return None
		except:
			log_utils.error()

	def refresh_token(self):
		traktToken = None
		traktRefresh = None
		traktExpires = None
		data = {
			"client_id": self.client_id,
			"client_secret": self.client_secret,
			"redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
			"grant_type": "refresh_token",
			"refresh_token": control.setting('trakt.refresh')
		}

		response = self.call("oauth/token", data=data, with_auth=False, return_str=True)
		try: code = str(response[1])
		except: code = ''

		if code.startswith('5') or (response and isinstance(response, str) and '<html' in response) or not response: # covers Maintenance html responses ["Bad Gateway", "We're sorry, but something went wrong (500)"])
			log_utils.log('Temporary Trakt Server Problems', level=log_utils.LOGNOTICE)
			control.notification(title=32315, message=33676)
			return False
		elif response and code in ['423']:
			log_utils.log('Locked User Account - Contact Trakt Support: %s' % str(response[0]), level=log_utils.LOGWARNING)
			control.notification(title=32315, message=33675)
			return False

		if response and code not in ['401', '405']:
			try:
				response = response.json()
			except:
				log_utils.error()
				return False
			if 'error' in response and response['error'] == 'invalid_grant':
				log_utils.log('Please Re-Authorize your Trakt Account: %s' % response['error'], __name__, level=log_utils.LOGWARNING)
				control.notification(title=32315, message=33677)
				return False

			traktToken = response["access_token"]
			traktRefresh = response["refresh_token"]
			traktExpires = time.time() + 7776000
			control.setSetting('trakt.token', traktToken)
			control.setSetting('trakt.refresh', traktRefresh)
			control.setSetting('trakt.expires', str(traktExpires))
		self.token = traktToken

	def auth(self):
		try:
			code = self.get_device_code()
			token = self.get_device_token(code)
			if token:
				expires_at = time.time() + 7776000
				control.setSetting('trakt.expires', str(expires_at))
				control.setSetting('trakt.token', token["access_token"])
				control.setSetting('trakt.refresh', token["refresh_token"])
				self.expires_at = expires_at
				self.token = token["access_token"]
				control.sleep(1000)
				try:
					user = self.call("users/me", with_auth=True)
					control.setSetting('trakt.username', str(user['username']))
				except: pass
				control.notification(message=40074, icon=trakt_icon)
				return True
			control.notification(message=40075, icon=trakt_icon)
			return False
		except:
			log_utils.error()

	def revoke(self):
		data = {"token": control.setting('trakt.token')}
		try: self.call("oauth/revoke", data=data, with_auth=False)
		except: pass
		control.setSetting('trakt.username', '')
		control.setSetting('trakt.expires', '')
		control.setSetting('trakt.token', '')
		control.setSetting('trakt.refresh', '')
		control.dialog.ok(control.lang(32315), control.lang(32314))

	def account_info(self):
		response = self.call("users/me", with_auth=True)
		return response

	def extended_account_info(self):
		account_info = self.call("users/settings", with_auth=True)
		stats = self.call("users/%s/stats" % account_info['user']['ids']['slug'], with_auth=True)
		return account_info, stats

	def account_info_to_dialog(self):
		from datetime import datetime, timedelta
		try:
			account_info, stats = self.extended_account_info()
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
			movies_watched_minutes = control.lang(40071) % (movies_watched_minutes[0], movies_watched_minutes[1].split(':')[0], movies_watched_minutes[1].split(':')[1])
			shows_collected = stats['shows']['collected']
			shows_watched = stats['shows']['watched']
			episodes_watched = stats['episodes']['watched']
			episode_minutes = stats['episodes']['minutes']
			if episode_minutes == 0: episodes_watched_minutes = ['0 days', '0:00:00']
			elif episode_minutes < 1440: episodes_watched_minutes = ['0 days', "{:0>8}".format(str(timedelta(minutes=episode_minutes)))]
			else: episodes_watched_minutes = ("{:0>8}".format(str(timedelta(minutes=episode_minutes)))).split(', ')
			episodes_watched_minutes = control.lang(40071) % (episodes_watched_minutes[0], episodes_watched_minutes[1].split(':')[0], episodes_watched_minutes[1].split(':')[1])
			heading = control.lang(32315)
			items = []
			items += [control.lang(40036) % username]
			items += [control.lang(40063) % timezone]
			items += [control.lang(40064) % joined]
			items += [control.lang(40065) % private]
			items += [control.lang(40066) % vip]
			items += [control.lang(40067) % str(total_given_ratings)]
			items += [control.lang(40068) % (movies_collected, movies_watched, movies_watched_minutes)]
			items += [control.lang(40069) % (shows_collected, shows_watched)]
			items += [control.lang(40070) % (episodes_watched, episodes_watched_minutes)]
			return control.selectDialog(items, heading)
		except:
			log_utils.error()
			return