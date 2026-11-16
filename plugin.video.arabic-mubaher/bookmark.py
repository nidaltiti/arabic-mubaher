# bookmark.py
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
from m3u_file import player_m3u, play_m3u_item, save_m3u_item, download_m3u_item, set_dependencies

# YouTube links (youtube.com/watch?v=..., youtu.be/..., youtube.com/playlist?list=...)
# are web pages, NOT playable streams, so they must never be handed to
# PlayMedia/xbmc.Player directly. youtube_pluging.py turns them into
# plugin://plugin.video.youtube/... URLs (official YouTube add-on) and plays them.
try:
    from  resources.lib.youtube_pluging import (
        is_youtube_url,
        is_youtube_playlist_url,
        launch_youtube_async,
        get_playlist_route_url,
    )
    YOUTUBE_AVAILABLE = True
except Exception as _yt_err:
    # youtube_pluging.py missing / not in the same folder / has an error.
    # Bookmarks keep working; YouTube links just show a notification.
    YOUTUBE_AVAILABLE = False
    xbmc.log(f"[YouTube] Could not import youtube_pluging.py: {_yt_err}", xbmc.LOGERROR)


class bookmark:

    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.addon_path = self.addon.getAddonInfo('path')
        self.bookmark_manager = BookmarkManager(filename="bookmarks.db")

        self.settings_instance = KodiSettings(filename="media_library.json")
       
    def show_favorites(self):
        DEFAULT_THUMB = 'https://is3-ssl.mzstatic.com/image/thumb/Purple124/v4/2c/e6/9c/2ce69c27-3430-cd72-d954-5dad69956bfb/source/512x512bb.jpg'
        handle = int(sys.argv[1])

        bookmarks = self.bookmark_manager.read_all()
        _media = self.settings_instance.get("media", {})
        
        if not bookmarks:
            xbmcgui.Dialog().ok("المفضلة", "لا توجد مفضلة محفوظة.")
            # Always finish the directory, otherwise Kodi keeps waiting for it
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return
        
        # Keyed by name: a bookmark that appears twice is listed only once
        favorites = {
            bookmark: _media[bookmark]
            for bookmark in bookmarks
            if bookmark in _media
        }
        
        if not favorites:
            xbmcgui.Dialog().ok("المفضلة", "لا توجد بيانات للمفضلة المحفوظة.")
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return
        
        for favorite in favorites:
            try:
                media_item = favorites[favorite]
                
                # التحقق من وجود path
                if not isinstance(media_item, dict) or 'path' not in media_item:
                    continue
                
                path = media_item['path']
                if not path:
                    continue

                # A YouTube PLAYLIST bookmark opens as a folder that lists the
                # playlist's videos (same route the main add-on uses); a
                # playlist cannot be played as if it were one video.
                is_playlist = bool(
                    YOUTUBE_AVAILABLE and isinstance(path, str) and is_youtube_playlist_url(path)
                )
                
                list_item = xbmcgui.ListItem(label=favorite)
                list_item.setArt({'thumb': DEFAULT_THUMB})
                list_item.setProperty("IsFolder", "true" if is_playlist else "false")
                list_item.addContextMenuItems([("Remove from bookmarks", f"RunPlugin({sys.argv[0]}?action=remove&name={urllib.parse.quote(favorite)})")])
                
                # بناء URL بشكل صحيح
                if is_playlist:
                    url = get_playlist_route_url(sys.argv[0], path)
                else:
                    url = f"{sys.argv[0]}?action=play&path={urllib.parse.quote(path, safe='')}"
                
                xbmcplugin.addDirectoryItem(
                    handle=handle,
                    url=url,
                    listitem=list_item,
                    isFolder=is_playlist
                )
            except Exception as e:
                xbmc.log(f"خطأ في المفضلة {favorite}: {str(e)}", xbmc.LOGERROR)
                continue
        
        xbmcplugin.endOfDirectory(handle)


def _notify(message):
    """Show an error notification (never raises)."""
    try:
        xbmcgui.Dialog().notification("المفضلة", message, xbmcgui.NOTIFICATION_ERROR, 4000)
    except Exception:
        pass


def _is_youtube_link(url):
    """True if the URL is a YouTube WEB link that must be resolved first."""
    if YOUTUBE_AVAILABLE:
        return is_youtube_url(url)
    # youtube_pluging.py could not be imported: a crude guard so that a
    # YouTube page URL is still never passed to the player.
    lowered = url.lower()
    return lowered.startswith(("http://", "https://")) and (
        "youtube.com" in lowered or "youtu.be" in lowered
    )


def _play_youtube_bookmark(url):
    """Play a bookmarked YouTube link through youtube_pluging.py.

    Video link          -> plugin://plugin.video.youtube/play/?video_id=<ID>
    watch?v=..&list=..  -> that video
    Playlist link       -> opens the playlist's videos as a list
    Invalid link / missing YouTube add-on -> notification from youtube_pluging

    Returns True if the request was handed over, False otherwise.
    """
    if not YOUTUBE_AVAILABLE:
        _notify("دعم يوتيوب غير متاح (youtube_pluging.py)")
        return False

    if is_youtube_playlist_url(url):
        # Normally a playlist bookmark is already shown as a folder by
        # show_favorites(); this covers an old/direct "play" link.
        route = get_playlist_route_url(sys.argv[0], url)
        xbmc.executebuiltin(f'Container.Update("{route}")')
        return True

    # True/False; youtube_pluging shows its own notification on failure
    return bool(launch_youtube_async(url))


def play_video(url):
    """تشغيل الفيديو بشكل صحيح

    Returns True if playback was requested, False otherwise.
    """
    try:
        url = (url or "").strip()
        if not url:
            return False

        # YouTube web links are resolved by the YouTube add-on first
        if _is_youtube_link(url):
            return _play_youtube_bookmark(url)

        # الأنواع الأخرى: plugin, محلي, وروابط. The URL is quoted so that
        # commas / special characters in it cannot split the built-in's arguments.
        xbmc.executebuiltin(f'PlayMedia("{url}")')
        return True
    except Exception as e:
        xbmc.log(f"خطأ في تشغيل الفيديو: {str(e)}", xbmc.LOGERROR)
        _notify("تعذّر تشغيل الفيديو")
        return False

# معالجة المعاملات والأوامر
try:
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
    action = params.get("action")
    path = params.get("path")
    
    if action == "play" and path:
        play_video(path)
    elif action == "favorites":
        bm = bookmark()
        bm.show_favorites()
    elif action == "remove":
        name = params.get("name")
        if name:
            bm = bookmark()
            bm.bookmark_manager.remove(name)
            xbmcgui.Dialog().ok("المفضلة", f"تم إزالة {name} من المفضلة.")
            # "remove" is started with RunPlugin from the context menu, so there
            # is no directory to build here (the old call to show_favorites()
            # used handle -1). Just refresh the list that is on screen.
            xbmc.executebuiltin("Container.Refresh()")
except Exception as e:
    xbmc.log(f"خطأ في معالجة الأوامر: {str(e)}", xbmc.LOGERROR)