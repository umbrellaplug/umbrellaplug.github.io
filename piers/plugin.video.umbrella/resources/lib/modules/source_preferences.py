"""Explicit TV pack preferences; match only current, playable scrape results."""
import json
import os
import sqlite3


def scope(meta):
    if not isinstance(meta, dict) or meta.get('episode') in (None, '', 'None'):
        return None
    # TMDb distinguishes split series which can share an IMDb ID.
    for name in ('tmdb', 'imdb', 'tvdb'):
        value = meta.get(name)
        if value not in (None, '', '0', 0, 'None'):
            try:
                return '%s:%s' % (name, value), str(int(meta['season']))
            except (KeyError, TypeError, ValueError):
                return None


def eligible(item):
    return (item.get('package') in ('season', 'show') and bool(item.get('hash'))
            and item.get('url', '').startswith('magnet:')
            and bool(item.get('debrid')) and 'uncached' not in item.get('source', '').lower())


def _connection():
    from resources.lib.modules import control
    os.makedirs(control.dataPath, exist_ok=True)
    connection = sqlite3.connect(os.path.join(control.dataPath, 'source_preferences.db'), timeout=5)
    connection.execute('CREATE TABLE IF NOT EXISTS preferences (show TEXT, season TEXT, data TEXT, PRIMARY KEY(show, season))')
    return connection


def get(meta):
    key = scope(meta)
    if not key:
        return None
    connection = _connection()
    try:
        row = connection.execute('SELECT data FROM preferences WHERE show=? AND season=?', key).fetchone()
        return json.loads(row[0]) if row else None
    finally:
        connection.close()


def save(meta, item):
    key = scope(meta)
    if not key or not eligible(item):
        return False
    data = {'hash': item['hash'].lower(), 'debrid': item['debrid'], 'name': item.get('name', '')}
    connection = _connection()
    try:
        with connection:
            connection.execute('INSERT OR REPLACE INTO preferences VALUES (?, ?, ?)', key + (json.dumps(data),))
    finally:
        connection.close()
    return True


def clear(meta):
    key = scope(meta)
    if not key:
        return
    connection = _connection()
    try:
        with connection:
            connection.execute('DELETE FROM preferences WHERE show=? AND season=?', key)
    finally:
        connection.close()


def matching(items, preference):
    return [item for item in items if eligible(item)
            and item['hash'].lower() == preference['hash']
            and item['debrid'] == preference['debrid']]
