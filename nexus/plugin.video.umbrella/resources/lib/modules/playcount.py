# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from resources.lib.modules.control import setting as getSetting, refresh as containerRefresh, addonInfo, progressDialogBG, monitor, condVisibility, execute
from resources.lib.modules import trakt
from resources.lib.modules import simkl
from resources.lib.modules import mdblist
from resources.lib.modules import customtrakt
from resources.lib.modules import floppy
from resources.lib.modules import scrob
tmdb_api_key = 'edde6b5e41246ab79a2697cd125e1781'
omdb_api_key = 'd4daa2b'
tvdb_api_key = '06cff30690f9b9622957044f2159ffae'
traktIndicators = trakt.getTraktIndicatorsInfo()
simklIndicators = simkl.getSimKLIndicatorsInfo()
mdblistIndicators = mdblist.getMDBListIndicatorsInfo()
customIndicators = customtrakt.getCustomIndicatorsInfo()
floppyIndicators = floppy.getFloppyIndicatorsInfo()
scrobIndicators = scrob.getScrobIndicatorsInfo()
traktCredentials = trakt.getTraktCredentialsInfo()
simklCredentials = simkl.getSimKLCredentialsInfo()
mdblistCredentials = mdblist.getMDBListCredentialsInfo()
customCredentials = customtrakt.getCustomCredentialsInfo()
floppyCredentials = floppy.getFloppyCredentialsInfo()
scrobCredentials = scrob.getScrobCredentialsInfo()
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
		elif mdblistIndicators:
			if not refresh: timeout = 720
			elif mdblist.getMoviesWatchedActivity() < mdblist.timeoutsyncMovies(): timeout = 720
			else: timeout = 0
			indicators = mdblist.cachesyncMovies(timeout=timeout)
			return indicators
		elif customIndicators:
			if not refresh: timeout = 720
			elif customtrakt.getMoviesWatchedActivity() < customtrakt.timeoutsyncMovies(): timeout = 720
			else: timeout = 0
			indicators = customtrakt.cachesyncMovies(timeout=timeout)
			return indicators
		elif floppyIndicators:
			if not refresh: timeout = 720
			elif floppy.getMoviesWatchedActivity() < floppy.timeoutsyncMovies(): timeout = 720
			else: timeout = 0
			indicators = floppy.cachesyncMovies(timeout=timeout)
			return indicators
		elif scrobIndicators:
			if not refresh: timeout = 720
			elif scrob.getMoviesWatchedActivity() < scrob.timeoutsyncMovies(): timeout = 720
			else: timeout = 0
			indicators = scrob.cachesyncMovies(timeout=timeout)
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
		elif mdblistIndicators:
			if not refresh: timeout = 720
			elif mdblist.getEpisodesWatchedActivity() < mdblist.timeoutsyncTVShows(): timeout = 720
			else: timeout = 0
			indicators = mdblist.cachesyncTVShows(timeout=timeout)
			return indicators
		elif customIndicators:
			if not refresh: timeout = 720
			elif customtrakt.getEpisodesWatchedActivity() < customtrakt.timeoutsyncTVShows(): timeout = 720
			else: timeout = 0
			indicators = customtrakt.cachesyncTVShows(timeout=timeout)
			return indicators
		elif floppyIndicators:
			if not refresh: timeout = 720
			elif floppy.getEpisodesWatchedActivity() < floppy.timeoutsyncTVShows(): timeout = 720
			else: timeout = 0
			indicators = floppy.cachesyncTVShows(timeout=timeout)
			return indicators
		elif scrobIndicators:
			if not refresh: timeout = 720
			elif scrob.getEpisodesWatchedActivity() < scrob.timeoutsyncTVShows(): timeout = 720
			else: timeout = 0
			indicators = scrob.cachesyncTVShows(timeout=timeout)
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

