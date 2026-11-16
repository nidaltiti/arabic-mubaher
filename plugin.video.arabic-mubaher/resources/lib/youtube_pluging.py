# youtube_pluging.py
"""
YouTube playback for the Kodi add-on (Kodi 19 Matrix and newer).

How it works
------------
A YouTube *page* URL (https://www.youtube.com/watch?v=...) is not a playable
stream, so it is never handed to Kodi directly. Instead the video ID is
extracted from the URL and played through the official Kodi YouTube add-on,
which resolves the real stream:

    https://www.youtube.com/watch?v=<ID>
        -> plugin://plugin.video.youtube/play/?video_id=<ID>

Requirement: the add-on "YouTube" (plugin.video.youtube) must be installed
and enabled.

Showing a playlist as a Kodi directory listing
----------------------------------------------
display_youtube_playlist(handle, url) fills the CURRENT plugin directory:
one xbmcgui.ListItem per video, added with xbmcplugin.addDirectoryItem(
handle=handle, url=<plugin url>, listitem=..., isFolder=False), then it
finishes the directory with xbmcplugin.endOfDirectory(handle) - exactly once.
Each item is a playable plugin:// URL of the YouTube add-on, so selecting it
plays that video. Nothing is played automatically.

How the handle / URL reach this module: the main add-on shows a YouTube
playlist entry as a FOLDER whose URL is get_playlist_route_url(sys.argv[0],
playlist_url). Kodi opens it by calling the add-on again with a NEW handle
(sys.argv[1]); the main add-on passes that handle and the playlist URL here.

Importing a playlist WITHOUT playing it
---------------------------------------
import_youtube_playlist(url) reads every available video of a playlist (page
by page, original order) and APPENDS them to Kodi's video playlist
(xbmc.PlayList(xbmc.PLAYLIST_VIDEO)) with playlist.add(), one
xbmcgui.ListItem per video. It never starts playback: no Player().play(),
no PlayMedia, nothing that plays as a side effect. It also never clears the
existing playlist, and skips videos that are already in it (no duplicates).
Used for playlist URLs that cannot be shown as a folder (for example an
entry of an M3U file, which Kodi treats as a playable item).

Playing a playlist
------------------
The playlist is listed through the YouTube add-on (JSON-RPC
Files.GetDirectory on plugin://plugin.video.youtube/playlist/<ID>/),
page by page, in the original order. Playback starts as soon as the FIRST
page is loaded; the remaining pages are then appended to Kodi's video
playlist while the first videos are already playing, so large playlists
start quickly and Kodi never looks frozen. Private/deleted/unplayable entries
and duplicates are skipped.

Not blocking Kodi
-----------------
Kodi shows a busy spinner for as long as an add-on call is running. So the
main add-on does NOT do the YouTube work inside its own call. It calls
launch_youtube_async(url), which starts THIS file as a separate Kodi script
(RunScript) and returns immediately. The script then resolves/plays the
video or loads the playlist on its own, with its own progress bar.

Public functions (all return True / False and never raise)
-----------------------------------------------------------
    is_youtube_url(url)          -> bool   YouTube host? (youtube.com,
                                           www./m./music.youtube.com, youtu.be)
    extract_video_id(url)        -> str | None
    extract_playlist_id(url)     -> str | None
    get_youtube_type(url)        -> "video" | "playlist" | "video_in_playlist" | "invalid"
    get_playable_url(video_id)   -> plugin:// URL that Kodi can play
    play_youtube_video(url)      -> True if playback was started
    play_youtube_playlist(url)   -> True if playback was started
    process_youtube_url(url)     -> True if playback was started, else False

Notifications: shown ONLY when something fails. Success is silent.
"""

import json
import os
import re
import sys
import time
import traceback
import urllib.parse

# Kodi modules are optional at import time so the URL helpers can be tested
# outside Kodi.
try:
    import xbmc
    import xbmcgui
    import xbmcplugin
    KODI_AVAILABLE = True
except ImportError:  # pragma: no cover - only outside Kodi
    xbmc = None
    xbmcgui = None
    xbmcplugin = None
    KODI_AVAILABLE = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

YOUTUBE_ADDON_ID = "plugin.video.youtube"

YOUTUBE_HOSTS = ("youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com")
SHORT_HOST = "youtu.be"

TYPE_VIDEO = "video"
TYPE_PLAYLIST = "playlist"
TYPE_VIDEO_IN_PLAYLIST = "video_in_playlist"
TYPE_INVALID = "invalid"

