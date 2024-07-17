# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""


from re import sub as re_sub
import requests
from requests.adapters import HTTPAdapter
from sys import argv
from urllib.parse import quote_plus
from urllib3.util.retry import Retry
from resources.lib.modules import control
from resources.lib.modules import string_tools
from resources.lib.modules.source_utils import supported_video_extensions

accepted_extensions = tuple(supported_video_extensions())
getLS = control.lang
furk_icon = control.joinPath(control.artPath(), 'furk.png')
addonFanart = control.addonFanart()
base_link = "https://www.furk.net/api/"
account_info_link = "account/info?api_key=%s"
search_link = "plugins/metasearch?api_key=%s&q=%s&cached=yes" \
				"&match=%s&moderated=%s%s&sort=relevance&type=video&offset=0&limit=200"
# search_direct_link = "plugins/metasearch?api_key=%s&q=%s&cached=all" \
				# "&match=%s&moderated=%s%s&sort=relevance&type=video&offset=0&limit=200"
file_video_link = "file/get?api_key=%s&type=video"
file_tfile_link = "file/get?api_key=%s&t_files=1&id=%s"

session = requests.Session()
retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retries, pool_maxsize=100))


class Furk:
	def __init__(self):
		self.files = []
		self.api_key = control.setting('furk.api')
		self.highlight_color = control.setting('highlight.color')
		self.login_link = "login/login?login=%s&pwd=%s"

	def user_files(self):
		if not self.api_key: return
		try:
			url = base_link + file_video_link % self.api_key
			response = session.get(url, timeout=20).json()
			files = response['files']
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		for count, item in enumerate(files, 1):
			try:
				cached = True if 'url_dl' in item else False
				files_str = 'files'

				if cached:
					files_num_video = item['files_num_video']
					name = string_tools.strip_non_ascii_and_unprintable(item['name'])

					item_id = item['id'] if cached else item['info_hash']
					url_dl = item['url_dl'] if cached else item['info_hash']

					size = str(round(float(item['size']) / 1048576000, 1))
					label = '%02d | [B]%s GB[/B] | [B]%s %s[/B] |[I] %s [/I]' % (count, size, files_num_video, files_str, name)

					# url_dl = ''
					# for x in accepted_extensions:
						# if item['url_dl'].endswith(x): url_dl = item['url_dl']
						# else: continue
					# if url_dl == '': continue

					# if not int(item['files_num_video_player']) > 1:
						# if int(item['ss_num']) > 0: thumb = item['ss_urls'][0]
						# else: thumb = ''
						# self.addDirectoryItem(label , url_dl, thumb, '', isAction=False)
					self.addDirectoryItem(label , url_dl, furk_icon, '', isAction=False)
				else: pass
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		self.endDirectory()

	# def furk_tfile_video(params):
		# def _builder():
			# for count, item in enumerate(t_files, 1):
				# try:
					# cm = []
					# url_params = {'mode': 'media_play', 'url': item['url_dl'], 'media_type': 'video'}
					# url = build_url(url_params)
					# name = clean_file_name(item['name']).upper()
					# height = int(item['height'])
					# if 1200 < height > 2100: display_res = '4K'
					# elif 1000 < height < 1200: display_res = '1080P'
					# elif 680 < height < 1000: display_res = '720P'
					# else: display_res = 'SD'
					# display_name = '%02d | [B]%s[/B] | [B]%.2f GB[/B] | %smbps | [I]%s[/I]' % \
					# (count, display_res, float(item['size'])/1073741824, str(round(float(item['bitrate'])/1000, 2)), name)
					# listitem = make_listitem()
					# listitem.setLabel(display_name)
					# down_file_params = {'mode': 'downloader', 'name': item['name'], 'url': item['url_dl'], 'action': 'cloud.furk_direct', 'image': furk_icon}
					# cm.append((ls(32747),'RunPlugin(%s)' % build_url(down_file_params)))
					# listitem.addContextMenuItems(cm)
					# listitem.setArt({'icon': furk_icon, 'poster': furk_icon, 'thumb': furk_icon, 'fanart': fanart, 'banner': furk_icon})
					# yield (url, listitem, False)
				# except: pass
		# __handle__ = int(argv[1])
		# t_files = [i for i in Furk.t_files(params.get('item_id')) if 'video' in i['ct'] and 'bitrate' in i]
		# kodi_utils.add_items(__handle__, list(_builder()))
		# kodi_utils.set_content(__handle__, 'files')
		# kodi_utils.end_directory(__handle__)
		# kodi_utils.set_view_mode('view.premium')

	def search(self):
		from resources.lib.menus import navigator
		navigator.Navigator().addDirectoryItem(getLS(32603) % self.highlight_color, 'furk_SearchNew', 'search.png', 'DefaultAddonsSearch.png', isFolder=False)
		from sqlite3 import dbapi2 as database
		try:
			if not control.existsPath(control.dataPath): control.makeFile(control.dataPath)
			dbcon = database.connect(control.searchFile)
			dbcur = dbcon.cursor()
			dbcur.executescript('''CREATE TABLE IF NOT EXISTS furk (ID Integer PRIMARY KEY AUTOINCREMENT, term);''')
			dbcur.execute('''SELECT * FROM furk ORDER BY ID DESC''')
			dbcur.connection.commit()
			lst = []
			delete_option = False
			for (id, term) in sorted(dbcur.fetchall(), key=lambda k: re_sub(r'(^the |^a |^an )', '', k[1].lower()), reverse=False):
				if term not in str(lst):
					delete_option = True
					navigator.Navigator().addDirectoryItem(term, 'furk_searchResults&query=%s' % term, 'search.png', 'DefaultAddonsSearch.png', isSearch=True, table='furk')
					lst += [(term)]
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
		if delete_option:
			navigator.Navigator().addDirectoryItem(32605, 'cache_clearSearch', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		navigator.Navigator().endDirectory()

	def search_new(self):
		k = control.keyboard('', getLS(32010))
		k.doModal()
		query = k.getText() if k.isConfirmed() else None
		if not query: return control.closeAll()
		from sqlite3 import dbapi2 as database
		try:
			dbcon = database.connect(control.searchFile)
			dbcur = dbcon.cursor()
			dbcur.execute('''INSERT INTO furk VALUES (?,?)''', (None, query))
			dbcur.connection.commit()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
		control.closeAll()
		control.execute('ActivateWindow(Videos,plugin://plugin.video.umbrella/?action=furk_searchResults&query=%s,return)' % quote_plus(query))

	def query_results_to_dialog(self, query):
		if not self.api_key: return
		try:
			downloadMenu = getLS(40048)
			query = '@name+%s' % query
			url = (base_link + search_link % (self.api_key, query, 'extended', 'no', '')).replace(' ', '+')
			response = session.get(url, timeout=20).json()
			if 'files' not in response: # with reuselanguageinvoker on an empty directory must be loaded, do not use sys.exit()
				control.hide() ; control.notification(title='Furk', message=33049, icon=furk_icon)
			try:
				files = response['files']
				files.sort(key=lambda k: k['name'])
			except: files = []
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		for count, item in enumerate(files, 1):
			try:
				if item['is_ready'] == '1' and item['type'] == 'video':
					cm = []
					name = string_tools.strip_non_ascii_and_unprintable(item['name'])
					file_id = item['id']
					url_dl = item['url_dl']
					if url_dl == '': continue
					size = str(round(float(int(item['size'])) / 1048576000, 1))
					label = '%02d | [B]%s GB[/B] | [I]%s [/I]' % (count, size, name)
					url = 'furk_resolve_forPlayback&url=%s' % file_id
					cm.append((downloadMenu, 'RunPlugin(plugin://plugin.video.umbrella/?action=download&name=%s&image=%s&url=%s&caller=furk)' %
										(quote_plus(name), quote_plus(furk_icon), file_id)))
					self.addDirectoryItem(label, url, furk_icon, '', cm)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		self.endDirectory()

	def addDirectoryItem(self, name, query, thumb, icon, context=None, isAction=True):
		from sys import argv
		try:
			if isinstance(name, int): name = getLS(name)
			url = 'plugin://plugin.video.umbrella/?action=%s' % query if isAction else query
			item = control.item(label=name, offscreen=True)
			if context: item.addContextMenuItems(context)
			item.setArt({'icon': thumb, 'poster': thumb, 'thumb': thumb, 'fanart': addonFanart, 'banner': thumb})
			#item.setInfo(type='video', infoLabels={'plot': name})
			meta = {'plot': name}
			control.set_info(item, meta)
			control.addItem(handle=int(argv[1]), url=url, listitem=item, isFolder=False)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def endDirectory(self):
		from sys import argv
		try:
			syshandle = int(argv[1])
			control.content(syshandle, 'files')
			control.directory(syshandle, cacheToDisc=True)
			control.sleep(200)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def resolve_forPlayback(self, file_id):
		if not self.api_key: return
		control.busy()
		from json import loads as jsloads
		url = ''
		try:
			link = (base_link + file_tfile_link % (self.api_key, file_id))
			p = session.get(link)
			p = jsloads(p.text)
			if p['status'] != 'ok' or p['found_files'] != '1': return control.hide()

			files = p['files'][0]
			files = files['t_files']

			for i in files:
				if 'video' not in i['ct']: pass
				else: self.files.append(i)
			for i in self.files:
				if 'is_largest' in i: url = i['url_dl']

			control.hide()
			if not url: return control.notification(title='Furk', message=32401, icon=furk_icon)
			from resources.lib.modules import player
			return player.Player().play(url)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def account_info_to_dialog(self):
		from datetime import datetime
		try:
			username = control.setting('furk.user_name')
			api_key = control.setting('furk.api')
			items = []
			items += ['Username: ' % username]
			return control.selectDialog(items, 'Furk')
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
	def account_info_to_dialog(self):
		from datetime import datetime
		import time
		from resources.lib.windows.textviewer import TextViewerXML
		try:
			control.busy()
			username = control.setting('furk.user_name')
			api_key = control.setting('furk.api')
			body = []
			append = body.append
			append(getLS(40129) % username)  # Username
			append(getLS(40130) % api_key)  # Plan
			control.hide()
			windows = TextViewerXML('textviewer.xml', control.addonPath(control.addonId()), heading='[B]Furk[/B]', text='\n\n'.join(body))
			windows.run()
			del windows
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			control.hide()

	def get_api(self):
		try:
			username = control.setting('furk.user_name')
			userpass = control.setting('furk.user_pass')
			api_key = control.setting('furk.api')
			if api_key == '':
				if username == '' or userpass == '': return
				link = (base_link + self.login_link % (username, userpass))
				p = requests.post(link, timeout=20).json()
				if p['status'] == 'ok':
					api_key = p['api_key']
					control.setSetting('furk.api', api_key)
					furkmessage = control.notification(message='Furk API Key Saved.')
				else: 
					furkmessage = control.notification(message='Issue saving Furk key. Please check username and password.')
			return furkmessage
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return control.notification(message='Issue Saving Furk API Key. Please check username and password.')

	def clear_api(self):
		try:
			control.setSetting('furk.api', '')
			furkmessage = control.notification(message='Furk Key Cleared')
			return furkmessage
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return control.notification(message='Issue Clearing Furk API Key. Please check username and password.')