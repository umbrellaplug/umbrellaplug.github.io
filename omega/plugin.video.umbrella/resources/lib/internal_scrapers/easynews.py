# -*- coding: UTF-8 -*-
# (updated 7-19-2022)
'''
	Umbrella Internal Scrapers
'''

from base64 import b64encode
import re
import requests
from urllib.parse import quote
from resources.lib.modules.control import setting as getSetting
from resources.lib.modules import scrape_utils
from resources.lib.modules import source_utils

SORT = {'s1': 'relevance', 's1d': '-', 's2': 'dsize', 's2d': '-', 's3': 'dtime', 's3d': '-'}
SEARCH_PARAMS = {'st': 'adv', 'sb': 1, 'fex': 'm4v,3gp,mov,divx,xvid,wmv,avi,mpg,mpeg,mp4,mkv,avc,flv,webm', 'fty[]': 'VIDEO', 'spamf': 1, 'u': '1', 'gx': 1, 'pno': 1, 'sS': 3}
SEARCH_PARAMS.update(SORT)


class source:
	priority = 21
	pack_capable = False
	hasMovies = True
	hasEpisodes = True
	def __init__(self):
		self.language = ['en']
		self.base_link = "https://members.easynews.com"
		self.search_link = "/2.0/search/solr-search/advanced"

	def sources(self, data, hostDict):
		sources = []
		if not data: return sources
		sources_append = sources.append
		auth = self._get_auth()
		if not auth: return sources
		try:
			title_chk = getSetting('easynews.title.chk') == 'true'
			year = data['year']
			aliases = data['aliases']
			if 'tvshowtitle' in data:
				title = data['tvshowtitle'].replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
				episode_title = None
				years = None
				season = int(data.get('season'))
				episode = int(data.get('episode'))
				hdlr = 'S%02dE%02d' % (season, episode)
				query = '%s %s' % (re.sub(r'[^A-Za-z0-9\s\.-]+', '', title), hdlr)
			else:
				title = data['title'].replace('&', 'and').replace('/', ' ')
				episode_title = data['title']
				years = [str(int(year)-1), str(year), str(int(year)+1)]
				hdlr = year
				query = '%s' % re.sub(r'[^A-Za-z0-9\s\.-]+', '', title) # let "source_utils.check_title()" verify "release_title" contains a matching year in years list
			url, params = self._translate_search(query)
			results = requests.get(url, params=params, headers={'Authorization': auth}, timeout=20).json()
			down_url = results.get('downURL')
			dl_farm = results.get('dlFarm')
			dl_port = results.get('dlPort')
			files = results.get('data', [])
		except:
			source_utils.scraper_error('EASYNEWS')
			return sources


		for item in files:
			try:
				post_hash, post_title, ext, duration = item['0'], item['10'], item['11'], item['14']
				audio_langs = item.get('alangs')
				if audio_langs:
					if 'eng' not in audio_langs: continue

				if re.match(r'^\d+s', duration) or re.match('^[0-5]m', duration): continue
				if 'virus' in item and item['virus']: continue
				if 'type' in item and item['type'].upper() != 'VIDEO': continue
				stream_url = down_url + quote('/%s/%s/%s%s/%s%s' % (dl_farm, dl_port, post_hash, ext, post_title, ext))
				name = scrape_utils.clean_name(post_title)
				name_chk = name
				if 'tvshowtitle' in data:
					name_chk = re.sub(r'S\d+([.-])E\d+', hdlr, name_chk, 1, re.I)
					name_chk = re.sub(r'^tvp[.-]', '', name_chk, 1, re.I)
				name_chk = re.sub(r'disney[.-]gallery[.-]star[.-]wars[.-]', '', name_chk, 0, re.I)
				name_chk = re.sub(r'marvels[.-]', '', name_chk, 0, re.I)

				if title_chk:
					if not scrape_utils.check_title(title, aliases, name_chk, hdlr, year, years): continue
				name_info = scrape_utils.info_from_name(name_chk, title, year, hdlr, episode_title)
				# if source_utils.remove_lang(name_info, check_foreign_audio): continue
				#if not audio_langs:
				#	if source_utils.remove_lang(name_info, check_foreign_audio): continue
				#if undesirables and source_utils.remove_undesirables(name_info, undesirables): continue

				file_dl = '%s%s' % (stream_url, '|Authorization=%s' % quote(auth))
				quality, info = scrape_utils.get_release_quality(name_info, file_dl)
				try:
					dsize, isize = scrape_utils.convert_size(float(int(item['rawSize'])), to='GB')
					if isize: info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				sources_append({'provider': 'easynews', 'source': 'direct', 'name': name, 'name_info': name_info, 'quality': quality,
											'language': "en", 'url': file_dl, 'info': info, 'direct': True, 'debridonly': False, 'size': dsize})
			except:
				source_utils.scraper_error('EASYNEWS')
		return sources

	def _get_auth(self):
		auth = None
		try:
			username, password = getSetting('easynews.user'), getSetting('easynews.password')
			if username == '' or password == '': return auth
			user_info = '%s:%s' % (username, password)
			user_info = user_info.encode('utf-8')
			auth = '%s%s' % ('Basic ', b64encode(user_info).decode('utf-8'))
		except:
			source_utils.scraper_error('EASYNEWS')
		return auth

	def _translate_search(self, query):
		params = SEARCH_PARAMS
		params['pby'] = 1000 # Results per Page, increased from 350
		moderation = 1 if getSetting('easynews.moderation') == 'true' else 0
		params['safeO'] = moderation # 1 is the moderation (adult filter) ON, 0 is OFF.
		params['safeO'] = 1 if getSetting('easynews.moderation') == 'true' else 0 # 1 is the moderation(adult filter) ON, 0 is OFF.
		# params['gps'] = params['sbj'] = query # gps stands for "group search" and does so by "Keywords", sbj=subject and can limit results, use gps only
		params['gps'] = query
		url = '%s%s' % (self.base_link, self.search_link)
		return url, params