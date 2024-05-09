# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from json import dumps as jsdumps, loads as jsloads
import os.path
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
#import xml.etree.ElementTree as ET
from threading import Thread
from xml.dom.minidom import parse as mdParse
from urllib.parse import unquote, unquote_plus
from re import sub as re_sub

# Kodi JSON-RPC API endpoint
api_url = 'http://localhost:8080/jsonrpc'
addon = xbmcaddon.Addon
AddonID = xbmcaddon.Addon().getAddonInfo('id')
addonInfo = xbmcaddon.Addon().getAddonInfo
addonName = addonInfo('name')
addonVersion = addonInfo('version')
getLangString = xbmcaddon.Addon().getLocalizedString


dialog = xbmcgui.Dialog()
numeric_input = xbmcgui.INPUT_NUMERIC
alpha_input = xbmcgui.INPUT_ALPHANUM
getCurrentDialogId = xbmcgui.getCurrentWindowDialogId()
getCurrentWindowId = xbmcgui.getCurrentWindowId()
homeWindow = xbmcgui.Window(10000)
playerWindow = xbmcgui.Window(12005)
infoWindow = xbmcgui.Window(12003)
item = xbmcgui.ListItem
progressDialog = xbmcgui.DialogProgress()
progressDialogBG = xbmcgui.DialogProgressBG()
progress_line = '%s[CR]%s'
progress_line2 = '%s[CR]%s[CR]%s'

addItem = xbmcplugin.addDirectoryItem
content = xbmcplugin.setContent
directory = xbmcplugin.endOfDirectory
property = xbmcplugin.setProperty
resolve = xbmcplugin.setResolvedUrl
sortMethod = xbmcplugin.addSortMethod

condVisibility = xbmc.getCondVisibility
execute = xbmc.executebuiltin
infoLabel = xbmc.getInfoLabel
jsonrpc = xbmc.executeJSONRPC
keyboard = xbmc.Keyboard
log = xbmc.log
monitor_class = xbmc.Monitor
monitor = monitor_class()
player = xbmc.Player()
player2 = xbmc.Player
playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
playlistM = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
skin = xbmc.getSkinDir()

deleteDir = xbmcvfs.rmdir
deleteFile = xbmcvfs.delete
existsPath = xbmcvfs.exists
legalFilename = xbmcvfs.makeLegalFilename
listDir = xbmcvfs.listdir
makeFile = xbmcvfs.mkdir
makeDirs = xbmcvfs.mkdirs
openFile = xbmcvfs.File
transPath = xbmcvfs.translatePath

joinPath = os.path.join
isfilePath = os.path.isfile
absPath = os.path.abspath

SETTINGS_PATH = transPath(joinPath(addonInfo('path'), 'resources', 'settings.xml'))
try: dataPath = transPath(addonInfo('profile')).decode('utf-8')
except: dataPath = transPath(addonInfo('profile'))
settingsFile = joinPath(dataPath, 'settings.xml')
viewsFile = joinPath(dataPath, 'views.db')
bookmarksFile = joinPath(dataPath, 'bookmarks.db')
providercacheFile = joinPath(dataPath, 'providers.db')
metacacheFile = joinPath(dataPath, 'metadata.db')
searchFile = joinPath(dataPath, 'search.db')
libcacheFile = joinPath(dataPath, 'library.db')
libCacheSimilar = joinPath(dataPath, 'librarymoviescache.db')
cacheFile = joinPath(dataPath, 'cache.db')
traktSyncFile = joinPath(dataPath, 'traktSync.db')
subsFile = joinPath(dataPath, 'substitute.db')
fanarttvCacheFile = joinPath(dataPath, 'fanarttv.db')
metaInternalCacheFile = joinPath(dataPath, 'video_cache.db')
favouritesFile = joinPath(dataPath, 'favourites.db')
plexSharesFile = joinPath(dataPath, 'plexshares.db')
trailer = 'plugin://plugin.video.youtube/play/?video_id=%s'
subtitlesPath = joinPath(dataPath, 'subtitles')

def getKodiVersion(full=False):
	if full: return xbmc.getInfoLabel("System.BuildVersion")
	else: return int(xbmc.getInfoLabel("System.BuildVersion")[:2])

def setContainerName(value):
	try:
		if value:
			value = unquote_plus(value)
		else:
			value = ''
		import sys
		xbmcplugin.setPluginCategory(int(sys.argv[1]), value)
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def setHomeWindowProperty(propertyname, property):
	win = xbmcgui.Window(10000)
	win.setProperty(str(propertyname), property)
