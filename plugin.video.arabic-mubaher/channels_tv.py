# channels_tv.py
import os
import sys
import json
import time
import threading
import urllib.parse

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs

from resources.lib.settings import KodiSettings
from resources.lib.gui.OptionsWindow import OptionsWindow
from m3u_file import player_m3u, play_m3u_item, save_m3u_item, download_m3u_item, set_dependencies

# Initialize settings
settings = KodiSettings()
_media_library = KodiSettings(filename="media_library.json")

HANDLE = int(sys.argv[1])


class TV:
    """TV addon class for managing media files"""
    
    VIDEO_EXT = ['.mp4', '.mkv', '.avi', '.m3u8', 'm3u', '.strm']
    AUDIO_EXT = ['.mp3', '.flac']

    addon = xbmcaddon.Addon()
    MEDIA_FOLDER = addon.getSetting("media_folder")

    @staticmethod
    def notify(title, msg, time=5000):
        """Display notification in Kodi"""
        xbmc.executebuiltin(f"Notification('{title}','{msg}',{time})")

    @classmethod
    def save_settings(cls):
        """Save settings to addon"""
        cls.addon.setSetting("media_folder", cls.MEDIA_FOLDER)

    @classmethod
    def check_folder(cls, path=None):
        """Check if media folder exists and is valid"""
        folder = path if path else cls.MEDIA_FOLDER

        if not folder or not os.path.exists(folder) or not os.path.isdir(folder):
            cls.notify("TV Addon", f"Folder not found:\n{folder}\nPlease select a new folder...")

            new_folder = xbmcgui.Dialog().browse(
                type=3,
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
                cls.notify("TV Addon", "No valid folder selected! No data loaded")

        return folder

    @classmethod
    def chk_browse_data(cls, path=None):
        """Check and browse media data
        
        Logic:
        1. إذا كانت البيانات موجودة في JSON → عرض من البيانات
        2. إذا كانت البيانات فارغة → مسح المجلد وحفظ البيانات
        """
        # تحقق من البيانات الموجودة
        existing_media = _media_library.get("media", {})
        
        if existing_media:
            # ✅ البيانات موجودة - عرض من JSON بدون مسح
            container_database()
        elif os.listdir(cls.MEDIA_FOLDER):
            # ✅ المجلد فيه ملفات - مسح وحفظ
            cls.browse_folder()
        else:
            # ❌ المجلد فارغ والبيانات فارغة
            cls.notify("TV Addon", "Media folder is empty!")

    @classmethod
    def get_media_nosql(cls):
        """Get media data from storage"""
        data = _media_library.get("media", {})
        return data

    @classmethod
    def browse_folder(cls, path=None):
        """Scan folder and save all media files to database
        
        هذه الدالة تُستدعى فقط عندما تكون البيانات فارغة وتحتاج مسح
        """
        # Convert all play settings to true
        data = settings.get("play", {})
        for key in list(data.keys()):
            data[key] = True
        settings.set("play", data)

        folder = path if path else cls.MEDIA_FOLDER

        if not folder:
            cls.notify("TV Addon", "Media folder not set!")
            return

        try:
            cls.notify("TV Addon", "Scanning media files...")
            
            # Recursively scan all files and save to database
            cls._scan_and_save_files(folder)
            cls.notify("TV Addon", "Media library loaded successfully!")
            
            # Display from database
            container_database()
        except Exception as e:
            cls.notify("TV Addon", f"Error scanning folder: {e}")

    @classmethod
    def _scan_and_save_files(cls, folder, recursive=True):
        """Recursively scan folder and save all media files to database"""
        try:
            for item in os.listdir(folder):
                item_path = os.path.join(folder, item)
                
                # If it's a directory, scan recursively
                if os.path.isdir(item_path):
                    if recursive:
                        cls._scan_and_save_files(item_path, recursive=True)
                else:
                    # Check file extension
                    ext = os.path.splitext(item)[1].lower()
                    if ext in cls.VIDEO_EXT or ext in cls.AUDIO_EXT:
                        # Save to database
                        container_file(item_path)
        except Exception as e:
            cls.notify("TV Addon", f"Error scanning: {item_path} - {e}")


# Initialize M3U module with TV class dependencies
set_dependencies(settings, _media_library, HANDLE, TV)


def show_info(file_path):
    """Display file information"""
    if not file_path or not os.path.exists(file_path):
        xbmcgui.Dialog().notification("Info", "File not found!")
        return

    file_size = os.path.getsize(file_path)
    file_size_mb = file_size / (1024 * 1024)
    file_name = os.path.basename(file_path)

    info_text = f"File: {file_name}\nSize: {file_size_mb:.2f} MB\nPath: {file_path}"
    xbmcgui.Dialog().ok("File Info", info_text)


def delete_file(file_name, file_path):
    """Delete file from database and Kodi window
    
    Args:
        file_name: Name of the file (e.g. 'movie.mp4')
        file_path: Full path to the file (e.g. '/path/to/movie.mp4')
    """
    if not file_name or not file_path:
        xbmcgui.Dialog().notification("Delete", "Invalid file info!")
        return

    confirm = xbmcgui.Dialog().yesno(
        "Remove from Library",
        f"Are you sure you want to remove:\n{file_name}?"
    )

    if confirm:
        try:
            # Delete from media database
            data_media = _media_library.get("media", {})
            if file_name in data_media:
                del data_media[file_name]
                _media_library.set("media", data_media)
            
            # Refresh Kodi window
            xbmc.executebuiltin("Container.Refresh()")
            xbmcgui.Dialog().notification("Delete", "Removed from library successfully!")
            
        except Exception as e:
            xbmcgui.Dialog().notification("Delete", f"Error: {str(e)}")
    else:
        xbmcgui.Dialog().notification("Delete", "Removal cancelled")


def add_bookmark(file_path):
    """Add a bookmark to a file"""
    if not file_path:
        xbmcgui.Dialog().notification("Bookmark", "Invalid file path!")
        return

    keyboard = xbmc.Keyboard('', 'Enter bookmark name')
    keyboard.doModal()

    if keyboard.isConfirmed():
        bookmark_name = keyboard.getText()
        if bookmark_name:
            xbmcgui.Dialog().notification("Bookmark", f"Bookmarked as: {bookmark_name}")
        else:
            xbmcgui.Dialog().notification("Bookmark", "Bookmark name cannot be empty!")
    else:
        xbmcgui.Dialog().notification("Bookmark", "Bookmark cancelled")


def add_data(file_path):
    """Add data/notes to a file"""
    if not file_path:
        xbmcgui.Dialog().notification("Add Data", "Invalid file path!")
        return

    keyboard = xbmc.Keyboard('', 'Enter data/notes')
    keyboard.doModal()

    if keyboard.isConfirmed():
        data = keyboard.getText()
        if data:
            xbmcgui.Dialog().notification("Add Data", "Data saved successfully!")
        else:
            xbmcgui.Dialog().notification("Add Data", "No data entered!")
    else:
        xbmcgui.Dialog().notification("Add Data", "Operation cancelled")


def copy_m3u_content(file_path, file_name):
    """Copy all M3U/M3U8 file content to clipboard
    
    Args:
        file_path: Full path to the M3U file
        file_name: Name of the file
    """
    if not file_path or not os.path.exists(file_path):
        xbmcgui.Dialog().notification("Copy Content", "File not found!")
        return

    try:
        # Read M3U file content
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                m3u_content = f.read()
        except:
            with xbmcvfs.File(file_path) as f:
                m3u_content = f.read().decode('utf-8', errors='ignore')

        if not m3u_content or not m3u_content.strip():
            xbmcgui.Dialog().notification("Copy Content", "File is empty!")
            return

        # Copy to clipboard using xbmc
        import subprocess
        
        # Try different methods based on platform
        try:
            # For Linux/Windows with xclip
            process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
            process.communicate(m3u_content.encode('utf-8'))
        except:
            try:
                # For Windows with powershell
                process = subprocess.Popen(['powershell', '-Command', f"[System.Windows.Forms.SendKeys]::SendWait('{m3u_content}')"], stdin=subprocess.PIPE)
            except:
                try:
                    # For macOS
                    process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
                    process.communicate(m3u_content.encode('utf-8'))
                except:
                    # Fallback: show content in dialog
                    xbmcgui.Dialog().textviewer("M3U Content - " + file_name, m3u_content)
                    xbmcgui.Dialog().notification(
                        "Content Displayed",
                        "M3U content shown in text viewer.\nCopy manually if needed."
                    )
                    return

        # Count lines and items
        lines = m3u_content.strip().split('\n')
        extinf_count = sum(1 for line in lines if line.startswith('#EXTINF:'))
        url_count = sum(1 for line in lines if line and not line.startswith('#'))

        xbmcgui.Dialog().notification(
            "Content Copied",
            f"M3U Content copied to clipboard!\n"
            f"Lines: {len(lines)} | Channels: {extinf_count} | URLs: {url_count}"
        )

    except Exception as e:
        xbmc.log(f"Copy M3U Error: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Error", f"Failed to copy content:\n{str(e)}")


# Default icons/thumbnails
DEFAULT_ICON = 'https://www.shutterstock.com/shutterstock/videos/3400579563/thumb/11.jpg?ip=x480'
DEFAULT_THUMB = 'https://is3-ssl.mzstatic.com/image/thumb/Purple124/v4/2c/e6/9c/2ce69c27-3430-cd72-d954-5dad69956bfb/source/512x512bb.jpg'
Refresh_ICON = 'https://cdn-icons-png.flaticon.com/512/6033/6033657.png'


def create_media_list_item(file_name, path, ext, icon=None, thumb=None, info=None):
    """Create a ListItem for media with context menu
    
    Args:
        file_name: Display name of the file
        path: Full path to the file
        ext: File extension
        icon: Icon URL (optional)
        thumb: Thumbnail URL (optional)
        info: Description/info text (optional)
        
    Returns:
        tuple: (url, list_item, parameter_video)
    """
    parameter_video = "VPlayerM3U" if ("m3u" in ext.lower() or "m3u8" in ext.lower()) else "VPlayer"
    
    # Create ListItem
    list_item = xbmcgui.ListItem(label=file_name)
    
    # Set artwork
    list_item.setArt({
        'icon': icon if icon else DEFAULT_ICON,
        'thumb': thumb if thumb else DEFAULT_THUMB
    })
    
    # Set video info
    list_item.setInfo('video', {
        'title': file_name,
        'plot': info if info else 'No description available.'
    })
    
    # Create parameters dictionary
    params = {
        "info": info,
        "path": path,
        "file": file_name,
        "extension": f"{ext.lower().lstrip('.')}",
        "icon": icon,
        "thumb": thumb
    }
    json_param = urllib.parse.quote(json.dumps(params))
    
    # Create context menu
    context_menu = [
        ("File Info", f"RunPlugin({sys.argv[0]}?action=info&json={json_param})"),
        ("Add Bookmark", f"RunPlugin({sys.argv[0]}?action=bookmark&file={urllib.parse.quote(json_param)})"),
        ("Add Data", f"RunPlugin({sys.argv[0]}?action=adddata&file={urllib.parse.quote(json_param)})"),
    ]
    
    # Add copy content option for M3U/M3U8 files
    if "m3u" in ext.lower() or "m3u8" in ext.lower():
        context_menu.append(
            ("[COLOR green]📋 Copy M3U Content[/COLOR]", f"RunPlugin({sys.argv[0]}?action=copy_m3u&json={json_param})")
        )
    
    # Add delete option
    context_menu.append(
        ("[COLOR red]Delete File[/COLOR]", f"RunPlugin({sys.argv[0]}?action=delete&json={json_param})")
    )
    
    list_item.addContextMenuItems(context_menu, replaceItems=False)
    
    # Create URL
    url = f"{sys.argv[0]}?{parameter_video}={json_param}"
    
    return url, list_item, parameter_video


def container_database():
    """Display media from database"""
    # Add Refresh button
    refresh_url = f"{sys.argv[0]}?action=refresh"
    refresh_item = xbmcgui.ListItem(label="Refresh Library")
    refresh_item.setArt({
        'icon': Refresh_ICON,
        'thumb': Refresh_ICON
    })
    xbmcplugin.addDirectoryItem(HANDLE, refresh_url, refresh_item, isFolder=False)
    data = _media_library.get("media", {})

    for key in list(data.keys()):
        block = data[key]
        path = block.get("path", None)
        file_name = block.get("file", None)
        icon = block.get("icon", None)
        thumb = block.get("thumb", None)
        info = block.get("info", None)
        ext = block.get("extension", None)

        url, list_item, _ = create_media_list_item(
            file_name, path, ext, icon, thumb, info
        )
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=True)

    

    xbmcplugin.endOfDirectory(HANDLE)


