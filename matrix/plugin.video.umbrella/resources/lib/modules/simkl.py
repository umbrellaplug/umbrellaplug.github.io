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
					control.progressDialog.close()
					self.secret = responseJson['access_token']
				except:
					log_utils.error()
					control.okDialog(title='default', message=40347)
					if fromSettings == 1:
						control.openSettings('7.0', 'plugin.video.umbrella')
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
		line = '%s\n%s'
		progressDialog = control.progressDialog
		progressDialog.create(getLS(40346))
		progressDialog.update(-1, line % (getLS(32513) % 'https://simkl.com/pin/', getLS(32514) % response['user_code']))
		self.auth_timeout = int(response['expires_in'])
		self.auth_step = int(response['interval'])
		self.device_code = response['device_code']
		self.user_code = response['user_code']        
		while self.secret == '':
			if progressDialog.iscanceled():
				progressDialog.close()
				break
			self.auth_loop(fromSettings=fromSettings)
		if self.secret: self.save_token(fromSettings=fromSettings)

	def save_token(self, fromSettings=0):
		try:
			self.token = self.secret
			control.sleep(500)
			control.setSetting('simkltoken', self.token)
			if fromSettings == 1:
				control.openSettings('7.0', 'plugin.video.umbrella')
				control.notification(message="Simkl Authorized", icon=simkl_icon)
			return True, None
		except:
			log_utils.error('Simkl Authorization Failed : ')
			if fromSettings == 1:
				control.openSettings('7.0', 'plugin.video.umbrella')
			return False, None

	def reset_authorization(self, fromSettings=0):
		try:
			control.setSetting('simkltoken', '')
			control.setSetting('simklusername', '')
			if fromSettings == 1:
				control.openSettings('7.0', 'plugin.video.umbrella')
			control.dialog.ok(getLS(40343), getLS(32320))

		except: log_utils.error()