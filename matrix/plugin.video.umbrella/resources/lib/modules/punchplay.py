# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""
import json
import time
import uuid
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from email.utils import parsedate_to_datetime
from threading import Lock
from urllib.parse import urlencode

import requests
from resources.lib.database import punchplaysync
from resources.lib.modules import control, log_utils

BASE_URL = 'https://punchplay.tv/api/platform/v1'
PUBLIC_URL = 'https://punchplay.tv/api/public/v1'
CLIENT_ID = 'ppc_a1ff58cf1a767f044d66308b'
CLIENT_SECRET = 'pps_c8a0d48febe54904858bac23ac17cc412008aa0e7cc36bc7fe03206657b766a2'
SCOPES = ('profile:read history:read history:write playback:read playback:write '
          'lists:read lists:write ratings:read ratings:write collection:read collection:write')
getSetting = control.setting
setSetting = control.setSetting
_session = requests.Session()
_refresh_lock = Lock()
_sync_lock = Lock()
_playback_lock = Lock()
_sessions = {}
_server_clock = None


@contextmanager
def _account_sync_lock():
    # A separate database lets token refresh proceed while this lock is held.
    con = sqlite3.connect(control.punchplaySyncFile + '.lock', timeout=120)
    try:
        con.execute('CREATE TABLE IF NOT EXISTS sync_lock (id INTEGER PRIMARY KEY)')
        con.execute('BEGIN IMMEDIATE')
        yield
    finally:
        con.close()


class PunchPlayError(Exception):
    pass


def _now_iso():
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')


def _watch_time():
    # PunchPlay rejects even small future offsets. Prefer the API's clock,
    # allowing for HTTP Date's whole-second precision and clock differences.
    if _server_clock is not None:
        stamp, received = _server_clock
        now = stamp + max(0, time.monotonic() - received)
    else:
        now = time.time()
    return datetime.utcfromtimestamp(now - 5).strftime('%Y-%m-%dT%H:%M:%S.000Z')


def _credentials():
    body = {'client_id': CLIENT_ID.strip()}
    secret = CLIENT_SECRET.strip()
    if secret:
        body['client_secret'] = secret
    return body


def _connection():
    con = punchplaysync.get_connection()
    con.execute('CREATE TABLE IF NOT EXISTS punchplay_state (key TEXT PRIMARY KEY, value TEXT)')
    return con


def _state(key, default=None):
    with _connection() as con:
        row = con.execute('SELECT value FROM punchplay_state WHERE key=?', (key,)).fetchone()
    con.close()
    return json.loads(row[0]) if row else default


def _put(con, key, value):
    con.execute('INSERT OR REPLACE INTO punchplay_state VALUES (?, ?)', (key, json.dumps(value)))


def _save_tokens(data, con=None):
    tokens = dict(data, client_id=_credentials()['client_id'])
    tokens['generation'] = data.get('generation') or str(uuid.uuid4())
    tokens['expires_at'] = time.time() + int(data.get('expires_in') or 3600)
    own = con is None
    if own:
        con = _connection()
    _put(con, 'tokens', tokens)
    if own:
        con.commit()
        con.close()
    for key, value in [('accesstoken', tokens['access_token']), ('refreshtoken', tokens.get('refresh_token', '')),
                       ('tokenexpiry', str(tokens['expires_at'])), ('isauthed', 'true')]:
        setSetting('punchplay.' + key, value)
    return tokens


def _tokens():
    tokens = _state('tokens', {})
    if tokens.get('client_id') != _credentials()['client_id']:
        return {}
    return tokens


def getPunchPlayCredentialsInfo():
    tokens = _tokens() if CLIENT_ID.strip() and getSetting('punchplay.accesstoken') else {}
    return bool(CLIENT_ID.strip() and getSetting('punchplay.accesstoken')
                and getSetting('punchplay.isauthed') == 'true' and tokens
                and not tokens.get('reauth_required'))


def getPunchPlayWriteCredentialsInfo():
    return getPunchPlayCredentialsInfo()


def getPunchPlayIndicatorsInfo():
    return getPunchPlayCredentialsInfo() and getSetting('indicators.alt') == '7'


def _notify(message):
    if getSetting('punchplay.general.notifications') == 'true':
        control.notification(title='PunchPlay', message=message)


def _error(response):
    try:
        data = response.json()
    except ValueError:
        data = {}
    code = data.get('error') or 'http_%s' % response.status_code
    request_id = data.get('request_id') or response.headers.get('X-PunchPlay-Request-Id', '')
    # Never include submitted credentials or response bodies in logs.
    log_utils.log('PunchPlay: %s (HTTP %s, request_id=%s)' % (code, response.status_code, request_id),
                  level=log_utils.LOGWARNING)
    return PunchPlayError('%s%s' % (code, ' (request %s)' % request_id if request_id else ''))


def _refresh(failed_token=None, generation=None):
    # SQLite serializes refreshes across Kodi plugin invocations as well as threads.
    with _refresh_lock:
        con = _connection()
        try:
            con.execute('BEGIN IMMEDIATE')
            row = con.execute("SELECT value FROM punchplay_state WHERE key='tokens'").fetchone()
            current = json.loads(row[0]) if row else {}
            if generation and current.get('generation') != generation:
                raise PunchPlayError('PunchPlay account changed; request cancelled.')
            if current.get('reauth_required'):
                raise PunchPlayError('Please authorize PunchPlay again.')
            if current.get('client_id') != _credentials()['client_id'] or not current.get('refresh_token'):
                raise PunchPlayError('Please authorize PunchPlay again.')
            if failed_token and current.get('access_token') != failed_token:
                return current
            if not failed_token and current.get('expires_at', 0) > time.time() + 60:
                return current
            response = _session.post(BASE_URL + '/auth/refresh',
                                     json=dict(_credentials(), refresh_token=current['refresh_token']), timeout=20)
            if response.status_code != 200:
                try: invalid_grant = response.json().get('error') == 'invalid_grant'
                except (ValueError, AttributeError): invalid_grant = False
                if invalid_grant:
                    # Persist across plugin invocations so every heartbeat does
                    # not retry the same rejected refresh token and hit limits.
                    current['reauth_required'] = True
                    _put(con, 'tokens', current)
                    con.commit()
                    setSetting('punchplay.isauthed', 'false')
                    control.notification(title='PunchPlay', message='Session expired. Please authorize PunchPlay again in settings.')
                raise _error(response)
            result = _save_tokens(dict(response.json(), generation=current.get('generation')), con)
            con.commit()
            return result
        except requests.RequestException:
            raise PunchPlayError('Unable to refresh PunchPlay authorization.')
        finally:
            con.close()


def _request(path, method='GET', body=None, headers=None, auth=True, public=False):
    global _server_clock
    if public:
        if method != 'GET':
            raise PunchPlayError('The public catalog is read-only.')
        auth = False
    # Native DELETE routes parse JSON even where OpenAPI documents no body.
    if method == 'DELETE' and body is None:
        body = {}
    if not path.startswith('/') or path.startswith('//'):
        raise PunchPlayError('Invalid PunchPlay path')
    tokens = _tokens() if auth else {}
    generation = tokens.get('generation')
    if auth:
        if not tokens:
            raise PunchPlayError('Please authorize PunchPlay.')
        if tokens.get('reauth_required'):
            raise PunchPlayError('Please authorize PunchPlay again.')
        if tokens.get('expires_at', 0) <= time.time() + 60:
            tokens = _refresh(generation=generation)
    for attempt in range(3):
        if auth and _tokens().get('generation') != generation:
            raise PunchPlayError('PunchPlay account changed; request cancelled.')
        request_headers = {'Accept': 'application/json'}
        request_headers.update(headers or {})
        if auth:
            request_headers['Authorization'] = 'Bearer ' + tokens['access_token']
        try:
            response = _session.request(method, (PUBLIC_URL if public else BASE_URL) + path, json=body,
                                        headers=request_headers, timeout=20)
        except requests.RequestException:
            # Retry only reads and explicitly idempotent mutations.
            if attempt < 2 and (method == 'GET' or (headers or {}).get('Idempotency-Key') or
                                path.startswith('/playback/') and body and body.get('event_id')):
                if control.monitor.waitForAbort(2 ** attempt):
                    raise PunchPlayError('Request cancelled')
                continue
            raise PunchPlayError('Unable to connect to PunchPlay.')
        if response.status_code == 401 and auth and attempt == 0:
            tokens = _refresh(tokens['access_token'], generation)
            continue
        if response.status_code == 429 and attempt < 2:
            delay = max(float(response.headers.get('Retry-After') or 5), 1)
            if delay > 30 or control.monitor.waitForAbort(delay):
                raise _error(response)
            continue
        if 200 <= response.status_code < 300:
            server_date = response.headers.get('Date')
            if isinstance(server_date, str) and server_date:
                try:
                    _server_clock = (parsedate_to_datetime(server_date).timestamp(), time.monotonic())
                except (ValueError, TypeError, OverflowError):
                    pass
            return response.json() if response.content else {}
        if response.status_code >= 500 and attempt < 2 and (method == 'GET' or
                (headers or {}).get('Idempotency-Key') or path.startswith('/playback/') and body and body.get('event_id')):
            if control.monitor.waitForAbort(2 ** attempt):
                raise PunchPlayError('Request cancelled')
            continue
        raise _error(response)
    raise PunchPlayError('PunchPlay request failed.')


