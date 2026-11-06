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


def report_failure(title, message):
	from resources.lib.modules.download_manager import DownloadStore
	try:
		store = DownloadStore()
		job = store.create(title or 'Download', '')
		store.update(job, 'Failed', message=message)
	except Exception: pass
	control.hide()
	control.notification(title='Downloads - Failed', message=message, icon='ERROR', time=6000)
	return False


def download(name, image, url, meta_name=None, pack=None, no_confirm=False):
	if control.setting('debug.level') == '1':
		log_utils.log('name: %s' % name, __name__)
		log_utils.log('image: %s' % image, __name__)
		log_utils.log('meta_name: %s' % meta_name, __name__)
		log_utils.log('pack: %s' % pack, __name__)


	#test = url.rsplit('/', 1)[1].split('|')[0]
	#log_utils.log('test: %s' % str(test), __name__)
	#test = unquote(test).replace(" ","")
	#log_utils.log('test2: %s' % str(test), __name__)

	if not url:
		return report_failure(name, 'No downloadable link was returned by the provider.')
	try:
		file_format = control.setting('downloads.file.format')
		try: headers = dict(parse_qsl(url.rsplit('|', 1)[1]))
		except: headers = dict('')
		url = url.split('|')[0]
		try:
			name = name.replace(':','')
		except:
			pass
		try: transname = name.translate((None, r'\/:*?"<>|')).strip('.').replace(':', '')
		except: transname = name.translate(name.maketrans('', '', r'\/:*?"<>|')).strip('.').replace(':', '')  # maketrans() is in string module for py2
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
								transname = meta_name.translate((None, r'\/:*?"<>|')).strip('.').replace(':', '')
							except:
								transname = meta_name.translate(meta_name.maketrans('', '', r'\/:*?"<>|')).strip('.').replace(':', '')
			if control.setting('debug.level') == '1':
				log_utils.log('content: %s' % str(content), __name__)
			# transname = url.rsplit('/', 1)[1].split('|')[0]
			url_basename = unquote(url.rsplit('/', 1)[1].split('|')[0])
			basename_has_ep = bool(re.search(r'S\d{1,2}E\d{1,2}', url_basename, re.I))
			if basename_has_ep and any(url_basename.lower().endswith(ext) for ext in ('.3gp', '.avi', '.divx', '.flv', '.m4v', '.mp4', '.mpeg', '.mpg', '.m2ts', '.mov', '.mkv', '.wmv', '.webm', '.xvid')):
				transname = url_basename


		elif meta_name:
			try: content = re.search(r'(.+?)\sS(\d*)E(\d*)$', meta_name, re.I).groups()
			except: content = ()
			if file_format == '0':
				try:
					transname = meta_name.translate((None, r'\/:*?"<>|')).strip('.').replace(':', '')
				except: transname = meta_name.translate(meta_name.maketrans('', '', r'\/:*?"<>|')).strip('.').replace(':', '')
		else:
			try: content = re.search(r'(.+?)(?:|\.| - |-|.-.|\s)(?:S|s|\s|\.)(\d{1,2})(?!\d)(?:|\.| - |-|.-.|x|\s)(?:E|e|\s|.)([0-2]{1}[0-9]{1})(?!\w)', name.replace('\'', ''), re.I).groups()
			except: content = ()
		if control.setting('debug.level') == '1':
			log_utils.log('content: %s' % str(content), __name__)

		for i in video_extensions: transname = transname.replace(i, "")
		transname = transname.replace(':','')


		if len(content) == 0:
			dest = control.transPath(control.setting('movie.download.path'))
			if not dest: dest = control.transPath('special://profile/addon_data/plugin.video.umbrella/Movies/')
			for level in levels:
				try: control.makeFile(os.path.abspath(os.path.join(dest, level)))
				except: pass
			control.makeFile(dest)
			if meta_name:
				try:
					meta_trans = meta_name.translate((None, r'\/:*?"<>|')).strip('.').replace(':', '')
					dest = os.path.join(dest, meta_trans)
				except:
					dest = os.path.join(dest, meta_name.translate(meta_name.maketrans('', '', r'\/:*?"<>|')).strip('.').replace(':', ''))
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
			if not dest: dest = control.transPath('special://profile/addon_data/plugin.video.umbrella/TVShows/')
			for level in levels:
				try: control.makeFile(os.path.abspath(os.path.join(dest, level)))
				except:
					log_utils.error()
					pass
			control.makeFile(dest)
			try: transtvshowtitle = content[0].translate((None, r'\/:*?"<>|')).strip('.').replace('.', ' ').replace(':', '')
			except: transtvshowtitle = content[0].translate(content[0].maketrans('', '', r'\/:*?"<>|')).strip('.').replace('.', ' ').replace(':', '')
			if not meta_name:
				transtvshowtitle = titlecase(re.sub(r'[^A-Za-z0-9\s-]+', ' ', transtvshowtitle))
			dest = os.path.join(dest, transtvshowtitle)

			if control.setting('debug.level') == '1':
				log_utils.log('dest: %s' % dest, __name__)

			control.makeFile(dest)
			dest = os.path.join(dest, 'Season %02d' % int(content[1]))
			control.makeFile(dest)
			if file_format == '0' and not meta_name:
				transname = transtvshowtitle + ' S%02dE%02d' % (int(content[1]), int(content[2]))
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
		return doDownload(url, dest, transname + '.' + ext, image, headers, no_confirm=no_confirm)
	except Exception:
		return report_failure(name, 'Unable to prepare the download. Check the download folders and filename.')

