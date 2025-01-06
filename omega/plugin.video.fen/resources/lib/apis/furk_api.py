# -*- coding: utf-8 -*-
from caches.main_cache import cache_object
from modules.utils import remove_accents
from modules.kodi_utils import make_session, clear_property, maincache_db, database, get_setting, set_setting
# from modules.kodi_utils import logger

base_url = 'http://www.furk.net/api/'
login_url = 'login/login?login=%s&pwd=%s'
file_get_video_url = 'file/get?api_key=%s&type=video'
file_link_url = 'file/link?api_key=%s&id=%s'
file_unlink_url = 'file/unlink?api_key=%s&id=%s'
file_protect_url = 'file/protect?api_key=%s&id=%s&is_protected=%s'
tfile_url = 'file/get?api_key=%s&t_files=1&id=%s'
account_info_url = 'account/info?api_key=%s'
search_url = 'plugins/metasearch?api_key=%s&q=%s&cached=yes' \
						'&match=%s&moderated=0%s&sort=relevance&type=video&offset=0&limit=200'
search_direct_url = 'plugins/metasearch?api_key=%s&q=%s&cached=all' \
						'&sort=cached&type=video&offset=0&limit=700'
timeout = 20.0
session = make_session(base_url)

class FurkAPI:
	def __init__(self):
		self.api_key = self.get_api()
		if not self.api_key: return

	def check_status(self, result):
		return result.get('status', 'not_ok') == 'ok'

	def get_api(self):
		api_key = get_setting('fen.furk_api_key', '')
		if not api_key:
			try:
				user_name, user_pass = get_setting('fen.furk_login'), get_setting('fen.furk_password')
				if not user_name or not user_pass: return
				url = base_url + login_url % (user_name, user_pass)
				result = session.post(url, timeout=timeout)
				result = result.json()
				if self.check_status(result):
					api_key = result['api_key']
					set_setting('furk_api_key', api_key)
			except: pass
		return api_key

	def search(self, query, expiration=48):
		try:
			search_in = '' if '@files' in query else '&attrs=name'
			url = base_url + search_url % (self.api_key, query, 'extended', search_in)
			string = 'fen_FURK_SEARCH_%s' % url
			return cache_object(self._process_files, string, url, json=False, expiration=expiration)
		except: return

	def direct_search(self, query):
		try:
			url = base_url + search_direct_url % (self.api_key, query)
			string = 'fen_FURK_SEARCH_DIRECT_%s' % url
			return cache_object(self._process_files, string, url, json=False, expiration=48)
		except: return

	def t_files(self, file_id):
		try:
			url = base_url + tfile_url % (self.api_key, file_id)
			string = 'fen_%s_%s' % ('FURK_T_FILE', file_id)
			return cache_object(self._process_tfiles, string, url, json=False, expiration=168)
		except: return

	def file_get_video(self):
		try:
			url = base_url + file_get_video_url % self.api_key
			return self._get(url)['files']
		except: return

	def file_link(self, item_id):
		try:
			url = base_url + file_link_url % (self.api_key, item_id)
			return self._get(url)
		except: return

	def file_unlink(self, item_id):
		try:
			url = base_url + file_unlink_url % (self.api_key, item_id)
			return self._get(url)
		except: return

	def file_protect(self, item_id, is_protected):
		try:
			url = base_url + file_protect_url % (self.api_key, item_id, is_protected)
			return self._get(url)
		except: return

	def account_info(self):
		try:
			url = base_url + account_info_url % self.api_key
			return self._get(url)
		except: return

	def _process_files(self, url):
		result = self._get(url)
		if not self.check_status(result): return None
		if not 'files' in result: return []
		return result['files']

	def _process_tfiles(self, url):
		result = self._get(url)
		if not self.check_status(result) or result['found_files'] != '1': return None
		return result['files'][0]['t_files']

	def _get(self, url):
		try:
			result = session.get(url, timeout=timeout)
			return result.json()
		except: return None

def clear_media_results_database():
	results = []
	dbcon = database.connect(maincache_db, timeout=40.0, isolation_level=None)
	dbcur = dbcon.cursor()
	dbcur.execute('''PRAGMA synchronous = OFF''')
	dbcur.execute('''PRAGMA journal_mode = OFF''')
	dbcur.execute("SELECT id FROM maincache WHERE id LIKE 'fen_FURK_SEARCH_%'")
	try:
		furk_results = [str(i[0]) for i in dbcur.fetchall()]
		if not furk_results: results.append('success')
		dbcur.execute("DELETE FROM maincache WHERE id LIKE 'fen_FURK_SEARCH_%'")
		for i in furk_results: clear_property(i)
		results.append('success')
	except: results.append('failed')
	dbcur.execute("SELECT id FROM maincache WHERE id LIKE 'fen_FURK_SEARCH_DIRECT_%'")
	try:
		furk_results = [str(i[0]) for i in dbcur.fetchall()]
		if not furk_results: results.append('success')
		dbcur.execute("DELETE FROM maincache WHERE id LIKE 'fen_FURK_SEARCH_DIRECT_%'")
		for i in furk_results: clear_property(i)
		results.append('success')
	except: results.append('failed')
	return 'failed' if 'failed' in results else 'success'
