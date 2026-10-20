"""Portable settings backups with explicit, dependency-based account consent.

This explicit list is intentional: new settings must be reviewed before they can
be exported. Do not replace it with a credential-name blacklist or prefix match.
"""
import json
import math
from datetime import datetime
from xml.etree import ElementTree


ALLOWED_SETTINGS = frozenset("""
appearance.1
icon.logos
index.labels
highlight.color
api.language
mpa.country
mpa.prefix
useLanguageforOriginal
useOriginCountries
originCountry
searchmovie.indexer
searchtv.indexer
page.item.limit
search.page.limit
fanart
enable.fanarttv
prefer.tmdbArt
tmdb.imageResolutions
prefer.fanarttv
hidecinema
hidecinema.rollback
movie.unaired.identify
enable.umbrellahidewatched
notification.sound
general.checkAddonUpdates
umbrella.autostart
enable.containerTitles
favourite.refreshwidgets
favourite.refreshcontainer
movies.showyear
sort.movies.tmdblist.type
sort.movies.tmdblist.order
sort.movies.type
sort.movies.order
sort.collections.type
sort.collections.order
sort.movies.plantowatch.type
sort.movies.plantowatch.order
sort.movies.watchlist.type
sort.movies.watchlist.order
sort.movies.favourites.type
sort.movies.favourites.order
sort.movies.history.type
sort.movies.history.order
dialogs.useumbrelladialog
dialogs.lightordarkmode
dialogs.customcolor
dialogs.usecolortitle
dialogs.titlebar.color
dialogs.button.color
flatten.tvshows
flatten.desc
tv.specials
tvshows.show.year
showunaired
unaired.identify
multi.unwatched.enabled
tvshows.calendar.extended
tvshows.progress.watched
tvshows.episodecount
sort.shows.tmdblist.type
sort.shows.tmdblist.order
sort.shows.type
sort.shows.order
sort.shows.plantowatch.type
sort.shows.plantowatch.order
sort.shows.watchlist.type
sort.shows.watchlist.order
sort.progress.type
sort.progress.order
sort.watched.type
sort.watched.order
sort.shows.favourite.type
sort.shows.favourite.order
tvshows.air.enabled
tvshows.air.zone
tvshows.air.location
tvshows.air.format
tvshows.air.day
tvshows.air.time
tvshows.air.bold
bookmarks
bookmarks.auto
skip.intro.enable
skip.recap.enable
skip.intro.auto
skip.recap.auto
crefresh
markwatched.percent
enable.playnext
umbrella.multiSeason
playnext.theme
playnext.background.color
enable.playnext.theme
playnext.method
playnext.segment.fallback
playnext.time
playnext.percent
playnext.min.seconds
playnext.sub.backupmethod
playnext.sub.seconds
playnext.sub.percent
playnext.default.action
playnext.hidebutton
stillwatching.count
stillwatching.default.action
source.prioritize.hdrdv
source.prioritize.dolbyvisionfirst
source.prioritize.av1
source.prioritize.hevc
hosts.quality
source.checkReboots
source.filtermbysize
source.movie.linespeed
source.min.moviesize
source.max.moviesize
source.filterebysize
source.min.epsize
source.max.epsize
source.episode.linespeed
remove.duplicates
remove.duplicates.logging
remove.duplicates.popup
torrent.remove.uncached
sources.nocachepopup
sources.retryall
remove.dolby.vision
remove.hdr
remove.hevc
remove.av1
remove.atvp
remove.avc
remove.aiupscaled.sources
remove.divx
remove.mp4
remove.mpeg
remove.wmv
remove.cam.sources
remove.sd.sources
remove.3D.sources
torrent.min.seeders
remove.audio.opus
remove.audio.dd
remove.audio.ddplus
remove.audio.atmos
remove.audio.ddtruehd
remove.audio.dts
remove.audio.dtshd
remove.audio.dtshdma
remove.audio.dtsx
remove.audio.aac
remove.audio.mp3
remove.channel.2ch
remove.channel.6ch
remove.channel.7ch
remove.channel.8ch
play.mode
play.mode.movie
play.mode.tv
rescrape.default
rescrape.default2
scrapers.prioritize
cf.disable
imdb.Moviemeta.check
imdb.Movietitle.check
imdb.Movieyear.check
imdb.Showmeta.check
imdb.Showtitle.check
imdb.Showyear.check
sources.useTitleSubs
progress.dialog
sources.dialog.fanartBG
scrapers.timeout
scraper.dialog.color
terminate.onCloud.sources
preemptive.termination.movie
preemptive.limit.movie
preemptive.res.movie
preemptive.termination.tv
preemptive.limit.tv
preemptive.res.tv
sources.select.fanartBG
sources.highlightmethod
sources.highlight.color
sources.real-debrid.color
sources.alldebrid.color
sources.offcloud.color
sources.premiumize.me.color
sources.torbox.color
sources.easynews.color
sources.plexshare.color
sources.gdrive.color
sources.filepursuit.color
sources.usecoloricons
sources.sort.order
source.prefer.smaller
cloud.sources.first
uncached.seeder.sort
autoplay.sd
sources.useonlyone
sources.backbutton
scrobble.notify
trakt.markwatched
simkl.markwatched
mdblist.markwatched
custom.markwatched
floppy.markwatched
scrob.markwatched
punchplay.markwatched
services.directProgress.scrape
services.progressFlatten
services.paginate.lists
services.general.notifications
simkl.progressFlatten
simkl.progress.showunaired
simkl.UpcomingProgress.prependDate
simkl.service.syncInterval
simkl.progress.episodes
simkl.progress.shows
background.service.syncInterval
trakt.server.notifications
trakt.useLanguage
trakt.rating
trakt.progress.showunaired
trakt.UpcomingProgress.prependDate
trakt.collection.hideWatched
trakt.lists.showowner
trakt.progress.episodes
trakt.progress.shows
mdblist.service.syncInterval
mdblist.progressFlatten
mdblist.progress.showunaired
mdblist.UpcomingProgress.prependDate
mdblist.progress.episodes
mdblist.progress.shows
floppy.readonly
floppy.service.syncInterval
floppy.progress.showunaired
floppy.UpcomingProgress.prependDate
scrob.service.syncInterval
punchplay.service.syncInterval
punchplay.progress.showunaired
alldebrid.enable
alldebridexpirynotice
alldebrid.priority
alldebrid.saveToCloud
ad_cloud.enabled
ad_cloud.ignore.m2ts
alldebrid.server.notifications
offcloud.enable
offcloud.priority
oc_cloud.enabled
premiumize.enable
premiumizeexpirynotice
premiumize.priority
premiumize.saveToCloud
pm_cloud.enabled
pm_cloud.ignore.m2ts
premiumize.server.notifications
realdebrid.alternateapi
realdebrid.enable
realdebridexpirynotice
realdebrid.priority
realdebrid.saveToCloud
realdebrid.filter.filename
rd_cloud.enabled
rd_cloud.ignore.m2ts
realdebrid.server.notifications
torbox.enable
torbox.priority
torbox.saveToCloud
tb_cloud.enabled
provider.external.enabled
plexshare.enable
plexshare.priority
easynews.enable
easynews.moderation
easynews.title.chk
easynews.seekable
easynews.priority
filepursuit.enable
filepursuit.priority
gdrive.enable
gdrive.title.chk
gdrive.priority
tmdb.paginate.lists
library.general.notification
library.service.update
library.import.hours
library.service.notification
library.autoimportlists
library.update
library.check
library.importdelay
library.include_specials
library.include_unknown
library.include_unaired
library.strm.use_tmdbhelper
downloads
downloads.file.format
torrent.cacheprogress.dialog
simkl.general.notifications
simkl.directProgress.scrape
simkl.paginate.lists
trakt.general.notifications
trakt.directProgress.scrape
trakt.progressFlatten
trakt.paginate.lists
trakt.HiddenManager.hideWatched
mdblist.general.notifications
mdblist.paginate.lists
mdblist.directProgress.scrape
custom.general.notifications
custom.directProgress.scrape
custom.paginate.lists
floppy.general.notifications
floppy.paginate.lists
floppy.directProgress.scrape
scrob.general.notifications
scrob.paginate.lists
scrob.directProgress.scrape
punchplay.general.notifications
punchplay.paginate.lists
punchplay.directProgress.scrape
subtitles
subtitles.notification
subtitles.prefer.embedded
subtitles.prefer.hearing_impaired
subtitles.prefer.forced
subtitles.utf
subtitles.lang.1
subtitles.lang.2
cache.tmdblist
cache.tmdbcollection
cache.tmdbrecentday
cache.tmdbrecentweek
cache.traktunfinished
cache.traktprogress
cache.trakthistory
cache.traktpopular
cache.trakttrending
cache.traktother
cache.traktuserlist
cache.mdblist
cache.simkl
cache.providers
context.umbrella.addtoLibrary
context.umbrella.addtoFavourite
context.umbrella.artworkCustomize
context.umbrella.libMdblistManager
context.umbrella.addLibtoFavourite
context.umbrella.playTrailer
context.umbrella.playTrailerSelect
context.umbrella.traktManager
context.umbrella.mdblistManager
context.umbrella.simklManager
context.umbrella.customManager
context.umbrella.floppyManager
context.umbrella.scrobManager
context.umbrella.punchplayManager
context.umbrella.tmdbListManager
context.umbrella.tmdbWatchlist
context.umbrella.clearProviders
context.umbrella.clearBookmark
context.umbrella.rescrape
context.umbrella.rescrape2
context.umbrella.rescrape3
context.umbrella.playFromHere
context.umbrella.autoPlay
context.umbrella.sourceSelect
context.umbrella.findSimilar
context.umbrella.browseSeries
context.umbrella.browseEpisodes
enable.umbrellawidgetcontext
context.useUmbrellaContext
""".split())

