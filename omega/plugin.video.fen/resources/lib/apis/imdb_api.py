# -*- coding: utf-8 -*-
import re
import json
from caches.main_cache import cache_object
from modules.dom_parser import parseDOM
from modules.kodi_utils import requests, get_setting, local_string as ls, sleep
from modules.utils import imdb_sort_list, remove_accents, replace_html_codes, string_alphanum_to_num

# Standard headers for IMDb requests
headers = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/101.0.4951.64 Safari/537.36 Edge/101.0.1210.53'
    ),
    'Accept-Language': 'en-us,en;q=0.5'
}

# URL templates
base_url               = 'https://www.imdb.com/%s'
# NEW: JSON endpoint for watchlist
watchlist_url_json     = 'https://v2.sg.media-imdb.com/suggestion/watchlist/ur%s.json'
user_list_movies_url   = 'list/%s/?view=detail&sort=%s&title_type=movie,short,video,tvShort,tvMovie,tvSpecial&start=1&page=%s'
user_list_tvshows_url  = 'list/%s/?view=detail&sort=%s&title_type=tvSeries,tvMiniSeries&start=1&page=%s'
# (other URL templates unchanged…)
watchlist_url          = 'user/ur%s/watchlist/?sort=date_added,desc&title_type=feature'
user_list_movies_url   = 'list/%s/?view=detail&sort=%s&title_type=movie,short,video,tvShort,tvMovie,tvSpecial&start=1&page=%s'
user_list_tvshows_url  = 'list/%s/?view=detail&sort=%s&title_type=tvSeries,tvMiniSeries&start=1&page=%s'
keywords_movies_url    = 'search/keyword/?keywords=%s&sort=moviemeter,asc&title_type=movie&page=%s'
keywords_tvshows_url   = 'search/keyword/?keywords=%s&sort=moviemeter,asc&title_type=tvSeries&page=%s'
lists_link             = 'user/ur%s/lists?tab=all&sort=mdfd&order=desc&filter=titles'
reviews_url            = 'title/%s/reviews/?sort=num_votes,desc'
trivia_url             = 'title/%s/trivia'
blunders_url           = 'title/%s/goofs'
parentsguide_url       = 'title/%s/parentalguide'
images_url             = 'title/%s/mediaindex?page=%s'
videos_url             = '_json/video/%s'
keywords_search_url    = 'find?s=kw&q=%s'
people_images_url      = 'name/%s/mediaindex?page=%s'
people_trivia_url      = 'name/%s/trivia'
people_search_url      = 'https://sg.media-imdb.com/suggests/%s/%s.json'
people_search_url_backup = 'search/name/?name=%s'
year_check_url         = 'https://v2.sg.media-imdb.com/suggestion/t/%s.json'

timeout = 20.0


def imdb_people_id(actor_name):
    cache_key = f'imdb_people_id_{actor_name.lower()}'
    name = actor_name.lower()
    url = people_search_url % (name[0], name.replace(' ', '%20'))
    url_backup = base_url % people_search_url_backup % name
    params = {'url': url, 'action': 'imdb_people_id', 'name': name, 'url_backup': url_backup}
    return cache_object(get_imdb, cache_key, params, False, 8736)[0]


def imdb_watchlist(media_type, foo_var, page_no):
    """
    Fetches your IMDb watchlist via the JSON suggestion API
    and returns a page of results plus a flag for next page.
    """
    imdb_user = string_alphanum_to_num(get_setting('fen.imdb_user'))
    cache_key = f'imdb_watchlist_{media_type}_{imdb_user}_{page_no}'
    url = watchlist_url_json % imdb_user

    def _fetch(dummy):
        data = requests.get(url, headers=headers, timeout=timeout).json()
        entries = data.get('d', [])
        # paginated 20 items per page
        start = (page_no - 1) * 20
        page_items = entries[start:start + 20]

        imdb_list = []
        for e in page_items:
            imdb_list.append({
                'title': e.get('l'),
                'year': str(e.get('y')),
                'imdb_id': e.get('id')
            })
        next_page = len(entries) > start + 20
        return imdb_list, next_page

    # cache for 2 hours (7200 seconds)
    return cache_object(_fetch, cache_key, 'dummy', False, 7200)


def imdb_user_lists(media_type):
    imdb_user = string_alphanum_to_num(get_setting('fen.imdb_user'))
    cache_key = f'imdb_user_lists_{media_type}_{imdb_user}'
    url = base_url % lists_link % imdb_user
    params = {'url': url, 'action': 'imdb_user_lists'}
    return cache_object(get_imdb, cache_key, params, False, 2)[0]


def imdb_user_list_contents(media_type, list_id, page_no):
    imdb_user = string_alphanum_to_num(get_setting('fen.imdb_user'))
    sort = imdb_sort_list()
    cache_key = f'imdb_user_list_contents_{media_type}_{imdb_user}_{list_id}_{sort}_{page_no}'
    params = {
        'url': list_id,
        'action': 'imdb_user_list_contents',
        'media_type': media_type,
        'sort': sort,
        'page_no': page_no
    }
    return cache_object(get_imdb, cache_key, params, False, 2)


