# -*- coding: utf-8 -*-
import re
import json
import base64
from urllib.parse import parse_qsl, quote, urlencode
from caches.base_cache import connect_database
from caches.main_cache import cache_object
from caches.settings_cache import get_setting
from modules.dom_parser import parseDOM
from modules.utils import chunks
from modules.kodi_utils import make_session, clear_property
# from modules.kodi_utils import logger

video_extensions = 'm4v, 3g2, 3gp, nsv, tp, ts, ty, pls, rm, rmvb, mpd, ifo, mov, qt, divx, xvid, bivx, vob, nrg, img, iso, udf, pva, wmv, asf, asx, ogm, m2v, avi, bin, dat,' \
'mpg, mpeg, mp4, mkv, mk3d, avc, vp3, svq3, nuv, viv, dv, fli, flv, wpl, xspf, vdr, dvr-ms, xsp, mts, m2t, m2ts, evo, ogv, sdp, avs, rec, url, pxml, vc1, h264, rcv, rss, mpls,' \
'mpl, webm, bdmv, bdm, wtv, trp, f4v, pvr, disc'
SEARCH_PARAMS = {'st': 'adv', 'sb': 1, 'fex': video_extensions, 'fty[]': 'VIDEO', 'spamf': 1, 'u': 1, 'gx': 1, 'pno': 1, 'sS': 3, 's1': 'relevance', 's1d': '-', 'pby': 1000}
IMAGE_SEARCH_PARAMS = {'st': 'adv', 'safeO': 0, 'sb': 1, 's1': 'relevance', 's1d': '+', 's2': 'nsubject', 's2d': '+', 's3': 'nrfile', 's3d': '+', 'pno': 1, 'sS':1,
'fty[]': 'IMAGE', 'pby': 10000}
search_types_params = {'VIDEO': SEARCH_PARAMS, 'IMAGE': IMAGE_SEARCH_PARAMS}
image_remove_filters = ['comic', 'fake', 'erotica']
timeout = 20.0
session = make_session()

def import_easynews():
	''' API version setting currently disabled '''
	# if get_setting('fenlight.easynews.api_version') == '0': return EasyNewsAPI()
	# else: return EasyNewsAPIv3()
	return EasyNewsAPI()

