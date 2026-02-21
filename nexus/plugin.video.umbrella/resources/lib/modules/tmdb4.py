# -*- coding: utf-8 -*-
"""
	Umbrella Add-on - TMDB v4 API Support
"""

from json import dumps as jsdumps
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from resources.lib.modules import control
from resources.lib.modules import log_utils

getLS = control.lang
getSetting = control.setting
setSetting = control.setSetting

TMDB_V4_BASE = 'https://api.themoviedb.org/4'
tmdb4_icon = control.joinPath(control.artPath(), 'tmdb.png')
highlight_color = getSetting('highlight.color')

session = requests.Session()
retries = Retry(total=4, backoff_factor=0.3, status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 524, 530])
session.mount('https://api.themoviedb.org', HTTPAdapter(max_retries=retries, pool_maxsize=100))


def getTMDbV4CredentialsInfo():
	token = getSetting('tmdb.v4.accesstoken')
	account = getSetting('tmdb.v4.accountid')
	return bool(token and account)


def _get_headers(use_user_token=True):
	if use_user_token:
		token = getSetting('tmdb.v4.accesstoken')
	else:
		token = getSetting('tmdb.v4.readtoken')
	return {
		'Authorization': 'Bearer %s' % token,
		'Content-Type': 'application/json;charset=utf-8'
	}


def getTMDbV4(url, post=None, delete=False):
	try:
		if not url.startswith('http'):
			url = TMDB_V4_BASE + url
		headers = _get_headers(use_user_token=True)
		if delete:
			response = session.delete(url, data=jsdumps(post) if post else None, headers=headers, timeout=20)
		elif post:
			response = session.post(url, data=jsdumps(post), headers=headers, timeout=20)
		else:
			response = session.get(url, headers=headers, timeout=20)
		if response.status_code in (200, 201):
			return response.json()
		elif response.status_code == 401:
			log_utils.log('TMDB v4: 401 Unauthorized - check access token', level=log_utils.LOGWARNING)
			control.notification(title='TMDB v4', message='Unauthorized. Please re-authenticate in Settings.', icon='ERROR')
		elif response.status_code == 429:
			if 'Retry-After' in response.headers:
				throttle = int(response.headers['Retry-After'])
				control.sleep((throttle + 1) * 1000)
				return getTMDbV4(url, post=post, delete=delete)
		else:
			log_utils.log('TMDB v4 error: %s - %s' % (response.status_code, url), level=log_utils.LOGWARNING)
		return None
	except:
		log_utils.error()
		return None

