from metahandler.lib.modules import kodi
from metahandler.lib.modules import db_utils
from metahandler.lib.modules import log_utils

import xbmcvfs

logger = log_utils.Logger.get_logger()

class DB_Connection():

    def __init__(self, videocache):
        """
        Initialize DB, either MYSQL or SQLITE
        """   

        '''
        Use SQLIte3 wherever possible, needed for newer versions of XBMC/Kodi
        Keep pysqlite2 for legacy support
        '''
        try:
            if  kodi.get_setting('use_remote_db')=='true' and   \
                kodi.get_setting('db_address') and \
                kodi.get_setting('db_user') and \
                kodi.get_setting('db_pass') and \
                kodi.get_setting('db_name'):
                import mysql.connector as new_database
                logger.log_info('Loading MySQLdb as DB engine version: %s' % new_database.version.VERSION_TEXT)
                self.DB_Type = 'mysql'
            else:
                raise ValueError('MySQL not enabled or not setup correctly')
        except:
            from sqlite3 import dbapi2 as new_database
            logger.log_info('Loading sqlite3 as DB engine version: %s' % new_database.sqlite_version)
            self.DB_Type = 'sqlite'

        self.videocache = videocache
        self.database = new_database

        if self.DB_Type == 'mysql':
            class MySQLCursorDict(self.database.cursor.MySQLCursor):
                def _row_to_python(self, rowdata, desc=None):
                    row = super(MySQLCursorDict)._row_to_python(rowdata, desc)
                    if row:
                        return dict(zip(column_names, row))
                    return None
            db_address = kodi.get_setting('db_address')
            db_port = kodi.get_setting('db_port')
            if not db_port: db_port = '3306'
            db_user = kodi.get_setting('db_user')
            db_pass = kodi.get_setting('db_pass')
            db_name = kodi.get_setting('db_name')
            self.dbcon = self.database.connect(database=db_name, user=db_user, password=db_pass, host=db_address, port=db_port, buffered=True)
            self.dbcur = self.dbcon.cursor(cursor_class=MySQLCursorDict, buffered=True)
        else:
            self.dbcon = self.database.connect(videocache)
            self.dbcon.row_factory = self.database.Row # return results indexed by field names and not numbers so we can convert to dict
            self.dbcur = self.dbcon.cursor()

        # initialize cache db
        self.__create_cache_db()


    def __del__(self):
        ''' Cleanup db when object destroyed '''
        try:
            self.dbcur.close()
            self.dbcon.close()
        except: pass


    def __create_cache_db(self):
        ''' Creates the cache tables if they do not exist.  '''   

        # Create Movie table
        sql_create = "CREATE TABLE IF NOT EXISTS movie_meta ("\
                            "imdb_id TEXT, "\
                            "tmdb_id TEXT, "\
                            "title TEXT, "\
                            "year INTEGER,"\
                            "director TEXT, "\
                            "writer TEXT, "\
                            "tagline TEXT, cast TEXT,"\
                            "rating FLOAT, "\
                            "votes TEXT, "\
                            "duration TEXT, "\
                            "plot TEXT,"\
                            "mpaa TEXT, "\
                            "premiered TEXT, "\
                            "genre TEXT, "\
                            "studio TEXT,"\
                            "thumb_url TEXT, "\
                            "cover_url TEXT, "\
                            "trailer_url TEXT, "\
                            "backdrop_url TEXT,"\
                            "imgs_prepacked TEXT,"\
                            "overlay INTEGER,"\
                            "UNIQUE(imdb_id, tmdb_id, title, year)"\
                            ");"
        if self.DB_Type == 'mysql':
            sql_create = sql_create.replace("imdb_id TEXT","imdb_id VARCHAR(10)")
            sql_create = sql_create.replace("tmdb_id TEXT","tmdb_id VARCHAR(10)")
            sql_create = sql_create.replace("title TEXT"  ,"title VARCHAR(255)")

            # hack to bypass bug in myconnpy
            # create table if not exists fails bc a warning about the table
            # already existing bubbles up as an exception. This suppresses the
            # warning which would just be logged anyway.
            # http://stackoverflow.com/questions/1650946/mysql-create-table-if-not-exists-error-1050
            sql_hack = "SET sql_notes = 0;"
            self.dbcur.execute(sql_hack)
            
            self.dbcur.execute(sql_create)
            try: self.dbcur.execute('CREATE INDEX nameindex on movie_meta (title);')
            except: pass
        else:
            self.dbcur.execute(sql_create)
            self.dbcur.execute('CREATE INDEX IF NOT EXISTS nameindex on movie_meta (title);')
        logger.log('Table movie_meta initialized')
        
        # Create TV Show table
        sql_create = "CREATE TABLE IF NOT EXISTS tvshow_meta ("\
                            "imdb_id TEXT, "\
                            "tvdb_id TEXT, "\
                            "title TEXT, "\
                            "year INTEGER,"\
                            "cast TEXT,"\
                            "rating FLOAT, "\
                            "duration TEXT, "\
                            "plot TEXT,"\
                            "mpaa TEXT, "\
                            "premiered TEXT, "\
                            "genre TEXT, "\
                            "studio TEXT,"\
                            "status TEXT,"\
                            "banner_url TEXT, "\
                            "cover_url TEXT,"\
                            "trailer_url TEXT, "\
                            "backdrop_url TEXT,"\
                            "imgs_prepacked TEXT,"\
                            "overlay INTEGER,"\
                            "UNIQUE(imdb_id, tvdb_id, title)"\
                            ");"

        if self.DB_Type == 'mysql':
            sql_create = sql_create.replace("imdb_id TEXT","imdb_id VARCHAR(10)")
            sql_create = sql_create.replace("tvdb_id TEXT","tvdb_id VARCHAR(10)")
            sql_create = sql_create.replace("title TEXT"  ,"title VARCHAR(255)")
            self.dbcur.execute(sql_create)
            try: self.dbcur.execute('CREATE INDEX nameindex on tvshow_meta (title);')
            except: pass
        else:
            self.dbcur.execute(sql_create)
            self.dbcur.execute('CREATE INDEX IF NOT EXISTS nameindex on tvshow_meta (title);')
        logger.log('Table tvshow_meta initialized')

        # Create Season table
        sql_create = "CREATE TABLE IF NOT EXISTS season_meta ("\
                            "imdb_id TEXT, "\
                            "tvdb_id TEXT, " \
                            "season INTEGER, "\
                            "cover_url TEXT,"\
                            "overlay INTEGER,"\
                            "UNIQUE(imdb_id, tvdb_id, season)"\
                            ");"
                
        if self.DB_Type == 'mysql':
            sql_create = sql_create.replace("imdb_id TEXT","imdb_id VARCHAR(10)")
            sql_create = sql_create.replace("tvdb_id TEXT","tvdb_id VARCHAR(10)")
            self.dbcur.execute(sql_create)
        else:
            self.dbcur.execute(sql_create)
        logger.log('Table season_meta initialized')
                
        # Create Episode table
        sql_create = "CREATE TABLE IF NOT EXISTS episode_meta ("\
                            "imdb_id TEXT, "\
                            "tvdb_id TEXT, "\
                            "episode_id TEXT, "\
                            "season INTEGER, "\
                            "episode INTEGER, "\
                            "title TEXT, "\
                            "director TEXT, "\
                            "writer TEXT, "\
                            "plot TEXT, "\
                            "rating FLOAT, "\
                            "premiered TEXT, "\
                            "poster TEXT, "\
                            "overlay INTEGER, "\
                            "UNIQUE(imdb_id, tvdb_id, episode_id, title)"\
                            ");"
        if self.DB_Type == 'mysql':
            sql_create = sql_create.replace("imdb_id TEXT"   ,"imdb_id VARCHAR(10)")
            sql_create = sql_create.replace("tvdb_id TEXT"   ,"tvdb_id VARCHAR(10)")
            sql_create = sql_create.replace("episode_id TEXT","episode_id VARCHAR(10)")
            sql_create = sql_create.replace("title TEXT"     ,"title VARCHAR(255)")
            self.dbcur.execute(sql_create)
        else:
            self.dbcur.execute(sql_create)

        logger.log('Table episode_meta initialized')

        # Create Addons table
        sql_create = "CREATE TABLE IF NOT EXISTS addons ("\
                            "addon_id TEXT, "\
                            "movie_covers TEXT, "\
                            "tv_covers TEXT, "\
                            "tv_banners TEXT, "\
                            "movie_backdrops TEXT, "\
                            "tv_backdrops TEXT, "\
                            "last_update TEXT, "\
                            "UNIQUE(addon_id)"\
                            ");"

        if self.DB_Type == 'mysql':
            sql_create = sql_create.replace("addon_id TEXT", "addon_id VARCHAR(255)")
            self.dbcur.execute(sql_create)
        else:
            self.dbcur.execute(sql_create)
        logger.log('Table addons initialized')

        # Create Configuration table
        sql_create = "CREATE TABLE IF NOT EXISTS config ("\
                            "setting TEXT, "\
                            "value TEXT, "\
                            "UNIQUE(setting)"\
                            ");"

        if self.DB_Type == 'mysql':
            sql_create = sql_create.replace("setting TEXT", "setting VARCHAR(255)")
            sql_create = sql_create.replace("value TEXT", "value VARCHAR(255)")
            self.dbcur.execute(sql_create)
        else:
            self.dbcur.execute(sql_create)
        logger.log('Table config initialized')
        

    def select_single(self, query):
        try:
            self.dbcur.execute(query)
            return self.dbcur.fetchone()
        # except sqlite3.Error as e:
        #     logger.log_error('************* Error selecting from sqlite cache table: %s ' % e)
        #     pass
        # except (MySQLdb.Error, MySQLdb.Warning) as e:
        #     logger.log_error('************* Error selecting from mysql cache table: %s ' % e)
        #     pass
        except Exception as e:
            logger.log_error('************* Error selecting from cache table: %s ' % e)
            pass


    def select_all(self, query, parms=None):
        try:
            if parms:
                self.dbcur.execute(query, parms)
            else:
                self.dbcur.execute(query)
            return self.dbcur.fetchall()
        # except sqlite3.Error as e:
        #     logger.log_error('************* Error selecting from sqlite cache table: %s ' % e)
        #     pass
        # except (MySQLdb.Error, MySQLdb.Warning) as e:
        #     logger.log_error('************* Error selecting from mysql cache table: %s ' % e)
        #     pass
        except Exception as e:
            logger.log_error('************* Error selecting from cache table: %s ' % e)
            pass


    def insert(self, query, values):
        try:
            self.dbcur.execute(query, values)
            self.dbcon.commit()
        # except sqlite3.Error as e:
        #     logger.log_error('************* Error inserting to sqlite cache table: %s ' % e)
        #     pass
        # except (MySQLdb.Error, MySQLdb.Warning) as e:
        #     logger.log_error('************* Error inserting to mysql cache table: %s ' % e)
        #     pass
        except Exception as e:
            logger.log_error('************* Error inserting to cache table: %s ' % e)
            pass


    def commit(self, query):
        try:
            self.dbcur.execute(query)
            self.dbcon.commit()
        # except sqlite3.Error as e:
        #     logger.log_error('************* Error committing to sqlite cache table: %s ' % e)
        #     pass
        # except (MySQLdb.Error, MySQLdb.Warning) as e:
        #     logger.log_error('************* Error committing to mysql cache table: %s ' % e)
        #     pass
        except Exception as e:
            logger.log_error('************* Error committing to cache table: %s ' % e)
            pass


    def delete_cache_db(self) :
        logger.log_info("Metahandler - deleting cache database...")
        try:
            if xbmcvfs.exists(self.videocache): xbmcvfs.delete(self.videocache)
            return True
        except Exception as e:
            logger.log_warning('Failed to delete cache DB: %s' % e)
            return False
