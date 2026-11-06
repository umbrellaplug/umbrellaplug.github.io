# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from sqlite3 import dbapi2 as db
from resources.lib.modules import control


def clearViews():
	try:
		skin = control.skin
		control.hide()
		if not control.yesnoDialog(control.lang(32056), '', ''): return
		control.makeFile(control.dataPath)
		dbcon = db.connect(control.viewsFile)
		dbcur = dbcon.cursor()
		try:
			dbcur.execute('''DROP TABLE IF EXISTS views''')
			dbcur.execute('''VACUUM''')
			dbcur.execute('''CREATE TABLE IF NOT EXISTS views (skin TEXT, view_type TEXT, view_id TEXT, UNIQUE(skin, view_type));''')
			dbcur.connection.commit()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
		try:
			kodiDB = control.transPath('special://home/userdata/Database')
			kodiViewsDB = control.joinPath(kodiDB, 'ViewModes6.db')
			dbcon = db.connect(kodiViewsDB)
			dbcur = dbcon.cursor()
			dbcur.execute('''DELETE FROM view WHERE path LIKE "plugin://plugin.video.umbrella/%"''')
			dbcur.connection.commit()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
		skinName = control.addon(skin).getAddonInfo('name')
		skinIcon = control.addon(skin).getAddonInfo('icon')
		control.notification(title=skinName, message=32087, icon=skinIcon)
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def addView(content):
	try:
		skin = control.skin
		record = (skin, content, str(control.getCurrentViewId()))
		control.makeFile(control.dataPath)
		dbcon = db.connect(control.viewsFile)
		dbcur = dbcon.cursor()
		dbcur.execute('''CREATE TABLE IF NOT EXISTS views (skin TEXT, view_type TEXT, view_id TEXT, UNIQUE(skin, view_type));''')
		dbcur.execute('''DELETE FROM views WHERE (skin=? AND view_type=?)''', (record[0], record[1]))
		dbcur.execute('''INSERT INTO views Values (?, ?, ?)''', record)
		dbcur.connection.commit()
		viewName = control.infoLabel('Container.Viewmode')
		skinName = control.addon(skin).getAddonInfo('name')
		skinIcon = control.addon(skin).getAddonInfo('icon')
		control.notification(title=skinName, message=viewName, icon=skinIcon)
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def _view_request_matches():
	try:
		from sys import argv
		from urllib.parse import urlsplit, parse_qsl
		requested = urlsplit(argv[0] + argv[2])
		visible = urlsplit(control.infoLabel('Container.FolderPath'))
		return (requested.scheme == visible.scheme == 'plugin'
			and requested.netloc == visible.netloc == 'plugin.video.umbrella'
			and requested.path.rstrip('/') == visible.path.rstrip('/')
			and sorted(parse_qsl(requested.query)) == sorted(parse_qsl(visible.query)))
	except Exception:
		return False


def setView(content, viewDict=None):
	# Resolve the preference first: most skins have no override to wait for.
	view = (viewDict or {}).get(control.skin)
	connection = None
	try:
		if control.existsPath(control.viewsFile):
			connection = db.connect(control.viewsFile, timeout=0.25)
			row = connection.execute('SELECT view_id FROM views WHERE skin=? AND view_type=?',
				(control.skin, content)).fetchone()
			if row: view = row[0]
	except db.Error:
		pass
	finally:
		if connection is not None: connection.close()
	if view is None: return
	# endOfDirectory may precede the GUI update. Check immediately, then wait
	# briefly and cancellably; never set a view on another listing or a widget.
	for attempt in range(21):
		if control.monitor.abortRequested(): return
		if (control.condVisibility('Window.IsActive(videos)') and _view_request_matches()
				and control.condVisibility('Container.Content(%s)' % content)):
			if str(control.getCurrentViewId()) != str(view):
				return control.execute('Container.SetViewMode(%s)' % view)
			return
		if attempt < 20 and control.monitor.waitForAbort(0.05): return
