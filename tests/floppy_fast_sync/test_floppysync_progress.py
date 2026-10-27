# -*- coding: utf-8 -*-
"""Task 4a: atomic progress (bookmarks) snapshot and delta primitives in floppysync.py."""
import sqlite3
import unittest

from tests.floppy_fast_sync import test_floppysync_tx as base
from tests.floppy_fast_sync.test_floppysync_tx import LOG, SENTINEL

floppysync = base.floppysync

AT = '2024-05-06T07:08:09.000Z'

def mark(tmdb, imdb='', title=None, percent='25.0', at=AT, tvdb=''):
	# A movie bookmark in the table's own 14-column order.
	return ('', title or 'Movie %s' % tmdb, 'rid-m%s' % tmdb, imdb, str(tmdb), tvdb, '', '', '', '', '', '', percent, at)

def epmark(tmdb, season, ep, imdb='', show='Show', percent='50.0', at=AT, tvdb='7'):
	return (show, 'Ep %s' % ep, 'rid-%s-%s-%s' % (tmdb, season, ep), imdb, str(tmdb), tvdb, str(season), str(ep), '', '', '', '', percent, at)


class ProgressCase(base.TxTestCase):
	def bookmarks(self):
		return sorted(self.query('SELECT * FROM bookmarks', table='bookmarks'))

	def pcursor(self):
		return self.state('progress_cursor')

	def snapshot_state(self):
		return (self.bookmarks(), self.pcursor(), self.service('last_paused_at'), self.cursor())


class ProgressSnapshotTests(ProgressCase):
	def test_snapshot_into_empty_database_stores_rows_and_cursor(self):
		self.assertTrue(floppysync.replace_progress_snapshot([mark(1, 'tt1'), epmark(10, 1, 2, 'tt10')], 42))
		self.assertEqual(self.bookmarks(), sorted([mark(1, 'tt1'), epmark(10, 1, 2, 'tt10')]))
		self.assertEqual(self.pcursor(), '42')
		self.assertNotEqual(self.service('last_paused_at'), None)

	def test_snapshot_does_not_touch_the_watched_cursor_or_watched_cache(self):
		floppysync.replace_watched_snapshot([base.movie(1)], [], 5)
		self.seed_cache()
		floppysync.replace_progress_snapshot([mark(1)], 9)
		self.assertEqual(self.cursor(), '5')
		self.assertEqual(self.cache_rows(), [('k',)])

	def test_snapshot_replaces_everything_and_drops_stale_and_local_rows(self):
		floppysync.upsert_bookmark(title='Local', imdb='ttX', tmdb='99', percent_played='10')
		floppysync.replace_progress_snapshot([mark(1), mark(2)], 5)
		self.assertTrue(floppysync.replace_progress_snapshot([mark(2, title='New')], 9, expected_cursor=5))
		self.assertEqual(self.bookmarks(), [mark(2, title='New')])
		self.assertEqual(self.pcursor(), '9')

	def test_empty_snapshot_is_valid_and_clears_rows(self):
		floppysync.replace_progress_snapshot([mark(1)], 5)
		floppysync.replace_progress_snapshot([], 6, expected_cursor=5)
		self.assertEqual(self.bookmarks(), [])
		self.assertEqual(self.pcursor(), '6')

	def test_duplicate_identities_in_a_snapshot_keep_the_last(self):
		floppysync.replace_progress_snapshot([mark(1, percent='10'), mark(1, 'tt1', percent='20')], 3)
		self.assertEqual(self.bookmarks(), [mark(1, 'tt1', percent='20')])

	def test_blank_and_filled_imdb_for_one_item_do_not_create_duplicates(self):
		floppysync.replace_progress_snapshot([mark(1, '')], 3)
		floppysync.apply_progress_changes([('upsert', mark(1, 'tt1'))], 3, 4)
		self.assertEqual(self.bookmarks(), [mark(1, 'tt1')])

	def test_snapshot_cas_mismatch_raises_and_changes_nothing(self):
		floppysync.replace_progress_snapshot([mark(1)], 5)
		before = self.snapshot_state()
		with self.assertRaises(floppysync.CursorMismatch) as raised:
			floppysync.replace_progress_snapshot([mark(2)], 9, expected_cursor=4)
		self.assertEqual((raised.exception.expected, raised.exception.stored), ('4', '5'))
		self.assertEqual(self.snapshot_state(), before)
		with self.assertRaises(floppysync.CursorMismatch):
			floppysync.replace_progress_snapshot([mark(2)], 9)  # expects no cursor
		self.assertEqual(self.snapshot_state(), before)
		self.assertEqual(LOG.errors, [])

	def test_failure_mid_snapshot_rolls_back_rows_and_cursor(self):
		floppysync.replace_progress_snapshot([mark(1), mark(2)], 5)
		before = self.snapshot_state()
		self.add_failure_trigger('bookmarks', 'tmdb', '77')
		with self.assertRaises(sqlite3.Error):
			floppysync.replace_progress_snapshot([mark(3), mark(77), mark(4)], 9, expected_cursor=5)
		self.assertEqual(self.snapshot_state(), before)

	def test_malformed_rows_are_rejected_before_any_write(self):
		floppysync.replace_progress_snapshot([mark(1)], 5)
		before = self.snapshot_state()
		bad_rows = [
			mark(0), mark('abc'), mark(1.5), mark(None), mark(True),
			epmark(10, 'x', 1), epmark(10, 1, -1), epmark(10, 1.5, 1), epmark(10, True, 1),
			('', 'T', 'r', '', '5', '', '1', '', '', '', '', '', '1', AT),  # season without episode
			('too', 'short'),
		]
		for row in bad_rows:
			with self.assertRaises((ValueError, TypeError), msg=repr(row)):
				floppysync.replace_progress_snapshot([mark(2), row], 9, expected_cursor=5)
			self.assertEqual(self.snapshot_state(), before, repr(row))

	def test_invalid_cursors_are_rejected(self):
		for cursor in (None, -1, 'abc', 1.5, True):
			with self.assertRaises((ValueError, TypeError)):
				floppysync.replace_progress_snapshot([], cursor)
		self.assertEqual(self.bookmarks(), [])

	def test_identical_resnapshot_is_unchanged_but_moves_the_cursor(self):
		floppysync.replace_progress_snapshot([mark(1), epmark(10, 1, 2)], 5)
		self.seed_service()
		con = self.raw()
		con.execute("INSERT OR REPLACE INTO service VALUES ('last_paused_at', ?)", (SENTINEL,))
		con.commit()
		floppysync.replace_progress_snapshot([epmark(10, 1, 2), mark(1)], 6, expected_cursor=5)
		self.assertEqual(self.service('last_paused_at'), SENTINEL)
		self.assertEqual(self.pcursor(), '6')

	def test_numeric_text_is_canonicalised(self):
		floppysync.replace_progress_snapshot([('S', 'T', 'r', '', ' 007 ', '', 1, 2.0, '', '', '', '', 1, 2)], 1)
		self.assertEqual(self.bookmarks(), [('S', 'T', 'r', '', '7', '', '1', '2', '', '', '', '', '1', '2')])


