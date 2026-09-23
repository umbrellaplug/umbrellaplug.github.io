# -*- coding: utf-8 -*-
"""Read-only library sources for Umbrella's self-hosted tracking providers."""
from importlib import import_module
from urllib.parse import urlencode, urlsplit
import re

from resources.lib.modules import control

SERVICES = ('custom', 'scrob', 'floppy')
PREFIXES = tuple(name + '://' for name in SERVICES)
FLOPPY_STATUSES = {'watchlist': 0, 'watching': 1, 'hold': 2, 'completed': 3, 'dropped': 4}


def _provider(service):
    if service not in SERVICES:
        raise ValueError('Unknown library service')
    return import_module('resources.lib.modules.' + ('customtrakt' if service == 'custom' else service))


def service_label(service):
    return _provider(service).getCustomServiceName() if service == 'custom' else service.capitalize()


def available_services():
    # Avoid importing unconfigured providers (and initializing their HTTP sessions).
    setting = control.setting
    configured = {
        'custom': setting('dev.enable.custom') == 'true' and setting('custom.user.token'),
        'scrob': setting('scrob.baseurl') and any(setting('scrob.' + key) for key in ('apikey', 'accesstoken', 'refreshtoken')),
        'floppy': setting('floppy.baseurl') and setting('floppy.token')}
    getters = {'custom': 'getCustomCredentialsInfo', 'scrob': 'getScrobCredentialsInfo', 'floppy': 'getFloppyCredentialsInfo'}
    return [{'name': service_label(service), 'url': service} for service in SERVICES
            if configured[service] and getattr(_provider(service), getters[service])()]


def _read(service, path):
    provider = _provider(service)
    if service == 'custom':
        response = provider.getCustom(path, silent=True)
    elif service == 'scrob':
        response = provider.getScrob(path, auth='api_key', silent=True)
    else:
        response = provider.getFloppy(path, silent=True)
    if response is None or response.status_code != 200:
        raise RuntimeError('%s library source could not be read.' % service_label(service))
    try:
        return response.json(), response.headers
    except (ValueError, TypeError):
        raise RuntimeError('%s returned an invalid library response.' % service_label(service))


def _rows(data, keys=('items', 'results', 'lists')):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in keys:
            if isinstance(data.get(key), list):
                return data[key]
    raise RuntimeError('Unexpected library list response')


def _pages(service, path):
    """Read complete snapshots, rejecting failed later pages instead of truncating."""
    result, previous = [], None
    page, offset = 1, 0
    for _ in range(1000):
        if control.monitor.abortRequested():
            raise RuntimeError('Library import cancelled')
        params = {'limit': 200, 'offset': offset} if service == 'floppy' else {'limit': 1000, 'page': page}
        data, headers = _read(service, path + ('&' if '?' in path else '?') + urlencode(params))
        rows = _rows(data)
        pagination = data.get('pagination') if isinstance(data, dict) else None
        pagination = pagination or {}
        total_pages = pagination.get('total_pages') or pagination.get('page_count') or headers.get('X-Pagination-Page-Count')
        more = bool(pagination.get('next')) if 'next' in pagination else (page < int(total_pages) if total_pages else None)
        if rows == previous or not rows:
            if more:
                raise RuntimeError('Library pagination did not advance')
            return result
        result.extend(rows)
        if more is False:
            return result
        if service == 'floppy' and more is None and len(rows) < 200:
            return result
        previous = rows
        offset += len(rows)
        page += 1
    raise RuntimeError('Library source exceeded the pagination limit')


def _list_id(service, item):
    value = _provider(service).list_numeric_id(item) if service == 'custom' else item.get('id')
    value = str(value or '')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', value):
        raise ValueError('Invalid library list identifier')
    return value


def get_sources(service):
    if service == 'custom':
        data, _ = _read(service, '/users/me/lists')
        lists = _rows(data)
        sources = [('watchlist', 'Watchlist', 0), ('collection', 'Collection', 0)]
    elif service == 'floppy':
        lists = _pages(service, '/lists/')
        sources = [('watchlist', 'Watchlist', 0), ('collection', 'Collection', 0),
                   ('watching', 'Watching', 0), ('hold', 'On Hold', 0),
                   ('completed', 'Completed', 0), ('dropped', 'Dropped', 0)]
    elif service == 'scrob':
        data, _ = _read(service, '/lists')
        lists = _rows(data, ('lists',))
        sources = []
    else:
        raise ValueError('Unknown library service')
    sources += [('lists/' + _list_id(service, item), item.get('name') or 'Untitled',
                 item.get('item_count') or item.get('items_count') or 0)
                for item in sorted(lists, key=lambda i: (i.get('name') or '').casefold())]
    return [{'name': name, 'list_name': name, 'url': service + '://' + source,
             'list_id': service + '_' + source.replace('/', '_'), 'list_count': count,
             'action': 'mixed', 'list_owner': '', 'list_owner_slug': '', 'likes': 0, 'selected': ''}
            for source, name, count in sources]


