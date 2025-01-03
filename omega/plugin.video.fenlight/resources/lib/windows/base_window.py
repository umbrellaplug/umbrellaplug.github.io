# -*- coding: utf-8 -*-
import re
import json
from threading import Thread
from xml.dom.minidom import parse as mdParse
from modules import kodi_utils
from caches.settings_cache import get_setting, set_setting, restore_setting_default
from modules.utils import manual_function_import

window_xml_dialog, logger, xbmc_player, notification = kodi_utils.window_xml_dialog, kodi_utils.logger, kodi_utils.xbmc_player, kodi_utils.notification
make_listitem, sleep, open_file, path_exists, confirm_dialog = kodi_utils.make_listitem, kodi_utils.sleep, kodi_utils.open_file, kodi_utils.path_exists, kodi_utils.confirm_dialog
addon_installed, addon_path, delete_folder = kodi_utils.addon_installed, kodi_utils.addon_path, kodi_utils.delete_folder
clear_property, run_plugin, get_visibility = kodi_utils.clear_property, kodi_utils.run_plugin, kodi_utils.get_visibility
show_busy_dialog, hide_busy_dialog, addon_enabled, getSkinDir = kodi_utils.show_busy_dialog, kodi_utils.hide_busy_dialog, kodi_utils.addon_enabled, kodi_utils.getSkinDir
build_url, execute_builtin, set_property, get_property = kodi_utils.build_url, kodi_utils.execute_builtin, kodi_utils.set_property, kodi_utils.get_property
translate_path, get_infolabel, list_dirs, current_skin = kodi_utils.translate_path, kodi_utils.get_infolabel, kodi_utils.list_dirs, kodi_utils.current_skin
get_system_setting, select_dialog, ok_dialog = kodi_utils.jsonrpc_get_system_setting, kodi_utils.select_dialog, kodi_utils.ok_dialog
extras_keys, folder_options = ('upper', 'uppercase', 'italic', 'capitalize', 'black', 'mono', 'symbol'), ('xml', '1080', '720', '1080p', '720p', '1080i', '720i', '16x9')
needed_font_values = ((21, False, 'font10'), (26, False, 'font12'), (30, False, 'font13'), (33, False, 'font14'), (38, False, 'font16'), (60, True, 'font60'))
current_skin_prop, current_font_prop = 'fenlight.current_skin', 'fenlight.current_font'
addon_skins_folder = 'special://home/addons/plugin.video.fenlight/resources/skins/Default/1080i/'

def open_window(import_info, skin_xml, **kwargs):
	'''
	import_info: ('module', 'function')
	'''
	try:
		xml_window = create_window(import_info, skin_xml, **kwargs)
		choice = xml_window.run()
		del xml_window
		return choice
	except Exception as e:
		logger('error in open_window', str(e))

def create_window(import_info, skin_xml, **kwargs):
	'''
	import_info: ('module', 'function')
	'''
	try:
		function = manual_function_import(*import_info)
		args = (skin_xml, addon_path())
		xml_window = function(*args, **kwargs)
		return xml_window
	except Exception as e:
		logger('error in create_window', str(e))
		return notification('Error')

def window_manager(obj):
	def close():
		obj.close()
		clear_property('fenlight.window_loaded')
		clear_property('fenlight.window_stack')

	def monitor():
		timer = 0
		while not get_property('fenlight.window_loaded') == 'true' and timer <= 5:
			sleep(50)
			timer += 0.05
		hide_busy_dialog()
		obj.close()
		clear_property('fenlight.window_loaded')

	def runner(params):
		try:
			mode = params['mode']
			if mode == 'extras_menu_choice':
				from indexers.dialogs import extras_menu_choice
				extras_menu_choice(params)
			elif mode == 'person_data_dialog':
				from indexers.people import person_data_dialog
				person_data_dialog(params)
			else: close()
		except: close()

	def get_stack():
		try: window_stack = json.loads(get_property('fenlight.window_stack'))
		except: window_stack = []
		return window_stack

	def add_to_stack(params):
		window_stack.append(params)
		set_property('fenlight.window_stack', json.dumps(window_stack))

	def remove_from_stack():
		previous_params = window_stack.pop()
		set_property('fenlight.window_stack', json.dumps(window_stack))
		return previous_params
	show_busy_dialog()
	try:
		clear_property('fenlight.window_loaded')
		current_params = obj.current_params
		new_params = obj.new_params
		window_stack = get_stack()
		if current_params: add_to_stack(current_params)
		if new_params:
			Thread(target=monitor).start()
			runner(new_params)
		elif window_stack:
			previous_params = remove_from_stack()
			if previous_params:
				Thread(target=monitor).start()
				runner(previous_params)
		else: close()
	except: close()
	hide_busy_dialog()

