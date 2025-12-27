# channels_tv.py
import os
import sys
import xbmcgui
import xbmcplugin
import xbmc
import xbmcaddon
import urllib.parse
import json
import xbmcvfs
from  resources.lib.settings import KodiSettings
import threading
import time
settings = KodiSettings()
_media_library = KodiSettings(filename="media_library.json")


HANDLE = int(sys.argv[1])
playboll=False

class TV:
    VIDEO_EXT = ['.mp4', '.mkv', '.avi', '.m3u8', '.strm']
    AUDIO_EXT = ['.mp3', '.flac']

    addon = xbmcaddon.Addon()  # get current addon
    MEDIA_FOLDER = addon.getSetting("media_folder")  # read from addon settings

    @staticmethod
    def notify(title, msg, time=5000):
        xbmc.executebuiltin(f"Notification('{title}','{msg}',{time})")

    @classmethod
    def save_settings(cls):
        cls.addon.setSetting("media_folder", cls.MEDIA_FOLDER)

    @classmethod
    def check_folder(cls, path=None):
        
     

        folder = path if path else cls.MEDIA_FOLDER

        if not folder or not os.path.exists(folder) or not os.path.isdir(folder):
            cls.notify("TV Addon", f"Folder not found:\n{folder}\nPlease select a new folder...")

            new_folder = xbmcgui.Dialog().browse(
                type=3,  # Folder
                heading="Select Media Folder",
                shares='files',
                useThumbs=False
            )

            if new_folder and os.path.exists(new_folder):
                cls.MEDIA_FOLDER = new_folder
                cls.save_settings()
                folder = new_folder
                cls.notify("TV Addon", f"New folder saved:\n{folder}")
            else:
                cls.notify("TV Addon", "No valid folder selected! no data loaded")
            

        return folder
    @classmethod
    def chk_browse_data(cls, path=None):
        if os.listdir( cls.MEDIA_FOLDER):
         cls.browse_folder()
        elif  not os.listdir( cls.MEDIA_FOLDER):
         #   cls.notify("TV Addon", "The selected folder is empty!")
            container_Dtatabase ()
        else:
            cls.notify("TV Addon", "No valid folder selected! nodata loaded")
    @  classmethod
    def get_media_nosql(cls):
        data=_media_library.get("media", {})
        return data
    @classmethod
    def browse_folder(cls, path=None):
        data=settings.get("play", {})
        for key in list(data.keys()):
           
               data[ key] = True
        settings.set("play", data)
      
        folder = path if path else cls.MEDIA_FOLDER

        if not folder:
            cls.notify("TV Addon", "Media folder not set!")
            return
      
        try:
            media_list=os.listdir(folder)
            for media in os.listdir(folder):
                media_path = os.path.join(folder, media)
                list_item = xbmcgui.ListItem(label=media)

                if os.path.isdir(media_path):
                    # URL-encode the path for Kodi
                    url = sys.argv[0] + "?category=0&path=" + urllib.parse.quote(media_path)
                    xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=True)
                else:
                    ext = os.path.splitext(media)[1].lower()
                    if ext in cls.VIDEO_EXT:
                        url, list_item = container_file (media_path)

                        '''''
                        list_item.setInfo("video", {"title": media})
                        list_item.setProperty("IsPlayable", "true")
                        context_menu = [
                            ("File Info", f"RunPlugin({sys.argv[0]}?action=info&file={urllib.parse.quote(media_path)})"),
                            ("Delete File", f"RunPlugin({sys.argv[0]}?action=delete&file={urllib.parse.quote(media_path)})"),
                            ("Add Bookmark", f"RunPlugin({sys.argv[0]}?action=bookmark&file={urllib.parse.quote(media_path)})"),
                            ("Add Data", f"RunPlugin({sys.argv[0]}?action=adddata&file={urllib.parse.quote(media_path)})")
                        ]
                        
                        list_item.addContextMenuItems(context_menu)
                        list_item.setProperty('ForceResolvePlugin', 'true')'''

                    elif ext in cls.AUDIO_EXT:
                        list_item.setInfo("music", {"title": media})
                        list_item.setProperty("IsPlayable", "true")
                        '''  
                    # Direct path to file
               url = media_path
                    xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=False)'''
                    xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=True)
                  
            xbmcplugin.endOfDirectory(HANDLE)
        except Exception as e:
            cls.notify("TV Addon", f"Error browsing folder: {e}")


