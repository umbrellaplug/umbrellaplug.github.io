# -*- coding: utf-8 -*-
"""
	My Accounts
"""

from myaccounts.modules.control import addonPath, addonVersion, joinPath
from myaccounts.windows.textviewer import TextViewerXML

def get(file):
	myaccounts_path = addonPath()
	myaccounts_version = addonVersion()
	helpFile = joinPath(myaccounts_path, 'lib', 'myaccounts', 'help', file + '.txt')
	r = open(helpFile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]My Accounts -  v%s - %s[/B]' % (myaccounts_version, file)
	windows = TextViewerXML('textviewer.xml', myaccounts_path, heading=heading, text=text)
	windows.run()
	del windows