FORMAT = 'umbrella-preferences'
VERSION = 1
MAX_BACKUP_BYTES = 1024 * 1024


def preference_types(schema):
    root = ElementTree.fromstring(schema)
    return {node.get('id'): node.get('type') for node in root.iter('setting')
            if node.get('id') in ALLOWED_SETTINGS and node.get('type') in ('boolean', 'integer', 'number', 'string')}


def serialize_preferences(get_setting, types):
    values = {key: get_setting(key) for key in sorted(types) if key in ALLOWED_SETTINGS}
    return json.dumps({'format': FORMAT, 'version': VERSION, 'settings': values}, indent=2, ensure_ascii=False)


def parse_preferences(content, types):
    if len(content.encode('utf-8')) > MAX_BACKUP_BYTES:
        raise ValueError('Backup is too large')
    data = json.loads(content)
    if not isinstance(data, dict) or data.get('format') != FORMAT or type(data.get('version')) is not int or data['version'] != VERSION:
        raise ValueError('Unsupported preference backup')
    values = data.get('settings')
    if not isinstance(values, dict):
        raise ValueError('Invalid preference settings')
    result = {}
    for key, value in values.items():
        # Ignore account fields even if someone inserts them into a backup.
        if key not in ALLOWED_SETTINGS or key not in types: continue
        if not isinstance(value, str): raise ValueError('Invalid preference value')
        kind = types[key]
        if kind == 'boolean' and value not in ('true', 'false'):
            raise ValueError('Invalid boolean preference')
        if kind == 'integer': int(value)
        if kind == 'number' and not math.isfinite(float(value)):
            raise ValueError('Invalid numeric preference')
        result[key] = value
    if not result: raise ValueError('No supported preferences in backup')
    return result