# Action handlers
def show_info(file_path):
    if not file_path or not os.path.exists(file_path):
        xbmcgui.Dialog().notification("Info", "File not found!")
        return
    
    file_size = os.path.getsize(file_path)
    file_size_mb = file_size / (1024 * 1024)
    file_name = os.path.basename(file_path)
    
    info_text = f"File: {file_name}\nSize: {file_size_mb:.2f} MB\nPath: {file_path}"
    xbmcgui.Dialog().ok("File Info", info_text)


def delete_file(file_path):
    if not file_path or not os.path.exists(file_path):
        xbmcgui.Dialog().notification("Delete", "File not found!")
        return
    
    # Confirm deletion
    confirm = xbmcgui.Dialog().yesno(
        "Delete File",
        f"Are you sure you want to delete:\n{os.path.basename(file_path)}?"
    )
    
    if confirm:
        try:
            os.remove(file_path)
            xbmcgui.Dialog().notification("Delete", "File deleted successfully!")
            xbmc.executebuiltin("Container.Refresh")  # Refresh the list
        except Exception as e:
            xbmcgui.Dialog().notification("Delete", f"Error: {str(e)}")
    else:
        xbmcgui.Dialog().notification("Delete", "Deletion cancelled")


def add_bookmark(file_path):
    if not file_path:
        xbmcgui.Dialog().notification("Bookmark", "Invalid file path!")
        return
    
    # Get bookmark name from user
    keyboard = xbmc.Keyboard('', 'Enter bookmark name')
    keyboard.doModal()
    
    if keyboard.isConfirmed():
        bookmark_name = keyboard.getText()
        if bookmark_name:
            # Here you would save the bookmark (to a file or addon settings)
            xbmcgui.Dialog().notification("Bookmark", f"Bookmarked as: {bookmark_name}")
        else:
            xbmcgui.Dialog().notification("Bookmark", "Bookmark name cannot be empty!")
    else:
        xbmcgui.Dialog().notification("Bookmark", "Bookmark cancelled")


def add_data(file_path):
    if not file_path:
        xbmcgui.Dialog().notification("Add Data", "Invalid file path!")
        return
   # co=xbmcgui.
    # Get data from user
    keyboard = xbmc.Keyboard('', 'Enter data/notes')
    keyboard.doModal()
    
    if keyboard.isConfirmed():
        data = keyboard.getText()
        if data:
            # Here you would save the data (to a file or addon settings)
            xbmcgui.Dialog().notification("Add Data", "Data saved successfully!")
        else:
            xbmcgui.Dialog().notification("Add Data", "No data entered!")
    else:
        xbmcgui.Dialog().notification("Add Data", "Operation cancelled")
def  container_Dtatabase ():
    data=_media_library.get("media", {})
    for key in list(data.keys()):
        block=data[key]
        path=block.get("path", None)    
        file_name=block.get("file", None)
        icon=block.get("icon", None)
        thumb=block.get("thumb", None)
        info=block.get("info", None)
        ext=block.get("extension", None)
        item_items=xbmcgui.ListItem(label=file_name)
        item_items.setArt({
        'icon': icon if icon else 'https://www.shutterstock.com/shutterstock/videos/3400579563/thumb/11.jpg?ip=x480',
        'thumb': thumb if thumb else 'https://is3-ssl.mzstatic.com/image/thumb/Purple124/v4/2c/e6/9c/2ce69c27-3430-cd72-d954-5dad69956bfb/source/512x512bb.jpg'
    })      
        Json_Pramter = urllib.parse.quote(json.dumps(block))
        item_items.setInfo('video', {
        'title': file_name, 
        'plot': info if info else 'No description available.'})
        SEPARATOR = ("[COLOR gray]╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌[/COLOR]", "")
        item_items.addContextMenuItems([
    ("File Info", f"RunPlugin({sys.argv[0]}?action=info&json={Json_Pramter})"),
    ("Add Bookmark", f"RunPlugin({sys.argv[0]}?action=bookmark&file={urllib.parse.quote(Json_Pramter)})"),
    ("Add Data", f"RunPlugin({sys.argv[0]}?action=adddata&file={urllib.parse.quote(Json_Pramter)})",),
   
    ("[COLOR red]Delete File[/COLOR]", f"RunPlugin({sys.argv[0]}?action=delete&file={urllib.parse.quote(Json_Pramter)})")
    , SEPARATOR,
], replaceItems=False)

        url =f"{sys.argv[0]}?VPlayer={urllib.parse.quote(json.dumps(block))}"
        xbmcplugin.addDirectoryItem(HANDLE, url, item_items, isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)