class ProgressDeltaTests(ProgressCase):
	def seeded(self):
		floppysync.replace_progress_snapshot([mark(1, 'tt1'), epmark(10, 1, 2, 'tt10')], 5)

	def test_upsert_and_delete_apply_in_order_and_advance_the_cursor(self):
		self.seeded()
		changed = floppysync.apply_progress_changes([
			('upsert', mark(2, 'tt2')),
			('upsert', epmark(10, 1, 3, 'tt10')),
			('delete', ('1', '', '')),
			('delete', ('10', 1, 2)),
		], 5, 8)
		self.assertEqual(changed, 4)
		self.assertEqual(self.bookmarks(), sorted([mark(2, 'tt2'), epmark(10, 1, 3, 'tt10')]))
		self.assertEqual(self.pcursor(), '8')

	def test_upsert_replaces_an_existing_position(self):
		self.seeded()
		self.assertEqual(floppysync.apply_progress_changes([('upsert', mark(1, 'tt1', percent='80.0'))], 5, 6), 1)
		self.assertEqual(self.bookmarks(), sorted([mark(1, 'tt1', percent='80.0'), epmark(10, 1, 2, 'tt10')]))

	def test_upsert_then_delete_of_one_key_in_a_page_leaves_it_absent(self):
		self.seeded()
		floppysync.apply_progress_changes([('upsert', mark(3)), ('delete', ('3', '', ''))], 5, 7)
		self.assertEqual(self.bookmarks(), sorted([mark(1, 'tt1'), epmark(10, 1, 2, 'tt10')]))

	def test_delete_then_upsert_of_one_key_in_a_page_leaves_it_present(self):
		self.seeded()
		floppysync.apply_progress_changes([('delete', ('1', '', '')), ('upsert', mark(1, 'tt1', percent='90'))], 5, 7)
		self.assertIn(mark(1, 'tt1', percent='90'), self.bookmarks())

	def test_no_change_page_advances_cursor_and_leaves_timestamp_alone(self):
		self.seeded()
		con = self.raw()
		con.execute("INSERT OR REPLACE INTO service VALUES ('last_paused_at', ?)", (SENTINEL,))
		con.commit()
		self.assertEqual(floppysync.apply_progress_changes([], 5, 9), 0)
		self.assertEqual(floppysync.apply_progress_changes([('delete', ('404', '', ''))], 9, 11), 0)
		self.assertEqual(floppysync.apply_progress_changes([('upsert', mark(1, 'tt1'))], 11, 12), 0)
		self.assertEqual(self.pcursor(), '12')
		self.assertEqual(self.service('last_paused_at'), SENTINEL)

	def test_changes_bump_last_paused_at(self):
		self.seeded()
		con = self.raw()
		con.execute("INSERT OR REPLACE INTO service VALUES ('last_paused_at', ?)", (SENTINEL,))
		con.commit()
		floppysync.apply_progress_changes([('upsert', mark(5))], 5, 6)
		self.assertNotEqual(self.service('last_paused_at'), SENTINEL)

	def test_cas_mismatch_raises_and_changes_nothing(self):
		self.seeded()
		before = self.snapshot_state()
		with self.assertRaises(floppysync.CursorMismatch):
			floppysync.apply_progress_changes([('upsert', mark(2))], 4, 8)
		self.assertEqual(self.snapshot_state(), before)
		self.assertEqual(LOG.errors, [])

	def test_delta_without_a_snapshot_is_a_mismatch(self):
		with self.assertRaises(floppysync.CursorMismatch):
			floppysync.apply_progress_changes([], 0, 1)
		self.assertEqual(self.bookmarks(), [])

	def test_failure_halfway_rolls_back_the_page_and_keeps_the_cursor(self):
		self.seeded()
		before = self.snapshot_state()
		self.add_failure_trigger('bookmarks', 'tmdb', '77')
		with self.assertRaises(sqlite3.Error):
			floppysync.apply_progress_changes([('upsert', mark(2)), ('delete', ('1', '', '')), ('upsert', mark(77))], 5, 9)
		self.assertEqual(self.snapshot_state(), before)

	def test_malformed_op_rolls_back_before_any_write(self):
		self.seeded()
		before = self.snapshot_state()
		for ops in ([('upsert', mark(2)), ('bogus', 1)], [('upsert', mark(0))], [('delete', ('x', '', ''))],
				[('delete', ('1', 'a', ''))], [('delete', ('1',))], [('upsert', ('short',))]):
			with self.assertRaises((ValueError, TypeError), msg=repr(ops)):
				floppysync.apply_progress_changes(ops, 5, 9)
			self.assertEqual(self.snapshot_state(), before, repr(ops))

	def test_cursor_cannot_move_backwards_or_be_invalid(self):
		self.seeded()
		for args in (([], 5, 4), ([], 5, None), ([], None, 6), ([], 5, 1.5)):
			with self.assertRaises((ValueError, TypeError)):
				floppysync.apply_progress_changes(*args)
		self.assertEqual(self.pcursor(), '5')


