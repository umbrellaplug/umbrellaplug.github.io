# -*- coding: utf-8 -*-
import re
from xml.dom.minidom import parse as mdParse
from modules import kodi_utils
from modules.settings import skin_location, use_skin_fonts, use_custom_skins
from modules.utils import manual_function_import

window_xml_dialog, logger, player, notification, delete_folder = kodi_utils.window_xml_dialog, kodi_utils.logger, kodi_utils.player, kodi_utils.notification, kodi_utils.delete_folder
make_listitem, sleep, open_file, path_exists, confirm_dialog = kodi_utils.make_listitem, kodi_utils.sleep, kodi_utils.open_file, kodi_utils.path_exists, kodi_utils.confirm_dialog
closing_actions, selection_actions, context_actions = kodi_utils.window_xml_closing_actions, kodi_utils.window_xml_selection_actions, kodi_utils.window_xml_context_actions
json, clear_property, run_plugin, Thread, get_visibility = kodi_utils.json, kodi_utils.clear_property, kodi_utils.run_plugin, kodi_utils.Thread, kodi_utils.get_visibility
show_busy_dialog, hide_busy_dialog, addon_enabled, getSkinDir = kodi_utils.show_busy_dialog, kodi_utils.hide_busy_dialog, kodi_utils.addon_enabled, kodi_utils.getSkinDir
up_action, down_action, get_setting = kodi_utils.window_xml_up_action, kodi_utils.window_xml_down_action, kodi_utils.get_setting
build_url, execute_builtin, set_property, get_property = kodi_utils.build_url, kodi_utils.execute_builtin, kodi_utils.set_property, kodi_utils.get_property
translate_path, get_infolabel, list_dirs, current_skin = kodi_utils.translate_path, kodi_utils.get_infolabel, kodi_utils.list_dirs, kodi_utils.current_skin
use_skin_fonts_prop, addon_installed, get_system_setting = kodi_utils.use_skin_fonts_prop, kodi_utils.addon_installed, kodi_utils.jsonrpc_get_system_setting
left_action, right_action, info_action = kodi_utils.window_xml_left_action, kodi_utils.window_xml_right_action, kodi_utils.window_xml_info_action
current_skin_prop, current_font_prop = kodi_utils.current_skin_prop, kodi_utils.current_font_prop
extras_keys, folder_options = ('upper', 'uppercase', 'italic', 'capitalize', 'black', 'mono', 'symbol'), ('xml', '1080', '720', '1080p', '720p', '1080i', '720i', '16x9')
needed_font_values = ((21, False, 'font10'), (26, False, 'font12'), (30, False, 'font13'), (33, False, 'font14'), (38, False, 'font16'), (60, True, 'font60'))
addon_skins_folder = 'special://home/addons/plugin.video.fen/resources/skins/Default/1080i/'
highlight_var_dict = {'skin.arctic.horizon.2': '$VAR[ColorHighlight]'}

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
		args = (skin_xml, skin_location(skin_xml))
		xml_window = function(*args, **kwargs)
		return xml_window
	except Exception as e:
		logger('error in create_window', str(e))
		return notification(32574)

