# -*- coding: utf-8 -*-
# By Umbrella for Umbrella (07/18/22)
"""
	Umbrella Add-on
"""


import requests
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from resources.lib.modules import control
from resources.lib.modules import log_utils


#mdblist use your own key
#trakt limiting users lists now. lets see if we can start using some other list providers.
#yes I know this needs cleanup.
getLS = control.lang
getSetting = control.setting
mdblist_api = getSetting('mdblist.api')
mdblist_baseurl = 'https://api.mdblist.com'
mdblist_top_list ='/lists/top?apikey='
mdblist_user_list ='/lists/user/?apikey='
mdblist_page_limit = '&limit=%s' % getSetting('page.item.limit')
session = requests.Session()
retries = Retry(total=4, backoff_factor=0.3, status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 524, 530])
session.mount('https://api.mdblist.com', HTTPAdapter(max_retries=retries, pool_maxsize=100))
highlight_color = getSetting('highlight.color')
artPath = control.artPath()
iconLogos = getSetting('icon.logos') != 'Traditional'
mdblist_icon = control.joinPath(control.artPath(), 'mdblist.png')
headers = {}
headers['Content-Type'] = 'application/json'

def getMDBTopList(self, listType):
	try:
		response = session.get(mdblist_baseurl + mdblist_top_list + mdblist_api, timeout=20)
		if isinstance(response, dict):
			return None
		items = _map_top_list(response, listType)
		return items
	except: log_utils.error('get MDBList Error: ')
	return None

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
    for i in jsonResponse:
        item = {}
        item['label'] = i.get('title')
        item['rank'] = i.get('rank')
        item['adult'] = i.get('adult')
        item['title'] = i.get('title')
        item['id'] = i.get('id')
        item['imdb'] = i.get('imdb_id')
        item['release_year'] = i.get('release_year')
        items_append(item)
    return items
def getMDBUserList(self, listType):
    try:
        response = session.get(mdblist_baseurl + mdblist_user_list + mdblist_api + mdblist_page_limit, timeout=20)
        if isinstance(response, dict): 
            log_utils.log(response.error, level=log_utils.LOGDEBUG)
            return None
        items = _map_user_list_items(response, listType)
        return items
    except: log_utils.error('get MDBList Error: ')
    return None
def _map_user_list_items(response, listType):
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
            items_append(item)
    return items

def get_user_watchlist(listType):
    try:
        
        response = session.get(f"{mdblist_baseurl}/watchlist/items?apikey={mdblist_api}", timeout=20)
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

def manager(name, imdb=None, tvdb=None, tmdb=None):
    lists = []
    try:
        items = []
        items += [(getLS(40596) % highlight_color, 'add')]
        items += [(getLS(40597) % highlight_color, 'remove')]
        if not tvdb or tvdb == 'None':
            from resources.lib.menus import movies
            result = movies.Movies().getMDBUserList(create_directory=False)
        else:
            from resources.lib.menus import tvshows
            result = tvshows.TVShows().getMDBUserList(create_directory=False)
        lists = [(i['name'], i['list_id']) for i in result]
        lists2 = [(i['name'], i['list_id']) for i in result]
        lists = [lists[i//2] for i in range(len(lists)*2)]

        for i in range(0, len(lists), 2):
            lists[i] = ((getLS(33580) % (highlight_color, lists[i][0])), '/lists/%s/items/add' % lists[i][1])
        for i in range(1, len(lists), 2):
            lists[i] = ((getLS(33581) % (highlight_color, lists[i][0])), '/lists/%s/items/remove' % lists[i][1])
        items += lists
        control.hide()
        select = control.selectDialog([i[0] for i in items], heading=control.addonInfo('name') + ' - ' + getLS(32515))
        if select == -1: return
        if select >= 0:
                if not tvdb or tvdb == 'None': post = {"movies": [{"imdb": imdb}]}
                else:
                    post = {"shows": [{"tmdb": tmdb}]}
                if type(post) == dict or type(post) == list: 
                    import json
                    post = json.dumps(post)
                if items[select][1] == 'add':
                    response = session.post(f"{mdblist_baseurl}/watchlist/items/add?apikey={mdblist_api}",data=post, headers=headers, timeout=20)
                    action = 'add'
                    listid = 'MDBList Watchlist'
                if items[select][1] == 'remove':
                    response = session.post(f"{mdblist_baseurl}/watchlist/items/remove?apikey={mdblist_api}",data=post, headers=headers, timeout=20)
                    action = 'remove'
                    listid = 'MDBList Watchlist'
                for count in range(len(lists)):
                    i = lists[count]
                    if i[1] == '%s' % items[select][1]:
                        response = session.post(mdblist_baseurl + items[select][1] + '?apikey=' + mdblist_api, data=post, headers=headers, timeout=20)
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