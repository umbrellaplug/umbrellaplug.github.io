# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from json import loads as jsloads
import re
from threading import Thread
from resources.lib.modules import client


class youtube(object):
	def __init__(self, key=''):
		self.list = []
		self.data = []
		self.base_link = 'https://www.youtube.com'
		self.key_link = '&key=%s' % key
		self.playlists_link = 'https://www.googleapis.com/youtube/v3/playlists?part=snippet&maxResults=50&channelId=%s'
		self.playlist_link = 'https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=50&playlistId=%s'
		self.videos_link = 'https://www.googleapis.com/youtube/v3/search?part=snippet&order=date&maxResults=50&channelId=%s'
		self.content_link = 'https://www.googleapis.com/youtube/v3/videos?part=contentDetails&id=%s'
		self.play_link = 'plugin://plugin.video.youtube/play/?video_id=%s'

	def playlists(self, url):
		url = self.playlists_link % url + self.key_link
		return self.play_list(url)

	def playlist(self, url, pagination=False):
		cid = url.split('&')[0]
		url = self.playlist_link % url + self.key_link
		return self.video_list(cid, url, pagination)

	def videoseries(self, url, pagination=False):
		lid = url.split('list=')[1]
		url = self.playlist_link % lid + self.key_link
		return self.video_list(lid, url, pagination)

	def videos(self, url, pagination=False):
		cid = url.split('&')[0]
		url = self.videos_link % url + self.key_link
		return self.video_list(cid, url, pagination)

	def play_list(self, url):
		try:
			result = client.request(url)
			result = jsloads(result)
			items = result['items']
		except: pass

		for i in range(1, 5):
			try:
				if 'nextPageToken' not in result: raise Exception()
				next = url + '&pageToken=' + result['nextPageToken']
				result = client.request(next)
				result = jsloads(result)
				items += result['items']
			except: pass

		for item in items:
			try:
				title = item['snippet']['title']
				url = item['id']
				image = item['snippet']['thumbnails']['high']['url']
				if '/default.jpg' in image: raise Exception()
				image = image
				self.list.append({'title': title, 'url': url, 'image': image})
			except: pass
		return self.list

	def video_list(self, cid, url, pagination):
		try:
			result = client.request(url)
			result = jsloads(result)
			items = result['items']
		except: pass
		for i in range(1, 5):
			try:
				if pagination: raise Exception()
				if 'nextPageToken' not in result: raise Exception()
				page = url + '&pageToken=' + result['nextPageToken']
				result = client.request(page)
				result = jsloads(result)
				items += result['items']
			except: pass
		try:
			if not pagination: raise Exception()
			next = cid + '&pageToken=' + result['nextPageToken']
		except: next = ''
		for item in items: 
			try:
				title = item['snippet']['title']
				try: url = item['snippet']['resourceId']['videoId']
				except: url = item['id']['videoId']
				image = item['snippet']['thumbnails']['high']['url']
				if '/default.jpg' in image: raise Exception()
				image = image
				append = {'title': title, 'url': url, 'image': image}
				if next != '': append['next'] = next
				self.list.append(append)
			except: pass
		try:
			u = [range(0, len(self.list))[i:i+50] for i in range(len(range(0, len(self.list))))[::50]]
			u = [','.join([self.list[x]['url'] for x in i]) for i in u]
			u = [self.content_link % i + self.key_link for i in u]

			threads = []
			append = threads.append
			for i in range(0, len(u)):
				append(Thread(target=self.thread, args=(u[i], i)))
				self.data.append('')
			[i.start() for i in threads]
			[i.join() for i in threads]
			items = []
			for i in self.data: items += jsloads(i)['items']
		except: pass

		for item in range(0, len(self.list)):
			try:
				vid = self.list[item]['url']
				self.list[item]['url'] = self.play_link % vid
				d = [(i['id'], i['contentDetails']) for i in items]
				d = [i for i in d if i[0] == vid]
				d = d[0][1]['duration']
				duration = 0
				try: duration += 60 * 60 * int(re.findall(r'(\d*)H', d)[0])
				except: pass
				try: duration += 60 * int(re.findall(r'(\d*)M', d)[0])
				except: pass
				try: duration += int(re.findall(r'(\d*)S', d)[0])
				except: pass
				duration = str(duration)
				self.list[item]['duration'] = duration
			except: pass
		return self.list

	def thread(self, url, i):
		try:
			result = client.request(url)
			self.data[i] = result
		except: return