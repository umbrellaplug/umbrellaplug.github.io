# -*- coding: utf-8 -*-
from windows.base_window import BaseDialog, json, select_dialog, confirm_dialog, ok_dialog
# from modules.kodi_utils import logger

status_property_string = 'download_status.%s'

class DownloadsManager(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
		self.window_id = 2500
		self.closed = False
		self.position = 0

	def onInit(self):
		self.make_active_downloads(first_run=True)
		self.monitor()

	def run(self):
		self.doModal()
		self.clearProperties()

	def onAction(self, action):
		if action in self.closing_actions:
			self.closed = True
			return self.close()
		else:
			if action in self.selection_actions: return self.set_status(self.get_listitem(self.window_id))

	def make_active_downloads(self, first_run=False):
		def queued_builder():
			for item in self.active_queued_downloads:
				try:
					listitem = self.make_listitem()
					listitem.setProperty('name', item.replace('.', ' ').replace('_', ' '))
					listitem.setProperty('item_id', item)
					listitem.setProperty('percent', '0')
					listitem.setProperty('status', 'queued')
					yield listitem
				except: pass
		def builder():
			for item in self.active_downloads:
				try:
					listitem = self.make_listitem()
					listitem.setProperty('name', item.replace('.', ' ').replace('_', ' '))
					listitem.setProperty('item_id', item)
					listitem.setProperty('percent', self.get_home_property(item))
					listitem.setProperty('status', self.get_status(item))
					yield listitem
				except: pass
		try:
			self.active_downloads = json.loads(self.get_home_property('active_downloads') or '[]')
			self.active_item_list = list(builder())
			self.active_queued_downloads = json.loads(self.get_home_property('active_queued_downloads') or '[]')
			self.queued_item_list = list(queued_builder())
			self.item_list = self.active_item_list + self.queued_item_list
			self.setProperty('active', str(len(self.active_item_list)))
			self.setProperty('queued', str(len(self.queued_item_list)))
			self.add_items(self.window_id, self.item_list)
			if first_run: self.setFocusId(self.window_id)
			else: self.select_item(self.window_id, self.position)
		except: pass

	def get_status(self, item_id):
		return self.get_home_property(status_property_string % item_id)

	def set_status(self, list_item):
		choices = []
		item_id = list_item.getProperty('item_id')
		status = self.get_status(item_id)
		if status == 'queued': choices.append(('Full Filename', 'filename'))
		elif status == 'paused': choices.append(('Resume Download', 'unpaused'))
		else: choices.append(('Pause Download', 'paused'))
		choices.append(('Cancel Download', 'cancelled'))
		choices.append(('Full Filename', 'filename'))
		list_items = [{'line1': i[0]} for i in choices]
		kwargs = {'items': json.dumps(list_items), 'narrow_window': 'true'}
		status_choice = select_dialog([i[1] for i in choices], **kwargs)
		if status_choice == None: return
		if status_choice == 'filename': return ok_dialog(text=list_item.getProperty('name'))
		if status_choice == 'cancelled' and not confirm_dialog(): return
		return self.set_home_property(status_property_string % item_id, status_choice)

	def monitor(self):
		while not self.closed:
			if not self.active_downloads and not self.active_queued_downloads: break
			self.sleep(2500)
			self.position = self.get_position(self.window_id)
			self.reset_window(self.window_id)
			self.make_active_downloads()
