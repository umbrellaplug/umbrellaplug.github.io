# -*- coding: utf-8 -*-
"""
	Umbrellascrapers Module
"""

from umbrellascrapers.modules.control import addonPath, addonVersion, joinPath
from umbrellascrapers.windows.textviewer import TextViewerXML


def get(file):
	umbrellascrapers_path = addonPath()
	umbrellascrapers_version = addonVersion()
	helpFile = joinPath(umbrellascrapers_path, 'lib', 'umbrellascrapers', 'help', file + '.txt')
	r = open(helpFile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]umbrellascrapers -  v%s - %s[/B]' % (umbrellascrapers_version, file)
	windows = TextViewerXML('textviewer.xml', umbrellascrapers_path, heading=heading, text=text)
	windows.run()
	del windows