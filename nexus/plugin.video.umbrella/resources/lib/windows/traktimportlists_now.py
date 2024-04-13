# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from resources.lib.modules.control import joinPath, artPath, dialog, setting as getSetting
from resources.lib.modules.library import lib_tools
from resources.lib.windows.base import BaseDialog
from resources.lib.modules import control


class TraktImportListsNowXML(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, args)
		self.window_id = 2050
		self.results = kwargs.get('results')
		self.highlight_color = getSetting('highlight.color')
		self.total_results = str(len(self.results))
		self.selected_items = []
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
					trakt_id = chosen_listitem.getProperty('umbrella.trakt_id')
					if chosen_listitem.getProperty('umbrella.isSelected') == 'true':
						chosen_listitem.setProperty('umbrella.isSelected', '')
						if trakt_id in str(self.selected_items):
							pos = next((index for (index, d) in enumerate(self.selected_items) if d["trakt_id"] == trakt_id), None)
							self.selected_items.pop(pos)
					else:
						chosen_listitem.setProperty('umbrella.isSelected', 'true')
				elif focus_id == 2051: # OK Button
					self.selected_items = []
					for item in self.item_list:
						if item.getProperty('umbrella.isSelected') == 'true':
							self.selected_items.append({'type': item.getProperty('umbrella.action'), 'list_name': item.getProperty('umbrella.list_name'), 'url': item.getProperty('umbrella.url')})
					itemtopass = self.selected_items
					self.close()
					if len(itemtopass) > 0:
						lib_tools().importNow(itemtopass)
				elif focus_id == 2052: # Cancel Button
					self.selected_items = None
					self.close()
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
					isMovie = ''
					isTVShow = ''
					isMixed = ''
					if item.get('action').split('&')[0] == 'movies':
						isMovie = 'true'
					if item.get('action').split('&')[0] == 'tvshows':
						isTVShow = 'true'
					if item.get('action').split('&')[0] == 'mixed':
						isMixed = 'true'
					listitem = self.make_listitem()
					listitem.setProperty('umbrella.list_owner', item.get('list_owner'))
					listitem.setProperty('umbrella.list_name', str(item.get('list_name')))
					listitem.setProperty('umbrella.list_owner_slug', str(item.get('list_owner_slug')))
					listitem.setProperty('umbrella.trakt_id', str(item.get('list_id')))
					listitem.setProperty('umbrella.item_count', str(item.get('list_count')))
					listitem.setProperty('umbrella.likes', str(item.get('likes')))
					listitem.setProperty('umbrella.action', str(item.get('action')))
					listitem.setProperty('umbrella.isMovie', isMovie)
					listitem.setProperty('umbrella.isTVShow', isTVShow)
					listitem.setProperty('umbrella.isMixed', isMixed)
					listitem.setProperty('umbrella.isSelected', item.get('selected'))
					listitem.setProperty('umbrella.url', item.get('url'))
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
			self.setProperty('umbrella.trakt_icon', joinPath(artPath(), 'trakt.png'))
		except:
			from resources.lib.modules import log_utils
			log_utils.error()