def apply_preferences(values, get_setting, set_setting):
    if any(key not in ALLOWED_SETTINGS for key in values):
        raise ValueError('Unsupported preference')
    previous = {key: get_setting(key) for key in values}
    try:
        for key, value in values.items():
            if set_setting(key, value) is False: raise RuntimeError('Preference write failed')
    except Exception:
        for key, value in previous.items():
            set_setting(key, value)
        raise


def _read(control, path):
    handle = control.openFile(path)
    try:
        if handle.size() > MAX_BACKUP_BYTES: raise ValueError('Backup is too large')
        return handle.read()
    finally:
        handle.close()


def _write(control, path, content):
    handle = control.openFile(path, 'w')
    try:
        if handle.write(content) is False: raise IOError('Backup write failed')
    finally:
        handle.close()
    if _read(control, path) != content: raise IOError('Backup verification failed')


def _types(control):
    return preference_types(_read(control, control.SETTINGS_PATH))


def export_settings():
    from resources.lib.modules import control
    try:
        addon = control.addon()
        def choose(account, reasons):
            options = [control.lang(40837), control.lang(40838), control.lang(40839)]
            heading = '%s: %s' % (ACCOUNT_NAMES[account], ', '.join(reasons))
            selected = control.dialog.select(heading, options)
            return True if selected == 0 else False if selected == 1 else None
        content = serialize_backup(addon.getSetting, _types(control), choose)
        if content is None: return
        included = list(json.loads(content)['accounts'])
        if included:
            message = control.lang(40836) % ', '.join(ACCOUNT_NAMES[key] for key in included)
            if not control.dialog.yesno(control.lang(40830), message): return
        folder = control.dialog.browse(0, control.lang(40830), 'files')
        if not folder: return
        name = 'Umbrella-settings-%s.json' % datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        _write(control, control.joinPath(folder, name), content)
        control.dialog.ok(control.lang(40830), control.lang(40832))
    except Exception:
        control.dialog.ok(control.lang(40830), control.lang(40835))


