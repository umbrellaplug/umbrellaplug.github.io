# -*- coding: utf-8 -*-
import re
import sys
import time
import hashlib
import random
import _strptime
import unicodedata
from html import unescape
from threading import Thread, activeCount
from zipfile import ZipFile
from importlib import import_module, reload as rel_module
from datetime import datetime, timedelta, date
from modules.settings import max_threads
from modules.kodi_utils import translate_path, sleep, show_busy_dialog, hide_busy_dialog, path_exists
# from modules.kodi_utils import logger

def change_image_resolution(image, replace_res):
	return re.sub(r'(w185|w300|w342|w780|w1280|h632|original)', replace_res, image)

def append_module_to_syspath(location):
	sys.path.append(translate_path(location))

def manual_function_import(location, function_name):
	return getattr(import_module(location), function_name)

def reload_module(location):
	return rel_module(manual_module_import(location))

def manual_module_import(location):
	return import_module(location)

def make_thread_list(_target, _list):
	_max_threads = max_threads()
	for item in _list:
		while activeCount() > _max_threads: sleep(1)
		threaded_object = Thread(target=_target, args=(item,))
		threaded_object.start()
		yield threaded_object

def make_thread_list_multi_arg(_target, _list):
	_max_threads = max_threads()
	for item in _list:
		while activeCount() > _max_threads: sleep(1)
		threaded_object = Thread(target=_target, args=item)
		threaded_object.start()
		yield threaded_object

def make_thread_list_enumerate(_target, _list):
	_max_threads = max_threads()
	for count, item in enumerate(_list):
		while activeCount() > _max_threads: sleep(1)
		threaded_object = Thread(target=_target, args=(count, item))
		threaded_object.start()
		yield threaded_object

def chunks(item_list, limit):
	"""
	Yield successive limit-sized chunks from item_list.
	"""
	for i in range(0, len(item_list), limit): yield item_list[i:i + limit]

def string_to_float(string, default_return):
	"""
	Remove all alpha from string and return a float.
	Returns float of "default_return" upon ValueError.
	"""
	try: return float(''.join(c for c in string if (c.isdigit() or c =='.')))
	except ValueError: return float(default_return)

def string_alphanum_to_num(string):
	"""
	Remove all alpha from string and return remaining string.
	Returns original string upon ValueError.
	"""
	try: return ''.join(c for c in string if c.isdigit())
	except ValueError: return string

def jsondate_to_datetime(jsondate_object, resformat, remove_time=False):
	if not jsondate_object: return None
	if remove_time: datetime_object = datetime_workaround(jsondate_object, resformat).date()
	else: datetime_object = datetime_workaround(jsondate_object, resformat)
	return datetime_object

def get_datetime(string=False, dt=False):
	d = datetime.now()
	if dt: return d
	if string: return d.strftime('%Y-%m-%d')
	return datetime.date(d)

def get_current_timestamp():
	return int(time.time())
	
def adjust_premiered_date(orig_date, adjust_hours):
	if not orig_date: return None, None
	orig_date += ' 20:00:00'
	datetime_object = jsondate_to_datetime(orig_date, '%Y-%m-%d %H:%M:%S')
	adjusted_datetime = datetime_object + timedelta(hours=adjust_hours)
	adjusted_string = adjusted_datetime.strftime('%Y-%m-%d')
	return adjusted_datetime.date(), adjusted_string

def make_day(today, date, date_format='%Y-%m-%d', use_words=True):
	if use_words:
		day_diff = (date - today).days
		if day_diff == -1: day = 'YESTERDAY'
		elif day_diff == 0: day = 'TODAY'
		elif day_diff == 1: day = 'TOMORROW'
		elif 1 < day_diff < 7: day = date.strftime('%A').upper()
		else:
			try: day = date.strftime(date_format)
			except ValueError: day = date.strftime('%Y-%m-%d')
	else:
		try: day = date.strftime(date_format)
		except ValueError: day = date.strftime('%Y-%m-%d')
	return day

def subtract_dates(date1, date2):
	return (date1 - date2).days
	return day

def datetime_workaround(data, str_format):
	try: datetime_object = datetime.strptime(data, str_format)
	except: datetime_object = datetime(*(time.strptime(data, str_format)[0:6]))
	return datetime_object

