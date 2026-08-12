# -*- coding: utf-8 -*-
"""
    Deepbrid debrid module for Umbrella.

    Deepbrid API:
    https://www.deepbrid.com/api-docs
"""

import time
import os
import re
import requests

from sys import argv
from resources.lib.modules import (
    control,
    log_utils
)
from resources.lib.database import cache
from urllib.parse import urlparse, unquote, quote_plus
from resources.lib.modules.source_utils import (
    seas_ep_filter,
    extras_filter,
    supported_video_extensions
)
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed
)

BASE_URL = 'https://www.deepbrid.com/api/v1/'
USER_AGENT = 'Umbrella-Deepbrid/1.3'

VIDEO_EXTENSIONS = tuple(supported_video_extensions())

deepbrid_icon = control.joinPath(control.artPath(), 'deepbrid.png')
if not control.existsPath(deepbrid_icon):
    deepbrid_icon = control.addonIcon()

addon_fanart = control.addonFanart()


class Deepbrid:
    name = 'Deepbrid'

    def __init__(self):
        self.api_key = control.setting('deepbrid.token').strip()
        self.timeout = 30.0

        try:
            self.sort_priority = int(control.setting('deepbrid.priority') or '10')
        except:
            self.sort_priority = 10

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'application/json'
        })

        self._set_auth(self.api_key)

    # -------------------------------------------------
    # Internal helpers
    # -------------------------------------------------

    def _torrent_list(self):
        result = self._get('torrents/info', silent=True)

        if not isinstance(result, dict):
            return []

        return [
            value for value in result.values()
            if isinstance(value, dict) and value.get('id')
        ]

    def torrent_list(self):
        return self._torrent_list()

    def _probe_torrent_links(self, links, indexes=None):
        if not links:
            return []

        if indexes is None:
            indexed_links = list(enumerate(links))
        else:
            indexed_links = [
                (int(index), link)
                for index, link in zip(indexes, links)
            ]

        if not indexed_links:
            return []

        results = []

        # Keep concurrency conservative. These requests follow the file-host
        # redirect and can be substantially slower than filename-only probes.
        workers = min(4, len(indexed_links))

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    self._probe_torrent_link,
                    link,
                    index
                ): index
                for index, link in indexed_links
            }

            for future in as_completed(futures):
                index = futures[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    log_utils.log(
                        'Deepbrid probe worker failed: index=%s error=%s' % (
                            index,
                            type(e).__name__
                        ),
                        level=log_utils.LOGWARNING
                    )

        results.sort(key=lambda item: item.get('index', 0))
        return results

    def _probe_torrent_link(self, link, index):
        response = None

        try:
            response = requests.get(
                link,
                headers={
                    'Range': 'bytes=0-0',
                    'Accept-Encoding': 'identity'
                },
                allow_redirects=True,
                stream=True,
                timeout=(10, 60)
            )

            filename = self._filename_from_headers(response)
            content_type = (
                response.headers.get('Content-Type', '')
                .split(';', 1)[0]
                .strip()
                .lower()
            )

            size = 0
            content_range = response.headers.get('Content-Range', '')
            if '/' in content_range:
                try:
                    size = int(content_range.rsplit('/', 1)[1])
                except Exception:
                    pass

            if not size:
                try:
                    size = int(response.headers.get('Content-Length') or 0)
                except Exception:
                    pass

            # Do not retain or log Deepbrid/CDN one-time URLs. Callers only
            # need stable selection metadata from a probe.
            result = {
                'index': index,
                'filename': filename,
                'content_type': content_type,
                'size': size,
                'status': response.status_code
            }

            log_utils.log(
                'Deepbrid file probe: index=%s status=%s filename=%s size=%s' % (
                    index,
                    response.status_code,
                    filename,
                    size
                ),
                level=log_utils.LOGDEBUG
            )
            return result

        except Exception as e:
            log_utils.log(
                'Deepbrid file probe failed: index=%s error=%s' % (
                    index,
                    type(e).__name__
                ),
                level=log_utils.LOGWARNING
            )
            return None

        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass

    def _probe_torrent_link_name(self, link, index):
        response = None

        try:
            # Filename-only probe: never follow the one-time redirect to the
            # file host. The redirect path is enough to recover the filename.
            response = requests.get(
                link,
                headers={
                    'Range': 'bytes=0-0',
                    'Accept-Encoding': 'identity'
                },
                allow_redirects=False,
                stream=True,
                timeout=(5, 10)
            )

            location = response.headers.get('Location') or ''
            filename = None
            if location:
                try:
                    path = unquote(urlparse(location).path)
                    filename = os.path.basename(path)
                except Exception:
                    pass

            # Keep the redirect URL local only. It is one-time data and should
            # never enter probe dictionaries or debug logs.
            result = {
                'index': index,
                'filename': filename,
                'status': response.status_code
            }

            log_utils.log(
                'Deepbrid fast file probe: index=%s status=%s filename=%s' % (
                    index,
                    response.status_code,
                    filename
                ),
                level=log_utils.LOGDEBUG
            )
            return result

        except Exception as e:
            log_utils.log(
                'Deepbrid fast probe failed: index=%s error=%s' % (
                    index,
                    type(e).__name__
                ),
                level=log_utils.LOGWARNING
            )
            return None

        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass

    def _probe_torrent_link_names(self, links):
        if not links:
            return []

        results = []
        workers = min(8, len(links))

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    self._probe_torrent_link_name,
                    link,
                    index
                ): index
                for index, link in enumerate(links)
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    log_utils.log(
                        'Deepbrid cloud probe failed: index=%s error=%s' % (
                            futures[future],
                            type(e).__name__
                        ),
                        level=log_utils.LOGWARNING
                    )

        results.sort(key=lambda item: item.get('index', 0))
        return results

    def torrent_file_metadata(
        self,
        request_id,
        expected_count=0,
        torrent_name=''
    ):
        """Return stable torrent file metadata without caching short URLs."""
        info = self.torrent_info(request_id)
        if not isinstance(info, dict):
            return {}

        error = info.get('error')
        if error not in (None, 0, '0', False):
            return {}

        try:
            progress = int(info.get('progress') or 0)
        except Exception:
            progress = 0

        links = info.get('links') or []
        if progress < 100 or not links:
            return {}

        try:
            expected_count = int(expected_count or len(links))
        except Exception:
            expected_count = len(links)

        if expected_count != len(links):
            return {}

        probes = self._probe_torrent_link_names(links)
        by_index = {
            item.get('index'): item
            for item in probes
            if isinstance(item, dict) and item.get('index') is not None
        }

        # Retry only the entries whose short redirect did not reveal a name.
        # This keeps the initial metadata build robust without following the
        # CDN/file-host redirect or re-probing the whole pack.
        missing = [
            index for index in range(len(links))
            if not (by_index.get(index) or {}).get('filename')
        ]
        if missing:
            with ThreadPoolExecutor(
                max_workers=min(4, len(missing))
            ) as executor:
                futures = {
                    executor.submit(
                        self._probe_torrent_link_name,
                        links[index],
                        index
                    ): index
                    for index in missing
                }
                for future in as_completed(futures):
                    try:
                        item = future.result()
                        if item:
                            by_index[item.get('index')] = item
                    except Exception:
                        pass

        files = []
        for index in range(len(links)):
            filename = (by_index.get(index) or {}).get('filename') or ''
            if not filename and len(links) == 1:
                filename = info.get('filename') or torrent_name or ''
            files.append({
                'index': index,
                'filename': filename
            })

        named_count = len([item for item in files if item.get('filename')])
        if not named_count:
            return {}

        log_utils.log(
            'Deepbrid torrent metadata scan: id=%s files=%s named=%s' % (
                request_id,
                len(files),
                named_count
            ),
            level=log_utils.LOGDEBUG
        )

        return {
            'count': len(links),
            'files': files
        }

    def cached_torrent_file_metadata(
        self,
        request_id,
        expected_count=0,
        torrent_name=''
    ):
        # File ordering/names are stable, while Deepbrid's short URLs are
        # explicitly one-time. Cache only index/name metadata for 24 hours.
        return cache.get(
            self.torrent_file_metadata,
            24,
            str(request_id),
            int(expected_count or 0),
            str(torrent_name or '')
        ) or {}

    def _find_episode_file(self, links, season, episode):
        if not links:
            return None

        # Probe small batches and stop as soon as the requested episode is
        # found. A failed/no-filename short-link probe gets one fast retry,
        # but only when the first pass did not already find the episode.
        batch_size = 8

        for start in range(0, len(links), batch_size):
            batch = list(
                enumerate(
                    links[start:start + batch_size],
                    start=start
                )
            )
            results = {}

            with ThreadPoolExecutor(
                max_workers=min(batch_size, len(batch))
            ) as executor:
                futures = {
                    executor.submit(
                        self._probe_torrent_link_name,
                        link,
                        index
                    ): index
                    for index, link in batch
                }

                for future in as_completed(futures):
                    index = futures[future]
                    try:
                        item = future.result()
                    except Exception:
                        item = None
                    if item:
                        results[index] = item

            matches = [
                item for item in results.values()
                if item.get('filename')
                and seas_ep_filter(
                    season,
                    episode,
                    item.get('filename')
                )
            ]

            if not matches:
                retry_items = [
                    (index, link)
                    for index, link in batch
                    if not (results.get(index) or {}).get('filename')
                ]

                if retry_items:
                    log_utils.log(
                        'Deepbrid retrying fast filename probes: indexes=%s' %
                        [item[0] for item in retry_items],
                        level=log_utils.LOGDEBUG
                    )
                    with ThreadPoolExecutor(
                        max_workers=min(4, len(retry_items))
                    ) as executor:
                        futures = {
                            executor.submit(
                                self._probe_torrent_link_name,
                                link,
                                index
                            ): index
                            for index, link in retry_items
                        }
                        for future in as_completed(futures):
                            index = futures[future]
                            try:
                                item = future.result()
                            except Exception:
                                item = None
                            if item:
                                results[index] = item

                    matches = [
                        item for item in results.values()
                        if item.get('filename')
                        and seas_ep_filter(
                            season,
                            episode,
                            item.get('filename')
                        )
                    ]

            if matches:
                matches.sort(key=lambda item: item.get('index', 0))
                selected = matches[0]
                log_utils.log(
                    'Deepbrid episode fast match: '
                    'S%sE%s index=%s filename=%s' % (
                        str(season).zfill(2),
                        str(episode).zfill(2),
                        selected.get('index'),
                        selected.get('filename')
                    ),
                    level=log_utils.LOGDEBUG
                )
                return selected

        log_utils.log(
            'Deepbrid: no file matched S%sE%s' % (
                str(season).zfill(2),
                str(episode).zfill(2)
            ),
            level=log_utils.LOGWARNING
        )
        return None

    def _find_movie_file(self, links, title=None):
        if not links:
            return None

        # First recover filenames without following Deepbrid's one-time short
        # URLs. This cheaply removes samples/extras/non-video files. Any entry
        # whose filename could not be recovered remains eligible for the old
        # full Range probe so this optimization cannot hide a valid movie.
        name_probes = self._probe_torrent_link_names(links)
        by_index = {
            item.get('index'): item
            for item in name_probes
            if isinstance(item, dict) and item.get('index') is not None
        }

        title_lower = (title or '').lower()
        extras = tuple(
            extra for extra in extras_filter()
            if extra not in title_lower
        )

        candidates = []
        unknown = []
        for index in range(len(links)):
            filename = (by_index.get(index) or {}).get('filename') or ''
            if not filename:
                unknown.append(index)
                continue

            lower_name = filename.lower()
            if not lower_name.endswith(VIDEO_EXTENSIONS):
                continue
            if any(extra in lower_name for extra in extras):
                continue
            candidates.append(index)

        if len(candidates) == 1 and not unknown:
            selected = dict(by_index[candidates[0]])
            selected.setdefault('content_type', '')
            selected.setdefault('size', 0)
            log_utils.log(
                'Deepbrid movie fast match: index=%s filename=%s' % (
                    selected.get('index'),
                    selected.get('filename')
                ),
                level=log_utils.LOGDEBUG
            )
            return selected

        probe_indexes = sorted(set(candidates + unknown))
        if not probe_indexes:
            # Preserve the known-working fallback for unusual files whose
            # extensions do not reveal that they are video.
            probe_indexes = list(range(len(links)))

        log_utils.log(
            'Deepbrid movie full-probe candidates: %s of %s' % (
                len(probe_indexes),
                len(links)
            ),
            level=log_utils.LOGDEBUG
        )

        probes = self._probe_torrent_links(
            [links[index] for index in probe_indexes],
            indexes=probe_indexes
        )
        return self._select_probed_file(probes, title=title)

    def _is_video_probe(self, item):
        filename = (item.get('filename') or '').lower()
        content_type = (item.get('content_type') or '').lower()

        audio_extensions = (
            '.eac3', '.ac3', '.dts', '.aac', '.flac',
            '.mp3', '.m4a', '.wav', '.ogg', '.opus'
        )

        if filename.endswith(audio_extensions):
            return False
        if filename.endswith(VIDEO_EXTENSIONS):
            return True
        if content_type.startswith('video/'):
            return True
        if content_type.startswith('audio/'):
            return False
        return False

    def _filename_from_headers(self, response):
        disposition = response.headers.get(
            'Content-Disposition', ''
        )

        # RFC 5987 form:
        # filename*=UTF-8''Some.Movie.mkv
        match = re.search(
            r"filename\*\s*=\s*UTF-8''([^;]+)",
            disposition,
            re.I
        )

        if match:
            return unquote(
                match.group(1).strip().strip('"')
            )

        # Normal:
        # filename="Some.Movie.mkv"
        match = re.search(
            r'filename\s*=\s*"?([^";]+)"?',
            disposition,
            re.I
        )

        if match:
            return match.group(1).strip()

        # Sometimes the redirect destination itself contains
        # the filename.
        try:
            path = unquote(urlparse(response.url).path)
            name = os.path.basename(path)

            if '.' in name:
                return name
        except Exception:
            pass

        return None

    def _magnet_display_name(self, magnet):
        try:
            query = magnet.split('?', 1)[1]

            for part in query.split('&'):
                if part.startswith('dn='):
                    # Use unquote rather than unquote_plus:
                    # names such as HDR10+ contain a literal '+'.
                    return unquote(part[3:]).strip()
        except Exception:
            pass

        return None

    def _set_auth(self, key):
        self.api_key = (key or '').strip()

        self.session.headers.pop('Authorization', None)
        self.session.headers.pop('X-Api-Key', None)

        if self.api_key:
            self.session.headers['Authorization'] = 'Bearer %s' % self.api_key
            self.session.headers['X-Api-Key'] = self.api_key

    def _request(self, method, endpoint, params=None, data=None,
                 json_data=None, files=None, silent=False, timeout=None):

        url = BASE_URL + endpoint.lstrip('/')
        request_timeout = self.timeout if timeout is None else timeout
        method = method.upper()

        # GET requests are safe to retry. Avoid blindly retrying torrent/
        # Usenet creation POSTs because a timeout or 5xx may happen after
        # Deepbrid has already accepted the transfer.
        safe_post = endpoint.lstrip('/') in (
            'generate/link',
            'generate/folder'
        )
        retry_transient = method == 'GET' or safe_post
        max_attempts = 3

        for attempt in range(max_attempts):
            response = None

            try:
                if method == 'GET':
                    response = self.session.get(
                        url,
                        params=params,
                        timeout=request_timeout
                    )
                else:
                    response = self.session.post(
                        url,
                        params=params,
                        data=data,
                        json=json_data,
                        files=files,
                        timeout=request_timeout
                    )

                status = response.status_code

                if status == 401:
                    if not silent:
                        control.notification(
                            title=self.name,
                            message='Invalid or expired API key',
                            icon='ERROR'
                        )
                    return {
                        'error': 401,
                        'message': 'Invalid or expired API key'
                    }

                if status == 429 and attempt + 1 < max_attempts:
                    try:
                        retry_after = float(
                            response.headers.get('Retry-After') or 1
                        )
                    except Exception:
                        retry_after = 1.0

                    retry_after = max(0.5, min(retry_after, 10.0))
                    if not silent:
                        log_utils.log(
                            'Deepbrid rate limited; retrying in %.1fs' %
                            retry_after,
                            level=log_utils.LOGWARNING
                        )
                    time.sleep(retry_after)
                    continue

                if (
                    retry_transient
                    and status in (500, 502, 503, 504)
                    and attempt + 1 < max_attempts
                ):
                    delay = min(1.0 * (2 ** attempt), 4.0)
                    if not silent:
                        log_utils.log(
                            'Deepbrid HTTP %s; retrying in %.1fs' % (
                                status,
                                delay
                            ),
                            level=log_utils.LOGWARNING
                        )
                    time.sleep(delay)
                    continue

                try:
                    result = response.json()
                except Exception:
                    result = {}

                if status >= 400:
                    if not isinstance(result, dict):
                        result = {}

                    result = dict(result)
                    result.setdefault('error', status)
                    result.setdefault(
                        'message',
                        response.reason or 'HTTP %s' % status
                    )

                    if not silent:
                        log_utils.log(
                            'Deepbrid API error: %s' % result,
                            level=log_utils.LOGWARNING
                        )
                    return result

                if isinstance(result, dict):
                    error = result.get('error')

                    if error not in (None, 0, '0', False):
                        if not silent:
                            log_utils.log(
                                'Deepbrid API error: %s' % result,
                                level=log_utils.LOGWARNING
                            )
                        return result

                return result

            except (requests.exceptions.Timeout,
                    requests.exceptions.ConnectionError) as e:
                if retry_transient and attempt + 1 < max_attempts:
                    delay = min(1.0 * (2 ** attempt), 4.0)
                    if not silent:
                        log_utils.log(
                            'Deepbrid request failed; retrying in %.1fs: %s' % (
                                delay,
                                str(e)
                            ),
                            level=log_utils.LOGWARNING
                        )
                    time.sleep(delay)
                    continue

                if not silent:
                    log_utils.log(
                        'Deepbrid request error: %s' % str(e),
                        level=log_utils.LOGERROR
                    )
                return {
                    'error': 'request_failed',
                    'message': str(e)
                }

            except Exception as e:
                if not silent:
                    log_utils.log(
                        'Deepbrid request error: %s' % str(e),
                        level=log_utils.LOGERROR
                    )
                return {
                    'error': 'request_failed',
                    'message': str(e)
                }

        return {
            'error': 'request_failed',
            'message': 'Deepbrid request failed'
        }

    def _get(self, endpoint, params=None, silent=False, timeout=None):
        return self._request(
            'GET',
            endpoint,
            params=params,
            silent=silent,
            timeout=timeout
        )

    def _post(self, endpoint, data=None, json_data=None,
              files=None, silent=False):
        return self._request(
            'POST',
            endpoint,
            data=data,
            json_data=json_data,
            files=files,
            silent=silent
        )

    # -------------------------------------------------
    # Authentication / Account
    # -------------------------------------------------

    def auth(self):
        control.sleep(200)

        key = control.dialog.input(
            'Deepbrid API Key',
            type=control.alpha_input
        )

        if not key:
            return

        key = key.strip()

        self._set_auth(key)

        info = self.account_info()

        if info and (
            info.get('username') or
            info.get('email') or
            info.get('type')
        ):
            control.setSetting('deepbrid.token', key)
            control.setSetting('deepbrid.enable', 'true')

            control.notification(
                title=self.name,
                message='Deepbrid authorized'
            )

            control.sleep(800)
            control.openSettings(
                '0.0',
                'plugin.video.umbrella'
            )
        else:
            control.notification(
                title=self.name,
                message='Invalid API key',
                icon='ERROR'
            )
            self.remove_auth()

    def remove_auth(self):
        self._set_auth('')

        control.setSetting(
            'deepbrid.token',
            ''
        )
        control.setSetting(
            'deepbrid.enable',
            'false'
        )

        control.notification(
            title=self.name,
            message='Deepbrid authorization removed'
        )

    def account_info(self):
        if not self.api_key:
            return {}

        return self._get('user')

    def account_stats(self):
        if not self.api_key:
            return {}

        return self._get('user/stats')

    def account_limits(self):
        if not self.api_key:
            return {}

        return self._get('user/limits')

    def account_info_to_dialog(self):
        from datetime import datetime

        info = self.account_info()
        if not isinstance(info, dict) or info.get('error'):
            return control.notification(
                title=self.name,
                message='Could not get account info',
                icon='ERROR'
            )

        stats = self.account_stats()
        if not isinstance(stats, dict) or stats.get('error'):
            stats = {}

        lines = []
        if info.get('username'):
            lines.append('Username: %s' % info.get('username'))
        if info.get('email'):
            lines.append('Email: %s' % info.get('email'))
        if info.get('type'):
            lines.append('Account Type: %s' % str(info.get('type')).capitalize())

        expiration = info.get('expiration')
        if expiration:
            expiration_text = str(expiration)
            lines.append('Expiration: %s' % expiration_text)
            try:
                expires = datetime.strptime(expiration_text[:10], '%Y-%m-%d').date()
                days_remaining = (expires - datetime.now().date()).days
                lines.append('Days Remaining: %s' % days_remaining)
            except Exception:
                pass

        if info.get('fidelity_points') is not None:
            lines.append('Fidelity Points: %s' % info.get('fidelity_points'))
        if info.get('maxDownloads') is not None:
            lines.append('Max Downloads: %s' % info.get('maxDownloads'))
        if info.get('maxConnections') is not None:
            lines.append('Max Connections: %s' % info.get('maxConnections'))
        if stats.get('downloads') is not None:
            lines.append('Downloads: %s' % stats.get('downloads'))
        if stats.get('bandwidth'):
            lines.append('Bandwidth Used: %s' % stats.get('bandwidth'))
        if stats.get('torrents') is not None:
            lines.append('Torrents: %s' % stats.get('torrents'))
        if stats.get('remote') is not None:
            lines.append('Remote Uploads: %s' % stats.get('remote'))

        if not lines:
            lines.append(str(info))

        return control.selectDialog(lines, heading='Deepbrid Account Info')

    def account_limits_to_dialog(self):
        limits = self.account_limits()
        if not isinstance(limits, dict) or limits.get('error'):
            return control.notification(
                title=self.name,
                message='Could not get hoster limits',
                icon='ERROR'
            )

        hosters = limits.get('hosters') or []
        lines = []
        reset = limits.get('reset')
        if reset:
            lines.append('[B]Reset: %s[/B]' % str(reset).capitalize())

        for item in hosters:
            if not isinstance(item, dict):
                continue
            domain = item.get('domain') or 'Unknown host'
            if item.get('type') == 'bandwidth':
                used = item.get('used_str') or str(item.get('used', 0))
                limit = item.get('limit_str') or str(item.get('limit', 0))
                remaining = item.get('remaining_str') or str(item.get('remaining', 0))
                lines.append('%s: %s / %s (remaining %s)' % (domain, used, limit, remaining))
            else:
                lines.append('%s: %s / %s links (remaining %s)' % (
                    domain,
                    item.get('used', 0),
                    item.get('limit', 0),
                    item.get('remaining', 0)
                ))

        if not lines:
            lines.append('No per-hoster limits reported')
        return control.selectDialog(lines, heading='Deepbrid Hoster Limits')

    def download_history(self, limit=100, offset=0):
        if not self.api_key:
            return {}
        try:
            limit = max(1, min(int(limit), 500))
        except Exception:
            limit = 100
        try:
            offset = max(0, int(offset))
        except Exception:
            offset = 0

        result = self._get('downloads', params={'limit': limit, 'offset': offset})
        if not isinstance(result, dict) or result.get('error'):
            return {}
        return result

    def download_history_to_listitem(self, offset=0, limit=100):
        try:
            offset = max(0, int(offset))
        except Exception:
            offset = 0
        try:
            limit = max(1, min(int(limit), 500))
        except Exception:
            limit = 100
        try:
            syshandle = int(argv[1])
        except Exception:
            return

        result = self.download_history(limit=limit, offset=offset)
        if not result:
            control.notification(
                title=self.name,
                message='Could not get download history',
                icon='ERROR'
            )
            control.directory(syshandle, cacheToDisc=False)
            return

        items = result.get('data') or []
        total = result.get('count')
        try:
            total = int(total)
        except Exception:
            total = offset + len(items)

        sysaddon = 'plugin://plugin.video.umbrella/'
        for index, item in enumerate(items, offset + 1):
            if not isinstance(item, dict):
                continue
            filename = item.get('filename') or 'Unknown file'
            size = item.get('size') or 'Unknown size'
            date = item.get('date') or ''
            original = item.get('original') or ''
            direct = item.get('download') or ''

            label = '%03d | [B]%s[/B] | %s' % (index, filename, size)
            if date:
                label += ' | %s' % date

            listitem = control.item(label=label, offscreen=True)
            listitem.setArt({
                'icon': deepbrid_icon,
                'poster': deepbrid_icon,
                'thumb': deepbrid_icon,
                'fanart': addon_fanart,
                'banner': deepbrid_icon
            })
            plot = 'Size: %s' % size
            if date:
                plot += '[CR]Date: %s' % date
            if original:
                plot += '[CR]Original: %s' % original
            control.set_info(listitem, {'title': filename, 'plot': plot})

            if direct:
                listitem.setProperty('IsPlayable', 'true')
                item_url = '%s?action=db_PlayDownload&url=%s' % (sysaddon, quote_plus(direct))
            else:
                item_url = ''

            control.addItem(
                handle=syshandle,
                url=item_url,
                listitem=listitem,
                isFolder=False
            )

        next_offset = offset + len(items)
        if items and next_offset < total:
            label = '[B]Next Page[/B] (%s-%s of %s)' % (
                next_offset + 1,
                min(next_offset + limit, total),
                total
            )
            listitem = control.item(label=label, offscreen=True)
            listitem.setArt({
                'icon': deepbrid_icon,
                'poster': deepbrid_icon,
                'thumb': deepbrid_icon,
                'fanart': addon_fanart,
                'banner': deepbrid_icon
            })
            control.set_info(listitem, {'title': label})
            control.addItem(
                handle=syshandle,
                url='%s?action=db_DownloadHistory&offset=%s' % (sysaddon, next_offset),
                listitem=listitem,
                isFolder=True
            )

        control.content(syshandle, 'files')
        control.directory(syshandle, cacheToDisc=False)

    # -------------------------------------------------
    # Hoster support
    # -------------------------------------------------

    def unrestrict_link(self, link, returnAll=False):
        if not self.api_key or not link:
            return None

        result = self._post(
            'generate/link',
            data={'link': link}
        )

        if not result:
            return None

        direct = (
            result.get('link') or
            result.get('download') or
            result.get('download_url')
        )

        if not direct:
            return None

        return result if returnAll else direct

    def _fetch_hosts(self):
        result = self._get(
            'hosts',
            silent=True
        )

        hosts = []

        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict):
                    for domain, status in item.items():
                        if not domain:
                            continue

                        if (
                            status
                            and str(status).lower().startswith('down')
                        ):
                            continue

                        hosts.append(str(domain).lower())

        elif isinstance(result, dict) and not result.get('error'):
            data = (
                result.get('hosts') or
                result.get('data') or
                []
            )

            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        for domain, status in item.items():
                            if not domain:
                                continue

                            if (
                                status
                                and str(status).lower().startswith('down')
                            ):
                                continue

                            hosts.append(str(domain).lower())

        return list(set(hosts))

    def get_hosts(self):
        hosts_dict = {
            'Deepbrid': []
        }

        try:
            # Deepbrid exposes live host status, so use a shorter cache than
            # Umbrella's 168-hour RD/PM host cache while still avoiding one
            # /hosts request per candidate host during every scrape.
            hosts = cache.get(
                self._fetch_hosts,
                6
            ) or []

            hosts_dict['Deepbrid'] = hosts

        except:
            log_utils.error()

        return hosts_dict

    def valid_url(self, host):
        try:
            host = (host or '').lower().strip()

            if not host:
                return False

            hosts = self.get_hosts()

            if isinstance(hosts, dict):
                host_list = hosts.get(
                    self.name,
                    []
                )
            else:
                host_list = hosts or []

            for supported in host_list:
                supported = supported.lower()

                if (
                    host == supported or
                    host.endswith('.' + supported)
                ):
                    return True

            return False

        except:
            return False

    # -------------------------------------------------
    # Cache
    # -------------------------------------------------

    def check_cache(self, hashlist):
        """
        Deepbrid does not document a bulk hash-cache endpoint.

        Umbrella therefore treats torrents as unchecked and lets
        Deepbrid perform the transfer when the source is resolved.
        """
        return {}

    def check_cache_single(self, hash_string):
        return {}

    # -------------------------------------------------
    # Torrents
    # -------------------------------------------------

    def add_magnet(self, magnet):
        if not self.api_key or not magnet:
            return None

        magnet = str(magnet).strip()

        if not magnet.lower().startswith('magnet:?'):
            decoded = unquote(magnet)

            if decoded.lower().startswith('magnet:?'):
                magnet = decoded
            else:
                return None

        # Snapshot current torrents both for safe pre-add reuse and so we
        # can identify a newly-created torrent when Deepbrid returns
        # error=0/id=None. /torrents/info does not expose the info hash, so
        # only reuse a unique exact display-name match; never fuzzy-match.
        before = self._torrent_list()
        expected_name = self._magnet_display_name(magnet)

        if expected_name:
            existing_matches = [
                item for item in before
                if str(item.get('filename', '')).strip() == expected_name
            ]

            if len(existing_matches) == 1:
                existing_id = str(existing_matches[0]['id'])
                log_utils.log(
                    'Deepbrid reusing existing torrent before add: '
                    'id=%s filename=%s' % (
                        existing_id,
                        expected_name
                    ),
                    level=log_utils.LOGDEBUG
                )
                return existing_id

        before_ids = {
            str(item.get('id'))
            for item in before
            if item.get('id')
        }

        result = self._post(
            'torrents/add',
            data={'magnet': magnet}
        )

        log_utils.log(
            'Deepbrid add torrent response: %s' % repr(result),
            level=log_utils.LOGDEBUG
        )

        if not isinstance(result, dict):
            return None

        torrent_id = result.get('id')

        if torrent_id:
            return str(torrent_id)

        if result.get('error') != 0:
            log_utils.log(
                'Deepbrid torrent rejected: error=%s message=%s' % (
                    result.get('error'),
                    result.get('message')
                ),
                level=log_utils.LOGWARNING
            )
            return None

        # Deepbrid sometimes returns error=0/id=None for a torrent
        # that already exists (or was added without its ID being returned).
        for attempt in range(3):
            if attempt:
                time.sleep(1)

            after = self._torrent_list()

            # Safest recovery: exactly one new torrent appeared.
            new_torrents = [
                item for item in after
                if str(item.get('id')) not in before_ids
            ]

            if len(new_torrents) == 1:
                recovered_id = str(new_torrents[0]['id'])

                log_utils.log(
                    'Deepbrid recovered newly-created torrent id=%s' %
                    recovered_id,
                    level=log_utils.LOGDEBUG
                )

                return recovered_id

            # Duplicate/add-existing case: match the magnet's display name.
            if expected_name:
                matches = [
                    item for item in after
                    if str(item.get('filename', '')).strip() == expected_name
                ]

                # Don't guess if filenames are ambiguous.
                if len(matches) == 1:
                    recovered_id = str(matches[0]['id'])

                    log_utils.log(
                        'Deepbrid recovered existing torrent id=%s '
                        'filename=%s' % (
                            recovered_id,
                            expected_name
                        ),
                        level=log_utils.LOGDEBUG
                    )

                    return recovered_id

        log_utils.log(
            'Deepbrid returned OK with no torrent ID and recovery failed',
            level=log_utils.LOGWARNING
        )

        return None

    def torrent_info(self, request_id='', timeout=None):
        if request_id:
            return self._get(
                'torrents/info',
                params={'id': request_id},
                timeout=timeout
            )

        return self._get('torrents/info', timeout=timeout)

    def _is_video_link(self, link, filename=''):
        text = '%s %s' % (
            link or '',
            filename or ''
        )

        text = text.lower()

        return any(
            ext in text
            for ext in VIDEO_EXTENSIONS
        )

    def _select_probed_file(
        self,
        probes,
        title=None
    ):
        if not probes:
            return None

        videos = [
            item for item in probes
            if item and self._is_video_probe(item)
        ]

        if not videos:
            log_utils.log(
                'Deepbrid: no video files found after probing',
                level=log_utils.LOGWARNING
            )
            return None

        title_lower = (title or '').lower()

        extras = tuple(
            item for item in extras_filter()
            if item not in title_lower
        )

        movies = []

        for item in videos:
            filename = (
                item.get('filename') or ''
            ).lower()

            if any(extra in filename for extra in extras):
                continue

            movies.append(item)

        if not movies:
            return None

        movies.sort(
            key=lambda item: item.get('size', 0),
            reverse=True
        )

        selected = movies[0]

        log_utils.log(
            'Deepbrid movie file selected: '
            'index=%s filename=%s size=%s' % (
                selected.get('index'),
                selected.get('filename'),
                selected.get('size')
            ),
            level=log_utils.LOGDEBUG
        )

        return selected

    def _select_torrent_link(
            self,
            info,
            title=None,
            season=None,
            episode=None
        ):
        links = info.get('links') or []

        if len(links) == 1:
            probe = self._probe_torrent_link(
                links[0],
                0
            )

            if not probe or not self._is_video_probe(probe):
                log_utils.log(
                    'Deepbrid single-file torrent is not a video: %s' %
                    repr(probe),
                    level=log_utils.LOGWARNING
                )
                return None

            fresh_info = self.torrent_info(
                info.get('id')
            )

            if not isinstance(fresh_info, dict):
                return None

            fresh_links = fresh_info.get('links') or []

            if len(fresh_links) == 1:
                log_utils.log(
                    'Deepbrid returning refreshed single video file: '
                    'id=%s filename=%s' % (
                        info.get('id'),
                        probe.get('filename')
                    ),
                    level=log_utils.LOGDEBUG
                )
                return fresh_links[0]

            log_utils.log(
                'Deepbrid could not safely refresh single-file torrent',
                level=log_utils.LOGWARNING
            )
            return None

        if len(links) > 1:
            is_episode = (
                season not in (None, '')
                and episode not in (None, '')
            )

            if is_episode:
                selected = self._find_episode_file(
                    links,
                    season,
                    episode
                )
            else:
                selected = self._find_movie_file(
                    links,
                    title=title
                )

            if not selected:
                return None

            log_utils.log(
                'Deepbrid selected torrent file: %s' %
                repr(selected),
                level=log_utils.LOGDEBUG
            )

            # Refresh links after probing because Deepbrid describes them as
            # one-time short URLs. File tokens change, so preserve mapping by
            # index only when the refreshed list length is unchanged.
            fresh_info = self.torrent_info(
                info.get('id')
            )

            if not isinstance(fresh_info, dict):
                return None

            fresh_links = fresh_info.get('links') or []
            index = selected.get('index')

            if (
                index is not None
                and len(fresh_links) == len(links)
                and index < len(fresh_links)
            ):
                log_utils.log(
                    'Deepbrid using refreshed file by index=%s' %
                    index,
                    level=log_utils.LOGDEBUG
                )

                return fresh_links[index]

            log_utils.log(
                'Deepbrid could not safely map probed file '
                'to refreshed torrent link',
                level=log_utils.LOGWARNING
            )

        return None

    def resolve_magnet(
        self,
        magnet_url,
        info_hash=None,
        season=None,
        episode=None,
        title=None
    ):
        if not self.api_key or not magnet_url:
            return None

        try:
            deadline = time.monotonic() + 120.0
            last_status_log = 0.0
            last_progress = None
            last_seeders = None
            last_speed = None
            last_links_count = 0

            torrent_id = self.add_magnet(
                magnet_url
            )

            if not torrent_id:
                log_utils.log(
                    'Deepbrid: torrent was not accepted',
                    level=log_utils.LOGWARNING
                )
                return None

            # Deepbrid does not give us a webhook/callback. Poll the
            # documented /torrents/info endpoint, but enforce the timeout
            # using wall-clock time so slow HTTP requests cannot stretch a
            # nominal two-minute poll into a much longer background worker.
            while time.monotonic() < deadline:

                if control.monitor.abortRequested():
                    return None

                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break

                info = self.torrent_info(
                    torrent_id,
                    timeout=max(1.0, min(self.timeout, remaining))
                )

                if not info:
                    remaining = deadline - time.monotonic()
                    if remaining > 0:
                        time.sleep(min(2.0, remaining))
                    continue

                try:
                    error = int(
                        info.get('error', 0)
                    )
                except:
                    error = 0

                if error:
                    log_utils.log(
                        'Deepbrid torrent error: %s' % info,
                        level=log_utils.LOGWARNING
                    )
                    return None

                try:
                    progress = int(
                        info.get('progress', 0)
                    )
                except:
                    progress = 0

                links = info.get('links') or []

                last_progress = progress
                last_seeders = info.get('seeders')
                last_speed = info.get('speed')
                last_links_count = len(links)

                now = time.monotonic()
                if (
                    not last_status_log
                    or now - last_status_log >= 10.0
                    or progress >= 100
                ):
                    log_utils.log(
                        'Deepbrid torrent status: '
                        'id=%s progress=%s seeders=%s speed=%s links=%s' % (
                            torrent_id,
                            progress,
                            last_seeders,
                            last_speed,
                            last_links_count
                        ),
                        level=log_utils.LOGDEBUG
                    )
                    last_status_log = now

                # Deepbrid explicitly states that links are empty
                # until progress reaches 100.
                if progress >= 100 and links:
                    link = self._select_torrent_link(
                        info,
                        title=title,
                        season=season,
                        episode=episode
                    )

                    if link:
                        return link

                    # A completed torrent with multiple links cannot be mapped
                    # to a filename with Deepbrid's current response shape.
                    # Polling again cannot make that selection deterministic.
                    return None

                # Don't hammer the API.
                remaining = deadline - time.monotonic()
                if remaining > 0:
                    time.sleep(min(2.0, remaining))

            log_utils.log(
                'Deepbrid: torrent timed out after polling '
                'id=%s progress=%s seeders=%s speed=%s links=%s' % (
                    torrent_id,
                    last_progress,
                    last_seeders,
                    last_speed,
                    last_links_count
                ),
                level=log_utils.LOGWARNING
            )

            return None

        except Exception as e:
            log_utils.log(
                'Deepbrid resolve_magnet: %s' % str(e),
                level=log_utils.LOGERROR
            )
            return None

    # -------------------------------------------------
    # Usenet
    # -------------------------------------------------

    def add_usenet(
        self,
        nzb_url=None,
        nzb_file=None
    ):
        if not self.api_key:
            return None

        result = None

        if nzb_url:
            nzb_url = str(nzb_url).strip()
            if not nzb_url.lower().startswith(('http://', 'https://')):
                return None
            result = self._post(
                'usenet/add',
                data={'nzb_url': nzb_url}
            )

        elif nzb_file:
            try:
                with open(nzb_file, 'rb') as file_handle:
                    result = self._post(
                        'usenet/add',
                        files={'nzb_file': file_handle}
                    )
            except Exception:
                log_utils.error()
                return None

        log_utils.log(
            'Deepbrid add Usenet response: %s' % repr(result),
            level=log_utils.LOGDEBUG
        )

        if not isinstance(result, dict):
            return None

        error = result.get('error')
        if error not in (None, 0, '0', False):
            return None

        return result

    def usenet_uploads(self):
        result = self._get('usenet/uploads')

        if not isinstance(result, dict):
            return []

        error = result.get('error')
        if error not in (None, 0, '0', False):
            return []

        items = result.get('items') or result.get('data') or []
        return [item for item in items if isinstance(item, dict)]

    def usenet_info(self, upload_id):
        if upload_id in (None, ''):
            return {}

        result = self._get(
            'usenet/uploads/info',
            params={'id': upload_id}
        )

        return result if isinstance(result, dict) else {}

    def user_cloud_usenet(self, request_id=None):
        if request_id:
            return self.usenet_info(request_id)

        return {'items': self.usenet_uploads()}

    def unrestrict_usenet(self, file_link_or_id):
        if not file_link_or_id:
            return None

        if str(file_link_or_id).startswith(('http://', 'https://')):
            return file_link_or_id

        return None

    @staticmethod
    def _usenet_upload_id(result):
        if not isinstance(result, dict):
            return None

        upload_id = result.get('id') or result.get('upload_id')
        if upload_id:
            return str(upload_id)

        data = result.get('data')
        if isinstance(data, dict):
            upload_id = data.get('id') or data.get('upload_id')
            if upload_id:
                return str(upload_id)

        return None

    def _recover_usenet_upload_id(self, before, nzb_url=None):
        before_ids = {
            str(item.get('id'))
            for item in (before or [])
            if item.get('id') is not None
        }

        for attempt in range(4):
            if attempt:
                time.sleep(1)

            uploads = self.usenet_uploads()
            new_items = [
                item for item in uploads
                if item.get('id') is not None
                and str(item.get('id')) not in before_ids
            ]

            if len(new_items) == 1:
                return str(new_items[0].get('id'))

            if nzb_url:
                exact = [
                    item for item in uploads
                    if str(item.get('source_url') or '').strip() == nzb_url
                ]
                if len(exact) == 1:
                    return str(exact[0].get('id'))

        return None

    def _select_usenet_file(
        self,
        files,
        title=None,
        season=None,
        episode=None
    ):
        videos = []

        for item in files or []:
            if not isinstance(item, dict):
                continue

            name = item.get('name') or item.get('filename') or ''
            link = item.get('link') or ''
            if not link or not self._is_video_link(link, name):
                continue

            try:
                size = int(item.get('size') or 0)
            except Exception:
                size = 0

            videos.append({
                'name': name,
                'link': link,
                'size': size
            })

        if not videos:
            return None

        is_episode = (
            season not in (None, '')
            and episode not in (None, '')
        )

        if is_episode:
            matches = [
                item for item in videos
                if item.get('name')
                and seas_ep_filter(season, episode, item.get('name'))
            ]

            if not matches:
                log_utils.log(
                    'Deepbrid Usenet: no file matched S%sE%s' % (
                        str(season).zfill(2),
                        str(episode).zfill(2)
                    ),
                    level=log_utils.LOGWARNING
                )
                return None

            matches.sort(key=lambda item: item.get('size', 0), reverse=True)
            selected = matches[0]
        else:
            title_lower = (title or '').lower()
            extras = tuple(
                extra for extra in extras_filter()
                if extra not in title_lower
            )
            filtered = [
                item for item in videos
                if not any(
                    extra in (item.get('name') or '').lower()
                    for extra in extras
                )
            ]
            pool = filtered or videos
            pool.sort(key=lambda item: item.get('size', 0), reverse=True)
            selected = pool[0]

        log_utils.log(
            'Deepbrid Usenet selected file: name=%s size=%s' % (
                selected.get('name'),
                selected.get('size')
            ),
            level=log_utils.LOGDEBUG
        )
        return selected

    def usenet_file_metadata(self, upload_id, upload_title=''):
        """Return stable NZB file metadata without caching direct links."""
        info = self.usenet_info(upload_id)
        if not isinstance(info, dict):
            return {}

        error = info.get('error')
        if error not in (None, 0, '0', False):
            return {}

        raw_files = info.get('files') or []
        if not raw_files:
            return {}

        # Do not cache an upload that has not exposed any playable links yet.
        if not any(
            isinstance(item, dict) and item.get('link')
            for item in raw_files
        ):
            return {}

        files = []
        for index, item in enumerate(raw_files):
            if not isinstance(item, dict):
                files.append({
                    'index': index,
                    'filename': '',
                    'size': 0
                })
                continue

            try:
                size = int(item.get('size') or 0)
            except Exception:
                size = 0

            files.append({
                'index': index,
                'filename': item.get('name') or item.get('filename') or '',
                'size': size
            })

        return {
            'count': len(raw_files),
            'files': files
        }

    def cached_usenet_file_metadata(self, upload_id, upload_title=''):
        return cache.get(
            self.usenet_file_metadata,
            24,
            str(upload_id),
            str(upload_title or '')
        ) or {}

    def add_usenet_url_dialog(self):
        nzb_url = control.dialog.input(
            'Deepbrid NZB URL',
            type=control.alpha_input
        )

        if not nzb_url:
            return

        nzb_url = nzb_url.strip()
        if not nzb_url.lower().startswith(('http://', 'https://')):
            return control.notification(
                title=self.name,
                message='Please enter a valid NZB URL',
                icon='ERROR'
            )

        before = self.usenet_uploads()
        result = self.add_usenet(nzb_url=nzb_url)
        if not result:
            return control.notification(
                title=self.name,
                message='NZB could not be added',
                icon='ERROR'
            )

        upload_id = self._usenet_upload_id(result)
        if not upload_id:
            upload_id = self._recover_usenet_upload_id(before, nzb_url=nzb_url)

        message = 'NZB added to Deepbrid'
        if upload_id:
            message += ' (ID %s)' % upload_id

        control.notification(title=self.name, message=message)
        control.refresh()
        return True

    # -------------------------------------------------
    # Cloud (read-only)
    # -------------------------------------------------

    def resolve_cloud_torrent_file(
        self,
        request_id,
        index,
        expected_count
    ):
        """Resolve cached torrent index against fresh one-time links."""
        info = self.torrent_info(request_id)
        if not isinstance(info, dict):
            return None

        error = info.get('error')
        if error not in (None, 0, '0', False):
            return None

        links = info.get('links') or []
        try:
            index = int(index)
            expected_count = int(expected_count)
        except Exception:
            return None

        if len(links) != expected_count or index < 0 or index >= len(links):
            log_utils.log(
                'Deepbrid cloud torrent mapping changed: '
                'id=%s expected=%s actual=%s index=%s' % (
                    request_id,
                    expected_count,
                    len(links),
                    index
                ),
                level=log_utils.LOGWARNING
            )
            return None

        return links[index]

    def resolve_cloud_usenet_file(
        self,
        upload_id,
        index,
        expected_count
    ):
        """Resolve cached NZB index against a fresh upload-info response."""
        info = self.usenet_info(upload_id)
        if not isinstance(info, dict):
            return None

        error = info.get('error')
        if error not in (None, 0, '0', False):
            return None

        files = info.get('files') or []
        try:
            index = int(index)
            expected_count = int(expected_count)
        except Exception:
            return None

        if len(files) != expected_count or index < 0 or index >= len(files):
            return None

        item = files[index]
        if not isinstance(item, dict):
            return None
        return item.get('link')

    def user_cloud(self, request_id=None):
        if request_id:
            return self.torrent_info(request_id)

        return self.torrent_info()

    @staticmethod
    def _cloud_sort_id(item):
        try:
            return int(item.get('id') or 0)
        except Exception:
            return 0

    def _cloud_listitem_art(self, listitem):
        listitem.setArt({
            'icon': deepbrid_icon,
            'poster': deepbrid_icon,
            'thumb': deepbrid_icon,
            'fanart': addon_fanart,
            'banner': deepbrid_icon
        })

    def user_cloud_to_listItem(self, folder_id=None):
        try:
            syshandle = int(argv[1])
        except Exception:
            return

        torrents = self._torrent_list()
        uploads = self.usenet_uploads()
        sysaddon = 'plugin://plugin.video.umbrella/'

        categories = [
            (
                'Torrent Cloud (%s)' % len(torrents),
                '%s?action=db_CloudTorrents' % sysaddon
            ),
            (
                'Usenet Uploads (%s)' % len(uploads),
                '%s?action=db_CloudUsenet' % sysaddon
            )
        ]

        for label, item_url in categories:
            listitem = control.item(label=label, offscreen=True)
            self._cloud_listitem_art(listitem)
            control.set_info(listitem, {'title': label})
            control.addItem(
                handle=syshandle,
                url=item_url,
                listitem=listitem,
                isFolder=True
            )

        control.content(syshandle, 'files')
        control.directory(syshandle, cacheToDisc=False)

    def cloud_torrents_to_listitem(self):
        try:
            syshandle = int(argv[1])
        except Exception:
            return

        sysaddon = 'plugin://plugin.video.umbrella/'
        torrents = self._torrent_list()
        torrents.sort(key=self._cloud_sort_id, reverse=True)

        for count, item in enumerate(torrents, 1):
            request_id = item.get('id')
            name = item.get('filename') or 'Torrent %s' % request_id
            try:
                progress = int(item.get('progress') or 0)
            except Exception:
                progress = 0
            links = item.get('links') or []
            ready = progress >= 100 and bool(links)
            status = 'Ready' if ready else '%s%%' % progress
            label = '%02d | [B]%s[/B] | %s' % (count, status, name)

            plot = 'Progress: %s%%' % progress
            if item.get('seeders') is not None:
                plot += '[CR]Seeders: %s' % item.get('seeders')
            if item.get('speed'):
                plot += '[CR]Speed: %s' % item.get('speed')
            plot += '[CR]Files: %s' % len(links)

            listitem = control.item(label=label, offscreen=True)
            self._cloud_listitem_art(listitem)
            control.set_info(listitem, {'title': name, 'plot': plot})

            item_url = ''
            if ready and request_id is not None:
                item_url = (
                    '%s?action=db_BrowseCloud&id=%s&mediatype=torrent' %
                    (sysaddon, request_id)
                )

            control.addItem(
                handle=syshandle,
                url=item_url,
                listitem=listitem,
                isFolder=bool(item_url)
            )

        control.content(syshandle, 'files')
        control.directory(syshandle, cacheToDisc=False)

    def cloud_usenet_to_listitem(self):
        try:
            syshandle = int(argv[1])
        except Exception:
            return

        sysaddon = 'plugin://plugin.video.umbrella/'
        uploads = self.usenet_uploads()

        for count, item in enumerate(uploads, 1):
            upload_id = item.get('id')
            title = item.get('title') or 'NZB %s' % upload_id
            source = item.get('source') or 'unknown'
            added_at = item.get('added_at') or ''
            label = '%02d | [B]%s[/B] | %s' % (count, source.capitalize(), title)
            if added_at:
                label += ' | %s' % added_at

            plot = 'Source: %s' % source
            if item.get('source_url'):
                plot += '[CR]Source URL: %s' % item.get('source_url')
            if added_at:
                plot += '[CR]Added: %s' % added_at

            listitem = control.item(label=label, offscreen=True)
            self._cloud_listitem_art(listitem)
            control.set_info(listitem, {'title': title, 'plot': plot})

            item_url = ''
            if upload_id is not None:
                item_url = (
                    '%s?action=db_BrowseCloud&id=%s&mediatype=usenet' %
                    (sysaddon, upload_id)
                )

            control.addItem(
                handle=syshandle,
                url=item_url,
                listitem=listitem,
                isFolder=bool(item_url)
            )

        control.content(syshandle, 'files')
        control.directory(syshandle, cacheToDisc=False)

    def _add_cloud_file_item(
        self,
        syshandle,
        count,
        name,
        stable_token,
        size_text=''
    ):
        if not stable_token:
            return

        label = '%02d | [B]FILE[/B]' % count
        if size_text:
            label += ' | %s' % size_text
        label += ' | %s' % name

        listitem = control.item(label=label, offscreen=True)
        self._cloud_listitem_art(listitem)
        control.set_info(
            listitem,
            {
                'title': name,
                'plot': ('Size: %s' % size_text) if size_text else name
            }
        )
        listitem.setProperty('IsPlayable', 'true')
        item_url = (
            'plugin://plugin.video.umbrella/?action=db_PlayCloud&token=%s' %
            quote_plus(stable_token)
        )
        control.addItem(
            handle=syshandle,
            url=item_url,
            listitem=listitem,
            isFolder=False
        )

    def browse_user_torrents(
        self,
        folder_id,
        mediatype='torrent'
    ):
        try:
            syshandle = int(argv[1])
        except Exception:
            return

        if mediatype == 'usenet':
            info = self.usenet_info(folder_id)
            files = info.get('files') or [] if isinstance(info, dict) else []
            expected_count = len(files)
            count = 0

            for index, item in enumerate(files):
                if not isinstance(item, dict):
                    continue
                name = item.get('name') or item.get('filename') or ''
                direct = item.get('link') or ''
                if not direct or not self._is_video_link(direct, name):
                    continue
                count += 1
                size_text = item.get('size_human') or ''
                if not size_text and item.get('size'):
                    try:
                        size_text = '%.2f GB' % (
                            float(item.get('size')) / 1073741824.0
                        )
                    except Exception:
                        size_text = str(item.get('size'))
                stable_token = 'dbu,%s,%s,%s' % (
                    folder_id,
                    index,
                    expected_count
                )
                self._add_cloud_file_item(
                    syshandle,
                    count,
                    name or 'Usenet file %s' % count,
                    stable_token,
                    size_text=size_text
                )

        else:
            info = self.torrent_info(folder_id)
            if not isinstance(info, dict):
                info = {}
            links = info.get('links') or []
            expected_count = len(links)
            probes = self._probe_torrent_link_names(links)

            if len(links) == 1 and probes and not probes[0].get('filename'):
                probes[0]['filename'] = info.get('filename') or 'Torrent file'

            count = 0
            for probe in probes:
                index = probe.get('index')
                if index is None or index >= expected_count:
                    continue
                name = probe.get('filename') or ''
                if not self._is_video_link('', name):
                    continue
                count += 1
                stable_token = 'dbt,%s,%s,%s' % (
                    folder_id,
                    index,
                    expected_count
                )
                self._add_cloud_file_item(
                    syshandle,
                    count,
                    name,
                    stable_token
                )

        control.content(syshandle, 'files')
        control.directory(syshandle, cacheToDisc=False)

    # -------------------------------------------------
    # Delete operations
    # -------------------------------------------------

    def delete_torrent(self, request_id=''):
        return False

    def delete_usenet(self, request_id=''):
        return False

    def delete_torrent_queued(
        self,
        request_id=''
    ):
        return False

    def delete_webdl(
        self,
        request_id=''
    ):
        return False

    def delete_user_torrent(
        self,
        request_id,
        mediatype,
        name,
        multi=False
    ):
        return False

    def delete_all_user_torrents(self):
        control.notification(
            title=self.name,
            message='Delete not supported by Deepbrid API'
        )
        return False

    def user_cloud_clear(self):
        control.notification(
            title=self.name,
            message='Delete not supported by Deepbrid API'
        )
        return False

    def unrestrict_webdl(self, file_id):
        return None

    def queued_torrents(self):
        return []