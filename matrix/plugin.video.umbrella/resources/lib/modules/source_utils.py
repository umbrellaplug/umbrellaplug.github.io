# -*- coding: utf-8 -*-
"""
	Umbrella Add-on Updated 8-25-22
"""

import re
from urllib.parse import unquote, unquote_plus

VIDEO_3D = ('.3d.', '.sbs.', '.hsbs', 'sidebyside', 'side.by.side', 'stereoscopic', '.tab.', '.htab.', 'topandbottom', 'top.and.bottom')

DOLBY_VISION = ('dolby.vision', 'dolbyvision', '.dovi.', '.dv.')
HDR = ('2160p.bluray.hevc.truehd', '2160p.bluray.hevc.dts', '2160p.bluray.hevc.lpcm',
			'2160p.blu.ray.hevc.truehd', '2160p.blu.ray.hevc.dts',
			'2160p.uhd.bluray', '2160p.uhd.blu.ray',
			'2160p.us.bluray.hevc.truehd', '2160p.us.bluray.hevc.dts',
			'.hdr.', 'hdr10', 'hdr.10',
			'uhd.bluray.2160p', 'uhd.blu.ray.2160p')
HDR_true = ('.hdr.', 'hdr10', 'hdr.10')

CODEC_H264 = ('avc', 'h264', 'h.264', 'x264', 'x.264')
CODEC_H265 = ('h265', 'h.265', 'hevc', 'x265', 'x.265')
CODEC_XVID = ('xvid', '.x.vid')
CODEC_DIVX = ('divx', 'div2', 'div3', 'div4')
CODEC_MPEG = ('.mpg', '.mp2', '.mpeg', '.mpe', '.mpv', '.m4p', '.m4v', 'msmpeg', 'mpegurl')
CODEC_MP4 = ('.mp4','.mp4.')
CODEC_MKV = ('.mkv', 'matroska')
REMUX = ('remux', 'bdremux')

BLURAY = ('bluray', 'blu.ray', 'bdrip', 'bd.rip', '.brrip.', 'br.rip')
DVD = ('dvdrip', 'dvd.rip')
WEB = ('.web.', 'webdl', 'web.dl', 'web-dl', 'webrip', 'web.rip')
HDRIP = ('.hdrip', '.hd.rip')
SCR = ('scr.', 'screener','dvdscr', 'dvd.scr', '.r5', '.r6')
HC = ('.hc', 'korsub', 'kor.sub')

DOLBY_TRUEHD = ('true.hd', 'truehd')
DOLBY_DIGITALPLUS = ('dolby.digital.plus', 'dolbydigital.plus', 'dolbydigitalplus', 'dd.plus.', 'ddplus', '.ddp.', 'ddp2', 'ddp5', 'ddp7', 'eac3', '.e.ac3', 'e.ac.3')

DOLBY_DIGITALEX = ('.dd.ex.', 'ddex', 'dolby.ex.', 'dolby.digital.ex.', 'dolbydigital.ex.')
DOLBYDIGITAL = ('dd2.', 'dd5', 'dd7', 'dolbyd.', 'dolby.digital', 'dolbydigital', '.ac3', '.ac.3.', '.dd.')

DTSX = ('.dts.x.', 'dtsx')
DTS_HDMA = ('hd.ma', 'hdma')
DTS_HD = ('dts.hd.', 'dtshd')

AUDIO_8CH = ('ch8.', '8ch.', '7.1ch', '7.1.')
AUDIO_7CH = ('ch7.', '7ch.', '6.1ch', '6.1.')
AUDIO_6CH = ('ch6.', '6ch.', '5.1ch', '5.1.')
AUDIO_2CH = ('ch2', '2ch', '2.0ch', '2.0.', 'audio.2.0.', 'stereo')

