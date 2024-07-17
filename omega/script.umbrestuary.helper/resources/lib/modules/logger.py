# -*- coding: utf-8 -*-
import xbmc


def logger(heading, function):
    xbmc.log("###%s###: %s" % (heading, function), 1)