def container_file(media_path):
    """Process a media file and return URL and ListItem"""
    data_media = _media_library.get("media", {})
    base_name = os.path.basename(media_path)
    ext = os.path.splitext(media_path)[1].lower()

    # Get file info from database if exists
    if base_name in data_media:
        file_data = data_media[base_name]
        info = file_data.get("info", None)
        icon = file_data.get("icon", None)
        thumb = file_data.get("thumb", None)
        file_path = file_data.get("path", None)
    else:
        info = None
        icon = None
        thumb = None
        file_path = media_path

        # Process strm files
        if "strm" in ext.lower():
            file_path = xbmcvfs.File(media_path).read().strip()

        # Store in database
        data_media[base_name] = {
            "info": info,
            "path": file_path,
            "file": base_name,
            "extension": f"{ext.lower().lstrip('.')}",
            "icon": icon,
            "thumb": thumb
        }

        # For m3u files, also read content
        if "m3u" in ext.lower() or "m3u8" in ext.lower():
            content_txt = xbmcvfs.File(file_path).read().strip()
            data_media[base_name]["containtxt"] = content_txt

        _media_library.set("media", data_media)

    # Create and return ListItem using helper function
    url, list_item, _ = create_media_list_item(
        base_name, file_path, ext, icon, thumb, info
    )
    return url, list_item


