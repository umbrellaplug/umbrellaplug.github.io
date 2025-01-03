# -*- coding: utf-8 -*-
from windows.base_window import BaseDialog, ok_dialog
from modules.meta_lists import color_palette
from modules.kodi_utils import kodi_dialog
# from modules.kodi_utils import logger

class SelectColor(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
		self.kwargs = kwargs
		self.current_setting = self.kwargs.get('current_setting')
		self.window_id = 2000
		self.selected = None
		self.make_menu()

	def onInit(self):
		self.add_items(self.window_id, self.item_list)
		self.setFocusId(self.window_id)
		self.select_item(self.window_id, 0)

	def run(self):
		self.doModal()
		self.clearProperties()
		return self.selected

	def onAction(self, action):
		if action in self.closing_actions: self.setFocusId(11)
		elif action in self.selection_actions:
			focus_id = self.getFocusId()
			if focus_id == 2000:
				chosen_listitem = self.get_listitem(self.window_id)
				self.current_setting = self.selected = chosen_listitem.getProperty('highlight')
				self.setFocusId(10)
			elif focus_id == 10: self.close()
			elif focus_id == 11:
				self.selected = None
				self.close()
			else:
				color_value = self.color_input()
				if not color_value: return
				self.current_setting = self.selected = color_value
				self.close()

	def make_menu(self):
		def builder():
			for count, item in enumerate(color_palette):
				try:
					listitem = self.make_listitem()
					listitem.setProperty('highlight', item)
					yield listitem
				except: pass
		self.item_list = list(builder())

	def color_input(self):
		color_value = kodi_dialog().input('Enter Highight Color Value', defaultt=self.current_setting)
		if not color_value: return None
		color_value = color_value.upper()
		if not color_value.isalnum() or not color_value.startswith('FF') or not len(color_value) == 8:
			ok_dialog(text='Value must begin with [B]FF[/B], be [B]8[/B] characters in length and be [B]Alphanumeric[/B].[CR][CR]Please try again..')
			return self.color_input()
		return color_value
