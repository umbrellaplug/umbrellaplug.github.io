# -*- coding: UTF-8 -*-
# modified by   for Umbrellascrapers (updated 12-14-2021)
'''
	Umbrellascrapers Project
'''

from json import loads as jsloads
import os.path
from xbmc import executeJSONRPC as jsonrpc
from xbmcvfs import File as openFile
from umbrellascrapers.modules import cleantitle
from umbrellascrapers.modules import source_utils


class source:
	priority = 29
	pack_capable = False
	hasMovies = True
	hasEpisodes = True
	def __init__(self):
		self.language = ['en', 'de', 'fr', 'ko', 'pl', 'pt', 'ru']
		self.domains = []

	def sources(self, data, hostDict):
		sources = []
		if not data: return sources
		append = sources.append
		try:
			content_type = 'episode' if 'tvshowtitle' in data else 'movie'
			years = (data['year'], str(int(data['year'])+1), str(int(data['year'])-1))

			if content_type == 'movie':
				title = cleantitle.get_simple(data['title']).lower()
				ids = [data['imdb']]
				r = jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties": ["imdbnumber", "title", "originaltitle", "file"]}, "id": 1}' % years)
				if 'movies' not in r: return sources
				r = jsloads(r)['result']['movies']
				r = [i for i in r if str(i['imdbnumber']) in ids or title in (cleantitle.get_simple(i['title']), cleantitle.get_simple(i['originaltitle']))]
				try: r = [i for i in r if not i['file'].encode('utf-8').endswith('.strm')]
				except: r = [i for i in r if not i['file'].endswith('.strm')]
				if not r: return sources
				r = r[0]
				r = jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": {"properties": ["streamdetails", "file"], "movieid": %s }, "id": 1}' % str(r['movieid']))
				r = jsloads(r)['result']['moviedetails']

			elif content_type == 'episode':
				title = cleantitle.get_simple(data['tvshowtitle']).lower()
				season, episode = data['season'], data['episode']
				r = jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties": ["imdbnumber", "title"]}, "id": 1}' % years)
				if 'tvshows' not in r: return sources
				r = jsloads(r)['result']['tvshows']
				r = [i for i in r if title in (cleantitle.get_simple(i['title']).lower() if not ' (' in i['title'] else cleantitle.get_simple(i['title']).split(' (')[0])]
				if not r: return sources
				else: r = r[0]
				r = jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"filter":{"and": [{"field": "season", "operator": "is", "value": "%s"}, {"field": "episode", "operator": "is", "value": "%s"}]}, "properties": ["file"], "tvshowid": %s }, "id": 1}' % (str(season), str(episode), str(r['tvshowid'])))
				r = jsloads(r)['result']['episodes']
				if not r: return sources
				try: r = [i for i in r if not i['file'].encode('utf-8').endswith('.strm')]
				except: r = [i for i in r if not i['file'].endswith('.strm')]
				if not r: return sources
				r = r[0]
				r = jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodeDetails", "params": {"properties": ["streamdetails", "file"], "episodeid": %s }, "id": 1}' % str(r['episodeid']))
				r = jsloads(r)['result']['episodedetails']

			url = r['file']
			try: name = os.path.basename(url)
			except:
				try: name = url.rsplit('/', 1)[1]
				except: name = url
			# log_utils.log('name = %s' % name, __name__)
			try:
				quality = int(r['streamdetails']['video'][0]['width'])
			except:
				source_utils.scraper_error('LIBRARY')
				quality = -1

			if quality > 1920: quality = '4K'
			if quality >= 1920: quality = '1080p'
			if 1280 <= quality < 1900: quality = '720p'
			if quality < 1280: quality = 'SD'

			info = []
			info_append = info.append
			try:
				f = openFile(url) ; s = f.size() ; f.close()
				dsize = float(s) / 1073741824
				isize = '%.2f GB' % dsize
				info.insert(0, isize)
			except:
				source_utils.scraper_error('LIBRARY')
				dsize = 0
			try:
				c = r['streamdetails']['video'][0]['codec']
				if c == 'avc1': c = 'h264'
				info_append(c)
			except:
				source_utils.scraper_error('LIBRARY')
			try:
				ac = r['streamdetails']['audio'][0]['codec']
				if ac == 'dca': ac = 'dts'
				if ac == 'dtshd_ma': ac = 'dts-hd ma'
				info_append(ac)
			except:
				source_utils.scraper_error('LIBRARY')
			try:
				ach = r['streamdetails']['audio'][0]['channels']
				if ach == 1: ach = 'mono'
				if ach == 2: ach = '2.0'
				if ach == 6: ach = '5.1'
				if ach == 8: ach = '7.1'
				info_append(ach)
			except:
				source_utils.scraper_error('LIBRARY')

			info = ' | '.join(info)

			append({'provider': 'library', 'source': 'local', 'quality': quality, 'name': name, 'language': 'en', 'url': url, 'info': info,
							'local': True, 'direct': True, 'debridonly': False, 'size': dsize})
			return sources
		except:
			source_utils.scraper_error('LIBRARY')
			return sources