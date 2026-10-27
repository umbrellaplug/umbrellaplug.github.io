# -*- coding: utf-8 -*-
"""Compact, transactional Floppy watched/progress synchronization."""

import time
import uuid
from urllib.parse import urljoin

import requests

from resources.lib.database import floppysync
from resources.lib.modules import control, log_utils


class FloppySyncError(Exception):
	def __init__(self, message, status=None, code=None, reason=None, retry_after=None):
		super(FloppySyncError, self).__init__(message)
		self.status = status
		self.code = code
		self.reason = reason
		self.retry_after = retry_after


class FloppyCursorExpired(FloppySyncError):
	pass


class FloppyRouteUnavailable(FloppySyncError):
	pass


class FloppyConnectionInactive(FloppySyncError):
	pass


_session = requests.Session()


def _base_url():
	url = (control.setting('floppy.baseurl') or '').strip()
	if url and not url.startswith(('http://', 'https://')): url = 'https://' + url
	url = url.rstrip('/')
	if url and not url.endswith('/api/v1'): url += '/api/v1'
	return url


def _aborted():
	try: return control.monitor.abortRequested()
	except Exception: return False


def _wait(seconds):
	try: return control.monitor.waitForAbort(int(seconds))
	except Exception:
		control.sleep(int(seconds * 1000))
		return False


def _sync_request(method, path, params=None, body=None, retry_post=False):
	base = _base_url()
	if not base: raise FloppySyncError('Floppy base URL is not configured')
	url = path if path.startswith(base) else urljoin(base + '/', path.lstrip('/'))
	headers = {'Accept': 'application/json', 'Content-Type': 'application/json',
		'Authorization': 'Bearer %s' % control.setting('floppy.token')}
	attempts = 2 if method.upper() != 'POST' or retry_post else 1
	response = None
	for attempt in range(attempts):
		if _aborted(): raise FloppySyncError('Floppy sync aborted')
		try:
			response = _session.request(method.upper(), url, params=params, json=body,
				headers=headers, timeout=(5, 15))
			break
		except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as error:
			if attempt + 1 >= attempts: raise FloppySyncError(str(error))
			_session.close()
			if _wait(1): raise FloppySyncError('Floppy sync aborted')
	if response is None: raise FloppySyncError('Floppy request did not return a response')
	status = response.status_code
	try: payload = response.json()
	except Exception: payload = None
	if status in (404, 405): raise FloppyRouteUnavailable('Fast-sync route is unavailable', status=status)
	if status == 409:
		code = payload.get('code') if isinstance(payload, dict) else None
		reason = payload.get('reason') if isinstance(payload, dict) else None
		message = payload.get('detail') if isinstance(payload, dict) else 'Floppy sync conflict'
		if code == 'cursor_expired':
			raise FloppyCursorExpired(message, status=status, code=code, reason=reason)
		if code == 'connection_inactive':
			raise FloppyConnectionInactive(message, status=status, code=code, reason=reason)
		raise FloppySyncError(message, status=status, code=code, reason=reason)
	if status == 429:
		retry_after = response.headers.get('Retry-After')
		try: retry_after = int(retry_after)
		except Exception: retry_after = None
		raise FloppySyncError('Floppy throttled fast sync', status=status, retry_after=retry_after)
	if status < 200 or status >= 300:
		code = payload.get('code') if isinstance(payload, dict) else None
		reason = payload.get('reason') if isinstance(payload, dict) else None
		message = payload.get('detail') if isinstance(payload, dict) else 'Floppy HTTP %s' % status
		retry_after = response.headers.get('Retry-After')
		raise FloppySyncError(message, status=status, code=code, reason=reason, retry_after=retry_after)
	if not isinstance(payload, dict): raise FloppySyncError('Floppy returned malformed JSON')
	return payload


def _instance_key():
	return floppysync.get_or_create_sync_state('instance_key', lambda: uuid.uuid4().hex)


def _ensure_registered(force=False):
	identity = '%s|%s' % (_base_url(), _instance_key())
	origin = floppysync.get_sync_state('origin_key')
	if origin and not force and floppysync.get_sync_state('registered_identity') == identity:
		return origin
	data = _sync_request('POST', '/sync/connections/',
		body={'instance_key': _instance_key(), 'label': 'Umbrella'}, retry_post=True)
	origin = str(data.get('origin_key') or '').strip()
	if not origin: raise FloppySyncError('Floppy registration omitted origin_key')
	floppysync.set_sync_state('registered_identity', identity)
	floppysync.set_sync_state('origin_key', origin)
	if data.get('resnapshot_required'):
		floppysync.reset_sync_cursors('watched')
	return origin


def _positive_int(value, name, allow_zero=True):
	if isinstance(value, bool): raise ValueError('%s must be an integer' % name)
	try: result = int(value)
	except Exception: raise ValueError('%s must be an integer' % name)
	if str(result) != str(value).strip() and not isinstance(value, int): raise ValueError('%s must be an integer' % name)
	if result < (0 if allow_zero else 1): raise ValueError('%s is out of range' % name)
	return result


