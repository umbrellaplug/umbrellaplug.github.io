#Added 2/11/25 by Umbrella_Dev for custom artwork
from resources.lib.modules import control
from resources.lib.modules.control import existsPath, dataPath, makeFile, artworkFile
from resources.lib.modules import log_utils
from sqlite3 import dbapi2 as db
from json import loads as jsloads, dumps as jsdumps

def fetch_movie(imdb, tmdb):
	list = ''
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', ('movies',)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (imdb TEXT, tmdb TEXT, poster TEXT, fanart TEXT, landscape TEXT, banner TEXT, clearart TEXT, clearlogo TEXT, discart TEXT, keyart TEXT, UNIQUE(imdb));''' % 'movies')
			dbcur.connection.commit()
			return list
		try:
			match = dbcur.execute('''SELECT * FROM movies WHERE imdb=?''' , (imdb,)).fetchall()
			list = [{'imdb': i[0], 'tmdb': i[1], 'poster': i[2], 'fanart': i[3], 'landscape': i[4], 'banner': i[5], 'clearart': i[6], 'clearlogo': i[7], 'discart': i[8], 'keyart': i[9]} for i in match]
		except: pass
	except:
		
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()
	return list

def fetch_show(imdb=None, tmdb=None, tvdb=None):
	list = ''
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', ('shows',)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (imdb TEXT, tmdb TEXT, tvdb TEXT, poster TEXT, fanart TEXT, landscape TEXT, banner TEXT, clearart TEXT, clearlogo TEXT, season TEXT, episode TEXT, UNIQUE(imdb));''' % 'shows')
			dbcur.connection.commit()
			return list
		try:
			match = dbcur.execute('''SELECT * FROM shows WHERE imdb=? or tvdb=?''' , (imdb, tvdb,)).fetchall()
			list = [{'imdb': i[0], 'tmdb': i[1], 'tvdb': i[2], 'poster': i[3], 'fanart': i[4], 'landscape': i[5], 'banner': i[6], 'clearart': i[7], 'clearlogo': i[8], 'season': i[8], 'episode': i[9]} for i in match]
		except: pass
	except:
		
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()
	return list

def fetch_season(imdb=None, tmdb=None, tvdb=None, season=None):
	list = ''
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', ('seasons',)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (imdb TEXT, tmdb TEXT, tvdb TEXT, poster TEXT, fanart TEXT, landscape TEXT, banner TEXT, clearart TEXT, clearlogo TEXT, season TEXT, UNIQUE(imdb, season));''' % 'seasons')
			dbcur.connection.commit()
			return list
		try:
			match = dbcur.execute('''SELECT * FROM seasons WHERE (imdb=? OR tvdb=?) AND season=?''', (imdb, tvdb, season)).fetchall()
			list = [{'imdb': i[1], 'tmdb': i[2], 'tvdb': i[3], 'poster': i[4], 'fanart': i[5], 'landscape': i[6], 'banner': i[7], 'clearart': i[8], 'clearlogo': i[9], 'season': i[10]} for i in match]
		except: pass
	except:
		
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()
	return list