def download_pack(name, image, info):
	debrid = info.get('debrid', '')
	url = info.get('url', '')
	info_hash = info.get('hash', '')

	if 'Real-Debrid' in debrid:
		from resources.lib.debrid.realdebrid import RealDebrid as DebridClass
		def resolve(d, link): return d.unrestrict_link(link)
	elif 'Premiumize' in debrid:
		from resources.lib.debrid.premiumize import Premiumize as DebridClass
		def resolve(d, link): return d.add_headers_to_url(link)
	elif 'AllDebrid' in debrid:
		from resources.lib.debrid.alldebrid import AllDebrid as DebridClass
		def resolve(d, link): return d.unrestrict_link(link)
	elif 'Offcloud' in debrid:
		from resources.lib.debrid.offcloud import Offcloud as DebridClass
		def resolve(d, link): return link
	elif 'TorBox' in debrid:
		from resources.lib.debrid.torbox import TorBox as DebridClass
		def resolve(d, link): return d.add_headers_to_url(d.unrestrict_link(link))
	else:
		return report_failure(name, 'Pack downloads are not supported by this provider.')

	control.busy()
	try:
		svc = DebridClass()
		file_list = svc.display_magnet_pack(url, info_hash)
	except:
		return report_failure(name, 'Unable to load the pack files. Check the provider account.')

	if not file_list:
		control.hide()
		return control.notification(message='No files found in pack', icon='WARNING')

	video_files = sorted(
		[f for f in file_list if any(f.get('filename', '').lower().endswith(ext) for ext in video_extensions)],
		key=lambda f: f.get('filename', '').lower()
	)
	if not video_files:
		video_files = sorted(file_list, key=lambda f: f.get('filename', '').lower())

	total_size = sum(f.get('size', 0) for f in video_files)
	control.hide()

	if control.yesnoDialog(
		'%d files  |  %.2f GB total' % (len(video_files), total_size / float(1073741824)),
		'Pack: %s' % name,
		'Download all files?',
		'[B]Download Pack[/B]', 'Download', 'Cancel'
	) == 1:
		return

	total = len(video_files)
	succeeded, failed = 0, 0
	control.progressDialog.create('Downloading Pack', name)
	try:
		for idx, f in enumerate(video_files):
			if control.progressDialog.iscanceled():
				break
			filename = f.get('filename', '')
			link = f.get('link', '')
			if not filename or not link:
				failed += 1
				report_failure(filename or name, 'The pack entry has no downloadable link.')
				continue
			pct = int(idx * 100 / total)
			control.progressDialog.update(pct, '%d / %d  |  %s' % (idx + 1, total, filename))
			try:
				resolved = resolve(svc, link)
			except:
				failed += 1
				report_failure(filename, 'Unable to resolve this pack file.')
				continue
			if resolved:
				if download(filename, image, resolved, meta_name=None, pack=None, no_confirm=True): succeeded += 1
				else: failed += 1
			else:
				failed += 1
				report_failure(filename, 'No downloadable link was returned for this pack file.')
	finally:
		control.progressDialog.close()
		control.notification(title='Download Pack', message='%s completed, %s unsuccessful, %s not started. See Download Manager.' %
			(succeeded, failed, total - succeeded - failed), time=6000)


def getResponse(url, headers, size):
	headers = dict(headers)
	if size > 0: headers['Range'] = 'bytes=%d-' % int(size)
	return urlopen(Request(url, headers=headers), context=ctx, timeout=30)


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

