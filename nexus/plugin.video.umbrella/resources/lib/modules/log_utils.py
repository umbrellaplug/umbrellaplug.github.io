# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from datetime import datetime
import inspect
from resources.lib.modules import string_tools
from resources.lib.modules.control import transPath, setting as getSetting, lang, joinPath, existsPath

LOGDEBUG = 0
LOGINFO = 1
LOGWARNING = 2
LOGERROR = 3
LOGFATAL = 4
LOGNONE = 5 # not used

debug_list = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'FATAL']
DEBUGPREFIX = '[ plugin.video.umbrella: %s ]'
LOGPATH = transPath('special://logpath/')


def log(msg, caller=None, level=LOGINFO):
	debug_enabled = getSetting('debug.enabled') == 'true'
	if not debug_enabled: return
	debug_level = getSetting('debug.level')
	if level == LOGDEBUG and debug_level != '1': return
	debug_location = getSetting('debug.location')

	if isinstance(msg, int): msg = lang(msg) # for strings.po translations
	try:
		if not msg.isprintable(): # ex. "\n" is not a printable character so returns False on those cases
			msg = '%s (NORMALIZED by log_utils.log())' % string_tools.normalize(msg)
		if isinstance(msg, bytes):
			msg = '%s (ENCODED by log_utils.log())' % msg.decode('utf-8', errors='replace')

		if caller is not None and level != LOGERROR:
			func = inspect.currentframe().f_back.f_code
			line_number = inspect.currentframe().f_back.f_lineno
			caller = "%s.%s()" % (caller, func.co_name)
			msg = 'From func name: %s Line # :%s\n                       msg : %s' % (caller, line_number, msg)
		elif caller is not None and level == LOGERROR:
			msg = 'From func name: %s.%s() Line # :%s\n                       msg : %s' % (caller[0], caller[1], caller[2], msg)

		if debug_location == '1':
			log_file = joinPath(LOGPATH, 'umbrella.log')
			if not existsPath(log_file):
				f = open(log_file, 'w')
				f.close()
			reverse_log = getSetting('debug.reversed') == 'true'
			if not reverse_log:
				with open(log_file, 'a', encoding='utf-8') as f:  # "with" auto cleans up and closes
					line = '[%s %s] %s: %s' % (datetime.now().date(), str(datetime.now().time())[:8], DEBUGPREFIX % debug_list[level], msg)
					f.write(line.rstrip('\r\n') + '\n')
					# f.writelines([line1, line2]) ## maybe an option for the 2 lines without using "\n"
			else:
				with open(log_file, 'r+', encoding='utf-8') as f:
					line = '[%s %s] %s: %s' % (datetime.now().date(), str(datetime.now().time())[:8], DEBUGPREFIX % debug_list[level], msg)
					log_file = f.read()
					f.seek(0, 0)
					f.write(line.rstrip('\r\n') + '\n' + log_file)
		else:
			import xbmc
			if level == 0:
				xbmc.log('%s: %s' % (DEBUGPREFIX % debug_list[0], msg), 1)
			else:
				xbmc.log('%s: %s' % (DEBUGPREFIX % debug_list[level], msg), level)
	except Exception as e:
		import traceback
		traceback.print_exc()
		import xbmc
		xbmc.log('[ plugin.video.umbrella ] log_utils.log() Logging Failure: %s' % (e), LOGERROR)

def error(message=None, exception=True):
	try:
		import sys
		if exception:
			type, value, traceback = sys.exc_info()
			addon = 'plugin.video.umbrella'
			filename = (traceback.tb_frame.f_code.co_filename)
			filename = filename.split(addon)[1]
			name = traceback.tb_frame.f_code.co_name
			linenumber = traceback.tb_lineno
			errortype = type.__name__
			errormessage = value or value.message
			if str(errormessage) == '': return
			if message: message += ' -> '
			else: message = ''
			message += str(errortype) + ' -> ' + str(errormessage)
			caller = [filename, name, linenumber]
		else:
			caller = None
		del(type, value, traceback) # So we don't leave our local labels/objects dangling
		log(msg=message, caller=caller, level=LOGERROR)
	except Exception as e:
		import xbmc
		xbmc.log('[ plugin.video.umbrella ] log_utils.error() Logging Failure: %s' % (e), LOGERROR)

def clear_logFile():
	cleared = False
	try:
		from resources.lib.modules.control import yesnoDialog
		if not yesnoDialog(lang(32056), '', ''): return 'canceled'
		log_file = joinPath(LOGPATH, 'umbrella.log')
		if not existsPath(log_file):
			f = open(log_file, 'w')
			return f.close()
		f = open(log_file, 'r+')
		f.truncate(0) # need '0' when using r
		f.close()
		cleared = True
	except Exception as e:
		import xbmc
		xbmc.log('[ plugin.video.umbrella ] log_utils.clear_logFile() Failure: %s' % (e), LOGERROR)
		cleared = False
	return cleared

def view_LogFile(name):
	try:
		from resources.lib.windows.textviewer import TextViewerXML
		from resources.lib.modules.control import addonPath
		log_file = joinPath(LOGPATH, '%s.log' % name.lower())
		if not existsPath(log_file):
			from resources.lib.modules.control import notification
			return notification(message='Log File not found, likely logging is not enabled.')
		f = open(log_file, 'r', encoding='utf-8', errors='ignore')
		text = f.read()
		f.close()
		heading = '[B]%s -  LogFile[/B]' % name
		windows = TextViewerXML('textviewer.xml', addonPath('plugin.video.umbrella'), heading=heading, text=text)
		windows.run()
		del windows
	except: error()

def upload_LogFile(name):
	from resources.lib.modules.control import notification
	url = 'https://paste.kodi.tv/'
	log_file = joinPath(LOGPATH, '%s.log' % name.lower())
	if not existsPath(log_file):
		return notification(message='Log File not found, likely logging is not enabled.')
	try:
		import requests
		from resources.lib.modules.control import addonVersion, selectDialog
		f = open(log_file, 'r', encoding='utf-8', errors='ignore')
		text = f.read()
		f.close()
		UserAgent = 'Umbrella %s' % addonVersion('plugin.video.umbrella')
		response = requests.post(url + 'documents', data=text.encode('utf-8', errors='ignore'), headers={'User-Agent': UserAgent})
		if 'key' in response.json():
			result = url + response.json()['key']
			log('%s log file uploaded to: %s' % (name, result))
			from sys import platform as sys_platform
			supported_platform = any(value in sys_platform for value in ('win32', 'linux2'))
			highlight_color = getSetting('highlight.color')
			list = [('[COLOR %s]url:[/COLOR]  %s' % (highlight_color, str(result)), str(result))]
			if supported_platform: list += [('[COLOR %s]  -- Copy url To Clipboard[/COLOR]' % highlight_color, ' ')]
			select = selectDialog([i[0] for i in list], lang(32196) if name.lower() == 'umbrella' else lang(32199))
			if 'Copy url To Clipboard' in list[select][0]:
				try:
					from resources.lib.modules.source_utils import copy2clip
					copy2clip(list[select - 1][1])
				except:
					pass
		elif 'message' in response.json():
			notification(message='%s Log upload failed: %s' % (name, str(response.json()['message'])))
			log('%s Log upload failed: %s' % (name, str(response.json()['message'])), level=LOGERROR)
		else:
			notification(message='%s Log upload failed' % name)
			log('%s Log upload failed: %s' % (name, response.text), level=LOGERROR)
	except:
		error('%s log upload failed' % name)
		notification(message='pastebin post failed: See log for more info')