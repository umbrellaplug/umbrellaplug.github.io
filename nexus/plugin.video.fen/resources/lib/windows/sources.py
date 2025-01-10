# -*- coding: utf-8 -*-
from windows.base_window import BaseDialog
from modules.settings import get_art_provider, provider_sort_ranks, get_fanart_data, avoid_episode_spoilers
from modules import kodi_utils
# logger = kodi_utils.logger

json, Thread, dialog, select_dialog, ok_dialog = kodi_utils.json, kodi_utils.Thread, kodi_utils.dialog, kodi_utils.select_dialog, kodi_utils.ok_dialog
hide_busy_dialog, addon_fanart, empty_poster = kodi_utils.hide_busy_dialog, kodi_utils.addon_fanart, kodi_utils.empty_poster
fetch_kodi_imagecache, get_icon, ls = kodi_utils.fetch_kodi_imagecache, kodi_utils.get_icon, kodi_utils.local_string

resume_dict = {10: 'resume', 11: 'start_over', 12: 'cancel'}
info_icons_dict = {'furk': get_icon('provider_furk'), 'easynews': get_icon('provider_easynews'), 'alldebrid': get_icon('provider_alldebrid'),
				'real-debrid': get_icon('provider_realdebrid'), 'premiumize': get_icon('provider_premiumize'), 'ad_cloud': get_icon('provider_alldebrid'),
				'rd_cloud': get_icon('provider_realdebrid'), 'pm_cloud': get_icon('provider_premiumize')}
info_quality_dict = {'4k': get_icon('flag_4k'), '1080p': get_icon('flag_1080p'), '720p': get_icon('flag_720p'), 'sd': get_icon('flag_sd')}
extra_info_choices = (('PACK', 'PACK'), ('DOLBY VISION', 'D/VISION'), ('HIGH DYNAMIC RANGE (HDR)', 'HDR'), ('HYBRID', 'HYBRID'), ('AV1', 'AV1'),
					('HEVC (X265)', 'HEVC'), ('REMUX', 'REMUX'), ('BLURAY', 'BLURAY'), ('SDR', 'SDR'), ('3D', '3D'), ('DOLBY ATMOS', 'ATMOS'), ('DOLBY TRUEHD', 'TRUEHD'),
					('DOLBY DIGITAL EX', 'DD-EX'), ('DOLBY DIGITAL PLUS', 'DD+'), ('DOLBY DIGITAL', 'DD'), ('DTS-HD MASTER AUDIO', 'DTS-HD MA'), ('DTS-X', 'DTS-X'),
					('DTS-HD', 'DTS-HD'), ('DTS', 'DTS'), ('AAC', 'AAC'), ('OPUS', 'OPUS'), ('MP3', 'MP3'), ('8CH AUDIO', '8CH'), ('7CH AUDIO', '7CH'), ('6CH AUDIO', '6CH'),
					('2CH AUDIO', '2CH'), ('DVD SOURCE', 'DVD'), ('WEB SOURCE', 'WEB'), ('MULTIPLE LANGUAGES', 'MULTI-LANG'), ('SUBTITLES', 'SUBS'))
quality_choices = ('4K', '1080P', '720P', 'SD', 'CAM/SCR/TELE')
prerelease_values, prerelease_key = ('CAM', 'SCR', 'TELE'), 'CAM/SCR/TELE'
poster_lists, pack_check = ('list', 'medialist'), ('true', 'show', 'season')
filter_str, info_str, down_file_str, browse_pack_str, down_pack_str, furk_addto_str = ls(32152), ls(32987), ls(32747), ls(33004), ls(32007), ls(32769)
filter_title, filter_extraInfo, cloud_str, filters_ignored, start_scrape = ls(32679), ls(32169), ls(32016), ls(32686), ls(33023)
show_uncached_str, spoilers_str, run_plugin_str = ls(32088), ls(33105), 'RunPlugin(%s)'
string = str
upper, lower = string.upper, string.lower
resume_timeout = 10000

