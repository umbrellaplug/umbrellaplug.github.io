# -*- coding: utf-8 -*-
"""Task 3 remediation: atomic reset, identity state, crash recovery, real two-connection locking."""
import os
import sqlite3
import subprocess
import sys
import threading
import time
import unittest
from contextlib import contextmanager

from tests.floppy_fast_sync import kodi_stubs
from tests.floppy_fast_sync import test_floppysync_tx as base
from tests.floppy_fast_sync.test_floppysync_tx import LOG, SENTINEL, EPOCH, movie, episode

floppysync = base.floppysync
REPO_ROOT = kodi_stubs.REPO_ROOT


class _TimeoutDb(object):
	"""Stand-in for floppysync.db that forces a connect timeout (get_connection hard-codes 60 s)."""
	def __init__(self, timeout):
		self.timeout = timeout
	def connect(self, *args, **kwargs):
		kwargs['timeout'] = self.timeout
		return sqlite3.dbapi2.connect(*args, **kwargs)
	def __getattr__(self, name):
		return getattr(sqlite3.dbapi2, name)


class RemediationCase(base.TxTestCase):
	@contextmanager
	def busy_timeout(self, seconds):
		saved = floppysync.db
		floppysync.db = _TimeoutDb(seconds)
		try: yield
		finally: floppysync.db = saved

	def holder(self):
		# A second, independent connection that owns the write lock until commit()/rollback().
		con = sqlite3.connect(self.path, timeout=5, isolation_level=None)
		self.addCleanup(con.close)
		con.execute('BEGIN IMMEDIATE')
		return con

	def run_thread(self, func):
		box = {}
		def target():
			try: box['result'] = func()
			except BaseException as error: box['error'] = error
		thread = threading.Thread(target=target)
		thread.daemon = True
		thread.start()
		return thread, box

	def assert_blocked(self, thread, seconds=0.6):
		thread.join(seconds)
		self.assertTrue(thread.is_alive(), 'writer did not wait for the write lock')

	def finish(self, thread, box):
		thread.join(30)
		self.assertFalse(thread.is_alive(), 'writer never finished')
		return box

	def tmdbs(self):
		return sorted(m[1] for m in self.movies())

	def seed_user_state(self):
		con = self.raw()
		con.execute('CREATE TABLE IF NOT EXISTS floppy_sync_state (key TEXT PRIMARY KEY, value TEXT)')
		con.executemany('INSERT OR REPLACE INTO floppy_sync_state VALUES (?, ?)', [
			('instance_key', 'stable'), ('watched_cursor', '7'), ('progress_cursor', '11'),
			('registered_identity', 'user-a'), ('origin_key', 'origin-a')])
		con.commit()


class QueryHelperTests(RemediationCase):
	def test_query_returns_empty_only_for_absent_table(self):
		self.assertEqual(self.query('SELECT * FROM nothing_here', table='nothing_here'), [])

	def test_query_raises_for_other_errors(self):
		self.raw().execute('CREATE TABLE t (a TEXT)')
		with self.assertRaises(sqlite3.OperationalError):
			self.query('SELECT missing_column FROM t', table='t')
		with self.assertRaises(sqlite3.OperationalError):
			self.query('SELECT * FROM nothing_here')  # no table declared: never swallowed


