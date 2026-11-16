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
from resources.lib.bookmark_db import BookmarkManager
from resources.lib.gui.OptionsWindow import OptionsWindow
from m3u_file import player_m3u, play_m3u_item, save_m3u_item, download_m3u_item, set_dependencies, decode_json_param
# YouTube support (detect + resolve + play videos/playlists) lives in youtube_pluging.py
# Set ENABLE_YOUTUBE = False to switch ALL YouTube handling off and get the
# original behaviour back (handy to find out what is freezing Kodi).
ENABLE_YOUTUBE = True

YOUTUBE_AVAILABLE = False
YT_PLAYLIST_ACTION = "youtube_playlist"   # same value as youtube_pluging.PLAYLIST_ACTION
if ENABLE_YOUTUBE:
    try:
        from  resources.lib.youtube_pluging import (
            is_youtube_url,
            is_youtube_playlist_url,
            extract_playlist_id,
            launch_youtube_async,
            display_youtube_playlist,
            get_playlist_route_url,
            PLAYLIST_ACTION as YT_PLAYLIST_ACTION,
        )
        YOUTUBE_AVAILABLE = True
    except Exception as _yt_err:
        # youtube_pluging.py missing / not in the same folder / has an error.
        # The add-on keeps working; the reason is written to kodi.log.
        xbmc.log(f"[YouTube] Could not import youtube_pluging.py: {_yt_err}", xbmc.LOGERROR)

#from resources.lib.m3u_file import M3UFileHandler
# Initialize settings

settings = KodiSettings()
bookmark=BookmarkManager()
_media_library = KodiSettings(filename="media_library.json")

HANDLE = int(sys.argv[1])
# Initialize M3UFileHandler with settings and media library


class TV:
    
    """TV addon class for managing media files"""
   
   
    VIDEO_EXT = ['.mp4', '.mkv', '.avi', '.m3u8', '.m3u', '.strm']
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


def is_playlist_entry(path):
    """True if a library entry is a YouTube PLAYLIST URL.

    Such entries are shown as FOLDERS: opening one lists the playlist's videos
    in a Kodi directory (see display_youtube_playlist) instead of playing.
    """
    return bool(
        YOUTUBE_AVAILABLE
        and isinstance(path, str)
        and is_youtube_url(path)
        and extract_playlist_id(path)
    )


def play_if_youtube(url):
    """Hand a YouTube link to youtube_pluging.py WITHOUT blocking Kodi.

        YouTube playlist URL -> (only reached for playable entries such as M3U
                                items; library entries open as a folder
                                instead) all its videos are IMPORTED into
                                Kodi's video playlist, playback NOT started
        YouTube video URL    -> played

    The work runs in a separate Kodi script, so this call returns
    immediately (a long add-on call makes Kodi show a busy spinner / look
    frozen). The script shows its own notification.

    Args:
        url: Path or URL that is about to be played.

    Returns:
        bool: True  -> it is a YouTube URL and it was handed over, so the
                       caller must NOT play it again.
              False -> not a YouTube URL (or YouTube support unavailable);
                       the caller continues with its normal logic.
    """
    if not YOUTUBE_AVAILABLE or not isinstance(url, str):
        return False

    try:
        if not is_youtube_url(url):
            return False

        # Report success only when the YouTube module actually accepted the URL.
        return bool(launch_youtube_async(url))
    except Exception as e:
        # Never break the add-on because of the YouTube module
        import traceback
        xbmc.log(f"[YouTube] error: {e}\n{traceback.format_exc()}", xbmc.LOGERROR)
        return False


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