def getSeasonIndicators(imdb, tvdb, refresh=False, has_next_episode=False, tmdb_total_aired=None, force_lookup=False):
	try:
		if traktIndicators:
			timeoutsyncSeasons = trakt.timeoutsyncSeasons(imdb, tvdb)
			if timeoutsyncSeasons is None:
				if not force_lookup: return # if no entry means no completed season watched so do not make needless requests
				return trakt.cachesyncSeasons(imdb, tvdb, timeout=0) # caller needs an authoritative answer (e.g. Collection hide-watched filter), do a one-off live lookup
			if not refresh: timeout = 720
			elif trakt.getEpisodesWatchedActivity() < timeoutsyncSeasons: timeout = 720
			else: timeout = 0
			indicators = trakt.cachesyncSeasons(imdb, tvdb, timeout=timeout)
			# Trakt live API confirmed a new episode (has_next_episode) but cache shows all watched, or
			# TMDb's aired-episode count is higher than our cached total (tmdb_total_aired) — either way
			# the cached counts are stale. Force a refresh so this read and all subsequent reads across
			# all views see the correct count.
			if timeout != 0 and indicators:
				counts = indicators[1] if len(indicators) > 1 else {}
				if counts:
					cached_total = sum(v.get('total', 0) for v in counts.values())
					stale = (has_next_episode and cached_total == sum(v.get('watched', 0) for v in counts.values())) or \
						(tmdb_total_aired and int(tmdb_total_aired) > cached_total)
					if stale:
						indicators = trakt.cachesyncSeasons(imdb, tvdb, timeout=0)
			return indicators
		elif simklIndicators:
			timeoutsyncSeasons = simkl.timeoutsyncSeasons(imdb, tvdb)
			if timeoutsyncSeasons is None:
				if not force_lookup: return # if no entry means no completed season watched so do not make needless requests
				return simkl.cachesyncSeasons(imdb, tvdb, timeout=0) # caller needs an authoritative answer (e.g. Collection hide-watched filter), do a one-off live lookup
			if not refresh: timeout = 720
			elif simkl.getEpisodesWatchedActivity() < timeoutsyncSeasons: timeout = 720
			else: timeout = 0
			indicators = simkl.cachesyncSeasons(imdb, tvdb, timeout=timeout)
			# Simkl progress confirmed a new episode (has_next_episode) but cache shows all watched, or
			# TMDb's aired-episode count is higher than our cached total (tmdb_total_aired) — either way
			# the cached counts are stale. Force a refresh so this read and all subsequent reads across
			# all views see the correct count.
			if timeout != 0 and indicators:
				counts = indicators[1] if len(indicators) > 1 else {}
				if counts:
					cached_total = sum(v.get('total', 0) for v in counts.values())
					stale = (has_next_episode and cached_total == sum(v.get('watched', 0) for v in counts.values())) or \
						(tmdb_total_aired and int(tmdb_total_aired) > cached_total)
					if stale:
						indicators = simkl.cachesyncSeasons(imdb, tvdb, timeout=0)
			return indicators
		elif mdblistIndicators:
			# syncSeasons derives totals from TMDb season meta (96h cache) — always fetch fresh from local DB
			indicators = mdblist.cachesyncSeasons(imdb, tvdb, timeout=0)
			# MDBList progress confirmed a new episode (has_next_episode), or TMDb's aired-episode count is
			# higher than our cached total (tmdb_total_aired), but counts show all watched.
			# TMDb season meta may be stale — force-refresh it so syncSeasons picks up the new episode total.
			counts = indicators[1] if indicators and len(indicators) > 1 else {}
			cached_total = sum(v.get('total', 0) for v in counts.values()) if counts else 0
			stale = has_next_episode or (tmdb_total_aired and int(tmdb_total_aired) > cached_total)
			if stale and indicators:
				if counts and sum(v.get('watched', 0) for v in counts.values()) == cached_total:
					try:
						from resources.lib.database import cache as _cache
						from resources.lib.indexers import tmdb as _tmdb
						tmdb_result = _cache.get(_tmdb.TVshows().IdLookup, 96, imdb, tvdb)
						tmdb_id = str(tmdb_result.get('id', '')) if tmdb_result else ''
						if tmdb_id:
							_cache.get(_tmdb.TVshows().get_showSeasons_meta, 0, tmdb_id)  # force fresh, updates cache
							indicators = mdblist.cachesyncSeasons(imdb, tvdb, timeout=0)  # re-run with fresh totals
					except:
						from resources.lib.modules import log_utils
						log_utils.error()
			return indicators
		elif customIndicators:
			# syncSeasons derives totals from TMDb season meta (96h cache) — always fetch fresh from local DB
			indicators = customtrakt.cachesyncSeasons(imdb, tvdb, timeout=0)
			counts = indicators[1] if indicators and len(indicators) > 1 else {}
			cached_total = sum(v.get('total', 0) for v in counts.values()) if counts else 0
			stale = has_next_episode or (tmdb_total_aired and int(tmdb_total_aired) > cached_total)
			if stale and indicators:
				if counts and sum(v.get('watched', 0) for v in counts.values()) == cached_total:
					try:
						from resources.lib.database import cache as _cache
						from resources.lib.indexers import tmdb as _tmdb
						tmdb_result = _cache.get(_tmdb.TVshows().IdLookup, 96, imdb, tvdb)
						tmdb_id = str(tmdb_result.get('id', '')) if tmdb_result else ''
						if tmdb_id:
							_cache.get(_tmdb.TVshows().get_showSeasons_meta, 0, tmdb_id)  # force fresh, updates cache
							indicators = customtrakt.cachesyncSeasons(imdb, tvdb, timeout=0)  # re-run with fresh totals
					except:
						from resources.lib.modules import log_utils
						log_utils.error()
			return indicators
		elif floppyIndicators:
			# syncSeasons derives totals from TMDb season meta (96h cache) — always fetch fresh from local DB
			indicators = floppy.cachesyncSeasons(imdb, tvdb, timeout=0)
			counts = indicators[1] if indicators and len(indicators) > 1 else {}
			cached_total = sum(v.get('total', 0) for v in counts.values()) if counts else 0
			stale = has_next_episode or (tmdb_total_aired and int(tmdb_total_aired) > cached_total)
			if stale and indicators:
				if counts and sum(v.get('watched', 0) for v in counts.values()) == cached_total:
					try:
						from resources.lib.database import cache as _cache
						from resources.lib.indexers import tmdb as _tmdb
						tmdb_result = _cache.get(_tmdb.TVshows().IdLookup, 96, imdb, tvdb)
						tmdb_id = str(tmdb_result.get('id', '')) if tmdb_result else ''
						if tmdb_id:
							_cache.get(_tmdb.TVshows().get_showSeasons_meta, 0, tmdb_id)  # force fresh, updates cache
							indicators = floppy.cachesyncSeasons(imdb, tvdb, timeout=0)  # re-run with fresh totals
					except:
						from resources.lib.modules import log_utils
						log_utils.error()
			return indicators
		elif scrobIndicators:
			# syncSeasons derives totals from TMDb season meta (96h cache) — always fetch fresh from local DB
			indicators = scrob.cachesyncSeasons(imdb, tvdb, timeout=0)
			counts = indicators[1] if indicators and len(indicators) > 1 else {}
			cached_total = sum(v.get('total', 0) for v in counts.values()) if counts else 0
			stale = has_next_episode or (tmdb_total_aired and int(tmdb_total_aired) > cached_total)
			if stale and indicators:
				if counts and sum(v.get('watched', 0) for v in counts.values()) == cached_total:
					try:
						from resources.lib.database import cache as _cache
						from resources.lib.indexers import tmdb as _tmdb
						tmdb_result = _cache.get(_tmdb.TVshows().IdLookup, 96, imdb, tvdb)
						tmdb_id = str(tmdb_result.get('id', '')) if tmdb_result else ''
						if tmdb_id:
							_cache.get(_tmdb.TVshows().get_showSeasons_meta, 0, tmdb_id)  # force fresh, updates cache
							indicators = scrob.cachesyncSeasons(imdb, tvdb, timeout=0)  # re-run with fresh totals
					except:
						from resources.lib.modules import log_utils
						log_utils.error()
			return indicators
		else:
			from resources.lib.database import watchedcache
			return [watchedcache, watchedcache]
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
		elif mdblistIndicators or customIndicators or floppyIndicators or scrobIndicators:
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
		elif mdblistIndicators or customIndicators or floppyIndicators or scrobIndicators:
			playcount = {'total': 0, 'watched': 0}
			for key, value in iter(indicators.items()):
				playcount['total'] += value['total']
				playcount['watched'] += value['watched']
			playcount = '5' if playcount['total'] == playcount['watched'] else '4'
			return playcount
		else:
			playcount = indicators._get_watched('tvshow', imdb, '')
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
		elif mdblistIndicators or customIndicators or floppyIndicators or scrobIndicators:
			playcount = [i for i in indicators if int(season) == int(i)]
			playcount = '5' if len(playcount) > 0 else '4'
			return playcount
		else:
			playcount = indicators._get_watched('season', imdb, '', season)
			return str(playcount)
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return '4'