####################################################
# --- Custom Dialogs
####################################################
def getProgressWindow(heading='', icon=None, qr=0, artwork=0):
	if icon == None:
		icon = addonIcon()
	from resources.lib.windows.umbrella_dialogs import ProgressUmbrella
	window = ProgressUmbrella('progress_umbrella.xml', addonPath(addonId()), heading=heading, icon=icon, qr=qr, artwork=artwork)
	Thread(target=window.run).start()
	return window

def setting(id, fallback=None):
	try: settings_dict = jsloads(homeWindow.getProperty('umbrella_settings'))
	except: settings_dict = make_settings_dict()
	if settings_dict is None: settings_dict = settings_fallback(id)
	value = settings_dict.get(id, '')
	if fallback is None: return value
	if value == '': return fallback
	return value

def settings_fallback(id):
	return {id: xbmcaddon.Addon().getSetting(id)}

def setSetting(id, value):
	xbmcaddon.Addon().setSetting(id, value)

def make_settings_dict(): # service runs upon a setting change
	try:
		#root = ET.parse(settingsFile).getroot()
		root = mdParse(settingsFile) #minidom instead of element tree
		curSettings = root.getElementsByTagName("setting") #minidom instead of element tree
		settings_dict = {}
		for item in curSettings:
			dict_item = {}
			#setting_id = item.get('id')
			setting_id = item.getAttribute('id') #minidom instead of element tree
			try:
				setting_value = item.firstChild.data #minidom instead of element tree
			except:
				setting_value = None
			if setting_value is None: setting_value = ''
			dict_item = {setting_id: setting_value}
			settings_dict.update(dict_item)
		homeWindow.setProperty('umbrella_settings', jsdumps(settings_dict))
		refresh_playAction()
		refresh_libPath()
		return settings_dict
	except: return None

def openSettings(query=None, id=addonInfo('id')):
	try:
		hide()
		execute('Addon.OpenSettings(%s)' % id)
		if not query: return
		c, f = query.split('.')
		execute('SetFocus(%i)' % (int(c) - 100))
		execute('SetFocus(%i)' % (int(f) - 80))
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def lang(language_id):
	return str(getLangString(language_id))

def sleep(time):  # Modified `sleep`(in milli secs) that honors a user exit request
	while time > 0 and not monitor.abortRequested():
		xbmc.sleep(min(100, time))
		time = time - 100

def getCurrentViewId():
	win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
	return str(win.getFocusId())

def getUmbrellaVersion():
	return xbmcaddon.Addon('plugin.video.umbrella').getAddonInfo('version')

def addonVersion(addon):
	return xbmcaddon.Addon(addon).getAddonInfo('version')

def addonId():
	return addonInfo('id')

def addonName():
	return addonInfo('name')

def addonPath(addon):
	try: addonID = xbmcaddon.Addon(addon)
	except: addonID = None
	if addonID is None: return ''
	else:
		try: return transPath(addonID.getAddonInfo('path').decode('utf-8'))
		except: return transPath(addonID.getAddonInfo('path'))

def addonInstalled(addon_id):
	return condVisibility('System.HasAddon(%s)' % addon_id)

def artPath():
	theme = appearance()
	return joinPath(xbmcaddon.Addon('plugin.video.umbrella').getAddonInfo('path'), 'resources', 'artwork', theme)

def genreIconPath():
	theme = appearance()
	return joinPath(xbmcaddon.Addon('plugin.video.umbrella').getAddonInfo('path'), 'resources', 'artwork', theme, 'genre_media', 'icons')

def genrePosterPath():
	theme = appearance()
	return joinPath(xbmcaddon.Addon('plugin.video.umbrella').getAddonInfo('path'), 'resources', 'artwork', theme, 'genre_media', 'posters')

def appearance():
	theme = setting('skinpackicons').lower()
	return theme

def iconFolders():
	return joinPath(xbmcaddon.Addon('plugin.video.umbrella').getAddonInfo('path'), 'resources', 'artwork')

def addonIcon():
	theme = appearance()
	art = artPath()
	if not (art is None and theme in ('-', '')): return joinPath(art, 'icon.png')
	return addonInfo('icon')

def addonThumb():
	theme = appearance()
	art = artPath()
	if not (art is None and theme in ('-', '')): return joinPath(art, 'poster.png')
	elif theme == '-': return 'DefaultFolder.png'
	return addonInfo('icon')

def addonPoster():
	theme = appearance()
	art = artPath()
	if not (art is None and theme in ('-', '')): return joinPath(art, 'poster.png')
	return 'DefaultVideo.png'

def addonFanart():
	theme = appearance()
	art = artPath()
	if not (art is None and theme in ('-', '')): return joinPath(art, 'fanart.jpg')
	return addonInfo('fanart')

