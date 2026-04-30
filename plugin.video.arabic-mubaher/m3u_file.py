# m3u_file.py
"""M3U Playlist Handler Module
معالج ملفات M3U/M3U8 - التشغيل والحفظ والتحميل
"""

import os
import sys
import json
import urllib.parse

import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs


def set_dependencies(settings_obj, media_library_obj, handle, tv_class):
    """Initialize dependencies
    
    ضبط الاعتماديات من channels_tv.py
    """
    global settings, _media_library, HANDLE, TV
    settings = settings_obj
    _media_library = media_library_obj
    HANDLE = handle
    TV = tv_class


def player_m3u(args):
    """Play media from M3U/M3U8 playlist files (IPTV or Videos/Sounds list)
    
    إذا كان الملف يحتوي على رابط واحد فقط → شغله مباشرة
    إذا كانت هناك عدة روابط → عرض القائمة
    """
    try:
        raw_json = urllib.parse.unquote(args["VPlayerM3U"])
        data = json.loads(raw_json)
        file_path = data.get("path")
        ext = data.get("extension")
        filename = data.get("file")

        if not file_path or not os.path.exists(file_path):
            xbmcgui.Dialog().notification("Error", f"File not found: {file_path}")
            return

        # Check if M3U content is stored in database
        data_media = _media_library.get("media", {})
        base_name = os.path.basename(file_path)
        
        # Try to get content from database first
        m3u_content = None
        if base_name in data_media:
            m3u_content = data_media[base_name].get("containtxt")
        
        # If not in database, read from file
        if not m3u_content:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    m3u_content = f.read().strip()
            except:
                with xbmcvfs.File(file_path) as f:
                    m3u_content = f.read().decode('utf-8', errors='ignore').strip()

        if not m3u_content:
            xbmcgui.Dialog().notification("Error", "M3U file is empty")
            return

        # Parse M3U content - handle EXTINF and EXTVLCOPT
        lines = m3u_content.split('\n')
        playlist_items = []
        current_title = ""
        i = 0

        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and header
            if not line or line == "#EXTM3U":
                i += 1
                continue
            
            # Extract title from EXTINF
            if line.startswith('#EXTINF:'):
                # Format: #EXTINF:duration,title
                parts = line.split(',', 1)
                current_title = parts[1].strip() if len(parts) > 1 else ""
                i += 1
                continue
            
            # Skip EXTVLCOPT and other metadata (but continue looking for URL)
            if line.startswith("#EXTVLCOPT:") or line.startswith("#EXT-X-") or line.startswith("#"):
                i += 1
                continue
            
            # Found a valid URL/path
            if line and (line.startswith(('http://', 'https://', 'rtmp://', 'mmsh://', '/', './'))):
                item_name = current_title if current_title else os.path.basename(line)
                item_name = item_name.strip()
                
                if item_name and line:
                    playlist_items.append({
                        "name": item_name,
                        "url": line,
                        "info": current_title
                    })
                
                current_title = ""
            
            i += 1

        if not playlist_items:
            xbmcgui.Dialog().notification(
                "No Items Found",
                "Could not find playable URLs in M3U file"
            )
            return

        # إذا كان هناك رابط واحد فقط → شغله مباشرة
        if len(playlist_items) == 1:
            item = playlist_items[0]
            url = item["url"]
            name = item["name"]
            
            # Check if URL is in content
            if url not in m3u_content:
                xbmcgui.Dialog().notification(
                    "URL Not Found",
                    "URL not found in M3U file"
                )
                return
            
            # Play directly
            key = filename
            play_data = settings.get("play", {})

            if key not in play_data:
                play_data[key] = True
                settings.set("play", play_data)
            if play_data[key]:  
                player_obj = xbmc.Player()
                if "plugin://" in str(url).lower():
                    xbmc.executebuiltin(f'PlayMedia("{url}")')
                else:
                    player_obj.play(url)
                play_data[key] = False  
                settings.set("play", play_data)   
                
                xbmcgui.Dialog().notification(
                    "Playing",
                    f"Now playing:\n{name}",
                    xbmcgui.NOTIFICATION_INFO,
                    3000
                )
            else:
                play_data[key] = True
                settings.set("play", play_data)
            xbmc.executebuiltin("Action(Back)")
           
            return

        # إذا كانت هناك عدة روابط → عرض القائمة
        xbmcplugin.setContent(HANDLE, "videos")

        for item in playlist_items:
            list_item = xbmcgui.ListItem(label=item["name"])
            
            # Check if audio or video
            url = item["url"]
            is_audio = any(aud_ext in url.lower() for aud_ext in ['.mp3', '.flac', '.aac', '.wav', '.ogg'])
            
            if is_audio:
                list_item.setInfo('music', {
                    'title': item["name"],
                    'artist': "From M3U Playlist"
                })
            else:
                list_item.setInfo('video', {
                    'title': item["name"],
                    'plot': item["info"] if item["info"] else "From M3U/M3U8 Stream"
                })
            
            # Mark as playable
            list_item.setProperty("IsPlayable", "true")

            # Create playback URL with verification
            play_params = {
                "action": "play_m3u_item",
                "url": url,
                "name": item["name"],
                "parent_file": filename,
                "verify_in_content": m3u_content  # Pass content for verification
            }
            json_param = urllib.parse.quote(json.dumps(play_params))
            item_url = f"{sys.argv[0]}?action=play_m3u_item&json={json_param}"
            
            # Add context menu items
            save_params = {
                "action": "save_m3u_item",
                "url": url,
                "name": item["name"]
            }
            save_json = urllib.parse.quote(json.dumps(save_params))
            save_url = f"{sys.argv[0]}?action=save_m3u_item&json={save_json}"
            
            download_params = {
                "action": "download_m3u_item",
                "url": url,
                "name": item["name"]
            }
            download_json = urllib.parse.quote(json.dumps(download_params))
            download_url = f"{sys.argv[0]}?action=download_m3u_item&json={download_json}"
            
            context_menu_items = [
                ("Save URL", f"RunPlugin({save_url})"),
                ("Download File", f"RunPlugin({download_url})")
            ]
            list_item.addContextMenuItems(context_menu_items)

            xbmcplugin.addDirectoryItem(HANDLE, item_url, list_item, isFolder=False)

        xbmcplugin.endOfDirectory(HANDLE)

    except Exception as e:
        xbmc.log(f"M3U Parse Error: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Parse Error", f"Failed to parse M3U:\n{str(e)}")
   

