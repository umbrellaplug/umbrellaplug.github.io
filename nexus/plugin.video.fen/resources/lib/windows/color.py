# -*- coding: utf-8 -*-
from windows.base_window import BaseDialog
from modules.kodi_utils import colorpalette_path
from modules.meta_lists import palette_basic, palette_material_design, palette_web, palette_rainbow
from modules.kodi_utils import dialog, ok_dialog, path_join, local_string as ls
from modules.kodi_utils import logger

button_ids = (10, 11)
palettes = {'basic': palette_basic, 'material_design': palette_material_design, 'webcolors': palette_web, 'rainbow': palette_rainbow}
palette_list = ['basic', 'material_design', 'webcolors', 'rainbow']
logger('colorpalette_path', colorpalette_path)

class SelectColor(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
		self.kwargs = kwargs
		self.current_setting = self.kwargs.get('current_setting')
		self.window_id = 2000
		self.selected = None
		self.texture_location = path_join(colorpalette_path, '%s.png')
		self.current_palette = palette_list[3]
		self.make_menu()
		self.set_properties()

	def onInit(self):
		if not self.palette_check():
			self.notification(33111, duration=5000)
			self.close()
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
				self.current_setting = chosen_listitem.getProperty('label')
				self.selected = self.current_setting
				self.setFocusId(10)
			elif focus_id == 10: self.close()
			elif focus_id == 11:
				self.selected = None
				self.close()
			elif focus_id == 12:
				color_value = self.color_input()
				if not color_value: return
				self.current_setting = color_value
				self.selected = self.current_setting
				self.close()
			else: self.palette_switcher()

	def make_menu(self):
		def builder():
			for count, item in enumerate(palettes[self.current_palette]):
				try:
					listitem = self.make_listitem()
					listitem.setProperty('label', item)
					listitem.setProperty('image', self.texture_location % item)
					yield listitem
				except: pass
		current_palette = palettes[self.current_palette]
		self.item_list = list(builder())

	def set_properties(self):
		self.setProperty('current_palette', self.current_palette)
		self.setProperty('current_palette_name', self.current_palette.capitalize())

	def palette_switcher(self):
		try: self.current_palette = palette_list[palette_list.index(self.current_palette) + 1]
		except: self.current_palette = palette_list[0]
		self.reset_window(self.window_id)
		self.set_properties()
		self.make_menu()
		self.add_items(self.window_id, self.item_list)

	def palette_check(self):
		if self.path_exists(colorpalette_path): status = True
		else:
			self.busy_dialog()
			try:
				from zipfile import ZipFile
				from modules.kodi_utils import colorpalette_zip_path, userdata_path
				zipfile = ZipFile(colorpalette_zip_path)
				zipfile.extractall(path=userdata_path)
				if self.path_exists(colorpalette_path): status = True
				else: status = False
			except: status = False
			self.busy_dialog('false')
		return status

	def color_input(self):
		color_value = dialog.input(ls(32047), defaultt=self.current_setting)
		if not color_value: return None
		color_value = color_value.upper()
		if not color_value.isalnum() or not color_value.startswith('FF') or not len(color_value) == 8:
			ok_dialog(text=32153)
			return self.color_input()
		return color_value

	def busy_dialog(self, state='true'):
		self.setProperty('show_busy_dialog', state)