def manager(**kwargs):
	mediatype = kwargs.get('mediatype')
	imdb = kwargs.get('imdb')
	tmdb = kwargs.get('tmdb')
	tvdb = kwargs.get('tvdb')
	season = kwargs.get('season')
	episode = kwargs.get('episode')
	poster = kwargs.get('poster')
	fanart = kwargs.get('fanart')
	landscape = kwargs.get('landscape')
	banner = kwargs.get('banner')
	clearlogo = kwargs.get('clearlogo')
	clearart = kwargs.get('clearart')
	discart = kwargs.get('discart')
	keyart = kwargs.get('keyart')
	lists = []
	try:
		if season: season = int(season)
		if episode: episode = int(episode)
		#media_type = 'Show' if tvdb else 'Movie'
		mediatype = mediatype
		items = []
		movieartworkItems = [{'poster': poster}, {'fanart': fanart}, {'landscape': landscape},{'banner': banner},{'clearart': clearart}, {'clearlogo': clearlogo}, {'discart': discart}, {'keyart': keyart}]
		tvshowartworkItems = [{'poster': poster}, {'fanart': fanart}, {'landscape': landscape},{'banner': banner},{'clearart': clearart}, {'clearlogo': clearlogo}]
		if mediatype == 'movie':
			for artwork in movieartworkItems:
				for key, value in artwork.items():
					item = control.item(label=key, offscreen=True)
					item.setArt({'thumb': value})
					items.append(item)
		else:
			for artwork in tvshowartworkItems:
				for key, value in artwork.items():
					item = control.item(label=key, offscreen=True)
					item.setArt({'thumb': value})
					items.append(item)
		resetItem = control.item(label='Reset All', offscreen=True)
		items.append(resetItem)

		control.hide()
		select = control.selectDialog(items, heading=control.addonInfo('name') + ' - ' + 'Customize Artwork', useDetails=True)
		if select == -1: return
		if select >= 0:
			if items[select].getLabel() == 'Reset All':
				delete_artwork(season=season, episode=episode, media_type=mediatype,imdb=imdb, tmdb=tmdb)
			if items[select].getLabel() == 'poster':
				heading = str(items[select].getLabel()) + ' artwork for: %s' % control.infoLabel('Container.ListItem.Title')
				show_artwork_window(season=season, episode=episode, imdb=imdb, tmdb=tmdb, tvdb=tvdb, mediatype=mediatype, heading=heading, artworktype=str(items[select].getLabel()), title=control.infoLabel('Container.ListItem.Title'), poster=poster, fanart=fanart, landscape=landscape, banner=banner, clearart=clearart, clearlogo=clearlogo, discart=discart, keyart=keyart)
			if items[select].getLabel() == 'fanart':
				heading = str(items[select].getLabel()) + ' artwork for: %s' % control.infoLabel('Container.ListItem.Title')
				show_artwork_window(season=season, episode=episode, imdb=imdb, tmdb=tmdb, tvdb=tvdb, mediatype=mediatype, heading=heading, artworktype=str(items[select].getLabel()), title=control.infoLabel('Container.ListItem.Title'), poster=poster, fanart=fanart, landscape=landscape, banner=banner, clearart=clearart, clearlogo=clearlogo, discart=discart, keyart=keyart)
			if items[select].getLabel() == 'landscape':
				heading = str(items[select].getLabel()) + ' artwork for: %s' % control.infoLabel('Container.ListItem.Title')
				show_artwork_window(season=season, episode=episode, imdb=imdb, tmdb=tmdb, tvdb=tvdb, mediatype=mediatype, heading=heading, artworktype=str(items[select].getLabel()), title=control.infoLabel('Container.ListItem.Title'), poster=poster, fanart=fanart, landscape=landscape, banner=banner, clearart=clearart, clearlogo=clearlogo, discart=discart, keyart=keyart)
			if items[select].getLabel() == 'banner':
				heading = str(items[select].getLabel()) + ' artwork for: %s' % control.infoLabel('Container.ListItem.Title')
				show_artwork_window(season=season, episode=episode, imdb=imdb, tmdb=tmdb, tvdb=tvdb, mediatype=mediatype, heading=heading, artworktype=str(items[select].getLabel()), title=control.infoLabel('Container.ListItem.Title'), poster=poster, fanart=fanart, landscape=landscape, banner=banner, clearart=clearart, clearlogo=clearlogo, discart=discart, keyart=keyart)
			if items[select].getLabel() == 'clearart':
				heading = str(items[select].getLabel()) + ' artwork for: %s' % control.infoLabel('Container.ListItem.Title')
				show_artwork_window(season=season, episode=episode, imdb=imdb, tmdb=tmdb, tvdb=tvdb, mediatype=mediatype, heading=heading, artworktype=str(items[select].getLabel()), title=control.infoLabel('Container.ListItem.Title'), poster=poster, fanart=fanart, landscape=landscape, banner=banner, clearart=clearart, clearlogo=clearlogo, discart=discart, keyart=keyart)
			if items[select].getLabel() == 'clearlogo':
				heading = str(items[select].getLabel()) + ' artwork for: %s' % control.infoLabel('Container.ListItem.Title')
				show_artwork_window(season=season, episode=episode, imdb=imdb, tmdb=tmdb, tvdb=tvdb, mediatype=mediatype, heading=heading, artworktype=str(items[select].getLabel()), title=control.infoLabel('Container.ListItem.Title'), poster=poster, fanart=fanart, landscape=landscape, banner=banner, clearart=clearart, clearlogo=clearlogo, discart=discart, keyart=keyart)
			if items[select].getLabel() == 'discart':
				heading = str(items[select].getLabel()) + ' artwork for: %s' % control.infoLabel('Container.ListItem.Title')
				show_artwork_window(season=season, episode=episode, imdb=imdb, tmdb=tmdb, tvdb=tvdb, mediatype=mediatype, heading=heading, artworktype=str(items[select].getLabel()), title=control.infoLabel('Container.ListItem.Title'), poster=poster, fanart=fanart, landscape=landscape, banner=banner, clearart=clearart, clearlogo=clearlogo, discart=discart, keyart=keyart)
			if items[select].getLabel() == 'keyart':
				heading = str(items[select].getLabel()) + ' artwork for: %s' % control.infoLabel('Container.ListItem.Title')
				show_artwork_window(season=season, episode=episode, imdb=imdb, tmdb=tmdb, tvdb=tvdb, mediatype=mediatype, heading=heading, artworktype=str(items[select].getLabel()), title=control.infoLabel('Container.ListItem.Title'), poster=poster, fanart=fanart, landscape=landscape, banner=banner, clearart=clearart, clearlogo=clearlogo, discart=discart, keyart=keyart)
			control.hide()

			is_widget = 'plugin' not in control.infoLabel('Container.PluginName')
			if is_widget: control.trigger_widget_refresh()
			control.refresh()
			
	except:
		log_utils.error()
		control.hide()

