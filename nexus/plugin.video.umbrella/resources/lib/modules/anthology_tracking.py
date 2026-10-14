"""Tracking integration for titles whose provider catalogs disagree."""
from importlib import import_module
from datetime import datetime
from resources.lib.modules import episode_mapping as mapping

PROVIDERS = {'1': 'trakt', '2': 'simkl', '3': 'mdblist', '4': 'customtrakt',
             '5': 'floppy', '6': 'scrob', '7': 'punchplay'}
SETTINGS = {'customtrakt': 'custom', 'mdblist': 'mdblist'}
CREDENTIALS = {'trakt': 'getTraktCredentialsInfo', 'simkl': 'getSimKLCredentialsInfo',
               'mdblist': 'getMDBListCredentialsInfo', 'customtrakt': 'getCustomCredentialsInfo',
               'floppy': 'getFloppyCredentialsInfo', 'scrob': 'getScrobCredentialsInfo',
               'punchplay': 'getPunchPlayCredentialsInfo'}


def module(name):
    return import_module('resources.lib.modules.' + name)


def local_indicators(tmdb):
    from resources.lib.database import watchedcache
    rows = watchedcache.get_episodes_watched('episode', '', str(tmdb))
    episodes = [(int(r['season']), int(r['episode'])) for r in rows if int(r['overlay']) == 5]
    return [({'tmdb': str(tmdb)}, len(episodes), episodes)]


def indicators(provider, tmdb):
    if provider == 'local':
        return local_indicators(tmdb)
    api = module(provider)
    if provider == 'simkl':
        return api.cachedTVShowIndicators()
    if provider == 'trakt':
        from resources.lib.database import traktsync
        return traktsync.cache_existing(api.syncTVShows) or []
    # These functions read the local episode tables, with no provider requests.
    return api.syncTVShows() or []


def season_indicators(provider, tmdb):
    return mapping.season_indicators(indicators(provider, tmdb), provider, tmdb)


def write(provider, tmdb, season, episode, remove):
    body = mapping.history_payload(provider, tmdb, season, episode)
    if str(tmdb) == mapping.BAKE_OFF:
        return write_bake_off(provider, str(tmdb), season, episode, remove, body)
    if provider == 'local':
        from resources.lib.database import watchedcache
        for en in ([int(episode)] if episode is not None else range(1, mapping.MONSTER[str(tmdb)][1] + 1)):
            watchedcache.change_watched('episode', '', str(tmdb), season=1, episode=en, watched=4 if remove else 5)
        return True
    api = module(provider)
    if provider in ('trakt', 'simkl', 'customtrakt', 'mdblist'):
        path = '/sync/watched' if provider == 'mdblist' else '/sync/history'
        if remove: path += '/remove'
        if provider == 'trakt': result = api.getTraktAsJson(path, body)
        elif provider == 'simkl': result = api.post_request(path, body)
        elif provider == 'customtrakt': result = api.getCustomAsJson(path, body)
        else: result = api.get_request(path, post=body)
        if not isinstance(result, dict) or result.get('error') or result.get('errors') or any((result.get('not_found') or {}).values()):
            return False
        # Reject errors/empty acknowledgements rather than invent watched history.
        if not any(k in result for k in ('added', 'deleted', 'existing', 'updated')):
            return False
        if provider in ('trakt', 'simkl'):
            api.cachesyncTVShows(timeout=0)
        else:
            update_local(provider, api, tmdb, episode, remove)
        return True
    suffix = 'AsNotWatched' if remove else 'AsWatched'
    if provider == 'punchplay':
        if episode is not None:
            return api._history_write('episode', imdb='', tmdb=str(tmdb), tvdb='', season=1, episode=int(episode), remove=remove)
        return api._season_watch('', '', 1, remove, str(tmdb))
    # Floppy and Scrob already implement their own permissions/cache updates.
    fn = getattr(api, ('markEpisode' if episode is not None else 'markSeason') + suffix)
    args = ('', '', 1, int(episode)) if episode is not None else ('', '', 1)
    return fn(*args, tmdb=str(tmdb))


