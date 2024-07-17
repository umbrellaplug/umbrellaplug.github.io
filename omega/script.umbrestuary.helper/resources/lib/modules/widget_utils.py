# -*- coding: utf-8 -*-
import xbmc, xbmcgui

# from modules.logger import logger


def widget_monitor(list_id):
    if len(list_id) != 5:
        return
    monitor = xbmc.Monitor()
    window = None
    try:
        delay = float(xbmc.getInfoLabel("Skin.String(category_widget_delay)")) / 1000
    except:
        delay = 0.75
    display_delay = (
        xbmc.getInfoLabel("Skin.HasSetting(category_widget_display_delay)") == "True"
    )
    stack_id = list_id + "1"
    poster_toggle, landscape_toggle = True, False
    while not monitor.abortRequested():
        window_id = xbmcgui.getCurrentWindowId()
        if window_id not in [10000, 11121]:
            break
        else:
            window = xbmcgui.Window(window_id)
            stack_control = window.getControl(int(stack_id))
            stack_label_control = (
                window.getControl(int(stack_id + "666"))
                or window.getControl(int(stack_id + "667"))
                or window.getControl(int(stack_id + "668"))
                or window.getControl(int(stack_id + "669"))
            )
        monitor.waitForAbort(0.25)
        if list_id != str(window.getFocusId()):
            break
        last_path = window.getProperty("umbrestuary.%s.path" % list_id)
        cpath_path = xbmc.getInfoLabel("ListItem.FolderPath")
        if last_path == cpath_path or xbmc.getCondVisibility(
            "System.HasActiveModalDialog"
        ):
            continue
        switch_widget = True
        countdown = delay
        while not monitor.abortRequested() and countdown >= 0 and switch_widget:
            monitor.waitForAbort(0.25)
            countdown -= 0.25
            if list_id != str(window.getFocusId()):
                switch_widget = False
            if last_path == cpath_path:
                switch_widget = False
            if xbmc.getInfoLabel("ListItem.FolderPath") != cpath_path:
                switch_widget = False
            if xbmc.getCondVisibility("System.HasActiveModalDialog"):
                switch_widget = False
            if xbmcgui.getCurrentWindowId() not in [10000, 11121]:
                switch_widget = False
            widget_label = xbmc.getInfoLabel("ListItem.Label")
            if display_delay:
                stack_label_control.setLabel(
                    "Loading [COLOR accent_color][B]{}[/B][/COLOR] in [B]%0.2f[/B] seconds".format(
                        widget_label
                    )
                    % (countdown)
                )
        if switch_widget:
            position = int(xbmc.getInfoLabel("Container(%s).Position" % list_id))
            cpath_label = xbmc.getInfoLabel("ListItem.Label")
            stack_label_control.setLabel(cpath_label)
            window.setProperty("umbrestuary.%s.label" % list_id, cpath_label)
            window.setProperty("umbrestuary.%s.path" % list_id, cpath_path)
            monitor.waitForAbort(0.2)
            update_wait_time = 0
            while (
                xbmc.getCondVisibility("Container(%s).IsUpdating" % stack_id)
                and not update_wait_time > 3
            ):
                monitor.waitForAbort(0.10)
                update_wait_time += 0.10
            monitor.waitForAbort(0.50)
            try:
                stack_control.selectItem(0)
            except:
                pass
        else:
            stack_label_control.setLabel(
                window.getProperty("umbrestuary.%s.label" % list_id)
            )
            monitor.waitForAbort(0.25)
    try:
        del monitor
    except:
        pass
    try:
        del window
    except:
        pass