def getEpisodeOverlay(indicators, imdb, tvdb, season, episode):
	if not indicators: return '4'
	try:
		if traktIndicators or simklIndicators or mdblistIndicators or customIndicators or floppyIndicators or scrobIndicators:
			eps_data = [i[2] for i in indicators if (i[0].get('imdb') == imdb or str(i[0].get('tvdb')) == tvdb)]
			eps_data = eps_data[0] if eps_data else []
			if isinstance(eps_data, dict): # range format: {season: [(start_ep, end_ep), ...]}
				s_ranges = eps_data.get(int(season), [])
				ep_int = int(episode)
				return '5' if any(s <= ep_int <= e for s, e in s_ranges) else '4'
			else: # legacy tuple-list format: [(season, episode), ...]
				return '5' if any(int(season) == int(i[0]) and int(episode) == int(i[1]) for i in eps_data) else '4'
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
		elif mdblistIndicators or customIndicators or floppyIndicators or scrobIndicators:
			if not indicators: return None
			result = {'total': 0, 'watched': 0, 'unwatched': 0}
			for key, value in iter(indicators.items()):
				result['total'] += value['total']
				result['watched'] += value['watched']
				result['unwatched'] += value['unwatched']
			return result
		else:
			try:
				from resources.lib.database import watchedcache as wc
				from resources.lib.indexers import tmdb as tmdb_indexer
				from resources.lib.database import cache
				watched_count = wc.get_watched_count_for_show(imdb)
				if not watched_count: return None
				tmdb_result = cache.get(tmdb_indexer.TVshows().IdLookup, 96, imdb, tvdb)
				tmdb_id = str(tmdb_result.get('id')) if tmdb_result else ''
				if not tmdb_id: return None
				seasons_meta = cache.get(tmdb_indexer.TVshows().get_showSeasons_meta, 96, tmdb_id)
				total = sum(s.get('episode_count', 0) for s in (seasons_meta or {}).get('seasons', []) if s.get('season_number', 0) > 0)
				return {'total': total, 'watched': watched_count, 'unwatched': max(0, total - watched_count)}
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
				return None
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return None

