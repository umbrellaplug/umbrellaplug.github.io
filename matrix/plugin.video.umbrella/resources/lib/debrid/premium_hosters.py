# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

hostprDict = ('4shared.com', 'vidcloud.r', 'fastfile.cc', 'rapidu.net', 'sky.fm', 'upload.ac', 'filer.net', 'goloady.com',
				'backin.net', 'uploadboy.com', 'exload.com', 'turbo.to', 'takefile.link', '2shared.com', 'oboom.com',
				'wupfile.com', 'filerio.com', 'israbox.ch', 'filespace.com', 'uppit.com', 'hitf.cc', 'uploadboy.me',
				'earn4files.com', 'uploadcloud.pro', 'rarefile.net', 'redbunker.net', 'archive.org', 'dailymotion.com',
				'load.to', 'filedown.org', 'mixdrop.club', 'clicknupload.me', 'uloz.to', 'vidtodo.com', 'cosmobox.org',
				'dfichiers.com', 'videobin.co', 'desfichiers.com', 'isra.cloud', 'youporn.com', 'mp4upload.com', 'tezfiles.com',
				'vshare.e', 'filerio.in', 'ex-load.com', 'sendit.cloud', 'faststore.org', 'depositfiles.org', 'gigapeta.com',
				'hexupload.net', 'pjointe.com', 'depositfiles.com', 'filezip.cc', 'cjoint.net', 'flashbit.cc', 'jazzradio.com',
				'florenfile.com', 'hulkshare.com', 'dl.free.fr', 'turbobit.pw', 'hotlink.cc', 'vidlox.tv', 'filestore.to', 'k2share.cc',
				'uploadfiles.e', 'uploaded.net', 'ulozto.net', 'rapidgator.net', 'turbobit.net', 'nowvideo.pw', 'nowvideo.club',
				'turbobit5.net', 'icerbox.com', 'bdupload.in', 'playvidto.com', 'youtu.be', 'radiotunes.com', 'turb.to',
				'file4safe.com', 'dropapk.com', 'nelion.me', 'tusfiles.com', 'inclouddrive.com', 'zippyshare.com', 'keep2share.cc',
				'uploadbox.io', 'thevideo.website', 'simfileshare.net', 'flashx.pw', 'clicknupload.co', 'vidcloud.co', 'uptobox.com',
				'fshare.vn', 'douploads.net', 'giga-down.com', 'gounlimited.to', 'vidto-do.com', 'fireget.com', 'heroupload.com',
				'clicknupload.org', 'real-debrid.com', 'alterupload.com', 'uploadrar.com', 'rockfile.co', 'flashx.net', 'mixloads.com',
				'dfiles.r', 'turbo-bit.net', 'wushare.com', 'bayfiles.com', 'alldebrid.com', 'vidoza.co', 'vidlox.me', 'userscloud.com',
				'bdupload.asia', 'dailyuploads.net', 'isrbx.net', 'anzfile.net', 'zachowajto.pl', 'flashx.co', 'flashx.cc', 'uploadgig.com',
				'btafile.com', 'docs.google.com', 'keep2s.cc', 'mediafire.com', 'hitfile.net', 'ul.to', 'dropapk.to', 'k2s.cc', 'redtube.com',
				'mixdrop.co', 'drive.google.com', 'thevideo.io', 'mesfichiers.org', 'filenext.com', 'speed-down.org', '4downfiles.org',
				'example.com', 'salefiles.com', 'ddownload.com', 'clicknupload.link', 'unibytes.com', 'wayupload.com', 'classicalradio.com',
				'turb.cc', 'feurl.com', 'usersdrive.com', 'vimeo.com', 'letsupload.to', 'filedown.com', 'file-upload.com', 'mexashare.com',
				'datafilehost.com', 'rutube.r', 'vev.io', 'rg.to', 'tusfiles.net', 'rockfile.e', 'wipfiles.net', 'flashx.ws', 'world-files.com',
				'flashx.bz', 'vidoza.net', 'turbobit.cc', 'example.net', 'xubster.com', 'ubiqfile.com', 'catshare.net', 'uploadev.org',
				'fileupload.pw', 'rapidrar.com', 'daofile.com', 'vk.com', 'uploadc.com', 'alfafile.net', 'modsbase.com', 'thevideo.me',
				'tvad.me', 'ulozto.sk', 'youtube.com', 'nitroflare.com', '1fichier.com', 'uploadev.com', 'letsupload.io', 'filedown.net',
				'clicknupload.com', 'extmatrix.com', 'hitf.to', 'mega.nz', 'solidfiles.com', 'rapidgator.asia', 'filefactory.com', 'mega.co.nz',
				'piecejointe.net', 'flashx.tv', 'indishare.me', 'scribd.com', 'megadl.fr', 'upstore.net', 'uptostream.com', 'filesabc.com',
				'letsupload.org', 'dl4free.com', 'filefox.cc', 'tenvoi.com', 'vidoza.org', 'ddl.to', 'file.al', 'cloudvideo.tv', 'dfiles.e',
				'uploadc.ch', 'douploads.com', 'mexa.sh', 'katfile.com', 'worldbytez.com', 'sendspace.com', 'uploaded.to',
				'letsupload.cc', 'di.fm', 'letsupload.co', 'clipwatching.com', 'turbobit.cloud', 'fboom.me', 'brupload.net', 'soundcloud.com',
				'prefiles.com', 'wdupload.com', 'easybytez.com', 'file-up.org')

sourcecfDict = ('rapidmoviez', 'scenerls', 'extratorrent', 'limetorrents', 'torrentgalaxy') #cloudflare only providers

# hostcapDict = ('flashx.tv', 'flashx.to', 'flashx.sx', 'flashx.bz', 'flashx.cc', 'hugefiles.cc', 'hugefiles.net', 'jetload.net', 'jetload.tv',
					# 'jetload.to', 'kingfiles.net', 'streamin.to', 'thevideo.me', 'torba.se', 'uptobox.com', 'uptostream.com', 'vidup.io',
					# 'vidup.me', 'vidup.tv', 'vshare.eu', 'vshare.io', 'vev.io')

# hostblockDict = ('divxme.com', 'divxstage.eu', 'estream.to', 'facebook.com', 'oload.download', 'oload.fun', 'oload.icu', 'oload.info',
					# 'oload.life', 'oload.space', 'oload.stream', 'oload.tv', 'oload.win', 'openload.co', 'openload.io', 'openload.pw', 'rapidvideo.com',
					# 'rapidvideo.is', 'rapidvid.to', 'streamango.com', 'streamcherry.com', 'twitch.tv', 'youtube.com', 'zippyshare.com')