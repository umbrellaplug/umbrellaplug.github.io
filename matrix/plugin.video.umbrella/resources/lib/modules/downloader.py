# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

import os
import re
import ssl
from urllib.parse import parse_qsl, urlparse, unquote
from urllib.request import urlopen, Request
from resources.lib.modules import control
from resources.lib.modules import log_utils
homeWindow = control.homeWindow
ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
levels =['../../../..', '../../..', '../..', '..']
video_extensions = ('.3gp', '.avi', '.divx', '.flv', '.m4v', '.mp4', '.mpeg', '.mpg', '.m2ts', '.mov', '.mkv', '.wmv', '.webm', '.xvid')


def download(name, image, url, meta_name=None, pack=None): # needs re-write, pack file support
	if control.setting('debug.level') == '1':
		log_utils.log('name: %s' % name, __name__)
		log_utils.log('image: %s' % image, __name__)
		log_utils.log('url: %s' % url, __name__)
		log_utils.log('meta_name: %s' % meta_name, __name__)
		log_utils.log('pack: %s' % pack, __name__)


	#test = url.rsplit('/', 1)[1].split('|')[0]
	#log_utils.log('test: %s' % str(test), __name__)
	#test = unquote(test).replace(" ","")
	#log_utils.log('test2: %s' % str(test), __name__)

	if not url: return control.hide()
	try:
		file_format = control.setting('downloads.file.format')
		try: headers = dict(parse_qsl(url.rsplit('|', 1)[1]))
		except: headers = dict('')
		url = url.split('|')[0]
		try:
			name = name.replace(':','')
		except:
			pass
		try: transname = name.translate((None, '\/:*?"<>|')).strip('.').replace(':', '')
		except: transname = name.translate(name.maketrans('', '', '\/:*?"<>|')).strip('.').replace(':', '')  # maketrans() is in string module for py2
		# for i in video_extensions: transname = transname.rstrip(i)
		# if pack == 'season':
		if pack in ('season', 'show'):
			# content = url.rsplit('/', 1)[1].split('|')[0]
			content = unquote(url.rsplit('/', 1)[1].split('|')[0])
			if control.setting('debug.level') == '1':
				log_utils.log('content: %s' % str(content), __name__)
			try: content = re.search(r'(.+?)(?:|\.| - |-|.-.|\s)(?:S|s|\s|\.)(\d{1,2})(?!\d)(?:|\.| - |-|.-.|x|\s)(?:E|e|\s|.)([0-2]{1}[0-9]{1})(?!\w)', content, re.I).groups()
			except:
				content = ()
				if meta_name:
					try: content = re.search(r'(.+?)\sS(\d*)E\d*$', meta_name, re.I).groups()
					except: 
						content = ()
						if file_format == '0':
							try:
								transname = meta_name.translate((None, '\/:*?"<>|')).strip('.').replace(':', '')
							except:
								transname = meta_name.translate(meta_name.maketrans('', '', '\/:*?"<>|')).strip('.').replace(':', '')
			if control.setting('debug.level') == '1':
				log_utils.log('content: %s' % str(content), __name__)
			# transname = url.rsplit('/', 1)[1].split('|')[0]
			transname = unquote(url.rsplit('/', 1)[1].split('|')[0])


		elif meta_name:
			try: content = re.search(r'(.+?)\sS(\d*)E(\d*)$', meta_name, re.I).groups()
			except: content = ()
			if file_format == '0':
				try:
					transname = meta_name.translate((None, '\/:*?"<>|')).strip('.').replace(':', '')
				except: transname = meta_name.translate(meta_name.maketrans('', '', '\/:*?"<>|')).strip('.').replace(':', '')
		else:
			try: content = re.search(r'(.+?)(?:|\.| - |-|.-.|\s)(?:S|s|\s|\.)(\d{1,2})(?!\d)(?:|\.| - |-|.-.|x|\s)(?:E|e|\s|.)([0-2]{1}[0-9]{1})(?!\w)', name.replace('\'', ''), re.I).groups()
			except: content = ()
		if control.setting('debug.level') == '1':
			log_utils.log('content: %s' % str(content), __name__)

		for i in video_extensions: transname = transname.replace(i, "")
		transname = transname.replace(':','')


		if len(content) == 0:
			dest = control.transPath(control.setting('movie.download.path'))
			if not dest: dest = 'special://profile/addon_data/plugin.video.umbrella/Movies/'
			for level in levels:
				try: control.makeFile(os.path.abspath(os.path.join(dest, level)))
				except: pass
			control.makeFile(dest)
			if meta_name:
				try:
					meta_trans = meta_name.translate((None, '\/:*?"<>|')).strip('.').replace(':', '')
					dest = os.path.join(dest, meta_trans)
				except:
					dest = os.path.join(dest, meta_name.translate(meta_name.maketrans('', '', '\/:*?"<>|')).strip('.').replace(':', ''))
			else:
				try: movie_info = re.search(r'(.+?)(?:\.{0,1}-{0,1}\.{0,1}|\s*)(?:|\(|\[|\.)((?:19|20)(?:[0-9]{2}))', name.replace('\'', '')).groups()
				except: movie_info = ()
				if len(movie_info) != 0:
					movietitle = titlecase(re.sub(r'[^A-Za-z0-9\s]+', ' ', movie_info[0]))
					dest = os.path.join(dest, movietitle + ' (' + movie_info[1] + ')')
					if file_format == '0':
						transname = movietitle + ' (' + movie_info[1] + ')'
					# else:
					# 	try:
					# 		s = re.sub(r'^[\w,\s-]+\.[A-Za-z]{3}$)','', transname)
					# 	except:
					# 		s = None
					# 	if not s:
					# 		return control.notification(title=control.lang(33586), message=control.lang(40250), icon=image, time=3000)
				else:
					dest = os.path.join(dest, transname)
			control.makeFile(dest)
		else:
			dest = control.transPath(control.setting('tv.download.path'))
			if not dest: dest = 'special://profile/addon_data/plugin.video.umbrella/TVShows/'
			for level in levels:
				try: control.makeFile(os.path.abspath(os.path.join(dest, level)))
				except:
					log_utils.error()
					pass
			control.makeFile(dest)
			try: transtvshowtitle = content[0].translate((None, '\/:*?"<>|')).strip('.').replace('.', ' ').replace(':', '')
			except: transtvshowtitle = content[0].translate(content[0].maketrans('', '', '\/:*?"<>|')).strip('.').replace('.', ' ').replace(':', '')
			if not meta_name:
				transtvshowtitle = titlecase(re.sub(r'[^A-Za-z0-9\s-]+', ' ', transtvshowtitle))
			dest = os.path.join(dest, transtvshowtitle)

			if control.setting('debug.level') == '1':
				log_utils.log('dest: %s' % dest, __name__)

			control.makeFile(dest)
			dest = os.path.join(dest, 'Season %01d' % int(content[1]))
			control.makeFile(dest)
			if file_format == '0' and not meta_name:
				transname = transtvshowtitle + ' S%sE%s' % (content[1], content[2])
			# else:
			# 	try:
			# 		s = re.sub(r'^[\w,\s-]+\.[A-Za-z]{3}$)','', transname)
			# 	except:
			# 		s = None
			# 	if not s:
			# 		return control.notification(title=control.lang(33586), message=control.lang(40250), icon=image, time=3000)
		ext = os.path.splitext(urlparse(url).path)[1][1:]

		if control.setting('debug.level') == '1':
			log_utils.log('ext: %s' % ext, __name__)

		if not ext in ('3gp', 'divx', 'xvid', 'm4v', 'mp4', 'mpeg', 'mpg', 'm2ts', 'mov', 'mkv', 'flv', 'avi', 'wmv', 'webm'): ext = 'mp4'
		dest = os.path.join(dest, transname + '.' + ext)
		# doDownload(url, dest, name, image, headers)
		doDownload(url, dest, transname + '.' + ext, image, headers)
	except: log_utils.error('url: %s' % url)