# SAFE_MODE = True  (default)
#   The YouTube add-on does ALL the work. This module only issues ONE Kodi
#   built-in call, PlayMedia(<plugin url>), for a video or a whole playlist.
#   No JSON-RPC, no progress bar, no Kodi playlist building, no extra
#   script, no loops: it cannot block or freeze Kodi.
#   (A video-inside-a-playlist link plays that video.)
# SAFE_MODE = False
#   Full import: this module lists the playlist itself and fills
#   xbmc.PlayList with one xbmcgui.ListItem per video (more control, but
#   more moving parts). Only enable it once SAFE_MODE works for you.
SAFE_MODE = True

# After importing a playlist, optionally open Kodi's video-playlist window so
# the user can see and pick a video. This only shows the list; it does not
# start playback. Default: off (the import just shows a notification).
OPEN_PLAYLIST_WINDOW = False

# Seconds to wait for Kodi to report that playback started.
# 0 (default) = do NOT wait: return True as soon as the play request is sent,
# so Kodi's UI is never blocked. Resolving errors (private/deleted video ...)
# are then reported by the YouTube add-on itself.
# A value > 0 blocks the add-on (Kodi shows a busy spinner) for up to that
# many seconds, but lets us notify when playback did not start.
PLAY_TIMEOUT = 0

# Value of the "action" parameter used to route a click on a playlist folder
# back into the add-on (see get_playlist_route_url).
PLAYLIST_ACTION = "youtube_playlist"

# Fields requested when a playlist is listed. If this Kodi rejects one of
# them (JSON-RPC "Invalid params") we fall back to the basic pair.
_BASE_PROPERTIES = ["title", "thumbnail"]
_directory_properties = ["title", "thumbnail", "plot", "runtime"]

MAX_PLAYLIST_PAGES = 100    # safety limit (the add-on returns ~50 videos per page)
MAX_PLAYLIST_ITEMS = 5000   # safety limit for huge playlists
MAX_LOAD_SECONDS = 180      # stop reading more playlist pages after this long
NOTIFY_DEDUPE_SECONDS = 3

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_PLAYLIST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,}$")
_VIDEO_PATH_PREFIXES = ("embed", "shorts", "live", "v")
_UNAVAILABLE_MARKERS = ("private video", "deleted video")

_last_notification = {"message": None, "time": 0.0}


# ---------------------------------------------------------------------------
# Logging / notifications
# ---------------------------------------------------------------------------

def _log(message, error=False):
    """Write to kodi.log (no-op outside Kodi)."""
    if not KODI_AVAILABLE:
        return
    if error:
        level = xbmc.LOGERROR
    else:
        level = getattr(xbmc, "LOGINFO", xbmc.LOGDEBUG)  # LOGINFO exists on Kodi 19+
    xbmc.log(f"[YouTube] {message}", level)


def _notify(message, warning=False, duration=5000, info=False):
    """Show a notification (an identical one just before is skipped).

    Red error icon by default; warning=True -> yellow, info=True -> normal.
    """
    if not KODI_AVAILABLE:
        return
    now = time.time()
    if (_last_notification["message"] == message
            and now - _last_notification["time"] < NOTIFY_DEDUPE_SECONDS):
        return
    _last_notification["message"] = message
    _last_notification["time"] = now

    if info:
        icon = xbmcgui.NOTIFICATION_INFO
    elif warning:
        icon = xbmcgui.NOTIFICATION_WARNING
    else:
        icon = xbmcgui.NOTIFICATION_ERROR
    xbmcgui.Dialog().notification("YouTube", message, icon, duration)


def _finish(ok, message="", notify=True, warning=False):
    """Common exit: log + notify ONLY on failure, then return the bool."""
    if not ok:
        _log(message, error=True)
        if notify:
            _notify(message, warning=warning)
    return ok


# ---------------------------------------------------------------------------
# URL detection / ID extraction (pure Python)
# ---------------------------------------------------------------------------

def _clean_url(url):
    """Return a stripped URL with a scheme, or None if unusable."""
    if not isinstance(url, str):
        return None
    url = url.strip()
    if not url:
        return None
    if "://" not in url:
        url = "https://" + url
    return url


def _valid_video_id(value):
    return bool(value) and bool(_VIDEO_ID_RE.match(value))


def _valid_playlist_id(value):
    return bool(value) and bool(_PLAYLIST_ID_RE.match(value))


def is_youtube_url(url):
    """True if the URL's host is YouTube (http/https links only).

    plugin:// paths, local files and other sites return False so the
    existing add-on code keeps handling them.
    """
    try:
        cleaned = _clean_url(url)
        if not cleaned:
            return False
        parsed = urllib.parse.urlparse(cleaned)
        if parsed.scheme.lower() not in ("http", "https"):
            return False
        host = (parsed.hostname or "").lower()
        return host == SHORT_HOST or host in YOUTUBE_HOSTS
    except Exception:
        return False