class AtomicResetTests(RemediationCase):
	def seed(self):
		floppysync.replace_watched_snapshot([movie(1, 'tt1')], [episode(10, 1, 1, 'tt10')], 7)
		self.seed_service()
		self.seed_cache()

	def test_clear_does_not_leave_cursor_over_empty_tables_when_snapshot_races_in(self):
		self.seed()
		fired = []
		real_get_connection = floppysync.get_connection

		def racing_get_connection(*args, **kwargs):
			con = real_get_connection(*args, **kwargs)
			def trace(statement):
				if fired or not statement.startswith('DELETE FROM floppy_watched_movies'): return
				fired.append(statement)
				# A first-run snapshot (expected_cursor=None) lands while the clear is in flight.
				other = sqlite3.connect(self.path, timeout=0, isolation_level=None)
				try:
					other.execute('BEGIN IMMEDIATE')
					if other.execute("SELECT value FROM floppy_sync_state WHERE key='watched_cursor'").fetchone() is None:
						other.execute("INSERT INTO floppy_watched_movies VALUES ('', '99', 'Raced', '2020', 'x')")
						other.execute("INSERT OR REPLACE INTO floppy_sync_state VALUES ('watched_cursor', '50')")
					other.execute('COMMIT')
				except sqlite3.OperationalError:
					pass  # locked out by the clear's own transaction: exactly what atomicity should do
				finally: other.close()
			con.set_trace_callback(trace)
			return con

		floppysync.get_connection = racing_get_connection
		try: floppysync.delete_floppy_tables(('floppy_watched_movies', 'floppy_watched_episodes'))
		finally: floppysync.get_connection = real_get_connection
		self.assertTrue(fired, 'race injection never triggered; the test is vacuous')
		cursor, movies, episodes = self.cursor(), self.movies(), self.episodes()
		self.assertFalse(cursor is not None and not movies and not episodes,
			'cursor %r survived over empty tables' % (cursor,))

	def test_failed_clear_rolls_back_cursor_rows_and_timestamps(self):
		self.seed()
		before = self.snapshot_state()
		con = self.raw()
		con.execute("CREATE TRIGGER boom BEFORE DELETE ON floppy_watched_episodes BEGIN SELECT RAISE(ABORT, 'boom'); END")
		con.commit()
		floppysync.delete_floppy_tables(('floppy_watched_movies', 'floppy_watched_episodes'))
		self.assertEqual(self.snapshot_state(), before)
		self.assertEqual(before[2], '7')
		self.assertTrue(LOG.errors)

	def test_clear_empties_tables_cursor_and_timestamps_together(self):
		self.seed()
		floppysync.set_sync_state('instance_key', 'keep')
		floppysync.delete_floppy_tables(('floppy_watched_movies', 'floppy_watched_episodes', 'movies_completed'))
		self.assertEqual((self.movies(), self.episodes(), self.cursor()), ([], [], None))
		self.assertEqual(self.service('last_history_at'), EPOCH)
		self.assertEqual(self.state('instance_key'), 'keep')
		self.assertEqual(LOG.errors, [])


class CursorMappingTests(RemediationCase):
	def test_bookmarks_wipe_clears_progress_cursor_only(self):
		self.seed_user_state()
		floppysync.upsert_bookmark(title='T', imdb='tt1', tmdb='1', percent_played='10', duration='100')
		floppysync.delete_floppy_tables(('bookmarks',))
		self.assertIsNone(self.state('progress_cursor'))
		self.assertEqual(self.state('watched_cursor'), '7')
		self.assertEqual(self.state('instance_key'), 'stable')
		self.assertEqual(self.query('SELECT * FROM bookmarks', table='bookmarks'), [])

	def test_watched_wipe_leaves_progress_cursor(self):
		self.seed_user_state()
		floppysync.delete_floppy_tables(('floppy_watched_episodes',))
		self.assertIsNone(self.state('watched_cursor'))
		self.assertEqual(self.state('progress_cursor'), '11')

	def test_revoke_style_wipe_clears_every_cursor_but_not_identity(self):
		self.seed_user_state()
		floppysync.delete_floppy_tables(('bookmarks', 'floppy_watched_movies', 'floppy_watched_episodes', 'movies_completed'))
		self.assertIsNone(self.state('watched_cursor'))
		self.assertIsNone(self.state('progress_cursor'))
		self.assertEqual(self.state('registered_identity'), 'user-a')  # identity is clear_sync_state()'s job

	def test_other_tables_keep_every_cursor(self):
		self.seed_user_state()
		floppysync.delete_floppy_tables(('movies_completed',))
		self.assertEqual((self.state('watched_cursor'), self.state('progress_cursor')), ('7', '11'))


