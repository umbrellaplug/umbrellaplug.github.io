# -*- coding: UTF-8 -*-
# modified by   for Umbrellascrapers  (updated 01-02-2022)
'''
	Umbrellascrapers Project
'''

import re
import time
from urllib.parse import urljoin, quote_plus
from umbrellascrapers.modules import cfscrape
from umbrellascrapers.modules import cleantitle
from umbrellascrapers.modules import client
from umbrellascrapers.modules import dom_parser  # switch to client.parseDOM() to rid import
from umbrellascrapers.modules import source_utils
from umbrellascrapers.modules import workers


class source:
	priority = 24
	pack_capable = False
	hasMovies = True
	hasEpisodes = True
	def __init__(self):
		self.language = ['en']
		# self.base_link = 'http://rapidmoviez.cr/' # cloudflare IUAM challenge failure
		self.base_link = "http://rmz.cr"
		self.search_link = "/search/%s"
		self.scraper = cfscrape.create_scraper()

	def search(self, title, year):
		try:
			url = urljoin(self.base_link, self.search_link % (quote_plus(title)))
			r = self.scraper.get(url, timeout=10).text
			if not r: return None
			r = dom_parser.parse_dom(r, 'div', {'class': 'list_items'})[0] # switch to client.parseDOM() to rid import
			r = dom_parser.parse_dom(r.content, 'li')
			r = [(dom_parser.parse_dom(i, 'a', {'class': 'title'})) for i in r]
			r = [(i[0].attrs['href'], i[0].content) for i in r]
			r = [(urljoin(self.base_link, i[0])) for i in r if cleantitle.get(title) in cleantitle.get(i[1]) and year in i[1]]
			if r: return r[0]
			else: return None
		except:
			return None

	def sources(self, data, hostDict):
		self.sources = []
		if not data: return self.sources
		self.sources_append = self.sources.append
		try:
			self.hostDict = hostDict
			self.title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
			self.title = self.title.replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
			self.aliases = data['aliases']
			self.episode_title = data['title'] if 'tvshowtitle' in data else None
			self.year = data['year']
			self.hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else self.year
			imdb = data['imdb']

			url = self.search(self.title, self.year)
			# log_utils.log('url = %s' % url)
			if not url: return self.sources

			result = self.scraper.get(url, timeout=10).text
			if not result: return self.sources
			r_pack = None
			if 'tvshowtitle' in data:
				r = dom_parser.parse_dom(result, 'ul', {'id': 'episodes'})
				# r_pack = dom_parser.parse_dom(result, 'ul', {'id': 'packs'}) # Rapidmoviez has pack files, needs more work
			else:
				r = dom_parser.parse_dom(result, 'ul', {'id': 'releases'})

			if not r and not r_pack: return self.sources
			if r:
				r = dom_parser.parse_dom(r[0].content, 'a', req=['href'])
				r = [(i.content, urljoin(self.base_link, i.attrs['href'])) for i in r if i and i.content != 'Watch']
				r = [(i[0], i[1]) for i in r if self.hdlr in i[0].upper()]

			# if r_pack:
				# r_pack = dom_parser.parse_dom(r_pack[0].content, 'a', req=['href'])
				# r_pack = [(i.content, urljoin(self.base_link, i.attrs['href'])) for i in r_pack if i and i.content != 'Watch']
				# r += [(i[0], i[1]) for i in r_pack if 'S%02d' % int(data['season']) in i[0].upper()]
				# r += [(i[0], i[1]) for i in r_pack if 'SEASON %02d' % int(data['season']) in i[0].upper()]
			# log_utils.log('r = %s' % r)

			self.undesirables = source_utils.get_undesirables()
			self.check_foreign_audio = source_utils.check_foreign_audio()
			threads = []
			append = threads.append
			for i in r:
				append(workers.Thread(self.get_sources, i[0], i[1]))
			[i.start() for i in threads]
			alive = [x for x in threads if x.is_alive() is True]
			while alive:
				alive = [x for x in threads if x.is_alive() is True]
				time.sleep(0.1)
			return self.sources
		except:
			source_utils.scraper_error('RAPIDMOVIEZ')
			return self.sources

	def get_sources(self, name, url):
		try:
			r = self.scraper.get(url, timeout=10).text
			name = client.replaceHTMLCodes(name)
			if name.startswith('['): name = name.split(']')[1]
			name = name.strip().replace(' ', '.')
			name_info = source_utils.info_from_name(name, self.title, self.year, self.hdlr, self.episode_title)
			if source_utils.remove_lang(name_info, self.check_foreign_audio): return
			if self.undesirables and source_utils.remove_undesirables(name_info, self.undesirables): return

			l = dom_parser.parse_dom(r, 'pre', {'class': 'links'})
			if l == []: return
			s = ''
			for i in l: s += i.content
			urls = re.findall(r'''((?:http|ftp|https)://[\w_-]+(?:(?:\.[\w_-]+)+)[\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])''', i.content, flags=re.M | re.S)

			for link in urls:
				url = client.replaceHTMLCodes(str(link))
				if url in str(self.sources): continue

				valid, host = source_utils.is_host_valid(url, self.hostDict)
				if not valid: continue

				quality, info = source_utils.get_release_quality(name, url)
				try:
					size = re.search(r'((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|Gb|MB|MiB|Mb))', name).group(0)
					dsize, isize = source_utils._size(size)
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				self.sources_append({'provider': 'rapidmoviez', 'source': host, 'name': name, 'name_info': name_info, 'quality': quality, 'language': 'en', 'url': url,
													'info': info, 'direct': False, 'debridonly': True, 'size': dsize})
		except:
			source_utils.scraper_error('RAPIDMOVIEZ')