def addonBanner():
	theme = appearance()
	art = artPath()
	if not (art is None and theme in ('-', '')): return joinPath(art, 'banner.png')
	return 'DefaultVideo.png'

def addonNext():
	theme = appearance()
	art = artPath()
	if not (art is None and theme in ('-', '')): return joinPath(art, 'next.png')
	return 'DefaultVideo.png'

def skin_location():
	return transPath('special://home/addons/plugin.video.umbrella')

####################################################
# --- Dialogs
####################################################
def notification(title=None, message=None, icon=None, time=3000, sound=(setting('notification.sound') == 'true')):
	if title == 'default' or title is None: title = addonName()
	if isinstance(title, int): heading = lang(title)
	else: heading = str(title)
	if isinstance(message, int): body = lang(message)
	else: body = str(message)
	if not icon or icon == 'default': icon = addonIcon()
	elif icon == 'INFO': icon = xbmcgui.NOTIFICATION_INFO
	elif icon == 'WARNING': icon = xbmcgui.NOTIFICATION_WARNING
	elif icon == 'ERROR': icon = xbmcgui.NOTIFICATION_ERROR
	return dialog.notification(heading, body, icon, time, sound)

def yesnoDialog(line1, line2, line3, heading=addonInfo('name'), nolabel='', yeslabel='', icon=None):
	message = '%s[CR]%s[CR]%s' % (line1, line2, line3)
	if setting('dialogs.useumbrelladialog') == 'true':
		from resources.lib.windows.umbrella_dialogs import Confirm
		if yeslabel == '':
			myyes = lang(32179)
		else:
			myyes = yeslabel
		if nolabel == '':
			myno = lang(32180)
		else:
			myno = nolabel
		window = Confirm('confirm.xml', addonPath(addonId()), heading=heading, text=message, ok_label=myyes, cancel_label=myno, default_control=11, icon=icon)
		confirmWin = window.run()
		del window
		return confirmWin
	else:
		return dialog.yesno(heading, message, nolabel, yeslabel)

def yesnocustomDialog(line1, line2, line3, heading=addonInfo('name'), customlabel='', nolabel='', yeslabel=''):
	message = '%s[CR]%s[CR]%s' % (line1, line2, line3)
	return dialog.yesnocustom(heading, message, customlabel, nolabel, yeslabel)

def selectDialog(list, heading=addonInfo('name')):
	return dialog.select(heading, list)

def okDialog(title=None, message=None, icon=None):
	if title == 'default' or title is None: title = addonName()
	if isinstance(title, int): heading = lang(title)
	else: heading = str(title)
	if isinstance(message, int): body = lang(message)
	else: body = str(message)
	if setting('dialogs.useumbrelladialog') == 'true':
		if icon == None:
			icon = addonIcon()
		from resources.lib.windows.umbrella_dialogs import OK
		window = OK('ok.xml', addonPath(addonId()), heading=heading, text=body, ok_label=lang(32179), icon=icon)
		okayWin = window.run()
		del window
		return okayWin
	else:
		return dialog.ok(heading, body)

def context(items=None, labels=None):
	if items:
		labels = [i[0] for i in items]
		choice = dialog.contextmenu(labels)
		if choice >= 0: return items[choice][1]()
		else: return False
	else: return dialog.contextmenu(labels)

def multiSelect(title=None, items=None, preselect=None):
    if items:
        labels = [i for i in items]
        if preselect == None:
            return dialog.multiselect(title, labels)
        else:
            return dialog.multiselect(title, labels, preselect=preselect)
    else: return

####################################################
# --- Built-in
####################################################
def busy():
	return execute('ActivateWindow(busydialognocancel)')

def hide():
	execute('Dialog.Close(busydialog)')
	execute('Dialog.Close(busydialognocancel)')

def closeAll():
	return execute('Dialog.Close(all,true)')

def closeOk():
	return execute('Dialog.Close(okdialog,true)')

def refresh():
	return execute('Container.Refresh')

def folderPath():
    return infoLabel('Container.FolderPath')

def queueItem():
	return execute('Action(Queue)') # seems broken in 19 for show and season level, works fine in 18

def refreshRepos():
	return execute('UpdateAddonRepos')
########################

def cancelPlayback():
	from sys import argv
	playlist.clear()
	resolve(int(argv[1]), False, item(offscreen=True))
	closeOk()