def show_artwork_window(**kwargs):
	global mediatype, heading, artworkType, imdb, tmdb, tvdb, season, episode, title
	global poster, fanart, landscape, banner, clearart, clearlogo, discart, keyart

	mediatype = kwargs.get('mediatype', '')
	heading = kwargs.get('heading', 'Umbrella Art')
	artworkType = kwargs.get('artworktype', '')
	imdb = kwargs.get('imdb', '')
	tmdb = kwargs.get('tmdb', '')
	tvdb = kwargs.get('tvdb', '')
	season = kwargs.get('season', '')
	episode = kwargs.get('episode', '')
	title = kwargs.get('title')
	poster = kwargs.get('poster')
	fanart = kwargs.get('fanart')
	landscape = kwargs.get('landscape')
	banner = kwargs.get('banner')
	clearart = kwargs.get('clearart')
	clearlogo = kwargs.get('clearlogo')
	discart = kwargs.get('discart')
	keyart = kwargs.get('keyart')

	try:
		control.busy()
		items = get_artwork(imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, mediatype=mediatype, artwork_type=artworkType)
		if not items: 
			return control.notification(title, 'No %s artwork found.' % artworkType)

		resetItem = {'artworkType': items[0]['artworkType'], 'source': 'Reset to Default', 'url': ''}
		items.append(resetItem)
		control.hide()
		itemsDumped = jsdumps(items)

		from resources.lib.windows.artselection import ArtSelect
		window = ArtSelect('artwork.xml', control.addonPath(control.addonId()), mediatype=mediatype, heading=heading, items=itemsDumped)
		selected_items = window.run()
		del window

		if selected_items or selected_items == 0:
			selectedUrl = items[selected_items].get('url')

			if mediatype == 'show' and selectedUrl == '':
				delete_artwork_one_item(media_type=mediatype, artworkType=artworkType, imdb=imdb, tvdb=tvdb)
				return
			if mediatype == 'movie' and selectedUrl == '':
				delete_artwork_one_item(media_type=mediatype, artworkType=artworkType, imdb=imdb)
				return
			if mediatype == 'season' and selectedUrl == '':
				delete_artwork_one_item(media_type=mediatype, artworkType=artworkType, imdb=imdb, season=season)
				return

			globals()[artworkType] = selectedUrl

			if mediatype == 'show':
				add_show_entry(artworkType=artworkType, media_type=mediatype, imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, url=selectedUrl)
			if mediatype == 'movie':
				add_movie_entry(artworkType=artworkType, media_type=mediatype, imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, url=selectedUrl)
			if mediatype == 'season':
				add_season_entry(artworkType=artworkType, media_type=mediatype, imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, url=selectedUrl)
			if control.setting('debug.level') == '1':
				from resources.lib.modules import log_utils
				log_utils.log('selected item: %s' % str(items[selected_items]), 1)

		control.hide()
		manager(mediatype=mediatype, imdb=imdb, tmdb=tmdb, tvdb=tvdb, season=season, episode=episode, 
				poster=poster, fanart=fanart, landscape=landscape, banner=banner, clearart=clearart, 
				clearlogo=clearlogo, discart=discart, keyart=keyart)

	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		control.hide()

