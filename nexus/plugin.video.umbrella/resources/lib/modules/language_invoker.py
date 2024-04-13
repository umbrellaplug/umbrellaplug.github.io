# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

#import xml.etree.ElementTree as ET
from resources.lib.modules import control
from xml.dom.minidom import parse as mdParse

def set_reuselanguageinvoker(fromSettings=False):
	try:
		addon_xml = control.joinPath(control.addonPath('plugin.video.umbrella'), 'addon.xml')
		#tree = ET.parse(addon_xml)
		#root = tree.getroot()
		try:
			tree = mdParse(addon_xml)
			reuse = tree.getElementsByTagName("reuselanguageinvoker")[0]
			current_value = reuse.firstChild.data
		except:
			from resources.lib.modules import log_utils
			return log_utils.log('Unable to set language invoker. cannot find current value.', level=log_utils.LOGDEBUG)
		if current_value:
			new_value = 'true' if current_value == 'false' else 'false'
			if not control.yesnoDialog(control.lang(33018) % (current_value, new_value), '', ''):
				if fromSettings == 'True':
					return control.openSettings(query='0.3')
				else: return
			if new_value == 'true':
				if not control.yesnoDialog(control.lang(33019), '', ''): return
			tree.getElementsByTagName("reuselanguageinvoker")[0].firstChild.data = new_value
			hash_start = gen_file_hash(addon_xml)
			newxml = str(tree.toxml())[22:] #for some reason to xml adds this so we remove it."<?xml version="1.0" ?>"
			with open(addon_xml, "w") as f:
				f.write(newxml)
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