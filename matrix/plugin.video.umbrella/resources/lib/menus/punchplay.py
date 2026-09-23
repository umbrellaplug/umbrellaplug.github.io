# -*- coding: utf-8 -*-
"""PunchPlay public discovery and personal release calendar."""
from datetime import datetime
from urllib.parse import urlencode

from resources.lib.modules import control, log_utils, punchplay


def _folders(items):
    from resources.lib.menus.navigator import Navigator
    nav = Navigator(lightweight=True)
    for name, params in items:
        nav.addDirectoryItem(name, 'plugin://plugin.video.umbrella/?' + urlencode(params),
                             'punchplay.png', 'punchplay.png', isAction=False)
    nav.endDirectory()


def catalog_menu(media_type=None):
    if media_type not in ('movie', 'show', 'anime'):
        return _folders([(name, {'action': 'punchplay_catalog_menu', 'media_type': kind})
                         for name, kind in [('Movies', 'movie'), ('TV Shows', 'show'), ('Anime', 'anime')]])
    categories = [('Trending', 'trending'), ('Popular', 'popular'), ('Top Rated', 'top_rated'),
                  ('Now Playing', 'now_playing'), ('Upcoming', 'upcoming')]
    _folders([(name, {'action': 'punchplay_catalog', 'media_type': media_type,
                     'category': category, 'folderName': 'PunchPlay - ' + name})
              for name, category in categories])


def _title_item(row):
    kind = row['type']
    item = {'tmdb': str(row['tmdbId']), 'imdb': '', 'tvdb': '',
            'title': row['name'], 'originaltitle': row['name'], 'year': str(row.get('year') or ''),
            'plot': row.get('overview', ''), 'poster': row.get('posterUrl', ''),
            'fanart': row.get('backdropUrl', ''), 'premiered': row.get('releaseDate', ''),
            'mediatype': 'movies' if kind == 'movie' else 'tvshows'}
    if kind == 'show':
        item['tvshowtitle'] = row['name']
    return item


def _titles(items, kind, folder_name, next_url='', calendar=False, show_unreleased=False):
    if kind == 'movie':
        from resources.lib.menus.movies import Movies
        menu = Movies()
    else:
        from resources.lib.menus.tvshows import TVshows
        menu = TVshows()
    menu.list = items
    menu.worker()
    for item in menu.list:
        item['next'] = next_url
    if calendar:
        menu.list.sort(key=lambda i: (i['punchplay_date'], i['title'].casefold()))
    if kind == 'movie':
        if calendar or show_unreleased:
            menu.hidecinema = False
        menu.movieDirectory(menu.list, folderName=folder_name)
    else:
        if show_unreleased:
            menu.showunaired = True
        menu.tvshowDirectory(menu.list, folderName=folder_name)


def catalog(media_type='movie', category='popular', kind=None, page=1, folder_name=''):
    # Anime is a display category containing both movies and series. Keep each
    # Kodi directory homogeneous so the normal playback and context actions work.
    if media_type == 'anime' and kind not in ('movie', 'show'):
        return _folders([(name, {'action': 'punchplay_catalog', 'media_type': 'anime',
                                 'category': category, 'kind': value, 'folderName': folder_name})
                         for name, value in [('Movies', 'movie'), ('TV Shows', 'show')]])
    kind = kind if media_type == 'anime' else media_type
    try:
        rows = punchplay.get_catalog(media_type, category)
        items = [_title_item(i) for i in rows if i.get('type') == kind]
        page = max(1, int(page))
        limit = max(1, int(control.setting('page.item.limit') or 20))
        start = (page - 1) * limit
        next_url = ''
        if start + limit < len(items):
            next_url = 'plugin://plugin.video.umbrella/?' + urlencode({
                'action': 'punchplay_catalog', 'media_type': media_type, 'category': category,
                'kind': kind, 'page': page + 1, 'folderName': folder_name})
        _titles(items[start:start + limit], kind, folder_name or 'PunchPlay', next_url,
                show_unreleased=category == 'upcoming')
    except Exception as exc:
        log_utils.error()
        control.notification(title='PunchPlay', message=str(exc))
        _folders([])


def calendar_menu(media_type='movie'):
    now = datetime.now()
    months = []
    for offset in range(12):
        year, month = divmod(now.year * 12 + now.month - 1 + offset, 12)
        date = datetime(year, month + 1, 1)
        months.append((date.strftime('%B %Y'), {'action': 'punchplay_my_calendar',
                       'media_type': media_type, 'month': date.strftime('%Y-%m')}))
    _folders(months)


def _calendar_movie(row):
    return {'tmdb': str(row['tmdbId']), 'imdb': '', 'title': row['title'], 'year': '',
            'poster': row.get('posterUrl', ''), 'premiered': row['date'], 'mediatype': 'movies',
            'punchplay_date': row['date'],
            'punchplay_release': 'Digital' if row['kind'] == 'movie-digital' else 'Theatrical'}


def _calendar_episode(row):
    from resources.lib.database import cache
    from resources.lib.indexers.tmdb import TVshows
    nxt = row.get('nextEpisode') or {}
    if nxt.get('season') is None or nxt.get('episode') is None:
        return None
    tmdb = str(row['tmdbId'])  # Calendar episode IDs identify the parent show.
    season, episode = int(nxt['season']), int(nxt['episode'])
    values = {}
    try:
        indexer = TVshows()
        values.update(cache.get(indexer.get_showSeasons_meta, 96, tmdb) or {})
        season_meta = indexer.get_seasonEpisodes_meta_checked(tmdb, season) or {}
        values.update({k: v for k, v in season_meta.items() if k != 'episodes'})
        values.update(next((i for i in season_meta.get('episodes', [])
                            if int(i.get('episode', -1)) == episode), {}))
    except Exception:
        log_utils.error()
    values.update({'tmdb': tmdb, 'imdb': values.get('imdb', ''), 'tvdb': values.get('tvdb', ''),
                   'tvshowtitle': row['title'], 'title': nxt.get('name') or values.get('title') or row['title'],
                   'season': season, 'episode': episode, 'premiered': row['date'],
                   'punchplay_date': row['date'], 'mediatype': 'episode',
                   'unaired': 'true' if row['date'] > datetime.now().strftime('%Y-%m-%d') else '',
                   'poster': row.get('posterUrl') or values.get('poster', ''), 'action': 'episodes'})
    values.pop('episodes', None)
    # TMDB's episode metadata uses minutes; the directory renderer expects seconds.
    if values.get('duration'):
        values['duration'] = int(values['duration']) * 60
    return values


def calendar(month, media_type='movie'):
    try:
        rows = punchplay.get_calendar_items(month, media_type)
        folder_name = 'PunchPlay Calendar - ' + month
        if media_type == 'movie':
            _titles([_calendar_movie(i) for i in rows], 'movie', folder_name, calendar=True)
        else:
            from resources.lib.menus.episodes import Episodes
            menu = Episodes()
            items = []
            for row in rows:
                if control.monitor.abortRequested():
                    break
                if not menu.showspecials and (row.get('nextEpisode') or {}).get('season') == 0:
                    continue
                item = _calendar_episode(row)
                if item:
                    items.append(item)
            menu.showunaired = True
            menu.episodeDirectory(items, folderName=folder_name)
    except Exception as exc:
        log_utils.error()
        control.notification(title='PunchPlay', message=str(exc))
        _folders([])
