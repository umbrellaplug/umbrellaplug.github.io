# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from re import findall as re_findall
import requests
from requests.adapters import HTTPAdapter
from threading import Thread
from urllib3.util.retry import Retry
from urllib.parse import quote_plus
from resources.lib.database import cache, metacache, fanarttv_cache
from resources.lib.indexers.tmdb import TVshows as tmdb_indexer
from resources.lib.indexers.fanarttv import FanartTv
from resources.lib.modules import client
from resources.lib.modules.control import notification, sleep, apiLanguage, setting as getSetting
from resources.lib.modules import trakt

base_link = 'https://api.tvmaze.com'
info_link = 'https://api.tvmaze.com/shows/%s?embed=cast'

session = requests.Session()
retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
session.mount('https://api.tvmaze.com', HTTPAdapter(max_retries=retries, pool_maxsize=100))


class TVMaze:
	def __init__(self):
		self.lang = apiLanguage()['tvdb']

	def get_request(self,url): # API calls are rate limited to allow at least 20 calls every 10 seconds per IP address
		try:
			try:
				response = session.get(url, timeout=20)
			except requests.exceptions.SSLError:
				response = session.get(url, verify=False)
		except requests.exceptions.ConnectionError:
			return notification(message=32024)
		if response.status_code in (200, 201): return response.json()
		elif response.status_code == 404:
			if getSetting('debug.level') == '1':
				from resources.lib.modules import log_utils
				log_utils.log('TVMAZE get_request() failed: (404:NOT FOUND) - URL: %s' % url, __name__, level=log_utils.LOGDEBUG)
		elif 'Retry-After' in response.headers: # API REQUESTS ARE BEING THROTTLED, INTRODUCE WAIT TIME
			throttleTime = response.headers['Retry-After']
			notification(message='TVMAZE Throttling Applied, Sleeping for %s seconds' % throttleTime)
			sleep((int(throttleTime) + 1) * 1000)
			return self.get_request(url)
		else:
			if getSetting('debug.level') == '1':
				from resources.lib.modules import log_utils
				log_utils.log('TVMaze get_request() failed: URL: %s\n                       msg : TVMaze Response: %s' % (
					url, response.text), __name__, log_utils.LOGDEBUG)
			return None


