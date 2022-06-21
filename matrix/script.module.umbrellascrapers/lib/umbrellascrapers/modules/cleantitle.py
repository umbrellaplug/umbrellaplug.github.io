# -*- coding: utf-8 -*-
"""
	Umbrellascrapers Module
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
		from umbrellascrapers.modules import log_utils
		log_utils.error()
		return title

def get_simple(title):
	try:
		if not title: return
		title = re.sub(r'(&#[0-9]+)([^;^0-9]+)', '\\1;\\2', title).lower()# fix html codes with missing semicolon between groups
		title = re.sub(r'&#(\d+);', '', title)
		title = re.sub(r'(\d{4})', '', title)
		title = title.replace('&quot;', '\"').replace('&amp;', '&').replace('&nbsp;', '')
		title = re.sub(r'\n|[()[\]{}]|[:;–\-",\'!_.?~$@]|\s', '', title) # stop trying to remove alpha characters "vs" or "v", they're part of a title
		title = re.sub(r'<.*?>', '', title) # removes tags
		return title
	except:
		from umbrellascrapers.modules import log_utils
		log_utils.error()
		return title

def geturl(title):
	if not title: return
	try:
		title = title.lower().rstrip()
		try: title = title.translate(None, ':*?"\'\.<>|&!,')
		except:
			try: title = title.translate(title.maketrans('', '', ':*?"\'\.<>|&!,'))
			except:
				for c in ':*?"\'\.<>|&!,': title = title.replace(c, '')
		title = title.replace('/', '-').replace(' ', '-').replace('--', '-').replace('–', '-').replace('!', '')
		return title
	except:
		from umbrellascrapers.modules import log_utils
		log_utils.error()
		return title

def normalize(title):
	try:
		import unicodedata
		title = ''.join(c for c in unicodedata.normalize('NFKD', title) if unicodedata.category(c) != 'Mn')
		return str(title)
	except:
		from umbrellascrapers.modules import log_utils
		log_utils.error()
		return title