def date_difference(current_date, compare_date, difference_tolerance, allow_postive_difference=False):
	try:
		difference = subtract_dates(current_date, compare_date)
		if not allow_postive_difference and difference > 0: return False
		else: difference = abs(difference)
		if difference > difference_tolerance: return False
		return True
	except: return True

def calculate_age(born, str_format, died=None):
	''' born and died are str objects e.g. '1972-05-28' '''
	born = datetime_workaround(born, str_format)
	if not died: today = date.today()
	else: today = datetime_workaround(died, str_format)
	return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def batch_replace(s, replace_info):
	for r in replace_info:
		s = str(s).replace(r[0], r[1])
	return s

def clean_file_name(s, use_encoding=False, use_blanks=True):
	try:
		hex_entities = [['&#x26;', '&'], ['&#x27;', '\''], ['&#xC6;', 'AE'], ['&#xC7;', 'C'],
					['&#xF4;', 'o'], ['&#xE9;', 'e'], ['&#xEB;', 'e'], ['&#xED;', 'i'],
					['&#xEE;', 'i'], ['&#xA2;', 'c'], ['&#xE2;', 'a'], ['&#xEF;', 'i'],
					['&#xE1;', 'a'], ['&#xE8;', 'e'], ['%2E', '.'], ['&frac12;', '%BD'],
					['&#xBD;', '%BD'], ['&#xB3;', '%B3'], ['&#xB0;', '%B0'], ['&amp;', '&'],
					['&#xB7;', '.'], ['&#xE4;', 'A'], ['\xe2\x80\x99', '']]
		special_encoded = [['"', '%22'], ['*', '%2A'], ['/', '%2F'], [':', ','], ['<', '%3C'],
							['>', '%3E'], ['?', '%3F'], ['\\', '%5C'], ['|', '%7C']]
		
		special_blanks = [['"', ' '], ['/', ' '], [':', ''], ['<', ' '],
							['>', ' '], ['?', ' '], ['\\', ' '], ['|', ' '], ['%BD;', ' '],
							['%B3;', ' '], ['%B0;', ' '], ["'", ""], [' - ', ' '], ['.', ' '],
							['!', ''], [';', ''], [',', '']]
		s = batch_replace(s, hex_entities)
		if use_encoding: s = batch_replace(s, special_encoded)
		if use_blanks: s = batch_replace(s, special_blanks)
		s = s.strip()
	except: pass
	return s

def byteify(data, ignore_dicts=False):
	try:
		if isinstance(data, unicode): return data.encode('utf-8')
		if isinstance(data, list): return [byteify(item, ignore_dicts=True) for item in data]
		if isinstance(data, dict) and not ignore_dicts:
			return dict([(byteify(key, ignore_dicts=True), byteify(value, ignore_dicts=True)) for key, value in data.iteritems()])
	except: pass
	return data

def normalize(txt):
	txt = re.sub(r'[^\x00-\x7f]',r'', txt)
	return txt

def safe_string(obj):
	try:
		try: return str(obj)
		except UnicodeEncodeError: return obj.encode('utf-8', 'ignore').decode('ascii', 'ignore')
		except: return ""
	except: return obj

def remove_accents(obj):
	try:
		try: obj = u'%s' % obj
		except: pass
		obj = ''.join(c for c in unicodedata.normalize('NFD', obj) if unicodedata.category(c) != 'Mn')
	except: pass
	return obj

def regex_from_to(text, from_string, to_string, excluding=True):
	if excluding: r = re.search(r"(?i)" + from_string + r"([\S\s]+?)" + to_string, text).group(1)
	else: r = re.search(r"(?i)(" + from_string + r"[\S\s]+?" + to_string + ")", text).group(1)
	return r

def regex_get_all(text, start_with, end_with):
	r = re.findall(r"(?i)(" + start_with + r"[\S\s]+?" + end_with + ")", text)
	return r

def replace_html_codes(txt):
	txt = re.sub(r"(&#[0-9]+)([^;^0-9]+)", "\\1;\\2", txt)
	txt = unescape(txt)
	txt = txt.replace("<ul>", "\n")
	txt = txt.replace("</ul>", "\n")
	txt = txt.replace("<li>", "\n* ")
	txt = txt.replace("</li>", "")
	txt = txt.replace("<br/><br/>", "\n")
	txt = txt.replace("&quot;", "\"")
	txt = txt.replace("&amp;", "&")
	txt = txt.replace("[spoiler]", "")
	txt = txt.replace("[/spoiler]", "")
	return txt

