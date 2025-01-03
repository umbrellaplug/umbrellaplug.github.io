# -*- coding: utf-8 -*-
import os
import sys
from urllib.parse import unquote
from apis.tmdb_api import tmdb_people_info
from windows.base_window import open_window
from indexers.images import Images
from modules import kodi_utils
# logger = kodi_utils.logger

get_icon, addon_fanart = kodi_utils.get_icon, kodi_utils.get_addon_fanart()
add_items, set_content, set_category, end_directory = kodi_utils.add_items, kodi_utils.set_content, kodi_utils.set_category, kodi_utils.end_directory
build_url, make_listitem = kodi_utils.build_url, kodi_utils.make_listitem
tmdb_image_base = 'https://image.tmdb.org/t/p/%s%s'
default_image = get_icon('genre_family')

def tmdb_people(params):
	return Images().run({'mode': 'tmdb_people_list_image_results', 'action': params['action'], 'page_no': 1})

def person_search(key_id=None):
	return Images().run({'mode': 'tmdb_people_search_image_results', 'key_id': unquote(key_id), 'page_no': 1})

def favorite_people():
	return Images().run({'mode': 'favorite_people_list_image_results'})

def person_data_dialog(params):
	if 'key_id' in params: key_id = unquote(params.get('key_id'))
	elif 'query' in params: key_id = unquote(params.get('query'))
	else: key_id = None
	open_window(('windows.people', 'People'), 'people.xml', key_id=key_id, actor_name=params.get('actor_name'), actor_image=params.get('actor_image'),
				actor_id=params.get('actor_id'), reference_tmdb_id=params.get('reference_tmdb_id'), is_external=params.get('is_external', 'false'),
				starting_position=params.get('starting_position', None))

def person_direct_search(key_id):
	def _builder():
		for item in data:
			actor_id = int(item['id'])
			actor_name = item['name']
			image_path = item['profile_path']
			if item['profile_path']: actor_image = tmdb_image_base % ('h632', item['profile_path'])
			else: actor_image = default_image
			known_for_list = [i.get('title', 'NA') for i in item['known_for']]
			known_for_list = [i for i in known_for_list if not i == 'NA']
			known_for = '[B]Known for:[/B]\n%s' % '\n'.join(known_for_list) if known_for_list else ' '
			url_params = {'mode': 'person_data_dialog', 'actor_name': actor_name, 'actor_image': actor_image, 'actor_id': actor_id}
			url = build_url(url_params)
			listitem = make_listitem()
			listitem.setLabel(actor_name)
			listitem.setArt({'icon': actor_image, 'poster': actor_image, 'thumb': actor_image, 'fanart': addon_fanart, 'banner': actor_image})
			info_tag = listitem.getVideoInfoTag()
			info_tag.setPlot(known_for)
			yield (url, listitem, False)
	try:
		key_id = unquote(key_id)
		data = tmdb_people_info(key_id)['results']
	except: data = []
	handle = int(sys.argv[1])
	add_items(handle, list(_builder()))
	set_content(handle, 'movies')
	set_category(handle, key_id)
	end_directory(handle, cacheToDisc=False)



