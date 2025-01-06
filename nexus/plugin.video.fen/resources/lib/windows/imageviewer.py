# -*- coding: utf-8 -*-
from apis.tmdb_api import tmdb_popular_people
from windows.base_window import BaseDialog, window_manager
from indexers.people import person_data_dialog
from modules.settings import download_directory
from modules.kodi_utils import json, select_dialog, addon_fanart, get_icon, local_string as ls
# from modules.kodi_utils import logger

nextpage_str = ls(32799)
nextpage_icon = get_icon('nextpage')

class ThumbImageViewer(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
		self.window_id = 2000
		self.current_page = 1
		self.selected = None
		self.list_items = kwargs.get('list_items')
		self.next_page_params = kwargs.get('next_page_params')
		self.ImagesInstance = kwargs.get('ImagesInstance')

	def onInit(self):
		self.set_home_property('window_loaded', 'true')
		self.make_page()

	def run(self):
		self.doModal()
		self.clearProperties()

	def onAction(self, action):
		if action in self.closing_actions:
			if self.current_page == 1: return self.close()
			return self.previous_page()
		try:
			position = self.get_position(self.window_id)
			chosen_listitem = self.get_listitem(self.window_id)
		except: return
		if action in self.selection_actions:
			if chosen_listitem.getProperty('next_page_item') == 'true': self.new_page()
			else:
				thumb_params = chosen_listitem.getProperty('action')
				thumb_params = json.loads(thumb_params)
				if thumb_params['mode'] == 'imageviewer':
					thumb_params['current_index'] = position
					ending_position = self.ImagesInstance.run(thumb_params)
					self.select_item(self.window_id, ending_position)
				elif thumb_params['mode'] == 'person_data_dialog':
					person_data_dialog({'query': thumb_params['actor_name']})
		elif action in self.context_actions:
			choice = self.make_context_menu(enable_delete=chosen_listitem.getProperty('delete') == 'true')
			if choice:
				if choice == 'delete_image': return self.reset_after_delete(chosen_listitem, position)
				#download
				name, thumb, path = chosen_listitem.getProperty('name'), chosen_listitem.getProperty('thumb'), chosen_listitem.getProperty('path')
				params = {'mode': 'downloader', 'action': 'image', 'name': name, 'thumb_url': thumb, 'image_url': path, 'media_type': 'image', 'image': thumb}
				self.execute_code('RunPlugin(%s)' % self.build_url(params))

	def make_page(self):
		try:
			self.set_properties()
			if self.next_page_params.get('page_no', 'final_page') != 'final_page': self.make_next_page()
			self.add_items(self.window_id, self.list_items)
			self.setFocusId(self.window_id)
		except: pass

	def make_context_menu(self, enable_delete):
		choices = []
		choices_append = choices.append
		if enable_delete: choices_append((ls(32785), 'delete_image'))
		else: choices_append((ls(32747), 'download_image'))
		list_items = [{'line1': i[0]} for i in choices]
		kwargs = {'items': json.dumps(list_items), 'narrow_window': 'true'}
		choice = select_dialog([i[1] for i in choices], **kwargs)
		return choice

	def new_page(self):
		try:
			self.current_page += 1
			self.next_page_params['in_progress'] = 'true'
			self.list_items, self.next_page_params = self.ImagesInstance.run(self.next_page_params)
			self.reset_window(self.window_id)
			self.make_page()
		except: self.close()

	def previous_page(self):
		try:
			self.current_page -= 1
			self.next_page_params['page_no'] = self.current_page
			self.next_page_params['in_progress'] = 'true'
			self.list_items, self.next_page_params = self.ImagesInstance.run(self.next_page_params)
			self.reset_window(self.window_id)
			self.make_page()
		except: self.close()

	def make_next_page(self):
		try:
			listitem = self.make_listitem()
			listitem.setProperty('name', nextpage_str % str(self.current_page + 1))
			listitem.setProperty('thumb', nextpage_icon)
			listitem.setProperty('next_page_item', 'true')
			self.list_items.append(listitem)
		except: pass

	def reset_after_delete(self, choice, position):
		self.set_home_property('delete_image_finished', 'false')
		self.ImagesInstance.run({'mode': 'delete_image', 'image_url': choice.getProperty('path'), 'thumb_url': choice.getProperty('thumb')})
		while not self.get_home_property('delete_image_finished') == 'true': self.sleep(10)
		self.reset_window(self.window_id)
		self.list_items = self.ImagesInstance.browser_image(download_directory('image'), return_items=True)
		self.make_page()
		self.select_item(self.window_id, position)

	def set_properties(self):
		self.setProperty('page_no', str(self.current_page))
		self.setProperty('fanart', addon_fanart)

class ImageViewer(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
		self.window_id = 5000
		self.all_images = kwargs.get('all_images')
		self.index = kwargs.get('index')
		self.set_properties()
		self.make_items()

	def onInit(self):
		self.add_items(self.window_id, self.item_list)
		self.select_item(self.window_id, self.index)
		self.setFocusId(self.window_id)

	def run(self):
		self.doModal()
		return self.position

	def onAction(self, action):
		if action in self.closing_actions:
			self.position = self.get_position(self.window_id)
			self.close()

	def make_items(self):
		def builder():
			for item in self.all_images:
				try:
					listitem = self.make_listitem()
					listitem.setProperty('image', item[0])
					listitem.setProperty('title', item[1])
					yield listitem
				except: pass
		self.item_list = list(builder())

	def set_properties(self):
		self.setProperty('fanart', addon_fanart)
