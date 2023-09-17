import xbmc, xbmcgui
from threading import Thread
from modules.OMDb import OMDbAPI
import json

logger = xbmc.log
empty_ratings = {
    "metascore": "",
    "tomatoMeter": "",
    "tomatoUserMeter": "",
    "tomatoImage": "",
    "imdbRating": "",
    "tmdbRating": "",
}


class RatingsService(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.omdb_api = OMDbAPI
        self.window = xbmcgui.Window
        self.get_window_id = xbmcgui.getCurrentWindowId
        self.get_infolabel = xbmc.getInfoLabel
        self.get_visibility = xbmc.getCondVisibility

    def onNotification(self, sender, method, data):
        if sender == "xbmc":
            if method in ("GUI.OnScreensaverActivated", "System.OnSleep"):
                self.window(self.get_window_id()).setProperty("pause_services", "true")
                logger("###Umbrestuary: Device is Asleep, PAUSING Ratings Service", 1)
            elif method in ("GUI.OnScreensaverDeactivated", "System.OnWake"):
                self.window(self.get_window_id()).clearProperty("pause_services")
                logger("###Umbrestuary: Device is Awake, RESUMING Ratings Service", 1)

    def listitem_monitor(self):
        while not self.abortRequested():
            if (
                self.window(self.get_window_id()).getProperty("pause_services")
                == "true"
            ):
                self.waitForAbort(2)
                continue
            if xbmc.getSkinDir() != "skin.umbrestuary":
                self.waitForAbort(15)
                continue
            api_key = self.get_infolabel("Skin.String(omdb_api_key)")
            if not api_key:
                self.waitForAbort(10)
                continue
            if not self.get_visibility(
                "Window.IsVisible(videos) | Window.IsVisible(home) | Window.IsVisible(11121)"
            ):
                self.waitForAbort(2)
                continue
            if self.get_visibility("Container.Scrolling"):
                self.waitForAbort(0.2)
                continue
            imdb_id = self.get_infolabel("ListItem.IMDBNumber")
            tmdb_rating = self.get_infolabel("ListItem.Rating")
            set_property = self.window(self.get_window_id()).setProperty
            get_property = self.window(self.get_window_id()).getProperty
            cached_ratings = get_property(f"umbrestuary.cachedRatings.{imdb_id}")
            if not imdb_id or not imdb_id.startswith("tt"):
                for k, v in empty_ratings.items():
                    set_property("umbrestuary.%s" % k, v)
                self.waitForAbort(0.2)
                continue
            if cached_ratings:
                result = json.loads(cached_ratings)
                for k, v in result.items():
                    set_property("umbrestuary.%s" % k, v)
                self.waitForAbort(0.2)
                continue
            Thread(
                target=self.set_ratings, args=(api_key, imdb_id, tmdb_rating)
            ).start()
            self.waitForAbort(0.2)

    def set_ratings(self, api_key, imdb_id, tmdb_rating):
        set_property = self.window(self.get_window_id()).setProperty
        result = self.omdb_api().fetch_info({"imdb_id": imdb_id}, api_key, tmdb_rating)
        if result:
            set_property(f"umbrestuary.cachedRatings.{imdb_id}", json.dumps(result))
            for k, v in result.items():
                set_property("umbrestuary.%s" % k, v)


logger("###Umbrestuary: Ratings Service Started", 1)
RatingsService().listitem_monitor()
logger("###Umbrestuary: RatingsService Finished", 1)
