# -*- coding: utf-8 -*-
"""
	Umbrella Add-on (added by Umbrella Dev 12/23/22)
"""

import re
import requests
from requests.adapters import HTTPAdapter
from sys import argv, exit as sysexit
from urllib3.util.retry import Retry
from resources.lib.modules import control
from resources.lib.modules import log_utils

getLS = control.lang
getSetting = control.setting
oauth_base_url = 'https://api.simkl.com/oauth/pin'
simkl_icon = control.joinPath(control.artPath(), 'simkl.png')
simklclientid = 'cecec23773dff71d940876860a316a4b74666c4c31ad719fe0af8bb3064a34ab'
session = requests.Session()
retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
session.mount('https://api.simkl.com', HTTPAdapter(max_retries=retries, pool_maxsize=100))
sim_qr = control.joinPath(control.artPath(), 'simklqr.png')


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
		self.highlightColor = control.setting('highlight.color')

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
		self.progressDialog.update(-1, line % (getLS(32513) % (self.highlightColor, 'https://simkl.com/pin/'), getLS(32514) % (self.highlightColor,response['user_code']), getLS(40390)))
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
			if fromSettings == 1:
				control.openSettings('9.0', 'plugin.video.umbrella')
				control.notification(message="Simkl Authorized", icon=simkl_icon)
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
			if fromSettings == 1:
				control.openSettings('9.0', 'plugin.video.umbrella')
			control.dialog.ok(getLS(40343), getLS(32320))

		except: log_utils.error()

	def get_request(self, url):
		try:
			try: response = session.get(url, timeout=20)
			except requests.exceptions.SSLError:
				response = session.get(url, verify=False)
		except requests.exceptions.ConnectionError:
			control.notification(message=40349)
			from resources.lib.modules import log_utils
			log_utils.error()
			return None
		try:
			if response.status_code in (200, 201): return response.json()
			elif response.status_code == 404:
				if getSetting('debug.level') == '1':
					from resources.lib.modules import log_utils
					log_utils.log('Simkl get_request() failed: (404:NOT FOUND) - URL: %s' % url, level=log_utils.LOGDEBUG)
				return '404:NOT FOUND'
			elif 'Retry-After' in response.headers: # API REQUESTS ARE BEING THROTTLED, INTRODUCE WAIT TIME (TMDb removed rate-limit on 12-6-20)
				throttleTime = response.headers['Retry-After']
				control.notification(message='SIMKL Throttling Applied, Sleeping for %s seconds' % throttleTime)
				control.sleep((int(throttleTime) + 1) * 1000)
				return self.get_request(url)
			else:
				if getSetting('debug.level') == '1':
					from resources.lib.modules import log_utils
					log_utils.log('SIMKL get_request() failed: URL: %s\n                       msg : SIMKL Response: %s' % (url, response.text), __name__, log_utils.LOGDEBUG)
				return None
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return None

	def simkl_list(self, url):
		if not url: return
		url = url % simklclientid
		try:
			#result = cache.get(self.get_request, 96, url % self.API_key)
			result = self.get_request(url)
			if result is None: return
			items = result
		except: return
		self.list = [] ; sortList = []
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
				self.list.append(values)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		return self.list