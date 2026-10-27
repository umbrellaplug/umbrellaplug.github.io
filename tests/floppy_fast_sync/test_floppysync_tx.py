# -*- coding: utf-8 -*-
"""Task 3: transactional watched cache in floppysync.py (stdlib unittest, no Kodi)."""
import os
import shutil
import sqlite3
import tempfile
import unittest

from tests.floppy_fast_sync import kodi_stubs

CONTROL, LOG = kodi_stubs.install('matrix')
from resources.lib.database import floppysync

EPOCH = '1970-01-01T00:00:00.000Z'
SENTINEL = '2001-02-03T04:05:06.000Z'

def movie(tmdb, imdb='', title='', year='2020', at='2024-01-01T00:00:00.000Z'):
	return (imdb, str(tmdb), title or 'Movie %s' % tmdb, year, at)

def episode(show_tmdb, season, ep, show_imdb='', show_tvdb='', at='2024-01-01T00:00:00.000Z'):
	return (show_imdb, str(show_tmdb), show_tvdb, season, ep, at)


class TxTestCase(unittest.TestCase):
	def setUp(self):
		self.tmp = tempfile.mkdtemp(prefix='floppysync-test-')
		self.path = os.path.join(self.tmp, 'floppysync.db')
		CONTROL.floppySyncFile = self.path
		floppysync.floppySyncFile = self.path
		del LOG.errors[:]
		self.addCleanup(shutil.rmtree, self.tmp, True)

	def raw(self):
		con = sqlite3.connect(self.path)
		self.addCleanup(con.close)
		return con

	def query(self, sql, args=(), table=None):
		# An empty result is only legitimate when sqlite_master confirms `table` is absent; any other
		# error (locked, bad column, corrupt) propagates so state comparisons can't pass vacuously.
		con = self.raw()
		try: return con.execute(sql, args).fetchall()
		except sqlite3.OperationalError:
			if table and not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone(): return []
			raise

	def movies(self):
		return sorted(self.query('SELECT imdb, tmdb, title, year, last_watched_at FROM floppy_watched_movies', table='floppy_watched_movies'))

	def episodes(self):
		return sorted(self.query('SELECT show_imdb, show_tmdb, show_tvdb, season, episode, last_watched_at FROM floppy_watched_episodes', table='floppy_watched_episodes'))

	def service(self, key):
		rows = self.query('SELECT value FROM service WHERE setting=?', (key,), table='service')
		return rows[0][0] if rows else None

	def state(self, key):
		rows = self.query('SELECT value FROM floppy_sync_state WHERE key=?', (key,), table='floppy_sync_state')
		return rows[0][0] if rows else None

	def cursor(self):
		return self.state('watched_cursor')

	def seed_service(self, value=SENTINEL):
		con = self.raw()
		con.execute('CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting))')
		con.execute('INSERT OR REPLACE INTO service VALUES (?, ?)', ('last_history_at', value))
		con.commit()

	def seed_cache(self):
		con = self.raw()
		con.execute('CREATE TABLE IF NOT EXISTS watched (key TEXT, value TEXT, date INTEGER, UNIQUE(key))')
		con.execute('INSERT OR REPLACE INTO watched VALUES (?, ?, ?)', ('k', 'v', 1))
		con.commit()

	def cache_rows(self):
		return self.query('SELECT key FROM watched', table='watched')

	def add_failure_trigger(self, table, column, value):
		# Fails inside the transaction, after earlier statements already ran.
		con = self.raw()
		con.execute("CREATE TRIGGER boom BEFORE INSERT ON %s WHEN NEW.%s = '%s' BEGIN SELECT RAISE(ABORT, 'boom'); END" % (table, column, value))
		con.commit()

	def snapshot_state(self):
		return (self.movies(), self.episodes(), self.cursor(), self.service('last_history_at'), self.cache_rows())