def _ids(row):
	ids = row.get('ids')
	if not isinstance(ids, dict): raise ValueError('sync row ids must be an object')
	return ids


def _watched_row(row):
	if not isinstance(row, dict): raise ValueError('watched row must be an object')
	if row.get('numbering') == 'custom' or row.get('episode_order_id') is not None: return None
	ids = _ids(row)
	media_type = row.get('media_type')
	ts = str(row.get('watched_at') or row.get('last_watched_at') or '')
	if media_type == 'movie':
		tmdb = str(ids.get('tmdb') or row.get('media_id') or '').strip()
		if not tmdb or not tmdb.isdigit(): raise ValueError('movie row needs TMDB id')
		return ('movie', (str(ids.get('imdb') or ''), tmdb, str(row.get('title') or ''),
			str(row.get('year') or ''), ts))
	if media_type == 'episode':
		tmdb = str(ids.get('tmdb') or '').strip()
		if not tmdb or not tmdb.isdigit(): raise ValueError('episode row needs show TMDB id')
		season = _positive_int(row.get('season_number'), 'season')
		episode = _positive_int(row.get('episode_number'), 'episode', allow_zero=False)
		return ('episode', (str(ids.get('imdb') or ''), tmdb, str(ids.get('tvdb') or ''), season, episode, ts))
	return None


def _watched_change(event):
	normalized = _watched_row(event)
	if normalized is None: return None
	media_type, row = normalized
	watched = bool(event.get('watched')) and event.get('kind') != 'delete'
	if media_type == 'movie': return ('upsert_movie', row) if watched else ('delete_movie', row[1])
	return ('upsert_episode', row) if watched else ('delete_episode', (row[1], row[3], row[4]))


def _fetch_watched_snapshot(connection, max_pages=50):
	movies, episodes = {}, {}
	page_cursor, resume_cursor = None, None
	for _page in range(max_pages):
		params = {'connection': connection, 'limit': 1000}
		if page_cursor is not None:
			params.update({'cursor': page_cursor, 'resume_cursor': resume_cursor})
		data = _sync_request('GET', '/sync/watched-state/', params=params)
		if not isinstance(data.get('results'), list): raise FloppySyncError('Snapshot results are malformed')
		if resume_cursor is None: resume_cursor = _positive_int(data.get('resume_cursor'), 'resume_cursor')
		elif _positive_int(data.get('resume_cursor'), 'resume_cursor') != resume_cursor:
			raise FloppySyncError('Snapshot resume cursor changed')
		for raw in data['results']:
			normalized = _watched_row(raw)
			if normalized is None: continue
			kind, row = normalized
			if kind == 'movie': movies[row[1]] = row
			else: episodes[(row[1], row[3], row[4])] = row
		next_cursor = _positive_int(data.get('next_cursor'), 'next_cursor')
		if data.get('has_more') and next_cursor == page_cursor: raise FloppySyncError('Snapshot cursor did not advance')
		page_cursor = next_cursor
		if not data.get('has_more'): return list(movies.values()), list(episodes.values()), resume_cursor
	raise FloppySyncError('Snapshot exceeded page limit')


def _sync_watched_once(connection, force_snapshot=False, max_pages=200):
	cursor = floppysync.get_sync_state('watched_cursor')
	changed = 0
	if force_snapshot or cursor is None:
		movies, episodes, resume = _fetch_watched_snapshot(connection)
		floppysync.replace_watched_snapshot(movies, episodes, resume, expected_cursor=cursor)
		cursor = str(resume)
		changed += len(movies) + len(episodes)
	for _page in range(max_pages):
		data = _sync_request('GET', '/sync/changes/', params={'connection': connection, 'cursor': cursor, 'limit': 200})
		results = data.get('results')
		if not isinstance(results, list): raise FloppySyncError('Change results are malformed')
		ops = []
		for event in results:
			op = _watched_change(event)
			if op is not None: ops.append(op)
		next_cursor = _positive_int(data.get('next_cursor'), 'next_cursor')
		if data.get('has_more') and str(next_cursor) == str(cursor): raise FloppySyncError('Change cursor did not advance')
		changed += floppysync.apply_watched_changes(ops, cursor, next_cursor)
		cursor = str(next_cursor)
		if not data.get('has_more'): return changed
	raise FloppySyncError('Change feed exceeded page limit')


def sync_watched_fast(force_snapshot=False):
	resnapshots = 0
	while True:
		connection = _ensure_registered()
		try: return _sync_watched_once(connection, force_snapshot=force_snapshot or resnapshots > 0)
		except FloppyConnectionInactive as error:
			if error.reason != 'missing' or resnapshots: raise
			floppysync.set_sync_state('origin_key', '')
			floppysync.set_sync_state('registered_identity', '')
			_ensure_registered(force=True)
			resnapshots += 1
		except FloppyCursorExpired:
			if resnapshots: raise
			floppysync.reset_sync_cursors('watched')
			resnapshots += 1