MULTI_LANG = ('hindi.eng', 'ara.eng', 'ces.eng', 'chi.eng', 'cze.eng', 'dan.eng', 'dut.eng', 'ell.eng', 'esl.eng', 'esp.eng', 'fin.eng', 'fra.eng', 'fre.eng',
				'frn.eng', 'gai.eng', 'ger.eng', 'gle.eng', 'gre.eng', 'gtm.eng', 'heb.eng', 'hin.eng', 'hun.eng', 'ind.eng', 'iri.eng', 'ita.eng', 'jap.eng', 'jpn.eng',
				'kor.eng', 'lat.eng', 'lebb.eng', 'lit.eng', 'nor.eng', 'pol.eng', 'por.eng', 'rus.eng', 'som.eng', 'spa.eng', 'sve.eng', 'swe.eng', 'tha.eng', 'tur.eng',
				'uae.eng', 'ukr.eng', 'vie.eng', 'zho.eng', 'dual.audio', 'dual.yg', 'multi')
LANG = ('arabic', 'bgaudio', 'castellano', 'chinese', 'dutch', 'finnish', 'french', 'german', 'greek', 'hebrew', 'italian', 'latino', 'polish',
				'portuguese', 'russian', 'spanish', 'tamil', 'telugu', 'truefrench', 'truespanish', 'turkish')
ABV_LANG = ('.ara.', '.ces.', '.chi.', '.chs.', '.cze.', '.dan.', '.de.', '.deu.', '.dut.', '.ell.', '.es.', '.esl.', '.esp.', '.fi.', '.fin.', '.fr.', '.fra.', '.fre.', '.frn.', '.gai.', '.ger.', '.gle.', '.gre.',
				'.gtm.', '.he.', '.heb.', '.hi.', '.hin.', '.hun.', '.hindi.', '.ind.', '.iri.', '.it.', '.ita.', '.ja.', '.jap.', '.jpn.', '.ko.', '.kor.', '.lat.', '.nl.', '.lit.', '.nld.', '.nor.', '.pl.', '.pol.',
				'.pt.', '.por.', '.ru.', '.rus.', '.som.', '.spa.', '.sv.', '.sve.', '.swe.', '.tha.', '.tr.', '.tur.', '.uae.', '.uk.', '.ukr.', '.vi.', '.vie.', '.zh.', '.zho.')
SUBS = ('subita', 'subfrench', 'subspanish', 'subtitula', 'swesub', 'nl.subs')
ADS = ('1xbet', 'betwin')

APPLE_TV = ('atvp',)

def seas_ep_filter(season, episode, release_title, split=False):
	try:
		release_title = re.sub(r'[^A-Za-z0-9-]+', '.', unquote(release_title).replace('\'', '')).replace('&', 'and').replace('%', '.percent').lower()
		season = str(season)
		season_fill = season.zfill(2)
		episode = str(episode)
		episode_fill = episode.zfill(2)
		int_episode = int(episode)

		string1 = r'(s<<S>>[.-]?e[p]?[.-]?<<E>>[.-])'
		string2 = r'(season[.-]?<<S>>[.-]?episode[.-]?<<E>>[.-])|' \
						r'([s]?<<S>>[x.]<<E>>[.-])'
		string3 = r'(s<<S>>e<<E1>>[.-]?e?<<E2>>[.-])'
		string4 = r'([.-]<<S>>[.-]?<<E>>[.-])'
		string5 = r'(episode[.-]?<<E>>[.-])'
		string6 = r'([.-]e[p]?[.-]?<<E>>[.-])'

		string_list = []
		append = string_list.append
		append(string1.replace('<<S>>', season_fill).replace('<<E>>', episode_fill))
		append(string1.replace('<<S>>', season).replace('<<E>>', episode_fill))
		append(string1.replace('<<S>>', season_fill).replace('<<E>>', episode))
		append(string1.replace('<<S>>', season).replace('<<E>>', episode))
		append(string2.replace('<<S>>', season_fill).replace('<<E>>', episode_fill))
		append(string2.replace('<<S>>', season).replace('<<E>>', episode_fill))
		append(string2.replace('<<S>>', season_fill).replace('<<E>>', episode))
		append(string2.replace('<<S>>', season).replace('<<E>>', episode))
		append(string3.replace('<<S>>', season_fill).replace('<<E1>>', str(int_episode-1).zfill(2)).replace('<<E2>>', episode_fill))
		append(string3.replace('<<S>>', season_fill).replace('<<E1>>', episode_fill).replace('<<E2>>', str(int_episode+1).zfill(2)))
		append(string4.replace('<<S>>', season_fill).replace('<<E>>', episode_fill))
		append(string4.replace('<<S>>', season).replace('<<E>>', episode_fill))
		append(string5.replace('<<E>>', episode_fill))
		append(string5.replace('<<E>>', episode))
		append(string6.replace('<<E>>', episode_fill))

		final_string = '|'.join(string_list)
		reg_pattern = re.compile(final_string)
		if split: return release_title.split(re.search(reg_pattern, release_title).group(), 1)[1]
		else: return bool(re.search(reg_pattern, release_title))
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return None