class TVshows(TVMaze):
	def __init__(self):
		TVMaze.__init__(self)
		last = []
		self.count = 40
		self.list = []
		self.meta = []
		self.threads = []
		self.tvdb_key = getSetting('tvdb.apikey')
		self.imdb_user = getSetting('imdbuser').replace('ur', '')
		self.user = str(self.imdb_user) + str(self.tvdb_key)
		self.enable_fanarttv = getSetting('enable.fanarttv') == 'true'

	def tvmaze_list(self, url):
		try:
			result = client.request(url) # not json request
			next = ''
			if getSetting('tvshows.networks.view') == '0':
				result = client.parseDOM(result, 'section', attrs = {'id': 'this-seasons-shows'})
				items = client.parseDOM(result, 'span', attrs = {'class': 'title .*'})
				list_count = 60
			elif getSetting('tvshows.networks.view') == '1':
				result = client.parseDOM(result, 'div', attrs = {'id': 'w1'})
				items = client.parseDOM(result, 'span', attrs = {'class': 'title'})
				list_count = 25
				page = int(str(url.split('&page=', 1)[1]))
				next = '%s&page=%s' % (url.split('&page=', 1)[0], page+1)
				last = []
				last = client.parseDOM(result, 'li', attrs = {'class': 'last disabled'})
				if last != []: next = ''
			items = [client.parseDOM(i, 'a', ret='href') for i in items]
			items = [i[0] for i in items if len(i) > 0]
			items = [re_findall(r'/(\d+)/', i) for i in items] #https://www.tvmaze.com/networks/645/tlc pulls tvmaze_id from link
			items = [i[0] for i in items if len(i) > 0]
			items = items[:list_count]
			sortList = items
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
			return

		def items_list(tvmaze_id):
			# if i['metacache']: return # not possible with only a tvmaze_id
			try:
				values = {}
				values['next'] = next
				values['tvmaze'] = tvmaze_id
				url = info_link % tvmaze_id
				item = self.get_request(url) 
				values['content'] = item.get('type', '').lower()
				values['mediatype'] = 'tvshow'
				values['title'] = item.get('name')
				values['originaltitle'] = values['title']
				values['tvshowtitle'] = values['title']
				values['premiered'] = str(item.get('premiered', '')) if item.get('premiered') else ''
				try: values['year'] = values['premiered'][:4]
				except: values['year'] = ''
				ids = item.get('externals')
				imdb = str(ids.get('imdb', '')) if ids.get('imdb') else ''
				tvdb = str(ids.get('thetvdb', '')) if ids.get('thetvdb') else ''
				tmdb = '' # TVMaze does not have tmdb_id in api
				studio = item.get('network', {}) or item.get('webChannel', {})
				values['studio'] = studio.get('name', '')
				values['genre'] = []
				for i in item['genres']: values['genre'].append(i.title())
				if values['genre'] == []: values['genre'] = 'NA'
				values['duration'] = int(item.get('runtime', '')) * 60 if item.get('runtime') else ''
				values['rating'] = str(item.get('rating').get('average', '')) if item.get('rating').get('average') else ''
				values['plot'] = client.cleanHTML(item['summary'])
				values['status'] = item.get('status', '')
				values['castandart'] = []
				for person in item['_embedded']['cast']:
					try: values['castandart'].append({'name': person['person']['name'], 'role': person['character']['name'], 'thumbnail': (person['person']['image']['medium'] if person['person']['image']['medium'] else '')})
					except: pass
					if len(values['castandart']) == 150: break
				image = item.get('image', {}) or ''
				values['poster'] = image.get('original', '') if image else ''
				values['fanart'] = '' ; values['banner'] = ''
				values['mpaa'] = '' ; values['votes'] = ''
				try: values['airday'] = item['schedule']['days'][0]
				except: values['airday'] = ''
				values['airtime'] = item['schedule']['time'] or ''
				try: values['airzone'] = item['network']['country']['timezone']
				except: values['airzone'] = ''
				values['metacache'] = False 

#### -- Missing id's lookup -- ####
				if not tmdb and (imdb or tvdb):
					try:
						result = cache.get(tmdb_indexer().IdLookup, 168, imdb, tvdb)
						tmdb = str(result.get('id', '')) if result.get('id') else ''
					except: tmdb = ''
				if not imdb or not tmdb or not tvdb:
					try:
						trakt_ids = trakt.SearchTVShow(quote_plus(values['tvshowtitle']), values['year'], full=False)
						if not trakt_ids: raise Exception
						ids = trakt_ids[0].get('show', {}).get('ids', {})
						if not imdb: imdb = str(ids.get('imdb', '')) if ids.get('imdb') else ''
						if not tmdb: tmdb = str(ids.get('tmdb', '')) if ids.get('tmdb') else ''
						if not tvdb: tvdb = str(ids.get('tvdb', '')) if ids.get('tvdb') else ''
					except:
						log_utils.error()