def update_local(provider, api, tmdb, episode, remove, season=1):
    dbname, table = ('mdbsync', 'mdb_watched_episodes') if provider == 'mdblist' else ('customtraktsync', 'custom_watched_episodes')
    db = import_module('resources.lib.database.' + dbname)
    con = db.get_connection()
    try:
        cur = con.cursor()
        db._ensure_watched_tables(cur)
        episodes = [int(episode)] if episode is not None else range(1, mapping.season_totals(tmdb)[int(season)] + 1)
        for en in episodes:
            con.execute('DELETE FROM %s WHERE show_tmdb=? AND season=? AND episode=?' % table, (str(tmdb), int(season), en))
            if not remove:
                con.execute('INSERT INTO %s VALUES (?, ?, ?, ?, ?, ?)' % table,
                            ('', str(tmdb), '', int(season), en, datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')))
        con.commit()
    finally:
        con.close()
    db.cache_delete(db._hash_function(api.syncTVShows, ()))
    if provider == 'mdblist': api._clr_episode_progress_cache()
    else:
        from resources.lib.database import cache
        from resources.lib.menus.episodes import Episodes
        ep = Episodes()
        cache.remove(ep.custom_progress_list, 'customepisodesprogress', ep.custom_directProgressScrape)


def write_bake_off(provider, tmdb, season, episode, remove, body):
    seasons = list(mapping.season_totals(tmdb)) if season in (None, '') else [int(season)]
    if provider == 'local':
        from resources.lib.database import watchedcache
        for sn in seasons:
            for en in ([int(episode)] if episode is not None else range(1, mapping.season_totals(tmdb)[sn] + 1)):
                watchedcache.change_watched('episode', '', tmdb, season=sn, episode=en, watched=4 if remove else 5)
        return True
    api = module(provider)
    if provider in ('trakt', 'simkl', 'customtrakt', 'mdblist'):
        path = '/sync/watched' if provider == 'mdblist' else '/sync/history'
        if remove: path += '/remove'
        if provider == 'trakt': result = api.getTraktAsJson(path, body)
        elif provider == 'simkl': result = api.post_request(path, body)
        elif provider == 'customtrakt': result = api.getCustomAsJson(path, body)
        else: result = api.get_request(path, post=body)
        if not isinstance(result, dict) or result.get('error') or result.get('errors') or any((result.get('not_found') or {}).values()): return False
        if not any(k in result for k in ('added', 'deleted', 'existing', 'updated')): return False
        if provider in ('trakt', 'simkl'): api.cachesyncTVShows(timeout=0)
        else:
            for sn in seasons: update_local(provider, api, tmdb, episode, remove, season=sn)
        return True
    success = True
    for sn in seasons:
        if provider == 'punchplay':
            result = (api._history_write('episode', imdb='', tmdb=tmdb, tvdb='', season=sn, episode=int(episode), remove=remove)
                      if episode is not None else api._season_watch('', '', sn, remove, tmdb))
        else:
            suffix = 'AsNotWatched' if remove else 'AsWatched'
            fn = getattr(api, ('markEpisode' if episode is not None else 'markSeason') + suffix)
            args = ('', '', sn, int(episode)) if episode is not None else ('', '', sn)
            result = fn(*args, tmdb=tmdb)
        success = bool(result) and success
    return success


def manager_write(provider, tmdb, season, episode, remove, refresh):
    from resources.lib.modules import control, log_utils
    try:
        if provider == 'floppy' and module(provider).isReadOnly(): return False
        success = write(provider, str(tmdb), season, episode, remove)
    except Exception:
        log_utils.error()
        success = False
    if not success:
        control.notification(message='Unable to update mapped show history on %s' % provider)
    if refresh: control.refresh()
    control.trigger_widget_refresh()
    return success


def mark(tmdb, season=None, episode=None, watched=5, refresh=False):
    """Honor the primary indicator provider and enabled additional write targets."""
    from resources.lib.modules import control, log_utils
    selected = PROVIDERS.get(control.setting('indicators.alt'), 'local')
    targets = [selected]
    for provider in PROVIDERS.values():
        if provider != selected and control.setting(SETTINGS.get(provider, provider) + '.markwatched') == 'true':
            targets.append(provider)
    failures = []
    for provider in targets:
        try:
            if provider != 'local':
                api = module(provider)
                if not getattr(api, CREDENTIALS[provider])():
                    if provider == selected: failures.append(provider)
                    continue
                if provider == 'floppy' and api.isReadOnly(): continue
            if not write(provider, str(tmdb), season, episode, int(watched) != 5):
                failures.append(provider)
        except Exception:
            log_utils.error()
            failures.append(provider)
    if failures:
        control.notification(message='Unable to update mapped show history on: %s' % ', '.join(failures))
    if refresh: control.refresh()
    control.trigger_widget_refresh()
    return not failures
