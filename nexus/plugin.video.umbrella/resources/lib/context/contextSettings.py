# -*- coding: utf-8 -*-

import xbmc

if __name__ == '__main__':
	plugin = 'plugin://plugin.video.umbrella/'
	path = 'RunPlugin(%s?action=tools_contextUmbrellaSettings&opensettings=false)' % plugin
	xbmc.executebuiltin(path)
	# xbmc.executebuiltin('RunPlugin(%s?action=widgetRefresh)' % plugin) #now part of "tools_contextUmbrellaSettings" action