def authenticate(fromSettings=0):
	import time
	import traceback
	log_utils.log('TMDB v4: authenticate() called, fromSettings=%s' % fromSettings, level=log_utils.LOGINFO)
	try:
		if fromSettings:
			control.sleep(1200)

		read_token = (getSetting('tmdb.v4.readtoken') or '').strip()
		if not read_token:
			control.notification(title='TMDB v4', message='Please enter your TMDB v4 Read Access Token in Settings first.', icon='ERROR', time=5000)
			if fromSettings:
				control.openSettings(id='plugin.video.umbrella')
			return

		read_headers = {
			'Authorization': 'Bearer %s' % read_token,
			'Content-Type': 'application/json;charset=utf-8'
		}

		# Step 1: Request token
		url = TMDB_V4_BASE + '/auth/request_token'
		post = {'redirect_to': 'approved'}
		response = session.post(url, data=jsdumps(post), headers=read_headers, timeout=20)

		if response.status_code not in (200, 201):
			control.notification(title='TMDB v4', message='Failed to get request token.', icon='ERROR', time=5000)
			return

		request_token = response.json().get('request_token')
		if not request_token:
			control.notification(title='TMDB v4', message='Failed to get request token.', icon='ERROR', time=5000)
			return

		approval_url = 'https://www.themoviedb.org/auth/access?request_token=%s' % request_token
		message = 'Scan QR or visit URL to authorize:[CR][CR]%s' % approval_url

		dialog_shown = False
		approved = False

		try:
			if control.setting('dialogs.useumbrelladialog') == 'true':
				from resources.lib.modules import tools
				tmdb_qr = tools.make_qr(approval_url)
				progressDialog = control.getProgressWindow('TMDB v4 Authentication', tmdb_qr, 1)
				progressDialog.set_controls()
				progressDialog.update(0, message)
			else:
				progressDialog = control.progressDialog
				progressDialog.create('TMDB v4 Authentication', message)

			dialog_shown = True
			start = time.time()

			# Step 2: Poll for approval
			while not progressDialog.iscanceled() and (time.time() - start) < 600:
				control.sleep(2000)

				url2 = TMDB_V4_BASE + '/auth/access_token'
				post2 = {'request_token': request_token}
				response2 = session.post(url2, data=jsdumps(post2), headers=read_headers, timeout=20)

				if response2.status_code in (200, 201):
					result = response2.json()
					access_token = result.get('access_token')
					account_id = result.get('account_id')

					if access_token and account_id:
						setSetting('tmdb.v4.accesstoken', access_token)
						setSetting('tmdb.v4.accountid', account_id)
						approved = True
						break

		except Exception as e:
			log_utils.log('TMDB v4: Dialog exception: %s' % str(e), level=log_utils.LOGWARNING)
			log_utils.log(traceback.format_exc(), level=log_utils.LOGWARNING)

		finally:
			if dialog_shown:
				try:
					progressDialog.close()
				except:
					pass

		# Final result
		if approved:
			control.notification(title='TMDB v4', message='Successfully authenticated!', icon=tmdb4_icon)
		else:
			control.notification(title='TMDB v4', message='Authorization cancelled or timed out.', icon='ERROR', time=5000)

		if fromSettings:
			control.openSettings(id='plugin.video.umbrella')

	except Exception as e:
		log_utils.log('TMDB v4: authenticate() exception: %s' % str(e), level=log_utils.LOGWARNING)
		log_utils.log(traceback.format_exc(), level=log_utils.LOGWARNING)
		log_utils.error()


def revoke(fromSettings=0):
	try:
		access_token = getSetting('tmdb.v4.accesstoken')
		if not access_token:
			if fromSettings:
				control.openSettings(id='plugin.video.umbrella')
			return

		url = TMDB_V4_BASE + '/auth/access_token'
		response = session.delete(url, data=jsdumps({'access_token': access_token}), headers=_get_headers(use_user_token=True), timeout=20)
		# Clear stored credentials regardless of response
		setSetting('tmdb.v4.accesstoken', '')
		setSetting('tmdb.v4.accountid', '')
		if response.status_code in (200, 201):
			control.notification(title='TMDB v4', message='Successfully revoked authentication.')
		else:
			control.notification(title='TMDB v4', message='Credentials cleared (server response: %s).' % response.status_code)
		if fromSettings:
			control.openSettings(id='plugin.video.umbrella')
	except:
		log_utils.error()
		setSetting('tmdb.v4.accesstoken', '')
		setSetting('tmdb.v4.accountid', '')
		if fromSettings:
			control.openSettings(id='plugin.video.umbrella')


def get_user_lists():
	try:
		account_id = getSetting('tmdb.v4.accountid')
		if not account_id:
			return []
		url = TMDB_V4_BASE + '/account/%s/lists' % account_id
		result = getTMDbV4(url)
		if not result:
			return []
		items = result.get('results', [])
		all_items = list(items)
		page = result.get('page', 1)
		total_pages = result.get('total_pages', 1)
		while page < total_pages:
			page += 1
			next_result = getTMDbV4(url + '?page=%s' % page)
			if not next_result:
				break
			all_items += next_result.get('results', [])
		return all_items
	except:
		log_utils.error()
		return []