def getSeasonCount(imdb, tvdb, season=None):
	try:
		if all(not value for value in (imdb, tvdb)): return
		#if not traktIndicators or not simklIndicators: return None # metahandler does not currently provide counts
		if traktIndicators: result = trakt.seasonCount(imdb, tvdb)
		elif simklIndicators: result = simkl.seasonCount(imdb, tvdb)
		elif mdblistIndicators: result = mdblist.seasonCount(imdb, tvdb)
		elif customIndicators: result = customtrakt.seasonCount(imdb, tvdb)
		elif floppyIndicators: result = floppy.seasonCount(imdb, tvdb)
		elif scrobIndicators: result = scrob.seasonCount(imdb, tvdb)
		else:
			try:
				from resources.lib.database import watchedcache as wc
				from resources.lib.indexers import tmdb as tmdb_indexer
				from resources.lib.database import cache
				tmdb_result = cache.get(tmdb_indexer.TVshows().IdLookup, 96, imdb, tvdb)
				tmdb_id = str(tmdb_result.get('id')) if tmdb_result else ''
				if not tmdb_id: return None
				seasons_meta = cache.get(tmdb_indexer.TVshows().get_showSeasons_meta, 96, tmdb_id)
				watched_eps = wc.get_watched_episode_ids(imdb)
				result = {}
				for s in (seasons_meta or {}).get('seasons', []):
					snum = s.get('season_number', 0)
					if snum == 0: continue
					total = s.get('episode_count', 0)
					watched = sum(1 for ep in watched_eps if int(ep[0]) == snum)
					result[snum] = {'total': total, 'watched': watched, 'unwatched': max(0, total - watched)}
				if not result: return None
				if not season: return result
				else: return result.get(int(season))
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
				return None
		if not result: return None
		if not season: return result
		else: return result.get(int(season))
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return None

