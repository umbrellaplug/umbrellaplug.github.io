# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""
from resources.lib.modules import control
from resources.lib.modules import client
import re
from urllib.parse import quote_plus

class Search:
	def init(self):
		self.page_limit = control.getSetting('page.item.limit')
		self.keyword_link = 'https://www.imdb.com/search/keyword/?keywords=%s&sort=moviemeter&title_type=%s&count=%s' % ('%s', '%s', self.page_limit)

	def imdb_list(self, url, media):
		list = []
		try:
			result = client.request(url)
			items = client.parseDOM(result, 'li', attrs={'class': 'ipl-zebra-list__item user-list'})
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		for item in items:
			try:
				name = client.parseDOM(item, 'a')[0]
				name = client.replaceHTMLCodes(name)
				url = client.parseDOM(item, 'a', ret='href')[0]
				url = url.split('/list/', 1)[-1].strip('/')
				url = self.imdblist_link % url
				url = client.replaceHTMLCodes(url)
				list.append({'name': name, 'url': url, 'context': url, 'image': 'imdb.png', 'icon': 'DefaultVideoPlaylists.png', 'action': media+'&folderName=%s' % quote_plus(name)})
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		list = sorted(list, key=lambda k: re.sub(r'(^the |^a |^an )', '', k['name'].lower()))
		return list
	def movieKeywordSearch(self, keywords):
		result = None
		if keywords:
			keywords = keywords.replace(' ', '-')
			try:
				url = self.keyword_link(quote_plus(keywords), 'movie')
				result = self.imdb_list(url, media='movie')
				return result
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
				return result

	def tvShowKeywordSearch(self, keywords):
		result = None
		if keywords:
			keywords = keywords.replace(' ', '-')
			try:
				url = self.keyword_link(quote_plus(keywords), 'tvshows')
				result = self.imdb_list(url, media='tvshows')
				return result
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
				return result
