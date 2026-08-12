# -*- coding: utf-8 -*-
"""
    Umbrella Deepbrid cloud scraper.

    Deepbrid's torrent API exposes one-time short links but no per-file
    metadata. This scraper therefore caches only stable file metadata
    (index/name/size), never the short URLs themselves. Playback resolves
    the cached index against a fresh Deepbrid response.
"""

from resources.lib.cloud_scrapers import cloud_utils
from resources.lib.debrid.deepbrid import Deepbrid
from resources.lib.modules.source_utils import (
    supported_video_extensions,
    seas_ep_filter
)
from resources.lib.modules import scrape_utils as sc_utils


class source:
    priority = 0
    pack_capable = False
    hasMovies = True
    hasEpisodes = True

    def __init__(self):
        self.language = ['en']

    @staticmethod
    def _progress(item):
        try:
            return int(item.get('progress') or 0)
        except Exception:
            return 0

    @staticmethod
    def _year_matches(year, *names):
        if not year:
            return True

        try:
            years = (
                str(int(year) - 1),
                str(int(year)),
                str(int(year) + 1)
            )
        except Exception:
            return True

        text = ' '.join(
            cloud_utils.release_title_format(name or '')
            for name in names
        )
        return any(value in text for value in years)

    @staticmethod
    def _cloud_title_matches(title, aliases, file_name, folder_name):
        return (
            cloud_utils.cloud_check_title(title, aliases, file_name)
            or cloud_utils.cloud_check_title(title, aliases, folder_name)
        )

    def _append_source(
        self,
        sources,
        data,
        title,
        aliases,
        episode_title,
        hdlr,
        folder_name,
        file_item,
        url,
        file_hash=''
    ):
        name = file_item.get('filename') or file_item.get('name') or ''
        if not name:
            return

        lower_name = name.lower()
        if not lower_name.endswith(tuple(supported_video_extensions())):
            return

        # M2TS folders need a largest-file heuristic that Deepbrid's torrent
        # metadata endpoint cannot provide. Skip them rather than emit a
        # potentially wrong automatic source.
        if lower_name.endswith('.m2ts'):
            return

        rt = cloud_utils.release_title_format(name)
        if any(value in rt for value in cloud_utils.extras_filter()):
            return

        is_episode = 'tvshowtitle' in data
        if is_episode:
            if not seas_ep_filter(data['season'], data['episode'], name):
                return
        elif not self._year_matches(data.get('year'), name, folder_name):
            return

        if not self._cloud_title_matches(
            title,
            aliases,
            name,
            folder_name
        ):
            return

        name_info = sc_utils.info_from_name(
            name,
            title,
            data.get('year'),
            hdlr,
            episode_title
        )
        quality, info = sc_utils.get_release_quality(name_info, name)

        size = file_item.get('size') or 0
        try:
            dsize, isize = sc_utils.convert_size(size, to='GB')
            info.insert(0, isize)
        except Exception:
            dsize = 0

        sources.append({
            'provider': 'db_cloud',
            'source': 'cloud',
            'debrid': 'Deepbrid',
            'seeders': '',
            'hash': file_hash or '',
            'name': name,
            'name_info': name_info,
            'quality': quality,
            'language': 'en',
            'url': url,
            'info': ' / '.join(info),
            'direct': True,
            'debridonly': True,
            'size': dsize
        })

    def sources(self, data, hostDict):
        sources = []
        if not data:
            return sources

        try:
            title = (
                data['tvshowtitle']
                if 'tvshowtitle' in data
                else data['title']
            )
            title = title.replace('&', 'and').replace(
                'Special Victims Unit',
                'SVU'
            )
            aliases = data.get('aliases') or []
            episode_title = (
                data.get('title')
                if 'tvshowtitle' in data
                else None
            )
            hdlr = (
                'S%02dE%02d' % (
                    int(data['season']),
                    int(data['episode'])
                )
                if 'tvshowtitle' in data
                else data.get('year')
            )
            db = Deepbrid()
        except Exception:
            from resources.lib.modules import log_utils
            log_utils.error('DB_CLOUD: ')
            return sources

        # Torrent cloud. Filter on the torrent display name before asking for
        # cached file metadata so unrelated large packs are never probed.
        try:
            for folder in db.torrent_list():
                folder_name = folder.get('filename') or ''
                links = folder.get('links') or []
                request_id = folder.get('id')

                if (
                    request_id in (None, '')
                    or self._progress(folder) < 100
                    or not links
                ):
                    continue

                if not cloud_utils.cloud_check_title(
                    title,
                    aliases,
                    folder_name
                ):
                    continue

                metadata = db.cached_torrent_file_metadata(
                    request_id,
                    len(links),
                    folder_name
                )
                files = metadata.get('files') or []
                expected_count = metadata.get('count') or len(links)

                for file_item in files:
                    index = file_item.get('index')
                    if index is None:
                        continue
                    stable_url = 'dbt,%s,%s,%s' % (
                        request_id,
                        index,
                        expected_count
                    )
                    self._append_source(
                        sources,
                        data,
                        title,
                        aliases,
                        episode_title,
                        hdlr,
                        folder_name,
                        file_item,
                        stable_url,
                        file_hash=folder.get('hash') or ''
                    )
        except Exception:
            from resources.lib.modules import log_utils
            log_utils.error('DB_CLOUD torrent: ')

        # Usenet cloud. The upload list has titles but file metadata is only
        # available from the per-upload info endpoint, so apply the same
        # folder-name prefilter before consulting the metadata cache.
        try:
            for upload in db.usenet_uploads():
                upload_id = upload.get('id')
                folder_name = upload.get('title') or ''
                if upload_id in (None, ''):
                    continue

                if not cloud_utils.cloud_check_title(
                    title,
                    aliases,
                    folder_name
                ):
                    continue

                metadata = db.cached_usenet_file_metadata(
                    upload_id,
                    folder_name
                )
                files = metadata.get('files') or []
                expected_count = metadata.get('count') or 0

                for file_item in files:
                    index = file_item.get('index')
                    if index is None:
                        continue
                    stable_url = 'dbu,%s,%s,%s' % (
                        upload_id,
                        index,
                        expected_count
                    )
                    self._append_source(
                        sources,
                        data,
                        title,
                        aliases,
                        episode_title,
                        hdlr,
                        folder_name,
                        file_item,
                        stable_url,
                        file_hash=upload.get('hash') or ''
                    )
        except Exception:
            from resources.lib.modules import log_utils
            log_utils.error('DB_CLOUD Usenet: ')

        # A single cloud file should only be emitted once even if metadata
        # happens to contain duplicate display names.
        unique = []
        seen = set()
        for item in sources:
            key = (item.get('name'), item.get('url'))
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    def resolve(self, url):
        try:
            kind, request_id, index, expected_count = str(url).split(',', 3)
            db = Deepbrid()

            if kind == 'dbt':
                return db.resolve_cloud_torrent_file(
                    request_id,
                    index,
                    expected_count
                )
            if kind == 'dbu':
                return db.resolve_cloud_usenet_file(
                    request_id,
                    index,
                    expected_count
                )
        except Exception:
            from resources.lib.modules import log_utils
            log_utils.error('DB_CLOUD resolve: ')
        return None
