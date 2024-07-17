# -*- coding: utf-8 -*-
from xbmcgui import Window
from xbmc import sleep, getInfoLabel
from xbmcvfs import translatePath
from xbmcaddon import Addon
import json
import os

# from modules.logger import logger

window = Window(10000)

PROFILE_PATH = os.path.join(
    translatePath("special://userdata/addon_data/script.umbrestuary.helper"),
    "current_profile.json",
)


def check_for_update(skin_id):
    property_version = window.getProperty("%s.installed_version" % skin_id)
    installed_version = Addon(id=skin_id).getAddonInfo("version")
    if not property_version:
        return set_installed_version(skin_id, installed_version)
    if property_version == installed_version:
        return
    from modules.cpath_maker import remake_all_cpaths, starting_widgets
    from modules.search_utils import remake_all_spaths

    set_installed_version(skin_id, installed_version)
    sleep(1000)
    remake_all_cpaths(silent=True)
    remake_all_spaths(silent=True)
    starting_widgets()


def set_installed_version(skin_id, installed_version):
    window.setProperty("%s.installed_version" % skin_id, installed_version)


def set_current_profile(skin_id, current_profile):
    dir_path = os.path.dirname(PROFILE_PATH)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    with open(PROFILE_PATH, "w") as f:
        json.dump(current_profile, f)
    window.setProperty("%s.current_profile" % skin_id, current_profile)


def check_for_profile_change(skin_id):
    current_profile = getInfoLabel("System.ProfileName")
    saved_profile = window.getProperty("%s.current_profile" % skin_id)
    try:
        with open(PROFILE_PATH, "r") as f:
            saved_profile = json.load(f)
    except FileNotFoundError:
        saved_profile = None
    if not saved_profile:
        set_current_profile(skin_id, current_profile)
        return
    if saved_profile == current_profile:
        return
    from modules.cpath_maker import remake_all_cpaths

    set_current_profile(skin_id, current_profile)
    sleep(200)
    remake_all_cpaths(silent=True)