def _pages(path):
    """Read complete cursor, offset or page-number collections; fail without truncation."""
    items, seen = [], set()
    current = path
    while current:
        if control.monitor.abortRequested():
            raise PunchPlayError('Sync cancelled')
        data = _request(current)
        if isinstance(data, list):
            return items + data
        if not isinstance(data, dict) or not isinstance(data.get('items'), list):
            raise PunchPlayError('Unexpected PunchPlay collection response')
        items.extend(data['items'])
        param, value = None, None
        if data.get('nextCursor') is not None:
            param, value = 'cursor', data['nextCursor']
        elif data.get('nextOffset') is not None:
            param, value = 'offset', data['nextOffset']
        elif data.get('hasMore'):
            param, value = 'page', int(data.get('page') or 1) + 1
        if param is None:
            break
        marker = (param, str(value))
        if marker in seen:
            raise PunchPlayError('PunchPlay pagination did not advance')
        seen.add(marker)
        from urllib.parse import urlsplit, parse_qsl
        query = dict(parse_qsl(urlsplit(path).query))
        query[param] = value
        current = path.split('?')[0] + '?' + urlencode(query)
    return items


def _offer_provider_selection():
    if not control.yesnoDialog(
            'Use PunchPlay for watched history, watched indicators, and playback scrobbling?',
            '', '', 'Umbrella - PunchPlay', 'No', 'Yes'):
        return False
    control.homeWindow.setProperty('umbrella.updateSettings', 'false')
    try:
        setSetting('indicators.alt', '7')
        setSetting('scrobble.source', '7')
        setSetting('indicators', 'PunchPlay')
        setSetting('scrobble', 'PunchPlay')
    finally:
        control.homeWindow.setProperty('umbrella.updateSettings', 'true')
    control.trigger_widget_refresh()
    return True


def punchplayAuth(fromSettings=0):
    if not _credentials()['client_id']:
        control.okDialog(title='PunchPlay', message='The Umbrella PunchPlay client ID has not been configured in punchplay.py.')
        return
    dialog = control.progressDialog
    try:
        device = _request('/auth/device/code', 'POST', dict(_credentials(), scope=SCOPES), auth=False)
        expires = time.time() + int(device.get('expires_in') or 600)
        interval = max(int(device.get('interval') or 5), 5)
        message = 'Visit %s\nEnter code: [B]%s[/B]' % (device['verification_uri'], device['user_code'])
        dialog.create('Umbrella - PunchPlay', message)
        result = None
        while time.time() < expires and not dialog.iscanceled():
            if control.monitor.waitForAbort(interval):
                return
            response = _session.post(BASE_URL + '/auth/device/token',
                                     json=dict(_credentials(), device_code=device['device_code'],
                                               device_name='Umbrella Kodi'), timeout=20)
            if response.status_code == 200:
                result = response.json()
                break
            data = response.json()
            if response.status_code == 429 or data.get('error') == 'slow_down':
                interval = max(interval + 5, int(response.headers.get('Retry-After') or 0))
            elif data.get('error') != 'authorization_pending':
                raise _error(response)
            dialog.update(max(0, min(99, int(100 * (1 - (expires - time.time()) / int(device.get('expires_in') or 600))))), message)
        if not result:
            return
        # Verify identity/scopes before replacing any existing account's cache.
        response = _session.get(BASE_URL + '/me', headers={'Authorization': 'Bearer ' + result['access_token']}, timeout=20)
        if response.status_code != 200:
            raise _error(response)
        me = response.json()
        missing = set(SCOPES.split()) - set(me.get('scopes') or [])
        if missing:
            raise PunchPlayError('Enable these app scopes and authorize again: ' + ', '.join(sorted(missing)))
        con = _connection()
        try:
            con.execute('BEGIN IMMEDIATE')
            for table in ('punchplay_watched_movies', 'punchplay_watched_episodes', 'punchplay_lists', 'bookmarks', 'watched'):
                con.execute('DROP TABLE IF EXISTS ' + table)
            con.execute('DELETE FROM punchplay_state')
            _put(con, 'account', me['id'])
            _save_tokens(result, con)
            con.commit()
        finally:
            con.close()
        setSetting('punchplay.username', me.get('username') or me.get('name') or '')
        dialog.close()
        control.notification(title='PunchPlay', message='PunchPlay authorized')
        _offer_provider_selection()
        sync_account(forced=True)
        control.trigger_widget_refresh()
    except (PunchPlayError, requests.RequestException, ValueError, KeyError) as exc:
        control.okDialog(title='PunchPlay', message='PunchPlay authorization failed: %s' % exc if isinstance(exc, PunchPlayError)
                         else 'PunchPlay authorization failed. Please try again.')
    finally:
        dialog.close()
        if fromSettings:
            control.openSettings('5.0', 'plugin.video.umbrella')


def punchplayRevoke(fromSettings=0):
    tokens = _tokens()
    try:
        if tokens:
            _request('/oauth/revoke', 'POST', dict(_credentials(), token=tokens.get('refresh_token') or tokens['access_token']), auth=False)
    except PunchPlayError:
        control.notification(title='PunchPlay', message='Local authorization cleared; revoke the app on PunchPlay to remove remote access.')
    finally:
        con = _connection()
        try:
            for table in ('punchplay_state', 'punchplay_watched_movies', 'punchplay_watched_episodes', 'punchplay_lists', 'bookmarks', 'watched'):
                con.execute('DROP TABLE IF EXISTS ' + table)
            con.commit()
        finally:
            con.close()
        for key in ('accesstoken', 'refreshtoken', 'tokenexpiry', 'isauthed', 'username'):
            setSetting('punchplay.' + key, '')
        for key, label in [('indicators.alt', 'indicators'), ('scrobble.source', 'scrobble')]:
            if getSetting(key) == '7':
                setSetting(key, '0')
                setSetting(label, 'Local')
        control.trigger_widget_refresh()
        if fromSettings:
            control.openSettings('5.0', 'plugin.video.umbrella')


def _resolve_tmdb(media_type, imdb='', tvdb=''):
    from resources.lib.database import cache
    from resources.lib.indexers import tmdb
    if media_type == 'movie':
        result = cache.get(tmdb.Movies().IdLookup, 96, imdb) if imdb else None
    else:
        result = cache.get(tmdb.TVshows().IdLookup, 96, imdb, tvdb) if imdb or tvdb else None
    return str((result or {}).get('id') or '')


def _resolve_movie_imdb(tmdb_id):
    from resources.lib.database import cache
    from resources.lib.indexers import tmdb
    result = cache.get(tmdb.Movies().get_external_ids, 96, str(tmdb_id), '')
    return str((result or {}).get('imdb_id') or '')


def _resolve_tv_imdb(tmdb_id):
    from resources.lib.database import cache
    from resources.lib.indexers import tmdb
    result = cache.get(tmdb.TVshows().get_external_ids, 96, str(tmdb_id))
    return str((result or {}).get('imdb_id') or '')


def _title_id(tmdb='', imdb='', tvdb=''):
    if tmdb and str(tmdb).isdigit() and int(tmdb) > 0:
        return str(tmdb)
    if imdb and str(imdb).startswith('tt') and str(imdb)[2:].isdigit():
        return str(imdb)
    if tvdb and str(tvdb).isdigit() and int(tvdb) > 0:
        return 'tvdb:' + str(tvdb)
    raise PunchPlayError('No valid media identifier is available.')


def _title(kind, tmdb='', imdb='', tvdb=''):
    return _request('/title/%s/%s' % (kind, _title_id(tmdb, imdb, tvdb)))


def _identity(kind, imdb='', tmdb='', tvdb=''):
    body = {}
    if tmdb and str(tmdb).isdigit() and int(tmdb) > 0:
        body['tmdb_id'] = int(tmdb)
    elif imdb and str(imdb).startswith('tt'):
        body['imdb_id'] = imdb
    elif tvdb and str(tvdb).isdigit() and int(tvdb) > 0:
        body['tvdb_id'] = int(tvdb)
    else:
        raise PunchPlayError('No valid media identifier is available.')
    return body