def get_artwork(**kwargs):
	arttype = kwargs.get('mediatype')
	if arttype == 'movie':
		artworkList = []
		from resources.lib.indexers import fanarttv
		fanartList = fanarttv.FanartTv().get_all_movie_art(imdb=kwargs.get('imdb',''), tmdb=kwargs.get('tmdb',''), artwork_type=kwargs.get('artwork_type'))
		if fanartList and fanartList != '404:NOT FOUND':
			artworkList.extend(fanartList)
		from resources.lib.indexers import tmdb
		tmdbList = tmdb.Movies().get_all_movie_art(imdb=kwargs.get('imdb',''), tmdb=kwargs.get('tmdb',''), artwork_type=kwargs.get('artwork_type'))
		if tmdbList:
			artworkList.extend(tmdbList)
		return artworkList
	if arttype == 'show' or 'season':
		artworkList = []
		from resources.lib.indexers import fanarttv
		fanartList = fanarttv.FanartTv().get_all_show_art(imdb=kwargs.get('imdb',''), tmdb=kwargs.get('tmdb',''), tvdb=kwargs.get('tvdb',''), artwork_type=kwargs.get('artwork_type'))
		if fanartList and fanartList != '404:NOT FOUND':
			artworkList.extend(fanartList)
		from resources.lib.indexers import tmdb
		tmdbList = tmdb.TVshows().get_all_show_art(imdb=kwargs.get('imdb',''), tmdb=kwargs.get('tmdb',''), tvdb=kwargs.get('tvdb',''), artwork_type=kwargs.get('artwork_type'))
		if tmdbList:
			artworkList.extend(tmdbList)
		return artworkList

	else:
		pass
	return type

