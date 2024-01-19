# -*- coding: utf-8 -*-
"""
	Umbrella Add-on (added by Umbrella Dev 01/07/23 Updated 1/21/23)
"""

from resources.lib.modules import control
from xml.dom.minidom import parseString as mdStringParse
import os
from io import BytesIO
from zipfile import ZipFile
from urllib.request import urlopen
import xbmcvfs

getLS = control.lang
getSetting = control.setting
LOGINFO = 1

class iconPackHandler:
	name = "iconPack"
	def __init__(self):
		self.hosters = None

	def show_skin_packs(self):
		try:
			control.busy()
			self.list = self.get_skin_packs()
			control.hide()
			from resources.lib.windows.icon_packs import IconPacksView
			window = IconPacksView('icon_packs.xml', control.addonPath(control.addonId()), results=self.list)
			selected_items = window.run()
			del window
			if selected_items:
				if control.setting('debug.level') == '1':
					from resources.lib.modules import log_utils
					log_utils.log('selected items: %s' % str(selected_items), 1)
			control.hide()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			control.hide()

	def get_skin_packs(self):
		self.list1 = []
		directory = control.iconFolders()
		subfolders = [ f.name for f in os.scandir(directory) if f.is_dir() ]
		#we need to walk the directory now and get all the pre-installed skin packs
		try:
			import requests
			repo_xml = requests.get('https://raw.githubusercontent.com/umbrellaplug/umbrellaplug.github.io/master/matrix/xml/skinpack/Skins.xml')
			if not repo_xml.status_code == 200:
				from resources.lib.modules import log_utils
				return log_utils.log('Could not connect to remote repo XML: status code = %s' % repo_xml.status_code, level=log_utils.LOGINFO)
			root = mdStringParse(repo_xml.text)
			webskins = root.getElementsByTagName("skin")
			for count, item in enumerate(webskins, 1):
				try:
					label = item.childNodes[1].firstChild.data
					url = item.childNodes[3].firstChild.data
					imageurl = item.childNodes[5].firstChild.data
					if str(label).lower() in subfolders:
						downloaded = 1
					else:
						downloaded = 0
					listitem = {"name": label, "url": url, "imageurl": imageurl, "downloaded": str(downloaded)}
					self.list1.append(listitem)
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
		except:
			from resources.lib.modules import log_utils
			log_utils.log('Error getting skin packs from github.', 1)
		return self.list1

	def set_active_skin_pack(self, skinpack):
		#control.setSetting('appearance.1', str(skinpack))
		control.homeWindow.setProperty('umbrella.updateSettings', 'false')
		control.setSetting('skin.pack', str(skinpack))
		control.homeWindow.setProperty('umbrella.updateSettings', 'true')
		control.setSetting('skinpackicons', str(skinpack))
		control.openSettings('0.0', 'plugin.video.umbrella')

	def download_skin_pack(self, skinpack, url, imageurl):
		def download_and_unzip(url):
			try:
				http_response = urlopen(url)
				control.notification(title='Downloading', message='Downloading icon package.', icon=imageurl, time=3000)
				zipfile = ZipFile(BytesIO(http_response.read()))
				dest = control.joinPath(control.iconFolders())
				zipfile.extractall(path=dest)
			except:
				return control.notification(title='Download Issue', message='There was an issue downloading skin package.', icon=imageurl, time=3000)
			control.hide()
			if not control.yesnoDialog(getLS(40386), '', ''): return self.show_skin_packs()
			self.set_active_skin_pack(skinpack)
		control.busy()
		download_and_unzip(url)
		

	def delete_skin_pack(self, skinpack, imageurl):
		control.busy()
		try:
			def delete_folder(path=None):
				''' Delete objects and folder
				'''
				delete_path = path is not None
				path = path or control.joinPath(control.iconFolders(),skinpack)
				dirs, files = xbmcvfs.listdir(path)
				delete_recursive(path, dirs)
				for file in files:
					xbmcvfs.delete(os.path.join(path, file))
				if delete_path:
					xbmcvfs.rmdir(path)
				control.hide()
				self.show_skin_packs()
			def delete_recursive(path, dirs):
				''' Delete files and dirs recursively.
				'''
				for directory in dirs:
					dirs2, files = xbmcvfs.listdir(os.path.join(path, directory))
					for file in files:
						xbmcvfs.delete(os.path.join(path, directory, file))

					delete_recursive(os.path.join(path, directory), dirs2)
					xbmcvfs.rmdir(os.path.join(path, directory))
			delete_folder(path=control.joinPath(control.iconFolders(),skinpack))
		except:
			from resources.lib.modules import log_utils
			log_utils.error()