def apiLanguage(ret_name=None):
	langDict = {'Arabic Saudi Arabia': 'ar-SA', 'Bulgarian': 'bg', 'Chinese': 'zh', 'Croatian': 'hr', 'Czech': 'cs', 'Danish': 'da', 'Dutch': 'nl', 'English': 'en', 'Finnish': 'fi',
					'French': 'fr', 'German': 'de', 'Greek': 'el', 'Hebrew': 'he', 'Hungarian': 'hu', 'Italian': 'it', 'Japanese': 'ja', 'Korean': 'ko',
					'Norwegian': 'no', 'Polish': 'pl', 'Portuguese': 'pt', 'Romanian': 'ro', 'Russian': 'ru', 'Serbian': 'sr', 'Slovak': 'sk',
					'Slovenian': 'sl', 'Spanish': 'es', 'Swedish': 'sv', 'Thai': 'th', 'Turkish': 'tr', 'Ukrainian': 'uk'}
	trakt = ('bg', 'cs', 'da', 'de', 'el', 'en', 'es', 'fi', 'fr', 'he', 'hr', 'hu', 'it', 'ja', 'ko', 'nl', 'no', 'pl', 'pt', 'ro', 'ru', 'sk', 'sl', 'sr', 'sv', 'th', 'tr', 'uk', 'zh')
	tvdb = ('en', 'sv', 'no', 'da', 'fi', 'nl', 'de', 'it', 'es', 'fr', 'pl', 'hu', 'el', 'tr', 'ru', 'he', 'ja', 'pt', 'zh', 'cs', 'sl', 'hr', 'ko')
	youtube = ('gv', 'gu', 'gd', 'ga', 'gn', 'gl', 'ty', 'tw', 'tt', 'tr', 'ts', 'tn', 'to', 'tl', 'tk', 'th', 'ti', 'tg', 'te', 'ta', 'de', 'da', 'dz', 'dv', 'qu', 'zh', 'za', 'zu',
					'wa', 'wo', 'jv', 'ja', 'ch', 'co', 'ca', 'ce', 'cy', 'cs', 'cr', 'cv', 'cu', 'ps', 'pt', 'pa', 'pi', 'pl', 'mg', 'ml', 'mn', 'mi', 'mh', 'mk', 'mt', 'ms',
					'mr', 'my', 've', 'vi', 'is', 'iu', 'it', 'vo', 'ii', 'ik', 'io', 'ia', 'ie', 'id', 'ig', 'fr', 'fy', 'fa', 'ff', 'fi', 'fj', 'fo', 'ss', 'sr', 'sq', 'sw', 'sv', 'su', 'st', 'sk',
					'si', 'so', 'sn', 'sm', 'sl', 'sc', 'sa', 'sg', 'se', 'sd', 'lg', 'lb', 'la', 'ln', 'lo', 'li', 'lv', 'lt', 'lu', 'yi', 'yo', 'el', 'eo', 'en', 'ee', 'eu', 'et', 'es', 'ru',
					'rw', 'rm', 'rn', 'ro', 'be', 'bg', 'ba', 'bm', 'bn', 'bo', 'bh', 'bi', 'br', 'bs', 'om', 'oj', 'oc', 'os', 'or', 'xh', 'hz', 'hy', 'hr', 'ht', 'hu', 'hi', 'ho',
					'ha', 'he', 'uz', 'ur', 'uk', 'ug', 'aa', 'ab', 'ae', 'af', 'ak', 'am', 'an', 'as', 'ar', 'av', 'ay', 'az', 'nl', 'nn', 'no', 'na', 'nb', 'nd', 'ne', 'ng',
					'ny', 'nr', 'nv', 'ka', 'kg', 'kk', 'kj', 'ki', 'ko', 'kn', 'km', 'kl', 'ks', 'kr', 'kw', 'kv', 'ku', 'ky')
	tmdb = ('ar-SA','bg', 'cs', 'da', 'de', 'el', 'en', 'es', 'fi', 'fr', 'he', 'hr', 'hu', 'it', 'ja', 'ko', 'nl', 'no', 'pl', 'pt', 'ro', 'ru', 'sk', 'sl', 'sr', 'sv', 'th', 'tr', 'uk', 'zh')
	name = None
	name = setting('api.language')
	if not name: name = 'AUTO'
	if name[-1].isupper():
		try: name = xbmc.getLanguage(xbmc.ENGLISH_NAME).split(' ')[0]
		except: pass
	try: name = langDict[name]
	except: name = 'en'
	lang = {'trakt': name} if name in trakt else {'trakt': 'en'}
	lang['tvdb'] = name if name in tvdb else 'en'
	lang['youtube'] = name if name in youtube else 'en'
	lang['tmdb'] = name if name in tmdb else 'en'
	if ret_name:
		lang['trakt'] = [i[0] for i in iter(langDict.items()) if i[1] == lang['trakt']][0]
		lang['tvdb'] = [i[0] for i in iter(langDict.items()) if i[1] == lang['tvdb']][0]
		lang['youtube'] = [i[0] for i in iter(langDict.items()) if i[1] == lang['youtube']][0]
		lang['tmdb'] = [i[0] for i in iter(langDict.items()) if i[1] == lang['tmdb']][0]
	return lang

