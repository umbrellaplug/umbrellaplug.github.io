# -*- coding: utf-8 -*-

from resources.lib.windows.base import BaseDialog


class TextViewerXML(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, args)
		self.window_id = 2060
		self.heading = kwargs.get('heading')
		self.text = kwargs.get('text')

	def onInit(self):
		self.set_properties()
		self.setFocusId(self.window_id)

	def run(self):
		self.doModal()
		self.clearProperties()

	def onAction(self, action):
		if action in self.closing_actions or action in self.selection_actions:
			self.close()

	def set_properties(self):
		self.setProperty('umbrella.text', self.text)
		self.setProperty('umbrella.heading', self.heading)