'''
    These classes cache metadata from TheMovieDB, OMDB and TVDB.
    It uses sqlite or mysql databases.
       
    It uses themoviedb JSON api class and TVDB XML api class.
    OMDB api is used as a backup for TMDB, fill in missing pieces.

    For TVDB it currently uses a modified version of 
    Python API by James Smith (http://loopj.com)
    
    Author: Eldorado
'''

import os
import re
import sys
import time

from metahandler.lib.sources.TMDB import TMDB
from metahandler.lib.sources.thetvdbapi import TheTVDB
from metahandler.lib.modules import db_utils
from metahandler.lib.modules import meta_types
from metahandler.lib.modules import utils
from metahandler.lib.modules import constants
from metahandler.lib.modules import log_utils
from metahandler.lib.modules import kodi
from metahandler import common

logger = log_utils.Logger.get_logger()

sys.path.append((os.path.split(common.addon_path))[0])
       
class MetaData:  
    '''
    This class performs all the handling of meta data, requesting, storing and sending back to calling application

        - Create cache DB if it does not exist
        - Get the meta data from TMDB/IMDB/TVDB
        - Store/Retrieve meta from cache DB
    '''  

     
    def __init__(self, tmdb_api_key=None, omdb_api_key=None, tvdb_api_key=None):
        """
        Initialize MetaData class

        Metahandlers must be initialized with api keys
        It is the developers responsibility to ensure that these are working
        Users are able to override the keys by supplying their own

            :param tmdb_api_key=None: TMDB API key
            :param omdb_api_key=None: OMDB API Key
            :param tvdb_api_key=None: TVDB API Key
        """

        # Class variables
        self.tmdb_image_url = ''
        self.path = common.profile_path
        self.cache_path = utils.make_dir(self.path, 'meta_cache')
        self.videocache = os.path.join(self.cache_path, 'video_cache.db')
        self.tmdb_api_key=tmdb_api_key
        self.omdb_api_key=omdb_api_key
        self.tvdb_api_key=tvdb_api_key

        if kodi.get_setting('override_tmdb_key') == 'true' and kodi.get_setting('tmdb_api_key'):
            logger.log('Using user supplied TMDB API Key')
            self.tmdb_api_key=kodi.get_setting('tmdb_api_key')

        if kodi.get_setting('override_omdb_key') == 'true' and kodi.get_setting('omdb_api_key'):
            logger.log('Using user supplied OMDB API Key')       
            self.omdb_api_key=kodi.get_setting('omdb_api_key')
    
        if kodi.get_setting('override_tvdb_key') == 'true' and kodi.get_setting('tvdb_api_key'):
            logger.log('Using user supplied TVDB API Key')
            self.tvdb_api_key=kodi.get_setting('tvdb_api_key')

        # Check to make sure we have api keys set before continuing
        if not self.tmdb_api_key and not self.omdb_api_key and not self.tvdb_api_key:
            logger.log_error('*** Metahandlers does NOT come with API keys, developer must supply their own ***')
       
        # Initialize DB
        self.DB = db_utils.DB_Connection(self.videocache)

        # Check TMDB configuration, update if necessary
        self._set_tmdb_config()
   

    def get_meta(self, media_type, name, imdb_id='', tmdb_id='', year='', overlay=6, update=False):
        '''
        Main method to get meta data for movie or tvshow. Will lookup by name/year 
        if no IMDB ID supplied.       
        
        Args:
            media_type (str): 'movie' or 'tvshow'
            name (str): full name of movie/tvshow you are searching
        Kwargs:
            imdb_id (str): IMDB ID        
            tmdb_id (str): TMDB ID
            year (str): 4 digit year of video, recommended to include the year whenever possible
                        to maximize correct search results.
            overlay (int): To set the default watched status (6=unwatched, 7=watched) on new videos
                        
        Returns:
            DICT of meta data or None if cannot be found.
        '''
       
        logger.log('---------------------------------------------------------------------------------------')
        logger.log('Attempting to retrieve meta data for %s: %s %s %s %s' % (media_type, name, year, imdb_id, tmdb_id))
 
        meta = {}
        if imdb_id:
            imdb_id = utils.valid_imdb_id(imdb_id)

        # First check cache for saved entry
        if imdb_id:
            meta = self._cache_lookup_by_id(media_type, imdb_id=imdb_id)
        elif tmdb_id:
            meta = self._cache_lookup_by_id(media_type, tmdb_id=tmdb_id)
        else:
            meta = self._cache_lookup_by_name(media_type, name, year)

        # If meta not found in cache lookup thru online services
        if not meta:
            
            if media_type==constants.type_movie:
                meta = self._get_tmdb_meta(imdb_id, tmdb_id, name, year)
            elif media_type==constants.type_tvshow:
                meta = self._get_tvdb_meta(imdb_id, name, year)

            if meta:
                self._cache_save_video_meta(meta, name, media_type, overlay)
            
        if meta:
            meta = self.__format_meta(media_type, meta, name)
        
        return meta


    def get_seasons(self, tvshowtitle, imdb_id, seasons, overlay=6):
        '''
        Requests from TVDB a list of images for a given tvshow
        and list of seasons
        Args:
            tvshowtitle (str): TV Show Title
            imdb_id (str): IMDB ID
            seasons (str): a list of seasons, numbers only
        Returns:
            (list) list of covers found for each season
        '''     
        try:
            if imdb_id:
                imdb_id = utils.valid_imdb_id(imdb_id)

            coversList = []
            tvdb_id = self._get_tvdb_id(tvshowtitle, imdb_id)
            images  = None
            for season in seasons:
                meta = self._cache_lookup_season(imdb_id, tvdb_id, season)
                if meta is None:
                    meta = {}
                    if tvdb_id is None or tvdb_id == '':
                        meta['cover_url']=''
                    elif images:
                        meta['cover_url']=self._find_cover(season, images )
                    else:
                        if len(str(season)) == 4:
                            meta['cover_url']=''
                        else:
                            images = self._get_season_posters(tvdb_id, season)
                            meta['cover_url']=self._find_cover(season, images )

                    meta['season'] = int(season)
                    meta['tvdb_id'] = tvdb_id
                    meta['imdb_id'] = imdb_id
                    meta['overlay'] = overlay
                    meta['backdrop_url'] = self._get_tvshow_backdrops(imdb_id, tvdb_id)
                    #Ensure we are not sending back any None values, XBMC doesn't like them
                    meta = utils.remove_none_values(meta)
                    self._cache_save_season_meta(meta)

                #Set Watched flag
                meta['playcount'] = utils.set_playcount(meta['overlay'])

                coversList.append(meta)
            return coversList
        except:
            import traceback
            traceback.print_exc()






    def __insert_from_dict(self, table, size):
        ''' Create a SQL Insert statement with dictionary values '''
        sql = 'INSERT INTO %s ' % table
        
        if self.DB.DB_Type == 'mysql':
            format = ', '.join(['%s'] * size)
        else:
            format = ', '.join('?' * size)
        
        sql_insert = sql + 'Values (%s)' % format
        return sql_insert


    def _get_config(self, setting):
        '''
        Query local Config table for values
        '''
        
        #Query local table first for current values
        sql_select = "SELECT * FROM config where setting = '%s'" % setting

        logger.log('Looking up in local cache for config data: %s' % setting)
        logger.log('SQL Select: %s' % sql_select)        

        try:    
            matchedrow = self.DB.select_single(sql_select)
        except Exception as e:
            logger.log_error('************* Error selecting from cache db: %s' % e)
            return None

        if matchedrow:
            logger.log('Found config data in cache table for setting: %s value: %s' % (setting, dict(matchedrow)))
            return dict(matchedrow)['value']
        else:
            logger.log('No match in local DB for config setting: %s' % setting)
            return None            
            

    def _set_config(self, setting, value):
        '''
        Set local Config table for values
        '''      
        sql_insert = "REPLACE INTO config (setting, value) VALUES(%s,%s)"
        if self.DB.DB_Type == 'sqlite':
            sql_insert = 'INSERT OR ' + sql_insert.replace('%s', '?')

        logger.log('Updating local cache for config data: %s value: %s' % (setting, value))
        logger.log('SQL Insert: %s' % sql_insert)

        values = (setting, value)
        self.DB.insert(sql_insert, values)
            

    def _set_tmdb_config(self):
        '''
        Query config database for required TMDB config values, set constants as needed
        Validate cache timestamp to ensure it is only refreshed once every 7 days
        '''

        logger.log('Looking up TMDB config cache values')        
        tmdb_image_url = self._get_config('tmdb_image_url')
        tmdb_config_timestamp = self._get_config('tmdb_config_timestamp')
        
        #Grab current time in seconds            
        now = time.time()
        age = 0

        #Cache limit is 7 days, value needs to be in seconds: 60 seconds * 60 minutes * 24 hours * 7 days
        expire = 60 * 60 * 24 * 7
              
        #Check if image and timestamp values are valid
        if tmdb_image_url and tmdb_config_timestamp:
            created = float(tmdb_config_timestamp)
            age = now - created
            logger.log('Cache age: %s , Expire: %s' % (age, expire))
            
            #If cache hasn't expired, set constant values
            if age <= float(expire):
                logger.log('Cache still valid, setting values')
                logger.log('Setting tmdb_image_url: %s' % tmdb_image_url)
                self.tmdb_image_url = tmdb_image_url
            else:
                logger.log('Cache is too old, need to request new values')
        
        #Either we don't have the values or the cache has expired, so lets request and set them - update cache in the end
        if (not tmdb_image_url or not tmdb_config_timestamp) or age > expire:
            logger.log('No cached config data found or cache expired, requesting from TMDB')

            tmdb = TMDB(tmdb_api_key=self.tmdb_api_key, omdb_api_key=self.omdb_api_key, lang=utils.get_tmdb_language())
            config_data = tmdb.call_config()

            if config_data:
                self.tmdb_image_url = config_data['images']['base_url']
                self._set_config('tmdb_image_url', config_data['images']['base_url'])
                self._set_config('tmdb_config_timestamp', now)
            else:
                self.tmdb_image_url = tmdb_image_url
                

    def check_meta_installed(self, addon_id):
        '''
        Check if a meta data pack has been installed for a specific addon

        Queries the 'addons' table, if a matching row is found then we can assume the pack has been installed
        
        Args:
            addon_id (str): unique name/id to identify an addon
                        
        Returns:
            matchedrow (dict) : matched row from addon table
        '''

        if addon_id:
            sql_select = "SELECT * FROM addons WHERE addon_id = '%s'" % addon_id
        else:
            logger.log_warning('Invalid addon id')
            return False
        
        logger.log('Looking up in local cache for addon id: %s' % addon_id)
        logger.log('SQL Select: %s' % sql_select)
        try:    
            matchedrow = self.DB.select_single(sql_select)
        except Exception as e:
            logger.log_error('************* Error selecting from cache db: %s' % e)
            return None
        
        if matchedrow:
            logger.log('Found addon id in cache table: %s' % dict(matchedrow))
            return dict(matchedrow)
        else:
            logger.log('No match in local DB for addon_id: %s' % addon_id)
            return False


    def insert_meta_installed(self, addon_id, last_update):
        '''
        Insert a record into addons table

        Insert a unique addon id AFTER a meta data pack has been installed
        
        Args:
            addon_id (str): unique name/id to identify an addon
            last_update (str): date of last meta pack installed - use to check to install meta updates
        '''

        if addon_id:
            sql_insert = "INSERT INTO addons(addon_id, last_update) VALUES (?,?)"
        else:
            logger.log_warning('Invalid addon id')
            return
        
        logger.log('Inserting into addons table addon id: %s' % addon_id)
        logger.log('SQL Insert: %s' % sql_insert)
        values = (addon_id, last_update)
        self.DB.insert(sql_insert, values)
                   

    def __format_meta(self, media_type, meta, name):
        '''
        Format and massage movie/tv show data to prepare for return to addon
        
        Args:
            media_type (str): 'movie' or 'tvshow'
            meta (dict): movie / tv show meta data dictionary returned from cache or online
            name (str): full name of movie/tvshow you are searching
        Returns:
            DICT. Data formatted and corrected for proper return to xbmc addon
        '''      

        try:
            #We want to send back the name that was passed in
            meta = meta['meta_data']
            meta_data = {}
            meta['title'] = name
            
            #Change cast back into a tuple
            if meta['cast']:
                meta['cast'] = eval(str(meta['cast']))
                
            #Return a trailer link that will play via youtube addon
            try:
                meta['trailer'] = ''
                trailer_id = ''
                if meta['trailer_url']:
                    r = re.match('^[^v]+v=(.{3,11}).*', meta['trailer_url'])
                    if r:
                        trailer_id = r.group(1)
                    else:
                        trailer_id = meta['trailer_url']
                 
                if trailer_id:
                    meta['trailer'] = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s' % trailer_id
                    
            except Exception as e:
                meta['trailer'] = ''
                logger.log_warning('Failed to set trailer: %s' % e)
                pass
    
            #Ensure we are not sending back any None values, XBMC doesn't like them
            meta = utils.remove_none_values(meta)
            
            #Add TVShowTitle infolabel
            if media_type==constants.type_tvshow:
                meta['TVShowTitle'] = meta['title']
            
            #Set Watched flag for movies
            if media_type==constants.type_movie:
                meta['playcount'] = utils.set_playcount(meta['overlay'])
            
            # Piece together the full URL for images from TMDB
            if media_type == constants.type_movie:
                if meta['cover_url'] and len(meta['cover_url']) > 1:
                    if not meta['cover_url'].startswith('http'):
                        meta['cover_url'] = self.tmdb_image_url  + kodi.get_setting('tmdb_poster_size') + meta['cover_url']
                else:
                    meta['cover_url'] = ''
                if meta['backdrop_url'] and len(meta['backdrop_url']) > 1:
                    if not meta['backdrop_url'].startswith('http'):
                        meta['backdrop_url'] = self.tmdb_image_url  + kodi.get_setting('tmdb_backdrop_size') + meta['backdrop_url']
                else:
                    meta['backdrop_url'] = ''
    
            logger.log('Returned Meta: %s' % meta)
            return meta  
        except Exception as e:
            logger.log_error('************* Error formatting meta: %s' % e)
            return meta  


    def update_meta(self, media_type, name, imdb_id, tmdb_id='', new_imdb_id='', new_tmdb_id='', year=''):
        '''
        Updates and returns meta data for given movie/tvshow, mainly to be used with refreshing individual movies.
        
        Searches local cache DB for record, delete if found, calls get_meta() to grab new data

        name, imdb_id, tmdb_id should be what is currently in the DB in order to find current record
        
        new_imdb_id, new_tmdb_id should be what you would like to update the existing DB record to, which you should have already found
        
        Args:
            name (int): full name of movie you are searching            
            imdb_id (str): IMDB ID of CURRENT entry
        Kwargs:
            tmdb_id (str): TMDB ID of CURRENT entry
            new_imdb_id (str): NEW IMDB_ID to search with
            new_tmdb_id (str): NEW TMDB ID to search with
            year (str): 4 digit year of video, recommended to include the year whenever possible
                        to maximize correct search results.
                        
        Returns:
            DICT of meta data or None if cannot be found.
        '''
        logger.log('---------------------------------------------------------------------------------------')
        logger.log('Updating meta data: %s Old: %s %s New: %s %s Year: %s' % (name.encode('ascii','replace'), imdb_id, tmdb_id, new_imdb_id, new_tmdb_id, year))
        
        if imdb_id:
            imdb_id = utils.valid_imdb_id(imdb_id)        
        
        if imdb_id:
            meta = self._cache_lookup_by_id(media_type, imdb_id=imdb_id)
        elif tmdb_id:
            meta = self._cache_lookup_by_id(media_type, tmdb_id=tmdb_id)
        else:
            meta = self._cache_lookup_by_name(media_type, name, year)
            
        #if no old meta found, the year is probably not in the database
        if not imdb_id and not tmdb_id:
            year = ''
            
        if meta:
            overlay = meta['overlay']
            self._cache_delete_video_meta(media_type, imdb_id, tmdb_id, name, year)
        else:
            overlay = 6
            logger.log_warning('No match found in cache db')
        
        if not new_imdb_id:
            new_imdb_id = imdb_id
        elif not new_tmdb_id:
            new_tmdb_id = tmdb_id
            
        return self.get_meta(media_type, name, new_imdb_id, new_tmdb_id, year, overlay, True)


    def _cache_lookup_by_id(self, media_type, imdb_id='', tmdb_id=''):
        '''
        Lookup in SQL DB for video meta data by IMDB ID
        
        Args:
            imdb_id (str): IMDB ID
            media_type (str): 'movie' or 'tvshow'
        Kwargs:
            imdb_id (str): IDMB ID
            tmdb_id (str): TMDB ID                        
        Returns:
            DICT of matched meta data or None if no match.
        '''        
        if media_type == constants.type_movie:
            sql_select = "SELECT * FROM movie_meta"
            if imdb_id:
                sql_select = sql_select + " WHERE imdb_id = '%s'" % imdb_id
            else:
                sql_select = sql_select + " WHERE tmdb_id = '%s'" % tmdb_id

        elif media_type == constants.type_tvshow:
            sql_select = ("SELECT a.*, "
                               "CASE "
                                   "WHEN b.episode ISNULL THEN 0 "
                                   "ELSE b.episode "
                               "END AS episode, "
                               "CASE "
                                   "WHEN c.playcount ISNULL THEN 0 "
                                   "ELSE c.playcount "
                               "END AS playcount "
                       "FROM tvshow_meta a "
                       "LEFT JOIN "
                         "(SELECT imdb_id, "
                                 "count(imdb_id) AS episode "
                          "FROM episode_meta "
                          "WHERE imdb_id = '%s' "
                          "GROUP BY imdb_id) b ON a.imdb_id = b.imdb_id "
                       "LEFT JOIN "
                         "(SELECT imdb_id, "
                                 "count(imdb_id) AS playcount "
                          "FROM episode_meta "
                          "WHERE imdb_id = '%s' "
                            "AND OVERLAY=7 "
                          "GROUP BY imdb_id) c ON a.imdb_id = c.imdb_id "
                       "WHERE a.imdb_id = '%s'") % (imdb_id, imdb_id, imdb_id)

            if self.DB.DB_Type == 'mysql':
                sql_select = sql_select.replace("ISNULL", "IS NULL")

        logger.log('Looking up in local cache by id for: %s %s %s' % (media_type, imdb_id, tmdb_id))
        logger.log( 'SQL Select: %s' % sql_select)

        try:    
            matchedrow = self.DB.select_single(sql_select)
        except Exception as e:
            logger.log_error('************* Error selecting from cache db: %s' % e)
            return None
        
        if matchedrow:
            logger.log('Found meta information by id in cache table: %s' % dict(matchedrow))
            return dict(matchedrow)
        else:
            logger.log('No match in local DB')
            return None


    def _cache_lookup_by_name(self, media_type, name, year=''):
        '''
        Lookup in SQL DB for video meta data by name and year
        
        Args:
            media_type (str): 'movie' or 'tvshow'
            name (str): full name of movie/tvshow you are searching
        Kwargs:
            year (str): 4 digit year of video, recommended to include the year whenever possible
                        to maximize correct search results.
                        
        Returns:
            DICT of matched meta data or None if no match.
        '''        

        name =  utils.clean_string(name.lower())
        if media_type == constants.type_movie:
            sql_select = "SELECT * FROM movie_meta WHERE title = '%s'" % name
        elif media_type == constants.type_tvshow:
            sql_select = "SELECT a.*, CASE WHEN b.episode ISNULL THEN 0 ELSE b.episode END AS episode, CASE WHEN c.playcount ISNULL THEN 0 ELSE c.playcount END as playcount FROM tvshow_meta a LEFT JOIN (SELECT imdb_id, count(imdb_id) AS episode FROM episode_meta GROUP BY imdb_id) b ON a.imdb_id = b.imdb_id LEFT JOIN (SELECT imdb_id, count(imdb_id) AS playcount FROM episode_meta WHERE overlay=7 GROUP BY imdb_id) c ON a.imdb_id = c.imdb_id WHERE a.title = '%s'" % name
            if self.DB.DB_Type == 'mysql':
                sql_select = sql_select.replace("ISNULL", "IS NULL")
        logger.log('Looking up in local cache by name for: %s %s %s' % (media_type, name, year))
        
        if year and (media_type == constants.type_movie or media_type == constants.type_tvshow):
            sql_select = sql_select + " AND year = %s" % year
        logger.log('SQL Select: %s' % sql_select)
        
        try:
            matchedrow = self.DB.select_single(sql_select)
        except Exception as e:
            logger.log_error('************* Error selecting from cache db: %s' % e)
            return None
            
        if matchedrow:
            logger.log('Found meta information by name in cache table: %s' % dict(matchedrow))
            return dict(matchedrow)
        else:
            logger.log('No match in local DB')
            return None

    
    def _cache_save_video_meta(self, meta_group, name, media_type, overlay=6):
        '''
        Saves meta data to SQL table given type
        
        Args:
            meta_group (dict/list): meta data of video to be added to database
                                    can be a list of dicts (batch insert)or a single dict
            media_type (str): 'movie' or 'tvshow'
        Kwargs:
            overlay (int): To set the default watched status (6=unwatched, 7=watched) on new videos                        
        '''            
        
        if media_type == constants.type_movie:
            table='movie_meta'
        elif media_type == constants.type_tvshow:
            table='tvshow_meta'

        for meta in meta_group:
    
            #If a list of dicts (batch insert) has been passed in, ensure individual list item is converted to a dict
            if type(meta_group) is list:
                meta = dict(meta)
                name = meta['title']
            
            #Else ensure we use the dict passed in
            else:
                meta = meta_group['meta_data']
                
            #strip title
            meta['title'] =  utils.clean_string(name.lower())
                    
            if 'cast' in meta:
                meta['cast'] = str(meta['cast'])
    
            #set default overlay - watched status
            meta['overlay'] = overlay
            
            logger.log('Saving cache information: %s' % meta)

            sql_insert = ''
            if media_type == constants.type_movie and meta['imdb_id'] and meta['tmdb_id'] and meta['title'] and meta['year']:
                sql_insert = self.__insert_from_dict(table, 22)
                values = (meta['imdb_id'], meta['tmdb_id'], meta['title'],
                                meta['year'], meta['director'], meta['writer'], meta['tagline'], meta['cast'],
                                meta['rating'], meta['votes'], meta['duration'], meta['plot'], meta['mpaa'],
                                meta['premiered'], meta['genre'], meta['studio'], meta['thumb_url'], meta['cover_url'],
                                meta['trailer_url'], meta['backdrop_url'], None, meta['overlay'])

            elif media_type == constants.type_tvshow and meta['imdb_id'] and meta['tvdb_id'] and meta['title']:
                sql_insert = self.__insert_from_dict(table, 19)
                logger.log('SQL INSERT: %s' % sql_insert)
                values = (meta['imdb_id'], meta['tvdb_id'], meta['title'], meta['year'], 
                        meta['cast'], meta['rating'], meta['duration'], meta['plot'], meta['mpaa'],
                        meta['premiered'], meta['genre'], meta['studio'], meta['status'], meta['banner_url'],
                        meta['cover_url'], meta['trailer_url'], meta['backdrop_url'], None, meta['overlay'])

            #Commit all transactions
            if sql_insert:
                self.DB.insert(sql_insert, values)
                logger.log('SQL INSERT Successfully Commited')
            
            #Break loop if we are dealing with just 1 record
            if type(meta_group) is dict:
                break


    def _cache_delete_video_meta(self, media_type, imdb_id, tmdb_id, name, year):
        '''
        Delete meta data from SQL table
        
        Args:
            media_type (str): 'movie' or 'tvshow'
            imdb_id (str): IMDB ID
            tmdb_id (str): TMDB ID   
            name (str): Full movie name
            year (int): Movie year
                        
        '''         
        
        if media_type == constants.type_movie:
            table = 'movie_meta'
        elif media_type == constants.type_tvshow:
            table = 'tvshow_meta'
            
        if imdb_id:
            sql_delete = "DELETE FROM %s WHERE imdb_id = '%s'" % (table, imdb_id)
        elif tmdb_id:
            sql_delete = "DELETE FROM %s WHERE tmdb_id = '%s'" % (table, tmdb_id)
        else:
            name =  utils.clean_string(name.lower())
            sql_delete = "DELETE FROM %s WHERE title = '%s'" % (table, name)
            if year:
                sql_delete = sql_delete + ' AND year = %s' % (year)

        logger.log('Deleting table entry: %s %s %s %s ' % (imdb_id, tmdb_id, name, year))
        logger.log('SQL DELETE: %s' % sql_delete)
        self.DB.commit(sql_delete)
        

    def _get_tmdb_meta(self, imdb_id, tmdb_id, name, year=''):
        '''
        Requests meta data from TMDB and creates proper dict to send back
        
        Args:
            imdb_id (str): IMDB ID
            name (str): full name of movie you are searching
        Kwargs:
            year (str): 4 digit year of movie, when imdb_id is not available it is recommended
                        to include the year whenever possible to maximize correct search results.
                        
        Returns:
            DICT. It must also return an empty dict when
            no movie meta info was found from tmdb because we should cache
            these "None found" entries otherwise we hit tmdb alot.
        '''        


        # Check to make sure we have api keys set before continuing
        if not self.tmdb_api_key:
            logger.log_error('*** Metahandlers does NOT come with API keys, developer must supply their own ***')
            return meta_types.init_movie_meta(imdb_id, tmdb_id, name, year)
        
        tmdb = TMDB(tmdb_api_key=self.tmdb_api_key, omdb_api_key=self.omdb_api_key, lang=utils.get_tmdb_language())
        meta = tmdb.tmdb_lookup(name,imdb_id,tmdb_id, year)
        
        if meta is None:
            # create an empty dict so below will at least populate empty data for the db insert.
            meta = {}

        return self._format_tmdb_meta(meta, imdb_id, name, year)


    def _format_tmdb_meta(self, md, imdb_id, name, year):
        '''
        Copy tmdb to our own for conformity and eliminate KeyError. Set default for values not returned
        
        Args:
            imdb_id (str): IMDB ID
            name (str): full name of movie you are searching
        Kwargs:
            year (str): 4 digit year of movie, when imdb_id is not available it is recommended
                        to include the year whenever possible to maximize correct search results.
                        
        Returns:
            DICT. It must also return an empty dict when
            no movie meta info was found from tvdb because we should cache
            these "None found" entries otherwise we hit tvdb alot.
        '''      
        
        #Intialize movie_meta dictionary    
        meta = {}
        meta_data = meta_types.init_movie_meta(imdb_id, md.get('id', ''), name, year)
        meta = meta_data['meta_data']
        
        meta['imdb_id'] = md.get('imdb_id', imdb_id)
        meta['title'] = md.get('name', name)      
        meta['tagline'] = md.get('tagline', '')
        if md.get('rating'):
            meta['rating'] = float(md.get('rating'))
        meta['votes'] = str(md.get('votes', ''))
        if meta['duration']:
            meta['duration'] = int(str(md.get('runtime'))) * 60
        meta['plot'] = md.get('overview', '')
        meta['mpaa'] = md.get('certification', '')       
        meta['premiered'] = md.get('released', '')
        meta['director'] = md.get('director', '')
        meta['writer'] = md.get('writer', '')       

        #Do whatever we can to set a year, if we don't have one lets try to strip it from premiered
        if not year and meta['premiered']:
            #meta['year'] = int(self._convert_date(meta['premiered'], '%Y-%m-%d', '%Y'))
            meta['year'] = int(meta['premiered'][:4])
            
        meta['trailer_url'] = md.get('trailers', '')
        meta['genre'] = md.get('genre', '')
        
        #Get cast, director, writers
        cast_list = []
        cast_list = md.get('cast','')
        if cast_list:
            for cast in cast_list:
                char = cast.get('character','')
                if not char:
                    char = ''
                meta['cast'].append((cast.get('name',''),char))
                        
        crew_list = []
        crew_list = md.get('crew','')
        if crew_list:
            for crew in crew_list:
                job=crew.get('job','')
                if job == 'Director':
                    meta['director'] = crew.get('name','')
                elif job == 'Screenplay':
                    if meta['writer']:
                        meta['writer'] = meta['writer'] + ' / ' + crew.get('name','')
                    else:
                        meta['writer'] = crew.get('name','')
                    
        genre_list = []
        genre_list = md.get('genres', '')
        if(genre_list):
            meta['genre'] = ''
        for genre in genre_list:
            if meta['genre'] == '':
                meta['genre'] = genre.get('name','')
            else:
                meta['genre'] = meta['genre'] + ' / ' + genre.get('name','')
        
        if 'tvdb_studios' in md:
            meta['studio'] = md.get('tvdb_studios', '')
        try:
            meta['studio'] = (md.get('studios', '')[0])['name']
        except:
            try:
                meta['studio'] = (md.get('studios', '')[1])['name']
            except:
                try:
                    meta['studio'] = (md.get('studios', '')[2])['name']
                except:
                    try:    
                        meta['studio'] = (md.get('studios', '')[3])['name']
                    except:
                        logger.log('Studios failed: %s ' % md.get('studios', ''))
                        pass
        
        meta['cover_url'] = md.get('cover_url', '')
        meta['backdrop_url'] = md.get('backdrop_url', '')
        if 'posters' in md:
            # find first thumb poster url
            for poster in md['posters']:
                if poster['image']['size'] == 'thumb':
                    meta['thumb_url'] = poster['image']['url']
                    break
            # find first cover poster url
            for poster in md['posters']:
                if poster['image']['size'] == 'cover':
                    meta['cover_url'] = poster['image']['url']
                    break

        if 'backdrops' in md:
            # find first original backdrop url
            for backdrop in md['backdrops']:
                if backdrop['image']['size'] == 'original':
                    meta['backdrop_url'] = backdrop['image']['url']
                    break

        meta_data['meta_data'] = meta
        return meta_data
        
        
    def _get_tvdb_meta(self, imdb_id, name, year=''):
        '''
        Requests meta data from TVDB and creates proper dict to send back
        
        Args:
            imdb_id (str): IMDB ID
            name (str): full name of movie you are searching
        Kwargs:
            year (str): 4 digit year of movie, when imdb_id is not available it is recommended
                        to include the year whenever possible to maximize correct search results.
                        
        Returns:
            DICT. It must also return an empty dict when
            no movie meta info was found from tvdb because we should cache
            these "None found" entries otherwise we hit tvdb alot.
        '''      
        # Check to make sure we have api keys set before continuing
        if not self.tvdb_api_key:
            logger.log_error('*** Metahandlers does NOT come with API keys, developer must supply their own ***')
            return meta_types.init_tvshow_meta(imdb_id, None, name, year)

        logger.log('Starting TVDB Lookup')
        tvdb = TheTVDB(api_key=self.tvdb_api_key, language=utils.get_tvdb_language())
        tvdb_id = ''
        
        try:
            if imdb_id:
                tvdb_id = tvdb.get_show_by_imdb(imdb_id)
        except Exception as e:
            logger.log_error('************* Error retreiving from thetvdb.com: %s ' % e)
            tvdb_id = ''
            pass
            
        #Intialize tvshow meta dictionary
        meta = meta_types.init_tvshow_meta(imdb_id, tvdb_id, name, year)

        # if not found by imdb, try by name
        if tvdb_id == '':
            try:
                #If year is passed in, add it to the name for better TVDB search results
                #if year:
                #    name = name + ' ' + year
                show_list=tvdb.get_matching_shows(name)
            except Exception as e:
                logger.log_error('************* Error retreiving from thetvdb.com: %s ' % e)
                show_list = []
                pass
            logger.log('Found TV Show List: %s' % show_list)
            tvdb_id=''
            for show in show_list:
                (junk1, junk2, junk3) = show
                try:
                    #if we match imdb_id or full name (with year) then we know for sure it is the right show
                    if (imdb_id and junk3==imdb_id) or (year and utils.string_compare(utils.clean_string(junk2), utils.clean_string(name + year))):
                        tvdb_id = utils.clean_string(junk1)
                        if not imdb_id:
                            imdb_id = utils.clean_string(junk3)
                        name = junk2
                        break
                    #if we match just the cleaned name (without year) keep the tvdb_id
                    elif utils.string_compare(utils.clean_string(junk2), utils.clean_string(name)):
                        tvdb_id = utils.clean_string(junk1)
                        if not imdb_id:
                            imdb_id = utils.clean_string(junk3)
                        break
                        
                except Exception as e:
                    logger.log_error('************* Error retreiving from thetvdb.com: %s ' % e)

        if tvdb_id:
            logger.log('Show *** ' + name + ' *** found in TVdb. Getting details...')

            try:
                show = tvdb.get_show(tvdb_id)
            except Exception as e:
                logger.log_error('************* Error retreiving from thetvdb.com: %s ' % e)
                show = None
                pass
            
            if show is not None:
                meta['imdb_id'] = imdb_id
                meta['tvdb_id'] = tvdb_id
                meta['title'] = name
                if str(show.rating) != '' and show.rating != None:
                    meta['rating'] = float(show.rating)
                meta['duration'] = int(show.runtime) * 60
                meta['plot'] = show.overview
                meta['mpaa'] = show.content_rating
                meta['premiered'] = str(show.first_aired)

                #Do whatever we can to set a year, if we don't have one lets try to strip it from show.first_aired/premiered
                if not year and show.first_aired:
                        #meta['year'] = int(self._convert_date(meta['premiered'], '%Y-%m-%d', '%Y'))
                        meta['year'] = int(meta['premiered'][:4])

                if show.genre != '':
                    temp = show.genre.replace("|",",")
                    temp = temp[1:(len(temp)-1)]
                    meta['genre'] = temp
                meta['studio'] = show.network
                meta['status'] = show.status
                if show.actors:
                    for actor in show.actors:
                        meta['meta_data']['cast'].append(actor)
                meta['banner_url'] = show.banner_url
                meta['cover_url'] = show.poster_url
                meta['backdrop_url'] = show.fanart_url
                meta['overlay'] = 6

                if meta['plot'] == 'None' or meta['plot'] == '' or meta['plot'] == 'TBD' or meta['plot'] == 'No overview found.' or meta['rating'] == 0 or meta['duration'] == 0 or meta['cover_url'] == '':
                    logger.log(' Some info missing in TVdb for TVshow *** '+ name + ' ***. Will search imdb for more')
                    tmdb = TMDB(tmdb_api_key=self.tmdb_api_key, omdb_api_key=self.omdb_api_key, lang=utils.get_tmdb_language())
                    imdb_meta = tmdb.search_imdb(name, imdb_id)
                    if imdb_meta:
                        imdb_meta = tmdb.update_imdb_meta(meta, imdb_meta)
                        if 'overview' in imdb_meta:
                            meta['plot'] = imdb_meta['overview']
                        if 'rating' in imdb_meta:
                            meta['rating'] = float(imdb_meta['rating'])
                        if 'runtime' in imdb_meta:
                            meta['duration'] = int(imdb_meta['runtime']) * 60
                        if 'cast' in imdb_meta:
                            meta['cast'] = imdb_meta['cast']
                        if 'cover_url' in imdb_meta:
                            meta['cover_url'] = imdb_meta['cover_url']

                return meta
            else:
                tmdb = TMDB(tmdb_api_key=self.tmdb_api_key, omdb_api_key=self.omdb_api_key, lang=utils.get_tmdb_language())
                imdb_meta = tmdb.search_imdb(name, imdb_id)
                if imdb_meta:
                    meta = tmdb.update_imdb_meta(meta, imdb_meta)
                return meta    
        else:
            return meta


    def search_movies(self, name):
        '''
        Requests meta data from TMDB for any movie matching name
        
        Args:
            name (str): full name of movie you are searching
                        
        Returns:
            Array of dictionaries with trimmed down meta data, only returned data that is required:
            - IMDB ID
            - TMDB ID
            - Name
            - Year
        ''' 
        logger.log('---------------------------------------------------------------------------------------')
        logger.log('Meta data refresh - searching for movie: %s' % name)
        tmdb = TMDB(tmdb_api_key=self.tmdb_api_key, omdb_api_key=self.omdb_api_key, lang=utils.get_tmdb_language())
        movie_list = []
        meta = tmdb.tmdb_search(name)
        if meta:
            if meta['total_results'] == 0:
                logger.log('No results found')
                return None
            for movie in meta['results']:
                if movie['release_date']:
                    year = movie['release_date'][:4]
                else:
                    year = None
                movie_list.append({'title': movie['title'],'original_title': movie['original_title'], 'imdb_id': '', 'tmdb_id': movie['id'], 'year': year})
        else:
            logger.log('No results found')
            return None

        logger.log('Returning results: %s' % movie_list)
        return movie_list


    def similar_movies(self, tmdb_id, page=1):
        '''
        Requests list of similar movies matching given tmdb id
        
        Args:
            tmdb_id (str): MUST be a valid TMDB ID
        Kwargs:
            page (int): page number of result to fetch
        Returns:
            List of dicts - each movie in it's own dict with supporting info
        ''' 
        logger.log('---------------------------------------------------------------------------------------')
        logger.log('TMDB - requesting similar movies: %s' % tmdb_id)
        tmdb = TMDB(tmdb_api_key=self.tmdb_api_key, omdb_api_key=self.omdb_api_key, lang=utils.get_tmdb_language())
        movie_list = []
        meta = tmdb.tmdb_similar_movies(tmdb_id, page)
        if meta:
            if meta['total_results'] == 0:
                logger.log('No results found')
                return None
            for movie in meta['results']:
                movie_list.append(movie)
        else:
            logger.log('No results found')
            return None

        logger.log('Returning results: %s' % movie_list)
        return movie_list


    def get_episode_meta(self, tvshowtitle, imdb_id, season, episode, air_date='', episode_title='', overlay=''):
        '''
        Requests meta data from TVDB for TV episodes, searches local cache db first.
        Args:
            tvshowtitle (str): full name of tvshow you are searching
            imdb_id (str): IMDB ID
            season (int): tv show season number, number only no other characters
            episode (int): tv show episode number, number only no other characters
        Kwargs:
            air_date (str): In cases where episodes have no episode number but only an air date - eg. daily talk shows
            episode_title (str): The title of the episode, gets set to the title infolabel which must exist
            overlay (int): To set the default watched status (6=unwatched, 7=watched) on new videos

        Returns:
            DICT. It must also return an empty dict when
            no meta info was found in order to save these.
        '''  

        logger.log('---------------------------------------------------------------------------------------')
        logger.log('Attempting to retrieve episode meta data for: imdbid: %s season: %s episode: %s air_date: %s' % (imdb_id, season, episode, air_date))

        try:
            if not season:
                season = 0
            if not episode:
                episode = 0

            if imdb_id:
                imdb_id = utils.valid_imdb_id(imdb_id)

            #Find tvdb_id for the TVshow
            tvdb_id = self._get_tvdb_id(tvshowtitle, imdb_id)

            #Check if it exists in local cache first
            meta = self._cache_lookup_episode(imdb_id, tvdb_id, season, episode, air_date)

            #If not found lets scrape online sources
            if not meta:

                #I need a tvdb id to scrape The TVDB
                if tvdb_id:
                    meta = self._get_tvdb_episode_data(tvdb_id, season, episode, air_date)
                else:
                    logger.log("No TVDB ID available, could not find TVshow with imdb: %s " % imdb_id)

                #If nothing found
                if not meta:
                    #Init episode meta structure
                    meta = meta_types.init_episode_meta(imdb_id, tvdb_id, episode_title, season, episode, air_date)


                logger.log("meta from Metahandler = %s" % meta)

                #set overlay if used, else default to unwatched
                if overlay:
                    meta['overlay'] = int(overlay)
                else:
                    meta['overlay'] = 6

                if not meta.get('title'):
                    meta['title']= episode_title

                meta['tvdb_id'] = tvdb_id
                meta['imdb_id'] = imdb_id
                meta['cover_url'] = meta.get('poster')
                meta = self._get_tv_extra(meta)

                self._cache_save_episode_meta(meta)

            #Ensure we are not sending back any None values, XBMC doesn't like them
            meta = utils.remove_none_values(meta)

            #Set Watched flag
            meta['playcount'] = utils.set_playcount(meta['overlay'])

            #Add key for subtitles to work
            meta['TVShowTitle']= tvshowtitle

            logger.log('Returned Meta: %s' % meta)
            return meta
        except:
            import traceback
            traceback.print_exc()


    def _get_tv_extra(self, meta):
        '''
        When requesting episode information, not all data may be returned
        Fill in extra missing meta information from tvshow_meta table which should
        have already been populated.
        
        Args:
            meta (dict): current meta dict
                        
        Returns:
            DICT containing the extra values
        '''
        
        if meta['imdb_id']:
            sql_select = "SELECT * FROM tvshow_meta WHERE imdb_id = '%s'" % meta['imdb_id']
        elif meta['tvdb_id']:
            sql_select = "SELECT * FROM tvshow_meta WHERE tvdb_id = '%s'" % meta['tvdb_id']
        else:
            sql_select = "SELECT * FROM tvshow_meta WHERE title = '%s'" % utils.clean_string(meta['title'].lower())
            
        logger.log('Retrieving extra TV Show information from tvshow_meta')
        logger.log('SQL SELECT: %s' % sql_select)
        
        try:     
            matchedrow = self.DB.select_single(sql_select)
        except Exception as e:
            logger.log_error('************* Error attempting to select from tvshow_meta table: %s ' % e)
            pass   

        if matchedrow:
            match = dict(matchedrow)
            meta['genre'] = match['genre']
            meta['duration'] = match['duration']
            meta['studio'] = match['studio']
            meta['mpaa'] = match['mpaa']
            meta['backdrop_url'] = match['backdrop_url']
        else:
            meta['genre'] = ''
            meta['duration'] = '0'
            meta['studio'] = ''
            meta['mpaa'] = ''
            meta['backdrop_url'] = ''

        return meta


    def _get_tvdb_id(self, name, imdb_id):
        '''
        Retrieves TVID for a tv show that has already been scraped and saved in cache db.
        
        Used when scraping for season and episode data
        
        Args:
            name (str): full name of tvshow you are searching            
            imdb_id (str): IMDB ID
                        
        Returns:
            (str) imdb_id 
        '''      
        
        #clean tvshow name of any extras       
        name =  utils.clean_string(name.lower())
        
        if imdb_id:
            sql_select = "SELECT tvdb_id FROM tvshow_meta WHERE imdb_id = '%s'" % imdb_id
        elif name:
            sql_select = "SELECT tvdb_id FROM tvshow_meta WHERE title = '%s'" % name
        else:
            return None
            
        logger.log('Retrieving TVDB ID')
        logger.log('SQL SELECT: %s' % sql_select)
        
        try:
            matchedrow = self.DB.select_single(sql_select)
        except Exception as e:
            logger.log_error('************* Error attempting to select from tvshow_meta table: %s ' % e)
            pass
                        
        if matchedrow:
                return dict(matchedrow)['tvdb_id']
        else:
            return None

     
    def update_episode_meta(self, name, imdb_id, season, episode, tvdb_id='', new_imdb_id='', new_tvdb_id=''):
        '''
        Updates and returns meta data for given episode, 
        mainly to be used with refreshing individual tv show episodes.
        
        Searches local cache DB for record, delete if found, calls get_episode_meta() to grab new data
               
        
        Args:
            name (int): full name of movie you are searching
            imdb_id (str): IMDB ID
            season (int): season number
            episode (int): episode number
        Kwargs:
            tvdb_id (str): TVDB ID
                        
        Returns:
            DICT of meta data or None if cannot be found.
        '''
        logger.log('---------------------------------------------------------------------------------------')
        logger.log('Updating episode meta data: %s IMDB: %s SEASON: %s EPISODE: %s TVDB ID: %s NEW IMDB ID: %s NEW TVDB ID: %s' % (name, imdb_id, season, episode, tvdb_id, new_imdb_id, new_tvdb_id))

      
        if imdb_id:
            imdb_id = utils.valid_imdb_id(imdb_id)
        else:
            imdb_id = ''

        #Find tvdb_id for the TVshow
        tvdb_id = self._get_tvdb_id(name, imdb_id)
        
        #Lookup in cache table for existing entry
        meta = self._cache_lookup_episode(imdb_id, tvdb_id, season, episode)
        
        #We found an entry in the DB, so lets delete it
        if meta:
            overlay = meta['overlay']
            self._cache_delete_episode_meta(imdb_id, tvdb_id, name, season, episode)
        else:
            overlay = 6
            logger.log('No match found in cache db')
       
        if not new_imdb_id:
            new_imdb_id = imdb_id
        elif not new_tvdb_id:
            new_tvdb_id = tvdb_id
            
        return self.get_episode_meta(name, imdb_id, season, episode, overlay=overlay)


    def _cache_lookup_episode(self, imdb_id, tvdb_id, season, episode, air_date=''):
        '''
        Lookup in local cache db for episode data
        
        Args:
            imdb_id (str): IMDB ID
            tvdb_id (str): TheTVDB ID
            season (str): tv show season number, number only no other characters
            episode (str): tv show episode number, number only no other characters
        Kwargs:
            air_date (str): date episode was aired - YYYY-MM-DD

        Returns:
            DICT. Returns results found or None.
        ''' 
        logger.log('Looking up episode data in cache db, imdb id: %s season: %s episode: %s air_date: %s' % (imdb_id, season, episode, air_date))
        
        try:

            sql_select = ('SELECT '
                               'episode_meta.title as title, '
                               'episode_meta.plot as plot, '
                               'episode_meta.director as director, '
                               'episode_meta.writer as writer, '
                               'tvshow_meta.genre as genre, '
                               'tvshow_meta.duration as duration, '
                               'episode_meta.premiered as premiered, '
                               'tvshow_meta.studio as studio, '
                               'tvshow_meta.mpaa as mpaa, '
                               'tvshow_meta.title as TVShowTitle, '
                               'episode_meta.imdb_id as imdb_id, '
                               'episode_meta.rating as rating, '
                               '"" as trailer_url, '
                               'episode_meta.season as season, '
                               'episode_meta.episode as episode, '
                               'episode_meta.overlay as overlay, '
                               'tvshow_meta.backdrop_url as backdrop_url, '                               
                               'episode_meta.poster as cover_url ' 
                               'FROM episode_meta, tvshow_meta '
                               'WHERE episode_meta.imdb_id = tvshow_meta.imdb_id AND '
                               'episode_meta.tvdb_id = tvshow_meta.tvdb_id AND '
                               'episode_meta.imdb_id = "%s" AND episode_meta.tvdb_id = "%s" AND '
                               )  % (imdb_id, tvdb_id)
            
            #If air_date is supplied, select on it instead of season & episode #
            if air_date:
                sql_select = sql_select + 'episode_meta.premiered = "%s" ' % air_date
            else:
                sql_select = sql_select + 'season = %s AND episode_meta.episode = %s ' % (season, episode)

            logger.log('SQL SELECT: %s' % sql_select)
            
            matchedrow = self.DB.select_single(sql_select)
        except Exception as e:
            logger.log_error('************* Error attempting to select from Episode table: %s ' % e)
            return None
                        
        if matchedrow:
            logger.log('Found episode meta information in cache table: %s' % dict(matchedrow))
            return dict(matchedrow)
        else:
            return None


    def _cache_delete_episode_meta(self, imdb_id, tvdb_id, name, season, episode, air_date=''):
        '''
        Delete meta data from SQL table
        
        Args:
            imdb_id (str): IMDB ID
            tvdb_id (str): TVDB ID
            name (str): Episode title
            season (int): Season #
            episode(int): Episode #
        Kwargs:
            air_date (str): Air Date of episode
        '''

        if imdb_id:
            sql_delete = "DELETE FROM episode_meta WHERE imdb_id = '%s' AND tvdb_id = '%s' AND season = %s" % (imdb_id, tvdb_id, season)
            if air_date:
                sql_delete = sql_delete + ' AND premiered = "%s"' % air_date
            else:
                sql_delete = sql_delete + ' AND episode = %s' % episode

        logger.log('Deleting table entry: IMDB: %s TVDB: %s Title: %s Season: %s Episode: %s ' % (imdb_id, tvdb_id, name, season, episode))
        logger.log('SQL DELETE: %s' % sql_delete)
        self.DB.commit(sql_delete)


    def _get_tvdb_episode_data(self, tvdb_id, season, episode, air_date=''):
        '''
        Initiates lookup for episode data on TVDB
        
        Args:
            tvdb_id (str): TVDB id
            season (str): tv show season number, number only no other characters
            episode (str): tv show episode number, number only no other characters
        Kwargs:
            air_date (str): Date episode was aired
                        
        Returns:
            DICT. Data found from lookup
        '''      
        
        meta = {}
        tvdb = TheTVDB(language=utils.get_tvdb_language())
        if air_date:
            try:
                episode = tvdb.get_episode_by_airdate(tvdb_id, air_date)
            except Exception as e:
                logger.log_error('************* Error retreiving from thetvdb.com: %s ' % e)
                episode = None
                pass
                
            
            #We do this because the airdate method returns just a part of the overview unfortunately
            if episode:
                ep_id = episode.id
                if ep_id:
                    try:
                        episode = tvdb.get_episode(ep_id)
                    except:
                        logger.log_error('************* Error retreiving from thetvdb.com: %s ' % e)
                        episode = None
                        pass
        else:
            try:
                episode = tvdb.get_episode_by_season_ep(tvdb_id, season, episode)
            except Exception as e:
                logger.log_error('************* Error retreiving from thetvdb.com: %s ' % e)
                episode = None
                pass
            
        if episode is None:
            return None
        
        meta['episode_id'] = episode.id
        meta['plot'] = self._check(episode.overview)
        if episode.guest_stars:
            guest_stars = episode.guest_stars
            if guest_stars.startswith('|'):
                guest_stars = guest_stars[1:-1]
            guest_stars = guest_stars.replace('|', ', ')
            meta['plot'] = meta['plot'] + '\n\nGuest Starring: ' + guest_stars
        meta['rating'] = float(self._check(episode.rating,0))
        meta['premiered'] = self._check(episode.first_aired)
        meta['title'] = self._check(episode.name)
        meta['poster'] = self._check(episode.image)
        meta['director'] = self._check(episode.director)
        meta['writer'] = self._check(episode.writer)
        meta['season'] = int(self._check(episode.season_number,0))
        meta['episode'] = int(self._check(episode.episode_number,0))
              
        return meta


    def _check(self, value, ret=None):
        if value is None or value == '':
            if ret == None:
                return ''
            else:
                return ret
        else:
            return value

    def _cache_save_episode_meta(self, meta):
        '''
        Save episode data to local cache db.
        Args:
            meta (dict): episode data to be stored
        '''
        if meta['imdb_id']:
            sql_select = 'SELECT * FROM episode_meta WHERE imdb_id = "%s" AND season = %s AND episode = %s AND premiered = "%s" AND episode_id = "%s"'  % (meta['meta_data']['imdb_id'], meta['meta_data']['season'], meta['meta_data']['episode'], meta['meta_data']['premiered'], meta['meta_data']['episode_id'])
            sql_delete = 'DELETE FROM episode_meta WHERE imdb_id = "%s" AND season = %s AND episode = %s AND premiered = "%s" AND episode_id = "%s"'  % (meta['meta_data']['imdb_id'], meta['meta_data']['season'], meta['meta_data']['episode'], meta['meta_data']['premiered'], meta['meta_data']['episode_id'])
        elif meta['tvdb_id']:
            sql_select = 'SELECT * FROM episode_meta WHERE tvdb_id = "%s" AND season = %s AND episode = %s AND premiered = "%s" AND episode_id = "%s"'  % (meta['meta_data']['tvdb_id'], meta['meta_data']['season'], meta['meta_data']['episode'], meta['meta_data']['premiered'], meta['meta_data']['episode_id'])
            sql_delete = 'DELETE FROM episode_meta WHERE tvdb_id = "%s" AND season = %s AND episode = %s AND premiered = "%s" AND episode_id = "%s"'  % (meta['meta_data']['tvdb_id'], meta['meta_data']['season'], meta['meta_data']['episode'], meta['meta_data']['premiered'], meta['meta_data']['episode_id'])
        else:         
            sql_select = 'SELECT * FROM episode_meta WHERE title = "%s" AND season = %s AND episode = %s AND premiered = "%s" AND episode_id = "%s"'  % (utils.clean_string(meta['meta_data']['title'].lower()), meta['meta_data']['season'], meta['meta_data']['episode'], meta['meta_data']['premiered'], meta['meta_data']['episode_id'])
            sql_delete = 'DELETE FROM episode_meta WHERE title = "%s" AND season = %s AND episode = %s AND premiered = "%s" AND episode_id = "%s"'  % (utils.clean_string(meta['meta_data']['title'].lower()), meta['meta_data']['season'], meta['meta_data']['episode'], meta['meta_data']['premiered'], meta['meta_data']['episode_id'])
        logger.log('Saving Episode Meta')
        logger.log('SQL Select: %s' % sql_select)
        
        matchedrow = self.DB.select_single(sql_select)
        if matchedrow:
            logger.log('Episode matched row found, deleting table entry')
            logger.log('SQL Delete: %s' % sql_delete)
            self.DB.commit(sql_delete)
        
        logger.log('Saving episode cache information: %s' % meta)
        sql_insert = self.__insert_from_dict('episode_meta', 13)
        values = (meta['meta_data']['imdb_id'], meta['meta_data']['tvdb_id'], meta['meta_data']['episode_id'], meta['meta_data']['season'], 
                            meta['meta_data']['episode'], meta['meta_data']['title'], meta['meta_data']['director'], meta['meta_data']['writer'], meta['meta_data']['plot'], 
                            meta['meta_data']['rating'], meta['meta_data']['premiered'], meta['meta_data']['poster'], meta['meta_data']['overlay'])
        logger.log('SQL INSERT: %s' % sql_insert)
        self.DB.insert(sql_insert, values)


    def update_trailer(self, media_type, imdb_id, trailer, tmdb_id=''):
        '''
        Change videos trailer
        
        Args:
            media_type (str): media_type of video to update, 'movie', 'tvshow' or 'episode'
            imdb_id (str): IMDB ID
            trailer (str): url of youtube video
        Kwargs:            
            tmdb_id (str): TMDB ID
                        
        '''      
        if media_type == 'movie':
            table='movie_meta'
        elif media_type == 'tvshow':
            table='tvshow_meta'
        
        if imdb_id:
            imdb_id = utils.valid_imdb_id(imdb_id)

        if imdb_id:
            sql_update = "UPDATE %s set trailer_url='%s' WHERE imdb_id = '%s'" % (table, trailer, imdb_id)
        elif tmdb_id:
            sql_update = "UPDATE %s set trailer_url='%s' WHERE tmdb_id = '%s'" % (table, trailer, tmdb_id)
               
        logger.log('Updating trailer for type: %s, imdb id: %s, tmdb_id: %s, trailer: %s' % (media_type, imdb_id, tmdb_id, trailer))
        logger.log('SQL UPDATE: %s' % sql_update)
        self.DB.commit(sql_update)


    def change_watched(self, media_type, name, imdb_id, tmdb_id='', season='', episode='', year='', watched='', air_date=''):
        '''
        Change watched status on video
        
        Args:
            imdb_id (str): IMDB ID
            media_type (str): type of video to update, 'movie', 'tvshow' or 'episode'
            name (str): name of video
        Kwargs:            
            season (int): season number
            episode (int): episode number
            year (int): Year
            watched (int): Can specify what to change watched status (overlay) to
                        
        '''   
        logger.log('---------------------------------------------------------------------------------------')
        logger.log('Updating watched flag for: %s %s %s %s %s %s %s %s %s' % (media_type, name, imdb_id, tmdb_id, season, episode, year, watched, air_date))

        if imdb_id:
            imdb_id = utils.valid_imdb_id(imdb_id)

        tvdb_id = ''
        if media_type in (constants.type_tvshow, constants.type_season):
            tvdb_id = self._get_tvdb_id(name, imdb_id)                                  
        
        if media_type in (constants.type_movie, constants.type_tvshow, constants.type_season):
            if not watched:
                watched = self._get_watched(media_type, imdb_id, tmdb_id, season=season)
                if watched == 6:
                    watched = 7
                else:
                    watched = 6
            self._update_watched(imdb_id, media_type, watched, tmdb_id=tmdb_id, name=utils.clean_string(name.lower()), year=year, season=season, tvdb_id=tvdb_id)                
        elif media_type == constants.type_episode:
            if tvdb_id is None:
                tvdb_id = ''
            tmp_meta = {}
            tmp_meta['imdb_id'] = imdb_id
            tmp_meta['tvdb_id'] = tvdb_id 
            tmp_meta['title'] = name
            tmp_meta['season']  = season
            tmp_meta['episode'] = episode
            tmp_meta['premiered'] = air_date

            if not watched:
                watched = self._get_watched_episode(tmp_meta)
                if watched == 6:
                    watched = 7
                else:
                    watched = 6
            self._update_watched(imdb_id, media_type, watched, name=name, season=season, episode=episode, tvdb_id=tvdb_id, air_date=air_date)


    def _update_watched(self, imdb_id, media_type, new_value, tmdb_id='', name='', year='', season='', episode='', tvdb_id='', air_date=''):
        '''
        Commits the DB update for the watched status
        
        Args:
            imdb_id (str): IMDB ID
            media_type (str): type of video to update, 'movie', 'tvshow' or 'episode'
            new_value (int): value to update overlay field with
        Kwargs:
            name (str): name of video        
            season (str): season number
            tvdb_id (str): tvdb id of tvshow                        

        '''      
        if media_type == constants.type_movie:
            if imdb_id:
                sql_update="UPDATE movie_meta SET overlay = %s WHERE imdb_id = '%s'" % (new_value, imdb_id)
            elif tmdb_id:
                sql_update="UPDATE movie_meta SET overlay = %s WHERE tmdb_id = '%s'" % (new_value, tmdb_id)
            else:
                sql_update="UPDATE movie_meta SET overlay = %s WHERE title = '%s'" % (new_value, name)
                if year:
                    sql_update = sql_update + ' AND year=%s' % year
        elif media_type == constants.type_tvshow:
            if imdb_id:
                sql_update="UPDATE tvshow_meta SET overlay = %s WHERE imdb_id = '%s'" % (new_value, imdb_id)
            elif tvdb_id:
                sql_update="UPDATE tvshow_meta SET overlay = %s WHERE tvdb_id = '%s'" % (new_value, tvdb_id)
        elif media_type == constants.type_season:
            sql_update="UPDATE season_meta SET overlay = %s WHERE imdb_id = '%s' AND season = %s" % (new_value, imdb_id, season)        
        elif media_type == constants.type_episode:
            if imdb_id:
                sql_update="UPDATE episode_meta SET overlay = %s WHERE imdb_id = '%s'" % (new_value, imdb_id)
            elif tvdb_id:
                sql_update="UPDATE episode_meta SET overlay = %s WHERE tvdb_id = '%s'" % (new_value, tvdb_id)
            else:
                return None
            
            #If we have an air date use that instead of season/episode #
            if air_date:
                sql_update = sql_update + " AND premiered = '%s'" % air_date
            else:
                sql_update = sql_update + ' AND season = %s AND episode = %s' % (season, episode)
                
        else: # Something went really wrong
            return None

        logger.log('Updating watched status for type: %s, imdb id: %s, tmdb_id: %s, new value: %s' % (media_type, imdb_id, tmdb_id, new_value))
        logger.log('SQL UPDATE: %s' % sql_update)
        try:
            self.DB.commit(sql_update)
        except:
            import traceback
            traceback.print_exc()

    def _get_watched(self, media_type, imdb_id, tmdb_id, season=''):
        '''
        Finds the watched status of the video from the cache db
        Args:
            media_type (str): type of video to update, 'movie', 'tvshow' or 'episode'                    
            imdb_id (str): IMDB ID
            tmdb_id (str): TMDB ID
        Kwargs:
            season (int): tv show season number    
        ''' 

        sql_select = ''
        if media_type == constants.type_movie:
            if imdb_id:
                sql_select="SELECT overlay FROM movie_meta WHERE imdb_id = '%s'" % imdb_id
            elif tmdb_id:
                sql_select="SELECT overlay FROM movie_meta WHERE tmdb_id = '%s'" % tmdb_id
        elif media_type == constants.type_tvshow:
            sql_select="SELECT overlay FROM tvshow_meta WHERE imdb_id = '%s'" % imdb_id
        elif media_type == constants.type_season:
            sql_select = "SELECT overlay FROM season_meta WHERE imdb_id = '%s' AND season = %s" % (imdb_id, season)
        
        logger.log('SQL Select: %s' % sql_select)
        matchedrow = self.DB.select_single(sql_select)
                    
        if matchedrow:
            return dict(matchedrow)['overlay']
        else:
            return 6

        
    def _get_watched_episode(self, meta):
        '''
        Finds the watched status of the video from the cache db
        Args:
            meta (dict): full data of episode                    
        '''
        if meta['imdb_id']:
            sql_select = "SELECT * FROM episode_meta WHERE imdb_id = '%s'"  % meta['imdb_id']
        elif meta['tvdb_id']:
            sql_select = "SELECT * FROM episode_meta WHERE tvdb_id = '%s'"  % meta['tvdb_id']
        else:         
            sql_select = "SELECT * FROM episode_meta WHERE title = '%s'"  % utils.clean_string(meta['title'].lower())
        
        if meta['premiered']:
            sql_select += " AND premiered = '%s'" % meta['premiered']
        else:
            sql_select += ' AND season = %s AND episode = %s' % (meta['season'], meta['episode'])
            
        logger.log('Getting episode watched status')
        logger.log('SQL Select: %s' % sql_select)

        matchedrow = self.DB.select_single(sql_select)
        if matchedrow:
                return dict(matchedrow)['overlay']
        else:
            return 6


    def _find_cover(self, season, images):
        '''
        Finds the url of the banner to be used as the cover 
        from a list of images for a given season
        
        Args:
            season (str): tv show season number, number only no other characters
            images (dict): all images related
                        
        Returns:
            (str) cover_url: url of the selected image
        '''         
        cover_url = ''
        
        for image in images:
            (banner_url, banner_type, banner_season) = image
            if banner_season == season and banner_type == 'season':
                cover_url = banner_url
                break
        
        return cover_url


    def update_season(self, tvshowtitle, imdb_id, season):
        '''
        Update an individual season:
            - looks up and deletes existing entry, saving watched flag (overlay)
            - re-scans TVDB for season image
        
        Args:
            tvshowtitle (str): TV Show Title
            imdb_id (str): IMDB ID
            season (int): season number to be refreshed
                        
        Returns:
            (list) list of covers found for each season
        '''     

        #Find tvdb_id for the TVshow
        tvdb_id = self._get_tvdb_id(tvshowtitle, imdb_id)

        logger.log('---------------------------------------------------------------------------------------')
        logger.log('Updating season meta data: %s IMDB: %s TVDB ID: %s SEASON: %s' % (tvshowtitle, imdb_id, tvdb_id, season))

      
        if imdb_id:
            imdb_id = utils.valid_imdb_id(imdb_id)
        else:
            imdb_id = ''
       
        #Lookup in cache table for existing entry
        meta = self._cache_lookup_season(imdb_id, tvdb_id, season)
        
        #We found an entry in the DB, so lets delete it
        if meta:
            overlay = meta['overlay']
            self._cache_delete_season_meta(imdb_id, tvdb_id, season)
        else:
            overlay = 6
            logger.log('No match found in cache db')

        return self.get_seasons(tvshowtitle, imdb_id, season, overlay)


    def _get_tvshow_backdrops(self, imdb_id, tvdb_id):
        '''
        Gets the backdrop_url from tvshow_meta to be included with season & episode meta
        
        Args:              
            imdb_id (str): IMDB ID
            tvdb_id (str): TVDB ID

        ''' 

        sql_select = "SELECT backdrop_url FROM tvshow_meta WHERE imdb_id = '%s' AND tvdb_id = '%s'" % (imdb_id, tvdb_id)
        
        logger.log('SQL Select: %s' % sql_select)
        
        matchedrow = self.DB.select_single(sql_select) 
                   
        if matchedrow:
            return dict(matchedrow)['backdrop_url']
        else:
            return ''


    def _get_season_posters(self, tvdb_id, season):
        tvdb = TheTVDB(language=utils.get_tvdb_language())
        
        try:
            images = tvdb.get_show_image_choices(tvdb_id)
        except Exception as e:
            logger.log_error('************* Error retreiving from thetvdb.com: %s ' % e)
            images = None
            pass
            
        return images
        

    def _cache_lookup_season(self, imdb_id, tvdb_id, season):
        '''
        Lookup data for a given season in the local cache DB.
        
        Args:
            imdb_id (str): IMDB ID
            tvdb_id (str): TVDB ID
            season (str): tv show season number, number only no other characters
                        
        Returns:
            (dict) meta data for a match
        '''      
        
        logger.log('Looking up season data in cache db, imdb id: %s tvdb_id: %s season: %s' % (imdb_id, tvdb_id, season))
        
        if imdb_id:
            sql_select = "SELECT a.*, b.backdrop_url FROM season_meta a, tvshow_meta b WHERE a.imdb_id = '%s' AND season =%s and a.imdb_id=b.imdb_id and a.tvdb_id=b.tvdb_id"  % (imdb_id, season)
        elif tvdb_id:
            sql_select = "SELECT a.*, b.backdrop_url FROM season_meta a, tvshow_meta b WHERE a.tvdb_id = '%s' AND season =%s  and a.imdb_id=b.imdb_id and a.tvdb_id=b.tvdb_id"  % (tvdb_id, season)
        else:
            return None
            
          
        logger.log('SQL Select: %s' % sql_select)
        
        matchedrow = self.DB.select_single(sql_select)
                    
        if matchedrow:
            logger.log('Found season meta information in cache table: %s' % dict(matchedrow))
            return dict(matchedrow)
        else:
            return None


    def _cache_save_season_meta(self, meta):
        '''
        Save data for a given season in local cache DB.
        
        Args:
            meta (dict): full meta data for season
        '''     
        
        matchedrow = self.DB.select_single("SELECT * FROM season_meta WHERE imdb_id = '%s' AND season ='%s' " 
                            % ( meta['imdb_id'], meta['season'] ) ) 
        if matchedrow:
            logger.log('Season matched row found, deleting table entry')
            self.DB.commit("DELETE FROM season_meta WHERE imdb_id = '%s' AND season ='%s' " 
                                % ( meta['imdb_id'], meta['season'] ) )
                    
        logger.log('Saving season cache information: %s' % meta)
        sql_insert = self.__insert_from_dict('season_meta', 5)
        logger.log('SQL Insert: %s' % sql_insert)
        values = (meta['imdb_id'],meta['tvdb_id'],meta['season'],meta['cover_url'],meta['overlay'])
        self.DB.insert(sql_insert, values)


    def _cache_delete_season_meta(self, imdb_id, tvdb_id, season):
        '''
        Delete meta data from SQL table
        
        Args:
            imdb_id (str): IMDB ID
            tvdb_id (str): TVDB ID
            season (int): Season #
        '''

        sql_delete = "DELETE FROM season_meta WHERE imdb_id = '%s' AND tvdb_id = '%s' and season = %s" % (imdb_id, tvdb_id, season)

        logger.log('Deleting table entry: IMDB: %s TVDB: %s Season: %s ' % (imdb_id, tvdb_id, season))
        logger.log('SQL DELETE: %s' % sql_delete)
        self.DB.commit(sql_delete)


    def get_batch_meta(self, media_type, batch_ids):
        '''
        Main method to get meta data for movie or tvshow. Will lookup by name/year 
        if no IMDB ID supplied.       
        
        Args:
            media_type (str): 'movie' or 'tvshow'
            batch_ids (tuple): a list of tuples containing the following in order:
                                - imdb_id (str)
                                - tmdb_id (str)
                                - movie/tvshow name (str)
                                - year (int)
        Returns:
            DICT of meta data or None if cannot be found.
        '''
       
        logger.log('---------------------------------------------------------------------------------------')
        logger.log('Starting batch meta grab')
        logger.log('Batch meta information passed in: %s' % batch_ids)

        #Ensure IMDB ID's are formatted properly first
        new_batch_ids = []
        for i,(imdb_id, tmdb_id, vidname, year) in enumerate(batch_ids):
            new_batch_ids.append((utils.valid_imdb_id(imdb_id), tmdb_id, vidname, year))

        #Check each record and determine if should query cache db against ID's or Name & Year
        batch_ids = []
        batch_names = []
        for x in new_batch_ids:
            if x[0] or x[1]:
                batch_ids.append((x[0], x[1], x[2], x[3]))
            else:
                batch_names.append((x[0], x[1], x[2], x[3]))
        
        cache_meta = []
        #Determine how and then check local cache for meta data
        if batch_ids:
            temp_cache = self.__cache_batch_lookup_by_id(media_type, batch_ids)
            if temp_cache:
                cache_meta += temp_cache
        
        if batch_names:
            temp_cache = self.__cache_batch_lookup_by_id(media_type, batch_names)
            if temp_cache:
                cache_meta += temp_cache            

        #Check if any records were not found in cache, store them in list if not found
        no_cache_ids = []
        if cache_meta:
            for m in new_batch_ids:
                try:
                    x = next((i for i,v in enumerate(cache_meta) if v['imdb_id'] == m[0] or v['tmdb_id'] == m[1] or v['name'] == m[2] ), None)
                except:
                    x = None
                if x is None:
                    no_cache_ids.append(m)
        else:
            cache_meta = []
            no_cache_ids = new_batch_ids

        new_meta = []

        for record in no_cache_ids:
            
            if media_type==constants.type_movie:
                meta = self._get_tmdb_meta(record[0], record[1], record[2], record[3])
                logger.log('---------------------------------------------------------------------------------------')
            elif media_type==constants.type_tvshow:
                #meta = self._get_tvdb_meta(record[0], record[1], record[2], record[3])
                meta = self._get_tvdb_meta(record[0], record[1], record[2])
                logger.log('---------------------------------------------------------------------------------------')

            new_meta.append(meta)
            
        #If we found any new meta, add it to our cache list
        if new_meta:
            cache_meta += new_meta
            
            #Save any new meta to cache
            self._cache_save_video_meta(new_meta, 'test', media_type)
        
        #Format and return final list of meta
        return_meta = []
        for meta in cache_meta:
            if type(meta) is self.DB.database.Row:
                meta = dict(meta)
            meta = self.__format_meta(media_type, meta,'test')
            return_meta.append(meta)
        
        return return_meta


    def __cache_batch_lookup_by_id(self, media_type, batch_ids):
        '''
        Lookup in SQL DB for video meta data by IMDB ID
        
        Args:
            media_type (str): 'movie' or 'tvshow'
            batch_ids (tuple): a list of list items containing the following in order:
                                - imdb_id (str)*
                                - tmdb_id (str)
                                - name (str)
                                - year (int)
        Returns:
            DICT of matched meta data or None if no match.
        '''        

        placeholder= '?'
        placeholders= ', '.join(placeholder for x in batch_ids)
        
        ids = []
        if media_type == constants.type_movie:
            sql_select = "SELECT * FROM movie_meta a"
            
            #If there is an IMDB ID given then use it for entire operation
            if batch_ids[0][0]:
                sql_select = sql_select + " WHERE a.imdb_id IN (%s)" % placeholders
                for x in batch_ids:
                    ids.append(x[0])
                    
            #If no IMDB but TMDB then use that instead
            elif batch_ids[0][1]:
                sql_select = sql_select + " WHERE a.tmdb_id IN (%s)" % placeholders
                for x in batch_ids:
                    ids.append(x[1])
                    
            #If no id's given then default to use the name and year
            elif batch_ids[0][2]:
                 
                #If we have a year then need to inner join with same table
                if batch_ids[0][3]:
                    sql_select = sql_select + (" INNER JOIN "
                                                    "(SELECT title, year FROM movie_meta "
                                                             "WHERE year IN (%s)) b "
                                                  "ON a.title = b.title AND a.year = b.year "
                                                "WHERE a.title in (%s) ") % (placeholders, placeholders)

                #If no year then just straight select on name
                else:
                    sql_select = sql_select + " WHERE a.title IN (%s)" % placeholders
                    for x in batch_ids:
                        ids.append(utils.clean_string(x[2].lower()))
            else:
                logger.log_error('No data given to create SQL SELECT or data types are currently unsupported')
                return None

        logger.log( 'SQL Select: %s' % sql_select)

        matchedrows = self.DB.select_all(sql_select, ids)
       
        if matchedrows:
            for row in matchedrows:
                logger.log('Found meta information by id in cache table: %s' % dict(row))
            return matchedrows
        else:
            logger.log('No match in local DB')
            return None
