"""Upgrade IMDb-only episode caches without discarding watched history."""


def ensure(cursor, table):
    if table not in ('mdb_watched_episodes', 'custom_watched_episodes'):
        raise ValueError('Unexpected episode table')
    schema = cursor.execute('SELECT sql FROM sqlite_master WHERE type=? AND name=?', ('table', table)).fetchone()
    cursor.execute('SAVEPOINT episode_identity_upgrade')
    try:
        _upgrade(cursor, table, schema)
        cursor.execute('RELEASE episode_identity_upgrade')
    except Exception:
        cursor.execute('ROLLBACK TO episode_identity_upgrade')
        cursor.execute('RELEASE episode_identity_upgrade')
        raise


def _upgrade(cursor, table, schema):
    if schema and 'UNIQUE(show_imdb, season, episode)' in schema[0]:
        # Build and copy first; replace only after every row has been copied.
        cursor.execute('SAVEPOINT episode_identity')
        try:
            cursor.execute('CREATE TABLE %s_identity (show_imdb TEXT, show_tmdb TEXT, show_tvdb TEXT, season INTEGER, episode INTEGER, last_watched_at TEXT)' % table)
            cursor.execute('INSERT INTO %s_identity SELECT * FROM %s' % (table, table))
            cursor.execute('DROP TABLE %s' % table)
            cursor.execute('ALTER TABLE %s_identity RENAME TO %s' % (table, table))
            cursor.execute('CREATE TABLE IF NOT EXISTS service (setting TEXT, value TEXT, UNIQUE(setting))')
            for key in ('last_history_at', 'last_watched_at', 'last_watched_sync_at_v2', 'last_watched_episodes_at'):
                cursor.execute('INSERT OR REPLACE INTO service VALUES (?, ?)', (key, '1970-01-01T00:00:00.000Z'))
            if cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='watched'").fetchone():
                cursor.execute('DELETE FROM watched')  # derived indicators, not history
            cursor.execute('RELEASE episode_identity')
        except Exception:
            cursor.execute('ROLLBACK TO episode_identity')
            cursor.execute('RELEASE episode_identity')
            raise
    # TMDB identifies split shows even when IMDb is empty/shared. Keep an IMDb
    # fallback for records whose provider has not returned a TMDB ID.
    # Older syncs can store the same TMDB episode under different IMDb IDs.
    # Collapse only exact identity/season/episode duplicates, keeping the newest
    # watched record. Do this before installing the stricter unique index.
    if not cursor.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name=?", (table + '_identity_key',)).fetchone():
        cursor.execute("CREATE INDEX IF NOT EXISTS %s_identity_migration ON %s "
                       "(COALESCE(NULLIF(show_tmdb, ''), show_imdb), season, episode)" % (table, table))
        cursor.execute("""DELETE FROM {table} WHERE rowid IN (
            SELECT older.rowid FROM {table} AS older
            WHERE EXISTS (SELECT 1 FROM {table} AS newer
                WHERE COALESCE(NULLIF(newer.show_tmdb, ''), newer.show_imdb)
                    = COALESCE(NULLIF(older.show_tmdb, ''), older.show_imdb)
                AND newer.season = older.season AND newer.episode = older.episode
                AND (COALESCE(newer.last_watched_at, '') > COALESCE(older.last_watched_at, '')
                    OR (COALESCE(newer.last_watched_at, '') = COALESCE(older.last_watched_at, '')
                        AND newer.rowid > older.rowid))))""".format(table=table))
        cursor.execute('DROP INDEX %s_identity_migration' % table)
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS %s_identity_key ON %s "
                   "(COALESCE(NULLIF(show_tmdb, ''), show_imdb), season, episode)" % (table, table))