def handle_action(action, file_data):
    """Handle context menu actions
    
    Args:
        action: Action type (info, delete, bookmark, adddata, copy_m3u)
        file_data: Dict with file information {path, file, extension, ...}
    """
    if not file_data:
        return
    
    file_name = file_data.get("file")
    file_path = file_data.get("path")

    if action == "info":
        show_info(file_path)
    elif action == "delete":
        delete_file(file_name, file_path)
    elif action == "bookmark":
        add_bookmark(file_path)
    elif action == "adddata":
        addon = xbmcaddon.Addon("plugin.video.arabic-mubaher")
        addon_path = addon.getAddonInfo("path")
        xml_file = "options.xml"
        skin_name = "default"
        res_name = "1080i"

        options_window = OptionsWindow(xml_file, addon_path, skin_name, res_name)
        options_window.doModal()
    elif action == "copy_m3u":
        copy_m3u_content(file_path, file_name)


def player(args):
    """Play media file"""
    raw_json = urllib.parse.unquote(args["VPlayer"])
    data = json.loads(raw_json)
    file_path = data.get("path")
    ext = data.get("extension")
    filename = data.get("file")

    player_obj = xbmc.Player()
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)

    key = filename
    play_data = settings.get("play", {})

    if key not in play_data:
        play_data[key] = True
        settings.set("play", play_data)

    if play_data[key]:
        if "plugin://" in str(file_path).lower():
            xbmc.executebuiltin(f'PlayMedia("{file_path}")')
        else:
            xbmc.Player().play(file_path)

        xbmcgui.Dialog().notification(
            "Playing",
            f"Now playing:\n{file_path}",
            xbmcgui.NOTIFICATION_INFO,
            3000
        )

        play_data[key] = False
        settings.set("play", play_data)
    else:
        play_data[key] = True
        settings.set("play", play_data)

    xbmc.executebuiltin('RunPlugin("plugin://plugin.video.arabic-mubaher/?category=0")')

    xbmcplugin.endOfDirectory(HANDLE)

    if not player_obj.isPlaying():
        url = "plugin://plugin.video.arabic-mubaher/?category=0"
        xbmc.executebuiltin(f"Container.Update({url}, replace)")


args = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))

if "action" in args:
    action = args["action"]
    if action == "refresh":
        TV.browse_folder()
        xbmc.executebuiltin("Container.Refresh()")
    elif action == "play_m3u_item":
        # Handle M3U item playback
        file_param = args.get("json")
        try:
            item_data = json.loads(urllib.parse.unquote(file_param))
            play_m3u_item(item_data)
        except Exception as e:
            xbmcgui.Dialog().notification("Error", f"Failed to play item: {str(e)}")
    elif action == "save_m3u_item":
        # Handle M3U item save
        file_param = args.get("json")
        try:
            item_data = json.loads(urllib.parse.unquote(file_param))
            save_m3u_item(item_data)
        except Exception as e:
            xbmcgui.Dialog().notification("Error", f"Failed to save item: {str(e)}")
    elif action == "download_m3u_item":
        # Handle M3U item download
        file_param = args.get("json")
        try:
            item_data = json.loads(urllib.parse.unquote(file_param))
            download_m3u_item(item_data)
        except Exception as e:
            xbmcgui.Dialog().notification("Error", f"Failed to download item: {str(e)}")
    else:
        # Handle other actions (info, delete, bookmark, adddata)
        file_param = args.get("json") or args.get("file")
        try:
            file_data = json.loads(urllib.parse.unquote(file_param))
            handle_action(action, file_data)
        except Exception as e:
            xbmcgui.Dialog().notification("Error", f"Action failed: {str(e)}")
elif "VPlayer" in args:
    player(args)
elif "VPlayerM3U" in args:
    player_m3u(args)