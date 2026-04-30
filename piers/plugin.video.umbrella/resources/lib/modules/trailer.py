# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from json import loads as jsloads
from random import choice
import re
from sys import argv
from urllib.parse import quote_plus
from resources.lib.modules import client
from resources.lib.modules import control
import random

class Trailer:
	def __init__(self):
		self.base_link = 'https://www.youtube.com'
		try:
			self.ytkey_link = control.addon('plugin.video.youtube').getSetting('youtube.api.key')
		except:
			control.hide()
			return control.notification('YouTube', 'The YouTube addon is required for this feature.', icon=None)
		if self.ytkey_link == '': self.ytkey_link = random.choice([
			'AIzaSyBW-Z3TneLX-aG9TC5G061BTc9bBgftmPA'
			'AIzaSyA0LiS7G-KlrlfmREcCAXjyGqa_h_zfrSE',
			'AIzaSyDgcri5Aipa9EBeE48IJAYyd71aiPOpwWw',
			'AIzaSyBOXZVC-xzrdXSAmau5UM3rG7rc8eFIuFw'])
		self.max_results = '15'
		self.key_link = '&key=%s' % self.ytkey_link
		self.search_link = 'https://www.googleapis.com/youtube/v3/search?part=id&type=video&maxResults=15&q=%s'+ self.key_link
		self.search_link_select = 'https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=15&q=%s%s' % ('%s', self.key_link)
		# self.search_link = 'https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=5&q=%s' + self.key_link
		self.youtube_watch = 'https://www.youtube.com/watch?v=%s'

	def play(self, type='', name='', year='', url='', imdb='', windowedtrailer=0):
		try:
			url = self.worker(type, name, year, url, imdb)
			if not url: return
			title = control.infoLabel('ListItem.Title')
			if not title: title = control.infoLabel('ListItem.Label')
			icon = control.infoLabel('ListItem.Icon')
			item = control.item(label=title, offscreen=True)
			item.setProperty('IsPlayable', 'true')
			item.setArt({'icon': icon, 'thumb': icon,})
			#item.setInfo(type='video', infoLabels={'title': title})
			meta = {'title': title}
			control.set_info(item, meta)
			control.addItem(handle=int(argv[1]), url=url, listitem=item, isFolder=False)
			control.refresh()
			control.resolve(handle=int(argv[1]), succeeded=True, listitem=item)
			if windowedtrailer == 1:
				control.sleep(1000)
				while control.player.isPlayingVideo():
					control.sleep(1000)
				control.execute("Dialog.Close(%s, true)" % control.getCurrentDialogId)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def worker(self, type, name, year, url, imdb):
		try:
			if url.startswith(self.base_link):
				url = self.resolve(url)
				if not url: raise Exception()
				return url
			elif not url.startswith('http'):
				url = self.youtube_watch % url
				url = self.resolve(url)
				if not url: raise Exception()
				return url
			else: raise Exception()
		except:
			query = name + ' trailer'
			query = self.search_link % quote_plus(query)
			return self.search(query, type, name, year, imdb)

	def search(self, url, type, name, year, imdb):
		try:
			apiLang = control.apiLanguage().get('youtube', 'en')
			if apiLang != 'en': url += "&relevanceLanguage=%s" % apiLang
			result = client.request(url, error=True)
			if not result: return
			if 'error' in result:
				from resources.lib.modules import log_utils
				items = jsloads(result).get('error', []).get('errors', [])
				log_utils.log('message = %s' % str(items[0].get('message')), __name__, log_utils.LOGDEBUG)
				items = self.trakt_trailer(type, name, year, imdb)
			else:
				items = jsloads(result).get('items', [])
				items = [i.get('id', {}).get('videoId') for i in items]
			for vid_id in items:
				url = self.resolve(vid_id)
				if url: return url
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def trakt_trailer(self, type, name, year, imdb):
		try:
			trailer_id = ''
			from resources.lib.modules import trakt
			id = (name.lower() + '-' + year) if imdb == '0' else imdb #check if this needs .replace(' ', '-') between title spaces
			if type == 'movie': item = trakt.getMovieSummary(id)
			else: item = trakt.getTVShowSummary(id)
			trailer_id = item.get('trailer').split('v=')
			trailer_id = [trailer_id[1]]
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		return trailer_id

	def resolve(self, url):
		try:
			id = url.split('?v=')[-1].split('/')[-1].split('?')[0].split('&')[0]
			result = client.request(self.youtube_watch % id)
			message = client.parseDOM(result, 'div', attrs={'id': 'unavailable-submessage'})
			message = ''.join(message)
			alert = client.parseDOM(result, 'div', attrs={'id': 'watch7-notification-area'})
			if len(alert) > 0: raise Exception()
			if re.search(r'[a-zA-Z]', message): raise Exception()
			url = 'plugin://plugin.video.youtube/play/?video_id=%s' % id
			return url
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def playContext(self, type='', name='', year='', url='', imdb='', windowedtrailer=0):
		try:
			id = url.split('v=')[-1].split('/')[-1].split('?')[0].split('&')[0]
			url = 'plugin://plugin.video.youtube/play/?%s' % id
			control.execute("Dialog.Close(%s, true)" % control.getCurrentDialogId)
			if windowedtrailer == 1:
				control.execute("RunPlugin(%s)" % (url))
			else:
				control.execute("RunPlugin(%s,1)" % (url))
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def play_select(self, type, name, year, windowedtrailer=0):
		if self.ytkey_link == '':
			control.hide()
			return control.notification('YouTube', 'API Keys must be added to YouTube addon to use this feature.', icon=None)
		control.busy()
		try:
			url = self.worker2(type, name, year)
			if not url: return
			control.execute("PlayMedia(%s)" % (url))
			if windowedtrailer == 1:
				control.sleep(100)
				while control.player.isPlayingVideo():
					control.sleep(100)
				control.execute("Dialog.Close(%s, true)" % control.getCurrentDialogId)
		except:
			import traceback
			traceback.print_exc()

	def worker2(self, type, name, year):
		query = name + ' ' + str(year) + ' trailer'
		query = self.search_link_select % quote_plus(query)
		return self.search_select(query)

	def search_select(self, url):
		try:
			apiLang = control.apiLanguage().get('youtube', 'en')
			if apiLang != 'en': url += "&relevanceLanguage=%s" % apiLang
			import requests
			response = requests.get(url).json()
			error =  response.get('error', [])
			if error:
				control.hide()
				message = error.get('message', [])
				icon = control.addon('plugin.video.youtube').getAddonInfo('icon')
				control.notification('YOUTUBE', message, icon=icon)
				return None
			json_items = response.get('items', [])
			items = [i.get('id', {}).get('videoId') for i in json_items]
			labels = [i.get('snippet', {}).get('title') for i in json_items]
			labels = [client.replaceHTMLCodes(i) for i in labels]
			control.hide()
			select = control.selectDialog(labels, control.getLangString(40512))
			if select == -1: return None
			item = [items[select]]

			for vid_id in item:
				url = 'plugin://plugin.video.youtube/play/?video_id=%s' % vid_id
				return url
		except:
			import traceback
			traceback.print_exc()
			control.hide()