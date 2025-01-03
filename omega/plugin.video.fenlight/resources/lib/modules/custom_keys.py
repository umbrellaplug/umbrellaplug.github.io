# -*- coding: utf-8 -*-
from urllib.parse import parse_qsl
from modules.kodi_utils import get_infolabel, activate_window, container_update, hide_busy_dialog
from indexers.dialogs import extras_menu_choice, options_menu_choice
# from modules.kodi_utils import logger

list_item_str, plugin_str = 'ListItem.Property(fenlight.%s)', 'plugin://plugin.video.fenlight/?'

def extras_menu():
	params = get_params('extras_params')
	if params: extras_menu_choice(params)

def options_menu():
	params = get_params('options_params')
	if params: options_menu_choice(params)

def more_like_this():
	hide_busy_dialog()
	params = get_params('more_like_this_params')
	if params:
		window_function = activate_window if params['is_external'] in (True, 'True', 'true') else container_update
		return window_function(params)

def get_params(param_name):
	try: params = dict(parse_qsl(get_infolabel(list_item_str % param_name).split(plugin_str)[1], keep_blank_values=True))
	except: params = None
	return params