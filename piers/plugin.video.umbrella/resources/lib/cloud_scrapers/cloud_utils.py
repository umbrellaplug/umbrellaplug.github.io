# -*- coding: utf-8 -*-
# created by Umbrella (updated 11-12-2021)
"""
	Umbrella Add-on
"""

import re
from resources.lib.modules import cleantitle


def aliases_to_array(aliases, filter=None):
	try:
		if all(isinstance(x, str) for x in aliases): return aliases
		if not filter: filter = []
		if isinstance(filter, str): filter = [filter]
		return [x.get('title') for x in aliases if not filter or x.get('country') in filter]
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return []

def cloud_check_title(title, aliases, release_title):
	aliases = aliases_to_array(aliases)
	title_list = []
	title_list_append = title_list.append
	if aliases:
		for item in aliases:
			try:
				alias = item.replace('&', 'and')
				if alias in title_list: continue
				title_list_append(alias)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
	try:
		match = True
		title = title.replace('&', 'and')
		title_list_append(title)

		# release_title = release_title_format(release_title).replace('!', '').replace('(', '').replace(')', '').replace('&', 'and') # converts to .lower()
		release_title = release_title.replace('&', 'and')
		release_title = re.split(r'(?:19|20)[0-9]{2}', release_title)[0] # split by 4 digit year

		clean_release_title = cleantitle.get(release_title)
		if not clean_release_title:
			match = False
		else:
			for i in title_list:
				clean_i = cleantitle.get(i)
				if not clean_i:
					match = False
					break
				if clean_i in clean_release_title:
					break
			else:
				match = False
		return match
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return match

def release_title_format(release_title):
	try:
		release_title = release_title.lower().replace("'", "").lstrip('.').rstrip('.')
		fmt = '.%s.' % re.sub(r'[^a-z0-9-~]+', '.', release_title).replace('.-.', '-').replace('-.', '-').replace('.-', '-').replace('--', '-')
		return fmt
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return release_title

	def abbrev_title(title):
		try:
			split_title = title.split(' ')
			if len(split_title) == 1: return title
			abbrev_title = ''.join([i[:1] for i in split_title])
			return abbrev_title
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return title

def extras_filter():
	return ('sample', 'extra', 'deleted', 'unused', 'footage', 'inside', 'blooper', 'making.of', 'feature', 'featurette', 'behind.the.scenes', 'trailer')