# m3u_file.py
"""M3U Playlist Handler Module
معالج ملفات M3U/M3U8 - التشغيل والحفظ والتحميل
"""

import os
import sys
import json
import urllib.parse
import importlib

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


def decode_json_param(raw):
    """Load the JSON that was put into a plugin URL parameter.

    The JSON is quoted ONCE when the URL is built, and Kodi/parse_qsl already
    decode it once, so it is normally valid JSON here. Decoding it a second
    time turns %2B / %20 / %26 / %3D inside a stream URL into + / space / & / =
    and breaks signed (token) URLs. Only if it is still percent-encoded
    (double-quoted URLs) is it decoded once more.
    """
    try:
        return json.loads(raw)
    except ValueError:
        return json.loads(urllib.parse.unquote(raw))


def _extinf_title(line):
    """Title of a '#EXTINF:<duration> <attributes>,<title>' line.

    The title follows the first comma that is NOT inside double quotes, so an
    attribute such as group-title="News, Sports" does not cut the title.
    """
    in_quotes = False
    for index, char in enumerate(line):
        if char == '"':
            in_quotes = not in_quotes
        elif char == "," and not in_quotes:
            return line[index + 1:].strip()
    return ""


def _end_directory_failed():
    """Finish this plugin request without a listing (nothing to show).

    Kodi keeps waiting (busy spinner) until a plugin request that Kodi opened
    as a directory is finished with endOfDirectory.
    """
    try:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    except Exception as e:
        xbmc.log(f"endOfDirectory failed: {str(e)}", xbmc.LOGERROR)


def _youtube_playlist_route(url):
    """Return this add-on's folder route for any YouTube URL carrying list=.

    A watch?v=...&list=... URL is a playlist context too: show its directory
    instead of resolving and playing the video immediately.
    """
    try:
        parsed = urllib.parse.urlparse(str(url or "").strip())
        host = (parsed.hostname or "").lower()
        if parsed.scheme.lower() not in ("http", "https") or host not in {
            "youtube.com", "www.youtube.com", "m.youtube.com",
            "music.youtube.com", "youtu.be"
        }:
            return None
        query = urllib.parse.parse_qs(parsed.query)
        if not query.get("list"):
            return None
        encoded = urllib.parse.quote(str(url).strip(), safe="")
        return f"{sys.argv[0]}?action=youtube_playlist&url={encoded}"
    except Exception as e:
        xbmc.log(f"M3U YouTube playlist route error: {e}", xbmc.LOGERROR)
        return None


def _play_m3u_url(url):
    """Play one M3U entry, routing YouTube pages through the existing resolver.

    Ordinary HTTP/HLS streams and existing plugin URLs retain their previous
    Kodi playback path. YouTube webpage URLs are never sent to Player.play().
    """
    url = str(url or "").strip()
    if not url:
        return False

    # Detect YouTube by hostname first. Ordinary streams must not acquire a
    # dependency on the optional YouTube resolver module.
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    is_youtube = parsed.scheme.lower() in ("http", "https") and host in {
        "youtube.com", "www.youtube.com", "m.youtube.com",
        "music.youtube.com", "youtu.be"
    }

    if is_youtube:
        # In this add-on the resolver normally lives at
        # resources.lib.youtube_pluging. Try the current package first, then
        # the explicit Kodi add-on package, then a top-level fallback.
        module_names = []
        if __package__:
            module_names.append(f"{__package__}.youtube_pluging")
        module_names.extend(("resources.lib.youtube_pluging", "youtube_pluging"))

        youtube = None
        import_errors = []
        for module_name in dict.fromkeys(module_names):
            try:
                youtube = importlib.import_module(module_name)
                break
            except ImportError as e:
                import_errors.append(f"{module_name}: {e}")

        if youtube is None:
            error_text = "; ".join(import_errors)
            xbmc.log(f"M3U YouTube resolver unavailable: {error_text}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification(
                "YouTube Error", "Cannot import resources.lib.youtube_pluging",
                xbmcgui.NOTIFICATION_WARNING, 5000
            )
            return False

        if not youtube.is_youtube_url(url):
            return False
        # Video links resolve to plugin.video.youtube; pure playlist links use
        # the existing import flow and do not start playback automatically.
        return bool(youtube.launch_youtube_async(url))

    if "plugin://" in url.lower():
        xbmc.executebuiltin(f'PlayMedia("{url}")')
    else:
        xbmc.Player().play(url)
    return True


