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

def setView(content, viewDict=None):
	for i in range(0, 200):
		control.sleep(300)
		if control.condVisibility('Container.Content(%s)' % content):
			try:
				skin = control.skin
				record = (skin, content)
				dbcon = db.connect(control.viewsFile)
				dbcur = dbcon.cursor()
				view = dbcur.execute('''SELECT * FROM views WHERE (skin=? AND view_type=?)''', (record[0], record[1])).fetchone()
				if not view: raise Exception()
				view = view[2]
				return control.execute('Container.SetViewMode(%s)' % str(view))
			except:
				try:
					control.sleep(100)
					skin = control.skin
					record = (skin, content)
					dbcon = db.connect(control.viewsFile)
					dbcur = dbcon.cursor()
					view = dbcur.execute('''SELECT * FROM views WHERE (skin=? AND view_type=?)''', (record[0], record[1])).fetchone()
					if not view: raise Exception()
					view = view[2]
					return control.execute('Container.SetViewMode(%s)' % str(view))
				except:
					try:
						if skin not in viewDict: return
						else:
							return control.execute('Container.SetViewMode(%s)' % str(viewDict[skin]))
					except:
						from resources.lib.modules import log_utils
						log_utils.error()
						return
			finally:
				dbcur.close() ; dbcon.close()
	control.sleep(100)