class SnapshotTests(TxTestCase):
	def test_snapshot_into_empty_database_stores_rows_and_cursor(self):
		self.seed_cache()
		ok = floppysync.replace_watched_snapshot([movie(1, 'tt1')], [episode(10, 1, 2, 'tt10', '99')], 42)
		self.assertTrue(ok)
		self.assertEqual(self.movies(), [movie(1, 'tt1')])
		self.assertEqual(self.episodes(), [episode(10, 1, 2, 'tt10', '99')])
		self.assertEqual(self.cursor(), '42')
		self.assertNotEqual(self.service('last_history_at'), None)
		self.assertEqual(self.cache_rows(), [])

	def test_snapshot_replaces_existing_rows_and_drops_stale(self):
		floppysync.replace_watched_snapshot([movie(1, 'tt1'), movie(2, 'tt2')], [episode(10, 1, 1), episode(10, 1, 2)], 5)
		ok = floppysync.replace_watched_snapshot([movie(2, 'tt2', title='New')], [episode(10, 1, 2)], 9, expected_cursor=5)
		self.assertTrue(ok)
		self.assertEqual(self.movies(), [movie(2, 'tt2', title='New')])
		self.assertEqual(self.episodes(), [episode(10, 1, 2)])
		self.assertEqual(self.cursor(), '9')

	def test_snapshot_carries_imdb_forward_for_same_tmdb(self):
		floppysync.replace_watched_snapshot([movie(1, 'tt1')], [episode(10, 1, 1, 'tt10')], 5)
		floppysync.replace_watched_snapshot([movie(1, ''), movie(3, '')], [episode(10, 1, 1, ''), episode(10, 1, 2, '')], 6, expected_cursor=5)
		self.assertEqual(self.movies(), sorted([movie(1, 'tt1'), movie(3, '')]))
		self.assertEqual(self.episodes(), [episode(10, 1, 1, 'tt10'), episode(10, 1, 2, 'tt10')])

	def test_snapshot_incoming_imdb_wins_over_existing(self):
		floppysync.replace_watched_snapshot([movie(1, 'tt1')], [], 5)
		floppysync.replace_watched_snapshot([movie(1, 'tt9')], [], 6, expected_cursor=5)
		self.assertEqual(self.movies(), [movie(1, 'tt9')])

	def test_snapshot_coerces_types_like_existing_helpers(self):
		floppysync.replace_watched_snapshot([('tt1', 7, 'M', 2020, 'x')], [('', 10, 5, '3', '4', 'x')], 1)
		self.assertEqual(self.movies(), [('tt1', '7', 'M', '2020', 'x')])
		self.assertEqual(self.episodes(), [('', '10', '5', 3, 4, 'x')])

	def test_failed_snapshot_midway_preserves_rows_cursor_service_and_cache(self):
		floppysync.replace_watched_snapshot([movie(1, 'tt1')], [episode(10, 1, 1)], 5)
		self.seed_service()
		self.seed_cache()
		before = self.snapshot_state()
		self.add_failure_trigger('floppy_watched_movies', 'title', 'BOOM')
		with self.assertRaises(sqlite3.Error):
			floppysync.replace_watched_snapshot([movie(2), movie(3, title='BOOM')], [episode(11, 1, 1)], 99, expected_cursor=5)
		self.assertEqual(self.snapshot_state(), before)
		self.assertEqual(before[2], '5')

	def test_malformed_snapshot_row_preserves_everything(self):
		floppysync.replace_watched_snapshot([movie(1, 'tt1')], [episode(10, 1, 1)], 5)
		self.seed_service()
		before = self.snapshot_state()
		with self.assertRaises((ValueError, TypeError)):
			floppysync.replace_watched_snapshot([movie(2)], [episode(10, 'x', 1)], 6, expected_cursor=5)
		self.assertEqual(self.snapshot_state(), before)

	def test_snapshot_requires_integer_cursor(self):
		with self.assertRaises((ValueError, TypeError)):
			floppysync.replace_watched_snapshot([movie(1)], [], 'abc')
		with self.assertRaises((ValueError, TypeError)):
			floppysync.replace_watched_snapshot([movie(1)], [], None)
		self.assertEqual(self.movies(), [])

	def test_snapshot_compare_and_swap(self):
		floppysync.replace_watched_snapshot([movie(1, 'tt1')], [], 5)
		self.seed_service()
		before = self.snapshot_state()
		with self.assertRaises(floppysync.CursorMismatch):
			floppysync.replace_watched_snapshot([movie(2)], [], 9, expected_cursor=4)
		with self.assertRaises(floppysync.CursorMismatch):
			floppysync.replace_watched_snapshot([movie(2)], [], 9)  # None expects no stored cursor
		self.assertEqual(self.snapshot_state(), before)
		self.assertTrue(floppysync.replace_watched_snapshot([movie(2)], [], 9, expected_cursor='5'))
		self.assertEqual(self.cursor(), '9')

	def test_identical_snapshot_advances_cursor_without_touching_history_or_cache(self):
		floppysync.replace_watched_snapshot([movie(1, 'tt1')], [episode(10, 1, 1)], 5)
		self.seed_service()
		self.seed_cache()
		ok = floppysync.replace_watched_snapshot([movie(1, 'tt1')], [episode(10, 1, 1)], 8, expected_cursor=5)
		self.assertTrue(ok)
		self.assertEqual(self.cursor(), '8')
		self.assertEqual(self.service('last_history_at'), SENTINEL)
		self.assertEqual(self.cache_rows(), [('k',)])

	def test_changed_snapshot_bumps_history_and_clears_cache(self):
		floppysync.replace_watched_snapshot([movie(1, 'tt1')], [], 5)
		self.seed_service()
		self.seed_cache()
		floppysync.replace_watched_snapshot([movie(1, 'tt1'), movie(2)], [], 6, expected_cursor=5)
		self.assertNotEqual(self.service('last_history_at'), SENTINEL)
		self.assertEqual(self.cache_rows(), [])


