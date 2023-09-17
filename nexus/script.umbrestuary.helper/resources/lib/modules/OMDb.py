import xbmc, xbmcvfs
import datetime as dt
import xml.etree.ElementTree as ET
import sqlite3 as database
import time
import requests
import json

# logger = xbmc.log

settings_path = xbmcvfs.translatePath(
    "special://profile/addon_data/script.umbrestuary.helper/"
)
ratings_database_path = xbmcvfs.translatePath(
    "special://profile/addon_data/script.umbrestuary.helper/ratings_cache.db"
)
IMAGE_PATH = "special://home/addons/skin.umbrestuary/resources/rating_images/"


def make_session(url="https://"):
    session = requests.Session()
    session.mount(url, requests.adapters.HTTPAdapter(pool_maxsize=100))
    return session


api_url = "http://www.omdbapi.com/?apikey=%s&i=%s&tomatoes=True&r=xml"
session = make_session("http://www.omdbapi.com/")


class OMDbAPI:
    last_checked_imdb_id = None

    def __init__(self):
        self.connect_database()

    def connect_database(self):
        if not xbmcvfs.exists(settings_path):
            xbmcvfs.mkdir(settings_path)
        self.dbcon = database.connect(ratings_database_path, timeout=60)
        self.dbcon.execute(
            """
        CREATE TABLE IF NOT EXISTS ratings (
            imdb_id TEXT PRIMARY KEY,
            ratings TEXT,
            last_updated TIMESTAMP
        );
        """
        )
        self.dbcur = self.dbcon.cursor()

    def datetime_workaround(self, data, str_format):
        try:
            datetime_object = dt.datetime.strptime(data, str_format)
        except:
            datetime_object = dt.datetime(*(time.strptime(data, str_format)[0:6]))
        return datetime_object

    def insert_or_update_ratings(self, imdb_id, ratings):
        ratings_data = json.dumps(ratings)
        self.dbcur.execute(
            """
            INSERT OR REPLACE INTO ratings (imdb_id, ratings, last_updated)
            VALUES (?, ?, ?)
            """,
            (imdb_id, ratings_data, dt.datetime.now()),
        )
        self.dbcon.commit()

    def get_cached_ratings(self, imdb_id):
        self.dbcur.execute(
            "SELECT imdb_id, ratings, last_updated FROM ratings WHERE imdb_id=?",
            (imdb_id,),
        )
        entry = self.dbcur.fetchone()
        if entry:
            _, ratings_data, last_updated = entry
            ratings = json.loads(ratings_data)
            last_updated_date = self.datetime_workaround(
                last_updated, "%Y-%m-%d %H:%M:%S.%f"
            )
            if dt.datetime.now() - last_updated_date < dt.timedelta(days=7):
                return ratings
        return None

    def fetch_info(self, meta, api_key, tmdb_rating):
        imdb_id = meta.get("imdb_id")
        if not imdb_id or not api_key:
            return {}
        cached_ratings = self.get_cached_ratings(imdb_id)
        if cached_ratings:
            return cached_ratings
        data = self.get_result(imdb_id, api_key, tmdb_rating)
        self.insert_or_update_ratings(imdb_id, data)
        return data

    def get_result(self, imdb_id, api_key, tmdb_rating):
        if not api_key:
            return {}
        url = api_url % (api_key, imdb_id)
        response = session.get(url)
        if response.status_code != 200:
            return {}
        root = ET.fromstring(response.content)
        data = root.find("movie")
        if data is None:
            return {}

        def get_rating_value(key, append_percent=False):
            val = data.get(key, "").strip()
            if val and val != "N/A" and (val.isdigit() or "." in val):
                return val + ("%" if append_percent else "")
            return ""

        tomatometer_rating = get_rating_value("tomatoMeter", True)
        tomatousermeter_rating = get_rating_value("tomatoUserMeter", True)
        tomato_image = data.get("tomatoImage")
        if tomato_image:
            tomatometer_icon = IMAGE_PATH + (
                "rtcertified.png"
                if tomato_image == "certified"
                else "rtfresh.png"
                if tomato_image == "fresh"
                else "rtrotten.png"
            )
        elif (
            tomatometer_rating and int(float(tomatometer_rating.replace("%", ""))) > 59
        ):
            tomatometer_icon = IMAGE_PATH + "rtfresh.png"
        else:
            tomatometer_icon = IMAGE_PATH + "rtrotten.png"
        if (
            tomatousermeter_rating
            and int(float(tomatousermeter_rating.replace("%", ""))) > 59
        ):
            tomatousermeter_icon = IMAGE_PATH + "popcorn.png"
        else:
            tomatousermeter_icon = IMAGE_PATH + "popcorn_spilt.png"
        data = {
            "metascore": get_rating_value("metascore", True),
            "metascoreImage": IMAGE_PATH + "metacritic.png",
            "tomatoMeter": tomatometer_rating,
            "tomatoUserMeter": tomatousermeter_rating,
            "tomatoImage": tomatometer_icon,
            "tomatoUserImage": tomatousermeter_icon,
            "imdbRating": get_rating_value("imdbRating"),
            "imdbImage": IMAGE_PATH + "imdb.png",
            "tmdbRating": tmdb_rating if tmdb_rating != "N/A" else "",
            "tmdbImage": IMAGE_PATH + "tmdb.png",
        }
        return data


def set_api_key():
    keyboard = xbmc.Keyboard("", "Enter OMDb API Key")
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():
        xbmc.executebuiltin(f"Skin.SetString(omdb_api_key,{keyboard.getText()})")
