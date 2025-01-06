# -*- coding: utf-8 -*-
import re
import os
import time
from apis.opensubtitles_api import OpenSubtitlesAPI
from apis.trakt_api import make_trakt_slug
from modules import kodi_utils as ku, settings as st, watched_status as ws
from modules.utils import sec2time
# logger = ku.logger

set_property, clear_property, convert_language, get_visibility, hide_busy_dialog = ku.set_property, ku.clear_property, ku.convert_language, ku.get_visibility, ku.hide_busy_dialog
Thread, json, ls, xbmc_player, translate_path, execute_builtin, sleep = ku.Thread, ku.json, ku.local_string, ku.xbmc_player, ku.translate_path, ku.execute_builtin, ku.sleep
make_listitem, volume_checker, list_dirs, get_setting, get_infolabel = ku.make_listitem, ku.volume_checker, ku.list_dirs, ku.get_setting, ku.get_infolabel
close_all_dialog, notification, select_dialog, poster_empty, fanart_empty = ku.close_all_dialog, ku.notification, ku.select_dialog, ku.empty_poster, ku.addon_fanart
auto_nextep_settings, disable_content_lookup, playback_settings = st.auto_nextep_settings, st.disable_content_lookup, st.playback_settings
get_art_provider, get_fanart_data, watched_indicators, auto_resume = st.get_art_provider, st.get_fanart_data, st.watched_indicators, st.auto_resume
clear_local_bookmarks, set_bookmark, mark_movie, mark_episode = ws.clear_local_bookmarks, ws.set_bookmark, ws.mark_movie, ws.mark_episode
xbmc_actor = ku.xbmc_actor
total_time_errors = ('0.0', '', 0.0, None)
video_fullscreen_check = 'Window.IsActive(fullscreenvideo)'

