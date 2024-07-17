# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcvfs
import json
import sqlite3 as database
from threading import Thread
from modules import xmls

# from modules.logger import logger

dialog = xbmcgui.Dialog()
window = xbmcgui.Window(10000)
Listitem = xbmcgui.ListItem
max_widgets = 10

settings_path = xbmcvfs.translatePath(
    "special://profile/addon_data/script.umbrestuary.helper/"
)
database_path = xbmcvfs.translatePath(
    "special://profile/addon_data/script.umbrestuary.helper/cpath_cache.db"
)
(
    movies_widgets_xml,
    tvshows_widgets_xml,
    custom1_widgets_xml,
    custom2_widgets_xml,
    custom3_widgets_xml,
) = (
    "script-umbrestuary-widget_movies",
    "script-umbrestuary-widget_tvshows",
    "script-umbrestuary-widget_custom1",
    "script-umbrestuary-widget_custom2",
    "script-umbrestuary-widget_custom3",
)
(
    movies_main_menu_xml,
    tvshows_main_menu_xml,
    custom1_main_menu_xml,
    custom2_main_menu_xml,
    custom3_main_menu_xml,
) = (
    "script-umbrestuary-main_menu_movies",
    "script-umbrestuary-main_menu_tvshows",
    "script-umbrestuary-main_menu_custom1",
    "script-umbrestuary-main_menu_custom2",
    "script-umbrestuary-main_menu_custom3",
)
default_xmls = {
    "movie.widget": (movies_widgets_xml, xmls.default_widget, "MovieWidgets"),
    "tvshow.widget": (tvshows_widgets_xml, xmls.default_widget, "TVShowWidgets"),
    "custom1.widget": (custom1_widgets_xml, xmls.default_widget, "Custom1Widgets"),
    "custom2.widget": (custom2_widgets_xml, xmls.default_widget, "Custom2Widgets"),
    "custom3.widget": (custom3_widgets_xml, xmls.default_widget, "Custom3Widgets"),
    "movie.main_menu": (movies_main_menu_xml, xmls.default_main_menu, "MoviesMainMenu"),
    "tvshow.main_menu": (
        tvshows_main_menu_xml,
        xmls.default_main_menu,
        "TVShowsMainMenu",
    ),
    "custom1.main_menu": (
        custom1_main_menu_xml,
        xmls.default_main_menu,
        "Custom1MainMenu",
    ),
    "custom2.main_menu": (
        custom2_main_menu_xml,
        xmls.default_main_menu,
        "Custom2MainMenu",
    ),
    "custom3.main_menu": (
        custom3_main_menu_xml,
        xmls.default_main_menu,
        "Custom3MainMenu",
    ),
}
main_include_dict = {
    "movie": {"main_menu": None, "widget": "MovieWidgets"},
    "tvshow": {"main_menu": None, "widget": "TVShowWidgets"},
    "custom1": {"main_menu": None, "widget": "Custom1Widgets"},
    "custom2": {"main_menu": None, "widget": "Custom2Widgets"},
    "custom3": {"main_menu": None, "widget": "Custom3Widgets"},
}
widget_types = (
    ("Poster", "WidgetListPoster"),
    ("BigPoster", "WidgetListBigPoster"),
    ("Landscape", "WidgetListLandscape"),
    ("BigLandscape", "WidgetListBigLandscape"),
    ("LandscapeInfo", "WidgetListEpisodes"),
    ("BigLandscapeInfo", "WidgetListBigEpisodes"),
    ("Category", "WidgetListCategory"),
)
default_path = "addons://sources/video"


