# -*- coding: utf-8 -*-
from windows.base_window import BaseDialog
# from modules.kodi_utils import logger

class TextViewer(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
		self.heading = kwargs.get('heading')
		self.text = kwargs.get('text')
		self.font_size = kwargs.get('font_size')
		self.focus_id = 2060 if self.font_size == 'small' else 2061
		self.set_properties()

	def onInit(self):
		self.setFocusId(self.focus_id)

	def run(self):
		self.doModal()
		self.clearProperties()

	def onAction(self, action):
		if action in self.closing_actions:
			self.close()

	def set_properties(self):
		self.setProperty('text', self.text)
		self.setProperty('heading', self.heading)
		self.setProperty('font_size', self.font_size)
