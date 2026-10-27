# -*- coding: utf-8 -*-
"""Install minimal Kodi fakes so Umbrella's Floppy modules import outside Kodi.

The real add-on packages (resources.lib.database, resources.lib.modules.cleandate)
load from the matrix tree; only the modules that need xbmc are replaced.
"""
import os
import sys
import types

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TREES = ('matrix', 'nexus', 'omega', 'piers')
ADDON_SUBPATH = os.path.join('plugin.video.umbrella', 'resources', 'lib')

def addon_root(tree='matrix'):
	return os.path.join(REPO_ROOT, tree, 'plugin.video.umbrella')

def tree_file(tree, relpath):
	return os.path.join(REPO_ROOT, tree, ADDON_SUBPATH, relpath)

class FakeLogUtils(types.ModuleType):
	def __init__(self):
		types.ModuleType.__init__(self, 'resources.lib.modules.log_utils')
		self.errors = []
		self.LOGDEBUG, self.LOGINFO, self.LOGWARNING, self.LOGERROR = 0, 1, 2, 3
	def error(self, message=None):
		import traceback
		self.errors.append(traceback.format_exc())
	def log(self, *args, **kwargs): pass
	def log_force(self, *args, **kwargs): pass

def install(tree='matrix'):
	"""Put the add-on on sys.path and register fakes. Returns (fake_control, fake_log)."""
	root = addon_root(tree)
	if root not in sys.path: sys.path.insert(0, root)
	import resources.lib.modules as modules_pkg
	control = types.ModuleType('resources.lib.modules.control')
	control.dataPath = ''
	control.floppySyncFile = ''
	control.existsPath = lambda path: True
	control.makeFile = lambda path: None
	log_utils = FakeLogUtils()
	for name, module in (('control', control), ('log_utils', log_utils)):
		sys.modules['resources.lib.modules.' + name] = module
		setattr(modules_pkg, name, module)
	return control, log_utils