def analyze_youtube_url(url):
    """Return {"type", "video_id", "playlist_id"} for a URL.

    Supported video forms: watch?v=ID, youtu.be/ID, /embed/ID, /shorts/ID,
    /live/ID, /v/ID. Playlists come from the "list" parameter.
    """
    invalid = {"type": TYPE_INVALID, "video_id": None, "playlist_id": None}
    try:
        if not is_youtube_url(url):
            return invalid

        parsed = urllib.parse.urlparse(_clean_url(url))
        host = (parsed.hostname or "").lower()
        segments = [s for s in parsed.path.split("/") if s]
        query = urllib.parse.parse_qs(parsed.query)

        video_id = None
        playlist_id = None

        list_values = query.get("list", [])
        if list_values and _valid_playlist_id(list_values[0]):
            playlist_id = list_values[0]

        if host == SHORT_HOST:
            if segments and _valid_video_id(segments[0]):
                video_id = segments[0]
        else:
            first = segments[0].lower() if segments else ""
            if first == "watch":
                v_values = query.get("v", [])
                if v_values and _valid_video_id(v_values[0]):
                    video_id = v_values[0]
            elif first in _VIDEO_PATH_PREFIXES and len(segments) > 1:
                if _valid_video_id(segments[1]):
                    video_id = segments[1]

        if video_id and playlist_id:
            url_type = TYPE_VIDEO_IN_PLAYLIST
        elif video_id:
            url_type = TYPE_VIDEO
        elif playlist_id:
            url_type = TYPE_PLAYLIST
        else:
            url_type = TYPE_INVALID

        return {"type": url_type, "video_id": video_id, "playlist_id": playlist_id}
    except Exception:
        return invalid


def extract_video_id(url):
    """Return the video ID found in the URL, or None."""
    return analyze_youtube_url(url)["video_id"]


def extract_playlist_id(url):
    """Return the playlist ID found in the URL, or None."""
    return analyze_youtube_url(url)["playlist_id"]


def get_youtube_type(url):
    """Return "video", "playlist", "video_in_playlist" or "invalid"."""
    return analyze_youtube_url(url)["type"]


def is_youtube_playlist_url(url):
    """True only for a pure playlist link (youtube.com/playlist?list=...).

    A video link that merely carries a list= parameter is a video, not a
    playlist, so it returns False.
    """
    return get_youtube_type(url) == TYPE_PLAYLIST


def get_playable_url(video_id):
    """Convert a video ID into a URL Kodi can play (via the YouTube add-on)."""
    return f"plugin://{YOUTUBE_ADDON_ID}/play/?video_id={video_id}"


# ---------------------------------------------------------------------------
# Kodi helpers
# ---------------------------------------------------------------------------

def _addon_ready():
    """True if plugin.video.youtube is installed AND enabled."""
    try:
        return bool(xbmc.getCondVisibility(f"System.AddonIsEnabled({YOUTUBE_ADDON_ID})"))
    except Exception:
        return False


def _set_title(list_item, title):
    """Set the title (InfoTagVideo on Kodi 20+, setInfo on Kodi 19)."""
    try:
        list_item.getVideoInfoTag().setTitle(title)
    except Exception:
        list_item.setInfo("video", {"title": title})


def _wait_for_playback(player, timeout=None):
    """Wait until Kodi reports playback started. True/False."""
    if timeout is None:
        timeout = PLAY_TIMEOUT  # read at call time so changing the constant works
    if timeout <= 0:
        return True  # "request initiated" is enough
    monitor = xbmc.Monitor()
    waited = 0.0
    step = 0.25
    while waited < timeout:
        if player.isPlaying():
            return True
        if monitor.waitForAbort(step):  # Kodi is shutting down
            return False
        waited += step
    return bool(player.isPlaying())


def _playlist_play_path(playlist_id):
    """Path that makes the YouTube add-on build and play the playlist itself."""
    return f"plugin://{YOUTUBE_ADDON_ID}/play/?playlist_id={playlist_id}"


def _play_media(path):
    """Fire-and-forget playback with Kodi's PlayMedia built-in.

    Returns immediately (Kodi does the resolving in the background), so it
    can never block the add-on. This is the same call the main add-on already
    uses for plugin:// paths.
    """
    _log(f"PlayMedia {path}")
    xbmc.executebuiltin(f'PlayMedia("{path}")')
    return True


def _play_path(path):
    """Start playback of one playable path with xbmc.Player."""
    list_item = xbmcgui.ListItem(path=path)
    list_item.setProperty("IsPlayable", "true")

    player = xbmc.Player()
    player.play(path, list_item)
    return _wait_for_playback(player)


# ---------------------------------------------------------------------------
# Playlist helpers
# ---------------------------------------------------------------------------

def _playlist_dir(playlist_id):
    """Directory path that lists a playlist's videos (read via JSON-RPC)."""
    return f"plugin://{YOUTUBE_ADDON_ID}/playlist/{playlist_id}/"


