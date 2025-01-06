# -*- coding: utf-8 -*-
from indexers import navigator
from caches.navigator_cache import navigator_cache, main_menus, main_menu_items, default_menu_items
from modules import kodi_utils
# logger = kodi_utils.logger

build_url, confirm_dialog, dialog, sleep, kodi_refresh = kodi_utils.build_url, kodi_utils.confirm_dialog, kodi_utils.dialog, kodi_utils.sleep, kodi_utils.kodi_refresh
get_infolabel, select_dialog, notification, execute_builtin = kodi_utils.get_infolabel, kodi_utils.select_dialog, kodi_utils.notification, kodi_utils.execute_builtin
external, open_settings, activate_window, container_update = kodi_utils.external, kodi_utils.open_settings, kodi_utils.activate_window, kodi_utils.container_update
json, tp, ls, parse_qsl, get_icon = kodi_utils.json, kodi_utils.translate_path, kodi_utils.local_string, kodi_utils.parse_qsl, kodi_utils.get_icon
show_busy_dialog, hide_busy_dialog, unquote, get_directory = kodi_utils.show_busy_dialog, kodi_utils.hide_busy_dialog, kodi_utils.unquote, kodi_utils.jsonrpc_get_directory
get_setting, get_all_icon_vars = kodi_utils.get_setting, kodi_utils.get_all_icon_vars
main_list_name_dict = {'RootList': ls(32457), 'MovieList': ls(32028), 'TVShowList': ls(32029)}
pos_str, top_pos_str, top_str, exists_str, addq_str, eadd_str, erename_str = ls(32707), ls(32708), ls(32709), ls(32727), ls(32728), ls(33140), ls(32137)
move_str, remove_str, add_org_str, fol_add_str, orig_add_str, fol_menu_str, trak_add_str = ls(32716), ls(32717), ls(32718), ls(32719), ls(32721), ls(32725), ls(32720)
res_str, brws_str, upd_str, reload_str, emove_str, eremove_str, eclear_str = ls(32722), ls(32706), ls(32723), ls(32724), ls(32712), ls(32713), '%s %s' % (ls(32671), ls(32129))
eedelete_str, eeremove_str, eeclear_str, eefadd_str, eefadde_str, eesets_str, trlike_str = ls(32703), ls(32786), ls(32699), ls(32731), ls(32730), ls(33081), ls(32776)
trunlike_str, trnew_str, trdel_str, eerem_disc_str, down_str, furk_add_str, furk_remove_str = ls(32783), ls(32780), ls(32781), ls(32698), ls(32747), ls(32769), ls(32766)
furk_p_str, furk_up_str, cloud_link_str, cloud_unlink_str, choose_icon_str = ls(32767), ls(32768), ls(33078), ls(33079), ls(33137)
tools_str, settings_str = '%s %s' % (ls(32641), ls(32456)), '%s %s' % (ls(32641), ls(32247))
default_path = 'plugin://plugin.video.fen'

