# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

import re
from collections import namedtuple

DomMatch = namedtuple('DOMMatch', ['attrs', 'content'])
re_type = type(re.compile(r''))

def parseDOM(html, name='', attrs=None, ret=False):
	try:
		if attrs:
			attrs = dict((key, re.compile(value + ('$' if value else ''))) for key, value in iter(attrs.items()))
		results = parse_dom(html, name, attrs, ret)
		if ret: results = [result.attrs[ret.lower()] for result in results]
		else: results = [result.content for result in results]
		return results
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def __get_dom_content(html, name, match):
	try:
		if match.endswith('/>'): return ''
		# override tag name with tag from match if possible
		tag = re.match(r'<([^\s/>]+)', match)
		if tag: name = tag.group(1)
		start_str = '<%s' % name
		end_str = "</%s" % name
		# start/end tags without matching case cause issues
		start = html.find(match)
		end = html.find(end_str, start)
		pos = html.find(start_str, start + 1)

		while pos < end and pos != -1:  # Ignore too early </endstr> return
			tend = html.find(end_str, end + len(end_str))
			if tend != -1: end = tend
			pos = html.find(start_str, pos + 1)

		if start == -1 and end == -1: result = ''
		elif start > -1 and end > -1: result = html[start + len(match):end]
		elif end > -1: result = html[:end]
		elif start > -1: result = html[start + len(match):]
		else: result = ''
		return result
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return ''

def __get_dom_elements(item, name, attrs):
	try:
		if not attrs:
			pattern = r'(<%s(?:\s[^>]*>|/?>))' % name
			this_list = re.findall(pattern, item, re.M | re.S | re.I)
		else:
			last_list = None

			for key, value in iter(attrs.items()):
				value_is_regex = isinstance(value, re_type)
				value_is_str = isinstance(value, str)
				pattern = r'''(<{tag}[^>]*\s{key}=(?P<delim>['"])(.*?)(?P=delim)[^>]*>)'''.format(tag=name, key=key)
				re_list = re.findall(pattern, item, re.M | re.S | re.I)
				if value_is_regex:
					this_list = [r[0] for r in re_list if re.match(value, r[2])]
				else:
					temp_value = [value] if value_is_str else value
					this_list = [r[0] for r in re_list if set(temp_value) <= set(r[2].split(' '))]

				if not this_list:
					has_space = (value_is_regex and ' ' in value.pattern) or (value_is_str and ' ' in value)
					if not has_space:
						pattern = r'''(<{tag}[^>]*\s{key}=((?:[^\s>]|/>)*)[^>]*>)'''.format(tag=name, key=key)
						re_list = re.findall(pattern, item, re.M | re.S | re.I)
						if value_is_regex:
							this_list = [r[0] for r in re_list if re.match(value, r[1])]
						else:
							this_list = [r[0] for r in re_list if value == r[1]]

				if last_list is None: last_list = this_list
				else: last_list = [item for item in this_list if item in last_list]
			this_list = last_list
		return this_list
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return this_list

def __get_attribs(element):
	try:
		attribs = {}
		for match in re.finditer(r'''\s+(?P<key>[^=]+)=\s*(?:(?P<delim>["'])(?P<value1>.*?)(?P=delim)|(?P<value2>[^"'][^>\s]*))''', element):
			match = match.groupdict()
			value1 = match.get('value1')
			value2 = match.get('value2')
			value = value1 if value1 is not None else value2
			if value is None: continue
			attribs[match['key'].lower().strip()] = value
		return attribs
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return attribs

def parse_dom(html, name='', attrs=None, req=False, exclude_comments=False):
	try:
		if attrs is None: attrs = {}
		name = name.strip()
		if isinstance(html, str) or isinstance(html, DomMatch): html = [html]
		elif not isinstance(html, list): return ''

		if not name: return ''
		if not isinstance(attrs, dict): return ''

		if req:
			if not isinstance(req, list): req = [req]
			req = set([key.lower() for key in req])

		all_results = []
		for item in html:
			if isinstance(item, DomMatch): item = item.content
			if exclude_comments: item = re.sub(re.compile(r'<!--.*?-->', re.S), '', item)
			results = []
			for element in __get_dom_elements(item, name, attrs):
				attribs = __get_attribs(element)
				if req and not req <= set(attribs.keys()): continue
				temp = __get_dom_content(item, name, element).strip()
				results.append(DomMatch(attribs, temp))
				item = item[item.find(temp, item.find(element)):]
			all_results += results
		return all_results
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return ''