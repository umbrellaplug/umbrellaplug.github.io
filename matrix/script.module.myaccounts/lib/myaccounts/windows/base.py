# -*- coding: utf-8 -*-
"""
	My Accounts
"""

from xbmc import executebuiltin
from xbmcgui import WindowXMLDialog, ListItem, ControlProgress


class BaseDialog(WindowXMLDialog):
	def __init__(self, *args):
		WindowXMLDialog.__init__(self, args)
		self.closing_actions = [9, 10, 13, 92]
		self.selection_actions = [7, 100]
		self.context_actions = [101, 117]
		self.info_actions = [11,]

	def make_listitem(self):
		return ListItem()

	def execute_code(self, command):
		return executebuiltin(command)

	def get_position(self, window_id):
		return self.getControl(window_id).getSelectedPosition()

	def getControlProgress(self, control_id):
		control = self.getControl(control_id)
		if not isinstance(control, ControlProgress):
			raise AttributeError("Control with Id {} should be of type ControlProgress".format(control_id))
		return control