def mpaCountry():
# Countries with Content Rating System
	countryDict = {'Australia': 'AU', 'Austria': 'AT', 'Brazil': 'BR', 'Bulgaria': 'BG', 'Canada': 'CA', 'China': 'CN', 'Denmark': 'DK', 'Estonia': 'EE',
						'Finland': 'FI', 'France': 'FR', 'Germany': 'DE', 'Greece': 'GR', 'Hungary': 'HU', 'Hong Kong SAR China': 'HK', 'India': 'IN',
						'Indonesia': 'ID', 'Ireland': 'IE', 'Italy': 'IT', 'Japan': 'JP', 'Kazakhstan': 'KZ', 'Latvia': 'LV', 'Lithuania': 'LT', 'Malaysia': 'MY',
						'Mexico': 'MX', 'Netherlands': 'NL', 'New Zealand': 'NZ', 'Norway': 'NO', 'Philippines': 'PH', 'Poland': 'PL', 'Portugal': 'PT',
						'Romania': 'RO', 'Russia': 'RU', 'Saudi Arabia': 'SA', 'Singapore': 'SG', 'Slovakia': 'SK', 'South Africa': 'ZA', 'South Korea': 'KR',
						'Spain': 'ES', 'Sweden': 'SE', 'Switzerland': 'CH', 'Taiwan': 'TW', 'Thailand': 'TH', 'Turkey': 'TR', 'Ukraine': 'UA',
						'United Arab Emirates': 'AE', 'United Kingdom': 'GB', 'United States': 'US', 'Vietnam': 'VN'}
	return countryDict[setting('mpa.country')]

def autoTraktSubscription(tvshowtitle, year, imdb, tvdb): #---start adding TMDb to params
	from resources.lib.modules import library
	library.libtvshows().add(tvshowtitle, year, imdb, tvdb)


def getProviderHighlightColor(sourcename):
    #Real-Debrid
    #Premiumize.me
	sourcename = str(sourcename).lower()
	source = 'sources.'+sourcename+'.color'
	colorString = setting(source)
	return colorString

def getColorPicker(params):
	#will need to open a window here.
	from resources.lib.windows.colorpick import ColorPick
	window = ColorPick('colorpick.xml', addonPath(addonId()), current_setting=params.get('current_setting'), current_value=params.get('current_value'))
	colorPick = window.run()
	del window
	return colorPick

def showColorPicker(current_setting):
	current_value = setting(current_setting)
	chosen_color = getColorPicker({'current_setting': current_setting, 'current_value': current_value})
	if chosen_color:
		homeWindow.setProperty('umbrella.updateSettings', 'false')
		setSetting(current_setting+'.display', str('[COLOR=%s]%s[/COLOR]' % (chosen_color, chosen_color)))
		homeWindow.setProperty('umbrella.updateSettings', 'true')
		setSetting(current_setting, str('%s' % (chosen_color)))

def getMenuEnabled(menu_title):
	is_enabled = setting(menu_title).strip()
	if (is_enabled == '' or is_enabled == 'false'): return False
	return True

def trigger_widget_refresh():
	# import time
	# timestr = time.strftime("%Y%m%d%H%M%S", time.gmtime())
	# homeWindow.setProperty("widgetreload", timestr)
	# homeWindow.setProperty('widgetreload-episodes', timestr)
	# homeWindow.setProperty('widgetreload-movies', timestr)
	execute('UpdateLibrary(video,/fake/path/to/force/refresh/on/home)') # make sure this is ok coupled with above

def refresh_playAction(): # for umbrella global CM play actions
	autoPlayTV = 'true' if setting('play.mode.tv') == '1' else '0'
	homeWindow.setProperty('umbrella.autoPlaytv.enabled', autoPlayTV)
	autoPlayMovie = 'true' if setting('play.mode.movie') == '1' else '0'
	homeWindow.setProperty('umbrella.autoPlayMovie.enabled', autoPlayMovie)

def refresh_libPath(): # for umbrella global CM library actions
	homeWindow.setProperty('umbrella.movieLib.path', transPath(setting('library.movie')))
	homeWindow.setProperty('umbrella.tvLib.path', transPath(setting('library.tv')))

def refresh_debugReversed(): # called from service "onSettingsChanged" to clear umbrella.log if setting to reverse has been changed
	if homeWindow.getProperty('umbrella.debug.reversed') != setting('debug.reversed'):
		homeWindow.setProperty('umbrella.debug.reversed', setting('debug.reversed'))
		execute('RunPlugin(plugin://plugin.video.umbrella/?action=tools_clearLogFile)')

