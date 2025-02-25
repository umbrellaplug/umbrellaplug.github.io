# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from resources.lib.modules.control import setting as getSetting, refresh as containerRefresh, addonInfo, progressDialogBG, monitor, condVisibility, execute
from resources.lib.modules import trakt
from resources.lib.modules import simkl
tmdb_api_key = 'edde6b5e41246ab79a2697cd125e1781'
omdb_api_key = 'd4daa2b'
tvdb_api_key = '06cff30690f9b9622957044f2159ffae'
traktIndicators = trakt.getTraktIndicatorsInfo()
simklIndicators = simkl.getSimKLIndicatorsInfo()
traktCredentials = trakt.getTraktCredentialsInfo()
simklCredentials = simkl.getSimKLCredentialsInfo()
#if not traktIndicators:
#	try:
#		if not condVisibility('System.HasAddon(script.module.metahandler)'): execute('InstallAddon(script.module.metahandler)', wait=True)
#	except: pass


def getMovieIndicators(refresh=False):
	try:
		if traktIndicators:
			if not refresh: timeout = 720
			elif trakt.getMoviesWatchedActivity() < trakt.timeoutsyncMovies(): timeout = 720
			else: timeout = 0
			indicators = trakt.cachesyncMovies(timeout=timeout)
			return indicators
		elif simklIndicators:
			if not refresh: timeout = 720
			elif simkl.getMoviesWatchedActivity() < simkl.timeoutsyncMovies(): timeout = 720
			else: timeout = 0
			indicators = simkl.cachesyncMovies(timeout=timeout)
			return indicators
		else:
#			from metahandler import metahandlers
#			indicators = metahandlers.MetaData(tmdb_api_key, omdb_api_key, tvdb_api_key)
			from resources.lib.database import watchedcache
			indicators = watchedcache
			return indicators
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def getTVShowIndicators(refresh=False):
	try:
		if traktIndicators:
			if not refresh: timeout = 720
			elif trakt.getEpisodesWatchedActivity() < trakt.timeoutsyncTVShows(): timeout = 720
			else: timeout = 0
			indicators = trakt.cachesyncTVShows(timeout=timeout)
			return indicators
		elif simklIndicators:
			if not refresh: timeout = 720
			elif simkl.getEpisodesWatchedActivity() < simkl.timeoutsyncTVShows(): timeout = 720
			else: timeout = 0
			indicators = simkl.cachesyncTVShows(timeout=timeout)
			return indicators
		else:
#			from metahandler import metahandlers
#			indicators = metahandlers.MetaData(tmdb_api_key, omdb_api_key, tvdb_api_key)
			from resources.lib.database import watchedcache
			indicators = watchedcache
			return indicators
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def getSeasonIndicators(imdb, tvdb, refresh=False):
	try:
		if traktIndicators:
			timeoutsyncSeasons = trakt.timeoutsyncSeasons(imdb, tvdb)
			if timeoutsyncSeasons is None: return # if no entry means no completed season watched so do not make needless requests 
			if not refresh: timeout = 720
			elif trakt.getEpisodesWatchedActivity() < timeoutsyncSeasons: timeout = 720
			else: timeout = 0
			indicators = trakt.cachesyncSeasons(imdb, tvdb, timeout=timeout)
			return indicators
		elif simklIndicators:
			timeoutsyncSeasons = simkl.timeoutsyncSeasons(imdb, tvdb)
			if timeoutsyncSeasons is None: return # if no entry means no completed season watched so do not make needless requests 
			if not refresh: timeout = 720
			elif simkl.getEpisodesWatchedActivity() < timeoutsyncSeasons: timeout = 720
			else: timeout = 0
			indicators = simkl.cachesyncSeasons(imdb, tvdb, timeout=timeout)
			return indicators
		else:
#			from metahandler import metahandlers
#			indicators = metahandlers.MetaData(tmdb_api_key, omdb_api_key, tvdb_api_key)
			from resources.lib.database import watchedcache
			indicators = watchedcache
			return indicators
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def getMovieOverlay(indicators, imdb):
	if not indicators: return '4'
	try:
		if traktIndicators:
			playcount = [i for i in indicators if i == imdb]
			playcount = '5' if len(playcount) > 0 else '4'
			return playcount
		elif simklIndicators:
			playcount = [i for i in indicators if i == imdb]
			playcount = '5' if len(playcount) > 0 else '4'
			return playcount
		else: # indicators will be metahandler object
			playcount = indicators.get_watched('movie', imdb, '')
			return str(playcount)
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return '4'