class FenPlayer(xbmc_player):
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
		if not self.monitor_playback: self.playback_successful = True
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
			sleep(100)

	def playback_close_dialogs(self):
		if self.monitor_playback:
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
				if disable_autoplay_next_episode: notification('%s - %s %s' % (ls(32135), ls(32178), ls(32736)), 4500)
				if any((play_random_continual, play_random, disable_autoplay_next_episode)): self.autoplay_nextep = False
				else: self.autoplay_nextep = self.sources_object.autoplay_nextep
			else: play_random_continual, self.autoplay_nextep = False, False
			while total_check_time <= 30 and not get_visibility(video_fullscreen_check):
				sleep(250)
				total_check_time += 0.25
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
					if self.current_point >= self.set_watched:
						if play_random_continual: self.run_random_continual(); break
						if not self.media_marked: self.media_watched_marker()
					if self.autoplay_nextep:
						if not self.nextep_info_gathered: self.info_next_ep()
						if round(self.total_time - self.curr_time) <= self.start_prep: self.run_next_ep(); break
					if not self.subs_searched: self.run_subtitles()
				except: pass
			hide_busy_dialog()
			if not self.media_marked: self.media_watched_marker()
			self.clear_playback_properties()
			clear_local_bookmarks()
		except:
			hide_busy_dialog()
			self.sources_object.playback_successful = False
			self.sources_object.cancel_all_playback = True
			return self.kill_dialog()

	def make_listing(self):
		listitem = make_listitem()
		listitem.setPath(self.url)
		if self.disable_lookup: listitem.setContentLookup(False)
		if self.is_generic:
			info_tag = listitem.getVideoInfoTag()
			info_tag.setMediaType('video')
			info_tag.setFilenameAndPath(self.url)
		else:
			self.tmdb_id, self.imdb_id, self.tvdb_id = self.meta_get('tmdb_id', ''), self.meta_get('imdb_id', ''), self.meta_get('tvdb_id', '')
			self.media_type, self.title, self.year = self.meta_get('media_type'), self.meta_get('title'), self.meta_get('year')
			self.season, self.episode = self.meta_get('season', ''), self.meta_get('episode', '')
			self.auto_resume, self.fanart_enabled = auto_resume(self.media_type), get_fanart_data()
			poster_main, poster_backup, fanart_main, fanart_backup, clearlogo_main, clearlogo_backup = get_art_provider()
			poster = self.meta_get('custom_poster') or self.meta_get(poster_main) or self.meta_get(poster_backup) or poster_empty
			fanart = self.meta_get('custom_fanart') or self.meta_get(fanart_main) or self.meta_get(fanart_backup) or fanart_empty
			clearlogo = self.meta_get('custom_clearlogo') or self.meta_get(clearlogo_main) or self.meta_get(clearlogo_backup) or ''
			if self.fanart_enabled:
				banner = self.meta_get('custom_banner') or self.meta_get('banner') or ''
				clearart = self.meta_get('custom_clearart') or self.meta_get('clearart') or ''
				landscape = self.meta_get('custom_landscape') or self.meta_get('landscape') or ''
			else: banner, clearart, landscape = '', '', ''
			duration, plot, genre, trailer, mpaa = self.meta_get('duration'), self.meta_get('plot'), self.meta_get('genre', ''), self.meta_get('trailer'), self.meta_get('mpaa')
			rating, votes = self.meta_get('rating'), self.meta_get('votes')
			premiered, studio, tagline = self.meta_get('premiered'), self.meta_get('studio', ''), self.meta_get('tagline')
			director, writer, cast, country = self.meta_get('director', ''), self.meta_get('writer', ''), self.meta_get('cast', []), self.meta_get('country', '')
			listitem.setLabel(self.title)
			if self.media_type == 'movie':
				if self.fanart_enabled:
					discart = self.meta_get('custom_discart') or self.meta_get('discart') or ''
					keyart = self.meta_get('custom_keyart') or self.meta_get('keyart') or ''
				else: discart, keyart = '', ''
				listitem.setArt({'poster': poster, 'fanart': fanart, 'icon': poster, 'banner': banner, 'clearart': clearart,
								'clearlogo': clearlogo, 'landscape': landscape, 'thumb': landscape, 'discart': discart, 'keyart': keyart})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setMediaType('movie')
				info_tag.setTitle(self.title)
				info_tag.setOriginalTitle(self.meta_get('original_title'))
				info_tag.setPlot(plot)
				info_tag.setYear(int(self.year))
				info_tag.setRating(rating)
				info_tag.setVotes(votes)
				info_tag.setMpaa(mpaa)
				info_tag.setDuration(duration)
				info_tag.setCountries(country)
				info_tag.setTrailer(trailer)
				info_tag.setPremiered(premiered)
				info_tag.setTagLine(tagline)
				info_tag.setStudios((studio or '',))
				info_tag.setUniqueIDs({'imdb': self.imdb_id, 'tmdb': str(self.tmdb_id)})
				info_tag.setIMDBNumber(self.imdb_id)
				info_tag.setGenres(genre.split(', '))
				info_tag.setWriters(writer.split(', '))
				info_tag.setDirectors(director.split(', '))
				info_tag.setCast([xbmc_actor(name=item['name'], role=item['role'], thumbnail=item['thumbnail']) for item in cast])
			else:
				listitem.setArt({'poster': poster, 'fanart': fanart, 'icon': poster, 'banner': banner, 'clearart': clearart, 'clearlogo': clearlogo, 'thumb': landscape,
								'landscape': landscape, 'tvshow.poster': poster, 'tvshow.clearart': clearart, 'tvshow.clearlogo': clearlogo})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setMediaType('episode')
				info_tag.setTitle(self.meta_get('ep_name'))
				info_tag.setOriginalTitle(self.meta_get('original_title'))
				info_tag.setTvShowTitle(self.title)
				info_tag.setTvShowStatus(self.meta_get('status'))
				info_tag.setSeason(self.season)
				info_tag.setEpisode(self.episode)
				info_tag.setPlot(plot)
				info_tag.setYear(int(self.year))
				info_tag.setRating(rating)
				info_tag.setVotes(votes)
				info_tag.setMpaa(mpaa)
				info_tag.setDuration(duration)
				info_tag.setTrailer(trailer)
				info_tag.setFirstAired(premiered)
				info_tag.setStudios((studio or '',))
				info_tag.setUniqueIDs({'imdb': self.imdb_id, 'tmdb': str(self.tmdb_id), 'tvdb': str(self.tvdb_id)})
				info_tag.setIMDBNumber(self.imdb_id)
				info_tag.setGenres(genre.split(', '))
				info_tag.setWriters(writer.split(', '))
				info_tag.setDirectors(director.split(', '))
				info_tag.setCast([xbmc_actor(name=item['name'], role=item['role'], thumbnail=item['thumbnail']) for item in cast])
				info_tag.setFilenameAndPath(self.url)
			self.set_resume_point(listitem)
			self.set_playback_properties()
		return listitem

	def media_watched_marker(self, force_watched=False):
		self.media_marked = True
		try:
			if self.current_point >= self.set_watched or force_watched:
				if self.media_type == 'movie': watched_function = mark_movie
				else: watched_function = mark_episode
				watched_params = {'action': 'mark_as_watched', 'tmdb_id': self.tmdb_id, 'title': self.title, 'year': self.year, 'season': self.season, 'episode': self.episode,
									'tvdb_id': self.tvdb_id, 'from_playback': 'true'}
				Thread(target=self.run_media_progress, args=(watched_function, watched_params)).start()
			else:
				clear_property('fen.random_episode_history')
				if self.current_point >= self.set_resume:
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

	def run_subtitles(self):
		self.subs_searched = True
		try: Thread(target=Subtitles().get, args=(self.title, self.imdb_id, self.season or None, self.episode or None)).start()
		except: pass

	def set_resume_point(self, listitem):
		if self.playback_percent > 0.0: listitem.setProperty('StartPercent', str(self.playback_percent))

	def info_next_ep(self):
		self.nextep_info_gathered = True
		try:
			nextep_settings = auto_nextep_settings()
			final_chapter = self.final_chapter() if nextep_settings['use_chapters'] else None
			percentage = 100 - final_chapter if final_chapter else nextep_settings['window_percentage']
			window_time = round((percentage/100) * self.total_time)
			use_window = nextep_settings['alert_method'] == 0
			default_action = nextep_settings['default_action']
			self.start_prep = nextep_settings['scraper_time'] + window_time
			self.nextep_settings = {'use_window': use_window, 'window_time': window_time, 'default_action': default_action, 'play_type': 'autoplay_nextep'}
		except: pass

	def final_chapter(self):
		final_chapter = None
		try:
			final = float(get_infolabel('Player.Chapters').split(',')[-1])
			if final >= 90: final_chapter = final
		except: pass
		return final_chapter

	def kill_dialog(self):
		try: self.sources_object._kill_progress_dialog()
		except: close_all_dialog()

	def set_constants(self, url, obj):
		self.url = url
		self.sources_object = obj
		self.disable_lookup = disable_content_lookup()
		self.is_generic = self.sources_object == 'video'
		if not self.is_generic:
			self.meta = self.sources_object.meta
			self.meta_get, self.kodi_monitor, self.playback_percent = self.meta.get, ku.monitor, self.sources_object.playback_percent or 0.0
			self.monitor_playback, self.playing_filename = self.sources_object.monitor_playback, self.sources_object.playing_filename
			self.media_marked, self.nextep_info_gathered, self.subs_searched = False, False, False
			self.playback_successful, self.cancel_all_playback = None, False
			self.set_watched, self.set_resume = playback_settings()

	def set_playback_properties(self):
		try:
			trakt_ids = {'tmdb': self.tmdb_id, 'imdb': self.imdb_id, 'slug': make_trakt_slug(self.title)}
			if self.media_type == 'episode': trakt_ids['tvdb'] = self.tvdb_id
			set_property('script.trakt.ids', json.dumps(trakt_ids))
			if self.playing_filename: set_property('subs.player_filename', self.playing_filename)
		except: pass

	def clear_playback_properties(self):
		clear_property('fen.window_stack')
		clear_property('script.trakt.ids')
		clear_property('subs.player_filename')

	def run_error(self):
		try: self.sources_object.playback_successful = False
		except: pass
		self.clear_playback_properties()
		notification(32121, 3500)
		return False

