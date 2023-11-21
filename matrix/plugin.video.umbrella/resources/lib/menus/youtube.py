# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from resources.lib.modules.control import directory as endOfDirectory, setting as getSetting
from resources.lib.modules import youtube_menu


class yt_index:  # initializes as musicvids, functions can override based on action and subid.
	def __init__(self):
		self.action = 'musicvids'
		self.base_url = 'https://raw.githubusercontent.com/umbrellaplug/umbrellaplug.github.io/master/matrix/xml/youtube/'
		self.mainmenu = self.base_url + 'musicvids.txt'
		self.submenu = '%s/%s.txt'
		self.default_icon = '%s/icons/music_video_folder_icon.png'
		self.default_fanart = '%s/icons/music_video_folder_fanart.jpg'
		self.useContainerTitles = getSetting('enable.containerTitles') == 'true'

	def init_vars(self, action):
		try:
			if action == 'youtube':
				self.action = 'youtube'
				self.base_url = 'https://raw.githubusercontent.com/umbrellaplug/umbrellaplug.github.io/master/matrix/xml/youtube/'
				self.mainmenu = self.base_url + 'ytmain.txt'
			self.submenu = self.submenu % (self.base_url, '%s')
			self.default_icon = self.default_icon % (self.base_url)
			self.default_fanart = self.default_fanart % (self.base_url)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def root(self, action, folderName=''):
		try:
			self.init_vars(action)
			from resources.lib.modules import control
			if self.useContainerTitles: control.setContainerName(folderName)
			menuItems = youtube_menu.youtube_menu().processMenuFile(self.mainmenu)
			for name, section, searchid, subid, playlistid, channelid, videoid, iconimage, fanart, description in menuItems:
				if subid != 'false': # Means this item points to a submenu
					youtube_menu.youtube_menu().addMenuItem(name, self.action, subid, iconimage, fanart, description, True)
				elif searchid != 'false': # Means this is a search term
					youtube_menu.youtube_menu().addSearchItem(name, searchid, iconimage, fanart)
				elif videoid != 'false': # Means this is a video id entry
					youtube_menu.youtube_menu().addVideoItem(name, videoid, iconimage, fanart)
				elif channelid != 'false': # Means this is a channel id entry
					if channelid.startswith('UC'):
						youtube_menu.youtube_menu().addChannelItem(name, channelid, iconimage, fanart)
					else:
						youtube_menu.youtube_menu().addUserItem(name, channelid, iconimage, fanart) # This really needs it's own userid created in the .txt files
				elif playlistid != 'false': # Means this is a playlist id entry
					youtube_menu.youtube_menu().addPlaylistItem(name, playlistid, iconimage, fanart)
				elif section != 'false': # Means this is a section placeholder/info line
					youtube_menu.youtube_menu().addSectionItem(name, self.default_icon, self.default_fanart)
			self.endDirectory()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def get(self, action, subid):
		try:
			self.init_vars(action)
			thisMenuFile = self.submenu % (subid)
			menuItems = youtube_menu.youtube_menu().processMenuFile(thisMenuFile)
			for name, section, searchid, subid, playlistid, channelid, videoid, iconimage, fanart, description in menuItems:
				if subid != 'false': # Means this item points to a submenu
					youtube_menu.youtube_menu().addMenuItem(name, self.action, subid, iconimage, fanart, description, True)
				elif searchid != 'false': # Means this is a search term
					youtube_menu.youtube_menu().addSearchItem(name, searchid, iconimage, fanart)
				elif videoid != 'false': # Means this is a video id entry
					youtube_menu.youtube_menu().addVideoItem(name, videoid, iconimage, fanart)
				elif channelid != 'false': # Means this is a channel id entry
					if channelid.startswith('UC'):
						youtube_menu.youtube_menu().addChannelItem(name, channelid, iconimage, fanart)
					else:
						youtube_menu.youtube_menu().addUserItem(name, channelid, iconimage, fanart) # This really needs it's own userid created in the .txt files
				elif playlistid != 'false': # Means this is a playlist id entry
					youtube_menu.youtube_menu().addPlaylistItem(name, playlistid, iconimage, fanart)
				elif section != 'false': # Means this is a section placeholder/info line
					youtube_menu.youtube_menu().addSectionItem(name, self.default_icon, self.default_fanart)
			self.endDirectory()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def endDirectory(self):
		from sys import argv # some functions throw invalid handle -1 unless this is imported here.
		endOfDirectory(int(argv[1]), cacheToDisc=True)