class EasyNewsAPI:
	def __init__(self):
		self.base_url = 'https://members.easynews.com'
		self.search_link = '/2.0/search/solr-search/advanced'
		self.account_link = 'https://account.easynews.com/editinfo.php'
		self.usage_link = 'https://account.easynews.com/usageview.php'
		self.username = get_setting('fenlight.easynews_user', 'empty_setting')
		self.password = get_setting('fenlight.easynews_password', 'empty_setting')
		self.auth = self._get_auth()
		self.auth_quoted = quote(self.auth)
		self.base_get = self._get
		self.base_process = self._process_files
		self.base_resolver = self.resolver

	def _get_auth(self):
		user_info = '%s:%s' % (self.username, self.password)
		user_info = user_info.encode('utf-8')
		auth = 'Basic ' + base64.b64encode(user_info).decode('utf-8')
		return auth

	def search(self, query, expiration=48):
		self.query = query
		url, self.params = self._translate_search()
		string = 'EASYNEWS_SEARCH_' + urlencode(self.params)
		return cache_object(self._process_search, string, url, json=False, expiration=expiration)

	def search_images(self, query, page_no=1, expiration=48):
		self.query = query
		self.base_process = self.process_image_files
		url, self.params = self._translate_search(search_type='IMAGE')
		string = 'EASYNEWS_IMAGE_SEARCH_%s' % urlencode(self.params)
		results = cache_object(self._process_search, string, url, json=False, expiration=expiration)
		try: results['results'] = results['results'][page_no -1]
		except: pass
		return results

	def account(self):
		account_info, usage_info = self.account_info(), self.usage_info()
		return account_info, usage_info

	def account_info(self):
		account_info = None
		try:
			account_html = self._get(self.account_link)
			account_info = parseDOM(account_html, 'form', attrs={'id': 'accountForm'})
			account_info = parseDOM(account_info, 'td')[0:11][1::3]
		except: pass
		return account_info

	def usage_info(self):
		usage_info = None
		try:
			usage_html = self._get(self.usage_link)
			usage_info = parseDOM(usage_html, 'div', attrs={'class': 'table-responsive'})
			usage_info = parseDOM(usage_info, 'td')[0:11][1::3]
			usage_info[1] = re.sub(r'[</].+?>', '', usage_info[1])
		except: pass
		return usage_info

	def process_image_files(self, files):
		def _process():
			count = 1
			for item in files:
				try:
					post_hash, size, group, post_title, ext = item['0'], item['4'], item['9'], item['10'], item['11']
					if ext == '.gif': continue
					if 'type' in item and item['type'].upper() != 'IMAGE': continue
					elif 'virus' in item and item['virus']: continue
					if any(i in group for i in image_remove_filters): continue
					url_add = quote('/%s/%s/%s%s/%s%s' % (dl_farm, dl_port, post_hash, ext, post_title, ext))
					url_dl = download_url + url_add
					file_dl = down_url + url_add + '|Authorization=%s' % self.auth_quoted
					thumbnail = 'https://th.easynews.com/thumbnails-%s/sm-%s.jpg' % (post_hash[0:3], post_hash)
					result = {'name': '%s_%s_%02d' % (self.query, post_title, count),
							  'fullsize': size,
							  'fullres': item['fullres'],
							  'url_dl': url_dl,
							  'down_url': file_dl,
							  'version': 'version2',
							  'thumbnail': thumbnail,
							  'group': group}
					count += 1
					yield result
				except Exception as e:
					from modules.kodi_utils import logger
					logger('easynews API Exception', str(e))
		down_url = files.get('downURL')
		download_url = 'https://%s:%s@members.easynews.com/dl' % (quote(self.username), quote(self.password))
		dl_farm, dl_port = self.get_farm_and_port(files)
		total_results, total_pages = files.get('results'), files.get('numPages')
		files = files.get('data', [])
		results = list(chunks(list(list(_process())), 50))
		return {'total_results': total_results, 'total_pages': len(results), 'results': results}

	def _process_files(self, files):
		def _process():
			for item in files:
				try:
					post_hash, size, post_title, ext, duration = item['0'], item['4'], item['10'], item['11'], item['14']
					if 'alangs' in item and item['alangs']: language = item['alangs']
					else: language = ''
					if 'type' in item and item['type'].upper() != 'VIDEO': continue
					elif 'virus' in item and item['virus']: continue
					if re.match(r'^\d+s', duration) or re.match(r'^[0-5]m', duration): short_vid = True
					else: short_vid = False
					url_add = quote('/%s/%s/%s%s/%s%s' % (dl_farm, dl_port, post_hash, ext, post_title, ext))
					stream_url = streaming_url + url_add
					file_dl = down_url + url_add + '|Authorization=%s' % self.auth_quoted
					thumbnail = 'https://th.easynews.com/thumbnails-%s/pr-%s.jpg' % (post_hash[0:3], post_hash)
					result = {'name': post_title,
							  'size': size,
							  'rawSize': item['rawSize'],
							  'width': int(item['width']),
							  'runtime': int(item['runtime']/60.0),
							  'url_dl': stream_url,
							  'down_url': file_dl,
							  'version': 'version2',
							  'short_vid': short_vid,
							  'language': language,
							  'thumbnail': thumbnail}
					yield result
				except Exception as e:
					from modules.kodi_utils import logger
					logger('easynews API Exception', str(e))
		down_url = files.get('downURL')
		streaming_url = 'https://%s:%s@members.easynews.com/dl' % (quote(self.username), quote(self.password))
		dl_farm, dl_port = self.get_farm_and_port(files)
		files = files.get('data', [])
		results = list(_process())
		return results

	def get_farm_and_port(self, files):
		dl_farm, dl_port = files.get('dlFarm'), files.get('dlPort')
		return dl_farm, dl_port

	def _process_files_v3(self, results):
		def _process():
			for item in files:
				try:
					post_hash, size, post_title, ext, duration, sig = item['hash'], item['bytes'], item['filename'], item['extension'], item['runtime'], item['sig']
					if 'alangs' in item and item['alangs']: language = item['alangs']
					else: language = ''
					if 'type' in item and item['type'].upper() != 'VIDEO': continue
					elif 'virus' in item and item['virus']: continue
					if re.match(r'^\d+s', duration) or re.match(r'^[0-5]m', duration): short_vid = True
					else: short_vid = False
					url_dl = self.stream_url % (post_hash, ext, post_title, sid, sig)
					thumbnail = 'https://th.easynews.com/thumbnails-%s/pr-%s.jpg' % (post_hash[0:3], post_hash)
					result = {'name': post_title,
							  'size': size,
							  'rawSize': item['rawSize'],
							  'width': int(item['width']),
							  'rawSize': size,
							  'url_dl': url_dl,
							  'version': 'version3',
							  'short_vid': short_vid,
							  'language': language,
							  'thumbnail': thumbnail}
					yield result
				except Exception as e:
					from modules.kodi_utils import logger
					logger('easynews API Exception', str(e))
		files, sid = results.get('data', []), results.get('sid')
		results = list(_process())
		return results

	def _translate_search(self, search_type='VIDEO'):
		params = search_types_params[search_type]
		params['safeO'] = 0
		params['gps'] = self.query
		url = self.base_url + self.search_link
		return url, params

	def _process_search(self, url):
		results = self.base_get(url, self.params)
		return self.base_process(results)

	def _get(self, url, params={}):
		headers = {'Authorization': self.auth}
		try: response = session.get(url, params=params, headers=headers, timeout=timeout).text
		except: return None
		try: return json.loads(response)
		except: return response

	def _get_v3(self, url, params={}):
		headers = {'Authorization': self.auth}
		try: response = session.get(url, params=params, headers=headers, timeout=timeout).content
		except: return None
		response = re.compile(self.regex, re.DOTALL).findall(response)
		response = response + '}'
		try: return json.loads(response)
		except: return response

	def resolve_easynews(self, url_dl):
		return self.base_resolver(url_dl)

	def resolver(self, url_dl):
		try:
			headers = {'Authorization': self.auth}
			resolved_link = session.get(url_dl, headers=headers, stream=True, timeout=timeout).url
		except: resolved_link = url_dl
		return resolved_link

	def resolver_v3(self, url_dl):
		headers = {'Authorization': self.auth}
		response = session.get(url_dl, headers=headers, stream=True, timeout=timeout)
		stream_url = response.url
		resolved_link = stream_url + '|Authorization=%s' % self.auth_quoted
		return resolved_link

