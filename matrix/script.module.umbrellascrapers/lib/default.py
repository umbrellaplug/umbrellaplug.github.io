# -*- coding: utf-8 -*-
"""
	Umbrellascrapers Module
"""

from sys import argv
from urllib.parse import parse_qsl
from umbrellascrapers import sources_umbrellascrapers
from umbrellascrapers.modules import control

params = dict(parse_qsl(argv[2].replace('?', '')))
action = params.get('action')
mode = params.get('mode')
query = params.get('query')
name = params.get('name')

if action is None:
	control.openSettings('0.0', 'script.module.umbrellascrapers')

if action == "umbrellascrapersSettings":
	control.openSettings('0.0', 'script.module.umbrellascrapers')

elif mode == "umbrellascrapersSettings":
	control.openSettings('0.0', 'script.module.umbrellascrapers')

elif action == 'ShowChangelog':
	from umbrellascrapers.modules import changelog
	changelog.get()

elif action == 'ShowHelp':
	from umbrellascrapers.help import help
	help.get(name)

elif action == "Defaults":
	sourceList = []
	sourceList = sources_umbrellascrapers.all_providers
	for i in sourceList:
		source_setting = 'provider.' + i
		value = control.getSettingDefault(source_setting)
		control.setSetting(source_setting, value)

elif action == "toggleAll":
	sourceList = []
	sourceList = sources_umbrellascrapers.all_providers
	for i in sourceList:
		source_setting = 'provider.' + i
		control.setSetting(source_setting, params['setting'])

elif action == "toggleAllHosters":
	sourceList = []
	sourceList = sources_umbrellascrapers.hoster_providers
	for i in sourceList:
		source_setting = 'provider.' + i
		control.setSetting(source_setting, params['setting'])

elif action == "toggleAllTorrent":
	sourceList = []
	sourceList = sources_umbrellascrapers.torrent_providers
	for i in sourceList:
		source_setting = 'provider.' + i
		control.setSetting(source_setting, params['setting'])

elif action == "toggleAllPackTorrent":
	control.execute('RunPlugin(plugin://script.module.umbrellascrapers/?action=toggleAllTorrent&amp;setting=false)')
	control.sleep(500)
	sourceList = []
	from umbrellascrapers import pack_sources
	sourceList = pack_sources()
	for i in sourceList:
		source_setting = 'provider.' + i
		control.setSetting(source_setting, params['setting'])

elif action == 'openMyAccount':
	from myaccounts import openMASettings
	openMASettings('0.0')
	control.sleep(500)
	while control.condVisibility('Window.IsVisible(addonsettings)') or control.homeWindow.getProperty('myaccounts.active') == 'true':
		control.sleep(500)
	control.sleep(100)
	control.syncMyAccounts()
	control.sleep(100)
	if params.get('opensettings') == 'true':
		control.openSettings(query, 'script.module.umbrellascrapers')

elif action == 'syncMyAccount':
	control.syncMyAccounts()
	if params.get('opensettings') == 'true':
		control.openSettings(query, 'script.module.umbrellascrapers')

elif action == 'cleanSettings':
	control.clean_settings()

elif action == 'undesirablesSelect':
	from umbrellascrapers.modules.undesirables import undesirablesSelect
	undesirablesSelect()

elif action == 'undesirablesInput':
	from umbrellascrapers.modules.undesirables import undesirablesInput
	undesirablesInput()

elif action == 'undesirablesUserRemove':
	from umbrellascrapers.modules.undesirables import undesirablesUserRemove
	undesirablesUserRemove()

elif action == 'undesirablesUserRemoveAll':
	from umbrellascrapers.modules.undesirables import undesirablesUserRemoveAll
	undesirablesUserRemoveAll()

elif action == 'tools_clearLogFile':
	from umbrellascrapers.modules import log_utils
	cleared = log_utils.clear_logFile()
	if cleared == 'canceled': pass
	elif cleared: control.notification(message='umbrellascrapers Log File Successfully Cleared')
	else: control.notification(message='Error clearing umbrellascrapers Log File, see kodi.log for more info')

elif action == 'tools_viewLogFile':
	from umbrellascrapers.modules import log_utils
	log_utils.view_LogFile(name)

elif action == 'tools_uploadLogFile':
	from umbrellascrapers.modules import log_utils
	log_utils.upload_LogFile()