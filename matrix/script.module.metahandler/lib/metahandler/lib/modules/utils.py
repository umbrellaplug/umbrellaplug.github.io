import os
import re
from datetime import datetime
import time

import xbmcvfs
from metahandler.lib.modules import log_utils
from metahandler.lib.modules import kodi

logger = log_utils.Logger.get_logger()


def make_dir(mypath, dirname):
    ''' Creates sub-directories if they are not found. '''
    subpath = os.path.join(mypath, dirname)
    try:
        if not xbmcvfs.exists(subpath): xbmcvfs.mkdirs(subpath)
    except:
        if not os.path.exists(subpath): os.makedirs(subpath)              
    return subpath


def bool2string(myinput):
    ''' Neatens up usage of prepack_images flag. '''
    if myinput is False: return 'false'
    elif myinput is True: return 'true'


def string_compare(s1, s2):
    """ Method that takes two strings and returns True or False, based
        on if they are equal, regardless of case.
    """
    try:
        return s1.lower() == s2.lower()
    except AttributeError:
        logger.log_error("Please only pass strings into this method.")
        logger.log_error("You passed a %s and %s" % (s1.__class__, s2.__class__))


def clean_string(string):
    """ 
        Method that takes a string and returns it cleaned of any special characters
        in order to do proper string comparisons
    """        
    try:
        return ''.join(e for e in string if e.isalnum())
    except:
        return string


def convert_date(string, in_format, out_format):
    ''' Helper method to convert a string date to a given format '''
    
    #Legacy check, Python 2.4 does not have strptime attribute, instroduced in 2.5
    if hasattr(datetime, 'strptime'):
        strptime = datetime.strptime
    else:
        strptime = lambda date_string, format: datetime(*(time.strptime(date_string, format)[0:6]))
    
    #strptime = lambda date_string, format: datetime(*(time.strptime(date_string, format)[0:6]))
    try:
        a = strptime(string, in_format).strftime(out_format)
    except Exception as e:
        logger.log_error('************* Error Date conversion failed: %s' % e)
        return None
    return a


def remove_none_values(meta):
    ''' Ensure we are not sending back any None values, XBMC doesn't like them '''
    for item in meta:
        if meta[item] is None:
            meta[item] = ''            
    return meta


def valid_imdb_id(imdb_id):
    '''
    Check and return a valid IMDB ID    
    
    Args:
        imdb_id (str): IMDB ID
    Returns:
        imdb_id (str) if valid with leading tt, else None
    '''      
    # add the tt if not found. integer aware.
    if imdb_id:
        if not imdb_id.startswith('tt'):
            imdb_id = 'tt%s' % imdb_id
        if re.search('tt[0-9]{7}', imdb_id):
            return imdb_id
        else:
            return None


def set_playcount(overlay):
    '''
    Quick function to check overlay and set playcount
    Playcount info label is required to have > 0 in order for watched flag to display in Frodo
    '''
    if int(overlay) == 7:
        return 1
    else:
        return 0


def get_tmdb_language():
    tmdb_language = kodi.get_setting('tmdb_language')
    if tmdb_language:
        return re.sub(".*\((\w+)\).*","\\1",tmdb_language)
    else:
        return 'en'

        
def get_tvdb_language() :
    tvdb_language =kodi.get_setting('tvdb_language')
    if tvdb_language and tvdb_language!='':
        return re.sub(".*\((\w+)\).*","\\1",tvdb_language)
    else:
        return 'en'