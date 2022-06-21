# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from binascii import b2a_hex
from json import loads as jsloads
from os import urandom
import re
from urllib.parse import unquote, urlencode, parse_qsl, parse_qs, urlparse
from resources.lib.modules import client


def google(url, ref=None):
	try:
		if 'lh3.googleusercontent' in url or 'bp.blogspot' in url:
			newheaders = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
							'Accept': '*/*', 'Host': 'lh3.googleusercontent.com', 'Accept-Language': 'en-US,en;q=0.8,de;q=0.6,es;q=0.4',
							'Accept-Encoding': 'identity;q=1, *;q=0', 'Referer': ref,
							'Connection': 'Keep-Alive', 'X-Client-Data': 'CJK2yQEIo7bJAQjEtskBCPqcygEIqZ3KAQjSncoBCKijygE=',
							'Range': 'bytes=0-'}
			resp = client.request(url, headers=newheaders, redirect=False, output='extended', timeout='10')
			loc = resp[2]['Location']
			c = resp[2]['Set-Cookie'].split(';')[0]
			url = '%s|Cookie=%s' % (loc, c)
			return url

		if any(x in url for x in ('youtube.', 'docid=')):
			url = 'https://drive.google.com/file/d/%s/view' % re.compile(r'docid=([\w-]+)').findall(url)[0]

		netloc = urlparse(url.strip().lower()).netloc
		netloc = netloc.split('.google')[0]

		if netloc == 'docs' or netloc == 'drive':
			url = url.split('/preview', 1)[0]
			url = url.replace('drive.google.com', 'docs.google.com')

		headers = {'User-Agent': client.agent()}
		result = client.request(url, output='extended', headers=headers)

		try: headers['Cookie'] = result[2]['Set-Cookie']
		except: pass

		result = result[0]
		if netloc == 'docs' or netloc == 'drive':
			result = re.compile(r'"fmt_stream_map",(".+?")').findall(result)[0]
			result = jsloads(result)
			result = [i.split('|')[-1] for i in result.split(',')]
			result = sum([googletag(i, append_height=True) for i in result], [])

		elif netloc == 'photos':
			result = result.replace('\r', '').replace('\n', '').replace('\t', '')
			result = re.compile(r'"\d*/\d*x\d*.+?","(.+?)"').findall(result)[0]
			result = result.replace('\\u003d', '=').replace('\\u0026', '&')
			result = re.compile(r'url=(.+?)&').findall(result)
			result = [unquote(i) for i in result]
			result = sum([googletag(i, append_height=True) for i in result], [])

		elif netloc == 'picasaweb':
			id = re.compile(r'#(\d*)').findall(url)[0]
			result = re.search(r'feedPreload:\s*(.*}]}})},', result, re.S).group(1)
			result = jsloads(result)['feed']['entry']

			if len(result) > 1: result = [i for i in result if str(id) in i['link'][0]['href']][0]
			elif len(result) == 1: result = result[0]

			result = result['media']['content']
			result = [i['url'] for i in result if 'video' in i['type']]
			result = sum([googletag(i, append_height=True) for i in result], [])

		elif netloc == 'plus':
			id = (urlparse(url).path).split('/')[-1]
			result = result.replace('\r', '').replace('\n', '').replace('\t', '')
			result = result.split('"%s"' % id)[-1].split(']]')[0]
			result = result.replace('\\u003d', '=').replace('\\u0026', '&')
			result = re.compile(r'url=(.+?)&').findall(result)
			result = [unquote(i) for i in result]
			result = sum([googletag(i, append_height=True) for i in result], [])
		result = sorted(result, key=lambda i: i.get('height', 0), reverse=True)
		url = []

		for q in ('4K', '1440p', '1080p', 'HD', 'SD'):
			try: url += [[i for i in result if i.get('quality') == q][0]]
			except: pass

		for i in url:
			i.pop('height', None)
			i.update({'url': i['url'] + '|%s' % urlencode(headers)})
		if not url: return
		return url
	except: return