class CPaths:
    def __init__(self, cpath_setting):
        self.connect_database()
        self.cpath_setting = cpath_setting
        self.cpath_lookup = "'%s'" % (self.cpath_setting + "%")
        self.media_type, self.path_type = self.cpath_setting.split(".")
        self.main_include = main_include_dict[self.media_type][self.path_type]
        self.refresh_cpaths, self.last_cpath = False, None

    def connect_database(self):
        if not xbmcvfs.exists(settings_path):
            xbmcvfs.mkdir(settings_path)
        self.dbcon = database.connect(database_path, timeout=20)
        self.dbcon.execute(
            "CREATE TABLE IF NOT EXISTS custom_paths (cpath_setting text unique, cpath_path text, cpath_header text, cpath_type text, cpath_label text)"
        )
        self.dbcur = self.dbcon.cursor()

    def add_cpath_to_database(
        self, cpath_setting, cpath_path, cpath_header, cpath_type, cpath_label
    ):
        self.refresh_cpaths = True
        self.dbcur.execute(
            "INSERT OR REPLACE INTO custom_paths VALUES (?, ?, ?, ?, ?)",
            (cpath_setting, cpath_path, cpath_header, cpath_type, cpath_label),
        )
        self.dbcon.commit()

    def update_cpath_in_database(
        self, cpath_setting, cpath_path, cpath_header, cpath_type, cpath_label
    ):
        self.refresh_cpaths = True
        self.dbcur.execute(
            """
            UPDATE custom_paths
            SET cpath_path = ?, cpath_header = ?, cpath_type = ?, cpath_label = ?
            WHERE cpath_setting = ?
        """,
            (cpath_path, cpath_header, cpath_type, cpath_label, cpath_setting),
        )
        self.dbcon.commit()

    def remove_cpath_from_database(self, cpath_setting):
        self.refresh_cpaths = True
        self.dbcur.execute(
            "DELETE FROM custom_paths WHERE cpath_setting = ?", (cpath_setting,)
        )
        self.dbcon.commit()

    def fetch_current_cpaths(self):
        results = self.dbcur.execute(
            "SELECT * FROM custom_paths WHERE cpath_setting LIKE %s" % self.cpath_lookup
        ).fetchall()
        try:
            results.sort(key=lambda k: int(k[0].split(".")[-1]))
        except:
            pass
        current_dict = {}
        for item in results:
            try:
                key = int(item[0].split(".")[-1])
            except:
                key = item[0]
            data = {
                "cpath_setting": item[0],
                "cpath_path": item[1],
                "cpath_header": item[2],
                "cpath_type": item[3],
                "cpath_label": item[4],
            }
            current_dict[key] = data
        return current_dict

    def fetch_one_cpath(self, cpath_setting):
        result = self.dbcur.execute(
            "SELECT * FROM custom_paths WHERE cpath_setting = ?", (cpath_setting,)
        ).fetchone()
        if result is None:
            return None
        return {
            "cpath_setting": result[0],
            "cpath_path": result[1],
            "cpath_header": result[2],
            "cpath_type": result[3],
            "cpath_label": result[4],
        }

    def path_browser(self, label="", file=default_path, thumbnail=""):
        show_busy_dialog()
        label = self.clean_header(label)
        results = files_get_directory(file)
        hide_busy_dialog()
        list_items = []
        if file != default_path:
            listitem = Listitem(
                "Use [B]%s[/B] as path" % label, "Set as path", offscreen=True
            )
            listitem.setArt({"icon": thumbnail})
            listitem.setProperty(
                "item",
                json.dumps({"label": label, "file": file, "thumbnail": thumbnail}),
            )
            list_items.append(listitem)
        for i in results:
            listitem = Listitem("%s »" % i["label"], "Browse path...", offscreen=True)
            listitem.setArt({"icon": i["thumbnail"]})
            listitem.setProperty(
                "item",
                json.dumps(
                    {
                        "label": i["label"],
                        "file": i["file"],
                        "thumbnail": i["thumbnail"],
                    }
                ),
            )
            list_items.append(listitem)
        choice = dialog.select("Choose path", list_items, useDetails=True)
        if choice == -1:
            return {}
        choice = json.loads(list_items[choice].getProperty("item"))
        if choice["file"] == file:
            return choice
        else:
            return self.path_browser(**choice)

    def make_main_menu_xml(self, active_cpaths):
        if not self.refresh_cpaths:
            return
        if not active_cpaths:
            self.make_default_xml()
        media_types = {
            "movie": (
                movies_main_menu_xml,
                xmls.main_menu_movies_xml,
                "movie.main_menu",
            ),
            "tvshow": (
                tvshows_main_menu_xml,
                xmls.main_menu_tvshows_xml,
                "tvshow.main_menu",
            ),
            "custom1": (
                custom1_main_menu_xml,
                xmls.main_menu_custom1_xml,
                "custom1.main_menu",
            ),
            "custom2": (
                custom2_main_menu_xml,
                xmls.main_menu_custom2_xml,
                "custom2.main_menu",
            ),
            "custom3": (
                custom3_main_menu_xml,
                xmls.main_menu_custom3_xml,
                "custom3.main_menu",
            ),
        }
        media_values = media_types.get(self.media_type)
        if media_values:
            menu_xml_file, main_menu_xml, key = media_values
        xml_file = "special://skin/xml/%s.xml" % (menu_xml_file)
        final_format = main_menu_xml.format(
            main_menu_path=active_cpaths[key]["cpath_path"],
            cpath_header=active_cpaths[key].get("cpath_header", ""),
        )
        if not "&amp;" in final_format:
            final_format = final_format.replace("&", "&amp;")
        self.write_xml(xml_file, final_format)
        self.update_skin_strings()

    def make_widget_xml(self, active_cpaths):
        if not self.refresh_cpaths:
            return
        if not active_cpaths:
            self.make_default_xml()
        media_type_to_xml = {
            "movie": movies_widgets_xml,
            "tvshow": tvshows_widgets_xml,
            "custom1": custom1_widgets_xml,
            "custom2": custom2_widgets_xml,
            "custom3": custom3_widgets_xml,
        }
        xml_filename = media_type_to_xml.get(self.media_type)
        xml_file = "special://skin/xml/%s.xml" % xml_filename
        media_type_id = {
            "movie": 19010,
            "tvshow": 22010,
            "custom1": 23010,
            "custom2": 24010,
            "custom3": 25010,
        }
        list_id = media_type_id.get(self.media_type)
        final_format = xmls.media_xml_start.format(main_include=self.main_include)
        for k, v in active_cpaths.items():
            cpath_list_id = list_id + k
            cpath_path, cpath_header, cpath_type, cpath_label = (
                v["cpath_path"],
                v["cpath_header"],
                v["cpath_type"],
                v["cpath_label"],
            )
            body = (
                xmls.stacked_media_xml_body
                if "Stacked" in cpath_label
                else xmls.media_xml_body
            )
            body = body.format(
                cpath_type=cpath_type,
                cpath_path=cpath_path,
                cpath_header=cpath_header,
                cpath_list_id=cpath_list_id,
            )
            if not "&amp;" in body:
                final_format += body.replace("&", "&amp;")
        final_format += xmls.media_xml_end
        self.write_xml(xml_file, final_format)

    def write_xml(self, xml_file, final_format):
        with xbmcvfs.File(xml_file, "w") as f:
            f.write(final_format)
        Thread(target=self.reload_skin).start()

    def handle_path_browser_results(self, cpath_setting, context):
        result = self.path_browser()
        if not result:
            return None
        cpath_path = result.get("file", None)
        if not cpath_path:
            return None
        default_header = result.get("label", None)
        if context == "widget":
            cpath_header = self.widget_header(default_header)
            if not cpath_header:
                return None
            self.create_and_update_widget(cpath_setting, cpath_path, cpath_header)
        else:  # context == 'main_menu'
            cpath_header = self.main_menu_header(default_header)
            if not cpath_header:
                return None
            self.add_cpath_to_database(cpath_setting, cpath_path, cpath_header, "", "")
            self.update_skin_strings()
        return True

    def manage_action_and_check(self, cpath_setting, context):
        action_choice = self.manage_action(cpath_setting, context)
        if action_choice == "clear_path":
            self.make_default_xml()
            dialog.ok("Umbrestuary", "Path cleared")
            return None
        if action_choice is None:
            return None
        return True

    def manage_main_menu_path(self):
        active_cpaths = self.fetch_current_cpaths()
        if active_cpaths and not self.manage_action_and_check(
            self.cpath_setting, "main_menu"
        ):
            return
        if not self.handle_path_browser_results(self.cpath_setting, "main_menu"):
            return self.make_main_menu_xml(active_cpaths)
        self.make_main_menu_xml(self.fetch_current_cpaths())

    def manage_widgets(self):
        active_cpaths = self.fetch_current_cpaths()
        widget_choices = [
            "Widget %s : %s"
            % (count, active_cpaths.get(count, {}).get("cpath_label", ""))
            for count in range(1, 11)
        ]
        choice = dialog.select("Choose widget", widget_choices)
        if choice == -1:
            return self.make_widget_xml(active_cpaths)
        active_cpath_check = choice + 1
        if active_cpath_check in active_cpaths:
            cpath_setting = active_cpaths[active_cpath_check]["cpath_setting"]
            if not self.manage_action_and_check(cpath_setting, "widget"):
                return self.manage_widgets()
        else:
            cpath_setting = "%s.%s" % (self.cpath_setting, active_cpath_check)
        if not self.handle_path_browser_results(cpath_setting, "widget"):
            return self.manage_widgets()
        return self.manage_widgets()

    def widget_header(self, default_header):
        header = dialog.input("Set widget label", defaultt=default_header)
        return header or None

    def main_menu_header(self, default_header):
        header = dialog.input("Set Main Menu label", defaultt=default_header)
        return header or None

    def get_widget_type(self, cpath_type):
        for widget_type, widget_list_type in widget_types:
            if widget_list_type == cpath_type:
                return widget_type
            elif "Stacked" in cpath_type and widget_list_type in cpath_type:
                return widget_type
        return None

    def widget_type(self, label="Choose widget display type", type_limit=7):
        choice = dialog.select(label, [i[0] for i in widget_types[0:type_limit]])
        if choice == -1:
            return None
        return widget_types[choice]

    def update_skin_strings(self):
        movie_cpath = self.fetch_one_cpath("movie.main_menu")
        tvshow_cpath = self.fetch_one_cpath("tvshow.main_menu")
        custom1_cpath = self.fetch_one_cpath("custom1.main_menu")
        custom2_cpath = self.fetch_one_cpath("custom2.main_menu")
        custom3_cpath = self.fetch_one_cpath("custom3.main_menu")
        movie_cpath_header = movie_cpath.get("cpath_header") if movie_cpath else None
        tvshow_cpath_header = tvshow_cpath.get("cpath_header") if tvshow_cpath else None
        custom1_cpath_header = (
            custom1_cpath.get("cpath_header") if custom1_cpath else None
        )
        custom2_cpath_header = (
            custom2_cpath.get("cpath_header") if custom2_cpath else None
        )
        custom3_cpath_header = (
            custom3_cpath.get("cpath_header") if custom3_cpath else None
        )
        default_movie_string_id = 342
        default_tvshow_string_id = 20343
        default_custom1_string = "Custom 1"
        default_custom2_string = "Custom 2"
        default_custom3_string = "Custom 3"
        default_movie_value = (
            xbmc.getLocalizedString(default_movie_string_id)
            if not movie_cpath_header
            else movie_cpath_header
        )
        default_tvshow_value = (
            xbmc.getLocalizedString(default_tvshow_string_id)
            if not tvshow_cpath_header
            else tvshow_cpath_header
        )
        default_custom1_value = (
            default_custom1_string if not custom1_cpath_header else custom1_cpath_header
        )
        default_custom2_value = (
            default_custom2_string if not custom2_cpath_header else custom2_cpath_header
        )
        default_custom3_value = (
            default_custom3_string if not custom3_cpath_header else custom3_cpath_header
        )
        xbmc.executebuiltin("Skin.SetString(MenuMovieLabel,%s)" % default_movie_value)
        xbmc.executebuiltin("Skin.SetString(MenuTVShowLabel,%s)" % default_tvshow_value)
        xbmc.executebuiltin(
            "Skin.SetString(MenuCustom1Label,%s)" % default_custom1_value
        )
        xbmc.executebuiltin(
            "Skin.SetString(MenuCustom2Label,%s)" % default_custom2_value
        )
        xbmc.executebuiltin(
            "Skin.SetString(MenuCustom3Label,%s)" % default_custom3_value
        )

    def manage_action(self, cpath_setting, context="widget"):
        choices = [
            ("Rename", "rename_path"),
            ("Remake", "remake_path"),
            ("Remove", "clear_path"),
        ]
        if context == "widget":
            choices = [
                ("Move up", "move_up"),
                ("Move down", "move_down"),
                ("Display type", "display_type"),
            ] + choices
        choice = dialog.select(
            "%s options" % self.path_type.capitalize().replace("_", " "),
            [i[0] for i in choices],
        )
        if choice == -1:
            return None
        action = choices[choice][1]
        if action in ["move_up", "move_down"]:
            parts = cpath_setting.split(".")
            current_order = int(parts[-1])
            if len(parts) < 3 or not parts[-1].isdigit():
                dialog.ok("Umbrestuary", "Cannot move this widget")
                return None
            if current_order == 1 and action == "move_up":
                new_order = max_widgets
            elif current_order == max_widgets and action == "move_down":
                new_order = 1
            else:
                new_order = (
                    current_order - 1 if action == "move_up" else current_order + 1
                )
            self.swap_widgets(parts, current_order, new_order)
        elif action == "remake_path":
            self.remove_cpath_from_database(cpath_setting)
            result = self.path_browser()
            if result:
                cpath_path = result.get("file", None)
                if context == "widget":
                    self.handle_widget_remake(result, cpath_setting)
                elif context == "main_menu":
                    default_header = result.get("label", None)
                    cpath_header = self.main_menu_header(default_header)
                    if not cpath_header:
                        return None
                    self.add_cpath_to_database(
                        cpath_setting, cpath_path, cpath_header, "", ""
                    )
                    self.make_main_menu_xml(self.fetch_current_cpaths())
                    dialog.ok("Umbrestuary", "Main menu remade")
        elif action == "rename_path":
            result = self.fetch_one_cpath(cpath_setting)
            if not result:
                return None
            cpath_path = result.get("cpath_path", None)
            cpath_type = result.get("cpath_type", None)
            cpath_label = result.get("cpath_label", None)
            if not cpath_path:
                return None
            default_header = result.get("cpath_header", None)
            if context == "widget":
                cpath_header = self.widget_header(default_header)
                if not cpath_header:
                    return None
                widget_type = self.get_widget_type(result["cpath_type"])
                if not widget_type:
                    return None
                if "Stacked" in cpath_type:
                    cpath_label = "%s | Stacked (%s) | Category" % (
                        cpath_header,
                        widget_type,
                    )
                else:
                    cpath_label = "%s | %s" % (cpath_header, widget_type)
                self.update_cpath_in_database(
                    cpath_setting,
                    cpath_path,
                    cpath_header,
                    result["cpath_type"],
                    cpath_label,
                )
            if context == "main_menu":
                cpath_header = self.main_menu_header(default_header)
                if not cpath_header or cpath_header.strip() == "":
                    cpath_map = {
                        "movie.main_menu": xbmc.getLocalizedString(342),
                        "tvshow.main_menu": xbmc.getLocalizedString(20343),
                        "custom1.main_menu": "Custom 1",
                        "custom2.main_menu": "Custom 2",
                        "custom3.main_menu": "Custom 3",
                    }
                    cpath_header = cpath_map.get(
                        cpath_setting, "Default main menu label not found"
                    )
                self.update_cpath_in_database(
                    cpath_setting, cpath_path, cpath_header, "", ""
                )
                self.make_main_menu_xml(self.fetch_current_cpaths())
        elif action == "display_type":
            result = self.fetch_one_cpath(cpath_setting)
            if not result:
                return None
            cpath_path = result.get("cpath_path", None)
            cpath_header = result.get("cpath_header", None)
            cpath_label = result.get("cpath_label", None)
            if not cpath_path:
                return None
            self.create_and_update_widget(
                cpath_setting, cpath_path, cpath_header, add_to_db=False
            )
        elif action == "clear_path":
            self.remove_cpath_from_database(cpath_setting)
            if context == "main_menu":
                self.make_default_xml()
                dialog.ok("Umbrestuary", "Path cleared")
        return None

    def swap_widgets(self, parts, current_order, new_order):
        current_widget = f"{parts[0]}.{parts[1]}.{current_order}"
        adjacent_widget = f"{parts[0]}.{parts[1]}.{new_order}"
        self.refresh_cpaths = True
        self.dbcur.execute(
            "UPDATE custom_paths SET cpath_setting = ? WHERE cpath_setting = ?",
            (f"{parts[0]}.{parts[1]}.temp", current_widget),
        )
        self.dbcur.execute(
            "UPDATE custom_paths SET cpath_setting = ? WHERE cpath_setting = ?",
            (current_widget, adjacent_widget),
        )
        self.dbcur.execute(
            "UPDATE custom_paths SET cpath_setting = ? WHERE cpath_setting = ?",
            (adjacent_widget, f"{parts[0]}.{parts[1]}.temp"),
        )
        self.dbcon.commit()

    def handle_widget_remake(self, result, cpath_setting):
        cpath_path, default_header = result.get("file", None), result.get("label", None)
        cpath_header = self.widget_header(default_header)
        self.create_and_update_widget(cpath_setting, cpath_path, cpath_header)

    def create_and_update_widget(
        self, cpath_setting, cpath_path, cpath_header, add_to_db=True
    ):
        widget_type = self.widget_type()
        if widget_type[0] == "Category" and dialog.yesno(
            "Stacked widget",
            "Make [COLOR accent_color][B]%s[/B][/COLOR] a stacked widget?"
            % cpath_header,
        ):
            widget_type = self.widget_type(label="Choose stacked widget display type")
            cpath_type, cpath_label = "%sStacked" % widget_type[
                1
            ], "%s | Stacked (%s) | Category" % (cpath_header, widget_type[0])
        else:
            cpath_type, cpath_label = widget_type[1], "%s | %s" % (
                cpath_header,
                widget_type[0],
            )
        if add_to_db:
            self.add_cpath_to_database(
                cpath_setting, cpath_path, cpath_header, cpath_type, cpath_label
            )
        else:
            self.update_cpath_in_database(
                cpath_setting, cpath_path, cpath_header, cpath_type, cpath_label
            )

    def reload_skin(self):
        if window.getProperty("umbrestuary.clear_path_refresh") == "true":
            return
        window.setProperty("umbrestuary.clear_path_refresh", "true")
        while xbmcgui.getCurrentWindowId() == 10035:
            xbmc.sleep(500)
        window.setProperty("umbrestuary.clear_path_refresh", "")
        xbmc.sleep(200)
        xbmc.executebuiltin("ReloadSkin()")
        starting_widgets()

    def clean_header(self, header):
        return header.replace("[B]", "").replace("[/B]", "").replace(" >>", "")

    def remake_main_menus(self):
        self.refresh_cpaths = True
        active_cpaths = self.fetch_current_cpaths()
        if active_cpaths:
            self.make_main_menu_xml(active_cpaths)
        else:
            self.make_default_xml()

    def remake_widgets(self):
        self.refresh_cpaths = True
        active_cpaths = self.fetch_current_cpaths()
        if active_cpaths:
            self.make_widget_xml(active_cpaths)
        else:
            self.make_default_xml()

    def make_default_xml(self):
        item = default_xmls[self.cpath_setting]
        final_format = item[1].format(includes_type=item[2])
        xml_file = "special://skin/xml/%s.xml" % item[0]
        with xbmcvfs.File(xml_file, "w") as f:
            f.write(final_format)
        self.update_skin_strings()
        Thread(target=self.reload_skin).start()


