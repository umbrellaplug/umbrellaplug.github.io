# -*- coding: utf-8 -*-
# By Umbrella for Umbrella (07/18/22)
"""
	Umbrella Add-on
"""


import requests
import re
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.database import mdbsync
from resources.lib.modules import cleandate

#mdblist use your own key
#trakt limiting users lists now. lets see if we can start using some other list providers.
#yes I know this needs cleanup.
getLS = control.lang
highlightColor = control.setting('highlight.color')

def _mdb_ts(ts_str):
	if not ts_str: return ts_str
	if '.' in ts_str: ts_str = re.sub(r'\.\d+', '', ts_str)  # strip only fractional seconds, preserve Z or tz suffix
	if ts_str.endswith('Z'): ts_str = ts_str[:-1] + '+00:00'
	if len(ts_str) == 7 and ts_str[4] == '-':
		ts_str = ts_str + '-01T00:00:00+00:00'
	elif len(ts_str) == 10 and ts_str[4] == '-' and 'T' not in ts_str:
		ts_str = ts_str + 'T00:00:00+00:00'
	elif 'T' in ts_str and '+' not in ts_str:
		ts_str = ts_str + '+00:00'
	return ts_str

getSetting = control.setting
mdblist_baseurl = 'https://api.mdblist.com'
mdblist_top_list = '/lists/top'
mdblist_user_list = '/lists/user/'
mdblist_liked_list = '/lists/liked'
mdblist_official_list = '/lists/official'
mdblist_page_limit = '?limit=%s' % getSetting('page.item.limit')
_CLIENT_ID = 'YVFS6WW6GT4c2LvaHxHGa8YlB6u9zGgL6KjtDsHg'
session = requests.Session()
retries = Retry(total=4, backoff_factor=0.3, status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 524, 530])
session.mount('https://api.mdblist.com', HTTPAdapter(max_retries=retries, pool_maxsize=100))
_mdblist_token = getSetting('mdblist.token')
if _mdblist_token:
	session.headers.update({'Authorization': 'Bearer %s' % _mdblist_token})
highlight_color = getSetting('highlight.color')
artPath = control.artPath()
iconLogos = getSetting('icon.logos') != 'Traditional'
mdblist_icon = control.joinPath(control.artPath(), 'mdblist.png')
headers = {}
headers['Content-Type'] = 'application/json'

def getMDBTopList(self, listType):
	try:
		response = session.get(mdblist_baseurl + mdblist_top_list, timeout=20)
		if isinstance(response, dict):
			return None
		items = _map_top_list(response, listType)
		return items
	except: log_utils.error('get MDBList Error: ')
	return None

def getMDBOfficialLists(self, listType):
	try:
		response = session.get(mdblist_baseurl + mdblist_official_list, timeout=20)
		if isinstance(response, dict):
			return None
		items = _map_official_list(response, listType)
		return items
	except: log_utils.error('get MDBList Official Lists Error: ')
	return None

def _map_official_list(response, listType):
    items = []
    items_append = items.append
    icon = 'userlists.png' if iconLogos else 'mdblist.png'
    iconPath = control.joinPath(artPath, icon)
    jsonResponse = response.json()
    for i in jsonResponse:
        item = {}
        item['label'] = i.get('name')
        item['art'] = {'icon': f'{iconPath}'}
        item['params'] = {
            'info': 'mdblist_officiallist',
            'list_name': i.get('name'),
            'list_id': i.get('slug'),
            'list_count': i.get('items'),
            'plugin_category': i.get('name')}
        item['unique_ids'] = {
            'slug': i.get('slug'),
            'mdblist': i.get('id')}
        items_append(item)
    return items

def _map_top_list(response, listType):
    items = []
    items_append = items.append
    icon = 'userlists.png' if iconLogos else 'mdblist.png'
    iconPath = control.joinPath(artPath, icon)
    jsonResponse = response.json()
    for i in jsonResponse:
        if i.get('mediatype') == listType:
            item = {}
            item['label'] = i.get('name')
            item['art'] = {'icon': f'{iconPath}'}
            item['params'] = {
                'info': 'mdblist_userlist',
                'list_name': i.get('name'),
                'list_id': i.get('id'),
                'list_count': i.get('items'),
                'plugin_category': i.get('name')}
            item['unique_ids'] = {
                'mdblist': i.get('id'),
                'slug': i.get('slug'),
                'user': i.get('user_id')}
            items_append(item)
    return items
def getMDBItems(url):
	try:
		response = session.get(url, timeout=20)
		if isinstance(response, dict): 
			log_utils.log(response.error, level=log_utils.LOGDEBUG)
			return None
		items = _map_list_items(response)
		return items
	except: log_utils.error('get MDBList Error: ')
	return None
def _map_list_items(response):
    items = []
    items_append = items.append
    icon = 'userlists.png' if iconLogos else 'mdblist.png'
    iconPath = control.joinPath(artPath, icon)

    jsonResponse = response.json()

    # fix to collect all media from shows or movies.
    media_list = jsonResponse.get('movies', []) + jsonResponse.get('shows', [])
    for i in media_list:
        item = {
            'label': i.get('title'),
            'rank': i.get('rank'),
            'adult': i.get('adult'),
            'title': i.get('title'),
            'id': i.get('id'),
            'imdb': i.get('imdb_id'),
            'release_year': i.get('release_year')
        }
        items_append(item)

    return items

def getMDBUserList(self, listType, addremove=False):

    try:
        response = session.get(mdblist_baseurl + mdblist_user_list + mdblist_page_limit, timeout=20)
        if isinstance(response, dict): 
            log_utils.log(response.error, level=log_utils.LOGDEBUG)
            return None
        items = _map_user_list_items(response, listType, addremove=addremove)
        return items
    except: log_utils.error('get MDBList Error: ')
    return None
def _map_user_list_items(response, listType, addremove=False):

    items = []
    items_append = items.append
    icon = 'userlists.png' if iconLogos else 'mdblist.png'
    iconPath = control.joinPath(artPath, icon)
    jsonResponse = response.json()
    for i in jsonResponse:
        if i.get('mediatype') == listType or i.get('mediatype') == None:
            item = {}
            item['label'] = i.get('name')
            item['art'] = {'icon': f'{iconPath}'}
            item['params'] = {
                'info': 'mdblist_userlist',
                'list_name': i.get('name'),
                'list_id': i.get('id'),
                'list_count': i.get('items'),
                'plugin_category': i.get('name')}
            item['unique_ids'] = {
                'mdblist': i.get('id'),
                'slug': i.get('slug')}
            if addremove:
                if i.get('dynamic') == False:
                    items_append(item)
            else:
                items_append(item)
    return items

def getMDBLikedLists(self, listType):
    try:
        data = get_request(mdblist_liked_list)
        if data is None:
            return None
        if isinstance(data, dict):
            for key in ('lists', 'liked', 'data', 'results', 'items'):
                if key in data and isinstance(data[key], list):
                    data = data[key]
                    break
            else:
                log_utils.log('getMDBLikedLists: unexpected dict response keys=%s' % list(data.keys()), level=log_utils.LOGDEBUG)
                return None
        if not isinstance(data, list):
            return None
        icon = 'userlists.png' if iconLogos else 'mdblist.png'
        iconPath = control.joinPath(artPath, icon)
        items = []
        for i in data:
            if i.get('mediatype') == listType or i.get('mediatype') is None:
                owner = i.get('user_name', '') or str(i.get('user_id', ''))
                item = {}
                item['label'] = i.get('name')
                item['art'] = {'icon': f'{iconPath}'}
                item['params'] = {
                    'info': 'mdblist_likedlist',
                    'list_name': i.get('name'),
                    'list_id': i.get('id'),
                    'list_count': i.get('items'),
                    'plugin_category': i.get('name'),
                    'list_owner': owner}
                item['unique_ids'] = {
                    'mdblist': i.get('id'),
                    'slug': i.get('slug'),
                    'user': owner}
                items.append(item)
        return items
    except: log_utils.error('getMDBLikedLists Error: ')
    return None

