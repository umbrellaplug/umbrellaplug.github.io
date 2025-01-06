# -*- coding: utf-8 -*-
import os
from windows.base_window import open_window
from apis.tmdb_api import tmdb_people_full_info, tmdb_popular_people
from apis.imdb_api import imdb_images, imdb_people_id, imdb_people_images
from modules import kodi_utils
# logger = kodi_utils.logger

json, notification, set_property, make_listitem, list_dirs = kodi_utils.json, kodi_utils.notification, kodi_utils.set_property, kodi_utils.make_listitem, kodi_utils.list_dirs
delete_file, show_busy_dialog, hide_busy_dialog, get_icon = kodi_utils.delete_file, kodi_utils.show_busy_dialog, kodi_utils.hide_busy_dialog, kodi_utils.get_icon
Thread, image_extensions, tmdb_image_base = kodi_utils.Thread, kodi_utils.image_extensions, 'https://image.tmdb.org/t/p/%s%s'

class Images():
	def run(self, params):
		show_busy_dialog()
		self.list_items = []
		self.params = params
		self.mode = self.params.pop('mode')
		if self.mode == 'people_image_results': self.people_image_results()
		elif self.mode == 'people_tagged_image_results': self.people_tagged_image_results()
		elif self.mode == 'imdb_image_results': self.imdb_image_results()
		elif self.mode == 'popular_people_image_results': self.popular_people_image_results()
		elif self.mode == 'browser_image': self.browser_image(params['folder_path'])
		elif self.mode == 'imageviewer': return self.imageviewer()
		elif self.mode == 'delete_image': return self.delete_image()
		hide_busy_dialog()
		if len(self.list_items) == 0: return notification(32575)
		if not 'in_progress' in params: self.open_window_xml()
		else: return self.list_items, self.next_page_params

	def open_window_xml(self):
		hide_busy_dialog()
		open_window(('windows.imageviewer', 'ThumbImageViewer'), 'thumbviewer.xml', list_items=self.list_items, next_page_params= self.next_page_params, ImagesInstance=self)

	def imageviewer(self):
		hide_busy_dialog()
		return open_window(('windows.imageviewer', 'ImageViewer'), 'imageviewer.xml', all_images=self.params['all_images'], index=int(self.params['current_index']))

	def popular_people_image_results(self):
		def builder():
			for item in image_info['results']:
				if item['profile_path']: actor_poster, actor_image = tmdb_image_base % ('w185', item['profile_path']), tmdb_image_base % ('h632', item['profile_path'])
				else: actor_poster, actor_image = get_icon('genre_family'), get_icon('genre_family')
				url_params = {'mode': 'person_data_dialog', 'actor_name': item['name'], 'actor_id': item['id'], 'actor_image': actor_image}
				listitem = make_listitem()
				listitem.setProperty('thumb', actor_poster)
				listitem.setProperty('name', item['name'])
				listitem.setProperty('action', json.dumps(url_params))
				yield listitem
		page_no = self.params['page_no']
		image_info = tmdb_popular_people(page_no)
		self.list_items = list(builder())
		if image_info['total_pages'] > page_no: page_no += 1
		else: page_no = 'final_page'
		self.next_page_params = {'mode': 'popular_people_image_results', 'page_no': page_no}

	def imdb_image_results(self):
		def builder(rolling_count):
			for item in image_info:
				try:
					listitem = make_listitem()
					rolling_count += 1
					name = '%s_%s_%03d' % (media_title, item['title'], rolling_count)
					listitem.setProperty('thumb', item['thumb'])
					listitem.setProperty('path', item['image'])
					listitem.setProperty('name', name)
					listitem.setProperty('action', image_action)
					yield listitem
				except: pass
		imdb_id, page_no, rolling_count_list = self.params['imdb_id'], self.params['page_no'], self.params['rolling_count_list']
		rolling_count = rolling_count_list[page_no-1]
		media_title = self.params['media_title']
		image_info, next_page = imdb_images(imdb_id, page_no)
		image_info.sort(key=lambda x: x['title'])
		all_images = [(i['image'], '%s_%s' % (media_title, i['title'])) for i in image_info]
		image_action = json.dumps({'mode': 'imageviewer', 'all_images': all_images})
		self.list_items = list(builder(rolling_count))
		rolling_count += len(image_info)
		if len(image_info) == 48:
			if len(rolling_count_list) == page_no: rolling_count_list.insert(page_no, rolling_count)
			page_no = next_page
		else: page_no = 'final_page'
		self.next_page_params = {'mode': 'imdb_image_results', 'imdb_id': imdb_id, 'page_no': page_no, 'rolling_count_list': rolling_count_list, 'media_title': media_title}

	def people_image_results(self):
		def get_tmdb():
			try: tmdb_append(tmdb_people_full_info(actor_id).get('images', []))
			except: pass
		def get_imdb():
			try: imdb_append(imdb_people_images(actor_imdb_id, page_no)[0])
			except: pass
		def builder():
			for item in all_images:
				try:
					listitem = make_listitem()
					listitem.setProperty('path', item[0])
					listitem.setProperty('name', item[1])
					listitem.setProperty('thumb', item[2])
					listitem.setProperty('action', image_action)
					yield listitem
				except: pass
		threads, tmdb_images, all_images, tmdb_results, imdb_results = [], [], [], [], []
		tmdb_append, imdb_append = tmdb_results.append, imdb_results.append
		actor_name, actor_id = self.params['actor_name'], self.params['actor_id']
		actor_imdb_id = self.params['actor_imdb_id'] or imdb_people_id(actor_name)
		actor_image = self.params.get('actor_image', '')
		page_no = self.params['page_no']
		rolling_count_list = self.params['rolling_count_list']
		rolling_count = rolling_count_list[page_no-1]
		if page_no == 1: threads.append(Thread(target=get_tmdb))
		threads.append(Thread(target=get_imdb))
		[i.start() for i in threads]
		[i.join() for i in threads]
		if page_no == 1:
			try:
				tmdb_image_info = tmdb_results[0]['profiles']
				tmdb_image_info.sort(key=lambda x: x['file_path'])
				tmdb_images = [(tmdb_image_base % ('original', i['file_path']), '%s_%03d' % (actor_name, count),
								tmdb_image_base % ('w185', i['file_path'])) for count, i in enumerate(tmdb_image_info, rolling_count+1)]
				all_images.extend(tmdb_images)
			except: pass
		rolling_count += len(tmdb_images)
		imdb_image_info = imdb_results[0]
		imdb_image_info.sort(key=lambda x: x['title'])
		imdb_images = [(i['image'], '%s_%s_%03d' % (actor_name, i['title'], count), i['thumb']) for count, i in enumerate(imdb_image_info, rolling_count+1)]
		all_images.extend(imdb_images)
		rolling_count += len(imdb_images)
		image_action = json.dumps({'mode': 'imageviewer', 'all_images': all_images})
		self.list_items = list(builder())
		if len(imdb_image_info) == 48:
			if len(rolling_count_list) == page_no: rolling_count_list.insert(page_no, rolling_count)
			page_no += 1
		else: page_no = 'final_page'
		self.next_page_params = {'mode': 'people_image_results', 'actor_id': actor_id, 'actor_name': actor_name, 'actor_imdb_id': actor_imdb_id,
								'actor_image': actor_image, 'page_no': page_no, 'rolling_count_list': rolling_count_list}

	def people_tagged_image_results(self):
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
					listitem.setProperty('thumb', thumb_url)
					listitem.setProperty('path', image_url)
					listitem.setProperty('name', name)
					listitem.setProperty('action', image_action)
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
		self.next_page_params = {'mode': 'people_tagged_image_results', 'actor_id': actor_id, 'actor_name': actor_name}

	def browser_image(self, folder_path, return_items=False):
		def builder():
			for item in image_info:
				try:
					listitem = make_listitem()
					image_url = os.path.join(folder_path, item)
					try: thumb_url = os.path.join(thumbs_path, item)
					except: thumb_url = image_url
					listitem.setProperty('thumb', thumb_url)
					listitem.setProperty('path', image_url)
					listitem.setProperty('name', item)
					listitem.setProperty('action', image_action)
					listitem.setProperty('delete', 'true')
					yield listitem
				except: pass
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

	def delete_image(self):
		delete_file(self.params['thumb_url'])
		delete_file(self.params['image_url'])
		hide_busy_dialog()
		set_property('fen.delete_image_finished', 'true')

