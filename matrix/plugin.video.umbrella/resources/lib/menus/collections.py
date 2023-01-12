# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

from datetime import datetime, timedelta
from json import dumps as jsdumps
import re
from threading import Thread
from urllib.parse import quote_plus, parse_qsl, urlparse
from resources.lib.database import cache, metacache, fanarttv_cache
from resources.lib.indexers.tmdb import Movies as tmdb_indexer
from resources.lib.indexers.fanarttv import FanartTv
from resources.lib.modules import cleangenre
from resources.lib.modules import client
from resources.lib.modules import control
from resources.lib.modules.playcount import getMovieIndicators, getMovieOverlay
from resources.lib.modules import trakt
from resources.lib.modules import views

getLS = control.lang
getSetting = control.setting


class Collections:
	def __init__(self):
		self.list = []
		self.page_limit = getSetting('page.item.limit')
		self.enable_fanarttv = getSetting('enable.fanarttv') == 'true'
		self.prefer_tmdbArt = getSetting('prefer.tmdbArt') == 'true'
		self.unairedcolor = control.getColor(getSetting('movie.unaired.identify'))
		self.highlight_color = control.getHighlightColor()
		self.date_time = datetime.now()
		self.today_date = (self.date_time).strftime('%Y-%m-%d')
		self.lang = control.apiLanguage()['trakt']
		self.traktCredentials = trakt.getTraktCredentialsInfo()
		self.imdb_user = getSetting('imdbuser').replace('ur', '')
		self.tmdb_key = getSetting('tmdb.apikey')
		if self.tmdb_key == '' or self.tmdb_key is None: self.tmdb_key = 'bc96b19479c7db6c8ae805744d0bdfe2'
		# self.user = str(self.imdb_user) + str(self.tmdb_key)
		self.user = str(self.tmdb_key)
		self.tmdb_link = 'https://api.themoviedb.org/4/list/%s?api_key=%s&sort_by=%s&page=1' % ('%s', self.tmdb_key, self.tmdb_sort())
		self.tmdbCollection_link = 'https://api.themoviedb.org/3/collection/%s?api_key=%s&page=1' % ('%s', self.tmdb_key) # does not support request sorting
		self.imdb_link = 'https://www.imdb.com/search/title?title=%s&title_type=%s&num_votes=1000,&countries=us&languages=en&sort=%s' % ('%s', '%s', self.imdb_sort())
		self.tmdbCollectionsSearch_link = 'https://api.themoviedb.org/3/search/collection?api_key=%s&language=en-US&query=%s&page=1' % (self.tmdb_key, '%s')
		self.imdblist_hours = int(getSetting('cache.imdblist'))

	def collections_Navigator(self, lite=False):
		self.addDirectoryItem('Movies', 'collections_Boxset', 'boxsets.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Based on a True Story', 'collections&url=%s' % quote_plus(self.tmdb_link % '7102955'), 'movies.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Boxing', 'collections&url=%s' % quote_plus(self.tmdb_link % '7102952'), 'boxing.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Martial Arts', 'collections_MartialArts', 'martial-arts.png', 'DefaultVideoPlaylists.png')
		if control.getMenuEnabled('navi.xmascollections'): self.addDirectoryItem('Christmas Collections', 'collections&url=%s' % quote_plus(self.tmdb_link % '32770'), 'boxsets.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('DC Comics', 'collections&url=%s' % quote_plus(self.tmdb_link % '32799'), 'dc-comics.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Marvel Comics', 'collections&url=%s' % quote_plus(self.tmdb_link % '32793'), 'marvel-comics.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Superheroes', 'collections_Superhero', 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Kids Collections', 'collections_Kids', 'collectionkids.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Search TMDb Collections', 'collections_Search', 'search.png', 'DefaultAddonsSearch.png')
		self.endDirectory()

	def collections_Boxset(self):
		self.addDirectoryItem('12 Rounds (2009-2015)', 'collections&url=%s' % quote_plus(self.tmdb_link % '13120'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('300 (2007-2014)', 'collections&url=%s' % quote_plus(self.tmdb_link % '13132'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('48 Hrs. (1982-1990)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33259'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Ace Ventura (1994-1995)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33260'), 'https://assets.fanart.tv/fanart/movies/3167/movieposter/ace-ventura-collection-5783ce46b408a.jpg', 'https://assets.fanart.tv/fanart/movies/3167/moviethumb/ace-ventura-collection-5d49919488f09.jpg')
		self.addDirectoryItem('Airplane (1980-1982)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33261'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Airport (1970-1979)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33262'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('American Graffiti (1973-1979)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33263'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Anaconda (1997-2004)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33264'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Analyze This (1999-2002)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33265'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Anchorman (2004-2013)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33266'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Austin Powers (1997-2002)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33267'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('AVP (2004-2007)', 'collections&url=%s' % quote_plus(self.tmdb_link % '13199'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Back to the Future (1985-1990)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33268'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Bad Ass (2012-2015)', 'collections&url=%s' % quote_plus(self.tmdbCollection_link % '261286'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Bad Boys (1995-2020)', 'collections&url=%s' % quote_plus(self.tmdbCollection_link % '14890'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Bad Santa (2003-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33270'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Basic Instinct (1992-2006)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33271'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Best Of The Best (1989-1998)', 'collections&url=%s' % quote_plus(self.tmdb_link % '13269'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Beverly Hills Cop (1984-1994)', 'collections&url=%s' % quote_plus(self.tmdbCollection_link % '85861'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Big Mommas House (2000-2011)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33273'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Bloodsport (1988-2010)', 'collections&url=%s' % quote_plus(self.tmdb_link % '13281'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Blues Brothers (1980-1998)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33274'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Bourne (2002-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33275'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Bruce Almighty (2003-2007)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33276'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Bruce Lee (1965-2017)', 'collections&url=%s' % quote_plus(self.tmdb_link % '13295'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Caddyshack (1980-1988)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33277'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Cats & Dogs (2001-2010)', 'collections&url=%s' % quote_plus(self.tmdb_link % '16501'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Cheaper by the Dozen (2003-2005)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33278'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Cheech and Chong (1978-1984)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33420'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Childs Play (1988-2004)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33279'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('City Slickers (1991-1994)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33280'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Conan (1982-2011)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33281'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Crank (2006-2009)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33282'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Crocodile Dundee (1986-2001)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33419'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Crow (1994-2005)', 'collections&url=%s' % quote_plus(self.tmdb_link % '13294'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Da Vinci Code (2006-2017)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33283'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Daddy Day Care (2003-2007)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33284'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Death Wish (1974-1994)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33285'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Delta Force (1986-1990)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33286'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Die Hard (1988-2013)', 'collections&url=%s' % quote_plus(self.tmdbCollection_link % '1570'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Dirty Dancing (1987-2004)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33288'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Dirty Harry (1971-1988)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33289'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Divergent (2014-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '13311'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Dumb and Dumber (1994-2014)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33290'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Escape from New York (1981-1996)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33291'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Every Which Way But Loose (1978-1980)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33292'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Exorcist (1973-2005)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33293'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Expendables (2010-2022)', 'collections&url=%s' % quote_plus(self.tmdbCollection_link % '126125'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Fantastic Beasts (2016-2022)', 'collections&url=%s' % quote_plus(self.tmdbCollection_link % '435259'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Fast and the Furious (2001-2023)', 'collections&url=%s' % quote_plus(self.tmdbCollection_link % '9485'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Father of the Bride (1991-1995)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33295'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Final Destination (2000-2011)', 'collections&url=%s' % quote_plus(self.tmdbCollection_link % '8864'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Fletch (1985-1989)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33296'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Fly (1986-1989)', 'collections&url=%s' % quote_plus(self.tmdb_link % '13303'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Friday (1995-2002)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33297'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Friday the 13th (1980-2009)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33298'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Fugitive (1993-1998)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33299'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('G.I. Joe (2009-2013)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33300'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Get Shorty (1995-2005)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33301'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Gettysburg (1993-2003)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33302'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Ghost Rider (2007-2011)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33303'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Ghostbusters (1984-2016)', 'collections&url=%s' % quote_plus(self.tmdbCollection_link % '2980'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Gods Not Dead (2014-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33304'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Godfather (1972-1990)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33305'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Godzilla (1956-2021)', 'collections&url=%s' % quote_plus(self.tmdb_link % '7106850'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Grown Ups (2010-2013)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33307'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Grumpy Old Men (2010-2013)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33308'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Guns of Navarone (1961-1978)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33309'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Halloween (1978-2009)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33310'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Hangover (2009-2013)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33311'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Hannibal Lector (1986-2007)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33312'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Hellraiser (1987-1996)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33313'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Highlander (1986-2007)', 'collections&url=%s' % quote_plus(self.tmdb_link % '141257'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Hobbit (1977-2014)', 'collections&url=%s' % quote_plus(self.imdb_link % ('the+hobbit', 'feature,tv_movie')), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Hollow Man (2000-2006)', 'collections&url=%s' % quote_plus(self.tmdb_link % '13251'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Honey I Shrunk the Kids (1989-1995)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33208'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Horrible Bosses (2011-2014)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33314'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Hostel (2005-2011)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33315'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Hot Shots (1991-1996)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33316'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Hunger Games (2012-2015)', 'collections&url=%s' % quote_plus(self.tmdbCollection_link % '131635'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Huntsman (2012-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '13235'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Independence Day (1996-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33317'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Indiana Jones (1981-2021)', 'collections&url=%s' % quote_plus(self.tmdb_link % '113191'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Insidious (2010-2015)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33319'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Iron Eagle (1986-1992)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33320'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Jack Reacher (2012-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33321'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Jack Ryan (1990-2014)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33322'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Jackass (2002-2022)', 'collections&url=%s' % quote_plus(self.tmdbCollection_link % '17178'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('James Bond (1962-2021)', 'collections&url=%s' % quote_plus(self.tmdbCollection_link % '645'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Jaws (1975-1987)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33325'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Jeepers Creepers (2001-2017)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33326'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('John Wick (2014-2021)', 'collections&url=%s' % quote_plus(self.tmdb_link % '113190'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Journey to the Center of the Earth (2008-2012)', 'collections&url=%s' % quote_plus(self.tmdb_link % '13216'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Judge Dredd (1995-2012)', 'collections&url=%s' % quote_plus(self.tmdb_link % '13215'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Jumanji (1995-2019)', 'collections&url=%s' % quote_plus(self.tmdb_link % '113189'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Jump Street (2012-2014)', 'collections&url=%s' % quote_plus(self.tmdb_link % '13213'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Jurassic Park (1993-2021)', 'collections&url=%s' % quote_plus(self.tmdb_link % '113188'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Kick-Ass (2010-2013)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33329'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Kill Bill (2003-2004)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33330'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('King Kong (1933-2020)', 'collections&url=%s' % quote_plus(self.tmdb_link % '113082'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Lara Croft (2001-2003)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33332'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Legally Blonde (2001-2003)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33333'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Lethal Weapon (1987-1998)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33334'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Look Whos Talking (1989-1993)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33335'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Lord of The Rings (1978-2003)', 'collections&url=%s' % quote_plus(self.imdb_link % ('the+lord+of+the+rings', 'feature')), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Machete (2010-2013)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33336'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Mad Max (1979-2015)', 'collections&url=%s' % quote_plus(self.tmdb_link % '13188'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Magic Mike (2012-2015)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33337'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Major League (1989-1998)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33338'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Man from Snowy River (1982-1988)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33339'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Mask (1994-2005)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33340'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Matrix (1999-2021)', 'collections&url=%s' % quote_plus(self.tmdbCollection_link % '2344'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Maze Runner(2014-2018)', 'collections&url=%s' % quote_plus(self.tmdb_link % '13182'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Mechanic (2011-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33342'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Meet the Parents (2000-2010)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33343'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Men in Black (1997-2012)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33344'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Mighty Ducks (1995-1996)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33345'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Miss Congeniality (2000-2005)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33346'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Missing in Action (1984-1988)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33347'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Mission Impossible (1996-2021)', 'collections&url=%s' % quote_plus(self.tmdb_link % '113187'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Mummy (1999-2017)', 'collections&url=%s' % quote_plus(self.imdb_link % ('mummy', 'feature')), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Musketeers (1921-2018)', 'collections&url=%s' % quote_plus(self.tmdb_link % '8191200'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Naked Gun (1988-1994)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33349'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('National Lampoon (1978-2006)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33350'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('National Lampoons Vacation (1983-2015)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33351'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('National Treasure (2004-2007)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33352'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Neighbors (2014-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33353'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Night at the Museum (2006-2014)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33354'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Nightmare on Elm Street (1984-2010)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33355'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Now You See Me (2013-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33356'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Nutty Professor (1996-2000)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33357'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Oceans Eleven (2001-2007)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33358'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Odd Couple (1968-1998)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33359'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Oh, God (1977-1984)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33360'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Olympus Has Fallen (2013-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33361'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Omen (1976-1981)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33362'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Paul Blart Mall Cop (2009-2015)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33363'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Pirates of the Caribbean (2003-2017)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33364'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Pitch Perfect (2012-2015)', 'collections&url=%s' % quote_plus(self.tmdb_link % '123873'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Planet of the Apes (1968-2017)', 'collections&url=%s' % quote_plus(self.tmdb_link % '13141'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Police Academy (1984-1994)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33366'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Poltergeist (1982-1988)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33367'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Porkys (1981-1985)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33368'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Predator (1987-2018)', 'collections&url=%s' % quote_plus(self.tmdb_link % '13136'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Purge (2013-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33370'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Rambo (1982-2008)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33371'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('RED (2010-2013)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33372'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Revenge of the Nerds (1984-1987)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33373'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Riddick (2000-2013)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33374'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Ride Along (2014-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33375'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Ring (2002-2017)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33418'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('RoboCop (1987-1993)', 'collections&url=%s' % quote_plus(self.tmdb_link % '13115'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Rocky (1976-2015)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33377'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Romancing the Stone (1984-1985)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33378'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Rush Hour (1998-2007)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33379'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Santa Clause (1994-2006)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33380'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Saw (2004-2017)', 'collections&url=%s' % quote_plus(self.tmdbCollection_link % '656'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Sex and the City (2008-2010)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33382'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Shaft (1971-2000)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33383'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Shanghai Noon (2000-2003)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33384'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Sin City (2005-2014)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33385'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Sinister (2012-2015)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33386'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Sister Act (1995-1993)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33387'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Smokey and the Bandit (1977-1986)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33388'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Speed (1994-1997)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33389'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Stakeout (1987-1993)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33390'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Star Trek (1979-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33391'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Star Wars (1977-2019)', 'collections&url=%s' % quote_plus(self.tmdb_link % '113185'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Step Up (2006-2014)', 'collections&url=%s' % quote_plus(self.tmdbCollection_link % '86092'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Sting (1973-1983)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33392'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Taken (2008-2014)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33393'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Taxi (1998-2007)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33394'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Ted (2012-2015)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33395'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Teen Wolf (1985-1987)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33396'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Terminator (1984-2015)', 'collections&url=%s' % quote_plus(self.tmdb_link % '7103416'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Terms of Endearment (1983-1996)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33398'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Texas Chainsaw Massacre (1974-2013)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33399'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Thing (1982-2011)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33400'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Thomas Crown Affair (1968-1999)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33401'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Transformers (2007-2017)', 'collections&url=%s' % quote_plus(self.imdb_link % ('Transformers', 'feature')), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Transporter (2002-2015)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33402'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Tron (1982-2010)', 'collections&url=%s' % quote_plus(self.imdb_link % ('Tron', 'feature')), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Twilight (2008-2012)', 'collections&url=%s' % quote_plus(self.tmdb_link % '7103415'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Under Siege (1992-1995)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33403'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Underworld (2003-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '7103414'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Universal Soldier (1992-2012)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33404'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Wall Street (1987-2010)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33405'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Waynes World (1992-1993)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33406'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Weekend at Bernies (1989-1993)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33407'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Whole Nine Yards (2000-2004)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33408'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('X-Files (1998-2008)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33409'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('xXx (2002-2005)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33410'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Young Guns (1988-1990)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33411'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Zoolander (2001-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33412'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Zorro (1998-2005)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33413'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.endDirectory()

	def collections_martial_arts(self):
		self.addDirectoryItem('All Movies', 'collections&url=%s' % quote_plus(self.tmdb_link % '117973'), 'boxsets.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('By Actors', 'collections_MartialArtsActors', 'people.png', 'DefaultVideoPlaylists.png')
		self.endDirectory()

	def collections_martial_arts_actors(self):
		self.addDirectoryItem('Brandon Lee', 'collections&url=%s' % quote_plus(self.tmdb_link % '117971'), 'https://i.postimg.cc/y8yBGNsG/Brandon-Lee.jpg', 'DefaultActor.png')
		self.addDirectoryItem('Bruce Lee', 'collections&url=%s' % quote_plus(self.tmdb_link % '118011'), 'https://i.postimg.cc/rmcfP8yf/bruce-lee-Biography.jpg', 'DefaultActor.png')
		self.addDirectoryItem('Chuck Norris', 'collections&url=%s' % quote_plus(self.tmdb_link % '118012'), 'https://i.postimg.cc/ZKkx7bfp/Chuck-Norris.jpg', 'DefaultActor.png')
		self.addDirectoryItem('Chow Yun-Fat', 'collections&url=%s' % quote_plus(self.tmdb_link % '118014'), 'https://i.postimg.cc/159f5bXb/Chow-Yun-Fat.jpg', 'DefaultActor.png')
		self.addDirectoryItem('Donnie Yen', 'collections&url=%s' % quote_plus(self.tmdb_link % '118015'), 'https://i.postimg.cc/SsFK0vHT/Donnie-Yen.jpg', 'DefaultActor.png')
		self.addDirectoryItem('Gary Daniels', 'collections&url=%s' % quote_plus(self.tmdb_link % '118035'), 'https://i.postimg.cc/nrdZLRwt/Gary-Daniels.jpg', 'DefaultActor.png')
		self.addDirectoryItem('Jackie Chan', 'collections&url=%s' % quote_plus( self.tmdb_link % '118017'), 'https://i.postimg.cc/90kSSvnz/Jackie-Chan.jpg', 'DefaultActor.png')
		self.addDirectoryItem('Jason Statham', 'collections&url=%s' % quote_plus(self.tmdb_link % '118016'), 'https://i.postimg.cc/K8SpMrSX/Jason-Statham-2019.jpg', 'DefaultActor.png')
		self.addDirectoryItem('Jean-Claude Van Damme', 'collections&url=%s' % quote_plus(self.tmdb_link % '118022'), 'https://i.postimg.cc/HLSfXc9Q/Jean-Claude-Van-Damme.jpg', 'DefaultActor.png')
		self.addDirectoryItem('Jet Li', 'collections&url=%s' % quote_plus(self.tmdb_link % '118023'), 'https://i.postimg.cc/hGGYD4Rh/Jet-Li.jpg', 'DefaultActor.png')
		self.addDirectoryItem('Mark Dacascos', 'collections&url=%s' % quote_plus(self.tmdb_link % '118024'), 'https://i.postimg.cc/4NJQkLgx/Mark-Dacascos.jpg', 'DefaultActor.png')
		self.addDirectoryItem('Michael Jai White', 'collections&url=%s' % quote_plus(self.tmdb_link % '118025'), 'https://i.postimg.cc/hPyTFKs2/Michael-Jai-White.jpg', 'DefaultActor.png')
		self.addDirectoryItem('Philip Ng', 'collections&url=%s' % quote_plus(self.tmdb_link % '118026'), 'https://i.postimg.cc/Kz8myhJ5/Philip-Ng.jpg', 'DefaultActor.png')
		self.addDirectoryItem('Rain', 'collections&url=%s' % quote_plus(self.tmdb_link % '118033'), 'https://i.postimg.cc/sDmdsNG6/Rain.jpg', 'DefaultActor.png')
		self.addDirectoryItem('Robin Shou', 'collections&url=%s' % quote_plus(self.tmdb_link % '118028'), 'https://i.postimg.cc/qMjY96WW/Robin-Shou.jpg', 'DefaultActor.png')
		self.addDirectoryItem('Scott Adkins', 'collections&url=%s' % quote_plus(self.tmdb_link % '118061'), 'https://i.postimg.cc/50SpLZVD/Scott-Adkins.jpg', 'DefaultActor.png')
		self.addDirectoryItem('Steven Seagal', 'collections&url=%s' % quote_plus(self.tmdb_link % '118029'), 'https://i.postimg.cc/0Qhm6n6h/Steven-Seagal.jpg', 'DefaultActor.png')
		self.addDirectoryItem('Tiger Chen', 'collections&url=%s' % quote_plus(self.tmdb_link % '118030'), 'https://i.postimg.cc/gkzcVRv7/Tiger-Chen.jpg', 'DefaultActor.png')
		self.addDirectoryItem('Tony Jaa', 'collections&url=%s' % quote_plus(self.tmdb_link % '118031'), 'https://i.postimg.cc/Bn80pCtm/Tony-Jaa.jpg', 'DefaultActor.png')
		self.endDirectory(content='actors')

	def collections_Superhero(self):
		self.addDirectoryItem('Avengers (2008-2017)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33128'), 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Batman (1989-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33129'), 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Captain America (2011-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33130'), 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Dark Knight Trilogy (2005-2013)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33132'), 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Deadpool (2016-2023)', 'collections&url=%s' % quote_plus(self.tmdb_link % '8176455'), 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Doctor Strange(2016-2022)', 'collections&url=%s' % quote_plus(self.tmdbCollection_link % '618529'), 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Fantastic Four (2005-2015)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33133'), 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Guardians of the Galaxy (2004-2023)', 'collections&url=%s' % quote_plus(self.tmdb_link % '8192726'), 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Hulk (2003-2008)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33134'), 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Iron Man (2008-2013)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33135'), 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Spider-Man (2002-2021)', 'collections&url=%s' % quote_plus(self.tmdb_link % '8176456'), 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Superman (1978-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33136'), 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Thor (2011-2022)', 'collections&url=%s' % quote_plus(self.tmdbCollection_link % '131296'), 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('X-Men (2000-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33137'), 'collectionsuperhero.png', 'DefaultVideoPlaylists.png')
		self.endDirectory()

	def collections_Kids(self):
		self.addDirectoryItem('Disney Collection', 'collections&url=%s' % quote_plus(self.tmdb_link % '32800'), 'collectiondisney.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Kids Boxset Collection', 'collections_BoxsetKids', 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Kids Movie Collection', 'collections&url=%s' % quote_plus(self.tmdb_link % '32802'), 'collectionkids.png', 'DefaultVideoPlaylists.png')
		self.endDirectory()

	def collections_BoxsetKids(self):
		self.addDirectoryItem('101 Dalmations (1961-2003)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33182'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Addams Family (1991-1998)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33183'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Aladdin (1992-1996)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33184'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Alvin and the Chipmunks (2007-2015)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33185'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Atlantis (2001-2003)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33186'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Babe (1995-1998)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33187'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Balto (1995-1998)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33188'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Bambi (1942-2006)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33189'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Beauty and the Beast (1991-2017)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33190'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Beethoven (1992-2014)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33191'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Brother Bear (2003-2006)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33192'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Cars (2006-2017)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33193'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Cats & Dogs (2001-2010)', 'collections&url=%s' % quote_plus(self.tmdb_link % '16501'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Cinderella (1950-2007)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33194'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Cloudy With a Chance of Meatballs (2009-2013)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33195'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Despicable Me (2010-2015)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33197'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Finding Nemo (2003-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33198'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Fox and the Hound (1981-2006)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33199'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Free Willy (1993-2010)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33200'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Ghostbusters (1984-2016)', 'collections&url=%s' % quote_plus(self.tmdbCollection_link % '2980'), 'collectionboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Gremlins (1984-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33202'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Happy Feet (2006-2011)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33204'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Harry Potter (2001-2011)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33205'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Home Alone (1990-2012)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33206'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Homeward Bound (1993-1996)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33207'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Honey, I Shrunk the Kids (1989-1997)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33208'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Hotel Transylvania (2012-2015)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33209'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('How to Train Your Dragon (2010-2014)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33210'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Hunchback of Notre Dame (1996-2002)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33211'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Ice Age (2002-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33212'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Kung Fu Panda (2008-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33218'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Lady and the Tramp (1955-2001)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33219'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Lilo and Stitch (2002-2006)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33220'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Madagascar (2005-2014)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33221'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Monsters Inc (2001-2013)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33222'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Mulan (1998-2004)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33223'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Narnia (2005-2010)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33224'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('New Groove (2000-2005)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33225'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Open Season (2006-2015)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33226'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Planes (2013-2014)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33227'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Pocahontas (1995-1998)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33228'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Problem Child (1990-1995)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33229'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Rio (2011-2014)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33230'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Sammys Adventures (2010-2012)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33231'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Scooby-Doo (2002-2014)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33232'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Short Circuit (1986-1988)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33233'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Shrek (2001-2011)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33234'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('SpongeBob SquarePants (2004-2017)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33235'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Spy Kids (2001-2011)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33236'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Stuart Little (1999-2002)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33238'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Tarzan (1999-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33239'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Teenage Mutant Ninja Turtles (1978-2009)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33240'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Jungle Book (1967-2003)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33216'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Karate Kid (1984-2010)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33241'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Lion King (1994-2016)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33242'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Little Mermaid (1989-1995)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33243'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Neverending Story (1984-1994)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33248'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('The Smurfs (2011-2013)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33249'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Tooth Fairy (2010-2012)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33251'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Tinker Bell (2008-2014)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33252'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Tom and Jerry (1992-2013)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33253'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Toy Story (1995-2014)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33254'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('VeggieTales (2002-2008)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33255'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Winnie the Pooh (2000-2005)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33257'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.addDirectoryItem('Wizard of Oz (1939-2013)', 'collections&url=%s' % quote_plus(self.tmdb_link % '33258'), 'collectionkidsboxset.png', 'DefaultVideoPlaylists.png')
		self.endDirectory()

	def get(self, url):
		self.list = []
		try:
			try: url = getattr(self, url + '_link')
			except: pass
			try: u = urlparse(url).netloc.lower()
			except: pass
			if u in self.tmdb_link and any(value in url for value in ('/list/', '/collection/')):
				self.list = tmdb_indexer().tmdb_collections_list(url) # caching handled in list indexer
				if '/collection/' in url: self.sort() # TMDb "/collections/" does not support request sort

			elif u in self.tmdbCollectionsSearch_link and '/search/collection' in url:
				self.list = tmdb_indexer().tmdb_collections_search(url) # caching handled in list indexer
				for i in self.list:
					name = i['name']
					action = 'collections&url=%s' % quote_plus(self.tmdbCollection_link % i['tmdb'])
					poster = i['poster']
					fanart = i['fanart']
					icon = i['poster']
					self.addDirectoryItem(name, action, poster, icon, fanart, context=None, queue=False)
				self.endDirectory()
				return self.list

			elif u in self.imdb_link:
				self.list = cache.get(self.imdb_list, self.imdblist_hours, url)
				self.worker()
			if self.list is None: self.list = []
			self.movieDirectory(self.list)
			return self.list
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def search(self): # update self.addDirectoryItem() to work for methods and not import navigator
		from resources.lib.menus import navigator
		navigator.Navigator().addDirectoryItem(getLS(32603) % self.highlight_color, 'collections_Searchnew', 'search.png', 'DefaultAddonsSearch.png', isFolder=False)
		from sqlite3 import dbapi2 as database
		try:
			if not control.existsPath(control.dataPath): control.makeFile(control.dataPath)
			dbcon = database.connect(control.searchFile)
			dbcur = dbcon.cursor()
			dbcur.executescript('''CREATE TABLE IF NOT EXISTS collections (ID Integer PRIMARY KEY AUTOINCREMENT, term);''')
			dbcur.execute('''SELECT * FROM collections ORDER BY ID DESC''')
			dbcur.connection.commit()
			lst = []
			delete_option = False
			for (id, term) in sorted(dbcur.fetchall(), key=lambda k: re.sub(r'(^the |^a |^an )', '', k[1].lower()), reverse=False):
				if term not in str(lst):
					delete_option = True
					navigator.Navigator().addDirectoryItem(term, 'collections_Searchterm&name=%s' % term, 'search.png', 'DefaultAddonsSearch.png', isSearch=True, table='collections')
					lst += [(term)]
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
		if delete_option: navigator.Navigator().addDirectoryItem(32605, 'cache_clearSearch', 'tools.png', 'DefaultAddonService.png', isFolder=False)
		navigator.Navigator().endDirectory()

	def search_new(self):
		k = control.keyboard('', getLS(32010))
		k.doModal()
		q = k.getText() if k.isConfirmed() else None
		if not q: return control.closeAll()
		from sqlite3 import dbapi2 as database
		try:
			dbcon = database.connect(control.searchFile)
			dbcur = dbcon.cursor()
			dbcur.execute('''INSERT INTO collections VALUES (?,?)''', (None, q))
			dbcur.connection.commit()
		except:
			from resources.lib.modules import log_utils
			log_utils.error()
		finally:
			dbcur.close() ; dbcon.close()
		url = self.tmdbCollectionsSearch_link % quote_plus(q)
		control.closeAll()
		control.execute('ActivateWindow(Videos,plugin://plugin.video.umbrella/?action=collections&url=%s,return)' % (quote_plus(url)))

	def search_term(self, name):
		url = self.tmdbCollectionsSearch_link % quote_plus(name)
		self.get(url)

	def imdb_sort(self):
		sort = int(getSetting('sort.collections.type'))
		imdb_sort = 'alpha'
		if sort == 1: imdb_sort = 'alpha'
		elif sort == 2: imdb_sort = 'user_rating'
		elif sort == 3: imdb_sort = 'release_date'
		imdb_sort_order = ',asc' if (int(getSetting('sort.collections.order')) == 0) else ',desc'
		sort_string = imdb_sort + imdb_sort_order
		return sort_string

	def tmdb_sort(self):
		sort = int(getSetting('sort.collections.type'))
		tmdb_sort = 'title'
		if sort == 1: tmdb_sort = 'title'
		elif sort == 2: tmdb_sort = 'vote_average'
		elif sort == 3: tmdb_sort = 'primary_release_date'
		tmdb_sort_order = '.asc' if (int(getSetting('sort.collections.order')) == 0) else '.desc'
		sort_string = tmdb_sort + tmdb_sort_order
		return sort_string

	def sort(self, type='collections'):
		try:
			if not self.list: return
			attribute = int(getSetting('sort.%s.type' % type))
			reverse = int(getSetting('sort.%s.order' % type)) == 1
			if attribute == 0: reverse = False # Sorting Order is not enabled when sort method is "Default"
			if attribute > 0:
				if attribute == 1:
					try: self.list = sorted(self.list, key=lambda k: re.sub(r'(^the |^a |^an )', '', k['title'].lower()), reverse=reverse)
					except: self.list = sorted(self.list, key=lambda k: k['title'].lower(), reverse=reverse)
				elif attribute == 2: self.list = sorted(self.list, key=lambda k: float(k['rating']), reverse=reverse)
				elif attribute == 3:
					for i in range(len(self.list)):
						if 'premiered' not in self.list[i]: self.list[i]['premiered'] = ''
					self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=reverse)
			elif reverse:
				self.list = list(reversed(self.list))
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def imdb_list(self, url, isRatinglink=False):
		list = []
		try:
			for i in re.findall(r'date\[(\d+)\]', url):
				url = url.replace('date[%s]' % i, (self.date_time - timedelta(days=int(i))).strftime('%Y-%m-%d'))
			result = client.request(url)
			result = result.replace('\n', ' ')
			items = client.parseDOM(result, 'div', attrs = {'class': '.+? lister-item'}) + client.parseDOM(result, 'div', attrs = {'class': 'lister-item .+?'})
			items += client.parseDOM(result, 'div', attrs = {'class': 'list_item.+?'})
		except: return
		next = ''
		try:
			# HTML syntax error, " directly followed by attribute name. Insert space in between. parseDOM can otherwise not handle it.
			result = result.replace('"class="lister-page-next', '" class="lister-page-next')
			next = client.parseDOM(result, 'a', ret='href', attrs = {'class': '.*?lister-page-next.*?'})
			if len(next) == 0:
				next = client.parseDOM(result, 'div', attrs = {'class': 'pagination'})[0]
				next = zip(client.parseDOM(next, 'a', ret='href'), client.parseDOM(next, 'a'))
				next = [i[0] for i in next if 'Next' in i[1]]
			next = url.replace(urlparse(url).query, urlparse(next[0]).query)
			next = client.replaceHTMLCodes(next)
		except: next = ''
		for item in items:
			try:
				title = client.replaceHTMLCodes(client.parseDOM(item, 'a')[1])
				year = client.parseDOM(item, 'span', attrs = {'class': 'lister-item-year.+?'})
				try: year = re.findall(r'(\d{4})', year[0])[0]
				except: continue
				if int(year) > int((self.date_time).strftime('%Y')): continue
				imdb = client.parseDOM(item, 'a', ret='href')[0]
				imdb = re.findall(r'(tt\d*)', imdb)[0]
				list.append({'title': title, 'originaltitle': title, 'year': year, 'imdb': imdb, 'tmdb': '', 'tvdb': '', 'next': next}) # just let super_info() TMDb request provide the meta and pass min to retrieve it
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		return list

	def worker(self):
		try:
			if not self.list: return
			self.meta = []
			total = len(self.list)
			for i in range(0, total): self.list[i].update({'metacache': False})
			self.list = metacache.fetch(self.list, self.lang, self.user)
			for r in range(0, total, 40):
				threads = []
				append = threads.append
				for i in range(r, r + 40):
					if i < total: append(Thread(target=self.super_imdb_info, args=(i,)))
				[i.start() for i in threads]
				[i.join() for i in threads]
			if self.meta: metacache.insert(self.meta)
			self.list = [i for i in self.list if i.get('tmdb')]
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def super_imdb_info(self, i):
		try:
			if self.list[i]['metacache']: return
			imdb, tmdb = self.list[i].get('imdb', ''), self.list[i].get('tmdb', '')
#### -- Missing id's lookup -- ####
			if not tmdb and imdb:
				try:
					result = cache.get(tmdb_indexer().IdLookup, 96, imdb)
					tmdb = str(result.get('id', '')) if result.get('id') else ''
				except: tmdb = ''
			if not tmdb and imdb:
				trakt_ids = trakt.IdLookup('imdb', imdb, 'movie') # "trakt.IDLookup()" caches item
				if trakt_ids: tmdb = str(trakt_ids.get('tmdb', '')) if trakt_ids.get('tmdb') else ''
			if not tmdb and not imdb:
				try:
					results = trakt.SearchMovie(title=quote_plus(self.list[i]['title']), year=self.list[i]['year'], fields='title', full=False) # "trakt.SearchMovie()" caches item
					if results[0]['movie']['title'] != self.list[i]['title'] or results[0]['movie']['year'] != self.list[i]['year']: return
					ids = results[0].get('movie', {}).get('ids', {})
					if not tmdb: tmdb = str(ids.get('tmdb', '')) if ids.get('tmdb') else ''
					if not imdb: imdb = str(ids.get('imdb', '')) if ids.get('imdb') else ''
				except: pass
#################################
			if not tmdb: return
			movie_meta = tmdb_indexer().get_movie_meta(tmdb)
			if not movie_meta or '404:NOT FOUND' in movie_meta: return
			values = {}
			values.update(movie_meta)
			if not imdb: imdb = values.get('imdb', '')
			if not values.get('imdb'): values['imdb'] = imdb
			if not values.get('tmdb'): values['tmdb'] = tmdb
			if self.lang != 'en':
				try:
					# if self.lang == 'en' or self.lang not in values.get('available_translations', [self.lang]): raise Exception()
					trans_item = trakt.getMovieTranslation(imdb, self.lang, full=True)
					if trans_item:
						if trans_item.get('title'): values['title'] = trans_item.get('title')
						if trans_item.get('overview'): values['plot'] =trans_item.get('overview')
				except:
					from resources.lib.modules import log_utils
					log_utils.error()
			if self.enable_fanarttv:
				extended_art = fanarttv_cache.get(FanartTv().get_movie_art, 336, imdb, tmdb)
				if extended_art: values.update(extended_art)
			values = dict((k, v) for k, v in iter(values.items()) if v is not None and v != '') # remove empty keys so .update() doesn't over-write good meta with empty values.
			self.list[i].update(values)
			meta = {'imdb': imdb, 'tmdb': tmdb, 'tvdb': '', 'lang': self.lang, 'user': self.user, 'item': values}
			self.meta.append(meta)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def movieDirectory(self, items, next=True):
		from sys import argv # some functions like ActivateWindow() throw invalid handle less this is imported here.
		if not items: # with reuselanguageinvoker on an empty directory must be loaded, do not use sys.exit()
			control.hide() ; control.notification(title=32000, message=33049)
		from resources.lib.modules.player import Bookmarks
		sysaddon, syshandle = 'plugin://plugin.video.umbrella/', int(argv[1])
		play_mode = getSetting('play.mode.movie') 
		rescrape_useDefault = getSetting('rescrape.default') == 'true'
		rescrape_method = getSetting('rescrape.default2')
		is_widget = 'plugin' not in control.infoLabel('Container.PluginName')
		settingFanart = getSetting('fanart') == 'true'
		addonPoster, addonFanart, addonBanner = control.addonPoster(), control.addonFanart(), control.addonBanner()
		indicators = getMovieIndicators() # refresh not needed now due to service sync
		if play_mode == '1': playbackMenu = getLS(32063)
		else: playbackMenu = getLS(32064)
		if trakt.getTraktIndicatorsInfo(): watchedMenu, unwatchedMenu = getLS(32068), getLS(32069)
		else: watchedMenu, unwatchedMenu = getLS(32066), getLS(32067)
		playlistManagerMenu, queueMenu = getLS(35522), getLS(32065)
		traktManagerMenu, addToLibrary = getLS(32070), getLS(32551)
		nextMenu, clearSourcesMenu = getLS(32053), getLS(32611)
		rescrapeMenu, rescrapeAllMenu, findSimilarMenu = getLS(32185), getLS(32193), getLS(32184)
		for i in items:
			try:
				imdb, tmdb, title, year = i.get('imdb', ''), i.get('tmdb', ''), i['title'], i.get('year', '')
				trailer, runtime = i.get('trailer'), i.get('duration')
				label = '%s (%s)' % (title, year)
				try:
					if int(re.sub(r'[^0-9]', '', str(i['premiered']))) > int(re.sub(r'[^0-9]', '', str(self.today_date))):
						label = '[COLOR %s][I]%s[/I][/COLOR]' % (self.unairedcolor, label)
				except: pass
				sysname, systitle = quote_plus(label), quote_plus(title)
				meta = dict((k, v) for k, v in iter(i.items()) if v is not None and v != '')
				meta.update({'code': imdb, 'imdbnumber': imdb, 'mediatype': 'movie', 'tag': [imdb, tmdb]})
				try: meta.update({'genre': cleangenre.lang(meta['genre'], self.lang)})
				except: pass
				if self.prefer_tmdbArt: poster = meta.get('poster3') or meta.get('poster') or meta.get('poster2') or addonPoster
				else: poster = meta.get('poster2') or meta.get('poster3') or meta.get('poster') or addonPoster
				fanart = ''
				if settingFanart:
					if self.prefer_tmdbArt: fanart = meta.get('fanart3') or meta.get('fanart') or meta.get('fanart2') or addonFanart
					else: fanart = meta.get('fanart2') or meta.get('fanart3') or meta.get('fanart') or addonFanart
				landscape = meta.get('landscape') or fanart
				thumb = meta.get('thumb') or poster or landscape
				icon = meta.get('icon') or poster
				banner = meta.get('banner3') or meta.get('banner2') or meta.get('banner') or addonBanner
				art = {}
				art.update({'icon': icon, 'thumb': thumb, 'banner': banner, 'poster': poster, 'fanart': fanart, 'landscape': landscape, 'clearlogo': meta.get('clearlogo', ''),
								'clearart': meta.get('clearart', ''), 'discart': meta.get('discart', ''), 'keyart': meta.get('keyart', '')})
				for k in ('metacache', 'poster2', 'poster3', 'fanart2', 'fanart3', 'banner2', 'banner3', 'trailer'): meta.pop(k, None)
				meta.update({'poster': poster, 'fanart': fanart, 'banner': banner})
				sysmeta, sysart = quote_plus(jsdumps(meta)), quote_plus(jsdumps(art))
				url = '%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&meta=%s' % (sysaddon, systitle, year, imdb, tmdb, sysmeta)
				sysurl = quote_plus(url)
####-Context Menu and Overlays-####
				cm = []
				try:
					watched = getMovieOverlay(indicators, imdb) == '5'
					if self.traktCredentials:
						cm.append((traktManagerMenu, 'RunPlugin(%s?action=tools_traktManager&name=%s&imdb=%s&watched=%s)' % (sysaddon, sysname, imdb, watched)))
					if watched:
						cm.append((unwatchedMenu, 'RunPlugin(%s?action=playcount_Movie&name=%s&imdb=%s&query=4)' % (sysaddon, sysname, imdb)))
						meta.update({'playcount': 1, 'overlay': 5})
						# meta.update({'lastplayed': trakt.watchedMoviesTime(imdb)}) # no skin support
					else:
						cm.append((watchedMenu, 'RunPlugin(%s?action=playcount_Movie&name=%s&imdb=%s&query=5)' % (sysaddon, sysname, imdb)))
						meta.update({'playcount': 0, 'overlay': 4})
				except: pass
				cm.append((playlistManagerMenu, 'RunPlugin(%s?action=playlist_Manager&name=%s&url=%s&meta=%s&art=%s)' % (sysaddon, sysname, sysurl, sysmeta, sysart)))
				cm.append((queueMenu, 'RunPlugin(%s?action=playlist_QueueItem&name=%s)' % (sysaddon, sysname)))
				cm.append((addToLibrary, 'RunPlugin(%s?action=library_movieToLibrary&name=%s&title=%s&year=%s&imdb=%s&tmdb=%s)' % (sysaddon, sysname, systitle, year, imdb, tmdb)))
				cm.append((findSimilarMenu, 'Container.Update(%s?action=movies&url=%s)' % (sysaddon, quote_plus('https://api.trakt.tv/movies/%s/related?limit=20&page=1,return' % imdb))))
				cm.append((playbackMenu, 'RunPlugin(%s?action=alterSources&url=%s&meta=%s)' % (sysaddon, sysurl, sysmeta)))
				if not rescrape_useDefault:
					cm.append(('Rescrape Options ------>', 'PlayMedia(%s?action=rescrapeMenu&title=%s&year=%s&imdb=%s&tmdb=%s&meta=%s)' % (sysaddon, systitle, year, imdb, tmdb, sysmeta)))
				else:
					if rescrape_method == '0':
						cm.append((rescrapeMenu, 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&meta=%s&rescrape=true&select=1)' % (sysaddon, systitle, year, imdb, tmdb, sysmeta)))
					if rescrape_method == '1':
						cm.append((rescrapeMenu, 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&meta=%s&rescrape=true&select=0)' % (sysaddon, systitle, year, imdb, tmdb, sysmeta)))
					if rescrape_method == '2':
						cm.append((rescrapeMenu, 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&meta=%s&rescrape=true&all_providers=true&select=1)' % (sysaddon, systitle, year, imdb, tmdb, sysmeta)))
					if rescrape_method == '3':
						cm.append((rescrapeMenu, 'PlayMedia(%s?action=play_Item&title=%s&year=%s&imdb=%s&tmdb=%s&meta=%s&rescrape=true&all_providers=true&select=0)' % (sysaddon, systitle, year, imdb, tmdb, sysmeta)))
				cm.append((clearSourcesMenu, 'RunPlugin(%s?action=cache_clearSources)' % sysaddon))
				cm.append(('[COLOR red]Umbrella Settings[/COLOR]', 'RunPlugin(%s?action=tools_openSettings)' % sysaddon))
####################################
				if trailer: meta.update({'trailer': trailer}) # removed temp so it's not passed to CM items, only infoLabels for skin
				else: meta.update({'trailer': '%s?action=play_Trailer&type=%s&name=%s&year=%s&imdb=%s' % (sysaddon, 'movie', sysname, year, imdb)})
				item = control.item(label=label, offscreen=True)
				if 'castandart' in i: item.setCast(i['castandart'])
				item.setArt(art)
				item.setUniqueIDs({'imdb': imdb, 'tmdb': tmdb})
				item.setProperty('IsPlayable', 'true')
				if is_widget: item.setProperty('isUmbrella_widget', 'true')
				resumetime = Bookmarks().get(name=label, imdb=imdb, tmdb=tmdb, year=str(year), runtime=runtime, ck=True)
				# item.setProperty('TotalTime', str(meta['duration'])) # Adding this property causes the Kodi bookmark CM items to be added
				item.setProperty('ResumeTime', str(resumetime))
				try:
					watched_percent = round(float(resumetime) / float(runtime) * 100, 1) # resumetime and runtime are both in seconds
					item.setProperty('percentplayed', str(watched_percent))
				except: pass
				item.setInfo(type='video', infoLabels=control.metadataClean(meta))
				item.addContextMenuItems(cm)
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		if next:
			try:
				if not items: raise Exception()
				url = items[0]['next']
				if not url: raise Exception()
				url_params = dict(parse_qsl(url))
				if 'imdb.com' in url and 'start' in url_params:
					page = '  [I](%s)[/I]' % str(((int(url_params.get('start')) - 1) / int(self.page_limit)) + 1)
				else:
					page = '  [I](%s)[/I]' % url_params.get('page')
				nextMenu = '[COLOR skyblue]' + nextMenu + page + '[/COLOR]'
				url = '%s?action=collections&url=%s' % (sysaddon, quote_plus(url))
				item = control.item(label=nextMenu, offscreen=True)
				icon = control.addonNext()
				item.setArt({'icon': icon, 'thumb': icon, 'poster': icon, 'banner': icon})
				item.setProperty ('SpecialSort', 'bottom')
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
		control.content(syshandle, 'movies')
		control.directory(syshandle, cacheToDisc=True)
		control.sleep(100)
		views.setView('movies', {'skin.estuary': 55, 'skin.confluence': 500})

	def addDirectoryItem(self, name, action, poster, icon, fanart=None, context=None, queue=False):
		try:
			from sys import argv # some functions like ActivateWindow() throw invalid handle less this is imported here.
			if isinstance(name, int): name = getLS(name)
			artPath = control.artPath()
			if not icon.startswith('Default'): icon = control.joinPath(artPath, icon)
			if poster.startswith('http'): poster = poster
			else: poster = control.joinPath(artPath, poster) if artPath else icon
			if not fanart: fanart = control.addonFanart()
			queueMenu = getLS(32065)
			url = 'plugin://plugin.video.umbrella/?action=%s' % action
			cm = []
			if context: cm.append((getLS(context[0]), 'RunPlugin(plugin://plugin.video.umbrella/?action=%s)' % context[1]))
			if queue: cm.append((queueMenu, 'RunPlugin(plugin://plugin.video.umbrella/?action=playlist_QueueItem)'))
			cm.append(('[COLOR red]Umbrella Settings[/COLOR]', 'RunPlugin(plugin://plugin.video.umbrella/?action=tools_openSettings)'))
			item = control.item(label=name, offscreen=True)
			item.setArt({'icon': icon, 'poster': poster, 'thumb': poster, 'fanart': fanart, 'banner': poster})
			item.setInfo(type='video', infoLabels={'plot': name})
			item.addContextMenuItems(cm)
			control.addItem(handle=int(argv[1]), url=url, listitem=item, isFolder=True)
		except:
			from resources.lib.modules import log_utils
			log_utils.error()

	def endDirectory(self, content=''):
		from sys import argv # some functions like ActivateWindow() throw invalid handle less this is imported here.
		syshandle = int(argv[1])
		skin = control.skin
		if content != 'actors': content = 'addons' if skin == 'skin.auramod' else ''
		else:
			if skin == 'skin.arctic.horizon': pass
			else: content = ''
		control.content(syshandle, content)# some skins use their own thumb for things like "genres" when content type is set here
		control.directory(syshandle, cacheToDisc=True)