def window_player(obj):
	def monitor():
		timer = 0
		while not get_property('fenlight.window_loaded') == 'true' and timer <= 5:
			sleep(50)
			timer += 0.05
		hide_busy_dialog()
		obj.close()
		clear_property('fenlight.window_loaded')

	def runner(params):
		try:
			mode = params['mode']
			if mode == 'extras_menu_choice':
				from indexers.dialogs import extras_menu_choice
				extras_menu_choice(params)
			else:
				from indexers.people import person_data_dialog
				person_data_dialog(params)
		except: close()
	try:
		window_player_url = obj.window_player_url
		if 'plugin.video.youtube' in window_player_url:
			if not addon_installed('plugin.video.youtube') or not addon_enabled('plugin.video.youtube'): return
		clear_property('fenlight.window_loaded')
		current_params = obj.current_params
		player = xbmc_player()
		player.play(window_player_url)
		sleep(2000)
		while not player.isPlayingVideo(): sleep(100)
		obj.close()
		while player.isPlayingVideo(): sleep(100)
		show_busy_dialog()
		sleep(1000)
		Thread(target=monitor).start()
		runner(current_params)
	except: obj.close()
	hide_busy_dialog()

class BaseDialog(window_xml_dialog):
	def __init__(self, *args):
		window_xml_dialog.__init__(self, args)
		self.args = args
		self.player = xbmc_player()
		self.left_action = 1
		self.right_action = 2
		self.up_action = 3
		self.down_action = 4
		self.info_action = 11
		self.selection_actions = (7, 100)
		self.closing_actions = (9, 10, 13, 92)
		self.context_actions = (101, 108, 117)

	def current_skin(self):
		return current_skin()

	def get_setting(self, setting_id, setting_default=''):
		return get_setting(setting_id, setting_default)

	def set_setting(self, setting_id, value):
		set_setting(setting_id, value)

	def restore_setting_default(self, params):
		restore_setting_default(params)

	def make_listitem(self):
		return make_listitem()

	def build_url(self, params):
		return build_url(params)

	def execute_code(self, command, block=False):
		return execute_builtin(command, block)
	
	def get_position(self, window_id):
		return self.get_control(window_id).getSelectedPosition()

	def get_listitem(self, window_id):
		return self.get_control(window_id).getSelectedItem()

	def add_items(self, _control, _items):
		self.get_control(_control).addItems(_items)

	def select_item(self, _control, _item):
		self.get_control(_control).selectItem(_item)

	def set_image(self, _control, _image):
		self.get_control(_control).setImage(_image)

	def set_label(self, _control, _label):
		self.get_control(_control).setLabel(_label)

	def set_text(self, _control, _text):
		self.get_control(_control).setText(_text)

	def set_percent(self, _control, _percent):
		self.get_control(_control).setPercent(_percent)

	def reset_window(self, _control):
		self.get_control(_control).reset()

	def get_control(self, control_id):
		return self.getControl(control_id)

	def make_contextmenu_item(self, label, action, params):
		cm_item = self.make_listitem()
		cm_item.set_properties({'label': label, 'action': action % self.build_url(params)})
		return cm_item

	def get_infolabel(self, label):
		return get_infolabel(label)

	def get_visibility(self, command):
		return get_visibility(command)
	
	def open_window(self, import_info, skin_xml, **kwargs):
		return open_window(import_info, skin_xml, **kwargs)

	def run_addon(self, command, block=False):
		run_plugin(command, block)

	def sleep(self, time):
		sleep(time)

	def path_exists(self, path):
		return path_exists(path)

	def translate_path(self, path):
		return translate_path(path)

	def set_home_property(self, prop, value):
		set_property('fenlight.%s' % prop, value)

	def get_home_property(self, prop):
		return get_property('fenlight.%s' % prop)

	def clear_home_property(self, prop):
		return clear_property('fenlight.%s' % prop)

	def get_attribute(self, obj, attribute):
		return getattr(obj, attribute)

	def set_attribute(self, obj, attribute, value):
		return setattr(obj, attribute, value)

	def clear_modals(self):
		try: del self.player
		except: pass

	def notification(self, text, duration=3000):
		return notification(text, duration)

	def addon_installed(self, addon_id):
		return addon_installed(addon_id)

	def addon_enabled(self, addon_id):
		return addon_enabled(addon_id)