def _bulk(path, items, return_results=False):
    results = []
    for start in range(0, len(items), 100):
        data = _request('/sync/' + path, 'POST', {'items': items[start:start + 100]},
                        {'Idempotency-Key': str(uuid.uuid4())})
        invalid = [i for i in data.get('results', []) if i.get('status') == 'invalid']
        if data.get('invalid') or invalid:
            reasons = []
            for result in invalid:
                reason = result.get('error') or result.get('reason')
                if reason:
                    reason = ' '.join(str(reason).split())[:500]
                    if reason not in reasons:
                        reasons.append(reason)
            message = 'PunchPlay rejected the update: ' + '; '.join(reasons) if reasons else (
                'PunchPlay rejected the update without providing a reason.')
            log_utils.log(message, level=log_utils.LOGWARNING)
            raise PunchPlayError(message)
        if data.get('deferred') or any(i.get('status') == 'deferred' for i in data.get('results', [])):
            raise PunchPlayError('PunchPlay queued the update for resolution. It will appear after the server processes it.')
        results.extend(data.get('results', []))
    return results if return_results else True


def _movie_history_write(imdb, tmdb, remove):
    # Serialize with full sync so an older downloaded snapshot cannot overwrite
    # this confirmed single-movie change. Do not download the account again here.
    with _sync_lock, _account_sync_lock():
        generation = _tokens().get('generation')
        metadata = _title('movie', tmdb, imdb)['title']
        source = metadata.get('tmdbId') or tmdb
        title, year = metadata.get('name'), metadata.get('year')
        if not title or not str(year).isdigit() or not 1888 <= int(year) <= 2100:
            raise PunchPlayError('Unable to read the title and release year required by PunchPlay history.')
        source = _title_id(source)
        stamp = _watch_time()
        if remove:
            _request('/title/movie/%s/history' % source, 'DELETE')
        else:
            _bulk('history', [dict(_identity('movie', tmdb=source), kind='movie', title=title,
                                  year=int(year), watched_at=stamp,
                                  client_item_id='umbrella:manual:' + str(uuid.uuid4()))])
        movie_imdb = imdb if imdb and str(imdb).startswith('tt') else _resolve_movie_imdb(source)
        con = _connection()
        try:
            con.execute('BEGIN IMMEDIATE')
            row = con.execute("SELECT value FROM punchplay_state WHERE key='tokens'").fetchone()
            if not row or json.loads(row[0]).get('generation') != generation:
                raise PunchPlayError('PunchPlay account changed; local update cancelled.')
            punchplaysync._ensure_watched_tables(con.cursor())
            if remove:
                con.execute('DELETE FROM punchplay_watched_movies WHERE tmdb=?', (source,))
            else:
                con.execute('INSERT OR REPLACE INTO punchplay_watched_movies VALUES (?,?,?,?,?)',
                            (movie_imdb, source, title, str(year), stamp))
            con.execute('CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting))')
            con.execute('INSERT OR REPLACE INTO service VALUES (?,?)', ('last_history_at', _now_iso()))
            if con.execute("SELECT 1 FROM sqlite_master WHERE name='watched'").fetchone():
                con.execute('DELETE FROM watched')
            con.commit()
        finally:
            con.close()
    return True


def _history_write(kind, imdb='', tmdb='', tvdb='', season=None, episode=None, remove=False):
    if kind == 'movie':
        return _movie_history_write(imdb, tmdb, remove)
    started = time.monotonic()
    with _sync_lock:
        acquired = time.monotonic()
        result = _episode_history_write(kind, imdb, tmdb, tvdb, season, episode, remove)
        log_utils.log('PunchPlay episode %s: sync lock %.2fs, remote/local update %.2fs' %
                      ('unwatch' if remove else 'watch', acquired - started, time.monotonic() - acquired),
                      level=log_utils.LOGINFO)
        return result


def _episode_history_write(kind, imdb, tmdb, tvdb, season, episode, remove):
    generation = _tokens().get('generation')
    if remove:
        source = _title_id(tmdb, imdb, tvdb)
        if kind == 'movie':
            _request('/title/movie/%s/history' % source, 'DELETE')
        else:
            # Delete only this episode's entries, including rewatches.
            rows = _state('episode_history')
            if rows is None:
                rows = _pages('/me/history?limit=100')
            canonical = str((_title('show', tmdb, imdb, tvdb).get('title') or {}).get('tmdbId') or '')
            source = canonical
            for row in rows:
                if str(row.get('showTmdbId')) == canonical and row.get('season') == int(season) and row.get('episode') == int(episode):
                    _request('/watch-history/%s' % row['id'], 'DELETE')
    else:
        # The live bulk-history validator requires title/year even though the
        # published OpenAPI contract marks them optional. Episodes use show metadata.
        metadata = _title('movie' if kind == 'movie' else 'show', tmdb, imdb, tvdb)['title']
        title, year = metadata.get('name'), metadata.get('year')
        if not title or not str(year).isdigit() or not 1888 <= int(year) <= 2100:
            raise PunchPlayError('Unable to read the title and release year required by PunchPlay history.')
        source = metadata.get('tmdbId') or tmdb
        item = dict(_identity(kind, imdb, source, tvdb), kind=kind, watched_at=_watch_time(),
                    title=title, year=int(year),
                    client_item_id='umbrella:manual:' + str(uuid.uuid4()))
        if kind == 'episode':
            item.update(season=int(season), episode=int(episode))
        results = _bulk('history', [item], return_results=True)
    _update_episode_cache(imdb, source, tvdb, int(season),
                          [] if remove else [int(episode)], remove, int(episode), generation)
    # IDs are needed for every rewatch deletion; persist them rather than paging
    # through the complete account again for the next episode.
    if remove:
        con = _connection()
        try:
            _put(con, 'episode_history', [r for r in rows if not (
                str(r.get('showTmdbId')) == str(source) and r.get('season') == int(season)
                and r.get('episode') == int(episode))])
            con.commit()
        finally:
            con.close()
    else:
        con = _connection()
        try:
            row = con.execute("SELECT value FROM punchplay_state WHERE key='episode_history'").fetchone()
            if row and isinstance(results, list) and results and results[0].get('id'):
                rows = json.loads(row[0])
                history_id = results[0]['id']
                rows = [r for r in rows if r.get('id') != history_id]
                rows.append({'id': history_id, 'type': 'episode', 'showTmdbId': int(source),
                             'season': int(season), 'episode': int(episode)})
                _put(con, 'episode_history', rows)
            elif not isinstance(results, list) or not results or results[0].get('status') != 'skipped':
                con.execute("DELETE FROM punchplay_state WHERE key='episode_history'")
            con.commit()
        finally:
            con.close()
    return True


def _update_episode_cache(imdb, source, tvdb, season, episodes, remove=False, episode=None, generation=None):
    """Publish only the episodes confirmed by the manual API operation."""
    show_imdb = imdb if imdb and str(imdb).startswith('tt') else _resolve_tv_imdb(source)
    con = _connection()
    try:
        con.execute('BEGIN IMMEDIATE')
        token = con.execute("SELECT value FROM punchplay_state WHERE key='tokens'").fetchone()
        if not token or json.loads(token[0]).get('generation') != generation:
            raise PunchPlayError('PunchPlay account changed; local update cancelled.')
        punchplaysync._ensure_watched_tables(con.cursor())
        if remove:
            query = 'DELETE FROM punchplay_watched_episodes WHERE show_tmdb=? AND season=?'
            args = (str(source), season)
            if episode is not None:
                query += ' AND episode=?'
                args += (episode,)
            con.execute(query, args)
        else:
            con.executemany('INSERT OR REPLACE INTO punchplay_watched_episodes VALUES (?,?,?,?,?,?)',
                            [(show_imdb, str(source), tvdb or '', season, ep, _now_iso()) for ep in episodes])
        con.execute('CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting))')
        con.execute('INSERT OR REPLACE INTO service VALUES (?,?)', ('last_history_at', _now_iso()))
        _put(con, 'manual_history_revision', str(uuid.uuid4()))
        if con.execute("SELECT 1 FROM sqlite_master WHERE name='watched'").fetchone():
            con.execute('DELETE FROM watched')
        con.commit()
    finally:
        con.close()


def markMovieAsWatched(imdb, tmdb=''):
    return _history_write('movie', imdb, tmdb)


def markMovieAsNotWatched(imdb, tmdb=''):
    return _history_write('movie', imdb, tmdb, remove=True)


def markEpisodeAsWatched(imdb, tvdb, season, episode, tmdb=''):
    return _history_write('episode', imdb, tmdb, tvdb, season, episode)


def markEpisodeAsNotWatched(imdb, tvdb, season, episode, tmdb=''):
    return _history_write('episode', imdb, tmdb, tvdb, season, episode, remove=True)


def _season_watch(imdb, tvdb, season=None, remove=False, tmdb=None):
    with _sync_lock, _account_sync_lock():
        return _season_history_write(imdb, tvdb, season, remove, tmdb)


