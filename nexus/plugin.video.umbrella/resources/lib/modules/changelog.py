# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from resources.lib.modules.control import addonPath, addonVersion, joinPath, existsPath
from resources.lib.windows.textviewer import TextViewerXML


def get(name, full=False):
	nameDict = {'Umbrella': 'plugin.video.umbrella'}
	addon_path = addonPath(nameDict[name])
	addon_version = addonVersion(nameDict[name])
	if not full: changelog_file = joinPath(addon_path, 'changelog.txt')
	else:
		changelog_file = joinPath(addon_path, 'fullchangelog.txt')
	if not existsPath(changelog_file):
		from resources.lib.modules.control import notification
		return notification(message='ChangeLog File not found.')
	f = open(changelog_file, 'r', encoding='utf-8', errors='ignore')
	text = f.read()
	f.close()
	heading = '[B]%s -  v%s - ChangeLog[/B]' % (name, addon_version)
	windows = TextViewerXML('textviewer.xml', addonPath('plugin.video.umbrella'), heading=heading, text=text)
	windows.run()
	del windows