# -*- coding: utf-8 -*-
from windows.base_window import BaseDialog
from modules.kodi_utils import Thread
# from modules.kodi_utils import logger

class VideoPlayer(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
		self.video = kwargs['video']
		self.setProperty('highlight_var', self.highlight_var(force=True))

	def onInit(self):
		Thread(target=self.monitor).start()
		self.player.play(self.video, windowed=True)

	def run(self):
		self.doModal()
		self.clearProperties()
	
	def onAction(self, action, controlID=None):
		if action in self.selection_actions: self.progress_display_toggle('true')
		elif action in self.closing_actions:self.closing_action()
		elif action == self.left_action: self.seek_back()
		elif action == self.right_action: self.seek_forward()
		elif action == self.up_action: self.seek_back_small()
		elif action == self.down_action: self.seek_forward_small()

	def monitor(self):
		while not self.player.isPlayingVideo(): self.sleep(1000)
		self.progress_display_toggle('true', incl_info=True)
		progress = 0
		while self.player.isPlayingVideo():
			self.sleep(1000)
			progress += 1
			if progress == 3: self.progress_display_toggle('false', incl_info=True)
		self.exit()

	def seek_forward(self):
		self.progress_display_toggle('true')
		try:
			self.player.seekTime(min(self.player.getTime() + 10.0, self.player.getTotalTime() - 1))
			self.sleep(1000)
		except: pass
		self.progress_display_toggle('false')

	def seek_forward_small(self):
		self.progress_display_toggle('true')
		try:
			self.player.seekTime(min(self.player.getTime() + 2.0, self.player.getTotalTime() - 1))
			self.sleep(1000)
		except: pass
		self.progress_display_toggle('false')

	def seek_back(self):
		self.progress_display_toggle('true')
		try:
			self.player.seekTime(max(self.player.getTime() - 10.0, 0.0))
			self.sleep(1000)
		except: pass
		self.progress_display_toggle('false')

	def seek_back_small(self):
		self.progress_display_toggle('true')
		try:
			self.player.seekTime(max(self.player.getTime() - 2.0, 0.0))
			self.sleep(1000)
		except: pass
		self.progress_display_toggle('false')

	def stop(self):
		self.player.stop()
		self.exit()

	def exit(self):
		self.sleep(500)
		self.clear_modals()
		self.close()

	def progress_display_toggle(self, toggle, incl_info=False):
		if incl_info: self.setProperty('display_fen_hint', toggle)
		self.setProperty('display_progress', toggle)

	def progress_display_status(self):
		return self.getProperty('display_progress')

	def closing_action(self):
		if self.progress_display_status() == 'true': self.progress_display_toggle('false')
		else: self.stop()
