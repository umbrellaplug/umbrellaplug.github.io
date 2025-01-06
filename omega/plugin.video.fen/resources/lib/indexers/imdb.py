# -*- coding: utf-8 -*-
from apis.imdb_api import imdb_user_lists, imdb_keyword_search
from modules import kodi_utils
# from modules.kodi_utils import logger

ls, sys, build_url, make_listitem, set_view_mode = kodi_utils.local_string, kodi_utils.sys, kodi_utils.build_url, kodi_utils.make_listitem, kodi_utils.set_view_mode
add_items, set_content, set_category, end_directory = kodi_utils.add_items, kodi_utils.set_content, kodi_utils.set_category, kodi_utils.end_directory
default_imdb_icon, fanart = kodi_utils.get_icon('imdb'), kodi_utils.addon_fanart

def imdb_build_user_lists(params):
	def _builder():
		for item in user_lists:
			try:
				cm = []
				cm_append = cm.append
				title = item['title']
				url = build_url({'mode': mode, 'action': 'imdb_user_list_contents', 'list_id': item['list_id']})
				listitem = make_listitem()
				cm_append((ls(32730),'RunPlugin(%s)' % build_url({'mode': 'menu_editor.add_external', 'name': title, 'iconImage': 'imdb'})))
				cm_append((ls(32731),'RunPlugin(%s)' % build_url({'mode': 'menu_editor.shortcut_folder_add_item', 'name': title, 'iconImage': 'imdb'})))
				listitem.addContextMenuItems(cm)
				listitem.setLabel(title)
				listitem.setArt({'icon': default_imdb_icon, 'poster': default_imdb_icon, 'thumb': default_imdb_icon, 'fanart': fanart, 'banner': default_imdb_icon})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				listitem.setProperty('fen.context_main_menu_params', build_url({'mode': 'menu_editor.edit_menu_external', 'name': title, 'iconImage': 'imdb'}))
				yield (url, listitem, True)
			except: pass
	handle = int(sys.argv[1])
	media_type = params.get('media_type')
	user_lists = imdb_user_lists(media_type)
	mode = 'build_%s_list' % media_type
	add_items(handle, list(_builder()))
	set_content(handle, 'files')
	set_category(handle, params.get('category_name'))
	end_directory(handle)
	set_view_mode('view.main')

def imdb_build_keyword_results(params):
	def _builder():
		for count, keyword in enumerate(results, 1):
			try:
				cm = []
				cm_append = cm.append
				name = '%s (IMDb)' % keyword.upper()
				url_params = {'mode': mode, 'action': 'imdb_keywords_list_contents', 'list_id': keyword.lower(), 'iconImage': 'imdb', 'category_name': keyword.capitalize()}
				url = build_url(url_params)
				listitem = make_listitem()
				cm_append((ls(32730),'RunPlugin(%s)' % build_url({'mode': 'menu_editor.add_external', 'name': name, 'iconImage': 'imdb'})))
				cm_append((ls(32731),'RunPlugin(%s)' % build_url({'mode': 'menu_editor.shortcut_folder_add_item', 'name': name, 'iconImage': 'imdb'})))
				listitem.addContextMenuItems(cm)
				listitem.setProperty('fen.context_main_menu_params', build_url({'mode': 'menu_editor.edit_menu_external', 'name': name, 'iconImage': 'imdb'}))
				listitem.setLabel('%02d | %s' % (count, keyword.upper()))
				listitem.setArt({'icon': default_imdb_icon, 'poster': default_imdb_icon, 'thumb': default_imdb_icon, 'fanart': fanart, 'banner': default_imdb_icon})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				yield (url, listitem, True)
			except: pass
	handle = int(sys.argv[1])
	media_type, query = params.get('media_type'), params.get('query')
	results = imdb_keyword_search(query)
	mode = 'build_%s_list' % media_type
	add_items(handle, list(_builder()))
	set_content(handle, 'files')
	set_category(handle, query.capitalize())
	end_directory(handle)
	set_view_mode('view.main')