def markMovieDuringPlayback(imdb, watched):
	try:
		watch_history_service = getSetting('indicators.alt')
		if watch_history_service == '1' and traktCredentials:
			if int(watched) == 5: trakt.markMovieAsWatched(imdb)
			else: trakt.markMovieAsNotWatched(imdb)
			if traktIndicators: trakt.cachesyncMovies()
		elif watch_history_service == '2' and simklCredentials:
			if int(watched) == 5: simkl.markMovieAsWatched(imdb)
			else: simkl.markMovieAsNotWatched(imdb)
			if simklIndicators: simkl.cachesyncMovies()
		elif watch_history_service == '3' and mdblistCredentials:
			if int(watched) == 5: mdblist.markMovieAsWatched(imdb)
			else: mdblist.markMovieAsNotWatched(imdb)
			if mdblistIndicators: mdblist.cachesyncMovies()
		elif watch_history_service == '4' and customCredentials:
			if int(watched) == 5: customtrakt.markMovieAsWatched(imdb)
			else: customtrakt.markMovieAsNotWatched(imdb)
			if customIndicators: customtrakt.cachesyncMovies()
		elif watch_history_service == '5' and floppyCredentials:
			if int(watched) == 5: floppy.markMovieAsWatched(imdb)
			else: floppy.markMovieAsNotWatched(imdb)
			if floppyIndicators: floppy.cachesyncMovies()
		elif watch_history_service == '6' and scrobCredentials:
			if int(watched) == 5: scrob.markMovieAsWatched(imdb)
			else: scrob.markMovieAsNotWatched(imdb)
			if scrobIndicators: scrob.cachesyncMovies()
		else:
			from resources.lib.database import watchedcache
			watchedcache.change_watched('movie', imdb, '', watched=int(watched))
		if watch_history_service != '1' and getSetting('trakt.markwatched') == 'true' and traktCredentials:
			if int(watched) == 5: trakt.markMovieAsWatched(imdb)
			else: trakt.markMovieAsNotWatched(imdb)
		if watch_history_service != '2' and getSetting('simkl.markwatched') == 'true' and simklCredentials:
			if int(watched) == 5: simkl.markMovieAsWatched(imdb)
			else: simkl.markMovieAsNotWatched(imdb)
		if watch_history_service != '3' and getSetting('mdblist.markwatched') == 'true' and mdblistCredentials:
			if int(watched) == 5: mdblist.markMovieAsWatched(imdb)
			else: mdblist.markMovieAsNotWatched(imdb)
		if watch_history_service != '4' and getSetting('custom.markwatched') == 'true' and customCredentials:
			if int(watched) == 5: customtrakt.markMovieAsWatched(imdb)
			else: customtrakt.markMovieAsNotWatched(imdb)
		if watch_history_service != '5' and getSetting('floppy.markwatched') == 'true' and floppyCredentials:
			if int(watched) == 5: floppy.markMovieAsWatched(imdb)
			else: floppy.markMovieAsNotWatched(imdb)
		if watch_history_service != '6' and getSetting('scrob.markwatched') == 'true' and scrobCredentials:
			if int(watched) == 5: scrob.markMovieAsWatched(imdb)
			else: scrob.markMovieAsNotWatched(imdb)
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def markEpisodeDuringPlayback(imdb, tvdb, season, episode, watched):
	try:
		watch_history_service = getSetting('indicators.alt')
		if watch_history_service == '1' and traktCredentials:
			if int(watched) == 5: trakt.markEpisodeAsWatched(imdb, tvdb, season, episode)
			else: trakt.markEpisodeAsNotWatched(imdb, tvdb, season, episode)
			if traktIndicators: trakt.cachesyncTV(imdb, tvdb)
		elif watch_history_service == '2' and simklCredentials:
			if int(watched) == 5: simkl.markEpisodeAsWatched(imdb, tvdb, season, episode)
			else: simkl.markEpisodeAsNotWatched(imdb, tvdb, season, episode)
			if simklIndicators: simkl.cachesyncTV(imdb, tvdb)
		elif watch_history_service == '3' and mdblistCredentials:
			if int(watched) == 5: mdblist.markEpisodeAsWatched(imdb, tvdb, season, episode)
			else: mdblist.markEpisodeAsNotWatched(imdb, tvdb, season, episode)
			if mdblistIndicators: mdblist.cachesyncTV(imdb, tvdb)
		elif watch_history_service == '4' and customCredentials:
			if int(watched) == 5: customtrakt.markEpisodeAsWatched(imdb, tvdb, season, episode)
			else: customtrakt.markEpisodeAsNotWatched(imdb, tvdb, season, episode)
			if customIndicators: customtrakt.cachesyncTV(imdb, tvdb)
		elif watch_history_service == '5' and floppyCredentials:
			if int(watched) == 5: floppy.markEpisodeAsWatched(imdb, tvdb, season, episode)
			else: floppy.markEpisodeAsNotWatched(imdb, tvdb, season, episode)
			if floppyIndicators: floppy.cachesyncTV(imdb, tvdb)
		elif watch_history_service == '6' and scrobCredentials:
			if int(watched) == 5: scrob.markEpisodeAsWatched(imdb, tvdb, season, episode)
			else: scrob.markEpisodeAsNotWatched(imdb, tvdb, season, episode)
			if scrobIndicators: scrob.cachesyncTV(imdb, tvdb)
		else:
			from resources.lib.database import watchedcache
			watchedcache.change_watched('episode', imdb, '', season=season, episode=episode, watched=int(watched))
		if watch_history_service != '1' and getSetting('trakt.markwatched') == 'true' and traktCredentials:
			if int(watched) == 5: trakt.markEpisodeAsWatched(imdb, tvdb, season, episode)
			else: trakt.markEpisodeAsNotWatched(imdb, tvdb, season, episode)
		if watch_history_service != '2' and getSetting('simkl.markwatched') == 'true' and simklCredentials:
			if int(watched) == 5: simkl.markEpisodeAsWatched(imdb, tvdb, season, episode)
			else: simkl.markEpisodeAsNotWatched(imdb, tvdb, season, episode)
		if watch_history_service != '3' and getSetting('mdblist.markwatched') == 'true' and mdblistCredentials:
			if int(watched) == 5: mdblist.markEpisodeAsWatched(imdb, tvdb, season, episode)
			else: mdblist.markEpisodeAsNotWatched(imdb, tvdb, season, episode)
		if watch_history_service != '4' and getSetting('custom.markwatched') == 'true' and customCredentials:
			if int(watched) == 5: customtrakt.markEpisodeAsWatched(imdb, tvdb, season, episode)
			else: customtrakt.markEpisodeAsNotWatched(imdb, tvdb, season, episode)
		if watch_history_service != '5' and getSetting('floppy.markwatched') == 'true' and floppyCredentials:
			if int(watched) == 5: floppy.markEpisodeAsWatched(imdb, tvdb, season, episode)
			else: floppy.markEpisodeAsNotWatched(imdb, tvdb, season, episode)
		if watch_history_service != '6' and getSetting('scrob.markwatched') == 'true' and scrobCredentials:
			if int(watched) == 5: scrob.markEpisodeAsWatched(imdb, tvdb, season, episode)
			else: scrob.markEpisodeAsNotWatched(imdb, tvdb, season, episode)
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def movies(name, imdb, watched):
	try:
		watch_history_service = getSetting('indicators.alt')
		if watch_history_service == '1' and traktCredentials:
			if int(watched) == 5: trakt.watch(content_type='movie', name=name, imdb=imdb, refresh=True)
			else: trakt.unwatch(content_type='movie', name=name, imdb=imdb, refresh=True)
		elif watch_history_service == '2' and simklCredentials:
			if int(watched) == 5: simkl.watch(content_type='movie', name=name, imdb=imdb, refresh=True)
			else: simkl.unwatch(content_type='movie', name=name, imdb=imdb, refresh=True)
		elif watch_history_service == '3' and mdblistCredentials:
			if int(watched) == 5: mdblist.watch(content_type='movie', name=name, imdb=imdb, refresh=True)
			else: mdblist.unwatch(content_type='movie', name=name, imdb=imdb, refresh=True)
		elif watch_history_service == '4' and customCredentials:
			if int(watched) == 5: customtrakt.watch(content_type='movie', name=name, imdb=imdb, refresh=True)
			else: customtrakt.unwatch(content_type='movie', name=name, imdb=imdb, refresh=True)
		elif watch_history_service == '5' and floppyCredentials:
			if int(watched) == 5: floppy.watch(content_type='movie', name=name, imdb=imdb, refresh=True)
			else: floppy.unwatch(content_type='movie', name=name, imdb=imdb, refresh=True)
		elif watch_history_service == '6' and scrobCredentials:
			if int(watched) == 5: scrob.watch(content_type='movie', name=name, imdb=imdb, refresh=True)
			else: scrob.unwatch(content_type='movie', name=name, imdb=imdb, refresh=True)
		else:
			from resources.lib.database import watchedcache
			watchedcache.change_watched('movie', imdb, '', title=name, watched=int(watched))
			containerRefresh()
		if watch_history_service != '1' and getSetting('trakt.markwatched') == 'true' and traktCredentials:
			if int(watched) == 5: trakt.watch(content_type='movie', name=name, imdb=imdb, refresh=False)
			else: trakt.unwatch(content_type='movie', name=name, imdb=imdb, refresh=False)
		if watch_history_service != '2' and getSetting('simkl.markwatched') == 'true' and simklCredentials:
			if int(watched) == 5: simkl.watch(content_type='movie', name=name, imdb=imdb, refresh=False)
			else: simkl.unwatch(content_type='movie', name=name, imdb=imdb, refresh=False)
		if watch_history_service != '3' and getSetting('mdblist.markwatched') == 'true' and mdblistCredentials:
			if int(watched) == 5: mdblist.watch(content_type='movie', name=name, imdb=imdb, refresh=False)
			else: mdblist.unwatch(content_type='movie', name=name, imdb=imdb, refresh=False)
		if watch_history_service != '4' and getSetting('custom.markwatched') == 'true' and customCredentials:
			if int(watched) == 5: customtrakt.watch(content_type='movie', name=name, imdb=imdb, refresh=False)
			else: customtrakt.unwatch(content_type='movie', name=name, imdb=imdb, refresh=False)
		if watch_history_service != '5' and getSetting('floppy.markwatched') == 'true' and floppyCredentials:
			if int(watched) == 5: floppy.watch(content_type='movie', name=name, imdb=imdb, refresh=False)
			else: floppy.unwatch(content_type='movie', name=name, imdb=imdb, refresh=False)
		if watch_history_service != '6' and getSetting('scrob.markwatched') == 'true' and scrobCredentials:
			if int(watched) == 5: scrob.watch(content_type='movie', name=name, imdb=imdb, refresh=False)
			else: scrob.unwatch(content_type='movie', name=name, imdb=imdb, refresh=False)
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def tvshows(tvshowtitle, imdb, tvdb, season, watched):
	try:
		watch_history_service = getSetting('indicators.alt')
		content_type = 'season' if season else 'tvshow'
		if watch_history_service == '1' and traktCredentials:
			if int(watched) == 5: trakt.watch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=True)
			else: trakt.unwatch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=True)
		elif watch_history_service == '2' and simklCredentials:
			if int(watched) == 5: simkl.watch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=True)
			else: simkl.unwatch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=True)
		elif watch_history_service == '3' and mdblistCredentials:
			if int(watched) == 5: mdblist.watch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=True)
			else: mdblist.unwatch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=True)
		elif watch_history_service == '4' and customCredentials:
			if int(watched) == 5: customtrakt.watch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=True)
			else: customtrakt.unwatch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=True)
		elif watch_history_service == '5' and floppyCredentials:
			if int(watched) == 5: floppy.watch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=True)
			else: floppy.unwatch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=True)
		elif watch_history_service == '6' and scrobCredentials:
			if int(watched) == 5: scrob.watch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=True)
			else: scrob.unwatch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=True)
		else:
			from resources.lib.database import watchedcache as wc
			from resources.lib.indexers import tmdb as tmdb_indexer
			from resources.lib.database import cache
			try:
				tmdb_result = cache.get(tmdb_indexer.TVshows().IdLookup, 96, imdb, tvdb)
				tmdb_id = str(tmdb_result.get('id')) if isinstance(tmdb_result, dict) else ''
				seasons_meta = cache.get(tmdb_indexer.TVshows().get_showSeasons_meta, 96, tmdb_id) if tmdb_id else {}
				for s in (seasons_meta if isinstance(seasons_meta, dict) else {}).get('seasons', []):
					snum = s.get('season_number', 0)
					if snum == 0: continue
					if season and str(snum) != str(season): continue
					for ep_num in range(1, s.get('episode_count', 0) + 1):
						wc.change_watched('episode', imdb, '', season=snum, episode=ep_num, title=tvshowtitle, watched=int(watched))
					wc.change_watched('season', imdb, '', season=snum, title=tvshowtitle, watched=int(watched))
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
			if not season:
				wc.change_watched('tvshow', imdb, '', title=tvshowtitle, watched=int(watched))
			containerRefresh()
		if watch_history_service != '1' and getSetting('trakt.markwatched') == 'true' and traktCredentials:
			if int(watched) == 5: trakt.watch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=False)
			else: trakt.unwatch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=False)
		if watch_history_service != '2' and getSetting('simkl.markwatched') == 'true' and simklCredentials:
			if int(watched) == 5: simkl.watch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=False)
			else: simkl.unwatch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=False)
		if watch_history_service != '3' and getSetting('mdblist.markwatched') == 'true' and mdblistCredentials:
			if int(watched) == 5: mdblist.watch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=False)
			else: mdblist.unwatch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=False)
		if watch_history_service != '4' and getSetting('custom.markwatched') == 'true' and customCredentials:
			if int(watched) == 5: customtrakt.watch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=False)
			else: customtrakt.unwatch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=False)
		if watch_history_service != '5' and getSetting('floppy.markwatched') == 'true' and floppyCredentials:
			if int(watched) == 5: floppy.watch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=False)
			else: floppy.unwatch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=False)
		if watch_history_service != '6' and getSetting('scrob.markwatched') == 'true' and scrobCredentials:
			if int(watched) == 5: scrob.watch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=False)
			else: scrob.unwatch(content_type=content_type, name=tvshowtitle, imdb=imdb, tvdb=tvdb, season=season, refresh=False)
		if watch_history_service != '0' and not (traktCredentials or simklCredentials or mdblistCredentials or customCredentials or floppyCredentials or scrobCredentials):
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
		watch_history_service = getSetting('indicators.alt')
		if watch_history_service == '1' and traktCredentials:
			if int(watched) == 5: trakt.watch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=True)
			else: trakt.unwatch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=True)
		elif watch_history_service == '2' and simklCredentials:
			if int(watched) == 5: simkl.watch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=True)
			else: simkl.unwatch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=True)
		elif watch_history_service == '3' and mdblistCredentials:
			if int(watched) == 5: mdblist.watch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=True)
			else: mdblist.unwatch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=True)
		elif watch_history_service == '4' and customCredentials:
			if int(watched) == 5: customtrakt.watch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=True)
			else: customtrakt.unwatch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=True)
		elif watch_history_service == '5' and floppyCredentials:
			if int(watched) == 5: floppy.watch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=True)
			else: floppy.unwatch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=True)
		elif watch_history_service == '6' and scrobCredentials:
			if int(watched) == 5: scrob.watch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=True)
			else: scrob.unwatch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=True)
		else:
			from resources.lib.database import watchedcache
			watchedcache.change_watched('episode', imdb, '', season=season, episode=episode, title=name, watched=int(watched))
			containerRefresh()
		if watch_history_service != '1' and getSetting('trakt.markwatched') == 'true' and traktCredentials:
			if int(watched) == 5: trakt.watch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=False)
			else: trakt.unwatch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=False)
		if watch_history_service != '2' and getSetting('simkl.markwatched') == 'true' and simklCredentials:
			if int(watched) == 5: simkl.watch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=False)
			else: simkl.unwatch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=False)
		if watch_history_service != '3' and getSetting('mdblist.markwatched') == 'true' and mdblistCredentials:
			if int(watched) == 5: mdblist.watch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=False)
			else: mdblist.unwatch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=False)
		if watch_history_service != '4' and getSetting('custom.markwatched') == 'true' and customCredentials:
			if int(watched) == 5: customtrakt.watch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=False)
			else: customtrakt.unwatch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=False)
		if watch_history_service != '5' and getSetting('floppy.markwatched') == 'true' and floppyCredentials:
			if int(watched) == 5: floppy.watch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=False)
			else: floppy.unwatch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=False)
		if watch_history_service != '6' and getSetting('scrob.markwatched') == 'true' and scrobCredentials:
			if int(watched) == 5: scrob.watch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=False)
			else: scrob.unwatch(content_type='episode', name=name, imdb=imdb, tvdb=tvdb, season=season, episode=episode, refresh=False)
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def tvshowsUpdate(imdb, tvdb):
	try:
		if traktCredentials: return
		if simklCredentials: return
		if mdblistCredentials: return
		if customCredentials: return
		if floppyCredentials: return
		if scrobCredentials: return
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