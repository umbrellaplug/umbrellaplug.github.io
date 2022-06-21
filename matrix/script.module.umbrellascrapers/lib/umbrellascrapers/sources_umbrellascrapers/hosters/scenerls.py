# -*- coding: utf-8 -*-
# modified by   for Umbrellascrapers (updated 01-02-2022)
'''
	Umbrellascrapers Project
'''

import re
from urllib.parse import quote_plus
from umbrellascrapers.modules import cfscrape
from umbrellascrapers.modules import client
from umbrellascrapers.modules import source_utils


class source:
	priority = 21
	pack_capable = False
	hasMovies = True
	hasEpisodes = True
	def __init__(self):
		self.language = ['en']
		self.base_link = "http://scene-rls.net"
		self.search_link = "/?s=%s"

	def sources(self, data, hostDict):
		sources = []
		if not data: return sources
		append = sources.append
		try:
			scraper = cfscrape.create_scraper()

			title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
			title = title.replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
			aliases = data['aliases']
			episode_title = data['title'] if 'tvshowtitle' in data else None
			year = data['year']
			hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else year

			query = '%s %s' % (title, hdlr)
			query = re.sub(r'(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', query)
			url = self.search_link % quote_plus(query)
			url = '%s%s' % (self.base_link, url)
			# log_utils.log('url = %s' % url)

			r = scraper.get(url, timeout=5).text
			posts = client.parseDOM(r, 'div', attrs={'class': 'post'})
			if not posts: return sources
		except:
			source_utils.scraper_error('SCENERLS')
			return sources
		items = []
		for post in posts:
			try:
				content = client.parseDOM(post, "div", attrs={"class": "postContent"})
				size = re.search(r'((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|Gb|MB|MiB|Mb))', content[0]).group(0)
				u = client.parseDOM(content, "h2")
				u = client.parseDOM(u, 'a', ret='href')
				u = [(i.strip('/').split('/')[-1], i, size) for i in u]
				items += u
			except:
				source_utils.scraper_error('SCENERLS')
				return sources

		undesirables = source_utils.get_undesirables()
		check_foreign_audio = source_utils.check_foreign_audio()
		for item in items:
			try:
				name = client.replaceHTMLCodes(item[0])
				if not source_utils.check_title(title, aliases, name, hdlr, year): continue
				name_info = source_utils.info_from_name(name, title, year, hdlr, episode_title)
				if source_utils.remove_lang(name_info, check_foreign_audio): continue
				if undesirables and source_utils.remove_undesirables(name_info, undesirables): continue

				# check year for reboot/remake show issues if year is available-crap shoot
				# if 'tvshowtitle' in data:
					# if re.search(r'([1-3][0-9]{3})', name):
						# if not any(value in name for value in (year, str(int(year)+1), str(int(year)-1))):
							# continue

				url = client.replaceHTMLCodes(str(item[1]))
				if url in str(sources): continue

				valid, host = source_utils.is_host_valid(url, hostDict)
				if not valid: continue

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					dsize, isize = source_utils._size(item[2])
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				append({'provider': 'scenerls', 'source': host, 'name': name, 'name_info': name_info, 'quality': quality, 'language': 'en', 'url': url,
								'info': info, 'direct': False, 'debridonly': True, 'size': dsize})
			except:
				source_utils.scraper_error('SCENERLS')
		return sources