def seas_filter(season, release_title, split=False):
	try:
		release_title = re.sub(r'[^A-Za-z0-9-]+', '.', unquote(release_title).replace('\'', '')).replace('&', 'and').replace('%', '.percent').lower()
		season = str(season)
		season_fill = season.zfill(2)

		string1 = r'(s<<S>>[.-])'
		string2 = r'(season[.-]?<<S>>[.-])|' \
						r'([s]?<<S>>[x.])'
		string4 = r'([.-]<<S>>[.-])'

		string_list = []
		append = string_list.append
		append(string1.replace('<<S>>', season_fill))
		append(string1.replace('<<S>>', season))
		append(string1.replace('<<S>>', season_fill))
		append(string1.replace('<<S>>', season))
		append(string2.replace('<<S>>', season_fill))
		append(string2.replace('<<S>>', season))
		append(string2.replace('<<S>>', season_fill))
		append(string2.replace('<<S>>', season))
		append(string4.replace('<<S>>', season_fill))
		append(string4.replace('<<S>>', season))

		final_string = '|'.join(string_list)
		reg_pattern = re.compile(final_string)
		if split: return release_title.split(re.search(reg_pattern, release_title).group(), 1)[1]
		else: return bool(re.search(reg_pattern, release_title))
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return None

def extras_filter():
	return ('sample', 'extra', 'deleted', 'unused', 'footage', 'inside', 'blooper', 'making.of', 'feature', 'featurette', 'behind.the.scenes', 'trailer')

def supported_video_extensions():
	try:
		from xbmc import getSupportedMedia
		supported_video_extensions = getSupportedMedia('video').split('|')
		return [i for i in supported_video_extensions if i != '' and i != '.zip']
	except:
		from resources.lib.modules import log_utils
		log_utils.error()

def scraper_error(provider):
	import traceback
	from resources.lib.modules import log_utils
	failure = traceback.format_exc()
	log_utils.log(provider.upper() + ' - Exception: \n' + str(failure), caller='scraper_error', level=log_utils.LOGERROR)