def container_file (mediapth=None):

    base_name = os.path.basename(mediapth)
    ext =os.path.splitext(mediapth)[1]
    info =   thumb=path=  icon=None
    data_media=_media_library.get("media", {})      
    if base_name in data_media:
         meda = data_media[base_name]
         info =meda.get("info", None)

         icon =meda.get("icon", None)
         thumb =meda.get("thumb", None)
         path =meda.get( "path", None)

    else:
            data_media[base_name] = {  "info":info,
    "path": mediapth,
    "file": base_name,
    "extension": f"{ext.lower().lstrip('.')}",
    "icon":icon,
     "thumb": thumb}
            _media_library.set("media", data_media)

    Pramters = {
     "info":info,
    "path": path if path else mediapth,
    "file": base_name,
    "extension": f"{ext.lower().lstrip('.')}",
    "icon":icon,
     "thumb": thumb
   # "size": os.path.getsize(media_path)
}
    Json_Pramter = urllib.parse.quote(json.dumps(Pramters))
    """Return a ListItem for the 'moob' folder without ending the directory"""
    folder_name = base_name
    list_item = xbmcgui.ListItem(label=folder_name)

    # Optional: add icon/thumb
    list_item.setArt({
        'icon': icon if icon else 'https://www.shutterstock.com/shutterstock/videos/3400579563/thumb/11.jpg?ip=x480',
        'thumb': thumb if thumb else 'https://is3-ssl.mzstatic.com/image/thumb/Purple124/v4/2c/e6/9c/2ce69c27-3430-cd72-d954-5dad69956bfb/source/512x512bb.jpg'
    })
    list_item.setInfo('video', {
        'title': base_name,   
 
        'plot': info if info else 'No description available.'})
    SEPARATOR = ("[COLOR gray]╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌[/COLOR]", "")
    # Optional: add context menu
    list_item.addContextMenuItems([
    ("File Info", f"RunPlugin({sys.argv[0]}?action=info&json={Json_Pramter})"),
    ("Add Bookmark", f"RunPlugin({sys.argv[0]}?action=bookmark&file={urllib.parse.quote(Json_Pramter)})"),
    ("Add Data", f"RunPlugin({sys.argv[0]}?action=adddata&file={urllib.parse.quote(Json_Pramter)})",),
   
    ("[COLOR red]Delete File[/COLOR]", f"RunPlugin({sys.argv[0]}?action=delete&file={urllib.parse.quote(Json_Pramter)})")
    , SEPARATOR,
], replaceItems=False)


    # URL Kodi will call when clicked
    url =f"{sys.argv[0]}?VPlayer={Json_Pramter}"
    return url, list_item
def handle_action(action, file_path):

    """Handle context menu actions"""
    if file_path:
        file_path = urllib.parse.unquote(file_path)
    
    if action == "info":
        show_info(file_path)
    elif action == "delete":
        delete_file(file_path)
    elif action == "bookmark":
        add_bookmark(file_path)
    elif action == "adddata":
       # add_data(file_path)
       ADaddDON = xbmcaddon.Addon("plugin.video.arabic-mubaher")
       ADDON_PATH = ADaddDON.getAddonInfo("path")
       xml_file = "resources/skins/default/1080i/options.xml" 
       XML_FILE  = "options.xml"
       SKIN_NAME = "default"
       RES_NAME  = "1080i"

