# -*- coding: utf-8 -*-
"""Feed events carry no title or year, so a delta upsert must not blank what a snapshot stored."""
import unittest

from tests.floppy_fast_sync import test_floppysync_tx as base
from tests.floppy_fast_sync.test_floppysync_tx import movie

floppysync = base.floppysync


class DeltaCarryTests(base.TxTestCase):
	def test_upsert_with_blank_title_and_year_keeps_the_stored_ones(self):
		floppysync.replace_watched_snapshot([movie(1, 'tt1', title='Stored', year='1999')], [], 5)
		changed = floppysync.apply_watched_changes([('upsert_movie', ('', '1', '', '', '2025-01-01T00:00:00.000Z'))], 5, 6)
		self.assertEqual(changed, 1)
		self.assertEqual(self.movies(), [('tt1', '1', 'Stored', '1999', '2025-01-01T00:00:00.000Z')])

	def test_upsert_with_a_title_replaces_the_stored_one(self):
		floppysync.replace_watched_snapshot([movie(1, 'tt1', title='Stored', year='1999')], [], 5)
		floppysync.apply_watched_changes([('upsert_movie', ('', '1', 'Renamed', '2001', 'x'))], 5, 6)
		self.assertEqual(self.movies(), [('tt1', '1', 'Renamed', '2001', 'x')])

	def test_new_movie_with_blank_title_is_stored_blank(self):
		floppysync.replace_watched_snapshot([], [], 5)
		floppysync.apply_watched_changes([('upsert_movie', ('', '9', '', '', 'x'))], 5, 6)
		self.assertEqual(self.movies(), [('', '9', '', '', 'x')])

	def test_blank_upsert_matching_the_stored_row_after_carry_is_no_change(self):
		floppysync.replace_watched_snapshot([movie(1, 'tt1', title='Stored', year='1999', at='x')], [], 5)
		self.assertEqual(floppysync.apply_watched_changes([('upsert_movie', ('', '1', '', '', 'x'))], 5, 6), 0)


if __name__ == '__main__':
	unittest.main()