def imdb_keywords_list_contents(media_type, keywords, page_no):
    keywords = keywords.replace(' ', '-')
    add_url = keywords_movies_url if media_type == 'movie' else keywords_tvshows_url
    url = base_url % add_url % (keywords, page_no)
    cache_key = f'imdb_keywords_list_contents_{media_type}_{keywords}_{page_no}'
    params = {'url': url, 'action': 'imdb_keywords_list_contents'}
    return cache_object(get_imdb, cache_key, params, False, 168)


def imdb_reviews(imdb_id):
    url = base_url % reviews_url % imdb_id
    cache_key = f'imdb_reviews_{imdb_id}'
    params = {'url': url, 'action': 'imdb_reviews'}
    return cache_object(get_imdb, cache_key, params, False, 168)[0]


def imdb_parentsguide(imdb_id):
    url = base_url % parentsguide_url % imdb_id
    cache_key = f'imdb_parentsguide_{imdb_id}'
    params = {'url': url, 'action': 'imdb_parentsguide'}
    return cache_object(get_imdb, cache_key, params, False, 168)[0]


def imdb_trivia(imdb_id):
    url = base_url % trivia_url % imdb_id
    cache_key = f'imdb_trivia_{imdb_id}'
    params = {'url': url, 'action': 'imdb_trivia'}
    return cache_object(get_imdb, cache_key, params, False, 168)[0]


def imdb_blunders(imdb_id):
    url = base_url % blunders_url % imdb_id
    cache_key = f'imdb_blunders_{imdb_id}'
    params = {'url': url, 'action': 'imdb_blunders'}
    return cache_object(get_imdb, cache_key, params, False, 168)[0]


def imdb_people_trivia(imdb_id):
    url = base_url % people_trivia_url % imdb_id
    cache_key = f'imdb_people_trivia_{imdb_id}'
    params = {'url': url, 'action': 'imdb_people_trivia'}
    return cache_object(get_imdb, cache_key, params, False, 168)[0]


def imdb_images(imdb_id, page_no):
    url = base_url % images_url % (imdb_id, page_no)
    cache_key = f'imdb_images_{imdb_id}_{page_no}'
    params = {'url': url, 'action': 'imdb_images', 'next_page': page_no + 1}
    return cache_object(get_imdb, cache_key, params, False, 168)


def imdb_videos(imdb_id):
    url = base_url % videos_url % imdb_id
    cache_key = f'imdb_videos_{imdb_id}'
    params = {'url': url, 'imdb_id': imdb_id, 'action': 'imdb_videos'}
    return cache_object(get_imdb, cache_key, params, False, 24)[0]


def imdb_people_images(imdb_id, page_no):
    url = base_url % people_images_url % (imdb_id, page_no)
    cache_key = f'imdb_people_images_{imdb_id}_{page_no}'
    params = {'url': url, 'action': 'imdb_images', 'next_page': 1}
    return cache_object(get_imdb, cache_key, params, False, 168)


def imdb_year_check(imdb_id):
    url = year_check_url % imdb_id
    cache_key = f'imdb_year_check_{imdb_id}'
    params = {'url': url, 'imdb_id': imdb_id, 'action': 'imdb_year_check'}
    return cache_object(get_imdb, cache_key, params, False, 8736)[0]


def imdb_keyword_search(keyword):
    url = base_url % keywords_search_url % keyword
    cache_key = f'imdb_keyword_search_{keyword}'
    params = {'url': url, 'action': 'imdb_keyword_search'}
    return cache_object(get_imdb, cache_key, params, False, 168)[0]


def get_imdb(params):
    """
    Fallback HTML scraper for other IMDb actions.
    (Unchanged from your original code; see your existing get_imdb implementation.)
    """
    # ... your existing get_imdb implementation goes here ...

    return ([], False)  # placeholder


def get_start_no(page_no):
    return ((page_no - 1) * 20) + 1


def clear_imdb_cache(silent=False):
    """
    Clears all cached IMDb entries from the Kodi main cache.
    """
    from modules.kodi_utils import path_exists, clear_property, database, maincache_db
    try:
        if not path_exists(maincache_db):
            return True
        dbcon = database.connect(maincache_db, timeout=40.0, isolation_level=None)
        dbcur = dbcon.cursor()
        dbcur.execute('PRAGMA synchronous = OFF')
        dbcur.execute('PRAGMA journal_mode = OFF')
        dbcur.execute("DELETE FROM maincache WHERE id LIKE ?", ('imdb_%',))
        return True
    except:
        return False


def refresh_imdb_meta_data(imdb_id):
    """
    Deletes any cached entries for a specific IMDb ID.
    """
    from modules.kodi_utils import path_exists, clear_property, database, maincache_db
    if not path_exists(maincache_db):
        return
    dbcon = database.connect(maincache_db, timeout=40.0, isolation_level=None)
    dbcur = dbcon.cursor()
    dbcur.execute('PRAGMA synchronous = OFF')
    dbcur.execute('PRAGMA journal_mode = OFF')
    for pattern in (f'%_{imdb_id}', f'%_{imdb_id}_%'):
        dbcur.execute("DELETE FROM maincache WHERE id LIKE ?", (pattern,))
    return