def add_bookmark(Vname):
    """Add a bookmark to a file"""
    if not Vname:
        xbmcgui.Dialog().notification("Bookmark", "Invalid file path!")
        return

    if bookmark.add(Vname):
        xbmcgui.Dialog().notification("Bookmark", f"'{Vname}' added to bookmarks!")

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

    # A YouTube playlist URL is shown as a FOLDER so that opening it lists the
    # playlist's videos. A playable item cannot show a directory.
    is_yt_playlist = is_playlist_entry(path)

    if not is_yt_playlist and parameter_video != "VPlayerM3U":
        # (An M3U/M3U8 file entry is NOT marked playable: opening it may have to
        # show a list of its links, which a playable item cannot do.)
        # This is a playable item, NOT a sub-directory. Without this, Kodi
        # treats the click as "navigate into a folder", pushing a new
        # (empty) directory level onto the navigation history every time an
        # item is played - i.e. content keeps "stacking" in Kodi.
        list_item.setProperty('IsPlayable', 'true')

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

    if is_yt_playlist:
        # Route back into this add-on: <base>?action=youtube_playlist&url=<playlist url>
        url = get_playlist_route_url(sys.argv[0], path)
    
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

        url, list_item, kind = create_media_list_item(
            file_name, path, ext, icon, thumb, info
        )
        # isFolder=False: these are playable files, not sub-directories.
        # isFolder=True was pushing a new (empty) directory level onto
        # Kodi's navigation stack every time an item was played.
        # (M3U/M3U8 file entries are the exception: they open a list of links.)
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=is_playlist_entry(path) or kind == "VPlayerM3U")

    

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
        add_bookmark(file_name)
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
    raw_json = args["VPlayer"]
    data = decode_json_param(raw_json)
    file_path = data.get("path")
    ext = data.get("extension")
    filename = data.get("file")

    key = filename
    play_data = settings.get("play", {})

    if key not in play_data:
        play_data[key] = True
        settings.set("play", play_data)

    player_obj = xbmc.Player()
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)

    if play_data[key]:
        # YouTube links (video / playlist / video inside a playlist) are
        # resolved and played by youtube_pluging.py, which also shows the
        # notification. Everything else uses the original logic below.
        youtube_handled = play_if_youtube(file_path)

        if youtube_handled:
            pass  # already playing (or error shown) - do not play twice
        elif "plugin://" in str(file_path).lower():
         
             xbmc.executebuiltin(f'PlayMedia("{file_path}")')
        
               
        else:
            xbmc.Player().play(file_path)

        # Kodi shows only one notification at a time, so skip the generic
        # "Playing" popup for YouTube (it would hide the YouTube message).
        if not youtube_handled:
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
    elif action == YT_PLAYLIST_ACTION:
        # A YouTube playlist folder was opened: list its videos in THIS
        # directory. display_youtube_playlist() calls
        # xbmcplugin.endOfDirectory(HANDLE) itself (once, also on failure),
        # so nothing else may finish this request.
        if YOUTUBE_AVAILABLE:
            display_youtube_playlist(HANDLE, args.get("url", ""))
        else:
            xbmcgui.Dialog().notification(
                "YouTube", "YouTube support is not available", xbmcgui.NOTIFICATION_ERROR
            )
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    elif action == "play_m3u_item":
        # Handle M3U item playback
        file_param = args.get("json")
        try:
            item_data = decode_json_param(file_param)
            # play_m3u_item resolves the final URL with xbmcplugin.setResolvedUrl.
            # Do not launch YouTube separately here: that leaves Kodi's playable
            # plugin request unfinished and can make the UI stack/freeze.
            play_m3u_item(item_data)
        except Exception as e:
            xbmcgui.Dialog().notification("Error", f"Failed to play item: {str(e)}")
    elif action == "save_m3u_item":
        # Handle M3U item save
        file_param = args.get("json")
        try:
            item_data = decode_json_param(file_param)
            save_m3u_item(item_data)
        except Exception as e:
            xbmcgui.Dialog().notification("Error", f"Failed to save item: {str(e)}")
    elif action == "download_m3u_item":
        # Handle M3U item download
        file_param = args.get("json")
        try:
            item_data = decode_json_param(file_param)
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