class EasyNewsAPIv3(EasyNewsAPI):
	def __init__(self):
		EasyNewsAPI.__init__(self)
		self.base_url = 'https://members-beta.easynews.com/3.0/index/basic'
		self.stream_url = 'https://members-beta.easynews.com/os/3.0/auto/443/%s%s/%s?sid=%s&sig=%s'
		self.search_link = ''
		self.regex = r'var INIT_RES = (.+?)};'
		self.base_get = self._get_v3
		self.base_process = self._process_files_v3
		self.base_resolver = self.resolver_v3

def clear_media_results_database():
	dbcon = connect_database('maincache_db')
	easynews_results = [str(i[0]) for i in dbcon.execute("SELECT id FROM maincache WHERE id LIKE 'EASYNEWS_SEARCH_%'").fetchall()]
	if easynews_results:
		try:
			dbcon.execute("DELETE FROM maincache WHERE id LIKE 'EASYNEWS_SEARCH_%'")
			for i in easynews_results: clear_property(i)
			process_result = True
		except: process_result = False
	else: process_result = True
	easynews_image_results = [str(i[0]) for i in dbcon.execute("SELECT id FROM maincache WHERE id LIKE 'EASYNEWS_IMAGE_SEARCH_%'").fetchall()]
	if easynews_image_results:
		try:
			dbcon.execute("DELETE FROM maincache WHERE id LIKE 'EASYNEWS_IMAGE_SEARCH_%'")
			for i in easynews_image_results: clear_property(i)
			process_image_result = True
		except: process_image_result = False
	else: process_image_result = True
	return (process_result, process_image_result) == (True, True)