def player_m3u(args):
    """Play media from M3U/M3U8 playlist files (IPTV or Videos/Sounds list)
    
    إذا كان الملف يحتوي على رابط واحد فقط → شغله مباشرة
    إذا كانت هناك عدة روابط → عرض القائمة
    """
    finished = False   # True once this request's directory has been finished
    try:
        raw_json = args["VPlayerM3U"]
        data = decode_json_param(raw_json)
        file_path = data.get("path")
        ext = data.get("extension")
        filename = data.get("file")

        if not file_path or not os.path.exists(file_path):
            xbmcgui.Dialog().notification("Error", f"File not found: {file_path}")
            _end_directory_failed()
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
            _end_directory_failed()
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
                current_title = _extinf_title(line)
                i += 1
                continue
            
            # Skip EXTVLCOPT and other metadata (but continue looking for URL)
            if line.startswith("#EXTVLCOPT:") or line.startswith("#EXT-X-") or line.startswith("#"):
                i += 1
                continue
            
            # Found a valid URL/path
            if line and (line.startswith(('http://', 'https://', 'rtmp://', 'mmsh://', '/', './'))):
                # No #EXTINF title: use the last part of the URL path (without
                # the query string); fall back to the URL itself if that is empty
                item_name = current_title if current_title else (
                    os.path.basename(line.split('?', 1)[0].rstrip('/')) or line
                )
                item_name = item_name.strip()
                
                if item_name and line:
                    playlist_items.append({
                        "name": item_name,
                        "url": line,
                        "info": current_title
                    })
                
                current_title = ""
            else:
                # Not a playable URL (unsupported scheme / malformed line): skip it
                # and forget its #EXTINF title so it is not attached to the next entry
                xbmc.log(f"M3U: skipped invalid entry: {line}", xbmc.LOGWARNING)
                current_title = ""
            
            i += 1

        if not playlist_items:
            xbmcgui.Dialog().notification(
                "No Items Found",
                "Could not find playable URLs in M3U file"
            )
            _end_directory_failed()
            return

        # A single ordinary URL keeps the original direct-play behaviour.
        # A YouTube URL with list= must instead open a folder listing.
        single_playlist_route = (
            _youtube_playlist_route(playlist_items[0]["url"])
            if len(playlist_items) == 1 else None
        )
        if len(playlist_items) == 1 and not single_playlist_route:
            item = playlist_items[0]
            url = item["url"]
            name = item["name"]
            
            # Check if URL is in content
            if url not in m3u_content:
                xbmcgui.Dialog().notification(
                    "URL Not Found",
                    "URL not found in M3U file"
                )
                _end_directory_failed()
                return
            
            # Play directly every time the M3U file is opened. The old
            # play_data toggle made every second click do nothing.
            if not _play_m3u_url(url):
                xbmcgui.Dialog().notification(
                    "Playback Error", f"Could not open: {name}",
                    xbmcgui.NOTIFICATION_WARNING, 4000
                )
                _end_directory_failed()
                finished = True
                return

            xbmcgui.Dialog().notification(
                "Opened",
                f"Request sent:\n{name}",
                xbmcgui.NOTIFICATION_INFO,
                3000
            )
            # The M3U entry was opened as a directory request; there is nothing to
            # list, so finish it without a listing (Kodi stays on the previous list)
            _end_directory_failed()
            finished = True
           
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
            
            # YouTube links carrying list= are folders, not playable entries.
            # This includes watch?v=VIDEO&list=PLAYLIST links.
            playlist_route = _youtube_playlist_route(url)
            if not playlist_route:
                list_item.setProperty("IsPlayable", "true")

            # Create playback URL. The M3U content is NOT copied into the URL:
            # play_m3u_item() verifies the URL against the stored content
            # (containtxt) through parent_file instead.
            play_params = {
                "action": "play_m3u_item",
                "url": url,
                "name": item["name"],
                "parent_file": filename
            }
            json_param = urllib.parse.quote(json.dumps(play_params))
            item_url = playlist_route or f"{sys.argv[0]}?action=play_m3u_item&json={json_param}"
            
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

            xbmcplugin.addDirectoryItem(
                HANDLE, item_url, list_item, isFolder=bool(playlist_route)
            )

        xbmcplugin.endOfDirectory(HANDLE)
        finished = True

    except Exception as e:
        xbmc.log(f"M3U Parse Error: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Parse Error", f"Failed to parse M3U:\n{str(e)}")
        if not finished:
            _end_directory_failed()
   

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
    """Resolve one M3U item for Kodi playback.

    Kodi invokes this add-on action for an IsPlayable directory item. Such
    requests must finish with setResolvedUrl(); calling Player.play() from
    inside the request leaves Kodi's plugin directory request unfinished and
    can cause the busy spinner / navigation stack to grow.
    """
    try:
        if not isinstance(item_data, dict):
            raise ValueError("Invalid M3U item data")

        url = str(item_data.get("url") or "").strip()
        name = item_data.get("name", "Unknown")
        parent_file = item_data.get("parent_file")

        if not url:
            raise ValueError("Invalid URL")

        # Verify that URL exists in the M3U content if we have it.
        verify_content = item_data.get("verify_in_content")
        if verify_content and url not in verify_content:
            raise ValueError("URL is not present in the M3U file")

        if parent_file and not verify_content:
            data_media = _media_library.get("media", {})
            if parent_file in data_media:
                stored_content = data_media[parent_file].get("containtxt")
                if stored_content and url not in stored_content:
                    raise ValueError("URL is not present in the stored M3U content")

        # YouTube webpage URLs are not directly playable. Resolve them to the
        # official Kodi YouTube add-on URL before handing playback to Kodi.
        target_url = url
        parsed = urllib.parse.urlparse(url)
        host = (parsed.hostname or "").lower()
        is_youtube = parsed.scheme.lower() in ("http", "https") and host in {
            "youtube.com", "www.youtube.com", "m.youtube.com",
            "music.youtube.com", "youtu.be"
        }

        if is_youtube:
            youtube = importlib.import_module("resources.lib.youtube_pluging")
            if not youtube.is_youtube_url(url):
                raise ValueError("Invalid YouTube URL")

            if youtube.is_youtube_playlist_url(url):
                # A pure playlist is imported in a separate script. It is not
                # a single playable item and must not block this Kodi request.
                started = youtube.launch_playlist_import_async(url)
                xbmcplugin.endOfDirectory(HANDLE, succeeded=bool(started))
                return bool(started)

            video_id = youtube.extract_video_id(url)
            if not video_id:
                raise ValueError("Could not extract YouTube video ID")
            target_url = youtube.get_playable_url(video_id)

        list_item = xbmcgui.ListItem(path=target_url)
        list_item.setProperty("IsPlayable", "true")
        list_item.setInfo("video", {"title": name})

        # Complete the playable plugin request exactly once. Kodi owns the
        # playback lifecycle from this point; do not call Player.play() here.
        xbmcplugin.setResolvedUrl(HANDLE, True, list_item)
        return True

    except Exception as e:
        xbmc.log(f"M3U item resolve error: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(
            "Playback Error", f"Could not open item: {e}",
            xbmcgui.NOTIFICATION_WARNING, 5000
        )
        try:
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        except Exception:
            try:
                xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
            except Exception:
                pass
        return False

