# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

#import xml.etree.ElementTree as ET
from resources.lib.modules.control import transPath, existsPath
from xml.dom.minidom import parse as mdParse

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
	#tree = ET.parse(xml_file)
	#root = tree.getroot()
	#sources = root.find(type)
	tree = mdParse(xml_file)
	sources = tree.getElementsByTagName(type)[0].getElementsByTagName('source')
	existing_source = None
	for count, source in enumerate(sources):
		xml_name = sources[count].childNodes[0].childNodes[0].data
		xml_path = sources[count].childNodes[1].childNodes[0].data
		try:
			thumbnail = sources[count].childNodes[2].childNodes[0].data
		except:
			thumbnail = None
		if thumbnail is not None:
			xml_thumbnail = thumbnail
		else:
			xml_thumbnail = ''
		if xml_name == name or xml_path == path:
			existing_source = source
			break
	if existing_source is not None:
		xml_name = sources[count].childNodes[0].childNodes[0].data
		xml_path = sources[count].childNodes[1].childNodes[0].data
		try:
			thumbnail = sources[count].childNodes[2].childNodes[0].data
		except:
			thumbnail = None
		if thumbnail is not None:
			xml_thumbnail = thumbnail
		else:
			xml_thumbnail = ''
		if xml_name == name and xml_path == path and xml_thumbnail == thumbnail:
			return False
		elif xml_name == name:
			sources[count].childNodes[1].childNodes[0].data = path
			sources[count].childNodes[2].childNodes[0].data = thumbnail
		elif xml_path == path:
			sources[count].childNodes[0].childNodes[0].data = name
			sources[count].childNodes[2].childNodes[0].data = thumbnail
		else:
			sources[count].childNodes[1].childNodes[0].data = path
			sources[count].childNodes[0].childNodes[0].data = name
	else:
		#new_source = ET.SubElement(sources, 'source')
		videosourcesec = tree.getElementsByTagName(type)[0]
		new_source = tree.createElement("source")
		new_name = tree.createElement("name")
		new_name_text = tree.createTextNode(name)
		new_name.appendChild(new_name_text)
		new_source.appendChild(new_name)
		new_path = tree.createElement("path")
		new_path.setAttribute("pathversion", "1")
		new_path_text = tree.createTextNode(path)
		new_path.appendChild(new_path_text)
		new_source.appendChild(new_path)
		new_thumbnail = tree.createElement("thumbnail")
		new_thumbnail.setAttribute("pathversion", "1")
		new_thumnail_text = tree.createTextNode(thumbnail)
		new_thumbnail.appendChild(new_thumnail_text)
		new_source.appendChild(new_thumbnail)
		new_allowsharing = tree.createElement("allowsharing")
		new_allowsharing_text = tree.createTextNode('true')
		new_allowsharing.appendChild(new_allowsharing_text)
		new_source.appendChild(new_allowsharing)
		videosourcesec.appendChild(new_source)
		#xmlFile.childNodes[0].appendChild( newScript )
		#new_name = ET.SubElement(new_source, 'name')
		#new_name.text = name
		#new_path = ET.SubElement(new_source, 'path')
		#new_thumbnail = ET.SubElement(new_source, 'thumbnail')
		#new_allowsharing = ET.SubElement(new_source, 'allowsharing')
		#new_path.attrib['pathversion'] = '1'
		#new_thumbnail.attrib['pathversion'] = '1'
		#new_path.text = path
		#new_thumbnail.text = thumbnail
		#new_allowsharing.text = 'true'
	#_indent_xml(tree)
	#tree.write(xml_file)
	newxml = str(tree.toxml())[22:]
	with open(xml_file, "w") as f:
		f.write(newxml)
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
	#tree = ET.parse(xml_file)
	#root = tree.getroot()
	#sources = root.find(type)
	tree = mdParse(xml_file)
	sources = tree.getElementsByTagName(type)[0].getElementsByTagName('source')
	for count, source in enumerate(sources):
		#xml_name = source.find('name').text
		xml_name = sources[count].childNodes[0].childNodes[0].data
		if xml_name == name:
			#return source.find(attr).text
			if attr == 'path':
				return sources[count].childNodes[1].childNodes[0].data
			elif attr == 'thumbnail':
				return sources[count].childNodes[2].childNodes[0].data
			elif attr == 'allowsharing':
				return 'true'
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