class DeltaTests(TxTestCase):
	def setUp(self):
		TxTestCase.setUp(self)
		floppysync.replace_watched_snapshot([movie(1, 'tt1'), movie(2, 'tt2')], [episode(10, 1, 1, 'tt10'), episode(10, 1, 2, 'tt10')], 5)
		self.seed_service()
		self.seed_cache()

	def test_upsert_and_delete_in_feed_order_advance_cursor(self):
		ops = [
			('upsert_movie', movie(3, 'tt3')),
			('delete_movie', '1'),
			('upsert_episode', episode(11, 2, 3, 'tt11')),
			('delete_episode', ('10', 1, 1)),
		]
		changed = floppysync.apply_watched_changes(ops, 5, 8)
		self.assertEqual(changed, 4)
		self.assertEqual(self.movies(), [movie(2, 'tt2'), movie(3, 'tt3')])
		self.assertEqual(self.episodes(), [episode(10, 1, 2, 'tt10'), episode(11, 2, 3, 'tt11')])
		self.assertEqual(self.cursor(), '8')
		self.assertNotEqual(self.service('last_history_at'), SENTINEL)
		self.assertEqual(self.cache_rows(), [])

	def test_upsert_then_delete_same_key_leaves_it_absent(self):
		ops = [('upsert_movie', movie(7, 'tt7')), ('delete_movie', 7), ('upsert_episode', episode(12, 1, 1)), ('delete_episode', (12, '1', '1'))]
		floppysync.apply_watched_changes(ops, 5, 6)
		self.assertEqual(self.movies(), [movie(1, 'tt1'), movie(2, 'tt2')])
		self.assertEqual(self.episodes(), [episode(10, 1, 1, 'tt10'), episode(10, 1, 2, 'tt10')])

	def test_delete_then_upsert_same_key_leaves_it_present(self):
		floppysync.apply_watched_changes([('delete_movie', 1), ('upsert_movie', movie(1, 'tt1', title='Again'))], 5, 6)
		self.assertEqual(self.movies(), [movie(1, 'tt1', title='Again'), movie(2, 'tt2')])

	def test_movie_upsert_keeps_existing_imdb_when_blank(self):
		floppysync.apply_watched_changes([('upsert_movie', movie(1, '', title='Renamed', at='2025-05-05T00:00:00.000Z'))], 5, 6)
		self.assertEqual(self.movies()[0], ('tt1', '1', 'Renamed', '2020', '2025-05-05T00:00:00.000Z'))

	def test_episode_upsert_keeps_show_imdb_when_blank(self):
		floppysync.apply_watched_changes([('upsert_episode', episode(10, 1, 3, ''))], 5, 6)
		self.assertIn(episode(10, 1, 3, 'tt10'), self.episodes())

	def test_failed_delta_rolls_back_whole_page_and_keeps_cursor(self):
		before = self.snapshot_state()
		self.add_failure_trigger('floppy_watched_movies', 'title', 'BOOM')
		ops = [('delete_movie', 1), ('upsert_episode', episode(13, 1, 1)), ('upsert_movie', movie(9, title='BOOM'))]
		with self.assertRaises(sqlite3.Error):
			floppysync.apply_watched_changes(ops, 5, 9)
		self.assertEqual(self.snapshot_state(), before)

	def test_malformed_or_unknown_op_rolls_back_and_keeps_cursor(self):
		before = self.snapshot_state()
		with self.assertRaises((ValueError, TypeError, KeyError)):
			floppysync.apply_watched_changes([('delete_movie', 1), ('upsert_episode', episode(13, 'x', 1))], 5, 9)
		with self.assertRaises((ValueError, TypeError, KeyError)):
			floppysync.apply_watched_changes([('delete_movie', 1), ('explode', 1)], 5, 9)
		self.assertEqual(self.snapshot_state(), before)

	def test_delta_compare_and_swap(self):
		before = self.snapshot_state()
		with self.assertRaises(floppysync.CursorMismatch):
			floppysync.apply_watched_changes([('delete_movie', 1)], 4, 9)
		self.assertEqual(self.snapshot_state(), before)
		self.assertEqual(LOG.errors, [])

	def test_delta_requires_baseline_cursor_and_forward_movement(self):
		before = self.snapshot_state()
		with self.assertRaises((ValueError, TypeError)):
			floppysync.apply_watched_changes([], None, 9)
		with self.assertRaises((ValueError, TypeError)):
			floppysync.apply_watched_changes([], 5, 4)
		self.assertEqual(self.snapshot_state(), before)

	def test_delta_without_snapshot_cursor_is_refused(self):
		os.remove(self.path)
		with self.assertRaises(floppysync.CursorMismatch):
			floppysync.apply_watched_changes([('upsert_movie', movie(1))], 5, 6)
		self.assertEqual(self.movies(), [])

	def test_empty_delta_advances_cursor_only(self):
		self.assertEqual(floppysync.apply_watched_changes([], 5, 12), 0)
		self.assertEqual(self.cursor(), '12')
		self.assertEqual(self.service('last_history_at'), SENTINEL)
		self.assertEqual(self.cache_rows(), [('k',)])

	def test_redundant_delta_ops_do_not_count_as_data_change(self):
		ops = [('upsert_movie', movie(1, 'tt1')), ('delete_movie', 999), ('delete_episode', (999, 1, 1)), ('upsert_episode', episode(10, 1, 1, 'tt10'))]
		self.assertEqual(floppysync.apply_watched_changes(ops, 5, 6), 0)
		self.assertEqual(self.cursor(), '6')
		self.assertEqual(self.service('last_history_at'), SENTINEL)
		self.assertEqual(self.cache_rows(), [('k',)])

	def test_same_cursor_noop_is_allowed(self):
		self.assertEqual(floppysync.apply_watched_changes([], 5, 5), 0)
		self.assertEqual(self.cursor(), '5')


