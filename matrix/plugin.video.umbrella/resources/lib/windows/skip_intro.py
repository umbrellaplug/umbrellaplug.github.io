# -*- coding: utf-8 -*-

import xbmc
from math import ceil

from resources.lib.modules import control, log_utils
from resources.lib.windows.base import BaseDialog


class SkipSegmentXML(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, args)
		self.playing_file = kwargs['playing_file']
		self.segment_end = float(kwargs.get('segment_end', kwargs.get('intro_end')))
		self.label_id = kwargs.get('label_id', 40813)
		self.closed = False

	def onInit(self):
		self.setProperty('umbrella.skipintro.label', control.lang(self.label_id))
		self.setProperty('umbrella.skipintro.yes', xbmc.getLocalizedString(107) or 'Yes')
		self.setProperty('umbrella.skipintro.no', xbmc.getLocalizedString(106) or 'No')
		self.setProperty('umbrella.skipintro.background', control.setting('playnext.background.color') or 'ff202020')
		self.setProperty('umbrella.skipintro.highlight', control.setting('sources.highlight.color') or 'ff0091ea')
		self._monitor()

	def onClick(self, control_id):
		if control_id == 40502:
			self._close()
			return
		if control_id != 40501: return
		try:
			player = xbmc.Player()
			if player.isPlayingVideo() and player.getPlayingFile() == self.playing_file:
				current = player.getTime()
				if current < self.segment_end:
					player.seekTime(self.segment_end)
		except Exception:
			log_utils.error()
		self._close()

	def onAction(self, action):
		if action in self.closing_actions:
			self._close()

	def _close(self):
		self.closed = True
		self.close()

	def _monitor(self):
		player = xbmc.Player()
		while not self.closed and not control.monitor.abortRequested():
			try:
				current_time = player.getTime()
				if (not player.isPlayingVideo() or player.getPlayingFile() != self.playing_file
						or current_time >= self.segment_end):
					break
				remaining = max(0, int(ceil(self.segment_end - current_time)))
				self.setProperty('umbrella.skipintro.countdown', control.lang(40818) % remaining)
			except Exception:
				break
			if control.monitor.waitForAbort(0.25): break
		if not self.closed: self._close()


# Retain the original name for compatibility with any external imports.
SkipIntroXML = SkipSegmentXML
