# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from urllib.request import urlopen, Request
from resources.lib.modules.control import addonPath, addonId, joinPath
from resources.lib.windows.textviewer import TextViewerXML

umbrella_path = addonPath(addonId())
news_file = 'https://raw.githubusercontent.com/umbrellaplug/umbrellaplug.github.io/master/matrix/plugin.video.umbrella/newsinfo.txt'
local_news = joinPath(umbrella_path, 'newsinfo.txt')


def news():
	message = open_news_url(news_file)
	compfile = open(local_news).read()
	if len(message) > 1:
		if compfile == message: pass
		else:
			text_file = open(local_news, "wb")
			text_file.write(message)
			text_file.close()
			compfile = message
	showText('[B]News and Info[/B]', compfile)

def open_news_url(url):
	req = Request(url)
	req.add_header('User-Agent', 'klopp')
	response = urlopen(req)
	link = response.read()
	response.close()
	return link

def news_local():
	compfile = open(local_news).read()
	showText('[B]News and Info[/B]', compfile)

def showText(heading, text):
	windows = TextViewerXML('textviewer.xml', umbrella_path, heading=heading, text=text)
	windows.run()
	del windows