def _source_rows(service, source, media_type):
    if source.startswith('lists/'):
        list_id = source[6:]
        if not re.fullmatch(r'[A-Za-z0-9_-]+', list_id):
            raise ValueError('Invalid library list identifier')
        if service == 'custom':
            data, _ = _read(service, '/users/me/lists/%s/items' % list_id)
            return [(i, None) for i in _rows(data)]
        if service == 'scrob':
            data, _ = _read(service, '/lists/%s' % list_id)
            return [(i, None) for i in _rows(data, ('items',))]
        return [(i, None) for i in _pages(service, '/lists/%s/items/' % list_id)]
    result = []
    for kind in ([media_type] if media_type else ['movie', 'show']):
        if service == 'custom' and source in ('watchlist', 'collection'):
            path = '/sync/%s/%s?extended=full' % (source, kind)
        elif service == 'floppy' and source in FLOPPY_STATUSES:
            path = '/media/%s/?status=%s' % ('movie' if kind == 'movie' else 'tv', FLOPPY_STATUSES[source])
        elif service == 'floppy' and source == 'collection':
            path = '/collection/?item_media_type=%s' % ('movie' if kind == 'movie' else 'tv')
        else:
            raise ValueError('Unknown library source')
        result.extend((i, kind) for i in _pages(service, path))
    return result


def _normalize(service, row, fallback_kind):
    if service == 'custom':
        kind = 'movie' if isinstance(row.get('movie'), dict) else 'show' if isinstance(row.get('show'), dict) else fallback_kind
        media = row.get(kind) or row
        ids = media.get('ids') or {}
        item = {'tmdb': str(ids.get('tmdb') or ''), 'imdb': str(ids.get('imdb') or ''), 'tvdb': str(ids.get('tvdb') or '')}
    else:
        media = row.get('media' if service == 'scrob' else 'item') or {}
        kind = media.get('type' if service == 'scrob' else 'media_type') or fallback_kind
        kind = 'show' if kind in ('tv', 'series', 'show') else kind
        item = {'tmdb': str(media.get('tmdb_id' if service == 'scrob' else 'media_id') or ''), 'imdb': '', 'tvdb': ''}
    if kind not in ('movie', 'show'):
        return None, None
    item.update(title=media.get('title') or '', year=str(media.get('year') or
                (media.get('release_date') or media.get('release_datetime') or '')[:4]),
                mediatype='movies' if kind == 'movie' else 'tvshows')
    return item, kind


def _hydrate(item, kind):
    from resources.lib.database import cache
    from resources.lib.indexers import tmdb
    indexer = tmdb.Movies() if kind == 'movie' else tmdb.TVshows()
    if not item['tmdb']:
        args = (item['imdb'],) if kind == 'movie' else (item['imdb'], item['tvdb'])
        result = cache.get(indexer.IdLookup, 96, *args) or {}
        item['tmdb'] = str(result.get('id') or '')
    if not item['tmdb'].isdigit() or int(item['tmdb']) <= 0:
        raise RuntimeError('Unable to identify a title for library export: ' + item['title'])
    if not item['title'] or not item['year'].isdigit():
        getter = indexer.get_movie_meta if kind == 'movie' else indexer.get_showSeasons_meta
        meta = cache.get(getter, 96, item['tmdb']) or {}
        item['title'] = item['title'] or meta.get('title') or meta.get('tvshowtitle') or ''
        item['year'] = str(meta.get('year') or item['year'])
        item['imdb'] = item['imdb'] or meta.get('imdb') or ''
        item['tvdb'] = item['tvdb'] or meta.get('tvdb') or ''
    if not item['title'] or not item['year'].isdigit():
        raise RuntimeError('Missing title or year for library export: ' + item['title'])
    item['originaltitle'] = item['title']
    if kind == 'show':
        item['tvshowtitle'] = item['title']
    return item


def get_items(url, media_type=None):
    parsed = urlsplit(url)
    service = parsed.scheme
    if service not in SERVICES or parsed.query or parsed.fragment or media_type not in (None, 'movie', 'show'):
        raise ValueError('Invalid library source')
    source = parsed.netloc + parsed.path
    # Fetch the whole snapshot before returning any titles to the library writer.
    rows = _source_rows(service, source, media_type)
    items, seen = [], set()
    for row, fallback_kind in rows:
        if control.monitor.abortRequested():
            raise RuntimeError('Library import cancelled')
        item, kind = _normalize(service, row, fallback_kind)
        if item is None or media_type and kind != media_type:
            continue
        item = _hydrate(item, kind)
        key = (kind, item['tmdb'])
        if key not in seen:
            seen.add(key)
            items.append(item)
    return items