class FontUtils:
	def execute_custom_fonts(self):
		if not self.skin_change_check(): return
		replacement_values, skin_font_xml = [], ''
		replacement_values_append = replacement_values.append
		skin_folder = self.get_skin_folder()
		if skin_folder: skin_font_xml = translate_path('special://skin/%s/Font.xml' % skin_folder)
		if skin_font_xml: self.skin_font_info = self.get_font_info(skin_font_xml) or self.default_font_info()
		else: self.skin_font_info = self.default_font_info()
		for item in needed_font_values: replacement_values_append(self.match_font(*item))
		for item in list_dirs(translate_path(addon_skins_folder))[1]: self.replace_font(item, replacement_values)
		set_property(current_skin_prop, self.current_skin)
		set_property(current_font_prop, self.current_font)

	def get_skin_folder(self):
		skin_folder = None
		try:
			skin_folder = mdParse(translate_path('special://skin/addon.xml')).getElementsByTagName('extension')[0].getElementsByTagName('res')[0].getAttribute('folder')
			if not skin_folder: skin_folder = [i for i in list_dirs(translate_path('special://skin'))[0] if i in folder_options][0]
		except: pass
		return skin_folder

	def skin_change_check(self):
		self.current_skin, self.current_font = current_skin(), get_system_setting('lookandfeel.font', 'Default')
		if self.current_skin != get_property(current_skin_prop) or self.current_font != get_property(current_font_prop): return True
		return False

	def match_font(self, size, bold, fallback):
		font_tag = 'FENLIGHT_%s%s' % (size, '_BOLD' if bold else '')
		size_range = range(int(size * 0.75), int(size * 1.25))
		compatibility_range = range(int(size * 0.50), int(size * 1.50))
		compatibility_fonts = [i['name'] for i in self.skin_font_info if i['name'] == fallback and i['size'] in compatibility_range]
		if compatibility_fonts: return (font_tag, compatibility_fonts[0])
		sized_fonts = [i for i in self.skin_font_info if i['size'] in size_range]
		if not sized_fonts: return fallback
		fonts = [i for i in sized_fonts if i['bold'] == bold and not i['extra_styles']] or [i for i in sized_fonts if i['bold'] == bold] \
				or [i for i in sized_fonts if not i['extra_styles']] or sized_fonts
		return (font_tag, [i['name'] for i in fonts if i['size'] == min([i['size'] for i in fonts], key=lambda k: abs(k-size))][0])

	def get_font_info(self, skin_font_xml):
		results = []
		if not skin_font_xml: return results
		results_append = results.append
		try:
			all_fonts = mdParse(skin_font_xml).getElementsByTagName('fontset')
			try: fontset = [i for i in all_fonts if i.getAttribute('id').lower() == self.current_font.lower()][0]
			except: fontset = all_fonts[0]
			for item in fontset.getElementsByTagName('font'):
				try: name = item.getElementsByTagName('name')[0].firstChild.data
				except: continue
				try: size = int(item.getElementsByTagName('size')[0].firstChild.data)
				except: continue
				try: style = item.getElementsByTagName('style')[0].firstChild.data.lower()
				except: style = ''
				name_compare = name.lower()
				bold = any('bold' in item for item in (name_compare, style))
				extra_styles = any(item in style for item in extras_keys)
				if not extra_styles: extra_styles = any(item in name_compare for item in extras_keys)
				results_append({'name': name, 'size': size, 'bold': bold, 'extra_styles': extra_styles})
		except: pass
		return results

	def replace_font(self, window, replacement_values):
		file = translate_path(addon_skins_folder + window)
		with open_file(file) as f: content = f.read()
		for item in replacement_values:
			try: content = re.sub(r'<font>(.*?)</font> <\!-- %s -->' % item[0], '<font>%s</font> <!-- %s -->' % (item[1], item[0]), content)
			except: pass
		with open_file(file, 'w') as f: f.write(content)

	def default_font_info(self):
		return [{'name': 'font10', 'size': 21, 'bold': False, 'extra_styles': False},
				{'name': 'font12', 'size': 26, 'bold': False, 'extra_styles': False},
				{'name': 'font13', 'size': 30, 'bold': False, 'extra_styles': False},
				{'name': 'font14', 'size': 33, 'bold': False, 'extra_styles': False},
				{'name': 'font16', 'size': 38, 'bold': False, 'extra_styles': False},
				{'name': 'font45', 'size': 45, 'bold': False, 'extra_styles': False},
				{'name': 'font60', 'size': 60, 'bold': False, 'extra_styles': False}]
