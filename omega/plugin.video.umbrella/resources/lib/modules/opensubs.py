# -*- coding: utf-8 -*-
"""
	Umbrella Addon
"""

import re
import requests
from resources.lib.modules import control
from resources.lib.modules import log_utils
import xbmc


base_url = 'https://api.opensubtitles.com/api/v1'
api_key = 'cQBWQwPugvGVDrpdU9MDRlvdfcu4WNTx'
version = control.getUmbrellaVersion()


class Opensubs():
	def __init__(self):
		self.username = control.setting('opensubsusername')
		self.password = control.setting('opensubspassword')
		self.jwt_token = control.setting('opensubstoken')
		self.headers = {
			'Content-Type': 'application/json',
			'Api-Key': api_key,
			'User-Agent': 'Umbrella v'+version}
		self.highlight_color = control.setting('highlight.color')

	def auth(self):
		url = base_url + '/login'
		if not self.username or not self.password: return False
		data = {
			"username": self.username,
			"password": self.password,
		}
		if self.jwt_token:
			url = base_url + '/infos/user'
			headers2 = {
			'Content-Type': 'application/json',
			'Api-Key': api_key,
			'Authorization': self.jwt_token,
			'User-Agent': 'Umbrella v'+version
			}
			response = requests.get(url,headers=headers2)
			if response.status_code == 200:
				return True
			else:
				url = base_url + '/login'
				response2 = requests.post(url, headers=self.headers, json=data)
				response2 = response.json()
				if response2.status_code == 200:
					control.setSetting('opensubstoken', response.get('token'))
					return True
				else:
					return False

		else:
			response = requests.post(url, headers=self.headers, json=data)
			response = response.json()
			control.setSetting('opensubstoken', response.get('token'))
			return True

	def getSubs(self, title, imdb, year, season=None, episode=None):
		try:
			language = xbmc.convertLanguage(control.setting('subtitles.lang.1'), xbmc.ISO_639_1)
			if season:
				url = base_url + '/subtitles?imdb_id=%s&season_number=%s&episode_number=%s&languages=%s' % (imdb, season, episode,language)
			else:
				url = base_url + '/subtitles?imdb_id=%s&year=%s&languages=%s' % (imdb, year, language)
			headers = {
				'Content-Type': 'application/json',
				'Api-Key': api_key,
				'Authorization': self.jwt_token,
				'User-Agent': 'Umbrella v'+version
				}
			response = requests.get(url,headers=headers)
			response = response.json()
			response = response['data']
			results = []
			from resources.lib.modules import log_utils
			log_utils.log('OpenSubs Searching: Imdb:%s Season: %s Episode: %s Language: %s.' % (imdb, season, episode,language), level=log_utils.LOGDEBUG)
			for count, x in enumerate(response):
				try:
					fileName = response[count]['attributes'].get('files')[0].get('file_name')
					fileID = response[count]['attributes'].get('files')[0].get('file_id')
					results.append({'fileName': fileName, 'fileID': fileID})
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
			return results
		except:
			results = []
			return results

	def downloadSubs(self, fileID, fileName):
		try:
			url = base_url + '/download'
			headers = {
				'Content-Type': 'application/json',
				'Api-Key': api_key,
				'Authorization': self.jwt_token,
				'User-Agent': 'Umbrella v'+version
				}
			data = {
				"file_id": fileID,
			}
			response = requests.post(url, headers=headers, json=data)
			response = response.json()
			link = response.get('link')
			from resources.lib.modules import log_utils
			log_utils.log('OpenSubs Download Link: %s Filename: %s.' % (link, fileName), level=log_utils.LOGDEBUG)
			return link, fileName
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return None

	def getAccountStatus(self):
		try:
			url = base_url + '/login'
			if not self.username or not self.password: return control.okDialog(title=40503, message='Please enter username and password.')
			data = {
				"username": self.username,
				"password": self.password,
			}
			headers = {
			'Content-Type': 'application/json',
			'Api-Key': api_key,
			'User-Agent': 'Umbrella v'+version}
			response = requests.post(url,headers=headers, json=data)
			response = response.json()
			responseUser = response.get('user')
			responseToken = response.get('token')
			username = self.username
			a_downloads = responseUser.get('allowed_downloads')
			control.setSetting('opensubstoken', responseToken)
			control.openSettings('14.0', 'plugin.video.umbrella')
			return control.okDialog(title=40503, message=control.getLangString(40508) % (username, a_downloads))
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return control.okDialog(title=40503, message='Error checking opensubs. Please check username and password. Press Ok to save and try checking again.')

	def revokeAccess(self):
		try:
			control.homeWindow.setProperty('umbrella.updateSettings', 'false')
			control.setSetting('opensubsusername','')
			control.setSetting('opensubspassword','')
			control.homeWindow.setProperty('umbrella.updateSettings', 'true')
			control.setSetting('opensubstoken','')
			self.jwt_token = ''
			control.openSettings('14.0', 'plugin.video.umbrella')
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