def _get_directory(path):
    """List a plugin directory via JSON-RPC: list of entries, [] or None (error)."""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "Files.GetDirectory",
        "params": {"directory": path, "media": "video",
                   "properties": list(_directory_properties)},
    }
    try:
        response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    except Exception as e:
        _log(f"JSON-RPC failed for {path}: {e}", error=True)
        return None

    if "error" in response:
        error = response["error"] or {}
        # -32602 = "Invalid params": this Kodi doesn't know one of the extra
        # properties. Remember that and retry once with the basic ones.
        if error.get("code") == -32602 and _directory_properties != _BASE_PROPERTIES:
            _directory_properties[:] = _BASE_PROPERTIES
            return _get_directory(path)
        _log(f"JSON-RPC error for {path}: {error}", error=True)
        return None
    return response.get("result", {}).get("files") or []


def _is_next_page(path, playlist_id):
    """True if a directory entry is the 'next page' link of this playlist.

    The YouTube add-on's own pagination token (page_token) is accepted
    whatever the path layout is, so a different URL layout in another
    add-on version does not silently cut the list after the first page.
    """
    lowered = (path or "").lower()
    if not lowered.startswith(f"plugin://{YOUTUBE_ADDON_ID}/"):
        return False
    query = urllib.parse.urlparse(path).query.lower()
    if "page_token" in query:
        return True
    return f"/playlist/{playlist_id.lower()}" in lowered and "page" in query


def _video_id_from_plugin_path(path):
    """Pull video_id out of a plugin://.../play/?video_id=... path."""
    try:
        values = urllib.parse.parse_qs(urllib.parse.urlparse(path).query).get("video_id", [])
        if values and _valid_video_id(values[0]):
            return values[0]
    except Exception:
        pass
    return None


class _PlaylistReader:
    """Reads a YouTube playlist page by page, in order.

    Skips private/deleted/unplayable entries and duplicates, and follows the
    "next page" entries, so pagination and big playlists are supported.

    Attributes:
        failed:   True if the FIRST page could not be listed at all
        partial:  True if a LATER page failed (we keep what we already have)
        skipped:  number of unavailable entries skipped so far
        total:    number of playable videos returned so far
    """

    def __init__(self, playlist_id):
        self.playlist_id = playlist_id
        self.queue = [_playlist_dir(playlist_id)]
        self.visited = set()
        self.seen_ids = set()
        self.pages = 0
        self.total = 0
        self.skipped = 0
        self.failed = False
        self.partial = False
        self.monitor = xbmc.Monitor()
        self.started = time.time()

    def exhausted(self):
        """True when there is nothing more to read (or we must stop)."""
        return (
            not self.queue
            or self.pages >= MAX_PLAYLIST_PAGES
            or self.total >= MAX_PLAYLIST_ITEMS
            or self.monitor.abortRequested()  # Kodi is closing
            or self._out_of_time()
        )

    def _out_of_time(self):
        if time.time() - self.started > MAX_LOAD_SECONDS:
            _log(f"Stopped loading playlist after {MAX_LOAD_SECONDS}s "
                 f"({self.total} videos so far)")
            return True
        return False

    def read_next_page(self):
        """Read one page. Returns a list of new items (possibly empty).

        Item = {"title", "path", "video_id", "thumb"}
        """
        while self.queue:
            directory = self.queue.pop(0)
            if directory in self.visited:
                continue
            self.visited.add(directory)
            self.pages += 1

            page_started = time.time()
            entries = _get_directory(directory)
            _log(f"Playlist page {self.pages} read in {time.time() - page_started:.1f}s")
            if entries is None:
                # Network / add-on error: stop reading further pages
                if self.pages == 1:
                    self.failed = True
                else:
                    self.partial = True
                self.queue = []
                return []

            items = []
            for entry in entries:
                path = entry.get("file") or ""
                title = entry.get("title") or entry.get("label") or ""

                if entry.get("filetype") == "directory":
                    if _is_next_page(path, self.playlist_id):
                        self.queue.append(path)
                    else:
                        # Helps diagnosing a pagination mismatch in kodi.log
                        _log(f"Ignored folder entry in playlist listing: {path}")
                    continue

                video_id = _video_id_from_plugin_path(path)
                if (not video_id
                        or any(m in title.lower() for m in _UNAVAILABLE_MARKERS)):
                    self.skipped += 1          # unavailable / deleted / private
                    continue
                if video_id in self.seen_ids:
                    continue                    # avoid duplicate items
                if self.total >= MAX_PLAYLIST_ITEMS:
                    break
                self.seen_ids.add(video_id)

                items.append({
                    "title": title or video_id,
                    "path": path if path.startswith("plugin://") else get_playable_url(video_id),
                    "video_id": video_id,
                    "thumb": entry.get("thumbnail") or "",
                    "plot": entry.get("plot") or "",
                    "duration": _to_seconds(entry.get("runtime")),
                })
                self.total += 1
            return items
        return []


