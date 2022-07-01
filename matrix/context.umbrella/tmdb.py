# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

import requests
import xbmc

API_key = 'bc96b19479c7db6c8ae805744d0bdfe2'
find_url = 'https://api.themoviedb.org/3/find/%s?api_key=%s&external_source=%s' % ('%s', API_key, '%s')
externalids_url = 'https://api.themoviedb.org/3/%s/%s/external_ids?api_key=%s' % ('%s', '%s', API_key)


def get_request(url):
	try:
		try: response = requests.get(url)
		except requests.exceptions.SSLError:
			response = requests.get(url, verify=False)
	except requests.exceptions.ConnectionError:
		return notification(message=32024)
	if '200' in str(response): return response.json()
	elif 'Retry-After' in response.headers: 	# API REQUESTS ARE BEING THROTTLED, INTRODUCE WAIT TIME (TMDb removed rate-limit on 12-6-20)
		throttleTime = response.headers['Retry-After']
		import xbmcgui
		xbmcgui.Dialog().notification(heading='TMDb', message='TMDB Throttling Applied, Sleeping for %s seconds' % throttleTime)
		xbmc.sleep((int(throttleTime) + 1) * 1000)
		return get_request(url)
	else:
		return None

def IdLookup(imdb, mediatype):
	result = None
	if not imdb: return result
	try:
		url = find_url % (imdb, 'imdb_id')
		result = get_request(url)
		if not result: raise Exception()
		if mediatype == 'movie':
			result = result.get('movie_results')[0]
		else:
			result = result.get('tv_results')[0]
	except:
		pass
	return result

def get_external_ids(tmdb, mediatype):
	result = None
	if not tmdb: return result
	try:
		mtype = 'tv' if mediatype == 'episode' else 'movie'
		url = externalids_url % (mtype, tmdb)
		result = get_request(url)
	except:
		pass
	return result