def googletag(url, append_height=False):
	quality = re.compile(r'itag=(\d*)').findall(url)
	quality += re.compile(r'=m(\d*)$').findall(url)
	try: quality = quality[0]
	except: return []
	itag_map = {'151': {'quality': 'SD', 'height': 72}, '212': {'quality': 'SD', 'height': 480}, '313': {'quality': '4K', 'height': 2160},
					'242': {'quality': 'SD', 'height': 240}, '315': {'quality': '4K', 'height': 2160}, '219': {'quality': 'SD', 'height': 480},
					'133': {'quality': 'SD', 'height': 240}, '271': {'quality': '1440p', 'height': 1440}, '272': {'quality': '4K', 'height': 2160},
					'137': {'quality': '1080p', 'height': 1080}, '136': {'quality': 'HD', 'height': 720}, '135': {'quality': 'SD', 'height': 480},
					'134': {'quality': 'SD', 'height': 360}, '82': {'quality': 'SD', 'height': 360}, '83': {'quality': 'SD', 'height': 480},
					'218': {'quality': 'SD', 'height': 480}, '93': {'quality': 'SD', 'height': 360}, '84': {'quality': 'HD', 'height': 720},
					'170': {'quality': '1080p', 'height': 1080}, '167': {'quality': 'SD', 'height': 360}, '22': {'quality': 'HD', 'height': 720},
					'46': {'quality': '1080p', 'height': 1080}, '160': {'quality': 'SD', 'height': 144}, '44': {'quality': 'SD', 'height': 480},
					'45': {'quality': 'HD', 'height': 720}, '43': {'quality': 'SD', 'height': 360}, '94': {'quality': 'SD', 'height': 480},
					'5': {'quality': 'SD', 'height': 240}, '6': {'quality': 'SD', 'height': 270}, '92': {'quality': 'SD', 'height': 240},
					'85': {'quality': '1080p', 'height': 1080}, '308': {'quality': '1440p', 'height': 1440}, '278': {'quality': 'SD', 'height': 144},
					'78': {'quality': 'SD', 'height': 480}, '302': {'quality': 'HD', 'height': 720}, '303': {'quality': '1080p', 'height': 1080},
					'245': {'quality': 'SD', 'height': 480}, '244': {'quality': 'SD', 'height': 480}, '247': {'quality': 'HD', 'height': 720},
					'246': {'quality': 'SD', 'height': 480}, '168': {'quality': 'SD', 'height': 480}, '266': {'quality': '4K', 'height': 2160},
					'243': {'quality': 'SD', 'height': 360}, '264': {'quality': '1440p', 'height': 1440}, '102': {'quality': 'HD', 'height': 720},
					'100': {'quality': 'SD', 'height': 360}, '101': {'quality': 'SD', 'height': 480}, '95': {'quality': 'HD', 'height': 720},
					'248': {'quality': '1080p', 'height': 1080}, '96': {'quality': '1080p', 'height': 1080}, '91': {'quality': 'SD', 'height': 144},
					'38': {'quality': '4K', 'height': 3072}, '59': {'quality': 'SD', 'height': 480}, '17': {'quality': 'SD', 'height': 144},
					'132': {'quality': 'SD', 'height': 240}, '18': {'quality': 'SD', 'height': 360}, '37': {'quality': '1080p', 'height': 1080},
					'35': {'quality': 'SD', 'height': 480}, '34': {'quality': 'SD', 'height': 360}, '298': {'quality': 'HD', 'height': 720},
					'299': {'quality': '1080p', 'height': 1080}, '169': {'quality': 'HD', 'height': 720}}
	if quality in itag_map:
		quality = itag_map[quality]
		if append_height:
			return [{'quality': quality['quality'], 'height': quality['height'], 'url': url}]
		else:
			return [{'quality': quality['quality'], 'url': url}]
	else: return []