class Subtitles(xbmc_player):
	def __init__(self):
		xbmc_player.__init__(self)
		self.os = OpenSubtitlesAPI()
		self.auto_enable = get_setting('fen.subtitles.auto_enable')
		self.subs_action = get_setting('fen.subtitles.subs_action')
		self.language = get_setting('fen.subtitles.language_primary')
		self.quality = ['bluray', 'hdrip', 'brrip', 'bdrip', 'dvdrip', 'webdl', 'webrip', 'webcap', 'web', 'hdtv', 'hdrip']

	def get(self, query, imdb_id, season, episode, secondary_search=False):
		def _notification(line, _time=3500):
			return notification(line, _time)
		def _video_file_subs():
			try: available_sub_language = self.getSubtitles()
			except: available_sub_language = ''
			if available_sub_language == self.language:
				if self.auto_enable == 'true': self.showSubtitles(True)
				_notification(32852)
				return True
			return False
		def _downloaded_subs():
			files = list_dirs(subtitle_path)[1]
			if len(files) > 0:
				match_lang1 = None
				match_lang2 = None
				files = [i for i in files if i.endswith('.srt')]
				for item in files:
					if item == search_filename:
						match_lang1 = item
						break
				final_match = match_lang1 or match_lang2 or None
				if final_match:
					subtitle = os.path.join(subtitle_path, final_match)
					_notification(32792)
					return subtitle
			return False
		def _searched_subs():
			chosen_sub = None
			result = self.os.search(query, imdb_id, self.language, season, episode)
			if not result or len(result) == 0: return False
			try: video_path = self.getPlayingFile()
			except: video_path = ''
			if '|' in video_path: video_path = video_path.split('|')[0]
			video_path = os.path.basename(video_path)
			if self.subs_action == '1':
				self.pause()
				choices = [i for i in result if i['SubLanguageID'] == self.language and i['SubSumCD'] == '1']
				if len(choices) == 0: return False
				dialog_list = ['[B]%s[/B] | [I]%s[/I]' % (i['SubLanguageID'].upper(), i['MovieReleaseName']) for i in choices]
				list_items = [{'line1': item} for item in dialog_list]
				kwargs = {'items': json.dumps(list_items), 'heading': video_path.replace('%20', ' '), 'enumerate': 'true', 'narrow_window': 'true'}
				chosen_sub = select_dialog(choices, **kwargs)
				self.pause()
				if not chosen_sub: return False
			else:
				try: chosen_sub = [i for i in result if i['MovieReleaseName'].lower() in video_path.lower() and i['SubLanguageID'] == self.language and i['SubSumCD'] == '1'][0]
				except: pass
				if not chosen_sub:
					fmt = re.split(r'\.|\(|\)|\[|\]|\s|\-', video_path)
					fmt = [i.lower() for i in fmt]
					fmt = [i for i in fmt if i in self.quality]
					if season and fmt == '': fmt = 'hdtv'
					result = [i for i in result if i['SubSumCD'] == '1']
					filter = [i for i in result if i['SubLanguageID'] == self.language \
												and any(x in i['MovieReleaseName'].lower() for x in fmt) and any(x in i['MovieReleaseName'].lower() for x in self.quality)]
					if len(filter) > 0: chosen_sub = filter[0]
					else: chosen_sub = result[0]
			try: lang = convert_language(chosen_sub['SubLanguageID'])
			except: lang = chosen_sub['SubLanguageID']
			sub_format = chosen_sub['SubFormat']
			final_filename = sub_filename + '_%s.%s' % (lang, sub_format)
			download_url = chosen_sub['ZipDownloadLink']
			temp_zip = os.path.join(subtitle_path, 'temp.zip')
			temp_path = os.path.join(subtitle_path, chosen_sub['SubFileName'])
			final_path = os.path.join(subtitle_path, final_filename)
			subtitle = self.os.download(download_url, subtitle_path, temp_zip, temp_path, final_path)
			sleep(1000)
			return subtitle
		if self.subs_action == '2': return
		sleep(2500)
		imdb_id = re.sub(r'[^0-9]', '', imdb_id)
		subtitle_path = translate_path('special://temp/')
		sub_filename = 'FENSubs_%s_%s_%s' % (imdb_id, season, episode) if season else 'FENSubs_%s' % imdb_id
		search_filename = sub_filename + '_%s.srt' % self.language
		subtitle = _video_file_subs()
		if subtitle: return
		subtitle = _downloaded_subs()
		if subtitle: return self.setSubtitles(subtitle)
		subtitle = _searched_subs()
		if subtitle: return self.setSubtitles(subtitle)
		if secondary_search: return _notification(32793)
		secondary_language = get_setting('fen.subtitles.language_secondary')
		if secondary_language in (self.language, None, 'None', ''): return _notification(32793)
		self.language = secondary_language
		self.get(query, imdb_id, season, episode, secondary_search=True)
