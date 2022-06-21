# -*- coding: utf-8 -*-
# modified by   for Umbrellascrapers (updated 01-02-2022)
'''
	Umbrellascrapers Project
'''

import re
from urllib.parse import quote_plus
from umbrellascrapers.modules import client
from umbrellascrapers.modules import source_utils


class source:
	priority = 29
	pack_capable = False
	hasMovies = True
	hasEpisodes = True
	def __init__(self):
		self.language = ['en']
		self.base_link = "https://www.300mbfilms.cx"
		self.search_link = "/?s=%s"

	def sources(self, data, hostDict):
		sources = []
		if not data: return sources
		append = sources.append
		try:
			title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
			title = title.replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
			aliases = data['aliases']
			episode_title = data['title'] if 'tvshowtitle' in data else None
			year = data['year']
			hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else year

			query = '%s %s' % (title, hdlr)
			query = re.sub(r'(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', query)
			url = '%s%s' % (self.base_link, self.search_link % quote_plus(query))
			# log_utils.log('url = %s' % url)
			r = client.request(url, timeout=5)
			if not r: return sources
			posts = client.parseDOM(r, 'h2')
			urls = []
		except:
			source_utils.scraper_error('300MBFILMS')
			return sources

		undesirables = source_utils.get_undesirables()
		check_foreign_audio = source_utils.check_foreign_audio()
		for item in posts:
			if not item.startswith('<a href'): continue
			try:
				name = client.parseDOM(item, "a")[0]
				if not source_utils.check_title(title, aliases, name, hdlr, year): continue
				name_info = source_utils.info_from_name(name, title, year, hdlr, episode_title)
				if source_utils.remove_lang(name_info, check_foreign_audio): continue
				if undesirables and source_utils.remove_undesirables(name_info, undesirables): continue

				quality, info = source_utils.get_release_quality(name_info, item[0])
				try:
					size = re.search(r'((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|Gb|MB|MiB|Mb))', item).group(0)
					dsize, isize = source_utils._size(size)
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				item = client.parseDOM(item, 'a', ret='href')
				url = item
				links = self.links(url)
				if links is None: continue
				urls += [(i, name, name_info, quality, info, dsize) for i in links]
			except:
				source_utils.scraper_error('300MBFILMS')

		for item in urls:
			try:
				if 'earn-money' in item[0]: continue
				url = client.replaceHTMLCodes(item[0])

				valid, host = source_utils.is_host_valid(url, hostDict)
				if not valid: continue

				append({'provider': '300mbfilms', 'source': host, 'name': item[1], 'name_info': item[2], 'quality': item[3], 'language': 'en', 'url': url,
								'info': item[4], 'direct': False, 'debridonly': True, 'size': item[5]})
			except:
				source_utils.scraper_error('300MBFILMS')
		return sources

	def links(self, url):
		urls = []
		try:
			if not url: return
			r = client.request(url[0], timeout=5)
			r = client.parseDOM(r, 'div', attrs={'class': 'entry'})
			r = client.parseDOM(r, 'a', ret='href')
			if 'money' not in str(r): return urls
			r1 = [i for i in r if 'money' in i][0]
			r = client.request(r1, timeout=5)
			if not r: return
			r = client.parseDOM(r, 'div', attrs={'id': 'post-\d+'})[0]
			if 'enter the password' in r:
				plink= client.parseDOM(r, 'form', ret='action')[0]
				post = {'post_password': '300mbfilms', 'Submit': 'Submit'}
				send_post = client.request(plink, post=post, output='cookie', timeout=5)
				link = client.request(r1, cookie=send_post, timeout=5)
			else:
				link = client.request(r1, timeout=5)
			if '<strong>Single' not in link: return urls
			link = re.findall(r'<strong>Single(.+?)</tr', link, re.DOTALL | re.I)[0]
			link = client.parseDOM(link, 'a', ret='href')
			link = [(i.split('=')[-1]) for i in link]
			for i in link: urls.append(i)
			return urls
		except:
			source_utils.scraper_error('300MBFILMS')
			return urls