def _to_seconds(value):
    """Safe int conversion for a runtime/duration value."""
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _set_video_info(list_item, item):
    """Title, plot, duration and media type (InfoTagVideo on Kodi 20+,
    setInfo on Kodi 19)."""
    title = item["title"]
    plot = item.get("plot") or ""
    duration = item.get("duration") or 0
    try:
        tag = list_item.getVideoInfoTag()
        tag.setTitle(title)
        tag.setMediaType("video")
        if plot:
            tag.setPlot(plot)
        if duration > 0:
            tag.setDuration(duration)
    except Exception:
        info = {"title": title, "mediatype": "video"}
        if plot:
            info["plot"] = plot
        if duration > 0:
            info["duration"] = duration
        list_item.setInfo("video", info)


def _make_list_item(item):
    """Create the xbmcgui.ListItem for one playlist video."""
    list_item = xbmcgui.ListItem(label=item["title"], path=item["path"])
    list_item.setProperty("IsPlayable", "true")
    _set_video_info(list_item, item)
    if item["thumb"]:
        list_item.setArt({"thumb": item["thumb"], "icon": item["thumb"]})
    return list_item


def _add_to_playlist(playlist, items):
    """Append items (in order) to a Kodi playlist with playlist.add()."""
    for item in items:
        playlist.add(url=item["path"], listitem=_make_list_item(item))


def _open_progress():
    """Small background progress bar so Kodi doesn't look frozen."""
    try:
        progress = xbmcgui.DialogProgressBG()
        progress.create("YouTube", "Loading playlist...")
        return progress
    except Exception:
        return None


