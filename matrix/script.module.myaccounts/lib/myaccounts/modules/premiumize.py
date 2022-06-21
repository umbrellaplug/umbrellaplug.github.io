# -*- coding: utf-8 -*-
"""
	My Accounts
"""

import requests
from myaccounts.modules import control
from myaccounts.modules import log_utils

CLIENT_ID = '776741998' # used to auth
BaseUrl = 'https://www.premiumize.me/api'
account_info_url = '%s/account/info' % BaseUrl
pm_icon = control.joinPath(control.artPath(), 'premiumize.png')

class Premiumize:
	name = "Premiumize.me"

	def __init__(self):
		self.token = control.setting('premiumize.token')
		self.headers = {'User-Agent': 'My Accounts for Kodi', 'Authorization': 'Bearer %s' % self.token}
		self.server_notifications = False

	def _get(self, url):
		try:
			response = requests.get(url, headers=self.headers, timeout=15).json()
			if 'status' in response:
				if response.get('status') == 'success':
					return response
				if response.get('status') == 'error' and self.server_notifications:
					control.notification(title='default', message=response.get('message'), icon='default')
		except:
			log_utils.error()
		return response

	def _post(self, url, data={}):
		try:
			response = requests.post(url, data, headers=self.headers, timeout=15).json()
			if 'status' in response:
				if response.get('status') == 'success':
					return response
				if response.get('status') == 'error' and self.server_notifications:
					control.notification(title='default', message=response.get('message'), icon='default')
		except:
			log_utils.error()
		return response

	def auth(self):
		data = {'client_id': CLIENT_ID, 'response_type': 'device_code'}
		token = requests.post('https://www.premiumize.me/token', data=data, timeout=15).json()
		expiry = float(token['expires_in'])
		token_ttl = token['expires_in']
		poll_again = True
		success = False
		progressDialog = control.progressDialog
		progressDialog.create(control.lang(40054), control.progress_line % (control.lang(32513) % token['verification_uri'], control.lang(32514) % token['user_code'], ''))
		progressDialog.update(0)
		while poll_again and not token_ttl <= 0 and not progressDialog.iscanceled():
			poll_again, success = self.poll_token(token['device_code'])
			progress_percent = 100 - int((float((expiry - token_ttl) / expiry) * 100))
			progressDialog.update(progress_percent)
			control.sleep(token['interval'] * 1000)
			token_ttl -= int(token['interval'])
		progressDialog.close()
		if success:
			control.notification(title=40057, message=40081, icon=pm_icon)

	def poll_token(self, device_code):
		data = {'client_id': CLIENT_ID, 'code': device_code, 'grant_type': 'device_code'}
		token = requests.post('https://www.premiumize.me/token', data=data, timeout=15).json()
		if 'error' in token:
			if token['error'] == "access_denied":
				control.okDialog(title='default', message=control.lang(40020))
				return False, False
			return True, False
		self.token = token['access_token']
		self.headers = {'User-Agent': 'My Accounts for Kodi', 'Authorization': 'Bearer %s' % self.token}
		control.sleep(500)
		account_info = self.account_info()
		control.setSetting('premiumize.token', token['access_token'])
		control.setSetting('premiumize.username', str(account_info['customer_id']))
		return False, True

	def revoke(self):
		try:
			control.setSetting('premiumize.token', '')
			control.setSetting('premiumize.username', '')
			control.dialog.ok(control.lang(40057), control.lang(32314))
		except:
			log_utils.error()

	def account_info(self):
		try:
			accountInfo = self._get(account_info_url)
			return accountInfo
		except:
			log_utils.error()
		return None

	def account_info_to_dialog(self):
		from datetime import datetime
		import math
		try:
			accountInfo = self.account_info()
			expires = datetime.fromtimestamp(accountInfo['premium_until'])
			days_remaining = (expires - datetime.today()).days
			expires = expires.strftime("%A, %B %d, %Y")
			points_used = int(math.floor(float(accountInfo['space_used']) / 1073741824.0))
			space_used = float(int(accountInfo['space_used']))/1073741824
			percentage_used = str(round(float(accountInfo['limit_used']) * 100.0, 1))
			items = []
			items += [control.lang(40040) % accountInfo['customer_id']]
			items += [control.lang(40041) % expires]
			items += [control.lang(40042) % days_remaining]
			items += [control.lang(40043) % points_used]
			items += [control.lang(40044) % space_used]
			items += [control.lang(40045) % percentage_used]
			return control.selectDialog(items, 'Premiumize')
		except:
			log_utils.error()
		return