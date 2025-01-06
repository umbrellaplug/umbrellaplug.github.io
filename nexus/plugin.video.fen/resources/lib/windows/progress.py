# -*- coding: utf-8 -*-
from windows.base_window import BaseDialog
from modules.kodi_utils import addon_icon
# from modules.kodi_utils import logger

class Progress(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
		self.is_canceled = False
		self.heading = kwargs.get('heading', '')
		self.icon = kwargs.get('icon', addon_icon)
		self.setProperty('highlight_var', self.highlight_var(force=True))

	def run(self):
		self.doModal()
		self.clearProperties()

	def onInit(self):
		self.set_controls()

	def iscanceled(self):
		return self.is_canceled

	def onAction(self, action):
		if action in self.closing_actions:
			self.is_canceled = True
			self.close()

	def set_controls(self):
		self.set_image(200, self.icon)
		self.set_label(2000, self.heading)

	def update(self, content='', percent=0, icon=None):
		try:
			self.set_text(2001, content)
			self.set_percent(5000, percent)
			if icon: self.set_image(200, icon)
		except: pass
