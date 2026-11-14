"""Defer HTTP imports and pools until a cached browse actually needs a request."""
from importlib import import_module
from threading import Lock


class LazyModule:
	def __init__(self, name):
		self._name = name

	def __getattr__(self, name):
		return getattr(import_module(self._name), name)


requests = LazyModule('requests')


def HTTPAdapter(*args, **kwargs):
	return import_module('requests.adapters').HTTPAdapter(*args, **kwargs)


class LazySession:
	def __init__(self, retry_options=None, prefixes=(), pool_maxsize=100):
		self._session = None
		self._lock = Lock()
		self._headers = {}
		self._retry_options = retry_options
		self._prefixes = tuple(prefixes)
		self._pool_maxsize = pool_maxsize

	def _ready(self):
		if self._session is None:
			with self._lock:
				if self._session is None:
					session = import_module('requests').Session()
					try:
						session.headers.update(self._headers)
						if self._retry_options is not None:
							retry = import_module('urllib3.util.retry').Retry(**self._retry_options)
							for prefix in self._prefixes:
								session.mount(prefix, HTTPAdapter(max_retries=retry, pool_maxsize=self._pool_maxsize))
					except BaseException:
						session.close()
						raise
					self._session = session
		return self._session

	@property
	def headers(self):
		return self._headers if self._session is None else self._session.headers

	@headers.setter
	def headers(self, value):
		if self._session is None: self._headers = value
		else: self._session.headers = value

	def close(self):
		if self._session is not None: return self._session.close()

	def __getattr__(self, name):
		return getattr(self._ready(), name)

	def __enter__(self):
		self._ready().__enter__()
		return self

	def __exit__(self, *args):
		return self._ready().__exit__(*args)