class JournalAndCompatTests(TxTestCase):
	def test_transaction_connection_uses_rollback_capable_journal(self):
		con = floppysync._tx_connection()
		try:
			self.assertEqual(con.execute('PRAGMA journal_mode').fetchone()[0].lower(), 'delete')
			self.assertEqual(con.execute('PRAGMA synchronous').fetchone()[0], 1)  # NORMAL
		finally: con.close()

	def test_get_connection_default_is_unchanged(self):
		con = floppysync.get_connection()
		try: self.assertEqual(con.execute('PRAGMA journal_mode').fetchone()[0].lower(), 'off')
		finally: con.close()

	def test_no_vacuum_or_modern_sqlite_syntax_in_new_code(self):
		import inspect
		for name in ('_tx_connection', 'get_sync_state', 'set_sync_state', 'get_or_create_sync_state', 'clear_sync_state',
				'reset_sync_cursors', 'replace_watched_snapshot', 'apply_watched_changes', '_reset_cursor_tables'):
			source = inspect.getsource(getattr(floppysync, name)).upper()
			for banned in ('VACUUM', 'ON CONFLICT', 'RETURNING', 'STRICT'):
				self.assertNotIn(banned, source, '%s uses %s' % (name, banned))

	def test_existing_helpers_work_after_transactional_write(self):
		floppysync.replace_watched_snapshot([movie(1, 'tt1')], [episode(10, 1, 1, 'tt10', '5')], 3)
		floppysync.upsert_watched_movie('tt2', 2, 'Two', 2021, 'x')
		floppysync.delete_watched_episode(10, 1, 1)
		floppysync.upsert_watched_episode('tt11', 11, '6', 2, 2, 'y')
		floppysync.upsert_bookmark(title='T', imdb='tt1', tmdb='1', percent_played='10', duration='100')
		self.assertEqual(sorted(floppysync.get_watched_movies()), ['tt1', 'tt2'])
		self.assertEqual(len(floppysync.get_watched_movies_full()), 2)
		self.assertEqual(floppysync.get_watched_episodes(), [('tt11', '11', '6', 2, 2)])
		self.assertEqual(floppysync.get_watched_shows()[0][1], '11')
		self.assertEqual(floppysync.fetch_bookmarks('tt1', tmdb='1'), '10')
		self.assertEqual(LOG.errors, [])

	def test_snapshot_and_delta_work_after_existing_helpers(self):
		floppysync.upsert_watched_movie('tt2', 2, 'Two', 2021, 'x')
		self.assertTrue(floppysync.replace_watched_snapshot([movie(1)], [], 1))
		self.assertEqual(floppysync.apply_watched_changes([('upsert_movie', movie(5))], 1, 2), 1)
		self.assertEqual([m[1] for m in self.movies()], ['1', '5'])


