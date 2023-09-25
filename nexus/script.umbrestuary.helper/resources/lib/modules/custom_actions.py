import xbmc
import xbmcgui


def set_image():
    image_file = xbmcgui.Dialog().browse(
        2, "Choose Custom Background Image", "network", ".jpg|.png|.bmp", False, False
    )
    if image_file:
        xbmc.executebuiltin("Skin.SetString(CustomBackground,%s)" % image_file)