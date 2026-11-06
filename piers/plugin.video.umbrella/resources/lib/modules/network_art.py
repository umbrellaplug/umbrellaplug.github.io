"""Bundled network logos, independent of the selected artwork theme."""
from resources.lib.modules.control import addonInfo, joinPath, transPath

_DIRECTORY = joinPath(transPath(addonInfo('path')), 'resources', 'artwork', 'networks')


def network_icon(filename):
    return joinPath(_DIRECTORY, filename)
