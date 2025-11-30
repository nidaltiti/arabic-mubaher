# lib/gui/gui.py

import os
import sys
import urllib.parse
import xbmcgui
import xbmcplugin
import lib.gui.gui as cgui  # تأكَّد إنّ ملف tv.py يحتوي كلاس TV

HANDLE = int(sys.argv[1])

class GUI:
    @classmethod
    def browse_folder(cls, path=None):
        folder = path if path else TV.MEDIA_FOLDER

        if not folder or not os.path.isdir(folder):
            TV.notify("TV Addon", f"Folder not found:\n{folder}")
            return

        try:
            for media in sorted(os.listdir(folder)):
                media_path = os.path.join(folder, media)
                list_item = xbmcgui.ListItem(label=media)

                # إعداد قائمة السياق المخصصة
                context_menu = [
                    ("📄 معلومات الملف",  f"RunPlugin({sys.argv[0]}?action=info&file={urllib.parse.quote(media_path)})"),
                    ("🗑️ حذف الملف",     f"RunPlugin({sys.argv[0]}?action=delete&file={urllib.parse.quote(media_path)})")
                ]
                list_item.addContextMenuItems(context_menu)

                if os.path.isdir(media_path):
                    url = sys.argv[0] + "?path=" + urllib.parse.quote(media_path)
                    xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=True)
                else:
                    ext = os.path.splitext(media)[1].lower()
                    if ext in TV.VIDEO_EXT:
                        list_item.setInfo("video", {"title": media})
                        list_item.setProperty("IsPlayable", "true")
                    elif ext in TV.AUDIO_EXT:
                        list_item.setInfo("music", {"title": media})
                        list_item.setProperty("IsPlayable", "true")

                    url = media_path
                    xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=False)

            xbmcplugin.endOfDirectory(HANDLE)
        except Exception as e:
            TV.notify("TV Addon", f"Error browsing folder: {e}")

    @staticmethod
    def handle_action(args):
        # مثال معالِجة بسيطة للأفعال
        action = args.get("action", [None])[0]
        file   = args.get("file",   [None])[0]
        if action == "info" and file:
            TV.notify("معلومات", f"الملف: {file}")
        elif action == "delete" and file:
            try:
                os.remove(file)
                TV.notify("تم الحذف", file)
            except Exception as e:
                TV.notify("خطأ بالحذف", str(e))
        else:
            TV.notify("غير معروف", f"Action={action}, file={file}")
