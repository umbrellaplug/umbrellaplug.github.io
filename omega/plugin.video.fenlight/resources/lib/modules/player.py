# -*- coding: utf-8 -*-
import json
from threading import Thread
from apis.trakt_api import make_trakt_slug
from caches.settings_cache import get_setting
from modules import kodi_utils as ku, settings as st, watched_status as ws
# logger = ku.logger

set_property, clear_property, get_visibility, hide_busy_dialog, xbmc_actor = ku.set_property, ku.clear_property, ku.get_visibility, ku.hide_busy_dialog, ku.xbmc_actor
xbmc_player, execute_builtin, sleep = ku.xbmc_player, ku.execute_builtin, ku.sleep
make_listitem, volume_checker, get_infolabel, xbmc_monitor = ku.make_listitem, ku.volume_checker, ku.get_infolabel, ku.xbmc_monitor
close_all_dialog, notification, poster_empty, fanart_empty = ku.close_all_dialog, ku.notification, ku.empty_poster, ku.get_addon_fanart()
auto_resume, auto_nextep_settings, store_resolved_to_cloud = st.auto_resume, st.auto_nextep_settings, st.store_resolved_to_cloud
set_bookmark, mark_movie, mark_episode = ws.set_bookmark, ws.mark_movie, ws.mark_episode
total_time_errors = ('0.0', '', 0.0, None)
set_resume, set_watched = 5, 90
video_fullscreen_check = 'Window.IsActive(fullscreenvideo)'

