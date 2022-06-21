# -*- coding: UTF-8 -*-
# modified by   for Umbrellascrapers (updated 01-02-2022)
'''
	Umbrellascrapers Project
'''

import re
from urllib.parse import quote_plus
from umbrellascrapers.modules import cfscrape
from umbrellascrapers.modules import client
from umbrellascrapers.modules import source_utils
from umbrellascrapers.modules import workers


class source:
	priority = 21
	pack_capable = False
	hasMovies = True
	hasEpisodes = True
	def __init__(self):
		self.language = ['en']
		self.base_link = "http://max-rls.com"
		self.search_link = "/?s=%s&submit=Find"

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
			query = re.sub(r'[^A-Za-z0-9\s\.-]+', '', query)
			url = ('%s%s' % (self.base_link, self.search_link % quote_plus(query))).replace('%3A+', '+')
			# log_utils.log('url = %s' % url)
			result = scraper.get(url, timeout=5).text

			if not result or "Sorry, but you are looking for something that isn't here" in str(result): return sources
			posts = client.parseDOM(result, "div", attrs={"class": "post"})
			if not posts: return sources
		except:
			source_utils.scraper_error('MAXRLS')
			return sources

		undesirables = source_utils.get_undesirables()
		check_foreign_audio = source_utils.check_foreign_audio()
		for post in posts:
			try:
				post_title = client.parseDOM(post, "h2", attrs={"class": "postTitle"})
				post_title = client.parseDOM(post_title, 'a')[0]
				if not source_utils.check_title(title, aliases, post_title, hdlr, year): continue
				content = client.parseDOM(post, "div", attrs={"class": "postContent"})
				ltr = client.parseDOM(content, "p", attrs={"dir": "ltr"})
				if not ltr: continue

				for i in ltr:
					if '<strong>' not in i or 'imdb.com' in i: continue
					name = re.search(r'<strong>(.*?)<', i).group(1)
					name = re.sub(r'(<span.*?>)', '', name).replace('</span>', '')
					if title not in name: continue # IMDB and Links: can be in name so check for title match
					name_info = source_utils.info_from_name(name, title, year, hdlr, episode_title)
					if source_utils.remove_lang(name_info, check_foreign_audio): continue
					if undesirables and source_utils.remove_undesirables(name_info, undesirables): continue

					links = client.parseDOM(i, "a", ret="href")
					size = re.search(r'((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|Gb|MB|MiB|Mb))', i).group(0)

					for url in links:
						if url in str(sources): continue
						valid, host = source_utils.is_host_valid(url, hostDict)
						if not valid: continue

						quality, info = source_utils.get_release_quality(name_info, url)
						try:
							dsize, isize = source_utils._size(size)
							info.insert(0, isize)
						except: dsize = 0
						info = ' | '.join(info)

						append({'provider': 'maxrls', 'source': host, 'name': name, 'name_info': name_info, 'quality': quality, 'language': 'en',
										'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize})
			except:
				source_utils.scraper_error('MAXRLS')
		return sources