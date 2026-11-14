"""Floppy contract=2 pull client. No page is published before both feeds catch up."""
from copy import deepcopy
from hashlib import md5
from math import isfinite
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit, parse_qsl, urlencode, urlunsplit


class Unavailable(Exception):
    """The server predates the reliable contract; legacy snapshots are required."""


class Reset(Exception):
    pass


class Cancelled(ValueError):
    """Kodi is stopping or reloading its profile; discard the staged sync."""


def number(value):
    if type(value) is not int or value < 0:
        raise ValueError('Invalid Floppy sync position')
    return value


def project(mirror, resolve_movie, resolve_show, old_movies=()):
    """Convert absolute server assertions to Umbrella's native provider tables."""
    previous = {str(row[1]): row for row in old_movies}
    movies, episodes, bookmarks, watched = [], [], [], set()
    resolved = {}

    def identity(row):
        media = row.get('media_type')
        if media not in ('movie', 'episode') or row.get('source') not in ('tmdb', None, ''):
            return None
        ids = row.get('ids') or {}
        tmdb = str(ids.get('tmdb') or row.get('media_id') or '')
        if not tmdb.isdigit() or int(tmdb) <= 0: raise ValueError('Missing TMDB sync identity')
        season = episode = ''
        if media == 'episode':
            sn, en = row.get('season_number'), row.get('episode_number')
            if type(sn) is not int or sn < 0 or type(en) is not int or en < 1:
                raise ValueError('Invalid Floppy episode coordinates')
            season, episode = str(sn), str(en)
        return tmdb, season, episode

    for row in mirror['watched'].values():
        key = identity(row)
        if key is None or not row['watched']: continue
        tmdb, season, episode = key
        watched.add(key)
        ids = row.get('ids') or {}
        imdb = str(ids.get('imdb') or '')
        if not imdb:
            lookup = ('episode' if season else 'movie', tmdb)
            if lookup not in resolved:
                resolved[lookup] = (resolve_show if season else resolve_movie)(tmdb)
            imdb = resolved[lookup]
        if season:
            episodes.append((imdb, tmdb, str(ids.get('tvdb') or ''), int(season), int(episode), row.get('watched_at') or ''))
        else:
            old = previous.get(tmdb, ('', '', '', '', ''))
            movies.append((imdb or old[0], tmdb, row.get('title') or old[2], str(row.get('year') or old[3]), row.get('watched_at') or ''))
    for row in mirror['progress'].values():
        key = identity(row)
        if key is None or key in watched or row['completed']: continue
        duration, position = float(row.get('duration_seconds') or 0), float(row.get('position_seconds') or 0)
        if not isfinite(duration) or not isfinite(position): raise ValueError('Invalid Floppy resume time')
        if duration <= 0 or position <= 0 or position / duration >= .9: continue
        tmdb, season, episode = key
        ids = row.get('ids') or {}
        imdb, tvdb = str(ids.get('imdb') or ''), str(ids.get('tvdb') or '')
        resume_id = md5(repr((imdb, tmdb, tvdb, season, episode)).encode('utf-8')).hexdigest()
        bookmarks.append((row.get('series_title') or '', row.get('title') or '', resume_id,
                          imdb, tmdb, tvdb, season, episode, '', '', '', str(duration),
                          str(round(position / duration * 100, 2)), row.get('updated_at') or ''))
    return movies, episodes, bookmarks


