# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

import xml.etree.ElementTree as ET
from resources.lib.modules.control import transPath, existsPath


def add_source(source_name, source_path, source_content, source_thumbnail, type='video'):
	xml_file = transPath('special://profile/sources.xml')
	if not existsPath(xml_file):
		with open(xml_file, 'w') as f:
			f.write(
'''
<sources>
	<programs>
		<default pathversion="1"/>
	</programs>
	<video>
		<default pathversion="1"/>
	</video>
	<music>
		<default pathversion="1"/>
	</music>
	<pictures>
		<default pathversion="1"/>
	</pictures>
	<files>
		<default pathversion="1"/>
	</files>
	<games>
		<default pathversion="1"/>
	</games>
</sources>
''')
	existing_source = _get_source_attr(xml_file, source_name, 'path', type=type)
	if existing_source and existing_source != source_path and source_content != '':
		_remove_source_content(existing_source)
	if _add_source_xml(xml_file, source_name, source_path, source_thumbnail, type=type) and source_content != '':
		_remove_source_content(source_path) # Added to also rid any remains because manual delete sources and kodi leaves behind a record in MyVideos*.db
		_set_source_content(source_content)

def _add_source_xml(xml_file, name, path, thumbnail, type='video'):
	tree = ET.parse(xml_file)
	root = tree.getroot()
	sources = root.find(type)
	existing_source = None
	for source in sources.findall('source'):
		xml_name = source.find('name').text
		xml_path = source.find('path').text
		if source.find('thumbnail') is not None:
			xml_thumbnail = source.find('thumbnail').text
		else:
			xml_thumbnail = ''
		if xml_name == name or xml_path == path:
			existing_source = source
			break
	if existing_source is not None:
		xml_name = source.find('name').text
		xml_path = source.find('path').text
		if source.find('thumbnail') is not None:
			xml_thumbnail = source.find('thumbnail').text
		else:
			xml_thumbnail = ''
		if xml_name == name and xml_path == path and xml_thumbnail == thumbnail:
			return False
		elif xml_name == name:
			source.find('path').text = path
			source.find('thumbnail').text = thumbnail
		elif xml_path == path:
			source.find('name').text = name
			source.find('thumbnail').text = thumbnail
		else:
			source.find('path').text = path
			source.find('name').text = name
	else:
		new_source = ET.SubElement(sources, 'source')
		new_name = ET.SubElement(new_source, 'name')
		new_name.text = name
		new_path = ET.SubElement(new_source, 'path')
		new_thumbnail = ET.SubElement(new_source, 'thumbnail')
		new_allowsharing = ET.SubElement(new_source, 'allowsharing')
		new_path.attrib['pathversion'] = '1'
		new_thumbnail.attrib['pathversion'] = '1'
		new_path.text = path
		new_thumbnail.text = thumbnail
		new_allowsharing.text = 'true'
	_indent_xml(root)
	tree.write(xml_file)
	return True

def _indent_xml(elem, level=0):
	i = '\n' + level*'\t'
	if len(elem):
		if not elem.text or not elem.text.strip():
			elem.text = i + '\t'
		if not elem.tail or not elem.tail.strip():
			elem.tail = i
		for elem in elem:
			_indent_xml(elem, level+1)
		if not elem.tail or not elem.tail.strip():
			elem.tail = i
	else:
		if level and (not elem.tail or not elem.tail.strip()):
			elem.tail = i

def _get_source_attr(xml_file, name, attr, type='video'):
	tree = ET.parse(xml_file)
	root = tree.getroot()
	sources = root.find(type)
	for source in sources.findall('source'):
		xml_name = source.find('name').text
		if xml_name == name:
			return source.find(attr).text
	return None

def _db_execute(db_name, command):
	databaseFile = _get_database(db_name)
	if not databaseFile: return False
	from sqlite3 import dbapi2
	dbcon = dbapi2.connect(databaseFile)
	dbcur = dbcon.cursor()
	dbcur.execute(command)
	dbcon.commit()
	dbcur.close ; dbcon.close()
	return True

def _get_database(db_name):
	from glob import glob
	path_db = 'special://profile/Database/%s' % db_name
	filelist = glob(transPath(path_db))
	if filelist: return filelist[-1]
	return None

def _remove_source_content(path):
	q = 'DELETE FROM path WHERE strPath LIKE "%{0}%"'.format(path)
	return _db_execute('MyVideos*.db', q)

def _set_source_content(content):
	q = 'INSERT OR REPLACE INTO path (strPath,strContent,strScraper,strHash,scanRecursive,useFolderNames,strSettings,noUpdate,exclude,dateAdded,idParentPath) VALUES '
	q += content
	return _db_execute('MyVideos*.db', q)