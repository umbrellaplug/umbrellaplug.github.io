# -*- coding: utf-8 -*-
from windows.base_window import BaseDialog
from modules.utils import change_image_resolution
from modules.kodi_utils import json, empty_poster, addon_fanart, notification
from modules.settings import get_art_provider
# from modules.kodi_utils import logger

list_ids = {'poster': 2020, 'fanart': 2021, 'clearlogo': 2022, 'banner': 2023, 'clearart': 2024, 'landscape': 2025, 'discart': 2026, 'keyart': 2027}
custom_key, count_name, count_insert = 'custom_%s', '%s.number', 'x%s'

class SelectArtwork(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
		self.kwargs = kwargs
		self.kwargs_get = self.kwargs.get
		self.images = self.kwargs_get('images')
		self.meta = self.kwargs_get('meta')
		self.meta_get = self.meta.get
		self.selected = {}
		self.active_items = []
		self.get_starting_artwork()

	def onInit(self):
		for image_type, image_list in self.images.items(): self.make_menu(image_type, image_list)
		if not self.active_items:
			notification(33069, 2000)
			return self.close()
		self.setFocusId(sorted(self.active_items)[0])

	def run(self):
		self.doModal()
		self.clearProperties()
		return self.selected

	def onAction(self, action):
		if action in self.selection_actions:
			chosen_listitem = self.get_listitem(self.getFocusId())
			if chosen_listitem.getProperty('check_status') == 'checked': return
			chosen_image_type = chosen_listitem.getProperty('image_type')
			for item in self.get_attribute(self, '%s_listitems' % chosen_image_type):
				if item.getProperty('check_status') == 'checked': item.setProperty('check_status', '')
			chosen_listitem.setProperty('check_status', 'checked')			
			chosen_image = chosen_listitem.getProperty('image')
			self.set_attribute(self, chosen_image_type, chosen_image)
			self.selected[custom_key % chosen_image_type] = chosen_image
		elif action in self.closing_actions:
			return self.close()

	def make_menu(self, image_type, image_list):
		def builder():
			for count, item in enumerate(image_list):
				try:
					listitem = self.make_listitem()
					res_prop, provider = self.image_check(item)
					listitem.setProperty('provider', provider)
					listitem.setProperty('thumbnail', change_image_resolution(item, res_prop))
					listitem.setProperty('image', item)
					listitem.setProperty('image_type', image_type)
					if item == self.get_attribute(self, image_type):
						listitem.setProperty('check_status', 'checked')
						self.focus_index = count
					else: listitem.setProperty('check_status', '')
					yield listitem
				except: pass
		try:
			self.focus_index = 0
			list_id = list_ids[image_type]
			item_list = list(builder())
			if not item_list: return
			self.setProperty(count_name % image_type, count_insert % len(item_list))
			self.set_attribute(self, '%s_listitems' % image_type, item_list)
			self.add_items(list_id, item_list)
			self.select_item(list_id, self.focus_index)
			self.add_active(list_id)
		except: pass

	def get_starting_artwork(self):
		poster_main, poster_backup, fanart_main, fanart_backup, clearlogo_main, clearlogo_backup = get_art_provider()
		self.poster = self.meta_get('custom_poster') or self.meta_get(poster_main) or self.meta_get(poster_backup) or empty_poster
		self.fanart = self.meta_get('custom_fanart') or self.meta_get(fanart_main) or self.meta_get(fanart_backup) or addon_fanart
		self.clearlogo = self.meta_get('custom_clearlogo') or self.meta_get(clearlogo_main) or self.meta_get(clearlogo_backup) or ''
		self.banner = self.meta_get('custom_banner') or self.meta_get('banner') or ''
		self.clearart = self.meta_get('custom_clearart') or self.meta_get('clearart') or ''
		self.landscape = self.meta_get('custom_landscape') or self.meta_get('landscape') or ''
		self.discart = self.meta_get('custom_discart') or self.meta_get('discart') or ''
		self.keyart = self.meta_get('custom_keyart') or self.meta_get('keyart') or ''

	def add_active(self, _id):
		self.active_items.append(_id)

	def image_check(self, image):
		if 'image.tmdb' in image: return 'w300', 'TMDb'
		else: return '/preview/', 'Fanart.tv'