# -*- coding: utf-8 -*-
"""
	Umbrellascrapers Module
"""
import sqlite3 as db
from umbrellascrapers.modules.control import existsPath, dataPath, makeFile, undesirablescacheFile, lang

class Undesirables():
	def get_enabled(self):
		self.make_database_objects()
		results = self.dbcur.execute('SELECT keyword FROM undesirables WHERE enabled = ?', (True,))
		return self.process_keywords(results)

	def get_default(self):
		self.make_database_objects()
		results = self.dbcur.execute('SELECT keyword FROM undesirables WHERE user_defined = ?', (False,))
		return self.process_keywords(results)

	def get_user_defined(self):
		self.make_database_objects()
		results = self.dbcur.execute('SELECT keyword FROM undesirables WHERE user_defined = ?', (True,))
		return self.process_keywords(results)

	def get_all(self):
		self.make_database_objects()
		results = self.dbcur.execute('SELECT keyword FROM undesirables')
		return self.process_keywords(results)

	def set_many(self, undesirables):
		self.make_database_objects()
		self.dbcur.executemany('INSERT OR REPLACE INTO undesirables VALUES (?, ?, ?)', undesirables)
		self.dbcon.commit()
		self.dbcon.close()

	def remove_many(self, undesirables):
		self.make_database_objects()
		self.dbcur.executemany('DELETE FROM undesirables WHERE keyword = ?', undesirables)
		self.dbcon.commit()
		self.dbcon.close()

	def make_connection(self):
		self.dbcon = db.connect(undesirablescacheFile, timeout=60)

	def make_cursor(self):
		self.dbcur = self.dbcon.cursor()
		self.dbcur.execute('''PRAGMA synchronous = OFF''')
		self.dbcur.execute('''PRAGMA journal_mode = OFF''')

	def make_database_objects(self):
		self.make_connection()
		self.make_cursor()

	def check_database(self):
		if not existsPath(dataPath): makeFile(dataPath)
		self.make_database_objects()
		try:
			self.dbcur.execute('SELECT keyword FROM undesirables WHERE user_defined = ?', (False,)).fetchone()[0]
			self.dbcon.close()
			return True
		except:
			self.dbcur.execute('CREATE TABLE IF NOT EXISTS undesirables (keyword TEXT NOT NULL, user_defined BOOL NOT NULL, enabled BOOL NOT NULL, UNIQUE(keyword))')
			self.set_defaults()
			return False

	def set_defaults(self):
		from umbrellascrapers.modules.source_utils import UNDESIRABLES
		self.set_many([(i, False, True) for i in UNDESIRABLES])

	def process_keywords(self, results):
		keywords = sorted([i[0] for i in results.fetchall()])
		self.dbcon.close()
		return keywords

def undesirablesSelect():
	from umbrellascrapers.modules.control import multiselectDialog
	from umbrellascrapers.modules.source_utils import UNDESIRABLES
	undesirables_cache = Undesirables()
	chosen = undesirables_cache.get_enabled()
	try: preselect = [UNDESIRABLES.index(i) for i in chosen]
	except: preselect = [UNDESIRABLES.index(i) for i in UNDESIRABLES]
	choices = multiselectDialog(UNDESIRABLES, preselect=preselect, heading=lang(32085))
	if not choices: return
	enabled = [UNDESIRABLES[i] for i in choices]
	disabled = [i for i in UNDESIRABLES if not i in enabled]
	new_settings = [(i, False, i in enabled) for i in UNDESIRABLES]
	undesirables_cache.set_many(new_settings)

def undesirablesUserRemove():
	from umbrellascrapers.modules.control import multiselectDialog, notification
	undesirables_cache = Undesirables()
	user_undesirables = undesirables_cache.get_user_defined()
	if not user_undesirables: return notification(message=32084)
	choices = multiselectDialog(user_undesirables, heading=lang(32086))
	if not choices: return
	removals = [(user_undesirables[i],) for i in choices]
	undesirables_cache.remove_many(removals)

def undesirablesUserRemoveAll():
	from umbrellascrapers.modules.control import yesnoDialog, notification
	undesirables_cache = Undesirables()
	user_undesirables = undesirables_cache.get_user_defined()
	if not user_undesirables: return notification(message=32084)
	if not yesnoDialog(lang(32060)): return
	removals = [(i,) for i in user_undesirables]
	undesirables_cache.remove_many(removals)
	notification(message=32087)

def undesirablesInput():
	from umbrellascrapers.modules.control import dialog
	undesirables_cache = Undesirables()
	user_defined = undesirables_cache.get_user_defined()
	if user_defined: current_user_string = ','.join(user_defined)
	else: current_user_string = ''
	undesirables_string = dialog.input(heading=lang(32048), defaultt=current_user_string)
	if not undesirables_string: return
	new_undesirables = undesirables_string.replace(' ', '').split(',')
	new_settings = [(i, True, True) for i in new_undesirables]
	undesirables_cache.set_many(new_settings)

def add_new_default_keywords():
	from umbrellascrapers.modules.source_utils import UNDESIRABLES
	undesirables_cache = Undesirables()
	current_undesirables = undesirables_cache.get_default()
	new_undesirables = [i for i in UNDESIRABLES if not i in current_undesirables]
	if not new_undesirables: return
	new_settings = [(i, False, True) for i in new_undesirables]
	undesirables_cache.set_many(new_settings)