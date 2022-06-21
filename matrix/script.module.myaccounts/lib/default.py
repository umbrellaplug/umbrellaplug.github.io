# -*- coding: utf-8 -*-

'''
	My Accounts
'''

import sys
from urllib.parse import parse_qsl
from myaccounts.modules import control

control.set_active_monitor()

params = {}
for param in sys.argv[1:]:
	param = param.split('=')
	param_dict = dict([param])
	params = dict(params, **param_dict)

action = params.get('action')
query = params.get('query')
addon_id = params.get('addon_id')

if action and not any(i in action for i in ['Auth', 'Revoke']):
	control.release_active_monitor()

if action is None:
	control.openSettings(query, "script.module.myaccounts")

elif action == 'traktAcct':
	from myaccounts.modules import trakt
	trakt.Trakt().account_info_to_dialog()

elif action == 'traktAuth':
	from myaccounts.modules import trakt
	control.function_monitor(trakt.Trakt().auth)

elif action == 'traktRevoke':
	from myaccounts.modules import trakt
	control.function_monitor(trakt.Trakt().revoke)

elif action == 'alldebridAcct':
	from myaccounts.modules import alldebrid
	alldebrid.AllDebrid().account_info_to_dialog()

elif action == 'alldebridAuth':
	from myaccounts.modules import alldebrid
	control.function_monitor(alldebrid.AllDebrid().auth)

elif action == 'alldebridRevoke':
	from myaccounts.modules import alldebrid
	control.function_monitor(alldebrid.AllDebrid().revoke)

elif action == 'premiumizeAcct':
	from myaccounts.modules import premiumize
	premiumize.Premiumize().account_info_to_dialog()

elif action == 'premiumizeAuth':
	from myaccounts.modules import premiumize
	control.function_monitor(premiumize.Premiumize().auth)

elif action == 'premiumizeRevoke':
	from myaccounts.modules import premiumize
	control.function_monitor(premiumize.Premiumize().revoke)

elif action == 'realdebridAcct':
	from myaccounts.modules import realdebrid
	realdebrid.RealDebrid().account_info_to_dialog()

elif action == 'realdebridAuth':
	from myaccounts.modules import realdebrid
	control.function_monitor(realdebrid.RealDebrid().auth)

elif action == 'realdebridRevoke':
	from myaccounts.modules import realdebrid
	control.function_monitor(realdebrid.RealDebrid().revoke)

elif action == 'tmdbAuth':
	from myaccounts.modules import tmdb
	control.function_monitor(tmdb.Auth().create_session_id)

elif action == 'tmdbRevoke':
	from myaccounts.modules import tmdb
	control.function_monitor(tmdb.Auth().revoke_session_id)

elif action == 'ShowChangelog':
	from myaccounts.modules import changelog
	changelog.get()

elif action == 'ShowHelp':
	from myaccounts.help import help
	help.get(params.get('name'))

elif action == 'ShowOKDialog':
	control.okDialog(params.get('title', 'default'), int(params.get('message', '')))

elif action == 'tools_clearLogFile':
	from myaccounts.modules import log_utils
	cleared = log_utils.clear_logFile()
	if cleared == 'canceled': pass
	elif cleared: control.notification(message='My Accounts Log File Successfully Cleared')
	else: control.notification(message='Error clearing My Accounts Log File, see kodi.log for more info')

elif action == 'tools_viewLogFile':
	from myaccounts.modules import log_utils
	log_utils.view_LogFile(params.get('name'))

elif action == 'tools_uploadLogFile':
	from myaccounts.modules import log_utils
	log_utils.upload_LogFile()