def add_to_list(list_id, tmdb_id, mediatype='movie'):
	try:
		url = TMDB_V4_BASE + '/list/%s/items' % list_id
		post = {'items': [{'media_type': mediatype, 'media_id': int(tmdb_id)}]}
		result = getTMDbV4(url, post=post)
		if result and result.get('success'):
			control.notification(title='TMDB v4', message='Added to list successfully.', icon=tmdb4_icon)
			return True
		elif result:
			control.notification(title='TMDB v4', message=result.get('status_message', 'Failed to add item.'), icon='ERROR')
		return False
	except:
		log_utils.error()
		return False


def remove_from_list(list_id, tmdb_id, mediatype='movie'):
	try:
		url = TMDB_V4_BASE + '/list/%s/items' % list_id
		post = {'items': [{'media_type': mediatype, 'media_id': int(tmdb_id)}]}
		result = getTMDbV4(url, post=post, delete=True)
		if result and result.get('success'):
			control.notification(title='TMDB v4', message='Removed from list successfully.', icon=tmdb4_icon)
			return True
		elif result:
			control.notification(title='TMDB v4', message=result.get('status_message', 'Failed to remove item.'), icon='ERROR')
		return False
	except:
		log_utils.error()
		return False


def create_list(name, description='', public=True):
	try:
		url = TMDB_V4_BASE + '/list'
		post = {
			'name': name,
			'iso_639_1': 'en',
			'description': description,
			'public': public
		}
		result = getTMDbV4(url, post=post)
		if result and result.get('id'):
			control.notification(title='TMDB v4', message='List "%s" created.' % name, icon=tmdb4_icon)
			return result['id']
		else:
			control.notification(title='TMDB v4', message='Failed to create list.', icon='ERROR')
		return None
	except:
		log_utils.error()
		return None


def create_list_dialog():
	try:
		if not getTMDbV4CredentialsInfo():
			control.notification(title='TMDB v4', message=getLS(40607) if _has_string(40607) else 'Not authenticated with TMDB v4. Check Settings.', icon='ERROR')
			return
		list_name = control.inputDialog(getLS(40608) if _has_string(40608) else 'New List Name')
		if not list_name:
			return
		create_list(list_name)
	except:
		log_utils.error()


def manager(name, tmdb, mediatype='movie'):
	try:
		if not getTMDbV4CredentialsInfo():
			control.notification(title='TMDB v4', message=getLS(40607) if _has_string(40607) else 'Not authenticated with TMDB v4. Check Settings.', icon='ERROR')
			return

		user_lists = get_user_lists()
		if user_lists is None:
			return

		items = [('[COLOR %s][B]Create New List[/B][/COLOR]' % highlight_color, ('create', None))]
		for lst in user_lists:
			lst_name = lst.get('name', '')
			lst_id = lst.get('id')
			items.append(('Add to [COLOR %s]%s[/COLOR]' % (highlight_color, lst_name), ('add', lst_id)))
			items.append(('Remove from [COLOR %s]%s[/COLOR]' % (highlight_color, lst_name), ('remove', lst_id)))

		control.hide()
		select = control.selectDialog([i[0] for i in items], heading='%s - %s' % (control.addonInfo('name'), getLS(40606) if _has_string(40606) else 'TMDB List Manager'))
		if select < 0:
			return

		action, list_id = items[select][1]

		if action == 'create':
			list_name = control.inputDialog(getLS(40608) if _has_string(40608) else 'New List Name')
			if list_name:
				new_id = create_list(list_name)
				if new_id and tmdb:
					add_to_list(new_id, tmdb, mediatype)
		elif action == 'add' and tmdb:
			add_to_list(list_id, tmdb, mediatype)
		elif action == 'remove' and tmdb:
			remove_from_list(list_id, tmdb, mediatype)
	except:
		log_utils.error()


def _has_string(string_id):
	"""Check if a language string ID exists without raising exceptions."""
	try:
		val = getLS(string_id)
		return bool(val and val != str(string_id))
	except:
		return False
