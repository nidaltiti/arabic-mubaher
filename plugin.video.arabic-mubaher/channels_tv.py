# channels_tv.py
import os
import sys
import xbmcgui
import xbmcplugin
import xbmc
import xbmcaddon
import urllib.parse
import json


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
                cls.notify("TV Addon", "No valid folder selected!")
                return None

        return folder

    @classmethod
    def browse_folder(cls, path=None):
      
        folder = path if path else cls.MEDIA_FOLDER

        if not folder:
            cls.notify("TV Addon", "Media folder not set!")
            return
      
        try:
          
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

def container_file (mediapth=None):

    base_name = os.path.basename(mediapth)
    ext =os.path.splitext(mediapth)[1]
    info =   thumb=  icon=None
    Pramters = {
     "info":info,
    "path": mediapth,
    "file": base_name,
    "Extension": f"{ext.lower().lstrip('.')}",
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
        'icon': 'https://m.media-amazon.com/images/I/41JOUrrSWyL.png',
        'thumb': 'https://i.ytimg.com/vi/kpiM9_P-hkQ/maxresdefault.jpg'
    })
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
        add_data(file_path)
        pass
    pass


def player (args):
          
          raw_json = urllib.parse.unquote(args["VPlayer"])
          data = json.loads(raw_json)
          file_path = data.get("path")
          ext= data.get("Extension")

        #  file_path = os.path.join(folder_path, f)
          list_item = xbmcgui.ListItem(label= data.get("file"))
          list_item.setPath(file_path)
          list_item.setProperty("IsPlayable", "true")  # mark as playable
          xbmcplugin.addDirectoryItem(HANDLE, url=file_path, listitem=list_item, isFolder=False)
          player = xbmc.Player()
          playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
          
        
        
        
          class dict:
           auto={}
           def  __init__(self):
            pass
           def append(self,item):
                dict.auto.append(item)
                dict[item]=True
             
                return  dict.auto
           
           
        
        
        
        
          player.play(file_path)
         
# Finish the directory listing
          xbmcplugin.endOfDirectory(HANDLE)
          if  ext != "strm":
            
            # player.stop()
            xbmc.executebuiltin("Action(ParentDir)")
          if player.isPlaying():
               player.stop() 

args = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
if "VPlayer" in args:
      #  xbmcgui.Dialog().ok("","yes")
      player(args)