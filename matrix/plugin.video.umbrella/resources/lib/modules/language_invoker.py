# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

import xml.etree.ElementTree as ET
from resources.lib.modules import control


def set_reuselanguageinvoker():
	try:
		addon_xml = control.joinPath(control.addonPath('plugin.video.umbrella'), 'addon.xml')
		tree = ET.parse(addon_xml)
		root = tree.getroot()
		for item in root.iter('reuselanguageinvoker'):
			current_value = str(item.text)
		if current_value:
			new_value = 'true' if current_value == 'false' else 'false'
			if not control.yesnoDialog(control.lang(33018) % (current_value, new_value), '', ''):
				return control.openSettings(query='13.6')
			if new_value == 'true':
				if not control.yesnoDialog(control.lang(33019), '', ''): return
			item.text = new_value
			hash_start = gen_file_hash(addon_xml)
			tree.write(addon_xml)
			hash_end = gen_file_hash(addon_xml)
			if hash_start != hash_end:
				control.setSetting('reuse.languageinvoker', new_value)
				control.okDialog(message='%s\n%s' % (control.lang(33017) % new_value, control.lang(33020)))
			else:
				return control.okDialog(message=33021)
			current_profile = control.infoLabel('system.profilename')
			control.execute('LoadProfile(%s)' % current_profile)
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def gen_file_hash(file):
	try:
		from hashlib import md5
		md5_hash = md5()
		with open(file, 'rb') as afile:
			buf = afile.read()
			md5_hash.update(buf)
			return md5_hash.hexdigest()
	except:
		from resources.lib.modules import log_utils
		log_utils.error()