class SourcesResults(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
		self.window_format = kwargs.get('window_format', 'list')
		self.window_style = kwargs.get('window_style', 'contrast')
		self.window_id = kwargs.get('window_id', 2000)
		self.filter_window_id = 2100
		self.results = kwargs.get('results')
		self.uncached_torrents = kwargs.get('uncached_torrents', [])
		self.info_highlights_dict = kwargs.get('scraper_settings')
		self.prescrape = kwargs.get('prescrape')
		self.meta = kwargs.get('meta')
		self.meta_get = self.meta.get
		self.highlight_value = self.highlight_var(force=True)
		self.make_poster = self.window_format in poster_lists
		self.filters_ignored = '[B](%s)[/B]' % filters_ignored if kwargs.get('filters_ignored', False) else ''
		self.poster_main, self.poster_backup, self.fanart_main, self.fanart_backup, self.clearlogo_main, self.clearlogo_backup = get_art_provider()
		self.poster = self.original_poster()
		self.make_items()
		self.make_filter_items()
		self.set_properties()

	def onInit(self):
		self.filter_applied = False
		if self.make_poster: Thread(target=self.set_poster).start()
		self.add_items(self.window_id, self.item_list)
		self.add_items(self.filter_window_id, self.filter_list)
		self.setFocusId(self.window_id)

	def run(self):
		self.doModal()
		self.clearProperties()
		hide_busy_dialog()
		return self.selected

	def get_provider_and_path(self, provider):
		try: return provider, info_icons_dict[provider]
		except: return 'folders', get_icon('provider_folder')

	def get_quality_and_path(self, quality):
		try: return quality, info_quality_dict[quality]
		except: return 'sd', get_icon('flag_sd')

	def filter_action(self, action):
		if action == self.right_action or action in self.closing_actions:
			self.select_item(self.filter_window_id, 0)
			self.setFocusId(self.window_id)
		if action in self.selection_actions:
			chosen_listitem = self.get_listitem(self.filter_window_id)
			filter_type, filter_value = chosen_listitem.getProperty('filter_type'), chosen_listitem.getProperty('filter_value')
			if filter_type in ('quality', 'provider'):
				if filter_value == prerelease_key: filtered_list = [i for i in self.item_list if i.getProperty(filter_type) in filter_value.split('/')]
				else: filtered_list = [i for i in self.item_list if i.getProperty(filter_type) == filter_value]
			elif filter_type == 'special':
				if filter_value == 'title':
					keywords = dialog.input(ls(33063))
					if not keywords: return
					keywords.replace(' ', '')
					keywords = keywords.split(',')
					choice = [upper(i) for i in keywords]
					filtered_list = [i for i in self.item_list if all(x in i.getProperty('name') for x in choice)]
				elif filter_value == 'extraInfo':
					list_items = [{'line1': item[0], 'icon': self.poster} for item in extra_info_choices]
					kwargs = {'items': json.dumps(list_items), 'heading': filter_str, 'multi_choice': 'true'}
					choice = select_dialog(extra_info_choices, **kwargs)
					if choice == None: return
					choice = [i[1] for i in choice]
					filtered_list = [i for i in self.item_list if all(x in i.getProperty('extraInfo') for x in choice)]
				elif filter_value == 'showuncached': filtered_list = self.make_items(self.uncached_torrents)
			if not filtered_list: return ok_dialog(text=32760)
			self.set_filter(filtered_list)

	def onAction(self, action):
		if self.get_visibility('Control.HasFocus(%s)' % self.filter_window_id): return self.filter_action(action)
		chosen_listitem = self.get_listitem(self.window_id)		
		if action in self.closing_actions:
			if self.filter_applied: return self.clear_filter()
			self.selected = (None, '')
			return self.close()
		if action == self.info_action:
			self.open_window(('windows.sources', 'SourcesInfo'), 'sources_info.xml', item=chosen_listitem)
		elif action in self.selection_actions:
			if self.prescrape and chosen_listitem.getProperty('perform_full_search') == 'true':
				self.selected = ('perform_full_search', '')
				return self.close()
			chosen_source = json.loads(chosen_listitem.getProperty('source'))
			if 'Uncached' in chosen_source.get('cache_provider', ''):
				from modules.sources import Sources
				return Thread(target=Sources().resolve_uncached_torrents, args=(chosen_source['debrid'], chosen_source['url'], 'package' in chosen_source)).start()
			self.selected = ('play', chosen_source)
			return self.close()
		elif action in self.context_actions:
			source = json.loads(chosen_listitem.getProperty('source'))
			choice = self.context_menu(source)
			if choice:
				if isinstance(choice, dict): return self.execute_code(run_plugin_str % self.build_url(choice))
				if choice == 'results_info': return self.open_window(('windows.sources', 'SourcesInfo'), 'sources_info.xml', item=chosen_listitem)
		elif action in self.closing_actions:
			if self.filter_applied: return self.clear_filter()
			self.selected = (None, '')
			return self.close()

	def make_items(self, filtered_list=None):
		def builder(results):
			for count, item in enumerate(results, 1):
				try:
					get = item.get
					listitem = self.make_listitem()
					set_property = listitem.setProperty
					scrape_provider, source, quality, name = get('scrape_provider'), get('source'), get('quality', 'SD'), get('display_name')
					basic_quality, quality_icon = self.get_quality_and_path(lower(quality))
					pack = get('package', 'false') in pack_check
					extraInfo = get('extraInfo', '')
					extraInfo = extraInfo.rstrip('| ')
					if pack: extraInfo = '[B]%s PACK[/B] | %s' % (get('package'), extraInfo)
					elif not extraInfo: extraInfo = 'N/A'
					if scrape_provider == 'external':
						source_site = upper(get('provider'))
						provider = upper(get('debrid', source_site).replace('.me', ''))
						provider_lower = lower(provider)
						provider_icon = self.get_provider_and_path(provider_lower)[1]
						if 'cache_provider' in item:
							if 'Uncached' in item['cache_provider']:
								if 'seeders' in item: set_property('source_type', 'UNCACHED (%d SEEDERS)' % get('seeders', 0))
								else: set_property('source_type', 'UNCACHED')
								set_property('highlight', 'FF7C7C7C')
							else:
								cache_flag = '[B]CACHED[/B]' if provider == 'PREMIUMIZE' else 'UNCHECKED'
								if highlight_type == 0: key = 'torrent_highlight'
								elif highlight_type == 1: key = provider_lower
								else: key = basic_quality
								set_property('highlight', self.info_highlights_dict[key])
							if pack: set_property('source_type', '%s [B]PACK[/B]' % cache_flag)
							else: set_property('source_type', '%s' % cache_flag)
						else:
							if highlight_type == 0: key = 'hoster_highlight'
							elif highlight_type == 1: key = provider_lower
							else: key = basic_quality
							set_property('highlight', self.info_highlights_dict[key])
							set_property('source_type', source)
						set_property('provider', provider)
					else:
						if pack: extraInfo = extraInfo.replace('true PACK', 'PACK')
						source_site = upper(source)
						provider, provider_icon = self.get_provider_and_path(lower(source))
						if highlight_type in (0, 1): key = provider
						else: key = basic_quality
						set_property('highlight', self.info_highlights_dict[key])
						set_property('source_type', 'DIRECT')
						set_property('provider', upper(provider))
					set_property('name', upper(name))
					set_property('source_site', source_site)
					set_property('provider_icon', provider_icon)
					set_property('quality_icon', quality_icon)
					set_property('size_label', get('size_label', 'N/A'))
					set_property('extraInfo', extraInfo)
					set_property('quality', upper(quality))
					set_property('count', '%02d.' % count)
					set_property('hash', get('hash', 'N/A'))
					set_property('source', json.dumps(item))
					yield listitem
				except: pass
		try:
			highlight_type = self.info_highlights_dict['highlight_type']
			if filtered_list: return list(builder(filtered_list))
			self.item_list = list(builder(self.results))
			if self.prescrape:
				prescrape_listitem = self.make_listitem()
				prescrape_listitem.setProperty('perform_full_search', 'true')
			self.total_results = string(len(self.item_list))
			if self.prescrape: self.item_list.append(prescrape_listitem)
		except: pass

	def make_filter_items(self):
		def builder(data):
			for item in data:
				listitem = self.make_listitem()
				listitem.setProperties({'label': item[0], 'filter_type': item[1], 'filter_value': item[2]})
				yield listitem
		duplicates = set()
		qualities = [i.getProperty('quality') for i in self.item_list \
							if not (i.getProperty('quality') in duplicates or duplicates.add(i.getProperty('quality'))) \
							and not i.getProperty('quality') == '']
		if any(i in prerelease_values for i in qualities): qualities = [i for i in qualities if not i in prerelease_values] + [prerelease_key]
		qualities.sort(key=quality_choices.index)
		duplicates = set()
		providers = [i.getProperty('provider') for i in self.item_list \
							if not (i.getProperty('provider') in duplicates or duplicates.add(i.getProperty('provider'))) \
							and not i.getProperty('provider') == '']
		sort_ranks = provider_sort_ranks()
		sort_ranks['premiumize'] = sort_ranks.pop('premiumize.me')
		provider_choices = sorted(sort_ranks.keys(), key=sort_ranks.get)
		provider_choices = [upper(i) for i in provider_choices]
		providers.sort(key=provider_choices.index)
		qualities = [('Show [B]%s[/B] Only' % i, 'quality', i) for i in qualities]
		providers = [('Show [B]%s[/B] Only' % i, 'provider', i) for i in providers]
		data = qualities + providers
		if self.uncached_torrents: data.append(('Show [B]%s[/B] Only' % show_uncached_str, 'special', 'showuncached'))
		data.extend([(filter_title, 'special', 'title'), (filter_extraInfo, 'special', 'extraInfo')])
		self.filter_list = list(builder(data))

	def set_properties(self):
		self.setProperty('highlight_var', self.highlight_value)
		self.setProperty('window_format', self.window_format)
		self.setProperty('window_style', self.window_style)
		self.setProperty('fanart', self.original_fanart())
		self.setProperty('clearlogo', self.meta_get('custom_clearlogo') or self.meta_get(self.clearlogo_main) or self.meta_get(self.clearlogo_backup) or '')
		self.setProperty('title', self.meta_get('title'))
		self.setProperty('total_results', self.total_results)
		self.setProperty('filters_ignored', self.filters_ignored)

	def original_poster(self):
		poster = self.meta_get('custom_poster') or self.meta_get(self.poster_main) or self.meta_get(self.poster_backup) or empty_poster
		self.current_poster = poster
		if 'image.tmdb' in self.current_poster:
			try: poster = self.current_poster.replace('w185', 'original').replace('w342', 'original').replace('w780', 'original')
			except: pass
		elif 'fanart.tv' in self.current_poster:
			if not self.check_poster_cached(self.current_poster): self.current_poster = self.meta_get(self.poster_backup) or empty_poster
		return poster

	def set_poster(self):
		if self.current_poster:
			image_id = 200 if self.window_id == 2000 else 201
			self.set_image(image_id, self.current_poster)
			self.set_image(210, self.poster)
			total_time = 0
			while not self.check_poster_cached(self.poster):
				if total_time >= 200: break
				total_time += 1
				self.sleep(50)
			self.set_image(image_id, self.poster)

	def check_poster_cached(self, poster):
		try:
			if poster == empty_poster: return True
			if fetch_kodi_imagecache(poster): return True
			return False
		except: return True

	def original_fanart(self):
		fanart = self.meta_get('custom_fanart') or self.meta_get(self.fanart_main) or self.meta_get(self.fanart_backup) or addon_fanart
		return fanart

	def context_menu(self, item):
		down_file_params, down_pack_params, browse_pack_params, add_magnet_to_cloud_params, add_files_to_furk_params = None, None, None, None, None
		item_get = item.get
		item_id, name, magnet_url, info_hash = item_get('id', None), item_get('name'), item_get('url', 'None'), item_get('hash', 'None')
		provider_source, scrape_provider, cache_provider = item_get('source'), item_get('scrape_provider'), item_get('cache_provider', 'None')
		uncached_torrent = 'Uncached' in cache_provider
		source, meta_json = json.dumps(item), json.dumps(self.meta)
		choices = []
		choices_append = choices.append
		if not uncached_torrent and scrape_provider != 'folders':
			down_file_params = {'mode': 'downloader', 'action': 'meta.single', 'name': self.meta.get('rootname', ''), 'source': source,
								'url': None, 'provider': scrape_provider, 'meta': meta_json}
		if 'package' in item:
			if scrape_provider == 'furk':
				add_files_to_furk_params = {'mode': 'furk.add_to_files', 'item_id': item_id}
				if item_get('package', 'false') == 'true':                 
					browse_pack_params = {'mode': 'furk.browse_packs', 'file_name': name, 'file_id': item_id}
					down_pack_params = {'mode': 'downloader', 'action': 'meta.pack', 'name': self.meta.get('rootname', ''), 'source': source,
										'url': None, 'provider': scrape_provider, 'meta': meta_json, 'file_name': name, 'file_id': item_id}
			elif not uncached_torrent:
				down_pack_params = {'mode': 'downloader', 'action': 'meta.pack', 'name': self.meta.get('rootname', ''), 'source': source, 'url': None,
									'provider': cache_provider, 'meta': meta_json, 'magnet_url': magnet_url, 'info_hash': info_hash}
		if provider_source == 'torrent' and not uncached_torrent:
			browse_pack_params = {'mode': 'debrid.browse_packs', 'provider': cache_provider, 'name': name,
								'magnet_url': magnet_url, 'info_hash': info_hash}
			add_magnet_to_cloud_params = {'mode': 'manual_add_magnet_to_cloud', 'provider': cache_provider, 'magnet_url': magnet_url}
		choices_append((info_str, 'results_info'))
		if add_magnet_to_cloud_params: choices_append((cloud_str, add_magnet_to_cloud_params))
		if add_files_to_furk_params: choices_append((furk_addto_str, add_files_to_furk_params))
		if browse_pack_params: choices_append((browse_pack_str, browse_pack_params))
		if down_pack_params: choices_append((down_pack_str, down_pack_params))
		if down_file_params: choices_append((down_file_str, down_file_params))
		list_items = [{'line1': i[0], 'icon': self.poster} for i in choices]
		kwargs = {'items': json.dumps(list_items)}
		choice = select_dialog([i[1] for i in choices], **kwargs)
		return choice

	def set_filter(self, filtered_list):
		self.filter_applied = True
		self.reset_window(self.window_id)
		self.add_items(self.window_id, filtered_list)
		self.setFocusId(self.window_id)
		self.setProperty('total_results', string(len(filtered_list)))
		self.setProperty('filter_applied', 'true')

	def clear_filter(self):
		self.filter_applied = False
		self.reset_window(self.window_id)
		self.add_items(self.window_id, self.item_list)
		self.setFocusId(self.window_id)
		self.select_item(self.filter_window_id, 0)
		self.setProperty('total_results', self.total_results)
		self.setProperty('filter_applied', 'false')

class SourcesPlayback(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
		self.meta = kwargs.get('meta')
		self.highlight_value = self.highlight_var(force=True)
		self.is_canceled, self.skip_resolve, self.resume_choice = False, False, None
		self.meta_get = self.meta.get
		self.enable_scraper()

	def run(self):
		self.doModal()
		self.clearProperties()
		self.clear_modals()

	def onClick(self, controlID):
		self.resume_choice = resume_dict[controlID]

	def onAction(self, action):
		if action in self.closing_actions: self.is_canceled = True
		elif action == self.right_action and self.window_mode == 'resolver': self.skip_resolve = True

	def iscanceled(self):
		return self.is_canceled

	def skip_resolved(self):
		status = self.skip_resolve
		self.skip_resolve = False
		return status

	def reset_is_cancelled(self):
		self.is_canceled = False

	def enable_scraper(self):
		self.window_mode = 'scraper'
		self.set_scraper_properties()

	def enable_resolver(self):
		self.window_mode = 'resolver'
		self.set_resolver_properties()

	def enable_resume(self, percent):
		self.window_mode = 'resume'
		self.set_resume_properties(percent)

	def busy_spinner(self, toggle='true'):
		self.setProperty('enable_busy_spinner', toggle)

	def set_scraper_properties(self):
		poster_main, poster_backup, fanart_main, fanart_backup, clearlogo_main, clearlogo_backup = get_art_provider()
		title, year, genre = self.meta_get('title'), string(self.meta_get('year')), self.meta_get('genre', '')
		poster = self.meta_get('custom_poster') or self.meta_get(poster_main) or self.meta_get(poster_backup) or empty_poster
		fanart = self.meta_get('custom_fanart') or self.meta_get(fanart_main) or self.meta_get(fanart_backup) or addon_fanart
		clearlogo = self.meta_get('custom_clearlogo') or self.meta_get(clearlogo_main) or self.meta_get(clearlogo_backup) or ''
		self.setProperty('highlight_var', self.highlight_value)
		self.setProperty('window_mode', self.window_mode)
		self.setProperty('title', title)
		self.setProperty('fanart', fanart)
		self.setProperty('clearlogo', clearlogo)
		self.setProperty('year', year)
		self.setProperty('poster', poster)
		self.setProperty('genre', genre)
		self.setProperty('flag_highlight', self.get_setting('fen.scraper_flag_identify_colour', 'FF7C7C7C'))
		self.setProperty('result_highlight', self.get_setting('fen.scraper_result_identify_colour', 'FFFFFFFF'))

	def set_resolver_properties(self):
		if self.meta_get('media_type') == 'movie': self.text = self.meta_get('plot')
		else:
			if avoid_episode_spoilers(): plot = self.meta_get('tvshow_plot') or spoilers_str
			else: plot = self.meta_get('plot', '') or self.meta_get('tvshow_plot', '')
			self.text = '[B]%02dx%02d - %s[/B][CR][CR]%s' % (self.meta_get('season'), self.meta_get('episode'), self.meta_get('ep_name', 'N/A').upper(), plot)
		self.setProperty('highlight_var', self.highlight_value)
		self.setProperty('window_mode', self.window_mode)
		self.setProperty('text', self.text)

	def set_resume_properties(self, percent):
		self.setProperty('window_mode', self.window_mode)
		self.setProperty('resume_percent', percent)
		self.setFocusId(10)
		self.update_resumer()

	def update_scraper(self, results_sd, results_720p, results_1080p, results_4k, results_total, content='', percent=0):
		self.setProperty('results_4k', string(results_4k))
		self.setProperty('results_1080p', string(results_1080p))
		self.setProperty('results_720p', string(results_720p))
		self.setProperty('results_sd', string(results_sd))
		self.setProperty('results_total', string(results_total))
		self.setProperty('percent', string(percent))
		self.set_text(2001, content)

	def update_resolver(self, text='', percent=0):
		try: self.setProperty('percent', string(percent))
		except: pass
		if text: self.set_text(2002, text)

	def update_resumer(self):
		count = 0
		while self.resume_choice is None:
			percent = int((float(count)/resume_timeout)*100)
			if percent >= 100: self.resume_choice = 'resume'
			self.setProperty('percent', string(percent))
			count += 100
			self.sleep(100)

class SourcesInfo(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
		self.item = kwargs['item']
		self.item_get_property = self.item.getProperty
		self.set_properties()

	def run(self):
		self.doModal()

	def onAction(self, action):
		self.close()

	def get_provider_and_path(self):
		try:
			provider = lower(self.item_get_property('provider'))
			icon_path = info_icons_dict[provider]
		except: provider, icon_path = 'folders', get_icon('provider_folder')
		return provider, icon_path

	def get_quality_and_path(self):
		quality = lower(self.item_get_property('quality'))
		icon_path = info_quality_dict[quality]
		return quality, icon_path

	def set_properties(self):
		provider, provider_path = self.get_provider_and_path()
		quality, quality_path = self.get_quality_and_path()
		self.setProperty('name', self.item_get_property('name'))
		self.setProperty('source_type', self.item_get_property('source_type'))
		self.setProperty('source_site', self.item_get_property('source_site'))
		self.setProperty('size_label', self.item_get_property('size_label'))
		self.setProperty('extraInfo', self.item_get_property('extraInfo'))
		self.setProperty('highlight', self.item_get_property('highlight'))
		self.setProperty('hash', self.item_get_property('hash'))
		self.setProperty('provider', provider)
		self.setProperty('quality', quality)
		self.setProperty('provider_icon', provider_path)
		self.setProperty('quality_icon', quality_path)

class SourcesChoice(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
		self.window_id = 5001
		self.xml_choices = kwargs.get('xml_choices')
		self.xml_items = []
		self.make_items()

	def onInit(self):
		self.add_items(self.window_id, self.xml_items)
		self.setFocusId(self.window_id)

	def run(self):
		self.doModal()
		return self.choice

	def onAction(self, action):
		if action in self.closing_actions:
			self.choice = None
			self.close()
		if action in self.selection_actions:
			chosen_listitem = self.get_listitem(self.window_id)
			self.choice = chosen_listitem.getProperty('name')
			self.close()

	def make_items(self):
		append = self.xml_items.append
		for item in self.xml_choices:
			listitem = self.make_listitem()
			listitem.setProperty('name', item[0])
			listitem.setProperty('image', item[1])
			append(listitem)