def metadataClean(metadata):
	if not metadata: return metadata
	allowed = ('genre', 'country', 'year', 'episode', 'season', 'sortepisode', 'sortseason', 'episodeguide', 'showlink',
					'top250', 'setid', 'tracknumber', 'rating', 'userrating', 'watched', 'playcount', 'overlay', 'cast', 'castandrole',
					'director', 'mpaa', 'plot', 'plotoutline', 'title', 'originaltitle', 'sorttitle', 'duration', 'studio', 'tagline', 'writer',
					'tvshowtitle', 'premiered', 'status', 'set', 'setoverview', 'tag', 'imdbnumber', 'code', 'aired', 'credits', 'lastplayed',
					'album', 'artist', 'votes', 'path', 'trailer', 'dateadded', 'mediatype', 'dbid')
	return {k: v for k, v in iter(metadata.items()) if k in allowed}

def set_info(item, meta, setUniqueIDs=None, resumetime='', fileNameandPath=None):
	if getKodiVersion() >= 20:
		try:
			meta_get = meta.get
			info_tag = item.getVideoInfoTag()
			info_tag.setMediaType(meta_get('mediatype'))
			if setUniqueIDs:
				info_tag.setUniqueIDs(setUniqueIDs)
			#log('unique id title:%s imdb:%s filenameandpath: %s'%(meta_get('title'), setUniqueIDs.get('imdb'), fileNameandPath), 1)
			if fileNameandPath:
				info_tag.setPath(unquote(fileNameandPath))
			if fileNameandPath:
				info_tag.setFilenameAndPath(unquote(fileNameandPath))
			if meta_get('title') == None:
				info_title = item.getLabel()
			else:
				info_title = meta_get('title')
			info_tag.setTitle(info_title)
			info_tag.setSortTitle(meta_get('sorttitle'))
			#info_tag.setSortEpisode(meta_get('sortepisode'))
			#info_tag.setSortSeason(meta_get('sortseason'))
			info_tag.setOriginalTitle(meta_get('originaltitle'))
			info_tag.setPlot(meta_get('plot'))
			info_tag.setPlotOutline(meta_get('plot'))
			info_tag.setDateAdded(meta_get('dateadded'))
			info_tag.setPremiered(meta_get('premiered'))
			info_tag.setYear(convert_type(int, meta_get('year', 0)))
			info_tag.setRating(convert_type(float, meta_get('rating', 0.0)))
			info_tag.setMpaa(meta_get('mpaa'))
			if meta_get('duration') != '':
				info_tag.setDuration(meta_get('duration', 0))
			info_tag.setPlaycount(convert_type(int, meta_get('playcount', 0)))
			if isinstance(meta_get('votes'), str): 
				meta_votes = str(meta_get('votes')).replace(",","")
			else:
				meta_votes = meta_get('votes')
			if meta_votes:
				info_tag.setVotes(convert_type(int, meta_votes))
			info_tag.setLastPlayed(meta_get('lastplayed'))
			info_tag.setAlbum(meta_get('album'))
			info_tag.setGenres(to_list(meta_get('genre', [])))
			info_tag.setCountries(to_list(meta_get('country', [])))
			info_tag.setTags(meta_get('tag', []))
			info_tag.setTrailer(meta_get('trailer'))
			info_tag.setTagLine(meta_get('tagline'))
			info_tag.setStudios(to_list(meta_get('studio', [])))
			info_tag.setWriters(to_list(meta_get('writer', [])))
			info_tag.setDirectors(to_list(meta_get('director', [])))
			if setUniqueIDs:
				info_tag.setIMDBNumber(setUniqueIDs.get('imdb'))
			if resumetime: info_tag.setResumePoint(float(resumetime))
			if meta_get('mediatype') in ['tvshow', 'season']:
				info_tag.setTvShowTitle(meta_get('tvshowtitle'))
				info_tag.setTvShowStatus(meta_get('status'))
			if meta_get('mediatype') in ['episodes', 'episode']:
				info_tag.setTvShowTitle(meta_get('tvshowtitle'))
				info_tag.setEpisode(convert_type(int, meta_get('episode')))
				info_tag.setSeason(convert_type(int, meta_get('season')))
			info_tag.setCast([xbmc.Actor(name=item['name'], role=item['role'], thumbnail=item['thumbnail']) for item in meta_get('castandart', [])])
			#info_tag.setCast([xbmc_actor(name=item['name'], role=item['role'], thumbnail=item['thumbnail']) for item in meta_get('castandart', [])])
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
	else:
		if setUniqueIDs:
			item.setUniqueIDs(setUniqueIDs)
		item.setCast(meta.get('castandart', []) + meta.get('guest_stars', []))
		meta = metadataClean(meta)
		try: meta.pop('cast')
		except: pass
		item.setInfo('video', meta)
		if resumetime:
			item.setProperties({'ResumeTime': resumetime, 'TotalTime': str(meta.get('duration', 2700))})
	return item

