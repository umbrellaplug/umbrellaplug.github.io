# -*- coding: UTF-8 -*-
# (updated 01-02-2022)
'''
	Umbrellascrapers Project
'''

from base64 import b64encode
from json import loads as jsloads
import re
from urllib.parse import urljoin
from umbrellascrapers.modules import cache
from umbrellascrapers.modules import client
from umbrellascrapers.modules.control import setting as getSetting
from umbrellascrapers.modules import source_utils


class source:
	priority = 25
	pack_capable = False
	hasMovies = False
	hasEpisodes = True
	def __init__(self):
		self.language = ['en']
		self.base_link = "https://ororo.tv"
		self.moviesearch_link = "/api/v2/movies"
		self.tvsearch_link = "/api/v2/shows"
		self.movie_link = "/api/v2/movies/%s"
		self.show_link = "/api/v2/shows/%s"
		self.episode_link = "/api/v2/episodes/%s"
		self.user = getSetting('ororo.user')
		self.password = getSetting('ororo.pass')
		self.headers = {
			'Authorization': self._get_auth(),
			'User-Agent': 'Placenta for Kodi'}

	def _get_auth(self):
		user_info = '%s:%s' % (self.user, self.password)
		user_info = user_info.encode('utf-8')
		auth = 'Basic ' + b64encode(user_info).decode('utf-8')
		return auth

	def sources(self, data, hostDict):
		sources = []
		if not data: return sources
		append = sources.append
		try:
			if (self.user == '' or self.password == ''): return sources
			url = cache.get(self.ororo_tvcache, 120, self.user)
			if not url: return sources
			url = [i[0] for i in url if data['imdb'] == i[1]]
			if not url: return sources
			url = self.show_link % url[0]

			url = urljoin(self.base_link, url)
			r = client.request(url, headers=self.headers)
			r = jsloads(r)['episodes']
			r = [(str(i['id']), str(i['season']), str(i['number']), str(i['airdate'])) for i in r]
			url = [i for i in r if data['season'] == i[1] and data['episode'] == i[2]]
			url += [i for i in r if data['premiered'] == i[3]]
			if not url: return sources
			url= self.episode_link % url[0][0]

			url = urljoin(self.base_link, url)
			url = client.request(url, headers=self.headers)
			if not url: return sources
			url = jsloads(url)['url']
			# log_utils.log('url = %s' % url, __name__)

			name = re.sub(r'(.*?)\/video/file/(.*?)/', '', url).split('.smil')[0].split('-')[0]
			quality, info = source_utils.get_release_quality(name)
			info = ' | '.join(info)

			append({'provider': 'ororo', 'source': 'direct', 'name': name, 'quality': quality, 'language': 'en', 'url': url,
							'info': info, 'direct': True, 'debridonly': False, 'size': 0}) # Ororo does not return a file size
			return sources
		except:
			source_utils.scraper_error('ORORO')
			return sources

	def ororo_tvcache(self, user):
		try:
			url = urljoin(self.base_link, self.tvsearch_link)
			r = client.request(url, headers=self.headers)
			r = jsloads(r)['shows']
			r = [(str(i['id']), str(i['imdb_id'])) for i in r]
			r = [(i[0], 'tt' + re.sub(r'[^0-9]', '', i[1])) for i in r]
			return r
		except:
			source_utils.scraper_error('ORORO')
			return