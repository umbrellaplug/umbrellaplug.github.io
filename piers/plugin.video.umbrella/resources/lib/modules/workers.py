# -*- coding: utf-8 -*-
"""
	Umbrella Module
"""

from threading import Thread as thread

class Thread(thread):
	def __init__(self, target, *args):
		self._target = target
		self._args = args
		thread.__init__(self, target=self._target, args=self._args)