def files_get_directory(directory, properties=["title", "file", "thumbnail"]):
    command = {
        "jsonrpc": "2.0",
        "id": "plugin.video.umbrella",
        "method": "Files.GetDirectory",
        "params": {"directory": directory, "media": "files", "properties": properties},
    }
    try:
        results = [
            i
            for i in get_jsonrpc(command).get("files")
            if i["file"].startswith("plugin://") and i["filetype"] == "directory"
        ]
    except:
        results = None
    return results


def get_jsonrpc(request):
    response = xbmc.executeJSONRPC(json.dumps(request))
    result = json.loads(response)
    return result.get("result", None)


def remake_all_cpaths(silent=False):
    for item in (
        "movie.widget",
        "tvshow.widget",
        "custom1.widget",
        "custom2.widget",
        "custom3.widget",
    ):
        CPaths(item).remake_widgets()
    for item in (
        "movie.main_menu",
        "tvshow.main_menu",
        "custom1.main_menu",
        "custom2.main_menu",
        "custom3.main_menu",
    ):
        CPaths(item).remake_main_menus()
    if not silent:
        xbmcgui.Dialog().ok("Umbrestuary", "Menus and widgets remade")


def starting_widgets():
    window = xbmcgui.Window(10000)
    window.setProperty("umbrestuary.starting_widgets", "finished")
    for item in (
        "movie.widget",
        "tvshow.widget",
        "custom1.widget",
        "custom2.widget",
        "custom3.widget",
    ):
        try:
            active_cpaths = CPaths(item).fetch_current_cpaths()
            if not active_cpaths:
                continue
            widget_type = item.split(".")[0]
            widget_type_id = {
                "movie": 19010,
                "tvshow": 22010,
                "custom1": 23010,
                "custom2": 24010,
                "custom3": 25010,
            }
            base_list_id = widget_type_id.get(widget_type)
            for count in range(1, 11):
                active_widget = active_cpaths.get(count, {})
                if not active_widget:
                    continue
                if not "Stacked" in active_widget["cpath_label"]:
                    continue
                cpath_setting = active_widget["cpath_setting"]
                if not cpath_setting:
                    continue
                try:
                    list_id = base_list_id + int(cpath_setting.split(".")[2])
                except:
                    continue
                try:
                    first_item = files_get_directory(active_widget["cpath_path"])[0]
                except:
                    continue
                if not first_item:
                    continue
                cpath_label, cpath_path = first_item["label"], first_item["file"]
                window.setProperty("umbrestuary.%s.label" % list_id, cpath_label)
                window.setProperty("umbrestuary.%s.path" % list_id, cpath_path)
        except:
            pass
    try:
        del window
    except:
        pass


def show_busy_dialog():
    return xbmc.executebuiltin("ActivateWindow(busydialognocancel)")


def hide_busy_dialog():
    xbmc.executebuiltin("Dialog.Close(busydialognocancel)")
    xbmc.executebuiltin("Dialog.Close(busydialog)")