#################################
				if not tmdb:
					return log_utils.log('tvshowtitle: (%s) missing tmdb_id: ids={imdb: %s, tmdb: %s, tvdb: %s}' % (values['tvshowtitle'], imdb, tmdb, tvdb), __name__, log_utils.LOGDEBUG) # log TMDb shows that they do not have
				# self.list = metacache.fetch(self.list, self.lang, self.user)
				# if self.list['metacache'] is True: raise Exception()

				showSeasons = cache.get(tmdb_indexer().get_showSeasons_meta, 96, tmdb)
				if not showSeasons: return
				showSeasons = dict((k, v) for k, v in iter(showSeasons.items()) if v is not None and v != '') # removes empty keys so .update() doesn't over-write good meta
				values.update(showSeasons)
				if not values.get('imdb'): values['imdb'] = imdb
				if not values.get('tmdb'): values['tmdb'] = tmdb
				if not values.get('tvdb'): values['tvdb'] = tvdb
				for k in ('seasons',): values.pop(k, None) # pop() keys from showSeasons that are not needed anymore
				if self.enable_fanarttv:
					extended_art = fanarttv_cache.get(FanartTv().get_tvshow_art, 336, tvdb)
					if extended_art: values.update(extended_art)
				meta = {'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'lang': self.lang, 'user': self.user, 'item': values} # DO NOT move this after "values = dict()" below or it becomes the same object and "del meta['item']['next']" removes it from both
				values = dict((k,v) for k, v in iter(values.items()) if v is not None and v != '')
				self.list.append(values)
				if 'next' in meta.get('item'): del meta['item']['next'] # next can not exist in metacache
				self.meta.append(meta)
				self.meta = [i for i in self.meta if i.get('tmdb')] # without this ui removed missing tmdb but it still writes these cases to metacache?
				metacache.insert(self.meta)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		try:
			threads = []
			append = threads.append
			for tvmaze_id in items:
				append(Thread(target=items_list, args=(tvmaze_id,)))
			[i.start() for i in threads]
			[i.join() for i in threads]
			sorted_list = []
			self.list = [i for i in self.list if i.get('tmdb') and i.get('tmdb') != '0'] # to rid missing tmdb_id's because season list can not load without
			for i in sortList:
				sorted_list += [item for item in self.list if str(item['tvmaze']) == str(i)]
			return sorted_list
		except:
			log_utils.error()
			return

	def show_lookup(self, tvdb):
		url = '%s%s' % (base_link, '/lookup/shows?thetvdb=%s' % tvdb)
		response = self.get_request(url)
		return response['id']

	def get_full_series(self, tvmaze):
		url = '%s%s' % (base_link, '/shows/%s?embed[]=seasons&embed[]=episodes&embed[]=cast&embed[]=images' % tvmaze)
		response = self.get_request(url)
		return response

	def get_networks_thisSeason(self):
		return [
			('A&E', '/networks/29/ae', 'https://i.imgur.com/xLDfHjH.png'),
			('ABC', '/networks/3/abc', 'https://i.imgur.com/qePLxos.png'),
			('Acorn TV', '/webchannels/129/acorn-tv', 'https://i.imgur.com/YMtys7n.png'),
			('Adult Swim', '/networks/10/adult-swim', 'https://i.imgur.com/jCqbRcS.png'),
			('Amazon', '/webchannels/3/amazon', 'https://i.imgur.com/ru9DDlL.png'),
			('AMC', '/networks/20/amc', 'https://i.imgur.com/ndorJxi.png'),
			('Animal Planet', '/networks/92/animal-planet', 'https://i.imgur.com/olKc4RP.png'),
			('Apple TV+', '/webchannels/310/apple-tv', 'https://i.imgur.com/HjEYPad.png'),
			('AT-X', '/networks/167/at-x', 'https://i.imgur.com/JshJYGN.png'),
			('Audience', '/networks/31/audience-network', 'https://i.imgur.com/5Q3mo5A.png'),
			('BBC America', '/networks/15/bbc-america', 'https://i.imgur.com/TUHDjfl.png'),
			('BBC One', '/networks/12/bbc-one', 'https://i.imgur.com/u8x26te.png'),
			('BBC Two', '/networks/37/bbc-two', 'https://i.imgur.com/SKeGH1a.png'),
			('BBC Three', '/webchannels/71/bbc-three', 'https://i.imgur.com/SDLeLcn.png'),
			('BBC Four', '/networks/51/bbc-four', 'https://i.imgur.com/PNDalgw.png'),
			('BET', '/networks/56/bet', 'https://i.imgur.com/ZpGJ5UQ.png'),
			('Blackpills', '/webchannels/186/blackpills', 'https://i.imgur.com/8zzNqqq.png'),
			('Brat', '/webchannels/274/brat', 'https://i.imgur.com/x2aPEx1.png'),
			('Bravo', '/networks/52/bravo', 'https://i.imgur.com/TmEO3Tn.png'),
			('Cartoon Network', '/networks/11/cartoon-network', 'https://i.imgur.com/zmOLbbI.png'),
			('CBC', '/networks/36/cbc', 'https://i.imgur.com/unQ7WCZ.png'),
			('CBS', '/networks/2/cbs', 'https://i.imgur.com/8OT8igR.png'),
			('Channel 4', '/networks/45/channel-4', 'https://i.imgur.com/6ZA9UHR.png'),
			('Channel 5', '/networks/135/channel-5', 'https://i.imgur.com/5ubnvOh.png'),
			('Cinemax', '/networks/19/cinemax', 'https://i.imgur.com/zWypFNI.png'),
			('CNBC', '/networks/93/cnbc', 'https://i.imgur.com/ENjlkvv.png'),
			('Comedy Central', '/networks/23/comedy-central', 'https://i.imgur.com/ko6XN77.png'),
			('Crackle', '/webchannels/4/crackle', 'https://i.imgur.com/53kqZSY.png'),
			('CTV', '/networks/48/ctv', 'https://i.imgur.com/qUlyVHz.png'),
			('CuriosityStream', '/webchannels/188/curiositystream', 'https://i.imgur.com/5wJsQdi.png'),
			('CW', '/networks/5/the-cw', 'https://i.imgur.com/Q8tooeM.png'),
			('CW Seed', '/webchannels/13/cw-seed', 'https://i.imgur.com/nOdKoEy.png'),
			('DC Universe', '/webchannels/187/dc-universe', 'https://i.imgur.com/bhWIubn.png'),
			('Discovery Channel', '/networks/66/discovery-channel', 'https://i.imgur.com/8UrXnAB.png'),
			('Discovery ID', '/networks/89/investigation-discovery', 'https://i.imgur.com/07w7BER.png'),
			('Disney+', '/webchannels/287/disney', 'https://i.postimg.cc/SQ8fG2qF/435560.jpg'),
			('Disney Channel', '/networks/78/disney-channel', 'https://i.imgur.com/ZCgEkp6.png'),
			('Disney Junior', '/networks/1039/disney-junior', 'https://i.imgur.com/EqPPq5S.png'),
			('Disney XD', '/networks/25/disney-xd', 'https://i.imgur.com/PAJJoqQ.png'),
			('E! Entertainment', '/networks/43/e', 'https://i.imgur.com/3Delf9f.png'),
			('E4', '/networks/41/e4', 'https://i.imgur.com/frpunK8.png'),
			('Epix', '/networks/253/epix', 'https://i.postimg.cc/3JMv8Q1g/epix.png'),
			# ('Fearnet', '/networks/466/fearnet', 'https://i.imgur.com/CdJ6fZt.png'),
			('FOX', '/networks/4/fox', 'https://i.imgur.com/6vc0Iov.png'),
			('Freeform', '/networks/26/freeform', 'https://i.imgur.com/f9AqoHE.png'),
			('Fusion', '/networks/187/fusion', 'https://i.imgur.com/NPxic1M.png'),
			('FX', '/networks/13/fx', 'https://i.imgur.com/aQc1AIZ.png'),
			('Hallmark', '/networks/50/hallmark-channel', 'https://i.imgur.com/zXS64I8.png'),
			# ('Hallmark Movies & Mysteries', '/networks/252/hallmark-movies-mysteries', 'https://static.tvmaze.com/uploads/images/original_untouched/13/34664.jpg'),
			('HBO', '/networks/8/hbo', 'https://i.imgur.com/Hyu8ZGq.png'),
			('HGTV', '/networks/192/hgtv', 'https://i.imgur.com/INnmgLT.png'),
			('History Channel', '/networks/53/history', 'https://i.imgur.com/LEMgy6n.png'),
			# ('H2', '/networks/74/h2', 'https://i.imgur.com/OvkmoDA.png'),
			('Hulu', '/webchannels/2/hulu', 'https://i.imgur.com/gvHOZgC.png'),
			('ITV', '/networks/35/itv', 'https://i.imgur.com/5Hxp5eA.png'),
			('Lifetime', '/networks/18/lifetime', 'https://i.imgur.com/tvYbhen.png'),
			('MTV', '/networks/22/mtv', 'https://i.imgur.com/QM6DpNW.png'),
			('National Geographic', '/networks/42/national-geographic-channel', 'https://i.imgur.com/XCGNKVQ.png'),
			('NBC', '/networks/1/nbc', 'https://i.imgur.com/yPRirQZ.png'),
			('Netflix', '/webchannels/1/netflix', 'https://i.postimg.cc/c4vHp9wV/netflix.png'),
			('Nickelodeon', '/networks/27/nickelodeon', 'https://i.imgur.com/OUVoqYc.png'),
			('Nicktoons', '/networks/73/nicktoons', 'https://i.imgur.com/890wBrw.png'),
			('Oxygen', '/networks/79/oxygen', 'https://i.imgur.com/uFCQvbR.png'),
			('Paramount Network', '/networks/34/paramount-network', 'https://i.postimg.cc/fL9YCz5R/paramount-network.png'),
			('PBS', '/networks/85/pbs', 'https://i.imgur.com/r9qeDJY.png'),
			# ('Playboy TV', '/networks/1035/playboy-tv', 'https://i.postimg.cc/sxVWPpL3/playboy-tv.png'),
			('Showcase', '/networks/270/showcase', 'https://i.postimg.cc/CKN3Ph8S/66074.jpg'),
			('Showtime', '/networks/9/showtime', 'https://i.imgur.com/SawAYkO.png'),
			('Sky1', '/networks/63/sky-1', 'https://i.imgur.com/xbgzhPU.png'),
			('Starz', '/networks/17/starz', 'https://i.imgur.com/Z0ep2Ru.png'),
			('Sundance', '/networks/33/sundance-tv', 'https://i.imgur.com/qldG5p2.png'),
			('Syfy', '/networks/16/syfy', 'https://i.imgur.com/9yCq37i.png'),
			('TBS', '/networks/32/tbs', 'https://i.imgur.com/RVCtt4Z.png'),
			('TLC', '/networks/80/tlc', 'https://i.imgur.com/c24MxaB.png'),
			('TNT', '/networks/14/tnt', 'https://i.imgur.com/WnzpAGj.png'),
			('Travel Channel', '/networks/82/travel-channel', 'https://i.imgur.com/mWXv7SF.png'),
			('TruTV', '/networks/84/trutv', 'https://i.imgur.com/HnB3zfc.png'),
			('TV Land', '/networks/57/tvland', 'https://i.imgur.com/1nIeDA5.png'),
			('TV One', '/networks/224/tv-one', 'https://i.imgur.com/gGCTa8s.png'),
			('USA', '/networks/30/usa-network', 'https://i.imgur.com/Doccw9E.png'),
			('VH1', '/networks/55/vh1', 'https://i.imgur.com/IUtHYzA.png'),
			('Viceland', '/networks/1006/viceland', 'https://i.imgur.com/sLNNqEY.png'),
			('WGN', '/networks/28/wgn-america', 'https://i.imgur.com/TL6MzgO.png'),
			('WWE Network', '/webchannels/15/wwe-network', 'https://i.imgur.com/JjbTbb2.png'),
			('YouTube Premium', '/webchannels/43/youtube-premium', 'https://i.postimg.cc/vHtqdhyt/youtube-premium.png')]

	def get_networks_viewAll(self):
		return [
			('A&E', '/shows?Show[network_id]=29&page=1', 'https://i.imgur.com/xLDfHjH.png'),
			('ABC', '/shows?Show[network_id]=3&page=1', 'https://i.imgur.com/qePLxos.png'),
			('Acorn TV', '/shows?Show[network_id]=129&page=1', 'https://i.imgur.com/YMtys7n.png'),
			('Adult Swim', '/shows?Show[network_id]=10&page=1', 'https://i.imgur.com/jCqbRcS.png'),
			('Amazon', '/shows?Show[webChannel_id]=3&page=1', 'https://i.imgur.com/ru9DDlL.png'),
			('AMC', '/shows?Show[network_id]=20&page=1', 'https://i.imgur.com/ndorJxi.png'),
			('Animal Planet', '/shows?Show[network_id]=92&page=1', 'https://i.imgur.com/olKc4RP.png'),
			('Apple TV+', '/shows?Show[webChannel_id]=310&page=1', 'https://i.imgur.com/HjEYPad.png'),
			('AT-X', '/shows?Show[network_id]=167&page=1', 'https://i.imgur.com/JshJYGN.png'),
			('Audience', '/shows?Show[network_id]=31&page=1', 'https://i.imgur.com/5Q3mo5A.png'),
			('BBC America', '/shows?Show[network_id]=15&page=1', 'https://i.imgur.com/TUHDjfl.png'),
			('BBC One', '/shows?Show[network_id]=12&page=1', 'https://i.imgur.com/u8x26te.png'),
			('BBC Two', '/shows?Show[network_id]=37&page=1', 'https://i.imgur.com/SKeGH1a.png'),
			('BBC Three', '/shows?Show[network_id]=71&page=1', 'https://i.imgur.com/SDLeLcn.png'),
			('BBC Four', '/shows?Show[network_id]=51&page=1', 'https://i.imgur.com/PNDalgw.png'),
			('BET', '/shows?Show[network_id]=56&page=1', 'https://i.imgur.com/ZpGJ5UQ.png'),
			('Blackpills', '/shows?Show[webChannel_id]=186&page=1', 'https://i.imgur.com/8zzNqqq.png'),
			('Brat', '/shows?Show[webChannel_id]=274&page=1', 'https://i.imgur.com/x2aPEx1.png'),
			('Bravo', '/shows?Show[network_id]=52&page=1', 'https://i.imgur.com/TmEO3Tn.png'),
			('Cartoon Network', '/shows?Show[network_id]=11&page=1', 'https://i.imgur.com/zmOLbbI.png'),
			('CBC', '/shows?Show[network_id]=36&page=1', 'https://i.imgur.com/unQ7WCZ.png'),
			('CBS', '/shows?Show[network_id]=2&page=1', 'https://i.imgur.com/8OT8igR.png'),
			# ('CBS All Access', '1709', 'https://i.imgur.com/ZvaWMuU.png'),
			('CNBC', '/shows?Show[network_id]=93&page=1', 'https://i.imgur.com/ENjlkvv.png'),
			('Channel 4', '/shows?Show[network_id]=45&page=1', 'https://i.imgur.com/6ZA9UHR.png'),
			('Channel 5', '/shows?Show[network_id]=135&page=1', 'https://i.imgur.com/5ubnvOh.png'),
			('Cinemax', '/shows?Show[network_id]=19&page=1', 'https://i.imgur.com/zWypFNI.png'),
			('Comedy Central', '/shows?Show[network_id]=23&page=1', 'https://i.imgur.com/ko6XN77.png'),
			('Crackle', '/shows?Show%5BwebChannel_id%5D=4&page=1', 'https://i.imgur.com/53kqZSY.png'),
			('CTV', '/shows?Show[network_id]=48&page=1', 'https://i.imgur.com/qUlyVHz.png'),
			('CuriosityStream', '/shows?Show[webChannel_id]=188&page=1', 'https://i.imgur.com/5wJsQdi.png'),
			('CW', '/shows?Show[network_id]=5&page=1', 'https://i.imgur.com/Q8tooeM.png'),
			('CW Seed', '/shows?Show[webChannel_id]=13&page=1', 'https://i.imgur.com/nOdKoEy.png'),
			('DC Universe', '/shows?Show%5BwebChannel_id%5D=187&page=1', 'https://i.imgur.com/bhWIubn.png'),
			('Discovery Channel', '/shows?Show[network_id]=66&page=1', 'https://i.imgur.com/8UrXnAB.png'),
			('Discovery ID', '/shows?Show[network_id]=89&page=1', 'https://i.imgur.com/07w7BER.png'),
			('Disney+', '/shows?Show[webChannel_id]=287&page=1', 'https://i.postimg.cc/zBNHHbKZ/disney.png'),
			('Disney Channel', '/shows?Show[network_id]=78&page=1', 'https://i.imgur.com/ZCgEkp6.png'),
			('Disney Junior', '/shows?Show[network_id]=1039&page=1', 'https://i.imgur.com/EqPPq5S.png'),
			('Disney XD', '/shows?Show[network_id]=25&page=1', 'https://i.imgur.com/PAJJoqQ.png'),
			('E! Entertainment', '/shows?Show[network_id]=43&page=1', 'https://i.imgur.com/3Delf9f.png'),
			('E4', '/shows?Show[network_id]=41&page=1', 'https://i.imgur.com/frpunK8.png'),
			('Epix', '/shows?Show[network_id]=253&page=1', 'https://i.postimg.cc/3JMv8Q1g/epix.png'),
			('Fearnet', '/shows?Show[network_id]=466&page=1', 'https://i.imgur.com/CdJ6fZt.png'),
			('FOX', '/shows?Show[network_id]=4&page=1', 'https://i.imgur.com/6vc0Iov.png'),
			('Freeform', '/shows?Show[network_id]=26&page=1', 'https://i.imgur.com/f9AqoHE.png'),
			('Fusion', '/shows?Show[network_id]=187&page=1', 'https://i.imgur.com/NPxic1M.png'),
			('FX', '/shows?Show[network_id]=13&page=1', 'https://i.imgur.com/aQc1AIZ.png'),
			('Hallmark', '/shows?Show[network_id]=50&page=1', 'https://i.imgur.com/zXS64I8.png'),
			('Hallmark Movies & Mysteries', '/shows?Show[network_id]=252&page=1', 'https://static.tvmaze.com/uploads/images/original_untouched/13/34664.jpg'),
			('HBO', '/shows?Show[network_id]=8&page=1', 'https://i.imgur.com/Hyu8ZGq.png'),
			# ('HBO Max', '3186', 'https://i.imgur.com/mmRMG75.png'),
			('HGTV', '/shows?Show[network_id]=192&page=1', 'https://i.imgur.com/INnmgLT.png'),
			('History Channel', '/shows?Show[network_id]=53&page=1', 'https://i.imgur.com/LEMgy6n.png'),
			('H2', '/shows?Show[network_id]=74&page=1', 'https://i.imgur.com/OvkmoDA.png'),
			('Hulu', '/shows?Show[webChannel_id]=2&page=1', 'https://i.imgur.com/gvHOZgC.png'),
			('ITV', '/shows?Show[network_id]=35&page=1', 'https://i.imgur.com/5Hxp5eA.png'),
			('Lifetime', '/shows?Show[network_id]=18&page=1', 'https://i.imgur.com/tvYbhen.png'),
			('MTV', '/shows?Show[network_id]=22&page=1', 'https://i.imgur.com/QM6DpNW.png'),
			('National Geographic', '/shows?Show[network_id]=42&page=1', 'https://i.imgur.com/XCGNKVQ.png'),
			('NBC', '/shows?Show[network_id]=1&page=1', 'https://i.imgur.com/yPRirQZ.png'),
			('Netflix', '/shows?Show[webChannel_id]=1&page=1', 'https://i.postimg.cc/c4vHp9wV/netflix.png'),
			# ('Nick Junior', '35', 'https://i.imgur.com/leuCWYt.png'),
			('Nickelodeon', '/shows?Show[network_id]=27&page=1', 'https://i.imgur.com/OUVoqYc.png'),
			('Nicktoons', '/shows?Show[network_id]=73&page=1', 'https://i.imgur.com/890wBrw.png'),
			('Oxygen', '/shows?Show[network_id]=79&page=1', 'https://i.imgur.com/uFCQvbR.png'),
			# ('Playboy TV', '/shows?Show[network_id]=1035&page=1', 'https://i.postimg.cc/sxVWPpL3/playboy-tv.png'),
			('Paramount Network', '/shows?Show[network_id]=34&page=1', 'https://i.postimg.cc/fL9YCz5R/paramount-network.png'),
			('PBS', '/shows?Show[network_id]=85&page=1', 'https://i.imgur.com/r9qeDJY.png'),
			('Showcase', '/shows?Show[network_id]=270&page=1', 'https://i.postimg.cc/CKN3Ph8S/66074.jpg'),
			('Showtime', '/shows?Show[network_id]=9&page=1', 'https://i.imgur.com/SawAYkO.png'),
			('Sky1', '/shows?Show[network_id]=63&page=1', 'https://i.imgur.com/xbgzhPU.png'),
			# ('Sky Atlantic', '1063', 'https://i.imgur.com/9u6M0ef.png'),
			# ('Spike', '55', 'https://i.imgur.com/BhXYytR.png'),
			('Starz', '/shows?Show[network_id]=17&page=1', 'https://i.imgur.com/Z0ep2Ru.png'),
			('Sundance', '/shows?Show[network_id]=33&page=1', 'https://i.imgur.com/qldG5p2.png'),
			('Syfy', '/shows?Show[network_id]=16&page=1', 'https://i.imgur.com/9yCq37i.png'),
			('TBS', '/shows?Show[network_id]=32&page=1', 'https://i.imgur.com/RVCtt4Z.png'),
			('TLC', '/shows?Show[network_id]=80&page=1', 'https://i.imgur.com/c24MxaB.png'),
			('TNT', '/shows?Show[network_id]=14&page=1', 'https://i.imgur.com/WnzpAGj.png'),
			('Travel Channel', '/shows?Show[network_id]=82&page=1', 'https://i.imgur.com/mWXv7SF.png'),
			('TruTV', '/shows?Show[network_id]=84&page=1', 'https://i.imgur.com/HnB3zfc.png'),
			('TV Land', '/shows?Show[network_id]=57&page=1', 'https://i.imgur.com/1nIeDA5.png'),
			('TV One', '/shows?Show[network_id]=224&page=1', 'https://i.imgur.com/gGCTa8s.png'),
			('USA Network', '/shows?Show[network_id]=30&page=1', 'https://i.imgur.com/Doccw9E.png'),
			('VH1', '/shows?Show[network_id]=55&page=1', 'https://i.imgur.com/IUtHYzA.png'),
			('Viceland', '/shows?Show[network_id]=1006&page=1', 'https://i.imgur.com/sLNNqEY.png'),
			# ('WB', '21', 'https://i.imgur.com/rzfVME6.png'),
			('WGN America', '/shows?Show[network_id]=28&page=1', 'https://i.imgur.com/TL6MzgO.png'),
			('WWE Network', '/shows?Show[webChannel_id]=15&page=1', 'https://i.imgur.com/JjbTbb2.png'),
			# ('YouTube', '/webchannels/21/youtube', 'https://i.imgur.com/ZfewP1Y.png'),
			('YouTube Premium', '/shows?Show[webChannel_id]=43&page=1', 'https://i.postimg.cc/vHtqdhyt/youtube-premium.png')]

	def original_thisSeason(self):
		return [
			('Amazon', '/webchannels/3/amazon', 'https://i.imgur.com/ru9DDlL.png'),
			('Hulu', '/webchannels/2/hulu', 'https://i.imgur.com/gvHOZgC.png'),
			('Netflix', '/webchannels/1/netflix', 'https://i.postimg.cc/c4vHp9wV/netflix.png')]

	def originals_viewAll(self):
		return [
			('Amazon', '/shows?Show[webChannel_id]=3&page=1', 'https://i.imgur.com/ru9DDlL.png'),
			('Hulu', '/shows?Show[webChannel_id]=2&page=1', 'https://i.imgur.com/gvHOZgC.png'),
			('Netflix', '/shows?Show[webChannel_id]=1&page=1', 'https://i.postimg.cc/c4vHp9wV/netflix.png')]