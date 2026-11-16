import xbmcgui
import xbmcplugin
import sys
import urllib.parse
import json
import xbmc
import xbmcaddon
import get_category
import os
import xbmcvfs
import channels_tv as tvchannels
import channels_radio as radio_channel
import bookmark
from  resources.lib.settings import KodiSettings
settings_instance = KodiSettings()
def add_category():
    list_Categories = get_category.categories
    xbmcplugin.setContent(int(sys.argv[1]), "videos")
    Categories = list_Categories._categories()

    for count, Category in enumerate(Categories):
        list_Category = xbmcgui.ListItem(label=Category["name"])
        list_Category.setArt({'fanart': Category["img"]})
        list_Category.setArt({'thumb': Category["img"]})
        list_Category.setProperty("IsFolder", "true")
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sys.argv[0] + "?category=" + str(count), listitem=list_Category, isFolder=True)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))
 
def main():
    favorite = bookmark.bookmark()
    show_TVchannels = tvchannels.TV()
    show_Radiochannels = radio_channel.radio()

    # Parse the command-line arguments
    args = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))

    # Check if this is an action request (context menu actions)
    if "action" in args:
        action = args.get("action")
        file_path = args.get("file")
        tvchannels.handle_action(action, file_path)
        return  # Exit after handling action

    # Check if browsing a subfolder within TV category
    if "category" in args and args["category"] == "0" and "path" in args:
        path = urllib.parse.unquote(args["path"])
        show_TVchannels.browse_folder(path)
        return

    # Main category selection
    if "category" not in args:
        add_category()
    else:
        Category_index = int(args["category"])
        if Category_index == 0:
            show_TVchannels.check_folder()
            show_TVchannels.chk_browse_data()
        elif Category_index == 1:
            show_Radiochannels.channel()
        elif Category_index == 2:
            favorite.show_favorites()

if __name__ == "__main__":
    main()