def window_manager(obj):
	def close():
		obj.close()
		clear_property('fen.window_loaded')
		clear_property('fen.window_stack')
	def monitor():
		timer = 0
		while not get_property('fen.window_loaded') == 'true' and timer <= 5:
			sleep(50)
			timer += 0.05
		hide_busy_dialog()
		obj.close()
		clear_property('fen.window_loaded')
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
		try: window_stack = json.loads(get_property('fen.window_stack'))
		except: window_stack = []
		return window_stack
	def add_to_stack(params):
		window_stack.append(params)
		set_property('fen.window_stack', json.dumps(window_stack))
	def remove_from_stack():
		previous_params = window_stack.pop()
		set_property('fen.window_stack', json.dumps(window_stack))
		return previous_params
	show_busy_dialog()
	try:
		clear_property('fen.window_loaded')
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
		while not get_property('fen.window_loaded') == 'true' and timer <= 5:
			sleep(50)
			timer += 0.05
		hide_busy_dialog()
		obj.close()
		clear_property('fen.window_loaded')
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
		clear_property('fen.window_loaded')
		current_params = obj.current_params
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
		self.player = player
		self.closing_actions = closing_actions
		self.selection_actions = selection_actions
		self.context_actions = context_actions
		self.info_action = info_action
		self.left_action = left_action
		self.right_action = right_action
		self.up_action = up_action
		self.down_action = down_action

	def current_skin(self):
		return getSkinDir()

	def highlight_var(self, force=False):
		custom_var = highlight_var_dict.get(self.current_skin(), None)
		if not custom_var: return get_infolabel('Window(10000).Property(fen.main_highlight)')
		if 'Custom' in self.args[1]: var = custom_var
		elif force:
			if use_custom_skins(): var = custom_var
			else: var = 'Window(10000).Property(fen.main_highlight)'
		else: var = 'Window(10000).Property(fen.main_highlight)'
		result = get_infolabel(var)
		return result

	def get_setting(self, setting_id, setting_default=''):
		return get_setting(setting_id, setting_default)

	def make_listitem(self):
		return make_listitem()

	def build_url(self, params):
		return build_url(params)

	def execute_code(self, command):
		return execute_builtin(command)
	
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
		cm_item.setProperty('label', label)
		cm_item.setProperty('action', action % self.build_url(params))
		return cm_item

	def get_infolabel(self, label):
		return get_infolabel(label)

	def get_visibility(self, command):
		return get_visibility(command)
	
	def open_window(self, import_info, skin_xml, **kwargs):
		return open_window(import_info, skin_xml, **kwargs)

	def sleep(self, time):
		sleep(time)

	def path_exists(self, path):
		return path_exists(path)

	def translate_path(self, path):
		return translate_path(path)

	def set_home_property(self, prop, value):
		set_property('fen.%s' % prop, value)

	def get_home_property(self, prop):
		return get_property('fen.%s' % prop)

	def get_attribute(self, obj, attribute):
		return getattr(obj, attribute)

	def set_attribute(self, obj, attribute, value):
		return setattr(obj, attribute, value)

	def get_current_skin(self):
		return current_skin()

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
		if skin_font_xml and self.use_skin_fonts == 'true': self.skin_font_info = self.get_font_info(skin_font_xml) or self.default_font_info()
		else: self.skin_font_info = self.default_font_info()
		for item in needed_font_values: replacement_values_append(self.match_font(*item))
		for item in list_dirs(translate_path(addon_skins_folder))[1]: self.replace_font(item, replacement_values)
		for item in ((current_skin_prop, self.current_skin), (current_font_prop, self.current_font), (use_skin_fonts_prop, self.use_skin_fonts)): set_property(*item)

	def get_skin_folder(self):
		skin_folder = None
		try:
			skin_folder = mdParse(translate_path('special://skin/addon.xml')).getElementsByTagName('extension')[0].getElementsByTagName('res')[0].getAttribute('folder')
			if not skin_folder: skin_folder = [i for i in list_dirs(translate_path('special://skin'))[0] if i in folder_options][0]
		except: pass
		return skin_folder

	def skin_change_check(self):
		self.current_skin, self.current_font, self.use_skin_fonts = current_skin(), get_system_setting('lookandfeel.font', 'Default'), use_skin_fonts()
		if self.current_skin != get_property(current_skin_prop) or self.current_font != get_property(current_font_prop) or self.use_skin_fonts != get_property(use_skin_fonts_prop):
			return True
		return False

	def match_font(self, size, bold, fallback):
		font_tag = 'FEN_%s%s' % (size, '_BOLD' if bold else '')
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
			try: fontset = [i for i in all_fonts if i.getAttribute('id').lower() == 'default'][0]
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