def _bookmark_row(row):
	if not isinstance(row, dict): raise ValueError('progress row must be an object')
	if row.get('numbering') == 'custom' or row.get('episode_order_id') is not None: return None
	if row.get('completed'): return None
	ids = _ids(row)
	duration = row.get('duration_seconds') or 0
	position = row.get('position_seconds') or 0
	try: duration, position = float(duration), float(position)
	except Exception: raise ValueError('progress duration/position must be numeric')
	if duration <= 0: return None
	tmdb = str(ids.get('tmdb') or row.get('media_id') or '').strip()
	if not tmdb or not tmdb.isdigit(): raise ValueError('progress row needs TMDB id')
	season = episode = ''
	if row.get('media_type') == 'episode':
		season = str(_positive_int(row.get('season_number'), 'season'))
		episode = str(_positive_int(row.get('episode_number'), 'episode', allow_zero=False))
	elif row.get('media_type') != 'movie': return None
	percent = str(round((position / duration) * 100, 2))
	return (str(row.get('series_title') or ''), str(row.get('title') or ''), tmdb,
		str(ids.get('imdb') or ''), tmdb, str(ids.get('tvdb') or ''), season, episode,
		'', '', '', str(duration), percent, str(row.get('updated_at') or ''))


def _strict_progress_snapshot():
	rows, offset = [], 0
	for _page in range(100):
		data = _sync_request('GET', '/playback/progress/', params={'limit': 200, 'offset': offset})
		results = data.get('results')
		if not isinstance(results, list): raise FloppySyncError('Progress snapshot is malformed')
		for raw in results:
			row = _bookmark_row(raw)
			if row is not None: rows.append(row)
		pagination = data.get('pagination')
		if not isinstance(pagination, dict): raise FloppySyncError('Progress pagination is malformed')
		if not pagination.get('next'): return rows
		if not results: raise FloppySyncError('Progress pagination did not advance')
		offset += len(results)
	raise FloppySyncError('Progress snapshot exceeded page limit')


def _progress_op(event):
	if not isinstance(event, dict): raise ValueError('progress event must be an object')
	if event.get('numbering') == 'custom' or event.get('episode_order_id') is not None: return None
	row = _bookmark_row(event)
	ids = _ids(event)
	tmdb = str(ids.get('tmdb') or event.get('media_id') or '').strip()
	season = '' if event.get('media_type') == 'movie' else str(_positive_int(event.get('season_number'), 'season'))
	episode = '' if event.get('media_type') == 'movie' else str(_positive_int(event.get('episode_number'), 'episode', allow_zero=False))
	if event.get('kind') == 'delete' or row is None: return ('delete', (tmdb, season, episode))
	return ('upsert', row)


def _sync_progress_once(force_snapshot=False):
	connection = _ensure_registered()
	cursor = floppysync.get_sync_state('progress_cursor')
	changed = 0
	if force_snapshot or cursor is None:
		meta = _sync_request('GET', '/sync/progress-changes/', params={'cursor': 0, 'limit': 1})
		resume = _positive_int(meta.get('newest_sequence') or 0, 'newest_sequence')
		rows = _strict_progress_snapshot()
		floppysync.replace_progress_snapshot(rows, resume, expected_cursor=cursor)
		cursor = str(resume)
		changed += len(rows)
	for _page in range(100):
		data = _sync_request('GET', '/sync/progress-changes/', params={'connection': connection, 'cursor': cursor, 'limit': 500})
		results = data.get('results')
		if not isinstance(results, list): raise FloppySyncError('Progress changes are malformed')
		ops = []
		for event in results:
			op = _progress_op(event)
			if op is not None: ops.append(op)
		next_cursor = _positive_int(data.get('next_cursor'), 'next_cursor')
		if data.get('has_more') and str(next_cursor) == str(cursor): raise FloppySyncError('Progress cursor did not advance')
		changed += floppysync.apply_progress_changes(ops, cursor, next_cursor)
		cursor = str(next_cursor)
		if not data.get('has_more'): return changed
	raise FloppySyncError('Progress feed exceeded page limit')


def sync_progress_fast(force_snapshot=False):
	resnapshots = 0
	while True:
		try: return _sync_progress_once(force_snapshot=force_snapshot or resnapshots > 0)
		except FloppyCursorExpired:
			if resnapshots: raise
			floppysync.reset_sync_cursors('progress')
			resnapshots += 1
		except FloppyConnectionInactive as error:
			if error.reason != 'missing' or resnapshots: raise
			floppysync.set_sync_state('origin_key', '')
			floppysync.set_sync_state('registered_identity', '')
			_ensure_registered(force=True)
			floppysync.reset_sync_cursors('progress')
			resnapshots += 1


def sync_background():
	try:
		changed = sync_watched_fast()
		if control.setting('bookmarks') == 'true' and control.setting('scrobble.source') == '5':
			changed += sync_progress_fast()
		if changed:
			try: playing = control.player.isPlaying()
			except Exception: playing = False
			if not playing: control.trigger_widget_refresh()
		return changed
	except Exception as error:
		log_utils.log('FLOPPY: fast background sync failed; cached state retained: %s' % error,
			level=log_utils.LOGWARNING)
		return 0