def delete_artwork(**kwargs):
	if kwargs.get('media_type') == 'movie':
		try:
			dbcon = get_connection()
			dbcur = get_connection_cursor(dbcon)
			ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', ('movies',)).fetchone()
			if not ck_table:
				dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (imdb TEXT, tmdb TEXT, poster TEXT, fanart TEXT, landscape TEXT, banner TEXT, clearart TEXT, clearlogo TEXT, discart TEXT, keyart TEXT, UNIQUE(imdb));''' % 'movies')
				dbcur.connection.commit()
			try:
				imdb = kwargs.get('imdb','')
				dbcur.execute("DELETE FROM movies WHERE imdb = ?;", (imdb,))
			except Exception as e:
				log_utils.log("Exception: %s" % (str(e)), 1)  # Log the problematic item
			dbcur.connection.commit()
		except:
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
	elif kwargs.get('media_type') == 'show':
		try:
			dbcon = get_connection()
			dbcur = get_connection_cursor(dbcon)
			ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', ('shows',)).fetchone()
			if not ck_table:
				dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (imdb TEXT, tmdb TEXT, tvdb TEXT, poster TEXT, fanart TEXT, landscape TEXT, banner TEXT, clearart TEXT, clearlogo TEXT, season TEXT, episode TEXT, UNIQUE(imdb));''' % 'movies')
				dbcur.connection.commit()
			try:
				imdb = kwargs.get('imdb','')
				dbcur.execute("DELETE FROM shows WHERE imdb = ?;", (imdb,))
			except Exception as e:
				log_utils.log("Exception: %s" % (str(e)), 1)  # Log the problematic item
			dbcur.connection.commit()
		except:
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
	elif kwargs.get('media_type') == 'season':
		try:
			dbcon = get_connection()
			dbcur = get_connection_cursor(dbcon)
			ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', ('seasons',)).fetchone()
			if not ck_table:
				dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (imdb TEXT, tmdb TEXT, tvdb TEXT, poster TEXT, fanart TEXT, landscape TEXT, banner TEXT, clearart TEXT, clearlogo TEXT, season TEXT, UNIQUE(imdb, season));''' % 'seasons')
				dbcur.connection.commit()
			try:
				imdb = kwargs.get('imdb','')
				dbcur.execute("DELETE FROM seasons WHERE imdb = ? and season = ?;", (imdb, season,))
			except Exception as e:
				log_utils.log("Exception: %s" % (str(e)), 1)  # Log the problematic item
			dbcur.connection.commit()
		except:
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
	else:
		pass


def delete_artwork_one_item(**kwargs):
	if kwargs.get('media_type') == 'movie':
		try:
			dbcon = get_connection()
			dbcur = get_connection_cursor(dbcon)
			ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', ('movies',)).fetchone()
			if not ck_table:
				dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (imdb TEXT, tmdb TEXT, poster TEXT, fanart TEXT, landscape TEXT, banner TEXT, clearart TEXT, clearlogo TEXT, discart TEXT, keyart TEXT, UNIQUE(imdb));''' % 'movies')
				dbcur.connection.commit()
			try:
				imdb = kwargs.get('imdb','')
				artworkType = kwargs.get('artwork_type')
				dbcur.execute(f"UPDATE movies SET {artworkType} = NULL WHERE imdb = ?;", (imdb,))
			except Exception as e:
				log_utils.log("Exception: %s" % (str(e)), 1)  # Log the problematic item
			dbcur.connection.commit()
		except:
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
	elif kwargs.get('media_type') == 'show':
		try:
			dbcon = get_connection()
			dbcur = get_connection_cursor(dbcon)
			ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', ('shows',)).fetchone()
			if not ck_table:
				dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (imdb TEXT, tmdb TEXT, tvdb TEXT, poster TEXT, fanart TEXT, landscape TEXT, banner TEXT, clearart TEXT, clearlogo TEXT, season TEXT, episode TEXT, UNIQUE(imdb));''' % 'shows')
				dbcur.connection.commit()
			try:
				imdb = kwargs.get('imdb','')
				artworkType = kwargs.get('artwork_type')
				dbcur.execute(f"UPDATE shows SET {artworkType} = NULL WHERE imdb = ?;", (imdb,))
			except Exception as e:
				log_utils.log("Exception: %s" % (str(e)), 1)  # Log the problematic item
			dbcur.connection.commit()
		except:
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
	elif kwargs.get('media_type') == 'season':
		try:
			dbcon = get_connection()
			dbcur = get_connection_cursor(dbcon)
			ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', ('seasons',)).fetchone()
			if not ck_table:
				dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (id INTEGER PRIMARY KEY AUTOINCREMENT, imdb TEXT, tmdb TEXT, tvdb TEXT, poster TEXT, fanart TEXT, landscape TEXT, banner TEXT, clearart TEXT, clearlogo TEXT, season TEXT, UNIQUE(imdb, season));''' % 'seasons')
				dbcur.connection.commit()
			try:
				imdb = kwargs.get('imdb','')
				artworkType = kwargs.get('artwork_type')
				dbcur.execute(f"UPDATE shows SET {artworkType} = NULL WHERE imdb = ? and season = ?;", (imdb, season,))
			except Exception as e:
				log_utils.log("Exception: %s" % (str(e)), 1)  # Log the problematic item
			dbcur.connection.commit()
		except:
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()

