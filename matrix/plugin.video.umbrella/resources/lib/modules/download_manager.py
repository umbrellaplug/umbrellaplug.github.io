"""Persistent download status shared by separate Kodi plugin invocations.

Resume requests are stored separately from display history in addon_data.
URLs and headers are never returned to the manager UI or written to logs.
Home-window markers identify workers in this Kodi run.
"""
import os
import sqlite3
import json
from contextlib import closing
from time import time
from uuid import uuid4

ACTIVE = ('Connecting', 'Awaiting confirmation', 'Downloading', 'Retrying', 'Cancelling')


class DownloadStore:
    def __init__(self, path=None, window=None):
        from resources.lib.modules import control
        self.path = path or os.path.join(control.dataPath, 'downloads.db')
        self.window = window if window is not None else control.homeWindow
        if not path: control.makeFile(control.dataPath)
        with closing(self.connect()) as con, con:
            con.execute('''CREATE TABLE IF NOT EXISTS downloads (
                id TEXT PRIMARY KEY, title TEXT, destination TEXT, status TEXT,
                downloaded INTEGER, total INTEGER, speed REAL, message TEXT,
                created REAL, updated REAL, cancel INTEGER DEFAULT 0)''')
            con.execute('''CREATE TABLE IF NOT EXISTS resume_requests (
                id TEXT PRIMARY KEY, url TEXT, headers TEXT,
                validator_name TEXT, validator TEXT, total INTEGER)''')

    def connect(self):
        con = sqlite3.connect(self.path, timeout=5)
        con.row_factory = sqlite3.Row
        return con

    def marker(self, job):
        return 'umbrella.download.' + job

    def create(self, title, destination):
        job = uuid4().hex
        self.window.setProperty(self.marker(job), 'running')
        try:
            with closing(self.connect()) as con, con:
                con.execute('BEGIN IMMEDIATE')
                rows = con.execute('SELECT id, status FROM downloads WHERE destination=?', (destination,)).fetchall()
                for row in rows:
                    if row['status'] in ACTIVE and self.window.getProperty(self.marker(row['id'])):
                        raise ValueError('This file is already being downloaded.')
                now = time()
                con.execute('INSERT INTO downloads VALUES (?, ?, ?, ?, 0, 0, 0, ?, ?, ?, 0)',
                            (job, title, destination, 'Connecting', '', now, now))
            return job
        except Exception:
            self.window.clearProperty(self.marker(job))
            raise

    def update(self, job, status, downloaded=0, total=0, speed=0, message=''):
        with closing(self.connect()) as con, con:
            con.execute('UPDATE downloads SET status=?, downloaded=?, total=?, speed=?, message=?, updated=? WHERE id=?',
                        (status, downloaded, total, speed, message, time(), job))
        if status not in ACTIVE: self.window.clearProperty(self.marker(job))
        if status == 'Completed':
            with closing(self.connect()) as con, con:
                con.execute('DELETE FROM resume_requests WHERE id=?', (job,))

    def save_request(self, job, url, headers, validator_name, validator, total):
        with closing(self.connect()) as con, con:
            con.execute('INSERT OR REPLACE INTO resume_requests VALUES (?, ?, ?, ?, ?, ?)',
                        (job, url, json.dumps(headers), validator_name, validator, total))

    def claim_resume(self, job):
        """Atomically reserve an existing partial download for one worker."""
        with closing(self.connect()) as con, con:
            con.execute('BEGIN IMMEDIATE')
            row = con.execute('''SELECT d.*, r.url, r.headers, r.validator_name, r.validator,
                r.total AS expected_total FROM downloads d JOIN resume_requests r ON d.id=r.id
                WHERE d.id=?''', (job,)).fetchone()
            if not row or row['status'] not in ('Failed', 'Interrupted', 'Cancelled'):
                raise ValueError('This download has no saved resume information or is already active.')
            for other in con.execute('SELECT id, status FROM downloads WHERE destination=?', (row['destination'],)):
                if other['status'] in ACTIVE and self.window.getProperty(self.marker(other['id'])):
                    raise ValueError('This file is already being downloaded.')
            result = dict(row)
            result['headers'] = json.loads(row['headers'])
            con.execute("UPDATE downloads SET status='Connecting', cancel=0, speed=0, message='', updated=? WHERE id=?", (time(), job))
            self.window.setProperty(self.marker(job), 'running')
        return result

    def cancelled(self, job):
        with closing(self.connect()) as con:
            row = con.execute('SELECT cancel FROM downloads WHERE id=?', (job,)).fetchone()
        return bool(row and row['cancel'])

    def cancel(self, job):
        with closing(self.connect()) as con, con:
            con.execute("UPDATE downloads SET cancel=1, status='Cancelling' WHERE id=? AND status IN (%s)" %
                        ','.join('?' for _ in ACTIVE), (job,) + ACTIVE)

    def rows(self):
        with closing(self.connect()) as con, con:
            rows = con.execute('SELECT * FROM downloads ORDER BY created DESC').fetchall()
            for row in rows:
                if row['status'] in ACTIVE and not self.window.getProperty(self.marker(row['id'])):
                    con.execute("UPDATE downloads SET status='Interrupted', message=? WHERE id=?",
                                ('Kodi or the download worker stopped before completion.', row['id']))
            result = [dict(row) for row in con.execute('''SELECT downloads.*,
                EXISTS(SELECT 1 FROM resume_requests r WHERE r.id=downloads.id) AS can_resume FROM downloads
                ORDER BY CASE WHEN status IN ('Connecting','Awaiting confirmation','Downloading','Retrying','Cancelling')
                THEN 0 ELSE 1 END, created DESC LIMIT 200''')]
            for row in result:
                row['can_resume'] = bool(row['can_resume'] and row['status'] in ('Failed', 'Cancelled', 'Interrupted')
                                         and os.path.isfile(row['destination'] + '.part'))
            return result

    def remove(self, job):
        """Remove a finished history entry without touching its files."""
        with closing(self.connect()) as con, con:
            result = con.execute('''DELETE FROM downloads WHERE id=?
                AND status IN ('Failed', 'Cancelled', 'Interrupted', 'Completed')''', (job,))
            if result.rowcount:
                con.execute('DELETE FROM resume_requests WHERE id=?', (job,))
            return result.rowcount > 0


def open_manager():
    from resources.lib.modules import control
    from resources.lib.windows.download_manager import DownloadManager
    try:
        store = DownloadStore()
        window = DownloadManager('download_manager.xml', control.addonInfo('path'), 'Default', '1080i', store=store)
        window.run()
        del window
    except Exception:
        control.notification(title='Downloads', message='Unable to open download history.', icon='ERROR')
