# -*- coding: utf-8 -*-
import json
from urllib.parse import parse_qsl, unquote
from caches.navigator_cache import navigator_cache, main_menus
from modules import kodi_utils
# logger = kodi_utils.logger

build_url, confirm_dialog, kodi_dialog, sleep, kodi_refresh = kodi_utils.build_url, kodi_utils.confirm_dialog, kodi_utils.kodi_dialog, kodi_utils.sleep, kodi_utils.kodi_refresh
get_infolabel, select_dialog, notification, execute_builtin = kodi_utils.get_infolabel, kodi_utils.select_dialog, kodi_utils.notification, kodi_utils.execute_builtin
get_icon, random_valid_type_check = kodi_utils.get_icon, kodi_utils.random_valid_type_check
show_busy_dialog, hide_busy_dialog, get_directory = kodi_utils.show_busy_dialog, kodi_utils.hide_busy_dialog, kodi_utils.jsonrpc_get_directory
get_all_icon_vars = kodi_utils.get_all_icon_vars
main_list_name_dict = {'RootList': 'Root', 'MovieList': 'Movies', 'TVShowList': 'TV Shows', 'AnimeList': 'Animes'}
default_path = 'plugin://plugin.video.fenlight?mode=navigator.main&full_list=true'

class MenuEditor:
	def __init__(self, params):
		self.name = self._get_menu_item(get_infolabel('ListItem.FileNameAndPath')).get('name', '')
		self.active_list = params.get('active_list')
		self.position = int(params.get('position', '0'))
		self.action = params.get('action')
		try: self.list_name = main_list_name_dict[self.active_list]
		except: self.list_name = params.get('name')

	def move(self):
		list_items = navigator_cache.currently_used_list(self.active_list)
		if len(list_items) == 1: return notification('Cancelled', 1500)
		choice_items = [i for i in list_items if str(i['name']) != str(self.name)]
		new_position = self._menu_select(choice_items, self.name, multi_line='true', position_list=True)
		if new_position == None or new_position == self.position: return
		list_items.insert(new_position, list_items.pop(self.position))
		self._db_execute('set', self.active_list, list_items)

	def remove(self):
		if not confirm_dialog(): return notification('Cancelled', 1500)
		list_items = navigator_cache.currently_used_list(self.active_list)
		if len(list_items) == 1: return notification('Cancelled', 1500)
		list_items = [i for i in list_items if str(i['name']) != str(self.name)]
		self._db_execute('set', self.active_list, list_items)

	def restore(self):
		if not confirm_dialog(): return notification('Cancelled', 1500)
		self._db_execute('delete', self.active_list, list_type='edited', refresh=False)
		self._db_execute('set', self.active_list, main_menus[self.active_list], 'default')

	def reload(self):
		default, edited = navigator_cache.get_main_lists(self.active_list)
		list_type = 'edited' if edited else 'default'
		current_list = edited or default
		try: new_item = [i for i in default if str(i['name']) == str(self.name)][0]
		except: return notification('No Results', 1500)
		list_items = [i for i in current_list if str(i['name']) != str(self.name)]
		list_items.insert(self.position, new_item)
		self._db_execute('set', self.active_list, list_items, list_type)

	def update(self):
		new_contents = main_menus[self.active_list]
		default, edited = navigator_cache.get_main_lists(self.active_list)
		list_type = 'edited' if edited else'default'
		current_list = edited or default
		if default == new_contents: return notification('No New Items', 1500)
		new_entry = [i for i in new_contents if not i in default][0]
		new_entry_translated_name = new_entry.get('name')
		if not confirm_dialog(text='New item [B]%s[/B] Exists[CR]Would you like to add this to the Menu?' % new_entry_translated_name): return notification('Cancelled', 1500)
		item_position = self._menu_select(current_list, new_entry_translated_name, position_list=True)
		if item_position == None: return notification('Cancelled', 1500)
		current_list.insert(item_position, new_entry)
		self._db_execute('set', self.active_list, current_list, list_type)
		if list_type == 'edited': self._db_execute('set', self.active_list, new_contents, 'default')

	def browse(self):
		list_name =  main_list_name_dict[self.active_list]
		try: choice_items = self._get_removed_items()
		except: return notification('No Results', 1500)
		if not choice_items: return notification('No Results', 1500)
		browse_item = self._menu_select(choice_items, list_name)
		if browse_item == None: return
		browse_item = choice_items[browse_item]
		if browse_item.get('mode') == 'build_popular_people': command = 'RunPlugin(%s)'
		else: command = 'Container.Update(%s)'
		execute_builtin(command % build_url(browse_item))

	def add(self):
		list_name =  main_list_name_dict[self.active_list]
		list_items = navigator_cache.currently_used_list(self.active_list)
		browsed_result = self._path_browser()
		if browsed_result == None: return
		menu_item = self._get_menu_item(browsed_result['file'])
		name, icon = browsed_result['label'], self._get_icon_var(browsed_result['thumbnail'])
		menu_name = self._get_external_name_input(name) or name
		icon_choice = self._icon_select(default_icon=icon)
		menu_item.update({'name': menu_name, 'iconImage': icon_choice})
		position = self._menu_select(list_items, list_name, multi_line='true', position_list=True)
		if position == None: return notification('Cancelled', 1500)
		list_items.insert(position, menu_item)
		self._db_execute('set', self.active_list, list_items)

	def shortcut_folder_edit(self):
		if self.action == 'clear':
			if not confirm_dialog(): return notification('Cancelled', 1500)
			list_items = []
		elif self.action == 'add': return self.shortcut_folder_add()
		else:
			list_items = navigator_cache.get_shortcut_folder_contents(self.active_list)
			if self.action == 'rename':
				current_item = list_items[self.position]
				item_name = current_item['name']
				new_item_name = self._get_external_name_input(item_name)
				if not new_item_name or new_item_name == item_name: return
				current_item['name'] = new_item_name
				list_items[self.position] == current_item
			elif self.action == 'remove':
				if not confirm_dialog(): return notification('Cancelled', 1500)
				list_items = [i for i in list_items if str(i['name']) != str(self.name)]
			elif self.action == 'move':
				if len(list_items) == 1: return notification('Cancelled', 1500)
				choice_items = [i for i in list_items if str(i['name']) != str(self.name)]
				new_position = self._menu_select(choice_items, self.name, multi_line='true', position_list=True)
				if new_position == None or new_position == self.position: return
				list_items.insert(new_position, list_items.pop(self.position))
			elif self.action == 'add':
				return self.shortcut_folder_add()
		self._db_execute('set', self.active_list, list_items, 'shortcut_folder')

	def shortcut_folder_make(self):
		list_name = kodi_dialog().input('')
		if not list_name: return
		self._db_execute('make_new_shortcut_folder', list_name, list_type='shortcut_folder')

	def shortcut_folder_delete(self):
		if not confirm_dialog(): return notification('Cancelled', 1500)
		main_menu_items_list = [(i, navigator_cache.currently_used_list(i)) for i in main_menus]
		self._db_execute('delete', self.name, list_type='shortcut_folder')
		self._remove_active_shortcut_folder(main_menu_items_list, self.name)

	def shortcut_folder_rename(self):
		new_folder_name = self._get_external_name_input(self.name)
		if not new_folder_name: return
		if new_folder_name == self.name: return
		list_items = navigator_cache.get_shortcut_folder_contents(self.name)
		self._db_execute('delete', self.name, list_type='shortcut_folder', refresh=False)
		self._db_execute('make_new_shortcut_folder', new_folder_name, list_items)

	def shortcut_folder_convert(self):
		list_items = navigator_cache.get_shortcut_folder_contents(self.name)
		valid_random_items = [i for i in list_items if i.get('mode').replace('random.', '') in random_valid_type_check]
		make_random = '[COLOR red][RANDOM][/COLOR]' not in self.name
		if make_random:
			if not valid_random_items: return notification('No random supported items in this list', 5000)
			new_folder_name = self.name + ' [COLOR red][RANDOM][/COLOR]'
		else: new_folder_name = self.name.replace(' [COLOR red][RANDOM][/COLOR]', '')
		self._db_execute('delete', self.name, list_type='shortcut_folder', refresh=False)
		self._db_execute('make_new_shortcut_folder', new_folder_name, list_items)

	def shortcut_folder_add(self):
		choice_name, list_items = self.list_name, navigator_cache.get_shortcut_folder_contents(self.list_name)
		browsed_result = self._path_browser()
		if browsed_result == None: return
		menu_item = self._get_menu_item(browsed_result['file'])
		name, icon = browsed_result['label'], self._get_icon_var(browsed_result['thumbnail'])
		menu_name = self._get_external_name_input(name) or name
		icon_choice = self._icon_select(default_icon=icon)
		menu_item.update({'name': menu_name, 'iconImage': icon_choice})
		if list_items:
			position = self._menu_select(list_items, menu_name, multi_line='true', position_list=True)
			if position == None: return notification('Cancelled', 1500)
		else: position = 0
		list_items.insert(position, menu_item)
		self._db_execute('set', choice_name, list_items, 'shortcut_folder')

	def _menu_select(self, choice_items, menu_name, heading='', multi_line='false', position_list=False):
		def _builder():
			for item in choice_items:
				item_get = item.get
				line2 = 'Place [B]%s[/B] below [B]%s[/B]' % (menu_name, item_get('name', None) or item_get('list_name') if position_list else '')
				iconImage = item_get('iconImage', None)
				if iconImage: icon = iconImage if iconImage.startswith('http') else get_icon(item_get('iconImage'))
				else: icon = get_icon('folder')
				yield {'line1': item_get('name'), 'line2': line2, 'icon':icon}
		list_items = list(_builder())
		if position_list: list_items.insert(0, {'line1': 'Top Position', 'line2': 'Place [B]%s[/B] at Top of List' % menu_name, 'icon': get_icon('top')})
		index_list = [list_items.index(i) for i in list_items]
		kwargs = {'items': json.dumps(list_items), 'heading': heading, 'multi_line': multi_line}
		return select_dialog(index_list, **kwargs)

	def _icon_select(self, default_icon=''):
		all_icons = get_all_icon_vars()
		if default_icon:
			try:
				all_icons.remove(default_icon)
				all_icons.insert(0, default_icon)
			except: pass
			list_items = [{'line1': i if i != default_icon else '%s (default)' % default_icon, 'icon': get_icon(i)} for i in all_icons]
		else: list_items = [{'line1': i, 'icon': get_icon(i)} for i in all_icons]
		kwargs = {'items': json.dumps(list_items), 'heading': 'Choose Icon'}
		icon_choice = select_dialog(all_icons, **kwargs) or default_icon or 'folder'
		return icon_choice

	def _get_removed_items(self):
		default_list_items, list_items = navigator_cache.get_main_lists(self.active_list)
		return [i for i in default_list_items if not i in list_items]

	def _get_external_name_input(self, current_name):
		new_name = kodi_dialog().input('', defaultt=current_name)
		if new_name == current_name: return None
		return new_name

	def _remove_active_shortcut_folder(self, main_menu_items_list, folder_name):
		for x in main_menu_items_list:
			try:
				match = [i for i in x[1] if str(i['name']) == str(folder_name)][0]
				new_list = [i for i in x[1] if i != match]
				self._db_execute('set', x[0], new_list, refresh=False)
			except: pass

	def _db_execute(self, db_action, list_name, list_contents=[], list_type='edited', refresh=True):
		if db_action == 'set': navigator_cache.set_list(list_name, list_type, list_contents)
		elif db_action == 'delete': navigator_cache.delete_list(list_name, list_type)
		elif db_action == 'make_new_shortcut_folder': navigator_cache.set_list(list_name, 'shortcut_folder', list_contents)
		else: return notification('Failed', 1500)
		notification('Success', 1500)
		sleep(500)
		if refresh: kodi_refresh()

	def _path_browser(self, label='', file=default_path, thumbnail=''):
		show_busy_dialog()
		results = get_directory(file)
		hide_busy_dialog()
		list_items, function_items = [], []
		if file != default_path:
			list_items.append({'line1': 'Use [B]%s[/B] As Path' % label, 'icon': thumbnail})
			function_items.append(json.dumps({'label': label, 'file': file, 'thumbnail': thumbnail}))
		list_items.extend([{'line1': '%s >>' % i['label'], 'icon': i['thumbnail']} for i in results])
		function_items.extend([json.dumps({'label': i['label'], 'file': '%s%s' % (i['file'], '&full_list=true') if 'navigator.main' in i['file'] else i['file'],
								'thumbnail': i['thumbnail']}) for i in results])
		kwargs = {'items': json.dumps(list_items)}
		choice = select_dialog(function_items, **kwargs)
		if choice == None: return None
		choice = json.loads(choice)
		if choice['file'] == file: return choice
		else: return self._path_browser(**choice)

	def _get_menu_item(self, path):
		return dict(parse_qsl(path.replace('plugin://plugin.video.fenlight/?','')))

	def _get_icon_var(self, icon_path):
		try:
			all_icons = get_all_icon_vars(include_values=True)
			icon_value = unquote(icon_path)
			icon_value = icon_value.replace('image://', '').replace('.png/', '').replace('.png', '')
			icon_value = icon_value.split('/')[-1]
			icon_var = [i[0] for i in all_icons if i[1] == icon_value][0]
		except: icon_var = 'folder'
		return icon_var
