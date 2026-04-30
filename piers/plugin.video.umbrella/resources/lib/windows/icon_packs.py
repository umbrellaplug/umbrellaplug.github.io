# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from json import dumps as jsdumps
from urllib.parse import quote_plus
import xbmc
from resources.lib.modules.control import dialog, setting as getSetting, addonFanart
from resources.lib.windows.base import BaseDialog



class IconPacksView(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, args)
		self.window_id = 2050
		self.results = kwargs.get('results')
		self.selected_items = []
		self.activePack = getSetting('skinpackicons').lower()
		self.fanart = addonFanart()
		self.make_items()
		self.highlight_color = getSetting('highlight.color')
		self.set_properties()

	def onInit(self):
		win = self.getControl(self.window_id)
		win.addItems(self.item_list)
		self.setFocusId(self.window_id)

	def run(self):
		self.doModal()
		self.clearProperties()
		return self.selected_items

	# def onClick(self, controlID):
		# from resources.lib.modules import log_utils
		# log_utils.log('controlID=%s' % controlID)

	def onAction(self, action):
		try:
			if action in self.selection_actions:
				focus_id = self.getFocusId()
				if focus_id == 2050: # listItems
					position = self.get_position(self.window_id)
					chosen_listitem = self.item_list[position]
					if chosen_listitem.getProperty('umbrella.isSelected') == 'true':
						chosen_listitem.setProperty('umbrella.isSelected', '')
					else:
						chosen_listitem.setProperty('umbrella.isSelected', 'true')
					cm = []
					chosen_listitem = self.item_list[self.get_position(self.window_id)]
					packname = chosen_listitem.getProperty('umbrella.title')
					downloaded = chosen_listitem.getProperty('umbrella.downloaded')
					url = chosen_listitem.getProperty('umbrella.downloadurl')
					active = chosen_listitem.getProperty('umbrella.active')
					poster = chosen_listitem.getProperty('umbrella.imageurl')
					if downloaded == '1' and active == '0' and str(packname).lower() != 'umbrella':
						cm += [('[B]Set as Active Pack[/B]', 'activepack')]
						cm += [('[B]Delete Pack[/B]', 'deletepack')]
					elif downloaded == '1' and active == '0':
						cm += [('[B]Set as Active Pack[/B]', 'activepack')]
					elif downloaded == '0':
						cm += [('[B]Download Pack[/B]', 'downloadpack')]
					else:
						return
					chosen_cm_item = dialog.contextmenu([i[0] for i in cm])
					if chosen_cm_item == -1: return
					cm_action = cm[chosen_cm_item][1]
					if cm_action == 'activepack':
						from resources.lib.modules import skin_packs
						skin_packs.iconPackHandler().set_active_skin_pack(packname)
						self.close()
					elif cm_action == 'downloadpack':
						from resources.lib.modules import skin_packs
						skin_packs.iconPackHandler().download_skin_pack(packname, url, poster)
						self.close()
					elif cm_action == 'deletepack':
						self.close()
						from resources.lib.modules import skin_packs
						skin_packs.iconPackHandler().delete_skin_pack(packname, poster)
				elif focus_id == 2051: # OK Button
					self.close()
					self.selected_items = None
			elif action in self.closing_actions:
				self.selected_items = None
				self.close()


		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			self.close()

	def make_items(self):
		def builder():
			for count, item in enumerate(self.results, 1):
				try:
					listitem = self.make_listitem()
					listitem.setProperty('umbrella.title', item.get('name'))
					listitem.setProperty('umbrella.isSelected', '')
					poster = item.get('imageurl', '')
					listitem.setProperty('umbrella.poster', poster)
					listitem.setProperty('umbrella.downloadurl', item.get('url'))
					listitem.setProperty('umbrella.downloaded', item.get('downloaded'))
					if str(item.get('name')).lower() == self.activePack:
						listitem.setProperty('umbrella.active', '1')
					else:
						listitem.setProperty('umbrella.active', '0')
					yield listitem
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
		try:
			self.item_list = list(builder())
			self.total_results = str(len(self.item_list))
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def set_properties(self):
		try:
			self.setProperty('umbrella.highlight.color', self.highlight_color)
			self.setProperty('umbrella.fanart', self.fanart)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()