def convert_type(_type, _value):
	try:
		return _type(_value)
	except Exception as Err:
		from resources.lib.modules import log_utils
		log_utils.log("conversion error: %s"% Err, 1)

def to_list(item_str):
	if not isinstance(item_str, list): 
		item_str = [item_str]
	return item_str

def darkColor(color):
	try:
		compareColor = color[2:]
		import math
		rgbColor = tuple(int(compareColor[i:i+2], 16)  for i in (0, 2, 4))
		[r,g,b]=rgbColor
		hsp = math.sqrt(0.299 * (r * r) + 0.587 * (g * g) + 0.114 * (b * b))
		if (hsp>127.5):
			return 'light'
		else:
			return 'dark'
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return 'dark'

def reload_addon():
    disable_enable_addon()
    update_local_addon()

def disable_enable_addon():
    #attempting to fix Crashy Crasherson
    jsonrpc('{"jsonrpc": "2.0", "id":1, "method": "Addons.SetAddonEnabled", "params": {"addonid": "plugin.video.umbrella", "enabled": false }}')
    xbmc.log('[ plugin.video.umbrella ] umbrella disabled', 1)
    jsonrpc('{"jsonrpc": "2.0", "id":1, "method": "Addons.SetAddonEnabled", "params": {"addonid": "plugin.video.umbrella", "enabled": true }}')
    xbmc.log('[ plugin.video.umbrella ] umbrella re-enabled', 1)

def addonEnabled(addon_id):
	return condVisibility('System.AddonIsEnabled(%s)' % addon_id)

def update_local_addon():
    execute('UpdateLocalAddons')

def jsonrpc_get_addons():
	try:
		results = jsonrpc('{"jsonrpc": "2.0", "id":1, "method": "Addons.GetAddons", "params": {"type": "xbmc.python.module", "properties": ["thumbnail", "name"] }}')
		results = jsloads(results)['result']['addons']
	except:
		results = []
	return results
    
def jsondate_to_datetime(jsondate_object, resformat, remove_time=False):
	import _strptime  # fix bug in python import
	from datetime import datetime
	import time
	if remove_time:
		try: datetime_object = datetime.strptime(jsondate_object, resformat).date()
		except TypeError: datetime_object = datetime(*(time.strptime(jsondate_object, resformat)[0:6])).date()
	else:
		try: datetime_object = datetime.strptime(jsondate_object, resformat)
		except TypeError: datetime_object = datetime(*(time.strptime(jsondate_object, resformat)[0:6]))
	return datetime_object