def import_settings():
    from resources.lib.modules import control
    try:
        path = control.dialog.browse(1, control.lang(40831), 'files', '.json')
        if not path: return
        types = _types(control)
        values, accounts = parse_backup(_read(control, path), types)
        message = control.lang(40833)
        if accounts:
            message += '[CR][CR]' + control.lang(40840) % ', '.join(ACCOUNT_NAMES[key] for key in accounts)
        if not control.dialog.yesno(control.lang(40831), message): return
        addon = control.addon()
        # The automatic disk rollback remains preference-only; account rollback
        # is in memory, so import never silently creates another credential file.
        rollback = control.joinPath(control.dataPath, 'preferences-before-import.json')
        _write(control, rollback, serialize_preferences(addon.getSetting, types))
        apply_backup(values, accounts, addon.getSetting, addon.setSetting)
        control.homeWindow.clearProperty('umbrella_settings')
        control.trigger_widget_refresh(force=True)
        control.dialog.ok(control.lang(40831), control.lang(40834))
    except Exception:
        control.dialog.ok(control.lang(40831), control.lang(40835))


# Only explicitly reviewed account fields can appear in version 2 backups.
ACCOUNT_FIELDS = {
    'trakt': 'trakt.user.name trakt.user.token trakt.refreshtoken trakt.token.expires trakt.authed.clientid trakt.clientid trakt.clientsecret traktuserkey.customenabled trakt.isauthed',
    'simkl': 'simkltoken simklusername simkljoindate',
    'mdblist': 'mdblist.token mdblist.refresh.token',
    'custom': 'dev.enable.custom custom.servicename custom.baseurl custom.clientid custom.clientsecret custom.user.name custom.user.token custom.refreshtoken custom.token.expires custom.isauthed',
    'floppy': 'floppy.baseurl floppy.token floppy.user.name floppy.readonly floppy.isauthed',
    'scrob': 'scrob.baseurl scrob.apikey scrob.accesstoken scrob.refreshtoken scrob.tokenexpiry scrob.isauthed',
    'punchplay': 'punchplay.username punchplay.accesstoken punchplay.refreshtoken punchplay.tokenexpiry punchplay.isauthed punchplay.deviceid',
    'realdebrid': 'realdebridtoken realdebridusername realdebrid.clientid realdebridsecret realdebridrefresh',
    'alldebrid': 'alldebridtoken alldebridusername',
    'premiumize': 'premiumizetoken premiumizeusername',
    'offcloud': 'offcloudtoken offcloud.username offcloudAuthInfo',
    'torbox': 'torboxtoken torbox.username',
    'easynews': 'easynews.user easynews.password',
    'filepursuit': 'filepursuittoken',
    'gdrive': 'gdrivetoken',
    'plexshare': 'plexsharetoken plex.client_id plex.device_id plexshare.sourceTitle plexshare.accessToken plexshare.url',
    'opensubs': 'opensubsusername opensubspassword opensubstoken',
    'tmdb': 'tmdb.apikey tmdb.baseaddress tmdbusername tmdbpassword tmdb.sessionid tmdb.v4.readtoken tmdb.v4.accesstoken tmdb.v4.accountid',
    'fanart': 'fanart_tv.api_key',
}
ACCOUNT_FIELDS = {key: frozenset(value.split()) for key, value in ACCOUNT_FIELDS.items()}
ACCOUNT_NAMES = {'trakt': 'Trakt', 'simkl': 'Simkl', 'mdblist': 'MDBList', 'custom': 'Custom Tracking',
    'floppy': 'Floppy', 'scrob': 'Scrob', 'punchplay': 'PunchPlay', 'realdebrid': 'Real-Debrid',
    'alldebrid': 'AllDebrid', 'premiumize': 'Premiumize', 'offcloud': 'Offcloud', 'torbox': 'TorBox',
    'easynews': 'Easynews', 'filepursuit': 'FilePursuit', 'gdrive': 'Google Drive', 'plexshare': 'Plex',
    'opensubs': 'OpenSubtitles', 'tmdb': 'TMDb', 'fanart': 'Fanart.tv'}