class StateTests(TxTestCase):
	def test_sync_state_round_trip_and_default(self):
		self.assertIsNone(floppysync.get_sync_state('instance_key'))
		self.assertEqual(floppysync.get_sync_state('instance_key', 'd'), 'd')
		floppysync.set_sync_state('instance_key', 'abc')
		floppysync.set_sync_state('instance_key', 'def')
		self.assertEqual(floppysync.get_sync_state('instance_key'), 'def')

	def test_reset_sync_cursors_clears_watched_cursor_only(self):
		floppysync.replace_watched_snapshot([movie(1)], [], 7)
		floppysync.set_sync_state('instance_key', 'abc')
		floppysync.reset_sync_cursors()
		self.assertIsNone(self.cursor())
		self.assertEqual(floppysync.get_sync_state('instance_key'), 'abc')
		self.assertEqual(self.movies(), [movie(1)])

	def test_delete_floppy_tables_resets_cursor_for_watched_tables(self):
		for tables in (('floppy_watched_movies',), ('floppy_watched_episodes',), ('floppy_watched_movies', 'floppy_watched_episodes')):
			floppysync.replace_watched_snapshot([movie(1)], [episode(10, 1, 1)], 7, expected_cursor=self.cursor())
			floppysync.set_sync_state('instance_key', 'abc')
			floppysync.delete_floppy_tables(tables)
			self.assertIsNone(self.cursor(), tables)
			self.assertEqual(floppysync.get_sync_state('instance_key'), 'abc')
			self.assertEqual(self.service('last_history_at'), EPOCH)

	def test_delete_floppy_tables_for_other_tables_keeps_cursor(self):
		floppysync.replace_watched_snapshot([movie(1)], [], 7)
		floppysync.delete_floppy_tables(('floppy_watchlist',))
		self.assertEqual(self.cursor(), '7')
		self.assertEqual(self.movies(), [movie(1)])

	def test_delete_floppy_tables_without_state_table_still_works(self):
		floppysync.upsert_watched_movie('tt1', 1, 'One', 2020, 'x')
		floppysync.delete_floppy_tables(('floppy_watched_movies',))
		self.assertEqual(self.movies(), [])
		self.assertEqual(LOG.errors, [])

	def test_snapshot_after_clear_accepts_fresh_cursor(self):
		floppysync.replace_watched_snapshot([movie(1)], [], 7)
		floppysync.delete_floppy_tables(('floppy_watched_movies', 'floppy_watched_episodes'))
		self.assertTrue(floppysync.replace_watched_snapshot([movie(2)], [], 3))
		self.assertEqual(self.cursor(), '3')


if __name__ == '__main__':
	unittest.main()