def syncAccounts():
	try:
		if setting('umbrella.colorSecond') == 'false':
			homeWindow.setProperty('umbrella.updateSettings', 'false')
			setSetting('highlight.color', 'FFFFFF33')
			setSetting('highlight.color.display', '[COLOR=FFFFFF33]FFFFFF33[/COLOR]')
			setSetting('movie.unaired.identify', 'FF5CFF34')
			setSetting('movie.unaired.identify.display', '[COLOR=FF5CFF34]FF5CFF34[/COLOR]')
			setSetting('dialogs.customcolor', 'FF00B8E6')
			setSetting('dialogs.customcolor.display', '[COLOR=FF00B8E6]FF00B8E6[/COLOR]')
			setSetting('dialogs.titlebar.color', 'FF00B8E6')
			setSetting('dialogs.titlebar.color.display', '[COLOR=FF00B8E6]FF00B8E6[/COLOR]')
			setSetting('dialogs.button.color', 'FF00B8E6')
			setSetting('dialogs.button.color.display', '[COLOR=FF00B8E6]FF00B8E6[/COLOR]')
			setSetting('unaired.identify', 'FF34FF33')
			setSetting('unaired.identify.display', '[COLOR=FF34FF33]FF34FF33[/COLOR]')
			setSetting('playnext.background.color', 'FF000000')
			setSetting('playnext.background.color.display', '[COLOR=FF000000]FF000000[/COLOR]')
			setSetting('scraper.dialog.color', 'FFFFFF33')
			setSetting('scraper.dialog.color.display', '[COLOR=FFFFFF33]FFFFFF33[/COLOR]')
			setSetting('sources.highlight.color', 'FF4DFFFF')
			setSetting('sources.highlight.color.display', '[COLOR=FF4DFFFF]FF4DFFFF[/COLOR]')
			setSetting('sources.real-debrid.color', 'FFFF3334')
			setSetting('sources.real-debrid.color.display', '[COLOR=FFFF3334]FFFF3334[/COLOR]')
			setSetting('sources.alldebrid.color', 'FFFFB84E')
			setSetting('sources.alldebrid.color.display', '[COLOR=FFFFB84E]FFFFB84E[/COLOR]')
			setSetting('sources.premiumize.me.color', 'FF4700B4')
			setSetting('sources.premiumize.me.color.display', '[COLOR=FF4700B4]FF4700B4[/COLOR]')
			setSetting('sources.easynews.color', 'FF24B301')
			setSetting('sources.easynews.color.display', '[COLOR=FF24B301]FF24B301[/COLOR]')
			setSetting('sources.plexshare.color', 'FFAD34FF')
			setSetting('sources.plexshare.color.display', '[COLOR=FFAD34FF]FFAD34FF[/COLOR]')
			setSetting('sources.gdrive.color', 'FFFF4DFF')
			setSetting('sources.gdrive.color.display', '[COLOR=FFFF4DFF]FFFF4DFF[/COLOR]')
			setSetting('sources.filepursuit.color', 'FF00CC29')
			setSetting('sources.filepursuit.color.display', '[COLOR=FF00CC29]FF00CC29[/COLOR]')
			homeWindow.setProperty('umbrella.updateSettings', 'true')
			setSetting('umbrella.colorSecond', 'true')
			notification('Umbrella', 'Reloading addon due to new settings added.')
		if setting('umbrella.externalWarning') != 'true':
			setSetting('umbrella.externalWarning', 'true')
			from resources.help import help
			help.get('externalProviders')
		if setting('context.useUmbrellaContext') == 'true':
			homeWindow.setProperty('context.umbrella.showUmbrella', '[B][COLOR '+setting('highlight.color')+']Umbrella[/COLOR][/B] - ')
		else:
			homeWindow.setProperty('context.umbrella.showUmbrella', '')
		homeWindow.setProperty('context.umbrella.highlightcolor', setting('highlight.color'))
	except:
		from resources.lib.modules import log_utils
		log_utils.error()


def checkPlayNextEpisodes():
	try:
		if setting('enable.playnext') == 'true': #we have to check for the episodes settings now
			nextEpisode = jsloads(jsonrpc('{"jsonrpc":"2.0", "method":"Settings.GetSettingValue", "params":{"setting":"videoplayer.autoplaynextitem"}, "id":1}'))
			#selectAction = jsloads(jsonrpc('{"jsonrpc":"2.0", "method":"Settings.GetSettingValue", "params":{"setting":"myvideos.selectaction"}, "id":1}'))
			try:
				nextEpisodeSetting = nextEpisode.get('result')['value'][0]
			except:
				nextEpisodeSetting = 0
			if nextEpisodeSetting != 2:
				jsonrpc('{"jsonrpc":"2.0", "method":"Settings.SetSettingValue", "params":{"setting":"videoplayer.autoplaynextitem", "value":[2]}, "id":1}')
			if not xbmc.getCondVisibility('Window.IsActive(settings)'):
				if setting('play.mode.tv') != '1':
					setSetting('play.mode.tv', '1')
		else:pass
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def removeCorruptSettings():
    #added 12-18 to attempt to correct corrupted settings.xml files.
	try:
		if not yesnoDialog('Delete settings file to try to fix blank settings?', 'You will need to re-authenticate services.','' , '[B]Confirm Clear[/B]', 'Cancel', 'Yes') == 1: return
		deleteFile(settingsFile)
		current_profile = infoLabel('system.profilename')
		execute('LoadProfile(%s)' % current_profile)
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def setContextColors():
	#tell me i cannot do some shit again.
	try:
		homeWindow.setProperty('context.umbrella.highlightcolor', setting('highlight.color'))
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def checkModules():
	if setting('provider.external.enabled') == 'false':
		setSetting('external_provider.name', '')
		setSetting('external_provider.module', '')

def backToMain(folder):
	if folder == 'movies':
		url = 'plugin://plugin.video.umbrella/?action=movieNavigator&folderName=Discover%20Movies'
	elif folder =='tvshows':
		url = 'plugin://plugin.video.umbrella/?action=tvNavigator&folderName=Discover%20TV%20Shows'
	else:
		url = None
	if url: execute('Container.Refresh(%s)'% url)

def timeFunction(function, *args):
	from timeit import default_timer as timer
	from datetime import timedelta
	start = timer()
	try:
		exeFunction = function(*args)
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	stop = timer()
	from resources.lib.modules import log_utils
	log_utils.log('Function Timer: %s Time: %s' %(_get_function_name(function), timedelta(seconds=stop-start)),1)
	return exeFunction

def _get_function_name(function_instance):
	return re_sub(r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', repr(function_instance))