def add_movie_entry(**kwargs):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', ('movies',)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (imdb TEXT, tmdb TEXT, poster TEXT, fanart TEXT, landscape TEXT, banner TEXT, clearart TEXT, clearlogo TEXT, discart TEXT, keyart TEXT, UNIQUE(imdb));''' % 'movies')
			dbcur.connection.commit()
		try:
			imdb = kwargs.get('imdb','')
			artworkType =  kwargs.get('artworkType','')
			url = kwargs.get('url','')
			dbcur.execute(f'''INSERT INTO movies (imdb, {artworkType}) Values (?, ?) ON CONFLICT(imdb) DO UPDATE SET {artworkType} = excluded.{artworkType}''', (imdb, url))
		except Exception as e:
			log_utils.log("Exception: %s" % (str(e)), 1)  # Log the problematic item
		dbcur.connection.commit()
	except:
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def add_show_entry(**kwargs):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', ('shows',)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (imdb TEXT, tmdb TEXT, tvdb TEXT, poster TEXT, fanart TEXT, landscape TEXT, banner TEXT, clearart TEXT, clearlogo TEXT, season TEXT, episode TEXT, UNIQUE(imdb));''' % 'shows')
			dbcur.connection.commit()
		try:
			imdb = kwargs.get('imdb','')
			artworkType =  kwargs.get('artworkType','')
			url = kwargs.get('url','')
			dbcur.execute(f'''INSERT INTO shows (imdb, {artworkType}) Values (?, ?) ON CONFLICT(imdb) DO UPDATE SET {artworkType} = excluded.{artworkType}''', (imdb, url))
		except Exception as e:
			log_utils.log("Exception: %s" % (str(e)), 1)  # Log the problematic item
		dbcur.connection.commit()
	except:
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def add_season_entry(**kwargs):
	try:
		dbcon = get_connection()
		dbcur = get_connection_cursor(dbcon)
		ck_table = dbcur.execute('''SELECT * FROM sqlite_master WHERE type='table' AND name=?;''', ('seasons',)).fetchone()
		if not ck_table:
			dbcur.execute('''CREATE TABLE IF NOT EXISTS %s (id INTEGER PRIMARY KEY AUTOINCREMENT, imdb TEXT, tmdb TEXT, tvdb TEXT, poster TEXT, fanart TEXT, landscape TEXT, banner TEXT, clearart TEXT, clearlogo TEXT, season TEXT, UNIQUE(imdb, season));''' % 'seasons')
			dbcur.connection.commit()
		try:
			imdb = kwargs.get('imdb','')
			season = kwargs.get('season','')
			artworkType =  kwargs.get('artworkType','')
			url = kwargs.get('url','')
			dbcur.execute(f'''INSERT INTO seasons (imdb, season, {artworkType}) VALUES (?, ?, ?) ON CONFLICT(imdb, season) DO UPDATE SET {artworkType} = excluded.{artworkType}, season = excluded.season''', (imdb, season, url))
		except Exception as e:
			log_utils.log("Exception: %s" % (str(e)), 1)  # Log the problematic item
		dbcur.connection.commit()
	except:
		log_utils.error()
	finally:
		dbcur.close() ; dbcon.close()

def get_connection(setRowFactory=False):
	if not existsPath(dataPath): makeFile(dataPath)
	dbcon = db.connect(artworkFile, timeout=60)
	dbcon.execute('''PRAGMA page_size = 32768''')
	dbcon.execute('''PRAGMA journal_mode = OFF''')
	dbcon.execute('''PRAGMA synchronous = OFF''')
	dbcon.execute('''PRAGMA temp_store = memory''')
	dbcon.execute('''PRAGMA mmap_size = 30000000000''')
	if setRowFactory: dbcon.row_factory = _dict_factory
	return dbcon

def get_connection_cursor(dbcon):
	dbcur = dbcon.cursor()
	return dbcur

def _dict_factory(cursor, row):
	d = {}
	for idx, col in enumerate(cursor.description): d[col[0]] = row[idx]
	return d