def save_m3u_item(item_data):
    """Save M3U item URL to a text file
    
    حفظ رابط العنصر في ملف نصي
    """
    try:
        if not item_data:
            return
        
        url = item_data.get("url")
        name = item_data.get("name", "Unknown")
        data_media = _media_library.get("media", {})
        
        if not url:
            xbmcgui.Dialog().notification("Error", "Invalid URL")
            return
         
        # Store in database
        data_media[name] = {
            "info": None,
            "path": url,
            "file": name,
            "extension": "strm",
            "icon": None,
            "thumb": None
        }
        _media_library.set("media", data_media)
        
        xbmcgui.Dialog().notification(
            "Saved",
            f"URL saved:\n{name}",
            xbmcgui.NOTIFICATION_INFO,
            3000
        )
    except Exception as e:
        xbmc.log(f"Save Error: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Error", f"Failed to save: {str(e)}")


def download_m3u_item(item_data):
    """Download M3U item file
    
    تحميل ملف العنصر من M3U
    """
    try:
        if not item_data:
            return
        
        url = item_data.get("url")
        name = item_data.get("name", "Unknown")
        
        if not url:
            xbmcgui.Dialog().notification("Error", "Invalid URL")
            return
        
        # Check if it's a remote URL (http/https/rtmp)
        file_path = os.path.join(TV.MEDIA_FOLDER, f"{name}.strm")
        
        # If file exists, ask user
        if os.path.exists(file_path):
            overwrite = xbmcgui.Dialog().yesno(
                "File Exists",
                f"{name}.strm already exists.\nOverwrite?"
            )
            if not overwrite:
                return
        
        # Save URL to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(url)
        
        xbmcgui.Dialog().notification(
            "Download Complete",
            f"Stream file saved:\n{name}.strm",
            xbmcgui.NOTIFICATION_INFO,
            3000
        )
    
    except Exception as e:
        xbmc.log(f"Download Error: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Error", f"Failed to save: {str(e)}")

def play_m3u_item(item_data):
    """Play a single item from M3U playlist
    
    يتحقق من وجود الرابط في محتوى الملف المحفوظ (containtxt) قبل التشغيل
    """
    try:
        if not item_data:
            return

        url = item_data.get("url")
        name = item_data.get("name", "Unknown")
        parent_file = item_data.get("parent_file")

        if not url:
            xbmcgui.Dialog().notification("Error", "Invalid URL")
            return

        # Verify that URL exists in M3U content if we have it
        verify_content = item_data.get("verify_in_content")
        
        if verify_content and url not in verify_content:
            xbmcgui.Dialog().notification(
                "URL Not Found",
                f"This URL is not found in the M3U file.\n"
                f"URL: {url[:50]}..."
            )
            xbmc.log(f"URL not in M3U content: {url}", xbmc.LOGWARNING)
            return

        # Check database for URL existence
        if parent_file and not verify_content:
            data_media = _media_library.get("media", {})
            if parent_file in data_media:
                stored_content = data_media[parent_file].get("containtxt")
                if stored_content and url not in stored_content:
                    xbmcgui.Dialog().notification(
                        "URL Not Found",
                        f"URL not found in stored M3U content"
                    )
                    xbmc.log(f"URL not in stored M3U content: {url}", xbmc.LOGWARNING)
                    return

        # URL verification passed, proceed with playback
        player_obj = xbmc.Player()

        # Check if it's a plugin URL or regular file/stream
        if "plugin://" in str(url).lower():
            xbmc.executebuiltin('RunPlugin("plugin://plugin.video.arabic-mubaher/?category=0")')
        else:
            player_obj.play(url)

        xbmcgui.Dialog().notification(
            "Playing",
            f"Now playing:\n{name}",
            xbmcgui.NOTIFICATION_INFO,
            3000
        )
      

    except Exception as e:
        xbmc.log(f"Playback Error: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Error", f"Playback failed: {str(e)}")