def gen_file_hash(file):
	try:
		md5_hash = hashlib.md5()
		with open(file, 'rb') as afile:
			buf = afile.read()
			md5_hash.update(buf)
			return md5_hash.hexdigest()
	except: pass

def sec2time(sec, n_msec=3):
	''' Convert seconds to 'D days, HH:MM:SS.FFF' '''
	if hasattr(sec,'__len__'): return [sec2time(s) for s in sec]
	m, s = divmod(sec, 60)
	h, m = divmod(m, 60)
	d, h = divmod(h, 24)
	if n_msec > 0: pattern = '%%02d:%%02d:%%0%d.%df' % (n_msec+3, n_msec)
	else: pattern = '%02d:%02d:%02d'
	if d == 0: return pattern % (h, m, s)
	return ('%d days, ' + pattern) % (d, h, m, s)

def released_key(item):
	if 'released' in item: return item['released'] or '2050-01-01'
	if 'first_aired' in item: return item['first_aired'] or '2050-01-01'
	return '2050-01-01'

def title_key(title):
	try:
		if title is None: title = ''
		articles = ['the', 'a', 'an']
		match = re.match(r'^((\w+)\s+)', title.lower())
		if match and match.group(2) in articles: offset = len(match.group(1))
		else: offset = 0
		return title[offset:]
	except: return title

def sort_for_article(_list, _key):
	_list.sort(key=lambda k: re.sub(r'(^the |^a |^an )', '', k[_key].lower()))
	return _list
	
def sort_list(sort_key, sort_direction, list_data):
	try:
		reverse = sort_direction != 'asc'
		if sort_key == 'rank': return sorted(list_data, key=lambda x: x['rank'], reverse=reverse)
		if sort_key == 'added': return sorted(list_data, key=lambda x: x['listed_at'], reverse=reverse)
		if sort_key == 'title': return sorted(list_data, key=lambda x: title_key(x[x['type']].get('title')), reverse=reverse)
		if sort_key == 'released': return sorted(list_data, key=lambda x: released_key(x[x['type']]), reverse=reverse)
		if sort_key == 'runtime': return sorted(list_data, key=lambda x: x[x['type']].get('runtime', 0), reverse=reverse)
		if sort_key == 'popularity': return sorted(list_data, key=lambda x: x[x['type']].get('votes', 0), reverse=reverse)
		if sort_key == 'percentage': return sorted(list_data, key=lambda x: x[x['type']].get('rating', 0), reverse=reverse)
		if sort_key == 'votes': return sorted(list_data, key=lambda x: x[x['type']].get('votes', 0), reverse=reverse)
		if sort_key == 'random': return sorted(list_data, key=lambda k: random.random())
		return list_data
	except: return list_data

def paginate_list(item_list, page, limit=20, paginate_start=0):
	if paginate_start:
		item_list = item_list[paginate_start:]
		pages = list(chunks(item_list, limit))
		pages.insert(0, [])
	else: pages = list(chunks(item_list, limit))
	result = (pages[page - 1], len(pages))
	return result

def unzip(zip_location, destination_location, destination_check, show_busy=True):
	if show_busy: show_busy_dialog()
	try:
		zipfile = ZipFile(zip_location)
		zipfile.extractall(path=destination_location)
		if path_exists(destination_check): status = True
		else: status = False
	except: status = False
	if show_busy: hide_busy_dialog()
	return status

def copy2clip(txt):
	if sys.platform == "win32":
		try:
			from subprocess import check_call
			cmd = 'echo ' + txt.replace('&', '^&').strip() + '|clip'
			return check_call(cmd, shell=True)
		except: return
	if sys.platform == "darwin":
		try:
			from subprocess import check_call
			cmd = 'echo ' + txt.strip() + '|pbcopy'
			return check_call(cmd, shell=True)
		except: return
	if sys.platform == "linux":
		try:
			from subprocess import Popen, PIPE
			p = Popen(['xsel', '-pi'], stdin=PIPE)
			p.communicate(input=txt)
		except: return