def get_user_watchlist(listType):
    try:
        
        response = session.get(f"{mdblist_baseurl}/watchlist/items", timeout=20)
        if isinstance(response, dict): 
            log_utils.log(response.error, level=log_utils.LOGDEBUG)
            return None
        items = _map_user_watchlist_items(response, listType)
        return items
    except: log_utils.error('get MDBList Watchlist Error: ')
    return None

def _map_user_watchlist_items(response, listType):
    items = []
    items_append = items.append
    jsonResponse = response.json()
    if listType == 'movie': jsonResponse = jsonResponse.get('movies')
    elif listType == 'tvshow': jsonResponse = jsonResponse.get('shows')
    for i in jsonResponse:
        item = {}
        item['label'] = i.get('title')
        item['rank'] = i.get('rank')
        item['adult'] = i.get('adult')
        item['title'] = i.get('title')
        item['id'] = i.get('id')
        item['imdb'] = i.get('imdb_id')
        item['release_year'] = i.get('release_year')
        watchlist_at = i.get('watchlist_at')
        watchlist_fixed = watchlist_at.replace(" ", "T")[:-3] + "Z"
        item['added'] = watchlist_fixed
        items_append(item)
    return items

def get_user_collection(listType):
    try:
        mediatype = 'movie' if listType == 'movie' else 'episode'
        base_url = f"{mdblist_baseurl}/sync/collection?mediatype={mediatype}&limit=1000"
        all_raw = []
        url = base_url
        while url:
            response = session.get(url, timeout=20)
            if isinstance(response, dict):
                log_utils.log(response.error, level=log_utils.LOGDEBUG)
                return None
            data = response.json()
            key = 'movies' if listType == 'movie' else 'episodes'
            all_raw.extend(data.get(key) or [])
            next_cursor = data.get('pagination', {}).get('next_cursor')
            url = f"{base_url}&cursor={next_cursor}" if next_cursor else None
        return _map_movie_collection_items(all_raw) if listType == 'movie' else _map_show_collection_items(all_raw)
    except: log_utils.error('get MDBList Collection Error: ')
    return None

def _map_movie_collection_items(raw_list):
    items = []
    for i in raw_list:
        try:
            movie = i.get('movie', {})
            ids = movie.get('ids', {})
            collected_at = i.get('collected_at', '')
            try: collected_fixed = collected_at[:-5] + 'Z' if collected_at else ''
            except: collected_fixed = ''
            items.append({
                'label': movie.get('title'),
                'title': movie.get('title'),
                'release_year': movie.get('year'),
                'imdb': ids.get('imdb', ''),
                'tmdb': str(ids.get('tmdb', '') or ''),
                'tvdb': '',
                'id': ids.get('mdblist', ''),
                'added': collected_fixed,
            })
        except: pass
    return items

def _map_show_collection_items(episodes_raw):
    """Deduplicate episodes by show, returning one entry per unique show."""
    seen = {}
    for i in episodes_raw:
        try:
            show = i.get('episode', {}).get('show', {})
            ids = show.get('ids', {})
            imdb = ids.get('imdb', '')
            tmdb = ids.get('tmdb', 0)
            key = imdb or str(tmdb)
            if not key or key in seen: continue
            collected_at = i.get('collected_at', '')
            try: collected_fixed = collected_at[:-5] + 'Z' if collected_at else ''
            except: collected_fixed = ''
            seen[key] = {
                'label': show.get('title'),
                'title': show.get('title'),
                'release_year': show.get('year'),
                'imdb': imdb,
                'tmdb': str(tmdb or ''),
                'tvdb': '',
                'id': ids.get('mdblist', ''),
                'added': collected_fixed,
            }
        except: pass
    return list(seen.values())

def _map_dropped_show_items(raw_list):
    items = []
    for i in raw_list:
        try:
            show = i.get('show') or i
            ids = show.get('ids', {})
            dropped_at = i.get('dropped_at', '')
            try: dropped_fixed = dropped_at[:-5] + 'Z' if dropped_at else ''
            except: dropped_fixed = ''
            items.append({
                'label': show.get('title'), 'title': show.get('title'),
                'release_year': show.get('year'),
                'imdb': ids.get('imdb', ''), 'tmdb': str(ids.get('tmdb', '') or ''),
                'tvdb': str(ids.get('tvdb', '') or ''), 'id': ids.get('mdblist', ''),
                'added': dropped_fixed,
            })
        except: pass
    return items

def get_user_dropped():
    try:
        base_url = f"{mdblist_baseurl}/sync/dropped?limit=1000"
        all_raw = []
        url = base_url
        while url:
            response = session.get(url, timeout=20)
            if isinstance(response, dict):
                log_utils.log(str(response), level=log_utils.LOGDEBUG)
                return None
            data = response.json()
            all_raw.extend(data.get('shows') or [])
            next_cursor = data.get('pagination', {}).get('next_cursor')
            url = f"{base_url}&cursor={next_cursor}" if next_cursor else None
        return _map_dropped_show_items(all_raw)
    except: log_utils.error('get_user_dropped Error: ')
    return None

def getDroppedActivity(activities=None):
    try:
        if activities: i = activities
        else: i = getActivities()
        if not i: return 0
        dropped_at = i.get('dropped_at')
        if not dropped_at: return 0
        return int(cleandate.iso_2_utc(_mdb_ts(dropped_at)) or 0)
    except: log_utils.error()
    return 0

def sync_dropped(activities=None, forced=False):
    try:
        if forced:
            items = get_user_dropped()
            if items is not None: mdbsync.insert_dropped(items, 'shows_dropped')
        else:
            db_last_dropped = mdbsync.last_sync('last_dropped_at')
            droppedActivity = getDroppedActivity(activities)
            if droppedActivity - db_last_dropped >= 60:
                log_utils.log('Mdb Dropped Sync Update...(local db latest "dropped_at" = %s, mdblist api latest "dropped_at" = %s)' % \
                                    (str(db_last_dropped), str(droppedActivity)), __name__, log_utils.LOGINFO)
                items = get_user_dropped()
                if items is not None: mdbsync.insert_dropped(items, 'shows_dropped')
    except: log_utils.error()

