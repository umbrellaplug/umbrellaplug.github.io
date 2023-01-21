'''
    common XBMC Module
    Copyright (C) 2011 t0mm0

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''
from six.moves import http_cookiejar
import gzip
import re
import six
from six.moves import urllib_request, urllib_parse
import socket
# Set Global timeout - Useful for slow connections and Putlocker.
socket.setdefaulttimeout(10)


class Net:
    _cj = http_cookiejar.LWPCookieJar()
    _proxy = None
    _user_agent = 'Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0'
    _http_debug = False

    def __init__(self, cookie_file='', proxy='', user_agent='', ssl_verify=True, http_debug=False):
        '''
        Kwargs:
            cookie_file (str): Full path to a file to be used to load and save
            cookies to.

            proxy (str): Proxy setting (eg.
            ``'https://user:pass@example.com:1234'``)

            user_agent (str): String to use as the User Agent header. If not
            supplied the class will use a default user agent (chrome)

            http_debug (bool): Set ``True`` to have HTTP header info written to
            the XBMC log for all requests.
        '''
        if cookie_file:
            self.set_cookies(cookie_file)
        if proxy:
            self.set_proxy(proxy)
        if user_agent:
            self.set_user_agent(user_agent)
        self._ssl_verify = ssl_verify
        self._http_debug = http_debug
        self._update_opener()

    def set_cookies(self, cookie_file):
        '''
        Set the cookie file and try to load cookies from it if it exists.

        Args:
            cookie_file (str): Full path to a file to be used to load and save
            cookies to.
        '''
        try:
            self._cj.load(cookie_file, ignore_discard=True)
            self._update_opener()
            return True
        except:
            return False

    def get_cookies(self, as_dict=False):
        '''Returns A dictionary containing all cookie information by domain.'''
        if as_dict:
            return dict((cookie.name, cookie.value) for cookie in self._cj)
        else:
            return self._cj._cookies

    def save_cookies(self, cookie_file):
        '''
        Saves cookies to a file.

        Args:
            cookie_file (str): Full path to a file to save cookies to.
        '''
        self._cj.save(cookie_file, ignore_discard=True)

    def set_proxy(self, proxy):
        '''
        Args:
            proxy (str): Proxy setting (eg.
            ``'https://user:pass@example.com:1234'``)
        '''
        self._proxy = proxy
        self._update_opener()

    def get_proxy(self):
        '''Returns string containing proxy details.'''
        return self._proxy

    def set_user_agent(self, user_agent):
        '''
        Args:
            user_agent (str): String to use as the User Agent header.
        '''
        self._user_agent = user_agent

    def get_user_agent(self):
        '''Returns user agent string.'''
        return self._user_agent

    def _update_opener(self):
        '''
        Builds and installs a new opener to be used by all future calls to
        :func:`urllib2.urlopen`.
        '''
        handlers = [urllib_request.HTTPCookieProcessor(self._cj), urllib_request.HTTPBasicAuthHandler()]

        if self._http_debug:
            handlers += [urllib_request.HTTPHandler(debuglevel=1)]
        else:
            handlers += [urllib_request.HTTPHandler()]

        if self._proxy:
            handlers += [urllib_request.ProxyHandler({'http': self._proxy})]

        try:
            import platform
            node = platform.node().lower()
        except:
            node = ''

        if not self._ssl_verify or node == 'xboxone':
            try:
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                if self._http_debug:
                    handlers += [urllib_request.HTTPSHandler(context=ctx, debuglevel=1)]
                else:
                    handlers += [urllib_request.HTTPSHandler(context=ctx)]
            except:
                pass

        opener = urllib_request.build_opener(*handlers)
        urllib_request.install_opener(opener)

    def http_GET(self, url, headers={}, compression=True):
        '''
        Perform an HTTP GET request.

        Args:
            url (str): The URL to GET.

        Kwargs:
            headers (dict): A dictionary describing any headers you would like
            to add to the request. (eg. ``{'X-Test': 'testing'}``)

            compression (bool): If ``True`` (default), try to use gzip
            compression.

        Returns:
            An :class:`HttpResponse` object containing headers and other
            meta-information about the page and the page content.
        '''
        return self._fetch(url, headers=headers, compression=compression)

    def http_POST(self, url, form_data, headers={}, compression=True):
        '''
        Perform an HTTP POST request.

        Args:
            url (str): The URL to POST.

            form_data (dict): A dictionary of form data to POST.

        Kwargs:
            headers (dict): A dictionary describing any headers you would like
            to add to the request. (eg. ``{'X-Test': 'testing'}``)

            compression (bool): If ``True`` (default), try to use gzip
            compression.

        Returns:
            An :class:`HttpResponse` object containing headers and other
            meta-information about the page and the page content.
        '''
        return self._fetch(url, form_data, headers=headers, compression=compression)

    def http_HEAD(self, url, headers={}):
        '''
        Perform an HTTP HEAD request.

        Args:
            url (str): The URL to GET.

        Kwargs:
            headers (dict): A dictionary describing any headers you would like
            to add to the request. (eg. ``{'X-Test': 'testing'}``)

        Returns:
            An :class:`HttpResponse` object containing headers and other
            meta-information about the page.
        '''
        request = urllib_request.Request(url)
        request.get_method = lambda: 'HEAD'
        request.add_header('User-Agent', self._user_agent)
        for key in headers:
            request.add_header(key, headers[key])
        response = urllib_request.urlopen(request)
        return HttpResponse(response)

    def http_DELETE(self, url, headers={}):
        '''
        Perform an HTTP DELETE request.

        Args:
            url (str): The URL to GET.

        Kwargs:
            headers (dict): A dictionary describing any headers you would like
            to add to the request. (eg. ``{'X-Test': 'testing'}``)

        Returns:
            An :class:`HttpResponse` object containing headers and other
            meta-information about the page.
        '''
        request = urllib_request.Request(url)
        request.get_method = lambda: 'DELETE'
        request.add_header('User-Agent', self._user_agent)
        for key in headers:
            request.add_header(key, headers[key])
        response = urllib_request.urlopen(request)
        return HttpResponse(response)

    def _fetch(self, url, form_data={}, headers={}, compression=True):
        '''
        Perform an HTTP GET or POST request.

        Args:
            url (str): The URL to GET or POST.

            form_data (dict): A dictionary of form data to POST. If empty, the
            request will be a GET, if it contains form data it will be a POST.

        Kwargs:
            headers (dict): A dictionary describing any headers you would like
            to add to the request. (eg. ``{'X-Test': 'testing'}``)

            compression (bool): If ``True`` (default), try to use gzip
            compression.

        Returns:
            An :class:`HttpResponse` object containing headers and other
            meta-information about the page and the page content.
        '''
        req = urllib_request.Request(url)
        if form_data:
            if isinstance(form_data, six.string_types):
                form_data = form_data
            else:
                form_data = urllib_parse.urlencode(form_data, True)
            form_data = form_data.encode('utf-8') if six.PY3 else form_data
            req = urllib_request.Request(url, form_data)
        req.add_header('User-Agent', self._user_agent)
        for key in headers:
            req.add_header(key, headers[key])
        if compression:
            req.add_header('Accept-Encoding', 'gzip')
        host = req.host if six.PY3 else req.get_host()
        req.add_unredirected_header('Host', host)
        response = urllib_request.urlopen(req, timeout=15)
        return HttpResponse(response)


class HttpResponse:
    '''
    This class represents a resoponse from an HTTP request.

    The content is examined and every attempt is made to properly encode it to
    Unicode.

    .. seealso::
        :meth:`Net.http_GET`, :meth:`Net.http_HEAD` and :meth:`Net.http_POST`
    '''

    # content = ''
    '''Unicode encoded string containing the body of the reponse.'''

    def __init__(self, response):
        '''
        Args:
            response (:class:`mimetools.Message`): The object returned by a call
            to :func:`urllib2.urlopen`.
        '''
        self._response = response

    @property
    def content(self):
        html = self._response.read()
        encoding = None
        try:
            if self._response.headers['content-encoding'].lower() == 'gzip':
                html = gzip.GzipFile(fileobj=six.BytesIO(html)).read()
        except:
            pass

        try:
            content_type = self._response.headers['content-type']
            if 'charset=' in content_type:
                encoding = content_type.split('charset=')[-1]
        except:
            pass

        if encoding is None:
            epattern = r'<meta\s+http-equiv="Content-Type"\s+content="(?:.+?);\s+charset=(.+?)"'
            epattern = epattern.encode('utf8') if six.PY3 else epattern
            r = re.search(epattern, html, re.IGNORECASE)
            if r:
                encoding = r.group(1).decode('utf8') if six.PY3 else r.group(1)

        if encoding is not None:
            html = html.decode(encoding, errors='ignore')
        else:
            html = html.decode('ascii', errors='ignore') if six.PY3 else html
        return html

    def get_headers(self, as_dict=False):
        '''Returns headers returned by the server.
        If as_dict is True, headers are returned as a dictionary otherwise a list'''
        if as_dict:
            return dict([(item[0].title(), item[1]) for item in list(self._response.info().items())])
        else:
            return self._response.info()._headers

    def get_url(self):
        '''
        Return the URL of the resource retrieved, commonly used to determine if
        a redirect was followed.
        '''
        return self._response.geturl()
