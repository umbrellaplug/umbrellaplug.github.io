def init_movie_meta(imdb_id, tmdb_id, name, year=0):
    '''
    Initializes a movie_meta dictionary with default values, to ensure we always
    have all fields
    
    Args:
        imdb_id (str): IMDB ID
        tmdb_id (str): TMDB ID
        name (str): full name of movie you are searching
        year (int): 4 digit year
                    
    Returns:
        DICT in the structure of what is required to write to the DB
    '''                
    return {
        'meta_data' : __movie_meta(imdb_id, tmdb_id, name, year),
        'art_data' : __art_meta(),
        'cast_data' : __cast_meta()
    }


def init_tvshow_meta(imdb_id, tvdb_id, name, year=0):
    '''
    Initializes a tvshow_meta dictionary with default values, to ensure we always
    have all fields
    
    Args:
        imdb_id (str): IMDB ID
        tvdb_id (str): TVDB ID
        name (str): full name of movie you are searching
        year (int): 4 digit year
                    
    Returns:
        DICT in the structure of what is required to write to the DB
    '''
    return {
        'meta_data' : __tvshow_meta(imdb_id, tvdb_id, name, year),
        'art_data' : __art_meta(),
        'cast_data' : __cast_meta()
    }


def init_episode_meta(imdb_id, tvdb_id, episode_title, season, episode, air_date):
    '''
    Initializes a movie_meta dictionary with default values, to ensure we always
    have all fields
    
    Args:
        imdb_id (str): IMDB ID
        tvdb_id (str): TVDB ID
        episode_title (str): full name of Episode you are searching - NOT TV Show name
        season (int): episode season number
        episode (int): episode number
        air_date (str): air date (premiered data) of episode - YYYY-MM-DD
                    
    Returns:
        DICT in the structure of what is required to write to the DB
    '''
    return {
        'meta_data' : __episode_meta(imdb_id, tvdb_id, episode_title, season, episode, air_date),
        'art_data' : __art_meta(),
        'cast_data' : __cast_meta()
    }


def __movie_meta(imdb_id, tmdb_id, name, year=0):
    '''
    Initializes a movie_meta dictionary with default values, to ensure we always
    have all fields
    
    Args:
        imdb_id (str): IMDB ID
        tmdb_id (str): TMDB ID
        name (str): full name of movie you are searching
        year (int): 4 digit year
                    
    Returns:
        DICT in the structure of what is required to write to the DB
    '''                
    
    if year:
        int(year)
    else:
        year = 0
        
    return {
        'imdb_id' : imdb_id,
        'tmdb_id' : str(tmdb_id),   
        'backdrop_url' : '',
        'cast' : [],
        'cover_url' : '',
        'director' : '',
        'duration' : '',
        'genre' : '',
        'IMDBNumber' : '',
        'mpaa' : '',
        'overlay' : 6,
        'plot' : '',
        'premiered' : '',
        'rating' : 0,
        'studio' : '',
        'tagline' : '',
        'thumb_url' : '',
        'title' : name,
        'trailer' : '',
        'trailer_url' : '',
        'votes' : '',
        'writer' : '',
        'year' : int(year),
    }


def __tvshow_meta(imdb_id, tvdb_id, name, year=0):
    '''
    Initializes a tvshow_meta dictionary with default values, to ensure we always
    have all fields
    
    Args:
        imdb_id (str): IMDB ID
        tvdb_id (str): TVDB ID
        name (str): full name of movie you are searching
        year (int): 4 digit year
                    
    Returns:
        DICT in the structure of what is required to write to the DB
    '''
    
    if year:
        int(year)
    else:
        year = 0
        
    return {
        'imdb_id' : imdb_id,
        'tvdb_id' : tvdb_id,
        'title' : name,
        'TVShowTitle' : name,
        'rating' : 0,
        'duration' : '',
        'plot' : '',
        'mpaa' : '',
        'premiered' : '',
        'year' : int(year),
        'trailer_url' : '',
        'genre' : '',
        'studio' : '',
        'status' : '' ,       
        'cast' : [],
        'banner_url' : '' ,
        'cover_url' : '',
        'backdrop_url' : '',
        'overlay' : 6,
        'episode' : 0,
        'playcount' : 0,
    }


def __episode_meta(imdb_id, tvdb_id, episode_title, season, episode, air_date):
    '''
    Initializes a movie_meta dictionary with default values, to ensure we always
    have all fields
    
    Args:
        imdb_id (str): IMDB ID
        tvdb_id (str): TVDB ID
        episode_title (str): full name of Episode you are searching - NOT TV Show name
        season (int): episode season number
        episode (int): episode number
        air_date (str): air date (premiered data) of episode - YYYY-MM-DD
                    
    Returns:
        DICT in the structure of what is required to write to the DB
    '''

    return {
        'imdb_id' : imdb_id,
        'tvdb_id' : '',
        'episode_id' : '',
        'season' : int(season),
        'episode' : int(episode),
        'title' : episode_title,
        'director' : '',
        'writer' : '',
        'plot' : '',
        'rating' : 0,
        'premiered' : air_date,
        'poster' : '',
        'cover_url' : '',
        'trailer_url' : '',
        'premiered' : '',
        'backdrop_url' : '',
        'overlay' : 6
    }


def __art_meta():
    '''
    Initializes a art meta dictionary with default values, to ensure we always
    have all fields
                   
    Returns:
        DICT in the structure of what is required to write to the DB
    '''
    
    return {
        'thumb' : '',
        'poster' : '',
        'banner' : '',
        'fanart' : '',
        'clearart' : '',
        'clearlogo' : '',
        'landscape' : '',
        'icon' : ''
    }


def __cast_meta():
    '''
    Initializes a art meta dictionary with default values, to ensure we always
    have all fields
                   
    Returns:
        DICT in the structure of what is required to write to the DB
    '''
    
    return {
        'name' : '',
        'role' : '',
        'thumbnail' : '',
        'order' : 0
    }
    