def _season_history_write(imdb, tvdb, season, remove, tmdb):
    generation = _tokens().get('generation')
    detail = _title('show', tmdb=tmdb, imdb=imdb, tvdb=tvdb)
    title = detail['title']
    source = str(title['tmdbId'])
    if season is None:
        # TMDB supplies season numbers; never assume all seasons are contiguous.
        from resources.lib.database import cache
        from resources.lib.indexers import tmdb
        meta = cache.get(tmdb.TVshows().get_showSeasons_meta, 96, source) or {}
        seasons = [s['season_number'] for s in meta.get('seasons', [])
                   if s['season_number'] != 0 or getSetting('tv.specials') == 'true']
        if not seasons:
            raise PunchPlayError('Unable to read show seasons.')
    else:
        seasons = [int(season)]
    today = datetime.utcnow().strftime('%Y-%m-%d')
    for sn in seasons:
        path = '/title/show/%s/season/%s/watch' % (source, sn)
        if remove:
            _request(path, 'DELETE')
            _update_episode_cache(imdb, source, tvdb, sn, [], True, generation=generation)
            continue
        metadata = _request('/title/show/%s/season/%s' % (source, sn))
        episodes = [{'episodeNumber': e['episodeNumber'], 'name': e['name'],
                     'airDate': e.get('airDate') or '', 'runtime': e.get('runtime') or 0}
                    for e in metadata['episodes'] if e.get('airDate') and e['airDate'][:10] <= today]
        if episodes:
            _request(path, 'POST', {'episodes': episodes, 'title': title['name'], 'year': title['year'],
                                   'watchedAt': _watch_time(), 'allowRewatches': False})
            _update_episode_cache(imdb, source, tvdb, sn, [e['episodeNumber'] for e in episodes], generation=generation)
    con = _connection()
    try:
        con.execute("DELETE FROM punchplay_state WHERE key='episode_history'")
        con.commit()
    finally:
        con.close()
    return True


def markTVShowAsWatched(imdb, tvdb):
    return _season_watch(imdb, tvdb)


def markTVShowAsNotWatched(imdb, tvdb):
    return _season_watch(imdb, tvdb, remove=True)


def markSeasonAsWatched(imdb, tvdb, season):
    return _season_watch(imdb, tvdb, season)


def markSeasonAsNotWatched(imdb, tvdb, season):
    return _season_watch(imdb, tvdb, season, remove=True)


def watch(content_type, name, imdb=None, tvdb=None, season=None, episode=None, refresh=True):
    return _watch(content_type, name, imdb, tvdb, season, episode, refresh, False)


def unwatch(content_type, name, imdb=None, tvdb=None, season=None, episode=None, refresh=True):
    return _watch(content_type, name, imdb, tvdb, season, episode, refresh, True)


def _watch(content_type, name, imdb, tvdb, season, episode, refresh, remove, tmdb=None):
    try:
        if content_type == 'movie':
            _history_write('movie', imdb=imdb, tmdb=tmdb, remove=remove)
        elif content_type == 'episode':
            _history_write('episode', imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, remove=remove)
        else:
            _season_watch(imdb, tvdb, season if content_type == 'season' else None, remove, tmdb)
        is_widget = 'plugin' not in control.infoLabel('Container.PluginName')
        control.trigger_widget_refresh(update_library=is_widget, force=True)
        if refresh and not is_widget:
            control.refresh()
        _notify('%s marked as %s on PunchPlay' % (name, 'unwatched' if remove else 'watched'))
        return True
    except (PunchPlayError, ValueError, TypeError) as exc:
        _notify('%s: failed to mark %s on PunchPlay: %s' % (name, 'unwatched' if remove else 'watched', exc))
        return False


def _key(tmdb, imdb, tvdb, season, episode):
    return (str(tmdb or imdb or tvdb), str(season), str(episode))


def _playback(action, media_type, imdb='', tmdb='', tvdb='', title='', year='0',
              season=None, episode=None, watched_percent=0, current_time=0, total_time=0,
              completed=False, already_watched=False):
    try:
        kind = 'movie' if media_type == 'movie' else 'episode'
        key = _key(tmdb, imdb, tvdb, season, episode)
        with _playback_lock:
            state = _sessions.get(key)
            if state and state.get('closed') and action != 'start':
                return True
            if action in ('progress', 'pause', 'resume') and not state:
                return False
            if not state or action == 'start':
                if not title:
                    meta = _title('movie' if kind == 'movie' else 'show', tmdb, imdb, tvdb)['title']
                    title, year = meta['name'], meta['year']
                state = {'session': str(uuid.uuid4()), 'title': title, 'year': year, 'last_ms': 0}
                _sessions[key] = state
            stamp = max(int(time.time() * 1000), state['last_ms'] + 1)
            state['last_ms'] = stamp
            payload = dict(_identity(kind, imdb, tmdb, tvdb), media_type=kind,
                           title=state['title'], playback_session_id=state['session'],
                           event_id=str(uuid.uuid4()), event_created_at=stamp,
                           progress=max(0, min(float(watched_percent) / 100, 1)),
                           position_seconds=max(float(current_time or 0), 0),
                           duration_seconds=max(float(total_time or 0), 0),
                           watched_threshold=float(getSetting('markwatched.percent') or 85) / 100,
                           device_id=_device_id(), client_version=control.addonInfo('version'))
            if str(state['year']).isdigit() and 1888 <= int(state['year']) <= 2100:
                payload['year'] = int(state['year'])
            if kind == 'episode':
                payload.update(season=int(season), episode=int(episode))
            if action == 'stop':
                payload['watched'] = bool(completed)
            _request('/playback/' + action, 'POST', payload)
            if action == 'stop':
                state['closed'] = True
                if completed:
                    punchplaysync.delete_bookmark(imdb or '', tmdb=str(tmdb or ''), tvdb=str(tvdb or ''),
                                                 season='' if season is None else str(season),
                                                 episode='' if episode is None else str(episode))
                else:
                    punchplaysync.upsert_bookmark(
                        tvshowtitle=state['title'] if kind == 'episode' else '', title=state['title'],
                        imdb=imdb, tmdb=str(tmdb or ''), tvdb=str(tvdb or ''),
                        season='' if season is None else str(season),
                        episode='' if episode is None else str(episode),
                        duration=str(total_time or ''), percent_played=str(watched_percent), paused_at=_now_iso())
        return True
    except (PunchPlayError, ValueError, TypeError) as exc:
        log_utils.log('PunchPlay playback failed: %s' % exc, level=log_utils.LOGWARNING)
        return False


def _device_id():
    value = getSetting('punchplay.deviceid')
    if not value:
        value = 'umbrella-' + str(uuid.uuid4())
        setSetting('punchplay.deviceid', value)
    return value


def scrobbleStart(media_type, title='', tvshowtitle='', year='0', imdb='', tmdb='', tvdb='',
                  season=None, episode=None, watched_percent=0, current_time=0, total_time=0, resumed=False):
    action = 'resume' if resumed else 'start'
    return _playback(action, media_type, imdb, tmdb, tvdb, tvshowtitle or title, year,
                     season, episode, watched_percent, current_time, total_time)


def scrobbleMovie(imdb, tmdb, watched_percent, current_time=0, total_time=0):
    return _playback('pause', 'movie', imdb, tmdb, watched_percent=watched_percent,
                     current_time=current_time, total_time=total_time)


def scrobbleEpisode(imdb, tmdb, tvdb, season, episode, watched_percent, current_time=0, total_time=0):
    return _playback('pause', 'episode', imdb, tmdb, tvdb, season=season, episode=episode,
                     watched_percent=watched_percent, current_time=current_time, total_time=total_time)


def scrobbleProgress(media_type, imdb='', tmdb='', tvdb='', season=None, episode=None,
                     watched_percent=0, current_time=0, total_time=0):
    return _playback('progress', media_type, imdb, tmdb, tvdb, season=season, episode=episode,
                     watched_percent=watched_percent, current_time=current_time, total_time=total_time)


def markMovieDuringPlayback(imdb, watched):
    """Update indicators immediately; the completed stop owns the remote history write."""
    tmdb = _resolve_tmdb('movie', imdb)
    if tmdb:
        if int(watched) == 5:
            punchplaysync.upsert_watched_movie(imdb, tmdb, last_watched_at=_now_iso())
        else:
            punchplaysync.delete_watched_movie(tmdb)
        punchplaysync.clear_cache()


def markEpisodeDuringPlayback(imdb, tvdb, season, episode, watched):
    tmdb = _resolve_tmdb('show', imdb, tvdb)
    if tmdb:
        if int(watched) == 5:
            punchplaysync.upsert_watched_episode(imdb, tmdb, tvdb, int(season), int(episode), _now_iso())
        else:
            punchplaysync.delete_watched_episode(tmdb, int(season), int(episode))
        punchplaysync.clear_cache()


