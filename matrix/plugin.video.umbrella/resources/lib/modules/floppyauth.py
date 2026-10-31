# -*- coding: utf-8 -*-
"""Floppy public-client device authorization and rotating OAuth credentials."""
import json
import sqlite3
import time
import uuid
from urllib.parse import urlsplit

import requests
from resources.lib.modules import control

DEVICE_GRANT = 'urn:ietf:params:oauth:grant-type:device_code'
SCOPES = 'catalog:read progress:read progress:write watchlist:read watchlist:write scrobble:write sync:read lists:read lists:write'


class AuthError(Exception):
    pass


def _setting(key):
    # Read Kodi's current settings, not a different interpreter's cached copy.
    return control.addon('plugin.video.umbrella').getSetting(key)


def _load(key):
    raw = _setting(key)
    if not raw: return {}
    try:
        value = json.loads(raw)
        if isinstance(value, dict): return value
    except (ValueError, TypeError): pass
    raise AuthError('Floppy authorization is unreadable. Please authorize again.')


def _save(key, value):
    control.setSetting(key, json.dumps(value, separators=(',', ':')) if value else '')
    control.make_settings_dict()


def _lock():
    control.makeFile(control.dataPath)
    connection = sqlite3.connect(control.joinPath(control.dataPath, 'floppyOAuth.lock'), timeout=60)
    connection.execute('BEGIN IMMEDIATE')
    return connection


def _root(base):
    return base[:-7] if base.endswith('/api/v1') else base.rstrip('/')


def _endpoint(root, url):
    source, target = urlsplit(root), urlsplit(url)
    prefix = source.path.rstrip('/') + '/'
    if (target.scheme, target.netloc.lower()) != (source.scheme, source.netloc.lower()) or not target.path.startswith(prefix):
        raise AuthError('Floppy returned an OAuth address outside the configured server.')
    if target.username or target.password or target.fragment:
        raise AuthError('Floppy returned an invalid OAuth address.')
    return url


def _json(response):
    try:
        data = response.json()
        return data if isinstance(data, dict) else {}
    except ValueError: return {}


def _post(session, url, data):
    # A refresh token is single-use. Never automatically repeat its exchange.
    return session.post(url, data=data, timeout=(10, 30), allow_redirects=False)


def _tokens(data, base, client, generation=None):
    if not data.get('access_token') or not data.get('refresh_token') or str(data.get('token_type', '')).lower() != 'bearer':
        raise AuthError('Floppy returned incomplete OAuth credentials.')
    if not set(SCOPES.split()).issubset(str(data.get('scope') or '').split()):
        raise AuthError('Floppy did not grant all permissions required by Umbrella. Please authorize again.')
    lifetime = int(data.get('expires_in') or 0)
    if lifetime <= 0: raise AuthError('Floppy returned an invalid OAuth expiry.')
    return dict(server=base, client_id=client, access_token=data['access_token'],
                refresh_token=data['refresh_token'], expires_at=time.time() + lifetime,
                scope=data['scope'], generation=generation or uuid.uuid4().hex)