class FenLightPlayer(xbmc_player):
	def __init__ (self):
		xbmc_player.__init__(self)

	def run(self, url=None, obj=None):
		hide_busy_dialog()
		self.clear_playback_properties()
		if not url: return self.run_error()
		try: return self.play_video(url, obj)
		except: return self.run_error()

	def play_video(self, url, obj):
		self.set_constants(url, obj)
		volume_checker()
		self.play(self.url, self.make_listing())
		if not self.is_generic:
			self.check_playback_start()
			if self.playback_successful: self.monitor()
			else:
				self.sources_object.playback_successful = self.playback_successful
				self.sources_object.cancel_all_playback = self.cancel_all_playback
				if self.cancel_all_playback: self.kill_dialog()
				self.stop()
			try: del self.kodi_monitor
			except: pass

	def check_playback_start(self):
		resolve_percent = 0
		while self.playback_successful is None:
			hide_busy_dialog()
			if not self.sources_object.progress_dialog: self.playback_successful = True
			elif self.sources_object.progress_dialog.skip_resolved(): self.playback_successful = False
			elif self.sources_object.progress_dialog.iscanceled() or self.kodi_monitor.abortRequested(): self.cancel_all_playback, self.playback_successful = True, False
			elif resolve_percent >= 100: self.playback_successful = False
			elif get_visibility('Window.IsTopMost(okdialog)'):
				execute_builtin('SendClick(okdialog, 11)')
				self.playback_successful = False
			elif self.isPlayingVideo():
				try:
					if self.getTotalTime() not in total_time_errors and get_visibility(video_fullscreen_check): self.playback_successful = True
				except: pass
			resolve_percent = round(resolve_percent + 26.0/100, 1)
			self.sources_object.progress_dialog.update_resolver(percent=resolve_percent)
			sleep(50)

	def playback_close_dialogs(self):
		self.sources_object.playback_successful = True
		self.kill_dialog()
		sleep(200)
		close_all_dialog()

	def monitor(self):
		try:
			ensure_dialog_dead, total_check_time = False, 0
			if self.media_type == 'episode':
				play_random_continual = self.sources_object.random_continual
				play_random = self.sources_object.random
				disable_autoplay_next_episode = self.sources_object.disable_autoplay_next_episode
				if disable_autoplay_next_episode: notification('Scrape with Custom Values - Autoplay Next Episode Cancelled', 4500)
				if any((play_random_continual, play_random, disable_autoplay_next_episode)): self.autoplay_nextep, self.autoscrape_nextep = False, False
				else: self.autoplay_nextep, self.autoscrape_nextep = self.sources_object.autoplay_nextep, self.sources_object.autoscrape_nextep
			else: play_random_continual, self.autoplay_nextep, self.autoscrape_nextep = False, False, False
			while total_check_time <= 30 and not get_visibility(video_fullscreen_check):
				sleep(100)
				total_check_time += 0.10
			hide_busy_dialog()
			sleep(1000)
			while self.isPlayingVideo():
				try:
					try: self.total_time, self.curr_time = self.getTotalTime(), self.getTime()
					except: sleep(250); continue
					if not ensure_dialog_dead:
						ensure_dialog_dead = True
						self.playback_close_dialogs()
					sleep(1000)
					self.current_point = round(float(self.curr_time/self.total_time * 100), 1)
					if self.current_point >= set_watched:
						if play_random_continual: self.run_random_continual(); break
						if not self.media_marked: self.media_watched_marker()
					if self.autoplay_nextep or self.autoscrape_nextep:
						if not self.nextep_info_gathered: self.info_next_ep()
						if round(self.total_time - self.curr_time) <= self.start_prep: self.run_next_ep(); break
				except: pass
			hide_busy_dialog()
			if not self.media_marked: self.media_watched_marker()
			self.clear_playback_properties()
			self.clear_playing_item()
		except:
			hide_busy_dialog()
			self.sources_object.playback_successful = False
			self.sources_object.cancel_all_playback = True
			return self.kill_dialog()

	def make_listing(self):
		listitem = make_listitem()
		listitem.setPath(self.url)
		listitem.setContentLookup(False)
		if self.is_generic:
			info_tag = listitem.getVideoInfoTag()
			info_tag.setMediaType('video')
			info_tag.setFilenameAndPath(self.url)
		else:
			self.tmdb_id, self.imdb_id, self.tvdb_id = self.meta_get('tmdb_id', ''), self.meta_get('imdb_id', ''), self.meta_get('tvdb_id', '')
			self.media_type, self.title, self.year = self.meta_get('media_type'), self.meta_get('title'), self.meta_get('year')
			self.season, self.episode = self.meta_get('season', ''), self.meta_get('episode', '')
			self.auto_resume = auto_resume(self.media_type)
			poster = self.meta_get('poster') or poster_empty
			fanart = self.meta_get('fanart') or fanart_empty
			clearlogo = self.meta_get('clearlogo') or ''
			duration, plot, genre, trailer, mpaa = self.meta_get('duration'), self.meta_get('plot'), self.meta_get('genre', ''), self.meta_get('trailer'), self.meta_get('mpaa')
			rating, votes = self.meta_get('rating'), self.meta_get('votes')
			premiered, studio, tagline = self.meta_get('premiered'), self.meta_get('studio', ''), self.meta_get('tagline')
			director, writer, cast, country = self.meta_get('director', ''), self.meta_get('writer', ''), self.meta_get('cast', []), self.meta_get('country', '')
			listitem.setLabel(self.title)
			if self.media_type == 'movie':
				listitem.setArt({'poster': poster, 'fanart': fanart, 'icon': poster, 'clearlogo': clearlogo})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setMediaType('movie'), info_tag.setTitle(self.title), info_tag.setOriginalTitle(self.meta_get('original_title')), info_tag.setPlot(plot)
				info_tag.setYear(int(self.year)), info_tag.setRating(rating), info_tag.setVotes(votes), info_tag.setMpaa(mpaa)
				info_tag.setDuration(duration), info_tag.setCountries(country), info_tag.setTrailer(trailer), info_tag.setPremiered(premiered)
				info_tag.setTagLine(tagline), info_tag.setStudios(studio), info_tag.setIMDBNumber(self.imdb_id), info_tag.setGenres(genre)
				info_tag.setWriters(writer), info_tag.setDirectors(director), info_tag.setUniqueIDs({'imdb': self.imdb_id, 'tmdb': str(self.tmdb_id)})
				info_tag.setCast([xbmc_actor(name=item['name'], role=item['role'], thumbnail=item['thumbnail']) for item in cast])
			else:
				listitem.setArt({'poster': poster, 'fanart': fanart, 'icon': poster, 'clearlogo': clearlogo, 'tvshow.poster': poster, 'tvshow.clearlogo': clearlogo})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setMediaType('episode'), info_tag.setTitle(self.meta_get('ep_name')), info_tag.setOriginalTitle(self.meta_get('original_title'))
				info_tag.setTvShowTitle(self.title), info_tag.setTvShowStatus(self.meta_get('status')), info_tag.setSeason(self.season), info_tag.setEpisode(self.episode)
				info_tag.setPlot(plot), info_tag.setYear(int(self.year)), info_tag.setRating(rating), info_tag.setVotes(votes)
				info_tag.setMpaa(mpaa), info_tag.setDuration(duration), info_tag.setTrailer(trailer), info_tag.setFirstAired(premiered)
				info_tag.setStudios(studio), info_tag.setIMDBNumber(self.imdb_id), info_tag.setGenres(genre), info_tag.setWriters(writer)
				info_tag.setDirectors(director), info_tag.setUniqueIDs({'imdb': self.imdb_id, 'tmdb': str(self.tmdb_id), 'tvdb': str(self.tvdb_id)})
				info_tag.setCast([xbmc_actor(name=item['name'], role=item['role'], thumbnail=item['thumbnail']) for item in cast])
				info_tag.setFilenameAndPath(self.url)
			self.set_resume_point(listitem)
			self.set_playback_properties()
		return listitem

	def media_watched_marker(self, force_watched=False):
		self.media_marked = True
		try:
			if self.current_point >= set_watched or force_watched:
				if self.media_type == 'movie': watched_function = mark_movie
				else: watched_function = mark_episode
				watched_params = {'action': 'mark_as_watched', 'tmdb_id': self.tmdb_id, 'title': self.title, 'year': self.year, 'season': self.season, 'episode': self.episode,
									'tvdb_id': self.tvdb_id, 'from_playback': 'true'}
				Thread(target=self.run_media_progress, args=(watched_function, watched_params)).start()
			else:
				clear_property('fenlight.random_episode_history')
				if self.current_point >= set_resume:
					progress_params = {'media_type': self.media_type, 'tmdb_id': self.tmdb_id, 'curr_time': self.curr_time, 'total_time': self.total_time,
									'title': self.title, 'season': self.season, 'episode': self.episode, 'from_playback': 'true'}
					Thread(target=self.run_media_progress, args=(set_bookmark, progress_params)).start()
		except: pass

	def run_media_progress(self, function, params):
		try: function(params)
		except: pass

	def run_next_ep(self):
		from modules.episode_tools import EpisodeTools
		if not self.media_marked: self.media_watched_marker(force_watched=True)
		EpisodeTools(self.meta, self.nextep_settings).auto_nextep()

	def run_random_continual(self):
		from modules.episode_tools import EpisodeTools
		if not self.media_marked: self.media_watched_marker(force_watched=True)
		EpisodeTools(self.meta).play_random_continual(False)

	def set_resume_point(self, listitem):
		if self.playback_percent > 0.0: listitem.setProperty('StartPercent', str(self.playback_percent))

	def info_next_ep(self):
		self.nextep_info_gathered = True
		try:
			play_type = 'autoplay_nextep' if self.autoplay_nextep else 'autoscrape_nextep'
			nextep_settings = auto_nextep_settings(play_type)
			final_chapter = self.final_chapter() if nextep_settings['use_chapters'] else None
			percentage = 100 - final_chapter if final_chapter else nextep_settings['window_percentage']
			window_time = round((percentage/100) * self.total_time)
			use_window = nextep_settings['alert_method'] == 0
			default_action = nextep_settings['default_action']
			self.start_prep = nextep_settings['scraper_time'] + window_time
			self.nextep_settings = {'use_window': use_window, 'window_time': window_time, 'default_action': default_action, 'play_type': play_type}
		except: pass

	def final_chapter(self):
		try:
			final_chapter = float(get_infolabel('Player.Chapters').split(',')[-1])
			if final_chapter >= 90: return final_chapter
		except: pass
		return None

	def kill_dialog(self):
		try: self.sources_object._kill_progress_dialog()
		except: close_all_dialog()

	def set_constants(self, url, obj):
		self.url = url
		self.sources_object = obj
		self.is_generic = self.sources_object == 'video'
		if not self.is_generic:
			self.meta = self.sources_object.meta
			self.meta_get, self.kodi_monitor, self.playback_percent = self.meta.get, xbmc_monitor(), self.sources_object.playback_percent or 0.0
			self.playing_filename = self.sources_object.playing_filename
			self.media_marked, self.nextep_info_gathered = False, False
			self.playback_successful, self.cancel_all_playback = None, False
			self.playing_item = self.sources_object.playing_item

	def set_playback_properties(self):
		try:
			trakt_ids = {'tmdb': self.tmdb_id, 'imdb': self.imdb_id, 'slug': make_trakt_slug(self.title)}
			if self.media_type == 'episode': trakt_ids['tvdb'] = self.tvdb_id
			set_property('script.trakt.ids', json.dumps(trakt_ids))
			if self.playing_filename: set_property('subs.player_filename', self.playing_filename)
		except: pass

	def clear_playback_properties(self):
		clear_property('fenlight.window_stack')
		clear_property('script.trakt.ids')
		clear_property('subs.player_filename')

	def clear_playing_item(self):
		if self.playing_item['cache_provider'] == 'Offcloud':
			if self.playing_item.get('direct_debrid_link', False): return
			if store_resolved_to_cloud('Offcloud', 'package' in self.playing_item): return
			from apis.offcloud_api import OffcloudAPI
			OffcloudAPI().clear_played_torrent(self.playing_item)

	def run_error(self):
		try: self.sources_object.playback_successful = False
		except: pass
		self.clear_playback_properties()
		notification('Playback Failed', 3500)
		return False
