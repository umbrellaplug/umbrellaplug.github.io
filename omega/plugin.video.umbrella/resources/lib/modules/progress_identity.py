"""Reconcile partial provider IDs without combining split-catalog stories."""


def matches_show(ids, imdb='', tmdb='', tvdb=''):
    def clean(value):
        return '' if value in (None, '', 'None', '0', 0) else str(value)
    wanted = dict(imdb=clean(imdb), tmdb=clean(tmdb), tvdb=clean(tvdb))
    actual = {field: clean(ids.get(field)) for field in wanted}
    if wanted['tmdb'] and actual['tmdb']:
        return wanted['tmdb'] == actual['tmdb']
    return any(value and value == actual[field] for field, value in wanted.items())


def group_watched_shows(episodes, watched_shows=()):
    def clean(value):
        return '' if value in (None, '', 'None', '0', 0) else str(value)

    episodes, watched_shows = list(episodes), list(watched_shows)
    aliases = {}
    for row in episodes + watched_shows:
        imdb, tmdb, tvdb = map(clean, row[:3])
        if tmdb:
            for kind, value in (('imdb', imdb), ('tvdb', tvdb)):
                if value: aliases.setdefault((kind, value), set()).add(tmdb)

    def identity(row):
        imdb, tmdb, tvdb = map(clean, row[:3])
        if not tmdb:
            candidates = set()
            for kind, value in (('imdb', imdb), ('tvdb', tvdb)):
                candidates.update(aliases.get((kind, value), ()))
            if len(candidates) == 1: tmdb = next(iter(candidates))
            elif candidates: return None, imdb, '', tvdb
        key = ('tmdb', tmdb) if tmdb else ('imdb', imdb) if imdb else ('tvdb', tvdb)
        return key if key[1] else None, imdb, tmdb, tvdb

    shows = {}
    for row in episodes:
        key, imdb, tmdb, tvdb = identity(row)
        if key is None: continue
        show = shows.setdefault(key, dict(imdb='', tmdb='', tvdb='', watched_set=set()))
        for field, value in (('imdb', imdb), ('tmdb', tmdb), ('tvdb', tvdb)):
            if value: show[field] = value
        show['watched_set'].add((int(row[3]), int(row[4])))
    for row in watched_shows:
        key = identity(row)[0]
        if key in shows:
            shows[key]['lastplayed'] = max(shows[key].get('lastplayed', ''), row[3] or '')
    return list(shows.values())