class ProgressInteractionTests(ProgressCase):
	def test_existing_bookmark_helpers_still_work_after_transactional_writes(self):
		floppysync.replace_progress_snapshot([mark(1, 'tt1', percent='33.0')], 5)
		self.assertEqual(floppysync.fetch_bookmarks('tt1', tmdb='1'), '33.0')
		floppysync.upsert_bookmark(title='Local', imdb='tt2', tmdb='2', percent_played='44')
		floppysync.delete_bookmark('tt1', tmdb='1')
		self.assertEqual(sorted(r[4] for r in self.bookmarks()), ['2'])

	def test_clear_bookmarks_resets_only_the_progress_cursor(self):
		floppysync.replace_watched_snapshot([base.movie(1)], [], 4)
		floppysync.replace_progress_snapshot([mark(1)], 5)
		floppysync.clear_bookmarks()
		self.assertEqual(self.bookmarks(), [])
		self.assertEqual(self.pcursor(), None)
		self.assertEqual(self.cursor(), '4')

	def test_clear_bookmarks_failure_keeps_rows_and_cursor_together(self):
		floppysync.replace_progress_snapshot([mark(1)], 5)
		con = self.raw()
		con.execute("CREATE TRIGGER nodel BEFORE DELETE ON bookmarks BEGIN SELECT RAISE(ABORT, 'nodel'); END")
		con.commit()
		floppysync.clear_bookmarks()
		self.assertEqual(self.bookmarks(), [mark(1)])
		self.assertEqual(self.pcursor(), '5')

	def test_progress_and_watched_primitives_use_independent_cursors(self):
		floppysync.replace_watched_snapshot([base.movie(1)], [], 10)
		floppysync.replace_progress_snapshot([mark(1)], 3)
		floppysync.apply_progress_changes([('upsert', mark(2))], 3, 4)
		floppysync.apply_watched_changes([('upsert_movie', base.movie(2))], 10, 11)
		self.assertEqual((self.cursor(), self.pcursor()), ('11', '4'))

	def test_no_vacuum_or_modern_sqlite_syntax_in_progress_primitives(self):
		import inspect
		for name in ('_progress_connection', 'replace_progress_snapshot', 'apply_progress_changes', 'clear_bookmarks'):
			source = inspect.getsource(getattr(floppysync, name)).upper()
			for banned in ('VACUUM', 'ON CONFLICT', 'RETURNING', 'STRICT'):
				self.assertNotIn(banned, source, '%s uses %s' % (name, banned))

	def test_delete_floppy_tables_bookmarks_clears_progress_cursor(self):
		floppysync.replace_progress_snapshot([mark(1)], 5)
		floppysync.delete_floppy_tables(('bookmarks',))
		self.assertEqual((self.bookmarks(), self.pcursor()), ([], None))


if __name__ == '__main__':
	unittest.main()