def getTVShowOverlay(indicators, imdb, tvdb): # tvdb no longer used
	if not indicators: return '4'
	try: #{1: {'total': 10, 'watched': 10, 'unwatched': 0}, 2: {'total': 2, 'watched': 2, 'unwatched': 0}}
		if traktIndicators:
			playcount = {'total': 0, 'watched': 0}
			for key, value in iter(indicators.items()):
				playcount['total'] += value['total']
				playcount['watched'] += value['watched']
			playcount = '5' if playcount['total'] == playcount['watched'] else '4'
			return playcount
		elif simklIndicators:
			playcount = {'total': 0, 'watched': 0}
			for key, value in iter(indicators.items()):
				playcount['total'] += value['total']
				playcount['watched'] += value['watched']
			playcount = '5' if playcount['total'] == playcount['watched'] else '4'
			return playcount
		else: # indicators will be metahandler object
			playcount = indicators._get_watched('tvshow', imdb, '', '')
			return str(playcount)
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return '4'

def getSeasonOverlay(indicators, imdb, tvdb, season): # tvdb no longer used
	if not indicators: return '4'
	try:
		if traktIndicators:
			playcount = [i for i in indicators if int(season) == int(i)]
			playcount = '5' if len(playcount) > 0 else '4'
			return playcount
		elif simklIndicators:
			playcount = [i for i in indicators if int(season) == int(i)]
			playcount = '5' if len(playcount) > 0 else '4'
			return playcount
		else: # indicators will be metahandler object
			playcount = indicators._get_watched('season', imdb, '', season)
			return str(playcount)
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return '4'

def getEpisodeOverlay(indicators, imdb, tvdb, season, episode):
	if not indicators: return '4'
	try:
		if traktIndicators:
			playcount = [i[2] for i in indicators if (i[0].get('imdb') == imdb or str(i[0].get('tvdb')) == tvdb)]
			playcount = playcount[0] if len(playcount) > 0 else []
			playcount = [i for i in playcount if int(season) == int(i[0]) and int(episode) == int(i[1])]
			playcount = '5' if len(playcount) > 0 else '4'
			return playcount
		elif simklIndicators:
			playcount = [i[2] for i in indicators if (i[0].get('imdb') == imdb or str(i[0].get('tvdb')) == tvdb)]
			playcount = playcount[0] if len(playcount) > 0 else []
			playcount = [i for i in playcount if int(season) == int(i[0]) and int(episode) == int(i[1])]
			playcount = '5' if len(playcount) > 0 else '4'
			return playcount
		else: # indicators will be metahandler object
			playcount = indicators.get_watched_episode('episode', imdb, '', season=season, episode=episode)
			return str(playcount)
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return '4'

def getShowCount(indicators, imdb, tvdb): # ID's currently not used. totals from indicators
	try:
		if traktIndicators:
			if not indicators: return None
			result = {'total': 0, 'watched': 0, 'unwatched': 0}
			for key, value in iter(indicators.items()):
				result['total'] += value['total']
				result['watched'] += value['watched']
				result['unwatched'] += value['unwatched']
			return result
		elif simklIndicators:
			if not indicators: return None
			result = {'total': 0, 'watched': 0, 'unwatched': 0}
			for key, value in iter(indicators.items()):
				result['total'] += value['total']
				result['watched'] += value['watched']
				result['unwatched'] += value['unwatched']
			return result
		else: return None # metahandler does not currently provide counts
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return None

def getSeasonCount(imdb, tvdb, season=None):
	try:
		if all(not value for value in (imdb, tvdb)): return
		if not traktIndicators or not simklIndicators: return None # metahandler does not currently provide counts
		if traktIndicators: result = trakt.seasonCount(imdb, tvdb)
		elif simklIndicators: result = simkl.seasonCount(imdb, tvdb)
		if not result: return None
		if not season: return result
		else: return result.get(int(season))
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return None

def markMovieDuringPlayback(imdb, watched):
	try:
		if traktCredentials:
			if int(watched) == 5: trakt.markMovieAsWatched(imdb)
			else: trakt.markMovieAsNotWatched(imdb)
			if traktIndicators:trakt.cachesyncMovies()
		if simklCredentials:
			if int(watched) == 5: simkl.markMovieAsWatched(imdb)
			else: simkl.markMovieAsNotWatched(imdb)
			if simklIndicators: simkl.cachesyncMovies()
		else:
#			from metahandler import metahandlers
#			metaget = metahandlers.MetaData(tmdb_api_key, omdb_api_key, tvdb_api_key)
#			metaget.get_meta('movie', name='', imdb_id=imdb)
#			metaget.change_watched('movie', name='', imdb_id=imdb, watched=int(watched))
			from resources.lib.database import watchedcache
			watchedcache.change_watched('movie', imdb, '', watched=int(watched))
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def markEpisodeDuringPlayback(imdb, tvdb, season, episode, watched):
	try:
		if traktCredentials:
			if int(watched) == 5: trakt.markEpisodeAsWatched(imdb, tvdb, season, episode)
			else: trakt.markEpisodeAsNotWatched(imdb, tvdb, season, episode)
			if traktIndicators: trakt.cachesyncTV(imdb, tvdb) # updates all watched shows, as well as season indicators and counts for given ID of show
		if simklCredentials:
			if int(watched) == 5: simkl.markEpisodeAsWatched(imdb, tvdb, season, episode)
			else: simkl.markEpisodeAsNotWatched(imdb, tvdb, season, episode)
			if simklIndicators: simkl.cachesyncTV(imdb, tvdb)
		else:
#			from metahandler import metahandlers
#			metaget = metahandlers.MetaData(tmdb_api_key, omdb_api_key, tvdb_api_key)
#			metaget.get_meta('tvshow', name='', imdb_id=imdb)
#			metaget.get_episode_meta('', imdb_id=imdb, season=season, episode=episode)
#			metaget.change_watched('episode', '', imdb_id=imdb, season=season, episode=episode, watched=int(watched))
			from resources.lib.database import watchedcache
			watchedcache.change_watched('episode', imdb, '', season=season, episode=episode, watched=int(watched))
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def movies(name, imdb, watched):
	try:
		if traktCredentials:
			if int(watched) == 5: trakt.watch(content_type='movie', name=name, imdb=imdb, refresh=True)
			else: trakt.unwatch(content_type='movie', name=name, imdb=imdb, refresh=True)
		if simklCredentials:
			if int(watched) == 5: simkl.watch(content_type='movie', name=name, imdb=imdb, refresh=True)
			else: simkl.unwatch(content_type='movie', name=name, imdb=imdb, refresh=True)
		else:
#			from metahandler import metahandlers
#			metaget = metahandlers.MetaData(tmdb_api_key, omdb_api_key, tvdb_api_key)
#			metaget.get_meta('movie', name=name, imdb_id=imdb)
#			metaget.change_watched('movie', name=name, imdb_id=imdb, watched=int(watched))
			from resources.lib.database import watchedcache
			watchedcache.change_watched('movie', imdb, '', title=name, watched=int(watched))
			containerRefresh()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def tvshows(tvshowtitle, imdb, tvdb, season, watched):
	try:
		if traktCredentials:
			content_type='season' if season else 'tvshow'
			if int(watched) == 5: trakt.watch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=True)
			else: trakt.unwatch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=True)
		if simklCredentials:
			content_type='season' if season else 'tvshow'
			if int(watched) == 5: simkl.watch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=True)
			else: simkl.unwatch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=True)
		else:
			from metahandler import metahandlers
			from resources.lib.menus import episodes
			from sys import exit as sysexit

			name = addonInfo('name')
			dialog = progressDialogBG
			dialog.create(str(name), str(tvshowtitle))
			dialog.update(0, str(name), str(tvshowtitle))

			metaget = metahandlers.MetaData(tmdb_api_key, omdb_api_key, tvdb_api_key)
			metaget.get_meta('tvshow', name='', imdb_id=imdb)
			items = episodes.Episodes().get(tvshowtitle, '0', imdb, tvdb, {}, create_directory=False)

			for i in range(len(items)):
				items[i]['season'] = int(items[i]['season'])
				items[i]['episode'] = int(items[i]['episode'])
			try: items = [i for i in items if int('%01d' % int(season)) == int('%01d' % i['season'])]
			except: pass

			items = [{'label': '%s S%02dE%02d' % (tvshowtitle, i['season'], i['episode']), 'season': int('%01d' % i['season']), 'episode': int('%01d' % i['episode'])} for i in items]
			count = len(items)
			for i in range(count):
				if monitor.abortRequested(): return sysexit()
				dialog.update(int(100.0 / count * i), str(name), str(items[i]['label']))
				season, episode = items[i]['season'], items[i]['episode']
				metaget.get_episode_meta('', imdb_id=imdb, season=season, episode=episode)
				metaget.change_watched('episode', '', imdb_id=imdb, season=season, episode=episode, watched=int(watched))
			tvshowsUpdate(imdb=imdb, tvdb=tvdb)

			try: dialog.close()
			except: pass
			del dialog
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def seasons(tvshowtitle, imdb, tvdb, season, watched):
	tvshows(tvshowtitle=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, watched=watched)

