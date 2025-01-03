# -*- coding: utf-8 -*-
from windows.base_window import BaseDialog
# from modules.kodi_utils import logger

class SettingsManager(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
	
	def run(self):
		self.doModal()
		self.clearProperties()

class SettingsManagerFolders(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)

	def run(self):
		self.doModal()
		self.clearProperties()
