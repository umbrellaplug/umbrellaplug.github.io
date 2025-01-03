# -*- coding: utf-8 -*-
import json
from windows.base_window import BaseDialog, window_manager, select_dialog
from indexers.people import person_data_dialog
from indexers.dialogs import favorites_choice
from modules.settings import download_directory
from modules.kodi_utils import addon_fanart, get_icon, nextpage
# from modules.kodi_utils import logger

backup_thumbnail = get_icon('genre_family')

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
				thumb_params = json.loads(chosen_listitem.getProperty('action'))
				mode = thumb_params['mode']
				if mode == 'imageviewer':
					thumb_params['current_index'] = position
					ending_position = self.ImagesInstance.run(thumb_params)
					self.select_item(self.window_id, ending_position)
				elif mode == 'person_data_dialog':
					person_data_dialog(thumb_params)
		elif action in self.context_actions:
			if chosen_listitem.getProperty('next_page_item') == 'true': return
			in_favorites = chosen_listitem.getProperty('in_favorites') == 'true'
			enable_favorite = chosen_listitem.getProperty('fav_enabled') == 'true' or in_favorites
			choice = self.make_context_menu(enable_delete=chosen_listitem.getProperty('delete') == 'true', enable_favorite=enable_favorite)
			if choice:
				if choice == 'delete_image': return self.reset_after_delete(chosen_listitem, position)
				elif choice == 'download_image':
					name, thumb, path = chosen_listitem.getProperty('name'), chosen_listitem.getProperty('thumb'), chosen_listitem.getProperty('path')
					if not path: return self.notification('No Image Path to Download')
					params = {'mode': 'downloader.runner', 'action': 'image', 'name': name, 'thumb_url': thumb, 'image_url': path, 'media_type': 'image', 'image': path}
					self.execute_code('RunPlugin(%s)' % self.build_url(params))
				elif choice == 'manage_favorite':
					actor_id = chosen_listitem.getProperty('actor_id')
					actor_image = chosen_listitem.getProperty('actor_image') or chosen_listitem.getProperty('path')
					title = '%s|%s|%s' % (chosen_listitem.getProperty('actor_name'), chosen_listitem.getProperty('thumb'), actor_image)
					action = favorites_choice({'media_type': 'people', 'tmdb_id': actor_id, 'title': title, 'refresh': 'false'})
					if in_favorites and action == 'Remove From Favorites?': self.reset_after_favorite_delete(position)
				else:#exit_image
					return self.close()

	def make_page(self):
		try:
			self.set_properties()
			if self.next_page_params.get('page_no', 'final_page') != 'final_page': self.make_next_page()
			self.add_items(self.window_id, self.list_items)
			self.setFocusId(self.window_id)
		except: pass

	def make_context_menu(self, enable_delete, enable_favorite):
		choices = []
		choices_append = choices.append
		if enable_delete: choices_append(('Delete', 'delete_image'))
		else: choices_append(('Download File', 'download_image'))
		if enable_favorite: choices_append(('Favorites Manager', 'manage_favorite'))
		if self.current_page > 1: choices_append(('Exit Images', 'exit_image'))
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
			listitem.setProperties({'name': 'Next Page (%s) >>' % str(self.current_page + 1), 'thumb': nextpage, 'next_page_item': 'true'})
			self.list_items.append(listitem)
		except: pass

	def reset_after_delete(self, choice, position):
		self.ImagesInstance.delete_image(choice.getProperty('path'), choice.getProperty('thumb'))
		self.reset_window(self.window_id)
		self.list_items = self.ImagesInstance.browser_image(download_directory('image'), return_items=True)
		self.make_page()
		self.select_item(self.window_id, position)

	def reset_after_favorite_delete(self, position):
		self.reset_window(self.window_id)
		self.list_items = self.ImagesInstance.favorite_people_list_image_results(return_items=True)
		self.make_page()
		self.select_item(self.window_id, position)

	def set_properties(self):
		self.setProperty('page_no', str(self.current_page))
		self.setProperty('fanart', addon_fanart())
		self.setProperty('backup_thumbnail', backup_thumbnail)

class ImageViewer(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
		self.window_id = 5000
		self.all_images = kwargs.get('all_images')
		self.index = kwargs.get('index')
		self.scroll_ids = (self.left_action, self.right_action)
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
					listitem.setProperties({'image': item[0], 'title': item[1]})
					yield listitem
				except: pass
		self.item_list = list(builder())

	def set_properties(self):
		self.setProperty('fanart', addon_fanart())
		self.setProperty('backup_thumbnail', backup_thumbnail)