def _update_progress(progress, reader):
    if progress is None:
        return
    try:
        percent = min(95, reader.pages * 100 // MAX_PLAYLIST_PAGES + 5)
        progress.update(percent, "YouTube", f"Loading playlist... {reader.total} videos")
    except Exception:
        pass


def _close_progress(progress):
    if progress is not None:
        try:
            progress.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Public playback functions
# ---------------------------------------------------------------------------

def play_youtube_video(url, notify=True):
    """Extract the video ID, resolve it via the YouTube add-on and play it.

    Returns:
        True  - playback was started
        False - invalid URL / add-on missing / playback could not start
                (a notification is shown unless notify=False)
    """
    try:
        video_id = extract_video_id(url)
        if not video_id:
            return _finish(False, "Invalid YouTube video URL", notify, warning=True)

        if not _addon_ready():
            return _finish(
                False,
                "YouTube add-on (plugin.video.youtube) is not installed or disabled",
                notify,
            )

        if SAFE_MODE:
            return _play_media(get_playable_url(video_id))

        if _play_path(get_playable_url(video_id)):
            return True  # success is silent

        return _finish(
            False, "Video could not be played (private, deleted or restricted?)", notify
        )
    except Exception as e:
        _log(f"play_youtube_video failed: {e}\n{traceback.format_exc()}", error=True)
        return _finish(False, f"YouTube error: {e}", notify)


def play_youtube_playlist(url, notify=True, start_video_id=None):
    """Load a YouTube playlist into Kodi's video playlist and play it.

    Steps: extract the playlist ID -> read the first page -> build the
    xbmc.PlayList (one xbmcgui.ListItem per video, original order) -> start
    xbmc.Player().play(playlist) -> keep appending the remaining pages while
    the first videos play.

    If start_video_id is given (URL had both a video and a playlist ID),
    playback starts at that video.

    Returns:
        True  - playlist loaded and playback initiated
        False - invalid URL, add-on missing, or playlist could not be loaded
                (a notification is shown unless notify=False)
    """
    progress = None
    try:
        playlist_id = extract_playlist_id(url)
        if not playlist_id:
            return _finish(False, "Invalid YouTube playlist URL", notify, warning=True)

        if not _addon_ready():
            return _finish(
                False,
                "YouTube add-on (plugin.video.youtube) is not installed or disabled",
                notify,
            )

        if SAFE_MODE:
            if start_video_id:
                return _play_media(get_playable_url(start_video_id))
            return _play_media(_playlist_play_path(playlist_id))

        reader = _PlaylistReader(playlist_id)
        progress = _open_progress()
        items = []
        start_index = None

        # Phase 1: read pages until there is something to start with
        # (or, for a video-in-playlist link, until that video is found).
        while not reader.exhausted():
            items.extend(reader.read_next_page())
            _update_progress(progress, reader)

            if start_video_id:
                for index, item in enumerate(items):
                    if item["video_id"] == start_video_id:
                        start_index = index
                        break
                if start_index is not None:
                    break
            elif items:
                break

        if reader.failed:
            if start_video_id:
                # Link also had a video: at least play that one
                _log(f"Playlist {playlist_id} not loadable; playing the single video")
                return play_youtube_video(
                    f"https://www.youtube.com/watch?v={start_video_id}", notify=notify
                )
            return _finish(
                False,
                "Playlist could not be loaded (network error, private/deleted playlist, "
                "or YouTube add-on API not configured)",
                notify,
            )

        if not items:
            return _finish(False, "Playlist is empty or has no available videos",
                           notify, warning=True)

        if start_index is None:
            start_index = 0

        # Phase 2: build the Kodi playlist and START PLAYBACK right away
        kodi_playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        kodi_playlist.clear()
        _add_to_playlist(kodi_playlist, items)

        player = xbmc.Player()
        player.play(kodi_playlist, startpos=start_index)

        # Phase 3: while it plays, append the remaining pages in order
        while not reader.exhausted():
            page = reader.read_next_page()
            _add_to_playlist(kodi_playlist, page)
            items.extend(page)
            _update_progress(progress, reader)

        _log(f"Playlist {playlist_id}: {len(items)} videos loaded, "
             f"{reader.skipped} unavailable skipped, {reader.pages} page(s)")

        if reader.partial and notify:
            _notify(f"Only part of the playlist could be loaded ({len(items)} videos)",
                    warning=True)

        if _wait_for_playback(player):
            return True
        return _finish(False, "Playlist could not be played", notify)

    except Exception as e:
        _log(f"play_youtube_playlist failed: {e}\n{traceback.format_exc()}", error=True)
        return _finish(False, f"YouTube error: {e}", notify)
    finally:
        _close_progress(progress)


def get_playlist_route_url(base_url, playlist_url):
    """Plugin URL that makes the add-on LIST a playlist's videos.

    Args:
        base_url:     the add-on's own base URL, i.e. sys.argv[0]
                      (e.g. "plugin://plugin.video.arabic-mubaher/")
        playlist_url: the YouTube playlist URL

    Use it as the URL of a FOLDER item (isFolder=True, no IsPlayable). Kodi
    then opens it as a directory by calling the add-on again with a new
    handle, and the add-on answers with display_youtube_playlist().
    """
    encoded = urllib.parse.quote((playlist_url or "").strip(), safe="")
    return f"{base_url}?action={PLAYLIST_ACTION}&url={encoded}"


def display_youtube_playlist(handle, url, notify=True, finalize=True):
    """Show every available video of a YouTube playlist in the CURRENT
    Kodi directory, using xbmcplugin.addDirectoryItem().

    Nothing is played: the user selects a video manually. Kodi playlists are
    not touched.

    Args:
        handle:   the plugin handle Kodi passed to the add-on (int(sys.argv[1])).
        url:      YouTube playlist URL (any valid one; the ID is extracted).
        notify:   show a notification on errors.
        finalize: call xbmcplugin.endOfDirectory(handle) here (exactly once,
                  also on failure, so Kodi never waits forever). Pass False
                  only if the caller finishes the directory itself, using the
                  returned value as `succeeded`.

    Returns:
        True  - at least one video was added to the directory
        False - invalid URL / add-on missing / playlist could not be loaded
                or was empty (a notification explains why)
    """
    if (not KODI_AVAILABLE or isinstance(handle, bool)
            or not isinstance(handle, int) or handle < 0):
        # Without a valid handle there is no directory to finish
        return _finish(False, "Invalid Kodi directory handle", notify)

    succeeded = False
    added = 0
    progress = None
    try:
        if not is_youtube_url(url):
            return _finish(False, "Invalid YouTube playlist URL", notify, warning=True)
        playlist_id = extract_playlist_id(url)
        if not playlist_id:
            return _finish(False, "Invalid YouTube playlist URL", notify, warning=True)

        if not _addon_ready():
            return _finish(
                False,
                "YouTube add-on (plugin.video.youtube) is not installed or disabled",
                notify,
            )

        reader = _PlaylistReader(playlist_id)
        progress = _open_progress()

        xbmcplugin.setContent(handle, "videos")
        # Keep the playlist's original order (do not let Kodi re-sort by title)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_UNSORTED)
        try:
            xbmcplugin.setPluginCategory(handle, "YouTube playlist")
        except Exception:
            pass

        cancelled = False
        while not reader.exhausted() and not cancelled:
            for item in reader.read_next_page():     # already de-duplicated
                result = xbmcplugin.addDirectoryItem(
                    handle=handle,
                    url=item["path"],                 # plugin://plugin.video.youtube/play/?video_id=...
                    listitem=_make_list_item(item),   # title, art, metadata, IsPlayable=true
                    isFolder=False,
                )
                if result is False:                   # the user cancelled the listing
                    cancelled = True
                    break
                added += 1
            _update_progress(progress, reader)

        _log(f"Directory {playlist_id}: {added} videos, {reader.skipped} unavailable "
             f"skipped, {reader.pages} page(s)")

        if added == 0:
            if cancelled:
                # The user backed out of Kodi's busy dialog: not an error
                _log("Playlist listing cancelled by the user")
                return False
            if reader.failed:
                return _finish(
                    False,
                    "Playlist could not be loaded (network error, private/deleted "
                    "playlist, or YouTube add-on API not configured)",
                    notify,
                )
            return _finish(False, "Playlist is empty or has no available videos",
                           notify, warning=True)

        if reader.partial and notify:
            _notify(f"Only part of the playlist could be loaded ({_plural(added)})",
                    warning=True)

        succeeded = True
        return True

    except Exception as e:
        _log(f"display_youtube_playlist failed: {e}\n{traceback.format_exc()}", error=True)
        succeeded = added > 0      # keep what was already listed
        _finish(False, f"YouTube error: {e}", notify)
        return succeeded
    finally:
        _close_progress(progress)
        if finalize:
            # The ONE place the directory is finished for this request.
            try:
                xbmcplugin.endOfDirectory(handle, succeeded=succeeded, cacheToDisc=False)
            except Exception as e:
                _log(f"endOfDirectory failed: {e}", error=True)


def _existing_playlist_video_ids():
    """Video IDs already in Kodi's video playlist (used to avoid duplicates)."""
    ids = set()
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "Playlist.GetItems",
        "params": {"playlistid": xbmc.PLAYLIST_VIDEO, "properties": ["file"]},
    }
    try:
        response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
        for entry in response.get("result", {}).get("items", []) or []:
            video_id = _video_id_from_plugin_path(entry.get("file") or "")
            if video_id:
                ids.add(video_id)
    except Exception as e:
        _log(f"Could not read the current playlist: {e}", error=True)
    return ids