def scrobbleStopMovie(imdb, tmdb, watched_percent, completed=False, current_time=0, total_time=0, already_watched=False):
    return _playback('stop', 'movie', imdb, tmdb, watched_percent=watched_percent, completed=completed,
                     current_time=current_time, total_time=total_time, already_watched=already_watched)


def scrobbleStopEpisode(imdb, tmdb, tvdb, season, episode, watched_percent, completed=False,
                        current_time=0, total_time=0, already_watched=False):
    return _playback('stop', 'episode', imdb, tmdb, tvdb, season=season, episode=episode,
                     watched_percent=watched_percent, completed=completed, current_time=current_time,
                     total_time=total_time, already_watched=already_watched)


def get_continue_watching():
    """Adapt exact resume items to Umbrella's existing unfinished-item renderer."""
    return [_resume_item(i) for i in _pages('/playback/in-progress')]


def _resume_item(i):
    kind = i['type']
    return {'id': i['id'], 'watched_at': i['updatedAt'], 'position_seconds': i['progressSeconds'],
            'duration_seconds': i.get('durationSeconds'), 'progress_percent': float(i['progressPercent']) / 100,
            'media': {'type': kind, 'tmdb_id': i['tmdbId'], 'title': i.get('episodeTitle') or i['title'],
                      'show_tmdb_id': i.get('showTmdbId'), 'show_title': i.get('showTitle'),
                      'season_number': i.get('season'), 'episode_number': i.get('episode')}}


def get_resume_item(tmdb, season=None, episode=None):
    for item in get_continue_watching():
        media = item['media']
        if season is not None and episode is not None:
            if media['type'] == 'episode' and str(media['show_tmdb_id']) == str(tmdb) and media['season_number'] == int(season) and media['episode_number'] == int(episode):
                return item
        elif media['type'] == 'movie' and str(media['tmdb_id']) == str(tmdb):
            return item
    return None


def get_resume_percent(tmdb, season=None, episode=None):
    item = get_resume_item(tmdb, season, episode)
    return item['progress_percent'] * 100 if item else 0


def _resetPlaybackProgress(imdb, tmdb=None, tvdb=None, season=None, episode=None, refresh=True,
                  widgetRefresh=False, clear_local=True):
    tmdb = tmdb or _resolve_tmdb('movie' if season is None else 'show', imdb, tvdb)
    item = get_resume_item(tmdb, season, episode)
    if item:
        _request('/playback/in-progress/%s' % item['id'], 'DELETE')
    if clear_local:
        punchplaysync.delete_bookmark(imdb or '', tvdb=tvdb or '', tmdb=str(tmdb or ''),
                                     season='' if season is None else str(season),
                                     episode='' if episode is None else str(episode))
    if refresh:
        control.refresh()
    if widgetRefresh:
        control.trigger_widget_refresh()
    return True

def scrobbleReset(imdb, tmdb=None, tvdb=None, season=None, episode=None, refresh=True,
                  widgetRefresh=False, clear_local=True):
    try:
        if not getPunchPlayCredentialsInfo(): raise PunchPlayError('Please authorize PunchPlay.')
        if not tmdb: tmdb = _resolve_tmdb('movie' if season is None else 'show', imdb, tvdb)
        if not tmdb: raise PunchPlayError('Unable to identify title.')
        result = _resetPlaybackProgress(imdb, tmdb, tvdb, season, episode, False, False, clear_local)
        if refresh or widgetRefresh: finishProgressRemoval(1, 1)
        return result
    except Exception:
        log_utils.error()
        if refresh or widgetRefresh: finishProgressRemoval(0, 1)
        return False


def finishProgressRemoval(succeeded, total):
	failed = total - succeeded
	message = 'Removed playback progress for %s item(s).' % succeeded
	if failed: message += ' Failed to remove %s item(s); check the log and PunchPlay authorization.' % failed
	control.notification(title='PunchPlay', message=message)
	if succeeded:
		control.trigger_widget_refresh(force=True)
		if 'plugin.video.umbrella' in control.infoLabel('Container.PluginName'): control.refresh()



def get_next_up(upcoming=False):
    items = _pages('/me/continue-watching')
    results = []
    for i in items:
        nxt = i.get('nextEpisodeToAir') if upcoming else None
        sn = nxt.get('season') if nxt else i.get('nextSeason')
        ep = nxt.get('episode') if nxt else i.get('nextEpisode')
        if sn is None or ep is None or i.get('status') == 'DROPPED':
            continue
        results.append({'show': {'tmdb_id': i['showTmdbId']},
                        'next_episode': {'season_number': sn, 'episode_number': ep},
                        'last_watched_at': i.get('lastWatchedAt') or ''})
    return results


def get_lists():
    return _pages('/me/lists?limit=100')


def get_list_items(list_id):
    data = _request('/lists/%s' % int(list_id))
    if data.get('isDynamicList'):
        return _pages('/lists/%s/items?limit=100' % int(list_id))
    return data['items']


def _list_writable(lst):
    return not lst.get('externalSource') and not lst.get('isDynamicList')


def create_list(name):
    return _request('/lists', 'POST', {'name': name, 'isPublic': False})['id']


def add_to_list(list_id, tmdb, media_type, title):
    detail = _request('/lists/%s' % int(list_id))
    if not _list_writable(detail) or not (detail.get('isOwner') or detail.get('isCollaborator')):
        raise PunchPlayError('This list is read-only.')
    _request('/lists/%s/items' % int(list_id), 'POST',
             {'kind': 'movie' if media_type == 'movie' else 'show', 'sourceId': int(tmdb), 'title': title})
    return True


def remove_from_list(list_id, item_id):
    detail = _request('/lists/%s' % int(list_id))
    if not _list_writable(detail) or not (detail.get('isOwner') or detail.get('isCollaborator')):
        raise PunchPlayError('This list is read-only.')
    _request('/lists/%s/items/%s' % (int(list_id), int(item_id)), 'DELETE')
    return True


def _watchlist(tmdb, kind, remove=False):
    metadata = _title(kind, tmdb=tmdb)['title']
    return _bulk('watchlist', [{'kind': kind, 'tmdb_id': int(metadata.get('tmdbId') or tmdb),
                              'title': metadata['name'], 'remove': remove,
                              'client_item_id': 'umbrella:watchlist:' + str(uuid.uuid4())}])


def _refresh_watchlist_cache():
    return _refresh_list_cache()


def _refresh_list_cache(list_id=None):
    with _sync_lock, _account_sync_lock():
        generation = _tokens().get('generation')
        watchlist = (_request('/lists/%s' % int(list_id)) if list_id is not None else
                     next((i for i in get_lists() if i.get('isWatchlist')), None))
        if watchlist is None:
            raise PunchPlayError('PunchPlay did not return a Watchlist.')
        items = get_list_items(watchlist['id'])
        rows = [(str(watchlist['id']), watchlist['name'], str(i['id']), str(i['tmdbId']),
                 i['title'], (i.get('releaseDate') or '')[:4],
                 'movie' if i['type'] == 'movie' else 'series', i.get('addedAt') or '')
                for i in items if i['type'] in ('movie', 'show')]
        con = _connection()
        try:
            con.execute('BEGIN IMMEDIATE')
            row = con.execute("SELECT value FROM punchplay_state WHERE key='tokens'").fetchone()
            if not row or json.loads(row[0]).get('generation') != generation:
                raise PunchPlayError('PunchPlay account changed; Watchlist refresh cancelled.')
            con.execute('CREATE TABLE IF NOT EXISTS punchplay_lists (list_id TEXT, list_name TEXT, item_id TEXT, tmdb TEXT, title TEXT, year TEXT, media_type TEXT, listed_at TEXT, UNIQUE(list_id,item_id))')
            con.execute('DELETE FROM punchplay_lists WHERE list_id=?', (str(watchlist['id']),))
            con.executemany('INSERT OR REPLACE INTO punchplay_lists VALUES (?,?,?,?,?,?,?,?)', rows)
            con.commit()
        finally:
            con.close()


def _finish_list_action(list_id, refresh):
    try:
        _refresh_list_cache(list_id)
    except (PunchPlayError, ValueError, TypeError, KeyError) as exc:
        _notify('List saved on PunchPlay, but the local list refresh failed: %s' % exc)
        return
    is_widget = 'plugin' not in control.infoLabel('Container.PluginName')
    control.trigger_widget_refresh(update_library=is_widget, force=True)
    if refresh and not is_widget:
        control.refresh()


def _normal_item(i):
    return {'tmdb': str(i.get('tmdbId') or ''), 'title': i.get('title') or '',
            'year': str(i.get('year') or (i.get('releaseDate') or '')[:4]),
            'imdb': '', 'tvdb': '', 'premiered': (i.get('releaseDate') or '')[:10],
            'added': i.get('addedAt') or i.get('updatedAt') or '', 'entry_id': i.get('id')}


