# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from json import loads as jsloads
import xbmc
from resources.lib.modules import control

Id = xbmc.PLAYLIST_VIDEO
videoplaylist = 10028
notification = True
refresh = True


def playlistManager(name=None, url=None, meta=None, art=None):
	try:
		items = []
		items += [(control.lang(32065), 'playlistAdd')]
		items += [(control.lang(35518), 'playlistRemove')]
		items += [(control.lang(35517), 'playlistShow')]
		items += [(control.lang(35516), 'playlistClear')]
		control.hide()
		select = control.selectDialog([i[0] for i in items], heading = control.addonInfo('name') + ' - ' + control.lang(35522))
		if select == -1: return
		if select >= 0:
			if select == 0:
				control.busy()
				playlistAdd(name, url, meta, art)
				control.hide()
			elif select == 1:
				control.busy()
				playlistRemove(name)
				control.hide()
			elif select == 2:
				control.busy()
				playlistShow()
				control.hide()
			elif select == 3:
				control.busy()
				playlistClear()
				control.hide()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		control.hide()

def playlist():
	return xbmc.PlayList(Id)

def playlistShow():
	if len(playListItems()) > 0:
		control.closeAll()
		videoplaylistID = 10028
		control.execute('ActivateWindow(%d)' % videoplaylistID)
	else:
		if notification: control.notification(title=35522, message=32119)

def playlistClear():
	playlist().clear()
	if notification: control.notification(title=35522, message=35521)

def playListItems():
	rpc = '{"jsonrpc": "2.0", "method": "Playlist.GetItems", "params": {"playlistid" : %s}, "id": 1 }' % Id
	result = control.jsonrpc(rpc)
	limits =jsloads(result)['result']['limits']
	total = limits['total']
	if int(total) <= 0: return []
	result = jsloads(result)['result']['items']
	try: return [i['label'] for i in result]
	except: return []

def position(label):
	try: return playListItems().index(label)
	except: return -1

def playlistAdd(name, url, meta, art):
	labelPosition = position(label=name)
	if labelPosition >= 0:
		return control.notification(title=35522, message=32120)
	if isinstance(meta, str):
		meta = jsloads(meta)
	if isinstance(art, str):
		art = jsloads(art)
	item = control.item(label=name, offscreen=True)
	item.setArt(art)
	item.setProperty('IsPlayable', 'true')
	#item.setInfo(type='video', infoLabels=control.metadataClean(meta))
	control.set_info(item, meta)
	cm = []
	item.addContextMenuItems(cm)
	playlist().add(url=url, listitem=item)
	if notification: control.notification(title=35522, message=control.lang(32121) % str(name))

def playlistRemove(name):
	labelPosition = position(label=name)
	if labelPosition >= 0:
		rpc = '{"jsonrpc": "2.0", "method": "Playlist.Remove", "params": {"playlistid": %s, "position": %s}, "id": 1 }' % (Id, labelPosition)
		control.jsonrpc(rpc)
		if notification: control.notification(title=35522, message=control.lang(32122) % str(name))
	if labelPosition == -1:
		if notification: control.notification(title=35522, message=32123)
	# control.refresh()