def _plural(count, word="video"):
    return f"{count} {word}" + ("" if count == 1 else "s")


def import_youtube_playlist(url, notify=True):
    """Add every available video of a YouTube playlist to Kodi's video playlist.

    Playback is NOT started and the existing playlist is NOT cleared. Videos
    already in the playlist, duplicates, and private/deleted videos are
    skipped. Pagination is followed, so large playlists are supported.

    Returns:
        True  - at least one video was added (a notification shows how many)
        False - invalid URL, add-on missing, playlist could not be loaded,
                empty, or nothing new to add (a notification explains why)
    """
    progress = None
    try:
        if not is_youtube_url(url):
            return _finish(False, "Invalid YouTube playlist URL", notify, warning=True)
        playlist_id = extract_playlist_id(url)
        if not playlist_id:
            return _finish(False, "Invalid YouTube playlist URL", notify, warning=True)

        if not _addon_ready():
            return _finish(
                False,
                "YouTube add-on (plugin.video.youtube) is not installed or disabled",
                notify,
            )

        reader = _PlaylistReader(playlist_id)
        progress = _open_progress()
        existing_ids = _existing_playlist_video_ids()
        kodi_playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)  # NOT cleared

        added = 0
        already_there = 0

        while not reader.exhausted():
            for item in reader.read_next_page():
                if item["video_id"] in existing_ids:
                    already_there += 1
                    continue
                kodi_playlist.add(url=item["path"], listitem=_make_list_item(item))
                existing_ids.add(item["video_id"])
                added += 1
            _update_progress(progress, reader)

        _log(f"Import {playlist_id}: {added} added, {already_there} already in "
             f"playlist, {reader.skipped} unavailable, {reader.pages} page(s)")

        if reader.failed:
            return _finish(
                False,
                "Playlist could not be loaded (network error, private/deleted "
                "playlist, or YouTube add-on API not configured)",
                notify,
            )
        if reader.total == 0:
            return _finish(False, "Playlist is empty or has no available videos",
                           notify, warning=True)
        if added == 0:
            return _finish(
                False,
                f"Nothing added: all {_plural(already_there)} are already in the playlist",
                notify, warning=True,
            )

        message = f"{_plural(added)} added to the playlist"
        extras = []
        if already_there:
            extras.append(f"{already_there} already there")
        if reader.skipped:
            extras.append(f"{reader.skipped} unavailable")
        if reader.partial:
            extras.append("loading stopped early")
        if extras:
            message += " (" + ", ".join(extras) + ")"
        if notify:
            _notify(message, warning=reader.partial, info=not reader.partial)

        if OPEN_PLAYLIST_WINDOW:
            # Only SHOWS the list; it does not start playback.
            xbmc.executebuiltin("ActivateWindow(VideoPlaylist)")
        return True

    except Exception as e:
        _log(f"import_youtube_playlist failed: {e}\n{traceback.format_exc()}", error=True)
        return _finish(False, f"YouTube error: {e}", notify)
    finally:
        _close_progress(progress)


