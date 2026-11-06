"""Briefly share successful menu activity probes between Kodi invocations."""
from hashlib import sha256
from json import dumps, loads
from time import time
from uuid import uuid4
from resources.lib.modules import control

_VALUE = 'umbrella.trakt.browse_activities'
_GENERATION = 'umbrella.trakt.browse_activities.generation'
_RETRY = 'umbrella.trakt.browse_activities.retry'
_TTL = 15


def invalidate():
	# A new generation also rejects a response from an already-running request.
	try:
		control.homeWindow.setProperty(_GENERATION, uuid4().hex)
		control.homeWindow.clearProperty(_VALUE)
	except Exception:
		pass


def get(fetch, account, fresh=False):
	scope = sha256(account.encode('utf-8')).hexdigest()
	marker = None
	try:
		if fresh: invalidate()
		retry = loads(control.homeWindow.getProperty(_RETRY) or '{}')
		if retry.get('scope') == scope and time() < retry.get('until', 0):
			return None
		marker = control.homeWindow.getProperty(_GENERATION)
		if not marker:
			invalidate()
			marker = control.homeWindow.getProperty(_GENERATION)
		if not fresh and marker:
			entry = loads(control.homeWindow.getProperty(_VALUE) or '{}')
			age = time() - entry.get('stored', 0)
			if (entry.get('scope') == scope and entry.get('generation') == marker
					and 0 <= age < _TTL and _valid(entry.get('activities'))):
				return entry['activities']
	except Exception:
		pass
	result = fetch()
	try:
		if marker and _valid(result) and control.homeWindow.getProperty(_GENERATION) == marker:
			control.homeWindow.setProperty(_VALUE, dumps(dict(scope=scope, generation=marker,
				stored=time(), activities=result)))
	except Exception:
		pass
	return result


def defer(account, seconds):
	"""Honor server throttling without blocking the directory request."""
	try:
		control.homeWindow.setProperty(_RETRY, dumps(dict(
			scope=sha256(account.encode('utf-8')).hexdigest(), until=time() + max(0, seconds))))
	except Exception: pass


def is_visible_reload():
	# A request for the already-visible path may be a native Kodi refresh.
	# Conservatively bypass reuse: a false positive only costs another probe.
	try:
		from sys import argv
		from urllib.parse import urlsplit, parse_qsl
		if len(argv) < 3 or int(argv[1]) < 0: return False
		requested = urlsplit(argv[0] + argv[2])
		visible = urlsplit(control.infoLabel('Container.FolderPath'))
		return (requested.scheme == visible.scheme == 'plugin'
			and requested.netloc == visible.netloc == 'plugin.video.umbrella'
			and requested.path.rstrip('/') == visible.path.rstrip('/')
			and sorted(parse_qsl(requested.query)) == sorted(parse_qsl(visible.query)))
	except Exception:
		return False


def _valid(value):
	if not isinstance(value, dict) or not isinstance(value.get('all'), str) or not value['all']: return False
	fields = dict(movies=('watched_at', 'collected_at', 'watchlisted_at', 'paused_at', 'hidden_at'),
		episodes=('watched_at', 'collected_at', 'watchlisted_at', 'paused_at'),
		shows=('watchlisted_at', 'hidden_at'), seasons=('watchlisted_at', 'hidden_at'),
		lists=('liked_at', 'updated_at'))
	return all(isinstance(value.get(section), dict)
		and all(isinstance(value[section].get(field), str) and value[section][field]
			for field in required) for section, required in fields.items())
