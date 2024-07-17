# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

import re


def get(title):
	try:
		if not title: return
		title = re.sub(r'(&#[0-9]+)([^;^0-9]+)', '\\1;\\2', title) # fix html codes with missing semicolon between groups
		title = re.sub(r'&#(\d+);', '', title).lower()
		title = title.replace('&quot;', '\"').replace('&amp;', '&').replace('&nbsp;', '')
		title = re.sub(r'([<\[({].*?[})\]>])|([^\w0-9])', '', title)
		return title
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return title

def get_sc(title):
	try:
		if not title: return
		title = re.sub(r'(&#[0-9]+)([^;^0-9]+)', '\\1;\\2', title) # fix html codes with missing semicolon between groups
		title = re.sub(r'&#(\d+);', '', title).lower()
		title = title.replace('&quot;', '\"').replace('&amp;', '&').replace('&nbsp;', '')
		#title = re.sub(r'[<\[({].*?[})\]>]|[^\w0-9]|[_]', '', title) #replaced with lines below to stop removing () and everything between.
		title = re.sub(r'\([^\d]*(\d+)[^\d]*\)', '', title) #eliminate all numbers between ()
		title = re.sub(r'[<\[{].*?[}\]>]|[^\w0-9]|[_]', '', title)
		return title
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return title

def normalize(title):
	try:
		import unicodedata
		title = ''.join(c for c in unicodedata.normalize('NFKD', title) if unicodedata.category(c) != 'Mn')
		return str(title)
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return title