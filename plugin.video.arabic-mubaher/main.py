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
import settings as kodi_settings
file=None
def add_category():
   
    list_Categories = get_category.categories
    # Create the Kodi window
    window = xbmcgui.Window(10000)
    # Clear the existing items in the window
    addon = xbmcaddon.Addon()
    xbmcplugin.setContent(int(sys.argv[1]), "videos")
    Categories = list_Categories._categories()
 
    # Categories = (data['categories'])
    for count, Category in enumerate(Categories):
        list_Category = xbmcgui.ListItem(label=Category["name"])
        list_Category.setArt({'fanart': Category["img"]})
        list_Category.setArt({'thumb': Category["img"]})
        list_Category.setProperty("IsFolder", "true")
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sys.argv[0] + "?category=" + str(count), listitem=list_Category, isFolder=True)

    # End the window
    xbmcplugin.endOfDirectory(int(sys.argv[1]))
 
def main():
    kodi_settings_instance = kodi_settings.KodiSettings()
    if "autoplay" in     kodi_settings_instance.all():
        pass
    else:

     kodi_settings_instance.set("autoplay", True)


    show_TVchannels = tvchannels.TV
    show_Radiochannels = radio_channel.radio
 
  
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
        pass
        # If no category was selected, add the categories to the Kodi window
    else:
        Category_index = int(args["category"])
        if Category_index == 0:
            # show_TVchannels.load_settings()
            show_TVchannels.check_folder()
            show_TVchannels.browse_folder()
            # folder = show_TVchannels.check_folder()
            pass
        
        elif Category_index == 1:
            show_Radiochannels.channel()
            pass


if __name__ == "__main__":
    main()