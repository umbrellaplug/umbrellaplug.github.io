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

'''
This module provides a small front API for accessing some of the basic metahandler features.

You will likely want to use directly the metahandlers.MetaData() class for the majority of functions.

eg.
    from metahandler import metahandlers
    mh=metahandlers.MetaData(tmdb_api_key=<key>, omdb_api_key=<key>, tvdb_api_key=<key>)

To lookup a movie or tv show:
    mh.get_meta(media_type, name, imdb_id=, tmdb_id=, year=)

To lookup a tv show seasons:
    mh.get_seasons(title, imdb_id, seasons)

To lookup an episode:
    mh.get_episode_meta(title, imdb_id, season, episode, air_date=, episode_title=)
     

Check each function for a full description of args and return values

'''
from metahandler import common
from metahandler.lib.modules import log_utils

logger = log_utils.Logger.get_logger()
logger.log_info('Initializing MetaHandlers version: %s' % common.addon_version)
