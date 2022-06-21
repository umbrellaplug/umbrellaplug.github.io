# -*- coding: utf-8 -*-
# modified by   for Umbrellascrapers (updated 01-02-2022)
'''
	Umbrellascrapers Project
'''

import re
from umbrellascrapers.modules import cfscrape
from umbrellascrapers.modules import client
from umbrellascrapers.modules import source_utils


class source:
	priority = 26
	pack_capable = False
	hasMovies = True
	hasEpisodes = True
	def __init__(self):
		self.language = ['en']
		self.base_link = "https://rlsbb.cc/"
		self.search_link = "https://search.rlsbb.cc/?s=%s" #may use in future but adds a request to do so.


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

			isSeasonQuery = False
			query = '%s %s' % (title, hdlr)
			query = re.sub(r'(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', query)
			query = re.sub(r'\s', '-', query)

			if int(year) >= 2021: self.base_link = self.base_new
			# else: self.base_link = self.base_old
			else: return sources # "old3.proxybb.com" does not seem operational anymore

			url = '%s%s' % (self.base_link, query)
			# log_utils.log('url = %s' % url, log_utils.LOGDEBUG)
			r = scraper.get(url, timeout=5).text
			if not r or 'nothing was found' in r:
				if 'tvshowtitle' in data:
					season = re.search(r'S(.*?)E', hdlr).group(1)
					query = re.sub(r'(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', title)
					query = re.sub(r'\s', '-', query)
					query = query + "-S" + season
					url = '%s%s' % (self.base_link, query)
					r = scraper.get(url, timeout=5).text
					isSeasonQuery = True
				else: return sources 
			if not r or 'nothing was found' in r: return sources
			# may need to add fallback to use self.search_link if nothing found
			posts = client.parseDOM(r, "div", attrs={"class": "content"})
			if not posts: return sources
		except:
			source_utils.scraper_error('RLSBB')
			return sources

		release_title = re.sub(r'[^A-Za-z0-9\s\.-]+', '', title).replace(' ', '.')
		count = 0

		undesirables = source_utils.get_undesirables()
		check_foreign_audio = source_utils.check_foreign_audio()
		for post in posts:
			if count >= 300: break # to limit large link list and slow scrape time
			items = []
			items_append = items.append
			try:
				post_titles = re.findall(r'(?:.*>|>\sRelease Name.*|\s)(%s.*?)<' % release_title, post, re.I) #parse all matching release_titles in each post(content) group
				if len(post_titles) >1:
					index = 0
					for name in post_titles:
						start = post_titles[index].replace('[', '\\[').replace('(', '\\(').replace(')', '\\)').replace('+', '\\+').replace(' \\ ', ' \\\\ ')
						end = (post_titles[index + 1].replace('[', '\\[').replace('(', '\\(').replace(')', '\\)').replace('+', '\\+')).replace(' \\ ', ' \\\\ ') if index + 1 < len(post_titles) else ''
						try: container = re.findall(r'(?:%s)([\S\s]+)(?:%s)' % (start, end), post, re.I)[0] #parse all data between release_titles in multi post(content) group
						except:
							source_utils.scraper_error('RLSBB')
							continue
						try: size = re.search(r'((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|Gb|MB|MiB|Mb))', container).group(0).replace(',', '.')
						except: size = '0'
						container = client.parseDOM(container, 'a', ret='href')
						items_append((name, size, container))
						index += 1
				elif len(post_titles) == 1:
					name = post_titles[0]
					container = client.parseDOM(post, 'a', ret='href') #parse all links in a single post(content) group
					try: size = re.search(r'((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|Gb|MB|MiB|Mb))', post).group(0).replace(',', '.')
					except: size = '0'
					items_append((name, size, container))
				else: continue

				for group_name, size, links in items:
					for i in links:
						name = group_name
						# if isSeasonQuery and hdlr not in name.upper():
							# name = i.rsplit("/", 1)[-1]
							# if hdlr not in name.upper(): continue
						if hdlr not in name.upper():
							name = i.rsplit("/", 1)[-1]
							if hdlr not in name.upper(): continue

						name = source_utils.strip_non_ascii_and_unprintable(client.replaceHTMLCodes(name))
						name_info = source_utils.info_from_name(name, title, year, hdlr, episode_title)
						if source_utils.remove_lang(name_info, check_foreign_audio): continue
						if undesirables and source_utils.remove_undesirables(name_info, undesirables): continue

						url = client.replaceHTMLCodes(str(i))
						if url in str(sources): continue

						valid, host = source_utils.is_host_valid(url, hostDict)
						if not valid: continue

						quality, info = source_utils.get_release_quality(name, url)
						try:
							if size == '0':
								try: size = re.search(r'((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|Gb|MB|MiB|Mb))', name).group(0).replace(',', '.')
								except: raise Exception()
							dsize, isize = source_utils._size(size)
							info.insert(0, isize)
						except: dsize = 0
						info = ' | '.join(info)

						append({'provider': 'rlsbb', 'source': host, 'name': name, 'name_info': name_info, 'quality': quality, 'language': 'en', 'url': url,
										'info': info, 'direct': False, 'debridonly': True, 'size': dsize})
						count += 1
			except:
				source_utils.scraper_error('RLSBB')
		return sources