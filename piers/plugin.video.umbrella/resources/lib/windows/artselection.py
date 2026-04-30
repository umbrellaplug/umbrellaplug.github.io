"""
	Umbrella Add-on (art selection. anybody want to make a window)
"""
from resources.lib.windows.base import BaseDialog
import json

ok_id, cancel_id, = 10, 11
button_ids = (ok_id, cancel_id)

class ArtSelect(BaseDialog):
    def __init__(self, *args, **kwargs):
        BaseDialog.__init__(self, args)
        self.window_id = 2025
        self.kwargs = kwargs
        self.mediatype = self.kwargs.get('mediatype', '')
        self.heading = self.kwargs.get('heading', '')
        self.items = json.loads(self.kwargs['items'])
        try:
            self.artworktype = self.items[0].get('artwork_type','')
        except:
            self.artworktype = ''
        self.item_list = []
        self.chosen_indexes = []
        self.selected = None
        self.set_properties()
        self.make_menu()
        
    def onInit(self):
        win = self.getControl(self.window_id)
        win.addItems(self.item_list)
        self.setFocusId(self.window_id)
        
    def run(self):
        self.doModal()
        self.clearProperties() 
        return self.selected

    def onClick(self, controlID):
        self.control_id = None
        if controlID in button_ids:
            if controlID == ok_id:
                self.selected = sorted(self.chosen_indexes)
                self.close()
            elif controlID == cancel_id:
                self.close()
        else: self.control_id = controlID

    def onAction(self, action):
        if action in self.selection_actions:
            if not self.control_id: return
            position = self.get_position(self.window_id)
            self.selected = position
            return self.close()
        elif action in self.closing_actions:
            return self.close()

    def make_menu(self):
        def builder():
            for count, item in enumerate(self.items, 1):
                listitem = self.make_listitem()
                line1 = item['source']
                if 'url' in item: line2 = item['url']
                else: line2 = ''
                if 'icon' in item: listitem.setProperty('icon', item['icon'])
                else: listitem.setProperty('icon', '')
                listitem.setProperty('line1', line1)
                listitem.setProperty('line2', line2)
                listitem.setProperty('artworktype', item['artworkType'])
                listitem.setProperty('poster', item['url'])
                yield listitem
        self.item_list = list(builder())

    def set_properties(self):
        self.setProperty('heading', self.heading)
        self.setProperty('artworktype', self.artworktype)
        