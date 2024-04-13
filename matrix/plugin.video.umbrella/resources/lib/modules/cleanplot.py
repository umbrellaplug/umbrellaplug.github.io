# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from re import match as re_match

# no longer used-links not found in plot these days
def cleanPlot(plot):
	if not plot: return
	try:
		index = plot.rfind('See full summary')
		if index == -1: index = plot.rfind("It's publicly available on")
		if index >= 0: plot = plot[:index]
		plot = plot.strip()
		if re_match(r'[a-zA-Z\d]$', plot): plot += ' ...'
		return plot
	except:
		from resources.lib.modules import log_utils
		log_utils.error()