SERVICE_IDS = dict(zip(('1', '2', '3', '4', '5', '6', '7'),
    ('trakt', 'simkl', 'mdblist', 'custom', 'floppy', 'scrob', 'punchplay')))
SELECTORS = {'indicators.alt': 'Watch history and indicators', 'scrobble.source': 'Scrobbling'}


def account_dependencies(get_setting, preferences):
    """Return the active account dependencies, with human-readable reasons."""
    required = {}
    def add(account, reason):
        required.setdefault(account, []).append(reason)
    for key, label in SELECTORS.items():
        account = SERVICE_IDS.get(get_setting(key))
        if account: add(account, label)
    for account in SERVICE_IDS.values():
        key = account + '.markwatched'
        if preferences.get(key) == 'true': add(account, 'Mark watched with this service')
    for account in ('realdebrid', 'alldebrid', 'premiumize', 'offcloud', 'torbox', 'easynews', 'filepursuit', 'gdrive', 'plexshare'):
        if preferences.get(account + '.enable') == 'true': add(account, 'Enabled source provider')
    if preferences.get('subtitles') == 'true': add('opensubs', 'Subtitle downloads')
    # User API keys affect metadata even when no tracking account is selected.
    if get_setting('tmdb.apikey') or get_setting('tmdb.v4.accesstoken'):
        add('tmdb', 'Custom metadata API/account')
    if preferences.get('enable.fanarttv') == 'true' and get_setting('fanart_tv.api_key'):
        add('fanart', 'Fanart.tv artwork')
    return required


def dependent_keys(account, preferences, get_setting):
    keys = {key for key in preferences if key.startswith(account + '.')}
    keys.add(account + '.enable')
    for key in SELECTORS:
        if SERVICE_IDS.get(get_setting(key)) == account: keys.add(key)
    if account == 'opensubs': keys.update(key for key in preferences if key.startswith('subtitles'))
    if account == 'fanart': keys.update(('enable.fanarttv', 'prefer.fanarttv'))
    return keys


def serialize_backup(get_setting, types, choose):
    preferences = json.loads(serialize_preferences(get_setting, types))['settings']
    for key in SELECTORS:
        value = get_setting(key)
        if value in ('0', *SERVICE_IDS): preferences[key] = value
    accounts = {}
    for account, reasons in account_dependencies(get_setting, preferences).items():
        decision = choose(account, reasons) if account_ready(account, get_setting) else False
        if decision is None: return None
        if decision and account_ready(account, get_setting):
            accounts[account] = {key: get_setting(key) for key in sorted(ACCOUNT_FIELDS[account])}
        else:
            for key in dependent_keys(account, preferences, get_setting): preferences.pop(key, None)
    return json.dumps({'format': FORMAT, 'version': 2, 'settings': preferences, 'accounts': accounts},
        indent=2, ensure_ascii=False)


