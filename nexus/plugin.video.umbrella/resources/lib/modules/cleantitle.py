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