def access_token(base, session, failed_token=None, expected_identity=None):
    if not _setting('floppy.oauth'):
        token = _setting('floppy.token')
        if expected_identity is not None and token != expected_identity:
            raise AuthError('Floppy credentials changed; request cancelled.')
        return token
    connection = _lock()
    try:
        state = _load('floppy.oauth')
        if not state: raise AuthError('Floppy credentials changed; request cancelled.')
        if expected_identity is not None and state.get('generation') != expected_identity:
            raise AuthError('Floppy credentials changed; request cancelled.')
        if state.get('server') != base:
            raise AuthError('Floppy server changed. Please authorize this server again.')
        if state.get('reauth_required'):
            raise AuthError('Floppy authorization expired or was revoked. Please authorize again.')
        token = state.get('access_token')
        if failed_token and token != failed_token: return token
        if not failed_token and state.get('expires_at', 0) > time.time() + 60: return token
        try:
            response = _post(session, _root(base) + '/oauth/token', dict(
                client_id=state['client_id'], grant_type='refresh_token', refresh_token=state['refresh_token']))
        except requests.RequestException:
            # The server may have rotated the token before the response was lost.
            # Replaying an old refresh token can revoke the entire token family.
            state['reauth_required'] = True
            _save('floppy.oauth', state)
            control.setSetting('floppy.isauthed', '')
            raise AuthError('Floppy token refresh could not be confirmed. Please authorize again.')
        if response.status_code != 200:
            if _json(response).get('error') in ('invalid_grant', 'invalid_client', 'unauthorized_client'):
                state['reauth_required'] = True
                _save('floppy.oauth', state)
                control.setSetting('floppy.isauthed', '')
            raise AuthError('Unable to refresh Floppy authorization. Please check the connection or authorize again.')
        try:
            updated = _tokens(_json(response), base, state['client_id'], state.get('generation'))
        except (AuthError, ValueError, TypeError):
            state['reauth_required'] = True
            _save('floppy.oauth', state)
            control.setSetting('floppy.isauthed', '')
            raise AuthError('Floppy returned invalid refreshed credentials. Please authorize again.')
        _save('floppy.oauth', updated)
        return updated['access_token']
    finally:
        connection.close()


def begin(base, session):
    root = _root(base)
    response = session.get(root + '/.well-known/oauth-authorization-server', timeout=(10, 30), allow_redirects=False)
    metadata = _json(response)
    if response.status_code != 200 or DEVICE_GRANT not in metadata.get('grant_types_supported', []):
        raise AuthError('This Floppy server does not advertise OAuth device authorization. Update Floppy or use the API-key connection.')
    if not set(SCOPES.split()).issubset(metadata.get('scopes_supported', [])):
        raise AuthError('This Floppy server does not support all OAuth permissions required by Umbrella.')
    endpoints = {key: _endpoint(root, metadata.get(key) or '') for key in
                 ('registration_endpoint', 'device_authorization_endpoint', 'token_endpoint', 'revocation_endpoint')}
    try: client = _load('floppy.oauth.client')
    except AuthError: client = {}
    for attempt in range(2):
        if client.get('server') != base or not client.get('client_id'):
            response = _post(session, endpoints['registration_endpoint'], {'client_name': 'Umbrella'})
            data = _json(response)
            if response.status_code != 201 or not data.get('client_id'):
                raise AuthError('Unable to register Umbrella with Floppy. Please try again later.')
            client = dict(server=base, client_id=data['client_id'])
            _save('floppy.oauth.client', client)
        response = _post(session, endpoints['device_authorization_endpoint'], dict(client_id=client['client_id'], scope=SCOPES))
        device = _json(response)
        if response.status_code == 200: break
        if attempt == 0 and device.get('error') == 'invalid_client':
            client = {}
            continue
        raise AuthError('Unable to start Floppy authorization. Please try again later.')
    if not all(device.get(key) for key in ('device_code', 'user_code', 'verification_uri', 'expires_in')):
        raise AuthError('Floppy returned an incomplete device authorization.')
    _endpoint(root, device['verification_uri'])
    if device.get('verification_uri_complete'): _endpoint(root, device['verification_uri_complete'])
    return dict(base=base, client_id=client['client_id'], endpoints=endpoints, device=device)


def poll(flow, session):
    try:
        response = _post(session, flow['endpoints']['token_endpoint'], dict(
            client_id=flow['client_id'], grant_type=DEVICE_GRANT, device_code=flow['device']['device_code']))
    except requests.RequestException:
        return None, 'slow_down'
    data = _json(response)
    if response.status_code == 200:
        return _tokens(data, flow['base'], flow['client_id']), None
    error = data.get('error')
    if error in ('authorization_pending', 'slow_down'): return None, error
    if response.status_code == 429 or response.status_code >= 500: return None, 'slow_down'
    if error == 'access_denied': raise AuthError('Floppy authorization was declined.')
    if error in ('expired_token', 'invalid_grant'): raise AuthError('Floppy authorization expired. Please try again.')
    raise AuthError('Floppy authorization failed. Please try again later.')