class Client:
    def __init__(self, base, request, cancelled=lambda: False):
        self.base, self.request, self.cancelled = base.rstrip('/'), request, cancelled

    def url(self, value, **params):
        if not isinstance(value, str) or not value:
            raise ValueError('Missing Floppy sync URL')
        root = urlsplit(self.base)
        target = urlsplit(urljoin(self.base + '/', value))
        if ((target.scheme, target.netloc) != (root.scheme, root.netloc)
                or not target.path.startswith(root.path + '/')
                or target.username or target.password or target.fragment):
            raise ValueError('Floppy sync URL outside configured API')
        query = dict(parse_qsl(target.query, keep_blank_values=True))
        query.update({k: str(v) for k, v in params.items()})
        return urlunsplit(target._replace(query=urlencode(query)))

    def fetch(self, url, method='GET', bootstrap=False):
        if self.cancelled(): raise Cancelled('Floppy sync cancelled')
        try:
            response = self.request(self.url(url), method=method, silent=True)
        except RuntimeError as exc:
            # getFloppy's strict mode supplies sanitized failure details.
            raise ValueError('%s %s: %s' % (method, urlsplit(url).path, exc)) from None
        if response is None: raise ValueError('Floppy sync request failed')
        # Only the bootstrap's absence proves this is an older server.
        if bootstrap and response.status_code in (404, 405): raise Unavailable()
        try: data = response.json()
        except Exception: raise ValueError('Invalid Floppy sync response (HTTP %s)' % response.status_code)
        if not isinstance(data, dict): raise ValueError('Invalid Floppy sync response')
        if response.status_code in (400, 409) and data.get('code') in (
                'sync_not_initialized', 'cursor_expired', 'sync_reset_required',
                'cursor_invalid', 'invalid_context', 'invalid_page'):
            raise Reset()
        if response.status_code != 200:
            raise ValueError('Floppy sync HTTP %s (%s)' % (response.status_code, data.get('code', 'unknown')))
        return data

    def rows(self, mirror, resource, rows):
        if not isinstance(rows, list): raise ValueError('Invalid Floppy sync rows')
        for row in rows:
            if not isinstance(row, dict) or number(row.get('item_id')) == 0:
                raise ValueError('Missing Floppy item identity')
            key = str(row['item_id'])
            if row.get('kind') == 'delete':
                mirror[resource].pop(key, None)
            else:
                if resource == 'watched' and type(row.get('watched')) is not bool:
                    raise ValueError('Missing Floppy watched assertion')
                if resource == 'progress' and type(row.get('completed')) is not bool:
                    raise ValueError('Missing Floppy progress assertion')
                if resource == 'progress' and not row.get('updated_at'):
                    old = mirror[resource].get(key, {})
                    same = all(old.get(field) == row.get(field) for field in
                               ('position_seconds', 'duration_seconds', 'completed'))
                    row = dict(row, updated_at=(old.get('updated_at') if same else None)
                               or datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z'))
                mirror[resource][key] = row

    def snapshot(self, state, mirror, resource):
        url = self.url(state['snapshots'][resource], limit=500)
        seen = set()
        last_item = 0
        for _ in range(10000):
            data = self.fetch(url)
            if (data.get('resource') != resource or data.get('cursor') != state['cursors'][resource]
                    or type(data.get('has_more')) is not bool):
                raise ValueError('Mixed Floppy snapshot context')
            rows = data.get('results')
            if not isinstance(rows, list): raise ValueError('Invalid Floppy snapshot rows')
            for row in rows:
                item = number(row.get('item_id'))
                if item <= last_item: raise ValueError('Out-of-order Floppy snapshot')
                last_item = item
            self.rows(mirror, resource, rows)
            if not data['has_more']: return
            if not rows: raise ValueError('Empty continued Floppy snapshot')
            after = data.get('after')
            if not isinstance(after, str) or not after or after in seen:
                raise ValueError('Floppy snapshot did not advance')
            seen.add(after)
            url = self.url(state['snapshots'][resource], limit=500, after=after)
        raise ValueError('Floppy snapshot page limit exceeded')

    def drain(self, state, mirror, resource):
        cursor = number(state['cursors'][resource])
        for _ in range(10000):
            data = self.fetch(self.url(state['feeds'][resource], cursor=cursor, limit=500))
            next_cursor = number(data.get('next_cursor'))
            high = number(data.get('high_water'))
            floor = number(data.get('minimum_valid_cursor'))
            more = data.get('has_more')
            if (data.get('complete') is not True or data.get('recording_enabled') is not True
                    or data.get('generation') != state['generation']):
                raise Reset()
            if (type(more) is not bool or not floor <= cursor <= next_cursor <= high
                    or (more and next_cursor <= cursor) or (not more and next_cursor != high)):
                raise ValueError('Invalid Floppy sync interval')
            rows = data.get('results')
            if not isinstance(rows, list): raise ValueError('Invalid Floppy feed rows')
            last = cursor
            for row in rows:
                sequence = number(row.get('sequence'))
                if not last < sequence <= next_cursor: raise ValueError('Out-of-order Floppy event')
                last = sequence
            if more and (not rows or last != next_cursor):
                raise ValueError('Floppy feed cursor does not match page')
            self.rows(mirror, resource, rows)
            state['cursors'][resource] = cursor = next_cursor
            if not more: return
        raise ValueError('Floppy feed page limit exceeded')

    def sync(self, saved=None, mirror=None, forced=False):
        # Everything is staged privately, including replay. A failed request leaves
        # the caller's durable mirror and cursors untouched.
        for attempt in range(2):
            try:
                state = deepcopy(saved) if saved and not forced else None
                staged = deepcopy(mirror) if state else {'watched': {}, 'progress': {}}
                if state is None:
                    state = self.fetch(self.base + '/sync/bootstrap/', method='POST', bootstrap=True)
                    if (state.get('contract') != 2 or not state.get('context') or not state.get('generation')):
                        raise ValueError('Unsupported Floppy bootstrap')
                    for resource in ('watched', 'progress'):
                        number(state['cursors'][resource])
                        self.url(state['feeds'][resource])
                        self.snapshot(state, staged, resource)
                for resource in ('watched', 'progress'):
                    self.drain(state, staged, resource)
                return state, staged
            except Reset:
                saved, mirror, forced = None, None, True
                if attempt: raise