class ClearSyncStateTests(RemediationCase):
	def test_default_keeps_only_instance_key(self):
		self.seed_user_state()
		floppysync.clear_sync_state()
		rows = self.query('SELECT key, value FROM floppy_sync_state ORDER BY key')
		self.assertEqual(rows, [('instance_key', 'stable')])

	def test_does_not_touch_cached_rows(self):
		floppysync.replace_watched_snapshot([movie(1)], [episode(10, 1, 1)], 3)
		floppysync.set_sync_state('instance_key', 'stable')
		floppysync.clear_sync_state()
		self.assertEqual(self.movies(), [movie(1)])
		self.assertIsNone(self.cursor())
		self.assertEqual(floppysync.get_sync_state('instance_key'), 'stable')

	def test_custom_keep_and_bare_string(self):
		self.seed_user_state()
		floppysync.clear_sync_state(keep='origin_key')
		self.assertEqual(self.query('SELECT key FROM floppy_sync_state'), [('origin_key',)])
		floppysync.clear_sync_state(keep=())
		self.assertEqual(self.query('SELECT key FROM floppy_sync_state'), [])

	def test_works_without_existing_state_table(self):
		floppysync.clear_sync_state()
		self.assertEqual(self.query('SELECT key FROM floppy_sync_state'), [])

	def test_rolls_back_on_failure(self):
		self.seed_user_state()
		con = self.raw()
		con.execute("CREATE TRIGGER boom BEFORE DELETE ON floppy_sync_state WHEN OLD.key = 'origin_key' BEGIN SELECT RAISE(ABORT, 'boom'); END")
		con.commit()
		with self.assertRaises(sqlite3.Error):
			floppysync.clear_sync_state()
		self.assertEqual(self.state('registered_identity'), 'user-a')
		self.assertEqual(self.state('watched_cursor'), '7')


class StateGuardTests(RemediationCase):
	def test_generic_write_to_a_cursor_key_is_refused(self):
		floppysync.replace_watched_snapshot([movie(1)], [], 7)
		for key in ('watched_cursor', 'progress_cursor'):
			with self.assertRaises(ValueError):
				floppysync.set_sync_state(key, 99)
		self.assertEqual(self.cursor(), '7')
		self.assertIsNone(self.state('progress_cursor'))

	def test_get_or_create_refuses_cursor_keys(self):
		with self.assertRaises(ValueError):
			floppysync.get_or_create_sync_state('watched_cursor', lambda: '1')

	def test_reset_accepts_bare_cursor_name(self):
		self.seed_user_state()
		floppysync.reset_sync_cursors('watched')
		self.assertIsNone(self.state('watched_cursor'))
		self.assertEqual(self.state('progress_cursor'), '11')
		floppysync.reset_sync_cursors('progress')
		self.assertIsNone(self.state('progress_cursor'))
		self.assertEqual(self.state('instance_key'), 'stable')

	def test_reset_with_several_names_and_unknown_name(self):
		self.seed_user_state()
		with self.assertRaises((KeyError, ValueError)):
			floppysync.reset_sync_cursors(('watched', 'nope'))
		self.assertEqual(self.state('watched_cursor'), '7')  # nothing was reset
		floppysync.reset_sync_cursors(('watched', 'progress'))
		self.assertEqual((self.state('watched_cursor'), self.state('progress_cursor')), (None, None))