def get_collection_entries(media_type='movie'):
    kind = 'movie' if media_type == 'movie' else 'show'
    return [_normal_item(i) for i in _pages('/me/collection?limit=200') if i.get('kind') == kind]


def remove_from_collection(entry_id):
    _request('/collection/%s' % int(entry_id), 'DELETE')
    return True


def get_dropped(media_type=None):
    kind = None if media_type is None else 'movie' if media_type == 'movies' else 'show'
    return [_normal_item(i) for i in _pages('/me/watch-status')
            if i.get('showStatus') == 'DROPPED' and i.get('scope') in (None, 'title') and (kind is None or i.get('kind') == kind)]


def get_library_items(category, kind):
    if category == 'collection':
        rows = _state('collection', [])
        # Editions share a title; the browser presents each title once.
        rows = [i for i in rows if i.get('kind') == kind]
        return list({str(i['tmdbId']): _normal_item(i) for i in rows}.values())
    statuses = {'planning': 'PLANNING', 'watching': 'WATCHING', 'hold': 'ON_HOLD', 'dropped': 'DROPPED'}
    if category in statuses:
        return [_normal_item(i) for i in _state('statuses', [])
                if i.get('kind') == kind and i.get('showStatus') == statuses[category]
                and i.get('scope', 'title') in ('title', 'series')]
    if category == 'favourites':
        return [_normal_item(i) for i in _pages('/me/favourites') if i.get('kind') == kind]
    raise PunchPlayError('Unknown library category')


def get_calendar(month):
    try:
        month = datetime.strptime(month, '%Y-%m').strftime('%Y-%m')
    except (TypeError, ValueError):
        raise PunchPlayError('Invalid calendar month.')
    return _request('/calendar?' + urlencode({'month': month}))


def get_catalog(media_type='movie', category='popular'):
    if media_type not in ('movie', 'show', 'anime') or category not in (
            'trending', 'popular', 'top_rated', 'now_playing', 'upcoming'):
        raise PunchPlayError('Unknown catalog category.')
    query = {'type': media_type}
    path = '/catalog/trending' if category == 'trending' else '/catalog/discover'
    if category != 'trending':
        query['category'] = category
    # The public contract returns a complete items array, without pagination.
    data = _request(path + '?' + urlencode(query), public=True)
    if not isinstance(data, dict) or not isinstance(data.get('items'), list):
        raise PunchPlayError('Unexpected PunchPlay catalog response.')
    return data['items']


def get_calendar_items(month, media_type):
    if media_type not in ('movie', 'episode'):
        raise PunchPlayError('Unknown calendar media type.')
    data = get_calendar(month)
    if not isinstance(data, dict) or not isinstance(data.get('days'), list):
        raise PunchPlayError('Unexpected PunchPlay calendar response.')
    items = []
    for day in data['days']:
        for item in day['items']:
            kind = item.get('kind')
            if (media_type == 'movie' and kind in ('movie', 'movie-digital') or
                    media_type == 'episode' and kind == 'episode'):
                values = dict(item)
                values['date'] = day['date']
                items.append(values)
    return sorted(items, key=lambda i: (i['date'], i.get('title', '').casefold()))


def get_export_lists():
    """Stable sources consumed by the existing library import scheduler."""
    lists = get_lists()  # Propagate failures; never replace saved choices with an empty result.
    sources = [('watchlist', 'Watchlist', 0), ('favourites', 'Favourites', 0),
               ('collection', 'Collection', 0)]
    sources += [('lists/%s' % int(i['id']), i['name'], i.get('itemCount', 0))
                for i in sorted(lists, key=lambda i: i['name'].casefold()) if not i.get('isWatchlist')]
    return [{'name': name, 'list_name': name, 'url': 'punchplay://' + source,
             'list_id': 'punchplay_' + source.replace('/', '_'), 'list_count': count,
             'action': 'mixed', 'list_owner': '', 'list_owner_slug': '', 'likes': 0, 'selected': ''}
            for source, name, count in sources]


def get_export_items(url, media_type=None):
    """Read every page fresh; deduplicate collection editions by routable kind and TMDB ID."""
    if not url.startswith('punchplay://'):
        raise PunchPlayError('Invalid PunchPlay library source.')
    source = url[len('punchplay://'):]
    if source == 'watchlist':
        watchlist = next((i for i in get_lists() if i.get('isWatchlist')), None)
        if watchlist is None:
            raise PunchPlayError('PunchPlay did not return a Watchlist.')
        rows = get_list_items(watchlist['id'])
    elif source in ('favourites', 'collection'):
        rows = _pages('/me/%s?limit=100' % source)
    elif source.startswith('lists/') and source[6:].isdigit():
        rows = get_list_items(int(source[6:]))
    else:
        raise PunchPlayError('Unknown PunchPlay library source.')
    items, seen = [], set()
    for row in rows:
        kind = row.get('kind') or row.get('type')
        if kind not in ('movie', 'show') or media_type and kind != media_type:
            continue
        tmdb = str(row.get('tmdbId') or '')
        key = (kind, tmdb)
        if not tmdb.isdigit() or int(tmdb) <= 0 or key in seen:
            continue
        seen.add(key)
        item = _normal_item(row)
        # Lists may omit the release year. Resolve it before writing library filenames.
        if not item['title'] or not item['year']:
            title = _title(kind, tmdb=tmdb)['title']
            item['title'] = item['title'] or title['name']
            item['year'] = item['year'] or str(title.get('year') or (title.get('releaseDate') or '')[:4])
        if not item['title'] or not item['year'].isdigit():
            raise PunchPlayError('Missing title or release year for library export (%s %s).' % key)
        item['imdb'] = _resolve_movie_imdb(tmdb) if kind == 'movie' else _resolve_tv_imdb(tmdb)
        item['mediatype'] = 'movies' if kind == 'movie' else 'tvshows'
        item['originaltitle'] = item['title']
        if kind == 'show':
            item['tvshowtitle'] = item['title']
        items.append(item)
    return items


def remove_dropped_items(tmdb_ids, media_type):
    kind = 'movie' if media_type == 'movies' else 'show'
    for tmdb in tmdb_ids:
        _request('/title/%s/%s/interact' % (kind, _title_id(tmdb)), 'PATCH', {'showStatus': None})
    sync_account(forced=True)
    return True


