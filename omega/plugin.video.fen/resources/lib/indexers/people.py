# -*- coding: utf-8 -*-
import os
from apis.tmdb_api import tmdb_people_info
from windows.base_window import open_window
from indexers.images import Images
from modules import kodi_utils
# logger = kodi_utils.logger

json, select_dialog, dialog, show_busy_dialog, hide_busy_dialog = kodi_utils.json, kodi_utils.select_dialog, kodi_utils.dialog, kodi_utils.show_busy_dialog, kodi_utils.hide_busy_dialog
notification, get_icon, unquote, kodi_refresh, ls = kodi_utils.notification, kodi_utils.get_icon, kodi_utils.unquote, kodi_utils.kodi_refresh, kodi_utils.local_string
add_items, set_content, set_category, end_directory = kodi_utils.add_items, kodi_utils.set_content, kodi_utils.set_category, kodi_utils.end_directory
build_url, make_listitem, sys = kodi_utils.build_url, kodi_utils.make_listitem, kodi_utils.sys
addon_fanart = kodi_utils.addon_fanart
tmdb_image_url = 'https://image.tmdb.org/t/p/h632/%s'
default_image = get_icon('genre_family')

def popular_people():
	Images().run({'mode': 'popular_people_image_results', 'page_no': 1})

def person_data_dialog(params):
	if params.get('query', ''): query = unquote(params['query'])
	else: query = None
	open_window(('windows.people', 'People'), 'people.xml', query=query, actor_name=params.get('actor_name'), actor_image=params.get('actor_image'),
				actor_id=params.get('actor_id'), reference_tmdb_id=params.get('reference_tmdb_id'), is_external=params.get('is_external', 'false'),
				starting_position=params.get('starting_position', None))

def person_direct_search(query):
	def _builder():
		for item in data:
			actor_id = int(item['id'])
			actor_name = item['name']
			actor_image = tmdb_image_url % item['profile_path'] if item['profile_path'] else default_image
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
	query = unquote(query)
	try: data = tmdb_people_info(query)
	except: data = []
	handle = int(sys.argv[1])
	add_items(handle, list(_builder()))
	set_content(handle, 'movies')
	set_category(handle, query)
	end_directory(handle, False)

def person_search(query=None):
	show_busy_dialog()
	query = unquote(query)
	try: data = tmdb_people_info(query)
	except: data = []
	hide_busy_dialog()
	if not data: return notification(32760)
	if len(data) == 1:
		person = data[0]
		actor_id, actor_name = person['id'], person['name']
		try: image_id = person['profile_path']
		except: image_id = None
		if not image_id: actor_image = default_image
		else: actor_image = tmdb_image_url % image_id
	else:
		def _builder():
			for item in data:
				known_for_list = [i.get('title', 'NA') for i in item['known_for']]
				known_for_list = [i for i in known_for_list if not i == 'NA']
				image = tmdb_image_url % item['profile_path'] if item['profile_path'] else default_image
				yield {'line1': item['name'], 'line2': ', '.join(known_for_list) if known_for_list else '', 'icon': image}
		list_items = list(_builder())
		kwargs = {'items': json.dumps(list_items), 'multi_line': 'true'}
		person = select_dialog(data, **kwargs)
		if person == None: return None, None, None
		actor_id = int(person['id'])
		actor_name = person['name']
		actor_image = tmdb_image_url % person['profile_path'] if person['profile_path'] else default_image
	if not actor_name: return
	return person_data_dialog({'actor_name': actor_name, 'actor_image': actor_image, 'actor_id': actor_id})



