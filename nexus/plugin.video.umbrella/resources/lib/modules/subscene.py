# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

url = 'https://subscene.com'
import re
from urllib.parse import parse_qsl, quote_plus
from resources.lib.modules import client
from resources.lib.modules import number2ordinal
from resources.lib.modules.dom_parser import parseDOM
from resources.lib.modules import control

import os, fnmatch
# new module created for subscene subtitles
def get_subtitles(title, year, season=None, episode=None):
	try:
		return search_request(title, year, season, episode)
	except:
		return None

def match_title(title, year, response):
	title_plus_year = '%s (%s)' % (title, year)
	href_regex = r'<a href="(.*?)">' + re.escape(title_plus_year) + r'</a>'
	return re.search(href_regex, response, re.IGNORECASE)


def match_title_tv(title, season, response):
	ordinal_season = number2ordinal.convert(season).strip()
	title_plus_season = '%s' % (title)
	href_regex = r'<a href="(.*?)">' + re.escape(title_plus_season) + r'</a>'
	return re.search(href_regex, response, re.IGNORECASE)


def find_title(title, year, season, response):
	if season == None:
		result = match_title(title, year, response)
		if not result:
			prev_year = int(year) - 1
			result = match_title(title, prev_year, response)
	else:
		result = match_title_tv(title, season, response)

	if not result:
		return None

	title_href = result.group(1)
	request = title_href

	return request

def search_request(title, year, season=None, episode=None):
	if title:
		if season == None and episode == None:
			#movie
			searchUrl = url+'/subtitles/searchbytitle?query='+quote_plus(title)
			searchResponse = client.request(searchUrl)
		else:
			#tvshow
			ordinal_season = number2ordinal.convert(season).strip()
			title = '%s - %s Season' % (title, ordinal_season)
			searchUrl = url+'/subtitles/searchbytitle?query='+quote_plus(title)
			searchResponse = client.request(searchUrl)

		title_href = find_title(title, year, season, searchResponse)
		title_result = client.request(url+title_href)
		any_regex = r'.*?'
		results_regex = (
				r'<a href="' + re.escape(title_href) + r'(.*?)">' +
					any_regex + r'</span>' + any_regex +
					r'<span>(.*?)</span>' + any_regex +
				r'</a>' + any_regex +
				r'(<td class="a41">)?' + any_regex +
			r'</tr>'
		)
		results = re.findall(results_regex, title_result, re.DOTALL)
		if not results:
			return None
		else:
			langResults = []
			for count, x in enumerate(results):
				detectedLanguage = results[count][0].split('/')[1]
				fileName = results[count][1].lstrip().rstrip()
				subtitleUrl = url+title_href+results[count][0]
				langResults.append({'language': detectedLanguage, 'fileName': fileName, 'subtitleUrl': subtitleUrl})
			return langResults
	else:
		from resources.lib.modules import log_utils
		return log_utils.log('Cannot search. No title sent')

def get_download_url(kurl):
	downloadPage = client.request(kurl)
	reggy = re.compile('(?<=href=").*?(?=")')
	downloadlink = parseDOM(downloadPage, 'div', attrs={'class': 'download'})
	downloadPage = reggy.findall(str(downloadlink))
	downloadPage = url + downloadPage[0]
	return downloadPage

def delete_all_subs():
	try:
		from resources.lib.modules import log_utils
		log_utils.log('removing all subtitle files.', level=log_utils.LOGDEBUG)
		download_path = control.subtitlesPath
		subtitle = download_path
		def find(pattern, path):
			result = []
			for root, dirs, files in os.walk(path):
				for name in files:
					if fnmatch.fnmatch(name, pattern):
						result.append(os.path.join(root, name))
			return result

		subtitles = find('*.*', subtitle)
		for x in subtitles:
			try:
				os.remove(x)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()