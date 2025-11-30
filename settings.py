import os
import json
import xbmc

class KodiSettings:
    def __init__(self, addon_id="plugin.video.arabic-mubaher", filename="settings.json"):
        # مسار حفظ البيانات
        self.ADDON_DATA = xbmc.translatePath(f"special://profile/addon_data/{addon_id}/")
        self.FILE_PATH = os.path.join(self.ADDON_DATA, filename)

        # تأكد من وجود المجلد
        if not os.path.exists(self.ADDON_DATA):
            os.makedirs(self.ADDON_DATA)

        # تحميل أو إنشاء الملف
        if os.path.exists(self.FILE_PATH):
            with open(self.FILE_PATH, "r") as f:
                try:
                    self.settings = json.load(f)
                except:
                    self.settings = {}
        else:
            self.settings = {}
            self._save()

    def _save(self):
        """حفظ التغييرات في الملف"""
        with open(self.FILE_PATH, "w") as f:
            json.dump(self.settings, f, indent=4)

    def get(self, key, default=None):
        """إرجاع قيمة مفتاح محدد"""
        return self.settings.get(key, default)

    def set(self, key, value):
        """تعيين أو تحديث قيمة مفتاح"""
        self.settings[key] = value
        self._save()

    def remove(self, key):
        """حذف مفتاح إذا كان موجود"""
        if key in self.settings:
            del self.settings[key]
            self._save()

    def all(self):
        """إرجاع كل الإعدادات"""
        return self.settings