def parse_backup(content, types):
    if len(content.encode('utf-8')) > MAX_BACKUP_BYTES: raise ValueError('Backup is too large')
    data = json.loads(content)
    if not isinstance(data, dict): raise ValueError('Invalid backup')
    if data.get('version') == 1:
        return parse_preferences(content, types), {}
    if data.get('format') != FORMAT or type(data.get('version')) is not int or data['version'] != 2:
        raise ValueError('Unsupported backup')
    settings = data.get('settings')
    accounts = data.get('accounts')
    if not isinstance(settings, dict) or not isinstance(accounts, dict): raise ValueError('Invalid backup')
    values = parse_preferences(json.dumps({'format': FORMAT, 'version': 1, 'settings': settings}), types)
    for key in SELECTORS:
        if key in settings:
            if settings[key] not in ('0', *SERVICE_IDS): raise ValueError('Invalid service selection')
            values[key] = settings[key]
    validated = {}
    for account, fields in accounts.items():
        if account not in ACCOUNT_FIELDS or not isinstance(fields, dict): raise ValueError('Unknown account')
        if any(key not in ACCOUNT_FIELDS[account] or not isinstance(value, str) for key, value in fields.items()):
            raise ValueError('Invalid account fields')
        validated[account] = fields
    # Missing/incomplete accounts must not activate dependent settings on import.
    # This also handles edited backups that bypass the export wizard.
    for account in account_dependencies(values.get, values):
        if account not in validated or not account_ready(account, validated[account].get):
            for key in dependent_keys(account, values, values.get): values.pop(key, None)
    return values, validated


def apply_backup(values, accounts, get_setting, set_setting):
    allowed = ALLOWED_SETTINGS | SELECTORS.keys()
    combined = dict(values)
    if any(key not in allowed for key in values): raise ValueError('Invalid preferences')
    for account, fields in accounts.items():
        if account not in ACCOUNT_FIELDS or any(key not in ACCOUNT_FIELDS[account] for key in fields):
            raise ValueError('Invalid account')
        combined.update(fields)
    previous = {key: get_setting(key) for key in combined}
    try:
        # Credentials first, service selectors last.
        for key in sorted(combined, key=lambda key: key in SELECTORS):
            if set_setting(key, combined[key]) is False: raise RuntimeError('Settings write failed')
        labels = {'indicators.alt': 'indicators', 'scrobble.source': 'scrobble'}
        for key, label in labels.items():
            if key in values:
                previous[label] = get_setting(label)
                name = ACCOUNT_NAMES.get(SERVICE_IDS.get(values[key]), 'Local')
                if set_setting(label, name) is False: raise RuntimeError('Settings write failed')
    except Exception:
        for key, value in previous.items():
            try: set_setting(key, value)
            except Exception: pass
        raise


def account_ready(account, get_setting):
    required = {
        'trakt': (('trakt.user.name',), ('trakt.user.token',), ('trakt.refreshtoken',)),
        'simkl': (('simkltoken',),), 'mdblist': (('mdblist.token',),),
        'custom': (('custom.baseurl',), ('custom.user.name',), ('custom.user.token',), ('dev.enable.custom',)),
        'floppy': (('floppy.baseurl',), ('floppy.token',)),
        'scrob': (('scrob.baseurl',), ('scrob.apikey', 'scrob.accesstoken', 'scrob.refreshtoken')),
        'punchplay': (('punchplay.accesstoken', 'punchplay.refreshtoken'),),
        'realdebrid': (('realdebridtoken',),), 'alldebrid': (('alldebridtoken',),),
        'premiumize': (('premiumizetoken',),), 'offcloud': (('offcloudtoken',),), 'torbox': (('torboxtoken',),),
        'easynews': (('easynews.user',), ('easynews.password',)), 'filepursuit': (('filepursuittoken',),),
        'gdrive': (('gdrivetoken',),), 'plexshare': (('plexsharetoken', 'plexshare.accessToken'),),
        'opensubs': (('opensubsusername',), ('opensubspassword',)),
        'tmdb': (('tmdb.apikey', 'tmdb.v4.accesstoken', 'tmdb.v4.readtoken'),), 'fanart': (('fanart_tv.api_key',),),
    }
    if account == 'custom' and get_setting('dev.enable.custom') != 'true': return False
    return all(any(get_setting(key) for key in alternatives) for alternatives in required[account])