def _download_error(exc, phase):
	# Do not expose signed download URLs, authorization headers or server bodies.
	from urllib.error import HTTPError, URLError
	if isinstance(exc, HTTPError): return 'Server returned HTTP %s.' % exc.code
	if isinstance(exc, (TimeoutError, URLError)): return 'Connection failed or timed out.'
	if isinstance(exc, ValueError): return str(exc)
	if phase == 'file': return 'Unable to write the download. Check the folder permissions and free space.'
	return 'Download failed. The connection was interrupted.'


def _check_resume_response(resp, offset, content, validator_name='', validator=''):
	match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', resp.headers.get('Content-Range', ''))
	if (resp.getcode() != 206 or not match or int(match[1]) != offset
		or int(match[2]) != content - 1 or int(match[3]) != content):
		raise ValueError('The server did not honor the resume request or the file changed. Partial file retained.')
	if validator and resp.headers.get(validator_name) != validator:
		raise ValueError('The remote file changed. Resume stopped to protect the partial file.')


def doDownload(url, dest, title, image, headers, no_confirm=False, resume_job=None):
	from time import monotonic
	import xbmcvfs
	from resources.lib.modules.download_manager import DownloadStore
	store, job, resp, output = None, None, None, None
	total, content, speed = 0, 0, 0
	phase = 'network'
	partial = dest + '.part'
	validator_name, validator = '', ''
	status, message = 'Failed', 'Download did not finish.'
	try:
		store = DownloadStore()
		if resume_job:
			saved = store.claim_resume(resume_job)
			job = resume_job
			url, dest, title, headers = saved['url'], saved['destination'], saved['title'], saved['headers']
			partial = dest + '.part'
			content = saved['expected_total']
			validator_name, validator = saved['validator_name'], saved['validator']
		else:
			job = store.create(title, dest)
		control.hide()
		control.notification(title='Downloads', message='Connecting: ' + title, icon=image)
		if not url: raise ValueError('No downloadable link was returned by the provider.')
		if control.existsPath(dest): raise ValueError('The destination file already exists. Choose another name or remove it first.')
		if not resume_job and control.existsPath(partial):
			raise ValueError('A partial download already exists. Resume the original entry in Download Manager, or move/remove its .part file.')
		headers = dict(headers or {})
		headers.setdefault('User-Agent', 'Mozilla/5.0')
		# Byte counts and Range offsets must refer to the actual file bytes.
		headers['Accept-Encoding'] = 'identity'
		headers.pop('Range', None)
		if resume_job:
			phase = 'file'
			# Native update mode preserves existing bytes. Kodi VFS "w" truncates
			# files, so remote VFS-only destinations cannot safely resume here.
			local_partial = control.transPath(partial)
			if not os.path.isfile(local_partial):
				raise ValueError('The partial file is missing or this destination does not support local file resume.')
			output = open(local_partial, 'r+b')
			total = os.fstat(output.fileno()).st_size
			if not validator or not content or not 0 < total <= content:
				raise ValueError('The partial file size or saved resume information is invalid. File retained.')
			headers['If-Range'] = validator
			phase = 'network'
			offset = min(total, content - 1)
			headers['Range'] = 'bytes=%d-' % offset
			resp = getResponse(url, headers, offset)
			if resp is None: raise ValueError('No response from the download server.')
			_check_resume_response(resp, offset, content, validator_name, validator)
			output.seek(total)
		else:
			resp = getResponse(url, headers, 0)
		if resp is None: raise ValueError('No response from the download server.')
		if not resume_job:
			if resp.getcode() != 200: raise ValueError('The server did not return a complete file response.')
			try: content = max(0, int(resp.headers.get('Content-Length', 0)))
			except (TypeError, ValueError): content = 0
		mime = resp.headers.get('Content-Type', '').lower()
		if 'text/html' in mime or 'application/json' in mime:
			raise ValueError('The server returned an error page instead of a video file.')
		resumable = bool(resume_job) or 'bytes' in resp.headers.get('Accept-Ranges', '').lower()
		if not resume_job:
			etag = resp.headers.get('ETag', '')
			if etag and not etag.startswith('W/'):
				validator_name, validator = 'ETag', etag
			elif resp.headers.get('Last-Modified'):
				validator_name, validator = 'Last-Modified', resp.headers['Last-Modified']
			if resumable and content and validator:
				store.save_request(job, url, headers, validator_name, validator, content)
		store.update(job, 'Awaiting confirmation', total, content)
		if not no_confirm:
			size = '%.2f GB' % (content / 1073741824.0) if content else 'Unknown (progress will show downloaded bytes)'
			if control.yesnoDialog('File size: ' + size, 'Path: ' + dest,
				'Continue with download?', '[B]Confirm Download[/B]', 'Confirm', 'Cancel') == 1:
				status, message = 'Cancelled', 'Download declined.'
				return False
		if store.cancelled(job) or control.monitor.abortRequested():
			status, message = 'Cancelled', 'Download cancelled.'
			return False
		phase = 'file'
		if output is None: output = control.openFile(partial, 'w')
		store.update(job, 'Downloading', total, content)
		control.notification(title='Downloads', message=('Resumed: ' if resume_job else 'Started: ') + title, icon=image)
		started = last_update = monotonic()
		initial_bytes = total
		retries = 0
		while True:
			if store.cancelled(job) or control.monitor.abortRequested():
				status, message = 'Cancelled', 'Download cancelled. Partial file retained: ' + partial
				return False
			if content and total == content: break
			phase = 'network'
			try:
				chunk = resp.read(256 * 1024)
				if not chunk and content and total != content:
					raise IOError('Incomplete response')
			except Exception:
				if not resumable or not content or not total or retries >= 3:
					raise ValueError('Download interrupted before completion. Partial file retained: ' + partial)
				retries += 1
				store.update(job, 'Retrying', total, content, message='Reconnecting (%s/3)' % retries)
				resp.close()
				if validator: headers['If-Range'] = validator
				resp = getResponse(url, headers, total)
				if resp is None: raise ValueError('Unable to reconnect to the download server.')
				_check_resume_response(resp, total, content, validator_name, validator)
				continue
			if not chunk:
				if total == 0: raise ValueError('The server returned an empty file.')
				break
			if content and total + len(chunk) > content:
				raise ValueError('The server returned an unexpected file size.')
			phase = 'file'
			written = output.write(chunk)
			if written is False or (type(written) is int and written != len(chunk)):
				raise IOError('Short write')
			total += len(chunk)
			now = monotonic()
			speed = (total - initial_bytes) / max(now - started, 0.001)
			if now - last_update >= 1:
				store.update(job, 'Downloading', total, content, speed)
				last_update = now
		phase = 'file'
		output.close()
		output = None
		if store.cancelled(job) or control.monitor.abortRequested():
			status, message = 'Cancelled', 'Download cancelled. Partial file retained: ' + partial
			return False
		if control.existsPath(dest) or not xbmcvfs.rename(partial, dest):
			raise ValueError('Unable to finalize the file. Completed data retained: ' + partial)
		status, message = 'Completed', 'Saved to: ' + dest
		return True
	except Exception as exc:
		message = _download_error(exc, phase)
		return False
	finally:
		if resp is not None:
			try: resp.close()
			except Exception: pass
		if output is not None:
			try: output.close()
			except Exception: pass
		if store is not None and job:
			try: store.update(job, status, total, content, speed, message)
			except Exception: pass
		control.hide()
		control.notification(title='Downloads - ' + status, message=title + ': ' + message,
			icon='ERROR' if status == 'Failed' else image, time=6000)


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
		try: transname = name.translate(None, r'\/:*?"<>|').strip('.')
		except: transname = name.translate(name.maketrans('', '', r'\/:*?"<>|')).strip('.')  # maketrans() is in string module for py2
		ext_list = ('.3gp', '.divx', '.xvid', '.m4v', '.mp4', '.mpeg', '.mpg', '.m2ts', '.mov', '.mkv', '.flv', '.avi', '.wmv', '.webm')
		for i in ext_list: transname = transname.rstrip(i)
		if meta_name:
			try: content = re.search(r'(.+?)\sS(\d*)E\d*$', meta_name).groups()
			except: content = ()
			if file_format == '0':
				try: transname = meta_name.translate(None, r'\/:*?"<>|').strip('.')
				except: transname = meta_name.translate(meta_name.maketrans('', '', r'\/:*?"<>|')).strip('.')
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
				try: dest = os.path.join(dest, meta_name.translate(None, r'\/:*?"<>|').strip('.'))
				except: dest = os.path.join(dest, meta_name.translate(meta_name.maketrans('', '', r'\/:*?"<>|')).strip('.'))
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
			try: transtvshowtitle = content[0].translate(None, r'\/:*?"<>|').strip('.').replace('.', ' ')
			except: transtvshowtitle = content[0].translate(content[0].maketrans('', '', r'\/:*?"<>|')).strip('.').replace('.', ' ')
			if not meta_name:
				transtvshowtitle = titlecase(re.sub(r'[^A-Za-z0-9\s-]+', ' ', transtvshowtitle))
			dest = os.path.join(dest, transtvshowtitle)
			control.makeFile(dest)
			dest = os.path.join(dest, 'Season %02d' % int(content[1]))
			control.makeFile(dest)
			if file_format == '0' and not meta_name:
				transname = transtvshowtitle + ' S%02dE%02d' % (int(content[1]), int(content[2]))
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
