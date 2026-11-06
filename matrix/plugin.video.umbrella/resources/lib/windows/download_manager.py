"""Skin-independent live download status dialog."""
from threading import Event, Thread, RLock
import xbmcgui
from resources.lib.modules import control
from resources.lib.modules.download_manager import ACTIVE


def size_text(value):
    value = float(value or 0)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if value < 1024 or unit == 'TB': return '%.1f %s' % (value, unit)
        value /= 1024


def status_text(row):
    amount = size_text(row['downloaded'])
    if row['total']:
        amount = '%d%% | %s / %s' % (min(100, row['downloaded'] * 100 // row['total']), amount, size_text(row['total']))
    else: amount += ' | size unknown'
    if row['status'] == 'Downloading': amount += ' | %s/s' % size_text(row['speed'])
    return '%s | %s' % (row['status'], amount)


class DownloadManager(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.store = kwargs['store']
        self.stopped = Event()
        self.lock = RLock()
        self.worker = None
        self.rows = []

    def onInit(self):
        self.setProperty('download.heading', control.lang(40867) or 'Download Manager')
        self.render()
        self.setFocusId(100 if self.rows else 101)
        self.worker = Thread(target=self.refresh, name='umbrella-download-status')
        self.worker.daemon = True
        self.worker.start()

    def refresh(self):
        while not self.stopped.wait(1):
            if control.monitor.abortRequested(): break
            try: self.render()
            except Exception:
                self.setProperty('download.message', 'Unable to refresh download history.')

    def render(self):
        with self.lock:
            rows = self.store.rows()
            listing = self.getControl(100)
            old_ids = [row['id'] for row in self.rows]
            new_ids = [row['id'] for row in rows]
            if old_ids != new_ids:
                selected = listing.getSelectedPosition()
                selected_id = old_ids[selected] if 0 <= selected < len(old_ids) else None
                listing.reset()
                listing.addItems([control.item(label=row['title'], offscreen=True) for row in rows])
                if selected_id in new_ids: listing.selectItem(new_ids.index(selected_id))
                elif rows: listing.selectItem(min(max(selected, 0), len(rows) - 1))
                elif old_ids: self.setFocusId(101)
            for index, row in enumerate(rows):
                listing.getListItem(index).setLabel2(status_text(row))
            self.rows = rows
            active = sum(row['status'] in ACTIVE for row in rows)
            self.setProperty('download.message', '%s active | Select a download for details, resume, cancellation or removal.' % active
                             if rows else 'No downloads yet. Downloads you start will appear here.')

    def onClick(self, control_id):
        if control_id == 101:
            self.stopped.set()
            return self.close()
        if control_id != 100: return
        with self.lock:
            index = self.getControl(100).getSelectedPosition()
            if index < 0 or index >= len(self.rows): return
            row = dict(self.rows[index])
        details = '%s\n%s\n%s' % (status_text(row), row['destination'], row['message'])
        if row['status'] in ACTIVE:
            if control.dialog.yesno('Cancel download?', row['title'] + '\n' + details,
                                    nolabel='Keep downloading', yeslabel='Cancel download'):
                self.store.cancel(row['id'])
        else:
            options = ['View details', 'Remove from list']
            if row.get('can_resume') and row['status'] in ('Failed', 'Interrupted', 'Cancelled'):
                options.append('Resume download')
            choice = control.dialog.select(row['title'], options)
            if choice == 0:
                control.dialog.textviewer(row['title'], details)
            elif choice == 1:
                try:
                    with self.lock:
                        self.store.remove(row['id'])
                        self.render()
                except Exception:
                    control.notification(title='Downloads', message='Unable to remove this history entry.', icon='ERROR')
            elif choice == 2 and len(options) > 2:
                from urllib.parse import quote_plus
                control.execute('RunPlugin(plugin://plugin.video.umbrella/?action=downloadResume&id=%s)' % quote_plus(row['id']))

    def onAction(self, action):
        if action.getId() in (9, 10, 92):
            self.stopped.set()
            self.close()

    def run(self):
        try: self.doModal()
        finally:
            self.stopped.set()
            if self.worker: self.worker.join(timeout=6)