def sync_account(forced=False, progress_callback=None, refresh_widgets=True):
    """Use the durable change feed to invalidate complete presentation caches.

    Fetch all remote pages first, then publish history/lists/bookmarks and the cursor
    together. Failed reads never clear watched state or advance the sync cursor.
    """
    if not getPunchPlayCredentialsInfo():
        return False
    with _sync_lock, _account_sync_lock():
        generation = _tokens().get('generation')
        cursor = None if forced else _state('cursor')
        history_revision = _state('manual_history_revision')
        first = _request('/me/sync/changes' + ('?' + urlencode({'cursor': cursor}) if cursor else ''))
        dirty = set(first['resources']) if not cursor or first['resetRequired'] else set()
        page = first
        while True:
            dirty.update(c['resource'] for c in page['changes'])
            next_cursor = page['nextCursor']
            if not page['hasMore'] or page['resetRequired']:
                break
            if next_cursor == cursor:
                raise PunchPlayError('PunchPlay change cursor did not advance')
            cursor = next_cursor
            page = _request('/me/sync/changes?' + urlencode({'cursor': cursor}))
        movies = episodes = lists = raw_bookmarks = collection = statuses = None
        if 'history' in dirty:
            if progress_callback:
                progress_callback('Syncing PunchPlay history')
            history = _pages('/me/history?limit=100')
            movies, episodes = {}, {}
            movie_ids, show_ids = {}, {}
            for i in history:
                if i['type'] == 'movie':
                    tmdb = str(i['tmdbId'])
                    if tmdb not in movie_ids:
                        movie_ids[tmdb] = _resolve_movie_imdb(tmdb)
                    row = (movie_ids[tmdb], tmdb, i['title'], str(i['year']), i['watchedAt'])
                    if tmdb not in movies or row[-1] > movies[tmdb][-1]:
                        movies[tmdb] = row
                else:
                    tmdb = str(i['showTmdbId'] or '')
                    if not tmdb or i['season'] is None or i['episode'] is None:
                        continue
                    if tmdb not in show_ids:
                        show_ids[tmdb] = _resolve_tv_imdb(tmdb)
                    key = (tmdb, i['season'], i['episode'])
                    row = (show_ids[tmdb], tmdb, '', int(i['season']), int(i['episode']), i['watchedAt'])
                    if key not in episodes or row[-1] > episodes[key][-1]:
                        episodes[key] = row
        if {'list', 'list_item'} & dirty:
            if progress_callback:
                progress_callback('Syncing PunchPlay lists')
            lists = []
            for lst in get_lists():
                for i in get_list_items(lst['id']):
                    kind = i['type']
                    if kind not in ('movie', 'show'):
                        continue
                    lists.append((str(lst['id']), lst['name'], str(i['id']), str(i['tmdbId']),
                                  i['title'], (i.get('releaseDate') or '')[:4],
                                  'movie' if kind == 'movie' else 'series', i.get('addedAt') or ''))
        if 'playback' in dirty or 'history' in dirty:
            raw_bookmarks = _pages('/playback/in-progress')
        if 'collection' in dirty:
            collection = _pages('/me/collection?limit=200')
        if 'interaction' in dirty:
            statuses = _pages('/me/watch-status')
        con = _connection()
        try:
            con.execute('BEGIN IMMEDIATE')
            row = con.execute("SELECT value FROM punchplay_state WHERE key='tokens'").fetchone()
            if not row or json.loads(row[0]).get('generation') != generation:
                raise PunchPlayError('PunchPlay account changed; sync cancelled.')
            punchplaysync._ensure_watched_tables(con.cursor())
            revision_row = con.execute("SELECT value FROM punchplay_state WHERE key='manual_history_revision'").fetchone()
            current_revision = json.loads(revision_row[0]) if revision_row else None
            if movies is not None and current_revision == history_revision:
                _put(con, 'episode_history', [i for i in history if i.get('type') == 'episode'])
                con.execute('DELETE FROM punchplay_watched_movies')
                con.executemany('INSERT OR REPLACE INTO punchplay_watched_movies VALUES (?,?,?,?,?)', movies.values())
                con.execute('DELETE FROM punchplay_watched_episodes')
                con.executemany('INSERT OR REPLACE INTO punchplay_watched_episodes VALUES (?,?,?,?,?,?)', episodes.values())
            if lists is not None:
                con.execute('CREATE TABLE IF NOT EXISTS punchplay_lists (list_id TEXT, list_name TEXT, item_id TEXT, tmdb TEXT, title TEXT, year TEXT, media_type TEXT, listed_at TEXT, UNIQUE(list_id,item_id))')
                con.execute('DELETE FROM punchplay_lists')
                con.executemany('INSERT OR REPLACE INTO punchplay_lists VALUES (?,?,?,?,?,?,?,?)', lists)
            if raw_bookmarks is not None:
                _put(con, 'resume', raw_bookmarks)
                punchplaysync._ensure_bookmarks_table(con.cursor())
                con.execute('DELETE FROM bookmarks')
                for i in raw_bookmarks:
                    episode = i['type'] == 'episode'
                    con.execute('INSERT OR REPLACE INTO bookmarks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                                (i.get('showTitle') or i['title'] if episode else '', i['title'], str(i['id']), '',
                                 str(i.get('showTmdbId') or '') if episode else str(i['tmdbId']), '',
                                 str(i['season']) if episode else '', str(i['episode']) if episode else '',
                                 '', '', '', str(i.get('durationSeconds') or ''), str(i['progressPercent']), i['updatedAt']))
            if collection is not None:
                _put(con, 'collection', collection)
            if statuses is not None:
                _put(con, 'statuses', statuses)
            if current_revision == history_revision:
                _put(con, 'cursor', next_cursor)
            _put(con, 'last_sync', time.time())
            con.execute('CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting))')
            con.execute('INSERT OR REPLACE INTO service VALUES (?,?)', ('last_history_at', _now_iso()))
            if con.execute("SELECT 1 FROM sqlite_master WHERE name='watched'").fetchone():
                con.execute('DELETE FROM watched')
            con.commit()
        finally:
            con.close()
        if dirty and refresh_widgets:
            control.trigger_widget_refresh()
        return True


def sync_watchedProgress(activities=None, forced=False, progress_callback=None):
    return sync_account(forced, progress_callback)


sync_watched = sync_watchedProgress


def sync_user_lists(forced=False):
    return sync_account(forced)


def sync_playbackProgress(activities=None, forced=False):
    return sync_account(forced)


def force_punchplaySync():
    dialog = control.progressDialog
    dialog.create('Umbrella - PunchPlay', 'Syncing PunchPlay...')
    try:
        if sync_account(True, lambda phase, *args: dialog.update(0, phase)):
            _notify('PunchPlay sync complete')
    except PunchPlayError as exc:
        _notify('PunchPlay sync failed: %s' % exc)
    finally:
        dialog.close()


def manager(name, imdb=None, tvdb=None, tmdb=None, season=None, episode=None,
            refresh=True, watched=None, unfinished=False, tvshow=None):
    kind = 'show' if tvshow or season not in (None, '') or episode not in (None, '') or tvdb not in (None, '', 'None', '0') else 'movie'
    content = 'episode' if episode not in (None, '') else 'season' if season not in (None, '') else 'tvshow' if kind == 'show' else 'movie'
    actions = [('Mark watched', 'watch'), ('Mark unwatched', 'unwatch')]
    if content in ('movie', 'episode'):
        actions.append(('Clear resume progress', 'resume'))
    if content in ('movie', 'tvshow'):
        actions += [('Add to watchlist', 'watchlist_add'), ('Remove from watchlist', 'watchlist_remove'),
                    ('Add to list', 'list_add'), ('Remove from list', 'list_remove'),
                    ('Add to collection', 'collection_add'), ('Remove from collection', 'collection_remove'),
                    ('Set watch status', 'status'), ('Set rating', 'rating'),
                    ('Add to favourites', 'favourite_add'), ('Remove from favourites', 'favourite_remove')]
    control.hide()
    select = control.selectDialog([a[0] for a in actions], heading='Umbrella - PunchPlay')
    if select < 0:
        return
    action = actions[select][1]
    try:
        if action in ('watch', 'unwatch'):
            _watch(content, name, imdb, tvdb, season, episode, refresh, action == 'unwatch', tmdb)
            return
        source = tmdb or _resolve_tmdb(kind, imdb, tvdb)
        if action == 'resume':
            scrobbleReset(imdb, source, tvdb, season, episode, refresh=refresh, widgetRefresh=True)
            return
        elif action.startswith('watchlist_'):
            _watchlist(source, kind, action.endswith('remove'))
            _notify('%s %s PunchPlay Watchlist' % (name, 'removed from' if action.endswith('remove') else 'added to'))
            try:
                _refresh_watchlist_cache()
            except (PunchPlayError, ValueError, TypeError, KeyError) as exc:
                _notify('Watchlist saved on PunchPlay, but the local list refresh failed: %s' % exc)
                return
            is_widget = 'plugin' not in control.infoLabel('Container.PluginName')
            control.trigger_widget_refresh(update_library=is_widget, force=True)
            if refresh and not is_widget:
                control.refresh()
            return
        elif action == 'list_add':
            lists = [i for i in get_lists() if _list_writable(i)]
            idx = control.selectDialog(['Create new list'] + [i['name'] for i in lists], heading='PunchPlay lists')
            if idx < 0:
                return
            if idx == 0:
                keyboard = control.keyboard('', 'List name')
                keyboard.doModal()
                if not keyboard.isConfirmed() or not keyboard.getText().strip():
                    return
                list_id = create_list(keyboard.getText().strip())
            else:
                list_id = lists[idx - 1]['id']
            add_to_list(list_id, source, kind, name)
            _notify('%s added to PunchPlay list' % name)
            _finish_list_action(list_id, refresh)
            return
        elif action == 'list_remove':
            matches = []
            for lst in get_lists():
                if _list_writable(lst):
                    for item in get_list_items(lst['id']):
                        if str(item['tmdbId']) == str(source) and item['type'] == kind:
                            matches.append((lst['id'], lst['name'], item['id']))
            if not matches:
                _notify('No writable list contains this title.')
                return
            idx = control.selectDialog([i[1] for i in matches], heading='Remove from list')
            if idx < 0:
                return
            remove_from_list(matches[idx][0], matches[idx][2])
            _notify('%s removed from PunchPlay list' % name)
            _finish_list_action(matches[idx][0], refresh)
            return
        elif action == 'collection_add':
            formats = ['digital', '4k_bluray', 'bluray', 'hd_dvd', 'dvd']
            idx = control.selectDialog(['Digital', '4K Blu-ray', 'Blu-ray', 'HD DVD', 'DVD'], heading='Collection format')
            if idx < 0:
                return
            _request('/collection', 'POST', {'kind': kind, 'sourceId': int(source), 'title': name, 'format': formats[idx]})
        elif action == 'collection_remove':
            items = [i for i in _pages('/me/collection?limit=200') if str(i['tmdbId']) == str(source) and i['kind'] == kind]
            if not items:
                _notify('This title is not in your PunchPlay collection.')
                return
            idx = control.selectDialog(['%s (season %s)' % (i['format'], i['season']) for i in items], heading='Remove collection edition')
            if idx < 0:
                return
            remove_from_collection(items[idx]['id'])
        elif action in ('status', 'rating', 'favourite_add', 'favourite_remove'):
            if action == 'status':
                values = ['PLANNING', 'WATCHING', 'ON_HOLD', 'DROPPED', 'WATCHED', None]
                idx = control.selectDialog(['Planning', 'Watching', 'On hold', 'Dropped', 'Watched', 'Clear status'], heading='PunchPlay status')
                if idx < 0:
                    return
                body = {'showStatus': values[idx]}
            elif action == 'rating':
                idx = control.selectDialog(['Remove rating'] + [str(i) for i in range(1, 11)], heading='PunchPlay rating')
                if idx < 0:
                    return
                body = {'rating': idx or None}
            else:
                body = {'isFavourite': action == 'favourite_add'}
            _request('/title/%s/%s/interact' % (kind, _title_id(source)), 'PATCH', body)
            if action == 'rating':
                _notify('%s: %s on PunchPlay' % (name, 'rating removed' if body['rating'] is None
                                               else 'rated %s/10' % body['rating']))
                # Ratings have no local watched/list state to reconcile. Do not
                # hold confirmation behind a full account history/list download.
                return
        _notify('%s: %s completed on PunchPlay' % (name, actions[select][0]))
        try:
            # Refresh only the resource changed by this action, never account history/lists.
            if action.startswith('collection_'):
                _refresh_manager_resource('collection', '/me/collection?limit=200')
            elif action == 'status':
                _refresh_manager_resource('statuses', '/me/watch-status')
            elif action == 'resume':
                _refresh_manager_resource('resume', '/playback/in-progress')
        except (PunchPlayError, ValueError, TypeError, KeyError) as exc:
            _notify('Saved on PunchPlay, but the local refresh failed: %s' % exc)
        is_widget = 'plugin' not in control.infoLabel('Container.PluginName')
        control.trigger_widget_refresh(update_library=is_widget, force=True)
        if refresh and not is_widget:
            control.refresh()
    except (PunchPlayError, ValueError, TypeError) as exc:
        _notify('%s: %s failed on PunchPlay: %s' % (name, actions[select][0], exc))


