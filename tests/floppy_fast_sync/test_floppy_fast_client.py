# -*- coding: utf-8 -*-
import importlib
import sys
import types
import unittest

from tests.floppy_fast_sync import kodi_stubs


class FastSyncClientTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		if 'resources.lib.modules.control' in sys.modules:
			cls.control = sys.modules['resources.lib.modules.control']
			cls.log = sys.modules['resources.lib.modules.log_utils']
		else:
			cls.control, cls.log = kodi_stubs.install()
		cls.settings = {
			'floppy.baseurl': 'https://floppy.example',
			'floppy.token': 'not-a-real-token',
			'bookmarks': 'false',
			'scrobble.source': '0',
		}
		cls.control.setting = lambda key: cls.settings.get(key, '')
		cls.control.sleep = lambda value: None
		cls.control.trigger_widget_refresh = lambda: None
		cls.control.monitor = types.SimpleNamespace(abortRequested=lambda: False, waitForAbort=lambda seconds: False)
		cls.control.player = types.SimpleNamespace(isPlaying=lambda: False)
		for name in ('resources.lib.modules.floppy_fast_sync',):
			sys.modules.pop(name, None)
		cls.fast = importlib.import_module('resources.lib.modules.floppy_fast_sync')

	def setUp(self):
		self._saved = {}
		for owner, names in (
			(self.fast, ('_sync_request', '_ensure_registered')),
			(self.fast.floppysync, ('get_or_create_sync_state', 'get_sync_state', 'set_sync_state',
				'reset_sync_cursors', 'replace_watched_snapshot', 'apply_watched_changes')),
		):
			for name in names: self._saved[(owner, name)] = getattr(owner, name)

	def tearDown(self):
		for (owner, name), value in self._saved.items(): setattr(owner, name, value)

	def test_snapshot_rows_are_strict_and_custom_numbering_is_skipped(self):
		movie = self.fast._watched_row({
			'media_type': 'movie', 'media_id': '603', 'ids': {'tmdb': 603, 'imdb': 'tt0133093'},
			'title': 'The Matrix', 'watched_at': '2026-01-01T00:00:00Z',
		})
		self.assertEqual(movie[0], 'movie')
		self.assertEqual(movie[1][1], '603')
		episode = self.fast._watched_row({
			'media_type': 'episode', 'ids': {'tmdb': 103516, 'imdb': 'tt12327578'},
			'season_number': 4, 'episode_number': 10, 'watched_at': 'now', 'numbering': 'provider',
		})
		self.assertEqual(episode[1][1:5], ('103516', '', 4, 10))
		self.assertIsNone(self.fast._watched_row({
			'media_type': 'episode', 'ids': {'tmdb': 1}, 'season_number': 1,
			'episode_number': 1, 'numbering': 'custom', 'episode_order_id': 9,
		}))
		with self.assertRaises(ValueError):
			self.fast._watched_row({'media_type': 'episode', 'ids': {'tmdb': 1}, 'season_number': 1})

	def test_initial_snapshot_then_delta_uses_atomic_database_calls(self):
		state = {}
		calls = []
		self.fast.floppysync.get_or_create_sync_state = lambda key, factory: state.setdefault(key, factory())
		self.fast.floppysync.get_sync_state = lambda key, default=None: state.get(key, default)
		self.fast.floppysync.set_sync_state = lambda key, value: state.__setitem__(key, value)
		self.fast.floppysync.reset_sync_cursors = lambda which: state.pop(which + '_cursor', None)
		def replace(movies, episodes, cursor, expected_cursor=None):
			calls.append(('snapshot', len(movies), len(episodes), cursor, expected_cursor))
			state['watched_cursor'] = str(cursor)
			return True
		def apply(ops, old, new):
			calls.append(('delta', ops, str(old), str(new)))
			state['watched_cursor'] = str(new)
			return len(ops)
		self.fast.floppysync.replace_watched_snapshot = replace
		self.fast.floppysync.apply_watched_changes = apply
		responses = [
			{'origin_key': 'origin', 'resnapshot_required': True},
			{'results': [
				{'media_type': 'movie', 'media_id': '603', 'ids': {'tmdb': 603}, 'title': 'M', 'watched_at': 'a'},
				{'media_type': 'episode', 'ids': {'tmdb': 103516}, 'season_number': 1, 'episode_number': 1,
				 'watched_at': 'b', 'numbering': 'provider'},
			], 'next_cursor': 50, 'has_more': False, 'resume_cursor': 7},
			{'results': [
				{'sequence': 8, 'kind': 'upsert', 'watched': False, 'media_type': 'movie',
				 'media_id': '603', 'ids': {'tmdb': 603}},
			], 'next_cursor': 8, 'has_more': False},
		]
		self.fast._sync_request = lambda *args, **kwargs: responses.pop(0)
		changed = self.fast.sync_watched_fast()
		self.assertEqual(changed, 3)
		self.assertEqual(calls[0], ('snapshot', 1, 1, 7, None))
		self.assertEqual(calls[1][0], 'delta')
		self.assertEqual(calls[1][1][0], ('delete_movie', '603'))
		self.assertEqual(state['watched_cursor'], '8')

	def test_malformed_or_nonadvancing_page_is_not_applied(self):
		self.fast.floppysync.get_sync_state = lambda key, default=None: '4' if key == 'watched_cursor' else 'origin'
		self.fast._ensure_registered = lambda force=False: 'origin'
		applied = []
		self.fast.floppysync.apply_watched_changes = lambda *args: applied.append(args)
		self.fast._sync_request = lambda *args, **kwargs: {
			'results': [], 'next_cursor': 4, 'has_more': True,
		}
		with self.assertRaises(self.fast.FloppySyncError): self.fast.sync_watched_fast()
		self.assertEqual(applied, [])

	def test_background_service_never_calls_heavy_status_or_collection_sync(self):
		path = kodi_stubs.tree_file('matrix', 'modules/tools.py')
		with open(path, 'r') as handle: source = handle.read()
		block = source.split("if internets and not video_playing and floppy.getFloppyCredentialsInfo()", 1)[1]
		block = block.split("if control.monitor.abortRequested(): break", 1)[0]
		self.assertIn('floppy.sync_background()', block)
		self.assertNotIn('sync_watch_list', block)
		self.assertNotIn('sync_collection', block)
		self.assertNotIn('sync_watchedProgress', block)
		self.assertIn("getSetting('floppy.fastsync.auto') == 'true'", block)

	def test_automatic_fast_sync_has_an_explicit_safe_default_toggle(self):
		path = kodi_stubs.addon_root('matrix') + '/resources/settings.xml'
		with open(path, 'r') as handle: source = handle.read()
		self.assertIn('id="floppy.fastsync.auto"', source)
		fragment = source.split('id="floppy.fastsync.auto"', 1)[1].split('</setting>', 1)[0]
		self.assertIn('<default>false</default>', fragment)

	def test_forced_sync_does_not_clear_watched_cache_before_network_success(self):
		path = kodi_stubs.tree_file('matrix', 'modules/floppy.py')
		with open(path, 'r') as handle: source = handle.read()
		block = source.split('def force_floppySync():', 1)[1].split('#### Indicators', 1)[0]
		self.assertNotIn("'floppy_watched_movies'", block)
		self.assertNotIn("'floppy_watched_episodes'", block)
		self.assertIn('sync_watchedProgress(forced=True', block)


if __name__ == '__main__':
	unittest.main()