def getFileType(name_info=None, url=None):
	try:
		file_type = ''
		if name_info: fmt = name_info
		elif url: fmt = url_strip(url)
		if not fmt: return file_type
		if any(value in fmt for value in APPLE_TV): file_type += ' APPLE-TV-PLUS /' #new apple tv plus format keep seeing
		if any(value in fmt for value in VIDEO_3D):  file_type += ' 3D /'
		if '.sdr' in fmt: file_type += ' SDR /'
		elif any(value in fmt for value in DOLBY_VISION): file_type += ' DOLBY-VISION /'
		elif any(value in fmt for value in HDR): file_type += ' HDR /'
		elif all(i in fmt for i in ('2160p', 'remux')): file_type += ' HDR /'
		if ' DOLBY-VISION ' in file_type:
			# if any(value in fmt for value in HDR_true) or 'hybrid' in fmt: file_type += ' HDR /' # for hybrid DV and HDR sources
			if any(value in fmt for value in HDR_true) or any(value in fmt for value in ('hybrid', 'remux.sl.dv.')): file_type += ' HDR /' # for hybrid DV and HDR sources. "remux.sl.dv" is used by plexshares as hybrid sources
		if any(value in fmt for value in CODEC_H264): file_type += ' AVC /'
		if '.av1.' in fmt: file_type += ' AV1 /'
		if any(value in fmt for value in CODEC_H265): file_type += ' HEVC /'
		elif any(i in file_type for i in (' HDR ', ' DOLBY-VISION ')): file_type += ' HEVC /'
		elif any(value in fmt for value in CODEC_XVID): file_type += ' XVID /'
		elif any(value in fmt for value in CODEC_DIVX): file_type += ' DIVX /'

		if '.wmv' in fmt: file_type += ' WMV /'
		elif any(value in fmt for value in CODEC_MPEG): file_type += ' MPEG /'
		elif any(value in fmt for value in CODEC_MP4): file_type += ' MP4 /'
		elif '.avi' in fmt: file_type += ' AVI /'
		elif any(value in fmt for value in CODEC_MKV): file_type += ' MKV /'

		if any(value in fmt for value in REMUX): file_type += ' REMUX /'

		if any(value in fmt for value in BLURAY): file_type += ' BLURAY /'
		elif any(i in fmt for i in DVD): file_type += ' DVD /'
		elif any(value in fmt for value in WEB): file_type += ' WEB /'
		elif 'hdtv' in fmt: file_type += ' HDTV /'
		elif 'pdtv' in fmt: file_type += ' PDTV /'
		elif any(value in fmt for value in SCR): file_type += ' SCR /'
		elif any(value in fmt for value in HDRIP): file_type += ' HDRIP /'

		#if 'opus' in fmt: file_type += ' OPUS /'

		if 'atmos' in fmt: file_type += ' ATMOS /'
		if any(value in fmt for value in DOLBY_TRUEHD): file_type += ' DOLBY-TRUEHD /'
		if any(value in fmt for value in DOLBY_DIGITALPLUS): file_type += ' DD+ /'
		elif any(value in fmt for value in DOLBYDIGITAL): file_type += ' DOLBYDIGITAL /'
		elif any(value in fmt for value in DOLBY_DIGITALEX): file_type += ' DD-EX /'

		if 'aac' in fmt: file_type += ' AAC /'
		elif 'mp3' in fmt: file_type += ' MP3 /'
		elif 'flac' in fmt: file_type += ' FLAC /'
		elif 'opus' in fmt and not fmt.endswith('opus.'): file_type += ' OPUS /' #OPUS also a group titles endswith

		if any(value in fmt for value in DTSX): file_type += ' DTS-X /'
		elif any(value in fmt for value in DTS_HDMA): file_type += ' DTS-HD MA /'
		elif any(value in fmt for value in DTS_HD): file_type += ' DTS-HD /'
		elif '.dts' in fmt: file_type += ' DTS /'

		if any(value in fmt for value in AUDIO_8CH): file_type += ' 8CH /'
		elif any(value in fmt for value in AUDIO_7CH): file_type += ' 7CH /'
		elif any(value in fmt for value in AUDIO_6CH): file_type += ' 6CH /'
		elif any(value in fmt for value in AUDIO_2CH): file_type += ' 2CH /'

		if any(value in fmt for value in HC): file_type += ' HC /'

		if any(value in fmt for value in MULTI_LANG): file_type += ' MULTI-LANG /'
		elif any(value in fmt for value in LANG) and any(value in fmt for value in ('.eng.', '.en.', 'english')): file_type += ' MULTI-LANG /'
		elif any(value in fmt for value in ABV_LANG) and any(value in fmt for value in ('.eng.', '.en.', 'english')):file_type += ' MULTI-LANG /'

		if any(value in fmt for value in ADS): file_type += ' ADS /'
		if any(value in fmt for value in SUBS):
			if file_type != '': file_type += ' WITH SUBS'
			else: file_type = 'SUBS'
		file_type = file_type.rstrip('/') # leave trailing space for cases like " HDR " vs. " HDRIP "
		return file_type
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return ''

