# -*- coding: utf-8 -*-
"""Remote playback-segment lookup used by the Umbrella player."""

from threading import Thread

import requests


REQUEST_TIMEOUT = (3.05, 6.05)
MAX_MEDIA_SECONDS = 6 * 60 * 60
MAX_INTRO_SECONDS = 30 * 60


def _seconds(value, milliseconds=False):
	try:
		value = float(value)
		if milliseconds:
			value /= 1000.0
		if value < 0 or value > MAX_MEDIA_SECONDS:
			return None
		return value
	except (TypeError, ValueError, OverflowError):
		return None


def _validated_intro(start, end, milliseconds=False):
	start = _seconds(start, milliseconds)
	end = _seconds(end, milliseconds)
	if start is None or end is None or end <= start or end - start > MAX_INTRO_SECONDS:
		return None
	return start, end


def _segment_list(items, milliseconds=False):
	if isinstance(items, dict): items = [items]
	if not isinstance(items, list): return []
	segments = []
	for item in items:
		if not isinstance(item, dict): continue
		segment = _validated_intro(item.get('start_ms' if milliseconds else 'start_sec'),
				item.get('end_ms' if milliseconds else 'end_sec'), milliseconds)
		if segment: segments.append(segment)
	segments.sort(key=lambda segment: segment[0])
	return segments


class SegmentScraper:
	def __init__(self, imdb, tmdb, season, episode, request_get=None):
		self.params = {
			'imdb_id': str(imdb or ''), 'tmdb_id': str(tmdb or ''),
			'season': str(season), 'episode': str(episode)
		}
		self.request_get = request_get or requests.get

	def _request(self, provider, url, parser):
		try:
			response = self.request_get(url, params=self.params, timeout=REQUEST_TIMEOUT)
			response.raise_for_status()
			return parser(response.json())
		except Exception as exc:
			try:
				from resources.lib.modules import log_utils
				log_utils.log('Skip Intro: %s lookup failed: %s' % (provider, exc),
							  level=getattr(log_utils, 'LOGDEBUG', 0))
			except Exception: pass
			return {'intro': None, 'recaps': [], 'credits': None}

	@staticmethod
	def _parse_introdb(data):
		intro, outro = data.get('intro') or {}, data.get('outro') or {}
		return {
			'intro': _validated_intro(intro.get('start_sec'), intro.get('end_sec')),
			'recaps': _segment_list(data.get('recap')),
			'credits': _seconds(outro.get('start_sec'))
		}

	@staticmethod
	def _parse_theintrodb(data):
		intro_items, credit_items = data.get('intro') or [], data.get('credits') or []
		if not isinstance(intro_items, list): intro_items = []
		if not isinstance(credit_items, list): credit_items = []
		intro = intro_items[0] if intro_items and isinstance(intro_items[0], dict) else {}
		credits = credit_items[0] if credit_items and isinstance(credit_items[0], dict) else {}
		return {
			'intro': _validated_intro(intro.get('start_ms'), intro.get('end_ms'), True),
			'recaps': _segment_list(data.get('recap'), True),
			'credits': _seconds(credits.get('start_ms'), True)
		}

	def fetch_introdb(self):
		return self._request('IntroDB.app', 'https://api.introdb.app/segments', self._parse_introdb)

	def fetch_theintrodb(self):
		return self._request('TheIntroDB', 'https://api.theintrodb.org/v3/media', self._parse_theintrodb)

	def run(self):
		# Neither provider should make playback wait for the other's timeout.
		results = [None, None]
		def fetch(index, method):
			results[index] = method()
		threads = [Thread(target=fetch, args=(0, self.fetch_introdb)),
				   Thread(target=fetch, args=(1, self.fetch_theintrodb))]
		for thread in threads:
			thread.daemon = True
			thread.start()
		for thread in threads:
			thread.join()
		intro = credits = None
		recaps = []
		for result in results:
			result = result or {}
			if intro is None: intro = result.get('intro')
			if not recaps: recaps = result.get('recaps') or []
			if credits is None: credits = result.get('credits')
		return intro, recaps, credits
