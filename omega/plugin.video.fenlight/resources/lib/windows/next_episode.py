# -*- coding: utf-8 -*-
import time
from windows.base_window import BaseDialog
# from modules.kodi_utils import logger

pause_time_before_end, hold_pause_time = 10, 900
episode_flag_base = 'fenlight_flags/episodes/%s.png'
button_actions = {10: 'close', 11: 'play', 12: 'cancel'}
episode_status_dict = {
'season_premiere': 'b30385b5',
'mid_season_premiere': 'b385b503',
'series_finale': 'b38503b5',
'season_finale': 'b3b50385',
'mid_season_finale': 'b3b58503',
'':  ''}

class NextEpisode(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
		self.closed = False
		self.meta = kwargs.get('meta')
		self.selected = kwargs.get('default_action', 'cancel')
		self.set_properties()

	def onInit(self):
		self.setFocusId(11)
		self.monitor()

	def run(self):
		self.doModal()
		self.clearProperties()
		self.clear_modals()
		return self.selected

	def onAction(self, action):
		if action in self.closing_actions:
			self.selected = 'close'
			self.closed = True
			self.close()

	def onClick(self, controlID):
		self.selected = button_actions[controlID]
		self.closed = True
		self.close()

	def set_properties(self):
		episode_type = self.meta.get('episode_type', '')
		self.setProperty('thumb', self.meta.get('ep_thumb', None) or self.meta.get('fanart', ''))
		self.setProperty('clearlogo', self.meta.get('clearlogo', ''))
		self.setProperty('episode_label', '%s[B] | [/B]%02dx%02d[B] | [/B]%s' % (self.meta['title'], self.meta['season'], self.meta['episode'], self.meta['ep_name']))
		self.setProperty('episode_status.highlight', episode_status_dict[episode_type])
		self.setProperty('episode_status.flag', episode_flag_base % episode_type)

	def monitor(self):
		total_time = self.player.getTotalTime()
		while self.player.isPlaying():
			remaining_time = round(total_time - self.player.getTime())
			if self.closed: break
			elif self.selected == 'pause' and remaining_time <= pause_time_before_end:
				self.player.pause()
				self.sleep(500)
				break
			self.sleep(1000)
		if self.selected == 'pause':
			start_time = time.time()
			end_time = start_time + hold_pause_time
			current_time = start_time
			while current_time <= end_time and self.selected == 'pause':
				try:
					current_time = time.time()
					pause_timer = time.strftime('%M:%S', time.gmtime(max(end_time - current_time, 0)))
					self.setProperty('pause_timer', pause_timer)
					self.sleep(1000)
				except: break
			if self.selected != 'cancel': self.player.pause()
		self.close()
