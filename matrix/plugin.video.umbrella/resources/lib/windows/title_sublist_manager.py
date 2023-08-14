# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from resources.lib.modules import sources
from resources.lib.modules.control import joinPath, artPath, setting as getSetting
from resources.lib.windows.base import BaseDialog


class TitleSublistManagerXML(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, args)
		self.window_id = 2050
		self.results = kwargs.get('results')
		self.total_results = str(len(self.results))
		self.selected_items = []
		self.highlight_color = getSetting('highlight.color')
		self.make_items()
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
					org_id = chosen_listitem.getProperty('umbrella.originalTitle')
					if chosen_listitem.getProperty('umbrella.isSelected') == 'true':
						chosen_listitem.setProperty('umbrella.isSelected', '')
						if org_id in str(self.selected_items):
							pos = next((index for (index, d) in enumerate(self.selected_items) if d["originalTitle"] == org_id), None)
							self.selected_items.pop(pos)
					else:
						chosen_listitem.setProperty('umbrella.isSelected', 'true')
						original_title = chosen_listitem.getProperty('umbrella.originalTitle')
						sub_title = chosen_listitem.getProperty('umbrella.subTitle')
						self.selected_items.append({'ID': None, 'originalTitle': original_title, 'subTitle': sub_title})
				elif focus_id == 2051: # OK Button
					self.close()
				elif focus_id == 2052: # Cancel Button
					self.selected_items = None
					self.close()
				elif focus_id == 2053: # Add Button
					from resources.lib.modules import sources
					self.close()
					sources.Sources().addNewSub()
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
					listitem.setProperty('umbrella.originalTitle', item.get('originalTitle'))
					listitem.setProperty('umbrella.subTitle', str(item.get('subTitle')))
					listitem.setProperty('umbrella.isSelected', '')
					listitem.setProperty('umbrella.count', '%02d.)' % count)
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
			self.setProperty('umbrella.total_results', self.total_results)
			self.setProperty('umbrella.highlight.color', self.highlight_color)
			self.setProperty('umbrella.umbrella_icon', joinPath(artPath(), 'icon.png'))
		except:
			from resources.lib.modules import log_utils
			log_utils.error()