def manager(name, imdb=None, tvdb=None, tmdb=None, watched=None, season=None, episode=None):
    lists = []
    try:
        if season: season = int(season)
        if episode: episode = int(episode)
        if episode:
            content_type = 'episode'
        elif season:
            content_type = 'season'
        elif tvdb and tvdb != 'None':
            content_type = 'tvshow'
        else:
            content_type = 'movie'
        items = []
        if watched is not None:
            if watched is True:
                items += [(getLS(33652) % highlight_color, 'unwatch')]
            else:
                items += [(getLS(33651) % highlight_color, 'watch')]
        else:
            items += [(getLS(33651) % highlight_color, 'watch')]
            items += [(getLS(33652) % highlight_color, 'unwatch')]
        if content_type in ('movie', 'episode', 'season'):
            items += [(getLS(40076) % highlight_color, 'scrobbleReset')]
        items += [(getLS(40596) % highlight_color, 'add')]
        items += [(getLS(40597) % highlight_color, 'remove')]
        items += [(getLS(40707) % highlight_color, 'collection_add')]
        items += [(getLS(40708) % highlight_color, 'collection_remove')]
        if content_type == 'tvshow':
            items += [(getLS(40712) % highlight_color, 'dropped_add')]
            items += [(getLS(40713) % highlight_color, 'dropped_remove')]
        if not tvdb or tvdb == 'None':
            from resources.lib.menus import movies
            result = movies.Movies().getMDBUserList(create_directory=False, addremove=True)
        else:
            from resources.lib.menus import tvshows
            result = tvshows.TVshows().getMDBUserList(create_directory=False, addremove=True)
        lists = [(i['name'], i['list_id']) for i in result]
        lists2 = [(i['name'], i['list_id']) for i in result]
        lists = [lists[i//2] for i in range(len(lists)*2)]

        for i in range(0, len(lists), 2):
            lists[i] = ((getLS(33580) % (highlight_color, lists[i][0])), '/lists/%s/items/add' % lists[i][1])
        for i in range(1, len(lists), 2):
            lists[i] = ((getLS(33581) % (highlight_color, lists[i][0])), '/lists/%s/items/remove' % lists[i][1])
        items += lists
        control.hide()
        select = control.selectDialog([i[0] for i in items], heading=control.addonInfo('name') + ' - ' + getLS(40649))
        if select == -1: return
        if select >= 0:
                if items[select][1] == 'watch':
                    watch(content_type, name, imdb=imdb, tvdb=tvdb, tmdb=tmdb, season=season, episode=episode)
                    return
                if items[select][1] == 'unwatch':
                    unwatch(content_type, name, imdb=imdb, tvdb=tvdb, tmdb=tmdb, season=season, episode=episode)
                    return
                if items[select][1] == 'scrobbleReset':
                    scrobbleReset(imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, refresh=True, clear_local=True)
                    return
                if not tvdb or tvdb == 'None': post = {"movies": [{"imdb": imdb}]}
                else:
                    post = {"shows": [{"tmdb": tmdb}]}
                if type(post) == dict or type(post) == list: 
                    import json
                    post = json.dumps(post)
                if items[select][1] == 'add':
                    response = session.post(f"{mdblist_baseurl}/watchlist/items/add", data=post, headers=headers, timeout=20)
                    action = 'add'
                    listid = 'MDBList Watchlist'
                if items[select][1] == 'remove':
                    response = session.post(f"{mdblist_baseurl}/watchlist/items/remove", data=post, headers=headers, timeout=20)
                    action = 'remove'
                    listid = 'MDBList Watchlist'
                if items[select][1] in ('collection_add', 'collection_remove'):
                    import json as _cjson
                    if not tvdb or tvdb == 'None':
                        collection_post = _cjson.dumps({"movies": [{"ids": {"imdb": imdb, "tmdb": int(tmdb) if tmdb else None}}]})
                    else:
                        collection_post = _cjson.dumps({"shows": [{"ids": {"imdb": imdb}}]})
                if items[select][1] == 'collection_add':
                    response = session.post(f"{mdblist_baseurl}/sync/collection", data=collection_post, headers=headers, timeout=20)
                    action = 'add'
                    listid = 'MDBList Collection'
                if items[select][1] == 'collection_remove':
                    response = session.post(f"{mdblist_baseurl}/sync/collection/remove", data=collection_post, headers=headers, timeout=20)
                    action = 'remove'
                    listid = 'MDBList Collection'
                if items[select][1] == 'dropped_add':
                    import json as _djson
                    from datetime import datetime as _dt
                    _dpost = _djson.dumps({'shows': [{'ids': {'imdb': imdb}, 'dropped_at': _dt.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}]})
                    response = session.post(f"{mdblist_baseurl}/sync/dropped", data=_dpost, headers=headers, timeout=20)
                    if response.status_code in (200, 201):
                        mdbsync.insert_dropped([{'imdb': imdb, 'title': name, 'tmdb': str(tmdb or ''), 'tvdb': str(tvdb or '')}], 'shows_dropped', new_sync=False)
                        control.notification(title='MDBList', message='%s added to Dropped' % name, icon=mdblist_icon)
                    else:
                        control.notification(title='MDBList', message='Error: %s' % response.text)
                    control.hide(); return
                if items[select][1] == 'dropped_remove':
                    import json as _djson
                    _dpost = _djson.dumps({'shows': [{'ids': {'imdb': imdb}}]})
                    response = session.post(f"{mdblist_baseurl}/sync/dropped/remove", data=_dpost, headers=headers, timeout=20)
                    if response.status_code in (200, 201):
                        mdbsync.delete_dropped_items([imdb], 'shows_dropped', col_name='imdb')
                        control.notification(title='MDBList', message='%s removed from Dropped' % name, icon=mdblist_icon)
                    else:
                        control.notification(title='MDBList', message='Error: %s' % response.text)
                    control.hide(); return
                for count in range(len(lists)):
                    i = lists[count]
                    if i[1] == '%s' % items[select][1]:
                        response = session.post(mdblist_baseurl + items[select][1], data=post, headers=headers, timeout=20)
                        match = re.search(r'/lists/(\d+)/', i[1])
                        list_id_num = int(match.group(1)) if match else None
                        listid = next((name for name, id in lists2 if id == list_id_num), 'Unknown List')
                        if 'add' in i[1]:
                            action = 'add'
                        if 'remove' in i[1]:    
                            action = 'remove'
                if response.status_code == 200:
                    response = response.json()
                    if action == 'add':
                        if int(response.get('added').get('movies')) > 0:
                            control.notification("Movie Added", "%s added to %s" % (name, listid), icon=mdblist_icon)
                        if int(response.get('added').get('shows')) > 0:
                            control.notification("Show Added", "%s added to %s" % (name, listid), icon=mdblist_icon)
                        if int(response.get('existing').get('movies')) > 0 and int(response.get('added').get('movies')) == 0:
                            control.notification("Error", "%s already on %s" % (name, listid), icon=mdblist_icon)
                        if int(response.get('existing').get('shows')) > 0 and int(response.get('added').get('shows')) == 0:
                            control.notification("Error", "%s already on %s" % (name, listid), icon=mdblist_icon)
                    if action == 'remove':
                        if int(response.get('removed').get('movies')) > 0:
                            control.notification("Movie Removed", "%s removed from %s" % (name, listid), icon=mdblist_icon)
                        if int(response.get('removed').get('shows')) > 0:
                            control.notification("Show Removed", "%s removed from %s" % (name, listid), icon=mdblist_icon)
                elif response.status_code == 403:
                    response = response.json()
                    control.notification("Error", response.get('detail'), icon=mdblist_icon)
                else:
                    control.notification("Error", response.text)

                control.hide()
    except:
        log_utils.error()
        control.hide()
        
def sync_watch_list(activities=None, forced=False):
    try:
        link = f"{mdblist_baseurl}/watchlist/items"
        if forced:
            items = get_mdb_list_as_json(link,'movie')
            mdbsync.insert_watch_list(items, 'movies_watchlist')
            items = get_mdb_list_as_json(link, 'tvshow')
            mdbsync.insert_watch_list(items, 'shows_watchlist')
        else:
            db_last_watchList = mdbsync.last_sync('last_watchlisted_at')
            watchListActivity = getWatchListedActivity(activities)
            if watchListActivity - db_last_watchList >= 60: # do not sync unless 1 min difference or more
                log_utils.log('Mdb Watch List Sync Update...(local db latest "watchlist_at" = %s, mdblist api latest "watchlisted_at" = %s)' % \
                                    (str(db_last_watchList), str(watchListActivity)), __name__, log_utils.LOGINFO)
                items = get_mdb_list_as_json(link,'movie')
                mdbsync.insert_watch_list(items, 'movies_watchlist')
                items = get_mdb_list_as_json(link, 'tvshow')
                mdbsync.insert_watch_list(items, 'shows_watchlist')
    except: log_utils.error()

def get_mdb_collection_as_json(url, listKind):
    try:
        mediatype = 'movie' if listKind == 'movie' else 'episode'
        key = 'movies' if listKind == 'movie' else 'episodes'
        base_url = f"{url}?mediatype={mediatype}&limit=1000"
        all_raw = []
        current_url = base_url
        while current_url:
            response = session.get(current_url, timeout=20)
            if isinstance(response, dict):
                log_utils.log(response.error, level=log_utils.LOGDEBUG)
                return None
            data = response.json()
            all_raw.extend(data.get(key) or [])
            next_cursor = data.get('pagination', {}).get('next_cursor')
            current_url = f"{base_url}&cursor={next_cursor}" if next_cursor else None
        return _map_movie_collection_items(all_raw) if listKind == 'movie' else _map_show_collection_items(all_raw)
    except: log_utils.error()
    return None

def sync_collection(activities=None, forced=False):
    try:
        link = f"{mdblist_baseurl}/sync/collection"
        if forced:
            items = get_mdb_collection_as_json(link, 'movie')
            if items is not None: mdbsync.insert_collection(items, 'movies_collection')
            items = get_mdb_collection_as_json(link, 'tvshow')
            if items is not None: mdbsync.insert_collection(items, 'shows_collection')
        else:
            db_last_collection = mdbsync.last_sync('last_collected_at')
            collectionActivity = getCollectedActivity(activities)
            if collectionActivity - db_last_collection >= 60:
                log_utils.log('Mdb Collection Sync Update...(local db latest "collected_at" = %s, mdblist api latest "collected_at" = %s)' % \
                                    (str(db_last_collection), str(collectionActivity)), __name__, log_utils.LOGINFO)
                items = get_mdb_collection_as_json(link, 'movie')
                if items is not None: mdbsync.insert_collection(items, 'movies_collection')
                items = get_mdb_collection_as_json(link, 'tvshow')
                if items is not None: mdbsync.insert_collection(items, 'shows_collection')
    except: log_utils.error()

def getCollectedActivity(activities=None):
    try:
        if activities: i = activities
        else: i = getActivities()
        if not i: return 0
        activity = []
        collected_at = i.get('collected_at')
        if collected_at: activity.append(collected_at)
        if not activity: return 0
        activity = [int(cleandate.iso_2_utc(_mdb_ts(i)) or 0) for i in activity]
        activity = sorted(activity, key=int)[-1]
        return activity
    except: log_utils.error()
    return 0

def removeCollectionItems(media_type, imdb_list):
    """Remove items from MDBList collection. media_type: 'movies' or 'shows'. imdb_list: list of IMDb IDs."""
    if not imdb_list: return
    try:
        import json as _json
        total_items = len(imdb_list)
        if media_type == 'movies':
            post = _json.dumps({'movies': [{'ids': {'imdb': i}} for i in imdb_list]})
            table = 'movies_collection'
        else:
            post = _json.dumps({'shows': [{'ids': {'imdb': i}} for i in imdb_list]})
            table = 'shows_collection'
        response = session.post('%s/sync/collection/remove' % mdblist_baseurl, data=post, headers=headers, timeout=20)
        if response.status_code == 200:
            mdbsync.delete_collection_items(imdb_list, table, col_name='imdb')
            control.trigger_widget_refresh()
            control.notification(title='MDBList Collection Manager',
                message='Successfully Removed %s Item%s' % (total_items, 's' if total_items > 1 else ''))
        else:
            control.notification(title='MDBList', message='Error: %s' % response.text)
    except: log_utils.error()

def removeDroppedItems(imdb_list):
    """Remove shows from MDBList dropped. imdb_list: list of IMDb IDs."""
    if not imdb_list: return
    try:
        import json as _json
        total_items = len(imdb_list)
        post = _json.dumps({'shows': [{'ids': {'imdb': i}} for i in imdb_list]})
        response = session.post('%s/sync/dropped/remove' % mdblist_baseurl, data=post, headers=headers, timeout=20)
        if response.status_code in (200, 201):
            mdbsync.delete_dropped_items(imdb_list, 'shows_dropped', col_name='imdb')
            control.trigger_widget_refresh()
            control.notification(title='MDBList Dropped Manager',
                message='Successfully Removed %s Item%s' % (total_items, 's' if total_items > 1 else ''))
        else:
            control.notification(title='MDBList', message='Error: %s' % response.text)
    except: log_utils.error()

def get_mdb_list_as_json(url, listKind):
    response = session.get(url, timeout=20)
    if isinstance(response, dict):
        log_utils.log(response.error, level=log_utils.LOGDEBUG)
        return None
    items = []
    items_append = items.append
    jsonResponse = response.json()
    if listKind == 'movie': jsonResponse = jsonResponse.get('movies')
    elif listKind == 'tvshow': jsonResponse = jsonResponse.get('shows')
    for i in jsonResponse:
        item = {}
        item['label'] = i.get('title')
        item['rank'] = i.get('rank')
        item['adult'] = i.get('adult')
        item['title'] = i.get('title')
        item['id'] = i.get('id')
        item['imdb'] = i.get('imdb_id')
        item['release_year'] = i.get('release_year')
        watchlist_at = i.get('watchlist_at')
        watchlist_fixed = watchlist_at.replace(" ", "T")[:-3] + "Z"
        item['added'] = watchlist_fixed
        items_append(item)
    return items

def get_list_items_for_library(url):
    """Fetch all items from an MDBList list URL with mediatype (movie/tvshow) preserved."""
    try:
        response = session.get(url, timeout=20)
        if isinstance(response, dict):
            log_utils.log(str(response), level=log_utils.LOGDEBUG)
            return None
        items = []
        jsonResponse = response.json()
        for i in jsonResponse.get('movies', []):
            items.append({
                'title': i.get('title', ''),
                'year': str(i.get('release_year', '')) if i.get('release_year') else '',
                'imdb': str(i.get('imdb_id', '')) if i.get('imdb_id') else '',
                'mediatype': 'movie',
            })
        for i in jsonResponse.get('shows', []):
            items.append({
                'title': i.get('title', ''),
                'year': str(i.get('release_year', '')) if i.get('release_year') else '',
                'imdb': str(i.get('imdb_id', '')) if i.get('imdb_id') else '',
                'mediatype': 'tvshow',
            })
        return items
    except:
        log_utils.error('get_list_items_for_library Error: ')
    return None

def getWatchListedActivity(activities=None):
    try:
        if activities: i = activities
        else: i = getActivities()
        if not i: return 0
        activity = []
        activity.append(i['watchlisted_at'])
        activity = [int(cleandate.iso_2_utc(_mdb_ts(i)) or 0) for i in activity]
        activity = sorted(activity, key=int)[-1]
        return activity
    except: log_utils.error()
    return 0

def getMDBListCredentialsInfo():
	return bool(getSetting('mdblist.token'))

def getMDBListIndicatorsInfo():
	return getSetting('indicators.alt') == '3'

def mdblistAuth(fromSettings=0):
	try:
		response = session.post(
			'https://api.mdblist.com/oauth/device-authorization/',
			data={'client_id': _CLIENT_ID, 'scope': 'write'},
			timeout=20)
		if response.status_code != 200:
			control.notification(title='MDBList', message='Authorization request failed')
			if fromSettings: control.openSettings('5.4', 'plugin.video.umbrella')
			return False
		device_data = response.json()
		device_code = device_data['device_code']
		user_code = device_data['user_code']
		verification_url = device_data.get('verification_url', 'https://mdblist.com/oauth/device/')
		expires_in = int(device_data.get('expires_in', 300))
		interval = int(device_data.get('interval', 5))
		verification_url_display = control.lang(32513) % (highlightColor, verification_url)
		user_code_display = control.lang(32514) % (highlightColor, user_code)
		if control.setting('dialogs.useumbrelladialog') == 'true':
			from resources.lib.modules import tools
			mdb_qr = tools.make_qr(verification_url, 'mdblist_qr.png')
			progressDialog = control.getProgressWindow('MDBList Authorization', mdb_qr, 1)
			progressDialog.set_controls()
			progressDialog.update(0, control.progress_line % (verification_url_display, user_code_display))
		else:
			progressDialog = control.progressDialog
			progressDialog.create('MDBList Authorization',
				control.progress_line % (verification_url_display, user_code_display))
		access_token = None
		refresh_token = ''
		start = time.time()
		try:
			while not progressDialog.iscanceled():
				time_passed = time.time() - start
				if time_passed >= expires_in:
					break
				control.sleep(interval * 1000)
				poll = session.post(
					'https://api.mdblist.com/oauth/token/',
					data={
						'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
						'device_code': device_code,
						'client_id': _CLIENT_ID},
					timeout=20)
				if poll.status_code == 200:
					access_token = poll.json().get('access_token', '')
					refresh_token = poll.json().get('refresh_token', '')
					break
				progress = int(100 - 100 * time_passed / expires_in)
				progressDialog.update(progress, control.progress_line % (verification_url_display, user_code_display))
		finally:
			progressDialog.close()
		if not access_token:
			control.notification(title='MDBList', message='Authorization failed or timed out')
			if fromSettings: control.openSettings('5.4', 'plugin.video.umbrella')
			return False
		control.setSetting('mdblist.token', access_token)
		if refresh_token:
			control.setSetting('mdblist.refresh.token', refresh_token)
		session.headers.update({'Authorization': 'Bearer %s' % access_token})
		control.notification(title='MDBList', message='MDBList Authorized Successfully')
		if fromSettings: control.openSettings('5.4', 'plugin.video.umbrella')
		return True
	except:
		log_utils.error()
		if fromSettings: control.openSettings('5.4', 'plugin.video.umbrella')
		return False

def mdblistRevoke(fromSettings=0):
	try:
		control.homeWindow.setProperty('umbrella.updateSettings', 'false')
		control.setSetting('mdblist.token', '')
		control.setSetting('mdblist.refresh.token', '')
		control.homeWindow.setProperty('umbrella.updateSettings', 'true')
		session.headers.pop('Authorization', None)
		clr_mdb = {'mdb_watched_movies': True, 'mdb_watched_episodes': True, 'watched': True, 'bookmarks': True,
			'movies_watchlist': True, 'shows_watchlist': True, 'movies_collection': True, 'shows_collection': True, 'shows_dropped': True}
		mdbsync.delete_mdb_tables(clr_mdb)
		if getSetting('indicators.alt') == '3':
			control.setSetting('indicators.alt', '0')
			control.setSetting('indicators', 'Local')
		if getSetting('scrobble.source') == '3':
			control.setSetting('scrobble.source', '0')
			control.setSetting('scrobble', 'Local')
		control.setSetting('mdblist.markwatched', 'false')
		control.notification(title='MDBList', message='MDBList Authorization Revoked')
	except: log_utils.error()
	finally:
		if fromSettings: control.openSettings('5.4', 'plugin.video.umbrella')

def _refresh_token():
	try:
		refresh_token = getSetting('mdblist.refresh.token')
		if not refresh_token:
			return False
		resp = session.post(
			'https://api.mdblist.com/oauth/token/',
			data={'grant_type': 'refresh_token', 'refresh_token': refresh_token, 'client_id': _CLIENT_ID},
			timeout=20
		)
		if resp.status_code == 200:
			data = resp.json()
			access_token = data.get('access_token', '')
			new_refresh = data.get('refresh_token', '')
			if access_token:
				control.setSetting('mdblist.token', access_token)
				if new_refresh:
					control.setSetting('mdblist.refresh.token', new_refresh)
				session.headers.update({'Authorization': 'Bearer %s' % access_token})
				log_utils.log('MDBList token refreshed successfully', level=log_utils.LOGDEBUG)
				return True
		log_utils.log('MDBList token refresh failed: status=%s body=%r' % (resp.status_code, resp.text[:200]), level=log_utils.LOGDEBUG)
		return False
	except:
		log_utils.error()
		return False

def get_request(url, post=None, method='GET', _retried=False):
	try:
		full_url = f"{mdblist_baseurl}{url}"
		import json as _json
		for _attempt in range(2):
			try:
				if method == 'DELETE':
					response = session.delete(full_url, headers=headers, timeout=20)
				elif post is not None:
					response = session.post(full_url, data=_json.dumps(post), headers=headers, timeout=20)
				else:
					response = session.get(full_url, timeout=20)
				break
			except requests.exceptions.ConnectionError:
				if _attempt == 0:
					log_utils.log('MDBList get_request: connection reset, retrying with fresh connection...', level=log_utils.LOGDEBUG)
					session.close()
				else:
					raise
		if response.status_code in (200, 201, 204):
			try: return response.json()
			except: return {}
		if response.status_code == 401 and not _retried:
			if _refresh_token():
				return get_request(url, post=post, method=method, _retried=True)
			control.notification(title='MDBList', message='MDBList session expired — please re-authenticate in settings')
		log_utils.log('MDBList get_request non-2xx: url=%s status=%s body=%r' % (url, response.status_code, response.text[:200]), level=log_utils.LOGDEBUG)
		return None
	except: log_utils.error()
	return None

def getActivities():
	try:
		return get_request('/sync/last_activities')
	except: log_utils.error()
	return None

def get_up_next():
	try:
		result = get_request('/upnext?limit=100&hide_unreleased=true')
		if result is None:
			return []
		items = result if isinstance(result, list) else result.get('items', result.get('shows', []))
		return items
	except: log_utils.error()
	return []

def get_calendar(start, end):
	# MDBList's own /calendar/events — personalized to the user's watchlist/tracked
	# shows, confirmed live (real response shape: {'events': [{'type': 'episode'|'movie',
	# 'title': <show title>, 'episode_title':, 'show_tmdb':, 'season_number':,
	# 'episode_number':, 'start': 'YYYY-MM-DD', ...}]}). Distinct from get_up_next()'s
	# /upnext endpoint (per-show "next episode" only, unreliable for out-of-order
	# watching — see mdblist_progress_list()'s local reconstruction for that case).
	try:
		result = get_request('/calendar/events?limit=1000&start=%s&end=%s' % (start, end))
		if not result: return []
		return result.get('events') or []
	except: log_utils.error()
	return []

def getWatchedActivity(activities=None):
	try:
		i = activities if activities else getActivities()
		if not i: return 0
		if isinstance(i, str):
			import json as _json
			i = _json.loads(i)
		val = i.get('watched_at') or i.get('history_at') or None
		if not val: return 0
		return int(cleandate.iso_2_utc(_mdb_ts(val)) or 0)
	except: log_utils.error()
	return 0

def getMoviesWatchedActivity():
	try: return mdbsync.last_sync('last_watched_movies_at')
	except: log_utils.error()
	return 0

def getEpisodesWatchedActivity():
	try: return mdbsync.last_sync('last_watched_episodes_at')
	except: log_utils.error()
	return 0

def timeoutsyncMovies():
	return mdbsync.timeout(syncMovies)

def timeoutsyncTVShows():
	return mdbsync.timeout(syncTVShows)

def timeoutsyncSeasons(imdb, tvdb):
	try: return mdbsync.timeout(syncSeasons, imdb, tvdb, returnNone=True)
	except: log_utils.error()

def sync_watchedProgress(activities=None, forced=False):
	try:
		db_last = mdbsync.last_sync('last_watched_at')
		api_last = getWatchedActivity(activities)
		if not forced and db_last and (api_last - db_last) < 60: return
		from datetime import datetime as _dt
		since = _dt.utcfromtimestamp(db_last).strftime('%Y-%m-%dT%H:%M:%SZ') if db_last else '1970-01-01T00:00:00Z'
		offset = 0
		limit = 1000
		while True:
			url = f"/sync/watched?since={since}&limit={limit}&offset={offset}"
			data = get_request(url)
			if not data: break
			for item in data.get('movies', []):
				ids = item.get('movie', {}).get('ids', {})
				imdb = str(ids.get('imdb', ''))
				if not imdb: continue
				mdbsync.upsert_watched_movie(
					imdb=imdb,
					tmdb=str(ids.get('tmdb', '')),
					title=item.get('movie', {}).get('title', ''),
					year=str(item.get('movie', {}).get('year', '')),
					last_watched_at=item.get('last_watched_at', '')
				)
			for item in data.get('episodes', []):
				ep = item.get('episode', {})
				show_ids = ep.get('show', {}).get('ids', {})
				show_imdb = str(show_ids.get('imdb', ''))
				if not show_imdb: continue
				mdbsync.upsert_watched_episode(
					show_imdb=show_imdb,
					show_tmdb=str(show_ids.get('tmdb', '')),
					show_tvdb=str(show_ids.get('tvdb', '')),
					season=ep.get('season', 0),
					episode=ep.get('number', 0),
					last_watched_at=item.get('last_watched_at', '')
				)
			pagination = data.get('pagination', {})
			if not pagination.get('has_more', False): break
			offset += limit
		mdbsync.update_last_watched_at('last_watched_at')
		mdbsync.update_last_watched_at('last_watched_movies_at')
		mdbsync.update_last_watched_at('last_watched_episodes_at')
		# invalidate indicator caches so next access fetches fresh data
		mdbsync.cache_delete(mdbsync._hash_function(syncMovies, ()))
		mdbsync.cache_delete(mdbsync._hash_function(syncTVShows, ()))
		control.trigger_widget_refresh()
	except: log_utils.error()


def syncMovies():
	try:
		if not getMDBListCredentialsInfo(): return None
		return mdbsync.get_watched_movies() or []
	except: log_utils.error()

def watchedMovies():
	try:
		if not getMDBListCredentialsInfo(): return None
		return mdbsync.get_watched_movies_full() or []
	except: log_utils.error()

def _make_episode_ranges(ep_nums_sorted):
	if not ep_nums_sorted: return []
	ranges = []
	start = end = ep_nums_sorted[0]
	for ep in ep_nums_sorted[1:]:
		if ep == end + 1:
			end = ep
		else:
			ranges.append((start, end))
			start = end = ep
	ranges.append((start, end))
	return ranges

def syncTVShows():
	try:
		if not getMDBListCredentialsInfo(): return None
		episodes = mdbsync.get_watched_episodes()
		if not episodes: return []
		shows = {}
		for (show_imdb, show_tmdb, show_tvdb, season, episode) in episodes:
			if show_imdb not in shows:
				shows[show_imdb] = {'ids': {'imdb': show_imdb, 'tmdb': show_tmdb, 'tvdb': show_tvdb}, 'by_season': {}}
			s = int(season)
			shows[show_imdb]['by_season'].setdefault(s, []).append(int(episode))
		indicators = []
		for v in shows.values():
			ep_ranges = {s: _make_episode_ranges(sorted(eps)) for s, eps in v['by_season'].items()}
			total = sum(e - s + 1 for ranges in ep_ranges.values() for s, e in ranges)
			indicators.append((v['ids'], total, ep_ranges))
		return indicators
	except: log_utils.error()

def watchedShows():
	try:
		if not getMDBListCredentialsInfo(): return None
		rows = mdbsync.get_watched_shows()
		if not rows: return []
		return [{'ids': {'imdb': r[0], 'tmdb': r[1], 'tvdb': r[2]}, 'last_watched_at': r[3]} for r in rows]
	except: log_utils.error()

def syncSeasons(imdb, tvdb):
	try:
		if not getMDBListCredentialsInfo(): return None
		if not imdb and not tvdb: return None
		episodes = mdbsync.get_watched_episodes()
		# MDBList's local watched-episode rows never populate show_tvdb (always ''), so
		# comparing "sv == tvdb" against an empty tvdb matched every other show's rows too
		# (both sides ''), silently merging hundreds of unrelated shows' episodes into one
		# season/episode count — only match on a given id when it's actually non-empty.
		show_eps = [(s, e) for (si, st, sv, s, e) in (episodes or []) if (imdb and si == imdb) or (tvdb and sv == tvdb)]
		from collections import defaultdict
		by_season = defaultdict(list)
		for (s, e) in show_eps:
			by_season[int(s)].append(int(e))
		# Get total episode counts per season from TMDb
		from resources.lib.database import cache as _cache
		from resources.lib.indexers import tmdb as _tmdb
		tmdb_id = ''
		try:
			result = _cache.get(_tmdb.TVshows().IdLookup, 96, imdb, tvdb)
			if result: tmdb_id = str(result.get('id', ''))
		except: pass
		season_totals = {}
		if tmdb_id:
			try:
				meta = _cache.get(_tmdb.TVshows().get_showSeasons_meta, 96, tmdb_id)
				if meta:
					status = (meta.get('status') or '').lower()
					ended = status in ('ended', 'canceled', 'cancelled')
					last_ep = meta.get('last_episode_to_air') or {}
					last_aired_sn = int(last_ep.get('season_number', 0)) if last_ep else 0
					last_aired_ep = int(last_ep.get('episode_number', 0)) if last_ep else 0
					for s_item in meta.get('seasons', []):
						sn = int(s_item.get('season_number', 0))
						if sn <= 0: continue
						ep_count = int(s_item.get('episode_count', 0))
						if ended or sn < last_aired_sn:
							season_totals[sn] = ep_count
						elif sn == last_aired_sn:
							season_totals[sn] = last_aired_ep if last_aired_ep > 0 else ep_count
						# sn > last_aired_sn: future/unaired season — omit so fallback uses watched count only
			except: pass
		counts = {}
		completed_seasons = []
		for sn, watched_eps in by_season.items():
			total = season_totals.get(sn, len(watched_eps))
			watched = len(set(watched_eps))
			unwatched = max(0, total - watched)
			counts[sn] = {'total': total, 'watched': watched, 'unwatched': unwatched}
			if total > 0 and watched >= total:
				completed_seasons.append('%01d' % sn)
		# Include aired seasons with no watched episodes so getShowCount totals all seasons, not just watched ones
		for sn, ep_count in season_totals.items():
			if sn not in counts:
				counts[sn] = {'total': ep_count, 'watched': 0, 'unwatched': ep_count}
		return [completed_seasons, counts]
	except: log_utils.error()
	return [[], {}]

def seasonCount(imdb, tvdb):
	try:
		result = syncSeasons(imdb, tvdb)
		if result and len(result) > 1: return result[1]
		return {}
	except: log_utils.error()


def cachesyncMovies(timeout=720):
	try:
		return mdbsync.get(syncMovies, timeout)
	except: log_utils.error()

def cachesyncTVShows(timeout=720):
	try:
		return mdbsync.get(syncTVShows, timeout)
	except: log_utils.error()

def cachesyncSeasons(imdb, tvdb='', timeout=720):
	try:
		imdb = imdb or ''
		tvdb = tvdb or ''
		return mdbsync.get(syncSeasons, timeout, imdb, tvdb)
	except: log_utils.error()

def cachesyncTV(imdb, tvdb):
	try:
		from concurrent.futures import ThreadPoolExecutor
		with ThreadPoolExecutor() as executor:
			executor.submit(cachesyncTVShows, 0)
			executor.submit(cachesyncSeasons, imdb, tvdb, 0)
	except: log_utils.error()

def _clr_episode_progress_cache():
	try:
		from resources.lib.menus.episodes import Episodes
		from resources.lib.database import cache
		ep = Episodes()
		cache.remove(ep.mdblist_progress_list, '/upnext', ep.mdblist_directProgressScrape)
		cache.remove(ep.mdblist_progress_list, 'mdbprogress', ep.mdblist_directProgressScrape)
	except: log_utils.error()


def _scrobble(endpoint, media_type, imdb, tmdb, tvdb, season, episode, percent):
	try:
		percent = round(float(percent), 2)
		if media_type == 'movie':
			post = {'movie': {'ids': {'imdb': imdb, 'tmdb': int(tmdb) if tmdb else None}}, 'progress': percent}
		else:
			post = {
				'show': {
					'ids': {'imdb': imdb, 'tmdb': int(tmdb) if tmdb else None, 'tvdb': int(tvdb) if tvdb else None},
					'season': int('%01d' % int(season)) if season else 1,
					'episode': int('%01d' % int(episode)) if episode else 1
				},
				'progress': percent
			}
		return get_request(endpoint, post=post)
	except: log_utils.error()
	return None

def scrobbleStart(media_type, title='', tvshowtitle='', year='0', imdb='', tmdb='', tvdb='', season='', episode='', watched_percent=0):
	try:
		_scrobble('/scrobble/start', media_type, imdb, tmdb, tvdb, season, episode, watched_percent)
	except: log_utils.error()

def scrobbleMovie(title, year, imdb, tmdb, watched_percent):
	try:
		result = _scrobble('/scrobble/pause', 'movie', imdb, tmdb, '', '', '', watched_percent)
		if result is not None and getSetting('scrobble.notify') == 'true':
			control.notification(message=40657)
		from datetime import datetime as _dt
		paused_at = _dt.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')
		mdbsync.upsert_bookmark(title=title or '', imdb=str(imdb) if imdb else '', tmdb=str(tmdb) if tmdb else '', percent_played=str(watched_percent), paused_at=paused_at)
		control.trigger_widget_refresh()
		log_utils.log('MDBList Scrobble Movie. imdb: %s percent: %s' % (imdb, watched_percent), level=log_utils.LOGDEBUG)
	except: log_utils.error()

def scrobbleEpisode(tvshowtitle, year, imdb, tmdb, tvdb, season, episode, watched_percent):
	try:
		result = _scrobble('/scrobble/pause', 'episode', imdb, tmdb, tvdb, season, episode, watched_percent)
		if result is not None and getSetting('scrobble.notify') == 'true':
			control.notification(message=40657)
		from datetime import datetime as _dt
		paused_at = _dt.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')
		mdbsync.upsert_bookmark(tvshowtitle=tvshowtitle or '', imdb=str(imdb) if imdb else '', tmdb=str(tmdb) if tmdb else '', tvdb=str(tvdb) if tvdb else '', season=str(season) if season else '', episode=str(episode) if episode else '', percent_played=str(watched_percent), paused_at=paused_at)
		control.trigger_widget_refresh()
		log_utils.log('MDBList Scrobble Episode. imdb: %s S%sE%s percent: %s' % (imdb, season, episode, watched_percent), level=log_utils.LOGDEBUG)
	except: log_utils.error()

def scrobbleReset(imdb, tmdb='', tvdb='', season=None, episode=None, refresh=False, clear_local=True, already_watched=False):
	if not getMDBListCredentialsInfo(): return
	try:
		if episode:
			ids = {}
			if imdb: ids['imdb'] = imdb
			if tmdb: ids['tmdb'] = int(tmdb)
			if tvdb: ids['tvdb'] = int(tvdb)
			post = {'show': {'ids': ids, 'season': int(season) if season else 1, 'episode': int(episode)}, 'progress': 0}
		else:
			ids = {}
			if imdb: ids['imdb'] = imdb
			if tmdb: ids['tmdb'] = int(tmdb)
			post = {'movie': {'ids': ids}, 'progress': 0}
		get_request('/scrobble/clear', post=post)
		if not already_watched:
			if episode:
				_post_sync_watched(show_ids={'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb},
					seasons_dict={int(season) if season else 1: [int(episode)]})
				_clr_episode_progress_cache()
			elif season:
				pass  # season-level reset clears local resume points only, no re-mark-watched
			else:
				_post_sync_watched(movies=[{'imdb': imdb, 'tmdb': tmdb}])
		if episode:
			mdbsync.delete_bookmark(imdb, tvdb or '', season or '', episode)
		elif season:
			mdbsync.delete_bookmarks_for_season(imdb, tvdb or '', season)
		else:
			mdbsync.delete_bookmark(imdb, tvdb or '', '', '')
		sync_watchedProgress(forced=True)
		control.trigger_widget_refresh()
		if refresh: control.refresh()
		if getSetting('scrobble.notify') == 'true':
			control.notification(title='MDBList', message='Successfully Removed MDBList playback progress')
		log_utils.log('MDBList scrobble reset. imdb: %s' % imdb, level=log_utils.LOGDEBUG)
	except: log_utils.error()

def sync_playbackProgress(forced=False):
	try:
		items = get_request('/sync/playback')
		if items is None: return
		server_ids = set()
		for i in items:
			resume_id = str(i.get('id', ''))
			server_ids.add(resume_id)
			percent_played = str(i.get('progress', '0'))
			paused_at = i.get('paused_at', '')
			if i.get('type') == 'episode':
				show_ids = (i.get('show') or {}).get('ids', {})
				ep = i.get('episode') or {}
				tvshowtitle = (i.get('show') or {}).get('title', '')
				title = ep.get('title', '')
				imdb = str(show_ids.get('imdb', '') or '')
				tmdb = str(show_ids.get('tmdb', '') or '')
				tvdb = str(show_ids.get('tvdb', '') or '')
				season = str(ep.get('season', ''))
				episode = str(ep.get('number', ''))
				mdbsync.upsert_bookmark(tvshowtitle=tvshowtitle, title=title, resume_id=resume_id, imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, percent_played=percent_played, paused_at=paused_at)
			else:
				movie_ids = (i.get('movie') or {}).get('ids', {})
				title = (i.get('movie') or {}).get('title', '')
				imdb = str(movie_ids.get('imdb', '') or '')
				tmdb = str(movie_ids.get('tmdb', '') or '')
				mdbsync.upsert_bookmark(title=title, resume_id=resume_id, imdb=imdb, tmdb=tmdb, percent_played=percent_played, paused_at=paused_at)
		mdbsync.delete_synced_bookmarks_not_in(server_ids)
	except: log_utils.error()

def removeWatchlistItems(media_type, imdb_list):
	"""Remove items from MDBList watchlist. media_type: 'movies' or 'shows'. imdb_list: list of IMDb IDs."""
	if not imdb_list: return
	try:
		import json as _json
		total_items = len(imdb_list)
		if media_type == 'movies':
			post = _json.dumps({'movies': [{'imdb': i} for i in imdb_list]})
			table = 'movies_watchlist'
		else:
			post = _json.dumps({'shows': [{'imdb': i} for i in imdb_list]})
			table = 'shows_watchlist'
		response = session.post('%s/watchlist/items/remove' % mdblist_baseurl, data=post, headers=headers, timeout=20)
		if response.status_code == 200:
			mdbsync.delete_watchList_items(imdb_list, table, col_name='imdb')
			control.trigger_widget_refresh()
			control.notification(title='MDBList Watchlist Manager',
				message='Successfully Removed %s Item%s' % (total_items, 's' if total_items > 1 else ''))
		else:
			control.notification(title='MDBList', message='Error: %s' % response.text)
	except: log_utils.error()

def force_mdblistSync():
	if not control.yesnoDialog(control.lang(32056), '', ''): return
	dialog = control.progressDialog
	dialog.create(control.addonName(), 'Preparing MDBList sync...')
	try:
		clr_mdb = {'mdb_watched_movies': True, 'mdb_watched_episodes': True, 'movies_watchlist': True, 'shows_watchlist': True, 'watched': True}
		mdbsync.delete_mdb_tables(clr_mdb)
		dialog.update(0, 'Syncing watchlist...')
		sync_watch_list(forced=True)
		dialog.update(50, 'Syncing watched history...')
		sync_watchedProgress(forced=True)
	finally:
		dialog.close()
	control.notification(message='Forced MDBList Sync Complete')


def _post_sync_watched(movies=None, show_ids=None, seasons_dict=None):
	try:
		now = __import__('datetime').datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')
		post = {}
		if movies:
			post['movies'] = [
				{'ids': {'imdb': m.get('imdb'), 'tmdb': int(m['tmdb']) if m.get('tmdb') else None},
				 'watched_at': now}
				for m in movies
			]
		if show_ids:
			show_entry = {
				'ids': {
					'imdb': show_ids.get('imdb'),
					'tmdb': int(show_ids['tmdb']) if show_ids.get('tmdb') else None,
					'tvdb': int(show_ids['tvdb']) if show_ids.get('tvdb') else None
				},
				'watched_at': now
			}
			if seasons_dict is not None:
				seasons = []
				for sn, eps in seasons_dict.items():
					if eps is None:
						seasons.append({'number': sn, 'watched_at': now})
					elif eps:
						seasons.append({'number': sn, 'episodes': [{'number': en, 'watched_at': now} for en in eps]})
				if seasons:
					show_entry['seasons'] = seasons
					del show_entry['watched_at']
			post['shows'] = [show_entry]
		if not post: return None
		return get_request('/sync/watched', post=post)
	except: log_utils.error()
	return None


def markMovieAsWatched(imdb, tmdb=''):
	try:
		_post_sync_watched(movies=[{'imdb': imdb, 'tmdb': tmdb}])
		mdbsync.upsert_watched_movie(imdb=imdb, tmdb=str(tmdb),
			last_watched_at=__import__('datetime').datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"))
		mdbsync.cache_delete(mdbsync._hash_function(syncMovies, ()))
		log_utils.log('MDBList markMovieAsWatched imdb: %s' % imdb, level=log_utils.LOGDEBUG)
		return True
	except: log_utils.error()

def markMovieAsNotWatched(imdb):
	try:
		mdbsync.delete_watched_movie(imdb)
		mdbsync.cache_delete(mdbsync._hash_function(syncMovies, ()))
		return True
	except: log_utils.error()

def markEpisodeAsWatched(imdb, tvdb, season, episode, tmdb=''):
	try:
		_post_sync_watched(show_ids={'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb},
			seasons_dict={int(season) if season else 1: [int(episode) if episode else 1]})
		mdbsync.upsert_watched_episode(show_imdb=imdb, show_tvdb=str(tvdb), season=season, episode=episode,
			last_watched_at=__import__('datetime').datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"))
		mdbsync.cache_delete(mdbsync._hash_function(syncTVShows, ()))
		_clr_episode_progress_cache()
		return True
	except: log_utils.error()

def markEpisodeAsNotWatched(imdb, tvdb, season, episode):
	try:
		mdbsync.delete_watched_episode(imdb, season, episode)
		mdbsync.cache_delete(mdbsync._hash_function(syncTVShows, ()))
		return True
	except: log_utils.error()

def markTVShowAsWatched(imdb, tvdb, tmdb=''):
	try:
		now = __import__('datetime').datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')
		from resources.lib.database import cache as _cache
		from resources.lib.indexers import tmdb as _tmdb
		tmdb_id = ''
		try:
			res = _cache.get(_tmdb.TVshows().IdLookup, 96, imdb, tvdb)
			if res: tmdb_id = str(res.get('id', ''))
		except: pass
		if tmdb_id:
			try:
				meta = _cache.get(_tmdb.TVshows().get_showSeasons_meta, 96, tmdb_id)
				for s_item in (meta or {}).get('seasons', []):
					sn = int(s_item.get('season_number', 0))
					ec = int(s_item.get('episode_count', 0))
					if sn > 0 and ec > 0:
						for en in range(1, ec + 1):
							mdbsync.upsert_watched_episode(show_imdb=imdb, show_tvdb=str(tvdb),
								show_tmdb=str(tmdb), season=sn, episode=en, last_watched_at=now)
			except: pass
		_post_sync_watched(show_ids={'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb})
		mdbsync.cache_delete(mdbsync._hash_function(syncTVShows, ()))
		return True
	except: log_utils.error()

def markTVShowAsNotWatched(imdb, tvdb):
	try:
		episodes = mdbsync.get_watched_episodes()
		# See syncSeasons() above: MDBList's local rows never populate show_tvdb (always
		# ''), so matching on an empty tvdb matched every other show's rows too and wiped
		# the entire local watched-episode table on a single unwatch — only match a given
		# id when it's actually non-empty.
		for (si, st, sv, s, e) in episodes:
			if (imdb and si == imdb) or (tvdb and sv == tvdb):
				mdbsync.delete_watched_episode(si, s, e)
		mdbsync.cache_delete(mdbsync._hash_function(syncTVShows, ()))
		return True
	except: log_utils.error()

def markSeasonAsWatched(imdb, tvdb, season, tmdb=''):
	try:
		now = __import__('datetime').datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')
		season = int(season)
		from resources.lib.database import cache as _cache
		from resources.lib.indexers import tmdb as _tmdb
		tmdb_id = ''
		try:
			res = _cache.get(_tmdb.TVshows().IdLookup, 96, imdb, tvdb)
			if res: tmdb_id = str(res.get('id', ''))
		except: pass
		if tmdb_id:
			try:
				raw = _cache.get(_tmdb.TVshows().get_season_request, 96, tmdb_id, season)
				for ep in (raw or {}).get('episodes', []):
					en = int(ep.get('episode_number', 0))
					if en > 0:
						mdbsync.upsert_watched_episode(show_imdb=imdb, show_tvdb=str(tvdb),
							show_tmdb=str(tmdb), season=season, episode=en, last_watched_at=now)
			except: pass
		_post_sync_watched(show_ids={'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb},
			seasons_dict={season: None})
		mdbsync.cache_delete(mdbsync._hash_function(syncTVShows, ()))
		return True
	except: log_utils.error()

def markSeasonAsNotWatched(imdb, tvdb, season):
	try:
		episodes = mdbsync.get_watched_episodes()
		for (si, st, sv, s, e) in episodes:
			if ((imdb and si == imdb) or (tvdb and sv == tvdb)) and int(s) == int(season):
				mdbsync.delete_watched_episode(si, s, e)
		mdbsync.cache_delete(mdbsync._hash_function(syncTVShows, ()))
		return True
	except: log_utils.error()

def update_syncMovies(imdb, remove_id=False):
	try:
		if remove_id: markMovieAsNotWatched(imdb)
		else: markMovieAsWatched(imdb)
		cachesyncMovies(timeout=0)
	except: log_utils.error()

def watch(content_type, name, imdb=None, tvdb=None, tmdb=None, season=None, episode=None, refresh=True):
	control.busy()
	success = False
	if content_type == 'movie':
		success = markMovieAsWatched(imdb, tmdb or '')
		if success: cachesyncMovies(timeout=0)
	elif content_type == 'tvshow':
		success = markTVShowAsWatched(imdb, tvdb, tmdb or '')
		if success: cachesyncTV(imdb, tvdb)
	elif content_type == 'season':
		success = markSeasonAsWatched(imdb, tvdb, season, tmdb or '')
		if success: cachesyncTV(imdb, tvdb)
	elif content_type == 'episode':
		success = markEpisodeAsWatched(imdb, tvdb, season, episode, tmdb or '')
		if success:
			cachesyncTV(imdb, tvdb)
			_clr_episode_progress_cache()
	control.hide()
	if refresh: control.refresh()
	control.trigger_widget_refresh()
	if season and not episode: name = '%s-Season%s...' % (name, season)
	if season and episode: name = '%s-S%sxE%02d...' % (name, season, int(episode))
	if getSetting('mdblist.general.notifications') == 'true':
		if success is True: control.notification(title='MDBList', message=getLS(40641) % ('[COLOR %s]%s[/COLOR]' % (highlightColor, name)))
		else: control.notification(title='MDBList', message=getLS(40640) % ('[COLOR %s]%s[/COLOR]' % (highlightColor, name)))
	if not success: log_utils.log(getLS(40640) % name + ' : ids={imdb: %s, tvdb: %s}' % (imdb, tvdb), __name__, level=log_utils.LOGDEBUG)

def unwatch(content_type, name, imdb=None, tvdb=None, tmdb=None, season=None, episode=None, refresh=True):
	control.busy()
	success = False
	if content_type == 'movie':
		success = markMovieAsNotWatched(imdb)
		if success: cachesyncMovies(timeout=0)
	elif content_type == 'tvshow':
		success = markTVShowAsNotWatched(imdb, tvdb)
		if success: cachesyncTV(imdb, tvdb)
	elif content_type == 'season':
		success = markSeasonAsNotWatched(imdb, tvdb, season)
		if success: cachesyncTV(imdb, tvdb)
	elif content_type == 'episode':
		success = markEpisodeAsNotWatched(imdb, tvdb, season, episode)
		if success: cachesyncTV(imdb, tvdb)
	control.hide()
	if refresh: control.refresh()
	control.trigger_widget_refresh()
	if season and not episode: name = '%s-Season%s...' % (name, season)
	if season and episode: name = '%s-S%sxE%02d...' % (name, season, int(episode))
	if getSetting('mdblist.general.notifications') == 'true':
		if success is True: control.notification(title='MDBList', message=getLS(40643) % ('[COLOR %s]%s[/COLOR]' % (highlightColor, name)))
		else: control.notification(title='MDBList', message=getLS(40642) % ('[COLOR %s]%s[/COLOR]' % (highlightColor, name)))