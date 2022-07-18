"""
    metahandler Kodi Addon
    Copyright (C) 2021 Eldorado

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from metahandler.lib.modules import db_utils
from metahandler.lib.modules import log_utils
from metahandler.lib.modules import kodi

logger = log_utils.Logger.get_logger()

def __enum(**enums):
    return type('Enum', (), enums)

MODES = __enum(RESET_CACHE='reset_cache')


@url_dispatcher.register(MODES.RESET_CACHE)
def reset_cache():
    if db_utils.delete_cache_db():
        kodi.notify(msg=kodi.i18n('cache_reset'))
    else:
        kodi.notify(msg=kodi.i18n('cache_reset_failed'))


def main(argv=None):
    if sys.argv: argv = sys.argv
    queries = kodi.parse_query(sys.argv[2])
    logger.log('Version: |%s| Queries: |%s|' % (kodi.get_version(), queries))
    logger.log('Args: |%s|' % (argv))

    # don't process params that don't match our url exactly. (e.g. plugin://plugin.video.1channel/extrafanart)
    plugin_url = 'plugin://%s/' % (kodi.get_id())
    if argv[0] != plugin_url:
        return

    mode = queries.get('mode', None)
    url_dispatcher.dispatch(mode, queries)


if __name__ == '__main__':
    sys.exit(main())