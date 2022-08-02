# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""


from resources.lib.modules.control import setting as getSetting, setSetting, notification
from resources.lib.modules import control


def syncMyAccounts(silent=False):
	# try:
	# 	all_acct = myaccounts.getAll()
	# 	trakt_acct = all_acct.get('trakt')
	# 	if getSetting('trakt.user.token') != trakt_acct.get('token'):
	# 		trakt_username = trakt_acct.get('username')
	# 		setSetting('trakt.user.name', trakt_username)
	# 		if trakt_username != '': setSetting('trakt.isauthed', 'true')
	# 		else: setSetting('trakt.isauthed', '')
	# 		setSetting('trakt.token.expires', trakt_acct.get('expires'))
	# 		setSetting('trakt.user.token', trakt_acct.get('token'))
	# 		setSetting('trakt.refreshtoken', trakt_acct.get('refresh'))

	# 	ad_acct = all_acct.get('alldebrid')
	# 	if getSetting('alldebridusername') != ad_acct.get('username'):
	# 		setSetting('alldebridtoken', ad_acct.get('token'))
	# 		# if getSetting('alldebridtoken') == '': setSetting('alldebrid.enable', 'false')
	# 		setSetting('alldebridusername', ad_acct.get('username'))

	# 	pm_acct = all_acct.get('premiumize')
	# 	if getSetting('premiumizeusername') != pm_acct.get('username'):
	# 		setSetting('premiumizetoken', pm_acct.get('token'))
	# 		# if getSetting('premiumizetoken') == '': setSetting('premiumize.enable', 'false')
	# 		setSetting('premiumizeusername', pm_acct.get('username'))

	# 	rd_acct = all_acct.get('realdebrid') # token refresh 1hr expiry, Umbrella handles this internally
	# 	if getSetting('realdebridusername') != rd_acct.get('username'):
	# 		setSetting('realdebridtoken', rd_acct.get('token'))
	# 		# if getSetting('realdebridtoken') == '': setSetting('realdebrid.enable', 'false')
	# 		setSetting('realdebridusername', rd_acct.get('username'))
	# 		setSetting('realdebrid.clientid', rd_acct.get('client_id'))
	# 		setSetting('realdebridrefresh', rd_acct.get('refresh'))
	# 		setSetting('realdebridsecret', rd_acct.get('secret'))

	# 	fp_acct = all_acct.get('filepursuit')
	# 	if getSetting('filepursuit.api') != fp_acct.get('api_key'):
	# 		setSetting('filepursuit.api', fp_acct.get('api_key'))

	# 	fu_acct = all_acct.get('furk')
	# 	if getSetting('furk.user.name') != fu_acct.get('username'):
	# 		setSetting('furk.user.name', fu_acct.get('username'))
	# 		setSetting('furk.pass.word', fu_acct.get('password'))
	# 	if getSetting('furk.api') != fu_acct.get('api_key'):
	# 		setSetting('furk.api', fu_acct.get('api_key'))

	# 	en_acct = all_acct.get('easyNews')
	# 	if getSetting('easynewsusername') != en_acct.get('username'):
	# 		setSetting('easynewsusername', en_acct.get('username'))
	# 		setSetting('easynewspassword', en_acct.get('password'))

	# 	or_acct = all_acct.get('ororo')
	# 	if getSetting('ororo.username') != or_acct.get('email'):
	# 		setSetting('ororo.username', or_acct.get('email'))
	# 		setSetting('ororo.password', or_acct.get('password'))

	# 	fanart_acct = all_acct.get('fanart_tv')
	# 	if getSetting('fanart_tv.api_key') != fanart_acct.get('api_key'):
	# 		setSetting('fanart_tv.api_key', fanart_acct.get('api_key'))

	# 	tmdb_acct = all_acct.get('tmdb')
	# 	if getSetting('tmdb.apikey') != tmdb_acct.get('api_key'):
	# 		setSetting('tmdb.apikey', tmdb_acct.get('api_key'))
	# 	if getSetting('tmdbusername') != tmdb_acct.get('username'):
	# 		setSetting('tmdbusername', tmdb_acct.get('username'))
	# 	if getSetting('tmdbpassword') != tmdb_acct.get('password'):
	# 		setSetting('tmdbpassword', tmdb_acct.get('password'))
	# 	if getSetting('tmdb.sessionid') != tmdb_acct.get('session_id'):
	# 		setSetting('tmdb.sessionid', tmdb_acct.get('session_id'))

	# 	# tvdb_acct = all_acct.get('tvdb') # no longer used in Umbrella
	# 	# if getSetting('tvdb.apikey') != tvdb_acct.get('api_key'):
	# 		# setSetting('tvdb.apikey', tvdb_acct.get('api_key'))

	# 	imdb_acct = all_acct.get('imdb')
	# 	if getSetting('imdbuser') != imdb_acct.get('user'):
	# 		setSetting('imdbuser', imdb_acct.get('user'))

	# 	if not silent: notification(message=32114)
	# except:
	from resources.lib.modules import log_utils
	#log_utils.error()
	log_utils.log('My accounts sync function removed.', level=log_utils.LOGWARNING)
