# -*- coding: utf-8 -*-
import sys
from urllib.parse import parse_qsl

# from modules.logger import logger


def routing():
    params = dict(parse_qsl(sys.argv[1], keep_blank_values=True))
    _get = params.get
    mode = _get("mode", "check_for_update")
    if mode == "widget_monitor":
        from modules.widget_utils import widget_monitor

        return widget_monitor(params.get("list_id"))

    if "actions" in mode:
        from modules import actions

        return exec("actions.%s(params)" % mode.split(".")[1])

    if mode == "check_for_update":
        from modules.version_monitor import check_for_update

        return check_for_update(_get("skin_id"))

    if mode == "check_for_profile_change":
        from modules.version_monitor import check_for_profile_change

        return check_for_profile_change(_get("skin_id"))

    if mode == "manage_widgets":
        from modules.cpath_maker import CPaths

        return CPaths(_get("cpath_setting")).manage_widgets()

    if mode == "manage_main_menu_path":
        from modules.cpath_maker import CPaths

        return CPaths(_get("cpath_setting")).manage_main_menu_path()

    if mode == "starting_widgets":
        from modules.cpath_maker import starting_widgets

        return starting_widgets()

    if mode == "remake_all_cpaths":
        from modules.cpath_maker import remake_all_cpaths

        return remake_all_cpaths()

    if mode == "search_input":
        from modules.search_utils import SPaths

        return SPaths().search_input()

    if mode == "remove_all_spaths":
        from modules.search_utils import SPaths

        return SPaths().remove_all_spaths()

    if mode == "re_search":
        from modules.search_utils import SPaths

        return SPaths().re_search()

    if mode == "open_search_window":
        from modules.search_utils import SPaths

        return SPaths().open_search_window()

    if mode == "set_api_key":
        from modules.OMDb import set_api_key

        return set_api_key()