def _refresh_manager_resource(key, path):
    with _sync_lock, _account_sync_lock():
        generation = _tokens().get('generation')
        rows = _pages(path)
        con = _connection()
        try:
            con.execute('BEGIN IMMEDIATE')
            token = con.execute("SELECT value FROM punchplay_state WHERE key='tokens'").fetchone()
            if not token or json.loads(token[0]).get('generation') != generation:
                raise PunchPlayError('PunchPlay account changed; local refresh cancelled.')
            _put(con, key, rows)
            con.commit()
        finally:
            con.close()


def syncMovies():
	try:
		if not getPunchPlayCredentialsInfo(): return None
		return punchplaysync.get_watched_movies() or []
	except:
		log_utils.error()
		return None

def watchedMovies():
	try:
		if not getPunchPlayCredentialsInfo(): return None
		return punchplaysync.get_watched_movies_full() or []
	except:
		log_utils.error()
		return None

def _make_episode_ranges(ep_nums_sorted):
	if not ep_nums_sorted: return []
	ranges = []
	start = end = ep_nums_sorted[0]
	for ep in ep_nums_sorted[1:]:
		if ep == end + 1: end = ep
		else:
			ranges.append((start, end))
			start = end = ep
	ranges.append((start, end))
	return ranges

def syncTVShows():
	try:
		if not getPunchPlayCredentialsInfo(): return None
		episodes = punchplaysync.get_watched_episodes()
		if not episodes: return []
		shows = {}
		for (show_imdb, show_tmdb, show_tvdb, season, episode) in episodes:
			if show_tmdb not in shows:
				shows[show_tmdb] = {'ids': {'imdb': show_imdb, 'tmdb': show_tmdb, 'tvdb': show_tvdb}, 'by_season': {}}
			s = int(season)
			shows[show_tmdb]['by_season'].setdefault(s, []).append(int(episode))
		indicators = []
		for v in shows.values():
			ep_ranges = {s: _make_episode_ranges(sorted(eps)) for s, eps in v['by_season'].items()}
			total = sum(e - s + 1 for ranges in ep_ranges.values() for s, e in ranges)
			indicators.append((v['ids'], total, ep_ranges))
		return indicators
	except:
		log_utils.error()
		return None

def getShowProgress(tmdb):
	try:
		if not tmdb: return None
		return punchplaysync.get(_fetchShowProgress, 15, tmdb)
	except:
		log_utils.error()
		return None

def _fetchShowProgress(tmdb):
	try:
		include_specials = getSetting('tv.specials') == 'true'
		episodes = punchplaysync.get_watched_episodes()
		show_eps = [(s, e) for (si, st, sv, s, e) in (episodes or []) if st == tmdb]
		from collections import defaultdict
		by_season = defaultdict(list)
		for (s, e) in show_eps:
			s = int(s)
			if s == 0 and not include_specials: continue
			by_season[s].append(int(e))
		from resources.lib.database import cache as _cache
		from resources.lib.indexers import tmdb as _tmdb
		season_counts = {}
		try:
			showSeasons = _cache.get(_tmdb.TVshows().get_showSeasons_meta, 96, tmdb)
			if showSeasons:
				status = (showSeasons.get('status') or '').lower()
				ended = status in ('ended', 'canceled', 'cancelled')
				last_ep = showSeasons.get('last_episode_to_air') or {}
				last_aired_sn = int(last_ep.get('season_number', 0)) if last_ep else 0
				last_aired_ep = int(last_ep.get('episode_number', 0)) if last_ep else 0
				for s in showSeasons.get('seasons', []):
					sn = s.get('season_number')
					if sn is None: continue
					if sn == 0 and not include_specials: continue
					ep_count = s.get('episode_count', 0)
					if ended or not last_aired_sn or sn < last_aired_sn:
						season_counts[sn] = ep_count
					elif sn == last_aired_sn:
						season_counts[sn] = last_aired_ep if last_aired_ep > 0 else ep_count
		except: pass
		if not season_counts and not by_season: return [[], {}]
		result_counts = {}
		fully_watched = []
		for s, watched_eps in by_season.items():
			total = season_counts.get(s, len(set(watched_eps)))
			watched = len(set(watched_eps))
			result_counts[s] = {'total': total, 'watched': watched, 'unwatched': max(total - watched, 0)}
			if watched >= total: fully_watched.append(s)
		for sn, total in season_counts.items():
			if sn not in result_counts:
				result_counts[sn] = {'total': total, 'watched': 0, 'unwatched': total}
		return [[str(s) for s in sorted(fully_watched)], result_counts]
	except:
		log_utils.error()
		return None

def syncSeasons(imdb, tvdb):
	try:
		if not getPunchPlayCredentialsInfo(): return None
		if not imdb and not tvdb: return None
		tmdb = _resolve_tmdb('tv', imdb=imdb, tvdb=tvdb)
		if not tmdb: return [[], {}]
		progress = getShowProgress(tmdb)
		return progress if progress else [[], {}]
	except:
		log_utils.error()
		return None

def getMoviesWatchedActivity():
	try: return punchplaysync.last_sync('last_history_at')
	except: log_utils.error()
	return 0

def getEpisodesWatchedActivity():
	try: return punchplaysync.last_sync('last_history_at')
	except: log_utils.error()
	return 0

def timeoutsyncMovies():
	return punchplaysync.timeout(syncMovies)

def timeoutsyncTVShows():
	return punchplaysync.timeout(syncTVShows)

def timeoutsyncSeasons(imdb, tvdb):
	try: return punchplaysync.timeout(syncSeasons, imdb, tvdb, returnNone=True)
	except: log_utils.error()

def cachesyncMovies(timeout=720):
	try: return punchplaysync.get(syncMovies, timeout)
	except: log_utils.error()

def cachesyncTVShows(timeout=720):
	try: return punchplaysync.get(syncTVShows, timeout)
	except: log_utils.error()

def cachesyncTV(imdb, tvdb):
	try:
		from threading import Thread as _Thread
		threads = [_Thread(target=cachesyncTVShows, args=(0,)), _Thread(target=cachesyncSeasons, args=(imdb, tvdb, 0))]
		[i.start() for i in threads]
		[i.join() for i in threads]
	except: log_utils.error()

def cachesyncSeasons(imdb, tvdb='', timeout=720):
	try:
		imdb = imdb or ''
		tvdb = tvdb or ''
		return punchplaysync.get(syncSeasons, timeout, imdb, tvdb)
	except: log_utils.error()

def seasonCount(imdb, tvdb):
	try:
		result = syncSeasons(imdb, tvdb)
		if result and len(result) > 1: return result[1]
		return {}
	except: log_utils.error()
