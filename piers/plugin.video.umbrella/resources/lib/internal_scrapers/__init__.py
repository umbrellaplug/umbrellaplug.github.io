# -*- coding: UTF-8 -*-

import os
from pkgutil import walk_packages
from resources.lib.modules.control import setting as getSetting
from resources.lib.modules import log_utils
debug_enabled = getSetting('debug.enabled') == 'true'

def internalSources():
	try:
		sourceDict = []
		sourceFolderLocation = os.path.dirname(__file__)
		for loader, module_name, is_pkg in walk_packages([sourceFolderLocation]):
			if is_pkg: continue
			if enabledCheck(module_name):
				try:
					module = loader.find_spec(module_name).loader.load_module(module_name)
					sourceDict.append((module_name, module.source))
				except Exception as e:
					if debug_enabled:
						log_utils.log('Error: Loading internal scraper module: "%s": %s' % (module_name, e), level=log_utils.LOGWARNING)
		return sourceDict
	except:
		log_utils.error()
		return []

def enabledCheck(scraper):
	parent_dict = {'plexshare': 'plexshare', 'easynews':'easynews', 'filepursuit': 'filepursuit', 'gdrive':'gdrive'}
	try:
		parent_setting = parent_dict[scraper]
		#log_utils.log('internal scraper token check: %s ' % (parent_setting), level=log_utils.LOGDEBUG)
		if parent_setting == 'easynews':
			pass
		else:
			if not getSetting(parent_setting + 'token'): return False
		if getSetting(parent_setting + '.enable') == 'true': return True
		else: return False
	except:
		log_utils.error()
		return False