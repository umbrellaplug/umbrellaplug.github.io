# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from string import printable
import unicodedata


def strip_non_ascii_and_unprintable(text):
	try:
		result = ''.join(char for char in text if char in printable)
		return result.encode('ascii', errors='ignore').decode('ascii', errors='ignore')
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return text

def normalize(msg):
	try:
		msg = ''.join(c for c in unicodedata.normalize('NFKD', msg) if unicodedata.category(c) != 'Mn')
		return str(msg)
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return msg