# -*- coding: utf-8 -*-
import os
import json
from windows.base_window import open_window
from apis.tmdb_api import tmdb_people_info, tmdb_people_full_info, tmdb_popular_people, tmdb_trending_people_day, tmdb_trending_people_week, tmdb_media_images
from apis.easynews_api import import_easynews
from modules.utils import paginate_list, chunks
from modules import kodi_utils
# logger = kodi_utils.logger

notification, make_listitem, list_dirs, image_extensions = kodi_utils.notification, kodi_utils.make_listitem, kodi_utils.list_dirs, kodi_utils.image_extensions
delete_file, show_busy_dialog, hide_busy_dialog, get_icon = kodi_utils.delete_file, kodi_utils.show_busy_dialog, kodi_utils.hide_busy_dialog, kodi_utils.get_icon
tmdb_image_base = 'https://image.tmdb.org/t/p/%s%s'

class Images():
	def run(self, params):
		show_busy_dialog()
		self.list_items = []
		self.params = params
		self.mode = self.params.pop('mode')
		self.direct_search_result = False
		if self.mode == 'imageviewer': return self.imageviewer()
		if self.mode == 'delete_image': return self.delete_image()
		if self.mode == 'tmdb_people_list_image_results': self.tmdb_people_list_image_results()
		elif self.mode == 'tmdb_people_search_image_results': self.tmdb_people_search_image_results()
		elif self.mode == 'favorite_people_list_image_results': self.favorite_people_list_image_results()
		elif self.mode == 'tmdb_media_image_results': self.tmdb_media_image_results()
		elif self.mode == 'tmdb_people_image_results': self.tmdb_people_image_results()
		elif self.mode == 'tmdb_people_tagged_image_results': self.tmdb_people_tagged_image_results()
		elif self.mode == 'favorites_image_results': self.favorites_image_results()
		elif self.mode == 'easynews_image_results': self.easynews_image_results()
		elif self.mode == 'browser_image': self.browser_image()
		hide_busy_dialog()
		if self.direct_search_result: return
		if len(self.list_items) == 0: return notification('None Found')
		if not 'in_progress' in params: self.open_window_xml()
		else: return self.list_items, self.next_page_params

	def tmdb_people_list_image_results(self):
		def builder():
			for item in image_info['results']:
				try:
					name, actor_id = item['name'], item['id']
					p_path = item['profile_path']
					if p_path: actor_poster, actor_image, actor_url = tmdb_image_base % ('w185', p_path), tmdb_image_base % ('h632', p_path), tmdb_image_base % ('original', p_path)
					else: actor_poster, actor_image, actor_url = get_icon('genre_family'), get_icon('genre_family'), ''
					url_params = {'mode': 'person_data_dialog', 'actor_name': name, 'actor_id': actor_id, 'actor_image': actor_image}
					listitem = make_listitem()
					listitem.setProperties({'thumb': actor_poster, 'path': actor_url, 'name': name, 'actor_name': name, 'actor_id': actor_id,
											'fav_enabled': 'true', 'action': json.dumps(url_params)})
					yield listitem
				except: pass
		action = self.params['action']
		page_no = self.params['page_no']
		function = tmdb_popular_people if action == 'popular' else tmdb_trending_people_day if action == 'day' else tmdb_trending_people_week
		image_info = function(page_no)
		self.list_items = list(builder())
		if image_info['total_pages'] > page_no: page_no += 1
		else: page_no = 'final_page'
		self.next_page_params = {'mode': 'tmdb_people_list_image_results', 'action': action, 'page_no': page_no}

	def tmdb_people_search_image_results(self):
		def builder():
			for item in results:
				try:
					name, actor_id = item['name'], item['id']
					p_path = item['profile_path']
					known_for_list = [i.get('title', 'NA') for i in item['known_for']]
					known_for_list = [i for i in known_for_list if not i == 'NA']
					known_for = ' | [I]%s[/I]' % ', '.join(known_for_list) if known_for_list else ''
					if p_path: actor_poster, actor_image = tmdb_image_base % ('w185', p_path), tmdb_image_base % ('h632', p_path)
					else: actor_poster, actor_image = get_icon('genre_family'), get_icon('genre_family')
					url_params = {'mode': 'person_data_dialog', 'actor_name': name, 'actor_id': actor_id, 'actor_image': actor_image}
					listitem = make_listitem()
					listitem.setProperties({'thumb': actor_poster, 'name': name + known_for, 'actor_name': name, 'actor_id': actor_id,
											'fav_enabled': 'true', 'action': json.dumps(url_params)})
					yield listitem
				except: pass
		page_no = self.params['page_no']
		key_id = self.params.get('key_id') or self.params.get('query')
		try: data = tmdb_people_info(key_id, page_no)
		except: return
		results = data['results']
		if len(results) == 1:
			self.direct_search_result = True
			item = results[0]
			return open_window(('windows.people', 'People'), 'people.xml', key_id=None, actor_name=item['name'], actor_id=item['id'],
					actor_image=tmdb_image_base % ('h632', item['profile_path']) if item['profile_path'] else get_icon('genre_family'))
		self.list_items = list(builder())
		if data['total_pages'] > page_no: page_no += 1
		else: page_no = 'final_page'
		self.next_page_params = {'mode': 'tmdb_people_search_image_results', 'key_id': key_id, 'page_no': page_no}

	def favorite_people_list_image_results(self, return_items=False):
		from modules.favorites import get_favorites
		def builder():
			for item in image_info:
				try:
					title, actor_id = item['title'], item['media_id']
					name, actor_poster, actor_image = title.split('|')
					url_params = {'mode': 'person_data_dialog', 'actor_name': name, 'actor_id': actor_id, 'actor_image': actor_image}
					listitem = make_listitem()
					listitem.setProperties({'thumb': actor_poster, 'name': name, 'actor_name': name, 'actor_id': actor_id, 'action': json.dumps(url_params), 'in_favorites': 'true'})
					yield listitem
				except: pass
		image_info = get_favorites('people', 'dummy_arg')
		self.list_items = list(builder())
		self.next_page_params = {}
		if return_items: return self.list_items

	def tmdb_media_image_results(self):
		def builder():
			for item in all_images:
				try:
					listitem = make_listitem()
					listitem.setProperties({'thumb': item[2], 'path': item[0], 'name': item[1], 'action': image_action})
					yield listitem
				except: pass
		rootname = self.params['rootname']
		all_images = []
		results = tmdb_media_images(self.params['media_type'], self.params['tmdb_id'])
		try:
			posters, clearlogos = [i for i in results['posters']], [dict(i, **{'file_path': '%s.png' % i['file_path'].split('.')[0]}) for i in results['logos']]
			fanarts, landscapes = [i for i in results['backdrops'] if not i['iso_639_1']], [i for i in results['backdrops'] if i['iso_639_1']]
			for item in ((posters, '%s _Poster_%03d'), (fanarts, '%s _Fanart_%03d'), (landscapes, '%s _Landscape_%03d'), (clearlogos, '%s _Clearlogo_%03d')):
				if item[0]: all_images.extend([(tmdb_image_base % ('original', i['file_path']), item[1] % (rootname, count), tmdb_image_base % ('w300', i['file_path'])) \
												for count, i in enumerate(item[0], 1)])
		except: pass
		image_action = json.dumps({'mode': 'imageviewer', 'all_images': all_images})
		self.list_items = list(builder())
		self.next_page_params = {}

	def tmdb_people_image_results(self):
		def builder():
			for item in all_images:
				try:
					listitem = make_listitem()
					listitem.setProperties({'thumb': item[2], 'path': item[0], 'name': item[1], 'action': image_action})
					yield listitem
				except: pass
		all_images = []
		actor_name, actor_id = self.params['actor_name'], self.params['actor_id']
		try:
			results = tmdb_people_full_info(actor_id).get('images', [])
			image_info = results['profiles']
			image_info.sort(key=lambda x: x['file_path'])
			all_images = [(tmdb_image_base % ('original', i['file_path']), '%s_%03d' % (actor_name, count),
						tmdb_image_base % ('w185', i['file_path'])) for count, i in enumerate(image_info, 1)]
		except: pass
		image_action = json.dumps({'mode': 'imageviewer', 'all_images': all_images})
		self.list_items = list(builder())
		self.next_page_params = {}

	def tmdb_people_tagged_image_results(self):
		def builder():
			for count, item in enumerate(image_info, 1):
				try:
					media = item['media']
					if 'title' in media: name_key = 'title'
					else: name_key = 'name'
					thumb_url = tmdb_image_base % ('w185', item['file_path'])
					image_url = tmdb_image_base % ('original', item['file_path'])
					name = '%s_%s_%03d' % (actor_name, media[name_key], count)
					listitem = make_listitem()
					listitem.setProperties({'thumb': thumb_url, 'path': image_url, 'name': name, 'action': image_action})
					yield listitem
				except: pass
		actor_name, actor_id = self.params['actor_name'], self.params['actor_id']
		try: results = tmdb_people_full_info(actor_id)['tagged_images']
		except: return
		image_info = results['results']
		image_info.sort(key=lambda x: x['file_path'])
		all_images = [(tmdb_image_base % ('original', i['file_path']), (i['media']['title']) if 'title' in i['media'] else i['media']['name']) for i in image_info]
		image_action = json.dumps({'mode': 'imageviewer', 'all_images': all_images})
		self.list_items = list(builder())
		self.next_page_params = {'mode': 'tmdb_people_tagged_image_results', 'actor_id': actor_id, 'actor_name': actor_name}

	def easynews_image_results(self):
		def builder():
			for item in image_info:
				try:
					listitem = make_listitem()
					listitem.setProperties({'thumb': item['thumbnail'], 'path': item['down_url'], 'name': item['name'], 'action': image_action})
					yield listitem
				except: pass
		EasyNews = import_easynews()
		key_id, page_no = self.params['key_id'], self.params['page_no']
		results = EasyNews.search_images(key_id, page_no)
		image_info, total_pages = results['results'], results['total_pages']
		all_images = [(i['url_dl'], i['name']) for i in image_info]
		image_action = json.dumps({'mode': 'imageviewer', 'all_images': all_images})
		self.list_items = list(builder())
		new_page = page_no + 1
		if new_page > total_pages: new_page = 'final_page'
		self.next_page_params = {'mode': 'easynews_image_results', 'key_id': key_id, 'page_no': new_page}

	def browser_image(self, folder_path=None, return_items=False):
		def builder():
			for item in image_info:
				try:
					listitem = make_listitem()
					image_url = os.path.join(folder_path, item)
					try: thumb_url = os.path.join(thumbs_path, item)
					except: thumb_url = image_url
					listitem.setProperties({'thumb': thumb_url, 'path': image_url, 'name': item, 'action': image_action, 'delete': 'true'})
					yield listitem
				except: pass
		if not folder_path: folder_path = self.params.get('folder_path')
		image_info = list_dirs(folder_path)[1]
		image_info.sort()
		thumbs_path = os.path.join(folder_path, '.thumbs')
		thumbs_info = list_dirs(thumbs_path)[1]
		thumbs_info.sort()
		thumbs_info = [i for i in thumbs_info if i.endswith(image_extensions)]
		image_info = [i for i in image_info if i in thumbs_info]
		all_images = [(os.path.join(folder_path, i), i) for i in image_info if i in thumbs_info]
		image_action = json.dumps({'mode': 'imageviewer', 'all_images': all_images, 'page_no': 'final_page'})
		self.list_items = list(builder())
		self.next_page_params = {}
		if return_items: return self.list_items

	def open_window_xml(self):
		hide_busy_dialog()
		open_window(('windows.imageviewer', 'ThumbImageViewer'), 'thumbviewer.xml', list_items=self.list_items, next_page_params= self.next_page_params, ImagesInstance=self)

	def imageviewer(self):
		hide_busy_dialog()
		return open_window(('windows.imageviewer', 'ImageViewer'), 'imageviewer.xml', all_images=self.params['all_images'], index=int(self.params['current_index']))

	def delete_image(self, image_url=None, thumb_url=None):
		image_url, thumb_url = image_url or self.params['image_url'], thumb_url or self.params['thumb_url']
		delete_file(thumb_url)
		delete_file(image_url)
		hide_busy_dialog()