def googlepass(url):
	try:
		try: headers = dict(parse_qsl(url.rsplit('|', 1)[1]))
		except: headers = None
		url = url.split('|')[0].replace('\\', '')
		url = client.request(url, headers=headers, output='geturl')
		if 'requiressl=yes' in url:
			url = url.replace('http://', 'https://')
		else:
			url = url.replace('https://', 'http://')
		if headers: url += '|%s' % urlencode(headers)
		return url
	except: return

def vk(url):
	try:
		query = parse_qs(urlparse(url).query)
		try: oid, video_id = query['oid'][0], query['id'][0]
		except: oid, video_id = re.findall(r'\/video(.*)_(.*)', url)[0]
		sources_url = 'http://vk.com/al_video.php?act=show_inline&al=1&video=%s_%s' % (oid, video_id)
		html = client.request(sources_url)
		html = re.sub(r'[^\x00-\x7F]+', ' ', html)
		sources = re.findall(r'(\d+)x\d+.+?(http.+?\.m3u8.+?)n', html)
		if not sources: sources = re.findall(r'"url(\d+)"\s*:\s*"(.+?)"', html)
		sources = [(i[0], i[1].replace('\\', '')) for i in sources]
		sources = dict(sources)
		url = []
		try: url += [{'quality': 'HD', 'url': sources['720']}]
		except: pass
		try: url += [{'quality': 'SD', 'url': sources['540']}]
		except: pass
		try: url += [{'quality': 'SD', 'url': sources['480']}]
		except: pass
		if url: return url
		try: url += [{'quality': 'SD', 'url': sources['360']}]
		except: pass
		if url: return url
		try: url += [{'quality': 'SD', 'url': sources['240']}]
		except: pass
		if not url == []: return url
	except: return

def odnoklassniki(url):
	try:
		media_id = re.compile(r'//.+?/.+?/([\w]+)').findall(url)[0]
		result = client.request('http://ok.ru/dk', post={'cmd': 'videoPlayerMetadata', 'mid': media_id})
		result = re.sub(r'[^\x00-\x7F]+', ' ', result)
		result = jsloads(result).get('videos', [])
		hd = []
		for name, quali in {'ultra': '4K', 'quad': '1440p', 'full': '1080p', 'hd': 'HD'}.items():
			hd += [{'quality': quali, 'url': i.get('url')} for i in result if i.get('name').lower() == name]
		sd = []
		for name, quali in {'sd': 'SD', 'low': 'SD', 'lowest': 'SD', 'mobile': 'SD'}.items():
			sd += [{'quality': quali, 'url': i.get('url')} for i in result if i.get('name').lower() == name]
		url = hd + sd[:1]
		if not url == []:
			return url
	except: return

def cldmailru(url):
	try:
		v = url.split('public')[-1]
		r = client.request(url)
		r = re.sub(r'[^\x00-\x7F]+', ' ', r)
		tok = re.findall(r'"tokens"\s*:\s*{\s*"download"\s*:\s*"([^"]+)', r)[0]
		url = re.findall(r'"weblink_get"\s*:\s*\[.+?"url"\s*:\s*"([^"]+)', r)[0]
		url = '%s%s?key=%s' % (url, v, tok)
		return url
	except: return

def yandex(url):
	try:
		cookie = client.request(url, output='cookie')
		r = client.request(url, cookie=cookie)
		r = re.sub(r'[^\x00-\x7F]+', ' ', r)
		sk = re.findall(r'"sk"\s*:\s*"([^"]+)', r)[0]
		idstring = re.findall(r'"id"\s*:\s*"([^"]+)', r)[0]
		idclient = b2a_hex(urandom(16))
		post = {'idClient': idclient, 'version': '3.9.2', 'sk': sk, '_model.0': 'do-get-resource-url', 'id.0': idstring}
		post = urlencode(post)
		r = client.request('https://yadi.sk/models/?_m=do-get-resource-url', post=post, cookie=cookie)
		r = jsloads(r)
		url = r['models'][0]['data']['file']
		return url
	except: return