# Create and show the window
       window = OptionsWindow(XML_FILE, ADDON_PATH, SKIN_NAME, RES_NAME)
       window.doModal()
       del win
       pass
    pass




class OptionsWindow(xbmcgui.WindowXML):
    def onInit(self):
        xbmcgui.Dialog().notification("Test", "Window loaded!", xbmcgui.NOTIFICATION_INFO, 3000)

    def onClick(self, controlId):
        if controlId == 200:
            xbmcgui.Dialog().notification("Play", "Playing video...", xbmcgui.NOTIFICATION_INFO, 3000)
        elif controlId == 201:
            xbmc.executebuiltin("Action(Info)")
            xbmcgui.Dialog().notification("Info", "Showing info...", xbmcgui.NOTIFICATION_INFO, 3000)
        elif controlId == 202:
            xbmcgui.Dialog().notification("Trailer", "Playing trailer...", xbmcgui.NOTIFICATION_INFO, 3000)

def player (args):
          
          raw_json = urllib.parse.unquote(args["VPlayer"])
          data = json.loads(raw_json)
          file_path = data.get("path")
          ext= data.get("Extension")
          filename= data.get("file")
 
        #  file_path = os.path.join(folder_path, f)
          list_item = xbmcgui.ListItem(label= data.get("file"))
          list_item.setPath(file_path)
          list_item.setProperty("IsPlayable", "true")  # mark as playable
          xbmcplugin.addDirectoryItem(HANDLE, url=file_path, listitem=list_item, isFolder=False)
          back_item = xbmcgui.ListItem(label="⬅ Back")
          back_item.setProperty("IsPlayable", "false")

          xbmcplugin.addDirectoryItem(
    handle=HANDLE,
    url="plugin://plugin.video.arabic-mubaher/?category=0",
    listitem=back_item,
    isFolder=True   # ⬅ هنا يجب أن يكون True
)

          player = xbmc.Player()
          playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
          xbmcgui.Dialog().ok("Playing", f"Now playing: {str (sys.argv[0] )}")
          key = filename
          data=settings.get("play", {})
      #    all_play = settings.get("play", {})
          if key not in data:
                data[key] = True
                settings.set("play", data)
                   
          if data[key]:
              
               #   player.play(file_path)
                  if "plugin://" in str(file_path).lower():
                #      smart_play(file_path)
                      xbmc.executebuiltin(f'PlayMedia("{file_path}")')
                  else:
                   xbmc.Player().play(file_path)

                   xbmcgui.Dialog().notification(
    "Playing",
    f"Now playing:\n{file_path}",
    xbmcgui.NOTIFICATION_INFO,
    3000
)             
  
                  data[key] = False
                  settings.set("play", data)
                
          else:
                # player.stop()
                 data[key] = True
                 settings.set("play", data)
          xbmc.executebuiltin(f'RunPlugin("plugin://plugin.video.arabic-mubaher/?category=0')
              


             #    xbmc.executebuiltin("Action(ParentDir)")
           #   xbmc.executebuiltin("ActivateWindow(Videos,plugin://plugin.video.arabic-mubaher/,return)")
          #xbmc.sleep(10000)
        #  xbmc.executebuiltin("Action(ParentDir)")
        #  xbmc.executebuiltin("ActivateWindow(Videos)")
        
         
                 


         

        
        
        
        
        
        
        
         



         # if not isinstance(all_play, dict):
       
        
        
        
           
         #     all_play = settings.get("play", {})
        
          xbmcplugin.endOfDirectory(HANDLE)
        
       #   player.play(file_path)
         
# Finish the directory listing
'''''
          xbmcplugin.endOfDirectory(HANDLE)
          if  ext != "strm":
            
            # player.stop()
            xbmc.executebuiltin("Action(ParentDir)")
          if player.isPlaying():
               player.stop() '''

args = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
if "VPlayer" in args:
      
      #  xbmcgui.Dialog().ok("","yes")
      player(args)
     