def episodes(name, imdb, tvdb, season, episode, watched):
	try:
		if traktCredentials:
			if int(watched) == 5: trakt.watch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=True)
			else: trakt.unwatch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=True)
		if simklCredentials:
			if int(watched) == 5: simkl.watch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=True)
			else: simkl.unwatch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=True)
		else:
#			from metahandler import metahandlers
#			metaget = metahandlers.MetaData(tmdb_api_key, omdb_api_key, tvdb_api_key)
#			show_meta = metaget.get_meta('tvshow', name=name, imdb_id=imdb)
#			episode_meta = metaget.get_episode_meta(name, imdb_id=imdb, season=season, episode=episode)
#			metaget.change_watched('episode', '', imdb_id=imdb, season=season, episode=episode, watched=int(watched))
			from resources.lib.database import watchedcache
			watchedcache.change_watched('episode', imdb, '', season=season, episode=episode, title=name, watched=int(watched))
			# watched_episodes = metaget._get_watched_episode({'imdb_id': imdb, 'season': season, 'episode': episode, 'premiered': ''})
#			watched_episodes = metaget._get_watched_episode({'imdb_id': imdb, 'tvdb_id': tvdb, 'season': season, 'episode': episode, 'premiered': ''})
			# tvshowsUpdate(imdb=imdb, tvdb=tvdb) # control.refresh() done in this function
			containerRefresh()
			# tvshowsUpdate(imdb=imdb, tvdb=tvdb) # control.refresh() done in this function
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def tvshowsUpdate(imdb, tvdb):
	try:
		if traktCredentials: return
		if simklCredentials: return
		from metahandler import metahandlers
		from resources.lib.menus import seasons, episodes
		from resources.lib.indexers import tmdb as tmdb_indexer
		from resources.lib.database import cache

		# name = addonInfo('name')
		metaget = metahandlers.MetaData(tmdb_api_key, omdb_api_key, tvdb_api_key)
		show_meta = metaget.get_meta('tvshow', name='', imdb_id=imdb)
		tvshowtitle = show_meta.get('title', '') # useless because it's in cleantitle format
		# seasons_meta = seasons.Seasons().get('', '', imdb, '', tvdb, {}, create_directory=False)
		# items = seasons.Seasons().get('', '', imdb, '', tvdb, {}, create_directory=False)
	# def get(self, tvshowtitle, year, imdb, tmdb, tvdb, art, idx=True, create_directory=True):

		tmdb = ''
		if not tmdb and (imdb or tvdb):
			try:
				result = cache.get(tmdb_indexer.TVshows().IdLookup, 96, imdb, tvdb)
				tmdb = str(result.get('id')) if result else ''
			except:
				if getSetting('debug.level') != '1': return
				from resources.lib.modules import log_utils
				return log_utils.log('tvshowtitle: (%s) missing tmdb_id: ids={imdb: %s, tmdb: %s, tvdb: %s}' % (tvshowtitle, imdb, tmdb, tvdb), __name__, log_utils.LOGDEBUG) # log TMDb shows that they do not have
		items = cache.get(tmdb_indexer.TVshows().get_showSeasons_meta, 96, tmdb)
		items = items.get('seasons', [])
		# for i in items:

		# items = episodes.Episodes().get('', '', imdb, '', tvdb, {}, create_directory=False)
	# def get(self, tvshowtitle, year, imdb, tmdb, tvdb, meta, season=None, episode=None, create_directory=True):

		for i in range(len(items)):
			items[i]['season'] = int(items[i]['season'])
			items[i]['episode'] = int(items[i]['episode'])

		seasons = {}
		for i in items:
			if i['season'] not in seasons: seasons[i['season']] = []
			seasons[i['season']].append(i)

		countSeason = 0
		metaget.get_seasons('', imdb, seasons.keys()) # Must be called to initialize the database.

		for key, value in iter(seasons.items()):
			countEpisode = 0
			for i in value:
				countEpisode += int(metaget._get_watched_episode({'imdb_id': i['imdb'], 'season': i['season'], 'episode': i['episode'], 'premiered': ''}) == 5)
			countSeason += int(countEpisode == len(value))
			metaget.change_watched('season', '', imdb_id=imdb, season=key, watched = 5 if countEpisode == len(value) else 4)
		metaget.change_watched('tvshow', '', imdb_id=imdb, watched = 5 if countSeason == len(seasons.keys()) else 4)
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	containerRefresh()