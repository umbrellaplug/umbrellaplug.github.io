# -*- coding: utf-8 -*-
"""The shared Floppy database module must be byte-identical and compile in all four trees."""
import ast
import hashlib
import py_compile
import os
import tempfile
import unittest

from tests.floppy_fast_sync import kodi_stubs

SHARED = (
	'database/floppysync.py',
	'modules/floppy_fast_sync.py',
	'modules/floppy.py',
	'modules/tools.py',
)

def sha256(path):
	with open(path, 'rb') as handle: return hashlib.sha256(handle.read()).hexdigest()

class TreeParityTests(unittest.TestCase):
	def test_shared_files_are_byte_identical_across_trees(self):
		for rel in SHARED:
			digests = dict((tree, sha256(kodi_stubs.tree_file(tree, rel))) for tree in kodi_stubs.TREES)
			self.assertEqual(len(set(digests.values())), 1, '%s differs: %r' % (rel, digests))

	def test_shared_files_compile_in_every_tree(self):
		out = tempfile.mkdtemp(prefix='floppy-compile-')
		for rel in SHARED:
			for tree in kodi_stubs.TREES:
				py_compile.compile(kodi_stubs.tree_file(tree, rel), cfile=os.path.join(out, tree + '.pyc'), doraise=True)

	def test_shared_files_parse_as_python_3_8_syntax_in_every_tree(self):
		# No python3.8 interpreter is guaranteed locally; the parser can still reject newer syntax.
		for rel in SHARED:
			for tree in kodi_stubs.TREES:
				path = kodi_stubs.tree_file(tree, rel)
				with open(path, 'rb') as handle: source = handle.read()
				ast.parse(source, filename=path, feature_version=(3, 8))

if __name__ == '__main__':
	unittest.main()