def getResponse(url, headers, size):
	try:
		if size > 0:
			size = int(size)
			headers['Range'] = 'bytes=%d-' % size
		req = Request(url, headers=headers)
		resp = urlopen(req, context=ctx, timeout=30)
		return resp
	except:
		log_utils.error('url: %s: ' % url)
		return None

def done(title, dest, downloaded):
	try:
		playing = control.player.isPlaying()
		text = homeWindow.getProperty('GEN-DOWNLOADED')
		# if len(text) > 0: text += '[CR]'
		if len(text) > 0: text += '\n'
		if downloaded:
			text += '%s : %s' % (dest.rsplit(os.sep)[-1], '[COLOR forestgreen]Download succeeded[/COLOR]')
		else:
			text += '%s : %s' % (dest.rsplit(os.sep)[-1], '[COLOR red]Download failed[/COLOR]')
		homeWindow.setProperty('GEN-DOWNLOADED', text)
		if (not downloaded) or (not playing): 
			control.okDialog(title, text)
			homeWindow.clearProperty('GEN-DOWNLOADED')
	except:
		log_utils.error()

def doDownload(url, dest, title, image, headers):

	if control.setting('debug.level') == '1':
		log_utils.log('url: %s' % url, __name__)
		log_utils.log('dest: %s' % dest, __name__)
		log_utils.log('title: %s' % title, __name__)
		log_utils.log('image: %s' % image, __name__)
		log_utils.log('headers: %s' % headers, __name__)


	file = dest.rsplit(os.sep, 1)[-1]
	if 'User-Agent' not in headers:
		headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:103.0) Gecko/20100101 Firefox/103.0'})
	resp = getResponse(url, headers, 0)
	if not resp:
		control.hide()
		return control.okDialog(title, dest + '[CR]Download failed: No response from server')
	try: content = int(resp.headers['Content-Length'])
	except: content = 0
	try: resumable = 'bytes' in resp.headers['Accept-Ranges'].lower()
	except: resumable = False
	if content < 1:
		control.hide()
		return control.okDialog(title, file + '[CR]Unknown filesize: Unable to download')
	size = 1024 * 1024
	gb = str(round(content / float(1073741824), 2))
	if content < size:
		size = content
	total = 0
	notify = 0
	errors = 0
	count = 0
	resume = 0
	sleep = 0
	control.hide()
	if control.yesnoDialog('File Size: %sGB' % gb, 'Path: %s' % dest, 'Continue with download?', '[B]Confirm Download[/B]', 'Confirm', 'Cancel') == 1: return
	f = control.openFile(dest, 'w')
	chunk = None
	chunks = []
	while True:
		downloaded = total
		for c in chunks: downloaded += len(c)
		percent = min(100 * downloaded / content, 100)
		if percent >= notify:
			control.notification(title=str(int(percent)) + '%', message=title, icon=image, time=3000) # xbmcgui.Dialog().notification() auto scroll time to complete supercedes allowed "time=" to run in Silvo, removed dest
			notify += 20
		chunk = None
		error = False
		try:
			chunk  = resp.read(size)
			if not chunk:
				if percent < 99: error = True
				else:
					while len(chunks) > 0:
						c = chunks.pop(0)
						f.write(c)
						del c
					f.close()
					if control.setting('debug.level') == '1':
						log_utils.log('Download Complete: %s' % dest, level=log_utils.LOGDEBUG)
					return done(title, dest, True)
		except Exception as e:
			log_utils.error('title: %s - DOWNNLOADER EXCEPTION (A RETRY WILL BE ATTEMPTED): '% title)
			error = True
			sleep = 10
			errno = 0
			if hasattr(e, 'errno'):
				errno = e.errno
			if errno == 10035: # A non-blocking socket operation could not be completed immediately
				pass
			if errno == 10054: # An existing connection was forcibly closed by the remote host
				errors = 10 # force resume
				sleep  = 30
			if errno == 11001: # getaddrinfo failed
				errors = 10 # force resume
				sleep  = 30
		if chunk:
			errors = 0
			chunks.append(chunk)
			if len(chunks) > 5:
				c = chunks.pop(0)
				f.write(c)
				total += len(c)
				del c
		if error:
			errors += 1
			count  += 1
			control.sleep(sleep*1000)
		if (resumable and errors > 0) or errors >= 10:
			if (not resumable and resume >= 25) or resume >= 50: # Give up!
				if control.setting('debug.level') == '1':
					log_utils.log('Download Canceled: %s too many errors whilst downloading' % dest, level=log_utils.LOGWARNING)
				return done(title, dest, False)
			resume += 1
			errors = 0
			if resumable:
				chunks  = []
				resp = getResponse(url, headers, total) # create new response
				if not resp:
					control.hide()
					if control.setting('debug.level') == '1':
						log_utils.log('Download failed: %s No response from server' % dest, level=log_utils.LOGWARNING)
					return control.okDialog(title, dest + '[CR]Download failed: No response from server')
			else: pass

