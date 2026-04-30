# -*- coding: utf-8 -*-
"""
	Umbrella Add-on
"""

import sys
from resources.lib.modules import router
from xbmc import getInfoLabel
if __name__ == '__main__':
	router.router(sys.argv[2])
	if 'umbrella' not in getInfoLabel('Container.PluginName'): sys.exit(1) #TikiPeter RLI-Fix Test