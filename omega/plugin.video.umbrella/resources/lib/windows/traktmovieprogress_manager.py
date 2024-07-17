# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

import xbmc
from resources.lib.modules.control import dialog, sleep, condVisibility
from resources.lib.windows.base import BaseDialog
from resources.lib.modules.control import setting as getSetting

monitor = xbmc.Monitor()


class TraktMovieProgressManagerXML(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, args)
		self.window_id = 2050
		self.results = kwargs.get('results')
		self.total_results = str(len(self.results))
		self.selected_items = []
		self.highlight_color = getSetting('highlight.color')
		self.make_items()
		self.set_properties()
		self.hasVideo = False

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
					imdb = chosen_listitem.getProperty('umbrella.imdb')
					if chosen_listitem.getProperty('umbrella.isSelected') == 'true':
						chosen_listitem.setProperty('umbrella.isSelected', '')
						if imdb in self.selected_items: self.selected_items.remove(imdb)
					else:
						chosen_listitem.setProperty('umbrella.isSelected', 'true')
						self.selected_items.append(imdb)
				elif focus_id == 2051: # OK Button
					self.close()
				elif focus_id == 2052: # Cancel Button
					self.selected_items = None
					self.close()
				elif focus_id == 2053: # Select All Button
					for item in self.item_list:
						item.setProperty('umbrella.isSelected', 'true')
						self.selected_items.append(item.getProperty('umbrella.imdb'))
				elif focus_id == 2045: # Stop Trailer Playback Button
					self.execute_code('PlayerControl(Stop)')
					sleep(500)
					self.setFocusId(self.window_id)

			elif action in self.context_actions:
				cm = []
				chosen_listitem = self.item_list[self.get_position(self.window_id)]
				# media_type = chosen_listitem.getProperty('umbrella.media_type')
				source_trailer = chosen_listitem.getProperty('umbrella.trailer')
				if not source_trailer:
					from resources.lib.modules import trailer
					source_trailer = trailer.Trailer().worker('movie', chosen_listitem.getProperty('umbrella.title'), chosen_listitem.getProperty('umbrella.year'), None, chosen_listitem.getProperty('umbrella.imdb'))

				if source_trailer: cm += [('[B]Play Trailer[/B]', 'playTrailer')]
				chosen_cm_item = dialog.contextmenu([i[0] for i in cm])
				if chosen_cm_item == -1: return
				cm_action = cm[chosen_cm_item][1]

				if cm_action == 'playTrailer':
					self.execute_code('PlayMedia(%s, 1)' % source_trailer)
					total_sleep = 0
					while True:
						sleep(500)
						total_sleep += 500
						self.hasVideo = condVisibility('Player.HasVideo')
						if self.hasVideo or total_sleep >= 10000: break
					if self.hasVideo:
						self.setFocusId(2045)
						while (condVisibility('Player.HasVideo') and not monitor.abortRequested()):
							self.setProgressBar()
							sleep(1000)
						self.hasVideo = False
						self.progressBarReset()
						self.setFocusId(self.window_id)
					else: self.setFocusId(self.window_id)

			elif action in self.closing_actions:
				self.selected_items = None
				if self.hasVideo: self.execute_code('PlayerControl(Stop)')
				else: self.close()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			self.close()

	def setProgressBar(self):
		try: progress_bar = self.getControlProgress(2046)
		except: progress_bar = None
		if progress_bar is not None:
			progress_bar.setPercent(self.calculate_percent())

	def calculate_percent(self):
		return (xbmc.Player().getTime() / float(xbmc.Player().getTotalTime())) * 100

	def progressBarReset(self):
		try: progress_bar = self.getControlProgress(2046)
		except: progress_bar = None
		if progress_bar is not None:
			progress_bar.setPercent(0)

	def make_items(self):
		def builder():
			for count, item in enumerate(self.results, 1):
				try:
					listitem = self.make_listitem()
					listitem.setProperty('umbrella.title', item.get('title'))
					listitem.setProperty('umbrella.year', str(item.get('year')))
					# labelProgress = str(round(float(item['progress'] * 100), 1)) + '%'
					labelProgress = str(round(float(item['progress']), 1)) + '%'
					listitem.setProperty('umbrella.progress', '[' + labelProgress + ']')
					listitem.setProperty('umbrella.isSelected', '')
					listitem.setProperty('umbrella.imdb', item.get('imdb'))
					# listitem.setProperty('umbrella.tmdb', item.get('tmdb'))
					listitem.setProperty('umbrella.rating', str(round(float(item.get('rating', '0')), 1)))
					listitem.setProperty('umbrella.trailer', item.get('trailer'))
					listitem.setProperty('umbrella.studio', item.get('studio'))
					listitem.setProperty('umbrella.genre', item.get('genre', ''))
					listitem.setProperty('umbrella.duration', str(item.get('duration')))
					listitem.setProperty('umbrella.mpaa', item.get('mpaa') or 'NA')
					listitem.setProperty('umbrella.plot', item.get('plot'))
					listitem.setProperty('umbrella.poster', item.get('poster', ''))
					listitem.setProperty('umbrella.clearlogo', item.get('clearlogo', ''))
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
		except:
			from resources.lib.modules import log_utils
			log_utils.error()