def commit(state, session):
    # Verify the candidate before replacing a working API key or OAuth session.
    response = session.get(state['server'] + '/media/movie/?limit=1',
                           headers={'Authorization': 'Bearer ' + state['access_token']},
                           timeout=(10, 30), allow_redirects=False)
    if response.status_code != 200 or not isinstance(_json(response).get('results'), list):
        raise AuthError('Floppy could not validate the new authorization. Existing credentials were retained.')
    from resources.lib.database import floppysync
    if not floppysync.reset_for_authorization():
        raise AuthError('Floppy could not prepare the local cache. Existing credentials were retained.')
    _save('floppy.oauth', state)
    # Compatibility marker for existing provider selectors and settings. Refreshes
    # update the atomic OAuth record; they do not change this session marker.
    control.setSetting('floppy.token', state['access_token'])
    control.setSetting('floppy.user.name', '')
    control.setSetting('floppy.isauthed', 'true')
    control.make_settings_dict()


def identity():
    try: state = _load('floppy.oauth')
    except AuthError: return _setting('floppy.oauth')
    return state.get('generation') or _setting('floppy.token')


def authorize(base, session):
    dialog = control.progressDialog
    try:
        initial_identity = identity()
        flow = begin(base, session)
        device = flow['device']
        lifetime = int(device['expires_in'])
        expires = time.monotonic() + lifetime
        interval = max(5, int(device.get('interval') or 5))
        message = 'Visit %s\nEnter code: [B]%s[/B]' % (device['verification_uri'], device['user_code'])
        # OAuth approval should be scannable even when other custom dialogs are disabled.
        qr_dialog = None
        try:
            from resources.lib.modules import tools
            qr = tools.make_qr(device.get('verification_uri_complete') or device['verification_uri'], 'floppy_qr.png')
            if qr:
                qr_dialog = control.getProgressWindow('Umbrella - Floppy', qr, 1)
                qr_dialog.set_controls()
                qr_message = 'Scan the QR code or ' + message[0].lower() + message[1:]
                qr_dialog.update(0, qr_message)
                dialog, message = qr_dialog, qr_message
        except Exception:
            if qr_dialog is not None:
                try: qr_dialog.close()
                except Exception: pass
        if dialog is control.progressDialog:
            dialog.create('Umbrella - Floppy', message)
        while time.monotonic() < expires and not dialog.iscanceled():
            if control.monitor.waitForAbort(interval): return False
            if dialog.iscanceled(): return False
            state, error = poll(flow, session)
            if error == 'slow_down': interval += 5
            if state:
                connection = _lock()
                try:
                    raw_base = _setting('floppy.baseurl').strip().rstrip('/')
                    if raw_base and not raw_base.startswith(('http://', 'https://')): raw_base = 'https://' + raw_base
                    if raw_base and not raw_base.endswith('/api/v1'): raw_base += '/api/v1'
                    if raw_base != base or identity() != initial_identity:
                        raise AuthError('Floppy credentials changed during authorization. Please try again.')
                    if control.monitor.abortRequested() or dialog.iscanceled(): return False
                    commit(state, session)
                finally: connection.close()
                return True
            dialog.update(max(0, min(99, int(100 * (1 - (expires - time.monotonic()) / lifetime)))), message)
        return False
    finally:
        dialog.close()


def disconnect(session):
    connection = _lock()
    try:
        state = _load('floppy.oauth')
        if not state: return True
        response = _post(session, _root(state['server']) + '/oauth/revoke', dict(
            client_id=state['client_id'], token=state['refresh_token'], token_type_hint='refresh_token'))
        if response.status_code != 200 and _json(response).get('error') != 'invalid_client':
            raise AuthError('Floppy could not revoke this connection. Credentials were retained; please try again.')
        _save('floppy.oauth', {})
        return True
    finally:
        connection.close()
