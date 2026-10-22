"""Normalize playback metadata without depending on Kodi."""
from json import loads
from urllib.parse import unquote


def normalize(meta, **fallbacks):
	if isinstance(meta, str):
		try:
			meta = loads(meta)
		except (ValueError, TypeError):
			try:
				meta = loads(unquote(meta))
			except (ValueError, TypeError):
				meta = {}
	result = dict(meta) if isinstance(meta, dict) else {}
	for key, value in fallbacks.items():
		if result.get(key) in (None, '') and value not in (None, ''):
			result[key] = value
	return result