def url_strip(url):
	try:
		url = unquote_plus(url)
		if 'magnet:' in url: url = url.split('&dn=')[1]
		url = url.lower().replace("'", "").lstrip('.').rstrip('.')
		fmt = re.sub(r'[^a-z0-9]+', '.', url)
		fmt = '.%s.' % fmt
		fmt = re.sub(r'(.+)((?:19|20)[0-9]{2}|season.\d+|s[0-3]{1}[0-9]{1}|e\d+|complete)(.complete\.|.episode\.\d+\.|.episodes\.\d+\.\d+\.|.series|.extras|.ep\.\d+\.|.\d{1,2}\.|-|\.|\s)', '', fmt) # new for pack files
		if '.http' in fmt: fmt = None
		if fmt == '': return None
		else: return '.%s' % fmt
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return None

def aliases_check(title, aliases):
	fixed_aliases = []
	try:
		bad_aliases = {'Dexter': ['Dexter: New Blood',], 'Titans': ['Teen Titans',]}
		if title in bad_aliases:
			for i in aliases:
				if i.get('title') not in bad_aliases.get(title): fixed_aliases.append(i)
			aliases = fixed_aliases
		if title == 'Gomorrah': aliases.append({'title': 'Gomorra', 'country': ''})
		if title == 'Daredevil': aliases.append({'title': "Marvel's Daredevil", 'country': 'us'})
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
	return aliases

def tvshow_reboots():
	reboots = {
		"Adam-12": "1990", "Battlestar Galactica": "2004", "Charlie's Angels": "2011", "Charmed": "2018", "Dynasty": "2017", "Fantasy Island": "2021",
		"The Flash": "2014", "The Fugitive": "2000", "The Fugitive": "2020", "Ghostwriter": "2019", "Gossip Girl": "2021", "Hawaii Five-0": "2010",
		"Ironside": "2013", "Kojak": "2005", "Kung Fu": "2021", "Lost in Space": "2018", "MacGyver": "2016", "Magnum P.I.": "2018", "Nancy Drew": "2019",
		"The Odd Couple": "2015", "One Day at a Time": "2017", "The Outer Limits": "1995", "Party of Five": "2020", "Perry Mason": "2020", "S.W.A.T.": "2017",
		"The Twilight Zone": "1985", "The Twilight Zone": "2002", "The Twilight Zone": "2019", "The Untouchables": "1993", "V": "2009", "The Wonder Years": "2021"}
	return reboots

def copy2clip(txt):
	from sys import platform
	if platform == "win32":
		try:
			from subprocess import check_call
			# cmd = "echo " + txt.strip() + "|clip"
			cmd = "echo " + txt.replace('&', '^&').strip() + "|clip" # "&" is a command seperator
			return check_call(cmd, shell=True)
		except:
			from resources.lib.modules import log_utils
			log_utils.error('Windows: Failure to copy to clipboard')
	elif platform == "darwin":
		try:
			from subprocess import check_call
			cmd = "echo " + txt.strip() + "|pbcopy"
			return check_call(cmd, shell=True)
		except:
			from resources.lib.modules import log_utils
			log_utils.error('Mac: Failure to copy to clipboard')
	elif platform == "linux":
		try:
			from subprocess import Popen, PIPE
			p = Popen(["xsel", "-pi"], stdin=PIPE)
			p.communicate(input=txt)
		except:
			from resources.lib.modules import log_utils
			log_utils.error('Linux: Failure to copy to clipboard')