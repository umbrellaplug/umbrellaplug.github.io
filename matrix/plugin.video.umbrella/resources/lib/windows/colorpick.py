# -*- coding: utf-8 -*-
from resources.lib.windows.base import BaseDialog
from resources.lib.modules import colors
from resources.lib.modules.control import dialog, setting as getSetting, darkColor

button_ids = (10, 11)
palettes = {'rainbow': colors.rainbow}
palette_list = ['rainbow']
colorpalette_path = 'color_palette2/'

class ColorPick(BaseDialog):
    def __init__(self, *args, **kwargs):
        BaseDialog.__init__(self, *args)
        self.kwargs = kwargs
        self.current_setting = self.kwargs.get('current_setting')
        self.current_value = self.kwargs.get('current_value')
        self.window_id = 2000
        self.selected = None
        self.texture_location = colorpalette_path + '%s.png'
        self.current_palette = palette_list[0]
        self.make_menu()
        self.lightordark = getSetting('dialogs.lightordarkmode')
        self.buttonColor = getSetting('dialogs.button.color')
        self.customBackgroundColor = getSetting('dialogs.customcolor')
        self.dark_text_background = darkColor(self.customBackgroundColor)
        self.useCustomTitleColor = getSetting('dialogs.usecolortitle') == 'true'
        self.customTitleColor = getSetting('dialogs.titlebar.color')
        self.set_properties()

    def onInit(self):
        win = self.getControl(self.window_id)
        win.addItems(self.item_list)
        self.setFocusId(self.window_id)
        self.getControl(self.window_id).selectItem(0)

    def run(self):
        self.doModal()
        self.clearProperties()
        return self.selected

    def onAction(self, action):
        if action in self.closing_actions: self.setFocusId(11)
        elif action in self.selection_actions:
            focus_id = self.getFocusId()
            if focus_id == 2000:
                chosen_listitem = self.item_list[self.get_position(self.window_id)]
                self.current_setting = chosen_listitem.getProperty('label')
                self.selected = self.current_setting
                self.setFocusId(10)
            elif focus_id == 10: self.close()
            elif focus_id == 11:
                self.selected = None
                self.close()
            elif focus_id == 12:
                color_value = dialog.input('Enter Color Value', defaultt=self.current_value)
                if not color_value: return
                if len(color_value) == 6:
                    color_value = "FF"+color_value
                self.current_setting = color_value
                self.selected = self.current_setting
                self.close()
            else: self.palette_switcher()

    def make_menu(self):
        def builder():
            for count, item in enumerate(palettes[self.current_palette]):
                try:
                    listitem = self.make_listitem()
                    listitem.setProperty('label', item)
                    listitem.setProperty('image', self.texture_location % item)
                    yield listitem
                except: pass
        current_palette = palettes[self.current_palette]
        self.item_list = list(builder())

    def set_properties(self):
        self.setProperty('umbrella.buttonColor', self.buttonColor)
        if self.useCustomTitleColor:
            #need to use a custom titlebar color
            self.setProperty('umbrella.titleBarColor', self.customTitleColor)
            if darkColor(self.customTitleColor) == 'dark':
                self.setProperty('umbrella.titleTextColor', 'FFF5F5F5')
            else:
                self.setProperty('umbrella.titleTextColor', 'FF302F2F')
        if darkColor(self.buttonColor) == 'dark':
            self.setProperty('umbrella.buttonTextColor', 'FFF5F5F5')
        else:
            self.setProperty('umbrella.buttonTextColor', 'FF302F2F')
        if self.lightordark == '0':
            self.setProperty('umbrella.backgroundColor', 'FF302F2F') #setting dark grey for dark mode
            self.setProperty('umbrella.textColor', 'FFF5F5F5')
            self.setProperty('umbrella.buttonnofocus', '33F5F5F5')
            if not self.useCustomTitleColor:
                self.setProperty('umbrella.titleBarColor', 'FF302F2F')
                self.setProperty('umbrella.titleTextColor', 'FFF5F5F5')
            self.setProperty('umbrella.buttonTextColorNS', 'FFF5F5F5')
        elif self.lightordark == '1':
            self.setProperty('umbrella.backgroundColor', 'FFF5F5F5') #setting dirty white for light mode. (the hell you call me)
            self.setProperty('umbrella.textColor', 'FF302F2F')
            self.setProperty('umbrella.buttonnofocus', '33302F2F')
            if not self.useCustomTitleColor:
                self.setProperty('umbrella.titleBarColor', 'FFF5F5F5')
                self.setProperty('umbrella.titleTextColor', 'FF302F2F')
            self.setProperty('umbrella.buttonTextColorNS', 'FF302F2F')
        elif self.lightordark == '2':
            #ohh now we need a custom color, aren't we just special.
            self.setProperty('umbrella.backgroundColor', self.customBackgroundColor) #setting custom color because screw your light or dark mode.
            if self.dark_text_background == 'dark':
                self.setProperty('umbrella.textColor', 'FFF5F5F5')
                self.setProperty('umbrella.buttonTextColorNS', 'FFF5F5F5')
                self.setProperty('umbrella.buttonnofocus', 'FFF5F5F5')
                if not self.useCustomTitleColor:
                    self.setProperty('umbrella.titleTextColor', 'FFF5F5F5')
                    self.setProperty('umbrella.titleBarColor', self.customBackgroundColor) #setting titletext and background color if not using a custom value
            else:
                self.setProperty('umbrella.textColor', 'FF302F2F')
                self.setProperty('umbrella.buttonTextColorNS', 'FF302F2F')
                self.setProperty('umbrella.buttonnofocus', '33302F2F')
                if not self.useCustomTitleColor:
                    self.setProperty('umbrella.titleTextColor', 'FF302F2F')
                    self.setProperty('umbrella.titleBarColor', self.customBackgroundColor)#setting titletext and background color if not using a custom value
        self.setProperty('current_palette', self.current_palette)
        self.setProperty('current_palette_name', self.current_palette.capitalize())

    def palette_switcher(self):
        try: self.current_palette = palette_list[palette_list.index(self.current_palette) + 1]
        except: self.current_palette = palette_list[0]
        self.reset_window(self.window_id)
        self.set_properties()
        self.make_menu()
        self.add_items(self.window_id, self.item_list)