class GetOrCreateTests(RemediationCase):
	def test_creates_once_and_returns_stored_value(self):
		calls = []
		def factory():
			calls.append(1)
			return 'key-%d' % len(calls)
		self.assertEqual(floppysync.get_or_create_sync_state('instance_key', factory), 'key-1')
		self.assertEqual(floppysync.get_or_create_sync_state('instance_key', factory), 'key-1')
		self.assertEqual(calls, [1])
		self.assertEqual(self.state('instance_key'), 'key-1')

	def test_concurrent_first_runs_agree_on_one_value(self):
		barrier = threading.Barrier(4)
		def create(n):
			barrier.wait()
			return floppysync.get_or_create_sync_state('instance_key', lambda: 'key-%d' % n)
		threads = [self.run_thread(lambda n=n: create(n)) for n in range(4)]
		results = [self.finish(*pair).get('result') for pair in threads]
		self.assertEqual(len(set(results)), 1, results)
		self.assertEqual(self.state('instance_key'), results[0])

	def test_lock_failure_raises_and_never_overwrites_stored_key(self):
		floppysync.set_sync_state('instance_key', 'original')
		hold = self.holder()
		with self.busy_timeout(0.3):
			with self.assertRaises(sqlite3.OperationalError):
				floppysync.get_or_create_sync_state('instance_key', lambda: 'intruder')
		hold.execute('ROLLBACK')
		self.assertEqual(self.state('instance_key'), 'original')

	def test_lock_failure_on_first_run_creates_nothing(self):
		floppysync.set_sync_state('other', 'x')  # state table exists, instance_key does not
		hold = self.holder()
		with self.busy_timeout(0.3):
			with self.assertRaises(sqlite3.OperationalError):
				floppysync.get_or_create_sync_state('instance_key', lambda: 'new')
		hold.execute('ROLLBACK')
		self.assertIsNone(self.state('instance_key'))

	def test_factory_failure_or_empty_value_stores_nothing(self):
		def explode(): raise RuntimeError('no entropy')
		with self.assertRaises(RuntimeError):
			floppysync.get_or_create_sync_state('instance_key', explode)
		for bad in (None, ''):
			with self.assertRaises(ValueError):
				floppysync.get_or_create_sync_state('instance_key', lambda bad=bad: bad)
		self.assertIsNone(self.state('instance_key'))
		self.assertEqual(floppysync.get_or_create_sync_state('instance_key', lambda: 'ok'), 'ok')


CHILD = r'''
import os, sys
repo, path = sys.argv[1], sys.argv[2]
sys.path.insert(0, repo)
from tests.floppy_fast_sync import kodi_stubs
control, log = kodi_stubs.install('matrix')
from resources.lib.database import floppysync
control.floppySyncFile = floppysync.floppySyncFile = path
con = floppysync._tx_connection()
con.execute('PRAGMA cache_size = 1')  # force dirty pages out to the database file before commit
con.execute('BEGIN IMMEDIATE')
con.execute('DELETE FROM floppy_watched_movies')
con.execute('DELETE FROM floppy_watched_episodes')
con.executemany('INSERT INTO floppy_watched_movies VALUES (?, ?, ?, ?, ?)',
	[('', 'new%d' % i, 'New title %d ' % i + 'z' * 200, '2021', 'x') for i in range(4000)])
con.execute("INSERT OR REPLACE INTO floppy_sync_state VALUES ('watched_cursor', '999')")
con.execute("INSERT OR REPLACE INTO service VALUES ('last_history_at', 'child-wrote-this')")
con.execute('DELETE FROM watched')
sys.stdout.write('ready\n'); sys.stdout.flush()
os._exit(1)  # die before COMMIT: leaves a hot -journal, no cleanup of any kind
'''