def titlecase(string): # not perfect but close enough
	try:
		articles = ['a', 'an', 'the', 'vs', 'v']
		word_list = re.split(' ', string)
		sw_num = re.match(r'^(19|20)[0-9]{2}', string)
		final = [word_list[0].capitalize()]
		pos = 1
		for word in word_list[1:]:
			final.append(word if word in articles and (not sw_num and pos == 1) else word.capitalize())
			pos += 1
		return " ".join(final)
	except:
		log_utils.error()
		return string

def createStrm(name, image, url, meta_name=None):
	if not url: return control.hide()
	try:
		url = url.split('|')[0]
		file_format = control.setting('downloads.file.format')
		try: transname = name.translate(None, '\/:*?"<>|').strip('.')
		except: transname = name.translate(name.maketrans('', '', '\/:*?"<>|')).strip('.')  # maketrans() is in string module for py2
		ext_list = ('.3gp', '.divx', '.xvid', '.m4v', '.mp4', '.mpeg', '.mpg', '.m2ts', '.mov', '.mkv', '.flv', '.avi', '.wmv', '.webm')
		for i in ext_list: transname = transname.rstrip(i)
		if meta_name:
			try: content = re.search(r'(.+?)\sS(\d*)E\d*$', meta_name).groups()
			except: content = ()
			if file_format == '0':
				try: transname = meta_name.translate(None, '\/:*?"<>|').strip('.')
				except: transname = meta_name.translate(meta_name.maketrans('', '', '\/:*?"<>|')).strip('.')
		else:
			try: content = re.search(r'(.+?)(?:|\.| - |-|.-.|\s)(?:S|s|\s|\.)(\d{1,2})(?!\d)(?:|\.| - |-|.-.|x|\s)(?:E|e|\s|.)([0-2]{1}[0-9]{1})(?!\w)', name.replace('\'', '')).groups()
			except: content = ()
		levels =['../../../..', '../../..', '../..', '..']
		if len(content) == 0:
			dest = control.transPath(control.setting('movie.download.path'))
			for level in levels:
				try: control.makeFile(os.path.abspath(os.path.join(dest, level)))
				except: pass
			control.makeFile(dest)
			if meta_name:
				try: dest = os.path.join(dest, meta_name.translate(None, '\/:*?"<>|').strip('.'))
				except: dest = os.path.join(dest, meta_name.translate(meta_name.maketrans('', '', '\/:*?"<>|')).strip('.'))
			else:
				try: movie_info = re.search(r'(.+?)(?:\.{0,1}-{0,1}\.{0,1}|\s*)(?:|\(|\[|\.)((?:19|20)(?:[0-9]{2}))', name.replace('\'', '')).groups()
				except: movie_info = ()
				if len(movie_info) != 0:
					movietitle = titlecase(re.sub(r'[^A-Za-z0-9\s]+', ' ', movie_info[0]))
					dest = os.path.join(dest, movietitle + ' (' + movie_info[1] + ')')
					if file_format == '0':
						transname = movietitle + ' (' + movie_info[1] + ')'
				else:
					dest = os.path.join(dest, transname)
			control.makeFile(dest)
		else:
			dest = control.transPath(control.setting('tv.download.path'))
			for level in levels:
				try: control.makeFile(os.path.abspath(os.path.join(dest, level)))
				except: pass
			control.makeFile(dest)
			try: transtvshowtitle = content[0].translate(None, '\/:*?"<>|').strip('.').replace('.', ' ')
			except: transtvshowtitle = content[0].translate(content[0].maketrans('', '', '\/:*?"<>|')).strip('.').replace('.', ' ')
			if not meta_name:
				transtvshowtitle = titlecase(re.sub(r'[^A-Za-z0-9\s-]+', ' ', transtvshowtitle))
			dest = os.path.join(dest, transtvshowtitle)
			control.makeFile(dest)
			dest = os.path.join(dest, 'Season %01d' % int(content[1]))
			control.makeFile(dest)
			if file_format == '0' and not meta_name:
				transname = transtvshowtitle + ' S%sE%s' % (content[1], content[2])
		dest = os.path.join(dest, transname + '.strm')
		doStrm(url, dest, transname)
	except: log_utils.error()

def doStrm(url, dest, transname):
	try:
		content = url
		f = control.openFile(dest, 'w')
		f.write(content)
		f.close()
		if control.setting('debug.level') == '1':
			log_utils.log('Strm Download Complete: %s' % (dest), level=log_utils.LOGDEBUG)
		control.hide()
		return control.okDialog(transname, '[COLOR forestgreen]Strm File Downloaded Successfully[/COLOR] '+dest)
	except: 
		log_utils.error()
		control.hide()
		return control.okDialog(transname, dest + 'Issue Downloading File.')