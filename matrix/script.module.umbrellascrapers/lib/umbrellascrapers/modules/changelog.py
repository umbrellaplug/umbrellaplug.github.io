# -*- coding: utf-8 -*-
"""
	Umbrellascrapers Module
"""

from umbrellascrapers.modules.control import addonPath, addonVersion, joinPath
from umbrellascrapers.windows.textviewer import TextViewerXML


def get():
	umbrellascrapers_path = addonPath()
	umbrellascrapers_version = addonVersion()
	changelogfile = joinPath(umbrellascrapers_path, 'changelog.txt')
	r = open(changelogfile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]umbrellascrapers -  v%s - ChangeLog[/B]' % umbrellascrapers_version
	windows = TextViewerXML('textviewer.xml', umbrellascrapers_path, heading=heading, text=text)
	windows.run()
	del windows