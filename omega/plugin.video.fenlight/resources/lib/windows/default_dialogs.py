# -*- coding: utf-8 -*-
import json
from windows.base_window import BaseDialog
# from modules.kodi_utils import logger

ok_id, cancel_id, selectall_id, deselectall_id = 10, 11, 12, 13
button_ids = (ok_id, cancel_id, selectall_id, deselectall_id)
select_deselect_ids = (selectall_id, deselectall_id)
confirm_dict = {10: True, 11: False}

class Select(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
		self.window_id = 2025
		self.kwargs = kwargs
		self.enumerate = self.kwargs.get('enumerate', 'false')
		self.multi_choice = self.kwargs.get('multi_choice', 'false')
		self.multi_line = self.kwargs.get('multi_line', 'false')
		self.preselect = self.kwargs.get('preselect', [])
		self.items = json.loads(self.kwargs['items'])
		self.heading = self.kwargs.get('heading', '')
		self.media_type = self.kwargs.get('media_type', '')
		self.narrow_window = self.kwargs.get('narrow_window', 'false')
		self.enable_context_menu = self.kwargs.get('enable_context_menu', 'false') == 'true'
		self.item_list = []
		self.chosen_indexes = []
		self.selected = None
		self.set_properties()
		self.make_menu()

	def onInit(self):
		self.add_items(self.window_id, self.item_list)
		if self.preselect:
			if len(self.preselect) == len(self.item_list): self.setProperty('select_button', 'deselect_all')
			for index in self.preselect:
				self.item_list[index].setProperty('check_status', 'checked')
				self.chosen_indexes.append(index)
		self.setFocusId(self.window_id)

	def run(self):
		self.doModal()
		self.clearProperties()
		return self.selected

	def onClick(self, controlID):
		self.control_id = None
		if controlID in button_ids:
			if controlID == ok_id:
				self.selected = sorted(self.chosen_indexes)
				self.close()
			elif controlID == cancel_id:
				self.close()
			elif controlID in select_deselect_ids:
				item_list_indexes = list(range(0, len(self.item_list)))
				if controlID == selectall_id: status, select_property, self.chosen_indexes = 'checked', 'deselect_all', item_list_indexes
				else: status, select_property, self.chosen_indexes = '', 'select_all', []
				for index in item_list_indexes: self.item_list[index].setProperty('check_status', status)
				self.setProperty('select_button', select_property)
				try: self.setFocusId(ok_id)
				except: pass
		else: self.control_id = controlID

	def onAction(self, action):
		chosen_listitem = self.get_listitem(self.window_id)
		if action in self.selection_actions:
			if not self.control_id: return
			position = self.get_position(self.window_id)
			if self.multi_choice == 'true':
				if chosen_listitem.getProperty('check_status') == 'checked':
					chosen_listitem.setProperty('check_status', '')
					self.chosen_indexes.remove(position)
				else:
					chosen_listitem.setProperty('check_status', 'checked')
					self.chosen_indexes.append(position)
			else:
				self.selected = position
				return self.close()
		elif action in self.context_actions or action in self.closing_actions: return self.close()

	def make_menu(self):
		def builder():
			for count, item in enumerate(self.items, 1):
				listitem = self.make_listitem()
				if enum: line1 = '%02d. %s' % (count, item['line1'])
				else: line1 = item['line1']
				if 'line2' in item: line2 = item['line2']
				else: line2 = ''
				if 'icon' in item: listitem.setProperty('icon', item['icon'])
				else: listitem.setProperty('icon', '')
				listitem.setProperty('line1', line1)
				listitem.setProperty('line2', line2)
				yield listitem
		enum = self.enumerate == 'true'
		self.item_list = list(builder())

	def set_properties(self):
		self.setProperty('multi_choice', self.multi_choice)
		self.setProperty('multi_line', self.multi_line)
		self.setProperty('select_button', 'select_all')
		self.setProperty('heading', self.heading)
		self.setProperty('narrow_window', self.narrow_window)

class Confirm(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
		self.ok_label = kwargs['ok_label']
		self.cancel_label = kwargs['cancel_label']
		self.text = kwargs['text']
		self.heading = kwargs['heading']
		self.default_control = kwargs['default_control']
		self.selected = None
		self.set_properties()

	def onInit(self):
		self.setFocusId(self.default_control)

	def run(self):
		self.doModal()
		return self.selected

	def onClick(self, controlID):
		self.selected = confirm_dict[controlID]
		self.close()

	def onAction(self, action):
		if action in self.closing_actions: self.close()

	def set_properties(self):
		self.setProperty('ok_label', self.ok_label)
		self.setProperty('cancel_label', self.cancel_label)
		self.setProperty('text', self.text)
		self.setProperty('heading', self.heading)

class OK(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
		self.ok_label = kwargs.get('ok_label')
		self.text = kwargs['text']
		self.heading = kwargs['heading']
		self.set_properties()

	def run(self):
		self.doModal()

	def onClick(self, controlID):
		self.close()

	def onAction(self, action):
		if action in self.closing_actions:
			self.close()

	def set_properties(self):
		self.setProperty('ok_label', self.ok_label)
		self.setProperty('text', self.text)
		self.setProperty('heading', self.heading)