class MenuEditor:
	def __init__(self, params):
		self.params = params
		self.params_get = self.params.get
		if 'menu_item' in self.params: self.menu_item = json.loads(self.params.get('menu_item'))
		else: self.menu_item = dict(parse_qsl(get_infolabel('ListItem.FileNameAndPath').replace('plugin://plugin.video.fen/?','')))
		self.menu_item_get = self.menu_item.get
		self.window_function = activate_window if external() else container_update

	def edit_menu(self):
		active_list, position = self.params_get('active_list'), int(self.params_get('position', '0'))
		menu_name = self.menu_item_get('name')
		menu_name_translated = ls(menu_name)
		menu_name_translated_display = self._remove_bold(menu_name_translated)
		external_list_item, shortcut_folder = self.menu_item_get('external_list_item', 'False') == 'True', self.menu_item_get('shortcut_folder', 'False') == 'True'
		list_name =  main_list_name_dict[active_list]
		listing = []
		append = listing.append
		if len(active_list) != 1:
			append((move_str % menu_name_translated_display, self.move))
			append((remove_str % menu_name_translated_display, self.remove))
		if not shortcut_folder: append((add_org_str % menu_name_translated_display, self.add_original_external))
		append((fol_add_str % menu_name_translated_display, self.shortcut_folder_add_item))
		append((orig_add_str % list_name, self.add_original))
		append((fol_menu_str % list_name, self.shortcut_folder_add_to_main_menu))
		if get_setting('fen.trakt.user', ''): append((trak_add_str % list_name, self.add_trakt))
		append((res_str % list_name, self.restore))
		append((upd_str % list_name, self.check_update_list))
		if not external_list_item: append((reload_str % menu_name_translated_display, self.reload_menu_item))
		append((brws_str, self.browse))
		append((tools_str, self.open_tools))
		append((settings_str, self.open_settings))
		list_items = [{'line1': i[0]} for i in listing]
		kwargs = {'items': json.dumps(list_items), 'narrow_window': 'true'}
		function = select_dialog([i[1] for i in listing], **kwargs)
		if function == None: return
		self.params = {'active_list': active_list, 'list_name': list_name, 'menu_name': menu_name, 'menu_name_translated': menu_name_translated, 'position': position}
		self.params_get = self.params.get
		return function()

	def edit_menu_shortcut_folder(self):
		listing = [(eadd_str, 'add'), ('Rename', 'rename'), (emove_str, 'move'), (eremove_str, 'remove'), (eclear_str, 'clear_all')]
		list_items = [{'line1': i[0]} for i in listing]
		kwargs = {'items': json.dumps(list_items), 'narrow_window': 'true'}
		self.action = select_dialog([i[1] for i in listing], **kwargs)
		if self.action == None: return
		return self.shortcut_folder_contents_adjust()

	def edit_menu_external(self):
		mode, list_type, action = self.menu_item_get('mode'), self.menu_item_get('list_type'), self.menu_item_get('action')
		listing = []
		append = listing.append
		if mode == 'navigator.build_shortcut_folder_list':
			append((self._remove_bold(erename_str), self.shortcut_folder_rename))
			append((self._remove_bold(eedelete_str), self.shortcut_folder_delete))
		elif mode == 'get_search_term':
			append((self._remove_bold(eeremove_str), self.remove_search_history), (self._remove_bold(eeclear_str), self.clear_search_history))
		elif mode in ('playback.video', 'real_debrid.resolve_rd', 'alldebrid.resolve_ad', 'easynews.resolve_easynews', 'cloud.furk_direct', 'furk.furk_t_file_browser'):
			append((self._remove_bold(down_str), self.premium_file_download))
			if mode == 'furk.furk_t_file_browser':
				if self.params_get('display_mode') == 'search': append((self._remove_bold(furk_add_str), self.furk_add_file))
				else:
					append((self._remove_bold(furk_remove_str), self.furk_remove_file))
					if self.params_get('is_protected') == '0': append((self._remove_bold(furk_p_str), self.furk_protect_file))
					elif self.params_get('is_protected') == '1': append((self.remove_bold(furk_up_str), self.furk_unprotect_file))
		elif mode in ('real_debrid.browse_rd_cloud', 'alldebrid.browse_ad_cloud') or self.params_get('service') == 'FOLDERS':
			append((self._remove_bold(cloud_link_str), self.add_link_to_debrid_folders), (self._remove_bold(cloud_unlink_str), self.remove_link_to_debrid_folders))
		else:
			append((self._remove_bold(eefadde_str), self.add_external))
			append((self._remove_bold(eefadd_str), self.shortcut_folder_add_item))
			if action == 'tmdb_movies_sets': append((self._remove_bold(eesets_str), self.movie_sets_to_collection))
			elif mode == 'trakt.list.build_trakt_list':
				if list_type == 'user_lists':
					if not self.menu_item_get('user') == 'Trakt Official':
						append((self._remove_bold(trlike_str), self.trakt_like_list))
						append((self._remove_bold(trunlike_str), self.trakt_unlike_list))
				elif list_type == 'my_lists':
					append((self._remove_bold(trnew_str), self.trakt_new_list))
					append((self._remove_bold(trdel_str), self.trakt_delete_list))
				elif list_type == 'liked_lists':
					append((self._remove_bold(trunlike_str), self.trakt_unlike_list))
			elif list_type == 'discover_history':
				append((self._remove_bold(eerem_disc_str), self.remove_single_discover_history))
				append((self._remove_bold(eeclear_str), self.remove_all_discover_history))
		append((tools_str, self.open_tools))
		append((settings_str, self.open_settings))
		list_items = [{'line1': i[0]} for i in listing]
		kwargs = {'items': json.dumps(list_items), 'narrow_window': 'true'}
		function = select_dialog([i[1] for i in listing], **kwargs)
		if function == None: return
		return function()

	def browse(self):
		active_list = self.params_get('active_list')
		list_name =  main_list_name_dict[active_list]
		try: choice_items = self._get_removed_items(active_list)
		except: return notification(32760, 1500)
		if not choice_items: return notification(32760, 1500)
		browse_item = self._menu_select(choice_items, list_name)
		if browse_item == None: return
		browse_item = choice_items[browse_item]
		if browse_item.get('mode') == 'build_popular_people': command = 'RunPlugin(%s)'
		else: command = 'Container.Update(%s)'
		execute_builtin(command % build_url(browse_item))

	def move(self):
		active_list = self.params_get('active_list')
		list_items = navigator_cache.currently_used_list(active_list)
		if len(list_items) == 1: return notification(32736, 1500)
		choice_items = [i for i in list_items if str(i['name']) != str(self.params_get('menu_name'))]
		current_position = self.params_get('position')
		new_position = self._menu_select(choice_items, self.params_get('menu_name_translated'), multi_line='true', position_list=True)
		if new_position == None or new_position == current_position: return
		list_items.insert(new_position, list_items.pop(current_position))
		self._db_execute('set', active_list, list_items)

	def remove(self):
		if not confirm_dialog(): return notification(32736, 1500)
		active_list = self.params_get('active_list')
		list_items = navigator_cache.currently_used_list(active_list)
		if len(list_items) == 1: return notification(32736, 1500)
		list_items = [i for i in list_items if str(i['name']) != str(self.params_get('menu_name'))]
		self._db_execute('set', active_list, list_items)

	def add_original(self):
		active_list = self.params_get('active_list')
		try: choice_items = self._get_removed_items(active_list)
		except: return notification(32760, 1500)
		menu_name_translated = self.params_get('menu_name_translated')
		choice = self._menu_select(choice_items, menu_name_translated)
		if choice == None: return notification(32736, 1500)
		choice_list = choice_items[choice]
		list_items = navigator_cache.currently_used_list(active_list)
		position = self._menu_select(list_items, menu_name_translated, multi_line='true', position_list=True)
		if position == None: return notification(32736, 1500)
		list_items.insert(position, choice_list)
		self._db_execute('set', active_list, list_items)

	def add_original_external(self):
		active_list = self.params_get('active_list')
		choice_items = self._get_main_menu_items(active_list)
		choice = self._menu_select([i[1] for i in choice_items], '')
		if choice == None: return notification(32736, 1500)
		menu_name_translated = self.params_get('menu_name_translated')
		choice_name, choice_list = choice_items[choice]
		list_items = navigator_cache.currently_used_list(choice_list['action'])
		menu_name = self._get_external_name_input(menu_name_translated)
		position = self._menu_select(list_items, menu_name or menu_name_translated, multi_line='true', position_list=True)
		if position == None: return notification(32736, 1500)
		list_items.insert(position, self._add_external_info_to_item(self.menu_item, menu_name, False))
		self._db_execute('set', choice_name, list_items, refresh=False)

	def add_trakt(self):
		from apis.trakt_api import get_trakt_list_selection
		trakt_selection = get_trakt_list_selection(list_choice='nav_edit')
		if trakt_selection == None: return notification(32736, 1500)
		active_list = self.params_get('active_list')
		list_items = navigator_cache.currently_used_list(active_list)
		menu_name = self._get_external_name_input(trakt_selection['name'])
		position = self._menu_select(list_items, menu_name or trakt_selection['name'], multi_line='true', position_list=True)
		if position == None: return notification(32736, 1500)
		trakt_selection.update({'iconImage': 'trakt', 'mode': 'trakt.lists.build_trakt_list'})
		list_items.insert(position, self._add_external_info_to_item(trakt_selection, menu_name, False))
		self._db_execute('set', active_list, list_items)

	def restore(self):
		if not confirm_dialog(): return notification(32736, 1500)
		active_list = self.params_get('active_list')
		self._db_execute('delete', active_list, list_type='edited', refresh=False)
		self._db_execute('set', active_list, main_menus[active_list], 'default')

	def reload_menu_item(self):
		active_list = self.params_get('active_list')
		default, edited = navigator_cache.get_main_lists(active_list)
		list_type = 'edited' if edited else 'default'
		current_list = edited or default
		menu_name = self.params_get('menu_name')
		try: new_item = [i for i in default if str(i['name']) == str(menu_name)][0]
		except: return notification(32760, 1500)
		list_items = [i for i in current_list if str(i['name']) != str(menu_name)]
		list_items.insert(self.params_get('position', 0), new_item)
		self._db_execute('set', active_list, list_items, list_type)

	def check_update_list(self):
		active_list = self.params_get('active_list')
		new_contents = main_menus[active_list]
		default, edited = navigator_cache.get_main_lists(active_list)
		list_type = 'edited' if edited else'default'
		current_list = edited or default
		if default == new_contents: return notification(32983, 1500)
		new_entry = [i for i in new_contents if not i in default][0]
		new_entry_translated_name = ls(new_entry.get('name'))
		if not confirm_dialog(text='%s[CR]%s' % (exists_str % new_entry_translated_name, addq_str)): return notification(32736, 1500)
		item_position = self._menu_select(current_list, new_entry_translated_name, position_list=True)
		if item_position == None: return notification(32736, 1500)
		current_list.insert(item_position, new_entry)
		self._db_execute('set', active_list, current_list, list_type)
		if list_type == 'edited': self._db_execute('set', active_list, new_contents, 'default')

	def add_external(self):
		choice_items = self._get_main_menu_items([])
		choice = self._menu_select([i[1] for i in choice_items], '')
		if choice == None: return notification(32736, 1500)
		name = self._fix_name(self.params_get('name'))
		choice_name, choice_list = choice_items[choice]
		list_items = navigator_cache.currently_used_list(choice_list['action'])
		menu_name = self._get_external_name_input(name) or name
		position = self._menu_select(list_items, menu_name, multi_line='true', position_list=True)
		if position == None: return notification(32736, 1500)
		list_items.insert(position, self._add_external_info_to_item(self.menu_item, menu_name))
		self._db_execute('set', choice_name, list_items, refresh=False)

	def shortcut_folder_contents_adjust(self):
		active_list = self.params_get('active_list')
		if self.action == 'clear_all':
			if not confirm_dialog(): return notification(32736, 1500)
			list_items = []
		else:
			list_name = self.menu_item_get('name')
			list_items = navigator_cache.get_shortcut_folder_contents(active_list)
			if self.action == 'add': return self.shortcut_folder_browse_for_content()
			if self.action == 'rename':
				try:
					position = int(self.params_get('position'))
					current_item = list_items[position]
					item_name = current_item['name']
					new_item_name = self._get_external_name_input(item_name)
					if not new_item_name or new_item_name == item_name: return
					current_item['name'] = new_item_name
					list_items[position] == current_item
				except: return
			elif self.action == 'remove':
				if not confirm_dialog(): return notification(32736, 1500)
				list_items = [i for i in list_items if str(i['name']) != str(list_name)]
			elif self.action == 'move':
				if len(list_items) == 1: return notification(32736, 1500)
				choice_items = [i for i in list_items if str(i['name']) != str(list_name)]
				current_position = int(self.params_get('position', '0'))
				new_position = self._menu_select(choice_items, list_name, multi_line='true', position_list=True)
				if new_position == None or new_position == current_position: return
				list_items.insert(new_position, list_items.pop(current_position))
		self._db_execute('set', active_list, list_items, 'shortcut_folder', True)

	def shortcut_folder_make(self):
		list_name = dialog.input('')
		if not list_name: return
		self._db_execute('make_new_folder', list_name, list_type='shortcut_folder')

	def shortcut_folder_add_item(self):
		shortcut_folders = navigator_cache.get_shortcut_folders()
		if len(shortcut_folders) == 1: choice_name, choice_list = shortcut_folders[0]
		elif shortcut_folders:
			choice = self._menu_select([{'name': i[0], 'iconImage': 'folder'} for i in shortcut_folders], '')
			if choice == None: return notification(32736, 1500)
			choice_name, choice_list = shortcut_folders[choice]
		else:
			if not confirm_dialog(text=32702, default_control=10): return notification(32736, 1500)
			self.shortcut_folder_make()
			try: choice_name, choice_list = navigator_cache.get_shortcut_folders()[0]
			except: return notification(32736, 1500)
		list_items = choice_list
		name = self._remove_bold(self.params_get('name') or self.params_get('menu_name_translated'))
		menu_name = self._get_external_name_input(name) or name
		icon_choice = self._icon_select(default_icon=self.params_get('iconImage', None) or self.menu_item_get('iconImage') or 'folder')
		self.menu_item.update({'name': menu_name, 'iconImage': icon_choice})
		if list_items:
			position = self._menu_select(list_items, menu_name, multi_line='true', position_list=True)
			if position == None: return notification(32736, 1500)
		else: position = 0
		list_items.insert(position, self.menu_item)
		self._db_execute('set', choice_name, list_items, 'shortcut_folder', False)

	def shortcut_folder_add_to_main_menu(self):
		shortcut_folders = navigator_cache.get_shortcut_folders()
		if len(shortcut_folders) == 1: name = shortcut_folders[0][0]
		elif shortcut_folders:
			choice = self._menu_select([{'name': i[0], 'iconImage': 'folder'} for i in shortcut_folders], '')
			if choice == None: return notification(32736, 1500)
			name = shortcut_folders[choice][0]
		else:
			if not confirm_dialog(text=32702, default_control=10): return notification(32736, 1500)
			self.shortcut_folder_make()
			try: name = navigator_cache.get_shortcut_folders()[0][0]
			except: return notification(32736, 1500)
		active_list = self.params_get('active_list')
		list_items = navigator_cache.currently_used_list(active_list)
		position = self._menu_select(list_items, self.params_get('menu_name_translated'), multi_line='true', position_list=True)
		if position == None: return notification(32736, 1500)
		icon_choice = self._icon_select(default_icon='folder')
		chosen_folder = {'mode': 'navigator.build_shortcut_folder_list', 'name': name, 'iconImage': icon_choice, 'shortcut_folder': 'True', 'external_list_item': 'True'}
		list_items.insert(position, chosen_folder)
		self._db_execute('set', active_list, list_items)

	def shortcut_folder_delete(self):
		if not confirm_dialog(): return notification(32736, 1500)
		main_menu_items_list = [(i, navigator_cache.currently_used_list(i)) for i in default_menu_items]
		folder_name = self.menu_item_get('name')
		self._db_execute('delete', folder_name, list_type='shortcut_folder')
		self._remove_active_shortcut_folder(main_menu_items_list, folder_name)

	def shortcut_folder_rename(self):
		folder_name = self.menu_item_get('name')
		new_folder_name = self._get_external_name_input(folder_name)
		if not new_folder_name: return
		if new_folder_name == folder_name: return
		list_items = navigator_cache.get_shortcut_folder_contents(folder_name)
		self._db_execute('delete', folder_name, list_type='shortcut_folder')
		self._db_execute('make_new_folder', new_folder_name, list_items)

	def shortcut_folder_browse_for_content(self):
		list_name = self.params_get('list_name')
		choice_name, list_items = list_name, navigator_cache.get_shortcut_folder_contents(list_name)
		browsed_result = self._path_browser()
		if browsed_result == None: return
		self.menu_item = dict(parse_qsl(browsed_result['file'].replace('plugin://plugin.video.fen/?','')))
		name, icon = self._remove_bold(browsed_result['label']), self._get_icon_var(browsed_result['thumbnail'])
		menu_name = self._get_external_name_input(name) or name
		icon_choice = self._icon_select(default_icon=icon)
		self.menu_item.update({'name': menu_name, 'iconImage': icon_choice})
		if list_items:
			position = self._menu_select(list_items, menu_name, multi_line='true', position_list=True)
			if position == None: return notification(32736, 1500)
		else: position = 0
		list_items.insert(position, self.menu_item)
		self._db_execute('set', choice_name, list_items, 'shortcut_folder')

	def trakt_like_list(self):
		from apis.trakt_api import trakt_like_a_list
		params = {'user': self.menu_item_get('user'), 'list_slug': self.menu_item_get('slug')}
		trakt_like_a_list(params)

	def trakt_unlike_list(self):
		from apis.trakt_api import trakt_unlike_a_list
		params = {'user': self.menu_item_get('user'), 'list_slug': self.menu_item_get('slug')}
		trakt_unlike_a_list(params)

	def trakt_new_list(self):
		from apis.trakt_api import make_new_trakt_list
		make_new_trakt_list('dummy')

	def trakt_delete_list(self):
		from apis.trakt_api import delete_trakt_list
		params = {'user': self.menu_item_get('user'), 'list_slug': self.menu_item_get('slug')}
		delete_trakt_list(params)

	def movie_sets_to_collection(self):
		from indexers.dialogs import movie_sets_to_collection_choice
		movie_sets_to_collection_choice({'collection_id': self.menu_item_get('tmdb_id')})

	def remove_search_history(self):
		from modules.history import remove_from_search_history
		params = {'setting_id': self.menu_item_get('setting_id'), 'query': self.menu_item_get('query')}
		remove_from_search_history(params)

	def clear_search_history(self):
		from modules.history import clear_all_history
		clear_all_history(self.menu_item_get('setting_id'), refresh='true')

	def remove_single_discover_history(self):
		from indexers.discover import Discover
		params = {'data_id': self.menu_item_get('data_id'), 'silent': 'false'}
		Discover(params).remove_from_history()

	def remove_all_discover_history(self):
		from indexers.discover import Discover
		Discover(self.menu_item).remove_all_history()

	def furk_add_file(self):
		from indexers.furk import add_to_files
		add_to_files(self.menu_item_get('item_id'))

	def furk_remove_file(self):
		from indexers.furk import remove_from_files
		remove_from_files(self.menu_item_get('item_id'))

	def furk_protect_file(self):
		from indexers.furk import myfiles_protect_unprotect
		myfiles_protect_unprotect('protect', self.menu_item_get('name'), self.menu_item_get('item_id'))

	def furk_unprotect_file(self):
		from indexers.furk import myfiles_protect_unprotect
		myfiles_protect_unprotect('unprotect', self.menu_item_get('name'), self.menu_item_get('item_id'))

	def add_link_to_debrid_folders(self):
		from indexers.dialogs import link_folders_choice
		folder_id = self.menu_item_get('id', None)  or self.params_get('id')
		link_folders_choice({'service': self.params_get('service'), 'folder_id': folder_id, 'action': 'add'})

	def remove_link_to_debrid_folders(self):
		from indexers.dialogs import link_folders_choice
		folder_id = self.menu_item_get('id', None)  or self.params_get('id')
		link_folders_choice({'service': self.params_get('service'), 'folder_id': folder_id, 'action': 'remove'})

	def premium_file_download(self):
		from modules.downloader import runner
		params = {'mode': 'downloader', 'name': self.menu_item_get('name'), 'url': self.menu_item_get('url') or self.menu_item_get('url_dl'),
					'action': self.params_get('action'), 'image': self.params_get('iconImage')}
		runner(params)

	def open_settings(self):
		return open_settings('0.0')

	def open_tools(self):
		return self.window_function({'mode': 'navigator.tools'})

	def _menu_select(self, choice_items, menu_name, heading='', multi_line='false', position_list=False):
		def _builder():
			for item in choice_items:
				item_get = item.get
				line2 = pos_str % (menu_name, ls(item_get('name', None) or item_get('list_name')) if position_list else '')
				iconImage = item_get('iconImage', None)
				if iconImage: icon = iconImage if iconImage.startswith('http') else get_icon(item_get('iconImage'))
				else: icon = get_icon('folder')
				yield {'line1': ls(item_get('name')), 'line2': line2, 'icon':icon}
		list_items = list(_builder())
		if position_list: list_items.insert(0, {'line1': top_str, 'line2': top_pos_str % menu_name, 'icon': get_icon('top')})
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
		kwargs = {'items': json.dumps(list_items), 'heading': choose_icon_str}
		icon_choice = select_dialog(all_icons, **kwargs) or default_icon or 'folder'
		return icon_choice

	def _remove_bold(self, _str):
		return _str.replace('[B]', '').replace('[/B]', '').replace(':', '')

	def _fix_name(self, name):
		name = name.replace('[B]', '').replace('[/B]', '').replace(':', '')
		name = ' '.join(i.lower().title() for i in name.split())
		name = name.replace('  ', ' ').replace('Tv', 'TV')
		return name

	def _get_removed_items(self, active_list):
		default_list_items, list_items = navigator_cache.get_main_lists(active_list)
		return [i for i in default_list_items if not i in list_items]

	def _get_external_name_input(self, current_name):
		new_name = dialog.input('', defaultt=current_name)
		if new_name == current_name: return None
		return new_name

	def _add_external_info_to_item(self, menu_item, menu_name=None, add_all_params=True):
		if add_all_params:
			self.params.pop('mode', None)
			menu_item.update(self.params)
		if menu_name: menu_item['name'] = menu_name
		menu_item['external_list_item'] = 'True'
		icon_choice = self._icon_select(default_icon=menu_item.get('iconImage', 'folder'))
		menu_item['iconImage'] = icon_choice
		return menu_item

	def _get_main_menu_items(self, active_list):
		choice_list = [i for i in default_menu_items if i != active_list]
		return [(i, main_menu_items[i]) for i in choice_list]

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
		elif db_action == 'make_new_folder': navigator_cache.set_list(list_name, 'shortcut_folder', list_contents)
		notification(32576, 1500)
		sleep(200)
		if refresh: kodi_refresh()

	def _path_browser(self, label='', file=default_path, thumbnail=''):
		show_busy_dialog()
		results = get_directory(file)
		hide_busy_dialog()
		list_items, function_items = [], []
		if file != default_path:
			list_items.append({'line1': 'Use [B]%s[/B] As Path' % self._remove_bold(label), 'icon': thumbnail})
			function_items.append(json.dumps({'label': label, 'file': file, 'thumbnail': thumbnail}))
		list_items.extend([{'line1': '%s >>' % i['label'], 'icon': i['thumbnail']} for i in results])
		function_items.extend([json.dumps({'label': i['label'], 'file': i['file'], 'thumbnail': i['thumbnail']}) for i in results])
		kwargs = {'items': json.dumps(list_items)}
		choice = select_dialog(function_items, **kwargs)
		if choice == None: return None
		choice = json.loads(choice)
		if choice['file'] == file: return choice
		else: return self._path_browser(**choice)

	def _get_icon_var(self, icon_path):
		try:
			all_icons = get_all_icon_vars(include_values=True)
			icon_value = unquote(icon_path)
			icon_value = icon_value.replace('image://', '').replace('.png/', '').replace('.png', '')
			icon_value = icon_value.split('/')[-1]
			icon_var = [i[0] for i in all_icons if i[1] == icon_value][0]
		except: icon_var = 'folder'
		return icon_var
