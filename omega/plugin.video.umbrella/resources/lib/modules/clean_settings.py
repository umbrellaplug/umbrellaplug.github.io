# -*- coding: utf-8 -*-
"""
	Umbrella Add-on Modified by Umbrella 1/2/23 to use minidom instead of element tree. we adapt.
"""

#import xml.etree.ElementTree as ET
from resources.lib.modules import control
from xml.dom.minidom import parse as mdParse

def clean_settings():
	def _make_content(dict_object):
		content = '<settings version="2">'
		for item in dict_object:
			if item['id'] in active_settings:
				if 'default' in item and 'value' in item: content += '\n    <setting id="%s" default="%s">%s</setting>' % (item['id'], item['default'], item['value'])
				elif 'default' in item: content += '\n    <setting id="%s" default="%s"></setting>' % (item['id'], item['default'])
				elif 'value' in item: content += '\n    <setting id="%s">%s</setting>' % (item['id'], item['value'])
				else: content += '\n    <setting id="%s"></setting>'
			else: removed_settings.append(item)
		content += '\n</settings>'
		return content


	try:
		removed_settings = []
		active_settings = []
		current_user_settings = []
		addon = control.addon('plugin.video.umbrella')
		addon_name = addon.getAddonInfo('name')
		addon_dir = control.transPath(addon.getAddonInfo('path'))
		profile_dir = control.transPath(addon.getAddonInfo('profile'))
		active_settings_xml = control.joinPath(addon_dir, 'resources', 'settings.xml')
		root = mdParse(active_settings_xml) #minidom instead of element tree
		curSettings = root.getElementsByTagName("setting") #minidom instead of element tree
		#root = ET.parse(active_settings_xml).getroot()
		#for item in root.findall('./section/category/group/setting'):
		for item in curSettings: #minidom instead of element tree
			#setting_id = item.get('id')
			setting_id = item.getAttribute('id') #minidom instead of element tree
			if setting_id:
				active_settings.append(setting_id)
		try:
			settings_xml = control.joinPath(profile_dir, 'settings.xml')
		except:
			if control.setting('debug.level') == '1':
				from resources.lib.modules import log_utils
				log_utils.log('Error Accessing Settings.xml at Startup. Caught error and moving on.')
			return control.notification(title=addon_name, message=32115)
		#root = ET.parse(settings_xml).getroot()
		root = mdParse(settings_xml) #minidom instead of element tree
		root = root.getElementsByTagName("setting") #minidom instead of element tree
		for item in root:
			dict_item = {}
			#setting_id = item.get('id')
			#setting_default = item.get('default')
			#setting_value = item.text
			setting_id = item.getAttribute('id') #minidom instead of element tree
			setting_default = item.getAttribute('default') #minidom instead of element tree
			try:
				setting_value = item.firstChild.data #minidom instead of element tree
			except:
				setting_value = None
			dict_item['id'] = setting_id
			if setting_value:
				dict_item['value'] = setting_value
			if setting_default:
				dict_item['default'] = setting_default
			current_user_settings.append(dict_item)
		new_content = _make_content(current_user_settings)
		nfo_file = control.openFile(settings_xml, 'w')
		nfo_file.write(new_content)
		nfo_file.close()
		control.sleep(200)
		control.notification(title=addon_name, message=control.lang(32084).format(str(len(removed_settings))))
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		control.notification(title=addon_name, message=32115)