def process_youtube_url(url, notify=True):
    """Entry point: pick video / playlist handling for a URL.

    Returns:
        True  - playback was started
        False - not a YouTube URL, invalid URL, or playback could not start

    A non-YouTube URL returns False SILENTLY (no notification). Use
    is_youtube_url(url) first if you need to tell "not YouTube" apart from
    "YouTube but failed".
    """
    try:
        if not KODI_AVAILABLE or not is_youtube_url(url):
            return False

        analysis = analyze_youtube_url(url)
        url_type = analysis["type"]

        if url_type == TYPE_VIDEO:
            return play_youtube_video(url, notify=notify)
        if url_type == TYPE_PLAYLIST:
            # Playlist URLs are IMPORTED into Kodi's playlist, not played.
            return import_youtube_playlist(url, notify=notify)
        if url_type == TYPE_VIDEO_IN_PLAYLIST:
            # Play the playlist, starting at the given video
            return play_youtube_playlist(
                url, notify=notify, start_video_id=analysis["video_id"]
            )

        return _finish(False, "Invalid YouTube URL", notify, warning=True)
    except Exception as e:
        _log(f"process_youtube_url failed: {e}\n{traceback.format_exc()}", error=True)
        return _finish(False, f"YouTube error: {e}", notify)


# ---------------------------------------------------------------------------
# Non-blocking entry point (used by the main add-on) + script entry
# ---------------------------------------------------------------------------

SCRIPT_PATH = os.path.abspath(__file__)


def _run_mode(mode, url):
    """Run the work for a mode: "import" (playlist import) or "play"."""
    if mode == "import":
        return import_youtube_playlist(url)
    return process_youtube_url(url)


def _launch_script(mode, url, inline):
    """Start this file as a separate Kodi script: RunScript(file, mode, url).

    inline: function to call instead if the script file cannot be found
    (each caller passes its OWN function, so the playlist-import path can
    never end up in the playback code).
    """
    if not os.path.isfile(SCRIPT_PATH):
        # Should not happen; fall back to running inline
        _log("Script file not found; running inline", error=True)
        return inline(url)

    # Fully percent-encode the URL so commas, '&', '?' etc. cannot break
    # RunScript's argument parsing.
    argument = urllib.parse.quote(url.strip(), safe="")
    xbmc.executebuiltin(f'RunScript("{SCRIPT_PATH}","{mode}","{argument}")')
    _log(f"Launched script ({mode}) for {url}")
    return True


def launch_playlist_import_async(url):
    """Import a playlist in a separate Kodi script and return AT ONCE.

    Reading a playlist can take a while, so it never runs inside the add-on
    call (Kodi would show a busy spinner). The script shows the result as a
    notification. No playback is started.

    Returns True if the script was started, False for non-YouTube URLs.
    """
    try:
        if not KODI_AVAILABLE or not is_youtube_url(url):
            return False
        return _launch_script("import", url, import_youtube_playlist)
    except Exception as e:
        _log(f"launch_playlist_import_async failed: {e}\n{traceback.format_exc()}", error=True)
        return _finish(False, f"YouTube error: {e}")


def launch_youtube_async(url):
    """Main entry for the add-on: handle any YouTube URL WITHOUT blocking Kodi.

        playlist URL        -> imported into Kodi's video playlist (no playback)
        video URL           -> played

    Returns:
        True  - the URL was handed over (the script notifies on failure)
        False - not a YouTube URL / could not be started
    """
    try:
        if not KODI_AVAILABLE or not is_youtube_url(url):
            return False

        if is_youtube_playlist_url(url):
            return _launch_script("import", url, import_youtube_playlist)

        if SAFE_MODE:
            # Only one instant built-in call is needed: no separate script
            return process_youtube_url(url)

        return _launch_script("play", url, process_youtube_url)
    except Exception as e:
        _log(f"launch_youtube_async failed: {e}\n{traceback.format_exc()}", error=True)
        return _finish(False, f"YouTube error: {e}")


def _run_as_script(argv):
    """Runs when Kodi starts this file with RunScript(<file>, <mode>, <url>)."""
    if len(argv) >= 3:
        mode, url = argv[1], urllib.parse.unquote(argv[2])
    elif len(argv) == 2:
        mode, url = "play", urllib.parse.unquote(argv[1])   # older single-argument form
    else:
        mode, url = "play", ""
    _log(f"Script started ({mode}) for: {url}")
    result = _run_mode(mode, url)
    _log(f"Script finished, result={result}")


if __name__ == "__main__":
    _run_as_script(sys.argv)