class CrashRecoveryTests(RemediationCase):
	def test_legacy_off_opener_sees_old_commit_after_writer_dies_mid_transaction(self):
		movies = [movie(i, 'tt%d' % i, title='Old title %d ' % i + 'y' * 200) for i in range(1, 4001)]
		self.assertTrue(floppysync.replace_watched_snapshot(movies, [episode(10, 1, 1, 'tt10', '5')], 42))
		self.seed_service()
		self.seed_cache()
		before = self.snapshot_state()
		self.assertEqual(len(before[0]), 4000)
		with open(self.path, 'rb') as handle: pristine = handle.read()

		child = subprocess.Popen([sys.executable, '-I', '-c', CHILD, REPO_ROOT, self.path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out, err = child.communicate()
		self.assertEqual(child.returncode, 1, err.decode('utf-8', 'replace'))
		self.assertEqual(out.decode().strip(), 'ready')

		journal = self.path + '-journal'
		self.assertTrue(os.path.exists(journal), 'child left no hot journal: crash was not mid-transaction')
		with open(self.path, 'rb') as handle: crashed = handle.read()
		self.assertNotEqual(crashed, pristine, 'no dirty page reached the database file: rollback is not being exercised')

		# The next opener is the legacy journal_mode=OFF connection every other Floppy helper uses.
		con = floppysync.get_connection()
		try:
			self.assertEqual(con.execute('PRAGMA journal_mode').fetchone()[0].lower(), 'off')
			self.assertEqual(con.execute('SELECT value FROM floppy_sync_state WHERE key=?', ('watched_cursor',)).fetchone()[0], '42')
			self.assertEqual(con.execute('SELECT COUNT(*) FROM floppy_watched_movies').fetchone()[0], 4000)
			self.assertEqual(con.execute('PRAGMA integrity_check').fetchall(), [('ok',)])
		finally: con.close()
		self.assertFalse(os.path.exists(journal), 'hot journal was not rolled back')
		self.assertEqual(self.snapshot_state(), before)

	def test_work_continues_normally_after_recovery(self):
		floppysync.replace_watched_snapshot([movie(1, 'tt1')], [], 5)
		subprocess.Popen([sys.executable, '-I', '-c', CHILD, REPO_ROOT, self.path], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
		self.assertEqual(floppysync.apply_watched_changes([('upsert_movie', movie(2, 'tt2'))], 5, 6), 1)
		self.assertEqual(self.tmdbs(), ['1', '2'])


class TwoConnectionTests(RemediationCase):
	def setUp(self):
		RemediationCase.setUp(self)
		floppysync.replace_watched_snapshot([movie(1, 'tt1'), movie(2, 'tt2')], [episode(10, 1, 1, 'tt10')], 5)
		self.seed_service()
		self.seed_cache()

	def advance_under_lock(self, hold):
		hold.execute("UPDATE floppy_sync_state SET value='6' WHERE key='watched_cursor'")
		hold.execute("INSERT OR REPLACE INTO floppy_watched_movies VALUES ('', '50', 'Other writer', '2020', 'x')")
		hold.execute('COMMIT')

	def test_delta_waits_for_write_lock_then_loses_the_compare_and_swap(self):
		hold = self.holder()
		with self.busy_timeout(20):
			thread, box = self.run_thread(lambda: floppysync.apply_watched_changes([('delete_movie', 1)], 5, 8))
			self.assert_blocked(thread)
			self.advance_under_lock(hold)
			box = self.finish(thread, box)
		self.assertIsInstance(box.get('error'), floppysync.CursorMismatch, box)
		self.assertEqual(self.cursor(), '6')
		self.assertEqual(self.tmdbs(), ['1', '2', '50'])  # delete_movie(1) was not applied

	def test_snapshot_waits_for_write_lock_then_loses_the_compare_and_swap(self):
		hold = self.holder()
		with self.busy_timeout(20):
			thread, box = self.run_thread(lambda: floppysync.replace_watched_snapshot([movie(9)], [], 9, expected_cursor=5))
			self.assert_blocked(thread)
			self.advance_under_lock(hold)
			box = self.finish(thread, box)
		self.assertIsInstance(box.get('error'), floppysync.CursorMismatch, box)
		self.assertEqual(self.cursor(), '6')
		self.assertEqual(self.tmdbs(), ['1', '2', '50'])

	def test_waiting_delta_applies_when_the_holder_leaves_the_cursor_alone(self):
		hold = self.holder()
		with self.busy_timeout(20):
			thread, box = self.run_thread(lambda: floppysync.apply_watched_changes([('delete_movie', 1)], 5, 8))
			self.assert_blocked(thread)
			hold.execute('ROLLBACK')
			box = self.finish(thread, box)
		self.assertEqual(box.get('result'), 1, box)
		self.assertEqual(self.cursor(), '8')

	def test_concurrent_deltas_from_the_same_cursor_apply_exactly_once(self):
		barrier = threading.Barrier(2)
		def go(n):
			barrier.wait()
			return floppysync.apply_watched_changes([('upsert_movie', movie(100 + n, 'tt%d' % (100 + n)))], 5, 6)
		pairs = [self.run_thread(lambda n=n: go(n)) for n in range(2)]
		boxes = [self.finish(*pair) for pair in pairs]
		wins = [b for b in boxes if b.get('result') == 1]
		losses = [b for b in boxes if isinstance(b.get('error'), floppysync.CursorMismatch)]
		self.assertEqual((len(wins), len(losses)), (1, 1), boxes)
		self.assertEqual(len(self.movies()), 3)
		self.assertEqual(self.cursor(), '6')

	def test_snapshot_racing_delta_leaves_a_consistent_pair(self):
		barrier = threading.Barrier(2)
		def snap():
			barrier.wait()
			return floppysync.replace_watched_snapshot([movie(7, 'tt7')], [], 9, expected_cursor=5)
		def delta():
			barrier.wait()
			return floppysync.apply_watched_changes([('delete_movie', 1)], 5, 6)
		(t1, b1), (t2, b2) = self.run_thread(snap), self.run_thread(delta)
		b1, b2 = self.finish(t1, b1), self.finish(t2, b2)
		self.assertEqual(sum('result' in b for b in (b1, b2)), 1, (b1, b2))
		self.assertEqual(sum(isinstance(b.get('error'), floppysync.CursorMismatch) for b in (b1, b2)), 1, (b1, b2))
		if 'result' in b1: self.assertEqual((self.cursor(), self.tmdbs()), ('9', ['7']))
		else: self.assertEqual((self.cursor(), self.tmdbs()), ('6', ['2']))

	def test_legacy_off_writer_waits_for_fast_sync_transaction_instead_of_interleaving(self):
		hold = self.holder()
		hold.execute("INSERT INTO floppy_watched_movies VALUES ('', '60', 'Fast sync', '2020', 'x')")
		with self.busy_timeout(20):
			thread, box = self.run_thread(lambda: floppysync.upsert_watched_movie('tt70', 70, 'Legacy', 2020, 'x'))
			self.assert_blocked(thread)
			self.assertNotIn('70', self.tmdbs())
			hold.execute('COMMIT')
			self.finish(thread, box)
		self.assertEqual(self.tmdbs(), ['1', '2', '60', '70'])
		self.assertEqual(LOG.errors, [])

	def test_legacy_off_writer_gives_up_with_lock_error_not_corruption(self):
		hold = self.holder()
		hold.execute("INSERT INTO floppy_watched_movies VALUES ('', '60', 'Fast sync', '2020', 'x')")
		with self.busy_timeout(0.3):
			floppysync.upsert_watched_movie('tt70', 70, 'Legacy', 2020, 'x')
		hold.execute('ROLLBACK')
		self.assertTrue(any('locked' in e for e in LOG.errors), LOG.errors)
		self.assertEqual(self.tmdbs(), ['1', '2'])
		self.assertEqual(self.raw().execute('PRAGMA integrity_check').fetchall(), [('ok',)])


class NormalizationTests(RemediationCase):
	def test_non_string_fields_are_stored_as_text_and_resnapshot_is_unchanged(self):
		rows = [('tt1', 7, 12345, 2020, 20240101)]
		eps = [('tt9', 10, 55, 1, 2, 20240102)]
		floppysync.replace_watched_snapshot(rows, eps, 1)
		self.assertEqual(self.movies(), [('tt1', '7', '12345', '2020', '20240101')])
		self.assertEqual(self.episodes(), [('tt9', '10', '55', 1, 2, '20240102')])
		self.seed_service()
		self.seed_cache()
		floppysync.replace_watched_snapshot(rows, eps, 2, expected_cursor=1)
		self.assertEqual(self.service('last_history_at'), SENTINEL)
		self.assertEqual(self.cache_rows(), [('k',)])

	def test_non_string_delta_fields_do_not_inflate_the_change_count(self):
		floppysync.replace_watched_snapshot([('tt1', 7, 12345, 2020, 20240101)], [('tt9', 10, 55, 1, 2, 20240102)], 1)
		ops = [('upsert_movie', ('tt1', 7, 12345, 2020, 20240101)), ('upsert_episode', ('tt9', 10, 55, 1, 2, 20240102))]
		self.assertEqual(floppysync.apply_watched_changes(ops, 1, 2), 0)

	def test_ids_are_stripped(self):
		floppysync.replace_watched_snapshot([(' tt1 ', ' 7 ', 'T', ' 2020 ', 'x')], [(' tt9 ', ' 10 ', ' 55 ', 1, 2, 'x')], 1)
		self.assertEqual(self.movies(), [('tt1', '7', 'T', '2020', 'x')])
		self.assertEqual(self.episodes(), [('tt9', '10', '55', 1, 2, 'x')])

	def test_integral_numeric_strings_and_floats_are_accepted_for_season_and_episode(self):
		floppysync.replace_watched_snapshot([], [('', 10, '', ' 2 ', 3.0, 'x')], 1)
		self.assertEqual(self.episodes(), [('', '10', '', 2, 3, 'x')])

	def test_bad_numbers_and_ids_are_rejected_without_writing(self):
		floppysync.replace_watched_snapshot([movie(1)], [episode(10, 1, 1)], 5)
		before = self.snapshot_state()
		bad_episodes = [('', 10, '', 1.9, 1, 'x'), ('', 10, '', True, 1, 'x'), ('', 10, '', 1, False, 'x'),
			('', 10, '', '1.9', 1, 'x'), ('', 10, '', -1, 1, 'x'), ('', 10, '', None, 1, 'x'), ('', 10, '', 'x', 1, 'x')]
		for row in bad_episodes:
			with self.assertRaises((ValueError, TypeError), msg=repr(row)):
				floppysync.replace_watched_snapshot([], [row], 6, expected_cursor=5)
		for tmdb in ('', '   ', None, '0', 0, '123.0', 123.0, True, '-4', 'abc', '1e3'):
			with self.assertRaises((ValueError, TypeError), msg=repr(tmdb)):
				floppysync.replace_watched_snapshot([('', tmdb, 'T', '2020', 'x')], [], 6, expected_cursor=5)
			with self.assertRaises((ValueError, TypeError), msg=repr(tmdb)):
				floppysync.apply_watched_changes([('delete_movie', tmdb)], 5, 6)
		for payload in (('1', 1.5, 1), ('1', True, 1), ('1', 1, '1.5'), ('0', 1, 1)):
			with self.assertRaises((ValueError, TypeError), msg=repr(payload)):
				floppysync.apply_watched_changes([('delete_episode', payload)], 5, 6)
		self.assertEqual(self.snapshot_state(), before)

	def test_none_text_fields_become_empty_strings(self):
		floppysync.replace_watched_snapshot([(None, 7, None, None, None)], [(None, 10, None, 1, 2, None)], 1)
		self.assertEqual(self.movies(), [('', '7', '', '', '')])
		self.assertEqual(self.episodes(), [('', '10', '', 1, 2, '')])


class TvdbCarryForwardTests(RemediationCase):
	def test_snapshot_carries_known_tvdb_forward(self):
		floppysync.replace_watched_snapshot([], [episode(10, 1, 1, 'tt10', '99')], 5)
		floppysync.replace_watched_snapshot([], [episode(10, 1, 1, '', ''), episode(10, 1, 2, '', '')], 6, expected_cursor=5)
		self.assertEqual(self.episodes(), [episode(10, 1, 1, 'tt10', '99'), episode(10, 1, 2, 'tt10', '99')])

	def test_snapshot_incoming_tvdb_wins(self):
		floppysync.replace_watched_snapshot([], [episode(10, 1, 1, 'tt10', '99')], 5)
		floppysync.replace_watched_snapshot([], [episode(10, 1, 1, 'tt10', '77')], 6, expected_cursor=5)
		self.assertEqual(self.episodes(), [episode(10, 1, 1, 'tt10', '77')])

	def test_delta_carries_known_tvdb_forward_for_new_and_existing_rows(self):
		floppysync.replace_watched_snapshot([], [episode(10, 1, 1, 'tt10', '99')], 5)
		ops = [('upsert_episode', episode(10, 1, 2, '', '')), ('upsert_episode', episode(10, 1, 1, '', '', at='2025-01-01T00:00:00.000Z'))]
		self.assertEqual(floppysync.apply_watched_changes(ops, 5, 6), 2)
		self.assertEqual(self.episodes(), [episode(10, 1, 1, 'tt10', '99', at='2025-01-01T00:00:00.000Z'), episode(10, 1, 2, 'tt10', '99')])

	def test_delta_incoming_tvdb_wins_and_other_shows_are_unaffected(self):
		floppysync.replace_watched_snapshot([], [episode(10, 1, 1, 'tt10', '99'), episode(11, 1, 1, 'tt11', '55')], 5)
		floppysync.apply_watched_changes([('upsert_episode', episode(10, 1, 2, '', '77'))], 5, 6)
		self.assertEqual(self.episodes(), sorted([episode(10, 1, 1, 'tt10', '99'), episode(10, 1, 2, 'tt10', '77'), episode(11, 1, 1, 'tt11', '55')]))

	def test_delta_tvdb_only_carry_does_not_mark_unchanged_row_as_changed(self):
		floppysync.replace_watched_snapshot([], [episode(10, 1, 1, 'tt10', '99')], 5)
		self.assertEqual(floppysync.apply_watched_changes([('upsert_episode', episode(10, 1, 1, '', ''))], 5, 6), 0)


class LegacyDatabaseTests(RemediationCase):
	def seed_legacy(self):
		# What the old full-sync path leaves behind: NULL imdb, 'None' year/tvdb, no sync-state table.
		floppysync.upsert_watched_movie(None, 1, 'Legacy One', None, 'old')
		floppysync.upsert_watched_movie('tt2', 2, 'Legacy Two', 2020, 'old')
		floppysync.upsert_watched_episode('tt10', 10, None, 1, 1, 'old')
		floppysync.upsert_watched_episode('', 11, None, 2, 2, 'old')
		self.assertEqual(self.query('SELECT name FROM sqlite_master WHERE name=?', ('floppy_sync_state',)), [])

	def test_first_snapshot_replaces_legacy_rows_cleanly(self):
		self.seed_legacy()
		self.assertIn((None, '1', 'Legacy One', 'None', 'old'), self.query('SELECT imdb, tmdb, title, year, last_watched_at FROM floppy_watched_movies'))
		self.seed_service()
		self.seed_cache()
		self.assertTrue(floppysync.replace_watched_snapshot(
			[('', 1, 'One', 2019, 'new'), ('', 2, 'Two', 2020, 'new'), ('', 3, 'Three', '', 'new')],
			[('', 10, '', 1, 1, 'new'), ('', 11, '', 2, 2, 'new')], 20))
		self.assertEqual(self.movies(), sorted([('', '1', 'One', '2019', 'new'), ('tt2', '2', 'Two', '2020', 'new'), ('', '3', 'Three', '', 'new')]))
		# 'None' placeholders from the old path are not "known" ids and must not be carried forward.
		self.assertEqual(self.episodes(), sorted([('tt10', '10', '', 1, 1, 'new'), ('', '11', '', 2, 2, 'new')]))
		self.assertEqual(self.cursor(), '20')
		self.assertNotEqual(self.service('last_history_at'), SENTINEL)
		self.assertEqual(self.cache_rows(), [])

	def test_identical_resnapshot_after_legacy_replacement_is_unchanged(self):
		self.seed_legacy()
		rows = ([('', 1, 'One', 2019, 'new'), ('', 2, 'Two', 2020, 'new')], [('', 10, '', 1, 1, 'new')])
		floppysync.replace_watched_snapshot(rows[0], rows[1], 20)
		first = self.snapshot_state()
		self.seed_service()
		self.seed_cache()
		self.assertTrue(floppysync.replace_watched_snapshot(rows[0], rows[1], 21, expected_cursor=20))
		self.assertEqual(self.movies(), first[0])
		self.assertEqual(self.episodes(), first[1])
		self.assertEqual(self.cursor(), '21')
		self.assertEqual(self.service('last_history_at'), SENTINEL)
		self.assertEqual(self.cache_rows(), [('k',)])

	def test_delta_after_legacy_replacement_works(self):
		self.seed_legacy()
		floppysync.replace_watched_snapshot([('', 1, 'One', 2019, 'new')], [], 20)
		self.assertEqual(floppysync.apply_watched_changes([('delete_movie', 1)], 20, 21), 1)
		self.assertEqual(self.movies(), [])


if __name__ == '__main__':
	unittest.main()
